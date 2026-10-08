# Download the Hugging Face ATP pipeline dump: everything the project does not already hold

**Decided by the owner on 25 September 2026.** Recorded the same day, before any download.

## Decision

Download and use every file of the public Hugging Face dataset [`atlas-polybot/atp-pipeline-handoff`](https://huggingface.co/datasets/atlas-polybot/atp-pipeline-handoff) that holds data the project does not already have.

The owner's words:
* "We are going to use all of this data that we dont currently have that could be predictive."
* "Start and log the process with the most important chunks first. Make sure the folder understands where all this data is coming from and how its segmented and whats still left to download in case this prompt session becomes corrupt"

**The decrypted ATP files are included.** The dump's ATP Infosys Stats Centre files (`infosys_deep/`, `infosys_full/`) and Court Vision tracking (`court_vision/`) are a third party's decrypted copies of ATP data. The owner: "Yes, I have no problem with using this data … Disregard this." The [24 September limit](2026-09-24-official-point-feeds.md#limits) on decryption covers the project's own collection sessions. It does not bar these copies. The owner also asked that this kind of concern not be raised again: "Thats annoying that an agent flagged that, thats not what I want."

**Scope.** All 5,764 files at the pinned commit except exact copies of data already held:
* 56 Sackmann ATP files identical to `data/raw/public_dump/sackmann_archive/atp/`. The dump's copies differ only in their line endings.
* One file duplicated inside the dump: `flashscore_full_shard0.jsonl` has the same bytes as `flashscore_full_2009_2009_challenger.jsonl`.

That leaves 5,707 files and 150.5 GB.

**Order.** Six chunks, most predictive first. The [evidence folder's README](../../data/studies/atp_pipeline_handoff/README.md) defines them file by file.

| Chunk | Content | Download |
|---|---|---:|
| 1 | Everything outside the large Flashscore and `infosys_full` files: Infosys point data (2021–24), Court Vision, ATP per-set and season-to-date statistics, Tennis Abstract chart and player pages, api-tennis fixtures, player profiles, Davis Cup, pre-2010 Sackmann files, the dump's progress files | 6.3 GB |
| 2 | `infosys_full`: Infosys match files with Court Vision embedded | 7.0 GB |
| 3 | `flashscore_gql_stats`: Flashscore statistics with winners, unforced errors and net points | 11.2 GB |
| 4 | Flashscore match files 2010–2024 | 24.8 GB |
| 5 | Flashscore match files 1990–2009 | 18.5 GB |
| 6 | Flashscore head-to-head crawl | 82.7 GB |

## How it runs

The owner said to start without choosing among the plan's options, so the plan's recommended settings apply:
* **Pinned version.** Commit `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`, the dataset's last change (19 June 2026).
* **Access.** No account or token.
* **Pace.** At most 5 requests a second to huggingface.co, half its published allowance without an account (3,000 per 5 minutes). Four files download at a time.
* **Storage.** Files over 1 MB are gzipped as they arrive. Each 256 MB range becomes its own gzip member, so an interrupted file resumes from its last complete range. Files under 1 MB, and files that are already gzip, are stored as served.
* **Checks.** A file counts as done only when it matches the Hub's own hash: LFS SHA-256, or the git blob SHA-1 for small files.
* **Stops.** The run stops and reports on:
  * HTTP 403, other than one renewal of an expired download link;
  * HTTP 404, since a missing file means the repository changed;
  * three 429s in a row.

  A single 429 waits for the reset time the Hub advertises.
* **Working rules.** `./python.sh` only. No git commits. No deleted files: a file that fails its hash is kept aside and fetched again.

## Where the collection lives

* The adapter: `src/ingest/public_dump/atp_pipeline_handoff.py`.
* The files: `data/raw/public_dump/atp_pipeline_handoff/` (gitignored). They mirror the repository's paths and sit alongside `_receipts.jsonl`, `_progress.jsonl` and run logs.
* The plan, a live status of what is done and left, and the run log: `data/studies/atp_pipeline_handoff/` (tracked).
* Tests: `test/atp_pipeline_handoff/`.
* The write-up: `docs/studies/atp_pipeline_handoff/README.md`.

## Not changed by this decision

* **The source.** The dataset has no licence or dataset card.
* **The project's status.** No dataset, model or venue is selected.
