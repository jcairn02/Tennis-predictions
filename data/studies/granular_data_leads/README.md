# Granular data leads: evidence

Evidence for [docs/research/granular-data-leads/](../../../docs/research/granular-data-leads/README.md) (24 September 2026). Research only; nothing here is an approved source.

| Item | What it is |
|---|---|
| [tennis_abstract_chart_gap.csv](tennis_abstract_chart_gap.csv) | Every chart id on the Tennis Abstract index or in the held Match Charting Project export, with whether it is on the website, in the export, and has points in the dump; URL for website charts. Built by `src/eda/granular_data_leads/mcp_website_gap.py` from the index downloaded on 23 Sep 2026 |
| [tennis_abstract_chart_gap.json](tennis_abstract_chart_gap.json) | Counts from the same script: 6,447 website-only charts by year and tour; 2,416 export matches without points in the dump, by decade |
| [tdi_wayback_match_ids.csv](tdi_wayback_match_ids.csv) | The 634 TDI Tennis Results match ids from before the site's ~93-day listing window that the Wayback Machine preserves (homepage listings and match-page captures), with the capture each came from. Built from Wayback captures on 24 Sep 2026 |
| [research_notes/A_tour_official.md](research_notes/A_tour_official.md) | ATP and WTA official data: TDI Tennis Results, Infosys Stats Centre files, the SirGenkii fork, the WTA API, TennisViz |
| [research_notes/B_grand_slams.md](research_notes/B_grand_slams.md) | Grand Slam scoring feeds (Wimbledon, US Open, Australian Open, Roland-Garros), IBM extras, other official events |
| [research_notes/C_commercial_vendors.md](research_notes/C_commercial_vendors.md) | Paid and B2B feeds and Sportradar's public widget feed, with a per-point width matrix |
| [research_notes/D_open_datasets.md](research_notes/D_open_datasets.md) | Open datasets and code repositories: Court Vision copies, MCP pre-2010 files, From AO to AI, return-impact tracking, older point strings |
| [probe_logs/](probe_logs/) | Request logs of the ATP/WTA and Grand Slam passes (UTC time, URL, status, bytes, headers used); per-draw "H" coverage counts; the follow-up's 21 TDI requests (`E_tdi_access_probe_log.tsv`) |
| [research_notes/E_access_routes.md](research_notes/E_access_routes.md) | Follow-up for [TDI and open data](../../../docs/research/granular-data-leads/access-routes-tdi-and-open-data.md) (rows 9–13): TDI's listing window and where older ids survive; paid routes (Sportradar micro-markets, Live Tennis API, an Apify scraper); the four downloads checked; larger public copies (Hugging Face ATP Stats Centre dump, Tennis Australia's 2019 release, the TennisVisuals upstream) |
| [research_notes/F_slam_licensees.md](research_notes/F_slam_licensees.md) | Follow-up for [access routes](../../../docs/research/granular-data-leads/access-routes.md) (rows 2–6): who holds and sells official Wimbledon, US Open and Australian Open data; IBM, Hawk-Eye, TennisViz, Infosys |
| [research_notes/G_vendor_history.md](research_notes/G_vendor_history.md) | Follow-up (rows 2–6): which vendors sell historical Slam point-by-point data, with fields, buyers, prices and licence limits |
| [research_notes/H_wta.md](research_notes/H_wta.md) | Follow-up (rows 2–6): WTA terms and robots.txt, who powers and holds WTA data, paid routes |
| [research_notes/I_open_datasets.md](research_notes/I_open_datasets.md) | Follow-up (rows 2–6): status of Sackmann's deleted Slam archive and its copies; the IBM 2016 Wimbledon release; official open releases |

The research passes were run by parallel agents; the notes are their reports as returned, lightly edited. Payloads they read were kept in the session scratchpad, not here, and are not reproducible downloads.

Rerun the chart gap: `./python.sh src/eda/granular_data_leads/mcp_website_gap.py`
