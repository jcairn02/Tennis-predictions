# Pipeline boundaries

The domain sequence is **data → data science process → predictions → betting venues and available markets → the bet itself**. These boundaries organize research and future artifacts. They do not select technology, models, providers, operating frequency, or delivery dates.

| Domain | Responsibility | Evidence or output kept distinct |
|---|---|---|
| Data | Identify real markets and obtain matching sporting and market history | Source records, IDs, timestamps, provenance, update history, coverage, settlement text, prices/trades/books |
| Data science process | Understand data, define targets, explore features and evaluate models | Reproducible studies, causal availability assumptions, missingness, evaluation evidence |
| Predictions | Represent a forecast for a specified event and outcome | Event/outcome identity, forecast time, probability, model/data version, uncertainty |
| Venues and markets | Relate that forecast to a contract and available quote | Venue/market/token IDs, outcome mapping, rule version, quote time, fees, spread, available size |
| Bet | Record the actual economic action and result | Order/fill or ticket, size, paid price, costs, settlement, bankroll accounting |

Market coverage constrains the beginning of the pipeline: a historical tennis match is useful only if it is the same event and outcome as the contract under study. Outrights, match winners, handicaps, totals, and set contracts can require different labels and settlement handling.

## UFC analogy

The UFC repository separates experiment code (`src/eda/`), reports (`docs/studies/`), artifacts (`data/studies/`), predictions, and actual betting history. Tennis adopts that distinction as a filing convention. UFC live model recipes, feature choices, thresholds, and retired versions are references to assess, not tennis approvals.

## Daily predictions (since 11 Oct 2026)

**Run predictions only from `scripts/master_pipeline.ipynb`** ([how it works](studies/master_pipeline/README.md)). Each cell is one call into `src/pipeline/`; the bet-day cells run the daily engine `src/eda/daily_prediction/` ([report](studies/daily_prediction/README.md)). The working guide's section "Daily predictions: the master notebook" (`CLAUDE.md`) holds the map:

| Path | What it is |
|---|---|
| `scripts/master_pipeline.ipynb` | The front door: bet day, data update, rebuild and retrain |
| `src/pipeline/` | The notebook's layer: runs the project's commands and reads their outputs |
| `src/eda/daily_prediction/` | The daily engine (`dp.py`; the notebook calls its `run_day`) |
| `src/eda/prediction_pipeline/` | The engine's plan and the prototypes it imports; not run directly |
| `src/eda/prediction_run/` | The 8 Oct live path: its refresh, live rows and gate are the engine's parts; its full sandbox rebuild (`run.py --build`, about 2 hours) is the reference for proofs, not a way to predict |
| `docs/studies/daily_update_speed/` | A closed study (the speed scoping, the bet-time pricing measurements, the 2027 fix); no code to run |

## Existing implementation

The downloaders, loader, Elo code, betting mathematics, and tests remain in place as inherited experiments. Feature/model/notebook directories are reserved homes without committed interfaces, apart from the master notebook and its layer (above). Detailed inherited ideas are in the [archive](research/legacy-one-shot/INDEX.md).
