"""The level layer inside the model's joint solves: role C2 of the level-evidence system (lower_level_evidence).

The families (docs/studies/lower_level_evidence/system/SPEC.md §3, the "joint solves" row):
    ios                the surface IOS: iosO_* and iosD_* on seven statistics (14 inputs), and the products prod_* (7),
                       which follow from them (surface_ios/arms.py, recipe: prod = O_A (-D_B) - O_B (-D_A), on the
                       surface-effective O and D). Also the pooled leak-proof IOS of match_timing/rebuild.py, an
                       intermediate of the chain that lane 3's mapping check (surface_ios/arms.py) ties to lane 2's
                       "current" runs, so both are hooked alike
    ios_points_short   the short-memory IOS points matchup: ios_time.run_timed on spw with half-life 4 weeks (men) /
                       13 (women), turned into a match probability by stageB_ios.matchup_points (rebuild.py:199-221)

What the chain rebuilds (run_chain.py's lanes; checked 9 Oct 2026):
    lane 2 rebuilds the surface IOS from Stage 0 (build_cache.py, then build_features.py: every "current" and "surface"
    full-history run; the sandbox copy excludes full_runs/, so nothing is reused). Lane 3 turns them into the 21 inputs.
    ios_points_short and the pooled IOS are READ STORED: lane 1's leakproof_frame (tabpfn_leakproof/build_frame.py),
    elo_frames (surface_elo_pieces/build_frames.py) and lane 3's frames.py read match_timing/leakproof_features.parquet,
    which only match_timing/rebuild.py writes (run_chain's lane 0, a candidate's step, "not yet exercised"). A build
    whose layer touches this family therefore runs, in the sandbox, before lane 1's leakproof_frame:
        rebuild.py --part ios     the timed solves (7 statistics "tuned" + spw "short", both tours), hooked
        rebuild.py --part merge   leakproof_features.parquet = the stored per-player part + the new IOS part
    (run_ios_part() below, or --run-ios-part). The guards make an out-of-order build fail instead of mixing configs.
    A candidate Stage 0 with new matches runs run_chain's lane 0 instead (its timing_features step is rebuild.py in full,
    whose IOS part this patch hooks): the merge alone would join the stored per-player part of the old pool.

SWITCHED OFF BY DEFAULT. LLE_LAYER names the layer config (SPEC §6.3). Unset, every hook returns its input object
unchanged and every solve is the decided builder's own function. Set, a solve of a tour the config names, in a family
the config switches on, runs the solver variants below, which are the decided solvers (ios_time.run_timed,
ios_surface.run) with two per-row arrays added:

    m_k      the row's exchange rate: its weight is (d_k / d_typical)^tau 2^(-age/h) x m_k. MAIN and TEAM rows: 1.
             A row with m_k = 0 is dropped, exactly as if it had no box score (it leaves the system, its pairs and
             the incremental step), so "w = 0" is a physical exclusion, not a near-zero weight
    delta_k  the level term in the solve's own units (the centred logit of the statistic's rate per opportunity, the
             IOS's y): y_k <- y_k - delta_k, lower-level rows only. Form (a) of SPEC §3: a supplied delta

With every m_k = 1 and delta_k = 0 the variants perform the decided solvers' floating-point operations in the same order
(x * 1.0 and y - 0.0 are exact), so the identity config reproduces the reference bit for bit.

The settings (the lead's rulings of 9 Oct 2026, Phase 2):
    m_k        the arm's number, or with weight "fitted" role B's w_joint (relationship/params.parquet, method F4: the
               mean of the serve statistic's and its receiving side's w) for the solve's serve-side statistic (spw for
               ios_points_short), the row's level and its own season (params_season_floor 2013 for 2010-2012 rows),
               as fitted (B's cap 3); missing_params "untouched" leaves a cell with no parameter at 1; ITF and ITFQ 0
               under itf_box "exclude", untouched under "as_is". Read through C1's level_layer.weights
    level term translate true: form (b), solve_fe below: a level effect estimated inside each snapshot's solve, at role
               A's delta_levels of the solve's statistic (classes.csv, kind "stat"; "none": no term), every lower level
               but ITF/ITFQ when the classes are null (SYS_NOCLASS). A solve with no level effect left (e.g. w = 0 at
               every lower level) runs the plain variant. Form (a), a supplied delta, stays in the solvers, switched off
               in the config path
    prior      "pool" only: role B's method F4 did not keep the newcomer prior, and no tier means are in the solve

The sandbox patch (apply_patch; never the repository), each edit anchored on text found exactly once:
    match_timing/rebuild.py        import; ios_features: annotate_td(td, rows); _ios_task: run_timed(..., label=label);
                                   part_ios: stamp(meta) into ios_features_summary.json
    surface_ios/build_cache.py     import; annotate_cache(arrays, rows, idx) before each tour's npz
    surface_ios/build_features.py  import; RUNS = runs_dir(...) (a folder per layer config, so a sandbox never reuses
                                   another config's runs); task: run_surface(...); stamp(...) into build_features.json
    tabpfn_leakproof/build_frame.py   require_consistent(ROOT, "ios_part") at the start of main()
    surface_ios/arms.py            require_consistent(ROOT, "both") at the start of main()
    surface_ios/probe.py           the probe's td gets its tour and levels; run_surface in place of IS.run

Run (from the repository root):
    ./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox SB --apply-patch | --check-patch
    LLE_LAYER=<config> ./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox SB --run-ios-part [--out D]
    ./python.sh src/eda/lower_level_evidence/level_layer_ios.py --write-configs
    ./python.sh src/eda/lower_level_evidence/level_layer_ios.py --sandbox SB --collect-inputs LABEL [--config CFG]
    ./python.sh src/eda/lower_level_evidence/level_layer_ios.py --gate-identity LABEL | --gate-drop CFG [...]
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402

ENV = "LLE_LAYER"
IOS_VERSION_ENV = "IOS_CONSTANTS_VERSION"
IOS_VERSION = "2026-10-08_reference"
PY = "C:/Users/zerom/miniforge3/envs/tennis/python.exe"
STAGE0_MATCHES = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
OUT = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "ios_layer"
TOURS = ("atp", "wta")
FAMILIES = ("ios", "ios_points_short")
BUCKETS = tuple(LC.BUCKETS)                         # MAIN TQ GSQ CH CHQ ITF ITFQ TEAM
CODE = {b: i for i, b in enumerate(BUCKETS)}
LOWER = tuple(LC.LOWER)                             # TQ GSQ CH CHQ ITF ITFQ (TEAM is kept apart, as MAIN)
LOWER_CODES = np.array([CODE[b] for b in LOWER], dtype=np.int8)
ITF_CODES = np.array([CODE["ITF"], CODE["ITFQ"]], dtype=np.int8)


def log(msg: str) -> None:
    print(f"[level_layer_ios] {msg}", flush=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------
# The config (SPEC §6.3): C1's loader (src/eda/lower_level_evidence/level_layer.py: validate, config, weights,
# delta_levels), so every family reads one config the same way. Keys this family reads:
#     tours, families.ios, families.ios_points_short, itf_box     as SPEC 6.3
#     weight            a number, or "fitted": role B's column named by solve_w (C1's key; default "w_joint", one weight
#                       per joint-solve observation, the mean of the serve statistic's and its receiving side's w), for
#                       the solve's serve-side statistic (spw for ios_points_short), the row's level and own season
#                       (params_season_floor for 2010-2012 rows); missing_params "untouched" leaves a cell with no
#                       parameter at w 1
#     translate         true: the level term, in form (b) (below); classes: role A's delta_levels of the statistic
#     prior             "pool" only (the newcomer prior was not kept: role B's method F4)
#     ios_level_term    this module's own option: "fixed_effect" (form b, the default and the lead's choice of 9 Oct
#                       2026) or "supplied" (form a, B's delta subtracted from y: in the solvers, switched off in the
#                       config path)

from src.eda.lower_level_evidence import level_layer as LL  # noqa: E402

LEVEL_TERMS = ("supplied", "fixed_effect")
LEVEL_TERM_DEFAULT = "fixed_effect"


def validate_config(cfg: dict, where: str = "<config>") -> dict:
    """C1's validation (SPEC §6.3 and C1's extensions), plus this module's ios_level_term."""
    out = LL.validate(dict(cfg), where)
    out.setdefault("ios_level_term", LEVEL_TERM_DEFAULT)
    if out["ios_level_term"] not in LEVEL_TERMS:
        raise ValueError(f"{where}: ios_level_term must be one of {LEVEL_TERMS}")
    return out


def config() -> dict | None:
    """The layer config named by LLE_LAYER (C1's loader, cached per file state), or None when it is unset or empty
    (the decided behaviour)."""
    cfg = LL.config()
    if cfg is None:
        return None
    if "ios_level_term" not in cfg:
        cfg["ios_level_term"] = LEVEL_TERM_DEFAULT
    if cfg["ios_level_term"] not in LEVEL_TERMS:
        raise ValueError(f"{cfg.get('_path')}: ios_level_term must be one of {LEVEL_TERMS}")
    return cfg


def family_on(cfg: dict | None, tour: str, family: str) -> bool:
    return cfg is not None and tour in cfg["tours"] and bool(cfg["families"].get(family, False))


