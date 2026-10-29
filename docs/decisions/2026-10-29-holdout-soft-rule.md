# The untouched test of the model's edge counts from 19 Oct 2026, as a soft rule; a register of held-out matches and a look ledger

**The owner's decision, 29 October 2026.** Verbatim:

> Note: I am good to start the fair test from 19 october 2026, but I want it to be a user decision to potentially
> over-ride it. Not a hard lock. Like a "soft-rule" so when I give vague instructions to an LLM to test it out on recent
> data, it may return to me the option of when to test it, and should we have the clean hold out.
>
> Im building out womens models, prop models , ITF models, and lets say in 3 months, not using that data to inform
> decisions is a significant cost. Its loosely related to the current model I have.
> Im not sure how to navigate that trade off. How psiloed to keep the prop and ITF models from the main model.
>
> What do you think of a ledger of keeping track of each time we touched sets of data going forward so that we can
> backwards reason HOW contaminatead certain data is.
> A file that stores all of this that the claude/agents.md file is aware about, and directs agents doing work to the
> existence of it, so when it looks at the "hold outs" to inform a decision that makes its way to the model it updates
> this ledger automatically without me explicitly telling it.

This answers the question the P9 study left open
([§ 6](../studies/p9_point_details/README.md#6-a-lapse-of-mine-the-sealed-matches)).
* **The design below is Claude's** (an agent's choice): the register, the ledger and its tool, what counts as a read,
  and the wording in CLAUDE.md.
* **The policy for the side models is Claude's recommendation, for the owner to confirm.**

## What the owner decided

1. **The untouched test of the live model's edge counts the matches played from 19 Oct 2026** (period H1). For that test
   it replaces 29 Jul 2026, the start the edge-anatomy study set.
2. **It is a soft rule.**
   * The owner may spend it, move it or read it at any time.
   * Agents never decide any of that themselves. When an instruction leaves it open, they offer the owner the choice
     and recommend one option.
3. **A ledger records every read of recent results.** CLAUDE.md points every agent to it, and agents log their reads
   without being told.

## How it works (Claude's design)

The rules are in the [holdouts README](../holdouts/README.md).
* **[The register](../holdouts/register.csv) lists the protected periods, each with the one question it protects:**
  * **H1, the live model's edge,** from 19 Oct 2026.
  * **H2, the five-pattern score's final read,** registered by the unpriced-leads study on matches from 29 Jul 2026 and
    read in August 2027.
  * **H3, the serve-and-return traits' check,** locked in on 16 Oct 2026 on men's matches from 29 Jul 2026, on a
    schedule the owner sets.
* **[The ledger](../holdouts/looks.csv)** holds reads and decisions. Rows are only ever appended.
* **The tool** is `src/eda/holdouts/ledger.py`:
  * `check` lists the periods a window touches;
  * `add` logs a read; it works out the periods from the window, or takes them from `--periods`;
  * `decide` logs a decision that rests on logged reads;
  * `status` shows each period's reads and decisions, with the size of their effect where it can be computed.
* **The P9 scoring tool's warning now reads the register.** Before, it carried its own 29 Jul date.
  * Tests: 13 new (12 for the ledger, 1 for the warning), plus the P9 suite. 34 of 34 pass.
* **What counts as a read:** anything computed from recent matches' results and set against a model, a feature, a
  rule, a price or an idea. Results here means who won, the score or the box score.
* **Not a read:**
  * training and prediction runs under the decided recipe;
  * data checks between sources, and counts;
  * prices without results;
  * watching bet-day results. A change made because of bet-day results is logged as a decision.
* **A retrain's harm check** reads every season up to its cut-off, H1 included. It is a decided procedure and does not
  ask first; the agent who runs or reports it logs it.
* **Why per question:**
  * A period protects a question, not the data. Matches seen for one question can be unseen for another, which is how
    the serve-and-return study counted the weeks the five-pattern check had read.
  * Training never spends a period; only choices made by looking do.
  * How much a period is spent follows the clean-holdout rebuild's arithmetic (se × m_k for a choice among k options,
    scaled by the share of the period inside the read's window).

## The side models (Claude's recommendation, for the owner to confirm)

* **The women's model** predicts the same matches' winners as the live model's women's half, so H1 covers it.
  * **Recommended: build it on matches to 18 Oct 2026, and test it on H1's women's matches,** which accumulate while
    it is built. Thirteen seasons of history carry the design choices; three more months add little to them.
  * **The alternative is the owner's to choose each time** (agents ask): use the recent women's matches.
    * That spends H1's women's half.
    * The live model's test then rests on men alone and takes about twice as long. Men's and women's tour-level
      matches are about equal in number (4,394 and 4,199 from 2025 to 28 Jul 2026).
* **Props and ITF models** answer other questions: other markets, and matches the live model does not predict.
  * They may use recent matches without asking, with every read logged, on two conditions:
    * they never measure the live model's own forecasts against H1's results;
    * nothing they choose enters the live model without its own test.
  * They may take the live model's chance as an input: that uses it, it does not grade it.
  * Their own clean test, at the owner's word, can take either form:
    * a new register row from the day each design is frozen;
    * their forecasts recorded before the matches and graded afterwards, as the bet day records the live model's.
* **The live record is a test no later read can spoil.** It is the predictions the system made before each match, graded
  by A7 and kept by A8's ledger. It tests the system as it ran, each version on the matches it predicted.

## Reads of H1 so far

**One:** the qualifying study's follow-up 2 (22 Oct; L0002).
* It pooled 4 qualifying matches played on 19 Oct with 15,830 earlier ones.
* The decision resting on it, keeping the five-pattern adjustment on for qualifying, was a harm check (D0002).
* So H1 is, in effect, untouched.

**How this was checked:**
* the dates of that study's matches;
* the frame of the 21 Oct instance, the newest frame any later comparison scored, which ends with events of 12 Oct;
* the P9 study's window, which ends on 18 Oct.

No other read reaching 19 Oct was found. Rows L0001 (the five-pattern check, to 23 Sep) and L0003 (the P9 study, to
18 Oct) record the reads of H2's and H3's dates.

## What it replaces, and what it leaves alone

* **For the model's edge:** it replaces the 29 Jul 2026 seal (edge anatomy, § 3). Old studies' code keeps its 29 Jul
  constants as a record of its time; new work reads the register.
* **H2 and H3** keep their own registered windows and rules.
* **The 8 Oct proposals** (the feature-provenance plan's phase 0 and the clean-holdout rebuild) asked for a central seal
  and look ledger. This is a lighter, soft version of that idea. Their designs remain proposals.

## Left to the owner

* **When to read H1.** It is not set yet. An untouched test needs several thousand matches.
* **The side-model policy above.**
* **Whether a retrain should log its own harm check in the ledger.** That would be a change to the live path, and it is
  not done.
