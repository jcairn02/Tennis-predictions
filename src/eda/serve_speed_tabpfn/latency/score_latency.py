"""The latency follow-up's exploratory outcome scorer (data/studies/serve_speed_tabpfn/latency/plan.md, reading 3).

The owner's question (7 Oct 2026): "If we CANT get the speed reading in time, is there a way to make it still
predictive?" The modeller rebuilds the speed column under availability scenarios (A instant; B today's sources; fixed lags
L1-L14) and methods (M0 as built; M1 re-tuned half-life; M2 nowcast fill) in latency/variants.parquet: match_id plus
spd_<scenario>_<method> columns, each standardised, never NaN, women 0. Everything here is EXPLORATORY: 2024-2026 results
were opened by the study's pre-registered test.

Per variant, men 2024-2026, debut seasons out (the study's 7,068 matches), with the study's own machinery, imported from
src/eda/serve_speed_tabpfn/score.py and not edited:
    S9    the walk-forward nudge (the owner's "current best model"): logit q = s_tour,Y eta + b_Y z, s and b fitted on the
          base's out-of-sample seasons 2019 .. Y - 1 (seeds 0-3 mean, debut out), shrunk (tau 0.05) and unshrunk, applied
          to the 16-seed base. mLL against the calibrated base, POSITIVE = THE NUDGE HAS THE LOWER LOG LOSS (BETTER),
          block-only interval; pooled 2024-2026 and by season; with the fitted s, b, SE and shrunk b per season
    S0    the information test (score.encompassing): b in log-odds PER UNIT OF THE VARIANT'S OWN COLUMN, positive = the man
          whose speed state is higher wins more often than the base says
    share the variant's S9 gain / A's S9 gain (A = the study's spd_f as run): a point value, no interval
Each variant is put in the Scorer's spd_f slot, so score.nudge / score.nudge_parameters run unchanged; the by-season split
mirrors score.nudge's formula and is checked against its pooled value to 1e-12.

Modes:
    --check       result-free: the variants, their counts and value summaries (no outcome), the hashes. Writes
                  latency/check_latency.json
    --synthetic   outcomes DRAWN from a planted model (never read): recovery of a planted beta, null rejection rates.
                  Writes latency/synthetic/<tag>.json
    --run         ONCE (the lead): first reproduces the study's S9 shrunk (+0.410 [+0.045, +0.775]) and S0 (+0.0650) with
                  spd_f to 1e-9, refusing to write anything otherwise; then scores every variant. Writes
                  latency/results_latency.json and .csv and refuses to overwrite them. The only path that reads a_won.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

VARIANT = re.compile(r"^spd_(?P<scenario>[A-Z][A-Za-z0-9]*)_(?P<method>M\d+)$")
REFERENCE = "spd_f"                  # A as run: the study's column (features/speed.parquet)
A_VARIANT = "spd_A_M0"               # the modeller's rebuild of A; should equal spd_f
HEADLINE = ("spd_B_M0", "spd_B_M2")  # plan.md: today's sources with no fix, and with the nowcast
TOL = 1e-9
CODE = ("src/eda/serve_speed_tabpfn/latency/score_latency.py",) + C.CODE_FILES


def folder(P: C.Paths) -> Path:
    return P.out / "latency"


def variants_path(P: C.Paths) -> Path:
    return folder(P) / "variants.parquet"


def code_hash() -> str:
    h = hashlib.sha256(b"serve_speed_tabpfn/latency/v1")
    for rel in CODE:
        h.update(rel.encode())
        h.update((ROOT / rel).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------
# Inputs (no outcome)

def variant_columns(P: C.Paths) -> list[str]:
    return [c for c in pq.read_schema(variants_path(P)).names if VARIANT.match(c)]


def validate_variants(P: C.Paths, cols: list[str]) -> pd.DataFrame:
    """The whole variants file against the whole model frame (every season): one row per frame match, no other row, every
    variant finite everywhere and 0 for every woman. A broken build is refused even where the scorer never reads it."""
    frame = pd.read_parquet(P.model_frame, columns=["match_id", "tour"])
    frame["match_id"] = frame["match_id"].astype(str)
    v = pd.read_parquet(variants_path(P), columns=["match_id"] + cols)
    v["match_id"] = v["match_id"].astype(str)
    if v["match_id"].duplicated().any():
        raise RuntimeError("variants.parquet: duplicate match ids")
    extra, missing = set(v["match_id"]) - set(frame["match_id"]), set(frame["match_id"]) - set(v["match_id"])
    if extra or missing:
        raise RuntimeError(f"variants.parquet: {len(missing)} frame matches missing, {len(extra)} unknown ids")
    v = v.set_index("match_id").reindex(frame["match_id"])
    if not np.isfinite(v.to_numpy(float)).all():
        bad = {c: int((~np.isfinite(v[c].to_numpy(float))).sum()) for c in cols if not np.isfinite(v[c]).all()}
        raise RuntimeError(f"variants must never be NaN: {bad}")
    women = (frame["tour"] == "wta").to_numpy()
    nonzero = {c: int((v.loc[women, c] != 0).sum()) for c in cols if (v.loc[women, c] != 0).any()}
    if nonzero:
        raise RuntimeError(f"variants must be 0 for every woman: {nonzero}")
    return v


def population(P: C.Paths) -> pd.DataFrame:
    """The study's population table (score.population: no result) with every validated variant column joined."""
    info = S.population(P)
    cols = variant_columns(P)
    if not cols:
        raise RuntimeError(f"{variants_path(P)}: no spd_<scenario>_<method> column")
    v = validate_variants(P, cols)
    return info.join(v.reindex(info.index))


