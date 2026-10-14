# R1, the researcher: published evidence and data sources for statistics the 2025–26 close may miss

13 Oct 2026 · Unpriced-leads team, round 1 · Role: R1, the researcher ([brief](../briefs/04_researcher.md)) · Claude Opus 5.5 (`claude-opus-5-5`), a subagent of session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Input to the lead's long list, not a decision.

* **Outcomes read: none, of any season.**
  * My counts are availability flags, start and end times (presence only for 2025–26), umpire event types and field names.
  * Tiebreaks played, the one count derived from scores, covers seasons ≤ 2024 only.
* **2025–26 results seen:** only edge_anatomy's README ledger of in-model statistics, which the lead had also read. § 4 marks the ideas it shaped.
* **Labels:**
  * [Obs]: a repository file.
  * [PC]: a published or web source, accessed 13 Oct 2026, with its type and read level in § 8. A † marks a source taken from a repository note of 2–6 Oct.
  * [Inf]: inference.
* **Evidence** (`data/studies/unpriced_leads/team/researcher/`): the lanes' reports verbatim (about 90 sources) and briefs, probe receipts (`receipts/receipts.jsonl`), and the outcome-free count scripts with their JSON.

## In short

* **Almost no published study tests a player statistic against a sharp close.**
  * The one candidate tested against prices that include Pinnacle is the previous match's heat (Burke et al. 2023), and it is **priced**.
  * The rest is measured against rankings, Elo or soft odds, mostly before 2020.
  * So "unpriced" rests on a mechanism plus the project's own ledgers.
* **Clutch outcomes are luck.**
  * Over-performance in tiebreaks has a year-to-year correlation of "almost exactly zero". Over-performance on break points does not persist, and deciding-set records regress hard.
  * [Obs] The pool's men's measure of break points won beyond expectation was shrunk entirely away (no persistent variance), so it was never tested.
  * Edge_anatomy finds the close over-rates men's break-point saving in every era.
  * **Hence candidate 1: an unshrunk stock of luck.**
* **Load predicts lost time.** Injury research finds that cumulative load causes time away from competition, more so with age, and that spikes against a player's own normal predict injury. Retirements and withdrawals hit a record 4.8% of ATP matches in 2025 (news). The pool's acute:chronic load ratio (U-161) has never been screened.
* **New to the project: the draw shadow.**
  * Top-20 players who are not superstars win 3.4 percentage points less often while a superstar is still in the draw (ATP 2004–19, controlling for rankings; never tested against odds).
  * The Sinner–Alcaraz era recreates the condition.
* **Weakened or closed by the literature:**
  * travel;
  * extra rest from a walkover;
  * letdown after a title;
  * the previous match's heat;
  * popularity and search signals;
  * a player's volatility as a trait (the pool's split-half reliability was 0.051).
* **Data** [Obs]:
  * start times cover 99% of ATP main-draw matches and 93% or more of the WTA's from 2018;
  * Flashscore end times thin to 11–16% for men in 2025–26, but start time plus Stage 0's minutes (94–99%) fills the gap;
  * TennisLive's finish-time field is an empty placeholder;
  * doubles are on disk;
  * the WTA umpire log records physio calls, toilet breaks and heat suspensions;
  * there is no public serve-speed source for women.
