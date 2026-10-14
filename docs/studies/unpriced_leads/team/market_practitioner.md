# Market practitioner (B3): where the 2025–26 close is blind, turned into statistics

13 Oct 2026 · Unpriced-leads team, round 1 · Role B3, the market practitioner ([brief](../briefs/03_market_practitioner.md), with the [shared context](../briefs/00_shared_context.md)) · Claude Opus 5.5, a subagent of session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Input to the lead's long list, not a decision. Ideas table: [market_practitioner_ideas.csv](market_practitioner_ideas.csv) (28 rows, prefix MP).

* **Outcomes read: none, of any season.** Book-against-book and open-to-close readings were made on seasons ≤ 2024 only. For 2025–26 I read only coverage counts and when prices were stamped. Code and outputs: `data/studies/unpriced_leads/team/market_practitioner/` (`descriptives.py`, `totals_flow.py`, their JSON, `probes/`).
* **Labels.** [Obs] observed in a repository file or in my outcome-free computation (path given); [Prov] provider or published claim (URL at the end, accessed 13 Oct 2026); [Inf] inference; [Sug] suggestion.
* **Keys.** Coefficients are in log-odds per standard deviation (SD) unless stated; z is cluster-robust over tournament weeks.

## In short

1. **The close is a product** (§ 1): a model-made opener, corrected by limit-capped sharp money. From 7 Sep 2025 the model's price is BetOnline's last *recorded* line. Blind spots sit outside the books' player models, after the last line, and where limits stop correction.
2. **Three structural facts** [Obs, `descriptives.json`]:
   * **BetOnline's last line is often early.** It was stamped more than 60 minutes before the listed start in 20–38% of men's and 26–43% of women's matches a season (2018–26). For about a third of matches the benchmark predates the day's news and conditions.
   * **A whole market is unused.** BetOnline's total-games lines (opening and last) are on disk for 2019–26, linked to 83–97% of the frame's matches from 2020. No study has used them.
   * **The 2026 market thinned.** OddsTrader books pricing the median match fell from 30–34 (2018–21) to 24 (2025) and 12 (2026). BetOnline's opener came a median 31–38 hours before the start to 2024, 24.6 in 2026.
3. **One crowd-bias mechanism failed an outcome-free gate.** The idea: BetOnline's US clientele makes it shade US or famous players. At the close (2018–24), BetOnline prices them no shorter than Pinnacle does: US players +0.0008 log-odds (z 0.7), top-10 players −0.001 to −0.002 (z −0.4 to −0.9), and their lines do not move differently from open to close.
4. **My top five:**
   1. the totals market's view of the match against the moneyline's (MP-01);
   2. wind, heat and altitude at the scheduled hour, with indoor matches as a negative control (MP-04–06);
   3. line momentum: does the close finish its own move? (MP-02);
   4. the incentive calendar: Finals race, ranking cliffs, points to defend (MP-07–09);
   5. each player's record against the close (MP-10).

   Then rest hours and the line's formation window (MP-11, MP-12), and Polymarket's informed flow, testable only prospectively (MP-13).
5. **Market-side requirements for the frozen test** (§ 5): report the Pinnacle and BetOnline periods separately; split fresh from stale closes; test each book's move against its own close; treat retirements by the books' rules; start any Polymarket test after the registration date.

## 1. How the 2025–26 close is formed, and where it leaves room

