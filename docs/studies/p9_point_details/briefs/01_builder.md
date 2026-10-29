# Brief 01: the builder

You are the builder of the P9 point-details study, in the Tennis-predictions repository (`C:\Users\zerom\Documents\Tennis-predictions`). First read `docs/studies/p9_point_details/briefs/00_shared_context.md` (the request, the gate's findings, the plan, the rules), then this brief.

## Goal

Build the men's rally-length data that pre-match statistics will be made from. Link it to today's Stage 0, and measure two things:
1. how much P9 raises each player's rally-length history in 2025–26. **This number decides whether the study continues;**
2. how reliable the candidate rally rates are with P9 and without it.

Do not build any pre-match feature for scoring yet, and never relate anything to the results of the matches being predicted.

## Inputs

* **P9:** `data/dump/points/infosys_atp_recent/`.
  * `points.parquet` (MatchBeats): `server`, `scorer`, `result`, `set`/`game`/`seq`, the older rally counts `tm1Rally`/`tm2Rally` with `rallyLengthMissing`, the newer recount `tm1Shot`/`tm2Shot`, the net flags.
  * `rally.parquet` (the rally-analysis files): `category` is the shot the point ended on ("Serve", "Return", "3rd shot" … "9+ odd shots"); `list`; `t1NetPoint`/`t2NetPoint`.
  * `matches.parquet`: ATP 4-character player codes `p1_id`/`p2_id`, names, `event_id`, `tournament_start`, `round_from_code`, `draw`, `level`, `family`, `series`.

  The files carry no match dates. The gate's profile, `data/studies/p9_point_details/field_profile.json`, documents the fields.
* **The earlier sources,** for history and for overlap checks: the [shot-level study](../../shot_level/README.md)'s common point tables, `data/studies/shot_level/stage1_points_*.parquet` (infosys = the Hugging Face handoff of ATP match-centre files 2018 to early 2025; sirgenkii = the same ATP files, Dec 2024–Apr 2025; tdi = TDI's capture, mostly June–Sept 2026; slamtracker, slam_pbp, slam_tracking, ausopen, mcp). They were built under one convention by `src/eda/shot_level/points.py` and `stats.py`. Read `docs/studies/shot_level/stage0.md` and `stage1.md` for what rally length counts and how the sources agree. Its links to the Stage 0 of 2 Oct are `data/studies/shot_level/stage0_source_matches.parquet` (`match_id`, orientation `a1`, `cnt_rally`, `cnt_net`, …).
* **Today's Stage 0:** `data/studies/predictability_diagnostic/stage0_matches.parquet`, and the match clock `data/studies/match_timing/timing.parquet`. Men's player ids are `atp:<number>` (Tennis My Life / Sackmann ids). Stage 0's id fixes live in `data/studies/input_data_audit/fixes/id_aliases.csv` (another session is adding a row today; read only).
* **Linking P9:** it carries ATP codes and no dates. The data map places P9 matches by ATP ids (`src/eda/data_map/measure.py`, `load_infosys_atp_recent`, and `build.py`). Find or build a crosswalk from ATP code to Stage 0 player id: Tennis My Life's player file, the data map's linker, or another table the repo already has. Then link each P9 match to its Stage 0 match (event, round and players). Report the link rate by level, draw and season, and list the failures. Never guess a link.

## Tasks, in this order

1. **Convention.**
   * Establish what `tm1Rally + tm2Rally` counts (each player's shots? the serve included?). Check it against the rally files' `category` on the same points.
   * Check it against overlapping earlier sources on the same matches: SirGenkii (the same ATP files) and TDI, and the Hugging Face Infosys copy where it overlaps.
   * Map it to the shot-level study's convention, with agreement rates.
   * Decide how to use the newer recount (`tm1Shot`/`tm2Shot`), for example only where the old count is missing, and say why.
2. **The point table.** One row per point with a known rally length, men's matches 2018–2026, every source, deduplicated by linked Stage 0 match (P9 preferred where sources overlap). Columns:
   * the Stage 0 match id; set, game and point order;
   * the server and the point's winner as Stage 0 player ids;
   * the rally length in the shot-level convention, and a band (justify the bands, consistent with the shot-level study's "quick points" and "long rallies", e.g. 1–2, 3–4, 5–8, 9+);
   * the net flags where the source has them;
   * the source.

   Store it as `data/studies/p9_point_details/build/rally_points.parquet`.
3. **The atoms.** One row per (Stage 0 match, player). Each player's:
   * serve points and return points with a known rally length, by band, and how many were won;
   * shots hit;
   * net points approached and won, with a coverage flag;
   * the match's date, round order, level, draw and surface from Stage 0.

   Store it as `build/atoms.parquet`. These are the raw material for features of later matches.
4. **Depth: the stopping rule's number.** Take every men's Stage 0 match from 2025-01-01 to 2026-10-18 at tour level (Slams included, main draws and qualifying) and at Challengers (main draws and qualifying). For each player, count the points with a known rally length in their matches of the 52 weeks before. Strictly earlier: earlier dates, and earlier rounds of the same event. Say which clock you use: Stage 0's `tournament_date` and `round_order`, or the match clock's `es`/`lf`.
   * Count with every source, and without P9.
   * Report, by level group (Slams; 250s to Finals; Challengers) and half-year: the median and quartiles with and without P9; the ratio; the share of matches where both players have at least 300 and at least 1,000 such points.
   * Put the headline in your final message: the median ratio over tour-level main draws plus Challenger main draws.
5. **Reliability** (do this after task 4). For candidate rates, compute split-half reliability across players: the share of serve points ending by shot 2, by shot 4, and at 9+; points won by band on serve and on return; mean rally length on serve and on return; net approach rate and net points won. Use 50 random splits of each player's matches inside 52-week windows ending in 2025 and in 2026, with P9 and without it. Compare with `data/studies/shot_level/stage1_reliability.csv`. This is description only.
6. **Timing.** The atoms follow each player's own matches, so they are safe by construction. Still, run a small probe on your 52-week aggregator, in the spirit of `src/eda/match_timing/probe.py`: scramble every point winner after a cut day, re-aggregate a sample, and confirm that nothing dated before the cut moves.

## Where you may write

* Code: `src/eda/p9_point_details/build_*.py`, each with a short docstring.
* Outputs: `data/studies/p9_point_details/build/`.
* Your memo: `docs/studies/p9_point_details/team/builder.md`.
* Tests, if you add them: `test/p9_point_details/`.

Nothing else.

## Your memo

It covers:
* what was built;
* the convention and its checks, with agreement rates;
* the link rates and failures;
* the depth table and the stopping-rule number;
* the reliability table;
* the probe;
* open problems;
* "Process notes": every variant tried, every failure and fix, every choice and its reason.

Label each claim observed, inferred or unknown, with the file behind it.

## Your final message

A short summary: the stopping-rule number first, then the link rate, the convention, the reliability headline, and the paths of everything you wrote.
