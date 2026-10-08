"""Report section for Stage 0, "Data used": what the analysis table holds, box-score coverage by tour,
level and year, the cleaning log in plain words, and the known holes.

Every number comes from stage0_summary.json and stage0_checks.json (render_report.py assembles the page).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": 0, "id": "data-used", "title": "Data used"}

ROWS = [  # (level, qualifying, label, evaluated)
    ("GS", False, "Grand Slams", True), ("GS", True, "Grand Slam qualifying", True),
    ("FIN", False, "Tour Finals", True),
    ("T1000", False, "1000s", True), ("T1000", True, "1000 qualifying", True),
    ("T500", False, "500s", True), ("T500", True, "500 qualifying", True),
    ("T250", False, "250s", True), ("T250", True, "250 qualifying", True),
    ("CH", False, "Challenger / WTA 125", True), ("CH", True, "Challenger / 125 qualifying", True),
    ("TEAM", False, "Team events", False), ("ITF", False, "ITF", False), ("ITF", True, "ITF qualifying", False),
]
LEVEL_WORDS = {"GS": "Grand Slams", "FIN": "Tour Finals", "T1000": "1000s", "T500": "500s", "T250": "250s",
               "CH": "Challenger / WTA 125", "TEAM": "team events", "ITF": "ITF"}
TOUR_LEVEL_WORDS = {("atp", "CH"): "Challengers", ("wta", "CH"): "125s"}
TOUR = {"atp": "ATP", "wta": "WTA"}
BINS = [(0, 5), (5, 25), (25, 50), (50, 75), (75, 90), (90, 97), (97, 100.01)]

ACTION_WORDS = {
    "drop_row": "match removed", "relabel": "corrected", "fill": "filled in", "flag": "kept, flagged",
    "flag_missing": "marked missing", "flag_partial": "kept in part", "drop_box": "box score dropped",
    "drop_svgms": "service games dropped", "drop_score": "score counts dropped",
}
GROUPS = [  # (title, rule ids or id prefixes, first match wins)
    ("Merging the two sources and removing repeats", ("D1", "D2", "D3", "D4", "C01", "C02", "C03", "C04", "C62")),
    ("Who won, identities, dates and levels", ("D5", "L", "C05", "F1", "C60", "C61")),
    ("Results and scores", ("C1",)),
    ("Box scores", ("C2", "C3")),
    ("Formats and missing values", ("C4", "C5")),
]


def esc(x) -> str:
    return html.escape(str(x))


def n(x) -> str:
    return f"{int(round(x)):,}"


def pct(x, d=1) -> str:
    return f"{x:.{d}f}%"


def spans(years: list) -> str:
    """[2015, 2016, 2017, 2019] -> '2015–2017 and 2019'."""
    out, run = [], []
    for y in years:
        if run and y != run[-1] + 1:
            out.append(run)
            run = []
        run.append(y)
    if run:
        out.append(run)
    words = [str(r[0]) if len(r) == 1 else f"{r[0]}–{r[-1]}" for r in out]
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1] if words else "no season"


def load(study_dir: Path, name: str) -> dict:
    return json.loads((study_dir / name).read_text(encoding="utf-8"))


def pair_tile(label, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(label)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div>'
            f'<div><small>WTA</small><div class="value">{wta}</div></div></div>'
            f'<div class="note">{note}</div></div>')


def render(study_dir: Path) -> dict:
    s = load(study_dir, "stage0_summary.json")
    ch = load(study_dir, "stage0_checks.json")
    t, merge, holes = s["tables"], s["merge"], s["holes"]
    levels = {(r["tour"], r["level"], r["qualifying"]): r for r in t["levels"]}
    cov = s["coverage"]
    src = {(r["tour"], r["source"], r["period"]): r["matches"] for r in t["sources"]}
    ev, box, head = t["evaluation_by_tour"], t["evaluation_box_pct_by_tour"], t["evaluation_headline_by_tour"]
    parts = []

    # ------------------------------------------------------------------ intro and tiles
    parts.append(f'''    <div class="prose">
      <p>Stage 0 builds the table every later stage reads. It holds every singles match that Jeff Sackmann's files
      and Tennis My Life list at any level, from the week of {esc(t["first_week"])} (the first week of the 2010 season)
      to the week of {esc(t["last_week"])}: {n(t["matches"])} matches, one row each, and two rows per match for its players
      ({n(t["player_rows"])} rows). {n(t["players_by_tour"]["atp"])} men and {n(t["players_by_tour"]["wta"])} women play in them.
      Later stages score predictions only on <b>evaluation matches</b>, a subset set by the Brief; everything else is history
      that ratings and averages learn from.</p>
    </div>
    <div class="tiles" role="list">
      <div class="tile" role="listitem"><div class="label">Matches in the table</div><div class="value">{n(t["matches"])}</div>
        <div class="note">ATP {n(t["matches_by_tour"]["atp"])} · WTA {n(t["matches_by_tour"]["wta"])}; singles, every level, 2010 to September 2026</div></div>
      {pair_tile("Evaluation matches, 2013–2026", n(ev["atp"]), n(ev["wta"]), "tour events, their qualifying, and Challenger / WTA 125")}
      {pair_tile("Evaluation matches, 2022–2026", n(head["atp"]), n(head["wta"]), "the headline window")}
      {pair_tile("Evaluation matches with a box score", pct(box["atp"]), pct(box["wta"]), "the nine serve and return counts, after the checks below")}
    </div>''')

    # ------------------------------------------------------------------ A. what the table holds
    rows_html = []
    for level, qual, label, evaluated in ROWS:
        a, w = levels.get(("atp", level, qual)), levels.get(("wta", level, qual))
        if not a and not w:
            continue
        tag = "" if evaluated else '<span class="tag">history only</span>'

        def cells(r):
            if not r:
                return '<td class="r">–</td><td class="r">–</td><td class="r">–</td>'
            return (f'<td class="r">{n(r["matches"])}</td><td class="r">{n(r["evaluation"])}</td>'
                    f'<td class="r">{pct(r["box_pct"])}</td>')
        rows_html.append(f"<tr><td>{esc(label)}{tag}</td>{cells(a)}{cells(w)}</tr>")
    link_totals = {}
    for r in merge["tml_rows_by_link"]:
        for k, v in r.items():
            if k not in ("tour", "group", "period"):
                link_totals[(r["tour"], k)] = link_totals.get((r["tour"], k), 0) + v
    tml_rows = {tour: sum(v for (tt, _), v in link_totals.items() if tt == tour) for tour in ("atp", "wta")}
    linked = {tour: tml_rows[tour] - link_totals.get((tour, "unlinked"), 0) for tour in ("atp", "wta")}
    parts.append(f'''    <div class="sub">
      <h3>What the table holds</h3>
      <div class="prose">
        <p><span class="kind">Observed</span>Two tables. <code>stage0_matches</code> has one row per match: its level, round, surface,
        indoor or outdoor where known, best of three or five sets, tournament and date, status, score, length in minutes,
        which source it came from, and a place in one chronological order. <code>stage0_match_players</code> has one row per player per
        match: side A or B, won or lost, ranking, ranking points, seed, entry route, age, height, hand, country, the nine
        box-score counts, and each rate below stored as its numerator and denominator. A match's <b>side A</b> is set by a hash of
        its id, never by who won, their ranking or their name, so side A won {pct(t["side_a_won_pct"])} of all matches.</p>
        <p><span class="kind">Observed</span>Sources. Jeff Sackmann's files are the base: {n(src.get(("atp", "sackmann", "before 2026-05-25"), 0) + src.get(("atp", "sackmann", "2026-05-25 on"), 0))} ATP and
        {n(src.get(("wta", "sackmann", "before 2026-05-25"), 0) + src.get(("wta", "sackmann", "2026-05-25 on"), 0))} WTA matches. Tennis My Life (TML), a site that rebuilds the same
        format from official results, adds the matches Sackmann lacks: {n(src.get(("atp", "tml", "2026-05-25 on"), 0))} ATP and
        {n(src.get(("wta", "tml", "2026-05-25 on"), 0))} WTA matches from the weeks after Sackmann's files stop (25 May 2026 for the main tours,
        1–2 June for the lower levels), and {n(src.get(("atp", "tml", "before 2026-05-25"), 0))} ATP and {n(src.get(("wta", "tml", "before 2026-05-25"), 0))} older ones. Of TML's
        {n(tml_rows["atp"] + tml_rows["wta"])} rows, {n(linked["atp"] + linked["wta"])} were matched to a Sackmann match first, by the two players' names,
        then by one player in the same tournament and round, then by player ids. A match is listed once.</p>
      </div>
      <dl class="terms">
        <dt>Level</dt><dd>How big the event is. Grand Slams (the four majors), the Tour Finals (season finales), then the 1000s,
        500s and 250s of the ATP and WTA tours (the number is the ranking points the winner gets), then the Challenger /
        WTA 125 tier below them, then the ITF tier at the bottom. Team events are the Davis Cup, Billie Jean King Cup, ATP Cup,
        United Cup, Laver Cup and the Olympics.</dd>
        <dt>Qualifying</dt><dd>A small knockout event just before the main draw; its winners take the last places in the main draw.</dd>
        <dt>Round</dt><dd>Q1–Q3 are qualifying rounds; R128 to F are the main draw (round of 128 down to the final). RR is a round robin,
        where each player of a group meets the others.</dd>
        <dt>Box score</dt><dd>Nine counts per player per match: aces, double faults, points served, first serves in, points won on the
        first serve, points won on the second serve, service games, and break points saved and faced (a break point is a point
        that would win the game for the receiver).</dd>
        <dt>Retirement, walkover</dt><dd>A player who stops during a match has retired; the opponent advances and is recorded as the
        winner. A walkover is a withdrawal before the match starts: no point is played.</dd>
        <dt>Tiebreak</dt><dd>A set that reaches 6-6 is decided by a first-to-7-points tiebreak. A match tiebreak (first to 10 points)
        replaces the deciding set in some formats.</dd>
        <dt>Date</dt><dd>Every date is the Monday of the event's week, not the day the match was played. A week's events are therefore
        simultaneous in the order; rounds give the order within an event.</dd>
      </dl>
      <div class="panel">
        <div class="panel-head"><h3>Matches by level</h3><p>All years 2010–2026; evaluation matches are 2013–2026, completed or retired</p></div>
        <div class="table-wrap"><table class="wide">
          <thead><tr><th>Level</th><th class="r">ATP matches</th><th class="r">ATP evaluation</th><th class="r">ATP with box score</th>
          <th class="r">WTA matches</th><th class="r">WTA evaluation</th><th class="r">WTA with box score</th></tr></thead>
          <tbody>{"".join(rows_html)}</tbody></table></div>
      </div>
    </div>''')

    # ------------------------------------------------------------------ B. box-score coverage
    wta_pre = [r for r in cov if r["tour"] == "wta" and not r["qualifying"] and r["level"] in ("T1000", "T500", "T250")
               and 2010 <= r["year"] <= 2015]
    wta_post = [r for r in cov if r["tour"] == "wta" and not r["qualifying"] and r["level"] in ("T1000", "T500", "T250")
                and 2019 <= r["year"] <= 2026]
    lo_pre, hi_pre = min(r["box_pct"] for r in wta_pre), max(r["box_pct"] for r in wta_pre)
    lo_post = min(r["box_pct"] for r in wta_post)
    itf = {(r["tour"], r["year"]): r["box_pct"] for r in cov if r["level"] == "ITF" and not r["qualifying"]}
    gsq = {(r["tour"], r["year"]): r["box_pct"] for r in cov if r["level"] == "GS" and r["qualifying"]}
    parts.append(f'''    <div class="sub">
      <h3>Box-score coverage</h3>
      <div class="prose">
        <p>Each square is one level in one season: the share of its matches with a box score that passed every check; the key
        above the chart gives each shade's range. <span class="kind">Observed</span>The main tours are near complete throughout. The WTA's 1000, 500 and 250 main draws
        range from {pct(lo_pre)} to {pct(hi_pre)} in 2010–2015 and are at least {pct(lo_post)} from 2019, which is why the Brief evaluates WTA
        box-score features from 2019. ITF matches have box scores only from 2025 ({pct(itf[("atp", 2025)])} of men's, {pct(itf[("wta", 2025)])} of
        women's matches that year). Grand Slam qualifying has gaps on both tours: the men's is at {pct(gsq[("atp", 2016)])} in 2016 and
        {pct(gsq[("atp", 2017)])} in 2017.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>Matches with a usable box score, by level and season</h3><p>Hover a square for its numbers; 2010–2012 are history only</p></div>
        <div class="scale" id="heat-scale" aria-hidden="true"></div>
        <div class="heat-pair" id="heat-pair"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap" id="heat-table"></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ C. cleaning in plain words
    rules = {r["rule_id"]: r for r in s["cleaning"]["rules"]}
    over = s["cleaning"]["cells_over_1pct"]
    groups_html = []
    used = set()
    for title, prefixes in GROUPS:
        ids = [rid for rid in sorted(rules) if rid not in used and rid.startswith(prefixes)]
        used |= set(ids)
        body = []
        for rid in ids:
            r = rules[rid]
            k = r["cells_over_1pct"]
            flag = f' · <span class="flag">{k} cell{"" if k == 1 else "s"} over 1%</span>' if k else ""
            body.append(f'<tr><td>{esc(rid)}</td><td>{esc(r["rule"][0].upper() + r["rule"][1:])}'
                        f'<br><span class="muted">{esc(ACTION_WORDS.get(r["action"], r["action"]))}</span>{flag}</td>'
                        f'<td class="r">{n(r["count"])}</td></tr>')
        groups_html.append(f'<tr class="group"><td colspan="3">{esc(title)}</td></tr>' + "".join(body))
    by_rule = {}
    for c in over:
        by_rule.setdefault(c["rule_id"], []).append(c)
    over_items = []
    for rid, cells in sorted(by_rule.items()):
        cells = sorted(cells, key=lambda c: -c["pct_of_cell"])
        shown = "; ".join(f'{TOUR[c["tour"]]} {TOUR_LEVEL_WORDS.get((c["tour"], c["level"]), LEVEL_WORDS.get(c["level"], c["level"]))}{" qualifying" if c["qualifying"] else ""} '
                          f'{c["year"]} ({pct(c["pct_of_cell"])})' for c in cells[:6])
        more = f" and {len(cells) - 6} more" if len(cells) > 6 else ""
        over_items.append(f'<li><b>{esc(rid)}</b> {esc(rules[rid]["rule"])}: {esc(shown)}{esc(more)}.</li>')
    parts.append(f'''    <div class="sub">
      <h3>Cleaning, in plain words</h3>
      <div class="prose">
        <p>Every rule below is logged with its count in each tour × level × season cell (qualifying and main draw apart) in
        <code>stage0_cleaning_log.csv</code>. Nothing is deleted from the sources: a rule removes a row from the table, or marks a
        value missing, and says so. The Brief sends to the owner any rule that removes more than 1% of a cell; those are listed
        after the table.</p>
      </div>
      <div class="panel">
        <div class="table-wrap"><table>
          <thead><tr><th>Rule</th><th>What it does, and its effect</th><th class="r">Matches</th></tr></thead>
          <tbody>{"".join(groups_html)}</tbody></table></div>
      </div>
      <div class="prose">
        <h3>For the owner: rules above 1% of a cell</h3>
        <ul class="plain">{"".join(over_items)}</ul>
      </div>
    </div>''')

    # ------------------------------------------------------------------ D. known holes
    since = {(r["tour"], r["level"], r["qualifying"]): r["matches"] for r in holes["qualifying_since_2026_05_25"]}
    before = {(r["tour"], r["level"], r["qualifying"]): r["matches"] for r in holes["qualifying_same_weeks_2025"]}
    wta_q_before = sum(v for (tour, lv, q), v in before.items() if tour == "wta" and q)
    wta_q_since = sum(v for (tour, lv, q), v in since.items() if tour == "wta" and q)
    chq_before, chq_since = before.get(("atp", "CH", True), 0), since.get(("atp", "CH", True), 0)
    w125_before, w125_since = before.get(("wta", "CH", False), 0), since.get(("wta", "CH", False), 0)
    itf_before = before.get(("atp", "ITF", False), 0) + before.get(("wta", "ITF", False), 0)
    itf_since = since.get(("atp", "ITF", False), 0) + since.get(("wta", "ITF", False), 0)
    far = sum(r["rows"] for r in merge["links_by_agreement"] if r["days"] == "32-366")
    ind = holes["indoor_known_pct"]
    mins = holes["minutes_known_pct"]
    nosv = {(r["tour"], r["year"]): r["matches"] for r in holes["box_without_service_games"]}
    wta_nosv = sum(v for (tour, y), v in nosv.items() if tour == "wta" and 2010 <= y <= 2014)
    incl = {}
    for r in holes["sv_gms_incl_tb_events"]:
        if r["level"] == "GS":
            for e in r["events"].split("; "):
                incl.setdefault(e.title().replace("Us Open", "US Open"), set()).add(r["year"])
    incl_text = "; ".join(f"{e} {spans(sorted(ys))}" for e, ys in sorted(incl.items()))
    chq = {r["year"]: r["matches"] for r in cov if r["tour"] == "atp" and r["level"] == "CH" and r["qualifying"]}
    gsq_gap = {tour: spans(sorted(y for (tt, y), v in gsq.items() if tt == tour and v < 90)) for tour in ("atp", "wta")}
    wta_gap = spans(sorted({r["year"] for r in cov if r["tour"] == "wta" and not r["qualifying"]
                            and r["level"] in ("T1000", "T500", "T250") and r["box_pct"] < 90}))
    parts.append(f'''    <div class="sub">
      <h3>Known holes</h3>
      <ul class="plain">
        <li><span class="kind">Observed</span><b>The last weeks are thin below the main tours.</b> TML, the only source after Sackmann's files
        stop, lists no WTA 125 events, no qualifying on the WTA side and no Challenger or ITF qualifying, and no ITF events at all.
        From 25 May 2026 the table holds {n(w125_since)} WTA 125 matches ({n(w125_before)} in the same weeks of 2025), {n(wta_q_since)} WTA qualifying
        matches ({n(wta_q_before)}), {n(chq_since)} Challenger qualifying matches ({n(chq_before)}) and {n(itf_since)} ITF matches ({n(itf_before)}), all from
        Sackmann's last weeks (to 2 June).</li>
        <li><span class="kind">Observed</span><b>Men's Challenger qualifying is missing before 2016.</b> Sackmann's files hold none before 2015
        and {n(chq.get(2015, 0))} in 2015, against {n(chq.get(2016, 0))} in 2016, so 2013–2015 Challenger qualifying adds almost nothing to the evaluation.</li>
        <li><span class="kind">Observed</span><b>Box scores.</b> Under 90% of matches have one in the WTA's 1000, 500 and 250 main draws of {esc(wta_gap)},
        in Grand Slam qualifying in {esc(gsq_gap["atp"])} (men) and {esc(gsq_gap["wta"])} (women), and in every ITF season before 2025.
        For {n(wta_nosv)} WTA matches of 2010–2014 the box score lacks the service-games count, so hold and break rates are missing
        there while the point counts are kept.</li>
        <li><span class="kind">Observed</span><b>Service games are counted two ways.</b> At some Grand Slams the count includes tiebreak games
        ({esc(incl_text)}, on either tour); everywhere else it does not. Both pass the checks, and each match where a tiebreak shows the
        difference is flagged (<code>sv_gms_incl_tb</code>). A hold rate there counts a tiebreak as a service game.</li>
        <li><span class="kind">Observed</span><b>Indoor or outdoor is mostly unknown outside the ATP main tour.</b> Only TML records it: known for
        {pct(ind["atp|T250"])} of ATP 250 matches but {pct(ind["atp|CH"])} of Challengers and {pct(ind["wta|T250"])} of WTA 250 matches.</li>
        <li><span class="kind">Observed</span><b>Match length.</b> Minutes are known for {pct(mins["atp|T250"])} of ATP 250 matches, {pct(mins["wta|T250"])} of
        WTA 250 matches and {pct(mins["atp|ITF"])} of men's ITF matches.</li>
        <li><span class="kind">Observed</span><b>Rankings.</b> {pct(holes["evaluation_rank_known_pct"]["atp"])} of ATP and {pct(holes["evaluation_rank_known_pct"]["wta"])} of WTA
        players in evaluation matches carry a ranking.</li>
        <li><span class="kind">Inferred</span><b>Dates of TML-only matches.</b> TML gives some later editions of a Challenger the first edition's
        name and date (2022's Forlì Challengers all read "Forli 1"); {n(far)} TML rows matched a Sackmann match of the same event and
        score more than a month away. Where Sackmann holds the event its date is used, but a TML-only match may sit in the wrong week.</li>
      </ul>
    </div>''')

    # ------------------------------------------------------------------ checks
    cnt = ch["counts_vs_data_map"]
    tot = {r["tour"]: r for r in cnt["totals_by_tour"]}
    bx = ch["box_vs_merge_feasibility"]
    sa = ch["side_a_won"]["all"]
    lp = ch["asof_leak_probe"]
    parts.append(f'''    <div class="sub">
      <h3>How the table was checked</h3>
      <ul class="plain">
        <li><b>Against the data map</b> (2018 on, walkovers left out): {n(tot["M"]["stage0"])} men's matches against the map's
        {n(tot["M"]["map_result_files"])} from the same two sources, and {n(tot["W"]["stage0"])} women's against {n(tot["W"]["map_result_files"])};
        {cnt["cells_within_1pct_of_result_files"]} of {cnt["cells_with_result_files"]} tour × level × season cells agree within 1%. The differences are
        explained in <code>stage0.md</code>.</li>
        <li><b>Against the merge-feasibility study's box-score coverage</b>: {bx["within_1_point"]} of {bx["cells"]} cells within one percentage
        point; of the other {bx["cells"] - bx["within_1_point"]}, {bx["off_by_more_than_1_point_by_tier"].get("team", 0)} are team events, which here also include the Olympics and the ATP and United Cups.</li>
        <li><b>Side A</b> won {pct(100 * sa["share"], 2)} of {n(sa["n"])} matches (95% range {pct(100 * sa["lo"], 2)}–{pct(100 * sa["hi"], 2)}).</li>
        <li><b>No look-ahead.</b> On the {n(lp["rows"])} player rows of 2024, the as-of helper gave the same values for every match
        before and at {lp["asof_helper"]["cuts"]} random cut points when everything from the cut on was scrambled; a deliberately leaky running
        total changed at {n(lp["leaky_running_total_including_the_match"]["changed_at_cut"])} of the cut rows.</li>
      </ul>
    </div>''')

    data = {"coverage": [{k: r[k] for k in ("tour", "level", "qualifying", "year", "matches", "evaluation", "box_pct",
                                              "box_in_source_pct")} for r in cov],
            "rows": [{"level": lv, "qualifying": q, "label": lab, "evaluated": e} for lv, q, lab, e in ROWS],
            "years": list(range(2010, 2027)), "bins": BINS}
    return {"html": "\n".join(parts), "data": data, "script": HEAT_JS}


HEAT_JS = r"""
(function () {
  const D = window.REPORT["data-used"];
  const years = D.years, bins = D.bins;
  const by = new Map(D.coverage.map(r => [r.tour + "|" + r.level + "|" + r.qualifying + "|" + r.year, r]));
  const fmt = v => v.toLocaleString("en-US");
  const binOf = v => bins.findIndex(([lo, hi]) => v >= lo && v < hi);
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };

  const scale = document.getElementById("heat-scale");
  scale.appendChild(el("span", "lbl", "Share with a box score:"));
  bins.forEach(([lo, hi], i) => {
    const w = el("span"); w.style.display = "inline-flex"; w.style.alignItems = "center"; w.style.gap = "4px";
    const sw = el("span", "sw"); sw.style.background = "var(--seq-" + i + ")"; w.appendChild(sw);
    w.appendChild(el("span", null, lo + "–" + Math.min(100, Math.round(hi)) + "%")); scale.appendChild(w);
  });
  const nw = el("span"); nw.style.display = "inline-flex"; nw.style.alignItems = "center"; nw.style.gap = "4px";
  nw.appendChild(el("span", "sw none")); nw.appendChild(el("span", null, "no matches")); scale.appendChild(nw);

  const pair = document.getElementById("heat-pair");
  ["atp", "wta"].forEach(tour => {
    const box = el("div", "heat");
    box.appendChild(el("h4", null, tour === "atp" ? "ATP (men)" : "WTA (women)"));
    const grid = el("div", "heat-grid");
    grid.setAttribute("role", "img");
    grid.setAttribute("aria-label", (tour === "atp" ? "ATP" : "WTA") + " box-score coverage by level and season; the table below holds the numbers");
    grid.style.gridTemplateColumns = "minmax(6rem, 11rem) repeat(3, minmax(0, 1fr)) 6px repeat(" + (years.length - 3) + ", minmax(0, 1fr))";
    grid.appendChild(el("div"));
    years.forEach((y, i) => { if (i === 3) grid.appendChild(el("div", "gap")); grid.appendChild(el("div", "yl" + ((y - 2010) % 3 ? " minor" : ""), "'" + String(y).slice(2))); });
    D.rows.forEach(row => {
      const any = years.some(y => by.has(tour + "|" + row.level + "|" + row.qualifying + "|" + y));
      if (!any) return;
      const lab = el("div", "rl" + (row.evaluated ? "" : " hist"), row.label); lab.title = row.label + (row.evaluated ? "" : " (history only)");
      grid.appendChild(lab);
      years.forEach((y, i) => {
        if (i === 3) grid.appendChild(el("div", "gap"));
        const r = by.get(tour + "|" + row.level + "|" + row.qualifying + "|" + y);
        const c = el("div", "cell" + (r ? "" : " none"));
        if (r) {
          c.style.background = "var(--seq-" + binOf(r.box_pct) + ")";
          c.tabIndex = -1;
          window.reportTip.bind(c, () => [
            r.box_pct.toFixed(1) + "% with a box score",
            (tour === "atp" ? "ATP" : "WTA") + " · " + row.label + " · " + y,
            fmt(r.matches) + " matches, " + fmt(r.evaluation) + " evaluated",
            "before the checks: " + r.box_in_source_pct.toFixed(1) + "%"]);
        }
        grid.appendChild(c);
      });
    });
    box.appendChild(grid);
    pair.appendChild(box);
  });

  const holder = document.getElementById("heat-table");
  ["atp", "wta"].forEach(tour => {
    const t = el("table"); const th = el("thead"); const hr = el("tr");
    hr.appendChild(el("th", null, (tour === "atp" ? "ATP" : "WTA") + ", % with a box score"));
    years.forEach(y => hr.appendChild(el("th", "r", String(y))));
    th.appendChild(hr); t.appendChild(th);
    const tb = el("tbody");
    D.rows.forEach(row => {
      const cells = years.map(y => by.get(tour + "|" + row.level + "|" + row.qualifying + "|" + y));
      if (!cells.some(Boolean)) return;
      const tr = el("tr"); tr.appendChild(el("td", null, row.label));
      cells.forEach(r => { const td = el("td", "r", r ? r.box_pct.toFixed(0) : "–"); if (r) td.title = fmt(r.matches) + " matches"; tr.appendChild(td); });
      tb.appendChild(tr);
    });
    t.appendChild(tb); holder.appendChild(t);
  });
})();
"""
