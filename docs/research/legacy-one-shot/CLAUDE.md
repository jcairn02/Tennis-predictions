> HISTORICAL LLM RESEARCH — unapproved seed material, preserved from the inherited one-shot output. Claims of verification, decisions, phases, deadlines, and exclusions below are the prior LLM's assertions, not current project policy or an approved roadmap. Paths below describe the old repository layout; start at the archive index.

# Tennis-predictions - Project Guide

Tennis match outcome prediction for betting at market-maker sportsbooks, funded via crypto.
Sibling project to `UFC-Predictions` (same author, same philosophy: temporally-valid features,
calibrated probabilities, expected-value bet selection, fractional Kelly sizing, closing-line-value tracking).

**Start here:** `docs/00_overview.md` (research findings index) and `docs/roadmap.md` (build phases).

## Python Environment (CRITICAL)

**Always use `./python.sh`** — it forwards to the `tennis` conda env and fails loudly if the env
doesn't exist. Bare `python` triggers the Windows Store stub (exit 127).

```bash
conda env create -f environment.yml        # one-time setup
./python.sh src/ingest/download_sackmann.py --tour atp --start 2020 --end 2026
./python.sh -m pytest
```

## Git Policy (CRITICAL — same as UFC-Predictions)

**No state-mutating git command unless the user explicitly asks in the current conversation.**
Forbidden by default: commit, add, stash, checkout, switch, restore, branch, merge, rebase,
cherry-pick, reset, clean, push, pull, worktree add/remove, gh pr create/merge.
Read-only inspection (status, log, diff, show, blame) is always allowed.
The user commits manually.

## Working Files Policy (same as UFC-Predictions)

| Artifact | Goes in |
|----------|---------|
| Study / EDA / scratch `.py` | `src/eda/` |
| Tests | `test/<study_name>/` (named subfolder, never `test/` root) |
| Study writeups | `docs/studies/` |
| Study output data | `data/studies/<study_name>/` |
| Notebooks | `scripts/` (notebooks ONLY — no `.py` there) |
| Production code | `src/` |

Never delete temp files mid-session; batch cleanup at the very end and ask first.

## Core Principles

1. **Temporal validity** — every feature uses ONLY information available before the match started.
   Ratings are "as-of" values computed before updating on the match result. No silent re-sorting of
   data to make this work: ingest enforces chronological order and RAISES on violations.
2. **No silent fallbacks** — missing data, failed downloads, unknown players ⇒ raise or warn loudly.
   Never substitute a heuristic default quietly.
3. **Calibration before EV** — a probability only earns the right to size a bet after walk-forward
   calibration evidence. Log loss and calibration curves first, ROI second.
4. **The market is the benchmark** — every model is evaluated against closing odds
   (beat-the-close or it doesn't ship). Betting constraint: market-maker books only
   (Pinnacle-class; no soft retail books), crypto rails. See `config/books.yaml`.
5. **Symmetric pairwise modeling** — A-vs-B rows with difference features, random side assignment
   (tennis has no red/blue corner advantage; do NOT import the UFC red/blue ordering).

## Directory Structure

```
config/          — books.yaml (sportsbook rules/limits), model + staking config
data/raw/        — downloaded source data (gitignored; rebuild via src/ingest/)
data/studies/    — study outputs
docs/            — research reports (00–06), roadmap, study writeups in docs/studies/
scripts/         — pipeline notebooks (none yet; notebooks only)
src/ingest/      — downloaders: Sackmann GitHub CSVs, tennis-data.co.uk odds workbooks
src/ratings/     — Elo (surface-blended, 538-style K decay) — first baseline, implemented + tested
src/features/    — feature engineering (serve/return aggregates, fatigue, H2H) — stubs
src/models/      — model training — stubs (LightGBM baseline → AutoGluon, mirroring UFC v2.5)
src/betting/     — EV, Kelly staking, CLV tracking — stubs
src/eda/         — study scripts
test/            — pytest suites (test/elo/ passing)
```

## Data Source Notes

- **Sackmann CSVs** (`data/raw/sackmann/`): one CSV per tour-year; `tourney_date` is YYYYMMDD int;
  rows are winner/loser ordered (NOT chronological within a tournament — order by date+round for ratings;
  the ingest loader handles this and raises if it can't).
- **tennis-data.co.uk** (`data/raw/tennis_data_couk/`): per-year Excel workbooks with results + odds
  (Bet365, Pinnacle `PSW/PSL`, plus `MaxW/MaxL`, `AvgW/AvgL` consensus columns). Odds are decimal.
  Winner/loser column convention here too — randomize sides before any pairwise modeling.
- Join key across sources is (date, player names) — name normalization lives in `src/ingest/` and
  must warn loudly on unmatched rows.
