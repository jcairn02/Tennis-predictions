"""S3, the pool rebuilder of the unpriced-leads study (docs/studies/unpriced_leads/team/pool_rebuild.md, 13 Oct 2026).

Feature-store columns that may enter the study's registered lead groups, rebuilt for EVERY match of the current
instance's frame (data/studies/current_best_model/template_2026-10-10/model_frame.parquet, 67,226 matches, 2013-2026) by
the original builder functions, run unchanged (imported, never edited) on a panel and a long table assembled from the
current tables. The store (data/studies/feature_universe/store.parquet) was built on the 30 Sep tables for the frozen
frame: it lacks men's 2018 and part of 2026, and its box-score columns predate the 8 Oct corrections.

    catalogue      store column(s)                                   builder (module function, unchanged)
    U-284 / U-162  fp__f19_motiv__post_a/_b, fi__B-MOTIV__post_slam  f19_motiv.prepare_motiv, combine_bmotiv
    U-283          fi__B-MOTIV__elite_pre_slam                       f19_motiv.combine_bmotiv (pre_slam x top-20)
    U-254          fp__f09_venue__f09_ve, fi__B-VENUE__x             f09_venue.prepare_venue (the leak-proof venue
                   (and the unscaled f09_venue_pace_x_ace)           pace, the module's own clock logic), x_i072,
                                                                     f01_structure_lib.signed_block
    U-330          el__low_share_a/_b, el__low_share_diff            event_levels.blend.history (universe_columns.py's
                                                                     call: years 2013-2026, main-tour queries)
    U-261          fp__f12_salience__salL_a/_b, hasL_a/_b,           f12_salience.prepare_i082; x = salL_A - salL_B
                   fi__I-082__x
    U-175          pp__seeded_a/_b                                   build_store's rule: Stage 0's seed present
    U-177          fp__f14_anchor__fame_a/_b                         f14_anchor.prepare_fame (mkt_common.fame)
    U-138 / U-307  fp__f17_info__bd11_on_n_a/_b, fi__B11__bd11_on    f24_onsite.prepare_b11, b11_members (I-051 On)
    U-143 / U-322  fp__f28_state__bdst_pastfat_a/_b, fi__B-STATE__x  f28_state.past_fat on f20_fatigue.history,
                                                                     f20_fatigue.block (BOD-C1 alone, as combine_state)
    U-153          fp__f17_info__bd11_nov_a/_b                       f24_onsite.prepare_b11 (Nov)
    U-148          fp__f23_arrival__bd10_trav_a/_b                   f23_arrival.prepare_b10 (Trav)

Values (values.parquet): match_id, then for every rebuilt store column `rb__<store name>` (pairs as _a, _b and their
A - B as `rb__<stem>_a-b`; match-level and difference columns under their own names). No result column.

The registered build (V1) reads:
    long table   screen.long_table() (feature_interactions.history.long_table's logic) on the 8 Oct Stage 0
                 (data/studies/predictability_diagnostic/) and the match clock as on disk
                 (data/studies/match_timing/timing.parquet), with the box-score columns
    panel        the frame's ids, tours, seasons and dates (never its result) + the same Stage 0's pre-match fields and
                 sides + the clock's es / lf (feature_interactions.panel's join, for the columns these builders read)
    surface IOS  the current instance's own table (its build sandbox, C:/Users/zerom/tnr_lyr_new; it reproduces the
                 frame's IOS inputs bit for bit), frozen as an extract in inputs/ with its SHA-256: the venue pace's
                 expected ace rate and the target's ace offence
    Stage B z    the current instance's own stageB_adj (same sandbox; men's per-match z with the level layer), extract
                 in inputs/: the per-match z of salience (I-082)
    Court        tennis-data's Court through the 8 Oct Stage 1 odds (indoor status, for novelty)
Variants (outcome-free; for the verification and the sensitivity only, never registered):
    V0  the store's own inputs: the 30 Sep Stage 0 and clock, the repository's surface IOS and Stage B, the store's
        frame (63,737 matches): must reproduce the store
    Vk  V0 with today's clock                                  (V0 -> Vk: the clock)
    Vs  V1 with the repository's surface IOS and Stage B        (Vk -> Vs: the 8 Oct Stage 0 and the frame)
    Vz  V1 with Stage B rebuilt on the same 8 Oct Stage 0 without the level layer (the layer-off build of the
        level-layer adoption study, C:/Users/zerom/tnr_lyr_off; added after the first screen, to explain the move
        of salience)                                           (Vs -> Vz: the instance's surface IOS, Stage B rebuilt)
                                                               (Vz -> V1: the level layer inside Stage B)
    V2  the instance's own Stage 0 (8 Oct + the accepted men's 2026 Challenger package) and clock (10 Oct)

Checks: verify.csv (each rebuilt column against the store on the matches both hold, seasons <= 2024: share equal to
1e-9, correlation, and each difference attributed to the step that makes it), probes.json (screen.timing_probe on every
own-sequence builder, run on a panel of every match so each history row is compared; the venue pace: f01's probe-
equivalent and the scramble probe's future rows; leaky controls must move; all on the history before 29 Jul 2026),
coverage.json (by tour and season, 2013-2024, 2025, and 2026 before 29 Jul), sensitivity.csv (V2 against V1, matches
before 29 Jul 2026).
Screens: every rebuilt candidate with the harness on seasons <= 2024 (screen.load_frame is the only read of a result):
raw and orthogonal part, close lens without and with the curvature terms, the model and move lenses, and the raw column
on the store's rows only; summary.csv sets the pool statistician's readings of the store column beside them.

Blinding: values are computed for every frame match (2013-2026); no 2025-26 value is compared with its result, and no
match from 29 Jul 2026 on is counted, summarised or inspected (every count below filters tournament_date < 29 Jul 2026).

Run: ./python.sh src/eda/unpriced_leads/rebuild_pool.py      (CPU, one BLAS thread; about an hour on a busy machine)
     --reuse-variants   reuse variants/*.parquet already built (development only)
     --skip-probes      no timing probes (development only)
"""
from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[_v] = "1"             # one BLAS thread before numpy loads: the same digits on any machine, and no
                                     # oversubscription while other jobs share the CPU

import argparse  # noqa: E402
import gc  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import blend as BL  # noqa: E402
from src.eda.event_levels import common as ELC  # noqa: E402
from src.eda.feature_interactions import panel as PN  # noqa: E402
from src.eda.feature_interactions.features import f01_structure_lib as S1  # noqa: E402
from src.eda.feature_interactions.features import f09_venue as F09  # noqa: E402
from src.eda.feature_interactions.features import f12_salience as F12  # noqa: E402
from src.eda.feature_interactions.features import f14_anchor as F14  # noqa: E402
from src.eda.feature_interactions.features import f19_motiv as F19  # noqa: E402
from src.eda.feature_interactions.features import f20_fatigue as F20  # noqa: E402
from src.eda.feature_interactions.features import f23_arrival as F23  # noqa: E402
from src.eda.feature_interactions.features import f24_onsite as F24  # noqa: E402
from src.eda.feature_interactions.features import f28_state as F28  # noqa: E402
from src.eda.feature_interactions.features import mkt_common as M  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

STUDIES = ROOT / "data" / "studies"
OUT = STUDIES / "unpriced_leads" / "candidates" / "pool_rebuilt"
INPUTS = OUT / "inputs"
VARIANT_DIR = OUT / "variants"
STORE = STUDIES / "feature_universe" / "store.parquet"
POOL_SUMMARY = STUDIES / "unpriced_leads" / "pool_scan" / "summary.csv"
OLD = STUDIES / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
SANDBOX = Path("C:/Users/zerom/tnr_lyr_new") / "data" / "studies"     # the current instance's build sandbox (its
                                                                      # README: build_template.sh C:/Users/zerom/tnr_lyr_new)
SEALED = pd.Timestamp("2026-07-29")         # Look B: values computed, never counted, summarised or inspected
PD = "predictability_diagnostic"
BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced", "tpw_n", "tpw_d",
       "spw_n", "spw_d", "rpw_n", "rpw_d"]
IOS_COLS = ["srf_O_eff_ace", "srf_D_eff_ace", "srf_O_eff_spw", "srf_D_eff_spw"]   # what f09's serve_rows reads
PLAYER_FIELDS = ("rank", "rank_points", "seed", "entry", "age", "height", "hand", "country")
MATCH_FIELDS = ["tournament_id", "tournament_name", "round", "level", "best_of", "indoor", "surface", "draw_size",
                "player_a_id", "player_b_id"]
