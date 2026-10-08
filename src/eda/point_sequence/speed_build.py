"""Item C (audit_scoped.md section 2): the serve-speed change feature for the residual screen. Builds features only;
reads no match result.

Statistic per player P before match m (own history in order: P's earlier events, and earlier rounds of the same
event, as predictability_diagnostic.common.asof_sums; other events of the same week never count):

    m2  = mean speed of P's first serves in, over P's earlier matches whose best-estimate day (match-timing `obs`) is
          at most 14 days before m's
    m52 = the same over at most 364 days
    xP  = m2 - m52 (km/h); missing when P has no timed first serve in the 2-week window (m52 then always exists)

The feature of a match is x = xA - xB, missing when either side is missing.

Speeds: data/studies/shot_level/stage1_match_stats.parquet, spd1_n (sum of speeds of first serves in that carry a speed)
and spd1_d (their count) per Stage 0 match and side, which the shot-level study aggregated from its point tables
(stage1_points_<source>.parquet, column `speed`; one source per match in its priority order; a match counts only when
at least half of its first serves in are timed). Sources with speeds: Infosys (ATP tour and qualifying, from 2021,
dense from 2022), Hawk-Eye's AO/RG copy, SlamTracker, Sackmann's Slam point-by-point.

Also built (secondaries, pre-registered in speed_prereg.md):
    x_surf    the same windows on surface-centred speeds (each match's speeds minus the frozen 2010-2018 tour x surface
              mean of the shot-level study, stage2_constants.json `mu`)
    x_evt     the same windows on event-family-centred speeds: each match's speeds minus its family's offset from the
              tour mean (families AO, RG, W, USO at the Slams and "tour" elsewhere, i.e. Infosys), offsets frozen on
              timed first serves of matches to 2021; it removes the tracking systems' level differences (Infosys reads
              men about 5-8 km/h faster than the US Open's feed)
    x_shot    the shot-level study's own feature `spd1_change|off|dec2-w52` (two-week half-life minus 52 weeks, shrunk
              toward the tour mean, surface-centred; stage2_features.parquet), reused as it is

Only matches to 2024 are read (2025-26 is a closed holdout). The frame is the meta-stack walk-forward table's matches
(data/studies/meta_stack/walkforward.parquet: main-tour main draws with closing odds), read without its result column.

Run: ./python.sh src/eda/point_sequence/speed_build.py
Writes data/studies/point_sequence/speed_features.parquet and speed_build_summary.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PD  # noqa: E402

OUT = ROOT / "data" / "studies" / "point_sequence"
SHOT = ROOT / "data" / "studies" / "shot_level"
WF = ROOT / "data" / "studies" / "meta_stack" / "walkforward.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
FEATURES = OUT / "speed_features.parquet"
SUMMARY = OUT / "speed_build_summary.json"
LAST_YEAR = 2024
SHORT, LONG = 14.0, 364.0
SURFACES = ("Hard", "Clay", "Grass", "Carpet")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def player_rows() -> pd.DataFrame:
    """Every Stage 0 player-match to 2024 with the own-history keys, the clock day and the speed sums (0 where none)."""
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "level", "qualifying", "round", "round_order",
                                             "surface", "tournament_id", "tournament_date", "order", "player_a_id",
                                             "player_b_id"], filters=[("year", "<=", LAST_YEAR)])
    rows = pd.concat([m.assign(side="A", player_id=m["player_a_id"]), m.assign(side="B", player_id=m["player_b_id"])],
                     ignore_index=True).drop(columns=["player_a_id", "player_b_id"])
    tm = pd.read_parquet(TIMING, columns=["match_id", "obs"], filters=[("year", "<=", LAST_YEAR)])
    rows = rows.merge(tm, on="match_id", how="left")
    st = pd.read_parquet(SHOT / "stage1_match_stats.parquet", columns=["match_id", "side", "spd1_n", "spd1_d",
                                                                        "spd1_src"])
    rows = rows.merge(st, on=["match_id", "side"], how="left")
    rows["spd1_n"] = rows["spd1_n"].fillna(0.0)
    rows["spd1_d"] = rows["spd1_d"].fillna(0.0)
    # surface-centred sums: minus the frozen tour x surface mean per timed serve
    mu = json.loads((SHOT / "stage2_constants.json").read_text(encoding="utf-8"))["mu"]
    sf = rows["surface"].where(rows["surface"].isin(SURFACES), "all")
    mus = np.array([mu.get(f"spd1|{t}|{s}", mu[f"spd1|{t}|all"]) for t, s in zip(rows["tour"], sf)])
    rows["spd1_c"] = rows["spd1_n"] - rows["spd1_d"] * mus
    # event-family-centred sums: minus the family's frozen offset from the tour mean (families: AO, RG, W, USO at the
    # Slams, "tour" elsewhere, i.e. Infosys); offsets from timed first serves of matches to 2021 only
    tn = pd.read_parquet(PD.MATCHES, columns=["match_id", "tournament_name"], filters=[("year", "<=", LAST_YEAR)])
    rows = rows.merge(tn, on="match_id", how="left")
    rows["family"] = family_of(rows["level"], rows["tournament_name"])
    early = (rows["year"] <= 2021) & (rows["spd1_d"] > 0)
    fam = rows[early].groupby(["tour", "family"])[["spd1_n", "spd1_d"]].sum()
    tour_mean = rows[early].groupby("tour")["spd1_n"].sum() / rows[early].groupby("tour")["spd1_d"].sum()
    off = (fam["spd1_n"] / fam["spd1_d"]).sub(tour_mean, level="tour")
    OFFSETS.clear()
    OFFSETS.update({f"{t}|{f}": float(v) for (t, f), v in off.items()})
    o = np.array([OFFSETS.get(f"{t}|{f}", 0.0) for t, f in zip(rows["tour"], rows["family"])])
    rows["spd1_e"] = rows["spd1_n"] - rows["spd1_d"] * o
    rows["tdate"] = rows["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    return rows


OFFSETS: dict[str, float] = {}


def family_of(level: pd.Series, name: pd.Series) -> pd.Series:
    n = name.fillna("").str.lower()
    out = np.where(n.str.contains("australian|aus open"), "AO",
                   np.where(n.str.contains("roland|french open"), "RG",
                            np.where(n.str.contains("wimbledon"), "W",
                                     np.where(n.str.contains("us open|u.s. open"), "USO", "tour"))))
    return pd.Series(np.where(level.eq("GS").to_numpy(), out, "tour"), index=level.index)


def window_feature(rows: pd.DataFrame, targets: np.ndarray, n_col: str = "spd1_n") -> pd.DataFrame:
    """For each target row (an index into rows), the player's window sums over earlier own-history matches."""
    r = rows
    keys = list(zip(r["tour"].to_numpy(), r["player_id"].to_numpy()))
    order = np.lexsort((r["round_order"].to_numpy(), r["tdate"].to_numpy(), r["player_id"].to_numpy(),
                        r["tour"].to_numpy()))
    tour_s, pid_s = r["tour"].to_numpy()[order], r["player_id"].to_numpy()[order]
    starts = np.flatnonzero(np.r_[True, (tour_s[1:] != tour_s[:-1]) | (pid_s[1:] != pid_s[:-1])])
    ends = np.r_[starts[1:], len(order)]
    grp = {}
    tdate, tid, ro, obs = (r["tdate"].to_numpy(), r["tournament_id"].to_numpy(), r["round_order"].to_numpy(),
                           r["obs"].to_numpy())
    nn, dd = r[n_col].to_numpy(float), r["spd1_d"].to_numpy(float)
    for s, e in zip(starts, ends):
        idx = order[s:e]
        idx = idx[dd[idx] > 0]                      # only timed history matters
        grp[(tour_s[s], pid_s[s])] = idx
    out = np.full((len(targets), 4), 0.0)
    for k, t in enumerate(targets):
        h = grp.get(keys[t])
        if h is None or h.size == 0:
            continue
        earlier = (tdate[h] < tdate[t]) | ((tid[h] == tid[t]) & (ro[h] < ro[t]))
        age = obs[t] - obs[h]
        w52 = earlier & (age <= LONG)
        if not w52.any():
            continue
        w2 = earlier & (age <= SHORT)
        out[k] = (nn[h][w2].sum(), dd[h][w2].sum(), nn[h][w52].sum(), dd[h][w52].sum())
    return pd.DataFrame(out, columns=["s2", "n2", "s52", "n52"], index=targets)


