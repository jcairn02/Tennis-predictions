# Tennis-signal scout: what the 2025–26 close plausibly misses (round 1)

12 Oct 2026 · Role: the tennis-signal scout ([brief](../briefs/03_tennis_scout.md)) · Claude Opus 5.5, a subagent of the lead's session · Written before any result of this study.

* **Outcomes read: none, of any season.** The only computation is a set of result-free counts from the feature store (which has no result column) and from prices: `data/studies/edge_anatomy/team/tennis_scout/descriptives.py` → `descriptives.json` / `.md`.
* **Labels.**
  * *Observed* = in a repository file (path given).
  * *Provider claim* = a web source (URLs at the end, accessed 12 Oct 2026).
  * *Inferred* = my reasoning.
  * *Suggestion* = not decided.
* **Keys.** Gains are in mLL per match. Each coefficient has its own direction key. An interval spanning 0 is "unresolved".

## Summary

1. **The repository's pattern.**
   * Priced: what describes how a player *is*, such as ratings, surface skill, style, momentum and shot-level rates.
   * Not priced: what describes how he is *right now* (two-week form, serve-speed change), or *where his evidence comes from* (lower levels, the draw).
   * I ranked the candidates through that lens.
2. **Only one signal has blind evidence of being unpriced by the 2025–26 close:** men's serve-speed change, already stage 2. Extend that family first.
3. **Next in line:**
   * arrivals from lower levels: the mispricing grew by era and is unseen on 2025–26;
   * on-site rhythm at the expanded 12-day events: the calendar change shows in our own data;
   * crowd over-reaction: does BetOnline's close, the 2026 benchmark, keep more of it than Pinnacle's?
4. **What one test on 2025 – 28 Jul 2026 can see.**
   * It resolves about 0.07 log-odds per SD (≈ 0.5 mLL); men alone, about 0.09 (≈ 0.9 mLL).
   * Most candidates are 0.1–0.4 mLL, so "unresolved" is their likely reading.
   * So use result-free gates, the open-to-close move and the sealed matches.
5. **Where admitted signals go.** TabPFN under-uses small, sparse signals as columns: speed 8%, rust 39%, the lower-level share about a third of what was left. Admitted signals belong in a walk-forward stage-2 layer around the close.

## 1. The lens and the harness

**Four ways a 2025–26 close can miss something:**
* **M1, unwatched data.** Prices are set from results, rankings and news, not from radar, tracking or umpire logs.
* **M2, slow anchors.** Rankings and reputations lag current level.
* **M3, structural change.** The 2023 and 2025 calendar expansions, the growing second tier, court and ball changes, the 2026 heat rule.
* **M4, crowd over-reaction a close keeps.** It is likelier at a recreational book. Since 7 Sep 2025 the model's price is BetOnline's line, because Pinnacle's closes are missing (`pinnacle_first`).

**What 2025–26 can resolve** (*observed*, prices only, `model_frame.parquet`).
* The sample: 8,591 matches from 2025 to 28 Jul 2026, of which 4,394 are men's; mean p(1−p) ≈ 0.206.
* **The coefficient test.** For a signal beside the both-stages forecast, the SE is ≈ 0.024 log-odds per SD (men 0.033), before clustering. At 80% power it detects ≈ 0.067 per SD (≈ 0.46 mLL).
* **The near misses.** A near miss screened on 2014–24 (52,707 matches) would show about 0.40 × its screen z.
* *Suggestion.* Apart from #1's base statistic and the age input behind #5, every candidate is unseen on 2025–26 (`universe.csv`). Spend that one look on a pre-registered family (Holm) of #2–#5, and read the rest on the sealed matches.

**A result-free companion: does the line move toward the signal?**
* **The test.** Regress BetOnline's open-to-close move on the signal, by season, 2018–2026 (openings: `bet_timing`, `data/dump/odds/oddstrader/`). It reads no result, so it can run on the sealed period too, and it is precise.
* **How to read it, crossed with the outcome test:**
  * moves and still predicts beyond the close: partly learned;
  * moves, no prediction left: priced at the close, an early-bet signal;
  * no move, predicts: **unpriced**;
  * "no move" alone could also mean priced at the opening.
