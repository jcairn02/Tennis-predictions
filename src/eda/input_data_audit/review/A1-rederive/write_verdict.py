"""Write data/studies/input_data_audit/fixes/A1-rederive/verdict.json (reviewer A1-rederive, lens: re-derive)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

D = "data/studies/input_data_audit/fixes/A1-rederive/"
S = "src/eda/input_data_audit/review/A1-rederive/"

v = {"reviewer": "A1-rederive", "lens": "rederive", "candidates": {}}
C = v["candidates"]

C["F1"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("All 2,382 Stage 0 player rows (1,191 matches, both players) that carry a box at the 30 WTA tour events "
              "dated 23 Feb - 24 Aug 2015 other than Doha (Acapulco ... New Haven), all from Sackmann's "
              "wta_matches_2015.csv; 193 of them have df = 0 (no-op). The same as the candidate's 2,382 rows. Not in "
              "scope: 10 raw player rows (5 matches) of these events without a Stage 0 box (4 failed B6 because of "
              "this fault, Kuala Lumpur F is a partial box)."),
    "scope_file": D + "F1_scope.csv",
    "fix": "svpt := svpt + df on each listed player row; every other count unchanged",
    "reasons": (
        "Raw file: each of the 30 events has >= 1 row failing the definition test second_won + df <= svpt - first_in "
        "(1-13% of rows per event; 105 of 3,890 WTA 2015 rows; 0 in 2014, 2016, the four 2015 Slams and the 9 "
        "earlier 2015 events). Second-serve points won read 49.8-55.4% per event (42-48% everywhere else). MCP "
        "(my own link, 168 window player-matches): among df > 0 rows svpt + df equals the charted serve points in 137 "
        "of 153 and svpt alone in 2 (Suarez Navarro, Rome F: second_won also off and her opponent's row exclusive; "
        "Pliskova, Birmingham F: first_in off by 2 and Kerber's row off by 6, a noisy chart). Outside the window "
        "(df > 0): svpt 692/825, svpt + df 8/825. The audit's '12% svpt alone' is the df = 0 rows (14 of my 16). "
        "The other counts agree with MCP equally inside and outside the window (first_in 70% vs 69%, second_won 86% "
        "vs 83%, df 97% vs 96%), so only svpt changes. A calibrated per-match likelihood (second serves in, binomial) "
        "puts the inclusive share of the 30 events at 0.0 (95% upper bound 3.3%); it reads Doha 2015's R32-R16 "
        "inclusive (0.90), as MCP shows, and every window event exclusive. After the fix no scope row fails B3, B6 "
        "or the definition test. Boundaries: Doha (same week) is mixed: MCP shows R32/R16 inclusive (6 rows) but "
        "SF Safarova-Suarez Navarro and F Azarenka-Safarova exclusive (4 rows exact once df is added); those two "
        "matches are also corrupt but lie outside the candidate's scope (ext_F1_doha.csv). Acapulco's R32 is already "
        "exclusive (rows 782 and 794 fail the definition test). The US Open 2015 is inclusive and no WTA tour box "
        "scores follow it in 2015. 2015 qualifying and Fed Cup have no box scores (0 of 19,727 qual/ITF rows; 0 of "
        "130 Fed Cup rows); the 2015 Slams are inclusive (MCP svpt-only vs svpt+df-only: AO 35/0, RG 24/1, "
        "Wimbledon 36/0, USO 6/1). TML's 2015 WTA rows are a verbatim copy of Sackmann's."),
    "checks": [
        f"{S}f1_events.py: per-event definition-test failures and second-serve shares, WTA 2014-2016 (f1_events_2014_2016.csv)",
        f"{S}f1_mcp.py: MCP vs svpt / svpt+df split by window and df=0/df>0 (f1_mcp_pairs.csv): window df>0 137/153 vs 2/153",
        f"{S}f1_scope.py: raw rows -> Stage 0: 2,392 raw player rows, 2,382 with Stage 0 box, Stage 0 equals raw on all 2,382; after fix 0 B3/B6/definition failures",
        f"{S}f1_scope.py + f1_mixture.py: calibrated per-match LLR and per-event inclusive share (f1_event_mixture.csv): 30 events 0.0 [0, 0.033]",
        "boundary checks: Doha 2015 by round (MCP: R32/R16 inclusive, SF/F exclusive), Acapulco R32 definition failures, 2015 Slams, qual/ITF, Fed Cup",
        "TML 2015 WTA vs Sackmann: identical box values (not independent)"]}

C["F2"] = {
    "vote": "confirm_narrowed", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("59 of the 88 matches (118 player rows). 52 verified by the WTA API (all 18 counts equal once the boxes "
              "are exchanged; the API's winner = the recorded winner): Abu Dhabi 2021 28 (22 main + 6 qualifying), "
              "Phillip Island 2021 18 (14 + 4), Saint-Malo 2025 2, San Jose 2022 R32 Osaka-Zheng, Linz 2023 Q2 "
              "Galfi-Rakhimova, Hua Hin 2024 R16 Rodionova-Bai, Charleston 2024 R64 Gracheva-Ngounoue. 3 verified by "
              "official records: US Open 2022 Q1 Seppi-Horansky (US Open statistics, 18/18), Wimbledon 2019 R128 "
              "Wang-Martincova (Wimbledon statistics, 14/18 exchanged vs 3/18 as recorded), Miami 2025 R64 "
              "Bergs-Rublev (ATP key statistics, 12/12). 4 on internal evidence only: Roanne CH 2021 R32 "
              "Debru-Pellegrino, Barletta CH 2025 R16 Dodig-Sultanov, W50 Indian Harbour Beach 2025 R32 "
              "Karatancheva-Kononova, Tenerife 1 CH 2026 R32 Merida Aguilar-Samuel. Per-match verdicts for all 88: "
              + D + "F2_verdicts_all88.csv"),
    "scope_file": D + "f2_scope.csv",
    "fix": "exchange all nine counts between the two player rows of each listed match (the players, scores and winners stay)",
    "reasons": (
        "Rejected (29): Palermo 2022 R32 Sorribes Tormo-Bogdan: the WTA API equals the box AS RECORDED. Five Slam "
        "matches whose independent record matches the box as recorded: AO 2012 R32 Kukushkin-Monfils (Slam PBP "
        "svpt 148/159, points won 86/87, aces, DFs all as recorded), Wimbledon 2016 R128 Bellucci-Bemelmans (PBP), "
        "RG 2019 R64 Blinkova-Garcia (PBP), AO 2022 R128 Paire-Monteiro (ball tracking: 12/14 as recorded, only "
        "the service games swapped), AO 2025 R128 Blinkova-Saville (infosys PBP), plus AO 2025 Q2 Garin-Djere "
        "(infosys: aces 3/7 and DFs as recorded). W35 Timaru 2025 F: the score '1-6 2-6' and the box agree that the "
        "recorded winner lost, so the winner label, not the box, is the likely error. 21 internal-only matches with "
        "a games margin <= 1: a one-game service-game attribution makes the box 'fit exchanged', which is what all "
        "5 Slam records show. Calibration: among 22,576 boxes the WTA API shows genuine, none fits only when "
        "exchanged; among 72 API-verified exchanges, 48 have a games margin >= 4 and a recorded-winner point deficit "
        ">= 10, which is the rule used for the 4 internal-only confirmations (each exact or within one game once "
        "exchanged, deficits 10-27 points, and the recorded winner plays the next round, so the winner is right). "
        "B0-B9 are per-player or symmetric and unchanged by the exchange. Outside the 88, the WTA API shows 24 more "
        "exact exchanges (Abu Dhabi 2021 +11, Phillip Island 2021 +6, Saint-Malo 2025 +2 and others; "
        "ext_F2_api_exchanges_outside_88.csv), not voted here."),
    "checks": [
        f"{S}wta_api_link.py / wta_api_agree.py: Sackmann WTA 2019-2026 vs WTA API, 24,519 linked matches; 99.4% equal on all 18 counts outside the 3 faulty events; exchanges classified",
        f"{S}f2_internal.py: my games identity, points, progression, WTA API per player (f2_internal.csv): 52 equal_exchanged, 1 equal_recorded",
        f"{S}f2_external.py: MCP, Sackmann Slam PBP, infosys AO 2025, ATP key stats (f2_external.csv)",
        f"{S}f2_verdict.py: US Open 2022 statistics, Wimbledon 2019 statistics, ATP key stats Miami 2025, AO 2022 ball tracking",
        f"{S}f2_calibrate.py: false 'exchange fits' among API-verified genuine boxes = 0/22,576 (f2_calibration.csv)"]}

C["F3a"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("38 matches (76 player rows), not 'about 19 matches, 38 player rows': every Sackmann row of Adelaide 2 "
              "2022 (tourney 2022-2030, 10 Jan 2022) whose 18-count box equals an Adelaide 2021 box (2021-2030, "
              "22 Feb 2021). 70 of the 76 player rows carry a box in Stage 0 (R16 Gauff-Kostyuk, R32 Davis-Teichmann "
              "and Q1 Hunter-Wang already fail Stage 0's checks). The 4 boxed matches that are not copies (Q1 rows "
              "31677-31680) are excluded; 7 matches have no box."),
    "scope_file": D + "F3a_scope.csv",
    "fix": "blank all nine counts of both players in each listed match (missing, as Stage 0 treats a failed box)",
    "reasons": (
        "38 of the 42 boxed Adelaide 2 2022 matches carry an Adelaide 2021 box verbatim, placed by match number: "
        "the 2022 final Keys d. Riske carries the 2021 final Swiatek d. Bencic; the SF walkover Riske d. Zidansek "
        "carries Swiatek d. Teichmann. The WTA API's 2022 counts (event 2030) differ from Sackmann on every one of "
        "the copies it holds, while the 4 non-copies equal the API on all 18 counts. TML's Adelaide 2 2022 rows "
        "carry the same copies (26 of 27 identical), so TML is no independent record."),
    "checks": [f"{S}f3.py: copy search against all Adelaide 2021 boxes, both orientations (f3_matches.csv)",
               f"{S}f3b.py: Stage 0 mapping (Stage 0 equals the copied counts on all 70 boxed rows), TML comparison"]}

C["F3b"] = {
    "vote": "confirm", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("The same 38 matches (76 player rows): 37 matches (74 rows) take the WTA API's counts (event 2030, "
              "2022; Storm Hunter is 'Storm Sanders' in the API), all of which pass B0-B9 against the 2022 score; the "
              "SF walkover Riske d. Zidansek (2 rows, which has a box in Stage 0) is blanked. Per-row API counts are "
              "in the scope file."),
    "scope_file": D + "F3b_scope.csv",
    "fix": ("replace all nine counts of both players with the WTA API's counts where f3b_action = 'replace from WTA "
            "API' (api_* columns); blank where it says 'blank (walkover...)'. Preferred over F3a."),
    "reasons": (
        "The WTA API measures what Sackmann measures: on the clean WTA events of 2021-2022 (136 events, 6,452 "
        "matches; Abu Dhabi 2021, Phillip Island 2021 and Adelaide 2 2022 excluded) the exact per-player-row "
        "agreement is ace 99.81%, df 99.78%, svpt 99.72%, first_in 99.71%, first_won 99.71%, second_won 99.75%, "
        "sv_gms 99.87%, bp_saved 99.74%, bp_faced 99.73%, and all 18 counts 99.675% of matches; 18 of the 21 "
        "differing matches differ in >= 8 counts (Sackmann-side whole-box errors). The API's Adelaide 2 2022 counts "
        "pass every Stage 0 check. Replacing with a source that matches the training data beats blanking (as the "
        "Slam box-score decision argued)."),
    "checks": [f"{S}f3.py: WTA API per-count agreement on clean 2021-2022 events (f3_api_agreement.csv)",
               f"{S}f3b.py: API link per copied match and B0-B9 on the API counts (f3_scope.csv)"]}

C["F4"] = {
    "vote": "confirm_narrowed", "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
    "scope": ("27 copy rows (27 matches, 54 player rows; 22 still carry a Stage 0 box) of the audit's 41 rows (39 "
              "same-pair + 2 Dusseldorf). Which row is the copy is decided per pair and is NOT always the later match: "
              "19 pairs confirm the audit's listed copy (incl. both Dusseldorf 2012 final rubbers, which carry the "
              "box of the RR rubber Tipsarevic d. Kohlschreiber), and in 8 pairs the audit's SOURCE row is the copy: "
              "Montreal 2010 F Wozniacki-Zvonareva, Nanchang 2014 R32 Xu-Zhang, RG 2013 R128 Cornet-Koehler, AO 2011 "
              "Q1 Gojnea-Han, Wimbledon 2014 QF Kvitova-Strycova, Marbella 2010 Q1 Halep-Rogowska, Nuremberg 2014 "
              "R32 Bouchard-Strycova, Acapulco 2010 Q1 Pous Tio-Soler Espinosa. 14 pairs undecided and excluded "
              "(f4_audit_pairs.csv). The scope file lists the copy rows by match_id, player_id, _source_file, _row."),
    "scope_file": D + "f4_scope.csv",
    "fix": "blank all nine counts of both players in each listed copy row",
    "reasons": (
        "My own repeat search on 16 counts (service games are blank in WTA rows before Feb 2015) finds the same 40 "
        "same-pair repeats as the audit plus two same-score ones; the audit file has no duplicate lines. "
        "Decisions: (R1) an independent record (Sackmann's Slam PBP, MCP linked by event name and date) agrees with "
        "one row, or contradicts one while the box fits the other; (R2) exact games identity with service games "
        "fits one row only; (R3) impossible serve points per game on one row (< 4 or > 10.5) and normal on the "
        "other; (R4) the break-margin test fails and points per game lie outside 4.8-8.5 on one row only. "
        "Calibration on 259,203 boxes: the break-margin test fails 1.2% of genuine boxes; points per game 99.9th "
        "percentile 8.7 (ATP) / 9.1 (WTA). Examples of reversals: RG 2013 PBP 70/60 serve points vs the box's "
        "53/66 while USO 2013's PBP equals it; Wimbledon 2014 QF: MCP and PBP 56/78 vs 48/47; Nanchang 2014 12.9 "
        "and Acapulco 2010 24.3 points per game; AO 2011 Q1 2.9. Undecided pairs have no record and internal tests "
        "that do not separate the rows (e.g. Koukalova-Vekic x3; Kudryavtseva-Parra Santonja, whose box fits "
        "neither row at 11.5 points per game). Extension, not voted: AO 2012 R128 Li-Pervak carries Wimbledon "
        "2012's box (same score, not in the audit's list; ext_F4_other_pairs.csv)."),
    "checks": [f"{S}f4.py: all verbatim 16-count repeats in Sackmann 2009-2026 (f4_groups.csv, f4_cross_groups.csv)",
               f"{S}f4_decide.py: per-row break-margin, points per game, games identity, MCP and Slam PBP (f4_pairs.csv)",
               f"{S}f4_calibrate.py: false-failure rates on all other boxes (f4_calibration.csv)",
               f"{S}f4_scope.py: mapping to the audit's 41 rows and Stage 0 (f4_audit_pairs.csv); Stage 0 equals raw on all 44 boxed scope rows"]}

C["F5"] = {
    "vote": "reject", "corrupt_beyond_doubt": True, "fix_clear_and_correct": False,
    "scope": ("None. (Corrupt beyond doubt: the first/second-serve split of Sackmann's RG 2025 qualifying rows where "
              "first_in exceeds RG's by several serves while serve points and serve points won agree, e.g. Li Tu Q1 "
              "82 vs 57 first serves in, 11 vs 22 second-serve points won. The proposed fix is not clear.)"),
    "scope_file": None,
    "fix": "none",
    "reasons": (
        "RG's key statistics do give all nine counts (svpt and first_in from 'First Serve', first_won and second_won "
        "from 'Win On 1st/2nd Serve', bp from the opponent's 'Break Points Won', sv_gms from the opponent's 'Break "
        "Points Converted Games' denominator), are internally consistent (100% of denominator and total checks) and "
        "equal RG's own point-by-point in 99.3-99.95% of player rows for the point counts (service games only 80%). "
        "But they do not reproduce Sackmann's measurement where no large fault is suspected. In the RG 2025 main "
        "draw all nine counts agree in only 47% (men) and 56% (women) of player rows: svpt 92-93%, first_in "
        "75-76%, sv_gms 68-84%. Against TML's 2026 men's qualifying, whose pooled first-in rate equals RG's (63.2%), "
        "svpt agrees in 74%, first_in in 66% (differences symmetric) and sv_gms in 11%. So replacing whole boxes would "
        "change serve points and service games in many rows for convention reasons, not error. The decision's own "
        "rule ('a Slam feed that has matched Sackmann's history', 98-100% at the US Open and Wimbledon) is not met. "
        "The candidate's scope, 'rows that differ', mixes the fault with these differences. The fix is not unique "
        "(blank the split, replace only the split, replace the box), and docs/decisions/2026-10-06-slam-box-scores.md "
        "left Sackmann's RG qualifying 2022-2025 unchanged until a study measures its effect. Observed fault pattern "
        "(qualifying 2025): where svpt agrees, serve points won agree in 99.4-99.5% of rows, but Sackmann's first_in "
        "is higher in 57-60% of rows (mean +3.4 to +3.8; >= 6 in 21-24%). A narrower candidate (replace first_in, "
        "first_won and second_won from RG where svpt and serve points won agree) could be examined separately."),
    "checks": [f"{S}f5.py: keystats parse and consistency, keystats vs RG PBP, linkage to Stage 0, agreement by year/tour/draw (f5_agreement.csv, f5_rg_vs_stage0.csv)",
               "size and sign of the differences, main vs qualifying vs TML 2026 (inline analysis on f5_rg_vs_stage0.csv)",
               "read docs/decisions/2026-10-06-slam-box-scores.md (Not decided: RG men's qualifying 2022-2025)"]}

C["F6"] = {
    "vote": "confirm_exclusion", "corrupt_beyond_doubt": False, "fix_clear_and_correct": False,
    "scope": "None (exclusion confirmed).",
    "scope_file": None,
    "fix": "none",
    "reasons": (
        "The fault is real at edition level (Stage 0 pooled first serves in): RG qualifying 2022-2025 men 68.5/65.3/"
        "65.2/68.6% (2012-2021: 59.8-62.7%; TML 2026 63.2%) and women 69.9/68.1/67.0/68.6% (61.0-65.2%); RG main "
        "draw 2022 men 66.1%, women 65.5% (other years 59.9-63.9%), women 2024 64.7%; Paris Olympics 2024 men 70.3%, "
        "women 67.9% (2012/2016: 61.3-64.4%). But no per-match record covers it: the ball tracking holds only part "
        "of the main draws (2022 about 88% of rows, 2023-2024 about half, none of qualifying or the Olympics). "
        "Where it holds rows, the pattern is not uniform: 2019 matches Stage 0 exactly (100%); in 2022 Stage 0 "
        "reads higher in 53% of rows (mean +3.1 men, +1.6 women); in 2023-2024 it reads higher in only 15-25% "
        "(mean -0.9 to +0.4). The ball tracking has its own gaps (2024 svpt equal in only 68%). So which rows are "
        "corrupt cannot be told from the edition signal, and the fix (blank the split, blank the box, or replace "
        "from partial ball tracking) is a choice. The 6 Oct decision left these editions flagged pending a study."),
    "checks": [f"{S}f6.py: pooled rates by RG/Olympics edition 2012-2026 (f6_editions.csv); ball tracking RG 2019-2024 vs Stage 0 (f6_balltracking_vs_stage0.csv)"]}

out = R.OUT / "verdict.json"
out.write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
json.loads(out.read_text(encoding="utf-8"))
print("wrote", out)
