# Data

Data is the current research priority. Measure coverage against actual markets, preserving unmatched events and ambiguous identities.

| Location | Purpose |
|---|---|
| `raw/` | Downloaded source records, gitignored; preserve provenance and retrieval time |
| `raw/public_dump/<source>/` | Byte-exact downloads of the public data dump with `_receipts.jsonl` per source (URL, time, hash, route) |
| `dump/<branch>/<source>/` | Tabular staging of the dump as string-typed Parquet, one file per source file, gitignored; branches `matches`, `players`, `rankings`, `points`, `odds` |
| `studies/<study_name>/` | Audit artifacts and measured data-quality results |
| `studies/public_data_dump/` | Tracked manifest, coverage tables and download log of the dump |
| `betting_history/` | Reserved actual bet and settlement records |

Files over 50 MB are not in git; [LARGE_FILES.md](LARGE_FILES.md) explains how to regenerate or re-download each one.

The public data dump is produced by `src/ingest/public_dump/` and described in [its report](../docs/studies/public_data_dump/README.md). Older downloader paths `raw/sackmann/` and `raw/tennis_data_couk/` are inherited experiments (June 2026 snapshots), not an approved source selection. Sackmann's `tourney_date` is tournament start, not actual match time. Winner-first rows, schedule changes, retirements, and source identities need explicit handling.

[Old data notes](../docs/research/legacy-one-shot/data/README.md), including odds-column and coverage claims, are archived. Use fresh source evidence and measured audits before relying on them.
