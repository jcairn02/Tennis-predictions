# The data alarm counts matches, not bytes, when Tennis My Life's files shrink

**The owner's decision, 28 October 2026**, on Claude's recommendation of 27 October. Verbatim:

> fix the alarm and fix mensik

The recommendation it answered:

> Fix the alarm so it counts matches instead of bytes; the download already records how many matches each revision
> removes. If it's left alone, it will go off every time Tennis My Life re-saves its files, and a real loss becomes
> easier to miss.

The Mensik half is [its own decision](2026-10-28-mensik-id-alias.md). **The design below is Claude's** (an agent's
choice, in the production-integrity plan's sense). The matches are counted in the project's own copies of the files,
not read from the download's change log. The copies also cover a version the download held back, which the change log
never records.

## Why

* **The weekly alarm** (`src/eda/data_continuity/canary.py`, the "data continuity" alarm on STATUS) compares Tennis My
  Life's file list with its previous run. It raised SHRANK when a file got smaller by more than its line endings could
  explain.
* **On 26 Oct it raised SHRANK on 34 files that had kept every match.**
  * Tennis My Life had re-saved them on 22-23 Oct with Unix line endings (one byte less a line) and corrected some
    cells.
  * The alarm counts the line endings in the project's copy. The daily download had already replaced that copy with
    the re-saved file, so it found none to allow for.
  * Each of the 34 holds the same number of rows before and after.

## Decision

* **A Tennis My Life file the list shows smaller than at the alarm's previous run** is judged by its matches when the
  project keeps both versions. The two versions are found by their sizes among the current copy, the replaced copies
  (`superseded/`) and the copies the download held back (`held/`).
  * Fewer matches: `SHRANK (k files hold fewer matches: 2024_challenger.csv 6063 -> 5936, ...)`.
  * The same number or more: no flag.
* **Only the earlier version kept** (the later one was never downloaded): its line endings are the allowance.
* **Neither version kept** (the seasons the project does not hold): as before, by size. The allowance is the line
  endings of the project's copy, if it holds one, else 2%.
* **Unchanged:** SHRANK on a shorter file list, REVISED and every other flag. The flag still starts with SHRANK, the
  word the acknowledgments and the health check read.

## Evidence

**Each recorded run, rebuilt with the new rule** (the copies on disk, 28 Oct):

| Run | Recorded | With the new rule |
|---|---|---|
| 26 Oct (against 19 Oct) | SHRANK: 34 files smaller; REVISED: 80 | REVISED: 80. 48 files had both versions kept, every one with all its matches. 22 files the project does not keep were within 2%. For `2015_wta.csv` the version listed was written at 14:38 UTC, after that day's download, and replaced before the next; the earlier copy's line endings explain the drop |
| 19 Oct (against 12 Oct) | REVISED: 3 | the same |
| 12 Oct (against 6 Oct) | SHRANK: 207 → 171 files; SHRANK: 3 files smaller | SHRANK: 207 → 171 files; **8 files hold fewer matches**; 1 file smaller (`1981_challenger.csv`, not kept) |

* **The first live run with the new rule** (28 Oct, 15:54 UTC, against 26 Oct):
  * 15 men's season files were smaller again (Tennis My Life kept re-saving). The project kept both versions of all
    15, and each kept all its matches, so no SHRANK was raised. The old rule would have raised it on all 15: the
    project's copies are Unix-ended now.
  * REVISED: 26 earlier-season files.
  * TERMS fired on both of Tennis My Life's licence statements: the site's MIT statement was replaced by
    non-commercial terms naming prediction models ([data continuity, 4.8](../studies/data_continuity/README.md)).
* **Missed by the byte rule:** in Tennis My Life's revision of 12 Oct, eight Challenger season files really lost
  matches, and the byte rule flagged only one of them.

  | Season | Matches before | Matches after |
  |---|---|---|
  | 2018 | 4,684 | 4,681 |
  | 2019 | 3,244 | 3,243 |
  | 2020 | 2,184 | 2,183 |
  | 2021 | 4,344 | 4,340 |
  | 2022 | 5,391 | 5,384 |
  | 2023 | 5,693 | 5,688 |
  | 2024 | 6,063 | 5,936 |
  | 2025 | 6,411 | 6,399 |

  The download held the 2022-25 files, and they were accepted after review on 14 Oct.
* **Tests:**
  * `test/data_continuity/test_data_continuity.py`: two new tests, the flags with match counts and finding the two
    versions among the copies (current, replaced, held back, qualifying subfolder);
  * the alarm's and the health check's test files: 49 of 49 pass.

## Not covered

* **Files the project does not keep** (most seasons before 2000) are still judged by size.
* **REVISED still fires on every correction of an earlier season.** Tennis My Life corrects old seasons most weeks, so
  it is informational.
* **A file the download holds back is not an alarm flag.** The download reports it itself. Another session's work of
  28 Oct (master pipeline process log, Part 10) adds a held-file status.