* **Known so far** (observed):
  * BetOnline's line does not move toward the model as a whole: +0.01 (`bet_timing`);
  * Polymarket's price moves 29–45% of the way toward it from 24–48 hours out;
  * Polymarket's price learns the surface-offset ratings' view between 24 hours and the close (`surface_rating_race`).

## 2. Ranked candidates

| # | Signal | Mechanism | Status on 2025–26 | Likely reading of the cheap test |
|---|---|---|---|---|
| 1 | Serve-speed state, extended (men) | M1 | the base replicated blind; extensions new | the gate resolves; the outcome test is unresolved with P(better) > 0.5 |
| 2 | Arrivals from lower levels (U-330) | M2, M3 | unseen | z ≈ 1.6 at the 2020–24 size |
| 3 | On-site rhythm and the seed's bye (U-138, U-307) | M3 | unseen | z ≈ 1.3–1.5 |
| 4 | Over-reaction kept by BetOnline's close (U-278–U-281) | M4 | unseen | the paired Pinnacle-vs-BetOnline test is precise |
| 5 | Age-curve drift since last seen | M2 | age seen; the drift new | unresolved; it may have flipped |
| 6 | Autumn season load × age (U-144, U-296) | M3 | unseen | unknown alone |
| 7 | Real rest hours (C07, U-195) | M1, M3 | never built | gate first |
| 8 | Edition pace and balls (U-192, U-254) | M3 | unseen | z ≈ 1.0 |
| 9 | Women's state from the WTA's advanced statistics | M1 | never built | gate first |
| 10 | Calendar incentives (U-283, U-284) | M3 | unseen | rare events |
| 11 | Heat stress | M1, M3 | new data | gate first |
| 12 | Same-event doubles load | M1 | never built | likely unresolved |

**1. Serve-speed state, extended (men).**
* **Mechanism.** A man serving faster than his own norm is physically up before results show it.
* **Evidence** (`serve_speed_tabpfn`; + = the man whose speed rose wins more than forecast):
  * the blind 2025–26 replication: +0.103 [+0.029, +0.178] log-odds per 6.0 km/h;
  * beyond the model, 2024–26: +0.065 [+0.012, +0.118] per 2.2 km/h;
  * TabPFN used 8% of it; as a nudge it gained +0.41 [+0.04, +0.78] mLL (+ = the nudge better).
* **Why the close may miss it.** The data are fragmented or encrypted, and radars break between editions: the same men read +8.5 km/h at Wimbledon 2024→25 and +9.7 at the US Open 2025→26.
* **Counter.** The seasons disagree (I² ≈ 50%; 2023 lost 1.3 mLL, `infosys_atp_backfill`). None of its 2026 readings is against Pinnacle's close, which is missing.
* **New, untested.**
  * The second-serve speed change: `sl__spd2_*` and ManTennisData.
  * The fault speed and the last match's speed fade, from per-point files: AO/RG 2025–26 on disk; ATP 2025–26 decryptable under the 8 Oct approval.
  * The daily collector: +0.38 mLL with weekly data, +0.47 daily, +0.54 instant (`docs/decisions/2026-10-08-scraping-approved.md`).
  * A cap on the Challenger dose: 1.5% → 13% of the panel in 2026 (`lower_level_evidence` §1.4).
* **Test.**
  * The gate (≤ 2024): does it predict next-match first-serve points won beyond `spd_L`?
  * Then an information test beyond both stages, men, 2025–Jul 2026 (SE ≈ 0.034 per SD).

