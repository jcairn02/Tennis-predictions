"""The closing prices the return is computed at, for every test match of the 58-input model frame, in A/B orientation.

    pinnacle   tennis-data.co.uk's PSW/PSL as Stage 1 linked them to Stage 0 (stage1_odds.parquet: ps_a, ps_b,
               ps_coherent: overround 1.00-1.20). The provider says its odds "generally represent the most recent before
               play starts"; they carry no time. Its Pinnacle columns stop in mid-January 2026
    betonline  the last line OddsTrader recorded (src/ingest/oddstrader.py), linked and cleaned exactly as the
               BetOnline-lines study does (src/eda/betonline_lines/sharpness.py: load_tennis_data, betonline_markets,
               the sharp benchmark's link, attach_betonline): a pair outside overround 1.00-1.20, or a close the adapter
               flags uncertain (stamped over 30 minutes after the listed start, or not two-sided), gives no price.
               Joined to Stage 1's tennis-data row by tour, date, winner and loser (the two loaders number rows
               differently); 2024 to 2026
    status     Stage 0's: completed or retired (walkovers never reach the model frame)

Stage 1 is read as it stood before the rebuild of 7 Oct 2026 (data_continuity's copy of the replaced files), the
snapshot the model frame was built on: the rebuild changed the ids of 40 of its June 2026 WTA test matches.

A is tennis-data's winner unless Stage 1 linked the row with winner and loser exchanged; that orientation is checked
against the market average's odds, which must agree with Stage 1's for A on every row.

Prices stay in the gitignored book_odds.parquet (*.parquet): this repository is public and OddsTrader's lines are not
republished. book_counts.json holds counts only.
Run: ./python.sh src/eda/tabpfn_thinking58/books.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.betonline_lines import sharpness as SH  # noqa: E402
from src.eda.sharp_benchmark import build as BLD  # noqa: E402
from src.eda.tabpfn_thinking58 import common as C  # noqa: E402

STAGE1 = (ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" /
          "studies" / "predictability_diagnostic" / "stage1_odds.parquet")         # the model frame's snapshot
BOL_SEASONS = (2024, 2025, 2026)
KEY = ["tour", "date", "winner", "loser"]


def betonline_rows() -> pd.DataFrame:
    """Every tennis-data row of 2024-2026 with BetOnline's closing decimal odds for its winner and loser."""
    td = SH.load_tennis_data(BOL_SEASONS)
    bo, frame = SH.betonline_markets()
    m = SH.attach_betonline(td, bo, BLD.link(td, frame))
    m = m[KEY + ["AvgW", "AvgL", "BOLCW", "BOLCL", "ok_bol", "mw_close_after_listed_min"]].copy()
    m["winner"], m["loser"] = m["winner"].astype(str), m["loser"].astype(str)
    if m.duplicated(KEY).any():
        raise RuntimeError("tennis-data rows are not unique by tour, date, winner and loser")
    return m


def main() -> int:
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "tour", "season", "a_won", "tabpfn_split"])
    f = f[f["tabpfn_split"] == "test"].drop(columns="tabpfn_split")
    f["match_id"] = f["match_id"].astype(str)
    s1 = pd.read_parquet(STAGE1, columns=["match_id", "status", "link", "td_date", "td_winner", "td_loser", "avg_a",
                                          "avg_b", "ps_a", "ps_b", "ps_coherent"])
    s1["match_id"] = s1["match_id"].astype(str)
    o = f.merge(s1, on="match_id", how="left", validate="one_to_one")
    if o["td_winner"].isna().any():
        raise RuntimeError("a test match has no tennis-data row in Stage 1")
    # A is tennis-data's winner unless the row was linked with winner and loser exchanged (Stage 1's rule)
    a_is_w = o["a_won"].astype(bool).to_numpy() ^ o["link"].eq("winner_swapped").to_numpy()
    o["ok_ps"] = o["ps_coherent"].fillna(False).astype(bool)

    b = betonline_rows()
    o = o.merge(b.rename(columns={"date": "td_date", "winner": "td_winner", "loser": "td_loser"}),
                on=["tour", "td_date", "td_winner", "td_loser"], how="left", validate="one_to_one")
    in_bol = o["season"].isin(BOL_SEASONS).to_numpy()
    # a row the current tennis-data file no longer holds as Stage 1 read it (seen: 4 rows Stage 1 linked with winner
    # and loser exchanged) gets no BetOnline price; counted below
    unjoined = in_bol & o["AvgW"].isna().to_numpy()
    if unjoined.sum() > 10:
        raise RuntimeError(f"{int(unjoined.sum())} 2024-2026 test matches did not join their tennis-data row")
    avg_w = np.where(a_is_w, o["AvgW"], o["AvgL"])                       # the market average's odds for A
    k = in_bol & o["avg_a"].notna().to_numpy() & np.isfinite(avg_w)
    if not np.allclose(o["avg_a"].to_numpy()[k], avg_w[k]):
        raise RuntimeError("A's market-average odds disagree between the two loaders: orientation is wrong")
    o["bol_a"] = np.where(a_is_w, o["BOLCW"], o["BOLCL"])
    o["bol_b"] = np.where(a_is_w, o["BOLCL"], o["BOLCW"])
    o["ok_bol"] = o["ok_bol"].fillna(False).astype(bool) & in_bol & ~unjoined
    o["bol_close_min"] = o["mw_close_after_listed_min"]          # BetOnline's last line, minutes after the listed start

    keep = ["match_id", "tour", "season", "status", "ps_a", "ps_b", "ok_ps", "bol_a", "bol_b", "ok_bol", "bol_close_min"]
    o[keep].to_parquet(C.OUT / "book_odds.parquet", index=False)
    counts = {
        "test_matches": int(len(o)),
        "orientation_checked_rows": int(k.sum()),
        "status": {str(k_): int(v) for k_, v in o["status"].value_counts().items()},
        "pinnacle_close": {str(s): int(g["ok_ps"].sum()) for s, g in o.groupby("season")},
        "betonline_close": {str(s): int(g["ok_bol"].sum()) for s, g in o.groupby("season")},
        "betonline_linked_rows_2024_2026": int(o.loc[in_bol, "BOLCW"].notna().sum()),
        "unjoined_tennis_data_rows_2024_2026": int(unjoined.sum()),
        "both_books": int((o["ok_ps"] & o["ok_bol"]).sum()),
        "betonline_close_stamped_over_60_min_before_listed_start": int((o["ok_bol"] & (o["bol_close_min"] < -60)).sum()),
    }
    C.write_json(C.OUT / "book_counts.json", counts)
    C.log(f"book_odds.parquet: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
