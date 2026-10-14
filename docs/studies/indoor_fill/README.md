# The indoor input for every match: women's from the WTA's calendar and tennis-data's Court

9 October 2026 · For the owner, and for agents who build the current best model or its live inputs. **For an audit** of how the study was set up (the chronology, the choices set aside, how strongly each claim was checked, the weak points, how to reproduce it), read the [process record](process.md).

**The owner's request (9 Oct 2026):** "In my current best performing model the indoor/outdoor input is missing for every women's match. It could be filled from tennis-data.co.uk's Court column. Get this data and integrate it into our models training data sources after you've downloaded it all." And: "The 127 men's matches of the 2026 US Open are also missing it, obtain them if you can find them."

## In short

* **Done.** The model's `indoor` input now has a value for every match of both tours: the 32,507 women's matches and the men's 2026 US Open (127, outdoor). The chain builds it by default (`tabpfn_thinking/build_frame.py` calls `src/eda/indoor_fill/status.py`), and prediction runs build it for live matches.
* **Downloaded.** All 47 tennis-data.co.uk workbooks were fetched again, beside the shared dump. The Court of every model match was already on disk; the fresh copies add only ATP Beijing and Tokyo of 30 Sep – 6 Oct. The WTA's calendar was completed to 2010–2026.
* **One departure from the request, for the owner to confirm.** tennis-data's Court is wrong on 26 of the model's 1,609 events: 10 men's and 16 women's (Stuttgart 2013–17 "outdoor", for one). Each was checked against the venue: seven events by web search, three from general knowledge. So the women's value comes from the WTA's own calendar, which was right on all 16, and tennis-data's Court fills what the calendar lacks (Eastbourne). The men keep TML's flag, which was right on all 10. Court alone would differ on 371 women's matches (1.1%); `STEPS` in `status.py` sets the order.
* **Harm check** (fixed before any fit; + = the fill better, 2020–2024, both stages): at Pinnacle's opening line +0.007 [−0.014, +0.029] mLL per match, unresolved, P(better) 0.75; women +0.013 (P 0.76). At the close −0.002 [−0.016, +0.013], P(better) 0.41. No over-reaction. Outcome under the rule: adopt, claiming no edge.
* **Live:** with every tennis-data link of a season removed, the rule gives every 2018–2026 match its training value. The gate marks "do not bet" any live match whose value stays unknown.

## The test plan (written before any fit ran)

**The change.** One input, `indoor`, of the current best model (57 inputs, Pinnacle-first odds). Until now it was Stage 0's flag (Tennis My Life's event field) for the men and missing for every women's match. The new rule (`src/eda/indoor_fill/status.py`) is:
* **Men:** Stage 0's flag, as before; tennis-data's Court only where TML gives none (the 127 matches of the 2026 US Open).
* **Women:** the WTA's own calendar (its `inOutdoor` per edition); tennis-data's Court where the calendar lacks the edition (Eastbourne 2013–2025).

**Why not tennis-data's Court alone.** Checked event by event before any fit, it is wrong on 26 of the frame's 1,609 events (1.6%; § "The data"). The other source was right on every one checked against the venue.

**The comparison.** The lean review's arm A2 (the Pinnacle-first frame without `ios_points_short`: the decided 57 inputs, on the tables of 8 Oct) against the same frame with only `in_indoor` replaced.
* Fits: seasons 2019–2024, seeds 0–3, each fed the close and Pinnacle's opening line, as the lean review fitted A2. `fits.py --check` shows the two arms' jobs differ in the indoor column alone.
* Scored: 2020–2024, both stages, through `compare.py`'s recipe, paired by seed. + = the fill better.
* Yardsticks: Pinnacle's opening line (O, the declared primary, as in the lean review) and the close (C).
* Populations: both tours (primary), women, men. The men's training rows do not change in 2013–2024, so any men's change comes through the pooled fit alone.
* Also, for the record: `compare.py --candidate` against the frozen reference (its input check, and both stages at the close).

