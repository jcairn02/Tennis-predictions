# Lane B: Grand Slam official scoring feeds and other official event sites (24 Sep 2026)

All probes ran on 24 Sep 2026, 15:37–16:15 UTC. Research only: no sign-up, login, form, purchase, CAPTCHA, forged token or decryption. Every probe was a single request; nothing was bulk-downloaded; every saved file was under 5 MB and kept in the session scratchpad; the repository was not modified by this lane. 7 WebSearch calls. The full request log (301 rows, with User-Agent and Referer for each) is copied to [`../probe_logs/B_slams_probe_log.tsv`](../probe_logs/B_slams_probe_log.tsv), endpoint families in [`../probe_logs/B_slams_probe_families.txt`](../probe_logs/B_slams_probe_families.txt), and the per-draw "H" counts in [`../probe_logs/B_slams_coverage_table.json`](../probe_logs/B_slams_coverage_table.json).

**Labels:** [observed] fetched and seen; [provider claim] the operator says so; [third-party report] press or another repo; [search excerpt] search snippet only; [inference] reasoning; [not stated].

**What the project already holds** [observed in the staged dump]: Slam main-draw singles 2011–2024 (AO and RG to 2021, no Wimbledon 2020), plus doubles and mixed files for AO and RG 2018–2021, US Open 2019–2024 and Wimbledon 2019 and 2021–2023. No qualifying anywhere (every held `match_num` is below 10000), no Wimbledon 2024 doubles, and no per-point Unix timestamps.

## 0. Bottom line

1. **Older Wimbledon feeds are still online** [observed], which overturns the 23 Sep note that Wimbledon 2024 was unreachable. `https://2025.wimbledon.com/en_GB/scores/feeds/{year}/…` serves draws, point histories and match statistics for **2019 and 2021–2025**; 2018 returns 404; 2026 is on `www.wimbledon.com`. Qualifying is 112/112 (or 111/112) "H" in every one of those years, and sampled qualifying matches have point histories. Before 2025, qualifying had no electronic line calling: those histories carry the point outcome, stroke side and timestamps, but no speed, placement or distance; rally count appears in 3 of 5 samples.
2. **US Open covers 2022–2026 only** [observed]. 2019, 2020 and 2021 return 404 on `www.usopen.org` and on `2024.usopen.org` (the only year subdomain that resolves). The Wayback Machine has 18 US Open history captures for 2019 and 2021.
3. **The official feeds add per-point fields that even held editions lack** [observed] (US Open 2022–2024, Wimbledon 2019 and 2021–2024): `EpochTimeStart` and `EpochTimeEnd` (Unix seconds, filled on 100% of points in every sample 2019–2026); `KickHeight`; `Sentence`, which names the stroke and the error type ("backhand volley forced error", "forehand smash winner"); `TeamOrientStart/End`, `Court`/`CourtIndicator`, `PointID`, `P1/P2DistanceRunTotal`, `Stage`, `ChallengeWon` (Wimbledon only). The timestamps would allow an exact join to market price histories [inference].
4. **Four feeds not in the 23 Sep notes** [observed]: US Open 2026 limb tracking (serve biomechanics per player, per match and per set, singles main draw only); IBM live likelihood-to-win (one row per point, US Open 2025–26 and Wimbledon 2025–26, singles main draw); US Open 2026 key moments; TennisViz Shot Quality / In Attack / Conversion / Steal per set for Wimbledon 2024–25 singles.
5. **Australian Open: only 2026 is served** [observed]: 604 matches (MS 127, WS 127, MQ 112, WQ 112, MD 63, WD 63). Each point has commentary and a Unix timestamp, but no per-point speed, rally or serve number. 2022–2025 are gone from the API; the Wayback Machine has 65 match-centre captures for 2022–2025. Infosys MatchBeats files exist for 2022, 2025 and 2026 but are encrypted blobs (not decoded).
6. **Roland-Garros: no plain-text point-level route** [observed]. Match pages carry a box score only; Court Vision returns 403 (plain and with a Chrome UA plus Referer); MatchBeats is encrypted, both as a static file and in 957+ archived Wayback captures.
7. **Rights: all four Slams' terms prohibit automated extraction and/or commercial use** [observed; quotes below].
8. **Other official events: none has rich public per-point data.** United Cup: ATP box score only. Davis Cup and Billie Jean King Cup: client-rendered pages with no statistics found. Olympics: olympics.com timed out. Laver Cup: no public statistics.
9. **Time-sensitive** [inference]. The AO API already calls itself "AusOpen 2027 / Pre-tournament" but still serves 2026; since 2025 has already disappeared, 2026 will probably vanish in January 2027. The `2025.wimbledon.com` archive host could be retired at any time.