**2. Arrivals from lower levels, and what their lower-level box scores say.**
* **Mechanism.** Prices lean on rankings, and ranking points accrue slowly below the main tour. Elo rates these players about right; the market does not (`event_levels` §3, §8).
* **Evidence.** β of the share difference beside the average close; + = the price under-rates the more lower-level player.
  * By era: +0.06 (2013–16, unresolved), +0.13 (2017–19), +0.18 [+0.09, +0.27] (2020–24). **It grew; it did not decay.**
  * Pinnacle, 2013–24: +0.12 [+0.06, +0.17].
  * By level: 500s +0.41, 250s +0.20, 1000s −0.02.
  * The current model leaves +0.12 [+0.03, +0.21] (2020–24).
  * As an input, unresolved (+ = with the share better): +0.06 [−0.10, +0.23] mLL as a 59th column, +0.08 [−0.35, +0.50] as a stage-2 term. Its walk-forward coefficient was positive in every season.
* **Why now** (provider claims). WTA 125 events went from 24 (2022) to 53 (2025), with about 68 listed for 2026. Challenger 175s run beside the 12-day 1000s.
* **Counter.**
  * It is worth about 0.1 mLL a match on the main tour.
  * The men's level layer, adopted on 10 Oct, may already carry part of it.
* **Data.**
  * `el__low_share_*` in the feature store;
  * `data/studies/event_levels/history.parquet`;
  * the layer's translated forms (`data/studies/current_best_model/level_layer/official.json`).
* **New angles.**
  * Translated lower-level form minus ranking-implied strength.
  * For women, the P7 ITF box scores.
* **Precondition.** Stage 0 lost ITF, WTA 125 and women's qualifying after early June 2026 (`lower_level_evidence` §1.4, item 3). Women's 2026 values are therefore biased toward 0 for exactly these players. Repair this first, as a candidate.
* **Test.**
  * The model's leftover β on 2025–Jul 2026, with the 250/500 split pre-registered (SE ≈ 0.06–0.07 per unit of share).
  * The move test, by season.

**3. On-site rhythm, and the seed's bye at the expanded 1000s.**
* **Mechanism.** Matches already won at the event, qualifying included, adapt a player to its balls, court and conditions. At 96-player draws the seeds start with a bye and then meet opponents who have played there.
* **Observed, result-free** (`descriptives.json`).
  * Share of 1000s matches played at 96-player draws: about 33% (2013–22), 69% (2023–24), 86% men and 80% women (2025–26).
  * Share of 1000s matches where a seed meets an unseeded player with more matches at the event: 33–34% → 40% → 43%.
  * Across all levels, such matches number 1,030–1,110 a full season in 2013–22 and 1,363 in 2025.
* **Evidence.** Beyond the current model, On reads z +3.29 (2014–21 +2.63, 2022–24 +1.99); beyond the price +3.03. + = the player with more matches here wins more than forecast. It was a descriptive member of a failed block, so selection inflates it.
* **Counter.** "The dangerous qualifier" is old lore, and `sets_14d` and `round` carry part of it.
* **Test.** One-sided, beyond both stages, with the cold-seed subset as the secondary (about 40% power, one-sided).

**4. Over-reaction that a recreational close keeps.**
* **Mechanism.** Salient results draw recreational money:
  * a flattering last-round scoreline;
  * a raw head-to-head of three or more meetings;
  * wins beyond the points earned;
  * a favourite whose price strays from the rating's view.
* **Evidence.**
  * As a block: z +2.13 beyond the model, +2.27 beyond the price. Both windows were positive (+1.64, +1.38), and the block was never decomposed.
  * Conversion luck alone (`market_anchoring`): −0.01 [−0.10, +0.09] mLL for 2019–25 and +0.28 [−0.07, +0.62] for 2026, both unresolved (+ = the nudge better).
* **Counter.** BetOnline's and Pinnacle's closes could not be told apart in 2024–25: +0.3 [−0.3, +0.9] mLL (+ = Pinnacle sharper).
* **Test (cheap and decisive).**
  * The method: each member's coefficient beside Pinnacle's close and beside BetOnline's close (`book_prices.parquet`), on the same matches of 2024 – 7 Sep 2025, as a paired difference. It is precise because the two prices nearly coincide.
  * What it would show: if BetOnline's close keeps more over-reaction, part of 2026's +3.57 comes from the benchmark, not from tennis.

