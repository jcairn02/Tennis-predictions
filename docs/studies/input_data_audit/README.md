# Input-data audit of the current best model: the "4 km/h year" in serve speed, and errors like it

8 October 2026 · Data-cleaning research, not a model, data or betting decision. **Nothing in the pipeline was changed;** every fix below is a suggestion.

**The request** (owner, 8 Oct 2026): "I was told there was a potential bug in the serving speed data one year being 4km/hr higher on every serve? Search for similar errors. Our best tabpfn 3.5 non thinking model and the data used to feed it is the data I want analyzed, column for column, the input data that is used to build the advanced averages too."

**What was audited.** Both stages of the current best model ([decision](../../decisions/2026-10-07-speed-nudge.md)):
* the 58 inputs in `data/studies/surface_rating_race/model/model_frame.parquet` (63,737 matches), column by column;
* the Stage 0 box scores that the averages are built from (two-week form, IOS profiles and products, points aggregates). Two snapshots were checked:
  * **30 Sep**, which every model input was built on;
  * **7 Oct**, today's tables, which the next rebuild will read;
* the closing odds (Stage 1);
* the serve-speed panel behind `spd_L`.

**Labels.** **Observed** = computed here, with its file; *inferred* = reasoning; **suggestion** = not decided.

## In short

**The reported bug is Australian Open 2024, and it does not reach the model** (observed, §2.1).
* **The shift.** The same men served 3.5 km/h faster at AO 2024 than at AO 2023 (women +2.4).
* **The cause.**
  * It is in the AO's own published numbers, on particular courts: Rod Laver, Margaret Court, John Cain, Courts 3 and 8. Courts 5–7 read normally.
  * The project's code path is clean: field, unit and rounding were checked.
* **Why it does not reach the model.** The speed column centres every edition on what that edition's radar read. It learns a new edition within about a day.
  * Effect on `spd_L` with the weekly feed in use: 0.
  * With instant speeds: at most 0.12 units.
  * No fix is needed.

**The same search found errors of that kind that do reach the model.** All observed, ordered by how many model rows they touch.

