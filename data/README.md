# data/ layout

```
raw/                          (gitignored — rebuild via src/ingest/)
  sackmann/
    atp/   atp_matches_YYYY.csv, atp_players.csv, atp_rankings_*.csv
    wta/   wta_matches_YYYY.csv, wta_players.csv
  tennis_data_couk/
    atp/   YYYY.xlsx (results + closing odds: B365, Pinnacle PS, Max, Avg)
    wta/   YYYY.xlsx
processed/                    (built by future pipeline steps)
studies/<study_name>/         (per-study outputs)
```

## Column conventions to remember

- Sackmann `tourney_date` = tournament START date (YYYYMMDD int), not match date.
  Within-tournament chronology comes from `round` order (R128→R64→…→F). The loader
  builds a sortable round rank; matches on the same date+round keep file order.
- Sackmann rows are winner-first (`winner_name`/`loser_name`) — like the UFC men_only
  CSV, you MUST randomize side assignment for pairwise modeling or you leak the label.
- tennis-data.co.uk odds columns: `PSW`/`PSL` = Pinnacle closing decimal odds for the
  match winner/loser; `B365W/L` = Bet365; `MaxW/L`,`AvgW/L` = market max/average
  (Oddsportal-derived); `BFEW/BFEL` = Betfair Exchange (2025+ files, undocumented in the
  site's notes.txt).
- **PSW/PSL are DEAD from Feb 2026** (94.5% blank in the 2026 file — OddsPortal delisted
  Pinnacle in Jan 2026). The sharp-price reference must splice PSW→BFEW around
  Oct 2025–Jan 2026, and the two differ (vigged book price vs commission-free exchange
  price). See docs/02_data_and_tools.md.
- All odds in tennis-data.co.uk are DECIMAL (unlike the UFC pipeline's American odds).
