"""R3-referee (follow-up), step 7: pooled serve rates by edition, as Stage 0 would hold them today and with the candidate.

Roland Garros 2019-2026 rows from sub_today.parquet / sub_cand.parquet (extract.py), kept where the version's box
passes Stage 0's checks (sim_rows.csv, simulate.py: box status full or no_svgms); service-game rates only where the
service games survive (full). RG's own statistics (official_rows.csv: my parse, every linked match whose record is
consistent) for the same editions. Comparators from Stage 0's own player table: the Australian Open, Wimbledon and the
US Open, and the clay Masters (Madrid, Rome, Monte Carlo), 2019-2026.
Rates: first serves in / serve points, first-serve points won / first serves in, second-serve points won / second
serves, aces / serve points, double faults / serve points and / second serves, serve points per game of the score,
break points faced per service game, hold rate.

Writes rates_by_edition.csv into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/rates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


def side_table(fr: pd.DataFrame, status: pd.Series) -> pd.DataFrame:
    fr = fr.copy()
    fr["key"] = F.rowkey(fr["_source_file"], fr["_row"])
    fr = fr[fr["key"].isin(status.index)].drop_duplicates("key")
    st = fr["key"].map(status)
    games = fr["score"].fillna("").map(lambda s: sum(B.score_counts(str(s), False)[2:4]))
    out = []
    for s in ("w", "l"):
        d = pd.DataFrame({"season": pd.to_numeric(fr["season"]).to_numpy(), "tour": fr["tour"].to_numpy(),
                          "draw": np.where(fr["qualifying"].astype(bool), "qual", "main"), "status": st.to_numpy(),
                          "games": games.to_numpy()})
        for c, col in F.NINE.items():
            d[c] = pd.to_numeric(fr[f"{s}_{col}"].astype("object").where(fr[f"{s}_{col}"].notna(), "").astype(str)
                                 .str.strip().replace("", np.nan), errors="coerce").to_numpy()
        out.append(d)
    return pd.concat(out, ignore_index=True)


def pooled(d: pd.DataFrame, label: str, event: str) -> pd.DataFrame:
    use = d[d["status"].isin(["full", "no_svgms"])].copy()
    sv = use[use["status"].eq("full") & use["sv_gms"].gt(0)]
    g, gs = use.groupby(["season", "tour", "draw"]), sv.groupby(["season", "tour", "draw"])
    t = pd.DataFrame({"player_rows": g.size(), "svpt": g["svpt"].sum(), "first_in": g["first_in"].sum(),
                      "first_won": g["first_won"].sum(), "second_won": g["second_won"].sum(), "ace": g["ace"].sum(),
                      "df": g["df"].sum(), "games": g["games"].sum() / 2})
    t["first_in_pct"] = 100 * t["first_in"] / t["svpt"]
    t["first_won_pct"] = 100 * t["first_won"] / t["first_in"]
    t["second_won_pct"] = 100 * t["second_won"] / (t["svpt"] - t["first_in"])
    t["ace_pct"] = 100 * t["ace"] / t["svpt"]
    t["df_pct"] = 100 * t["df"] / t["svpt"]
    t["df_per_second_pct"] = 100 * t["df"] / (t["svpt"] - t["first_in"])
    t["svpt_per_game"] = t["svpt"] / t["games"]
    t["rows_with_sv_gms"] = gs.size()
    t["bp_faced_per_sv_game"] = gs["bp_faced"].sum() / gs["sv_gms"].sum()
    t["hold_pct"] = 100 * (1 - (gs["bp_faced"].sum() - gs["bp_saved"].sum()) / gs["sv_gms"].sum())
    t = t.reset_index()
    t["event"], t["version"] = event, label
    return t


def official(o: pd.DataFrame) -> pd.DataFrame:
    o = o[o["code"].notna() & o["consistent_both"].eq(True) & ~(o["source"].eq("tml") & o["draw"].eq("main"))]
    rows = []
    for s in ("w", "l"):
        d = pd.DataFrame({"season": o["season"], "tour": o["tour"], "draw": o["draw"], "status": "full",
                          "games": o["games"]})
        for c in F.NINE:
            d[c] = o[f"my_{s}_{c}"]
        rows.append(d)
    d = pd.concat(rows, ignore_index=True)
    d = d[d["svpt"].gt(0)]
    d.loc[d["sv_gms"].isna(), "status"] = "no_svgms"
    return pooled(d, "RG's own record", "RG")


def main() -> int:
    sim = pd.read_csv(F.OUT / "sim_rows.csv", index_col=0)
    parts = []
    for v, f in (("Stage 0 today", "sub_today.parquet"), ("with the candidate", "sub_cand.parquet")):
        fr = pd.read_parquet(F.OUT / f)
        fr["_row"] = pd.to_numeric(fr["_row"]).astype("int64")
        fr = fr[fr["tourney_name"].eq("Roland Garros")]
        col = "today_box_status" if v == "Stage 0 today" else "cand_box_status"
        st = sim.loc[sim["tourney_name"].eq("Roland Garros"), col]
        parts.append(pooled(side_table(fr, st), v, "RG"))
    parts.append(official(pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)))
    # comparators: Stage 0's own player rows
    m = pd.read_parquet(F.S0 / "stage0_matches.parquet", columns=["match_id", "tournament_name", "year", "tour",
                                                                  "qualifying", "box_status", "score"])
    p = pd.read_parquet(F.S0 / "stage0_match_players.parquet",
                        columns=["match_id", "svpt", "first_in", "first_won", "second_won", "ace", "df", "sv_gms",
                                 "bp_faced", "bp_saved"])
    ev = {"Australian Open": "AO", "Wimbledon": "Wimbledon", "US Open": "US Open", "Us Open": "US Open",
          "Madrid Masters": "clay Masters", "Rome Masters": "clay Masters", "Monte Carlo Masters": "clay Masters"}
    m = m[m["tournament_name"].isin(ev) & m["year"].between(2019, 2026)]
    d = p.merge(m, on="match_id")
    d["games"] = d["score"].fillna("").map(lambda s: sum(B.score_counts(str(s), False)[2:4]))
    d = d.rename(columns={"year": "season", "box_status": "status"})
    d["draw"] = np.where(d["qualifying"], "qual", "main")
    for e in sorted(set(ev.values())):
        dd = d[d["tournament_name"].map(ev).eq(e)]
        parts.append(pooled(dd, "Stage 0 today", e))
    t = pd.concat(parts, ignore_index=True)
    keep = ["event", "season", "tour", "draw", "version", "player_rows", "first_in_pct", "first_won_pct",
            "second_won_pct", "ace_pct", "df_pct", "df_per_second_pct", "svpt_per_game", "rows_with_sv_gms",
            "bp_faced_per_sv_game", "hold_pct"]
    t = t[keep].round(3)
    t.to_csv(F.OUT / "rates_by_edition.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    rg = t[t["event"].eq("RG")]
    for c in ["first_in_pct", "second_won_pct", "ace_pct", "df_pct", "svpt_per_game", "hold_pct"]:
        print(f"\n===== RG {c}")
        print(rg.pivot_table(index=["tour", "draw", "season"], columns="version", values=c).round(2).to_string())
    print("\n===== comparators, first serves in % (Stage 0 today)")
    print(t[~t["event"].eq("RG")].pivot_table(index=["event", "tour", "draw"], columns="season",
                                               values="first_in_pct").round(1).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
