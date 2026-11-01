#!/usr/bin/env python3
"""Builds the static HTML pages from data/club.json (squad, staff, sponsors, contacts)
and data/team_sponsors.json (youth and girls team sponsors).
Run this only when club details change; live match data is loaded by assets/js/site.js."""
import html
import re
import json
from pathlib import Path
from urllib.parse import quote

e = html.escape
ROOT = Path(__file__).resolve().parent.parent
C = json.loads((ROOT / "data" / "club.json").read_text())
TEAMS = json.loads((ROOT / "data" / "teams-config.json").read_text())["teams"]
try:
    LIVE_TEAMS = json.loads((ROOT / "data" / "teams.json").read_text()).get("sides", {})
except Exception:  # noqa: BLE001
    LIVE_TEAMS = {}
try:
    TEAM_SPONSORS = json.loads((ROOT / "data" / "team_sponsors.json").read_text())
except Exception:  # noqa: BLE001
    TEAM_SPONSORS = {}
EMAIL = C["contact"]["email"]


def tt(title):
    """Escape a team title, keeping the plural 's' of '2010s' lower-case inside upper-case headings."""
    return re.sub(r"(\d{4})s\b", r'\1<span class="lc">s</span>', e(title))


def team_page(t):
    return t.get("page") or f"team-{t['slug']}.html"


def side_sources(side):
    """Source links for a side: from the last data update if available, else from the config."""
    live = LIVE_TEAMS.get(side["id"], {}).get("sources")
    if live:
        return live
    out = []
    if side.get("clyfa_table"):
        out.append({"name": "CLYFA league table", "url": f"https://www.clyfa.teamexpert.co.uk/leaguetablefeed/{side['clyfa_table']['feed']}"})
    if side.get("syfa_cup"):
        out.append({"name": "SYFA Scottish Cup", "url": "https://scottishyouthfa.co.uk/competitions/"})
    if side.get("clyfa_ss"):
        out.append({"name": "CLYFA small-sided fixtures", "url": f"https://clyfa.leaguerepublic.com/team/463404811/{side['clyfa_ss']['team_id']}.html"})
    return out


TEAMS_META = json.dumps([{"slug": t["slug"], "title": t["title"], "page": team_page(t),
                          "sides": [{"id": sd["id"], "name": sd.get("name", t["title"]), "ss": bool(sd.get("clyfa_ss"))} for sd in t.get("sides", [])]}
                         for t in TEAMS], separators=(",", ":")).replace("</", "<\\/")
youth = [t for t in TEAMS if t["group"] != "senior"]
team_opts = "".join(f'<option value="{t["slug"]}"{" selected" if t["slug"] == "first-team" else ""}>{e(t["title"])}</option>'
                    for t in TEAMS if t["group"] == "senior" or t.get("sides"))

ICON = {
 "Facebook": '<svg viewBox="0 0 24 24"><path d="M13.5 21v-7.5h2.6l.4-3h-3V8.6c0-.9.3-1.5 1.6-1.5h1.6V4.4c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 4v2.2H7.9v3h2.6V21h3z"/></svg>',
 "Instagram": '<svg viewBox="0 0 24 24"><path d="M12 7.3A4.7 4.7 0 1 0 12 16.7 4.7 4.7 0 0 0 12 7.3zm0 7.7a3 3 0 1 1 0-6 3 3 0 0 1 0 6zm6-7.9a1.1 1.1 0 1 1-2.2 0 1.1 1.1 0 0 1 2.2 0zM12 4.6c2.4 0 2.7 0 3.6.1 2.4.1 3.6 1.3 3.7 3.7.1.9.1 1.2.1 3.6s0 2.7-.1 3.6c-.1 2.4-1.3 3.6-3.7 3.7-.9.1-1.2.1-3.6.1s-2.7 0-3.6-.1c-2.4-.1-3.6-1.3-3.7-3.7-.1-.9-.1-1.2-.1-3.6s0-2.7.1-3.6C4.8 6 6 4.8 8.4 4.7c.9-.1 1.2-.1 3.6-.1zM12 3c-2.4 0-2.8 0-3.7.1C5 3.2 3.2 5 3.1 8.3 3 9.2 3 9.6 3 12s0 2.8.1 3.7c.1 3.3 1.9 5.1 5.2 5.2.9.1 1.3.1 3.7.1s2.8 0 3.7-.1c3.3-.1 5.1-1.9 5.2-5.2.1-.9.1-1.3.1-3.7s0-2.8-.1-3.7C20.8 5 19 3.2 15.7 3.1 14.8 3 14.4 3 12 3z"/></svg>',
 "X": '<svg viewBox="0 0 24 24"><path d="M17.8 3h3.1l-6.8 7.8 8 10.2h-6.3l-4.9-6.4L5.3 21H2.2l7.3-8.3L1.8 3h6.4l4.4 5.9L17.8 3zm-1.1 16.2h1.7L7.4 4.7H5.6l11.1 14.5z"/></svg>',
 "mail": '<svg viewBox="0 0 24 24"><path d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm1 2.2V17h16V7.2l-8 5.6-8-5.6zM5.6 7l6.4 4.5L18.4 7H5.6z"/></svg>',
 "pin": '<svg viewBox="0 0 24 24"><path d="M12 2a7 7 0 0 1 7 7c0 5.2-7 13-7 13S5 14.2 5 9a7 7 0 0 1 7-7zm0 4.5a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5z"/></svg>',
 "user": '<svg viewBox="0 0 24 24"><path d="M12 12a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9zm0 2c-4.4 0-8 2.2-8 5v2h16v-2c0-2.8-3.6-5-8-5z"/></svg>',
}
SILHOUETTE = '<svg viewBox="0 0 200 220" aria-hidden="true"><path d="M100 18c22 0 38 17 38 40s-16 44-38 44-38-21-38-44 16-40 38-40zM22 220c2-46 30-80 78-80s76 34 78 80z"/></svg>'

