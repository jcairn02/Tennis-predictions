# The women's model: what it needs before women's matches are bettable

16 Oct 2026 · For the owner · **A working list, not a decision.** Tick items as they are done, and add new ones at the
end of their section. [Process log](process_log.md).

**Where things stand.** You treat women's matches as unbettable for now. The evidence supports that:
* **The women's edge over the market has never been clear.** In past seasons the model leaned ahead of Pinnacle's closing
  prices on women's matches, and simulated bets leaned profitable at Pinnacle and BetOnline, but none of it was clearly
  above zero.
* **The men's fix for lower-level matches (10 Oct) does not apply to women.** Women's lower-level matches (WTA 125,
  ITF, qualifying) still count as if they were main-tour matches.
* **Several data holes hit women harder than men.** Women's lower-level evidence is mostly ITF, and ITF data is the
  patchiest.

**Suggested order:** item 1 now; items 2a and 2b next (small and clear); item 3 when the older ITF statistics land
(about 22 Oct – 2 Nov), with items 2c and 2d decided inside it; item 5 after item 3; item 4 as time allows.

## 1. Stop bets on women's matches until this list is done

- [ ] **Make the bet sheet mark every women's match "do not bet".**
  * **Why:** you've decided they are unbettable, so the sheet should say so. Today it treats women's matches like men's.
  * **Status:** not done. A softer version (no stakes or token stakes on women's matches) was recommended on 9 Oct and
    never decided.
  * **Effort:** under an hour.

## 2. Fill the data holes we already have on disk

- [ ] **a. Women's Slam qualifying statistics, 2026.**
  * **What:** 336 matches are in the model as results only. The WTA's own data counts these statistics differently from
    ours (only 4–37% of counts agree), so they were left out.
  * **The fix:** the Slams' own records count the same way as ours, and they are on disk (Roland Garros, the Wimbledon
    and US Open feeds).
  * **Status:** recommended on 13 Oct, not done. **Effort:** an hour or two.
- [ ] **b. Nottingham and Berlin 2026: 58 women's main-tour matches without statistics.**
  * **Why:** the women's grass-season form numbers of June read them.
  * **The fix:** the WTA's own data has them. It is a main-tour repair, decided on the data evidence.
  * **Status:** recommended on 13 Oct, not done. **Effort:** about an hour.
- [ ] **c. About 4,400 women's lower-level matches the history lacks, plus 118 statistics.**
  * **What:** ITF main draws 3,177; WTA 125 qualifying 460; tour qualifying 308; Slam qualifying 214; WTA 125 main
    draws 207 (2010–2026). Plus 118 box scores from the WTA's own data for WTA 125 and qualifying matches we hold as
    results only.
  * **Why:** about 2,300 of the matches involve a player who also plays the main tour.
  * **Status:** they pass the 14 Oct rule for filling holes, by my reading. Same route as the men's package of 16 Oct.
  * **Recommendation:** add them together with item 3, so they enter once, at the weights item 3 sets.
- [ ] **d. Women's ITF qualifying, 2010–2018: about 82,000 results the history lacks.**
  * **What:** today the history has women's ITF qualifying only from 2019 (almost none before 2017). Adding these would
    make the record even across seasons.
  * **Why it needs a test:** it changes what women's rating and workload numbers mean in the seasons before 2019, which
    the model learned from. About 10,100 involve main-tour players.
  * **Recommendation:** decide it inside item 3's test.
- [ ] **e. Women's ITF statistics, June to mid-September 2026: a hole with no consistent source.**
  * The ITF's live data starts on 15 September; SofaScore's 2026 ITF statistics lack break points; TennisLive's miss
    points in about 15% of matches. The results are in; the statistics are not.
  * **Status:** accepted as a known hole (the coverage alarm ignores it until 31 January 2027). Nothing to do unless a
    source turns up.
- [ ] **f. Bet days see women's lower-level matches up to a week late.**
  * **Why:** the lower-level feed refreshes on Wednesdays. A player who played a WTA 125 or ITF event since then is
    missing those matches on a bet day, and the bet-day check cannot see a match the table lacks.
  * **Options:** run the feed by hand before a bet day (about an hour), or make the bet-day check look at TennisLive's
    daily listing for missing matches.