def fingerprint(cfg: dict | None, families=FAMILIES) -> str:
    """What the IOS outputs depend on, as one hash; "off" when no named family is on for any tour (the decided build).
    Two configs with one fingerprint build the same IOS inputs."""
    if cfg is None or not any(family_on(cfg, t, f) for t in TOURS for f in families):
        return "off"
    fitted = cfg["weight"] == "fitted"
    classes = cfg.get("classes")
    keys = {"tours": sorted(cfg["tours"]), "families": {f: bool(cfg["families"].get(f)) for f in families},
            "translate": cfg["translate"], "weight": cfg["weight"], "prior": cfg["prior"], "itf_box": cfg["itf_box"],
            "params_sha256": cfg.get("params_sha256") if fitted else None,
            "solve_w": cfg.get("solve_w", "w_joint") if fitted else None,
            "missing_params": cfg.get("missing_params", "error") if fitted else None,
            "params_season_floor": cfg.get("params_season_floor") if fitted else None,
            "classes_sha256": (cfg.get("classes_sha256") or (sha256_file(Path(classes)) if classes else None))
            if cfg["translate"] else None,
            "classes_null": (not classes) if cfg["translate"] else None,
            "ios_level_term": cfg.get("ios_level_term", LEVEL_TERM_DEFAULT) if cfg["translate"] else None}
    if fitted and cfg.get("params_season_ceiling") is not None:
        # added 10 Oct 2026 for the current best model; absent from the study's configs, so their fingerprints are kept
        keys["params_season_ceiling"] = cfg["params_season_ceiling"]
    text = json.dumps(keys, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def record(families=FAMILIES) -> dict | None:
    """What a hooked build writes beside its outputs: the config, its fingerprint and this module's hash."""
    cfg = config()
    if cfg is None:
        return None
    path = cfg.get("_path")
    return {"config": path, "config_sha256": sha256_file(Path(path)) if path else None, "name": cfg["name"],
            "fingerprint": fingerprint(cfg, families), "families": list(families),
            "module_sha256": sha256_file(Path(__file__)), "level_layer_sha256": sha256_file(Path(LL.__file__)),
            "time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}


def stamp(meta: dict, families=FAMILIES) -> dict:
    """meta unchanged when the layer is off; else meta with "lle_layer": record(families)."""
    rec = record(families)
    if rec is None:
        return meta
    return {**meta, "lle_layer": rec}


# ------------------------------------------------------------------------------------------------
# Levels of the rows

_BUCKET_CACHE: dict = {}


def bucket_map(stage0_matches: Path = STAGE0_MATCHES) -> pd.Series:
    """match_id -> the study's bucket code (common.bucket of Stage 0's map_level), cached per file."""
    p = Path(stage0_matches)
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _BUCKET_CACHE:
        m = pd.read_parquet(p, columns=["match_id", "map_level"])
        b = LC.bucket(m["map_level"]).astype(str).map(CODE).astype("int8")
        _BUCKET_CACHE.clear()
        _BUCKET_CACHE[key] = pd.Series(b.to_numpy(), index=m["match_id"].to_numpy())
    return _BUCKET_CACHE[key]


def bucket_codes(match_ids, stage0_matches: Path | None = None) -> np.ndarray:
    """Per match id: its level code (CODE). Stage 0's match table: the given one, else the layer config's
    stage0_matches (C1's extension), else this tree's own."""
    if stage0_matches is None:
        cfg = LL.config()
        stage0_matches = (cfg or {}).get("stage0_matches") or STAGE0_MATCHES
    b = bucket_map(stage0_matches).reindex(np.asarray(match_ids))
    if b.isna().any():
        raise KeyError(f"{int(b.isna().sum())} rows' matches are not in {stage0_matches}")
    return b.to_numpy().astype(np.int8)


def bucket_names(codes) -> np.ndarray:
    return np.asarray(BUCKETS, dtype=object)[np.asarray(codes, dtype=np.int64)]


def annotate_td(td: dict, rows: pd.DataFrame, idx=None, tour: str | None = None) -> dict:
    """td unchanged when the layer is off; else a copy carrying each row's level code (lle_bucket) and season
    (lle_season, Stage 0's year), and its tour when given. idx: the td rows' positions in ``rows`` (default
    td["idx"])."""
    if config() is None:
        return td
    idx = np.asarray(td["idx"] if idx is None else idx)
    out = dict(td)
    if tour is not None:
        out["tour"] = tour
    out["lle_bucket"] = bucket_codes(rows["match_id"].to_numpy()[idx])
    out["lle_season"] = rows["year"].to_numpy()[idx].astype(np.int64)
    return out


def annotate_cache(arrays: dict, rows: pd.DataFrame, idx) -> dict:
    """The surface-IOS cache's arrays of one tour, unchanged when the layer is off; else with lle_bucket and
    lle_season added (build_cache.py writes them into the tour's npz, C.load_tour hands them to the solver)."""
    if config() is None:
        return arrays
    idx = np.asarray(idx)
    return {**arrays, "lle_bucket": bucket_codes(rows["match_id"].to_numpy()[idx]),
            "lle_season": rows["year"].to_numpy()[idx].astype(np.int64)}


# ------------------------------------------------------------------------------------------------
# The rows' exchange rates and level terms

@dataclass
class RowPlan:
    mult: np.ndarray                 # m_k per td row (1 = as decided; 0 = dropped)
    delta: np.ndarray                # delta_k per td row, in the solve's units (0 = as decided)
    summary: dict = field(default_factory=dict)
    fe_code: np.ndarray | None = None   # form (b): each row's level-effect index (-1 none); None = no level effect
    fe_levels: tuple = ()


def stat_key(stat: str, family: str) -> str:
    """Role B's and role A's key for a solve: its own serve-side statistic; spw for ios_points_short (the lead,
    9 Oct 2026). Every solve of the family is of a serve-side statistic (spw, ace, df, first_in, first_won, second_won,
    hold, bp_saved), whose receiving side is the same observation."""
    return "spw" if family == "ios_points_short" else stat


NO_LEVEL_TERM = ("ITF", "ITFQ")      # never translated (C1's rule): no training season has their box scores before P7


def fe_levels(cfg: dict, tour: str, key: str) -> tuple[str, ...]:
    """Form (b): the levels whose effect a solve estimates. Classes null (SYS_NOCLASS): every lower level. Else role
    A's delta_levels of the solve's statistic (classes.csv, kind "stat"; "none": no level term), for a statistic of
    class OPP or ENV (the lead, 9 Oct 2026). ITF and ITFQ never get one: as C1's translation(), they are dropped
    ("exclude") or left as the reference has them ("as_is")."""
    if not cfg.get("classes"):
        return tuple(L for L in LOWER if L not in NO_LEVEL_TERM)
    row = LL.class_row(cfg, key, tour, "stat")
    if str(row["class"]) not in ("OPP", "ENV"):
        return ()
    allowed = LL.delta_levels(cfg, key, tour, "stat")
    return tuple(L for L in LOWER if L in allowed and L not in NO_LEVEL_TERM)


def level_arrays(cfg: dict, tour: str, key: str, bucket: np.ndarray, season: np.ndarray,
                 valid: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(m, delta) per row of one tour's solve under ``cfg`` (key: stat_key). m from C1's level_layer.weights: 1 at
    MAIN and TEAM; ITF and ITFQ 0 under itf_box "exclude", untouched under "as_is"; the arm's number, or role B's
    fitted column named by solve_w (w_joint) for the key, the row's level and own season, with the config's season
    floor and missing_params. valid: the rows that enter the solve (a parameter is read only for them). delta is 0:
    form (a) is switched off in the config path, and the level term is form (b), estimated in the solve (fe_plan)."""
    if cfg["translate"] and cfg.get("ios_level_term", LEVEL_TERM_DEFAULT) == "supplied":
        raise NotImplementedError("ios_level_term 'supplied' (form a: role B's delta subtracted from y) is switched off "
                                  "for the joint solves: B's delta is a residual after the Elo term, not in the solve's "
                                  "units. The level term is form (b), 'fixed_effect' (the lead, 9 Oct 2026)")
    if cfg["prior"] != "pool":
        raise NotImplementedError("prior 'newcomer': not in the joint solves (role B's method F4 keeps the pool prior)")
    names = bucket_names(bucket)
    m = LL.weights(cfg, key, np.full(len(names), tour, dtype=object), names, np.asarray(season), "box", valid=valid,
                   column=cfg.get("solve_w", "w_joint"))
    m = np.asarray(m, dtype=np.float64)
    if not np.all(np.isfinite(m)) or np.any(m < 0):
        raise ValueError(f"{key} {tour}: an exchange rate is not finite and >= 0")
    d = np.zeros(len(names), dtype=np.float64)
    return m, d


def fe_plan(cfg: dict, tour: str, key: str, bucket: np.ndarray, mult: np.ndarray, valid: np.ndarray):
    """(fe_code, levels) for form (b), or (None, ()) when the config asks for no level term (translate false). Only
    levels with a kept observation (a box score in the solve, valid, with m > 0) get an effect; MAIN and TEAM never.
    With no such level (fe_code all -1) the solve is the plain variant's."""
    if not (cfg["translate"] and cfg.get("ios_level_term", LEVEL_TERM_DEFAULT) == "fixed_effect"):
        return None, ()
    kept = (np.asarray(mult) > 0) & np.asarray(valid, dtype=bool)
    levels = [L for L in fe_levels(cfg, tour, key) if ((bucket == CODE[L]) & kept).any()]
    code = np.full(len(bucket), -1, dtype=np.int64)
    for j, L in enumerate(levels):
        code[(bucket == CODE[L]) & kept] = j
    return code, tuple(levels)


def row_plan(td: dict, stat: str, family: str) -> RowPlan | None:
    """The plan for one solve, or None when the decided solve should run (layer off, tour or family not switched on)."""
    cfg = config()
    if cfg is None:
        return None
    tour = td.get("tour")
    if tour not in TOURS:
        raise KeyError("the layer is on but the solver's rows carry no tour (td['tour'])")
    if not family_on(cfg, tour, family):
        return None
    if "lle_bucket" not in td or "lle_season" not in td:
        raise RuntimeError("the layer is on but the solver's rows carry no level (annotate_td / annotate_cache did not "
                           "run: is the sandbox patched, and was the surface-IOS cache rebuilt with LLE_LAYER set?)")
    bucket = np.asarray(td["lle_bucket"])
    season = np.asarray(td["lle_season"])
    ok = np.asarray(td["stats"][stat]["ok"], bool)
    key = stat_key(stat, family)
    m, d = level_arrays(cfg, tour, key, bucket, season, valid=ok)
    fe_code, levels = fe_plan(cfg, tour, key, bucket, m, ok)
    lower = ok & np.isin(bucket, LOWER_CODES)
    summary = {"config": cfg["name"], "fingerprint": fingerprint(cfg), "family": family, "key": key,
               "box_rows": int(ok.sum()), "dropped_rows": int((ok & (m == 0)).sum()),
               "reweighted_rows": int((ok & (m != 0) & (m != 1)).sum()),
               "shifted_rows": int((ok & (d != 0)).sum()),
               "dropped_by_level": {b: int((ok & (m == 0) & (bucket == CODE[b])).sum()) for b in BUCKETS
                                    if (ok & (m == 0) & (bucket == CODE[b])).any()},
               "mean_w_lower_kept": float(m[lower & (m > 0)].mean()) if (lower & (m > 0)).any() else None,
               "level_effects": list(levels) if fe_code is not None else None}
    return RowPlan(m, d, summary, fe_code, levels)


def _fe_result(res: dict, plan: RowPlan, query: np.ndarray) -> dict:
    """The fixed-effect solve's level estimates in the record: the last snapshot whose day precedes the 2025-2026
    holdout (29 Dec 2024 or earlier), so a build record never carries an estimate made from holdout box scores."""
    cut = int((np.datetime64(LC.HOLDOUT_START.date(), "D") - np.datetime64(1, "D")).astype("int64"))
    pre = np.flatnonzero(np.isfinite(query) & (query <= cut))
    if len(pre) and len(plan.fe_levels):
        r = pre[np.argmax(query[pre])]
        res["solver"]["lle_layer_beta_2024"] = {L: float(v) for L, v in zip(plan.fe_levels, res["beta_rows"][r])}
    return res


def _has_fe(plan: RowPlan) -> bool:
    return plan.fe_code is not None and bool((plan.fe_code >= 0).any())


# ------------------------------------------------------------------------------------------------
# The timed (pooled) solver with the layer: src/eda/match_timing/ios_time.py's TimedSystem, snapshots and run_timed,
# with m and delta. Every other operation is the decided one, in the same order.

def _it():
    from src.eda.match_timing import ios_time as IT
    return IT


def _is():
    from src.eda.surface_ios import ios_surface as IS
    return IS


def _ref_day() -> float:
    from src.eda.ufc_ideas import stageB_common as B
    return float(B.REF_DAY)


class TimedSystemL:
    """ios_time.TimedSystem over the rows the layer keeps (m > 0), y shifted by delta, m kept per observation."""

    def __init__(self, td: dict, stat: str, release: np.ndarray, obs: np.ndarray, mult: np.ndarray,
                 delta: np.ndarray):
        st = td["stats"][stat]
        k = np.flatnonzero(st["ok"] & (mult > 0) & np.isfinite(release) & np.isfinite(obs))
        k = k[np.argsort(release[k], kind="stable")]
        n = td["n_players"]
        self.rows, self.n = k, n
        self.srv, self.ret = td["pid"][k], td["pid"][k ^ 1]
        self.y, self.d = st["y"][k] - delta[k], st["d"][k]
        self.m = mult[k]
        self.release, self.obs = release[k].astype(np.int64), obs[k].astype(np.float64)
        self.typ = st["typ"]
        key = self.srv * n + self.ret
        uniq, self.pair = np.unique(key, return_inverse=True)
        ps, pr = uniq // n, uniq % n
        self.n_pairs = len(uniq)
        indptr = np.r_[0, np.cumsum(np.bincount(ps, minlength=n))]
        self.W = sp.csr_matrix((np.zeros(len(uniq)), pr.astype(np.int32), indptr.astype(np.int64)), shape=(n, n))
        perm = np.lexsort((ps, pr))
        indptr_t = np.r_[0, np.cumsum(np.bincount(pr, minlength=n))]
        self.WT = sp.csr_matrix((np.zeros(len(uniq)), ps[perm].astype(np.int32), indptr_t.astype(np.int64)), shape=(n, n))
        self.perm = perm


def timed_snapshots(sysm: TimedSystemL, days: np.ndarray, h: float, kappa: float, tau: int):
    """ios_time.snapshots with each observation's weight multiplied by its m."""
    from src.eda.ufc_ideas import stageB_ios as I
    n, ref = sysm.n, _ref_day()
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    w0 = (sysm.d / sysm.typ) ** tau if tau else np.ones(len(sysm.d))
    ws = w0 * sysm.m * np.exp2((sysm.obs - ref) * lam)
    Pc, Qc, bOc, bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    PWc = np.zeros(sysm.n_pairs)
    ptr, x = 0, np.zeros(2 * n)
    W, WT = sysm.W, sysm.WT
    for i, S in enumerate(days):
        new = int(np.searchsorted(sysm.release, S, side="right"))
        if new > ptr:
            sl = slice(ptr, new)
            Pc += np.bincount(sysm.srv[sl], weights=ws[sl], minlength=n)
            Qc += np.bincount(sysm.ret[sl], weights=ws[sl], minlength=n)
            wy = ws[sl] * sysm.y[sl]
            bOc += np.bincount(sysm.srv[sl], weights=wy, minlength=n)
            bDc -= np.bincount(sysm.ret[sl], weights=wy, minlength=n)
            PWc += np.bincount(sysm.pair[sl], weights=ws[sl], minlength=sysm.n_pairs)
            ptr = new
        g = np.exp2(-(S - ref) * lam)
        P, Q = Pc * g, Qc * g
        W.data[:] = PWc * g
        WT.data[:] = W.data[sysm.perm]
        dO, dD = P + kappa, Q + kappa

        def matvec(v, dO=dO, dD=dD):
            o, dd = v[:n], v[n:]
            return np.concatenate([dO * o - W @ dd, dD * dd - WT @ o])
        b = np.concatenate([bOc * g, bDc * g])
        x, it, conv = I.pcg(matvec, np.concatenate([dO, dD]), b, x)
        yield i, x[:n], x[n:], P, Q, it, conv


def solve_timed(td: dict, stat: str, h: float, kappa: float, tau: int, es: np.ndarray, lf: np.ndarray,
                obs: np.ndarray, mult: np.ndarray, delta: np.ndarray, lookback: int | None = None) -> dict:
    """ios_time.run_timed with per-row exchange rates (mult) and level terms (delta)."""
    IT = _it()
    lookback = IT.LOOKBACK if lookback is None else lookback
    mult = np.asarray(mult, dtype=np.float64)
    delta = np.asarray(delta, dtype=np.float64)
    nr = len(td["pid"])
    if mult.shape != (nr,) or delta.shape != (nr,):
        raise ValueError("mult and delta need one value per row")
    if np.any(mult < 0) or not np.all(np.isfinite(mult)) or not np.all(np.isfinite(delta)):
        raise ValueError("mult must be finite and >= 0, delta finite")
    release = np.where(np.isfinite(lf), lf + 1, np.nan)
    query = es.astype(np.float64)
    if np.any(release <= query):
        raise ValueError("a match's latest possible finish precedes its earliest possible start")
    sysm = TimedSystemL(td, stat, release, obs, mult, delta)
    pid = td["pid"]
    days, ginv = np.unique(query, return_inverse=True)
    order = np.argsort(ginv, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(days)))]
    Os, Ds, Ps, Qs = (np.full(nr, np.nan) for _ in range(4))
    its, nonconv = [], 0
    for i, O, D, P, Q, it, conv in timed_snapshots(sysm, days, h, kappa, tau):
        r = order[bounds[i]:bounds[i + 1]]
        p = pid[r]
        Os[r], Ds[r], Ps[r], Qs[r] = O[p], D[p], P[p], Q[p]
        its.append(it)
        nonconv += int(not conv)

    # the incremental step over each player's own unreleased earlier matches (ios_time.run_timed's, with m and delta)
    st = td["stats"][stat]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ok = st["ok"] & np.isfinite(release) & (mult > 0)
    w0 = np.where(ok, ((st["d"] / st["typ"]) ** tau if tau else 1.0) * mult, 0.0)
    opp = np.arange(nr) ^ 1
    okr, w0r = ok[opp], w0[opp]
    y = st["y"] - delta
    yr = y[opp]
    Dopp, Oopp = np.nan_to_num(Ds[opp]), np.nan_to_num(Os[opp])
    seq = IT.own_order(td)
    sp_ = pid[seq]
    day, ev, rn = td["day"][seq], td["ev"][seq], td["round_order"][seq]
    rel_s, q_s, obs_s = release[seq], query[seq], obs[seq]
    G = np.zeros((nr, 4))
    gaps = np.zeros(nr, dtype=np.int64)
    for k in range(1, lookback + 1):
        tgt = np.arange(k, nr)
        src = tgt - k
        same = sp_[src] == sp_[tgt]
        precedes = (day[src] < day[tgt]) | ((ev[src] == ev[tgt]) & (rn[src] < rn[tgt]))
        unreleased = rel_s[src] > q_s[tgt]
        use = same & precedes & unreleased
        if not use.any():
            if not same.any():
                break
            continue
        tg, sr = seq[tgt[use]], seq[src[use]]
        age = np.maximum(q_s[tgt[use]] - obs_s[src[use]], 0.0)
        e = np.exp2(-age * lam)
        G[tg, 0] += np.where(ok[sr], w0[sr] * e, 0.0)
        G[tg, 1] += np.where(ok[sr], w0[sr] * e * (y[sr] + Dopp[sr]), 0.0)
        G[tg, 2] += np.where(okr[sr], w0r[sr] * e, 0.0)
        G[tg, 3] += np.where(okr[sr], w0r[sr] * e * (Oopp[sr] - yr[sr]), 0.0)
        gaps[tg] += 1
    O1 = ((Ps + kappa) * Os + G[:, 1]) / (Ps + kappa + G[:, 0])
    D1 = ((Qs + kappa) * Ds + G[:, 3]) / (Qs + kappa + G[:, 2])
    return {"O_snap": Os, "D_snap": Ds, "O": O1, "D": D1, "gap_matches": gaps,
            "solver": {"snapshots": int(len(days)), "observations": int(len(sysm.y)), "pairs": int(sysm.n_pairs),
                       "players": int(sysm.n), "iterations_mean": float(np.mean(its)) if its else 0.0,
                       "iterations_max": int(np.max(its)) if its else 0, "not_converged": nonconv,
                       "rows_with_incremental_gap": int((gaps > 0).sum())}}


# ------------------------------------------------------------------------------------------------
# The surface solver with the layer: src/eda/surface_ios/ios_surface.py's SurfaceSystem, snapshots and run, with m and
# delta. Every other operation is the decided one, in the same order.

class SurfaceSystemL:
    """ios_surface.SurfaceSystem over the rows the layer keeps (m > 0), y shifted by delta, m kept per observation."""

    def __init__(self, td: dict, stat: str, release: np.ndarray, obs: np.ndarray, typ: float, mult: np.ndarray,
                 delta: np.ndarray):
        S = _is().S
        st = td["stats"][stat]
        k = np.flatnonzero(st["ok"] & (mult > 0) & np.isfinite(release) & np.isfinite(obs))
        k = k[np.argsort(release[k], kind="stable")]
        srv_full, ret_full = td["pid"][k], td["pid"][k ^ 1]
        self.active = np.unique(np.r_[srv_full, ret_full])
        self.n_full = int(td["n_players"])
        self.cmap = np.full(self.n_full, -1, dtype=np.int64)
        self.cmap[self.active] = np.arange(len(self.active))
        n = len(self.active)
        self.n = n
        self.rows = k
        self.srv, self.ret = self.cmap[srv_full], self.cmap[ret_full]
        self.surf = td["surf"][k].astype(np.int64)
        if (self.surf < 0).any() or (self.surf > S).any():
            raise ValueError("surface codes must be 0..S")
        self.y, self.d = st["y"][k] - delta[k], st["d"][k]
        self.m = mult[k]
        self.release, self.obs = release[k].astype(np.int64), obs[k].astype(np.float64)
        self.typ = typ
        key = (self.srv * n + self.ret) * (S + 1) + self.surf
        uniq, self.triple = np.unique(key, return_inverse=True)
        self.n_triples = len(uniq)
        ts = uniq % (S + 1)
        pr = (uniq // (S + 1)) % n
        ps = (uniq // (S + 1)) // n
        self.W, self.WT, self.slot = [], [], []
        for s in range(S + 1):
            m = np.flatnonzero(ts == s)
            a, b = ps[m], pr[m]
            indptr = np.r_[0, np.cumsum(np.bincount(a, minlength=n))]
            W = sp.csr_matrix((np.zeros(len(m)), b.astype(np.int32), indptr.astype(np.int64)), shape=(n, n))
            perm = np.lexsort((a, b))
            indptr_t = np.r_[0, np.cumsum(np.bincount(b, minlength=n))]
            WT = sp.csr_matrix((np.zeros(len(m)), a[perm].astype(np.int32), indptr_t.astype(np.int64)), shape=(n, n))
            self.W.append(W)
            self.WT.append((WT, perm))
            self.slot.append(m)


def surface_snapshots(sysm: SurfaceSystemL, days: np.ndarray, h: float, kappa: float, kappa_s, tau: int):
    """ios_surface.snapshots with each observation's weight multiplied by its m."""
    IS = _is()
    S = IS.S
    n, ref = sysm.n, _ref_day()
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    w0 = (sysm.d / sysm.typ) ** tau if tau else np.ones(len(sysm.d))
    ws = w0 * sysm.m * np.exp2((sysm.obs - ref) * lam)
    kE, kF, surface_terms = IS.split_kappa(kappa_s)
    Pc, Qc, bOc, bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    Psc, Qsc, bEc, bFc = (np.zeros((S + 1, n)) for _ in range(4))
    TWc = np.zeros(sysm.n_triples)
    ptr = 0
    nS = n * S
    nv = 2 * n + 2 * nS if surface_terms else 2 * n
    x = np.zeros(nv)
    for i, Sday in enumerate(days):
        new = int(np.searchsorted(sysm.release, Sday, side="right"))
        if new > ptr:
            sl = slice(ptr, new)
            srv, ret, sf, w = sysm.srv[sl], sysm.ret[sl], sysm.surf[sl], ws[sl]
            wy = w * sysm.y[sl]
            Pc += np.bincount(srv, weights=w, minlength=n)
            Qc += np.bincount(ret, weights=w, minlength=n)
            bOc += np.bincount(srv, weights=wy, minlength=n)
            bDc -= np.bincount(ret, weights=wy, minlength=n)
            if surface_terms:
                np.add.at(Psc, (sf, srv), w)
                np.add.at(Qsc, (sf, ret), w)
                np.add.at(bEc, (sf, srv), wy)
                np.add.at(bFc, (sf, ret), -wy)
            TWc += np.bincount(sysm.triple[sl], weights=w, minlength=sysm.n_triples)
            ptr = new
        g = np.exp2(-(Sday - ref) * lam)
        P, Q = Pc * g, Qc * g
        Ws, WTs = [], []
        for s in range(S + 1):
            W = sysm.W[s]
            W.data[:] = TWc[sysm.slot[s]] * g
            WT, perm = sysm.WT[s]
            WT.data[:] = W.data[perm]
            Ws.append(W)
            WTs.append(WT)
        if not surface_terms:
            dO, dD = P + kappa, Q + kappa

            def matvec(v, dO=dO, dD=dD, Ws=Ws, WTs=WTs):
                o, dd = v[:n], v[n:]
                return np.concatenate([dO * o - sum(W @ dd for W in Ws), dD * dd - sum(WT @ o for WT in WTs)])
            diag = np.concatenate([dO, dD])
            b = np.concatenate([bOc * g, bDc * g])
            x, it, conv = IS.pcg_block(matvec, lambda r, diag=diag: r / diag, b, x)
            zero = np.zeros((n, S))
            yield i, x[:n], x[n:], zero, zero, P, Q, zero, zero, it, conv
            continue
        Ps, Qs = Psc[1:] * g, Qsc[1:] * g
        aO, aD = P + kappa, Q + kappa
        dE, dF = Ps + kE, Qs + kF
        AO, AD = IS.Arrow(aO, Ps, dE), IS.Arrow(aD, Qs, dF)
        o_, d_, e_, f_ = slice(0, n), slice(n, 2 * n), slice(2 * n, 2 * n + nS), slice(2 * n + nS, nv)

        def matvec(v, aO=aO, aD=aD, dE=dE, dF=dF, Ps=Ps, Qs=Qs, Ws=Ws, WTs=WTs):
            O, D = v[o_], v[d_]
            E, F = v[e_].reshape(S, n), v[f_].reshape(S, n)
            gs = np.empty((S, n))
            hs = np.empty((S, n))
            for s in range(S):
                gs[s] = Ws[s + 1] @ (D + F[s])
                hs[s] = WTs[s + 1] @ (O + E[s])
            out = np.empty(nv)
            out[o_] = aO * O + (Ps * E).sum(axis=0) - Ws[0] @ D - gs.sum(axis=0)
            out[d_] = aD * D + (Qs * F).sum(axis=0) - WTs[0] @ O - hs.sum(axis=0)
            out[e_] = (Ps * O + dE * E - gs).reshape(-1)
            out[f_] = (Qs * D + dF * F - hs).reshape(-1)
            return out

        def precond(r, AO=AO, AD=AD):
            out = np.empty(nv)
            x0, xs = AO.solve(r[o_], r[e_].reshape(S, n))
            out[o_], out[e_] = x0, xs.reshape(-1)
            x0, xs = AD.solve(r[d_], r[f_].reshape(S, n))
            out[d_], out[f_] = x0, xs.reshape(-1)
            return out
        b = np.concatenate([bOc * g, bDc * g, (bEc[1:] * g).reshape(-1), (bFc[1:] * g).reshape(-1)])
        x, it, conv = IS.pcg_block(matvec, precond, b, x)
        yield (i, x[o_], x[d_], x[e_].reshape(S, n).T, x[f_].reshape(S, n).T, P, Q, Ps.T, Qs.T, it, conv)


def solve_surface(td: dict, stat: str, h: float, kappa: float, kappa_s, tau: int, typ: float, mult: np.ndarray,
                  delta: np.ndarray, until_day: int | None = None, lookback: int | None = None) -> dict:
    """ios_surface.run with per-row exchange rates (mult) and level terms (delta)."""
    IS = _is()
    S = IS.S
    lookback = IS.LOOKBACK if lookback is None else lookback
    mult = np.asarray(mult, dtype=np.float64)
    delta = np.asarray(delta, dtype=np.float64)
    nr = len(td["pid"])
    if mult.shape != (nr,) or delta.shape != (nr,):
        raise ValueError("mult and delta need one value per row")
    if np.any(mult < 0) or not np.all(np.isfinite(mult)) or not np.all(np.isfinite(delta)):
        raise ValueError("mult must be finite and >= 0, delta finite")
    es, lf, obs = td["es"], td["lf"], td["obs"]
    release = np.where(np.isfinite(lf), lf + 1, np.nan)
    query = es.astype(np.float64)
    if np.any(release <= query):
        raise ValueError("a match's latest possible finish precedes its earliest possible start")
    sysm = SurfaceSystemL(td, stat, release, obs, typ, mult, delta)
    pid, surf = td["pid"], td["surf"].astype(np.int64)
    cp = sysm.cmap[pid]
    cp = np.where(cp >= 0, cp, sysm.n)
    in_range = np.ones(nr, dtype=bool) if until_day is None else (query <= until_day)
    days, ginv = np.unique(query[in_range], return_inverse=True)
    rows_in = np.flatnonzero(in_range)
    order = np.argsort(ginv, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(days)))]
    O_s, D_s, P_s, Q_s = (np.full(nr, np.nan) for _ in range(4))
    E_all, F_all, PS_all, QS_all = (np.full((nr, S), np.nan) for _ in range(4))
    its, nonconv = [], 0
    z1, zS = np.zeros(1), np.zeros((1, S))
    for i, O, D, E, F, P, Q, Ps, Qs, it, conv in surface_snapshots(sysm, days, h, kappa, kappa_s, tau):
        r = rows_in[order[bounds[i]:bounds[i + 1]]]
        p = cp[r]
        O_s[r], D_s[r] = np.r_[O, z1][p], np.r_[D, z1][p]
        P_s[r], Q_s[r] = np.r_[P, z1][p], np.r_[Q, z1][p]
        E_all[r], F_all[r] = np.vstack([E, zS])[p], np.vstack([F, zS])[p]
        PS_all[r], QS_all[r] = np.vstack([Ps, zS])[p], np.vstack([Qs, zS])[p]
        its.append(it)
        nonconv += int(not conv)

    sidx = np.clip(surf - 1, 0, S - 1)
    known = surf >= 1
    E_row = np.where(known, E_all[np.arange(nr), sidx], 0.0)
    F_row = np.where(known, F_all[np.arange(nr), sidx], 0.0)

    # the incremental step (ios_surface.run's, with m and delta)
    st = td["stats"][stat]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ok = st["ok"] & np.isfinite(release) & (mult > 0)
    w0 = np.where(ok, ((st["d"] / typ) ** tau if tau else 1.0) * mult, 0.0)
    opp = np.arange(nr) ^ 1
    okr, w0r = ok[opp], w0[opp]
    y = st["y"] - delta
    yr = y[opp]
    Dopp = np.nan_to_num(D_s[opp] + F_row[opp])
    Oopp = np.nan_to_num(O_s[opp] + E_row[opp])
    seq = IS.own_order(td)
    sp_ = pid[seq]
    day, ev, rn = td["day"][seq], td["ev"][seq], td["round_order"][seq]
    rel_s, q_s, obs_s = release[seq], query[seq], obs[seq]
    GO, GOy, GD, GDy = (np.zeros((nr, S + 1)) for _ in range(4))
    gaps = np.zeros(nr, dtype=np.int64)
    for k in range(1, lookback + 1):
        tgt = np.arange(k, nr)
        src = tgt - k
        same = sp_[src] == sp_[tgt]
        precedes = (day[src] < day[tgt]) | ((ev[src] == ev[tgt]) & (rn[src] < rn[tgt]))
        unreleased = rel_s[src] > q_s[tgt]
        use = same & precedes & unreleased
        if not use.any():
            if not same.any():
                break
            continue
        tg, sr = seq[tgt[use]], seq[src[use]]
        age = np.maximum(q_s[tgt[use]] - obs_s[src[use]], 0.0)
        e = np.exp2(-age * lam)
        sg = surf[sr]
        GO[tg, sg] += np.where(ok[sr], w0[sr] * e, 0.0)
        GOy[tg, sg] += np.where(ok[sr], w0[sr] * e * (y[sr] + Dopp[sr]), 0.0)
        GD[tg, sg] += np.where(okr[sr], w0r[sr] * e, 0.0)
        GDy[tg, sg] += np.where(okr[sr], w0r[sr] * e * (Oopp[sr] - yr[sr]), 0.0)
        gaps[tg] += 1
    kE, kF, surface_terms = IS.split_kappa(kappa_s)
    if surface_terms:
        E_snap = np.nan_to_num(E_all)
        F_snap = np.nan_to_num(F_all)
        PSn, QSn = np.nan_to_num(PS_all), np.nan_to_num(QS_all)
        aO = P_s + kappa
        aD = Q_s + kappa
        rO = aO * O_s + (PSn * E_snap).sum(axis=1) + GOy.sum(axis=1)
        rE = PSn * O_s[:, None] + (PSn + kE) * E_snap + GOy[:, 1:]
        O1, E1 = IS.arrow_solve(aO + GO.sum(axis=1), PSn + GO[:, 1:], PSn + kE + GO[:, 1:], rO, rE)
        rD = aD * D_s + (QSn * F_snap).sum(axis=1) + GDy.sum(axis=1)
        rF = QSn * D_s[:, None] + (QSn + kF) * F_snap + GDy[:, 1:]
        D1, F1 = IS.arrow_solve(aD + GD.sum(axis=1), QSn + GD[:, 1:], QSn + kF + GD[:, 1:], rD, rF)
        E1_row = np.where(known, E1[np.arange(nr), sidx], 0.0)
        F1_row = np.where(known, F1[np.arange(nr), sidx], 0.0)
    else:
        O1 = ((P_s + kappa) * O_s + GOy.sum(axis=1)) / (P_s + kappa + GO.sum(axis=1))
        D1 = ((Q_s + kappa) * D_s + GDy.sum(axis=1)) / (Q_s + kappa + GD.sum(axis=1))
        E1_row = np.zeros(nr)
        F1_row = np.zeros(nr)
        E1 = F1 = None
    out = {"O_eff": O1 + E1_row, "D_eff": D1 + F1_row, "O": O1, "D": D1, "E": E1_row, "F": F1_row,
           "O_snap": O_s, "D_snap": D_s, "E_snap": E_row, "F_snap": F_row, "gap_matches": gaps,
           "P": P_s, "Q": Q_s, "P_surf": np.where(known, np.nan_to_num(PS_all)[np.arange(nr), sidx], 0.0),
           "Q_surf": np.where(known, np.nan_to_num(QS_all)[np.arange(nr), sidx], 0.0),
           "solver": {"snapshots": int(len(days)), "observations": int(len(sysm.y)), "triples": int(sysm.n_triples),
                      "players": int(sysm.n), "players_in_history": int(sysm.n_full),
                      "iterations_mean": float(np.mean(its)) if its else 0.0,
                      "iterations_max": int(np.max(its)) if its else 0, "not_converged": nonconv,
                      "rows_with_incremental_gap": int((gaps > 0).sum())}}
    if E1 is not None:
        out["E_all"], out["F_all"] = E1, F1
    if until_day is not None:
        for k_ in ("O_eff", "D_eff", "O", "D", "E", "F", "O_snap", "D_snap", "E_snap", "F_snap", "P", "Q", "P_surf",
                   "Q_surf"):
            out[k_] = np.where(in_range, out[k_], np.nan)
    return out


# ------------------------------------------------------------------------------------------------
# Form (b) of the level term: a level fixed effect estimated inside each snapshot's solve (SPEC §3, "a level fixed
# effect estimated inside the solve, on the leak-proof clock"). One solver for both families: the surface model, or the
# pooled one with kappa_s = inf (the timed solves' model; rows' surfaces are then irrelevant).
#
#     y_k = O_srv + E_srv,s - D_ret - F_ret,s + beta_L(k) + noise,   beta = 0 at MAIN, TEAM and levels without the term
#     minimise  sum_k w_k m_k (...)^2 + kappa (|O|^2 + |D|^2) + kappa_s (|E|^2 + |F|^2) + kappa_beta |beta|^2
#
# beta_L is the level's serve-return balance for the same players against the same opponents (role 03's delta_L, in
# the solve's own units, with the solve's own decay). It is re-estimated at every snapshot from the released rows only,
# so it is walk-forward by construction. The incremental step holds beta at the gap match's own snapshot, as it holds
# the opponent's rating there.

def snapshots_fe(sysm: SurfaceSystemL, fe: np.ndarray, n_fe: int, days: np.ndarray, h: float, kappa: float, kappa_s,
                 tau: int, kappa_beta: float):
    """surface_snapshots with the level effects as n_fe extra unknowns. fe: per kept observation, its level-effect
    index (-1: none). Yields (i, O, D, E, F, P, Q, Ps, Qs, beta, iterations, converged)."""
    IS = _is()
    S = IS.S
    n, ref, nL = sysm.n, _ref_day(), int(n_fe)
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    w0 = (sysm.d / sysm.typ) ** tau if tau else np.ones(len(sysm.d))
    ws = w0 * sysm.m * np.exp2((sysm.obs - ref) * lam)
    kE, kF, surface_terms = IS.split_kappa(kappa_s)
    Pc, Qc, bOc, bDc = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n)
    Psc, Qsc, bEc, bFc = (np.zeros((S + 1, n)) for _ in range(4))
    TWc = np.zeros(sysm.n_triples)
    PLc, QLc = np.zeros((n, nL)), np.zeros((n, nL))
    PsLc, QsLc = (np.zeros((S + 1, n, nL)) for _ in range(2)) if surface_terms else (None, None)
    SLc, bBc = np.zeros(nL), np.zeros(nL)
    ptr = 0
    nS = n * S
    nv = (2 * n + 2 * nS if surface_terms else 2 * n) + nL
    x = np.zeros(nv)
    for i, Sday in enumerate(days):
        new = int(np.searchsorted(sysm.release, Sday, side="right"))
        if new > ptr:
            sl = slice(ptr, new)
            srv, ret, sf, w, fl = sysm.srv[sl], sysm.ret[sl], sysm.surf[sl], ws[sl], fe[sl]
            wy = w * sysm.y[sl]
            Pc += np.bincount(srv, weights=w, minlength=n)
            Qc += np.bincount(ret, weights=w, minlength=n)
            bOc += np.bincount(srv, weights=wy, minlength=n)
            bDc -= np.bincount(ret, weights=wy, minlength=n)
            if surface_terms:
                np.add.at(Psc, (sf, srv), w)
                np.add.at(Qsc, (sf, ret), w)
                np.add.at(bEc, (sf, srv), wy)
                np.add.at(bFc, (sf, ret), -wy)
            TWc += np.bincount(sysm.triple[sl], weights=w, minlength=sysm.n_triples)
            has = fl >= 0
            if has.any():
                np.add.at(PLc, (srv[has], fl[has]), w[has])
                np.add.at(QLc, (ret[has], fl[has]), w[has])
                if surface_terms:
                    np.add.at(PsLc, (sf[has], srv[has], fl[has]), w[has])
                    np.add.at(QsLc, (sf[has], ret[has], fl[has]), w[has])
                SLc += np.bincount(fl[has], weights=w[has], minlength=nL)
                bBc += np.bincount(fl[has], weights=wy[has], minlength=nL)
            ptr = new
        g = np.exp2(-(Sday - ref) * lam)
        P, Q = Pc * g, Qc * g
        PL, QL = PLc * g, QLc * g
        dB = SLc * g + kappa_beta
        bB = bBc * g
        Ws, WTs = [], []
        for s in range(S + 1):
            W = sysm.W[s]
            W.data[:] = TWc[sysm.slot[s]] * g
            WT, perm = sysm.WT[s]
            WT.data[:] = W.data[perm]
            Ws.append(W)
            WTs.append(WT)
        b_ = slice(nv - nL, nv)
        if not surface_terms:
            dO, dD = P + kappa, Q + kappa

            def matvec(v, dO=dO, dD=dD, Ws=Ws, WTs=WTs, PL=PL, QL=QL, dB=dB):
                o, dd, bt = v[:n], v[n:2 * n], v[b_]
                return np.concatenate([dO * o - sum(W @ dd for W in Ws) + PL @ bt,
                                       dD * dd - sum(WT @ o for WT in WTs) - QL @ bt,
                                       dB * bt + PL.T @ o - QL.T @ dd])
            diag = np.concatenate([dO, dD, dB])
            b = np.concatenate([bOc * g, bDc * g, bB])
            x, it, conv = IS.pcg_block(matvec, lambda r, diag=diag: r / diag, b, x)
            zero = np.zeros((n, S))
            yield i, x[:n], x[n:2 * n], zero, zero, P, Q, zero, zero, x[b_].copy(), PL, QL, it, conv
            continue
        Ps, Qs = Psc[1:] * g, Qsc[1:] * g
        PsL, QsL = PsLc[1:] * g, QsLc[1:] * g
        aO, aD = P + kappa, Q + kappa
        dE, dF = Ps + kE, Qs + kF
        AO, AD = IS.Arrow(aO, Ps, dE), IS.Arrow(aD, Qs, dF)
        o_, d_, e_, f_ = slice(0, n), slice(n, 2 * n), slice(2 * n, 2 * n + nS), slice(2 * n + nS, 2 * n + 2 * nS)

        def matvec(v, aO=aO, aD=aD, dE=dE, dF=dF, Ps=Ps, Qs=Qs, Ws=Ws, WTs=WTs, PL=PL, QL=QL, PsL=PsL, QsL=QsL,
                   dB=dB):
            O, D = v[o_], v[d_]
            E, F = v[e_].reshape(S, n), v[f_].reshape(S, n)
            bt = v[b_]
            gs = np.empty((S, n))
            hs = np.empty((S, n))
            for s in range(S):
                gs[s] = Ws[s + 1] @ (D + F[s])
                hs[s] = WTs[s + 1] @ (O + E[s])
            out = np.empty(nv)
            out[o_] = aO * O + (Ps * E).sum(axis=0) - Ws[0] @ D - gs.sum(axis=0) + PL @ bt
            out[d_] = aD * D + (Qs * F).sum(axis=0) - WTs[0] @ O - hs.sum(axis=0) - QL @ bt
            out[e_] = (Ps * O + dE * E - gs + PsL @ bt).reshape(-1)
            out[f_] = (Qs * D + dF * F - hs - QsL @ bt).reshape(-1)
            out[b_] = (dB * bt + PL.T @ O - QL.T @ D + np.einsum("snl,sn->l", PsL, E)
                       - np.einsum("snl,sn->l", QsL, F))
            return out

        def precond(r, AO=AO, AD=AD, dB=dB):
            out = np.empty(nv)
            x0, xs = AO.solve(r[o_], r[e_].reshape(S, n))
            out[o_], out[e_] = x0, xs.reshape(-1)
            x0, xs = AD.solve(r[d_], r[f_].reshape(S, n))
            out[d_], out[f_] = x0, xs.reshape(-1)
            out[b_] = r[b_] / dB
            return out
        b = np.concatenate([bOc * g, bDc * g, (bEc[1:] * g).reshape(-1), (bFc[1:] * g).reshape(-1), bB])
        x, it, conv = IS.pcg_block(matvec, precond, b, x)
        yield (i, x[o_], x[d_], x[e_].reshape(S, n).T, x[f_].reshape(S, n).T, P, Q, Ps.T, Qs.T, x[b_].copy(), PL, QL,
               it, conv)