## 1. Leads

### Lead 1: Wimbledon IBM SlamTracker feeds, 2019 and 2021–2026, including qualifying and doubles

- **URL templates** [observed]: years 2019 and 2021–2025 `https://2025.wimbledon.com/en_GB/scores/feeds/{year}/…` with `draws/{EV}.json` (EV = MS, LS, QS, RS, MD, LD), `slamtracker/history/{id}C.json`, `matches/complete/{id}.json`. The config names the template: `"matchStatsPath": "https://2025.wimbledon.com/en_GB/scores/feeds/<match_year>/matches/complete/<match_id>.json"`. 2026: the same paths on `www.wimbledon.com`, except that the 2026 `draws/MS.json` and `draws/LS.json` return **302 → /robots.txt** (an Akamai redirect; not worked around; `completed_matches/days/day_{n}.json` used for match lists instead).
- **Granularity:** point level plus per-point fields derived from tracking. No raw ball or player coordinates.
- **Per-point fields** [observed; 57 keys in 2026, 52–54 in 2019–2023]: `ElapsedTime, MatchID, SetNo, GameNo, PointNumber, ServeNumber, Stage, History, Sentence, EpochTimeStart, EpochTimeEnd, MatchWinner, SetWinner, GameWinner, PointWinner, PointServer, ServeIndicator, P1Score, P2Score, P1GamesWon, P2GamesWon, P1PointsWon, P2PointsWon, P1SetsWon, P2SetsWon, PointTrack, SetTrack, P1Momentum, P2Momentum, Rally20OrMore, Deuces5OrMore, ChallengeWon, Ace, Winner, DoubleFault, UnforcedError, NetPoint, BreakPoint, BreakPointWon, BreakPointOpportunity, Speed_KMH, Speed_MPH, WinnerType, WinnerShotType, Court, CourtIndicator, TeamOrientStart, TeamOrientEnd, P1DistanceRun, P2DistanceRun, P1DistanceRunTotal, P2DistanceRunTotal, RallyCount, ServeWidth, ServeDepth, ReturnDepth, KickHeight`
- **Fields not in the held archive:** `EpochTimeStart`, `EpochTimeEnd`; `KickHeight` (e.g. "1.3,4.3", probably metres and feet [inference]); `Sentence`; `TeamOrientStart`, `TeamOrientEnd`; `Court`, `CourtIndicator` (D/A, probably deuce/ad side [inference]); `ChallengeWon`, `Stage`, `PointTrack`, `SetTrack`; `Rally20OrMore`, `Deuces5OrMore`; `P1/P2DistanceRunTotal`; `MatchWinner`, `P1/P2SetsWon`, `MatchID`. `Ace`, `Winner`, `DoubleFault`, `UnforcedError` and the break-point fields store the player number (the raw form of the held `P1Ace`/`P2Ace`-style flags [inference]). Forced error has no field of its own and appears only in `Sentence`.
- **Match statistics file:** `base_stats`, `serve_stats` (first- and second-serve average and fastest speeds), `return_stats`, `rally_stats` (winners, forced and unforced errors by stroke family), `dss` (serve speed and points won by serve 1st/2nd × ad/deuce × wide/body/T), `serves`, `distance_run`. The 2026 file shows `"statsLevel": "K"` (meaning not stated).
- **Coverage: "H" matches / matches in draw** (bold = not held):

  | Year | MS | LS | QS | RS | MD | LD |
  |---|---|---|---|---|---|---|
  | 2019 | 127/127 (held) | held | **112/112** | **112/112** | held | held |
  | 2021 | 126/127 (held) | held | **112/112** | **112/112** | held | held |
  | 2022 | 125/127 (held) | held | **112/112** | **111/112** | held | held |
  | 2023 | 127/127 (held) | held | **112/112** | **112/112** | held | held |
  | 2024 | 125/127 (held) | 127/127 (held) | **112/112** | **112/112** | **62/63** | **62/63** |
  | 2025 | **127/127** | **127/127** | **112/112** | **112/112** | **62/63** | **61/63** |
  | 2026 | draw blocked; round 1 days 1–2: **61/61 H** | draw blocked; round 1 days 1–2: **64/64 H** | **112/112** | **112/112** | **61/63** | **62/63** |

  Samples [observed]: main draw has tracking fields (2026 MS 1101: speed on 275/285 points, `KickHeight` 282/285, epoch 285/285; 2019 MS 1101: epoch 176/176). Pre-2025 qualifying (2022 RS 12101, 2024 QS 11101, 2019 RS 12102, 2021 QS 11217, 2023 RS 12215): speed, width, distance and `KickHeight` 0 on every point; epoch on 100%; `RallyCount` filled in 3 of 5. 2024 doubles (MD 3101): epoch 91/91, rally 88/91, no speed.
