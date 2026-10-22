# The 2026 data gaps: why they happened, what is fixed, and how the pipeline keeps them closed

13 Oct 2026 · For the owner · [Process log](process_log.md) (the audit trail) · [Decision](../../decisions/2026-10-13-lower-level-feed.md)

## 1. The short answer

**You asked:** why the best TabPFN-3.5 model has 2026 data gaps; fix them; download what is missing; connect what is
already on disk; and make the pipeline do this by itself so it cannot happen again.

**Why the gaps exist.** Four causes, all found in the data and the code:
1. **The main match source stopped in early June 2026.** The model's match history (called "Stage 0" in the code: one
   table of every match the model learns from) was built from Jeff Sackmann's files plus Tennis My Life. Sackmann's
   files ended on 25 May (main tour) and 1–2 June (lower levels). Since then new matches come only from Tennis My Life,
   which publishes the ATP and WTA main tours, ATP qualifying and ATP Challenger main draws, and **nothing else: no ITF,
   no WTA 125, no women's qualifying, no men's Challenger qualifying.**
2. **Women's ITF qualifying had already gone in January 2025,** inside Sackmann's own file: 16,685 qualifying rounds at
   ITF events in 2024, none in 2025 or 2026.
3. **The replacement data was downloaded, but never connected.** Other sessions collected the WTA's own data, TennisLive,
   the ITF's live data, TDI (the ATP's data company) and SofaScore. But the match table reads only Sackmann and Tennis
   My Life, and the 8–9 Oct rule lets lower-level data in only as a separately accepted "package". One package was
   accepted (men's 2026 Challenger data, 10 Oct), as a one-off to 5 Oct.
4. **Nothing watched coverage against the year before,** so a lost level went unnoticed for four months.

Plus one main-tour hole: **Roland Garros 2026 has no match statistics for either tour's main draw** (254 matches).
Tennis My Life has none, and the repair you approved on 10 Oct (taking them from Roland Garros's own records) was never
applied: it was waiting for another job to finish, and then nobody ran it.

**What is fixed.**
* **The missing lower levels are back in the model:** 48,572 matches from the WTA's own data, TennisLive, the ITF's
  live data and TDI. Every level that had dropped out is back to roughly last year's match count.
  * Box scores are back everywhere except ITF events between 1 June and 14 September, where no source counts the way
    the history does.
  * Women's ITF qualifying and women's Slam qualifying enter as results only, by design (§ 4).
* **It passed its harm check:** +0.044 per match on the log-loss scale (in thousandths), within a 95% range of −0.097
  to +0.185; positive means better. That is unresolved, with a 74% chance of being better, and far from the harm line.
  So it was adopted on your rule.
* **The Roland Garros repair you adopted on 10 Oct is applied.** It fills Roland Garros 2026's 254 main-draw matches
  that had no statistics, and corrects 2022–2025 and the Australian Open's service games.
* **The model in use since 14 Oct, 09:10, carries all of it:** `template_2026-10-14`, built on the day's tables with
  the new data, the Roland Garros repair, and Tennis My Life's corrections that another session accepted yesterday.
  * It passed the notebook's readiness checks.
  * In its replay test, 18 of 23 matches gave inputs identical to the model's own. The 5 others (all men's) differ by at
    most 0.0000045, for a reason explained in § 7, item 7. Every women's match was identical.
  * From 13 Oct 20:41 until then, a bridge model carried the new data alone (`template_2026-10-13`).

**What keeps it fixed.** A second daily Windows task collects the new data, rebuilds and checks the feed every
Wednesday, and switches to the new week's data only when every check passes. A weekly coverage alarm compares every
tour and level with one and two years earlier and notifies you if one drops (§ 5).

**What still needs you** (§ 7, each with my recommendation):
* two small box-score repairs I recommend: Nottingham and Berlin 2026, and women's Slam qualifying from the Slams' own
  records;
* one hole I recommend accepting: women's ITF box scores, June to mid-September 2026;
* one fix to the level layer's re-centring rule, so that bet-day inputs equal training inputs exactly again;
* one tightening of the builder's partial-name matching;
* one fix to how jobs share the graphics card, which can otherwise stall a bet day, and 45 minutes of evaluation fits to
  run when you're not betting;
* when you re-issue the unpriced-leads registration, its completeness check should read a build's tables, not the
  repository's.

## 2. The gaps, measured

The model's match history today (the reference tables of 8 Oct rebuilt from today's Tennis My Life files, plus the
accepted men's package), June–September of each year. "Stats" = matches with a box score (aces, double faults, serve
points, first serves in and won, second serves won, service games, break points).

