# Lock-in: the men's serve, return and serve-speed traits, for one check on unseen matches

**Frozen 16 Oct 2026, 14:15 PDT**, before any result of these traits from 29 Jul 2026 on was read. This file's SHA-256, and those of its scales and code, are in the [process log](process_log.md). A change before the first look is logged there with old and new hashes; after the first look, nothing here changes.

Study: [serve/return leads](README.md) · Kept by Claude Opus 5.5, session `6483c720-30a3-46ff-9519-287690b6f9d8` · The owner's words of 16 Oct 2026: "Lock in these traits and their expected direction now, and check them once on the unseen matches" (the full request is in the log).

## 1. What was seen when this was written

* **Where the traits were found:** the edge-anatomy study's ledger, men, 1 Jan 2025 – 28 Jul 2026 (4,394 matches). Their 2013–24 readings were also published there.
* **The combined score (R0, § 3) was defined before its reading was computed,** then read on the same seen windows: 2025–26 z +5.59, 2013–24 +2.16, 2020–24 +1.61 (`data/studies/serve_return_leads/timeline.json`).
* **No result from 29 Jul 2026 on has been read for these traits by anyone.**
  * The unpriced-leads check of 13 Oct read the results of 29 Jul – 23 Sep 2026 once, for its five-pattern score. That score was projected off the model's inputs, these traits among them.
  * Its luck group was switched off in those months, and its speed term was 0 there.
  * Those 416 men's matches are included below, with that disclosure.

## 2. The traits

Men's main tour; the model's own inputs, A − B, as the decided chain builds them for the instance current at the look.

| Trait | Columns | Direction: the player higher on it… |
|---|---|---|
| **T1** Serving strength (long memory: holds and break points saved, per surface, opponent-adjusted) | `iosO_hold`, `iosO_bp_saved` | loses to the close more often than it implies |
| **T2** Break points saved, recently (two-week form) | `form_bp_saved` | loses to the close |
| **T3** Returning strength (long memory: holding the server's first-serve points and service games down) | `iosD_first_won`, `iosD_hold` | beats the close |
| **T4** Serve-speed change (the serve-speed stage's 28-day memory) | `spd_L`: `spd_L_B` for matches before 8 Oct 2026, `spd_L_D` from 8 Oct, as the production rule defines it | beats the close |

## 3. The scores

* **A missing input counts 0.**
* **Each column** is divided by its frozen RMS and multiplied by its sign (− for T1 and T2's columns, + for T3's and T4's).
* **A trait** is the mean of its columns, divided by its frozen RMS.
* **R0, the combined serve/return score,** is the mean of T1, T2 and T3, divided by its frozen RMS. Speed stays out of R0: it is a separate stage of the model and was unstable by season.
* **The frozen scales** are `data/studies/serve_return_leads/lock_in_scales.json`: the RMS of each column, trait and R0 over the men's matches with tournament dates 1 Jan 2025 – 28 Jul 2026 (4,336 matches; the speed column's RMS over its non-zero values). They were computed outcome-free.

## 4. Hypotheses

* **H0 (primary): β(R0) > 0.** Beyond the close, the combined serve/return score predicts who wins in its registered direction.
* **HS (speed, its own family): β(T4) > 0.**
* **H1–H3:** β(T1), β(T2), β(T3) > 0. They are tested only at a look where H0 is confirmed, with Holm at that look's level.

## 5. The matches and the test

* **Matches:** the men's main-tour matches of the frame of the instance current at the look, debut seasons out, with tournament date from **29 Jul 2026** to the look's cut-off.
* **The price:** the frame's odds input, margin-free (in this window BetOnline's closing line, the books' average where it has none). L is its log-odds.
* **The fit:** logistic, no intercept: logit P(A wins) = s·L + k·L|L| + β·score, every coefficient fitted in the window.
  * This is unpriced leads' registered `look.fit`, unchanged.
  * β is per RMS of the score in the window.
* **Uncertainty:** cluster-robust over four-week blocks; the one-sided p comes from t on G − 1 degrees of freedom.
* **Verdict words:**
  * **confirmed:** the one-sided p is at or below the look's level;
  * **contrary:** the p in the other direction is at or below it;
  * **unresolved:** otherwise, with P(β > 0).
  * "Tie" is never used.

## 6. When the check runs

**The owner chooses the schedule before the first look.** A look run before a schedule is written here is invalid. Recommended, with power (`timeline.csv`, R0; at 1 the 2025–26 strength survives in full, at 0.45 the typical share survives, and "back to 2013–24" means about a quarter of it):

| Schedule | Overall error | If fully real | At 0.45 | Back to 2013–24 |
|---|---|---|---|---|
| **Three looks**, at the first table rebuild after 31 Jan, 31 May and 31 Aug 2027 (about 1,050, 2,100 and 2,900 unseen men's matches), each at one-sided 0.0221 (Pocock), stopping at a confirmation | 0.05 | 0.99 | 0.46 | 0.15 |
| One look after 31 May 2027, one-sided 0.05 | 0.05 | 0.97 | 0.48 | 0.21 |
| One look after 31 Aug 2027, one-sided 0.05 | 0.05 | 0.996 | 0.62 | 0.26 |
| One look now (416 matches, 3 blocks), one-sided 0.05 | 0.05 | 0.32 | 0.14 | 0.09 |

HS uses the same schedule at the same levels, as its own family. If nothing is real, the chance of at least one false "confirmed" across H0–H3 and HS is about 0.10. The power figures use the normal approximation scaled from the seen window; the sequential ones are simulated.

## 7. Reported beside the verdicts (no verdict words)

* each trait alone;
* beyond the model's both-stages forecast (the instance current at the look);
* the large-gap table of the edge-anatomy explanation (the market's price, the model's price and how often the stronger player won, by size of gap);
* completed matches only;
* the Slams left out;
* BetOnline's open-to-close move on R0 (outcome-free: does the line learn it before the close?);
* the 416 matches already read by the five-pattern check, apart and left out.

## 8. Deviations

* **Allowed before the first look, each logged with old and new hashes:**
  * the schedule (§ 6);
  * a data repair found by outcome-free checks;
  * a bug fix that leaves the specification as written;
  * an addendum that **adds** cleaner versions, with its own hypotheses and error budget. An addendum never changes §§ 2–5 or § 7.
* **Not allowed:** changing a trait, a column, a direction, the scales, R0's construction, the window's start, the price or the test.