- **New matches** [inference]: about 1,119 qualifying matches from 2019 and 2021–2024; 124 doubles from 2024; about 601 in 2025; about 601 in 2026. **Total ≈ 2,445**, plus the new fields on about 1,260 held main-draw singles matches.
- **Access** [observed]: public, unauthenticated JSON, 150–480 KB per history. `robots.txt` does not disallow `/en_GB/scores/feeds/`. *Correction, later the same day:* that holds for `www.wimbledon.com`. The `2025.wimbledon.com` archive host's robots.txt is `Disallow: /` for every agent; see [access routes](../../../../docs/research/granular-data-leads/access-routes.md).
- **Terms** [observed]: AELTC Digital Platforms Terms of Use (`https://2025.wimbledon.com/en_GB/cms/feeds/about_wimbledon/acceptable_use_policy.xml`; effective date not stated): "6.2 You must not use any part of or any content obtained from an AELTC Digital Platform for commercial purposes without first obtaining a licence from AELTC or from AELTC's official licensors"; "6.3 You may print one copy of, and/or may download extracts of, any page(s)… provided that: (i) such extracts are used only by you for personal, non-commercial purposes"; "11.2 You agree not to reproduce, duplicate, copy or re-sell any part of an AELTC Digital Platform…"; "You agree not to use any AELTC Digital Platform for any commercial or business purposes". Machine learning not stated.
- **Other evidence** [observed]: `…/2024/slamtracker/history/1101C.json` is 406,556 B with epoch on 240/240 points; 2018 returns 404; the www host returns 403 for the 2024 history.
- **Confidence:** high technically; low to medium on rights.

### Lead 2: US Open IBM SlamTracker feeds, 2022–2026

- **URL templates** [observed]: `https://www.usopen.org/en_US/scores/feeds/{year}/` with `draws/{EV}.json`, `slamtracker/history/{id}C.json`, `matches/complete/{id}.json`, `slamtracker/distance/{id}.dist.json`. 2024 is mirrored on `2024.usopen.org`. Plain `curl` gets "Connection was reset"; a Chrome User-Agent gets 200.
- **Fields:** as Lead 1, except `PointID` present and `ChallengeWon` absent. `Sentence` values seen: "forehand volley winner", "forehand smash winner", "service winner", "backhand volley forced error", "forehand smash unforced error", "fails to convert the break point…", "saves the break point…".
- **Coverage: "H" / in draw** [observed]:

  | Year | MS | WS | MQ | WQ | MD | WD |
  |---|---|---|---|---|---|---|
  | 2022 | 126/127 (held) | 126/127 (held) | **43/112** | **39/112** | held | held |
  | 2023 | 127/127 (held) | 126/127 (held) | **41/112** | **39/112** | held | held |
  | 2024 | 127/127 (held) | 126/127 (held) | **41/112** | **44/112** | held | held |
  | 2025 | **126/127** | **126/127** | **67/112** | **64/112** | **63/63** | **63/63** |
  | 2026 | **127/127** | **127/127** | **111/112** | **112/112** | **61/63** | **62/63** |

  8 of 8 sampled "H" qualifying matches had 87–176 points; 2 of 2 sampled "S" matches were empty; the 23 Sep pass found one match "H" in the draw but "S" in its statistics file with an empty history, so "H" can slightly overcount. Serve speed present in all sampled "H" qualifying matches; `RallyCount` 0 in the 2022 samples, mixed in 2023–2024, filled in 2025; 2022 MS 1101: epoch 145/145, `KickHeight` 125/145.