| Tour | Level | 2025 matches (with stats) | 2026 matches (with stats) |
|---|---|---:|---:|
| Men | ITF | 8,087 (7,603) | 393 (391), all in the first week of June |
| Men | Challenger qualifying | 1,431 (1,422) | 1,665 (**116**): results from the 10 Oct package, almost no stats |
| Men | Challenger main draw | 2,576 (2,551) | 2,904 (2,894): fine |
| Women | ITF | 7,932 (7,480) | 427 (424) |
| Women | WTA 125 | 775 (767) | 93 (93) |
| Women | WTA 125 qualifying | 198 (197) | 18 (18) |
| Women | Tour qualifying | 310 (309) | **0** |
| Women | Slam qualifying | 224 (224) | **0** (none since the 2026 Australian Open) |
| Women | ITF qualifying | 0 since January 2025 | 0 (16,684 in all of 2024) |
| Both | Roland Garros 2026 main draw | – | 254 matches, **0 stats** |

These are the gaps the earlier summary described: in July, matches with stats were 40% of the year before for men and
19% for women (this report's check reproduces those exact figures).

## 3. Why each gap exists (the evidence)

* **Sackmann's files ended.** His GitHub repositories have answered "not found" since June 2026; the project's copy is
  a mirror whose last data are the week of 25 May (main tour) and 1–2 June (lower levels). The match-table builder
  reads only two sources: those files and Tennis My Life (`stage0_build.py`, its source list). Every lower level in
  the table stops in the first week of June 2026.
* **Tennis My Life never carried those levels.** Its files are the ATP main tour, ATP qualifying, ATP Challenger main
  draws, the WTA main tour and its in-progress events. An earlier study (data continuity, 6 Oct) measured the loss and
  proposed filling women's qualifying and WTA 125 from the WTA's own data; that proposal waited for a decision.
* **Women's ITF qualifying stopped earlier, inside Sackmann's own file.** His women's file of 2024 holds 16,685
  qualifying rounds at ITF events; those of 2025 and 2026 hold none (tour qualifying is still there). So the table has
  had no women's ITF qualifying since January 2025.
* **The data to fill the gaps was downloaded but never connected.** On disk: the WTA's own data (WTA 125, qualifying and
  Slam qualifying, with box scores), the WTA website's records and its player pages (every women's result, ITF and
  qualifying included), TennisLive's listings (every level, both tours), the ITF's live data (every ITF match since
  15 Sep, with box scores), TDI (men's Challengers since late June, with box scores) and SofaScore. A builder that turns
  them into match-table rows exists (written for the lower-level study on 9 Oct), but the rule of 8–9 Oct lets
  lower-level data into the model only as a package you accept, and only one was: men's 2026 Challenger results to
  5 Oct (10 Oct), a one-off with no way to keep it current.
* **Nothing compared coverage with the year before.** The only source watch checked whether sources still exist, not
  how many matches arrive, so four months passed before three studies noticed the gap by chance.
* **Roland Garros 2026.** Tennis My Life has no box scores for it. Roland Garros's own statistics are on disk, and you
  adopted the repair that uses them on 10 Oct, to be applied "after the level-layer work". That work finished the same
  day; the repair was never applied.
* **Smaller holes found on the way:** the women's grass events of Nottingham and Berlin 2026 (58 matches) have no box
  scores, because Tennis My Life's are incomplete and the match table's checks blank them; and Tennis My Life's
  Challenger files of 2022–2025 have been held for review since 10 Oct (the daily download alerts about it), a separate
  matter of past seasons' revisions.

## 4. What was done

**Downloads.** Almost everything needed was already on disk or being downloaded: another session was collecting the
WTA's newest data (its WTA 125, qualifying and player pages) and SofaScore's ITF records while I worked, so I did not
touch those sites. TennisLive had not been collected since 4 Oct; I fetched its last two complete weeks (37 requests, no
refusal). Nothing else that counts the way the history counts was missing (see § 7 for what no source can fill).

**Connecting what is on disk: the lower-level feed.**
* The builder written for the lower-level study (it links each source's matches to the players the match table already
  knows, drops duplicates, and dates each match cautiously) was extended with three sources and two rules:
  * the WTA's own player pages, for women's 2026 results the website copy lacks;
  * TDI, for men's Challenger box scores since late June;
  * box scores only from sources that count the way the history counts (§ 2's table of agreement); results only where
    the history never had box scores (women's ITF qualifying) or the only source counts differently (women's Slam
    qualifying);
  * a scope rule: only the levels that were lost, each from the week it was lost.
* **The first snapshot (13 Oct): 48,572 matches the history lacked, 5,743 of them with box scores.** Before they
  went in, the matches the builder links to known players were hand-checked on samples by a separate agent:
  140 of 140 links were right, 215 of 228 players were right (9 wrong, 4 unsure), and 51 of 60 new players were right.
  The errors come from two routes that resolve only a few dozen of the 48,572 matches. They are listed in § 7 as
  builder fixes.

  | Tour | Level | Matches added | With box scores | From |
  |---|---|---:|---:|---|
  | Men | ITF (from 1 June) | 8,000 | 1,443 | TennisLive and the ITF's live data (box scores from 15 Sep) |
  | Men | Challenger qualifying (2026) | 1,763 | 1,291 | TennisLive; box scores from TDI |
  | Men | Challenger main draw (Sep–Oct, matches the history lacked) | 75 | 64 | TDI |
  | Women | ITF (from 1 June) | 7,201 | 1,392 | the WTA's records and TennisLive; box scores from the ITF's live data (from 15 Sep) |
  | Women | ITF qualifying (from Dec 2024) | 29,600 | 0 (results only) | the WTA's records and TennisLive |
  | Women | WTA 125 (from 1 June) | 925 | 893 | the WTA's own data |
  | Women | WTA 125 qualifying | 313 | 301 | the WTA's own data |
  | Women | Tour qualifying (from 18 May) | 359 | 359 | the WTA's own data |
  | Women | Slam qualifying (Roland Garros, Wimbledon, US Open 2026) | 336 | 0 (results only) | the WTA's own data |

* **The same table as § 2, June–September, after the snapshot** (the box-score figures in brackets):

  | Tour | Level | 2025 | 2026 before | 2026 after |
  |---|---|---:|---:|---:|
  | Men | ITF | 8,087 (7,603) | 393 (391) | 7,984 (1,452) |
  | Men | Challenger qualifying | 1,431 (1,422) | 1,665 (116) | 1,665 (1,307) |
  | Women | ITF | 7,932 (7,480) | 427 (424) | 7,073 (1,305) |
  | Women | WTA 125 | 775 (767) | 93 (93) | 911 (881) |
  | Women | WTA 125 qualifying | 198 (197) | 18 (18) | 271 (259) |
  | Women | Tour qualifying | 310 (309) | 0 | 335 (335) |
  | Women | Slam qualifying | 224 (224) | 0 | 224 (results only) |
  | Women | ITF qualifying | 0 (gone since Jan 2025) | 0 | 6,072 (results only) |
  | Men | All levels | 13,664 (13,024) | 6,536 (4,934) | 14,127 (7,186) |
  | Women | All levels | 10,443 (9,943) | 1,588 (1,515) | 15,936 (3,760) |

  Every lost level's match count is back to roughly last year's. Box scores are back at every level except ITF
  between 1 June and 14 September. There, no source counts the way the history does (§ 7, item 4), so the all-level
  box-score totals stay below last year's for those months. In the last four weeks (13 Sep – 10 Oct), every level is
  at 84–148% of the larger of the same weeks one and two years earlier, box scores included. The coverage alarm finds
  59 problems before the snapshot and none after: the ITF months are acknowledged (§ 5).

**The check that it does no harm.** It was fixed in writing before anything was built, and uses the same rule you
chose for the men's Challenger data on 10 Oct.
* **What was compared:** the model built with the snapshot, against the model in use (`template_2026-10-10`).
* **On what:** every main-tour match of 2025 and 2026 (9,457), both tours, both stages of the model, seeds 0–3.
* **The rule:** it would be harm if worse by more than 0.10 per match, with the whole 95% range below zero.
* **First, a consistency check (passed):** on the 60,412 matches the new data cannot reach, every input of the two
  models is identical. The only exception is the jointly solved ratings, which differ by at most 0.00000000001. So
  nothing else changed between the two builds.
* **The result:**

  | Group | Change per match (+ = better) | 95% range | Chance it is better |
  |---|---:|---|---:|
  | **Both tours (decides)** | **+0.044** | −0.097 to +0.185 | 74% |
  | Men | +0.016 | −0.005 to +0.038 | 94% |
  | Women | +0.073 | −0.214 to +0.359 | 70% |
  | 2025 only | +0.017 | −0.024 to +0.058 | 82% |
  | 2026 only | +0.076 | −0.257 to +0.408 | 69% |

  None of these resolve. The range is far wider than anything a data repair could plausibly move, so this check
  guards against harm. It is not evidence of a gain, and it earns no credit toward betting edge.

**What this changes for the model.** A main-tour match is "touched" when one of its players has a match added by the
snapshot in the year before it. That is the reach of the "coming up from lower levels" inputs and the players' forms.
* **Women:** 38% of 2026's main-tour matches are touched: 53% in June, 86% in July, 71% in August and 97% in September
  (11–16% from January to May, through ITF qualifying). In 2025: 10%.
* **Men:** 4% of 2026's matches are touched: 4–19% a month from June, none before (the 10 Oct package already held
  the Challengers).

So the women's inputs change the most. That matches the summary you were given ("off for about 70% of women's
matches").

**Putting it into use (13 Oct, evening).**
* The snapshot was registered, so every build and bet day now merges it. The 10 Oct men's package was retired: the
  feed holds all 1,735 of its matches, one of them filed under another source's id for a player new to the history.
* The model built for the harm check became the model in use (`template_2026-10-13`). It passed the notebook's five
  readiness checks.
* **The replay test:** 19 of the 23 replayed matches gave inputs identical to the model's own. The other 4 (all men's)
  differ by at most 0.0000044, from the layer's re-centring rule (§ 7, item 7). All 8 women's matches, where the new
  data changes most, were identical.