* **Openers are model-made, at low limits** [Inf]. BetOnline's close ties Pinnacle's in sharpness (2024–25) at a wider margin; its opener is 2.7 mLL softer than its close [Obs, `betonline_lines`].
* **Correction is limit-capped** [Prov, forum reports; "general practice" per `bet_timing`'s limitations]. Limits rise toward the start and are highest at Slams and 1000s, lowest in women's matches, 250s and early rounds.
* **What the close plausibly lacks** [Inf]:
  * information no book's player model ingests (conditions, incentives, the other markets, its own path);
  * news after BetOnline's last recorded line;
  * corrections that limits cut short;
  * persistent player-level misreads.

## 2. The long list

"From" is the first season discoverable on history; details per row are in the CSV.

| ID | Statistic | Data | From | Rank |
|---|---|---|---|---|
| MP-01 | Excess total: the total-games line beyond what the moneyline and the pair's serve levels imply | on disk | 2019 | 1 |
| MP-02 | Line momentum: the open-to-close move, beyond the same book's close | on disk | 2018 | 3 |
| MP-03 | Late steam: the last-3-hour move, line changes, time of the last change | download | 2018 | 10 |
| MP-04 | Wind at the scheduled hour × price steepness, and × serve gap | download (free) | 2013 | 2 |
| MP-05 | Heat (approximate WBGT) × age gap, and × home-climate gap | download | 2013 | 6 |
| MP-06 | Altitude × serve gap, and × altitude experience | download | 2013 | 14 |
| MP-07 | Finals-race pressure: in contention, clinched, eliminated (needs the clock) | partial | 2013 | 4 |
| MP-08 | Ranking cliffs: Slam seeding (rank 28–40), direct entry (90–120) | on disk | 2013 | 8 |
| MP-09 | Points to defend at this event | partial | 2013 | 13 |
| MP-10 | The player's shrunk record against the close | on disk | 2015 | 5 |
| MP-11 | Rest hours since the previous match ended | partial | 2018 | 7 |
| MP-12 | Formation window: hours from BetOnline's opener to the start (a stratifier) | on disk | 2018 | — |
| MP-13 | Polymarket informed flow, 48–6 h out | partial | 2025–26 only | 9 |
| MP-14 | Edition pace learned this week × serve gap (needs the clock) | on disk | 2013 | 11 |
| MP-15 | Doubles tells: a doubles walkover or retirement, doubles load | partial | 2018 | 12 |
| MP-16 | Lucky loser × a late first line | on disk | 2018 | — |
| MP-17 | An injury withdrawal from an event in the last 30 days | download | 2013 | 15 |
| MP-18 | Attention context: books quoting, opener time, Polymarket stake | on disk | 2018 | — |
| MP-19 | Public attention: Wikipedia pageviews against ranking (the clientele gate failed) | download | 2016 | — |
| MP-20 | Night session × the player's night record | partial | 2018 | — |
| MP-21 | Exhibition and team-event load | download | 2013 | — |
| MP-22 | Slam first round × a recent retirement or withdrawal | on disk | 2013 | — |
| MP-23 | Overnight close: US and European bettors both asleep | on disk | 2018 | — |
| MP-24 | Retirement settlement (test design) | on disk | — | — |
| MP-25 | Stale BetOnline close (test design) | on disk | — | — |
| MP-26 | Outright-implied strength minus the match price | download | 2025–26 | — |
| MP-27 | Coaching change | not available | — | — |
| MP-28 | Ball-brand switch between events | manual | 2013 | — |

## 3. The top ideas in depth

### 3.1 MP-01 · What the totals market knows that the moneyline does not

* **Statistic.** `excess` = BetOnline's total-games line minus its expected value given:
  * the moneyline's |logit p| and its square;
  * tour, best of, surface, indoor, level;
  * the pair's in-model serve levels (the feature store's IOS hold and ace sums, U-222, U-229, U-217).

  The expectation is fitted on 2019–24 with no outcome.
  * **Primary:** z(excess at the close) × logit p_close, a slope term. A positive excess means the totals market expects a closer match than the moneyline does, so the favourite is predicted to be over-priced.
  * **Members:**
    * the excess at the open;
    * the totals move net of the move the moneyline implies;
    * a diff form: total-implied minus moneyline-implied favourite strength, from the inverted fit.
* **Why the 2025–26 close would miss it** [Inf].
  * The two markets are bet by different money: favourite and parlay money on the moneyline, smaller and sharper money on totals.
  * They settle differently. Totals are void on any retirement; the moneyline has action once one set is complete ([Prov] Pinnacle's rules, quoted at the end; BetOnline's per the archived rule text in `docs/research/legacy-one-shot/docs/research_raw/retirement-void-rules.md`).
  * No arbitrage ties one to the other. So the gap holds a moneyline tilt the totals do not share, and the market's priced retirement risk. Neither is in the model.
