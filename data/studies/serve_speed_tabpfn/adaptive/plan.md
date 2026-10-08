# Adaptive speed memory: 14 days when the speeds are in hand, 28 when they are late

**Written by the lead on 8 October 2026, before any computation of this step.** The design and the readings below are fixed now. The outcome readings are **exploratory**: 2024–26 results were already read (look ledger rows 34 and 40).

## The owner's request (8 Oct 2026)

> "can we program it such that IF WE HAVE the sources then we do what you are suggesting (the 14-day memory). Then IF WE DONT have the sources in time then it goes to 28-day memory?"

## The rule, fixed now

**Per match, at forecast time t.** In a backtest t is the match's `es`; live it is the moment of the forecast.

1. **A player is late** if one of his own earlier matches meets all of these:
   * it is expected to carry a speed;
   * it finished at least a day before t (`lf + 1 < t`, earlier by own order);
   * it falls within the last 14 days (`obs ≥ t − 14`);
   * its speed is not in hand at t.

   **"Expected to carry a speed"** means:
   * in a backtest: the match has a usable speed row in the panel (`use`);
   * live: its event is covered by a speed source whose publication watermark is earlier than the match day. That means a pending week of ManTennisData, a Slam whose feed is not yet collected, or a missed weekly commit. A match at an event with no speed (Barcelona, for example) is never late.
2. **The match's mode is T** (timely) when neither player is late, **otherwise L** (late).
3. **The two modes:**

   | Mode | Speed form | Standardised by | Coefficients (s_tour, b̃) |
   |---|---|---|---|
   | **T** | 14-day half-life (the study's filter) on the speeds in hand | s_f = 2.224 km/h | walk-forward on the **instant** history: the study's S9 (2026: s_atp 0.9007, b̃ 0.0389) |
   | **L** | 28-day half-life (latency B-M1) on the speeds in hand | 1.950 km/h (B-M1's SD) | walk-forward on the **today's-sources** history: the latency run's B-M1 (2026: s_atp 0.8996, b̃ 0.0376) |

4. **The forecast:** logit q = s_tour,mode · η + b̃_mode · column_mode. Women are unchanged (their speed column is 0).
5. **Refit and shrinkage.** Both coefficient sets are refitted each season on 2019..Y−1, from the history each mode was defined on, and shrunk with τ = 0.05, as decided.

**Why a 1-day grace.** A 1-day delay cost nothing in the latency run (L1 = 100% of instant). So a match that finished yesterday and is not yet in hand does not switch the mode.

## Checks and exploratory readings (fixed now)

**Availability scenarios** (from `latency/availability.parquet`, extended by the engineer):
* **A,** instant;
* **B,** today's sources: weekly ManTennisData, Slams after the event;
* **D,** a daily tour collector (`lf + 2`) with Slams after the event;
* **E,** weekly tour data with live Slam feeds (Slams at `lf + 2`).

**Arms in each scenario** (men 2024–26, 7,068 matches; mLL against the calibrated base, positive = better, block interval):
1. pure T;
2. pure L;
3. **the switch.**

**Required reproductions:**
* under A, the switch equals pure T equals S9: +0.410 [+0.045, +0.775];
* under B, pure L equals the latency run's B-M1: +0.38 [+0.11, +0.64].

**Reported:**
* the share of matches in each mode, per scenario;
* the switch against the better pure arm, paired, per scenario. Expected: the switch is at least as good as the better pure arm in every scenario, and better in the mixed ones (D, E).

**A descriptive variant:** one joint walk-forward fit of s, b̃_T and b̃_L under each scenario's own history, with the mode flags.

**The outcome run happens once,** after the builds pass their tests and the auditor's checks. It is logged in the look ledger.