**The Roland Garros repair (adopted by you on 10 Oct; applied tonight).**
* Its tables went in at 21:12, and the match table was rebuilt in the coordinated way its decision asks (21:12–21:48).
* That rebuild also carries Tennis My Life's checked corrections (the other session's work, decided today).
* The history check is clean: 2,964 Slam matches repaired as decided, 104 Tennis My Life corrections, 9 main-tour
  record changes (Davis Cup, Laver Cup, one Båstad match), and nothing blocked.
* Because the repair changes past box scores, the model was rebuilt on today's tables with everything in
  (`template_2026-10-14`, in use since 14 Oct 09:10). The session building it ended at 00:30 and stopped the build one
  step from the end. It was resumed from that step at 07:01, so nothing was rebuilt twice.
* **Its comparison with the 8 Oct reference** (2020–2024, the standard check after a batch of changes): +0.014 per
  match, 95% range −0.336 to +0.365, unresolved. The range is wide because the odds input changed since 8 Oct.
* **Its input check** flags 19 inputs as moving unevenly across seasons, the warning sign the project watches for.
  Each one comes from a change already decided:
  * 11 were already in the 10 Oct model you adopted;
  * the new data adds women's 2026 surface layoffs (shorter, now that their lower-level matches are visible);
  * the Roland Garros repair adds women's 2013–2014 hold and break inputs (service games that were blank and are now
    filled, the effect its 10 Oct check recorded) and women's 2026 forms (Roland Garros 2026's statistics).
