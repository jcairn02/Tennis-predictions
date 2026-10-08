"""Exploratory scorer of the adaptive speed memory (data/studies/serve_speed_tabpfn/adaptive/plan.md, "Checks and
exploratory readings"). 2024-2026 results were already read (look ledger rows 34 and 40): everything is EXPLORATORY.

Inputs: adaptive/columns.parquet (the modeller's): per scenario S in A (instant), B (today's sources), D (daily tour
collector), E (live Slam feeds): spd_T_<S>, spd_L_<S> (standardised; 0 for women; never NaN), late_a_<S>, late_b_<S> and
mode_<S> ("T" or "L"). The coefficients are refitted inside the run, walk-forward (adjust.fit: T on the instant history
spd_f, L on today's-sources spd_B_M1, both 2019 .. Y - 1, seeds 0-3, shrunk tau 0.05), and compared with
adaptive/coefficients.json.

Per scenario, men 2024-2026, debut seasons out (7,068), each against the calibrated base (positive = the arm has the
lower log loss, better; mLL; block-only interval; pooled and by season), with adjust.apply:
    pure_T    every match in mode T: spd_T_<S> with T's coefficients
    pure_L    every match in mode L: spd_L_<S> with L's coefficients
    switch    mode_<S> per match (the rule)
    joint     descriptive: one walk-forward fit of s, b_T and b_L on the scenario's own history with the mode flags
              (logit q = s_tour eta + b_T z_T 1[T] + b_L z_L 1[L]; each b shrunk with tau 0.05)
Plus the share of matches in each mode, and the switch against the better pure arm, paired (positive = the switch
better).

Modes:
    --check      result-free: the columns validated, the mode shares, how far spd_T_A is from spd_f and spd_L_B from
                 spd_B_M1, whether the inputs equal the study's. Writes adaptive/check_adaptive.json
    --synthetic  outcomes drawn from a planted model (never read)
    --run        ONCE (the lead). Refuses to start unless the columns build passed (columns_meta.json: probes_pass,
                 reads_results false, the recorded hash equal to the file's). Refuses to write unless, under A, the
                 switch equals pure T equals the study's S9
                 (+0.410 [+0.045, +0.775]) and, under B, pure L equals the latency run's B-M1 (+0.3754 [+0.1097,
                 +0.6410]), each to 1e-9. Writes adaptive/results_adaptive.json and .csv; refuses to overwrite them.
"""
from __future__ import annotations

import argparse
import json
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
from src.eda.serve_speed_tabpfn.adaptive import adjust as J  # noqa: E402

SCENARIOS = ("A", "B", "D", "E")
ARMS = ("pure_T", "pure_L", "switch")
TOL = 1e-9
DIRECTION = "positive = the arm has the lower log loss (better) than the calibrated base"


def needed(s: str) -> list[str]:
    return [f"spd_T_{s}", f"spd_L_{s}", f"late_a_{s}", f"late_b_{s}", f"mode_{s}"]


def scenarios(P: C.Paths) -> list[str]:
    names = set(pq.read_schema(J.columns_path(P)).names)
    return [s for s in SCENARIOS if set(needed(s)) <= names]


def columns(P: C.Paths) -> pd.DataFrame:
    """The columns file validated against the whole model frame: one row per frame match; for each scenario, both
    columns finite and 0 for every woman, the mode T or L, and the mode L exactly when a player is late."""
    scen = scenarios(P)
    if not scen:
        raise RuntimeError("columns.parquet holds no complete scenario")
    frame = pd.read_parquet(P.model_frame, columns=["match_id", "tour"])
    frame["match_id"] = frame["match_id"].astype(str)
    cols = [c for s in scen for c in needed(s)]
    c = pd.read_parquet(J.columns_path(P), columns=["match_id"] + cols)
    c["match_id"] = c["match_id"].astype(str)
    if c["match_id"].duplicated().any():
        raise RuntimeError("columns.parquet: duplicate match ids")
    if set(c["match_id"]) != set(frame["match_id"]):
        raise RuntimeError("columns.parquet must hold exactly the frame's matches")
    c = c.set_index("match_id").reindex(frame["match_id"])
    women = (frame["tour"] == "wta").to_numpy()
    for s in scen:
        for col in (f"spd_T_{s}", f"spd_L_{s}"):
            v = c[col].to_numpy(float)
            if not np.isfinite(v).all():
                raise RuntimeError(f"{col}: NaN")
            if (v[women] != 0).any():
                raise RuntimeError(f"{col}: non-zero for a woman")
        mode = c[f"mode_{s}"].astype(str).to_numpy()
        if not set(np.unique(mode)) <= set(J.MODES):
            raise RuntimeError(f"mode_{s}: values other than T and L")
        late = c[f"late_a_{s}"].astype(bool).to_numpy() | c[f"late_b_{s}"].astype(bool).to_numpy()
        if not np.array_equal(mode == "L", late):
            raise RuntimeError(f"mode_{s}: L must mean exactly that a player is late")
    return c


