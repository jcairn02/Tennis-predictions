# Career coverage: ten Challenger careers checked match by match

**99.1% of the 4,025 matches on ten randomly drawn Challenger players' official ATP records are somewhere in the staged public dump (98% with at least the final score), and 57% carry serve and return totals. Detail is set by level and date rather than by player: 98% of Challenger and tour-level matches have serve statistics, against 0.1% of ITF main-draw matches before 2025 (92% from January 2025 to June 2026). Point-level or shot-level data exists for 2%. ITF qualifying, which the ATP record omits, is absent from every source (30 such matches in the one ITF season that could be read).**

**Status: study, not a decision.** It measures the staged public dump of 22 September 2026 against official records; it does not select a source or approve a structure.

| Item | Where |
|---|---|
| Report for readers (HTML: charts, match explorer, findings) | [report.html](report.html) |
| Sample draw | `src/eda/career_coverage/select_players.py` → [sample.json](../../../data/studies/career_coverage/sample.json) |
| Official record, transcribed | [atp_activity_raw/](../../../data/studies/career_coverage/atp_activity_raw/) (per season, plus `_fix` re-reads and a `superseded/` folder of discarded split reads), [atp_event_lists/](../../../data/studies/career_coverage/atp_event_lists/) (independent tournament lists), [itf_activity_raw/](../../../data/studies/career_coverage/itf_activity_raw/), [atp_profile_totals.json](../../../data/studies/career_coverage/atp_profile_totals.json) |
| Transcription check | `check_transcripts.py` → [transcript_check.json](../../../data/studies/career_coverage/transcript_check.json) |
| Linking and grading | `build_coverage.py` → [reference_record.csv](../../../data/studies/career_coverage/reference_record.csv), [local_rows.csv](../../../data/studies/career_coverage/local_rows.csv), [coverage.json](../../../data/studies/career_coverage/coverage.json) |
| Report rendering | `render_report.py` + `report_template.html` |
| Tests | `test/career_coverage/` (offline, 13 tests) |

## Question

For players who compete on the ATP Challenger Tour: (A) a random sample across the ranking range; (B) every match of their careers, lined up against the official record; (C) what share is in the dump, by player, level and season, and what is missing and why; (D) how much in-match detail the dump holds for the matches it has, and how unevenly that detail is spread.

## Method

