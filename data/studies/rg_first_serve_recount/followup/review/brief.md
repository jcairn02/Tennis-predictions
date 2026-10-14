# Roland Garros follow-ups of 9 October: brief for the reviewers (round 2)

9 October 2026 · Written by the lead session for three independent reviewers (R1-rederive, R2-skeptic, R3-referee) · Follow-ups to item 6 of [the adoption checklist](../../../../../docs/studies/adoption_framework/checklist.md), whose steps 1–2 are in [the report](../../../../../docs/studies/rg_first_serve_recount/README.md).

## 1. What you are deciding

The step-2 report ended with three suggestions. The owner answered (9 Oct 2026): "Do all of these that you think is a good idea, review it first, then execute if you do." The lead judged all three worth doing. One is a documentation fix. **The other two change data, so they come to you:**

| Group | What | Operation |
|---|---|---|
| **RGX** | Four RG 2021 women's main-draw matches where Sackmann's row gives the winner the loser's box and the reverse | `exchange_box`: the nine counts exchanged back (the fix F2 of 8 Oct, rule E2) |
| **W22** | RG's whole box score for the Roland Garros matches of 2022–2025 (Sackmann's rows) | One override row per match (stage0_build's `--box-overrides` table): the nine counts of both players from RG's record |
| **W26** | The same for 2026: Sackmann's blank main-draw rows (both tours) and TML's men's qualifying rows | As W22 |

**W22 and W26 apply the rule of the Slam decision of 6 Oct** ([decision](../../../../../docs/decisions/2026-10-06-slam-box-scores.md), point 4): "at a Slam whose official feed is held and has matched Sackmann's history, the feed is the box-score source." That decision applied it to Wimbledon and the US Open 2026 and listed Roland Garros 2026 as "no official feed is held". The feed has been held since 7 Oct.

**What is kept is decided as on 8 Oct:** only what all three of you confirm, the same matches with the same values.

**What "confirm" means:**
* **RGX:** as on 8 Oct, the row is corrupt beyond reasonable doubt, and the fix is clear, unique and correct.
* **W22 and W26:** two bars are possible. Say which you apply, and you may apply a different one to each group.
  * **The source rule (the lead's proposal).** Confirm a match when all of these hold:
    * RG's record qualifies as the source under the 6 Oct rule;
    * the override row is RG's record of this match: the right match, the right players, the right orientation, the values as RG's documents give them;
    * the official box passes Stage 0's checks;
    * no record shows RG's value wrong on a count that changes.

    The row need not be provably corrupt on every count. Where the evidence is silent, the rule takes the feed, as it did for Wimbledon and the US Open.
  * **The 8 Oct bar.** Confirm only matches whose row is corrupt beyond reasonable doubt on every count that changes.
  * **Why it matters.** Step 2's reviewers judged the split alone on the 8 Oct bar. They dropped most sides where Sackmann has fewer first serves in than RG ("−", "0"), because RG's own record is sometimes the wrong one there. The source rule takes RG's values on those too, unless an independent record contradicts them.
    * The proposal already leaves out any match where Court Vision (2019, 2020, 2022) or a hand chart reads the row's value instead of RG's.
    * Whether the remaining small differences should follow the rule is the main judgment you are asked for.
* **W26's main draws:** Sackmann's 2026 main-draw rows are blank, so nothing in them is corrupt. The question is only whether RG's box is the right one to fill them.

**You judge the data only.** Whether the changed data enters the model is decided later: a candidate build under the frozen-reference rule (`CLAUDE.md`), then the owner's acceptance. Don't weigh model performance; no model result is read here.

## 2. Read first

* **The report of steps 1–2:** `docs/studies/rg_first_serve_recount/README.md`, §§ 1–5. The records, the recount's validation, the proposal, round 1's review, and the findings (§ 5) that led here.
* **Round 1:** the brief (`data/studies/rg_first_serve_recount/review/brief.md`) and the consensus (`confirmed/consensus.json`: 1,447 sides confirmed, on 933 rows).
* **The two decisions:** 6 Oct (Slam box scores: point 4 and "Not decided") and 8 Oct (corrupt data fixes: the three-reviewer rule, F2, and F5/F6).

## 3. What is new since round 1

* **RG's own statistics for 2026,** fetched today with the same adapter (`src/ingest/point_sources/rolandgarros.py`). It writes raw copies and receipts; the run's summary and log are in `data/studies/rg_first_serve_recount/followup/collection/`. The staged tables (`data/dump/points/rolandgarros/`) now hold 2019–2026.
* **The proposal code:** `src/eda/rg_first_serve_recount/whole_box.py`. Its tables are in `data/studies/rg_first_serve_recount/followup/`.
* **Stage 0 overrides can now name a Sackmann row.** `stage0_build.apply_box_overrides` accepts an optional `source` column (`sackmann` or `tml`). The decided table has no such column and reads as TML, as before. Tests: `test/rg_first_serve_recount/test_overrides.py`.
* **MatchBeats service games in Sackmann's convention:** `sources._mb_counts` adds `sv_gms_regular`, the games a player served with tiebreak games not counted.

## 4. The lead's claims (to check)

Counts are Sackmann's: serve points include double faults.

* **E1. RG qualifies under the 6 Oct rule.**
  * **The feed is held:** RG's statistics for 2019–2026, its MatchBeats for 2019–2026, and its key statistics for 2025–2026.
  * **It matched Sackmann's history.** In 2019–2021, RG's statistics equal Sackmann's rows on all eight counts they share in 2,732 of 2,740 linked player rows (`control_2019_2021.csv`). The other 8 are the four RGX matches.
  * **Service games are the exception.** RG's statistics have none.
    * MatchBeats' service games, tiebreaks not counted, equal Sackmann's in 97.8% of 2022–2025 rows.
    * In 2019–2021 they equal only 80.6%: Sackmann's earlier rows mix both ways of counting tiebreaks, and Stage 0's B5 accepts either.
* **E2. On the counts the proposal changes, the independent records side with RG.** Proposed player rows, where the record holds every point:

  | Count | Player rows changing | Court Vision 2022: RG's value / the row's / held | Hand charts: RG's / the row's / held |
  |---|---:|---|---|
  | serve points | 357 | 15 / 0 / 15 | 39 / 0 / 39 |
  | aces | 83 | 10 / 0 / 10 | 2 / 0 / 2 |
  | double faults | 207 | 21 / 0 / 21 | 5 / 0 / 5 |
  | first serves in | 1,833 | 232 / 0 / 236 | 130 / 0 / 140 |
  | first-serve points won | 1,390 | 182 / 0 / 185 | 84 / 0 / 88 |
  | second-serve points won | 1,378 | 178 / 0 / 181 | 81 / 0 / 86 |

  * The zeros are partly by construction: 13 matches where a referee read the row's value on some count are left out (`referee_contradicts`). Almost all are one-count differences of 1.
  * "Held" counts rows where the referee reads neither value.
  * **Where aces and double faults change, the row is almost always lower than RG's:**
    * aces: 81 of 83 changing rows, 65 of them by one;
    * double faults: 182 of 207, 142 by one.

    A record that misses some aces and double faults would do this (*inferred*).
* **E3. Service games.** In the proposed player rows:
  * 2,976 take MatchBeats' count;
  * 40 keep the row's own (MatchBeats lacks points of the match);
  * 2 are blank (neither fits the score).

  Where MatchBeats changes Sackmann's count in 2022–2025 (56 rows), it fits the score. Examples:
  * Nakashima 6-4 2-6 4-6 7-6(3) 6-2: 48 non-tiebreak games, so 24 each. Sackmann has 23, MatchBeats 24.
  * Gojo, 3 tiebreaks: 28 each. Sackmann has 27.
  * The partial boxes: Kovalik 6 → 15 in a 30-game match.
* **E4. RG 2026 in Stage 0 today:**
  * **Main draws:** 127 men's and 127 women's matches from Sackmann's rows, every one with no box score. The 6 Oct decision names only the men's.
  * **Men's qualifying:** 112 matches from TML.
    * TML writes 0 service games in 194 of 224 player rows, so Stage 0 holds service games for only 26 rows, and 15 matches have no box.
    * TML's other counts are near RG's but not equal: serve points in 69% of rows (88% within one), first serves in 60% (78% within one).
    * Unlike TML's Wimbledon 2026, its pooled first serves in (63.2%) are level with RG's (63.1%): this is not the first-serve fault.
  * **Women's qualifying:** none in Stage 0 (a coverage question, not proposed).
* **E5. RGX, the four exchanged boxes** (`exchange_rows.csv`):
  * RG's statistics equal Sackmann's two boxes exchanged, on all eight counts, for both players, and not as recorded.
  * Service games are equal for both players in each match (13–13, 16–16, 13–13, 15–15), so exchanging all nine is exact.
* **E6. The dry run** (`proposal_summary.json`, `dry_run`). The whole candidate applied to the raw rows with the build's own code: the decided override table plus the 1,509 RG rows, then the decided corrections plus step 2's split rows of matches without an override (12 RG rows, 46 Olympic rows) and the 4 exchanges.
  * Every override row reads its table afterwards: 1,509 RG and 731 decided.
  * No row is both overridden and corrected.
  * The exchanges read exchanged.
  * 3,265 rows change, 0 outside the tables.
  * 252 RG matches without a box get one: 251 in 2026, and Moreno de Alboran–Karatsev 2023.
* **E7. The proposal:**
  * **2,278 Stage 0 matches** of 2022–2026: 1,509 proposed, 730 equal, 12 walkovers, 13 `statistics_short`, 13 `referee_contradicts`, 1 `no_link` (Kolar d. Faurel, Sackmann's "T. Farquhar").
  * **The proposed matches:** 1,177 in 2022–2025, and 332 in 2026 (124 men's main, 127 women's main, 81 men's qualifying).
  * **Step 2's confirmed split rows:** 875 of its 887 RG rows lie inside proposed overrides, which give the same split.
  * Pooled first serves in after the overrides equal RG's own in every edition and draw, except where `statistics_short` matches stay out.

## 5. The proposal

* **`whole_box_rows.csv`:** one row per Stage 0 player row of RG 2022–2026. Columns:
  * the match's class and what changes;
  * `raw_*`: the row as read, before Stage 0's checks;
  * `off_*`: RG's record (eight counts from RG's statistics, `off_sv_gms` as `sv_gms_from` says);
  * MatchBeats `mb_*`, key statistics `ks_*`, Court Vision `cv_*` and the hand charts `mcp_*`.
* **`proposed_overrides.csv`:** one row per proposed match, in the override table's columns:
  * the key stage0_build looks up: `source`, `tour`, `tid`, `round`, `winner_key`, `loser_key`;
  * `w_*` and `l_*` for the raw row's winner and loser;
  * the RG document's SHA-256 and retrieval time. `tml_score` is the row's own score, whatever its source.
* **`proposed_exchanges.csv`** (row_corrections.csv's columns, fix `RGX`) and **`exchange_rows.csv`** (the evidence).
* **`proposal_summary.json`:** classes by edition, the counts that change, what the referees say, pooled rates before and after, the dry run.
* **Classes of a match** (the first that applies):
  1. `walkover`;
  2. `no_link`: RG's statistics not placed on the match by both names;
  3. `record_fails_checks`: RG's own consistency checks fail, or a count is missing;
  4. `names`: a player is not the raw row's winner or loser by name;
  5. `equal`: all eight counts already equal, nothing to do;
  6. `statistics_short`: MatchBeats holds more serve points than RG's statistics;
  7. `mb_contradicts`: MatchBeats or the key statistics hold every point and give another split, aces or double faults;
  8. `referee_contradicts`: as above;
  9. `fails_stage0_checks`: the official box fails B0–B4 or B6–B9 under the row's score;
  10. `proposed`.

## 6. Points to settle

1. **The rule.** Does RG qualify under the 6 Oct rule (feed held; matched Sackmann's history)? Is applying it to Sackmann's own history (2022–2025) justified, or should W22 meet the 8 Oct bar? The 6 Oct decision applied the rule only to rows after Sackmann's data ends.
2. **The bar** for W22 and W26, and any narrower scope (editions, draws, classes, size of difference).
3. **The values.** Do your own numbers equal the override rows? Check them against RG's raw API documents, and service games against MatchBeats.
4. **Service games.** RG's statistics have none.
   * Is MatchBeats' count (tiebreaks not counted) right where it changes the row's?
   * Is the fallback acceptable: the row's own count, the one count not from RG's record?
5. **Links and orientation,** especially in 2026: TML's qualifying rows, and Sackmann's blank main-draw rows of both tours.
6. **Exclusions.** Should any proposed match be left out? For example, RG's record wrong or incomplete, or a different convention: retirements, defaults, penalty points. Should any excluded match be in?
7. **RGX.** Corrupt beyond doubt, and the fix clear?
   * Check the winner: the score's orientation, and who played the next round.
   * Check all nine counts, service games included.
   * Rule out other explanations, such as names swapped rather than boxes.

## 7. Your lens

* **R1-rederive: recompute every claim from the raw files, with your own code.**
  * Parse RG's API documents (`data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz`) yourself.
  * Decrypt and recount MatchBeats with the adapter's `decrypt` and `blocks_of`, as in round 1.
  * Read Sackmann's and TML's rows with `stage0_build.normalise(stage0_build.load_raw())`, and link them yourself.
  * Don't import `whole_box.py` or read the proposal's tables until you have your own numbers. Then compare, and explain every difference.
* **R2-skeptic: attack every claim. Look for another explanation, and for matches that should not be there or should be.**
  * Conventions: retirements, defaults, penalty points.
  * Links in 2026, where TML's names and Sackmann's blank rows meet RG's.
  * Whether RG's record is the faulty one on the small differences.
  * Whether the service-game convention holds.
  * Whether the rule is stretched.
* **R3-referee: check against independent records, and simulate the fix.**
  * The hand charts; Court Vision where reliable (2019, 2020, 2022).
  * Pooled rates by edition.
  * Build the candidate's two tables as `whole_box.candidate_tables` does, or your own way. Apply them with `stage0_build.apply_box_overrides`, then `src.eda.input_data_audit.corrections.apply_row_corrections`, to the raw rows.
  * Reproduce Stage 0's box checks (B0–B9) on the result.
  * List the rows Stage 0 drops today that the overrides bring back.

You may read your own lens's round-1 work and reuse its code: `data/studies/rg_first_serve_recount/review/<you>/` and `src/eda/rg_first_serve_recount/review/<you>/`. Don't read the other lenses' folders, of either round.

## 8. What to write

Your outputs go in `data/studies/rg_first_serve_recount/followup/review/<your name>/`, and your scripts in `src/eda/rg_first_serve_recount/review_followup/<your name>/`.

* **`verdict.json`:**
  ```json
  {"reviewer": "R1-rederive", "lens": "rederive",
   "groups": {"RGX": {"vote": "confirm|narrow|reject", "corrupt_beyond_doubt": true, "fix_clear_and_correct": true,
                      "scope": "...", "reasons": "...", "checks": ["script: what it showed"]},
              "W22": {"vote": "confirm|narrow|reject", "rule_applies": true, "bar": "source rule|8 Oct bar",
                      "scope": "which matches, by what test", "reasons": "...", "checks": ["..."]},
              "W26": {...}},
   "other_findings": "..."}
  ```
* **`overrides_scope.csv`:** one row per match you confirm, with **the values you derived**.
  * Columns: `feed_key, stage0_match_id, w_ace, w_df, w_svpt, w_1stIn, w_1stWon, w_2ndWon, w_SvGms, w_bpSaved, w_bpFaced, l_ace, l_df, l_svpt, l_1stIn, l_1stWon, l_2ndWon, l_SvGms, l_bpSaved, l_bpFaced`.
  * `w` and `l` are the raw row's winner and loser. Leave a count blank where you agree it should be blank.
  * A match you don't list is not confirmed.
* **`exchanges_scope.csv`:** `source_file, source_row` (and optionally `match_id`), one row per exchange you confirm.
* Any evidence files you want.

## 9. Limits

* **Read-only** everywhere except your two folders.
* Don't run the lead's `whole_box.py`, `consensus_followup.py`, `recount.py`, `propose.py` or `consensus.py`: they rewrite the study's tables.
* No network: don't fetch anything.
* Use `./python.sh` (the project's `tennis` environment), from the repository root in Git Bash.
* No GPU, no `run_chain.py`, no git commands.
* Other sessions run in parallel, so keep memory moderate. Stage 0's raw loader takes about a minute and a few GB; don't hold two copies at once.
