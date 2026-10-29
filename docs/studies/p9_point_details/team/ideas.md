# P9 point details: the ideas agent's memo

28 Oct 2026 · Ideas agent (Claude Opus 5.5), run inside the lead's session `4ad0f090-214d-4b51-b18a-41ad8262b656` · Brief: [02_ideas.md](../briefs/02_ideas.md) · One row per idea: [ideas.csv](ideas.csv)

**Status.** Written after the lead stopped the study at its declared depth rule (the lead's message is quoted in the process notes). Nothing here is registered or scored. No statistic was related to any match result.

Labels: **observed** (read or computed here, file named), **inferred** (my reading), **unknown**.

## In short

* **Eight ideas, ranked by my prior that an edge beyond the close exists** (inferred; the percentages are rough subjective priors that a real gain of at least 0.2 mLL exists on the matches where the statistic exists):
  1. **R1, serve first-strike change** (state, about 12%): a player's recent share of serve points won within 4 shots, against his own norm, adjusted for returners and venues. The rally analogue of the serve-speed change, the one point-level state that replicated.
  2. **R2, return-neutralisation change** (state, about 10%): his recent share of returns put in play, against his own norm, adjusted for servers and venues.
  3. **R3, long-rally luck** (state, about 8%): recent long-rally points won beyond what both players' long-run long-rally strengths imply. A rally member of the luck family, which has replicated.
  4. **R4, within-event long-rally load** (state, about 6%): long rallies played in the last 4 days, decayed, beyond what minutes and points played imply.
  5. **R5, venue rally pace as a price-slope modulator** (context, about 5%): at venues whose rallies run longer than the players' norms imply, the favourite beats the close.
  6. **R6, rally-mix style clash** (trait × matchup, about 3%): how much this opponent and venue shift the mix of rally lengths toward or away from each player's band strengths.
  7. **R7, rally balance at depth** (trait, about 3%): strength in rallies of 5+ shots minus strength in points of 4 shots or fewer, for players with deep histories only.
  8. **R8, net-approach change** (state, about 1%; net play, the brief's secondary).
* **The three I would register, if a later round had the depth:** R1, R2 and R3, with the combined score z(R1) + z(R2) − z(R3) (positive = A beats the close). R1 and R2 rest on the one mechanism type that has replicated for point data: a process measure of how a player is right now, read against his own norm. R3 rests on the luck family, which replicated in every era. They use the densest data (every serve and return point of a covered match), not the thin long-rally win rates.
* **Testable at tour level now?** Computable: R1 to R7, essentially on the 1000s, the half of the 250s and 500s with real rally lengths, and Wimbledon and the US Open. R8 is not computable (a median of 3 flagged matches per player in 22 months). Resolvable at plausible sizes: none.
  * R5 has the widest coverage, because it needs a venue's rally history, not each player's.
  * R1 to R3 would run on roughly 1,500–2,000 tour-level matches in 2025–26 (inferred, not counted). On that many matches, an effect as large as the serve-speed change (0.09 log-odds per SD) would read only about z 1.8. Rally effects are likely smaller.

## 1. What the closures leave open

From the reports the brief named (read 28 Oct 2026):
* **Traits are closed.** Rally length, endings, net play and the other style rates add nothing to the close ([shot level, Stage 2](../../shot_level/stage2.md)). Momentum, streaks, leverage and tempo are closed as traits at full depth ([point sequence § 6](../../point_sequence/README.md)).
* **The noisy traits are data-limited, not closed.** Quick points won on serve and on return, long-rally points won and net points won pass only 15–34% of a player's true value into the pre-match feature. The real results cannot rule out edges up to 1–2 mLL in them ([Stage 3](../../shot_level/stage3.md), parts C and the reading).
* **States remain.** The men's serve-speed change replicated: +0.090 [+0.017, +0.162] log-odds per SD given the model ([point sequence § 5.6](../../point_sequence/README.md)). Second-serve speed is the steadier member ([serve and return leads § 5.4](../../serve_return_leads/README.md)).
* **No rally measure was ever built as a change against the player's own normal** ([point-shot ideas, item 1](../../../research/point-shot-ideas/README.md)). Stage 2's only change feature was `spd1_change`.
* **Load.** Sets in 14 days is a model input. The minutes kernels (U-139, U-152), past fatigue (U-143), minutes over 7 and 14 days (U-156) and the previous match's length (U-157) were built and tied or were small given the price ([feature universe](../../feature_universe/README.md), `universe.csv`). Shots and long rallies as load were proposed once, as E4 "intensity-weighted load", and parked at 47/100 without being built (`data/studies/point_sequence/debate/3_audit_round2.md`).
* **The closest closed relatives:**
  * rally recovery (the point after a long rally) was rejected at 39/100 in the same debate;
  * a returner's extra gain against big servers is real in the points, but the close prices it ([serve and return leads § 5.3](../../serve_return_leads/README.md));
  * fast courts × big servers (venue pace from aces × the ace gap) is pattern 3 of the production adjustment ([unpriced leads](../../unpriced_leads/README.md)).

## 2. The data the ideas must live with

* **Observed (the builder, relayed by the lead on 28 Oct):**
  * real rally lengths exist in 4,330 of P9's 25,004 matches: nearly all 1000s, about half the 250s and 500s, and 566 Challenger main draws, mostly 2026;
  * the "rally length known" flag is junk outside tracked matches;
  * P9 raises the median player-match's 52-week rally history 1.07 times (1.39 at tour-level main draws), below the 1.5 stopping rule;
  * real net flags exist at 24 events.
* **Observed** (`src/eda/p9_point_details/ideas_coverage.py`, second run, printed only). Its criterion is "a shot count of 1–60 on at least half the match's points", slightly looser than the builder's:

  | | Share of matches with real rally lengths |
  |---|---|
  | 1000s main / qualifying | 99% / 93% |
  | 250s main / qualifying | 48% / 49% |
  | 500s main / qualifying | 44% / 45% |
  | Challengers main / qualifying | 6% / 7% |

  * Of later-round player-rows at an event, the previous round there is also covered for 97% at the 1000s, 46% at the 250s, 43% at the 500s and 4% at Challengers.
  * At partly covered 250s and 500s, coverage leans to the busiest court (34% and 12% there, against 0–24% elsewhere). So which players have data is not random.
  * Rally mix at the 1000s, from the rally files' "category" (2.4% unclassified): ended on the serve 12.5%, on the return 20.2%, at shots 3–4 27.2%, 5–8 24.9%, 9+ 12.8%.
  * A covered 1000s match has a median of 124 points with a real rally length. Its mean rally (the older count) has a median of 4.3 shots and a spread of 0.76 across matches.
  * Net flags: 1,072 matches, 335 players, a median of 3 flagged matches per player (148 players with 5 or more).
* **Observed (inline check, not saved).** At Challengers, 53–56% of points flagged "known" carry a shot count of 0, which agrees with the builder's finding.
* **Other histories** (shared context): the Slam feeds (Wimbledon and the US Open fully), the ATP handoff (2018 to early 2025), SirGenkii (Dec 2024 – Apr 2025), TDI (June – Sept 2026), the volunteer charts.

## 3. Conventions used by every idea

* **Rally length:** the shot-level convention. The serve is shot 1 and the ending shot counts: an ace is 1, a double fault 0, a missed return 2. Only points the builder marks as real count.
* **Bands:** 1–2 (decided by the serve or the return), 3–4 (serve plus one, return plus one), 5–8, 9+. These match the shot-level study's quick points (4 or fewer) and long rallies (9+), and the ATP's public 0–4 / 5–8 / 9+ split.
* **As of match m:**
  * a player's own earlier matches count only when they surely finished before m could start (`lf + 1 ≤ es`, `data/studies/match_timing/timing.parquet`);
  * opponent, returner, server and venue norms combine other players' matches, so they use the same clock and must pass `src/eda/match_timing/probe.py`.
* **Shrinkage:** empirical Bayes. K = the statistic's per-unit sampling variance divided by its between-unit variance, estimated on 2018–2024 rows without reading any result. Where Stage 1 has K for the same statistic (men), its value is the default.
* **Venue norm:** the event's excess over the two players' norms, from earlier editions (weight halved per year back) and earlier days of this edition, shrunk toward the surface's norm with K from the spread between editions.

## 4. The ideas

### R1. Serve first-strike change (rank 1; state)

* **Definition.**
  * **Per earlier covered match j of player i:** n = i's serve points with a real rally length, double faults excluded; k = those i won within 4 shots (ace, unreturned serve, a serve-plus-one winner or forced error).
  * **Adjusted:** e_j = logit((k + 0.5)/(n + 1)) − (surface norm + returner's norm + venue norm). The returner's norm is how often servers won quickly against him in his 52 weeks before j, shrunk.
  * **As of m:** the n-weighted mean of e over the 28 days before m (stage 2's speed memory), minus the n-weighted mean over days 29–364. The 28-day mean is shrunk toward the longer one by N₂₈/(N₂₈ + K). With no covered match in 28 days, the value is 0, with a missing flag.
  * **Variant:** "ended within 4 shots", whoever won: a pure process measure, closer to speed's nature.
* **Encoding:** A − B, standardised.
* **Direction:** positive. A player whose recent first-strike serving runs above his own norm wins more often than the close implies.
* **Mechanism.**
  * It measures how the serve and the first ball are working right now, with every serve point of a match, not just the result.
  * Under consecutive-day fatigue, serve speed held but serve accuracy fell [3], and second-serve win rates fell after day 1 [4]. A rally-based serve measure can see placement and the first ball, which a radar misses.
  * The close prices results and reputation. The serve-speed change, the same kind of state, replicated given both the model and the close.
* **Not closed:** no rally measure was ever built as a change against the player's norm (§ 1). Quick points won on serve was tested only as a long-run level.
* **Coverage (realistic):** tour-level matches where both players had a covered match in the last 28 days and a 52-week norm. These are mostly the 1000s and the weeks around them, plus the covered 250s and 500s and two Slams. Challengers: almost none.
* **Testable at tour level:** computable on roughly 1,500–2,000 matches in 2025–26 (inferred); low power.
* **How it could be wrong:**
  * it may be a noisy copy of the speed stage (`spd_L`), whose radar events overlap the covered ones, or of the model's two-week box-score forms (aces, first-serve points won);
  * venue confounds (balls, altitude, weather) survive a venue norm built from only a few earlier days;
  * a 28-day window spanning a surface switch mixes norms;
  * rally counts from different tracking set-ups may differ by event.
* **Literature:** [3], [4], [7]; project: [point sequence § 5.6](../../point_sequence/README.md), [serve and return leads § 5.4](../../serve_return_leads/README.md).

### R2. Return-neutralisation change (rank 2; state)

* **Definition.**
  * **Per earlier covered match j:** n = the opponent's serve points with a real rally length, double faults excluded; k = returns i put in play (rally length 3 or more, or a return winner).
  * **Adjusted:** logit residual − (surface norm + server's unreturned-serve norm + venue norm).
  * **As of m:** the same 28-day minus days 29–364 contrast as R1, with the same shrinkage and missing rule.
* **Encoding:** A − B, standardised.
* **Direction:** positive. A rise in returns put in play, against his norm and the servers faced, means A beats the close.
* **Mechanism.**
  * Returning is reaction, first step and footwork. Under consecutive-day load, sprint and jump fell on days 2–4 [3] and stretched returns rose [4].
  * The box score holds return outcomes, not whether the return came back.
  * The 2025–26 close under-rated returning relative to serving ([serve and return leads](../../serve_return_leads/README.md), seen data).
* **Not closed:** returns in play was built only as a trait (split-half 0.86–0.91, Stage 1). It was never built as a change.
* **Coverage and testability:** as R1 (about 80 return points per match).
* **How it could be wrong:**
  * big servers drive most of the variation, so the server norm carries the weight;
  * its 2025–26 reading is not independent of the seen "returning under-rated" finding;
  * it may proxy the model's return forms.
* **Literature:** [3], [4]; project as above.

### R3. Long-rally luck (rank 3; state)

* **Definition.**
  * **Per earlier covered match j:** N = points of 9+ shots (either server); W = those i won.
  * **Expected:** E = N × expit(λᵢ − λₒ). λ is each player's long-rally strength as of j: the logit of his career share of long-rally points won, opponent-adjusted in one pass, shrunk with K ≈ 152 long-rally points (Stage 1, men).
  * **Luck in j:** D = W − E, in points.
  * **As of m:** L = Σ 2^(−age/28 d) × D over matches in the 16 weeks before m.
* **Encoding:** A − B, in points.
* **Direction:** negative. A player whose recent long rallies went his way beyond his skill loses to the close.
* **Mechanism.**
  * Per point, a long rally carries far less player-specific signal than a quick point: Stage 1's men's K is 152 for 9+ against 41–44 for quick points.
  * So results built on recent long-rally wins are disproportionately luck. Prices follow results; the luck family (break points saved beyond serve points) leans this way in every era and held in the 2025–26 check.
  * Long rallies leave almost no after-effect on the next point [6], consistent with their outcome not carrying.
* **Not closed:** long-rally points won was tested as a level (a trait, which predicts the opposite sign) and scored −0.04 given the odds. The luck form was never built.
* **Coverage and testability:** as R1, but with a 16-week window, so somewhat wider. Tour level only.
* **How it could be wrong:**
  * long-rally wins partly reflect a physical state that persists for weeks, which would flip the sign;
  * the model's two-week points-won forms already absorb part of it;
  * the long-run λ is itself noisy, so D carries real change in skill too;
  * the effect on results is small: about 16 long rallies per 1000s match.
* **Literature:** [6], [10]; project: [unpriced leads, group 1](../../unpriced_leads/README.md), [serve and return leads § 5.1](../../serve_return_leads/README.md), [shot level, Stage 1](../../shot_level/stage1.md).

### R4. Within-event long-rally load (rank 4; state; the brief's rally-load state)

* **Definition.**
  * **Load:** LR = Σ exp(−Δ/2 days) × N9 over i's singles matches whose latest finish is at most 4 days before m's earliest start. Δ is that gap in days, and N9 is the match's points of 9+ shots.
  * Defined only when every match in the window has real rally lengths. Otherwise it is missing, never imputed, because imputation would turn it back into a style.
  * **Beyond minutes:** X = log(1 + LR) − f(log(1 + MIN), log(1 + PTS)). MIN and PTS are the same kernel on minutes and points played. f is a least-squares fit on 2018–2024 player-match rows with fully covered windows (outcome-free).
  * **Variants:** total shots in place of 9+ rallies; X × [rest under 30 hours]; X × the expected long-rally demand of match m (both players' long-point shares and the venue).
* **Encoding:** A − B.
* **Direction:** negative. More long-rally load beyond minutes means A loses to the close.
* **Mechanism.**
  * Blood lactate rises with strokes per rally (r = 0.43) and rally duration (0.51) [1]. The same was reported for professional men [2].
  * Back-to-back long days cut sprint and jump, raise muscle-damage markers [3], and raise errors [4].
  * The market sees sets, the scoreline and perhaps the duration, not the rally composition: two matches of equal minutes can differ greatly in long rallies.
* **Not closed:** E4 was parked, never built. Minutes, sets and the fatigue kernels were tested; shots and long rallies were not.
* **Coverage (realistic):** later-round matches whose previous rounds are covered: 97% of such player-rows at the 1000s, 46% at the 250s, 43% at the 500s, 4% at Challengers (observed, above). First-round matches have no load unless a previous event ended within 4 days.
* **Testable at tour level:** computable on about the 1000s' later rounds plus covered 250s and 500s, perhaps 1,000 matches in 2025–26 (inferred). Too few for plausible effects.
* **How it could be wrong:**
  * minutes absorb most of it, leaving a residual of little variance;
  * survival: only winners carry load;
  * long rallies mark close matches against tough opponents, which the market sees;
  * the market may over-react to long matches, which would flip the sign;
  * heat and slow conditions drive long rallies;
  * missingness follows the show courts.
  * Reid and Duffield note that causal links from physiological decline to outcomes are missing [5]. In football, running workload did not support a profitable betting strategy [12].
* **Literature:** [1], [2], [3], [4], [5], [12], [13]; project: point-sequence debate E4.

### R5. Venue rally pace as a price-slope modulator (rank 5; symmetric context)

* **Definition.**
  * **Pace:** V = the venue's shrunk mean, over points at its earlier editions and earlier days of this edition, of the rally length minus its expectation from the server's and returner's 52-week rally-length norms (log-linear, as of each point's match).
  * **Scored as:** logit q = a + b·logit p + c·V·logit p, per tour level, with p the price.
  * **Variant, the rally analogue of pattern 3:** −V × (FS_A − FS_B). FS is the 52-week share of own serve points won within 4 shots.
* **Encoding:** a symmetric price-slope modulator. The variant is an A − B pair term.
* **Direction:** c > 0. Where rallies run longer than the players' norms imply, the favourite beats the close; where they run shorter, the underdog does.
* **Mechanism.** Prices adjust for the surface, but learn a venue's own pace slowly (pattern 3's mechanism). Slower conditions mean fewer serve-decided points and tie-breaks, so skill shows more. Rally length measures pace on every shot, not just through aces, which depend on who served.
* **Not closed:** venue pace exists only from aces (U-192, pattern 3). A rally-length pace was never built. Whether pace × price was tried in the price-slope family (f10) is unknown.
* **Coverage (realistic):** the widest of the eight, because it needs venue history, not player depth. That means every 1000s match, the fully covered 250s and 500s (27 and 13 events), and Wimbledon and the US Open, with earlier editions from the ATP handoff (2018 to early 2025) and P9. Inferred: most tour-level main draws outside partly covered events.
* **Testable at tour level:** the most testable.
* **How it could be wrong:**
  * it may re-find pattern 3, which is in production and was checked on 2025–26, so a test needs pattern 3's term as a control;
  * the price's own favourite–longshot curve must be fitted first;
  * the venue's norm from a few early days is noisy.
* **Literature:** [14] (the 0–4 shot share, as context); project: [unpriced leads, group 3](../../unpriced_leads/README.md), U-192.

### R6. Rally-mix style clash (rank 6; trait × matchup; the brief's style clash)

* **Definition.**
  * **Per player:** 52-week, opponent-adjusted, shrunk band edges on serve, σ(b), and on return, ρ(b), for b ∈ {≤4, 5–8, 9+}. Also band-mix tendencies on serve, πˢ(b), and on return, πʳ(b), from point lengths only.
  * **Mix on A's serve in this match:** π_AB(b) ∝ πˢ_A(b) · πʳ_B(b) / π̄(b) × the venue's term.
  * **Clash on A's serve:** Δ_A = Σ_b [π_AB(b) − πˢ_A(b)] · expit(μ_b + σ_A(b) − ρ_B(b)). This is how much this opponent and venue move A's serve-point chance through the mix alone. Δ_B is the same with the roles swapped.
* **Encoding:** Δ_A − Δ_B (A − B, in point-probability units).
* **Direction:** positive. When the mix this matchup produces favours A's band strengths, A beats the close.
* **Mechanism.** Ratings and prices carry one serve and one return strength per player and surface. A grinder who drags a first-strike server into long rallies changes the point mix itself, which a scalar strength cannot represent.
* **Not closed:** finer matchups were listed as not tested (Stage 3). Boosting on 102 inputs a side found nothing, but with wide intervals.
* **Coverage:** tour-level matches where both players have 52-week band profiles (inferred: mostly players who play the 1000s); Challengers almost none.
* **Testable at tour level:** computable, very low power. The 9+ edges pass little of the truth.
* **How it could be wrong:**
  * the closest test, the returner's elasticity against big servers, was priced by the close;
  * the noisy band edges dominate;
  * it overlaps pattern 3 through the venue term and the IOS profiles through the edges.
* **Literature:** [14]; project: [shot level, Stage 3](../../shot_level/stage3.md), [serve and return leads § 5.3](../../serve_return_leads/README.md).

### R7. Rally balance at depth (rank 7; trait; the brief's noisy traits re-specified)

* **Definition.**
  * B = (the opponent-adjusted logit edge in points of 5+ shots, serve and return pooled) − (the edge in points of 4 shots or fewer, pooled), over 52 weeks.
  * Each part is shrunk with Stage 1's K (158 and 41–44, men).
  * Defined only for players with at least 1,000 real-rally points in the 52 weeks. That is Stage 3's deepest quarter, where the features reach a squared correlation of 0.50–0.60 with the truth.
* **Encoding:** A − B.
* **Direction:** positive. A player relatively stronger in rallies than in first-strike points beats the close.
* **Mechanism.** In 2025–26, the close gave serving too much weight relative to returning at equal strength ([serve and return leads](../../serve_return_leads/README.md), seen data). First-strike points are where serving shows. B is that balance measured on rally length.
* **Not closed:** the separate noisy traits were data-limited (up to 1–2 mLL could hide). The balance form was never built.
* **Coverage:** the deepest players only (inferred: the top 60–100 men, at the 1000s); Challengers none.
* **Testable at tour level:** computable on few matches. Its 2025–26 reading is not independent of the serve-over-returning lead, which was found in that window.
* **How it could be wrong:** it is a proxy of that lead; style traits have never beaten the close here; the 5+ edges are noisy.
* **Literature:** [9]; project: [shot level, Stage 3](../../shot_level/stage3.md) (the depth table).

### R8. Net-approach change (rank 8; state; net play, secondary)

* **Definition.**
  * a = net approaches per point played (serve and return), flagged events only.
  * The 28-day mean minus the 52-week mean, surface-adjusted, shrunk with Stage 1's K (52 points, men).
* **Encoding:** A − B.
* **Direction:** negative, with low confidence. Coming forward more than usual is read as shortening points to cope with fatigue: fatigued players moved less [3], and players change tactics to offset declining function [5].
* **Not closed:** net approaches and net points won were closed as traits. A change was never built.
* **Coverage:** 24 events; a median of 3 flagged matches per player in 22 months (observed).
* **Testable at tour level:** no.
* **How it could be wrong:** grass and conditions drive net play; the direction could equally be confidence.
* **Literature:** [3], [5].

## 5. Ranking and what to register

| Rank | Idea | Kind | Prior (inferred) | Computable at tour level | Resolvable now |
|---|---|---|---|---|---|
| 1 | R1 serve first-strike change | state | ~12% | yes, ~1,500–2,000 matches | no |
| 2 | R2 return-neutralisation change | state | ~10% | yes, as R1 | no |
| 3 | R3 long-rally luck | state | ~8% | yes, somewhat wider | no |
| 4 | R4 within-event long-rally load | state | ~6% | yes, ~1,000 matches | no |
| 5 | R5 venue rally pace × price | context | ~5% | yes, widest | no; needs pattern 3 as a control |
| 6 | R6 rally-mix style clash | matchup | ~3% | yes | no |
| 7 | R7 rally balance at depth | trait | ~3% | few matches | no; not independent of a seen lead |
| 8 | R8 net-approach change | state | ~1% | no | no |

* **Register R1, R2 and R3 with the combined score z(R1) + z(R2) − z(R3)**, if a future round has the depth. Why these:
  * they are states, the only kind of point statistic that has replicated;
  * two of them use every serve or return point of a covered match, so they are the least data-hungry;
  * R3 brings the one market-bias mechanism with a record in every era.
* **The rally-load state (R4)** is the brief's required idea and has the strongest physiology. It ranks fourth because the market sees match length, and the project's minutes and sets features already tie given the price.
* **What would make them testable** (inferred): rally lengths on most tour-level and Challenger matches. Candidates are counting shots from Court Vision's per-stroke tracking, where it exists beyond P9's tracked matches, and TDI's forward capture. That is the lead's call.

## 6. Literature (all accessed 28 Oct 2026)

How each was read: **full** = the full text or a summary of it; **abstract**; **snippet** = a search-result excerpt only.

1. Fernandez-Fernandez J, Mendez-Villanueva A, Fernandez-Garcia B, Terrados N (2007). Match activity and physiological responses during a junior female singles tennis tournament. *Br J Sports Med* 41(11):711–716, doi:10.1136/bjsm.2007.036210. https://pmc.ncbi.nlm.nih.gov/articles/PMC2465267 (full).
   * Lactate against strokes per rally: r 0.43; against rally duration: 0.51. Heart rate against strokes per rally: 0.38.
   * Eight players; game-level correlations.
2. Mendez-Villanueva A et al. (2007). *Br J Sports Med* 41(5):296. https://bjsm.bmj.com/content/41/5/296 (snippet).
   * Eight internationally ranked men on outdoor clay; longer rallies and more strokes per rally went with higher lactate, as cited in [1].
   * The title was not seen on the page.
3. Gescheit DT, Cormack SJ, Reid M, Duffield R (2015). Consecutive days of prolonged tennis match play: performance, physical, and perceptual responses in trained players. *Int J Sports Physiol Perform* 10(7):913–920, doi:10.1123/ijspp.2014-0329. https://opus.lib.uts.edu.au/handle/10453/118907 (abstract).
   * Seven men, 4-hour matches on 4 days.
   * Serve speed held; post-match serve accuracy fell.
   * Sprint fell on days 2–4 after play, and jump before play.
   * Players moved less; muscle-damage markers and soreness rose daily.
4. Gescheit DT, Duffield R, Skein M, Brydon N, Cormack SJ, Reid M (2017). Effects of consecutive days of match play on technical performance in tennis. *J Sports Sci* 35(20):1988–1994, doi:10.1080/02640414.2016.1244352. https://opus.lib.uts.edu.au/handle/10453/114778 (abstract).
   * More stretch groundstrokes and returns; relative unforced errors up on day 4 against day 2.
   * Second-serve win rate down after day 1; effective playing time down on days 3–4.
5. Reid M, Duffield R (2014). The development of fatigue during match-play tennis. *Br J Sports Med* 48(Suppl 1), doi:10.1136/bjsports-2013-093196. https://opus.lib.uts.edu.au/handle/10453/34239 (abstract).
   * Evidence on fatigue within and between matches is lacking, and causal links to outcomes are missing.
   * Players adapt their tactics to declining function.
6. Tennis Abstract (10 Sep 2015). The effects (and maybe even momentum) of a long rally. https://www.tennisabstract.com/blog/2015/09/10/the-effects-and-maybe-even-momentum-of-a-long-rally/, read through https://www.tennisabstract.com/blog/wp-json/wp/v2/posts/1830 (full; author not named in the feed).
   * Match Charting Project, about 1,100 matches, the longest 1% of points.
   * The next point is shorter (men 4.03 against 4.64 shots), and the after-effect lasts about one point.
7. Tennis Abstract (5 Oct 2015). The slow but steady erosion of the server's advantage. https://www.tennisabstract.com/blog/2015/10/05/the-slow-but-steady-erosion-of-the-servers-advantage/, read through `…/wp/v2/posts/1872` (full).
   * Holds are about 2% less likely by game 12 and about 5% by game 25.
   * Fatigue is offered as one explanation, not measured.
8. Kovalchik SA, Reid M (2017). Comparing matchplay characteristics and physical demands of junior and professional tennis athletes in the era of big data. *J Sports Sci Med* 16:489–497. https://www.jssm.org/jssm-16-489.xml-abst (snippet). Professionals carry more match volume. Not used for any claim.
9. Wilkens S (2021). Sports prediction and betting models in the machine learning age: the case of tennis. *J Sports Analytics*, doi:10.3233/JSA-200463. https://journals.sagepub.com/doi/10.3233/JSA-200463 (snippet).
   * No learner beat forecasts from betting odds, and the odds were the most informative input.
   * The author is inferred from citing papers.
10. Lyócsa Š, Výrost T (2018). *Applied Economics*. https://muni.cz/en/research/publications/1397002 (snippet). Correcting for data snooping across 40 tennis betting rules shrinks their apparent profits. Title not seen.
11. Lobão J et al. (2015). Another look at the efficiency of markets: the case of the tennis betting exchanges. *RAE* 55(4). https://periodicos.fgv.br/rae/article/view/52958 (snippet). Betfair data; some strategies look profitable.
12. Soebbing BP et al. (2021). *J Sports Economics* 22(3):231–250. https://ideas.repec.org/a/sae/jospec/v22y2021i3p231-250.html (snippet). Football running workloads against betting-market probabilities: no profitable strategy.
13. Ashman T, Bowman RA, Lambrinos J (2010). *J Sports Economics* 11(6):602–613. https://ideas.repec.org/a/sae/jospec/v11y2010i6p602-613.html (snippet). Do NBA point spreads price fatigue? The answer was not seen.
14. O'Shannessy C. "The Magic Number One", tennisplayer.net (members' page). https://www.tennisplayer.net/members/strategy/craig_o_shannessy/the_magic_number_one (snippet). Rally bands 0–4 / 5–8 / 9+; "70% of all points at the Australian Open were 0–4 shots" (year not given).

## 7. Process notes

**Order of work** (28 Oct 2026, local time UTC−7).

1. **Read:**
   * briefs 02 and 00, then the builder's and harness's briefs, and the study's process log;
   * shot level: README, Stages 1–3;
   * point sequence: README, §§ 1–6;
   * the point-shot ideas list;
   * the serve and return leads README;
   * the unpriced leads README;
   * the feature universe: its header, the load-and-schedule and shot-and-point families, § 9, and the `universe.csv` rows U-137–U-215;
   * the point-sequence debate's ideas round 1 (B6, E4) and audit round 2 (the scores).
   * No other study's result table was opened.
2. **The gate's profile:** `field_profile.json` and `field_profile_events.csv`.
3. **`ideas_coverage.py`, first run (09:01).** It had two bugs:
   * the rally files' "10+ even shots" fell outside the 9+ band;
   * coverage was counted from the "known" flag.

   Its classification by court names failed, because `court_name` is empty in this copy.
4. **Inline checks (not saved):**
   * court numbers;
   * at Challengers, 53–56% of flagged points carry a count of 0 (the old and new counts alike);
   * real coverage by level and year: 1000s 96–98%; 250s 45–49%; 500s 34% (2025) and 55% (2026); Challengers 2% (2025) and 11% (2026).
5. **Searches (WebSearch, standard mode), nine queries:**
   * consecutive-day match play (Gescheit);
   * rally length and lactate (Fernandez-Fernandez, Mendez-Villanueva);
   * Kovalchik and Reid, big data;
   * betting-market efficiency and fatigue;
   * O'Shannessy and 0–4 shot rallies, twice: the first returned only motorsport and quiz shows, the second only snippets;
   * Kovalchik's "GOAT" paper;
   * Wilkens 2021;
   * Tennis Abstract on fatigue.
6. **Fetches (WebFetch):** PMC2465267; UTS 118907, 114778 and 34239; Tennis Abstract's API, posts 1830 and 1872; the SUU working paper (below).
7. **The lead's message** arrived during literature work (verbatim):

   > "Lead here: the study stops at its declared depth rule, so nothing will be pre-registered or scored this round. The builder found that P9 raises the median player-match's 52-week rally-length history only 1.07 times (tour-level main draws 1.39). The reason is that P9's "rally length known" flag is junk outside tracked matches. Real rally lengths exist in only 4,330 of its 25,004 matches: nearly all 1000s, about half of the 250s and 500s, and 566 Challenger main draws, mostly 2026. Real net flags are at 24 events. Please wrap up now: finish team/ideas.md and team/ideas.csv with the ideas you have, with no new searches. Add to each idea its realistic coverage given these facts, and say which (if any) would still be testable at tour level. Then stop, and keep your final message short."

   * After it: no new search or fetch.
   * One 5-second rerun of `ideas_coverage.py` with both bugs fixed: coverage now uses real shot counts (`known` = flag and a count of 1–60), and courts are ranked by matches hosted. The numbers in § 2 are from that rerun.

**Sources rejected or unread:**
* The SUU working paper "One more shot" (2018), https://www.suu.edu/business/economics/working-paper-series/pdf/2018/lowrance-one-more-shot.pdf. Its PDF text could not be extracted: no PDF tool is in the environment, and the project's Python has no `pypdf`. A copy sits in the scratchpad, untouched.
* Kovalchik (2016), "Searching for the GOAT of tennis win prediction", *JQAS* 12(3):127–138, https://vuir.vu.edu.au/34652/: only the record was seen, so it is not cited for any claim.
* Off-topic hits: betting pages for the player "Kovalik", motorsport rallies, quiz shows.

**Ideas dropped, and why:**
* **Ball-in-play time.** `pointDuration` is unusable, per the gate.
* **Rally recovery** (the point after a long rally). It was rejected at 39/100 in the point-sequence debate, and [6] shows a one-point after-effect.
* **The previous match's within-match rally fade.** Within-match fade is closed for women and finishing form is inconclusive, and a fade per match would rest on even thinner data.
* **The plain noisy traits at depth.** Quick points won on serve and on return and long-rally points won, as levels, have no market mechanism beyond "more information". Their mechanism-bearing forms are R3 (luck) and R7 (balance).
* **"Rallies getting shorter" over both sides.** The direction is ambiguous (dominance or impatience), so it was split into R1 and R2.
* **Grinder × best of five.** It applies only to men's Slam main draws, about 500 a year: no power.
* **A recovery trait from rally data.** The minutes-based recovery trait (U-145) has a split-half of 0.086.
* **Wing, placement and serve direction.** They are outside the gate's scope (rally length and net play only).

**Variants weighed:**
* R1: "won within 4 shots" (chosen: the dominance it measures carries most player signal per point) against "ended within 4 shots" (kept as a variant).
* R1 and R2: a 28-day memory, matching stage 2, against the speed test's 14 days.
* R4: 9+ rallies (chosen: the anaerobic part, [1]) against total shots (kept as a variant); never imputed.
* R5: the symmetric price slope (chosen: no overlap with the ace gap) against the pattern-3 analogue (kept as a variant).

**Outcome discipline.**
* No match result and no winner column was loaded. The script reads no `match_winner`, `winner_from_points` or `scorer`.
* No within-match point winners were used in any computation.
* No other study's result tables were read beyond their reports.

**Files written:** this memo; [ideas.csv](ideas.csv); `src/eda/p9_point_details/ideas_coverage.py` (prints only; `./python.sh src/eda/p9_point_details/ideas_coverage.py`, about 5 seconds).
