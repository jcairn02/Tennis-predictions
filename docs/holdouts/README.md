# Held-out matches: the register and the look ledger

The owner's decision of 29 Oct 2026 ([record](../decisions/2026-10-29-holdout-soft-rule.md)). This page holds the rules
agents follow, the two files, and how to tell how much a protected period has been used.

## Why

Once a result has been read to make a choice, it is no longer a fair test of that choice. A **protected period** keeps
recent matches unseen for **one question**, so that question gets one honest answer. Matches seen for one question can
still be unseen for another: the serve-and-return study counts matches the five-pattern check had read as unseen for its
own traits, with that disclosure ([§ 3](../studies/serve_return_leads/README.md)). **The ledger records every read**, so
later work can say how much each period has been used, and for what.

**Training never spends a period.** Retrains keep learning from every match. Only choosing spends it: picking a feature,
a setting or a model by how the options did on those matches.

## The files

| File | What it holds |
|---|---|
| [register.csv](register.csv) | The protected periods. Each has its question (`protects`), its matches (`tours`, `levels`, `first_day`, `last_day`), its `status` (open, read or released), its `read_plan` and its `source` |
| [looks.csv](looks.csv) | The ledger: reads (`L0001`, …) and decisions (`D0001`, …). Rows are only ever appended; a correction is a new row with a note |
| `src/eda/holdouts/ledger.py` | The tool: `check`, `add`, `decide`, `status`. Tools can call `ledger.warn()`, as the P9 scoring tool does |

**Today's periods:**
* **H1, the live model's edge,** from 19 Oct 2026.
* **H2, the five-pattern score's final read,** from 29 Jul 2026. It is read in August 2027, as pre-registered.
* **H3, the serve-and-return traits' check,** from 29 Jul 2026. The owner sets its schedule.

## The soft rule (for agents)

The periods are soft: the owner may spend, move or read any of them. Agents never decide that themselves.

1. **Before a read, run `check`** on the window you plan to use.
   * The work may measure what a touched period protects, and the owner's instruction may not say which matches to
     use. Then offer the owner the choice, with your recommendation:
     * stop the window the day before the period;
     * or use the recent matches and spend part of the period.
   * For a new model (women's, props, ITF, …), also ask whether it should get a clean period of its own, and from
     when. A new period is a new register row, at the owner's word.
2. **After the read, log it with `add`,** as part of the work, without being asked, whether or not it changes anything.
   Log one row per read, or one per batch of reads with a single purpose.
3. **When a decision rests on logged reads, log it with `decide`.**
   * Use `--chose reading` when the reading chose among the options, adopting or not included. The chosen option's later
     readings are inflated.
   * Use `--chose harm-check` when the kind of change decided and the reading could only veto. That inflates almost
     nothing.
4. **The owner's rulings on a period** (spend, move, read or release it) go into [docs/decisions/](../decisions/README.md)
   and change its register row.

**A read** is anything computed from the results of matches since the earliest open period's start (29 Jul 2026 today)
and set against a model, a feature, a rule, a price or an idea. Results here means who won, the score or the box score.
Log it even when the work belongs to another model: the record lets that model's own clean test be set later.

**Not a read:**
* training and prediction runs under the decided recipe;
* data checks that compare one source with another, or count matches;
* prices without results, such as closing-line value;
* watching bet-day results.

**A change made because of bet-day results is a decision.** Log what was seen as a read, then the decision.

**A retrain's harm check** reads every season up to its cut-off, H1 included. It is a decided procedure, so it does not
ask first. The agent who runs or reports the retrain logs it, with `--chose harm-check`.

## Commands

```bash
./python.sh src/eda/holdouts/ledger.py check --from 2026-09-01 --to 2026-10-28 --tours atp --levels tour
./python.sh src/eda/holdouts/ledger.py add --by "Claude (study X)" --from 2025-01-01 --to 2026-10-28 \
    --tours both --levels tour --model main --what "the candidate against the live model, both stages" \
    --where docs/studies/x/README.md --options 2 --se 0.15
./python.sh src/eda/holdouts/ledger.py decide --by owner --uses L0007 --what "the candidate adopted" \
    --chose reading --where docs/decisions/2026-11-02-x.md
./python.sh src/eda/holdouts/ledger.py status
```

* **Levels:**
  * `tour` is the main model's matches: ATP and WTA 250s and above, Slams included, main draws and their qualifying;
  * `lower` is Challengers, WTA 125s, ITF and their qualifying;
  * `all` is both.
* **The check compares days, tours and levels only.** Each period's source defines its exact matches. A read that
  touched fewer periods than the check finds (for example, qualifying matches against a period of main draws) states
  them with `--periods`.
* **`--options`** counts the options the reading chose among, the status quo included. Adopting or not is 2.
* **`--se`** is the standard error of the options' difference in mLL (thousandths of log loss per match).

## How much has a period been used?

`status` lists each period's reads and the decisions resting on them. **The size of the damage** follows the
clean-holdout rebuild's arithmetic
([02, § 1](../studies/clean_holdout_rebuild/02_contamination_and_forecast.md#1-why-re-selecting-cannot-clean-everything)):

* **A choice among k options** inflates the chosen option's reading by about se × m_k.
  * se is the standard error of the options' difference.
  * m_k is the expected best of k random draws: 0.56, 0.85, 1.03, 1.27 and 1.54 for k = 2, 3, 4, 6 and 10.
  * `status` prints each such term.
* **A period inherits that term in proportion to its share of matches inside the read's window.** Count the share at
  the period's own read, from the logged window.
* **A choice made on another measure carries over only partly.** That covers another market, a price at another time,
  or a statistic instead of who won.
* **A harm check, or a choice almost any noise would have made, inflates almost nothing.**

**Example.** Adopting a feature on a reading with se 0.15 (k = 2) inflates its later reading by about 0.08 thousandths
of log loss a match. The inflation is that full amount if the read's window held the whole period, and a third of it if
it held a third. The model's edge over the close has been about 1–3.

## History

* **12 Oct 2026:** the edge-anatomy study kept matches from 29 Jul 2026 sealed for an untouched test of the model's
  edge.
  * Two proposals of 8 Oct, the feature-provenance plan's phase 0 and the clean-holdout rebuild, had asked for a central
    seal file and look ledger. Neither was decided.
  * Studies kept their own date constants and look ledgers, for example
    [serve_speed_tabpfn/look_ledger.md](../studies/serve_speed_tabpfn/look_ledger.md). They remain records of their
    time, and new work reads the register.
* **13 Oct:** the owner-approved five-pattern check read matches to 23 Sep (L0001), and the adjustment went live on it
  (D0001).
* **28 Oct:** the P9 study read the live model against the close to 18 Oct (L0003), without checking the seal.
* **29 Oct:** the owner moved the model's untouched test to 19 Oct, as a soft rule, and asked for this ledger.
* **What the ledger holds from before 29 Oct:** only the reads known to touch today's periods (L0001–L0003).
  * Earlier harm checks on 2025–2026 are in
    [class_record.csv](../../data/studies/adoption_framework/class_record.csv).
  * One read reached H1 before it existed: the qualifying check of 22 Oct pooled 4 matches of 19 Oct with 15,830
    others (L0002), and the decision on it was a harm check (D0002).
