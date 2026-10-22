# Free Pinnacle tennis prices for the missing months (August 2025 on)

21–22 October 2026 · Written for the owner · Research, with the changes you asked for on 21 October. How it was done, step by step: [process log](process_log.md).

**What you asked** (21 Oct 2026): "Scour the internet to find free 2026 pinnacle tennis odds, we need to fill in that missing gap for our data model"

**The gap.** The model trains on Pinnacle's closing price where we have it. Pinnacle shut its public data service on 23 July 2025, and from August 2025 the model has trained on BetOnline's closing price (5,263 matches) or the books' average (323).

## The answer in short

1. **Found: TennisExplorer (tennisexplorer.com) shows Pinnacle's match-winner price for ATP and WTA tour matches, free, without logging in.**
   * Each match page lists about 15 bookmakers, Pinnacle among them.
   * Each price comes with every change and its time, and with the opening price and its time.
2. **It covers the gap.** Every match page since August 2025 is downloaded: about 6,300 pages, no block. The site has a Pinnacle price for 97% of the model's 6,130 matches since August 2025.
3. **It is Pinnacle's price.**
   * Against our own recordings of Pinnacle's website (18–20 October 2026): the same to the cent on 210 of 227 readings. The rest look like the site recording a change a little late.
   * Its margin is Pinnacle's: 2.8–2.9%.
   * Its last price before a match comes a median of 42–65 minutes before the listed start. That is a little earlier than a true close.
