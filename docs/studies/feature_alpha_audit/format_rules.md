# Forecast format repair

Implemented 2026-10-02 in `src/eda/predictability_diagnostic/scheduled_format.py`.
The original Stage 0 `format` is a retrospective score-anatomy label. The raw
`best_of` also mislabels 113 men's Wimbledon final qualifying matches as best of
three. Neither column now determines a forecast's match format.

The repaired helper uses tournament name, tour, year, level, qualifying status
and the scheduled round. It covers this study's 2010–2026 singles scope:

| Event | Forecast format |
|---|---|
| Men's Grand Slam main draw | Best of five |
| Men's Wimbledon final qualifying round (Q3) | Best of five |
| Other Grand Slam singles, including qualifying | Best of three |
| ATP/WTA 1000, 500, 250, Challenger/125 and ordinary Finals | Best of three |
| Next Gen Finals | Known short/no-ad sets; excluded from the ordinary iid conversion |
| 2021 Yarra Valley Classic, Gippsland Trophy, Grampians Trophy | Excluded pending independently timestamped match-format metadata |
| ITF, team events, unknown or incomplete rules | No match probability from this helper |

The existing Grand Slam deciding-set rule table remains the rule source for set
tiebreaks. Score reconstruction remains available through the explicitly named
`retrospective_best_of_five` helper for retrospective simulations. Prediction
paths use `scheduled_iid_prob`; unknown formats return NaN instead of silently
becoming ordinary best-of-three or best-of-five matches. The repaired dated
history also uses scheduled metadata for box-history eligibility and excludes
unsupported event editions. This is conservative: some point counts may be
usable, but whole-event classifications inferred from later scores must not
decide whether an earlier observation enters a forecast's history. The original
observed format label is retained separately for provenance.

The Melbourne exclusions cover entire event editions by metadata. Official WTA
reporting documents a mid-event switch to match tiebreaks. The stored tournament
date cannot identify which rules applied before an individual match, and a
straight-set result cannot reveal whether a match tiebreak was scheduled.
This is deliberately conservative; the exclusion does not inspect match outcomes.

Sources checked 2026-10-02 (public web documents; source claims about rules,
not evidence of executable historical prices):

- [2025 Grand Slam rulebook, section I.L](https://www.wimbledon.com/pdf/Grand_Slam_Rulebook_2025.pdf): men's main draw best of five, other events best of three subject to tournament exceptions.
- [Wimbledon 2019 Compendium, Qualifying Competitions](https://www.wimbledon.com/pdf/TheWimbledon_Compendium_2019.pdf): men's final qualifying round best of five since 1972, with exceptional years all preceding this study.
- [ATP's Wimbledon qualifying report, 2023](https://www.atptour.com/en/news/arnaldi-albot-wimbledon-qualifying-2023-thursday): confirms continued men's best-of-five final qualifying.
- [Next Gen official format](https://www.nextgenatpfinals.com/en/event/format) and [ATP's 2024 rules briefing](https://www.atptour.com/en/news/next-gen-2024-player-briefing-rules-and-innovations): short sets, best of five; the current ordinary-set iid model is inappropriate.
- [WTA's 5 February 2021 preview](https://www.wtatennis.com/news/2015495/saturday-wta-500s-preview-osaka-muguruza-looking-for-spot-in-finals): the Melbourne events changed to two regular sets followed, if needed, by a ten-point match tiebreak.

Coverage of ordinary ATP/WTA evaluation tiers across the study years is a
historical scope assumption; unrecorded exceptional tournament rulings remain
possible. No fresh out-of-sample validation is created by this implementation fix.
