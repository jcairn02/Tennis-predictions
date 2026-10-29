# Brief 02: the ideas agent

You are the ideas agent of the P9 point-details study, in the Tennis-predictions repository (`C:\Users\zerom\Documents\Tennis-predictions`). First read `docs/studies/p9_point_details/briefs/00_shared_context.md` (the request, the gate's findings, the plan, the rules), then this brief.

## Goal

Propose **at most ten** pre-match statistics for **men**, built from rally length (shots per point) and, where a source flags it, net play. Each one needs a mechanism for why the 2025–26 betting close would misprice it. The lead will choose from your list and pre-register at most eight, plus one combined score. They will be tested once, against the closing price and the live model, on men's 2025–26 matches at tour level and at Challengers.

The owner's first criterion is orthogonality to the market: information about the result that the close lacks. Helping the model comes second.

## What you must read first, so you do not re-propose what is closed

* **Shot-level study:** [README](../../shot_level/README.md), [stage1.md](../../shot_level/stage1.md) (the 25 statistics), [stage2.md](../../shot_level/stage2.md) (the 141 features and the rundown), [stage3.md](../../shot_level/stage3.md) (method or data; which statistics were data-limited; the depth table; "Not tested").
* **Point-sequence study:** [README](../../point_sequence/README.md) §§ 5–6. Traits are closed; only states remain. The men's serve-speed change replicated; finishing form is inconclusive.
* **Serve and return leads:** [README](../../serve_return_leads/README.md).
* **Unpriced leads:** [README](../../unpriced_leads/README.md). Its five patterns are now a production adjustment. Pattern 3, fast courts × big servers, uses venue pace × the ace gap.
* **Feature universe:** [README](../../feature_universe/README.md) § 2, "Shot and point level", and its load and schedule family (sets in 14 days is a model input; minutes and fatigue kernels were built).
* **The list of point and shot ideas:** `docs/research/point-shot-ideas/README.md`, if it exists.

## The data you can count on (observed by the lead)

* **P9** (men, January 2025 to about 18 October 2026): rally length is known on about 95% of points at the 1000s, 50–64% at the 250s and 500s, and 25–35% at Challengers, varying by event. Net flags exist at only 24 events (1,133 matches). Each point has a server, a winner and an ending (ace, double fault, winner, forced or unforced error), though some events leave many endings unclassified. Serve speeds exist on the 4,324 matches whose events had radar.
* **Earlier sources** for longer histories:
  * the Slam feeds (Wimbledon and US Open fully; Australian Open 2025 and Roland Garros 2025–26 thinly);
  * the volunteer charts (the top players);
  * the ATP match-centre handoff, 2018 to early 2025, with rally lengths on about 1,200–2,000 men's matches a year;
  * TDI's capture, mostly June–September 2026, rally length and net points;
  * SirGenkii's copy of the ATP files, December 2024 to April 2025.
* **The model already holds:** box-score aces, double faults, first serves in, first- and second-serve points won, holds, break points saved (as surface IOS profiles and two-week forms); total points won; sets in 14 days; age; Elo; serve speed (stage 2); the five patterns.

## For each idea, give

* a **name** and an **exact definition**: the as-of rule, the memory (window or half-life), any opponent adjustment, and shrinkage toward a prior whose strength comes from the statistic's spread, never from results;
* the **encoding**: an A − B difference, a pair (A's and B's values), or a symmetric context or price-slope modulator;
* the **declared direction** (which side it favours relative to the price) and the **mechanism**: why the close would miss it;
* why it is **not one of the closed statistics**, or why more depth changes the earlier verdict;
* whether it is a **state or a trait**;
* its **expected coverage**, given the data above;
* **how it could be wrong** (confounds; what would make it a proxy of something priced);
* **literature** support, with URLs and the date you read them, where any exists.

## Cover at least

* a **rally-load state**: recent shots hit, or long rallies played, over the last days or the previous match. This is physical load beyond the sets and minutes the model already has;
* a **change state**: the recent rally profile against the long-run one, by analogy with the serve-speed change that replicated;
* a **style clash**: a matchup of one player's short-rally strength against the other's long-rally strength, or the like;
* the shot-level study's **noisy traits**, re-specified for depth (quick points won on serve and on return, long-rally points won), only if a mechanism argues that the market misses them.

Then rank the ideas by your prior that an edge beyond the close exists, and say which three you would register and why.

## Allowed and not allowed

* **Allowed:** you may look at data distributions (coverage, how often something occurs) and search the web for literature on rally length, physical load and tennis betting market efficiency.
* **Not allowed:** relating any statistic to match results. Do not compute any outcome-based score, and do not read other studies' result tables to pick a winner beyond what their reports say.

## Where you may write

* `docs/studies/p9_point_details/team/ideas.md`;
* `docs/studies/p9_point_details/team/ideas.csv` (one row per idea, with the fields above);
* scratch code under `src/eda/p9_point_details/ideas_*.py`, if you need any.

Nothing else.

## Your final message

The ranked list in a few lines each, your three to register, and the paths of what you wrote. Put your process notes (searches, sources rejected, ideas dropped and why) in the memo.
