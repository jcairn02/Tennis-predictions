"""Step 5: the instance's inputs for the study's qualifying matches, built with the instance's own code on its build
tree's tables, and gated by exact equality with the instance's own frame on its rows.

The instance template_2026-10-21b was built in the tree C:/Users/zerom/tnr_tpl1021: its chain frame
(model_frame_chain.parquet, 58 inputs, the books' average as the odds input) holds main-tour matches with a closing price
only, but the tables under it cover the whole pool (main tour, tour and Slam qualifying, Challengers), so the chain's
recipes give every pool match the same inputs (as the event-levels study did on the 30 Sep snapshot):
    31 inputs   tabpfn_thinking/build_frame.py's recipes (Stage 4 and the UFC-ideas Stage D tables; the match context:
                tour, surface, level, indoor by the indoor rule, scheduled best-of, round), with ios_points_short from
                the leak-proof table (tabpfn_leakproof's REPLACED: its column ios_short)
    21 inputs   the surface IOS profile (surface_ios/arms.recipe on surface_features.parquet: iosO, iosD, prod)
    6 inputs    the offset Elo (surface_elo_pieces/arms.new_inputs on pieces.parquet)
The tree's src/ is put first on sys.path, so every recipe and path is the tree's: the code that built the instance
(identical, file for file, to the repository's on 22 Oct 2026) and the tables it was built on.

Qualifying rows (the study's population, common.qualifying_matches on the tree's Stage 0):
    level    TQ 6, GSQ 7 (the event-levels study's codes; the model's are GS 0 .. T250 4)
    round    Stage 0's round order (Q1 1, Q2 2, Q3 3)
    best_of  3; 5 where Stage 0 records 5 for a men's Slam qualifying match (event metadata, never the score)
    indoor   the indoor rule (indoor_fill/status.py), which reads every match of a tennis-data level, qualifying
             included, and fills a qualifying match from its event
    odds     left missing here (no tennis-data price exists); prices.py supplies OddsTrader's closes

The gate (pre-registered): on every row of the instance's chain frame, each of its 58 inputs equals the rebuilt value
(same missing cells), the labels and the debut flags are equal, and swapping A and B twice gives the frame back.
Otherwise nothing is written.

Writes data/studies/qualifying_targets/frame.parquet (the qualifying rows: identifiers, label, debut flag, the 57
template inputs as in_<name>, in_odds_logit missing) and frame_manifest.json.
Run: ./python.sh src/eda/qualifying_targets/frame.py
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
TREE = Path("C:/Users/zerom/tnr_tpl1021")
sys.path.insert(0, str(TREE))                    # the instance's own code and tables

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.special import logit  # noqa: E402

from src.eda.indoor_fill import status as IF  # noqa: E402
from src.eda.surface_elo_pieces import arms as EA  # noqa: E402
from src.eda.surface_ios import arms as SI  # noqa: E402
from src.eda.tabpfn_leakproof import common as LP  # noqa: E402
from src.eda.tabpfn_thinking import build_frame as BF  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402


def _common():
    spec = importlib.util.spec_from_file_location("qualifying_targets_common",
                                                  REPO / "src" / "eda" / "qualifying_targets" / "common.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _common()
POOL_COLS = ["match_id", "tour", "year", "group", "status", "a_won", "p_mkt"]
MATCH_COLS = ["match_id", "tournament_name", "tournament_id", "tournament_date", "surface", "indoor", "round",
              "round_order", "level", "qualifying", "best_of", "nonstandard_format", "player_a_id", "player_b_id"]
SPROF = [f"{k}_{s}" for k in ("iosO", "iosD", "prod") for s in T.IOS_STATS]
SURFACE_FEATURES = TREE / "data" / "studies" / "surface_ios" / "surface_features.parquet"
PIECES = TREE / "data" / "studies" / "surface_elo_pieces" / "pieces.parquet"


def tree_code() -> dict:
    mods = {"tabpfn_thinking.common": T, "tabpfn_thinking.build_frame": BF, "surface_ios.arms": SI,
            "surface_elo_pieces.arms": EA, "indoor_fill.status": IF, "tabpfn_leakproof.common": LP}
    out = {}
    for name, mod in mods.items():
        path = Path(mod.__file__).resolve()
        if TREE.resolve() not in path.parents:
            raise SystemExit(f"{name} was imported from {path}, not from the tree")
        rel = path.relative_to(TREE.resolve())
        out[name] = {"tree": str(path), "same_as_repository": (REPO / rel).read_bytes() == path.read_bytes()}
    return out


def pool_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """(pool rows with the match facts, the 58 inputs per pool row, info) on the tree's tables."""
    pool = pd.read_parquet(T.SOURCES["stage4"], columns=POOL_COLS)
    tables = {}
    for key in ("stageD", "stageD_profile"):
        cols = sorted({c for f in T.FEATURES if f["src"] == key
                       for c in (f["col"].values() if isinstance(f["col"], dict) else [f["col"]])})
        t = pd.read_parquet(T.SOURCES[key], columns=["match_id"] + cols)
        if not np.array_equal(t["match_id"].to_numpy(), pool["match_id"].to_numpy()):
            raise SystemExit(f"{key} is not in Stage 4's order")
        tables[key] = t
    m = pd.read_parquet(T.SOURCES["stage0_matches"], columns=MATCH_COLS)
    m["match_id"] = m["match_id"].astype(str)
    pool["match_id"] = pool["match_id"].astype(str)
    m = m.set_index("match_id").reindex(pool["match_id"]).reset_index()
    tour = pool["tour"].to_numpy()
    group = pool["group"].to_numpy()
    X = pd.DataFrame(index=pool.index)
    for spec in T.FEATURES:                                   # build_frame.build's recipes, every pool row
        name, src, col = spec["name"], spec["src"], spec["col"]
        if src in tables:
            if isinstance(col, dict):
                v = np.full(len(pool), np.nan)
                for t_, c in col.items():
                    v = np.where(tour == t_, tables[src][c].to_numpy(dtype="float64"), v)
                X[name] = v
            else:
                X[name] = tables[src][col].to_numpy(dtype="float64")
    pm = pool["p_mkt"].to_numpy(dtype="float64")
    X["odds_logit"] = np.where(np.isfinite(pm), logit(np.clip(pm, T.EPS, 1 - T.EPS)), np.nan)
    X["tour"] = pool["tour"].map(T.CODES["tour"]).astype("float64").to_numpy()
    X["surface"] = m["surface"].map(T.CODES["surface"]).astype("float64").to_numpy()
    codes = {**T.CODES["level"], **C.LEVEL_CODES}
    X["level"] = pd.Series(group).map(codes).astype("float64").to_numpy()
    f = pd.DataFrame({"match_id": pool["match_id"], "tour": pool["tour"], "group": pool["group"]})
    X["indoor"], indoor_src, indoor_info = BF.indoor_codes(f, m, False)
    meta = m.assign(tour=pool["tour"], year=pool["year"], group=pool["group"])
    bo, supported = BF.scheduled_best_of(meta)
    recorded = m["best_of"].astype("float64").to_numpy()
    bo = np.where((tour == "atp") & (group == "GSQ") & (recorded == 5), 5.0, bo)
    X["best_of"] = bo
    X["round"] = m["round_order"].astype("float64").to_numpy()
    lp = pd.read_parquet(LP.LEAKPROOF, columns=["match_id", LP.REPLACED["ios_points_short"]])
    lp["match_id"] = lp["match_id"].astype(str)
    lp = pool[["match_id"]].merge(lp, on="match_id", how="left", validate="one_to_one")
    X["ios_points_short"] = lp[LP.REPLACED["ios_points_short"]].to_numpy(dtype="float64")
    sf = pd.read_parquet(SURFACE_FEATURES)
    sf["match_id"] = sf["match_id"].astype(str)
    sf = pool[["match_id"]].merge(sf, on="match_id", how="left", validate="one_to_one")
    for n in SPROF:
        X[n] = SI.recipe(n, sf)                               # the surface profile replaces the thinking frame's
    pieces = pd.read_parquet(PIECES)
    pieces["match_id"] = pieces["match_id"].astype(str)
    pieces = pool[["match_id"]].merge(pieces, on="match_id", how="left", validate="one_to_one")
    el = EA.new_inputs(pieces).reset_index(drop=True)
    for c in el.columns:
        X[c] = el[c].to_numpy(dtype="float64")
    facts = pool.assign(tournament_date=pd.to_datetime(m["tournament_date"]).to_numpy(),
                        tournament_name=m["tournament_name"].to_numpy(), round_name=m["round"].to_numpy(),
                        event_level=m["level"].to_numpy(), qualifying=m["qualifying"].to_numpy(),
                        nonstandard=m["nonstandard_format"].fillna(False).astype(bool).to_numpy(),
                        player_a_id=m["player_a_id"].to_numpy(), player_b_id=m["player_b_id"].to_numpy(),
                        format_supported=supported, indoor_source=np.asarray(indoor_src, dtype=object))
    return facts, X, {"indoor": indoor_info}


