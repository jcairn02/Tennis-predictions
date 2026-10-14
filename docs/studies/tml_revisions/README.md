# Tennis My Life's corrections: the decision you gave on 11 Oct, recorded, and the four held files, checked and accepted

13 Oct 2026 · For the owner · [Process log](process_log.md) (the audit trail) · [Decision](../../decisions/2026-10-13-tml-lower-level-revisions.md)

## 1. The short answer

**You asked** whether the sessions disagreed about the pipeline's state. They did. Two "standing notes" on every bet
sheet said a decision of yours was still open and that four files were waiting for review. Then you said: "record the
decision and run the check on the four files".

**What was wrong:**
* **Your 11 Oct answer was never written down.** You asked "why aren't we just using the newest data?" about
  Tennis My Life's corrections of old lower-level matches, and agreed not to retrain for them alone. The session you
  told did not record a decision. So the project's rules still said such data could not change by itself, model
  rebuilds would have refused to run, and every later session read the question as open.
* **Two session reports recommended opposite things:** one "accept them", the other "keep bet days on the 8 Oct data".
  The second was written before your answer and never updated.
* **Four Tennis My Life files had been parked since 10 Oct.** Every report said "needs review"; nobody reviewed them.

**What is done now:**
* **The decision is recorded.** Tennis My Life's own corrections of the levels it publishes (men's Challengers, ATP tour
  and Slam qualifying) go into bet-day predictions at once and into the model's training at its next rebuild. There is
  no retrain for them alone. Other sources' lower-level data still needs a test or an accepted feed.
* **The rebuild check now lists these corrections instead of refusing to build.**
* **The four files were checked and accepted.** They are cleanup, not damage (§ 3).
* **The project rules and both session reports now say the same thing.**
* **The bet sheet's two notes:** see § 4.

**What still needs you:** nothing for this decision.

## 2. The decision, in plain words

1. When Tennis My Life corrects a match it published at a level it already supplies (a player's identity, an age, a
   score, a box score), removes a duplicate, or adds a past match it had missed, the change goes in by itself.
2. **Bet days use it at once.** Each bet-day run rebuilds the match history from the day's files, so it already did.
3. **Training uses it at the next rebuild of the model.** Rebuilding for these alone is not worth about four hours and
   75 GB of disk. The one such rebuild is planned tonight (§ 4).
4. **Each rebuild still gets a harm check** against the model in use.
5. **Still tested first:** new sources or new kinds of lower-level data (ITF box scores, women's lower levels, other
   sites), anything Tennis My Life sends at a level it never supplied, and any change to the older matches that come
   from Jeff Sackmann's frozen files.
6. **When the download safety check parks a Tennis My Life file** because rows disappeared, a scratch rebuild lists
   every match it would change. The file goes in only if every change is a cleanup (duplicates, misplaced matches,
   corrected ids or counts) and no main-tour match changes. Otherwise it stays parked and comes to you.

## 3. The four files: what they change

Tennis My Life republished its 2022–2025 Challenger files on 10 Oct. The safety check parked them because rows had
disappeared: 38, 67, 127 and 12. I rebuilt the match history twice in a scratch copy, once with the old files and once
with the new, using the same code. The copy's handling of the files matches the real pipeline's exactly. Then I compared
the two builds match by match.

| What | Matches | Plain meaning |
|---|---:|---|
| Champaign Challenger 2025: duplicate copies removed | 4 | The old file gave some players the wrong ids, so four matches were in the history twice, once under the wrong players |
| Rome (Georgia) Challenger: February 2023 matches that had been filed under July 2022 | 3 | 2 were duplicates of the real 2023 rows and are removed. The third, missing from the other source, moves to its real date, seven months later |
| 2026 Challenger matches under a new label | 8 × 2 | The same matches, the same players, the same statistics. Four players' ids are now matched earlier, so the label differs |
| Rows Tennis My Life itself removed | 139 | Four 2008 events misfiled in the 2024 file, and 15 duplicates. The match-history builder was already dropping them |
| Main-tour matches changed | **0** | |
| Facts changed on any match present in both builds | **0** | |