4. **One limit: August – October 2025.** There the site's Pinnacle price has no times, and it is the same number tennis-data.co.uk has (on 91–95% of matches). Neither is known to be Pinnacle's close.
   * tennis-data's Pinnacle column matched our other record of Pinnacle's close (OddsTrader's, with times) 62–73% of the time in each of the first three weeks of July 2025.
   * From 24 July, the day after the shutdown, that fell to 9%.
   * The site's times return around 24–27 October 2025.
5. **The site has errors of its own, and the model is now protected from them.** In 2026:
   * on 3 matches its Pinnacle price disagrees with its own other 14 books, BetOnline and tennis-data;
   * on 1 match its whole page has the two players' prices the wrong way round.

   On those, BetOnline's close stays (details below).
6. **tennis-data.co.uk has errors too:** four matches with the two players' prices swapped. Every book on TennisExplorer agrees with OddsTrader on all four (details below).
7. **Nothing else free covers the gap** (see "Other places checked").

## What changed on your instructions (21 October, evening)

Your words: fill the gap from November 2025 with the site's time-stamped Pinnacle prices in place of BetOnline's close; reverse the 21 October mirror rule so that OddsTrader wins; record the plan where future agents will see it when they rebuild; download Pinnacle's closing values automatically. Then: "DO NOT DO THE TEST YET".

1. **The next retrain trains on the site's Pinnacle closes from 1 November 2025.**
   * It is now the default rule of the step that every retrain runs, so the next retrain applies it by itself.
   * The live model is untouched. It keeps the rule it was built with, and that rule still reproduces its inputs exactly, on all 67,531 matches.
   * BetOnline's close stays where the site has no time-stamped Pinnacle price, or where the site's price is one of its own errors.
   * If the site ever prices under 75% of a month's matches, the step stops rather than quietly falling back to BetOnline.
2. **When OddsTrader and tennis-data are mirror images, OddsTrader now wins.** That fixes the four matches.
   * My first version reached too far: it would also have replaced 18 correct tennis-data prices at the 2021 US Open, where OddsTrader's recording of Pinnacle is known to have failed.
   * It now acts only where the 21 October rule acted.
3. **The note for future agents** is in the project's working guide (CLAUDE.md), which every session reads. It says:
   * the closing-line rule from 2025 on changes at the next retrain;
   * the test build was deferred by you, so nobody runs it until you ask.

   Your words are kept verbatim in the decision record.
4. **Pinnacle's closing prices now download every morning** with the other daily downloads (7:30).
   * Each run fetches the finished tour-level matches of the last three weeks, usually 20–80 pages, about 5 minutes.
   * A refusal by the site pauses the job and shows a Windows notification. Any other failure notifies the second time in a row.
5. **Not done, as you said: the test build** comparing the new rule with the current model. I also held back a reading of how well the site's prices predicted 2026 results, because it reads the same seasons that test will.

**What the next retrain will change** (counted on the live model's matches, nothing fitted):

| | Matches |
|---|---:|
| BetOnline's close → the site's Pinnacle | 4,311 |
| The books' average → the site's Pinnacle | 232 |
| tennis-data's swapped Pinnacle → OddsTrader's Pinnacle (2023, 2025) | 2 |
| **All** | **4,545** |

Months from November 2025: the site's Pinnacle prices 87–98% of each month's matches.

## The matches with wrong prices

**tennis-data's rows with the players' prices swapped.** The live model is fed each of these upside down:

| Match | The live model's chance for the first-named | Every book on TennisExplorer |
|---|---:|---|
| Bergs v Alcaraz, Shanghai 2026 | Bergs 90% | Bergs about 10% |
| Zverev v Fery, Wimbledon semifinal 2026 | Zverev 16% | Zverev about 85% |
| Gauff v Sabalenka, French Open final 2025 | Gauff 69% | Gauff about 33% |
| Konjuh v Sherif, Lyon 2023 | Konjuh 33% | Konjuh about 69% |

**The site's own errors**, where BetOnline's close stays:

| Match | What is wrong on the site |
|---|---|
| Kopriva v Engel, Munich 2026 | Its Pinnacle row is the mirror image of its other 14 books |
| Carreno Busta v Halys, Doha 2026 | Its Pinnacle row is far from its other books |
| Guo v Kessler, Roland Garros 2026 | Its Pinnacle row is the mirror image of its other books |
| Atmane v Tiafoe, Washington 2026 | All its books have Atmane (ranked 56) as a heavy favourite; BetOnline and tennis-data have Tiafoe (ranked 19) |

## Which is more accurate in 2026: Pinnacle's last price, or BetOnline's closing price?

Your question of 22 October.

**What is compared.** For each match there are two prices, both taken shortly before it started:
1. **Pinnacle's last price before the match**, as TennisExplorer recorded it.
2. **BetOnline's closing price**, as OddsTrader recorded it (the price the model trains on now).

Each price is turned into a win chance (the bookmaker's margin removed). Each chance is then scored against who actually won. The score is the standard one for forecasts ("log loss"): giving the winner a high chance scores well, and being confidently wrong scores badly. Lower is more accurate.

| Matches compared | Pinnacle's score | BetOnline's score | More accurate | Chance Pinnacle is truly the more accurate |
|---|---:|---:|---|---:|
| **Nov 2025 – Oct 2026, every Pinnacle price TennisExplorer recorded** (4,371) | 0.5883 | 0.5882 | BetOnline, by 0.0001 | 37% |
| Nov 2025 – Oct 2026, **without the 69 Pinnacle prices the model won't use**: 4 that TennisExplorer recorded wrongly, and the rest shown without times (4,302) | 0.5881 | 0.5884 | Pinnacle, by 0.0003 | 74% |
| The same, **2026 matches only** (4,229) | 0.5882 | 0.5885 | Pinnacle, by 0.0003 | 75% |

* **The two prices are about equally accurate.** The scores differ in the fourth decimal place.
* **The data cannot say which is better.** One season of about 4,300 matches can only show a difference of about 0.001 or more. Every row is well inside that, so none is a result.
* **The first row was fixed before any result was looked at.** The second row leaves out the prices the model will not use. The four wrong ones (described above) cost Pinnacle's score more than its whole lead.
* **Other evidence leans to Pinnacle:**
  * in January – July 2025, Pinnacle's last price on TennisExplorer was more accurate than BetOnline's closing price, with a 93% chance;
  * over 2018–2025, Pinnacle's own closing price beat BetOnline's clearly.
* **BetOnline's price is usually taken later:** a median 23 minutes before the start, against 46 minutes for Pinnacle's on TennisExplorer.
* **Margins:** Pinnacle 2.8%, BetOnline 4.0%.

## How a bad Pinnacle entry is caught and replaced

Every Pinnacle price from TennisExplorer passes three checks before the model may train on it:
1. **It must carry a time.** 65 prices of November 2025 – October 2026 have none and are not used.
2. **It must agree with the site's own other bookmakers.** About 14 other books are on each match page. If they agree among themselves and Pinnacle's price is far from them (more than 10 points of win chance), it is a recording error. 3 found.
3. **It must not be contradicted by both outside sources.** These are BetOnline's close (OddsTrader) and the bookmakers' average (tennis-data). If those two agree with each other and both contradict the site, the site's page is wrong. 1 found (Atmane v Tiafoe).

A price that fails is replaced by BetOnline's close.

**Ordinary disagreement is not treated as an error.** Pinnacle often disagrees with other books, and when it does it is usually right (the October odds study). Only gross gaps count, so a small recording error could pass.

**The same goes the other way.** When tennis-data's row is the bad one (the four swapped matches), OddsTrader's price is used. From 2018 OddsTrader's records cross-check tennis-data. For 2013–2017 there is no second source:
* I checked all 14 matches from 2013–2026 where the odds make a far lower-ranked player a strong favourite;
* 13 were genuine: del Potro in 2016, Sharapova in 2017, Kyrgios in 2022, Nadal in 2024, Vondrousova and Bencic after time away;
* 1 was the known Zverev v Fery swap.

A full check of 2013–2017 would take about 28 hours of downloading to find perhaps 1–2 more swapped rows out of 67,000. I don't recommend it.

## Still open (my recommendations)

1. **End tennis-data's Pinnacle prices on 23 July 2025 instead of 31 July.** From 24 July they are no longer Pinnacle's close (point 4 above). About one week of matches. Not in your instructions, so not changed.
2. **The test build, when you want it.** It would also be the moment to read how the site's prices did against BetOnline's on 2026 results.
3. **August – October 2025 stay as they are** (OddsTrader's Pinnacle to 7 September, BetOnline after). No free time-stamped Pinnacle price exists for them that I could find.

## How close the site's last price is to Pinnacle's own close

Checked on January – June 2025, when tennis-data's column was still Pinnacle's own close (about 3,400 matches; downloaded on 22 October, finished 05:07, no block):

* **The same to the cent on 43–57% of matches a month.** The median gap is 0.002–0.014 in log-odds, under half a point of chance.
* **A gap over 0.1 in log-odds on 2–5%,** and a gross gap on 1 match.
* **For comparison:** our two direct records of Pinnacle's close agreed with each other to the cent on 55–72%.

So the site's last price is a close stand-in for Pinnacle's close, a little less exact.

**One caution for 2026.** The site's last price came a median 21–22 minutes before the listed start in early 2025, but 42–65 minutes before it in 2026. Its 2026 prices may sit a little further from the true close than this check shows. Nothing free measures that directly. Our own recordings near the start agreed on 5 of 6 matches.

## Other places checked

| Source | What it has | Why not used |
|---|---|---|
| **BetExplorer** | Opening and closing prices for many books | From this connection it lists no Pinnacle row, on a 2026 match and a 2024 one alike |
| **OddsPortal** | Many books, Pinnacle among them in some countries | Not tried: same owner as BetExplorer; its data are scrambled and depend on the visitor's country. Not needed once TennisExplorer worked |
| **OddsPapi** | Says its free plan includes Pinnacle's price history from January 2026 | Needs an account in your name (not created without asking). Its free plan allows 250 requests a month, one match each: the gap would take about two years |
| **pinnapi, PinnOdds, PinnWire** | Pinnacle's current prices, resold since the shutdown | Live prices only; no history |
| **The Odds API, BettingIsCool, OddsMarket, OddsLink** | Pinnacle history | Paid only (from about $30 to €599 a month) |
| **Apify scrapers** | Ready-made scrapers of Pinnacle and of TennisExplorer | Paid per result; they read the same pages we now read ourselves |
| **GitHub, Kaggle** | Tennis datasets | None with Pinnacle's 2025–26 prices |
| **Pinnacle's own site** | Current prices | No history. We already record it on bet days |

## Where things are

* **The site's pages:** every page as downloaded, with a receipt for each request. Kept on this machine only, in the data folders the project does not publish. The adapter is `src/ingest/tennisexplorer.py`.
* **The checks:** `data/studies/pinnacle_gap/` (counts only, no prices). Re-run them with `./python.sh src/eda/pinnacle_gap/check.py --no-accuracy` and `./python.sh src/eda/pinnacle_gap/dry_run.py`.
* **The rule:** `src/eda/current_best_model/odds_input.py`, recorded in the [decision](../../decisions/2026-10-09-pinnacle-first-odds-input.md) (amendments of 21 October).
