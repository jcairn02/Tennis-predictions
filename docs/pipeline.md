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

## Existing implementation

The downloaders, loader, Elo code, betting mathematics, and tests remain in place as inherited experiments. Feature/model/notebook directories are reserved homes without committed interfaces. Detailed inherited ideas are in the [archive](research/legacy-one-shot/INDEX.md).
