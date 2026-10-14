"""The level layer in the current best model (men; docs/decisions/2026-10-10-level-evidence-layer.md): the official
config, and the config each build resolves from it.

The official config (OFFICIAL, data/studies/current_best_model/level_layer/official.json) is the level-evidence study's
tested configuration (its SYS arm: data/studies/lower_level_evidence/system/arms/configs/SYS.json), with the frozen
parameters, classes and Stage B pin, each hash-checked by the layer. Two things belong to each build:
    the opponent strength   the plain pre-match Elo on the build's own Stage 0: Stage 1's pass (retirements counted),
                            with the frozen reference's K (the official config's strength_k), without the layer's
                            w_results weighting. The frozen strength (A's strength_elo.parquet) covers only the
                            reference's matches; a match played after the freeze needs its own. The build's value must
                            equal the frozen one on the reference's matches; any difference is reported (a main-tour
                            revision moves the ratings after it). If the scale shifts (a tour-season's mean difference on
                            the reference's main-tour matches beyond SHIFT_TOL Elo points), the strength is re-centred
                            as addition 7 did for NEW_SYS_BOTH (option c): the frozen value for every match it covers, the
                            build's value less its tour-season shift for the others
    the records             the hooks' layer_calls.jsonl, inside the build's own tree

Run inside the tree being built, with that tree's interpreter path (run_chain.py --prepare-layer does it in its sandbox;
prediction_run/run.py --build does it after Stage 0):
    python <tree>/src/eda/current_best_model/layer_config.py --resolve [--official <path>]
writes into <tree>/data/studies/current_best_model/level_layer/this_build/:
    strength_elo.parquet (+ .sha256)   match_id, elo_a_ret, elo_b_ret, n_a_ret, n_b_ret (float32, as Stage 1 stores them)
    strength_check.json                 the check against the frozen strength, and the rule applied
    build_config.json (+ .sha256)       the official config with this strength, the tree's record folder, and the
                                        Stage 0 it was resolved on (the lanes refuse a config resolved on another)
and prints the build config's path: every step then reads it as LLE_LAYER.
    python <tree>/src/eda/current_best_model/layer_config.py --check     the strength check only, nothing written

The repository's own builders are hooked but off: LLE_LAYER unset builds the template without the layer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]           # the tree being built (a sandbox), or the repository
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OFFICIAL = Path("C:/Users/zerom/Documents/Tennis-predictions/data/studies/current_best_model/level_layer/official.json")
REL_BUILD = Path("data") / "studies" / "current_best_model" / "level_layer" / "this_build"
STAGE0 = Path("data") / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
STRENGTH_COLS = ["match_id", "elo_a_ret", "elo_b_ret", "n_a_ret", "n_b_ret"]
RULE = "ret"                                         # Stage 1's rule the strength reads: retirements counted
SHIFT_TOL = 1.0                                      # Elo points: a tour-season mean shift beyond it re-centres


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def log(msg: str) -> None:
    print(f"[layer_config] {msg}", flush=True)


def official(path: Path | str = OFFICIAL) -> dict:
    """The official config, hash-checked against its .sha256 file and validated by the layer's own loaders."""
    from src.eda.lower_level_evidence import level_layer_ios as LI
    p = Path(path)
    side = p.with_suffix(".sha256")
    if not side.exists() or side.read_text(encoding="utf-8").split()[0].lstrip("*") != sha256(p):
        raise SystemExit(f"{p}: its sha256 does not match {side}")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    LI.validate_config(dict(cfg), str(p))
    for key in ("strength_k", "strength"):
        if not cfg.get(key):
            raise SystemExit(f"{p}: no {key}")
    return cfg


# ------------------------------------------------------------------------------------------------
# The strength

def plain_strength(k: dict) -> pd.DataFrame:
    """The plain pre-match overall Elo of every match of this tree's Stage 0: stage1_baselines' own pass (elo_pass,
    retirements counted, every played match a full update: no layer weighting), with the K given per tour, cast to
    float32 as Stage 1 stores it. Only the overall rating is read; the surface ratings, which do not feed it, are not
    computed."""
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic import stage1_baselines as B1
    m = C.load_matches(["match_id", "tour", "status", "surface", "tournament_id", "tournament_date", "round_order",
                        "player_a_id", "player_b_id", "a_won"])
    block = np.full((len(m), 4), np.nan)
    for tour in C.TOURS:
        idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
        t = m.iloc[idx].reset_index(drop=True)
        h = B1.history_arrays(t)
        kk = {c: float(k[tour][c]) for c in ("k0", "offset", "shape")}
        t0 = time.time()
        out = B1.run_elo(h, t["status"], RULE, kk, surface=False)
        block[idx] = out[:, :4]
        log(f"{tour}: {len(t):,} matches, K {kk}, {time.time() - t0:.0f} s")
    s = pd.DataFrame({"match_id": m["match_id"].astype(str).to_numpy()})
    for j, c in enumerate(STRENGTH_COLS[1:]):
        s[c] = block[:, j].astype("float32")         # Stage 1: "ratings to 0.001 point; counts exact below 2**24"
    return s


MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250")   # Stage 0's main-tour map levels (the scale is read on them)


def stage0_matches() -> pd.DataFrame:
    """This tree's Stage 0 matches, the columns the check and the re-centring read."""
    from src.eda.predictability_diagnostic import common as C
    m = C.load_matches(["match_id", "tour", "year", "tournament_date", "map_level"])
    m["match_id"] = m["match_id"].astype(str)
    return m


def check(s: pd.DataFrame, ref_path: Path, m: pd.DataFrame | None = None) -> tuple[dict, pd.Series]:
    """The build's strength against the frozen one, on the matches both hold: equal bit for bit, or where they differ
    (the first differing day per tour; differences by tour and season), and the tour-season shift of the main-tour
    matches (the scale). New matches (not in the frozen table) and dropped ones are counted. m: Stage 0's matches
    (default this tree's)."""
    ref = pd.read_parquet(ref_path, columns=STRENGTH_COLS)
    ref["match_id"] = ref["match_id"].astype(str)
    m = stage0_matches() if m is None else m
    j = ref.merge(s, on="match_id", suffixes=("_ref", ""), how="inner").merge(m, on="match_id", how="left")
    cols = ["elo_a_ret", "elo_b_ret"]
    a = j[cols].to_numpy("float32")
    r = j[[f"{c}_ref" for c in cols]].to_numpy("float32")
    differ = ~((a == r) | (np.isnan(a) & np.isnan(r))).all(axis=1)
    out = {"frozen_matches": int(len(ref)), "build_matches": int(len(s)), "both": int(len(j)),
           "new_in_build": int((~s["match_id"].isin(ref["match_id"])).sum()),
           "dropped_from_build": int((~ref["match_id"].isin(s["match_id"])).sum()),
           "missing_ratings_in_build": int(s[cols].isna().to_numpy().sum()),
           "differing_matches": int(differ.sum()),
           "equal_bit_for_bit": bool(not differ.any()),
           "largest_difference": float(np.nanmax(np.abs(a - r))) if len(j) else 0.0}
    if differ.any():
        d = j.loc[differ]
        out["first_differing_day"] = {t: str(pd.Timestamp(g["tournament_date"].min()).date())
                                      for t, g in d.groupby("tour")}
        out["differing_by_tour_season"] = {f"{t}|{y}": int(n) for (t, y), n in d.groupby(["tour", "year"]).size().items()}
    # the scale: the mean, over the reference's main-tour matches of each tour and season, of the two players' new
    # rating minus the frozen one, in system_new_arms.strength_centred's own arithmetic (pandas, the stored float32)
    jm = j[j["map_level"].isin(MAIN_LEVELS)]
    d = ((jm["elo_a_ret"] - jm["elo_a_ret_ref"]) + (jm["elo_b_ret"] - jm["elo_b_ret_ref"])) / 2.0
    shift = d.groupby([jm["tour"], jm["year"]]).mean()
    out["main_tour_shift_by_tour_season"] = {f"{t}|{y}": round(float(v), 4) for (t, y), v in shift.items() if v != 0}
    out["largest_main_tour_shift"] = float(shift.abs().max()) if len(shift) else 0.0
    out["scale_shift"] = bool(out["largest_main_tour_shift"] > SHIFT_TOL)
    return out, shift


def centre(s: pd.DataFrame, ref_path: Path, shift: pd.Series, m: pd.DataFrame | None = None) -> pd.DataFrame:
    """Option (c) of the study's addition 7 (system_new_arms.strength_centred, keep_reference): every match the frozen
    strength covers takes its frozen value; every other match takes the build's value less its tour-season shift (a
    season without main-tour matches takes the nearest season's, interpolated). m: Stage 0's matches."""
    m = stage0_matches() if m is None else m
    out = s.merge(m[["match_id", "tour", "year"]], on="match_id", how="left")
    if out[["tour", "year"]].isna().any().any():
        raise SystemExit("matches of the strength are missing from Stage 0")
    v = shift.reindex(pd.MultiIndex.from_frame(out[["tour", "year"]])).to_numpy(dtype="float64")
    if np.isnan(v).any():                                    # a season without main-tour matches: interpolated
        full = shift.groupby(level=0).apply(lambda x: x.droplevel(0).reindex(range(int(out["year"].min()),
                                                                                 int(out["year"].max()) + 1))
                                            .interpolate(limit_direction="both"))
        v = full.reindex(pd.MultiIndex.from_frame(out[["tour", "year"]])).to_numpy(dtype="float64")
    for c in ("elo_a_ret", "elo_b_ret"):
        out[c] = (out[c].to_numpy(dtype="float64") - v).astype(s[c].dtype)
    out = out[STRENGTH_COLS]
    ref = pd.read_parquet(ref_path, columns=STRENGTH_COLS)
    r = ref.assign(match_id=ref["match_id"].astype(str)).set_index("match_id")
    hit = out["match_id"].isin(r.index)
    for c in STRENGTH_COLS[1:]:
        out.loc[hit, c] = r[c].reindex(out.loc[hit, "match_id"]).to_numpy()
    return out