def solve_fe(td: dict, stat: str, h: float, kappa: float, kappa_s, tau: int, typ: float, mult: np.ndarray,
             fe_code: np.ndarray, kappa_beta: float | None = None, until_day: int | None = None,
             lookback: int | None = None) -> dict:
    """solve_surface with the level term estimated in the solve: fe_code per row is the row's level-effect index
    (-1: none, e.g. MAIN and TEAM). kappa_s = inf is the pooled model (the timed solves'). Returns solve_surface's keys
    plus beta_rows (each row's snapshot estimate of every level effect, rows x n_fe) and beta_last (the last snapshot's)."""
    IS = _is()
    S = IS.S
    lookback = IS.LOOKBACK if lookback is None else lookback
    kappa_beta = float(kappa) if kappa_beta is None else float(kappa_beta)
    mult = np.asarray(mult, dtype=np.float64)
    fe_code = np.asarray(fe_code, dtype=np.int64)
    nr = len(td["pid"])
    if mult.shape != (nr,) or fe_code.shape != (nr,):
        raise ValueError("mult and fe_code need one value per row")
    if np.any(mult < 0) or not np.all(np.isfinite(mult)):
        raise ValueError("mult must be finite and >= 0")
    n_fe = int(fe_code.max()) + 1 if (fe_code >= 0).any() else 0
    es, lf, obs = td["es"], td["lf"], td["obs"]
    release = np.where(np.isfinite(lf), lf + 1, np.nan)
    query = es.astype(np.float64)
    if np.any(release <= query):
        raise ValueError("a match's latest possible finish precedes its earliest possible start")
    sysm = SurfaceSystemL(td, stat, release, obs, typ, mult, np.zeros(nr))
    fe = fe_code[sysm.rows]
    pid, surf = td["pid"], td["surf"].astype(np.int64)
    cp = sysm.cmap[pid]
    cp = np.where(cp >= 0, cp, sysm.n)
    in_range = np.ones(nr, dtype=bool) if until_day is None else (query <= until_day)
    days, ginv = np.unique(query[in_range], return_inverse=True)
    rows_in = np.flatnonzero(in_range)
    order = np.argsort(ginv, kind="stable")
    bounds = np.r_[0, np.cumsum(np.bincount(ginv, minlength=len(days)))]
    O_s, D_s, P_s, Q_s = (np.full(nr, np.nan) for _ in range(4))
    E_all, F_all, PS_all, QS_all = (np.full((nr, S), np.nan) for _ in range(4))
    B_all = np.full((nr, max(n_fe, 1)), np.nan)
    SH_srv, SH_ret = np.full((nr, max(n_fe, 1)), np.nan), np.full((nr, max(n_fe, 1)), np.nan)
    its, nonconv = [], 0
    z1, zS, zL = np.zeros(1), np.zeros((1, S)), np.zeros((1, max(n_fe, 1)))
    beta_last = np.zeros(n_fe)
    for i, O, D, E, F, P, Q, Ps, Qs, beta, PL, QL, it, conv in snapshots_fe(sysm, fe, n_fe, days, h, kappa, kappa_s,
                                                                            tau, kappa_beta):
        r = rows_in[order[bounds[i]:bounds[i + 1]]]
        p = cp[r]
        O_s[r], D_s[r] = np.r_[O, z1][p], np.r_[D, z1][p]
        P_s[r], Q_s[r] = np.r_[P, z1][p], np.r_[Q, z1][p]
        E_all[r], F_all[r] = np.vstack([E, zS])[p], np.vstack([F, zS])[p]
        PS_all[r], QS_all[r] = np.vstack([Ps, zS])[p], np.vstack([Qs, zS])[p]
        if n_fe:
            B_all[r] = beta
            # each row's player's share of his serve (and return) data weight at each effect's level, at the snapshot
            with np.errstate(invalid="ignore", divide="ignore"):
                SH_srv[r] = np.where(P_s[r, None] > 0, np.vstack([PL, zL])[p] / P_s[r, None], 0.0)
                SH_ret[r] = np.where(Q_s[r, None] > 0, np.vstack([QL, zL])[p] / Q_s[r, None], 0.0)
        beta_last = beta
        its.append(it)
        nonconv += int(not conv)

    sidx = np.clip(surf - 1, 0, S - 1)
    known = surf >= 1
    E_row = np.where(known, E_all[np.arange(nr), sidx], 0.0)
    F_row = np.where(known, F_all[np.arange(nr), sidx], 0.0)

    # the incremental step, each gap row's y net of its level effect at the gap match's own snapshot
    st = td["stats"][stat]
    lam = 0.0 if not np.isfinite(h) else 1.0 / (7.0 * h)
    ok = st["ok"] & np.isfinite(release) & (mult > 0)
    w0 = np.where(ok, ((st["d"] / typ) ** tau if tau else 1.0) * mult, 0.0)
    opp = np.arange(nr) ^ 1
    okr, w0r = ok[opp], w0[opp]
    if n_fe:
        bl = np.where(fe_code >= 0, B_all[np.arange(nr), np.clip(fe_code, 0, None)], 0.0)
        y = st["y"] - np.nan_to_num(bl)
    else:
        y = st["y"].astype(np.float64)
    yr = y[opp]
    Dopp = np.nan_to_num(D_s[opp] + F_row[opp])
    Oopp = np.nan_to_num(O_s[opp] + E_row[opp])
    seq = IS.own_order(td)
    sp_ = pid[seq]
    day, ev, rn = td["day"][seq], td["ev"][seq], td["round_order"][seq]
    rel_s, q_s, obs_s = release[seq], query[seq], obs[seq]
    GO, GOy, GD, GDy = (np.zeros((nr, S + 1)) for _ in range(4))
    gaps = np.zeros(nr, dtype=np.int64)
    for k in range(1, lookback + 1):
        tgt = np.arange(k, nr)
        src = tgt - k
        same = sp_[src] == sp_[tgt]
        precedes = (day[src] < day[tgt]) | ((ev[src] == ev[tgt]) & (rn[src] < rn[tgt]))
        unreleased = rel_s[src] > q_s[tgt]
        use = same & precedes & unreleased
        if not use.any():
            if not same.any():
                break
            continue
        tg, sr = seq[tgt[use]], seq[src[use]]
        age = np.maximum(q_s[tgt[use]] - obs_s[src[use]], 0.0)
        e = np.exp2(-age * lam)
        sg = surf[sr]
        GO[tg, sg] += np.where(ok[sr], w0[sr] * e, 0.0)
        GOy[tg, sg] += np.where(ok[sr], w0[sr] * e * (y[sr] + Dopp[sr]), 0.0)
        GD[tg, sg] += np.where(okr[sr], w0r[sr] * e, 0.0)
        GDy[tg, sg] += np.where(okr[sr], w0r[sr] * e * (Oopp[sr] - yr[sr]), 0.0)
        gaps[tg] += 1
    kE, kF, surface_terms = IS.split_kappa(kappa_s)
    if surface_terms:
        E_snap = np.nan_to_num(E_all)
        F_snap = np.nan_to_num(F_all)
        PSn, QSn = np.nan_to_num(PS_all), np.nan_to_num(QS_all)
        aO = P_s + kappa
        aD = Q_s + kappa
        rO = aO * O_s + (PSn * E_snap).sum(axis=1) + GOy.sum(axis=1)
        rE = PSn * O_s[:, None] + (PSn + kE) * E_snap + GOy[:, 1:]
        O1, E1 = IS.arrow_solve(aO + GO.sum(axis=1), PSn + GO[:, 1:], PSn + kE + GO[:, 1:], rO, rE)
        rD = aD * D_s + (QSn * F_snap).sum(axis=1) + GDy.sum(axis=1)
        rF = QSn * D_s[:, None] + (QSn + kF) * F_snap + GDy[:, 1:]
        D1, F1 = IS.arrow_solve(aD + GD.sum(axis=1), QSn + GD[:, 1:], QSn + kF + GD[:, 1:], rD, rF)
        E1_row = np.where(known, E1[np.arange(nr), sidx], 0.0)
        F1_row = np.where(known, F1[np.arange(nr), sidx], 0.0)
    else:
        O1 = ((P_s + kappa) * O_s + GOy.sum(axis=1)) / (P_s + kappa + GO.sum(axis=1))
        D1 = ((Q_s + kappa) * D_s + GDy.sum(axis=1)) / (Q_s + kappa + GD.sum(axis=1))
        E1_row = np.zeros(nr)
        F1_row = np.zeros(nr)
    out = {"O_eff": O1 + E1_row, "D_eff": D1 + F1_row, "O": O1, "D": D1, "E": E1_row, "F": F1_row,
           "O_snap": O_s, "D_snap": D_s, "E_snap": E_row, "F_snap": F_row, "gap_matches": gaps, "P": P_s, "Q": Q_s,
           "beta_rows": B_all[:, :n_fe], "beta_last": np.asarray(beta_last),
           "share_srv_rows": SH_srv[:, :n_fe], "share_ret_rows": SH_ret[:, :n_fe],
           "solver": {"snapshots": int(len(days)), "observations": int(len(sysm.y)), "triples": int(sysm.n_triples),
                      "players": int(sysm.n), "level_effects": n_fe,
                      "iterations_mean": float(np.mean(its)) if its else 0.0,
                      "iterations_max": int(np.max(its)) if its else 0, "not_converged": nonconv,
                      "rows_with_incremental_gap": int((gaps > 0).sum())}}
    if until_day is not None:
        for k_ in ("O_eff", "D_eff", "O", "D", "E", "F", "O_snap", "D_snap", "E_snap", "F_snap", "P", "Q"):
            out[k_] = np.where(in_range, out[k_], np.nan)
    return out


