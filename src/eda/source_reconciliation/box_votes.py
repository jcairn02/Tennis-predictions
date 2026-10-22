"""Three-way votes on each count: Stage 0 (what the model reads), the tour's own published box, and the tour's own
point record recounted. Where two agree and one differs, the odd one out is named; where Stage 0 is the odd one out,
both official records agree against it, and the row is a candidate for correction.

Trios (each recount on its complete rows only):
    wta     Stage 0 · wta_api_box (the WTA's box, B3) · wta_events_recount (its chair umpire's event log)
    atp     Stage 0 · atp_ks_handoff (Infosys key statistics, 2021-24) · atp_mb_handoff_recount (its MatchBeats points)
    atp_ch  Stage 0 · atp_ks_handoff · atp_ch_recount (Challenger MatchBeats, 2021-24)
    atp_mtd Stage 0 · atp_mantennisdata (the Stats Centre's rendered box) · atp_mb_handoff_recount
    atp_site2 Stage 0 · atp_mantennisdata · tp_atp_scraped (two scrapes of the ATP's own numbers, no point record:
            weaker evidence, used where nothing else is held, mostly 2015-2020)
    slam    Stage 0 · (no published Slam box on disk for these years) -> lead_slam_pbp_recount and tp_mcp_recount
            are handled in lead_slam_corrections.py instead

Writes data/studies/source_reconciliation/box/:
    votes.csv          trio x tour x band x count: rows, all equal, Stage 0 odd, box odd, recount odd, all differ
    votes_matches.csv  trio x tour x band: matches where Stage 0's whole box (18 counts) is the odd one out on at least
                       one count while box == recount on every count of the match (the correction candidates)
    votes_long.parquet the per-row classes (gitignored)
Run: ./python.sh src/eda/source_reconciliation/box_votes.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation.box_engine import band, LEVEL_GROUP  # noqa: E402

BOX = C.OUT / "box"
READERS = BOX / "readers"
TRIOS = {"wta": ("wta_api_box", "wta_events_recount"), "atp": ("atp_ks_handoff", "atp_mb_handoff_recount"),
         "atp_ch": ("atp_ks_handoff", "atp_ch_recount"), "atp_mtd": ("atp_mantennisdata", "atp_mb_handoff_recount"),
         # before 2021 no ATP point record is held for most matches: two separate scrapes of the ATP's own numbers
         # (ManTennisData from the Stats Centre pages, 2015-2026; the atptour.com scrape, to 2024) vote instead
         "atp_site2": ("atp_mantennisdata", "tp_atp_scraped")}


def reader(name: str, complete_only: bool = False) -> pd.DataFrame:
    f = pd.read_parquet(READERS / f"{name}.parquet", columns=["match_id", "player_id", "complete"] + C.COUNTS)
    f = f.drop_duplicates(["match_id", "player_id"])
    return f[f["complete"].astype(bool)] if complete_only else f


def main() -> int:
    m = pd.read_parquet(C.SNAP / "stage0_matches.parquet", columns=["match_id", "tour", "year", "map_level", "source"])
    m["band"] = band(m["year"].astype(int))
    m["level_group"] = m["map_level"].map(LEVEL_GROUP).fillna("other")
    s0 = reader("lead_stage0")
    rows, longs, cand = [], [], []
    for trio, (bx, rc) in TRIOS.items():
        if not (READERS / f"{bx}.parquet").exists() or not (READERS / f"{rc}.parquet").exists():
            continue
        j = s0.merge(reader(bx), on=["match_id", "player_id"], suffixes=("", "_b")).merge(
            reader(rc, True), on=["match_id", "player_id"], suffixes=("", "_r"))
        j = j.merge(m, on="match_id", how="left")
        for f in C.COUNTS:
            a, b, r = j[f], j[f"{f}_b"], j[f"{f}_r"]
            ok = a.notna() & b.notna() & r.notna()
            cls = np.select([~ok, (a == b) & (b == r), (b == r) & (a != b), (a == r) & (a != b), (a == b) & (a != r)],
                            ["missing", "all_equal", "stage0_odd", "box_odd", "recount_odd"], "all_differ")
            j[f"cls_{f}"] = cls
            t = pd.DataFrame({"tour": j["tour"], "band": j["band"], "level_group": j["level_group"], "cls": cls})
            t = t[t["cls"] != "missing"]
            g = t.groupby(["tour", "level_group", "band", "cls"]).size().unstack(fill_value=0).reset_index()
            g.insert(0, "count", f)
            g.insert(0, "trio", trio)
            rows.append(g)
        cc = [f"cls_{f}" for f in C.COUNTS]
        cl = j[cc]
        any_s0_odd = cl.eq("stage0_odd").any(axis=1)
        # box and recount agree on every count both hold (they may lack a count)
        box_eq_rc = pd.concat([(j[f"{f}_b"] == j[f"{f}_r"]) | j[f"{f}_b"].isna() | j[f"{f}_r"].isna()
                               for f in C.COUNTS], axis=1).all(axis=1)
        j["s0_odd_row"] = any_s0_odd & box_eq_rc
        per_match = j.groupby("match_id").agg(s0_odd=("s0_odd_row", "any"), tour=("tour", "first"),
                                              band=("band", "first"), level_group=("level_group", "first"),
                                              source=("source", "first")).reset_index()
        g = per_match.groupby(["tour", "level_group", "band", "source"]).agg(
            matches=("match_id", "size"), stage0_odd_matches=("s0_odd", "sum")).reset_index()
        g.insert(0, "trio", trio)
        cand.append(g)
        keep = ["match_id", "player_id", "tour", "year", "level_group", "source"] + C.COUNTS + \
               [f"{f}_b" for f in C.COUNTS] + [f"{f}_r" for f in C.COUNTS] + cc + ["s0_odd_row"]
        longs.append(j[keep].assign(trio=trio))
    votes = pd.concat(rows, ignore_index=True).fillna(0)
    for c in ("all_equal", "stage0_odd", "box_odd", "recount_odd", "all_differ"):
        if c not in votes:
            votes[c] = 0
    votes["rows"] = votes[["all_equal", "stage0_odd", "box_odd", "recount_odd", "all_differ"]].sum(axis=1)
    votes.to_csv(BOX / "votes.csv", index=False)
    pd.concat(cand, ignore_index=True).to_csv(BOX / "votes_matches.csv", index=False)
    pd.concat(longs, ignore_index=True).to_parquet(BOX / "votes_long.parquet", index=False)
    s = votes.groupby(["trio", "count"])[["rows", "all_equal", "stage0_odd", "box_odd", "recount_odd", "all_differ"]].sum()
    for c in ("all_equal", "stage0_odd", "box_odd", "recount_odd", "all_differ"):
        s[c] = (s[c] / s["rows"]).round(4)
    pd.set_option("display.width", 220)
    print(s.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
