# Women's matches are switched off for the bet day (the notebook's A1–A8)

**The owner's decision, 28 October 2026.** Verbatim:

> For the master_pipeline.ipynb steps A1-A8 temporarily disable womens matches
> We havent demonstrated they are profitable yet, im not betting on them, and their matches constantly cause errors
> because the pipeline isnt robust enough yet. It just slows everything down massively

**The design below is Claude's** (an agent's choice, in the production-integrity plan's sense): how each step applies
the switch, and that it reaches only the bet day. It moves no men's pick. How it was done:
[master pipeline process log](../studies/master_pipeline/process_log.md), Part 24.

## The switch

`BET_TOURS = ("atp",)` in `src/pipeline/config.py`. **Women's matches come back with `("atp", "wta")`**; then restart
the notebook's kernel. Nothing is deleted, so every step's women's output comes back from the files. STATUS shows the
switch under Model ("BET DAY (A1-A8)").

## What each step does while women's matches are off

| Step | Effect |
|---|---|
| A1 | Unchanged. Its downloads are shared, and the model is trained on both tours |
| A2 | A women's listing is left out before any linking (no Tennis My Life event, Stage 0 name or TennisLive request), with the reason "women's matches are switched off". The listing gives their count in one line; the `_linking` file keeps every row |
| A3 | Only men's matches are written. `check_matchups` refuses a women's row typed by hand (the fallback) |
| A3b, A4 | Men's matches only, as A3 wrote them. The daily engine is unchanged |
| A5 | A live run made before the switch keeps its women's predictions in its files. The record and the sheet leave them out, "Not predicted" leaves out the women's listings, and one note says how many. A replay (C8) keeps both tours |
| A5b | Only the run's men's matches are repriced |
| A7 | Every run is still graded in full by the engine (its files are the record). The states and figures shown are the men's matches'. A run with women's predictions is graded again only when a men's result arrives, and a women's run alone is not listed |
| A8 | The ledger file keeps every prediction. The reading (the summary and its table) is the men's matches', with one line saying how many women's predictions it leaves out |

## What is not switched off

The scheduled downloads, the lower-level feed, the shared tables (B6), the builds, the replay proof and the training
rows keep both tours. The live instance's frame holds 34,874 men's and 32,657 women's rows, and `in_tour` is an input:
the model is trained on both tours together, and a retrain needs the women's data current.

## Why this design

* **Linking is where women's matches cost time and fail** (28 Oct):
  * A3's 14:53 slate held 21 predictable matches, 12 of them women's.
  * A4 at 14:58 stopped on two women's Guangzhou matches whose ids Tennis My Life had re-keyed (process log, Part 23):
    seven minutes lost, then a second run.
* **Inside A4 the women's share is small.** The engine's women's box-score fills found nothing to fill in the last 8
  live runs. The states step's 7 women's IOS jobs add about 90 s to a full recompute (66–150 s each, against the
  men's 250–400 s, on 7 workers). The engine is left unchanged: skipping women there would save little and need the
  replay proof.
* **No men's pick moves.** The engine and its inputs are unchanged, and a men's match's inputs are built per player and
  tour. Checked on the 15:30 run of 28 Oct: its sheet remade with the switch, at the original sheet's own time and
  parameters, gives the same 9 men's rows in all 80 columns as the owner's 15:53 sheet, without its 12 women's.

## Evidence

On 28 Oct's files, read only (process log, Part 24):

* **A2** on the 14:52 pull: all 22 women's listings left out with the switch's reason; the 29 men's rows with the same
  status as A3's 14:53 file, and the same 9 predictable matches.
* **A7:** the 3 runs due show their men's matches' log losses (19 women's predictions left out of the figures). The 15
  runs up to date show the same states as before; those without women show the same figures.
* **A8:** the reading covers 211 of the ledger's 353 predictions (111 of 196 matches); the file keeps all 353.
* **Tests:** 15 new (`test/master_pipeline/test_women_switched_off.py`). Each sets the switch itself, so they hold either
  way. The two tests of the linker's women's code ask for both tours by name.

## Left to the owner

* When to switch women back on. The evidence for it accrues only in the predictions already made (11–28 Oct): A8's
  ledger file and the runs' grades keep them.
* The owner's "while you fix a single row it shouldnt hold up the whole pipeline" (process log, Part 23, P23.9) is a
  separate change: a live match the run cannot place would be left out with its reason, not stop the run. It is
  proposed there, for the owner to decide.

## Amended later on 28 October 2026

The owner asked for that change the same evening ([one bad match left out](2026-10-28-one-bad-match-left-out.md);
process log, Part 25). Since then A3's `check_matchups` no longer refuses a women's row typed by hand. It flags the
row with the switch's reason, loudly, and A4 leaves it out of the run, which predicts the other matches. A4's last
lines name it, as one left out by the switch, not as an error.
