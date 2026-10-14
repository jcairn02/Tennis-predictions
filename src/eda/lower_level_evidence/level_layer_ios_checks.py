"""Extra checks of the IOS-family level layer (role C2), beside level_layer_ios.py's gates. Each reads inputs, solver
outputs or a sandbox's tables; none reads an outcome of 2025-2026 (the form (b) demo stops its history at 29 Dec 2024).
Outputs go to data/studies/lower_level_evidence/system/ios_layer/gates/ (and fe_demo/).

    --mapping SB LABEL          lane 3's mapping check (surface_ios/arms.py:83-91) on a sandbox's hooked outputs, on the
                                reference frame's matches: lane 2's "current" runs against the IOS part's pooled IOS, to
                                1e-12 -> gates/mapping_<LABEL>.json
    --products LABEL            each IOS-family input's SD by tour and season, the reference against a config's inputs
                                (inputs/<LABEL>.parquet), as a ratio to 2024 (input audit finding #6)
                                -> gates/products_spread_<LABEL>.csv
    --decided-active-set SB TOUR STAT
                                the decided ios_surface.run on the full history against itself without ITF/ITFQ rows,
                                single-threaded, on the rows before the tour's first ITF box score
                                -> gates/decided_active_set_<TOUR>_<STAT>.json
    --hooked-path SB            run FROM the sandbox (its own copies are imported): the patched rebuild.ios_features on
                                Jan-Jun 2023 with LLE_LAYER against the decided code -> gates/hooked_path_<config>.json
    --fe-demo SB TOUR STAT      form (b) on real rows: the level effects at the last 2024 snapshot and the change of
                                main-tour ratings 2019-2024 -> fe_demo/<TOUR>_<STAT>.json
    --fe-surfzero SB TOUR STAT RUNS
                                run FROM the sandbox, as --hooked-path: one lane-2 pooled run (kappa_s = inf) of the
                                sandbox's build with the rows' surfaces zeroed, against the stored lane-2 run in
                                full_runs/RUNS and against the IOS part's inputs (leakproof_features.parquet), on the tour's
                                pool matches -> gates/fe_surfzero_<TOUR>_<STAT>.json. First run 10 Oct 2026 00:55 UTC on the
                                SYS build (module 077c760a, whose run_surface split the pooled form-(b) run by surface): the
                                diagnosis behind run_surface's zeroed surfaces in 3fa5f69e

Run (repository root): ./python.sh src/eda/lower_level_evidence/level_layer_ios_checks.py --mapping C:/Users/zerom/tnr_sys_ios SEP_ALL
--hooked-path imports the sandbox's modules, so it runs with the sandbox's python path:
    cd SB && LLE_LAYER=<config> python <repo>/src/eda/lower_level_evidence/level_layer_ios_checks.py --hooked-path SB
"""
from __future__ import annotations

import os
for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # a script, never imported by a builder: the builders' single-threaded BLAS

import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
GATES = REPO / "data" / "studies" / "lower_level_evidence" / "system" / "ios_layer" / "gates"


def _repo_imports():
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from src.eda.lower_level_evidence import level_layer_ios as L
    return L


SYSTEM = REPO / "data" / "studies" / "lower_level_evidence" / "system"
PHASE2_ARMS = ("SYS", "SYS_w0", "SYS_w50", "SYS_w100", "SYS_NOCLASS", "SYS_BOTH", "SYS_ITFASIS", "SYS_BOTH_ITFASIS")


