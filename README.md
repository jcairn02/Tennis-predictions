# Tennis predictions

Research toward a tennis analytics and betting system, with data connected to the markets actually available to bet on. The current priority is historical tennis data and its coverage of Polymarket events.

**No implementation roadmap has been approved.** The inherited one-shot LLM output is an unapproved seed of ideas, including its architecture, timelines, source claims, model choices, venue preferences, and exclusions. It is preserved in the [historical research archive](docs/research/legacy-one-shot/INDEX.md). A future roadmap will be rebuilt separately.

## Organization

The organizing sequence is **data → data science process → predictions → betting venues and available markets → the bet itself**. Market identity, timestamps, and settlement rules also constrain what data is useful at the start. This is a domain map, not a scheduled implementation plan.

Start with the [documentation index](docs/00_overview.md), [pipeline boundaries](docs/pipeline.md), and [roadmap status](docs/roadmap.md). Current evidence belongs in [research](docs/research/README.md); bounded experiments belong in [studies](docs/studies/README.md).

The [tennis data and Polymarket coverage audit](docs/research/tennis-data-audit/README.md) is the current research deliverable, with a linked source register, market inventory, payload-quality checks and saved evidence. It does not approve a dataset, model or architecture. The [public data dump](docs/studies/public_data_dump/README.md) is the first acquisition run built on it: public sources from 2010 onward, staged by source under `data/dump/`, with a [proposed target structure](docs/studies/public_data_dump/structure-plan.md) for the cleaning and merge phase.

| Location | Purpose and current status |
|---|---|
| `data/`, `src/ingest/` | Source data, provenance, and experimental loaders |
| `src/eda/`, `docs/studies/`, `data/studies/` | Investigations, reports, reproducible evidence |
| `src/ratings/`, `src/features/`, `src/models/` | Inherited experiments or reserved homes; no approved model stack |
| `predictions/` | Reserved home for future prediction outputs |
| `config/` | Future explicit configuration; no approved venue configuration |
| `src/betting/`, `data/betting_history/` | Inherited betting-math experiment and reserved actual bet records |
| `test/` | Scaffold tests; passing tests do not approve the scaffold |
| `scripts/` | Notebooks, following the UFC convention |
| `docs/research/legacy-one-shot/` | Archived suggestions, raw research, configuration, and paper extracts |

The sibling [UFC project](../ufc-predictions/) is an organizational reference. Its production model choices and deployment rules are not automatically tennis decisions.

## Existing scaffold

The source code is retained for inspection and possible reuse. It does not establish production readiness, chronological correctness, data completeness, or a chosen architecture. Original benchmark claims remain in the archive and were not revalidated by the documentation reorganization.

The documented environment is the `tennis` Conda environment through `./python.sh`; see [working conventions](CLAUDE.md). Running code is separate from approving it.
