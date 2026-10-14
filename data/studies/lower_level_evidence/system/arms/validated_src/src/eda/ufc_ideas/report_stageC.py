"""Report section for Stage C of the study "ideas borrowed from UFC-predictions": strength of schedule, the
retrospective credit for old opponents and fatigue, scored by the shared harness. Every number comes from
data/studies/ufc_ideas/stageC_summary.json (written by stageC_rundown.py); render_report.py assembles the page.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": "C", "id": "stage-c", "title": "Strength of schedule, credit for old opponents, fatigue"}
TOUR = {"atp": "ATP (men)", "wta": "WTA (women)"}
FAMILIES = ("strength of schedule", "retrospective credit", "fatigue", "earlier study")


def esc(x) -> str:
    return html.escape(str(x))


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def f2(x) -> str:
    v = num(x)
    return "–" if v is None else f"{v:.2f}".replace("-0.00", "0.00").replace("-", "−")


def n0(x) -> str:
    v = num(x)
    return "–" if v is None else f"{int(round(v)):,}"


def label(r: dict) -> str:
    """The row's name (each Stage C name already says its window: last 52 weeks, decayed, career)."""
    return r["name"]


def best(rows: list, tour: str, fams: tuple, key: str = "elo_imp") -> dict:
    c = [r for r in rows if r["tour"] == tour and r["group"] in fams and num(r.get(key)) is not None]
    return max(c, key=lambda r: r[key])


def pair_tile(lab, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(lab)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div><div><small>WTA</small><div class="value">{wta}</div>'
            f'</div></div><div class="note">{note}</div></div>')


