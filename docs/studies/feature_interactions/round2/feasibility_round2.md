# Round 2 · Feasibility rulings on the rebuttals and the new ideas

6 October 2026 · Feasibility auditor · Research evidence, not a decision. Data, timing and leak risk only; value and mathematics are the mathematical auditor's ([hypothesis family](hypothesis_family.md)).

**No results.**
* No column was related to `a_won`, and no price was compared with an outcome.
* The 2014–2024 values come from the round-1 augmented panel, with `a_won` dropped at load.
* For 2025–2026, only these were read:
  * schedule fields: the clock's es and lf, match and player ids, dates, rounds;
  * provenance: `source`, `has_box`, link-file ids, the override file's match ids.
* **Disclosure for the look ledger.** While checking the column layout of `data_continuity/slam_box_overrides.csv`, two rows were printed in full. They are US Open 2026 men's Q1 qualifying matches, which are not in the model frame, and the print showed their box scores and scores. Nothing used them.

**Coverage** is the share of matches with the column defined for both players. It is given as men / women, 2014–21 | 2022–24, in %. "Test n" counts 2025–26 model rows. Machine-readable copy: `data/studies/feature_interactions/round2/feasibility_round2.csv`. Scripts: `src/eda/feature_interactions/round2/feasibility/`. JSON outputs: `data/studies/feature_interactions/round2/feasibility/`.

## 1. Rebuttals of G2 verdicts

| ID | Ruling | One sentence, with the number |
|---|---|---|
| I-008 | **ACCEPT → pass** | Declared as its remainder after a projection on the 58 inputs fitted on 2014–2018 without outcomes. Out of the fit, in 2019–21, the remainder's SD is 0.205 (men) and 0.086 (women) match log-odds (verified; mechanics found 0.205 / 0.089). The R4 serve-point form z_spw leaves 0.24 / 0.20. Coverage 100 / 100 \| 100 / 100 |
| I-009, I-015 | **ACCEPT → pass** | The same remainder rule (finding 3) lifts deferrals that rested on R² alone. Coverage 100% |
| I-012 | **ACCEPT → pass** | With MEC-04's declared g, R² on the 58 is 0.922 (men) and 0.929 (women), under 0.95 (read from `round2/mechanics/checks.json`). Coverage 100% |
| I-060 | **ACCEPT → pass** | With event countries from the Stage 4 table plus the ITF id codes, and the 81 + 46-code continent map, every event in both players' last 42 days is mapped in 79 / 82 \| 75 / 88% (verified with that map; 1.8% of history rows stay unmapped) |
| I-074 | **ACCEPT → pass** | Continent-level offsets are defined for both players at 93 / 95 \| 91 / 95% of first-match rows. The ≥ 5-hour trigger touches only 1.9 / 1.3 \| 1.2 / 0.5% of matches (either player) |
| I-075 | **ACCEPT → pass** | Every part of Nov is defined for both players at 71 / 57 \| 72 / 57% of first-match rows. The indoor part binds, because women's indoor exists only for priced matches (tennis-data's Court). Later rounds have Nov = 0 by construction |
| I-085 | **ACCEPT → pass** | F = c·(`elo_overall` + `elo_surf_offset`), with c from price SDs (no outcome), covers 100% from 2014 |
| I-086 | **ACCEPT → pass** | Under S11, coverage is 100%. The quarter-final-on rows it multiplies (15–17%) have both previous prices in 99.6–99.9% of cases |
| I-051 Off | **ACCEPT (data)** | The off-site kernel with games-imputed minutes covers 100%. Its status as a hypothesis is the mathematical auditor's call |
| I-020 | **The auditor revises its own pass → kill (c)** | Round 1's 70% / 68% was any speed history. A recent change needs speeds in the player's last three matches, which both players have in only 10 / 10 \| 58 / 13%. This agrees with the mathematical audit and the originator |

## 2. The new ideas

