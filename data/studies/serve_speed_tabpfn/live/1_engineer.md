# The daily live speed pipeline (speed-data engineer)

8 October 2026.
* **Decisions:** the speed-nudge amendment (28-day memory, daily speeds) and the scraping approval as clarified: path (a); the daily collector decrypts the current season; the 2015–2021 backfill stays encrypted.
* **Offline only:** no ATP request, no match result read, nothing outside the study edited.

## What was built

Code is in `src/eda/serve_speed_tabpfn/live/`; outputs are in `data/studies/serve_speed_tabpfn/live/`.

| Piece | What it does |
|---|---|
| `staging.py` | **Staging format**, one row per match:<ul><li>year, event, match code, round (the source's; otherwise from the main-draw code, MS001 F … MS064–127 R128, right on 99.5% of held links);</li><li>date if known, both players' ATP codes and names;</li><li>first-serve average, first serves in / total, second-serve average, maximum;</li><li>completed flag, source, retrieved_at, collected_on.</li></ul>**Parsers:**<ul><li>`parse_keystats` reads a decrypted keystats object;</li><li>`from_rendered` is the path (b) hook (page labels to the same row);</li><li>`mantd_rows` stages the weekly fallback, with the pair in code order so it carries no winner</li></ul> |
| `atp_daily.py` | **Path (a):**<ul><li>`decrypt_and_stage` imports `infosys_slams.key_iv` / `decrypt`;</li><li>`guard` refuses 2015–2021, any year before 2026, and any path under `data/raw/point_sources/infosys_atp/`, **before the file is opened**;</li><li>`plan_days`, and `fetch_daily` (off)</li></ul> |
| `link.py` | **Crosswalk** from ATP code to project id, 2,462 codes, learned from ManTennisData's Stage 0 links, the Infosys handoff's and Tennis My Life's (TML) rows Stage 0 holds. The majority id is kept if it has ≥ 80% of a code's links; an unknown code becomes `atpcode:` (Stage 0's own convention).<br>**Matches:** the id Stage 0 would build, else the same pair in the event, else names (shot-level linker), else TML for matches newer than Stage 0. TML is read through its identity columns only |
| `live_panel.py` | `speed_panel_live.parquet` is the frozen panel, unchanged, plus new rows:<ul><li>basis KS − 0.5, n = first serves in;</li><li>release = the collection day, never before `lf + 1`;</li><li>frozen rows take scenario B's release, capped at 7 Oct but not before `lf + 1`</li></ul> |
| `form.py` | The 28-day form of each ATP player as of a day: f̂, σ̂, L̂, rows, k14, k28 and his latest reading. It reuses `features_latency.Scenario` / `side_values_v`, `features.prepare_panel` and `panel.EditionOffsets`.<br>`spd_L(a, b, day)` = clip(Δf̂ / 1.9496051535048338, ±4) |
| `src/ingest/speed_daily.py` | The runner:<ol><li>ManTennisData refresh on Mondays, then staging;</li><li>ATP collector (off; `--plan-only` sends nothing);</li><li>linking;</li><li>live panel;</li><li>`speed_form_<date>.parquet`; one line in `runs.jsonl`.</li></ol>Not wired into `scheduled.py` |

**Today's offline run** (8 Oct): 8 new rows (4 matches the acquisition had not linked); the form covers 1,093 players, 174 with a reading in 28 days, the latest on 3 Oct.

## Tests

38 offline tests in `test/serve_speed_tabpfn/test_ssp_live_*.py`, **all pass**; 59 with the panel and availability suites.

| Test file | What passes |
|---|---|
| Staging | <ul><li>40 held handoff records parse to exactly what `panel.py`'s parser cached (60+ player values);</li><li>the path (b) hook equals the decrypted row;</li><li>code→round cases; the plausibility rule;</li><li>ManTennisData pairs drop the winner order</li></ul> |
| Decrypt | <ul><li>the four pinned keys;</li><li>a synthetic round trip in 2026 and 2027;</li><li>every 2015–2021 year refused, and 2022–2025;</li><li>the backfill folder refused whatever the year;</li><li>a 2019 file refused before it is read;</li><li>decrypt-and-stage values;</li><li>the fetch off by default, and refused without the adapter unless allowed;</li><li>a stand-in client gets the exact routes within the budget</li></ul> |
| Link (held 2026 ManTennisData) | <ul><li>Agrees with the acquisition's links on 99.8% of 2,121 player-matches, same side 99.9%.</li><li>With Tokyo, Beijing, Chengdu and Hangzhou hidden from Stage 0, TML links 111 of 113; the ids built equal Stage 0's on 99.1%, the sides on 100%.</li></ul> |
| Form and panel | <ul><li>**The live `spd_L` reproduces the adaptive study's `spd_L_D` exactly** on 40 men's frame matches (largest difference 0.0).</li><li>Antisymmetry and clipping; a player with no data counts 0.</li><li>New rows follow the key-statistic rule.</li><li>The runner offline leaves the frozen files' SHA-256 unchanged and the frozen rows equal.</li><li>Plan-only stages nothing.</li></ul> |

## The first live test (after the lead's go-ahead)

1. **Set** `live/collector.json` to `"atp_daily_enabled": true`.
   * Also either put the backfill adapter on disk or set `"require_backfill_adapter": false`. The adapter is not on disk here.
   * **Lead's correction, 8 Oct 09:30.** The adapter *is* on disk: `src/ingest/point_sources/infosys_atp.py`, 30,644 bytes. It imports cleanly from the repository root. So `require_backfill_adapter` stays `true`, and the collector uses its client and headers.
2. **Run** `./python.sh src/ingest/speed_daily.py --mantd skip --max-requests 60` (`--plan-only` first sends nothing).
3. **What it asks for:** for each tour-level or Challenger round that TML lists as played yesterday, that round's codes. The route is `https://itp-atp-sls.infosys-platforms.com/prod/api/stats-plus/v1/keystats/year/<Y>/eventId/<E>/matchId/<MID>`.
4. **Today's plan, for 7 Oct:** Shanghai (event 5014) R128, MS064–MS127, 64 codes, cut to **60 requests**. That is about 2.5 minutes at 2 s plus up to 1 s of jitter, with Origin/Referer atptour.com.
5. **How each answer is kept:** a receipt for every answer in `data/raw/point_sources/infosys_atp_daily/`; a 404 is recorded as absent and asked again when its round is played; any block (403, 429, a challenge, a redirect) stops the run.
6. **Then:** decrypt (2026 only) → `staging/atp_daily_<date>.parquet` → link → live panel → form.

## Caveats

* **Byes and unplayed codes cost requests** (about half of Shanghai's R128 codes are byes). The answer for an unplayed code is not yet known; RG 2026's API answered 404.
* **Qualifying asks up to QS063,** because QS codes overlap between rounds.
* **TML dates** ran 1–2 days after the timing clock on 24 of 111 matches at Asian events; only a reading's age is affected.
* **216 ManTennisData 2026 Challenger qualifying rows stay unlinked:** Stage 0 and TML lack them.
