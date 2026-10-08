"""Report section for the summary, at the top of the page: what the study found, for a reader who is skimming.

What it holds, in order: three takeaways; how far each forecaster gets from a coin flip to the bookmakers' prices;
every family of features tried, with how much of Elo's gap to the bookmakers each closes; which match statistics are
skill and which are luck (the chart of persistence against match impact); how much of a match anyone can predict;
what to do next; the decisions for the owner.

Every number comes from summary_results.json, which copies or re-expresses the stages' outputs (render_report.py
assembles the page and puts this section before the stages).
"""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

SECTION = {"stage": "summary", "id": "summary", "title": "What we found"}

TOUR = {"atp": "ATP", "wta": "WTA"}
TOUR_LONG = {"atp": "Men (ATP)", "wta": "Women (WTA)"}
SEX = {"atp": "men", "wta": "women"}
CORNER_ORDER = ["trait", "style", "luck", "noise"]
CORNER_WORDS = {"trait": ["Skill", "consistent and decisive"], "style": ["Habit", "consistent, rarely decisive"],
                "luck": ["Luck", "decisive, not consistent"], "noise": ["Noise", "neither"]}
# what each family's result means, in a few words
NOTES = {
    "ratings": "They see every point, not just who won.",
    "points": "The last 12 months help; career averages do not.",
    "workload": "It means a player is still winning: form, not fatigue.",
    "margin": "Mostly the margin of the latest match.",
    "surface": "Players start a new surface worse than Elo expects.",
    "age": "Older men do worse than Elo expects.",
    "rankings": "A flaw in the test's early seasons hides them; since 2022 they add a little.",
    "length": "Already inside the strength ratings.",
    "style": "Habits, not match-winners.",
    "clutch": "Luck: a good tiebreak record even predicts slightly worse results.",
    "results": "Elo is already made of wins and losses.",
    "h2h": "",
    "background": "Tiny effects, for the men only.",
}


def esc(x) -> str:
    return html.escape(str(x))


def num(x) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def n0(x) -> str:
    v = num(x)
    return "–" if v is None else f"{int(round(v)):,}"


def pc(x) -> str:
    """A share as a percentage: whole numbers, one decimal under 10%... under 1%."""
    v = num(x)
    if v is None:
        return "–"
    return f"{100 * v:.1f}%" if abs(v) < 0.01 else f"{100 * v:.0f}%"


def width(x) -> str:
    """A bar's width in percent, for the style attribute ('%' formatting, which the number check does not tag)."""
    v = max(0.0, min(1.0, num(x) or 0.0))
    return "%.1f" % (100 * v)


def tag(k: str) -> str:
    return f'<span class="ktag">{esc(k)}</span>'


def kick(k: str) -> str:
    """The label above a takeaway's headline."""
    return f'<span class="ktag" style="display:block;margin:0 0 4px">{esc(k)}</span>'


def load(study_dir: Path, name: str) -> dict:
    return json.loads((study_dir / name).read_text(encoding="utf-8"))


def shown(s: str) -> str:
    """A printed figure as the page shows it: without the invisible marks the number check (summary_number_check.py)
    adds to name each number's source, so its tagged page reads as the real one."""
    return re.sub("⁣\\d+⁣", "", s)


def both(atp: str, wta: str, tail: str = "") -> str:
    """One figure when the two tours print alike, else the men's and the women's."""
    return f"{atp}{tail}" if shown(atp) == shown(wta) else f"{atp} (men) and {wta} (women)"


def words(items: list[str]) -> str:
    items = list(items)
    return "".join(items) if len(items) <= 1 else ", ".join(items[:-1]) + " and " + items[-1]


def size_word(share: float) -> str:
    v = num(share) or 0
    return "the best" if v >= 0.15 else "yes" if v >= 0.05 else "a little" if v >= 0.02 else "negligible"


