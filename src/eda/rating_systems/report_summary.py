"""The summary section of the report of "rating systems against Elo" (opens report.html).

Contract (as the earlier studies' report sections): SECTION and render(study_dir) -> {"html", "data", "script"}. Every
number is read from summary_results.json (src/eda/rating_systems/summary_results.py); the literature's numbers are
quoted from docs/research/rating-systems/README.md, which records their sources. The page shell's CSS classes are
src/eda/predictability_diagnostic/report_shell.html's.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": "summary", "id": "summary", "title": "What we found"}
TOUR = {"atp": "ATP (men)", "wta": "WTA (women)"}
WINDOWS = [("2013-2026", "2013–2026"), ("2019-2026", "2019–2026 (after the tuning years)"),
           ("2022-2026 (headline)", "2022–2026")]
LEAD = ["glicko_cs", "ttt", "glicko2m", "trueskill"]      # the systems carried through every test (harness, ladder)
SHORT = {"glicko_cs": "Glicko, correlated surfaces", "ttt": "TrueSkill Through Time", "ttt_hold": "TTT, two-week events held",
         "glicko2m": "Glicko-2, match by match", "trueskill": "TrueSkill", "trueskill_cs": "TrueSkill, correlated surfaces",
         "glicko1m": "Glicko-1, match by match", "glicko2": "Glicko-2, weekly periods", "glicko1": "Glicko-1, weekly periods"}


def esc(x) -> str:
    return html.escape(str(x))


def mm(x, d=2) -> str:
    if x is None:
        return "–"
    s = f"{abs(x):.{d}f}"
    return ("−" if x < 0 and s.strip("0.") else "+") + s


def rng(lo, hi) -> str:
    return "–" if lo is None or hi is None else f"{mm(lo)} to {mm(hi)}"


def pc(x) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def kick(label: str) -> str:
    return f'<span class="kind">{esc(label)}</span>'


def render(study_dir: Path) -> dict:
    S = json.loads((Path(study_dir) / "summary_results.json").read_text(encoding="utf-8"))
    names, systems = S["names"], S["systems"]
    raw, orth, mk, hs = S["raw"], S["orthogonality"], S["market"], S["harness"]
    W19, W22 = "2019-2026", "2022-2026 (headline)"
    parts = []

    def best_vs_elo(t, w=W19):
        rec = raw[t][w]["systems"]
        s = max((k for k in rec if k in LEAD), key=lambda k: rec[k]["better_than_elo"])
        return s, rec[s]

    # ------------------------------------------------------------------ the current standing (the owner, 3 Oct 2026)
    ld = S["leader"]
    assert all(ld["tuning_rank"][t][0] == ld["system"] == "ttt" for t in TOUR), "the standing's text assumes TTT leads"

    def vs(t, s, w=W19):
        r = ld["head_to_head"][t][w][s]
        return f'{mm(r["ttt_better"])} ({rng(r["lo"], r["hi"])})'
    parts.append(f'''    <div class="takeaways" role="list">
      <div class="takeaway" role="listitem" style="grid-column:1/-1">{kick("decision")}<span class="head">Current standing: TrueSkill Through Time
        is the leading candidate for the base rating</span>
        <p>Named by the owner on 3 Oct 2026, it is the present leader, not a final choice
        (<a href="../../decisions/2026-10-03-leading-rating-candidate.md">decision record</a>). It has the lowest log loss
        of the {len(ld["tuning_rank"]["atp"])} ratings on the tuning years, the rule that picks the leader, on both tours.
        After them it stays best for the men, ahead of the correlated-surface Glicko by {vs("atp", "glicko_cs")}
        milli-log-loss in 2019–2026. For the women it is level with TrueSkill with correlated surfaces,
        {vs("wta", "trueskill_cs")}. It makes a better forecast but is not an edge on the market.</p></div>
    </div>''')

    # ------------------------------------------------------------------ the question
    parts.append('''    <div class="prose">
      <p>The owner asked whether a <b>Glicko-2</b> or <b>TrueSkill</b> rating, or whatever rating the published evidence
      finds most predictive in tennis, improves on the surface Elo the earlier studies used as their base, and whether any
      rating adds to the bookmakers' closing prices. Each system was built for tennis under the same time rule as Elo (a
      match sees only earlier weeks and earlier rounds of its own event), tuned on the same seasons (2013–2018, with
      2010–2012 as warm-up), frozen, and scored on the same 155,130 men's and 60,321 women's matches of 2013–2026. Scores
      are log loss: lower is better, a coin scores 0.693, and one milli-log-loss is 0.001. The ranges are 95% intervals
      clustered by four-week calendar blocks, as the shared test now computes them.</p>
    </div>''')

    # ------------------------------------------------------------------ takeaways (each tour's leading system: the one
    # furthest ahead of Elo on every evaluation match of 2019-2026, after the tuning years)
    lead = {t: best_vs_elo(t)[0] for t in TOUR}
    gm = {t: hs[t]["systems"] for t in TOUR}
    o22 = {t: orth[t]["2022"]["bases"] for t in TOUR}
    weekly = {t: raw[t][W19]["systems"].get("glicko2", {}).get("better_than_elo") for t in TOUR}

    def gain(t, w=W19, odds=False):
        r = raw[t][w]["systems"][lead[t]]
        if odds:
            return f'{mm(r["better_than_elo_odds"])} ({rng(r["odds_block_lo"], r["odds_block_hi"])})'
        return f'{mm(r["better_than_elo"])} ({rng(r["block_lo"], r["block_hi"])})'

    def mkt_line(t):
        g = gm[t][lead[t]]["given_market"]
        return "–" if not g else f'{mm(g["imp"])} ({rng(g["lo"], g["hi"])})'

    def orth_line(t, key):
        r = o22[t].get(lead[t], {}).get(key)
        return "–" if not r else f'{mm(r["gain"])} ({rng(r["lo"], r["hi"])})'
    parts.append(f'''    <div class="takeaways" role="list">
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">Against surface Elo</span>
        <p>On every evaluation match after the tuning years (2019–2026), the leading system of those carried through
        every test beats surface Elo by
        {gain("atp")} milli-log-loss for the men ({esc(names[lead["atp"]])}) and {gain("wta")} for the women
        ({esc(names[lead["wta"]])}). Glicko-2 run as Glickman specifies it, a week as the rating period, scores
        {mm(weekly["atp"])} and {mm(weekly["wta"])} against Elo.</p></div>
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">Against the bookmakers</span>
        <p>On the main-tour matches with odds (2019–2026) the leading system is {gain("atp", odds=True)} (men) and
        {gain("wta", odds=True)} (women) against Elo. Added to the closing prices through the shared test, it gains
        {mkt_line("atp")} and {mkt_line("wta")} milli-log-loss.</p></div>
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">Beside the promising features</span>
        <p>In the audit's full feature model (2022–2026), the leading system in Elo's place changes the forecast by
        {orth_line("atp", "full_vs_elo_full")} (men) and {orth_line("wta", "full_vs_elo_full")} (women); kept beside Elo
        it adds {orth_line("atp", "both_full_vs_elo_full")} and {orth_line("wta", "both_full_vs_elo_full")}.</p></div>
    </div>''')

    # ------------------------------------------------------------------ the chart: each system against Elo
    chart = {}
    for t in TOUR:
        for w, _ in WINDOWS:
            rec = raw[t][w]["systems"]
            chart[f"{t}|{w}"] = [{"s": s, "name": SHORT.get(s, names[s]), "imp": rec[s]["better_than_elo"], "lo": rec[s]["block_lo"],
                                  "hi": rec[s]["block_hi"], "n": raw[t][w]["n_all"]} for s in systems]
            rec_o = rec
            chart[f"{t}|{w}|odds"] = [{"s": s, "name": SHORT.get(s, names[s]), "imp": rec_o[s]["better_than_elo_odds"],
                                       "lo": rec_o[s]["odds_block_lo"], "hi": rec_o[s]["odds_block_hi"],
                                       "n": raw[t][w]["n_odds"]} for s in systems]
    seg_w = "".join(f'<button type="button" data-rsw="{esc(w)}" aria-pressed="{"true" if w == W19 else "false"}">{esc(lab.split(" (")[0])}</button>'
                    for w, lab in WINDOWS)
    seg_p = ('<button type="button" data-rsp="all" aria-pressed="true">Every evaluation match</button>'
             '<button type="button" data-rsp="odds" aria-pressed="false">Matches with odds</button>')
    parts.append(f'''    <div class="panel" id="rs-forest">
      <div class="panel-head"><h3>Each system against surface Elo</h3><p>milli-log-loss better (+) or worse (−) than Elo
      on the same matches; 95% intervals clustered by four-week blocks</p></div>
      <div class="controls"><span>Seasons</span><span class="seg">{seg_w}</span><span>Matches</span><span class="seg">{seg_p}</span></div>
      <div class="chart-pair" id="rs-forest-charts"></div>
      <details class="twin"><summary>The numbers</summary><div class="table-wrap"><table class="num" id="rs-forest-table">
        <thead><tr><th>System</th><th class="r">Men</th><th class="r">95% interval</th><th class="r">Women</th><th class="r">95% interval</th></tr></thead>
        <tbody></tbody></table></div></details>
    </div>''')

    # ------------------------------------------------------------------ the coin-to-market ladder
    lad = S["ladder_2022_2026"]
    rungs = [("elo", "Surface Elo (the base so far)")] + [(s, names[s]) for s in LEAD] + [("market", "Bookmakers' closing prices")]
    boxes = []
    for t in TOUR:
        cells = []
        for k, name in rungs:
            v = lad[t].get(k)
            if v is None:
                continue
            cells.append(f'<span>{esc(name)}</span><div class="track"><div class="fill{" market" if k == "market" else ""}" '
                         f'style="width:{max(0.0, min(100.0, 100 * v)):.1f}%"></div></div><span class="val">{pc(v)}</span>')
        boxes.append(f'<div><h4 style="margin:0 0 8px">{TOUR[t]}</h4><div class="ladder">{"".join(cells)}</div></div>')
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>How far each rating gets, from a coin flip to the bookmakers</h3><p>Main-tour matches
      with odds, 2022–2026: {raw["atp"][W22]["n_odds"]:,} men's and {raw["wta"][W22]["n_odds"]:,} women's</p></div>
      <p class="note-small" style="margin:0 0 12px">A coin flip is 0% and the bookmakers' closing prices are 100%, on
      log loss. The ratings stand alone here, with no features added.</p>
      <div class="chart-pair">{"".join(boxes)}</div>
    </div>''')

    # ------------------------------------------------------------------ orthogonality
    def orow(label, key, since="2022"):
        cells = []
        for t in TOUR:
            for b in ("glicko_cs", "ttt"):
                r = orth[t][since]["bases"].get(b, {}).get(key)
                cells.append(f'<td class="r">{mm(r["gain"]) if r else "–"}<br><small class="muted">{rng(r["lo"], r["hi"]) if r else ""}</small></td>')
        return f'<tr><td>{esc(label)}</td>{"".join(cells)}</tr>'
    ell = {t: orth[t]["2022"]["elo_full_vs_calibrated"] for t in TOUR}
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>Is a better rating still orthogonal to the promising features?</h3><p>The feature-alpha
      audit's ladder with each rating in Elo's place; scored 2022–2026, calendar-week intervals</p></div>
      <p class="note-small" style="margin:0 0 10px">The audit's full model adds the serve-and-return ratings, the two-week
      opponent-adjusted points won, the short-memory IOS matchup, the games-weighted Elo, recent sets, the first matches
      on a surface and age to a base rating; with Elo as the base it gains {mm(ell["atp"]["gain"])} (men) and
      {mm(ell["wta"]["gain"])} (women) on calibrated Elo.</p>
      <div class="table-wrap"><table class="wide num"><thead><tr><th>milli-log-loss</th>
        <th class="r">Men, correlated-surface Glicko</th><th class="r">Men, TrueSkill Through Time</th>
        <th class="r">Women, correlated-surface Glicko</th><th class="r">Women, TrueSkill Through Time</th></tr></thead><tbody>
        {orow("The rating alone, against calibrated Elo", "calibrated_vs_elo_calibrated")}
        {orow("Plus serve-and-return ratings, against the same with Elo", "sr_vs_elo_sr")}
        {orow("The full model, against the full model with Elo", "full_vs_elo_full")}
        {orow("The full model with both ratings, against the full model with Elo", "both_full_vs_elo_full")}
      </tbody></table></div>
    </div>''')

    # ------------------------------------------------------------------ the closing line, men
    def mrow(label, model, comp, window="2019-2026"):
        cells = []
        for market in ("p_ps_a", "p_avg_a"):
            r = mk.get(market, {}).get(window, {}).get(model, {}).get(comp)
            cells.append(f'<td class="r">{mm(r["gain"]) if r else "–"}<br><small class="muted">{rng(r["lo"], r["hi"]) if r else ""}</small></td>')
        return f'<tr><td>{esc(label)}</td>{"".join(cells)}</tr>'
    n_mk = mk.get("p_ps_a", {}).get("2019-2026", {}).get("profile", {}).get("calibrated_market", {}).get("n")
    mrows = [mrow("Surface Elo", "rating_elo", "calibrated_market")]
    mrows += [mrow(names[s], f"rating_{s}", "calibrated_market") for s in LEAD]
    mrows += [mrow("The men's 16-input statistics profile (the audit's lead)", "profile", "calibrated_market"),
              mrow("The profile plus correlated-surface Glicko, against the profile", "profile_rating_glicko_cs", "profile"),
              mrow("The profile plus TrueSkill Through Time, against the profile", "profile_rating_ttt", "profile")]
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>Against the closing line (men)</h3><p>Gain over the calibrated closing price, 2019–2026,
      {f"{n_mk:,}" if n_mk else "–"} matches with both prices; calendar-week intervals</p></div>
      <div class="table-wrap"><table class="num"><thead><tr><th>Added to the closing price</th><th class="r">Pinnacle</th>
        <th class="r">Average of books</th></tr></thead><tbody>{"".join(mrows)}</tbody></table></div>
      <p class="note-small" style="margin:10px 0 0">The audit's own machinery: the market's log-odds unpenalised, a ridge on
      the rest chosen from the two preceding seasons, Pinnacle and the average on the same matches.</p>
    </div>''')

    # ------------------------------------------------------------------ the literature and what next
    parts.append('''    <div class="panel">
      <div class="panel-head"><h3>What the published evidence says</h3><p><a href="../../research/rating-systems/README.md">docs/research/rating-systems</a></p></div>
      <ul class="plain">
        <li><b>Reported.</b> No peer-reviewed tennis study compares Glicko-2 with Elo. Glicko-1 ties Elo in the two
        peer-reviewed tennis tests (ATP 2018–19; WTA 2022), and TrueSkill ties or slightly beats a constant-K Elo.</li>
        <li><b>Reported.</b> The largest published gain over Elo comes from smoothing (TrueSkill Through Time, KickScore):
        about 0.011 nats per match, but against a constant-K Elo without a surface model, and never against odds.</li>
        <li><b>Reported.</b> A surface model is the most consistent extension. No study shows any rating beating the
        bookmakers, and none tests a rating against closing odds.</li>
      </ul>
    </div>''')
    data = {"tours": [[t, TOUR[t]] for t in TOUR], "chart": chart, "windows": [w for w, _ in WINDOWS]}
    return {"html": "\n".join(parts), "data": data, "script": JS}


JS = r"""
(function () {
  const D = window.REPORT["summary"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const f2 = v => v == null ? "–" : (v < 0 && Math.abs(v).toFixed(2) !== "0.00" ? "−" : "+") + Math.abs(v).toFixed(2);
  const host = document.getElementById("rs-forest-charts");
  const tbody = document.querySelector("#rs-forest-table tbody");
  let win = "2019-2026", pop = "all";
  function draw() {
    host.replaceChildren(); tbody.replaceChildren();
    const key = t => t + "|" + win + (pop === "odds" ? "|odds" : "");
    let lo = -1, hi = 1;
    D.tours.forEach(([t]) => (D.chart[key(t)] || []).forEach(r => { [r.lo, r.hi, r.imp].forEach(v => { if (v != null) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }); }));
    const span = hi - lo, step = span <= 4 ? 0.5 : span <= 10 ? 1 : 2;
    lo = Math.floor(lo / step) * step; hi = Math.ceil(hi / step) * step;
    D.tours.forEach(([t, name]) => {
      const rows = D.chart[key(t)] || [];
      const box = el("div", "chart"); box.appendChild(el("h4", null, name));
      const W = 470, L = 196, R = 12, T = 6, B = 34, rowH = 24;
      const H = T + rows.length * rowH + B;
      const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
        "aria-label": name + ": each rating's log loss against surface Elo with 95% intervals; the table holds the numbers" });
      const x = v => L + (W - L - R) * (v - lo) / (hi - lo);
      for (let v = lo; v <= hi + 1e-9; v += step) {
        const vv = Math.round(v * 100) / 100;
        S("line", { x1: x(vv), x2: x(vv), y1: T, y2: H - B, class: vv === 0 ? "ref" : "grid" }, svg);
        S("text", { x: x(vv), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = (vv < 0 ? "−" : vv > 0 ? "+" : "") + Math.abs(vv);
      }
      S("text", { x: (L + W - R) / 2, y: H - 3, "text-anchor": "middle" }, svg).textContent = "better than Elo (+) or worse (−), milli-log-loss";
      rows.forEach((r, i) => {
        const yc = T + i * rowH + rowH / 2;
        S("text", { x: L - 8, y: yc + 4, "text-anchor": "end", class: "lab" }, svg).textContent = r.name;
        if (r.lo != null && r.hi != null) S("line", { x1: x(r.lo), x2: x(r.hi), y1: yc, y2: yc, stroke: "var(--ink-2)", "stroke-width": 1.5 }, svg);
        S("circle", { cx: x(r.imp), cy: yc, r: 5, fill: "var(--series-1)", stroke: "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
        const hit = S("rect", { x: 0, y: T + i * rowH, width: W, height: rowH, class: "hit" }, svg);
        window.reportTip.bind(hit, () => [f2(r.imp) + " milli-log-loss against Elo", r.name + " · " + name,
          "95% interval " + f2(r.lo) + " to " + f2(r.hi), Math.round(r.n).toLocaleString("en-US") + " matches"]);
      });
      box.appendChild(svg); host.appendChild(box);
    });
    const byS = {};
    D.tours.forEach(([t]) => (D.chart[key(t)] || []).forEach(r => { (byS[r.s] = byS[r.s] || { name: r.name })[t] = r; }));
    Object.values(byS).forEach(r => {
      const tr = el("tr");
      tr.appendChild(el("td", null, r.name));
      D.tours.forEach(([t]) => {
        const v = r[t];
        tr.appendChild(el("td", "r", v ? f2(v.imp) : "–"));
        tr.appendChild(el("td", "r", v ? f2(v.lo) + " to " + f2(v.hi) : "–"));
      });
      tbody.appendChild(tr);
    });
  }
  const seg = (attr, fn) => document.querySelectorAll(`#rs-forest [${attr}]`).forEach(b => b.addEventListener("click", () => {
    document.querySelectorAll(`#rs-forest [${attr}]`).forEach(o => o.setAttribute("aria-pressed", String(o === b)));
    fn(b.getAttribute(attr));
  }));
  seg("data-rsw", v => { win = v; draw(); });
  seg("data-rsp", v => { pop = v; draw(); });
  draw();
})();
"""
