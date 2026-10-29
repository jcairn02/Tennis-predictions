# Data continuity: process log

Opened 29 Oct 2026, when the study's cold-storage copy (README § 4.2) was resumed. Earlier work has no log; anything here about it is reconstructed from the README and the files, not contemporaneous. · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code · Sessions: 34071ffb-ecad-4722-87a2-1d3fb691be73 · For a future reviewer · Report: [README.md](README.md)

## Part 1. The downloaded tennis data to the bucket (29 Oct 2026)

### 1. The request

* **The owner's words, verbatim** (29 Oct 2026):
  > "check all the data that is in the data/ folder related to objective "tennis data" not our model.
  > See what the data is currently in my google cloud.
  > The data thats been downloaded recently that isnt in my cloud, compress it and upload it to the cloud in the same folder my other tennis data was uploaded to (dont remove it from disk)"
* **How it was read:**
  * **"Tennis data, not our model":** `data/raw/` (every download as served, with its receipts) and `data/dump/` (the same downloads staged as tables). These are the data map's `raw` and `staged` stages. Left out: `data/studies/`, the map's `evidence` stage (study outputs, features, fits and the daily engine's caches, about 58 GB per model instance); also `data/backups/` and `data/betting_history/`.
  * **"My google cloud":** the Cloud Storage bucket `gs://tennis-predictions-archive/`. It is the only off-PC copy that `data/LARGE_FILES.md` and `data/studies/data_continuity/backups.jsonl` record. Google Drive was not checked: its connector is not authorised in this session, and no project document mentions it.
  * **"Isn't in my cloud":** `backup.py`'s rule. A file counts as held when a zip in the bucket has it at the same path, size and CRC-32. Anything new or changed since the 8 Oct snapshot (16:05 UTC) is a candidate.
  * **"The same folder":** `gs://tennis-predictions-archive/data/`, where `backup.py` puts each dated set. `data/2026-10-08/` holds 8 Oct's raw, dump and studies zips, and the new set goes beside it in `data/2026-10-29/`. Readings set aside:
    * writing into `data/2026-10-08/` itself, whose README, manifest and summary describe the 8 Oct set and whose names the new set's files would collide with;
    * `public_dump/`, which holds the September zips of two named downloads.
  * **"Don't remove it from disk":** nothing is deleted. The zips are written to `data/backups/2026-10-29/` and stay there.

### 2. Starting point

* **Code:** HEAD `9228b26`, equal to origin's main (checked with `git ls-remote`, 07:2x local). `backup.py` and its test were unmodified in the working tree.
* **Bucket (observed, `gcloud storage ls --long --recursive`, 29 Oct):**
  * `data/2026-10-08/`: the raw, dump and studies zips of 8 Oct (3.95, 2.74 and 15.41 GB), `manifest.csv.gz`, `summary.json` and `README.txt`.
  * `public_dump/`: `tennis_public_dump_raw_2026-09-22.zip` (0.47 GB), `tennis_atp_pipeline_handoff_raw_2026-09-25.zip` (16.67 GB) and `README.txt`.
  * 36.55 GiB in all.
* **Backups made so far:** one, 8 Oct (`backups.jsonl` has one line).
* **The scheduled downloads:** the daily task starts at 07:30 local and usually ends 08:15–08:40 (`data/raw/_scheduled/runs.jsonl`). The lower-level feed starts at 12:00.

### 3. Plan

1. Inventory `data/raw/` and `data/dump/` against the 8 Oct manifest. Read-only: path, size and modified time, no CRC. A scratch script, `inventory_raw_dump.py`, in the session's scratchpad.
2. Add a `--groups` option to `backup.py`, so that a set can hold raw and dump only. The default stays all three zips, as on 8 Oct. A set's README names its scope and lists, oldest first, the earlier zips a restore needs. As written, a second run would also have zipped every new study file, the daily engine's caches among them.
3. Run `test/data_continuity/test_backup.py`, with new tests of the scope and the README.
4. After the daily download finishes, run `backup.py plan --groups raw,dump`, then `pack`, `verify` and `upload`. They run detached in Git Bash, with a log. The download writes into `data/raw/`, so packing during it would catch half-written files.
5. Checks:
   * `verify` checks every zip three ways: CRC, the manifest, and Windows tar extracting it to a pipe;
   * `upload` checks each object's size, MD5 and storage class;
   * after the upload, the bucket's zips are read back by range request, as the next plan will read them, and every file zipped here must show as held.

### 4. Chronology

Local time (UTC−7).

| When | Step | Why | Output |
|---|---|---|---|
| 07:25 | Read `LARGE_FILES.md`, `backup.py`, the 8 Oct set's files and `backups.jsonl`; listed the bucket | find the cloud copy and how it was made | the bucket and backup facts in § 2 |
| 07:25 | Checked the scheduled tasks and the disk | timing and space | daily task due 07:30; 375.8 GB free on C: |
| ~07:35 | Launched the read-only inventory (scratchpad) | step 1 | pending |
| before 07:31 | The inventory finished (`inventory_raw_dump.txt` / `.csv` in the session's scratchpad) | step 1 | Observed:<br>• raw and dump: 1,104,481 files, 46.23 GB<br>• at the same path, size and modified time as in the 8 Oct manifest: 207,041 files, 26.39 GB<br>• new paths: 896,968 files, 18.91 GB<br>• another size: 377 files, 0.80 GB<br>• same size, modified since: 95 files, 0.13 GB<br>• backed-up files gone: none<br>The largest new folders: `point_sources/infosys_atp_recent` 7.05 GB, `tennisexplorer_lower/matches` 3.81 GB, `point_sources/tennislive` 2.03 GB, `point_sources/sofascore_editions` 0.89 GB plus its receipts (0.24 GB). The study's estimate (§ 4.2: 0.5–1 GB a month) predates the October work packages. |
| before 07:31 | Added `--groups` to `backup.py`: the scan keeps to the chosen folders; the README names the scope and lists the earlier zips oldest first; the raw zip's text no longer says "the September zips" alone. Two new tests | steps 2 and 3 | `pytest test/data_continuity/test_backup.py`: 5 passed |
| 07:31:40 | Listed the running processes | what writes into raw | Observed:<br>• the daily task, started 07:30:01 (its speeds job was running);<br>• a SofaScore by-edition download (`--gap itf_detail`, up to 30,000 requests), running since 28 Oct 16:00 and writing into `raw/point_sources/sofascore_editions/`;<br>• another session's `cleanup_inventory/delete_2026_10_29.py`, running since 07:21. It deletes work trees outside `data/`, bytecode in the frozen reference's code copy and nine P9 study tables, and lists `data/raw` and `data/dump` as kept trees. Neither process conflicts with the backup. |
| 07:33:01 | Read the task's state from Git Bash, and made a gcloud call with prompts disabled | the runner depends on both | both work |
| 07:33:41 | Launched `data/backups/2026-10-29/run_backup.sh` detached (`Start-Process` Git Bash `-l -c`, pid 15136). It waits for the daily task, then runs `plan --groups raw,dump`, `pack`, `verify` and `upload` with `--date 2026-10-29`, stopping at the first failure | step 4 | `run.log` beside it: "start" 07:33:43; "waiting: the daily download task is running" 07:33:45 |
