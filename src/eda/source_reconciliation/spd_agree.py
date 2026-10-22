"""Source reconciliation, Part G (serve speed), step 2: each source against the point mean, and the panel's rows against
the point mean and the consensus. Reads no match result (speed/records.parquet, the live speed history's own rows).

The point mean of a copy is the mean speed of the points the player served on his first serve that were in (serve 1,
not a double fault), timed, n1 >= 10. A copy is COMPLETE when n1 / f1 >= 0.9 (the panel's gate is 0.5: PARTIAL).

The referee of a player-match: its best complete point copy by precedence
    MatchBeats (mb_slams, mb_atp) > SlamTracker points (ibm_pts) > the Hawk-Eye copy (hawkeye_pts) > Sackmann's Slam
    files (sackmann_pts) > rally analysis (ra_atp, ra_handoff, ra_sirgenkii)
A point copy is judged against the best complete copy of ANOTHER reader; an aggregate against the best complete copy.
The MatchBeats scale: a rally-analysis copy of the ATP host reads 0.5 km/h low by definition (its speeds are cut to whole
km/h, MatchBeats rounds; spd_checks.py: -0.503 km/h on 25,108 points), so ref_mb = its mean + 0.5. Every other copy is
taken at its own mean (Hawk-Eye and Sackmann at AO / RG have no overlap with MatchBeats; their scale is unknown to within
0.5 km/h).

Task 1 (t1_agreement.csv): per source, tour and season (and pooled): rows compared, the referees used, bias (mean of
source - referee), median, SD, robust SD (1.4826 MAD), MAE, the shares within 1, 3 and 5 km/h after removing the pair's
pooled median (the definitional offset, t1_pairs.csv), and the shares beyond 5 and 10 km/h (raw).
t1_pairs.csv: every pair of sources on the player-matches both hold (pooled). t1_ks_mechanism.csv: the ATP key
statistic's error against the referee by whether its first set disagrees with its later sets (Infosys publishes the
statistic per set). t1_ks_flags.csv: validity rules for a key statistic, judged on 2021-25 rows that have a referee
(an error = more than 5 km/h off the referee on the MatchBeats scale), and how many 2025-26 key-statistic rows without
any other source each rule would flag.

Task 2: the live feed's history (live_panel.frozen_panel(): the corrected copy plus the ATP backfill), every row:
    y_mb       the panel's published value on the MatchBeats scale (key statistic: as published; rally analysis
               (infosys, sirgenkii): + 0.5; AO match centre: + 0.5, its average is the floor of the point mean; other
               point copies: as computed)
    ref_mb     the row's referee (above); d_ref = y_mb - ref_mb
    cons_mb    the consensus: the median of the independent sources the player-match has, each once, on the MatchBeats
               scale: the best point copy (complete, else partial), the ATP key statistic (any copy), the IBM feeds'
               statistic, RG's key statistic, the AO match centre; d_cons = y_mb - cons_mb
t2_panel_vs_referee.csv / t2_panel_vs_consensus.csv: rows and counts beyond 3, 5, 10 km/h by tour, season and the
panel's chosen source. Per-row values: speed/panel_rows.parquet.

Run: ./python.sh src/eda/source_reconciliation/spd_agree.py   (after spd_build.py; about 1 minute)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402

OUT = C.OUT / "speed"
COMPLETE, GATE, MIN_N = 0.9, 0.5, 10
PRECEDENCE = {"mb_slams": 0, "mb_atp": 0, "ibm_pts": 1, "hawkeye_pts": 2, "sackmann_pts": 3, "ra_atp": 4,
              "ra_handoff": 5, "ra_sirgenkii": 6}
RA = {"ra_atp", "ra_handoff", "ra_sirgenkii"}
KS = ["ks_mantd", "ks_handoff", "ks_atp", "ks_sirgenkii"]          # one statistic, several copies (in this order)
# the panel's source names -> this part's readers
PANEL_SRC = {"mantennisdata": "ks_mantd", "handoff_ks": "ks_handoff", "infosys_atp_ks": "ks_atp",
             "infosys": "ra_handoff", "sirgenkii": "ra_sirgenkii", "infosys_atp": "mb_atp",
             "infosys_slams": "mb_slams", "slamtracker": "ibm_pts", "slam_pbp": "sackmann_pts",
             "slam_tracking": "hawkeye_pts", "ausopen_mc": "ao_mc"}
PANEL_TO_MB = {"infosys": 0.5, "sirgenkii": 0.5, "ausopen_mc": 0.5}   # added to the panel's raw value
MEN_MIN, WOMEN_MIN = 120.0, 100.0                                     # the panel's implausibility floors


def load_records() -> pd.DataFrame:
    r = pd.read_parquet(OUT / "records.parquet")
    r = r[r["valid"]].copy()
    r["share"] = r["n1"] / r["f1"].where(r["f1"] > 0)
    r["mb"] = np.where(r["src"].isin(RA), r["s1"] + 0.5, r["s1"])
    _, s0p = C.stage0(["match_id"], ["match_id", "side", "first_in"])
    r = r.merge(s0p.rename(columns={"first_in": "s0_first_in"}), on=["match_id", "side"], how="left")
    # a copy's coverage of the match: its first serves in against the box score's (Stage 0)
    r["cover"] = r["f1"] / r["s0_first_in"].where(r["s0_first_in"] > 0)
    return r


def point_copies(r: pd.DataFrame) -> pd.DataFrame:
    """Gated point copies; complete = timed share >= 0.9 and, where Stage 0 has a box score, the copy's first serves in
    within 10% of the box's (a fully timed copy can still lack a set)."""
    p = r[r["kind"].eq("points") & (r["n1"] >= MIN_N) & (r["share"] >= GATE)].copy()
    covered = p["cover"].isna() | p["cover"].between(0.9, 1.1)
    p["complete"] = (p["share"] >= COMPLETE) & covered
    p["prec"] = p["src"].map(PRECEDENCE)
    return p.sort_values(["match_id", "side", "complete", "prec", "n1"], ascending=[True, True, False, True, False])