def columns_status(P: C.Paths) -> dict:
    """The modeller's build record (adaptive/columns_meta.json): probes passed, no result read, and the recorded hash
    equal to the columns file's. --run refuses otherwise; --check reports it."""
    meta_path = J.folder(P) / "columns_meta.json"
    out = {"ok": False, "problems": []}
    if not meta_path.exists():
        out["problems"].append("columns_meta.json missing")
        return out
    meta = C.read_json(meta_path)
    if meta.get("probes_pass") is not True:
        out["problems"].append("probes_pass is not true")
    if meta.get("reads_results") is not False:
        out["problems"].append("reads_results is not false")
    if meta.get("columns_parquet_sha256") != C.sha256_file(J.columns_path(P)):
        out["problems"].append("the recorded columns_parquet_sha256 differs from the file")
    out["ok"] = not out["problems"]
    return out


def population(P: C.Paths) -> tuple[pd.DataFrame, list[str]]:
    info = J.history_info(P)                         # score.population + spd_B_M1; no result
    c = columns(P)
    return info.join(c.reindex(info.index)), scenarios(P)


def mode_shares(info: pd.DataFrame, scen: list[str]) -> dict:
    men = info.loc[S.population_ids(info, "men", S.TEST)]
    hist = info.loc[S.population_ids(info, "men", C.CAL_SEASONS)]
    out = {}
    for s in scen:
        m = men[f"mode_{s}"].astype(str)
        out[s] = {"share_L_2024_2026": float((m == "L").mean()),
                  "share_L_by_season": {str(y): float((g[f"mode_{s}"].astype(str) == "L").mean())
                                        for y, g in men.groupby("season")},
                  "share_L_2019_2023": float((hist[f"mode_{s}"].astype(str) == "L").mean())}
    return out


# ------------------------------------------------------------------------------------------------
# Arms

def paired(qb, qa, y, inf) -> dict:
    r = S.paired_stats(C.ll(qb, y), C.ll(qa, y), np.zeros(1), np.zeros(1), inf["block"].to_numpy(),
                       inf["week"].to_numpy())
    return {"matches": r["matches"], "estimate": r["estimate"], "lo": r["lo_block_only"], "hi": r["hi_block_only"]}


def gains(qb, qa, y, inf) -> dict:
    out = {"pooled": paired(qb, qa, y, inf)}
    for s in S.TEST:
        k = (inf["season"] == s).to_numpy()
        out[str(s)] = paired(qb[k], qa[k], y[k], inf[k])
    return out


def joint_parameters(sc: S.Scorer, info: pd.DataFrame, s: str, season: int) -> dict:
    """Descriptive: s_tour, b_T and b_L fitted together on 2019 .. season - 1 with the scenario's own columns and
    modes, eta the base's seeds 0-3 mean, debut out; each b shrunk with tau 0.05 by its own SE."""
    hist = tuple(range(C.CALIB_FROM, season))
    eta = sc.bank.eta("model", C.CAL_SEEDS, hist, "td")
    inf = info.reindex(eta.index)
    if inf["season"].max() >= season:
        raise RuntimeError("the joint fit read a season >= Y")
    keep = ~inf["debut"].to_numpy(bool)
    e, atp = eta.to_numpy()[keep], (inf["tour"].to_numpy() == "atp")[keep]
    is_t = (inf[f"mode_{s}"].astype(str).to_numpy() == "T")[keep]
    zt = np.where(is_t, inf[f"spd_T_{s}"].to_numpy(float)[keep], 0.0)
    zl = np.where(~is_t, inf[f"spd_L_{s}"].to_numpy(float)[keep], 0.0)
    yy = sc.y.reindex(eta.index[keep]).to_numpy(float)
    beta, se = C.fit_logistic(np.column_stack([np.where(atp, e, 0.0), np.where(~atp, e, 0.0), zt, zl]), yy)
    tau2 = C.TAU_NUDGE ** 2
    return {"s_atp": float(beta[0]), "s_wta": float(beta[1]), "b_T": float(beta[2]), "se_T": float(se[2]),
            "b_L": float(beta[3]), "se_L": float(se[3]), "b_T_shrunk": float(beta[2] * tau2 / (tau2 + se[2] ** 2)),
            "b_L_shrunk": float(beta[3] * tau2 / (tau2 + se[3] ** 2)), "rows": int(keep.sum())}