* **Weather is free** (Open-Meteo, § 3). A venue table of the 278 main-tour event names and 3,000–4,000 requests would cover it. The free tier is non-commercial; whether betting counts as commercial is the owner's call.
* **No documented public source exists for:** a court-pace index by edition (the media's numbers come from social-media accounts), the ball used at each event, or dated coaching changes.
* **The search cap** (200 per session, shared) was reached by the lanes; § 7 lists the searches left.

## 1. How this memo was made

* **Built on, not repeated:** the research notes the brief lists, edge_anatomy's team memos, feature_interactions' round-0 literature scout (75 references) and the predictive-frontier register.
* **Three literature lanes** ran as background subagents: L1 body and conditions; L2 luck and psychology; L3 markets, incentives and the draw.
* **Checked at source** ("c" in § 8): Creutzburg 2024 (full text), Kovalchik 2020, Sackmann 2012 and 2018, Burke 2023.
* **Probes:** Open-Meteo ×5, Wikipedia ×3, GitHub ×1, and one WTA order-of-play PDF.
* **Local counts:** `scripts/*.py`, run with `./python.sh`. PDF text was extracted with pypdf in the base miniforge Python (`-I`), a declared research utility, because `tennis` lacks pypdf.

## 2. What the published evidence says

"vs mkt" means tested against betting prices.

| Topic | Key evidence [PC] | vs mkt | Reading |
|---|---|---|---|
| Fatigue, rest | **Slams** (Goossens 2015†): one set more in the previous match costs women −0.286 logit; men lose −0.184 only after two sets more; rest days n.s. **Time on court** (Sackmann 2017†): next-round win ratio against Elo falls from 1.07 after a short match to 0.76 after 4:30+. **Walkover rest:** 48.2% won against 48.9% predicted | Elo | Load matters, rest days do not |
| Night, time of day | Lab study, 12 players (Turner 2022): serve speed 10.5 km/h lower at 20:00 than at 14:00. ATP 2025 rules: post-midnight finishes fell from 50 to 39 | none | Thin |
| Travel | WTA: less sleep but no link to results (Maynard 2025/26†). MLB and NBA effects appear only after eastward travel, and are disputed | NBA spreads | Not recommended |
| Home | ATP +4.3 pp, surviving closed doors (Gucciardi & Ruberti 2025†). Davis Cup hosts' singles +15% against Elo | Elo | Project: priced (U-170) |
| Heat | **Burke 2023** (177,868 matches, 2002–17): over 10% more double faults at 35 °C than at 15 °C; a hotter previous match costs ≈0.1% of win probability per °C; "most tennis betting markets appear to accurately price climate risk". **Simani 2026** (men's Slams): in heat, older players do relatively better. **ATP 2026 rule:** a cooling break at WBGT ≥ 30.1 °C | **Pinnacle + 8 books: priced** | Interactions untested; a new rule from 2026 |
| Wind, altitude | Altitude: more aces (Sánchez Pay 2019†). Wind: no study of results | none | Venue pace (U-192) absorbs |
| Balls, court speed | ITF: ≈2 pace-rating points per km/h of post-bounce speed (snippet). Paris court pace index 46.6 → 35.1: social-media sourced, and copies disagree (SI 2025). ATP ball centralisation 2025–27, with no per-event list | none | No reliable table |
| Clutch | Tiebreak over-performance: year-to-year r "almost exactly zero" (Sackmann 2012, c). Break-point over-performance does not persist (2015†). Break point faced −0.76 pp; tiebreak −0.06 pp n.s. (Kovalchik & Ingram 2016). Break points won add "negligible" information (Kovalchik & Reid 2018) | none | Luck |
| Day form | 36% three-setters against 44% predicted; 7-0 tiebreaks 1.7% against 0.93%. The set-1 loser is 20.5 pp less likely to win set 2 given the odds (De Paola & Scoppa 2017) | average odds | Strong within a match; as a pre-match trait it does not persist |
| Momentum | +3.1–3.3 pp per win in the last 10, controlling for rankings only (Jetter & Walker 2015). No letdown after titles (Sackmann 2014) | ranks | Priced |
| Biases, efficiency | Higher margins on WTA matches (Barrutiabengoa 2022). The favourite–longshot bias grows with uncertainty (Abinzano 2019). Weighted Elo profits only at the best of 11 books (Angelini 2022). Markets beat models (Clegg & Cartlidge 2026†) | Pinnacle; average odds | Sharp closes hold |
| Retirements, injury | Cumulative load raises time-loss: hazard ratio 1.05 [1.01, 1.10] per 1,000 games, magnified with age (Kovalchik 2020, c). Lower-tier retirements: men 3.30%; +31% risk per 5 years of age (Palau 2024). Walkovers: injury in 28.7%, unknown in 61% (Casals 2025). Elo over-rates returning players by ≈25% (Sackmann 2018†) | none | Load-driven and rising |
| Age | Top-100 players got older, 27.9 on average by 2012 (Kovalchik 2014). Serve speed peaks around 26 (Sutter 2018) | none | Project: older men are over-priced |
| Gender, pressure | +1 SD of pressure raises the chance of being broken by +4.9 pp (men) and +2.8 pp (women) (Cohen-Zada 2017) | in-match | In-play only |
| Incentives | **Superstar in the draw** (Creutzburg 2024, c): top-20 players −3.4 pp; players outside the top 50 +4.1 pp. **Prize spreads** raise effort (Gilsdorf & Sukhatme 2008; Sunde 2009). **The week before a Slam:** seeds win 61% against 70% (Sackmann 2013, raw) | ranks | The shadow is new |
| Entry type | Slam first round: qualifiers +0.40 to +0.67 log-odds; men's lucky losers −0.40 (Eckmann 2024) | ranks | Project: priced (U-176) |
| Lower levels | Challenger→tour points-won factor 1.086–1.103; player ratios 0.98–1.18, persistence untested (Sackmann 2018, c) | — | Project: the close under-rates arrivals (U-330) |

## 3. Partial-information sources

The 8 Oct approval covers public data and the sites' own decryption, not logins, paywalls or CAPTCHAs; paid data is the owner's call.

| Need | What exists [Obs unless marked] | Route, terms | Covered? |
|---|---|---|---|
| Hourly weather, WBGT | Open-Meteo archive: wet-bulb, temperature, humidity, wind, gusts and radiation; ERA5 0.25° from 1940, ERA5-Land 0.1°; 5-day delay. Archived day-1 and day-2 forecasts through the previous-runs API. WBGT is then computed (Liljegren). 4 probes in `receipts/openmeteo/` | Free below 10,000 calls a day; CC BY 4.0; non-commercial | Yes (paid if betting counts as commercial) |
| Venue table | **Geocoder:** coordinates, elevation and IANA time zone (Kitzbühel 751 m, Europe/Vienna). **Elevation API:** Bogotá 2,582 m. **Stage 0 names to map:** 278 main-tour, 859 Challenger, 5,021 ITF. **The project's own table:** continent-level offsets only | Free | Yes |
| Court pace by edition | No documented public index. Could be estimated from Court Vision bounces (ATP 2021–24 and AO/RG on disk) | — | Partly |
| Ball by event | No compiled table found | By hand | — |
| Start and end times | **Start times** (`match_timing/links/*.parquet`): ATP main draw ≥98.6% every season; WTA 65–72% to 2017, ≥93% from 2018. **End times, Flashscore:** ATP 90–99% to 2024, then 16% (2025) and 11% (2026); WTA 65–86% to 2024, 99% (2025), 37% (2026). **Fallback:** start + Stage 0 minutes (ATP ≈99% except 2015, 52%; WTA ≥93% from 2016). **TennisLive's** `finished_at` is '0' on 99.98% of listings: not a source. **Order-of-play PDFs:** keep only the last day, released the evening before | On disk | Yes |
| Doubles | Sackmann ATP 2010–20, ≈1,300 matches a year, by event only. TennisLive 2018–26, with start times but no finish times: tour ≈1,900 a year, Slams 504, Challengers 2,150–3,200 | On disk | Yes |
| Medical time-outs, retirements | **WTA umpire log 2019–26:** physio calls (6,704); toilet breaks (14,179); suspensions for heat (236), injury (654) and illness (196). **Coverage:** 1,100–2,700 matches a year have a physio, toilet, suspension or coaching event. **Men:** none | On disk | Yes |
| Withdrawals, points to defend, prize money | Wikipedia edition pages: withdrawn seeds with reason and a dated reference; seeds' points before, dropped and after; withdrawal lists; protected rankings; prize money | Public, CC BY-SA; ≈4,000 pages | Yes |
| Coaching changes | Nothing dated or structured | News | — |
| Hawk-Eye tracking | **On disk:** ATP 2021–24 (4,570 matches); AO and RG 2019–24. **ATP 2025–26:** Stats Centre files can be decrypted under the approval; Court Vision unverified | Approved | Yes |
| Women's serve speed | None. The 434 WTA advanced-statistics fields of 2021–26 hold no speed | Ask SMT, WTA or Stats Perform | Paid / ask |
| Match Charting Project | Head `1813a13` (18 Sep 2026) is still the version held | GitHub | Yes |

## 4. The long list

Full fields are in `researcher_ideas.csv`.

**Codes.**
* **Status:** D on disk, P partial, N needs a download, X not available.
* **Exposure** (whether a 2025–26 result shaped the idea): p partly, n no.

| id | Statistic | Area | Status | Exposure | Rank |
|---|---|---|---|---|---|
| RS01 | Clutch-luck stock (break points + tiebreaks beyond the match's own point rates) | conversion_luck | D | p | 1 |
| RS02–04 | Its pieces: break-point luck, tiebreak luck, deciding-set luck | conversion_luck | D | p | – |
| RS05 | Load spike against own normal (acute:chronic ratio) | rhythm_body | D | p | 2 |
| RS06 | Season load × age | rhythm_body | D | p | 9 |
| RS07 | Turnaround in hours, late finish, doubles since last singles | rhythm_body | P | n | 5 |
| RS08 | Doubles load at the same event | rhythm_body | P | n | 7 |
| RS09 | Draw shadow (a dominant player alive in the draw; next-round shadow) | other | D | n | 3 |
| RS10 | Player's own translation ratio, lower level → tour | career | D | n | 4 |
| RS11 | Ranking stakes (points to defend, distance to a threshold) | career | P | n | 6 |
| RS12 | Heat-weighted recent load; heat × age | conditions | N | n | 8 |
| RS13 | Edition court pace from Hawk-Eye bounces | conditions | P | n | – |
| RS14 | Decline from own peak (men's serve speed and serve points) | career | P | p | 10 |
| RS15 | Day-form volatility | point_state | D | p | – |
| RS16 | Early-retirement risk under each venue's settlement rule | market_info | D | n | – |
| RS17 | Recent withdrawal with an injury reason | rhythm_body | N | n | – |
| RS18 | Lucky-loser entry | career | D | n | – |
| RS19 | Pre-Slam effort, post-Slam letdown | career | D | n | – |
| RS20 | Exposure to tiebreaks in the matchup | point_state | D | n | – |
| RS21 | Night session | conditions | P | n | – |
| RS22 | Eastward travel (not recommended) | rhythm_body | P | n | – |
| RS23 | Altitude and acclimatisation | conditions | N | n | – |
| RS24 | Wind at the scheduled hour | conditions | N | n | – |
| RS25 | Ball switch (not recommended) | conditions | X | n | – |
| RS26 | Coaching change | career | X | n | – |
| RS27 | Women's serve-speed state | serve_return | X | n | – |
| RS28 | Physical state from the rally | point_state | P | n | – |
| RS29 | Score-state resilience | point_state | P | n | – |
| RS30 | Trust in the close (market-internal) | market_info | P | n | – |

## 5. The top ideas in depth

**RS01. The clutch-luck stock.**
* **Definition.** For each completed match with a box score in the last 365 days, three residuals against that match's own point rates, assuming independent points:
  * break points saved − faced·p_s;
  * break points converted − chances·(1−p_o);
  * tiebreaks won − played·q, where q = p_s(1−p_o) / [p_s(1−p_o) + (1−p_s)p_o].

  Each is summed with a 13-week half-life and not shrunk. The composite is the mean of the three standardised stocks, A − B, with an expected negative sign. It follows each player's own sequence.
* **Mechanism.** Records, rankings and "clutch" narratives absorb luck that later regresses. The model's raw break-point rates mix that luck with serving skill.
* **Evidence:**
  * § 2;
  * the pool's men's version came out constant (`src/eda/feature_interactions/inventory/build_inventory.py`);
  * edge_anatomy, 2013–24: men's break points saved against the price, z −1.6 (long memory) and −2.3 (two weeks).
* **Overlap:** medium (`form_bp_saved`, `iosO_bp_saved`). It is the same family as B2's PS01/PS03, which S2b is building.
* **Exposure: partly.** The idea was shaped by edge_anatomy's 2025–26 reading of the in-model break-point rates (men z −3.9 and −2.8). The residual itself has never been read on 2025–26.
* **Test.** Effects like the in-model rates (β 0.02–0.04 per RMS unit) would show z 2–4 in discovery. On Look A they are unresolved alone, so register this within a group.
* **What kills it:** split-half persistence above 0.3, or the close loading on it with no residual left.

**RS05. Load spike against the player's own normal, × age.**
* **Definition.**
  * log(G14 / max(G_chronic, floor)): games played (singles at every level, plus doubles where held) in the 14 days before `es`, over the mean 14-day load on days 15–70.
  * A flag at a ratio of 1.5 or more.
  * The member RS06: games in the last 52 weeks × max(0, age − 27).
  * A − B; own sequence.
* **Mechanism.** The close and the model see absolute counts (`sets_14d`). Spikes cause injury and flat performances before any news comes out, and the 12-day Masters (2023, 2025) raised spikes.
* **Evidence:**
  * Kovalchik 2020 (389 players, 55,773 weeks);
  * an acute:chronic review (thresholds 1.3–1.5);
  * [Obs] B9a's odometer × age, z₂ +2.52 on 2022–24.
* **Pool:** U-161, U-139, U-144, U-296.
* **Exposure: partly.** The family's 2025–26 strength is known; the ratio has never been read.
* **What kills it:** an orthogonal part near zero, or no effect on the next match's points won against the player's own norm in a gate on ≤ 2024.

**RS09. Draw shadow.**
* **Definition.**
  * Dominant: as-of Elo at least 100 above the field's third-best entrant.
  * S = 1[another dominant player is still alive at `es`] × 1[the player is in the Elo top 20 and not dominant].
  * N = 1[a dominant player is the projected next opponent].
  * A reverse term for players outside the top 50.
  * A − B.
  * Being "alive" depends on other players' results, so it needs the clock and `probe.py`.
* **Mechanism.** Effort in an elimination draw responds to the draw beyond the current match; prices are set match-up by match-up.
* **Evidence.**
  * Creutzburg 2024: ATP 2004–19, 27,366 matches; player-season, tournament and round fixed effects; superstars named (Federer, Nadal, Djokovic, Murray); no odds. The +4.1 pp loses significance with more events.
  * Deutscher, Neuberg & Thiem 2023.
  * Against: no effect in golf or skiing (Babington 2020).
* **Exposure:** no.
* **Resolution:** about 0.1–0.3 mLL [Inf], unresolved alone. Also read 2013–19, where the papers found it.
* **What kills it:** no effect with Elo, rather than rankings, as the control.

**RS10. Player's own translation ratio.**
* **Definition.**
  * Men: opponent-adjusted points won at Challengers over tour level, last 36 months, shrunk toward the walk-forward global factor (≈1.095).
  * Women: WTA 125 against tour level (box scores 99% from 2016; ITF only from 2025).
  * Feature: (ratio − global) × U-330's share; A − B; own sequence.
* **Mechanism.** One shared discount (rankings, Elo, the level layer) misjudges players whose lower-level form translates unusually. The close under-rates arrivals from lower levels.
* **Evidence.**
  * The published support is thin (Sackmann 2018).
  * [Obs] U-330 beside the close: +0.13 [+0.07, +0.19] (2013–24); after the current best, +0.12 [+0.03, +0.21] (2020–24).
* **Exposure:** no.
* **What kills it:** split-half persistence below 0.2, or no gain beside U-330.

**RS07. Turnaround in hours.**
* **Definition.**
  * H = hours from the previous match's end (singles or doubles) to this match's scheduled start.
  * The end is Flashscore's end time where present, else the start time + Stage 0's minutes; for doubles, which have a start time only, a typical duration.
  * Features: min(H, 48); a flag for H < 20; a flag for a previous finish after 23:00 local time (needs the venue table); doubles since the last singles match.
  * The schedule is published the evening before, so it is known at bet time.
* **Mechanism.** Books and models count days, not hours.
* **Evidence:** indirect only: lab work, NBA and NFL spread studies, and previous-match load. The ATP had to legislate late finishes.
* **Overlap:** low. It is the same as B1's RB03/04, which S2a is building.
* **Exposure:** no.
* **Power:** under 20 h in 4–9% of matches, so it is likely unresolved alone.

## 6. The five research-backed candidates most likely unpriced by the 2025–26 close

1. **RS01, the clutch-luck stock:** the outcomes are luck, and the close over-rates men's break-point saving.
2. **RS05, a load spike against the player's own normal, with age:** injury evidence, inside the family the close misses.
3. **RS09, the draw shadow:** −3.4 pp against rankings; a new mechanism.
4. **RS10, the player's own translation ratio:** the project's evidence of mispricing, though the literature is thin.
5. **RS07, turnaround in hours:** new clock data, indirect evidence.

**Next:** RS11 (stakes), RS08 (doubles) and RS12 (heat × load or age; lowered by Burke).

## 7. Gaps and cautions

* **Not searched (cap reached):**
  * Pinnacle's and BetOnline's own retirement rules (the lanes found conflicting one-set and two-set quotes);
  * Brown & Minor 2014 (a "shadow" study cited by Creutzburg);
  * the ITF's pace-rating formula, and who compiles the media index;
  * lists of balls and coaches;
  * serve against return as predictors.
* **Read levels.** Many rows are abstracts or snippets; unchecked numbers are as the lanes reported.
* **Timing.** RS09 and RS13 need the clock and `probe.py`. RS12 should train on the weather at the scheduled hour and run live on day-ahead forecasts.
* **Stale closes.** BetOnline's last line is often hours old (B1, B3), which affects RS07, RS12 and RS17.

## 8. Key sources

All accessed 13 Oct 2026; the lane files hold about 90. Type: PR peer-reviewed, WP working paper, TH thesis, BL practitioner, PV provider/news. Read: f full, p partial, a abstract, s snippet, c checked by R1.

* Burke et al. 2023, NBER WP 31650. WP; f, c. https://www.nber.org/papers/w31650
* Kovalchik 2020, *PLoS One* 15(4). PR; a, c. https://pmc.ncbi.nlm.nih.gov/articles/PMC7164605/
* Amor-Salamanca et al. 2025, *Sports* 13(10). PR; a. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12568103/
* Simani et al. 2026, *MSSE*, doi:10.1249/MSS.0000000000004152. PR; a.
* Turner et al. 2022, *IJSSC* 19(1). PR; a. https://ro.ecu.edu.au/ecuworks2022-2026/1509
* ATP: heat rule. PV. https://www.atptour.com/en/news/new-heat-rule-effective-from-2026
* ATP: ball centralisation. PV; c. https://www.atptour.com/en/news/ball-centralisation-june-2025
* Sports Illustrated, Paris court speed, 2025. PV; c. https://www.si.com/onsi/serve/news/data-shows-major-change-in-2025-rolex-paris-masters-court-speed
* Capel-Davies & Spurr 2019, ITF review. PV; s. https://itfcoachingreview.com/index.php/journal/article/view/89
* Palau et al. 2024, *PLoS One* 19(6). PR; f. https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0304638
* Casals et al. 2025, *MJSSM* 21(2). PR; f. https://mjssm.me/clanci/MJSSM_September_2025_Rodrigo.pdf
* Kovalchik 2014, *JQAS* 10(2). PR; s. https://vuir.vu.edu.au/40255/
* Sutter et al. 2018, *Behav Ecol*. PR; a. https://datadryad.org/dataset/doi:10.5061/dryad.58dm217
* Sackmann posts (BL):
  * 2012 tiebreak luck (c): https://tennisabstract.com/blog/?p=922
  * 2012 withdrawals: https://www.tennisabstract.com/blog/2012/09/03/withdrawal-effects/
  * 2013 week before a Slam: https://www.tennisabstract.com/blog/?p=1067
  * 2014 post-Masters: https://tennisabstract.com/blog/?p=1689
  * 2018 translation (c): https://www.tennisabstract.com/blog/2018/04/25/translating-atp-statistics-across-main-tour-and-challenger-levels/
  * 2024 three-set: https://www.tennisabstract.com/blog/?p=6950
* Kovalchik & Ingram 2016, MIT Sloan SAC. Conference paper; f. https://martiningram.github.io/papers/hot-heads-cool-heads.pdf
* Kovalchik & Reid 2018, *Stat Appl* 30(2). PR; f. https://www.sa-ijas.org/ojs/index.php/sa-ijas/article/view/30-11
* De Paola & Scoppa 2017, IZA DP 9315. PR; f. https://www.iza.org/publications/dp/9315
* Jetter & Walker 2015, IZA DP 8934. PR; f. https://www.iza.org/publications/dp/8934
* Cohen-Zada et al. 2017, IZA DP 10587. WP; f. https://docs.iza.org/dp10587.pdf
* Angelini et al. 2022, *EJOR* 297(1). PR; f. https://cris.unibo.it/handle/11585/821483
* Creutzburg 2024, HCED WP 079. WP; f, c. http://www.hced.uni-hamburg.de/WorkingPapers/HCED-079.pdf
* Deutscher, Neuberg & Thiem 2023, *JEP* 99. PR; a. https://ideas.repec.org/a/eee/joepsy/v99y2023ics0167487023000648.html
* Babington et al. 2020, *JSE* 21(1). PR; a. https://ideas.repec.org/a/sae/jospec/v21y2020i1p44-63.html
* Gilsdorf & Sukhatme 2008, *JSE* 9(3). PR; a. https://ideas.repec.org/a/sae/jospec/v9y2008i3p287-303.html
* Sunde 2009, IZA DP 947. PR; p. https://docs.iza.org/dp947.pdf
* Eckmann 2024, Cornell. TH; s. https://doi.org/10.7298/kr1a-s955
* Barrutiabengoa et al. 2022, *JSE* 23(7). PR; a. https://ideas.repec.org/a/sae/jospec/v23y2022i7p881-906.html
* Abinzano et al. 2019, *JSE* 20(2). PR; a.
* Open-Meteo: terms and API documentation. PV; c. https://open-meteo.com/en/terms
* † Goossens 2015; Sackmann 2015/2017/2018; Gucciardi & Ruberti 2025; Maynard 2025/26; Sánchez Pay 2019; Clegg & Cartlidge 2026. All are in `docs/studies/feature_interactions/round0/literature.md` and `docs/research/`.