NAV = [("index.html", "Home"), ("teams.html", "Teams"), ("fixtures.html", "Fixtures &amp; Results"),
       ("sponsors.html", "Sponsors"), ("visit.html", "Matchday"), ("contact.html", "Contact")]


def nav_key(fname):
    if fname in ("teams.html", "table.html", "squad.html", "first-team.html") or fname.startswith("team-"):
        return "teams.html"
    return fname


def social_links(cls=""):
    return "".join(f'<a href="{s["url"]}" target="_blank" rel="noopener" aria-label="{s["name"]}: {e(s["label"])}" class="{cls}">{ICON[s["name"]]}{"<span>" + e(s["label"]) + "</span>" if cls else ""}</a>' for s in C["social"])


def page(fname, title, body, desc, hero_img=None):
    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == nav_key(fname) else ""}>{t}</a>' for h, t in NAV)
    full_title = f"{title} | Eddlewood FC" if fname != "index.html" else "Eddlewood FC | Our Town. Our Club."
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{full_title}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#0a0a0b">
<meta property="og:title" content="{full_title}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:image" content="assets/img/{hero_img or 'badge-512.png'}">
<link rel="icon" href="assets/img/favicon.png">
<link rel="apple-touch-icon" href="assets/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
<div class="topbar"><div class="wrap"><div class="tb-left"><span>{e(C['league'])}</span><span>{e(C['division'])} · {e(C['season'])}</span></div><div class="social">{social_links()}</div></div></div>
<header class="site"><div class="wrap">
 <a class="brand" href="index.html"><img src="assets/img/badge-256.png" alt="Eddlewood FC badge" width="58" height="57"><div><b>Eddlewood FC</b><small>Hamilton · Lanarkshire</small></div></a>
 <nav class="main" aria-label="Main">{nav}</nav>
 <button class="burger" aria-label="Menu" aria-expanded="false"><span></span><span></span><span></span></button>
</div><nav class="mobile-nav" aria-label="Mobile">{nav}</nav></header>
<main>
{body}
</main>
{footer()}
<script type="application/json" id="teams-meta">{TEAMS_META}</script>
<script src="assets/js/site.js" defer></script>
</body>
</html>
"""


def footer():
    return f"""<footer class="site"><div class="wrap">
<div class="f-grid">
 <div><div class="f-brand"><img src="assets/img/badge-256.png" alt="Eddlewood FC badge"><div><b>Eddlewood<br>Football Club</b><em>{e(C['tagline'])}</em></div></div>
 <p style="margin-top:16px;max-width:360px">{e(C['ground']['name'])}, {e(C['ground']['address'])}</p></div>
 <div><h4>Teams</h4><ul>{''.join(f'<li><a href="{team_page(t)}">{e(t["title"])}</a></li>' for t in TEAMS)}</ul></div>
 <div><h4>Club</h4><ul><li><a href="fixtures.html">Fixtures &amp; results</a></li><li><a href="table.html">League table</a></li><li><a href="squad.html">First-team squad</a></li><li><a href="sponsors.html">Sponsors</a></li><li><a href="visit.html">Matchday</a></li><li><a href="contact.html">Contact</a></li></ul></div>
 <div><h4>Follow</h4><ul>{''.join(f'<li><a href="{s["url"]}" target="_blank" rel="noopener">{s["name"]} · {e(s["label"])}</a></li>' for s in C['social'])}</ul></div>
