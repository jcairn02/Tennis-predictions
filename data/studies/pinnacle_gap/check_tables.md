# Pinnacle from TennisExplorer: check tables

Written by `src/eda/pinnacle_gap/check.py`.

## 1. Coverage of the frame's matches from August 2025

| Month | Frame matches | Linked to TennisExplorer | With a Pinnacle price | Share |
|---|---:|---:|---:|---:|
| 2025-08 | 538.0 | 528.0 | 509 | 94.6% |
| 2025-09 | 296.0 | 296.0 | 286 | 96.6% |
| 2025-10 | 550.0 | 549.0 | 537 | 97.6% |
| 2025-11 | 84.0 | 84.0 | 83 | 98.8% |
| 2026-01 | 498.0 | 490.0 | 484 | 97.2% |
| 2026-02 | 543.0 | 543.0 | 527 | 97.1% |
| 2026-03 | 537.0 | 537.0 | 519 | 96.6% |
| 2026-04 | 387.0 | 387.0 | 378 | 97.7% |
| 2026-05 | 556.0 | 546.0 | 537 | 96.6% |
| 2026-06 | 594.0 | 593.0 | 581 | 97.8% |
| 2026-07 | 373.0 | 373.0 | 363 | 97.3% |
| 2026-08 | 702.0 | 702.0 | 693 | 98.7% |
| 2026-09 | 323.0 | 323.0 | 297 | 92.0% |
| 2026-10 | 149.0 | 149.0 | 146 | 98.0% |
| **All** | **6,130** | **6,100** | **5,940** | **96.9%** |

By the source the current instance uses there:

| Current odds input | Frame matches | With a TennisExplorer Pinnacle price |
|---|---:|---:|
| average | 323 | 274 |
| betonline | 5,263 | 5,137 |
| pinnacle (oddstrader) | 544 | 529 |

## 2. TennisExplorer's last Pinnacle price against the other recordings of Pinnacle

| Against | Month | Matches | Same price | Median gap (log-odds) | Gap over 0.1 | Over 1.0, per 1,000 |
|---|---|---:|---:|---:|---:|---:|
| tennis-data PSW/PSL | 2025-01 | 437 | 57% | 0.002 | 2.3% | 0.0 |
| tennis-data PSW/PSL | 2025-02 | 508 | 52% | 0.006 | 2.8% | 0.0 |
| tennis-data PSW/PSL | 2025-03 | 533 | 51% | 0.007 | 1.9% | 0.0 |
| tennis-data PSW/PSL | 2025-04 | 361 | 43% | 0.014 | 5.3% | 0.0 |
| tennis-data PSW/PSL | 2025-05 | 535 | 52% | 0.007 | 3.9% | 1.9 |
| tennis-data PSW/PSL | 2025-06 | 572 | 53% | 0.004 | 2.8% | 0.0 |
| tennis-data PSW/PSL | 2025-07 | 477 | 71% | 0.000 | 1.7% | 0.0 |
| tennis-data PSW/PSL | 2025-08 | 506 | 95% | 0.000 | 1.2% | 0.0 |
| tennis-data PSW/PSL | 2025-09 | 283 | 94% | 0.000 | 0.4% | 0.0 |
| tennis-data PSW/PSL | 2025-10 | 409 | 91% | 0.000 | 0.5% | 0.0 |
| tennis-data PSW/PSL | 2025-11 | 76 | 58% | 0.000 | 3.9% | 13.2 |
| tennis-data PSW/PSL | 2026-01 | 172 | 70% | 0.000 | 2.3% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-01 | 430 | 48% | 0.009 | 3.0% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-02 | 504 | 38% | 0.015 | 3.8% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-03 | 523 | 36% | 0.015 | 3.3% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-04 | 358 | 30% | 0.021 | 7.8% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-05 | 509 | 34% | 0.017 | 6.9% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-06 | 539 | 38% | 0.013 | 3.0% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-07 | 453 | 20% | 0.027 | 12.4% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-08 | 473 | 9% | 0.042 | 19.7% | 0.0 |
| OddsTrader book 20 (stamped <= 30 min after the start) | 2025-09 | 56 | 14% | 0.054 | 25.0% | 0.0 |