def referee(p: pd.DataFrame, exclude: str | None = None) -> pd.DataFrame:
    """The best complete copy per player-match (excluding one reader)."""
    q = p[p["complete"]]
    if exclude is not None:
        q = q[q["src"] != exclude]
    q = q.drop_duplicates(["match_id", "side"])
    return q[["match_id", "side", "src", "s1", "mb", "n1"]].rename(columns={"src": "ref_src", "s1": "ref_raw",
                                                                         "mb": "ref_mb", "n1": "ref_n1"})


def stats_table(d: pd.DataFrame, off: float | pd.Series) -> dict:
    x = d["diff"]
    h = x - off
    med = x.median()
    return {"n": int(len(x)), "bias": x.mean(), "median": med, "sd": x.std(ddof=1) if len(x) > 1 else np.nan,
            "sd_robust": 1.4826 * (x - med).abs().median(), "mae": x.abs().mean(),
            "within_1": (h.abs() <= 1).mean(), "within_3": (h.abs() <= 3).mean(), "within_5": (h.abs() <= 5).mean(),
            "beyond_5": (x.abs() > 5).mean(), "beyond_10": (x.abs() > 10).mean()}


def pairs(r: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    vals = pd.concat([p.assign(val=p["s1"])[["match_id", "side", "src", "val", "tour"]],
                      r[r["kind"].eq("stat") & r["v1"].notna()].assign(val=r["v1"])[["match_id", "side", "src", "val",
                                                                                      "tour"]]])
    w = vals.pivot_table(index=["match_id", "side"], columns="src", values="val", aggfunc="first")
    tour = vals.drop_duplicates(["match_id", "side"]).set_index(["match_id", "side"])["tour"].reindex(w.index)
    rows, srcs = [], list(w.columns)
    for i, x in enumerate(srcs):
        for y in srcs[i + 1:]:
            for t in ("atp", "wta", "both"):
                m = w[[x, y]].dropna()
                if t != "both":
                    m = m[tour.reindex(m.index).eq(t).to_numpy()]
                if len(m) < 20:
                    continue
                d = pd.DataFrame({"diff": m[x] - m[y]})
                rows.append({"x": x, "y": y, "tour": t, **stats_table(d, d["diff"].median())})
    return pd.DataFrame(rows)


def agreement(r: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    out = []
    for src in sorted(r["src"].unique()):
        g = r[r["src"].eq(src)]
        if g["kind"].iloc[0] == "points":
            g = p[p["src"].eq(src)]
            ref = referee(p, exclude=src)
            val = g["s1"]
        else:
            g = g[g["v1"].notna()]
            ref = referee(p)
            val = g["v1"]
        d = g.assign(val=val.to_numpy())[["match_id", "side", "tour", "year_s0", "val"]].merge(ref, on=["match_id",
                                                                                                  "side"])
        if d.empty:
            continue
        d["diff"] = d["val"] - d["ref_raw"]
        off = d.groupby("ref_src")["diff"].transform("median")      # the pair's pooled definitional offset
        d["off"] = off
        for (tour, year), x in list(d.groupby(["tour", "year_s0"])) + [((t, "all"), x) for t, x in d.groupby("tour")]:
            mix = x["ref_src"].value_counts()
            out.append({"src": src, "tour": tour, "year": year, "referees": ";".join(f"{k}:{v}" for k, v in mix.items()),
                        **stats_table(x, x["off"])})
    return pd.DataFrame(out)


def ks_mechanism(r: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    ref = referee(p)
    k = r[r["src"].isin(["ks_handoff", "ks_atp"]) & r["v1"].notna()].merge(ref, on=["match_id", "side"])
    k["err"] = k["v1"] - k["ref_mb"]
    k["set1_gap"] = (k["v1_set1"] - k["v1_rest"]).abs()
    k["rest_err"] = k["v1_rest"] - k["ref_mb"]
    k["band"] = pd.cut(k["set1_gap"], [-0.1, 3, 6, 10, 20, np.inf], labels=["<=3", "3-6", "6-10", "10-20", ">20"])
    k.loc[k["v1_rest"].isna(), "band"] = np.nan
    rows = []
    for (src, band), g in list(k.groupby(["src", "band"], observed=True)) + \
            [((s, "no later set"), g) for s, g in k[k["v1_rest"].isna()].groupby("src")]:
        rows.append({"src": src, "set1_vs_later_sets_kmh": band, "n": int(len(g)),
                     "match_ks_beyond_5": (g["err"].abs() > 5).mean(), "match_ks_beyond_10": (g["err"].abs() > 10).mean(),
                     "match_ks_mae": g["err"].abs().mean(),
                     "later_sets_ks_beyond_5": (g["rest_err"].abs() > 5).mean() if g["v1_rest"].notna().any() else np.nan,
                     "later_sets_ks_mae": g["rest_err"].abs().mean() if g["v1_rest"].notna().any() else np.nan})
    return pd.DataFrame(rows)


def arbitration(r: pd.DataFrame, p: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
    """Where the ATP key statistic and the referee disagree by more than 3 km/h: which is closer to the player's norm
    (the median of his other use rows of the panel within 91 days, at least 3, on the MatchBeats scale). Result-free;
    the norm's rows are mostly key statistics themselves, so the test leans toward the key statistic if anything."""
    ref = referee(p)
    k = r[r["src"].isin(KS) & r["v1"].notna()].copy()
    k["ord"] = k["src"].map({s: i for i, s in enumerate(KS)})
    k = k.sort_values("ord").drop_duplicates(["match_id", "side"]).merge(ref, on=["match_id", "side"])
    k["gap"] = k["v1"] - k["ref_mb"]
    k = k[k["gap"].abs() > 3]
    u = h[h["use"].astype(bool)][["match_id", "side", "player_id", "obs", "y_mb"]]
    by = {pid: g for pid, g in u.groupby("player_id")}
    obs = u.set_index(["match_id", "side"])["obs"]
    norms = []
    for m, s, pid in zip(k["match_id"], k["side"], k["player_id"]):
        g = by.get(pid)
        if g is None or (m, s) not in obs.index:
            norms.append(np.nan)
            continue
        o = g[(g["match_id"] != m) & ((g["obs"] - obs[(m, s)]).abs() <= 91)]
        norms.append(float(np.median(o["y_mb"])) if len(o) >= 3 else np.nan)
    k["norm"] = norms
    k = k[k["norm"].notna()]
    k["ks_dev"], k["ref_dev"] = (k["v1"] - k["norm"]).abs(), (k["ref_mb"] - k["norm"]).abs()
    rows = []
    for lo, hi in ((3, 5), (5, 10), (10, 20), (20, np.inf)):
        z = k[(k["gap"].abs() > lo) & (k["gap"].abs() <= hi)]
        rows.append({"gap_kmh": f"({lo}, {hi}]", "rows": int(len(z)),
                     "point_mean_closer_to_norm": (z["ref_dev"] < z["ks_dev"]).mean() if len(z) else np.nan,
                     "median_abs_point_mean_minus_norm": z["ref_dev"].median(),
                     "median_abs_ks_minus_norm": z["ks_dev"].median()})
    return pd.DataFrame(rows)


def norm_dev(panel: pd.DataFrame) -> pd.Series:
    """|y - the median of the player's other use rows within 91 days (obs)|, raw km/h; NaN with fewer than 3 others."""
    q = panel[panel["use"].astype(bool)][["match_id", "side", "player_id", "obs", "y"]].copy()
    out = pd.Series(np.nan, index=panel.index)
    pos = {k: i for i, k in enumerate(zip(panel["match_id"], panel["side"]))}
    for pid, g in q.groupby("player_id"):
        if len(g) < 4:
            continue
        ob, y = g["obs"].to_numpy(float), g["y"].to_numpy(float)
        near = np.abs(ob[:, None] - ob[None, :]) <= 91
        np.fill_diagonal(near, False)
        for i in range(len(g)):
            o = y[near[i]]
            if len(o) >= 3:
                out.iloc[pos[(g["match_id"].iloc[i], g["side"].iloc[i])]] = abs(y[i] - np.median(o))
    return out


def ks_flags(r: pd.DataFrame, p: pd.DataFrame, panel_rows: pd.DataFrame, s0p: pd.DataFrame) -> pd.DataFrame:
    """Validity rules for a key statistic; precision and recall on rows with a referee; counts on rows without."""
    ref = referee(p)
    k = r[r["src"].isin(KS) & r["v1"].notna()].copy()
    k["ord"] = k["src"].map({s: i for i, s in enumerate(KS)})
    # the per-set values exist only in the Infosys copies (the handoff's, the ATP host's): take them from there
    per = k[k["src"].isin(["ks_handoff", "ks_atp"]) & k["v1_rest"].notna()].sort_values("ord").drop_duplicates(
        ["match_id", "side"])[["match_id", "side", "v1_set1", "v1_rest"]]
    k = k.sort_values("ord").drop_duplicates(["match_id", "side"]).drop(columns=["v1_set1", "v1_rest"])
    k = k.merge(per, on=["match_id", "side"], how="left")
    k = k.merge(ref, on=["match_id", "side"], how="left")
    nd = panel_rows.set_index(["match_id", "side"])["norm_dev"]
    k["norm_dev"] = nd.reindex(pd.MultiIndex.from_frame(k[["match_id", "side"]])).to_numpy()
    men = k["tour"].eq("atp")
    k["err5"] = (k["v1"] - k["ref_mb"]).abs() > 5
    flags = {
        "avg_ge_max": k["v1"] >= k["vmax"],
        "second_ge_first": k["v2"] >= k["v1"],
        "band_150_235_men_125_205_women": np.where(men, (k["v1"] < 150) | (k["v1"] > 235),
                                                   (k["v1"] < 125) | (k["v1"] > 205)),
        "below_panel_floor_120": k["v1"] < np.where(men, MEN_MIN, WOMEN_MIN),
        "first_in_differs_from_stage0_by_3+": (k["vfin"] - k["s0_first_in"]).abs() >= 3,
        "set1_vs_later_sets_10+": (k["v1_set1"] - k["v1_rest"]).abs() >= 10,
        "off_player_norm_10+": k["norm_dev"] >= 10,
        "off_player_norm_7+": k["norm_dev"] >= 7,
    }
    flags["audit_rules_any"] = flags["avg_ge_max"] | flags["second_ge_first"] | flags["band_150_235_men_125_205_women"]
    flags["audit_rules_or_norm10"] = flags["audit_rules_any"] | flags["off_player_norm_10+"]
    flags["avg_ge_max_or_set_gap10"] = flags["avg_ge_max"] | flags["set1_vs_later_sets_10+"]
    has_ref = k["ref_mb"].notna()
    yrs = k["year_s0"]
    others = r[~r["src"].isin(KS) & ((r["kind"].eq("stat") & r["v1"].notna()) | (r["kind"].eq("points") &
                                                                                   (r["n1"] >= MIN_N)))]
    alone = ~pd.MultiIndex.from_frame(k[["match_id", "side"]]).isin(pd.MultiIndex.from_frame(others[["match_id",
                                                                                                    "side"]]))
    rows = []
    for name, f in flags.items():
        f = pd.Series(np.asarray(f, bool), index=k.index)
        for scope, m in (("with_referee_2021_25", has_ref & yrs.between(2021, 2025)),):
            e = k.loc[m, "err5"]
            ff = f[m]
            rows.append({"rule": name, "scope": scope, "rows": int(m.sum()), "errors": int(e.sum()),
                         "flagged": int(ff.sum()), "flagged_errors": int((ff & e).sum()),
                         "precision": (ff & e).sum() / max(ff.sum(), 1), "recall": (ff & e).sum() / max(e.sum(), 1)})
        for y in (2025, 2026):
            m = alone & yrs.eq(y) & men
            rows.append({"rule": name, "scope": f"ks_only_men_{y}", "rows": int(m.sum()), "errors": np.nan,
                         "flagged": int(f[m].sum()), "flagged_errors": np.nan, "precision": np.nan, "recall": np.nan})
    return pd.DataFrame(rows)


def panel_rows(r: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    hist = LP.frozen_panel()
    cols = ["match_id", "side", "player_id", "tour", "year", "level", "qualifying", "slam", "source", "basis", "kind",
            "y", "y_raw", "n", "spd_max", "spd2_raw", "use", "drop_reason", "obs", "edition"]
    h = hist[cols].copy()
    h["src"] = h["source"].map(PANEL_SRC)
    h["y_mb"] = h["y_raw"] + h["source"].map(PANEL_TO_MB).fillna(0.0)
    ref = referee(p)
    h = h.merge(ref, on=["match_id", "side"], how="left")
    h["d_ref"] = h["y_mb"] - h["ref_mb"]
    h["same_copy"] = h["src"].eq(h["ref_src"])
    # the consensus: independent families, each once, on the MatchBeats scale; an aggregate the live feed itself rejects
    # does not vote (the input-data audit's impossible rule, average >= 240 km/h or >= the record's own maximum, and the
    # panel's floors, men < 120 and women < 100 km/h)
    best = p.drop_duplicates(["match_id", "side"])[["match_id", "side", "src", "mb", "complete"]].rename(
        columns={"src": "pt_src", "mb": "fam_points", "complete": "pt_complete"})
    floor = np.where(r["tour"].eq("atp"), MEN_MIN, WOMEN_MIN)
    rejected = (r["v1"] >= 240) | (r["v1"] >= r["vmax"]) | (r["v1"] < floor)
    r = r[~(r["kind"].eq("stat") & rejected)]
    ks = r[r["src"].isin(KS) & r["v1"].notna()].copy()
    ks["ord"] = ks["src"].map({s: i for i, s in enumerate(KS)})
    ks = ks.sort_values("ord").drop_duplicates(["match_id", "side"])[["match_id", "side", "v1"]].rename(
        columns={"v1": "fam_ks"})
    fam = best
    for src, name, off in (("ibm_stat", "fam_ibm_stat", 0.0), ("ks_rg", "fam_rg_ks", 0.0), ("ao_mc", "fam_ao_mc", 0.5)):
        s = r[r["src"].eq(src) & r["v1"].notna()].drop_duplicates(["match_id", "side"])[["match_id", "side", "v1"]]
        fam = fam.merge(s.assign(v1=s["v1"] + off).rename(columns={"v1": name}), on=["match_id", "side"], how="outer")
    fam = fam.merge(ks, on=["match_id", "side"], how="outer")
    fcols = ["fam_points", "fam_ks", "fam_ibm_stat", "fam_rg_ks", "fam_ao_mc"]
    fam["n_families"] = fam[fcols].notna().sum(axis=1)
    fam["cons_mb"] = fam[fcols].median(axis=1, skipna=True)
    h = h.merge(fam, on=["match_id", "side"], how="left")
    h["d_cons"] = h["y_mb"] - h["cons_mb"]
    h["norm_dev"] = norm_dev(h)
    return h


def counts(h: pd.DataFrame, col: str, have: str) -> pd.DataFrame:
    rows = []
    u = h[h["use"].astype(bool)]
    for keys, g in list(u.groupby(["tour", "year", "source"])) + [((t, y, "all"), g) for (t, y), g in
                                                                 u.groupby(["tour", "year"])] + \
            [((t, "all", "all"), g) for t, g in u.groupby("tour")]:
        x = g[g[have].notna()]
        d = x[col].abs()
        rows.append({"tour": keys[0], "year": keys[1], "panel_source": keys[2], "panel_rows": int(len(g)),
                     "with_" + have: int(len(x)), "same_copy": int(x["same_copy"].sum()) if col == "d_ref" else np.nan,
                     "beyond_3": int((d > 3).sum()), "beyond_5": int((d > 5).sum()), "beyond_10": int((d > 10).sum()),
                     "share_beyond_5": (d > 5).mean() if len(x) else np.nan,
                     "median_abs": d.median() if len(x) else np.nan})
    return pd.DataFrame(rows)


def main() -> int:
    r = load_records()
    p = point_copies(r)
    t1 = agreement(r, p)
    t1.to_csv(OUT / "t1_agreement.csv", index=False, float_format="%.4f")
    pr = pairs(r, p)
    pr.to_csv(OUT / "t1_pairs.csv", index=False, float_format="%.4f")
    km = ks_mechanism(r, p)
    km.to_csv(OUT / "t1_ks_mechanism.csv", index=False, float_format="%.4f")
    h = panel_rows(r, p)
    h.to_parquet(OUT / "panel_rows.parquet", index=False)
    kf = ks_flags(r, p, h, None)
    kf.to_csv(OUT / "t1_ks_flags.csv", index=False, float_format="%.4f")
    ar = arbitration(r, p, h)
    ar.to_csv(OUT / "t1_arbitration.csv", index=False, float_format="%.4f")
    t2r = counts(h, "d_ref", "ref_mb")
    t2r.to_csv(OUT / "t2_panel_vs_referee.csv", index=False, float_format="%.4f")
    t2c = counts(h, "d_cons", "cons_mb")
    t2c.to_csv(OUT / "t2_panel_vs_consensus.csv", index=False, float_format="%.4f")
    u = h[h["use"].astype(bool)]
    summ = {
        "reads_results": False,
        "point_copies_gated": int(len(p)), "player_matches_with_a_complete_copy": int(p[p["complete"]].drop_duplicates(
            ["match_id", "side"]).shape[0]),
        "panel_rows": int(len(h)), "panel_use_rows": int(len(u)),
        "panel_use_rows_with_referee": int(u["ref_mb"].notna().sum()),
        "panel_use_rows_beyond_3_5_10_of_referee": [int((u["d_ref"].abs() > t).sum()) for t in (3, 5, 10)],
        "panel_use_rows_beyond_3_5_10_of_consensus": [int((u["d_cons"].abs() > t).sum()) for t in (3, 5, 10)],
        "panel_use_rows_by_families": u["n_families"].value_counts().sort_index().to_dict(),
    }
    C.write_json(OUT / "agree_summary.json", summ)
    print(summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