def value_summary(info: pd.DataFrame, cols: list[str]) -> dict:
    """Values only (no outcome): men 2024-2026 (the scored population)."""
    men = info.loc[S.population_ids(info, "men", S.TEST)]
    out = {}
    for c in [REFERENCE] + cols:
        x = men[c].to_numpy(float)
        out[c] = {"matches": int(len(x)), "nonzero": int((x != 0).sum()), "sd": float(x.std()),
                  "corr_with_spd_f": float(np.corrcoef(x, men[REFERENCE].to_numpy(float))[0, 1]) if x.std() > 0 else None,
                  "max_abs_diff_from_spd_f": float(np.abs(x - men[REFERENCE].to_numpy(float)).max()),
                  "nonzero_by_season": {str(s): int((g[c] != 0).sum()) for s, g in men.groupby("season")}}
    return out


def base_fits_missing(P: C.Paths) -> list:
    out = []
    for s in S.HIST:
        for k in S.SEEDS16:
            try:
                F.find_fit("model", s, k, P)
            except FileNotFoundError:
                out.append((s, k))
    return out


# ------------------------------------------------------------------------------------------------
# Scoring one variant with the study's machinery

def as_spd_f(info: pd.DataFrame, col: str) -> pd.DataFrame:
    """The population table with the variant in the Scorer's spd_f slot (score.nudge and nudge_parameters read it)."""
    out = info.copy()
    out["spd_f"] = info[col].to_numpy(float)
    return out


def nudge_detail(sc: S.Scorer) -> dict:
    """score.nudge (pooled, exactly the study's S9) plus the same formula by season; the mirror must equal the pooled
    value to 1e-12."""
    pooled, params = S.nudge(sc)
    ids = S.population_ids(sc.info, "men", S.TEST)
    qb, _ = sc.forecast("model", S.SEEDS16, S.TEST, "td", "calibrated", ids)
    eta16 = sc.bank.eta("model", S.SEEDS16, S.TEST, "td").reindex(ids).to_numpy()
    inf = sc.info.loc[ids]
    y = sc.y.reindex(ids).to_numpy(float)
    z = inf["spd_f"].to_numpy(float)
    atp = inf["tour"].to_numpy() == "atp"
    season = inf["season"].to_numpy()
    rows = []
    for variant, label in (("b_shrunk", "S9_shrunk"), ("b_mle", "S9_mle")):
        logit_q = np.empty(len(ids))
        for s, p in params.items():
            k = season == int(s)
            logit_q[k] = np.where(atp, p["s_atp"], p["s_wta"])[k] * eta16[k] + p[variant] * z[k]
        llb, llf = C.ll(qb, y), C.ll(expit(logit_q), y)
        whole = S.paired_stats(llb, llf, np.zeros(1), np.zeros(1), inf["block"].to_numpy(), inf["week"].to_numpy())
        ref = next(r for r in pooled if r["cid"] == label)
        if abs(whole["estimate"] - ref["estimate"]) > 1e-12:
            raise RuntimeError(f"{label}: the by-season mirror does not reproduce score.nudge")
        for s in S.TEST:
            k = season == s
            r = S.paired_stats(llb[k], llf[k], np.zeros(1), np.zeros(1), inf["block"].to_numpy()[k],
                               inf["week"].to_numpy()[k])
            rows.append({"cid": f"{label}_{s}", "seasons": [s], "matches": r["matches"], "estimate": r["estimate"],
                         "lo": r["lo_block_only"], "hi": r["hi_block_only"]})
    return {"pooled": pooled, "by_season": rows, "parameters": params}


