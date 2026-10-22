"""The report's box-score tables, written from the engine's outputs so that every number in the README traces to a
file: data/studies/source_reconciliation/box/report_tables.md.

    T1  each source against each tour's own point record (complete recounts only): exact agreement per count
    T2  the three-way votes: how often Stage 0, the tour's box and its point record is the odd one out, per count
    T3  the candidate corrections: classes, matches, seasons, and how far they reach the model
Run after box_engine.py, box_votes.py, lead_slam_corrections.py and lead_official_corrections.py:
    ./python.sh src/eda/source_reconciliation/report_tables.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation.exposure import exposure  # noqa: E402

BOX = C.OUT / "box"
COUNTS = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_faced", "bp_saved"]
LABEL = {"ace": "aces", "df": "double faults", "svpt": "serve points", "first_in": "first serves in",
         "first_won": "1st-serve pts won", "second_won": "2nd-serve pts won", "sv_gms": "service games",
         "bp_faced": "break pts faced", "bp_saved": "break pts saved"}
READER_LABEL = {
    "lead_stage0": "**Stage 0 (what the model reads)**", "lead_sackmann_raw": "Sackmann's raw rows",
    "lead_tml_raw": "Tennis My Life's raw rows", "wta_api_box": "the WTA's published box",
    "atp_ks_handoff": "the ATP's key statistics (Infosys)", "atp_mantennisdata": "ManTennisData (ATP pages)",
    "tp_atp_scraped": "atptour.com scrape", "tp_sofascore_box": "SofaScore's box",
    "tp_sofascore_recount": "SofaScore's points, recounted", "tp_mcp_recount": "Match Charting Project",
    "tp_tennislive_stats": "TennisLive's statistics", "tp_flashscore_stats": "Flashscore's statistics",
    "atp_tdi_stats": "TDI's statistics", "atp_ks_backfill": "the ATP's key statistics (backfill)",
    "atp_ks_sirgenkii": "the ATP's key statistics (SirGenkii)"}
REF_LABEL = {"wta_events_recount": "WTA umpire log, 2019–26", "atp_mb_handoff_recount": "ATP MatchBeats, 2021–24",
             "atp_ch_recount": "ATP Challenger MatchBeats, 2021–24", "lead_slam_pbp_recount": "Slam point files, 2011–24",
             "atp_tdi_recount": "TDI points, 2026"}


def pct(x) -> str:
    return "" if pd.isna(x) else f"{100 * x:.2f}"


def table_t1(acc: pd.DataFrame) -> list[str]:
    out = ["## T1. Each source against each tour's own point record", "",
           "Exact agreement, % of player rows, on the referee's complete recounts. Higher is better.", ""]
    for ref, name in REF_LABEL.items():
        t = acc[acc["referee"] == ref]
        if t.empty:
            continue
        g = t.groupby(["reader", "field"])[["n", "equal"]].sum().reset_index()
        g["eq"] = g["equal"] / g["n"]
        piv = g.pivot_table(index="reader", columns="field", values="eq")
        n = g.groupby("reader")["n"].max()
        piv = piv.loc[[r for r in READER_LABEL if r in piv.index and n.get(r, 0) >= 200]]
        if piv.empty:
            continue
        out += [f"**Referee: {name}**", "",
                "| Source | rows | " + " | ".join(LABEL[c] for c in COUNTS) + " |",
                "|---|---:|" + "---:|" * len(COUNTS)]
        for r, row in piv.iterrows():
            out.append(f"| {READER_LABEL[r]} | {int(n[r]):,} | " +
                       " | ".join(pct(row.get(c)) for c in COUNTS) + " |")
        out.append("")
    return out


def table_t2(votes: pd.DataFrame) -> list[str]:
    names = {"wta": "WTA: Stage 0 · the WTA's box · its umpire log",
             "atp": "ATP 2021–24: Stage 0 · key statistics · MatchBeats",
             "atp_ch": "ATP Challengers 2021–24: Stage 0 · key statistics · MatchBeats",
             "atp_site2": "ATP 2015–24 (no point record): Stage 0 · ManTennisData · atptour.com scrape"}
    out = ["## T2. Three-way votes: which record is the odd one out", "",
           "% of player rows where exactly one of the three differs (the other two agree). Lower is better for Stage 0.", ""]
    for trio, name in names.items():
        t = votes[votes["trio"] == trio]
        if trio == "atp_site2":
            t = t[t["level_group"] != "slam"]
        if t.empty:
            continue
        s = t.groupby("count")[["rows", "stage0_odd", "box_odd", "recount_odd", "all_differ"]].sum()
        out += [f"**{name}**", "", "| Count | rows | Stage 0 odd | box odd | point record odd |", "|---|---:|---:|---:|---:|"]
        for c in COUNTS:
            if c in s.index:
                r = s.loc[c]
                out.append(f"| {LABEL[c]} | {int(r['rows']):,} | {pct(r['stage0_odd'] / r['rows'])} | "
                           f"{pct(r['box_odd'] / r['rows'])} | {pct(r['recount_odd'] / r['rows'])} |")
        out.append("")
    return out


def table_t3() -> list[str]:
    out = ["## T3. Candidate corrections", "", "| Class | Matches | Where | Reach: model matches within 28 days (train / test) |",
           "|---|---:|---|---|"]
    s1 = pd.read_csv(BOX / "slam_svgms_candidates.csv")
    o1 = pd.read_csv(BOX / "official_candidates.csv")
    o1t = pd.read_csv(BOX / "official_candidates_tml.csv")
    for label, f, where in (("S1 Slam service games exchanged", s1,
                             ", ".join(f"{r.x_tournament} {r.x_year}" for r in
                                       s1.groupby(["x_tournament", "x_year"]).size().reset_index().itertuples())),
                            ("O1 whole box from the tour's own records", o1,
                             ", ".join(f"{t} {y}: {n}" for (t, y), n in o1.groupby(["x_tour", "x_year"]).size().items())),
                            ("O1 rows that are TML's (after the splice)", o1t, "WTA 2026")):
        ex = exposure(set(f["match_id"]))
        e28 = ex["frame_matches_within_28d"]
        out.append(f"| {label} | {len(f)} | {where} | {e28['train_to_2024']} / {e28['test_2025_26']} |")
    out.append("")
    return out


def main() -> int:
    acc = pd.read_csv(BOX / "engine_accuracy.csv")
    votes = pd.read_csv(BOX / "votes.csv")
    lines = ["# Box-score tables (generated by src/eda/source_reconciliation/report_tables.py)", ""]
    lines += table_t1(acc) + table_t2(votes) + table_t3()
    (BOX / "report_tables.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
