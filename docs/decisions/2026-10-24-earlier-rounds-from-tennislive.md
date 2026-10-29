# A qualifier's earlier rounds come from TennisLive until their source publishes them

**The owner's instruction, 24 October 2026**, on the bet sheet of 19:50 PDT. Of its 21 rows, 16 were qualifying
round-2 matches, blocked because their round 1 was not in the data. Verbatim:

> This is annoying why cant I get this data? we need to get this data.

> Also if you are only patching this as "right now thing" also patch it so this doesnt happen again, and I can
> succesfully and accurately bet these qualifiers a day out when a similar issue happens.

**The design below is Claude's choice** (an agent's choice, in the production-integrity plan's sense). The owner
decided that the data must be got, and that the fix must last.

## Why the data was missing

* **The gate** (decision of 22 Oct, [qualifying bets](2026-10-22-qualifying-bets.md)) blocks a qualifying round 2 or 3
  whose player has no match of the round before in the data. Without that match, the player's inputs miss a result,
  not only a box score.
* **Men:** Tennis My Life's qualifying file lags by days. On 24 Oct its 2026 file had last changed on 23 Oct, with the
  qualifying played on 17-18 Oct. A round 2 the day after its round 1 was therefore always blocked.
* **Women:** Tennis My Life carries no women's qualifying. It reaches the data only through the weekly lower-level feed
  (Wednesdays), after the qualifying is over. Every women's round 2 and 3 was blocked; the morning run of 24 Oct
  blocked 6 of 13 matches for it, the evening run 16 of 22.
* **The data was on disk all along.** The linker (cell A2) reads TennisLive's results of the event to find the round,
  and those list every finished match within minutes.

## Decision

* **A2** (`src/pipeline/live.py`, `src/pipeline/qualifying.py`). For a qualifying match after round 1, each player's
  finished wins at the event before it are taken from TennisLive's results, unless Tennis My Life's rows of the edition
  hold them. Each comes with:
  * its score, written as Tennis My Life writes one;
  * the box score of its TennisLive match page: the eight counts the history's other TennisLive fills use;
  * each side's service games, which the page does not list. They are derived from the score and the match's first
    server; a page without a first server falls back to its "Service games won" line, only when that line agrees with
    the score.

  Pages are fetched paced, with a receipt and a raw copy (the scraping decision of 8 Oct). The rows are written beside
  the matchups CSV, as `<matchups>_earlier.csv`.
* **The run** (`src/eda/prediction_run/earlier_rounds.py`, `run.py`, `inject.py`, `stage0_build.py`). Each row enters
  the run's own tables as a played match of the event: a live row with its result. It is dated like a live match, so
  its result counts for the next round as it would once published.
  * **Live only:** never in the training history.
  * **The source wins:** when Tennis My Life (or the feed) holds the match, its row stands and the fill is dropped.
    When its row is a result without a box score (Tennis My Life posted Vienna's and Basel's round 1 that way at
    about 21:00 PDT on 24 Oct), the row keeps its result and takes TennisLive's box score as a live fill, as the
    WTA API's and the ATP's fills do, when the two agree on the winner and every set's games.
* **The gate is unchanged.**
  * A filled round with a box score is complete.
  * One without a box score (no match page) is treated as any missing qualifying box score: a bet needs a 1-point edge.
  * A round that could not be filled stays blocked, with its reason: an opponent the data does not know, or TennisLive
    not answering.
* **A3b** (`src/pipeline/readiness.py`) reads the same file, so its verdict matches the run's.

## Evidence

* **TennisLive against Tennis My Life**, on last week's men's tour qualifying (Almaty, Brussels, Lyon: 36 matches,
  published by Tennis My Life on 23 Oct):
  * scores equal on 36 of 36;
  * service games, as derived, equal on 36 of 36;
  * the other eight counts equal on 33 of 36. The other three differ by a single point each, all in Brussels round 1.
  * Earlier measurements against the history: 99.6-100% at Slam and Challenger qualifying and every women's level
    ([TennisLive box fill](../studies/tennislive_box_fill/README.md)).
* **The replay proof** ([master pipeline process log](../studies/master_pipeline/process_log.md), Part 14). The 22 Oct
  replay of Almaty and Brussels round 2 (8 matches) had reproduced all 57 inputs bit for bit, with Tennis My Life's
  round 1. It was run again with those 16 rows dropped and filled from TennisLive, as a live run fills them:
  * **5 of 8 matches** are bit for bit on all 36 inputs outside the surface IOS. The other 3 are exactly the Brussels
    matches with the one-point source differences: up to 0.020 on 4 inputs.
  * The surface IOS, solved jointly over all players, absorbs those points: at most 0.004.
  * **The forecast** moves by 0.05 to 0.24 points against Tennis My Life's own data (largest difference over the whole
    price grid, per match; median about 0.1). For comparison, the gate review measured a median 0.35 points for one
    missing box score.
  * The first run of the proof failed on service games, which the filled rows lacked (hold and break inputs off by up
    to 0.28). That is why they are derived.

