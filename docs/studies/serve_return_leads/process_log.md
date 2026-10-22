# Process log: the men's serve, return and serve-speed leads

16 Oct 2026 · Study: serve_return_leads (a follow-up of [edge anatomy](../edge_anatomy/README.md)) · Kept by Claude Opus 5.5 (`claude-opus-5-5`), session `6483c720-30a3-46ff-9519-287690b6f9d8` (the session that ran edge anatomy; its context was summarized before this request, and the edge-anatomy log and the unpriced-leads study were re-read where needed) · Template: [process_log_template.md](../process_log_template.md)

## 1. The request

**The owner, 16 Oct 2026, verbatim** (the indented parts were pasted from my explanation of 13 Oct):

> These four traits
>
> > Serving strength. How often a player holds his serve, and how often he saves break points (the points where the opponent can win his service game). It is measured over his whole career, with recent matches counting more, separately for each surface. It is also adjusted for opponents: holding serve 85% of the time against weak returners counts for less than 85% against strong ones.
> > Break points saved, recently. The same break-point measure over just the last two weeks.
> > Returning strength. How well a player holds down his opponents' serving: how far below their usual level they win their first-serve points against him. It is opponent-adjusted in the same way.
> > Serve-speed change. Whether a player's first serve has recently got faster or slower than his own normal speed. It comes from radar data; a faster-than-usual serve is a sign of good physical shape.
>
> Men only
>
> Lock in these traits and their expected direction now, and check them once on the unseen matches.
>
> THEN
>
> > Build cleaner versions:
> > return quality measured against each server's normal level;
> > "break points saved beyond what the player's overall serving predicts" (the luck part);
> > more speed data: second serves, and how speed fades during a match.
>
> See if they hold up.
>
> First assess if my suggest order of operations is correct. Perhaps you should build cleaner versions first then check them on unseen matches.
> Im not sure what matches have been seen or not in the study of this earlier. Or if it means LIVE FORWARD data.
>
> Dont make any changes to the production best tabpfn3.5 model/post adjustment yet, this is diagnostic and explorative

**Interpretation acted on.**
1. Assess the proposed order (lock in → check on unseen matches → build cleaner versions → see if they hold up) against the alternative (build first, then one check), and recommend.
2. Say exactly which matches have been seen, by which study, and what "unseen" can mean now: the sealed matches already played, or live forward matches.
3. Then do the diagnostic work in the recommended order, men only, without spending unseen matches: no result dated 29 Jul 2026 or later is read in this study unless the owner gives a go for a check.
4. Nothing in production changes: not the TabPFN fits, the serve-speed stage, the five-pattern adjustment, the daily engine or its files. Another session (`05787e62-…`) is editing the live five-pattern code today; this study touches none of it.

