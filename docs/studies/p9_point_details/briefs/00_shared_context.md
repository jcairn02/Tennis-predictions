# Shared context for every agent of the P9 point-details study

28 Oct 2026 · Written by the lead (Claude Opus 5.5, session `4ad0f090-214d-4b51-b18a-41ad8262b656`) · Read this before your own brief.

## The request (the owner's words, verbatim)

> "24,997 of the 25,003 matches that have every point now carry the eight extra details per point, such as point duration and net approaches. Due to the P9 ATP infosys files
>
> IF AND ONLY IF, these were statistics not explored before properly for predictiveness (either from insufficient data, it not being relevant to the prodution model but now is, or we simply didnt have these stats before).
> Do a deep dive with a team of agents to see if any of these extra details could be promising as a new predictive statistics for either men or women (or both).
> The most important quality is orthogonality to the market information. Having it help the model predict better also helps."

## What the lead's gate found (observed; `data/studies/p9_point_details/field_profile.json`, script `src/eda/p9_point_details/field_profile.py`)

P9 is the ATP Stats Centre's own decrypted files for **men's** tour-level (250s to the Finals, main draws and qualifying) and Challenger singles (main and qualifying), January 2025 to about 18 October 2026: 25,003 matches with every point. The Grand Slams are not on this host. There are no women. Report: `docs/studies/serve_speed_acquisition/README.md` § 9. Tables: `data/dump/points/infosys_atp_recent/` (`points.parquet` = MatchBeats, one row per point; `rally.parquet` = the rally-analysis files; `matches.parquet`; `keystats.parquet`; `court_vision*.parquet`). Every column is stored as a string.

The eight "extra details" of the newer MatchBeats copy, field by field:
* `firstServer`: the server of the match's first point, on every match. Nothing new.
* `lastHitter`: empty on every point.
* `serveClassId`: 1 = ace, 2 = in play, 4 = double fault (99.99% agreement with the ending field). Nothing new.
* `tm1Shot`, `tm2Shot`: a recount of the older copy's `tm1Rally`, `tm2Rally` (equal on 95.6% of points; 23,382 points filled where the old count was 0). Rally length is known (`rallyLengthMissing == 'FALSE'`) on 38.7% of points: about 95% at the 1000s, 50–64% at the 250s and 500s, 25–35% at Challengers, by event. Raw values include garbage (−1,795 to 208,154): use 0–60 only.
* `pointDuration`: behaves as a duration at only 17 of 535 events (768 matches). Elsewhere rally-ended points get the same value as aces, and it has no link to the match clock. Unusable.
* `tm1AtNet`, `tm2AtNet`: flagged at 24 of 535 events (1,133 matches), the same 24 as the rally files' `t1NetPoint`/`t2NetPoint`. A duplicate, and thin.
* The momentum score per game: a running tally (+1 per hold, +2 per break, reset each set). A function of the score.

**The gate's verdict:** the deep dive goes ahead **only for men's rally length** (the statistic the shot counts name), with net play as a secondary where flagged. The reason: rally length was tested before only on data the [shot-level study](../../shot_level/README.md) itself called too thin. Its Stage 3: the noisy rally rates pass 15–34% of a player's true value into the pre-match feature, and edges of 1–2 milli-log-loss could hide. Its Stage 0 names "the men's tour-level gap of April 2025 to June 2026, between SirGenkii's files and TDI's window", which P9 fills. P9's rally data have never been read for prediction.

**Already closed elsewhere** (do not re-propose without a new reason): momentum, streaks, big-point leverage and tempo as player traits ([point sequence](../../point_sequence/README.md), at full depth); style rates as traits for winner markets (shot level; point sequence § 6). The one pattern the point-sequence study left open: **states, not traits** (how a player is right now: serve-speed change replicated; finishing form inconclusive).

## The plan

* **Round 1 (now, in parallel):** a builder (the rally data, linked to today's Stage 0, and the depth and reliability numbers); an ideas agent (at most ten statistics with mechanisms); a harness agent (the scoring machinery, the prices, the live model's forecasts, placebos). Nobody reads a candidate statistic's relation to match results.
* **Stopping rule (declared before any result):** if, on priced men's matches of 2025–26, the median player-match's 52-week count of points with a known rally length is less than 1.5 times what the same matches had without P9, the study stops there.
* **Then:** the lead pre-registers at most eight statistics and one combined score (frozen with a hash), the builder builds them, one scoring pass is run, and a red team checks it.
* **The end product** is an admission verdict per statistic for the [feature universe](../../feature_universe/README.md) (the pool), not a change to the model.

## The owner's thesis (from the lead's notes)

The owner wants an edge on the betting market from point-by-point data: offensive and defensive profiles of individual statistics, which are orthogonal to the market. Results-only information (W/L, rankings, Elo and other ratings) and points-won aggregates are assumed priced in: useful as controls, never as headlines. A null result against the close is read as a process flaw to hunt, never as proof the market is unbeatable. Rank results by their gain over the closing odds, never by their gain over Elo.

## The production model (what "the model" means here)

The live instance is named in `data/studies/master_pipeline/selected_instance.json`: today `template_2026-10-21b`, in `data/studies/current_best_model/template_2026-10-21b/`.
1. **Stage 1:** TabPFN-3.5 (local) on 57 inputs. They include the closing odds; Elo variants; the surface IOS offence and defence profiles of seven box-score statistics; the two-week form of twelve box-score statistics; sets in 14 days; age; context. Season Y is trained on 2013..Y−1, and 16 seeds are averaged.
2. **Stage 2:** the serve-speed adjustment, logit q = s_tour·η + b̃·`spd_L` (28-day speed memory).
3. **The five-pattern adjustment,** in the daily predictions only. It covers luck, the post-Slam letdown, fast courts × big servers, status over-priced, and rhythm.

CLAUDE.md: "New features and studies are compared against both stages, never the TabPFN fit alone." Stage 0 (today's shared tables) is `data/studies/predictability_diagnostic/stage0_matches.parquet`. The match clock is `data/studies/match_timing/timing.parquet` (`es` = earliest possible start; `lf` = latest possible finish; a result counts from `lf + 1`).

## Rules for every agent

* **Read** `CLAUDE.md` (sections "Feature timing", "Research discipline", "Environment", "Git and working files") before you start.
* **Python:** `./python.sh` from the repository root (Git Bash). If it fails, stop and report; never fall back to another interpreter.
* **The machine is shared** with other sessions, and the owner may run a bet-day prediction. Keep jobs modest: at most 4 worker processes, no GPU, no TabPFN fit, nothing running after you finish.
* **Git:** no command that changes state. Never delete or overwrite files you did not create. Other studies' code and tables are read-only: import them, never edit them.
* **Write only** in your brief's own paths.
* **Labels:** every claim is **observed** (computed or read here, with the file), **inferred**, or **unknown**. Compute every number before you state it, and say which file holds it.
* **Log as you go** in your memo's "Process notes" section: what you tried, what failed, the variants and why you chose one. The lead copies these into the study's process log.
* **Outcome discipline:** only the harness agent reads match results, and only for the price, the model and placebo features. Nobody relates a rally statistic to match results before the lead's pre-registration is frozen. Point winners inside a match are raw material for the features of *later* matches. Using them that way is not reading an outcome.