def render(study_dir: Path) -> dict:
    res = load(study_dir, "summary_results.json")
    q, pl = res["quoted"], res["plain"]
    q2, q4 = q["stage2"], q["stage4"]
    lad, fams = pl["ladder"], pl["families"]
    pts = res["chart"]["points"]
    split = q2["split_2022_2026_with_odds"]
    ratings = next(f for f in fams if f["key"] == "ratings")
    r_share = {t: ratings["tours"][t]["best"]["share_of_gap"] for t in TOUR}
    mkt_best = max(pl["best_market"][t]["market_share"] for t in TOUR)
    versions = sum(pl["versions"].values())

    # ------------------------------------------------------------------ the takeaways
    parts = [f'''    <div class="prose">
      <p class="lede" style="margin-top:0">Can information known before a tennis match predict the winner better than an Elo
      rating, and better than the bookmakers' closing prices? We tested {pl["candidates"]} candidate features ({versions:,}
      versions in all) on {n0(q4["pool_evaluation"]["atp"])} men's and {n0(q4["pool_evaluation"]["wta"])} women's professional
      matches from 2013 to 2026, always predicting each season from earlier seasons only.</p>
    </div>
    <div class="takeaways" role="list">
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">The bookmakers stay ahead</span>
        <p>No feature improves on their closing prices by more than {pc(mkt_best)} of the way from a coin flip to their
        prices: far too little to bet on.</p></div>
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">A few things beat Elo, modestly</span>
        <p>Serve-and-return strength ratings do best: they close about {both(pc(r_share["atp"]), pc(r_share["wta"]))} of the
        gap between Elo and the bookmakers. Recent form, recent workload and a new surface add less.</p></div>
      <div class="takeaway" role="listitem">{kick("inferred")}<span class="head">Pre-match records look priced in</span>
        <p>If there is an edge, it is more likely in live (in-play) data, or in markets less sharp than the bookmakers'
        closing prices.</p></div>
    </div>''']

    # ------------------------------------------------------------------ the ladder
    rungs = [("ranking", "Official ranking"), ("elo", "Elo rating"), ("elo_plus_best", "Elo + the best new feature"),
             ("market", "Bookmakers' closing prices")]
    boxes = []
    for t in TOUR:
        cells = "".join(f'<span>{esc(name)}</span><div class="track"><div class="fill{" market" if k == "market" else ""}" '
                        f'style="width:{width(lad[t][k])}%"></div></div><span class="val">{pc(lad[t][k])}</span>'
                        for k, name in rungs)
        boxes.append(f'<div><h4 style="margin:0 0 8px">{TOUR_LONG[t]}</h4><div class="ladder">{cells}</div></div>')
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>How far each forecast gets, from a coin flip to the bookmakers</h3><p>Main-tour matches
      with bookmaker odds, 2022–2026</p></div>
      <p class="note-small" style="margin:0 0 12px">Forecasts are scored by how much probability they gave the player who
      actually won (log loss). On this scale a coin flip is 0% and the bookmakers' closing prices are 100%.</p>
      <div class="chart-pair">{"".join(boxes)}</div>
    </div>''')

    # ------------------------------------------------------------------ the families
    def share_of(f, t):
        x = f["tours"].get(t)
        return (x["best"]["share_of_gap"] if x and x["best"] else -1)
    order = sorted(fams, key=lambda f: -max(share_of(f, t) for t in TOUR))

    def cell(f, t):
        x = f["tours"].get(t)
        label = f'data-label="{SEX[t].capitalize()}"'
        if not x:
            return f'<td {label} class="muted">not played</td>'
        if x["verdict"] == "helps":
            b = x["best"]
            return (f'<td {label}><div class="meter"><div class="track"><div class="fill" style="width:{width(b["share_of_gap"])}%"></div></div>'
                    f'<span class="num">{pc(b["share_of_gap"])}</span><span class="word">{size_word(b["share_of_gap"])}</span></div></td>')
        return f'<td {label}><span class="word">{"no: reversed" if x["verdict"] == "reversed" else "no"}</span></td>'

    def market_cell(f):
        hits = [(t, f["tours"][t]["market"]) for t in TOUR if t in f["tours"] and f["tours"][t]["market"]]
        if not hits:
            return '<td data-label="Bookmakers" class="muted">no</td>'
        shares = [pc(m["market_share"]) for _, m in hits]
        who = "" if len(hits) == 2 else f', {SEX[hits[0][0]]} only'
        return f'<td data-label="Bookmakers">barely ({esc(shares[0] if len({shown(s) for s in shares}) == 1 else " and ".join(shares))}{who})</td>'

    rows = []
    for f in order:
        note = NOTES.get(f["key"], "")
        rows.append(f'<tr><td><b>{esc(f["title"])}</b><span class="what">{esc(f["what"][:1].upper() + f["what"][1:])}.'
                    f'{" " + esc(note) if note else ""}</span></td>{cell(f, "atp")}{cell(f, "wta")}{market_cell(f)}</tr>')
    parts.append(f'''    <div class="sub">
      <h3>What helps beyond Elo, and by how much</h3>
      <div class="panel">
        <div class="panel-head"><h3>Every family of features tried</h3><p>Share of the gap between Elo and the bookmakers
        that each family's best version closes, on main-tour matches</p></div>
        <div class="table-wrap"><table class="families">
          <thead><tr><th>What we tried</th><th>Men</th><th>Women</th><th>Beyond the bookmakers?</th></tr></thead>
          <tbody>{"".join(rows)}</tbody></table></div>
        <p class="note-small">Only versions that passed the study's strict test count: fitted on earlier seasons, tested on
        later ones, and better than chance across all {versions:,} tests. The families overlap, so their shares do not add up.
        Main tour: Grand Slams down to 250s, where bookmakers price matches. Each version's result is in Stage 4 below.</p>
      </div>
    </div>''')

    # ------------------------------------------------------------------ skill or luck
    corners = res["chart"]["corners"]
    skill = [p["short"].lower() for p in pts if p["tour"] == "atp" and p["corner_all"] == "trait"][:5]
    ptab = "".join(
        f'<tr><td>{esc(p["label"])}</td>' + "".join(
            f'<td class="r">{pc(x["reliability"])}</td><td class="r">{pc(x["impact_share"])}</td><td>{esc(CORNER_WORDS[x["corner_all"]][0])}</td>'
            for x in (next(y for y in pts if y["tour"] == t and y["stat"] == p["stat"]) for t in TOUR)) + "</tr>"
        for p in pts if p["tour"] == "atp")
    parts.append(f'''    <div class="sub">
      <h3>Which match statistics are skill, and which are luck</h3>
      <ul class="plain">
        <li>{tag("observed")} <b>Skill, top right:</b> {esc(words(skill))} are both consistent from season to season and
        decisive within a match. Useful features come from here.</li>
        <li>{tag("observed")} <b>Luck, left:</b> break points, tiebreaks, even a season's sets won swing with chance.
        <b>Habit, bottom right:</b> aces, double faults and first serves in are consistent but rarely decide a match.</li>
      </ul>
      <div class="panel">
        <div class="panel-head"><h3>Consistency against importance</h3><p>Each dot is a statistic measured in a match.
        Across: how much of a season's figure is the player rather than chance. Up: how much of the doubt about who won it
        removes in that match</p></div>
        <div class="chart-pair" id="sum-chart"></div>
        <details class="twin"><summary>Show the numbers as a table</summary><div class="table-wrap"><table class="num wide">
          <thead><tr><th rowspan="2">Statistic</th><th colspan="3">Men</th><th colspan="3">Women</th></tr>
          <tr><th class="r">Consistent</th><th class="r">Decides</th><th>Kind</th><th class="r">Consistent</th><th class="r">Decides</th><th>Kind</th></tr></thead>
          <tbody>{ptab}</tbody></table></div></details>
      </div>
    </div>''')

    # ------------------------------------------------------------------ the ceiling
    stacks = []
    for t in TOUR:
        s = split[t]
        segs = [("s1", s["known_before_share"], "known before"), ("s2", s["on_the_day_share"], "on the day"),
                ("s3", s["luck_share"], "scoring luck")]
        stacks.append(f'<div><h4 style="margin:0">{TOUR_LONG[t]}</h4><div class="stack">' + "".join(
            f'<span class="{c}" style="width:{width(v)}%" title="{esc(n)}">{pc(v)}</span>' for c, v, n in segs) + "</div></div>")
    parts.append(f'''    <div class="sub">
      <h3>How much of a match can anyone predict?</h3>
      <div class="panel">
        <div class="chart-pair">{"".join(stacks)}</div>
        <div class="legend" style="margin-top:8px">
          <span class="key"><span class="sw-rect" style="background:var(--seq-5)"></span>Known before the match (what the bookmakers price)</span>
          <span class="key"><span class="sw-rect" style="background:var(--seq-3)"></span>How the players play that day</span>
          <span class="key"><span class="sw-rect" style="background:var(--seq-1)"></span>Scoring luck</span>
        </div>
        <p class="note-small">Stage 2's estimate, from replaying every match point by point (main-tour matches with odds,
        2022–2026). Its method still awaits your approval.</p>
      </div>
      <p>{tag("inferred")} This decomposition is conditional on the iid point replay and its denoising assumptions.
      It does not establish a ceiling for perfect pre-match information, or prove that day-level performance is
      unknowable before play. Point-by-point information remains a separate hypothesis to test.</p>
    </div>''')

    # ------------------------------------------------------------------ next, and decisions
    parts.append(f'''    <div class="sub">
      <h3>What we suggest next</h3>
      <ul class="plain">
        <li>{tag("suggestion")} <b>Test the best features together.</b> One model with the strength ratings, recent points won
        and recent workload, checked against the bookmakers. The <a href="../feature_alpha_audit/repairs.html">repaired
        feature comparison</a> supersedes the original results. Failure of these features would not close the
        pre-match research route.</li>
        <li>{tag("suggestion")} <b>Try live (in-play) data.</b> Point observations may help update day-level performance
        estimates. Testing this needs time-stamped point data and live prices, which this study did not have.</li>
        <li>{tag("suggestion")} <b>Test against the market you would actually bet on.</b> Polymarket's tennis prices may be
        less sharp than the bookmakers' closing prices.</li>
        <li>{tag("suggestion")} <b>Fix the known data problems first.</b> Some players appear under two ids in 2026 and some
        lower-level scores are misread; the effects here are small, but any rebuild inherits them.</li>
      </ul>
    </div>
    <div class="sub">
      <h3>Decisions for you</h3>
      <ul class="plain">
        <li><b>Which features to carry forward.</b> Our suggestion: the strength ratings, recent points won and recent
        workload.</li>
        <li><b>What to do next:</b> the combined test, live data, or the Polymarket comparison.</li>
        <li><b>The open technical choices from the earlier stages</b>, listed in <a href="summary.md">summary.md</a>. Stage
        2's estimate of luck, quoted above, is one of them.</li>
      </ul>
      <p class="note-small">Every number on this page is checked against the study's data files by a script
      (<code>summary_number_check.py</code>); its latest result is in summary.md. The detail behind each finding is in the
      stages below. A study, not a decision.</p>
    </div>''')

    data = {"tours": [[t, TOUR_LONG[t]] for t in TOUR], "repeats": res["settings"]["repeats_line"],
            "decides": res["settings"]["decides_share_of_coin"],
            "corners": {c: CORNER_WORDS[c] for c in CORNER_ORDER},
            "points": {t: [{"stat": p["stat"], "label": p["label"], "short": p["short"], "rel": num(p["reliability"]),
                            "lo": num(p["reliability_lo"]), "hi": num(p["reliability_hi"]), "share": num(p["impact_share"]),
                            "corner": p["corner_all"], "border": p["borderline"]}
                           for p in pts if p["tour"] == t] for t in TOUR}}
    return {"html": "\n".join(parts), "data": data, "script": JS}


JS = r"""
(function () {
  const D = window.REPORT["summary"];
  const NS = "http://www.w3.org/2000/svg";
  const S = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const pc = v => v == null ? "–" : (100 * v).toFixed(0) + "%";
  const tip = (node, rows) => window.reportTip.bind(node, rows);
  const host = document.getElementById("sum-chart");
  const overlaps = (b, list) => list.some(o => b.x0 < o.x1 && b.x1 > o.x0 && b.y0 < o.y1 && b.y1 > o.y0);
  const area = (b, list) => list.reduce((s, o) => s + Math.max(0, Math.min(b.x1, o.x1) - Math.max(b.x0, o.x0)) * Math.max(0, Math.min(b.y1, o.y1) - Math.max(b.y0, o.y0)), 0);

  D.tours.forEach(([t, name]) => {
    const box = el("div", "chart"); box.appendChild(el("h4", null, name)); host.appendChild(box);
    const W = 460, H = 380, L = 46, R = 12, T = 12, B = 46;
    const svg = S("svg", { viewBox: `0 0 ${W} ${H}`, class: "viz", role: "img",
      "aria-label": name + ": how consistent each statistic is against how much it decides a match; the table below holds the numbers" }, box);
    const x = v => L + (W - L - R) * Math.max(0, Math.min(1, v));
    const y = v => T + (H - T - B) * (1 - Math.max(0, Math.min(1, v)));
    [0, 0.25, 0.5, 0.75, 1].forEach(v => {
      S("line", { x1: x(v), x2: x(v), y1: T, y2: H - B, class: v === 0 ? "axis" : "grid" }, svg);
      S("text", { x: x(v), y: H - B + 16, "text-anchor": "middle" }, svg).textContent = Math.round(v * 100) + "%";
      S("line", { x1: L, x2: W - R, y1: y(v), y2: y(v), class: v === 0 ? "axis" : "grid" }, svg);
      S("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end" }, svg).textContent = Math.round(v * 100) + "%";
    });
    S("text", { x: (L + W - R) / 2, y: H - 8, "text-anchor": "middle" }, svg).textContent = "consistent from season to season";
    S("text", { x: 12, y: (T + H - B) / 2, "text-anchor": "middle", transform: `rotate(-90 12 ${(T + H - B) / 2})` }, svg).textContent = "decides the match";
    S("line", { x1: x(D.repeats), x2: x(D.repeats), y1: T, y2: H - B, class: "ref", "stroke-width": 1.5 }, svg);
    S("line", { x1: L, x2: W - R, y1: y(D.decides), y2: y(D.decides), class: "ref", "stroke-width": 1.5 }, svg);

    const pts = D.points[t].map(p => ({ p, cx: x(p.rel), cy: y(p.share) }));
    pts.forEach(o => { if (o.p.lo != null && o.p.hi != null)
      S("line", { x1: x(o.p.lo), x2: x(o.p.hi), y1: o.cy, y2: o.cy, stroke: "var(--ink-2)", "stroke-width": 1 }, svg); });
    const dots = pts.map(o => ({ x0: o.cx - 7, y0: o.cy - 7, x1: o.cx + 7, y1: o.cy + 7 }));
    const whiskers = pts.filter(o => o.p.lo != null && o.p.hi != null).map(o => ({ x0: x(o.p.lo), y0: o.cy - 2, x1: x(o.p.hi), y1: o.cy + 2 }));
    const marks = dots.concat(whiskers);

    // the corners' names, in the first corner of their quadrant clear of every dot and whisker
    const taken = [];
    const xm = x(D.repeats), ym = y(D.decides);
    const quads = { trait: [xm, W - R, T, ym], luck: [L, xm, T, ym], style: [xm, W - R, ym, H - B], noise: [L, xm, ym, H - B] };
    const cornerOrder = { trait: ["tr", "br", "tl", "bl"], luck: ["tl", "bl", "tr", "br"], style: ["br", "tr", "bl", "tl"], noise: ["bl", "tl", "br", "tr"] };
    Object.keys(quads).forEach(key => {
      const [qx0, qx1, qy0, qy1] = quads[key];
      const [title, desc] = D.corners[key];
      const g = S("text", { class: "lab", "font-weight": "650" }, svg); g.textContent = title;
      const d = S("text", {}, svg); d.textContent = desc;
      const w = Math.max(g.getComputedTextLength(), d.getComputedTextLength()) + 4, h = 28;
      const spot = c => {
        const left = c[1] === "l", top = c[0] === "t";
        const x0 = left ? qx0 + 6 : qx1 - 6 - w, y0 = top ? qy0 + 4 : qy1 - 4 - h;
        return { x0, y0, x1: x0 + w, y1: y0 + h, left };
      };
      const cands = cornerOrder[key].map(spot);
      const b = cands.find(c => !overlaps(c, marks)) || cands[0];
      const anchor = b.left ? "start" : "end", ax = b.left ? b.x0 + 2 : b.x1 - 2;
      [[g, b.y0 + 11], [d, b.y0 + 24]].forEach(([n, yy]) => { n.setAttribute("x", ax); n.setAttribute("y", yy); n.setAttribute("text-anchor", anchor); });
      taken.push(b);
    });

    pts.forEach(o => {
      const dot = S("circle", { cx: o.cx, cy: o.cy, r: 5, fill: o.p.border ? "var(--surface)" : "var(--series-1)",
        stroke: o.p.border ? "var(--series-1)" : "var(--surface)", "stroke-width": 2, class: "mark", tabindex: "0" }, svg);
      const hit = S("circle", { cx: o.cx, cy: o.cy, r: 12, class: "hit" }, svg);
      const rowsFn = () => [o.p.label + " · " + name, pc(o.p.rel) + " consistent · decides " + pc(o.p.share),
        "kind: " + D.corners[o.p.corner][0].toLowerCase() + (o.p.border ? " (on the edge)" : "")];
      tip(hit, rowsFn); tip(dot, rowsFn);
    });

    // labels: each at the nearest spot clear of the marks and the labels already placed; a few orders tried, the tidiest kept
    const bounds = { x0: L + 2, y0: T, x1: W - 2, y1: H - B + 3 };
    const texts = pts.map(o => { const n = S("text", { x: 0, y: 0, class: "lab" }, svg); n.textContent = o.p.short; return n; });
    const widths = texts.map(n => n.getComputedTextLength());
    function layout(order) {
      const placed = taken.slice(), out = new Array(pts.length);
      let cost = 0;
      order.forEach(i => {
        const o = pts[i], w = widths[i];
        const others = marks.filter((_, j) => j !== i);
        let best = null, fallback = null;
        for (const d of [8, 14, 20, 28, 38, 50, 64, 80]) {
          const cands = [[o.cx + d, o.cy + 4, "start"], [o.cx - d, o.cy + 4, "end"], [o.cx, o.cy - d + 2, "middle"], [o.cx, o.cy + d + 9, "middle"],
            [o.cx + 0.7 * d, o.cy - 0.7 * d + 2, "start"], [o.cx - 0.7 * d, o.cy - 0.7 * d + 2, "end"],
            [o.cx + 0.7 * d, o.cy + 0.7 * d + 9, "start"], [o.cx - 0.7 * d, o.cy + 0.7 * d + 9, "end"]];
          for (const [lx, ly, anchor] of cands) {
            const x0 = anchor === "start" ? lx : anchor === "end" ? lx - w : lx - w / 2;
            const b = { x0: x0 - 1, y0: ly - 10, x1: x0 + w + 1, y1: ly + 2 };
            if (b.x0 < bounds.x0 || b.x1 > bounds.x1 || b.y0 < bounds.y0 || b.y1 > bounds.y1) continue;
            const hit = area(b, placed) + area(b, others);
            if (hit === 0) { best = { lx, ly, anchor, b, d, hit: 0 }; break; }
            if (!fallback || hit < fallback.hit) fallback = { lx, ly, anchor, b, d, hit };
          }
          if (best) break;
        }
        best = best || fallback;
        out[i] = best; placed.push(best.b);
        cost += 1000 * best.hit + best.d;
      });
      return { out, cost };
    }
    let order = pts.map((o, i) => [i, pts.filter(q => Math.hypot(q.cx - o.cx, q.cy - o.cy) < 40).length])
      .sort((a, b) => b[1] - a[1]).map(a => a[0]);
    let kept = layout(order);
    for (let k = 0; k < 8; k++) {
      const worst = kept.out.map((b, i) => [i, 1000 * b.hit + b.d]).sort((a, b) => b[1] - a[1])[0][0];
      if (order[0] === worst) break;
      order = [worst].concat(order.filter(i => i !== worst));
      const tried = layout(order);
      if (tried.cost < kept.cost) kept = tried;
    }
    kept.out.forEach((best, i) => {
      const o = pts[i];
      texts[i].setAttribute("x", best.lx); texts[i].setAttribute("y", best.ly); texts[i].setAttribute("text-anchor", best.anchor);
      if (best.d > 14) {
        const bx = Math.max(best.b.x0, Math.min(o.cx, best.b.x1)), by = Math.max(best.b.y0, Math.min(o.cy, best.b.y1));
        S("line", { x1: o.cx, y1: o.cy, x2: bx, y2: by, stroke: "var(--rule)", "stroke-width": 1 }, svg);
      }
    });
    svg.querySelectorAll("circle.mark, circle.hit").forEach(n => svg.appendChild(n));
  });
})();
"""