- **New matches:** 247 qualifying matches 2022–2024, 509 in 2025, 600 in 2026: **1,356**, plus new fields on about 1,130 held main-draw matches.
- **Terms** [observed]: `https://www.usopen.org/en_US/cms/feeds/general_content/terms.xml`, "Last revised: April 30th, 2024": "The USTA grants you a limited license to access and make personal, non-commercial use of the USTA Site." Contents "(including, without limitation rankings, tournament scores and standings)… may not… be reproduced… downloaded… repurposed… or otherwise exploited for any commercial or competitive purpose without our prior express written consent." "You shall not use the USTA Site in a manner that… (iii) results in the scraping or copying of information, data, or content, or (iv) circumvents or overrides security features." Machine learning not stated.
- **Confidence:** high technically; low to medium on rights.

### Lead 3: US Open 2026 limb-tracking serve biomechanics

- **URL:** `https://www.usopen.org/clouddata/limbtracking/2026/match/{id}.json` [observed; listed in the config under `limbTracking`].
- **Granularity:** aggregated per match and per set for each player; the best serve in each set is given with its `point_number`. No per-serve array (guessed `point/` and `set/` paths return "notfound").
- **Fields** [observed, union of 7 files]: header `insight_type` ("serve quality"), `resolution_type` ("match"), player ids and names; per player `insight` (text), `match_summary.{average_serve_quality, average_efficiency_score, average_effectiveness_score, total_serves}`; `standout_metrics` by phase: `toss.{apex_height_norm, drift_horizontal_ft, drift_total_3d_ft, toss_to_contact_s}`, `loading.{min_knee_angle, pelvis_rise_pct, hip_shoulder_sep}`, `cocking.{elbow_flexion_at_mer, trunk_extension_at_mer}`, `acceleration.{chain_order_fraction, hip_shoulder_timing_ms, peak_knee_ext_velocity, peak_racket_speed_mph}`, `contact.{contact_height_norm, elbow_flexion, front_knee_angle, lateral_flexion, shoulder_abduction}`, `effectiveness.{serve_in_count, serve_in_pct, is_ace_count, is_ace_pct, avg_ball_speed_mph, avg_bounce_placement_dist_ft}`; per set `set{N}_summary.{average_serve_quality, best_serve_quality.{serve_quality, insight, point_number}}`. Only each player's "top phases" are included, so phase metrics are incomplete.
- **Coverage** [observed]: 7 of 7 sampled 2026 singles main-draw matches, including outer courts 7, 10 and 12; none for qualifying, doubles or 2025. About 254 matches [inference].
- **Evidence:** sample insight [observed]: "Lorenzo Sonego's 77% serve quality score featured a controlled toss and good racket preparation. His serves landed 1.4 feet from the target zone on average, with 73% going in." Fortune, 12 Sep 2026 [third-party report, via the web-fetch summariser]: "Serve scores like this are available for every singles match in the tournament – only after completion."; "21 limbs and joints"; "production-ready for Wimbledon" possible.
- **Confidence:** high that the files can be obtained; low data density.

### Lead 4: IBM live likelihood-to-win per point, key moments and pre-match likelihood