</div>
<div class="f-legal"><span>{e(C['charity'])}</span><span>Fixtures, results and tables update automatically from the West of Scotland Football League, CLYFA and Scottish Youth FA websites.</span><span>© <span id="yr">2026</span> Eddlewood FC</span></div>
</div></footer>"""


def sponsor_tile(s):
    cls = "sp" + (" dark" if s["tile"] == "dark" else "") + (" cap" if s.get("caption") else "")
    if s.get("logo"):
        inner = f'<img src="{s["logo"]}" alt="{e(s["name"])}" loading="lazy">' + (f'<span>{e(s["name"])}</span>' if s.get("caption") else "")
    else:
        inner = f'<span class="txt">{e(s["name"])}</span>'
    return f'<div class="{cls}" title="{e(s["name"])}">{inner}</div>'


def sponsor_display_name(t):
    """Name used for a team that has no separate sides. Girls are the 2016/17 side."""
    if t["slug"] == "girls":
        return "Girls 2016/17"
    return t["title"]


def youth_sponsor_units(t):
    """One entry per youth/girls side, using the names those teams already use."""
    if t.get("sides"):
        return [{"id": sd["id"], "name": sd["name"], "page": team_page(t)} for sd in t["sides"]]
    return [{"id": t["slug"], "name": sponsor_display_name(t), "page": team_page(t)}]


def team_sponsor_items(team_id):
    out = []
    for s in TEAM_SPONSORS.get(team_id) or []:
        if not isinstance(s, dict):
            continue
        name, logo = (s.get("name") or "").strip(), (s.get("logo") or "").strip()
        if name or logo:
            out.append({"name": name, "logo": logo, "tile": s.get("tile") or "light"})
    return out


def sponsor_mailto(team_name):
    return f"mailto:{EMAIL}?subject={quote(f'Sponsoring the {team_name} team')}"


def sponsor_placeholder(team_name, show_name=False):
    who = f'<p>{e(team_name)}</p>' if show_name else ""
    return f'<div class="info-card"><h3>Sponsor this team</h3>{who}<a class="btn btn-red" href="{sponsor_mailto(team_name)}">Get in touch</a></div>'


SPONSOR_CTA = f"""<div class="cta-band"><div><h3>Partner with Eddlewood</h3><p>Interested in sponsoring Eddlewood FC? Get in touch with the club to find out about sponsorship opportunities.</p></div>
<a class="btn btn-dark" href="mailto:{C['contact']['email']}?subject=Sponsorship%20enquiry">Enquire now</a></div>"""

# ----------------------------------------------------------------- HOME
home = f"""
<section class="hero" style="padding:0">
 <div class="hero-bg" style="background-image:url('assets/img/photos/dressing_room.jpg')" role="img" aria-label="Eddlewood FC home strips hanging in the dressing room"></div>
 <div class="wrap">
  <img class="hero-badge" src="assets/img/badge-256.png" alt="Eddlewood FC badge">
  <div class="eyebrow" style="color:#fff;opacity:.85">Eddlewood Football Club · Hamilton</div>
  <h1>Our Town.<br><em>Our Club.</em></h1>
  <p class="lead">{e(C['league'])} · {e(C['division'])}. Home games at {e(C['ground']['name'])}, {e(C['ground']['address'])}.</p>
  <div class="ctas"><a class="btn btn-red" href="fixtures.html">Fixtures &amp; results</a><a class="btn btn-ghost" href="teams.html">Our teams</a></div>
  <div class="hero-meta"><div>League position<b data-stat="pos">–</b></div><div>Points<b data-stat="pts">–</b></div><div>Matches (all comps)<b data-stat="played">–</b></div><div>Goals (all comps)<b data-stat="goals">–</b></div></div>
 </div>
</section>

<div class="match-centre"><div class="wrap"><div class="mc-grid">
 <div class="card card-dark next" data-next><div class="card-body"><div class="empty" style="color:#999;border-color:#333">Loading next match…</div></div></div>
 <div class="card" data-last><div class="card-body"><div class="empty">Loading last result…</div></div></div>
 <div class="card mini"><div class="card-head"><span data-division>League table</span><a class="tag" href="table.html" style="text-decoration:none">Full table →</a></div><div style="padding:6px 12px 4px" data-table data-mini></div></div>
