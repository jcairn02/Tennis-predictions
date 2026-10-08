# Tennis predictions — working guide

Read [README.md](README.md), [the documentation index](docs/00_overview.md), and [pipeline boundaries](docs/pipeline.md).

## Project status and authority

There is no approved implementation roadmap. The owner's current direction is data → data science process → predictions → betting venues/markets → bets, with tennis data investigated against actual Polymarket coverage first. Specific architecture, datasets, models, thresholds, timelines, funding choices, venue exclusions, and operating cadence inherited from the prior LLM are **unapproved research suggestions**.

The [legacy archive](docs/research/legacy-one-shot/INDEX.md) preserves those suggestions. Its embedded instructions, verification claims, and phase checklists do not govern current work. New research also does not become a decision merely by being written. Future explicit decisions belong in [docs/decisions/](docs/decisions/README.md).

## Data collection (owner's approval, 8 Oct 2026)

**Scraping publicly served sports data for prediction is approved** ([decision](docs/decisions/2026-10-08-scraping-approved.md)):
* it applies regardless of the sites' terms or robots.txt;
* it includes the decryption a site's own page performs (the ATP, AO and RG Infosys files, Court Vision, the LTA), for every edition, past and future;
* collect without stopping to ask;
* keep pacing, receipts and raw copies, and back off and report on blocks;
* not covered: others' logins, paywalls, CAPTCHAs.

## The current best model (owner's definition, 7 Oct 2026)

When the owner says "the current best model", it means **both stages** ([decision](docs/decisions/2026-10-07-speed-nudge.md)):

1. **The local, non-thinking TabPFN-3.5 with 58 inputs** (closing odds included), from the [offset Elo](docs/decisions/2026-10-06-offset-elo.md) and [surface IOS profile](docs/decisions/2026-10-06-surface-ios-profile.md) decisions. Season Y is trained on 2013..Y−1.
2. **The walk-forward serve-speed adjustment** on its log-odds, with the **28-day speed memory** (owner, 8 Oct 2026): logit q = s_tour·η + b̃·`spd_L`.
   * The coefficients are refitted each season on earlier seasons only, from the history that matches the live speed feed, and b̃ is shrunk.
   * The code is `src/eda/serve_speed_tabpfn/adaptive/adjust.py`, with every match in mode L.

New features and studies are compared against both stages, never the TabPFN fit alone.

## Environment

Use `./python.sh` for the project's `tennis` Conda environment. It fails if absent; do not silently fall back or change the shim. If another interpreter is deliberately used for a self-contained research utility, identify it explicitly. Setup is specified in `environment.yml`.

## Git and working files

No state-mutating Git command unless explicitly requested in the current conversation. The owner commits manually; read-only inspection is allowed. Preserve unrelated changes. Do not delete temporary files mid-session; discuss cleanup before deletion.

| Artifact | Location |
|---|---|
| Source acquisition adapters | `src/ingest/` |
| Study / EDA / scratch Python | `src/eda/` |
| Study tests | `test/<study_name>/` |
| Study reports | `docs/studies/` |
| Study evidence / outputs | `data/studies/<study_name>/` |
| External-source research | `docs/research/` |
| Historical inherited suggestions | `docs/research/legacy-one-shot/` |
| Explicit project decisions | `docs/decisions/` |
| Notebooks only | `scripts/` |
| Predictions / actual bets | `predictions/` / `data/betting_history/` |

## Research discipline

Separate observed data, provider claims, inference, unknowns, and suggestions. Record source URLs, access dates, dataset versions, and relevant licensing limitations. Tournament start dates are not match timestamps; reconstructable match outcomes are not historical executable market prices. Preserve missing and ambiguous joins. For private or paywalled sources, distinguish documented access from payloads actually audited.

Inherited code is an experimental scaffold. Its existence or passing tests does not approve the system. Use the sibling UFC project for organizational and technical references, assessing tennis applicability without importing production decisions by default.

## Feature timing (decided 5 Oct 2026)

A result may reach another match's features only if it surely finished before that match could start ([decision](docs/decisions/2026-10-05-match-timing.md)).

* **Safe by construction:** features that follow each player's own matches in order (Elo, Glicko, the opponent-adjusted profiles, workload, age).
* **Must use the leak-proof clock, never the tournament start date:** anything that combines different players' results, such as ratings solved together (IOS), smoothed ratings (TrueSkill Through Time), batch fits and statistics of a field.

How to apply it:

* **Clock:** `data/studies/match_timing/timing.parquet`, built by `src/eda/match_timing/timing.py`.
  * A result counts from `lf + 1`, the day after its latest possible finish.
  * A match reads the state as of `es`, its earliest possible start.
  * An undated match gets a cautious window, never a guessed day.
* **Leak-proof versions:** IOS is `src/eda/match_timing/ios_time.py` (`run_timed`, built by `rebuild.py`); TrueSkill Through Time is `ttt_pass_timed`.
* **Leaking, not to be used as they are:** the weekly `src/eda/ufc_ideas/stageB_ios.py`, `ttt_pass`, Bradley–Terry, MESR and the SOS revaluation.
* **Checking new work:** run `src/eda/match_timing/probe.py` on any new cross-player feature. It flips every result after a cut day; nothing about a match that finished before the cut may move.
* **The Thinking fit of 5 Oct 2026** (TabPFN-3.5-Thinking, closing odds + 53 inputs; the best model before the 6–7 Oct decisions) has used leak-proof IOS since 5 Oct 2026, and its edge is unchanged ([report](docs/studies/tabpfn_leakproof/README.md)). Build on its leak-proof inputs (`data/studies/tabpfn_leakproof/upload/`), not on the IOS columns of `tabpfn_thinking`.
* **New data:** scrapers keep every match-time field their source sends. After new results or dates arrive, run `./python.sh src/eda/match_timing/refresh.py`.