# ------------------------------------------------------------------------------------------------
# The hooks the sandbox patch calls

def run_timed(td: dict, stat: str, h: float, kappa: float, tau: int, es: np.ndarray, lf: np.ndarray, obs: np.ndarray,
              lookback: int | None = None, label: str = "tuned") -> dict:
    """In place of ios_time.run_timed (rebuild.py's _ios_task). label "short" is ios_points_short's run, every other
    label the family "ios". The decided function's result when the layer does not apply."""
    IT = _it()
    family = "ios_points_short" if label == "short" else "ios"
    plan = row_plan(td, stat, family)
    if plan is None:
        return IT.run_timed(td, stat, h, kappa, tau, es, lf, obs, IT.LOOKBACK if lookback is None else lookback)
    t0 = time.time()
    if _has_fe(plan):
        # form (b): the pooled model (kappa_s = inf) in the fixed-effect solver, as lane 2's "current" runs
        tdf = dict(td, es=es, lf=lf, obs=obs, surf=np.zeros(len(td["pid"]), dtype=np.int64))
        res = _fe_result(solve_fe(tdf, stat, h, kappa, np.inf, tau, td["stats"][stat]["typ"], plan.mult,
                                  plan.fe_code, kappa_beta=kappa, lookback=lookback), plan, np.asarray(es, float))
    else:
        res = solve_timed(td, stat, h, kappa, tau, es, lf, obs, plan.mult, plan.delta, lookback)
    res["solver"]["lle_layer"] = {**plan.summary, "seconds": round(time.time() - t0, 1)}
    return res