## 3. Relate lower-level matches to main-tour matches (the women's version of the men's fix)

- [ ] **Translate women's lower-level matches into main-tour terms, and count them at fitted weights,** as men's have
  been since 10 Oct.
  * **Why:** today they count as if they were main-tour matches. For return statistics that is known to mislead:
    pooling them as equal predicted women's later main-tour statistics worse than ignoring them. Translating them
    predicted clearly better than both.
  * **The weights are already estimated.** For example, a WTA 125 result counts about three-quarters of a main-tour
    result, and an ITF result about half to three-quarters.
  * **The blocker:** women's lower-level evidence is mostly ITF, and ITF statistics exist in our history only for 2025
    and 2026. The adjustment has to be learned from earlier seasons. SofaScore's 2018–2024 ITF statistics are
    downloading now (due about 22 Oct – 2 Nov), and the test plan is written.
  * **Decided inside it:**
    * **Today's women's ITF statistics,** which count in full but appear only from 2025. Removing them leaned better for
      women on 2025–26, about a 78% chance, not clear.
    * **Item 2d,** the ITF qualifying results of 2010–2018.
    * **Item 2c,** the remaining holes, entering at the new weights.
  * **Effort:** a day or two once the data lands.
- [ ] **Revisit how thin-evidence women are rated.**
  * **What:** a woman whose record is mostly lower-level gets her statistic ratings pulled toward an average that is not
    her peer group. In tests, such women's break points saved were over-rated by about 1 point per 100.
  * **Tried before:** starting each player from her home tier's average fixed much of it, but over-corrected in
    2013–2018 and read worse overall, so it was not kept.
  * **Next step:** try it again inside the women's layer, with the ITF data in.

## 4. New statistics for women

- [ ] **a. Serve speed.** The men's model has a serve-speed adjustment; women have none.
  * WTA tour-level speeds are not publicly available (only from data vendors).
  * The Slams' own feeds may hold women's speeds for four events a year. Check how much, before deciding anything.
  * **Priority:** low.
- [ ] **b. Point-by-point profiles.** Your edge thesis is point-level statistics.
  * The WTA's own per-match documents and SofaScore's point data are being collected; women's point-level profiles have
    not been built.
  * **Route:** build them as feature ideas for the pool. New features go to the pool, and selection rounds decide.
- [ ] **c. Coverage gaps in today's women's inputs.** Each is worth a check for a better source:
  * holds, break points faced and return games cover about 74% of women's matches of 2013–2021;
  * height covers 64% of women's matches of 2022–2024 and 39% of 2025–2026;
  * match minutes are estimated before 2016.

## 5. Prove it before betting

- [ ] **A check, fixed in advance, of the women's predictions on matches no choice has read,** at the price you would
  bet at, after costs.
  * **Which matches:** women's matches from October 2026 on, then live. Earlier seasons were used to build and check the
    model, so they flatter it.
  * **Why:** this is what turns "fixed" into "bettable".
- [ ] **Check that the women's probabilities are the right size.** In past seasons the closing price was slightly too
  extreme in women's matches between established players, and the model's probabilities track the price.
- [ ] **Then start small:** token stakes first, and watch whether prices move toward the model after the bet.

## 6. Small open items

- [ ] **The women's indoor input** reads the WTA's calendar first, then tennis-data's court field. That order is Claude's
  recommendation and still needs your confirmation.
- [ ] **14 active players cannot be predicted,** because each one's name matches two player records. Check how many are
  women, and merge the records.
- [ ] **Added 16 Oct 2026: the rebuild of 16 October read worse for women's 2024.**
  * The new model against the one it replaced: −0.125 mLL per match on women's 2024 (95% range −0.227 to −0.022). It
    was the only one of 21 season slices clear of zero. All women's seasons together: −0.023 (P(better) 0.14).
  * It did not decide anything, since the harm check reads both tours together, and one slice in twenty is expected by
    chance.
  * Since 14 October, women's data changed mainly through TennisLive's box scores for 2015–2024 and the weekly feed for
    2025–26. Nothing was traced to 2024 specifically.
  * Worth a look in the deeper dive (item 2): which women's 2024 inputs moved between the two models.
  * The details are in the [men's lower-level fill report](../men_lower_level_fill/README.md).