* **Its replay test:** 18 of 23 matches identical; 5 men's within 0.0000045 (§ 7, item 7).

## 5. Keeping it closed

**A second Windows task, "Tennis predictions - lower-level feed",** runs every day at 12:00 (the 07:30 task is
unchanged). Nothing needs you unless something fails; then one Windows notification says what.

| When | Job | What it does |
|---|---|---|
| Every day | TennisLive | Lists the last complete week and the week in progress up to yesterday: every level's results, the doubles, and the start and finish times TennisLive keeps for only about a month |
| Wednesdays | WTA | The WTA's own match lists and box scores of the last five weeks (WTA 125, qualifying, Slams) |
| Wednesdays | Feed | Rebuilds the lower-level additions from every source, checks them, keeps only the lost levels, and writes a dated snapshot. If every check passes, the snapshot becomes the one every build and bet-day run merges; if one fails, last week's stays in use and you get a notification |
| Wednesdays | Coverage alarm | Counts matches and box scores by tour, level and month, with the feed merged, against the larger of the same months one and two years earlier. A level that drops below 70% notifies you when it first does and every four weeks while it lasts |

**What the alarm cannot do by itself:** add a newly lost level to the model. The feed covers only the levels lost in
2026, each from the week it was lost (one line per level in the feed's driver). If the alarm reports another level,
for example if Tennis My Life stopped publishing the men's Challengers, adding that level is a change to what the
model learns from. So it gets the same harm check as this one before it enters. The alarm makes sure you hear about it
within a week.

**Why the alarm compares with two years earlier too:** a level lost for over a year compares zero with zero against the
year before and goes quiet. That is how women's ITF qualifying stayed invisible since January 2025. Against two years
earlier it shows (today: 0 in the last four weeks against 1,292).

**Bet days.** Every prediction run already merges the accepted packages; it now merges the feed's current snapshot
too, without any change to the daily pipeline. The notebook's morning cell (A1) prints the feed's snapshot and any
coverage alarm, and a new cell (B8) runs the feed by hand. The first bet day after a Wednesday update can take longer.
A new snapshot can also re-file a few older lower-level matches, for example when the WTA's records take over a match
TennisLive supplied. The daily engine then recomputes the input families whose history changed instead of resuming
them from its saved state, and saves a new state for the next run. The model itself is not retrained: the new weeks
enter its inputs at once, and its training rows at the next rebuild, as Tennis My Life's new matches do.

**Guards I added because I broke something on the way** (process log, 16:10): a TennisLive run limited to recent weeks
rewrote the shared listing with only those weeks, for about ten minutes, before I restored it from the stored pages.
Every TennisLive run now stages every week on disk, with a test.

## 6. Doubles and start times (the "rhythm" statistics at bet time)

The unpriced-leads study's "rhythm" group needs, at the time of a bet: doubles played at other events in the last
week, and the hours since a player's previous match ended.
* **Doubles:** TennisLive's listings hold every level's doubles. They were not collected after 4 Oct, and the collector
  could not read the week in progress. It now can (`--through-yesterday`), and the new task runs it every day.
* **When the previous match ended:** TennisLive records observed start and finish times (since 9 Sep 2026, 28–82% of
  matches) but keeps them for only about a month, so the daily run is what preserves them. The ITF's live data has
  start and end times for ITF; TDI and the WTA's data have first-point times.
* **When the next match starts:** Pinnacle's listing, which the bet-day cells already pull, gives each match's start
  time. No ATP or WTA order-of-play page is collected; with Pinnacle's times it is not needed.
* **Not done:** the rhythm statistics themselves are not computed at bet time. That is part of building the adjustment,
  which waits for its test (your "go" on the unpriced-leads registration). The rest statistic will also need these
  finish times wired into the match-timing tables; today it reads Flashscore's (ending 17 Apr 2026) and copies of it
  (ending 13 Aug).
* **One more piece the adjustment will need, which I left for when it is built:** matches finished earlier on the bet
  day itself (a doubles match that morning, for instance). The daily run collects up to yesterday. TennisLive keeps a
  page per day, so the bet-day cells could fetch today's page on demand. I have not checked how complete today's page
  is while play goes on. **Recommend:** add this together with the adjustment, because nothing reads it until then.

## 7. Not fixed yet, and what I recommend

Accepting any of these is your call; each comes with my recommendation.

1. **The Roland Garros repair you adopted on 10 Oct is applied** (§ 4), and the model in use carries it. **One
   leftover:** the new model has 16 seeds for 2026, which is what predictions need, but only 4 for 2019–2025, which
   is what the comparisons and the speed adjustment use. The other 12 seeds of those seasons serve only 16-seed
   evaluations. **Recommend:** run them from the notebook when you're not betting (about 45 minutes):
   `fit_seasons('template_2026-10-14', seasons='2019-2025', seeds='4-15')`. See item 10 for why not beside a bet
   day.
2. **Nottingham and Berlin 2026, 58 women's matches without box scores.** The WTA's own data holds them. **Recommend:**
   add them as a main-tour repair, the way the Wimbledon and US Open 2026 box scores were added on 6 Oct. Small, and
   the women's grass form inputs of June read them.
3. **Women's Slam qualifying 2026: results only for now.** The WTA's own box scores for Slam qualifying count
   differently from the history (4–37% of counts equal), so the feed adds these 336 matches without box scores. The
   Slams' own records (Roland Garros's statistics, the Wimbledon and US Open feeds, all on disk) count the same way.
   **Recommend:** add them as a box-score source for this level (an hour or two of work).