def run_surface(td: dict, stat: str, h: float, kappa: float, kappa_s, tau: int, typ: float,
                until_day: int | None = None, lookback: int | None = None) -> dict:
    """In place of ios_surface.run (build_features.py's task, surface_ios/probe.py). The decided function's result when
    the layer does not apply."""
    IS = _is()
    plan = row_plan(td, stat, "ios")
    if plan is None:
        return IS.run(td, stat, h, kappa, kappa_s, tau, typ, until_day, IS.LOOKBACK if lookback is None else lookback)
    t0 = time.time()
    if _has_fe(plan):
        if not IS.split_kappa(kappa_s)[2]:
            # the pooled model (lane 2's "current" runs): the rows' surfaces play no part in it, and they are zeroed as
            # run_timed zeroes them, so both solves do the same floating-point operations and lane 3's mapping check
            # (surface_ios/arms.py:90, 1e-12) holds bit for bit. Split by surface, the level effects' coupling let the
            # rounding grow to 2.6e-12 on men's holds (SYS, 10 Oct 2026; 4e-15 at most without a level effect)
            td = dict(td, surf=np.zeros(len(td["pid"]), dtype=np.int64))
        res = _fe_result(solve_fe(td, stat, h, kappa, kappa_s, tau, typ, plan.mult, plan.fe_code, kappa_beta=kappa,
                                  until_day=until_day, lookback=lookback), plan, np.asarray(td["es"], float))
    else:
        res = solve_surface(td, stat, h, kappa, kappa_s, tau, typ, plan.mult, plan.delta, until_day, lookback)
    res["solver"]["lle_layer"] = {**plan.summary, "seconds": round(time.time() - t0, 1)}
    return res


def runs_dir(base: Path) -> Path:
    """build_features.py's folder of full-history runs: ``base`` when the family "ios" is off, else a folder of its own
    per layer fingerprint (a saved run is reused only when its constants match, and the constants know nothing of the
    layer, so two configs must never share a folder)."""
    cfg = config()
    fp = fingerprint(cfg, ("ios",))
    if fp == "off":
        return Path(base)
    return Path(base) / f"lle_{cfg['name']}_{fp[:12]}"


# ------------------------------------------------------------------------------------------------
# The guards: an out-of-order build fails instead of mixing a config's outputs with another's

def recorded_fingerprint(path: Path, key: str | None = None) -> str:
    """The layer fingerprint a builder's summary records ("off" when it records none, as the decided builders write)."""
    if not Path(path).exists():
        return "missing"
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    if key is not None:
        d = d.get(key) or {}
    rec = d.get("lle_layer")
    return "off" if not rec else rec["fingerprint"]


def consistency(root: Path) -> dict:
    """The IOS family's outputs in a tree against the layer config in effect: the timed part (ios_features_summary.json,
    and its copy inside leakproof_features_summary.json, which the merge writes) and lane 2 (build_features.json)."""
    root = Path(root)
    cfg = config()
    mt = root / "data" / "studies" / "match_timing"
    want_part, want_lane2 = fingerprint(cfg, FAMILIES), fingerprint(cfg, ("ios",))
    got = {"ios_part": recorded_fingerprint(mt / "ios_features_summary.json"),
           "merge": recorded_fingerprint(mt / "leakproof_features_summary.json", key="ios"),
           "lane2": recorded_fingerprint(root / "data" / "studies" / "surface_ios" / "build_features.json")}
    want = {"ios_part": want_part, "merge": want_part, "lane2": want_lane2}
    return {"config": None if cfg is None else cfg["_path"], "want": want, "got": got,
            "ok": {k: got[k] == want[k] for k in want}}


def require_consistent(root: Path, which: str = "both") -> None:
    """Raise unless the tree's IOS outputs were built with the layer config in effect: which "ios_part" (the timed solves
    and the merge, which lane 1's leakproof_frame reads) or "both" (also lane 2's runs, which lane 3 reads)."""
    c = consistency(root)
    keys = ("ios_part", "merge") if which == "ios_part" else ("ios_part", "merge", "lane2")
    bad = [k for k in keys if not c["ok"][k]]
    if bad:
        raise RuntimeError(
            f"[level_layer_ios] the IOS family's outputs do not match the layer config in effect ({c['config']}): "
            f"{ {k: (c['got'][k][:12], c['want'][k][:12]) for k in bad} } (got, want). Run the IOS part "
            f"(level_layer_ios.py --run-ios-part, i.e. match_timing/rebuild.py --part ios then --part merge) and lane 2 "
            f"with the same LLE_LAYER before lane 1's leakproof_frame and lane 3")
    log(f"guard ({which}): the IOS family's outputs match the layer config in effect "
        f"({c['want']['ios_part'][:12]})")


# ------------------------------------------------------------------------------------------------
# The sandbox patch (never the repository)

# Since 10 Oct 2026 the repository's builders carry these edits themselves (docs/decisions/2026-10-10-level-evidence-
# layer.md), under this tag; the study's sandboxes and snapshot carry them under OLD_TAG (system_sandbox.normalize)
TAG = "# level layer, joint solves (LLE_LAYER)"
OLD_TAG = "# lower_level_evidence C2 (sandbox only)"
IMPORT = f"from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  # noqa: E402   {TAG}\n"
COPIED = ("src/eda/lower_level_evidence/level_layer_ios.py", "src/eda/lower_level_evidence/level_layer.py",
          "src/eda/lower_level_evidence/common.py")