**How it arose and what it costs** (adoption framework §§ 2–3).
* It widens an input the model already has to the tour that lacked it, from data the project already collects: tennis-data feeds the reference's odds, and the WTA adapter's calendar is already read by prediction runs. It was not found in the scored seasons.
* Free and reversible: `--indoor-men-only` rebuilds the old input exactly. No new live feed: a prediction run reads the WTA's calendar page for the season.
* So the outcome test is a harm check, not a search for an edge. The input check is the gate.

**The rule, fixed now.** Suggest adoption (the rule stays the chain's default) unless one of these holds:
1. both tours, both stages, at (O) or at (C): the 95% interval lies below 0 (clearly worse);
2. women, both stages, at (O) or at (C): clearly worse;
3. the realisation slope at (O), both tours, falls below 0.9 while A2's is above it (the change makes the model over-react).

Otherwise: adopt, and claim no edge for it.

**Read before the scores: the input check.** By construction the women's `indoor` goes from always missing to known, so `compare.py` will flag it in every women's season. That is the fill itself, not finding #6, provided the women's indoor share moves by season only as the calendar does. The season profile is reported in § "The data".

## The data

### The download (9 Oct 2026)

* **tennis-data.co.uk:** every season workbook the site lists, 47 of them (ATP 2000–2026, WTA 2007–2026), fetched again by `snapshot.py` into `data/raw/indoor_fill/tennis_data_couk/`, one receipt each, about 2.5 s apart. Results in [`snapshot.json`](../../../data/studies/indoor_fill/snapshot.json).
  * 43 are the same bytes the shared dump was staged from (5 Oct 2026).
  * ATP 2026 gained 62 rows at its end: Beijing and Tokyo, 30 Sep – 6 Oct, both "Outdoor". Its 2,204 earlier rows are unchanged, so restaging keeps every Stage 1 link valid.
  * ATP 2002, 2004 and 2006 are served again. The dump never held them; they predate the model's history.
  * WTA 2026 is unchanged since 27 Sep.
  * So the Court of every model match was already on disk, including the 127 matches of the 2026 US Open ("Outdoor"; the ATP Grand Slam partition of 5 Oct holds 4 × 127 rows).
* **The shared dump was not touched.** While this ran, other sessions' candidate builds were reading `data/dump/` through junctions, and restaging it would have changed their inputs mid-run. The routine refresh (`src/ingest/refresh_odds.py`, its `tennis_data` step) restages it; run it when no build reads the dump.
* **The WTA's calendar:** the seasons the WTA adapter lacked, 2010–2015 and 2017, fetched with `wta.py --calendar-only` (7 requests). The calendar pages now cover 2010–2026.

### tennis-data's Court against a second source (`crosscheck.py`)

Every model event (the Pinnacle-first frame: 67,226 matches, 1,609 events). No event's rows mix "Indoor" and "Outdoor".

| Tour | Second source | Events agreeing | Matches agreeing |
|---|---|---|---|
| Men | Stage 0's flag (TML) | 849 of 859 | 34,319 of 34,592 (99.2%) |
| Women | The WTA's calendar | 721 of 737 | 31,673 of 32,044 (98.8%) |

13 events have no second source: the men's 2026 US Open (TML blank) and Eastbourne 2013–2025 (absent from the WTA's calendar until 2026). tennis-data says "Outdoor" for all 13, which is right.

**The 26 disagreements: tennis-data is wrong every time.**