KEYS = ["match_id", "tour", "season", "tournament_date", "debut_season"]
TOL = 1e-9
T0 = time.time()

# the current instance's own tables, pinned (SHA-256 of the sandbox files read on 13 Oct 2026), frozen as extracts
INSTANCE = {
    "ios": {"src": SANDBOX / "surface_ios" / "surface_features.parquet",
            "sha256": "caadfc7fa2be3606f7ae0b8c8f875965a0dc149fc1aafefc8eae9374388bfc2d",
            "extract": INPUTS / "instance_surface_ios.parquet",
            "cols": ["match_id"] + [f"{c}_{s}" for c in IOS_COLS for s in "ab"]},
    "stageb": {"src": SANDBOX / "ufc_ideas" / "stageB_adj.parquet",
               "sha256": "e901bb15c5cfebdb1b51a78909972f1f4b1367fb172f4839cfeb144c53c1c15e",
               "extract": INPUTS / "instance_stageB_z.parquet",
               "cols": ["match_id", "player_id", "z_adjperf_tpw"]},
    # Stage B on the same 8 Oct Stage 0 with the level layer off (the level-layer adoption study's B_off build,
    # LLE_LAYER unset; its Stage 0 hashes as the repository's): variant Vz only, to separate the layer's effect
    "stageb_off": {"src": Path("C:/Users/zerom/tnr_lyr_off") / "data" / "studies" / "ufc_ideas" / "stageB_adj.parquet",
                   "sha256": "26573353a3a27d90cbda4ac33f93f77bb058a9adfd87e96bbb836b16f81829c3",
                   "extract": INPUTS / "layer_off_stageB_z.parquet",
                   "cols": ["match_id", "player_id", "z_adjperf_tpw"]},
}
REPO = {"ios": STUDIES / "surface_ios" / "surface_features.parquet",
        "stageb": STUDIES / "ufc_ideas" / "stageB_adj.parquet"}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_info(p: Path) -> dict:
    p = Path(p)
    return {"path": str(p), "sha256": sha256(p), "bytes": p.stat().st_size,
            "modified": pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").isoformat(timespec="seconds")}


# ------------------------------------------------------------------------------------------------------ the tables

@dataclass(frozen=True)
class Tables:
    name: str
    desc: str
    stage0_m: str
    stage0_p: str
    timing: str
    odds: str           # Stage 1 odds: the tennis-data Court links (indoor status)
    ios: str            # "repo" | "instance" | a table's path (live_members.py)
    stageb: str         # "repo" | "instance" | "layer_off"
    frame: str          # "current" | "store"


CUR = STUDIES / PD
SPEC = {
    "V1": Tables("V1", "registered: the 8 Oct Stage 0, the clock as on disk, the instance's surface IOS and Stage B; "
                       "the current frame",
                 str(CUR / "stage0_matches.parquet"), str(CUR / "stage0_match_players.parquet"),
                 str(STUDIES / "match_timing" / "timing.parquet"), str(CUR / "stage1_odds.parquet"),
                 "instance", "instance", "current"),
    "V0": Tables("V0", "the store's inputs: the 30 Sep Stage 0 and clock, the repository's surface IOS and Stage B; "
                       "the store's frame",
                 str(OLD / PD / "stage0_matches.parquet"), str(OLD / PD / "stage0_match_players.parquet"),
                 str(OLD / "match_timing" / "timing.parquet"), str(OLD / PD / "stage1_odds.parquet"),
                 "repo", "repo", "store"),
    "Vk": Tables("Vk", "V0 with the clock as on disk",
                 str(OLD / PD / "stage0_matches.parquet"), str(OLD / PD / "stage0_match_players.parquet"),
                 str(STUDIES / "match_timing" / "timing.parquet"), str(OLD / PD / "stage1_odds.parquet"),
                 "repo", "repo", "store"),
    "Vs": Tables("Vs", "V1 with the repository's (30 Sep tables) surface IOS and Stage B",
                 str(CUR / "stage0_matches.parquet"), str(CUR / "stage0_match_players.parquet"),
                 str(STUDIES / "match_timing" / "timing.parquet"), str(CUR / "stage1_odds.parquet"),
                 "repo", "repo", "current"),
    "Vz": Tables("Vz", "V1 with Stage B rebuilt on the same 8 Oct Stage 0 without the level layer (the layer-off "
                       "build's)",
                 str(CUR / "stage0_matches.parquet"), str(CUR / "stage0_match_players.parquet"),
                 str(STUDIES / "match_timing" / "timing.parquet"), str(CUR / "stage1_odds.parquet"),
                 "instance", "layer_off", "current"),
    "V2": Tables("V2", "the instance's own tables: its Stage 0 (8 Oct + the accepted men's 2026 Challenger package) and "
                       "its clock (10 Oct), with its surface IOS and Stage B; the current frame",
                 str(SANDBOX / PD / "stage0_matches.parquet"), str(SANDBOX / PD / "stage0_match_players.parquet"),
                 str(SANDBOX / "match_timing" / "timing.parquet"), str(CUR / "stage1_odds.parquet"),
                 "instance", "instance", "current"),
}


def instance_extract(kind: str) -> Path:
    """The current instance's table (`kind` ios or stageb) as a frozen extract: written from the sandbox once, after
    checking the sandbox file's pinned SHA-256; reused afterwards when its record matches (the sandbox may go)."""
    spec = INSTANCE[kind]
    ext, meta = spec["extract"], spec["extract"].with_suffix(".json")
    if ext.exists() and meta.exists():
        rec = json.loads(meta.read_text(encoding="utf-8"))
        if rec["source_sha256"] == spec["sha256"] and rec["extract_sha256"] == sha256(ext):
            return ext
    if not spec["src"].exists():
        raise FileNotFoundError(f"{spec['src']} (the instance's {kind} table) is gone and no valid extract exists")
    got = sha256(spec["src"])
    if got != spec["sha256"]:
        raise RuntimeError(f"{spec['src']} is not the pinned instance table ({got[:12]} != {spec['sha256'][:12]})")
    t = pd.read_parquet(spec["src"], columns=spec["cols"])
    t["match_id"] = t["match_id"].astype(str)
    INPUTS.mkdir(parents=True, exist_ok=True)
    t.to_parquet(ext, index=False)
    meta.write_text(json.dumps({"source": str(spec["src"]), "source_sha256": got, "columns": spec["cols"],
                                "rows": int(len(t)), "extract_sha256": sha256(ext),
                                "written_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}, indent=1),
                    encoding="utf-8")
    log(f"extract written: {ext.name} ({len(t):,} rows)")
    return ext


def table_path(T: Tables, kind: str) -> Path:
    which = getattr(T, kind)
    if which == "instance":
        return instance_extract(kind)
    if which == "layer_off":
        return instance_extract("stageb_off")
    if which == "repo":
        return REPO[kind]
    return Path(which)          # a table named by path: live_members.py's run surface IOS (16 Oct 2026)


class Patched:
    """Points the builders' hard-wired sources at a variant's tables for the duration of a build: the harness's long
    table (screen.STAGE0_M / STAGE0_P / TIMING), the surface IOS f01 reads, the Stage 1 odds f25's Court join reads,
    the Stage 0 event_levels.blend.load reads, and f12's Stage B z (read from the long table's `zB` column, which
    long_table() merges from the variant's Stage B). Module files are never edited; everything is restored on exit."""

    def __init__(self, T: Tables):
        self.T = T

    def __enter__(self):
        self.saved = (H.STAGE0_M, H.STAGE0_P, H.TIMING, S1.SURFACE_FEATURES, PN.SOURCES["stage1_odds"],
                      ELC.SOURCES["stage0_matches"], ELC.SOURCES["stage0_players"], F12.stage_b_z)
        H.STAGE0_M, H.STAGE0_P, H.TIMING = Path(self.T.stage0_m), Path(self.T.stage0_p), Path(self.T.timing)
        S1.SURFACE_FEATURES = table_path(self.T, "ios")
        PN.SOURCES["stage1_odds"] = Path(self.T.odds)
        ELC.SOURCES["stage0_matches"] = (Path(self.T.stage0_m), None)
        ELC.SOURCES["stage0_players"] = (Path(self.T.stage0_p), None)
        F12.stage_b_z = z_from_history
        clear_caches()
        return self

    def __exit__(self, *exc):
        (H.STAGE0_M, H.STAGE0_P, H.TIMING, S1.SURFACE_FEATURES, PN.SOURCES["stage1_odds"],
         ELC.SOURCES["stage0_matches"], ELC.SOURCES["stage0_players"], F12.stage_b_z) = self.saved
        clear_caches()
        return False


def clear_caches() -> None:
    """The builders memoise on object ids (mkt_common) and on (id(L), season) (f20): cleared before every build so no
    stale history can be served to a new (e.g. scrambled) table that reuses an id."""
    M.clear_memo()
    F20.clear_cache()


def z_from_history(Hh: pd.DataFrame) -> np.ndarray:
    """f12_salience.stage_b_z's replacement: Stage B's per-match z_adjperf_tpw, merged into the long table by
    long_table() from the variant's Stage B with f12's own rule (one value per match and player, left join)."""
    return Hh["zB"].to_numpy(float)


def long_table(T: Tables) -> tuple[pd.DataFrame, dict]:
    """screen.long_table() on the variant's Stage 0 and clock, with the box-score columns and Stage B's z (`zB`).
    Stage 0 matches without a clock row (only Vk: 42 matches of 2026 that the later Stage 0 dropped) leave the table,
    and the harness's own sequence columns are recomputed for what remains."""
    L = H.long_table(player_cols=BOX)
    early = (pd.to_datetime(L["tournament_date"]) < SEALED).to_numpy()      # counts never include Look B's period
    miss = ~np.isfinite(L["obs"].to_numpy(float))
    info = {"counted": "rows with a tournament date before 29 Jul 2026", "rows": int(early.sum()),
            "players": int(L.loc[early, "player_id"].nunique()), "rows_without_clock": int((miss & early).sum())}
    if miss.any():
        L = L[~miss].copy()
        L = L.sort_values(["player_id", "ev_obs", "tday", "tournament_id", "round_order", "match_num"], kind="stable")
        L["k"] = L.groupby("player_id").cumcount()
        L["obs_mono"] = L.groupby("player_id")["obs"].cummax()
        g = L.groupby("player_id")
        L["rest_days"] = L["obs_mono"] - g["obs_mono"].shift(1)
        L["rest_min"] = L["es"] - g["lf"].shift(1)
        L = L.reset_index(drop=True)
    z = pd.read_parquet(table_path(T, "stageb"), columns=["match_id", "player_id", "z_adjperf_tpw"])
    z["match_id"], z["player_id"] = z["match_id"].astype(str), z["player_id"].astype(str)
    z = z.drop_duplicates(["match_id", "player_id"])
    L["player_id"] = L["player_id"].astype(str)
    L["zB"] = L[["match_id", "player_id"]].merge(z, on=["match_id", "player_id"], how="left")["z_adjperf_tpw"] \
        .to_numpy(float)
    early = (pd.to_datetime(L["tournament_date"]) < SEALED).to_numpy()
    info["rows_with_z"] = int((np.isfinite(L["zB"].to_numpy(float)) & early).sum())
    return L, info


def keys_frame(kind: str) -> pd.DataFrame:
    """The population's keys (never a result column): the current frame's or the store's rows."""
    src = H.FRAME if kind == "current" else STORE
    f = pd.read_parquet(src, columns=KEYS)
    f["match_id"] = f["match_id"].astype(str)
    if f["match_id"].duplicated().any():
        raise RuntimeError(f"{src.name}: duplicated match ids")
    return f.reset_index(drop=True)


def panel(T: Tables, keys: pd.DataFrame) -> pd.DataFrame:
    """feature_interactions.panel's join, for the columns these builders read: the keys, Stage 0's pre-match match
    fields and sides, each side's pre-match player fields, the clock's es / lf, and the surface IOS ace offence."""
    P = keys.copy()
    m = pd.read_parquet(T.stage0_m, columns=["match_id"] + MATCH_FIELDS)
    m["match_id"] = m["match_id"].astype(str)
    P = P.merge(m, on="match_id", how="left", validate="one_to_one")
    p = pd.read_parquet(T.stage0_p, columns=["match_id", "side"] + list(PLAYER_FIELDS))
    p["match_id"] = p["match_id"].astype(str)
    for side, tag in (("A", "a"), ("B", "b")):
        q = p[p["side"] == side].drop(columns="side").drop_duplicates("match_id")
        q = q.rename(columns={c: f"{c}_{tag}" for c in PLAYER_FIELDS})
        P = P.merge(q, on="match_id", how="left", validate="one_to_one")
    t = pd.read_parquet(T.timing, columns=["match_id", "es", "lf", "exact"])
    t["match_id"] = t["match_id"].astype(str)
    P = P.merge(t.rename(columns={"exact": "clock_exact"}), on="match_id", how="left", validate="one_to_one")
    sf = pd.read_parquet(table_path(T, "ios"), columns=["match_id", "srf_O_eff_ace_a", "srf_O_eff_ace_b"])
    sf["match_id"] = sf["match_id"].astype(str)
    sf = sf.drop_duplicates("match_id").rename(columns={"srf_O_eff_ace_a": "ios_srfO_ace_a",
                                                        "srf_O_eff_ace_b": "ios_srfO_ace_b"})
    P = P.merge(sf, on="match_id", how="left", validate="one_to_one")
    P["player_a_id"], P["player_b_id"] = P["player_a_id"].astype(str), P["player_b_id"].astype(str)
    if set(P.columns) & {"a_won", "won", "y", "score"}:
        raise RuntimeError("a result column entered the panel")
    return P


def panel_all(T: Tables, L: pd.DataFrame) -> pd.DataFrame:
    """A panel of every match of the long table (for the probes: each history row then carries a value). Season: the
    tournament date's year, from 20 Dec the next (f20's rule)."""
    m = pd.read_parquet(T.stage0_m, columns=["match_id", "tour", "tournament_date"])
    m["match_id"] = m["match_id"].astype(str)
    m = m[m["match_id"].isin(set(L["match_id"]))]
    d = pd.to_datetime(m["tournament_date"])
    season = d.dt.year + ((d.dt.month == 12) & (d.dt.day >= 20)).astype(int)
    keys = pd.DataFrame({"match_id": m["match_id"].to_numpy(), "tour": m["tour"].to_numpy(),
                         "season": season.to_numpy(), "tournament_date": m["tournament_date"].to_numpy(),
                         "debut_season": False})
    P = panel(T, keys)
    return P[np.isfinite(P["es"].to_numpy(float))].reset_index(drop=True)


# ------------------------------------------------------------------------------------------------------ the build

PAIRS = ["fp__f19_motiv__post", "fi__B-MOTIV__elite_pre_slam", "fi__B-VENUE__f09_venue_pace_x_ace", "el__low_share",
         "fp__f12_salience__salL", "fp__f12_salience__hasL", "pp__seeded", "fp__f14_anchor__fame",
         "fp__f17_info__bd11_on_n", "fp__f28_state__bdst_pastfat", "fp__f17_info__bd11_nov",
         "fp__f23_arrival__bd10_trav"]


def build(T: Tables, L: pd.DataFrame, P: pd.DataFrame) -> dict[str, np.ndarray]:
    """Every rebuilt column at the panel's matches (store names, no prefix). Call inside Patched(T)."""
    clear_caches()
    out: dict[str, np.ndarray] = {}
    # U-284 / U-162 and U-283: f19_motiv
    mot = F19.prepare_motiv(P, L)
    Q = P.assign(**mot)
    bm = F19.combine_bmotiv(Q)
    out["fp__f19_motiv__nslam_days"] = np.asarray(mot["nslam_days"], float)
    out["fp__f19_motiv__post_a"], out["fp__f19_motiv__post_b"] = mot["post_a"], mot["post_b"]
    out["fi__B-MOTIV__post_slam"] = np.asarray(bm["tabpfn"]["post_slam"][0], float)
    s = F19.pre_slam(Q)
    ra, rb = M.pair(Q, "rank")
    ta = np.where(np.isfinite(ra), ra <= F19.TOP, False).astype(float)
    tb = np.where(np.isfinite(rb), rb <= F19.TOP, False).astype(float)
    out["fi__B-MOTIV__elite_pre_slam_a"], out["fi__B-MOTIV__elite_pre_slam_b"] = s * ta, s * tb
    out["fi__B-MOTIV__elite_pre_slam"] = np.asarray(bm["tabpfn"]["elite_pre_slam"][0], float)
    if not np.allclose(out["fi__B-MOTIV__elite_pre_slam"], s * ta - s * tb, equal_nan=True):
        raise RuntimeError("elite_pre_slam: the per-player parts do not add up")
    log(f"  {T.name}: f19_motiv done")
    # U-254: f09_venue (leak-proof venue pace on the clock; I-072 x ace offence; the block's single column)
    ven = F09.prepare_venue(P, L)
    Q = P.assign(**ven)
    x72 = np.asarray(F09.x_i072(Q), float)
    ve = np.asarray(ven["f09_ve"], float)
    out["fp__f09_venue__f09_ve"] = ve
    out["fi__B-VENUE__f09_venue_pace_x_ace"] = x72
    out["fi__B-VENUE__f09_venue_pace_x_ace_a"] = ve * S1.ios(Q, "srfO", "ace", "a")
    out["fi__B-VENUE__f09_venue_pace_x_ace_b"] = ve * S1.ios(Q, "srfO", "ace", "b")
    out["fi__B-VENUE__x"] = np.asarray(S1.signed_block(Q, [(x72, "+")]), float)
    log(f"  {T.name}: f09_venue done")
    # U-330: event_levels.blend.history, as universe_columns.py calls it
    m0, p0 = BL.load()
    h = BL.history(m0, p0, years=(ELC.TRAIN_FROM, 2026), levels=ELC.MAIN, match_ids=P["match_id"])
    ids = pd.Index(P["match_id"].astype(str))
    for side, tag in (("A", "a"), ("B", "b")):
        g = h[h["side"] == side]
        if g["match_id"].duplicated().any():
            raise RuntimeError("blend.history: a duplicated side row")
        g = g.set_index(g["match_id"].astype(str))
        pid = g["player_id"].reindex(ids).astype(object).to_numpy()
        want = P[f"player_{tag}_id"].to_numpy()
        found = pd.notna(pid)
        if not (pid[found].astype(str) == want[found]).all():
            raise RuntimeError("blend.history: side A is not the panel's side A")
        out[f"el__low_share_{tag}"] = g["low_share"].reindex(ids).to_numpy(float)
    out["el__low_share_diff"] = out["el__low_share_a"] - out["el__low_share_b"]
    del m0, p0, h
    log(f"  {T.name}: event_levels done")
    # U-261: f12_salience (Stage B's z read from the long table's zB, see Patched)
    sal = F12.prepare_i082(P, L)
    for k in ("salL", "hasL"):
        out[f"fp__f12_salience__{k}_a"], out[f"fp__f12_salience__{k}_b"] = sal[f"{k}_a"], sal[f"{k}_b"]
    out["fi__I-082__x"] = np.asarray(sal["salL_a"], float) - np.asarray(sal["salL_b"], float)
    # U-175: build_store's seeded flag; U-177: fame
    out["pp__seeded_a"] = P["seed_a"].notna().astype(float).to_numpy()
    out["pp__seeded_b"] = P["seed_b"].notna().astype(float).to_numpy()
    fame = F14.prepare_fame(P, L)
    out["fp__f14_anchor__fame_a"], out["fp__f14_anchor__fame_b"] = fame["fame_a"], fame["fame_b"]
    log(f"  {T.name}: salience, seeded, fame done")
    # U-138 / U-307 / U-153: f24_onsite (f20's history, f23's geography, f25's indoor status)
    b11 = F24.prepare_b11(P, L)
    for k in ("on_n", "nov"):
        out[f"fp__f17_info__bd11_{k}_a"], out[f"fp__f17_info__bd11_{k}_b"] = b11[f"bd11_{k}_a"], b11[f"bd11_{k}_b"]
    out["fi__B11__bd11_on"] = np.asarray(F24.b11_members(P.assign(**b11))["I-051 On"], float)
    # U-143 / U-322: f28_state's PastFat on f20's history; the block is BOD-C1 alone (combine_state)
    Hh = F20.history(P, L)
    pfa, pfb = F20.at_model(P, Hh, F28.past_fat(Hh))
    out["fp__f28_state__bdst_pastfat_a"], out["fp__f28_state__bdst_pastfat_b"] = pfa, pfb
    out["fi__B-STATE__x"] = np.asarray(F20.block(P, [(pfa - pfb, +1)]), float)
    # U-148: f23_arrival's Trav
    b10 = F23.prepare_b10(P, L)
    out["fp__f23_arrival__bd10_trav_a"], out["fp__f23_arrival__bd10_trav_b"] = b10["bd10_trav_a"], b10["bd10_trav_b"]
    log(f"  {T.name}: f20 family done")
    for stem in PAIRS:
        a, b = np.asarray(out[f"{stem}_a"], float), np.asarray(out[f"{stem}_b"], float)
        out[f"{stem}_a"], out[f"{stem}_b"] = a, b
        out[f"{stem}_a-b"] = a - b
    clear_caches()
    return {k: np.asarray(v, float) for k, v in out.items()}


def run_variant(T: Tables, reuse: bool = False) -> tuple[pd.DataFrame, dict]:
    """Build a variant's values (store names) at its population's matches; cached in variants/<name>.parquet."""
    path = VARIANT_DIR / f"{T.name}.parquet"
    meta_path = path.with_suffix(".json")
    if reuse and path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("tables") == asdict(T):
            log(f"{T.name}: reused {path.name}")
            return pd.read_parquet(path), meta
    t0 = time.time()
    log(f"{T.name}: {T.desc}")
    with Patched(T):
        L, linfo = long_table(T)
        keys = keys_frame(T.frame)
        P = panel(T, keys)
        log(f"{T.name}: long table {len(L):,} rows, panel {len(P):,} matches")
        vals = build(T, L, P)
    df = pd.DataFrame({"match_id": P["match_id"].astype(str).to_numpy(), **vals})
    early = (pd.to_datetime(P["tournament_date"]) < SEALED).to_numpy()      # counts never include Look B's matches
    meta = {"tables": asdict(T), "long_table": linfo, "counted": "panel matches dated before 29 Jul 2026",
            "panel_rows": int(early.sum()),
            "panel_without_clock": int((~np.isfinite(P["es"].to_numpy(float)) & early).sum()),
            "panel_without_sides": int(((P["player_a_id"].isin(["nan", "None"]) |
                                         P["player_b_id"].isin(["nan", "None"])).to_numpy() & early).sum()),
            "seconds": round(time.time() - t0, 1)}
    if T.name == "V1":                      # the instance's IOS must be the frame's own inputs, bit for bit
        f = pd.read_parquet(H.FRAME, columns=["match_id", "in_iosO_ace"])
        f["match_id"] = f["match_id"].astype(str)
        d = (P["ios_srfO_ace_a"] - P["ios_srfO_ace_b"]).to_numpy(float) - \
            P[["match_id"]].merge(f, on="match_id", how="left")["in_iosO_ace"].to_numpy(float)
        d = d[early]
        meta["ios_reproduces_frame_iosO_ace_max_abs_diff"] = float(np.nanmax(np.abs(d)))
        meta["ios_rows_compared"] = int(np.isfinite(d).sum())
    VARIANT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    meta_path.write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    del L, P
    gc.collect()
    log(f"{T.name}: done in {meta['seconds']}s")
    return df, meta


# ------------------------------------------------------------------------------------------------------ verification

VERIFY_COLS = [  # (store column, rebuilt column): every store column this build reproduces
    "fp__f19_motiv__post_a", "fp__f19_motiv__post_b", "fi__B-MOTIV__post_slam", "fp__f19_motiv__nslam_days",
    "fi__B-MOTIV__elite_pre_slam", "fp__f09_venue__f09_ve", "fi__B-VENUE__f09_venue_pace_x_ace", "fi__B-VENUE__x",
    "el__low_share_a", "el__low_share_b", "el__low_share_diff", "fp__f12_salience__salL_a", "fp__f12_salience__salL_b",
    "fp__f12_salience__hasL_a", "fp__f12_salience__hasL_b", "fi__I-082__x", "pp__seeded_a", "pp__seeded_b",
    "fp__f14_anchor__fame_a", "fp__f14_anchor__fame_b", "fp__f17_info__bd11_on_n_a", "fp__f17_info__bd11_on_n_b",
    "fi__B11__bd11_on", "fp__f28_state__bdst_pastfat_a", "fp__f28_state__bdst_pastfat_b", "fi__B-STATE__x",
    "fp__f17_info__bd11_nov_a", "fp__f17_info__bd11_nov_b", "fp__f23_arrival__bd10_trav_a",
    "fp__f23_arrival__bd10_trav_b"]


def equal(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    with np.errstate(invalid="ignore"):
        return (np.isfinite(a) & np.isfinite(b) & (np.abs(a - b) <= TOL)) | (np.isnan(a) & np.isnan(b))


def corr(a: np.ndarray, b: np.ndarray) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 3 or np.std(a[ok]) == 0 or np.std(b[ok]) == 0:
        return np.nan
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def verify(var: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Each rebuilt column against the store on the matches the store and the current frame both hold, seasons <= 2024
    (outcome-free). Every difference of V1 from the store is attributed to the steps that move it, along the chain
    store -> V0 (code: must be none) -> Vk (the clock) -> Vs (the 8 Oct Stage 0, its id fixes and box-score
    corrections, and the frame's scaling rows) -> Vz (the instance's surface IOS; Stage B rebuilt on the 8 Oct tables,
    layer off) -> V1 (the level layer inside Stage B). A row moved by several steps is counted under each."""
    import pyarrow.parquet as pq
    keys = keys_frame("current")
    names = set(pq.read_schema(STORE).names)
    cols = [c for c in VERIFY_COLS if c in names]
    store = pd.read_parquet(STORE, columns=["match_id"] + cols)
    store["match_id"] = store["match_id"].astype(str)
    common = keys[(keys["season"] <= 2024) & keys["match_id"].isin(set(store["match_id"]))].reset_index(drop=True)
    ids = common["match_id"]

    def at(df: pd.DataFrame, c: str) -> np.ndarray:
        s = df.set_index(df["match_id"].astype(str))[c]
        return s.reindex(ids).to_numpy(float)
    rows, by_season = [], []
    tour = common["tour"].to_numpy()
    season = common["season"].to_numpy()
    for c in cols:
        st = at(store, c)
        v = {k: at(var[k], c) for k in ("V0", "Vk", "Vs", "Vz", "V1")}
        d_total = ~equal(v["V1"], st)
        d_code = ~equal(v["V0"], st)
        d_clock = ~equal(v["Vk"], v["V0"])
        d_s0 = ~equal(v["Vs"], v["Vk"])
        d_reb = ~equal(v["Vz"], v["Vs"])
        d_lay = ~equal(v["V1"], v["Vz"])
        d_inst = d_reb | d_lay
        for t in ("both", "atp", "wta"):
            m = np.ones(len(ids), bool) if t == "both" else tour == t
            a, b = v["V1"][m], st[m]
            fin = np.isfinite(a) & np.isfinite(b)
            dd = np.abs(a[fin] - b[fin])
            rows.append({
                "column": c, "rebuilt": f"rb__{c}", "tour": t, "rows_common_le_2024": int(m.sum()),
                "rows_both_finite": int(fin.sum()),
                "share_equal_1e-9": float(np.mean(equal(a, b))) if m.any() else np.nan,
                "share_equal_1e-9_finite": float(np.mean(dd <= TOL)) if fin.any() else np.nan,
                "corr": corr(a, b), "mean_abs_diff": float(dd.mean()) if fin.any() else np.nan,
                "max_abs_diff": float(dd.max()) if fin.any() else np.nan,
                "rows_nan_store_only": int((np.isnan(b) & np.isfinite(a)).sum()),
                "rows_nan_rebuilt_only": int((np.isnan(a) & np.isfinite(b)).sum()),
                "rows_differ": int(d_total[m].sum()),
                "v0_share_equal_1e-9": float(np.mean(~d_code[m])), "v0_corr": corr(v["V0"][m], b),
                "rows_differ_code_v0": int(d_code[m].sum()),
                "of_differing_moved_by_clock": int((d_total & d_clock)[m].sum()),
                "of_differing_moved_by_stage0_frame": int((d_total & d_s0)[m].sum()),
                "of_differing_moved_by_rebuilt_ios_stageB": int((d_total & d_reb)[m].sum()),
                "of_differing_moved_by_level_layer": int((d_total & d_lay)[m].sum()),
                "of_differing_unattributed": int((d_total & ~d_clock & ~d_s0 & ~d_inst & ~d_code)[m].sum()),
                "corr_vs_v0": corr(a, v["V0"][m]), "corr_store_vs_vz": corr(v["Vz"][m], b),
            })
        for t in ("atp", "wta"):
            for y in sorted(set(season[tour == t])):
                m = (tour == t) & (season == y)
                by_season.append({"column": c, "tour": t, "season": int(y), "rows": int(m.sum()),
                                  "differ": int(d_total[m].sum()), "code_v0": int(d_code[m].sum()),
                                  "clock": int((d_total & d_clock)[m].sum()),
                                  "stage0_frame": int((d_total & d_s0)[m].sum()),
                                  "rebuilt_ios_stageB": int((d_total & d_reb)[m].sum()),
                                  "level_layer": int((d_total & d_lay)[m].sum())})
    return pd.DataFrame(rows), pd.DataFrame(by_season)


def sensitivity(v1: pd.DataFrame, v2: pd.DataFrame) -> pd.DataFrame:
    """V2 (the instance's own Stage 0 and clock) against V1, outcome-free, matches before 29 Jul 2026 only."""
    keys = keys_frame("current")
    keys = keys[pd.to_datetime(keys["tournament_date"]) < SEALED].reset_index(drop=True)
    ids = keys["match_id"]
    a_df, b_df = v1.set_index("match_id").reindex(ids), v2.set_index("match_id").reindex(ids)
    period = np.where(keys["season"] <= 2024, "2013-2024", keys["season"].astype(str))
    rows = []
    for c in [c for c in v1.columns if c != "match_id"]:
        a, b = a_df[c].to_numpy(float), b_df[c].to_numpy(float)
        for t in ("atp", "wta"):
            for per in ("2013-2024", "2025", "2026"):
                m = (keys["tour"].to_numpy() == t) & (period == per)
                if not m.any():
                    continue
                rows.append({"column": f"rb__{c}", "tour": t, "period": per + (" (to 28 Jul)" if per == "2026" else ""),
                             "rows": int(m.sum()), "share_equal_1e-9": float(np.mean(equal(a[m], b[m]))),
                             "rows_differ": int((~equal(a[m], b[m])).sum()), "corr": corr(a[m], b[m])})
    return pd.DataFrame(rows)


def coverage(v1: pd.DataFrame) -> dict:
    """Outcome-free: the share of frame matches (debut seasons out, as the harness) where each rebuilt column is
    present, by tour and season; 2026 only before 29 Jul 2026."""
    keys = keys_frame("current")
    keys = keys[(pd.to_datetime(keys["tournament_date"]) < SEALED) & ~keys["debut_season"].astype(bool)]
    v = v1.set_index("match_id").reindex(keys["match_id"])
    out = {"population": "current frame, debut seasons out, tournament date before 29 Jul 2026 (2026 = Look A part)",
           "rows": {}, "columns": {}}
    for t in ("atp", "wta"):
        for y in sorted(keys["season"].unique()):
            m = ((keys["tour"] == t) & (keys["season"] == y)).to_numpy()
            out["rows"][f"{t}|{int(y)}"] = int(m.sum())
    for c in [c for c in v1.columns if c != "match_id"]:
        x = v[c].to_numpy(float)
        cov = {}
        for t in ("atp", "wta"):
            for y in sorted(keys["season"].unique()):
                m = ((keys["tour"] == t) & (keys["season"] == y)).to_numpy()
                if m.any():
                    cov[f"{t}|{int(y)}"] = round(float(np.isfinite(x[m]).mean()), 4)
            for lab, (lo, hi) in (("2013-2024", (2013, 2024)), ("2025-2026", (2025, 2026))):
                m = ((keys["tour"] == t) & keys["season"].between(lo, hi)).to_numpy()
                cov[f"{t}|{lab}"] = round(float(np.isfinite(x[m]).mean()), 4)
        out["columns"][f"rb__{c}"] = cov
    return out


# ------------------------------------------------------------------------------------------------------ probes

def to_long(P: pd.DataFrame, parts: dict[str, tuple]) -> pd.DataFrame:
    """Per-(match, player) rows from a panel's side-A / side-B values."""
    a = pd.DataFrame({"match_id": P["match_id"].astype(str).to_numpy(),
                      "player_id": P["player_a_id"].astype(str).to_numpy(),
                      **{k: np.asarray(v[0], float) for k, v in parts.items()}})
    b = pd.DataFrame({"match_id": P["match_id"].astype(str).to_numpy(),
                      "player_id": P["player_b_id"].astype(str).to_numpy(),
                      **{k: np.asarray(v[1], float) for k, v in parts.items()}})
    return pd.concat([a, b], ignore_index=True).drop_duplicates(["match_id", "player_id"])


def probe_hist(Pall: pd.DataFrame):
    """The mkt_common.hist family: post-Slam, the elite pre-Slam parts, fame, salience; and two leaky controls (the
    current match's own points played, the next match's)."""
    def fn(Ls: pd.DataFrame) -> pd.DataFrame:
        clear_caches()
        mot = F19.prepare_motiv(Pall, Ls)
        Q = Pall.assign(**mot)
        s = F19.pre_slam(Q)
        ra, rb = M.pair(Q, "rank")
        ta = np.where(np.isfinite(ra), ra <= F19.TOP, False).astype(float)
        tb = np.where(np.isfinite(rb), rb <= F19.TOP, False).astype(float)
        fame = F14.prepare_fame(Pall, Ls)
        sal = F12.prepare_i082(Pall, Ls)
        Hh = M.hist(Ls, Pall)
        pts = Hh["tpw_d"].to_numpy(float)
        own = M.at_model(Hh, Pall, pts)
        nxt = M.at_model(Hh, Pall, pd.Series(pts).groupby(Hh["pc"].to_numpy()).shift(-1).to_numpy(float))
        out = to_long(Pall, {"post": (mot["post_a"], mot["post_b"]), "elite": (s * ta, s * tb),
                             "fame": (fame["fame_a"], fame["fame_b"]), "salL": (sal["salL_a"], sal["salL_b"]),
                             "hasL": (sal["hasL_a"], sal["hasL_b"]), "leak_own_points": own,
                             "leak_next_points": nxt})
        clear_caches()
        return out
    return fn, ["post", "elite", "fame", "salL", "hasL"], ["leak_own_points", "leak_next_points"]


def probe_f20(Pall: pd.DataFrame):
    """The f20_fatigue.history family: matches here, novelty, travel, past fatigue; leaky controls: the current match's
    own load (its minutes) and the next match's."""
    def fn(Ls: pd.DataFrame) -> pd.DataFrame:
        clear_caches()
        b11 = F24.prepare_b11(Pall, Ls)
        Hh = F20.history(Pall, Ls)
        pf = F20.at_model(Pall, Hh, F28.past_fat(Hh))
        b10 = F23.prepare_b10(Pall, Ls)
        load = Hh["load"].to_numpy(float)
        own = F20.at_model(Pall, Hh, load)
        nxt = F20.at_model(Pall, Hh, pd.Series(load).groupby(Hh["pid"].to_numpy()).shift(-1).to_numpy(float))
        out = to_long(Pall, {"on_n": (b11["bd11_on_n_a"], b11["bd11_on_n_b"]),
                             "nov": (b11["bd11_nov_a"], b11["bd11_nov_b"]),
                             "trav": (b10["bd10_trav_a"], b10["bd10_trav_b"]), "pastfat": pf,
                             "leak_own_load": own, "leak_next_load": nxt})
        clear_caches()
        return out
    return fn, ["on_n", "nov", "trav", "pastfat"], ["leak_own_load", "leak_next_load"]


def probe_u330(T: Tables):
    """U-330: blend.history with each Stage 0 player row's status and won taken from the (scrambled) long table; every
    pool match 2010-2026 queried (the history itself is every played match, as always)."""
    with Patched(T):
        m0, p0 = BL.load()
    p0["match_id"], p0["player_id"] = p0["match_id"].astype(str), p0["player_id"].astype(str)
    key0 = pd.MultiIndex.from_frame(p0[["match_id", "player_id"]])

    def fn(Ls: pd.DataFrame) -> pd.DataFrame:
        lk = Ls.set_index(["match_id", "player_id"])
        p2 = p0.copy()
        p2["status"] = lk["status"].reindex(key0).to_numpy()
        p2["won"] = lk["won"].reindex(key0).astype(object).to_numpy()
        p2["won"] = p2["won"].astype(bool)
        h = BL.history(m0, p2, years=(2010, 2026), levels=BL.POOL)
        h = h.assign(match_id=h["match_id"].astype(str), player_id=h["player_id"].astype(str))
        return h[["match_id", "player_id", "low_share"]].drop_duplicates(["match_id", "player_id"])
    return fn, ["low_share"], []


def probe_venue_scramble(Pall: pd.DataFrame):
    """The venue pace at every match, for the scramble probe: the future rows must not move; own rows may (a match that
    finished before the target started belongs to the pace whether or not it started after the cut)."""
    ms = int(Pall["season"].max())

    def fn(Ls: pd.DataFrame) -> pd.DataFrame:
        R = F09.serve_rows(S1.cut_history(Ls, Pall), ms)
        v = F09.venue_state(Pall, R)
        R2 = R.assign(lf=R["lf"].to_numpy(float) - 10.0)          # leaky: results counted 9 days early
        vl = F09.venue_state(Pall, R2)
        return to_long(Pall, {"venue_pace": (v, v), "leak_release_9_days_early": (vl, vl)})
    return fn, ["venue_pace"], ["leak_release_9_days_early"]


class ContentCache:
    """A builder's output keyed on the table's content (the bytes of columns every scramble or reversal moves), so
    separate probe calls that perturb identically (the harness seeds its generator per call) share one build."""

    def __init__(self, fn, cols=("won", "tpw_d", "minutes", "ace", "spw_n")):
        self.fn, self.cols, self.store = fn, cols, {}

    def __call__(self, Ls: pd.DataFrame):
        h = hashlib.sha256(str(len(Ls)).encode())
        for c in self.cols:
            if c in Ls.columns:
                h.update(np.ascontiguousarray(Ls[c].to_numpy(dtype=float, na_value=np.nan)).tobytes())
        k = h.hexdigest()
        if k not in self.store:
            self.store[k] = self.fn(Ls)
        return self.store[k]


class Recorder:
    """Wraps a cached builder for screen.timing_probe, keeping each call's output: the base build first, then one per
    cut in order (the harness's call order), for the per-column breakdown."""

    def __init__(self, cache: ContentCache, cols: list[str]):
        self.cache, self.cols, self.calls = cache, cols, []

    def __call__(self, Ls: pd.DataFrame) -> pd.DataFrame:
        out = self.cache(Ls)[["match_id", "player_id"] + self.cols]
        self.calls.append(out)
        return out


def breakdown(L: pd.DataFrame, calls: list, col: str, cuts) -> dict:
    """Per cut, the harness's two row sets (future: lf + 1 <= cut; own: each player's first row from the cut whose
    earlier rows are untouched, the harness's selection), with how many carry a value and how they moved: the value
    changed (exactly, as the harness counts; and by more than 1e-9 relative, with the largest change), was lost
    (finite -> missing: the row left the builder's population) or gained. Builders that exclude the current row as a
    cumulative sum minus the row's own term (mkt_common.decayed, f28_state.past_fat) move by rounding (about 1e-16
    relative) when the row's own term is scrambled: an exact change, not a leak."""
    keys = pd.MultiIndex.from_frame(L[["match_id", "player_id"]].astype(str))
    base = calls[0].set_index(["match_id", "player_id"])[col].reindex(keys).to_numpy(float)
    es, lf = L["es"].to_numpy(float), L["lf"].to_numpy(float)
    out = {}
    for j, cut in enumerate(cuts):
        new = calls[j + 1].set_index(["match_id", "player_id"])[col].reindex(keys).to_numpy(float)
        c_day = (pd.Timestamp(cut) - pd.Timestamp("1970-01-01")).days
        after = (es >= c_day) | ~np.isfinite(es)
        A = pd.DataFrame({"player_id": L["player_id"].to_numpy(), "k": L["k"].to_numpy(), "after": after})
        first_after = A[A["after"]].groupby("player_id")["k"].min()
        last_before = A[~A["after"]].groupby("player_id")["k"].max()
        okp = first_after.index[(first_after > last_before.reindex(first_after.index).fillna(-1)).to_numpy()]
        fa = first_after.loc[okp]
        own = L.set_index(["player_id", "k"]).index.isin(pd.MultiIndex.from_arrays([fa.index, fa.to_numpy()]))
        rec = {}
        for lab, m in (("future", lf + 1 <= c_day), ("own", own)):
            a, b = base[m], new[m]
            fa_, fb_ = np.isfinite(a), np.isfinite(b)
            both = fa_ & fb_
            d = np.abs(a[both] - b[both])
            big = d > 1e-9 * np.maximum(1.0, np.abs(a[both]))
            rec[lab] = {"rows": int(m.sum()), "with_value": int(fa_.sum()),
                        "value_changed": int((d > 0).sum()), "value_changed_beyond_1e-9": int(big.sum()),
                        "max_abs_change": float(d.max()) if d.size else 0.0,
                        "lost_value": int((fa_ & ~fb_).sum()), "gained_value": int((~fa_ & fb_).sum())}
        out[cut] = rec
    return out


def run_probes(T: Tables) -> dict:
    cuts = ("2016-06-01", "2019-03-01", "2022-09-01")
    out: dict = {"tables": T.name, "cuts": list(cuts),
                 "how": "screen.timing_probe, run on a panel of every match of the long table (so every history row "
                        "carries a value): results and box scores (Stage B's z included, as the long table's zB) of "
                        "the matches that may start on or after the cut are scrambled; for an own-sequence builder the "
                        "rows that surely finished before the cut (future) and each player's first scrambled row "
                        "(own) must not move; the leaky controls must. `harness` is the harness's own count (all the "
                        "group's real columns jointly; NaN = NaN counts as unchanged), `breakdown` the same rows per "
                        "column: the value changed, lost (the row left the population) or gained"}
    with Patched(T):
        L, _ = long_table(T)
        # the probes never touch Look B: the history is cut before 29 Jul 2026 (the cuts are 2016-2022, and every
        # builder reads strictly earlier rows, so dropping later rows changes no compared value)
        L = L[(pd.to_datetime(L["tournament_date"]) < SEALED).to_numpy()].reset_index(drop=True)
        Pall = panel_all(T, L)
    out["history"] = "long table rows dated before 29 Jul 2026"
    out["panel_all_matches"] = int(len(Pall))
    groups = {"hist": probe_hist(Pall), "f20": probe_f20(Pall), "u330": probe_u330(T),
              "venue_scramble": probe_venue_scramble(Pall)}
    for name, (fn, cols, leaks) in groups.items():
        t0 = time.time()
        with Patched(T):
            cache = ContentCache(fn)
            rec, rec_l = Recorder(cache, cols), Recorder(cache, leaks)
            res = {"harness": H.timing_probe(rec, L, cols, cuts=cuts)}
            if leaks:
                res["harness_leaky_controls"] = H.timing_probe(rec_l, L, leaks, cuts=cuts)
            res["breakdown"] = {c: breakdown(L, rec.calls, c, cuts) for c in cols}
            res["breakdown"].update({c: breakdown(L, rec_l.calls, c, cuts) for c in leaks})
            res["builds"] = len(cache.store)
            res["seconds"] = round(time.time() - t0, 1)
        out[name] = res
        del cache, rec, rec_l
        gc.collect()
        h = res["harness"]
        log(f"probe {name}: {res['seconds']}s, {res['builds']} builds; future changed "
            f"{[v['future_rows_changed'] for v in h.values()]}, own changed {[v['own_rows_changed'] for v in h.values()]}"
            + (f"; leaky future {[v['future_rows_changed'] for v in res['harness_leaky_controls'].values()]}, own "
               f"{[v['own_rows_changed'] for v in res['harness_leaky_controls'].values()]}" if leaks else ""))
    # the venue pace: f01's probe-equivalent as f09_venue.probe() runs it (results after each cut reversed between the
    # two players; every frame match with es <= cut must keep its value exactly), with a leaky control that must move
    t0 = time.time()
    with Patched(T):
        keys = keys_frame("current")
        P = panel(T, keys[(pd.to_datetime(keys["tournament_date"]) < SEALED).to_numpy()].reset_index(drop=True))
        Lc = S1.cut_history(L, P)
        ms = int(P["season"].max())

        def both(LL):
            R = F09.serve_rows(LL, ms)
            return F09.venue_state(P, R), F09.venue_state(P, R.assign(lf=R["lf"].to_numpy(float) - 10.0))
        vc = ContentCache(both, cols=("won", "ace", "svpt", "spw_n", "spw_d"))
        out["venue_probe_equivalent"] = {
            "how": "f01_structure_lib.probe_check: every match that surely started after the cut has its result and "
                   "box score reversed between its two players; no frame match starting by the cut may move",
            "pace": S1.probe_check(lambda LL: vc(LL)[0], Lc, P, F09.STAT_COLS),
            "leaky_release_9_days_early": S1.probe_check(lambda LL: vc(LL)[1], Lc, P, F09.STAT_COLS),
            "builds": len(vc.store), "seconds": round(time.time() - t0, 1)}
    log(f"venue probe-equivalent: passed {out['venue_probe_equivalent']['pace']['passed']}; the leaky control passed "
        f"(must be False) {out['venue_probe_equivalent']['leaky_release_9_days_early']['passed']}")
    del L, Pall, vc
    gc.collect()
    return out


# ------------------------------------------------------------------------------------------------------ screens

CANDIDATES = [  # (screened name, kind, the store / pool-scan names it rebuilds, catalogue)
    ("rb__fi__B-MOTIV__post_slam", "diff", ["fi__B-MOTIV__post_slam", "fp__f19_motiv__post_a-b"], "U-284 / U-162"),
    ("rb__fi__B-MOTIV__elite_pre_slam", "diff", ["fi__B-MOTIV__elite_pre_slam"], "U-283"),
    ("rb__fi__B-VENUE__x", "diff", ["fi__B-VENUE__x"], "U-254"),
    ("rb__fp__f09_venue__f09_ve", "context", ["fp__f09_venue__f09_ve"], "U-192 (B-VENUE's venue pace)"),
    ("rb__el__low_share_diff", "diff", ["el__low_share_diff", "el__low_share_a-b"], "U-330"),
    ("rb__fi__I-082__x", "diff", ["fi__I-082__x", "fp__f12_salience__salL_a-b"], "U-261"),
    ("rb__fp__f12_salience__hasL_a-b", "diff", ["fp__f12_salience__hasL_a-b"], "U-261 (has low-visibility form)"),
    ("rb__pp__seeded_a-b", "diff", ["pp__seeded_a-b"], "U-175"),
    ("rb__fp__f14_anchor__fame_a-b", "diff", ["fp__f14_anchor__fame_a-b"], "U-177"),
    ("rb__fp__f17_info__bd11_on_n_a-b", "diff", ["fp__f17_info__bd11_on_n_a-b"], "U-138"),
    ("rb__fi__B11__bd11_on", "diff", ["fi__B11__bd11_on"], "U-307"),
    ("rb__fp__f28_state__bdst_pastfat_a-b", "diff", ["fp__f28_state__bdst_pastfat_a-b"], "U-143"),
    ("rb__fi__B-STATE__x", "diff", ["fi__B-STATE__x"], "U-322"),
    ("rb__fp__f17_info__bd11_nov_a-b", "diff", ["fp__f17_info__bd11_nov_a-b"], "U-153"),
    ("rb__fp__f23_arrival__bd10_trav_a-b", "diff", ["fp__f23_arrival__bd10_trav_a-b"], "U-148"),
]
# added after the first screen had been seen (salience moved for men): the same statistic with Stage B rebuilt on the
# 8 Oct tables WITHOUT the level layer (variant Vz), to show which part of the move the layer makes; never registered
EXTRA = [("rb__fi__I-082__x__layer_off", "diff", ["fi__I-082__x", "fp__f12_salience__salL_a-b"],
          "U-261, Stage B without the level layer (variant Vz; descriptive, not registered)", "Vz", "fi__I-082__x")]


def screen_safe(frame: pd.DataFrame, x, name: str, kind: str, curv: bool, lenses=("close", "model", "move")):
    """screen.screen; where the move lens's least squares is singular, the same lenses with the move lens skipped."""
    try:
        return H.screen(frame, x, name, kind, lenses=lenses, curv=curv)
    except np.linalg.LinAlgError:
        out = H.screen(frame, x, name, kind, lenses=tuple(l for l in lenses if l != "move"), curv=curv)
        return out


def run_screens(values: pd.DataFrame, var: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    frame = H.load_frame()                      # seasons <= 2024 (filtered in the read, asserted), debut out
    if frame["season"].max() > 2024 or frame["tournament_date"].max() >= H.DISCOVERY_END:
        raise RuntimeError("an outcome from 2025 on is in the screened frame")
    ids = frame["match_id"].astype(str)
    v = values.set_index("match_id").reindex(ids)
    store_ids = set(pd.read_parquet(STORE, columns=["match_id"])["match_id"].astype(str))
    in_store = ids.isin(store_ids).to_numpy()
    parts, orth_coef = [], {}
    todo = [(name, kind, v[name].to_numpy(float)) for name, kind, _, _ in CANDIDATES]
    todo += [(name, kind, var[vn].set_index("match_id").reindex(ids)[col].to_numpy(float))
             for name, kind, _, _, vn, col in EXTRA]
    for name, kind, x in todo:
        for curv in (False, True):
            lens = ("close", "model", "move") if not curv else ("close",)
            r = screen_safe(frame, x, name, kind, curv, lens)
            r["encoding"] = "raw"
            parts.append(r)
            if kind == "diff":
                xo, coef = H.orthogonal_part(frame, x)
                orth_coef[name] = coef
                ro = screen_safe(frame, xo, name + "__orth", kind, curv, lens)
                ro["encoding"] = "orth"
                parts.append(ro)
        xs = np.where(in_store, x, np.nan)      # the same values on the store's rows only (no men's 2018)
        rs = H.close_lens(frame, xs, name + "__store_rows", kind)
        rs["encoding"] = "raw_store_rows"
        rs["r2_inputs"] = np.nan
        parts.append(rs)
        log(f"  screened {name}")
    long = pd.concat(parts, ignore_index=True)
    long["candidate"] = long["name"].str.replace(r"__(orth|store_rows)$", "", regex=True)
    return long, frame, orth_coef


def summarize(long: pd.DataFrame) -> pd.DataFrame:
    def summ(enc: str, lens: str, suffix: str, keep: list[str]) -> pd.DataFrame:
        s = H.summarize(long[long["encoding"] == enc], lens=lens)
        s["candidate"] = s["name"].str.replace(r"__(orth|store_rows)$", "", regex=True)
        s = s[["candidate", "tour"] + keep]
        return s.rename(columns={k: f"{k}{suffix}" for k in keep})
    era = [f"z_{e}" for e in H.ERAS]
    base = ["beta_pool", "z_pool", "eras_same_sign", "eras_abs_z_ge_2", "present_2013_24"] + era
    out = summ("raw", "close", "", base + ["z_model_2020_24", "z_move_2018_24", "r2_inputs", "q_pool"])
    out = out.merge(summ("raw", "close+curv", "_curv", ["beta_pool", "z_pool", "eras_same_sign"] + era),
                    on=["candidate", "tour"], how="left")
    out = out.merge(summ("orth", "close", "_orth", ["beta_pool", "z_pool", "eras_same_sign"] + era +
                         ["z_model_2020_24", "z_move_2018_24", "q_pool"]), on=["candidate", "tour"], how="left")
    out = out.merge(summ("orth", "close+curv", "_orth_curv", ["beta_pool", "z_pool", "eras_same_sign"]),
                    on=["candidate", "tour"], how="left")
    out = out.merge(summ("raw_store_rows", "close", "_store_rows", ["z_pool", "eras_same_sign", "present_2013_24"]),
                    on=["candidate", "tour"], how="left")
    meta = pd.DataFrame([{"candidate": n, "kind": k, "catalogue": cat, "store_names": "; ".join(names)}
                         for n, k, names, cat in CANDIDATES] +
                        [{"candidate": n, "kind": k, "catalogue": cat, "store_names": "; ".join(names)}
                         for n, k, names, cat, _, _ in EXTRA])
    out = meta.merge(out, on="candidate", how="right")
    # the pool statistician's readings of the store column (its first name), same tour
    pool = pd.read_csv(POOL_SUMMARY)
    keep = {"z_pool": "pool_z_pool", "eras_same_sign": "pool_eras_same_sign", "z_pool_orth": "pool_z_pool_orth",
            "eras_same_sign_orth": "pool_eras_same_sign_orth", "z_model_2020_24": "pool_z_model_2020_24",
            "z_move_2018_24": "pool_z_move_2018_24", "r2_inputs": "pool_r2_inputs", "present_2013_24": "pool_present",
            "z_2013-16": "pool_z_2013-16", "z_2017-19": "pool_z_2017-19", "z_2020-22": "pool_z_2020-22",
            "z_2023-24": "pool_z_2023-24"}
    pool = pool[["candidate", "tour"] + list(keep)].rename(columns=keep | {"candidate": "pool_candidate"})
    out["pool_candidate"] = out["store_names"].str.split("; ").str[0]
    out = out.merge(pool, on=["pool_candidate", "tour"], how="left")
    out["z_pool_minus_pool"] = out["z_pool"] - out["pool_z_pool"]
    out["z_pool_orth_minus_pool"] = out["z_pool_orth"] - out["pool_z_pool_orth"]
    order = {n: i for i, (n, *_) in enumerate(CANDIDATES + EXTRA)}
    tour_order = {"both": 0, "atp": 1, "wta": 2}
    out = out.sort_values(["candidate", "tour"], key=lambda s: s.map(order) if s.name == "candidate"
                          else s.map(tour_order)).reset_index(drop=True)
    return out


# ------------------------------------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reuse-variants", action="store_true", help="development only")
    ap.add_argument("--skip-probes", action="store_true", help="development only")
    args = ap.parse_args()
    warnings.simplefilter("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    info: dict = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                  "code": file_info(Path(__file__)), "variants": {}, "tables": {k: asdict(v) for k, v in SPEC.items()}}
    # 1. the variants (V1 is the registered build)
    var, meta = {}, {}
    for name in ("V1", "V0", "Vk", "Vs", "Vz", "V2"):
        var[name], meta[name] = run_variant(SPEC[name], reuse=args.reuse_variants)
    info["variants"] = meta
    v1 = var["V1"]
    values = v1.rename(columns={c: f"rb__{c}" for c in v1.columns if c != "match_id"})
    if set(values.columns) & {"a_won", "won", "y"}:
        raise RuntimeError("a result column in the values")
    keys = keys_frame("current")
    if len(values) != len(keys) or not (values["match_id"].to_numpy() == keys["match_id"].to_numpy()).all():
        raise RuntimeError("the values are not one row per current-frame match, in the frame's order")
    values.to_parquet(OUT / "values.parquet", index=False)
    info["values"] = {"rows": int(len(values)), "columns": int(values.shape[1] - 1), "sha256": sha256(OUT / "values.parquet")}
    log(f"values.parquet: {values.shape}")
    # 2. verification, sensitivity, coverage (outcome-free)
    ver, ver_season = verify(var)
    ver.to_csv(OUT / "verify.csv", index=False)
    ver_season.to_csv(OUT / "verify_by_season.csv", index=False)
    sens = sensitivity(var["V1"], var["V2"])
    sens.to_csv(OUT / "sensitivity.csv", index=False)
    cov = coverage(v1)
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")
    log("verification, sensitivity, coverage written")
    # 3. probes
    if not args.skip_probes:
        pr = run_probes(SPEC["V1"])
        (OUT / "probes.json").write_text(json.dumps(pr, indent=1, default=str), encoding="utf-8")
        log("probes.json written")
    # 4. screens (outcomes <= 2024 through the harness only)
    long, frame, orth_coef = run_screens(values, var)
    long.to_csv(OUT / "long.csv", index=False)
    summ = summarize(long)
    summ.to_csv(OUT / "summary.csv", index=False)
    (OUT / "orth_coef.json").write_text(json.dumps(orth_coef), encoding="utf-8")
    info["screen"] = {"frame_rows": int(len(frame)), "last_date": str(frame["tournament_date"].max().date()),
                      "max_season": int(frame["season"].max()), "candidates": len(CANDIDATES)}
    info["inputs"] = {name: file_info(Path(p)) for name, p in
                      {"stage0_matches": SPEC["V1"].stage0_m, "stage0_players": SPEC["V1"].stage0_p,
                       "timing": SPEC["V1"].timing, "stage1_odds": SPEC["V1"].odds, "frame": H.FRAME,
                       "store": STORE, "pool_summary": POOL_SUMMARY, "repo_surface_ios": REPO["ios"],
                       "repo_stageB": REPO["stageb"], "instance_ios_extract": INSTANCE["ios"]["extract"],
                       "instance_stageB_extract": INSTANCE["stageb"]["extract"],
                       "layer_off_stageB_extract": INSTANCE["stageb_off"]["extract"],
                       "old_stage0_matches": SPEC["V0"].stage0_m, "old_timing": SPEC["V0"].timing,
                       "instance_stage0_matches": SPEC["V2"].stage0_m, "instance_timing": SPEC["V2"].timing}.items()
                      if Path(p).exists()}
    info["seconds"] = round(time.time() - T0, 1)
    (OUT / "build.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    log(f"done in {info['seconds']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
