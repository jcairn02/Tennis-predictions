# The main statistician's review of the audit

6 October 2026 · Response to [audit.md](audit.md), written before any TabPFN call.

**Key.**
* Log loss: lower is better.
* Gains are milli-log-loss (mLL), and positive means the named model is better.
* Brackets are paired 95% intervals over four-week blocks. A range that spans 0 is a tie.

## Verdict on the audit

I accept the audit's verdict and every blocking and should-fix item. I re-derived the three claims that would change
the test with my own code before acting on them (`verify_audit.py` in the session's scratchpad; the same quantities are
now written by the study's `evidence.py` and `build_frames.py`).

**B1, the 2026 identity split. Confirmed.**
* A player whose first Stage 0 match falls in the current season flags 73 women's matches in 2026: 0 from January to
  May, 55 of 297 in June and 18 of 181 in July. The IDs are new `wta:3xxxxx` ones.
* The same rule flags 0–5 matches per season and tour in 2013–2025.
* It flags 92 of the 23,819 test matches.

**S1, career counts and form beside the offset Elo. Confirmed.** Forward-chained over 2016–2021:

| Added beside the offset Elo | Men, no odds | Women, no odds | Men, with odds |
|---|---|---|---|
| Career counts | −0.75 [−1.41, −0.08], worse | −0.20 [−0.51, +0.10], tie | −0.13 [−0.23, −0.04], worse |
| Career counts capped at 20 | −0.25, tie | +0.08, tie | −0.07, tie |
| Last season's form | +0.17 [+0.00, +0.34], better by a hair | −0.06, tie | |
| Season counts + layoff | +2.56 [+1.36, +3.75], better | +3.83 [+2.53, +5.12], better | |

**S5.1, the offset as a shift. Confirmed.** For players with more than 160 matches on a surface the offset averages:
* men: clay +76.9 and hard +60.1;
* women: clay +60.2 and hard +48.0.

## Item by item

| Item | Decision | What changed | Note |
|---|---|---|---|
| **B1** identity split | **Accept** | `build_frames.debut_season` flags the matches by the audit's rule, the same in every season. Every scored comparison leaves them out; the full population is a sensitivity (`score.py`, `population` column) | Training is untouched, because 2026 is never a training season. Jobs, fingerprints and quotes do not change |
| **B2** power | **Accept, with a nuance** | The pilot writes `mde.json` before any confirmation call. It takes the seed-matched paired SE of primary against base on 2019–2021, scales it to the confirmation's size and gives the MDE at 80% power. Decision rule: better if the interval is above 0, worse if below, otherwise a tie reported with its MDE. Such a tie is "inconclusive at the expected effect size" when the MDE exceeds 0.4 mLL. Seed rule: if base seeds 0 and 1 return identical probabilities, the confirmation runs seed 0 only | The audit's 0.82 mLL comes from a boosting proxy. Boosting moves much more between input sets than TabPFN with the odds does: the two thinking fits differed by 0.015 log-odds (RMS) and their SE was 0.04 mLL. The pilot's own SE replaces the proxy. The single seeds make it conservative |
| **S1** composition of `primary` | **Accept** | `primary` = base − `elo_logit` − `surface_first` + `elo_overall` + the surface offset + the season pair + the layoff pair (58 columns). `switch_only` = base − `surface_first` + the two pairs (57). `elo_only` = base − `elo_logit` + `elo_overall` + the offset (55), so the two ablations decompose `primary`. `literal` keeps all four pairs (62): the owner's items as written | My principle 3 rested on the inexperience penalty measured against overall Elo. Beside the offset Elo the penalty is smaller, priced, and the counts made the fits worse. Another reason to drop them: career counts start in 2010 and drift (median 100 in 2013, 215 in 2025), so in a walk-forward the input means different things in training and test |
| **G2** the offset as its own piece | **Accept** | `elo_surf_offset` = (D_A − D_B) × ln 10 / 400 sits beside `elo_overall` (collinearity 0.98 before). The combined `elo_offset` column is gone | This is also the owner's idea more exactly: the overall rating plus its surface component |
| **S2** a lost seed silently drops a season | **Accept** | Each comparison uses the seeds present for both arms in every season, the same seeds for both arms. The primary endpoint refuses to run if that set is empty. Log losses are shown on identical rows with their counts. A test covers both behaviours | |
| **S3** the fit's bill | **Accept** | `guard.py` reads usage between fit and prediction. `dispatch.py` logs the fit and prediction tokens separately, and the served model and mode | |
| **S4** pilot mechanics | **Accept** | The pilot is read seed-matched, which the common-seed rule does on its own. Any re-run gets a new stage name | |
| **S5** text corrections 1–10 | **Accept all** | Applied to the amended strategy | 1. the offset shifts as well as specialises. 2. principle 3 withdrawn. 3. "re-anchoring with Stage 1's K". 4. the weight-by-bin gains are in-sample upper bounds. 5. career counts added to the tables. 6. the offset's gain by period. 7. the priced table rebuilt on one population with the recalibrated market and SEs (`evidence_priced.csv`). 8. the 31–34 quote is men only. 9. the probes. 10. the layoff cap neutralises the 2010 start |
| **G1** stronger probes | **Accept** | `pieces.py` now runs Stage 1's date-and-round probe on the anchored, offset and surface-blind passes, and a truncation probe on the switch quantities, beside the flip probe | |
| **G2b** the surface-blind control | **Accept** | Built in `pieces.py` (columns `DG_a`/`DG_b`) and scored in `evidence.py` (`evidence_beside_offset.csv`) | It makes principle 1 stronger: the gain is surface structure |
| **G3** pairs or difference + sum | **Agree** | Pairs kept | |
| **G4** subset intervals | **Accept** | Grass is labelled directional, and calendar-week intervals are reported beside the four-week ones | |
| **G5** housekeeping | **Accept** | A run never overwrites the registered quote. The HTTP timeout is out of the request's identity. The frame carries the raw season counts | |
| **G6** interpretation risks | **Accept** | Stated in the amended strategy and the report. The most important is that the base inputs were chosen on 2022–2026, which slightly favours `base` | |
| **G7** tune the offset on the recalibrated loss | **Decline** | None | It mirrors Stage 1's tuning, and the valley is flat. TabPFN rescales its inputs, so the offset's over-confidence (slope 0.915) cannot matter to the test |

## Additions of my own

* **The repair's alias IDs.** The feature-alpha repair's alias and conflict IDs touch 421 of the 23,819 test matches.
  Most are men's, spread over every season, and one or two rows per alias. The debut rule catches an alias only when
  its first row falls in the match's season.
  * This issue affects every arm alike through Elo, which the base already carries.
  * It is listed as a limit, not a reason to change the population.
* **The order of operations.** The audit's changes were made before any 2022–2026 result of any arm was seen. The
  pilot (2019–2021) runs after them. So everything here is still pre-registration.
