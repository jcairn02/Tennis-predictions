# The master pipeline notebook: data → model → predictions, without asking an LLM

11 October 2026, **updated 13 October: the bet-time output is now the bet sheet** ([below](#the-bet-sheet-a5); process log, Part 2) · For the owner · Process log: [process_log.md](process_log.md) · The design as the critics saw it: [design_v1.md](design_v1.md); briefs: [subagent_briefs.md](subagent_briefs.md) · **Not a decision:** the notebook runs the current best model as decided and changes nothing in its recipe.

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
  * **tabpfn35** is the current best model: local TabPFN-3.5, 57 inputs, seeds 0–15, and stage 2 with its walk-forward calibration slope. It works today.
  * **tabpfn35_thinking** is ready on the retrain side: a free cost quote of the season fit, then the one paid fit when you say so. Daily predictions with it wait for two things:
    * the daily_prediction session's `--model thinking`, which we agreed it builds, since it owns the fit;
    * your decisions below.

    Until then the predict cell says exactly what it waits for.
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

## A bet day, in seven cells

| Cell | Call | What it does | Time |
|---|---|---|---|
| A1 | `tp.morning_refresh()` | Refetches results and serve speeds if older than 6 h; shows held files and alerts | seconds (minutes if it runs) |
| A2 | `tp.record_pinnacle()`, `tp.todays_matches()` | Pinnacle's listing now (three paced requests, raw copies and receipts); each match linked or left out with its reason | ~10 s |
| A3 | `tp.build_matchups(matches)`, `tp.check_matchups(...)` | The matchups CSV (`only=` / `drop=` to choose); the daily pipeline's own refusals checked first | seconds |
| A3b | `tp.data_check(MATCHUPS)` | **Since 13 Oct:** the run's gate applied before the run, [below](#the-data-check-a3b) | ~100 s; ~20 s when nothing new was downloaded |
| A4 | `tp.predict_day(MATCHUPS, model=MODEL)` | The template check, then the daily pipeline's `run_day --refresh` (seeds 0–15) in a new run folder and the notebook's own work tree | ~7 min warm; the first run on new tables 23 min (11 Oct) |
| A5 | `tp.bet_diagnostics(RUN)` | The bet sheet, below | seconds |
| A6 | `tp.reprice(RUN)` | A new Pinnacle price, read off the run's stored curve (no refit), then a new bet sheet | seconds |

If Pinnacle doesn't list a match, use `tp.manual_matchups([...])` with both players' odds, American or decimal; the margin is kept for EV. BetOnline's line stands in only while Pinnacle has none.

If a run is stopped midway, the notebook removes its work tree with the daily pipeline's own cleanup. `tp.cleanup_work_tree()` does it by hand. Never delete that folder by hand: it holds links to the repository's `data/raw` and `data/dump`.

## The data check (A3b)

Made 13 Oct after your question: *"Why would there be no box score? … wouldnt it make sense to wire up obtaining the necessary data … such that theres a logical flow in the master script"*.

**Why the three 11 Oct matches were blocked.** Tennis My Life *had* the Laver Cup box scores. Our Stage 0 rejected two of them, which blocked three matches: it read the 10-8 and 13-11 match tiebreaks as full sets, so the box scores looked like part of a 41- and a 43-game match. That reading is now repaired, as you approved ([decision](../../decisions/2026-10-13-match-tiebreak-reading.md)). Exactly those 2 matches change in all of Stage 0.

**The check** (`src/pipeline/readiness.py`) tells you before the 10-minute run which matches the run's gate will block.
* **It reads what the run reads:**
  * Stage 0 built now on the downloads on disk, by the run's own builder, into a cache (never the shared tables);
  * the lower-level packages and feeds merged in, by the run's own merge.
* **It applies the gate's rule:** every earlier match of either player, at the event or in the 14 days before, needs a usable box score, and a qualifier needs a qualifying match.
* **Each match is "ready", "ready once filled" or "will be blocked"** ("ready once filled": the run fills a women's box score from the WTA's own feed), with the cause and what fixes it:

| Cause | What fixes it |
|---|---|
| Tennis My Life has none yet | Wait, run A1 again, then A3b. Women's tour matches after 8 Oct: the run fills them itself. Men's: no other source yet |
| Tennis My Life has it, but our consistency check rejected it | A data repair (as for the Laver Cup); blocked until then |
| A match from the lower-level feed lacks one | Its source's next publication, taken at the feed's next snapshot (B8) |
| A qualifier without a qualifying match | Nothing on the day |

**It agrees with the real gate.** On the 11 Oct run's own Stage 0 and matchups it blocks the same three matches, for the same cause, after checking the same number of earlier matches; a test holds it to that. On today's repaired data the same eight are all ready.

**The run stays the authority.** It downloads once more, then decides with its own gate, which also checks the indoor input that only the run builds. The check errs toward a block: a match missing from the shared timeline gets a cautious window.

## The bet sheet (A5)

Made 13 Oct after your question: *"if I were a businessman looking at this information … which side to bet, and by how much?"* The 11 Oct file had 53 columns. The decision sat in columns 40–46, every number carried up to 16 decimals, and the players were Stage 0's sides, not Pinnacle's order. The same three run warnings repeated on every row, and times were in UTC.

**What changed is the presentation only.** Rebuilt from the same run at the same times, the two 11 Oct files are reproduced exactly: 52 of 52 columns, 81 and 31 rows. The one difference is intended: the run's notes are said once, in the header, instead of on every row.

* **The file:** `predictions/<day>/bet_sheet_<made>.xlsx`, a new one each call. Its sheets:
  * **Bet sheet:** one row per match, BET first, then PASS, then BLOCKED, colour-coded. A row gives the start in your time zone, the match as Pinnacle lists it, the decision and the player, the stake, Pinnacle's odds (decimal and US), the lowest odds still worth taking (1 / model chance), the model's and the market's chance, the edge in points, the expected profit, the event, and a plain note: why a PASS or a block, or a thin edge.
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

### The record behind it (`records/bet_sheet_<made>.csv`)

Everything is side A / side B as the daily pipeline's Stage 0 fixes them; the names come from Stage 0's own player rows.

| Group | Columns |
|---|---|
| The match | day, start (UTC), minutes to start, tour, event, round, best of, surface, indoor (and its source) |
| The price | source, quote time and age, Pinnacle's odds for both players (with its margin), overround, the margin-free price the model was fed (`p_market_a`), Pinnacle's stake limit |
| The model | `p_base_a` (stage 1), `eta`, `spd_L` with each man's serve-speed readings in 28 days, `q_a`/`q_b` (both stages: the forecast), fair odds 1/q for both, the spread of the 16 seeds |
| The patterns (since 13 Oct 2026) | The five-pattern adjustment ([decision](../../decisions/2026-10-13-five-pattern-adjustment.md)): `patterns` (on/off), `q_a_patterns_off` and `q_a_patterns_on` (`q_a` is the one used), `pattern_shift_pts_a`, the decision without it (`pick_patterns_off`, `ev_a_pinnacle_patterns_off`, `ev_b_pinnacle_patterns_off`), and `patterns_effect` ("bet only with the patterns", "the patterns remove this bet", "the patterns switch the side"). The sheet shows "Model chance without patterns" and says in Notes when the patterns make or switch a bet |
| The bet | `edge_a` = q − p; the **pick** is the side whose EV at Pinnacle's own odds, margin included, is positive; `min_odds_to_bet` = 1/q, the least odds still +EV at any venue before fees; its EV at Pinnacle; EV at another venue when you pass its prices (`venue_prices={...}`: odds, or a Polymarket share price) |
| Break-even | every side-A price where the model's curve crosses q = p, the one nearest the current price, or "none in [0.05, 0.95]". Curves cross 0 to 3 times (a replay: 6, 9, 1 and 7 matches) |
| Blocked | no pick and no EV when:<br>• the gate says do not bet<br>• not a main-tour match, or an unsupported format<br>• the match has started<br>• the quote is over 30 min old<br>• a price or player read-back mismatch<br>• a new price off the curve<br>• no bookmaker odds with their margin, without which EV would flatter every pick |
| Warnings | this match's own: a player new since Stage 0, seeds that disagree, missing speed form. The run's own notes (the history check, recomputed state parts, an unclean results download) go to the provenance and the sheet's header since 13 Oct |
| Not predicted | one row per listed match of the window that was left out, with the reason |

A stake column appears with `stake_rule="owner_8oct"`: your 8 Oct research rule in units, labelled as research. The notebook sets it since 13 Oct (decision 7). No staking rule is decided.

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

* **First rounds can't be predicted.** The daily pipeline needs a played match of the event, so tomorrow's Wuhan first round waits.
* **14 active players can't be predicted.** Their name keys point to two Stage 0 ids (decision 3).
* **Thinking's daily predictions are not wired yet** (above).
* **The daily pipeline can't be switched to a new instance from the notebook.** Its session is adding `DP_INSTANCE`; until then `use_instance()` lists the steps.
* **Stage 2 reads the weekly speed set** (decision 2).
* **The gate marks women who came through qualifying "do not bet".** Tennis My Life has no WTA qualifying since June.
* **BetOnline's line, when Pinnacle has none, is entered by hand** (`manual_matchups`).
* **The notebook checks names against the shared Stage 0 of 8 Oct.** A player new since then is found in Tennis My Life's rows instead, and the run's own refreshed Stage 0 holds them.

## Decisions for you

| # | Question | My recommendation |
|---|---|---|
| 1 | **Thinking:** approve paid use? | **Yes, in steps.** First the free quote (C9; it costs nothing). Then one paid fit for 2026, about 180k tokens billed (an estimate from past receipts). Then daily predictions on that saved fit, about 30k tokens a day, seed 0 only. Use stage 2's 8 Oct research rule (η + the local b̃·spd_L, no slope; Thinking's own slope was 0.99), labelled research, with no edge credit, until paid back-season fits (about 1.3M billed) allow a calibrated slope. One fit per season rather than refitting daily (the in-season policy would cost about 5.5M a month for a gain of 0.001–0.01 mLL). The API's terms for betting use were not checked. **13 Oct, at your request:** the 2026 fit was made on the active instance (181,901 tokens; `thinking/template_2026-10-10/season2026/fit.json`), and today's five Shanghai matches were predicted with it, uncalibrated (one call, 31,572 tokens; `src/eda/thinking_live_compare/`; process log Part 3). Daily Thinking predictions are still not wired. |
| 2 | Stage 2's speed set: the decision says `spd_L_D` once the daily collector runs, and it has run daily since 8 Oct; the code still uses `spd_L_B` | **Switch live runs to `spd_L_D`** as the decision says, replays before 8 Oct keeping `spd_L_B`. It changes predictions, so it is yours. The daily_prediction session is asking you too. |
| 3 | 14 active players with two Stage 0 ids (Mensik, Landaluce, Gigante, …) | **Two fixes.** The daily pipeline should take each player's id from the matchups CSV (my CSV already carries `stage0_id_a/b`). The duplicates should be merged as a repair, through the candidate route since some rows are lower-level. |
| 4 | The rebuild sandbox copies `data/studies` whole, including 55 GB of TabPFN caches (disk: 106–119 GB free) | **Exclude `daily_prediction`, `prediction_run` and `master_pipeline` from `run_chain`'s copy.** It changes no output. Until then `build_instance` refuses below 130 GB free, with this explanation. |
| 5 | A Pinnacle cadence: pulls are by hand today | **Add a pull to the scheduled task during events** (hourly, plus near match starts). It records a price history and the closing lines your 9 Oct decision would retrain on. Cadence is a download decision, so it is yours. |
| 6 | Where the layer lives (CLAUDE.md's table has no row for it) | **Add a row:** "Operator pipeline (the notebook's functions): `src/pipeline/`". |
| 7 | A stake column | ~~Leave it off until a staking rule is decided.~~ **13 Oct: shown**, since you asked "by how much?". It uses your 8 Oct research rule, which sizes by the price only, labelled on the sheet; `STAKE_RULE = None` hides it. **Still open:** a decided staking rule, and whether a bet needs a minimum expected profit. Today any +EV counts, even Fils' +0.3% on 11 Oct, which the sheet flags as thin. |
| 8 | The four held Tennis My Life Challenger files (2022–2025; rows vanished upstream) | Review them before accepting (B2). They are lower-level data, so accepting one changes the lower-level history. Nothing in this work touched them.<br>**Done 13 Oct (owner's word; [decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)):** checked by a scratch rebuild ([report](../tml_revisions/README.md)): cleanup, not damage. 24 Stage 0 matches change, all men's Challengers: duplicates removed, a misplaced match restored, keys rebuilt. No main-tour match changes. Accepted at 18:48. |
| 9 | Today's diagnostics warn on every row: "history check: the lower-level history differs from the reference". On 11 Oct, Tennis My Life corrected 50 old lower-level matches; nothing was newly played (lookup of 11 Oct, process log):<br>• **30 re-identified:** who played, mostly 2011 Rome and Umag qualifying, where the frozen copy has 24 unnamed placeholder ids.<br>• **One duplicate id merged:** Andre Ilagan, who then has one id.<br>• **18 ages fixed:** Ilagan was recorded as 56 in 15 Challengers (now 25.6), Miguel Tobon as 58 in 3 (now 20.2).<br>• **None of today's 8 predicted players is touched.**<br>A template build would refuse this; the live path builds from the day's data and only reports it. The daily_prediction session is putting three options to you: hold lower-level history at the 8 Oct freeze in live runs, accept the revisions, or refuse such runs | **Accept them, under a standing policy** (revised 11 Oct, after your question). The level-layer decision of 10 Oct already settled how men's Challenger and qualifying data enters (translated by opponent strength, weighted). The proposed policy covers lower-level data from the feeds that route was validated on (new rows, corrections, backfills):<br>• It enters by itself: in live runs at once, in training at the next instance rebuild.<br>• The history check keeps listing every change, and a harm check runs at each rebuild.<br>• The candidate step stays for new kinds only: ITF box scores (the P7 test), new sources, women's lower levels.<br>Without such a policy: hold at the freeze (the daily_prediction session's option 1). Until you decide, the diagnostics warn and do not block.<br>**Retraining for these 50 alone: not now** (owner's question, 11 Oct):<br>• **Small reach:** 97 players are touched, in 6,402 of the 62,869 rows the 2026 fit trains on, but only through one to three old qualifying results each in long-memory ratings. The effect is likely far below what a comparison can resolve (an inference, not measured).<br>• **Live runs already use the corrections.**<br>• **The cost is not the GPU:** ~4 h of build, a shared-table rebuild, ~75 GB of sandbox on ~100 GB free, and a new checkpoint and caches.<br>• **Batch it with the next rebuild that matters:** P7's ITF test, Pinnacle's missing closes, the in-season fit, or the 2027 rollover.<br>**Decided 13 Oct by the owner: accept them under the standing policy, no retrain for them alone** ("record the decision and run the check on the four files"; [decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)). `history.py` lists Tennis My Life's own lower-level changes as `tml_lower` and no longer refuses a build for them. The bet sheet's note was still calling this open; that wording is being changed. |

## Files

| What | Where |
|---|---|
| The notebook | `scripts/master_pipeline.ipynb` (kernel: the `tennis` conda env) |
| The layer | `src/pipeline/`:<br>• `config` (paths, interpreters read from the shims)<br>• `runner` (streamed steps, logs, receipts, dry runs)<br>• `overview` (status)<br>• `data`, `train`, `live`, `predict`, `diagnostics` (the record)<br>• `bet_sheet` (the sheet, the workbook, the notebook's view; since 13 Oct)<br>• `readiness` (the data check, `tp.data_check`; since 13 Oct)<br>• `thinking` and `thinking_api` (season fits) |
| The data checks | `data/studies/master_pipeline/data_check/`: each check's table and gaps, and the Stage 0 cache (`stage0/`, rebuilt when its downloads or code change) |
| The bet sheets | `predictions/<day>/bet_sheet_*.xlsx`; their records, provenance and the daily engine's archive in `predictions/<day>/records/` |
| The Pinnacle recorder | `src/ingest/pinnacle.py`; raw `data/raw/pinnacle/<day>/`, staged `data/dump/odds/pinnacle/pulls/<day>/` |
| Logs, receipts, matchups CSVs, Thinking records | `data/studies/master_pipeline/` |
| Tests | `test/master_pipeline/` (`./python.sh -m pytest test/master_pipeline -q`, 38 tests on 13 Oct, about 40 s) |

Nothing outside these, this folder and two index rows (`docs/studies/README.md`, `scripts/README.md`) was created or edited. No git command changed anything.