def scenario_arms(sc: S.Scorer, info: pd.DataFrame, coef: dict, s: str, with_joint: bool = True) -> dict:
    ids = S.population_ids(info, "men", S.TEST)
    inf = info.loc[ids]
    y = sc.y.reindex(ids).to_numpy(float)
    qb, _ = sc.forecast("model", S.SEEDS16, S.TEST, "td", "calibrated", ids)
    eta16 = sc.bank.eta("model", S.SEEDS16, S.TEST, "td").reindex(ids).to_numpy()
    zt, zl = inf[f"spd_T_{s}"].to_numpy(float), inf[f"spd_L_{s}"].to_numpy(float)
    modes = {"pure_T": "T", "pure_L": "L", "switch": inf[f"mode_{s}"].astype(str).to_numpy()}
    q = {a: J.apply(eta16, inf["tour"].to_numpy(), inf["season"].to_numpy(), m, zt, zl, coef) for a, m in modes.items()}
    out = {a: gains(qb, q[a], y, inf) for a in ARMS}
    better = max(("pure_T", "pure_L"), key=lambda a: out[a]["pooled"]["estimate"])
    out["switch_vs_better"] = {"better_pure_arm": better, **paired(q[better], q["switch"], y, inf),
                               "direction": f"positive = the switch has the lower log loss (better) than {better}"}
    if with_joint:
        params = {str(Y): joint_parameters(sc, info, s, Y) for Y in S.TEST}
        is_t = modes["switch"] == "T"
        logit = np.empty(len(ids))
        for Y, p in params.items():
            k = (inf["season"] == int(Y)).to_numpy()
            sl = np.where(inf["tour"].to_numpy() == "atp", p["s_atp"], p["s_wta"])
            logit[k] = sl[k] * eta16[k] + p["b_T_shrunk"] * np.where(is_t, zt, 0.0)[k] \
                + p["b_L_shrunk"] * np.where(~is_t, zl, 0.0)[k]
        out["joint"] = {**gains(qb, expit(logit), y, inf), "parameters": params, "descriptive": True}
    return out


def evaluate(bank: S.Bank, info: pd.DataFrame, y: pd.Series, scen: list[str], with_joint: bool = True) -> dict:
    coef = J.fit(bank, info, y, S.TEST)
    sc = S.Scorer(bank, info, y)
    return {"coefficients": coef, "scenarios": {s: scenario_arms(sc, info, coef, s, with_joint) for s in scen}}


def reproductions(res: dict, P: C.Paths) -> dict:
    """Under A: the switch equals pure T equals the study's S9 shrunk; under B: pure L equals the latency run's B-M1."""
    study = next(r for r in C.read_json(P.out / "results.json")["S9"] if r["cid"] == "S9_shrunk")
    lat = next(r for r in C.read_json(P.out / "latency" / "results_latency.json")["variants"]["spd_B_M1"]["S9"]
               if r["cid"] == "S9_shrunk")
    out = {}
    if "A" in res["scenarios"]:
        a = res["scenarios"]["A"]
        t, w = a["pure_T"]["pooled"], a["switch"]["pooled"]
        d = {k: max(abs(t[k] - study[k]), abs(w[k] - t[k])) for k in ("estimate", "lo", "hi")}
        out["A_switch_equals_pure_T_equals_S9"] = {"max_difference": d, "passed": max(d.values()) <= TOL}
    if "B" in res["scenarios"]:
        b = res["scenarios"]["B"]["pure_L"]["pooled"]
        d = {k: abs(b[k] - lat[k]) for k in ("estimate", "lo", "hi")}
        out["B_pure_L_equals_B_M1"] = {"max_difference": d, "passed": max(d.values()) <= TOL}
    out["passed"] = len(out) == 2 and all(v["passed"] for v in out.values())
    return out


