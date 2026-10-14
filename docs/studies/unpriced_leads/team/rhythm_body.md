# Rhythm and body: readiness information the 2025–26 close may miss (B1, round 1)

13 Oct 2026 · Role B1, the rhythm-and-body scout ([brief](../briefs/01_rhythm_body.md), [shared context](../briefs/00_shared_context.md)) · Claude Opus 5.5, a subagent of the lead's session `e1ffc84e-fa2d-42f9-9d17-7c936a046c45` · Written before any result of this study · The ideas table: [rhythm_body_ideas.csv](rhythm_body_ideas.csv) (26 rows)

* **Outcomes read: none, of any season.** Every number below is a count, a coverage share or an R² between rough encodings and the model's inputs; no winner, score or box-score numerator was read. Scripts and outputs: `data/studies/unpriced_leads/team/rhythm_body/` (`peek_*.py`, `prevalence.py`, `novelty.py`; `*.txt`, `*.json`).
* **One web probe:** a single request to the free Open-Meteo archive, to confirm it serves the heat fields (receipt in `probes/`).
* **Labels:** *observed* (a repository file), *provider claim* (web, URL and date), *inferred*, *suggestion*, *recalled* (literature not verified in this session).
* **2025–26 exposure.** This lens exists because edge_anatomy's 2025–26 ledger found the schedule-and-body family unpriced, so every idea is at least "partly" exposed through its motivation. None rests on a 2025–26 result of the statistic itself unless its CSV row says so.

## Summary

1. **The in-model schedule inputs are crude, and they mix things.** `sets_14d` counts singles sets, blending survival through this draw, match rhythm and load; the surface pair sees only the surface label; age is a population curve entered as A − B.
   * *Inferred* from edge_anatomy and feature_interactions: the market under-values recent match play, under-penalises surface rust and under-prices ageing, while at the scale of days fatigue looks priced (every days- or minutes-based load measure tied beyond the close).
   * So the richer information is match play the singles record cannot see, recovery in hours (the one scale where fatigue is physiologically sharp), adaptation to conditions, and the body's own trajectory.
2. **My top five.**
   1. **Hidden doubles play** (RB01, with RB02 and RB24): doubles matches in the last 7 days and at this event. It is match play without the survival signal of singles wins.
   2. **Rest in hours and the same-round turnaround gap** (RB03, RB04): late finishes, early starts, and the day-session against night-session gap.
   3. **Heat × acclimatisation** (RB07): hot sessions, weighted by how much heat each player met in the previous two weeks.
   4. **Style-specific ageing** (RB10): age × the return share of the player's long-memory edge.
   5. **Qualifier and lucky-loser arrival cost** (RB13): what the qualifying run cost and how little rest followed. The lucky-loser contrast also tells rhythm from survival.
3. **Two facts from the data, both observed.**
   * **Doubles is common and invisible.** In 2018–24, exactly one of the two players had played doubles in the previous 7 days in 30–38% of men's and 33–38% of women's frame matches. A rough encoding has R² 0.02–0.03 on the model's 49 non-price inputs.
   * **Rest in hours is computable from files on disk:** for 90–97% of men's frame matches (2013–26) and 70–97% of women's from 2018.
4. **What one look can see.** Look A resolves about 0.064 log-odds per RMS unit (one-sided, both tours; `data/studies/unpriced_leads/resolution.json`). Most ideas here need 0.1 log-odds or more where non-zero, so "unresolved" alone is their likely reading: bundle them, and use Look B.
5. **A trap for late information.** BetOnline's recorded last line comes more than 6 hours before the start in 10–15% of 2023–26 matches. Rest hours, the day's heat and last night's doubles can arrive after it, and would then look unpriced for the wrong reason (§ 5).

## 1. What the coarse inputs measure, and what they leave out

**What the inputs measure** (observed).
* **`sets_14d`:** log(1 + singles sets in events whose tournament date falls within the 14 days before this event, plus this event's earlier rounds), at every Stage 0 level, team-tie singles rubbers included, counted from event start dates (docstring of `src/eda/feature_interactions/inventory/perplayer_load.py`, after Stage 4's `state()`). Stage 0 holds no doubles.
* **`surf_season`, `surf_layoff`:** singles matches on the surface label only; indoor or outdoor, court pace, altitude and heat are invisible.
* **`age`, `age_sq`:** A − B on a population curve; the model cannot apply A's own curve.