- **URLs** [observed]: live L2W `https://www.usopen.org/clouddata/livel2w/{2025|2026}/{id}C.json`, `https://2025.wimbledon.com/clouddata/livel2w/2025/{id}C.json`, `https://www.wimbledon.com/clouddata/livel2w/2026/{id}C.json`; key moments `https://www.usopen.org/clouddata/keymoments/key_moment/2026/{id}.json`; pre-match `https://www.usopen.org/clouddata/likelihood-to-win/2026/{id}.json`.
- **Fields** [observed]: live L2W `point_number, live_l2w_p1, live_l2w_p2, p1_l2w, p2_l2w, p1_score, p2_score, p1_games_won, p2_games_won, p1_sets_won, p2_sets_won, support_stats.{p1/p2_points_needed, p1/p2_points_to_next_set_win, p1/p2_points_to_next_game_win, p1/p2_momentum_percent_scaled, serve_indicator}, created_epoch, created_time`; key moments `insight_importance, moment_type, point_number, factual_insight, insight, set_number, created_epoch`; pre-match `predicted_winner, likelihood_to_win`.
- **Caveats** [observed]: `created_epoch` lags the point's `EpochTimeEnd` by a median of 63 s (10th percentile 36 s, 90th 133 s, max 510 s): join on `point_number`, not time. The Wimbledon file at a "2024" path (Sinner vs Hanfmann) was generated on 2025-05-27, a replay rather than a live 2024 record.
- **Coverage** [observed]: US Open 2025–2026 singles main draw (absent for qualifying and 2022–2024); Wimbledon 2025–2026; config `"l2wEvents": ["A","B","WS","MS"]` indicates singles only.
- **Confidence:** high; model output rather than raw data, but a ready in-play benchmark [inference].

### Lead 5: Australian Open 2026 match-centre API, plus 2022–2025 Wayback captures

- **URLs** [observed]: `https://prod-scores-api.ausopen.com/match-centre/{MID}` (no year in the id; `?year=` ignored); `https://prod-scores-api.ausopen.com/event/{nid}/draws` (2026 event ids: MS 257391, WS 257400, MQ 257390, WQ 257399, MD 257388, WD 257397); `https://prod-scores-api.ausopen.com/year/{Y}/period/{MD|Q}/day/{d}/results`.
- **Per-point fields** [observed]: `commentary[]` with `id` (e.g. `MS701-004-012-005`), `timestamp` (Unix), `commentary`, `set`, `winner`, `score`, `type`, `duration`, `games_score`, `is_game_complete`. Timestamps span 181.7 minutes against a listed match length of 3:02. Commentary vocabulary: Forehand/Backhand × Winner / Forced Error / Unforced Error, Ace, Double Fault, Service Winner. No stroke subtype, speed, rally count or serve number per point. Per-set aggregates include "Fastest serve", "1st Serve Average", "2nd serve average", and FH/BH winners and unforced errors by GroundStroke/Volley/Approach/Passing/Lob/Overhead/Drop.
- **Coverage** [observed]: 2026: 604 matches in the six events; 9 of 9 sampled files had commentary and timestamps (MS101, MS123 on Court 13, MS701, WS120, MD101, WD101, WQ101, plus MQ109 and MQ129 from 23 Sep). 2022–2025: the API returns "No Results", "No Draws" or "match id not found"; the Wayback CDX has 65 captures (MS 39, WS 15, MD 2, WD 1, WQ 1, ED 6, CS 1); the archived 2024 final is complete with 283 point rows.
- **Terms** [observed; Tennis Australia "Conditions of Use – Online Systems", read from a Wayback copy dated 1 Jan 2026 because the live page returns 403]: users must not "(g.) collect content from any Online System using automated means (such as harvesting bots, robots, spiders, or scrapers)"; "no material from an Online System may be distributed or copied for any commercial purpose"; material may be reproduced "solely for your personal (non-commercial) education or information."
- **Confidence:** AO 2026 high today but at risk; AO 2022–2025 low.

### Lead 6: TennisViz Shot Quality / In Attack, Wimbledon 2024–2025

- **URL:** `https://2025.wimbledon.com/clouddata/tz/{year}/{id}.json` (bucket `tennisviz-prd`) [observed].
- **Fields** [observed]: `insights.{in_attack, serve_quality, return_quality, forehand_quality, backhand_quality}`, each with `.match.{set1..set5,total}.{p1,p2,neutral}`, `.player_average`, `.championship_average`; `ai_selected.{in_attack, shot_quality.{serve,return,forehand,backhand}, conversion, steal}`. Config tooltip: Shot Quality is "calculated in real time by analysing each shot's speed, spin, depth, width, and the impact the shot has on the opponent."
- **Coverage** [observed]: present for 2025 MS 1101, MS 1219, LS 2101 and 2024 MS 1101; absent for qualifying, all of 2026 (404 `NoSuchKey`), and the equivalent US Open path.
- **Confidence:** medium; aggregate only.

