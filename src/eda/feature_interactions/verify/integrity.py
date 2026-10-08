"""Harness verifier, part 1: integrity of the screen's frame, the panel and the history (no result is related to any
feature here; a_won is read only to repeat the frame's own side-A agreement check).

Run: ./python.sh src/eda/feature_interactions/verify/integrity.py
Writes data/studies/feature_interactions/verify/integrity.json
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions.panel import panel, SOURCES  # noqa: E402

OUT = C.OUT / "verify"


def frame_checks(F: pd.DataFrame) -> dict:
    s0 = pd.read_parquet(S.PRE_REBUILD_STAGE0, columns=["match_id", "player_a_id", "a_won"])
    s0["match_id"] = s0["match_id"].astype(str)
    m = F[["match_id"]].merge(s0, on="match_id", how="left")
    return {"rows": int(len(F)), "by_window": F["window"].value_counts().to_dict(),
            "by_tour_window": {f"{t}|{w}": int(n) for (t, w), n in F.groupby(["tour", "window"]).size().items()},
            "seasons_by_tour": {t: sorted(F.loc[F["tour"] == t, "season"].unique().tolist()) for t in C.TOURS},
            "s0_missing": int(m["a_won"].isna().sum()), "player_id_missing": int(F["player_a_id"].isna().sum() +
                                                                                 F["player_b_id"].isna().sum()),
            "same_player_both_sides": int((F["player_a_id"].astype(str) == F["player_b_id"].astype(str)).sum()),
            "blocks": {w: int(F.loc[F["window"] == w, "block"].nunique()) for w in ("discovery", "replication")},
            "z_model_sd": float(F["z_model"].std()), "z_market_sd": float(F["z_market"].std()),
            "corr_model_market": float(np.corrcoef(F["z_model"], F["z_market"])[0, 1]),
            "match_id_unique": bool(F["match_id"].is_unique)}


def orientation(P: pd.DataFrame) -> dict:
    """Each per-player source's A - B against a model input built from the same quantity: correlation and the share
    of rows whose signs agree (a mis-oriented join shows as a share near 0.5 or a negative correlation)."""
    pairs = {"ios_srfO_hold": "in_iosO_hold", "ios_srfD_ace": "in_iosD_ace", "elo_R": "in_elo_overall",
             "sets_14d": "in_sets_14d", "age_pl": "in_age", "form_ace": "in_form_ace", "s3_serve": "in_ratings_iid",
             "ttt_mu": "in_elo_overall", "rank_points": "in_points_52w", "elo_NS": "in_elo_surf_offset"}
    out = {}
    for stem, ref in pairs.items():
        if f"{stem}_a" not in P.columns:
            out[stem] = "absent"
            continue
        d = P[f"{stem}_a"].astype(float) - P[f"{stem}_b"].astype(float)
        r = P[ref].astype(float)
        ok = np.isfinite(d) & np.isfinite(r) & (d != 0) & (r != 0)
        by = {}
        for s, g in P[ok].groupby("season"):
            dd, rr = d[g.index], r[g.index]
            by[int(s)] = round(float(np.corrcoef(dd, rr)[0, 1]), 3)
        out[stem] = {"ref": ref, "n": int(ok.sum()), "corr": round(float(np.corrcoef(d[ok], r[ok])[0, 1]), 4),
                     "sign_agree": round(float((np.sign(d[ok]) == np.sign(r[ok])).mean()), 4),
                     "max_abs_diff": float(np.nanmax(np.abs(d[ok] - r[ok]))), "corr_by_season": by}
    # odds: de-vigged average odds against in_odds_logit
    ia, ib = 1 / P["avg_a"].astype(float), 1 / P["avg_b"].astype(float)
    z = np.log(ia / ib)
    ok = np.isfinite(z) & np.isfinite(P["in_odds_logit"])
    out["avg_odds"] = {"n": int(ok.sum()), "max_abs_diff": float(np.abs(z[ok] - P.loc[ok, "in_odds_logit"]).max()),
                       "sign_agree": float((np.sign(z[ok]) == np.sign(P.loc[ok, "in_odds_logit"])).mean())}
    return out


def p3_orientation(P: pd.DataFrame) -> dict:
    t = pd.read_parquet(C.ROOT / "data/studies/data_continuity/rebuilds/2026-10-07T0005Z/replaced/data/studies/"
                        "match_timing/ttt_timed.parquet", columns=["match_id", "p_ttt_timed"])
    t["match_id"] = t["match_id"].astype(str)
    p = P[["match_id"]].merge(t, on="match_id", how="left")["p_ttt_timed"].to_numpy(float)
    z = np.log(p / (1 - p))
    ok = np.isfinite(z)
    pc = pd.read_parquet(SOURCES["pieces"], columns=["match_id", "S_a", "S_b", "R_a", "R_b"])
    pc["match_id"] = pc["match_id"].astype(str)
    q = P[["match_id"]].merge(pc, on="match_id", how="left")
    dR = (q["R_a"] - q["R_b"]).to_numpy(float)
    okr = np.isfinite(dR)
    return {"ttt_timed_coverage": float(ok.mean()),
            "ttt_timed_corr_odds": float(np.corrcoef(z[ok], P.loc[ok, "in_odds_logit"])[0, 1]),
            "ttt_timed_sign_agree_odds": float((np.sign(z[ok]) == np.sign(P.loc[ok, "in_odds_logit"])).mean()),
            "pieces_R_equals_elo_R": float(np.nanmax(np.abs(dR[okr] - (P["elo_R_a"] - P["elo_R_b"]).to_numpy()[okr])))}


def main() -> int:
    warnings.simplefilter("ignore")
    OUT.mkdir(parents=True, exist_ok=True)
    F = S.load(with_model=True)
    res = {"frame": frame_checks(F)}
    P = panel(max_season=2024)
    dup = P.columns[P.columns.duplicated()].tolist()
    pos = pd.Series(np.arange(len(P)), index=P["match_id"]).reindex(F["match_id"]).to_numpy()
    res["panel"] = {"rows": int(len(P)), "duplicated_columns": dup, "match_id_unique": bool(P["match_id"].is_unique),
                    "frame_rows_missing": int(np.isnan(pos).sum()),
                    "player_a_agrees": bool((P["player_a_id"].astype(str).to_numpy()[pos.astype(int)] ==
                                             F["player_a_id"].astype(str).to_numpy()).all()),
                    "memory_mb": round(P.memory_usage(deep=True).sum() / 2**20, 1)}
    res["orientation"] = orientation(P)
    res["p3"] = p3_orientation(P)
    C.write_json(OUT / "integrity.json", res)
    C.log("written integrity.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
