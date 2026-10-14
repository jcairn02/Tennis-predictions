"""The level layer of the lower-level-evidence system (role C1): how a lower-level observation (tour and Slam qualifying,
Challenger main draw and qualifying; ITF and ITF qualifying once P7 lands) enters the chain that builds the model's
58 inputs. Specification: docs/studies/lower_level_evidence/system/SPEC.md (sections 3, 4 and 6.3).

SWITCHED OFF BY DEFAULT. Every hook returns its input object unchanged unless the environment variable LLE_LAYER holds
the path of a layer config (SPEC 6.3), so the hooked builders build exactly the template without the layer while it is
unset. During the study the hooks lived only in sandbox copies (src/eda/lower_level_evidence/system_sandbox.py). Since
10 Oct 2026 the same calls are in the repository's builders (docs/decisions/2026-10-10-level-evidence-layer.md), and
the current best model builds with the official config (data/studies/current_best_model/level_layer/official.json,
resolved per build by src/eda/current_best_model/layer_config.py).

The config (JSON; SPEC 6.3 plus the extensions marked *):
    name              the arm
    tours             the tours the layer touches (["atp"] unless an arm says otherwise); other tours: untouched
    params            B's params.parquet (or null when no parameter is read); params_sha256 must match the file
    classes           A's classes.csv (or null: every statistic translated by its own gamma and delta, SYS_NOCLASS);
                      its sha256 (classes_sha256*, else the sibling .sha256 file) must match
    translate         true: lower-level observations are translated by T (below)
    weight            "fitted" (B's w per season, tour, statistic and level, capped at fitted_cap) or a number in
                      [0, 1.5]: box-score rows
    weight_results    "fitted" (B's rows with stat "results", every lower level, ITF and ITFQ included, capped at
                      fitted_cap_results) or a number in [0, 1.5]: results in the Elo passes
    prior             "pool" (the builders' own shrinkage targets) or "newcomer" (refused until a home-tier rule exists)
    itf_box           "exclude" (ITF and ITFQ box rows get w = 0 in every box-score family) or "as_is" (left as the
                      reference has them: w = 1, never translated, no ITF parameter exists before P7)
    families          {"points_52w", "forms", "ios", "ios_points_short", "ratings_iid", "elo"}: true or false each
    strength*         {"path", "sha256"}: the reference build's pre-match Elo (A's classes/strength_elo.parquet), read
                      in every arm
    gamma_scale*      Elo points per unit of the strength gap gamma multiplies (default 100: A's and B's units)
    forms_norm_weight* true (default): w also weights the rows of the opponents' norms (step 1), not only step 3
    forms_own_delta*  true (default): the match's own value at a lower level is shifted by delta (not gamma: the
                      re-referenced norm already accounts for who is across the net)
    elo_count*        "weighted" (default, the only one implemented): a lower-level result moves the rating by
                      K x w_results and the player's rated-match count by w_results (B's estimator does the same)
    solve_stat*       {"ratings_iid": "spw"}: whose w the serve/return ratings read
    solve_w*          "w_joint" (default: one weight per observation, B's mean of the two sides') or "w"
    ratings_level_term* "none" (default: B's delta is a residual after Elo's gamma, not in the solve's units) or
                      "supplied"
    params_season_floor*  null (every season needs its own parameters) or a season whose parameters serve the seasons
                      before it (SYS: 2013, the lead's ruling)
    params_season_ceiling*  null (default: every season needs its own parameters, as in the study) or "last_fitted":
                      a row of a season after the last season the params hold for its tour reads that last season's
                      parameters, until the next refit (the current best model's config, 10 Oct 2026). Leak-free: they
                      were fitted on earlier seasons
    missing_params*   "error" (default) or "untouched": an observation without parameters is left as the reference
                      has it (SYS_BOTH: women's service-game cells of 2013-2015, the lead's ruling)
    fitted_cap*       1 (default; the lead's ruling at checkpoint 1, 10 Oct 2026: "informative, never more than
                      equivalent") or null: a fitted box-score weight above it is set to it, whichever column is read
                      (w for points_52w and the forms, w_joint for ratings_iid and C2's joint solves). B's values are
                      checked against B's cap of 3 first. The capped rows are recorded (dev seasons only, see below)
    fitted_cap_results* 1 (default) or null: the same for B's fitted w_results in the Elo passes
    pins*             {"stageB_adjperf": {"path", "sha256"}}: tuned constants replaced by the reference build's
    record_dir*       where the hooks append layer_calls.jsonl (absolute; null: no record). Records describe rows of
                      seasons before 2025 only: of the sealed seasons (the 2025-2026 holdout, whose 2026 parameters
                      were fitted on 2025 results) they give row counts, never a parameter's value or anything derived
                      from one
    stage0_matches*   Stage 0's match table for the levels (default: this tree's own)

The relationship (SPEC 3), per observation of statistic s, tour g, level L (in the arm's tours only):
    T = gamma_{s,g} x (opponent's reference pre-match Elo - strength_ref) / gamma_scale + delta_{s,g,L}
        the gamma term only for an input of class OPP (A's classes), delta only at the levels A's delta_levels lists
        for the statistic s (the joint solve's input, for ratings_iid); classes null: both, everywhere. MAIN and TEAM
        rows: T = 0, w = 1. Units: the logit of the rate per opportunity ((x + 1/2) / (d + 1)); the log for break
        points faced per service game. Only rows whose observation exists are translated and weighted
    translated value = value - T
    w = the exchange rate; ITF and ITFQ box rows: w = 0 under itf_box "exclude"
    parameters of the observation's own season (season_used = the row's Stage 0 year): every observation is
    translated and weighted with the parameters fitted before its own season
The hooks, family by family (the patched builder line in brackets):
    points_52w   points_counts       [stage4_features.history_sums]   spw and rpw counts: x <- x + d (expit(logit(r) -
                                     T) - r), r = (x + 1/2) / (d + 1) (rows with T = 0 untouched); then x, d <- w x, w d
    forms        forms_z             [stageB_adjperf.build, after the per-match z]   the 17 (statistic, channel) pairs
                                     recomputed: each row of an opponent o's norm is an observation about o, translated
                                     by the strength of o's opponent at that row with the parameters of the statistic
                                     the row is (form_views: adjperf = what o allowed, A's def_<s> or minus the mirror
                                     statistic; adjdef = what o produced) and weighted by w (forms_norm_weight); the
                                     match's own value <- value - delta
                 forms_step3         [stageB_adjperf.build, step 3]   each box row's weight x w; a row with w = 0 does
                                     not make the form exist
                 pin                 [stageB_adjperf.main]   the tuned constants replaced by the reference build's
    ratings_iid  ratings_arrays      [stage3_ratings.main, the final pass]   serve points and points won x w (a
                                     tempered likelihood: the observation counts as w of a main-tour one; w_joint);
                                     the pass's intercept + delta only under ratings_level_term "supplied"; the
                                     stored mu_logit is untouched
    elo          elo_weights         [stage1_baselines.main (probe), surface_elo_pieces.pieces.main,
                                      stage4_features.elo_variants]   played matches get w_results (1 at MAIN/TEAM)
                 elo_rerun           [stage1_baselines.tune, the final pass]   the frozen pass re-run with the weights
                 (the passes themselves: K x upd[i] and the count + upd[i]; with booleans they are the original)
    The tuning steps read the unweighted data, so Stage 1's K and surface weight, the offset's kd and Stage 3's
    constants are the reference's by construction; Stage B's tuning reads Elo, so its constants are pinned.

API for the joint-solve engineer (C2): config(), active(family), buckets_of(), in_scope(), weights(), translation(),
opponent_strength(), gate(), params_table(), record().
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]          # the repository, or the sandbox when copied there
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402

ENV = "LLE_LAYER"
STAGE0_MATCHES = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
FAMILIES = ("points_52w", "forms", "ios", "ios_points_short", "ratings_iid", "elo")
REQUIRED = ("name", "tours", "params", "translate", "weight", "weight_results", "prior", "itf_box", "families")
LOWER = tuple(LC.LOWER)                              # TQ, GSQ, CH, CHQ, ITF, ITFQ
ITF_LEVELS = ("ITF", "ITFQ")
UNTOUCHED = ("MAIN", "TEAM")
TOURS = ("atp", "wta")
RATE_STATS = ("spw", "rpw")
PROFILE = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
           "rpw_first", "rpw_second")
DEFENCE = ("ace", "df", "first_in", "bp_faced_pg")
FORM_SPECS = tuple([(s, "adjperf") for s in PROFILE] + [("tpw", "adjperf")] + [(s, "adjdef") for s in DEFENCE])
# the same quantity seen from the other player (stageB_common.MIRROR): A's x against B is the complement of B's mirror
MIRROR = {"spw": "rpw", "rpw": "spw", "first_won": "rpw_first", "rpw_first": "first_won", "second_won": "rpw_second",
          "rpw_second": "second_won", "hold": "brk", "brk": "hold", "bp_saved": "bp_conv", "bp_conv": "bp_saved",
          "tpw": "tpw"}
DEFAULTS = {"classes": None, "params_sha256": None, "classes_sha256": None, "strength": None, "gamma_scale": 100.0,
            "forms_norm_weight": True, "forms_own_delta": True, "elo_count": "weighted",
            "solve_stat": {"ratings_iid": "spw"}, "params_season_floor": None, "pins": {}, "record_dir": None,
            "stage0_matches": None, "fitted_cap": 1.0, "fitted_cap_results": 1.0}
CLASSES = ("OPP", "ENV", "INTR", "WORK", "RES", "CTX")
MAX_WEIGHT = 1.5                                     # SPEC 6.3: the config's numeric weight
FITTED_MAX = 3.0                                     # B's estimator's cap on the free w (relationship.py)
SEALED_FROM = 2025                                   # the 2025-2026 holdout's seasons: records give counts only
CEILING_LAST = "last_fitted"                         # params_season_ceiling: the last season the params hold


def allowed_view(stat: str) -> tuple[str, float]:
    """What a player ALLOWED on `stat` (the value his opponent produced against him), as a statistic about the player:
    A's def_<stat> where it exists (aces, double faults, first serves in, break points faced per game: no mirror),
    otherwise the complement of his mirror statistic (log-odds: minus it). (statistic key, sign)."""
    if stat in DEFENCE:
        return f"def_{stat}", 1.0
    return MIRROR[stat], -1.0


def form_views(stat: str, channel: str) -> dict:
    """The statistic each part of a Stage B form reads, as an observation about the player it belongs to:
        norm   a row of the opponent o's norm: adjperf = what o allowed (allowed_view), adjdef = what o produced
        own    the match's own value: adjperf = the player's own production, adjdef = o's production in this match
        step3  the player's per-match z in his own form: adjperf = his statistic, adjdef = his def_<statistic>
    Each is (statistic key, sign); the strength of a norm row is always the norm owner's opponent at that row."""
    if channel == "adjperf":
        return {"norm": allowed_view(stat), "own": (stat, 1.0), "step3": (stat, 1.0)}
    return {"norm": (stat, 1.0), "own": (stat, 1.0), "step3": (f"def_{stat}", 1.0)}