### Lead 7: IBM SlamTracker 3D (Immersiv), likely trajectory data, not accessed

- **Observed:** `3d.usopen.org` ("IBM SlamTracker 3D") is a Unity WebGL app served from `us-open-prod.r2.immersiv.cloud`; its loader pulls Firebase auth and Firestore from `https://us-open-prod.firebaseio.com`; the config's `immersivConfig` enables "View in 3D" on all 17 match courts. [search excerpt] The usopen.org SlamTracker page describes it as letting you "follow ball positions in real-time." Wimbledon's config has no 3D feature.
- **Not accessed:** reading it would mean opening a Firebase Auth session (likely anonymous sign-in), beyond single public requests and against the US Open terms ("circumvents or overrides security features").
- **Confidence: low.** The likeliest source of trajectory data at the US Open; only via USTA, IBM or Immersiv.

### Lead 8: Infosys MatchBeats and Court Vision (AO and RG, 2018–2026), encrypted

- **Endpoints** [observed, from the public bundles `itp-ao-sls…/itp/prod/ao/match-centre/main.js` and `itp-rg-sls…/itp/prod/rg/match-centre/main.js`; tournament ids 580 (AO) and 520 (RG)]: `/static/prod/match-beats/#year/#eventId/#matchId/data.json`; `/prod/api/court-vision/year/#year/eventId/#eventId/matchId/#matchId/pointId/#pointId`; `/prod/api/rally-analysis/…`, `/prod/api/stroke-analysis/rally/v2/…`, `/prod/api/stats-plus/v1/keystats/…`; RG only `/prod/api/patterns-of-play/…`, `/prod/api/match-momentum/data/…`.
- **AO** [observed]: Court Vision plain request CloudFront "403 ERROR The request could not be satisfied"; with Chrome UA + Referer ausopen.com, S3 `AccessDenied`; all `/prod/api/*` 403; MatchBeats static files for 2022, 2025 and 2026 return 200 (110–211 KB) but contain `{"lastModified":…,"response":"unJ0PxRr…"}`, an encrypted blob.
- **RG** [observed]: Court Vision API 403 plain and with Chrome UA + Referer rolandgarros.com; MatchBeats 2022 static file encrypted; Wayback CDX (hit its 5,000-row limit): 957 unique MatchBeats-data URLs across 2018–2026 (426 from 2024) plus 48 Court Vision URLs; archived samples (2022 SM008, 2019 SD096) also encrypted. RG match pages carry only the box score in their Nuxt state; RG's own API (`/api/{lang}/…`) returns lists only.
- **RG terms:** "The User is prohibited from using any software, device, robot, script, program, automated means, other process or technological technique to extract any information, data or content from the Website."
- **Confidence: low.** Only through a licence.

### Lead 9: Wimbledon Match Archive (minor)

- 49 classic matches from 1977 to 2019, listed at `https://2025.wimbledon.com/en_GB/cms/feeds/archives/matchArchives.json`; point data at `…/json/man/scores/archive/{id}.json` (e.g. `2013W2601`) with `epochTimeStart`. Negligible volume.

## 2. How much each Slam adds

"H" matches in events not held; "width" = new fields on matches already held.

| Slam | Edition | New point-level matches | Tracking-derived fields | Width on held matches |
|---|---|---|---|---|
| US Open | 2022 / 2023 / 2024 | 82 / 80 / 85 (qualifying) | yes; rally count patchy | about 375 per year (singles + doubles) |
| US Open | 2025 | 509 (all six events) | yes, plus L2W | — |
| US Open | 2026 | 600 | yes, plus limb tracking and L2W | — |
| Wimbledon | 2019, 2021, 2022, 2023 | about 224 per year (qualifying) | qualifying: none | about 253 singles per year, plus doubles |
| Wimbledon | 2024 | 348 (qualifying + doubles) | qualifying none; doubles partial | 252 |
| Wimbledon | 2025 | 601 | yes, plus L2W and TennisViz | — |
| Wimbledon | 2026 | about 601 | yes, plus L2W | — |
| Australian Open | 2022–2025 | about 65 (Wayback) | no | — |
| Australian Open | 2026 | 604 | no (per-set speed only) | — |
| Roland-Garros | 2022–2026 | 0 in plain text | — | — |

