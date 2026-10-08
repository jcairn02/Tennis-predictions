# Latency follow-up: the availability model (speed-data engineer)

8 October 2026. Labels: **observed** (computed here; scripts named), *inferred*, **suggestion**.
* No match result, outcome or price was read, and nothing ran on the GPU.
* The network use is only that listed under Requests.

## 1. Scenario B at tour level: from the commit history

**What the history shows** (observed: `latency/mantd_history.py` → `evidence/mantd_publication.json`).
* **Timing.** All 89 commits touching `matches_2026.csv` and `matches_2025.csv` land on a **Sunday at 16:10 Central European time** (14:10 UTC in summer, 15:10 in winter).
* **Missed weeks:** 2026 missed 4 of 40 Sundays (17 May – 7 Jun); 2025 missed 2 of 52.
* **The diffs:** the 10 consecutive versions of 26 Jul – 27 Sep 2026 against the held head of 4 Oct. A match is published when both first-serve averages appear: 848 new matches, 717 linked to Stage 0 clock days. 98 were rows held a week earlier without speed.
* **Lag from the match day (`obs`) to the publishing commit:**

  | Match day | Next Sunday's commit | A week later |
  |---|---:|---:|
  | Mon | 92 | 0 |
  | Tue | 202 | 2 |
  | Wed | 114 | 2 |
  | Thu | 72 | 20 |
  | Fri | 62 | 9 |
  | Sat | 27 | 60 |
  | Sun (the commit day) | **0 of 43** | 52 |

  * **A Sunday commit never holds that Sunday's matches,** and rarely Saturday's (Saturday finals appeared a week later). The Thursday–Friday delays are mostly Hangzhou and Chengdu.
  * Lag from `lf`: median 5 days, 90th percentile 8.