1. **Sample.** Players ranked 1–700 in the Tennis My Life ATP ranking of 31 August 2026, with at least five Challenger main-draw matches in the preceding 52 weeks and born 1994 or later (so a whole career fits the dump's 2010+ window). Five rank bands (1–100, 101–200, 201–300, 301–450, 451–700), two players each, seed 20260923; two reserves per band were drawn and not needed (every pick's first ATP season is 2012 or later). Sample: Choinski, Walton, Glinka, Onclin, Sanchez Izquierdo, Hardt, Piraino, Pieri, Holt, Villalon.
2. **Official record.** The ATP website's per-season singles activity (`https://www.atptour.com/en/-/www/activity/sgl/<code>/<year>?v=1`), 96 player-seasons, read on 23 September 2026 through the WebFetch tool (plain HTTP clients get a Cloudflare challenge) and transcribed into pipe-separated lines. It lists ITF (Futures) main draws, Challenger and tour-level main draws and qualifying, and Davis Cup.
3. **Transcription control.** Every season was read a second time as a short list of tournament ids, dates and match counts; tournaments missing from, extra to, or miscounted in a transcription were re-read one at a time (`_fix` files, which replace that tournament's lines; `NONE|id` would remove one). After this, all 96 seasons agree with their lists. Each player's tour-level win–loss in the transcription was compared with the ATP profile's headline figure: nine of ten agree, and Walton's difference (25–48 vs 25–46) is exactly two tour-level losses in the window described next.
4. **Unreadable window.** Walton's 2024 page is longer than the reading tool's ~100,000-character limit; everything before Burnie 2 (week of 5 February 2024) never reached it and every read of it was invented. Only the part before the cut is kept (`UNREAD` in `build_coverage.py`); our 18 rows in those weeks are labelled rather than counted as errors.
5. **ITF record.** The ITF activity API was to add ITF qualifying. After the first reads the ITF website refused all automated requests (empty responses, including its homepage); no workaround was attempted. Only Pieri's 2023 season was read, so ITF qualifying is reported as a sample and the headline figures use the ATP record.
6. **Local rows.** Every row for each player in the eight dump sources: Sackmann archive (ATP main, qualifying/Challenger, Futures; by numeric id, a second id where the player file has one, and exact name), Tennis My Life (ATP code and name), tennis-data.co.uk (`Surname I.`), Open Tennis Data (Sackmann ids), Live Tennis API sample (index and June 2026 score states), Match Charting Project, Grand Slam point files, Polymarket moneylines (with minute-price presence).
7. **Linking.** A row links to an official match of the same player when the opponent agrees (ATP code for Tennis My Life; otherwise normalised name equal, token containment, surname plus initial, a shared token of four or more letters, or a close fuzzy match) and the date is inside the tournament week (±10 days, or −12/+20 for match-day and scheduled-time sources); round agreement and the smaller gap break ties, and remaining ties are ambiguous. Two further passes recover rows filed under another week (same round and opponent, shared tournament-name word, within a year, unique) and rows naming another opponent (same round and week, identical set scores, unique). A leftover row repeating a matched row of the same source is a duplicate; a leftover row in a week the official record has the player elsewhere is flagged as misattributed.
8. **Grading.** Each official match takes the richest layer any source holds: missing; listed only (schedule or market, no score); score only; score plus serve/return totals (both players' serve points present in Sackmann or Tennis My Life); point-by-point (Grand Slam point files or Live Tennis API score states); shot-by-shot (Match Charting Project).

## Results

| Depth | Matches | Share |
|---|---:|---:|
| Not in any source | 37 | 0.9% |
| Listed only, no score | 59 | 1.5% |
| Score only | 1,644 | 40.8% |
| Score + serve/return totals | 2,200 | 54.7% |
| Point-by-point sequence | 76 | 1.9% |
| Shot-by-shot chart | 9 | 0.2% |

* **By level.** ITF main draws are half of these careers (2,008 matches): 99% present, but before 2025 0.1% with statistics (the sources kept scores only), 92% from January 2025 to June 2026. Challenger main draws (1,312), tour-level qualifying (212) and main draws (119) are 100% present, 98% or more with serve statistics. Challenger qualifying (360) is 98% present; 8 of its 9 gaps predate June 2026, while 14 of its 23 listed-only matches (schedule or market, no score) come after it, when no source carries that level. Davis Cup (14): 2 ties absent.
* **By player.** Presence 94% (Villalon) to 100% (Walton). Serve statistics 49% (Glinka, 59% of career at ITF level) to 77% (Walton, 23%): the share of a career spent at ITF level before 2025 decides it.
* **Missing matches (37).** 5 lower-level matches after June 2026; 11 single matches from tournaments otherwise present (8 ITF main-draw, 3 Challenger qualifying); 21 in 12 tournaments absent from every source (ITF events such as Spain F30/F31 2018, Challenger qualifying such as Furth 2015, two Davis Cup ties). A further 59 matches are listed only by a schedule or market, 29 of them lower-level matches after June 2026. The report's match explorer lists all of them.
* **Deeper layers.** 85 matches: 82 with Live Tennis API score states (a one-month sample, June 2026), 9 in Grand Slam point files, 9 charted.
* **Agreement between sources.** Where both Sackmann and Tennis My Life have serve totals (1,334 matches), serve points are identical in 1,326. All 3,584 box-score rows carry all 18 serve fields; 3,541 also carry match length.
* **ITF qualifying (sample).** Pieri's 2023 ITF record lists 30 qualifying matches next to 42 matches on the ATP record for that season; none is in the dump even as a schedule entry. All 42 of that season's ITF main-draw matches on the ITF record are also on the ATP record.

## Findings for the cleaning and merge phase

1. **Sackmann second identities.** Nicolas Villalon's later ITF matches (80) sit under "Nicolas Villalon Valdes" (id 211477) as well as id 210507. Identity resolution must merge such records before any per-player history is built.
2. **Sackmann misattribution.** Ten 2018–2020 ITF wins in Asia and Egypt are credited to Gauthier Onclin; in four of those weeks the ATP record has Onclin at a different tournament.
3. **Sackmann wrong opponent.** Milan Welte's results appear under Alexandre Aubriot's name (same scores, same rounds) in two players' careers.
4. **Sackmann duplicates.** Choinski's Germany F3 run (January 2017) is repeated as "Germany F4" in June 2017.
5. **Tennis My Life misdating.** 36 rows are filed under the wrong week, up to ten months off (Hardt's Antalya Challengers of November–December 2021 under January 2021; Holt's February 2025 Manama run under November 2025). Earlier observed: a row carrying Glinka's code on another pairing's match (Charlottesville 2025).
6. **Coverage edges.** Challenger qualifying and ITF main draws have no source after 1 June 2026 (Tennis My Life carries Challenger main draws only); ITF qualifying has never been collected; the dump is ahead of the ATP record for matches of the current week.
7. **For anyone reading the ATP site:** Davis Cup rubbers of a tie share one stats URL (`…/ms000`); lucky losers appear as a Q loss followed by an R128 bye; seasons dated from late December belong to the next year; long seasons exceed a web-reading tool's page limit.

## Limitations

* The official record is a model-mediated transcription. Structural errors were controlled (second list read, targeted re-reads, win–loss check, and every dump row matched back), but a score or opponent-rank typo can remain; scores are not used for coverage except in the wrong-opponent pass.
* ITF qualifying was measured for one player-season only; the dump's blind spot there is certain, its size across careers is not.
* Ten players show the pattern for this kind of player, not exact rates for the whole Challenger tour.
* College (NCAA), junior, exhibition and doubles matches are outside the record; several players have college seasons with no professional matches.
* The reference is a snapshot of 23 September 2026; active careers will grow, and two current-week matches in the dump are not yet on it.

## Rerunning

```
./python.sh src/eda/career_coverage/select_players.py     # sample.json (seeded; reproduces the same draw)
./python.sh src/eda/career_coverage/check_transcripts.py  # transcript_check.json
./python.sh src/eda/career_coverage/build_coverage.py     # reference_record.csv, local_rows.csv, coverage.json
./python.sh src/eda/career_coverage/render_report.py      # docs/studies/career_coverage/report.html
./python.sh -m pytest test/career_coverage -q
```

The official-record transcriptions are evidence files, not reproducible downloads: they were read on 23 September 2026 through a web-reading tool because the ATP site refuses plain HTTP clients. Re-reading them later will give a longer record for active players. Rights of each source are unchanged by this study.
