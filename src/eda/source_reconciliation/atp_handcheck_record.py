"""Records the hand checks (brief rule 8) in each atp_ reader's JSON: the keys atp_handcheck.py printed (the same
seeded sample), what was compared, and the verdict read off its output by the session (16 Oct 2026).

Run after atp_handcheck.py: ./python.sh src/eda/source_reconciliation/atp_handcheck_record.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402
from src.eda.source_reconciliation import atp_handcheck as H  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

VERDICTS = {
    "atp_ks_handoff": ("raw JSON line (keystats.setStats.set0, keystats.players, the record's player1/2)",
                       "5 of 5: every count equals the raw set0 value (Aces, Double Faults, 1st Serve n/d, 1st and 2nd "
                       "Serve Points Won numerators, Break Points Saved n/d, Service Games Played, Service Points Won) "
                       "for both players; the keystats player list is the record's; each ATP code sits on the Stage 0 "
                       "player of the same name"),
    "atp_mb_handoff_recount": ("raw JSON line (rally_analysis.rallyData), tallied directly: aces by the side that won "
                               "them, double faults by the side that lost them, points won per side",
                               "5 of 5 complete recounts: the reader's aces, double faults and points won (sv_won1 + "
                               "svpt2 - sv_won2) equal the raw tallies; playerDetails codes are the record's; Stage 0 "
                               "names match; all nine counts equal Stage 0's in these five"),
    "atp_ks_backfill": ("staged keystats.parquet set0 rows and matches.parquet (p1/p2 codes and names)",
                        "5 of 5: counts equal the staged values; p1/p2 sit on the Stage 0 players of the same names"),
    "atp_backfill_recount": ("staged points.parquet tallied directly by the server field: rows, serve == 1, won on "
                             "serve 1 / 2, result A, result P or DF",
                             "5 of 5 complete recounts: svpt, first_in, first_won, second_won, ace, df equal the "
                             "tallies; orientation by codes and names matches Stage 0"),
    "atp_ch_recount": ("staged points.parquet tallied directly by the server field (4 MatchBeats matches) and one "
                       "rally-only match (no MatchBeats to tally)",
                       "4 of 4 MatchBeats recounts equal the tallies; the rally-only recount (server derived) equals "
                       "Stage 0 on all nine counts; orientation by codes (the staged rally-only rows carry no names) "
                       "matches Stage 0"),
    "atp_ks_sirgenkii": ("staged atp_key_stats.parquet set_n 0 rows (one valued, one -999 per match)",
                         "5 of 5: the present player's aces, double faults, service games and break points faced "
                         "equal the staged counts and bp_saved = share x faced; where the reconstruction is unique "
                         "(3 of the 5 matches) its counts reproduce the four shares to five decimals and equal Stage "
                         "0; in 2 matches it is ambiguous and left NaN, as designed; the absent player's service games "
                         "are the present player's return games"),
    "atp_sirgenkii_recount": ("staged atp_rally_analysis.parquet tallied by subject, ending and outcome",
                              "5 of 5 complete recounts: aces (ACE, W) and double faults (DOUBLE FAULT, L) per subject "
                              "equal the reader's per player; codes sit on the Stage 0 players of the same names"),
    "atp_ks_daily": ("the collector's raw file, decrypted in memory (set0 and the players list)",
                     "5 of 5: counts equal the decrypted set0 values; the players list's codes and names sit on Stage "
                     "0's players; one file read matchCompleted False (MS024) and its counts still equal Stage 0's"),
    "atp_tdi_stats": ("staged statistics.parquet (period match) and matches.parquet (team codes, names, scores)",
                      "5 of 5: aces, double faults, service games, break points faced and saved, service points won "
                      "equal the staged values; svpt = service points won + the opponent's return points won; team "
                      "A/B codes and names sit on Stage 0's players"),
    "atp_tdi_recount": ("staged points.parquet tallied directly by team_serving: points, label first serves in, won on "
                        "them, aces, double faults, points won",
                        "5 of 5 complete recounts equal the tallies; orientation by codes matches Stage 0"),
    "atp_mantennisdata": ("staged atp_matches_<year>.parquet row (win_ / los_ columns, winner / loser codes and names)",
                          "5 of 5 (seasons 2018 on): counts equal the staged values; winner and loser codes sit on the "
                          "Stage 0 players of the same names"),
}
WHERE = {"atp_mb_handoff_recount": lambda r: r["complete"], "atp_backfill_recount": lambda r: r["complete"],
         "atp_sirgenkii_recount": lambda r: r["complete"], "atp_tdi_recount": lambda r: r["complete"],
         "atp_mantennisdata": lambda r: r["x_season"] >= 2018}


def keys_of(reader: str) -> list[str]:
    if reader == "atp_ch_recount":
        a = H.sample(reader, where=lambda r: r["complete"] & r["x_route"].eq("match-beats"), n=4)
        b = H.sample(reader, where=lambda r: r["x_route"].eq("rally-analysis"), n=1)
        return sorted(set(a["source_key"]) | set(b["source_key"]))
    return sorted(set(H.sample(reader, where=WHERE.get(reader))["source_key"]))


def main() -> int:
    for reader, (how, verdict) in VERDICTS.items():
        path = A.READERS / f"{reader}.json"
        info = json.loads(path.read_text(encoding="utf-8"))
        keys = keys_of(reader)
        r = pd.read_parquet(A.READERS / f"{reader}.parquet", columns=["source_key", "match_id"])
        mids = r[r["source_key"].isin(keys)].drop_duplicates("source_key").set_index("source_key")["match_id"]
        info["hand_checks"] = {"by": "atp_handcheck.py (seed %d), read by the session on 16 Oct 2026" % H.SEED,
                               "compared_with": how, "verdict": verdict,
                               "keys": [{"source_key": k, "match_id": mids.get(k)} for k in keys]}
        C.write_json(path, info)
        print(reader, len(keys))
    return 0


if __name__ == "__main__":
    sys.exit(main())