* **Candidate rules scored** (681 matches whose predicted commit falls in the window):

  | Rule: S = the first Sunday on or after … | Exact | Too early | Too late |
  |---|---:|---:|---:|
  | lf + 1 (the plan's fallback) | 86.5% | 13.4% | 0.1% |
  | **lf + 2** | **91.0%** | 4.9% | 4.1% |
  | lf + 3 | 83.6% | 3.5% | 12.9% |

**The rule fixed** (every non-Slam row: tour level, Challengers, team, ITF; key statistics and point means alike): **S = the first Sunday on or after lf + 2; the row is usable from S + 1, a Monday.**
* Monday–Friday finishes are released the next Monday; Saturday or Sunday finishes a week later. `release_B − lf` is 3–9 days.
* The commit is not used on its own Sunday: up to half a day conservative.

## 2. Scenario B at the Slams

* **Release = the last main-draw day + 1 + 2 days of collection.** The last main-draw day is the latest `lf` of the Slam-year's singles main draw, both tours together (the feeds are collected once, after the event).
* It applies to every GS row, qualifying included, whatever the source: points, Hawk-Eye copies, SlamTracker, Infosys AO/RG, the AO match centre.
* One release day per Slam-year (tested). `release_B − lf` is 3–23 days.

## 3. The file

**`data/studies/serve_speed_tabpfn/latency/availability.parquet`**, built by `src/eda/serve_speed_tabpfn/latency/availability.py` in 30 s:
* **Rows:** one per Stage 0 player-match (1,746,728, rebuilt ids), with `in_panel` / `use` from the speed panel (43,089 / 42,900).
* **Columns:** `lf`, `release_A` (= lf + 1), `release_B`, `release_L1`, `release_L3`, `release_L7`, `release_L14`, `rule_B` (`mantd_weekly_sunday` | `slam_after_event`), `slam_last_main_day`, and `box_release` (= lf + 1; Tennis My Life is downloaded daily).
* The release columns are defined for every row; only `in_panel` rows carry a speed.

**For the modeller:**
* `availability.panel_with_release("B")` returns the panel with a `release` column.
* `panel.EditionOffsets(p, tour, release="release")` then fits each snapshot on rows released by that day. It bypasses the disk cache and takes about 7 s per tour for every frame day.

**Tests:** `test/serve_speed_tabpfn/test_ssp_latency_availability.py`, **7 passed**: one row per player-match with every panel row; exact A, L and box columns; B never before A; the weekly and Slam rules with worked examples; the rule reproduces 91% of observed commits; the as-of offsets run on B.

## 4. What B leaves at bet time (values only)

Men's frame sides 2024–26, debut seasons out: 14,136 sides, of which 14,018 have a timed reading within 364 days (`availability_diagnostics.json`).

| Target / the side's latest timed reading | Sides | Latest reading usable at es: A | B | L7 | Median age of the latest usable reading, A → B (days) |
|---|---:|---:|---:|---:|---|
| **All** | 14,018 | 88.0% | **50.1%** | 46.2% | 7 → **17** |
| Non-Slam, latest from an earlier event | 6,785 | 100% | 85.5% | 80.6% | 15 → 18 |
| Non-Slam, latest from the same event | 4,475 | 62.4% | **0.5%** | 0.0% | 1 → 15 |
| Slam, earlier event | 1,366 | 100% | 88.4% | 74.2% | 14 → 15 |
| Slam, same event | 1,392 | 99.7% | **0.0%** | 0.1% | 2 → 19 |

* **Under B, 99.5% of sides still have some usable reading,** but no same-event reading is ever usable. *Inferred:* B removes the filter's most heavily weighted rows, the event's earlier rounds; the level survives.
* **Caveat for the modeller:** the plan's A (`lf + 1`) is stricter than the backtest as run, which took own earlier rounds by order. Under `lf + 1`, 37.6% of non-Slam same-event latest readings are not yet released at `es`.

## 5. Routes to timely data

| Route | What it would need | Decision position (quoted) | Estimated lag |
|---|---|---|---|
| **ATP Stats Centre pages, scraped daily** (ManTennisData's own route) | <ul><li>A browser collector of our own: the repository holds data only, and its collector is `msolonskyi/tennisAnalyzer`.</li><li>A daily run.</li></ul> | <ul><li>Not covered. The 7 Oct decision leaves standing that "atptour.com's terms forbid systematic retrieval".</li><li>The bar on decryption "still holds for everything else, including the ATP Stats Centre files"; the pages decrypt in the browser, so the owner must say whether rendering them counts.</li><li>The speed-nudge decision leaves "How and where to collect speeds fast enough for bet time" open.</li></ul> | lf + 1: the next morning |
| **Slam feeds during the event** (W, USO) | <ul><li>A live mode that "re-reads the draws on each run and fetches only finished matches".</li><li>Someone present to stop on a block.</li></ul> | <ul><li>24 Sep: collect W and USO "regardless of their no-scraping terms".</li><li>6 Oct: "Collecting during the event waits for the betting pipeline"; build it "before the first Slam the project bets on".</li><li>RG: "has no official feed held".</li></ul> | Minutes after the match ("each match's box score minutes after it ends"): lf + 1 |
| **AO and RG Infosys files, live** | The same adapter, run daily | Decryption is allowed "for these files only": AO 2025, RG 2025, RG 2026. AO / RG 2027 need the decision extended | Minutes; lf + 1 |
| **AO match centre, plain API, live** | <ul><li>2027 event ids.</li><li>The live mode above.</li></ul> | <ul><li>24 Sep row 4 covers the "Australian Open 2026 match centre".</li><li>Tennis Australia's terms bar collecting "using automated means".</li><li>Live collection waits under 6 Oct.</li></ul> | Minutes; integer floor (+0.5) |
| **Flashscore** | Slams only (off the Slams only the odd final). The desktop feed is signed (401); the mobile site's robots.txt "disallows `/match/`" | No decision covers it; 25 Sep accepted only the handoff's copy | Minutes; integer values |
| **Decrypting the ATP's Infosys files** | The courtside-style key step on the Stats Centre files | **Barred** by 7 Oct, and the 2015–21 request "was not carried out" | Minutes; lf + 1 |

**Suggestion.** At tour level, today's decisions allow only weekly ManTennisData (B); anything faster needs the owner's decision on the ATP's pages. At the Slams, the 6 Oct live mode, once built, gives A.

## Requests

All on 8 Oct 2026 UTC, read-only; the log is `evidence/requests.log`.

| Time (UTC) | Request | Result |
|---|---|---|
| 03:06:13 | `gh api repos/msolonskyi/ManTennisData/commits?path=atp/matches_2026.csv&per_page=100 --paginate` | 37 commits, 1 page |
| 03:06:14 | The same for `matches_2025.csv` | 52 commits, 1 page |
| 03:08:03–03:08:33 | 10 × GET `raw.githubusercontent.com/msolonskyi/ManTennisData/<sha>/atp/matches_2026.csv`, 3 s apart, for the commits of 26 Jul … 27 Sep 2026 | All HTTP 200, 3.48–4.52 MB |

Files are in `data/raw/serve_speed_tabpfn_latency/mantennisdata/`; SHA-256 and git blob receipts are in `evidence/version_receipts.jsonl`. The held head matches its stored blob hash.

## Looks

Values and counts only: each match's first publishing commit against its clock days (2026), and men's 2024–26 frame sides' usable readings and their ages. No speed was related to any outcome, statistic target or price.
