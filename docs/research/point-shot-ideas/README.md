# Ideas for point-by-point and shot-by-shot tests, waiting for better data

**Status: a list of untested ideas, not a decision.** Started 8 October 2026 at the owner's request: "Add this to a list somewhere of potential ideas for point by point /shot by shot testing in the future with better data."

Each entry says where the idea came from, why it is on the list, what data it needs and what the project already holds. Add new ideas at the end with their date. When one is tested, link the result under it and keep the entry.

Labels: **observed** (measured or seen in the files), **inferred** (a reading), **suggestion** (a proposal), **unknown**.

* **Point-by-point:** one record per point, such as who won it, the score, the serve's speed and direction.
* **Shot-by-shot:** the rally itself: every stroke, how long the rally lasts, how it ends, where the ball goes.

## 1. Physical condition from the rally, not style (shot-by-shot)

**Added 8 Oct 2026**, from the follow-up to the [shot-level study's Stage 3](../../studies/shot_level/stage3.md).

**The idea** (*inferred, untested*). The serve-speed signal catches a player who is physically up or down right now. A player's state might show in his rallies too, measured against his own normal:
* groundstroke speed dropping;
* more running per point;
* rallies getting shorter;
* errors creeping up.

**Why it is on the list.**
* *Observed.* Serve-speed change is the one point-derived signal that replicated. On 7 Oct 2026 the owner made it part of the current best model ([decision](../../decisions/2026-10-07-speed-nudge.md)). It measures a state, how a player is right now.
* *Observed.* Every style trait tested so far tied with the close or did worse:
  * rally length, how points end, net play, return depth and the wing ([shot-level study](../../studies/shot_level/stage3.md));
  * momentum, streaks, big-point play and tempo ([point-sequence study](../../studies/point_sequence/README.md)).
* *Observed.* The shot-level features were long-run levels, shrunk to the tour's average. The only "change against the player's own normal" built there was serve speed (`spd1_change`).
* *Observed.* The closest test so far is the point-sequence study's women's within-match fade (first serves in, double faults, tempo), and it tied. No rally measure has been built as a change against the player's own normal.

**Data on hand** (*observed*; never used for features):
* **ATP tour, 2021–2024:** Hawk-Eye Court Vision files for 4,570 tour-level matches: 298 in 2021, 1,348 in 2022, 791 in 2023, 2,119 in 2024, and 14 from 2018.
  * Per point: ball positions at hit, bounce and net, speeds, net clearance, serve type and outcome.
  * Source: the [ATP pipeline dump](../../studies/atp_pipeline_handoff/README.md), folder `court_vision/`; also embedded in `infosys_full`.
* **Australian Open and Roland-Garros, 2022–2024:** the Court Vision JSON of 1,225 matches, with the ball's hit, peak, net and bounce positions for every stroke ([AO/RG points](../../studies/ao_rg_points/README.md)).
  * The same copy holds the JSON of 2019–2021 (802 matches), not fetched.
* **Rally length and errors** for every charted or tracked match: the shot-level study's point table (6.2 million points). It is thin per player.

**Better data that would make it testable at scale:**
* tracking for every tour-level match, on both tours and at Challengers;
* 2025–2026, so the test can run on the closed holdout;
* data arriving daily, so the measure is current at bet time. The serve-speed nudge keeps 66–92% of its gain with today's data delays ([latency follow-up](../../studies/serve_speed_tabpfn/latency.md)).

Collection is covered by the [scraping approval of 8 Oct 2026](../../decisions/2026-10-08-scraping-approved.md), Court Vision decryption included.

**How it could be tested** (*suggestion*):
* Build each measure per player as an as-of filter against his own normal, the way the [serve-speed TabPFN study](../../studies/serve_speed_tabpfn/README.md) built speed form.
* Centre by event or venue first, because measuring systems shift. The serve-speed study found Wimbledon's speeds 8.5 km/h higher in 2025 than in 2024 for the same men.
* Centring combines different players' results, so it must use the leak-proof clock ([timing decision](../../decisions/2026-10-05-match-timing.md)).
* Pre-register the test. Score it as a walk-forward adjustment on the current best model, both stages, and against the close.
* It counts if it replicates with an interval clear of zero.

**Unknowns.**
* Whether the ATP files' speeds cover every shot or only the serve.
* Whether any file carries player positions. If none does, running could only be estimated from the distance between a player's successive hit positions.
* How many players appear often enough in 2021–2024 to have a "normal" to measure against.

## Other open ideas, recorded elsewhere

Pointers only; the details stay in the linked write-ups.

| Idea | Kind | Where | What it needs |
|---|---|---|---|
| Rally style with complete charting. Up to about 1–2 milli-log-loss of edge (price off by about 2–3 percentage points) could hide in quick points, long rallies and net points | Shot-by-shot | [Shot-level Stage 3](../../studies/shot_level/stage3.md), parts C and the reading | Charting of every match: the features would capture about 50–60% of a player's true value instead of 15–34% |
| The rally's small gain on serve points since 2022, the one sign that rally data gains value with volume | Shot-by-shot | [Shot-level Stage 3](../../studies/shot_level/stage3.md), part A | More seasons of dense rally data, then a match-level test against the current best model |
| The serve-speed family together: the 14-day change, the within-match speed fade and box-score serve form | Point-by-point | [Point-sequence study](../../studies/point_sequence/README.md), section 6 | ATP non-Slam per-point speeds for 2025–2026; judged on the closed holdout |
| Serve speed for women | Point-by-point | [Serve-speed sources](../serve-speed-sources/README.md) | WTA tour-level speeds, which no free source holds for any year; the nudge is men-only |
| In-play: real matches cluster slightly more within sets than random point order, which an in-play price that treats points as independent could miss | Point-by-point | [Point-sequence study](../../studies/point_sequence/README.md), section 6 | In-play prices and live point data |
| Totals and handicaps: within-set serve clustering and rally style as inputs for games and handicap markets, not winners | Both | [Point-sequence study](../../studies/point_sequence/README.md), section 6; [shot-level Stage 3](../../studies/shot_level/stage3.md), "Not tested" | Whether Polymarket lists such markets, and their prices |