**What has been tried in this lens** (observed: `universe.csv` U-128–U-180, [feature_interactions](../../feature_interactions/README.md), [next_candidates](../../feature_interactions/next_candidates.md)). z in each block's declared direction, on 2014–24 (U-132: Stage 4's 2013–26 windows):

| Tried | Result |
|---|---|
| Days since the last match (U-132) | tied at the close |
| Minute kernels (B-LOAD) | z +0.63 |
| The previous-round scare × rest (B-PREV) | −0.07 |
| Arrival debt: deep run, travel, continent-level jet lag (B10) | +0.37 |
| Constitution × load (B9a) | +1.48 (z₁ +0.10, z₂ +2.52) |
| Match demand × fatigue (B9b) | −0.81 |
| Age × recovery debt (I-053) | failed replication |
| The indoor-switch state (B-SWITCH) | Wald p 0.31 |

None passed. Near misses: matches already played here (U-138, +3.29 beyond the model, descriptive); rust after a break (I-043, +4.05, then unresolved on 2025–26); the autumn odometer × age (U-296).

**My reading** (inferred). The edge sits on the rhythm side: counts of match play carry it (`sets_14d`, matches here, surface matches), while measures of fatigue in days tie. So I looked for match play and recovery that neither the singles record nor the day count can see.

## 2. The long list

"New" means beyond the 57 inputs, `spd_L` and the pool. Ranks: 1 = best; "—" = long tail. Definitions, paths and coverage are in the CSV.

| ID | Idea | Data | New? | Rank |
|---|---|---|---|---|
| RB01 | Doubles matches in the last 7 days and at this event | on disk 2018–26; men event-level 2010–20 | new | 1 |
| RB02 | Surface rust counting doubles | on disk | new construction of an input | 7 |
| RB03 | Rest in hours (short turnaround) | on disk | new (U-132 counts days) | 2 |
| RB04 | The two players' rest gap within a round | on disk | new | 3 |
| RB05 | Recovery ratio after a long match | on disk | new | — |
| RB06 | Late finish, then early start | partial | new | — |
| RB07 | Heat × acclimatisation | download | new | 4 |
| RB08 | Heat tolerance: home climate, body size | download | new | 12 |
| RB09 | Women's heat-break and medical history (WTA log) | on disk | near U-179 | — |
| RB10 | Style-specific ageing | on disk | new (BOD-27, never built) | 5 |
| RB11 | Career mileage, full careers | partial | better data for U-158 | 9 |
| RB12 | Years past the player's own peak | on disk | near U-045 | — |
| RB13 | Qualifier and lucky-loser arrival cost | on disk | new parts of U-176, U-276 | 6 |
| RB14 | The bye seed's cold start | on disk | a population of U-138 | 13 |
| RB15 | Retirement or walkover given, any level, recently | on disk | full-history U-160 | 10 |
| RB16 | Withdrawal from an entered event | download | new | 11 |
| RB17 | Conditions-matched rust (indoor, pace, altitude) | partial | new construction | 8 |
| RB18 | Altitude arrival | download | new | — |
| RB19 | Real time-zone shift and direction | download | better data for U-151 | 14 |
| RB20 | Excess on-site cost (struggle or cruise) | on disk | BOD-01's Ex, never built | 15 |
| RB21 | Distance run at the Slams | partial | new | 16 |
| RB22 | Serve-speed fade in the previous match | partial | B2's lens | — |
| RB23 | Short off-season | on disk | near I-043 | — |
| RB24 | Still alive in the doubles draw | partial | new | — |
| RB25 | Team-tie doubles rubbers and travel | partial | new | — |
| RB26 | Exhibition match play | partial | new | — |

