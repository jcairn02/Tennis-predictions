# New statistics the 2025–26 closing line may miss: five pre-registered lead groups

13 Oct 2026 · For the owner · A brainstorm, a discovery screen on 2013–2024 and a registered test plan: research evidence, not a decision. Nothing here changes the model or a stake.
* [Pre-registration](preregistration.md) (frozen; its hash is in § 9) · [process log](process_log.md) (the audit trail) · [long list](../../../data/studies/unpriced_leads/longlist.csv) · the team's [memos](team/) and [briefs](briefs/)

## Update, 13 Oct 2026 (evening): the check ran, and passed

**What changed.** The two-look plan below would most likely have given a firm answer only in August 2027. You replaced it with one check now, on every match since January 2025, under [rules written before looking](check_now_rules.md). The plan in plain words is on [this page](next_steps.html).

**The result** (9,457 matches, 2025 to 23 September 2026):
* **On top of the full current model** (TabPFN plus serve speed), the five patterns combined predict winners 3.8 standard errors beyond chance. The pass mark was 1.0.
* **Against the closing odds alone:** 3.85. The closing line did not price these patterns in 2025–26.
* **About 78% of the 2013–24 strength survived.** About 45% was expected.
* **It holds against Pinnacle** (2.6) as well as BetOnline (2.5), and on finished matches only (3.6).
* **Which patterns carry it:**
  * fast courts and big servers (2.0) and rhythm (1.7) most;
  * luck (0.8) and the post-Slam slump (0.7) a little;
  * reputation nothing (−0.3).
  * By the rules all five stay in.

**The adjustment is switched on** in the daily predictions: you switched it on on 13 October ([decision](../../decisions/2026-10-13-five-pattern-adjustment.md)).
* **Every prediction file shows both versions:**
  * the prediction file keeps the model's chance (the one used) and adds the chance without the patterns and with them;
  * the bet sheet shows "Model chance without patterns" and says in Notes when a bet exists only because of the patterns.
* **Size:** about 1 percentage point for a typical match, at most about 5 points.
* **Live numbers match the historical ones exactly** on a replayed day (23 matches).
* **Known live gaps:**
  * short rest needs scheduled start times for upcoming matches;
  * the court-speed part uses ratings data that end at the last model rebuild;
  * the luck and lower-level parts are not built for live use. Luck stays switched off (box scores are still thin). Since the new lower-level feed (14 October), the lower-level part is switched back on and counts as zero until it is built.
* **Update, 16 Oct 2026: the court-speed gap was worse than listed.**
  * The fast-courts pattern was missing for every live match, not just short of an event's newest days. Its ratings came from a file fixed at the 10 Oct model build, and a match not yet played is never in such a file.
  * Fixed the same day: it now reads the ratings each run computes on today's data. Every run checks them against the model's own inputs ([decision, amendment](../../decisions/2026-10-13-five-pattern-adjustment.md)).
  * **Also on 16 Oct, at your word: renamed events are one venue.** The 2026 Shanghai main draw ("Shanghai") had been split from its history ("Shanghai Masters"); 12 such renames are now joined, and moves of city or surface stay apart. This departs from the checked definition at 406 of the check's 9,326 matches, by a median 0.02 points of shift (same amendment).

## 1. The short answer

**What you asked for.** A small team to find statistics that predict results, that the 2025–26 BetOnline and Pinnacle closing line does not price, and that are not in the current best model; a deep brainstorm made into a plan; five lead groups pre-registered now.

**What the team did.**
* Four agents brainstormed and researched independently: rhythm and body, point structure, the betting market, and the literature with data sources. They produced 104 ideas.
* Five statistics agents built and screened them: about 100 new statistics and 340 already-built pool features.
* Every outcome read came from 2013–2024. **No 2025–26 result of any of these statistics was looked at,** so 2025–26 is still an honest test for them.
* Each statistic was also tested on its **new part**: what is left after removing everything the model's own inputs already say about it.

**The five lead groups.** On 2013–2024, each group predicts results beyond the close, the model leaves it unused, and the five are unrelated to each other.