def side_values(win: pd.DataFrame) -> pd.Series:
    m2 = win["s2"] / win["n2"].where(win["n2"] > 0)
    m52 = win["s52"] / win["n52"].where(win["n52"] > 0)
    return m2 - m52


def match_features(rows: pd.DataFrame, frame_ids: set) -> pd.DataFrame:
    tgt = rows.index[rows["match_id"].isin(frame_ids)].to_numpy()
    raw = window_feature(rows, tgt, "spd1_n")
    cen = window_feature(rows, tgt, "spd1_c")
    evt = window_feature(rows, tgt, "spd1_e")
    side = rows.loc[tgt, ["match_id", "side"]].copy()
    side["x_raw_side"] = side_values(raw).to_numpy()
    side["x_surf_side"] = side_values(cen).to_numpy()
    side["x_evt_side"] = side_values(evt).to_numpy()
    side["n2"], side["n52"] = raw["n2"].to_numpy(), raw["n52"].to_numpy()
    cols = ["x_raw_side", "x_surf_side", "x_evt_side", "n2", "n52"]
    a = side[side["side"] == "A"].set_index("match_id")
    b = side[side["side"] == "B"].set_index("match_id")
    f = a[cols].add_suffix("_a").join(b[cols].add_suffix("_b"), how="inner")
    f["x_raw"] = f["x_raw_side_a"] - f["x_raw_side_b"]
    f["x_surf"] = f["x_surf_side_a"] - f["x_surf_side_b"]
    f["x_evt"] = f["x_evt_side_a"] - f["x_evt_side_b"]
    return f.reset_index()


