/* Eddlewood FC — renders live data:
   data/live.json  (first team, written by scripts/update_data.py)
   data/teams.json (youth teams, written by scripts/update_youth.py)
   Team list/order comes from the #teams-meta block that scripts/build_pages.py puts in every page. */
(function () {
  "use strict";
  var MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  var MONTHS_L = ["January","February","March","April","May","June","July","August","September","October","November","December"];
  var DAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
  var DAYS_L = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
  var BADGE = "assets/img/badge-256.png";
  var NOW = Date.now();

  // mobile menu
  var burger = document.querySelector(".burger");
  if (burger) burger.addEventListener("click", function () {
    var open = document.body.classList.toggle("menu-open");
    burger.setAttribute("aria-expanded", open ? "true" : "false");
  });

  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]; }); }
  function isUs(t) { return /eddlewood/i.test(t || ""); }
  function disp(t) { return String(t || "").replace(/^\d{2}s\s*-\s*/, ""); }   // "16s - Eddlewood Reds" -> "Eddlewood Reds"
  var META = (function () { try { return JSON.parse(document.getElementById("teams-meta").textContent); } catch (err) { return []; } })();
  function dateOf(m) { return m.kickoff ? new Date(m.kickoff) : (m.date ? new Date(m.date + "T12:00:00") : null); }
  function ukParts(d) {
    // Format in UK time regardless of the visitor's device timezone
    var f = new Intl.DateTimeFormat("en-GB", {timeZone: "Europe/London", weekday: "short", day: "numeric", month: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false});
    var o = {}; f.formatToParts(d).forEach(function (p) { o[p.type] = p.value; });
    return {wd: DAYS.indexOf(o.weekday), day: +o.day, mon: +o.month - 1, year: +o.year, time: o.hour + ":" + o.minute};
  }
  function longDate(m) {
    var d = dateOf(m); if (!d) return "Date TBC";
    var p = ukParts(d); return DAYS_L[p.wd] + " " + p.day + " " + MONTHS_L[p.mon] + " " + p.year;
  }
  function shortDate(m) { var d = dateOf(m); if (!d) return "TBC"; var p = ukParts(d); return DAYS[p.wd] + " " + p.day + " " + MONTHS[p.mon]; }
  function koText(m) { return m.time ? m.time.replace(/^(\d+):(\d+)$/, function (_, h, mm) { h = +h; return (h % 12 || 12) + (mm !== "00" ? "." + mm : "") + (h >= 12 ? "pm" : "am"); }) : "KO TBC"; }
  function initials(n) { return n.replace(/[^A-Za-z' ]/g, "").split(/\s+/).filter(function (w) { return w && !/^(FC|AFC|United|Utd)$/i.test(w); }).slice(0, 2).map(function (w) { return w[0]; }).join("").toUpperCase() || n[0]; }
  function crest(team) {
    return isUs(team) ? '<div class="crest"><img src="' + BADGE + '" alt="Eddlewood FC badge"></div>'
                      : '<div class="crest init" aria-hidden="true">' + esc(initials(team)) + "</div>";
  }
  function outcome(m) {
    if (m.home_score == null) return null;
    var us = isUs(m.home) ? m.home_score : m.away_score, them = isUs(m.home) ? m.away_score : m.home_score;
    if (us > them) return "W"; if (us < them) return "L";
    return "D";
  }
  function shortComp(c) { return (c || "").replace(" - ", " · "); }
  function ordinal(n) { var s = ["th","st","nd","rd"], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }
  function upcomingOnly(list) { return list.filter(function (m) { var d = dateOf(m); return !d || d.getTime() + 2.5 * 3600e3 > NOW; }); }
  function byDate(a, b) { var x = dateOf(a), y = dateOf(b); return (x ? x.getTime() : 9e15) - (y ? y.getTime() : 9e15); }
  function stampText(prefix, iso) { if (!iso) return ""; var p = ukParts(new Date(iso)); return prefix + " · checked " + p.day + " " + MONTHS[p.mon] + " " + p.year + ", " + p.time + " (UK time)"; }

  // ---- shared fixture/result rows
  function fxRow(m, played, showTeam) {
    var d = dateOf(m), p = d ? ukParts(d) : null;
    var home = isUs(m.home), o = played ? outcome(m) : null;
    var teams = played
      ? '<span class="' + (home ? "us" : "them") + '">' + esc(disp(m.home)) + '</span><span class="sc">' + m.home_score + "–" + m.away_score + '</span><span class="' + (home ? "them" : "us") + '">' + esc(disp(m.away)) + "</span>"
      : '<span class="' + (home ? "us" : "them") + '">' + esc(disp(m.home)) + '</span> <span style="color:var(--red)">v</span> <span class="' + (home ? "them" : "us") + '">' + esc(disp(m.away)) + "</span>";
    var meta = played ? (m.note ? '<span class="pens">' + esc(m.note) + "</span>" : (home ? "Home" : "Away") + (m.venue ? " · " + esc(m.venue) : ""))
                      : esc(m.time ? koText(m) : "KO TBC") + (m.venue ? " · " + esc(m.venue) : "");
    if (m.status) meta += " · " + esc(m.status);
    var tl = showTeam && m._label ? '<span class="tl">' + esc(m._label).replace(/(\d{4})s\b/, '$1<span class="lc">s</span>') + "</span>" : "";
    return '<a class="fx ' + (home ? "home" : "away") + '" href="' + esc(m.url) + '" target="_blank" rel="noopener">' +
      '<div class="date">' + (p ? "<b>" + p.day + "</b><span>" + DAYS[p.wd] + " " + MONTHS[p.mon] + "</span>" : "<b>?</b><span>TBC</span>") + "</div>" +
      '<div><div class="comp">' + tl + esc(shortComp(m.competition)) + '</div><div class="teams">' + teams + '</div><div class="meta">' + meta + "</div></div>" +
      (o ? '<span class="wdl ' + o + '">' + o + "</span>" : "") + "</a>";
  }
  function list(items, played, grouped, showTeam, emptyMsg) {
    if (!items.length) return '<div class="empty">' + esc(emptyMsg || (played ? "No results yet." : "No fixtures scheduled.")) + "</div>";
    var out = "", cur = "";
    items.forEach(function (m) {
      if (grouped) {
        var d = dateOf(m), key = d ? (function (p) { return MONTHS_L[p.mon] + " " + p.year; })(ukParts(d)) : "Date to be confirmed";
        if (key !== cur) { out += '<div class="month">' + esc(key) + "</div>"; cur = key; }
      }
      out += fxRow(m, played, showTeam);
    });
    return out;
  }
  function tableHTML(rows, opts) {
    // opts.gd: first-team table with F/A/GD; opts.mini: compact
    var mini = opts.mini, gd = opts.gd;
    var head = '<tr><th class="pos">#</th><th class="tm">Team</th><th>P</th>' + (mini ? "" : "<th>W</th><th>D</th><th>L</th>" + (gd ? '<th class="hide-sm">F</th><th class="hide-sm">A</th>' : "")) + (gd ? "<th>GD</th>" : "") + "<th>Pts</th></tr>";
    var body = rows.map(function (r) {
      return '<tr class="' + (isUs(r.team) ? "us" : "") + '"><td class="pos">' + r.pos + '</td><td class="tm">' + esc(r.team) + "</td><td>" + r.p + "</td>" +
        (mini ? "" : "<td>" + r.w + "</td><td>" + r.d + "</td><td>" + r.l + "</td>" + (gd ? '<td class="hide-sm">' + r.f + '</td><td class="hide-sm">' + r.a + "</td>" : "")) +
        (gd ? "<td>" + (r.gd > 0 ? "+" : "") + r.gd + "</td>" : "") + '<td class="pts">' + r.pts + "</td></tr>";
    }).join("");
    return '<table class="lt"><thead>' + head + "</thead><tbody>" + body + "</tbody></table>";
  }

  // ---- normalise all matches from both data files, tagged with team
  function collect(live, teams) {
    var fx = [], rs = [];
    function tag(m, slug, label, league) { var c = {}; for (var k in m) c[k] = m[k]; c._team = slug; c._label = label; c._league = league; return c; }
    if (live) {
      (live.fixtures || []).forEach(function (m) { fx.push(tag(m, "first-team", "First Team", /Division/i.test(m.competition || ""))); });
      (live.results || []).forEach(function (m) { rs.push(tag(m, "first-team", "First Team", /Division/i.test(m.competition || ""))); });
    }
    if (teams && teams.sides) META.forEach(function (t) {
      (t.sides || []).forEach(function (sd) {
        var d = teams.sides[sd.id]; if (!d) return;
        var lg = function (m) { return sd.ss || /Division|League/i.test(m.competition || ""); };
        (d.fixtures || []).forEach(function (m) { fx.push(tag(m, t.slug, sd.name, lg(m))); });
        (d.results || []).forEach(function (m) { rs.push(tag(m, t.slug, sd.name, lg(m))); });
      });
    });
    fx.sort(byDate); rs.sort(byDate);
    return {fixtures: upcomingOnly(fx), results: rs};
  }

  // ================================================================ FIRST TEAM (live.json)
  function renderFirstTeam(live) {
    var fixtures = (live.fixtures || []).slice();
    var results = (live.results || []).slice();
    var upcoming = upcomingOnly(fixtures);
    var next = upcoming.filter(function (m) { return m.kickoff; })[0] || upcoming[0];
    var last = results[results.length - 1];

    $$("[data-next]").forEach(function (el) {
      if (!next) { el.innerHTML = '<div class="card-body"><div class="empty">No fixtures scheduled — check back soon.</div></div>'; return; }
      var home = isUs(next.home);
      var cd = next.kickoff ? '<div class="countdown" data-ko="' + esc(next.kickoff) + '"><div><b data-u="d">0</b><small>Days</small></div><div><b data-u="h">00</b><small>Hrs</small></div><div><b data-u="m">00</b><small>Mins</small></div><div><b data-u="s">00</b><small>Secs</small></div></div><div class="live-flag">Match in progress</div>' : "";
      el.innerHTML =
        '<div class="card-head"><span>Next match</span><span class="tag">' + (home ? "Home" : "Away") + "</span></div>" +
        '<div class="card-body">' +
        '<div class="comp">' + esc(shortComp(next.competition)) + "</div>" +
        '<div class="versus"><div class="team">' + crest(next.home) + '<div class="nm">' + esc(next.home) + '</div></div><div class="vs">V</div><div class="team">' + crest(next.away) + '<div class="nm">' + esc(next.away) + "</div></div></div>" +
        '<div class="when"><b>' + esc(longDate(next)) + "</b><span>Kick-off " + esc(koText(next)) + "</span></div>" +
        (next.venue ? '<div class="venue-line">' + esc(next.venue) + (next.venue_address && next.venue !== "Eddlewood Park" ? " · " + esc(next.venue_address) : "") + "</div>" : "") +
        cd +
        '<div class="actions">' + (next.map ? '<a class="btn btn-red" href="' + esc(next.map) + '" target="_blank" rel="noopener">Directions</a>' : "") +
        '<a class="btn btn-ghost" href="fixtures.html?team=first-team">All fixtures</a></div></div>';
    });

    $$("[data-last]").forEach(function (el) {
      if (!last) { el.innerHTML = '<div class="card-body"><div class="empty">No results yet this season.</div></div>'; return; }
      var o = outcome(last);
      var form = results.slice(-5).map(function (m) { var r = outcome(m); return '<span class="wdl ' + r + '" title="' + esc(m.home + " " + m.home_score + "-" + m.away_score + " " + m.away) + '">' + r + "</span>"; }).join("");
      var word = {W: "Win", D: "Draw", L: "Defeat"}[o];
      el.innerHTML =
        '<div class="card-head"><span>Last result</span><span class="tag">' + esc(shortComp(last.competition)) + "</span></div>" +
        '<div class="card-body result">' +
        '<span class="result-chip ' + o + '">' + word + "</span>" +
        '<div class="versus" style="margin:4px 0 6px"><div class="team">' + crest(last.home) + '<div class="nm">' + esc(last.home) + '</div></div><div class="score">' + last.home_score + "<i>–</i>" + last.away_score + '</div><div class="team">' + crest(last.away) + '<div class="nm">' + esc(last.away) + "</div></div></div>" +
        '<div class="note">' + esc(longDate(last)) + (last.note ? " · " + esc(last.note) : "") + "</div>" +
        '<div class="form"><small>Form</small>' + form + "</div></div>";
    });

    $$("[data-table]").forEach(function (el) {
      var t = live.table; if (!t || !t.rows) return;
      el.innerHTML = tableHTML(t.rows, {gd: true, mini: el.hasAttribute("data-mini")});
      $$("[data-division]").forEach(function (d) { d.textContent = t.division || "League table"; });
    });

    $$("[data-fixtures]").forEach(function (el) {
      var n = +el.getAttribute("data-fixtures") || 0;
      var items = n ? upcoming.filter(function (m) { return m !== next; }).slice(0, n) : upcoming;
      el.innerHTML = list(items, false, !n);
    });
    $$("[data-results]").forEach(function (el) {
      var n = +el.getAttribute("data-results") || 0;
      var items = results.slice().reverse(); if (n) items = items.slice(0, n);
      el.innerHTML = list(items, true, !n);
    });

    var us = live.table && live.table.rows && live.table.rows.filter(function (r) { return isUs(r.team); })[0];
    $$("[data-stat]").forEach(function (el) {
      var k = el.getAttribute("data-stat");
      if (k === "pos" && us) el.textContent = ordinal(us.pos);
      if (k === "pts" && us) el.textContent = us.pts;
      if (k === "played") el.textContent = results.length;
      if (k === "goals") el.textContent = results.reduce(function (a, m) { return a + (isUs(m.home) ? m.home_score : m.away_score); }, 0);
    });

    $$("[data-updated]").forEach(function (el) { el.textContent = stampText("First team: data from the West of Scotland Football League", live.updated_at || live.checked_at); });
    tick();
  }

  // ================================================================ YOUTH (teams.json)
  function renderYouth(teams) {
    var S = teams.sides || {};
    function sideMatches(id, key) {
      var d = S[id]; if (!d) return [];
      return (d[key] || []).slice().sort(byDate);
    }
    // team pages
    $$("[data-yt-table]").forEach(function (el) {
      var id = el.getAttribute("data-yt-table"), t = S[id] && S[id].table;
      if (!t || !t.rows || !t.rows.length) { el.innerHTML = '<div class="empty">League table not available right now.</div>'; return; }
      el.innerHTML = tableHTML(t.rows, {});
      $$('[data-yt-division="' + id + '"]').forEach(function (d) { d.textContent = t.division || "League table"; });
    });
    $$("[data-yt-fixtures]").forEach(function (el) {
      var id = el.getAttribute("data-yt-fixtures");
      el.innerHTML = list(upcomingOnly(sideMatches(id, "fixtures")), false, false, false, "No upcoming fixtures published yet.");
    });
    $$("[data-yt-results]").forEach(function (el) {
      var id = el.getAttribute("data-yt-results");
      el.innerHTML = list(sideMatches(id, "results").reverse(), true, false, false, "No results published yet.");
    });
    $$("[data-yt-sources]").forEach(function (el) {
      var d = S[el.getAttribute("data-yt-sources")];
      if (d && d.sources && d.sources.length) el.innerHTML = d.sources.map(function (x) { return '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener">' + esc(x.name) + "</a></li>"; }).join("");
    });
    $$("[data-yt-updated]").forEach(function (el) { el.textContent = stampText("Youth: data from CLYFA and the Scottish Youth FA", teams.updated_at || teams.checked_at); });

    // home "across the club" strip (youth only)
    var all = collect(null, teams);
    $$("[data-club-results]").forEach(function (el) {
      var n = +el.getAttribute("data-club-results") || 4;
      el.innerHTML = list(all.results.slice().reverse().slice(0, n), true, false, true, "No youth results published yet.");
    });
    $$("[data-club-fixtures]").forEach(function (el) {
      var n = +el.getAttribute("data-club-fixtures") || 4;
      el.innerHTML = list(all.fixtures.slice(0, n), false, false, true, "No youth fixtures published yet.");
    });
  }

  // ---- Teams index snippets
  function renderSnips(live, teams) {
    var S = (teams && teams.sides) || {};
    function nextLine(f) { return f ? "Next: " + shortDate(f) + " v " + disp(isUs(f.home) ? f.away : f.home) : ""; }
    function lastLine(r) {
      if (!r) return ""; var h = isUs(r.home);
      return "Last: " + {W: "Won", D: "Drew", L: "Lost"}[outcome(r)] + " " + (h ? r.home_score : r.away_score) + "–" + (h ? r.away_score : r.home_score) + " v " + disp(h ? r.away : r.home);
    }
    $$("[data-team-snip]").forEach(function (el) {
      var slug = el.getAttribute("data-team-snip"), lines = [];
      if (slug === "first-team") {
        if (!live) return;
        var row = live.table && (live.table.rows || []).filter(function (r) { return isUs(r.team); })[0];
        if (row) lines.push(ordinal(row.pos) + " in " + (live.table.division || "the league") + " · " + row.pts + " pts");
        lines.push(nextLine(upcomingOnly(live.fixtures || [])[0]));
        var rs = live.results || []; lines.push(lastLine(rs[rs.length - 1]));
      } else {
        var t = META.filter(function (x) { return x.slug === slug; })[0];
        if (!t || !t.sides.length) return;
        t.sides.forEach(function (sd) {
          var d = S[sd.id]; if (!d) return;
          var pre = t.sides.length > 1 ? sd.name + ": " : "";
          var row = d.table && (d.table.rows || []).filter(function (r) { return isUs(r.team); })[0];
          var bits = [];
          if (row) bits.push(ordinal(row.pos) + " of " + d.table.rows.length + " in " + (d.table.division || "league"));
          var nx = upcomingOnly((d.fixtures || []).slice().sort(byDate))[0];
          if (nx) bits.push(nextLine(nx));
          else { var r = (d.results || []).slice().sort(byDate).pop(); if (r) bits.push(lastLine(r)); }
          if (bits.length) lines.push(pre + bits.join(" · "));
        });
      }
      lines = lines.filter(Boolean);
      el.innerHTML = lines.length ? lines.map(function (l) { return "<span>" + esc(l) + "</span>"; }).join("") : "Fixtures will appear here when published.";
    });
  }

  // ================================================================ FIXTURES PAGE (all teams + filter)
  function renderAll(live, teams) {
    var fEl = $("[data-all-fixtures]"), rEl = $("[data-all-results]");
    if (!fEl && !rEl) return;
    var all = collect(live, teams);
    var sel = $("#team-filter");
    var q = (location.search.match(/[?&]team=([^&]+)/) || [])[1];
    if (sel && q && $('option[value="' + decodeURIComponent(q).replace(/"/g, "") + '"]', sel)) sel.value = decodeURIComponent(q);
    var chip = "all";
    function draw() {
      var team = sel ? sel.value : "first-team";
      var ok = function (m) {
        if (team !== "all" && m._team !== team) return false;
        if (chip === "league") return m._league; if (chip === "cup") return !m._league;
        if (chip === "home") return isUs(m.home); if (chip === "away") return !isUs(m.home);
        return true;
      };
      var meta = META.filter(function (t) { return t.slug === team; })[0];
      var ssOnly = meta && meta.sides.length && meta.sides.every(function (s) { return s.ss; });
      if (fEl) fEl.innerHTML = list(all.fixtures.filter(ok), false, true, team === "all" || (meta && meta.sides.length > 1), "No upcoming fixtures for this selection.");
      if (rEl) rEl.innerHTML = list(all.results.filter(ok).reverse(), true, true, team === "all" || (meta && meta.sides.length > 1),
        ssOnly ? "CLYFA's small-sided site doesn't publish scores for this age group, so there are no results to show." : "No results for this selection yet.");
    }
    if (sel) sel.onchange = function () {
      draw();
      if (history.replaceState) history.replaceState(null, "", "?team=" + sel.value + location.hash);
    };
    $$(".filters").forEach(function (f) {
      $$("button", f).forEach(function (b) {
        b.onclick = function () {
          $$("button", f).forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); });
          chip = b.getAttribute("data-f"); draw();
        };
      });
    });
    draw();
  }

  // ---- tabs
  $$(".tabs").forEach(function (tabs) {
    $$("button", tabs).forEach(function (b) {
      b.onclick = function () {
        $$("button", tabs).forEach(function (x) { x.setAttribute("aria-selected", x === b ? "true" : "false"); $("#" + x.getAttribute("aria-controls")).hidden = x !== b; });
        if (history.replaceState) history.replaceState(null, "", location.search + "#" + b.getAttribute("aria-controls"));
      };
    });
    var h = location.hash.slice(1); var hb = h && $('[aria-controls="' + h + '"]', tabs); if (hb) hb.onclick();
  });

  // ---- countdown
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function tick() {
    $$(".countdown[data-ko]").forEach(function (cd) {
      var diff = new Date(cd.getAttribute("data-ko")).getTime() - Date.now();
      var flag = cd.nextElementSibling;
      if (diff <= 0) { cd.style.display = "none"; if (flag) flag.style.display = "block"; return; }
      var s = Math.floor(diff / 1000);
      cd.querySelector('[data-u="d"]').textContent = Math.floor(s / 86400);
      cd.querySelector('[data-u="h"]').textContent = pad(Math.floor(s % 86400 / 3600));
      cd.querySelector('[data-u="m"]').textContent = pad(Math.floor(s % 3600 / 60));
      cd.querySelector('[data-u="s"]').textContent = pad(s % 60);
    });
  }
  setInterval(tick, 1000);

  // ================================================================ load
  function getJSON(u) { return fetch(u, {cache: "no-cache"}).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).catch(function () { return null; }); }
  var FT_SEL = "[data-next],[data-last],[data-table],[data-fixtures],[data-results],[data-stat]";
  var needLive = $(FT_SEL + ",[data-all-fixtures],[data-team-snip]");
  var needTeams = $("[data-yt-table],[data-yt-fixtures],[data-club-results],[data-club-fixtures],[data-all-fixtures],[data-team-snip],[data-yt-updated]");
  Promise.all([needLive ? getJSON("data/live.json") : null, needTeams ? getJSON("data/teams.json") : null]).then(function (r) {
    var live = r[0], teams = r[1];
    if (live) renderFirstTeam(live);
    else if (needLive) $$(FT_SEL.replace(",[data-stat]", "")).forEach(function (el) {
      el.innerHTML = '<div class="card-body"><div class="empty">Live data is unavailable right now. See <a href="https://www.wosfl.co.uk/page/eddlewood.html">the WoSFL website</a>.</div></div>';
    });
    if (teams) renderYouth(teams);
    else $$("[data-yt-table],[data-yt-fixtures],[data-yt-results],[data-club-results],[data-club-fixtures]").forEach(function (el) {
      el.innerHTML = '<div class="empty">Youth data is unavailable right now.</div>';
    });
    renderSnips(live, teams);
    renderAll(live, teams);
  });
})();
