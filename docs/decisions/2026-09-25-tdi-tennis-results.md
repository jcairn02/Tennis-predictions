# Collect TDI's Tennis Results site regardless of its no-scraping terms

**Decided by the owner on 25 September 2026.** Recorded the same day, before any download, by the session that researched TDI's access routes. The owner's words: "Dont be concerned about no scraping".

## Decision

Collect TDI's public Tennis Results site (`results.tennisdata.com`; row 9 of the [granular data leads](../research/granular-data-leads/README.md)).

**Its terms, which this decision sets aside:** they forbid scraping, and use for statistical models or betting. They are quoted in [TDI and open data](../research/granular-data-leads/access-routes-tdi-and-open-data.md).

**Scope:** every ATP Tour (non-Slam) and Challenger match the site serves, singles and doubles, main draw and qualifying.

**Order:**
1. The match ids in the listing's rolling window (about 93 days), before the window moves on.
2. The pages of those matches.
3. The 634 older ids preserved by the Wayback Machine ([tdi_wayback_match_ids.csv](../../data/studies/granular_data_leads/tdi_wayback_match_ids.csv)).
4. Every new match, going forward.

**Basis:** this extends the [24 September decision](2026-09-24-official-point-feeds.md) on the official Slam and WTA feeds to TDI.

## Limits

The [24 September limits](2026-09-24-official-point-feeds.md#limits) apply unchanged:
* about 2 seconds between requests, plus jitter;
* a `--max-requests` budget on every run;
* everything cached with a receipt, and nothing fetched twice;
* stop and report on any block, and don't escalate;
* no logins, tokens, CAPTCHA solving or decryption, and no working around a redirect or a 403;
* `./python.sh` only; no git commits; no deleted files.

**How they apply to this site:**
* **Old match pages.** An old match page answered with HTTP 404 that still carries its points is a document, not an absence. A 404 without points is an absence.
* **Out-of-window dates.** A listing date outside the window is answered with today's list. It is recorded as outside the window, not as that day's matches.

## Where the collection lives

TDI joins the study `official_point_feeds`:
* the adapter in `src/ingest/point_sources/tdi.py`;
* verbatim pages in `data/raw/point_sources/tdi/`;
* staged tables in `data/dump/points/tdi/`;
* run summaries and checks in `data/studies/official_point_feeds/`;
* tests in `test/official_point_feeds/`;
* a TDI section in `docs/studies/official_point_feeds/README.md`.

## Not changed by this decision

* **The terms.** TDI's terms are unchanged.
* **The project's status.** No dataset, model or venue is selected.
