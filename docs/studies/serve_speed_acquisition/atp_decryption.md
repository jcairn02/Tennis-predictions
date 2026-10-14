# Local ATP Infosys decryption — 8 October 2026

The owner requested decryption and verification of every downloaded file in `data/raw/point_sources/infosys_atp/`. The [updated collection decision](../../decisions/2026-10-08-scraping-approved.md) records the instruction superseding the earlier encrypted-only backfill.

## Outputs and verification

**4,906 of 4,906 encrypted envelopes decoded successfully**, with zero errors. Plain UTF-8 JSON is in **`data/dump/points/infosys_atp/decrypted/`**, retaining `<year>/<event>/<route>/<match>.json`. Every decoded field is retained. Court Vision retains its original `a...` field names.

* Original compressed envelopes: 177,357,446 bytes. All raw file hashes remained unchanged after processing.
* Plain JSON: 366,892,254 bytes (366.9 MB).
* Every decompressed envelope matches the SHA-256 in the download inventory.
* Every written JSON was re-read and compared with its decoded object; every output also passed an independent hash and schema-type check.
* All files have the expected tennis schema for key statistics, MatchBeats, rally analysis or Court Vision. MatchBeats event IDs and match IDs match their file paths. The 2018 final identifies Novak Djokovic and Alexander Zverev, with maximum, first-serve average and second-serve average speeds.
* The existing decoder tests passed: 9 passed, 17 deselected (`key_iv or decrypt or to_base`).

The file-level audit is `data/studies/serve_speed_acquisition/infosys_atp_decryption/files.csv`; totals and route counts are in `summary.json`. These include envelope and output hashes, tennis schema checks, identity checks, positive-speed counts and any errors.

## Observed serve-speed coverage

Valid match data does not necessarily contain measured speeds. **731 files contain positive speed values, covering 186 distinct year/event/match codes across routes.** Of those, **184 matches** belong to the backfill; two are the newer calibration matches.

| Year | Files decoded | Files with positive speeds | Distinct matches with positive speeds |
|---|---:|---:|---:|
| 2018 | 59 | 59 | 15 |
| 2019 | 90 | 0 | 0 |
| 2020 | 491 | 0 | 0 |
| 2021 | 4,262 | 668 | 169 |
| 2022 calibration | 3 | 3 | 1 |
| 2025 calibration | 1 | 1 | 1 |
| Total | 4,906 | 731 | 186 |

There are no 2015–2017 envelopes in the local folder. The 2019–2020 payloads are valid tennis data but contain no positive speeds in the expected speed fields. The remaining 4,175 files across all years have no positive speeds. Missing fields, empty values and zeros are preserved.

Speed fields audited: key-statistic rows named `Max Speed`, `1st Serve Average Speed` and `2nd Serve Average Speed`; `serveSpeed` and `faultSrvSpd` in the point payloads; and Court Vision trajectory field `a16`, with values such as `194.38 KPH`. Multiple routes represent the same match, and per-set statistics repeat aggregate values; the speed-value counts are not counts of unique serves.

This export is not a cleaned model input. 124 positive speed values fall outside the audit range of 50–300; all are preserved and flagged in the file report. Cross-source player reconciliation and later feature construction remain separate work.

## Reproduction

Run offline, through the project environment:

```bash
./python.sh -m src.ingest.point_sources.infosys_atp_decrypt
```

The exporter reuses the existing Infosys browser-compatible decoder. Existing plaintext files must match the expected decoded bytes; differing outputs are preserved and reported as errors. It makes no HTTP requests.
