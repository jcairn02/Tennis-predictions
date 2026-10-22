# The men's serve, return and serve-speed leads: lock in, build, then one check

16 Oct 2026 · For the owner · A follow-up of the [edge-anatomy study](../edge_anatomy/README.md). Diagnostic and exploratory: **nothing in the model, the serve-speed stage, the five-pattern adjustment or the daily predictions changes.**
* [Lock-in](lock_in.md) (frozen 16 Oct, 14:15) · [addendum 1](lock_in_addendum_1.md) (frozen 15:15) · [process log](process_log.md) (the audit trail) · the helpers' [briefs](briefs/) and [memos](team/)

## Update, 22 Oct 2026: where this stands, and what production uses

**Where we are.**
* **Done:** the lock-in and its addendum, frozen on 16 Oct.
* **Waiting on you:** the check's schedule (§ 6, item 1).
* **Not done:** neither steady signal has been admitted to the feature pool, and no candidate has been built.
* **Since 16 Oct:**
  * the unseen men's matches in the newest tables have grown from 416 to 571 (to 12 Oct);
  * free, time-stamped Pinnacle closes from November 2025 were found (TennisExplorer). Once a retrain applies the new closing-line rule, a check reads against Pinnacle's price, the one we bet at. That covers most of § 6, item 4.

**What today's bets use** (the live run of 21 Oct):
* **Second-serve speed: nothing.** The speed stage uses first-serve speed only.
* **Break-point luck: only what the model's own inputs carry.**
  * The model has raw break-point saving among its inputs, and leans the right way, but too little. In 2025–26 save luck still predicts winners beyond production's forecast (z +2.0).
  * The five-pattern adjustment has a luck group, but its monthly data check has switched it off since June. In October, box scores were at 57% of a year earlier for men, against a 70% bar, because the 2026 lower-level box scores are thin. Its member, net break-point luck, is also the weaker version: +0.3 and +1.5 beyond the model's forecast in 2020–24 and 2025–26.

**Should it?** Seen matches only (`production_view.json`):
* **Luck: yes, at a small size.** Break points saved beyond what a man's serve points imply (your definition of 16 Oct) reads +2.1 and +2.0 beyond production's forecast in 2020–24 and 2025–26, after 12 years against Pinnacle's close.
  * **Size:** sized like the five patterns, it moves a typical men's match by about half a point, and the top 5% by about 1.6 points.
  * **Route:** one men's adjustment on top of the model, checked and re-checked monthly like the five patterns. For men it stands in for the switched-off luck group, so luck is never counted twice. It needs the luck values built live, and your go.
* **Second-serve speed: not on its own now.** Beyond production's forecast it reads +1.0 and +1.5, unresolved: about a quarter of a point on a typical match.
  * **Route:** test it as a second term when the speed stage is next refitted.
* **Both are too small for a model comparison to see** (about 0.10 and 0.04 log-loss units per match, against a resolution near 0.35). The sensitive test is the one the five patterns used: a single coefficient beyond the full model.

## 1. The short answer

**Your order is right on one point and should change on another.**
* **Lock in first: yes, done.** The four traits, their directions and the test were frozen on 16 Oct, before any unseen result was read (§ 4).
* **Build the cleaner versions before the check, not after.** Unseen matches can be used once. A check now would spend them and most likely say "unresolved". The cleaner versions would then need a second batch of unseen matches, that is, months more. Built first and locked in beside the four traits, they share one check.

**"Unseen" means every match from 29 July 2026 on, and in practice that is mostly live forward data.**
* 416 men's matches from 29 Jul to 23 Sep 2026 are in the tables today. Their results were read once, on 13 Oct, for the five-pattern check: other statistics, built to be unrelated to these traits. Nobody has looked at these traits on them.
* Nothing from 24 Sep on is in the tables yet. Those matches, and every match still to be played, enter at each table rebuild.