| Event | Seasons | Matches | tennis-data | Right | Venue |
|---|---|---|---|---|---|
| São Paulo | 2016–17 | 54 | Indoor | Outdoor (TML) | Clube Pinheiros, outdoor clay ([2016 Brasil Open](https://en.wikipedia.org/wiki/2016_Brasil_Open)) |
| Santiago | 2020–26 | 189 | Indoor | Outdoor (TML) | San Carlos de Apoquindo, outdoor clay ([2023 Chile Open](https://en.wikipedia.org/wiki/2023_Chile_Open)) |
| Antalya | 2021 | 30 | Indoor | Outdoor (TML) | Outdoor hard ([2021 Antalya Open](https://en.wikipedia.org/wiki/2021_Antalya_Open)) |
| Stuttgart | 2013–17 | 135 | Outdoor | Indoor (WTA) | Porsche Arena, indoor clay; tennis-data itself says "Indoor" from 2018 |
| Zhuhai, Elite Trophy | 2015–19 | 75 | Indoor | Outdoor (WTA) | Hengqin International Tennis Centre, outdoor hard ([WTA Elite Trophy](https://en.wikipedia.org/wiki/WTA_Elite_Trophy)) |
| Dubai | 2016 | 27 | Indoor | Outdoor (WTA) | Outdoor hard, every year |
| Taipei | 2017–18 | 61 | Outdoor | Indoor (WTA) | Taipei Arena, then Heping Gymnasium, indoor hard ([2017 Taiwan Open](https://en.wikipedia.org/wiki/2017_Taiwan_Open)) |
| Tokyo | 2018 | 27 | Outdoor | Indoor (WTA) | Arena Tachikawa Tachihi while Ariake was rebuilt ([2018 Toray Pan Pacific Open](https://en.wikipedia.org/wiki/2018_Toray_Pan_Pacific_Open)) |
| Guadalajara, WTA Finals | 2021 | 15 | Indoor | Outdoor (WTA) | Panamerican Tennis Center, outdoor hard |
| Tallinn | 2022 | 31 | Outdoor | Indoor (WTA) | Forus Tennis Center, indoor hard ([2022 Tallinn Open](https://en.wikipedia.org/wiki/2022_Tallinn_Open)) |

**How the venues were checked** (9 Oct 2026).
* The linked rows by web search, through a search tool's summaries of the results, not the pages themselves. Santiago was searched for 2023 only; its other seasons assume the same venue.
* Stuttgart, Dubai and Guadalajara 2021 rest on general knowledge and were not searched.
* So each tour reads its better source first, and tennis-data's Court fills only what that source lacks.
* The [process record](process.md) lists every check and how strong it is.

### The rule's values on the model's matches

| Tour | Source | Matches |
|---|---|---|
| Men | Stage 0's flag, unchanged | 34,592 |
| Men | tennis-data's Court (the 2026 US Open, outdoor) | 127 |
| Women | The WTA's calendar | 32,044 |
| Women | tennis-data's Court (Eastbourne 2013–2025, outdoor) | 463 |

No match is left unknown, and no value the model already had changes (`arm.py`'s checks; [`arm.json`](../../../data/studies/indoor_fill/arm.json)).

**Season profile.** The share of indoor matches moves with the calendar only:

| Season | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Men | 19.6% | 16.4% | 17.2% | 15.2% | 15.2% | 16.0% | 16.3% | 29.9% | 16.2% | 17.8% | 14.0% | 14.0% | 14.5% | 4.1% |
| Women | 11.0% | 9.5% | 8.7% | 8.7% | 11.3% | 11.3% | 7.6% | 7.9% | 12.5% | 8.2% | 5.5% | 5.3% | 6.5% | 7.8% |
| Women's indoor events | 10 | 9 | 8 | 8 | 10 | 10 | 7 | 3 | 10 | 7 | 5 | 5 | 6 | 6 |

2020 was a short season with a long indoor autumn for the men. 2021 added autumn indoor events for the women (Courmayeur, Ostrava, Nur-Sultan, the second Cluj-Napoca). 2026 runs to September, before the indoor season.

## Can a prediction run reproduce it?

A live match has no tennis-data row: tennis-data publishes a match after it is played, and a prediction run's Stage 1 row has no link. `live_check.py` drops every tennis-data link of a season (the worst case: nothing of the season published) and runs the rule again, season by season.

| Tour | Matches | Same value | Unknown | Different value |
|---|---|---|---|---|
| Men | 34,719 | 34,719 | 0 | 0 |
| Women | 32,507 | 32,211 | 296 | 0 |

* **Men:** TML's flag, which live rows carry; the 2026 US Open from its previous edition.
* **Women:** the WTA's calendar, which lists an edition before it starts.
  * 43 of 2026's 45 events match their edition by id: TML's ids are the WTA's own.
  * The other two, the Australian Open and Roland Garros, match by name. Stage 0 files the women's Slams under ATP-style ids (580, 520); the WTA's are 901 and 903.
  * Events the calendar misses without tennis-data's Location take the previous edition's value, which equals the training value in every case: Eastbourne; Roland Garros under Sackmann's ids, to 2018; Cincinnati 2020, played in New York.
* **The 296 unknowns** are Eastbourne 2014–17 and Roland Garros 2016, under the older ids of Sackmann's files, which neither the WTA's calendar nor an earlier edition matches without tennis-data's Location. No live match will carry those ids.
* **No live value differs from the training value.** A live match whose value stays unknown is marked "do not bet" by the gate.

**The prediction run's changes.**
* `run.py --refresh --matchups` fetches the WTA's calendar pages of the women's live seasons again, so a new edition is listed.
* `--build` records each live match's indoor value and source in `live_indoor.csv`.
* The gate (`gate.py`) marks "do not bet" any live match whose `indoor` is unknown.

## Results (read after the test plan above was fixed)

**The harm check:** the lean review's arm A2 against the same frame with `indoor` filled. 2020–2024, seeds 0–3 paired, both stages; mLL per match, + = the fill better ([`score_summary.json`](../../../data/studies/indoor_fill/score_summary.json)).

| Yardstick | Population | Matches | Estimate [95%] | P(better) |
|---|---|---|---|---|
| Pinnacle's opening line (primary) | Both tours | 20,979 | +0.007 [−0.014, +0.029] | 0.75 |
| | Women | 9,760 | +0.013 [−0.023, +0.050] | 0.76 |
| | Men | 11,219 | +0.002 [−0.020, +0.024] | 0.58 |
| The close | Both tours | 22,265 | −0.002 [−0.016, +0.013] | 0.41 |
| | Women | 10,593 | +0.001 [−0.028, +0.030] | 0.53 |
| | Men | 11,672 | −0.004 [−0.031, +0.023] | 0.38 |

* All six are unresolved. Every level and season is too ([`scores.csv`](../../../data/studies/indoor_fill/scores.csv)).
* Stage 2 changes nothing here: the women's speed column is 0, and the men's inputs did not change.
* **Realisation at the opening line, both tours:** A2 1.056, the fill 1.061. The model does not over-react.
* **Size:** the model beats its calibrated opening line by +1.254 mLL (A2) and +1.262 (the fill), and its close by +1.091 and +1.089.
* **The rule's outcome: adopt, claiming no edge.** None of its three conditions holds.

**Against the frozen reference** (`compare.py --candidate data/studies/indoor_fill/arm`, for the record; [summary](../../../data/studies/indoor_fill/arm/vs_reference_2026-10-08/summary.json)).
* The candidate also carries two decided changes the reference predates: the Pinnacle-first odds input and the dropped `ios_points_short`.
* Both stages at the close, + = the candidate better: both tours +0.007 [−0.306, +0.320] (P 0.52), men −0.137, women +0.166, all unresolved. The Pinnacle-first instance alone read +0.01 [−0.29, +0.31].
* **The input check** flags `indoor` as "uneven" in exactly the 14 women's seasons, where it goes from missing to known. No men's season is flagged, and no other input except the decided odds input changed. This is the fill itself, not finding #6: the season profile above moves with the calendar.

**How to read it** (adoption framework).
* A free, reversible change that widens an input the model already reads, from data already collected. It was not chosen on the scored seasons.
* At the declared primary it points the right way, and nothing in the check suggests harm. So it is adopted, as the owner asked, with no edge claimed.
* The effect is small, as expected: the women's indoor share is 5–13% of matches, and the close already prices conditions.

**Under the decision recorded later that night** ([adoption by kind of change](../../decisions/2026-10-09-adoption-by-change-class.md), written after these results):
* The fill is a **Repair**: it restores lost coverage. The data evidence decides, and the comparison is a bug alarm, which is how this study used it.
* That decision's default harm tolerance is worse by more than 0.10 mLL with the whole 95% interval below 0. That is looser than this study's rule (any interval below 0). The readings pass both.
* The "uneven" flag is explained by its dose: missing to known, in the women's seasons only.
* **For the pooled record it names** (`data/studies/adoption_framework/class_record.csv`, not yet created when this was written), this study's readings are:
  * kind Repair; target Pinnacle's opening line, both tours, 2020–2024, both stages;
  * +0.007 mLL, SE 0.011 (20,979 matches);
  * at the close −0.002, SE 0.007 (22,265).

## What changed

* **`src/eda/indoor_fill/`** (new):
  * `status.py`: the rule;
  * `snapshot.py`: the download beside the dump, and its comparison;
  * `crosscheck.py`: the second sources;
  * `live_check.py`: the live simulation;
  * `arm.py`, `fits.py`, `score.py`: the harm check.

  Tests: `test/indoor_fill/` (13).
* **`src/eda/tabpfn_thinking/build_frame.py`:** the indoor input from `status.py`. The frame keeps each row's source (`indoor_source`) and the manifest the counts. `--indoor-men-only` builds the old input; a check shows it reproduces the 9 Oct instance's column exactly.
* **`src/eda/prediction_run/`:**
  * `run.py --refresh --matchups` refetches the WTA's calendar pages of the women's live seasons;
  * the build writes `live_indoor.csv`;
  * `gate.py` fails a live match whose indoor input is unknown.
* **Data:**
  * `data/raw/indoor_fill/tennis_data_couk/`: the 47 workbooks and their receipts;
  * the WTA's calendar pages of 2010–2015 and 2017 (`data/raw/point_sources/wta/calendar/`);
  * `data/studies/indoor_fill/`: the evidence, and the candidate's frame and fits (`arm/`).

**Not changed.**
* The shared tennis-data dump. Restage it with the routine refresh when no build reads it; Stage 1's links stay valid.
* `data/dump/points/wta/editions.parquet`, which still lists 2016 and 2018–2026 until the WTA adapter next stages. The rule reads the calendar pages directly.
* Stage 0: its `indoor` column, and with it the history check, are as they were.
* The frozen reference, the Pinnacle-first instance and the lean review's arms keep the old input (women missing). Their fits must not forecast rows built since: a forecast uses the template's fit on the same build (the prediction run's step 5).

**Open.**
* No instance of the template with the filled input is stored, by design: the next template build has it. A live forecast needs fits for its season (16 seeds), built when a task needs them.
* The tour-pooling study's strict expected failure (`test/tour_pooling/test_common.py`, "notour inputs name the tour") reads the 9 Oct instance and still fails as expected. It will pass, and so fail the strict marker, when that study is rerun on a build with the fill. Update its note then.
* Ambiguous: the WTA Elite Trophy 2023 (Zhuhai), on a covered outdoor court, is "indoor" in both sources and stays so (15 matches).

## To undo

* **The whole fill:** run `tabpfn_thinking/build_frame.py --indoor-men-only`, or make it the default again. Then the chain builds the old input.
* **tennis-data's Court instead of the WTA's calendar for the women:** put "own" and "event" before "calendar" in `STEPS["wta"]` (`status.py`).