## Not covered yet

* **Main-draw matches of qualifiers and lucky losers:** their qualifying matches are missing in the same way, a day
  later. In round 1 the inputs silently lack them; from round 2 the gate blocks ("came through qualifying").
  Extending the same fill to them is the next step, with its own replay proof. (Done on 25 Oct 2026: below.)
* **An opponent the data does not know** (a new player, or a women's player only in the weekly feed): that round is
  not filled, and the match stays blocked.
* **When the feed and the fill hold the same women's match,** the run keeps the fill, because the merge skips the
  feed's copy. The two count alike at women's levels.
* **Event ids.** A fill takes the live match's event id, so a round 2 and its filled round 1 are one event, as in
  training.
  * Tennis My Life files a men's qualifying under its main draw's id: 205 of 206 editions of 2025-26 (Shanghai 2026
    used one of its own).
  * The feed files most women's qualifying the same way, but its newest editions (Wuhan, Osaka, Ningbo 2026) carry the
    feed's own ids. Within training, "the same event" is therefore not the same thing for every women's qualifier.
  * Women's qualifying inputs were never replay-proven: the 22 Oct proof was men's, and so is this one.

## 25 Oct 2026: the main draw too

**Still Claude's design (an agent's choice)**, on the owner's second instruction above ("patch it so this doesnt
happen again"). Master pipeline process log, Part 17.

* **Why.** A main-draw match's qualifiers and lucky losers lack their qualifying matches the same way, a day later.
  * In round 1 the gate cannot see it. A live row takes a player's columns from his Tennis My Life row at the event;
    before the main draw is published that row is a qualifying one, whose entry is blank, not Q. So the inputs
    silently lack the qualifying.
  * From round 2 his round-1 row says Q, and the gate blocks while Stage 0 holds none of his qualifying.
* **A2** (`live._qualifiers`, for every linked main-draw match): each player's finished qualifying matches at the
  event, from TennisLive's results, a lucky loser's lost round included, unless Tennis My Life holds them with a box
  score.
  * Tennis My Life's qualifying rows of the edition are found under the main draw's id, else under the event's name in
    the three weeks before its latest row.
  * Each comes with its score and box score as above, best of 3 (a men's Slam qualifying round: as its previous
    edition).
  * The run is unchanged: the same live rows, the same "source wins" rule, the same override for a Tennis My Life row
    without a box score.
* **TennisLive's spellings** (both kinds of fill): an opponent's name that is not a Stage 0 name is read as the one
  Stage 0 player whose name is another spelling of it (`earlier_rounds.same_player`; TennisLive adds given names:
  "Chak Lam Coleman Wong" for "Coleman Wong", "Jodie Anna Burrage" for "Jodie Burrage"). Two or more such players: not
  filled, as before.
* **A3b** lets a qualifier through when his qualifying rounds are in the sidecar.
* **Evidence** (process log, Part 17): a replay of Shanghai 2026's first main-draw day.
  * 14 matches; 7 with a qualifier. Their 14 qualifying matches were taken out of Tennis My Life's data and filled from
    TennisLive: 14 filled, all with box scores, all under Stage 0's own match ids, all 14 scores equal.
  * **The 7 matches without a qualifier come out as in training:** within 4e-8 on every input, 2 exactly.
  * **The 7 with one differ through the data alone.** At Shanghai's qualifying, TennisLive's box scores differ from
    Tennis My Life's on 13 of the 13 matches compared, mostly 1 to 5 fewer first serves in; last week's 250s agreed on
    33 of 36.
  * **The forecast effect, at each match's own price:** mean 0.19 points, at most 0.34. The model itself moves a
    forecast about that much on any change to a match's inputs: TabPFN adds a hash of each row as a feature. The
    matches whose inputs differ only by rounding moved 0.04 to 0.21. So the fill's own effect is about 0.1 to 0.2
    points, a fifth of the 1-point bar at most.
* **Not covered:**
  * **A round-1 qualifier whose round could not be filled** is predicted without it, flagged only in the match's notes
    (the gate cannot see a round-1 qualifier).
  * **A women's main-draw round 1 on its first day is not predicted at all:** Tennis My Life holds no row of the event
    yet, and the linker waits for one (56 such matches on 11-19 Oct). Separate from this fill. **Not to be built for
    now** (the owner, 27 Oct 2026: "dont built predictions for womens rounds 1, we arent betting women yet").
  * **Some match ids are built from a player's Tennis My Life number, not his Stage 0 id** (a quirk of Stage 0 seen in
    the instance's own tables: Mina Hodzic's Tennis My Life match at Athens 2026 is keyed 326113, her id 216095). A
    fill of such a player's match gets such an id: the run's pin cannot find it, so the timeline's own rule dates it,
    and an exact replay cannot hold it (3 of Beijing 2026's 16 women's qualifying rounds).
