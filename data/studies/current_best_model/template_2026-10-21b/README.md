# template_2026-10-21b: the first retrain with its odds input repaired

The owner's word, 21 Oct 2026 (afternoon), to the question "Correct the live model now? A corrected copy of today's
retrain with the repaired odds (288 recent matches to BetOnline, 3 mirrored prices replaced, the new mirror rule), the
same checks as this morning, and a switch only if they pass": **"Yes, start now (Recommended)"**.

* **The build:** `template_2026-10-21`'s, unchanged (the tables of 21 Oct, rebuilt 13:47 UTC; build tree
  `C:/Users/zerom/tnr_tpl1021`): its chain frame and input list and the build's records were copied here; nothing was
  rebuilt (`SKIP_BUILD=1`).
* **The repair:** the finishing steps (the notebook's `finish_instance`) with the odds step of 21 Oct afternoon:
  OddsTrader's tables brought up to date first (the link and the every-book pull had stayed at 9 Oct, so the matches
  from late September stood on the books' average), and an OddsTrader price that is the mirror image of tennis-data's
  books left out. Expected against `template_2026-10-21`: 291 rows (2026: 288 average → BetOnline, 1 BetOnline →
  average; 2023 and 2025: 1 each, a mirrored OddsTrader Pinnacle → tennis-data's Pinnacle).
* **Then the retrain's own path** (`src/eda/in_season_retrain/retrain.sh`): the cut-off, stage 2's speed table, the fits,
  the harm check against `template_2026-10-21` (the instance in use), the switch with its replay proof, the remaining
  evaluation fits. Log: `data/studies/in_season_retrain/retrains/template_2026-10-21b.log`.
* **Report:** `docs/studies/in_season_retrain/README.md`; process log § 4c.
