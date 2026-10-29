# Jakub Mensik's second player id is merged into his established one

**The owner's decision, 28 October 2026**, on Claude's recommendation of 27 October (master pipeline process log,
Part 17, P17.12). Verbatim:

> fix the alarm and fix mensik

The alarm half is [its own decision](2026-10-28-alarm-counts-matches.md). **The design below is Claude's** (an agent's
choice, in the production-integrity plan's sense): the alias's direction, and A2 reading the alias table.

## Why

* Stage 0 held Jakub Mensik under two ids:
  * `atp:210150`: 291 matches, June 2021 to October 2026, at every level;
  * `atp:210084`: 11 Challenger and Challenger-qualifying matches of 9 January to 1 May 2023 (Nonthaburi 2 and 3,
    Cherbourg, Les Franqueses del Valles, Ostrava, Prague). They come only from Sackmann's archive file
    `atp_matches_qual_chall_2023.csv`, which gave him a second id.
* **One person.** Both ids carry the same name and country (CZE). Their ages give a birth date in September 2005. No
  week has a match under both.
* **What it cost.** A2 left out every listing of his: "'Jakub Mensik' names 2 Stage 0 players: the run would stop".
  A run given his match would stop at its own name check (`prediction_run/run.py`), with every other match. His
  inputs also lacked those 11 matches.

## Decision

* **One row in the decided id aliases** (`data/studies/input_data_audit/fixes/id_aliases.csv`):
  `atp,atp:210084,atp:210150,jakub mensik`.
  * Every Stage 0 build maps the second id's rows to the established id (`stage0_build.apply_id_aliases`). That covers
    A3b, the bet-day engine's tables (its work tree copies the repository's tables) and the shared tables at their
    next rebuild.
  * A replay reads the instance's build-tree copy, without the row, so it rebuilds the tables that instance was built
    on.
* **A2's name check applies the same table** (`src/pipeline/live._stage0_keys`). The check reads the shared Stage 0,
  built on 21 Oct with both ids. With the table applied, his name names one player now, not only after the shared
  tables' next rebuild. Any later alias takes effect there the same way.
* **Training takes it at the next retrain.** It is registered in `data/studies/current_best_model/pending_at_retrain.json`
  (`2026-10-28-mensik-id-alias`), with its check `src/eda/input_data_audit/verify_aliases.py`: no player row under
  the second id, and rows under the established one. The live instance keeps his two ids in its training rows until
  then.

## Evidence

* **A Stage 0 build on 28 Oct's files** (`stage0_build.py --out-dir`, in a scratch folder; 84 s, exit 0):
  * 11 rows mapped to `atp:210150`;
  * Mensik is one player with 303 matches;
  * `verify_aliases.py` passes 12 of 12 aliases.
* **On the shared tables of 21 Oct** the check still fails on `atp:210084`, as it should until the next rebuild.
* **A2 on the shared tables:** "Jakub Mensik" links to `atp:210150`.
  * In the recorded listing of 9 Oct, his Shanghai match (v Cerundolo) now passes the name check.
  * In that recorded listing it is left out only because the match was already played.
* **The bet-day engine:** a change to history before its checkpoint makes it recompute the families that read that
  history. It does this routinely: on 25 Oct six families were recomputed for other changes, and the states step took
  478 s.
* **Tests:**
  * `test/master_pipeline/test_id_aliases_link.py` (2) and `test/input_data_audit/test_verify_aliases.py` (4), both new;
  * `test_master_pipeline.py::test_linker_on_the_probe` had asserted the ambiguity. It now asserts his row passes the
    name check.

## Not covered

* **Other players with a second id are not searched for.** A2 reports each one when his name is listed ("names 2
  Stage 0 players"). Namesakes are real, so each needs the same look as this one before a row is added.