**Pool items in my lens that deserve a solo screen** (not new; S1's job): U-138 matches here; U-152 the 21-day fitness kernel, a "control" never screened alone; U-296 the autumn odometer × age; U-162 the post-Slam letdown.

## 3. The top ideas

### 3.1 Hidden doubles play (RB01; RB02 and RB24 as members)

**Definition.**
* For player X before a match on clock day d (`timing.parquet`, `obs`): **D7_X** = doubles matches X played on days d−7..d−1 at any level, split into this event and elsewhere (a load variant counts their sets); x = log1p(D7_A) − log1p(D7_B), with the two parts also as separate members.
* Same-day doubles are left out: 83% of TennisLive's doubles rows show 00:00 or 09:00, which look like placeholder times, so the order within a day is unknown.
* **Men, 2013–17:** Sackmann gives events, not days. The bet-time-safe version is 1[entered in this event's doubles draw] (known at the draw) plus doubles at the previous event.
* **RB02** recomputes `surf_layoff` counting doubles on the surface; **RB24** flags a player still alive in the doubles draw.

**Mechanism** (inferred). **Rhythm without survival.** If the market under-values recent match play (`sets_14d` and U-138 both beat it), it should under-value doubles too. Doubles carries no singles survival or form signal, so its sign tells which mechanism drives the family. If fatigue dominates instead, the late-week, previous-day part turns negative: hence the separate parts.

**Why the 2025–26 close would miss it** (inferred). Singles prices are made from singles ratings, singles results and news. Doubles results sit in another market and feed; no rating system, public model or our model reads them. Pinnacle and BetOnline can see the doubles schedule, but nobody turns it into a singles adjustment.

**Data** (observed).
* **TennisLive** (`data/dump/points/tennislive/listed.parquet`): 170,241 doubles rows, 2018–26 (ATP about 3,700 a year in 2018–20, then 9,100–13,800; WTA about 1,300 in 2018–19, 2,700 in 2020, then 6,700–10,500). The jump is ITF doubles; tour-level doubles rows are stable at about 1,900 a year plus 504 at the Slams (2018–24). 95.8% of member-rows map to a Stage 0 id by exact normalised name through the lower-level team's crosswalk (`data/studies/lower_level_evidence/system/stage0/C0_now/evidence/crosswalk_tennislive.csv`).
* **Sackmann's ATP doubles 2010–20** use the same `atp:` ids, with minutes but no days; **the WTA API** holds doubles for 2019–26, with ids. **Not held:** women's doubles before 2018.

**Prevalence** (observed, `prevalence.txt` part B). Frame matches in which exactly one player had doubles in days −7..−1:

| | Share |
|---|---|
| Men | 0.38 (2018) falling to 0.30 (2024); 0.25 (2025), 0.24 (2026) |
| Women | 0.33–0.38; 0.36 (2025), 0.30 (2026) |
| Men by level (2018–26) | 250s 0.37, 500s 0.39, 1000s 0.32, Slams 0.18 |
| Women by level | 0.28–0.38 |
| Men 2013–20, the same event's doubles draw (Sackmann, by level) | 0.43–0.45 |

**Overlap.** None of the 57 inputs. The rough x has R² 0.034 (men) and 0.023 (women) on the 49 non-price, non-context inputs, and correlation 0.03–0.04 with `sets_14d` (`novelty.json`). Pool: none (edge_anatomy's scout listed it, #12, unbuilt).

**Earlier evidence.** None for doubles. Family prior: `sets_14d` beats the close in 10 of 10 tour-eras (edge_anatomy; 2013–24 z men +3.5, women +4.0); U-138 adds +3.29 beyond the model (feature_interactions, 2014–24, descriptive).

**2025–26 exposure:** partly, through the lens only.

**The test and its likely resolution.**
* **Discovery:** the harness on 2018–24 (about 32,000 frame matches; SE about 0.013 per RMS unit), with the men's event-level version on 2013–17 as a replication; the move lens shows whether BetOnline's line already moves toward it.
* **Look A** needs about 0.10 log-odds (2.5 points at even odds) where one player has played two doubles matches and the other none. My prior is about half that: "unresolved" alone is likely; beside U-138 in a bundle it has a better chance.

**What would kill it.** Discovery |z| below 1 in both tours with the eras split; or the two parts cancel (then keep the parts, not the sum); or the line moves all the way to it before the close.

### 3.2 Rest in hours (RB03, RB04; RB05 and RB06 as variants)

**Definition.**
* rest_h = this match's start (UTC) minus the end of X's previous played match, at any level. **Starts** from the clock's link files (Flashscore first, then SofaScore, Live Tennis API, api-tennis, WTA API, Slam feeds, TDI, Match Charting); **ends** from Flashscore's `end_utc` where the implied duration is 15–420 minutes, else start plus Stage 0 minutes.
* **Encodings:** RB03, x = s(rest_A) − s(rest_B) with s(h) = max(0, 24 − h)/24; RB04, when both rests are under 72 h, x = clip(rest_A − rest_B, −36, 36)/12; RB05, rest relative to a long previous match; RB06, "last to end on its day at its event" × "first or second on court today" (no time zone needed).
* **At bet time:** the scheduled start from the order of play (published the evening before) and the previous match's end.

**Mechanism.** "Played yesterday" spans 14 to 34 hours. Sleep after a night finish is the physiologically sharp cost (*recalled:* sleep restriction lowered tennis serve accuracy, Reyner and Horne 2013). Days-based load tied beyond the close; the hours tail and the day/night asymmetry were never built.

**Why the close would miss it** (inferred). The facts are public but need arithmetic across two matches. BetOnline's opening comes a median 24–38 hours before the start ([bet_timing](../../bet_timing/README.md)), often before the previous round is played. Sharp money probably prices the famous 3 a.m. finishes, not the routine 10-hour gap.

**Coverage** (observed, `prevalence.txt` part C).
* Both players' rest in hours: men 0.90–0.97 of frame matches (2013–26); women 0.70–0.97 from 2018, 0.37–0.39 before.
* Both under 72 h: 40–46% of matches. A player under 20 h: 4–9%. Within 72 h, 6.7% of player-matches are under 20 h and 28% under 24 h.
* A gap of 12 h or more: 7–11% of men's matches and 8–12% of women's (from 2018); the gap's median is 2.8 h, P75 6.8 h, P90 23 h.

**Overlap.** R² on the inputs 0.029 / 0.023 (short rest, men / women) and 0.014 / 0.012 (gap); correlation with `sets_14d` 0.07–0.08 and −0.03. Pool: U-132 (days), U-139, U-291, U-195 (start time, never tested).

**Earlier evidence:** none for hours. **2025–26 exposure:** no, beyond the lens.

**The test and its likely resolution.** Discovery on 2013–24, declared direction: less rest loses to the close. Rest under 20 h affects about 5% of matches, so Look A needs about 0.2 log-odds where present; the gap (non-zero in about 40%) needs about 0.1 log-odds per 12 hours. Both are a stretch alone: bundle them.

**What would kill it.** Discovery |z| below 1; or no dose-response (the under-16 h bin no worse than 20–24 h); or the effect disappears once the line must postdate the previous match's end (§ 5).

### 3.3 Heat × acclimatisation (RB07; RB08 and RB09 as companions)

**Definition.**
* **WBGT for each outdoor match** at the venue over its hours, from hourly temperature, humidity, wet-bulb temperature, radiation and wind (Liljegren's outdoor method or a simpler approximation). **H_m** = max(0, WBGT_m − 25 °C), 0 indoors (Stage 0's flag for men; the 9 Oct indoor input for women).
* **Acc_X** = Σ max(0, WBGT_j − 22)·exp(−days_j / 7) over X's own matches in the 14 days before; x = H_m·(Acc_A − Acc_B)/sd.
* **Companions:** RB08 (tolerance from home climate and body size); RB09 (women's heat-break and physio history in the WTA umpire log).

**Mechanism.** Heat acclimatisation builds over one to two weeks of exposure (*recalled:* Périard, Racinais and Sawka 2015). Players reach the Australian summer from the European winter or from Brisbane and the United Cup, and Washington and Canada from European clay or indoor events. Both players face the same heat, so the price moves little; acclimatisation is in nobody's model.

**Why the close would miss it** (inferred). No form guide carries the weather history of the venues a player came from; the market knows the famous heat sufferers, not the gradient.

**Data.**
* **To download.** Open-Meteo's archive serves hourly temperature, humidity, dew point, wet-bulb temperature, shortwave radiation, wind and apparent temperature (*provider claim:* probe of 13 Oct 2026, one request, HTTP 200).
* **A venue gazetteer to build:** 211 frame venue names (265 tour × name pairs) and 816 Challenger names (Stage 0, 2012 on); cities are in `data/dump/points/wta/editions.parquet` and `data/dump/matches/open_tennis_data/tournaments.parquet`. Start times are on disk (§ 3.2).
* **A validation label for women** (observed): the WTA umpire log flags heat breaks in 22, 21, 14, 17, 23, 52, 38 and 32 matches a year, 2019–26.

**Overlap.** None; pool row U-196 (not held; register C01, untested). **2025–26 exposure:** no.

**The test and its likely resolution.** Discovery on 2013–24 for men, women from 2018 (start times). Declared direction: in heat, the better-acclimatised player beats the close. Hot outdoor sessions are perhaps a tenth of matches (inferred; to measure), so only a strong effect resolves on Look A. The 2026 heat rules may damp it (*provider claim* via edge_anatomy's scout: an ATP cooling break at WBGT ≥ 30.1 °C from 2026).

**What would kill it.** No heat gradient in discovery; or reanalysis error too large to rank sessions (check WBGT against the WTA heat-break label and the Slams' published temperatures).

### 3.4 Style-specific ageing (RB10; RB11 as a companion)

**Definition.** Drift_X = (age_X − 29)+ × RS_X, with RS_X = D̄/(|Ō| + |D̄|), Ō and D̄ the means of X's standardised per-surface IOS offence and defence values (the store's per-player `pp__ios_srfO_*`, `pp__ios_srfD_*`, on the leak-proof IOS), optionally × the profile's effective memory; x = Drift_A − Drift_B. **RB11** adds career mileage beyond age from full careers (Stage 0 starts in 2010; U-158's tie was flagged as an artefact of that truncation).

**Mechanism.** Return and movement skills fade earlier than serving (*recalled*; check outcome-free first: per-statistic year-on-year change by age on box scores of seasons ≤ 2024). The long-memory profile still carries an ageing returner's younger seasons, and the model, seeing age only as A − B, cannot form A's age × A's style.

**Why the close would miss it** (inferred). edge_anatomy finds age itself unpriced (older men do worse than priced, z −3.3, 2013–24); a curve that depends on style is a finer judgement than "he is 31".

**Data:** on disk. **Overlap:** medium (`age`, `iosD_*`). Pool: none (BOD-27, proposed 6 Oct, never built); height × age (U-294) is spanned by the inputs (novelty R² 0.958).

**Earlier evidence.** B-AGE (age × the form gap, a different construction) failed replication. **2025–26 exposure:** partly (age's 2025–26 ledger reading, men z −2.0).

**The test.** Discovery on 2013–24, men primary (31% of men's player-matches are by players aged 30+, 2013–21); its broad prevalence resolves better than the others. **A tension:** edge_anatomy's 2025–26 "returners under-rated" points the other way for older returners; discovery on ≤ 2024 decides.

**What would kill it.** No style difference in the outcome-free ageing curves; or R² with the inputs of 0.5 or more.

### 3.5 Qualifier and lucky-loser arrival cost (RB13)

**Definition.** For a qualifier or lucky loser (LL) in the first main-draw match: Qcost = log1p(points played in this event's qualifying, from box-score denominators); Qrest = hours since the qualifying final ended (§ 3.2); LL = 1 for a lucky loser. x = Qcost_A − Qcost_B (0 for direct entrants); secondary LL × U-138.

**Mechanism.** The market prices the tag: the qualifier entry beats surface Elo (men +0.40) but ties at the close (U-176). It does not price what the run cost or how short the rest was. **The LL contrast:** lucky losers have on-site rhythm but lost their last match, so if LLs carry U-138's effect, the effect is rhythm, not survival.

**Data** (observed): on disk; a qualifier or LL plays in 19–31% of frame matches; their rest has a lower quartile of 24 h and a median of 41 h.

**Overlap.** Medium (`sets_14d` and U-138 count qualifying). Pool: U-176, U-138, U-276 (qualifying form, inside B-INFO, never screened alone). **2025–26 exposure:** partly (U-176 was scored on windows that include 2025–26).

**The test.** Discovery on 2013–24; the cost is two-sided (fatigue − against match-tightness +). **What would kill it:** nothing beyond U-138 and `sets_14d`.

### 3.6 Shorter notes

* **Conditions-matched rust (RB17)** recomputes `surf_layoff` from matches with the same indoor status, a similar court pace (the leak-proof venue pace, U-192) and the same altitude band. Its priors are negative (B-SWITCH p 0.31; acclimatisation × novelty +0.10): keep it only if it beats `surf_layoff` on ≤ 2024.
* **Health beyond results (RB15, RB16, RB09):** a retirement or walkover given at any level in the last 28 days without a long break since (on disk; U-160 tied, but on a history cut to the main tour), and withdrawals for injury from Wikipedia entry lists (download). Both are rare: worth testing only as a bundle.

## 4. Data to obtain

| Data | Route | Cost | Serves |
|---|---|---|---|
| Hourly weather | Open-Meteo archive (free, public; probe OK) | about 1,000 locations; a few thousand requests | RB07, RB08 |
| Venue gazetteer (coordinates, elevation, time zone) | city names on disk (WTA editions, open-tennis-data, TennisLive events), plus GeoNames or Wikidata | about 1,000 venues, mostly automatic | RB07, RB17–RB19 |
| Women's doubles before 2018; men's doubles days 2013–17 | WTA API earlier seasons; tour results archives | moderate | RB01 |
| Withdrawals with reasons | Wikipedia event pages; ATP and WTA entry lists | about 1,800 pages | RB16 |
| Careers before 2010 | Sackmann's public archive | small | RB11 |
| Distance run beyond the US Open | Slam feeds, Court Vision | to scope | RB21 |
| Live doubles results and orders of play | the TennisLive collector; tour schedule pages | a small scraper | RB01 and RB03 at bet time |

Paid data: none needed.

## 5. Cautions for the lead and the red team

1. **Stale lines and late information** (observed: `data/studies/bet_timing/frame.parquet`, `h_bol_close`). BetOnline's recorded last line comes a median 0.3–0.7 h before the start, but more than 6 h before for 10–15% of 2023–26 matches and more than 12 h before for 4–7%. A late finish, the day's heat and last night's doubles can all postdate it. *Suggestion:* register these statistics with a line-time filter (the frame has `t_bol_close` and `prev_lf_a/_b`), and read Pinnacle's close (to 7 Sep 2025) as the cleaner benchmark.
2. **Women's clock times cover 37–39% of matches before 2018:** the hours ideas are effectively men-only before then.
3. **Flashscore's end times are mostly missing for men's 2025–26.** Start plus minutes replaces them; use that same rule in discovery, or the measurement shifts between windows.
4. **Doubles:** a covariate shift (matches where either man had played doubles in the 7 days before fell from 0.47 in 2018 to 0.27 in 2025–26); TennisLive's lower-level doubles (ITF from 2020) enter mid-window, so a player's 7-day count can rise from 2020 for coverage alone (tour-level doubles rows are stable); name mapping covers 95.8% of member-rows; the order within a day is unknown; men's 2013–17 data is event-level only.
5. **Scheduled against listed starts.** At bet time the start is scheduled; history holds listed or actual times. Quantify the mismatch (the WTA API flags estimated starts).
6. **Builds for the look use 2025–26 results of earlier matches** (retirements, the IOS): normal for a feature at look time, but keep the discovery build cut at 2024.

## 6. Bundles I would offer as lead groups

| Bundle | Members |
|---|---|
| **Match play the singles record misses** | RB01, RB02, RB24, plus U-138 from the pool and RB13's LL contrast |
| **Recovery in hours** | RB03, RB04, RB05, RB06 |
| **Adaptation to conditions** | RB07, RB08, RB17, RB19 |
| **The body's own clock** | RB10, RB11, RB12, with U-296 from the pool |
| **Health beyond results** | RB15, RB16, RB09 |

## 7. My expectations, before any result

1. **Doubles:** positive at the 7-day horizon on both tours (rhythm), and null or negative for previous-day doubles late in the week. Stronger at 250s and 500s, and for women.
2. **Rest:** a cost only below about 18 hours; the gap adds little beyond that tail.
3. **Heat × acclimatisation:** positive, concentrated in January (Australia) and July–August (North America); men more than women (best of five).
4. **Style-specific ageing:** negative for older returners, men only.
5. **Lucky losers** carry U-138's effect as much as qualifiers: rhythm, not survival.
6. **Most ideas read "unresolved" alone on Look A;** a bundle has a chance.

## Sources

* **Open-Meteo historical weather API**, `https://archive-api.open-meteo.com/v1/archive`. Probed 13 Oct 2026, 15:04 UTC; the receipt and SHA-256 are in `data/studies/unpriced_leads/team/rhythm_body/probes/`.
* **The ATP heat rule from 2026.** A provider claim cited by edge_anatomy's scout: [Free Malaysia Today](https://www.freemalaysiatoday.com/category/sports/2025/12/16/atp-to-introduce-new-heat-policy-from-2026-season), accessed 12 Oct 2026 by that agent; not re-checked.
* **Recalled, not verified:**
  * Reyner and Horne (2013), sleep restriction and serving accuracy, *Physiology & Behavior*;
  * Périard, Racinais and Sawka (2015), heat acclimation, *Scandinavian Journal of Medicine & Science in Sports*.
