"""Audit step 12: every edition of the panel against the same players elsewhere.

Model (per tour, the panel's use rows, weights 1/(22 + 12.4^2/n) as the project's offsets):
    y = alpha_{player, season} + gamma_{edition} + e      (edition = tournament_id | M/Q | basis, as the panel)
gamma is identified by each player's other matches of the same season. Then
    spike_e  = gamma_e - median(gamma of the same event, mq, basis in the other years)   (one-year jumps)
    step     = gamma_e - gamma of the same event's previous year                          (breaks)
and the residuals r = y - alpha - gamma are scanned within editions by court (Slams), by day and by round.
Read-only on the repo; writes scratch tables t_edition_effects.csv, t_within_cells.csv."""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 800)
pd.set_option("display.max_columns", 40)

P = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_panel.parquet")
u = P[P["use"]].copy()
u["season"] = u["year"]

# ---------------------------------------------------------------- courts for Slam rows
def courts() -> pd.Series:
    out = {}
    sk = ROOT / "data/dump/points/sackmann_archive/slam_pointbypoint"
    for f in sk.glob("*-matches.parquet"):
        if "doubles" in f.name or "mixed" in f.name:
            continue
        m = pd.read_parquet(f, columns=["match_id", "court_name"])
        out.update(dict(zip("pbp|" + m["match_id"].astype(str), m["court_name"].astype(str))))
    for site in ("wimbledon", "usopen"):
        m = pd.read_parquet(ROOT / f"data/dump/points/{site}/matches.parquet",
                            columns=["year", "event", "match_id", "entry.courtName"])
        k = "st|" + site + "_" + m["year"].astype(str) + "_" + m["event"].astype(str) + "_" + m["match_id"].astype(str)
        out.update(dict(zip(k, m["entry.courtName"].astype(str))))
    m = pd.read_parquet(ROOT / "data/dump/points/slam_ball_tracking/matches.parquet",
                        columns=["slam", "year", "match_id", "court_name"])
    m["code"] = m["match_id"].astype(str).str.split("_").str[-1]
    k = "he|" + m["slam"].astype(str) + "_" + m["year"].astype(str) + "_" + m["match_id"].astype(str)
    out.update(dict(zip(k, m["court_name"].astype(str))))
    m = pd.read_parquet(ROOT / "data/dump/points/infosys_slams/matches.parquet",
                        columns=["slam", "year", "match_id", "court_name"])
    k = "is|" + m["slam"].astype(str) + "_" + m["year"].astype(str) + "_" + m["match_id"].astype(str)
    out.update(dict(zip(k, m["court_name"].astype(str))))
    m = pd.read_parquet(ROOT / "data/dump/points/ausopen/matches.parquet", columns=["record_key", "court_name"])
    out.update(dict(zip("mc|" + m["record_key"].astype(str), m["court_name"].astype(str))))
    return pd.Series(out)


C = courts()
pref = u["source"].map({"slam_pbp": "pbp|", "slamtracker": "st|", "slam_tracking": "he|", "infosys_slams": "is|",
                        "ausopen_mc": "mc|"})
key = pref + u["source_key"].astype(str)
u["court"] = key.map(C).where(pref.notna())
u["court"] = (u["court"].fillna("").str.replace("Show Court", "Court").str.replace("-", " ").str.strip()
              .str.upper().replace({"": np.nan, "NAN": np.nan}))
print("Slam use rows with a court:", int(u.loc[u["level"].eq("GS"), "court"].notna().sum()), "of",
      int(u["level"].eq("GS").sum()))


