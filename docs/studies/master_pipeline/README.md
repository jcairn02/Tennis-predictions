# The master pipeline notebook: data → model → predictions, without asking an LLM

11 October 2026, **updated 13 October: the bet-time output is now the bet sheet** ([below](#the-bet-sheet-a5); process log, Part 2); **updated 20 October: TabPFN-3.5-Thinking beside the local model, US odds only** ([below](#tabpfn-35-thinking-beside-the-local-model-20-oct-2026); process log, Part 6); **updated 22 October: the qualifying of the 250s and above is predicted and bet** ([below](#qualifying-of-the-250s-and-above-22-oct-2026); process log, Part 8); **updated 28 October: women's matches switched off for the bet day** ([below](#womens-matches-switched-off-for-the-bet-day-28-oct-2026); process log, Part 24); **updated 28 October, evening: one bad match is left out, loudly, and the rest are predicted** ([below](#one-bad-match-is-left-out-loudly-28-oct-2026); process log, Part 25) · For the owner · Process log: [process_log.md](process_log.md) · The design as the critics saw it: [design_v1.md](design_v1.md); briefs: [subagent_briefs.md](subagent_briefs.md) · **Not a decision:** the notebook runs the current best model as decided and changes nothing in its recipe.

## In short

* **Built:**
  * `scripts/master_pipeline.ipynb`: 32 cells, no stored outputs.
  * The layer it calls, `src/pipeline/`: ten small modules that run the project's own command lines in the right environment and read their outputs.
  * The Pinnacle recorder, `src/ingest/pinnacle.py`.
  * The tests, `test/master_pipeline/`: **26 passed** in 15 s.
* **It mirrors the UFC master script.**
  * A map, then setup and status.
  * The most frequent cells first: **A. Bet day**.
  * Then **B. Data update** and **C. Rebuild and retrain**, then maintenance.
  * Each cell is one call, and the switches are keywords (`MODEL`, `DRY_RUN`, …).
* **The data differs from UFC, as you said.**
  * A Windows task already downloads results, box scores and serve speeds every day at 07:30.
  * A prediction run rebuilds that day's tables in a sandbox and resumes each feature family from a saved checkpoint.
  * The notebook shows what is fresh and runs the rest by hand. Only B6 touches the shared tables.
  * **Since 13 Oct 2026, B8:** the lower-level feed and the coverage alarm (`tp.feed_status()`, `tp.lower_level_feed()`). A second Windows task keeps the levels Tennis My Life does not publish (ITF, WTA 125, women's qualifying, men's Challenger qualifying) flowing into every build and prediction run, and A1 prints the feed's snapshot and any coverage alarm ([the 2026 data gaps](../data_gaps_2026/README.md)).
* **The model switch:** `MODEL = "tabpfn35"` or `"tabpfn35_thinking"`.
  * **tabpfn35** is the current best model alone: local TabPFN-3.5, 57 inputs, seeds 0–15, and stage 2 with its walk-forward calibration slope.
  * **tabpfn35_thinking** (wired 20 Oct 2026, [below](#tabpfn-35-thinking-beside-the-local-model-20-oct-2026)) is that same run plus TabPFN-3.5-Thinking beside it, uncalibrated. The bet sheet shows both models and decides on their 50/50 average in log-odds. It needs `SPEND_TOKENS = True`.
* **Prediction-time data was the missing piece, and it now exists.**
  * One call pulls Pinnacle's listing: the live price you decided on, and the matchups.
  * The linker ties each match to Tennis My Life's event and to Stage 0's players.
  * It writes the daily pipeline's matchups CSV, and lists every match it leaves out, with the reason.
  * **Today (observed, 10:15 PDT):** 75 listed moneylines; **8 ATP Shanghai R32 matches for 12 Oct linked**. The 23 WTA Wuhan first-round matches are left out, because a first round waits for the event's first played match.
* **The bet sheet (A5, since 13 Oct):** `predictions/<day>/bet_sheet_<time>.xlsx`, also shown in the notebook, described below. It replaced the 53-column diagnostics CSV, whose record it keeps in `records/`.
* **The first live day ran end to end from these functions** (11 Oct, 23 minutes; the first run on new tables recomputes most state and saves a checkpoint, so later days take about 7). All 8 of tomorrow's Shanghai R32 matches were predicted. The diagnostics file is `predictions/2026-10-12/live_2026-10-11_110150_diagnostics_*.csv`.
* **Found on the way:**
  * **A name swap, now fixed.** `predictions.csv` could print a player's probability beside the other player's name. I found it; the daily_prediction session fixed it.
  * **14 active players can never be predicted.** Their name points to two Stage 0 ids, which would stop a whole run; Jakub Mensik is one. The linker now leaves them out.
  * **A rebuild would fill the disk.** Its sandbox copies 55 GB of TabPFN caches it doesn't use.
  * **A run started from a shell without conda died silently (14 Oct, fixed the same day).** numpy's math library could not find the right version of its own parts, and the run stopped in its states step about 12 minutes in, with no error message. Three bet-day runs were lost. The runner now puts each step's environment folders first on PATH, as `conda activate` does, whichever shell starts the notebook (`test/master_pipeline/test_runner_env.py`; process log, Part 4).

## One bad match is left out, loudly (28 Oct 2026)

Made after your request of 28 Oct: *"while you fix a single row it shouldnt hold up the whole pipeline"*, then *"Be
sure to mention the match that was left out and that there was an error in one row clearly and loudly, however still
give all the other predictions"* ([decision](../../decisions/2026-10-28-one-bad-match-left-out.md); process log,
Part 25).

* **What changed:** a match whose own row a step cannot handle is left out with its reason, and the step goes on with
  the others. That holds in A2 (one listing), A3's check (it no longer stops A3 or A4), A3b, A4 (A3's flagged rows and
  the engine's own), A5b, A7 (one run) and A8 (one sheet's record).
* **Where you see it:**
  * Lines starting `!!!` in the cell where it happens.
  * The last lines of A4: each match left out, its event and round, where the run found it, the error, and how many
    matches were predicted.
  * The bet sheet: red lines above everything naming each one with its error, and a NOT PREDICTED row whose reason
    starts "ERROR in its row", first on "Not predicted".
* **What it costs:** nothing, unless the run's own check of its data finds the bad match. Then the run builds its data
  again without it, so the others are predicted as if the match had not been listed. That takes about 2 minutes when
  the check right after Stage 0 finds it. It takes 5–11 minutes when only the check after the slow additions step does
  (a package that changed the match's row).
* **What still stops:** a run whose every match is left out, and a failure that names no match. Replays keep every
  refusal.

## Women's matches switched off for the bet day (28 Oct 2026)

Made after your request of 28 Oct: *"For the master_pipeline.ipynb steps A1-A8 temporarily disable womens matches.
We havent demonstrated they are profitable yet, im not betting on them, and their matches constantly cause errors"*
([decision](../../decisions/2026-10-28-women-switched-off.md); process log, Part 24).

* **The switch:** `BET_TOURS = ("atp",)` in `src/pipeline/config.py`. To bring women back, set it to `("atp", "wta")`
  and restart the kernel; nothing was deleted. STATUS shows it ("BET DAY (A1-A8)").
* **What you see:**
  * A2 lists men's matches only, and says in one line how many women's listings it left out. It does no linking work
    for them.
  * A3 to A5b: men's matches only. A sheet of a run made before the switch leaves its women's predictions out, and says
    so.
  * A7 and A8 show the men's figures. The runs' grades and the ledger file keep every prediction.
  * A1 is unchanged: the downloads keep both tours, because the model trains on both.
* **What it doesn't change:**
  * The model and the daily engine. A4 still builds both tours' tables; women's work is about 90 s of its states step.
  * The men's picks: the 15:30 run's sheet, remade with the switch, equals yours on all 9 men's matches.

## Qualifying of the 250s and above (22 Oct 2026)

Made after your decision of 22 Oct: *"We've done enough tests to conclude we should be betting the qualifying rounds of 250+ tournaments. Build the acceptance of this into A1-A5 so we can predict on them using the live model"* ([decision](../../decisions/2026-10-22-qualifying-bets.md); the evidence: [the qualifying study](../qualifying_targets/README.md); process log Part 8).

**What changed for you: nothing in how you run A1 to A5.** Qualifying matches of ATP and WTA 250s, 500s, 1000s and Slams now come through A2 like main-draw matches, are predicted in A4 and appear on the bet sheet. Their round shows as Q1, Q2 or Q3. Challenger, WTA 125 and ITF qualifying still stay out.

**The model is the live one, unchanged:** the same instance, the same 16 seeds, the same calibration (learned from main draws). A qualifying match's inputs are built exactly as in the study that measured the edge. **Stakes are the main draw's** (your word, later on 22 Oct: "Stakes should be the same as main"): the sheet's stake rule applies to qualifying bets unchanged.

**How A2 places a qualifying match.** Pinnacle's listing says only "ATP Almaty - Qualifiers", so A2 works out two things itself:
* **The event.** It is found in Tennis My Life's results once the event has any. Before that (every round 1, and all women's qualifying, which Tennis My Life does not carry), A2 builds it from the event's edition a year earlier: its surface, indoor setting, level and draw size.
* **The round.** A2 reads it from TennisLive's live results of the event: neither player has played yet, round 1; both won round 1, round 2. A round TennisLive cannot confirm (for example a player whose result is missing there) is left out with the reason; run A2 again later.
* **Fixed on 23 Oct:** A2 stopped with `KeyError: 'draw'` the first time a listed qualifying event had no finished match yet: Tokyo's, the day before it began. Such a match now reads as round 1, as intended. On the 11:39 listing, all 21 qualifying matches of Tokyo and Guangzhou were placed as round 1 and passed the daily pipeline's checks ([process log, Part 12](process_log.md)).

**Blocked: a round 2 or 3 whose round before is missing from the data.** The model needs each player's earlier qualifying result, as in training.
* **Men:** Tennis My Life publishes qualifying results within hours. Until it has round 1, round 2 is blocked; run A1 and A3b again later.
* **Women:** their qualifying results reach the data only through the weekly lower-level feed, so **women's rounds 2 and 3 are blocked on the day.** Women's round 1 can be bet. A same-day source for women's results is possible (the WTA's own API lists them); it is not built.

**What the checks showed:**
* **The inputs are the study's, exactly.** The engine's inputs for 956 past qualifying matches (both tours, Slams included) equal the study's to the last bit.
* **A replay of 17 Oct's round 1 (Almaty, Brussels) built as live rows gave all 57 inputs exactly**, once each match carried its main draw's start date. That date matters: before the main draw is played, the data would date the event by its first qualifying day, which moved 19 inputs (up to 2.4 sets in "sets in the last 14 days").
* **A2 estimates the main draw's start:** exact for 81% of the 2025–26 qualifying matches, within a day for 97%, never more than 2 days off. **Where it is a day off, the forecast moves:** on the replay's 16 matches, the model's chance by 0.4 points on average (at most 1.9), the chance used (with the patterns) by 0.1 (at most 0.4). Over all matches, with 81% exact, that averages under 0.1 point.
* **An event built from last year's edition matched what was later published**, on 778 men's round-1 matches of 2026: indoor, level, best-of 100%; surface 99%; players' ages within a day.
* **On the listing of 16 Oct 22:58 UTC**, A2 placed 32 of the 33 qualifying matches of Almaty, Brussels, Ningbo and Osaka. The one left out needs a name alias (Pinnacle's "Joel Josef Schwaerzler" is Tennis My Life's "Joel Schwaerzler").

**The five-pattern adjustment, tested on qualifying later on 22 Oct (your request): it does no harm, and stays on.** As on a main-draw match, it can move a forecast by up to about 5 points. Computed exactly as the daily run computes it, on the study's 15,834 qualifying matches of 2020–2026, it made the live model's forecasts +0.28 thousandths better (range −0.07 to +0.63: not proven, no harm), and the returns at the close rose (BetOnline every +EV side +4.5% → +5.8%, top 40% of edges +8.3% → +10.4%; Pinnacle +4.7% → +5.3% and +9.8% → +14.3%). The Slam-qualifying slice leaned slightly the other way (−0.12, not proven). [The study's follow-up 2](../qualifying_targets/README.md#follow-up-2-22-oct-1304-the-five-pattern-adjustment-on-qualifying).

**Not tested on qualifying, and on as for every match:** the Thinking ensemble, when `MODEL = "tabpfn35_thinking"`.

## TabPFN-3.5-Thinking beside the local model (20 Oct 2026)

Made after your request of 20 Oct: *"a tabpfn 3.5 paid thinking version I can run IN ADDITION to the tabpfn3.5 nonthinking version, so I can see their results side by side in the tennis bet sheet … We'll use basically a 50/50 ensemble to calculate edge/expected profit."* Recorded as a [decision](../../decisions/2026-10-20-thinking-beside-local.md); process log Part 6.

**Why A4 refused before.** The refusal came from the notebook's own guard, before any call to the API. The daily engine had no way to run Thinking, so `predict_day` stopped there. Setting `spend_tokens=True` would not have helped.

**How to use it:**
1. In Setup, set `MODEL = "tabpfn35_thinking"` and `SPEND_TOKENS = True`.
2. Run A1 to A5 as usual.
   * **A4** runs the local model as before, then makes one paid Thinking call for all the run's matches (about 32–35k tokens).
   * **The first Thinking run on a new instance** first makes that instance's season fit (about 180k tokens and 8 minutes). C1 (`instance_status`, "Thinking fits") shows whether the live model has one; on 22 Oct 2026 the live model (the 21 Oct retrain, `template_2026-10-21b`) had none, so its first Thinking run makes it.
   * **A5** shows the sheet below. A5b (A6 until 27 Oct) reprices both models off their stored curves, at no cost.

**What Thinking is.** The same model in everything but how it is called and that its probabilities are not calibrated:
* the same 57 inputs and exactly the same training rows (the engine checks their hash against the fit's);
* the same rows to predict (each match at 91 prices and its own, both orientations averaged);
* seed 0;
* ~~no stage 2~~ no calibration slope, but stage 2's serve-speed term is added: the local b̃ · `spd_L`, men only (the owner, the evening of 20 Oct 2026: "should still move with the serve speed numbers ... just not the calibration"; process log Part 7).

The 13 Oct paid answers, replayed through the new step without any token, came out identical to that day's comparison.

**The bet sheet now:**
* **Odds:** only US odds, everywhere. The "Lowest odds to take" column is in US odds too, and any price above it is better.
* **A Thinking run's chances:** "Model chance", then the non-thinking, the thinking and the ensemble chance without patterns. The ensemble is the two chances averaged 50/50 in log-odds (your answer of 20 Oct: 60% and 70% give 65.2%, 10% and 20% give 14.3%), and "Model chance" adds the five-pattern adjustment to it.
* **Training rows:** both models train on 2013–2025 for the 2026 season (the annual protocol). The in-season growth you decided on 9 Oct is not built yet ([the decision](../../decisions/2026-10-20-thinking-beside-local.md), "Cost and limits").
* **What uses the ensemble:** the edge, the expected profit, the decision and the stake.
* **If the Thinking call fails:** the sheet is the local model's alone, and its first note says so; A4 prints a warning in capitals.

| Bet sheet columns | Local run | Thinking run |
|---|---|---|
| Odds | US odds, Lowest odds to take (both American) | the same |
| Chances | Model chance, Model chance without patterns, Market chance | Model chance, Non-thinking / Thinking / Ensemble chance without patterns, Market chance |

**Not measured:** the ensemble on past seasons. A walk-forward test needs a paid Thinking fit per season (about 1.3M tokens for 2019–2025). The 8 Oct study found uncalibrated Thinking level with the calibrated local model on 58 inputs.

## A bet day, cell by cell

**Run A1 to A8 top to bottom, whenever it suits you** (since 27 Oct 2026, your request: *"If i could just sequentially run A1-A8 (except A6) it would make my life easier. But Id want the aproximate same net effect of I did A7 more selectively. A6 could maybe renamed A5b, as I see b steps as more optional"*; how it works is an agent's design, [process log, Part 19](process_log.md)).
* **The b cells are optional,** and a run-through skips them: A3b checks the data before the 10-minute run; A5b (A6 until 27 Oct) reads new prices for the matches A4 predicted, later the same day.
* **A day with nothing to predict:** A3 says so without an error, A3b to A5b skip, and A7 and A8 still run. A3 starts each pass afresh, so a kernel left open since another day never predicts that day's matchups again.
* **A7 grades the earlier runs by itself:** a run once its matches' results are on disk, again as more arrive, never the run A4 just made. It reads the freshest results on disk, as A8 does, so it no longer waits for B6. Seconds when nothing is new.
* **A7 and A8 kept their numbers;** there is no A6 now.

| Cell | Call | What it does | Time |
|---|---|---|---|
| A1 | `tp.morning_refresh()` | Refetches results and serve speeds if older than 6 h; shows held files and alerts | seconds (minutes if it runs) |
| A2 | `tp.record_pinnacle()`, `tp.todays_matches()` | Pinnacle's listing now (three paced requests, raw copies and receipts); each match linked or left out with its reason | ~10 s |
| A3 | `tp.build_matchups(matches)`, `tp.check_matchups(...)` | The matchups CSV (`only=` / `drop=` to choose); the daily pipeline's own refusals checked first | seconds |
| A3b | `tp.data_check(MATCHUPS)` | **Since 13 Oct:** the run's gate applied before the run, [below](#the-data-check-a3b) | ~100 s; ~20 s when nothing new was downloaded |
| A4 | `tp.predict_day(MATCHUPS, model=MODEL, spend_tokens=SPEND_TOKENS)` | The template check, then the daily pipeline's `run_day --refresh` (seeds 0–15) in a new run folder and the notebook's own work tree; with `"tabpfn35_thinking"`, one paid Thinking call after the local fit (and the instance's season fit first, once) | ~7 min warm; the first run on new tables 23 min (11 Oct); Thinking adds about a minute (8 more for a season fit) |
| A5 | `tp.bet_diagnostics(RUN)` | The bet sheet, below | seconds |
| A5b | `tp.reprice(RUN)` | Optional, later the same day: a new Pinnacle price, read off the run's stored curve (no refit), then a new bet sheet; with no run in the kernel, the newest run | seconds |
| A7 | `tp.grade_due()` | **Since 27 Oct:** every earlier run whose results came in since its last grade, graded again (`tp.grade(run)` grades one by hand) | seconds; about a minute the first time |
| A8 | `tp.clv_ledger()` | **Since 25 Oct:** every bet sheet's predictions against Pinnacle's close, [below](#the-closing-line-a8) | ~10 s |

If Pinnacle doesn't list a match, use `tp.manual_matchups([...])` with both players' odds, American or decimal; the margin is kept for EV. BetOnline's line stands in only while Pinnacle has none.

If a run is stopped midway, the notebook removes its work tree with the daily pipeline's own cleanup. `tp.cleanup_work_tree()` does it by hand. Never delete that folder by hand: it holds links to the repository's `data/raw` and `data/dump`.

**If a cell says "STOP: … was not run. This notebook's kernel is running older code than the files on disk"** (since 23 Oct 2026):
* **The cause:** a file the notebook's code uses changed after the kernel loaded it, usually an agent's edit. The kernel keeps running the old copy until it is restarted.
* **What to do:** restart the kernel (Restart, in the toolbar), run SETUP, then the bet-day cells again from A1. A matchups file or bet sheet the kernel made after the change came from the old code; the message lists each file and when it changed.
* **What it prevents:** on 23 Oct, a kernel started on 21 Oct stopped A4 with "dp_common.py: cannot read its default INSTANCE_ID / DP_BASE_TREE". Its old copy of the code was reading a file changed on 22 Oct. Old code can also apply a replaced rule without saying so ([process log, Part 11](process_log.md)).

The check is an agent's choice, not yours, and it changes no forecast.

## The data check (A3b)

Made 13 Oct after your question: *"Why would there be no box score? … wouldnt it make sense to wire up obtaining the necessary data … such that theres a logical flow in the master script"*.

**Why the three 11 Oct matches were blocked.** Tennis My Life *had* the Laver Cup box scores. Our Stage 0 rejected two of them, which blocked three matches: it read the 10-8 and 13-11 match tiebreaks as full sets, so the box scores looked like part of a 41- and a 43-game match. That reading is now repaired, as you approved ([decision](../../decisions/2026-10-13-match-tiebreak-reading.md)). Exactly those 2 matches change in all of Stage 0.

**The check** (`src/pipeline/readiness.py`) tells you before the 10-minute run what the run's gate will do to each match.
* **It reads what the run reads:**
  * Stage 0 built now on the downloads on disk, by the run's own builder, into a cache (never the shared tables);
  * the lower-level packages and feeds merged in, by the run's own merge.
* **It applies the gate's rule** (replaced on 14 Oct 2026, [decision](../../decisions/2026-10-14-box-score-gate.md)): every earlier match of either player, at the event or in the 14 days before, is checked for a usable box score. A missing one never blocks:
  * of a kind training nearly always has (main tour, Challenger / WTA 125, qualifying above ITF level), a bet needs a 1-point edge;
  * of a kind training mostly lacks (team events, ITF), it is only noted.

  A qualifier without a qualifying match still blocks.
* **Each match is "ready", "ready once filled", "needs a 1-point edge" or "will be blocked"** ("ready once filled": the run fills the box score from an official feed), with the cause and what fixes it:

| Cause | What fixes it |
|---|---|
| Tennis My Life has none yet | Wait, run A1 again, then A3b. The run fills women's tour matches after 8 Oct from the WTA's own feed |
| Tennis My Life has it, but our consistency check rejected it | A data repair (as for the Laver Cup); until then a 1-point edge |
| A match from the lower-level feed lacks one | Its source's next publication, taken at the feed's next snapshot (B8) |
| A qualifier without a qualifying match | Nothing on the day: blocked |

**It agrees with the real gate.** On the 11 Oct run's own Stage 0 and matchups it checks the same earlier matches and finds the same three gaps; a test holds it to that. Those were the Laver Cup's, a team event, so under the rule of 14 Oct they are only noted and all eight matches are ready.

**The run stays the authority.** It downloads once more, then decides with its own gate, which also checks the indoor input that only the run builds. The check errs toward a gap: a match missing from the shared timeline gets a cautious window.

## The bet sheet (A5)

Made 13 Oct after your question: *"if I were a businessman looking at this information … which side to bet, and by how much?"* The 11 Oct file had 53 columns. The decision sat in columns 40–46, every number carried up to 16 decimals, and the players were Stage 0's sides, not Pinnacle's order. The same three run warnings repeated on every row, and times were in UTC.

**What changed is the presentation only.** Rebuilt from the same run at the same times, the two 11 Oct files are reproduced exactly: 52 of 52 columns, 81 and 31 rows. The one difference is intended: the run's notes are said once, in the header, instead of on every row.

* **The file:** `predictions/<day>/bet_sheet_<made>.xlsx`, a new one each call. Its sheets:
  * **Bet sheet:** one row per match, BET first, then PASS, then BLOCKED, colour-coded. A row gives the start in your time zone, the match as Pinnacle lists it, the decision and the player, the stake, Pinnacle's US odds, the lowest US odds still worth taking (1 / model chance), the model's chance and the market's (since 24 Oct: the chance Pinnacle's posted price implies, its margin included, [below](#the-market-chance-is-the-posted-prices-24-oct-2026)), the edge in points (model minus market), the expected profit, the event, and a plain note: why a PASS or a block, or a thin edge. Since 20 Oct every price is in US odds (the decimal column is gone), and a Thinking run shows the non-thinking, the thinking and the ensemble chance without patterns ([above](#tabpfn-35-thinking-beside-the-local-model-20-oct-2026)).
  * **Matches:** every figure of both players.
  * **Not predicted.**
  * **Run:** provenance.
  * **How to read:** every column.
* **The header says once:**
  * the totals: units staked, to win, and the model's expected profit;
  * the price's time and the 30-minute rule;
  * the model;
  * the stake rule;
  * "expected profit is the model's estimate, not a measured return";
  * the run's notes.
* **In the notebook:** the same table, with each match's note listed under it.
* **`records/` holds the machine record** (the columns below, unchanged, plus `decision`, `home_side` and `gate_detail`), its provenance, and the daily engine's archive of the run.

The sheet computes nothing: `src/pipeline/bet_sheet.py` only reads the record. A test holds it to that: every BET is the record's pick at its odds, EV and stake, and no BLOCKED row offers a player, a stake or odds.

### The market chance is the posted price's (24 Oct 2026)

Your words, about Griekspoor at −121: *"I dont care what the fair value is with vig removed, I just care about the price that the bookmaker posts. Market chance should be market chance INCLUDING VIG ON THE SIDE WE ARE TRYING TO BET."* Until then the sheet showed the price with Pinnacle's margin removed (53.2%, the model's own input). The edge against it (+1.9 points) looked far bigger than the expected profit (+0.7%).
* **Now:** "Market chance" is 1 ÷ the decimal odds of the player shown: 54.75% at −121, the chance he must win to break even. "Edge" is the model's chance minus it: +0.4 points. A positive edge is a positive expected profit (the expected profit is the edge times the payout), and a match with a data gap needs an edge above 1 point. The Matches tab shows both players' posted chances; they add up to 100% plus the margin.
* **Chosen by Claude to match:** the Matches tab's "Edge gone if the market reaches" was measured against the margin-free price too. It is now "Zero edge if Pinnacle moves to": the price Pinnacle would have to post for the model's side for its expected profit to be zero. The model's chance moves with Pinnacle's line, so it is re-read off the run's curve at each price, with Pinnacle's margin kept as it is. These prices are often far from the current one, because the model mostly moves with the market.
* **Unchanged:** the model is still fed the price with the margin removed, as in training (your rule of 9 Oct). No decision, expected profit, stake or block changed: the 21:47 sheet of 24 Oct, rebuilt before and after, has the same 10 bets and 9 passes, and every figure but these columns is the same (process log Part 15).

### The record behind it (`records/bet_sheet_<made>.csv`)

Everything is side A / side B as the daily pipeline's Stage 0 fixes them; the names come from Stage 0's own player rows.

| Group | Columns |
|---|---|
| The match | day, start (UTC), minutes to start, tour, event, round, best of, surface, indoor (and its source) |
| The price | source, quote time and age, Pinnacle's odds for both players (with its margin), overround, the margin-free price the model was fed (`p_market_a`), Pinnacle's stake limit |
| The model | `p_base_a` (stage 1), `eta`, `spd_L` with each man's serve-speed readings in 28 days, `q_a`/`q_b` (both stages: the forecast), fair odds 1/q for both, the spread of the 16 seeds. A Thinking run (since 20 Oct): `q_a` and everything computed from it are the 50/50 ensemble's, with `q_a_local`, `q_a_local_patterns_off` and `q_a_thinking` beside them; the record's odds stay decimal (expected profit is computed from them), the sheet shows them in US odds |
| The patterns (since 13 Oct 2026) | The five-pattern adjustment ([decision](../../decisions/2026-10-13-five-pattern-adjustment.md)): `patterns` (on/off), `q_a_patterns_off` and `q_a_patterns_on` (`q_a` is the one used), `pattern_shift_pts_a`, the decision without it (`pick_patterns_off`, `ev_a_pinnacle_patterns_off`, `ev_b_pinnacle_patterns_off`), and `patterns_effect` ("bet only with the patterns", "the patterns remove this bet", "the patterns switch the side"). The sheet shows "Model chance without patterns" and says in Notes when the patterns make or switch a bet |
| The bet | `edge_a` = q − p; the **pick** is the side whose EV at Pinnacle's own odds, margin included, is positive; `min_odds_to_bet` = 1/q, the least odds still +EV at any venue before fees; its EV at Pinnacle; EV at another venue when you pass its prices (`venue_prices={...}`: odds, or a Polymarket share price) |
| Break-even | every side-A price where the model's curve crosses q = p, the one nearest the current price, or "none in [0.05, 0.95]". Curves cross 0 to 3 times (a replay: 6, 9, 1 and 7 matches) |
| Zero EV (since 24 Oct 2026) | `zero_ev_implied_a`/`_b`: each side's posted chance, margin included, at which its EV at Pinnacle's odds would be zero if the line moved there with its margin kept, the model's chance re-read off the curve; `nearest_zero_ev_implied_a`/`_b`: the one nearest the current price. The sheet's "Zero edge if Pinnacle moves to" |
| The edge bar (since 14 Oct 2026) | `gate_edge_bar`: an earlier main-tour, Challenger or qualifying match lacks a box score (`gate_detail` says whose), so a side is picked only if its forecast moved 1 point against it is still +EV at the odds; `passed_by_bar`: the +EV side the bar took away (a PASS that says so). `gate_notes`: missing box scores of kinds the model was trained without (team events, ITF), noted only ([decision](../../decisions/2026-10-14-box-score-gate.md)) |
| Blocked | no pick and no EV when:<br>• the gate says do not bet (since 14 Oct: only an unknown indoor input, or a qualifier with no qualifying match; since 22 Oct also a qualifying round whose player's round before is missing)<br>• neither a main-tour match nor tour-level qualifying (bet since 22 Oct), or an unsupported format<br>• the quote is over 30 min old<br>• a price or player read-back mismatch<br>• a new price off the curve<br>• no bookmaker odds with their margin, without which EV would flatter every pick<br>A listed start that has passed no longer blocks, since 24 Oct 2026 (the owner; [decision](../../decisions/2026-10-24-start-time-never-blocks.md)). A2 and the reprice keep a match Pinnacle still lists pre-match after its listed start |
| Warnings | this match's own: a player new since Stage 0, seeds that disagree, missing speed form. The run's own notes (the history check, recomputed state parts, an unclean results download) go to the provenance and the sheet's header since 13 Oct |
| Not predicted | one row per listed match of the window that was left out, with the reason |

A stake column appears with `stake_rule="owner_8oct"`: your 8 Oct research rule in units, labelled as research. The notebook sets it since 13 Oct (decision 7). No staking rule is decided.

## The closing line (A8)

Made 25 Oct after your question: *"comparing the "best model predictionsat the time of the run" to the closing line (as well as see how much the line drifted since then to calculate CLV) will be useful"*. Every rule below is an agent's choice, not yours ([process log, Part 18](process_log.md)).

**What it is.** `tp.clv_ledger()` rebuilds `predictions/clv/ledger.csv` from every bet sheet's record, each time it runs.
* One row per sheet and predicted match, each with Pinnacle's close, the line's move since the sheet, and the closing-line value of the pick.
* Nothing is kept by hand, so it cannot go stale. Run it again after the 07:30 download for the closes of the matches played since.
* UFC's snapshot keeps only the last run before each card. Here every sheet is kept, and each match is read on its last sheet before the start, the one a bet most likely came from.

**Where the close comes from:**
* **Pinnacle's own listing, read by our pulls:** a *true close* when the next pull, within 15 minutes, finds the pre-match market shut or gone. The bet-day pulls (A2, A5b) rarely land that near a start; P11's 10-minute capture does, but it ran on 22–23 Oct only (decision 5 below).
* **TennisExplorer's record of Pinnacle** (the daily `pinnacle_closes` download): the close the model's training data uses since Nov 2025.
  * It counts as the close here when it is known to hold within 2 hours of the start (its record, or a later pull of ours with the same price).
  * Its record ends a median 47 minutes before the start, and it keeps only some of Pinnacle's changes: it equalled our own pull at the same moment on 162 of 191 readings.
* **Qualifying has no TennisExplorer pages:** a qualifying match has a close only if Pinnacle's listing was read near its start.
* A match with only an earlier price is listed, but left out of the figures. So is a void match (a walkover, or a pairing that changed before the match).

**The figures** (each pick, at the price on its sheet):

| Figure | What it means |
|---|---|
| Beat close by (the closing-line value) | The odds taken against the closing odds, both with Pinnacle's margin. 0: the line did not move |
| EV if close is fair | The expected profit per unit if the closing price, margin removed, is the true chance. A bet at the closing price itself scores minus Pinnacle's margin (about −2.7%), so compare with that, not 0 |
| Line toward pick | How far the market moved toward the pick, in points of probability |
| Model EV at close | The model's chance re-read off its curve at the closing price, against the closing odds |
| The move toward the model | Over every match with a close: the share of the model's disagreement with the sheet's price that the market closed. The backtest found +0.01 [−0.02, +0.04] ([bet timing](../bet_timing/README.md)) |
| Results | Once a Stage 0 holds them (the freshest of the repository's, A3b's and the newest run's): won or lost; the log losses of the model, the sheet's price and the close |

**What it is not.**
* **A check on the model.** The market does not move toward this model before the close, so the model's alarm is the strength of its lean ([production-integrity plan](../../decisions/2026-10-22-production-integrity-plan.md), principle 8). The closing line checks the prices we got.
* **The bets placed.** These are the sheets' picks at Pinnacle's price. Nothing records the bets you place yet (the plan's step 3).

## Data: what is automatic and what is by hand

| Source | Automatic? | Cell |
|---|---|---|
| Tennis My Life (results, box scores), ATP serve speeds, ITF live | Daily at 07:30 (Windows task) | B1–B3 by hand; A1 refetches when stale |
| TDI and the WTA API (exact match days for the timeline) | TDI on Mondays; WTA not scheduled | B4 |
| tennis-data.co.uk, OddsTrader (odds history) | Not scheduled (last pulls 5–6 Oct) | B5 |
| Stage 0, Stage 1's odds, the timeline (the shared tables) | Never by itself: other sessions read them | B6, with `confirm=True` |
| Pinnacle's current lines | By hand, in A2 (each pull kept: a price history from today) | A2 |

## How it was built

A small team, as you asked:
* **Recon:** four read-only agents mapped the UFC workflow, the data refreshes, the rebuild and daily paths, and the Thinking variant.
* **Design:** two critics then reviewed the design independently, one from your seat, one for correctness and money safety. Their main points were adopted; the log records each adoption and each departure, with reasons.
* **Code review:** an independent reviewer read the finished code. Its 12 findings are fixed (process log, 10:45). The two that mattered most:
  * typed (manual) odds were losing their margin, which showed losing picks as +EV;
  * long steps died if the notebook's kernel died.
* **The peer session:** the daily_prediction session was improving the prediction code at the same time. We agreed an interface:
  * the notebook calls `dp.py` only through its command line;
  * this side builds the prediction-time inputs and the Thinking season fits;
  * that side owns the Thinking switch inside its fit.

  I built the prediction part last, as you suggested. Nothing in its folders was edited from here.

## Verified

| Check | Result |
|---|---|
| Every command the layer can issue against its target's own `--help` (32 commands, 19 scripts and modules) | All flags exist |
| The arithmetic: odds conversion, proportional margin removal, rounds from the draw, break-even roots, side orientation | Pass |
| The Pinnacle staging and the linker on the saved 9 Oct probe | 46 usable of 58; Shanghai linked; the matches Tennis My Life already holds, and Mensik's ambiguous name, left out |
| The diagnostics on an existing replay (read only) | q and edge equal `predictions.csv`'s; blocked rows have no pick; every pick is +EV at the odds shown; root counts as the reviewer found |
| A Thinking fit without `--spend-tokens` | Refused. Nothing in this work spent a token |
| The training-row hash a Thinking fit records | Equal to the daily pipeline's own recipe |
| The whole notebook executed top to bottom with `DRY_RUN = True` (again after the review's fixes) | 4–5 s, no error; A1–A4 ran their real checks |
| The review's fixes: margins kept for typed odds, a spend flag for Thinking, the instance checked = the instance run, a dry-run reprice, run order, event and time-zone rules | 6 tests added: 26 pass |
| A real Pinnacle pull and today's linking | Above |
| **A live end-to-end day, from the notebook's functions** (11 Oct, 11:01–11:25 PDT) | **Worked.**<br>• **The run:** a Pinnacle pull at 18:01Z; 8 Shanghai R32 matches of 12 Oct linked and checked; the template check passed; the daily pipeline's run of 1,393 s (states 390, checkpoint 609, fit 57); all 8 predicted with the checked instance.<br>• **The checks:** every price read back exactly. Where Pinnacle's home player is Stage 0's side B (Bergs v Alcaraz, Lehecka v Jodar) the price was flipped correctly. `price_quoted_at` arrived.<br>• **The bets:** the gate allowed 5; 4 matches show a +EV side at Pinnacle's own odds.<br>• **A6:** a re-price at 18:26Z, read off the curve |

## Limits

* **First rounds can't be predicted.** The daily pipeline needs a played match of the event, so tomorrow's Wuhan first round waits. *Since 22 Oct 2026 this holds for main-draw first rounds only:* a qualifying round 1 is built from its previous edition ([above](#qualifying-of-the-250s-and-above-22-oct-2026)). The same could serve main-draw first rounds; not done, since nothing about them was asked.
* **14 active players can't be predicted.** Their name keys point to two Stage 0 ids (decision 3).
* ~~**Thinking's daily predictions are not wired yet** (above).~~ **Wired 20 Oct 2026**, beside the local model ([above](#tabpfn-35-thinking-beside-the-local-model-20-oct-2026)). Its ensemble with the local model is not measured on past seasons.
* ~~**The daily pipeline can't be switched to a new instance from the notebook.**~~ **Done (11 Oct 2026), and since 22 Oct 2026 one place names the live model:** the notebook's selection (`data/studies/master_pipeline/selected_instance.json`), written by `use_instance()` or a retrain's switch. The daily pipeline reads it too and has no default of its own: with no selection it refuses to predict, and STATUS says "LIVE MODEL: NONE SELECTED". A bet sheet blocks every match of a live run made with another model than the selected one ([process log, Part 9](process_log.md)).
* **Stage 2 reads the weekly speed set** (decision 2). *Fixed 14 Oct: live runs read the daily set.*
* **The gate marks women who came through qualifying "do not bet".** Tennis My Life has no WTA qualifying since June.
* **BetOnline's line, when Pinnacle has none, is entered by hand** (`manual_matchups`).
* **The notebook checks names against the shared Stage 0 of 8 Oct.** A player new since then is found in Tennis My Life's rows instead, and the run's own refreshed Stage 0 holds them. Since 28 Oct 2026 the check applies the decided id aliases, so a player's second id merged after the shared tables were built no longer makes his name ambiguous ([decision](../../decisions/2026-10-28-mensik-id-alias.md)).

## Decisions for you

| # | Question | My recommendation |
|---|---|---|
| 1 | **Thinking:** approve paid use? | **Yes, in steps.** First the free quote (C9; it costs nothing). Then one paid fit for 2026, about 180k tokens billed (an estimate from past receipts). Then daily predictions on that saved fit, about 30k tokens a day, seed 0 only. Use stage 2's 8 Oct research rule (η + the local b̃·spd_L, no slope; Thinking's own slope was 0.99), labelled research, with no edge credit, until paid back-season fits (about 1.3M billed) allow a calibrated slope. One fit per season rather than refitting daily (the in-season policy would cost about 5.5M a month for a gain of 0.001–0.01 mLL). The API's terms for betting use were not checked. **13 Oct, at your request:** the 2026 fit was made on the active instance (181,901 tokens; `thinking/template_2026-10-10/season2026/fit.json`), and today's five Shanghai matches were predicted with it, uncalibrated (one call, 31,572 tokens; `src/eda/thinking_live_compare/`; process log Part 3). Daily Thinking predictions are still not wired.<br>**Decided 20 Oct by the owner:** Thinking runs beside the local model, never alone; its own probability, uncalibrated, no serve-speed term; the bet sheet decides on the 50/50 average in log-odds ([decision](../../decisions/2026-10-20-thinking-beside-local.md)). Wired the same day: `MODEL = "tabpfn35_thinking"`, `SPEND_TOKENS = True`. Seed 0 only, and the patterns after the average: both confirmed by you the same day. The first season fit, `template_2026-10-16`'s, was made by A4 at 08:16–08:23 (181,901 tokens). |
| 2 | Stage 2's speed set: the decision says `spd_L_D` once the daily collector runs, and it has run daily since 8 Oct; the code still uses `spd_L_B` | **Switch live runs to `spd_L_D`** as the decision says, replays before 8 Oct keeping `spd_L_B`. It changes predictions, so it is yours. The daily_prediction session is asking you too.<br>**Decided 14 Oct by the owner: yes. Done in the daily pipeline the same day** (matches from 8 Oct take the daily set; `predictions.csv`'s `speed_feed` says which; [its report](../daily_prediction/README.md)). |
| 3 | 14 active players with two Stage 0 ids (Mensik, Landaluce, Gigante, …) | **Two fixes.** The daily pipeline should take each player's id from the matchups CSV (my CSV already carries `stage0_id_a/b`). The duplicates should be merged as a repair, through the candidate route since some rows are lower-level. |
| 4 | The rebuild sandbox copies `data/studies` whole, including 55 GB of TabPFN caches (disk: 106–119 GB free) | **Exclude `daily_prediction`, `prediction_run` and `master_pipeline` from `run_chain`'s copy.** It changes no output. Until then `build_instance` refuses below 130 GB free, with this explanation. |
| 5 | A Pinnacle cadence: pulls are by hand today | **Add a pull to the scheduled task during events** (hourly, plus near match starts). It records a price history and the closing lines your 9 Oct decision would retrain on. Cadence is a download decision, so it is yours. *21 Oct 2026:* the closing lines now come daily from TennisExplorer (the daily task's `pinnacle_closes` job, on your word; [research](../../research/pinnacle-gap/README.md)). A price history through the day from Pinnacle's own site stays open. *25 Oct 2026, with the closing line (A8):* **run P11's 10-minute capture as a standing job.** Without it, a qualifying match has no close at all: TennisExplorer has no qualifying pages, and of the 55 qualifying matches predicted 11–25 Oct only the 5 the capture read on 23 Oct have one. A main-draw close is then TennisExplorer's record, which ends a median 47 minutes before the start. A close not recorded on the day is lost. |
| 6 | Where the layer lives (CLAUDE.md's table has no row for it) | **Add a row:** "Operator pipeline (the notebook's functions): `src/pipeline/`". |
| 7 | A stake column | ~~Leave it off until a staking rule is decided.~~ **13 Oct: shown**, since you asked "by how much?". It uses your 8 Oct research rule, which sizes by the price only, labelled on the sheet; `STAKE_RULE = None` hides it. **Still open:** a decided staking rule, and whether a bet needs a minimum expected profit. Today any +EV counts, even Fils' +0.3% on 11 Oct, which the sheet flags as thin. |
| 8 | The four held Tennis My Life Challenger files (2022–2025; rows vanished upstream) | Review them before accepting (B2). They are lower-level data, so accepting one changes the lower-level history. Nothing in this work touched them.<br>**Done 13 Oct (owner's word; [decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)):** checked by a scratch rebuild ([report](../tml_revisions/README.md)): cleanup, not damage. 24 Stage 0 matches change, all men's Challengers: duplicates removed, a misplaced match restored, keys rebuilt. No main-tour match changes. Accepted at 18:48. |
| 9 | Today's diagnostics warn on every row: "history check: the lower-level history differs from the reference". On 11 Oct, Tennis My Life corrected 50 old lower-level matches; nothing was newly played (lookup of 11 Oct, process log):<br>• **30 re-identified:** who played, mostly 2011 Rome and Umag qualifying, where the frozen copy has 24 unnamed placeholder ids.<br>• **One duplicate id merged:** Andre Ilagan, who then has one id.<br>• **18 ages fixed:** Ilagan was recorded as 56 in 15 Challengers (now 25.6), Miguel Tobon as 58 in 3 (now 20.2).<br>• **None of today's 8 predicted players is touched.**<br>A template build would refuse this; the live path builds from the day's data and only reports it. The daily_prediction session is putting three options to you: hold lower-level history at the 8 Oct freeze in live runs, accept the revisions, or refuse such runs | **Accept them, under a standing policy** (revised 11 Oct, after your question). The level-layer decision of 10 Oct already settled how men's Challenger and qualifying data enters (translated by opponent strength, weighted). The proposed policy covers lower-level data from the feeds that route was validated on (new rows, corrections, backfills):<br>• It enters by itself: in live runs at once, in training at the next instance rebuild.<br>• The history check keeps listing every change, and a harm check runs at each rebuild.<br>• The candidate step stays for new kinds only: ITF box scores (the P7 test), new sources, women's lower levels.<br>Without such a policy: hold at the freeze (the daily_prediction session's option 1). Until you decide, the diagnostics warn and do not block.<br>**Retraining for these 50 alone: not now** (owner's question, 11 Oct):<br>• **Small reach:** 97 players are touched, in 6,402 of the 62,869 rows the 2026 fit trains on, but only through one to three old qualifying results each in long-memory ratings. The effect is likely far below what a comparison can resolve (an inference, not measured).<br>• **Live runs already use the corrections.**<br>• **The cost is not the GPU:** ~4 h of build, a shared-table rebuild, ~75 GB of sandbox on ~100 GB free, and a new checkpoint and caches.<br>• **Batch it with the next rebuild that matters:** P7's ITF test, Pinnacle's missing closes, the in-season fit, or the 2027 rollover.<br>**Decided 13 Oct by the owner: accept them under the standing policy, no retrain for them alone** ("record the decision and run the check on the four files"; [decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)). `history.py` lists Tennis My Life's own lower-level changes as `tml_lower` and no longer refuses a build for them. The bet sheet's note was still calling this open; that wording is being changed. |

## Files

| What | Where |
|---|---|
| The notebook | `scripts/master_pipeline.ipynb` (kernel: the `tennis` conda env) |
| The layer | `src/pipeline/`:<br>• `config` (paths, interpreters read from the shims)<br>• `runner` (streamed steps, logs, receipts, dry runs)<br>• `overview` (status)<br>• `data`, `train`, `live`, `predict`, `diagnostics` (the record)<br>• `bet_sheet` (the sheet, the workbook, the notebook's view; since 13 Oct)<br>• `readiness` (the data check, `tp.data_check`; since 13 Oct)<br>• `thinking` and `thinking_api` (season fits)<br>• `qualifying` (a qualifying match's event, round and main-draw start; since 22 Oct)<br>• `closing_line` (the closing-line ledger, `tp.clv_ledger`; since 25 Oct) |
| The closing-line ledger (25 Oct) | `predictions/clv/`: `ledger.csv` (every sheet's every prediction), `ledger.provenance.json` (sources, checks, rules), `summary.json` (what A8 shows) |
| The qualifying checks (22 Oct) | `src/eda/master_pipeline/qualifying_dates.py` (the main-draw start against training's dates), `qualifying_rows_check.py` (built round-1 rows against published ones); their outputs, the replays' frame and logs in `data/studies/master_pipeline/qualifying_replay/`; the replays in `data/studies/daily_prediction/runs/replay_2026-10-19_Q*_qualifying*/`; the engine's input checks in `data/studies/daily_prediction/checks/tree_check_*_qualifying.json` |
| Thinking's daily call (since 20 Oct) | the daily engine's `src/eda/daily_prediction/dp_thinking.py` (`run_day --thinking --spend-tokens`); each run's query, paid call and receipts in its `thinking/` folder; the season fits in `data/studies/master_pipeline/thinking/<instance>/season<Y>/` |
| The data checks | `data/studies/master_pipeline/data_check/`: each check's table and gaps, and the Stage 0 cache (`stage0/`, rebuilt when its downloads or code change) |
| The bet sheets | `predictions/<day>/bet_sheet_*.xlsx`; their records, provenance and the daily engine's archive in `predictions/<day>/records/` |
| The Pinnacle recorder | `src/ingest/pinnacle.py`; raw `data/raw/pinnacle/<day>/`, staged `data/dump/odds/pinnacle/pulls/<day>/` |
| Logs, receipts, matchups CSVs, Thinking records | `data/studies/master_pipeline/` |
| Tests | `test/master_pipeline/` (`./python.sh -m pytest test/master_pipeline -q`, 46 tests on 14 Oct, about 4 minutes on a busy machine; `test_qualifying.py`, 8 offline tests, since 22 Oct; `test_code_guard.py`, 10 offline tests of the stale-kernel refusal, since 23 Oct); Thinking's step: `test/daily_prediction/test_thinking.py` (6 tests, offline, 20 Oct) |

Nothing outside these, this folder and two index rows (`docs/studies/README.md`, `scripts/README.md`) was created or edited. No git command changed anything.