def score_variant(bank: S.Bank, info: pd.DataFrame, y: pd.Series, col: str) -> dict:
    sc = S.Scorer(bank, as_spd_f(info, col), y)
    nd = nudge_detail(sc)
    ids = S.population_ids(sc.info, "men", S.TEST)
    eta_b = bank.eta("model", S.SEEDS16, S.TEST, "td").reindex(ids).to_numpy()
    unit = ("log-odds per unit of spd_f (one s_f = 2.224 km/h)" if col == REFERENCE
            else f"log-odds per unit of {col} (the variant's own standardised column)")
    s0 = S.encompassing(sc.info.loc[ids], sc.y.reindex(ids).to_numpy(float), eta_b,
                        sc.info.loc[ids, "spd_f"].to_numpy(float), unit)
    s0["direction"] = "positive = the man whose speed state is higher wins more often than the base says"
    direction = "positive = the nudge has the lower log loss (better) than the calibrated base"
    return {"column": col, "S9": [{**r, "direction": direction, "unit": "mLL"} for r in nd["pooled"]],
            "S9_by_season": [{**r, "direction": direction, "unit": "mLL"} for r in nd["by_season"]],
            "S9_parameters": nd["parameters"], "S0": s0}


def gain(res: dict, label: str) -> float:
    return next(r["estimate"] for r in res["S9"] if r["cid"] == label)


def shares(res: dict, ref: dict) -> dict:
    """The variant's S9 gain as a share of A's (point values, no interval)."""
    out = {}
    for label in ("S9_shrunk", "S9_mle"):
        a = gain(ref, label)
        out[label] = gain(res, label) / a if a != 0 else None
    return out


def evaluate(bank: S.Bank, info: pd.DataFrame, y: pd.Series, cols: list[str]) -> dict:
    ref = score_variant(bank, info, y, REFERENCE)
    out = {"reference": ref, "variants": {}}
    for c in cols:
        r = score_variant(bank, info, y, c)
        r["share_of_A"] = shares(r, ref)
        out["variants"][c] = r
    return out


def reproduction(ref: dict, study: dict) -> dict:
    """The harness check of plan.md: spd_f must reproduce the study's S9 shrunk (estimate and interval) and S0."""
    mine = next(r for r in ref["S9"] if r["cid"] == "S9_shrunk")
    theirs = next(r for r in study["S9"] if r["cid"] == "S9_shrunk")
    diffs = {"S9_shrunk_estimate": mine["estimate"] - theirs["estimate"], "S9_shrunk_lo": mine["lo"] - theirs["lo"],
             "S9_shrunk_hi": mine["hi"] - theirs["hi"], "S0_estimate": ref["S0"]["estimate"] - study["S0"]["estimate"]}
    return {"study": {"S9_shrunk": [theirs["estimate"], theirs["lo"], theirs["hi"]], "S0": study["S0"]["estimate"]},
            "here": {"S9_shrunk": [mine["estimate"], mine["lo"], mine["hi"]], "S0": ref["S0"]["estimate"]},
            "differences": diffs, "passed": all(abs(d) <= TOL for d in diffs.values())}