**Total ≈ 4,470 new point-level matches** [inference], about 1,270 of them 2025–2026 main-draw singles at the US Open, Wimbledon and AO; new fields on about 2,400 held matches.

## 3. Dead ends

- US Open 2019, 2020, 2021: 404 on www and on `2024.usopen.org`; subdomains 2019–2022 and 2025 `.usopen.org` do not resolve; Wayback has 18 captures for 2019/2021.
- US Open config feeds that failed: 404 for `slamtracker/keys`, `keys`, `charts/U_…_3keys.xml`, `completed_matches/match_stats_{id}`; "notfound" for `match-insights`, `match-insights/power-rankings`, `win-factors`; `api/tennis/matches/match/{id}` returns the HTML app shell; `keymoments` 2025 and `livel2w` 2022–2024 absent. The US Open Power Index (`wpi_latest.json`) is player-level and daily, not point data.
- Wimbledon subdomains 2021–2024 and 2026 `.wimbledon.com` do not resolve; the 2018 feed returns 404; the www host returns 403 for 2024; the 2026 MS/LS draw files redirect to robots.txt (not bypassed); `limbtracking` and `keymoments` 2026 return NoSuchKey.
- AO: the results API for 2022, 2024 and 2025 returns "No Results"; old event draws return "No Draws"; lookup by uuid returns "match id not found"; `/year/2025/match-centre` returns 403 "Missing Authentication Token"; all Infosys API endpoints return 403.
- RG: `/api/en-us/matches/2026/SM001` returns 404; `/api/en-us/finished` gives only day and match lists; the Infosys commentary API returns 403.
- United Cup: `https://www.unitedcup.com/-/tournaments/matchStatsApi/MatchStats?year=2026&eventId=9900&matchId=ms011` returns an ATP box score only.
- Davis Cup: Next.js pages on the ITF/Stadion backend; no statistics in the HTML and no data API found. BJK Cup not checked separately (probably the same platform [inference]).
- Olympics: the Paris 2024 results page on olympics.com timed out for curl and WebFetch.
- Laver Cup: lavercup.com (WordPress) has no score or statistics data and links to atptour.com.
- Kaggle `alessiore02/point-by-point-dataset` (224 MB, 2026-08-23, licence "Unknown"): a Sackmann copy of editions already held (2014–2024).
- Kaggle, Hugging Face and GitHub searches for 2022–2026 AO/RG/USO/Wimbledon point data: only the known Wimbledon 2023/24 derivatives and Sackmann mirrors.
- GitHub code search for `"slamtracker/history"`: 9 hits, small 2026 projects calling the live US Open feed plus the 2017-era `skoval/deuce` scraper (`http://{YEAR}.{slam}/…/xml/gen/slamtracker/history/`). None publishes a dataset.

## 4. Probe log (condensed; full log in `../probe_logs/B_slams_probe_log.tsv`)

