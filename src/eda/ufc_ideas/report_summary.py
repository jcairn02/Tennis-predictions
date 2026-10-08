"""Report section for the summary of the study "ideas borrowed from UFC-predictions", at the top of its page.

What it holds, in order: the takeaways; how far each forecast gets from a coin flip to the bookmakers (the earlier
ladder, with the new base rating added where Stage A built one); every feature tried in both studies, family by family,
with whether it was promising and how it did, each family unfolding to list every version; what to do next and the
decisions for the owner.

Every number comes from data/studies/ufc_ideas/summary_results.json (summary_results.py), which re-expresses the
stages' rankings on the earlier summary's scale.
"""
from __future__ import annotations

import html
import json
import math
from pathlib import Path

SECTION = {"stage": "summary", "id": "ufc-summary", "title": "What we tried, and what it did"}

TOUR = {"atp": "ATP", "wta": "WTA"}
TOUR_LONG = {"atp": "Men (ATP)", "wta": "Women (WTA)"}
SEX = {"atp": "men", "wta": "women"}
STAGE_WORDS = {"A": "Stage A", "B": "Stage B", "C": "Stage C", "D": "Stage D", "4": "earlier study"}
# one line per family of the new study (the catalog's one-line descriptions are per version)
FAMILY_WHAT = {
    "bt rating": "a Bradley–Terry rating: every result re-solved at once, with a time decay and a ridge toward an anchor, in place of Elo",
    "bradley-terry": "a Bradley–Terry rating: every result re-solved at once, with a time decay and a ridge toward an anchor, in place of Elo",
    "mesr": "a rating solved from the closing odds rather than results: the market's opinion of each player, carried forward",
    "adjperf": "a player's statistics scored against what each opponent usually allows, averaged with a decay and a prior",
    "adjdef": "how far a player held each opponent below the opponent's own norm, averaged with a decay and a prior",
    "ios": "offense and defense ratings per statistic, solved as a ridge regression over the whole history at each week",
    "opponent split": "performance against strong opponents against performance against weak ones",
    "strength of schedule": "how strong the opponents met in the last year were, and the strength of those beaten and lost to",
    "retrospective credit": "credit for old opponents at what they turned out to be worth: their rating now minus at the meeting",
    "fatigue": "whether a player fades as a match gets long, from Grand Slam points and from long matches in the box scores",
    "together": "the best inputs of both studies in one model",
    "statistics profile": "the individual statistics' opponent-adjusted ratings together in one model (aces, double faults, first serves in, first- and second-serve points won, holds, break points), without the points-won aggregates",
}
READING_WORDS = {"finding": "finding", "possible": "possible", "no sign": "no sign", "worse": "worse",
                 "no information (constant)": "constant", "not scored": "not scored", "not read": "not read"}


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
    return "–" if v is None else f"{v:+.2f}"


def pc(x) -> str:
    v = num(x)
    if v is None:
        return "–"
    return f"{100 * v:.1f}%" if abs(v) < 0.01 else f"{100 * v:.0f}%"


def width(x) -> str:
    v = max(0.0, min(1.0, num(x) or 0.0))
    return "%.1f" % (100 * v)


def tag(k: str) -> str:
    return f'<span class="ktag">{esc(k)}</span>'


def kick(k: str) -> str:
    return f'<span class="ktag" style="display:block;margin:0 0 4px">{esc(k)}</span>'


def size_word(share) -> str:
    v = num(share) or 0
    return "the best" if v >= 0.15 else "yes" if v >= 0.05 else "a little" if v >= 0.02 else "negligible"


def both(atp: str, wta: str) -> str:
    return atp if atp == wta else f"{atp} (men) and {wta} (women)"


def load(study_dir: Path) -> dict:
    return json.loads((study_dir / "summary_results.json").read_text(encoding="utf-8"))


def with_form(name: str, form: str) -> str:
    """The version's name with its form, unless the name already says it."""
    if form == "single" or form.lower() in name.lower() or (form == "52 weeks" and "last year" in name.lower()):
        return name
    return f"{name} ({form})"


def reading_cell(r: dict | None, key: str = "overall_gain") -> str:
    if not r:
        return '<td class="muted">–</td>'
    v = num(r.get(key))
    word = READING_WORDS.get(r.get("reading"), r.get("reading", ""))
    cls = {"finding": "", "possible": "muted", "worse": "flag"}.get(r.get("reading"), "muted")
    return f'<td class="r"><span class="{cls}">{f2(v)}</span> <span class="word">{esc(word)}</span></td>'