def table(res: dict) -> pd.DataFrame:
    rows = []
    for col, r in [(REFERENCE, res["reference"])] + list(res["variants"].items()):
        m = VARIANT.match(col)
        tag = {"variant": col, "scenario": m["scenario"] if m else "A (as run)", "method": m["method"] if m else "-",
               "headline": col in HEADLINE}
        for row in r["S9"] + r["S9_by_season"]:
            share = r.get("share_of_A", {}).get(row["cid"]) if row["cid"] in ("S9_shrunk", "S9_mle") else None
            rows.append({**tag, "endpoint": row["cid"], "matches": row["matches"], "estimate": row["estimate"],
                         "lo": row["lo"], "hi": row["hi"], "unit": "mLL", "share_of_A": share,
                         "direction": row["direction"]})
        s0 = r["S0"]
        rows.append({**tag, "endpoint": "S0", "matches": s0["matches"], "estimate": s0["estimate"], "lo": s0["lo"],
                     "hi": s0["hi"], "unit": s0["unit"], "share_of_A": None, "direction": s0["direction"]})
    t = pd.DataFrame(rows)
    t["verdict"] = [("better" if lo > 0 else "worse" if hi < 0 else "tie") if u == "mLL"
                    else ("positive" if lo > 0 else "negative" if hi < 0 else "tie")
                    for lo, hi, u in zip(t["lo"], t["hi"], t["unit"])]
    return t


# ------------------------------------------------------------------------------------------------
# Modes

def hashes(P: C.Paths) -> dict:
    plan = folder(P) / "plan.md"
    return {"variants_sha256": C.sha256_file(variants_path(P)),
            "plan_sha256": C.sha256_file(plan) if plan.exists() else None,
            "latency_code_sha256": code_hash(), "scorer_code_sha256": C.code_hash(),
            "model_frame_sha256": C.sha256_file(P.model_frame), "feature_sha256": C.sha256_file(P.feature_file)}


def study_record(P: C.Paths) -> dict:
    """The study's frozen hashes (results.json -> hashes). Read for the hashes only in --check."""
    path = P.out / "results.json"
    if not path.exists():
        raise RuntimeError("the study's results.json is missing: nothing to reproduce")
    return C.read_json(path)


def same_inputs(P: C.Paths, study: dict) -> dict:
    rec, now = study["hashes"], hashes(P)
    return {"scorer_code": rec["SCORER_CODE_SHA256"] == now["scorer_code_sha256"],
            "model_frame": rec["MODEL_FRAME_SHA256"] == now["model_frame_sha256"],
            "feature_file": rec["FEATURE_SHA256"] == now["feature_sha256"]}


def check(P: C.Paths = C.DEFAULT) -> dict:
    info = population(P)
    cols = variant_columns(P)
    study = study_record(P)
    out = {"what": "result-free check of the latency scorer's inputs (no outcome read)", "variants": cols,
           "headline_present": {c: c in cols for c in HEADLINE}, "a_variant_present": A_VARIANT in cols,
           "population_sha256": S.ids_hash(S.population_ids(info, "men", S.TEST)),
           "population_equals_study": S.ids_hash(S.population_ids(info, "men", S.TEST)) ==
           study["hashes"]["POPULATION_SHA256"],
           "same_inputs_as_the_study": same_inputs(P, study), "values_men_2024_2026": value_summary(info, cols),
           "base_fits_missing": base_fits_missing(P), "reuse_checks": F.checks_passed(P), "hashes": hashes(P)}
    C.write_json(folder(P) / "check_latency.json", out)
    return out


