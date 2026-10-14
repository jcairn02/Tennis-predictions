# The men's 2026 Challenger and Challenger-qualifying matches enter the current best model, through the level layer

**Requested by the owner on 10 October 2026,** in the session that put the [level layer](2026-10-10-level-evidence-layer.md)
into the template. The owner's words:

> "Also Wire in the 2026 challenger data we already have to the model, including the 2026 men's qualifying box scores
> sitting on disk. That fills a live gap."

Claude reported what is on disk and asked which data the owner meant; the owner chose the recommended option
(AskUserQuestion, 10 Oct 2026):

> "Men's 2026 CH + CHQ (Recommended)": role F's checked additions, 1,735 men's 2026 Challenger and
> Challenger-qualifying matches (~20 with box scores), entering through the level layer. Built as a candidate on the
> layer template and adopted unless the harm check fails. ITF and women stay out. Fills Elo, workload and recent form
> for June–October 2026; a live feed for future weeks is separate work.

What Claude had found (put to the owner with the question): Stage 0 already holds men's 2026 Challenger main draws through
5 Oct (6,194 of 6,215 with box scores) and men's tour qualifying (734 of 739 with box scores). It lacks men's Challenger
qualifying after 1 June 2026 (Sackmann's lower tiers end there; Tennis My Life does not carry them). On disk those are
results (TennisLive and SofaScore listings) with box scores for about 20; SofaScore holds statistics for 4 of its 497.

**Adopted on 10 October 2026 under the owner's chosen rule ("adopted unless the harm check fails"): the harm check
shows no harm.** Recorded by Claude, who carried it out ([record](../studies/level_layer_adoption/README.md)).

## Decision

1. **The template's training history gains 1,735 men's matches of 2026 and one box score** (the package
   `men_2026_ch_chq`):
   * 1,723 Challenger-qualifying matches: 1,674 TennisLive results (5 Jan – 29 Sep 2026; 19 with box scores) and 49
     SofaScore results (15 Jun – 5 Oct);
   * 12 Challenger main-draw matches (11 SofaScore of 5 Oct, 1 TennisLive of 21 Sep);
   * one box score completing a men's 2026 Challenger match Stage 0 held as a result only.

   They are role F's additions of the level-evidence study (`data/studies/lower_level_evidence/system/stage0/C0_now/`,
   linked, identity-checked and timed by its builder), the men's 2026 Challenger and Challenger-qualifying part:
   candidate `data/studies/level_layer_adoption/stage0/C0_men26/` (`candidate_stage0.py --derive-from C0_now
   --keep-tours atp --keep-levels CH,CHQ --keep-years 2026`; its checks pass).
2. **They enter through the [level layer](2026-10-10-level-evidence-layer.md),** like every lower-level match:
   translated, weighted, results in Elo at the fitted exchange rate.
3. **Every build merges them into its own tables, never the repository's.** The package is
   `data/studies/current_best_model/accepted_additions/men_2026_ch_chq/`, listed in `accepted.json`
   (`src/eda/current_best_model/additions.py`):
   * a template build runs `run_chain.py --additions` after `--setup`, then lane 0 (Stage 1's odds link and the
     leak-proof features; its timeline step skipped, since the package brings its own rows), then `--prepare-layer` and
     the lanes with `--layer` (`build_template.sh <sandbox> <out> 1 accepted`);
   * a prediction run merges it after Stage 0 and pins its timeline rows after the timeline is rebuilt;
   * an added match whose id, or whose players, tournament and round, a feed has published since is skipped (the feed's
     row wins); `history.py` counts the package as "accepted", so it refuses no build.
4. **What it fills.** Elo, workload and recent form for men who played Challenger qualifying in June–October 2026, which
   Stage 0 has lacked since its lower tiers ended on 1 June. **Not** a live feed: Challenger qualifying after 5 Oct still
   has none (separate work, which would have to pay for itself).

## Evidence

* **Classified before any result:** more data of a kind already used (Challenger qualifying is in the history to
  1 June 2026), entering by the route the level-evidence study's evidence supports; the comparison is a harm check.
  In the adoption framework's table it is an expansion (new sources for a level already used), not an accretion; the
  label was made precise when the reading was pooled, after the result. Both kinds are adopted unless the harm check
  fails, so the label does not change the decision.
  The study's own reading of its men's 2025–26 additions through the system: +0.031 [−0.035, +0.097] on the holdout,
  unresolved, P 0.84.
* **The build.** The template with the layer on C0_men26 (lane 0 first; strength rule "plain": 14,476 reference
  matches of men's 2026 move after 5 Jan, the 2026 main-tour scale by 0.06 Elo points). Against the template on the
  reference's tables: women's inputs exact; every input of the 65,064 matches the additions cannot reach exact, except
  the joint solves' convergence noise (≤ 7.9e-9; at a 1e-13 solver tolerance the two builds agree to 8e-12:
  `checks/solver_tolerance.json`); 2,162 men's 2026 matches changed. Merging the package into the frozen tables gives
  C0_men26's tables exactly, so the build is the template's recipe.
* **The harm check** (men, both stages, season 2026, the only season the additions reach; seeds 0–3 paired;
  `system_pairs.py`): **+0.058 [−0.048, +0.164] mLL per match, unresolved, P(better) 0.89** (+ = with the data better;
  2,190 matches, 11 blocks). Women −0.0004 [−0.006, +0.005]. No harm; no edge credit. 2026 was read by the study's
  holdout once already; this reading is a harm check, not a selection.

## To undo

Remove `men_2026_ch_chq` from `accepted.json`: builds then merge nothing.