def table(res: dict) -> pd.DataFrame:
    rows = []
    for s, arms in res["scenarios"].items():
        for a in ARMS + ("joint",):
            if a not in arms:
                continue
            for part in ["pooled"] + [str(y) for y in S.TEST]:
                r = arms[a][part]
                rows.append({"scenario": s, "arm": a, "seasons": part, **{k: r[k] for k in ("matches", "estimate",
                                                                                         "lo", "hi")},
                             "unit": "mLL", "direction": DIRECTION, "descriptive_only": a == "joint"})
        sv = arms["switch_vs_better"]
        rows.append({"scenario": s, "arm": f"switch_vs_{sv['better_pure_arm']}", "seasons": "pooled",
                     **{k: sv[k] for k in ("matches", "estimate", "lo", "hi")}, "unit": "mLL",
                     "direction": sv["direction"], "descriptive_only": False})
    t = pd.DataFrame(rows)
    t["verdict"] = ["better" if lo > 0 else "worse" if hi < 0 else "tie" for lo, hi in zip(t["lo"], t["hi"])]
    return t


# ------------------------------------------------------------------------------------------------
# Modes

def inputs_equal_study(P: C.Paths) -> dict:
    rec = C.read_json(P.out / "results.json")["hashes"]
    return {"scorer_code": rec["SCORER_CODE_SHA256"] == C.code_hash(),
            "model_frame": rec["MODEL_FRAME_SHA256"] == C.sha256_file(P.model_frame),
            "feature_file": rec["FEATURE_SHA256"] == C.sha256_file(P.feature_file)}


def base_missing(P: C.Paths) -> list:
    out = []
    for s in S.HIST:
        for k in S.SEEDS16:
            try:
                F.find_fit("model", s, k, P)
            except FileNotFoundError:
                out.append((s, k))
    return out


def check(P: C.Paths = C.DEFAULT) -> dict:
    info, scen = population(P)
    men = info.loc[S.population_ids(info, "men", S.TEST)]
    diffs = {}
    if "A" in scen:
        diffs["spd_T_A_vs_spd_f"] = float(np.abs(info["spd_T_A"] - info["spd_f"]).max())
        diffs["mode_A_all_T"] = bool((info["mode_A"].astype(str) == "T").all())
    if "B" in scen:
        diffs["spd_L_B_vs_spd_B_M1"] = float(np.abs(info["spd_L_B"] - info["spd_B_M1"]).max())
    coef = J.coefficients_path(P)
    out = {"what": "result-free check of the adaptive scorer's inputs (no outcome read)", "scenarios": scen,
           "mode_shares_men": mode_shares(info, scen),
           "values_men_2024_2026": {c: {"sd": float(men[c].std()), "nonzero": int((men[c] != 0).sum())}
                                    for s in scen for c in (f"spd_T_{s}", f"spd_L_{s}")},
           "reproduction_preconditions": diffs, "inputs_equal_study": inputs_equal_study(P),
           "coefficients_json": {"exists": coef.exists(),
                                 "agreement_with_published": C.read_json(coef).get("agreement_with_published")
                                 if coef.exists() else None},
           "base_fits_missing": base_missing(P), "reuse_checks": F.checks_passed(P),
           "columns_status": columns_status(P), "columns_sha256": C.sha256_file(J.columns_path(P))}
    C.write_json(J.folder(P) / "check_adaptive.json", out)
    return out


