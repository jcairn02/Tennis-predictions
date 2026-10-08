# Collect the official Slam and WTA point feeds regardless of their no-scraping terms

**Decided by the owner on 24 September 2026.** Recorded the same day, before any download.

**Loosened on 8 October 2026** by the owner's [approval of all scraping for sports prediction](2026-10-08-scraping-approved.md). Decryption is now allowed, and the "Not allowed" list below is replaced there.

## Decision

Collect the five public feeds in rows 2–6 of the [granular data leads](../research/granular-data-leads/README.md), regardless of the sites' no-scraping terms:

| Row | Feed |
|---|---|
| 2 | Wimbledon scoring feeds, 2019 and 2021–2026 |
| 3 | US Open scoring feeds, 2022–2026 |
| 4 | Australian Open 2026 match centre |
| 5 | IBM extras at the US Open and Wimbledon |
| 6 | WTA official API |

**Basis.** The same as the owner's 23 September decision on SofaScore and TennisLive: collect for non-commercial research. That decision is recorded in the [point- and shot-level sources study](../studies/point_shot_sources/README.md#direct-download-24-september-2026).

**Order.** One source per session. The Australian Open goes first, because only its current edition is served and 2026 will probably vanish in January 2027. It is also the smallest (604 matches), so it sets the pattern for the Wimbledon, US Open and WTA sessions.

## Limits

These apply to every collection session under this decision.

* **Pace.** About 2 seconds between requests, plus jitter. Every run has a `--max-requests` budget. Everything is cached with a receipt, and nothing is fetched twice.
* **Blocks.** Stop and report on any block: HTTP 403 or 429, a bot challenge, a redirect to robots.txt, or a connection reset. Don't escalate.
* **Not allowed:**
  * logins or tokens;
  * solving a CAPTCHA;
  * decryption (Infosys MatchBeats and Court Vision are out of scope);
  * working around a redirect or a 403.
* **Working rules.** Run through `./python.sh` only. No git commits. Don't delete files.

**Clarification given with the decision.** The Australian Open's scores API (`prod-scores-api.ausopen.com`) answers unknown paths with HTTP 403 `{"message": "Missing Authentication Token"}`. That is API Gateway's "not found", not a block, so it is recorded as an absent document rather than stopping the run. Any other 403 still stops the run.

## Where the collection lives

The study `official_point_feeds`:

* adapters in `src/ingest/point_sources/`;
* verbatim responses in `data/raw/point_sources/<source>/`;
* staged tables in `data/dump/points/<source>/`;
* run summaries and checks in `data/studies/official_point_feeds/`;
* tests in `test/official_point_feeds/`;
* the write-up in `docs/studies/official_point_feeds/README.md`.

## Not changed by this decision

* **The terms.** The sites' terms are unchanged; they are quoted in [access routes](../research/granular-data-leads/access-routes.md#terms-and-robotstxt-quoted).
* **The project's status.** No dataset, model or venue is selected.
