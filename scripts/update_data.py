#!/usr/bin/env python3
"""
Eddlewood FC website - live data updater.

Fetches fixtures, results and the league table from the West of Scotland
Football League website (www.wosfl.co.uk, run on LeagueRepublic) and writes
data/live.json, which the website renders from.

Designed to run unattended (e.g. GitHub Actions cron):
  * every section (results / fixtures / table) is validated separately;
    if a fetch or parse fails, the last good copy of that section is kept;
  * the file is written atomically, and never replaced with something worse;
  * the script always exits 0 so a temporary outage never breaks the site.
    Problems are recorded in live.json -> "warnings" and printed to the log.

The WoSFL site sits behind an AWS WAF JavaScript check. Plain HTTP is tried
first; if the challenge page comes back, headless Chrome is used instead
(Chrome is preinstalled on GitHub's ubuntu runners).

Season roll-over is automatic: the season ID and Eddlewood's team ID are
re-discovered from the WoSFL home page, and the division is found by looking
for Eddlewood in each division's table (so promotion is handled too).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

BASE = "https://www.wosfl.co.uk"
TEAM_NAME = "Eddlewood"
HOME_VENUE = "Eddlewood Park"
UK = ZoneInfo("Europe/London")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "live.json"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")

# Known IDs for 2026-27 (used first; re-discovered automatically if they stop working)
DEFAULTS = {"season_id": "236635540", "team_id": "56981581", "division_id": "262552944"}

warnings: list[str] = []
_chrome_profile = tempfile.mkdtemp(prefix="wosfl-chrome-")


def log(msg: str) -> None:
    print(f"[update] {msg}", flush=True)


def warn(msg: str) -> None:
    warnings.append(msg)
    log("WARNING: " + msg)


# --------------------------------------------------------------------------- fetch
def _is_challenge(html: str) -> bool:
    return ("awswaf" in html or "challenge-container" in html
            or "verify that you're not a robot" in html or len(html) < 5000)


def _chrome_bin() -> str | None:
    for name in (os.environ.get("CHROME_PATH"), "google-chrome", "google-chrome-stable",
                 "chromium", "chromium-browser"):
        if name and shutil.which(name):
            return shutil.which(name)
    return None


def fetch(path: str) -> str:
    url = path if path.startswith("http") else BASE + path
    # 1) plain HTTP
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB"})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", "replace")
        if not _is_challenge(html):
            return html
    except Exception as e:  # noqa: BLE001
        log(f"plain fetch failed for {url}: {e}")
    # 2) headless Chrome (solves the WAF JavaScript check)
    chrome = _chrome_bin()
    if not chrome:
        raise RuntimeError("blocked by WAF and no Chrome available")
    for attempt in range(3):
        profile = tempfile.mkdtemp(dir=_chrome_profile)
        out_path = os.path.join(profile, "dom.html")
        try:
            with open(out_path, "w") as out:
                proc = subprocess.Popen(
                    [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
                     "--disable-dev-shm-usage", "--no-first-run",
                     f"--user-agent={UA}", "--virtual-time-budget=15000", "--dump-dom", url],
                    stdout=out, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                    start_new_session=True)
                try:
                    proc.wait(timeout=90)
                finally:
                    try:
                        os.killpg(proc.pid, 9)
                    except Exception:  # noqa: BLE001
                        pass
            html = Path(out_path).read_text(errors="replace")
            if html and not _is_challenge(html):
                return html
        except Exception as e:  # noqa: BLE001
            log(f"chrome fetch attempt {attempt + 1} failed for {url}: {e}")
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"could not fetch {url}")


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def clean(s: str) -> str:
    return " ".join(s.split())


# --------------------------------------------------------------------------- discovery
def discover_ids(prev: dict) -> dict:
    ids = dict(DEFAULTS)
    ids.update(prev.get("ids", {}))
    try:
        s = soup(fetch("/"))
        for a in s.find_all("a", href=True):
            m = re.fullmatch(r"/team/(\d+)/(\d+)\.html", a["href"].strip())
            if m and clean(a.get_text()) == TEAM_NAME:
                if (m.group(1), m.group(2)) != (ids["season_id"], ids["team_id"]):
                    log(f"discovered new IDs season={m.group(1)} team={m.group(2)}")
                ids["season_id"], ids["team_id"] = m.group(1), m.group(2)
                break
    except Exception as e:  # noqa: BLE001
        log(f"ID discovery skipped ({e}); using stored IDs")
    return ids


# --------------------------------------------------------------------------- parsing
def parse_dt(date_s: str, time_s: str | None):
    d = dt.datetime.strptime(date_s, "%d/%m/%y").date()
    t = dt.time(15, 0)
    tbc = True
    if time_s and re.fullmatch(r"\d{1,2}:\d{2}", time_s):
        h, m = map(int, time_s.split(":"))
        t, tbc = dt.time(h, m), False
    local = dt.datetime.combine(d, t, tzinfo=UK)
    return d.isoformat(), (None if tbc else t.strftime("%H:%M")), local.isoformat()


def parse_match_hub(html: str, base: str = BASE) -> list[dict]:
    s = soup(html)
    table = s.select_one(".match-list-container table")
    if table is None:
        raise ValueError("match list table not found (page layout changed?)")
    out = []
    for tr in table.select("tr[data-match-href]"):
        tds = tr.find_all("td")
        if len(tds) < 4:
            continue
        when = clean(tds[0].get_text(" "))
        m = re.match(r"(\d{2}/\d{2}/\d{2})\s*(\d{1,2}:\d{2})?", when)
        if not m:  # TBC date
            date_iso = time_s = ko = None
        else:
            date_iso, time_s, ko = parse_dt(m.group(1), m.group(2))
        home, away = clean(tds[1].get_text(" ")), clean(tds[3].get_text(" "))
        mid = clean(tds[2].get_text(" "))
        details = clean(tds[4].get_text(" ")) if len(tds) > 4 else ""
        comp, venue = details, None
        if " @ " in details:
            comp, venue = details.split(" @ ", 1)
        comp = re.sub(r"\s*-\s*", " - ", comp).strip()
        row = {
            "date": date_iso, "time": time_s, "kickoff": ko,
            "home": home, "away": away,
            "competition": comp, "venue": venue,
            "url": base + tr["data-match-href"],
        }
        sm = re.match(r"(\d+)\s*-\s*(\d+)\s*(.*)$", mid)
        if sm:
            row["home_score"], row["away_score"] = int(sm.group(1)), int(sm.group(2))
            note = sm.group(3).strip()
            if note:
                row["note"] = note.strip("()")
        elif mid and mid.upper() != "VS":
            row["status"] = mid  # e.g. postponed / abandoned
        out.append(row)
    return out


def next_page(html: str, current: str) -> str | None:
    for a in soup(html).find_all("a", href=True):
        if clean(a.get_text()) == "Next" and a["href"].strip() != current:
            return a["href"].strip()
    return None


def fetch_hub(ids: dict, played: bool) -> list[dict]:
    path = f"/matchHub/{ids['season_id']}/-1_-1/{ids['team_id']}/-1/-1/-1/{2 if played else 1}/true.html"
    rows, seen = [], set()
    for _ in range(10):  # pagination guard
        html = fetch(path)
        rows += parse_match_hub(html)
        seen.add(path)
        nxt = next_page(html, path)
        if not nxt or nxt in seen:
            break
        path = nxt
        time.sleep(2)
    return rows


def parse_table(html: str) -> list[dict] | None:
    s = soup(html)
    for table in s.find_all("table"):
        heads = [clean(th.get_text()) for th in table.select("thead th")]
        if "PTS" not in heads or "P" not in heads:
            continue
        rows = []
        for tr in table.select("tbody tr"):
            c = [clean(td.get_text(" ")) for td in tr.find_all("td")]
            if len(c) < 10 or not c[0].isdigit():
                continue
            rows.append({"pos": int(c[0]), "team": c[1], "p": int(c[2]), "w": int(c[3]),
                         "d": int(c[4]), "l": int(c[5]), "f": int(c[6]), "a": int(c[7]),
                         "gd": int(c[8]), "pts": int(c[9])})
        return rows
    return None


def division_options(html: str) -> dict[str, str]:
    s = soup(html)
    sel = s.find("select", id=re.compile("divisionSeasonID|filterDivision", re.I))
    opts = {}
    for o in s.find_all("option"):
        t = clean(o.get_text())
        if re.search(r"(Premier|First|Second|Third|Fourth|Fifth) Division", t) and o.get("value", "").isdigit():
            opts[o["value"]] = t
    return opts


def fetch_table(ids: dict) -> dict:
    tried = set()
    order = [ids.get("division_id")]
    html = None
    while order:
        div = order.pop(0)
        if not div or div in tried:
            continue
        tried.add(div)
        html = fetch(f"/standingsForDate/{div}/1/-1/-1.html")
        rows = parse_table(html) or []
        opts = division_options(html)
        if any(r["team"] == TEAM_NAME for r in rows):
            ids["division_id"] = div
            return {"division": opts.get(div, "League"), "rows": rows,
                    "url": f"{BASE}/standingsForDate/{div}/1/-1/-1.html"}
        # not here: queue every division listed on the page (handles new season / promotion)
        order += [d for d in opts if d not in tried]
        time.sleep(2)
    raise ValueError("Eddlewood not found in any division table")


def venue_address(match_url: str) -> str | None:
    """Read the venue address block from a WoSFL match page."""
    try:
        t = soup(fetch(match_url)).get_text("\n", strip=True)
        m = re.search(r"\nAddress\n(.+?)\nSocial, News", t, re.S)
        if m:
            lines = [clean(x) for x in m.group(1).split("\n") if clean(x)]
            return ", ".join(lines[:5]) or None
    except Exception as e:  # noqa: BLE001
        log(f"venue lookup failed: {e}")
    return None


# --------------------------------------------------------------------------- main
def load_prev() -> dict:
    try:
        return json.loads(OUT.read_text())
    except Exception:  # noqa: BLE001
        return {}


def digest(d: dict) -> str:
    keep = {k: d.get(k) for k in ("results", "fixtures", "table", "venues")}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()


def main() -> int:
    prev = load_prev()
    data = dict(prev)
    ids = discover_ids(prev)
    season_changed = prev.get("ids", {}).get("season_id") not in (None, ids["season_id"])

    # Results
    try:
        res = fetch_hub(ids, played=True)
        res = [r for r in res if "home_score" in r or r.get("status")]
        if not res and prev.get("results") and not season_changed:
            raise ValueError("results list came back empty")
        data["results"] = sorted(res, key=lambda r: r["kickoff"] or "")
    except Exception as e:  # noqa: BLE001
        warn(f"results not updated, keeping last good copy: {e}")
    time.sleep(2)

    # Fixtures
    try:
        fx = fetch_hub(ids, played=False)
        data["fixtures"] = sorted(fx, key=lambda r: r["kickoff"] or "9999")
    except Exception as e:  # noqa: BLE001
        warn(f"fixtures not updated, keeping last good copy: {e}")
    time.sleep(2)

    # League table
    try:
        tbl = fetch_table(ids)
        if len(tbl["rows"]) < 4:
            raise ValueError(f"table only has {len(tbl['rows'])} rows")
        data["table"] = tbl
    except Exception as e:  # noqa: BLE001
        warn(f"table not updated, keeping last good copy: {e}")

    # Venue addresses for upcoming away grounds (cached; one lookup per new venue)
    venues = dict(prev.get("venues", {}))
    venues.setdefault(HOME_VENUE, "Eddlewood Park, Queens Drive, Hamilton, ML3 7ST")
    for f in data.get("fixtures", [])[:3]:
        v = f.get("venue")
        if v and v not in venues:
            time.sleep(2)
            addr = venue_address(f["url"])
            if addr:
                venues[v] = addr
    data["venues"] = venues
    for f in data.get("fixtures", []):
        v = f.get("venue")
        if v:
            f["venue_address"] = venues.get(v)
            f["map"] = "https://www.google.com/maps/search/?api=1&query=" + quote_plus(venues.get(v) or f"{v}, {f['home']} FC")

    if not any(k in data for k in ("results", "fixtures", "table")):
        warn("no data at all yet - nothing written")
        return 0

    now = dt.datetime.now(UK).replace(microsecond=0).isoformat()
    data["ids"] = ids
    data["team"] = TEAM_NAME
    data["source"] = {"name": "West of Scotland Football League", "url": f"{BASE}/team/{ids['season_id']}/{ids['team_id']}.html"}
    data["checked_at"] = now
    if digest(data) != digest(prev):
        data["updated_at"] = now
    data["warnings"] = warnings

    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, OUT)
    log(f"wrote {OUT.relative_to(ROOT)}: {len(data.get('results', []))} results, "
        f"{len(data.get('fixtures', []))} fixtures, table rows {len(data.get('table', {}).get('rows', []))}, "
        f"{len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001  - never fail the scheduled job
        log(f"unexpected error, existing data left untouched: {e}")
        sys.exit(0)
    finally:
        shutil.rmtree(_chrome_profile, ignore_errors=True)