**5. Age-curve drift since the player was last seen.**
* **Evidence.**
  * In the anchored fit (men, 2013–25), age was the strongest single nudge: −0.072 per RMS unit, z −3.7 (negative = the older player does worse than priced).
  * Elo change over 26/52 weeks made close-based forecasts worse for men: −0.26 and −0.30 mLL, + = better (U-028, an early harness).
  * B-AGE failed replication (z₁ +1.32, z₂ −0.01).
* **It may have changed.**
  * *Observed:* men's matches with a player aged 32 or over fell from 38% (2017–19) to 21% (2025–26).
  * *Inferred:* young stars are now headline news, so the price may over-react to them.
* **Build.** The age-curve slope, fitted on rating increments to 2024, × days since the last match (U-132).
* **Test.** The drift beyond both stages, plus its move test. The lead's scan reads age itself.

**6. Autumn season load × age, after the calendar expansion** (U-144, U-296).
* **Evidence.**
  * The B9a block (height × load, height × age, recovery, odometer × age): z₁ +0.10 (2014–21), z₂ +2.52 (2022–24) (+ = the declared direction). It was absent in 2014–21 and present in 2022–24. *Inferred:* that fits the denser calendar from 2023, although 2022 comes before it.
  * `next_candidates` names the autumn odometer × age its likeliest member. That member is declared as "a heavier season, past 27, costs more in the autumn than forecast".
  * The member was never screened alone.
* **Why now** (provider claim): heat retirements at Shanghai 2025.
* **Test.** Pre-register the member now, then read it once on autumn 2025 plus autumn 2026 (the sealed matches). If it carries the block's 2022–24 signal, z ≈ 2.

**7. Real rest hours** (register C07, never built).
* **Mechanism.** Recovery runs in hours; models and most bettors count days.
* **Counter.** Every days- or minutes-based load measure was unresolved beyond the close (B-LOAD, B-PREV, I-056).
* **Data on disk.**
  * Start times: `tennislive_events` (2018–2026), the match-timing links (`start_utc`), Flashscore start times and set durations.
  * Durations: match minutes.
  * Point clocks: the Slam feeds, the WTA umpire log, TDI.
* **Test.** A gate on ≤ 2024: does rest under about 20 hours predict worse next-match serve and return points beyond days? It touches a few percent of matches, so only large effects resolve.

**8. Edition pace and ball changes.**
* **Provider claims.**
  * Paris moved to La Défense Arena in 2025, and its Court Pace Index fell from 46.6 to 35.1.
  * Tournaments choose their own balls.
* **Evidence.** B-VENUE, venue pace × the server's ace offence: z +2.50 beyond the model, +2.72 beyond the price (+ = the bigger server gains more at fast venues).
* **Observed, result-free.** The as-of pace shows no surge of edition jumps in 2025–26: 2.8% and 1.3% of editions moved by more than 0.10, against 2–10% in 2014–24. Either the changes were smaller than reported, or the estimator, shrunk by 2,000 points, lags.
* **Counter.** The close applies 43% of the iid serve-dominance scaling, against a damped truth of about 39% (`feature_interactions`).
* **Test.** B-VENUE beyond both stages (z ≈ 1.0). A faster-learning variant can be checked on the changed editions, as case studies.

**9. A women's state signal from the WTA's advanced statistics.**
* **Mechanism.** Women have no tour-level speeds. The WTA API holds winners and errors for 2022–24, and fault reasons, rallies and net play for 2025–26 (`data/dump/points/wta/advanced/`). A change against her own normal may flag a state.
* **Counter.** Error rates are noisy, and the shot-level study closed them as traits. The women's edge so far is "mostly a curved calibration of the odds".
* **Test.** A gate on 2022–24, then a nudge scored once on women's 2025–Jul 2026.

**10. Calendar incentives.**
* **Mechanism.** Effort saved before a Slam; a letdown after a deep Slam run.
* **Rule change** (provider claim): from 2026 the mandatory ATP 500s fell from five to four, and the ranking counts 18 results instead of 19.
* **Evidence.** B-MOTIV: z₁ +2.39, z₂ +0.49.
* **Test.** Rare events, so read with the sealed matches.