def render(study_dir: Path) -> dict:
    s = json.loads((Path(study_dir) / "stageC_summary.json").read_text(encoding="utf-8"))
    rank, rr, sos, fat = s["ranking"], s["ranking_given_ratings"], s["sos"], s["fatigue"]
    new = ("strength of schedule", "retrospective credit")
    b1 = {t: best(rank, t, new) for t in TOUR}
    b2 = {t: best(rank, t, ("fatigue",)) for t in TOUR}
    b3 = {t: best(rank, t, new + ("fatigue",), "market_imp") for t in TOUR}
    p1, p2 = sos["probe"], fat["probe"]
    lines = s["lines"]
    parts = [f'''    <div class="prose">
      <p>Three ideas from the owner's UFC models, built for the same pool of matches as the earlier study and scored by
      the same harness: <b>strength of schedule</b> (how strong the opponents a player met were), the <b>retrospective
      credit</b> for old opponents (whether the players someone beat turned out to be good), and <b>fatigue</b> (whether a
      player fades as a match gets long). Four rows of the earlier study's Stage 4 were scored again in the same run as
      references; they reproduce its numbers (largest difference {max(x["largest_difference"] for x in s["reference_check"]):.1e}).</p>
    </div>
    <div class="tiles" role="list">
      {pair_tile("Best schedule or credit row, given Elo (milli-log-loss)", f2(b1["atp"]["elo_imp"]), f2(b1["wta"]["elo_imp"]),
                 f"{esc(label(b1['atp']))}; {esc(label(b1['wta']))}")}
      {pair_tile("Best fatigue row, given Elo", f2(b2["atp"]["elo_imp"]), f2(b2["wta"]["elo_imp"]),
                 f"{esc(label(b2['atp']))}; {esc(label(b2['wta']))}")}
      {pair_tile("Best new row, given the closing odds", f2(b3["atp"]["market_imp"]), f2(b3["wta"]["market_imp"]),
                 f"{esc(label(b3['atp']))}; {esc(label(b3['wta']))}; "
                 + ("none reaches 1, the earlier study's “clear” size" if max(b3[t]["market_imp"] for t in TOUR) < 1
                    else "at least one reaches 1, the earlier study's “clear” size"))}
      <div class="tile" role="listitem"><div class="label">Leak probes: protected matches whose features moved</div>
        <div class="value">{n0(p1["protected_changed"] + p2["protected_changed"])} of {n0(p1["protected_checked"] + p2["protected_checked"])}</div>
        <div class="note">two probes cut by date, event and round; a deliberately leaky control moved at
        {n0(p1["control_protected_changed"] + p2["control_protected_changed"])}</div></div>
    </div>
    <div class="sub"><h3>Terms used in this section</h3><dl class="terms">
      <dt>Strength of schedule</dt><dd>The UFC project's measure of the opposition: the mean pre-match strength of the
      opponents a player met in the last 52 weeks (surface Elo, or the Stage 3 serve and return ratings). "Quality of
      wins" is the same over the opponents beaten.</dd>
      <dt>Phantom prior</dt><dd>K imaginary opponents of the tour's typical strength mixed into the mean, so that a
      player with few matches sits near typical: (sum + K × typical) / (n + K). K was chosen on 2013–2018 and frozen.</dd>
      <dt>Revaluation (credit)</dt><dd>For each opponent of the last 52 weeks: their Elo now (before the week of the match
      being predicted) minus their Elo when they were met. "Later only" also removes the meeting's own Elo change, as
      the UFC rule does, so that only the opponent's later matches revise the credit.</dd>
      <dt>Late decline</dt><dd>From the Grand Slam point-by-point files: a player's serve points won in the third set
      onward minus in the first two, against the opponent's same change. Positive means holding up better late.</dd>
      <dt>Grinder</dt><dd>Points won above what the Stage 3 ratings expected, in long matches (minutes per set above the
      tour's upper quartile) minus in short ones.</dd>
      <dt>Reliability</dt><dd>The correlation of a player's measure between two random halves of their matches: near 0,
      the measure is luck; it must also beat the same measure on pure-luck replays, which have no fatigue.</dd>
      <dt>Given Elo, given the market</dt><dd>Milli-log-loss better (positive) than surface Elo, or the closing odds,
      alone; walk-forward by season, beside 20 shuffled copies. The family-wide line given Elo is
      {f2(lines["atp|elo"]["line"])} (men) and {f2(lines["wta|elo"]["line"])} (women) standard deviations of the copies.</dd>
    </dl></div>''']
    table = {t: [{"fam": r["group"], "label": label(r), "elo": num(r["elo_imp"]), "lo": num(r["elo_lo"]), "hi": num(r["elo_hi"]),
                  "bmax": num(r["elo_band_max"]), "line": bool(r["elo_clears_line"]), "eras": r["eras_positive"],
                  "eras_n": r["eras_scored"], "e22": num(r.get("elo_2022-2026")), "mkt": num(r.get("market_imp")),
                  "mlo": num(r.get("market_lo")), "mhi": num(r.get("market_hi")), "mbmax": num(r.get("market_band_max")),
                  "reading": r["reading"], "from": r["scored_from"]} for r in rank if r["tour"] == t] for t in TOUR}
    parts.append('''    <div class="sub"><h3>Every row, given Elo and given the market</h3>
      <div class="panel"><div class="controls"><span>Tour:</span><div class="seg" role="group" aria-label="Tour">
        <button type="button" data-sctour="atp" aria-pressed="true">ATP (men)</button>
        <button type="button" data-sctour="wta" aria-pressed="false">WTA (women)</button></div></div>
        <div class="table-wrap"><table class="num wide" id="sc-rank"><thead><tr><th>Row</th>
          <th class="r">Given Elo (95% range)</th><th class="r">Band max</th><th>Line</th><th class="r">Eras +</th>
          <th class="r">2022–26</th><th class="r">Given market (95% range)</th><th class="r">Band max</th><th>Reading</th></tr></thead>
          <tbody></tbody></table></div>
        <p class="note-small">Milli-log-loss, positive = better. "Band max": the best of the 20 shuffled copies. "Line":
        clears the family-wide line given Elo. A finding clears the line and is better than Elo in three eras or more.
        The women's box-score, point-by-point and ratings rows are scored from 2019. Every group is in
        <code>stageC_results.csv</code>; this table is <code>stageC_ranking.csv</code>.</p></div></div>''')
    rows_r = "".join(
        f'<tr><td>{esc(TOUR[r["tour"]])}</td><td>{esc(label(r))}{" <span class=tag>reference</span>" if r["group"] == "earlier study" else ""}'
        f'</td><td class="r">{f2(r["ratings_imp"])} ({f2(r["ratings_lo"])} to '
        f'{f2(r["ratings_hi"])})</td><td class="r">{f2(r["ratings_band_max"])}</td><td>{esc(r["reading"])}</td></tr>' for r in rr)
    parts.append(f'''    <div class="sub"><h3>Added to the Stage 3 ratings instead of Elo</h3>
      <div class="prose"><p>The two rows with the largest gain given Elo in each of the schedule and credit families,
      per tour, added to the earlier study's strongest feature (the serve and return ratings through the iid model).
      The women's are scored from 2019, where the ratings are. The ratings know nothing of results, so a results-based
      strength measure is expected to add here.</p></div>
      <div class="panel"><div class="table-wrap"><table class="num"><thead><tr><th>Tour</th><th>Row</th>
        <th class="r">Given the ratings (95% range)</th><th class="r">Band max</th><th>Reading</th></tr></thead>
        <tbody>{rows_r}</tbody></table></div></div></div>''')
    rel = {}
    for t in TOUR:
        rel[f"decline|{t}"] = fat["reliability_decline"][t]["sets"]["by_n"]
        rel[f"grinder|{t}"] = fat["reliability_grinder"][t]["by_n"]
    titles = {"decline|atp": "Late decline, men", "decline|wta": "Late decline, women", "grinder|atp": "Grinder, men",
              "grinder|wta": "Grinder, women"}
    twin = "".join(f'<tr><td>{esc(titles[k])}</td><td class="r">{x["n"]}</td><td class="r">{n0(x["players"])}</td>'
                   f'<td class="r">{f2(x["r"])}</td><td class="r">{f2(x["luck_r_mean"])}</td>'
                   f'<td class="r">{f2(x["luck_r_min"])} to {f2(x["luck_r_max"])}</td></tr>' for k, v in rel.items() for x in v)
    kd, kg = fat["K_used"]["decline"], fat["K_used"]["grinder"]
    parts.append(f'''    <div class="sub"><h3>Are the fatigue measures traits?</h3>
      <div class="prose"><p>The correlation of each player's measure between two random halves of their matches, against
      the number of matches in each half, beside the same measure on replays where every point is an independent draw
      (pure luck: no fatigue, but the same players, strengths and match formats). A hollow dot rests on fewer than 300
      players: directional only. The shrinkage constants used are {n0(kd["atp"])} and {n0(kd["wta"])} effective points
      for the late decline (men, women) and {n0(kg["atp"])} and {n0(kg["wta"])} for the grinder.</p></div>
      <div class="panel"><div class="legend"><span class="key"><span class="sw-line" style="background:var(--series-1)"></span>Real matches</span>
        <span class="key"><span class="sw-line" style="background:var(--series-2)"></span>Pure-luck replays (mean; band: their range)</span></div>
        <div class="chart-pair" id="sc-rel"></div>
        <details class="twin"><summary>The numbers as a table</summary><div class="table-wrap"><table class="num">
          <thead><tr><th>Measure</th><th class="r">Matches per half</th><th class="r">Players</th><th class="r">Real</th>
          <th class="r">Pure luck</th><th class="r">Luck range</th></tr></thead><tbody>{twin}</tbody></table></div></details></div></div>''')
    data = {"table": table, "rel": rel, "titles": titles}
    return {"html": "\n".join(parts), "data": data, "script": JS}