* **Earlier evidence, outcome-free** [Obs, `totals_flow.json`; BetOnline 2019–24, 22,086 matches]:
  * **About a third of the total is not the moneyline's.** Best of three: the residual SD is 0.94 games at the open and 0.88 at the close (R² 0.60 → 0.67). Best of five: 3.8 → 2.8.
  * **The excess is transient.** At the open and at the close it correlates only 0.27.
  * **Some information flows from totals to the moneyline.** When the opening total says "closer", the opening favourite drifts by the close: −0.013 |log-odds| per SD, z −1.8 (best of five z −1.5).
  * **The total follows the moneyline hard:** a firming favourite lowers the total, z −17.
  * *Reading* [Inf]: the moneyline leads and the totals follow, with a weak flow back. The outcome test asks what is left at the close.
  * [Prov] Books mis-set game totals when the Slams changed their tiebreak rules in 2019–21 (Rose-Berman 2024), so register two-sided.
* **Learned or never priced.** If the market learns, the excess at the open predicts the moneyline's move (above, weakly) and nothing is left beyond the close. If it never prices it, there is a coefficient beyond the close and no move. Run edge_anatomy's three moments: beyond the open, the move, beyond the close.
* **Test.** Two-sided, both tours, beyond the model's odds input and beyond BetOnline's own close.
  * Coverage: about 4,300 matches in 2025 and 4,200 in 2026.
  * Resolution [Inf]: pair_strength's slope test had SE ≈ 0.012 per SD on 50,000 matches, so expect about 0.03 on Look A. Only an effect near ±0.06 per SD resolves: likely unresolved alone, so bundle it.
  * Live use: Pinnacle's and BetOnline's live totals exist.
