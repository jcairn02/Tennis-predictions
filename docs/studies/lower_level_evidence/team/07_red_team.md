# Red team: the lower-level evidence dossier, draft of 9 October 2026

9 October 2026 · Team role 07 (red team) of the lower-level-evidence study · Review of a draft, not a decision. The lead applies the fixes.

**What was checked.**
* The draft [README](../README.md), every team report (01–06, briefs) and the evidence files behind its numbers.
* About 30 numbers re-derived from the files, 12 code citations opened, the tests and the refresh run.
* One new measurement (the appendix), on seasons up to 2024 only, with the study's holdout guard.

**Ground rules kept.** Read-only except this file. No rebuild, fit or long script. No state-changing Git. Nothing deleted. No outcome of a 2025–2026 match read. The candidate builder's sandbox and `candidates/` folder were not opened.

**Keys.**
* *Observed* = read in a file or computed here (cited); *Inferred* = reasoning; *Suggestion* = a proposed fix.
* Severity:
  * **MUST FIX**: wrong against a decision in force, a leak, or a bug that destroys evidence;
  * **SHOULD FIX**: a misleading number or claim, or a gap in the proposal's logic;
  * **NOTE**: precision, wording, small bugs.
* Replacement text in quotes is written for the dossier: its links are relative to the dossier's folder.
* Scores: + = the first-named version better (lower log loss) unless stated. Following the owner's decision of today (below), a reading is "better" or "worse" only when its 95% interval clears 0; otherwise it is "unresolved", with P(better) = Φ(estimate / SE). Bias estimates (not scores) say which group is over-rated.

## Findings, most severe first

### MUST FIX

