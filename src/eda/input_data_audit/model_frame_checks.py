"""The 58 inputs of the current best model, column by column, and how far each box-score fault reaches them.

Reads data/studies/surface_rating_race/model/model_frame.parquet (built on the Stage 0 tables of 30 Sep 2026) and both
Stage 0 snapshots. Side A is random, so every A - B input should have mean about 0 and a spread that moves smoothly
from season to season; a break in one season's spread, missing share, share of exact zeros or link to the odds is the
column-level analogue of "one year reads 4 km/h high".

Writes data/studies/input_data_audit/:
    frame_season_profile.csv   per input and tour-season: SD, missing share, exact-zero share, correlation with the
                               closing odds' log-odds and with the label
    frame_split_ids_<snap>.csv players whose history is split across two ids (an id first seen after Sackmann's end,
                               25 May 2026, whose name already has matches under another id), with model-frame matches
    frame_context_changes.csv  events whose surface, level or indoor code changes between seasons
    frame_missing_age.csv      model-frame matches with age missing, by event
    frame_fault_exposure.csv   model-frame matches (train / test) where a player had a match hit by each box-score
                               fault in the previous 28 days (the two-week form inputs) or 365 days (long memory)
    frame_product_drift.csv    per IOS statistic and tour-season: the mean surface-IOS level of the model's players
                               and the SD of prod_<s> as built and with each season's mean level removed
    frame_summary.json
Run after box_checks.py: ./python.sh src/eda/input_data_audit/model_frame_checks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.input_data_audit import common as C  # noqa: E402

SPLICE = pd.Timestamp("2026-05-25")
CONTEXT = ["in_tour", "in_surface", "in_level", "in_indoor", "in_best_of", "in_round"]


def season_profile(f: pd.DataFrame, summary: dict) -> None:
    cols = [c for c in f.columns if c.startswith("in_") and c not in CONTEXT]
    y = f["a_won"].astype(float)
    rows = []
    for (tour, season), g in f.groupby(["tour", "season"]):
        for c in cols:
            v = g[c]
            rows.append({"input": c[3:], "tour": tour, "season": season, "matches": len(g), "sd": v.std(),
                         "missing": v.isna().mean(), "exact_zero": (v == 0).mean(),
                         "corr_odds": v.corr(g["in_odds_logit"]), "corr_label": v.corr(y.loc[g.index])})
    p = pd.DataFrame(rows)
    p.to_csv(C.OUT / "frame_season_profile.csv", index=False)
    # breaks: a season whose SD sits more than 25% from the median of the same tour's other seasons
    p["sd_vs_median"] = p["sd"] / p.groupby(["input", "tour"])["sd"].transform("median") - 1
    flagged = p[(p["sd_vs_median"].abs() > 0.25) & (p["missing"] < 0.5)]
    summary["sd_breaks"] = flagged.sort_values("sd_vs_median").apply(
        lambda r: f"{r['input']} {r['tour']} {r['season']}: SD {r['sd']:.3f} ({100 * r['sd_vs_median']:+.0f}% vs median)", axis=1).tolist()
    summary["missing_over_5pct"] = p[p["missing"] > 0.05].apply(
        lambda r: f"{r['input']} {r['tour']} {r['season']}: {100 * r['missing']:.1f}%", axis=1).tolist()
    summary["exact_zero_in_ratings"] = p[p["input"].isin(["elo_overall", "elo_surf_offset", "ratings_iid", "elo_games"])
                                         & (p["exact_zero"] > 0)].apply(
        lambda r: f"{r['input']} {r['tour']} {r['season']}: {100 * r['exact_zero']:.1f}%", axis=1).tolist()


def split_ids(snap: str, f: pd.DataFrame, summary: dict) -> None:
    folder = C.SNAPSHOTS[snap]
    p = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name"])
    m = pd.read_parquet(folder / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date", "tournament_name"])
    d = p.merge(m, on="match_id")
    d["key"] = d["player_name"].map(C.name_key)
    ids = d.groupby(["tour", "key", "player_id"]).agg(matches=("match_id", "size"), first=("tournament_date", "min"),
                                                      last=("tournament_date", "max")).reset_index()
    rows = []
    for (tour, key), g in ids.groupby(["tour", "key"]):
        if len(g) < 2:
            continue
        g = g.sort_values("first")
        for i in range(1, len(g)):
            new = g.iloc[i]
            older = g[(g["first"] < new["first"]) & (g.index != g.index[i])]
            if new["first"] < SPLICE or older.empty:
                continue
            main = older.sort_values("matches").iloc[-1]
            rows.append({"tour": tour, "name_key": key, "established_id": main["player_id"],
                         "established_matches": int(main["matches"]), "new_id": new["player_id"],
                         "new_id_matches": int(new["matches"]), "new_id_first": new["first"], "new_id_last": new["last"]})
    s = pd.DataFrame(rows)
    in_frame = d[d["match_id"].isin(f["match_id"]) & d["player_id"].isin(set(s["new_id"]))] if len(s) else d.iloc[:0]
    s["model_frame_matches"] = s["new_id"].map(in_frame.groupby("player_id")["match_id"].nunique()).fillna(0).astype(int)
    s.sort_values(["model_frame_matches", "established_matches"], ascending=False).to_csv(
        C.OUT / f"frame_split_ids_{snap}.csv", index=False)
    hit = f[f["match_id"].isin(in_frame["match_id"])]
    summary[f"split_ids_{snap}"] = {
        "pairs": int(len(s)), "pairs_by_tour": s["tour"].value_counts().to_dict(),
        "model_frame_matches_with_a_split_player": int(hit["match_id"].nunique()),
        "by_event": d[d["match_id"].isin(hit["match_id"])].drop_duplicates("match_id")["tournament_name"].value_counts().to_dict()}


def context_changes(f: pd.DataFrame, m: pd.DataFrame) -> None:
    x = f.merge(m[["match_id", "tournament_name"]], on="match_id", how="left")
    x["event"] = x["tour"] + "|" + x["tournament_name"].map(C.event_key)
    rows = []
    for col in ("in_surface", "in_level", "in_indoor"):
        n = x.groupby("event")[col].nunique()
        for ev in n[n > 1].index:
            by = x[x["event"].eq(ev)].groupby("season")[col].agg(lambda v: "/".join(map(str, sorted(set(v.dropna().astype(int))))))
            rows.append({"input": col[3:], "event": ev, "codes_by_season": "; ".join(f"{s}: {c}" for s, c in by.items())})
    pd.DataFrame(rows).to_csv(C.OUT / "frame_context_changes.csv", index=False)


def missing_age(f: pd.DataFrame, m: pd.DataFrame, summary: dict) -> None:
    x = f[f["in_age"].isna()].merge(m[["match_id", "tournament_name", "source"]], on="match_id", how="left")
    g = x.groupby(["tour", "season", "source", "tournament_name"]).size().rename("matches").reset_index()
    g.to_csv(C.OUT / "frame_missing_age.csv", index=False)
    summary["missing_age"] = {"matches": int(len(x)), "wta_2026": int(((x["tour"] == "wta") & (x["season"] == 2026)).sum()),
                              "training_seasons": int((x["season"] <= 2021).sum())}


def product_drift(f: pd.DataFrame, d: pd.DataFrame, summary: dict) -> None:
    """The seven matchup products prod_<s> = O_B * D_A - O_A * D_B are not invariant to a common shift of the
    ratings: shifting every O by o0 and every D by d0 adds o0 * (D_A - D_B) - d0 * (O_A - O_B). The A - B inputs are.
    So a drift in the surface IOS's level for the model's players (for example when ITF box scores join the pool)
    changes the products' scale while no player changes. Checked on the surface IOS's own per-player values."""
    stats = ["ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"]
    cols = ["match_id"] + [f"srf_{k}_eff_{s}_{x}" for s in stats for k in ("O", "D") for x in ("a", "b")]
    s = pd.read_parquet(C.ROOT / "data/studies/surface_ios/surface_features.parquet", columns=cols)
    x = f[["match_id", "tour", "season", "tournament_date"] + [f"in_prod_{st}" for st in stats]].merge(s, on="match_id")
    rows, same = [], {}
    for st in stats:
        oa, ob = x[f"srf_O_eff_{st}_a"], x[f"srf_O_eff_{st}_b"]
        da, db = x[f"srf_D_eff_{st}_a"], x[f"srf_D_eff_{st}_b"]
        same[st] = bool(np.allclose(oa * (-db) - ob * (-da), x[f"in_prod_{st}"], equal_nan=True))
        key = [x["tour"], x["season"]]
        mo = ((oa + ob) / 2).groupby(key).transform("mean")
        md = ((da + db) / 2).groupby(key).transform("mean")
        centred = (oa - mo) * (-(db - md)) - (ob - mo) * (-(da - md))
        g = pd.DataFrame({"tour": x["tour"], "season": x["season"], "mean_O": (oa + ob) / 2, "mean_D": (da + db) / 2,
                          "prod": x[f"in_prod_{st}"], "prod_centred": centred})
        a = g.groupby(["tour", "season"]).agg(mean_O=("mean_O", "mean"), mean_D=("mean_D", "mean"),
                                              sd_prod=("prod", "std"), sd_prod_centred=("prod_centred", "std"))
        rows.append(a.assign(stat=st).reset_index())
    out = pd.concat(rows, ignore_index=True)
    out.to_csv(C.OUT / "frame_product_drift.csv", index=False)
    b = d[d["has_box"] & (d["tournament_date"] >= "2023-07-01")]
    itf = b.assign(itf=b["level"].eq("ITF"), q=b["tournament_date"].dt.to_period("Q").astype(str)).groupby(["q", "tour"])["itf"].mean()
    summary["product_drift"] = {
        "products_reproduced_from_ratings": same,
        "itf_share_of_box_rows_by_quarter": {f"{q} {t}": round(float(v), 3) for (q, t), v in itf.items()},
        "prod_hold_sd_and_level": {f"{r.tour} {r.season}": {"sd_as_built": round(r.sd_prod, 3),
                                                            "sd_centred": round(r.sd_prod_centred, 3),
                                                            "mean_D": round(r.mean_D, 3)}
                                   for r in out[out["stat"].eq("hold")].itertuples()}}


def fault_rows(d: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The player rows each confirmed box-score fault touches (box_checks.py's findings)."""
    b = d[d["has_box"]]
    tour_2015 = (b["tour"].eq("wta") & b["year"].eq(2015) & b["level"].isin(["T1000", "T500", "T250"])
                 & ~b["qualifying"] & b["tournament_date"].between("2015-02-23", "2015-08-24"))
    w15 = b[tour_2015]
    share = w15.groupby("tournament_name").apply(lambda x: x["second_won"].sum() / (x["svpt"] - x["first_in"]).sum())
    one_a = b[b["side"].eq("A")]
    swapped = one_a[C.identity_flags(one_a)["swapped_box_fits"]]["match_id"]
    rg = b["tournament_name"].eq("Roland Garros") & b["year"].between(2022, 2025)
    return {
        "WTA tour Feb-Aug 2015: serve points exclude double faults": w15[w15["tournament_name"].isin(share[share > 0.49].index)],
        "box scores exchanged between winner and loser": b[b["match_id"].isin(swapped)],
        "Roland Garros 2022-25 qualifying: second serves booked as first": b[rg & b["qualifying"]],
        "Roland Garros 2022-25 main draw: same fault, smaller": b[rg & ~b["qualifying"]],
        "Paris Olympics 2024: same fault": b[b["tournament_name"].eq("Paris Olympics")],
        "Wimbledon 2026 men, TML: second serves booked as first": b[b["tour"].eq("atp") & b["tournament_name"].eq("Wimbledon")
                                                                   & b["year"].eq(2026) & b["source"].eq("tml")],
        "WTA Adelaide 2 2022: box scores of Adelaide 2021": b[b["tour"].eq("wta") & b["tournament_name"].eq("Adelaide 2")
                                                             & b["year"].eq(2022)],
    }


