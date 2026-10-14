"""Report section for Stage B of "ideas borrowed from UFC-predictions": opponent-adjusted statistics (adjperf, adjdef),
IOS ridge ratings per statistic, and performance split by the opponent's strength.

Every number comes from data/studies/ufc_ideas/stageB_summary.json (written by stageB_rundown.py); render_report.py
assembles the page. Contract: SECTION and render(study_dir) -> {"html", "data", "script"}.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": "B", "id": "stage-b", "title": "Opponent-adjusted statistics, IOS ratings and who they were earned against"}
TOURS = (("atp", "ATP (men)"), ("wta", "WTA (women)"))
FORM = {"52 weeks": "last 52 weeks", "decayed": "decayed", "career": "career", "single": "", "adjusted": "opponent-adjusted"}
CHANNELS = (("stage4_adjusted", "Stage 4: adjusted form"), ("adjperf", "adjperf"), ("adjdef", "adjdef"),
            ("ios_own", "IOS: own rating"), ("ios_allowed", "IOS: what it allows"))
BINS = (0.1, 0.25, 0.5, 1.0, 2.0, 4.0)          # heat steps, milli-log-loss given Elo; 0 or below has no fill


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


def f3(x) -> str:
    v = num(x)
    return "–" if v is None else f"{v:.3f}".replace("-0.000", "0.000").replace("-", "−")


def n0(x) -> str:
    v = num(x)
    return "–" if v is None else f"{int(round(v)):,}"


def hl(x) -> str:
    return "∞" if str(x) == "inf" or (num(x) is not None and not math.isfinite(float(x))) else f"{float(x):g}"


def label(r: dict) -> str:
    f = FORM.get(r.get("form", ""), r.get("form", ""))
    return r["name"] + (f" ({f})" if f else "")


def rng(r: dict, k: str = "elo") -> str:
    return f'{f2(r.get(f"{k}_imp"))} <span class="muted">({f2(r.get(f"{k}_lo"))} to {f2(r.get(f"{k}_hi"))})</span>'


def tile(lbl: str, vals: dict, note: str) -> str:
    return (f'<div class="tile" role="listitem"><div class="label">{esc(lbl)}</div><div class="pair">'
            + "".join(f'<div><small>{t.upper()}</small><div class="value">{vals[t]}</div></div>' for t, _ in TOURS)
            + f'</div><div class="note">{note}</div></div>')


def tour_seg(name: str) -> str:
    return (f'<div class="controls"><span>Tour:</span><div class="seg" role="group" aria-label="Tour">'
            + "".join(f'<button type="button" data-sb{name}="{t}" aria-pressed="{str(i == 0).lower()}">{esc(w)}</button>'
                      for i, (t, w) in enumerate(TOURS)) + "</div></div>")


def by_tour(name: str, body: dict) -> str:
    return "".join(f'<div data-sb{name}-tour="{t}"{"" if i == 0 else " hidden"}>{body[t]}</div>' for i, (t, _) in enumerate(TOURS))


SCALE_WORDS = ("up to 0.1", "0.1–0.25", "0.25–0.5", "0.5–1", "1–2", "2–4", "over 4")


def heat_style(v) -> tuple[str, str]:
    """(class, style) of a heat cell: the shell's sequential ramp (seq-0 to seq-6, with its ink), none at 0 or below."""
    if v is None or v <= 0:
        return "none", ""
    k = sum(1 for b in BINS if v > b)
    return "", f' style="background:var(--seq-{k});color:var(--seq-ink-{k})"'


