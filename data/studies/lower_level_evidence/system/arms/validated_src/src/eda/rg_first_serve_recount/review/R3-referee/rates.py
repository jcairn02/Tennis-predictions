"""R3-referee, step 4: pooled serve rates by edition, before and after the fix, against the other editions.

Sackmann's rows (raw_subset.parquet) with a full box that passes Stage 0's per-side checks, pooled per event, year,
tour and draw: first serves in (1stIn / svpt), first-serve points won (1stWon / 1stIn), second-serve points won
(2ndWon / (svpt - 1stIn)), double faults per second-serve point (df / (svpt - 1stIn)) and serve points won (unchanged
by any split fix). For RG 2022-2025 and the Paris Olympics: before, after the whole proposal, and after this
reviewer's scope (scope.csv, when present); and RG's own statistics (every consistent record, parsed from the raw API
files) for RG 2019-2025. Comparators: RG 2019-2021 (the clean editions), the other Slams, the clay Masters, Tokyo 2020.

Writes rates_by_edition.csv. Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/rates.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3common as C  # noqa: E402

OUT = C.OUT
EVENT = {"Roland Garros": "RG", "Paris Olympics": "OG Paris", "Tokyo Olympics": "OG Tokyo", "Australian Open": "AO",
         "Wimbledon": "WIM", "US Open": "USO", "Us Open": "USO", "Madrid Masters": "clay M1000", "Madrid": "clay M1000",
         "Rome Masters": "clay M1000", "Rome": "clay M1000", "Monte Carlo Masters": "clay M1000"}


def corrected(raw: pd.DataFrame, table: pd.DataFrame) -> pd.DataFrame:
    """raw with the split counts of the given sides replaced (table: source_file, source_row, side, first_in,
    first_won, second_won)."""
    r = raw.copy()
    idx = {(f, int(s)): i for i, f, s in zip(r.index, r["_source_file"], r["_row"])}
    for t in table.itertuples():
        i = idx[(t.source_file, int(t.source_row))]
        for c, v in (("1stIn", t.first_in), ("1stWon", t.first_won), ("2ndWon", t.second_won)):
            r.at[i, f"{t.side}_{c}"] = str(int(v))
    return r


def pooled(raw: pd.DataFrame, label: str) -> pd.DataFrame:
    s = C.side_rows(raw)
    s["event"] = s["tourney_name"].map(EVENT)
    s = s[s["event"].notna()]
    full = s[["raw_svpt", "raw_first_in", "raw_first_won", "raw_second_won", "raw_df", "raw_ace"]].notna().all(axis=1) \
        & s["raw_svpt"].gt(0)
    ok = full & ~(s["raw_first_in"] > s["raw_svpt"]) & ~(s["raw_first_won"] > s["raw_first_in"]) \
        & ~(s["raw_second_won"] > s["raw_svpt"] - s["raw_first_in"]) & ~(s["raw_df"] > s["raw_svpt"] - s["raw_first_in"])
    s = s[ok]
    s["draw"] = np.where(s["qualifying"], "qual", "main")
    g = s.groupby(["event", "season", "tour", "draw"])
    out = pd.DataFrame({"sides": g.size(), "svpt": g["raw_svpt"].sum(), "fi": g["raw_first_in"].sum(),
                        "fw": g["raw_first_won"].sum(), "sw": g["raw_second_won"].sum(), "df": g["raw_df"].sum()})
    out["first_in_pct"] = 100 * out["fi"] / out["svpt"]
    out["first_won_pct"] = 100 * out["fw"] / out["fi"]
    out["second_won_pct"] = 100 * out["sw"] / (out["svpt"] - out["fi"])
    out["df_per_second_pct"] = 100 * out["df"] / (out["svpt"] - out["fi"])
    out["spw_pct"] = 100 * (out["fw"] + out["sw"]) / out["svpt"]
    out = out.reset_index()
    out["version"] = label
    return out


def official_rg() -> pd.DataFrame:
    api = C.rg_api_all()
    api = api[api["consistent_both"]].copy()
    api["tour"] = np.where(api["code"].str[1].eq("D"), "wta", "atp")
    api["draw"] = np.where(api["code"].str[0].eq("Q"), "qual", "main")
    g = api.groupby(["year", "tour", "draw"])
    out = pd.DataFrame({"sides": g.size(), "svpt": g["svpt"].sum(), "fi": g["first_in"].sum(), "fw": g["first_won"].sum(),
                        "sw": g["second_won"].sum(), "df": g["df"].sum()})
    out["first_in_pct"] = 100 * out["fi"] / out["svpt"]
    out["first_won_pct"] = 100 * out["fw"] / out["fi"]
    out["second_won_pct"] = 100 * out["sw"] / (out["svpt"] - out["fi"])
    out["df_per_second_pct"] = 100 * out["df"] / (out["svpt"] - out["fi"])
    out["spw_pct"] = 100 * (out["fw"] + out["sw"]) / out["svpt"]
    out = out.reset_index().rename(columns={"year": "season"})
    out["event"], out["version"] = "RG", "official (RG statistics)"
    return out


def within_edition() -> pd.DataFrame:
    """Within each edition: the rows where Sackmann and the official record agree (class equal) against the proposed
    rows as each record reads them. Where no clean edition exists (the Olympics), the undisputed rows of the same
    event are the yardstick: the record that is right should read the disputed rows like the undisputed ones."""
    d = C.lead_rows()
    d = d[(d["event"].eq("OG")) | d["year"].between(2022, 2025)]
    out = []
    for (ev, tour, draw), g in d.groupby(["event", "tour", "draw"]):
        eq, pr = g[g["cls"].eq("equal")], g[g["proposed"].astype(bool)]
        rec = {"event": ev, "tour": tour, "draw": draw, "equal_rows": len(eq), "proposed_rows": len(pr)}
        for lab, h, p in (("equal", eq, "raw"), ("proposed_official", pr, "off"), ("proposed_sackmann", pr, "raw")):
            sv, fi = h[f"{p}_svpt"].sum(), h[f"{p}_first_in"].sum()
            rec[f"{lab}_first_in_pct"] = round(100 * fi / sv, 2)
            rec[f"{lab}_first_won_pct"] = round(100 * h[f"{p}_first_won"].sum() / fi, 2)
            rec[f"{lab}_second_won_pct"] = round(100 * h[f"{p}_second_won"].sum() / (sv - fi), 2)
            rec[f"{lab}_df_per_second_pct"] = round(100 * h[f"{p}_df"].sum() / (sv - fi), 2)
        out.append(rec)
    return pd.DataFrame(out)


def main() -> int:
    w = within_edition()
    w.to_csv(OUT / "rates_within_edition.csv", index=False)
    print(w.to_string())
    raw = C.raw_subset()
    raw = raw[pd.to_numeric(raw["season"]).between(2019, 2025)]
    prop = pd.read_csv(C.STUDY / "proposed_corrections.csv")
    rows = []
    for r in prop.itertuples():
        for s in ("w", "l"):
            if pd.notna(getattr(r, f"{s}_1stIn")):
                rows.append({"source_file": r.source_file, "source_row": r.source_row, "side": s,
                             "first_in": getattr(r, f"{s}_1stIn"), "first_won": getattr(r, f"{s}_1stWon"),
                             "second_won": getattr(r, f"{s}_2ndWon")})
    whole = pd.DataFrame(rows)
    parts = [pooled(raw, "Sackmann as read"), pooled(corrected(raw, whole), "after the whole proposal")]
    if (OUT / "scope.csv").exists():
        parts.append(pooled(corrected(raw, pd.read_csv(OUT / "scope.csv")), "after R3's scope"))
    parts.append(official_rg())
    t = pd.concat(parts, ignore_index=True)
    t = t[["event", "season", "tour", "draw", "version", "sides", "first_in_pct", "first_won_pct", "second_won_pct",
           "df_per_second_pct", "spw_pct"]].round(2)
    t.to_csv(OUT / "rates_by_edition.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 500)
    for ev in ["RG", "OG Paris", "OG Tokyo", "clay M1000", "AO", "WIM", "USO"]:
        x = t[t["event"].eq(ev)]
        if x.empty:
            continue
        piv = x.pivot_table(index=["tour", "draw", "season"], columns="version",
                            values=["first_in_pct", "second_won_pct", "df_per_second_pct"]).round(2)
        print(f"\n===== {ev}\n", piv.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