**11. Heat stress.**
* **Provider claims.** Shanghai 2025's retirements; an ATP heat rule from 2026: a cooling break at WBGT ≥ 30.1 °C, play suspended above 32.2 °C.
* **Data.** No weather is held.
* **Test.** A gate on retirements and on men's speed fade in hot sessions.

**12. Same-event doubles load.**
* **Mechanism.** It is invisible to singles histories.
* **Data.** `tennislive_events` lists doubles.
* **Test.** The cheapest to build; likely unresolved.

## 3. The owner's thesis

**Which candidates fit.**
* *Fit:* #1 (point-derived), #9, and the translated box-score form in #2.
* *Do not fit:* #3–#8 and #10–#12. They are structural, behavioural or physical context.

**What supports it** (observed).
* **TabPFN-Thinking's adjustment** to the price leans on the IOS profile (0.62), the two-week profile (0.44) and load/age (0.40), and on Elo only 0.12. These are the shares lost when each group is shuffled (`tabpfn_thinking`, men, inputs before the repair).
* **The 16-statistic profile** was the strongest family against the price: +0.33 mLL beside the average close and +0.30 beside Pinnacle (2019–25), +0.91 in 2026 (`market_anchoring`).
* **No rating adds** anything given the odds.

**What goes against it.**
* Every trait-like point statistic tested is priced or noise, including 0 of 280 shot-level rows.
* The surface profile adds nothing at the close: +0.01 [−0.10, +0.13].
* The linear profile's gain fell from +0.83 to +0.25 after the leak repair.

**My reading** (*inferred*).
* Right: win/loss ratings are priced.
* Too narrow: the unpriced part is not in long-run offence/defence *profiles*. It is in how fast the model updates a player's *current* point-level state, plus structural information that is no point statistic at all.

**Caution for 2025–26 first-serve readings.**
* Tennis My Life recorded men's Slam first serves wrongly from about August 2025 (`data_continuity`).
* The Roland Garros 2022–25 repair, adopted on 10 Oct, is not in the current instance, which is built on the 8 Oct tables.
* 15 inputs are exposed, in 264 men's test matches of the frozen frame (`feature_universe` §6, item 8).

## 4. Priced with high confidence: stop here

| Information | Why (observed unless marked) |
|---|---|
| Overall strength: Elo, TrueSkill Through Time, Glicko, rankings | No rating adds given the odds (`rating_systems`, `surface_rating_race`) |
| Surface skill and specialisation | All unresolved at the close: surface Elo −0.01, surface IOS +0.01, surface statistics +0.02. Polymarket's 24-hour price moves toward it by the close (`surface_rating_race`) |
| Serve dominance and best-of-five leverage | The close applies 43% of the iid scaling; the truth is about 39% |
| Style, momentum, leverage, tempo, shot-level rates | Every trait gate or residual screen fails (`point_sequence`, `shot_level`) |
| Rust after a break | z +3.51 (2014–21), then +1.93 (2022–24), then −0.27 [−0.64, +0.10] mLL on 2025–26 (+ = the rust nudge better). This is what alpha decay looks like; plot this curve for every candidate |
| Pair strength, weak-pair favourite–longshot bias | Not confirmed on 2025–26: the slope b +0.022 [−0.030, +0.074], on the side opposite to the prediction (`pair_strength`) |
| Head to head, home, travel, days-based fatigue, indoor | Unresolved or worse beyond the close |
| A physio treatment's effect on the result | The retirement risk ratio is 2.27, but the effect is unresolved given the close: a settlement question |
| Late news: injury, illness, withdrawals | *Inferred:* in the close by construction and never in our inputs. Check where the model fights a sharply moved line |

## 5. New data: source and cost

