"""R2-measure: exposure of the 2025-2026 test matches to the documented Tennis My Life (TML) box-score faults, and the
clean sources on disk. COUNTS ONLY: reads provenance and dates (source, has_box, tournament date, match and player ids,
link-file ids, the overrides' match ids), never a box-score value, score or result.

Faults (docs/studies/data_continuity/README.md): women's aces and double faults from TML, Dec 2024 - Feb 2026; men's
Slam first serves from TML since about Aug 2025 (Wimbledon and the US Open 2026 replaced by the official feeds at the
6 Oct rebuild, 731 rows; the frozen model frame was built before that).
Writes data/studies/feature_interactions/round2/feasibility/r2_measure.json.
Run: ./python.sh src/eda/feature_interactions/round2/feasibility/r2_measure.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from src.eda.feature_interactions.round1.feasibility import base as B  # noqa: E402

OUT = B.C.OUT / "round2" / "feasibility"
S = B.ROOT / "data" / "studies"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
MCOLS = ["match_id", "tour", "level", "qualifying", "tournament_id", "tournament_name", "tournament_date", "source", "has_box"]


def window_counts(pid, day, flag, q_pid, q_day, w):
    """Per query (player, day): the sum of flag over that player's rows with day in [q_day - w, q_day)."""
    key = pid.astype(np.int64) * 100_000 + day.astype(np.int64)
    o = np.argsort(key, kind="stable")
    ks, cs = key[o], np.concatenate([[0.0], np.cumsum(flag[o])])
    qk = q_pid.astype(np.int64) * 100_000
    hi = np.searchsorted(ks, qk + q_day.astype(np.int64), side="left")
    lo = np.searchsorted(ks, qk + (q_day - w).astype(np.int64), side="left")
    return cs[hi] - cs[lo]


def main() -> int:
    m = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet", columns=MCOLS)
    d = pd.to_datetime(m["tournament_date"])
    tml = m["source"].eq("tml") & m["has_box"].fillna(False).astype(bool)
    fw = tml & m["tour"].eq("wta") & d.between("2024-12-01", "2026-02-28")
    fm = tml & m["tour"].eq("atp") & m["level"].eq("GS") & (d >= "2025-08-01")
    ov = set(pd.read_csv(S / "data_continuity" / "slam_box_overrides.csv", usecols=["stage0_match_id"])["stage0_match_id"])
    res = {"faulty_rows_women_ace_df": m[fw].groupby(["level", "qualifying"]).size().rename("n").reset_index().to_dict("records"),
           "faulty_rows_men_slam_first_serve": m[fm].assign(ov=m["match_id"].isin(ov)).groupby(["tournament_name", "qualifying", "ov"])
           .size().rename("n").reset_index().to_dict("records")}
    # clean sources linked on disk (pre-rebuild link files: ids only)
    links = {}
    for src in ("wta_api", "slam_feeds", "tdi", "sofascore"):
        f = OLD / "match_timing" / "links" / f"{src}.parquet"
        if f.exists():
            links[src] = set(pd.read_parquet(f, columns=["match_id"])["match_id"])
    for name, mask in (("women_ace_df", fw), ("men_slam_first_serve", fm)):
        ids = set(m.loc[mask, "match_id"])
        res[f"clean_links_{name}"] = {k: len(ids & v) for k, v in links.items()} | {"rows": len(ids)}
    # exposure of the test matches: faulty rows in each player's own box-score history before the match
    p = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_match_players.parquet", columns=["match_id", "player_id", "side"])
    p = p.merge(m[["match_id", "tournament_date", "has_box"]], on="match_id", how="left")
    pid = pd.factorize(p["player_id"])[0]
    day = (pd.to_datetime(p["tournament_date"]) - pd.Timestamp("1970-01-01")).dt.days.to_numpy()
    box = p["has_box"].fillna(False).to_numpy(dtype=bool).astype(float)
    flags = {"women_ace_df": p["match_id"].isin(set(m.loc[fw, "match_id"])).to_numpy(float),
             "men_slam_first_serve": p["match_id"].isin(set(m.loc[fm, "match_id"])).to_numpy(float),
             "men_slam_first_serve_after_rebuild": p["match_id"].isin(set(m.loc[fm, "match_id"]) - ov).to_numpy(float)}
    mf = pd.read_parquet(B.C.MODEL_FRAME, columns=["match_id", "season", "tour"])
    test = mf[mf["season"] >= 2025]
    q = p[p["match_id"].isin(set(test["match_id"]))]
    qi = q.index.to_numpy()
    for w, tag in ((728, "104w"), (42, "6w")):
        tot = window_counts(pid, day, box, pid[qi], day[qi], w)
        for name, fl in flags.items():
            cnt = window_counts(pid, day, fl, pid[qi], day[qi], w)
            share = np.where(tot > 0, cnt / np.maximum(tot, 1), 0.0)
            per = pd.DataFrame({"match_id": q["match_id"].to_numpy(), "any": cnt > 0, "share": share})
            agg = per.groupby("match_id").agg(any=("any", "max"), share=("share", "max")).reset_index()
            agg = agg.merge(test, on="match_id")
            res[f"exposure_{name}_{tag}"] = {t: {"matches": int(len(g)), "either_player_any": int(g["any"].sum()),
                                                  "either_player_share_gt5pct": int((g["share"] > 0.05).sum())}
                                              for t, g in agg.groupby("tour")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "r2_measure.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
