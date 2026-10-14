"""R1-rederive (round 2): write overrides_scope.csv, exchanges_scope.csv and verdict.json from my own tables.

  overrides_scope.csv   one row per match I confirm (W22 and W26), with the values I derived (my_overrides.csv): RG's
                        statistics for the eight counts, service games as Sackmann counts them (tiebreak games and the
                        unfinished game of a retirement not counted) from RG's score and MatchBeats' first server, else
                        MatchBeats, else the row's own count. feed_key in the proposal's form (rolandgarros:<year>/<code>).
  exchanges_scope.csv   the four RG 2021 exchanges (rgx.csv)
  verdict.json          the votes, from the evidence files of this folder (evidence.json, compare.json, dry_run.json)
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/write_outputs.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
S = "src/eda/rg_first_serve_recount/review_followup/R1-rederive/"
COLS = ["feed_key", "stage0_match_id"] + [f"{s}_{c}" for s in "wl" for c in
                                         ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")]


def main() -> None:
    ov = pd.read_csv(HERE / "my_overrides.csv", dtype=str, keep_default_na=False)
    ov = ov[ov["group"].isin(["W22", "W26"])].copy()
    ov["feed_key"] = "rolandgarros:" + ov["feed_key"].str.replace(r"^RG(\d{4})\|", r"\1/", regex=True)
    ov[COLS].to_csv(HERE / "overrides_scope.csv", index=False)
    rgx = pd.read_csv(HERE / "rgx.csv", dtype=str, keep_default_na=False)
    m = pd.read_csv(HERE / "matches.csv", dtype=str, keep_default_na=False)
    rgx = rgx.merge(m[["source_file", "source_row", "s0_match_id"]], on=["source_file", "source_row"], how="left")
    rgx.rename(columns={"s0_match_id": "match_id"})[["source_file", "source_row", "match_id"]].to_csv(
        HERE / "exchanges_scope.csv", index=False)
    ev = json.loads((HERE / "evidence.json").read_text(encoding="utf-8"))
    cp = json.loads((HERE / "compare.json").read_text(encoding="utf-8"))
    dr = json.loads((HERE / "dry_run.json").read_text(encoding="utf-8"))
    n22, n26 = int(ov["group"].eq("W22").sum()), int(ov["group"].eq("W26").sum())
    diff = pd.read_csv(HERE / "compare_overrides.csv")
    dkeys = set(diff["feed_key"])
    d22 = sorted(k for k in dkeys if not k.startswith("rolandgarros:2026/"))
    d26 = sorted(k for k in dkeys if k.startswith("rolandgarros:2026/"))

    common_checks = [
        S + "stage0_rows.py: Stage 0's raw rows read once with stage0_build.normalise(stage0_build.load_raw()); RG "
        "2019-2026 kept (Sackmann's <year>-520 rows, TML's 2026 men's qualifying), with apply_box_overrides' lookup key: "
        "every key names exactly one raw row of its source.",
        S + "parse_feeds.py: all 3,768 rolandgarros.com documents of 2019-2026 parsed myself (3,748 with statistics); "
        "every team row passes the record's own checks (1st/2nd-serve denominators, receiving points = the opponent's "
        "serve points, total points = serve + return points won, counts present and in order). Every RG MatchBeats file "
        "(2019-2024 match-beats, 2025 match-centre, 2026 match-beats-api; 3,740 with points, 3 empty) decrypted with the "
        "adapter's blocks_of/decrypt and recounted myself, with service games per server (tiebreak games and unfinished "
        "games apart); key statistics 2025-2026 parsed.",
        S + "link_rows.py: each of the 3,656 Stage 0 raw rows of RG 2019-2026 paired with an RG document, and every "
        "document of a draw Stage 0 holds paired (RG 2026's women's qualifying has no Stage 0 rows); names within year, "
        "tour and round, optimal assignment; every link agrees on the winner and, but for one 2019 control match, on "
        "the games of every set; every name pair below an exact match reviewed (married names, transliterations, "
        "nicknames, Emilio/'Eduardo' Nava; 'T. Farquhar' = Thomas Faurel). Service games derived from RG's score and "
        "MatchBeats' first server agree with MatchBeats' server on every game it holds in every match with a file but "
        "one (2021 QD029).",
        S + "classify.py: classes computed my way in the brief's order; 2022-2026: 1,509 proposed, 730 equal, 12 "
        "walkovers, 13 statistics_short, 13 referee_contradicts, 1 identity slip (the lead's no_link), 0 record or "
        "Stage 0 check failures; identical to the lead's class on all 4,556 player rows (compare.py).",
        S + "compare.py: same 1,509 matches, same Stage 0 match ids, same lookup keys (source, tour, tid, round, winner "
        "and loser keys); of 27,162 values 27,149 equal; the 13 that differ are service games in 12 matches (see the "
        "group's scope and other_findings).",
        S + "dry_run.py: my 1,509 override rows applied with stage0_build.apply_box_overrides and the 4 exchanges with "
        "corrections.apply_row_corrections to the raw RG rows: every row found once and reading my values, 0 rows "
        "changed outside the table, no row both overridden and exchanged; Stage 0's own box_scores: all 1,509 rows "
        "'full' (service games kept), my check re-implementation agrees with it; " +
        f"{dr['matches_gaining_a_box']} matches gain a box ({dr['matches_gaining_a_box_by_year']}), none loses one.",
    ]
    verdict = {
        "reviewer": "R1-rederive", "lens": "rederive",
        "groups": {
            "RGX": {
                "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
                "scope": "All 4 rows of data/raw/public_dump/sackmann_archive/wta/wta_matches_2021.csv: 1097 (Muchova d. "
                         "Petkovic, R128), 1116 (Peterson d. Rogers, R128), 1194 (Zidansek d. Siniakova, R32), 1197 "
                         "(Badosa d. Bogdan, R32); action exchange_box (all nine counts), exactly as proposed_exchanges.csv.",
                "reasons": "Corrupt beyond doubt: for each match RG's statistics equal Sackmann's two boxes exchanged on all "
                           "eight shared counts for both players (16 of 16), and not as recorded; RG's MatchBeats (my "
                           "recount, a second RG record) agrees with RG's statistics; independent records agree too: the "
                           "hand charts equal RG's serve points, first serves in, aces and double faults for both players "
                           "of Peterson-Rogers and Zidansek-Siniakova, Court Vision those of Badosa-Bogdan (Bogdan 126 v "
                           "127 serve points, the rest equal). The winner is right: RG's winner flag, RG's set scores read "
                           "from the winner's side equal the row's score (1-6 6-3 6-4, 6-7 7-6 6-2, 0-6 7-6 6-2, 2-6 7-6 "
                           "6-4), and the row's winner id plays the next round in both Sackmann's rows and RG's documents "
                           "while the loser's does not, so names and ids go together and are not swapped: only the boxes "
                           "are. The fix is exact: service "
                           "games are equal for both players in every match in the row, in MatchBeats and in my score "
                           "derivation (13-13, 16-16, 13-13, 15-15), so exchanging all nine counts gives RG's box; applied "
                           "with apply_row_corrections, all four rows read RG's values and pass Stage 0's checks. They are "
                           "the only differences in 2019-2021 (2,732 of 2,740 linked player rows equal on all eight counts; "
                           "the other 8 are these).",
                "checks": [S + "evidence.py -> rgx.csv: every count of the four rows, RG's and MatchBeats', next-round "
                           "presence by id; " + S + "dry_run.py: the four exchanges applied, reading RG's nine counts; " +
                           S + "compare.py: proposed_exchanges.csv names the same four source rows, and exchange_rows.csv "
                           "equals my values on 8 of 8 player rows."] + common_checks[1:3],
            },
            "W22": {
                "vote": "narrow", "rule_applies": True, "bar": "source rule",
                "scope": f"All {n22} proposed matches of RG 2022-2025 (Sackmann's rows), every class exclusion as proposed "
                         "(12 walkovers in 2022-2026, 13 statistics_short, 13 referee_contradicts, the identity slip), with "
                         f"my values in overrides_scope.csv: {n22 - len(d22)} equal the proposal on all 18 values; on "
                         f"{len(d22)} retirements my service games are one lower for one player, because I count complete "
                         "games only, as Sackmann's own rows do (" + ", ".join(d22) + "). Test per match: RG's document "
                         "linked by both names, winner and games; RG's own checks pass; MatchBeats holds no more serve "
                         "points than RG's statistics; neither MatchBeats nor the key statistics, holding every point, "
                         "give another split, aces or double faults; no referee holding the player's points reads the "
                         "row's value on a changing count; the official box passes Stage 0's B0-B9 under the row's score.",
                "reasons": "The 6 Oct rule's conditions hold and, for these rows, its reason holds more strongly than at "
                           "Wimbledon or the US Open: RG's statistics are Sackmann's own Roland Garros record before the "
                           "fault (2019-2021: 2,732 of 2,740 player rows equal on all eight counts, the 8 being the RGX "
                           "exchanges, against 98.3-100% for the US Open feed). From 2022 Sackmann's rows come from "
                           "another record (the one SofaScore shows, per the report and round 1), with a measured fault: "
                           "second serves booked as first, aces and double faults missed (where they change, the row is "
                           "lower in 81 of 83 and 182 of 207 player rows), partial or inflated boxes (serve points from 72 "
                           "short, Kovalik 19 v 91, to 35 over, Nishikori 214 v 179, where MatchBeats holds every point "
                           "and equals RG, as Court Vision does for Rublev-Daniel). Taking RG's whole box makes RG "
                           "2019-2025 one measurement, the one the training data used before 2022, with the nine counts "
                           "of a match from one source. I therefore apply the source rule, not the 8 Oct bar, to Sackmann's "
                           "own 2022-2025 rows: the 8 Oct bar asks whether a row of a trusted source is corrupt; here the "
                           "question is which record is the event's box score, and Sackmann's own history answers it. "
                           "The evidence on the small differences: where an independent record holds the player's points "
                           "and a count changes, Court Vision 2022 reads RG's value 237 times and the row's once (first "
                           "serves in, the excluded matches included), the hand charts 136 and 11; the charts' 11 are "
                           "their own noise (on sides where RG and the row agree they read the agreed value +1 on 11.9%; "
                           "on disputed '+1' sides they read the row's 8 of 54). MatchBeats, holding every point, equals "
                           "RG's break points on all 601 changing rows. The residual risk is on '-1' sides (the row one "
                           "first serve in below RG): Court Vision reads the row's value once in 20 and the charts twice "
                           "in 21, above their baselines (0.6%, 1.9%), so RG may be wrong by one on some 5-10% of those "
                           "sides. I accept it: such an error moves one first serve of a side, unbiased, and is the same "
                           "kind of error the 2019-2021 training rows carry; the rows it would keep come from the record "
                           "that is wrong on most of them. Service games: MatchBeats' count (tiebreaks not counted) is "
                           "right where it changes the row (42 rows, each fitting the score exactly, each equal to my "
                           "independent derivation from RG's score and MatchBeats' first server); but the proposal also "
                           "counts the unfinished game of a retirement, which Sackmann's rows never count (62 of 62 "
                           "retirement rows of 2022-2025), so on 8 matches it would move a correct count by +1. The "
                           "fallback to the row's count is acceptable: in the 12 matches where MatchBeats lacks points my "
                           "derivation gives the row's count on all 24 rows, and in the 8 with no MatchBeats file the "
                           "row's count fits the score exactly.",
                "checks": common_checks + [
                    S + "evidence.py: E1 (2,732 of 2,740; service games equal in 98.1% of 2022-2025 rows with both counts, "
                    "80.9% in 2019-2021, counting complete games; 97.8%/80.6% when the unfinished game counts), E2 (my "
                    "table equals the brief's on every cell: rows changing 357/83/207/1,833/1,390/1,378; Court Vision 2022 "
                    "15/0/15, 10/0/10, 21/0/21, 232/0/236, 182/0/185, 178/0/181; hand charts as the brief, but 6 rows "
                    "reading neither serve-point value), E7 (1,177 proposed; 875 of round 1's 887 RG rows inside proposed "
                    "matches with the same split; pooled first serves in after the overrides equal RG's own to 0.03 "
                    "points except 2024-2025 men's and 2024 women's qualifying, where statistics_short matches stay out).",
                    S + "break_points.py: break points faced and saved recounted from MatchBeats on every changing row it "
                    "holds in full: equal to RG's on all 601, to the row's on none.",
                    S + "referee_noise.py -> referee_noise.csv: the referees' own noise on sides where RG and the row "
                    "agree, and their reads on disputed W22 sides by the size of the difference (other_findings 3)."],
            },
            "W26": {
                "vote": "narrow", "rule_applies": True, "bar": "source rule",
                "scope": f"All {n26} proposed matches of RG 2026 (124 men's main draw, 127 women's main draw from "
                         "Sackmann's blank rows; 81 men's qualifying from TML's rows), with my values in "
                         f"overrides_scope.csv: {n26 - len(d26)} equal the proposal on all 18 values; on {len(d26)} my "
                         "service games differ (" + ", ".join(d26) + "): three retirements where I count complete games "
                         "only, and Maestrelli d. Noguchi (QM080), whose service games the proposal leaves blank and I "
                         "give as 14 and 15. Same tests as W22.",
                "reasons": "This is the 6 Oct rule as applied to Wimbledon and the US Open 2026: rows after Sackmann's data "
                           "ends, at a Slam whose official feed is held (RG's statistics, MatchBeats and key statistics of "
                           "2026, all parsed here) and matched Sackmann's history (2019-2021, every count). Main draws: "
                           "Sackmann's 254 rows are blank, so nothing is corrupt; RG's box is RG's record of each match "
                           "(names, winner and games agree on all 254 links), passes its own checks and Stage 0's, and "
                           "MatchBeats, wherever it holds every point, gives the same split, aces, double faults and break "
                           "points. Men's qualifying: TML's rows link by names, winner and games; TML is near RG but not "
                           "equal (serve points equal in 69.4% of rows, 88.3% within one; first serves in 60.4%, 77.9%), "
                           "writes 0 service games in 194 of 224 rows (Stage 0 holds service games for 26 rows and no box "
                           "for 15 matches), and its pooled first serves in are level with RG's (63.24% v 63.11%): not the "
                           "first-serve fault, so the rule replaces a weaker record, not a corrupt one, as at the US Open. "
                           "Maestrelli d. Noguchi: RG and TML give one point to different servers (RG: Noguchi 114/88, "
                           "Maestrelli 91/48; TML 113/87, 92/49); MatchBeats holds all of Noguchi's serve points and agrees "
                           "with RG; its service games follow from RG's score and MatchBeats' first server, checked on 29 "
                           "games (14 and 15; the proposal: blank).",
                "checks": common_checks + [
                    S + "evidence.py: E4 (127 + 127 main-draw matches from Sackmann's rows, none with a box; 112 TML "
                    "qualifying matches; TML 0 service games in 194 of 224 rows; Stage 0: service games for 26 rows, 15 "
                    "matches without a box; TML against RG as in the reasons; no women's qualifying in Stage 0); TML's "
                    "2026 main-draw rows, not in Stage 0, carry the fault for the men (64.70% v RG 62.23%)."],
            },
        },
        "other_findings": (
            "1. Service games of retirements: the proposal's MatchBeats count (sources._mb_counts, sv_gms_regular: every "
            "game with points served by one player) includes the unfinished game at a retirement; Sackmann's rows exclude "
            "it (2022-2025: 62 of 62 retirement rows, all 12 with an unfinished game; 2019-2021: 40 of 42). It gives one "
            "player +1 in 11 proposed matches (8 of 2022-2025, where Sackmann's count was already right; 3 of 2026). "
            "Counting complete games (isGameComplete) fixes it; my values do. With complete games, E1's agreement is "
            "98.1% (2022-2025) and 80.9% (2019-2021), and E3's '56 rows' are 42 corrections, 6 blank counts filled "
            "(2023 Q3) and these 8. "
            "2. Service games are fixed by the score and the first server: servers alternate game by game, a tiebreak "
            "taking one turn. Derived from RG's score and MatchBeats' first point, they agree with MatchBeats' server on "
            "every game it holds in every match of 2019-2026 but 2021 QD029, so they fill the games MatchBeats lacks. "
            "They equal the row's count on all 24 rows where the proposal falls back to it, and give Maestrelli-Noguchi "
            "(2026 QM080) 14 and 15 where the proposal has blanks. "
            "3. Referee noise baselines (sides where RG and the row agree): hand charts read the agreed first serves in "
            "+1 on 11.9%, -1 on 1.9% of 469 sides; Court Vision 2019/2020/2022 +1 1.1%, -1 0.6% of 535. Disputed W22 "
            "sides: '+1': charts read the row 8/54, Court Vision 0/63; '-1': charts 2/21, Court Vision 1/20; size 2 or "
            "more: charts 1/84, Court Vision 0/160. "
            "4. Court Vision copy: a faulted first serve's row often carries no player ids ('NA': 4,094 rows in RG 2024, "
            "51 in 2022). Reading the point's server off its first row loses those points; reading it off the point's "
            "other row, my Court Vision 2022 tallies equal E2's on every cell. "
            "5. stage0_build.apply_box_overrides indexes ov['score'] and ov['minutes'] even when the table has no such "
            "columns (KeyError); the proposed table carries both, so it applies, but a table built without them fails "
            "(guard with `if col in ov`). "
            "6. Identity slip, outside this vote: 2024 QM126 Kolar d. 'T. Farquhar' (atp 212408, USA) is RG's Thomas "
            "Faurel (FRA); RG's box links by the opponent, games and winner, but the row's loser is the wrong player. "
            "It needs an identity correction before any box. "
            "7. E6's '252 RG matches without a box get one' counts blank raw rows. By Stage 0's own has_box, 277 "
            "matches gain a box: those 252, plus 25 that Stage 0 drops today for failed or partial boxes (14 TML "
            "qualifying matches of 2026; 11 of 2022-2025, e.g. Barrios Vera-Kovalik, Uchijima-Yuan, Pigossi-Kawa). "
            "8. TML's RG 2026 main-draw rows (dropped for Sackmann's blank rows) carry the first-serve fault for the men "
            "(pooled 64.70% v RG 62.23%; women 63.61% v 63.03%). They should never stand in for Sackmann's rows. "
            "9. Every claim E1-E7 was recomputed from the raw files and holds, with the definitions noted above. My "
            "numbers equal the proposal on every class (4,556 player rows) and on 27,149 of 27,162 override values; "
            "whole_box_rows.csv otherwise differs from mine only where neither is used: RG's statistics placed on the "
            "identity-slip match, 3 hand charts the lead linked in 'equal' matches, one MatchBeats point with scorer '0' "
            "(2024 SM123), and service games of non-proposed rows. "
            "10. 2024 men's qualifying: the 4 statistics_short matches and the identity slip keep Sackmann's split, so the "
            "pooled first-serve-in rate after the overrides alone is 61.91% against RG's 61.18%. Round 1's split rows of "
            "three of those matches, which the candidate keeps, narrow the gap."),
    }
    (HERE / "verdict.json").write_text(json.dumps(verdict, indent=1, ensure_ascii=False), encoding="utf-8")
    print("overrides_scope.csv:", len(ov), "matches (W22", n22, "| W26", n26, ") | exchanges_scope.csv: 4 rows |",
          "differing from the proposal:", len(d22), "+", len(d26))


if __name__ == "__main__":
    main()
