# Tennis predictions — working guide

Read [README.md](README.md), [the documentation index](docs/00_overview.md), and [pipeline boundaries](docs/pipeline.md).

## Project status and authority

There is no approved implementation roadmap. The owner's current direction is data → data science process → predictions → betting venues/markets → bets, with tennis data investigated against actual Polymarket coverage first. Specific architecture, datasets, models, thresholds, timelines, funding choices, venue exclusions, and operating cadence inherited from the prior LLM are **unapproved research suggestions**.

The [legacy archive](docs/research/legacy-one-shot/INDEX.md) preserves those suggestions. Its embedded instructions, verification claims, and phase checklists do not govern current work. New research also does not become a decision merely by being written. Future explicit decisions belong in [docs/decisions/](docs/decisions/README.md).

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
