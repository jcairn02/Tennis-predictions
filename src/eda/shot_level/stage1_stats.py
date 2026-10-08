"""Stage 1, part 3: the per-player, per-match shot-level statistics (src/eda/shot_level/stats.py), one table for all
sources, keyed by the predictability diagnostic's Stage 0 match and player.

For each source, its points (stage1_points_<source>.parquet) are turned to Stage 0's sides through the Stage 0 link
(stage0_source_matches.parquet: match_id and a1), and every statistic is computed per match and side. Where several
sources hold one match, each statistic is taken from the first source in PRIORITY that carries it for that match: the
volunteer charts (the most detailed record), then Hawk-Eye's copy at the Slams, the Slam feeds (SlamTracker, then
Sackmann's copies), Infosys, SirGenkii, TDI and the Australian Open's match centre. The source used is kept per statistic.

Nothing here reads who won a match beyond the point winners the statistics are made of.

Run:  ./python.sh src/eda/shot_level/stage1_stats.py   (about a minute)
Writes data/studies/shot_level/:
    stage1_match_stats.parquet   one row per Stage 0 player-match with any statistic: match_id, player_id, side, and per
                                 statistic <stat>_n, <stat>_d (numerator, denominator) and <stat>_src (the source used)
    stage1_stats_summary.json    per statistic: matches carrying it by tour and year, the pooled rate, the sources used
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402

PRIORITY = ["mcp", "slam_tracking", "slamtracker", "slam_pbp", "infosys", "sirgenkii", "tdi", "ausopen"]
SRC_CODE = {s: i + 1 for i, s in enumerate(PRIORITY)}
EXTRA = ["spd1_sq", "spd2_sq"]


def oriented(name: str, links: pd.DataFrame) -> pd.DataFrame:
    p = pd.read_parquet(S.OUT / f"stage1_points_{name}.parquet")
    lk = links[links["source"].eq(name) & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    # a Stage 0 match linked twice from one source (rare): keep the copy with the most points
    sizes = p.groupby("key").size().rename("pts")
    lk = lk.join(sizes, on="key").sort_values("pts", ascending=False).drop_duplicates("match_id")
    p = p.merge(lk[["key", "match_id", "a1"]], on="key", how="inner")
    a1 = p["a1"].astype(bool).to_numpy()
    for c in ("server", "winner", "ender"):
        v = p[c].to_numpy()
        p[c] = np.where(v == 0, 0, np.where(a1, v, 3 - v)).astype("int8")
    n1, n2 = p["net1"].to_numpy(), p["net2"].to_numpy()
    p["net1"], p["net2"] = np.where(a1, n1, n2), np.where(a1, n2, n1)
    return p.drop(columns=["a1"])


def build() -> pd.DataFrame:
    links = pd.read_parquet(S.OUT / "stage0_source_matches.parquet", columns=["source", "key", "match_id", "a1"])
    parts = []
    for name in PRIORITY:
        path = S.OUT / f"stage1_points_{name}.parquet"
        if not path.exists():
            continue
        p = oriented(name, links)
        ms = T.match_stats(p)
        sq = T.sequence_stats(p)
        st = ms.merge(sq, on=["match_id", "side"], how="left")
        st["source"] = name
        S.log(f"  {name}: {p['match_id'].nunique()} matches, sequence complete in {sq['match_id'].nunique()}")
        parts.append(st)
    allst = pd.concat(parts, ignore_index=True)
    allst["rank"] = allst["source"].map(SRC_CODE)
    out = allst[["match_id", "side"]].drop_duplicates().reset_index(drop=True)
    for s in T.ALL_STATS + EXTRA:
        d = allst[[f"{s}_d"]].fillna(0)
        # a match carries the statistic from a source when either side has a denominator there
        carry = allst.assign(_d=d[f"{s}_d"].to_numpy()).groupby(["match_id", "source"])["_d"].transform("max") > 0
        cand = allst[carry][["match_id", "side", "rank", "source", f"{s}_n", f"{s}_d"]]
        best = cand.groupby("match_id")["rank"].transform("min")
        pick = cand[cand["rank"].to_numpy() == best.to_numpy()].drop_duplicates(["match_id", "side"])
        pick = pick.rename(columns={"source": f"{s}_src"})[["match_id", "side", f"{s}_n", f"{s}_d", f"{s}_src"]]
        out = out.merge(pick, on=["match_id", "side"], how="left")
    for s in T.ALL_STATS + EXTRA:
        out[f"{s}_n"] = out[f"{s}_n"].fillna(0.0).astype("float64")
        out[f"{s}_d"] = out[f"{s}_d"].fillna(0.0).astype("float64")
    # Stage 0's player for each side
    m = C.load_matches(["match_id", "tour", "year", "player_a_id", "player_b_id"])
    out = out.merge(m, on="match_id", how="left")
    out["player_id"] = np.where(out["side"].eq("A"), out["player_a_id"], out["player_b_id"])
    return out.drop(columns=["player_a_id", "player_b_id"])


def summary(st: pd.DataFrame) -> dict:
    res = {}
    for s in T.ALL_STATS:
        has = st[f"{s}_d"] > 0
        sub = st[has]
        by = sub.drop_duplicates("match_id").groupby(["tour", "year"]).size()
        rate = float(sub[f"{s}_n"].sum() / sub[f"{s}_d"].sum()) if len(sub) else None
        res[s] = {"family": T.FAMILY_OF[s], "matches": int(sub["match_id"].nunique()),
                  "by_tour": {t: int(sub.loc[sub["tour"].eq(t), "match_id"].nunique()) for t in C.TOURS},
                  "by_tour_year": {f"{t}|{y}": int(v) for (t, y), v in by.items()},
                  "pooled": rate, "mean_denominator": float(sub[f"{s}_d"].mean()) if len(sub) else None,
                  "sources": sub.drop_duplicates("match_id")[f"{s}_src"].value_counts().to_dict()}
    return res


def main() -> int:
    S.log("per-match statistics by source")
    st = build()
    st.to_parquet(S.OUT / "stage1_match_stats.parquet", index=False)
    summ = summary(st)
    summ["_totals"] = {"player_match_rows": int(len(st)), "matches": int(st["match_id"].nunique())}
    (S.OUT / "stage1_stats_summary.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8")
    S.log(f"wrote stage1_match_stats.parquet ({len(st)} player-match rows, {st['match_id'].nunique()} matches)")
    for s, r in summ.items():
        if s.startswith("_"):
            continue
        print(f"{s:18s} {r['family']:9s} matches {r['matches']:6d} (atp {r['by_tour']['atp']:5d}, wta {r['by_tour']['wta']:5d})"
              f"  pooled {r['pooled'] if r['pooled'] is None else round(r['pooled'], 4)}  mean d {r['mean_denominator'] and round(r['mean_denominator'], 1)}"
              f"  {r['sources']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
