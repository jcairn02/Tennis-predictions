# Tennis data audit evidence

These artifacts support the [research reports](../../../docs/research/tennis-data-audit/README.md). They are research evidence, not production data contracts or an approved pipeline. Source access was checked on 10 September 2026; pre-existing tennis-data.co.uk workbooks are explicitly older local snapshots.

## Evidence inventory

| Folder / file | Content |
|---|---|
| [Polymarket audited summary](polymarket/audited-summary.json) | Sporting-date and event-overlap counts, classifications, missingness, IDs and date checks |
| [Polymarket request manifest](polymarket/request-manifest.json) | Exact source request URLs, retrieval times, saved-file paths and hashes |
| [Event inventory](polymarket/events.jsonl) | Full discovered event IDs, links, dates, tags, series, game IDs and scope flags |
| [Compressed contract inventory](polymarket/markets.jsonl.gz) | Contract IDs, token/outcome mapping, rules, date fields and snapshot metadata |
| [Independent QA](polymarket/independent-qa.json) | Separately reproduced counts, pagination/hash checks and specific overlap exceptions |
| [Volume missingness check](polymarket/volume-missingness-check.json) | Distinguishes absent/null volume fields from measured zero values |
| [Public-source receipts](public/fetch_receipts.json) | Downloaded source URLs, access failures and hashes |
| [Public CSV audit](public/csv_audit.json) | File-level schema, missingness, row counts and date ranges |
| [Public table audit](public/table_audit.json) | Parquet, point-state sample and inherited workbook measurements |
| [Market/result candidate joins](public/polymarket_public_candidate_links.json) | Conservative full-name/date candidate matches; not certified settlement joins (local only, 16 MB) |
| [Candidate-join summary](public/polymarket_public_link_summary.json) | Cohort definition, exclusions, ambiguity and results |
| [Unmatched records](public/polymarket_public_unmatched.json) | Retained unresolved records, not silently discarded (local only, 6 MB) |
| [Goalserve example audit](commercial/goalserve-sample-audit.json) | Downloaded static 2019 XML sample and observed ID/status defects |
| [Market-history probes](market_history/probes.jsonl) | Exact public Gamma/CLOB/Data API request receipts; bodies are beside the receipts |
| [Price-history summary](market_history/summary.json) | Thirteen direct observations of counts, intervals, gaps and timestamp units |

Large original downloads live in `public/raw/` and `polymarket/raw/`; the latter are gzip-compressed original JSON responses. Bulk payloads and large generated event/contract inventories are narrowly gitignored to avoid treating hundreds of megabytes as ordinary repository changes. They remain available locally. The same applies to three large generated outputs: the candidate-join and unmatched lists, which `link_public_results_to_polymarket.py` rebuilds, and `public/open_tennis_quarantine_records.json`, which `audit_public_tables.py` rebuilds. Their summaries stay tracked. Scripts, receipts, summaries, reports and source registers are retained as ordinary project files. A repository clone alone does not contain every downloaded raw payload; a later fresh fetch may differ from this saved snapshot.

## Reproduction utilities

| Utility | Behavior |
|---|---|
| [Polymarket census](../../../src/eda/tennis_data_audit/polymarket_census.py) | Read-only public API collection, cached raw pages and source manifest; no account or trading calls |
| [Census analysis](../../../src/eda/tennis_data_audit/analyze_polymarket_census.py) | Offline classification, missingness and count checks |
| [Independent census QA](../../../src/eda/tennis_data_audit/independent_polymarket_qa.py) | Offline independent reproduction and exception inventory |
| [Public payload audit](../../../src/eda/tennis_data_audit/audit_public_payloads.py) | Source requests and CSV checks |
| [Public table audit](../../../src/eda/tennis_data_audit/audit_public_tables.py) | Parquet/XLSX and point-state measurements |
| [Candidate joins](../../../src/eda/tennis_data_audit/link_public_results_to_polymarket.py) | Conservative name/date matching with unresolved records preserved |
| [TML audit](../../../src/eda/tennis_data_audit/audit_tml.py) | Additional Tennis My Life source checks |
| [Goalserve sample](../../../src/eda/audit_commercial_tennis_sample.ps1) | Self-contained PowerShell sample download/inspection |
| [Market-history probes](../../../src/eda/probe_market_history.ps1) | Read-only endpoint probes; refuses to replace existing captures |
| [Catalog chart](../../../src/eda/tennis_data_audit/plot_catalog.py) | Standalone PNG/SVG chart from audited metrics |
| [Report tables](../../../src/eda/tennis_data_audit/write_polymarket_report.py) | Census report tables and source records |
| [Combined source register](../../../src/eda/tennis_data_audit/build_source_register.py) | Validates and combines source catalogs without collapsing evidence levels |

The dedicated project `tennis` environment is absent. Standard-library research utilities deliberately used `C:/Users/zerom/miniforge3/envs/ufc-monitor/python.exe`; table/plot utilities used the existing `C:/Users/zerom/miniforge3/envs/ufc-ag/python.exe` for installed pandas/Parquet/plotting support. PowerShell utilities use PowerShell directly. No dependency installation, environment modification or change to `python.sh` was performed. Read each utility's arguments before rerunning: collection may use cached data, while public upstream sources may change.

## Interpretation limits

Catalog records are not distinct physical matches. Positive lifetime volume is not a year-bounded trade count; missing volume is not zero. A point-state row is not automatically a newly observed point. A name/date candidate is not a verified entity or settlement match. A paid-provider example is not a measured production error rate. Hashes establish which bytes were inspected, not that those bytes are complete or correct.
