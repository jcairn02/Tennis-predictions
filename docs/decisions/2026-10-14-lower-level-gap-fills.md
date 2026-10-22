# Lower-level data that fills holes enters by itself; only data that changes coverage is tested first

**Asked by the owner on 11 October 2026, decided on 14 October 2026.** On 11 October the owner asked (verbatim,
[master-pipeline process log](../studies/master_pipeline/process_log.md), row 11:55):

> "There was a freeze that was told to freeze and not include new challenger data until we run an experiment that checks how we should effectively integrate challenger data. We however completed the study and found how to effectively integrate challenger data by changing weight of that info and adjusting it by opponent skill. This is not that right? Why aren't we just using the newest data? Is it to save time from training a big model constantly?"

That session recommended a standing policy for lower-level data from the checked sources. What was recorded on
13 October covered only Tennis My Life's own corrections ([decision](2026-10-13-tml-lower-level-revisions.md)), so
sessions kept treating every other lower-level source's past data as frozen. On 14 October the owner asked, about
TennisLive's statistics for lower-level matches the history holds without a box score (verbatim):

> "In particular. I was pretty sure I lifted the data freeze? yet it keeps coming up?
> Filling in those ~420 box scores seems strictly better than not?"

Claude recommended filling them, and (verbatim):

> **Write down what you meant on 11 Oct, so this stops coming back.** Lower-level data goes in by itself, and is listed and covered by the check at each rebuild, when both of these hold:
> - its source counts the same way as our match table on the matches both hold;
> - it fills holes at levels and seasons we already cover.
>
> Test first only when it would add coverage we don't have in some seasons. For example, ITF box scores before 2025 would take a level from none to nearly all in a few seasons. That changes what the rating inputs mean from season to season, and it's the risk the freeze was invented for on 8 Oct. Keep the 8 Oct model as the yardstick; it costs nothing.

The owner answered: **"record the decision, update the projecct rules to match and build the tenis live package."**
Recorded and carried out by Claude ([report](../studies/tennislive_box_fill/README.md),
[process log](../studies/tennislive_box_fill/process_log.md)). The two conditions' thresholds below are Claude's,
written to make the owner's wording checkable; the owner may change them.

**Amended the same day, at the owner's word.** The first package left out 183 men's 2018 Roland Garros and Wimbledon
qualifying box scores: they missed both conditions as first written, and Claude recommended adding them, since both
misses came from where the lines were drawn. The owner answered (verbatim, quoting that paragraph): **"Yes add and fix
those"**. So both conditions were fixed (point 1 below: agreement read on today's tables; a season may catch up with
its level), and the matches entered as a second package.

## Decision