def synthetic(P: C.Paths = C.DEFAULT, scenario: str = "B", beta: float = 0.0, reps: int = 30, seed: int = 0,
              s_true: float = 0.9, tag: str | None = None) -> dict:
    """y ~ Bernoulli(expit(s_true eta + beta z)), z the scenario's switch column (spd_T where mode T, spd_L where L),
    for every 2019-2026 frame match; never reads a result. Coefficients refitted per replicate as in --run."""
    info, scen = population(P)
    bank = S.Bank(P, S.frame_index(P), require_checks=False)
    eta = bank.eta("model", S.SEEDS16, S.HIST, "td").reindex(info.index).to_numpy()
    is_t = info[f"mode_{scenario}"].astype(str).to_numpy() == "T"
    z = np.where(is_t, info[f"spd_T_{scenario}"].to_numpy(float), info[f"spd_L_{scenario}"].to_numpy(float))
    rng = np.random.default_rng(seed)
    rows = []
    for r in range(reps):
        y = pd.Series((rng.random(len(info)) < expit(s_true * eta + beta * z)).astype(float), index=info.index)
        res = evaluate(bank, info, y, [scenario], with_joint=True)["scenarios"][scenario]
        for a in ARMS + ("joint",):
            p = res[a]["pooled"]
            rows.append({"rep": r, "arm": a, "estimate": p["estimate"], "lo": p["lo"], "hi": p["hi"]})
        sv = res["switch_vs_better"]
        rows.append({"rep": r, "arm": "switch_vs_better", "estimate": sv["estimate"], "lo": sv["lo"], "hi": sv["hi"]})
    t = pd.DataFrame(rows)
    summary = {a: {"mean": float(g["estimate"].mean()), "reject_positive": float((g["lo"] > 0).mean()),
                   "reject_negative": float((g["hi"] < 0).mean())} for a, g in t.groupby("arm", sort=False)}
    out = {"what": "synthetic outcomes from a planted model; no match result read", "scenario": scenario,
           "beta": beta, "reps": reps, "seed": seed, "summary": summary, "replicates": t.to_dict(orient="records")}
    C.write_json(J.folder(P) / "synthetic" / f"{tag or f'{scenario}_b{beta:g}_r{reps}_s{seed}'}.json", out)
    return out


def run(P: C.Paths = C.DEFAULT) -> dict:
    jpath, cpath = J.folder(P) / "results_adaptive.json", J.folder(P) / "results_adaptive.csv"
    if jpath.exists() or cpath.exists():
        raise RuntimeError("results_adaptive exists: the exploratory outcome run happens once")
    same = inputs_equal_study(P)
    if not all(same.values()):
        raise RuntimeError(f"code or inputs differ from the study's frozen run: {same}")
    st = columns_status(P)
    if not st["ok"]:
        raise RuntimeError(f"the columns build is not passed: {st['problems']}")
    info, scen = population(P)
    if not {"A", "B"} <= set(scen):
        raise RuntimeError("scenarios A and B are needed for the reproductions")
    if base_missing(P):
        raise RuntimeError("base fits missing")
    if not all(F.checks_passed(P).values()):
        raise RuntimeError("reuse checks not passed")
    bank = S.Bank(P, S.frame_index(P), require_checks=True)
    y = S.labels(P)                                                            # the only result read
    res = evaluate(bank, info, y, scen)
    rep = reproductions(res, P)
    if not rep["passed"]:
        raise RuntimeError(f"the reproductions failed; nothing written: {rep}")
    coef_json = J.coefficients_path(P)
    res.update({"what": "EXPLORATORY (adaptive/plan.md); 2024-2026 results were already read", "reproductions": rep,
                "mode_shares_men": mode_shares(info, scen),
                "coefficients_equal_json": (J.agreement(res["coefficients"], {m: C.read_json(coef_json)[m]
                                                                              for m in J.MODES})
                                            if coef_json.exists() else None),
                "hashes": {"columns_sha256": C.sha256_file(J.columns_path(P)),
                           "plan_sha256": C.sha256_file(J.folder(P) / "plan.md") if (J.folder(P) / "plan.md").exists()
                           else None, "scorer_code_sha256": C.code_hash()},
                "key": "mLL against the calibrated base, positive = the arm better, block-only interval; the switch "
                       "against the better pure arm, positive = the switch better; joint = descriptive"})
    C.write_json(jpath, res)
    table(res).to_csv(cpath, index=False)
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--synthetic", action="store_true")
    g.add_argument("--run", action="store_true")
    ap.add_argument("--scenario", default="B")
    ap.add_argument("--beta", type=float, default=0.0)
    ap.add_argument("--reps", type=int, default=30)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    if a.check:
        out = check()
        print(json.dumps({k: out[k] for k in ("scenarios", "mode_shares_men", "reproduction_preconditions",
                                              "inputs_equal_study")}, indent=1))
        return 0
    if a.synthetic:
        print(json.dumps(synthetic(scenario=a.scenario, beta=a.beta, reps=a.reps, seed=a.seed)["summary"], indent=1))
        return 0
    res = run()
    print(json.dumps(res["reproductions"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