| # | Group | In one line | Why the close may miss it | 2013–24 evidence (new part only) | Data |
|---|---|---|---|---|---|
| 1 | **Luck read as skill** | Recent results that ran ahead of the points: break points, close sets, a flattering last scoreline | Prices follow results and scorelines; this luck does not persist | z +3.9, every era positive | On disk |
| 2 | **The post-Slam letdown** | A Slam quarter-final or better in the last 21 days | Prices credit the Slam run; the next weeks disappoint | z +3.6, every era (women +3.4, men +1.4) | On disk |
| 3 | **Fast courts amplify big servers** | The venue's pace × the ace gap between the players | Prices damp serve dominance and learn a venue's pace slowly | z +3.5, every era (women +4.2, men +1.2) | On disk; weather and altitude can be added |
| 4 | **Status over-priced** | Seeded and famous players do worse than priced; form earned at lower levels or out of view does better | Prices lean on reputation; the line even moves away from lower-level arrivals | z +4.2, every era | On disk |
| 5 | **Rhythm the singles record misses** | Doubles at other events last week; rest under 20 hours; recent load | Prices count singles results and days | z +4.0, every era | On disk; live doubles and schedule feeds for betting |
| | **All five together** | | | **z +8.8** | |

*z: how far the effect sits from zero, in standard errors, on 2013–2024; + means in the expected direction. Every number is of the statistic's new part. These are the best of about 500 screened statistics, so expect them to shrink.*

**The test is registered and waits for your go.**
* **The main test is one combined score of all five groups,** against the close. Each group is tested on its own only once the combined score is confirmed.
* **Look A:** the 2025 season to 28 Jul 2026, 8,591 matches. It can run as soon as you say so, and confirms at a strict one-sided p ≤ 0.02.
* **The final:** Looks A and B combined, read once in August 2027, when the sealed matches from 29 Jul 2026 number about 5,100. It confirms at one-sided 0.03.
* Together the two looks keep the false-confirmation rate at 5%.

**Be ready for "unresolved".**
* **The effects are small:** on 2013–24 the groups move a match's log-odds by 0.03–0.05 per standard deviation.
* **They will shrink.** Across everything screened, statistics keep about 45% of their discovery effect in later seasons.
* **At that rate, the combined score is confirmed by Look A about a quarter of the time, and by the August 2027 final about half the time.** A single group is rarely confirmed on its own.
* The looks still report each score's estimate, its probability of being positive, and how much of the 2013–24 effect survived. That is the evidence the next feature selection weighs.
* This is the size of these effects, not a failure of the idea.

**What we set aside, and why** (§ 4):
* Already priced: other rating systems, long-memory profile variants, shot-level statistics.
* In the model already: the load spike against a player's own normal, which is `sets_14d` again.
* Null: line momentum, each player's record against the close, ranking cliffs, points to defend.
* The draw shadow turned out to be part of the status group.
* Rust: already tested on 2025–26, so it waits for Look B.