* **What would kill it:**
  * no slope on 2019–24, or opposite signs in 2019–21 and 2022–24;
  * R² ≥ 0.5 on the model's serve inputs (then it is serve dominance again);
  * an effect that lives only in retirements (then it is MP-24's settlement wedge).
* **2025–26 exposure: no.**

### 3.2 MP-04–06 · Conditions at the scheduled hour, with indoor matches as the control

* **Statistic.** Taken from Open-Meteo's hourly archive at the venue over [listed start, +2 h]: wind speed and gusts, approximate WBGT from temperature, humidity and radiation, and elevation. The members:
  * z(wind) × logit p_close: predicted flatter;
  * z(wind) × the serve gap (`iosO_ace` or `iosO_first_won`, A − B): the bigger server's edge shrinks;
  * z(heat) × age gap;
  * z(heat) × home-climate gap (the mean summer temperature of each player's country);
  * 1[elevation > 500 m] × serve gap, and × altitude experience (own sequence).
  * **The placebo:** the same columns on indoor matches, built from the outside weather, should show nothing. It guards against venue and season confounding.
* **Why the close would miss it** [Inf].
  * Books price players. Weather reaches the price only through narrative and through bettors who look.
  * About a third of BetOnline's benchmark lines are stamped more than an hour before the listed start [Obs], before the day's conditions are known.
  * The 2026 ATP heat rule (cooling breaks from WBGT 30.1 °C) [Prov, via the edge_anatomy scout] shows the conditions are a live problem.
* **Earlier evidence.**
  * [Prov] At the Australian Open 2014–16 (360 matches per tour), higher WBGT brought more doctor calls, fewer winners and more double faults (Smith et al. 2018).
  * Practitioner pages say wind above about 15 mph favours underdogs, with no data.
  * In the project: never tested (U-196).
* **Data.** To download, cheaply.
  * Open-Meteo is free and the probe returned every field [Obs, `probes/receipts.jsonl`]: about 150 venues × seasons, 2,000–5,000 requests.
  * A venue gazetteer must be built.
  * The start hour: OddsTrader's listed time for 2018–26 (290 distinct times, so real hours [Obs]), session norms before that.
  * Covers every outdoor match, 80–94% of each season.
* **Learned or never priced.** Day-ahead forecasts exist at the open.
  * If the market learns, BetOnline's line flattens between open and close when wind is forecast.
  * If it never prices conditions, a coefficient remains beyond the close with no move, and it is larger where the close is stale.
  * Register a forecast-based variant too. The archive's weather at the listed hour is a near-nowcast for a bet at the close.
* **Test.** The wind slope over all outdoor matches (about 7,700 on Look A) carries most of the resolution. Heat sits in a few events, so read it as a bundle score.
* **What would kill it:**
  * the indoor placebo moves like the outdoor columns;
  * nothing on 2013–24;
  * the effect is gone from the close, though visible at the open (learned).
* **2025–26 exposure: no.**

### 3.3 MP-02 · Line momentum: does the close finish its own move?

* **Statistic.** mv = logit p_close − logit p_open at one book, oriented to A and RMS-scaled. It is tested beyond *that book's* close, overall and by limit tier: tour; Slam/1000 against 500/250; first match at the event (opening about 48 h out) against later rounds; price level.
  * Books: BetOnline (`bet_timing/frame.parquet`, 2018–26) and Pinnacle (OddsTrader's opening `p_ot20o`, 2018 to 7 Sep 2025).
  * Refinement: the late steam of MP-03, which needs the line history.
* **Why it would survive to the 2025–26 close** [Inf]. Limits stop sharp money short in low-limit segments, which leaves momentum. Match-day public money pushes visible sides too far, which brings reversal. Both are structural, and they last as long as the limits and the clientele do.
* **Earlier evidence.**
  * [Prov] Moskowitz 2021 (US sports): open-to-close momentum is reversed by outcomes, too small to beat costs.
  * [Prov] Buchdahl (Pinnacle tennis, all levels, 2015–19, 68,361 matches): "opening prices do not fully converge"; his gradient of 0.825 has a sign that is ambiguous as summarised. So register two-sided.
  * [Obs] BetOnline moves 2.5 points open to close, not toward the model (`bet_timing`).
  * [Obs, mine] The median |move| is 0.10–0.12 log-odds a season to 2024. US and top-10 players' lines show no different move (≤ 2024; top-10 men +0.008, z 1.4; women −0.009, z −1.8), so a fame-overshoot member is weak.
* **Learned or never priced.** The move *is* what the market learned. The coefficient beyond the close asks whether it learned all of it.
  * The outcome-free companion: does the move so far predict the rest of the move? That needs the line history, and it is the "beat the move" business.
* **Test.**
  * About 27,000 BetOnline matches in 2018–24 resolve roughly ±0.03 per SD.
  * Look A (about 8,000 at BetOnline; Pinnacle to 7 Sep 2025) resolves about ±0.05.
  * Test each book's move against its own close (§ 5).
* **What would kill it:** a coefficient of about 0 in every tier at both books on 2018–24, or opposite signs at the two books.
* **2025–26 exposure: no.**

### 3.4 MP-07–09 · The incentive calendar

* **Statistics** (diffs, A − B):
  * **Race pressure,** for tour-level matches from August. Year-to-date race points and the gap to the last qualifying place (top 8 on each tour), built from results finished before the match's earliest start. The states: *in contention* (the gap within the points available in his remaining events), *clinched* (likely to conserve), *eliminated*. The cut-off combines other players' results, so it needs the clock and `probe.py`.
  * **Ranking cliffs.** In the four weeks before a Slam's seeding ranking or entry-deadline ranking: 1[rank 28–40] (seeds 1–32) and 1[rank 90–120] (direct entry), signed by whether this round's points would cross the line. Own sequence: the published rank is a pre-match fact.
  * **Points to defend:** last year's points at this event ÷ his ranking points, and 1[defending champion].
  * The pool's B-MOTIV members (pre-Slam effort, post-Slam letdown) come along as known members.
* **Why the close would miss it** [Inf].
  * Incentives are absent from the books' player models and appear only as tipsters' anecdotes.
  * Stakes change week to week and differ by player.
  * The 2026 ATP rules (four mandatory 500s, 18 counting results) [Prov, via the edge_anatomy scout] move them again.
* **Earlier evidence** [Obs, `feature_interactions/next_candidates.md`]:
  * B-MOTIV: z₁ +2.39, z₂ +0.49 on 2014–24, so it failed replication;
  * I-061, the autumn odometer × age: z₂ +2.52;
  * race pressure, the cliffs and points to defend have never been built.
* **Learned or never priced.** All are known days before the opener. If never priced, the coefficient is the same beyond the open and beyond the close, with no move.
* **Test.** Each member touches a few hundred to about 2,000 matches a season. Register a bundle score; one member alone will read unresolved on Look A.
* **What would kill it:** no member keeps its sign across the four eras of 2013–24.
* **2025–26 exposure: no.**

### 3.5 MP-10 · Each player's record against the close

* **Statistic.** The shrunk mean of (result − closing probability), Σ(y − p)/(n + 30), over the player's previous ≤ 60 priced main-tour matches, each finished before this one could start. Members by role (as favourite, as underdog) and by surface. For Look A, a version frozen at 31 Dec 2024, so that no 2025 result enters.
* **Why the close would miss it** [Inf].
  * Books and bettors share player models. If they share a blind spot for a kind of player, the residual record carries it, named or not.
  * edge_anatomy found one such blind spot: men's returners under-rated in 2025–26.
  * A close cannot correct its own past errors per player unless someone tracks them; in tennis this is untested.
* **Earlier evidence: none.** The first gate, for the statisticians on ≤ 2024: the split-half reliability of the player residuals. Then the R² with the 56 non-price inputs.
* **Learned or never priced.** The record is known before the opener. Never priced = coefficients equal beyond the open and the close, with no move.
* **What would kill it:**
  * reliability near 0 (it is noise);
  * R² ≥ 0.5 (it is the IOS profile again);
  * no coefficient on 2015–24.
* **2025–26 exposure: partly.** The mechanism leans on edge_anatomy's 2025–26 finding about returners.

### 3.6 Next in line: rest hours and the formation window (MP-11, MP-12)

* **The statistics.** Hours from the previous match's estimated end to this match's listed start, capped at 72, with two members:
  * 1[rest < 20 h];
  * 1[the previous match ended after 23:00 local and this one starts before 15:00 the next day].

  The estimated end is the previous listed start plus its minutes, imputed from games where they are missing. The stratifier is the line's age, `h_bol_open`.
* **My angle** [Inf]:
  * after a late finish the next line is posted overnight, at low limits, with little money to correct it;
  * schedulers give stars the better slots, while the price follows reputation.
* **Data: partial.**
  * The match clock is day-level.
  * TennisLive's start times are placeholders: 99.8% of tour-level singles read 09:00 or 00:00 [Obs].
  * OddsTrader's listed times carry real hours, 2018–26.
* **Prior.** Day- and minute-based load measures were unresolved beyond the close (B-LOAD, B-PREV, I-056). Hours have never been built.
* **Exposure: partly.** edge_anatomy's 2025–26 refits found the schedule family unpriced.
* **Overlap.** This sits in B1's area. Pool it with theirs.

## 4. What exists only in 2025–26, and how it can still be tested

* **MP-13, Polymarket informed flow.**
  * **The statistic:** the net stake toward A from wallets that clearly beat Polymarket's close, placed 48–6 h before the listed start, ÷ all stake in that window. The wallets are classified walk-forward, on markets settled before the window opens, with `polymarket_sharp_money`'s rule.
  * **The prior** [Obs]: those 831 accounts beat Polymarket's close by +1.26¢ per $1 on held-out matches.
  * **No history to discover on.** So: register one fixed definition now, then read it once.
    * The primary: beyond BetOnline's close and beyond Pinnacle's recorded live price.
    * An outcome-free secondary: does the flow predict BetOnline's later move?
  * **Window caution** [Obs]. `polymarket_sharp_money` read Polymarket's closes and settled results to 21 Sep 2026, inside the sealed window that starts on 29 Jul 2026. This lead's look should therefore use matches after the registration date, captured by a live trade poller.
* **Betfair's close and Polymarket's volume** serve only as benchmarks and attention modulators (MP-18).

## 5. Market-side requirements for the frozen test

1. **Report the benchmark periods separately:** Pinnacle's close to 7 Sep 2025, BetOnline's last line after. A late-information statistic will look stronger in the BetOnline period, because that line is often stale (MP-25).
2. **Split weather, rest and line statistics by close freshness:** BetOnline's last line within 60 minutes of the listed start against earlier.
3. **Test a book's move against that book's own close.** For the 2025 months on Pinnacle's close, BetOnline's move is another book's move.
4. **Retirements.** The moneyline has action after one completed set at both books; totals are void on any retirement. Score with retirements before a completed set as void, and report retirements separately (MP-24).
5. **Keep the move readings for registration.** Following the lead's plan, open-to-close readings of the new statistics on 2025–26 stay a registered secondary; only ≤ 2024 moves were read here.
6. **Power** [Inf]. On Look A a full-sample statistic is detected with 80% power only from about 0.07 per SD (the edge_anatomy scout's figure). Subset statistics (windy matches, the cliffs, the race) need far more, so use bundle scores and Look B.
7. **Avoid market-structure measures with a 2026 break** (books per match, the opener's lead time), or standardise them within season.

## 6. Not proposed, and why

* **Book-against-book differences** (U-002–U-007, Polymarket minus BetOnline). They beat only a softer benchmark, and the production rule (Pinnacle's live line as the input) already uses them.
* **BetOnline shading toward US or famous players.** It failed the outcome-free gate (In short, item 3). An all-book fame bias stays in the long tail (MP-19).
* **Already closed or priced:** favourite–longshot by pair strength, head to head, home, travel, momentum and pressure traits.

## 7. How this memo was made

* **Read:** CLAUDE.md and both briefs; the reports of edge_anatomy (with its practitioner and scout memos), bet_timing, betonline_lines, odds_sources, sharp_benchmark, line_sharpening, polymarket_sharp_money, close_drift and pair_strength; the market-anchoring research; `universe.csv`; feature_interactions' near misses and its round-0 market brainstorm (MKT-01–25, built past rather than repeated); the OddsTrader adapter and research note.
* **Computed, outcome-free:** `descriptives.py` and `totals_flow.py`, above. No `a_won`, `won`, `score` or `status` column was loaded.
* **Probes:** one request each to Open-Meteo and Wikimedia pageviews (`probes/receipts.jsonl`).
* **Seasons whose outcomes were read: none.**
* **Weak points:**
  * the totals expectation here omits the IOS sums (the registered version adds them);
  * openers are OddsTrader's first sightings, and listed starts are schedules;
  * the gates compare BetOnline with Pinnacle, so they cannot see a bias both books share;
  * practitioner claims are not evidence, and Buchdahl's sign is ambiguous as summarised.

## Sources (accessed 13 Oct 2026)

* Pinnacle betting rules (tennis retirements, totals): https://www.pinnacle.com/en/future/betting-rules
* Buchdahl, "How efficient is the tennis betting market?": https://www.sportstradingnetwork.com/article/how-efficient-is-the-tennis-betting-market/
* Moskowitz, asset pricing and sports betting (summary): https://conference.nber.org/conf_papers/f92072/f92072.pdf
* Smith et al. 2018, heat stress at the Australian Open: https://opus.lib.uts.edu.au/handle/10453/129211 and https://opus.lib.uts.edu.au/handle/10453/129210
* Rose-Berman 2024, "How to bet on tennis" (totals and the Slam tiebreak rules): https://howgamblingworks.substack.com/p/how-to-bet-on-tennis
* Waterhouse VC, a professional tennis bettor ("scraping public data is easy … that's not an edge"): https://next.io/?p=122427
* Wind and conditions (practitioner pages, no data): https://www.tennismajors.com/?p=840272, https://www.tennisnerd.net/?p=28865
* Pinnacle tennis limits (forum reports): https://www.sportsbookreview.com/forum/sportsbooks-industry/1602843-pinnacle-betting-limits-how-to-view-without-account
* Open-Meteo archive API: https://archive-api.open-meteo.com/v1/archive; Wikimedia pageviews: https://wikimedia.org/api/rest_v1/
