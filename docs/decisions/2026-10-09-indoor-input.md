# The indoor input covers every match: women's matches and the men's 2026 US Open filled

**Requested by the owner on 9 October 2026.** Integrated and recorded the same day, after a harm check fixed before any fit ran ([study](../studies/indoor_fill/README.md)). The owner's words:

> "In my current best performing model the indoor/outdoor input is missing for every women's match. It could be filled from tennis-data.co.uk's Court column. Get this data and integrate it into our models training data sources after you've downloaded it all"

> "The 127 men's matches of the 2026 US Open are also missing it, obtain them if you can find them"

**One choice in carrying it out is Claude's recommendation, for the owner to confirm: the women's value comes from the WTA's own calendar first, and tennis-data's Court fills only what the calendar lacks.**
* tennis-data's Court is wrong on 26 of the model's 1,609 events. Each was checked against the venue: seven events by web search, three from general knowledge ([process record](../studies/indoor_fill/process.md)). Examples: Stuttgart 2013–17 is listed outdoor though it is played indoors on clay; Santiago 2020–26 is listed indoor though it is outdoor clay.
* On each of those events the other source is right: the WTA's calendar on all 16 women's events, Tennis My Life's flag on all 10 men's.
* The WTA's calendar also lists an edition before it starts, so prediction runs can use it live.
* Court alone would differ on 371 women's matches (1.1%). To use it instead, put "own" and "event" before "calendar" in `STEPS["wta"]` (`src/eda/indoor_fill/status.py`).

## Decision

1. **The model's `indoor` input** (one of the 57) is the rule of `src/eda/indoor_fill/status.py`. `src/eda/tabpfn_thinking/build_frame.py` applies it in every build of the chain.

   | Tour | Source, in order |
   |---|---|
   | Men | Stage 0's flag (TML's event field), as before; then tennis-data's Court (the match's own row, then its event's rows); then the previous edition |
   | Women | The WTA's calendar (the edition's `inOutdoor`); then tennis-data's Court; then the previous edition; then Stage 0's flag |

   * On the model's 67,226 matches no value is unknown, and no value the model already had changes.
   * What it fills: the 32,507 women's matches, and the 127 of the men's 2026 US Open (outdoor, from tennis-data's own rows).
2. **Live.**
   * A prediction run (`run.py --refresh --matchups`) fetches the WTA's calendar pages of its women's seasons again.
   * The build records each live match's value and source (`live_indoor.csv`).
   * The gate marks "do not bet" any live match whose indoor input is unknown.
   * With every tennis-data link of a season removed, the rule still gives every 2018–2026 model match its training value.
3. **What does not change.**
   * Stage 0's `indoor` column, and with it the training-history check.
   * The frozen reference, the Pinnacle-first instance of 9 Oct and the lean review's arms keep the old input (women missing). They stay as built.
   * The shared tennis-data dump. The fresh download is kept beside it (`data/raw/indoor_fill/tennis_data_couk/`): other sessions' builds were reading the dump. The routine refresh restages it; Stage 1's links stay valid.

## Evidence

**The harm check.** The lean review's arm A2 (the current best model's 57 inputs on the tables of 8 Oct) against the same frame with `indoor` filled: 2020–2024, both stages, seeds 0–3 paired, + = the fill better.
* At Pinnacle's opening line, the declared primary: both tours +0.007 [−0.014, +0.029] mLL per match, unresolved, P(better) 0.75. Women +0.013 [−0.023, +0.050] (0.76); men +0.002 (0.58).
* At the close: both tours −0.002 [−0.016, +0.013] (0.41); women +0.001 (0.53); men −0.004 (0.38).
* Realisation at the opening line: 1.056 → 1.061, so the model does not over-react.
* Under the rule fixed before any fit: adopt, claiming no edge.

**Against the frozen reference** (`compare.py`). The candidate also carries the decided Pinnacle-first odds input and the dropped input.
* Both tours +0.007 [−0.31, +0.32], unresolved.
* The input check flags `indoor` in exactly the 14 women's seasons, where it goes from missing to known. That is the fill itself; the women's indoor share moves with the calendar (5–13% a season).

## To undo

* Build with `tabpfn_thinking/build_frame.py --indoor-men-only`, or make that the default. The frame then has the old input again, Stage 0's flag for the men only.
