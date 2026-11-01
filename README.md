# Eddlewood FC website

Static, mobile-first club website. Fixtures, results, league table, next match and countdown update automatically
from the West of Scotland Football League via `scripts/update_data.py`. Youth fixtures, results and tables come from
CLYFA and the Scottish Youth FA via `scripts/update_youth.py`. GitHub Actions runs both on a schedule.

* `data/live.json` – generated first-team data (do not edit by hand)
* `data/teams.json` – generated youth data (do not edit by hand)
* `data/teams-config.json` – the club's teams in display order, and where each one's data comes from (CLYFA table feed,
  small-sided team pages). Edit this when a team is added or changes league, then run `python scripts/build_pages.py`.
* `data/club.json` – squad, staff, sponsors, admission, contacts → `python scripts/build_pages.py` rebuilds the HTML
* `assets/` – CSS, JS, badge, sponsor logos and club photos
* Local preview: `python -m http.server` then open http://localhost:8000

See **HOSTING.md** for the setup steps.