4. **Women's ITF box scores of 1 June – 14 September 2026 have no consistent source.** The ITF's live data starts on
   15 September; SofaScore's 2026 ITF box scores lack break points; TennisLive's miss points in 15% of matches. Their
   results are in; their box scores are not. **Recommend:** accept the hole (about 3.5 months of women's ITF box
   scores), rather than mix in counts that differ. The coverage alarm treats those months as known until 31 Jan 2027.
5. **The unpriced-leads study reads the repository's own match table,** which never includes packages or the feed (by
   the 8–9 Oct rule). So its completeness check would still see the gaps, and its registered statistics were computed on
   the tables of 8 Oct. **Recommend:** when you re-issue its registration (the single-look version you were weighing),
   point its completeness check at a build's tables, which include the feed, and rebuild its statistics on them.
6. **Live bet days see the lower levels a week late at most.** The feed refreshes on Wednesdays. A player who has
   played a WTA 125 or an ITF event since then is missing those matches on a bet day, and the bet-day gate cannot see a
   match the table lacks. **Recommend:** for now, read A1's coverage line. If it matters, run the feed by hand before a
   bet day (cell B8, about an hour), or later make the gate check TennisLive's daily listing for missing matches.
7. **A tiny gap between training and bet-day inputs, from the level layer's re-centring rule (new tonight).** The new
   women's data moved the women's 2026 rating scale by 3.75 points. That switched on, for the first time, the layer's
   decided rule of 10 Oct: re-centre every new match by its season's average shift. The average is taken over the
   whole season, so it moves slightly whenever the season's matches change. As a result the men's layer-fed form
   inputs on a bet day differ from what a rebuild would compute, by about 0.000004 in the replay test (4 of 23 matches;
   the other 19, and every women's match, were exact). That is far too small to change a prediction. It also means a
   later match's rating nudges an earlier match's input (a look-ahead, if a negligible one). **Recommend:** compute the
   shift once per build and hold it on bet days, or compute it as of each match's date. Either is a small change to
   the layer's code.
8. **Two identity faults the hand check found remain in the builder:** TennisLive's partial-name route (it matched 8 of
   60 sampled players to a person with an extra or missing given name; it touches 2 matches in this snapshot), and one
   pair of shortened Korean names merged. The third fault (one WTA player under two ids) is fixed for the weekly runs:
   12 players joined, 7 coincidences kept apart by a name check. **Recommend:** tighten the partial-name route before
   it grows (an hour's work).
9. **Tennis My Life's 2022–2025 Challenger files are no longer held.** Another session checked and accepted them
   on 13 Oct (24 matches change, none main-tour; [decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)).
   The model in use since 14 Oct carries them.
10. **Two jobs on the graphics card can stall each other (found this morning).** Every fitting job waits while any
    other fitting process exists (`training_window/fits.wait_for_card`), the daily engine's fit included. So two jobs
    that check at the same moment wait on each other until one gives up: up to 12 hours for a model's fits. This
    morning the replay test and a model's background fits did exactly that for 40 minutes, until I stopped the
    background fits. A bet day started while a long fit job runs could hang the same way. **Recommend:** make the
    oldest job never wait for a younger one, a few lines in that function (or give bet days priority). Until then,
    run one card job at a time.

## 8. Files

| What | Where |
|---|---|
| The audit trail | [process_log.md](process_log.md) |
| The decision | [docs/decisions/2026-10-13-lower-level-feed.md](../../decisions/2026-10-13-lower-level-feed.md) |
| The coverage check and alarm | `src/eda/data_gaps_2026/coverage.py`; outputs in `data/studies/data_gaps_2026/coverage/` (`weekly/` once the task runs) |
| The feed's driver | `src/eda/data_gaps_2026/feed.py`; its runs in `data/studies/data_gaps_2026/feed/runs.jsonl`; candidates (not in git) in `feed/candidates/` |
| The feed's snapshots | `data/studies/current_best_model/accepted_additions/lower_level_feed/<date>/`, named in `accepted.json` |
| The builder (extended) | `src/eda/lower_level_evidence/candidate_stage0.py` (`--box-sources`, `--box-exclude`, `--keep-since`, `--results-only`, the WTA player pages, TDI) |
| The merge (feeds, the same-week rule) | `src/eda/current_best_model/additions.py` |
| Decided repairs in the history check | `src/eda/current_best_model/history.py` |
| The scheduled jobs | `src/ingest/scheduled.py --weekly`; the Windows task "Tennis predictions - lower-level feed" |
| TennisLive's week in progress, and the staging fix | `src/ingest/point_sources/tennislive_events.py` (`--through-yesterday`) |
| The notebook | cell B8 of `scripts/master_pipeline.ipynb`; `src/pipeline/data.py` (`lower_level_feed`, `feed_status`) |
| The harm check | `src/eda/data_gaps_2026/harm.py`; `data/studies/data_gaps_2026/harm/` |
| Before and after | `src/eda/data_gaps_2026/after.py`; `data/studies/data_gaps_2026/coverage/after_<snapshot>/` |
| The models | `data/studies/current_best_model/template_2026-10-13/` (the bridge, the harm check's arm) and `template_2026-10-14/` (in use); their build scripts `data/studies/data_gaps_2026/harm/build_feed_arm.sh`, `build_final.sh`, `resume_final.sh`, `switch_final.sh` |
| The replay's Tennis My Life view for the model in use | `C:/Users/zerom/tnr_dump_freeze_1014/` (set `DP_FREEZE_DUMP` to it for a replay of `template_2026-10-14`) |
| Tests | `test/data_gaps_2026/`, and additions to `test/current_best_model/test_additions.py`, `test/lower_level_evidence/test_candidate_stage0.py`, `test/gap_downloads/test_tennislive_events.py`, `test/data_continuity/test_rebuild_and_schedule.py` |

**To rerun** (from the repository root, Git Bash):

```
./python.sh src/eda/data_gaps_2026/coverage.py --stage0 <a Stage 0 folder> --with-accepted   # the gaps, any day
./python.sh src/eda/data_gaps_2026/feed.py --run --auto --advance                             # a weekly snapshot
./python.sh -m src.ingest.scheduled --weekly --only tennislive,wta,feed,coverage              # the task's jobs by hand
```
