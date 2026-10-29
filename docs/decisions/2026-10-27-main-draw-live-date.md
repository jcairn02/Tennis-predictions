# A live main-draw match is dated by its main draw's first day

**The owner's decision, 27 October 2026**, on Claude's recommendation after the finding of 25 October (master
pipeline process log, Part 17, P17.6 and P17.12). Verbatim:

> switch the date fix on, dont built predictions for womens rounds 1, we arent betting women yet

**The design is Claude's** (an agent's choice, in the production-integrity plan's sense). The owner decided that the
fix is on. The second half of the instruction is recorded in the
[earlier-rounds decision](2026-10-24-earlier-rounds-from-tennislive.md): a women's main-draw round 1 on its first day
stays unpredicted.

## Why

* Stage 0 dates a whole event by its main draw's first day (rule C05: the earliest main-draw row). Many inputs count
  windows of days from that date: in the 22 Oct qualifying replay, a moved event date moved 19 inputs.
* A live main-draw row took its event's date from the event's earliest Tennis My Life row. In 2026 Tennis My Life
  dates each match by its day, and files a men's qualifying under the main draw's id, so that row was a qualifying one.
  Live rows count as main-draw rows, so the whole event moved back to the qualifying's day.
* **The live runs of 11-25 Oct:** of the 148 men's main-draw matches they predicted, 129 were dated before training's
  date (123 by one day, 6 by two). The women's were all right, because Tennis My Life carries no women's qualifying.
* The replay proofs could not see it: a replay builds each target from its own published row.

## Decision

* **A live main-draw row takes the main draw's first day** (`src/eda/prediction_run/live_rows.main_draw_date`). That
  is the earliest day known of the event's main draw, from these sources, none of which can come before it:
  * the earliest main-draw row Tennis My Life holds of the event;
  * each main-draw match of the event in the matchups CSV, by the linker's day where it gives one, else by its own
    (UK) day. The linker's day (A2, `event_main_date`; `src/pipeline/qualifying.main_draw_first_day`) is the earliest
    start among the event's main-draw matches on TennisLive and the listed match's own. It is read in the venue's time
    zone (TennisLive's country of the event and its city, through the timing study's tables), because Tennis My Life
    dates a match by its local day.
* **Tennis My Life's rows alone do not settle it** (the version shown to the owner on 25 Oct). Its file of events
  under way dated Almaty's and Brussels' first main-draw day, 19 Oct, as 20 Oct from 19 to 22 Oct, and corrected it on
  23 Oct. On those days it alone would have dated 62 matches a day late.
* **A UK day is not a local day in the far east.** Auckland's 11:00 start is 22:00 UTC the day before, so the CSV's
  own day alone would date that event a day early (Tennis My Life dated Auckland 2026's first main-draw day Monday 12
  January). That is why the linker's day is read in the venue's zone.
* Qualifying rows are unchanged: their main draw's start comes as the estimate decided on 22 Oct.
* **On by default from 27 Oct 2026.** `LIVE_MAIN_DRAW_DATE=0` reproduces the runs before.

## Evidence

* **Every live run of 11-25 Oct, rebuilt from what it could see** (process log P17.12). Each run's men's main-draw
  matches were dated from three sources: the archived copy of Tennis My Life's file of events under way in effect at
  the run's start, TennisLive's results finished by then, and the run's own matchups CSV. They were set against
  training's date of each event (today's Stage 0):

  | Rule | Right | 1 day early | 2 days early | 1 day late |
  |---|---|---|---|---|
  | Before (the runs as they ran) | 19 | 123 | 6 | 0 |
  | Tennis My Life's main-draw rows first (the 25 Oct version) | 86 | 0 | 0 | 62 |
  | **The earliest day known (decided)** | **148** | 0 | 0 | 0 |

* **The forecast effect** (25 Oct, the three men's finals run with and without the fix): 18 or 19 of 57 inputs moved,
  mostly the serve and return forms. At each final's own price the forecasts moved +0.005, −0.025 and +0.025 points,
  far below the 1-point bar. What the fix gains is that live inputs equal training's.
* **A live link on 27 Oct** (scratchpad `e2e_date.py`; two TennisLive requests, with receipts): a made-up Basel round-2
  listing linked, with TennisLive's first main-draw day 26 Oct in the venue's zone; the run's live row dated the event
  26 Oct.
* **Tests:**
  * `test/prediction_run/test_prediction_run.py`: on by default; `0` gives the old rule; a late Tennis My Life date
    corrected by the linker's day and by a listed day 1; a far-east local day standing for the UK day.
  * `test/master_pipeline/test_earlier_rounds.py`: TennisLive's first day in the venue's zone (Brussels, Auckland,
    Adelaide); the listed start before any match has finished; the linker writes it.

## Not covered

* **TennisLive not answering:** each row keeps its own UK day, beside Tennis My Life's rows, so a far-east morning
  start could date the event a day early until Tennis My Life publishes a main-draw row.
* **A country with several time zones whose city the timing study's tables do not list:** the UK day is used. It
  differs from the local day only for a morning start at UTC+11 or more.
* **Women** are dated by the same rule, though not bet now (the owner, 27 Oct: "we arent betting women yet").