def log(msg: str) -> None:
    print(f"[level_layer] {msg}", flush=True)


def input_name(stat: str, channel: str) -> str:
    """The model input a Stage B (statistic, channel) pair feeds."""
    if (stat, channel) == ("tpw", "adjperf"):
        return "adjperf_tpw_2w"
    return f"form_{stat}" if channel == "adjperf" else f"formdef_{stat}"


_SHA: dict = {}


def sha256(path) -> str:
    """A file's SHA-256, cached per (path, size, modification time)."""
    p = Path(path)
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _SHA:
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for b in iter(lambda: fh.read(1 << 20), b""):
                h.update(b)
        _SHA[key] = h.hexdigest()
    return _SHA[key]


def sibling_sha(path: Path) -> str | None:
    """The hash in <file>.sha256 or <stem>.sha256 beside a file (first token), if one exists."""
    for p in (path.with_name(path.name + ".sha256"), path.with_suffix(".sha256")):
        if p.exists():
            tok = p.read_text(encoding="utf-8").split()
            return tok[0].lstrip("*") if tok else None
    return None


# ------------------------------------------------------------------------------------------------
# The config

_CFG: dict = {}


def validate(cfg: dict, where: str = "config") -> dict:
    """The config with the extensions' defaults filled in; raises on anything SPEC 6.3 does not allow."""
    missing = [k for k in REQUIRED if k not in cfg]
    if missing:
        raise KeyError(f"{where}: the layer config lacks {missing}")
    out = {**copy.deepcopy(DEFAULTS), **cfg}
    out["tours"] = [str(t) for t in out["tours"]]
    if not out["tours"] or set(out["tours"]) - set(TOURS):
        raise ValueError(f"{where}: tours must be a non-empty subset of {TOURS}")
    fam = out["families"]
    if not isinstance(fam, dict) or set(fam) != set(FAMILIES) or not all(isinstance(v, bool) for v in fam.values()):
        raise ValueError(f"{where}: families must give true or false for each of {FAMILIES}")
    for key in ("weight", "weight_results"):
        v = out[key]
        if v == "fitted":
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.0 <= float(v) <= MAX_WEIGHT:
            raise ValueError(f"{where}: {key} must be 'fitted' or a number in [0, {MAX_WEIGHT}], not {v!r}")
        out[key] = float(v)
    if not isinstance(out["translate"], bool):
        raise ValueError(f"{where}: translate must be true or false")
    if out["prior"] not in ("pool", "newcomer"):
        raise ValueError(f"{where}: prior must be 'pool' or 'newcomer'")
    if out["prior"] == "newcomer" and not out.get("prior_tier_rule"):
        raise NotImplementedError(f"{where}: the newcomer prior needs role B's rule for a player's home tier "
                                  "(SPEC 3.3); no arm may run it before that rule is written into the config")
    if out["itf_box"] not in ("exclude", "as_is"):
        raise ValueError(f"{where}: itf_box must be 'exclude' or 'as_is'")
    if out["elo_count"] != "weighted":
        raise NotImplementedError(f"{where}: elo_count {out['elo_count']!r}: only 'weighted' is implemented")
    needs_params = out["translate"] or "fitted" in (out["weight"], out["weight_results"]) or out["prior"] == "newcomer"
    if needs_params and not out["params"]:
        raise ValueError(f"{where}: translate, fitted weights and the newcomer prior read params; none is named")
    if out["params"]:
        if not out["params_sha256"]:
            raise ValueError(f"{where}: params named without params_sha256")
    if out["translate"] and not out["strength"]:
        raise ValueError(f"{where}: translate reads the reference's pre-match Elo; strength is not named")
    if out["params_season_floor"] is not None:
        out["params_season_floor"] = int(out["params_season_floor"])
    ceiling = out.get("params_season_ceiling")
    if ceiling is not None and ceiling != CEILING_LAST:
        raise ValueError(f"{where}: params_season_ceiling must be null or {CEILING_LAST!r}, not {ceiling!r}")
    out.setdefault("missing_params", "error")
    if out["missing_params"] not in ("error", "untouched"):
        raise ValueError(f"{where}: missing_params must be 'error' or 'untouched'")
    out.setdefault("solve_w", "w_joint")
    out.setdefault("ratings_level_term", "none")
    if out["solve_w"] not in ("w", "w_joint") or out["ratings_level_term"] not in ("none", "supplied"):
        raise ValueError(f"{where}: solve_w must be 'w' or 'w_joint'; ratings_level_term 'none' or 'supplied'")
    for key in ("fitted_cap", "fitted_cap_results"):
        v = out[key]
        if v is None:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0.0 < float(v) <= FITTED_MAX:
            raise ValueError(f"{where}: {key} must be null or a number in (0, {FITTED_MAX}], not {v!r}")
        out[key] = float(v)
    out["gamma_scale"] = float(out["gamma_scale"])
    if "producer_gamma" in out:
        raise ValueError(f"{where}: producer_gamma is retired; the norms read A's def_<s> or mirror statistics")
    return out