def phase2_config(arm: str) -> dict:
    """C1's system_arms.phase2_config for an arm (SPEC 7, pre-registration addition 1), without its checkpoint-1 key: the
    same params (params_noclass for SYS_NOCLASS), classes, strength, floor, missing_params and solve_w. So the IOS
    fingerprint equals the arm's, and this family's gated inputs are the arm's 22 IOS columns."""
    import hashlib
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()   # noqa: E731
    rel = SYSTEM / "relationship"
    params = rel / ("params_noclass.parquet" if arm == "SYS_NOCLASS" else "params.parquet")
    classes = SYSTEM / "classes" / "classes.csv"
    ri = json.loads((SYSTEM / "arms" / "reference_inputs.json").read_text(encoding="utf-8"))
    fam = {"points_52w": True, "forms": True, "ios": True, "ios_points_short": True, "ratings_iid": True, "elo": True}
    cfg = {"name": arm, "params": str(params), "params_sha256": sha(params), "classes": str(classes),
           "classes_sha256": sha(classes), "strength": {"path": ri["strength"]["path"], "sha256": ri["strength"]["sha256"]},
           "translate": True, "weight": "fitted", "weight_results": "fitted", "prior": "pool", "itf_box": "exclude",
           "tours": ["atp"], "families": fam, "params_season_floor": 2013, "missing_params": "error",
           "solve_w": "w_joint", "ratings_level_term": "none"}
    dose = {"SYS_w0": 0.0, "SYS_w50": 0.5, "SYS_w100": 1.0}
    if arm in dose:
        cfg["weight"] = dose[arm]
    elif arm == "SYS_NOCLASS":
        cfg["classes"], cfg["classes_sha256"] = None, None
    elif arm in ("SYS_BOTH", "SYS_BOTH_ITFASIS"):
        cfg["tours"], cfg["missing_params"] = ["atp", "wta"], "untouched"
    if arm in ("SYS_ITFASIS", "SYS_BOTH_ITFASIS"):
        cfg["itf_box"] = "as_is"
    cfg["what"] = f"C2's gate copy of C1's {arm} config (system_arms.phase2_config, no checkpoint-1 key)"
    return cfg


def write_phase2_configs() -> dict:
    L = _repo_imports()
    out = {}
    d = L.OUT / "configs"
    d.mkdir(parents=True, exist_ok=True)
    for arm in PHASE2_ARMS:
        cfg = phase2_config(arm)
        L.validate_config(dict(cfg), arm)
        p = d / f"{arm}.json"
        text = json.dumps(cfg, indent=1) + "\n"
        if p.exists() and p.read_text(encoding="utf-8") != text:
            raise SystemExit(f"{p} exists with other content; a config is never changed in place")
        if not p.exists():
            p.write_text(text, encoding="utf-8")
        out[arm] = {"path": str(p), "fingerprint": L.fingerprint(L.validate_config(dict(cfg), arm))}
    print(json.dumps(out, indent=1))
    return out


def mapping(sb: str, label: str) -> dict:
    import numpy as np
    import pandas as pd
    L = _repo_imports()
    from src.eda.surface_ios import arms as SA
    sb = Path(sb)
    ref = L.reference_frame(["match_id", "tour", "season"])
    sf = pd.read_parquet(sb / "data/studies/surface_ios/surface_features.parquet")
    sf = ref[["match_id"]].merge(sf, on="match_id", how="left", validate="one_to_one")
    lp = pd.read_parquet(sb / "data/studies/match_timing/leakproof_features.parquet")
    lp = ref[["match_id"]].merge(lp, on="match_id", how="left", validate="one_to_one")
    out = {"label": label, "sandbox": str(sb), "matches": int(len(ref)), "checks": {},
           "records": L.consistency(sb)["got"]}
    worst, ok = 0.0, True
    for s in L.PROFILE:
        for kind, col in (("curO", f"ios_O_{s}|single"), ("curD", f"ios_D_{s}|single"), ("curprod", f"prod_{s}|single")):
            got = SA.recipe(f"{kind}_{s}", sf)
            want = lp[col].to_numpy(dtype="float64")
            gap = float(np.nanmax(np.abs(got - want)))
            same_nan = bool(np.array_equal(np.isnan(got), np.isnan(want)))
            out["checks"][col] = {"max_abs_gap": gap, "same_missing": same_nan}
            worst = max(worst, gap)
            ok &= (gap <= 1e-12) and same_nan
    out.update({"largest_gap": worst, "pass": bool(ok)})
    (GATES / f"mapping_{label}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"mapping check {label}: {'PASS' if ok else 'FAIL'}; largest gap {worst:.3g}; records {out['records']}")
    return out


def products(label: str):
    import numpy as np
    import pandas as pd
    L = _repo_imports()
    ref = L.reference_frame(["match_id", "tour", "season"] + [f"in_{n}" for n in L.IOS_INPUTS])
    got = pd.read_parquet(L.OUT / "inputs" / f"{label}.parquet")
    if not np.array_equal(ref["match_id"].to_numpy(), got["match_id"].to_numpy()):
        raise ValueError("the inputs are not on the reference frame's matches in its order")
    rows = []
    for n in L.IOS_INPUTS:
        for (tour, season), ix in ref.groupby(["tour", "season"]).indices.items():
            a = ref[f"in_{n}"].to_numpy(float)[ix]
            b = got[f"in_{n}"].to_numpy(float)[ix]
            rows.append({"input": n, "tour": tour, "season": int(season), "matches": int(len(ix)),
                         "sd_reference": float(np.nanstd(a)), f"sd_{label}": float(np.nanstd(b)),
                         "changed": int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())})
    t = pd.DataFrame(rows)
    for col in ("sd_reference", f"sd_{label}"):
        base = t[t["season"] == 2024].set_index(["input", "tour"])[col]
        t[col.replace("sd_", "ratio_to_2024_")] = [r[col] / base.get((r["input"], r["tour"]), np.nan)
                                                   for r in t.to_dict("records")]
    t.to_csv(GATES / f"products_spread_{label}.csv", index=False)
    show = t[t["input"].str.startswith("prod_") & t["season"].between(2022, 2026)]
    print(show.pivot_table(index=["input", "tour"], columns="season",
                           values=["ratio_to_2024_reference", f"ratio_to_2024_{label}"]).round(3).to_string())
    return t