def leak_probe(rows: pd.DataFrame, n_cuts: int = 8, seed: int = 0) -> dict:
    """Black-box check: speeds of every player-match at or after a random cut in the chronological order are replaced
    with noise and the feature recomputed; no target before the cut, nor the cut itself, may change."""
    rng = np.random.default_rng(seed)
    pool = rows.index[rows["year"].between(2021, LAST_YEAR)].to_numpy()
    tgt = rng.choice(pool, 4000, replace=False)
    base = side_values(window_feature(rows, tgt)).to_numpy()
    orders = np.sort(rows.loc[tgt, "order"].unique())
    changed_before = changed_at = 0
    for c in rng.choice(orders[len(orders) // 5:], n_cuts, replace=False):
        pert = rows.copy()
        late = (pert["order"] >= c) & (pert["spd1_d"] > 0)
        pert.loc[late, "spd1_n"] = rng.uniform(100, 250, int(late.sum())) * pert.loc[late, "spd1_d"]
        got = side_values(window_feature(pert, tgt)).to_numpy()
        diff = ~np.isclose(got, base, equal_nan=True)
        o = rows.loc[tgt, "order"].to_numpy()
        changed_before += int((diff & (o < c)).sum())
        changed_at += int((diff & (o == c)).sum())
    return {"cuts": n_cuts, "targets": int(len(tgt)), "changed_before_cut": changed_before,
            "changed_at_cut": changed_at}


def main() -> None:
    log("reading Stage 0, timing and shot-level speeds (to 2024)")
    rows = player_rows()
    wf = pd.read_parquet(WF, columns=["match_id", "tour", "year", "tournament_date"],
                         filters=[("year", "<=", LAST_YEAR)])
    ids = set(wf["match_id"])
    log(f"{len(rows)} player-matches; frame {len(wf)} matches")
    f = match_features(rows, ids)
    shot = pd.read_parquet(SHOT / "stage2_features.parquet", columns=["match_id", "spd1_change|off|dec2-w52"],
                           filters=[("year", "<=", LAST_YEAR)]).rename(columns={"spd1_change|off|dec2-w52": "x_shot"})
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "level", "round", "surface", "qualifying"],
                        filters=[("year", "<=", LAST_YEAR)])
    out = wf.merge(f, on="match_id", how="left").merge(shot, on="match_id", how="left").merge(m, on="match_id",
                                                                                              how="left")
    out.to_parquet(FEATURES, index=False)
    log("leak probe")
    probe = leak_probe(rows)
    log(f"probe: {probe}")
    # coverage by tour x window x subset (feature only)
    out["window"] = np.select([out["year"].between(2015, 2021), out["year"].between(2022, 2024)],
                              ["discovery", "replication"], "other")
    out["gs"] = out["level"].eq("GS")
    cov = []
    for (tour, w, gs), g in out[out["window"] != "other"].groupby(["tour", "window", "gs"]):
        cov.append({"tour": tour, "window": w, "slam": bool(gs), "frame_matches": int(len(g)),
                    "x_raw": int(g["x_raw"].notna().sum()), "x_shot": int(g["x_shot"].notna().sum()),
                    "x_raw_share": round(float(g["x_raw"].notna().mean()), 3)})
    by_year = (out.assign(has=out["x_raw"].notna()).groupby(["tour", "year", "gs"])["has"].agg(["size", "sum"])
               .reset_index().rename(columns={"size": "frame", "sum": "x_raw"}))
    xs = out["x_raw"].dropna()
    summary = {"built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "last_year_read": LAST_YEAR,
               "frame_matches": int(len(out)), "coverage": cov, "coverage_by_year": by_year.to_dict(orient="records"),
               "x_raw_describe_kmh": xs.describe().round(3).to_dict(),
               "x_raw_sd_by_tour": out.groupby("tour")["x_raw"].std().round(4).to_dict(),
               "corr_raw_shot": float(out[["x_raw", "x_shot"]].dropna().corr().iloc[0, 1]),
               "corr_raw_surf": float(out[["x_raw", "x_surf"]].dropna().corr().iloc[0, 1]),
               "corr_raw_evt": float(out[["x_raw", "x_evt"]].dropna().corr().iloc[0, 1]),
               "event_family_offsets_kmh_frozen_to_2021": OFFSETS,
               "leak_probe": probe}
    SUMMARY.write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    log(f"wrote {FEATURES.name}; coverage:\n{pd.DataFrame(cov).to_string(index=False)}")


if __name__ == "__main__":
    main()
