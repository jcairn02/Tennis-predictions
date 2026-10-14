# The research subagent's brief (P7's "elsewhere" search, 13 Oct 2026)

Companion of [process_log.md](process_log.md) (section "Work packages P7 and P13", appendix). Launched on 13 Oct 2026 at about 22:35 UTC by session `8b00b734-ccf1-42cc-bd90-a3bb292e7ad2`, as a general-purpose subagent in the background. Its report is [itf_2025_points.md](../../research/gap-sources/itf_2025_points.md). The brief, verbatim:

````text
You are researching data sources for a tennis prediction project at C:\Users\zerom\Documents\Tennis-predictions (Windows; use the project's `./python.sh` from Git Bash for any Python; it runs the `tennis` conda env). Research only: no git commands that change state, delete nothing, and do not edit existing files. The one file you may create is the research note named below.

## The gap to fill
Work package P7 collects SofaScore's point-by-point records (and box scores) for ITF main-draw singles matches. It found that **SofaScore has no ITF point records from January 2025 to February 2026**. Every request for a February 2026 match returned HTTP 404 (1,471 in a row), and SofaScore's listings flag almost every ITF event of January 2025 to February 2026 with `coverage: -1` (point records on 8 of 1,403 flagged events). From March 2026 on, coverage is near complete, and 2024 was complete in a trial. The missing window covers about 40,000 ITF main-draw singles matches, men and women. For most of them the project already holds results, and for many Sackmann's box scores, but no points.

**Goal:** find any other source of ITF point-by-point records (complete, or partial, e.g. point winners per game) for ITF matches of January 2025 to February 2026, or any route to them. Box scores are a secondary interest.

## Read first (skim; do not redo what is already established)
- `CLAUDE.md` (Research discipline section: separate observed data, provider claims, inference, unknowns; record URLs, access dates, versions).
- `docs/research/gap-sources/README.md`: the earlier source research, especially its ITF sections and the source table.
- `docs/studies/gap_downloads/collection-plan.md`: the P8 and P12 sections and "Not in this plan".
- `docs/studies/gap_downloads/README.md`: the section "SofaScore by edition: ITF (work package P7)" and the P4/P5 TennisLive sections (TennisLive pages carry partial ITF points, without the set-closing games).
- `docs/studies/atp_pipeline_handoff/README.md` and `data/data_map.yaml` entry `flashscore`.

## What to do
1. **Offline: the Flashscore handoff copy on disk** (`data/raw/public_dump/atp_pipeline_handoff/flashscore_full/`, `flashscore_gql_stats/`, `flashscore_daily/`, `flashscore_data/`, `flashscore_bruteforce/`; about 127 GB of JSON, never read for points; its loader is `src/ingest/public_dump/atp_pipeline_handoff.py`). Find out whether any of it holds point-by-point, or game-by-game point histories, for ITF matches, and how many of January 2025 to February 2026, by month and men/women. Sample sensibly: inspect the structure first, then count with streaming reads. Do not load 127 GB into memory. Report what fields exist and what grain they reach.
2. **Offline: anything else on disk** with ITF 2025 points: for example TennisLive's raw pages under `data/raw/point_sources/tennislive/` (what share of ITF 2025 match pages have points, and how partial), the ITF live-data API's raw files (`data/raw/point_sources/itf_live/` or similar), and other dumps under `data/raw/` and `data/dump/`. Use the existing study outputs (`data/studies/...`) where they already answer this.
3. **Web research** (WebSearch/WebFetch; no logins, no sign-ups, no paywalls, no CAPTCHAs):
   - public datasets with ITF 2025 point-by-point: GitHub, Kaggle, Hugging Face, Zenodo;
   - live-score sites and APIs that show ITF point-by-point publicly (Flashscore/Tennis24, AiScore, 365Scores, LiveScore, BetsAPI, Tennis Explorer and others). Check what one ITF match of, say, May or October 2025 shows. A handful of requests per site at most, at least 2 seconds apart; record the URLs and access dates;
   - vendors' claims about ITF point data for 2025 (Live Tennis API, Sportradar, API-Tennis, Goalserve, Enetpulse...): record the claims and free tiers only.
4. **Do NOT send any request** to these hosts, which other collectors are using or which are reserved:
   - `www.sofascore.com` or any `*.sofascore.*` API;
   - `itftennis.com` or `api.itf-production.sports-data.stadion.io`;
   - `tennislive.net`.

   Reason about those only from files on disk and from web search results.

## Output
Write `docs/research/gap-sources/itf_2025_points.md` (new file). For each candidate source, give:
- what it holds for ITF January 2025 to February 2026: complete points, partial points, box scores, or results; men or women; main draw or qualifying; how many matches;
- how it could be collected: requests, blocks, cost;
- the evidence, labelled observed, provider claim or inference, with URLs and access dates.

End with a short ranked recommendation. Keep it concise and factual. Then return a summary of under 300 words: the best two or three leads with their numbers, and anything that needs the owner's decision (paid sources, for example).
````