def decided_active_set(sb: str, tour: str, stat: str) -> dict:
    import numpy as np
    L = _repo_imports()
    from src.eda.ios_constants import registry as IC
    from src.eda.surface_ios import ios_surface as IS
    td = L._load_cache_tour(sb, tour)
    st = td["stats"][stat]
    itf = np.isin(td["lle_bucket"], [L.CODE["ITF"], L.CODE["ITFQ"]])
    td2 = dict(td, stats={**td["stats"], stat: {**st, "ok": st["ok"] & ~itf}})
    chosen, typ = IC.ios_constants()
    c = chosen[(tour, stat)]
    ch = IC.surface_choice()[f"{tour}|{stat}"]
    h, ks = c["h"] * ch["h_mult"], c["kappa"] * ch["ks_mult"]
    full = IS.run(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)])
    noitf = IS.run(td2, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)])
    first = L.first_release_by_tour()[tour]["es_min"]
    pre = td["es"] < first
    out = {"tour": tour, "stat": stat, "first_itf_es": first, "rows_before": int(pre.sum()),
           "players_in_system": [full["solver"]["players"], noitf["solver"]["players"]], "by_key": {}}
    for k in ("O_eff", "D_eff", "E", "F"):
        a, b = full[k][pre], noitf[k][pre]
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        both = np.isfinite(a) & np.isfinite(b)
        out["by_key"][k] = {"not_bitwise": int((~same).sum()),
                            "largest_abs_difference": float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0}
    (GATES / f"decided_active_set_{tour}_{stat}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out


def hooked_path(sb: str) -> dict:
    """Imports the SANDBOX's modules (sys.path first): run from the sandbox, with LLE_LAYER set, nothing of the
    repository's src imported before."""
    if "src" in sys.modules:
        raise RuntimeError("--hooked-path must import the sandbox's src first; run it as its own process")
    sys.path.insert(0, sb)
    os.chdir(sb)
    import numpy as np
    import pandas as pd
    from src.eda.match_timing import common as MT
    from src.eda.match_timing import rebuild as RB
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic import stage1_baselines as E
    from src.eda.feature_alpha_audit.repair_data import repair_tables
    from src.eda.lower_level_evidence import level_layer as LL
    if not Path(RB.__file__).resolve().is_relative_to(Path(sb).resolve()):
        raise RuntimeError(f"imported {RB.__file__}, not the sandbox's")
    timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"])
    m = C.load_matches()
    m = m[m["tournament_date"].between(pd.Timestamp("2023-01-01"), pd.Timestamp("2023-06-30"))].reset_index(drop=True)
    ids = set(m["match_id"])
    p = pd.read_parquet(C.MATCH_PLAYERS)
    p = p[p["match_id"].isin(ids)].reset_index(drop=True)
    odds = pd.read_parquet(E.ODDS)
    tm = timing[timing["match_id"].isin(ids)].reset_index(drop=True)
    mm, pp, _ = repair_tables(m, p)
    rows = RB.build_rows(mm, pp, odds)
    cfg = os.environ.get("LLE_LAYER", "")
    hooked, meta = RB.ios_features(rows, tm)
    os.environ.pop("LLE_LAYER", None)
    LL._CFG.clear()
    decided, meta0 = RB.ios_features(rows, tm)
    out = {"config": cfg, "slice": ["2023-01-01", "2023-06-30"], "pool_matches": int(len(next(iter(hooked.values())))),
           "differs": {}, "layer_records": {}}
    for k in hooked:
        a, b = np.asarray(hooked[k], float), np.asarray(decided[k], float)
        out["differs"][k] = int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
    for k, v in meta.items():
        rec = v.get("lle_layer") or {}
        out["layer_records"][k] = {"hooked": bool(rec), "level_effects": rec.get("level_effects"),
                                   "dropped_rows": rec.get("dropped_rows")}
    out["decided_has_no_record"] = not any(v.get("lle_layer") for v in meta0.values())
    name = Path(cfg).stem if cfg else "none"
    (GATES / f"hooked_path_{name}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps({"differs": out["differs"], "hooked": sum(r["hooked"] for r in out["layer_records"].values()),
                      "solves": len(out["layer_records"]), "decided_has_no_record": out["decided_has_no_record"]},
                     indent=1))
    return out


