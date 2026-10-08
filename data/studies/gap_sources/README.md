# Data map gaps: evidence for the candidate sources

Evidence for [docs/research/gap-sources/](../../../docs/research/gap-sources/README.md) (29 September 2026): whether the sources the [data map](../../data_map.html) names under "Could come from" for its eight gaps hold the missing data. Research only; nothing here is an approved source.

**The sample.** `src/eda/gap_sources/sample.py` (seed 20260929) draws tournament editions from each gap with probability proportional to their gap matches, then a fixed number of matches in each (`role = check`). The editions' other gap matches are kept (`role = listing`) so that a source's listing can be measured on all of them.

## Files

**The sample and SofaScore (the lead session):**

| File | What it is | Made by |
|---|---|---|
| [sample_editions.csv](sample_editions.csv), [sample_matches.csv](sample_matches.csv) | The drawn editions (75) and their gap matches (3,573; 226 to check) | `sample.py` |
| [sofascore_editions.csv](sofascore_editions.csv), [sofascore_matches.csv](sofascore_matches.csv), [sofascore_summary.json](sofascore_summary.json) | SofaScore: each edition located and listed, each gap match linked, and the checked matches' point-by-point and box score read. The summary keeps the last online run (736 requests, stopped by a block) | `sofascore_probe.py` |
| `sofascore_itf_*` (not yet written) | SofaScore for the two gaps no file lists: women's ITF qualifying 2025-26 (with a 2024 benchmark against Sackmann) and ITF after June 2026. Ready, not run: SofaScore was blocking the plain client | `sofascore_itf_listings.py` |

**Other checks by the lead session:**

| File | What it is | Made by |
|---|---|---|
| [wta_2018_probe.csv](wta_2018_probe.csv) | The WTA API's event log and point-by-point for 18 matches of nine 2018 editions | `wta_2018_probe.py` |
| [wta_site_kaggle.json](wta_site_kaggle.json) | The Kaggle copy of the WTA website's match records (`bwandowando`, v29) against Sackmann's women's ITF, year by year, and in the gap years | `wta_site_kaggle.py` |
| [flashscore_itf_summary.json](flashscore_itf_summary.json) | The Flashscore files already on disk (Hugging Face handoff) against the ITF gaps: box scores 2018-24, and women's qualifying | `flashscore_itf.py` |
| [lta_index_links.json](lta_index_links.json) | The Live Tennis API's public match index against the point gaps: an upper bound on what its paid archive could fill | `lta_index_links.py` |

**Lane A: Slam Hawk-Eye copies and women's charts** (the lane stalled after its tables; the lead compiled its notes and added the last two checks):

| File | What it is | Made by |
|---|---|---|
| [hawkilol_matches.csv](hawkilol_matches.csv), [hawkilol_summary.json](hawkilol_summary.json) | Every match of the `hawkilol` Court Vision copy, replayed and linked to the Slam and women's shot gaps | `fetch_hawkilol.py`, `hawkilol_matches.py` |
| [women_charts.csv](women_charts.csv), [women_charts_summary.json](women_charts_summary.json) | Women's website-only Tennis Abstract charts of 2018-26, whether the Hugging Face copy holds each, and the gap link | `women_charts.py` |
| [marcosjn2_ao_rg_summary.json](marcosjn2_ao_rg_summary.json) | marcosjn2 against the AO/RG gap, by lane A's link rules | `marcosjn2_slams.py` |
| [hawkilol_spotcheck.csv](hawkilol_spotcheck.csv) | The lead's independent replay of 40 sampled "complete" Hawk-Eye gap matches against the official score | `hawkilol_spotcheck.py` |
| [ta_chart_pages.json](ta_chart_pages.json) | Three website-only women's chart pages (point log present) and the chart index against 23 Sep | `ta_chart_pages.py` |

**Lane B: tour-level point datasets, the ATP files, Sackmann:**

| File | What it is | Made by |
|---|---|---|
| [marcosjn2_gap_links.csv](marcosjn2_gap_links.csv), [marcosjn2_summary.json](marcosjn2_summary.json) | The Kaggle SofaScore scrape `marcosjn2`: records, replay checks, and the gap matches it fills | `fetch_marcosjn2.py`, `marcosjn2_links.py` |
| [sirgenkii_matches.csv](sirgenkii_matches.csv), [sirgenkii_summary.json](sirgenkii_summary.json) | The SirGenkii fork's 2025 matches, their point outcomes, and the ATP gap link | `fetch_sirgenkii.py`, `sirgenkii_matches.py` |
| [atp_statscentre_probe.csv](atp_statscentre_probe.csv) | 20 ATP Stats Centre file requests for 2025-26 matches (existence and envelope; nothing decrypted) | `probe_atp_statscentre.py` |

**Lane C: ITF listings and Polymarket:**

| File | What it is | Made by |
|---|---|---|
| [itf_site_events.csv](itf_site_events.csv), [itf_site_summary.json](itf_site_summary.json) | The ITF's live-data API (last 14 days) and archived day lists: sampled events, draws, results, statistics and points | `itf_http.py`, `itf_site.py` |
| [itf_listing_counts.csv](itf_listing_counts.csv), [itf_listing_summary.json](itf_listing_summary.json) | ITF rows in the Live Tennis API sample, and Polymarket's settled ITF markets, by month and week | `itf_listing_counts.py` |

**Lane D: TennisLive:**

| File | What it is | Made by |
|---|---|---|
| [tennislive_matches.csv](tennislive_matches.csv), [tennislive_summary.json](tennislive_summary.json) | TennisLive.net on the same 226 checked matches: page, points, completeness, statistics against the official box score | `tennislive_probe.py` |
| [tennislive_itf_after_june.csv](tennislive_itf_after_june.csv), [tennislive_itf_after_june_matches.csv](tennislive_itf_after_june_matches.csv), [tennislive_itf_after_june_summary.json](tennislive_itf_after_june_summary.json) | Follow-up: 8 men's and 3 women's ITF events of July-September 2026 on TennisLive | `tennislive_itf_after_june.py` |

**Lane reports:** [research_notes/](research_notes/) (A, B, C, D), each with URLs, versions, request counts and evidence labels.

## Raw data and reruns

Raw answers are kept verbatim with receipts (URL, time, status, bytes, SHA-256) under `data/raw/gap_sources/<source>/` (gitignored): `sofascore/`, `tennislive/`, `wta/`, `itf/`, `wikipedia/`, `hawkilol/`, `ryurko/`, `ramizheman/`, `marcosjn2/`, `sirgenkii/`, `bwandowando/`, and the Flashscore extract `flashscore_itf.parquet`. The web probes are cached: a rerun asks only for what is missing, and `--offline` (or `--no-fetch`) rebuilds the tables from the cache.

The lead session's scripts, in order:

```
./python.sh src/eda/gap_sources/sample.py
./python.sh src/eda/gap_sources/sofascore_probe.py --max-requests 1500      # add --browser if SofaScore challenges the plain client
./python.sh src/eda/gap_sources/sofascore_itf_listings.py --max-requests 700
./python.sh src/eda/gap_sources/wta_2018_probe.py
./python.sh src/eda/gap_sources/wta_site_kaggle.py
./python.sh src/eda/gap_sources/flashscore_itf.py
./python.sh src/eda/gap_sources/lta_index_links.py
```

The lanes' scripts are rerun as their notes describe.
