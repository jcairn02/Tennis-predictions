"""Red team (role E), checkpoint-2 preparation: probes of role D's scorer (system_pairs.py) and queue (system_fits.py)
on SYNTHETIC data only. No real frame, fit, result or score is read; nothing is written outside a temporary folder.

P1  the sign chain readings() -> selection_from(): + = first-named better; a better challenger qualifies; the optional
    arms (SYS_w25) and SYS_PLACEBO never enter the selection.
P2  "no secondary is worse": the code's literal rule (system_pairs.py:793-798, 819-835) against addition 2's rule (the
    eight men's holdout readings of SELECTED vs REF, Holm, family-wise 5%).
P3  the selected arm absent from the holdout (incomplete fits): recommend() says "REF (no change)".
P4  verify_frame on a relaxed (C0_now) arm whose inputs are identical: pass is False (same_ids_in_order is None).
P5  Holm's p-value choice (normal vs t, one- vs two-sided) can flip the eighth-reading verdict: it must be pinned.
Run: ./python.sh data/studies/lower_level_evidence/system/audit/D_scorer/probe_scorer.py <temp folder>
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from src.eda.lower_level_evidence import system_fits as SF  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402

TMP = Path(sys.argv[1])
out = {}


# ------------------------------------------------------------------------------------------------ P1
def synth_info(n=6000, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.to_datetime("2020-01-06") + pd.to_timedelta(rng.integers(0, 5 * 364, n), unit="D")
    info = pd.DataFrame({"tour": rng.choice(["atp", "wta"], n), "season": dates.year.to_numpy(),
                         "tournament_date": dates, "debut": False}, index=[f"m{i}" for i in range(n)])
    info["block"] = SP.CMP.C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = SP.CMP.C.blocks(info["tournament_date"].to_numpy(), 7)
    q = rng.uniform(0.15, 0.85, n)
    info["y"] = (rng.uniform(size=n) < q).astype(float)
    info["p_ref"] = q
    return info, q, rng


def model(q, rng, noise, info):
    lq = np.log(q / (1 - q))
    p = pd.DataFrame({k: 1 / (1 + np.exp(-(lq + rng.normal(0, noise, len(q))))) for k in range(4)}, index=info.index)
    par = {Y: (1.0, 1.0, 0.0, 0.0, 0.0) for Y in range(2020, 2025)}
    return {"p": p, "s1": par, "s2": par, "z": pd.Series(0.0, index=info.index)}


info, q, rng = synth_info()
noise = {"REF": 0.9, "SYS": 0.6, "SYS_w0": 0.6, "SYS_w50": 0.4, "SYS_w100": 0.6, "SEP_ALL": 0.6, "SYS_NOCLASS": 0.25,
         "SYS_S2": 0.6, "R_S2": 0.6, "SYS_PLACEBO": 0.05, "SYS_BOTH": 0.6, "SYS_w25": 0.05}
models = {a: model(q, rng, s, info) for a, s in noise.items()}
test = tuple(range(2020, 2025))
t = SP.readings(info, models, test, "dev", [a for a in models if a != "REF"], SP.SYS_VS,
                extra_pairs=[("SYS_S2", "SYS")], strata=False, closes=False)
sel = SP.selection_from(t, "dev")
r = SP.get(t, "SYS", "SYS_NOCLASS", "men", period="dev")
out["P1"] = {"SYS_vs_SYS_NOCLASS_estimate_men (expect < 0: NOCLASS less noisy)": r["estimate"],
             "qualifying": sel["qualifying"], "selected": sel["selected"], "status": sel["status"],
             "SYS_w25_and_PLACEBO_best_but_not_selected": sel["selected"] not in ("SYS_w25", "SYS_PLACEBO"),
             "t_cdf_check": sel["t_cdf_check"]}


# ------------------------------------------------------------------------------------------------ P2
def rd(first, second, est, se, tour="men", pop="all", stage="both stages", period="holdout 2025-2026", G=22):
    tc = student_t.ppf(0.975, G - 1)
    lo, hi = est - tc * se, est + tc * se
    return {"period": period, "group": "vs REF" if second == "REF" else "arm vs arm", "comparison": f"{first} vs {second}",
            "first": first, "second": second, "stage": stage, "tour": tour, "population": pop, "matches": 1000,
            "estimate": est, "lo": lo, "hi": hi, "se": se, "p_better": norm.cdf(est / se),
            "p_better_t": student_t.cdf(est / se, G - 1), "blocks": G,
            "reading": "better" if lo > 0 else "worse" if hi < 0 else "unresolved"}


EIGHT = [("season 2025", "both stages"), ("season 2026", "both stages"), ("exposure < 10", "both stages"),
         ("exposure >= 10", "both stages"), ("share gap >= 0.5", "both stages"), ("share gap < 0.5", "both stages"),
         ("falsification: both 20+ main-tour, share < 0.10", "both stages"), ("all", "stage 1")]


def code_rule(t, selected):
    """system_pairs.holdout lines 788-798, verbatim logic."""
    H, Pd = "holdout 2025-2026", "pooled 2020-2026"
    primary, pooled = SP.get(t, selected, "REF", "men", period=H), SP.get(t, selected, "REF", "men", period=Pd)
    sec = t[(t["period"].isin([H, Pd])) & (t["group"] != "vs close")
            & ~((t["first"] == selected) & (t["second"] == "REF") & (t["tour"] == "men") & (t["population"] == "all")
                & (t["stage"] == "both stages"))]
    worse = sec[sec["reading"] == "worse"][["period", "comparison", "stage", "tour", "population"]].to_dict("records")
    return SP.recommend(primary, pooled, worse, selected)


def holm_worse(rows, alpha=0.05, p_of=lambda r: 2 * norm.sf(abs(r["estimate"] / r["se"]))):
    """Holm step-down on two-sided p-values; 'worse' = rejected and estimate < 0."""
    ps = sorted(((p_of(r), i) for i, r in enumerate(rows)))
    rejected = set()
    for k, (p, i) in enumerate(ps):
        if p <= alpha / (len(ps) - k):
            rejected.add(i)
        else:
            break
    return [rows[i] for i in rejected if rows[i]["estimate"] < 0]


def add2_rule(t, selected, **kw):
    H, Pd = "holdout 2025-2026", "pooled 2020-2026"
    primary, pooled = SP.get(t, selected, "REF", "men", period=H), SP.get(t, selected, "REF", "men", period=Pd)
    eight = [SP.get(t, selected, "REF", "men", pop, stage, period=H) for pop, stage in EIGHT]
    worse = holm_worse(eight, **kw)
    return SP.recommend(primary, pooled, worse, selected), [w["population"] + "/" + w["stage"] for w in worse]


rows = [rd("SYS", "REF", 0.10, 0.10), rd("SYS", "REF", 0.30, 0.10, period="pooled 2020-2026")]   # P 0.84; pooled better
rows += [rd("SYS", "REF", 0.05, 0.10, pop=p, stage=s) for p, s in EIGHT]
rows += [rd("SYS_w0", "REF", -0.40, 0.10, tour="women", pop="season 2025")]                       # outside the eight
t2 = pd.DataFrame(rows)
case_a = {"code": code_rule(t2, "SYS"), "addition_2": add2_rule(t2, "SYS")[0]}
rows_b = [r for r in rows if r["first"] == "SYS"]
rows_b = [rd("SYS", "REF", -0.23, 0.10, pop=r["population"], stage=r["stage"]) if r["population"] == "exposure < 10"
          else r for r in rows_b]                                                                     # raw worse, Holm not
t3 = pd.DataFrame(rows_b)
case_b = {"code": code_rule(t3, "SYS"), "addition_2": add2_rule(t3, "SYS")}
out["P2"] = {"a: worse reading outside the eight (women, SYS_w0)": case_a,
             "b: one of the eight raw-worse (z=-2.3), not worse after Holm": case_b}

# ------------------------------------------------------------------------------------------------ P3
out["P3"] = SP.recommend(None, None, [], "SYS")

# ------------------------------------------------------------------------------------------------ P4
ref_inputs = json.loads((SF.REF_DIR / "model_inputs.json").read_text(encoding="utf-8"))   # names and kinds only
names = [d["name"] for d in ref_inputs["inputs"]]
n = 12
fr = pd.DataFrame({"match_id": [f"x{i}" for i in range(n)], "tour": ["atp"] * 6 + ["wta"] * 6,
                   "season": [2020] * n, "tournament_date": pd.Timestamp("2020-03-02"), "a_won": [1, 0] * 6,
                   "p_mkt": 0.5, "tabpfn_split": "test", "debut_season": False,
                   **{f"in_{k}": np.arange(n, dtype=float) for k in names}})
refd, armd = TMP / "ref", TMP / "NEW_ASIS"
for d in (refd, armd):
    d.mkdir(parents=True, exist_ok=True)
    (d / "model_inputs.json").write_text(json.dumps(ref_inputs), encoding="utf-8")
fr.to_parquet(refd / "model_frame.parquet", index=False)
extra = fr.iloc[[0]].assign(match_id="extra")
pd.concat([fr, extra]).to_parquet(armd / "model_frame.parquet", index=False)
SF.REF_FRAME, SF.REF_DIR = refd / "model_frame.parquet", refd
SF.arm_dir = lambda arm: TMP / arm
v = SF.verify_frame("NEW_ASIS", write=False)
out["P4"] = {k: v[k] for k in ("rows_ok", "same_ids_in_order", "training_labels_equal_to_2025", "base_inputs_equal",
                               "extras_as_defined", "columns_are_the_inputs", "unexpected_moves", "pass")}

# ------------------------------------------------------------------------------------------------ P5
z, G = -2.75, 22
out["P5"] = {"z": z, "blocks": G, "Holm step-1 threshold (two-sided 0.05/8)": 0.05 / 8,
             "p two-sided normal": 2 * norm.sf(abs(z)), "p two-sided t(G-1)": 2 * student_t.sf(abs(z), G - 1),
             "p one-sided normal (=1-P(better))": norm.sf(abs(z)),
             "verdict normal two-sided": bool(2 * norm.sf(abs(z)) <= 0.05 / 8),
             "verdict t two-sided": bool(2 * student_t.sf(abs(z), G - 1) <= 0.05 / 8)}

print(json.dumps(out, indent=1, default=str))
