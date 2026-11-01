# Hosting the Eddlewood FC website (free, self-updating)

**Recommendation:** GitHub Pages (free hosting with HTTPS) plus a scheduled GitHub Actions job that refreshes
the fixtures, results and league table from the WoSFL website. Nobody at the club has to do anything week to week.

## How it updates itself
* `.github/workflows/update.yml` runs `scripts/update_data.py` (first team) and `scripts/update_youth.py` (youth teams) on a schedule:
  * Saturdays: every 30 minutes, 12:00–23:30 UTC (so results show within about 30 minutes of full time)
  * Weekday evenings: hourly, 18:00–23:00 UTC
  * Youth match mornings: every 30 minutes 09:00–11:30 UTC on Saturdays, and hourly on Sundays 09:45–19:45 UTC
  * Any other time: every 3 hours
  * You can also start it by hand: GitHub → Actions → "Update fixtures, results & tables (all teams)" → *Run workflow*.
* The script reads the West of Scotland Football League (LeagueRepublic) pages for Eddlewood: played matches,
  upcoming fixtures (league and cups), the division table and venue addresses. It writes them to `data/live.json`.
  The pages read that file in the visitor's browser, so the countdown, next match, last result and table all update together.
* `update_youth.py` reads the Central League Youth FA (CLYFA) league tables, CLYFA's small-sided fixtures site and the
  Scottish Youth FA Scottish Cup pages for each team listed in `data/teams-config.json`, and writes `data/teams.json`.
  CLYFA does not publish 11-a-side fixtures or results online, so youth results currently come from the Scottish Cup only.
  CLYFA's small-sided site lists fixtures but not scores.
  Teams with no online source (currently 2020s and Girls) show a "contact the club" panel instead.
* If a youth team moves to a different CLYFA division, the script searches the other CLYFA tables for that birth year
  and finds it. A brand-new team, or a small-sided team page that changes, needs an entry in `data/teams-config.json`, then `python scripts/build_pages.py`.
* It finds the current first-team season and division itself, so a new season or a promotion needs no changes.
* If the WoSFL, CLYFA or SYFA site is down or blocks a request, the previous good data is kept. The site never goes blank.
* A commit is only made when the data changes. A small "keep-alive" commit is also made if there has been no
  commit for 25 days, because GitHub pauses scheduled jobs after 60 days of inactivity.

## One-off setup (about 20 minutes)
1. Create a free GitHub account for the club (e.g. using info@eddlewoodfc.co.uk), and a **public** repository, e.g. `eddlewoodfc/website`.
2. Upload the contents of this `website/` folder to the repository root (the `screenshots/` and `tools/` folders aren't needed).
3. Repository → **Settings → Actions → General → Workflow permissions** → choose *Read and write permissions* → Save.
4. Repository → **Settings → Pages** → Source: *Deploy from a branch* → Branch `main`, folder `/ (root)` → Save.
   The site appears at `https://<account>.github.io/<repo>/` within a minute or two.
5. **Actions** tab → enable workflows if prompted → run "Update fixtures, results & tables (all teams)" once to check it works (green tick).
6. Custom domain: Settings → Pages → Custom domain → `www.eddlewoodfc.co.uk` → Save (the `CNAME` file already contains it).
7. DNS at IONOS (the domain's DNS is hosted at IONOS — **do not move the nameservers**). In IONOS → Domains → eddlewoodfc.co.uk → DNS:
   * Change the **www** record to a **CNAME** pointing to `<account>.github.io` (this replaces the current www A record 212.227.172.252).
   * Optional, so the bare domain works too: replace the **@ (apex) A** record (currently 217.160.0.203) with four A records:
     `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
     (Some IONOS packages lock the apex A record to their web-forwarding; if so, set IONOS forwarding of `eddlewoodfc.co.uk` → `https://www.eddlewoodfc.co.uk` instead.)
   * **Leave these untouched, or club email will stop working:** the MX records (`mx00.ionos.co.uk`, `mx01.ionos.co.uk`),
     the SPF TXT record (`v=spf1 include:_spf-eu.ionos.com ~all`), any DKIM/DMARC records, and the `autodiscover` CNAME.
8. Once DNS has updated (usually under an hour, up to 24h), go to Settings → Pages and tick **Enforce HTTPS**.

## Changing club details later
Squad, staff, sponsors, prices and contacts live in `data/club.json`. Edit it, then run `python scripts/build_pages.py`
(or ask whoever maintains the site) and commit the regenerated `.html` files. Match data never needs editing.

## Alternatives
* **Cloudflare Pages / Netlify**: also free, and both can deploy straight from the same GitHub repository. The GitHub Action
  still does the data updates. Only worth it if you want their extras; GitHub Pages is the simplest.