**Readings set aside.**
* (a) Run the check now, as the request's first step literally says. Set aside pending the assessment, which the owner asked for first; the assessment (§ 3) recommends against checking now.
* (b) "Unseen" = 2025–26. No: January 2025 – 28 July 2026 is the window in which these traits were found (edge anatomy's ledger), so it cannot confirm them.
* (c) Build the cleaner versions as production features. No: diagnostic only, by the owner's last sentence; any later adoption goes through the feature pool and `compare.py`.

**Plan.**
1. The ledger of seen and unseen matches (outcome-free counts only).
2. The timeline: how many unseen men's matches exist now and per month, and what a check could detect by when (outcome-free counts; power from the seen 2025–26 readings).
3. Lock in the four traits now: definitions, directions, one combined primary, the test, the window from 29 Jul 2026, frozen with a hash, before any further reading.
4. Build the cleaner versions on seen data only (results before 29 Jul 2026), each defined before its reading is computed.
5. Read them on the seen windows (2013–24 by era; 2025 – 28 Jul 2026), beside the raw traits, as diagnostics.
6. Register the chosen cleaner versions as an addendum to the lock-in, before any unseen match is read.
7. Report: README for the owner, chat summary.

## 2. Chronology

| When (PDT) | What | Why | Results seen | Output |
|---|---|---|---|---|
| 16 Oct 13:55–14:04 | **Read before acting:** the unpriced-leads README, pre-registration, `check_now_rules.md`, the check's `result.json` and `summary.txt`, `adjustment.json`, `forecasts_facts.json`, the luck builder's memo, the long list's serve/return and speed rows, the edge-anatomy ledger's rows for the four traits; the process-log entries of 14–16 Oct (another session fixing the live G3 member today) | Establish what has been seen before assessing the order | **Already-published readings only:** the check of 13 Oct (+3.80 beyond the model; groups G1 +0.84, G3 +1.95, G5 +1.71, G2 +0.72, G4 −0.27) and the ledger's men's z's (2025–26: iosO_hold −4.44, iosO_bp_saved −3.88, form_bp_saved −2.79, iosD_first_won +3.26, iosD_hold +2.54; 2013–24: −1.06, −1.64, −2.32, +0.93, +0.89); the luck builder's 2013–24 men's raw z's (hold luck −3.31, save luck −3.26) | — |
| 16 Oct 14:00 | **Outcome-free counts** on the 14 Oct instance's frame (columns tour, season, tournament date, debut flag, price; `a_won` not loaded): the frame ends at tournament date 23 Sep 2026; from 29 Jul 2026, men 416 (391 priced by BetOnline, 25 by the books' average), women 450; from 24 Sep, none. Monthly men's counts June–Sep 2026: 297, 192, 362, 54 | How many unseen matches exist | Counts only | — |
| 16 Oct 14:02 | **Outcome-free counts** of the serve-speed panel (`speed_panel_backfilled.parquet`): second-serve speed (`spd2`) on almost every row 2011–2026; first-serve fault speed (`fault1`) only in 2025 (924 men's rows) and 2026 (470); within-match SD and timed points on the point-level rows; the panel's last day about 30 Sep 2026 | Which speed extensions the data allow | Counts only | — |
| 16 Oct 14:04 | Schema of edge anatomy's `analysis.parquet`: seasons 2019–2026, tournament dates 31 Dec 2018 – 28 Jul 2026; men's speed column non-zero on 98.9% of rows | The seen-window base for the diagnostics | Schema and coverage only | — |
| 16 Oct 14:05 | **The ledger of seen and unseen matches** (§ 3.1), from the rows above | — | — | this log |
| 16 Oct 14:07 (stamped 14:20 when written; see the correction row at 14:15) | **Fixed before computing any reading** (`common.py`): the four traits as the owner worded them, men only. T1 serving = mean of −`iosO_hold`, −`iosO_bp_saved`; T2 = −`form_bp_saved`; T3 returning = mean of +`iosD_first_won`, +`iosD_hold`; T4 = +`spd` (the serve-speed stage's 28-day column). Each column over its RMS, each trait over its RMS, **R0 = the mean of T1–T3** over its RMS: equal weight per trait, not per column. Scales frozen on the men's matches of 1 Jan 2025 – 28 Jul 2026 (outcome-free). Speed is kept out of R0: it is a separate stage of the model, and it was unstable by season (edge anatomy: it cost in 2023). The fit is unpriced leads' registered `look.fit`, unchanged | R0's definition is principled (the owner's four traits, equal weights), not chosen on its reading. One primary instead of four correlated traits gives the check its best power | None yet | `src/eda/serve_return_leads/common.py` |
| 16 Oct 14:08–14:09 | **`timeline.py`** (first run, no failure). **Seen** (men, beyond the close, β per unit of the frozen score, z, matches, blocks): R0 2025–26 0.112, **+5.59** (4,394, 21); 2013–24 0.026, +2.16 (29,895, 141); 2020–24 0.032, +1.61. T1 +4.64 / +1.52 / +0.99; T2 +2.80 / +2.29 / +1.72; T3 +3.08 / +0.88 / +0.65; T4 +3.81 / +1.75 / +1.53 (T4 is 0 before 2019). **Outcome-free:** the newest frame ends 23 Sep 2026; the unseen men's matches number 416 now, and, projected from the same days a year earlier, about 770 by 31 Oct, 1,040 by 31 Jan 2027, 2,090 by 31 May, 2,920 by 31 Aug, 3,400 by 31 Dec 2027. **Power of R0, one look at one-sided 0.05** (fully real / 0.45 survives / back to 2013–24): now 0.32 / 0.14 / 0.09 (3 blocks); 31 Jan 2027 0.76 / 0.28 / 0.14; 31 May 0.97 / 0.48 / 0.21; 31 Aug 0.996 / 0.62 / 0.26. Three Pocock looks (Jan/May/Aug 2027): 0.99 / 0.46 / 0.15 | How long a check needs | The seen readings above; unseen: counts only | `data/studies/serve_return_leads/timeline.json`, `timeline.csv` |
| 16 Oct 14:09–14:10 | **`readings.py`** (the study's one reading path) written; the test run reproduces R0 exactly. **Seen, new:** R0 beyond the model's both-stages forecast, 2025–26: β 0.089, **z +4.59**; 2020–24: z +0.24. R0's part orthogonal to the model's inputs reads about 0, as it must for a combination of the model's own inputs | **The model left most of the 2025–26 signal unused**, while it had absorbed the 2020–24 one. This is the "too timid" reading of edge anatomy, now on one score | R0 beyond the model, 2020–Jul 2026 | `src/eda/serve_return_leads/readings.py` |
| 16 Oct 14:10 | **Outcome-free check** of `data/studies/surface_ios/surface_features.parquet`: the per-player surface-effective ratings' A − B equal the frame's IOS inputs to correlations of 0.996–0.999, with small differences (older tables). It holds point-level ratings (`spw`: serve points won, O and D) per player per match | The cleaner serve/return versions need per-player point-level ratings; the IOS model (`ios_time.py`: logit rate ~ O_server − D_returner) shows **the model's return ratings already measure each returner against each server's normal level**. So the owner's first cleaner version, as I worded it on 13 Oct, is what the model already has; the new version is the non-additive one (PS10) | None | — |
| 16 Oct 14:11 | **Two subagents launched in the background** (general-purpose, Opus): the speed builder ([brief](briefs/01_speed_builder.md), verbatim) and the return-elasticity builder ([brief](briefs/02_elasticity_builder.md), verbatim). Both read outcomes only through `readings.py`, edit no existing file, and register directions before reading | Parallel, independent builds | — | — |
| 16 Oct 14:13 | Scales frozen (outcome-free) | — | — | `data/studies/serve_return_leads/lock_in_scales.json` |
| 16 Oct 14:15 | **The lock-in frozen** ([lock_in.md](lock_in.md)): the four traits, columns, directions, scores, H0 (R0), HS (speed), H1–H3 (gatekept), matches from 29 Jul 2026, the registered fit, secondaries. **The schedule is left to the owner** (the actionable-horizon preference: say the timeline before freezing), with three looks in 2027 recommended; a look before a schedule is written is invalid. **SHA-256:** `lock_in.md` `99cd7852a82979da64d8e8bf5bd6def372ae5f9be0259276791988ef16ec731e`; `lock_in_scales.json` `2547980b0367e38bc8a8eecb89cdd07204b08990b050c0528d90aeba6773635c`; `common.py` `501462dfd5926ea508249e71c6efb75d1b89166ce707e3e930d1b43688a128fa`; `timeline.py` `16ac61f9987be73f0afb7173cd806d515c12aa063142ee9e4ebafdd9e8a3d81c`; `look.py` `4923f9bae3dfe8f833e7c608b417655c5f3ae674aa6d0429e23cfe8b4ef830f5` (equal to unpriced leads' registered hash: unchanged) | The owner's step 1 | As above | `docs/studies/serve_return_leads/lock_in.md` |
| 16 Oct 14:15 | **Registered before reading** (`decompose.py`), men, A − B, directions: SP point-level serving (`srf_O_eff_spw`) −; RP point-level returning (`srf_D_eff_spw`) +; ST balance SP − RP −; TOT SP + RP (control, read two-sided); HX = `iosO_hold` minus its projection on SP −; BX = `iosO_bp_saved` minus its projection on SP −; RX = `iosD_hold` minus its projection on RP +; unpriced leads' luck columns PS03_hold, _save, _break, _conv, _net (91-day) and PS03_hold_h365, PS03_save_h365, all −. Joint sets: [SP, HX, BX, RP, RX], [SP, RP, PS03_hold, PS03_save], [ST, TOT], [T1, T2, T3]. **The question:** is "serving over-rated" about point-level serving (SP, ST) or about the game-level excess beyond points (HX, BX, luck)? | Separates the two mechanisms of the 13 Oct explanation: style (serving per se) against luck (break points and holds beyond points) | None yet | `src/eda/serve_return_leads/decompose.py` |
| 16 Oct 14:16–14:19 | **`decompose.py`** (first run, no failure). **Seen, men, raw, beyond the close** (z: 2013-16 / 17-19 / 20-22 / 23-24 → 2013-24; 2025-26): **save luck PS03_save +1.43 / +1.11 / +2.49 / +1.65 → +3.12; +2.61**; **hold luck PS03_hold +2.05 / +0.74 / +3.16 / +0.41 → +2.97; +2.32**; net luck +2.43; +1.80; break luck +0.90; +1.00; conversion luck +1.83; +0.26; 365-day hold / save luck +0.27 / +1.18; +1.95 / +1.51. **Point-level:** balance ST −1.01 / +1.77 / +0.48 / +0.53 → +0.85; **+3.44**; SP +0.78; +2.68; RP +0.81; +2.87; **TOT (total point-level strength) +0.15; −0.09**. **Game-level excess:** HX +1.90; +2.25; BX +1.54; +1.72; RX +0.03; −0.32. Beyond the model, 2020–24: save luck +2.08, hold luck +1.48; the in-model traits and the point-level scores about 0. Orth readings of in-model combinations (T1–T3, R0, SP, RP, ST, HX, BX, RX) are numerical noise: their orthogonal part is about 0 (HX and BX's orth parts equal −SP's), so only their raw readings mean anything. Joint fits, 2025–26: [ST, TOT] ST +3.42, TOT −0.17; [T1, T2, T3] T1 +2.07, T2 +2.28, **T3 +0.31**; [SP, RP, hold luck, save luck] +1.41, +0.22, +1.07, +1.75; 2013–24 the same set +0.59, −0.05, +1.20, +1.86 | The decomposition registered at 14:15 | As listed | `decompose_single.csv`, `decompose_joint.csv`, `decompose_corr.csv` |
| 16 Oct 14:19–14:23 | **Checked the joint fits for a fault** (T1's SE doubled when T3, correlated 0.06 with it, was added). Printed the Hessian and the cluster sums: no fault. **Given the price, T1 and T3 are correlated about 0.64:** each correlates about 0.5 with the close's log-odds in the information metric (−0.52, +0.47), because at a fixed price a stronger server must be a weaker returner. So the two findings are one: **at a given price, the close over-weights serving relative to returning.** The joint split between T1 and T3 is weakly identified. The single balance (ST, or R0) is the right statistic | The decomposition's interpretation depends on it | Diagnostic numbers only | — |
| 16 Oct 14:20 | **Peer session** (`tennis-predictions-d0`) announced a new accepted lower-level package and tonight's instance switch, and asked whether this session reads `accepted.json` or `selected_instance.json`. Replied: no, the reads are the frozen 10 Oct frame, `surface_features.parquet`, the luck values, `analysis.parquet`, the speed panels and Stage 0's box scores | Coordination | — | — |
| 16 Oct 14:24–14:26 | **`plain.py`**, the owner's large-gap view (focal = the player higher on the oriented statistic; clear gap = more than one RMS). First run against the raw close; **its control TOT read +1.37 points in 2013–24 (favourites beat the raw close: the price curve's favourite–longshot tilt), so a statistic that picks favourites would borrow it. Re-run against the recalibrated close** (the test's own base, s·L + k·L\|L\|, fitted per window): TOT +0.50 [−0.26, +1.27]. **Seen, clear gap, surprise in points** (2013–24; 2025–26): save luck **+1.35 [+0.44, +2.26]; +2.76 [+0.14, +5.38]**; hold luck +1.14 [+0.23, +2.06]; +1.68 [−1.07, +4.43]; R0 +1.09; +2.51; T1 +0.65; +3.01; T2 +0.42; +1.72; T3 +0.33; +1.68; ST +0.05; +0.53; TOT +0.50; −0.05. Read from the focal side: the man whose recent break-point saving clearly ran ahead of his serve points was priced at 48.7% and won 47.3% (2013–24), and was priced at 48.3% and won 45.5% (2025–26) | For the README's plain explanation | As listed | `plain.csv` |
| 16 Oct 14:27 | **A combined luck score** (mean of oriented save and hold luck, RMS-scaled on 2013–24; defined at 14:26 as the natural one-number luck statistic, before reading). **Seen, raw, beyond the close:** +1.95 / +1.01 / +3.05 / +1.05 by era → **2013–24 +3.39 (β 0.043 per SD); 2025–26 +2.66 (β 0.090)**; beyond the model 2020–24 +1.95, 2025–26 +2.07; orth (beyond the model's inputs) 2013–24 +1.80, 2025–26 +0.87 | One number for the luck mechanism | As listed | — (inline; numbers in this row) |
| 16 Oct 14:28 | **`timeline_clean.py`**: the power of one look (one-sided 0.05) for the cleaner candidates, by date (2025–26 in full / 0.45 of it / the 2013–24 strength). **Luck score:** 31 Jan 2027 0.30 / 0.13 / 0.13; 31 Aug 2027 0.66 / 0.24 / 0.25. **ST:** 0.42 / 0.16 / 0.08; 0.84 / 0.33 / 0.11. R0 as before (0.76 → 1.00 in full). **Inferred: the steady luck signal is small per match, so a check on unseen matches cannot resolve it before 2028 at its long-run size. Its evidence is the 13-year record; a forward check is the tool for the new, large signals (R0, ST, speed)** | Shapes the recommendation: what to wait for, what to decide on the record | Power only | `timeline_clean.csv` |
| 16 Oct 14:30–14:31 | **Robustness on seen matches** (raw, beyond the close; z all / completed only / Slams out / Pinnacle months / BetOnline months). R0 2025–26: +5.59 / +4.81 / +5.07 / **+2.91 / +5.43**; 2013–24: +2.16 / +2.15 / +1.16. ST 2025–26: +3.44 / +2.96 / +3.77 / **+1.30 / +3.33**; 2013–24 +0.85 / +0.77 / −0.11. Speed T4 2025–26: +3.81 / +3.72 / +2.48 / **+1.56 / +3.70**. Luck score 2025–26: +2.66 / +2.57 / +1.62 / **+1.36 / +2.81**; 2013–24 +3.39 / +3.09 / +2.89. **Found: in 2025–26 every signal is about twice as strong against BetOnline's close (Sep 2025 – Jul 2026, about 2,170 matches) as against Pinnacle's (Jan – 7 Sep 2025, about 2,200).** Per match, R0 against Pinnacle in 2025 is still about 5× its 2013–24 strength. **Consequence:** the unseen matches can be checked only against BetOnline's close (Pinnacle's closes after Sep 2025 are not held), while live bets use Pinnacle's live line where it exists. A check against BetOnline can overstate the edge at Pinnacle. To go in the addendum as a disclosed secondary, and to the owner as another reason to buy Pinnacle's closes | Where a flaw could hide: the benchmark changed in the very window where the traits were found | As listed | `robustness.csv` |
| 16 Oct 14:32 | **Same matches, both books** (men; Pinnacle's and BetOnline's own margin-free closes from the instance's book prices; z against Pinnacle / BetOnline). **2025, 2,101 matches:** R0 +2.53 / +2.53; ST +1.17 / +1.18; speed +1.35 / +1.40; luck score +1.44 / +1.41; T1 +2.44 / +2.31; T3 +1.39 / +1.64. **2023–24, 5,043 matches:** all within ±0.9 (R0 +0.54 / +0.50; speed −0.88 / −0.86; luck +0.19 / +0.21). **So the 14:30 split is a change over time, not BetOnline's softness:** on the same 2025 matches the two closes price these traits alike. The signal grew from 2025 into Sep 2025 – Jul 2026. Whether BetOnline's line drifted from Pinnacle's after Sep 2025 cannot be tested without Pinnacle's later closes | Resolves the 14:30 concern, mostly | As listed | `same_matches_books.csv` |
| 16 Oct 14:32–14:33 | **`check.py`**, the lock-in's check, written before any unseen result exists. It reads the unseen window only with `--owner-go`, refuses a start before 29 Jul 2026, and checks the frozen scales' hash. **Dry run** (the seen window, the code only): R0 +5.590, T1 +4.635, T2 +2.801, T3 +3.076, T4 +3.806, equal to the readings above, so the code reproduces them. Its "confirmed" verdicts are meaningless in the discovery window. Without `--owner-go` it exits. **SHA-256:** `check.py` `0a593a85b728745cbaa38f161963c77aefc5bedff739bbc83a64ffe285c82856`; the dry run's `result.json` `3e3927e4530e4c4f664aff9095d201e64a50830b32d8ccee31836072657f789f`; `readings.py` `7454b446f3ab4660f73cb00678d8d871066b82cf6de1bf65bc78817ba5f24177`; `decompose.py` `fb89b427824bd00285eae6d20a4d93b63986d717b28d3fb4d28538adcbc4c60c` | The code fixed before the data, as unpriced leads did | Seen readings only | `src/eda/serve_return_leads/check.py`, `data/studies/serve_return_leads/checks/dry-run/` |
| 16 Oct 14:12–14:48 (the helper's own times) | **The return-elasticity builder (PS10) reported** ([memo](team/elasticity_builder.md); its chronology is there).
* **Construction:** per returner, the slope of his return-point residuals against the IOS prediction (pre-match `srf_*_eff_spw`) on the server's time-centred O. Half-life 365 days, lf + 1 ≤ es, shrunk each 1 January toward the population slope. The matchup term is A − B.
* **Checks:**
  * mapping: return points equal the opponent's serve points on 569,412 rows; μ matches on 252,919; the IOS prediction is calibrated, slope 0.95–1.03;
  * brute force: 293 targets to 3e-13;
  * timing probe: 0 changes at future rows; the 1 January constants move only for targets after the cut, as the rule allows.
* **Reliability (outcome-free):** men's split-half 0.08–0.20 weighted; the median shrink factor is 0.06–0.18. Women: no stable trait.
* **Points check** (the target match's own return points; no result read): men 2013–24 slope 1.01 (z 6.6), so the trait is real in the points; unresolved in 2023–24 (0.54) and 2025–26 (0.24).
* **The only result read** (14:41:43–14:42:09, seen window): men beyond the close 2013–24 +0.010 [−0.019, +0.039], P 0.76; 2025–26 −0.011, P 0.35; beyond the model 2020–24 −0.001, 2025–26 −0.015. All unresolved. Women 2013–24 +0.015 (P 0.82).
* **A benchmark added after the readings** (disclosed by the helper as outside its pre-set rule): if the close priced none of it, the points-calibrated size implies +0.062 per RMS in 2013–24. The reading sits 3.5 SE below, so the close very likely prices most of it.
* **Compliance note:** 31 men's and 30 women's seen matches (events of 27–28 Jul) could start after 29 Jul, and their ratings may hold later box scores. Re-read with them set to 0: men 2025–26 −0.010, unchanged.
* **The helper's recommendation:** do not register for the unseen check; "not admitted" to the feature pool; PS10 does not explain the 2025–26 returning mispricing.

**My reading:** I agree. The rule it wrote before reading (P(β > 0) ≥ 0.95, raw and orth, men 2013–24) fails at 0.76 and 0.59. The 2025–26 points show no non-additive pattern | Brief 02 | The helper's readings | `src/eda/serve_return_leads/elasticity.py`, `data/studies/serve_return_leads/elasticity/` |
| 16 Oct 14:12–15:10 (the helper's own times) | **The speed builder reported** ([memo](team/speed_builder.md); directions registered at 14:28:18; the only look at results was 15:01:00–15:04:18, through `readings.py`).
* **Reproduction:** `build_on` on the augmented history reproduces `spd_L_B` exactly (0 mismatches, 20 columns, 63,737 matches).
* **Found:** the stored speed file has no men's 2018 matches (`frame_keys` lacks the season). The helper added them as extra targets, outcome-free; production fits from 2019, so it is unaffected.
* **What was built:**
  * `spd2_L_B` and `spd2_T_B`: the second serve, its constants scaled from the frozen first-serve ones outcome-free; a sensitivity build with the frozen constants has r 0.995;
  * `gap_L_B`: the form of the first-minus-second gap;
  * `fault_dev_28`: Slam files only, 439 seen matches, descriptive;
  * `fade_dev_14`: point-ordered Slams from 2011 and the tour 2021–24; 8–81% of matches by year.
* **Probes:** 19 cut days each; 0 values moved; every leaky control was caught. The fault probe needed its peek widened to the weekly feed's Slam lag (30 days).
* **Readings, raw, beyond the close** (eras; 2013–24; 2025–26):
  * **`spd2_L_B` +1.86 / +2.03 / +2.12 / +0.75; +2.76; +1.90** (orth 2013–24 +2.54; beyond the model 2020–24 +0.97, 2025–26 +1.54);
  * `spd_L_B` +0.38 / +1.46 / +3.97 / −0.41; +1.94; +3.81;
  * gap −0.85 (2013–24); fade +0.58; fault: an artefact (6 blocks).
* **Joint fits, 2013–24:** first serve +0.84, second +1.98 (P 0.975); 2025–26: first +2.81, second +1.02. Joint with the gap, 2013–24: first +2.73, gap −1.73.
* **The helper's recommendation:** register `spd2_L` (+). Do not register the gap, the fade or fault speed. P9 is the only route to a real tour test of the fade and fault speed.

**My reading:** I agree. Second-serve form is steady by era (all four positive beyond the close), and its gain beyond the model is unresolved. **Also found:** my own T4 readings of 2013–24 (+1.75) count speed as 0 before 2019, because edge anatomy's analysis table starts in 2019. The helper's full-history `spd_L_B` reads +1.94. Speed's 2013–24 numbers in the README use the helper's reading | Brief 01 | The helper's readings | `src/eda/serve_return_leads/speed_ext.py`, `speed_read.py`, `data/studies/serve_return_leads/speed/` |
| 16 Oct 15:12 | **Outcome-free:** the speed builder's files are final (last written 15:10). The live speed panel has second-serve speeds on every men's row from July 2026, the daily collector's 182 October rows included; the panel's last day is 5 Oct 2026 | Can a second-serve check be built for unseen matches? Yes | Counts only | — |
| 16 Oct 15:13 | **`addendum_scales.py`:** C1 (luck: save and hold luck), C2 (the balance ST), C3 (`spd2_L_B`); frozen scales on the lock-in's window (4,336 men's matches). Seen readings as registered, identical to the earlier ones: C1 +3.39 (2013–24), +2.66 (2025–26); C2 +0.85, +3.44; C3 +2.76, +1.90. **Power by 31 Aug 2027** (full / 0.45 / the 2013–24 strength): C1 0.66 / 0.24 / 0.25; C2 0.84 / 0.33 / 0.11; C3 0.43 / 0.16 / 0.15 | The addendum's inputs | As listed | `addendum_scales.json`, `addendum_seen.csv`, `addendum_power.csv` |
| 16 Oct 15:15 | **Addendum 1 frozen** ([lock_in_addendum_1.md](lock_in_addendum_1.md)): HC1–HC3, one family, Holm at each look's level on the lock-in's schedule; values rebuilt at the look with the registered code, reproduction first. Not registered: PS10, the gap, the fade, fault speed. The stamp was first written as 15:16 and corrected to the clock's 15:15 before hashing. **SHA-256:** addendum `905ca2df94b2a719e55e052cf6c5e0ef32b70e13cf35788a20ec50864669e3a2`; the lock-in unchanged (`99cd7852…`); `addendum_scales.json` `b402e4e6…`; `speed_ext.py` `28550730…`; `build_luck.py` `1286a62e…` (equal to unpriced leads' registry); luck values `092d423c…` (equal); `builder_columns.parquet` `5bafccfb…`; `surface_features.parquet` `ba8514e8…`; `speed_read.py` `422964ac0eb71b250afa4016cb3b0ec1d29712d3a67251a11a9aa245878a4964`; `elasticity.py` `ab2cd2f1021d94a289227b776fb3085b86adb4769d8562fb5e2b96a99e70935a`; full hashes in the addendum's § 8 | The owner's "build cleaner versions", locked before any unseen read | — | `docs/studies/serve_return_leads/lock_in_addendum_1.md` |
| 16 Oct 15:16–15:17 | **The inline readings of 14:30 and 14:32 saved as `robustness.py`** and re-run: identical (max \|Δz\| 0 on 32 and 24 rows). The comparison copies of the inline files went to the system temp folder (`%TEMP%/claude_robustness_inline.csv`, `claude_books_inline.csv`), not the session scratchpad; they are left in place (no deletion mid-session) | Reproducibility | The same readings | `src/eda/serve_return_leads/robustness.py` |
| 16 Oct 15:15–15:18 | README completed (§§ 1, 5.3, 5.4, 6, 7). One correction while writing: § 7's speed bullet first said the 2017–19 speed readings lack 2018; the helper's readings include 2018 (extended keys); corrected before reporting | Report | — | `README.md` |
| 16 Oct 15:18 | **Index row added** to `docs/studies/README.md` (read fresh first; another session added a row today). **Checked:** no file under the imported production code or data (`serve_speed_tabpfn`, `infosys_atp_backfill`, unpriced leads' `build_luck.py`, `screen.py`, `look.py`, `match_timing`, `edge_anatomy`, the speed panels and columns, `surface_features.parquet`) changed since 13:50. `look.py` and `build_luck.py` still equal their registered hashes. Reported to the owner | Finish before reporting | — | — |
| 22 Oct 11:20 | **Resumed** (same conversation; the instruction files were re-read at the session's start: CLAUDE.md now carries the 20 Oct Thinking-beside-local decision, the 21 Oct closing-line rule (TennisExplorer's time-stamped Pinnacle from 1 Nov 2025, at the next retrain; the test build deferred by the owner) and the 20 Oct live-rows amendment; a new memory, "freeze only what is named"). **The owner, verbatim:** "'Don't wait for 2027 on the two steady signals. Break-point luck and second-serve speed are small per match, so even by late 2027 a check confirms them only 1 time in 4 to 7. Their evidence is the 13-year record. I'd add both to the feature pool now as leads. When you want model changes, they're candidates to compare in the usual way: luck as a men's adjustment on top of the model, second-serve speed as a second term in the speed stage.' Where are we in this process? Does our in production betting take this into consideration? Should it?" **Read as:** report the state since 16 Oct, what production uses today, and my recommendation, with evidence. Nothing in production changes | — | — | — |
| 22 Oct 11:23–11:25 | **State, outcome-free:**
* this study: untouched since 16 Oct 15:18; no decision cites it;
* the five-pattern switch: on, b = 0.0616, unchanged;
* the selected instance: `template_2026-10-21b` (frame to tournament date 12 Oct 2026; men from 29 Jul: 571, from 24 Sep: 155; odds input BetOnline 538, the books' average 33: the old rule);
* the feature universe: no row or note for these leads;
* the speed stage: no second-serve term anywhere in the engine (`grep spd2`);
* the notebook: `MODEL = "tabpfn35"` (local).
* **The latest live run** (`live_2026-10-21_203628`, 23 matches): the luck group's three members gated off for October 2026 (box-score supply against a year earlier: men 0.573, women 0.386, bar 0.70), so G1 adds nothing to today's bets; G4's lower-level pair is not built and counts 0. | What production uses | Counts and switches only | — |
| 22 Oct 11:24 | **Peer session** `tennis-predictions-0a` asked whether this session edits the daily engine or the prediction code (it is building the owner's 22 Oct qualifying-bets decision). Replied: no, reads only; the 11:23 change to `dp_steps.py` was not this session's | Coordination | — | — |
| 22 Oct 11:25–11:26 | **`production_view.py`** (seen matches only). **C1 (luck), beyond the model's both-stages forecast:** 2020–24 β 0.037 per SD, z +1.95, in-window gain +0.14 mLL; 2025–26 β 0.070, z +2.07, +0.50 mLL. **A size by the five-pattern template** (prior 0.45 × the 2013–24 β beyond the close, updated with the 2025–26 β beyond the model): **0.032 log-odds per SD**, which shifts a men's match at even odds by a median **0.5 points**, 1.6 at the 95th percentile, for a plausible gain of 0.10 mLL per match. **C3 (second-serve speed), beyond the model:** 2020–24 z +0.97, 2025–26 +1.54; size 0.019 per SD; a median 0.3 points, 1.0 at the 95th percentile; 0.04 mLL. **Against the comparison's resolution** (about ±0.35 mLL for `compare.py` over both tours, 2020–24): below it for both. A model comparison can only serve as a harm check; the β reading beyond the model is the sensitive test, as in the five-pattern check | Shapes "should it" | As listed | `src/eda/serve_return_leads/production_view.py`, `data/studies/serve_return_leads/production_view.json` |
| 22 Oct 11:27 | **Correction of the 16 Oct 14:26 row and of judgment call 8.** They say the luck score is "the equal mean of save and hold luck, the two the luck builder rated promising for men; defined before reading". **That is wrong on two counts:**
* the luck builder rated hold luck and net luck promising, and called the four pieces (save among them) not promising separately;
* when I defined the score at 14:26, the 2025–26 readings of every PS03 piece had been seen (14:16–14:19): save +2.61, hold +2.32, net +1.80, break +1.00, conversion +0.26.

So choosing save plus hold over net was partly informed by 2025–26. **Save luck alone is the owner's own definition** ("break points saved beyond what the player's overall serving predicts", 16 Oct, from my 13 Oct wording), fixed before any of its readings. Read the same way (11:28): beyond the close 2013–24 +3.12, 2025–26 +2.61; **beyond the model 2020–24 +2.08, 2025–26 +1.98**, the same story as C1. **Net luck** (the five-pattern adjustment's G1 member) is much weaker beyond the model: +0.29 and +1.50. Addendum 1 stays as frozen; this row records how C1 came to be | Correct by adding | Seen readings, as listed | `decompose_single.csv` |
| 22 Oct 11:28 | **Recorded:** the lock-in's § 5 says "the frame's odds input, margin-free (in this window BetOnline's closing line …)". The definition governs: an instance built under the 21 Oct rule carries TennisExplorer's time-stamped Pinnacle close from 1 Nov 2025, so a look on such an instance reads against Pinnacle. The parenthesis described the instances of 16 Oct. Not a change to the lock-in | — | — | — |
| 16 Oct 14:15 | **Correction (clock):** the rows and § 3 header stamped "14:05–14:20" and "14:20" were written between 14:05 and 14:08; `date` read 14:12 afterwards. The R0 row is re-stamped 14:07 with its original stamp kept beside it. No choice depended on the stamps | Rule: correct by adding | — | this log |

## 3. The assessment (written 16 Oct 14:05–14:20, before any new reading)

### 3.1 What has been seen

| Matches (men's main tour) | Seen by | For what | Status for these four traits |
|---|---|---|---|
| 2013–2024 | edge anatomy (the ledger by era); unpriced leads (about 500 statistics screened) | Discovery | Seen: in-sample |
| 1 Jan 2025 – 28 Jul 2026 (4,394 men's) | edge anatomy (the traits were **found** here); unpriced leads' check of 13 Oct (the five patterns) | Discovery for these traits | Seen: cannot confirm them |
| 29 Jul – 23 Sep 2026 (416 men's) | unpriced leads' check of 13 Oct read their results once, for the five-pattern score beyond the model. G1 (luck) was switched off there by its box-score gate; the speed term was 0 (no speed values in the forecasts' column) | A different, orthogonalised statistic | Not read for these traits. Lightly used: disclose, and include |
| 24 Sep 2026 → today | Nobody: not in the tables yet (the 14 Oct frame ends 23 Sep) | — | Unseen; enters at the next table rebuild |
| From today on | Live forward | — | Unseen |

So "the unseen matches" are one stream: everything from 29 Jul 2026, of which 416 men's matches are in the tables today and the rest arrive with each rebuild. For these traits it will mostly be live forward data, because only 11 weeks had passed by 23 Sep.

### 3.2 The order

(Recorded in full in the README, §§ 1 and 3; the numbers are the chronology's rows of 14:08–14:09 and 14:28.)

*Added 14:35: the "§ 3 written 14:05–14:20" header above was written by 14:08; see the correction row.*

## 4. Judgment calls

1. **R0 as the single primary** (14:07, before any reading). The owner named four traits; one combined score of the three serve/return traits, with equal weight per trait, gives the check its best power. Speed has its own test, because it is a separate stage of the model and was unstable by season. *Seen:* the edge-anatomy ledger's per-trait readings only.
2. **Frozen scales from the discovery window** (14:13): the score is a fixed function of the inputs, so its β compares directly with the seen β. Scale drift across rebuilds changes only the units, never the sign.
3. **The schedule left to the owner** (14:15): the actionable-horizon preference says to state the timeline before freezing. The traits, directions and test were frozen now; the timing waits for the owner, and a look before it is written is invalid.
4. **The 416 matches read on 13 Oct for the five patterns are included,** with a disclosure and a secondary without them (14:15). The five-pattern score was projected off the model's inputs (these traits among them); its luck group was gated off and its speed term was 0 there. So almost nothing about these traits was learned from them.
5. **"Return quality against each server's normal level" was reinterpreted** (14:10). The model's IOS defence is exactly that, additively. The new version is the non-additive elasticity (PS10), given to a helper. The README says so plainly: the 13 Oct wording described a measure the model already has.
6. **The decomposition was registered before reading** (14:15), with directions. TOT was read two-sided as a control.
7. **The plain tables were switched to the recalibrated close** (14:25), after the control TOT showed the raw close's favourite–longshot tilt (+1.37 points).
8. **The luck score** (14:26) is the equal mean of save and hold luck, the two the luck builder rated promising for men; it was defined before reading.
9. **The luck part is to be decided on the record, not on a forward check** (14:28): at its long-run size the check's power stays near 25% through 2027.

## 5. Threats to validity, and where a flaw would hide

* **Discovery-window reuse.** Every reading in this study is on seen matches, most in the window where the traits were found. The cleaner versions were chosen with those readings in view. Only the unseen check can confirm.
* **The benchmark changed inside the discovery window** (Pinnacle to 7 Sep 2025, BetOnline after). The signals are about twice as strong in the BetOnline months. On the same 2025 matches the two closes price the traits alike (14:32), so the split looks like change over time. But BetOnline after Sep 2025 cannot be compared with Pinnacle, and the unseen check can only use BetOnline.
* **The surface features are from older tables** than the 10 Oct instance (r 0.996–0.999 with its inputs). The ST, SP and RP readings could move slightly on the registered build.
* **The luck values were built by another study** (8 Oct Stage 0, timing-probed there). Their 2025–26 values had never been read against results before today, except PS03_net inside G1's group reading of 13 Oct.
* **Few clusters early.** The first looks have 6–10 four-week blocks, and t on G − 1 is then heavy-tailed. The power figures use the noncentral t; the three-look simulation draws normal increments and is approximate.
* **Multiplicity.** About 20 candidates × 7 windows × 2 forms × 2 bases were read. The claims rest on patterns across eras (luck steady; balance new), not on a single best reading.
* **The calendar projection** assumes the next year looks like the last. The off-season (Nov–Dec) adds few matches.

## 6. What a re-design would do

* Buy Pinnacle's closes from Sep 2025, re-read the discovery window against Pinnacle throughout, and check the unseen matches against Pinnacle as well.
* Build the cleaner versions on the instance's own tables (surface IOS and luck values from one build), so the seen and unseen values come from one pipeline.
* Increase the unseen information per match: the game-handicap or totals markets, if archived, would price game shares, which carry more information than wins.
* Consider Challenger matches as a second unseen stream for the luck part: it needs box scores and Challenger closes.

## 7. Claims and their evidence

| Claim (README) | Evidence |
|---|---|
| A check now would most likely say "unresolved" (32% if fully real) | `timeline.csv`, R0 row at 2026-09-23 (416 matches, 3 blocks) |
| The cleaner versions should be built first, then one check | The logic of § 3 above; `timeline.csv` (a second unseen batch takes 6–12 months to collect) |
| "Unseen" = from 29 Jul 2026; 416 in the tables; read once on 13 Oct; nothing after 23 Sep | Outcome-free counts at 14:00 (14 Oct frame); `unpriced_leads/check_now/now/result.json` (9,457 matches, last 23 Sep); `forecasts_facts.json` (speed term 0 for 416 men's matches) |
| A check can answer from early 2027 | `timeline.csv`, `timeline.json` (three-look simulation) |
| The luck part is old and steady | `decompose_single.csv` (PS03_save, PS03_hold), `addendum_seen.csv` (C1) |
| The serve-itself part is new | `decompose_single.csv` (ST), `addendum_seen.csv` (C2) |
| Overall strength is priced | `decompose_single.csv` (TOT) |
| Serving over-rated and returning under-rated are one finding | The 14:19–14:23 row (the information-metric correlations; partial correlation 0.64) |
| Return quality against the server's level is already the model's | `src/eda/match_timing/ios_time.py` (y ~ O_server − D_returner) |
| The elasticity is priced | `elasticity/readings_summary.csv`, `team/elasticity_builder.md` |
| The second serve is the steadier speed signal | `speed/readings.csv`, `speed/readings_joint.csv`, `team/speed_builder.md` |
| The signals strengthened after Sep 2025; on the same matches the two books agree | `robustness.csv`, `same_matches_books.csv` |
| The luck score reads +2.0 beyond the model in 2020–24 and 2025–26 | `addendum_seen.csv` (C1, `L_model`) |
| The combined score reads +4.6 beyond the model in 2025–26 | `decompose_single.csv` (R0, `L_model`) |
| The plain example (48.7% → 47.3%; 48.3% → 45.5%) | `plain.csv` (PS03_save, clear gap, recalibrated) |

## 8. Reviewer checklist

1. **No result from 29 Jul 2026 on was read.**
   * `common.seen()` filters tournament dates before 29 Jul and asserts it; `readings.py` is the only reading path.
   * The helpers' memos list their reads, and the elasticity helper's compliance note covers the events of 27–28 Jul.
   * `check.py` refuses a look without `--owner-go`.
2. **The lock-in and the addendum are unchanged:** their SHA-256 are in rows 14:15 and 15:15.
3. **The fit is unpriced leads' registered code:** the `look.py` hash equals its registry's.
4. **`check.py --dry-run` reproduces** R0 +5.590, T1 +4.635, T2 +2.801, T3 +3.076, T4 +3.806.
5. **Treat the orth readings of in-model combinations as noise** (row 14:16–14:19).
6. **The plain tables use the recalibrated close** (row 14:24–14:26).
7. **The speed helper's 2018 extension** is outcome-free and leaves the original rows bit-identical (its memo).
8. **The three-look power is approximate:** normal increments, with t critical values.

## 9. Reproduction

```
./python.sh src/eda/serve_return_leads/timeline.py          # when a check can answer (lock-in traits)
./python.sh src/eda/serve_return_leads/decompose.py         # the cleaner serve/return versions
./python.sh src/eda/serve_return_leads/plain.py             # the plain tables
./python.sh src/eda/serve_return_leads/timeline_clean.py    # power for the cleaner candidates
./python.sh src/eda/serve_return_leads/robustness.py        # subsets and the same-matches book check
./python.sh src/eda/serve_return_leads/addendum_scales.py   # the addendum's scales, seen readings and power
./python.sh src/eda/serve_return_leads/check.py --dry-run   # the registered check, on the seen window
```
The elasticity and speed builds: see their memos (`team/elasticity_builder.md`, `team/speed_builder.md`) for their commands.
