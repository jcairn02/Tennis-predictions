# Adaptive speed memory: switch to 28 days only when speeds are late?

8 October 2026 · A follow-up to the [serve-speed study](README.md) and its [latency check](latency.md). **Exploratory:** the design was fixed in [plan.md](../../../data/studies/serve_speed_tabpfn/adaptive/plan.md) before computing, and the outcome run was made once (look ledger row 45). 2024–26 results had been read before.

**Keys.** Gains are milli-log-loss (mLL) per match, men 2024–26 (7,068 matches). **Positive = the speed adjustment is better** than the calibrated model without it, unless a row says otherwise. Intervals are 95%; one that spans 0 is a tie.

## The request and what was built

> "can we program it such that IF WE HAVE the sources then we do what you are suggesting (the 14-day memory). Then IF WE DONT have the sources in time then it goes to 28-day memory?" (the owner, 8 Oct 2026)

**Built, tested and audited** (*observed*):
* **The rule, per match at forecast time.** A player is **late** if one of his own timed matches meets all of these:
  * it finished more than a day ago;
  * it falls within the last 14 days;
  * its speed is not yet in hand.

  If neither player is late, the match uses the **14-day memory** with its own coefficients (mode T). Otherwise it uses the **28-day memory** with its own coefficients (mode L).
* **Live, "not yet in hand"** comes from each source's publication watermark:
  * ManTennisData: the Friday before its latest Sunday commit;
  * a daily collector: yesterday;
  * a Slam feed: the last day collected.

  A match at an event that never records speed (Barcelona, for example) never counts as late.
* **Code:**
  * `src/eda/serve_speed_tabpfn/adaptive/columns.py`: both columns, the late flags and the mode;
  * `adjust.py`: the adjustment, its coefficient table and a command that scores a given date from data in hand;
  * `score_adaptive.py`: the comparison.
  * 96 tests pass.
* **The independent audit** ([4_audit.md](../../../data/studies/serve_speed_tabpfn/adaptive/4_audit.md)):
  * re-derived every men's late flag and mode in four scenarios, with 100% agreement;
  * confirmed the coefficients equal the published fits exactly, from seasons < Y only;
  * confirmed that the mode uses only clock and release days, never outcomes.

**How often each memory is used, men 2024–26:** the 28-day mode applies to 47% of matches with today's sources, 13% with a daily tour collector (Slams after the event), 34% with live Slam feeds but weekly tour data, and 0% with instant speeds.

## The result

*Observed* (`adaptive/results_adaptive.csv`). Both required reproductions held exactly: instant + switch = the study's +0.410, and today's sources + 28 days = the latency run's +0.375.

| How fast the speeds arrive | Always 14-day | **Always 28-day** | The switch | Switch − always 28-day (positive = the switch better) |
|---|---|---|---|---|
| Instant | +0.41 [+0.04, +0.78] | **+0.54 [+0.13, +0.95]** | +0.41 [+0.04, +0.78] | **−0.13 [−0.21, −0.05]**: 28-day better |
| Today's sources (weekly ManTennisData; Slams after the event) | +0.25 [+0.04, +0.46] | **+0.38 [+0.11, +0.64]** | +0.29 [+0.05, +0.52] | **−0.09 [−0.16, −0.02]**: 28-day better |
| Daily tour collector; Slams after the event | +0.33 [+0.08, +0.58] | **+0.47 [+0.17, +0.76]** | +0.36 [+0.11, +0.61] | **−0.11 [−0.19, −0.03]**: 28-day better |
| Weekly tour data; live Slam feeds | +0.34 [+0.05, +0.63] | **+0.44 [+0.10, +0.78]** | +0.34 [+0.03, +0.66] | **−0.10 [−0.17, −0.03]**: 28-day better |

* **By season, the 28-day memory is ahead in every one of the 12 season × scenario cells.** Instant, for example:

  | | 2024 | 2025 | 2026 |
  |---|---|---|---|
  | 28-day | +0.27 | +0.44 | +1.09 |
  | 14-day | +0.20 | +0.32 | +0.87 |

* **A descriptive variant,** one joint fit of both modes under each scenario's own history, did not beat always-28-day anywhere: +0.41, +0.25, +0.24 and +0.38.

## Reading

* **Observed.** The switch works as programmed, but it is not needed. **The 28-day memory is better in every situation tested, including when the speeds arrive instantly.** Switching to the 14-day memory for timely matches loses 0.09–0.13 mLL, and each of those intervals excludes 0.
* *Inferred:* the 14-day memory was simply too short. It came from the first round's tuning, on a target the auditor later found biased toward short memories. On the clean target the auditor already found a flat optimum near 21 days, and the latency tuning (result-free) chose 28. A player's serve-speed form persists for weeks, so a longer memory helps whether or not the latest match is in hand.
* **Faster data still pays.** With the 28-day memory, the gain rises from +0.38 (today's sources) to +0.47 (a daily tour collector) and +0.54 (instant).

**Suggestion** (the owner's call): replace the switch with a single rule, **always the 28-day memory**.
* It is simpler and needs no freshness check.
* It was better in every scenario.
* `adjust.py` already applies it: every match takes mode L.

If a faster source is added, the 28-day coefficients should be refitted on that source's history. Today's L coefficients were fitted on today's slower sources, which the auditor expects to under-weight faster data.

## Caveats

* **Exploratory.** 2024–26 results have now been read by three runs (the pre-registered test, the latency run and this one).
  * The 28-day memory itself was chosen without results, but comparing it with the 14-day memory on these seasons is an outcome comparison, and its advantage may be overstated.
  * Its consistency (every scenario, every season) and the result-free tuning both point the same way.
* **Coefficient history.** The L coefficients come from today's-sources history in every scenario. The T coefficients come from instant history. The auditor flags that this may slightly over-weight T and under-weight L in the mixed scenarios.
* **"The switch against the better arm"** compares with an arm read on the same outcomes. Here it is the same arm (28-day) in every scenario.
* **A prospective test** on matches after 7 October 2026 remains the clean confirmation.
