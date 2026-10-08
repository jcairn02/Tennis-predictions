# Pre-registered test: Elo by surface, as amended after the audit

6 October 2026 · Fixed before any TabPFN call and before any 2022–2026 result of the new inputs. The paper trail:
[strategy.md](strategy.md) (the draft, audited as written) → [audit.md](audit.md) → [audit_review.md](audit_review.md)
→ this protocol.

**Key.**
* Log loss: lower is better.
* Gains are milli-log-loss (mLL), and positive means the second-named forecast is better.
* Brackets are paired 95% intervals over four-week blocks of tournament dates. A range that spans 0 is a tie.

## Arms

All arms are trained and scored on identical matches. Each arm's columns are listed in `arms.ARMS`.

| Arm | Inputs | Columns |
|---|---|---|
| `base` | The current best model's 54 inputs (odds + 53, IOS leak-proof), value for value | 54 |
| **`primary`** | base − `elo_logit` − `surface_first` + `elo_overall` + `elo_surf_offset` + `surf_season_a/b` + `surf_layoff_a/b` | 58 |
| `literal` | base − `elo_logit` − `surface_first` + `elo_overall` + `elo_surface` + `surf_career_a/b` + `surf_season_a/b` + `surf_layoff_a/b` + `surf_form_prev_a/b`: the owner's items 5 and 6 as written | 62 |
| `elo_only` | base − `elo_logit` + `elo_overall` + `elo_surf_offset`: primary's Elo change alone | 55 |
| `switch_only` | base − `surface_first` + the season and layoff pairs: primary's switch change alone | 57 |
| `base_noodds`, `primary_noodds` | base and primary without `odds_logit` (diagnostic) | 53, 57 |

The new inputs:

* **`elo_overall`.** Stage 1's overall Elo, as log-odds.
* **`elo_surf_offset`.** (D_A − D_B) × ln 10 / 400. Each player's surface offset starts at 0, moves only on that surface
  and has its own K, tuned on 2013–2018.
* **`elo_surface`.** Stage 1's 1500-started surface-only rating, as log-odds.
* **The pairs.** Each is exchanged when A and B swap:
  * `surf_season`: log(1 + this season's earlier played matches on the surface);
  * `surf_layoff`: log(1 + days since the last surface match), capped at 3 years;
  * `surf_career`: log(1 + career surface matches since 2010);
  * `surf_form_prev`: last season's wins above overall Elo's expectation on the surface, divided by (matches + 5).

## Model and design

* **Model.** TabPFN-3.5 with thinking off (`v3.5_default`, the hosted "3.5-Plus"): 8 estimators, softmax temperature
  0.9, `ignore_pretraining_limits`, no description, no categorical declaration.
* **Walk-forward, one season per sample.** Season Y in 2022–2026 is trained on the main-tour matches with odds of 2013
  to Y − 1, and predicted as stored and with A and B swapped. A match's forecast is the mean of the two orientations.
* **Seeds 0, 1, 2.** An arm's forecast is the mean of the seeds present for both arms of a comparison in every season.
  * The primary endpoint refuses to run without one such seed.
  * If the pilot's base seeds 0 and 1 return identical probabilities, the confirmation runs seed 0 only.
* **Stages:**
  * pilot: 2019–2021; base seeds 0 and 1, primary and literal seed 0;
  * confirmation: 2022–2026; the five arms with odds × 3 seeds;
  * diagnostic: 2022–2026; the two no-odds arms, seed 0.

  Every job runs once (`guard.py`). A re-run of a stage would take a new stage name.

## Population

Every scored comparison leaves out the matches with a player whose first Stage 0 match falls in the match's season
(audit B1). In 2022–2026 that is 92 of 23,819 test matches:
* the 73 women's matches of June–July 2026 whose players re-appear under new IDs with no history;
* 19 true debuts.

The full population is reported as a sensitivity.

## Endpoint and decision rule

**Primary endpoint.** `primary` against `base`, both tours pooled, 2022–2026 pooled, on the population above.

**Reading:**
* **better** if the 95% interval lies above 0;
* **worse** if it lies below 0;
* otherwise a **tie**, reported with the minimum detectable effect (MDE).

A tie with an MDE above 0.4 mLL is **inconclusive at the expected effect size**, not "no effect".

**MDE.** Fixed from the pilot before any confirmation call (`mde.json`):
* the seed-matched paired SE of `primary_s0` against `base_s0` on 2019–2021, on the scored population;
* times √(pilot matches / confirmation matches), times (z 0.975 + z 0.80) = 2.80.

It is conservative, because single seeds carry fit noise that the confirmation's three-seed means mostly remove.

**Secondary results, reported but not used to claim the idea:**
* per tour;
* each season as one sample (five gains, their mean with a t interval on 4 df, how many are positive);
* `literal`, `elo_only`, `switch_only`;
* every arm against the closing odds recalibrated on each fold's training matches;
* subsets: early surface season, both new, the rest, and grass (directional, with calendar-week intervals);
* the noise floor: base seeds against each other;
* the full population.

All of these are unadjusted, and labelled so.

**The diagnostic's readings.** Each pairs primary − base without the odds with primary − base with the odds:

| Without the odds | With the odds | Reading |
|---|---|---|
| better | tie | the information is real and priced |
| tie | tie | TabPFN does not use the representation (or both effects are below the MDE) |
| better | better | an edge beyond the price |
| tie | better | it helps only beside the price: check carefully |

## Interpretation limits stated in advance

* **Only the non-thinking model is tested.** Whether a result carries to TabPFN-3.5-Thinking is untested.
* **The base inputs were selected on 2022–2026 by earlier studies.** `primary` and `literal` drop two of them, so this
  slightly favours `base`.
* **The ablations have less power than the primary endpoint.** Their attribution of any effect will be weak.
* **2026 is not like the other seasons.** It is partial (January to the end of July), with more clay and grass than a
  full season.
* **The odds are closing prices.** They are tennis-data's average of archived quotes, not executable prices. A log-loss
  gain is not a betting return.