PATCHES: dict[str, list[tuple[str, str]]] = {
    "src/eda/match_timing/rebuild.py": [
        ("from src.eda.ufc_ideas import stageB_ios as I  # noqa: E402\n",
         "from src.eda.ufc_ideas import stageB_ios as I  # noqa: E402\n" + IMPORT),
        ('    r = IT.run_timed(d["td"], stat, h, kappa, tau, d["es"], d["lf"], d["obs"])\n',
         f'    r = _LLEIOS.run_timed(d["td"], stat, h, kappa, tau, d["es"], d["lf"], d["obs"], label=label)  {TAG}\n'),
        ('        td = IT.tour_inputs(rows, sa, typ, t, stats)\n        idx = td["idx"]\n',
         '        td = IT.tour_inputs(rows, sa, typ, t, stats)\n'
         f'        td = _LLEIOS.annotate_td(td, rows)  {TAG}\n'
         '        idx = td["idx"]\n'),
        ('            "seconds": round(time.time() - start, 1)}\n    MT.jdump(meta, MT.OUT / "ios_features_summary.json")\n',
         '            "seconds": round(time.time() - start, 1)}\n'
         f'    meta = _LLEIOS.stamp(meta)  {TAG}\n'
         '    MT.jdump(meta, MT.OUT / "ios_features_summary.json")\n'),
    ],
    "src/eda/surface_ios/build_cache.py": [
        ("from src.eda.ufc_ideas import stageB_common as B  # noqa: E402\n",
         "from src.eda.ufc_ideas import stageB_common as B  # noqa: E402\n" + IMPORT),
        ('        np.savez_compressed(C.CACHE / f"{t}.npz", **arrays)\n',
         f'        arrays = _LLEIOS.annotate_cache(arrays, rows, idx)  {TAG}\n'
         '        np.savez_compressed(C.CACHE / f"{t}.npz", **arrays)\n'),
    ],
    "src/eda/surface_ios/build_features.py": [
        ("from src.eda.surface_ios.summarise_tuning import BLOCK_ORIGIN, ratio_gain  # noqa: E402\n",
         "from src.eda.surface_ios.summarise_tuning import BLOCK_ORIGIN, ratio_gain  # noqa: E402\n" + IMPORT),
        ('RUNS = C.OUT / "full_runs"\n',
         f'RUNS = _LLEIOS.runs_dir(C.OUT / "full_runs")  {TAG}\n'),
        ('    res = IS.run(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)])\n',
         f'    res = _LLEIOS.run_surface(td, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)])  {TAG}\n'),
        ('    C.jdump({"ios_constants": IC.record(constants), "choice": choice, "runs": meta}, '
         'C.OUT / "build_features.json")\n',
         '    C.jdump(_LLEIOS.stamp({"ios_constants": IC.record(constants), "choice": choice, "runs": meta}, '
         f'("ios",)),  {TAG}\n            C.OUT / "build_features.json")\n'),
    ],
    "src/eda/tabpfn_leakproof/build_frame.py": [
        ("def main() -> int:\n    X0_train, y0_train, X0_query, manifest0 = OD.load_upload()\n",
         "def main() -> int:\n"
         f"    from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  {TAG}\n"
         f'    _LLEIOS.require_consistent(ROOT, "ios_part")  {TAG}\n'
         "    X0_train, y0_train, X0_query, manifest0 = OD.load_upload()\n"),
    ],
    "src/eda/surface_ios/arms.py": [
        ('def main() -> int:\n    base = pd.read_parquet(C.OUT / "base_frame.parquet")\n',
         "def main() -> int:\n"
         f"    from src.eda.lower_level_evidence import level_layer_ios as _LLEIOS  {TAG}\n"
         f'    _LLEIOS.require_consistent(ROOT, "both")  {TAG}\n'
         '    base = pd.read_parquet(C.OUT / "base_frame.parquet")\n'),
    ],
    "src/eda/surface_ios/probe.py": [
        ("from src.eda.ufc_ideas import stageB_common as B  # noqa: E402\n",
         "from src.eda.ufc_ideas import stageB_common as B  # noqa: E402\n" + IMPORT),
        ("        pos = np.full(len(rows), -1)\n",
         f"        td = _LLEIOS.annotate_td(td, rows, idx=idx, tour=t)  {TAG}\n"
         "        pos = np.full(len(rows), -1)\n"),
        ('                r = IS.run(td, s, c["h"], c["kappa"], c["kappa"] * km, c["tau"], typ[(s, t)])\n',
         '                r = _LLEIOS.run_surface(td, s, c["h"], c["kappa"], c["kappa"] * km, c["tau"], '
         f'typ[(s, t)])  {TAG}\n'),
    ],
}
DIFF = OUT / "sandbox_patch_ios.diff"


def _is_sandbox(sb: Path) -> bool:
    return (Path(sb) / "src").is_dir() and Path(sb).resolve() != ROOT.resolve()


def integrated(text: str, rel: str) -> bool:
    """Whether a builder's text already carries every edit of this patch exactly once (the repository's builders since
    10 Oct 2026). Some but not all: refused."""
    present = [text.count(new) == 1 for _, new in PATCHES[rel]]
    if all(present):
        return True
    if any(present):
        raise SystemExit(f"{rel}: carries {sum(present)} of {len(present)} of this patch's edits")
    return False


def unpatched_text(text: str, rel: str) -> str:
    """The decided builder without this patch's edits (each undone, in reverse order); the tests build their fake
    sandboxes from it."""
    from src.eda.lower_level_evidence import system_sandbox as SB
    s = SB.normalize(text)
    if not integrated(s, rel):
        return s
    for old, new in reversed(PATCHES[rel]):
        s = s.replace(new, old, 1)
    return s


def apply_patch(sandbox) -> dict:
    """Copy this module (and common.py) into the sandbox and make the anchored edits in its copies of the builders.
    Refuses the repository itself and any file whose anchor is not found exactly once; an edit already made is left as
    it is. Writes the unified diff against the repository's files to system/ios_layer/sandbox_patch_ios.diff, unless
    there is none (the repository's builders carry the edits since 10 Oct 2026; the study's diff is then kept)."""
    sb = Path(sandbox)
    if not _is_sandbox(sb):
        raise SystemExit(f"{sb} is not a sandbox (or is the repository)")
    report = {"sandbox": str(sb), "copied": [], "files": {}}
    for rel in COPIED:
        (sb / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, sb / rel)
        report["copied"].append(rel)
    diffs = []
    for rel, edits in PATCHES.items():
        p = sb / rel
        s = p.read_text(encoding="utf-8")
        status = []
        for old, new in edits:
            if s.count(new) == 1:
                status.append("already patched")
                continue
            if s.count(old) != 1:
                raise SystemExit(f"{rel}: the anchor is found {s.count(old)} times, not once; nothing more patched "
                                 f"(anchor: {old[:60]!r})")
            s = s.replace(old, new)
            status.append("patched")
        p.write_text(s, encoding="utf-8")
        py_compile.compile(str(p), doraise=True)
        report["files"][rel] = status
        orig = (ROOT / rel).read_text(encoding="utf-8").splitlines(keepends=True)
        mod = p.read_text(encoding="utf-8").splitlines(keepends=True)
        diffs += difflib.unified_diff(orig, mod, fromfile=f"repository/{rel}", tofile=f"sandbox/{rel}")
    if diffs:
        DIFF.parent.mkdir(parents=True, exist_ok=True)
        DIFF.write_text("".join(diffs), encoding="utf-8")
        report["diff"] = str(DIFF)
    else:
        report["diff"] = None
        report["integrated_in_repository"] = True
    log(f"patched {sb}: " + "; ".join(f"{Path(k).name} {v}" for k, v in report["files"].items()))
    return report


def check_patch(sandbox) -> dict:
    """Whether the sandbox carries this patch exactly: each patched file equal to the repository's file plus these
    edits (so no other edit, and every edit once), the copied modules equal to the repository's, every patched file
    compiling, and each anchor still found once in the repository's builders. Returns {"ok": bool, "problems": [...],
    ...}; never raises on a bad sandbox."""
    sb = Path(sandbox)
    out = {"sandbox": str(sb), "ok": True, "problems": [], "files": {}}
    if not _is_sandbox(sb):
        return {**out, "ok": False, "problems": ["not a sandbox (or the repository)"]}
    for rel in COPIED:
        if not (sb / rel).exists() or sha256_file(sb / rel) != sha256_file(ROOT / rel):
            out["problems"].append(f"{rel}: the sandbox's copy differs from the repository's (re-run apply_patch)")
    for rel, edits in PATCHES.items():
        p = sb / rel
        s = p.read_text(encoding="utf-8") if p.exists() else ""
        repo = (ROOT / rel).read_text(encoding="utf-8")
        st = []
        expect = repo
        done = integrated(repo, rel)                   # the repository's builder carries the edits (since 10 Oct 2026)
        for old, new in edits:
            if not done and repo.count(old) != 1:
                out["problems"].append(f"{rel}: the repository's file no longer has the anchor once ({old[:50]!r})")
            if not done:
                expect = expect.replace(old, new, 1)
            st.append("present" if s.count(new) == 1 else "missing")
        if "missing" in st:
            out["problems"].append(f"{rel}: {st.count('missing')} edit(s) missing")
        if s != expect:
            out["problems"].append(f"{rel}: differs from the repository's file plus this patch (another edit?)")
        try:
            py_compile.compile(str(p), doraise=True)
        except (py_compile.PyCompileError, FileNotFoundError) as e:
            out["problems"].append(f"{rel}: does not compile ({str(e)[:80]})")
        out["files"][rel] = st
    out["ok"] = not out["problems"]
    out["pass"] = out["ok"]                            # C1's key (system_sandbox.check_patch)
    return out


def needs_ios_part(config_path=None) -> bool:
    """Whether a build with this layer config (default: LLE_LAYER's) must run the IOS part: some IOS family is on for
    some tour. False for the decided build and for configs that leave the joint solves alone (the stored tables serve,
    and the guards accept them)."""
    if config_path is None:
        return fingerprint(config(), FAMILIES) != "off"
    return fingerprint(validate_config(json.loads(Path(config_path).read_text(encoding="utf-8")),
                                       str(config_path)), FAMILIES) != "off"


