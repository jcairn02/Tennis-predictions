# The women's model to-do list: process log

16 Oct 2026, 13:50–14:10 (local, UTC−7) · Kept by Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code (VS Code) ·
Session: `c0f7c8d9-cc78-498f-9409-72258b59a7dd` · For a future reviewer · Report: [to_do.md](to_do.md)

## 1. The request

* **The owner's words, verbatim** (16 Oct 2026, about 13:40):
  > "And start a "to_do" list for womens model , as its currently needs a fix to be bettable. Maybe fill in data holes, new stats. Including relating lower level to high level matches etc. Adding the data thats not in for it"
* **Earlier the same session, verbatim:** "I currently see womens matches as unbettable , I have to do a deeper dive on
  the data missing and how its aligned."
* **How it was read:** a working list for the owner, compiled from what the project already knows, ordered, each item
  with its reason, status and next step. No data was changed and no model result was read for it.
* **Set aside:** starting any item. The owner asked for the list. Item 1 (marking women's matches "do not bet") was
  offered earlier in the session and not taken up.

## 4. Chronology

| When | Step | Output |
|---|---|---|
| 13:20–13:40 | Counts of the held-out women's data, by tour, level, year and reach (the session's scratch scripts on the 9–10 Oct candidate, the live tables, the packages and the feed) | The numbers in items 2c and 2d |
| 13:47–13:50 | Status checks: Nottingham and Berlin; women's Slam qualifying box scores; women's serve speeds | Items 2a, 2b, 4a |
| 13:50–14:10 | The list written | `to_do.md` |
| 14:33 | A row for the list in the studies index (`docs/studies/README.md`) | – |
| 18:11 | Item 6 gains the 16 Oct rebuild's women's 2024 reading (−0.125 [−0.227, −0.022], one of 21 slices; not deciding), from the men's fill's harm check | `to_do.md` |

## 5. Sources

Every item rests on a project document read in this session (no outside source):
* the 2026 data-gaps report, § 7 (items 2a, 2b, 2e, 2f);
* the lower-level evidence dossier, §§ 1.3, 3.2, 3.3, 4 (items 3, 5);
* the level-evidence study's README, § 4 and § 3.3b, and its role B report, § 6 (items 3 and 2d; the fitted result
  weights read from its frozen parameter table);
* the feature universe, § 6, point 7 (item 4c);
* the serve-speed acquisition report, the line on WTA speeds (item 4a);
* the adoption checklist, item 3 (item 1);
* the master-pipeline README (item 6, the 14 players);
* the indoor-input decision (item 6).

## 6. Judgment calls

1. **"Untouched" women's matches start in October 2026.** The proposed seal began on 29 July. The unpriced-leads check
   then read matches to 23 Sep 2026, and the feed's harm check read 2025–2026 seasons. So the list says "from October
   2026 on".
2. **Item 2c waits for item 3.** The holes pass the 14 Oct rule, but entering them at full weight now and at fitted
   weights two weeks later would change women's inputs twice.

## 8. Weak points

* The counts in items 2c and 2d come from the 9–10 Oct candidate, matched to today's tables by id and by players and
  date. A fresh build would change them slightly.
* The weights quoted in item 3 are the frozen table's fitted values for 2024–2026, not yet tested for women at the model
  level.
