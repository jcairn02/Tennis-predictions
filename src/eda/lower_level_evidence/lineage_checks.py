"""Spot checks of the lineage audit (team role 01) of the lower-level-evidence study.

Counts and light measurements behind docs/studies/lower_level_evidence/team/01_lineage.md. Reads the frozen reference's
Stage 0 (common.STAGE0_DIR) and frame; two checks also read intermediate tables of the 30 Sep build that the reference
did not freeze (named below). Reads no outcome of the 2025-2026 holdout: holdout matches are only counted (levels,
box-score coverage), and every value read from a box score, a score or a result belongs to an event before 30 Dec 2024
(asserted with common.assert_no_holdout_outcomes).

    pools      matches per tour, season and bucket in the two history pools the builders read: the result pool
               (completed or retired: Elo, games-weighted Elo, the surface counts, the workload) and the box-score pool
               (completed, standard format, box score held: the serve/return ratings, the 52-week points, the two-week
               form, the IOS). Counts only, 2010-2026.
    tuning     the populations the inherited constants and norms were tuned on, by bucket. Counts only.
    evidence   for every player row of a main-tour frame match of 2013-2024, the share of that player's earlier
               evidence that comes from each bucket, under the weight each input family gives a match (WEIGHTINGS).
               The time rule is the builders': earlier tournament weeks, plus earlier rounds of the same event (a
               qualifier's qualifying rounds are earlier rounds of his main-draw event). Histories before 30 Dec 2024.
    adj_shift  the one-step opponent adjustment of the two-week form (Stage B's per-match z, the source of form_*,
               formdef_* and adjperf_tpw_2w): the same player in the same season at a lower level and on the main tour;
               mean z there minus here, beside the same contrast on the raw (unadjusted) total-points share. Reads
               data/studies/ufc_ideas/stageB_adj.parquet (built 2 Oct 2026 on the 30 Sep tables), seasons to 2024.
    s3_resid   Stage 3's online serve/return ratings (the source of ratings_iid): serve points won minus expected, per
               serve point, by bucket and by the server's predicted edge. Reads data/studies/predictability_diagnostic/
               stage3_ratings.parquet (built 1 Oct 2026 on the 30 Sep tables), seasons to 2024.
    ios_resid  the decided surface IOS (the source of the 14 iosO_/iosD_ and 7 prod_ inputs): each server's centred
               value minus O_server - D_returner, by bucket, on the Stage 4 pool's matches. Reads data/studies/
               surface_ios/surface_features.parquet (built 6 Oct 2026), seasons to 2024.

Run: ./python.sh src/eda/lower_level_evidence/lineage_checks.py [--stage0-dir <folder>] [--only pools,tuning,...]
Writes data/studies/lower_level_evidence/lineage/*.csv and lineage_checks.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as L  # noqa: E402
from src.eda.predictability_diagnostic import common as PC  # noqa: E402   (asof_sums: a pure function)
from src.eda.predictability_diagnostic import stage3_traits as T3  # noqa: E402   (sums_before, lookback_sums)

OUT = L.OUT / "lineage"
STAGEB_ADJ = ROOT / "data" / "studies" / "ufc_ideas" / "stageB_adj.parquet"
STAGEB_ADJ_SUMMARY = ROOT / "data" / "studies" / "ufc_ideas" / "stageB_adj_summary.json"
STAGE3_RATINGS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage3_ratings.parquet"
STAGE4_CONSTANTS = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage4_constants.csv"

EVAL_LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "CH")       # predictability_diagnostic/common.py:49
GROUPS = {"MAIN": ("MAIN",), "TEAM": ("TEAM",), "Q": ("TQ", "GSQ"), "CH": ("CH", "CHQ"), "ITF": ("ITF", "ITFQ")}
# how each input family weighs an earlier match of the player (see the report's master table)
WEIGHTINGS = {
    "results_career": "played matches (completed or retired) since 2010: Elo's whole-history memory",
    "results_365d": "played matches in the last 364 days: the same, last year only",
    "box_52w_servepts": "serve points of box-score matches in the last 364 days: points_52w",
    "box_2w_decay": "box-score matches, weight 2^(-age/2 weeks): the two-week form (form_*, formdef_*, adjperf_tpw_2w)",
    "ios_long_servepts": "serve points, weight 2^(-age/52 weeks): the long-memory IOS on serve points (h 52, tau 1)",
    "ios_short_servepts": "serve points, weight 2^(-age/h), h 4 weeks men, 13 women: ios_points_short",
    "played_14d": "played matches in the last 14 days: sets_14d",
}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def write(df: pd.DataFrame, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    df.to_csv(p, index=False, float_format="%.6g")
    return p


# ------------------------------------------------------------------------------------------------ pools (counts)

def pools(m: pd.DataFrame) -> pd.DataFrame:
    played = m["status"].isin(["completed", "retired"])
    box = m["status"].eq("completed") & m["format"].eq("standard") & m["has_box"].astype(bool)
    out = []
    for name, sel in (("results", played), ("box", box)):
        g = m[sel].groupby(["tour", "year", "bucket"]).size().rename("matches").reset_index()
        out.append(g.assign(pool=name))
    df = pd.concat(out, ignore_index=True)
    tot = df.groupby(["pool", "tour", "year"])["matches"].transform("sum")
    df["share"] = df["matches"] / tot
    return df[["pool", "tour", "year", "bucket", "matches", "share"]]


# ------------------------------------------------------------------------------------------------ tuning populations

def tuning(m: pd.DataFrame) -> pd.DataFrame:
    """The populations named in the builders (counts by bucket and tour)."""
    yr = m["year"]
    played = m["status"].isin(["completed", "retired"])
    box = m["status"].eq("completed") & m["has_box"].astype(bool)
    box_std = box & m["format"].eq("standard")
    ev_level = m["level"].isin(EVAL_LEVELS)
    pops = {
        "Elo K and surface weight (stage1_baselines.py:226-246; also offset Elo kd, pieces.py:162)":
            m["evaluation"].astype(bool) & yr.between(2013, 2018),
        "Elo history (every update, stage1_baselines.py:69, 204)": played,
        "games-Elo scale (stage4_features.py:706-722)": played & yr.between(2010, 2018),
        "Stage 3 surface mu (stage3_ratings.py:224)": box & yr.between(2010, 2018),
        "Stage 3 tuning target (stage3_ratings.py:277)": box & ev_level & yr.between(2013, 2018),
        "surface means and shrinkage K of the box-score inputs (stage3_traits.py:765-767, 187-200, 421-450)":
            box_std & ev_level & yr.between(2010, 2018),
        "Stage B adjperf tuning target (stageB_adjperf.py:262)":
            m["evaluation"].astype(bool) & yr.between(2013, 2018) & box_std,
        "Stage B population MAD and typical units (stageB_adjperf.py:149-171, stageB_common.py:175-186)":
            box_std & yr.between(2010, 2018),
        "IOS tuning target (stageB_ios.py docstring: evaluation-level matches 2013-2018)":
            ev_level & box_std & yr.between(2013, 2018),
    }
    rows = []
    for name, sel in pops.items():
        g = m[sel].groupby(["tour", "bucket"]).size()
        for tour in ("atp", "wta"):
            gt = g.get(tour, pd.Series(dtype=float))
            tot = float(gt.sum())
            rec = {"population": name, "tour": tour, "matches": int(tot)}
            for b in L.BUCKETS:
                rec[b] = int(gt.get(b, 0))
            rec["lower_share"] = float(sum(gt.get(b, 0) for b in L.LOWER) / tot) if tot else np.nan
            rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ evidence shares

def player_rows(stage0_dir: Path) -> pd.DataFrame:
    """Player rows of matches before the holdout, with what the weightings read (serve points: a box-score count)."""
    m = L.load_matches(stage0_dir, ["tour", "year", "map_level", "level", "status", "format", "has_box",
                                    "tournament_id", "tournament_date", "round_order", "surface"])
    m = m[~L.in_holdout(m["tournament_date"])]
    mp = L.load_players(stage0_dir, ["side", "spw_d"], match_ids=m["match_id"])
    r = mp.merge(m, on="match_id", how="inner", validate="many_to_one")
    L.assert_no_holdout_outcomes(r["tournament_date"], "evidence: player rows")
    r["day"] = pd.to_datetime(r["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    r["pcode"] = pd.factorize(r["player_id"])[0]
    r["played"] = r["status"].isin(["completed", "retired"]).to_numpy()
    sp = pd.to_numeric(r["spw_d"], errors="coerce").to_numpy(dtype="float64")
    r["box_pts"] = np.where(r["status"].eq("completed") & r["format"].eq("standard") & np.isfinite(sp) & (sp > 0),
                            sp, 0.0)
    r["box"] = (r["box_pts"] > 0).astype("float64")
    return r.reset_index(drop=True)


def group_values(r: pd.DataFrame, w: np.ndarray) -> np.ndarray:
    """Columns: total, then one per GROUPS entry, of the weight w."""
    cols = [w]
    for _, buckets in GROUPS.items():
        cols.append(np.where(r["bucket"].isin(buckets).to_numpy(), w, 0.0))
    return np.column_stack(cols)


def asof(r: pd.DataFrame, V: np.ndarray) -> np.ndarray:
    tmp = r[["pcode", "tournament_date", "tournament_id", "round_order"]].copy()
    names = [f"_v{j}" for j in range(V.shape[1])]
    for j, c in enumerate(names):
        tmp[c] = V[:, j]
    return PC.asof_sums(tmp, names, player="pcode").to_numpy()


def windowed(r: pd.DataFrame, V: np.ndarray, days: int) -> np.ndarray:
    pc, day = r["pcode"].to_numpy(), r["day"].to_numpy()
    return asof(r, V) - T3.sums_before(pc, day, V, pc, day - days)


def decayed(r: pd.DataFrame, V: np.ndarray, half_life_weeks: np.ndarray) -> np.ndarray:
    """sum over earlier rows of V 2^(-age / h) (age in days of tournament dates), h per row (the target's tour)."""
    day = r["day"].to_numpy().astype("float64")
    ref = float(T3.REF_DAY)
    out = np.zeros_like(V)
    for h in np.unique(half_life_weeks):
        f = np.exp2((day - ref) / (7.0 * h))
        s = asof(r, V * f[:, None]) / f[:, None]
        sel = half_life_weeks == h
        out[sel] = s[sel]
    return out


def evidence(stage0_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    r = player_rows(stage0_dir)
    frame = L.load_frame(columns=["match_id", "tour", "season", "tournament_date"])
    frame = frame[~L.in_holdout(frame["tournament_date"])]
    tgt = r["match_id"].isin(set(frame["match_id"])).to_numpy()
    if not r.loc[tgt, "bucket"].eq("MAIN").all():
        raise AssertionError("a frame match is not a main-tour main-draw match")
    log(f"evidence: {len(r):,} player rows before the holdout; {int(tgt.sum()):,} rows of {len(frame):,} frame matches")
    played = r["played"].to_numpy().astype("float64")
    pts = r["box_pts"].to_numpy()
    box = r["box"].to_numpy()
    short_h = np.where(r["tour"].eq("atp"), 4.0, 13.0)
    results = {}
    results["results_career"] = asof(r, group_values(r, played))
    results["results_365d"] = windowed(r, group_values(r, played), 364)
    results["box_52w_servepts"] = windowed(r, group_values(r, pts), 364)
    results["box_2w_decay"] = decayed(r, group_values(r, box), np.full(len(r), 2.0))
    results["ios_long_servepts"] = decayed(r, group_values(r, pts), np.full(len(r), 52.0))
    results["ios_short_servepts"] = decayed(r, group_values(r, pts), short_h)
    results["played_14d"] = windowed(r, group_values(r, played), 14)
    log("evidence: sums done")
    t = r.loc[tgt, ["match_id", "player_id", "tour", "year", "level"]].reset_index(drop=True)
    long_rows, per_row = [], {"match_id": t["match_id"], "player_id": t["player_id"], "tour": t["tour"],
                              "year": t["year"], "level": t["level"]}
    for name, S in results.items():
        S = np.asarray(S)[tgt]
        tot = S[:, 0]
        has = tot > 1e-12
        shares = {g: np.where(has, S[:, 1 + j] / np.where(has, tot, 1.0), np.nan) for j, g in enumerate(GROUPS)}
        lower = shares["Q"] + shares["CH"] + shares["ITF"]
        per_row[f"{name}__lower"] = lower
        for scope, sel in [("all", np.ones(len(t), bool))] + [(lv, t["level"].eq(lv).to_numpy())
                                                               for lv in ("GS", "T1000", "T500", "T250")]:
            for tour in ("atp", "wta"):
                k = sel & t["tour"].eq(tour).to_numpy() & has
                if not k.any():
                    continue
                rec = {"weighting": name, "tour": tour, "level": scope, "player_rows": int(k.sum()),
                       "rows_without_evidence": int((sel & t["tour"].eq(tour).to_numpy() & ~has).sum()),
                       "mean_lower_share": float(np.mean(lower[k])),
                       "median_lower_share": float(np.median(lower[k])),
                       "rows_lower_over_half": float(np.mean(lower[k] > 0.5))}
                for g in GROUPS:
                    rec[f"mean_{g}_share"] = float(np.mean(shares[g][k]))
                long_rows.append(rec)
    return pd.DataFrame(long_rows), pd.DataFrame(per_row)


# ------------------------------------------------------------------------------------------------ one-step adjustment

ADJ_STATS = ["tpw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk",
             "bp_conv", "rpw_first", "rpw_second"]
DEF_STATS = ["ace", "df", "first_in", "bp_faced_pg"]
MIN_ROWS = 3


def adj_shift(stage0_dir: Path) -> pd.DataFrame:
    cols = (["match_id", "player_id", "tour", "year"] + [f"z_adjperf_{s}" for s in ADJ_STATS]
            + [f"z_adjdef_{s}" for s in DEF_STATS])
    z = pd.read_parquet(STAGEB_ADJ, columns=cols, filters=[("year", "<=", 2024)])
    m = L.load_matches(stage0_dir, ["map_level", "tournament_date", "surface"])
    z = z.merge(m, on="match_id", how="inner", validate="many_to_one")
    z = z[~L.in_holdout(z["tournament_date"])]
    L.assert_no_holdout_outcomes(z["tournament_date"], "adj_shift: per-match z")
    # the raw counterpart: total points won, its log-odds centred on the tour's surface average (Stage 3's, 2010-2018),
    # in units of the population MAD Stage B divides by (tau 0)
    mp = L.load_players(stage0_dir, ["tpw_n", "tpw_d"], match_ids=z["match_id"])
    z = z.merge(mp, on=["match_id", "player_id"], how="left", validate="one_to_one")
    k = pd.read_csv(STAGE4_CONSTANTS)
    k = k[k["kind"].eq("surface average") & k["stat"].eq("tpw")]
    mu = {(r.tour, r.surface): float(r.value) for r in k.itertuples(index=False)}
    mad = {r["tour"]: float(r["mad"]) for r in json.loads(STAGEB_ADJ_SUMMARY.read_text(encoding="utf-8"))["population_mad"]
           if r["stat"] == "tpw" and r["channel"] == "adjperf" and int(r["tau"]) == 0}
    surf = z["surface"].where(z["surface"].isin(["Hard", "Clay", "Grass", "Carpet"]), "all")
    m_ = np.array([mu[(t, s)] for t, s in zip(z["tour"], surf)])
    x, d = z["tpw_n"].to_numpy(dtype="float64"), z["tpw_d"].to_numpy(dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.log((x + 0.5) / (d - x + 0.5)) - np.log(m_ / (1 - m_))
        z["raw_tpw"] = np.where((d > 0) & z["z_adjperf_tpw"].notna(), v / z["tour"].map(mad).to_numpy(), np.nan)
        z["raw_tpw_share"] = np.where((d > 0) & z["z_adjperf_tpw"].notna(), x / d, np.nan)
    measures = (["raw_tpw", "raw_tpw_share"] + [f"z_adjperf_{s}" for s in ADJ_STATS]
                + [f"z_adjdef_{s}" for s in DEF_STATS])
    rows = []
    for low in ("CH", "TQ", "GSQ", "CHQ"):
        for tour in ("atp", "wta"):
            zz = z[z["tour"].eq(tour) & z["bucket"].isin(["MAIN", low])]
            for meas in measures:
                g = zz[zz[meas].notna()].groupby(["player_id", "year", "bucket"])[meas].agg(["mean", "size"])
                g = g.unstack("bucket")
                if ("size", low) not in g.columns or ("size", "MAIN") not in g.columns:
                    continue
                ok = (g[("size", low)] >= MIN_ROWS) & (g[("size", "MAIN")] >= MIN_ROWS)
                diff = (g.loc[ok, ("mean", low)] - g.loc[ok, ("mean", "MAIN")]).to_numpy()
                n = len(diff)
                if n < 20:
                    continue
                se = float(np.std(diff, ddof=1) / np.sqrt(n))
                rows.append({"lower": low, "tour": tour, "measure": meas, "player_seasons": n,
                             "mean_lower_minus_main": float(np.mean(diff)), "lo95": float(np.mean(diff) - 1.96 * se),
                             "hi95": float(np.mean(diff) + 1.96 * se),
                             "sd_of_measure_main": float(zz.loc[zz["bucket"].eq("MAIN"), meas].std())})
    out = pd.DataFrame(rows)
    # the share of the raw total-points shift left after the one-step adjustment
    for (low, tour), g in out.groupby(["lower", "tour"]):
        raw = g.loc[g["measure"].eq("raw_tpw"), "mean_lower_minus_main"]
        adj = g.loc[g["measure"].eq("z_adjperf_tpw"), "mean_lower_minus_main"]
        if len(raw) and len(adj) and raw.iloc[0] != 0:
            out.loc[(out["lower"] == low) & (out["tour"] == tour) & out["measure"].eq("z_adjperf_tpw"),
                    "share_of_raw_shift_left"] = float(adj.iloc[0] / raw.iloc[0])
    return out


# ------------------------------------------------------------------------------------------------ Stage 3 residuals

EDGE_BINS = [-np.inf, -0.4, -0.15, 0.15, 0.4, np.inf]
EDGE_LABELS = ["< -0.40", "-0.40..-0.15", "-0.15..0.15", "0.15..0.40", "> 0.40"]


def s3_resid(stage0_dir: Path) -> pd.DataFrame:
    rt = pd.read_parquet(STAGE3_RATINGS, columns=["match_id", "year", "updates", "p_serve_a", "p_serve_b", "mu_logit"],
                         filters=[("year", "<=", 2024)])
    rt = rt[rt["updates"].astype(bool)]
    m = L.load_matches(stage0_dir, ["tour", "map_level", "tournament_date"])
    rt = rt.merge(m, on="match_id", how="inner", validate="one_to_one")
    rt = rt[~L.in_holdout(rt["tournament_date"])]
    L.assert_no_holdout_outcomes(rt["tournament_date"], "s3_resid: serve points won")
    mp = L.load_players(stage0_dir, ["side", "spw_n", "spw_d"], match_ids=rt["match_id"])
    mp = mp[mp["match_id"].isin(set(rt["match_id"]))]
    a = mp[mp["side"].eq("A")].set_index("match_id")
    b = mp[mp["side"].eq("B")].set_index("match_id")
    parts = []
    for side, src, p in (("A", a, "p_serve_a"), ("B", b, "p_serve_b")):
        n = rt["match_id"].map(src["spw_d"]).to_numpy(dtype="float64")
        w = rt["match_id"].map(src["spw_n"]).to_numpy(dtype="float64")
        pp = rt[p].to_numpy(dtype="float64")
        edge = np.log(pp / (1 - pp)) - rt["mu_logit"].to_numpy(dtype="float64")
        parts.append(pd.DataFrame({"tour": rt["tour"].to_numpy(), "bucket": rt["bucket"].to_numpy(), "n": n, "w": w,
                                   "exp": n * pp, "edge": edge}))
    s = pd.concat(parts, ignore_index=True)
    s = s[np.isfinite(s["n"]) & np.isfinite(s["w"]) & (s["n"] > 0) & np.isfinite(s["exp"])]
    s["edge_bin"] = pd.cut(s["edge"], EDGE_BINS, labels=EDGE_LABELS)
    rows = []
    for keys, g in list(s.groupby(["tour", "bucket"])) + list(s.groupby(["tour", "bucket", "edge_bin"], observed=True)):
        tour, bucket = keys[0], keys[1]
        rows.append({"tour": tour, "bucket": bucket, "edge_bin": keys[2] if len(keys) > 2 else "all",
                     "server_rows": int(len(g)), "serve_points": float(g["n"].sum()),
                     "resid_pp_per_serve_point": float(100 * (g["w"].sum() - g["exp"].sum()) / g["n"].sum())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ surface IOS residuals

SURFACE_FEATURES = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
IOS_STATS = ("spw", "ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")


def ios_resid(stage0_dir: Path) -> pd.DataFrame:
    """The decided surface IOS (pre-match O + E_s and D + F_s, surface_features.parquet of 6 Oct 2026): each server's
    centred value minus O_server - D_returner, on the Stage 4 pool's matches (main tour, its qualifying, Challengers and
    their qualifying) before the holdout, by bucket. The model the solve assumes at every level."""
    cols = ["match_id"] + [f"srf_{k}_eff_{s}_{x}" for s in IOS_STATS for k in ("O", "D") for x in ("a", "b")]
    sf = pd.read_parquet(SURFACE_FEATURES, columns=cols)
    m = L.load_matches(stage0_dir, ["tour", "map_level", "tournament_date", "surface", "status", "format"])
    sf = sf.merge(m, on="match_id", how="inner", validate="one_to_one")
    sf = sf[~L.in_holdout(sf["tournament_date"]) & sf["status"].eq("completed") & sf["format"].eq("standard")]
    L.assert_no_holdout_outcomes(sf["tournament_date"], "ios_resid: box-score values")
    mp = L.load_players(stage0_dir, ["side"] + [f"{s}_{x}" for s in IOS_STATS for x in ("n", "d")],
                        match_ids=sf["match_id"])
    mp = mp[mp["match_id"].isin(set(sf["match_id"]))]
    a = mp[mp["side"].eq("A")].set_index("match_id").reindex(sf["match_id"])
    b = mp[mp["side"].eq("B")].set_index("match_id").reindex(sf["match_id"])
    k = pd.read_csv(STAGE4_CONSTANTS)
    k = k[k["kind"].eq("surface average")]
    surf = sf["surface"].where(sf["surface"].isin(["Hard", "Clay", "Grass", "Carpet"]), "all").to_numpy()
    tour = sf["tour"].to_numpy()
    rows = []
    for s in IOS_STATS:
        mu_tab = {(r.tour, r.surface): float(r.value) for r in k[k["stat"].eq(s)].itertuples(index=False)}
        mu = np.array([mu_tab[(t, x)] for t, x in zip(tour, surf)])
        parts = []
        for srv, ret, xs in ((a, "b", "a"), (b, "a", "b")):
            x, d = srv[f"{s}_n"].to_numpy(dtype="float64"), srv[f"{s}_d"].to_numpy(dtype="float64")
            with np.errstate(divide="ignore", invalid="ignore"):
                c = np.log((x + 0.5) / (d - x + 0.5)) - np.log(mu / (1 - mu))
            pred = sf[f"srf_O_eff_{s}_{xs}"].to_numpy(dtype="float64") - sf[f"srf_D_eff_{s}_{ret}"].to_numpy(dtype="float64")
            ok = np.isfinite(c) & np.isfinite(pred) & (d > 0)
            parts.append(pd.DataFrame({"tour": tour[ok], "bucket": sf["bucket"].to_numpy()[ok], "c": c[ok],
                                       "pred": pred[ok], "d": d[ok]}))
        p = pd.concat(parts, ignore_index=True)
        p["resid"] = p["c"] - p["pred"]
        for (t, bk), g in p.groupby(["tour", "bucket"]):
            rows.append({"stat": s, "tour": t, "bucket": bk, "server_rows": int(len(g)),
                         "mean_resid": float(g["resid"].mean()),
                         "se": float(g["resid"].std(ddof=1) / np.sqrt(len(g))) if len(g) > 1 else np.nan,
                         "mean_resid_units_weighted": float(np.average(g["resid"], weights=g["d"])),
                         "mean_pred": float(g["pred"].mean()), "mean_c": float(g["c"].mean()),
                         "sd_c": float(g["c"].std(ddof=1)) if len(g) > 1 else np.nan})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0-dir", default=str(L.STAGE0_DIR))
    ap.add_argument("--only", default="pools,tuning,evidence,adj_shift,s3_resid,ios_resid")
    a = ap.parse_args()
    s0 = Path(a.stage0_dir)
    only = set(a.only.split(","))
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "stage0_dir": str(s0),
               "holdout_start": str(L.HOLDOUT_START.date()), "weightings": WEIGHTINGS, "groups": GROUPS, "files": {}}
    if only & {"pools", "tuning"}:
        m = L.load_matches(s0, ["tour", "year", "level", "map_level", "status", "format", "has_box", "evaluation"])
        if "pools" in only:
            summary["files"]["pools"] = str(write(pools(m), "pool_composition.csv").relative_to(ROOT))
            log("pools written")
        if "tuning" in only:
            summary["files"]["tuning"] = str(write(tuning(m), "tuning_pools.csv").relative_to(ROOT))
            log("tuning written")
    if "evidence" in only:
        ev, per = evidence(s0)
        summary["files"]["evidence"] = str(write(ev, "evidence_shares.csv").relative_to(ROOT))
        per.to_parquet(OUT / "evidence_shares_rows.parquet", index=False)
        summary["files"]["evidence_rows"] = str((OUT / "evidence_shares_rows.parquet").relative_to(ROOT))
        log("evidence written")
    if "adj_shift" in only:
        summary["files"]["adj_shift"] = str(write(adj_shift(s0), "adj_level_shift.csv").relative_to(ROOT))
        log("adj_shift written")
    if "s3_resid" in only:
        summary["files"]["s3_resid"] = str(write(s3_resid(s0), "stage3_residuals.csv").relative_to(ROOT))
        log("s3_resid written")
    if "ios_resid" in only:
        summary["files"]["ios_resid"] = str(write(ios_resid(s0), "ios_residuals.csv").relative_to(ROOT))
        log("ios_resid written")
    path = OUT / "lineage_checks.json"
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    prev_files = prev.get("files", {})
    prev_files.update(summary["files"])
    summary["files"] = prev_files
    path.write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