</div></div></div>

<section class="bg-grey"><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Coming up</div><h2>Fixtures</h2></div><a class="more" href="fixtures.html">All fixtures</a></div>
 <div class="two-col">
  <div class="fx-mini" data-fixtures="4"></div>
  <div><div class="sec-head" style="margin:22px 0 12px"><h2 style="font-size:28px">Recent results</h2><a class="more" href="fixtures.html#results">All</a></div><div class="fx-mini" data-results="3"></div></div>
 </div>
 <p class="updated" data-updated></p>
</div></section>

<section class="club-strip"><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Across the club</div><h2>Youth &amp; girls</h2></div><a class="more" href="teams.html">All teams</a></div>
 <div class="team-pills">{''.join(f'<a href="{team_page(t)}">{tt(t["title"])}</a>' for t in youth)}</div>
 <div class="two-col even">
  <div><h3 class="sub">Latest youth results</h3><div class="fx-mini" data-club-results="4"><div class="empty">Loading…</div></div></div>
  <div><h3 class="sub">Youth fixtures</h3><div class="fx-mini" data-club-fixtures="4"><div class="empty">Loading…</div></div></div>
 </div>
 <p class="updated" data-yt-updated></p>
</div></section>

<section class="matchday" style="padding:0">
 <div class="hero-bg" style="background-image:url('assets/img/photos/walkout_mascots.jpg');background-position:center 30%"></div>
 <div class="wrap">
  <div><div class="eyebrow" style="color:#ff98a6">Matchday at {e(C['ground']['name'])}</div><h2>Be there<br>on matchday</h2>
   <p>{e(C['ground']['name'])}, {e(C['ground']['address'])}.</p>
   <div class="ctas" style="display:flex;gap:10px;flex-wrap:wrap;margin-top:18px"><a class="btn btn-red" href="{C['ground']['map']}" target="_blank" rel="noopener">Get directions</a><a class="btn btn-ghost" href="visit.html">Matchday info</a></div></div>
  <div class="prices">{''.join(f'<div class="price"><b>{e(a[1])}</b><span>{e(a[0])}</span>{"<small>" + e(a[2]) + "</small>" if len(a) > 2 else ""}</div>' for a in C['admission'])}</div>
 </div>
</section>

<section><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Club news</div><h2>Latest news</h2></div></div>
 <div class="news-grid" data-news>
  <div class="news-empty"><div><h3>News from the club</h3><p>Match reports, signings and club announcements will appear here. Until then, follow the club for the latest.</p></div>
  <div class="soc-row">{social_links("soc")}</div></div>
 </div>
</div></section>

<section class="bg-grey"><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Thank you</div><h2>First team sponsors</h2></div><a class="more" href="sponsors.html">All sponsors</a></div>
 <div class="spons-strip">{''.join(sponsor_tile(s) for s in C['sponsors'] if s.get('logo'))[:100000]}</div>
</div></section>
"""

# ----------------------------------------------------------------- FIXTURES
fixtures = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/stadium_session.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">Season {e(C['season'])}</div><h1>Fixtures &amp; Results</h1><p>Every Eddlewood match this season, first team and youth, league and cup. Updated automatically.</p></div></section>
<section><div class="wrap">
 <div class="team-filter"><label for="team-filter">Team</label><select id="team-filter"><option value="all">All teams</option>{team_opts}</select></div>
 <div class="tabs" role="tablist"><button role="tab" aria-selected="true" aria-controls="fixtures">Fixtures</button><button role="tab" aria-selected="false" aria-controls="results">Results</button></div>
 <div class="filters"><button data-f="all" aria-pressed="true">All</button><button data-f="league" aria-pressed="false">League</button><button data-f="cup" aria-pressed="false">Cups</button><button data-f="home" aria-pressed="false">Home</button><button data-f="away" aria-pressed="false">Away</button></div>
 <div id="fixtures" role="tabpanel" data-all-fixtures><div class="empty">Loading fixtures…</div></div>
 <div id="results" role="tabpanel" hidden data-all-results><div class="empty">Loading results…</div></div>
 <p class="updated" data-updated></p>
 <p class="updated" data-yt-updated></p>
</div></section>
"""

