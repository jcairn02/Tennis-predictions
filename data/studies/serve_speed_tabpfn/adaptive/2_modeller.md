# Adaptive memory: columns and per-match mode (agent 2, modeller)

8 October 2026, built to `adaptive/plan.md`. All numbers are **observed**.

**Values only.** No result, outcome, price or statistic target was read, so there is no look to log. No GPU; the earlier modules are reused by import, unedited.

## Built

* **Code:** `src/eda/serve_speed_tabpfn/adaptive/columns.py` (25 s; 4 min with the probe).
* **`adaptive/columns.parquet`:** 63,737 rows. `match_id`, then per scenario S (A, B, D, E):
  * `spd_T_S`: the 14-day filter, clip(Δf̂ / s_f, ±4);
  * `spd_L_S`: the 28-day filter, clip(Δf̂ / SD_L, ±4);
  * `late_a_S`, `late_b_S`, `mode_S`.
* **`columns_meta.json`:** standardisers, constants, mode shares per tour × season × scenario, the probe record, and input and code hashes.
* **Rows:** the latency variants' rule. A row enters the history and the as-of offsets only when `release_S ≤ es`. A is the build as run.
* **Standardisers:** the earlier builds' exact floats, s_f = 2.2239954 and SD_L = 1.9496052 km/h (B-M1's). Rounding would break the equalities.
* **Both equalities are exact on all 63,737 matches:** `spd_T_A` == `spd_f`, and `spd_L_B` == `spd_B_M1`.

## The late flag

**Backtest (`late_flags`).** A side is late at `es` if one of his own earlier matches meets all of these:
* it is earlier by own order;
* it is a usable panel row;
* `lf + 1 < es`;
* `obs ≥ es − 14`;
* `release_S > es`.

The mode is T unless a side is late.
* **Under A:** no side is late (checked).
* **Women:** never flagged, mode T, columns 0.

**Live (`late_flags_live(frame_rows, speeds_in_hand, watermarks, now)`).**
* **Inputs:** the played and target player-matches, each played one with its covering source ('' if none); the (match, player) pairs with a speed in hand; the source watermarks; and `now`.
* **Rule:** a match is outstanding when `pending(lf, watermark, covered)` (the engineer's helper) is true and its speed is not in hand. It is then treated as released after `now`, and the backtest rule applies.
* **One difference:** live, a covered match that the source will finally omit counts as late until the watermark passes it. The backtest has no row for it.

## Mode shares, men (values only)

| Share in mode L | A | B | D | E |
|---|---:|---:|---:|---:|
| 2022 | 0 | 36.1% | 10.6% | 25.7% |
| 2023 | 0 | 39.3% | 8.0% | 31.5% |
| 2024 | 0 | 50.3% | 10.2% | 40.8% |
| 2025 | 0 | 42.6% | 13.6% | 29.5% |
| 2026 | 0 | 46.8% | 16.2% | 31.4% |
| **2024–26** | 0 | **46.6%** | **13.0%** | **34.2%** |

Correlation with A's `spd_f`, men 2024–26:

| | B | D | E |
|---|---:|---:|---:|
| `spd_T` | 0.686 | 0.815 | 0.753 |
| `spd_L` | 0.673 | 0.796 | 0.738 |

A daily tour collector (D) closes most of the gap. Live Slam feeds (E) close less, because most late matches are at tour level.

## Probe B, scenario D

* **Days:** 19, namely the timing probe's four, every 2024–26 Slam second Wednesday, and 6 random.
* **Noise on day D:** every row with `release_D > D` gets a noised speed (filter and snapshots alike) and a new release day in (D, D + 60], so it is still pending.
* **Checked:** all five D columns of every men's match with `es ≤ D`. **0 moved: PASS.**
* **Leaky controls fired:**
  * columns from rows admitted at `lf + 1`: 3,145 sides moved;
  * a flag that peeks a week ahead: 94 sides moved.

## Tests

`test_ssp_adaptive_columns.py`: **10 passed.**

* **The build:**
  * never NaN, within ±4, and L exactly when a side is late;
  * both equalities, and the standardisers;
  * no late side under A;
  * women 0, T;
  * the stored flags equal the rule recomputed from release days.
* **Flip under D:** columns negate exactly, flags swap, mode holds.
* **Probe:** the record passes.
* **The rule by hand:**
  * 1-day grace: es − 1 is not late, es − 2 is;
  * 14-day window: es − 14 is late, es − 15 is not;
  * a speed in hand clears it;
  * another player's match, or the same or a later round, does not count;
  * an untimed event is never late.
* **Live by hand:**
  * a ManTennisData match behind the Friday watermark makes the player late, and he clears once it passes;
  * yesterday's match is in the grace;
  * a Barcelona-like event never counts;
  * a pending Slam counts only within 14 days.
* **Live equals backtest** on random histories.

## Choices

1. Exact standardiser floats, not the plan's 2.224 / 1.950.
2. A uses own order. B, D and E add `release ≤ es`.
3. The mode never changes the columns; the scorer picks `spd_T` or `spd_L` by `mode_S`.
