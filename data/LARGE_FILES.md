# Files over 50 MB: how to get them back

These files and folders are gitignored because they are over 50 MB, or hold files that are. GitHub warns above 50 MiB and rejects files above 100 MiB. A fresh clone does not have them.
* The rebuild and re-download results quoted below were tested on 23 September 2026, against the originals from 10 and 22 September 2026.
* Rows added or changed on 14 Oct 2026 take the way back from the code, the run logs and the study docs. Those rebuilds were not run.
* Sizes were measured on 14 Oct 2026.

**The cold-storage backup of 8 Oct 2026** is in `gs://tennis-predictions-archive/data/2026-10-08/`.
* It holds every file under `data/` that GitHub did not hold that day: 206,828 files, 25.26 GB.
* They are in three zips, `tennis_data_dump_2026-10-08.zip`, `tennis_data_raw_2026-10-08.zip` and `tennis_data_studies_2026-10-08.zip`. Beside them, `manifest.csv.gz` lists every file's SHA-256.
* Its `README.txt` gives the restore steps. That file and the manifest are also in `data/backups/2026-10-08/`.
* **Files made or changed after 8 Oct 2026 16:05 UTC are in no backup.**

| File | Size | What it is | Way back | Exact copy? |
|---|---:|---|---|---|
| `data/studies/tennis_data_audit/polymarket/markets.jsonl.gz` | 116.6 MB | Polymarket tennis contract inventory: the census of 10 Sep 2026, 411,502 contract rows | A backup, or an offline rebuild from a backup of its page cache. Otherwise a live re-run makes a new snapshot | Only from a backup |
| `data/dump/odds/polymarket/market_index.parquet` | 119.7 MB | Staged index of 524,656 Polymarket contracts (the census of 10 Sep 2026 plus the catalog extension to events listed for 7 Oct 2026) with an inferred tournament-type bucket | Offline rebuild, about half a minute; or the 8 Oct 2026 backup | Same rows; a later rebuild updates some flags. Byte-identical from the backup |
| `data/raw/public_dump/polymarket_prices/bodies/itf.jsonl.gz` | 91.5 MB | Raw minute price-history responses for 20,681 ITF moneylines (22 Sep 2026, topped up 5 Oct) | Re-download, about an hour together with the next file; or the 8 Oct 2026 backup | No by re-download; the responses matched in a spot check. Byte-identical from the backup |
| `data/raw/public_dump/polymarket_prices/bodies/challenger_125_inferred.jsonl.gz` | 54.4 MB | The same for 7,658 Challenger / WTA 125 moneylines | Same as the ITF file | Same as the ITF file |
| `data/raw/public_dump/match_charting_project/charting-m-points-2020s.csv` | 56.6 MB | Match Charting Project men's shot-by-shot points, 2020s | Re-download from a pinned commit | Yes |
| `data/raw/public_dump/atp_pipeline_handoff/` (a folder; dozens of its files are over 50 MB even gzipped) | 16.8 GB (150.5 GB uncompressed) | The Hugging Face dataset `atlas-polybot/atp-pipeline-handoff`: Infosys, Court Vision, Flashscore, ATP-site and Tennis Abstract files ([section 5](#5-the-hugging-face-atp-pipeline-dump)) | Restore the zip in cold storage, or re-download from a pinned commit (1–2 hours) | Yes |
| `data/raw/public_dump/polymarket_trades/` (a folder; eight bucket files over 50 MB) | 2.02 GB | Raw Data API trade responses for 40,174 tennis moneylines with matches to 5 Oct 2026, both parties of every fill, with receipts ([section 6](#6-polymarket-trade-fills)) | Re-download with the last top-up's cutoff, about an hour; or the 8 Oct 2026 backup | No by re-download; settled markets' fills should match. From the backup, as it was on 8 Oct |
| `data/dump/odds/polymarket/trades/` (a folder; seven files over 50 MB) | 923 MB | The same fills staged to Parquet, 38,097,959 rows | Offline rebuild from the raw folder, about 10 minutes; or the 8 Oct 2026 backup | Same rows |
| `data/dump/odds/oddstrader/books_lines.parquet` | 68.4 MB | OddsTrader's every-book pull of 9 Oct 2026 staged: 2,156,371 match-winner lines (every book's last line, Pinnacle's opening) for the main-tour matches of 2018–2026 ([odds-sources study](../docs/studies/odds_sources/README.md)) | Offline rebuild from the raw responses in `data/raw/oddstrader/books/` (590 MB, 491 files under 2 MB): `./python.sh -m src.ingest.oddstrader --stage-only`, about a minute; or re-download with `--books-eids` (491 requests, about 35 minutes) | Same rows from the raw files; a re-download may differ where OddsTrader has changed its records |
| `data/dump/points/tennislive/listed.parquet` | 71.6 MB | TennisLive.net's results listings: every match (singles and doubles, qualifying and main draw) of every ITF, Challenger, WTA 125, tour, Finals and Slam event the site lists from 2018 to yesterday, with scores, winners, page URLs, start times, and the observed start and finish times the site keeps for only about a month. 874,831 rows on 13 Oct 2026; a scheduled task (`src/ingest/scheduled.py`) rewrites it every day ([gap-downloads study](../docs/studies/gap_downloads/README.md)) | Offline rebuild from the raw pages and their receipts in `data/raw/point_sources/tennislive/`: `./python.sh -m src.ingest.point_sources.tennislive_events --stage-only --no-pages`, about 2 minutes. Otherwise re-download: `./python.sh -m src.ingest.point_sources.tennislive_events --pageless-days --skip-samples --no-pages --max-requests 25000`, about 12,300 requests, 7–8 hours | Same rows from the raw files. No by re-download: observed times older than about a month are gone. No backup holds it |
| `data/dump/points/wta/events/2024.parquet`, `2025.parquet`, `2026.parquet` | 50.4, 58.5 and 56.5 MB | The WTA API's umpire point logs, one row per record (each point, ace, fault, let, challenge and correction, with the server and a millisecond UTC time) for every WTA 1000, 500, 250, 125 and Finals match: 1,133,702, 1,315,287 and 1,273,535 rows. 2026 runs to 13 Oct and is rewritten every week ([official point feeds](../docs/studies/official_point_feeds/README.md)) | Offline rebuild from the raw documents and their receipts in `data/raw/point_sources/wta/` (0.60 GB on 14 Oct 2026): `./python.sh -m src.ingest.point_sources.wta --stage-only --years 2024-2026`, a few minutes. Otherwise re-download the logs: `./python.sh -m src.ingest.point_sources.wta --batch B1 --years 2024-2026 --max-requests 20000`, about 18,300 requests and 13 hours; it stages at the end | Same rows from the raw files. The 8 Oct 2026 backup holds 2024 and 2025 byte for byte, and 2026 as it was on 3 Oct. A re-download is untested |
| `data/raw/gap_sources/bwandowando/matches.csv` | 278.5 MB | Kaggle `bwandowando/womens-tennis-association-matches-1975-present`, version 29 (24 Sep 2026, Apache 2.0): the WTA website's women's match records at every level since 1975, ITF and qualifying included, each match once per player: 1,409,422 rows, 862,445 matches, to the editions of 7 Sep 2026. The lower-level feed reads it every week | Re-download, under a minute, no account: `./python.sh src/eda/gap_sources/wta_site_kaggle.py --fetch-only`; or the 8 Oct 2026 backup | Yes while version 29 is Kaggle's current one (it was on 11 Oct): check the SHA-256 in `_receipts.jsonl`. A newer version would come down in its place, and the feed would read it as if it were version 29 |
| `data/raw/gap_sources/marcosjn2/atp-matches.jsonl`, `wta-matches.jsonl` | 145.0 and 118.5 MB | Kaggle `marcosjn2/tennis-point-by-point-match-dataset-20152025`, version 2 (29 Aug 2025, MIT): a SofaScore scrape of 48,479 ATP and WTA tour-level matches (25,185 and 23,294), 20 Jun 2015 to 28 Jun 2025, with every point's winner in order | Re-download, under a minute, no account: `./python.sh src/eda/gap_sources/fetch_marcosjn2.py`; or the 8 Oct 2026 backup | Yes while version 2 is Kaggle's current one: check the SHA-256 in `_receipts.jsonl` |
| `data/raw/point_sources/sofascore_editions/_receipts.jsonl` | 57.9 MB, growing | The request log of the SofaScore by-edition downloads (since 30 Sep 2026): one line per request with URL, final URL, file, retrieval time, HTTP status, bytes and SHA-256. Its 404 answers and errors are recorded nowhere else. The adapter needs it: without it every request is made again, and `--stage-only` stages nothing | None by rebuilding. The 8 Oct 2026 backup holds its first 3,860,739 bytes (to 30 Sep) | Only from a backup |
| `data/raw/point_sources/wta/_receipts.jsonl` | 108.5 MB | The same log for the WTA API since 24 Sep 2026 (the batches, the 2026 top-ups, the player crawl, the weekly jobs and bet-day fills). Its 404 answers (7,442 match documents) mark documents absent | None by rebuilding, as above. The 8 Oct 2026 backup holds its first 102,594,342 bytes (to 3 Oct) | Only from a backup |
| `data/studies/predictability_diagnostic/stage0_match_players.parquet` | 62.4 MB | Predictability diagnostic, Stage 0: two rows per singles match, 2010 to September 2026 (players, box scores and rates) | Offline rebuild from the staged Sackmann and Tennis My Life files with `./python.sh src/eda/predictability_diagnostic/stage0_build.py`, about a minute | Same rows |
| `data/studies/predictability_diagnostic/stage1_baselines.parquet` | 74.6 MB | Predictability diagnostic, Stage 1: one row per singles match, every baseline's pre-match probability and each player's pre-match Elo ratings | Offline rebuild after Stage 0: `./python.sh src/eda/predictability_diagnostic/stage1_odds.py`, then `stage1_baselines.py`, about 5½ minutes | Same rows |
| `data/studies/predictability_diagnostic/stage4_features.parquet` | 197.0 MB | Predictability diagnostic, Stage 4: one row per evaluation-level match of 2010–2026 (completed or retired), every candidate's features (165 columns) beside the result and surface Elo's and the market's probabilities | Offline rebuild after Stages 0–3: `./python.sh src/eda/predictability_diagnostic/stage4_features.py`, about 9 minutes | Same rows; a rebuild on 1 Oct 2026 gave identical values |
| `data/studies/ufc_ideas/stageB_adj.parquet`, `stageB_adj_features.parquet`, `stageB_ios.parquet`, `stageB_split_features.parquet`, `stageB_features.parquet` | 84.3, 129.4, 95.6, 54.2 and 232.0 MB | UFC-ideas study, Stage B: the per-match adjperf/adjdef z per statistic; the adjperf/adjdef features per pool match; each player's pre-match IOS offence and defence per statistic for every match; the opponent-strength split features; the scored frame (the pool, the earlier study's re-scored columns, every Stage B feature) | Offline rebuild after the predictability diagnostic's Stages 0–4: `./python.sh src/eda/ufc_ideas/stageB_adjperf.py`, `stageB_ios.py`, `stageB_split.py`, `stageB_rundown.py` (about 23, 16, 6 and 9 minutes) | Same rows (deterministic; the frozen constants are in `stageB_summary.json`) |
| `data/studies/ufc_ideas/stageD_profile_features.parquet` | 110.5 MB | UFC-ideas study, Stage D: the pool with the individual-statistic adjperf / adjdef / IOS columns of Stage B and the seven matchup products, the inputs of the profile models | Offline rebuild after Stage B: `./python.sh src/eda/ufc_ideas/stageD_profile.py` (about 4 minutes) | Same rows |
| `data/studies/shot_level/stage2_features.parquet` | 103.5 MB | Shot-level study, Stage 2: the pool with the shot-level features alone | Offline rebuild after Stage 0 and the predictability diagnostic's Stages 0–4 and the UFC-ideas Stage D: `./python.sh src/eda/shot_level/stage1_points.py`, `stage1_stats.py`, `stage2_features.py` (about 1½, ½ and 6 minutes) | Same rows (deterministic) |
| `data/studies/shot_level/stage3_sides.parquet` | 193.2 MB | Shot-level study, Stage 3: per pool match, each player's own Stage 2 feature values (A and B), box-score serve and return form in the same memories, the serve-point counts and the ratings' serve forecasts | Offline rebuild after Stage 2 and the predictability diagnostic's Stage 3 ratings: `./python.sh src/eda/shot_level/stage3_sides.py` (a few minutes) | Same rows (deterministic) |
| `data/studies/rating_systems/stageA_ratings.parquet`, `stageB_features.parquet` | 132.1 and 99.3 MB | Rating-systems study: one row per singles match (872,704) with every system's pre-match probability and the main systems' ratings; the scored frame (the Stage 4 pool, the new ratings, the earlier leaders) | Offline rebuild after the predictability diagnostic's Stages 0–4 and the UFC-ideas Stage B: `./python.sh src/eda/rating_systems/stageA_ratings.py`, then `stageA_ttt_hold.py` and `stageB_compare.py` (the grids about an hour on 5 workers, `--reuse-grid` reads back `stageA_tuning.csv`; the rest about half an hour) | Same rows (deterministic; the frozen constants are in `stageA_summary.json`) |
| `data/studies/data_continuity/rebuilds/<stamp>/replaced/` (one folder per coordinated Stage 0 rebuild; each holds copies of files over 50 MB) | 383.0 MB (`2026-10-07T0005Z`), 383.8 MB (`2026-10-08T1853Z`) and 386.8 MB (`2026-10-14T0412Z`): 1.15 GB in all | What each coordinated Stage 0 rebuild replaced: 72 files under the same relative paths, with a SHA-256 manifest (Stage 0's tables and evidence, Stage 1's odds, and the match-timing links, timeline, feature tables and TrueSkill table). In order: the tables of 30 Sep (replaced 6 Oct for the Slam overrides), of 7 Oct (replaced 8 Oct for the corrections), and of 8 Oct, the frozen reference's (replaced 13 Oct for the Roland Garros repair) | None by rebuilding: Stage 0's builder or its inputs changed after each one (2, 8 and 13 Oct). Copy them back from here. The first two sets are also in the 8 Oct cold-storage zip; extract it outside the repository, because the second set's files sit at their live paths in it. `./python.sh src/eda/data_continuity/rebuild_stage0.py --restore <stamp>` puts a set back into the live tables, which rewrites them, so coordinate with other sessions first | Only from these copies or a backup. All 72 files of the first two sets are in the 8 Oct zip (matched by SHA-256). Of the third set, 52 files equal the frozen reference's copies; the other 20 (171.7 MB: the timeline, the IOS and leak-proof features, and two link sets of 13 Oct) exist only here |
| `data/studies/point_sequence/sequences.parquet` | 94.0 MB | Point-sequence study: the unified point-by-point table, one row per point (19.17 million) for 130,751 Stage 0 matches from 13 sources, with the `usable` flag | Offline rebuild from the staged point sources and Stage 0: `./python.sh src/eda/point_sequence/build.py` (about 2 minutes; `--refresh all` re-reads every source) | Same rows (deterministic) |
| `data/studies/level_layer_adoption/stage0/C0_men26/stage0_match_players.parquet` | 60 MB | The men's 2026 Challenger candidate's Stage 0 player rows (the frozen Stage 0's plus 1,735 matches'), 10 Oct 2026 ([decision](../docs/decisions/2026-10-10-men-2026-challenger-data.md)) | Offline rebuild from role F's C0_now: `./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_men26 --derive-from C0_now --keep-tours atp --keep-levels CH,CHQ --keep-years 2026 --out data/studies/level_layer_adoption/stage0/C0_men26 --status-log data/studies/level_layer_adoption/stage0/status.log`, then `--checks` and `--ready` with the same `--out` (a few minutes) | Same rows |
| `data/studies/match_timing/leakproof_features.parquet` | 97.7 MB | Match-timing study: the Stage 4 pool (255,123 matches) with the 46 sporting inputs rebuilt on the leak-proof timeline (per-player inputs and daily-solved IOS) | Offline rebuild after the predictability diagnostic's Stages 0–4, the feature-alpha repair and the match-timing links: `./python.sh src/eda/match_timing/timing.py`, then `rebuild.py` (about 1 and 15 minutes; after a timeline change only `rebuild.py --part ios` and `--part merge` need rerunning) | Same rows (deterministic) |
| `data/studies/feature_interactions/round1/_panel_aug.parquet` | 112.5 MB | Feature-interactions study, round 1: the augmented 2014–2024 player panel of the feasibility audit (history quantities, venue, shot-level sides, the current best's forecast), read by the round-1 audit and round-2 checks | `./python.sh src/eda/feature_interactions/round1/feasibility/augment.py` writes it again, but not the same values: its history quantities have changed since 6 Oct (see the next row) | No |
| `data/studies/feature_interactions/round1/_history_feats_2010_2024.parquet` | 74.4 MB | Feature-interactions study, round 1: per-player history quantities of 2010–2024, the values the feasibility audit saw | None. No script writes or reads it. A rebuild with today's code on 8 Oct 2026 (`history_feats.build`) differs in 35 of its 37 columns, because the history table changed after 6 Oct | Only from a backup |
| `data/studies/feature_universe/store.parquet` | 318.1 MB | Feature-universe store: 63,737 model-frame matches × 776 candidate features: the 58 inputs, alternatives, per-player pairs, other rating systems, opponent-adjusted profiles, serve speed, market-internal, interaction and module columns, levels, known-null placebos and context. Described column by column in the tracked `store_registry.csv`; the selection pool is `menu.csv` | Offline rebuild after the feature-interactions study's inputs and the rating-systems, UFC-ideas and shot-level tables: `./python.sh src/eda/feature_universe/perplayer_2026.py`, then `build_store.py` (about 1 and 8 minutes) | Same rows (deterministic) |
| `data/studies/ios_product_centring/centred_products.parquet` | 73.8 MB | IOS product-centring study: per Stage 4 pool match (255,123) and model statistic, the matchup product as built and centred, the reference level used and the two rating differences | Offline rebuild from the surface-IOS study's stored runs: `./python.sh src/eda/ios_product_centring/reference.py` (about 11 minutes on 14 workers), then `products.py` (about 10 seconds) | Same rows (deterministic; `reference.py` checks that its re-solve reproduces the stored runs exactly) |
| `data/studies/current_best_model/reference_2026-10-08/frozen/` (a read-only folder; four files over 50 MB: `env/tabpfn-v3.5-20260909.safetensors`, `tables/data/studies/predictability_diagnostic/stage0_match_players.parquet`, and `tables_later/data/studies/match_timing/ios_features.parquet` and `leakproof_features.parquet`) | 1.41 GB, 1,583 files; the four large files are 876.0, 62.3, 50.1 and 97.4 MB | The frozen reference of the current best model, 8 Oct 2026 ([README](studies/current_best_model/reference_2026-10-08/README.md)): the instance, the tables it was built on, the TabPFN weights its fits used, the code and the previous model, each file hashed in `files.csv.gz`. Its Stage 0 and timeline are read by the history check (the template-build gate and every bet day), the lower-level feed's builder and the level-evidence code | None by rebuilding: `reference.py --freeze` runs only once, and only while the live tables are the 8 Oct rebuild's (they were replaced on 13 Oct). **Not in cold storage: the only backup was taken before it.** Other copies exist for some files: Stage 0's players file is in `data_continuity/rebuilds/2026-10-14T0412Z/replaced/`; the weights are in `%APPDATA%\tabpfn\` and on Hugging Face (`./python_tabpfn_local.sh src/eda/tabpfn_local/verify.py` downloads them after a licence check). The two `tables_later` files exist nowhere else. After any restore, run `./python.sh src/eda/current_best_model/reference.py --verify` | Only from this copy, or from a backup once one is made; `--verify` re-hashes all 1,581 files against `files.csv.gz` |
| `data/studies/daily_prediction/state/<instance>/tabpfn/season2026/seed<0–15>/executor_state.joblib` (16 per instance; the `state/` folder has its own `.gitignore`) | 3,617.5 MB each; 57.9 GB per instance, for two instances (`template_2026-10-10`, `template_2026-10-13`) | The daily engine's TabPFN training caches: for each seed, the 2026 TabPFN-3.5 fit with the instance frame's 62,869 training rows already processed. A bet day loads one (about 2 seconds) and predicts (about 3) instead of refitting. Each new instance adds about 58 GB, and an old instance's caches stay until deleted | Rebuilt by the engine itself: the next bet day's or replay's fit step builds any seed whose cache is missing, or whose key has changed (training rows, seed, settings, library versions, weights, graphics card). About 45 seconds a seed, 12 minutes for 16 | Same forecasts, bit for bit (tested); the file bytes were not compared |
| `data/studies/daily_prediction/state/<instance>/<day>/forms/z.parquet` (one per checkpoint folder; days `2026-06-22` and `2026-09-21` for each instance) | 84.8–86.7 MB (a checkpoint folder is 186–194 MB) | The daily engine's checkpoints. Each holds every input family's state before the day (the Elo passes, Stage 3, the 14 IOS solves, and in `z.parquet` the z of every earlier box-score row), with the instance's constants files. Live runs resume from the newest one at least a week before their matches; the replay check uses 2026-06-22 | Not rebuilt by itself: without one, a run stops at its work-tree step. Make one in the master notebook with `tp.make_checkpoint("<day>", tree="<build tree>")`, or with `DP_INSTANCE=<instance> DP_BASE_TREE=<build tree> ./python.sh src/eda/daily_prediction/dp.py checkpoint --tree <build tree> --day <day>` (10–12 minutes each; `template_2026-10-13`'s build tree is `C:/Users/zerom/tnr_gaps`). A live run that had to recompute parts leaves a new one by itself | Not needed: a run checks each part against today's tables and recomputes any that changed. Made on the same tree with the same code, it should come out the same (untested) |
| `data/studies/daily_prediction/runs/live_<stamp>/stage0/stage0_match_players.parquet` (the runs of 11 Oct 11:01, 13 Oct 16:39 and 13 Oct 16:53) and `data/studies/prediction_run/live_2026-10-09/stage0/stage0_match_players.parquet` | 62.3–62.4 MB each (each `stage0/` folder 89.4 MB) | A live run's own Stage 0, built at its refresh step from that hour's Tennis My Life download into the run's folder, never into the shared tables. The run used it to list missing box scores and to give the day's players their Stage 0 ids. Afterwards only the bet sheet reads this folder, and only its `stage0_matches.parquet` | None: it records the data as it was at run time. `./python.sh src/eda/predictability_diagnostic/stage0_build.py --out-dir <folder>` builds today's instead (about 1½ minutes) | No: Tennis My Life rewrites its files (it keeps the replaced ones under `superseded/`), and Stage 0's builder has changed since |
| `data/studies/master_pipeline/data_check/stage0/stage0_match_players.parquet` | 62.4 MB (folder 89.5 MB) | The master notebook's data-check cell (A3b) cache: Stage 0 built on the downloads on disk by the run's own builder, with a `key.json` of its inputs and code | Rebuilt by itself: the next `tp.data_check(MATCHUPS)` builds it when it is missing or its key no longer matches, about 100 seconds | Same rows from the same downloads and code |
| `data/studies/box_score_gate_review/replay/_stage0_after_tables/stage0_match_players.parquet` | 64.7 MB (93.5 MB with `stage0_matches.parquet`) | Box-score gate review: the replay work tree's Stage 0 after the tables step (15 Jul 2026 replayed on the frozen Tennis My Life dump, with the lower-level feed merged). It is put back before each scenario removes box scores | None needed: only the study's `run` and `finish` steps read it, and the study's readings were written on 14 Oct. `./python.sh src/eda/box_score_gate_review/replay_gaps.py setup` makes a new one in a few minutes (it refuses while `replay/base/` exists) | No: a new one would merge the feed snapshot and timeline current at that time, and this one needed its timeline trimmed |
| `data/studies/data_gaps_2026/feed/candidates/` (`F20261013b/`, `F20261013c/` and `F20261013c_gaps/` each hold a `stage0_match_players.parquet` over 50 MB) | 629.8 MB in all; the three files are 75.3, 75.3 and 64.7 MB | The lower-level feed's first candidate Stage 0s, 13 Oct 2026. F20261013b was abandoned when a check failed. F20261013c is every source checked against the frozen reference, with its player matching checked by hand (`identity_verdicts.csv`). F20261013c_gaps is derived from it with only the levels the history lost, and was packaged as `lower_level_feed/20261013c`, the current feed in `accepted.json`. Builds and bet days merge that snapshot (`current_best_model/accepted_additions/lower_level_feed/20261013c/`, 5.4 MB), not these folders. Later weekly candidates are built in `C:/Users/zerom/tnr_feed/candidates/`. Since 14 Oct only the tables are ignored here; the small records, the hand check among them, are not | None needed. `./python.sh src/eda/data_gaps_2026/feed.py --run --hand --label F20261013c --candidates-dir data/studies/data_gaps_2026/feed/candidates` rebuilds from today's downloads (about 25 minutes), with the hand check's `identity_verdicts.csv` from these folders | No: the downloads have changed. On the same downloads the builder gives the same rows (b's and c's player tables are byte-identical) |
| `data/studies/lower_level_evidence/system/relationship/targets_dev_key.parquet` | 79.0 MB | Level-evidence study, role B: the per-target audit file, one row per main-tour player-match and statistic of 2013–2024 (2.04 million rows, 19 statistics), with each formulation's log-likelihood gain over F0. No code reads it | Offline rebuild on the frozen reference: `./python.sh src/eda/lower_level_evidence/relationship.py --steps dev --work <scratch>`, then `--steps tables --work <scratch>` (about 25 and 1½ minutes) | Not exactly: the stored file predates a fit fix (now two starting points). On real data, 89 of 90 sampled fits came out identical and the 90th differed by 1.1e-6 |
| `data/studies/lower_level_evidence/system/stage0/C0_now/stage0_match_players.parquet`, `C0_pre/stage0_match_players.parquet` | 75.4 and 71.3 MB (folders 202.2 and 189.9 MB) | Level-evidence study, role F, 9 Oct 2026: candidate Stage 0s. C0_now is the frozen reference plus every lower-level match the sources then held (1,171,445 matches, 298,008 new); C0_pre is the same with only the additions dated to 29 Dec 2024. The study's NEW arms are built on them, and the C0_men26 row above is derived from C0_now | C0_now: `./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now`, then `--checks`, a hand check of the identity samples, then `--ready` (about 35 and 25 minutes plus the hand check); this builds today's version, not this one. C0_pre is derived from C0_now: `--label C0_pre --derive-from C0_now --until 2024-12-29`, then `--checks` and `--ready` | C0_now: no (its sources and the builder changed on 13 Oct). C0_pre: same rows when derived from this C0_now |
| `data/studies/event_levels/frame.parquet` | 71.9 MB | Event-levels study: the model's 58 inputs for 177,806 matches of 2013–2024 (its own main-tour matches plus Challenger and qualifying matches), on the 30 Sep snapshot the model frame was built on | Offline rebuild: `./python.sh src/eda/event_levels/frame.py` (run time not recorded). It reads the 30 Sep Stage 0 from `data_continuity/rebuilds/2026-10-07T0005Z/replaced/` | Same rows: all eight of its sources still match the hashes in `frame_manifest.json` (checked 14 Oct), and it refuses to write unless the model's 55,144 rows equal the model frame |
| `data/studies/match_timing/ios_features.parquet` | 50.2 MB | Match-timing study: the IOS part of the leak-proof inputs (offence and defence ratings solved across all players together), one row per Stage 4 pool match (256,030), merged into `leakproof_features.parquet`. Rewritten by the coordinated rebuild of 13 Oct | Offline rebuild: `./python.sh src/eda/match_timing/rebuild.py --part ios` (4 minutes on 13 Oct; up to 10), then `--part merge` | Same rows (deterministic) while Stage 0, the timeline and the IOS constants stay as they are |
| `data/studies/surface_elo_pieces/pieces.parquet` | 86.9 MB | Elo-pieces study: one row per Stage 0 match (872,704) with each player's Elo parts (Stage 1's pass, the anchored and offset variants, the surface-blind control) and surface-switch quantities. Built 6 Oct on the 30 Sep Stage 0 | `./python.sh src/eda/surface_elo_pieces/pieces.py` (about 7 minutes) builds it on today's Stage 0 | No: today's Stage 0 differs (873,636 matches). The event-levels frame pins this copy's SHA-256 |
| `data/studies/surface_ios/surface_features.parquet` | 293.5 MB | Surface-IOS study: one row per Stage 4 pool match (255,123) with each side's IOS offence and defence per statistic, current and surface model. Built 6 Oct on the 30 Sep Stage 0 | `./python.sh src/eda/surface_ios/build_features.py` (about 30 minutes on 14 workers) builds it on today's tables | No: today's Stage 0 and timeline differ |
| `data/studies/surface_rating_race/ttt_offset.parquet` | 63.3 MB | Surface-rating-race study: the surface-offset TrueSkill Through Time pass over the whole history, one row per Stage 0 match (872,704). Built 6 Oct on the 30 Sep Stage 0 | `./python.sh src/eda/surface_rating_race/features.py` (about 22 minutes, the two tours side by side) | No: the study records that a rerun after the 6 Oct rebuild reads different inputs |
| `data/studies/tabpfn_thinking/frame.parquet` | 62.8 MB | TabPFN-Thinking study, 2 Oct: every main-tour pool match of 2010–2026 (82,874) with its result, Elo's and the market's probabilities and every input. The paid Thinking fit's upload was cut from it | `./python.sh src/eda/tabpfn_thinking/build_frame.py --indoor-men-only` (about a minute) builds it on today's Stage 0. It also rewrites `upload/` and the tracked `manifest.json` | No: it was built on the 30 Sep Stage 0 |
| `data/studies/unpriced_leads/candidates/luck/values.parquet` | 86.1 MB | Unpriced-leads study, the luck builder: per model-frame match (67,226), each player's scoring-luck statistics. Three of them are registered members of lead group G1 | `./python.sh src/eda/unpriced_leads/build_luck.py` (8–15 minutes; deterministic) builds it on today's Stage 0 | No, and only this copy will do: the frozen registry pins its SHA-256 (`092d423c…`) and the registered looks refuse any other file. It was built on the Stage 0 that the 13 Oct 21:12 rebuild replaced |

**Deleted on 11 Oct 2026, so no longer in the table** ([cleanup inventory](../docs/studies/cleanup_inventory/README.md)). These can be rebuilt offline if ever needed:
* The sharp-money study's four position tables (`wallet_markets`, `scored_positions`, `prematch_positions`, `prematch_positions_buffer30`): `build_positions.py`, `classify.py` and `prematch.py`, about 10 minutes (section 6).
* The shot-level scored frame, `stage2_frame.parquet`: `./python.sh src/eda/shot_level/stage2_rundown.py`, about 4 minutes.
* The line-sharpening study's `prices.parquet` and `takers.parquet`: `./python.sh src/eda/line_sharpening/build.py`, about 15 minutes.
* The point-sequence study's `trait_player_matches_variants.parquet`: `./python.sh src/eda/point_sequence/trait_build.py` (fixed seeds).

A rebuild reads today's tables, so the two built on Stage 0 (shot level, point sequence) may differ from the deleted copies. The match-timing study's old `undated_matches.csv` cannot be rebuilt: no script writes it. `timing.py` writes the current list, `undated_matches.csv.gz`.

Sizes are decimal megabytes. `data/dump/points/wta/events/2024.parquet` is 48.1 MiB, under GitHub's warning threshold, but it is over 50 MB, so it is listed.

## Before you start

* Create the environment with `conda env create -f environment.yml` and run the commands below from the repository root in Git Bash.
* `./python.sh` calls the `tennis` environment at the owner's install path. On another machine, activate `tennis` and use `python` in place of `./python.sh`.
* The Polymarket files depend on each other, so restore them in this order. The Match Charting file is independent.

```
polymarket_census.py   -> markets.jsonl.gz, events.jsonl        snapshot of 10 Sep 2026
polymarket_catalog.py  -> catalog extension (optional)          events created after the census
polymarket_prices.py   -> market_index.parquet                  offline, from the two above
                       -> bodies/itf.jsonl.gz,                  live download
                          bodies/challenger_125_inferred.jsonl.gz
match_charting.py      -> charting-m-points-2020s.csv           independent
```

## 1. `markets.jsonl.gz`: the Polymarket census

[`polymarket_census.py`](../src/eda/tennis_data_audit/polymarket_census.py) took a snapshot of Polymarket's public Gamma API on 10 September 2026 (348 requests, 21:30 to 21:35 UTC). Polymarket keeps revising its records, so **that snapshot cannot be downloaded again**. There are three ways back, best first.

1. **Restore a backup** of `markets.jsonl.gz` and `events.jsonl` (45 MB, same folder, also ignored) into `data/studies/tennis_data_audit/polymarket/`. Check them against the [checksums](#checksums).
2. **Rebuild from a backup of the page cache**, `data/studies/tennis_data_audit/polymarket/raw/` (696 files, 181 MB, ignored). Put it back in place and run:
   ```
   ./python.sh src/eda/tennis_data_audit/polymarket_census.py
   ```
   With a complete cache this takes under a minute and makes no network requests; each cached page is checked against the URL and SHA-256 in its `.meta.json`. Tested on 23 Sep 2026, the decompressed content, `events.jsonl`, `summary.json` and `request-manifest.json` all came out identical. The `.gz` file's own SHA-256 changes, because gzip records when it was written.
3. **Re-run against the live API.** Without the cache, the same command fetches everything again, in about 5 minutes, with no account. The result is a new census, not the 10 September one:
   * It includes contracts added since then, and volumes, prices and closed flags are current.
   * The in-window flag still uses the window fixed in the script, 10 Sep 2025 to 11 Sep 2026. Later matches are flagged out of window, and the price download in section 3 skips them.
   * It rewrites the tracked `summary.json` and `request-manifest.json`, which describe the snapshot that [the census report](../docs/research/tennis-data-audit/polymarket-census.md) cites. Don't commit the rewritten versions unless you mean to replace that evidence. Pass `--out <folder>` to write the new census somewhere else instead.

## 2. `market_index.parquet`: the staged contract index

[`polymarket_prices.py`](../src/ingest/public_dump/polymarket_prices.py) builds this from local files only. It needs the census from section 1 and, if present, the catalog extension in `data/raw/public_dump/polymarket_catalog/` (`events_extension.jsonl` and `markets_extension.jsonl.gz`, both ignored). This rebuilds the event and market index tables without downloading anything:

```
./python.sh -m src.ingest.public_dump.polymarket_prices --no-fetch --no-rebuild
```

* Expect 524,656 rows: 411,502 from the census and 113,154 from the extension files as they stood after the refresh of 5 Oct 2026. The tracked [manifest.json](studies/public_data_dump/manifest.json), regenerated between that day's two refresh runs, records 523,609. Without the extension files you get the 411,502 census rows only.
* The rebuild is deterministic. Pinned to the original build time (22 Sep 2026, about 22:23 UTC), the rebuild on 23 Sep was byte-identical. A normal run uses the current time, so extension contracts whose sporting date has passed become in-window and receive a bucket. A day later 4,667 rows differed, and the number grows with time.
* If the extension files are missing, recreate them first with `./python.sh -m src.ingest.public_dump.polymarket_catalog`. That fetches every tennis event newer than the census up to the day you run it, not just to 7 October 2026, so the index gains rows. Add `--revisit` for the results of events captured while still open.
* The command appends a line to the tracked `data/studies/public_data_dump/polymarket_runs.jsonl`.

## 3. `itf.jsonl.gz` and `challenger_125_inferred.jsonl.gz`: raw price histories

These are raw responses from Polymarket's public price-history endpoint, `https://clob.polymarket.com/prices-history`, which needs no account. They hold minute prices for the first outcome token of every moneyline, stored in one file per inferred tournament-type bucket. The market list comes from the census and the extension, so do sections 1 and 2 first. The `lower` group is exactly these two buckets:

```
./python.sh -m src.ingest.public_dump.polymarket_prices --buckets lower --workers 10 --rps 8
```

* The run of 22 Sep 2026 made 17,946 ITF and 7,024 Challenger requests. The top-up of 5 Oct made 3,127 and 651 more, for 21,073 and 7,675 in all, every one answered (`_receipts.jsonl`). The tracked [download_log.json](studies/public_data_dump/download_log.json), regenerated during 5 Oct, shows 20,610 and 7,631. At 8 requests per second the whole run takes about an hour.
* The run is resumable. If it is interrupted, run it again and it requests only the windows that have no stored response.
* The same command also rebuilds the index tables from section 2 and the price Parquet in `data/dump/odds/polymarket/price_history/`. The staging of 5 Oct holds 24,630,047 ITF and 15,637,893 Challenger price rows (the `.meta.json` files beside the tables); the original of 22 Sep staged 20,593,357 and 14,630,051 ([coverage_tables.md](studies/public_data_dump/coverage_tables.md)). The command also appends a line to `polymarket_runs.jsonl`.
* `--buckets all` re-downloads every bucket, which took 36,295 requests on 22 Sep and 4,482 more on 5 Oct.

The new files will not match the old bytes, because every stored response carries its retrieval time. The responses themselves can match. On 23 Sep 2026, four stored windows (two per bucket) were requested again and came back byte-identical. How long Polymarket keeps serving minute histories for old markets is unknown. A later run also covers more than the original:

* It picks up markets whose sporting date has passed since 5 Oct 2026.
* It extends the windows of markets that were still open then.

The bodies files are append-only: a top-up adds lines at the end. Their first 72,161,992 and 50,464,333 bytes are still the 23 Sep originals. This was checked on 14 Oct 2026 with `head -c <bytes> <file> | sha256sum`, against the [checksums](#checksums).

## 4. `charting-m-points-2020s.csv`: Match Charting Project

This file comes from [JeffSackmann/tennis_MatchChartingProject](https://github.com/JeffSackmann/tennis_MatchChartingProject) at commit `1813a1309b7ed7ebf1c7e884b32bf675d00e4edf` ("thru 18 sep 2026"). It is licensed CC BY-NC-SA 4.0. [`match_charting.py`](../src/ingest/public_dump/match_charting.py) downloads the planned files from that commit that are not already present, about 430 MB for the full set. It records receipts and stages the files to Parquet:

```
./python.sh -m src.ingest.public_dump.match_charting
```

To fetch only this file:

```
curl -L -o data/raw/public_dump/match_charting_project/charting-m-points-2020s.csv \
  https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/1813a1309b7ed7ebf1c7e884b32bf675d00e4edf/charting-m-points-2020s.csv
```

A file fetched with `curl` has no receipt, so the adapter downloads it again the next time it runs. The re-download on 23 Sep 2026 was byte-identical, and its SHA-256 matches the one recorded in [download_log.json](studies/public_data_dump/download_log.json). This only works while the repository stays online. Several of Sackmann's other repositories already returned HTTP 404 on 22 Sep 2026 (see [the public data dump report](../docs/studies/public_data_dump/README.md)).

Run the adapter directly rather than `run_all --sources mcp`, because `run_all` also rewrites the tracked manifest, coverage tables and download log.

## 5. The Hugging Face ATP pipeline dump

[`atp_pipeline_handoff.py`](../src/ingest/public_dump/atp_pipeline_handoff.py) downloads the dataset [`atlas-polybot/atp-pipeline-handoff`](https://huggingface.co/datasets/atlas-polybot/atp-pipeline-handoff) at commit `ea3d94d79f5d9e9b4bead031e2c6262f91a86c35`. The download needs no account. The tracked [plan.csv](studies/atp_pipeline_handoff/plan.csv) lists every file with its hash, and the adapter checks each file against it. From the repository root:

```
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff plan    # only if data/studies/atp_pipeline_handoff/plan.csv is missing
./python.sh -m src.ingest.public_dump.atp_pipeline_handoff fetch
```

* **Resuming.** The fetch resumes: finished files are skipped and part-way files continue from their last complete 256 MB range. [status.md](studies/atp_pipeline_handoff/status.md) shows what is done and what is left.
* **Exact copies.** Files over 1 MB are stored gzipped. The `.gz` bytes differ from run to run, but `gzip -dc` returns the original file, whose hash the adapter has checked.
* **Availability.** The dataset has no licence and could be withdrawn, so this re-download works only while it stays online.
* **Backup.** A zip of the whole folder is in cold storage at `gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip`: Coldline, uploaded 25 Sep 2026, 16,666,419,985 bytes, SHA-256 `bc7d1b49977d4c58f3f3cfe5f49f0f166370d64e2077e3b6593e7b9eb30e6c9f`. To restore:

  ```
  gcloud storage cp gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip .
  tar -x -f tennis_atp_pipeline_handoff_raw_2026-09-25.zip -C data\raw
  ```

  This recreates `data/raw/public_dump/atp_pipeline_handoff/`. The restore was tested with Windows `tar` before upload. `README.txt` in the same bucket folder describes both of the bucket's zips.

## 6. Polymarket trade fills

[`polymarket_trades.py`](../src/ingest/public_dump/polymarket_trades.py) downloads every fill of every tennis moneyline in the index from section 2 whose match was on or before the cutoff (default 21 Sep 2026). It uses Polymarket's public trades endpoint, `https://data-api.polymarket.com/trades?market=<condition id>&takerOnly=false`, which needs no account. The original run on 25 Sep 2026 made 36,028 requests for 35,756 markets with no errors:

```
./python.sh -m src.ingest.public_dump.polymarket_trades --buckets all --workers 8 --rps 14
```

* Two top-ups on 5 Oct 2026 added 4,635 requests for 4,632 markets, with matches to 5 Oct. The command above uses the default cutoff (21 Sep 2026). To get back today's folder, add `--cutoff 2026-10-05T23:24:57+00:00`.
* The run is resumable: a market counts as done when its receipt says so and all its pages are stored.
* The same command rebuilds `data/dump/odds/polymarket/trades/`. To rebuild only that from existing raw files: `./python.sh -m src.ingest.public_dump.polymarket_trades --no-fetch`. It also appends a line to `polymarket_runs.jsonl`.
* Each stored response carries its retrieval time, so the bytes will differ. Fills of settled markets should not change.

The study tables in `data/studies/polymarket_sharp_money/` rebuild offline from the staged fills with `build_positions.py`, `classify.py` and `prematch.py` (see the [study README](../docs/studies/polymarket_sharp_money/README.md#reproduce)).

## Checksums

These are the SHA-256 values of the originals on 23 September 2026. Use them to check a restored backup with `sha256sum <file>`.

| File | Bytes | SHA-256 |
|---|---:|---|
| `markets.jsonl.gz` | 116,560,662 | `cf994e5233da550d7fb7d750805397ae44433d3b7bb07a817f60c5c687319cc5` |
| `markets.jsonl.gz` decompressed (`gzip -dc`) | 928,489,681 | `c9638f66fc7c01114b0fade5246fa45d50742e870d45c7b6be677789845a9a2d` |
| `events.jsonl` (under 50 MB; restored with the census) | 45,028,131 | `8788240b915c5b9ae1a35ba725a3b978e9a76117b0c3ad5861297dd0666f37dd` |
| `market_index.parquet` | 106,526,218 | `248965c65fca1ac34b7775a49307ee40aad1b2a70ec88836b298658c6050e7fe` |
| `itf.jsonl.gz` | 72,161,992 | `987f213059af60790a751572f5c470b08022f427c542972ede9dc263a982d7bb` |
| `challenger_125_inferred.jsonl.gz` | 50,464,333 | `71a0b0176362ec9892c6e9a7d95b481367a96fc7c2bbac20b51f4e7212e8ba34` |
| `charting-m-points-2020s.csv` | 56,590,483 | `2cd43f73e0530a47ea4c02b99dae40177ca6d58a8ccf9189358eb05dffb4be9a` |

The `markets.jsonl.gz` and `events.jsonl` hashes also appear in [manifest.json](studies/public_data_dump/manifest.json), as the source hashes of the two index tables.

Three of these files changed on 5 Oct 2026. Today's copies are byte-identical to those in the 8 Oct 2026 backup (its `manifest.csv.gz`):

| File | Bytes | SHA-256 |
|---|---:|---|
| `market_index.parquet` (rebuilt 5 Oct) | 119,744,255 | `d3c099253169281fc666fd4272444faccda33562369bfcee6a83ca31171d0172` |
| `itf.jsonl.gz` (extended 5 Oct; its first bytes are the 23 Sep row above) | 91,536,045 | `2f65b10a59fc01e61ea788039a22a7674284327a0a2c7a23e1a998cd1e28d989` |
| `challenger_125_inferred.jsonl.gz` (extended 5 Oct; the same) | 54,424,476 | `3f6105e00711f85c068d9189354ff8714fd9bfc994eb2ff98ab35f29b6d33821` |

## Keeping this list current

`.gitignore` matches paths, not sizes. Four kinds of rule keep large files out of git:
* **Folders:** `data/raw/` and `data/dump/` as whole folders.
* **File types:**
  * every `.parquet` file;
  * arrays and model state anywhere (`.npz`, `.joblib`, `.safetensors`), since 14 Oct 2026;
  * archives (`.zip`, `.7z`, `.tar`, `.tar.gz`, `.tgz`) anywhere in `data/`, plus `data/backups/`;
  * a candidate Stage 0's `left_out.csv.gz` under `data/studies/`.
* **Temporary files:** the daily engine's solver caches, `_ios_cache_<stamp>.npz` (about 2.5 GB) and `_cache_tmp.npz`.
  * They exist only while a step runs (`src/eda/daily_prediction/dp_state.py` deletes them), so the table above
    leaves them out.
  * Before the `.npz` rule, one of them in a run folder was the only file over 50 MB that git would have committed
    (13 Oct 2026).
* **Names:** a list of every file over 50 MB, by name, or by folder where a folder holds many.

A large file anywhere else, for example a new CSV in `data/studies/`, would still be committed. So before committing, run these from the repository root in Git Bash.
* They take about a second, because git skips ignored folders.
* The "Permission denied" warnings come from the 11 locked test folders of 2 Oct ([cleanup inventory](../docs/studies/cleanup_inventory/README.md), F).

**Check.** This prints every untracked file over 50 MB that git would pick up. On 14 Oct 2026 it printed nothing: 187 files were over 50 MB, all ignored.

```
git ls-files --others --exclude-standard -z | xargs -0 -r stat -c '%s %n' | awk '$1 > 50000000 {sub(/^[0-9]+ /, ""); print}'
```

**Fix.** This appends each of those files to the end of `.gitignore`:

```
git ls-files --others --exclude-standard -z | xargs -0 -r stat -c '%s %n' | awk '$1 > 50000000 {sub(/^[0-9]+ /, ""); print}' >> .gitignore
```

Then move each new line into the named list in `.gitignore` and describe the file on this page.

**Count.** To count every file over 50 MB, ignored or not (as in the table), use PowerShell from the repository root. `find` takes more than 25 minutes here, because `data/raw` holds over 330,000 files.

```
Get-ChildItem -Recurse -File -Force -ErrorAction SilentlyContinue | Where-Object { $_.Length -gt 50000000 -and $_.FullName -notlike '*\.git\*' } | Measure-Object Length -Sum
```

**Already tracked.** An ignore rule does not remove a file git already tracks. This lists tracked files over 50 MB; on 14 Oct 2026 there were none:

```
git ls-files -z | xargs -0 -r stat -c '%s %n' | awk '$1 > 50000000 {sub(/^[0-9]+ /, ""); print}'
```

Take any it lists out of the index with `git rm --cached <file>`. The file stays on disk.

**Tracked files a newer rule matches.** On 14 Oct 2026 git still tracked:
* 1,646 `.npz` files: 1,279 still on disk (1.35 GB), and the rest deleted on 11 Oct;
* `data/studies/official_point_feeds/wta_checks.csv`.

`git ls-files -ci --exclude-standard` lists them. This takes them out of the index and keeps the files on disk:

```
git rm -r --cached -- '*.npz' data/studies/official_point_feeds/wta_checks.csv
```

The next commit shows them as deleted. History keeps their old versions, so this does not shrink the repository. It stops new versions from being committed.