def synthetic(P: C.Paths = C.DEFAULT, plant: str | None = None, beta: float = 0.0, reps: int = 50, seed: int = 0,
              s_true: float = 0.9, tag: str | None = None) -> dict:
    """y ~ Bernoulli(expit(s_true eta_B + beta z_plant)) for every 2019-2026 frame match (eta_B the base's 16-seed
    log-odds; z_plant a variant, 0 for women), never read. Every variant and spd_f are scored per replicate."""
    info = population(P)
    cols = variant_columns(P)
    plant = plant or (A_VARIANT if A_VARIANT in cols else REFERENCE)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index).to_numpy()
    truth = s_true * eta + beta * info[plant].to_numpy(float)
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(reps):
        y = pd.Series((rng.random(len(info)) < expit(truth)).astype(float), index=info.index)
        res = evaluate(bank, info, y, cols)
        for col, v in [(REFERENCE, res["reference"])] + list(res["variants"].items()):
            sh = next(x for x in v["S9"] if x["cid"] == "S9_shrunk")
            rows.append({"rep": r, "column": col, "S9_shrunk": sh["estimate"], "S9_lo": sh["lo"], "S9_hi": sh["hi"],
                         "S0_b": v["S0"]["estimate"], "S0_lo": v["S0"]["lo"], "S0_hi": v["S0"]["hi"]})
    t = pd.DataFrame(rows)
    summary = {}
    for col, g in t.groupby("column", sort=False):
        summary[col] = {"S0_b_mean": float(g["S0_b"].mean()),
                        "S0_reject_two_sided": float(((g["S0_lo"] > 0) | (g["S0_hi"] < 0)).mean()),
                        "S9_shrunk_mean": float(g["S9_shrunk"].mean()),
                        "S9_reject_positive": float((g["S9_lo"] > 0).mean()),
                        "S9_reject_negative": float((g["S9_hi"] < 0).mean())}
        if col == plant:
            summary[col]["S0_covers_beta"] = float(((g["S0_lo"] <= beta) & (beta <= g["S0_hi"])).mean())
    out = {"what": "synthetic outcomes from a planted model; no match result read",
           "plant": plant, "beta": beta, "reps": reps, "seed": seed, "s_true": s_true, "summary": summary,
           "replicates": t.to_dict(orient="records")}
    C.write_json(folder(P) / "synthetic" / f"{tag or f'{plant}_b{beta:g}_r{reps}_s{seed}'}.json", out)
    return out


def run(P: C.Paths = C.DEFAULT) -> dict:
    jpath, cpath = folder(P) / "results_latency.json", folder(P) / "results_latency.csv"
    if jpath.exists() or cpath.exists():
        raise RuntimeError("results_latency exists: the exploratory outcome run happens once")
    study = study_record(P)
    same = same_inputs(P, study)
    if not all(same.values()):
        raise RuntimeError(f"code or inputs differ from the study's frozen run: {same}")
    info = population(P)
    if S.ids_hash(S.population_ids(info, "men", S.TEST)) != study["hashes"]["POPULATION_SHA256"]:
        raise RuntimeError("the men's 2024-2026 population differs from the study's")
    missing = base_fits_missing(P)
    if missing:
        raise RuntimeError(f"{len(missing)} base fits missing, e.g. {missing[:5]}")
    if not all(F.checks_passed(P).values()):
        raise RuntimeError("reuse checks not passed")
    cols = variant_columns(P)
    bank = S.Bank(P, S.frame_index(P), require_checks=True)
    y = S.labels(P)                                                       # the only result read
    ref = score_variant(bank, info, y, REFERENCE)
    rep = reproduction(ref, study)
    if not rep["passed"]:
        raise RuntimeError(f"the harness does not reproduce the study's S9 / S0: {rep['differences']}")
    res = {"reference": ref, "variants": {}}
    for c in cols:
        r = score_variant(bank, info, y, c)
        r["share_of_A"] = shares(r, ref)
        res["variants"][c] = r
    res.update({"what": "EXPLORATORY latency reading (plan.md reading 3); 2024-2026 results were opened by the study's "
                        "pre-registered test", "reproduction": rep, "headline": list(HEADLINE),
                "values_men_2024_2026": value_summary(info, cols), "hashes": hashes(P),
                "key": "S9 in mLL, positive = the nudge better than the calibrated base, block-only interval; S0 in "
                       "log-odds per unit of the column, positive = the higher speed state wins more than the base "
                       "says; share_of_A = the variant's S9 gain / A's, a point value"})
    C.write_json(jpath, res)
    table(res).to_csv(cpath, index=False)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--synthetic", action="store_true")
    g.add_argument("--run", action="store_true")
    ap.add_argument("--plant", default=None)
    ap.add_argument("--beta", type=float, default=0.0)
    ap.add_argument("--reps", type=int, default=50)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.check:
        out = check()
        print(json.dumps({k: out[k] for k in ("variants", "headline_present", "same_inputs_as_the_study",
                                              "population_equals_study", "base_fits_missing")}, indent=1))
        return 0
    if a.synthetic:
        print(json.dumps(synthetic(plant=a.plant, beta=a.beta, reps=a.reps, seed=a.seed)["summary"], indent=1))
        return 0
    res = run()
    print(json.dumps(res["reproduction"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