def fe_surfzero(sb: str, tour: str, stat: str, runs_name: str) -> dict:
    """Imports the SANDBOX's modules (as hooked_path); LLE_LAYER = the build's config. Writes gates/fe_surfzero_*.json."""
    if "src" in sys.modules:
        raise RuntimeError("--fe-surfzero must import the sandbox's src first; run it as its own process")
    import time
    sb_ = Path(sb)
    sys.path.insert(0, str(sb_))
    import numpy as np
    import pandas as pd
    from src.eda.surface_ios import common as C
    from src.eda.lower_level_evidence import level_layer_ios as L
    for mod in (C, L, L.LL):
        if not Path(mod.__file__).resolve().is_relative_to(sb_.resolve()):
            raise RuntimeError(f"imported {mod.__file__}, not the sandbox's")
    chosen, typ = C.ios_constants()
    c = chosen[(tour, stat)]
    td = C.load_tour(tour)
    td0 = dict(td, surf=np.zeros(len(td["pid"]), dtype=np.int64))
    t0 = time.time()
    res = L.run_surface(td0, stat, c["h"] * 1.0, c["kappa"], np.inf, c["tau"], typ[(stat, tour)])
    secs = round(time.time() - t0, 1)

    def gap(a, b):
        a, b = np.asarray(a, dtype="float64"), np.asarray(b, dtype="float64")
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        fin = np.isfinite(a) & np.isfinite(b)
        return {"max_abs_gap": float(np.max(np.abs(a[fin] - b[fin]))) if fin.any() else 0.0,
                "cells_not_bitwise_equal": int((~same).sum()),
                "same_missing": bool(np.array_equal(np.isnan(a), np.isnan(b)))}

    out = {"tour": tour, "stat": stat, "seconds": secs, "config": os.environ.get("LLE_LAYER"),
           "solver": {k: v for k, v in res["solver"].items() if k != "lle_layer"}, "module": L.__file__,
           "level_layer": L.LL.__file__}
    cur = np.load(sb_ / "data/studies/surface_ios/full_runs" / runs_name / f"{tour}_{stat}_current.npz")
    out["vs_stored_lane2_run"] = {k: gap(res[k], cur[k]) for k in ("O_eff", "D_eff")}
    pool = pd.read_parquet(sb_ / "data/studies/surface_ios/cache/pool.parquet")
    sel = (pool["tour"] == tour).to_numpy()
    a, b = pool.loc[sel, "pos_a"].to_numpy(), pool.loc[sel, "pos_b"].to_numpy()
    cols = [f"ios_O_{stat}|single", f"ios_D_{stat}|single", f"prod_{stat}|single"]
    lp = pd.read_parquet(sb_ / "data/studies/match_timing/leakproof_features.parquet", columns=["match_id"] + cols)
    lp = pd.DataFrame({"match_id": pool.loc[sel, "match_id"].to_numpy()}).merge(lp, on="match_id", how="left",
                                                                                validate="one_to_one")
    for name, src in (("this_run_zeroed_surfaces", res), ("stored_lane2_run", cur)):
        O, D = np.asarray(src["O_eff"]), np.asarray(src["D_eff"])
        mine = {cols[0]: O[a] - O[b], cols[1]: D[a] - D[b], cols[2]: O[a] * (-D[b]) - O[b] * (-D[a])}
        out[f"{name}_vs_ios_part"] = {k: gap(mine[k], lp[k].to_numpy()) for k in cols}
    out["matches"] = int(sel.sum())
    (GATES / f"fe_surfzero_{tour}_{stat}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out


def fe_demo(sb: str, tour: str, stat: str) -> dict:
    import time
    import numpy as np
    L = _repo_imports()
    from src.eda.lower_level_evidence import common as LC
    from src.eda.ios_constants import registry as IC
    td = L._load_cache_tour(sb, tour)
    cut = int((np.datetime64(LC.HOLDOUT_START.date(), "D") - np.datetime64(1, "D")).astype("int64"))
    keep = td["lf"] + 1 <= cut           # no row released after 29 Dec 2024 reaches any snapshot
    st = td["stats"][stat]
    td = dict(td, stats={**td["stats"], stat: {**st, "ok": st["ok"] & keep}})
    chosen, typ = IC.ios_constants()
    c = chosen[(tour, stat)]
    ch = IC.surface_choice()[f"{tour}|{stat}"]
    ks, h = c["kappa"] * ch["ks_mult"], c["h"] * ch["h_mult"]
    n = len(td["pid"])
    bucket = td["lle_bucket"]
    levels = [b for b in ("TQ", "GSQ", "CH", "CHQ") if ((bucket == L.CODE[b]) & st["ok"] & keep).any()]
    code = np.full(n, -1, np.int64)
    for j, b in enumerate(levels):
        code[bucket == L.CODE[b]] = j
    mult = np.where(np.isin(bucket, [L.CODE["ITF"], L.CODE["ITFQ"]]), 0.0, 1.0)
    t0 = time.time()
    plain = L.solve_surface(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)], mult, np.zeros(n), until_day=cut)
    t_plain = time.time() - t0
    t0 = time.time()
    fe = L.solve_fe(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)], mult, code, until_day=cut)
    t_fe = time.time() - t0
    last = np.nanargmax(np.where(np.isfinite(fe["O_snap"]), td["es"], -np.inf))
    main = (bucket == L.CODE["MAIN"]) & np.isfinite(fe["O_eff"]) & (td["year"] >= 2019)
    out = {"tour": tour, "stat": stat, "h": h, "kappa": c["kappa"], "kappa_s": ks, "tau": c["tau"], "cut_day": cut,
           "levels": levels, "beta_at_last_snapshot_2024": dict(zip(levels, [float(v) for v in fe["beta_rows"][last]])),
           "seconds_plain": round(t_plain, 1), "seconds_fe": round(t_fe, 1),
           "iterations_mean_plain": plain["solver"]["iterations_mean"],
           "iterations_mean_fe": fe["solver"]["iterations_mean"],
           "not_converged": [plain["solver"]["not_converged"], fe["solver"]["not_converged"]],
           "main_tour_rows_2019_2024": int(main.sum()),
           "median_abs_change_main_2019_2024": {k: float(np.nanmedian(np.abs(fe[k][main] - plain[k][main])))
                                                for k in ("O_eff", "D_eff")},
           "sd_main_2019_2024": {k: float(np.nanstd(plain[k][main])) for k in ("O_eff", "D_eff")},
           "note": "ITF and ITFQ rows dropped; history released by 29 Dec 2024 only"}
    d = GATES.parent / "fe_demo"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{tour}_{stat}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))
    return out


