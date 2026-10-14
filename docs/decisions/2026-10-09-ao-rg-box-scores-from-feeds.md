# Future Australian Opens and Roland Garros take their box scores from the Slams' own records

**Decided by the owner on 9 October 2026.** Claude recommended: "Take future Australian Open and Roland Garros box scores from the Slams' own feeds: yes, and this matters most for betting. The match data we get for recent and future matches (Tennis My Life) carries both faults at these two Slams." The owner answered: "Execute these 3 fixes".

Recorded the same day by Claude, who carries it out.

## Decision

1. **From the Australian Open 2027 and Roland Garros 2027 on,** every Stage 0 match of each edition takes its whole box score from the Slam's own record once that record is collected after the event. It goes through the Slam override table, as the [Slam decision of 6 Oct](2026-10-06-slam-box-scores.md) did for Wimbledon and the US Open 2026.
   * **The eight counts other than service games** come from the Slam's statistics:
     * Roland Garros: rolandgarros.com's match statistics, which equalled Sackmann's 2019–2021 rows on every shared count;
     * the Australian Open: its Infosys key statistics.
   * **Service games** come from the Slam's Infosys point file: the completed games each player served, tiebreaks not counted. Where the file lacks points, they come from the score's alternation of serve from the proven first server.
   * **One record per match,** all nine counts from it, with the checks of the Roland Garros candidate ([report §§ 8.3 and 9](../studies/rg_first_serve_recount/README.md)):
     * links by both names;
     * the record's own consistency;
     * agreement with its point file where the file holds every point;
     * Stage 0's checks under the score.
2. **These records thereby join "the feeds that fed" the training data** (the frozen-reference rule), for matches played from now on.
   * This decision revises no match of the frozen reference.
   * Roland Garros 2022–2026 and the swapped service games of both Slams are the separate candidate of the [same day](2026-10-09-roland-garros-box-scores.md).
3. **Collection after each event,** under the [download-cadence decision](2026-10-06-download-cadence.md).
   * The daily scheduler now reminds weekly until each record is collected: both Slams' Infosys statistics and point files, and rolandgarros.com's statistics.
   * The Australian Open's own feed stays on the list as before.
4. **During an event** (live prediction runs), the same records replace Tennis My Life's rows for the event's earlier rounds.
   * This is built with the betting pipeline, before the first Australian Open or Roland Garros the project bets on (the download-cadence decision's point 5).
   * 41 of the model's 58 inputs read those rounds' box scores ([prediction-run decision](2026-10-08-prediction-run-box-scores.md)).

## Why

* **Tennis My Life's rows of these two Slams carry both faults** ([report §§ 8.2, 9.2](../studies/rg_first_serve_recount/README.md)):
  * its Roland Garros 2026 men's main draw books second serves as first (64.7% first serves in, against RG's 62.2%);
  * its service games at both Slams copy Sackmann's "winner served first" derivation, in most of the swapped matches the reviewers compared.
* **The Slams' own records are validated.**
  * RG's statistics equal Sackmann's 2019–2021 rows on every shared count.
  * The Australian Open's point record reproduces Sackmann's 2025 first serves on every complete row (731 of 731).
  * Both Slams' point files prove who served first. Court Vision and the hand charts agree in every match they hold.
* **The Australian Open's key statistics are served** like Roland Garros's. The 2026 edition was fetched on 9 Oct 2026.
* **They measure what the training data measured.** Against Sackmann's AO 2026 rows (952 player rows) they agree on:
  * double faults: 100%;
  * serve points: 99.8%;
  * first serves in: 99.6%;
  * points won on each serve: 99.8–99.9%;
  * break points: 99.9%;
  * aces: 98.4%.

  Service games agree in only 84.5%, which is Sackmann's swap fault (`slam_infosys_overrides/AO2026/summary.json`).
* **The builder reproduces the reviewed Roland Garros 2026 overrides** from the key statistics alone: the same 351 matches, all eighteen values equal in 349.

## Where it is implemented

* `src/ingest/scheduled.py`: the reminders, with tests in `test/data_continuity/test_rebuild_and_schedule.py`.
* `src/ingest/point_sources/infosys_slams.py` (`--editions AO<year>,RG<year>`, `--routes`) and `rolandgarros.py --years <year>`: the collection.
* `src/eda/data_continuity/slam_infosys_overrides.py`: an edition's override rows, from its records, with the checks above. It is written to be appended to the decided override table at the next coordinated Stage 0 rebuild, as on 6 Oct.

## Not decided

* **Wimbledon and the US Open after 2026.** The 6 Oct decision's "Making the Slam feeds the routine box-score source for later Slams" stays open for them.
  * When Claude recommended this decision it wrote that they "already work this way"; that holds for their 2026 editions only.
  * Claude recommends the same routine for them: their feeds matched Sackmann's history on every count.
