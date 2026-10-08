# Acquire more serve-speed data: ManTennisData, and the AO and RG Infosys files decrypted

**Decided by the owner on 7 October 2026.** Recorded the same day, before any download.

**Loosened on 8 October 2026** by the owner's [approval of all scraping for sports prediction](2026-10-08-scraping-approved.md):
* decryption is no longer limited to AO 2025, RG 2025 and RG 2026;
* the ATP Stats Centre files of 2015–2021, requested below and not carried out, are now approved.

## Decision

Take options 1 and 3 of the [serve-speed sources research](../research/serve-speed-sources/README.md#5-what-could-be-done-first-options-not-decisions):

| Order | Acquisition | What it fills |
|---|---|---|
| 1 | Download the public GitHub dataset [`msolonskyi/ManTennisData`](https://github.com/msolonskyi/ManTennisData), about 32 MB | ATP tour level from May 2025: the Stats Centre's per-match first-serve average, maximum and second-serve average |
| 2 | Decrypt the Australian Open's and Roland-Garros's Infosys match-centre files | AO 2025, RG 2025 and RG 2026, which no plain source carries |

The owner's words:
* "We are trying to acquire more serve speed data."
* "Download ManTennisData (about 32 MB) msolonskyi/ManTennisData on GitHub and Decrypt the AO and RG files for the 2025–26 Slam gaps."
* "I am personally ethically comfortable with Decrypting the AO and RG files as all we are doing is building a prediction engine for a fun game, there's no harm to anyone."

**ManTennisData involves no decryption.** It is plain CSV, and its collector keeps the numbers the ATP's own pages show.

**Decryption is allowed for these files only.**
* *Which files:* the AO and RG Infosys match-centre files of AO 2025, RG 2025 and RG 2026.
* *What the decryption is:* the files are served without a login. The Slam's page script decrypts each one in the visitor's browser, with a key derived from the file's own `lastModified` time. The project repeats that step on the files it has saved.
* *Other sources:* the [24 September](2026-09-24-official-point-feeds.md#limits) bar on decryption still holds for everything else, including the ATP Stats Centre files, the LTA's match centre and Court Vision.

## Requested later on 7 October and not carried out: the ATP Stats Centre files of 2015–2021

* **The request:** the owner asked for the ATP's own encrypted Stats Centre files of 2015–2021 ("Acquire this data.").
* **What happened:** Claude stopped before any collection. Six test requests were made, all for one match, the 2018 ATP Finals final; their decrypted copies sit only in the session scratchpad. Nothing was staged.
* **What was kept:** ManTennisData's plain seasons 2015–2020 were downloaded (the same repository and commit as decision 1). They carry no speeds.
* **What remains open:** a licensed route to ATP 2015–20 speeds, through the vendors in the research's section 4.

## Limits

The 24 September limits apply, except the bar on decryption:
* **Pace:** about 2 seconds between requests, plus jitter. Every run has a `--max-requests` budget. Everything is cached with a receipt, and nothing is fetched twice.
* **Blocks:** stop and report, without escalating, on any of these:
  * HTTP 429;
  * a challenge page;
  * a redirect;
  * a connection reset;
  * an HTTP 403 other than the storage's "no such object" answer. That answer counts as an absent file only on a route that has already served a file to the same request headers.
* **Not allowed:** logins or tokens; solving a CAPTCHA.
* **Headers:** requests send the Origin and Referer that the Slam's own page sends, as the research probes did.
* **Scope:** singles only, main draw and qualifying. Doubles are not fetched.
* **Working rules:** run through `./python.sh` only. No git commits. Don't delete files.

## Where the collection lives

* **ManTennisData:**
  * adapter: `src/ingest/public_dump/mantennisdata.py`;
  * raw files: `data/raw/public_dump/mantennisdata/`;
  * staged tables: `data/dump/matches/mantennisdata/`.
* **AO and RG Infosys files:**
  * adapter: `src/ingest/point_sources/infosys_slams.py`;
  * raw files: `data/raw/point_sources/infosys_slams/` (the envelopes as served);
  * staged tables: `data/dump/points/infosys_slams/` (decrypted).
* **The study `serve_speed_acquisition`:** run summaries, links and checks in `data/studies/serve_speed_acquisition/`; scripts in `src/eda/serve_speed_acquisition/`; tests in `test/serve_speed_acquisition/`; the write-up in [docs/studies/serve_speed_acquisition/README.md](../studies/serve_speed_acquisition/README.md).

## Not changed by this decision

* **The sources' terms.** Tennis Australia's and the FFT's sites prohibit automated extraction. atptour.com's terms forbid systematic retrieval, and ManTennisData carries no data licence.
* **The project's status.** No dataset, model or venue is selected.