**M1. The dossier calls readings "ties" and the adoption framework "a proposal". Both were overtaken by a decision today.**
* **Where.** Keys (line 19); answer 2's table, "Results" row ("a discount ties"); §1.1; §1.3 (products row); §3.1 (women's aces); §3.4; §8.2 (products); §8.5 (C1); §9 opening ("a proposal of 9 Oct"); §9.9.
* **What is wrong.**
  * [docs/decisions/2026-10-09-adoption-framework.md](../../../decisions/2026-10-09-adoption-framework.md) records the owner adopting the framework on 9 Oct 2026 "as guiding principles, not rules".
  * Its point 3 reads: "No comparison is called a 'tie.' … Say 'better' or 'worse' when the 95% interval clears 0; otherwise say 'unresolved' and give P(better)."
  * The owner's standing preference on direction labels was updated the same day: "Never 'tie'".
  * My brief (and the lead's convention) still said "tie". Role 02 already followed the new rule. The dossier went back to "tie".
  * The label also hides leans:
    * the ×0.75 Elo discount of men's ITF results is P(better) 0.96;
    * product centring is P(better) 0.33, a lean *worse*.
* **Evidence.** P(better) computed from each cited interval (SE = width / 3.92):

  | Dossier text | Replacement |
  |---|---|
  | Keys: "A 95% interval that spans 0 is a **tie**." | "'Better' or 'worse' when the 95% interval clears 0; otherwise 'unresolved', with P(better) = Φ(estimate / SE) (the owner's decision of 9 Oct 2026). Verdicts on declared primaries only; other cells are flags." |
  | §1.1: "−0.48 [−1.09, +0.14] mLL (a tie, …)" | "−0.48 [−1.09, +0.14] mLL (unresolved, P(better) 0.06: it leans worse; + = the version with Challenger rows better; 2022–2024)" |
  | §1.1: "turned the edge over the close into a tie" | "cut the edge over the close from +0.93 [+0.09, +1.76] to +0.45 [−0.65, +1.55] (unresolved, P 0.79), and the model's realisation from 0.91 to 0.63. The framework's worked example rejects it on that gate." |
  | §1.3 and §8.2: "centring removes it and tied" / "product centring tied" | "centring removes the drift. At the close it reads −0.06 [−0.33, +0.21] mLL (+ = centred better; unresolved, P(better) 0.33: it leans worse in every reading, 2022–2024 −0.05 [−0.21, +0.11])" |
  | §3.1: "+0.1 (tie)" | "+0.1 (interval spans 0)" |
  | Answer 2 "a discount ties"; §3.4 "×0.75 tie; ×1.25 is worse" | See S13 for the wording |
  | §8.5: "the share as a 59th input tied (event levels C1)" | "the share as a 59th input read +0.06 [−0.10, +0.23] (unresolved, P(better) 0.76; event levels C1)" |
  | §9: "the adoption framework (a proposal of 9 Oct)" | "the adoption framework (adopted by the owner on 9 Oct 2026 as guiding principles, not rules; [decision](../../decisions/2026-10-09-adoption-framework.md))" |
* **Also.**
  * Reports 01, 03 and 06 use "tie" throughout. The lead decides whether to fix them or add a one-line note at their heads.
  * `compare.py` now prints "unresolved" and `p_better`. Paste its §7 readings as printed.

**M2. §9.9 presents product centring as adopted. It was not, and it leans worse.**
* **Where.** §9.9: "A free, reversible change that protects against a known harm can be adopted on mechanism when it ties, as the product centring was."
* **What is wrong.**
  * The [centring study](../../ios_product_centring/README.md) is headed "A study, not a decision: it changes no decided file". Its line 36 says adoption is the owner's decision.
  * No decision record adopts it (`docs/decisions/`, 9 Oct).
  * Its readings at the close lean worse: primary −0.06 [−0.33, +0.21], P(better) 0.33.
  * CLAUDE.md: "New research also does not become a decision merely by being written."
* **Fix.** "Under the framework, a free, reversible change needs only to point the right way (cost 0). A change that prevents a known harm can be suggested on mechanism, and the owner decides. The product-centring study recommended centring on mechanism; the owner has not adopted it. At the close it leans worse in every reading (primary −0.06 [−0.33, +0.21], P(better) 0.33)."
  * Say the same where centring enters candidate 2 (§8.2, §8.6.2, Decision 6).

**M3. The ITF plan fits its offsets on the seasons its candidate is scored on: a leak in the test years.**
* **Where.**
  * §8.3.2: "First estimate its own offsets, weights and tier prior on 2018–2024 … with the windows moved (§10)".
  * §8.3.3: "then … as a candidate against the frozen reference".
  * §8.6.3; §10.2's `--fit-window 2018-2021 --tune 2019-2021 --validate 2022-2024`.
  * [briefs.md](briefs.md):116: "the ITF offsets estimated on 2018–2024".
* **What is wrong.**
  * `compare.py` scores the candidate on 2020–2024 (`current_best_model/compare.py:69-72`; decision of 8 Oct).
  * Constants fitted on 2018–2021 or 2018–2024 would carry the outcomes of 2020–2024 into those seasons' inputs.
  * The decided convention is the opposite. The [match-clock decision](../../../decisions/2026-10-05-match-timing.md) table freezes normalising constants on 2010–2018, "No leak in the test years". The [feature-provenance study](../../feature_provenance/README.md):126 and :193 say every tuned constant "predate[s] the test seasons".
* **Fix.** Replace §8.3.2 with: "**First estimate its own offsets, weights and tier means walk-forward:** for season Y, from ITF box scores of 2018 .. Y − 1 only, under the two-time rule (never 2025–2026). `translation.py` with moved windows (§10) is the statistic-level review. Its fixed 2018–2021 set must not be carried into a model candidate scored on 2020–2024. If a fixed set is used, pre-register scoring on the seasons after its fit window only (2022–2024 for a 2018–2021 fit)."
  * Fix §8.6.3, the §10.2 comment and briefs.md:116 to match.

**M4. §9's test plan omits the decided match clock and its leak probe for every cross-player quantity the proposal fits.**
* **Where.** §9.2: "Walk-forward everything: offsets, weights and tier means for season Y are fitted on seasons before Y." §9 never mentions `probe.py`.
* **What is wrong.**
  * The [match-clock decision](../../../decisions/2026-10-05-match-timing.md) point 1 covers "ratings solved for all players together (IOS) …, batch fits, and statistics of a field".
  * Each of these combines other players' results:
    * offsets and weights refitted per season;
    * home-tier means (a batch fit: `translation.py:656-678`);
    * the product centring level;
    * the joint-solve norm offered as the forms' alternative.
  * They must use the two-time rule (in at lf + 1, read at es), not "seasons before Y" by tournament date. The leak probe is required (CLAUDE.md, "Checking new work"; framework §5).
  * The first candidate is compliant as designed:
    * its offsets are frozen on 2010–2018, the decided convention for normalising constants (no leak in 2020–2024; in-sample for 2013–2018 training rows exactly as the reference's own constants are);
    * its invariance gate implies it changes only each player's own matches.
  * The dossier says neither.
* **Fix.** Replace §9.2 with: "**Walk-forward everything, on the match clock.** Offsets, weights and tier means for a match are fitted only on results that surely finished before it could start (the two-time rule of 5 Oct 2026: in at lf + 1, read at es). Every candidate that changes a cross-player quantity passes `src/eda/match_timing/probe.py` before any score: walk-forward offsets or weights, tier means, product centring, a joint-solve norm for the forms. Constants tuned on pooled histories are re-tuned on 2013–2018 for an arm that changes a solve."
  * Add to §7: "Its offsets are frozen on 2010–2018: the decided convention for normalising constants (no leak in the scored seasons; in-sample for the 2013–2018 training rows, like every constant of the reference). It changes only each player's own matches, so it needs no probe. The walk-forward refit (§9.2) is for adoption, not this first test."

**M5. `refresh.py` overwrites the first run's evidence when run on a candidate without `--label`, and skips the diff in silence.**
* **Where.** `src/eda/lower_level_evidence/refresh.py`.
* **What is wrong (observed in the code).**
  * `--label` defaults to `BASE_LABEL` (`:305`).
  * `step_commands` passes it to `composition.py` (writes `composition/<label>/`, `composition.py:1007`) and `translation.py` (writes `translation/<label>/`, `translation.py:1391`).
  * `refresh.py --stage0-dir <candidate>` with no label therefore:
    * rewrites `composition/reference_2026-10-08/` and `translation/reference_2026-10-08/` with the candidate's numbers;
    * rewrites the base snapshot (`:321-326`);
    * starts reading a new `incoming/reference_2026-10-08/` instead of the first run's `incoming/` (`:64-69`);
    * skips the diff because `label == base` (`:328`), with no message.
  * The dossier cites those folders throughout.
  * `composition.py` and `translation.py` have the same default label (`composition.py:86`, `translation.py:92`).
* **Observed in the run.** The brief's `refresh.py --steps snapshot,diff --label reference_2026-10-08` exited 0.
  * It rewrote `snapshots/reference_2026-10-08.json`: same 68,920 bytes and inputs; `generated_at` changed from 09:02 to 09:08 local.
  * It ran no diff at all, so it is not a "no-op diff".
  * The real no-op check is `test_refresh.py:116`, `R.diff(s, s) == []`. It passes.
* **Fix.**
  * Make `--label` required.
  * Refuse `--label reference_2026-10-08` unless `--stage0-dir` is the frozen reference's.
  * Refuse to write into an existing `<label>` folder without `--force`.
  * Print "diff skipped: label equals base" when it is skipped.
  * Add a test that a candidate run cannot reuse the base label.

### SHOULD FIX

**S1. The tier-prior evidence quotes the convenient number. The prior over-corrects in 2013–2018 and leaves break points saved over-rated.**
* **Where.** §3.3: "removes most of it (women's holds +0.58 → −0.29 bias) and scores better on 2019–2024"; §3.6 "Survivorship"; answer 6 "Anchor".
* **Observed** (`ios_arm_bias.csv`, asymmetry per 100; positive = lower-based players over-rated against main-tour-based ones at the main tour):

  | Women | The IOS as built | With the tier prior |
  |---|---|---|
  | Holds, 2013–2024 (the dossier's figure) | +0.58 [+0.25, +0.92] | −0.29 [−0.62, +0.04] |
  | Holds, 2013–2018 | +0.51 [−0.03, +1.04] | **−0.87 [−1.38, −0.36]: now under-rated** |
  | Holds, 2019–2024 | +0.63 [+0.22, +1.05] | +0.10 [−0.32, +0.51] |
  | Break points saved, 2013–2024 | +1.02 [+0.75, +1.29] | **+0.70 [+0.43, +0.96]: still over-rated** |
  | Break points saved, 2019–2024 | +1.11 [+0.73, +1.50] | +0.82 [+0.44, +1.20] |
  | Second-serve points, 2019–2024 | +0.58 [+0.34, +0.82] | +0.26 [+0.01, +0.50] |

  * The likelihood still improves in both periods. Women's holds score +0.24 [+0.03, +0.45] milli per unit in 2013–2018 (03 §3.1) and +0.08 in 2019–2024.
* **Inferred: selection runs both ways in the tier means.**
  * They average every player-season of a tier with 5+ typical matches of evidence (`translation.py:656-678`). These survivors make the prior generous to newcomers: the dossier's point.
  * The model forecasts only the members of that tier good enough to reach main draws. For them the tier mean is too low.
  * 2013–2018 shows the second effect can dominate.
  * Under-rating lower-based players is the direction of the market's error (§4), so an over-correcting prior is the same trap §4 describes for translation.
  * Women's WTA 125 tier is empty: 0 player-seasons in `tier_prior_means.csv`. Its members get the pool's zero, the very prior being replaced (`translation.py:660`).
* **Fix.**
  * Replace the §3.3 bullet with: "A prior set by the player's home tier … removes most of the women's bias on 2019–2024 (holds +0.63 → +0.10; second-serve points +0.58 → +0.26) and scores better there (women's holds +0.08 [+0.02, +0.13], break points saved +0.07 [+0.05, +0.09] milli per unit; low-exposure women up to +0.22). But it over-corrects women's holds in 2013–2018 (−0.87 [−1.38, −0.36]: lower-based women then under-rated) and leaves break points saved over-rated (+0.70 [+0.43, +0.96]). Men: only aces and break points saved clear 0 (+0.01, +0.04)."
  * Add to §3.6: "Selection in the tier means runs both ways (survivors against the best of a tier); over-correction pushes toward the market's error."
  * Add to §8.2: "an empty tier falls back to the nearest populated one, not to 0".

**S2. Translating the 18 aggregates adds no information about skill: it re-centres them by the level share. The control does not match that share.**
* **Where.** §7; §9.5; answer 3; the market reasoning of §4.
* **Inferred from the code.** The offset is one constant per statistic, tour and level. Translated:
  * a form becomes today's form minus δ × the player's shrunk lower-level share in its two-week window (step 3, `stageB_adjperf.py:404-409`; the formula is written out at `:422`: Σw·z / (Σw + K));
  * `points_52w` becomes itself minus δ × the shrunk lower-level share of its 364 days.
* So the first candidate gives TabPFN two share variables with loadings fixed by the δs, in place of today's inflation. It is in the family of the event-levels C1 input, which read +0.06 [−0.10, +0.23] (unresolved, P 0.76).
* **The control does not fit.**
  * The pre-registered control uses C1's `low_share_diff`: the 365-day *results* share (event levels, line 279).
  * The variable that drives 17 of the 18 changes is the two-week *box-score* share: bimodal, and for qualifiers mostly the same event's qualifying rounds (01 §1).
  * A gain that survives the C1 control can still be the two-week share in disguise.
* **Fix.** Add to §7, before the result arrives: "What the first candidate can and cannot show. It re-centres 18 inputs by two share variables; it adds no skill information. Expect a small effect, near C1's.
  * A gain that survives the C1 control is confirmed only against the reference plus the same two window shares (two-week box-score, 364-day box-score).
  * Its main value is protection: the layer that keeps P7's ITF box scores from inflating these inputs.
  * By the framework, B·(est − sel) > c with τ = 0.03 and c ≈ 0.01. At s ≈ 0.05–0.15, B ≈ 0.26–0.04, so a gain needs about +0.04 to +0.26 mLL, plus the winner's luck if the primary is chosen among the arms.
  * Or it is suggested on mechanism, as harm prevention ('more of a kind of data already used': not clearly negative, input check clean)."

**S3. New measurement: the one-step opponent norm leaves about two-thirds of the opponent-strength gradient inside the main tour too. The level offset fixes only the level part.**
* **Where.** §1.2's diagnosis (78%); §8.2's parenthesis "(Alternative for the forms: measure each match against the joint solve's prediction …)".
* **Observed** (appendix; main-tour main-draw matches 2013–2024; direct entrants; within player-season):
  * the per-match z of `adjperf_tpw_2w` rises +0.254 (SE 0.005, men) and +0.252 (SE 0.006, women) per unit of the opponent's log ranking;
  * raw total points won rises +2.10 and +2.30 points per unit, about 0.39 z;
  * so the z keeps about 65% of the opponent-strength gradient, the same proportion as the 78% across levels;
  * a qualifier or lucky-loser opponent adds nothing beyond his ranking: men −0.03 [−0.06, +0.00]; women −0.04 [−0.07, −0.01], z lower.
* **Inferred.**
  * The level contamination is one case of a general weakness of the one-step norm (`stageB_adjperf.py:195-207`). A player's form also carries the strength of his recent main-tour opponents: a run of qualifiers and wild cards inflates it; a run of seeds deflates it.
  * A level offset leaves that in place.
  * The parenthesised alternative fixes both: the leak-proof joint solve's prediction, or an iterated norm. It is Stage B's own suggestion: `docs/studies/ufc_ideas/stageB.md:363`, "so that every z sits on one scale".
  * These 17 forms are the owner's per-statistic profile (Stage D's lead against the odds), so a one-scale version matters to the thesis.
* **Fix.** Promote the parenthesis to a named option in §8.2 and §8.6: "The one-scale form: every match, at every level, measured against the leak-proof joint solve's prediction. It changes every form, so it cannot pass the first candidate's invariance gate. It is its own candidate, cross-player, so it needs the clock and `probe.py`." Cite this finding in §1.2.

**S4. §3.2's "exchange rates" come from an estimator that cannot separate translation from other things. One table cell is wrong, and the 0.7 weight for the forms is imported from it.**
* **Where.** §3.2 table and exchange-rate table; answer 3 ("worth about one main-tour match, except a men's Challenger"); §8.2 ("weight men's Challenger matches about 0.7"); §3.2's UFC sentence.
* **Observed** (`credibility_params.csv`, translated-and-weighted arm, 90% player bootstrap of 30 draws):
  * women's tour qualifying weights are *above* 1: total points 1.42 [1.21, 1.70]; serve points 1.16 [1.05, 1.44]; return points 1.40 [1.02, 1.77]; breaks 1.46 [1.03, 2.04];
  * men's tour-qualifying breaks: 0.63 [0.44, 1.07];
  * the cell "Tour qualifying | w ≈ 1 | w ≈ 1" is wrong for women.
* **Inferred.**
  * The estimator (`translation.py:1062-1218`) shrinks everyone toward one prior mean μ, the main-tour average. That is the pool-wide prior §3.3 criticises.
  * It weighs every match of the 365 days equally, with no recency, and has no opponent term.
  * So δ also absorbs the lower-based players' own lower main-tour level, and w absorbs recency: a qualifier's qualifying rounds are her most recent evidence.
  * Symptoms:
    * w above 1;
    * forecasting offsets 1.3–1.8× the same-season gaps for men's Challengers (total points +3.9 against +2.9; holds +6.8 against +3.7);
    * women's WTA 125 offsets smaller than their gaps (holds −0.9 against +4.0).
  * These parameters rank the arms; they are not exchange rates to port into two-week, opponent-adjusted forms.
  * The discount adds at most +0.04 once translated (§3.2). The 0.7 weight is unsupported for the forms; the framework sends unresolved variants to the simplest member.
  * The UFC sentence ("an unknown player starts at the main-tour average") misdescribes the UFC prior. That prior starts a newcomer at a flat newcomer anchor below the UFC average (−0.244 on MESR; 06 §1.2), which is closer to the home-tier prior.
* **Fix.**
  * Correct the cell: "women: w above 1 (total points 1.42 [1.21, 1.70])".
  * Add: "δ and w are fitted in a simple estimator (one main-tour prior mean, no recency, no opponent term). They absorb the group's level, recency and opponent mix, so they rank the arms but are not structural exchange rates; a weight above 1 is a symptom."
  * In §8.2, drop "weight men's Challenger matches about 0.7", or make it a separate pre-registered arm.
  * Fix the UFC sentence.
  * Add to "What it does not show": "The 17 forms are not modelled; the raw-rate estimator is their stand-in (03, 'What it does not show')."

**S5. The dossier contradicts itself on selection and on freezing, and the candidate uses the design §3.6 calls biased.**
* **Where.** §3.6 "Selection … inflates same-season gaps. The conclusions above rest on prior-only designs"; §7 "offsets … estimated on 2010–2018 same-player-season contrasts"; §8.5 "Freeze a discount fitted once on old seasons | Offsets drift".
* **What is wrong.**
  * §3.2's own data show the prior-only forecasting offsets are *larger* than the same-season gaps (S4), not smaller. The net direction of selection is unknown.
  * The first candidate uses the same-season design, frozen on 2010–2018, which §8.5 advises against.
  * Its half-dose arm brackets the dose only from below.
* **Fix.**
  * §3.6: "Selection. Same-season gaps are partly chosen by that season's results, but the net direction is unknown. The forecasting offsets are larger, not smaller, because they also absorb the prior mean, recency and opponents. The first candidate's same-season offsets may under-translate against the forecasting fit."
  * §7: "The offsets are frozen by design (the convention of M4); §8.5's warning is about adopting a frozen offset, not testing one. A follow-up arm at about 1.5× the dose would bracket it from above."
  * §3.6 "Drift": "a 2010–2018 offset is a fair but possibly stale test for 2019–2024 (men's Challenger serve offset −0.2 → −0.6)".

**S6. The summary sets statistic-level gains beside the market's error. The dossier's own reasoning says the remedy may lose at the close. Today's Pinnacle-first decision is missing.**
* **Where.** Answer 4 ("It matters most for exactly the players the market misprices", with "two to five times more for players with under 10 main-tour matches" just above); §4.
* **What is wrong.**
  * **Misleading framing.** A reader takes it as a betting gain. §4's inference predicts the opposite risk, and S2 predicts a small effect.
  * **Pinnacle-first is missing.** Since [9 Oct](../../../decisions/2026-10-09-pinnacle-first-odds-input.md) the decided odds input is "Pinnacle first". Pinnacle's close beats the books' average by 0.67 mLL [0.34, 1.00], 2019–2025.
    * §4 measured the books' average close of the frozen reference (02 §8).
    * Whether Pinnacle under-rates the lower-level-heavy player by +0.18 is unmeasured.
    * The instance exists: `data/studies/current_best_model/pinnacle_first_2026-10-09/` (frame, inputs, fits). `composition.py --model <folder>` can re-run part 5 on it in about 2 minutes.
    * `compare.py` stays the yardstick (the reference keeps the average), so §7 is unaffected.
  * **The edge is in-sample.** The 2020–2024 edge lies in the seasons that chose the inputs: +0.18 [−0.28, +0.64] in 2015–19 against +1.46 [+0.84, +2.08] in 2020–24 (framework §6).
* **Fix.**
  * Answer 4 ends: "… and it is also why the remedy could lose at the close. Today's inflated forms lean the model toward these under-rated players (§4). Expect a small effect (S2 of 07)."
  * §4 gains a line: "Measured against the books' average close (the frozen reference's input). The decided input is Pinnacle first since 9 Oct; re-run part 5 on its instance before relying on the +0.18. The 2020–2024 edge is in the seasons that chose the inputs."

**S7. ITF data through the layer will still step the evidence volume, and the first candidate may itself be flagged "uneven".**
* **Where.** Answer 5; §5 "P7 builds in a step"; §8.3.1, .3, .4; §9.3.
* **Inferred.**
  * **Volume, not just level.** Translation fixes the level of ITF evidence, not its volume.
    * A woman ranked 201+ has about 10 box scores in her 365 days today, and P7 adds about 22 (02 §2, §6).
    * Her `points_52w` and forms become much less shrunk from 2018 on, so the spread of the A − B inputs grows in 2018–2024 only.
    * `compare.py` flags a tour-season whose scale ratio moves by more than 10% (`compare.py:18, 74`), so a perfect translation can still be called "uneven".
  * **The candidate's own dose varies by season.** It moves each input in proportion to the season's lower-level box-score coverage: women's two-week form is 0.1% lower-level in 2015 against about 20% elsewhere (02 §4); men's Challenger qualifying has none in 2010–2015.
  * **The control needs both arms on one window.** §8.3.4's "run the comparison once with the training window starting in 2019" must train both arms from 2019. A candidate from 2019 against the reference from 2013 measures the window, not the step.
* **Fix.**
  * §8.3: "The layer removes the level inflation, not the volume step (less shrinkage from 2018), so the input check may still flag the inputs. Then: P7 back to 2014 (SofaScore holds women's ITF from 2014 per the match-clock decision's open points; its box scores are unmeasured), or both arms trained from 2019, or a cap on ITF evidence's effective count."
  * §7: "The candidate's dose follows each season's coverage (women's 2015, men's Challenger qualifying 2010–2015), so the input check may flag it 'uneven' by construction. Read a flag against `inputs_dose.csv` before treating it as harm."

**S8. The live guardrails: wrong wording for the speed guard, no score can judge the speed guard or the feed restoration, and the tier prior depends on the restored feeds.**
* **Where.** §1.4.1, §8.2 (stage 2 row), §8.4.1, §8.4.3, Decisions 3 and 4.
* **Observed** (`speed_panel_frozen_corrected.parquet`, usable rows): Challenger main draw plus qualifying is 167 (2022), 93, 96, 93 (2025), then 945 (2026). That is about 1.5% of the panel before 2026 and about 13% in 2026.
  * The 2026 coefficient was fitted on 2019–2025 histories that included Challenger speeds.
  * "Filter `spd_L` to the levels its coefficients were fitted on" would remove a level that was in the fit. What changed is the dose.
  * The 945 rows are already in the frozen reference.
* **Inferred.**
  * **No score can judge them.** The guard changes only 2026 rows (and the 2027 fit). The feed restoration and the 1,943 WTA API box scores change only 2025–2026 rows. `compare.py`'s 2020–2024 scores therefore cannot judge either without spending the holdout. They are the framework's data-fix lane, or the owner's call.
  * **Stage 2 already leans worse.** The framework's ledger flags stage 2 as leaning worse at its own target: men 2020–24, −0.26 [−0.60, +0.07] (+ = the adjustment helps; P(better) 0.06).
  * **The tier prior reads the broken feeds.** Candidate 2's home tier comes from Stage 0. With the lower tiers missing since June 2026, ITF-based women drift to a main-tour home tier and get the main-tour mean as their prior: the very bias it removes. The feed restoration is a prerequisite for candidate 2's live use.
* **Fix.**
  * §8.4.1: "cap or remove the Challenger dose to match the fitting seasons (about 90 rows a season), or put the speed panel behind the history check".
  * §8.4.3 and Decision 4: "These change only 2025–2026 rows, so a 2020–2024 comparison cannot judge them. Judge them on data evidence (the framework's data-fix lane) with the replay as proof, or by the owner's call."
  * §8.6: "Restore the feeds before candidate 2 is used live."

**S9. The evidence for "the joint solves wash out the level" is weak, and the sharper evidence is half-cited.**
* **Where.** Answer 2 ("most of the level gap washes out"); §1.2 ("within ±0.3 points … and ±0.08 SD … at Challenger and qualifying level").
* **What is wrong.**
  * **Weak test.** 01's level-average residuals are near zero almost by construction. Least squares makes each player's residuals average to about 0, and most players play mostly one level. They cannot show a level effect for the players who cross levels.
  * **Numbers.** Men's Challenger qualifying is +0.32, outside "±0.3" (`stage3_residuals.csv`). IOS break points saved sit at −0.10 to −0.14 SD at every level (01 §3), outside "±0.08".
  * **The sharper test is 03's.**
    * Same players, same season: the solve leaves 13–36% of the total-points gap. Men's Challengers +0.37 [+0.24, +0.50], Slam qualifying +1.19 [+0.91, +1.47] points per 100 (`residual_gaps.csv`).
    * 03 §2.4, omitted from the dossier: when lower-based and main-tour-based players meet, "the two groups' ratings are not on one scale". At the lower level, in-sample, women's tour-qualifying holds are +4.11 / −4.68 per 100.
  * The dossier's conclusion (informative, with a prior-driven leak) follows 03's mechanism tests and stands. The confidence is overstated.
* **Fix.**
  * §1.2: "The joint solves remove most of the same players' gap (64–87% of total points won, 03 §2.2) but not all, and their two groups of players are not on one scale when they meet (03 §2.4). Level-average residuals are small (within ±0.32 points; ±0.08 SD apart from break points saved) but near zero almost by construction."
  * Answer 2's table: "most of the level gap washes out" → "most, not all".

**S10. "Everything ran on the frozen reference" is not true of role 01's three measurements.**
* **Where.** Opening paragraph.
* **What is wrong.** 01's form-shift, Stage 3 and IOS residual checks read `stageB_adj.parquet` (2 Oct), `stage3_ratings.parquet` (1 Oct) and `surface_features.parquet` (6 Oct): the same code on the tables before the 8 Oct corrections (01, "Inputs read"). The 78% comes from there.
* **Fix.** "… except role 01's three code-level measurements, which read the builds of 1–6 Oct (the same code, on the tables before the corrections of 8 Oct)."

**S11. Labels and authority: study findings presented as settled, and owner decisions asked for things already decided.**
* **Where and what.**
  * **Answer 1.** "(Observed; settled on 8 Oct by the event-levels study)". A study does not settle anything, and "should keep doing so" is a suggestion. Fix: "**The model trains on main-tour matches only** (Observed: the decided configuration, [current-best-model decision](../../decisions/2026-10-08-current-best-model.md)). *Suggestion:* keep it. Added as rows, Challenger matches leaned harmful (event levels)."
  * **Decision 2's second sentence.** "whether to extend P7 back to women's ITF of 2014–2017" is a collection question. Collection is approved "without stopping to ask" (CLAUDE.md; [decision of 8 Oct](../../../decisions/2026-10-08-scraping-approved.md)). Fix: "P7 is extended back to 2014 if SofaScore serves it (collection is approved); the owner's decision is only how it enters the model."
  * **Decision 6.** It asks approval to *build* candidate 2. The owner's standing preference is that feature ideas are built and scored in-session, with approval gates only where he asks. Fix: "Candidate 2 will be built and scored before P7 is wired; adopting it is the owner's call."
  * **§8.2 "Qualifiers: Covered by the translation".** This is unsupported. A qualifier's same-event qualifying rounds are all wins (lucky losers aside). They sit in his two-week form (01 §1), selected on outcome, beyond the average qualifying offset. Fix: "partly; their same-event qualifying matches are selected on winning, so read the declared qualifier stratum (§9.6) before deciding."

**S12. Two summary statements overstate or blur direction.**
* **Answer 5, "it would contaminate 41 inputs".** The 14 IOS ratings are shift-invariant in A − B, and the dossier itself calls the joint solves informative. Fix: "it would inflate the 18 aggregates for ITF-active players, move the products' zero point (7), and change the IOS ratings' evidence and prior (15, untested at ITF level), in 2018–2024 only."
* **§4, "Today's inflated forms push the model toward these under-rated players, which is the market's error's direction."** It can be read as "the same direction as the market's error". Fix: "… toward these under-rated players, which corrects part of the market's error."

**S13. The Elo results in the summary need their qualifier and the full picture.**
* **Where.** Answer 2's "Results" row ("dropping them costs 6–7 mLL; a discount ties"); §3.4.
* **Observed** (`elo_k.csv`, 2013–2024; + = better than full weight; a plain Elo's own log loss, not the model's):
  * at ×0.75, every reading is unresolved: men's Challengers +0.01 (P 0.54); women's Challengers +0.03 (P 0.65); men's ITF +0.13 [−0.01, +0.28] (P 0.96, a lean toward discounting); women's ITF +0.06 (P 0.68);
  * ×0.5 is worse for men's Challengers: −0.58 [−1.10, −0.06];
  * ×1.25 is worse except women's Challengers: −0.12 [−0.26, +0.02], unresolved, P 0.04.
* **Fix.**
  * Table: "Lower-level results are needed (dropping them makes a plain Elo's forecasts 6–7 mLL worse); a ×0.75 discount is unresolved; Elo is a priced-in control, so it is not pursued."
  * §3.4 gets the bullets above.

**S14. `refresh.py`: the other bugs, beside M5.**
* **Missing outputs read as "No flag".** Observed in-process: `R.diff(base, {composition: {}, translation: {}, incoming: {}})` returns `[]`, and the markdown says "No flag. Nothing moved past the thresholds". Running `--steps snapshot,diff` on a label whose outputs do not exist, or are in another folder, gives a false all-clear. Fix: flag sections present in the base and absent in the candidate.
* **DRIFT fires on a window move.** The run §10.2 recommends after P7 refits on 2018–2021 instead of 2010–2018. Most offsets and weights will then leave the base's bootstrap range because the window moved. The snapshot stores the windows (`:170`) but `diff()` ignores them. Fix: if the windows differ, report "windows changed" and do not read DRIFT.
* **NEW LEVEL's definition.** It is documented as "gains box scores in the fitting seasons". `translation.py` sets `levels_with_box_scores` by `present_levels` over every season up to 2024 (`:1403-1404`; 200+ rows). Run with the default windows after P7, ITF is "present" while its fit window holds only 2018. Fix the doc or the logic.
* **The clock reads the reference.** `incoming.py:441` reads the reference's timeline whatever Stage 0 it is given, so trigger T3's clock check cannot see a refreshed timeline. `refresh.py`'s `--timing` also defaults to the reference's timeline with a candidate Stage 0. Fix: give `incoming.py` a `--timing`; require `--timing` when `--stage0-dir` is not the reference.

**S15. The ITF placeholder in the first candidate is never scored, but it would reach live inputs.**
* **Where.** §7, "ITF uses the Challenger offsets as a placeholder".
* **Inferred.**
  * No ITF box score exists in 2013–2024 windows, apart from 31 women's matches in 2022. So the placeholder affects only the 2025–2026 rows: holdout and live.
  * §7 cannot test it. 01 infers the ITF field effect is larger than the Challenger one.
* **Fix.** Add: "The placeholder changes only 2025–2026 inputs; the test does not score it. If the candidate is adopted before P7's own ITF offsets exist, women's live ITF evidence is translated by an untested offset."

### NOTES

| # | Where | What | Fix |
|---|---|---|---|
| N1 | §3.2 table, "Translated vs …" rows | Every number is the translated-and-weighted arm; translated alone is nearly equal (breaks +1.97 [+1.48, +2.47]) | Rename "Translated and weighted vs …" |
| N2 | §3.3 "A 2× discount helps only men's holds … and break points saved" | Also clear of 0 for men: second-serve points +0.03 [+0.02, +0.05], serve points +0.02 [+0.01, +0.03], first-serve points +0.02 [+0.01, +0.04] (`ios_arms.csv`) | "helps men's holds (+0.20) and break points saved (+0.08), and the points statistics a little (+0.02 to +0.03)" |
| N3 | §3.3 "(−2.99 ± 1.25 residual)"; §4 table "(0.03)" | The ± is a 95% half-width (SE 0.64); the sign convention is not stated; the parentheses in §4 are SEs | "their break points saved fall 2.99 per 100 short of the prediction (95% half-width 1.25; negative = over-rated)"; header "(SE)" |
| N4 | §3.4 "cost −6.8 [−8.4, −5.2] mLL" | Double negative | "are worse by 6.8 [5.2, 8.4] mLL" |
| N5 | Throughout | "IOS" never expanded; "finding #6" and "#7" not defined at first use; §8.4.2's "`refresh.py --sources sofascore`" collides with the study's own `refresh.py` | Define IOS once; one-line glosses of #6 and #7; write `match_timing/refresh.py` |
| N6 | §5 | `stage0_build.py:91-103`: the source list is at `:93-106` (the claim is right) | Fix the lines |
| N7 | §10.2 and answer 8, the dry run | Not made by `refresh.py`: no snapshot or flags JSON, no code path. It is 02's P7 scenario column fed in as a pseudo-candidate, so it only shows that the flag reads what the scenario built. It reproduces (13.7 / 12.1 / 6.2 / 15.5 from `itf_p7_scenario.csv`). "2018–2025 moved" is exact for 365 days and 13 weeks only: the two-week form moved 2018–2024, the 52-week 2018–2026 | Call it a construction; add it as a test or a `--scenario` option; state the per-memory seasons |
| N8 | Small facts | §3.5 "go from 0 to … 851": women's today is 6. Answer 5 and §5 "in 2019–2024 only": also +6 in 2018 and 2025. Answer 4 "58–87% of a player ranked 101 or worse": that is the two-week form and `points_52w` together (form alone 60–76%). §2 "Half of all model matches (50%)": results channel (box-score channel: women 39%, 250s 60%). §1.2 "qualifying 79–83%": 77–83% (Challenger qualifying 77%). §3.2 "as large as or larger than the same-season gaps": not for women's WTA 125 | Correct as stated |
| N9 | §5, TennisLive bullet | Point logs (missing the set-closing game) and the match-total box score (151 of 151 equal) are run together and read as a contradiction | "Its point logs drop …; its match-total box scores matched the official ones in all 151 trial matches" |
| N10 | `refresh.py`, minor | DRIFT covers 8 of 12 statistics: no bootstrap for double faults, first serves in, break points saved and converted (`credibility_params.csv`). UNEVEN DOSE fires with no unmoved season when every season moves unequally (in-process: +4 everywhere, +8 in 2018–2024 → flagged, `unmoved_seasons: []`), against its docstring. The snapshot stores incoming numbers, level effects and IOS arms that `diff()` never reads. Timestamps are local time without a zone | Document, or use them |
| N11 | `lineage_checks.py:357` | Loads every player row's box-score columns, 2025–26 included, before filtering; nothing is computed from them | Filtered read, as `translation.py:208-209`, so "no outcome read" is literally true |
| N12 | Files table | `translate_hooks.py` is not in the repository at review time; 07 and 08 links pending | Check before release |
| N13 | 02 §8c | "The model takes up about half of it, as it did there": the event-levels study says "about a third" (+0.12 of +0.18, line 291). The dossier's "a third to a half" is fine | Fix 02 |
| N14 | Answer 2; §1.2; §8.6.5 | The owner's thesis. The 17 forms *are* his per-statistic profile (Stage D's lead against the odds), so the contamination sits in the thesis's own features: say so. The headline 78% is on total points won, a points-won aggregate; lead with per-statistic shifts (men's Challengers: holds +0.42 z, breaks +0.41). P5/P6 point data (28,785 Challenger matches, 75% relevant, landing 10–13 Oct) are the thesis's raw material; "Later" may undersell them | Reword |
| N15 | Decision 5 | The 5 Oct match-clock decision makes `match_timing/refresh.py` the routine after new dates. The 8 Oct history gate does not see the timeline. The two decisions meet here | Say so in Decision 5 |
| N16 | Answer 4 | "+1.37 … not detectably weaker there" puts the overall edge where the stratum's belongs | "in the quarter where the shares differ most: +1.46 [+0.20, +2.73]; no family of strata differs (p 0.12–0.92)" |
| N17 | §9 | Missing two UFC/framework rules: read touched against untouched rows (06, training-context spillover); state the search (§3.3's remedies were picked from 10 arms × 26 statistic-tour cells; §8.2's per-statistic λ and aces offset are best-of-arms picks) | Add both; pre-register one recipe for candidate 2 |
| N18 | §1.2 | "26 are opponent-adjusted in a joint solve": Elo is an online rating, not a joint solve | "26 opponent-adjusted (online ratings or joint solves)" |
| N19 | §9.3 and the holdout line | `compare.py`'s input check reads every season's input distribution, 2025–26 included. Those are built from 2025–26 box scores: no result, but a look at holdout performance | Log it as a look (framework §9), or say why it is not one |