# ----------------------------------------------------------------- TABLE
table = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/warmup_wide.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">{e(C['league'])}</div><h1>League Table</h1><p><span data-division>{e(C['division'])}</span> · {e(C['season'])}</p></div></section>
<section><div class="wrap">
 <div class="two-col">
  <div class="card"><div class="card-head"><span data-division>{e(C['division'])}</span><span class="tag">{e(C['season'])}</span></div><div style="padding:6px 12px" data-table></div><div class="table-foot"><span data-updated></span><a href="https://www.wosfl.co.uk/page/eddlewood.html" target="_blank" rel="noopener">Source: WoSFL</a></div></div>
  <div style="display:grid;gap:16px">
   <div class="card card-dark next" data-next></div>
  </div>
 </div>
</div></section>
"""

# ----------------------------------------------------------------- SQUAD
def surname_key(p):
    parts = p["name"].split()
    return (0 if p.get("role") == "Goalkeeper" else 1, parts[-1], parts[0])


def player_card(p):
    first, last = p["name"].split(" ", 1)
    role = p.get("role")
    tag = f'<span class="role{" gk" if role == "Goalkeeper" else ""}">{e(role)}</span>' if role else ""
    sp = f'<div class="psp">Sponsored by {e(p["sponsor"])}</div>' if p.get("sponsor") else ""
    return f"""<article class="pl"><div class="ph">{SILHOUETTE}<span class="soon">Photo coming soon</span><img class="wm" src="assets/img/badge-256.png" alt=""></div><div class="info"><div class="fn">{e(first)}</div><div class="ln">{e(last)}</div>{tag}{sp}</div></article>"""


def initials(n):
    return "".join(w[0] for w in n.split()[:2])


squad = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/night_session.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">First team · {e(C['season'])}</div><h1>Squad</h1><p>The Eddlewood FC first-team squad and backroom staff. <a href="first-team.html" style="color:#fff">First team home →</a></p></div></section>
<section><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">First team</div><h2>Players</h2></div></div>
 <div class="squad-grid">{''.join(player_card(p) for p in sorted(C['squad'], key=surname_key))}</div>
 <p class="note-box" style="margin-top:22px">Player photos are coming soon. Images shown are placeholders.</p>
</div></section>
<section class="bg-grey"><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Behind the scenes</div><h2>Backroom staff</h2></div></div>
 <div class="staff">{''.join(f'<div class="st"><div class="av">{e(initials(n))}</div><div><b>{e(n)}</b><span>{e(r)}</span></div></div>' for n, r in C['staff'])}</div>
</div></section>
"""

# ----------------------------------------------------------------- SPONSORS
player_sp = sorted([p for p in C["squad"] if p.get("sponsor")], key=lambda p: p["name"].split()[-1])
def youth_sponsor_card(unit):
    names = [s["name"] for s in team_sponsor_items(unit["id"]) if s.get("name")]
    detail = ", ".join(e(n) for n in names) if names else "Sponsor wanted — get in touch"
    return f'<a class="link-card" href="{unit["page"]}"><b>{tt(unit["name"])}</b><span>{detail}</span></a>'


youth_units = [u for t in TEAMS if t["group"] != "senior" for u in youth_sponsor_units(t)]
sponsors = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/walkout_mascots.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">Thank you</div><h1>Our Sponsors</h1><p>The local businesses who back Eddlewood FC and its teams. Please support them as they support us.</p></div></section>
<section><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">First team</div><h2>First team sponsors</h2></div></div>
 <div class="spons-strip spons-big">{''.join(sponsor_tile(s) for s in C['sponsors'])}</div>
</div></section>
<section class="bg-grey"><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">2026/27</div><h2>Player sponsors</h2></div></div>
 <div class="ps-list">{''.join(f'<div class="ps"><b>{e(p["name"])}</b><span>{e(p["sponsor"])}</span></div>' for p in player_sp)}</div>
</div></section>
<section><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Sponsor wanted</div><h2>Youth &amp; girls' team sponsors</h2></div></div>
 <div class="link-grid">{''.join(youth_sponsor_card(u) for u in youth_units)}</div>