def render(study_dir: Path) -> dict:
    S = json.loads((Path(study_dir) / "stageB_summary.json").read_text(encoding="utf-8"))
    A, I, P = S["adjperf"], S["ios"], S["split"]
    fb = S["family_best"]
    parts = []

    def best_of(t, fams, key="elo"):
        rows = [fb[f"{t}|{f}"][key] for f in fams if f"{t}|{f}" in fb]
        return max(rows, key=lambda r: num(r.get(f"{key}_imp")) or -1e9)
    b_adj = {t: best_of(t, ("adjperf", "adjdef")) for t, _ in TOURS}
    b_ios = {t: best_of(t, ("IOS",)) for t, _ in TOURS}
    b_old = {t: best_of(t, ("earlier study",)) for t, _ in TOURS}
    b_mkt = {t: best_of(t, ("adjperf", "adjdef", "IOS", "opponent split"), "market") for t, _ in TOURS}
    parts.append(f'''    <div class="prose">
      <p>Stage B borrows three tools from the UFC pipeline. <b>adjperf</b> scores each of a player's matches against what
      that opponent usually allows; <b>adjdef</b> scores how far the player held the opponent below the opponent's own norm;
      <b>IOS</b> solves an offence and a defence rating per statistic over the whole history at once (a ridge regression,
      the batch twin of Stage 3's online serve and return ratings). A third part splits a player's opponent-adjusted
      performance by the opponent's strength. Every row is scored as the earlier study scored its rows: walk-forward by
      season, given surface Elo and given the closing odds, beside 20 shuffled copies; {S["rows_scored"]["atp"]} men's and
      {S["rows_scored"]["wta"]} women's rows.</p>
    </div>
    <div class="tiles" role="list">
      {tile("Best adjperf or adjdef row given Elo (milli-log-loss)", {t: f2(b_adj[t]["elo_imp"]) for t, _ in TOURS},
            "; ".join(esc(label(b_adj[t])) for t, _ in TOURS))}
      {tile("Best IOS row given Elo", {t: f2(b_ios[t]["elo_imp"]) for t, _ in TOURS},
            "; ".join(esc(label(b_ios[t])) for t, _ in TOURS) + " (diagnostics: a shorter memory than tuned, not tuned on results)")}
      {tile("The earlier study's ratings through the iid model, re-scored", {t: f2(b_old[t]["elo_imp"]) for t, _ in TOURS},
            "the earlier study's leader given Elo, in this run")}
      {tile("Best Stage B row given the closing odds", {t: f2(b_mkt[t]["market_imp"]) for t, _ in TOURS},
            "; ".join(f"{esc(label(b_mkt[t]))} ({f2(b_mkt[t]['market_lo'])} to {f2(b_mkt[t]['market_hi'])})" for t, _ in TOURS))}
    </div>''')
    ch_tpw = {c["tour"]: c for c in A["chosen"] if c["stat"] == "tpw"}
    tuned = {r["tour"]: r for r in S.get("ios_diagnostic_rows", []) if r["form"] == "single"}
    gaps = {d["tour"]: d for d in P["describe"]["player_season_gap"] if d["stat"] == "tpw"}
    parts.append(f'''    <ul class="plain">
      <li><span class="kind">Observed</span>adjperf works as a measure of current form: with a step-3 half-life of
      {hl(ch_tpw["atp"]["h3"])} weeks (both tours; the Brief's grid stopped at 26), total points won gains
      {f2(b_adj["atp"]["elo_imp"])} (men) and {f2(b_adj["wta"]["elo_imp"])} (women) on Elo, behind only the earlier study's
      ratings through the iid model ({f2(b_old["atp"]["elo_imp"])} and {f2(b_old["wta"]["elo_imp"])}).</li>
      <li><span class="kind">Observed</span>adjdef on a statistic with a mirror is exactly adjperf on the mirror, so those
      columns are scored once.</li>
      <li><span class="kind">Observed</span>IOS tuned on the next match's statistic forecasts serve points as well as the
      online ratings, but its points matchup gains only {f2(tuned["atp"]["elo_imp"])} and {f2(tuned["wta"]["elo_imp"])} on Elo;
      with a shorter memory, {f2(b_ios["atp"]["elo_imp"])} and {f2(b_ios["wta"]["elo_imp"])}.</li>
      <li><span class="kind">Observed</span>A player's own gap between strong and weak opponents is almost all chance (its
      spread beyond chance {f2(gaps["atp"]["sd_true"])} and {f2(gaps["wta"]["sd_true"])} z against {f2(gaps["atp"]["sd_chance"])}
      and {f2(gaps["wta"]["sd_chance"])} of chance; season to season r = {f2(gaps["atp"]["season_to_season_r"])} and
      {f2(gaps["wta"]["season_to_season_r"])}); no split row beats the unsplit average.</li>
      <li><span class="kind">Inferred</span>Elo is not missing a lasting "short against the strong, crushes the weak"
      trait; what it misses is recent form, measured against each opponent. The closing odds already price it.</li>
    </ul>''')

    # ------------------------------------------------------------------ terms
    parts.append('''    <div class="sub"><h3>Terms used in this section</h3><dl class="terms">
      <dt>z</dt><dd>A match's statistic on the log-odds scale minus the opponent's norm, over the opponent's typical
      match-to-match spread (MAD), clipped to ±4.</dd>
      <dt>MAD</dt><dd>Mean absolute deviation: the average distance of the opponent's matches from their own weighted mean,
      shrunk toward the population's.</dd>
      <dt>adjperf / adjdef</dt><dd>The player's average z of what they produced (adjperf), or of how far they held each
      opponent below that opponent's own norm (adjdef). In tennis adjdef on serve points won is exactly adjperf on return
      points won seen from the other side (likewise holds and breaks, and the other mirrored pairs), so those are scored
      once.</dd>
      <dt>IOS, κ</dt><dd>Implied offence and defence: per statistic, every match's log-odds rate ≈ the server's offence minus
      the returner's defence, solved jointly over all earlier weeks with recent matches weighted more; κ is the ridge, in
      typical matches, that pulls a rating toward the average.</dd>
      <dt>Forms</dt><dd>Last 52 weeks (no decay), decayed (a half-life h3), career; all shrunk toward 0 with K3 matches.</dd>
      <dt>Strong, weak</dt><dd>An opponent whose pre-match surface Elo is above (strong) or at or below (weak) the median of
      main-tour players in 2010–2018.</dd>
    </dl></div>''')

    # ------------------------------------------------------------------ priors
    ch = {(c["tour"], c["stat"]): c for c in A["chosen"]}
    br = {(c["tour"], c["stat"]): c for c in A["brief_grid_choice"]}
    prow = "".join(
        f'<tr><td>{t.upper()}</td><td>{esc(s)}</td><td class="r">{hl(c["h1"])}</td><td class="r">{hl(c["K1"])}</td>'
        f'<td class="r">{c["tau"]}</td><td class="r">{hl(c["h3"])}</td><td class="r">{hl(c["K3"])}</td>'
        f'<td class="r">{f3(c["improvement"])}</td><td class="r">{hl(br[(t, s)]["h3"])} / {hl(br[(t, s)]["K3"])}: '
        f'{f3(br[(t, s)]["improvement"])}</td></tr>' for (t, s), c in ch.items())
    ic = {(c["tour"], c["stat"]): c for c in I["chosen"]}
    ib = {(c["tour"], c["stat"]): c for c in I["brief_grid_choice"]}
    irow = "".join(
        f'<tr><td>{t.upper()}</td><td>{esc(s)}</td><td class="r">{hl(c["h"])}</td><td class="r">{hl(c["kappa"])}</td>'
        f'<td class="r">{c["tau"]}</td><td class="r">{f3(c["tuning_better_milli_per_unit"])}</td>'
        f'<td class="r">{hl(ib[(t, s)]["h"])} / {hl(ib[(t, s)]["kappa"])} / {ib[(t, s)]["tau"]}: '
        f'{f3(ib[(t, s)]["tuning_better_milli_per_unit"])}</td></tr>' for (t, s), c in sorted(ic.items(), key=lambda x: (x[0][1], x[0][0])))
    parts.append(f'''    <div class="sub"><h3>The priors chosen (2013–2018, then frozen)</h3>
      <div class="prose"><p><span class="kind">Observed</span>adjperf was tuned on serve, return and total points won by
      the in-sample gain of [Elo, feature] over Elo (milli-log-loss); IOS on the next match's log loss per unit of each
      statistic. Both tunings chose the edge of the Brief's grids, so the grids were extended (the Brief's own choice is
      beside). The step-3 half-life h3 matters most; the opponent's norm (h1, K1) hardly at all; weighting by units (τ = 1)
      lost on every adjperf grid.</p></div>
      <div class="panel"><div class="table-wrap"><table class="num wide"><thead><tr><th>Tour</th><th>adjperf</th>
        <th class="r">h1 (wk)</th><th class="r">K1</th><th class="r">τ</th><th class="r">h3 (wk)</th><th class="r">K3</th>
        <th class="r">Gain</th><th class="r">Brief's grid: h3 / K3: gain</th></tr></thead><tbody>{prow}</tbody></table></div>
      <details class="twin"><summary>IOS: the constants per statistic</summary><div class="table-wrap"><table class="num wide">
        <thead><tr><th>Tour</th><th>Statistic</th><th class="r">h (wk)</th><th class="r">κ</th><th class="r">τ</th>
        <th class="r">Gain per unit</th><th class="r">Brief's grid: h / κ / τ: gain</th></tr></thead><tbody>{irow}</tbody></table></div></details></div>
    </div>''')

    # ------------------------------------------------------------------ the channel per statistic (heat table)
    chan = S["channel_per_statistic"]
    heat = {}
    for t, _ in TOURS:
        rows = []
        for r in [c for c in chan if c["tour"] == t]:
            cells = []
            for k, _w in CHANNELS:
                c = r.get(k)
                v = num(c["elo_imp"]) if c else None
                if v is None:
                    cells.append('<td class="v none">–</td>')
                    continue
                tipr = [f"{f2(v)} milli-log-loss given Elo", f"{r['words']} · {_w}"]
                if k == "stage4_adjusted":
                    tipr.append(f"reading: {c['reading']}")
                else:
                    tipr += [f"best form: {FORM.get(c['form'], c['form']) or 'one form'} · 95% range {f2(c['elo_lo'])} to {f2(c['elo_hi'])}",
                             f"reading: {c['reading']}"]
                if k == "adjdef" and r.get("adjdef_is_alias_of"):
                    tipr.append(f"identical to {r['adjdef_is_alias_of']}")
                win = " best" if r.get("winner") == k else ""
                cls, sty = heat_style(v)
                cells.append(f'<td class="v {cls}{win}"{sty} tabindex="0" data-tip="{esc(json.dumps(tipr))}">{f2(v)}</td>')
            rows.append(f'<tr><td>{esc(r["words"])}</td>{"".join(cells)}</tr>')
        heat[t] = (f'<div class="table-wrap"><table class="heat num wide"><thead><tr><th>Statistic</th>'
                   + "".join(f'<th class="r">{esc(w)}</th>' for _, w in CHANNELS) + f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')
    wins = {t: {} for t, _ in TOURS}
    for c in chan:
        if c.get("winner"):
            wins[c["tour"]][c["winner"]] = wins[c["tour"]].get(c["winner"], 0) + 1
    wtxt = "; ".join(f"{t.upper()}: " + ", ".join(f"{dict(CHANNELS)[k]} {v}" for k, v in sorted(wins[t].items(), key=lambda x: -x[1]))
                     for t, _ in TOURS)
    scale = "".join(f'<span class="sw" style="background:var(--seq-{k})"></span><span class="lbl">{w}</span>'
                    for k, w in enumerate(SCALE_WORDS))
    parts.append(f'''    <div class="sub"><h3>Which channel adds most given Elo, statistic by statistic</h3>
      <div class="prose"><p><span class="kind">Observed</span>Each cell is the best form's walk-forward gain on surface Elo
      (milli-log-loss, all scored seasons); the bold cell is the statistic's winner ({esc(wtxt)}). For a return statistic
      the IOS ratings are those of its serve mirror (returning well is holding servers down). Hover or focus a cell for its
      form, range and reading.</p></div>
      <div class="panel">{tour_seg("heat")}
        <div class="scale" aria-hidden="true"><span class="sw none"></span><span class="lbl">0 or worse</span>{scale}</div>
        {by_tour("heat", heat)}</div>
    </div>''')

    # ------------------------------------------------------------------ the ten strongest rows, and the earlier study's
    def rank_table(rows, extra=None):
        body = "".join(
            f'<tr><td class="r">{i + 1}</td><td>{esc(label(r))}<span class="tag">{esc(r["group"])}</span></td>'
            f'<td class="r">{rng(r)}</td><td class="r">{f2(r.get("elo_2022-2026"))}</td>'
            f'<td class="r">{r.get("eras_positive", "–")} of {r.get("eras_scored", "–")}</td><td>{esc(r.get("reading", "–"))}</td>'
            f'<td class="r">{f2(r.get("market_imp"))}</td>{extra(r) if extra else ""}</tr>' for i, r in enumerate(rows))
        return body
    head = ('<tr><th class="r">#</th><th>Row</th><th class="r">Given Elo (95% range)</th><th class="r">2022–26</th>'
            '<th class="r">Eras +</th><th>Reading</th><th class="r">Given market</th>{x}</tr>')
    top = {t: f'<div class="table-wrap"><table class="num wide"><thead>{head.format(x="")}</thead><tbody>{rank_table(S["top10_given_elo"][t])}</tbody></table></div>'
           for t, _ in TOURS}
    rep = {(x["col"], x["tour"]): x for x in S["earlier_reproduced"]}
    old = {t: f'<div class="table-wrap"><table class="num wide"><thead>{head.format(x="<th class=r>Earlier study</th>")}</thead><tbody>'
           + rank_table(S["earlier_rows"][t], lambda r: f'<td class="r">{f2(rep.get((r["col"], r["tour"]), {}).get("stage4"))}</td>')
           + "</tbody></table></div>" for t, _ in TOURS}
    parts.append(f'''    <div class="sub"><h3>The ten strongest rows given Elo, and the earlier study's rows</h3>
      <div class="panel">{tour_seg("top")}{by_tour("top", top)}
        <details class="twin"><summary>The earlier study's rows, re-scored in this run</summary>{by_tour("top", old)}</details>
        <p class="note-small">Milli-log-loss better than surface Elo alone, all scored seasons (men 2013–2026; women's
        box-score rows 2019–2026). "Eras +" counts the eras with a positive gain. The full ranking is
        <code>stageB_ranking.csv</code>.</p></div>
    </div>''')

    # ------------------------------------------------------------------ who the statistics were earned against
    sp = {t: "".join(f'<tr><td>{esc(label(r))}</td><td class="r">{rng(r)}</td><td>{esc(r.get("reading", "–"))}</td>'
                     f'<td class="r">{rng(r, "market")}</td></tr>' for r in S["split_rows"][t]) for t, _ in TOURS}
    sp = {t: ('<div class="table-wrap" style="max-height:28rem;overflow-y:auto"><table class="num wide"><thead><tr><th>Row</th>'
              '<th class="r">Given Elo (95% range)</th><th>Reading</th><th class="r">Given market (95% range)</th></tr></thead>'
              f'<tbody>{v}</tbody></table></div>') for t, v in sp.items()}
    gap = "".join(f'<tr><td>{d["tour"].upper()}</td><td>{esc(d["stat"])}</td><td class="r">{n0(d["player_seasons"])}</td>'
                  f'<td class="r">{f2(d["mean_gap"])}</td><td class="r">{f2(d["sd_gap_observed"])}</td><td class="r">{f2(d["sd_chance"])}</td>'
                  f'<td class="r">{f2(d["sd_true"])}</td><td class="r">{f2(d["season_to_season_r"])}</td>'
                  f'<td class="r">{f2(d["strong_mean_season_to_season_r"])}</td></tr>' for d in P["describe"]["player_season_gap"])
    ps = P["population_slope"]
    parts.append(f'''    <div class="sub"><h3>Who the statistics were earned against</h3>
      <div class="prose"><p><span class="kind">Observed</span>The line between strong and weak opponents is a pre-match
      surface Elo of {n0(P["lines"]["atp"]["median"])} (men) and {n0(P["lines"]["wta"]["median"])} (women). Within a
      player's season, the opponent-adjusted z of total points won falls by {f2(-ps["atp"]["b0"])} (men) and
      {f2(-ps["wta"]["b0"])} (women) per 100 Elo points of the opponent. Per player-season with five or more matches in
      each group, the gap between strong and weak opponents is mostly chance: its spread beyond chance and its
      season-to-season correlation are in the table.</p></div>
      <div class="panel"><div class="table-wrap"><table class="num wide"><thead><tr><th>Tour</th><th>Statistic</th>
        <th class="r">Player-seasons</th><th class="r">Mean gap (z)</th><th class="r">Observed sd</th><th class="r">Chance sd</th>
        <th class="r">True sd</th><th class="r">Gap, season to season (r)</th><th class="r">Against the strong, season to season (r)</th>
        </tr></thead><tbody>{gap}</tbody></table></div></div>
      <div class="panel">{tour_seg("split")}{by_tour("split", sp)}</div>
    </div>''')

    # ------------------------------------------------------------------ beyond the ratings; IOS beside Stage 3; probes
    vr = "".join(f'<tr><td>{r["tour"].upper()}</td><td>{esc(label(r))}</td><td class="r">{f2(r["elo_imp"])}</td>'
                 f'<td class="r">{rng(r, "ratings")}</td><td class="r">{rng(r, "elo_ratings")}</td>'
                 f'<td class="r">{f2(r.get("elo_ratings_band_max"))}</td></tr>' for r in S["vs_ratings"])
    cmp_ = "".join(f'<tr><td>{c["tour"].upper()}</td><td>{esc(c["window"])}</td><td class="r">{n0(c["matches"])}</td>'
                   f'<td class="r">{f3(c["ios_better_milli_per_point"])}</td><td class="r">{f3(c["stage3_better_milli_per_point"])}</td>'
                   f'<td class="r">{f3(c["ios_minus_stage3_milli_per_point"])}</td></tr>' for c in I["stage3_comparison"])
    dsc = {(d["diagnostic"], d["tour"]): d for d in I.get("diagnostics", [])}
    diag = "".join(f'<tr><td>{r["tour"].upper()}</td><td>{esc(r["form"].replace("diagnostic: ", "") if r["form"] != "single" else "as tuned")}</td>'
                   f'<td class="r">{rng(r)}</td><td class="r">{f3(dsc.get((r["form"].replace("diagnostic: ", ""), r["tour"]), {}).get("spw_2019-2026")) if r["form"] != "single" else "–"}</td>'
                   f'<td class="r">{f2(r.get("market_imp"))}</td></tr>' for r in sorted(S.get("ios_diagnostic_rows", []), key=lambda r: (r["tour"], r["form"] != "single")))
    pa, pi, pp = A["probe"], I["probe"], P["probe"]
    ios_pc = sum(v["protected_rows_changed"] for v in pi.values())
    ios_pk = sum(v["protected_rows_checked"] for v in pi.values())
    parts.append(f'''    <div class="sub"><h3>Does anything add to the serve and return ratings?</h3>
      <div class="prose"><p>The three strongest adjperf, adjdef and IOS rows per tour given Elo, the tuned IOS points matchup
      and its best diagnostic, scored again two ways: with the ratings through the iid model as the only baseline, and with
      Elo and the ratings both in the model (refitted each season, the harness's walk, against the same model without the
      row; "copies' best" is the largest gain of 20 shuffled copies there).</p></div>
      <div class="panel"><div class="table-wrap"><table class="num wide"><thead><tr><th>Tour</th><th>Row</th>
        <th class="r">Given Elo</th><th class="r">Given the ratings (95% range)</th>
        <th class="r">Given Elo and the ratings (95% range)</th><th class="r">Copies' best</th></tr></thead><tbody>{vr}</tbody></table></div></div>
    </div>
    <div class="sub"><h3>IOS serve points beside Stage 3's online ratings</h3>
      <div class="prose"><p>Log loss per serve point, milli-log-loss better than the surface average, on exactly Stage 3's
      scoring set (its figures read from its JSON); 2013–2018 is in-sample for both.</p></div>
      <div class="panel"><div class="table-wrap"><table class="num"><thead><tr><th>Tour</th><th>Window</th><th class="r">Matches</th>
        <th class="r">IOS</th><th class="r">Stage 3</th><th class="r">IOS minus Stage 3</th></tr></thead><tbody>{cmp_}</tbody></table></div>
      <details class="twin"><summary>The IOS points matchup with other constants (diagnostics), given Elo</summary>
        <div class="table-wrap"><table class="num"><thead><tr><th>Tour</th><th>Constants</th><th class="r">Given Elo (95% range)</th>
        <th class="r">Serve points forecast, 2019–26</th><th class="r">Given market</th></tr></thead><tbody>{diag}</tbody></table></div></details></div>
    </div>
    <div class="sub"><h3>Checks</h3><ul class="plain">
      <li><b>Probes cut by date, event and round</b> (4 cuts in 2026 on the slice from 2023; what a cut may not see redrawn).
      adjperf and adjdef: {n0(pa["protected_changed"])} of {n0(pa["protected_checked"])} protected matches moved; a leaky
      control moved at {n0(pa["control_protected_changed"])}. IOS (serve points and holds, both tours): {n0(ios_pc)} of
      {n0(ios_pk)} protected player-rows. The opponent split: {n0(pp["protected_changed"])} of {n0(pp["protected_checked"])}.</li>
      <li><b>The mirror</b>: adjdef on each mirrored statistic equals adjperf on its mirror to within
      {max(m["z_max_abs_diff"] for m in A["mirror"]):.0e} per match (correlation {min(m["z_corr"] for m in A["mirror"]):.6f}).</li>
      <li><b>Tests</b>: <code>test/ufc_ideas/test_stageB.py</code> (hand-made histories against row-by-row readings; the IOS
      solve against a dense least squares).</li></ul></div>''')
    return {"html": "\n".join(parts), "data": {}, "script": JS}


JS = r"""
(function () {
  const root = document.getElementById("stage-b");
  if (!root) return;
  ["heat", "top", "split"].forEach(name => {
    const btns = root.querySelectorAll(`[data-sb${name}]`);
    btns.forEach(b => b.addEventListener("click", () => {
      btns.forEach(o => o.setAttribute("aria-pressed", String(o === b)));
      root.querySelectorAll(`[data-sb${name}-tour]`).forEach(d => { d.hidden = d.getAttribute(`data-sb${name}-tour`) !== b.getAttribute(`data-sb${name}`); });
    }));
  });
  root.querySelectorAll("td[data-tip]").forEach(td => window.reportTip.bind(td, () => JSON.parse(td.getAttribute("data-tip"))));
})();
"""