def load_config(path) -> dict:
    p = Path(path)
    cfg = validate(json.loads(p.read_text(encoding="utf-8")), str(p))
    cfg["_path"] = str(p)
    return cfg


def config() -> dict | None:
    """The layer's config, or None when LLE_LAYER is unset or empty (the unpatched behaviour). Cached per file state."""
    path = os.environ.get(ENV, "").strip()
    if not path:
        return None
    st = Path(path).stat()
    key = (path, st.st_size, st.st_mtime_ns)
    if key not in _CFG:
        _CFG.clear()
        _CFG[key] = load_config(path)
    return _CFG[key]


def active(family: str) -> dict | None:
    """The config when the layer is on and the family is switched on in it; None otherwise."""
    if family not in FAMILIES:
        raise KeyError(family)
    cfg = config()
    if cfg is None or not cfg["families"][family]:
        return None
    return cfg


def record(cfg: dict, entry: dict) -> None:
    d = cfg.get("record_dir")
    if not d:
        return
    d = Path(d)
    d.mkdir(parents=True, exist_ok=True)
    entry = {"time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "pid": os.getpid(),
             "arm": cfg["name"], "config": cfg.get("_path"), "tree": str(ROOT),
             "layer_sha256": sha256(Path(__file__)), **entry}
    with (d / "layer_calls.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=_json_default) + "\n")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return str(o)


# ------------------------------------------------------------------------------------------------
# Hash-checked tables: parameters, classes, the strength, the pins

_TABLES: dict = {}


def _checked(path, expected: str | None, what: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{what}: {p} does not exist")
    got = sha256(p)
    if expected and got != expected:
        raise RuntimeError(f"{what}: {p} has sha256 {got}, the config expects {expected}")
    side = sibling_sha(p)
    if side and side != got:
        raise RuntimeError(f"{what}: {p} has sha256 {got}, its .sha256 file says {side}")
    if not expected and not side:
        raise RuntimeError(f"{what}: {p} has no hash to check against (config or .sha256 file)")
    return p


def _cached(key, loader):
    if key not in _TABLES:
        _TABLES[key] = loader()
    return _TABLES[key]


PARAM_COLS = ("season_used", "tour", "stat", "level", "gamma", "delta", "w", "strength_ref")


def params_table(cfg: dict) -> pd.DataFrame:
    """B's parameters, indexed by (season_used, tour, stat, level); hash-checked; one row per key."""
    p = _checked(cfg["params"], cfg["params_sha256"], "params")

    def load():
        t = pd.read_parquet(p)
        miss = [c for c in PARAM_COLS if c not in t.columns]
        if miss:
            raise ValueError(f"{p}: params lack {miss} (SPEC 6.2)")
        t = t.astype({"season_used": "int64", "tour": "string", "stat": "string", "level": "string"})
        t = t.astype({"tour": object, "stat": object, "level": object})
        if t.duplicated(["season_used", "tour", "stat", "level"]).any():
            raise ValueError(f"{p}: more than one row for a (season_used, tour, stat, level)")
        return t.set_index(["season_used", "tour", "stat", "level"]).sort_index()
    return _cached(("params", str(p), sha256(p)), load)


def classes_table(cfg: dict) -> pd.DataFrame | None:
    """A's class table (classes.csv, read with keep_default_na=False as A asks), hash-checked."""
    if not cfg.get("classes"):
        return None
    p = _checked(cfg["classes"], cfg.get("classes_sha256"), "classes")

    def load():
        t = pd.read_csv(p, keep_default_na=False, dtype=str)
        need = {"name", "kind", "base_stat", "class", "tour", "delta_levels"}
        if need - set(t.columns):
            raise ValueError(f"{p}: classes lack {sorted(need - set(t.columns))} (A's schema, one row per name and tour)")
        bad = set(t["class"]) - set(CLASSES)
        if bad:
            raise ValueError(f"{p}: unknown classes {sorted(bad)}")
        if t.duplicated(["name", "kind", "tour"]).any():
            raise ValueError(f"{p}: more than one row for a (name, kind, tour)")
        return t
    return _cached(("classes", str(p), sha256(p)), load)


def strength_table(cfg: dict) -> tuple[pd.Series, pd.Series]:
    """(A's, B's) reference pre-match overall Elo (retirements counted) by match id, float64."""
    spec = cfg["strength"]
    p = _checked(spec["path"], spec.get("sha256"), "strength")

    def load():
        t = pd.read_parquet(p, columns=["match_id", "elo_a_ret", "elo_b_ret"])
        if t["match_id"].duplicated().any():
            raise ValueError(f"{p}: duplicate match ids")
        idx = t["match_id"].astype(str).to_numpy()
        return (pd.Series(t["elo_a_ret"].to_numpy("float64"), index=idx),
                pd.Series(t["elo_b_ret"].to_numpy("float64"), index=idx))
    return _cached(("strength", str(p), sha256(p)), load)


def pinned(cfg: dict, what: str):
    spec = (cfg.get("pins") or {}).get(what)
    if spec is None:
        return None
    p = _checked(spec["path"], spec.get("sha256"), f"pin {what}")
    return _cached(("pin", what, str(p), sha256(p)), lambda: json.loads(p.read_text(encoding="utf-8")))


# ------------------------------------------------------------------------------------------------
# Rows: level, scope, the opponent's strength

_BUCKETS: dict = {}


def bucket_map(stage0_matches) -> pd.Series:
    """match_id -> the study's bucket (common.bucket of Stage 0's map_level), cached per file state."""
    p = Path(stage0_matches)
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _BUCKETS:
        m = pd.read_parquet(p, columns=["match_id", "map_level"])
        _BUCKETS.clear()
        _BUCKETS[key] = pd.Series(LC.bucket(m["map_level"]).astype(str).to_numpy(), index=m["match_id"].to_numpy())
    return _BUCKETS[key]


def buckets_of(match_ids, cfg: dict | None = None) -> np.ndarray:
    path = (cfg or {}).get("stage0_matches") or STAGE0_MATCHES
    b = bucket_map(path).reindex(np.asarray(match_ids)).to_numpy()
    if pd.isna(b).any():
        raise KeyError(f"{int(pd.isna(b).sum())} rows' matches are not in {path}")
    return b.astype(str)


def in_scope(cfg: dict, tour) -> np.ndarray:
    return np.isin(np.asarray(tour).astype(str), cfg["tours"])


def lower_mask(bucket) -> np.ndarray:
    return np.isin(np.asarray(bucket), LOWER)


def opponent_strength(cfg: dict, match_ids, sides) -> np.ndarray:
    """Per row: the reference build's pre-match overall Elo of the OTHER player of the row's match (side A's row reads
    B's rating). Every arm reads the same table, whatever it does to the Elo inputs."""
    ea, eb = strength_table(cfg)
    mids = np.asarray(match_ids).astype(str)
    s = np.asarray(sides).astype(str)
    if not np.isin(s, ["A", "B"]).all():
        raise ValueError("sides must be 'A' or 'B'")
    a = ea.reindex(mids).to_numpy()
    b = eb.reindex(mids).to_numpy()
    out = np.where(s == "A", b, a)
    if np.isnan(out).any():
        raise KeyError(f"{int(np.isnan(out).sum())} rows have no reference pre-match Elo")
    return out


# ------------------------------------------------------------------------------------------------
# Parameters per row

def last_fitted(cfg: dict) -> dict:
    """The last season the params hold, per tour (params_season_ceiling "last_fitted")."""
    t = params_table(cfg)
    s = pd.Series(t.index.get_level_values("season_used"), index=t.index.get_level_values("tour"))
    return {str(k): int(v) for k, v in s.groupby(level=0).max().items()}


def _season_used(cfg: dict, season, tour=None) -> np.ndarray:
    """The season whose parameters a row reads: its own, raised to params_season_floor, and lowered to the last fitted
    season of its tour under params_season_ceiling "last_fitted" (seasons after the last refit)."""
    s = np.asarray(season).astype("int64")
    floor = cfg.get("params_season_floor")
    if floor is not None:
        s = np.maximum(s, floor)
    if cfg.get("params_season_ceiling") == CEILING_LAST:
        last = last_fitted(cfg)
        if tour is None:
            cap = np.full(len(s), max(last.values()), dtype="int64")
        else:
            tr = np.asarray(tour).astype(str)
            if set(tr.tolist()) - set(last):
                raise KeyError(f"params hold no season for tours {sorted(set(tr.tolist()) - set(last))}")
            cap = np.array([last[x] for x in tr], dtype="int64")
        above = s > cap
        if above.any():
            record(cfg, {"hook": "season_ceiling", "rows": int(above.sum()),
                         "seasons": sorted(set(s[above].tolist())), "read_as": sorted(set(cap[above].tolist()))})
            s = np.minimum(s, cap)
    return s


def param_rows(cfg: dict, col: str, stat: str, tour, bucket, season, mask: np.ndarray) -> np.ndarray:
    """Per row (where mask): B's `col` for (the row's season, tour, stat, level); NaN elsewhere. A missing key is an
    error naming it (no guessing, no fallback beyond params_season_floor and params_season_ceiling)."""
    out = np.full(len(mask), np.nan)
    if not mask.any():
        return out
    t = params_table(cfg)
    if col not in t.columns:
        raise KeyError(f"params lack column {col}")
    s = _season_used(cfg, np.asarray(season)[mask], np.asarray(tour)[mask])
    keys = pd.MultiIndex.from_arrays([s, np.asarray(tour)[mask].astype(str).astype(object),
                                      np.full(int(mask.sum()), stat, dtype=object),
                                      np.asarray(bucket)[mask].astype(str).astype(object)])
    v = t[col].reindex(keys).to_numpy(dtype="float64")
    bad = np.isnan(v)
    if bad.any():
        miss = sorted(set(zip(keys[bad].get_level_values(0).tolist(), keys[bad].get_level_values(1).tolist(),
                              keys[bad].get_level_values(2).tolist(), keys[bad].get_level_values(3).tolist())))
        if cfg.get("missing_params", "error") != "untouched":
            raise KeyError(f"params have no {col} for {len(miss)} (season_used, tour, stat, level) keys, e.g. "
                           f"{miss[:4]}")
        # missing_params "untouched" (a config choice): the caller leaves these observations as the reference has
        # them (no term from this column; w 1), recorded
        record(cfg, {"hook": "param_rows", "warning": f"no {col}: observations left untouched", "rows": int(bad.sum()),
                     "keys": [list(k) for k in miss[:20]], "keys_total": len(miss)})
    out[mask] = v
    return out


# ------------------------------------------------------------------------------------------------
# Classes: which terms an input takes (SPEC 4; A's rules_by_class_and_family)

def class_row(cfg: dict, name: str, tour: str, kind: str) -> pd.Series | None:
    """A's row for an input (kind "input") or a statistic (kind "stat") on a tour; None when classes is null."""
    t = classes_table(cfg)
    if t is None:
        return None
    r = t[(t["name"] == name) & (t["kind"] == kind) & (t["tour"] == tour)]
    if len(r) != 1:
        raise KeyError(f"classes: {len(r)} rows for {kind} {name!r}, tour {tour}")
    return r.iloc[0]


def parse_levels(text: str) -> frozenset:
    """A's delta_levels: "CH,CHQ" -> {CH, CHQ}; "none", "n/a" or blank -> nothing."""
    text = str(text).strip()
    if text.lower() in ("none", "n/a", ""):
        return frozenset()
    levels = frozenset(x.strip() for x in text.split(","))
    if levels - set(LOWER):
        raise ValueError(f"classes: unknown levels in delta_levels {text!r}")
    return levels


def input_class(cfg: dict, name: str, tour: str) -> tuple[bool, bool]:
    """(the input is translated at all, its gamma terms are on), by A's class of the input. Classes null (SYS_NOCLASS):
    both. OPP: both; ENV: delta only; INTR, WORK, RES, CTX: untouched (RES moves only through w_results)."""
    row = class_row(cfg, name, tour, "input")
    if row is None:
        return True, True
    cls = str(row["class"])
    return cls in ("OPP", "ENV"), cls == "OPP"


def delta_levels(cfg: dict, key: str, tour: str, kind: str) -> frozenset:
    """The levels where delta is used: A's delta_levels of the statistic (kind "stat") or of the input (kind "input";
    the joint solves, whose single level term is gated per input). Classes null: every lower level."""
    row = class_row(cfg, key, tour, kind)
    if row is None:
        return frozenset(LOWER)
    return parse_levels(row["delta_levels"])


def gate(cfg: dict, name: str, tour: str, base_stat: str | None = None) -> tuple[bool, bool, frozenset]:
    """(translated at all, gamma terms on, the levels where the input's level term is allowed) for a model input: A's
    class and delta_levels of the input row. The joint solves' gate (C2's level_layer_ios.fe_levels reads it)."""
    on, g_on = input_class(cfg, name, tour)
    return on, g_on, (delta_levels(cfg, name, tour, "input") if on else frozenset())


# ------------------------------------------------------------------------------------------------
# The row functions: w and T

def dev_rows(season) -> np.ndarray:
    """Rows of seasons before the sealed holdout's (records describe only these)."""
    return np.asarray(season).astype("int64") < SEALED_FROM


def weights(cfg: dict, stat: str, tour, bucket, season, kind: str = "box", valid=None, column: str = "w") -> np.ndarray:
    """Per row: the exchange rate. 1 at MAIN and TEAM and outside the arm's tours. ITF and ITFQ box rows: 0 under
    itf_box "exclude", untouched (1, as the reference treats them) under "as_is" (no ITF box score exists in a training
    season, so no parameter does: P7). Otherwise the arm's number or B's fitted w (kind "results": weight_results, B's
    stat "results", every lower level, ITF included), capped at fitted_cap (fitted_cap_results for results): a fitted
    value above the cap is set to it, whatever `column` is read (w, or w_joint for the joint solves)."""
    if kind not in ("box", "results"):
        raise ValueError(kind)
    tour = np.asarray(tour).astype(str)
    bucket = np.asarray(bucket).astype(str)
    w = np.ones(len(bucket))
    m = lower_mask(bucket) & in_scope(cfg, tour)
    if valid is not None:                             # rows where the observation exists (its value is read)
        m &= np.asarray(valid, dtype=bool)
    value = cfg["weight"] if kind == "box" else cfg["weight_results"]
    excl = np.zeros(len(bucket), dtype=bool)
    if kind == "box":
        itf = m & np.isin(bucket, ITF_LEVELS)
        m &= ~itf                                         # as_is: untouched
        if cfg["itf_box"] == "exclude":
            excl = itf
    fit = m & ~excl
    if value == "fitted":
        got = param_rows(cfg, column, "results" if kind == "results" else stat, tour, bucket, season, fit)[fit]
        w[fit] = np.where(np.isnan(got), 1.0, got)        # NaN only under missing_params "untouched"
        # B's values are checked against B's own bound (its estimator caps the free w at 3, relationship.py); then the
        # lead's cap (checkpoint 1, 10 Oct 2026): a fitted weight above fitted_cap is set to it
        if np.any((w[fit] < 0) | (w[fit] > FITTED_MAX)):
            raise ValueError(f"fitted w outside [0, {FITTED_MAX}] for {stat}")
        cap = cfg.get("fitted_cap_results" if kind == "results" else "fitted_cap", 1.0)
        limit = MAX_WEIGHT if cap is None else cap
        hi = fit & (w > limit)
        if hi.any():
            dev = hi & dev_rows(season)
            record(cfg, {"hook": "weights", "kind": kind, "stat": stat, "column": column,
                         **({"capped_at": cap} if cap is not None else {"warning": f"fitted w above {MAX_WEIGHT}"}),
                         "rows_dev_seasons": int(dev.sum()),
                         "max_before_dev_seasons": float(w[dev].max()) if dev.any() else None,
                         "levels_dev_seasons": sorted(set(np.asarray(bucket)[dev].tolist())),
                         "sealed_seasons": "not described (2025-2026 parameters are sealed)"})
            if cap is not None:
                w[hi] = cap
    else:
        w[fit] = float(value)
    w[excl] = 0.0
    return w


def translation(cfg: dict, name: str, stat: str, tour, bucket, season, strength=None, sign: float = 1.0,
                gamma_term: bool = True, delta_from: str = "stat", valid=None) -> np.ndarray:
    """Per row: T = sign x (gamma_stat x (strength - strength_ref) / gamma_scale + delta_stat), for lower-level rows in
    the arm's tours (0 elsewhere, and 0 everywhere when translate is false). `name` is the model input whose class
    (A's) decides whether the input is translated and whether its gamma terms are on; `stat` is the statistic the
    observation is (B's parameters; sign -1 when it is read as the complement of `stat`); the levels where delta is
    used are A's delta_levels of the statistic (delta_from "stat") or of the input ("input": the joint solves).
    gamma_term False: delta only (the joint solves, and a match's own value in a one-step form, where the opponent's
    re-referenced norm accounts for who was across the net). The strength is the opponent's reference pre-match Elo
    (the observation's owner's opponent). ITF and ITFQ rows are never translated (no training-season parameters before
    P7): under itf_box "exclude" they carry w = 0, under "as_is" they are left as the reference has them."""
    tour = np.asarray(tour).astype(str)
    bucket = np.asarray(bucket).astype(str)
    T = np.zeros(len(bucket))
    if not cfg["translate"]:
        return T
    m = lower_mask(bucket) & in_scope(cfg, tour) & ~np.isin(bucket, ITF_LEVELS)
    if valid is not None:                             # only rows whose observation exists are translated (and need
        m &= np.asarray(valid, dtype=bool)            # parameters: e.g. no women's service-game counts before 2015)
    if not m.any():
        return T
    use_g = np.zeros(len(bucket), dtype=bool)
    use_d = np.zeros(len(bucket), dtype=bool)
    for t in set(tour[m].tolist()):
        on, g_on = input_class(cfg, name, t)
        if not on:
            continue
        mt = m & (tour == t)
        use_g |= mt & bool(g_on and gamma_term)
        levels = delta_levels(cfg, stat if delta_from == "stat" else name, t, "stat" if delta_from == "stat" else "input")
        use_d |= mt & np.isin(bucket, list(levels))
    if use_g.any():
        if strength is None:
            raise ValueError(f"{name}: the gamma term needs the strength per row")
        g = param_rows(cfg, "gamma", stat, tour, bucket, season, use_g)
        ref = param_rows(cfg, "strength_ref", stat, tour, bucket, season, use_g)
        gap = (np.asarray(strength, dtype="float64") - ref) / cfg["gamma_scale"]
        T[use_g] += np.nan_to_num(g * gap)[use_g]           # NaN only under missing_params "untouched"
    if use_d.any():
        T[use_d] += np.nan_to_num(param_rows(cfg, "delta", stat, tour, bucket, season, use_d))[use_d]
    T *= float(sign)
    if not np.isfinite(T).all():
        raise ValueError(f"{name}: a translation is not finite")
    return T


def summary(w: np.ndarray, T: np.ndarray, bucket: np.ndarray, mask: np.ndarray | None, season) -> dict:
    """A record of what a hook did, per level: the rows of seasons before the sealed holdout's (w and T described), and
    a count of the sealed seasons' rows (nothing derived from their parameters)."""
    mask = np.ones(len(w), dtype=bool) if mask is None else np.asarray(mask, dtype=bool)
    dev = dev_rows(season)
    out = {}
    for L in sorted(set(np.asarray(bucket)[mask].tolist())):
        m = mask & (bucket == L) & dev
        out[L] = {"rows_dev_seasons": int(m.sum()), "rows_sealed_seasons": int((mask & (bucket == L) & ~dev).sum())}
        if m.any():
            out[L].update({"w_mean": float(w[m].mean()), "w_zero": int((w[m] == 0).sum()),
                           "T_mean": float(T[m].mean()), "T_abs_mean": float(np.abs(T[m]).mean())})
    return out


# ------------------------------------------------------------------------------------------------
# Family hooks: points_52w (Stage 4's history sums)

def points_counts(rows: pd.DataFrame, stat: str, x: np.ndarray, d: np.ndarray, ok: np.ndarray):
    """Stage 4's history counts of spw or rpw with each lower-level row translated and weighted: (x, d) as they were
    when the layer or the family is off, or for another statistic."""
    if stat not in RATE_STATS:
        return x, d
    cfg = active("points_52w")
    if cfg is None:
        return x, d
    t0 = time.time()
    mids = rows["match_id"].to_numpy()
    bucket = buckets_of(mids, cfg)
    tour = rows["tour"].to_numpy().astype(str)
    season = rows["year"].to_numpy()
    okb = np.asarray(ok, dtype=bool)
    xf, df = np.asarray(x, dtype="float64"), np.asarray(d, dtype="float64")
    w = weights(cfg, stat, tour, bucket, season, "box", valid=okb)
    strength = None
    if cfg["translate"]:
        strength = opponent_strength(cfg, mids, rows["side"].to_numpy())
    T = translation(cfg, "points_52w", stat, tour, bucket, season, strength, valid=okb)
    xt = xf.copy()
    tr = okb & (T != 0)
    if tr.any():
        r = (xf[tr] + 0.5) / (df[tr] + 1.0)
        xt[tr] = xf[tr] + df[tr] * (expit(logit(r) - T[tr]) - r)
    x2 = np.where(okb, xt * w, xf)
    d2 = np.where(okb, df * w, df)
    record(cfg, {"hook": "points_counts", "family": "points_52w", "stat": stat, "rows": int(len(rows)),
                 "admitted": int(okb.sum()), "translated": int(tr.sum()),
                 "levels": summary(w, T, bucket, okb & lower_mask(bucket), season),
                 "seconds": round(time.time() - t0, 2)})
    log(f"points_52w {stat}: {int((okb & lower_mask(bucket)).sum()):,} lower-level rows of {int(okb.sum()):,} "
        f"admitted; translated {int(tr.sum()):,}; w at zero {int((okb & (w == 0)).sum()):,}")
    return x2, d2


# ------------------------------------------------------------------------------------------------
# Family hooks: the 17 one-step forms (Stage B)

def pair_moments_w(P, specs: dict, wanted) -> dict:
    """stageB_common.pair_moments with a weight per source row: specs maps a name to (a, valid, units, rw), each per
    box row in P's sorted order. With rw = 1 it is pair_moments exactly (the same operations in the same order, x 1.0)."""
    from src.eda.ufc_ideas import stageB_common as B
    wanted = list(dict.fromkeys(wanted))
    prep = {}
    for name in {w_[0] for w_ in wanted}:
        a, valid, units, rw = specs[name]
        valid = np.asarray(valid, dtype=bool)
        av = np.where(valid, np.nan_to_num(np.asarray(a, dtype="float64")), 0.0)
        un = np.asarray(units, dtype="float64")
        rw = np.asarray(rw, dtype="float64")
        taus = {t for n_, _, t in wanted if n_ == name}
        prep[name] = (av, {t: np.where(valid, un ** t if t != 0 else 1.0, 0.0) * rw for t in taus})
    out = {k: (np.zeros(P.n), np.zeros(P.n), np.zeros(P.n)) for k in wanted}
    hs = {h for _, h, _ in wanted}
    for tgt, src, dt in P.chunks():
        lo, hi = int(tgt[0]), int(tgt[-1]) + 1
        rel = tgt - lo
        m = hi - lo
        decs = {h: B.decay(dt, h) for h in hs}
        gathered = {}
        for name, h, t in wanted:
            av, uv = prep[name]
            if name not in gathered:
                gathered[name] = av[src]
            a = gathered[name]
            w = decs[h] * uv[t][src]
            S0, S1, M = out[(name, h, t)]
            s0 = np.bincount(rel, weights=w, minlength=m)
            s1 = np.bincount(rel, weights=w * a, minlength=m)
            with np.errstate(divide="ignore", invalid="ignore"):
                mean = np.where(s0 > 0, s1 / np.where(s0 > 0, s0, 1.0), 0.0)
            S0[lo:hi] += s0
            S1[lo:hi] += s1
            M[lo:hi] += np.bincount(rel, weights=w * np.abs(a - mean[rel]), minlength=m)
        del gathered
    return out


_BOX: dict = {}                                       # kept for the tests' cache reset; the keys live on the context


def _box_keys(ctx, cfg: dict) -> dict:
    """Per box position of a Stage B context: match id, level, tour, season, side. Cached ON the context object, so a
    new context (Stage B's probe builds one per cut) never reads another's keys."""
    keys = getattr(ctx, "_lle_box_keys", None)
    if keys is None or keys["n"] != len(ctx.box_idx):
        rows = ctx.rows
        bi = ctx.box_idx
        mids = rows["match_id"].to_numpy()[bi]
        keys = {"n": len(bi), "mids": mids, "bucket": buckets_of(mids, cfg),
                "tour": np.asarray(ctx.tour_box).astype(str), "season": rows["year"].to_numpy()[bi],
                "side": rows["side"].to_numpy()[bi]}
        ctx._lle_box_keys = keys
    return keys


def forms_z(ctx, chosen: dict, Z: dict) -> dict:
    """Stage B's per-match z of the 17 pairs recomputed with the layer: the opponents' norms re-referenced (each norm row
    translated and weighted), the match's own value shifted by delta. Z unchanged (the same dict) when the layer or the
    family is off. The other pairs keep the builder's z."""
    cfg = active("forms")
    if cfg is None:
        return Z
    keys = [k for k in FORM_SPECS if k in Z]
    if not keys:
        return Z
    from src.eda.ufc_ideas import stageB_adjperf as AP
    t0 = time.time()
    K = _box_keys(ctx, cfg)
    bucket, tour, season = K["bucket"], K["tour"], K["season"]
    strength = opponent_strength(cfg, K["mids"], K["side"]) if cfg["translate"] else None
    # the match's own value: the row's match level, both rows of a match alike (all rows, not only box rows)
    rows = ctx.rows
    r_mids = rows["match_id"].to_numpy()
    r_bucket = buckets_of(r_mids, cfg)
    r_tour = rows["tour"].to_numpy().astype(str)
    r_season = rows["year"].to_numpy()
    specs, wanted, plan, rec = {}, [], {}, {}
    for s, ch in keys:
        name = input_name(s, ch)
        views = form_views(s, ch)
        a, ok, units = ctx.spec(s, ch)                    # per box position (the norm owner's row): value, valid, units
        nstat, nsign = views["norm"]
        T_norm = translation(cfg, name, nstat, tour, bucket, season, strength, nsign, valid=ok)
        a2 = np.where(ok, np.asarray(a, dtype="float64") - T_norm, a)
        w_row = weights(cfg, nstat, tour, bucket, season, "box", valid=ok)
        rw = w_row if cfg["forms_norm_weight"] else np.ones(len(w_row))
        specs[(s, ch)] = (ctx.P.to_sorted(a2), ctx.P.to_sorted(ok), ctx.P.to_sorted(units), ctx.P.to_sorted(rw))
        per_tour = {}
        for t in TOURS:
            c = AP.constants_for(chosen, s, ch, t)
            per_tour[t] = c
            wanted.append(((s, ch), c["h1"], c["tau"]))
        own = np.zeros(len(rows))
        if cfg["translate"] and cfg["forms_own_delta"]:
            ostat, osign = views["own"]
            own = translation(cfg, name, ostat, r_tour, r_bucket, r_season, None, osign, gamma_term=False,
                              valid=ctx.sa[s]["ok"])
        rec[name] = {"norm_view": nstat, "norm_sign": nsign,
                     "norm": summary(w_row, T_norm, bucket, np.asarray(ok, bool) & lower_mask(bucket), season),
                     "own_delta_rows": int((own != 0).sum())}
        plan[(s, ch)] = (per_tour, own)
    mom = pair_moments_w(ctx.P, specs, wanted)
    out = dict(Z)
    for s, ch in keys:
        per_tour, own = plan[(s, ch)]
        proxy = copy.copy(ctx)                            # the builder's own z formula, on the shifted own values
        proxy.sa = dict(ctx.sa)
        proxy.sa[s] = {**ctx.sa[s], "c": ctx.sa[s]["c"] - own}
        z = np.full(len(ctx.box_idx), np.nan)
        for t in TOURS:
            c = per_tour[t]
            m3 = mom[((s, ch), c["h1"], c["tau"])]
            m_ = tuple(ctx.P.from_sorted(x) for x in m3)
            zt, _, _ = proxy.z(s, ch, m_, c["K1"], c["tau"])
            sel = ctx.tour_box == t
            z[sel] = zt[sel]
        out[(s, ch)] = z
    record(cfg, {"hook": "forms_z", "family": "forms", "box_rows": int(len(ctx.box_idx)), "pairs": len(keys),
                 "inputs": rec, "seconds": round(time.time() - t0, 2)})
    log(f"forms: {len(keys)} pairs recomputed with the layer in {time.time() - t0:.0f} s")
    return out


def forms_step3(ctx, stat: str, channel: str, zs: list, units: np.ndarray, ok: np.ndarray, tau: int, half_lives):
    """Stage B's step-3 sums (Ctx.step3) with each box row's weight multiplied by its w; a row with w = 0 does not count
    toward the form's existence. Ctx.step3 itself when the layer or the family is off, or for the other pairs."""
    cfg = active("forms")
    if cfg is None or (stat, channel) not in FORM_SPECS:
        return ctx.step3(zs, units, ok, tau, half_lives)
    from src.eda.ufc_ideas import stageB_common as B
    K = _box_keys(ctx, cfg)
    rw = weights(cfg, form_views(stat, channel)["step3"][0], K["tour"], K["bucket"], K["season"], "box", valid=ok)
    k = len(zs)
    V = np.zeros((len(ctx.U), k + 2))
    w = np.where(ok, units ** tau if tau else 1.0, 0.0) * rw
    for j, z in enumerate(zs):
        V[ctx.u_pos_box, j] = np.where(ok, w * np.nan_to_num(z), 0.0)
    V[ctx.u_pos_box, k] = w
    V[ctx.u_pos_box, k + 1] = (np.asarray(ok, bool) & (rw > 0)).astype("float64")
    record(cfg, {"hook": "forms_step3", "family": "forms", "input": input_name(stat, channel),
                 "rows": int(np.asarray(ok, bool).sum()), "w_zero": int((np.asarray(ok, bool) & (rw == 0)).sum())})
    return B.windowed_sums(ctx.frame, V, [h for h in half_lives if np.isfinite(h)])


def pin(what: str, chosen: dict) -> dict:
    """A builder's tuned constants replaced by the reference build's (the config's pins); `chosen` itself when the layer
    is off or nothing is pinned. Stage B's adjperf: {(tour, core statistic): constants}."""
    cfg = config()
    if cfg is None:
        return chosen
    ref = pinned(cfg, what)
    if ref is None:
        return chosen
    if what != "stageB_adjperf":
        raise KeyError(f"no pin rule for {what}")
    out = {}
    for c in ref["chosen"]:
        d = {k: v for k, v in c.items() if k not in ("tour", "stat")}
        for k in ("h1", "K1", "h3", "K3"):
            d[k] = float(d[k])
        d["tau"] = int(d["tau"])
        out[(c["tour"], c["stat"])] = d
    keys5 = ("h1", "K1", "tau", "h3", "K3")
    same = {f"{t}|{s}": all(float(chosen[(t, s)][k]) == float(out[(t, s)][k]) for k in keys5) for (t, s) in out}
    if set(out) != set(chosen):
        raise KeyError(f"pin {what}: the reference names {sorted(out)}, the build {sorted(chosen)}")
    record(cfg, {"hook": "pin", "what": what, "tuned_equals_reference": same})
    log(f"pin {what}: the reference's constants used; tuned equal to them: {same}")
    return out


# ------------------------------------------------------------------------------------------------
# Family hooks: the serve and return ratings (Stage 3) and Elo

def ratings_arrays(t: pd.DataFrame, h: dict) -> dict:
    """Stage 3's pass inputs for one tour with the layer: each lower-level match's serve points and points won x w (the
    observation counts as w of a main-tour one; w = 0 moves nothing) and its intercept mu + delta (the level term in the
    solve's units, where A calls delta real for ratings_iid). h itself when the layer or the family is off."""
    cfg = active("ratings_iid")
    if cfg is None:
        return h
    t0 = time.time()
    stat = (cfg.get("solve_stat") or {}).get("ratings_iid", "spw")
    mids = t["match_id"].to_numpy()
    bucket = buckets_of(mids, cfg)
    tour = t["tour"].to_numpy().astype(str)
    season = t["year"].to_numpy()
    rated = np.asarray(h["upd"], dtype=bool)
    # one observation informs the server's S and the returner's R: one weight (B: w_joint, the two sides' mean); the
    # supplied delta is a residual after Elo's gamma, not in this solve's units (A, B, C2), so no level term unless the
    # config asks for it
    w = weights(cfg, stat, tour, bucket, season, "box", valid=rated, column=cfg.get("solve_w", "w_joint"))
    if cfg.get("ratings_level_term", "none") == "supplied":
        delta = translation(cfg, "ratings_iid", stat, tour, bucket, season, None, gamma_term=False,
                            delta_from="input", valid=rated)
    else:
        delta = np.zeros(len(t))
    out = dict(h)
    for c in ("n_a", "w_a", "n_b", "w_b"):
        out[c] = (np.asarray(h[c], dtype="float64") * w).tolist()
    out["mu"] = (np.asarray(h["mu"], dtype="float64") + delta).tolist()
    upd = np.asarray(h["upd"], dtype=bool)
    record(cfg, {"hook": "ratings_arrays", "family": "ratings_iid", "matches": int(len(t)),
                 "levels": summary(w, delta, bucket, upd & lower_mask(bucket), season),
                 "seconds": round(time.time() - t0, 2)})
    log(f"ratings_iid {tour[0] if len(tour) else ''}: {int((upd & lower_mask(bucket)).sum()):,} lower-level rating "
        f"matches; w at zero {int((upd & (w == 0)).sum()):,}")
    return out


def elo_weights(frame: pd.DataFrame, upd: list) -> list:
    """The Elo passes' update flags as weights: w_results for a played lower-level match in the arm's tours, 1 for the
    others, 0 where the match moves nothing. `upd` itself when the layer or the family is off. The patched passes add
    K x upd[i] and count upd[i]; with booleans they are the original passes."""
    cfg = active("elo")
    if cfg is None:
        return upd
    mids = frame["match_id"].to_numpy()
    bucket = buckets_of(mids, cfg)
    tour = frame["tour"].to_numpy().astype(str)
    season = frame["year"].to_numpy()
    w = weights(cfg, "results", tour, bucket, season, "results")
    u = np.asarray(upd, dtype=bool)
    out = np.where(u, w, 0.0)
    record(cfg, {"hook": "elo_weights", "family": "elo", "matches": int(len(frame)),
                 "levels": summary(w, np.zeros(len(w)), bucket, u & lower_mask(bucket), season)})
    return out.tolist()


def elo_rerun(frame: pd.DataFrame, upd: list, out, rerun):
    """A builder's frozen Elo pass `out` re-run with the layer's weights (rerun(weights) -> the pass); `out` itself when
    the layer or the family is off."""
    w = elo_weights(frame, upd)
    if w is upd:
        return out
    return rerun(w)


# ------------------------------------------------------------------------------------------------

def describe(cfg: dict) -> dict:
    """What an arm's config does, for the gates and the report."""
    return {"name": cfg["name"], "tours": cfg["tours"], "translate": cfg["translate"], "weight": cfg["weight"],
            "weight_results": cfg["weight_results"], "prior": cfg["prior"], "itf_box": cfg["itf_box"],
            "families": cfg["families"], "classes": cfg.get("classes"), "params": cfg.get("params"),
            "elo_count": cfg["elo_count"], "forms_norm_weight": cfg["forms_norm_weight"],
            "forms_own_delta": cfg["forms_own_delta"], "fitted_cap": cfg.get("fitted_cap"),
            "fitted_cap_results": cfg.get("fitted_cap_results"), "solve_w": cfg.get("solve_w"),
            "ratings_level_term": cfg.get("ratings_level_term"), "missing_params": cfg.get("missing_params"),
            "params_season_floor": cfg.get("params_season_floor"),
            "params_season_ceiling": cfg.get("params_season_ceiling"),
            "form_views": {input_name(s, ch): form_views(s, ch) for s, ch in FORM_SPECS}}


def capped_cells(cfg: dict, through: int = SEALED_FROM - 1) -> pd.DataFrame:
    """The parameter cells of the arm's tours whose fitted weight the caps change, seasons through `through` only (the
    sealed seasons' values are never read here): box statistics' w and w_joint against fitted_cap, w_results (stat
    "results", column w) against fitted_cap_results. Empty when the arm reads no fitted weight."""
    cols = ["season_used", "tour", "stat", "level", "column", "fitted", "capped_to"]
    if not cfg.get("params") or "fitted" not in (cfg["weight"], cfg["weight_results"]):
        return pd.DataFrame(columns=cols)
    t = params_table(cfg).reset_index()
    t = t[(t["season_used"] <= through) & t["tour"].isin(cfg["tours"])]
    rows = []
    for kind, cap in (("box", cfg.get("fitted_cap")), ("results", cfg.get("fitted_cap_results"))):
        if cap is None or (cfg["weight"] if kind == "box" else cfg["weight_results"]) != "fitted":
            continue
        sub = t[(t["stat"] == "results") == (kind == "results")]
        for col in (("w", "w_joint") if kind == "box" else ("w",)):
            if col not in sub.columns:
                continue
            hit = sub[sub[col] > cap]
            rows += [{"season_used": int(r.season_used), "tour": r.tour, "stat": r.stat, "level": r.level,
                      "column": col, "fitted": float(getattr(r, col)), "capped_to": float(cap)}
                     for r in hit.itertuples(index=False)]
    return pd.DataFrame(rows, columns=cols).sort_values(["tour", "column", "stat", "level", "season_used"],
                                                        ignore_index=True)