</div></section>
<section><div class="wrap">{SPONSOR_CTA}</div></section>
"""

# ----------------------------------------------------------------- VISIT
g = C["ground"]
visit = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/walkout_mascots.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">Visit us</div><h1>Matchday</h1><p>Everything you need for a matchday at {e(g['name'])}.</p></div></section>
<section><div class="wrap">
 <div class="info-grid">
  <div class="info-card"><h3>Getting here</h3><p class="big">{e(g['name'])}</p><p>{e(g['address'])}</p><p><a class="btn btn-red" href="{g['map']}" target="_blank" rel="noopener">{ICON['pin'].replace('<svg', '<svg fill="#fff"')} Open in Maps</a></p></div>
  <div class="info-card"><h3>Admission</h3>
   <table class="lt" style="margin-top:4px"><tbody>{''.join(f'<tr><td class="tm">{e(a[0])}{"<br><small style=color:var(--mute)>" + e(a[2]) + "</small>" if len(a) > 2 else ""}</td><td class="pts" style="text-align:right;font-size:20px">{e(a[1])}</td></tr>' for a in C['admission'])}</tbody></table>
  </div>
 </div>
 <div style="margin-top:16px"><iframe class="map-frame" title="Map of {e(g['name'])}" loading="lazy" src="https://www.google.com/maps?q=Eddlewood+Park,+Queens+Drive,+Hamilton+ML3+7ST&output=embed"></iframe></div>
</div></section>
<section class="bg-grey"><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Next up</div><h2>Next match</h2></div><a class="more" href="fixtures.html">All fixtures</a></div>
 <div style="max-width:560px"><div class="card card-dark next" data-next></div></div>
</div></section>
"""

# ----------------------------------------------------------------- CONTACT
contact = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/dressing_room.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">Get in touch</div><h1>Contact</h1><p>For club, sponsorship and matchday enquiries.</p></div></section>
<section><div class="wrap"><div class="info-grid">
 <div class="info-card"><h3>Club secretary</h3>
  <div class="contact-row"><div class="ic">{ICON['user']}</div><div><small>Secretary</small><b>{e(C['contact']['secretary'])}</b></div></div>
  <a class="contact-row" href="mailto:{C['contact']['email']}"><div class="ic">{ICON['mail']}</div><div><small>Email</small><b>{e(C['contact']['email'])}</b></div></a>
  <a class="contact-row" href="{g['map']}" target="_blank" rel="noopener"><div class="ic">{ICON['pin']}</div><div><small>Ground</small><b>{e(g['name'])}, {e(g['address'])}</b></div></a>
 </div>
 <div class="info-card"><h3>Follow the club</h3>
  {''.join(f'<a class="contact-row" href="{s["url"]}" target="_blank" rel="noopener"><div class="ic">{ICON[s["name"]]}</div><div><small>{s["name"]}</small><b>{e(s["label"])}</b></div></a>' for s in C['social'])}
 </div>
</div>
<div style="margin-top:28px">{SPONSOR_CTA}</div>
<p class="note-box" style="margin-top:22px">{e(C['charity'])}</p>
</div></section>
"""

# ----------------------------------------------------------------- TEAMS
JOIN = f"""<div class="cta-band"><div><h3>Want to play for Eddlewood?</h3><p>New players are welcome. Email the club and we will put you in touch with the right coach.</p></div>
<a class="btn btn-dark" href="mailto:{EMAIL}?subject=Joining%20Eddlewood%20FC">Email the club</a></div>"""


def team_card(t):
    fmt = f'<span class="tc-fmt">{e(t["format"])}</span>' if t.get("format") else ""
    if t["group"] == "senior":
        fmt = '<span class="tc-fmt">11-a-side</span>'
    return f"""<a class="team-card{' senior' if t['group'] == 'senior' else ''}" href="{team_page(t)}">
 <div class="tc-top"><div class="eyebrow">{e(t['eyebrow'])}</div>{fmt}</div>
 <h3>{tt(t['title'])}</h3>
 <div class="tc-snip" data-team-snip="{t['slug']}">{'' if t.get('sides') or t['group'] == 'senior' else 'No league fixtures published online. Get in touch to join.'}</div>
 <span class="tc-go">View team →</span></a>"""


senior = [t for t in TEAMS if t["group"] == "senior"]
youth_t = [t for t in TEAMS if t["group"] == "youth"]
girls_t = [t for t in TEAMS if t["group"] == "girls"]
teams_index = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/dressing_room.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">Season {e(C['season'])}</div><h1>Our Teams</h1><p>From the first team to our youngest players. Fixtures, results and tables update automatically where a league publishes them.</p></div></section>
<section><div class="wrap">
 <div class="sec-head"><div><div class="eyebrow">Senior</div><h2>First team</h2></div></div>
 <div class="team-grid">{''.join(team_card(t) for t in senior)}</div>
 <div class="sec-head" style="margin-top:40px"><div><div class="eyebrow">Youth · oldest to youngest</div><h2>Youth teams</h2></div></div>
 <div class="team-grid">{''.join(team_card(t) for t in youth_t)}</div>
 <div class="sec-head" style="margin-top:40px"><div><div class="eyebrow">Girls</div><h2>Girls</h2></div></div>
 <div class="team-grid">{''.join(team_card(t) for t in girls_t)}</div>
 <p class="updated" data-yt-updated></p>
</div></section>
<section class="bg-grey"><div class="wrap">{JOIN}</div></section>
"""