def _direction_task(args):
    cache_dir, tour, stat, cfg_path = args
    import time
    import numpy as np
    L = _repo_imports()
    from src.eda.lower_level_evidence import common as LC
    from src.eda.ios_constants import registry as IC
    os.environ["LLE_LAYER"] = cfg_path
    L.LL._CFG.clear()
    cfg = L.config()
    with np.load(Path(cache_dir) / f"{tour}.npz", allow_pickle=False) as z:
        td = {k: z[k] for k in z.files}
    from src.eda.surface_ios import common as SC
    td["stats"] = {s: {"ok": td.pop(f"{s}__ok"), "x": td.pop(f"{s}__x"), "d": td.pop(f"{s}__d"),
                       "y": td.pop(f"{s}__y"), "mu": td.pop(f"{s}__mu")} for s in SC.STATS}
    td["n_players"], td["tour"] = int(td["n_players"]), tour
    cut = int((np.datetime64(LC.HOLDOUT_START.date(), "D") - np.datetime64(1, "D")).astype("int64"))
    keep = td["lf"] + 1 <= cut                     # no row released after 29 Dec 2024 reaches any snapshot
    st = td["stats"][stat]
    td["stats"][stat] = {**st, "ok": st["ok"] & keep}
    plan = L.row_plan(td, stat, "ios")
    out = {"tour": tour, "stat": stat, "config": cfg["name"], "levels": list(plan.fe_levels)}
    if not L._has_fe(plan):
        out["note"] = "no level effect for this statistic"
        return out
    chosen, typ = IC.ios_constants()
    c = chosen[(tour, stat)]
    ch = IC.surface_choice()[f"{tour}|{stat}"]
    h, ks = c["h"] * ch["h_mult"], c["kappa"] * ch["ks_mult"]
    n = len(td["pid"])
    t0 = time.time()
    fe = L.solve_fe(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)], plan.mult, plan.fe_code,
                    kappa_beta=c["kappa"], until_day=cut)
    plain = L.solve_surface(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)], plan.mult, np.zeros(n),
                            until_day=cut)
    main = (td["lle_bucket"] == L.CODE["MAIN"]) & (td["year"] >= 2013) & np.isfinite(fe["O_eff"])
    beta = np.nan_to_num(fe["beta_rows"])
    pred_o = -(beta * np.nan_to_num(fe["share_srv_rows"])).sum(axis=1)
    pred_d = (beta * np.nan_to_num(fe["share_ret_rows"])).sum(axis=1)
    res = {}
    for side, dk, pred in (("O", "O_eff", pred_o), ("D", "D_eff", pred_d)):
        d = fe[dk][main] - plain[dk][main]
        p = pred[main]
        sd = float(np.std(p))
        corr = float(np.corrcoef(d, p)[0, 1]) if sd > 0 and np.std(d) > 0 else float("nan")
        slope = float(np.dot(p - p.mean(), d - d.mean()) / np.dot(p - p.mean(), p - p.mean())) if sd > 0 else float("nan")
        nz = np.abs(p) > 1e-6
        res[side] = {"rows": int(main.sum()), "sd_change": float(np.std(d)), "sd_predicted": sd,
                     "correlation": corr, "slope": slope,
                     "same_sign_share": float(np.mean(np.sign(d[nz]) == np.sign(p[nz]))) if nz.any() else float("nan")}
    last = np.nanargmax(np.where(np.isfinite(fe["O_snap"]), td["es"], -np.inf))
    out.update({"beta_2024": dict(zip(plan.fe_levels, [float(v) for v in fe["beta_rows"][last]])),
                "seconds": round(time.time() - t0, 1), **res})
    return out