def exposure(d: pd.DataFrame, f: pd.DataFrame, summary: dict) -> None:
    m = d[["match_id", "player_id"]].merge(f[["match_id", "tournament_date", "tabpfn_split"]], on="match_id")
    rows = []
    for name, x in fault_rows(d).items():
        hit = x[["player_id", "tournament_date"]].rename(columns={"tournament_date": "hit_date"}).drop_duplicates()
        j = m.merge(hit, on="player_id")
        lag = (j["tournament_date"] - j["hit_date"]).dt.days
        for window in (28, 365):
            ids = j.loc[(lag > 0) & (lag <= window), "match_id"].unique()
            split = f[f["match_id"].isin(ids)]["tabpfn_split"].value_counts()
            rows.append({"fault": name, "player_rows": int(len(x)), "window_days": window, "model_frame_matches": int(len(ids)),
                         "train": int(split.get("train", 0)), "test": int(split.get("test", 0))})
    e = pd.DataFrame(rows)
    e.to_csv(C.OUT / "frame_fault_exposure.csv", index=False)
    summary["fault_exposure"] = e.to_dict(orient="records")


def main() -> int:
    C.OUT.mkdir(parents=True, exist_ok=True)
    summary: dict = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    f = C.load_model_frame()
    m = pd.read_parquet(C.SNAPSHOTS["sep30"] / "stage0_matches.parquet", columns=["match_id", "tournament_name", "source"])
    summary["frame"] = {"matches": int(len(f)), "label_mean_by_tour_season_min": round(float(f.groupby(["tour", "season"])["a_won"].mean().min()), 3),
                        "label_mean_by_tour_season_max": round(float(f.groupby(["tour", "season"])["a_won"].mean().max()), 3),
                        "seasons_by_tour": f.groupby("tour")["season"].apply(lambda s: sorted(s.unique().tolist())).to_dict()}
    season_profile(f, summary)
    C.log("season profile written")
    for snap in ("sep30", "oct07"):
        split_ids(snap, f, summary)
    C.log("split ids written")
    context_changes(f, m)
    missing_age(f, m, summary)
    d = C.load_player_rows("sep30")
    exposure(d, f, summary)
    C.log("fault exposure written")
    product_drift(f, d, summary)
    C.log("product drift written")
    C.write_json(C.OUT / "frame_summary.json", summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