| Data | Source | Cost | Serves |
|---|---|---|---|
| ATP per-point files (speed per serve, fault speed, rally, direction) and Court Vision, 2025–26 and live | Stats Centre, decrypted under the 8 Oct approval. The daily collector already decrypts key statistics (`src/eda/serve_speed_tabpfn/live/`) | ≈ 10,000–20,000 requests, 6–12 hours | #1 |
| ITF box scores 2018–24 (≈ 197,000) | Collection plan P7, due about 31 Oct – 2 Nov | Planned; needs a women's level layer | #2 |
| Lower levels Stage 0 lost after June 2026 | `itf_live`, `tennislive_events`, the WTA API's player-matches | Integration only, as a candidate (freeze rules) | #2; women's live inputs |
| Order of play and end times, live | Tournament and tour schedule pages | A small scraper | #7 |
| Hourly weather for WBGT, and a venue gazetteer | Open-Meteo archive and forecast APIs (free) | About 350 venues; a few thousand requests | #11 |
| Ball brand and court resurfacing per edition | Fact sheets, media | Manual; completeness unknown (U-196) | #8 |
| Pinnacle's closes from August 2025 | BettingIsCool (€99/month) or The Odds API ($119–249/month) (`docs/research/early-lines/`) | Paid; tells tennis information from a softer benchmark | #4, the diagnosis |

No public WTA tour-level speed source exists (`serve_speed_acquisition`).

## 6. For the lead: my expectations, written before any result

*Inferred, for the red team to score:*
1. Men carry most of the 2025–26 gain, at the Slams and 250s.
2. Within it, the gain is larger:
   * where the lower-level share gap is 0.5 or more;
   * where on-site counts differ;
   * where a player is back from a break of six weeks or more.
3. Stage 2 adds about +0.3 mLL for men.
4. Part of 2026's gain sits where BetOnline's margin is widest: favourites at 90% or more, where it is 1.93 times Pinnacle's (`betonline_lines`).
5. Women's 2026 inputs differ from training: lower levels are missing after June, and some ids split. Treat a weak women's 2026 as a data flaw before reading it as a market verdict.

## Sources (provider claims, accessed 12 Oct 2026)

* The 12-day, 96-player events:
  * ATP 2025: [tennis.com/AP](https://prod.tennis.com/news/articles/the-atp-men-s-tennis-tour-s-2025-calendar-includes-expanded-events-in-canada-and-cincinnati);
  * WTA: [wtatennis.com](https://www.wtatennis.com/news/4212745/canadian-open-cincinnati-expand-to-96-player-fields-extended-format);
  * 2026: [atptour.com](https://www.atptour.com/en/news/2026-atp-tour-calendar-announced).
* Mandatory ATP 500s and the 18 counting results (8 Jan 2026): [SuperSport](https://supersport.com/tennis/news/a8aedeea-cec6-4e71-8cb7-e03e4eeff2c7/atp-tennis-announces-reduction-in-obligatory-events).
* Challenger 175: [Wikipedia](https://en.wikipedia.org/wiki/ATP_Challenger_Tour_175).
* WTA 125 growth: [WTA](https://www.wtatennis.com/news/4340252/wta-125-circuit-hits-new-milestone-with-over-50-tournaments-scheduled-across-2025); [2026 list](https://en.wikipedia.org/wiki/2026_WTA_125_tournaments).
* Court speed:
  * Paris 2025: [Sports Illustrated](https://www.si.com/onsi/serve/news/data-shows-major-change-in-2025-rolex-paris-masters-court-speed);
  * homogenisation: [Last Word on Sports](https://lastwordonsports.com/tennis/2025/10/04/are-alcaraz-and-sinner-benefiting-from-court-homogenization/).
* Balls: [AP, January 2024](https://www.clickondetroit.com/health/2024/01/17/can-too-many-tennis-ball-changes-cause-injuries-players-think-so-the-tours-are-checking/).
* Shanghai 2025 heat and the 2026 heat rule: [Free Malaysia Today](https://www.freemalaysiatoday.com/category/sports/2025/12/16/atp-to-introduce-new-heat-policy-from-2026-season).