def debut_flags(rows: pd.DataFrame) -> np.ndarray:
    """surface_elo_pieces/build_frames.debut_season's rule on the tree's Stage 0: a player's first Stage 0 match (any
    level, since 2010) falls in this match's season."""
    m = pd.read_parquet(T.SOURCES["stage0_matches"], columns=["match_id", "tour", "year", "player_a_id", "player_b_id"])
    first = pd.concat([m[["tour", "player_a_id", "year"]].rename(columns={"player_a_id": "pid"}),
                       m[["tour", "player_b_id", "year"]].rename(columns={"player_b_id": "pid"})]) \
        .groupby(["tour", "pid"])["year"].min()
    fa = first.reindex(pd.MultiIndex.from_arrays([rows["tour"], rows["player_a_id"]])).to_numpy()
    fb = first.reindex(pd.MultiIndex.from_arrays([rows["tour"], rows["player_b_id"]])).to_numpy()
    s = rows["season"].to_numpy()
    return (fa == s) | (fb == s)


def flip(X: pd.DataFrame, kinds: dict) -> pd.DataFrame:
    """A and B swapped: differences negated, pair inputs exchanged, context kept (serve_speed_tabpfn/arms.flip's rule)."""
    out = X.copy()
    for n, k in kinds.items():
        if k == "diff":
            out[n] = -X[n]
        elif k == "pair":
            stem, side = n.rsplit("_", 1)
            out[n] = X[f"{stem}_{'b' if side == 'a' else 'a'}"]
    return out


