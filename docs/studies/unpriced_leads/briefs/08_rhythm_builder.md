## Shared builder context (identical at the top of both round-2 briefs)

You are one of two builders in a small agent team in the tennis-predictions repository at `C:\Users\zerom\Documents\Tennis-predictions` (Windows; `./python.sh` runs the project's `tennis` conda environment). The lead (another Claude session) runs the study `docs/studies/unpriced_leads/`. **Read `CLAUDE.md` first (its rules bind you), then `docs/studies/unpriced_leads/process_log.md` §§ 1–3 and the chronology, and the docstring of the harness `src/eda/unpriced_leads/screen.py`.**

**The job:** build the new candidate statistics listed in your role section below, exactly as defined there (where a definition leaves a choice open, choose, and record the choice), and screen each one on seasons ≤ 2024 with the harness. This is discovery evidence for choosing five lead groups that will be pre-registered and tested later on 2025–26. Nothing is tested on 2025–26 now.

**Blinding (hard):**
* Outcomes are read only through the harness (`load_frame()`, the lenses), which reads matches before 1 Jan 2025 only and asserts it.
* You must compute each statistic's values for **every** frame match, 2013–2026 (the registration needs them, and coverage in 2025–26 is reported), but you never compare a 2025–26 value with that match's result. Earlier matches' facts (their scores, box scores, `won`) are legitimate inputs to a later match's statistic, as in every builder of the model's inputs.
* Never read `a_won`, `y` or a result of any match from 1 Jan 2025 on for scoring, plotting, or "a quick look". No market-response reading (line move, the close's loading) on 2025 or later either: those are registered secondaries.
* Matches from 29 Jul 2026 (the sealed set) may appear only as rows whose statistic values you compute; do not count, summarise or inspect them.

**Timing (hard):** every statistic must use only matches that surely finished before the match it describes.
* Player statistics: build from `H.long_table(player_cols=[...])` (each player's own matches at every level, in the player's own order, with the clock's `es`, `lf`, `start`, and `rest_days`, `rest_min`), taking values from STRICTLY EARLIER rows of the same player (`groupby("player_id")` + `shift(1)` or exclusive cumulative sums along `k`), then align to the frame with `H.at_frame(values, col, frame)` → (A's value, B's value); the screened column is A − B unless the role says otherwise.
* Run `H.timing_probe(build_fn, L, value_cols)` on every builder (it scrambles results after three cut days and checks (a) no earlier value moves and (b) no first-post-cut value moves; both counts must be 0). Pass the long table with every column the builder reads. Record the probe's output.
* Anything that combines different players' results (a field average, a venue norm, a joint fit) must read the state as of the match's earliest start `es` and count results from `lf + 1` (CLAUDE.md "Feature timing"); flag it and say how you ensured it; prefer constructions that avoid it. A constant fitted once on matches that all finished before 2013 (as below) is safe.

**Screening:** for each statistic, `H.screen(frame, x, name, kind)` on the raw A − B and on its orthogonal part (`H.orthogonal_part(frame, x)`, named `<name>__orth`), then `H.summarize()`. Also report `H.coverage_2025_26()` (outcome-free, on `H.frame_outcome_free()`; seasons 2025–26 there end at the frame's last date, so restrict to matches before 29 Jul 2026 for the count).

**Deliverables:**
1. Code: `src/eda/unpriced_leads/build_<your role>.py` (one command; deterministic; it writes the values for every frame match).
2. Values: `data/studies/unpriced_leads/candidates/<your role>/values.parquet` (match_id, and per statistic `<name>_a`, `<name>_b`, `<name>` = A − B), with no result column.
3. Readings: `data/studies/unpriced_leads/candidates/<your role>/long.csv`, `summary.csv`, `probes.json`, `coverage.json`.
4. A memo `docs/studies/unpriced_leads/team/<your role>.md` (1,000–2,500 words): each statistic's exact construction and the choices you made; its probe result; coverage (2013–24 and 2025–26, by tour); its readings (raw and orthogonal: pooled z, eras of the same sign, model lens, move lens, R²); what looks promising and what does not; caveats (data faults, coverage holes, near-copies of each other or of pool columns).

**Constraints:** read-only on the repository except your code file, your `candidates/<your role>/` folder and your memo. No Git command that changes state. No GPU. No download (if a statistic needs data the project does not hold, say what and stop on that one). Reporting: + = the player higher on the statistic beats the close; "better/worse" only when an interval clears 0; never "tie"; label observed vs inference. Under the null, the harness's z has SD about 1.08 (self-test), and you will run many screens: read single |z| < 3 as weak.

Finish by writing the files, then reply with a 10-line summary.

## Your role: S2a, the rhythm-and-body builder

Role name: `rhythm` (code `src/eda/unpriced_leads/build_rhythm.py`, folder `data/studies/unpriced_leads/candidates/rhythm/`, memo `docs/studies/unpriced_leads/team/rhythm_builder.md`).

**Read first:** the rhythm-and-body scout's memo `docs/studies/unpriced_leads/team/rhythm_body.md` (§§ 3, 5, 6 define what you build) and `rhythm_body_ideas.csv`; its outcome-free scripts in `data/studies/unpriced_leads/team/rhythm_body/` (`peek_*.py`, `prevalence.py`, `novelty.py`: where the doubles rows, the start and end times and the crosswalks live, and how it linked them); the market practitioner's § 3.6 (`team/market_practitioner.md`: rest hours from OddsTrader's listed times; note it judged the clock day-level and TennisLive's times placeholders, while the scout found real starts in the clock's link files: settle which source is real per season and tour, and record it).

**Build (values for every frame match; discovery on ≤ 2024; each statistic A − B unless stated; registered directions are the scout's § 7 expectations, and you report both signs):**
1. **RB01, hidden doubles play:** doubles matches played in days d−7..d−1 (clock day `obs`), at this event and elsewhere, as log1p counts, both parts separately and summed; same-day doubles left out; men 2013–17 from Sackmann's event-level doubles (entered in this event's doubles draw; doubles at the previous event) as a separate, flagged version. Report coverage by tour and season, and the covariate shift the scout flags (ITF doubles entering TennisLive from 2020): build a tour-level-doubles-only variant as the primary if the shift is material.
2. **RB03 and RB04, rest in hours:** rest_h = this match's start minus the previous played match's end (start + minutes where the end is missing; the same rule in every season), at any level; RB03 x = s(rest_A) − s(rest_B), s(h) = max(0, 24 − h)/24; RB04, when both rests are under 72 h, clip(rest_A − rest_B, −36, 36)/12. Also RB06 (last to finish on its day at its event × first or second on court today) if the order of play can be recovered. Use only times known before the match: the previous match's end is a result of an earlier match (allowed); this match's own start is a schedule fact (allowed).
3. **RB13, qualifier and lucky-loser arrival cost:** for a qualifier or lucky loser in the first main-draw match: log1p(points played in this event's qualifying, from box-score serve-point denominators), hours since the qualifying final ended, the LL flag; 0 for direct entrants. Secondary: LL × matches already played here (U-138; the store's column, see `store_registry.csv`).
4. **RB10, style-specific ageing:** (age − 29)+ × RS, RS = D̄/(|Ō| + |D̄|) from the player's own per-surface IOS offence and defence values (the store's `pp__ios_srfO_*`, `pp__ios_srfD_*`, which are leak-proof); A − B.
5. **RB15, health beyond results:** a retirement or walkover given at any level in the last 28 days without a 42-day break since (own sequence), A − B; and its Slam-first-round form (the market practitioner's MP-22).
6. **RB14, the bye seed's cold start:** at 96-player (and 56/48-player) draws, the seed's first match (after a bye) against an opponent who has already played at the event: an indicator signed toward the opponent; compare with U-138.
7. If time allows: RB02 (surface rust counting doubles), RB05 (rest relative to a long previous match), RB20 (excess on-site cost: minutes or points played at this event beyond what the opponents' strength implies), RB23 (short off-season).
8. Screen the pool's U-138 (matches here) and U-132 (days since the last match) beside yours for comparison.

**Also report:** the correlations of your statistics with `sets_14d`, U-138, U-132 and each other; for the time-based ones, the share of 2018–24 matches where BetOnline's last line (`t_bol_close` in `data/studies/bet_timing/frame.parquet`) predates the information (the previous match's end) — the stale-line trap both scouts flag — and the close-lens reading restricted to matches where the line postdates it.