The match history goes from 873,642 to 873,636 matches. 23 players are touched, and only 15 of the 62,869 matches the
2026 model learns from come after a touched player's first change. The effect on the model is far too small to
measure. The fixes are still right to make: they remove duplicates, and one result that had been dated seven months
too early.

**Accepted at 18:48.** The new versions are in place, the old ones are kept in case this needs undoing, and the files
installed are exactly the versions the check tested.

## 4. When it takes effect, and what is still open

* **Bet days:** the next bet-day run uses the four files' fixes. It already used the 11 Oct corrections.
* **The model's training:** the new-data session plans one coordinated rebuild tonight, about 22:30–23:30, if today's
  lower-level feed passes its harm check. It carries your adopted Roland Garros repair, the new feed and these Tennis
  My Life corrections together, and then gets its own harm check. I told it what changed. It waited for this before
  touching the shared tables.
  * **Update, 13 Oct 21:48:** the shared match history was rebuilt with the Roland Garros repair and these corrections
    (873,437 → 873,636 matches, the same count as my scratch build with the four files). Its rebuild check lists the
    104 Tennis My Life changes as allowed, refuses nothing ("the template may be built"), and finds no other
    lower-level change. The model build on today's tables, which brings them into training, was started next in the
    new-data session.
* **The bet sheet's two notes:**
  * The "your decision is still open" note is gone. A history note now appears only when a lower-level change comes
    from somewhere no decision covers.
  * The download note now names the files held for review. With the four accepted, it should not appear on
    tomorrow's sheets. A sheet remade from today's run will still name the four, since that run used the old copies.
  * The bet-sheet session owns this code. It was busy, so I made the changes, ran its tests, and told it exactly what
    changed.
* **The notebook's morning cell** no longer lists the four as held. It used to count every file in the held folder,
  including ones already accepted.

## 5. What could be wrong

* **The rule decides by where a row came from.** Tennis My Life's rows are allowed; rows from Jeff Sackmann's files
  stay checked. If a Tennis My Life correction ever changes a Sackmann row, through the way the two sources are joined,
  the rebuild check refuses and a person looks. That is the cautious direction. It did not happen with these files.
* **A change to the match-history builder's code that alters Tennis My Life rows also counts as allowed.** It is still
  listed, and the harm check at each rebuild covers it.
* **"Too small to measure"** is an inference from how few training matches are touched, not a measurement. The
  rebuild's harm check is the measurement.

## 6. Files

| What | Where |
|---|---|
| The decision | [docs/decisions/2026-10-13-tml-lower-level-revisions.md](../../decisions/2026-10-13-tml-lower-level-revisions.md) |
| The audit trail | [process_log.md](process_log.md) |
| The check (rerunnable for any future held file) | `src/eda/tml_revisions/held_check.py`; tests `test/tml_revisions/` |
| The check's results | `data/studies/tml_revisions/held_check/`: `summary.json`, `changes.csv` (every changed match), `players_touched.csv`, `cleaning_rules_changed.csv`, `history_A_B.json` |
| The rebuild check | `src/eda/current_best_model/history.py` (`tml_lower`); tests `test/current_best_model/test_history.py` |
| The replaced copies | `data/raw/public_dump/tennis_my_life/superseded/20{22,23,24,25}_challenger.20260922*.csv` |
| The scratch copy | `C:/Users/zerom/tnr_tmlcheck`: deleted at your word on 13 Oct, links first; the shared data folders it linked to were unchanged. `held_check.py setup` makes a new one |

**To rerun the check** on whatever files are held, from the repository root:

```
./python.sh src/eda/tml_revisions/held_check.py setup
./python.sh src/eda/tml_revisions/held_check.py validate
./python.sh src/eda/tml_revisions/held_check.py build A
./python.sh src/eda/tml_revisions/held_check.py stage
./python.sh src/eda/tml_revisions/held_check.py build B
./python.sh src/eda/tml_revisions/held_check.py compare
```
