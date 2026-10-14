"""R1-rederive (group SVX): swaps_scope.csv and the "SVX" entry of verdict.json, from my own tables.

swaps_scope.csv: one row per swap I confirm (source_file, source_row, match_id): the rows my svx_truth.py classes
"swapped" with a proven first server, that no other table of the candidate already changes (svx_checks.py).
verdict.json: adds a top-level "SVX" entry next to "addendum". Order of the output scripts:
  write_outputs.py, then addendum.py --compare, then this one.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_outputs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
S = "src/eda/rg_first_serve_recount/review_followup/R1-rederive/"


def main() -> None:
    x = pd.read_csv(HERE / "svx_checked.csv", low_memory=False)
    sw = x[x["cls"].eq("swapped") & ~x["excluded"].astype(bool)].copy()
    sw["source_row"] = sw["source_row"].astype(int)
    out = sw.rename(columns={"s0_match_id": "match_id"})[["source_file", "source_row", "match_id"]] \
        .sort_values(["source_file", "source_row"])
    out.to_csv(HERE / "swaps_scope.csv", index=False)
    cp = json.loads((HERE / "svx_compare.json").read_text(encoding="utf-8"))
    by = sw.groupby(["slam", "year"]).size()
    n = len(sw)
    comp = ~sw["score"].fillna("").str.contains("RET|DEF|W/O", regex=True)
    pr = x[x["proof"].eq("proven")]
    whole = pr[pr["mb_whole"].astype(str).eq("True")]
    whole_eq = int((whole["mb_w"].eq(whole["t_w"]) & whole["mb_l"].eq(whole["t_l"])).sum())
    pc = pr[~pr["score"].fillna("").str.contains("RET|DEF|W/O", regex=True) & pr["w_bpFaced"].notna()]
    entry = {
        "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
        "scope": f"All {n} proposed swaps (AO 2025 {by.get(('AO', 2025), 0)}; RG 2019 {by.get(('RG', 2019), 0)}, "
                 f"2020 {by.get(('RG', 2020), 0)}, 2021 {by.get(('RG', 2021), 0)}), in swaps_scope.csv, with the same "
                 f"source rows and match ids as proposed_swaps.csv ({cp['swaps']['both']} of {cp['swaps']['lead']}). "
                 "My own derivation found exactly these, plus RG 2023 QM119, which I leave out as the lead does: its "
                 "confirmed override already gives RG's service games, and an exchange applied after the override "
                 "would undo them.",
        "reasons": "First server proven (svx_truth.py, my decryption and recount): the file's games are in order with "
                   "no service game holding points of both servers; its first game is set 1 game 1 (set score 1-0 or "
                   "0-1 after it); every game it holds is served by the player the alternation names from that game's "
                   "server, a tiebreak by its first point, earlier sets counted from the row's score; each set it holds "
                   f"whole has the row's games by the games' winners. All {n} pass. "
                   "The truth comes from the row's score: servers alternate through the match, and a tiebreak takes "
                   "its turn uncounted (the final set's 10-point tiebreak at 6-6 included). A retirement counts its "
                   f"finished games only; {int((~comp).sum())} swaps are retirements. Where MatchBeats holds every "
                   "game, its own count of completed non-tiebreak games equals this truth on "
                   f"{whole_eq} of {len(whole)} proven rows. "
                   "A second derivation that does not use MatchBeats gives the same truth on all of them: the break "
                   "identity. A player's service games equal their non-tiebreak games won plus breaks conceded minus "
                   "breaks made, read off the row's own score and break points. It gives the truth on "
                   f"{int(sw['bp_eq_truth'].sum())} of {n} swaps and the row as recorded on "
                   f"{int(sw['bp_eq_row'].sum())}. In two rows (RG 2019 SD010 and SD020) the recorded counts are "
                   "impossible as they stand: breaks conceded exceed service games, B8. Exchanged, they are "
                   "consistent. So each row's two counts contradict its own score and break points as well as the "
                   "point record: corrupt beyond doubt. "
                   "Exchanging the two counts (exchange_svgms, F2y) gives exactly the truth. It leaves the total, and "
                   "so B5, unchanged. B8 passes afterwards on every row. No other table of the candidate touches "
                   "these rows (the decided corrections, round 1's split rows, the RGX exchanges, the RG overrides). "
                   "The fix is clear, unique and correct. "
                   f"{int(sw['row_is_winner_first'].sum())} rows read the score as if the winner had served first "
                   f"(the loser did); the other {int((~sw['row_is_winner_first'].astype(bool)).sum())} had the winner "
                   "serving first and read as if the loser had. "
                   "Links: RG rows by names, winner and games, with RG's player ids equal to MatchBeats'. AO 2025 "
                   "files by names within tour and round, every winner agreeing with MatchBeats' match winner; the "
                   "two names short of an exact match are transliterations (Sultanov, Bulgaru).",
        "checks": [
            S + "stage0_ao_rows.py: AO 2025 rows read once with stage0_build.normalise(stage0_build.load_raw()) (478 "
            "Sackmann rows, all in the live Stage 0).",
            S + "svx_parse.py: every MatchBeats file of RG 2019-2026 (3,740) and AO 2025 (469) decrypted with the "
            "adapter's blocks_of/decrypt; per game the server (a tiebreak by its first point), order, completion, "
            "set score and winner recounted myself; 7 files hold games out of order, 1 service game has points of "
            "both servers (those matches unproven).",
            S + "svx_truth.py: proof P1-P4, the truth from the row's score, the class; " +
            f"{int(pr.shape[0])} proven rows; MatchBeats' own count equals the truth wherever it holds every game "
            f"({whole_eq} of {len(whole)}).",
            S + "svx_checks.py: the break identity equals the truth on " + f"{int(pc['bp_eq_truth'].sum())} of "
            f"{len(pc)} proven completed rows (misses: 3 in RG 2021, none in AO 2025 or RG 2019-2020, the rest in "
            "2022-2026, where Sackmann's or TML's break points are not RG's), and on every swap; B8 after the "
            "exchange; exclusions.",
            S + "svx_compare.py: against the lead's matches.csv, the same class on 4,085 of 4,096 matches, the same "
            "truth and first server on all 4,079 both prove; the 11 class differences all have the row equal to the "
            "truth (no swap). Against proposed_swaps.csv: 323 of 323, same match ids."],
        "notes_for_the_lead": "1. Proof details. A file can lack the opening point of set 1 game 1 (AO 2025 MQ215 "
                              "first reads 0-30). The set-score field can be wrong after a tiebreak (RG 2021 SD103: "
                              "8-6 for 7-6). AO 2025 leaves 117 game winners as '0'. A proof resting on those fields "
                              "fails real swaps; resting on games and servers, my proven set and swap list equal "
                              "yours. "
                              "2. Five matches you call unproven pass my alternation check (RG 2023 QM073, QM094, "
                              "QD110; 2025 QM083, QM124), and six you prove fail my stricter opening or order checks. "
                              "All eleven have the row equal to the truth, so no swap depends on them. "
                              "3. The break identity is a second, MatchBeats-free proof. In this round's editions it "
                              "flags one more swap that MatchBeats cannot prove: AO 2025 WQ230 (7-6(5) 3-6 7-5, row "
                              "17/16, identity 16/17). It is not proposed; it could serve the addendum's editions too, "
                              "where Sackmann's break points are the event's own. "
                              "4. RG 2023 QM119 (left out): with Sackmann's own break points the identity backs his "
                              "10/11; with RG's (my confirmed override) it backs RG's 11/10. The override is the "
                              "consistent box, and the exchange must not be applied on top of it.",
    }
    vpath = HERE / "verdict.json"
    v = json.loads(vpath.read_text(encoding="utf-8"))
    v["SVX"] = entry
    vpath.write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
    print("swaps_scope.csv:", len(out), "rows | verdict.json: SVX entry written")


if __name__ == "__main__":
    main()
