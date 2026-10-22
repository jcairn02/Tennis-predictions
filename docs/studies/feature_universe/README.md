# The feature universe

7 October 2026 · Written for the owner and for a future feature-selection study · Research evidence, not a decision.

This is the **menu, not the meal**: every candidate input from which a future feature-selection process could rebuild the best model (local TabPFN-3.5, 58 inputs), with where it lives, whether it is safe in time, how much of the model population it covers, what earlier studies found, and a suggested priority. It includes the near misses of the [feature-interactions study](../feature_interactions/next_candidates.md). No selection algorithm was designed or run. No 2025–2026 result was read: the coverage of 2025–2026 counts rows and missing values only.

**Deliverables** (in `data/studies/feature_universe/`).
* `store.parquet`: every built candidate materialised on the model population, one column per encoding (section 0). Gitignored (over 50 MB); [rebuild](#rebuild).
* `store_registry.csv`: one row per store column: its kind, swap partner, source, flags, copies and coverage.
* `menu.csv`: **the selection pool**, one row per distinct usable store column, with its catalogue row, near-miss tier, 2025–2026 status and suggested priority.
* `universe.csv`: one row per conceptual feature (columns below), built or not.
* `build/`: `coverage_keys.csv`, `validation.json`, `duplicates.json`.
* This report: how the universe is organised, each family's candidates, the near misses, what is built, buildable or needs new data, the exclusions, and what a selection process must handle specially.

Code is in `src/eda/feature_universe/`:
* `perplayer_2026.py` and `build_store.py` build the store and its registry;
* `catalogue/` holds the catalogue:
  * `spec_*.py` and `fi_common.py`: the hand-written rows;
  * `coverage.py` → `coverage_keys.csv`;
  * `build_universe.py` → `universe.csv`, `menu.csv` and `validation.json`;
  * `duplicates.py` → `duplicates.json`.

Tests are in `test/feature_universe/`.

**Added 8 Oct 2026, at the owner's request:** U-330, the share of each player's last-year matches below the main tour, from the [event-levels study](../event_levels/README.md) (section 2, "Event-levels study"). Every earlier column, catalogue row, menu row and coverage figure is unchanged (section 8).

**Refreshed 14 Oct 2026, at the owner's request:** U-126, the form evidence: how much box-score evidence stands behind each player's two-week form, exactly as the current best model weighs it (five `fe__` columns; section 2, "Two-week profile"; its admission card is in section 9). Every earlier column and coverage figure is unchanged. Of the catalogue, only U-126's own row changed, and with it the priority of its four 7 Oct menu columns (section 8).

**Validation (observed, `validation.json`).**
* Every one of the store's 784 columns is referenced by a catalogue row, directly or through a copy, and every name in `store_columns` exists.
* All 58 model inputs are covered, by 56 rows: the two pair inputs (`surf_season_a/_b`, `surf_layoff_a/_b`) are one row each.
* 71 rows have no store column: features held only in other tables, or not built. Their `source` names the table and column.

## 0. The store and the menu

**What the store holds** (observed). One row per match of the model population (63,737), keyed by `match_id` with `tour`, `season`, `tournament_date` and `debut_season`. It has 784 feature columns and no result column.

| Prefix | What | Columns | On the menu |
|---|---|---:|---:|
| `m__` | the current best's 58 inputs, exactly as in the model frame | 58 | 58 |
| `alt__` | inputs replaced on 6 Oct, and alternatives: the Elo blend, surface-first, surface-only Elo, pooled IOS, surface deviations, decided and offset TTT | 46 | 46 |
| `pp__` | each player's own pre-match values (pairs), with two-week form, sets and age rebuilt to 2026 | 204 | 196 |
| `rt__` | Glicko-2, TrueSkill and correlated-surface ratings run match by match, with their uncertainty; five systems' forecasts | 19 | 18 |
| `ad__` | opponent-adjusted profiles, A − B, over 52 weeks and decayed | 60 | 21 |
| `sl__` | serve speed per player, only where real speed data exist | 14 | 14 |
| `mk__` | market-internal: Pinnacle, the best price and Bet365 against the average; overround; dispersion | 5 | 5 |
| `fi__` | the interactions study's screen, deployment and member columns | 123 | 92 |
| `fp__` | its per-player and match-level intermediates, including venue pace, indoor for both tours, days to the next Slam and matches since a return | 200 | 124 |
| `lv__` | the 17 level sums (A + B) | 17 | 17 |
| `ds__` | pre-declared descriptive columns | 8 | 7 |
| `kn__` | known-null placebos | 13 | 2 |
| `ctx__` | match context: the model's six, plus draw size, week and month | 9 | 3 |
| `el__` | the event-levels study's history composition: each player's share of last year's matches below the main tour, and A − B (added 8 Oct) | 3 | 3 |
| `fe__` | the form evidence (U-126 refreshed, 14 Oct): each player's decayed count of earlier box-score matches as the model weighs it, the form's shrinkage share, and A − B of the share | 5 | 5 |
| **All** | | **784** | **611** |

**Kinds and sides.**
* `diff` is A − B and flips sign when the players swap.
* `pair` is A's and B's own values, exchanged on a swap; `partner` names the other side.
* `context` is unchanged by a swap.

Side A is Stage 0's `player_a_id` (the pre-rebuild copy), as in the model frame.

**Checks** (observed; `store_build.json` and `test/feature_universe/`).
* `m__` equals the model frame's inputs exactly. The per-player pairs reproduce the model's A − B inputs: the largest gap is 7 × 10⁻⁸ over 2013–2026, and 2013–2024 is identical to the frozen rebuilds.
* **Swap behaviour.** Every screen, deployment and member column behaves as its kind when A and B swap, and so does every match-level intermediate, rebuilt on the swapped panel. There were 0 failures.
* **Other studies' tables use the same side A.**
  * The ratings' rated-match counts equal the panel's on every row.
  * The profile and serve-speed tables' market log-odds equal the model's price exactly.
* **No result is read.** The panel is loaded without its result column, and table reads refuse result columns by name.

**Copies and the menu.** The builders share intermediates, so one series often sits under several names. The registry marks each column's representative, chosen by group in the order m, alt, pp, rt, ad, sl, mk, lv, ctx, fi, fp, el, fe, ds, kn:
* 142 exact copies and 2 negated copies (`canonical`, `dup_sign`);
* 28 near copies (`near_dup_of`): |r| ≥ 0.999 on common rows, adding at most 0.5% of rows the representative lacks, so the both-tours indoor flag is not a copy of the men-only one;
* 3 columns constant within each tour (`degenerate`), two of them also copies;
* 5 pseudo-pairs re-registered:
  * `f07_k3`, `h2hn` and `bd9b_mpp` are the same for both players, so they are context;
  * `f08_bigpt` and `h2hres` are split differences (+d/2, −d/2), so they are diffs.

The remaining 611 columns form the menu (`menu = 1`). Three copies worth knowing:
* The model's two-week form inputs are exactly the decayed opponent-adjusted forms. 28 of the 30 `ad__…_decayed` columns are copies; only the serve-points-won pair is new.
* `fi__I-084__s` is `lv__elo` rescaled.
* The KN placebos equal their `alt__` twins.

**Flags.**
* **Base-dependent (10 columns).** They read the current best's 2014–2024 forecast: the screen columns of I-042, B-ANCHOR, B-RECAL (two), B-REPUTE and LIT-2, and the members I-037, I-040, I-041 and I-055. Recompute them with a new model's own out-of-sample forecast.
  * Eight are missing in 2013 and in 2025–2026, where that forecast does not exist.
  * **B-ANCHOR's and B-REPUTE's screen columns do have values there, but they mean something else.** They are sums whose forecast-dependent member (I-037, I-055) drops out where the forecast is missing.
* **Market-internal (8 columns):** the five `mk__` columns and B-ANCHOR's three.

**`menu.csv`, the selection pool.** One row per menu column with:
* the column, group, kind, partner and store flag;
* its defining catalogue row (the most specific one), with that row's name, family, status, timing, near-miss tier and priority;
* every catalogue row that references it or a copy;
* `seen_2025_2026`: yes if any of those rows was related to 2025–2026 results;
* its copies (`aliases`) and its coverage.

Counts:
* priority: high 141 (mostly the incumbents and their per-player pairs), medium 86, low 366, exclude 18;
* near-miss tier: A 20, B 15, C 53, D 38;
* seen on 2025–2026: yes 367, no 244.

**What is not in the store.** 71 catalogue rows:
* 39 built features left in their own study tables, all suggested low or exclude (Stage 4 aggregates, shot-level families, the frontier, splits, weekly Glicko-2);
* 21 buildable from disk, of which two are medium: the fatigue-adjusted form (U-127, needs a design) and the new serve-speed sources (U-199, need a pipeline);
* 6 leaking, 4 needing new data, and the Polymarket price (the venue to bet at, not an input).

### Rebuild

```
./python.sh src/eda/feature_universe/perplayer_2026.py             # about 1 minute
./python.sh src/eda/event_levels/universe_columns.py               # seconds (the el__ source; needs the event-levels
                                                                   # study's history.parquet and an existing store)
./python.sh src/eda/feature_universe/form_evidence.py --store      # about 4 minutes (the fe__ source; reads the
                                                                   # template_2026-10-13 build tree C:/Users/zerom/tnr_gaps,
                                                                   # read only; its checks need an existing store)
./python.sh src/eda/feature_universe/build_store.py                # about 8 minutes
./python.sh src/eda/feature_universe/catalogue/coverage.py         # a few minutes
./python.sh src/eda/feature_universe/catalogue/duplicates.py       # seconds
./python.sh src/eda/feature_universe/catalogue/build_universe.py   # seconds
./python.sh -m pytest test/feature_universe -q
```

`build_store.py --registry-only` re-annotates the registry from an existing store in seconds. `build_store.py --append-el` adds the three `el__` columns to an existing store without touching the others (how they were added on 8 Oct); `--append-fe` does the same for the five `fe__` columns (14 Oct). The full rebuild builds `fe__` last too, but it was not re-run on 14 Oct.

## 1. How the universe is organised

**One row per conceptual feature.** A row holds every encoding of one idea: the model's A − B input (`m__`), each player's value (`pp__`, `fp__`), and the study's deployment column (`fi__`). A selection process can then choose the encoding: a difference, a pair, or a symmetric level.

There are two exceptions.
* **Raw building blocks** (days since the last match, matches here, venue pace, the pair's Elo sum) have their own rows in the load, context and level families, beside the study's rows that combine them (section 4).
* **One duplicate is deliberate.** "Pinnacle close as the anchor" (U-003) reuses `m__odds_logit` and `mk__ps_minus_avg`, because choosing the anchor is a separate decision from adding Pinnacle's deviation.

**Columns of `universe.csv`.**

| Column | Content |
|---|---|
| `feature_id` | U-001 … U-330, in family order (the event-levels family, added later, comes last so no earlier id moved) |
| `name`, `family`, `subfamily`, `definition` | what it is (subfamily = the study's block id for its members) |
| `kind` | diff (A − B, flips sign when A and B swap), pair (A's and B's values), context (symmetric) |
| `source` | table and column, or builder module and function |
| `store_columns` | names in the store; `x_a/_b` means both sides; `lv__*` is a pattern; blank = not in the store |
| `menu_columns` | the row's store columns as menu representatives (copies replaced by the column they copy) |
| `status` | in_model / built_not_in_model / buildable_from_disk / needs_new_data / excluded_leaky / market_internal |
| `timing_class` | safe by construction / leak-proof clock + probe passed / leak-proof clock, probe needed / leaking |
| `coverage_2013_2021`, `coverage_2022_2024`, `coverage_2025_2026` | share of the model population's matches where the value exists for both players (for a pair), pooled when the tours agree within 0.02, else `M x / W y` |
| `evidence` | the best earlier results, each with its direction key |
| `near_miss_tier` | A / B / C / D / none, from `feature_interactions/next_candidates.md` |
| `seen_2025_2026` | yes if any earlier study related it to 2025–2026 results |
| `caveats` | data faults, duplicates, store flags |
| `priority_suggestion` | high / medium / low / exclude, with a one-line reason |

**Population.** The 63,737 matches of the frozen 58-input model frame: men 19,331 / women 20,587 (2013–2021), 7,958 / 7,268 (2022–2024), 4,394 / 4,199 (2025–2026). Coverage counts a value as present when it is finite. For a decaying column such as rust, "present" means defined, not non-zero.

**Timing.** "Safe by construction" follows each player's own matches in order. Market prices and match context are also in this class: they are known before the match and carry no result. A "leak-proof clock + probe passed" feature combines different players' results on the match clock and passed a cut probe:
* the surface IOS (`match_timing/probe.py`);
* the study's field statistics: venue pace, I-029, B4's fields, I-042's hazards and I-025's walk-forward fit;
* the body analyst's eleven rows (`meta/checkpoint_1.md` §2).

**Evidence keys.** Every number keeps its source's direction. Each string opens with its key:
* `[z: + = declared direction]`: the feature-interactions screen on 2014–2024, beyond the current best ("model") or the closing price ("price");
* `[mLL: + = feature or arm better]`: milli-log-loss gains, where a tie means the interval spans 0;
* `onE / onM / onP`: the round-0 register's tests, i.e. mLL added to surface Elo, to the average close, or to calibrated Pinnacle;
* `[Wald]` rows: two-sided p.

Round 0 warned that almost every earlier result was read on windows that include 2025–2026 (`feature_interactions/round0/inventory.md` §3). Hence `seen_2025_2026`.

**Counts by family and status** (rows):

| Family | in model | built, not in model | buildable from disk | needs new data | excluded (leaky) | market-internal | All |
|---|---|---|---|---|---|---|---|
| market | 1 | 0 | 2 | 2 | 0 | 7 | 12 |
| ratings | 4 | 26 | 0 | 0 | 5 | 0 | 35 |
| long-memory profile | 23 | 37 | 0 | 0 | 0 | 0 | 60 |
| two-week profile | 17 | 2 | 1 | 0 | 0 | 0 | 20 |
| load and schedule | 3 | 31 | 1 | 0 | 0 | 0 | 35 |
| player background | 2 | 12 | 4 | 0 | 0 | 0 | 18 |
| context | 6 | 9 | 1 | 1 | 0 | 0 | 17 |
| shot and point level | 0 | 10 | 6 | 1 | 1 | 0 | 18 |
| level sums | 0 | 19 | 0 | 0 | 0 | 0 | 19 |
| feature-interactions study | 0 | 89 | 6 | 0 | 0 | 0 | 95 |
| event-levels study | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| **All** | **56** | **236** | **21** | **4** | **6** | **7** | **330** |

**Priority suggestions.**
* 59 high: 53 incumbents and 6 new rows (section 7).
* 41 medium, 197 low, 33 exclude (U-126 moved from low to medium on 14 Oct).

**Seen on 2025–2026.** 160 yes and 170 no.
* Of the feature-interactions rows, five are seen: B-INJ's four, and I-084 (U-256), through the pair-strength study.
* Of the level sums, only the Elo sum (U-231) is seen, through the same study.

## 2. The candidates, family by family

IDs refer to `universe.csv`. ★ marks a near miss (tier in brackets). "Store" names the store prefix where one exists.

### Market (U-001–U-012)

* **U-001 closing price** (`m__odds_logit`): the average close, de-vigged. The anchor; in the model.
* **Book differences** (market-internal, `mk__`):
  * ★ U-002 Pinnacle minus average [A];
  * U-003 Pinnacle as the anchor [A];
  * U-004 best price minus average [C];
  * U-005 Bet365 minus average;
  * U-006 the average's overround;
  * U-007 cross-book dispersion [C].
* **Other books and venues**:
  * U-008 Expekt, Ladbrokes and Stan James: these stop in 2018.
  * U-009 Betfair: 2025–2026 files only.
  * U-010 opening prices and line movement: no history before 2025.
  * U-011 the Polymarket price: the betting venue, 2025–2026 only.
  * U-012 Polymarket flow: 2025–2026 only.

### Ratings (U-013–U-047)

* **In the model**:
  * U-013 overall Elo;
  * U-014 surface-offset Elo;
  * U-015 games-weighted Elo;
  * U-016 the iid serve/return matchup (`ratings_iid`).
* **Per-player parts and reliability** (`pp__`):
  * U-017 Stage 3 serve and return ratings;
  * U-018 their uncertainty;
  * U-019 their evidence;
  * U-020 the iid serve-point probability;
  * U-021 the tour × surface baseline;
  * U-022 rated matches (Elo N);
  * U-023 career surface matches (NS, KN-SURFCAREER).
* **Variants built but not in the model**:
  * U-024 the replaced Elo blend;
  * U-025 surface-only Elo (KN-ELOSURF);
  * U-026 Elo without retirements;
  * U-027 anchored and surface-blind Elo;
  * U-028 Elo change over 26 or 52 weeks;
  * U-029 points-weighted Elo;
  * U-030 the rank–Elo gap;
  * U-031–U-035 Glicko-1, Glicko-2 (match by match, and weekly), TrueSkill, and correlated-surface Glicko/TrueSkill. The Glicko-2 RD and volatility are the only per-player rating volatilities on disk. The match-by-match systems are in the store (`rt__`); the weekly Glicko-2 is not (dominated).
* **TrueSkill Through Time, leak-proof**:
  * ★ U-036 the decided TTT, `alt__ttt_logit` = `kn__KN-TTTLOGIT` [A]: a swap test, not an addition;
  * U-037 the offset TTT's overall part;
  * U-038 its surface part (= `kn__KN-TTTOFF`);
  * U-039 its counts.
* **Excluded as leaking**:
  * U-040 weekly TTT;
  * U-041 Bradley–Terry;
  * U-042 MESR;
  * U-044 revaluation;
  * U-047 the weekly stage-B IOS.
* U-043 strength of schedule is **unsettled**: its code follows each player's own sequence, but its script is on CLAUDE.md's leaking list. Run `probe.py` before use.
* **From the study's builders**:
  * U-045 career-peak Elo;
  * U-046 Elo at the return from a break.

### Long-memory profile (U-048–U-107)

* **Surface IOS in the model** (U-048–U-068): offence O, defence D and the matchup product for seven statistics (ace, df, first_in, first_won, second_won, hold, bp_saved). They are on the leak-proof clock, probe passed. Per player: `pp__ios_srfO_<s>`, `pp__ios_srfD_<s>`.
* **U-069 spw surface IOS** (O and D per player): the serve-point profile the 58 lack [D, through I-008].
* **Pooled IOS** (U-070–U-077): `alt__iosO_cur_<s>`, `alt__iosD_cur_<s>`, `alt__prod_cur_<s>` for the 8 statistics. Replaced on 6 Oct.
* **Surface deviations** (U-078–U-085): E (serve) and F (return) by statistic, `alt__sdevO/D_<s>`, which equal KN-SDEV's eight columns, a known null.
* U-086 the surface net shift (KN-SNET): equal to its placebo.
* **In the model**: U-087 the short-memory IOS points matchup; U-088 the 52-week points matchup.
* **Stage 4 aggregates** (U-089–U-094): 21 statistics × 5 forms, and the matchups. They duplicate incumbents.
* **Opponent-adjusted profiles** (U-095–U-098):
  * adjperf/adjdef over 52 weeks (`ad__…_52w`, 17 distinct);
  * the career (dominated, not stored);
  * the decayed forms (`ad__…_decayed`, medium). Observed: these are the model's own two-week form inputs, except the serve-points-won pair;
  * opponent-strength splits (closed).
* U-099–U-101: market-anchoring surface statistics.
* **Predictive frontier** (U-102–U-106). The `pf_event_*` speed × style is a field statistic that was never probed. Venue pace is its leak-proof analogue.
* U-107: last season's surface form.

### Two-week profile (U-108–U-127)

* **In the model** (U-108–U-124):
  * twelve `form_<s>`;
  * four `formdef_<s>`;
  * `adjperf_tpw_2w`.
* Each has per-player columns `pp__form_<s>_a/_b`, rebuilt for 2013–2026 (`perplayer_form_2013_2026.parquet`).
* **Built beside them**:
  * U-125 the 52-week level of the points form [C], so a model can form the short-minus-long gap itself;
  * U-126 the form's evidence and shrinkage [D]. **Refreshed on 14 Oct 2026** with the model's own weights (`fe__`, built by `form_evidence.py` on template_2026-10-13's tables):
    * `fe__sw_a/_b`: each player's decayed count of earlier box-score matches behind the two-week form, Stage B's step-3 weight sum for total points won (half-life 2 weeks; the level layer's weights for men, ITF box scores 0; 0 without one). With it, the model's `adjperf_tpw_2w` is rebuilt bit for bit;
    * `fe__r_a/_b`: the share of the raw two-week mean that the form keeps, sw / (sw + K3), K3 10 for men and 20 for women;
    * `fe__r_diff`: A − B of that share;
    * the 7 Oct builds (`fp__f07…s0`, `fp__f13…shr`: no level layer, the 30 Sep tables) stay for B6 and B7. Select `fe__`.
  * U-127 a fatigue-adjusted form (buildable) [C], meant to replace the raw form, not to be added to it.

### Load and schedule (U-128–U-162)

* **In the model**:
  * U-128 sets in 14 days;
  * U-129 the surface-season pair;
  * U-130 the surface-layoff pair.
* U-131 the replaced `surface_first`.
* **Raw building blocks of the strongest near miss (I-043 rust)**:
  * ★ U-132 days since the last match, any level [A]. Five near-identical copies are stored (`pp__rest_days`, and `fp__…rest` in f20, f10, f13 and f17).
  * ★ U-133 break length beyond the field's norm, U [A].
  * ★ U-134 matches since the return [A], `fp__f26_impairment__ret_n` (with the break's length in days, `ret_gap`, under U-133).
  * U-135 the rust state itself [A, seen].
  * U-136 injury-return flags; U-137 within-event serve decay [C], which is fault-exposed.
* ★ **U-138 matches already played at this event** [A]: the raw form of B11's On.
* **Load**:
  * U-139 the fatigue kernel (τ 3 days; eight identical copies);
  * U-140 its imputed share;
  * U-141 off-site load;
  * U-142 the previous on-site match's extra sets;
  * U-143 past fatigue [C];
  * U-144 the season odometer [C];
  * U-145 the recovery trait [C];
  * U-146 pace (`bd9b_mpp` is the same for A and B: a norm, so context);
  * U-152 the 21-day fitness kernel;
  * U-161 ACWR and team ties (sensitivities, not built).
* **Arrival** (B10's raw parts):
  * U-147 a deep run at the previous event;
  * U-148 travel;
  * U-149 last week's title and the first match here;
  * U-150 consecutive weeks played and weeks away;
  * U-151 jet lag.
* **On-site**: U-153 novelty of conditions; U-154 cold start [C]; U-155 the indoor-switch state.
* **Stage 4 and earlier studies**:
  * U-156 minutes and sets over 7 or 14 days;
  * U-157 the previous match's length and early end;
  * U-158 matches played;
  * U-159 late decline and grinder (closed);
  * U-160 the frontier's recovery context.
* U-162 the post-Slam letdown [B].

### Player background (U-163–U-180)

* **In the model**: U-163 age; U-164 age² (redundant for TabPFN given the per-player ages).
* **Body**:
  * U-165 height. Women's coverage for both players is 64% in 2022–2024 and 39% in 2025–2026.
  * U-166 left-handed;
  * U-167 record against the opponent's hand;
  * U-168 one-handed backhand (men only, static);
  * U-169 weight and turned-pro year: excluded, because the weight is today's, not at match time.
* **Nation and rank**:
  * U-170 country and home (categorical, not stored);
  * U-171 ranking (medium: one of the few positives beyond the price, for women);
  * U-172 ranking points;
  * U-173 the filled rank and the unranked flag;
  * U-174 rank trajectory and points to defend (buildable from the weekly rankings).
* **Draw**: U-175 seed; U-176 entry type.
* **Reputation**: U-177 fame [D].
* **Health**: U-178 the in-match retirement hazard; U-179 a WTA physio treatment in the previous match, which more than doubles the next retirement or withdrawal but moves results too little.
* U-180 head to head (Stage 4 and raw).

### Context (U-181–U-197)

* **In the model**: U-181 tour, U-182 surface, U-183 level, U-184 indoor, U-186 best of, U-187 round. `ctx__` equals `m__` for all six. The model's indoor flag is **men only**: women are 0% in `m__indoor` and in the store's `ctx__indoor`.
* U-185 indoor for both tours, `fp__f09_venue__f09_indoor`: Stage 0's flag, else tennis-data's Court field, else the event's majority.
* **Calendar**:
  * U-188 draw size;
  * U-189 week;
  * U-190 month;
  * U-191 Slam proximity [B], `fp__f19_motiv__nslam_days`: days to the tour's next Slam main draw (the planned "within 8 days" is `nslam_days ≤ 8`).
* ★ **U-192 venue pace** [A], `fp__f09_venue__f09_ve`: the venue's leak-proof ace excess.
* **Other venue features**:
  * U-193 indoor deviations (failed their gate);
  * U-194 attention and crowding;
  * U-195 start time of day;
  * U-196 altitude, weather, balls and court speed (not held);
  * U-197 the clock's width (a data-quality flag).

### Shot and point level (U-198–U-215)

* **Serve speed**:
  * U-198 the stored histories (thin before 2022). The men's 14-day speed change is the one point-level signal that replicated (point_sequence, 2025–2026 untouched).
  * U-199 the new 2021–2026 sources (ManTennisData, decrypted AO/RG), not yet a feature.
* **Shot-level families** (U-200–U-204, U-214), all built in `shot_level/stage3_sides` and prior-filled (use the `|has` flags):
  * rally length;
  * net play;
  * point endings;
  * placement;
  * pressure and after-loss excess.

  Against the close, 0 of 280 shot-level rows cleared the line.
* **Clutch**:
  * U-205 big-point return skill (Slam point files);
  * U-206 resilience (failed its gate);
  * U-207 tiebreaks and deciding sets.
* **Point sequences** (U-208–U-212, `point_sequence/sequences.parquet`, 19.17M points):
  * momentum and streaks (closed);
  * finishing form (inconclusive);
  * men's within-set serve clustering (weak);
  * women's tempo (closed);
  * the full-depth serve/return state.
* **Not usable**: U-213 tracking and win-probability feeds (too thin); U-215 post-match anatomy (history only).

### Level sums (U-216–U-234)

* **U-216 the H-S2 arm** [C], with its members U-217–U-230: the 14 surface-IOS sums (`lv__iosO_<s>`, `lv__iosD_<s>`).
* ★ **U-231 the pair's overall Elo sum** (`lv__elo`) [A]: the symmetric form of I-084's reversed slope. Tested as a 59th input on 2025–2026 by the pair-strength study: a tie leaning worse.
* U-232 the age sum; U-233 the load sum.
* **U-234 pair serve dominance**: kappa_pair, the leverage form of the spw IOS sums. The raw sum is buildable from U-069.

### The feature-interactions study (U-235–U-329)

**Layout.** Each screened hypothesis is a block row, with its screen column (`fi__<hid>__x`, `__x0…` for Wald rows, `__s` for a price-slope modulator) and its result on 2014–2024. Each block is then decomposed into its member columns, the TabPFN deployment columns `fi__<hid>__<column>`.

**Single-column hypotheses** (one row each):
* U-235 I-008, with its four sensitivities U-236–U-239 (`ds__I_008_*`);
* U-254 B-VENUE (I-072);
* U-255 I-036 (obscurity) and U-256 I-084 (pair prominence), both reversed;
* U-257 I-049;
* U-258 B-FLB;
* U-259 B-LEVER;
* U-260 I-042;
* U-261 I-082;
* U-266 B-ANCHOR;
* U-267 B-RECAL;
* U-272 LIT-2;
* U-285 I-053;
* U-252 B-AGE (I-070);
* U-253 B-CLUTCH (I-026);
* U-322 B-STATE (BOD-C1).

**Blocks and their members:**

| Block | Members (rows) |
|---|---|
| B2 (U-240) | I-012 shield, I-013 e_ace |
| B3 (U-243) | I-016 risky second, I-022 kick vs short |
| B7 (U-246) | I-023, I-031, I-032, I-048 E, I-048 F |
| B6 (U-262) | I-033 flux, BOD-L2 age distance, U_rest |
| B-REPUTE (U-268) | I-071, I-083, I-055 |
| B-INFO (U-273) | I-080, C-2, INFO-2 |
| B-OVERREACT (U-277) | I-025 luck, I-085 drift, I-086 narrative, I-091 raw head to head |
| B-MOTIV (U-282) | I-089 pre-Slam effort, I-090 post-Slam letdown |
| B-LOAD (U-286) | I-052 dFat, I-051 Off |
| B-PREV (U-289) | BOD-L1, I-056 |
| B9a (U-292) | I-024 h × Fat, I-024 h × age, I-058, I-061 |
| B9b (U-297) | I-063, I-065, I-066 |
| B10 (U-301) | I-059, I-088, I-060, I-074 |
| B11 (U-306) | I-051 On, I-075, I-076 (with their `ds__B11_member_*` copies) |
| B-SWITCH (U-310) | I-046, I-047 style, I-047 age, I-050 |
| B-INJ (U-315) | I-043, I-044, I-045 |
| B-HOME (U-319) | I-078, I-079 |
| B-STATE (U-322) | BOD-C1 (U-322), INFO-1 (U-323, descriptive, false premise) |

**Gate-dropped members** (U-324–U-329, buildable, never screened): B4's I-018, I-019 and I-021; I-009; I-028 and I-029 (B5); I-068. They failed pre-declared result-free reliability gates, so they are listed as "exclude".

### Event-levels study (U-330, added 8 Oct 2026)

* **U-330 share of the last year's matches below the main tour** (`el__low_share_diff`, A − B; per player `el__low_share_a/_b`). Each player's share of their played matches in the previous 365 days that were in tour or Slam qualifying, at Challengers or WTA 125s (main draw or qualifying), or at ITF events. Built from each player's own earlier matches: safe by construction. Coverage 99.9% (2013–2024), 99.4% (2025–2026).
* **Why it is here.** The [event-levels study](../event_levels/README.md) found that the average close and Pinnacle under-rate players arriving from lower levels. Beside the price's log-odds its coefficient is +0.18 [+0.09, +0.27] on 2020–2024, where it was found, and +0.09 [+0.02, +0.16] on 2013–2019, which replicates it. It is not match volume.
* **What tied.** As a 59th TabPFN input it gained +0.06 [−0.10, +0.23] mLL over the current best (both stages, 2020–2024); as a third walk-forward stage-2 term, +0.08 [−0.35, +0.50]. Both were tested on the seasons where the lead was found.
* **For a selection process.** Unseen on 2025–2026. Test it beside last year's win share (with both in, the share's coefficient rises to +0.18 and win share's is −0.25 [−0.45, −0.05], 2013–2024; the win share is not yet in the universe), and as a stage-2 term the way the serve speed is used. Its value differs by level: the price's coefficient is largest at the 500s (+0.41) and zero at the 1000s.

**Status.** The study's rows are `built_not_in_model`, except the six gate-dropped members, which are `buildable_from_disk`. Every block member is now stored apart as `fi__<hid>__m_<member>`; where a member equals a deployment column, the registry marks it a copy.
* None is seen on 2025–2026 except B-INJ and its three members, and I-084 (the pair-strength study).
* Every stored `fi__` column is built for 2013–2026, except the base-dependent ones (section 0).
* Six are flagged **base-dependent** by the store: I-042, B-ANCHOR, B-RECAL (×2), B-REPUTE and LIT-2 read the current best's 2014–2024 forecast. They must be recomputed with a new model's own forecast. I-042, B-RECAL and LIT-2 are missing in 2013 and in 2025–2026.

## 3. Near misses (from `feature_interactions/next_candidates.md`)

Read them with their base rate: about 11 of 34 members would reach |z| ≥ 1 by chance. Only Tier A and coherent mechanisms stand out.

| Tier | Rows | What a from-scratch model should get |
|---|---|---|
| **A** I-043 rust | U-132, U-133, U-134 (raw); U-135, U-315, U-316 (built, seen) | days since the last match, break length and matches since the return, as raw per-player inputs beside age (B-INJ's other members diluted it; tied on 2025–2026) |
| **A** I-084 reversed | U-231 `lv__elo`, U-256 `fi__I-084__s` | **since tested and not confirmed**: the [pair-strength study](../pair_strength/README.md)'s one-shot 2025–2026 test (slope and Elo-sum input both ties). It stays on the menu as a built input, but 2025–2026 is used for it; further tests must be prospective. Its screen size was inflated by the joint fit with I-036 (U-255) |
| **A** B11's On | U-138 (raw count), U-307 (On) | matches played here as a main effect |
| **A** B-VENUE | U-192 (venue pace, `fp__f09_venue__f09_ve`), U-254 | venue pace as symmetric context beside the ace ratings |
| **A** C-1 | U-002, U-003 | market-internal: only as an uncertainty input or an anchor choice |
| **A** KN-TTTLOGIT | U-036 | test which rating to keep (a swap), not an addition |
| **B** B-MOTIV | U-282–U-284, U-162, U-191 | the two indicators apart; Slam proximity as raw context |
| **B** B-OVERREACT | U-277–U-281 | its four mechanisms one by one |
| **C** | B11 block U-306 and I-076 U-309; B-STATE U-322, U-143, U-127; H-S2 U-216–U-230, U-232, U-233; I-036 U-255; B9a U-292–U-296 (I-061, U-144, is the likeliest member); I-053 U-285; B-ANCHOR U-266, U-004, U-007; B-AGE U-252; B3 U-243–U-245; B6 U-262–U-265; I-045 U-318, U-137; the long form level U-125 | as raw parts where the next-candidates note says so |
| **D** | B7 U-246–U-251; B-CLUTCH U-253; B-FLB U-258; B-REPUTE U-268–U-271; I-008 U-235–U-238, U-069; their raw parts U-019, U-045, U-126, U-177 | one strong window only |

## 4. Built, buildable, or needs new data

* **In the model (56 rows, 58 inputs)**: all stored as `m__`. Their per-player parts are stored as `pp__`, except elo_games, ios_points_short and points_52w, whose builders keep only A − B.
* **Built, not in the model (236 rows).** 197 of them are in the store, U-330 (8 Oct) included. That includes the near-miss raw blocks this study added on 7 Oct:
  * matches since the return (U-134) and the break's length;
  * venue pace (U-192), Slam proximity (U-191) and women's indoor (U-185);
  * the members I-085, I-055, C-2 and B-FLB's two;
  * the match-by-match ratings (`rt__`), the opponent-adjusted profiles (`ad__`) and serve speed (`sl__`).

  The other 39 live only in their study tables, all suggested low or exclude: Stage 4 aggregates, shot-level families, the frontier, market anchoring, splits, weekly Glicko-2. With the buildable, new-data, leaking and Polymarket rows, 71 rows have no store column.
* **Buildable from disk (21):**
  * the fatigue-adjusted form (medium; needs a design);
  * the new serve-speed sources (medium; need a pipeline);
  * ACWR and team ties, the backhand and weight, rank trajectories, WTA medical events and start times;
  * the point-sequence statistics;
  * the six gate-dropped members;
  * Betfair and the three books that stop in 2018.
* **Needs new data (4)**: opening prices before 2025, Polymarket flow, altitude/weather/court speed, ball tracking.

**Representations of one mechanism.** These pairs are alternative encodings of one idea. Choose one per mechanism, or test both under one hypothesis:
* raw parts and the study's combination: U-132/U-133/U-134 with U-316 (rust);
* the count and its log difference: U-138 with U-307 (On);
* the context and its product: U-192 with U-254 (venue);
* the sum and its standardised modulator: U-231 with U-256 (pair strength);
* the per-player state and its difference: U-144 with U-296 (odometer), U-143 with U-322 (past fatigue), U-162 with U-284 (letdown);
* two builds of the form evidence (U-126): `fe__` (14 Oct, the model's own weights) and the 7 Oct `fp__f07…s0` and `fp__f13…shr`. Select `fe__`.

## 5. Exclusions and why (33 rows marked "exclude")

* **Leaking** (6): weekly TTT, Bradley–Terry, MESR, revaluation, the weekly stage-B IOS (CLAUDE.md's list), and post-match anatomy (it describes the match itself).
* **No training history** (5): Betfair (2025–2026 only), Expekt/Ladbrokes/Stan James (stop in 2018), opening prices, the Polymarket price (the venue to bet at, not an input) and its flow.
* **Dominated or closed by earlier studies** (9): Elo without retirements, Glicko-2 weekly, career adjperf, opponent-strength splits, late decline and grinder, the net shift (equal to its placebo), momentum and streaks, women's tempo, resilience.
* **Not usable as is** (6):
  * frontier event speed (never probed; venue pace replaces it);
  * weight (not time-stamped);
  * the clock's width (data quality, not skill);
  * tracking feeds (too thin);
  * B-RECAL (a recalibration of the current model, not a feature);
  * INFO-1 (false premise).
* **Failed pre-declared reliability gates** (7): I-073's indoor deviations, I-018, I-019, I-021, I-009, I-028/I-029, I-068.

Exclusion is a suggestion. None of these was killed for a result on 2025–2026.

## 6. What a selection process must handle specially

1. **Copies.** Select from `menu.csv` (or the registry's `menu = 1`), not from the raw store: 784 columns hold 611 distinct usable ones (section 0). Examples:
   * `m__` equals `ctx__` for the six context inputs.
   * The fatigue kernel has eight copies, the imputed share six, off-site load four, rest four.
   * The on-site, rank, fame, height and salience intermediates are copied across modules.
   * The KN placebos equal their `alt__` twins.
   * Wald `x0…` columns and block members equal their deployment columns.
   * The decayed `ad__` forms are the model's own form inputs.
   * Near copies (|r| ≥ 0.999): `pp__rest_days` and `bd_rest` (up to 57 days apart on a few rows), the two 52-week levels, `bd11_on` and `ds__B11_member_On`, `pp__age_pl` and `pp__age`, Glicko-1's and Glicko-2's forecasts.

   `build/duplicates.json` lists the exact groups only.
2. **Pseudo-pairs.** `f07_k3`, `bd9b_mpp` and `h2hn` are identical for A and B, and `f08_bigpt` and `h2hres` are split differences. The registry re-registers them as context and diff (`kind`; the builders' own kinds are kept in `kind_built`).
3. **Base-dependent columns** (ten, flagged in the store). Recompute them with the new model's own out-of-sample forecast. Eight are missing in 2013 and 2025–2026, and B-ANCHOR's and B-REPUTE's sums change meaning there (section 0).
4. **Price-slope modulators** (`fi__…__s`, `lv__elo`, `mk__dispersion`) are symmetric. They act only through the price, so they must enter beside `m__odds_logit`. In a linear screen the candidate is s × price, with neither s × price among the controls nor s alone as a main effect (the study's builders.md rule).
5. **Market-internal inputs** help a model benchmarked on the average close. Polymarket is as sharp as Pinnacle, so judge them on the betting venue's price, or leave them out. Pinnacle covers only 59% of 2025–2026 (it ends in January 2026).
6. **Clean test seasons.** 160 rows were seen on 2025–2026: every incumbent and most earlier-study features. In `menu.csv`, 367 of the 611 columns are seen.
   * Seen among the near misses: the rust rows (B-INJ's U-315–U-318, and the raw blocks U-132–U-135, through B-INJ and Stage 4's days_since), C-1 (U-002, U-003), KN-TTTLOGIT (U-036), and pair strength (U-231, U-256: the pair-strength study's one-shot test, 7 Oct 2026).
   * Unseen: On, venue pace, B-MOTIV, B-OVERREACT and the tier C–D members (I-036 included; only its close relative, the Elo sum, was tested). For them, 2025–2026 is still a valid single test after a pre-registration chosen on 2014–2024 alone (next_candidates).
7. **Coverage holes by tour.**
   * Women's indoor is missing from `m__indoor` and `ctx__indoor`; `fp__f09_venue__f09_indoor` covers both tours.
   * Women's height covers 64% (2022–2024) and 39% (2025–2026).
   * Women's service-game statistics cover 74% of 2013–2021 (hold, break points faced, return games).
   * Women's minutes are imputed before 2016.
   * Shot-level histories are thin before 2022.
   * The S11 rule (a missing indicator × price) applies where a feature is missing for one side.
8. **The 2025–2026 first-serve fault.**
   * 15 incumbents and the first-serve candidates (first_in, first_won and second_won forms, IOS and sums; I-045; B3) are exposed in 264 frozen-frame men's test matches.
   * RG 2026 qualifying (97 rows) has no clean source.
   * Rebuild from the live corrected Stage 0 before testing.
9. **Stored on 7 Oct after the first catalogue pass**, which had found them missing:
   * venue pace (`fp__f09_venue__f09_ve`), Slam proximity (`fp__f19_motiv__nslam_days`) and women's indoor (`fp__f09_venue__f09_indoor`);
   * matches since a return and the break's length (`fp__f26_impairment__ret_n`, `ret_gap`);
   * the B-FLB members (`fi__B-FLB__m_*`);
   * per-player Glicko-2 RD and volatility (`rt__glicko2m_u`, `rt__glicko2m_vol`).

   Serve speed (`sl__`) keeps a value only where its source has real speed data, never its prior fill.
10. **Cross-player features need the clock.** Any new combination of different players' results (a field table, a venue estimate, a joint solve) must read the state at `es`, count results from `lf + 1`, and pass `src/eda/match_timing/probe.py`. U-043 (strength of schedule) and U-106 (frontier event speed) have never been probed.

## 7. High-priority candidates (suggestions)

* **Incumbents (53 of the 56 in-model rows)**: the anchor, overall and offset Elo, ratings_iid, the IOS profile, the short-memory points matchup, the two-week profile, load and the surface pairs, age and context. elo_games, points_52w and age² are medium.
* **New (6)**, all raw parts of tier-A near misses, all now in the store:
  * U-132 days since the last match;
  * U-133 break length;
  * U-134 matches since the return;
  * U-138 matches played here (and its log difference, U-307);
  * U-192 venue pace.

  The three rust blocks (U-132–U-134) are seen on 2025–2026 through B-INJ. Matches played here and venue pace are unseen.

  The pair's Elo sum (U-231) and I-084's modulator (U-256) were high until the pair-strength study tested them on 2025–2026 (ties). They are now low.

Medium-priority rows (41) include the decided-TTT and offset-TTT swaps, the B-MOTIV and B-OVERREACT members, past fatigue and the odometer, women's indoor, Slam proximity, serve speed, ranking, the Stage 3 uncertainties, the spw IOS, the decayed serve-points-won form, since 8 Oct the history composition (U-330) and, since 14 Oct, the form evidence (U-126).

## 8. Notes

* Constants, coverage and evidence are copied from the cited files. Nothing was refitted, and no result of any season was read. The pair-strength study's results were read from its report, after it had run.
* Evidence from the round-0 register mostly comes from windows that include 2025–2026. Treat it as a reason to look, not as a clean estimate.
* **Cleanup, 8 Oct 2026** (the owner allowed deleting what can be reproduced):
  * Deleted:
    * `data/studies/feature_interactions_universe_placeholder.txt`, one byte created by mistake;
    * `data/studies/feature_universe/build/__pycache__/`, left when the catalogue scripts moved to `src/eda/`;
    * the feature-interactions math audit's panel cache, `round1/math_audit/panel_le2021_noresult.parquet`. Today's panel reproduces all 281 of its columns exactly; its rebuild adds the later `eta_model` column, which no audit script reads. The audit rewrites it on first use.
  * Kept, because they are not reproducible: `round1/_history_feats_2010_2024.parquet` (35 of its 37 columns differ on a rebuild) and `round1/_panel_aug.parquet`, which is built from the same history quantities (inferred).
* **U-330 added, 8 Oct 2026** (the owner: "add this feature to the feature universe we will potentially feature select for"):
  * the three `el__` columns were appended with `build_store.py --append-el`, from `event_levels/universe_columns.py` on the same pre-rebuild Stage 0. Its side A equals the store's on all 63,737 rows, and its 2013–2024 values equal the study's own table;
  * the row sits in its own spec module (`catalogue/spec_event_levels.py`), last, so U-001 … U-329 kept their ids;
  * unchanged, checked against copies taken before: all 776 earlier store columns (byte for byte), every earlier registry field (one near-duplicate correlation differs by 1.6 × 10⁻¹³, float rounding of the larger matrix), all 1,793 earlier coverage keys, `duplicates.json`, U-001 … U-329, and the 603 earlier menu rows;
  * the store grew to 779 columns, the menu to 606 (`el__` 3), the catalogue to 330 rows. Two documents that describe the menu as it was (603) were left as written: [clean_holdout_rebuild](../clean_holdout_rebuild/README.md) and the feature-provenance study.
* **U-126 refreshed, 14 Oct 2026** (the owner: "Add an input to the candidate-feature list saying how much data stands behind each player's recent form"):
  * **Built** by `form_evidence.py --store`, with the model's own code on template_2026-10-13's build tree (`C:/Users/zerom/tnr_gaps`), read only, as the daily engine reads a base tree. Appended with `build_store.py --append-fe`;
  * **Re-filed in place, not a new row:** one row per conceptual feature (section 1), as U-125 holds two builds of its level. So no id moved, and the catalogue keeps 330 rows;
  * **Side A** is the store's (the pre-rebuild Stage 0's) wherever the tree has both players: 63,626 of 63,737 matches, each with the tree's own side A. The other 111 are WTA matches of June–July 2026, and they are missing:
    * 71 keep their match id but name other players in today's tables. 8 of their 86 old ids are the 8 Oct id fix's aliases (F7); the rest are presumably Tennis My Life's own id revisions (inferred, not traced);
    * 40 match ids are no longer in today's tables;
  * **The instance's own population** (its 67,226 matches) is beside, in `form_evidence/template_2026-10-13.parquet`. `template_2026-10-14.parquet` was built the same way on that instance's tree. The two differ on 2.8% of the player-rows, 84% of them in 2026 (that instance has the Roland Garros repair and Tennis My Life's revisions);
  * **Unchanged,** checked against copies taken before:
    * all 779 earlier store columns and the keys, value for value;
    * every earlier registry field, except two near-duplicate correlations that moved by float rounding (8.9 × 10⁻¹⁶ and 3.6 × 10⁻¹⁵);
    * all 1,797 earlier coverage keys and `duplicates.json`;
    * every catalogue row but U-126;
    * the 606 earlier menu rows, except the priority of U-126's four 7 Oct columns (low to medium, with their row);
  * the store grew to 784 columns and the menu to 611 (`fe__` 5).

## 9. The pool: admissions (since 9 Oct 2026)

**The universe is the pool** ([decision](../../decisions/2026-10-09-adoption-by-change-class.md), point 6; [adoption framework](../adoption_framework/README.md) § 11).
* A study of a new feature no longer asks "should this go into the model?". It ends with an admission verdict here.
* A selection round decides what enters the model, by cluster.

**The verdicts:**
* **admitted;**
* **admitted as a lead:** it has read results. The seasons it read are recorded, so that a round confirms it on others;
* **not admitted,** with the reason;
* **a repair:** it fixes an input already in the model, and goes to the framework's repair lane, not here.

**The admission card.** Each item rests mostly on what needs no result:
* **Definition and encodings:** a `universe.csv` row, or rows, with its store columns.
* **Stable measurement:** defined the same way in every season. Its coverage by tour and season, from `store_registry.csv`. Its own reliability where it applies (it predicts its own next value).
* **Timing:** safe by construction, or the match clock with `probe.py` passed (section 6, item 10).
* **Available at bet time:** its source and publication lag.
* **Not a near-copy:** its largest |r| with the menu, which `build/duplicates.json` lists for exact groups.
* **A mechanism:** why the market would misprice it.
* **Its cluster:** the node of the selection round's tree (the [rebuild](../clean_holdout_rebuild/03_rebuild_stages.md), § 5, item 4).
* **Results read, if any:** the seasons, the prices, the reading, and where it is logged.

**How to admit.**
* Add the row with `catalogue/spec_*.py` and `build_store.py`, keeping earlier ids, as U-330 was added (section 8).
* Record the verdict and card in that row's notes, and in the study's report.

**Re-filed on 9 Oct 2026:**
* **U-330, the lower-level share:** admitted as a lead. It read 2013–2024 results in the event-levels study: the mispricing, and the 59th-input test (+0.06 [−0.10, +0.23] mLL, + = with the share better). [Checklist](../adoption_framework/checklist.md) item 9 is no longer an adoption decision.
* **The two box-score share differences** (`in_box_low_share_h2w_diff`, `in_box_low_share_365d_diff`; the lower-level study's R_S2): to be admitted as a lead. They read 2020–2024 results; they are not yet in the store.

**Re-filed on 14 Oct 2026: U-126, the form evidence** (the owner: "Add an input to the candidate-feature list saying how much data stands behind each player's recent form"). **Recommended verdict: admitted.** Checks: `form_evidence/template_2026-10-13_checks.json`.
* **Definition and encodings.** For each player, the box-score evidence behind the two-week form, exactly as the current best model weighs it:
  * `fe__sw_a/_b`: sw, the decayed count of the player's earlier box-score matches. It is the denominator of Stage B's step 3 for total points won (`adjperf_tpw_2w`):
    * half-life 2 weeks, from tournament date to tournament date;
    * Stage B's time rule;
    * the level layer's weights for men: main tour 1, lower levels 0.49–0.90 on average, ITF box scores 0. Women: 1;
    * a main-tour match weighs 1. sw is 0 without an earlier box score.
  * `fe__r_a/_b`: r = sw / (sw + K3), the share of the raw two-week mean that the form keeps. K3 is total points won's: 10 for men, 20 for women. The serve-skill forms use the same K3; the return-skill forms use 160.
  * `fe__r_diff`: r_a − r_b.
  * **Why total points won.** Its mask is the broadest. The other forms' sw differ:
    * men's correlate 0.98–1.00 with it (the layer weighs each statistic);
    * women's service-game forms (hold, break points faced, return games) correlate 0.70 in 2013–2021, and are missing on 24% of the player-rows where its form exists.
* **Stable measurement.** Defined the same way in every season.
  * **Coverage:** 1.00, except women's 2025–2026 (0.97: the 111 matches of section 8).
  * **Its level moves with box-score coverage,** as the model's form denominators do:
    * women's 2015 lacks lower-level box scores: mean sw 2.05, against 2.7–3.5 in other seasons;
    * women's ITF box scores are 3.8% of sw in 2025 and 2.7% in 2026, and about 0 before. The layer leaves women untouched;
    * 2020 is lower for both tours.
  * **Reliability:** not applicable, since it is a count, not an estimate.
* **Timing.** Safe by construction: each player's own earlier matches under Stage B's time rule.
  * **A cut probe on sw** (8 cuts, 2.04 million protected rows): none moved beyond 10⁻¹². 134 moved by rounding, at most 1.8 × 10⁻¹⁵, and a leaky control was caught at 186 rows.
  * **The denominator check:** sw rebuilds the model's `adjperf_tpw_2w` bit for bit on all 67,226 frame matches.
  * **An independent recount** on 400 player-rows agrees to 1.2 × 10⁻¹⁴.
* **Available at bet time.** It comes from the same box scores as the forms, with Tennis My Life's lag and the WTA fills.
  * The daily engine already computes sw in step 3 (`forms_state.step3_for`), but does not output it yet.
  * A missing recent box score lowers sw at bet time, as it lowers the form's denominator.
* **Not a near-copy.**
  * Its largest |r|: 0.98 with its own 7 Oct build (`fp__f07…s0`), then 0.71 with `pp__sets_14d`.
  * `fe__r_diff`'s largest is 0.70, with the model's `sets_14d`.
  * None reaches 0.999, so all five are distinct menu columns.
* **Mechanism.** The model sees each form only after shrinkage, as A − B. It cannot tell a small difference between two thin histories from one between two thick ones. The evidence lets it weigh the 17 forms. Where recent form rests on few box scores (a return, a run below the main tour), the market's reading of it may be off.
* **Cluster.** The per-statistic profiles block, at the two-week profile's node, beside U-125's long level. Its mean |r| with sets in 14 days is about 0.7, below the 0.8 merge rule.
* **Results read.** None for `fe__`.
  * The 7 Oct builds entered B7 (I-031) and B6 (I-033) as parts of composites, screened on 2014–2024: oriented z +0.76 and +1.13, neither significant (feature interactions).
  * They were never tested as an input, and the request is the owner's, not drawn from those readings. So the verdict is "admitted", not "admitted as a lead". Those seasons are recorded here for a round to see.
* **Priority suggestion:** medium (low before), by the analogy with U-125.