## 3. Timing and margin of TennisExplorer's Pinnacle prices (linked frame matches)

| Quarter | Matches | No time shown (untimed) | Price changes recorded (both sides), median | Last change before the listed start, median min (90th pct) | Last change after the start | Opening, median h before | Margin, median |
|---|---:|---:|---:|---|---:|---:|---:|
| 2025Q1 | 1,478 | 1% | 2 | 22 (97) | 0.1% | 32 | 2.78% |
| 2025Q2 | 1,469 | 2% | 2 | 21 (83) | 0.0% | 30 | 2.73% |
| 2025Q3 | 1,273 | 53% | 0 | 46 (124) | 0.0% | 28 | 2.83% |
| 2025Q4 | 620 | 46% | 1 | 42 (149) | 0.0% | 20 | 2.94% |
| 2026Q1 | 1,530 | 2% | 2 | 42 (178) | 0.2% | 27 | 2.81% |
| 2026Q2 | 1,496 | 1% | 2 | 44 (196) | 0.0% | 28 | 2.81% |
| 2026Q3 | 1,353 | 1% | 2 | 53 (259) | 0.1% | 24 | 2.83% |
| 2026Q4 | 146 | 1% | 2 | 65 (225) | 0.0% | 24 | 2.86% |

## 4. Gross disagreements with TennisExplorer's other books

| Season | Matches with a referee | Gross | Of them mirrors | Per 1,000 |
|---|---:|---:|---:|---:|
| 2025 | 4,832 | 0 | 0 | 0.00 |
| 2026 | 4,514 | 3 | 2 | 0.66 |

The other way round: prices on our side that are the mirror image of the site's books (a swapped tennis-data row, or a swapped link of ours):

| Price | Matches with a referee | Gross | Of them mirrors |
|---|---:|---:|---:|
| tennis-data's average | 9,346 | 9 | 4 |
| the instance's odds input | 9,346 | 4 | 4 |

| Price | Match | Month | Current input's source | Its chance for A | The site's books | The site's Pinnacle |
|---|---|---|---|---:|---:|---:|
| tennis-data's average | `wta|2025-520|F|wta:214544|wta:221103` | 2025-05 | pinnacle (tennis-data) | 0.67 | 0.34 | 0.32 |
| tennis-data's average | `atp|2026-540|SF|atp:100644|atp:209259` | 2026-06 | average | 0.84 | 0.17 | 0.15 |
| tennis-data's average | `atp|2026-418|R32|atp:126207|atp:209279` | 2026-07 | betonline | 0.27 | 0.74 | 0.76 |
| tennis-data's average | `atp|2026-5014-20261007|R32|atp:200267|atp:207989` | 2026-10 | average | 0.10 | 0.90 | 0.9 |
| the instance's odds input | `wta|2025-520|F|wta:214544|wta:221103` | 2025-05 | pinnacle (tennis-data) | 0.69 | 0.34 | 0.32 |
| the instance's odds input | `atp|2026-540|SF|atp:100644|atp:209259` | 2026-06 | average | 0.84 | 0.17 | 0.15 |
| the instance's odds input | `atp|2026-418|R32|atp:126207|atp:209279` | 2026-07 | betonline | 0.23 | 0.74 | 0.76 |
| the instance's odds input | `atp|2026-5014-20261007|R32|atp:200267|atp:207989` | 2026-10 | average | 0.10 | 0.90 | 0.9 |

## 5. Accuracy: TennisExplorer's Pinnacle against the other prices (reads results)

mLL, TennisExplorer's Pinnacle − the other price (+ = TennisExplorer's Pinnacle worse), same matches.

| Period | Against | TennisExplorer − it |
|---|---|---|