## What I verified and found correct

**Re-derived from the evidence files** (each matches the dossier to its rounding unless noted above):
* **The 78%:** `adj_level_shift.csv`: men's Challenger z +0.51478 against raw +0.661178 (0.779); women 0.406 / 0.526 (0.773); qualifying 77–83%. 13 of 17 forms shift clearly; the four style forms do not. The code (`stageB_adjperf.py:144-145, 195-207`) builds z against the opponent's own-opponents norm, as described.
* **§3.2** (`credibility_scores.csv`, validation 2019–2024):
  * pooled against main-only, breaks: −1.431 [−1.862, −1.000] (men), −0.576 (women);
  * translated and weighted against pooled: +1.980 [+1.471, +2.488], +1.169 [+0.892, +1.445]; holds +0.446 / +0.680; total points +0.224 / +0.194;
  * against main-only, breaks: +0.549 / +0.593; low exposure +5.223 / +3.604;
  * the discount adds at most +0.04; untranslated return-statistic weights go to 0.
* **Exchange rates** (`credibility_params.csv`): men's Challenger total points w 0.727 (5–95%: 0.58–0.93), δ +3.9 points, 0.64 main-tour matches per match.
* **§3.3:**
  * removes 87% (men's Challengers) to 64% (Slam qualifying) of the total-points gap (`residual_gaps.csv`);
  * condition offsets −0.2 / −0.6 (`level_effects.csv`);
  * the arm gains (`ios_arms.csv`): tier prior women's holds +0.078 [+0.025, +0.132], break points saved +0.071, low-exposure holds +0.221; λ = 2 men's holds +0.197 [+0.148, +0.246]; dropping lower levels −0.20 to −1.27, low exposure to −4.88;
  * tier means +0.384 / +0.203 / +0.085 (`tier_prior_means.csv`);
  * bias +1.02 [+0.75, +1.29], +1.16 without lower rows (`ios_arm_bias.csv`); −2.99 (SE 0.64) on thin evidence (`residual_by_evidence.csv`).
* **§3.4** (`elo_k.csv`): −6.771 [−8.376, −5.167] men's Challengers at ×0; −6.391 [−8.126, −4.655] women's ITF at ×0.
* **§2** (`inputs_dose.csv`, `summary.json`): every cell of the dose table, the rank bands, 24% low exposure, 84–88%, 4 against 43 (men), 4 against 12 plus 26 (women), 42% / 7% ITF reach.
* **§4** (`scores.csv`): +1.374 [+0.668, +2.081] reproduced; intercepts −0.010, +0.094, +0.091, +0.178 (SE 0.043) close against +0.093 (SE 0.042) model; slopes 1.148, 1.331, 0.900; heterogeneity p 0.12–0.92.
* **§5** (`incoming/dose.csv`): 8,977 of 13,061 women's model matches (68.7%) and 1,266 of 14,270 men's (8.9%) reach P7 targets; pre-2018 step 72% / 14%. The P7 scenario's +11 to +14 points (`itf_p7_scenario.csv`).
* **§1.4.1:** Challenger speed rows (my recount: 93, 96, 93 a season, then 945 in 2026; 01 says 92, 94, 89, 940 on its "usable" filter).

**Code citations opened** (12):
* exact: `stage4_features.py:574, 959-962`; `stageB_adjperf.py:144-145, 195-207`; `history.py:58`; `stage1_baselines.py:169-170` (one K); `run_chain.py:35-37` (lane 0 never run); `atp_daily.py:132-145` (plans everything but Slams and team events); `adaptive/columns.py:135` (women's `spd_L` 0); `translation.py:578-580` with `:260-263` and `:449`; `composition.py:817`; `translation.py:203-212`; TabPFN `classifier.py:949` in `tennis-tabpfn-local` (`fit(self, X, y)`, no sample weights);
* slightly off: `stage0_build.py:91-103` (N6).

**Also checked.**
* **The code's verdicts hold:** the counting identity 9 + 23 + 26 = 58; the 49 history inputs; `compare.py`'s per-tour-season check (10% in scale, 0.10 SD in level: the dossier's "10%" applies to the scale only).
* **The proposal's routes comply with the frozen-reference rule** (candidates, `compare.py`, the owner decides), apart from M3 and S8.
* **The holdout.** Every outcome read I traced stops at 2024 with the study's guard. N11 is the one hygiene gap. The candidate design scores no 2025–26 outcome.
* **Tests and runs.**
  * `./python.sh -m pytest test/lower_level_evidence -q`: **46 passed** (6.2 s).
  * `refresh.py --steps snapshot,diff --label reference_2026-10-08`: exit 0, snapshot rewritten unchanged apart from its time, no diff run (M5).
  * Every snapshot reader finds its file and columns: 42 family doses, 112 season shares, 7 exposure cells, 120 credibility keys, 489 level effects, 176 IOS arms, 28 P7 shares, 97 coverage cells.
  * The step commands match each script's real CLI.
* **The UFC section** matches 06, and 06 matches its sources as cited.

## Open risks the dossier should state

1. **The first test will probably be small.** It is a re-centring by the level share (S2), near C1's +0.06. A null or a lean worse at the close is the predicted outcome, not a refutation of the layer. Its case is protection against P7.
2. **Over-correction pushes toward the market's error.** Too large an offset, or a too-harsh tier mean (S1, S5), under-rates lower-level players, the direction the close already errs in.
3. **The forms keep their schedule bias inside the main tour** after any level fix (S3).
4. **P7 will likely trip the input check even through the layer** (S7, evidence volume). The cures are coverage back to 2014, a 2019 window for both arms, or capped evidence.
5. **ITF is unknown territory until P7:** its field effect, the additive rating model at that level, and SofaScore's 2018 yield (Hungary F1 2018: 23 of 31). Every ITF number in the proposal is a placeholder.
6. **The market readings are on the books' average close, in 2020–2024**, the seasons that chose the inputs. At Pinnacle (the decided input since 9 Oct) the +0.18 may be smaller (S6).
7. **Live women's histories have no lower levels since June 2026.** Any level-aware remedy does nothing for them, and the tier prior misfires, until the feeds are restored (S8).
8. **Coverage gaps make every level-aware change uneven by construction:** women's 2015, men's Challenger qualifying 2010–2015, women's WTA 125 in 2013 and 2015 (S7).
9. **Frozen offsets go stale.** The men's Challenger serve offset moved −0.2 → −0.6 between eras.
10. **The timeline refresh after P6/P7 is an inferred risk, unmeasured** (§1.4.2). It is cheap to measure with the reference's own inputs before the refresh runs.
11. **Future point-level profiles inherit the data's biases:** TennisLive's missing set-closing games, ITF qualifying statistics mostly from final rounds, and integrity-alert events.
12. **Stage 2 is itself under review** (the ledger's −0.26 lean). Changes to its speed history are judged on data evidence only (S8).

## Appendix: the opponent-strength check behind S3

* **Data.**
  * `data/studies/ufc_ideas/stageB_adj.parquet` (the 2 Oct build role 01 used), read with `year <= 2024`;
  * the frozen Stage 0's `map_level` and `tournament_date`, with rows of events from 30 Dec 2024 dropped and `common.assert_no_holdout_outcomes` called before any z is used;
  * Stage 0's player rows for `entry`, `rank` and `tpw_n` / `tpw_d`.
* **Sample.** Main-tour main-draw matches of 2013–2024. The focal player is not a qualifier or lucky loser (`entry` not in Q, LL).
* **Paired contrast.** Focal player-seasons with 2+ matches against each kind of opponent, mean against qualifiers minus mean against direct entrants:
  * men (1,221 player-seasons): raw total points won +2.13 [+1.94, +2.32] per 100, z +0.299 [+0.265, +0.333];
  * women (1,194): +2.33 [+2.10, +2.56] and +0.262 [+0.224, +0.299].
* **Regression.** Within player-season (demeaned), the target on log(opponent's rank) and a qualifier-opponent dummy; SEs clustered by player-season.
  * Men (50,674 rows): z slope +0.254 (0.005), dummy −0.027 [−0.058, +0.004]; raw slope +2.103 (0.026) points, dummy −0.51 [−0.67, −0.35].
  * Women (45,237 rows): z +0.252 (0.006), dummy −0.038 [−0.070, −0.007]; raw +2.297 (0.033), dummy −0.36 [−0.55, −0.17].
* **In z units.** The raw slope is about 0.39 z (01's conversion, 0.185 z per point for men, 0.171 for women), so the z keeps about 65% of the gradient.
* **Caveats.** Ranking is a noisy strength index (both slopes attenuate alike). Round and stage are not separated.
* **Reproducing it.** The script was in the session scratchpad (`opp_norm_check.py`), which is temporary. It is about 60 lines of pandas and numpy over the files above and runs in under a minute.