# ------------------------------------------------------------------------------------------------
# The build's config

def resolve(official_path: Path | str = OFFICIAL, root: Path = ROOT) -> Path:
    """The build config of this tree (module docstring). Returns its path."""
    cfg = official(official_path)
    out_dir = root / REL_BUILD
    out_dir.mkdir(parents=True, exist_ok=True)
    stage0 = root / STAGE0
    stage0_sha = sha256(stage0)
    ref_path = Path(cfg["strength"]["path"])
    if sha256(ref_path) != cfg["strength"]["sha256"]:
        raise SystemExit(f"{ref_path}: not the frozen strength the official config names")
    s = plain_strength(cfg["strength_k"])
    chk, shift = check(s, ref_path)
    rule = "plain"
    if chk["missing_ratings_in_build"]:
        raise SystemExit(f"the strength has missing ratings: {chk}")
    if chk["scale_shift"]:
        s = centre(s, ref_path, shift)
        rule = "re-centred (option c)"
    dst = out_dir / "strength_elo.parquet"
    s.to_parquet(dst, index=False, compression="zstd")
    h = sha256(dst)
    dst.with_suffix(".parquet.sha256").write_text(f"{h} *{dst.name}\n", encoding="utf-8")
    chk.update({"rule": rule, "shift_tolerance_elo": SHIFT_TOL, "strength_sha256": h, "stage0_sha256": stage0_sha,
                "k": cfg["strength_k"], "frozen_strength": cfg["strength"], "written_at": now()})
    (out_dir / "strength_check.json").write_text(json.dumps(chk, indent=1, default=str), encoding="utf-8")
    build = {k: v for k, v in cfg.items() if k not in ("strength", "record_dir", "written_at")}
    build.update({"strength": {"path": str(dst), "sha256": h}, "record_dir": str(out_dir / "layer_calls"),
                  "resolved": {"from": str(Path(official_path)), "from_sha256": sha256(official_path),
                               "tree": str(root), "stage0_sha256": stage0_sha, "strength_rule": rule,
                               "at": now()}})
    from src.eda.lower_level_evidence import level_layer_ios as LI
    LI.validate_config(dict(build), "build config")
    p = out_dir / "build_config.json"
    p.write_text(json.dumps(build, indent=1) + "\n", encoding="utf-8")
    p.with_suffix(".sha256").write_text(f"{sha256(p)} *{p.name}\n", encoding="utf-8")
    log(f"strength: {rule}; equal to the frozen on the reference's matches: {chk['equal_bit_for_bit']} "
        f"({chk['differing_matches']:,} differ; {chk['new_in_build']:,} new matches)")
    return p


def build_config(root: Path) -> Path:
    return Path(root) / REL_BUILD / "build_config.json"


def require_resolved(config_path, root: Path) -> dict:
    """Refuse a build config that is not this tree's, or was resolved on another Stage 0 (a candidate Stage 0
    installed after it, say): run --resolve again. Returns the config."""
    p = Path(config_path)
    if not p.exists():
        raise SystemExit(f"{p} does not exist: resolve the layer for this tree first (run_chain.py --prepare-layer)")
    side = p.with_suffix(".sha256")
    if not side.exists() or side.read_text(encoding="utf-8").split()[0] != sha256(p):
        raise SystemExit(f"{p}: its sha256 does not match {side}")
    cfg = json.loads(p.read_text(encoding="utf-8"))
    res = cfg.get("resolved") or {}
    if Path(res.get("tree", "")).resolve() != Path(root).resolve():
        raise SystemExit(f"{p} was resolved for {res.get('tree')}, not {root}")
    now_sha = sha256(Path(root) / STAGE0)
    if res.get("stage0_sha256") != now_sha:
        raise SystemExit(f"{p} was resolved on another Stage 0 (its {str(res.get('stage0_sha256'))[:12]}, now "
                         f"{now_sha[:12]}): resolve it again (run_chain.py --prepare-layer)")
    return cfg


def now() -> str:
    return pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--resolve", action="store_true", help="write this tree's build config (and its strength)")
    g.add_argument("--check", action="store_true", help="the strength check only; nothing written")
    ap.add_argument("--official", default=str(OFFICIAL))
    a = ap.parse_args()
    if a.check:
        cfg = official(a.official)
        chk, _ = check(plain_strength(cfg["strength_k"]), Path(cfg["strength"]["path"]))
        print(json.dumps(chk, indent=1, default=str))
        return 0
    print(resolve(a.official))
    return 0


if __name__ == "__main__":
    sys.exit(main())
