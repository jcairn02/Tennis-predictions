# Round 0 ideas: body and schedule

6 October 2026 · Brainstormer "body and schedule" · Research evidence, not a decision.

This is a list of ideas only. Nothing here relates a feature to a match outcome or to the odds, and no 2025–2026 row was read. **Observed** marks numbers computed for this list: prevalence counts and model arithmetic only. **Inferred** marks reasoning. **Suggestion** marks proposals. The "expected effect" sizes are priors from the power arithmetic below, not measurements. Every effect size is a gain in milli-log-loss (mLL), where higher is better. Background that I recalled but could not verify (web search is not allowed in round 0) is marked **recalled** and left for the literature scout.

Scripts: `src/eda/feature_interactions/round0/body/` (`schemas.py`, `categories.py`, `counts.py`, `counts2.py`, `counts3.py`, `composition.py`). Outputs: `data/studies/feature_interactions/round0/body/` (`counts*.json`, `composition.json`). Run each with `./python.sh`. None of them reads the current match's result. Earlier matches' results are read only to tell who retired or gave a walkover in a player's previous match.

## 1. Conventions

**Notation.** For match m and player X ∈ {A, B}:

* **t**: the match clock's best-estimate day (`obs` in `data/studies/match_timing/timing.parquet`). **Observed:** 98.8% of men's and 93.3% of women's 2013–2021 main-tour player-matches have exact days for both the match and the player's previous match.
* **j**: X's earlier *played* matches (completed or retired) at every level: ITF, Challenger, qualifying and team ties. Δ_j = t − t_j days, where 0 means earlier the same day. **On-site** means the same `tournament_id`; qualifying shares the main draw's id (checked for Doha, Indian Wells and Wimbledon 2019).
* **L_j**: the load of match j in minutes, from Stage 0 `minutes` where present. Where minutes are missing, points played (box score `tpw_d`) × seconds per point; failing that, games × minutes per game. Both constants are set per tour and surface and frozen on 2010–2018. **Observed:** main-tour minutes cover 83% of men's matches in 2013–2015 and 99% from 2016. Women's minutes cover 0.2% in 2013–2015 and 98–99% from 2016.
* **Fat_X(τ)** = log(1 + Σ_j L_j·exp(−Δ_j/τ)), with a short τ (fatigue). **Fit_X(τ1)** is the same sum with a long τ1 (match fitness). (x)+ = max(x, 0).
* **p**: the de-vigged closing probability that A wins, so `odds_logit` = logit p.
* **Swap rules** (the brief's symmetry algebra). A ↔ B negates a *diff*, leaves a *context* unchanged, exchanges a *pair*, and maps p → 1 − p. A "W" feature enters as f(A) − f(B), kind diff. Every formula below states its swap check.

**Power arithmetic (inferred).** Suppose a logit shift Δ is correct for a match won by A with probability p. Adding it to a forecast that lacks it gains about ½·p(1 − p)·Δ² nats.

* With p(1 − p) ≈ 0.2, Δ = 0.1, 0.2 and 0.3 are worth about 1, 4 and 9 mLL per affected match. An estimated Δ keeps less.
* So 0.3 mLL overall needs roughly Δ ≈ 0.2 on 7–8% of matches, or Δ ≈ 0.1 on about 30%.
* For scale, the 54-input predecessor's edge over the recalibrated close is +1.30 mLL (both tours, 2022–2026).

**The scoring structure converts fatigue into match odds** (observed: `composition.py`, Stage 2's iid model only, no match data):

| Serve-point win probabilities (A, B) | Best of | P(A wins) | S_A = d logit P / d p_A | Expected points |
|---|---|---|---|---|
| 0.64, 0.64 | 3 / 5 | 0.50 / 0.50 | 19.9 / 24.9 | 165 / 271 |
| 0.70, 0.70 (two servers) | 3 / 5 | 0.50 / 0.50 | 18.6 / 23.3 | 166 / 273 |
| 0.58, 0.58 (two returners) | 3 / 5 | 0.50 / 0.50 | 20.9 / 26.2 | 164 / 271 |
| 0.70, 0.60 (A favourite) | 3 / 5 | 0.89 / 0.94 | 22.4 / 30.5 | 146 / 226 |

* **Observed.** One point less of serve-point probability (0.01) moves the match logit by about −0.20 in best of 3 and −0.25 in best of 5 in an even match.
* **Observed.** The hold curve flattens for big servers: its slope d hold/dp is 2.09 at p = 0.60, 1.75 at 0.64, 1.19 at 0.70 and 0.76 at 0.75.
* **Inferred.** Even so, a *uniform* decrement moves the match logit about equally for servers and returners: servers lose fewer holds, but each break counts more.
* **Inferred.** Best of five multiplies a uniform decrement's logit effect by 1.25–1.36. If the decrement grows with points played (1.55–1.65 times as many points), the factor is about 2.

**Prevalence on the main tour, 2013–2021, men / women** (observed: `counts.py`, `counts2.py`, `counts3.py`). These counts cover all main-draw matches played, with or without odds: 22,037 men's and 20,937 women's. The odds-linked model population is smaller, about 19.3k and 20.6k; the men's 2018 season has no odds.

| Situation | Men | Women |
|---|---|---|
| Player-match is the player's first at this event | 43.6% | 43.2% |
| Rest of 0 days (second match the same day) / 1 day / 2 days, on best-estimate days | 0.39% / 26.5% / 26.0% | 0.73% / 23.9% / 26.0% |
| Matches where both played within 14 days and their rest differs by 3+ days (exact days) | 30% of 17,692 | 23% of 15,026 |
| Previous match ≥ 180 min (men) / ≥ 150 min (women), of those with a known duration | 5.1% | 7.7% |
| Player retired in their previous match / and plays again within 14 days | 1.50% / 345 | 1.55% / 386 |
| First match within 4 days of a semi-final or final at the previous event (final only) | 1,412 (748) | 899 (477) |
| First match within 7 days of an event on another continent | 1,103 | 821 |
| Gap of 42+ days outside December–January | 0.89% | 1.0% |
| Played at 4+ events in the 42 days before (this event counts once a round has been played here) | 51% | 41% |
| The two players' on-site match counts differ / from the round of 16 on | 41% / 4,160 | 34% / 2,559 |
| Exactly one player's previous on-site match went to a deciding set / that player had ≤ 1 day of rest | 4,085 / 2,171 | 4,318 / 1,920 |
| Either player played a team tie in the 14 days before | 1,475 | 1,153 |
| Playing at home | 13.5% | 11.2% |
| Entry: qualifier / wild card / lucky loser / protected (PR men, SR women) | 10.7 / 5.8 / 1.8 / 0.66% | 11.3 / 5.9 / 1.6 / 0.08% |
| Age ≤ 23 / age ≥ 30 | 21.5% / 31.2% | 37.1% / 14.5% |
| 250/500 matches within 8 days of a Slam with a top-20 player | 305 | 592 |
| Matches at venues above about 1,000 m (Bogotá, Quito, Gstaad, Guadalajara) | 405 | 387 |
| Median season matches already played before an October match | 53 | 51 |

**Observed.** Women's `indoor` is missing on every Stage 0 row. Retirements end 26,880 of the 787,039 matches of 2010–2024 at all levels (3.4%).

## 2. What earlier studies already say about this family

* **Load is mostly survival, and one of the few rows the market lacked.** Given Elo, more sets in the last 14 days wins *more* often (Stage 4: "a player still in a draw has played more"). Given the market, the load rows were among the handful above the family-wide line: men's sets over 7 days +0.30 [+0.05, +0.54] and minutes over 7 days +0.18. These are historical rows from before the repair ([stage4.md](../../predictability_diagnostic/stage4.md) §3).
* **Fatigue traits are mostly luck.** The within-match late decline is not a trait for men, and the "grinder" contrast measures margin of victory ([ufc_ideas stageC](../../ufc_ideas/stageC.md) §3).
* **Rest, inactivity and retirement have not been tested on full histories.** They tied against the market as additive inputs: men −0.07 [−0.22, +0.08], women −0.24 [−0.49, +0.01] ([predictive frontier](../../predictive_frontier/README.md), "recovery context"). That build kept only main-tour matches with provider dates, so every Challenger, ITF and qualifying match was missing ("missing matches are not verified rest"). The match clock now dates all 872,704 matches.
* **The market absorbs surface-switch main effects.** The surface-switch pieces tie at the close ([surface Elo pieces](../../surface_elo_pieces/README.md)).
* **Load, age and surface familiarity are TabPFN's second-largest input group.** A spline GAM on the odds plus that group gains +1.00 [+0.22, +1.79] for women and +0.37 [−0.25, +0.99] for men over the recalibrated odds ([TabPFN-Thinking](../../tabpfn_thinking/README.md)). **Inferred:** the women's prices under-use this family, at least additively.
* **Several directions here are already registered** in the frontier research register but untested in that form ([research.md](../../predictive_frontier/research.md)): A07 (current-event versus pre-event load), A09 (load × recovery × age), A14 (completion risk), C01–C04 (weather, acclimatisation, travel, altitude), C07 (real rest hours) and C08 (incentives). Each idea below names its overlap.

## 3. The ideas

Families: **A.** Load and recovery (BOD-01 to BOD-11). **B.** Rust, injury and completion (BOD-12, BOD-13). **C.** Calendar, travel and conditions (BOD-14 to BOD-24). **D.** Effort and motivation (BOD-25, BOD-26). **E.** Age and the body over the years (BOD-27 to BOD-30).

BOD-02's Fat_X is the shared building block. Build it once on the match clock; ideas 03–08, 10–12, 24 and 29 reuse it.

Every kill test is run on 2013–2021: constants are tuned on 2013–2018 and checked on 2019–2021, against the closing price plus the current best model's out-of-sample forecast. "Adds nothing" means the 95% interval of the gain spans 0 (a tie). For an interaction, "beyond its main effects" means beyond its component terms entered separately.

### A. Load and recovery

#### BOD-01 · Load split: on-site survival against carried-over debt

| Field | Content |
|---|---|
| ID, name | BOD-01 · Load split: on-site survival against carried-over debt |
| Mechanism | `sets_14d`, the model's only load input, adds two different things. **Rounds already played at this event** (qualifying included) were won in today's conditions: they show survival, form and acclimatisation, and the market saw every one. **Load carried in from earlier events** (often another country, surface and time zone, sometimes a finals weekend) is debt to be recovered. Within the event, minutes beyond what that many rounds usually take are struggle plus fatigue. One A − B sum forces one weight on all three |
| Why the price might miss it | The market sees results and scores, not when last week's load ended or how many minutes it took. Load is one of the few families with market-orthogonal hints (§2), and splitting it is the cheapest way to find which part carries them. Registered as A07, untested |
| Type | W |
| Formula | **On_X** = log(1 + on-site matches before this one). **Ex_X** = log(1 + Σ_on-site L_j) − log(1 + E[Σ_on-site L_j given n_on, tour, surface, best_of]), with the expectation frozen on 2010–2018. **Off_X** = log(1 + Σ_{off-site, Δ_j ≤ 21} L_j·exp(−Δ_j/τ)), τ ∈ {3, 7} days. Three diffs: On_A − On_B, Ex_A − Ex_B, Off_A − Off_B. Swap: each is f(A) − f(B) and negates ✓ |
| Data | Stage 0 matches (`tournament_id`, `round`, `minutes`, `status`, `best_of`, `surface`) and players (`sets_won_d`, `games_won_d`, `tpw_d`) at every level; `timing.parquet` `obs`. Safe by construction (own matches) |
| Why the model cannot already do it | `sets_14d` is one A − B box-car sum. It counts sets, not minutes, between *event start dates*. None of the 58 inputs separates where or when the load was played |
| Expected effect | Off negative and Ex negative. On is small and positive (acclimatisation) once Off and Ex are held. Largest at a player's first match of an event (43% of player-matches) and after deep runs. Both tours; possibly women more (thinner prices, §2). 0.1–0.4 mLL |
| Kill test | The three columns add nothing beyond the price and the model forecast; or their coefficients are equal within error, so the split adds nothing beyond the sum |

#### BOD-02 · Duration × recency: a fitness–fatigue kernel on the match clock

| Field | Content |
|---|---|
| ID, name | BOD-02 · Duration × recency: a fitness–fatigue kernel on the match clock |
| Mechanism | A match's cost is its duration multiplied by how recently it ended: four hours yesterday is not four hours nine days ago. The impulse–response (Banister) model writes performance as fitness (slow decay, weeks) minus fatigue (fast decay, days) (recalled). The match clock supplies real days, which no earlier load input used. A second match on the same day after rain is the Δ = 0 limit. A retired or walkover opponent shows up as few minutes |
| Why the price might miss it | Bettors see "played a five-setter". They rarely price exactly one day of rest against three, the cumulative minutes of the week, or minutes saved by an opponent's retirement. The earlier rest test mismeasured rest on a truncated history (§2) |
| Type | W (within-player product of duration and recency) |
| Formula | Fat_X(τ2) with τ2 ∈ {1.5, 3, 5} days, and Fit_X(τ1) with τ1 ∈ {21, 42}, tuned on 2013–2018. Diffs: Fat_A − Fat_B and Fit_A − Fit_B, so the model weighs "form" = Fit − k·Fat itself. Swap ✓ |
| Data | As BOD-01. Lower-level history has windows (ITF median 9 days), which add noise to Δ only for players arriving from ITF events. Rest in *hours* (late finishes, night sessions) would need start times. The Australian Open archive has actual start, duration and session; the Slam feeds have point timestamps from 2019. Coverage is partial (frontier C07); cartographer to check |
| Why the model cannot already do it | No day-level timing, no minutes, no decay |
| Expected effect | Fat negative. Fit positive (match practice against layoff). Concentrated where rest is short and unequal: rest differs by 3+ days in 30% (men) and 23% (women) of matches where both played within 14 days. 0.1–0.5 mLL. Replication caveat: the 12-day Masters format of 2023+ changes the rest distribution |
| Kill test | For every τ2 in the grid, Fat adds nothing beyond `sets_14d`, the price and the model forecast |

#### BOD-03 · Age × recovery debt

| Field | Content |
|---|---|
| ID, name | BOD-03 · Age × recovery debt |
| Mechanism | Recovery slows with age: a 33-year-old clears a long match or a finals weekend more slowly than a 22-year-old. The same load is a bigger debt |
| Why the price might miss it | Age is priced as a level ("veteran"). Nobody quotes the product of age and yesterday's minutes |
| Type | W (+ S format variant) |
| Formula | Debt_X = Fat_X(τ2(age_X)), with τ2(age) = τ0·(1 + β·(age_X − 26)+) and β ∈ {0, 0.03, 0.06} per year. Simpler form: Fat_X·(age_X − 26)+. Diff Debt_A − Debt_B. Format variant: × (1 + γ·1[best_of = 5]), a context × diff product, antisymmetric. Swap ✓ |
| Data | Stage 0 `age` (97.5% of rows) and the loads. Safe |
| Why the model cannot already do it | This is the brief's own example. Age and load reach the model only as A − B differences, so age_A × load_A cannot be formed |
| Expected effect | Negative for older, recently loaded players. Men (31% of men's player-matches are at age 30+, 14.5% of women's); Slams' second weeks; back-to-back weeks. 0.05–0.3 mLL |
| Kill test | The product adds nothing beyond its main effects (the Fat and age differences) and the model forecast; or the age gradient changes sign between 2013–2018 and 2019–2021 |

#### BOD-04 · Fatigue through the point model: format and closeness

| Field | Content |
|---|---|
| ID, name | BOD-04 · Fatigue composed through the point → game → set → match chain |
| Mechanism | A fatigue state lowers serve- and return-point probabilities by some δ; the scoring structure then fixes the match effect. §1: one point of serve probability is worth −0.20 in the match logit in best of 3 and −0.25 in best of 5 for an even match, and −0.22 / −0.30 for a 0.70-vs-0.60 favourite. Best-of-five matches last about 1.55–1.65 times as many points, so a decrement that grows within the match roughly doubles there. A surface variant lets the decrement differ on clay (long rallies) |
| Why the price might miss it | A price adjusts for fatigue, if at all, by a rough rule. The structural amplification by format and expected length is a calculation. TabPFN's edge is largest at the Grand Slams (+2.75 men, 2022–2026), where best of five is played |
| Type | C (composition) with S character |
| Formula | δ_X = κ·Fat_X; variant: + λ per 100 points played within the match. Δ = logit P_iid(p_A − δ_A + η·δ_B, p_B − δ_B + η·δ_A; format, deciding-set rule) − logit P_iid(p_A, p_B; …). Here p_A, p_B are the Stage 3 serve-point expectations behind `ratings_iid`, η is the share of fatigue that shows on return, and the first server is averaged. κ, η and λ are tuned on 2013–2018. Swap: P(B wins) = 1 − P(A wins), so Δ negates ✓ |
| Data | `stage3_ratings.parquet` (`p_serve_a`, `p_serve_b`), `stage2_iid.py` (`match_win`, `deciding_set_rule`), Fat from BOD-02. Safe |
| Why the model cannot already do it | `best_of` is context and `ratings_iid` is one diff. The effect is format × both serve levels × each player's fatigue: a three-way product that includes levels the differences hide |
| Expected effect | Negative for the more tired player; 1.25–2 times larger in best of five; men's Slams. 0.1–0.3 mLL |
| Kill test | The composed column adds nothing beyond the plain Fat difference; or the best-of-five slope is not larger than the best-of-three slope (the modulation is unsupported) |

#### BOD-05 · Both tired against one tired

| Field | Content |
|---|---|
| ID, name | BOD-05 · Both tired against one tired |
| Mechanism | When both players are depleted (a Slam's second week, or both off finals weekends), the strength gap may compress (more errors and breaks, more variance) or widen (the deeper athlete prevails). Differences make "both exhausted" and "both fresh" identical |
| Why the price might miss it | Prices mark down the tired player. A match between two exhausted players is not a standard adjustment |
| Type | S (+ pair) |
| Formula | z1 = (Fat_A + Fat_B − c)·odds_logit: a symmetric sum × an antisymmetric logit, so antisymmetric ✓. z2 = (Fat_A − Fat_B)/(Fat_A + Fat_B + c), antisymmetric ✓. Also the pair (Fat_A, Fat_B), exchanged on swap |
| Data | As BOD-02 |
| Why the model cannot already do it | No fatigue level; only a load difference |
| Expected effect | Prior: z1 negative (the price over-confident when both are tired), held with low confidence. Men's Slam second weeks; women's consecutive weeks. 0.05–0.2 mLL |
| Kill test | z1 adds nothing, and the price's calibration slope does not differ between the top and bottom quintiles of Fat_A + Fat_B (bins declared in advance) |

#### BOD-06 · Which skills fatigue erodes: own style × own fatigue

| Field | Content |
|---|---|
| ID, name | BOD-06 · Own style × own fatigue |
| Mechanism | Fatigue may take the legs before the first strike, or the serve's leg drive before rally tolerance. A server whose edge is free points may lose less from tired legs than a defender whose edge is retrieval; the reverse holds if fatigue mostly cuts first-serve speed and percentage. BOD-04 shows the scoring structure is nearly neutral to style under a uniform δ, so any style effect must sit in the decrement itself, statistic by statistic |
| Why the price might miss it | The market prices "tired", if at all, as one adjustment per player |
| Type | W (C at statistic level) |
| Formula | Sty_X = standardised (serve rating − return rating) (Stage 3), or the IOS offence-minus-defence share. Feature: Fat_A·Sty_A − Fat_B·Sty_B (diff). Statistic-level variant: shift each player's profile with fatigue (first_in −θ1·Fat, df +θ2·Fat, first_won −θ3·Fat, rpw_second −θ4·Fat), then recompute the `prod_*` matchups and the point model. Swap ✓ |
| Data | Stage 3 ratings (safe). Per-player IOS, A and B separately (`data/studies/surface_ios/surface_features.parquet`), which must be on the leak-proof clock; cartographer to confirm |
| Why the model cannot already do it | Style and load arrive only as differences |
| Expected effect | The sign is the hypothesis. Concentrated in tired players with extreme styles. 0.05–0.2 mLL |
| Kill test | The fatigue slope does not differ across style terciles: the product adds nothing beyond its main effects |

#### BOD-07 · The opponent who exploits fatigue: long rallies and second-serve returns × the other's fatigue

| Field | Content |
|---|---|
| ID, name | BOD-07 · Opponent's exploiting skill × the other player's fatigue |
| Mechanism | How much of B's fatigue shows depends on A's game. A long-rally player makes a tired opponent run. A strong second-serve returner punishes a tired serve, whose second serves get slower and shorter. A big server who ends points in three shots lets a tired opponent rest. "One tired" against a grinder is not "one tired" against a server |
| Why the price might miss it | It is a cross-player product of one player's style and the other's state, and no pricing rule of thumb carries it |
| Type | X |
| Formula | X1 = R_A·Fat_B − R_B·Fat_A, where R is the shrunk, opponent-adjusted seconds per point (minutes × 60 / points played) relative to the tour-surface norm. X2 = Ret2_A·Fat_B − Ret2_B·Fat_A, where Ret2 is second-serve return strength (shrunk return points won against second serves, or the IOS defence on `second_won`). Swap: R_B·Fat_A − R_A·Fat_B = −X1 ✓; X2 likewise ✓ |
| Data | Stage 0 minutes and `tpw_d` (women: minutes from 2016, box scores with holes before 2019). As a check, rally counts from the Slam feeds and the Match Charting Project (partial). Pace and return from own matches with opponents' pre-match values are safe; the IOS-based Ret2 needs leak-proof IOS |
| Why the model cannot already do it | The `prod_*` columns cross offence with defence, never style with physical state |
| Expected effect | Positive for the grinder or strong returner facing a tired opponent; clay; best of five. 0.05–0.2 mLL |
| Kill test | X1 and X2 add nothing beyond their main effects; or opponent-adjusted seconds per point has split-half reliability below 0.3 (not a trait) |

#### BOD-08 · The favourite's hidden fatigue

| Field | Content |
|---|---|
| ID, name | BOD-08 · Asymmetric pricing of the favourite's and the underdog's fatigue |
| Mechanism | Prices anchor on names. When the favourite carries the load, backers who buy reputation may keep the price shorter than the state warrants. When the underdog carries it, the price moves freely |
| Why the price might miss it | This is a behavioural hypothesis about the market's own adjustment |
| Type | M |
| Formula | s = sign(odds_logit) and g = Fat_A − Fat_B. Then u = s·g, the favourite's fatigue minus the underdog's, which is symmetric. z1 = s·max(u, 0) (favourite more tired) and z2 = −s·max(−u, 0) (underdog more tired), so z1 + z2 = g. Swap: s and g change sign and u does not, so z1 and z2 negate ✓. A plain fatigue effect has β1 = β2; the hypothesis is \|β1\| > \|β2\| |
| Data | Fat from BOD-02 and the price |
| Why the model cannot already do it | It could form a crude version from `odds_logit` and `sets_14d`, but not with a fatigue measure it lacks. Its adjustment is also about 96% additive |
| Expected effect | β1 more negative than β2; heavier favourites. 0.05–0.15 mLL |
| Kill test | β1 = β2 within error |

#### BOD-09 · The previous-round scare: fatigue or over-reading, split by rest

| Field | Content |
|---|---|
| ID, name | BOD-09 · Previous-round scare × rest |
| Mechanism | A player who needed a deciding set in the previous round, or saved match points, carries two signals: real fatigue if the next match comes a day later, and an impression of poor form. Per-match performance is mostly noise (Stage 3), so a market that reads the scare as decline over-reacts. With one day of rest the fatigue part dominates; with two or more only the over-reading remains. The residual's sign should flip with rest |
| Why the price might miss it | The narrative ("struggled through") moves money. The rest structure that separates fatigue from noise is not part of the narrative |
| Type | M / W |
| Formula | Scare_X = 1[X's previous on-site match reached a deciding set]. Variants: closeness 1 − abs(2·games share − 1), or points won below X's pre-match expectation. Two diffs: Scare_A·1[rest_A ≤ 1] − Scare_B·1[rest_B ≤ 1] and Scare_A·1[rest_A ≥ 2] − Scare_B·1[rest_B ≥ 2]. Swap ✓ |
| Data | Stage 0 scores (`sets_won_d`, `best_of`), statuses and the match clock. Safe. **Observed:** 4,085 men's and 4,318 women's 2013–2021 matches have exactly one such player; that player had ≤ 1 day of rest in 2,171 and 1,920 |
| Why the model cannot already do it | The two-week profile averages the scare's statistics into form. There is no closeness or rest input, and the sign must depend on rest |
| Expected effect | Negative with ≤ 1 day of rest; positive with ≥ 2 (the over-reaction undone). Both tours. 0.05–0.3 mLL |
| Kill test | The two coefficients do not differ: the same sign, or both intervals span 0 |

#### BOD-10 · Acute-to-chronic load spike

| Field | Content |
|---|---|
| ID, name | BOD-10 · Acute:chronic workload ratio |
| Mechanism | Injury and performance risk rise when this week's load far exceeds what the player is used to. This is sports science's acute:chronic workload ratio (recalled; contested for statistical artefacts). A lower-ranked qualifier on a deep run spikes, and so does a returnee playing three weeks in a row; a top player used to heavy weeks does not |
| Why the price might miss it | Habitual load is invisible on a score sheet |
| Type | W |
| Formula | R_X = (L7_X + c)/(L28_X/4 + c), with minutes in the last 7 and 28 days (or exponentially weighted). f(R) = log R or (R − 1.5)+. Diff f(R_A) − f(R_B), with an age-product variant. Also an input to BOD-12's hazard. Swap ✓ |
| Data | As BOD-02. **Observed:** 28-day minutes are complete for 86% of men's and 55% of women's 2013–2021 player-matches; otherwise points or games fall back |
| Why the model cannot already do it | One 14-day window, no ratio |
| Expected effect | Negative above about 1.5; both tours. 0.05–0.15 mLL |
| Kill test | The ratio adds nothing beyond Fit and Fat (BOD-02) |

#### BOD-11 · Recovery as a player trait

| Field | Content |
|---|---|
| ID, name | BOD-11 · Player-specific sensitivity to short rest |
| Mechanism | Conditioning and physique differ, so some players recover better. A heavily shrunk, player-specific sensitivity could scale BOD-02's fatigue |
| Why the price might miss it | It is player-specific and rarely discussed except for a few stars |
| Type | U / W |
| Formula | Trait_X = X's shrunk mean of points won above the pre-match expectation in matches with Fat above the tour's 80th percentile, minus the same in matches below the median. K follows Stage 3's empirical-Bayes method on 2010–2018. Feature: Trait_A·Fat_A − Trait_B·Fat_B. Swap ✓ |
| Data | Stage 0 box scores; Stage 3 expectations. Safe |
| Why the model cannot already do it | No such trait exists among the inputs |
| Expected effect | Small. The prior is failure: Stage C found the within-match late decline was no trait for men |
| Kill test | Split-half reliability is not above Stage C's pure-luck replay's; this is checked before any outcome screen |

### B. Rust, injury and completion

#### BOD-12 · Retirement hazard × price: completion risk the contract may not price

| Field | Content |
|---|---|
| ID, name | BOD-12 · Retirement hazard × price |
| Mechanism | The label counts a retirement as the opponent's win. Some bookmakers void a bet when a player retires. The project's source register records the Betfair Exchange rule: a retirement before the first set is completed is void ([source register](../../../research/tennis-data-audit/source-register.md), rules audited 2026-09-10; not re-verified here). The legacy archive lists other books with void rules (unapproved, unverified). A price on such a contract prices *winning a completed match*; the label is *advancing*. Retirement risk is concentrated: recent retirements or withdrawals, age, load spikes, returns from layoff, heat, best of five |
| Why the price might miss it | (1) The contract mismatch. (2) The effect is nonlinear in the price. With P(A advances) = (1 − h_A − h_B)·p + h_B, the logit shift is ≈ h_B/p − h_A/(1 − p). A 5% hazard costs a 0.90 favourite about −0.5 in logit and a 0.10 underdog about −0.06. A linear "recent retirement" input, as the frontier recovery family tested (a tie), cannot express this. Registered as A14 and C10 |
| Type | M (with a W hazard) |
| Formula | h_X comes from a small logistic model of "X retires in this match", fitted walk-forward on earlier seasons only. Its inputs: X retired or gave a walkover in the last 28 days (decayed); retirements per match over 52 weeks (shrunk); age; Fat_X; R_X (BOD-10); the layoff (BOD-13); `best_of`; month. Feature: z = h_B/p − h_A/(1 − p), or exactly logit P_adv − logit p. Swap: h_A ↔ h_B and p → 1 − p give −z ✓ |
| Data | Stage 0 `status` and `status_detail` (retired, walkover, defaulted; the advancing player won) on the players' earlier matches, plus ages and loads. Player histories are safe. The hazard fit pools other players' finished seasons, walk-forward by season with no same-season pooling. Prevalence in §1 |
| Why the model cannot already do it | It has no retirement or status input. The shift scales with 1/(1 − p): a price × hazard interaction |
| Expected effect | Negative for the high-hazard player, mostly when that player is the favourite. Slams (longer matches) and hot events; both tours. 0.05–0.3 mLL |
| Kill test | (a) Out of sample, the hazard model does not beat the base rate on the retirement label (log loss); (b) z adds nothing beyond the model forecast; (c) the gain is no larger when the high-hazard player is the favourite |

#### BOD-13 · Unplanned layoff × age × how the layoff began

| Field | Content |
|---|---|
| ID, name | BOD-13 · Rust after an unplanned layoff |
| Mechanism | A mid-season gap of six weeks or more usually means injury; the off-season gap is planned. Returning players are rusty for a few matches. Older returners fare worse, and so do those whose last match was a retirement or a walkover given. Rankings lag (protected rankings), and Elo barely moves while a player is away |
| Why the price might miss it | The market sees the return and the name. How much rust is left after one or two matches, and the extra risk for the old and the injured, are judgement calls |
| Type | W |
| Formula | U_X = log(1 + (gap_X − E[gap given calendar week, ranking band])+), with E frozen on 2010–2018 (the off-season gap is expected). Rust_X = U_X·exp(−n_X/ν)·(1 + ρ·(age_X − 28)+ + η·1[pre-gap match ended in X's retirement or walkover given] + ψ·1[entry PR or SR]), where n_X = matches since the return and ν ∈ {1, 2, 4}. Diff Rust_A − Rust_B. Swap ✓ |
| Data | Stage 0 at every level (lower-level matches end many apparent layoffs that the frontier's history counted as rest) and the entry codes. Safe |
| Why the model cannot already do it | It has only surface layoffs (days since the last match on *this* surface, as pairs), which cannot tell "played elsewhere" from "did not play". There is no matches-since-return count, and age is only a difference |
| Expected effect | Negative for the returner, larger with age and an injury start, fading over 1–3 matches. Low prevalence (§1). 0.02–0.15 mLL |
| Kill test | No gain; or no decay with matches since the return |

### C. Calendar, travel and conditions

#### BOD-14 · Last week's deep run × a short gap × travel

| Field | Content |
|---|---|
| ID, name | BOD-14 · The Sunday finalist's Tuesday |
| Mechanism | Last week's semi-finalist or finalist often starts this week's event one to three days later, in another country and sometimes on another surface. They carry physical and emotional debt and have had no practice in the new conditions. The market sees a player in form: a title, ranking points, an Elo jump. Variant: the previous event was a Slam where X reached the quarter-finals (best of five for men; a post-Slam let-down) |
| Why the price might miss it | Recent results are visible and probably over-weighted; the squeeze in the calendar is not |
| Type | W (three-way within a player) |
| Formula | Run_X = (matches won at X's previous event, or 1[SF or F]) × exp(−gap_X/τ) × (1 + μ·Trav_X). gap_X = days from X's last match there to this match; Trav_X = 1[continent change] or abs(ΔZ_X)/12 (BOD-15); τ ∈ {2, 4}. Diff Run_A − Run_B. Swap ✓ |
| Data | Stage 0 rounds and ids; the match clock; `stage4_event_country.csv` (countries only) with a continent map. Safe. Prevalence in §1: 1,412 and 899 such player-matches; 1,103 and 821 continent changes within 7 days |
| Why the model cannot already do it | `sets_14d` counts last week's sets as plain load (positive overall, because load means survival), from event start dates, with no travel |
| Expected effect | Negative in the first match of the new event; larger with travel and a shorter gap. Both tours. 0.05–0.2 mLL |
| Kill test | No gain; or no dose–response (the effect does not shrink with longer gaps) |

#### BOD-15 · Jet lag: time zones × days since the last match away × direction

| Field | Content |
|---|---|
| ID, name | BOD-15 · Jet lag |
| Mechanism | Crossing five or more time zones disturbs sleep and timing for days. Eastward travel is usually harder, and adaptation takes roughly a day per zone (recalled). The last match at the previous venue bounds when the player could leave: one who lost early last week has adapted, the Sunday finalist has not |
| Why the price might miss it | No price input carries location. Schedules are public, but no betting line does the arithmetic of zones and days |
| Type | W |
| Formula | ΔZ_X = signed UTC-offset change from X's previous venue to this one (east positive); T_X = days from X's last match there to this match. JL_X = (a·(ΔZ_X)+ + b·(−ΔZ_X)+)·(1 − T_X/(c·abs(ΔZ_X)))+·(1 + ρ·(age_X − 28)+), with c ≈ 1 day per zone. Diff JL_A − JL_B. Swap ✓ |
| Data | A city-level venue → UTC offset table, with team-tie venues and daylight saving. It is **not on disk**: the event-country table gives 81 countries, and the US, Canada, Mexico, Brazil, Russia, China, Kazakhstan and Australia span several zones. Plus the match clock. Safe (a static table and the player's own sequence) |
| Why the model cannot already do it | Nothing about place is in the inputs |
| Expected effect | Negative in the first one or two matches after ≥ 5 zones within ≤ 5 days. Examples: Indian Wells after the Gulf, the Asian swing after the US Open, Australia in January. 0.05–0.2 mLL. Registered as C03 |
| Kill test | No gain on first matches with abs(ΔZ) ≥ 5 and T ≤ 5; no decay with T and no east–west asymmetry (no dose–response) |

#### BOD-16 · On-site acclimatisation × how new the conditions are

| Field | Content |
|---|---|
| ID, name | BOD-16 · On-site matches × conditions novelty |
| Mechanism | Matches already played at this venue buy knowledge of the courts, balls, air and clock: through qualifying, or a first round won while the opponent had a bye. That knowledge is worth most when the conditions are new to the player (time zone, surface, indoor or outdoor, altitude) and little when they are familiar |
| Why the price might miss it | The market sees "qualifier" (tired, or in form) and "seed with a bye" (rested). It does not weigh how new the conditions are |
| Type | W |
| Formula | OS_X = log(1 + on-site matches before this one). Nov_X = 1[surface switch from X's previous event] + 1[indoor/outdoor switch] + abs(ΔZ_X)/12 + altitude change in km. Feature: OS_A·Nov_A − OS_B·Nov_B, beside the main effects of OS and Nov. Swap ✓ |
| Data | Stage 0 (`tournament_id`, `surface`, men's `indoor`); the tables of BOD-15, BOD-22 and BOD-23. Safe. Prevalence in §1 |
| Why the model cannot already do it | `sets_14d` mixes on-site and off-site sets; there is no novelty measure |
| Expected effect | Positive for the acclimatised player when conditions are new: 96-draw Masters (byes), qualifiers after a continent change. 0.05–0.2 mLL. Registered as C02 |
| Kill test | OS·Nov adds nothing beyond OS and Nov |

#### BOD-17 · Weeks on the road × age

| Field | Content |
|---|---|
| ID, name | BOD-17 · Consecutive weeks away × age |
| Mechanism | The third or fourth straight week of tournaments, especially far from the home continent, accumulates travel, sleep and mental load. The 14-day window sees two weeks at most |
| Why the price might miss it | It means counting weeks and places, which nobody shows |
| Type | W |
| Formula | Wk_X = consecutive tennis weeks up to this one in which X played a match (all levels, team ties included). Away_X = weeks since X last played on the home continent (player country and event country mapped to continents). Feature: [Wk_X·(1 + α·(age_X − 28)+) + β·Away_X]_A − [·]_B. Swap ✓ |
| Data | Stage 0 `country`; event-country table; continent map. Safe |
| Why the model cannot already do it | One 14-day window, no place |
| Expected effect | Negative from about the fourth week, more for older players; the Asian and American swings. 0.05–0.2 mLL |
| Kill test | No gain beyond BOD-02's Fit and Fat; or no monotone rise with the number of weeks |

#### BOD-18 · Season odometer × age × time of year

| Field | Content |
|---|---|
| ID, name | BOD-18 · Season load × age × season phase |
| Mechanism | By October the leading players have 50+ matches behind them (median 53 for men, 51 for women before an October match). The season's cumulative load bites more for older players and in the indoor autumn, while players racing for the Finals or ranking cut-offs keep pushing. At the other end, players whose season ran into late November start January after a short off-season |
| Why the price might miss it | Prices follow form and rank, not a season-long odometer |
| Type | W (S-type month modulation) |
| Formula | Odo_X = (season minutes to date − E[· given date, ranking band])/E[·], with E frozen on 2010–2018. Feature: [Odo_X·(age_X − 27)+·1[month ≥ 9]]_A − [·]_B. Off-season variant for first matches of the season: [log(off-season days)·(age_X − 27)]_A − [·]_B. Swap ✓ |
| Data | Stage 0. Safe |
| Why the model cannot already do it | No season-level load; age only as a difference |
| Expected effect | Negative for overloaded veterans in September–November; men. 0.02–0.1 mLL |
| Kill test | No gain; or the effect is not concentrated in the autumn |

#### BOD-19 · Off-tour load: team ties and the travel they hide

| Field | Content |
|---|---|
| ID, name | BOD-19 · Team-tie load |
| Mechanism | Davis Cup and Billie Jean King Cup ties (best of five for men until 2018) and other team events add matches, travel and emotion outside the tour's results pages |
| Why the price might miss it | Tour-level form guides leave them out |
| Type | W |
| Formula | Team_X = log(1 + Σ_{team ties, Δ_j ≤ 21} L_j·exp(−Δ_j/τ))·(1 + Trav_X). Diff. Swap ✓ |
| Data | Stage 0 level `TEAM` (8,551 matches to 2024). Ties are 34% undated (median window 8 days), so Δ is coarse. Safe |
| Why the model cannot already do it | `sets_14d` may count team-tie sets (cartographer to check), but not separately and not with travel |
| Expected effect | Negative; September (ties after the US Open) and February. 0.02–0.1 mLL |
| Kill test | No gain beyond BOD-01 and BOD-02 built with team ties included |

#### BOD-20 · Surface-switch adaptation depends on style and age

| Field | Content |
|---|---|
| ID, name | BOD-20 · Surface switch × style, surface switch × age |
| Mechanism | After a switch, adaptation cost depends on game and age. Servers carry over to grass and clay grinders do not; movement adapts faster in the young, judgement faster in the experienced. The model knows each player's switch state (the `surf_season` and `surf_layoff` pairs) but receives style and age only as differences, so it cannot cross A's switch state with A's own style or age |
| Why the price might miss it | The market absorbs the switch's main effects (they tie at the close, §2). How the switch interacts with style is a finer judgement |
| Type | W |
| Formula | New_X = exp(−n_surf_season,X/ν)·log(1 + surf_layoff_X/30). Features: New_A·Sty_A − New_B·Sty_B and New_A·(age_A − 28) − New_B·(age_B − 28). Sty is the serve-minus-return style (BOD-06) or the player's specialisation (surface rating minus overall). Swap ✓ |
| Data | The model frame's pairs; Stage 3 ratings; per-player surface IOS (leak-proof). Safe |
| Why the model cannot already do it | A pair crossed with a difference cannot recover a product of A's own values |
| Expected effect | On grass, New × serve style positive; on clay, New × return style positive; switch weeks only. 0.05–0.2 mLL |
| Kill test | No interaction beyond the pairs and the model forecast in switch weeks |

#### BOD-21 · A stale surface profile: reliability by surface layoff

| Field | Content |
|---|---|
| ID, name | BOD-21 · Surface-profile staleness weighting |
| Mechanism | The per-surface IOS grass profile rests on matches up to eleven months old. For a player with no grass match since last July it is stale (ageing, changes of game); for one who played three grass events this June it is fresh. The model weighs iosO_A − iosO_B as if both halves were equally current |
| Why the price might miss it | Market makers see current form across surfaces; the gain here is mainly the model's own sharpness. Its edge leans most on the IOS profile |
| Type | U |
| Formula | w_X = n_X/(n_X + k)·exp(−surf_layoff_X/θ). ios*_X,s = w_X·ios_X,s(surface) + (1 − w_X)·ios_X,s(all surfaces). Diffs ios*_A,s − ios*_B,s beside, or instead of, iosO/iosD. Swap ✓ |
| Data | Per-player surface and all-surface IOS (`surface_features.parquet`, leak-proof clock required); `surf_layoff` |
| Why the model cannot already do it | Differences hide which half is stale |
| Expected effect | Small but broad; the opening weeks of the grass and clay seasons. 0.05–0.2 mLL |
| Kill test | The reweighted profile ties the plain one |

#### BOD-22 · Indoor–outdoor switch × serve style

| Field | Content |
|---|---|
| ID, name | BOD-22 · Indoor/outdoor switch × style |
| Mechanism | Indoors there is no wind or sun, and courts often play faster: servers gain and rhythm players need time. Moving from outdoor to indoor hard courts (after the US Open, or from the Asian swing to the European indoor season) is a switch the surface label "Hard" does not record |
| Why the price might miss it | Conditions switches inside one surface label are rarely priced |
| Type | W / S |
| Formula | In_X = 1[X's previous match outdoor and this one indoor, or the reverse]·exp(−n_X,recent indoor/ν). Feature: In_A·Sty_A − In_B·Sty_B. Swap ✓ |
| Data | Stage 0 `indoor` (men). **Observed:** women's `indoor` is missing on every row; tennis-data.co.uk's Court field may supply it (cartographer). Safe |
| Why the model cannot already do it | `indoor` is context, for men only; there is no switch state |
| Expected effect | Small; the autumn. 0.02–0.1 mLL. Registered as B11 |
| Kill test | No gain |

#### BOD-23 · Altitude × serve profile × acclimatisation

| Field | Content |
|---|---|
| ID, name | BOD-23 · Altitude |
| Mechanism | Thin air makes the ball fly faster and further: free points rise and control falls. Venues: Bogotá about 2,640 m, Quito about 2,850 m, Gstaad about 1,050 m; Kitzbühel and Madrid 650–760 m (recalled elevations). Servers gain; players just arrived from sea level need days |
| Why the price might miss it | Venue character is known, but its cross with each player's serve profile is not quoted |
| Type | S (+ W) |
| Formula | S part: Alt (km, hand-made table) × (iosO_ace_A − iosO_ace_B), antisymmetric ✓. W part: Alt × (OS_A − OS_B), or Alt × (days on site)_A − same_B ✓ |
| Data | An elevation table (about a dozen venues; not on disk); Stage 0. Prevalence in §1. Court pace estimated from other matches would need the leak-proof clock |
| Why the model cannot already do it | No altitude input |
| Expected effect | Positive for servers. Directional only: perhaps a few mLL within the subset, under 0.05 mLL overall. Registered as C04 |
| Kill test | The within-subset gain spans 0. Keep it only as a component of BOD-16's novelty |

#### BOD-24 · Heat × age × load × style

| Field | Content |
|---|---|
| ID, name | BOD-24 · Heat |
| Mechanism | Heat raises physiological strain most for older, loaded players and long-rally styles, and it produces retirements (BOD-12). Both players face the same heat; the edge is in their different sensitivity |
| Why the price might miss it | Weather is a same-day fact, and differential sensitivity is a model, not a headline |
| Type | S / W |
| Formula | Heat_m (daily maximum temperature or WBGT at the venue on the match day) × [Fat_X·(1 + ρ·(age_X − 28)+)·(1 + ψ·R_X)]_A − [·]_B, where R_X is BOD-07's rally-length style. Swap ✓ |
| Data | **None on disk, to my knowledge** (cartographer). It needs venue coordinates and a historical weather archive; climate normals by venue and month are a weak proxy |
| Why the model cannot already do it | No weather input |
| Expected effect | Negative for old, tired grinders in heat: the Australian Open, the US summer, humid Miami and Shanghai. Size unknown. Registered as C01 |
| Kill test | Park it if the data are unavailable; otherwise, no gain |

### D. Effort and motivation

#### BOD-25 · Effort allocation: elite players at small events, and ranking cliffs

| Field | Content |
|---|---|
| ID, name | BOD-25 · Elite effort before Slams; incentive cliffs |
| Mechanism | In the week before a Slam, top players use a 250 or 500 as practice and protect their bodies: they withdraw, retire or coast, while mid-ranked players chase points. Late in the season, players racing for the Finals or for Slam entry cut-offs push harder |
| Why the price might miss it | Prices follow strength; effort is a judgement, which the market knows in part |
| Type | W |
| Formula | E_X = 1[rank_X ≤ 20]·1[level ∈ {250, 500}]·1[a Slam main draw starts within 8 days]. Variant: 1[X is seeded at the coming Slam]. Cliff variant: how close X's points are to the Finals or Slam-entry cut-off in the relevant weeks, with thresholds declared in advance (the frontier register's C08 warns of the search space). Diff E_A − E_B. Swap ✓ |
| Data | Stage 0 `rank` (as of the tournament start), level, dates. Safe. **Observed:** 305 men's and 592 women's 2013–2021 matches qualify; top-10 players at 250/500 events in any week: 1,573 and 1,228 |
| Why the model cannot already do it | No ranking tier (only strength differences), and level is only context |
| Expected effect | Negative for elite players in pre-Slam weeks. 0.02–0.15 mLL |
| Kill test | No gain; or no difference between pre-Slam and other weeks for elite players |

#### BOD-26 · Home split into crowd and no travel

| Field | Content |
|---|---|
| ID, name | BOD-26 · Home × level × rank, and home × the opponent's travel |
| Mechanism | At home a player has the crowd and no travel. The crowd matters more for lower-ranked locals (wild cards) and at bigger events; "no travel" matters when the opponent has just crossed time zones |
| Why the price might miss it | The plain home effect is priced; its interaction with the opponent's jet lag is not |
| Type | W / X |
| Formula | H_X = 1[player country = event country]. Features: (H_A − H_B)·g(level); [H_X·log rank_X]_A − [·]_B; and the X-type H_A·JL_B − H_B·JL_A. Swap ✓ |
| Data | Stage 0 `country`; the event-country table; JL from BOD-15. Safe |
| Why the model cannot already do it | No location input |
| Expected effect | Small. 0.02–0.1 mLL. Stage 4 scored women's home as a main effect "worse" given Elo |
| Kill test | No gain beyond home's main effect |

### E. Age and the body over the years

#### BOD-27 · Style-specific ageing: servers age more slowly than movers

| Field | Content |
|---|---|
| ID, name | BOD-27 · Age × style drift |
| Mechanism | Serve skills rest on technique and height and fade slowly. Return and movement skills fade faster after about thirty. A long-memory profile therefore overstates an ageing returner more than an ageing server |
| Why the price might miss it | Age is priced as one number ("veteran") |
| Type | W |
| Formula | Drift_X = (age_X − 29)+·(RetShare_X − 0.5)·M_X. RetShare is the return side's share of X's points edge (Stage 3 or IOS); M_X is the profile's effective memory (years since the median match in it). Diff Drift_A − Drift_B. Variant: per-statistic drifts, fast for rpw_first and rpw_second, slow for ace and first_won. Swap ✓ |
| Data | Stage 3 ratings, per-player IOS (leak-proof), ages. A check that uses statistics only, no winners: per-statistic year-on-year changes by age from 2010–2018 box scores |
| Why the model cannot already do it | Age and style arrive only as differences |
| Expected effect | Negative for older return-based players; men. 0.05–0.2 mLL |
| Kill test | The statistics-only check shows no style difference in the age curves; or the product adds nothing |

#### BOD-28 · Age-dependent trust in recent form

| Field | Content |
|---|---|
| ID, name | BOD-28 · Age × (recent profile − long-memory profile) |
| Mechanism | Teenagers and early-twenties players improve fast, so their recent profile estimates them better than their long memory does. For veterans a recent dip is more often noise or a passing injury. The model sees both profiles and age, but only as differences, so it cannot trust A's recent form more because A is 19 |
| Why the price might miss it | Rising players are visible, but how far to update is a judgement. The long-memory IOS profile, TabPFN's most used group, lags them by construction |
| Type | W (U character) |
| Formula | Mix_X = (Short_X − Long_X)·h(age_X), with h(age) = (25 − age)+ − κ·(age − 30)+. Short is the two-week adjperf (or the short IOS points); Long is the long-memory IOS composite. Diff Mix_A − Mix_B, for the composite and for key statistics. Swap ✓ |
| Data | Per-player short and long profiles, A and B separately (leak-proof IOS); Stage 0 ages |
| Why the model cannot already do it | The brief's point about levels: A's age cannot meet A's own gap between recent and long-memory form |
| Expected effect | Positive weight on recent-minus-long for the young. Women (37% of women's player-matches are aged 23 or younger) and young men. Broad prevalence. 0.1–0.3 mLL |
| Kill test | The product adds nothing beyond its main effects |

#### BOD-29 · Height × age and height × load

| Field | Content |
|---|---|
| ID, name | BOD-29 · Height interactions |
| Mechanism | Very tall players rely on the serve, move less well and load their joints and backs more. Their decline with age, and what a long week costs them, may differ |
| Why the price might miss it | Height is a static fact that is rarely crossed with state |
| Type | W |
| Formula | [height_X·(age_X − 28)+]_A − [·]_B and [height_X·Fat_X]_A − [·]_B. Swap ✓ |
| Data | Stage 0 `height`: 52% of all rows. Stage 4 reported 87% of men's and 65% of women's evaluation matches, and 37% of women's in 2022–2026. Safe |
| Why the model cannot already do it | No height input |
| Expected effect | Small; men. 0.02–0.1 mLL |
| Kill test | No gain; coverage too thin for women |

#### BOD-30 · Serve decay inside the event: a fatigue or injury sensor

| Field | Content |
|---|---|
| ID, name | BOD-30 · Within-event serve trend |
| Mechanism | A player whose first-serve percentage and first-serve points won fall round by round, against their own profile, may be carrying a shoulder or back problem. Where radar exists, a drop in serve speed against the player's own baseline is a sharper sensor: the men's recent serve speed was the shot-level study's one direction to watch (+0.24 mLL) |
| Why the price might miss it | Trends inside an event are not on the score sheet |
| Type | W |
| Formula | Tr_X = the shrunk slope of X's first_won and first_in residuals against X's profile over X's matches at this event and the previous one. Speed variant: X's mean first-serve speed in the last two matches minus X's 52-week mean. Diff Tr_A − Tr_B, and its product with Fat. Swap ✓ |
| Data | Stage 0 box scores (safe). Serve speed from the Slam and other point feeds (partial, mostly from 2019) |
| Why the model cannot already do it | The two-week profile is a mean, not a slope |
| Expected effect | Negative; small; noisy |
| Kill test | Split-half reliability of Tr is not above the pure-luck replay's; then the screen |

## 4. Data notes for the cartographer

1. **Minutes.** Men's main tour 83% in 2013–2015, about 99% from 2016. Women: almost none before 2016, then 98–99%. Fallbacks: points from box scores (women's have holes before 2019) and games from scores. Stage C suggested a plausibility rule of 15–120 seconds per point.
2. **`sets_14d`'s exact window and levels.** Does it count ITF, team-tie and qualifying sets? It counts from event start dates (match-timing README §8).
3. **Per-player values, A and B separately**, for the IOS long-memory profile, the short memory, and Stage 3 serve and return ratings. Are they on the leak-proof clock? `surface_features.parquet` is listed in the brief.
4. **Women's indoor flag.** Missing on every Stage 0 row. Check tennis-data.co.uk's Court field.
5. **Tables not on disk:** venue → city → UTC offset (with daylight saving), venue elevation, and weather.
6. **Rest in hours:** start and finish times from the Australian Open archive (actual start, duration, session), the Slam feeds from 2019 (point timestamps), and SofaScore from now on. Coverage before 2019 is thin.
7. **Doubles workload.** Stage 0 is singles only; is any doubles history on disk?
8. **Retirement settlement rules** of the books inside tennis-data.co.uk's average, and how they changed over time. Only Betfair's and Pinnacle's current pages are registered.
9. **Byes.** No explicit rows (7 `bye` details to 2024). Infer them from `draw_size`, seeds and the player's first round.
10. **Prevalence denominators.** My counts cover all main-draw matches; the odds-linked population is about 90% of them (the men's 2018 season is missing).

## 5. Top 8, ranked

1. **BOD-01, load split.** `sets_14d` mixes on-site survival, which is priced, with carried-over debt, which is not. Splitting it is cheap and touches 43% of player-matches.
2. **BOD-12, retirement hazard × price.** Contract mismatch, and a logit shift ≈ h_B/p − h_A/(1 − p) that a linear input (the earlier tie) cannot express.
3. **BOD-02, duration × recency kernel.** First use of real days and minutes on the full history; the earlier rest null used a truncated history.
4. **BOD-03, age × recovery debt.** The brief's own example of what A − B inputs cannot form: A's age times A's load.
5. **BOD-09, previous-round scare × rest.** A sign flip, fatigue at ≤ 1 day of rest against over-reading at ≥ 2, separates the body from the market's narrative; about 4,000 matches per tour in 2013–2021, half with ≤ 1 day of rest.
6. **BOD-14, last week's deep run × short gap × travel.** Recent form is priced, but the calendar squeeze and the continent change are not.
7. **BOD-04, fatigue through the point model.** Best of five amplifies a decrement 1.25–2 times, at the Slams where TabPFN's edge is largest.
8. **BOD-28, age-dependent trust in recent form.** Young players' recent-minus-long gap, which differences hide; broad prevalence, especially for women.

Next in line: BOD-15 (jet lag), BOD-16 (on-site × novelty) and BOD-07 (the opponent who exploits fatigue).
