"""Part F, step 4: which price, or combination, is the best stand-in for Pinnacle's missing close, against results.

The scored rows: the gap rows (from 1 Aug 2025, the model's odds input BetOnline or the books' average, i.e. no
Pinnacle close) played before 29 Jul 2026 (the seal; their results are read through odds_common.results()). Every
price is margin-free (proportional, as the model's input); combinations average log-odds. The design was declared in
data/studies/source_reconciliation/odds/declared.json before any of these results was read.

    A. each candidate − BetOnline's last line (today's stand-in), paired on the matches both price (the primary)
    B. the same by part (2025: Aug-Nov, new against the odds-sources study's 2026 reading; 2026: Jan-28 Jul) and tour
    C. every candidate on one common set of matches (all of the widely available ones priced), and a second common set
       with tennis-data's PS after July 2025 (which stops in mid-January 2026)
    D. full-coverage rules on every gap row, each − today's rule (BetOnline, else the average)
    E. calibration slope of each candidate in the gap, with Pinnacle's and BetOnline's before the gap for reference
    F. the exploratory sweep: every equal average of 2-4 of the single sources, ranked on the even four-week blocks
       and read on the odd ones
    G. checks: Polymarket 60 minutes before the listed start; the walk-forward weights; the gap rows' prices as the
       model's input actually holds them

mLL; + = the candidate worse (higher log loss); 95% intervals over four-week blocks; "better"/"worse" only when the
interval clears 0, else "unresolved" with P(better).

Writes data/studies/source_reconciliation/odds/: scores.json, scores_tables.md (aggregates), gap_prices.parquet (per-match
margin-free chances of every candidate on the gap rows, no result; gitignored).
Run: ./python.sh src/eda/source_reconciliation/odds_score.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.source_reconciliation import odds_common as O  # noqa: E402
from src.eda.source_reconciliation import odds_proxy as PX  # noqa: E402

SINGLES = list(O.SINGLES) + list(O.ADDED)          # bol bfe pm psx b365 avg max otmed + b105 b105_pre
EQUAL = [["bol", "bfe"], ["bol", "pm"], ["bfe", "pm"], ["bol", "bfe", "pm"], ["bol", "bfe", "pm", "otmed"],
         ["bol", "psx"], ["bol", "bfe", "psx"], ["bol", "otmed"], ["bol", "b105"]]
WF = [["bol", "bfe"], ["bol", "pm"], ["bol", "bfe", "pm"], ["bol", "bfe", "pm", "otmed"]]
RULES = {"today": None, "bol_bfe": ["bol", "bfe"], "bol_pm": ["bol", "pm"], "sharp3": ["bol", "bfe", "pm"],
         "sharp4": ["bol", "bfe", "pm", "otmed"], "b105": ["bol", "b105"], "proxy": "proxy"}
COMMON = ["bol", "bfe", "pm", "b365", "avg", "max", "otmed", "b105"]
SWEEP = ["bol", "bfe", "pm", "psx", "b365", "avg", "max", "otmed", "b105"]
WF_MIN = 500
WF_FROM = pd.Timestamp("2018-01-01")


def walk_forward(df: pd.DataFrame, y: np.ndarray, members: list[str], score: np.ndarray) -> tuple[np.ndarray, dict]:
    """Weights refitted at each four-week block on every earlier row (from 2018, result known, every member priced):
    a logistic fit without intercept, normalised to sum to 1 (pools.weighted). A block is scored only with WF_MIN
    training rows."""
    Z = O.lg(df[[f"p_{m}" for m in members]].to_numpy(float))
    full = np.isfinite(Z).all(axis=1)
    blk = df["block"].to_numpy()
    base = full & np.isfinite(y) & (df["td_date"] >= WF_FROM).to_numpy()
    out = np.full(len(df), np.nan)
    weights = {}
    for b in sorted(np.unique(blk[score & full])):
        train = base & (blk < b)
        cur = score & full & (blk == b)
        if train.sum() < WF_MIN:
            weights[str(b)] = {"n_fit": int(train.sum()), "scored": False}
            continue
        beta, _ = OC.fit_logistic(Z[train], y[train])
        if beta.sum() < 0.5:
            weights[str(b)] = {"n_fit": int(train.sum()), "scored": False, "slope": round(float(beta.sum()), 3)}
            continue
        w = beta / beta.sum()
        out[cur] = O.ex(Z[cur] @ w)
        first = str(df.loc[cur, "td_date"].min().date())
        weights[str(b)] = {"from": first, "n_fit": int(train.sum()), "scored": True, "n_scored": int(cur.sum()),
                           "weights": {m: round(float(v), 3) for m, v in zip(members, w)},
                           "slope": round(float(beta.sum()), 3)}
    return out, weights


def polymarket_60(df: pd.DataFrame, y: np.ndarray) -> np.ndarray:
    """Polymarket 60 minutes before the listed start for side A, on rows whose result is known: the sharp benchmark's
    pw_pm_m60 joined through Stage 1's tennis-data file and row, oriented by the table's own 30-minute price."""
    key = ["tour", "td_date", "td_winner", "td_loser"]       # table.py's join key (odds_sources/table.KEY)
    s1 = pd.read_parquet(O.STAGE1, columns=["match_id", "td_date", "td_winner", "td_loser"])
    s1["match_id"] = s1["match_id"].astype(str)
    sb = pd.read_parquet(O.SHARP, columns=["tour", "date", "winner", "loser", "pw_pm_m30", "pw_pm_m60"])
    sb = sb.rename(columns={"date": "td_date", "winner": "td_winner", "loser": "td_loser"})
    for t in (s1, sb):
        t["td_date"] = pd.to_datetime(t["td_date"]).dt.normalize()
        t["td_winner"], t["td_loser"] = t["td_winner"].astype(str), t["td_loser"].astype(str)
    sb = sb[~sb.duplicated(key, keep=False)]
    x = df[["match_id", "tour", "p_pm"]].merge(s1, on="match_id", how="left").merge(sb, on=key, how="left",
                                                                                   validate="many_to_one")
    if not (x["match_id"].to_numpy() == df["match_id"].to_numpy()).all():
        raise RuntimeError("row order")
    p30, w30, w60 = x["p_pm"].to_numpy(float), x["pw_pm_m30"].to_numpy(float), x["pw_pm_m60"].to_numpy(float)
    known = np.isfinite(y)
    a_w = known & (np.abs(p30 - w30) < 1e-9) & (np.abs(w30 - 0.5) > 1e-9)
    a_l = known & (np.abs(p30 - (1 - w30)) < 1e-9) & (np.abs(w30 - 0.5) > 1e-9)
    return np.where(a_w, w60, np.where(a_l, 1 - w60, np.nan))


def build_candidates(df: pd.DataFrame, y: np.ndarray, gap: np.ndarray) -> tuple[dict, dict]:
    c = {s: df[f"p_{s}"].to_numpy(float) for s in SINGLES}
    for m in EQUAL:
        c["eq_" + "+".join(m)] = O.equal(df, m)
    info = {"walk_forward_weights": {}}
    for m in WF:
        c["wf_" + "+".join(m)], info["walk_forward_weights"]["+".join(m)] = walk_forward(df, y, m, gap)
    prx, fits = PX.proxies(df, gap)
    c.update(prx)
    info["proxy_fits"] = {k: {kk: vv for kk, vv in v.items() if kk != "patterns"} for k, v in fits.items()}
    avg = df["p_avg"].to_numpy(float)
    for name, members in RULES.items():
        if members is None:
            p = np.where(np.isfinite(c["bol"]), c["bol"], avg)
        elif members == "proxy":
            p = np.where(np.isfinite(c["proxy"]), c["proxy"], avg)
        else:
            q = O.equal(df, members, min_count=1)
            p = np.where(np.isfinite(q), q, avg)
        c["rule_" + name] = p
    info["rule_today_equals_model_input_on_gap_rows"] = bool(np.allclose(c["rule_today"][gap],
                                                                         df["p_input"].to_numpy(float)[gap]))
    c["pm60"] = polymarket_60(df, y)
    c["eq_bol+pm60"] = OC.mean_logit(np.column_stack([c["bol"], c["pm60"]]), min_count=2)
    return c, info


def verdict_text(r: dict | None) -> str:
    if not r or r.get("est") is None:
        return ""
    v = O.verdict(r)
    pb = r.get("p_neg")
    return v + (f", P(better) {pb:.2f}" if v == "unresolved" and pb is not None else "")


def vs(c: dict, base: str, names, y, blk, mask) -> dict:
    return {n: O.paired(c[n], c[base], y, blk, mask) for n in names if n != base}


def vs_recalibrated(c: dict, base: str, names, y, blk, mask) -> dict:
    """As vs(), after each price is given its own calibration slope on the compared matches (one parameter each, fitted
    in sample on both sides alike): what is left is the difference in information, not in calibration."""
    out = {}
    for n in names:
        if n == base:
            continue
        m = mask & np.isfinite(c[n]) & np.isfinite(c[base]) & np.isfinite(y)
        if m.sum() < 300:
            continue
        za, zb = O.lg(c[n][m]), O.lg(c[base][m])
        ba = float(OC.fit_logistic(za[:, None], y[m])[0][0])
        bb = float(OC.fit_logistic(zb[:, None], y[m])[0][0])
        pa, pb = np.full(len(y), np.nan), np.full(len(y), np.nan)
        pa[m], pb[m] = O.ex(ba * za), O.ex(bb * zb)
        r = O.paired(pa, pb, y, blk, m)
        r["slope_candidate"], r["slope_base"] = round(ba, 4), round(bb, 4)
        out[n] = r
    return out


def common_set(c: dict, members: list[str], names, y, blk, mask) -> dict:
    m = mask & np.isfinite(y)
    for s in members:
        m &= np.isfinite(c[s])
    out = {"n": int(m.sum()), "members_required": members, "log_loss": {}, "minus_bol": {}}
    for n in names:
        if not np.isfinite(c[n][m]).all():
            continue
        out["log_loss"][n] = round(float(O.log_loss(c[n][m], y[m]).mean()), 5)
        if n != "bol":
            out["minus_bol"][n] = O.paired(c[n], c["bol"], y, blk, m)
    return out


def calibration(c: dict, names, y, blk, mask) -> dict:
    out = {}
    for n in names:
        m = mask & np.isfinite(c[n]) & np.isfinite(y)
        if m.sum() < 300:
            continue
        out[n] = OC.slope_ci(O.lg(c[n][m]), y[m], blk[m])
    return out


def sweep(df: pd.DataFrame, y, blk, mask) -> dict:
    """Every equal average of 2-4 of SWEEP: − BetOnline on the even blocks (discovery) and the odd blocks."""
    even = (blk % 2 == 0)
    rows = []
    bol = df["p_bol"].to_numpy(float)
    for k in (2, 3, 4):
        for m in itertools.combinations(SWEEP, k):
            p = O.equal(df, list(m))
            d = O.paired(p, bol, y, blk, mask & even)
            v = O.paired(p, bol, y, blk, mask & ~even)
            rows.append({"members": "+".join(m), "k": k, "discovery": d, "confirmation": v})
    rows = [r for r in rows if r["discovery"].get("est") is not None]
    rows.sort(key=lambda r: r["discovery"]["est"])
    return {"n_combinations": len(rows), "ranked_by_discovery": rows[:15],
            "best_on_discovery": rows[0]["members"] if rows else None,
            "discovery_blocks": "even four-week blocks", "confirmation_blocks": "odd four-week blocks"}


def holm(readings: dict, alpha: float = 0.05) -> dict:
    """Holm's step-down over a family of readings (two-sided t p-values): which differences survive the multiplicity
    of the declared family."""
    items = sorted(((k, r["p_two_sided"]) for k, r in readings.items() if r and r.get("p_two_sided") is not None),
                   key=lambda kv: kv[1])
    m, out, stop = len(items), {}, False
    for i, (k, p) in enumerate(items):
        thr = alpha / (m - i)
        ok = (not stop) and p <= thr
        stop = stop or not ok
        out[k] = {"p_two_sided": round(p, 5), "holm_threshold": round(thr, 5), "survives": bool(ok)}
    return {"family_size": m, "alpha": alpha, "readings": out}


def where_pinnacle_known(df: pd.DataFrame, c: dict, y: np.ndarray) -> dict:
    """Against results where Pinnacle's close IS known, each candidate − Pinnacle and − BetOnline: the post-change
    window (1 Aug - 7 Sep 2025, match-day clusters) and 2024 - Jul 2025 by season with the proxies fitted walk-forward
    (2018 .. Y-1), four-week blocks."""
    pin = df["p_pin"].to_numpy(float)
    day = (df["td_date"].to_numpy("datetime64[D]") - np.datetime64("2010-01-01")).astype(int)
    blk = df["block"].to_numpy()
    out = {}
    w = ((df["td_date"] >= PX.WINDOW[0]) & (df["td_date"] <= PX.WINDOW[1]) & df["pin_known"]).to_numpy() & \
        np.isfinite(y)
    prx_w, _ = PX.proxies(df, w)
    cw = {**{k: c[k] for k in ["bol", "bfe", "psx", "b365", "avg", "max", "otmed", "b105", "b105_pre", "eq_bol+bfe",
                               "eq_bol+b105", "eq_bol+otmed"]}, **prx_w}
    out["window_2025-08-01_to_09-07"] = {
        "clusters": "match day",
        "minus_pinnacle": {k: O.paired(p, pin, y, day, w) for k, p in cw.items()},
        "minus_bol": {k: O.paired(p, cw["bol"], y, day, w) for k, p in cw.items() if k != "bol"}}
    for yr in (2024, 2025):
        m = (df["season"].to_numpy() == yr) & (df["td_date"] <= "2025-07-31").to_numpy() & \
            df["pin_known"].to_numpy() & np.isfinite(y)
        prx, _ = PX.proxies(df, m, hi=f"{yr - 1}-12-31")
        prx = {k: v for k, v in prx.items() if k in ("proxy", "proxy_bol")}
        cy = {**{k: c[k] for k in ["bol", "b365", "avg", "max", "otmed", "b105", "eq_bol+otmed", "eq_bol+b105"]},
              **prx}
        out[f"season_{yr}_to_2025-07-31"] = {
            "clusters": "four-week block",
            "minus_pinnacle": {k: O.paired(p, pin, y, blk, m) for k, p in cy.items()},
            "minus_bol": {k: O.paired(p, cy["bol"], y, blk, m) for k, p in cy.items() if k != "bol"}}
    return out


def table_rows(res: dict, names, base_label: str) -> list[str]:
    L = ["| Candidate | Matches | Log loss | Base's log loss | − " + base_label + ", mLL | Verdict |",
         "|---|---:|---:|---:|---|---|"]
    for n in names:
        r = res.get(n)
        if not r or r.get("est") is None:
            continue
        L.append(f"| {O.short(n)} | {r['n']:,} | {r['ll_a']:.4f} | {r['ll_b']:.4f} | {O.fmt(r)} | {verdict_text(r)} |")
    return L


def tables(res: dict) -> str:
    L = ["# Part F: the stand-in for Pinnacle's missing close, against results (generated by odds_score.py)", "",
         f"Gap rows played before 29 Jul 2026: {res['n_scored']:,} (of {res['n_gap']:,} gap rows). mLL, "
         "+ = the candidate worse (higher log loss) than the base; 95% intervals over four-week blocks; "
         "P(better) = P(the candidate's log loss is lower).", "",
         "## A. Each candidate − BetOnline's last line, on the matches both price (the primary)", ""]
    order = list(res["A"])
    L += table_rows(res["A"], order, "BetOnline")
    L += ["", "### A, after each price's own calibration slope (in sample, one parameter each): information only", ""]
    L += table_rows(res["A_recalibrated"], [n for n in order if n in res["A_recalibrated"]], "BetOnline")
    L += ["", "### D, after each rule's own calibration slope", ""]
    L += table_rows(res["D_recalibrated"], list(res["D_recalibrated"]), "today's rule")
    L += ["", "## B. By part and tour (− BetOnline)", ""]
    for part, r in res["B"].items():
        L += [f"**{part}**", ""] + table_rows(r, [n for n in order if n in r], "BetOnline") + [""]
    for key, title in (("C1", "C. One common set (every widely available source priced)"),
                       ("C2", "C. A second common set, with tennis-data's PS after July 2025 (Aug 2025 – Jan 2026)")):
        r = res[key]
        L += [f"## {title}: {r['n']:,} matches; required: {', '.join(r['members_required'])}", "",
              "| Candidate | Log loss | − BetOnline, mLL | Verdict |", "|---|---:|---|---|"]
        for n, ll in sorted(r["log_loss"].items(), key=lambda kv: kv[1]):
            d = r["minus_bol"].get(n)
            L.append(f"| {O.short(n)} | {ll:.4f} | {O.fmt(d) if d else '—'} | {verdict_text(d)} |")
        L.append("")
    L += ["## D. Full-coverage rules on every gap row before the seal, − today's rule (BetOnline, else the average)", ""]
    L += table_rows(res["D"], list(res["D"]), "today's rule")
    for part, r in res["D_by_part"].items():
        L += ["", f"**{part}**", ""] + table_rows(r, list(r), "today's rule")
    L += ["", "## E. Calibration slope in the gap (1 = calibrated; above 1 = too timid)", "",
          "| Price | Matches | Slope [95%] |", "|---|---:|---|"]
    for n, s in res["E"]["gap"].items():
        L.append(f"| {O.short(n)} | {s['n']:,} | {s['est']:.3f} [{s['lo']:.3f}, {s['hi']:.3f}] |")
    for n, s in res["E"]["reference_2024_to_2025_07"].items():
        L.append(f"| {O.short(n)}, 2024 – Jul 2025 (reference) | {s['n']:,} | {s['est']:.3f} [{s['lo']:.3f}, "
                 f"{s['hi']:.3f}] |")
    f = res["F"]
    L += ["", f"## F. Exploratory sweep: {f['n_combinations']} equal averages of 2–4 sources, − BetOnline", "",
          "Ranked on the even four-week blocks (discovery); the odd blocks read the same combination afresh.", "",
          "| Members | Discovery | Confirmation |", "|---|---|---|"]
    for r in f["ranked_by_discovery"]:
        L.append(f"| {' + '.join(O.short(m) for m in r['members'].split('+'))} | {O.fmt(r['discovery'])} | "
                 f"{O.fmt(r['confirmation'])}, {verdict_text(r['confirmation'])} |")
    g = res["G"]
    L += ["", "## G. Checks", "", "Polymarket's time (− the 30-minute price on the same matches):", ""]
    L += table_rows(g["polymarket_60"], list(g["polymarket_60"]), "the 30-minute version")
    L += ["", "Walk-forward weights (normalised), the last block scored:", ""]
    for k, w in g["walk_forward_last"].items():
        L.append(f"* {k}: {w}")
    L += ["", f"Today's rule equals the model's own input on every gap row: {g['rule_today_equals_model_input']}.", ""]
    gm = res["G_more"]
    L += ["More checks (mLL, + = the first named worse):", "",
          f"* BetOnline + Polymarket 60 min − BetOnline: {O.fmt_v(gm['eq_bol+pm60_minus_bol'])} "
          f"({gm['eq_bol+pm60_minus_bol'].get('n', 0):,} matches)",
          f"* The three-price rule with Polymarket's 60-minute price − today's rule: "
          f"{O.fmt_v(gm['rule_sharp3_pm60_minus_today'])}",
          f"* The three-price rule − today's rule, weekly clusters: {O.fmt_v(gm['rule_sharp3_minus_today_weekly_clusters'])}"
          f" ({gm['rule_sharp3_minus_today_weekly_clusters']['blocks']} weeks)",
          f"* By four-week block (mLL): {gm['rule_sharp3_minus_today_by_block']}",
          f"* Rows by how many of BetOnline, Betfair, Polymarket price them (before the seal): "
          f"{gm['sharp3_composition_before_seal']}"]
    for k, v in gm["head_to_head"].items():
        L.append(f"* {k.replace('_minus_', ' − ')}: {O.fmt_v(v)}")
    L.append("")
    h = res["holm_declared_family"]
    L += [f"## Multiplicity: Holm's step-down over the {h['family_size']} declared readings of A and D (5%)", "",
          "| Reading | Two-sided p | Holm threshold | Survives |", "|---|---:|---:|---|"]
    for k, r in list(h["readings"].items())[:12]:
        L.append(f"| {O.short(k)} | {r['p_two_sided']:.4f} | {r['holm_threshold']:.4f} | "
                 f"{'yes' if r['survives'] else 'no'} |")
    L += ["", "## H. Where Pinnacle's close is known: each candidate − Pinnacle, against results", ""]
    for part, r in res["H"].items():
        L += [f"**{part}** (clusters: {r['clusters']})", "", "| Candidate | Matches | − Pinnacle, mLL | Verdict | "
              "− BetOnline, mLL | Verdict |", "|---|---:|---|---|---|---|"]
        for k, d in r["minus_pinnacle"].items():
            if d.get("est") is None:
                continue
            b = r["minus_bol"].get(k)
            L.append(f"| {O.short(k)} | {d['n']:,} | {O.fmt(d)} | {verdict_text(d)} | "
                     f"{O.fmt(b) if b else '—'} | {verdict_text(b) if b else ''} |")
        L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    O.OUT.mkdir(parents=True, exist_ok=True)
    df = O.load_table()
    y = O.attach_y(df)
    gap = df["gap"].to_numpy()
    scored = gap & np.isfinite(y)
    if (scored & df["sealed"].to_numpy()).any():
        raise RuntimeError("a sealed row has a result")
    c, info = build_candidates(df, y, gap)
    blk = df["block"].to_numpy()

    names_A = (SINGLES + ["eq_" + "+".join(m) for m in EQUAL] + ["wf_" + "+".join(m) for m in WF] +
               list(PX.VARIANTS))
    res = {"n_gap": int(gap.sum()), "n_scored": int(scored.sum()), "A": vs(c, "bol", names_A, y, blk, scored)}
    res["A_recalibrated"] = vs_recalibrated(c, "bol", names_A, y, blk, scored)
    res["D_recalibrated"] = vs_recalibrated(c, "rule_today", [f"rule_{k}" for k in RULES if k != "today"], y, blk,
                                            scored)
    parts = {"2025 (1 Aug - 30 Nov 2025)": (df["td_date"] < "2026-01-01").to_numpy(),
             "2026 (1 Jan - 28 Jul 2026)": (df["td_date"] >= "2026-01-01").to_numpy(),
             "men": (df["tour"] == "atp").to_numpy(), "women": (df["tour"] == "wta").to_numpy()}
    res["B"] = {k: vs(c, "bol", names_A, y, blk, scored & m) for k, m in parts.items()}
    names_C = [n for n in names_A if n not in ("psx", "eq_bol+psx", "eq_bol+bfe+psx", "b105_pre")]
    res["C1"] = common_set(c, COMMON, names_C, y, blk, scored)
    res["C2"] = common_set(c, COMMON + ["psx"], names_A, y, blk, scored)
    res["D"] = {f"rule_{k}": O.paired(c[f"rule_{k}"], c["rule_today"], y, blk, scored) for k in RULES if k != "today"}
    res["D_by_part"] = {k: {f"rule_{r}": O.paired(c[f"rule_{r}"], c["rule_today"], y, blk, scored & m)
                            for r in RULES if r != "today"} for k, m in parts.items()}
    ref = (df["td_date"] >= "2024-01-01").to_numpy() & (df["td_date"] <= "2025-07-31").to_numpy() & \
        df["pin_known"].to_numpy()
    c["pin"] = df["p_pin"].to_numpy(float)
    res["E"] = {"gap": calibration(c, SINGLES + ["eq_bol+bfe", "eq_bol+pm", "eq_bol+bfe+pm", "eq_bol+b105", "proxy",
                                                 "rule_today"], y, blk, scored),
                "reference_2024_to_2025_07": calibration(c, ["pin", "bol", "avg", "b105"], y, blk, ref)}
    res["F"] = sweep(df, y, blk, scored)
    wfl = {}
    for k, w in info["walk_forward_weights"].items():
        done = [v for v in w.values() if v.get("scored") and v["from"] < str(O.SEAL.date())]
        wfl[k] = {"first_scored": done[0] if done else None, "last_scored_before_seal": done[-1] if done else None}
    q60 = OC.mean_logit(np.column_stack([c["bol"], c["bfe"], c["pm60"]]), min_count=1)
    c["rule_sharp3_pm60"] = np.where(np.isfinite(q60), q60, df["p_avg"].to_numpy(float))
    week = ((df["td_date"].to_numpy("datetime64[D]") - np.datetime64("2010-01-04")).astype(int) // 7)
    d3 = O.log_loss(c["rule_sharp3"], y) - O.log_loss(c["rule_today"], y)
    res["G_more"] = {
        "eq_bol+pm60_minus_bol": O.paired(c["eq_bol+pm60"], c["bol"], y, blk, scored),
        "rule_sharp3_pm60_minus_today": O.paired(c["rule_sharp3_pm60"], c["rule_today"], y, blk, scored),
        "rule_sharp3_minus_today_weekly_clusters": O.ci(d3[scored], week[scored]),
        "rule_sharp3_minus_today_by_block": {str(b): round(1000 * float(d3[scored & (blk == b)].mean()), 3)
                                             for b in sorted(np.unique(blk[scored]))},
        "head_to_head": {f"{a}_minus_{b}": O.paired(c[a], c[b], y, blk, scored) for a, b in
                         (("rule_sharp4", "rule_sharp3"), ("rule_bol_pm", "rule_sharp3"),
                          ("rule_bol_bfe", "rule_sharp3"), ("rule_proxy", "rule_sharp3"),
                          ("rule_b105", "rule_sharp3"))},
        "sharp3_composition_before_seal": {
            str(k): int(((np.isfinite(np.column_stack([c["bol"], c["bfe"], c["pm"]])).sum(axis=1) == k) & scored).sum())
            for k in range(4)}}
    res["G"] = {"polymarket_60": {"pm60": O.paired(c["pm60"], c["pm"], y, blk, scored),
                                  "eq_bol+pm60": O.paired(c["eq_bol+pm60"], c["eq_bol+pm"], y, blk, scored)},
                "pm60_priced_scored_rows": int(np.isfinite(c["pm60"][scored]).sum()),
                "walk_forward_last": wfl,
                "rule_today_equals_model_input": info["rule_today_equals_model_input_on_gap_rows"]}
    family = {**{k: v for k, v in res["A"].items() if k != "b105_pre"}, **res["D"]}
    res["holm_declared_family"] = holm(family)
    res["H"] = where_pinnacle_known(df, c, y)
    res["info"] = info
    res["inputs_sha256"] = O.sha_inputs()
    O.write_json(O.OUT / "scores.json", res)
    (O.OUT / "scores_tables.md").write_text(tables(res), encoding="utf-8")
    keep = ["match_id", "tour", "season", "td_date", "tournament_date", "month", "block", "kind", "sealed"]
    gp = df.loc[gap, keep].copy()
    for n, p in c.items():
        if n == "pin":
            continue
        gp[f"p_{n}"] = p[gap]
    gp.to_parquet(O.OUT / "gap_prices.parquet", index=False)
    print(tables(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