def direction(cache_dir: str, workers: int = 3) -> dict:
    """The direction gate of form (b), inputs-only, history released by 29 Dec 2024 only. For SYS (men) and SYS_BOTH
    (women), every statistic with a level effect: the surface solve with the level term against the same solve without
    it (the same fitted w), on main-tour rows of 2013-2024. Fitting beta_L shifts a server's rating by about -beta_L x
    his share of serve weight at L, and a returner's by +beta_L x his share of return weight (the term no longer loads
    onto the players): the change must correlate positively with that prediction. Required where the prediction varies
    (SD over 1e-4); the slope (about 1 for a player whose rating rests on his own rows) is reported."""
    from concurrent.futures import ProcessPoolExecutor
    L = _repo_imports()
    d = L.OUT / "configs"
    tasks = [(cache_dir, "atp", s, str(d / "SYS.json")) for s in L.PROFILE + ("spw",)]
    tasks += [(cache_dir, "wta", s, str(d / "SYS_BOTH.json")) for s in L.PROFILE + ("spw",)]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        rows = list(ex.map(_direction_task, tasks))
    req = [r for r in rows if "O" in r]
    checks = []
    for r in req:
        for side in ("O", "D"):
            v = r[side]
            required = v["sd_predicted"] > 1e-4
            checks.append({"tour": r["tour"], "stat": r["stat"], "side": side, "required": required,
                           "correlation": v["correlation"], "pass": (v["correlation"] > 0) if required else None})
    ok = all(c["pass"] for c in checks if c["required"])
    out = {"gate": "direction of form (b)", "cut": "rows released by 29 Dec 2024; main-tour rows 2013-2024",
           "pass": bool(ok), "required": sum(c["required"] for c in checks),
           "passed": sum(bool(c["pass"]) for c in checks if c["required"]), "checks": checks, "by_solve": rows}
    (GATES / "direction_form_b.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for r in req:
        print(f"{r['tour']} {r['stat']:10s} levels {','.join(r['levels']):10s} O corr {r['O']['correlation']:+.3f} "
              f"slope {r['O']['slope']:+.2f} | D corr {r['D']['correlation']:+.3f} slope {r['D']['slope']:+.2f} | "
              f"beta_2024 {r['beta_2024']}")
    print(f"direction gate: {'PASS' if ok else 'FAIL'} ({out['passed']} of {out['required']} required)")
    return out


def compare_inputs_files(a: str, b: str) -> dict:
    """Two collected input files (inputs/<label>.parquet) bit for bit: SYS_w0 against SEP_ALL (the w = 0 equivalence)."""
    import numpy as np
    import pandas as pd
    L = _repo_imports()
    x = pd.read_parquet(L.OUT / "inputs" / f"{a}.parquet")
    y = pd.read_parquet(L.OUT / "inputs" / f"{b}.parquet")
    if not np.array_equal(x["match_id"].to_numpy(), y["match_id"].to_numpy()):
        raise ValueError("not the same matches in the same order")
    by = {}
    for n in L.IOS_INPUTS:
        u, v = x[f"in_{n}"].to_numpy(float), y[f"in_{n}"].to_numpy(float)
        same = (u == v) | (np.isnan(u) & np.isnan(v))
        by[n] = int((~same).sum())
    out = {"gate": f"{a} against {b}, bit for bit", "matches": int(len(x)), "not_bitwise_by_input": by,
           "pass": all(v == 0 for v in by.values())}
    (GATES / f"equivalence_{a}_{b}.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"{a} vs {b}: {'PASS' if out['pass'] else 'FAIL'} ({sum(by.values())} cells differ)")
    return out


def main() -> int:
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    cmd, args = a[0], a[1:]
    if cmd == "--phase2-configs":
        write_phase2_configs()
        return 0
    if cmd == "--direction":
        return 0 if direction(*args)["pass"] else 1
    if cmd == "--equivalence":
        return 0 if compare_inputs_files(*args)["pass"] else 1
    if cmd == "--mapping":
        return 0 if mapping(*args)["pass"] else 1
    if cmd == "--products":
        products(*args)
        return 0
    if cmd == "--decided-active-set":
        decided_active_set(*args)
        return 0
    if cmd == "--hooked-path":
        hooked_path(*args)
        return 0
    if cmd == "--fe-demo":
        fe_demo(*args)
        return 0
    if cmd == "--fe-surfzero":
        fe_surfzero(*args)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
