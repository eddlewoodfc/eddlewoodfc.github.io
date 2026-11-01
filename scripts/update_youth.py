#!/usr/bin/env python3
"""
Eddlewood FC website - youth team live data updater.

Reads data/teams-config.json and writes data/teams.json, which the website
renders from. Sources (all public, no login):

  * CLYFA 11-a-side league tables  - https://www.clyfa.teamexpert.co.uk  (from COMET)
    (CLYFA publishes tables only on this site, no fixture/result lists)
  * SYFA Scottish Cup fixtures/results - https://scottishyouthfa.co.uk/competitions/
  * CLYFA small-sided fixtures     - https://clyfa.leaguerepublic.com
    (scores are not published for small-sided games, so fixtures only)

Fail-safe, like update_data.py: every section of every team is validated
separately and the last good copy is kept if a fetch/parse fails; the file is
written atomically; the script always exits 0. Problems go to "warnings".

Season roll-over: CLYFA tables are re-found by scanning the league-table index
for the team name, the SYFA cup season is read from the competitions index, and
small-sided team IDs are re-discovered from the Match Hub team list.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import update_data as ud  # noqa: E402  (reuses fetch(), Chrome fallback, match-hub parser)

ROOT = ud.ROOT
CONFIG = ROOT / "data" / "teams-config.json"
OUT = ROOT / "data" / "teams.json"
UK = ud.UK

CLYFA = "https://www.clyfa.teamexpert.co.uk"
CLYFA_INDEX = CLYFA + "/menu/league-tables-4"
SYFA = "https://scottishyouthfa.co.uk"
SS = "https://clyfa.leaguerepublic.com"
SS_SEASON = "463404811"  # "Season 2026" - re-discovered automatically if it changes

warnings: list[str] = []
log = ud.log


def warn(msg: str) -> None:
    warnings.append(msg)
    log("WARNING: " + msg)


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())


COLOURS = ("red", "black", "white", "blue", "yellow", "gold", "green")


def is_side(name: str, side: dict) -> bool:
    """True if a team name in a source is this Eddlewood side."""
    n = norm(name)
    if "eddlewood" not in n:
        return False
    year = side["year"].lower()
    if year not in n.replace(" ", "") and year not in n:
        return False
    words = n.split()
    has = lambda c: any(w.startswith(c) for w in words)  # noqa: E731  (red/reds, black/blacks)
    if side.get("variant"):
        return has(side["variant"])
    return not any(has(c) for c in COLOURS)


def today_uk() -> dt.date:
    return dt.datetime.now(UK).date()


# --------------------------------------------------------------------- CLYFA 11s tables
def parse_clyfa_table(html: str) -> tuple[str | None, list[dict], str | None]:
    s = ud.soup(html)
    m = re.search(r"(\d{4})/(\d{4}) - ([^|\n]+?)\s*(?:\||\n|$)", s.get_text("\n"))
    division = ud.clean(m.group(3)) if m else None
    season = f"{m.group(1)}/{m.group(2)[2:]}" if m else None
    t = s.select_one("table.LeagueTable")
    rows = []
    if t is not None:
        for tr in t.select("tbody tr"):
            th = tr.find("th")
            c = [ud.clean(td.get_text(" ")) for td in tr.find_all("td")]
            if th is None or len(c) < 6 or not ud.clean(th.get_text()).isdigit():
                continue
            rows.append({"pos": int(ud.clean(th.get_text())), "team": c[0], "p": int(c[1]), "w": int(c[2]),
                         "d": int(c[3]), "l": int(c[4]), "pts": int(c[5])})
    return division, rows, season


_clyfa_names: dict[str, str] | None = None


def clyfa_index() -> dict[str, str]:
    """feed id -> division name as listed on the CLYFA league-tables menu, e.g. '2011s (C) Division'."""
    global _clyfa_names
    if _clyfa_names is None:
        _clyfa_names = {}
        try:
            for a in ud.soup(ud.fetch(CLYFA_INDEX)).find_all("a", href=True):
                m = re.search(r"leaguetablefeed/(\d+)", a["href"])
                if m and ud.clean(a.get_text()):
                    _clyfa_names.setdefault(m.group(1), ud.clean(a.get_text()))
        except Exception as e:  # noqa: BLE001
            log(f"CLYFA index unavailable: {e}")
    return _clyfa_names


def clyfa_feeds_for(year: str) -> list[str]:
    return [f for f, name in clyfa_index().items() if year in name]


def clyfa_table(side: dict, ids: dict) -> dict:
    cfg = side["clyfa_table"]
    tried, order = set(), [ids.get("clyfa_feed") or str(cfg["feed"])]
    discovered = False
    while order:
        feed = order.pop(0)
        if feed in tried:
            continue
        tried.add(feed)
        url = f"{CLYFA}/leaguetablefeed/{feed}"
        division, rows, season = parse_clyfa_table(ud.fetch(url))
        if any(is_side(r["team"], side) for r in rows):
            if len(rows) < 3:
                raise ValueError(f"table only has {len(rows)} rows")
            ids["clyfa_feed"] = feed
            name = clyfa_index().get(feed)
            return {"division": f"CLYFA {name}" if name else (division or "CLYFA league"), "season": season, "rows": rows, "url": url,
                    "source": "Central Lanarkshire Youth Football Association (CLYFA)"}
        if not discovered:
            discovered = True
            order += [f for f in clyfa_feeds_for(side["year"]) if f not in tried]
        time.sleep(1)
    raise ValueError("team not found in any CLYFA table")


# --------------------------------------------------------------------- SYFA Scottish Cup
_syfa_index: str | None = None


def syfa_cup_url(year: str) -> str:
    global _syfa_index
    if _syfa_index is None:
        try:
            _syfa_index = ud.fetch(SYFA + "/competitions/")
        except Exception as e:  # noqa: BLE001
            log(f"SYFA index unavailable ({e}); guessing season")
            _syfa_index = ""
    seasons = re.findall(rf"/competitions/scottish-cup-{year}s/(\d{{4}}-\d{{4}})/", _syfa_index)
    if seasons:
        season = max(seasons)
    else:
        t = today_uk()
        y = t.year if t.month >= 7 else t.year - 1
        season = f"{y}-{y + 1}"
    return f"{SYFA}/competitions/scottish-cup-{year}s/{season}/"


def parse_syfa(html: str, url: str, side: dict) -> tuple[list[dict], list[dict], bool]:
    s = ud.soup(html)
    panels = {p.get("id", "").rsplit("-", 1)[-1]: p for p in s.select(".syfa-comp__panel")}
    if not {"fixtures", "results"} <= set(panels):
        raise ValueError("SYFA fixtures/results panels not found (page layout changed?)")
    out = {"fixtures": [], "results": []}
    total = 0
    for kind, panel in panels.items():
        if kind not in out:
            continue
        for day in panel.select("section.syfa-comp__day"):
            h = day.select_one(".syfa-comp__day-heading")
            try:
                d = dt.datetime.strptime(ud.clean(h.get_text()), "%A %d %B %Y").date()
            except Exception:  # noqa: BLE001
                d = None
            for li in day.select("li.syfa-match"):
                total += 1
                home = li.select_one(".syfa-match__team--home")
                away = li.select_one(".syfa-match__team--away")
                if not home or not away:
                    continue
                home, away = ud.clean(home.get_text()), ud.clean(away.get_text())
                if not (is_side(home, side) or is_side(away, side)):
                    continue
                chip = li.select_one(".syfa-match__chip")
                venue = li.select_one(".syfa-match__venue")
                row = {"date": d.isoformat() if d else None, "time": None, "kickoff": None,
                       "home": home, "away": away, "competition": "SYFA Scottish Cup",
                       "venue": ud.clean(venue.get_text()) if venue else None, "url": url}
                if chip is not None and "syfa-match__chip--result" in chip.get("class", []):
                    nums = [ud.clean(x.get_text()) for x in chip.find_all("span", recursive=False)]
                    nums = [x for x in nums if x.isdigit()]
                    if len(nums) < 2:
                        continue
                    row["home_score"], row["away_score"] = int(nums[0]), int(nums[1])
                else:
                    tm = ud.clean(chip.get_text()) if chip else ""
                    if d:
                        if re.fullmatch(r"\d{1,2}:\d{2}", tm):
                            row["time"] = tm
                            h_, m_ = map(int, tm.split(":"))
                            row["kickoff"] = dt.datetime.combine(d, dt.time(h_, m_), tzinfo=UK).isoformat()
                if d:
                    row["kickoff"] = row["kickoff"] or dt.datetime.combine(d, dt.time(12, 0), tzinfo=UK).isoformat()
                out[kind].append(row)
    return out["fixtures"], out["results"], total > 0


# --------------------------------------------------------------------- CLYFA small-sided
def ss_discover(side: dict, ids: dict) -> None:
    """Find the current season/team ID for a small-sided side from the Match Hub filters."""
    html = ud.fetch(f"{SS}/matchHub/{ids.get('ss_season', SS_SEASON)}/-1_-1/-1/-1/-1/-1/1/true.html")
    s = ud.soup(html)
    sel = s.find("select", id=re.compile("filterOuterSeasonID"))
    if sel:
        opts = [o.get("value") for o in sel.find_all("option") if (o.get("value") or "").isdigit()]
        cur = sel.find("option", selected=True)
        new = (cur.get("value") if cur else None) or (opts[0] if opts else None)
        if new and new != ids.get("ss_season", SS_SEASON):
            ids["ss_season"] = new
            html = ud.fetch(f"{SS}/matchHub/{new}/-1_-1/-1/-1/-1/-1/1/true.html")
            s = ud.soup(html)
    tsel = s.find("select", id=re.compile("filterTeamID"))
    for o in (tsel.find_all("option") if tsel else []):
        name = re.sub(r"\s*\[\d+\]$", "", ud.clean(o.get_text()))
        if is_side(name, side) and name.lower().startswith(side["year"].lower()):
            ids["ss_team"] = o["value"]
            return
    raise ValueError("team not found in the small-sided Match Hub team list")


def ss_fixtures(side: dict, ids: dict) -> list[dict]:
    ids.setdefault("ss_team", side["clyfa_ss"]["team_id"])
    ids.setdefault("ss_season", SS_SEASON)

    def get():
        url = f"/matchHub/{ids['ss_season']}/-1_-1/{ids['ss_team']}/-1/-1/-1/1/true.html"
        rows, seen, path = [], set(), url
        for _ in range(6):
            html = ud.fetch(SS + path)
            rows += ud.parse_match_hub(html, base=SS)
            seen.add(path)
            nxt = ud.next_page(html, path)
            if not nxt or nxt in seen:
                break
            path = nxt
            time.sleep(2)
        return rows

    rows = get()
    if not any(is_side(r["home"], side) or is_side(r["away"], side) for r in rows):
        log(f"{side['id']}: stored small-sided IDs gave no matches, re-discovering")
        ss_discover(side, ids)
        rows = get()
    rows = [r for r in rows if is_side(r["home"], side) or is_side(r["away"], side)]
    today = today_uk().isoformat()
    out = []
    for r in rows:
        if r.get("time") == "00:00":  # LeagueRepublic shows 00:00 when the time is not set
            r["time"] = None
            r["kickoff"] = dt.datetime.fromisoformat(r["kickoff"]).replace(hour=12, minute=0).isoformat()
        for k in ("home_score", "away_score", "note", "status"):
            r.pop(k, None)
        if r.get("date") and r["date"] < today:
            continue  # past dates: scores are not published for small-sided games
        out.append(r)
    return sorted(out, key=lambda r: r.get("kickoff") or "9999")


# --------------------------------------------------------------------- main
def load(p: Path) -> dict:
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return {}


def digest(d: dict) -> str:
    keep = {k: {kk: v.get(kk) for kk in ("table", "fixtures", "results")} for k, v in d.get("sides", {}).items()}
    return hashlib.sha256(json.dumps(keep, sort_keys=True).encode()).hexdigest()


def main() -> int:
    cfg = load(CONFIG)
    prev = load(OUT)
    data = {"sides": {}}
    for team in cfg.get("teams", []):
        for side in team.get("sides", []):
            sid = side["id"]
            old = prev.get("sides", {}).get(sid, {})
            cur = {"team": team["slug"], "label": side["label"], "ids": dict(old.get("ids", {})), "sources": []}
            for k in ("table", "fixtures", "results"):
                if k in old:
                    cur[k] = old[k]
            fixtures, results, fx_ok = [], [], False

            if side.get("clyfa_table"):
                try:
                    cur["table"] = clyfa_table(side, cur["ids"])
                    cur["sources"].append({"name": "CLYFA league table", "url": cur["table"]["url"]})
                except Exception as e:  # noqa: BLE001
                    warn(f"{sid}: CLYFA table not updated, keeping last good copy: {e}")
                    if cur.get("table"):
                        cur["sources"].append({"name": "CLYFA league table", "url": cur["table"]["url"]})
                time.sleep(1)

            if side.get("syfa_cup"):
                url = syfa_cup_url(re.sub(r"\D", "", side["year"]))
                try:
                    f, r, ok = parse_syfa(ud.fetch(url), url, side)
                    if not ok:
                        raise ValueError("cup page has no matches at all")
                    fixtures += f
                    results += r
                    fx_ok = True
                except Exception as e:  # noqa: BLE001
                    warn(f"{sid}: SYFA cup not updated, keeping last good copy: {e}")
                    fixtures += [m for m in old.get("fixtures", []) if m.get("competition") == "SYFA Scottish Cup"]
                    results += [m for m in old.get("results", []) if m.get("competition") == "SYFA Scottish Cup"]
                cur["sources"].append({"name": "SYFA Scottish Cup", "url": url})
                time.sleep(1)

            if side.get("clyfa_ss"):
                try:
                    fixtures += ss_fixtures(side, cur["ids"])
                    fx_ok = True
                except Exception as e:  # noqa: BLE001
                    warn(f"{sid}: small-sided fixtures not updated, keeping last good copy: {e}")
                    fixtures += [m for m in old.get("fixtures", []) if m.get("competition") != "SYFA Scottish Cup"]
                cur["sources"].append({"name": "CLYFA small-sided fixtures",
                                       "url": f"{SS}/team/{cur['ids'].get('ss_season', SS_SEASON)}/{cur['ids'].get('ss_team', side['clyfa_ss']['team_id'])}.html"})
                cur["scores_published"] = False

            if side.get("syfa_cup") or side.get("clyfa_ss"):
                cur["fixtures"] = sorted(fixtures, key=lambda m: m.get("kickoff") or "9999")
                cur["results"] = sorted(results, key=lambda m: m.get("kickoff") or "")
            data["sides"][sid] = cur
            log(f"{sid}: table {len(cur.get('table', {}).get('rows', []))} rows, "
                f"{len(cur.get('fixtures', []))} fixtures, {len(cur.get('results', []))} results")

    now = dt.datetime.now(UK).replace(microsecond=0).isoformat()
    data["checked_at"] = now
    data["updated_at"] = now if digest(data) != digest(prev) else prev.get("updated_at", now)
    data["warnings"] = warnings
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    os.replace(tmp, OUT)
    log(f"wrote {OUT.relative_to(ROOT)}: {len(data['sides'])} teams, {len(warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001  - never fail the scheduled job
        log(f"unexpected error, existing youth data left untouched: {e}")
        sys.exit(0)
    finally:
        import shutil
        shutil.rmtree(ud._chrome_profile, ignore_errors=True)