def market_cell(r: dict | None) -> str:
    if not r or num(r.get("market_gain")) is None:
        return '<td class="r muted">–</td>'
    v = num(r["market_gain"])
    mark = " ✓ line" if r.get("market_line") else (" ↑ band" if r.get("market_above_band") else "")
    return f'<td class="r">{f2(v)}<span class="word">{esc(mark)}</span></td>'


def family_cell(x: dict | None, t: str) -> str:
    label = f'data-label="{SEX[t].capitalize()}"'
    if not x:
        return f'<td {label} class="muted">not played</td>'
    if x["verdict"] == "helps" and x["best"]:
        b = x["best"]
        return (f'<td {label}><div class="meter"><div class="track"><div class="fill" style="width:{width(b["share_of_gap"])}%"></div></div>'
                f'<span class="num">{pc(b["share_of_gap"])}</span><span class="word">{size_word(b["share_of_gap"])}</span></div>'
                f'<span class="what">best: {esc(with_form(b["name"], b["form"]))}, '
                f'{f2(b["overall_gain"])} milli-log-loss given Elo</span></td>')
    ba = x.get("best_any")
    if ba and ba["reading"] == "finding":
        note = (f'<span class="what">a finding, {f2(ba["overall_gain"])} given Elo over every level, but no gain on the main '
                f'tour ({esc(with_form(ba["name"], ba["form"]))})</span>')
        word = "no on the main tour"
    else:
        note = f'<span class="what">best version {f2(ba["overall_gain"])} given Elo ({esc(READING_WORDS.get(ba["reading"], ba["reading"]))})</span>' if ba else ""
        word = "no: reversed" if x["verdict"] == "reversed" else "no"
    return f'<td {label}><span class="word">{word}</span>{note}</td>'


def family_market_cell(f: dict) -> str:
    hits = [(t, f["tours"][t]["market"]) for t in TOUR if t in f["tours"] and f["tours"][t]["market"]]
    if hits:
        shares = [pc(m["market_share"]) for _, m in hits]
        who = "" if len(hits) == 2 else f', {SEX[hits[0][0]]} only'
        gains = [f2(m["market_gain"]) for _, m in hits]
        return f'<td data-label="Bookmakers">barely ({esc(" and ".join(sorted(set(shares))))}{who}; {esc(" / ".join(gains))} milli-log-loss)</td>'
    best = [(t, f["tours"][t]["market_best_any"]) for t in TOUR if t in f["tours"] and f["tours"][t].get("market_best_any")]
    if best:
        g = max(best, key=lambda z: z[1]["market_gain"])[1]
        return f'<td data-label="Bookmakers" class="muted">no (largest {f2(g["market_gain"])})</td>'
    return '<td data-label="Bookmakers" class="muted">no</td>'


def versions_table(f: dict) -> str:
    """Every version of a family: one row per (id, form), the men's and the women's cells side by side."""
    keys = []
    for r in f["rows"]:
        k = (r["id"], r["form"])
        if k not in keys:
            keys.append(k)
    by = {(r["tour"], r["id"], r["form"]): r for r in f["rows"]}
    rows = []
    for i, fm in keys:
        a, w = by.get(("atp", i, fm)), by.get(("wta", i, fm))
        r0 = a or w
        name = with_form(r0["name"], fm)
        desc = r0.get("description", "")
        rows.append(f'<tr><td style="max-width:30rem;white-space:normal"><b>{esc(name)}</b>'
                    f'{"<span class=what>" + esc(desc) + "</span>" if desc else ""}</td>'
                    f'{reading_cell(a)}{reading_cell(w)}{market_cell(a)}{market_cell(w)}</tr>')
    return (f'<details class="twin" style="margin-top:0;border-top:0;padding-top:0"><summary>Every version ({len(keys)})</summary>'
            f'<div class="table-wrap"><table class="num" style="min-width:40rem">'
            f'<thead><tr><th rowspan="2">Version</th><th colspan="2">Given Elo (milli-log-loss, all scored seasons)</th>'
            f'<th colspan="2">Given the bookmakers</th></tr>'
            f'<tr><th class="r">Men</th><th class="r">Women</th><th class="r">Men</th><th class="r">Women</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            f'<p class="note-small">Readings given Elo: finding (clears the family-wide line and gains in three or more eras), '
            f'possible (above its own null band), no sign, worse. Given the bookmakers: ✓ line clears the family-wide line, '
            f'↑ band is above its own band.</p></details>')