| ID | Data (tables, columns) | Coverage % | Test n | Timing | Probe | Build h | Verdict |
|---|---|---|---|---|---|---|---|
| MEC-L1 serve–return link | surface IOS spw O, D | 100 all | 8,593 | IOS (clock-built) | no | 1 | **pass**, as a control or sensitivity only. As a column, R² is 0.986 / 0.961 (verified), so it fails novelty |
| MEC-K1 information-weighted Elo | Stage 0 results in each player's order; λ from surface IOS at earlier pool matches (1 elsewhere) | 100 all | 8,593 | safe; weights from clock-built IOS | recommended | 4 | **pass** |
| MEC-K2 the pair's realized character | box scores of earlier meetings; IOS at each meeting | defined 100%; meeting in 61 / 58 \| 59 / 57 | 8,593 | safe | no | 3 | **pass** |
| MAT-L1 later-round slope | model frame `in_round`; odds | 100 all | 8,593 | market | no | 0.5 | **pass** (near-duplicate of LIT-1's L) |
| MAT-K1 spw-only arm | surface IOS spw | 100 all | 8,593 | IOS | no | 1 | **pass** (a TabPFN arm) |
| MAT-K2 flexible-R² novelty rule | the 58 inputs | – | – | result-free | no | 2 | **pass** (a rule, not a column) |
| MAT-R1 fault detector | Stage 0 box scores by event, all levels with boxes | 100 (weights default 1) | 8,593 | **field statistic**: an event's flag from lf + 1; the venue prior for later rounds | **yes** | 8 | **pass** |
| MAT-R2 2025–26 shift | Stage 0 `source`, `tml_link` | counts | §4 | counts | no | 2 | **pass**: women none; men 264 → 144 test matches |
| LIT-1 later-round and high-profile slopes | `in_round`, level, draws | 100 all (L 53%, HP 22% of rows) | 8,593 | market | no | 0.5 | **pass** |
| LIT-2 fame asymmetry | fame (built in round 1); η | 100 all | 8,593 | safe | no | 0.5 | **pass** |
| C-1 sharp anchor | `stage1_odds` ps_a/b | 100 / 99 \| 100 / 99 | **5,054** | market | no | 0.5 | **pass**. In the test, Pinnacle ends in January 2026, and Betfair exists only in 2025–26 (untrainable) |
| C-2 rating against price × obscurity | Stage 0 rank; F | 100 / 100 \| 100 / 99.5 | 8,593 | safe | no | 1 | **pass** |
| INFO-1 own-result update | clock `rest_min`; previous match box score; IOS at its es | defined 100% (x = 0 elsewhere) | 8,593 | safe | recommended | 4 | **pass**, with a prevalence warning (§3) |
| INFO-2 late-formed qualifier price | entry codes; qualifying box scores; `onsite_n`, rest | defined 100%; subgroup 12.6 / 12.6 \| 13.3 / 14.6 | 8,593 | safe | no | 3 | **pass**: the qualifier's on-site box score in 87 / 85 \| 100 / 100% |
| BOD-L1 previous on-site set excess | Stage 0 previous match (sets, best of, status); clock | 100 (non-zero 67–69% either) | 8,593 | safe | no | 1 | **pass** |
| BOD-L2 career stage × price | age; η | 100 all | 8,593 | safe | no | 0.5 | **pass** |
| BOD-C1 fatigue-contaminated form | own Fat over the last 14 days (games-imputed) | 82 / 79 \| 84 / 80 | 8,593 | safe | no | 2 | **pass** |
| BOD-C2 staleness × price | rest days (own sequence); η | 100 all | 8,593 | safe | no | 0.5 | **pass** |

No new idea needs a kill or a deferral on data.

## 3. INFO-1: the clock's blind spot, verified

**What happens.**
* A result counts from lf + 1 (the decision of 5 October). On the model population, lf − es is:
  * 0 days (an exact local day) in 26% of matches;
  * 1 day in 68% (a UTC day from Flashscore-type sources);
  * 2–3 days in 6%.
* So when es ≤ lf of the player's previous match (rest ≤ 0), that previous result is outside the IOS inputs.

**The 36% holds for 2014–2021 and does not persist** (either player rest ≤ 0; `r2_extra.json`):

| Seasons | Men | Women |
|---|---|---|
| 2014–2018 | 33–37% | 46–48% |
| 2019 | 34% | 27% |
| 2020–2021 | 32% | 9%, 5% |
| 2022–2024 | 32%, 29%, 30% | 3%, 2%, 2% |
| 2025, 2026 (counts) | 26%, 20% | 1.1%, 0.6% |

Pooled over 2014–2021 it is 34.4% (men) and 36.9% (women). Per player-match it is 25–27%, which is 45% when the previous match was at the same event and under 2.3% otherwise.

**Why it collapses for women** (inferred): from 2019 the WTA API and the other exact local days give lf = es, so consecutive-day rounds have rest = 1.

**Consequences.**
* The blind spot is a property of the date sources, not of tennis.
* A women's signal found in 2014–2018 cannot recur in the test years.
* The model's IOS inputs are also fresher for women from 2020 than for men. **The meta-auditor should log this as a window shift.**

**Which per-player quantities from a player's own matches since the IOS cutoff are safe by construction and buildable.**

| Quantity | Includes the previous same-event match? | Status |
|---|---|---|
| The two-week profile (`form_*`, `formdef_*`, `adjperf_tpw_2w`) | **Yes.** The as-of rule counts earlier rounds of the same event at full weight. The value changes from one round to the next in 94.6% of 48,699 consecutive same-event pairs. The rest are previous matches without a box score | In the model; per player in `perplayer_form_2013_2024.parquet` |
| Elo (`elo_overall`, `elo_surf_offset`, `elo_games`), Stage 3 ratings (`ratings_iid`), `sets_14d`, `points_52w`, `surf_season` | **Yes** (the same time rule). Elo changes in 99.2% of those pairs | In the model; per player in `pieces`, `stage3_ratings` and round 1's load table |
| The previous match's own box score, with its IOS expectation at that match's es (INFO-1's u) | It *is* that match | Buildable for 95% / 97% (men) and 83% / 84% (women) of the players in the blind spot: previous match in the IOS pool and with a box score |
| The leak-proof IOS (22 inputs) | **No**, when rest ≤ 0 | By design; the gap INFO-1 fills |

Two cautions:
* u uses only that player's own match and IOS states already on the clock, so it is safe for that player. **Run `probe.py` on the finished column**: an opponent's IOS state enters the expectation.
* At bet time, the deployment fix (recompute IOS with each player's own last result) is leak-free for that player only.

## 4. R2-measure: the 2025–26 box-score faults, counts only

**Where the faults reach Stage 0** (pre-rebuild copy, which the frozen model frame was built from; provenance only):

* **Women's aces and double faults (TML, Dec 2024 – Feb 2026): no Stage 0 row is affected.** No women's row in that window is TML-sourced with a box score. Stage 0 took Sackmann's rows, and the official records side with Sackmann. MAT-R2's kill rule (contaminated share < 5%) is met for women.
* **Men's Slam first serves (TML, since about Aug 2025): 573 TML-sourced rows.**

  | Event | Rows | In the live tables since the rebuild |
  |---|---|---|
  | Wimbledon 2026, main and qualifying | 127 + 111 | Replaced by the official feeds |
  | US Open 2026, main and qualifying | 127 + 111 | Replaced by the official feeds |
  | Roland Garros 2026 qualifying | 97 | **Not replaced**: no Roland Garros feed on disk |

  US Open 2025, the Australian Open 2026 and Roland Garros 2026's main draw are Sackmann-sourced, so they are clean.

**Inputs affected (men only).**
* **15 of the 58 inputs:**
  * `form_first_in`, `form_first_won`, `form_second_won`, `formdef_first_in`;
  * the opponents' `form_rpw_first` and `form_rpw_second`, through the same counts;
  * `iosO_`, `iosD_` and `prod_` for first_in, first_won and second_won (9).
* Hold-based inputs only if those rows' service games are also off. TML agrees with the Slam feeds in only 75–92% of men's rows, so add `form_hold`, `form_brk` (opponent), `form_bp_faced_pg`, `formdef_bp_faced_pg` and the hold IOS as possibly affected.
* Serve-points-won inputs (`ratings_iid`, `points_52w`, `ios_points_short`) are not affected: the fault moves points between first and second serves.
* **Candidates touching these statistics:** I-004 (σ4), I-008 / I-014 / I-015 (first serves in, first- and second-serve points won), I-016, I-022, I-018's styles and MAT-R1.
* Candidates on the serve-point IOS are immune: MAT-K1, z_spw (R4), MEC-L1, I-001–I-003.

**Exposure of the test matches** (either player has affected rows in his own box-score history before the match):

| Data version | 104-week window, any affected row | 104-week window, affected share > 5% | 6-week window |
|---|---|---|---|
| Frozen frame (pre-rebuild) | 264 of 4,394 men's matches | 16 | 264 |
| Live tables (after the rebuild) | 144 | 0 | 74 |

Women: 0 everywhere. The IOS solve is joint, so affected rows also nudge other men's first-serve ratings slightly.

**Clean sources on disk.**
* 476 of the 573 rows are linked to the Slam feeds: the Wimbledon and US Open rows, already used by the live Stage 0.
* SofaScore links 572, but its first serves run high by 0.4–0.7 per player (data continuity), so it is not clean for this statistic.
* **No clean source exists for the 97 Roland Garros 2026 qualifying rows.**

**Suggestion for M2.**
* Pre-register that the final test's inputs are rebuilt from the live, corrected Stage 0. On 2013–2024 model matches it equals the pre-rebuild copy except for 7 minute values (round 0, §5.3), so training rows do not move.
* Down-weight or exclude the 97 Roland Garros 2026 qualifying rows in the histories (MAT-R1 / MAT-R2).

## 5. Other notes

* **Training-period faults to log** (MAT-R1's detector, consistent with round 0's list):
  * Roland Garros 2022 qualifying, women: +6.5 pp first serves in. Round 0 listed only the men.
  * The Paris Olympics 2024: +8.2 pp.
  * The Bratislava Challenger in most years.
* **Ruled elsewhere.** The withdrawals asked for (I-034, I-081, I-087) and the block changes are the mathematical auditor's decisions; they raise no data issue.