# ---------------------------------------------------------------- the fit
def fit(d: pd.DataFrame, iters: int = 500):
    w = 1.0 / (22.0 + 12.4 ** 2 / np.maximum(d["n"].to_numpy(float), 1))
    y = d["y"].to_numpy(float)
    pi, _ = pd.factorize(d["player_id"].astype(str) + "|" + d["season"].astype(str))
    ei, eu = pd.factorize(d["edition"])
    g = np.zeros(len(eu))
    wp, we = np.bincount(pi, w), np.bincount(ei, w)
    for _ in range(iters):
        a = np.bincount(pi, w * (y - g[ei])) / wp
        gn = np.bincount(ei, w * (y - a[pi])) / we
        if np.max(np.abs(gn - g)) < 1e-7:
            g = gn
            break
        g = gn
    a = np.bincount(pi, w * (y - g[ei])) / wp
    r = y - a[pi] - g[ei]
    # identification: players with >= 2 editions in the season
    multi = pd.Series(ei).groupby(pi).transform("nunique").to_numpy() > 1
    dof = max(int(multi.sum()) - len(eu) - len(np.unique(pi[multi])), 1)
    phi = float(np.sum(w[multi] * r[multi] ** 2) / dof)          # dispersion (1 = the weights' variances hold)
    ident = np.bincount(ei, w * multi)
    se = np.sqrt(phi / np.maximum(ident, 1e-9))
    print(f"  dispersion phi = {phi:.3f}; identified rows {int(multi.sum())}")
    ed = pd.DataFrame({"edition": eu, "gamma": g, "rows": np.bincount(ei), "rows_ident": np.bincount(ei, multi),
                       "se": se})
    return ed, r, multi


eds, resid = [], []
for tour in ("atp", "wta"):
    d = u[u["tour"] == tour].reset_index(drop=True)
    ed, r, multi = fit(d)
    # centre: the tour's main-draw editions of each season average 0 (men); women: the Slam main draws
    info = d.drop_duplicates("edition").set_index("edition")[["tour", "year", "event", "slam", "mq", "basis", "level",
                                                              "family", "tournament_name", "tdate"]]
    ed = ed.join(info, on="edition")
    src = d.groupby("edition")["source"].agg(lambda s: "+".join(sorted(set(s))))
    ed["sources"] = ed["edition"].map(src)
    tour_ref = ed["family"].eq("tour|M")
    slam_ref = ed["family"].isin(["AO|M", "RG|M", "W|M", "USO|M"])
    for yv, gg in ed.groupby("year"):
        rr = gg[tour_ref.loc[gg.index]]
        if rr["rows"].sum() < 200:                     # the project's rule: Slam main draws when the tour is thin
            rr = gg[slam_ref.loc[gg.index]]
        if len(rr):
            ed.loc[gg.index, "gamma_c"] = gg["gamma"] - np.average(rr["gamma"], weights=rr["rows"])
            ed.loc[gg.index, "ref"] = "tour|M" if rr["family"].eq("tour|M").all() else "slam|M"
    eds.append(ed)
    d["resid"], d["ident"] = r, multi
    resid.append(d)
E = pd.concat(eds, ignore_index=True)
R = pd.concat(resid, ignore_index=True)
R.drop(columns=["tournament_date"], errors="ignore").to_parquet(SCR / "panel_resid.parquet", index=False)

# ---------------------------------------------------------------- spikes and steps per event
E["ev"] = E["event"].astype(str) + "|" + E["mq"] + "|" + E["basis"]
rows = []
for (tour, ev), g in E.groupby(["tour", "ev"]):
    g = g.sort_values("year")
    for i, r in g.iterrows():
        oth = g[(g["year"] != r["year"]) & (g["rows_ident"] >= 10)]
        prev = g[g["year"] == r["year"] - 1]
        nxt = g[g["year"] == r["year"] + 1]
        rows.append({"idx": i, "spike": r["gamma_c"] - oth["gamma_c"].median() if len(oth) else np.nan,
                     "n_other_years": len(oth),
                     "step_from_prev": r["gamma_c"] - prev["gamma_c"].iloc[0] if len(prev) else np.nan,
                     "step_to_next": nxt["gamma_c"].iloc[0] - r["gamma_c"] if len(nxt) else np.nan})
S = pd.DataFrame(rows).set_index("idx")
E = E.join(S)
E.to_csv(SCR / "t_edition_effects.csv", index=False)

