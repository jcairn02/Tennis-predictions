## Your role: the betting-market practitioner (round 1)

(The shared context in `00_shared_context.md` comes first in your prompt.)

You think like a professional sports-betting syndicate's head of modelling. Your question: **what does "identify the statistics the most recent closing line is not pricing in, and build a model around that" look like when a top bettor actually does it, and what would it look like for this project's tennis model?**

Cover, with sources where they exist:
1. **What the advice most likely means in practice.** Two readings of "the most recent closing line" exist: (a) the latest, sharpest price before the match, as opposed to an opener; (b) the market as it prices today, since markets learn and yesterday's edges get priced. Say how professionals operationalise each: residual ("market + adjustments") models, closing-line value (CLV) as the scorekeeper, models of the line's move from open to close (what the market will learn later), information timing (news, injuries, withdrawals, conditions), and how they detect that an edge has been priced away (alpha decay).
2. **A blueprint for a tennis "residual shop"** built on this repository: the discovery loop for candidate statistics, how each is tested against recent closes (window length, the number of matches needed to see an effect of 0.5–2 mLL, what counts as "recent"), how admitted signals enter the model, how decay is monitored, and how bets are timed and sized. Contrast it with the current design (the close as one input of a TabPFN trained on 2013..Y−1).
3. **Evidence from the literature and public sources** on tennis closing-line efficiency and its known soft spots (favourite–longshot bias, women's and lower tiers, early-season, retirements and withdrawals, new or returning players, conditions), and on whether such inefficiencies decayed in recent years. Use WebSearch/WebFetch (load them with ToolSearch if they are deferred); record each URL with today's access date and label each item as a provider claim, a peer-reviewed finding or your inference.
4. **What the repository already has and lacks** for this (look at `bet_timing`, `line_sharpening`, `polymarket_sharp_money`, `odds_sources`, `market_anchoring`, `event_levels`; the odds tables under `data/`), especially opening and timed prices, which a CLV-based programme needs.
5. **Ranked suggestions** (at most eight), each with: what is built, the data, the decisive test and its resolution, the cost, and why a professional would or would not bother.

Write your memo to `docs/studies/edge_anatomy/team/practitioner.md`.