def run_ios_part(sandbox, out: Path | None = None, env: dict | None = None) -> int:
    """The IOS part of a hooked build, in the sandbox: match_timing/rebuild.py --part ios, then --part merge. Logs to
    SANDBOX/logs/; each step's exit code and seconds go to <out>/chain_lane_ios.json (run_chain's record format). Run it
    before lane 1's leakproof_frame (whose guard refuses otherwise), and lane 2 with the same LLE_LAYER.

    env: the environment the steps run with (default this process's), so a caller that keeps the arm's LLE_LAYER in a
    dict for its subprocesses (system_arms.build) passes that dict. IOS_CONSTANTS_VERSION defaults to the reference's.
    A candidate Stage 0 with new matches needs run_chain's lane 0 instead: the merge joins the STORED per-player part,
    whose pool is the old Stage 0's; lane 0 rebuilds rebuild.py in full, and its IOS part is hooked by this patch."""
    sb = Path(sandbox)
    if not _is_sandbox(sb):
        raise SystemExit(f"{sb} is not a sandbox (or is the repository)")
    chk = check_patch(sb)
    if not chk["ok"]:
        raise SystemExit(f"the sandbox is not patched as this module expects: {chk['problems'][:3]}")
    env = {**(os.environ if env is None else env), "PYTHONIOENCODING": "utf-8", "MODEL_REBUILD_SANDBOX": str(sb)}
    env.setdefault(IOS_VERSION_ENV, IOS_VERSION)
    if env[IOS_VERSION_ENV] != IOS_VERSION:
        log(f"note: {IOS_VERSION_ENV}={env[IOS_VERSION_ENV]}, not the reference's {IOS_VERSION}")
    out = Path(out) if out else sb / "logs"
    out.mkdir(parents=True, exist_ok=True)
    (sb / "logs").mkdir(exist_ok=True)
    rec_path = out / "chain_lane_ios.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {"steps": []}
    rec.update({"sandbox": str(sb), "lane": "ios", "lle_layer": env.get(ENV), IOS_VERSION_ENV: env[IOS_VERSION_ENV]})
    for name, args in (("lle_ios_part", ["--part", "ios"]), ("lle_ios_merge", ["--part", "merge"])):
        t0 = time.time()
        logf = sb / "logs" / f"{name}.log"
        log(f"--> {name}: match_timing/rebuild.py {' '.join(args)}")
        with logf.open("w", encoding="utf-8") as fh:
            done = subprocess.run([PY, str(sb / "src/eda/match_timing/rebuild.py"), *args], cwd=sb, stdout=fh,
                                  stderr=subprocess.STDOUT, env=env)
        row = {"step": name, "script": f"src/eda/match_timing/rebuild.py {' '.join(args)}", "exit": done.returncode,
               "seconds": round(time.time() - t0, 1), "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "log": str(logf)}
        rec["steps"].append(row)
        rec_path.write_text(json.dumps(rec, indent=1), encoding="utf-8")
        log(f"    exit {done.returncode} in {row['seconds']} s")
        if done.returncode != 0:
            print(logf.read_text(encoding="utf-8", errors="replace")[-3000:])
            return done.returncode
    return 0


# ------------------------------------------------------------------------------------------------
# Configs and gates (Phase 1)

PROFILE = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
IOS_INPUTS = (["ios_points_short"] + [f"iosO_{s}" for s in PROFILE] + [f"iosD_{s}" for s in PROFILE]
              + [f"prod_{s}" for s in PROFILE])
CONFIGS = {
    # SPEC §6.3: the identity config reproduces the reference (translate false, weights 1, prior pool, ITF as is); both
    # tours, so that every hooked solve runs the layer's code path
    "IDENTITY": {"name": "IDENTITY", "tours": ["atp", "wta"], "params": None, "params_sha256": None, "classes": None,
                 "translate": False, "weight": 1, "weight_results": 1, "prior": "pool", "itf_box": "as_is",
                 "families": {"points_52w": True, "forms": True, "ios": True, "ios_points_short": True,
                              "ratings_iid": True, "elo": True}},
    # SPEC §7: complete separation (men): no translation, w = 0 and w_results = 0, prior pool
    "SEP_ALL": {"name": "SEP_ALL", "tours": ["atp"], "params": None, "params_sha256": None, "classes": None,
                "translate": False, "weight": 0, "weight_results": 0, "prior": "pool", "itf_box": "exclude",
                "families": {"points_52w": True, "forms": True, "ios": True, "ios_points_short": True,
                             "ratings_iid": True, "elo": True}},
    # SPEC §7: the reference with ITF and ITFQ box scores at w = 0 in every box-score family, both tours; nothing else
    "REF_noITF": {"name": "REF_noITF", "tours": ["atp", "wta"], "params": None, "params_sha256": None, "classes": None,
                  "translate": False, "weight": 1, "weight_results": 1, "prior": "pool", "itf_box": "exclude",
                  "families": {"points_52w": True, "forms": True, "ios": True, "ios_points_short": True,
                               "ratings_iid": True, "elo": True}},
    # not an arm: the leak probe's second config, so the probe also runs the re-weighting path (w = 0.5 on every
    # lower-level row, both tours), not only the drop path (SEP_ALL)
    "PROBE_W50": {"name": "PROBE_W50", "tours": ["atp", "wta"], "params": None, "params_sha256": None, "classes": None,
                  "translate": False, "weight": 0.5, "weight_results": 1, "prior": "pool", "itf_box": "exclude",
                  "families": {"points_52w": False, "forms": False, "ios": True, "ios_points_short": True,
                               "ratings_iid": False, "elo": False}},
}


def probe_fe_config() -> dict:
    """Not an arm: the leak probe's config for form (b), the level effect estimated in the solve, at every lower level
    (classes null), w = 1, ITF excluded, both tours, the IOS families only. C1's loader asks for params and the strength
    whenever translate is on; this form reads neither, so A's strength file stands in for both (hash-checked if read)."""
    stand = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "classes" / "strength_elo.parquet"
    sha = sha256_file(stand)
    return {"name": "PROBE_FE", "tours": ["atp", "wta"], "params": str(stand), "params_sha256": sha,
            "strength": {"path": str(stand), "sha256": sha}, "classes": None, "translate": True, "weight": 1,
            "weight_results": 1, "prior": "pool", "itf_box": "exclude", "ios_level_term": "fixed_effect",
            "families": {"points_52w": False, "forms": False, "ios": True, "ios_points_short": True,
                         "ratings_iid": False, "elo": False},
            "note": "C2's leak-probe config, not an arm: params and strength are stand-ins the fixed-effect form "
                    "never reads"}


def write_configs(out: Path = OUT / "configs") -> dict:
    """The Phase 1 configs this role's gates use (C1 writes the arms' own layer_config.json), and the probe's."""
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    configs = dict(CONFIGS)
    stand = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "classes" / "strength_elo.parquet"
    if stand.exists():
        configs["PROBE_FE"] = probe_fe_config()
    for name, cfg in configs.items():
        validate_config(dict(cfg), name)
        p = out / f"{name}.json"
        text = json.dumps(cfg, indent=1) + "\n"
        if p.exists():
            if p.read_text(encoding="utf-8") != text:
                raise SystemExit(f"{p} exists with other content; a config is never changed in place")
        else:
            p.write_text(text, encoding="utf-8")
        paths[name] = str(p)
    return paths


def reference_frame(columns=None) -> pd.DataFrame:
    return pd.read_parquet(LC.FRAME, columns=columns)


def model_inputs_from(sandbox) -> pd.DataFrame:
    """The 22 IOS-family inputs as the chain would put them into the model frame, from a sandbox's outputs, on the
    reference frame's matches in its order: the 21 surface-profile inputs by surface_ios/arms.py's recipe on lane 2's
    surface_features.parquet (sprof's sources), and ios_points_short from the merged leakproof_features.parquet."""
    from src.eda.surface_ios import arms as SA
    sb = Path(sandbox)
    ref = reference_frame(["match_id", "tour", "season"])
    sf = pd.read_parquet(sb / "data" / "studies" / "surface_ios" / "surface_features.parquet")
    sf = ref[["match_id"]].merge(sf, on="match_id", how="left", validate="one_to_one")
    out = ref.copy()
    lp = pd.read_parquet(sb / "data" / "studies" / "match_timing" / "leakproof_features.parquet",
                         columns=["match_id", "ios_short"])
    out["in_ios_points_short"] = ref[["match_id"]].merge(lp, on="match_id", how="left",
                                                         validate="one_to_one")["ios_short"].to_numpy(dtype="float64")
    for kind in ("iosO", "iosD", "prod"):
        for s in PROFILE:
            out[f"in_{kind}_{s}"] = SA.recipe(f"{kind}_{s}", sf)
    return out[["match_id", "tour", "season"] + [f"in_{n}" for n in IOS_INPUTS]]


def collect_inputs(sandbox, label: str) -> dict:
    """Save a sandbox's 22 IOS-family inputs (model_inputs_from) and its builders' records under ios_layer/inputs/."""
    sb = Path(sandbox)
    d = OUT / "inputs"
    d.mkdir(parents=True, exist_ok=True)
    f = model_inputs_from(sb)
    f.to_parquet(d / f"{label}.parquet", index=False)
    recs = {}
    for rel in ("data/studies/match_timing/ios_features_summary.json",
                "data/studies/match_timing/leakproof_features_summary.json",
                "data/studies/surface_ios/build_features.json", "data/studies/surface_ios/cache/manifest.json"):
        p = sb / rel
        if p.exists():
            recs[rel] = {"sha256": sha256_file(p), "mtime_utc": pd.Timestamp(p.stat().st_mtime, unit="s",
                                                                              tz="UTC").isoformat(timespec="seconds")}
    for rel in ("data/studies/match_timing/ios_features.parquet", "data/studies/match_timing/leakproof_features.parquet",
                "data/studies/surface_ios/surface_features.parquet"):
        p = sb / rel
        recs[rel] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    cons = consistency(sb)
    meta = {"label": label, "sandbox": str(sb), "lle_layer": os.environ.get(ENV), "consistency": cons, "files": recs,
            "rows": int(len(f)), "time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    (d / f"{label}.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    log(f"collected {label}: {len(f):,} matches x {len(IOS_INPUTS)} inputs; records {cons['got']}")
    return meta


def compare_inputs(got: pd.DataFrame, ref: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per input, tour and season: rows, rows changed (not bitwise equal, NaN = NaN), the same-missing check, the largest
    absolute change, the scale ratio (SD got / SD reference) and the level shift (in reference SDs)."""
    ref = reference_frame(["match_id", "tour", "season"] + [f"in_{n}" for n in IOS_INPUTS]) if ref is None else ref
    if not np.array_equal(got["match_id"].to_numpy(), ref["match_id"].to_numpy()):
        raise ValueError("the inputs are not on the reference frame's matches in its order")
    rows = []
    for n in IOS_INPUTS:
        a, b = ref[f"in_{n}"].to_numpy(dtype="float64"), got[f"in_{n}"].to_numpy(dtype="float64")
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        for (tour, season), ix in ref.groupby(["tour", "season"]).indices.items():
            aa, bb, ss = a[ix], b[ix], same[ix]
            both = np.isfinite(aa) & np.isfinite(bb)
            sd = float(np.std(aa[both])) if both.sum() > 1 else np.nan
            rows.append({"input": n, "tour": tour, "season": int(season), "rows": int(len(ix)),
                         "changed": int((~ss).sum()),
                         "same_missing": bool(np.array_equal(np.isnan(aa), np.isnan(bb))),
                         "max_abs_change": float(np.max(np.abs(aa[both] - bb[both]))) if both.any() else 0.0,
                         "scale_ratio": float(np.std(bb[both]) / sd) if sd and np.isfinite(sd) and sd > 0 else np.nan,
                         "level_shift_sd": float((bb[both].mean() - aa[both].mean()) / sd)
                         if sd and np.isfinite(sd) and sd > 0 else np.nan})
    return pd.DataFrame(rows)


def gate_identity(label: str = "IDENTITY") -> dict:
    """The identity gate: the 22 IOS-family inputs of a hooked identity build equal the reference's bit for bit on all
    67,226 matches (and the same cells are missing)."""
    got = pd.read_parquet(OUT / "inputs" / f"{label}.parquet")
    cmp = compare_inputs(got)
    d = OUT / "gates"
    d.mkdir(parents=True, exist_ok=True)
    cmp.to_csv(d / f"identity_{label}.csv", index=False)
    by = cmp.groupby("input").agg(changed=("changed", "sum"), max_abs_change=("max_abs_change", "max"),
                                  same_missing=("same_missing", "all"))
    ok = bool((by["changed"] == 0).all() and by["same_missing"].all())
    meta = json.loads((OUT / "inputs" / f"{label}.json").read_text(encoding="utf-8"))
    res = {"gate": "identity", "label": label, "pass": ok, "matches": int(len(got)), "inputs": len(IOS_INPUTS),
           "changed_cells": int(by["changed"].sum()), "largest_change": float(by["max_abs_change"].max()),
           "by_input": by.reset_index().to_dict(orient="records"), "build": meta,
           "time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    (d / f"identity_{label}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(f"identity gate {label}: {'PASS' if ok else 'FAIL'} ({res['changed_cells']} cells changed, largest "
        f"{res['largest_change']:.3g})")
    return res


def first_release_by_tour(levels=("ITF", "ITFQ")) -> dict:
    """Per tour: the earliest earliest-possible-start (es) of a box-score match at the given levels: no match whose own
    es is earlier can read such a row (released at lf + 1 > es) in its snapshot."""
    from src.eda.match_timing import common as MT
    m = pd.read_parquet(STAGE0_MATCHES, columns=["match_id", "tour", "map_level", "has_box", "status"])
    m["bucket"] = LC.bucket(m["map_level"])
    t = pd.read_parquet(MT.TIMING, columns=["match_id", "es"])
    m = m.merge(t, on="match_id", how="left")
    sel = m["bucket"].isin(levels) & m["has_box"].astype(bool)
    out = {}
    for tour, g in m[sel].groupby("tour"):
        out[tour] = {"es_min": float(g["es"].min()), "date": str(pd.Timestamp(int(g["es"].min()), unit="D").date()),
                     "box_matches": int(len(g))}
    return out


TIMED_INPUTS = ("ios_points_short",)     # the timed solver's input in the frame; the other 21 come from the surface solver
EQUAL_TOL = 1e-12                         # lane 3's own tolerance between the two IOS solvers (surface_ios/arms.py:90)


def _equal_family(X: np.ndarray, Y: np.ndarray, sel: np.ndarray, cols: list[int]) -> dict:
    a, b = X[sel][:, cols], Y[sel][:, cols]
    same = (a == b) | (np.isnan(a) & np.isnan(b))
    both = np.isfinite(a) & np.isfinite(b)
    return {"cells": int(a.size), "not_bitwise": int((~same).sum()),
            "largest_abs_difference": float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0,
            "same_missing": bool(np.array_equal(np.isnan(a), np.isnan(b)))}


def gate_equal(label: str, cfg_name: str) -> dict:
    """For a w = 0 config: everything the config does not touch stays the reference's. Checked on the tours it does not
    name, and, for REF_noITF, on every match whose earliest start precedes the tour's first ITF/ITFQ box-score match
    (nothing excluded can have reached it). Also the size of the change where it may move.

    The criterion, per solver family:
        timed solver (ios_points_short)     bit for bit
        surface solver (the other 21)       within 1e-12, the same cells missing. Its system holds only the players with
                                            a kept box score somewhere in the history, so dropping the rows of players
                                            seen nowhere else (ITF-only players) shortens its CG vectors and changes the
                                            last bits of the BLAS reductions in every season. The decided solver does
                                            the same on that history (gates/decided_active_set_wta_hold.json: women's
                                            holds, 1.6e-15), and the drop gate shows the hook equal to it bit for bit.
    An untouched tour runs the decided code itself, so it is bit for bit in both families."""
    cfg = validate_config(dict(CONFIGS[cfg_name]), cfg_name)
    got = pd.read_parquet(OUT / "inputs" / f"{label}.parquet")
    ref = reference_frame(["match_id", "tour", "season"] + [f"in_{n}" for n in IOS_INPUTS])
    cmp = compare_inputs(got, ref)
    d = OUT / "gates"
    d.mkdir(parents=True, exist_ok=True)
    cmp.to_csv(d / f"equal_{label}.csv", index=False)
    checks = {}
    X = np.column_stack([ref[f"in_{n}"].to_numpy(dtype="float64") for n in IOS_INPUTS])
    Y = np.column_stack([got[f"in_{n}"].to_numpy(dtype="float64") for n in IOS_INPUTS])
    same = ((X == Y) | (np.isnan(X) & np.isnan(Y))).all(axis=1)
    timed = [i for i, n in enumerate(IOS_INPUTS) if n in TIMED_INPUTS]
    surface = [i for i, n in enumerate(IOS_INPUTS) if n not in TIMED_INPUTS]

    def check(sel: np.ndarray, untouched: bool) -> dict:
        t, s = _equal_family(X, Y, sel, timed), _equal_family(X, Y, sel, surface)
        ok_t = t["not_bitwise"] == 0
        ok_s = (s["not_bitwise"] == 0) if untouched else (s["largest_abs_difference"] <= EQUAL_TOL and s["same_missing"])
        return {"matches": int(sel.sum()), "changed": int((sel & ~same).sum()), "timed_solver": t,
                "surface_solver": s, "criterion": "bit for bit" if untouched else
                "timed bit for bit; surface within 1e-12, same missing", "pass": bool(ok_t and ok_s)}
    for tour in TOURS:
        sel = (ref["tour"] == tour).to_numpy()
        if tour not in cfg["tours"]:
            checks[f"{tour}: untouched tour"] = check(sel, True)
    if cfg["itf_box"] == "exclude" and cfg["weight"] == 1:
        from src.eda.match_timing import common as MT
        first = first_release_by_tour()
        es = ref[["match_id"]].merge(pd.read_parquet(MT.TIMING, columns=["match_id", "es"]), on="match_id",
                                     how="left")["es"].to_numpy(dtype="float64")
        for tour in cfg["tours"]:
            sel = (ref["tour"] == tour).to_numpy() & (es < first[tour]["es_min"])
            checks[f"{tour}: before the first ITF box score ({first[tour]['date']})"] = check(sel, False)
    ok = all(v["pass"] for v in checks.values())
    moved = cmp[cmp["changed"] > 0].groupby(["input", "tour"]).agg(seasons=("season", "nunique"),
                                                                    changed=("changed", "sum")).reset_index()
    res = {"gate": "everything else equal", "label": label, "config": cfg_name, "pass": ok, "checks": checks,
           "changed_matches": int((~same).sum()), "matches": int(len(same)),
           "changed_by_tour_season": cmp.groupby(["tour", "season"])["changed"].max().reset_index().to_dict(
               orient="records"),
           "moved_inputs": moved.to_dict(orient="records"),
           "build": json.loads((OUT / "inputs" / f"{label}.json").read_text(encoding="utf-8")),
           "time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    (d / f"equal_{label}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(f"everything-else-equal gate {label}: {'PASS' if ok else 'FAIL'} " + "; ".join(
        f"{k}: {v['matches']} matches, timed not bit for bit {v['timed_solver']['not_bitwise']}, surface largest "
        f"{v['surface_solver']['largest_abs_difference']:.2g} ({'pass' if v['pass'] else 'FAIL'})"
        for k, v in checks.items()))
    return res


def _drop_mask(cfg: dict, rows: pd.DataFrame) -> dict:
    """Per row of ``rows`` and family: True where the config gives the row m = 0 (Phase 1: m does not depend on the
    statistic)."""
    bucket = bucket_codes(rows["match_id"].to_numpy())
    season = rows["year"].to_numpy().astype(np.int64)
    tour = rows["tour"].to_numpy()
    out = {}
    for fam in FAMILIES:
        drop = np.zeros(len(rows), dtype=bool)
        for t in TOURS:
            if family_on(cfg, t, fam):
                sel = tour == t
                m, _ = level_arrays(cfg, t, "spw", bucket[sel], season[sel])
                drop[np.flatnonzero(sel)[m == 0]] = True
        out[fam] = drop
    return out


def gate_drop_timed(sandbox, cfg_name: str) -> dict:
    """The rows drop out, exactly: the decided rebuild.ios_features (unpatched, the decided ios_time.run_timed), on the
    history with the config's m = 0 rows' box scores removed (their ok set false), against the sandbox's hooked
    ios_features.parquet built with the config. Every value must be equal bit for bit."""
    from src.eda.match_timing import common as MT
    from src.eda.match_timing import rebuild as RB
    from src.eda.ufc_ideas import stageB_common as B
    cfg = validate_config(dict(CONFIGS[cfg_name]), cfg_name)
    saved = os.environ.pop(ENV, None)          # the decided code path, in this process and its workers
    try:
        t0 = time.time()
        timing = pd.read_parquet(MT.TIMING, columns=["match_id", "es", "lf", "obs"])
        rows, _, _ = RB.load_full_rows()
        drop = _drop_mask(cfg, rows)
        original = B.stat_arrays

        def stat_arrays_dropped(rows_, means, stats=B.STATS):
            sa = original(rows_, means, stats)
            for s in stats:
                fam = "ios_points_short" if s == "spw" else "ios"
                sa[s] = {**sa[s], "ok": sa[s]["ok"] & ~drop[fam]}
            return sa
        B.stat_arrays = stat_arrays_dropped
        try:
            feats, _ = RB.ios_features(rows, timing)
        finally:
            B.stat_arrays = original
        A, _ = B.pool_rows(rows)
        mine = pd.DataFrame({"match_id": rows["match_id"].to_numpy()[A], **feats})
    finally:
        if saved is not None:
            os.environ[ENV] = saved
    hooked = pd.read_parquet(Path(sandbox) / "data" / "studies" / "match_timing" / "ios_features.parquet")
    if not np.array_equal(hooked["match_id"].to_numpy(), mine["match_id"].to_numpy()):
        raise ValueError("the pools differ")
    cols = [c for c in mine.columns if c != "match_id"]
    by = {}
    for c in cols:
        a, b = mine[c].to_numpy(dtype="float64"), hooked[c].to_numpy(dtype="float64")
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        by[c] = {"unequal": int((~same).sum()),
                 "max_abs": float(np.nanmax(np.abs(a - b))) if np.isfinite(a - b).any() else 0.0}
    ok = all(v["unequal"] == 0 for v in by.values())
    res = {"gate": "drop-out, timed solves (rebuild.py --part ios)", "config": cfg_name, "pass": ok,
           "dropped_rows": {f: int(v.sum()) for f, v in drop.items()}, "pool_matches": int(len(mine)),
           "by_column": by, "seconds": round(time.time() - t0, 1),
           "time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    d = OUT / "gates"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"drop_timed_{cfg_name}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(f"drop gate (timed) {cfg_name}: {'PASS' if ok else 'FAIL'}; dropped {res['dropped_rows']}")
    return res


def _load_cache_tour(sandbox, tour: str) -> dict:
    """A sandbox's surface-IOS cache of one tour (surface_ios/common.load_tour on the sandbox's file)."""
    from src.eda.surface_ios import common as SC
    with np.load(Path(sandbox) / "data" / "studies" / "surface_ios" / "cache" / f"{tour}.npz", allow_pickle=False) as z:
        d = {k: z[k] for k in z.files}
    d["stats"] = {s: {"ok": d.pop(f"{s}__ok"), "x": d.pop(f"{s}__x"), "d": d.pop(f"{s}__d"), "y": d.pop(f"{s}__y"),
                      "mu": d.pop(f"{s}__mu")} for s in SC.STATS}
    d["n_players"] = int(d["n_players"])
    d["tour"] = tour
    return d


def _surface_drop_task(args):
    sandbox, tour, stat, kind, runs, cfg_name = args
    from src.eda.ios_constants import registry as IC
    from src.eda.surface_ios import ios_surface as IS
    cfg = validate_config(dict(CONFIGS[cfg_name]), cfg_name)
    td = _load_cache_tour(sandbox, tour)
    if "lle_bucket" not in td:
        raise RuntimeError("the sandbox's cache carries no levels (lane 2 not run with LLE_LAYER set?)")
    m, _ = level_arrays(cfg, tour, stat, td["lle_bucket"], td["lle_season"])
    st = td["stats"][stat]
    td2 = dict(td, stats={**td["stats"], stat: {**st, "ok": st["ok"] & (m > 0)}})
    chosen, typ = IC.ios_constants()
    c = chosen[(tour, stat)]
    ch = IC.surface_choice()[f"{tour}|{stat}"]
    if kind == "current":
        h, ks = c["h"], np.inf
    elif ch["variant"] == "shared":
        h, ks = c["h"] * ch["h_mult"], c["kappa"] * ch["ks_mult"]
    else:
        h = c["h"] * ch["h_mult"]
        ks = tuple(c["kappa"] * (np.inf if v is None else v) for v in (ch["kE_mult"], ch["kF_mult"]))
    t0 = time.time()
    r = IS.run(td2, stat, h, c["kappa"], ks, c["tau"], typ[(stat, tour)])
    saved = np.load(Path(runs) / f"{tour}_{stat}_{kind}.npz")
    out = {"tour": tour, "stat": stat, "kind": kind, "dropped_rows": int((st["ok"] & (m == 0)).sum()),
           "seconds": round(time.time() - t0, 1)}
    for k in ("O_eff", "D_eff", "O", "D", "E", "F"):
        a, b = r[k], saved[k]
        same = (a == b) | (np.isnan(a) & np.isnan(b))
        out[k] = int((~same).sum())
    out["equal"] = all(out[k] == 0 for k in ("O_eff", "D_eff", "O", "D", "E", "F"))
    return out


def gate_drop_surface(sandbox, cfg_name: str, stats=("hold",), workers: int = 4, kinds=("surface",)) -> dict:
    """The rows drop out, exactly, in lane 2. For every statistic and tour the config touches, the hooked system
    (SurfaceSystemL) is compared with the decided one (ios_surface.SurfaceSystem) on the cache with the config's m = 0
    rows' ok set false: the same rows, values, units, surfaces, release days and pattern. Then, for ``stats`` x ``kinds``,
    the decided ios_surface.run on that cache is solved in full and compared bit for bit with the sandbox's hooked
    full-history run of the config (full_runs/lle_<config>_<fp>/)."""
    from concurrent.futures import ProcessPoolExecutor
    from src.eda.surface_ios import common as SC
    cfg = validate_config(dict(CONFIGS[cfg_name]), cfg_name)
    fp = fingerprint(cfg, ("ios",))
    runs = Path(sandbox) / "data" / "studies" / "surface_ios" / "full_runs" / f"lle_{cfg_name}_{fp[:12]}"
    if not runs.is_dir():
        raise FileNotFoundError(f"{runs}: no hooked runs of {cfg_name} in the sandbox")
    t0 = time.time()
    structural = []
    IS = _is()
    for tour in cfg["tours"]:
        td = _load_cache_tour(sandbox, tour)
        rel = np.where(np.isfinite(td["lf"]), td["lf"] + 1, np.nan)
        for s in SC.STATS:
            m, d0 = level_arrays(cfg, tour, s, td["lle_bucket"], td["lle_season"])
            st = td["stats"][s]
            td2 = dict(td, stats={**td["stats"], s: {**st, "ok": st["ok"] & (m > 0)}})
            a = SurfaceSystemL(td, s, rel, td["obs"], 1.0, m, d0)
            b = IS.SurfaceSystem(td2, s, rel, td["obs"], 1.0)
            same = (np.array_equal(a.active, b.active) and np.array_equal(a.srv, b.srv)
                    and np.array_equal(a.ret, b.ret) and np.array_equal(a.y, b.y) and np.array_equal(a.d, b.d)
                    and np.array_equal(a.surf, b.surf) and np.array_equal(a.release, b.release)
                    and np.array_equal(a.triple, b.triple) and bool(np.all(a.m > 0)))
            structural.append({"tour": tour, "stat": s, "same_system": bool(same), "kept": int(len(a.y)),
                               "dropped_rows": int((st["ok"] & (m == 0)).sum())})
    tasks = [(str(sandbox), t, s, k, str(runs), cfg_name) for t in cfg["tours"] for s in stats for k in kinds]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        solved = list(ex.map(_surface_drop_task, tasks))
    ok = all(r["same_system"] for r in structural) and all(r["equal"] for r in solved)
    res = {"gate": "drop-out, surface solves (lane 2)", "config": cfg_name, "pass": ok, "runs_folder": str(runs),
           "structural": structural, "solved": solved, "seconds": round(time.time() - t0, 1),
           "time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    d = OUT / "gates"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"drop_surface_{cfg_name}.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    log(f"drop gate (surface) {cfg_name}: {'PASS' if ok else 'FAIL'}")
    return res


def status(message: str) -> None:
    """One line in the team's status log (append only)."""
    p = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "status.log"
    with p.open("a", encoding="utf-8") as fh:
        fh.write(f"{pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')} C2 {message}\n")


def main() -> int:
    # The gates compare against runs the builders made with single-threaded BLAS (rebuild.py and build_features.py set
    # these before importing numpy); worker processes started from here inherit the same, so their reductions round
    # alike. Set only in this CLI, never at import, so that an importing process and its lanes keep their own setting.
    for _v in ("OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "OMP_NUM_THREADS"):
        os.environ.setdefault(_v, "1")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sandbox")
    ap.add_argument("--apply-patch", action="store_true")
    ap.add_argument("--check-patch", action="store_true")
    ap.add_argument("--run-ios-part", action="store_true")
    ap.add_argument("--out", help="with --run-ios-part: the records' folder (default SANDBOX/logs)")
    ap.add_argument("--write-configs", action="store_true")
    ap.add_argument("--collect-inputs", metavar="LABEL")
    ap.add_argument("--gate-identity", metavar="LABEL")
    ap.add_argument("--gate-equal", nargs=2, metavar=("LABEL", "CONFIG"))
    ap.add_argument("--gate-drop-timed", metavar="CONFIG")
    ap.add_argument("--gate-drop-surface", metavar="CONFIG")
    ap.add_argument("--stats", default="hold", help="with --gate-drop-surface: the statistics solved in full")
    ap.add_argument("--kinds", default="surface", help="with --gate-drop-surface: current, surface or both")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    if a.write_configs:
        print(json.dumps(write_configs(), indent=1))
    if a.apply_patch:
        print(json.dumps(apply_patch(a.sandbox), indent=1))
    if a.check_patch:
        r = check_patch(a.sandbox)
        print(json.dumps(r, indent=1))
        if not r["ok"]:
            return 1
    if a.run_ios_part:
        rc = run_ios_part(a.sandbox, a.out)
        if rc:
            return rc
    if a.collect_inputs:
        collect_inputs(a.sandbox, a.collect_inputs)
    if a.gate_identity:
        if not gate_identity(a.gate_identity)["pass"]:
            return 1
    if a.gate_equal:
        if not gate_equal(*a.gate_equal)["pass"]:
            return 1
    if a.gate_drop_timed:
        if not gate_drop_timed(a.sandbox, a.gate_drop_timed)["pass"]:
            return 1
    if a.gate_drop_surface:
        if not gate_drop_surface(a.sandbox, a.gate_drop_surface, stats=tuple(a.stats.split(",")), workers=a.workers,
                                 kinds=tuple(a.kinds.split(",")))["pass"]:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
