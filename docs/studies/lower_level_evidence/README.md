# Lower-level evidence: informing the main-tour model without treating Challenger and ITF matches as equivalent

9 October 2026 · Written for the owner · A research dossier and a proposal, not a decision · Built to be re-run when new data lands (§10)

> **Start with the system instead.** On 10 Oct 2026 this exploration was followed by [the level-evidence system](system/README.md):
> * the relationship, built and verified;
> * the proposal for the men's model;
> * the test of the rule of 8 October;
> * the P7 plan.
>
> This dossier stays as the first run's record.

**The owner's question** (9 Oct 2026):

> "We are about to get a TON of new data from lower levels <250, I dont want it contanimating the model unecessarily (it currently does in a couple stats I believe?). Explore how much it makes sense to seperate these two sets of data. Not necessarily never using challenger information in the 250+ model, but very likely don't treat it as equivalent information. […] having strategies to use this data as INFORMATIVE (not replacing) for the 250+ model, and not treat it as EQUIVALENT. Diagnose how its currently used and then propose a solution for how it can be used to INFORM our model without directly being used as EQUIVALENT data."

**How it was done.** An eight-role team (§11; the briefs, for re-running it, are in [team/briefs.md](team/briefs.md)):
* six specialists worked in parallel: the code, the data's composition, the statistics of translation, the incoming data, outside practice, and the owner's UFC precedent;
* the lead merged their reports into this dossier;
* a red team re-derived its numbers and attacked its logic ([07](team/07_red_team.md)); its corrections are applied here;
* a candidate builder tested the main remedy on the model itself ([08](team/08_candidate.md)).

**What it ran on.** Everything ran on the [frozen reference](../../../data/studies/current_best_model/reference_2026-10-08/README.md) of 8 Oct 2026, with one exception. Role 01's three code-level measurements read the builds of 1–6 Oct: the same code, on the tables before the corrections of 8 Oct.

**No outcome of a 2025–2026 match was read** (the [proposed holdout](../clean_holdout_rebuild/README.md)); those seasons were only counted. One caveat (§9, point 10): `compare.py`'s input check reads 2025–26 input distributions.

