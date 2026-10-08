# BetOnline tennis lines: evidence

Counts only. This repository is public, and no price leaves the gitignored `data/raw/` and `data/dump/`.

| File | What | Made by |
|---|---|---|
| `oddstrader_coverage.csv` | Singles played (status complete or retired), and those with an opening line, a last line and both, by tour, year, book (BetOnline, SportsBetting.ag) and market (match winner, total games) | `src/eda/betonline_lines/oddstrader_coverage.py` |
| `oddstrader_checks.json` | The pull's receipts; opening and last lines against the listed start; overround and one-sided lines; close flags; SportsBetting.ag against BetOnline; tennis-data.co.uk main-tour matches 2024–2026 found on OddsTrader | the same script |
| `sharpness.json` | BetOnline's closing lines against Pinnacle's, 2024–2025: linking, log loss with paired ranges, checks, how far apart the chances are, and margins ([report](../../../docs/studies/betonline_lines/README.md)) | `src/eda/betonline_lines/sharpness.py` |
| `sharpness_matches.parquet` | One row per tennis-data row of 2024–2025 with both books' prices; gitignored (`*.parquet`), not published | the same script |

The data: `data/raw/oddstrader/` (339 responses with `_receipts.jsonl`) and `data/dump/odds/oddstrader/` (`events`, `lines`, `betonline_matches`), from `src/ingest/oddstrader.py`, pulled 7 October 2026 (UTC) under the [owner's decision](../../../docs/decisions/2026-10-06-oddstrader-betonline-lines.md). Write-up: [BetOnline tennis lines](../../../docs/research/betonline-lines/README.md).

Rerun, without new requests:

    ./python.sh -m src.ingest.oddstrader --stage-only
    ./python.sh src/eda/betonline_lines/oddstrader_coverage.py

The reach of The Odds API over the same years is computed by `src/eda/betonline_lines/odds_api_coverage.py`.