def facebook_follow(t):
    """Prominent follow button when a team has its own Facebook page in the config."""
    fb = t.get("facebook") or {}
    if isinstance(fb, str):
        fb = {"url": fb}
    url = str(fb.get("url") or "").strip()
    if not url:
        return ""
    name = str(fb.get("name") or "").strip()
    label = f"Follow the {t['title']} on Facebook"
    aria = f"{label} ({name})" if name else label
    icon = ICON["Facebook"].replace("<svg", '<svg fill="#fff"', 1)
    caption = f'<p>{e(name)}</p>' if name else ""
    return (f'<div style="margin-top:18px"><a class="btn btn-red" href="{e(url)}" target="_blank" rel="noopener" '
            f'aria-label="{e(aria)}" title="{e(name or label)}">{icon}Follow the {tt(t["title"])} on Facebook</a></div>{caption}')


first_team = f"""
<section class="page-hero" style="padding:0"><div class="hero-bg" style="background-image:url('assets/img/photos/warmup_wide.jpg')"></div><div class="wrap"><div class="eyebrow" style="color:#ff98a6">Senior men · {e(C['season'])}</div><h1>First Team</h1><p>{e(senior[0]['summary'])}</p>{facebook_follow(senior[0])}</div></section>
<section class="bg-grey"><div class="wrap">
 <div class="mc-grid">
  <div class="card card-dark next" data-next><div class="card-body"><div class="empty" style="color:#999;border-color:#333">Loading next match…</div></div></div>
  <div class="card" data-last><div class="card-body"><div class="empty">Loading last result…</div></div></div>
  <div class="card mini"><div class="card-head"><span data-division>League table</span><a class="tag" href="table.html" style="text-decoration:none">Full table →</a></div><div style="padding:6px 12px 4px" data-table data-mini></div></div>
 </div>
 <p class="updated" data-updated></p>
</div></section>
<section><div class="wrap">
 <div class="link-grid">
  <a class="link-card" href="fixtures.html?team=first-team"><b>Fixtures &amp; results</b><span>League and cup, all season</span></a>
  <a class="link-card" href="table.html"><b>League table</b><span>{e(C['league'])} · {e(C['division'])}</span></a>
  <a class="link-card" href="squad.html"><b>Squad &amp; staff</b><span>Players and backroom team</span></a>
  <a class="link-card" href="visit.html"><b>Matchday</b><span>{e(C['ground']['name'])}, admission and directions</span></a>
 </div>
</div></section>
"""


def side_block(t, sd):
    ss = bool(sd.get("clyfa_ss"))
    srcs = "".join(f'<li><a href="{e(x["url"])}" target="_blank" rel="noopener">{e(x["name"])}</a></li>' for x in side_sources(sd))
    multi = len(t["sides"]) > 1
    head = f'<div class="sec-head"><div><div class="eyebrow">{e(t["format"] or "")}</div><h2>{tt(sd["name"])}</h2></div></div>' if multi else ""
    table = "" if ss else f"""<div class="card"><div class="card-head"><span data-yt-division="{sd['id']}">League table</span><span class="tag">{e(C['season'])}</span></div><div style="padding:6px 12px" data-yt-table="{sd['id']}"><div class="empty">Loading table…</div></div></div>"""
    ssnote = ""
    return f"""<div class="side-block">{head}
 <div class="two-col">
  <div>
   <h3 class="sub">Fixtures</h3><div class="fx-mini" data-yt-fixtures="{sd['id']}"><div class="empty">Loading fixtures…</div></div>
   {'' if ss else f'<h3 class="sub" style="margin-top:26px">Results</h3><div class="fx-mini" data-yt-results="{sd["id"]}"><div class="empty">Loading results…</div></div>'}
   {ssnote}
  </div>
  <div style="display:grid;gap:16px;align-content:start">{table}
   <div class="info-card src-card"><h3>Sources</h3><ul class="src" data-yt-sources="{sd['id']}">{srcs}</ul></div>
  </div>
 </div></div>"""


