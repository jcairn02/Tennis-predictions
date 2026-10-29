"""Task 4's checks: what each arm of the depth count is made of, and whether the stopping-rule number moves under the
variants a reviewer would ask for. Reads no match result.

    1. composition: each target's 52-week count split by the source that gave each history match, with and without P9
       (headline population: tour-level and Challenger main draws, 2025-01-01 to 2026-10-18);
    2. "without P9" as the shot-level study had it on 2 Oct 2026: its own tables only (no AO/RG Infosys files, no
       2018-24 ATP files staged since, TDI only where that study's table held and linked the match);
    3. an upper bound for P9: its rally-carrying matches that link to no Stage 0 match (Challenger qualifying Stage 0
       lacks) added to the players' history with P9 only, placed at the event's Stage 0 date (else its first day) as a
       qualifying round, the players by the crosswalk;
    4. spot checks: a few players' counts at one target date, by source;
    5. overlaps: on matches P9 and another source both carry, P9's count against the other's, and both arms taking
       each match's largest count instead of the preferred source's.

Run:  ./python.sh src/eda/p9_point_details/build_depth_checks.py      (after build_depth.py; about a minute)
Writes data/studies/p9_point_details/build/depth_checks.json and depth_composition.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.p9_point_details import build_common as B  # noqa: E402
from src.eda.p9_point_details import build_depth as D  # noqa: E402

SHOT_LEVEL_ONLY = {"infosys", "sirgenkii", "slamtracker", "slam_pbp", "slam_tracking", "mcp", "tdi"}


def per_source_counts(ms: pd.DataFrame, allowed: set | None, exclude_p9: bool, tdi_keys: set | None = None):
    m = ms[ms["share"].fillna(0).ge(B.GATE) & ms["rp"].gt(0)].copy()
    if exclude_p9:
        m = m[m["source"].ne("p9")]
    if allowed is not None:
        m = m[m["source"].isin(allowed)]
    if tdi_keys is not None:
        m = m[~m["source"].eq("tdi") | m["src_key"].isin(tdi_keys)]
    m["pref"] = m["source"].map({s: i for i, s in enumerate(B.PREFERENCE)})
    c = m.sort_values(["match_id", "pref"]).drop_duplicates("match_id").set_index("match_id")
    return c[["source", "known_nondf"]]


def headline(t: pd.DataFrame, a: str, b: str) -> dict:
    h = t[t["headline_pop"]]
    return {"all": D.summarise(h, a, b), **{f"half_{k}": D.summarise(g, a, b) for k, g in h.groupby("half")},
            "tour_main": D.summarise(h[h["level"].ne("CH")], a, b), "ch_main": D.summarise(h[h["level"].eq("CH")], a, b)}


def main() -> int:
    ms = pd.read_parquet(B.OUT / "match_sources.parquet")
    rows = D.player_rows()
    res = {}
    # 1. composition
    w = per_source_counts(ms, None, False)
    wo = per_source_counts(ms, None, True)
    r = rows.copy()
    cols = []
    for arm, c in (("with", w), ("without", wo)):
        for s in B.PREFERENCE:
            col = f"{arm}__{s}"
            v = c["known_nondf"].where(c["source"].eq(s), 0)
            r[col] = r["match_id"].map(v).fillna(0)
            cols.append(col)
    sums = B.window_sums(r, cols)
    for col in cols:
        r[col] = sums[col].to_numpy()
    t = D.targets(r)
    h = t[t["headline_pop"]]
    comp = []
    for (grp, half), g in [(("all", "all"), h)] + [((("tour" if lv != "CH" else "CH"), hf), gg)
                                                    for (lv, hf), gg in h.assign(lv=np.where(h["level"].eq("CH"), "CH",
                                                                                             "tour"))
                                                    .groupby(["lv", "half"])]:
        for arm in ("with", "without"):
            tot = sum(g[f"{arm}__{s}"].sum() for s in B.PREFERENCE)
            for s in B.PREFERENCE:
                comp.append({"group": grp, "half": half, "arm": arm, "source": s,
                             "mean_points_per_player_match": float(g[f"{arm}__{s}"].mean()),
                             "share_of_arm": float(g[f"{arm}__{s}"].sum() / tot) if tot else np.nan})
    comp = pd.DataFrame(comp)
    comp.to_csv(B.OUT / "depth_composition.csv", index=False)
    res["composition_note"] = "depth_composition.csv: per group, half, arm and source, the mean 52-week count"
    # 2. without = the shot-level study's own tables as of 2 Oct 2026
    old = pd.read_parquet(B.SHOT_LEVEL / "stage0_source_matches.parquet", columns=["source", "key", "match_id"])
    tdi_old = set(old.loc[old["source"].eq("tdi") & old["match_id"].notna(), "key"])
    wo_old = per_source_counts(ms, SHOT_LEVEL_ONLY, True, tdi_keys=tdi_old)
    r2 = rows.copy()
    r2["n_with"] = r2["match_id"].map(w["known_nondf"]).fillna(0)
    r2["n_without"] = r2["match_id"].map(wo_old["known_nondf"]).fillna(0)
    s2 = B.window_sums(r2, ["n_with", "n_without"])
    r2["with_"], r2["without_"] = s2["n_with"].to_numpy(), s2["n_without"].to_numpy()
    res["without_as_shot_level_study_had_it"] = headline(D.targets(r2), "with_", "without_")
    # 3. upper bound: P9's unlinked rally-carrying matches added to the with arm
    links = pd.read_parquet(B.OUT / "links.parquet")
    xw = pd.read_parquet(B.OUT / "crosswalk.parquet").set_index("code")["pid"]
    un = links[links["source"].eq("p9") & links["carries"].fillna(False).astype(bool) & links["match_id_s0"].isna()]
    p = B.mb_convention(B.read_atp_points("p9"))
    p = p[p["key"].isin(set(un["key"]))]
    known = p[p["rally"] >= 1].groupby("key").size()
    s0 = B.stage0_men(["tournament_id", "tournament_date"], 2024)
    s0["tidp"] = B.tid_prefix(s0["tournament_id"])
    ev = s0.groupby("tidp").agg(tournament_id=("tournament_id", "first"), tournament_date=("tournament_date", "min"))
    extra = []
    for _, u in un.iterrows():
        n = int(known.get(u["key"], 0))
        e = ev.loc[u["tid"]] if u["tid"] in ev.index else None
        d = pd.Timestamp(e["tournament_date"]) if e is not None else pd.Timestamp(u["start"])
        tid = e["tournament_id"] if e is not None else u["tid"]
        for c in (u["c1"], u["c2"]):
            pid = xw.get(c)
            if pid is None:
                continue
            extra.append({"match_id": "p9_unlinked|" + u["key"], "player_id": pid, "tournament_date": d,
                          "tournament_id": tid, "round_order": 0, "level": "CH", "qualifying": True,
                          "status": "unlinked", "n_with": n, "n_without": 0})
    extra = pd.DataFrame(extra)
    r3 = rows.copy()
    r3["n_with"] = r3["match_id"].map(w["known_nondf"]).fillna(0)
    r3["n_without"] = r3["match_id"].map(wo["known_nondf"]).fillna(0)
    r3 = pd.concat([r3, extra], ignore_index=True)
    s3 = B.window_sums(r3, ["n_with", "n_without"])
    r3["with_"], r3["without_"] = s3["n_with"].to_numpy(), s3["n_without"].to_numpy()
    res["upper_bound_with_unlinked_p9"] = {"unlinked_rally_matches_added": int(len(un)),
                                           "player_rows_added": int(len(extra)),
                                           **headline(D.targets(r3), "with_", "without_")}
    # 4. spot checks at one date: the five players with the most tour main-draw matches in 2026H1
    tm = t[t["headline_pop"] & t["level"].ne("CH") & t["half"].eq("2026H1")]
    top = tm["player_id"].value_counts().head(3).index.tolist()
    ch = t[t["headline_pop"] & t["level"].eq("CH") & t["half"].eq("2026H1")]
    top += ch["player_id"].value_counts().head(2).index.tolist()
    spots = []
    for pid in top:
        g = t[t["player_id"].eq(pid) & t["headline_pop"]].sort_values("tournament_date")
        g = g[g["tournament_date"] >= pd.Timestamp("2026-05-01")].head(1)
        if g.empty:
            continue
        row = g.iloc[0]
        rec = {"player_id": pid, "target_match": row["match_id"], "date": str(row["tournament_date"].date())}
        for arm in ("with", "without"):
            rec[arm] = {s: float(row[f"{arm}__{s}"]) for s in B.PREFERENCE if row[f"{arm}__{s}"] > 0}
        spots.append(rec)
    res["spot_checks"] = spots
    # 5. overlaps: P9's count against the other source's on matches both carry, and the arms with the largest count
    car = ms[ms["share"].fillna(0).ge(B.GATE) & ms["rp"].gt(0)]
    p9c = car[car["source"].eq("p9")].set_index("match_id")["known_nondf"]
    oth = car[car["source"].ne("p9")].groupby("match_id")["known_nondf"].max()
    both = p9c.index.intersection(oth.index)
    res["overlap_p9_vs_other"] = {"matches": int(len(both)),
                                  "p9_mean": float(p9c.loc[both].mean()), "other_max_mean": float(oth.loc[both].mean()),
                                  "p9_lower_share": float((p9c.loc[both] < oth.loc[both]).mean()),
                                  "by_other_source": car[car["match_id"].isin(both) & car["source"].ne("p9")]
                                  .groupby("source")["match_id"].nunique().to_dict()}
    r5 = rows.copy()
    r5["n_with"] = r5["match_id"].map(car.groupby("match_id")["known_nondf"].max()).fillna(0)
    r5["n_without"] = r5["match_id"].map(oth).fillna(0)
    s5 = B.window_sums(r5, ["n_with", "n_without"])
    r5["with_"], r5["without_"] = s5["n_with"].to_numpy(), s5["n_without"].to_numpy()
    res["largest_count_per_match"] = headline(D.targets(r5), "with_", "without_")
    B.log(f"overlap: {res['overlap_p9_vs_other']}")
    B.write_json(B.OUT / "depth_checks.json", res)
    for k in ("without_as_shot_level_study_had_it", "upper_bound_with_unlinked_p9", "largest_count_per_match"):
        a = res[k]["all"]
        B.log(f"{k}: median ratio {a['median_ratio']:.3f}, excluding 0/0 {a['median_ratio_excluding_zero_both']:.3f}, "
              f"ratio of medians {a['ratio_of_medians']:.3f}; tour main {res[k]['tour_main']['median_ratio']:.3f}, "
              f"CH main {res[k]['ch_main']['median_ratio']:.3f}")
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        x = comp[comp["group"].isin(["all", "tour", "CH"])].pivot_table(
            index=["group", "half", "source"], columns="arm", values="mean_points_per_player_match").round(0)
        print(x[(x["with"] > 0) | (x["without"] > 0)].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