**Keys.**
* *Observed* = computed here or read in a file (cited); *Inferred* = reasoning; *Suggestion* = a proposal for the owner.
* **Scores.**
  * mLL = milli-log-loss per match; **+ = the named version is better** (lower log loss).
  * A reading is "better" or "worse" when its 95% interval clears 0. Otherwise it is "unresolved", with P(better) = Φ(estimate / SE) (the owner's [decision of 9 Oct 2026](../../decisions/2026-10-09-adoption-framework.md)).
  * Verdicts are given on declared primaries only; other readings are descriptive.
  * "Milli per unit" = thousandths of one statistic's own log loss per point or game: a statistic-level score, not a match-level one.
* **Levels.**
  * **MAIN** = main draws of the Slams, Finals, 1000s, 500s and 250s: the model's training rows.
  * **TQ / GSQ** = tour / Slam qualifying. **CH** = Challenger and WTA 125 main draws; **CHQ** = their qualifying. **ITF**, **ITFQ**.
  * "Lower" = everything below MAIN except team events.
* **Terms.**
  * **IOS** = the project's opponent-adjusted offence and defence ratings per statistic, solved jointly over all players.
  * **Finding #6** = the input-data audit's discovery that ITF box scores (present only January 2025 – May 2026) shifted the IOS pool's level and widened the 7 matchup products by 25–56%.
  * **Finding #7** = women's workload reading "rested" after the June 2026 feed change.

## The answer in short

**1. The model trains on main-tour matches only** (Observed: the decided configuration, [current-best-model decision](../../decisions/2026-10-08-current-best-model.md)). *Suggestion:* keep it. Added as training rows, Challenger matches leaned harmful in the [event-levels study](../event_levels/README.md). Lower-level matches reach the model through the players' histories behind 49 of its 58 inputs.

**2. All 49 of those inputs read every level, and none weighs or translates by level** (Observed, [01 lineage](team/01_lineage.md)). Whether that contaminates depends on how each input uses a match:

| Channel | Inputs | How a lower-level match counts today | Verdict |
|---|---|---|---|
| Raw and one-step aggregates | the 17 two-week forms (`form_*`, `formdef_*`, `adjperf_tpw_2w`) and `points_52w` | **As equivalent.** The "opponent-adjusted" forms keep about 78% of the raw level boost per match (men's Challengers: holds +0.42 z, breaks +0.41 z); `points_52w` keeps all of it | **Contaminated at the input level.** The owner's "couple of stats" is 18 inputs, and the 17 forms are his own per-statistic profile (the ufc_ideas Stage D lead against the odds). At the close, the first test found no measurable cost (point 7) |
| Joint solves | IOS profile (14 ratings, 7 products), `ios_points_short`, `ratings_iid` | Opponent-adjusted together with every player: most, not all, of the level gap washes out | **Informative, with two leaks:** a pool-wide prior that over-rates thin-evidence lower-level women, and products whose zero point moves with the pool (finding #6) |
| Results | offset Elo (2), `elo_games` | One K for every level | **Leave as is.** Lower-level results are needed (dropping them makes a plain Elo 6–7 mLL worse); a ×0.75 discount is unresolved; Elo is a priced-in control, so it is not pursued |
| Counts | `sets_14d`, 4 surface counts | Every match played | **Right to count every level**, but stale live since the June 2026 feed change |
| Stage 2 speed | `spd_L` | Each venue's radar centred on its own offset | **Level-aware**, but Challenger speeds grew from about 1.5% of the panel to 13% in 2026, with no guard |

**3. Separating the data completely throws information away; pooling it as equivalent misleads; translating it beats both** (Observed, [03 translation](team/03_translation.md)). Predicting a player's later main-tour statistics, fitted 2013–2018 and scored 2019–2024 (milli per unit, + = better):
* **Pooling misleads.** Raw lower-level return statistics pooled as equivalent predict **worse than ignoring them**: men's breaks −1.43 [−1.86, −1.00] against main-tour-only.
* **Translating beats both.** With a per-level offset (and a fitted weight), they beat pooling (breaks +1.98 men / +1.17 women) and ignoring (+0.55 / +0.59), and by two to five times more for players with under 10 main-tour matches in the year.
* **The offset carries the gain;** the weight adds at most +0.04.

This is the owner's UFC idea in statistical form: lower-level evidence as a translated prior that the player's own main-tour evidence overrides as it accumulates. Those are statistic-level gains, though. On the model itself, the first test found no gain at the close beyond what the players' lower-level shares already carry (point 7).

**4. The players it matters for are the ones the market misprices, and that cuts both ways** (Observed, [02 composition](team/02_composition.md)).
* **Who carries it.** Lower-level evidence is under 1% of a top-20 player's two-week form, and 60–76% of the form of a player ranked 101 or worse.
* **Low exposure is common.** In a quarter of model matches the less-exposed player has fewer than 10 main-tour results in the year, against about ten times as many lower-level box scores (men).
* **The market's error.** Where the two players' lower-level shares differ by half or more (a quarter of matches), the books' average close under-rates the more lower-level player by +0.18 log-odds, about 4.5 points of win probability in an even match. The model recovers a third to a half of that.
* **The model's edge.** There it is +1.46 [+0.20, +2.73] mLL over the recalibrated close (better). Overall it is +1.37 [+0.67, +2.08], and no family of strata differs (2020–2024, the seasons that also chose the inputs).
* **The catch** (*inferred* before the test). Today's inflated forms lean the model toward these under-rated players, which corrects part of the market's error. So removing the inflation could lose at the close unless the model gets that information another way (§4). In the test it neither lost nor won overall, and a plain share control matched it (point 7).

**5. The flood is mostly ITF box scores for women** (Observed, [04 incoming](team/04_incoming.md), [02](team/02_composition.md) §6).
* **What and when:** about 197,000 ITF box scores of 2018–2024 (collection plan P7), landing about 31 Oct – 2 Nov.
* **Reach:** the previous year of 69% of women's model matches (men 9%).
* **Wired in as it stands, it would:**
  * inflate the 18 aggregates for ITF-active players;
  * move the products' zero point (7 inputs);
  * change the IOS ratings' evidence and prior (15, untested at ITF level).
* **Unevenly:** women's lower-level share of box-score evidence rises by 11–14 points in 2019–2024, 6 in 2018 and 2025, and not at all in 2013–2017. That is the "uneven" shape of finding #6, moved back to 2018.
* **Point data:** Challenger point-by-point data (P5, P6, landing 10–13 Oct) reach no current input. They are raw material for the owner's point-level profiles.

**6. The proposal: a level-aware evidence layer, built in place, channel by channel, switched on where it pays** (Suggestion, §8).
* **Translate:** lower-level matches enter the 18 aggregates shifted by a per-statistic, per-level offset, refitted each season on the match clock. Built and tested (point 7): not worth adopting on today's data. It stays ready as the gate for the ITF box scores.
* **The share signal:** the market under-rates players whose evidence is mostly lower-level. That is what the translation's men's gain turned out to be. Test it directly (two share inputs, or a shrunk stage-2 term), pre-registered, on seasons no choice has read.
* **One scale for the forms** (a candidate of its own). The one-step forms under-adjust for opponent strength in general, not only across levels: inside the main tour they keep about 65% of the opponent-ranking gradient ([07](team/07_red_team.md) S3). Measuring every match against the leak-proof joint solve's prediction fixes both.
* **Anchor:** the joint solves shrink a thin-evidence player toward the average of his own tier (his "home tier"), not the whole pool. It needs care: it over-corrected women's holds in 2013–2018.
* **Keep:** Elo, the workload counts and the main-tour-only training rows.
* **Guard:**
  * ITF box scores enter only through the layer, with offsets fitted walk-forward;
  * the Challenger speed dose is capped;
  * the timeline refresh is checked;
  * the feeds lost in June are restored.
* **Don't:** add exposure columns as the fix, lower-level training rows, or a discount frozen on old seasons.

**7. The first test on the model found no gain beyond the share signal** (Observed, [08 candidate](team/08_candidate.md); §7).
* **What was tested.** The 18 aggregates translated, built through the whole decided chain in a sandbox, with every gate passed: the other 40 inputs identical; untouched players unmoved.
* **The primary:** +0.024 [−0.047, +0.096] mLL against the reference (2020–2024, both stages; unresolved, P(better) 0.75).
  * Men +0.083 [+0.002, +0.164] (better).
  * Women −0.040 (unresolved, P 0.24).
* **Where it comes from.** The two-week forms barely moved: their heavy shrinkage dilutes the offsets. The gain is `points_52w`'s, and it sits where the two players' shares differ most.
* **The control.** A model simply given the two share differences does as well: the translated model against it reads −0.003 [−0.165, +0.160], unresolved.
* **The pre-registered verdict:** unresolved, and not suggested for adoption on mechanism.
* *Suggestion:* don't adopt it now. Keep its machinery for the ITF box scores, where the dose is several times larger.

**8. It is renewable.** `refresh.py` re-runs the review on any Stage 0 and flags what moved (§10). Fed the base run's own preview of the ITF box scores (`--scenario p7`), it flags women's uneven dose in all four memories.

## 1. How lower-level data reaches the model today

### 1.1 Training rows: main tour only

*Observed* ([event levels](../event_levels/README.md) §1, §6). Every training row is a main-tour match with a closing price.
* **Challenger matches as rows.** Added as rows (price missing), they read −0.48 [−1.09, +0.14] mLL (+ = the version with Challenger rows better; unresolved, P(better) 0.06: it leans worse; 2022–2024).
* **They cut the edge over the close** from +0.93 [+0.09, +1.76] to +0.45 [−0.65, +1.55] (unresolved, P 0.79), and the model's realisation from 0.91 to 0.63.
* **One level only.** Training each level only on itself was worse at the 250s.

*Suggestion:* keep it. The separation question is about the inputs, not the rows.

### 1.2 The inputs, channel by channel

*Observed* ([01](team/01_lineage.md), master table, with the code lines). 58 inputs:
* **9 read no history:** the closing odds, the 6 match-context inputs, age and age².
* **23 treat a lower-level match as equivalent:**
  * **`points_52w`**: raw 52-week serve and return points, with no opponent term (`stage4_features.py:574, 959-962`).
  * **The 17 one-step forms.** A match's value is z = (value − E_o) / MAD_o, where E_o is what the opponent's own earlier opponents did against him, at whatever level he usually plays (`stageB_adjperf.py:144-145, 195-207`). So a Challenger match is measured against Challenger opponents' norms.
    * Same player, same season: the adjusted value keeps about **78% of the raw Challenger boost** (men; women 77%; qualifying 77–83%).
    * Per statistic (men's Challengers, z units): first-serve points won +0.41, holds +0.42, breaks +0.41, second-serve points won +0.31, aces +0.25.
    * The style statistics barely move: first serves in +0.05, double faults −0.09.
  * **`sets_14d` and the 4 surface counts:** plain counts.
* **26 are opponent-adjusted (online ratings or joint solves) with no level term:** offset Elo (2), `elo_games`, `ratings_iid`, `ios_points_short`, the 14 IOS ratings and the 7 products.
  * **The joint solves remove most of the same players' gap, not all:** 64–87% of the total-points gap ([03](team/03_translation.md) §2.2).
  * **They leave a residual:** men's Challengers +0.37 [+0.24, +0.50] points per 100, Slam qualifying +1.19.
  * **When lower-based and main-tour-based players meet,** the two groups' ratings are not on one scale (03 §2.4).
  * **Level averages of the residuals are small:** within ±0.32 points per 100 serve points for `ratings_iid`, and ±0.08 SD for the IOS apart from break points saved. But they are near zero almost by construction, since most players play mostly one level.
* **Level-aware:** only stage 2's speed centring, and the `level` input, which is the level of the match being forecast, not of the history.

**The one-step forms under-adjust in general, not just across levels** (*Observed* by the red team, [07](team/07_red_team.md) S3 and its appendix; main-tour matches of 2013–2024, within player-season):
* the per-match z of total points won rises +0.25 per unit of the opponent's log ranking (SE 0.005, men; 0.006, women);
* the raw rate rises about 0.39 z per unit;
* so the z keeps about 65% of the opponent-strength gradient inside the main tour.

So a run of qualifiers and wild cards inflates a player's form, and a run of seeds deflates it. The 78% level shift is one case of this.

### 1.3 The contamination paths

*Observed* ([01](team/01_lineage.md) §B; [03](team/03_translation.md) §2; [07](team/07_red_team.md)):

| Path | Inputs | Size | Status |
|---|---|---|---|
| One-step forms keep the level boost | 17 | about 78% of the raw shift | Confirmed, measured |
| One-step forms under-adjust for opponent strength in general | 17 | about 65% of the opponent-ranking gradient kept, inside the main tour | Confirmed, measured (new) |
| `points_52w` pools raw rates | 1 | the full raw shift: total points +2.9, breaks +8.4 per 100 (men's Challengers) | Confirmed |
| The IOS prior pulls thin-evidence players toward a pool-wide zero that is nobody's peer group | 21 + 1 (`ratings_iid` untested) | lower-based women over-rated at the main tour: break points saved +1.02 [+0.75, +1.29] per 100, holds +0.58 [+0.25, +0.92] | Confirmed. Present even with no lower-level rows (+1.16), so a prior problem, not an equivalence problem |
| The products' zero point moves with the pool's level | 7 | spread +25–56% in 2025–26 (finding #6) | Confirmed. [Centring](../ios_product_centring/README.md) removes the drift; at the close it read −0.06 [−0.33, +0.21] mLL (+ = centred better; unresolved, P(better) 0.33, a lean worse in every reading). Not adopted |
| Qualifiers' own qualifying rounds feed their main-draw form; no input marks a qualifier | the 17 forms most | 13% of frame player rows; their form evidence 75% (men) / 68% (women) lower-level, and those rounds are selected on winning | Confirmed (new) |
| The history's level mix moves between seasons with coverage | the 41 box-score inputs | women's lower-level share of box-score evidence 15% (2013–18), 23% (2019–24), 32% (2025–26); WTA 2015 none at all | Confirmed (new) |
| One Elo K for every level | 3 | an ITF update weighs 5–8% more in `elo_games`; Elo about calibrated across levels | Low harm |
| Constants tuned on pools that are mostly lower-level | every tuned input | men 75%, women 36–42% of the tuning pools | Confirmed; a fit question, not a bias |

### 1.4 Gaps in the guardrails

*Observed unless marked* ([01](team/01_lineage.md) §A, B; [04](team/04_incoming.md) §2, §6; [07](team/07_red_team.md) S8):
1. **The Challenger speed dose rose with no guard.**
   * Usable Challenger speed rows (main draw and qualifying) were 93–96 a season in 2023–2025, about 1.5% of the panel. In 2026 they are 945 (ManTennisData), about 13%.
   * The daily collector (enabled) plans Challenger matches too.
   * `history.py` checks Stage 0 only, not the speed panel.
   * Stage 2's coefficients were fitted on histories that included Challenger speeds, but at the low dose.
2. **A timeline refresh can change leak-proof inputs without touching Stage 0** (*inferred from the code*, `history.py:58` compares Stage 0 facts only). After the SofaScore runs, `match_timing/refresh.py --sources sofascore` rewrites the timeline and the leak-proof IOS table, and the history gate would not see it. Two decisions meet here: the match-clock decision makes that refresh the routine after new dates, and the frozen-reference gate does not cover the timeline.
3. **The live history lost its lower levels in June 2026.**
   * Since July, Stage 0 holds no ITF match, no men's Challenger qualifying, no WTA 125 and no women's qualifying. Sackmann's lower tiers ended on 1–2 June; Tennis My Life does not carry them.
   * So women's live inputs rest on an almost main-tour-only history, unlike every training season (finding #7, wider than recorded).
   * The prediction-run gate cannot see these missing matches, because they are not in Stage 0. In 2026 alone: 1,593 women's ITF matches involving main-tour players.
4. **`compare.py`'s input check works by tour-season.** Inflation confined to ITF-active players may move no tour-season's spread by 10% or its mean by 0.10 SD (*inferred*).

## 2. How much of the evidence is lower-level, and for whom

*Observed* ([02](team/02_composition.md); model matches of 2019–2024; pooled over sides):

| Input family | Men | Women |
|---|---|---|
| Two-week form (17 inputs) | 27% | 25% |
| `ios_points_short` | 28% | 23% |
| `points_52w` | 34% | 23% |
| IOS profile (21) | 38% | 23% |
| `ratings_iid` | 45% | 24% |
| Elo family (career results) | 55% | 54% |

* **Ranking decides it.**
  * Two-week form: top 20 under 1%; ranked 51–100, about 30%; 101–200, 60–69%; 201+, 64–76%.
  * `points_52w` reaches 75–87% for men ranked 101+.
* **In half of all model matches (50%, results channel), at least one player's last year was mostly lower-level.** At the 250s that is 64% of men's matches and 73% of women's. In the box-score channel it is men 50%, women 39%.
* **Low main-tour exposure is common, and comes with plenty of lower-level evidence.** In 24% of model matches the less-exposed player has fewer than 10 main-tour results in 365 days. For 84–88% of them, three quarters or more of the year was lower-level. Per year:
  * men: 4 main-tour box scores against 43 lower-level ones;
  * women: 4 against 12, plus 26 ITF results with no box score.
* **Women's box-score inputs already shift with coverage, not with the players** (§1.3). The model trains on all these seasons pooled.
* **ITF box scores of 2025–26** (Sackmann's, January 2025 – May 2026) already reach 42% of women's model matches (men 7%).

## 3. What a lower-level match is worth

### 3.1 Raw rates are not comparable

*Observed* ([03](team/03_translation.md) §1). Same players, same season, at a Challenger rather than the main tour (points per 100; + = higher at the lower level):

| | Total points won | Holds | Breaks | Aces | First serves in |
|---|---|---|---|---|---|
| Men | +2.9 [+2.8, +3.0] | +3.7 | +8.4 | +0.4 | −0.2 |
| Women (WTA 125) | +2.5 [+2.3, +2.7] | +4.0 | +7.7 | +0.1 (interval spans 0) | +0.4 |

* **The return side shifts most:** weaker opponents serve worse.
* **Statistics a player controls alone barely move** (first serves in, double faults). Outside practice finds the same: process statistics translate, and opponent-dependent outcomes do not ([05](team/05_best_practice.md) §2.7).
* **A correction to the event-levels study.** Its break shifts mixed in 18,138 rows that have return games but no break count. On complete rows:
  * men's qualifying +7.1, not +8.5;
  * women's qualifying +7.3, not +9.1;
  * WTA 125 +7.7, not +6.8.

### 3.2 For the aggregate inputs: translate, and the weight barely matters

*Observed* ([03](team/03_translation.md) §3.2). A credibility estimator predicts each player's next main-tour statistic from his previous 365 days:

θ̂ = (k·μ + main-tour evidence + w_L·(lower-level evidence − δ_L·units)) / (k + main-tour units + w_L·lower-level units)

* δ_L is the level's offset (the translation) and w_L its weight per unit (1 = equivalent, 0 = useless). Both are fitted on 2013–2018 and scored on 2019–2024.

| Comparison (milli per unit, + = the first named better) | Men | Women |
|---|---|---|
| Pooled as equivalent vs main-tour only, breaks | −1.43 [−1.86, −1.00] (worse) | −0.58 (worse) |
| Translated and weighted vs pooled, breaks | +1.98 [+1.47, +2.49] | +1.17 [+0.89, +1.44] |
| Translated and weighted vs pooled, holds | +0.45 [+0.21, +0.69] | +0.68 [+0.39, +0.97] |
| Translated and weighted vs pooled, total points | +0.22 [+0.18, +0.27] | +0.19 [+0.15, +0.23] |
| Translated and weighted vs main-tour only, breaks | +0.55 [+0.36, +0.73] | +0.59 [+0.40, +0.79] |
| Same, players with under 10 main-tour matches in the year: translated and weighted vs pooled, breaks | +5.22 | +3.60 |

* **The translation carries the gain.** Translated alone is nearly equal (men's breaks +1.97 [+1.48, +2.47]); the weight adds at most +0.04. Discounting without translating pushes the return statistics' weights to 0.
* **The fitted parameters rank the arms; they are not structural exchange rates** (*Inferred*, [07](team/07_red_team.md) S4).
  * The estimator shrinks everyone toward one prior mean (the main-tour average), weighs a year's matches equally with no recency, and has no opponent term.
  * So δ and w also absorb each group's own level, recency and opponent mix. Symptoms:
    * women's tour-qualifying weights sit above 1 (total points 1.42 [1.21, 1.70], 90% bootstrap);
    * men's Challenger offsets are larger than the same-season gaps (total points +3.9 against +2.9; holds +6.8 against +3.7);
    * women's WTA 125 offsets are smaller than theirs.
  * Read "a men's Challenger match is worth about 0.5–0.7 of a main-tour match" (w 0.73 [0.58, 0.93] on total points) as indicative only.

The UFC parallel is closer than it first looks. The UFC prior starts a newcomer at a flat newcomer anchor, below the UFC average, skewed toward his outside record ([06](team/06_ufc_analog.md) §1.2). That is nearer to the home-tier prior of §3.3 than to this estimator's single main-tour mean.

### 3.3 Inside the joint solves: the prior is the leak

*Observed* ([03](team/03_translation.md) §2, §3.1), on a simplified copy of the IOS (pooled surfaces, weekly snapshots, the decided constants):
* **The joint solve removes 64–87% of the same players' total-points gap.**
* **The leftover level "condition" offsets are small and drift by era.** Men's serve points won at Challengers: −0.2 points in 2010–2018, −0.6 in 2019–2024. Correcting for them gains at most +0.06 milli per unit (aces).
* **Lower-level box scores carry real information.** Dropping them costs every statistic 0.2–1.3 milli per unit, and low-exposure players 0.5–4.9 (men's holds −4.88).
* **A 2× discount helps men only:** holds +0.20 [+0.15, +0.25], break points saved +0.08, and the points statistics a little (+0.02 to +0.03). For women, no discount is best.
* **The remaining bias comes from the prior:**
  * **The mechanism.** The ridge pulls a player with thin box-score evidence toward one pool-wide zero, which sits far below main-tour players. On men's serve points, the average serve rating is +0.38 for main-tour-based players, +0.20 for Challenger-based and +0.09 for ITF-based (log-odds).
  * **Who it hits.** Lower-based women are over-rated at the main tour (break points saved +1.02 per 100), almost entirely those with under 5 typical matches of evidence. Their break points saved fall 2.99 per 100 short of the prediction (95% half-width 1.25; short = over-rated).
  * **A prior set by the player's home tier** (the tier where most of his previous year was played, known from his own earlier matches) fixes much of it:
    * **The bias, 2019–2024:** women's holds +0.63 → +0.10; second-serve points +0.58 → +0.26.
    * **The fit, 2019–2024:** women's holds +0.08 [+0.02, +0.13] and break points saved +0.07 [+0.05, +0.09] milli per unit; low-exposure women up to +0.22.
  * **But it is not clean** ([07](team/07_red_team.md) S1):
    * it over-corrects women's holds in 2013–2018 (−0.87 [−1.38, −0.36]: lower-based women then under-rated), although the likelihood still improves there (+0.24);
    * it leaves break points saved over-rated (+0.70 [+0.43, +0.96]);
    * the women's WTA 125 tier is empty, so its members fall back to the pool's zero.
  * **It is FIDE's 2024 problem** ([05](team/05_best_practice.md) §2.5): newcomers with biased first ratings entering one connected pool. FIDE fixed it with a prior for newcomers, a cap and an anchor.

### 3.4 Results: leave Elo alone

*Observed* ([03](team/03_translation.md) §4; `elo_k.csv`). A plain Elo over every level, scored on main-tour matches of 2013–2024 (its own log loss, not the model's; + = better than full weight):
* **Dropping lower-level results hurts:** at ×0, men's Challengers make it worse by 6.8 [5.2, 8.4] mLL, and women's ITF results by 6.4 [4.7, 8.1].
* **Half weight (×0.5) is worse** for men's Challengers: −0.58 [−1.10, −0.06].
* **×0.75 is unresolved everywhere.** Men's Challengers +0.01 (P 0.54); women's Challengers +0.03 (P 0.65); men's ITF +0.13 [−0.01, +0.28] (P 0.96, a lean toward discounting); women's ITF +0.06 (P 0.68).
* **×1.25 is worse,** except women's Challengers (unresolved, P 0.04).
* Elo is a priced-in control in the owner's thesis: a check, not a lead.

### 3.5 ITF: not estimable yet

* *Observed.* ITF box scores exist only in 2025 (95%) and 2026 (99%), all inside the holdout. No ITF translation can be fitted without reading it.
* After P7, the same-player, same-season anchors on development seasons (2018–2024) grow:
  * men's ITF with Challengers: from 0 to 2,109;
  * women's ITF with the main tour: from 6 to 851 ([04](team/04_incoming.md) §4).
* Men's ITF evidence has to be translated through the Challengers, carrying the error of the chain.
* `translation.py` reruns unchanged on a candidate Stage 0 and gives ITF and ITF qualifying their own offset, weight and tier mean (§10).

### 3.6 What can bias these numbers

*Inferred* ([03](team/03_translation.md) §6; [05](team/05_best_practice.md) §2.1; [07](team/07_red_team.md) S1, S5):
* **Selection, direction unknown.** A season with matches at two levels is partly chosen by its results: players drop after losing and climb after winning. Yet the forecasting offsets are larger than the same-season gaps, not smaller, because they also absorb the prior mean, recency and opponents. The first candidate's same-season offsets may under-translate.
* **Selection in the tier means runs both ways.** They average every player-season of a tier with enough evidence: generous to true newcomers, harsh on the best of a tier, who are the ones the model forecasts. Over-correction pushes toward the market's error (§4).
* **Drift.** The condition offsets moved by era (men's Challenger serve offset −0.2 → −0.6). Tennis Abstract's Challenger ratio slid from 1.100 to 1.086 over 2012–2017, and the UFC's transfer ratio jumped from 0.02 to 0.71. So a 2010–2018 offset is a fair but possibly stale test for 2019–2024, and an adopted translation must be refitted walk-forward.

## 4. Where it matters for betting

*Observed* ([02](team/02_composition.md) §8; 2020–2024; the frozen reference's forecasts, both stages, against its own input: the books' average close, recalibrated as decided):
* **The model's edge does not depend detectably on exposure or lower-level dose.** All 22,265 matches: +1.374 [+0.668, +2.081] mLL over the recalibrated close (+ = model better), exactly the reference's published figure. Every both-tours stratum's estimate is positive (+0.8 to +4.1), and no family of strata differs (heterogeneity p = 0.12–0.92).
* **The close under-rates the player with more lower-level evidence.** The result is regressed on the forecast's log-odds; + = the forecast under-rates that player.

  | Difference of the two players' box-score lower-level shares | Matches | The close (SE) | The model (SE) |
  |---|---|---|---|
  | 0–0.10 | 6,457 | −0.01 (0.03) | −0.02 (0.03) |
  | 0.10–0.25 | 4,820 | +0.09 (0.03) | +0.08 (0.03) |
  | 0.25–0.50 | 5,265 | +0.09 (0.04) | +0.06 (0.04) |
  | **0.50–1** | **5,619** | **+0.18 (0.04)** | **+0.09 (0.04)** |

  In the 0.50–1 stratum the model beats the close by +1.46 [+0.20, +2.73] mLL (better).
* **The close's calibration.** It is too timid when a player has no main-tour record in the year (slope 1.15 both tours, 1.33 men; 1 = right-sized), and too extreme in women's matches between established players (0.90). The model's slopes track the close's.
* **Pinnacle shows the same under-rating.** Its β on the share difference is +0.17 [+0.08, +0.26] in 2020–2024 ([event levels](../event_levels/README.md) §8). Since 9 Oct the decided odds input is "Pinnacle first" ([decision](../../decisions/2026-10-09-pinnacle-first-odds-input.md)). The stratum table above is on the books' average, the frozen reference's input; part 5 of `composition.py` can be re-run on the Pinnacle-first instance (`--model data/studies/current_best_model/pinnacle_first_2026-10-09`) before relying on the +0.18.
* **The edge is in-sample for the choices.** It lies in the seasons that chose the inputs: +0.18 [−0.28, +0.64] in 2015–2019 against +1.46 [+0.84, +2.08] in 2020–2024 ([feature provenance](../feature_provenance/README.md)).
* *Inferred.* This is the event-levels study's "climbers" finding, located: it sits in the quarter of matches where the two histories differ most.
  * Today's inflated forms lean the model toward these under-rated players, which corrects part of the market's error.
  * A correct translation removes that lean, so it could lose at the close unless the model gets the information another way.
  * The test therefore carries share controls (§7, §9). The UFC work met this trap first ([06](team/06_ufc_analog.md) §5.1).
* **Staking** (Suggestion, [05](team/05_best_practice.md) R7). Forecasts that rest on thin main-tour evidence are less certain. Shrink the stake there, even at the same edge, once per-stratum calibration is measured on the venue's prices.

## 5. What is coming

*Observed* ([04](team/04_incoming.md); status at 15:15 UTC, 9 Oct 2026; dates *inferred* from the logged pace):

| Package | What | Status | Lands (about) | Reaches the 58 inputs? |
|---|---|---|---|---|
| P1 | ITF live API, daily from 15 Sep 2026 | Done; daily job on | landed | Yes once wired (results; box scores of 2026 on) |
| P4 | TennisLive listings: every level 2018–2026, incl. 158,824 men's ITF qualifying results | Done | landed | Results only (Elo, counts); 0.6% of that ITF qualifying involves a main-tour player |
| P5 | TennisLive pages: Challengers 2018–24, qualifying | Running | evening of 10 Oct | Barely: point logs feed no input |
| P6 | SofaScore: Challengers, WTA 125, tour residual, WTA 2018 | Running (gap 1 of 7) | 12–13 Oct | Barely: points feed no input |
| **P7** | **SofaScore: ITF 2025–26, then 2018–24** | Queued | 2025–26: 17–18 Oct; **2018–24: 31 Oct – 2 Nov** (≈ 22 Oct at the faster pace) | **Yes: ~197,000 box scores** |
| P8 | TennisLive: the ITF pages SofaScore lacks | Queued | early–mid Nov | Yes (partial point logs) |
| P2 | WTA API catch-up; women's ITF after September | Not started | ~8 h once started | Yes: repairs women's live history |
| P9 | ATP Stats Centre 2025–26 incl. Challengers | Not started | 2–3 days once started | Stage 2, if Challenger files carry speeds (unmeasured) |
| P11 | Odds below the 250s | Not started (probe) | unknown | No input; enables a lower-level market test |

* **None of it is in Stage 0.** Stage 0 reads only Sackmann's and Tennis My Life's files (`stage0_build.py:93-106`).
  * Under the owner's history rule, every addition is "new past" or "revised", so it can reach the model only through a candidate build.
  * That needs identity crosswalks, a box-score override table and timeline adapters.
  * It will be the first real run of `run_chain.py`'s lane 0.
* **P7 builds in a step.** It stops at 2018. In 72% of women's model matches of 2013–2017 a player has pre-2018 ITF matches that stay results-only. So every training window would mix seasons with and without ITF box scores.
* **Repair data already on disk:** WTA API box scores for 1,943 women's 2025–26 lower-level matches that Stage 0 lacks.
* **Data-quality risks that bias a lower-level profile** ([04](team/04_incoming.md) §5):
  * **TennisLive's point logs** drop the game that closes each set. That lowers a set winner's points-won share by about a point, understating the players who dominate a level. Its match-total box scores matched the official ones in all 151 matches of the P5 trial.
  * **ITF qualifying statistics** exist mostly for final rounds, which flatters qualifiers.
  * **P5 and P6 fetch the same Challenger matches.** Weekly venues hold real rematches, so deduplication must key on the event, not the pair.
  * **Integrity alerts** concentrate at Challenger 50/75 and ITF.

## 6. What others do, and the UFC precedent

### 6.1 The common recipe

*Measured in each source, inferred as a pattern* ([05](team/05_best_practice.md) §1). Every mature field does four things:
1. translate lower-tier evidence per statistic;
2. count it as fewer observations;
3. shrink toward comparable players, not the top-tier average;
4. let top-tier data take over as it accumulates.

| Field | Translate | Discount | Shrink toward |
|---|---|---|---|
| Baseball projections | per component (AA→MLB home runs ×0.56, strikeouts ×1.27) | translated, then regressed like any sample | a mean weighted by the chance of reaching the majors (age for level) |
| Hockey (NHLe) | one factor per league (AHL 0.53, KHL 0.71) | one predictor among several, not NHL data | — |
| US Chess (Glickman & Doan, 2026) | a formula from the FIDE rating | worth 5–10 games, decaying with staleness; "established" needs 25+ | age-based rating |
| FIDE (2024 reform) | — | two hypothetical draws against 1800 | a cap at 2200; a one-time compression after biased newcomers drained the pool |
| Tennis Abstract | Challenger total points ×1.086–1.103 (2012–17) | no gain from weighting "important" matches | newcomers by level and gender |
| The owner's UFC prior | a ridge from the outside record | 0.9 × the centred prediction | a flat newcomer anchor, fading over 6 UFC fights |

* No published tennis study translates box-score statistics across levels beyond total points won, or tests level-discounted histories against the market.
* The installed TabPFN takes no sample weights (`fit(X, y)`), so a prior has to enter through better-built inputs or a stage-2 term.

### 6.2 The UFC precedent

*Observed in the UFC repository* ([06](team/06_ufc_analog.md)):
* **The mechanism.** A fighter's prior for two ratings is a ridge on nine counts of his pre-UFC record, set at a flat newcomer anchor + 0.9 × the centred prediction, and fading linearly to zero over six effective UFC fights. The outside data are results only.
* **What it has been worth.**
  * Nothing measurable beyond the debut betting line: the UFC market had priced the record.
  * The prior's direct channel read slightly harmful; removing it from that channel was 0.16 mLL better.
  * The one shipped "informative, not equivalent" device is a ramp gate that damps a pooled win rate on rookie fights. Its value faded as the worth of an outside result rose from 0.02 to 0.71 of a UFC result between eras.
* **What transfers** (*inferred*): the testing method (channel by channel, placebo twins, in-place changes, splits by exposure, pre-registration) and the shape of the fix.
* **What does not.** Tennis players move between levels every few weeks, the cross-level opponent graph is dense, Challengers have full box scores, and the tennis market **under-rates** players arriving from lower levels.
* **So the adaptation:** a level offset inside the evidence itself, fitted walk-forward, rather than a fading prior. Main-tour matches take over naturally, and top players, who have no lower-level evidence, are untouched by construction.

## 7. The first test on the model: translating the 18 aggregates

*Observed* ([08](team/08_candidate.md); built and scored on 9 Oct 2026, 16:11–19:21 UTC).

**What is tested.**
* Each lower-level match enters the 17 one-step forms and `points_52w` shifted by a per-statistic, per-tour, per-level offset. Nothing else changes.
* **The offsets:** same-player-season contrasts of 2010–2018, frozen. This is the decided convention for normalising constants: no leak in the scored seasons, and in-sample for the 2013–2018 training rows exactly as the reference's own constants are.
* **No leak probe is needed:** the translation changes only each player's own matches (its invariance gate checks this).
* **ITF** uses the Challenger offsets as a placeholder (no ITF box score exists before 2025). The placeholder changes only 2025–2026 inputs, so the test does not score it. If the candidate were adopted before P7's own ITF offsets exist, women's live ITF evidence would be translated by an untested offset.

**How.**
* Built in a sandbox copy of the chain (`run_chain.py --setup --candidate`); the repository's builders are untouched.
* Gated: every other input must equal the reference's exactly, and matches whose players have no lower-level evidence must not move.
* Fitted on seasons 2019–2024 and scored on 2020–2024 with `compare.py`, both stages.

**The pre-registered arms** (`data/studies/lower_level_evidence/candidates/preregistration.md`, hashed before any score):
* both changes together (the primary);
* each channel alone;
* half the dose;
* a placebo twin (the same changes shuffled across matches);
* the history-share control: with and without `low_share_diff`, event-levels' C1 input.

**Added before the scores, dated** (from the red team's review): the reference plus the two box-score share differences that actually drive the translation (two-week and 365-day). C1's 365-day results share is not the share behind 17 of the 18 changes.

**What it can and cannot show** (*inferred*, written before the scores; [07](team/07_red_team.md) S2, S5, S7):
* **It re-centres; it adds no new skill information.** With one offset per statistic, tour and level, each form becomes "today's form − δ × the player's shrunk lower-level share in its two-week window", and `points_52w` the same over 364 days. So it gives TabPFN the two shares with fixed loadings, in place of today's inflation.
* **Expect a small effect,** near C1's: the share as a 59th input read +0.06 [−0.10, +0.23] (unresolved, P(better) 0.76).
* **The adoption bar.** By the adoption framework, a gain must clear the shrunk bar: B·(estimate − selection) > c, with τ ≈ 0.03 and c ≈ 0.01 mLL. At this test's precision that means roughly +0.04 to +0.26 mLL, plus the winner's luck if the primary were chosen among arms. Failing that, the case is harm prevention before the ITF flood ("more of a kind of data already used": not clearly negative, input check clean). That is a suggestion on mechanism, for the owner.
* **The input check may flag it "uneven" by construction.** The dose follows each season's coverage: women's 2015 has almost no lower-level box score, and men's Challenger qualifying has none in 2010–2015. Read any flag against `inputs_dose.csv` before treating it as harm.
* **The dose brackets only from below.** The half dose sits under it; same-season offsets may under-translate (§3.6). An arm at about 1.5× would bracket from above.

**The gates** (all passed before any fit; `data/studies/lower_level_evidence/candidates/checks/`):
* **Reproduction.** The 40 untranslated inputs are identical to the reference's on all 67,226 matches. At zero offsets, the build's code reproduces the 18 translated inputs exactly.
* **Invariance.** On the 612 matches where neither player ever had a lower-level box score, the 17 forms did not move. On the 8,219 with none in 365 days, `points_52w` did not move.
* **Direction.** All 34 required input-tours moved toward the player with less lower-level evidence.
* **Linearity and the fit runner.** The forms are linear in the offsets; `points_52w` is not, so the half dose used its exact value. The runner for the 59- and 60-input arms reproduces a stored reference fit exactly.
* **No change to the builders' own constants or leak probes.** Stage B re-chose the reference's constants, and Stage 4's and Stage B's probes pass with the hook on.

**How far the inputs moved** (median change, in the reference's SD):
* the serve-side forms: 0.01–0.14;
* the return-side and defence forms: at most 0.09. They shrink hard (K up to 160 typical matches), so the same offset moves them little;
* `points_52w`: 0.45 (men) and 0.26 (women), by far the largest change.

So the per-match level shift of §1.2 (78% of the raw boost) reaches the two-week form inputs only weakly.

**The input check.**
* The 17 forms: no flag.
* `points_52w`: its spread widens by 9–36% in every tour-season, with its level unmoved. 27 of 28 tour-seasons are flagged "uneven". The one exception is women's 2015, just under the 10% line, the season with no women's lower-level box scores.

**The readings** (2020–2024, both stages, 22,265 matches; mLL, + = the first-named model better; `candidates/results/pairs.csv`):

| Comparison | Both tours | Men | Women |
|---|---|---|---|
| **FP (both translated) vs reference: the primary** | **+0.024 [−0.047, +0.096], unresolved, P 0.75** | +0.083 [+0.002, +0.164], better | −0.040 [−0.154, +0.073], unresolved, P 0.24 |
| F (forms only) vs reference | −0.003 [−0.060, +0.054], unresolved, P 0.46 | +0.005, unresolved | −0.010, unresolved |
| P (`points_52w` only) vs reference | +0.029 [−0.019, +0.077], unresolved, P 0.88 | +0.066 [+0.001, +0.131], better | −0.012, unresolved |
| FP_half vs reference | −0.009 [−0.064, +0.047], unresolved, P 0.38 | +0.027, unresolved, P 0.82 | −0.048, unresolved, P 0.12 |
| FP vs its placebo twin | +0.053 [−0.036, +0.142], unresolved, P 0.88 | +0.197 [+0.059, +0.335], better | −0.106 [−0.231, +0.019], unresolved, P 0.05 |
| FP_L vs R_L (both with event-levels' C1 share) | +0.075 [−0.007, +0.157], unresolved, P 0.96 | +0.115 [+0.001, +0.228], better | +0.031, unresolved |
| R_S2 (the two box-score shares) vs reference | +0.027 [−0.128, +0.182], unresolved, P 0.64 | +0.152 [−0.052, +0.357], unresolved, P 0.93 | −0.111 [−0.321, +0.098], unresolved, P 0.15 |
| **FP vs R_S2 (the dated addition)** | **−0.003 [−0.165, +0.160], unresolved, P 0.49** | −0.069, unresolved, P 0.24 | +0.071, unresolved, P 0.73 |

FP against the reference by stratum:

| Stratum | Matches | Inputs moved (SD) | mLL [95%] |
|---|---:|---:|---|
| Less-exposed side under 10 main-tour results in 365 days | 5,913 | 0.18 | +0.040 [−0.152, +0.232], unresolved, P 0.66 |
| 10 or more | 16,352 | 0.04 | +0.019 [−0.068, +0.106], unresolved, P 0.66 |
| The two players' 365-day box-score shares differ by 0.5 or more | 5,619 | 0.24 | **+0.165 [+0.004, +0.326], better** |
| They differ by less | 16,542 | 0.04 | −0.017 [−0.090, +0.055], unresolved, P 0.32 |
| Falsification: both established, both shares under 0.10 | 3,652 | 0.00 | −0.033 [−0.155, +0.088], unresolved (no decision rule) |

Without a decision rule:
* **By season:** 2020–2023 read −0.07 to +0.03 (all unresolved), and 2024 +0.183 [+0.020, +0.346].
* **By level,** all unresolved: the 1000s +0.104 (P 0.95), the 250s +0.055.
* **Against its own calibrated close,** every arm stays about +1.35 to +1.49 better.
* **Stage 2** barely notices: the 2024 coefficients agree within 0.005 across arms.

**The pre-registered verdict: unresolved, and not suggested for adoption on mechanism.**
* The primary is unresolved: the pre-registration's "tie" branch, read as "unresolved" under the owner's decision of 9 Oct.
* Of that branch's three conditions, two hold: no secondary is worse, and every secondary was scored.
* The third fails: the input check's pre-registered test counts `points_52w` as an unexpected uneven input.
* *Inferred* (08): the flag is a threshold artifact of a broad, every-season change, not finding #6's some-seasons shape. In its own season profile the translated `points_52w` is more even across eras than the reference's.

**The dated addition decides the reading regardless.** The translated model does no better than the reference given the two share differences (−0.003, P 0.49). What the translation adds at the close is the share signal in disguise, as the red team predicted.

**Reading it** (*Inferred*):
* **The equivalence problem is real at the input level,** and the translation fixes it there (the gates; the offsets' size). The men's model gains about +0.08 mLL from it, all through `points_52w`, in the matches where one player's evidence is mostly lower-level. The falsification stratum, where nothing moved, shows nothing: the mechanism sits where it should.
* **But two share columns deliver the same,** without changing 18 inputs. There is no dose-response (the half dose reads −0.009).
* **Women lean the other way** (FP −0.040; against its placebo −0.106, P 0.05). That fits role 03's finding: women's translated lower-level evidence is worth about one-for-one, and women's bias sits in the IOS prior, not in equivalence.
* **The size.** At best about a tenth of an mLL for men, against the model's +1.37 over the close, and in seasons many studies have read.
* **So at today's dose the contamination costs the model nothing measurable at the close, and the cure adds nothing a share column would not.**
* **The case for the layer is the coming dose.** P7 adds 11–14 points of lower-level box-score evidence for women in 2019–2024 (on top of today's 23–25%), and it comes from a level whose gap to the main tour is probably larger than the Challengers' (unmeasured until P7). A test on that data is the one that can show harm prevented.

**What it changes in the proposal** (§8):
* **The first remedy is not adopted now.** Its hook, offsets, gates and arms are the ready-made test for the ITF wiring: "ITF as it stands" against "ITF through the layer" against the reference.
* **The share signal gets its own pre-registered candidate:** the two share inputs, or a shrunk stage-2 term. It is scored against the reference and read on seasons no choice has seen, since these readings suggested it.
* **The input check's "unexpected uneven" test needs a better definition** before the next candidate (§8.4): read a flag against the tour-season's own change of evidence mix, not against a median split.
* **The sandbox** (`C:/Users/zerom/tnr_lle`, 18.9 GB) is kept, as CLAUDE.md requires mid-session. `MODEL_REBUILD_SANDBOX=C:/Users/zerom/tnr_lle ./python.sh src/eda/model_rebuild/run_chain.py --cleanup` removes it when the owner agrees.

## 8. The proposal

### 8.1 The principle

**One main-tour skill per player and statistic. Lower-level evidence informs it through a translation (an offset per statistic and level) inside a credibility blend; the player's own main-tour evidence takes over as it accumulates. A player with no lower-level evidence is untouched.**

This is the UFC "newcomer, skewed toward his record elsewhere", adapted to a career that moves between levels every few weeks, and done statistic by statistic, which UFC data never allowed.

### 8.2 Channel by channel

| Channel | Remedy | Evidence | When |
|---|---|---|---|
| **One-step forms (17) and `points_52w` (1)** | **Translate** each lower-level match by δ(statistic, tour, level), refitted walk-forward on the match clock. A down-weight only as its own pre-registered arm: the fitted weights are confounded (§3.2) | §3.2; §1.2; §7: no gain at the close beyond the share signal | **Built and tested; not adopted now.** It is switched on with the ITF data (§8.3), where its machinery is the ready-made test |
| **The share signal** | The two players' lower-level shares of box-score evidence (two-week and 365-day) as two inputs, or as a shrunk stage-2 term like the speed adjustment | §4 (the close under-rates the more lower-level player by +0.18 log-odds where shares differ by 0.5+); §7 (R_S2: men +0.152, P 0.93) | A new pre-registered candidate, read on seasons no choice has seen |
| **The forms, on one scale** | Measure every match, at every level, against the leak-proof joint solve's prediction instead of the opponent's raw norm. It fixes the level shift and the general opponent-strength under-adjustment together (Stage B's own suggestion: `docs/studies/ufc_ideas/stageB.md`, "so that every z sits on one scale"). It changes every form, so it is its own candidate, cross-player, needing the clock and `probe.py` | §1.2 (65% of the opponent gradient kept) | The third candidate |
| **Joint solves: IOS profile (21), `ios_points_short`** | **Anchor:** a home-tier prior in place of the pool-wide zero, with an empty tier falling back to the nearest populated one, never to 0. Then, as separate arms, product centring (not adopted; it leans worse at the close), half weight for men's holds and break points saved, and a condition offset for aces | §3.3, with its over-correction in 2013–2018 | The second candidate, before P7 is wired |
| `ratings_iid` | The same anchor, after measuring it | not yet measured | with the second candidate |
| **Elo (2), `elo_games`** | Leave as is: full weight for every level | §3.4 | — |
| **`sets_14d`, surface counts** | Keep counting every level; restore the lost feeds (§8.4) | UFC: the any-organisation clock was right | live hygiene |
| **Stage 2 `spd_L`** | Cap the Challenger dose to what the fitting seasons held (about 90 rows a season), or put the speed panel behind the history check. Then Challenger speeds as their own candidate | §1.4 | **Now** (cheap) |
| **Training rows** | Keep main tour only | §1.1 | — |
| **Qualifiers** | Partly covered by the translation (qualifying offsets about +2.4–3.4 points). Their same-event qualifying matches are selected on winning, so read a declared qualifier stratum before deciding on anything more | §1.3 | with the next candidate (the first read no qualifier stratum) |

### 8.3 The ITF data (P7): how it should enter

1. **Not by itself.** Wired as it stands, it would:
   * inflate the 17 forms and `points_52w` for ITF-active players (mostly women ranked 100–300, and qualifiers);
   * move the IOS zero point and the products in every season from 2018;
   * create the 2018 step (§5).

   The input check would call it uneven; `refresh.py --scenario p7` already does.
2. **Estimate its own offsets, weights and tier means walk-forward, on the match clock.**
   * For a match of season Y, they come from ITF box scores of 2018 .. Y − 1 only, under the two-time rule, and never from 2025–2026.
   * `translation.py` with moved windows (§10) is the statistic-level review. Its fixed 2018–2021 set must not be carried into a model candidate scored on 2020–2024.
   * If a fixed set is used anyway, pre-register scoring only on the seasons after its fit window (2022–2024 for a 2018–2021 fit).
3. **Then let it in only through the layer** (translated in the aggregates, tier-anchored in the solves), as a candidate against the frozen reference, input check first.
4. **The layer removes the level inflation, not the volume step.** From 2018, ITF-active women's inputs become much less shrunk (a woman ranked 201+ goes from about 10 box scores a year to about 32). The input check may still flag them. The cures:
   * **P7 back to 2014**, if SofaScore serves women's ITF of 2014–2017. Collection is approved, so that needs no decision.
   * **Both arms trained from 2019**, as a control for the step (a candidate from 2019 against the reference from 2013 would measure the window, not the step).
   * **A cap** on ITF evidence's effective count.
5. **Expect the tier prior to matter most here:** ITF-based women are the thin-evidence group of §3.3.

### 8.4 Guardrails

1. **Speed panel:** cap the Challenger dose to what the fitting seasons held, or extend the history check to the speed panel, before the daily collector brings Challenger speeds in bulk.
2. **Timeline refresh:** before `match_timing/refresh.py --sources sofascore` runs after P6/P7, measure whether it moves any frame input of the reference. If it does, treat it as a candidate build.
3. **The June feed loss:** restore the lost lower-level matches for live runs (P1, P2, P4, and the 1,943 WTA API box scores already on disk), with the prediction-run replay as proof.
   * These change only 2025–2026 rows, so no 2020–2024 comparison can judge them. They are the framework's data-fix lane, or the owner's call.
   * Restore them before the second candidate is used live: the home-tier prior reads Stage 0, and with the lower tiers missing, ITF-based women would drift to a main-tour home tier.
4. **A player-stratified input check** beside `compare.py`'s tour-season check: the shift of each input for players whose evidence is mostly lower-level. Also a better test of "unexpected" unevenness: read a flagged tour-season against its own change of evidence mix (the dose), not against a median split. The first candidate's flag on `points_52w` (§7) shows the need.
5. **`refresh.py` after every trigger** (§10).

### 8.5 What not to do

| Don't | Why |
|---|---|
| Add lower-level matches as training rows | They leaned harmful with the price in (§1.1) |
| Train each level on its own rows | Worse at the 250s (event levels) |
| Treat raw lower-level rates as main-tour evidence | Return statistics then predict worse than ignoring them (§3.2) |
| Drop lower-level evidence | It costs every statistic, most of all for low-exposure players (§3.3), and Elo 6–7 mLL (§3.4) |
| Add "exposure" or "lower-level share" columns as the remedy | Died in the UFC work; the share as a 59th input read +0.06 [−0.10, +0.23] (unresolved, P 0.76; event levels C1). It stays a **control**, not the fix |
| Adopt a discount fitted once on old seasons | Offsets drift (§3.6); the UFC's padded-record correction lost every seed after its regime ended. A frozen offset is fine for a test (§7), not for adoption |
| Chain ITF → Challenger → tour without carrying the error | Chaining compounds error (baseball, hockey) |
| Treat ITF like Challengers | Its offsets are unmeasured until P7 |
| Down-weight lower-level opponents inside an opponent-quality average | Fix how such an opponent is scored, not how much his game counts (UFC) |

### 8.6 The order of work

1. **Done (9 Oct):** the first candidate. Its verdict: unresolved; not adopted; kept as the ITF gate (§7).
2. **Now:** the speed-panel cap.
3. **Before P7 is wired (by about 31 Oct):**
   * the second candidate, the IOS anchor (home-tier prior; centring and the men's discount as separate arms; one recipe pre-registered);
   * the walk-forward refit of the offsets on the match clock;
   * the player-stratified input check and the better "unexpected" test.
4. **The third candidate, the one-scale forms** (§8.2). It fixes the opponent-strength under-adjustment inside the main tour too, which matters for the owner's per-statistic profile whatever the ITF data do. Expect the forms' heavy shrinkage to damp it, as it damped the translation (§7).
5. **The share-signal candidate** (§8.2), pre-registered now. It is read on the sealed seasons, which spends holdout looks: the owner's call.
6. **When P7 lands:**
   * `refresh.py` on its candidate Stage 0;
   * the walk-forward ITF offsets;
   * three arms against the frozen reference, with §7's hook and gates: ITF as it stands, ITF through the layer, and the reference itself.
7. **Live hygiene, in parallel:** restore the lost feeds (before the second candidate goes live); measure the timeline refresh.
8. **Point-level profiles at the Challengers** from the P5/P6 point logs (landing 10–13 Oct). They are the raw material of the owner's thesis, and they need the same translation from the start. Later, a Challenger model with its own market test once P11 finds prices.

## 9. How each step is tested

*Suggestion.* It combines the project's guardrail, the [adoption framework](../adoption_framework/README.md) (adopted by the owner on 9 Oct 2026 as guiding principles, not rules; [decision](../../decisions/2026-10-09-adoption-framework.md)), outside practice ([05](team/05_best_practice.md) §6) and the UFC method ([06](team/06_ufc_analog.md) §3, §5):
1. **Pre-register** the arms, the primary reading and the decision rule, and hash the file before any score. State the search: §3.3's remedies were picked from 10 arms × 26 statistic-tour cells, so the second candidate pre-registers one recipe.
2. **Walk-forward everything, on the match clock.**
   * Offsets, weights and tier means for a match are fitted only on results that surely finished before it could start (the [two-time rule](../../decisions/2026-10-05-match-timing.md): in at lf + 1, read at es).
   * Every candidate that changes a cross-player quantity passes `src/eda/match_timing/probe.py` before any score: walk-forward offsets or weights, tier means, product centring, a joint-solve norm for the forms.
   * Constants tuned on pooled histories are re-tuned on 2013–2018 for an arm that changes a solve.
3. **Candidate builds against the frozen reference** (`run_chain.py --setup --candidate`, `compare.py`), both stages, scored on 2020–2024. Read the input check first.
4. **Channel by channel,** each with a placebo twin of the same size whose alignment with the players is destroyed.
5. **Share controls:** each arm against the reference plus the share variables it moves (the translation moves each A − B input by about the share difference times the offset).
6. **Declared strata:** the less-exposed player's main-tour results (< 10 vs ≥ 10 in 365 days); the share difference (≥ 0.5); qualifiers. Read touched against untouched matches: changing training rows moves untouched test rows too (the UFC's spillover lesson).
7. **A falsification stratum:** matches between two established main-tour players should barely move. A gain there is suspect.
8. **The holdout stays sealed;** in particular, no ITF offset is estimated from 2025–2026.
9. **Read the gain through the adoption framework:** shrink it, subtract the winner's luck when choosing among variants, and set it against the cost.
   * Under the framework a free, reversible change needs only to point the right way, and a change that prevents a known harm can be suggested on mechanism. The owner decides.
   * The product-centring study recommended centring on mechanism; the owner has not adopted it, and at the close it leans worse in every reading (primary −0.06 [−0.33, +0.21], P(better) 0.33).
10. **Disclose the exposure.** `compare.py`'s input check reads every season's input distribution, 2025–26 included. Those inputs are built from 2025–26 box scores: no match result and no price is read.
    * The [lean ledger](../adoption_framework/lean_ledger.md) counts looks at the sealed matches against a price, so this is not one of them.
    * It is disclosed here because those inputs reflect 2025–26 play.
    * This study adopted nothing, so it adds no ledger row.

## 10. Keeping it current

### 10.1 When to re-review

*From [04](team/04_incoming.md) §6*, in the order the events are likely to happen:

| Trigger | What changes | Re-run |
|---|---|---|
| P5 and P6 done (10–13 Oct) | Challenger point logs; no current input. Then the SofaScore timeline refresh | `incoming.py`; the timeline check (§8.4) |
| P7's ITF 2025–26 done (17–18 Oct) | ITF points of the holdout seasons: live features only | `incoming.py`; the prediction gate's view |
| **P7's ITF 2018–24 wired into a candidate Stage 0 (about 1 Nov)** | **The main event** | `refresh.py` on the candidate (below), then the ITF candidate (§8.3) |
| P8 done (November) | The rest of the ITF; a source mix by event | as above |
| P9 with Challenger speeds | Stage 2 | a stage-2 candidate |
| P11 finds lower-level prices | Lower-level market tests | a Challenger model study |
| A new frozen reference, or any Stage 0 rebuild | Everything | `refresh.py` |

### 10.2 Re-running it

```
# the whole review on a candidate Stage 0 (about 10 minutes): its own label and its own timeline are required
./python.sh src/eda/lower_level_evidence/refresh.py --label <name> \
    --stage0-dir <candidate>/data/studies/predictability_diagnostic \
    --timing <candidate>/data/studies/match_timing/timing.parquet

# with ITF box scores of 2018-2024 in it, give ITF fitting seasons (a statistic-level review only: these fixed offsets
# must not enter a model candidate scored on 2020-2024; the model candidate fits them walk-forward, §8.3)
./python.sh src/eda/lower_level_evidence/refresh.py --label <name> ... \
    --translation-args "--fit-window 2018-2021 --tune 2019-2021 --validate 2022-2024"

# the flags of the base run's own ITF preview, a construction (writes snapshots/scenario_p7_vs_reference_2026-10-08.md)
./python.sh src/eda/lower_level_evidence/refresh.py --label scenario --scenario p7

./python.sh -m pytest test/lower_level_evidence -q
```

* **What it writes.**
  * It runs `incoming.py`, `composition.py` and `translation.py` on the given Stage 0.
  * It snapshots their headline numbers (`data/studies/lower_level_evidence/snapshots/<label>.json`).
  * It writes the flags against the first run (`<label>_vs_reference_2026-10-08.md`).
* **Its safety rules:**
  * `--label` is required, and the first run's label is refused for any other Stage 0;
  * a step whose output folder exists is refused without `--force`;
  * a candidate Stage 0 must bring its own timeline.
* **The flags:**
  * **MISSING:** a section of the base run is absent: never read as "nothing moved";
  * **UNEVEN DOSE:** a share moves in some seasons more than in others;
  * **NEW LEVEL:** a level reaches 200 box-score rows in the seasons read;
  * **WINDOWS CHANGED:** the fitting window moved, so DRIFT is not read;
  * **DRIFT:** an offset or weight leaves the first run's bootstrap range;
  * **FAMILY DOSE** and **EXPOSURE:** shifts of 3 and 2 points.
* **The P7 scenario** flags women's uneven dose in all four memories, by up to 15.5 points. 2018–2024 moved in every memory (2025 too in three, 2026 in the 52-week one), and 2013–2017 in none ([flags](../../../data/studies/lower_level_evidence/snapshots/scenario_p7_vs_reference_2026-10-08.md)).
* **The team** can be re-run from [team/briefs.md](team/briefs.md), with the candidate Stage 0 in place of the frozen one.

## 11. The team

| Role | Focus | Report |
|---|---|---|
| 01 Lineage auditor | How each of the 58 inputs and stage 2 takes in lower-level matches, in the code | [01_lineage.md](team/01_lineage.md) |
| 02 Evidence-dose and exposure analyst | How much of each input's evidence is lower-level, for whom; where the model is weak against the close | [02_composition.md](team/02_composition.md) |
| 03 Level-translation statistician | Per statistic: the offset, whether opponent adjustment removes it, the exchange rate | [03_translation.md](team/03_translation.md) |
| 04 Incoming-data scout | What is coming, when, how much reaches the model; the re-review triggers | [04_incoming.md](team/04_incoming.md) |
| 05 Best-practice researcher | Sports statistics, statistics and betting practice (66 sources) | [05_best_practice.md](team/05_best_practice.md) |
| 06 UFC-analog analyst | The owner's UFC prior, its record and its lessons | [06_ufc_analog.md](team/06_ufc_analog.md) |
| 07 Red team | Re-derived the load-bearing claims, measured the opponent-strength gradient, attacked the proposal | [07_red_team.md](team/07_red_team.md) |
| 08 Candidate builder | Built and scored the first remedy on the model | [08_candidate.md](team/08_candidate.md) |
| Lead | The synthesis, the proposal, this dossier, `refresh.py` | this file |

**Why this structure.**
* **The parallel phase.** The question splits into independent parts: the code (01), the data's composition (02), the statistics of translation (03), the incoming data (04), outside practice (05) and the owner's own precedent (06). Running them side by side on the same frozen tables let each check the others: 01's measured form shift is what 03's estimator corrects, 02's strata are where 08 reads its result, and 04's triggers are what `refresh.py` answers.
* **The checking phase.** The two later roles test the synthesis rather than add to it.
  * The red team found 5 errors that had to be fixed, among them a leak in the ITF plan and a `refresh.py` bug that could overwrite the first run's evidence.
  * It also found the one new measurement that changed the proposal (§1.2).

## Decisions for the owner

1. **The first remedy** (translating the 18 aggregates). The pre-registered verdict is unresolved and not on mechanism. *Suggestion:* do not adopt it now, and keep its machinery as the ITF gate. If you set aside the `points_52w` flag as a threshold artifact, the mechanism branch would otherwise pass. But the share control says the translation adds nothing two share columns would not.
2. **How ITF box scores enter the model** (§8.3): only through the level-aware layer, with offsets fitted walk-forward. P7 is extended back to 2014 if SofaScore serves it; that is collection, already approved.
3. **The speed-panel cap** (§8.4, point 1). It changes only 2026 rows, so it rests on data evidence, not a 2020–2024 score.
4. **Restoring the feeds lost in June 2026:** a candidate like new data (today's rule), or a data fix judged on data evidence with the replay as proof?
5. **The timeline refresh after the SofaScore runs.** The match-clock decision makes it routine; the frozen-reference gate does not see it. Measure it first, then decide whether it is a candidate.
6. **The second and third candidates** (the IOS anchor; the one-scale forms) will be built and scored as the order of work says. Adopting either is the owner's call.
7. **The share-signal candidate:** whether to spend holdout looks (the sealed seasons) on it, since 2020–2024 suggested it.
8. **Cleanup** (CLAUDE.md asks first):
   * the candidate sandbox, `C:/Users/zerom/tnr_lle` (18.9 GB), removed by `run_chain.py --cleanup`;
   * the superseded hand-made dry run, `data/studies/lower_level_evidence/snapshots/dryrun_p7_scenario_vs_reference_2026-10-08.md`.

   Also, the 8 arms' `fits/` folders (about 18 MB each, 144 MB in all) are not git-ignored. Like `model_rebuild/fits/`, they are your call at commit time.

## What it does not show

* **Match-level effects beyond the first candidate.** The translation, tier-prior and discount gains of §3 are statistic-level likelihoods. Only §7 measures the model, and it does so with:
  * seeds 0–3 (the decided application averages 16);
  * one placebo draw;
  * fixed same-season offsets;
  * untranslated opponent norms;
  * seasons that many studies have read.
* **The 17 forms are not modelled directly** in §3.2: the raw-rate estimator is their stand-in.
* **A simplified IOS.** Role 03's copy pools surfaces, solves weekly and has no incremental step, so the decided IOS may behave differently at the margins. `ratings_iid`'s prior is not mirrored.
* **ITF:** every ITF-level conclusion waits for P7, including whether the additive rating model holds there at all.
* **Lower-level markets:** no Challenger or ITF price before September 2025 is held, so nothing here measures an edge at those levels.
* **Closing prices only.** The market readings are against the books' average close (Pinnacle's β from the event-levels study), 2020–2024: the seasons that chose the inputs. Nothing is measured against an early price or a bet.
* **Many strata.** §4's readings are descriptive, about 2–4 standard errors each, among many strata, with no correction for the number of looks.

**Open risks** ([07](team/07_red_team.md)):
* **The first test came out as predicted:** unresolved at the close, no more than the share signal. That is not a refutation of the layer, whose case is the ITF dose.
* **Over-correction (an offset too large, a tier mean too harsh) pushes toward the market's error.**
* **The forms keep their schedule bias** inside the main tour after any level fix, until the one-scale candidate.
* **P7 may trip the input check even through the layer** (the volume step).
* **Live women's histories have no lower levels since June 2026,** so any level-aware remedy does nothing for them, and the tier prior misfires, until the feeds are restored.
* **Stage 2 is itself under review.** The [lean ledger](../adoption_framework/lean_ledger.md), row 3, shows it leaning worse outside the seasons that chose it: men 2020–24, −0.26 [−0.59, +0.06], P(better) 0.05, seeds paired; + = the adjustment helps.

## Files

| What | Where |
|---|---|
| This dossier and the team's reports | `docs/studies/lower_level_evidence/README.md`, `team/` (briefs, 01–08) |
| Shared definitions (paths, level buckets, the holdout guard, filtered reads) | `src/eda/lower_level_evidence/common.py` |
| The code-level checks (01) | `src/eda/lower_level_evidence/lineage_checks.py` → `data/studies/lower_level_evidence/lineage/` |
| Evidence dose and exposure (02) | `composition.py` → `…/composition/<label>/` |
| Translation, exchange rates, tier priors (03) | `translation.py` → `…/translation/<label>/` |
| Incoming data (04) | `incoming.py` → `…/incoming/` |
| The candidate (08) | `translate_hooks.py` (the hook), `offsets.py`, `sandbox_patch.py`, `candidate_arms.py`, `g4_linearity.py`, `candidate_fits.py` (the 59/60-input runner), `candidate_pairs.py` (the scorer) → `…/candidates/` (pre-registration and its hashes, offsets, `checks/`, one folder per arm, `results/`) |
| The refresh | `refresh.py` → `…/snapshots/` |
| Tests | `test/lower_level_evidence/` (`./python.sh -m pytest test/lower_level_evidence -q`) |
