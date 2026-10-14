"""The arms of the lower-level-evidence system (role C1): their layer configs, the reference inputs every arm reads, and
the build of an arm through the decided chain in a patched sandbox (system_sandbox.py).

    --prepare            the reference inputs, written once and hashed (no outcome is read):
                           arms/strength/reference_elo.parquet   the reference build's pre-match overall Elo per match
                                                                 (Stage 1 on the frozen tables, retirements counted;
                                                                 from the first run's sandbox, read-only), checked
                                                                 against the frozen frame's elo_overall
                           arms/constants/stageB_adj_summary_reference.json   Stage B's tuned constants as the
                                                                 reference build chose them (checked against the frozen
                                                                 build's log), for the pin
                           arms/constants/reference_constants.json  Stage 1's, the offset's and Stage 3's constants
                                                                 (frozen chain outputs and logs), for the constants gate
    --config ARM         writes arms/<ARM>/layer_config.json (a gated arm's comes from the frozen folder only)
    --write-configs      every arm's config into arms/configs/ with MANIFEST.json (written once; the CP1 addition
                         freezes it), and the dev seasons' cells the caps change per fitted arm
    --freeze-hashes      the sha256 the CP1 addition records: level_layer.py, system_sandbox.py, system_gates.py,
                         system_arms.py and arms/configs/MANIFEST.json
    --build ARM --sandbox D   lanes 1 and 2 side by side, then lane 3 and collect, with LLE_LAYER = the arm's config,
                         IOS_CONSTANTS_VERSION pinned; records in arms/<ARM>/ (chain_lane*.json, chain_logs/, build.json).
                         A gated arm (below) needs LLE_CP1_ADDITION: the lead's addition quoting the frozen hashes
    --status             each arm's state

The arms (SPEC 7; the layer touches the men only unless stated):
    IDENTITY   translate false, weights 1, prior pool, ITF box scores as they are, both tours, every family on: G1
               (C1's patches only; the layer copy of 9 Oct 20:31 UTC)
    IDENTITY_ALL  the same with C1's and C2's patches and the final modules: G1 at checkpoint 1
    SEP_ALL    men: no translation; w = 0 and w_results = 0 for every lower-level observation; prior pool
    REF_noITF  both tours: ITF and ITFQ box rows at w = 0 in every box-score family; nothing else
    gated, after the lead's CP1 addition: the SYS family (SYS, SYS_w0, SYS_w50, SYS_w100, SYS_NOCLASS, SYS_BOTH,
               SYS_w25, SYS_w75), addition 1's SYS_ITFASIS and SYS_BOTH_ITFASIS, and RES_ONLY (the reference plus
               B's Elo weighting, men: E's M3)
    the NEW arms (addition 3 section 4), on role F's candidate Stage 0 installed with system_new_arms.py --patch:
               NEW_ASIS and NEW_ASIS_PRE (the identity config on C0_now, C0_pre) and NEW_SYS_BOTH (SYS_BOTH's frozen
               config, the strength from NEW_ASIS's Stage 1), every tuned constant pinned to the reference's; lane 0
               first, then F's lane-0 check
Run: ./python.sh src/eda/lower_level_evidence/system_arms.py --prepare | --config ARM | --write-configs |
     --freeze-hashes | --build ARM --sandbox D | --status
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.lower_level_evidence import system_sandbox as SB  # noqa: E402

SYSTEM = LC.OUT / "system"
ARMS = SYSTEM / "arms"
STRENGTH = ARMS / "strength" / "reference_elo.parquet"
CONSTANTS = ARMS / "constants"
STAGEB_PIN = CONSTANTS / "stageB_adj_summary_reference.json"
REF_CONSTANTS = CONSTANTS / "reference_constants.json"
FIRST_RUN = Path("C:/Users/zerom/tnr_lle")
FROZEN_INSTANCE = LC.REF / "instance"
PY_SHIM = ROOT / "python.sh"
L10 = np.log(10.0) / 400.0
FAMILIES_ALL = {"points_52w": True, "forms": True, "ios": True, "ios_points_short": True, "ratings_iid": True,
                "elo": True}
BOX_FAMILIES = {"points_52w": True, "forms": True, "ios": True, "ios_points_short": True, "ratings_iid": True,
                "elo": False}
PHASE1 = ("IDENTITY", "IDENTITY_ALL", "SEP_ALL", "REF_noITF")
PHASE2 = ("SYS", "SYS_w0", "SYS_w100", "SYS_w50", "SYS_NOCLASS", "SYS_BOTH", "SYS_w25", "SYS_w75")   # the lead's order
CP1_ADDITION = SYSTEM / "preregistration_addition_cp1.sha256"     # the lead's dated addition at checkpoint 1


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o) if np.isfinite(o) else None
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return str(o)
    path.write_text(json.dumps(obj, indent=1, default=default), encoding="utf-8")


def now() -> str:
    return pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")


def status_line(msg: str) -> None:
    with (SYSTEM / "status.log").open("a", encoding="utf-8") as fh:
        fh.write(f"{pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%dT%H:%M:%SZ')} C1 {msg}\n")


# ------------------------------------------------------------------------------------------------
# The reference inputs

def prepare() -> int:
    rec = {"written_at": now(), "what": "the reference inputs every arm of the system reads (no outcome read)"}
    # 1. the strength: the reference build's pre-match overall Elo (Stage 1, retirements counted)
    src = FIRST_RUN / "data" / "studies" / "predictability_diagnostic" / "stage1_baselines.parquet"
    b = pd.read_parquet(src, columns=["match_id", "tour", "year", "elo_a_ret", "elo_b_ret"])
    m = pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])
    chk = {"rows": int(len(b)), "stage0_rows": int(len(m)),
           "same_ids_in_order_as_frozen_stage0": bool(len(b) == len(m) and (b["match_id"].to_numpy()
                                                                             == m["match_id"].to_numpy()).all()),
           "missing_ratings": int(b[["elo_a_ret", "elo_b_ret"]].isna().to_numpy().sum())}
    fr = pd.read_parquet(LC.FRAME, columns=["match_id", "in_elo_overall"])
    j = fr.merge(b, on="match_id", how="left")
    recon = L10 * (j["elo_a_ret"].to_numpy("float64") - j["elo_b_ret"].to_numpy("float64"))
    gap = np.abs(recon - j["in_elo_overall"].to_numpy("float64"))
    chk["frame_matches"] = int(len(fr))
    chk["frame_elo_overall_largest_gap"] = float(np.nanmax(gap))
    chk["frame_elo_overall_reproduced"] = bool(np.nanmax(gap) < 1e-5 and not np.isnan(recon).any())
    if not (chk["same_ids_in_order_as_frozen_stage0"] and chk["frame_elo_overall_reproduced"]
            and chk["missing_ratings"] == 0):
        raise SystemExit(f"the strength table fails its checks: {chk}")
    STRENGTH.parent.mkdir(parents=True, exist_ok=True)
    b.to_parquet(STRENGTH, index=False, compression="zstd")
    rec["strength"] = {"path": str(STRENGTH), "sha256": sha256(STRENGTH), "source": str(src),
                       "source_sha256": sha256(src), "columns": list(b.columns), "checks": chk,
                       "note": "elo_overall in the frozen frame is ln(10)/400 x (R_A - R_B) of pieces.py's pass, which "
                               "reproduces Stage 1's float32 ratings exactly (pieces_meta reproduction 0.0); the gap above "
                               "is float32 rounding"}
    (STRENGTH.with_suffix(".parquet.sha256")).write_text(f"{rec['strength']['sha256']} *{STRENGTH.name}\n",
                                                         encoding="utf-8")
    # 2. Stage B's constants for the pin, checked against the frozen build's log
    sb = FIRST_RUN / "data" / "studies" / "ufc_ideas" / "stageB_adj_summary.json"
    summ = json.loads(sb.read_text(encoding="utf-8"))
    logtxt = (FROZEN_INSTANCE / "chain_logs" / "ufc_stageB_adjperf.log").read_text(encoding="utf-8", errors="replace")
    pat = re.compile(r"chosen (atp|wta) (spw|rpw|tpw): h1 (\S+), K1 (\S+), tau (\d), h3 (\S+), K3 (\S+):")
    from_log = {(t, s): {"h1": float(h1), "K1": float(k1), "tau": int(tau), "h3": float(h3), "K3": float(k3)}
                for t, s, h1, k1, tau, h3, k3 in pat.findall(logtxt)}
    from_summary = {(c["tour"], c["stat"]): {"h1": float(c["h1"]), "K1": float(c["K1"]), "tau": int(c["tau"]),
                                             "h3": float(c["h3"]), "K3": float(c["K3"])} for c in summ["chosen"]}
    if len(from_log) != 6 or from_log != from_summary:
        raise SystemExit(f"Stage B's constants differ between the first run's summary and the frozen build's log: "
                         f"{from_log} vs {from_summary}")
    CONSTANTS.mkdir(parents=True, exist_ok=True)
    write_json(STAGEB_PIN, {"chosen": summ["chosen"], "source": str(sb), "source_sha256": sha256(sb),
                            "checked_against": "frozen/instance/chain_logs/ufc_stageB_adjperf.log (6 'chosen' lines)",
                            "written_at": now()})
    rec["stageB_pin"] = {"path": str(STAGEB_PIN), "sha256": sha256(STAGEB_PIN),
                         "equal_to_frozen_log": True}
    # 3. the other tuned constants, for the constants gate
    s1 = json.loads((FROZEN_INSTANCE / "chain_outputs" / "stage1_baselines_summary.json").read_text(encoding="utf-8"))
    pm = json.loads((FROZEN_INSTANCE / "chain_outputs" / "surface_elo_pieces_pieces_meta.json").read_text(
        encoding="utf-8"))
    s3log = (FROZEN_INSTANCE / "chain_logs" / "stage3_ratings.log").read_text(encoding="utf-8", errors="replace")
    s3 = {t: v for t, v in re.findall(r"(atp|wta): chosen (\{[^}]*\})", s3log)}
    write_json(REF_CONSTANTS, {"stage1_chosen": s1["chosen"], "offset_constants": pm["offset_constants"],
                               "offset_surface_blind_constants": pm["offset_surface_blind_constants"],
                               "stage3_chosen": s3,
                               "stageB_chosen": {f"{t}|{s}": v for (t, s), v in from_summary.items()},
                               "sources": ["frozen/instance/chain_outputs/stage1_baselines_summary.json",
                                           "frozen/instance/chain_outputs/surface_elo_pieces_pieces_meta.json",
                                           "frozen/instance/chain_logs/stage3_ratings.log",
                                           "frozen/instance/chain_logs/ufc_stageB_adjperf.log"],
                               "written_at": now()})
    rec["reference_constants"] = {"path": str(REF_CONSTANTS), "sha256": sha256(REF_CONSTANTS)}
    write_json(ARMS / "reference_inputs.json", rec)
    print(json.dumps(rec, indent=1, default=str))
    return 0


# ------------------------------------------------------------------------------------------------
# The arms' configs

def reference_inputs() -> dict:
    p = ARMS / "reference_inputs.json"
    if not p.exists():
        raise SystemExit("run --prepare first")
    r = json.loads(p.read_text(encoding="utf-8"))
    for k in ("strength", "stageB_pin"):
        if sha256(Path(r[k]["path"])) != r[k]["sha256"]:
            raise SystemExit(f"{r[k]['path']} has changed since --prepare")
    return r


A_STRENGTH = SYSTEM / "classes" / "strength_elo.parquet"      # role A's copy: the same values as arms/strength/


def team_strength() -> dict:
    """Role A's strength table (the one A's gamma and B's parameters read), hash-checked against A's record; identical
    to arms/strength/reference_elo.parquet (both are the reference build's Stage 1 ratings)."""
    meta = json.loads((A_STRENGTH.with_suffix(".json")).read_text(encoding="utf-8"))
    got = sha256(A_STRENGTH)
    if got != meta["copy_sha256"]:
        raise SystemExit(f"{A_STRENGTH}: sha256 {got}, A's record says {meta['copy_sha256']}")
    return {"path": str(A_STRENGTH), "sha256": got}


PHASE3 = ("NEW_ASIS", "NEW_SYS_BOTH")                   # pre-registration addition 1: on role F's candidate C0_now
ADDITION_1 = ("SYS_ITFASIS", "SYS_BOTH_ITFASIS")         # phase 2, after SYS and SYS_BOTH
CP1_ARMS = ("RES_ONLY",)                                 # the lead at checkpoint 1 (E's M3): after SYS, SYS_w0, SYS_w100
GATED = PHASE2 + ADDITION_1 + CP1_ARMS                   # built only under the lead's dated CP1 addition
CONFIGS = ARMS / "configs"                               # every arm's config, frozen by the CP1 addition (MANIFEST.json)
# the lead's rulings at checkpoint 1 (10 Oct 2026): a fitted weight above 1 is set to 1 (box-score w and w_joint, and
# B's w_results: the literal ruling; fitted_cap_results null would leave B's w_results as fitted)
CAPS = {"fitted_cap": 1.0, "fitted_cap_results": 1.0}


def arm_config(arm: str) -> dict:
    ri = reference_inputs()
    base = {"name": arm, "params": None, "params_sha256": None, "classes": None, "prior": "pool",
            "strength": team_strength(),
            "pins": {"stageB_adjperf": {"path": ri["stageB_pin"]["path"], "sha256": ri["stageB_pin"]["sha256"]}},
            "record_dir": str(ARMS / arm / "layer_calls"), "elo_count": "weighted"}
    if arm in ("IDENTITY", "IDENTITY_ALL"):
        cfg = {**base, "tours": ["atp", "wta"], "translate": False, "weight": 1.0, "weight_results": 1.0,
               "itf_box": "as_is", "families": dict(FAMILIES_ALL),
               "what": "G1: the layer on everywhere with neutral settings must reproduce the reference's 58 inputs"
                       + (" (C1's and C2's patches together)" if arm == "IDENTITY_ALL" else "")}
        if arm == "IDENTITY" and (ARMS / "IDENTITY" / "layer_config.json").exists():
            old = json.loads((ARMS / "IDENTITY" / "layer_config.json").read_text(encoding="utf-8"))
            cfg["strength"] = old["strength"]            # written before A's file existed; the same values
        return cfg
    if arm == "SEP_ALL":
        return {**base, "tours": ["atp"], "translate": False, "weight": 0.0, "weight_results": 0.0,
                "itf_box": "exclude", "families": dict(FAMILIES_ALL),
                "what": "SPEC 7: no translation; w = 0 and w_results = 0 for every lower-level observation; prior pool "
                        "(complete separation), men only"}
    if arm.endswith("_C1DRY") and arm[:-len("_C1DRY")] in ("SEP_ALL", "REF_noITF"):
        cfg = arm_config(arm[:-len("_C1DRY")])
        cfg.update({"name": arm, "record_dir": str(ARMS / arm / "layer_calls"),
                    "families": {**cfg["families"], "ios": False, "ios_points_short": False},
                    "what": f"a dry run of {arm[:-6]} with C1's families only (C2's IOS hooks not in the sandbox): it "
                            "checks C1's hooks through the whole chain; never READY, never fitted"})
        return cfg
    if arm == "REF_noITF":
        return {**base, "tours": ["atp", "wta"], "translate": False, "weight": 1.0, "weight_results": 1.0,
                "itf_box": "exclude", "families": dict(BOX_FAMILIES),
                "what": "SPEC 7: the reference with ITF and ITFQ box scores at w = 0 in every box-score family; "
                        "nothing else; both tours"}
    if arm in PHASE2 + ADDITION_1 + CP1_ARMS:
        return phase2_config(arm, base)
    if arm in PHASE3 + NEW_PRE:
        return new_config(arm, base)
    raise SystemExit(f"unknown arm {arm}")


NEW_PRE = ("NEW_ASIS_PRE",)                              # registered in addition 3, section 4 (optional)
NEW_STAGE0 = {"NEW_ASIS": "C0_now", "NEW_SYS_BOTH": "C0_now", "NEW_ASIS_PRE": "C0_pre"}
# NEW_SYS_BOTH's strength, option (c) of addition 7 (8e302da0..., 13:59 UTC): the reference's strength_elo for the
# 873,437 matches it covers, and NEW_ASIS's plain Elo on C0_now re-centred by tour and season for the 298,008 new ones
# (system_new_arms.strength_centred, keep_reference). Option (a), the plain Elo alone (NEW_C0_now_elo.parquet), built
# NEW_SYS_BOTH_optA_unread/, kept unread
NEW_STRENGTH = ARMS / "strength" / "NEW_C0_now_elo_optC.parquet"


def new_config(arm: str, base: dict) -> dict:
    """Addition 3, section 4: the NEW arms on role F's candidate Stage 0, every tuned constant pinned to the reference's
    (pin_constants: Stage 1's K and surface weight, the offset Elo's kd, Stage 3; Stage B by the layer's pin; the IOS
    constants by IOS_CONSTANTS_VERSION). NEW_ASIS and NEW_ASIS_PRE: the identity config. NEW_SYS_BOTH: SYS_BOTH's frozen
    config with the strength of C0_now's own unweighted Elo under the reference K."""
    pins = {"path": str(REF_CONSTANTS), "sha256": sha256(REF_CONSTANTS)}
    if arm in ("NEW_ASIS", "NEW_ASIS_PRE"):
        cfg = {**arm_config("IDENTITY_ALL"), "name": arm, "record_dir": str(ARMS / arm / "layer_calls"),
               "pin_constants": pins}
        cfg["what"] = (f"addition 3 section 4: the template recipe on {NEW_STAGE0[arm]} (the identity config), every "
                       "tuned constant pinned to the reference's")
        return cfg
    frozen = json.loads((CONFIGS / "SYS_BOTH.json").read_text(encoding="utf-8"))
    if not NEW_STRENGTH.exists():
        raise SystemExit(f"{NEW_STRENGTH} does not exist: write it first (system_new_arms.py --strength)")
    side = NEW_STRENGTH.with_suffix(".parquet.sha256").read_text(encoding="utf-8").split()[0]
    if side != sha256(NEW_STRENGTH):
        raise SystemExit(f"{NEW_STRENGTH}: sha256 differs from its .sha256 file")
    cfg = {k: v for k, v in frozen.items() if k != "written_at"}
    cfg.update({"name": arm, "record_dir": str(ARMS / arm / "layer_calls"), "pin_constants": pins,
                "strength": {"path": str(NEW_STRENGTH), "sha256": side},
                "what": "addition 3 section 4 as amended by addition 7: SYS_BOTH's frozen config on C0_now (B's "
                        "frozen parameters, ITF box rows excluded, the caps), every tuned constant pinned; the "
                        "opponent strength the reference's for its matches and C0_now's plain Elo, re-centred "
                        "by tour and season, for the new matches (option c)",
                "from_frozen_config": {"path": str(CONFIGS / "SYS_BOTH.json"),
                                       "sha256": sha256(CONFIGS / "SYS_BOTH.json")}})
    return cfg


CP1_ENV = "LLE_CP1_ADDITION"          # the lead's dated addition at checkpoint 1 (path); its .sha256 must match it
DOSE = {"SYS_w0": 0.0, "SYS_w25": 0.25, "SYS_w50": 0.5, "SYS_w75": 0.75, "SYS_w100": 1.0}


def phase2_config(arm: str, base: dict) -> dict:
    """SPEC section 7, pre-registration addition 1 and the lead's CP1 message (RES_ONLY). The configs are written before
    checkpoint 1 so that the lead's dated CP1 addition can freeze them (arms/configs/MANIFEST.json); building one needs
    that addition (build_gate). B's READY_params.txt must exist; B's params and A's classes are hash-checked; the prior
    is B's frozen choice per tour (READY_params.txt names it)."""
    rel = SYSTEM / "relationship"
    if not (rel / "READY_params.txt").exists():
        raise SystemExit(f"{arm}: B's frozen parameters (relationship/READY_params.txt) do not exist")
    # B's READY_params.txt: params.parquet (SYS's), params_noclass.parquet (SYS_NOCLASS's view: the no-class fit in
    # the same columns); every season from 2013 (params_season_floor 2013 for the rows of 2010-2012); prior "pool"
    params = rel / ("params_noclass.parquet" if arm == "SYS_NOCLASS" else "params.parquet")
    psha = sha256(params)
    pside = params.with_suffix(".sha256")
    if not pside.exists() or pside.read_text(encoding="utf-8").split()[0].lstrip("*") != psha:
        raise SystemExit(f"{params}: sha256 differs from {pside} (or it is missing)")
    if "newcomer prior is NOT kept" not in (rel / "READY_params.txt").read_text(encoding="utf-8"):
        raise SystemExit("B's READY_params.txt does not say the newcomer prior is not kept: wire its home-tier rule first")
    classes = SYSTEM / "classes" / "classes.csv"
    # the lead's rulings of 9 Oct: the 2013 floor; B's fitted w_results at every lower level, ITF and ITFQ included;
    # missing_params "untouched" for the women's cells B cannot fit (SYS_BOTH); ratings_iid: one weight per observation
    # (w_joint), no supplied level term. At checkpoint 1 (10 Oct): fitted weights capped at 1 (CAPS)
    cfg = {**base, "params": str(params), "params_sha256": psha, "classes": str(classes),
           "classes_sha256": sha256(classes), "translate": True, "weight": "fitted", "weight_results": "fitted",
           "prior": "pool", "itf_box": "exclude", "tours": ["atp"], "families": dict(FAMILIES_ALL),
           "params_season_floor": 2013, "missing_params": "error", "solve_w": "w_joint",
           "ratings_level_term": "none", **CAPS,
           # C2's form (b), the level effect estimated inside each snapshot's solve: level_layer_ios's default since 9
           # Oct 23:35 UTC, named here so the frozen config states it (E's M2)
           "ios_level_term": "fixed_effect"}
    if arm == "RES_ONLY":
        # the lead (CP1, E's M3): the reference plus B's Elo weighting and nothing else; SYS's tours, so that SYS
        # against RES_ONLY isolates SYS's results channel
        cfg.pop("ios_level_term")
        cfg.update({"classes": None, "classes_sha256": None, "translate": False, "weight": 1.0, "itf_box": "as_is",
                    "families": {f: f == "elo" for f in FAMILIES_ALL},
                    "what": "the lead at CP1 (E's M3): translate false, weight 1, B's fitted w_results at every lower "
                            "level (ITF and ITFQ included, capped like SYS's), prior pool, ITF box scores as they are, "
                            "Elo only; men, as SYS"})
        return cfg
    if arm in DOSE:
        cfg["weight"] = DOSE[arm]
    elif arm == "SYS_NOCLASS":
        cfg["classes"], cfg["classes_sha256"] = None, None
    elif arm in ("SYS_BOTH", "SYS_BOTH_ITFASIS"):
        cfg["tours"] = ["atp", "wta"]
        cfg["missing_params"] = "untouched"
    if arm in ("SYS_ITFASIS", "SYS_BOTH_ITFASIS"):
        cfg["itf_box"] = "as_is"
    cfg["what"] = f"SPEC 7 / pre-registration addition 1: {arm}"
    return cfg


FREEZE_FILES = ("src/eda/lower_level_evidence/level_layer.py", "src/eda/lower_level_evidence/system_sandbox.py",
                "src/eda/lower_level_evidence/system_gates.py", "src/eda/lower_level_evidence/system_arms.py")
CONFIG_ARMS = PHASE1 + PHASE2 + ADDITION_1 + CP1_ARMS     # the configs folder (phase 3 waits for F's C0_now)


def manifest() -> dict:
    """The frozen configs folder's MANIFEST.json, every listed file re-hashed (refuses on any difference)."""
    p = CONFIGS / "MANIFEST.json"
    if not p.exists():
        raise SystemExit(f"{p} does not exist: --write-configs first")
    man = json.loads(p.read_text(encoding="utf-8"))
    bad = [f for f, h in man["files"].items() if not (CONFIGS / f).exists() or sha256(CONFIGS / f) != h]
    if bad:
        raise SystemExit(f"the frozen configs differ from MANIFEST.json: {bad}")
    return {**man, "sha256": sha256(p)}


def write_configs() -> int:
    """Every arm's config in one folder, the set the lead's CP1 addition freezes: arms/configs/<ARM>.json (an arm built
    already keeps its config byte for byte), and for an arm reading fitted weights the dev seasons' cells the caps
    change (capped_cells_<ARM>.csv: seasons to 2024; the sealed 2025-2026 values are never read). MANIFEST.json lists
    each file's sha256; its own sha256 is the folder's. Written once."""
    import shutil
    from src.eda.lower_level_evidence import level_layer as L
    man_path = CONFIGS / "MANIFEST.json"
    if man_path.exists():
        raise SystemExit(f"{man_path} exists: the configs are frozen (another set needs another folder)")
    CONFIGS.mkdir(parents=True, exist_ok=True)
    files, arms = {}, {}
    for arm in CONFIG_ARMS:
        built = ARMS / arm / "layer_config.json"
        dst = CONFIGS / f"{arm}.json"
        if built.exists():
            shutil.copy2(built, dst)
        else:
            cfg = arm_config(arm)
            L.validate(cfg, arm)
            write_json(dst, {**cfg, "written_at": now()})
        files[dst.name] = sha256(dst)
        cfg = L.load_config(dst)
        arms[arm] = {"config": dst.name, "built_already": built.exists(), "describe": L.describe(cfg)}
        cells = L.capped_cells(cfg)
        if "fitted" in (cfg["weight"], cfg["weight_results"]):
            cp = CONFIGS / f"capped_cells_{arm}.csv"
            cells.to_csv(cp, index=False)
            files[cp.name] = sha256(cp)
            arms[arm]["capped_cells_dev_seasons"] = {f"{c}|{k}": int(n) for (c, k), n in cells.groupby(
                ["column", cells["stat"].eq("results").map({True: "results", False: "box"})]).size().items()}
    rec = {"written_at": now(), "what": "every arm's layer config, frozen by the lead's CP1 addition; build_gate "
                                        "refuses a gated arm unless the addition quotes this file's sha256",
           "files": files, "arms": arms,
           "rulings": {"caps": CAPS, "params_season_floor": 2013, "missing_params": "error (SYS_BOTH, "
                       "SYS_BOTH_ITFASIS: untouched)", "solve_w": "w_joint", "ratings_level_term": "none",
                       "weight_results": "B's fitted value at every lower level, ITF and ITFQ included"},
           "layer_sha256": sha256(ROOT / FREEZE_FILES[0])}
    write_json(man_path, rec)
    side = man_path.with_suffix(".sha256")
    side.write_text(f"{sha256(man_path)} *MANIFEST.json\n", encoding="utf-8")
    print(json.dumps({"MANIFEST.json": sha256(man_path), "files": files}, indent=1))
    return 0


def freeze_hashes() -> dict:
    """What the CP1 addition records: the four files' sha256 and the configs folder's (MANIFEST.json's)."""
    out = {rel: sha256(ROOT / rel) for rel in FREEZE_FILES}
    out["data/studies/lower_level_evidence/system/arms/configs/MANIFEST.json"] = manifest()["sha256"]
    return out


# The code that makes an arm's inputs: the CP1 addition must quote these as they are on disk (role D's guard holds the
# same rule for the layers). The build code (system_arms.py, system_gates.py) and the configs folder are recorded with
# each build: the lead's addition 3 (10 Oct 01:49 UTC) records a later change to them in a later addition, provided no
# SYS-family input changes (its section 1).
INPUT_CODE = ("src/eda/lower_level_evidence/level_layer.py", "src/eda/lower_level_evidence/level_layer_ios.py",
              "src/eda/lower_level_evidence/system_sandbox.py")


def build_gate(arm: str) -> dict:
    """A gated arm (the SYS family, addition 1's, RES_ONLY) is built only under the lead's dated CP1 addition (named by
    LLE_CP1_ADDITION, hash-checked against its .sha256) that quotes, in full, the sha256 of the two layers and of the
    patches as they are on disk; the arm's config must be in the frozen folder, unchanged since MANIFEST.json. Whether
    the addition also quotes the build code and MANIFEST.json is recorded."""
    add = os.environ.get(CP1_ENV, "").strip()
    if not add or not Path(add).exists():
        raise SystemExit(f"{arm} is built only after checkpoint 1: set {CP1_ENV} to the lead's dated addition")
    side = Path(add).with_suffix(".sha256")
    if not side.exists() or side.read_text(encoding="utf-8").split()[0].lstrip("*") != sha256(Path(add)):
        raise SystemExit(f"{add}: its sha256 does not match {side}")
    text = Path(add).read_text(encoding="utf-8")
    need = {rel: sha256(ROOT / rel) for rel in INPUT_CODE}
    missing = [k for k, h in need.items() if h not in text]
    if missing:
        raise SystemExit(f"the CP1 addition {add} does not quote the current sha256 of {missing}: the code that makes "
                         "the inputs changed, or the addition predates it")
    man = manifest()
    if f"{arm}.json" not in man["files"]:
        raise SystemExit(f"{arm}: no frozen config in {CONFIGS}")
    recorded = {rel: {"sha256": sha256(ROOT / rel), "quoted_in_addition": sha256(ROOT / rel) in text}
                for rel in FREEZE_FILES if rel not in INPUT_CODE}
    recorded["configs/MANIFEST.json"] = {"sha256": man["sha256"], "quoted_in_addition": man["sha256"] in text}
    return {"path": add, "sha256": sha256(Path(add)), "input_code": need, "build_code_and_configs": recorded}


def write_config(arm: str) -> Path:
    p = ARMS / arm / "layer_config.json"
    frozen = CONFIGS / f"{arm}.json"
    if frozen.exists():
        # the frozen folder's copy, byte for byte (an arm built before the folder existed keeps its own, the same)
        h = manifest()["files"].get(frozen.name)
        if h is None or sha256(frozen) != h:
            raise SystemExit(f"{frozen} is not the file MANIFEST.json froze")
        if p.exists():
            if sha256(p) != h:
                raise SystemExit(f"{p} differs from the frozen {frozen}")
            return p
        import shutil
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(frozen, p)
        return p
    if arm in GATED:
        raise SystemExit(f"{arm}: its config is written only into the frozen folder (--write-configs)")
    cfg = arm_config(arm)
    from src.eda.lower_level_evidence import level_layer as L
    L.validate(cfg, arm)                                  # refuses anything SPEC 6.3 does not allow
    if p.exists():
        old = json.loads(p.read_text(encoding="utf-8"))
        if {k: v for k, v in old.items() if k != "written_at"} != cfg:
            raise SystemExit(f"{p} exists with another content; an arm's config is not rewritten (move it first)")
        return p
    write_json(p, {**cfg, "written_at": now()})
    return p


# ------------------------------------------------------------------------------------------------
# The build

def run_lane(lane: str, sandbox: Path, out: Path, env: dict, log_path: Path) -> subprocess.Popen:
    fh = log_path.open("w", encoding="utf-8")
    return subprocess.Popen(["bash", str(PY_SHIM), "src/eda/model_rebuild/run_chain.py", "--lane", lane, "--out",
                             str(out)], cwd=ROOT, env=env, stdout=fh, stderr=subprocess.STDOUT)


def run_steps(steps: list, sandbox: Path, out: Path, env: dict, label: str) -> int:
    """run_chain.run_lane's runner for a part of a lane (the same interpreter, working folder, logs and record format;
    the record is <out>/chain_lane<label>.json): lane 1 is split around the IOS part, lane 0 runs without its timeline
    step when the candidate brings its own."""
    from src.eda.model_rebuild import run_chain as RC
    (sandbox / "logs").mkdir(exist_ok=True)
    record_path = out / f"chain_lane{label}.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {"steps": []}
    record.update({"sandbox": str(sandbox), "lane": label})
    for name, script in steps:
        t0 = time.time()
        log = sandbox / "logs" / f"{name}.log"
        print(f"--> {name}: {script}", flush=True)
        with log.open("w", encoding="utf-8") as fh:
            path, *args = script.split()
            done = subprocess.run([RC.PY, str(sandbox / path), *args], cwd=sandbox, stdout=fh,
                                  stderr=subprocess.STDOUT, env=env)
        row = {"step": name, "script": script, "exit": done.returncode, "seconds": round(time.time() - t0, 1),
               "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "log": str(log)}
        record["steps"].append(row)
        record_path.write_text(json.dumps(record, indent=1), encoding="utf-8")
        print(f"    exit {done.returncode} in {row['seconds']} s", flush=True)
        if done.returncode != 0:
            return done.returncode
    return 0


# Steps whose outputs an arm may take from the reference-equivalent build on the frozen tables (the first run's sandbox,
# read only: its Stage 1, Stage A, Stage C and offset-Elo steps ran the decided builders unpatched, 9 Oct) instead of
# rebuilding them: Stages A and C feed no model input (run_chain.py:15-17: only Stage D's rundown reads them); Stage 1
# and the offset Elo only when the arm leaves Elo unchanged. Never on a candidate Stage 0.
REUSABLE = {
    "stage1_baselines": ["data/studies/predictability_diagnostic/" + f for f in (
        "stage1_baselines.parquet", "stage1_baselines_summary.json", "stage1_elo_tuning.csv", "stage1_elo_weights.csv",
        "stage1_rank_fits.csv")],
    "ufc_stageA_ratings": ["data/studies/ufc_ideas/" + f for f in (
        "stageA_bt.parquet", "stageA_mesr.parquet", "stageA_bt_tuning.csv", "stageA_mesr_tuning.csv",
        "stageA_bt_summary.json")],
    "ufc_stageA_features": ["data/studies/ufc_ideas/" + f for f in ("stageA_features.parquet",
                                                                    "stageA_features_summary.json")],
    "ufc_stageC_fatigue": ["data/studies/ufc_ideas/" + f for f in (
        "stageC_fatigue_part.parquet", "stageC_fatigue_part.json", "stageC_fatigue_players.csv")],
    "ufc_stageC_sos": ["data/studies/ufc_ideas/" + f for f in ("stageC_sos_part.parquet", "stageC_sos_part.json")],
    "ufc_stageC_rundown": ["data/studies/ufc_ideas/" + f for f in (
        "stageC_features.parquet", "stageC_catalog.json", "stageC_null_copies.csv", "stageC_ranking.csv",
        "stageC_ratings_null_copies.csv", "stageC_ratings_ranking.csv", "stageC_ratings_results.csv",
        "stageC_ratings_results.json", "stageC_results.csv", "stageC_results.json", "stageC_summary.json")],
    "elo_pieces": ["data/studies/surface_elo_pieces/" + f for f in ("pieces.parquet", "pieces_meta.json")],
}
NO_INPUT = ("ufc_stageA_ratings", "ufc_stageA_features", "ufc_stageC_fatigue", "ufc_stageC_sos", "ufc_stageC_rundown")
ELO_STEPS = ("stage1_baselines", "elo_pieces")
# An arm that changes Elo only (RES_ONLY) leaves three expensive lane-1 steps' inputs as the reference's: Stage 3 reads
# no Elo; Stage B's adjperf and IOS read Elo only to tune, and their constants are pinned (the pin) or the registry's.
# Their outputs come from IDENTITY_ALL's sandbox: the final code at the identity settings, G1 passed (the files each
# step writes: their modification times in tnr_sys1's identity build, 9 Oct). The steps that read Elo for anything
# else (Stage 4, Stage B's split and rundown, Stage D, the frames, the offset Elo) run.
IDENTITY_SOURCE = "IDENTITY_ALL"
REUSABLE_IDENTITY = {
    "stage3_ratings": ["data/studies/predictability_diagnostic/" + f for f in (
        "stage3_rating_tuning.csv", "stage3_ratings.parquet", "stage3_ratings_summary.json")],
    "ufc_stageB_adjperf": ["data/studies/ufc_ideas/" + f for f in (
        "stageB_adj.parquet", "stageB_adj_features.parquet", "stageB_adj_summary.json", "stageB_adj_tuning.csv")],
    "ufc_stageB_ios": ["data/studies/ufc_ideas/" + f for f in (
        "stageB_ios.parquet", "stageB_ios_features.parquet", "stageB_ios_summary.json", "stageB_ios_tuning.csv")],
}


def elo_only(cfg: dict) -> bool:
    return [f for f, on in cfg["families"].items() if on] == ["elo"]


def identity_source() -> Path:
    """IDENTITY_ALL's sandbox, once its G1 and constants gates passed."""
    d = ARMS / IDENTITY_SOURCE
    s = json.loads((d / "gates" / "summary.json").read_text(encoding="utf-8")) if (d / "gates" / "summary.json").exists() \
        else {}
    if not (s.get("G1") is True and s.get("constants") is True):
        raise SystemExit(f"{IDENTITY_SOURCE} has not passed G1 and the constants gate: its steps cannot be reused")
    runs = json.loads((d / "build.json").read_text(encoding="utf-8"))["runs"]
    return Path([r for r in runs if r.get("ok")][-1]["sandbox"])


def reusable_steps(cfg: dict, sysrec: dict) -> list[str]:
    """The lane-1 steps this arm takes from a reference-equivalent build: Stages A and C always (no input reads
    them); Stage 1 and the offset Elo when the arm's Elo is the reference's (family off); Stage 3 and Stage B's adjperf
    and IOS when the arm changes Elo only. None on a candidate Stage 0."""
    if sysrec.get("candidate_stage0"):
        return []
    steps = list(NO_INPUT)
    if not cfg["families"]["elo"]:
        steps += list(ELO_STEPS)
    if elo_only(cfg):
        steps += list(REUSABLE_IDENTITY)
    return steps


def reuse(sandbox: Path, steps: list[str]) -> dict:
    """Copy the reused steps' outputs into this sandbox, with hashes: Stages A and C, Stage 1 and the offset Elo from
    the first run's sandbox (read only); Stage 3 and Stage B's adjperf and IOS from IDENTITY_ALL's."""
    import shutil
    rec = {"source": str(FIRST_RUN), "files": {}}
    for step in steps:
        src_root = identity_source() if step in REUSABLE_IDENTITY else FIRST_RUN
        for rel in (REUSABLE_IDENTITY.get(step) or REUSABLE[step]):
            src, dst = src_root / rel, sandbox / rel
            if not src.exists():
                raise SystemExit(f"{src} is missing: {step} cannot be reused")
            shutil.copy2(src, dst)
            rec["files"][rel] = {"step": step, "from": str(src_root), "sha256": sha256(dst),
                                 "source_sha256": sha256(src)}
            if rec["files"][rel]["sha256"] != rec["files"][rel]["source_sha256"]:
                raise SystemExit(f"{dst}: the copy differs from its source")
    return rec


VALIDATED_SRC = ARMS / "validated_src"
C2_PATCHED = ("src/eda/match_timing/rebuild.py", "src/eda/surface_ios/build_cache.py",
              "src/eda/surface_ios/build_features.py", "src/eda/tabpfn_leakproof/build_frame.py",
              "src/eda/surface_ios/arms.py", "src/eda/surface_ios/probe.py")


def restore_validated_code(sandbox: Path, skip_check=()) -> dict:
    """The sandbox's chain code made equal to the code IDENTITY_ALL ran and G1 validated (arms/validated_src/, a copy of
    tnr_sys4's src at 10 Oct 00:30 UTC; src/eda/lower_level_evidence/ excluded): a file that differs is copied back
    from the snapshot. The builders C1's and C2's patches rewrite are only checked (they are patched from the
    repository's text, so a difference means the repository's builder changed): a difference refuses the build.
    Files the snapshot does not hold (modules added to the repository since) are left; the validated code imports none.
    Why: the repository's src changed after 00:30 UTC (tabpfn_thinking's frame builder fills the women's indoor flag
    since 01:14 UTC), and a sandbox set up later carried that into SYS_w100's inputs (G2 caught it)."""
    import shutil
    sb = Path(sandbox)
    man = json.loads((VALIDATED_SRC / "MANIFEST.json").read_text(encoding="utf-8"))
    side = (VALIDATED_SRC / "MANIFEST.sha256").read_text(encoding="utf-8").split()[0]
    if side != sha256(VALIDATED_SRC / "MANIFEST.json"):
        raise SystemExit("validated_src/MANIFEST.json differs from its .sha256")
    patched = set(SB.PATCH_SPECS) | set(C2_PATCHED)
    out = {"snapshot_manifest_sha256": side, "files": len(man["files"]), "restored": [], "patched_checked": {}}
    for rel, h in man["files"].items():
        dst = sb / rel
        got = sha256(dst) if dst.exists() else None
        if rel in patched:
            if rel not in skip_check:                     # a NEW sandbox's pinned builders: system_new_arms checks them
                # since 10 Oct 2026 the repository's builders carry the hooks under the integrated tag: the same code,
                # other comments (SB.normalize), plus the post-validation edits that move no value (SB.validated_now)
                out["patched_checked"][rel] = got == h or (dst.exists() and dst.read_text(encoding="utf-8") ==
                                                           SB.validated_now((VALIDATED_SRC / rel).read_text(
                                                               encoding="utf-8"), rel))
            continue
        if got != h:
            src = VALIDATED_SRC / rel
            if sha256(src) != h:
                raise SystemExit(f"{src} differs from the snapshot's manifest")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            out["restored"].append(rel)
    bad = [k for k, v in out["patched_checked"].items() if not v]
    if bad:
        raise SystemExit(f"{sb}: patched builders differ from the validated ones (has the repository's builder "
                         f"changed?): {bad}")
    return out


def lane2_runs_dir(cfg: dict, sandbox: Path) -> dict:
    """The folder lane 2's surface runs go to under this config (C2's level_layer_ios.runs_dir: the decided folder when
    the "ios" family is off, else full_runs/lle_<name>_<fingerprint[:12]>), and whether it existed before the build."""
    base = Path(sandbox) / "data" / "studies" / "surface_ios" / "full_runs"
    c2 = SB.c2_module()
    fp = c2.fingerprint(cfg, ("ios",)) if c2 is not None else "off"
    path = base if fp == "off" else base / f"lle_{cfg['name']}_{fp[:12]}"
    return {"path": str(path), "fingerprint": fp, "hooked": fp != "off", "existed_before_build": path.exists()}


def lane_plan(cfg: dict, sysrec: dict, skip: list[str] | tuple = ()) -> dict:
    """Which parts a build runs: lane 0 for a candidate Stage 0 (its timeline step only when the candidate brings no
    timing.parquet), lane 1 (less the reused steps) split around C2's IOS part when an IOS family is on and C2's patch
    is in (a candidate's lane 0 rebuilds the whole leak-proof table instead), lanes 2 and 3."""
    from src.eda.model_rebuild import run_chain as RC
    cand = sysrec.get("candidate_stage0")
    ios_on = any(cfg["families"].get(f) for f in ("ios", "ios_points_short"))
    c2_in = bool(sysrec.get("c2"))
    lane0 = []
    if cand:
        lane0 = [s for s in RC.LANES["0"] if not (s[0] == "timeline" and cand.get("timing"))]
    steps1 = [s for s in RC.LANES["1"] if s[0] not in set(skip)]
    names = [n for n, _ in steps1]
    split = ios_on and c2_in and not cand
    i = names.index("leakproof_frame")
    return {"lane0": lane0, "lane1a": steps1[:i] if split else steps1, "ios_part": split,
            "lane1b": steps1[i:] if split else [], "ios_on": ios_on, "c2_in": c2_in, "candidate": bool(cand),
            "reused": list(skip)}


def build(arm: str, sandbox: str, lanes: str = "0123", reuse_steps: bool = True) -> int:
    sb = Path(sandbox)
    SB.refuse(sb)
    sysrec_path = sb / "LLE_SYSTEM.json"
    if not sysrec_path.exists():
        raise SystemExit(f"{sb} is not patched: system_sandbox.py --patch --sandbox {sb}")
    sysrec = json.loads(sysrec_path.read_text(encoding="utf-8"))
    pins_files = ()
    if sysrec.get("pins"):
        from src.eda.lower_level_evidence import system_new_arms as NEW
        pins_files = tuple(NEW.PIN_SPECS)
    validated = restore_validated_code(sb, skip_check=pins_files)
    if arm in PHASE3 + NEW_PRE:
        # a NEW arm: role F's candidate Stage 0 and the constant pins must be in this sandbox (system_new_arms.py)
        from src.eda.lower_level_evidence import system_new_arms as NEW
        cand = (sysrec.get("candidate_stage0") or {}).get("source", "")
        if not cand or Path(cand).name != NEW_STAGE0[arm] or not sysrec.get("pins"):
            raise SystemExit(f"{sb}: {arm} needs {NEW_STAGE0[arm]} and the pins: system_new_arms.py --patch --sandbox "
                             f"{sb} --stage0 {SYSTEM / 'stage0' / NEW_STAGE0[arm]}")
        chk = NEW.check_patch(sb)
    else:
        if sysrec.get("candidate_stage0") or sysrec.get("pins"):
            raise SystemExit(f"{sb} holds a candidate Stage 0 or the pins: not for {arm}")
        chk = SB.check_patch(sb)
    if not chk["pass"]:
        raise SystemExit(f"{sb}: C1's patches are not in place: {chk}")
    cp1 = build_gate(arm) if arm in GATED else None
    cfg_path = write_config(arm)
    from src.eda.lower_level_evidence import level_layer as L
    cfg = L.load_config(cfg_path)
    skip = reusable_steps(cfg, sysrec) if reuse_steps else []
    reused = reuse(sb, skip) if skip and "1" in lanes else None
    plan = lane_plan(cfg, sysrec, skip if reused else [])
    if arm != "IDENTITY" and plan["ios_on"] and not plan["c2_in"]:
        raise SystemExit(f"{arm} needs C2's IOS hooks in the sandbox (READY_ios_hooks.txt, then --patch again)")
    if plan["c2_in"]:
        c2 = SB.c2_module()
        c2chk = c2.check_patch(sb) if c2 is not None else {"pass": False}
        if not c2chk.get("pass"):
            raise SystemExit(f"{sb}: C2's patch is not in place: {c2chk.get('problems')}")
    out = ARMS / arm
    out.mkdir(parents=True, exist_ok=True)
    lane2_dir = lane2_runs_dir(cfg, sb)
    if lane2_dir["existed_before_build"] and lane2_dir["hooked"]:
        # C2's caution (C_layer_ios.md §6): lane 2 reuses the saved runs of a folder named after the arm and its
        # fingerprint, which knows neither level_layer.py's version nor the cap; a name is built once per sandbox
        raise SystemExit(f"{sb}: lane 2's folder {lane2_dir['path']} exists from an earlier build of {arm}: build this "
                         "arm in a sandbox that never built it")
    env = {**os.environ, "MODEL_REBUILD_SANDBOX": str(sb), "LLE_LAYER": str(cfg_path),
           "IOS_CONSTANTS_VERSION": SB.IOS_VERSION, "PYTHONIOENCODING": "utf-8"}
    # a shared machine (SPEC 9.10): lane 2's surface-IOS runs and the IOS part's solves are independent, so fewer
    # workers change no result, only the time (C2's READY_ios_hooks.txt names both variables)
    env.setdefault("SURFACE_IOS_WORKERS", "6")
    env.setdefault("MATCH_TIMING_WORKERS", "3")
    rec_path = out / "build.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {"runs": []}
    run = {"arm": arm, "sandbox": str(sb), "config": str(cfg_path), "config_sha256": sha256(cfg_path),
           "IOS_CONSTANTS_VERSION": SB.IOS_VERSION, "lanes": lanes,
           "plan": {k: ([s[0] if isinstance(s, (tuple, list)) else s for s in v] if isinstance(v, list) else v)
                    for k, v in plan.items()},
           "started_at": now(), "level_layer_sha256": sha256(ROOT / "src/eda/lower_level_evidence/level_layer.py"),
           "level_layer_sha256_in_sandbox": sha256(sb / "src/eda/lower_level_evidence/level_layer.py"),
           "level_layer_ios_sha256_in_sandbox": (sha256(sb / "src/eda/lower_level_evidence/level_layer_ios.py")
                                                 if (sb / "src/eda/lower_level_evidence/level_layer_ios.py").exists()
                                                 else None),
           "cp1_addition": cp1, "lane2_runs_dir": lane2_dir, "validated_code": validated, "sandbox_record": sysrec,
           "reused": reused, "steps": []}
    status_line(f"build {arm} started in {sb} (lanes {lanes}; IOS part {plan['ios_part']}; candidate Stage 0 "
                f"{plan['candidate']})")
    t0 = time.time()
    ok = True
    if "0" in lanes and plan["lane0"]:
        c0 = run_steps(plan["lane0"], sb, out, env, "0")
        run["steps"].append({"lane 0": c0, "seconds": round(time.time() - t0, 1)})
        ok = c0 == 0
        if ok and arm in PHASE3 + NEW_PRE:
            # F's lane-0 notes: the odds table the frozen one, the frame's matches unchanged, before lane 1
            from src.eda.lower_level_evidence import system_new_arms as NEW
            l0 = NEW.lane0_check(sb)
            write_json(out / "lane0_check.json", l0)
            run["steps"].append({"lane 0 check": l0["pass"]})
            ok = bool(l0["pass"])
    p2 = run_lane("2", sb, out, env, out / "lane2.out") if ok and "2" in lanes else None
    if ok and "1" in lanes:
        t1 = time.time()
        ios = {}
        th = None
        if plan["ios_part"]:
            # C2's IOS part reads no lane-1 output (READY_ios_hooks.txt: "before starting lanes 1 and 2"), so it runs
            # beside lane 1's first part and must end before leakproof_frame
            import threading

            def ios_part():
                t_ = time.time()
                ios["code"] = SB.c2_module().run_ios_part(sb, out, env=env)
                ios["seconds"] = round(time.time() - t_, 1)
            th = threading.Thread(target=ios_part)
            th.start()
        c1 = run_steps(plan["lane1a"], sb, out, env, "1a" if plan["ios_part"] else "1")
        if th is not None:
            th.join()
            run["steps"].append({"C2 IOS part": ios.get("code"), "seconds": ios.get("seconds")})
            if c1 == 0 and ios.get("code") != 0:
                c1 = 1
        if c1 == 0 and plan["lane1b"]:
            c1 = run_steps(plan["lane1b"], sb, out, env, "1b")
        run["steps"].append({"lane 1": c1, "seconds": round(time.time() - t1, 1)})
        ok = c1 == 0
    if p2 is not None:
        c2code = p2.wait()
        run["steps"].append({"lane 2": c2code, "seconds": round(time.time() - t0, 1)})
        ok = ok and c2code == 0
    if ok and "3" in lanes:
        t1 = time.time()
        p3 = run_lane("3", sb, out, env, out / "lane3.out")
        c3 = p3.wait()
        run["steps"].append({"lane 3": c3, "seconds": round(time.time() - t1, 1)})
        ok = c3 == 0
        if ok:
            c = subprocess.run(["bash", str(PY_SHIM), "src/eda/model_rebuild/run_chain.py", "--collect", "--out",
                                str(out)], cwd=ROOT, env=env, capture_output=True, text=True)
            run["steps"].append({"collect": c.returncode})
            ok = c.returncode == 0
            if ok:
                write_json(out / "model_inputs_sha256.json", {"model_frame.parquet": sha256(out / "model_frame.parquet"),
                                                              "model_inputs.json": sha256(out / "model_inputs.json")})
    run["finished_at"] = now()
    run["seconds"] = round(time.time() - t0, 1)
    run["ok"] = bool(ok)
    rec["runs"].append(run)
    write_json(rec_path, rec)
    status_line(f"build {arm} {'finished' if ok else 'FAILED'} in {run['seconds'] / 60:.1f} min ({sb})")
    return 0 if ok else 1


def resume(arm: str, sandbox: str, from_step: str) -> int:
    """Finish an arm's interrupted build in its sandbox: lane 1 from `from_step` (the earlier steps' outputs are this
    arm's, already in the sandbox; Stages A and C, if they come earlier and did not finish, are taken from the
    reference-equivalent build like every arm's), then lane 3 and collect. Lane 2 must have finished. The sandbox must
    still hold the layer copied when the build started (LLE_SYSTEM.json), so every step of the arm ran the same code."""
    from src.eda.model_rebuild import run_chain as RC
    sb = Path(sandbox)
    SB.refuse(sb)
    if arm in GATED:
        build_gate(arm)
    out = ARMS / arm
    sysrec = json.loads((sb / "LLE_SYSTEM.json").read_text(encoding="utf-8"))
    rel = "src/eda/lower_level_evidence/level_layer.py"
    if sha256(sb / rel) != sysrec["c1"]["copied"][rel]:
        raise SystemExit(f"{sb}: its layer is not the copy the build started with")
    validated = restore_validated_code(sb, skip_check=tuple(__import__("src.eda.lower_level_evidence.system_new_arms",
                                       fromlist=["PIN_SPECS"]).PIN_SPECS) if sysrec.get("pins") else ())
    lane2 = json.loads((out / "chain_lane2.json").read_text(encoding="utf-8"))
    if [s["step"] for s in lane2["steps"] if s["exit"] == 0][-2:] != ["surface_ios_cache", "surface_ios_features"]:
        raise SystemExit(f"{arm}: lane 2 has not finished")
    cfg_path = out / "layer_config.json"
    names = [n for n, _ in RC.LANES["1"]]
    i = names.index(from_step)
    cand = bool(sysrec.get("candidate_stage0"))
    # on a candidate Stage 0, Stages A and C are rebuilt like every step (never taken from the reference's build)
    earlier_reused = [] if cand else [s for s in NO_INPUT if names.index(s) < i]
    reused = reuse(sb, earlier_reused) if earlier_reused else None
    steps = [s for s in RC.LANES["1"][i:] if cand or s[0] not in NO_INPUT]
    env = {**os.environ, "MODEL_REBUILD_SANDBOX": str(sb), "LLE_LAYER": str(cfg_path),
           "IOS_CONSTANTS_VERSION": SB.IOS_VERSION, "PYTHONIOENCODING": "utf-8"}
    env.setdefault("SURFACE_IOS_WORKERS", "6")
    env.setdefault("MATCH_TIMING_WORKERS", "3")
    from src.eda.lower_level_evidence import level_layer as L
    cfg = L.load_config(cfg_path)
    # a candidate Stage 0's IOS tables come from its lane 0 (the full leak-proof rebuild on the candidate's pool); C2's
    # IOS part alone would merge with the stored per-player part, which it refuses there (READY_ios_hooks.txt)
    ios_fresh = (any(cfg["families"].get(f) for f in ("ios", "ios_points_short")) and bool(sysrec.get("c2"))
                 and not sysrec.get("candidate_stage0"))
    status_line(f"build {arm} resumed in {sb} from {from_step} (Stages A and C taken from the reference-equivalent "
                f"build: {earlier_reused}; C2's IOS part rebuilt first: {ios_fresh})")
    t0 = time.time()
    run = {"arm": arm, "sandbox": str(sb), "resumed_from": from_step, "reused": reused, "started_at": now(),
           "config_sha256": sha256(cfg_path), "level_layer_sha256_in_sandbox": sha256(sb / rel),
           "validated_code": validated, "steps": []}
    if ios_fresh:
        # never resume past a stale IOS part (C2's caution): it is rebuilt with the arm's config before lane 1 goes on
        code = SB.c2_module().run_ios_part(sb, out, env=env)
        run["steps"].append({"C2 IOS part (fresh)": code, "seconds": round(time.time() - t0, 1)})
        if code != 0:
            run.update({"finished_at": now(), "ok": False})
            rec_path = out / "build.json"
            rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {"runs": []}
            rec["runs"].append(run)
            write_json(rec_path, rec)
            return 1
    c1 = run_steps(steps, sb, out, env, "1r")
    run["steps"].append({"lane 1 (resumed)": c1, "seconds": round(time.time() - t0, 1)})
    ok = c1 == 0
    if ok:
        c3 = run_lane("3", sb, out, env, out / "lane3.out").wait()
        run["steps"].append({"lane 3": c3})
        ok = c3 == 0
    if ok:
        c = subprocess.run(["bash", str(PY_SHIM), "src/eda/model_rebuild/run_chain.py", "--collect", "--out", str(out)],
                           cwd=ROOT, env=env, capture_output=True, text=True)
        run["steps"].append({"collect": c.returncode})
        ok = c.returncode == 0
    run.update({"finished_at": now(), "seconds": round(time.time() - t0, 1), "ok": bool(ok)})
    rec_path = out / "build.json"
    rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.exists() else {"runs": []}
    rec["runs"].append(run)
    write_json(rec_path, rec)
    status_line(f"build {arm} {'finished' if ok else 'FAILED'} (resumed) in {run['seconds'] / 60:.1f} min ({sb})")
    return 0 if ok else 1


def status() -> int:
    for arm in PHASE1 + PHASE2 + ADDITION_1 + CP1_ARMS + PHASE3 + NEW_PRE:
        d = ARMS / arm
        if not d.exists():
            continue
        b = json.loads((d / "build.json").read_text(encoding="utf-8")) if (d / "build.json").exists() else {}
        last = (b.get("runs") or [{}])[-1]
        print(f"{arm:10s} config {'yes' if (d / 'layer_config.json').exists() else 'no '}  frame "
              f"{'yes' if (d / 'model_frame.parquet').exists() else 'no '}  build ok {last.get('ok')}  "
              f"READY {'yes' if (d / 'READY.txt').exists() else 'no'}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare", action="store_true")
    g.add_argument("--config")
    g.add_argument("--build")
    g.add_argument("--status", action="store_true")
    g.add_argument("--write-configs", action="store_true", help="every arm's config into arms/configs/ (frozen set)")
    g.add_argument("--freeze-hashes", action="store_true", help="print what the CP1 addition records")
    ap.add_argument("--sandbox")
    ap.add_argument("--lanes", default="0123")
    ap.add_argument("--no-reuse", action="store_true", help="rebuild every lane-1 step (no reused outputs)")
    ap.add_argument("--resume-from", help="with --build: finish an interrupted build from this lane-1 step")
    a = ap.parse_args()
    if a.build and a.resume_from:
        return resume(a.build, a.sandbox, a.resume_from)
    if a.prepare:
        return prepare()
    if a.write_configs:
        return write_configs()
    if a.freeze_hashes:
        print(json.dumps(freeze_hashes(), indent=1))
        return 0
    if a.config:
        print(write_config(a.config))
        return 0
    if a.build:
        if not a.sandbox:
            raise SystemExit("--sandbox is required")
        return build(a.build, a.sandbox, a.lanes, reuse_steps=not a.no_reuse)
    return status()


if __name__ == "__main__":
    sys.exit(main())