| UTC | URL | Status | Bytes | Finding |
|---|---|---|---|---|
| 15:37:58 | usopen.org config_web.json, curl UA | 000 | 0 | connection reset |
| 15:38:44 | same, Chrome UA | 200 | 13,831 transferred | limbTracking, liveL2W, keyMoment and 3D entries |
| 15:39:38–40 | usopen `feeds/{2019..2026}/draws/{MS,WS,MQ,WQ,MD,WD}` (36 requests) | 404 for 2019–21; 200 for 2022–26 | 113k–357k | statsLevel shares |
| 15:40:49 | usopen 2026 `history/1101C` | 200 | 38,186 transferred | 344 points, epoch on all |
| 15:42:01–12 | usopen limbtracking, keys, likelihood-to-win, livel2w, keymoments for 2026/1101 | 200 / 404 | 180–310,325 | leads 3–4 |
| 15:42:54–15:43:30 | usopen limbtracking and livel2w coverage (15 requests) | 200 or notfound | 3.5k–240k | coverage for leads 3–4 |
| 15:43:45 | wimbledon.com config (redirects to 2025 host) | 200 | 56,506 | tz feed; `<match_year>` template |
| 15:44:19–29 | www.wimbledon.com 2026 `draws/MS`, `draws/LS` | 302 → robots.txt | 500 | blocked; not bypassed |
| 15:44:39 | www.wimbledon.com 2026 `history/1101C` | 200 | 482,175 | epoch on all points |
| 15:45:05–46:03 | Wimbledon tz, livel2w, limbtracking, keymoments; 2025 host histories 2024/2023/2022/2021/2019/2018 | mixed; 404 for 2018 | 315–407k | archive host serves old years |
| 15:46:29–36 | 2024.usopen.org and www, 2019–2021 | 404 ×7 | 4,084 | US Open 2019–21 not served |
| 15:47:13–33 | Wimbledon 2024 and 2022 qualifying histories; 2026 days 8–9 | 200 | 156k–176k | qualifying without tracking fields; 2026 round 1 125/125 "H" |
| 15:48:51–59 | AO match-centre MS701/MS101; results 2026/2025/2024/2022 | 200 | 110–292k | AO 2026 only |
| 15:49:27 | itp-ao-sls `main.js` | 200 | 3,140,003 | Infosys templates |
| 15:51:56–57 | itp-ao-sls court-vision static, plain / Chrome UA + Referer | 403 / 403 (S3) | 919 / 263 | not readable |
| 15:52:08–22 | itp-ao-sls match-beats static 2026/2025/2022 | 200 | 110k–211k | encrypted blobs |
| 15:52:32–15:53:13 | Wayback CDX and the 2024 MS701 capture | 200 | 293–141k | 99 captures; full 2024 final |
| 15:54:12–56:34 | rolandgarros.com SM001 page and bundles; itp-rg-sls court-vision; match-beats 2022; Wayback CDX and captures | 200 / 403 | 3k–735k | box score; encrypted |
| 15:56:47–16:01:17 | unitedcup.com, daviscup.com, olympics.com | 200 / 404 / timeout | 0–411k | box score only / no statistics / unreachable |
| 16:02:29–16:04:31 | US Open, AELTC, Tennis Australia (Wayback) and RG terms | 200 | 9k–332k | terms quoted above |
| 16:04:57–16:07:30 | Kaggle, Hugging Face and GitHub APIs (36 requests) | 200 | 2–454k | §3 |
| 16:08:10–16:10:05 | width and qualifying samples (15 requests) | 200 (one 403) | 2.9k–341k | "H" has points; "S" empty |
| 16:11:15–37 | 3d.usopen.org, Immersiv config, Firebase loader | 200 | 1.2k–8.6k | Firebase; not queried |
| 16:12:37–16:13:20 | AO event draws ×6, day 4, uuid lookup, old event | 200 | 32–472k | 604 matches; old years gone |
| 16:14:52–54 | robots.txt for usopen.org, ausopen.com, rolandgarros.com | 200 | 77–2,111 | feeds not disallowed |

## 5. Leads passed to other lanes

- **ATP/Infosys:** the United Cup uses the ATP tournament platform's `/-/tournaments/matchStatsApi/MatchStats?year=&eventId=&matchId=` (box score); Infosys static MatchBeats files are reachable with a Referer but encrypted.
- **Markets:** Kaggle `oliviersportsdata/tennis-grand-slam-pinnacle-pure` ("Multi-Timestamped + 113 columns (2016-2026)", CC BY-NC 4.0, updated 2026-05-25) [observed metadata]; IBM L2W as an in-play benchmark [inference].
- **Features:** the US Open IBM Power Index daily file (`clouddata/power-rankings/2026/wpi_latest.json`) has `wpi_rank`, `performance_score`, `volume_score`, `sentiment`.
- **Vendors:** Immersiv (US Open 3D) and TennisViz (Wimbledon) are the tracking-derived suppliers behind these features; Hawk-Eye SkeleTRACK ran at the Laver Cup 2024 with data going to players; IBM limb tracking may reach Wimbledon (Fortune).
