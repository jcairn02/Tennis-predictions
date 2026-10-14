# The levels the history lost in 2026 come back, and a weekly feed keeps them current

**Requested by the owner on 13 October 2026,** after reading that the unpriced-leads adjustment could only partly run
because of 2026 data gaps (box scores at every level down sharply from mid-2026; women's ITF qualifying missing since
2025 and most lower-level events since June 2026; live doubles and start times), and that adding the lower-level data
"needs your OK". The owner's words:

> "I was told for the best tabpfn3.5 model that there are 2026 data gaps. Identify WHY these exist and fix them.
> Download all this data we need. If we have the data on disk, integrate it. Make sure our pipeline is set up to
> automatically integrate this so this doesnt happen again."

Read by Claude as the acceptance the summary asked for, on the condition the owner set for the same kind of data on
10 Oct: **adopted unless the harm check fails**. Carried out and recorded by Claude
([report](../studies/data_gaps_2026/README.md), [process log](../studies/data_gaps_2026/process_log.md)).

## Why the gaps exist

* **Sackmann's files ended in early June 2026** (main tour to 25 May, lower levels to 1–2 June). Since then Stage 0
  takes new results only from Tennis My Life, which publishes the ATP main tour and qualifying, ATP Challenger main
  draws and the WTA main tour, and **no ITF, no women's qualifying, no WTA 125 and no men's Challenger qualifying.**
* **Sackmann's own women's file had already dropped ITF qualifying with the 2025 season** (16,685 qualifying rounds at
  ITF events in 2024, none in 2025 or 2026).
* **The replacements were downloaded but never wired in.** The WTA API, the WTA website's records, TennisLive's
  listings, the ITF live-data API, SofaScore and TDI are on disk; Stage 0 reads only Sackmann and Tennis My Life, and
  the freeze of 8–9 Oct lets lower-level data in only as an accepted package. One package was accepted (men's 2026
  Challenger data, 10 Oct), as a one-off to 5 Oct.
* **Nothing compared coverage with the year before,** so a lost level went unseen for four months.
* **Roland Garros 2026's main draws have no box scores** (127 matches a tour): Tennis My Life has none, and the decided
  repair that takes them from RG's own record (9–10 Oct) waits to be applied.

## Decision

1. **A lower-level feed** (`lower_level_feed`): a package rebuilt from the newest downloads, as dated snapshots
   (`data/studies/current_best_model/accepted_additions/lower_level_feed/<date>/`), named in `accepted.json`'s "feeds".
   Every build (`run_chain.py --additions`) and every prediction run merges the current snapshot after the listed
   packages (`additions.py`). The repository's own Stage 0 is never changed.
2. **Its scope: the levels a feed lost, from the last week the frozen reference holds of each** (inclusive):
   men's Challenger and Challenger qualifying of 2026 (the 10 Oct package's scope; Challenger main draws only to
   5 Oct, Tennis My Life carries them after), men's ITF from 1 Jun 2026; women's ITF, WTA 125 and its qualifying from
   1 Jun 2026, tour qualifying from 18 May 2026, Slam qualifying from 19 Jan 2026, ITF qualifying from 16 Dec 2024.
   Men's ITF qualifying stays out (Stage 0 never held it).
3. **Its sources** (the level-evidence study's candidate builder, `candidate_stage0.py`, every match linked to Stage 0's
   players and timed by its rules): results from the WTA API, the WTA website's records and the WTA API's player pages,
   TennisLive's listings, the ITF live-data API and SofaScore; **box scores only from sources that count as Stage 0
   does**: the WTA API (99–100% equal at WTA 125 and qualifying), the ITF live-data API, TDI (99.8–100% on its published
   counts; its first-serve split counted from its point files) and TennisLive's pages at Challengers and qualifying
   (100% equal there). SofaScore's box scores stay out (43–92%), and so do TennisLive's at ITF (in 15% of matches they
   miss points: serve points 1.8 lower on average). **Results only** for women's ITF qualifying (no box score in any
   season of the history) and women's Slam qualifying (the WTA API's Slam box scores agree with Stage 0's on 4–37% of
   counts).
4. **It runs every week, by itself** (the Windows task "Tennis predictions - lower-level feed", daily at 12:00;
   `src/ingest/scheduled.py --weekly`): TennisLive every day (the last complete week and the week in progress up to
   yesterday); on Wednesdays the WTA API's last five weeks, then the feed
   (`src/eda/data_gaps_2026/feed.py --run --auto --advance`): the candidate, its checks, a rule screen of the identity
   samples in place of the hand check, the scope, the snapshot, and the check that merging it reproduces the candidate.
   **A snapshot that passes every step becomes current** (the policy of this decision); one that fails keeps the
   previous snapshot and raises a notification. (Another session's jobs share the task: the WTA API's per-match
   documents on Mondays, the WTA website's records on Tuesdays.)
5. **A coverage alarm** (`src/eda/data_gaps_2026/coverage.py`, Wednesdays after the feed): matches and box scores by
   tour, level and month, with every package and the feed merged, against the larger of the same months one and two
   years earlier, each measure against its own baseline; a level that falls below 70% raises a notification when it
   first does and every four weeks while it lasts. Known holes are acknowledged by name, month and an end date
   (`coverage.KNOWN`): women's Slam-qualifying box scores (results only by this decision), and ITF box scores of June
   to September 2026, which no source counts as Stage 0 does (until 31 Jan 2027, monthly cells only).
6. **The 10 Oct package** (`men_2026_ch_chq`) is retired once the feed's current snapshot holds every match it added
   (`additions.py --retire`, refused otherwise): the feed carries the same matches, with TDI's box scores.

## Evidence

* **Classified before any result:** a repair (levels the history held until a feed was lost), entering by the route
  the level-evidence study's evidence supports; the comparison is a harm check.
* **The harm check** (fixed before any build or reading; process log, § 3 addendum): the template on the frozen
  reference's tables plus the first snapshot's additions, against the current instance (`template_2026-10-10`), both
  stages, both tours, seasons 2025–2026, seeds 0–3 paired; harm = worse by more than 0.10 mLL with the whole 95%
  interval below 0.
* **The gate first** (passed): on the 60,412 matches the additions cannot reach, every input equals the current
  instance's bit for bit, except the joint solves' (at most 1.4e-11 apart; the tolerance is 1e-7). So the chain code
  changed since 10 Oct moves nothing there.
* **Result, read once at 20:28 on 13 Oct (+ = with the feed better):** 9,457 matches, **+0.044 mLL per match
  [−0.097, +0.185], P(better) 0.74, unresolved. No harm, so adopted.**
  * Not deciding: men +0.016 [−0.005, +0.038]; women +0.073 [−0.214, +0.359]; 2025 +0.017, 2026 +0.076.
  * The reading's half-width (0.14) is wider than any plausible effect of a repair, so it is a harm check, not evidence
    of a gain, and it earns no edge credit.
* **In use from 13 Oct 2026, 20:31:** the snapshot `lower_level_feed/20261013c` is named in `accepted.json`, and
  `men_2026_ch_chq` is retired. The instance built in the check is the current one
  (`data/studies/current_best_model/template_2026-10-13/`); the daily pipeline was pointed at it the same evening.

## To undo

Remove `lower_level_feed` from `accepted.json`'s "feeds" (and put `men_2026_ch_chq` back in "packages" from "retired");
disable the weekly task. Builds then merge only the listed packages.