| # | Error | Where | Size | Model rows it reaches | In today's (7 Oct) tables? |
|---|---|---|---|---|---|
| 1 | **Serve points leave out double faults** | 30 WTA tour events, 23 Feb – 24 Aug 2015; 2,382 player rows | Second-serve points won read 51.6% (44.9% corrected); first serves in about +3 points | 1,410 training matches through the two-week form; 3,763 within a year | Yes |
| 2 | **Second serves booked as first serves** | Roland Garros 2022–25 qualifying and main draw, both tours; the Paris Olympics 2024 (played at Roland Garros) | First serves in +5 points in qualifying (2025: 68.5% against RG's own 63.1% for men, 67.9% against 63.2% for women); +0.6 to +2.4 in the main draw; +6 to +8 at the Olympics | Test seasons: 292 + 1,362 + 424 matches through the form | Yes |
| 3 | **Box scores exchanged between winner and loser** | 88 matches, including a third to a half of the checkable matches at WTA Abu Dhabi 2021 and Phillip Island Trophy 2021 | The winner carries the loser's whole box score | 127 matches through the form (61 training, 66 test) | Yes |
| 4 | **Box scores copied from another match** | WTA Adelaide 2 2022 carries Adelaide 2021's box scores (38 rows), on other players; 39 more same-pair repeats, 11 of them into the 2015 WTA US Open | Another match's statistics | 68 test matches through the form | Yes |
| 5 | **One player split across two ids** | WTA from 8 June 2026: Queen's, 's-Hertogenbosch, Memphis and others | The player is rated as a newcomer. In the first round of Queen's and 's-Hertogenbosch every rating difference is exactly 0 | 71 test matches | Mostly fixed: 13 remain |
| 6 | **The IOS matchup products change scale with the ratings' level** | The 7 `prod_*` inputs. ITF box scores exist only from January 2025 to May 2026 and move the ratings' level | Products' spread +25–56% in 2025–26. With each season's level removed, it is flat | Every 2025–26 test match | Yes (a design issue) |
| 7 | **Women's workload reads "rested" after the TML splice** | `sets_14d` (and the surface-season pair) from June 2026: Stage 0 lost women's qualifying and most WTA 125 draws | Women with no sets in the previous 14 days: 27.4% in June–July 2026, against 9.1–9.3% in 2024–25 | WTA test matches from June 2026 | Yes |
| 8 | **Serve-speed rows the centring cannot absorb** | ATP key statistics up to 267 km/h; AO 2025 Courts 12–13 reading 5–10 km/h low; other broken rows. The filter's unclipped first reading amplifies them | Fixing them moves `spd_L` by ≥ 1 unit (≈ 0.9 points of win probability in an even match) in 102 of 7,070 men's test matches | Test (stage 2) | Yes |
| 9 | **Men's 2018 season missing** | The tennis-data.co.uk workbook failed to download on 22 Sep (404, no Wayback copy) | 2,620 training matches absent: +6.6% of the training rows when restored | Training | Odds restored in the 7 Oct Stage 1; the model frame still lacks them |
| 10 | **Wimbledon 2026 men: TML's first serves** (already known) | 476 player rows | First serves in +4 to +9 points | 164 test matches | Fixed in the 7 Oct tables; the model frame still has the old values |

Smaller items are in §3.5, §4 and §5: about 11 corrupt odds rows, including two finals with the odds reversed; 103 WTA 2026 matches without an age; and Slam counting conventions.

**What it means** (*inferred*).
* **Most columns are sound.** The label, the odds column, Elo, the context columns and the surface-switch pairs pass. The faults sit in four places:
  * the box scores under the averages;
  * one design choice (the products);
  * workload after the splice;
  * a few odds rows.
* **Rebuilding on today's tables does not clean the data.** Only #5 (mostly), #9 and #10 are fixed there. Everything that comes from Sackmann's files (#1–#4) or from design (#6–#8) is still in them.
* **The effect on log loss was not measured.** That needs a rebuild and GPU refits. Most faults touch a small share of rows. #2 and #6 touch the test seasons broadly.

**Suggestion:** correct at source, then rebuild the chain; the order is in §7. The rebuild is the owner's call.

## 1. How the search worked

Stage 0's row checks (B0–B9) catch a count that is impossible inside its own row. A season that reads 4 km/h high passes them, because every row is plausible. So four other tests were run (`src/eda/input_data_audit/box_checks.py`):

1. **Accounting across the two players of a match:**
   * a player's games (from the score) = her holds + the opponent's breaks conceded;
   * service games alternate;
   * the winner usually wins more points (96% of matches).
   * A failure that disappears when the two box scores are exchanged marks a swap.
2. **A definition test:** second-serve points won + double faults cannot exceed the second-serve points. It holds whenever serve points include double faults.
3. **Verbatim repeats:** a box score that appears in another match of Sackmann's raw files.
4. **Same-player shifts:**
   * Each edition's rates are compared with the same players' own matches in the same season on the same surface. This is the box-score version of the speed acquisition's "same players, year on year" check.
   * Also pooled rates by tour, level and season.
   * Suspects were then checked against independent records:
     * the Match Charting Project's hand-charted points;
     * Roland Garros's own key statistics (the decrypted Infosys files).

The model frame was profiled per input and tour-season: spread, missing share, exact zeros, and correlation with the odds and the label (`model_frame_checks.py`). Side A is random, so a break in one season's profile is the column-level sign of the same kind of error.

Two background agents audited the closing odds and the speed panel; their scripts and tables are kept under this study (§8). The claims this report leans on were re-checked by the lead:
* the cause of the missing 2018 season;
* the two reversed finals;
* the 267 km/h row;
* the filter's diffuse start in the code;
* the propagation table.

## 2. Serve speed (stage 2, `spd_L`)

### 2.1 AO 2024: the reported bug

*Observed* (`speed/a06_ao_paired.py`, `a07_ao_court_day_mc.py`, `a11_ao_court_fe.py`, `a15_learning.py`):
* **Size.** The same men served +3.49 km/h faster than at AO 2023 [1.89, 4.20], 88 players; women +2.38. From 2024 to 2025: −1.65 and −1.51.
* **It is the AO's own number.** Its match-centre "1st Serve Average" equals the copy's mean (Sinner 196 against 196.11 in the final; Medvedev 193 against 192.89).
* **The code path is clean:**
  * the field is the serve's `ballSpeed`, in KPH on every row;
  * whole numbers in every year;
  * the adapter and panel are identical across 2020–24.
* **It is a measurement offset, not real serving** (*inferred*):
  * it is additive, about +3 across the distribution;
  * first-serve faults did not move (+0.40 km/h);
  * it sits on some courts (Rod Laver, Margaret Court, John Cain, Courts 3 and 8), not others (Courts 5–7).
* **The pipeline absorbs it.** The as-of edition offset is 1.83 km/h short after day 1, 0.63 after about 90 rows and under 0.05 after about 230 rows.

| Effect on `spd_L`, men's 2024–26 test matches (7,070) | ≥ 0.25 units | max |
|---|---:|---:|
| AO 2024 edition offset, weekly feed (what the model uses) | 0 | 0.00 |
| AO 2024 edition offset, instant speeds | 0 | 0.12 |
| AO 2024 court-to-court spread, weekly feed | 7 | 0.38 |

### 2.2 Shifts of the same kind elsewhere

*Observed* (`speed/a12_global_scan.py`, `a13_row_checks.py`, `a21_flags.py`):

* **Slam editions:**
  * Wimbledon 2025: men +8.4 km/h, women +3.3. It persists in 2026: a system change, already known.
  * Wimbledon 2024: men −3.8.
  * US Open: men −3.9 over 2023–25, then +10.4 in 2026; 2024 qualifying: men −8.6, women −5.1.
  * Roland Garros: men +2.8 from 2023.
  * The edition centring absorbs all of these.
* **Courts and days:**
  * AO 2025 Court 13: men −5.5, women −5.4, women's qualifying −8.4. One men's qualifying match on that court read 139 and 137 km/h, 51 and 38 below the two players' norms.
  * AO 2025 Court 12: men −10.6.
  * US Open 2024 Courts 11 and 15: −5.9 and −8.3.
  * Doha, 16 Feb 2026: −6.6.
* **Broken rows:**
  * **ATP key statistics from the handoff** (370 rows): 26% are more than 10 km/h off the player's norm. 79 average at or above the match's fastest serve. All 14 men's panel rows of 240 km/h or more are among them, up to 267. The panel prefers them over valid point means.
  * **ManTennisData:**
    * 29 rows average at or above the maximum;
    * 193 have a second-serve average at or above the first;
    * in 86 matches both players read at least 8 km/h low;
    * 5 stat blocks are copied onto another match.
  * **Roland Garros 2023–24 Hawk-Eye copy:** a serve repeats the previous serve's speed 5.3% and 9.4% of the time, against 1.4–3.0% normally.

### 2.3 What reaches `spd_L`

**The amplifier** (observed in `src/eda/serve_speed_tabpfn/features.py`, `kalman`).
* **How the filter starts.** Each player's level starts diffuse (P11 = 10⁶). On the first row of his 364-day window the clip c·√S is about 2,000 km/h, so the level absorbs that row whole, however wrong it is. Later rows are clipped at about two SDs, so the level recovers slowly while the form state takes the gap.
* **Example.** atp:208233 has a 267 km/h key statistic from Atlanta 2024 qualifying.
  * While older rows led his window, the clip held it and his `f̂` stayed normal (−2.4 to +2.8 km/h).
  * At Wimbledon 2025 that row became the oldest in his window. His `f̂` read −13.8 and −14.5 km/h, against +2.6 and +3.1 with a robust start (`speed/t_first_row_A.csv`).
* **Scale.** 536 men's test-window sides (114 players) start their window with a row more than 15 km/h off the rest.

**Fixing each block**, weekly feed (`speed/t_propagation_summary.csv`; one unit of `spd_L` ≈ 0.9 points of win probability in a 50–50 match):

| Block corrected | Matches moved ≥ 0.25 / ≥ 0.5 / ≥ 1 unit | Max |
|---|---|---:|
| AO 2024 edition | 0 / 0 / 0 | 0.00 |
| AO 2025 Courts 12–13 | 73 / 19 / 0 | 0.85 |
| Handoff key statistics | 118 / 78 / 37 | 5.51 |
| ManTennisData broken rows | 302 / 155 / 64 | 5.23 |
| **All row and court fixes** | **519 / 249 / 102** | 5.54 |
| A robust start alone (median of the first five rows) | ≥ 1 unit in 96 | – |

**Also in this path** (observed):
* the panel predates the quarter-final label fix (one 2026 quarter-final missing);
* the mislink check misses ATP feeds linked to ITF matches (10 mislinks, 8 in 2024–26);
* AO 2024 raised the AO family's pooled offset, so AO 2025 started at −3.07 against its settled −5.93;
* the 120 km/h men's floor lets 125–165 km/h failures through, and there is no ceiling.

## 3. The box scores under the averages

These feed:
* the 16 two-week form inputs (`form_*`, `formdef_*`);
* the 14 IOS ratings and 7 products;
* the points aggregates: `adjperf_tpw_2w`, `ios_points_short`, `points_52w` and `ratings_iid`.

### 3.1 WTA 2015: serve points leave out double faults

*Observed* (`box_wta2015_events.csv`, `box_wta2015_vs_mcp.csv`, `box_svpt_df_editions_*.csv`):
* **The window.** From Acapulco (23 Feb 2015) to New Haven (24 Aug 2015), 30 of the 31 WTA tour events read second-serve points won around 50–55%. Every other WTA season, and that year's Slams, read about 45%. Doha is the exception: normal.
* **The definition test fails** in 2.6% of WTA 2015 rows. No other tour-season has more than 0.04%.
* **The Match Charting Project settles it.**
  * In the window, Sackmann's serve points + double faults equal the charted serve points in 83% of player-matches. Serve points alone equal them in 12%.
  * In other WTA matches of 2014–16 the figures are 7% and 73%.
  * For example, Serena Williams, Cincinnati 2015 semi-final: 71 charted serve points against Sackmann's 63, with 8 double faults.
* **Corrected**, the events' second-serve share falls back to 43–48%.
* **Effect.** First serves in, aces and double faults per point, second-serve points won and serve points won all read high. The points-won aggregates drop the double-fault points.
* **Also from 2015** (coverage): no WTA tour box scores from September to December 2015, and no WTA service games before February 2015. The latter is why the women's hold-based inputs are missing or zero in 2013–14.

### 3.2 Roland Garros 2022–25 and the Paris Olympics: second serves booked as first

*Observed* (`box_rg2025_vs_keystats.csv`, `box_slams_vs_mcp.csv`, `box_edition_effects_*.parquet`):

| Draw | Stage 0 first serves in | Independent record | Exact agreement |
|---|---:|---:|---:|
| RG 2025 qualifying, men | 68.5% | RG's key statistics 63.1% | 35% of rows |
| RG 2025 qualifying, women | 67.9% | RG's key statistics 63.2% | 39% |
| RG 2026 qualifying, men (TML) | 63.2% | 63.2% | 66% |
| RG main draw, men 2022 / 2023 / 2024 / 2025 | +2.3 / +1.0 / +0.6 / +0.2 points against charted matches | Match Charting Project | 36–64% |
| RG main draw, women 2022 / 2023 / 2024 / 2025 | +2.4 / +1.8 / +2.2 / +0.9 points | Match Charting Project | 58–68% |
| AO, Wimbledon, US Open 2019–25 (for comparison) | within 0.2 points | Match Charting Project | 43–97% |

* **The qualifying fault in other years.** Stage 0's qualifying reads 65.2–68.6% (men) and 67.0–69.9% (women) in 2022–25. In 2010–21 it read 59.8–62.7% (men) and 61.0–65.2% (women); TML's 2026 men's qualifying reads 63.2%.
* **What the error is.** One example: Li Tu's 2025 Q1 has 82 first serves in, where RG's statistics say 57, and 11 second-serve points won where they say 22. Second serves are recorded as first, as in TML's Wimbledon 2026 fault.
* **The Paris Olympics 2024, played at Roland Garros:** first serves in read 70.3% (men) and 67.9% (women), against 61–64% at the 2012 and 2016 Olympics. First-serve points won fall with it: the same fault (*inferred*).
* **What was known.** The [data-continuity study](../data_continuity/README.md) found the men's qualifying fault and kept it flagged. The women's side, the main draw and the Olympics are new.
* **Excluded:** Miami men read +5 points in 2024–25, but rose steadily after the 2019 venue move with no fall in first-serve points won. That is real, not a fault.

### 3.3 Box scores exchanged between winner and loser

*Observed* (`box_swapped_*.csv`, `box_identity_editions_*.csv`):
* **88 matches fit the score only with the two box scores exchanged.** 74 of them also have the "winner" winning fewer points.
* **Most are in two events:**
  * WTA Abu Dhabi 2021: 22 of its 62 main-draw matches, 6 qualifying;
  * WTA Phillip Island Trophy 2021: 14 main, 4 qualifying.
  * In those events' draws the recorded winner won fewer points in 30–62% of matches, against 4% normally.
* **Example.** Sabalenka d. Jabeur 6-2 6-4: the box score under Sabalenka gives 6 games; Jabeur's gives exactly 12.
* **The error is in Sackmann's raw file** and in TML's copy of it. Stage 0 cannot see it, because each row is plausible on its own.

### 3.4 Box scores copied from another match

*Observed* (`box_raw_copies.csv`):
* **WTA Adelaide 2 2022 (10 Jan) carries Adelaide 2021's box scores**, match number for match number, under other players:
  * Martincova d. Yastremska has Doi d. Blinkova's box score from 2021, to the point;
  * even a walkover carries one.
  * The names and scores are right; only the statistics are another year's. 38 rows.
* **39 more matches carry the box score of the same pair's earlier meeting.** Mostly WTA 2010–15; 11 of them are in the 2015 WTA US Open.

### 3.5 Smaller

* **Slam counting conventions** (observed; small effect on the hold and break-point inputs):
  * At some Slam editions the two players' service-game counts differ by two or more: men's Wimbledon 2018 and 2023, US Open 2019, in 21–24% of matches. Some feeds count tiebreaks as service games.
  * At others, breaks do not add up to the score: men's US Open 2013, women's Roland Garros 2018 and 2021 qualifying, AO 2022 and others, in 20–28% of matches, against 0.5% elsewhere.
* **The ITF regime.** ITF box scores exist only from January 2025 to May 2026: 45–80% of all box-score rows in those quarters, none before or after. That drives finding #6 (§4).
* **Ages** (none in model-frame matches):
  * TML's 2026 Challenger rows give some players ages of 56–58, a 1970 default birth date (*inferred*);
  * ITF ages of 11–12 and 67–75;
  * 182 ATP Challenger rows of 2020 run about 5 months behind.

### 3.6 How far each fault reaches the model

*Observed* (`frame_fault_exposure.csv`): model-frame matches where a player had an affected match in the previous 28 days (the two-week form inputs) or 365 days (the long-memory inputs).

| Fault | Player rows | Within 28 days: train / test | Within 365 days: train / test |
|---|---:|---|---|
| WTA 2015, serve points without double faults | 2,382 | 1,410 / 0 | 3,763 / 0 |
| Box scores exchanged | 176 | 61 / 66 | 1,379 / 761 |
| RG 2022–25 qualifying | 1,772 | 0 / 292 | 0 / 6,129 |
| RG 2022–25 main draw | 2,010 | 0 / 1,362 | 0 / 19,029 |
| Paris Olympics 2024 | 242 | 0 / 424 | 0 / 3,344 |
| Wimbledon 2026 men, TML | 476 | 0 / 164 | 0 / 190 |
| Adelaide 2 2022 copy | 78 | 0 / 68 | 0 / 891 |

The 365-day counts say who carries a faulty match in a long memory, not how much it moves them.

## 4. The model frame, column by column

*Observed* (`frame_season_profile.csv`, `frame_summary.json`, `frame_split_ids_*.csv`, `frame_product_drift.csv`). Side A is random in every season: the label's mean is 0.481–0.524 by tour-season.

| Inputs | Verdict | Findings |
|---|---|---|
| `odds_logit` | Sound, with gaps | Equals Stage 1 exactly (§5). Men's 2018 missing (#9). About 11 corrupt rows |
| `elo_overall`, `elo_surf_offset`, `ratings_iid`, `elo_games` | Sound, except one block | Exactly 0 on 1.2–1.6% of WTA 2026 matches, never otherwise: the split ids (#5) |
| `adjperf_tpw_2w`, `ios_points_short`, `points_52w` | Hit by #1, #3 and #4 | Women's 2015 spread 27% below other seasons (`adjperf_tpw_2w`) |
| `form_*` (12), `formdef_*` (4) | Hit by #1–#4 and #10 | Women's 2013–14 hold-based forms missing in 99% of matches (no service games). Women's 2015 spreads 12–25% low |
| `iosO_*`, `iosD_*` (14) | Long memory of #1–#4 | Women's 2013–14 hold ratings 0 (no data) |
| `prod_*` (7) | **Scale drifts (#6)** | See below |
| `sets_14d` | **Wrong for women after the splice (#7)** | Missing for 0.3–1.1% of women's 2021–23 matches |
| `age`, `age_sq` | One gap | Missing for 103 WTA 2026 matches. TML's Eastbourne, Bad Homburg and 's-Hertogenbosch rows carry no birth date; never missing in training |
| `surf_season_a/b`, `surf_layoff_a/b` | Sound; women's 2026 likely affected like #7 (*inferred*) | Partial seasons (2020, 2026) show as expected |
| `tour`, `surface`, `level`, `indoor`, `best_of`, `round` | Sound | Best-of agrees with every score. Every surface, level and indoor change between seasons is a real calendar change (for example Stuttgart to grass in 2015, Linz to clay in 2026). `indoor` is missing for women by design |

**The products (#6).**
* **The algebra.** `prod_s = O_B·D_A − O_A·D_B`. A common shift of every rating (o₀, d₀) adds o₀(D_A − D_B) − d₀(O_A − O_B). The A − B inputs do not change; the products do.
* **What happened.** The surface IOS's level for the model's players rose when ITF players filled the pool in 2025, and fell back after June 2026. For women's holds the mean defence level was 0.41 in 2024, 0.54 in 2025 and 0.73 in 2026.
* **The spread of `prod_hold`:**

| Tour, season | `prod_hold` SD as built | With each season's level removed |
|---|---:|---:|
| Men 2024 / 2025 / 2026 | 0.383 / 0.492 / 0.534 | 0.095 / 0.115 / 0.107 |
| Women 2024 / 2025 / 2026 | 0.228 / 0.275 / 0.343 | 0.095 / 0.098 / 0.085 |

So 7 of the 58 inputs reach the test seasons on a wider scale than training, while no player changed.

**Split ids (#5).**
* **30 Sep tables:** 130 players gained a second id after Sackmann's last week: 64 women and 66 men. The men's are at lower levels.
* **Model rows:** 71 women's 2026 matches have such a player; 's-Hertogenbosch 27 and Queen's 26 of them.
* **Examples:** Rybakina, Anisimova, Raducanu, Pliskova, Kasatkina and Krejcikova all played those events as newcomers.
* **7 Oct tables:** 13 pairs remain (9 women, 4 men), in 13 model-frame matches.

## 5. Closing odds

*Observed* by the odds agent (`odds/a01`–`a14`); the first two items were re-checked by the lead.
* **Men's 2018.**
  * The download failed twice on 22 Sep: live 404, and no Wayback capture (`data/raw/public_dump/tennis_data_couk/_receipts.jsonl`).
  * The 30 Sep Stage 1 has no ATP 2018 odds; the 7 Oct Stage 1 has 2,634.
  * The rule "no odds, no row" in `tabpfn_thinking/build_frame.py` then dropped the season.
* **Reversed or impossible odds:**
  * **The average odds are reversed against the individual books** in two training finals:
    * Wimbledon 2016: average 1.26 on Raonic against Bet365 4.33 and Pinnacle 4.36, so the model has 0.76 for Raonic;
    * Chennai 2013 semi-final.
  * **Nottingham 2017 final:** the names are swapped in tennis-data. Konta, ranked 8th, carries Vekic's (70th) underdog price, so the model has 0.19 for Konta.
  * **The average above the maximum:** two test rows.
  * **Placeholder prices:** the two Washington 2026 finals.
  * Altogether about 11 rows. They change the market's log loss by less than 0.0001.
* **The bookmaker set behind the average and maximum changed from August 2025.** The maximum's overround median went from 1.002–1.008 to 1.028. About 5,000 test rows are affected. To document, not fix.
* **Clean:**
  * links;
  * duplicates;
  * calibration by season and event;
  * no single-book or maximum-based average;
  * no in-play prices overall.
* **Small:**
  * 19 matches unlinked by name or date typos;
  * one walkover in training (`wta|2014-W-INT-USA-1A-2014|QF|wta:201320|wta:201447`).

## 6. Checks that came back clean

* **The label and side A:** `a_won` matches Stage 0; side A is random.
* **Best-of and rounds:** best-of fits every score; round codes fit the levels.
* **The odds column:** equals Stage 1 on every match, and its log-odds are exact.
* **The definition test (double faults):** no tour-season but WTA 2015 fails it.
* **The other Slams against the hand charting:**
  * AO, Wimbledon and the US Open agree within 0.2 points of first serves in, 2019–25;
  * RG 2019–21 agrees too.
* **Serve speed:**
  * no unit errors; Sackmann's km/h to mph ratio is 1.604–1.616 in every file;
  * no duplicate rows;
  * independent copies agree (Sackmann against Hawk-Eye SD 0.42 km/h);
  * the agent's recomputation of `spd_L` equals `adaptive/columns.parquet` exactly.
* **Surface-switch inputs and context columns:** no breaks beyond partial seasons.

## 7. Suggested fixes (none applied)

1. **Stage 0 corrections table**, applied like the decided Slam box-score overrides:
   * WTA 2015 window: serve points + double faults;
   * Roland Garros 2022–25 and the Olympics 2024: drop the first/second-serve split (first serves in, first- and second-serve points won), or take RG's statistics where held (2025); keep aces, double faults and break points;
   * exchange the 88 swapped box scores;
   * drop the copied ones (Adelaide 2 2022 and the 39 repeats);
   * finish the id remap;
   * take ages from each player's known birth date.
2. **New Stage 0 checks** at every build:
   * the games identity with the exchange test;
   * the winner-points share per event;
   * the double-fault definition test;
   * verbatim repeats;
   * new ids whose name has earlier matches;
   * per-edition first serves in against the referees. This is the data-continuity contract (§4.4), extended to the Sackmann years.
3. **Odds** (`stage1_odds.py`):
   * blank the average when two or more agreeing books oppose it, or when it exceeds the maximum;
   * orient name-swapped rows by result;
   * never link a row without a score.
   * Rebuild to restore 2018.
4. **Products:** centre the O and D ratings on a fixed reference group (for example main-tour players active in the past 52 weeks) before multiplying. Decide once whether ITF box scores enter the IOS at all.
5. **Workload after the splice:** fill the lost women's qualifying and WTA 125 matches from the WTA API (the data-continuity proposal 4.5). Until then, treat `sets_14d` and the surface-season pair as unreliable for women from June 2026.
6. **Speed** (`panel.py`, `features.py`):
   * start each window robustly (the median of the first rows);
   * prefer the point mean when a key statistic differs from it by more than 5 km/h;
   * drop rows with average ≥ maximum or second-serve average ≥ first, and copied blocks;
   * bands of about 150–235 km/h for men and 125–205 for women;
   * a court-level check at the Slams.
7. **Then rebuild the chain.** Stage 0 → Stage 1 → the feature studies → `model_frame.py` → the fits (the offset-Elo decision lists the steps). Compare the rebuilt model with the current one on the same matches.

## 8. Files and reruns

| What | Where |
|---|---|
| Code | `src/eda/input_data_audit/`: `common.py` (paths, loaders, detectors), `box_checks.py`, `model_frame_checks.py`; the agents' exploratory scripts in `speed/` (a01–a21) and `odds/` (a01–a14) |
| Tests (8) | `test/input_data_audit/test_detectors.py` |
| Evidence | `data/studies/input_data_audit/`: `box_*` and `frame_*` tables and `box_summary.json`, `frame_summary.json`; the agents' tables in `speed/` and `odds/` |

```
./python.sh src/eda/input_data_audit/box_checks.py          # about 2 minutes
./python.sh src/eda/input_data_audit/model_frame_checks.py  # about 15 seconds
./python.sh -m pytest test/input_data_audit -q
```

* **The agents' scripts** are exploratory and run from the repo root in their numbered order (`./python.sh src/eda/input_data_audit/speed/a06_ao_paired.py`, and so on). They write to `data/studies/input_data_audit/speed/` and `odds/`. The large intermediate parquet files were not kept, and the first scripts rebuild them.
* **Read-only.** No Stage 0, Stage 1, feature or model file was modified.
