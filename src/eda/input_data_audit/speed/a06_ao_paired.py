"""Audit step 6: AO 2024 against the same players at AO 2022/2023/2025 (raw points): first serves in, second serves,
first-serve faults; additive vs multiplicative; per court; per day; the AO match centre's own published averages.
Read-only on the repo; writes scratch tables."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_columns", 60)

pm = pd.read_parquet(SCR / "pm_slam_points.parquet")
pts = pd.read_parquet(SCR / "pts_slam_points.parquet")
KINDS = ["in1", "in2", "fault1"]


def per_player_year(d: pd.DataFrame, slam: str, mq: str = "M") -> pd.DataFrame:
    d = d[(d["slam"] == slam) & (d["mq"] == mq) & d["player_id"].notna()]
    out = []
    for k in KINDS:
        n, m = d[f"size_{k}"].fillna(0), d[f"mean_{k}"]
        t = d.assign(s=n * m.fillna(0), n=n).groupby(["tour", "year", "player_id"])[["s", "n"]].sum()
        t[k] = t["s"] / t["n"].where(t["n"] > 0)
        t[f"n_{k}"] = t["n"]
        out.append(t[[k, f"n_{k}"]])
    return pd.concat(out, axis=1).reset_index()


def paired(py: pd.DataFrame, y0: int, y1: int, kind: str, tour: str, min_n: int = 20) -> dict:
    a = py[(py["year"] == y0) & (py["tour"] == tour) & (py[f"n_{kind}"] >= min_n)].set_index("player_id")[kind]
    b = py[(py["year"] == y1) & (py["tour"] == tour) & (py[f"n_{kind}"] >= min_n)].set_index("player_id")[kind]
    c = a.index.intersection(b.index)
    d = b[c] - a[c]
    if len(c) < 5:
        return {"tour": tour, "kind": kind, "from": y0, "to": y1, "players": len(c)}
    rng = np.random.default_rng(0)
    bs = [np.median(rng.choice(d.to_numpy(), len(d))) for _ in range(2000)]
    return {"tour": tour, "kind": kind, "from": y0, "to": y1, "players": int(len(c)), "median": round(float(d.median()), 2),
            "lo": round(float(np.percentile(bs, 2.5)), 2), "hi": round(float(np.percentile(bs, 97.5)), 2),
            "mean": round(float(d.mean()), 2), "ratio_median": round(float((b[c] / a[c]).median()), 4)}


py = per_player_year(pm, "AO")
rows = []
for tour in ("atp", "wta"):
    for kind in KINDS:
        for y0, y1 in [(2020, 2021), (2021, 2022), (2022, 2023), (2023, 2024), (2024, 2025), (2022, 2024), (2023, 2025),
                       (2022, 2025)]:
            rows.append(paired(py, y0, y1, kind, tour))
pr = pd.DataFrame(rows)
print("=== AO main draw, same players, km/h (positive = faster in the later year)")
print(pr.to_string(index=False))
pr.to_csv(SCR / "t_ao_paired_by_kind.csv", index=False)

# RG as the control Slam (same copy, same years)
py_rg = per_player_year(pm, "RG")
rows = []
for tour in ("atp", "wta"):
    for kind in KINDS:
        for y0, y1 in [(2019, 2020), (2020, 2021), (2021, 2022), (2022, 2023), (2023, 2024), (2024, 2025), (2025, 2026),
                       (2023, 2025)]:
            rows.append(paired(py_rg, y0, y1, kind, tour))
print("=== RG main draw, same players (control)")
print(pd.DataFrame(rows).to_string(index=False))
pd.DataFrame(rows).to_csv(SCR / "t_rg_paired_by_kind.csv", index=False)

# additive vs multiplicative: point-level first serves in of players present in 2023, 2024 and 2025 (men, main draw)
for tour in ("atp", "wta"):
    q = pts[(pts["slam"] == "AO") & (pts["mq"] == "M") & (pts["kind"] == "in1") & (pts["tour"] == tour)
            & np.isfinite(pts["spd"]) & pts["player_id"].notna()]
    have = q.groupby("player_id")["year"].agg(lambda s: set(s))
    common = have[have.apply(lambda s: {2023, 2024, 2025} <= s)].index
    q = q[q["player_id"].isin(common)]
    qs = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
    t = q.groupby("year")["spd"].quantile(qs).unstack()
    t["n"] = q.groupby("year").size()
    print(f"=== {tour}: point-level first serves in, players at AO 2023, 2024 and 2025 ({len(common)}): quantiles")
    print(t.round(1).to_string())
    # within-player quantile shift (each player's own decile 2024 minus 2023)
    sh = []
    for pid, g in q.groupby("player_id"):
        a, b = g[g["year"] == 2023]["spd"], g[g["year"] == 2024]["spd"]
        c = g[g["year"] == 2025]["spd"]
        if min(len(a), len(b), len(c)) < 30:
            continue
        sh.append([pid] + [b.quantile(x) - a.quantile(x) for x in qs] + [b.quantile(x) - c.quantile(x) for x in qs])
    sh = pd.DataFrame(sh, columns=["pid"] + [f"24-23 q{x}" for x in qs] + [f"24-25 q{x}" for x in qs])
    print(f"   per-player quantile shifts, median over {len(sh)} players:")
    print(sh.drop(columns="pid").median().round(2).to_string())

# decimal share and zero-speed share per year of the raw strings (in-play first serves)
B = ROOT / "data/dump/points/slam_ball_tracking/points"
for y in range(2020, 2025):
    p = pd.read_parquet(B / f"AO_{y}.parquet", columns=["serve_num", "point_end_type", "serve_speed_kph", "tour"])
    s = p["serve_speed_kph"].astype(str)
    inplay = ~p["point_end_type"].astype(str).isin(["Faulty Serve"])
    dec = s.str.contains(r"\.\d", regex=True)
    v = pd.to_numeric(s.str.extract(r"([\d.]+)")[0], errors="coerce")
    print(f"AO {y}: in-play rows {int(inplay.sum())}, decimal share in-play {dec[inplay].mean():.4f}, faults "
          f"{dec[~inplay].mean():.4f}; in-play speeds <=40 or NA {(~(v[inplay] > 40)).mean():.4f}; "
          f"in-play mean (men) {v[inplay & (v > 40) & p['tour'].eq('M') & p['serve_num'].eq(1)].mean():.2f}")