**What we need from you** (§ 8):
1. The go for Look A, after reading the pre-registration. Change anything before the go, not after.
2. Acceptance to restore the lower-level data Stage 0 lost (women's ITF qualifying from 2025, every 2026 lower level) as a candidate.
3. A weather source for the conditions extension. It is a licensing choice.
4. Optionally: Pinnacle's 2025–26 closes (paid), the Polymarket recorder, and the ATP point files for serve speeds (approved).

## 2. How the team worked

| Round | Agents | What they produced |
|---|---|---|
| 1 | Rhythm-and-body scout, point-structure analyst, market practitioner, researcher (independent, before any result) | 104 ideas with definitions, mechanisms, data and 2025–26 exposure; about 90 published sources |
| 1 | Pool statistician | The 340 built-but-unused pool features against the close, 2013–24, with placebos and negative controls |
| 2 | Luck, market and rhythm builders (and the lead, for two of the researcher's ideas) | About 100 new statistics, each timing-probed, screened on 2013–24 |
| 2 | Pool rebuilder | The chosen pool features rebuilt on today's tables for every match |
| 3 | Red team | Re-derived every registered number exactly with its own code and found the blinding and timing sound. It found 3 blockers and 5 majors, all fixed before the freeze: two-look error control, what "confirmed" means, Look B's missing data, hash checks, an in-window re-projection, disclosures, a weak member dropped, a retirement reading |

**Discipline** (details in the [process log](process_log.md)):
* **One shared harness reads outcomes.** It reads seasons ≤ 2024 only, inside the file read, and checks it. It reproduces the edge-anatomy study's 2013–24 numbers exactly, and random placebo columns behave as noise.
* **Every new statistic passed a timing probe:** scramble every result after a cut date, rebuild, and confirm that nothing before the cut moves.
* **Nothing is "new" unless its new part counts.** Each statistic is tested as built and as its orthogonal part, what remains after the model's 48 non-price inputs are projected out. Only the orthogonal part is registered.

## 3. The five groups

Each group is one score: the average of its members, each the statistic's new part, scaled and signed. The registered definitions, columns and hashes are in the [pre-registration](preregistration.md) § 3 and the [registry](registry.json).

### 1. Luck read as skill: "returning against serving, and break-point luck"

This is the other analysis's second lead, made into statistics.
* **What it measures.** How far a player's recent results ran ahead of his points.
  * Break points saved and converted beyond what his serve and return points imply.
  * Sets from 5–5 won beyond the odds.
  * Whether his last scoreline flattered him (games share beyond points share).
  * Each against a point-by-point model calibrated once on 2010–12; summed over recent matches with a three-month half-life.
* **Why the close may miss it.** Rankings, results-based ratings and the crowd read luck as skill.
  * Holding a player's point-level skill fixed, the close leans toward the lucky player in every era.
  * The luck does not repeat: a player's luck in half his matches says nothing about the other half.
  * The edge-anatomy study saw this in 2025–26 for men's break-point saving; these statistics are its luck part, beyond anything the model's inputs already say.
* **Evidence.** z +3.9 on 2013–24, positive in every era but weakest in 2023–24 (+0.5): a decay to watch.
* **Retirements carry part of it:** 3.3 on completed matches only. Books settle retirements differently, so the test reports that reading too.
* **One piece reads the other way.** Creating more break-point chances than expected goes with doing *better* than priced. The registered member is the net figure, in which saves and conversions outweigh it.
* **Data:** on disk (box scores at every level).

### 2. The post-Slam letdown

* **What it measures.** The player reached a Grand Slam quarter-final or better in the last 21 days, at another event.
* **Why the close may miss it.** The price credits the Slam run. The next weeks, when the player is tired or flat, disappoint.
  * The model does not use this feature.
  * The line does not move toward it before the close.
* **Evidence.** z +3.6, every era (women +3.4, men +1.4), weaker in 2023–24 (+0.9). It touches only about 2% of matches, so it is a large effect where it applies.
* **Data:** on disk.

### 3. Fast courts amplify big servers

* **What it measures.** The venue's pace times the gap between the two players' ace rates. The pace is estimated only from aces served at earlier editions and earlier days of this edition, without leaking results.
* **Why the close may miss it.** Prices apply a damped serve advantage everywhere and learn a venue's speed slowly.
* **Evidence.** z +3.5, every era (women +4.2, men +1.2).
* **Partial information.** Weather (wind, heat) and altitude would add to it. That part is registered as a separate test that runs once the data is obtained (§ 6; pre-registration H6).

### 4. Status over-priced, low-visibility form under-priced

* **What it measures.**
  * Seeded and famous players (titles and deep Slam runs) do worse than priced.
  * Players arriving from lower levels, or whose recent form was earned out of view, do better.
* **Why the close may miss it.**
  * Prices lean on reputation.
  * Recreational money leans on names: BetOnline's line moves *away* from lower-level arrivals before the close, so the bias grows rather than shrinks.
  * The event-levels study found the lower-level half earlier; this group adds the name half.
* **Evidence.** z +4.2, every era. It is strongest in recent eras for the lower-level members.
* **Data:** on disk, with a gap for women. **Stage 0 holds no women's ITF qualifying from 2025** (16,684 matches in 2024, none in 2025), and every lower level falls away from June 2026.
  * The registered completeness gate switches the two lower-level members off where their inputs collapsed: 69% of Look A's women's matches and 11% of the men's.
  * There the group is seeded and fame alone.
  * Restoring that data would strengthen this group (§ 8).

### 5. Rhythm the singles record misses: "richer rhythm and rust"

This is the other analysis's first lead, made into statistics.
* **What it measures.**
  * Doubles played at other events in the previous week.
  * Rest under 20 hours since the previous match ended.
  * Recent match load beyond the model's set count.
* **Why the close may miss it.**
  * Prices count singles results and days.
  * Doubles live in another feed: the line does not move toward that member, and its signal is strongest where the line is fresh, not stale.
* **Evidence.** z +4.0, every era. The doubles member replicates on a second source (men's 2013–16).
* **Dropped before the freeze:** a bye seed's first match against an opponent who has already played at the venue. It read z +2.6 overall but about 0 since 2020; the line learns it; it is mostly the draw's structure; and it overlaps "seeded" in group 4. It is still reported, as a member-level secondary.
* **Rust,** the other half of that lead, was already tested on 2025–26 (unresolved), so it is registered for the sealed matches only (pre-registration H7).
* **Data:** on disk. For betting, doubles results and the order of play are needed live; the TennisLive collector exists.

## 4. What else was considered

**The long list.** 104 ideas, by area: rhythm and body 30, conditions 17, conversion luck 17, career 13, the market 12, point-level state 8, serve against return 3, other 4. Each idea's fate and, where built, its reading are in [longlist.csv](../../../data/studies/unpriced_leads/longlist.csv).

**Built and screened, not chosen** (2013–24; z of the new part, both tours):

| Idea | Reading | Why not |
|---|---|---|
| Load spike against the player's own normal | raw +3.95, new part −1.09 | It is `sets_14d` again (61% explained by the inputs) |
| Draw shadow (a superstar still in the draw) | its signal is "ranked outside the top 50" | The status group carries it |
| Totals market's late view of the match | +2.3, +1.8 with the price's curve controlled | The model already has it (−0.4 beyond the model) |
| Line momentum (the close finishing its own move) | −1.0 (BetOnline), −0.8 (Pinnacle) | Null |
| Each player's record against the close | does not persist (split-half −0.04) | Noise; prices chase it |
| Ranking cliffs, points to defend | \|z\| ≤ 1.2 | Null |
| Results-rating luck gap (Elo on results minus Elo on points) | new part −0.39 | The close uses it legitimately |
| Qualifier's arrival cost | new part −0.34 | It is the qualifier tag, which the inputs span |
| Style-specific ageing, recent retirements | signs flip between tours | No mechanism survives |

**Pool features with evidence but not chosen:**
* rust after a break (−3.05; already tested on 2025–26, so Look B only);
* women's travel between regions (−2.19, men about 0);
* novelty of conditions (−1.88);
* matches already played at this event (its signal is the bye seed's cold start, in group 5).

**Priced, by the pool scan:** long-memory profile variants (at chance), other rating systems (about 0 once the model's inputs are removed), shot- and point-level statistics including serve speed (0 of 10), load kernels, arrival features (gone by 2023–24), calendar context, height, handedness, head to head.

## 5. The test plan

The [pre-registration](preregistration.md) is binding; this is its summary.

**The question each look asks:** given the closing price, does the group's new part predict who wins?
* **The price:** the model's own odds input, Pinnacle's margin-free close to 7 Sep 2025, then BetOnline's closing line.
* **The fit:** a slope and a curvature term per tour on the price, so that no score borrows the price's favourite–longshot shape.
* **The test:** one-sided, uncertainty over four-week blocks.

| | What | When | Verdict |
|---|---|---|---|
| **Main test** | The combined score of all five groups | Look A: the 2025 season to 28 Jul 2026, 8,591 matches; on your go | confirmed if one-sided p ≤ 0.02 |
| **Each group** | Its own score, only if the main test is confirmed at that look | The same look | confirmed if p ≤ 0.02 after Holm across the five |
| **The final** (only if Look A did not confirm) | Looks A and B combined | Look B: 29 Jul 2026 – 31 Jul 2027, about 5,100 matches, read in August 2027 | confirmed if one-sided p ≤ 0.03; groups the same way, at 0.03 |

**Before anything is fitted,** an outcome-free completeness gate switches off a member wherever its input data collapsed: lower-level matches, box scores, doubles results or start times below 70% of the same months a year earlier. Each member is also re-projected on the look's own matches, so that no score re-finds what the model's inputs already say (the red team's fix).

**Also reported, without verdicts:**
* beyond the close *and* the model's 48 inputs (a confirmation that vanishes there is "re-finding in-model information");
* the raw statistics;
* beyond the model's own forecast;
* men and women;
* the Pinnacle months against the BetOnline months;
* fresh against stale BetOnline lines;
* completed matches only (retirements settle differently at each book);
* Look A before the 2026 data gap;
* whether the line moves toward each score before the close (learned early, or never priced);
* each member;
* the **realisation ratio**: the 2025–26 effect as a share of the 2013–24 effect;
* a probability that each score is positive, with the 45% shrinkage built in.

**Power of the combined score**, by how much of the 2013–24 effect survives:

| Survives | Confirmed at Look A (p ≤ 0.02) | Confirmed by the August 2027 final |
|---|---|---|
| All of it | 87% | 99% |
| Half | 29% | 60% |
| **About 45% (what the data predict)** | **24%** | **52%** |
| A quarter | 9% | 22% |

A single group is confirmed by the final 14–21% of the time at 45%.

**Why two looks.** A single confirmatory Look A at 0.05 would give the combined score 41% now and no confirmatory look later. The registered design gives 24% now and 52% by August 2027, with the error rate held at 5% throughout. If you would rather have one decisive look now, say so before the go: the registration would be re-issued before any result exists.

**On each outcome** (nothing changes the model by itself):
* **Confirmed:** the verdict belongs to the score tested (the five areas together, or one group), never to a member it did not test.
  * The members enter the feature pool as leads, each with its own reading and its group's verdict attached.
  * A group reading contrary is not admitted on the combined score's strength.
  * The next step, your call, is a candidate build (inputs or a nudge like the serve-speed stage), compared on both stages.
* **Unresolved:** they stay leads, and the final reads them again.
* **Contrary:** dropped and recorded.

**Registered beside these, with their own tests:**
* H6: weather and altitude, once the data is obtained.
* H7: rust, on Look B only.
* H8: Polymarket's informed money, prospective only.

## 6. Partial information: what to add, and from where

| Data | For | Route | Cost | Status |
|---|---|---|---|---|
| Hourly weather (wind, wet-bulb heat) and a venue table (coordinates, altitude, time zone) | Group 3's extension: wind × serve, altitude × serve, heat × acclimatisation | Open-Meteo's archive (its free tier is non-commercial; a paid plan exists) or ERA5 from Copernicus (free for any use, needs an account); venues from GeoNames or Wikidata | Free to low | **Your call** (licensing, an account) |
| ATP Stats Centre per-point files, 2025–26 | Serve-speed extensions: second serve, fault speed, the fade within a match | Decrypted as the site's own page does (collection package P9, about 60,000–90,000 requests) | Time | Approved 8 Oct |
| Hawk-Eye Court Vision, 2025–26 | An edition's court pace from ball bounces | The same route; whether 2025–26 files exist is unverified | Time | Approved 8 Oct |
| Live doubles results and orders of play | Group 5 at bet time (doubles, short rest) | The TennisLive collector (exists) and tour schedule pages | A small scraper | Public data, approved |
| Withdrawals with reasons | Health signals | Wikipedia's event pages (CC BY-SA), about 4,000 pages | Time | Public |
| Pinnacle's closes from Aug 2025 | The sharpest 2025–26 benchmark (the edge-anatomy study's recommendation 3) | BettingIsCool (€99 a month) or The Odds API | Paid | **Your call** |
| Polymarket trades from today | The informed-flow lead, prospective only | The existing adapter, once scheduled | Free | Approved; **you or a session you direct** starts it |
| Women's ITF qualifying 2025–26 and every 2026 lower level (WTA 125, women's qualifying, the ITF) | Group 4 (women), Look B, and the women's model inputs | The held WTA API, the Slam feeds, TDI (no ITF source is held) | Time | **Your acceptance**: lower-level history enters only as a candidate under the freeze rules |

## 7. What this does not show

* **No 2025–26 test has run.** Everything here is discovery on 2013–24 plus a plan.
* **The groups are the best of about 500 screened statistics.** Their 2013–24 numbers will shrink; the registration expects it.
* **The market learns.** Some groups weaken in 2023–24: close-set luck and the letdown. If the market has caught up, the realisation ratio will show it.
* **Women after 7 Sep 2025:** the benchmark is BetOnline's line, which for women is much softer than the exchanges. A group may look unpriced there for that reason, so the test reports the Pinnacle and BetOnline periods separately.
* **Data gaps.** Women's ITF qualifying is missing from 2025, and every lower level from June 2026. The gate protects the test, at the cost of group 4's women's power. Start times come from schedules after 17 Apr 2026 (Flashscore's feed ends).
* **What remains possible.** The red team estimates a residual leak of about 0.6 of Look A's standard error at most, from the model's own adjustment toward group 4, which the in-window re-projection reduces.
* **Archived closes, not bets.** No limits or delays.
* **The mechanisms are hypotheses.**

## 8. What we recommend

Accepting any of these is your call.
1. **Read the pre-registration, then give the go for Look A.**
   * It is one read of 8,591 matches nobody has used for these statistics.
   * It answers your question ("is that priced into the very recent closing line?") as directly as the data allow. It costs minutes of CPU.
   * After it, 2025–26 is spent for these statistics. Change anything, including the two-look design, before the go, not after.
2. **Accept restoring the lost lower-level data as a candidate:** women's ITF qualifying from 2025, and the 2026 WTA 125, women's qualifying and ITF matches.
   * Its absence switches off half of group 4 for women, and Look B depends on it.
   * It matters beyond this study: the same history feeds the women's model inputs.
3. **Keep the start-time and doubles feeds running until July 2027,** for Look B. If group 5 is confirmed, wire doubles results and the order of play into the live pipeline before betting it.
4. **Pick a weather source** for H6, the conditions extension.
   * Open-Meteo's archive is free only for non-commercial use (a paid plan exists); ERA5 from Copernicus is free for any use with an account.
   * Either way it is about 3,000–4,000 requests and a venue table, and a day's work once you choose.
5. **Read Look B in August 2027, not early 2027.** The sealed matches number 866 to 23 Sep 2026 and reach about 5,000 only by July 2027, not the "about 5,000, early 2027" of the edge-anatomy study.
   * That study's five in-model leads, if you approve them, should share the same read, with the two registries' error rates stated together.
6. **Pinnacle's 2025–26 closes** (paid) would let both looks be re-read against the sharpest price, especially for women, where BetOnline's line is soft. It is the edge-anatomy study's recommendation 3.
7. **Schedule the Polymarket trade recorder** if you want the informed-flow lead (H8) to start counting.
8. **The serve-speed extensions** (second serve, fault speed, the fade within a match) need the ATP's 2025–26 point files, already approved for decryption. They are a candidate for the next registration, not this one.

## 9. Files

**The freeze (13 Oct 2026, 13:08 PDT):** `preregistration.md` SHA-256 `e8570290356634c7f1cc5e526e24630d719ecda1acea03ea7316077e8ccff635`; `registry.json` `9364008c9058384a50ba7f504554dfd12c35992d8403de2bc899c9922d384a8a`. The pre-registration's § 14 lists the code, values, gate and dry-run hashes. Committing these files fixes them in git history; that step is yours.

| What | Where |
|---|---|
| The pre-registration (frozen) and its registry | [preregistration.md](preregistration.md), [registry.json](registry.json) |
| The audit trail | [process_log.md](process_log.md) |
| The team's memos and briefs | [team/](team/), [briefs/](briefs/) |
| Code | `src/eda/unpriced_leads/` (the harness `screen.py`, the builders, `register.py`, `look.py`) |
| Data | `data/studies/unpriced_leads/` (candidate values and readings, the pool scan, the long list, checks, the registration) |
