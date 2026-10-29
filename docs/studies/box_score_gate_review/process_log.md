# The box-score gate of 8 Oct 2026, reviewed: process log

13 October 2026 (PDT), started 21:40 · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) · Session:
`f66b9e99-f90d-40a5-b5fe-c347536062c5` (peer name `tennis-predictions-b2`) · For a future reviewer · Report:
[README.md](README.md) (written at the end)

## 1. The request

* **The owner's words, verbatim** (13 Oct 2026, about 21:35 PDT), after being told why the bet sheet withholds a bet when
  an earlier match lacks a box score:
  > "The oct 8 rule wasnt written by me it was written by an agent I gave authority. It could have been wrong and may
  > have made a major error in the practicality of the rule.
  > Do a deep exploration and see if that rule should be modified, what its original intention was, if it was misguided
  > and what you recommend we change it to.
  >
  > "40 of the model's 57 inputs come from the players' recent box scores (aces, serve points won, breaks, and so on).
  > If one is missing, the model doesn't know. It quietly skips that match, and the player's recent-form numbers drift
  > toward average."
  >
  > This seems incredibly bad?"
* **The owner's earlier words in this session** (verbatim): "Why is it blocking data? thats annoying". Before that, on the
  11 Oct blocks: "Why would there be no box score? if we were running predictions, wouldnt it make sense to wire up
  obtaining the necessary data to getting the predictions? ..." (master-pipeline process log, Part 2).
* **How it was read:**
  * **"The oct 8 rule":** point 3 of `docs/decisions/2026-10-08-prediction-run-box-scores.md`, the gate. For each upcoming
    match, every finished match of either player at the event, or in the last 14 days, must have a box score, or the
    match is marked not to bet. Since 9 Oct, an unknown indoor input also fails it, and since about 8 Oct a qualifier
    with no qualifying match (`src/eda/prediction_run/gate.py`).
  * **The four questions:**
    1. the rule's original intention;
    2. whether it was misguided, in principle and in practice;
    3. whether it should change;
    4. what to change it to.
  * **"This seems incredibly bad?":** a fifth question about the inputs themselves. Is skipping a missing box score, and
    shrinking a player's recent-form numbers toward average, a defect of the model's inputs, at bet time and in
    training? It is answered on the evidence, not on the phrasing.
  * **Authority:** the owner says the decision record's agent-written parts were the agent's, not the owner's. The
    record itself is not edited; any change is recommended, and the owner decides.
* **Readings set aside:** a rewrite of the feature families' missing-data treatment (that would be a model change, to
  the feature pool by the adoption rules), unless the evidence shows the treatment is a defect worth a repair.
* **The target** (adoption framework § 1):
  * the price: Pinnacle's current line at bet time, hours before the match, margin removed (the decided live input);
  * the matches: main-tour singles that the bet day predicts;
  * the seasons: the live 2026 season, plus the frame's seasons where history is simulated.
  * **What decides:** the gate is a betting rule, not a model change. Its value is the forecast error it prevents (how
    far a missing box score moves q) against the bets it withholds (how often it fires, and why).

## 2. Starting point

* **Code:** commit `677a63f`, with many uncommitted changes from other sessions. Today, other sessions changed
  `history.py`, `additions.py`, the lower-level feed and the daily engine. This session changed Stage 0's match-tiebreak
  reading (decision `2026-10-13-match-tiebreak-reading.md`) and added the bet-day data check.
* **Data:** the shared Stage 0, built 8 Oct; the shared timeline, refreshed 13 Oct 16:11; the frozen reference of
  8 Oct; the current instance `template_2026-10-13` (decision `2026-10-13-lower-level-feed.md`); the live runs of
  11 Oct and 13 Oct.