def render(study_dir: Path) -> dict:
    res = load(study_dir)
    fams, counts, lead = res["families"], res["counts"], res["leaders"]
    new = [f for f in fams if f["source"] == "new"]
    earlier = [f for f in fams if f["source"] == "earlier"]
    pool = counts["pool"]

    def best_new(t):
        rows = lead[t]["given_elo"]
        return max((r for r in rows if r.get("share_of_gap") is not None), key=lambda r: r["share_of_gap"], default=None)

    def best_mkt(t):
        rows = lead[t]["given_market"]
        return rows[0] if rows else None

    bn = {t: best_new(t) for t in TOUR}
    bm = {t: best_mkt(t) for t in TOUR}
    old_best = {t: next(f for f in earlier if f["key"] == "earlier:ratings")["tours"][t]["best"] for t in TOUR}
    n_find = {t: len(lead[t]["given_elo"]) for t in TOUR}
    n_clear = {t: len(lead[t]["clear_given_elo"]) for t in TOUR}
    n_line = {t: len(lead[t]["market_line"]) for t in TOUR}

    parts = [f'''    <div class="prose">
      <p class="lede" style="margin-top:0">The predictability diagnostic tested {counts["earlier_ids"]} candidate features
      ({counts["earlier_rows"]:,} versions) and found that nothing beats the bookmakers' closing prices, while serve-and-return
      strength ratings beat Elo most. This second pass borrows the UFC pipeline's tools: a Bradley–Terry rating in place of
      Elo, ratings solved from closing odds, opponent-adjusted statistics, strength of schedule and fatigue. It adds
      {counts["new_ids"]} features ({counts["new_rows"]:,} versions) on the same {pool["atp"]:,} men's and {pool["wta"]:,} women's
      matches of 2013–2026, scored with the same walk-forward test, so every number below sits on one scale.</p>
    </div>''']

    def box_elo(t):
        b = bn[t]
        if not b:
            return f"{TOUR_LONG[t]}: no new version is a finding given Elo."
        return (f'{TOUR_LONG[t]}: {esc(with_form(b["name"], b["form"]))} closes '
                f'{pc(b["share_of_gap"])} of the gap between Elo and the bookmakers (the earlier best, the strength ratings, '
                f'{pc(old_best[t]["share_of_gap"])}).')

    ss = res.get("stage_summaries", {})
    A, D, DP = ss.get("A", {}), ss.get("D", {}), ss.get("D_profile", {})
    gap = A.get("gap_closed_2022_2026", {})
    raw = A.get("raw", {})
    bt_worse = {t: num(raw.get(t, {}).get("2013-2026", {}).get("all", {}).get("elo_minus_bt", {}).get("milli")) for t in TOUR}
    adj = {t: DP.get("headline", {}).get(f"{t}|profile_adjperf", {}) for t in TOUR}
    ev = {t: D.get("headline", {}).get(f"{t}|everything", {}) for t in TOUR}
    mesr_rows = [r for f in fams for r in f["rows"] if r["id"] == "mesr"]
    mesr_mkt = {t: next((r["market_gain"] for r in mesr_rows if r["tour"] == t), None) for t in TOUR}

    def bt_box():
        if not gap:
            return "Stage A has not run."
        return (f'Tuned on the same seasons as Elo, the Bradley–Terry rating is worse than surface Elo by '
                f'{abs(bt_worse["atp"] or 0):.2f} (men) and {abs(bt_worse["wta"] or 0):.2f} (women) milli-log-loss over 2013–2026, '
                f'and sits further from the bookmakers than Elo does: it closes {pc(gap["atp"]["bt"])} and {pc(gap["wta"]["bt"])} '
                f'of the Elo-to-market gap. A rating solved from closing odds (MESR) adds {f2(mesr_mkt["atp"])} and {f2(mesr_mkt["wta"])} '
                f'to the odds themselves.')

    def profile_box():
        if not adj["atp"]:
            return "Stage D has not run."
        return (f'The profile of twelve individual statistics (2-week adjperf: aces, double faults, first serves in, first- and '
                f'second-serve points won, holds, break points, breaks, returns), nearly useless alone, adds {f2(adj["atp"]["market_imp"])} '
                f'milli-log-loss to the closing odds for the men ({num(adj["atp"]["market_lo"]):+.2f} to {num(adj["atp"]["market_hi"]):+.2f}; '
                f'{f2(adj["atp"]["market_2022-2026"])} in 2022–2026), the largest gain on the odds in either study, and {f2(adj["wta"]["market_imp"])} '
                f'for the women. The same statistics over 52 weeks, and the long-memory IOS traits, add nothing to the odds.')

    def everything_box():
        if not ev["atp"]:
            return ""
        return (f'Everything together adds {f2(ev["atp"]["elo_imp"])} (men) and {f2(ev["wta"]["elo_imp"])} (women) to Elo but only '
                f'{f2(ev["atp"]["market_imp"])} and {f2(ev["wta"]["market_imp"])} to the odds.')

    parts.append(f'''    <div class="takeaways" role="list">
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">Bradley–Terry does not replace Elo in tennis</span>
        <p>{bt_box()}</p></div>
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">Opponent-adjusted statistics beat Elo like the ratings do, not the bookmakers</span>
        <p>{box_elo("atp")} {box_elo("wta")} {everything_box()} Of the new versions, {n_find["atp"]} (men) and {n_find["wta"]} (women)
        are findings given Elo, {n_clear["atp"]} and {n_clear["wta"]} of them clear; {both(str(n_line["atp"]), str(n_line["wta"]))}
        clear the family-wide line against the bookmakers, none by a milli-log-loss.</p></div>
      <div class="takeaway" role="listitem">{kick("observed")}<span class="head">One lead against the odds: the men's individual-statistic profile</span>
        <p>{profile_box()}</p></div>
    </div>''')

    # the ladder (the earlier one, with the new base rating where Stage A supplies it)
    lad = res["ladder"]
    rungs = [("ranking", "Official ranking"), ("bt", "Bradley–Terry rating (Stage A)"), ("elo", "Elo rating"),
             ("elo_plus_best", "Elo + the earlier best feature"), ("elo_plus_all", "Elo + everything (Stage D)"),
             ("market", "Bookmakers' closing prices")]
    boxes = []
    for t in TOUR:
        cells = []
        for k, name in rungs:
            if k not in lad[t]:
                continue
            cells.append(f'<span>{esc(name)}</span><div class="track"><div class="fill{" market" if k == "market" else ""}" '
                         f'style="width:{width(lad[t][k])}%"></div></div><span class="val">{pc(lad[t][k])}</span>')
        boxes.append(f'<div><h4 style="margin:0 0 8px">{TOUR_LONG[t]}</h4><div class="ladder">{"".join(cells)}</div></div>')
    parts.append(f'''    <div class="panel">
      <div class="panel-head"><h3>How far each forecast gets, from a coin flip to the bookmakers</h3><p>Main-tour matches
      with bookmaker odds, 2022–2026</p></div>
      <p class="note-small" style="margin:0 0 12px">Forecasts are scored by how much probability they gave the player who
      actually won (log loss). On this scale a coin flip is 0% and the bookmakers' closing prices are 100%. The Bradley–Terry
      rung is Stage A's, where it was built.</p>
      <div class="chart-pair">{"".join(boxes)}</div>
    </div>''')

    # every family tried, both studies
    def fam_row(f):
        stage = STAGE_WORDS.get(f["stage"], f["stage"])
        what = FAMILY_WHAT.get(f["title"].lower(), f["what"] if f["source"] == "earlier" else "")
        if not what and f["what"]:
            what = f["what"].split(";")[0]
        what = what[:1].upper() + what[1:] if what else ""
        title = f["title"] if f["source"] == "earlier" else f["title"][:1].upper() + f["title"][1:]
        return (f'<tr><td><b>{esc(title)}</b> <span class="tag">{esc(stage)}</span>'
                f'<span class="what">{esc(what)}{"." if what and not what.endswith(".") else ""}</span></td>'
                f'{family_cell(f["tours"].get("atp"), "atp")}{family_cell(f["tours"].get("wta"), "wta")}{family_market_cell(f)}</tr>'
                f'<tr class="versions"><td colspan="4" style="padding-top:0;max-width:0">{versions_table(f)}</td></tr>')

    def order_key(f):
        return -max((f["tours"][t]["best"]["share_of_gap"] if f["tours"].get(t) and f["tours"][t]["best"] else -1) for t in TOUR)
    new_rows = "".join(fam_row(f) for f in sorted(new, key=order_key))
    old_rows = "".join(fam_row(f) for f in sorted(earlier, key=order_key))
    parts.append(f'''    <div class="sub">
      <h3>Every feature tried, in both studies, and how it did</h3>
      <p class="prose">Each family's figure is the share of the gap between Elo and the bookmakers that its best version
      closes, on main-tour matches (Grand Slams down to 250s, where bookmakers price matches). Only versions that passed the
      strict test count: fitted on earlier seasons, tested on later ones, and better than chance across the whole family of
      tests. Open a family to see every version with its reading. The families overlap, so shares do not add up.</p>
      <div class="panel">
        <div class="panel-head"><h3>Borrowed from UFC-predictions (this study)</h3><p>{len(new)} families, {counts["new_rows"]:,} versions</p></div>
        <div class="table-wrap"><table class="families">
          <thead><tr><th>What we tried</th><th>Men</th><th>Women</th><th>Beyond the bookmakers?</th></tr></thead>
          <tbody>{new_rows}</tbody></table></div>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>The earlier study (predictability diagnostic)</h3><p>{len(earlier)} families, {counts["earlier_rows"]:,} versions</p></div>
        <div class="table-wrap"><table class="families">
          <thead><tr><th>What we tried</th><th>Men</th><th>Women</th><th>Beyond the bookmakers?</th></tr></thead>
          <tbody>{old_rows}</tbody></table></div>
      </div>
    </div>''')

    parts.append(f'''    <div class="sub" id="ufc-summary-next">
      <h3>What we suggest next</h3>
      <ul class="plain">
        <li>{tag("inferred")} <b>What the closing line misses, if anything, is recent form in individual statistics, not a stable
        trait.</b> The gain against the odds sits in the two-week adjperf profile; the 52-week version and the long-memory IOS
        ratings, the most trait-like measures here, give nothing. The market prices what a player is and may miss a little of
        how they have played, statistic by statistic, in the last fortnight.</li>
        <li>{tag("suggestion")} <b>Tighten the men's lead before building on it.</b> A ridge-penalised fit instead of the plain
        logistic regression, Pinnacle's line instead of the average line, the gain by level and by season, and which statistics
        carry it. Half a milli-log-loss is about half a percent of the way from a coin flip to the odds: a lead, not an edge.</li>
        <li>{tag("suggestion")} <b>Then build the same recent-form profile from the point-by-point data.</b> The box score holds
        twelve statistics; the point logs collected in the other studies hold the finer ones (serve direction, rally length,
        pressure points), which is where an orthogonal profile would grow.</li>
        <li>{tag("suggestion")} <b>Keep surface Elo as the base rating.</b> Bradley–Terry, MESR, strength of schedule and the
        retrospective credit do not improve on it in tennis; the matches are too many and too frequent for a batch rating with
        one memory to beat a per-player K. The credit for opponents lost to and the women's quality of wins are small
        findings given Elo only.</li>
        <li>{tag("suggestion")} <b>Close fatigue as a pre-match family.</b> The late-match decline is not a trait in these data;
        what fatigue there is shows within a match, not before it.</li>
      </ul>
    </div>
    <div class="sub">
      <h3>Decisions for you</h3>
      <ul class="plain">
        <li><b>Whether to pursue the men's individual-statistic profile</b>, and with which tightening first.</li>
        <li><b>Which inputs to carry forward as the pre-match baseline</b>: our suggestion is surface Elo with the ratings through
        the iid model and the two-week adjperf profile, the only inputs that add to the odds at all.</li>
        <li><b>The stages' open technical choices</b>, listed in <a href="summary.md">summary.md</a>: the widened tuning grids of
        Stages A and B, the diagnostic IOS rows added after the first rundown, the tournament-date "week" that lets a few mid-week
        events see each other, and the data problems found (split identities in 2026, one impossible box score, non-Monday dates).</li>
      </ul>
      <p class="note-small">Every number on this page is read from the stages' output files by the page's scripts. A study, not a
      decision.</p>
    </div>''')
    data = {"leaders": lead, "counts": counts}
    return {"html": "\n".join(parts), "data": data, "script": ""}