**A check cannot answer before early 2027.** Assume the 2025–26 effect is fully real:
* checked at the end of January 2027 (about 1,050 unseen men's matches), it would confirm 3 times in 4;
* checked now, 1 time in 3.

If it shrinks the way most discoveries do, even August 2027 confirms it only 6 times in 10.

**The cleaner versions split the finding in two** (in-sample: these windows had been seen):

| | What | Since 2013 | 2025–26 |
|---|---|---|---|
| **Old, steady, small** | Break-point and hold **luck**: a man whose recent break-point saving ran ahead of what his serve points imply is over-rated | Leans the expected way in every era (z +3.4 over 2013–24) | Again (+2.7). The model doesn't use it (+2.0 beyond the model's forecast) |
| **New, large, unproven** | **Serving itself over-rated relative to returning**, at the same overall strength | Weak (+0.9) | Strong (+3.4) |
| **Priced** | Overall point-level strength, serve and return together | About 0 | About 0 |

**"Serving over-rated" and "returning under-rated" are one finding.** At a given price, a stronger server is a weaker returner, so the two statements describe the same mispricing: the close gives serving too much weight relative to returning.

**One of the three cleaner versions I suggested on 13 Oct was already in the model.** "Return quality measured against each server's normal level" is exactly how the model's return ratings are built.
* **The new version** asks whether a strong returner gains *more* against big servers than that rating allows. It is real in the points, but the close already prices it (§ 5.3). Dropped.

**Serve speed: the second serve is the steadier signal.**
* **Second serve:** a man whose second serve has sped up beats the close in every era since 2013 (z +2.8 over 2013–24, +1.9 in 2025–26).
* **First serve:** the model's speed stage uses it, and it is strong only in some years.
* **Not worth adding:** the gap between the two serves, the fade within a match and fault speed are unresolved, or have too little data (§ 5.4).

**Three cleaner versions are now locked in beside the four traits** ([addendum](lock_in_addendum_1.md), frozen 15:15):
* luck in the big points;
* serving over returning, at equal strength;
* second-serve speed change.

**What I recommend** (§ 6):
1. **Choose the check's schedule:** three looks in 2027 (after January, May and August), stopping at the first confirmation.
2. **Don't wait for 2027 on the two steady signals.** Luck in the big points and second-serve speed have pointed the same way in every era since 2013. A check can add little to that record before 2028. When you're ready to change the model, they are candidates to build and compare in the usual way.
3. **Wait for the check on the new signal:** serving over-rated relative to returning, which exists only in 2025–26.
4. **Buy Pinnacle's closes from September 2025.**

## 2. What has been seen

| Men's main-tour matches | Who looked | Why | Status for these traits |
|---|---|---|---|
| 2013–2024 | Edge anatomy (each trait by era); unpriced leads (about 500 statistics) | Discovery | Seen |
| 1 Jan 2025 – 28 Jul 2026 (4,394) | Edge anatomy **found the traits here**; unpriced leads' check of 13 Oct (the five patterns) | Discovery | Seen: cannot confirm them |
| 29 Jul – 23 Sep 2026 (416) | Unpriced leads' check of 13 Oct read their results once, for the five-pattern score. That score was built to be unrelated to the model's inputs, these traits among them. Its luck group was switched off there and its speed term was 0 | A different statistic | **Unseen for these traits**, with that disclosure |
| From 24 Sep 2026 | Nobody: not in the tables yet (the 14 Oct rebuild ends on 23 Sep) | — | Unseen |
| Still to be played | — | — | Live forward |

## 3. Why build first, and when a check can answer

**A check uses unseen matches once.** After a look, those matches have been seen for anything related to what was checked. So:

| Order | What happens |
|---|---|
| **Yours:** check the four traits now, then build cleaner versions, then check those | The first check has 416 matches and 3 four-week blocks. It confirms a fully real effect only about 1 time in 3, so most likely it says "unresolved". The cleaner versions then need a fresh set of unseen matches, collected after the first check: another 6–12 months |
| **Recommended:** lock in the four now (done), build the cleaner versions on seen matches, lock them in too, then one check of everything | One set of unseen matches answers both. Building takes days, while the unseen matches accumulate anyway |

**When a check of the four traits can answer.** The combined score's chance of a confirmation, by date (one look, one-sided 5%). Unseen men's matches up to 23 Sep are actual; later ones are projected from the same weeks a year earlier:

| Check at | Unseen men's matches | If the 2025–26 effect is fully real | If 45% survives (typical) | If it falls back to its 2013–24 size (about a quarter) |
|---|---|---|---|---|
| Now | 416 | 32% | 14% | 9% |
| 31 Jan 2027 | about 1,050 | 76% | 28% | 14% |
| 31 May 2027 | about 2,100 | 97% | 48% | 21% |
| 31 Aug 2027 | about 2,900 | 99.6% | 62% | 26% |
| Three looks: Jan, May and Aug 2027 | — | 99% | 46% | 15% |

The three-look plan keeps the overall false-confirmation rate at 5%. It can confirm in February 2027 if the effect is as strong as in 2025–26.

## 4. What is locked in

[The lock-in](lock_in.md), frozen 16 Oct 2026 at 14:15, before any unseen result was read and before the cleaner versions were built:
* **The four traits, men only, with their directions:**
  * **Serving strength** (long memory: holds and break points saved): the stronger server loses to the close more often than it implies.
  * **Break points saved, last two weeks:** the higher saver loses to the close.
  * **Returning strength** (long memory: holding the server's first-serve points and service games down): the stronger returner beats the close.
  * **Serve-speed change** (the 28-day speed memory): the man whose serve sped up beats the close.
* **One combined score** of the first three is the main test; speed has its own test. Each trait on its own is tested only if the combined score is confirmed.
* **The matches:** every men's main-tour match from 29 Jul 2026, at the price of the closing line.
* **The test:** the same one the five-pattern study registered.
* **Left open for you: the schedule.** A look run before you choose it is invalid by the lock-in's own rule.

Where the traits were found (January 2025 – July 2026), the combined score leaned the expected way at z +5.6. Over 2013–24 it was +2.2, about a quarter of the strength per match.

## 5. The cleaner versions

All readings here are on **seen** matches (2013 to 28 Jul 2026): they describe, they don't confirm.

### 5.1 Serving over-rated: is it the serve itself, or luck in the big moments?

Serving strength mixes two things:
* **how often a man wins points on his serve:** skill, and it persists;
* **how well his break points and close games went, beyond what those points imply:** mostly luck. A player's luck in half his matches says nothing about the other half (the other study measured this).

I split the trait into the two and read each against the close. z = the strength of the lean in the expected direction; + means the expected direction:

| | 2013–16 | 2017–19 | 2020–22 | 2023–24 | 2025–26 |
|---|---|---|---|---|---|
| Break points saved beyond what his serve points imply (last 3 months) | +1.4 | +1.1 | +2.5 | +1.7 | +2.6 |
| Holds beyond what his serve points imply (last 3 months) | +2.1 | +0.7 | +3.2 | +0.4 | +2.3 |
| The two together | +2.0 | +1.0 | +3.1 | +1.1 | +2.7 |
| Serving rather than returning, at the point level | −1.0 | +1.8 | +0.5 | +0.5 | +3.4 |
| Overall point-level strength, serve plus return (a control: the close should price it) | +1.0 | −0.5 | +0.2 | −0.6 | −0.1 |

* **The luck part is old and steady.** The close has over-rated the lucky saver in every era since 2013. The model doesn't use it either: beyond the model's own forecast it reads +2.0 in 2020–24 and +2.1 in 2025–26.
* **The serve-itself part is new.** It is strong only in 2025–26.
* **The control behaves:** the close prices overall strength correctly.

**In plain terms:** when one man's recent break-point saving clearly ran ahead of what his serve points imply, the close made him a 48.7% chance and he won 47.3% (2013–24, about 9,100 matches). In 2025–26 it made him 48.3% and he won 45.5% (about 1,370 matches). Measured against the close with its usual favourite tilt removed.

### 5.2 Serving over-rated and returning under-rated are one finding

* **The two traits are nearly unrelated across matches** (correlation 0.06).
* **At a given price they are tied together** (about 0.64). The price already reflects a player's overall strength, so at a fixed price, the man who is stronger on serve must be weaker on return.
* **So read side by side, the data can hardly tell them apart.** Serving takes most of the weight, and returning adds little beyond it.
* **The one-number version** is the balance of serving against returning at the same overall strength: the row "Serving rather than returning" in § 5.1.

### 5.3 Return quality against each server's level

**The model already has the plain version.** Its return ratings are fitted as "the server's normal level, minus how much this returner holds servers down".

**The new version asks a different question:** does a returner gain *more*, or less, against big servers than that rating allows? A helper built it ([memo](team/elasticity_builder.md)).
* **It is real in the points.** A returner's slope against big servers predicts his return points in his next matches. Over 2013–24 the prediction lands at full size.
* **It is weak per player.** A player's slope from half his matches barely predicts the other half (correlation 0.08–0.20), so most of each value is shrunk away.
* **The close prices it.** Against the close it reads about 0 in every window, 2013–24 included, and beyond the model it reads 0 too. Had the close ignored it, the points say it should have read clearly positive.
* **It does not explain 2025–26.** In the 2025–26 points the pattern is absent.

**Verdict: not registered, and not admitted to the feature pool.** The "returners under-rated" finding is the serve-versus-return balance of § 5.2, not a matchup effect.

### 5.4 Serve speed: second serves, the gap, the fade, fault speed

A helper built four extensions from the radar data, with the model's own speed method: the same 28-day memory, and the same correction for each event's radar ([memo](team/speed_builder.md)). z beyond the close, + = the man whose serve sped up (or faded less) beats the close:

| | 2013–16 | 2017–19 | 2020–22 | 2023–24 | 2025–26 |
|---|---|---|---|---|---|
| **Second-serve speed change** | +1.9 | +2.0 | +2.1 | +0.8 | +1.9 |
| First-serve speed change (the model's speed stage) | +0.4 | +1.5 | +4.0 | −0.4 | +3.8 |
| First serve minus second | −1.2 | −0.1 | +0.4 | −0.9 | +0.3 |
| Fade within the previous match | +0.1 | −0.5 | +1.0 | +0.3 | +0.3 |

* **The second serve is the steadier signal.** Read together over 2013–24, it carries most of what the two serves share (z +2.0, against +0.8 for the first serve). The first serve leads only in 2025–26, the window where it was found.
* **The signal is in both serves speeding up together, not in the gap between them.** That fits physical form. It also fits radar quirks the event corrections miss; this reading cannot tell the two apart.
* **The fade within a match is unresolved.** Its data cover mostly the Slams and the 2021–24 tour.
* **Fault speed exists for only 439 seen matches** (Slams, 2025–26): too few to read.
* **Verdict:** second-serve speed is registered (C3). The gap, the fade and fault speed are not.
  * The ATP's per-point files would test the fade and fault speed properly on the tour. They are approved for collection but not yet collected. On these readings, they are a low priority.
* **Found on the way:** the speed history the model's speed stage was built from has no men's 2018 matches. The stage fits from 2019, so production is unaffected.

## 6. What I recommend

Accepting any of these is your call. Nothing here changes production until you say so.

1. **Choose the check's schedule.** It applies to the four traits and the three cleaner versions together.
   * **Recommended: three looks in 2027,** at the first table rebuild after 31 January, 31 May and 31 August. Each is held to a stricter level, and the check stops at the first confirmation, so the overall false-alarm rate stays at 5%. It is the earliest a firm answer can come: February 2027, if the effect is as strong as in 2025–26.
   * **The alternative is one look after August 2027.** It has a little more power if the effect shrinks (62% against 46% for the four traits), but gives no answer before September 2027.
2. **Treat the two steady signals as candidates now, not in 2027.** Luck in the big points and second-serve speed have pointed the same way in every era since 2013, and the model does not fully use them.
   * Luck reads +2.0 beyond the model's own forecast in both 2020–24 and 2025–26. Second-serve speed reads +1.0 and +1.5, unresolved.
   * At their long-run size, a check on unseen matches confirms them only 1 time in 4 to 7 even by the end of 2027. It can add little to a 13-year record.
   * **The step for each, when you give the word, is the usual candidate comparison on both stages:**
     * luck: a men's nudge on top of the model. The five-pattern adjustment's luck group already carries a weaker, net version of it, switched off until its live box scores are wired;
     * second-serve speed: a second term in the serve-speed stage.
   * My recommendation: admit both to the feature pool as leads now.
3. **Wait for the check on the new signal:** serving over-rated relative to returning (the four traits' combined score, and the cleaner balance).
   * It exists only in 2025–26, the window it was found in.
   * The model already leans that way, if timidly: the combined score still reads +4.6 beyond the model's forecast in 2025–26.
   * **If you want to act on it before 2027 anyway,** the least-bad rule follows the five-pattern template:
     * a small men's nudge, sized from its 2013–24 strength (about a quarter of 2025–26's);
     * re-checked monthly on the unseen matches;
     * switched off if they read contrary.
   * I don't recommend it before the first look: its evidence is one window, and that is the window it was found in.
4. **Buy Pinnacle's closes from September 2025** (also the edge-anatomy study's recommendation).
   * These signals strengthened from September 2025, just when the benchmark became BetOnline's line. On the same 2025 matches the two books priced them identically, so this looks like a change over time.
   * Only Pinnacle's later closes can confirm that, and live bets use Pinnacle's price where it exists.
5. **Keep the tables growing.** Unseen matches count only once their results, closing prices and box scores are in the tables, and the current tables stop at 23 Sep 2026. The speed collector already records second serves.
6. **Not admitted to the feature pool:** the returner-against-big-servers statistic (priced), the speed gap, the fade, and fault speed (unresolved, or too little data).

## 7. What this does not show

* **No unseen match has been read** for these traits or their cleaner versions. Every reading in § 5 is on matches that had been seen, mostly where the traits were found.
* **The luck statistics were the best of about 90** the other study screened on 2013–24. Their 2025–26 reading is the first on matches they were not chosen on, though it overlaps with the known two-week break-point finding (correlation 0.5).
* **The cleaner versions' values here** come from tables slightly older than the model's own (correlation 0.996–0.999 with its inputs). The registered versions will be rebuilt on the tables current at the check.
* **The benchmark changed inside the window where the traits were found.** Pinnacle's close was the benchmark to 7 Sep 2025, BetOnline's after.
  * The signals are about twice as strong after the switch. On the same 2025 matches the two books price them alike.
  * The unseen check can use only BetOnline's close, unless Pinnacle's are bought.
* **Many readings were taken.** About 20 candidate statistics were read in 7 windows, two forms and against two bases. The conclusions rest on patterns across eras, steady against new, not on the best single number.
* **The stored speed file has no men's 2018 matches.** The helper filled them in for its readings in § 5.4, without reading results; the model's speed stage fits from 2019, so it is unaffected. My own first-serve readings in the timeline count speed as missing before 2019.
* **The mechanisms are hypotheses:** luck that regresses, a market that weighs serving too much, physical form showing in the radar.

## 8. Files

| What | Where |
|---|---|
| The lock-in and its frozen scales | [lock_in.md](lock_in.md), `data/studies/serve_return_leads/lock_in_scales.json` |
| Addendum 1 (the cleaner versions) and its scales | [lock_in_addendum_1.md](lock_in_addendum_1.md), `data/studies/serve_return_leads/addendum_scales.json` |
| The audit trail | [process_log.md](process_log.md) |
| The helpers' briefs and memos | [briefs/](briefs/), [team/](team/) |
| Code | `src/eda/serve_return_leads/`: `common.py` (the traits, the scores, the guarded loader), `readings.py` (the one way results are read), `timeline.py` and `timeline_clean.py` (when a check can answer), `decompose.py` (§ 5.1–5.2), `plain.py` (the plain tables), `check.py` (the registered check, with its dry run), `addendum_scales.py`, `elasticity.py` (§ 5.3), `speed_ext.py` and `speed_read.py` (§ 5.4) |
| Outputs | `data/studies/serve_return_leads/`: readings, power, robustness (`robustness.csv`, `same_matches_books.csv`), the helpers' folders `elasticity/` and `speed/`, the check's dry run (`checks/dry-run/`) |