def build() -> tuple[pd.DataFrame, dict]:
    code = tree_code()
    chain_meta = json.loads((C.INSTANCE / "model_inputs_chain.json").read_text(encoding="utf-8"))
    names58 = [d["name"] for d in chain_meta["inputs"]]
    kinds = {d["name"]: d["kind"] for d in chain_meta["inputs"]}
    tmpl_meta = json.loads((C.INSTANCE / "model_inputs.json").read_text(encoding="utf-8"))
    names57 = [d["name"] for d in tmpl_meta["inputs"]]
    if set(names58) - set(names57) != {"ios_points_short"} or not set(names57) <= set(names58):
        raise SystemExit("the template's input list is not the chain's without ios_points_short")
    facts, X, info = pool_inputs()
    missing = [n for n in names58 if n not in X.columns]
    if missing:
        raise SystemExit(f"recipes missing for {missing}")
    facts["season"] = facts["year"].astype(int)
    # ---- the gate: the instance's chain frame, row for row and input for input
    chain = pd.read_parquet(C.INSTANCE / "model_frame_chain.parquet")
    chain["match_id"] = chain["match_id"].astype(str)
    pos = pd.Series(np.arange(len(facts)), index=facts["match_id"].to_numpy())
    if chain["match_id"].map(pos).isna().any():
        raise SystemExit("chain-frame matches missing from the tree's Stage 4 pool")
    idx = chain["match_id"].map(pos).to_numpy(int)
    bad = {}
    for n in names58:
        a = X[n].to_numpy(dtype="float64")[idx]
        b = chain[f"in_{n}"].to_numpy(dtype="float64")
        if not np.array_equal(a, b, equal_nan=True):
            both = np.isfinite(a) & np.isfinite(b)
            bad[n] = {"differ": int((both & (a != b)).sum()), "missing_differs": int((np.isnan(a) != np.isnan(b)).sum()),
                      "max_abs": float(np.nanmax(np.abs(a - b))) if both.any() else None}
    labels_equal = bool(np.array_equal(facts["a_won"].to_numpy(bool)[idx], chain["a_won"].to_numpy(bool)))
    debut_chain = debut_flags(facts.iloc[idx].assign(season=chain["season"].to_numpy()))
    debut_equal = bool(np.array_equal(debut_chain, chain["debut_season"].to_numpy(bool)))
    Xc = X.iloc[idx][names58].reset_index(drop=True)
    involution = bool(np.allclose(flip(flip(Xc, kinds), kinds).to_numpy(), Xc.to_numpy(), equal_nan=True))
    gate = {"chain_rows": int(len(chain)), "inputs_checked": len(names58), "inputs_differing": bad,
            "labels_equal": labels_equal, "debut_equal": debut_equal, "flip_is_an_involution": involution}
    gate["passed"] = not bad and labels_equal and debut_equal and involution
    if not gate["passed"]:
        C.write_json(C.OUT / "frame_gate_failed.json", gate)
        raise SystemExit(f"the gate failed: {json.dumps(gate, default=str)[:2000]}")
    # ---- the qualifying rows
    q = C.qualifying_matches(T.SOURCES["stage0_matches"])
    if q["match_id"].map(pos).isna().any():
        raise SystemExit(f"{int(q['match_id'].map(pos).isna().sum())} qualifying matches are not in Stage 4's pool")
    qi = q["match_id"].map(pos).to_numpy(int)
    fq = facts.iloc[qi].reset_index(drop=True)
    if not fq["group"].isin(C.QUAL_GROUPS).all():
        raise SystemExit("a qualifying match outside Stage 4's TQ / GSQ groups")
    out = pd.DataFrame({"match_id": fq["match_id"], "tour": fq["tour"], "season": fq["season"],
                        "tournament_date": fq["tournament_date"], "tournament_name": fq["tournament_name"],
                        "kind": fq["group"], "event_level": fq["event_level"], "round": fq["round_name"],
                        "status": fq["status"], "a_won": fq["a_won"].astype(bool),
                        "player_a_id": fq["player_a_id"], "player_b_id": fq["player_b_id"],
                        "format_supported": fq["format_supported"], "indoor_source": fq["indoor_source"]})
    out["debut_season"] = debut_flags(out)
    Xq = X.iloc[qi].reset_index(drop=True)
    for n in names57:
        out[f"in_{n}"] = Xq[n].to_numpy(dtype="float64")
    if np.isfinite(out["in_odds_logit"]).any():
        raise SystemExit("a qualifying row has a tennis-data price: unexpected")
    cov = {n: float(np.isfinite(out[f"in_{n}"]).mean()) for n in names57}
    meta = {"code": code, "gate": gate, "indoor": info["indoor"],
            "rows": out.groupby(["tour", "kind", "season"]).size().rename("matches").reset_index().to_dict("records"),
            "unsupported_format": int((~out["format_supported"]).sum()),
            "coverage_qualifying": cov,
            "coverage_main_rows_of_chain": {n: float(np.isfinite(chain[f"in_{n}"]).mean()) for n in names57},
            "level_codes": out.groupby("kind")["in_level"].unique().map(list).to_dict(),
            "round_codes": out.groupby("round")["in_round"].unique().map(list).to_dict(),
            "best_of": out.groupby(["tour", "kind"])["in_best_of"].value_counts().rename("n").reset_index()
                          .to_dict("records"),
            "indoor_sources": out.groupby(["tour", "indoor_source"]).size().rename("n").reset_index()
                                 .to_dict("records"),
            "debut_share": float(out["debut_season"].mean()),
            "sources": {k: str(v) for k, v in T.SOURCES.items()} | {"surface_features": str(SURFACE_FEATURES),
                                                                    "pieces": str(PIECES),
                                                                    "leakproof": str(LP.LEAKPROOF)},
            "names57": names57}
    return out, meta


def main() -> int:
    out, meta = build()
    C.OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(C.FRAME, index=False)
    meta["frame_sha256"] = C.sha256_file(C.FRAME)
    meta["generated_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    C.write_json(C.OUT / "frame_manifest.json", meta)
    C.log(f"gate passed on {meta['gate']['chain_rows']:,} chain rows x {meta['gate']['inputs_checked']} inputs; "
          f"{len(out):,} qualifying rows written")
    low = {k: round(v, 3) for k, v in meta["coverage_qualifying"].items() if v < 0.9}
    C.log(f"qualifying coverage below 90%: {low}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