JS = r"""
(function () {
  const D = window.REPORT["stage-c"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, a, p) => { const n = document.createElementNS(NS, tag); for (const k in a) n.setAttribute(k, a[k]); if (p) p.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const f2 = v => v == null ? "–" : (v < 0 && Math.abs(v).toFixed(2) !== "0.00" ? "−" : "") + Math.abs(v).toFixed(2);
  let tour = "atp";
  const FAM = ["strength of schedule", "retrospective credit", "fatigue", "earlier study"];
  function table() {
    const body = document.querySelector("#sc-rank tbody");
    body.replaceChildren();
    let fam = null;
    D.table[tour].slice().sort((a, b) => FAM.indexOf(a.fam) - FAM.indexOf(b.fam) || (b.elo ?? -1e9) - (a.elo ?? -1e9)).forEach(r => {
      if (r.fam !== fam) {
        const g = el("tr", "group"), td = el("td", null, r.fam === "earlier study" ? "earlier study (reference rows)" : r.fam);
        td.colSpan = 9; g.appendChild(td); body.appendChild(g);
      }
      const tr = el("tr");
      [[r.label + (r.from === 2019 && tour === "wta" ? " · from 2019" : "")],
       [f2(r.elo) + " (" + f2(r.lo) + " to " + f2(r.hi) + ")", "r"], [f2(r.bmax), "r"], [r.line ? "clears" : ""],
       [r.eras + " of " + r.eras_n, "r"], [f2(r.e22), "r"], [r.mkt == null ? "–" : f2(r.mkt) + " (" + f2(r.mlo) + " to " + f2(r.mhi) + ")", "r"],
       [f2(r.mbmax), "r"], [r.reading]].forEach(([t, c]) => tr.appendChild(el("td", c || null, t)));
      if (r.reading === "finding") tr.lastChild.style.fontWeight = "650";
      tr.firstChild.style.cssText = "white-space:normal;min-width:13rem";
      fam = r.fam;
      body.appendChild(tr);
    });
  }
  document.querySelectorAll("#stage-c [data-sctour]").forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll("#stage-c [data-sctour]").forEach(o => o.setAttribute("aria-pressed", String(o === b)));
    tour = b.getAttribute("data-sctour"); table();
  }));
  table();
  const host = document.getElementById("sc-rel");
  Object.keys(D.rel).forEach(key => {
    const pts = D.rel[key].filter(p => p.luck_r_mean != null);
    const box = el("div", "chart"); box.appendChild(el("h4", null, D.titles[key])); host.appendChild(box);
    const W = 360, H = 210, L = 40, R = 12, T = 10, B = 34;
    const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img", "aria-label": D.titles[key] + ": split-half correlation, real and pure luck" }, box);
    const xs = pts.map(p => p.n), vals = pts.flatMap(p => [p.r, p.luck_r_min, p.luck_r_max]);
    const xmax = Math.max(...xs), ylo = Math.min(-0.05, Math.floor(Math.min(...vals) * 20) / 20), yhi = Math.max(0.2, Math.ceil(Math.max(...vals) * 20) / 20);
    const X = v => L + (W - L - R) * v / xmax, Y = v => T + (H - T - B) * (yhi - v) / (yhi - ylo);
    for (let y = ylo; y <= yhi + 1e-9; y += 0.05) {
      S("line", { x1: L, x2: W - R, y1: Y(y), y2: Y(y), class: Math.abs(y) < 1e-9 ? "axis" : "grid" }, svg);
      const t = S("text", { x: L - 6, y: Y(y) + 4, "text-anchor": "end" }, svg); t.textContent = f2(y);
    }
    xs.forEach(v => { const t = S("text", { x: X(v), y: H - B + 16, "text-anchor": "middle" }, svg); t.textContent = v; });
    const xl = S("text", { x: (L + W - R) / 2, y: H - 4, "text-anchor": "middle", class: "lab" }, svg); xl.textContent = "matches in each half";
    S("path", { d: pts.map((p, i) => (i ? "L" : "M") + X(p.n) + "," + Y(p.luck_r_max)).join("") + pts.slice().reverse().map(p => "L" + X(p.n) + "," + Y(p.luck_r_min)).join("") + "Z",
                fill: "var(--series-2)", opacity: 0.12 }, svg);
    [["luck_r_mean", "var(--series-2)"], ["r", "var(--series-1)"]].forEach(([k, c]) => {
      S("path", { d: pts.map((p, i) => (i ? "L" : "M") + X(p.n) + "," + Y(p[k])).join(""), fill: "none", stroke: c, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, svg);
      pts.forEach(p => S("circle", { cx: X(p.n), cy: Y(p[k]), r: 4, fill: p.players < 300 ? "var(--surface)" : c, stroke: p.players < 300 ? c : "var(--surface)", "stroke-width": 2 }, svg));
    });
    pts.forEach(p => {
      const hit = S("rect", { x: X(p.n) - 12, y: T, width: 24, height: H - T - B, class: "hit", tabindex: 0 }, svg);
      window.reportTip.bind(hit, () => ["real " + f2(p.r) + " · pure luck " + f2(p.luck_r_mean), "luck range " + f2(p.luck_r_min) + " to " + f2(p.luck_r_max),
        p.n + " matches per half, " + p.players.toLocaleString("en-US") + " players" + (p.players < 300 ? " (directional)" : "")]);
    });
  });
})();
"""