cols = ["tour", "edition", "tournament_name", "year", "mq", "basis", "sources", "rows", "rows_ident", "gamma_c", "se",
        "spike", "n_other_years", "step_from_prev", "step_to_next"]
print("=== Slam editions (gamma_c: edition effect, km/h, same player-season elsewhere = 0 reference)")
print(E[E["level"].eq("GS")].sort_values(["tour", "event", "mq", "year"])[cols].round(2).to_string(index=False))
print("=== spread of one-year spikes (edition minus the same event's median of other years), by family group")
E["fgroup"] = np.where(E["level"].eq("GS"), "slam", E["family"].astype(str))
ok = (E["rows_ident"] >= 20) & E["spike"].notna() & (E["n_other_years"] >= 2)
print(E[ok].groupby(["tour", "fgroup"])["spike"].describe().round(2).to_string())
sd_norm = E[ok & E["fgroup"].isin(["tour|M", "tour|Q"])].groupby("tour")["spike"].std()
print("normal SD of tour spikes:", sd_norm.round(2).to_dict())
flag = E[ok & (E["spike"].abs() >= 2.0 + 2 * 1.71) & (E["spike"].abs() >= 3 * E["se"])]
print(f"=== flagged editions (|spike| >= 2 km/h beyond 2 normal SD (= 5.4) and >= 3 SE, >= 20 identified rows): "
      f"{len(flag)}")
print(flag.sort_values(["tour", "spike"])[cols].round(2).to_string(index=False))
flag2 = E[ok & (E["spike"].abs() >= 3.0) & (E["spike"].abs() >= 3 * E["se"])]
print(f"=== editions with |spike| >= 3 km/h and >= 3 SE: {len(flag2)}")
print(flag2.sort_values(["tour", "year", "spike"])[cols].round(2).to_string(index=False))
steps = E[(E["rows_ident"] >= 20) & ((E["step_from_prev"].abs() >= 3.0) | (E["step_to_next"].abs() >= 3.0))
          & E["level"].eq("GS")]
print("=== Slam editions with a step of >= 3 km/h to or from the adjacent year")
print(steps.sort_values(["tour", "event", "year"])[cols].round(2).to_string(index=False))

# ---------------------------------------------------------------- within-edition cells
R["date"] = pd.to_datetime(R["obs"], unit="D").dt.date
cells = []
for by in ("court", "date", "round"):
    q = R[R["ident"] & R[by].notna()]
    w = 1.0 / (22.0 + 12.4 ** 2 / np.maximum(q["n"].to_numpy(float), 1))
    g = q.assign(w=w, wr=w * q["resid"]).groupby(["tour", "edition", by]).agg(
        rows=("resid", "size"), mean_resid=("resid", "mean"), w=("w", "sum"), wr=("wr", "sum"),
        sd=("resid", "std")).reset_index()
    g["wmean"] = g["wr"] / g["w"]
    g["t"] = g["mean_resid"] / (g["sd"] / np.sqrt(g["rows"]))
    g["by"], g["cell"] = by, g[by].astype(str)
    cells.append(g.drop(columns=[by]))
Wc = pd.concat(cells, ignore_index=True)
Wc = Wc.merge(E[["tour", "edition", "tournament_name", "year", "mq", "basis", "sources"]], on=["tour", "edition"],
              how="left")
Wc.to_csv(SCR / "t_within_cells.csv", index=False)
fl = Wc[(Wc["rows"] >= 8) & (Wc["mean_resid"].abs() >= 2.0) & (Wc["t"].abs() >= 3)]
print(f"=== within-edition cells with >= 8 rows, |mean residual| >= 2 km/h and |t| >= 3: {len(fl)}")
for by in ("court", "date", "round"):
    x = fl[fl["by"] == by].sort_values(["tour", "year", "edition", "mean_resid"])
    print(f"--- by {by}: {len(x)}")
    print(x[["tour", "tournament_name", "year", "mq", "basis", "sources", "cell", "rows", "mean_resid", "wmean", "t"]]
          .round(2).to_string(index=False))
