"""Report section for Stage A of "ideas borrowed from UFC-predictions": the Bradley-Terry rating (BT) against Elo and
the market, what BT absorbs of the earlier study's leading features, and the market-embedded skill rating (MESR).

Contract (as the predictability diagnostic's report sections): SECTION and render(study_dir) -> {"html", "data",
"script"}. Every number is read from stageA_summary.json (the comparisons, the harness rows side by side, the
ratings' constants, checks and probes) in study_dir (data/studies/ufc_ideas/); the page shell's CSS classes are
src/eda/predictability_diagnostic/report_shell.html's.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

SECTION = {"stage": "A", "id": "stage-a", "title": "A Bradley–Terry rating and a market rating"}

TOUR = {"atp": "ATP (men)", "wta": "WTA (women)"}
HEAD = "2022-2026 (headline)"
WIN_WORDS = {"2013-2026": "2013–2026", "2013-2018 (tuning)": "2013–2018 (tuning)", "2019-2026": "2019–2026",
             HEAD: "2022–2026"}
ERA_WORDS = {"2013-16": "2013–16", "2017-19": "2017–19", "2020-21": "2020–21", "2022-26": "2022–26"}
LEADER_IDS = ["rating_matchup", "elo_games", "sets_14d", "mu_points", "age", "surface_first"]
MESR_IDS = ["mesr", "mesr_minus_bt", "mesr_minus_elo", "bt", "elo", "bt_games", "bt_nodecay", "bt_surface",
            "bt_plus_ratings"]


def esc(x) -> str:
    return html.escape(str(x))


def n(x) -> str:
    return f"{int(round(x)):,}"


def ll3(x) -> str:
    return "–" if x is None else f"{x:.3f}"


def mm(x, d=2) -> str:
    return "–" if x is None else f"{x:+.{d}f}"


def pct(x) -> str:
    return "–" if x is None else f"{100 * x:.0f}%"


def pair_tile(label, atp, wta, note) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(label)}</div><div class="pair">'
            f'<div><small>ATP</small><div class="value">{atp}</div></div>'
            f'<div><small>WTA</small><div class="value">{wta}</div></div></div><div class="note">{note}</div></div>')


def score_cell(row: dict, s: str, dirn: bool = True) -> str:
    """'+1.23 (0.98 to 1.47)' with a mark when the score clears the family-wide line; '–' when not scored."""
    sc = row.get(s)
    if not sc or sc.get("imp") is None:
        return '<td class="r">–</td>'
    tag = " ★" if sc.get("clears_line") else (" ·" if sc.get("above_band") else "")
    tip = (f' title="null band {sc["band_min"]:+.2f} to {sc["band_max"]:+.2f}; {n(sc["scored"])} matches"'
           if sc.get("band_min") is not None and sc.get("scored") else "")
    rng = f'<br><small class="muted">{sc["lo"]:+.2f} to {sc["hi"]:+.2f}</small>' if sc.get("lo") is not None else ""
    return f'<td class="r"{tip}>{mm(sc["imp"])}{tag}{rng}</td>'


def render(study_dir: Path) -> dict:
    S = json.loads((Path(study_dir) / "stageA_summary.json").read_text(encoding="utf-8"))
    R = S["ratings"]
    raw, era, lvl, cal = S["raw"], S["by_era"], S["by_level"], S["calibration_2019_2026"]
    gap = S["gap_closed_2022_2026"]
    rows = {(r["tour"], r["id"]): r for r in S["side_by_side"]}
    H = {t: raw[t][HEAD]["odds"] for t in TOUR}
    parts = []

    # ------------------------------------------------------------------ intro and tiles
    parts.append(f'''    <div class="prose">
      <p>The owner's UFC models rate fighters with a tuned <b>Bradley–Terry rating</b> (BT): at every week, every earlier
      result is re-solved at once, older results weigh less (a half-life), and a ridge pulls each rating toward zero, or a
      newcomer toward a lower <i>anchor</i>. A win is credited at what the opponent turned out to be worth, where Elo
      credits it at what the opponent was worth that day. Here BT is built from wins and losses alone, with the same time
      rule as Stage 1's Elo, tuned on 2013–2018 and frozen. The <b>market-embedded skill rating</b> (MESR) is the same idea
      solved from closing odds instead of results. Every forecast is scored by log loss (a coin scores
      {S["coin"]:.3f}; lower is better; one milli-log-loss is 0.001).</p>
    </div>
    <div class="tiles" role="list">
      {pair_tile("BT, matches with odds, 2022–2026", ll3(H["atp"]["ll"]["bt"]), ll3(H["wta"]["ll"]["bt"]),
                 f"log loss; {n(H['atp']['n'])} and {n(H['wta']['n'])} tour-level main-draw matches")}
      {pair_tile("Surface Elo, same matches", ll3(H["atp"]["ll"]["elo"]), ll3(H["wta"]["ll"]["elo"]), "Stage 1's rating")}
      {pair_tile("Closing odds, same matches", ll3(H["atp"]["ll"]["market"]), ll3(H["wta"]["ll"]["market"]),
                 "the bookmakers' average, margin removed")}
      {pair_tile("Elo-to-market gap BT closes", pct(gap["atp"]["bt"]), pct(gap["wta"]["bt"]),
                 "(Elo − BT) / (Elo − market), matches with odds, 2022–2026; negative: BT is further from the market than Elo")}
    </div>''')

    # ------------------------------------------------------------------ per tour
    blocks = []
    for t in TOUR:
        # BT against Elo by window, era, level
        def line(label, c):
            a, o = c["all"], c["odds"]
            d = a.get("elo_minus_bt", {})
            dr = '<span class="tag">under 300</span>' if a.get("directional_only") else ""
            share = "–*" if o.get("directional_only") else pct(o["gap_closed"]["bt"]) if o.get("n") else "–"
            oc = (f'<td class="r">{n(o["n"])}</td><td class="r">{ll3(o["ll"]["bt"])}</td><td class="r">{ll3(o["ll"]["elo"])}</td>'
                  f'<td class="r">{ll3(o["ll"]["market"])}</td><td class="r">{share}</td>') if o.get("n") else '<td class="r">–</td>' * 5
            return (f'<tr><td>{esc(label)}{dr}</td><td class="r">{n(a["n"])}</td><td class="r">{ll3(a["ll"].get("bt"))}</td>'
                    f'<td class="r">{ll3(a["ll"].get("elo"))}</td><td class="r">{mm(d.get("milli"))}<br><small class="muted">'
                    f'{d.get("lo", 0):+.2f} to {d.get("hi", 0):+.2f}</small></td>{oc}</tr>')
        trs = [line(WIN_WORDS[w], raw[t][w]) for w in WIN_WORDS]
        trs += ['<tr class="group"><td colspan="10">By era</td></tr>'] + [line(ERA_WORDS[e], era[t][e]) for e in ERA_WORDS]
        trs += ['<tr class="group"><td colspan="10">By level, 2013–2026</td></tr>']
        trs += [line(S["level_groups"][g], lvl[t][g]) for g in S["level_groups"] if lvl[t][g]["all"]["n"]]
        dg = S["diagnostics"][t]

        def drows(title, block_, unit=""):
            return (f'<tr class="group"><td colspan="3">{esc(title)}</td></tr>'
                    + "".join(f'<tr><td>{esc(k)}{unit}</td><td class="r">{n(v["n"])}</td><td class="r">{mm(v["milli"])}'
                              f'{"*" if v["directional_only"] else ""}</td></tr>' for k, v in block_.items() if v["n"]))
        wtr = (drows("The less experienced player's edges in BT's snapshot", dg["fewest_snapshot_edges"])
               + drows("The longer layoff of the two (days since the previous date played)", dg["longest_layoff_days"])
               + drows("Grand Slam qualifying, by round", dg["grand_slam_qualifying_by_round"]))
        cb = cal[t]
        ctr = "".join(f'<tr><td>{esc(b["bin"])}</td><td class="r">{n(b["n"])}</td><td class="r">{100 * b["mean_forecast"]:.1f}%</td>'
                      f'<td class="r">{100 * b["won"]:.1f}%</td><td class="r">{n(e_["n"])}</td><td class="r">{100 * e_["mean_forecast"]:.1f}%</td>'
                      f'<td class="r">{100 * e_["won"]:.1f}%</td></tr>'
                      for b, e_ in zip(cb["bt"]["bins"], cb["elo"]["bins"]) if b["n"] and e_["n"])
        # the leaders given Elo, BT, MESR and the market
        ltr = []
        for cid in LEADER_IDS:
            r = rows.get((t, cid))
            if r:
                ltr.append(f'<tr><td>{esc(r["name"])}{" (" + esc(r["form"]) + ")" if r["form"] != "single" else ""}'
                           f'<br><small class="muted">from {r["scored_from"]}</small></td>'
                           f'{score_cell(r, "elo")}{score_cell(r, "bt")}{score_cell(r, "mesr")}{score_cell(r, "market")}</tr>')
        mtr = []
        for cid in MESR_IDS:
            r = rows.get((t, cid))
            if r:
                mtr.append(f'<tr><td>{esc(r["name"])}</td>{score_cell(r, "alone")}{score_cell(r, "elo")}{score_cell(r, "bt")}'
                           f'{score_cell(r, "mesr")}{score_cell(r, "market")}</tr>')
        lines = S["lines"]
        lw = ", ".join(f'{s} {lines[f"{t}|{s}"]["line"]:.1f}' for s in ("elo", "bt", "mesr", "market") if f"{t}|{s}" in lines)
        blocks.append(f'''      <div data-tour="{t}"{"" if t == "atp" else " hidden"}>
      <div class="panel">
        <div class="panel-head"><h3>BT against surface Elo, {esc(TOUR[t])}</h3><p>Log loss, lower is better; the last
        five columns are the matches with closing odds</p></div>
        <div class="table-wrap"><table class="num wide">
          <thead><tr><th></th><th class="r">Matches</th><th class="r">BT</th><th class="r">Elo</th><th class="r">BT better
          by (milli)</th><th class="r">With odds</th><th class="r">BT</th><th class="r">Elo</th><th class="r">Market</th>
          <th class="r">Gap closed</th></tr></thead>
          <tbody>{"".join(trs)}</tbody></table></div>
        <p class="note-small">BT better by: Elo's log loss minus BT's, milli-log-loss, with its 95% range from the per-match
        differences (negative: BT worse). Gap closed: (Elo − BT) / (Elo − market), not shown (–*) under 300 matches with
        odds, where the room to the market is too small to divide by.</p>
        <details class="twin"><summary>Calibration, 2019–2026 (ten bins of the forecast that A wins)</summary>
          <div class="table-wrap"><table class="num"><thead><tr><th>Forecast</th><th class="r">BT matches</th>
          <th class="r">BT said</th><th class="r">A won</th><th class="r">Elo matches</th><th class="r">Elo said</th>
          <th class="r">A won</th></tr></thead><tbody>{ctr}</tbody></table></div>
          <p class="note-small">Calibration slope (1 is perfect; below 1, too confident): BT {cb["bt"]["slope"]:.3f}
          ({cb["bt"]["slope_lo"]:.3f} to {cb["bt"]["slope_hi"]:.3f}), Elo {cb["elo"]["slope"]:.3f}
          ({cb["elo"]["slope_lo"]:.3f} to {cb["elo"]["slope_hi"]:.3f}).</p></details>
        <details class="twin"><summary>Where BT loses to Elo (evaluation matches, 2013–2026)</summary>
          <div class="table-wrap"><table class="num"><thead><tr><th></th><th class="r">Matches</th>
          <th class="r">BT better by (milli)</th></tr></thead><tbody>{wtr}</tbody></table></div>
          <p class="note-small">A player with no edge in the snapshot is rated at the newcomer anchor. * under 300 matches,
          directional only.</p></details>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>What BT absorbs: the earlier leaders, {esc(TOUR[t])}</h3><p>Milli-log-loss better than
        the base alone, all scored seasons, with the 95% range</p></div>
        <div class="table-wrap"><table class="num wide"><thead><tr><th>Earlier leader</th><th class="r">Given Elo</th>
        <th class="r">Given BT</th><th class="r">Given MESR</th><th class="r">Given the market</th></tr></thead>
        <tbody>{"".join(ltr)}</tbody></table></div>
        <p class="note-small">★ clears the family-wide line (the multiple-comparison guard: {esc(lw)} standard deviations of
        the shuffled copies); · above its own null band only. Hover a cell for the band. Given MESR: the matches where both
        players have an MESR, Challengers and qualifying included, where MESR alone is a much weaker base than Elo, so
        most rows add a lot to it.</p>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>The ratings as features, {esc(TOUR[t])}</h3><p>Each row added to each base, milli-log-loss
        better than the base alone</p></div>
        <div class="table-wrap"><table class="num wide"><thead><tr><th>Row</th><th class="r">Alone (vs a coin)</th>
        <th class="r">Given Elo</th><th class="r">Given BT</th><th class="r">Given MESR</th><th class="r">Given the market</th>
        </tr></thead><tbody>{"".join(mtr)}</tbody></table></div>
      </div>
      </div>''')
    parts.append(f'''    <div class="sub">
      <h3>By tour</h3>
      <div class="controls"><span>Tour:</span><div class="seg" role="group" aria-label="Tour">
        <button type="button" data-t="atp" aria-pressed="true">ATP (men)</button>
        <button type="button" data-t="wta" aria-pressed="false">WTA (women)</button></div></div>
{"".join(blocks)}
    </div>''')

    # ------------------------------------------------------------------ constants and checks
    ch, fl, ck = R["chosen"], R["flatness"], R["checks"]

    def hl(v):
        return "no decay" if v in (None, "none") else f"{v:g} years"
    con = "".join(
        f'<li><b>{esc(TOUR[t])}.</b> BT: half-life {hl(ch[t]["bt"]["half_life"])}, λ {ch[t]["bt"]["lam"]:g}, anchor '
        f'{ch[t]["bt"]["anchor"]:g}, retirement weight {ch[t]["bt"]["ret_w"]:g}; {fl[t]["bt_all"]["within_1_milli"]} of the '
        f'{fl[t]["bt_all"]["settings"]} settings tried within 1 milli-log-loss of the best. Surface BT: λ<sub>u</sub> '
        f'{ch[t]["bt_surface_lam_u"]:g}. MESR: half-life {ch[t]["mesr"]["half_life"]:g} years, λ {ch[t]["mesr"]["lam"]:g}, anchor '
        f'{ch[t]["mesr"]["anchor"]:g}; root-mean-square gap to the closing log-odds 2019–2026 '
        f'{R["mesr_rms_gap_chosen"][t]["rms_gap_2019_2026"]:.3f}.</li>' for t in TOUR)
    pt = S["probe_totals"]
    slice_from = R["probes"][0]["slice_from"][:4]
    top ="; ".join(f'{esc(TOUR[t])}: ' + esc(", ".join(p["name"] for p in R["top10_2026"][t]["players"][:5])) for t in TOUR)
    parts.append(f'''    <div class="sub">
      <h3>Constants and checks</h3>
      <ul class="plain">{con}
        <li><b>Probes</b> cut by date, event and round ({pt["cuts_real"]} cuts on the matches from {esc(slice_from)}, BT,
        its variants and MESR): {n(pt["protected_changed_real"])} of {n(pt["protected_checked_real"])} protected pre-match
        values changed. A deliberately leaky BT (snapshots that see their own date) changed
        {n(pt["protected_changed_leaky"])}.</li>
        <li><b>Reproduced.</b> Stage 1's Elo and market log losses ({S["stage1_reproduced"]["checked"]} numbers, largest
        difference {S["stage1_reproduced"]["max_abs_difference"]:.1e}) and the earlier ranking's scores of the leaders
        (largest difference {S["stage4_reference_reproduced"]["max_abs_difference"]:.1e}).</li>
        <li><b>Solver.</b> The tuning pass equals the frozen pass's first years (largest difference
        {max(ck[t]["tuning_pass_vs_full_pass_prefix_max_abs"] for t in TOUR):.1e}); a solve with tight tolerances moves no
        rating by more than {max(ck[t]["standard_vs_tight_tolerance_max_abs"] for t in TOUR):.1e}.</li>
        <li><b>Highest rated at the end of the table</b> (top five): {top}.</li>
      </ul>
    </div>''')
    return {"html": "\n".join(parts), "data": {"tours": list(TOUR)}, "script": JS}


JS = r"""
(function () {
  const root = document.getElementById("stage-a");
  if (!root) return;
  root.querySelectorAll('.seg button[data-t]').forEach(b => b.addEventListener("click", () => {
    root.querySelectorAll('.seg button[data-t]').forEach(o => o.setAttribute("aria-pressed", String(o === b)));
    root.querySelectorAll('[data-tour]').forEach(d => { d.hidden = d.dataset.tour !== b.dataset.t; });
  }));
})();
"""
