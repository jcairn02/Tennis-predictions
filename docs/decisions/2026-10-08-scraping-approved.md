# All scraping for sports prediction is approved, decryption included

**Decided by the owner on 8 October 2026.** Recorded the same day.

**The context.** Claude reported that the 7 October approval to decrypt the Roland-Garros and Australian Open files named only AO 2025, RG 2025 and RG 2026. So RG 2027 would need asking again. Earlier on 7 October, a session had also stopped short of the owner's request for the ATP's 2015–2021 Stats Centre files ("Acquire this data."). The owner's words:

> "No, thats an agent over compensating for a misperception. I do not want that. I approve this. We need this for the data for sports prediction. Loosen the requiements, I approve of all scraping for sports prediction reasons"

## Decision

1. **Any sports data that a website, app feed or file serves publicly may be collected by automated means for the project's predictions.**
   * This covers results, statistics, point-by-point data, serve speeds, odds, prices and schedules.
   * It applies regardless of the site's terms of use or its robots.txt.
2. **Decryption is allowed.** Repeating the step a site's own page performs to show its data is part of collecting it. This covers:
   * the Infosys match-centre files of the ATP Stats Centre, the Australian Open and Roland-Garros;
   * Court Vision;
   * the LTA's match centre;
   * any similar feed.

   It covers **every edition, past and future**. There are no more per-source or per-year approvals.
3. **Collecting during an event (live) is allowed.** When live collection is scheduled stays a practical choice (the [download cadence](2026-10-06-download-cadence.md)), not a permission.
4. **Sessions do not stop to ask** before collecting sports data under this decision. They keep receipts and raw copies as before, and say what they collected.

## Clarified by the owner later on 8 October 2026

> "The daily collector we NEED to decrypt them. The do not decrypt only applie to the 2015-2021 session"

* **The daily ATP speed collector decrypts** the current season's ATP Stats Centre (Infosys) files and stages their speeds. It is built for the serve-speed adjustment ([speed-nudge amendment](2026-10-07-speed-nudge.md)).
* **The 2015–2021 backfill stays encrypted.** Session `tennis-predictions-74` was told "DO NOT DECRYPT IT. I just want the encrypted files on my computer." Its files (`data/raw/point_sources/infosys_atp/`, years 2015–2021) are not decrypted until the owner says otherwise.

## How collection is run (good practice, not permission)

These keep the collectors working and avoid overloading the sites:
* **Pace.** About 2 seconds between requests plus jitter, a request budget per run, a cache so nothing is fetched twice, and every response kept with a receipt.
* **Blocks.** On HTTP 429, a challenge page or an unexpected 403: pause, back off, and report.

**Not covered,** because it is not scraping of publicly served data:
* logging in with credentials the owner has not supplied;
* getting past a paywall the project has not paid for;
* solving CAPTCHAs.

The owner can extend this.

**Working rules unchanged:** `./python.sh` only; no git commits; don't delete files.

## What it replaces

* **[24 September](2026-09-24-official-point-feeds.md):** its "Not allowed" list. Decryption is now allowed. Logins and CAPTCHAs fall under "Not covered" above; blocks under the practice above.
* **[7 October](2026-10-07-serve-speed-acquisition.md):** "Decryption is allowed for these files only." The ATP Stats Centre files, 2015–2021 and onward, are now approved, as is every AO and RG edition.

## Risks the owner accepts

* The sites' terms forbid automated extraction.
* Decrypting obfuscated files may raise legal questions in some places.
* Collectors can be blocked, and sources can change without notice.

The owner accepts these for a non-commercial prediction project.

## What it unlocks now

* **Daily ATP tour-level serve speeds** from the Stats Centre, for the speed adjustment. In the [latency follow-up](../studies/serve_speed_tabpfn/latency.md) (exploratory), its gain was +0.38 mLL with today's weekly data, about +0.47 with a daily tour collector, and +0.54 with instant data, all with the 28-day memory.
* **The ATP's 2015–2021 Stats Centre files:** serve speeds before October 2021, a longer history for the adjustment.
* **Every Australian Open and Roland-Garros edition,** and Wimbledon and the US Open live during the event.
* **Other restricted sources,** Flashscore for example.