def team_sponsors_section(t):
    units = youth_sponsor_units(t)
    filled = [(u, team_sponsor_items(u["id"])) for u in units]
    filled = [(u, items) for u, items in filled if items]
    empty = [u for u in units if not team_sponsor_items(u["id"])]
    blocks = []
    for u, items in filled:
        head = f'<h3 class="sub">{tt(u["name"])}</h3>' if len(units) > 1 else ""
        blocks.append(f'<div>{head}<div class="spons-strip">{"".join(sponsor_tile(s) for s in items)}</div></div>')
    if empty and not filled:
        blocks.append(sponsor_placeholder(sponsor_display_name(t)))
    else:
        for u in empty:
            blocks.append(sponsor_placeholder(u["name"], show_name=len(units) > 1))
    if filled:
        inner = f'<div style="display:grid;gap:16px">{"".join(blocks)}</div>' if len(blocks) > 1 else "".join(blocks)
    else:
        inner = f'<div class="link-grid">{"".join(blocks)}</div>'
    return f"""<div style="margin-top:28px">
 <div class="sec-head"><div><div class="eyebrow">Sponsor wanted</div><h2>Team sponsors</h2></div></div>
 {inner}
</div>"""


def youth_page(t):
    sides = t.get("sides", [])
    if sides:
        body = "".join(side_block(t, sd) for sd in sides)
        if all(sd.get("clyfa_ss") for sd in sides):
            body += '<p class="note-box" style="margin-top:22px">CLYFA\'s small-sided fixtures site does not list scores for these games, so only upcoming fixtures are shown here.</p>'
        intro = ""
    else:
        body = f"""<div class="empty-team"><h3>Fixtures coming soon</h3><p>We have not found a league that publishes fixtures or results for this team online yet. For match and training details, contact the club.</p>
<a class="btn btn-red" href="mailto:{EMAIL}?subject={e(t['title'])}%20enquiry">Email the club</a></div>"""
        intro = ""
    return f"""
<section class="page-hero" style="padding:0"><div class="wrap"><div class="eyebrow" style="color:#ff98a6">{e(t['eyebrow'])}</div><h1>{tt(t['title'])}</h1><p>{e(t.get('format') or 'Eddlewood FC')}{' · ' + str(len(sides)) + ' teams' if len(sides) > 1 else ''} · Season {e(C['season'])}</p>{facebook_follow(t)}</div></section>
<section><div class="wrap">{intro}{body}
 {'<p class="updated" data-yt-updated></p>' if sides else ''}
</div></section>
<section class="bg-grey"><div class="wrap">
 <div class="info-grid">
  <div class="info-card"><h3>Coaches</h3><p>Coach details coming soon.</p></div>
  <div class="info-card"><h3>Training</h3><p>Training details coming soon.</p></div>
 </div>
 {team_sponsors_section(t)}
 <div style="margin-top:22px">{JOIN}</div>
 <p style="margin-top:18px"><a class="more-link" href="teams.html">← All teams</a></p>
</div></section>
"""


pages = [
 ("index.html", "Home", home, "Eddlewood FC – community football club in Hamilton, playing in the West of Scotland Football League. Fixtures, results, table and matchday info.", "photos/dressing_room.jpg"),
 ("fixtures.html", "Fixtures & Results", fixtures, "Eddlewood FC fixtures and results, updated automatically.", None),
 ("table.html", "League Table", table, "West of Scotland Football League Fourth Division table.", None),
 ("squad.html", "Squad", squad, "Eddlewood FC first-team squad and backroom staff.", None),
 ("sponsors.html", "Sponsors", sponsors, "The sponsors who support Eddlewood FC and its teams.", None),
 ("visit.html", "Matchday", visit, "Visiting Eddlewood Park: address, directions and admission prices.", None),
 ("contact.html", "Contact", contact, "Contact Eddlewood FC.", None),
 ("teams.html", "Teams", teams_index, "Eddlewood FC teams: first team, youth teams and girls.", None),
 ("first-team.html", "First Team", first_team, "Eddlewood FC first team: West of Scotland Football League Fourth Division.", None),
] + [(team_page(t), t["title"], youth_page(t), f"Eddlewood FC {t['title']}: fixtures, results and how to join.", None) for t in TEAMS if t["group"] != "senior"]
for fname, title, body, desc, img in pages:
    (ROOT / fname).write_text(page(fname, e(title), body, desc, img))
    print("wrote", fname)
