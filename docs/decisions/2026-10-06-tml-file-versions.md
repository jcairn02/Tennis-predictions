# Tennis My Life downloads keep every version and never let a damaged file replace a good one

**Delegated by the owner on 6 October 2026.** The question put to the owner was "Do you keep the new TML default?". The owner did not find it clear, and asked: "I want you and a highly intelligent opus 5.5 extra high agent to discuss this and arrive at a solution."

Decided the same day by Claude after one round of review with an independent Opus agent. Recorded on 6 October 2026.

## What the question was

Tennis My Life (TML) is the project's only source of new results and box scores since Sackmann's files stopped in late May 2026 ([match clock](2026-10-05-match-timing.md), "Going forward"). TML rewrites its published files in place. It appends matches, corrects old seasons (an audit on 6 September changed entry codes and a few box scores in eight seasons), re-exports files with new line endings, and rewrites its ongoing-tournament files several times a day. Until 6 October each download replaced the project's copy, so every earlier version was lost. The question was whether to keep them.

## Decision

1. **Keep every version the project downloads.** When a download brings different bytes, the replaced file is kept under `superseded/`, with its receipts. The kept copy is named by the first time those bytes were seen. This applies to the season files, the ongoing files, the manifest and the README. The receipts files are append-only and are never compacted: they are the record of when each version was first seen.
2. **A damaged file never becomes the current copy.**
   * **Season files are held** when:
     * the last record is cut short (a half-written file);
     * the file is not the size TML's manifest lists (TML was rewriting it);
     * a column is lost;
     * more than five rows, or more than half the rows, of the current copy are gone once corrections are paired with the rows they correct.
   * **Ongoing files are held** only when cut short or missing a column.
   * **A held file** is kept under `held/` with the reason. The current copy and the staged tables stay as they were, and the run exits with an error. After review, `--accept-held NAME@SHA12` lets that exact version through.
   * **Every accepted revision** of a season file logs its added, removed and corrected rows, and every changed column, in `_changes.jsonl`.
3. **Safe writes and one run at a time.** Downloads, kept copies and their metadata are written whole and then renamed, so an interrupted run leaves no half-written file. A lock stops a second TML run while one younger than an hour is going.
4. **The adapter looks one season ahead** (this year and next). TML publishes the next season's file in late December; its 2025 file starts with matches of 29 Dec 2024.
5. **Each Stage 0 build records the SHA-256 of every file it reads**, the staged file's own and its source file's. A kept version can then be tied to the builds that used it.

## Why

* Stage 0 has 4,863 matches from the week of 25 May on that only TML supplies. A correction there would otherwise reach Stage 0 with no record of the earlier value, and no earlier training set could be rebuilt.
* TML's manifest showed a file it was still writing: it listed 12,873 bytes for an ongoing file whose download held 13,077, ending part-way through a row. Before this decision, the only check on a TML match file was that its header named `tourney_id`.
* **Replay on real versions.** The gate accepts the project's 22 September copies → TML's 6 October versions:
  * `2024.csv` with its one corrected cell logged;
  * the 2026 files with only appended rows;
  * the ongoing files' turnover.

  It holds a header-only file and a half-written file. Replayed on TML's own pre-audit backup of 6 September, it accepts every season with its corrections logged; the audit removed no row. Evidence: [tml_revisions_files.csv](../../data/studies/data_continuity/tml_revisions_files.csv), [tml_audit_backup.csv](../../data/studies/data_continuity/tml_audit_backup.csv).
* **Cost.** A few megabytes per run; under a gigabyte a year at one run a day.

## Where it is implemented

* `src/ingest/public_dump/common.py`:
  * `download(keep_superseded=..., gate=...)`, with a held outcome recorded under `held/<name>`, so the latest receipt under the file's own name still describes the current copy;
  * `keep_replaced`, `keep_held` and `write_atomic`, plus `Receipts.sightings`.
  * Other adapters are unchanged unless they ask for these.
* `src/ingest/public_dump/tennis_my_life.py`: the gate, `--accept-held`, `--no-keep-superseded`, the lock, the end year and `_changes.jsonl`. `run_all.py` counts a held file as a failure.
* `src/eda/predictability_diagnostic/stage0_build.py`: `inputs.files` in `stage0_summary.json`.
* Tests: `test/public_data_dump/test_keep_superseded.py` and `test_tml_gate.py`.
* TML's pre-audit backup of 6 September (31 files) is kept in `data/raw/data_continuity/tennis_my_life/backup_ll_audit_20260906_044746/`.

## Not decided (the owner's)

* **How often to download TML.** Old versions exist only for the days the project downloads. The adapter has run once, on 22 September, so every ongoing-file version published since is gone.
* **A copy off this PC**, which must include the kept versions and the receipts. For now they are themselves the only copy.
* **Whether backtests must use the data as first published.** That arises once a forward test is approved. It needs first-seen times per row, built from the kept versions.
* **`run_all.py` still passes its own end year (2026) to every adapter.** Run through it, TML will skip `2027.csv` from January. The direct adapter command, the one the match-clock decision names, looks ahead.