1. **Lower-level data that fills holes enters by itself.** It is built as an accepted package, or a feed's snapshot,
   by the level-evidence study's candidate builder (`src/eda/lower_level_evidence/candidate_stage0.py`), and
   registered in `accepted.json` without a decision of its own. It enters live runs at once and training at the next
   rebuild, with no retrain for it alone. Both conditions must hold:
   * **It counts the same way.** For each tour and level, take the matches the source and the history both hold with a
     box score. The source's box score must equal the history's in every count it gives on at least 98% of them,
     with at least 30 such matches. A source that gives no service games is compared on the other eight counts; Stage
     0 already accepts such a box score.
     * *The history* means the tables as they stand, with every decided repair: this reading decides. The builder's own
       links compare with the frozen copy of 8 October, which still carries errors a repair has since fixed (Roland
       Garros 2022–2026, below); that reading is recorded beside it. *Fixed at the owner's word the same day: the first
       package's check read only the frozen copy.*
   * **It fills holes at covered levels and seasons.** For each tour, level and season it touches, on today's tables,
     either of these:
     * the cell already holds at least half of it: a box score for at least half of its played matches (for box scores
       it completes), or at least as many matches as it adds (for new matches);
     * **or the fill brings the cell closer to its level's other seasons:** its share of matches with a box score moves
       nearer the median share of the same tour and level over the other seasons from 2013 (seasons with at least 30
       played matches). *Added at the owner's word the same day.* A season with a hole catches up with its neighbours;
       a level empty in most seasons (ITF before 2025, women's ITF qualifying) has a median near 0, so its fills still
       fail and stay tested candidates.
   * `src/eda/tennislive_box_fill/conditions.py` reads both on a built candidate.
   * **What the package records:** both conditions' numbers, per cell, in its README or manifest. The session that
     registers it says so in its report to the owner.
2. **Tested first, as before** (a `--candidate` build compared with `compare.py`, the input check read first):
   * data that fails either condition;
   * a level or seasons the history does not cover, such as ITF box scores before 2025. They would take a level from
     none to nearly all in a few seasons, the shift in the rating inputs' scale that the freeze of 8 October was made
     for (finding #6 of the [input-data audit](../studies/input_data_audit/README.md));
   * a level Stage 0 never held, such as men's ITF qualifying;
   * another source's revision of a box score the history already holds.

   A tested candidate is then decided by its kind ([adoption by kind of change](2026-10-09-adoption-by-change-class.md)).
3. **Unchanged:**
   * the frozen reference of 8 October stays the yardstick;
   * `history.py` lists every difference (a registered package's matches as "accepted"), and `run_chain.py --setup`
     still refuses a template build for lower-level changes nothing accepted;
   * Tennis My Life's own lower-level changes enter by themselves ([13 Oct](2026-10-13-tml-lower-level-revisions.md));
   * the weekly lower-level feed and its own rules ([13 Oct](2026-10-13-lower-level-feed.md));
   * main-tour data is a repair, decided on its evidence ([9 Oct](2026-10-08-current-best-model.md)).
4. **Each rebuild's harm check covers what entered since.** The check compares both stages; harm means worse by more
   than 0.10 mLL with the whole 95% interval below 0. The readings are pooled as repairs.
5. **The first packages under it: TennisLive's box scores** (`tennislive_box_fill`, 233; and
   `tennislive_box_fill_men_gsq`, 184, added at the owner's word the same day; below). *Then, on 16 Oct 2026 at the
   owner's word, the men's lower-level results (`men_lower_level_fill`, 4,376; below).*

## The TennisLive package

**In use from 14 Oct 2026, 09:59 PDT:** `tennislive_box_fill` is listed in `accepted.json`'s "packages"
(`data/studies/current_best_model/accepted_additions/tennislive_box_fill/`). Every template build
(`run_chain.py --additions`) and every bet-day run merges it, before the feed. It is in training from the next rebuild,
with no retrain for it alone.

* **What it holds:** 233 box scores, from TennisLive's match-page statistics, for lower-level matches the history
  holds as results only. No match is added, and no fact of a match changes.
  * By tour and level: men's Challengers 61, Challenger qualifying 20, tour qualifying 2; women's Slam qualifying 142
    (Roland Garros and Wimbledon 2018: 139), tour qualifying 5, WTA 125 and its qualifying 3.
  * By season: 2015 2, 2018 155, 2019 38, 2020 12, 2021 7, 2022 16, 2023 1, 2024 2.
  * TennisLive gives no service-games count, so these are kept as box scores without one (`no_svgms`), which Stage 0
    already accepts.
* **How it was built** (the level-evidence builder, the weekly feed's route):
  * candidate `TLB20261014`: TennisLive's pages only, ITF and ITF qualifying left out as in the feed, against the
    frozen reference;
  * its checks: every reference match and fact unchanged, box columns changed only where a completion applied, no
    duplicate, history "dropped 0, future 0";
  * the feed's identity screen: 19 of 20 sampled links right; the other is one player under her married name
    (Rüffer, Papadakis);
  * then derived as `TLB20261014_pkg`, with men's Slam qualifying kept as results only (below).
* **The conditions** (fixed before the candidate was built; `data/studies/tennislive_box_fill/`):
  * **It counts the same way.** Measured on the builder's own links against the frozen history, all eight counts it
    gives equal:
    * men's Challengers 99.87% (17,013 matches), Challenger qualifying 99.99% (6,746), tour qualifying 99.91% (2,294);
    * women's WTA 125 100% (229), its qualifying 100% (109), Slam qualifying 98.87% (796), tour qualifying 99.94%
      (1,778).
    * **Men's Slam qualifying fails: 95.26% (844).** The differences sit in Roland Garros 2022–2026, whose frozen rows
      carry the known error the Roland Garros repair replaced (second serves booked as first serves). Against today's
      tables, with that repair, it reads 99.64%.
  * **It fills holes at covered levels and seasons.** Every cell in the package passes. The narrowest are women's
    Slam qualifying 2018 (54% of matches with a box score before, 92% after) and men's tour qualifying 2015 (53%).
    **Men's Slam qualifying 2018 fails: 49% before.**
  * Men's Slam qualifying is therefore left out: 184 box scores, 183 of them for Roland Garros and Wimbledon 2018
    qualifying, which the history holds without any box score. They wait for a candidate test or the owner's word;
    Claude recommends adding them (the [report](../studies/tennislive_box_fill/README.md)). *Added the same day, at the
    owner's word, as the second package (next section).*
* **Checked by hand and by rule:**
  * 30 completions drawn at random were all the same match in both records: players, event, round and score;
  * on all 233, each player's counts sit on that player's side, re-derived from the names alone;
  * the winners agree on 232. The other is the 2018 Chengdu Challenger final (Ze Zhang beat Henri Laaksonen 2-6 5-2,
    retired), where TennisLive's winner field names the other player. Stage 0's result stands, and the box score is
    placed by name.
* **The merge:**
  * on the frozen reference's tables, the package gives the candidate's own tables (`additions.py --check-against`:
    matches, players and timeline equal);
  * on today's tables, read-only, 231 of the 233 apply. Two Roland Garros matches already have RG's own box score
    from its repair, and the merge skips them. The feed merges exactly as before;
  * after registration, `history.py` on the candidate reads "accepted 233 (completions 233) … the template may be
    built".
* **Reach:**
  * 1,229 of the frame's 67,226 main-tour matches (1.8%) have a player whose previous 365 days gain a box score, and
    169 within 28 days. Most are women's 2018–2019 (912 and 140).
  * No match of 2025 or 2026 gains one, so today's bets move only through the long-memory inputs, if at all.
* **The cost on bet days:** the daily engine's checkpoints hash the history they read, so the families that read old
  box scores are recomputed. That adds about four minutes a run until a run leaves a checkpoint on the new tables,
  which happens automatically from the week whose checkpoint day has none yet.

## The second package: men's Slam qualifying

**At the owner's word ("Yes add and fix those"), 14 Oct 2026:** `tennislive_box_fill_men_gsq`
(`data/studies/current_best_model/accepted_additions/tennislive_box_fill_men_gsq/`), listed in `accepted.json` after
the first package, **in use from 14 Oct 2026, 12:32 PDT.** After registration `history.py` on its candidate reads
"accepted 184 (completions 184) … the template may be built".

* **What it holds:** 184 box scores from TennisLive's statistics. 183 are for men's 2018 qualifying at Roland Garros (88)
  and Wimbledon (95), which the history holds without any box score. The other is one Roland Garros 2022 match that
  today's tables already score from RG's own record, so the merge skips it. 183 land on today's tables.
* **How it was built:** derived from the same candidate (`TLB20261014_mgsq`: men's Slam qualifying only), with its
  checks passed, its READY marker, the identity screen carried over from the parent, `--check-against` passed, and
  the read-only merge on today's tables (the report).
* **The fixed conditions** (`data/studies/tennislive_box_fill/men_gsq/`):
  * agreement on today's tables: men's Slam qualifying 99.65% (845 matches both score). On the frozen copy it is
    95.26%, where Roland Garros 2022–2026 still has the error the repair fixed;
  * coverage: 2018 holds a box score for 49% of its played matches before and 90% after, against the level's median of
    99.8% over the other seasons, so the fill brings it closer.
  * The whole candidate, re-read under the fixed conditions: all 417 completions of both packages pass
    (`data/studies/tennislive_box_fill/parent_fixed/`).
* **Checked:** 30 drawn at random were all the same match in both records (players, event, round, score). On all 184,
  each player's counts sit on that player's side, and the winners agree on every one.
* **Reach:** 913 of the frame's 67,226 main-tour matches have a player whose previous 365 days gain a box score, almost
  all men's of 2018 (323) and 2019 (582); 123 within 28 days, all 2018. No match of 2025 or 2026 gains one.

## The third package: the men's lower-level results

**At the owner's word, 16 Oct 2026** ("Add the men's 4,246 matches now"): `men_lower_level_fill`
(`data/studies/current_best_model/accepted_additions/men_lower_level_fill/`), listed in `accepted.json` after the two
TennisLive packages, **in use from 16 Oct 2026, 14:25 PDT.** After registration `history.py` on its candidate reads
"accepted 4,376 … the template may be built". Report: [men's lower-level fill](../studies/men_lower_level_fill/README.md).

* **What it holds:** 4,376 men's lower-level results, without box scores, from TennisLive, the ITF's live scores and
  SofaScore, dated where the weekly feed does not reach: Challengers and their qualifying to 31 Dec 2025, ITF main draws
  to 31 May 2026 (the feed covers men's Challenger levels from 1 Jan 2026 and men's ITF from 1 Jun 2026).
  * **On today's tables 4,345 land:** ITF 3,372, Challenger qualifying 953, Challengers 20. The other 31, all
    Challengers, are already held, and the merge skips them.
  * By season (played matches landing): 2017 3, 2018 951, 2019 232, 2020 73, 2021 187, 2022 164, 2023 207, 2024 263,
    2025 1,875 (ITF 1,742), 2026 389.
  * The level layer weighs them as it weighs these levels already: Challenger results in full, Challenger-qualifying
    results capped at full weight, ITF results at a quarter; workload counts take every match.
  * The owner's 4,246 was the morning's count, on the 10 Oct candidate. It treated two players meeting at the same
    level within ±10 days as one match, which would drop 124 of today's matches (ITF 122, Challenger qualifying 2): all
    rematches a week apart at venues with back-to-back weekly events (below). Under that rule today's build gives
    4,221, 25 fewer than the 10 Oct candidate.
* **The conditions** (`data/studies/men_lower_level_fill/package/`):
  * *It counts the same way* does not apply: no box score enters.
  * *It fills holes:* all 19 tour, level and season cells pass by the first branch, each already holding at least as
    many played matches as it gains. The narrowest are Challenger qualifying 2019 (271 held, 24 added) and 2020 (394
    and 17); the largest addition, ITF 2025, adds 1,742 to 17,870.
  * Read on today's tables as builds merge them, with the package in its registered place
    (`src/eda/men_lower_level_fill/conditions_new.py`; `conditions.py` reads box-score completions only).
* **How it was built** (the level-evidence builder, the feed's route):
  * candidate `MLF20261016` from the day's downloads, against the frozen reference, its checks passed;
  * the feed's identity screen: at most 5% unsure links per source;
  * the 20 sampled identity-repair moves checked by hand. All are the same person; two are plausible but not certain
    (Junhyun/Junhyeon Lee, Korea; Mohammed/Mhamed Affes, Tunisia, one match each);
  * derived as `MLF20261016_pkg` (men, the dates above, results only), with its checks passed and READY;
  * `--check-against` passed (matches, players and timeline equal).
* **Duplicates, looked for beyond the merge's guard:** 167 added matches whose two players also meet in today's tables
  within 14 days, at any round or level.
  * Every one is 7 or 14 days apart: rematches at venues that hold back-to-back weekly events. 166 have a different
    score.
  * The 3 with the same score are separate events. In the two same-venue cases (Tabarka 2019, Maanshan 2026) the held
    tables have no match of either player in the added week, and every other round's opponent differs.
* **The rebuild and its harm check:** `template_2026-10-16` on the day's tables with every accepted package and the
  feed, compared with `template_2026-10-14` (the rule of point 4; it covers everything that entered since that instance
  was built).
  * **No harm:** both tours, both stages, 2020–2026, 31,722 matches: +0.007 mLL [−0.025, +0.039], unresolved, P(better)
    0.66.
  * The input check's one new flag (men's `elo_surf_offset`, 2023) comes from the offset's K being re-tuned on
    2013–2018, as every build does. The men's choice moved to another grid point.
  * **In training from 16 Oct 2026, 17:58 PDT,** when the daily runs switched to `template_2026-10-16`. The switch's
    replay check passed: 42 of 57 inputs bit for bit, the largest difference 4.4e-6.

## Implemented

* **The rules:**
  * CLAUDE.md's training-data bullets;
  * the [decisions index](README.md);
  * notes in the [8 Oct](2026-10-08-current-best-model.md) and [13 Oct](2026-10-13-tml-lower-level-revisions.md)
    records.
* **The conditions:** `src/eda/tennislive_box_fill/conditions.py` reads them on a built candidate, with the
  independent side check and the hand-check sample. Tests: `test/tennislive_box_fill/test_conditions.py`.
* **Two fixes the first box-only package needed** (neither changes a candidate that adds matches):
  * `candidate_stage0.py` writes an empty additions table with its columns when a candidate adds no match
    (`empty_additions`). Its checks had stopped on a table without columns.
    Test: `test_a_candidate_without_new_matches_writes_additions_the_checks_can_read`.
  * `data_gaps_2026/feed.py`'s rule screen skips an empty identity sample (`_sample`). Test:
    `test/data_gaps_2026/test_feed.py`.
* **The package:** `additions.py --package` from `TLB20261014_pkg`; `--check-against` passed; `--register`.
  * The candidates, about 100 MB each, are in `C:/Users/zerom/tnr_tl_box/candidates/`, outside `data/studies`, as the
    feed's are.
  * The evidence is in `data/studies/tennislive_box_fill/`.

## To undo

* **The package:** remove `tennislive_box_fill` from `accepted.json`'s "packages". Builds and live runs then merge
  only the other packages and the feed. The same for `tennislive_box_fill_men_gsq` and `men_lower_level_fill`.
* **The policy:** restore the CLAUDE.md bullets of 13 October (git history), and treat lower-level data from other
  sources as candidates again. Packages registered under this decision stay listed until each is removed.