* **Earlier looks:** the prediction-run study (the gate's design and first live run); Stage B's recency diagnostic
  (`docs/studies/ufc_ideas/stageB.md`), the measurement behind the rule; the daily-prediction study's replay proofs.
* **Environment:** `tennis` env (pandas 3.0.6); the local TabPFN env for replays (RTX 5090; 7.6 GB in use and 2% busy
  at 21:39); 246 GB free on C:.
* **How the question arose:** the owner's frustration with a blocked bet. The only live blocks so far, three on 11 Oct,
  came from a Stage 0 parsing bug (repaired today), not from missing data.

## 3. Plan

1. **Intention and history** (documents; read-only subagents in parallel, briefs in the appendix):
   * what the owner asked;
   * what the agent chose, and why;
   * what was measured;
   * which parts were the owner's choices.
2. **Mechanics:** how a missing box score enters each of the 40 box-score inputs. Is the treatment the same in
   training? How much does one match weigh?
3. **Practical cost:** the gate simulated over past main-tour matches (2024 to 2026) on today's tables: how often it
   would have withheld a bet, and for which cause.
4. **Benefit:** the forecast's actual sensitivity. A past day is replayed through the daily engine as live rows, then
   replayed again with chosen box scores removed after the tables step, and q is compared match by match. The engine's
   steps are its CLI, the runs and work tree are this study's own, and nothing shared is written.
5. **Recommendation:** what the rule should be, with the evidence and the trade-off. The decision is the owner's.

## 4. Chronology

Local time (PDT, UTC−7), read from the clock unless marked "about". "Results" means any model output read.

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 21:39 | Clock, GPU (RTX 5090, 7.6 GB used, 2%), disk (246 GB free); related study folders listed | Feasibility | none | § 2 |
| 21:42 | Three read-only subagents launched in parallel (briefs verbatim in the appendix): H (history and intent), M (mechanics of missing box scores in the inputs), C (the measurement behind the rule) | Plan step 1–2 | none | — |
| 21:45–21:52 | `src/eda/box_score_gate_review/simulate_gate.py` written. It applies the gate's rule (its constants imported from `gate.py` and `prediction_run.common`) to every completed main-tour singles match (GS, Finals, 1000s, 500s, 250s; no qualifying, no team events) of 2024 to 7 Oct 2026, as if each were predicted live, on today's tables: the data check's repaired Stage 0 plus the accepted packages and the lower-level feed (`readiness.tables`). A target's day is the timeline's best start, else its anchor. First run: a column-name error (merge suffixes); fixed | Plan step 3 | none | — |
| 22:08 | **Bet-time gaps in the three live runs (observed, each run's `gaps.csv` from its refresh):** 11 Oct, 43 gaps: 3 WTA Beijing "fillable" (filled from the WTA API), 39 "held" (36 ATP and 1 WTA team-event matches, 1 ATP 1000 and 1 ATP 500 the frozen reference holds without a box score), 1 unserved team match. 13 Oct (two runs), 40: the same held and unserved ones, no fill needed | What a bet day actually meets | none | — |
| 22:12 | **Subagent C reported** (taken as reported; its file:line citations not all re-read). **The measurement behind the rule** (`ufc_ideas/stageB.md:172-197`) was a two-input logistic model (surface Elo plus one form column, the two-week adjperf of total points won), **without a market price**. It removed **every** same-event earlier round for **every** match, refitting each variant on its own definition: men 3.19 (2.85–3.54) → 2.09 (1.81–2.38), women 3.32 → 1.83. That measures the rounds' information, not one gap's effect on one forecast. **The same harness given the market close:** men 0.14 (−0.12 to 0.39) → 0.11 (−0.05 to 0.26), women −0.07 → −0.08: no detectable difference. **The current model** (edge_anatomy, 12 Oct, `template_2026-10-10`): the whole 17-input form family adds +0.14 [−0.35, +0.63] mLL beyond Pinnacle's price in 2025–26 (+0.30 [+0.05, +0.54] in 2020–24); the IOS profile +0.26 / +0.29. No study had measured a single gap's effect: this study's replay is the first | Plan step 1 | none (other studies' readings) | — |
| 22:14 | **Subagent H reported** (taken as reported; the decision's lines re-read by the lead earlier today). **The owner's 8 Oct words** (decision lines 3–5): "Make live inputs match what the model was trained on. Every prediction run should refresh box scores first ...". They name no gate, no blocking, no 14 days, no other events, no levels, no qualifying. The owner approved "the gate" by name among "Steps 1–4" (line 11). **Its content was the agent's design:** the 14-day window (`common.py:31` "the two-week profile's span": a half-life used as a span), every level including team events (no filter in `gate.py:67-70`), other events, the qualifying rule, the indoor rule, and "do not bet". None of these is marked as Claude's choice; a later session called the gate "the owner's policy". **Evidence:** the "98.4–99.7%" covers same-event rounds only, and no script for it was found. No alternative to blocking (warnings, down-weighting, imputation, partial blocks) is recorded. **Practicality:** 3 of 15 live matches blocked so far, all on 11 Oct (both Laver Cup causes: Stage 0's misreading and the 7-day window to 29 Sep). The 15 Jul replay: 3 of 23 blocked (women qualifiers); after today's feed, 2 of 23 (women's ITF W50/W100 box scores; replay `20261013T205131`). The gate requires ITF box scores although ITF box scores are not men's inputs (level-layer decision) | Plan step 1 | none | — |
| 22:20 | **The gate over the whole training span** (`simulate_gate.py --first 2013 --tag _2013`, observed). On today's tables, the main-tour matches with at least one permanent gap in the gate's window: **ATP 1.2–21.9% a season** (2013 13.7, 2015 21.9, 2016–2025 1.2–7.9); **WTA 9.2–64.4%** (2013 49.3, 2014 37.5, 2015 64.4, 2016–2023 11.1–21.2). The model trains on 2013 to Y−1, so its training rows carry these gaps at these rates. "Every earlier match must have a box score, as in training" was never true of training outside the same event's rounds of 2019–2025 | Plan step 3 | none (no model output) | `gate_simulation_2013.json` |
| 22:25 | **Subagent M reported** (taken as reported; the two-week form formula re-read in its brief's terms). In all 40 box-score inputs, a match without a box score gets weight 0: never imputed, never zero-filled, and the same code builds training and live rows. **Two-week forms:** value = Σ w·z / (Σ w + K3), w = 2^(−age/2 weeks), prior 0. K3 = 10 (men) or 20 (women) on the serve-side forms and adjperf_tpw_2w, 160 on the return forms and formdef. With three matches at the event, the newest carries 7.7%, 4.3% or 0.6% of the value, and the prior 77%, 87% or 98%. **Surface IOS:** a ridge toward 0, half-lives of 26–208 weeks or infinite; one match is about 2% for an active player, under 1% at the long half-lives, up to 25% for a newcomer. **ratings_iid:** a Glicko-style update, about 4–5% per match for an active player. **points_52w:** about 2%. **No input says how much evidence a value rests on.** For men, the level layer gives ITF box scores weight 0, the same as missing | Plan step 2 | none | — |
| 22:15–22:35 | **Replay setup failed at the tables step's `additions`** ("the merge made duplicate match ids, sides or timeline rows"). Cause (observed): the shared Stage 0 and timeline were rebuilt tonight, 21:13 and 21:16, by another session (B6-style; with today's accepted Tennis My Life files and this session's match-tiebreak repair). The timeline every work tree copies now dates 43 lower-level matches that a replay's frozen dump lacks and the feed adds, so their rows collide. **The engine's replays fail since then**; to be reported. The other session's replay of 20:51 ran before the rebuild. **Workaround in this study's tree only** (`replay_gaps.py retry_tables`): the tree's timeline trimmed to its frozen Stage 0's matches (873,636 → 873,339 rows), the state the 20:51 replay ran in. The replay holds the instance's timeline after the steps, so the trim feeds only the steps between. The failed attempt's scratch was kept as `run_failed_1`. The tables step then passed | Bug outside this study | none | `replay_retry.log` |
| 22:36 | Removals chosen (`removals.csv`): **same_event** one per live match (23); **other_event** 20 (3 live matches with no other-event match in the window are controls); **all_window** 94 matches over the 23 live matches. Four replays launched (base and three scenarios; states, fit and predict each; seeds 0–15) | Plan step 4 | none | running |
| — | **Correction (added 22:02 PDT, clock read with `date`):** the rows timed 22:05 to 22:36 (above and below) were timed by estimate and run ahead of the clock; it read 22:01 when this was noticed. Their order is right, except that the design row ("22:05") was written before the setup started. Real times, from file timestamps: design about 21:45; setup started 21:46 (`replay/base/run.json`); first tables attempt failed about 21:50; gaps lookup and subagents C, H and M about 21:47–21:54; the 2013 simulation about 21:52; the retried tables step 21:53–21:57 (`replay/base/tables.json` 21:57:37); the four replays launched 21:57. From here every time is read from the clock | Rule 4 (correct by adding) | — | this row |
| 22:02 | **Tonight's shared rebuild (21:13) restored Roland Garros 2026** (observed: 241 of 241 main-draw matches with full box scores, RG's own record under the 9 Oct decision; still partial: WTA Berlin 25 matches, WTA Nottingham 30 of 91). The data check's Stage 0 cache (21:03), on which the first simulations ran, predates it. **Simulation re-run on tonight's shared Stage 0** (`--stage0 data/studies/predictability_diagnostic`, tags `_now`, `_now2013`). 2024–2026: ATP 2.5 / 5.5 / **5.4%**, WTA 12.3 / 9.2 / **20.0%**; 2013–2026 as before (ATP 1.2–21.9%, WTA 9.2–64.4% a season). **Alternative rules, 2024–2026:** the current gate ATP 4.4%, WTA 13.7%; same-event gaps only 0.0 / 1.7%; main-tour gaps only 0.0 / 2.7%; same-event main-tour only 0.0 / 0.5%; the qualifier rule 0.2 / 0.4%. For men, every remaining block comes from team events, Challengers, ITF or qualifying. Superseded readings kept: `gate_simulation{,_2013}.*` (21:03 tables) | Correctness of the cost reading | none | `gate_simulation_now*.{json,parquet}` |
| 22:05 | **The replay experiment, designed before any of its output** (`src/eda/box_score_gate_review/replay_gaps.py`). The daily engine's own CLI steps, the active instance (`template_2026-10-13`, its build tree `tnr_gaps`, checkpoint 22 Jun), this study's own work tree (`C:/Users/zerom/tnr_gate_review`) and run folders (`data/studies/box_score_gate_review/replay/`). The day replayed is 13 Jul 2026's round of 16 (the engine's proof day: 23 matches at Bastad, Gstaad, Umag, Athens and Iasi), with seeds 0–15. Four scenarios share the tables step, and each removes box scores from the tree's Stage 0 the way Stage 0 drops one, then runs states, fit and predict: **base** (none); **same_event** (each live match: the most recent earlier round at the event, side A's player, else B's); **other_event** (the most recent match at another event within the gate's window, else none: such matches are controls for spill-over through the joint IOS solves); **all_window** (every earlier match in the window, both players). **Reading, fixed now:** \|Δq\| in percentage points per live match with a removal, against the controls' \|Δq\| (spill-over) and against the size of a typical edge (the 11 Oct sheet: edges of 2–3.5 pts). A gap that moves q by well under a point does not justify withholding a bet; one that often moves it by 2 or more does | Plan step 4 | none | — |
| 21:53 | **The gate's practical cost (observed; permanent gaps only, so a lower bound):** blocked share of main-tour matches, ATP 2.5% (2024), 5.5% (2025), 10.9% (2026); **WTA 12.3%, 9.2%, 24.5%**. The matches whose missing box scores cause the blocks: team events (ATP 264, WTA 230 blocked matches), ITF (WTA 402), main-tour events (ATP 121, WTA 304), qualifying (WTA 160). Largest single causes: **Roland Garros 2026** (no box scores in Tennis My Life: 121 WTA + 120 ATP matches blocked after it), WTA Berlin and Nottingham 2026 (partial: 96 + 91), BJK Cup and United Cup, ITF W100s. Every one of these gaps is permanent, so the training rows of those weeks lack the same box scores | Plan step 3 | none (no model output) | `data/studies/box_score_gate_review/gate_simulation*.{json,parquet}` |
| 22:14 | **The base scenario** ran states (21:57–22:12; gate 21 of 23 complete, as the 20:51 replay after the feed) and fit (22:12–22:14, 16 seeds, training caches). **Its predict step failed:** the combined-pattern adjustment, switched on at 21:09 tonight on the owner's instruction (`data/studies/unpriced_leads/check_now/adjustment.json`), needs its patterns step, which only `run_day` runs; the CLI's `predict` refuses without `live_patterns.parquet`. To be reported. Interim choice: read stage 1 from the fit's own output (each seed's own-price forecast, `fit/season*_seed*.npz`) and stage 2 as s_tour·η, with the speed term unchanged (no box score enters it) | Bug outside this study | none (no forecast read) | `replay_run.log` |
| 22:16 | **same_event's states step refused:** "build_config.json was resolved on another Stage 0 (its ab68b54ad272, now f0d53ee8db21)". The level layer's build config records the Stage 0 file it was resolved on (`layer_config.require_resolved`), and the removal rewrote Stage 0 | — | none | `replay_run2.log` |
| 22:20 | **Fix** (`replay_gaps.resolve_layer`): after each removal, the layer is resolved again on the tree's Stage 0 with the tree's own `layer_config.py --resolve`, as the tables step's `lle_layer` step resolves it on whatever Stage 0 a bet day has. Its strength is the plain Elo of Stage 0's results, which no box score enters, so the strength file's hash must stay the same; it is checked and logged (`replay/layer_resolves.jsonl`), and a change stops the run. The base's restore now copies the tables step's files byte for byte (the base's states ran on that file, hash ab68b54ad272). Relaunched 22:20 (`replay_run3.log`). **same_event's resolve:** strength hash unchanged (observed, 4cd73af8…), Stage 0 f0d53ee8… | Make the scenarios runnable without changing what they measure | none | `replay_run3.log` |
| 22:23 | **The reading widened to the forecast the bet sheet shows, before any scenario output.** The pattern adjustment's members include venue pace × ace offence (aces are box-score counts) and read the tree's tables (`unpriced_leads/live_members.py`), so a removal can move its z; the s_tour·η reading would miss that. Added `replay_gaps.py finish`: per scenario, Stage 0 set again, the layer resolved, the engine's patterns step (`dp_steps.step_patterns`), then the CLI's `predict`. `compare` reads `predictions.csv`'s q_a (stage 2 with its speed and pattern terms) when all four scenarios have it, and s_tour·η otherwise; it reports both, plus q without the patterns, z's change, and stage 1 checked against the fit's own reading. The decision rule of the 22:05 row is unchanged | Measure the forecast actually bet | none | — |
| 22:29 | **Classification and decision rule, fixed before any scenario output** (no scenario has a fit yet; the base's forecasts not read). **Kind:** the gate is a betting rule, not an input or a model change: it changes which forecasts are bet, never a forecast. The adoption framework's kinds are for model changes; the nearest is a **repair** (the owner's words named the same event's earlier rounds and training parity; the rest is unmeasured design), so the expected direction is "narrowing loses little", and what decides is the forecast error a gap causes against the bets the gate withholds. **Two questions, decided separately:** (1) *which gaps differ from training* (decided on the cost simulation and the training rates, not on the replay): a main-tour box score (same event or in the window) is present in 98.4-99.7% of training rows' same-event rounds, so a live gap there is a live-vs-training difference; team events, Challengers, ITF and qualifying box scores are missing in training at the rates the simulation shows, so their gaps are not. (2) *whether such a gap matters* (the replay): **primary reading** same_event's \|Δq\| on the forecast the sheet shows (q_a), over the live matches with a removal; all_window (every window box score of both players) as the worst case; other_event for one other-event match. **Mapping:** if same_event's 90th percentile is at least 1 point, or all_window's median is at least 1 point, main-tour gaps keep blocking (narrowed scope); otherwise they become a warning with a re-run after the fill, and nothing blocks for a single gap. 1 point is a third to a half of the 11 Oct sheet's edges (2-3.5 points). With 23 matches (about 20 with a removal), the percentiles are rough: a reading near a threshold is reported as such, not forced | Adoption framework § 0 and § 1 | none | — |
| 22:31 | **Training's own box-score coverage, measured** (`src/eda/box_score_gate_review/coverage.py`, tonight's shared Stage 0, completed singles; observed). Pooled 2013-2025: **main tour** ATP 100.0%, WTA 96.1% (WTA 77-90% in 2013-2015, 99-100% from 2016); **Challenger / WTA 125** ATP 99.5%, WTA 94.1%; **men's qualifying** 94.1%; **women's qualifying** 18.7% (9-14% a season in 2019-2024, 100% in 2025); **team events** ATP 48.1%, WTA 53.6% (0-100% by season); **ITF** 7.7% / 8.3% (0% to 2024, 94-95% in 2025 from today's feed). So the kinds training nearly always holds are the main tour, Challengers / WTA 125 and the men's qualifying; a gap of any other kind looks like thousands of training rows. This replaces the unscripted "98.4-99.7%" as the evidence for which gaps differ from training | Question (1) of the 22:29 row | none (no forecast) | `coverage.csv` |
| 22:33 | **Narrower scopes, counted** (`scopes.py` on the `_now` simulation, 2024-2026, with the qualifier rule; observed). Share of main-tour matches withheld, ATP / WTA: the current gate **4.4 / 13.7%**; **near-complete kinds** (main tour, Challenger / WTA 125, men's qualifying) **0.5 / 3.3%**; main tour only 0.2 / 3.2%; same event's main-draw rounds only 0.2 / 1.0%. The near-complete scope's WTA 2026 reading (8.4%) is almost all WTA Berlin (96) and Nottingham (91) 2026, whose box scores Tennis My Life holds in part; a live run would try the WTA's own feed for them first, so live it would block less. 2013-2026: the near-complete scope blocks ATP 2.5%, WTA 7.4% (the WTA's 2013-2015 seasons, 20-29%, are the old main-tour gaps) | Question (1) | none | `scopes_now.csv`, `scopes_now2013.csv` |
| 22:38 | **Correction (by adding):** subagent H's "3 of 15 live matches blocked" (row 22:14 above) is **3 of 13** on re-count: the daily engine's three live runs' own `gate.json` (11 Oct: 8 live, 5 complete; 13 Oct 16:39: 4 of 4; 13 Oct 16:53: 1 of 1). No other live run's gate record was found (every other `gate.json` is a replay or a test of 13 Jul's round of 16). The README uses 13 | Verify a subagent's count | none | — |
| 22:41 | **First look at a scenario's output (interim; same_event only; the s_tour·η reading, without the pattern term; slopes 0.90 / 0.92, the fallback, as no live run of this instance records its own).** same_event's states recomputed 19 of 21 parts in full (the 2 Elo parts resumed: results only), and all 40 box-score inputs changed for every live match (the joint solves spread a removal). One missing earlier round at the event, the most recent: **\|Δq\| median 0.35 points, mean 0.43, 90th percentile 1.17, max 1.39; 3 of 23 matches over 1 point, all men's (1.39, 1.34, 1.31)**; women's 0.03-0.37. Signed mean +0.002: no direction. The per-seed spread is 0.36 points (median), so the 16-seed mean's own noise is about 0.09; the scenarios share the fitted models and seeds (the fit trains on the instance frame only, `dp_fit.py`: the live rows are test rows), so the differences are the inputs' alone. Against the 22:29 mapping, the 90th percentile clears 1 point narrowly (1.17, the third-largest of 23 values); the median is well under. Nothing decided on it: the final reading is q_a after `finish`, with all_window and other_event | Plan step 4 | same_event interim (this row) | `replay/compare.csv` (interim, overwritten by the final compare) |
| 22:44 | **Extension, decided after the interim reading (22:41) and marked as such:** `same_event_b`, side B's most recent earlier round at the event, per live match. Why: the interim 90th percentile (1.17) sits at the pre-registered 1-point line on 23 values, and a second single-gap removal per match is the cheapest way to widen the sample (same tree, same day, about 20 minutes). Of 19 live matches where B has an earlier round, 5 are left out: side A had a bye there, so same_event had removed B's round already. **14 new single-gap readings**, and 9 live matches with no removal serve as spill-over controls. Its removals are in `removals_ext.csv`; `removals.csv` is unchanged. **The pre-registered verdict stays on same_event alone; the extension is reported beside it, never pooled into the verdict.** Its run folder is a copy of all_window's, still untouched after the tables step (no states output in it at 22:42) | Widen the single-gap sample | same_event interim (22:41) | `replay/removals_ext.csv` |
| 06:58 (14 Oct) | **Session break, and two notes added late (correct by adding).** (1) The session's context was summarized once on 13 Oct, about 22:15 (before the layer fix); the log was re-read at 22:23. (2) About 22:50 a test of the patterns step on a scratch copy of the base run was refused (its permission request was aborted) and never ran. Then a message arrived from the tennis-predictions-af session (verbatim in the appendix): the active instance would move to template_2026-10-14 around 01:30-02:00, and on the instance its re-centred layer strength moves men's layer-fed forms by about 1e-6 whenever Stage 0 changes. The computer restarted overnight; the owner resumed at 06:52: "my computer restarted, did we have more work to be done here that wasnt finished?" **State found (observed):** run3 ended `python exit 0` (other_event, all_window); run4 ran same_event_b (exit 0), then `finish` for all five scenarios, patterns and predict, 23:23-23:32 on 13 Oct (exit 0). Every forecast is template_2026-10-13's at checkpoint 2026-06-22 (each `predictions.csv`'s own instance and checkpoint columns; the run folders pin the instance), made before the switch. The layer's strength kept one hash through all 12 resolves (`layer_resolves.jsonl`); the tree's Stage 0 ends restored byte for byte | Resume | none | `replay_run3.log`, `replay_run4.log` |
| 06:58 | **The final reading** (`replay_gaps.py compare`, observed). Reading: the predict step's own q_a, the forecast the sheet shows. **The pattern term was paused for all 23 matches** (`live_patterns.json`: five members not built for live matches had their gates on), so q_a equals q without it, and the reading is stage 1 with stage 2's scale and speed term. Stage 1 from the fit's npz equals the predict step's p_base_a in every row. Per scenario, \|Δq\| in points: **same_event** (primary; 23 removals, all main-tour R32 at the five 250-level events) median 0.35, mean 0.43, 90th percentile 1.17, max 1.41; 3 of 23 over 1 point (men only: 1.41, 1.35, 1.31); signed mean +0.002. **other_event** (20 removals: 11 Wimbledon, 9 Challenger / WTA 125) median 0.21, 90th 0.35, max 0.72, none over 1; its 3 controls moved at most 0.024. **all_window** (94 matches: 63 main tour, 20 Challenger / WTA 125, 11 qualifying; 2-7 per live match) median 0.42, mean 0.57, 90th 1.36, max 1.84; 5 of 23 over 1; signed mean -0.04. **same_event_b** (extension; 14) median 0.26, 90th 0.58, max 0.74, none over 1; its 9 controls at most 0.023. **Verdict by the 22:29 mapping (primary same_event alone):** the 90th percentile 1.17 clears 1 point, so main-tour gaps (the near-complete kinds) keep blocking, narrowed scope. It clears narrowly: the third-largest of 23 values; the extension, reported beside it, reads 0.58 | Plan step 4 | all scenarios (this row) | `replay/compare.{csv,json}` |
| 06:58 | **Decision-level analysis, designed after the reading above (post hoc, marked).** Why: the 1-point line was a stand-in for the question the gate exists for, "does withholding the bet save more than it costs?", which needs the forecasts and could not be fixed in advance in money terms. Method (`decisions.py`): the bet sheet's own rule (bet the side with positive expected profit at the bookmaker's odds, `diagnostics.bet_diagnostics`); the replay has the closing probability, not odds, so odds are built with a 2.5% or 4% margin; flat one-unit stakes; each action judged by the complete-data forecast, or by that forecast with its edge over the market halved. **Results (observed), units-% of expected profit over the matches with a removal:** the complete-data forecast bets 10 of 23 (2.5% margin; mean expected profit 3.7% a bet; base edges median 0.98 points, max 4.77). A missing round changes 4 of 23 decisions in same_event, 1 of 20 in other_event, 5 of 23 in all_window, 2 of 14 in same_event_b. Judged by the complete-data forecast, betting through costs 2.98 (same_event), 0.27, 7.29, 0.41; blocking those matches forgoes 37.17, 31.85, 37.17, 18.86 (5-118 times as much; at a 4% margin 3-11 times). **Judged with the edge halved, it is closer and flips:** at 2.5% the block forgoes 1.3-4.6 times what a gap costs, except same_event_b (0.3); at 4% the complete-data bets themselves lose (-1.03 units-% in same_event), so a block "saves" money only because betting loses | Whether the pre-registered verdict serves its purpose | all scenarios | `replay/decisions.csv` |
| 06:58 | **A third rule, designed after the reading (post hoc, marked): the edge buffer.** A gapped match is bet only if its edge clears a margin about the size a gap moves the forecast (1 point: the primary's 90th percentile, 1.17, rounded down; 1.5 tried beside it, never tuned on profit). Expected profit, units-% (same_event; 2.5% margin): bet through 34.2, buffer 1 point 28.2, buffer 1.5 18.3, block 0 (complete data 37.2), judged by the complete-data forecast; judged with the edge halved: buffer 1 point 8.0, complete data 6.4, bet through 2.5, block 0; at 4% with the edge halved: buffer 2.5, block 0, bet through -3.1. Across the 16 cells (4 scenarios x 2 margins x 2 judges) the 1-point buffer beats a block in 15 (the 16th: -0.12 against 0) and is best or second-best in every judge-margin pair. **Caveat:** where the edge is halved, part of the buffer's gain is a minimum edge as such, which would help every bet, gapped or not: that is a stake question for all bets, not a gate question. 23 matches and about 10 bets: these sums illustrate the structure (a block forfeits whole bets; a gap moves a forecast by a fraction of a typical edge); they are not a test | A recommendation that holds whether the edges are real or overstated | all scenarios | — |
| 06:58 | **The recommendation, and where it departs from the pre-registered verdict.** The scope: narrow to the kinds training nearly always has (decided on the coverage evidence, 22:31-22:33, before any forecast). The action for those kinds: the 22:29 mapping gives "keep blocking" (narrowly). **I recommend the 1-point edge buffer instead,** a departure the framework allows (principles, not rules), for the reasons in the two rows above: the mapping's line stood in for the profit question, and answered directly a block costs more than it protects unless the model's edges are overstated, a case the buffer also handles. The narrowed block is presented to the owner as the alternative that follows the pre-registered rule; never blocking (warning only) as the simplest. Kept as blocks: the indoor rule and the qualifier rule (cheap, 0.2-0.4%, and unmeasured: a missing indoor value is one the model never saw in training; a missing qualifying run removes results, not only box scores). Not decided here: the owner decides | Recommend, don't delegate | all | README |

## 5. Claims and their evidence

| Claim in the README | Evidence | Status |
|---|---|---|
| The owner's 8 Oct words named no gate settings; every setting was the agent's, unmarked | Decision record lines 3-5 and 11 (subagent H; re-read by the lead on 13 Oct) | Observed |
| The measurement behind the rule had no market price and removed every same-event round at once; with the close, 0.14 → 0.11 (men), −0.07 → −0.08 (women) | `docs/studies/ufc_ideas/stageB.md:172-197` and its harness (subagent C) | As reported by C, not re-run |
| The form family adds +0.14 [−0.35, +0.63] (2025-26), +0.30 [+0.05, +0.54] (2020-24) beyond the price | The edge-anatomy study of 12 Oct (subagent C) | As reported by C |
| The gate withholds 4.4% / 13.7% of main-tour matches in 2024-2026 (2026: 5.4% / 20.0%); 1.2-21.9% / 9.2-64.4% a season since 2013 | `simulate_gate.py --stage0 data/studies/predictability_diagnostic --tag _now`, and `--first 2013 --tag _now2013` | Observed; permanent gaps only, a lower bound |
| What blocks them (Berlin and Nottingham 2026, team events, ITF, qualifying) | `gate_simulation_now.json` | Observed |
| Training's coverage by kind of match | `coverage.py` → `coverage.csv` | Observed, on the shared Stage 0 of 13 Oct 21:13 (packages not merged) |
| Narrower scopes cost 0.5 / 3.3%, 0.2 / 3.2%, 0.2 / 1.0%; the qualifier rule alone 0.19 / 0.44% | `scopes.py --tag _now`; the qualifier count at 07:00 on 14 Oct | Observed |
| 3 of 13 live matches blocked, all on 11 Oct | The three live runs' `gate.json` | Observed (corrects H's "3 of 15") |
| A missing box score gets zero weight, the same in training; the prior's shares | Subagent M's reading of the builders; the two-week form formula re-read | As reported by M |
| One missing same-event round moves q_a by a median 0.35, 90th percentile 1.17, max 1.41 points; the other scenarios as tabled | `replay_gaps.py compare` → `replay/compare.{csv,json}` | Observed, one day |
| Betting through costs 3.0 units-%, a block 37.2 (same_event, 2.5% margin, complete-data judge); the halved-edge readings | `decisions.py` → `replay/decisions.csv` | Observed; designed after the reading |
| The 1-point buffer beats a block in 15 of 16 cells | `decisions.py` → `replay/decision_rules.csv` | Observed; designed after the reading |
| The pattern term was paused for all 23 matches | `replay/base/live_patterns.json` | Observed |
| Replays fail at the tables step since the shared rebuild | `replay_setup.log`; the workaround in `retry_tables` | Observed in this study's tree only |

## 6. Threats to validity, and where a flaw would hide

* **One replayed day, 23 matches** (250-level rounds of 16, the week after Wimbledon). The primary's 90th percentile rests on three men's matches (1.41, 1.35, 1.31). Slams, best-of-five and players with little recent evidence may move more.
* **The removal blanks a box score; a late publication may lack the whole row.** The removal mimics Stage 0's dropped box score (counts and rates blank, has_box False). At bet time, Tennis My Life's late match may be missing as a row, with its result: then Elo and workload miss it too, and the move would be larger. Not measured. The gate cannot see a missing row either, except through the qualifier rule.
* **Closing prices.** The replay's market is the instance frame's close (median edge 0.98 points). Bet-time prices, margins and edges differ, and the decision sums move with them.
* **Post hoc analyses.** The decision analysis, the buffer and the extension scenario were designed after a look at the moves. The buffer's size comes from the move distribution (1.17 rounded down), not from the profits; 1.5 was run beside it and reported. The recommendation departs from the pre-registered verdict on these analyses: the main place a reviewer should push.
* **About 10 bets.** The profit sums illustrate the trade-off's structure. They are not a test, and no interval is given.
* **The pattern term was paused** on the replay day, so the reading excludes it. On active days, its venue-pace-times-ace member reads box scores.
* **Coverage and the simulation run on the shared tables of 13 Oct, 21:13-21:16,** not on the instance's own training frame. Any difference is small for 2013-2025.
* **Subagent readings** (C's numbers, M's prior shares) were taken as reported where no row says they were re-checked.
* **The level layer:** the strength file kept one hash across all resolves, and the controls moved at most 0.024 points. The re-centring effect af describes (about 1e-6) does not show at that scale.

## 7. What a re-design would do

* Replay several days across contexts: a Slam's second week, a WTA 125 week, a week after a team event, a newcomer-heavy draw. Model the move per removed match against the player's box-scored evidence.
* Simulate late publication as it happens: remove the latest match's whole row (result included), not only its box score.
* Score the rules on many past days at bet-time prices (the timed OddsTrader copies) with the owner's stake rule, not at the close with flat stakes.
* Measure Tennis My Life's publication delay directly (data continuity's first-seen times), to size how often the bar would apply.
* Test the evidence-count input in the feature pool, which would let the model price the gap itself.

## 8. Reviewer checklist

- [ ] `perturb` removes a box score the way Stage 0 drops one: compare a removed row with a natural has_box-False row.
- [ ] Every fit used the same training frame (each `fit.json`'s `frame_sha256`: e763a803… for all five, checked at 07:05 on 14 Oct) and seeds 0-15.
- [ ] Every scenario's states step saw its removal: `states.json` parts recomputed; every hit match's inputs changed (`compare.csv`'s `max_input_change`).
- [ ] The layer re-resolve was neutral: `layer_resolves.jsonl` shows one strength hash throughout.
- [ ] The controls (3 in other_event, 9 in same_event_b) moved at most 0.024 points.
- [ ] Stage 1 from the fit's npz equals the predict step's p_base_a in every row (`d_stage1_pts` against `d_stage1_check_pts`).
- [ ] `decisions.py`: odds built from the close with a proportional margin; the judge is the complete-data forecast or its halved edge; the decisions are the forecasts' own.
- [ ] The extension never entered the pre-registered verdict.
- [ ] The departure from the pre-registered verdict is argued, not assumed (§ 6, "Post hoc analyses").

## 9. Reproduction

Tables: the shared Stage 0 of 13 Oct 21:13 (`stage0_matches.parquet` sha256 b3ca7aec…, `stage0_match_players.parquet` f71ccc1f…) and the timeline of 21:16 (`timing.parquet` b984bbbb…). Instance template_2026-10-13 on `C:/Users/zerom/tnr_gaps`, checkpoint 2026-06-22, seeds 0-15, frame e763a803….

```text
./python.sh src/eda/box_score_gate_review/simulate_gate.py --stage0 data/studies/predictability_diagnostic --tag _now
./python.sh src/eda/box_score_gate_review/simulate_gate.py --stage0 data/studies/predictability_diagnostic --first 2013 --tag _now2013
./python.sh src/eda/box_score_gate_review/scopes.py --tag _now
./python.sh src/eda/box_score_gate_review/coverage.py
./python.sh src/eda/box_score_gate_review/replay_gaps.py setup        # then retry_tables, while the timeline collision lasts
./python.sh src/eda/box_score_gate_review/replay_gaps.py choose_ext
./python.sh src/eda/box_score_gate_review/replay_gaps.py run          # states and fit, every scenario (about 20 min each)
./python.sh src/eda/box_score_gate_review/replay_gaps.py finish       # patterns and predict, every scenario
./python.sh src/eda/box_score_gate_review/replay_gaps.py compare
./python.sh src/eda/box_score_gate_review/decisions.py
```

The replay's work tree (`C:/Users/zerom/tnr_gate_review`, 11 GB, holding `run_failed_1`) is kept until the owner decides on cleanup (`replay_gaps.py cleanup`).

## Appendix: the subagent briefs, verbatim

Three read-only `Explore` subagents, launched in parallel at 21:40 PDT (transcript times 04:40:20, 04:40:29 and 04:40:35 UTC on 14 Oct). Their reports were taken as reported, except where a row of the chronology says it was re-checked or corrected.

### H: "History and intent of the 8 Oct gate" (Explore)

```text
Read-only research in the repository C:/Users/zerom/Documents/Tennis-predictions (Windows; use the Read/Grep/Glob tools). Do not edit anything.

Topic: the "gate" rule of the prediction runs. A live match is marked "do not bet" when an earlier finished match of either player, at the same event or in the last 14 days, lacks a box score. Later additions: an unknown indoor input also fails it, and so does a player who entered through qualifying with no qualifying match in the data.

Sources to read, at least:
- docs/decisions/2026-10-08-prediction-run-box-scores.md
- docs/studies/prediction_run/README.md, and its process_log.md or audit files if present
- docs/studies/daily_prediction/README.md and docs/studies/daily_prediction/process_log.md (the parts about the gate)
- src/eda/prediction_run/gate.py (docstring and logic)
- CLAUDE.md's "Prediction runs (decided 8 Oct 2026)" section

Answer these questions:
1. What exactly did the owner ask on 8 Oct, verbatim? Quote it.
2. Which parts of the gate were chosen by the owner, and which were designed by the agent (Claude)? Cover: the 14-day window, every level including team events, matches at other events, the qualifying rule, the indoor rule, and "marked not to bet" rather than a warning or an adjustment. Cite lines.
3. What evidence justified the gate's scope? Cover the "training standard" (98.4–99.7%) and Stage B's recency diagnostic. Did anyone ever measure how much ONE missing box score moves ONE forecast? Quote what you find, or say clearly that nothing was found.
4. Which alternatives to blocking were considered or rejected (fills, imputation, warnings, partial blocks), and why?
5. Are there later notes on the gate's practicality? Examples: women who came through qualifying being marked "do not bet", permanent gaps such as Roland Garros 2026, team events, how often runs were blocked.

Report with file paths and line numbers. Quote verbatim where wording matters. Clearly separate what the text says (observed) from your inference. Keep the report under 900 words.
```

### M: "How missing box scores enter inputs" (Explore)

```text
Read-only research in the repository C:/Users/zerom/Documents/Tennis-predictions (Windows; use the Read/Grep/Glob tools). Do not edit anything. Search very thoroughly.

Question: how does a missing box score (a match whose Stage 0 row has has_box False) enter the current best model's 57 inputs?

Context:
- The input list: the instance folders under data/studies/current_best_model/ (template_2026-10-13, template_2026-10-10) and src/eda/current_best_model/template_inputs.py.
- Input names from a live frame: in_odds_logit, in_ratings_iid, in_elo_games, in_adjperf_tpw_2w, in_points_52w, in_sets_14d, in_age, in_age_sq, in_form_ace/df/first_in/first_won/second_won/hold/bp_saved/bp_faced_pg/brk/bp_conv/rpw_first/rpw_second, in_formdef_ace/df/first_in/bp_faced_pg, in_iosO_* and in_iosD_* (ace, df, first_in, first_won, second_won, hold, bp_saved), in_prod_* (the same seven), in_tour, in_surface, in_level, in_indoor, in_best_of, in_round, in_elo_overall, in_elo_surf_offset, in_surf_season_a/b, in_surf_layoff_a/b.
- Likely code: src/eda/ufc_ideas/stageB_*.py (the two-week "forms"), src/eda/match_timing/ios_time.py and src/eda/surface_ios/ (leak-proof IOS), src/eda/predictability_diagnostic/stage4_features.py and stage3_ratings.py, src/eda/daily_prediction/dp_forms.py, dp_ios.py and dp_elo.py (the live versions), src/eda/model_rebuild/run_chain.py (the chain).

For each family that reads box scores, find in the code:
(a) What happens when a match has no box score: skipped, treated as zero, imputed, or something else?
(b) The decay or half-life, and the prior (shrinkage toward 0 or toward a population mean), including its strength in matches or weight.
(c) Whether the training frame computes the feature with the same code, so that training rows skip missing box scores the same way.
(d) Whether any input tells the model how many box-scored matches a value rests on (a count, a weight, an indicator).
(e) The approximate weight ONE recent match carries in the feature. Example: for a player with 3 matches in the last 14 days, what fraction of the value comes from the most recent one, given the prior.

Also report:
- Which of the 57 inputs read no box score at all: odds, Elo, age, surface counts, and so on.
- Whether results without a box score still count in Elo and the other result-based inputs.

Report with file:line references. Clearly separate code behaviour you observed from your inference. Keep the report under 900 words.
```

### C: "The measurement behind the gate" (Explore)

```text
Read-only research in the repository C:/Users/zerom/Documents/Tennis-predictions (Windows; use the Read/Grep/Glob tools). Do not edit anything.

The decision docs/decisions/2026-10-08-prediction-run-box-scores.md cites: "In Stage B's recency diagnostic (docs/studies/ufc_ideas/stageB.md), leaving out the same event's earlier rounds cuts the two-week profile's gain over Elo (milli-log-loss, higher is better) from 3.19 to 2.09 for men and from 3.32 to 1.83 for women."

Part 1. Find that diagnostic in docs/studies/ufc_ideas/stageB.md, and the code that produced it (src/eda/ufc_ideas/stageB_*.py, report_stageB.py, or similar). Describe exactly:
- Which model was scored: a logistic model of Elo plus the profile? With or without a market price?
- Which matches and which seasons.
- How "leaving out the same event's earlier rounds" was done: every such round removed for every match, or single removals?
- The uncertainty of 3.19 vs 2.09, and of 3.32 vs 1.83: intervals, if reported.
- Whether the result says anything about the effect of ONE missing box score on ONE forecast.
- Whether it says anything about a model that also has the market price as an input. The current best model has the closing odds (Pinnacle first) as an input.

Part 2. Check whether any later study measured how much the box-score form inputs add beyond the closing odds: ablations, lean reviews, the feature universe, feature_alpha_audit, or similar. Report the size of their contribution to the current model with the odds included, if any study measured it, with the study's own numbers and interval.

Give file:line references and verbatim numbers. Clearly separate what is observed from your inference. Keep the report under 700 words.
```

### The tennis-predictions-af session's message (received about 22:50 PDT, 13 Oct), verbatim

```text
Heads-up from the data-gaps session (af): the daily pipeline's active instance will change again around 01:30–02:00 PDT. Your box-score gate replays read it through dp_env().

Now: template_2026-10-13 on C:/Users/zerom/tnr_gaps (switched 20:41: the frozen tables plus the lower-level feed).
Next: template_2026-10-14 on C:/Users/zerom/tnr_tpl1014, built now on the day's tables with the feed, the Roland Garros repair applied at 21:12, and f6's Tennis My Life files. I'll switch with use_instance, then make checkpoints 2026-06-22 and 2026-09-21 and run a replay check.

If your scenarios must all run on one instance, pin it: DP_INSTANCE=template_2026-10-13 and DP_BASE_TREE=C:/Users/zerom/tnr_gaps in your steps' environment, or finish before then. Tell me if you need the switch held, and I'll wait.

Also relevant to your replays: on this instance the level layer re-centres its strength (option c, triggered by the women's additions), with a season-wide shift. So any change to the tree's Stage 0 (your removals, or a replay's dropped later rounds) moves the men's layer-fed forms by about 1e-6 (my replay check: 19 of 23 matches identical, 4 men's within 4.4e-6). That is not your removal's effect.
```

At 07:05 on 14 Oct the active instance was still template_2026-10-13 on `tnr_gaps` (`train.dp_env()`): the switch had not happened (the restart, presumably). Every forecast of this study was made at 23:23-23:32 on 13 Oct, on template_2026-10-13.

---

# Part 2: carrying out the owner's decisions (14 Oct 2026)

Session: `f66b9e99-f90d-40a5-b5fe-c347536062c5` (peer name since the restart: `tennis-predictions-5d`). Times are PDT, read from the clock.

## P2.1 The request

* **The owner's words, verbatim** (14 Oct, about 07:30), quoting the three decisions of Part 1's report:
  > "Replace the gate with the rule above? Recommended.
  > Build the men's fill? Recommended.
  > Add an input to the candidate-feature list saying how much data stands behind each player's recent form? Recommended."
  >
  > Do all 3, but check if there are other processes that may contradict this work that are active and using this work.
  >
  > Then "My 11 GB replay work copy can be deleted. I've left it alone until you say so."
  > delete this
* **How it was read:**
  1. **The gate:** point 3 of the 8 Oct decision replaced by the recommended rule. A missing box score never blocks. A gap of a kind training lacks is a note; a gap of a kind training nearly always has sets a 1-point edge bar. The indoor and qualifier checks keep blocking.
  2. **The men's fill:** at bet time, a men's box score Tennis My Life hasn't published is filled from the ATP's own match statistics, live only, as the WTA fill does.
  3. **The evidence input:** into the feature pool (the feature universe), not the model. The selection rounds decide whether it enters.
  4. **"Check if there are other processes that may contradict this work":** before changing anything, check the running processes, the active sessions and recent edits to the files this work touches, and coordinate edits to shared files.
  5. **The deletion:** the replay's work tree, with the engine's own cleanup, which removes the links into the real data first.
* **Set aside:** putting the evidence input into the model now (the owner said "candidate-feature list").
* **Decision record:** `docs/decisions/2026-10-14-box-score-gate.md` (written when the gate change is in).

## P2.2 Plan

1. Conflict check (processes, sessions, recent edits); delete the work tree, counting the link targets before and after.
2. The gate: `gate.py` sorts each gap by kind and sets the bar. Then its readers: the engine's forecast file, the bet-sheet record and sheet, the data check, the notebook's summary. Then tests, the decision record, CLAUDE.md's gate line and the docs.
3. The men's fill: design from a read-only survey (subagent A; brief in the appendix), build in `prediction_run/fills.py` beside the WTA fill, test on real recent gaps.
4. The evidence input: the pool's admission route (subagent B; brief in the appendix), build, admission card, verdict.
5. Report to the owner.

## P2.3 Chronology

| When | Step | Why | Results seen by then | Output |
|---|---|---|---|---|
| 07:34 | **Conflict check (observed).** Running: two ITF point scrapers (sofascore_editions, flashscore_points, since 07:06), the scheduled downloader and itf_live (07:30), and `model_rebuild/fits.py --out .../template_2026-10-14 --seeds 4-15` (07:31: the data-gaps session building the next instance). No daily-engine run, no gate, fill or feature-pool process. Sessions: 13 peers after the restart, tennis-predictions-fc busy. Recent edits to the files this work touches: the pattern-adjustment session edited `diagnostics.py`, `bet_sheet.py` (13 Oct 21:08-21:09), CLAUDE.md, the master-pipeline and daily-prediction READMEs and a new decision (14 Oct 07:07-07:10). The cleanup-inventory session deleted `tnr_lyr_off` / `tnr_lyr_on` this morning; its log lists `tnr_gate_review` as "the gate review's tree, running that night", not for deletion. Nobody edited `gate.py`, `fills.py`, `readiness.py` or the feature universe in the last 24 hours. **Verdict:** nothing running uses or contradicts this work. Overlap is in files only: re-read each shared file just before editing it, and keep edits narrow | The owner's check | none | — |
| 07:35 | Two read-only subagents launched (briefs verbatim in the appendix): A, facts for the men's fill; B, how a feature enters the pool | Plan 3-4 | none | — |
| 07:36-07:38 | **Work tree deleted** (`replay_gaps.py cleanup` → `dp.py cleanup`: links removed as links first, none left, then the tree). It held 10 junctions: `data/raw`, eight `data/dump` folders, and `dump/matches/tennis_my_life` into `tnr_dump_freeze`. Link targets before and after: `data/dump` 6,899 files and `tnr_dump_freeze/matches/tennis_my_life` 208 files, byte totals equal; `data/raw` 390,682 → 390,753 files (the running scrapers). C: 259.6 → 270.3 GB free | The owner's instruction | — | `scratchpad/targets_before.json` (this session's) |
| 07:39 | **An error of Part 1 found (correct by adding).** While listing the level codes for the gate's kinds: ITF qualifying has no box score in training (67,884 matches, 0%). `simulate_gate.level_group` sorted qualifying before ITF, so `coverage.py` pooled the women's ITF qualifying (67,682) with the Slam, WTA and WTA 125 qualifying (19,048). That made "women's qualifying 19%". Split (2013-2025): women's tour-level qualifying 84.5%, WTA 125 qualifying 95.2%, ITF qualifying 0.0%; men's 87.2%, 99.7%, 0.0%. **Consequence:** the README's "kinds training lacks" wrongly held the women's qualifying; corrected, qualifying above ITF level is near-complete for both tours | Correctness of the rule's kinds | Part 1's readings | — |
| 07:40-07:41 | **Corrected and re-run on the same tables** (Stage 0 b3ca7aec…, timeline b984bbbb…, unchanged since 13 Oct 21:16). `level_group` now sorts ITF, then team events, then qualifying. `coverage.py`: women's qualifying above ITF level 85.1% pooled, 99-100% every season since 2019; men's 94.5%; ITF, qualifying included, 7.7% / 6.2%. `simulate_gate.py --tag _now_v2` and `--first 2013 --tag _now2013_v2`; any-kind blocks unchanged (4.4 / 13.7%). `scopes.py --tag _now_v2`, near-complete scope (now with both tours' qualifying above ITF): **0.5% / 4.3%** (was 0.5 / 3.3%); the women's 2026 8.4% → 11.5%, the added part the 2026 Slam qualifying (Roland Garros 29, Wimbledon 28, US Open 25), which Tennis My Life has lacked since June 2026. The `_now` files of 13 Oct are kept | Correct the evidence the rule rests on | the re-runs | `coverage.csv`, `gate_simulation*_now_v2*`, `scopes_now_v2.csv` |
| 07:41 | **README corrected visibly:** a correction note at the top, saying the owner approved the first version; the coverage and scope tables; the kind lists in "In short" and the recommendation. The principle the owner approved (a note for kinds training lacks, a bar for kinds it nearly always has) is unchanged; one kind moves between the lists | Report honestly | — | README |
| 07:42 | **Subagent B reported** (taken as reported where not re-checked): **the pool already holds this input as U-126, "form evidence and shrinkage"** (`data/studies/feature_universe/universe.csv:127`). Its columns are `fp__f07_evidence_age__f07_s0_a/_b`: s0, the decayed count of recent box-score matches, from `f07_evidence_age.form_state`, and `fp__f13_uncertainty__shr_a/_b`: s0/(s0 + K3), with K3 fixed at 37. Built 7 Oct; status built, not in the model; tier D, priority low. Its limits: the points form only, the frozen 63,737-match population (the template frame has 67,226), and no level layer. The model's own Σw is computed (`stageB_adjperf.py:222-225`, `level_layer.py:863-881`) but not stored. **So decision 3 becomes a refresh of U-126**, not a new id: rebuild it on the current population with the model's own weights, and re-file its verdict | Plan 4 | none | — |
| 07:44 | **Subagent A reported** (taken as reported where not re-checked). The ATP's Infosys keystats API holds the full box score per match: aces, double faults, first serves in and points, first- and second-serve points won, break points saved and faced, service games. The daily serve-speed collector (`serve_speed_tabpfn/live/atp_daily.py`) already fetches and decrypts it for TML's played rounds of events with per-match dates, but stages only speeds. TML's men's `tourney_id` is year plus ATP event id, and its player ids are ATP codes, so a gap can be matched by event, round's code range and both codes. The prediction-run README notes "TML usually has ATP box scores within minutes". No set scores in keystats; Challenger keystats unprobed; the agreement with TML for men unmeasured | Plan 3 | none | — |
| 07:45 | Subagent D launched (general-purpose, writes only the feature-pool files; brief verbatim in the appendix): refresh U-126 with the model's own weights, re-file its card | Plan 4 | none | — |
| 07:46-07:58 | **The gate replaced** (`src/eda/prediction_run/gate.py`). `kind()` sorts ITF and team events first, then qualifying, main tour, Challenger / WTA 125; `effect()` gives "note" for team events and ITF, else "edge bar" (an unknown kind included). A gap never blocks; `EDGE_BAR = 0.01`. Still blocking: the qualifier rule, not in Stage 0, an unknown indoor input. `gate.csv` gains `edge_bar`, `bar_gaps`, `noted_gaps`; `bet` is BET, BET_BAR ("may be bet if its edge clears 1 point") or NO_BET; `gate_missing.csv` gains `kind`, `effect`. Readers: `dp_predict.py` copies the bar into `predictions.csv` as `gate_edge_bar`; `diagnostics.py` blocks only what does not start "may be bet", picks a side only if its forecast moved the bar against it is still +EV (as the replay tested), records `gate_edge_bar`, `passed_by_bar`, `gate_notes`, and passes the gate's blocking reasons joined by " \| " (the qualifier reason holds a comma); `bet_sheet.py` says the bar, a bar-passed bet and noted gaps plainly, keeps the old wording for a run made before 14 Oct, and its Data check column reads complete / gap: 1-point edge needed / incomplete; `readiness.py` verdicts ready / ready once filled / needs a 1-point edge / will be blocked, with noted gaps in their own column; `predict.py` counts the bar. Re-read before editing: `diagnostics.py`, `bet_sheet.py` (the pattern session's edits of 13 Oct kept) | Decision 1 | — | the files named |
| 07:58-08:00 | **Tests.** Updated to the new rule: the gate's (a main-tour gap sets the bar and does not block; team and ITF gaps noted; kinds; the qualifier and indoor blocks), the data check's (five synthetic matches; on the 11 Oct run the three Laver Cup gaps are noted and nothing is blocked), the plain wording, and a new one: the bet sheet applies the bar exactly as the replay tested it. **First run: one failure, not the gate's:** `test_data_check_agrees_with_the_runs_own_gate` hit the duplicate-timeline collision (the 11 Oct run's Stage 0 is older than the shared timeline of 13 Oct 21:16; a fresh data check does not meet it). The test now restricts the timeline to that Stage 0's matches, as `retry_tables` did. **Then `test/prediction_run` and `test/master_pipeline`: 54 passed.** `test/daily_prediction` without a replay: 6 passed; the 11 that need a replay were not run (the collision) | Verify | — | tests |
| 08:00-08:02 | **Recorded:** `docs/decisions/2026-10-14-box-score-gate.md` (the owner's words verbatim, the rule, the evidence, the departure, the correction, the status) and its row in the index; a pointer at the top of the 8 Oct decision; the gate's line in CLAUDE.md (re-read first: the pattern session edited CLAUDE.md at 07:09); the data check and record sections of the master-pipeline README | Record the decision | — | the docs named |
| 08:03 | **How often the men's fill would be needed (observed, before building).** Shared Stage 0, 2025-2026, men's completed matches of the kinds that set the bar: 7 of about 25,000 lack a box score permanently (2 Challenger, 4 qualifying, 1 Shanghai). Today's gaps list (`fills.gaps` on the shared tables) has no fillable men's gap: the two Shanghai ones are held (the frozen reference holds them). The prediction-run README notes TML usually has men's box scores within minutes. So the fill is insurance for days TML lags; built because the owner decided it | Plan 3 | none | — |
| 08:04-08:06 | **Built** in `prediction_run/fills.py`: `atp_codes` (the bracket's codes; qualifying QS001-063), `held_keystats` (the collector's raw file, decrypted behind its year guard), `keystats_counts` (the nine counts as the backfill study maps them, plus a check that its own fractions agree), `_atp_client` (the collector's client, headers and receipts; nothing when the collector is off), `fill_atp` (files on disk first, then asks the codes not held for other players, stopping at the match; a block stops the fills), `fill_all` (WTA and ATP); `tml_keys` gains TML's player codes; `gaps()` classes ATP tour-level gaps fillable; `run.py --refresh` calls `fill_all`; the agreement check takes `--tour atp` (`--max-requests 0`: files on disk only) | Decision 2 | — | `fills.py`, `run.py` |
| 08:06 | **Agreement, files on disk only, Shanghai 2026 (observed):** 73 matches linked, all nine counts equal TML's on 146 of 146 player rows | Verify | — | `atp_fill_check/` |
| 08:06-08:08 | **The request path, live** (main draw, budget 40): the budget stopped the run cleanly; 66 filled, all equal (132 of 132 rows); 6 "not completed". **Then two corrections of my own reading:** (1) the ATP's `matchCompleted` reads False on finished matches (9 of 82 main-draw files, e.g. Tsitsipas v Fritz 3-6 7-5 6-3 with 15 service games each): replaced by `covers_match`, the flag or the service games adding up to TML's score (as B5), and the main draw then filled 82 of 82, all equal (164 of 164 rows); (2) the decision record's first status line said the 66 were fetched with real requests: the receipts show the 40 requests brought 6 files, all re-fetches of held ones, and 34 absent codes; corrected in the record | Verify | the agreement rows | `atp_fill_check_asked/` |
| 08:11-08:14 | **The request path finding new files** (Shanghai qualifying, none held, budget 70): 14 new files, 2 matches filled before the budget stopped it. **They disagreed with TML** on first serves. With the 14 new files, on disk only: 13 qualifying matches, ace, df, service games and break points equal on 26 of 26 rows, but first serves in on 9 of 26 (the ATP 0.73 lower on average), first-serve points won 14 of 26, second-serve points won 14 of 26, serve points 24 of 26. TML's qualifying numbers come from another source than its main draw's. **Choice:** the men's fill takes main-draw matches only (`gaps()`: not qualifying), where the ATP's numbers are exactly those the training rows hold; a qualifying gap waits for TML under the 1-point bar. Receipts of the fill's requests: 110 (20 answered, 90 absent) | Live inputs as in training | the agreement rows | `atp_fill_check_qualifying/`, `fills.py` |
| 08:09-08:15 | **Tests:** 5 new offline tests of the men's fill (the nine counts and the fraction check; `covers_match`; the codes; the classes, qualifying unserved; linking by codes with TML's orientation, a player listed second in the file). The first run of the orientation test failed on my test's expectation, not the code (the file listed Bublik first); fixed. **59 passed** (`test/prediction_run`, `test/master_pipeline`). **Recorded:** CLAUDE.md's "Box scores first" line, the data check's docstring and fix text, and the decision's status | Verify, record | — | tests, docs |
| 08:22 | **Subagent D reported** (taken as reported where not re-checked; its own chronology 07:45-08:22 is in its report, summarised here). Five `fe__` columns: `sw_a/_b`, the decayed count of earlier box-score matches as the model's total-points form weighs them (half-life 2 weeks, the level layer's weights for men, ITF 0); `r_a/_b` = sw/(sw + K3), with K3 10 for men and 20 for women; `r_diff`. Built with `level_layer.forms_step3` on the `tnr_gaps` tree, read-only. **Checks it reported:** the model's `adjperf_tpw_2w` rebuilt bit for bit on all 67,226 frame matches (an independent recount on 400 rows to 1.2e-14); against the old U-126 r 0.982 (0.998 without the layer); a timing probe with 8 cuts and 2.04M protected rows, nothing moved beyond 1e-12, and a leaky control caught; largest \|r\| with another column 0.98 (its own old build), then 0.71 (sets in 14 days); coverage 1.00 except women 2025-26 in the store (0.97). The store's values are missing for 111 WTA June-July 2026 matches: 71 keep their match id but name other players in today's tables, 40 are gone; not traced. **Verdict: admitted, U-126 re-filed in place; priority raised from low to medium (its call, flagged).** **Corrections to the brief:** the "K3 37" was a line number (K3 is 10 / 20); the engine runs `forms_state.step3_for` and does not keep the weight sum (live use would need it); `template_2026-10-14` exists and was built too (differs from 13 Oct on 2.8% of player-rows). Files: `form_evidence.py` and `form_evidence/` outputs, `build_store.py` (`--append-fe`), `catalogue/spec_form.py`, the feature-universe test, its README (the card in section 9), the store, registry, menu and universe | Decision 3 | none (no result read) | the files named |
| 08:23 | **Lead's check of D's work (observed):** `test/feature_universe` 14 passed; the store has 63,737 rows and 789 columns, with the five `fe__` columns (sw mean 3.28, max 13.5; r mean 0.19, max 0.57; r_diff centred on 0); U-126's row read in full (definition, source, the `fe__` columns to select over the 7 Oct ones, safe timing, "no result read", caveats, priority medium). Also: `test/current_best_model` 99 passed. **Recommendation to the owner:** keep the medium priority; flag the 71 WTA match ids that changed players as a possible id-stability issue, untraced | Verify | — | — |

## P2.4 Claims and their evidence

| Claim | Evidence | Status |
|---|---|---|
| Nothing running used or contradicted this work | The process list, the session list and the files changed in the last 24 hours (07:34) | Observed at 07:34; sessions can start later |
| The work copy was deleted without touching real data | Junction-first cleanup; link-target file counts and bytes before and after | Observed |
| The rule's kinds rest on training coverage | `coverage.py` re-run with ITF sorted before qualifying | Observed; corrects Part 1's pooling |
| The new gate does what the decision says | `test/prediction_run` (gate tests), `test/master_pipeline` (data check, bet sheet, the bar) | 59 passed; not yet seen on a live bet day |
| The bet sheet's bar equals the replay's tested rule | `test_the_bet_sheet_applies_the_edge_bar` | Observed (tests) |
| The men's fill equals TML's numbers in the main draw | Shanghai 2026, 82 matches, 164 of 164 player rows, all nine counts | Observed |
| The ATP's qualifying numbers differ from TML's | 13 Shanghai qualifying matches, first serves in equal 9 of 26 rows | Observed; why TML differs there is inferred (another source) |
| The men's fill will rarely be needed | 7 of about 25,000 men's matches lack a box score permanently in 2025-26; no fillable men's gap today | Observed on permanent gaps; bet-time delays unmeasured |
| The evidence input is refreshed in the pool | Subagent D's report and the lead's check (P2.3, 08:22-08:23) | Observed (D's checks as reported; the lead re-ran the tests and read the row) |

## P2.5 Threats to validity, and where a flaw would hide

* **The bar is tested on synthetic and replayed records, not a live bet day.** The first live run is the real test.
* **The men's fill's agreement rests on one event** (Shanghai 2026, a Masters). Smaller events, or files fetched during play, are untested. `covers_match` guards against a file of a match still in play.
* **Bet-time delays are unmeasured.** How often Tennis My Life lacks a box score at the hour of a bet is unknown: neither the fill's value nor the bar's frequency has a live estimate yet.
* **The data check errs toward a gap** (a cautious window for undated matches), so it may show "needs a 1-point edge" where the run finds none.
* **The kinds are fixed lists.** If training coverage of a kind changes (the lower-level feed fills ITF and WTA 125 box scores from 2025), a kind may move. The decision says to re-run `coverage.py` at each template build.
* **Shared code changed while other sessions work:** `diagnostics.py`, `bet_sheet.py`, `dp_predict.py`, `readiness.py`, `fills.py`, `run.py`, CLAUDE.md, the notebook. Each was re-read first, and edits were kept narrow, but a session holding an older copy in memory could overwrite them.

## P2.6 What a re-design would do

* Log every live day's gaps with their kind and whether the fill or the bar acted, and re-read the rule after a month of bet days.
* Probe Challenger keystats, and the WTA 125s' and Slams' feeds, for fills where training holds the box scores.
* Let the model price a gap itself (the evidence input), then retire the bar if the model handles thin evidence.

## P2.7 Reviewer checklist

- [ ] `gate.kind`: ITF and team events are sorted before qualifying (the error of Part 1).
- [ ] The bar in `diagnostics.py` moves each side's forecast against that side, for the pick with and without the patterns.
- [ ] A run made before 14 Oct still reads as it did (its gate text, `gate_detail` wording).
- [ ] `fills.gaps`: the ATP main draw only is fillable; the qualifying, Challengers, Slams and team events are not.
- [ ] `fill_atp` orients by TML's winner and loser codes, never by the file's order.
- [ ] The fill's requests: paced, receipted, raw copies kept, stopped on a block or the budget.
- [ ] The evidence input stays out of the model (pool only).

## P2.8 Reproduction

```text
./python.sh -m pytest test/prediction_run test/master_pipeline -q
./python.sh src/eda/box_score_gate_review/coverage.py
./python.sh src/eda/box_score_gate_review/simulate_gate.py --stage0 data/studies/predictability_diagnostic --tag _now_v2
./python.sh src/eda/box_score_gate_review/scopes.py --tag _now_v2
./python.sh -m src.eda.prediction_run.fills --stage0 data/studies/predictability_diagnostic     --events 2026-5014-20261005,2026-5014-20261007 --tour atp --out <folder> --max-requests 0
```

## P2.A Appendix: the subagent briefs of Part 2, verbatim

Transcript times (UTC): A 14:36:18, B 14:36:24 (07:36 PDT; the chronology says 07:35), D 14:45:27 (07:45 PDT).

### A: "Facts for building the men's fill" (Explore)

```text
Read-only research in the repository C:/Users/zerom/Documents/Tennis-predictions (Windows; use the Read/Grep/Glob tools). Do not edit anything. Search very thoroughly.

Goal: build a live "men's fill". At bet time, a men's (ATP) match whose box score Tennis My Life (TML) has not published yet would be filled from the ATP's own match statistics, the way post-freeze WTA gaps are filled from the WTA API today. I need the facts to design it.

1. The current fill design: src/eda/prediction_run/fills.py, and where src/eda/prediction_run/run.py --refresh and the daily engine's refresh step (src/eda/daily_prediction/) call it. Explain:
   - the gap classes (held / fillable / unserved) and how a gap is classified;
   - fill_wta's inputs and outputs, tml_keys, and override_table's columns;
   - how the overrides enter Stage 0 for a live run (stage0_build.py --box-overrides ... --confirm-live-overrides), and what stops fills from entering training;
   - how a fill is dropped once TML publishes.
   Quote the relevant code with file:line.
2. The 8 Oct plan for the men's equivalent. Search docs/decisions/2026-10-08-prediction-run-box-scores.md, docs/studies/prediction_run/ (README, process log, plans), docs/studies/daily_prediction/ and docs/studies/prediction_pipeline/ for any plan or note on an ATP fill (an ATP stats feed, Infosys, atptour.com match stats). Quote it.
3. Existing ATP match-statistics sources in the code. Search src/ingest/ and src/eda/ (for example infosys_atp_backfill, serve_speed_tabpfn/live, serve_speed_acquisition, official_point_feeds, ao_rg_points) for code that downloads ATP match statistics or the ATP Stats Centre / Infosys files, including any decryption, for recent matches. For each, report:
   - the URL pattern(s);
   - how matches are identified (ATP tournament id, year, match code like MS001);
   - what fields come back: aces, double faults, serve points, 1st serve in, 1st serve points won, 2nd serve points won, service games, break points saved and faced;
   - pacing, receipts and raw-copy conventions;
   - whether it covers Challengers.
   Report whether a live feed already fetches these per match during tournaments (for example for serve speeds), and where its raw files land.
4. How Stage 0 men's matches map to ATP tournament ids and match codes: any id-link tables (match_timing link_sources, tournament id maps, TML's tourney_id format like 2026-0314). Can a Stage 0 men's match be matched to an ATP match-stats record, by tournament, round and player ATP ids?
5. Stage 0's box-score columns and checks that a filled box score must pass: src/eda/predictability_diagnostic/common.py (C.BOX) and stage0_build.py (checks B0–B9).

Report with file:line references and verbatim quotes where wording matters. Separate observed code from inference. Keep the report under 1,200 words.
```

### B: "How a feature enters the pool" (Explore)

```text
Read-only research in the repository C:/Users/zerom/Documents/Tennis-predictions (Windows; use the Read/Grep/Glob tools). Do not edit anything.

Goal: add one candidate input to the project's feature pool (the "feature universe"): how much box-score evidence stands behind each player's recent form. I need to know how a feature enters the pool, and how to build this one.

1. The pool. Read docs/studies/feature_universe/README.md and its process log, docs/studies/adoption_framework/README.md § 11, and any docs/decisions file on the feature universe or selection rounds. Report:
   - how a candidate feature is registered: a registry file (its path, format and columns), a values parquet per feature, or something else;
   - what an "admission verdict" requires: a screen, a leak probe via src/eda/match_timing/probe.py, a cluster assignment, or more;
   - who decides (selection rounds by cluster).
   Give the most recent example of a feature admitted to the pool, with the exact files it added or changed.
2. The two-week form inputs of the current best model (in_form_*, in_formdef_*, in_adjperf_tpw_2w). Report:
   - where they are computed (src/eda/ufc_ideas/stageB_*.py, src/eda/daily_prediction/dp_forms.py, the chain in src/eda/model_rebuild/run_chain.py);
   - the weighting w = 2^(-age/2 weeks) and the prior K3;
   - how a match without a box score gets weight 0;
   - whether the code exposes Σw, the weighted count of box-scored matches per player-match, or would need to compute it.
   Do the same for the surface IOS profile (in_iosO_*, in_iosD_*) and points_52w: is there a natural "evidence" quantity per player, such as a count or weight of box-scored matches?
3. The template frame: where the instance's model frame lives (data/studies/current_best_model/template_2026-10-13/ or similar; model_frame_chain.parquet?), and its key columns (match_id, sides A/B, season), so a new feature can be joined to it.
4. The leak-proof timing rules for a per-player count feature (CLAUDE.md, "Feature timing"): which clock it must use.

Report with file:line references, and quote where wording matters. Separate what you observed from your inference. Keep the report under 1,000 words.
```

### D: "Refresh pool candidate U-126" (general-purpose)

```text
You are working in the repository C:/Users/zerom/Documents/Tennis-predictions on Windows (Git Bash and PowerShell are available). Run project Python only through ./python.sh, the project's `tennis` Conda environment. Read CLAUDE.md first; its rules bind you:
- no state-mutating git commands;
- never delete files;
- no model fits unless stated below.

The lead session is editing these right now, so do not edit them: src/eda/prediction_run/, src/pipeline/, src/eda/daily_prediction/, docs/decisions/, docs/studies/box_score_gate_review/, CLAUDE.md. Reading them is fine.

**The task.** The owner decided on 14 Oct 2026, verbatim: "Add an input to the candidate-feature list saying how much data stands behind each player's recent form". The pool (the "feature universe") already holds such a candidate: U-126, "form evidence and shrinkage". Refresh it so the pool carries a current, exact version. It goes to the pool only, never into the model: selection rounds decide later.

**Facts already found by a read-only survey.** Verify any you rely on.
- **U-126 today.** It is `data/studies/feature_universe/universe.csv:127`, with columns `fp__f07_evidence_age__f07_s0_a/_b` and `fp__f13_uncertainty__shr_a/_b` (menu.csv:321-322, 366-367).
  - s0 is the decayed count of recent box-score matches. It comes from `f07_evidence_age.form_state`: s0 = Σ 2^(-age/14 days) over box-score rows with a finite tpw z, under Stage 0's as-of rule.
  - shr = W/(W + K3), with K3 hard-coded at 37 (`f13_uncertainty.prepare_b6`).
  - Built 7 Oct on the frozen population of 63,737 matches. Points form only; no level layer. Status: built, not in the model; tier D, priority low.
- **The model's own two-week forms.** They come from `src/eda/ufc_ideas/stageB_adjperf.py`.
  - Formula: sum w z / (sum w + K3 u_typ^tau), with w = 2^(-age/h3) × units^tau. Chosen constants: tau = 0, h3 = 2 weeks.
  - K3 by skill: serve 10 (men) / 20 (women); return 160; tpw 10 / 20.
  - With tau = 0, Σw is the decayed match count.
  - A row without a box score gets weight 0 (stageB_adjperf.py:222). Σw is computed (sums column k, :225) but never stored.
  - The level layer (`level_layer.py:863-881`) multiplies w by its `rw` for men, and the template excludes ITF box scores (`itf_box: "exclude"`). Women are untouched.
  - The live engine computes the forms through `dp_forms.decided_inputs` (src/eda/daily_prediction/dp_forms.py:150-152), calling `LL.forms_step3`. An exact Σw is column k at ctx.ia/ctx.ib.
- **The pool's route.** It is in docs/studies/feature_universe/README.md: adding a feature (about lines 581-603), verdicts and the admission card (581-595), and the U-330 example.
  - A feature has a `catalogue/spec_*.py`; `build_store.py` appends it to `store.parquet` (one wide table keyed by match_id); then `store_registry.csv`, `menu.csv` and `universe.csv` are updated.
  - Tests live in test/feature_universe/test_store.py.
  - A per-player own-history count is "safe by construction" (CLAUDE.md, Feature timing). It uses Stage 0's as-of rule and needs no probe.
- **The template frame.** It is `data/studies/current_best_model/template_2026-10-13/model_frame_chain.parquet` (67,226 rows; match_id, tour, season, …; side A is Stage 0's player_a_id).

**What to build.**
1. **Columns.** Per match, for side A and side B, take the decayed count of the player's earlier box-scored matches exactly as the model's two-week forms weight them (Σw, with the layer's weights for men). Compute it, if at all possible, with the model's own code path, so it equals what the live engine computes. Also the shrinkage share r = Σw/(Σw + K3) with the model's own K3; say which skill's K3 you use, and why. Encode as the pool's conventions want (A, B and/or A − B).
   If the per-statistic masks make Σw differ between statistics (women's service-game statistics are partly missing), say how much, and pick one with a reason.
2. **Population.** Build for the store's population, and also save the template frame's population beside it, so a later round can use either.
3. **Checks, all without scoring any result against match outcomes.**
   - (a) Against the old U-126 s0: the correlation, the largest differences, and why they differ.
   - (b) On a sample: confirm Σw is the denominator of the model's own form value.
   - (c) How timing safety is enforced.
   - (d) Near-copies: the largest |r| against the store's columns and the model's inputs (for example in_sets_14d).
   - (e) Coverage by season.
4. **Register it in the pool** following the README's conventions; keep earlier ids. Either re-file U-126 or add a successor row, whichever the README's conventions say.
   - Write the admission card: definition, encodings, stable measurement and coverage, timing, available at bet time, not a near-copy, mechanism, cluster node, results read (none).
   - Recommend a verdict on the card's criteria.
   - Add tests in test/feature_universe/ like U-330's, and run the feature-universe tests.
5. **No fits and no outcome scoring.** If the README's admission rules require a screen against results, stop and report that, rather than running it.

**Report back** (under 900 words):
- the files you added or changed;
- the checks' numbers;
- the verdict and why;
- anything that contradicts the facts above;
- a short chronological record of your steps (with clock times from `date`, failures and dead ends), which the lead will copy into the study's process log.
```

---

## Note, 22 Oct 2026: the instance's build tree deleted

Added by the cleanup session `4437577b-803e-4161-baf5-c6fade971478`, at the owner's word
([cleanup inventory, process log § 9d](../cleanup_inventory/process_log.md)).
* **Deleted on 22 Oct 2026:** `C:/Users/zerom/tnr_gaps`, the build tree of `template_2026-10-13`. Every forecast of
  this study was made on that instance (13 Oct, 23:23-23:32; the row "At 07:05 on 14 Oct" above). This study's own
  work tree, `C:/Users/zerom/tnr_gate_review`, had been removed before.
* **What stays:** the run folders under `data/studies/box_score_gate_review/replay/` and every reading recorded here.
* **For a reviewer:** the readings come from the 13 Oct instance (the tables of 8 Oct plus the lower-level feed), an
  older version of the model; the live one is `template_2026-10-21b`. The scenarios' commands no longer run as written:
  a re-check replays on the current instance (the master notebook's selection), and its numbers may differ. Subagent
  D's form-evidence build (U-126, the 08:22 row) read the same tree; the feature-universe README has its note.

