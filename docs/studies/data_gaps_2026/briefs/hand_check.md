# Brief: the identity hand check of the lower-level feed's first candidate (F20261013c)

You are checking, by reading, whether a candidate Stage 0 of a tennis research project links source rows to the right
players. Your verdicts decide whether the candidate may be marked READY; nothing else depends on your judgment of
results. You read no match outcome for any purpose other than identifying players, and you score no model.

**The candidate:** `C:\Users\zerom\Documents\Tennis-predictions\data\studies\data_gaps_2026\feed\candidates\F20261013c\`.
It was built by `src/eda/lower_level_evidence/candidate_stage0.py` from seven sources (wta_api, wta_site, tennislive,
itf_live, sofascore, tennislive_pages, tdi) against a frozen Stage 0 (the project's match table of 8 Oct 2026).

**The samples** (written by the builder's checks, seeded): in that folder,
* `identity_sample_links.csv`: a source row read as a match Stage 0 already holds. Columns: the source's two player
  names (`src_p1`, `src_p2`), day, event and round, beside Stage 0's (`s0_a`, `s0_b`, `s0_date`, `s0_event`, `s0_round`),
  and `name_grade` (3 = same full name, 2 = one name inside the other or surname + initial, 1 = surname only, summed
  over the two players).
* `identity_sample_players.csv`: a new match whose player was resolved to an existing Stage 0 player (`route`:
  crosswalk = through the matches both hold; name = the exact name; name_subset = one name inside the other). The
  source's name, country, event, date and round beside that Stage 0 player's name, countries and nearest Stage 0 match.
* `identity_sample_new_ids.csv`: a source player given a NEW id (not found in Stage 0), with the reference players of
  the same tour who share the last name (`reference_same_last_name`).
* `identity_sample_repair_moves.csv`: a player row moved from one id to another by the identity repair (`from_name`
  -> `to_name`, countries, match counts, years).

**The 9 Oct precedent** (a hand check of the same builder's samples), for the standard expected:
`data/studies/lower_level_evidence/system/stage0/C0_now/identity_verdicts.csv`. Read it first. Note its rules: "right"
when it is the same person (spelling, transliteration or a married name aside) and, for links, the same event, week and
round; "wrong" when it is demonstrably a different person (e.g. "Camilo Andres Gonzalez Torres is not Andres Torres: a
shorter name with another given name"), or, for a new id, when Stage 0 already holds the player (a split: same person
under another spelling, e.g. "Meixu Wu is Stage 0's Mei Xu Wu"); "unsure" when it cannot be settled from the rows
(namesakes years apart, given names that differ).

**Your task:** judge every row of the four sample files and write
`data/studies/data_gaps_2026/feed/candidates/F20261013c/identity_verdicts.csv` with exactly these columns:
`kind,source,route,row,verdict,note,by`
* `kind`: links, players, new_ids or repair_moves; `source`: the row's source (`src` in repair_moves); `route`: the row's
  route (empty for links; "new" for new_ids);
* `row`: the row's 0-based index in its sample file (the first data row is 0);
* `verdict`: right, wrong or unsure (nothing else);
* `note`: a short reason, always for wrong and unsure, briefly for right ("same two players, event, week and round");
* `by`: `hand`.

You may look players up in the candidate's and the reference's tables to settle a case (read-only), e.g. with
`./python.sh` (the project's Python) on `stage0_matches.parquet` / `stage0_match_players.parquet` in the candidate folder,
or `data/studies/current_best_model/reference_2026-10-08/frozen/tables/data/studies/predictability_diagnostic/`.
Do not use the web. Do not modify any file other than the verdicts file you write. Do not run the builder.

**Report back** (under 300 words): the counts of right / wrong / unsure by kind and source, every wrong and unsure row
with its note, and anything systematic you noticed (a source whose names are written differently, a route that errs).
