# Lane I: openly licensed copies of the Slam feed data (24 Sep 2026)

This is a follow-up lane for [access routes](../../../../docs/research/granular-data-leads/access-routes.md).

**Question.** Is any of the data in rows 2–5 of the [granular data leads](../../../../docs/research/granular-data-leads/README.md) available as an openly licensed download? That data is:
- Wimbledon 2019 and 2021–2026;
- US Open 2022–2026;
- Australian Open 2026;
- IBM's likelihood-to-win and US Open 2026 limb tracking.

**Method.** Read-only. Metadata and file listings were read, plus at most one small sample file per dataset. A dataset that is itself a scrape of a Slam site is listed but flagged.

**Tools.** Parsing used the base `C:\Users\zerom\miniforge3\python`. CSV comparisons used `./python.sh`.

This is the agent's report as returned, lightly edited. Scratch files stayed in the session scratchpad.

**Labels:** [observed], [provider claim], [third-party report], [search excerpt], [inference], [not stated].

## Bottom line

No openly licensed download holds any of the 2019–2026 feed data. Specifically, nothing open has:
- clock times, Sentence text, qualifying, or 2025–26 files;
- IBM likelihood-to-win or limb tracking;
- Australian Open 2026 match-centre data.

Every open Slam point dataset for 2019–2024 that was found is Sackmann's archive, or a copy or subset of it.

The only official open release with clock times and forced errors is IBM's 2016 file for Wimbledon 2014–15, licensed Apache-2.0.

## 1. Sackmann's `tennis_slam_pointbypoint`

**The repo is gone.**
- The GitHub API returns 404 for `tennis_slam_pointbypoint`, `tennis_atp`, `tennis_wta` and `tennis_pointbypoint`. The account now has one public repo, `tennis_MatchChartingProject` [observed; rechecked by the main session at 17:57 UTC].
- The Wayback Machine shows the Slam repo live on 31 Oct 2025, at commit `6febb77` with 59 commits. Software Heritage recorded it as not found on 6 Aug 2026 [observed].
- `tennis_atp` disappeared between 8 May and 16 Jun 2026 (Software Heritage) [observed].
- No reason for the removals is given [not stated].

**Last commit.** `6febb77`, 11 Oct 2024: "add 2024 wimb + us open / no doubles (yet) for 2024 W" [observed, Software Heritage].

**Licence.** CC BY-NC-SA 4.0, stated in the README only. There is no LICENSE file [observed].

**It is itself a scrape.** The README says: "It was scraped from the four Grand Slam websites shortly after each event" [provider claim].

**What the README says about updates** [observed]:
- "I'll try to keep this updated after each tournament, but I can't make any promises as to punctuality."
- "Since 2023, I haven't attempted to extract this data from the AO or FO."
- It says AO and French Open 2018–22 were converted, yet no 2022 file exists for either.

**Final file inventory: 166 CSVs** [observed].

| Slam | Singles | Doubles | Mixed |
|---|---|---|---|
| Australian Open | 2011–21 | 2018–21 | 2018–21 |
| Roland-Garros | 2011–21 | 2018–21 | 2018, 2019, 2021 |
| Wimbledon | 2011–19, 2021–24 | 2019, 2021–23 | 2019, 2021–23 |
| US Open | 2011–24 | 2019–24 | 2019, 2021–24 |

There is **no 2025 or 2026 file, and no qualifying file,** for any Slam.

**Columns of the newest points files** (Wimbledon and US Open 2024, 65 columns) [observed]:
- **Time:** there is no clock time. The only time is `ElapsedTime`, in h:mm:ss from the match start.
- **Text:** there is no Sentence-like text. `History` holds numeric codes such as `11030`.
- **Rally count:** `RallyCount` is non-zero on 49% of Wimbledon rows and 91% of US Open rows. `Rally` is empty.
- **Forced errors:** `P1ForcedError` and `P2ForcedError` are blank on every row.

**The project's mirror copy matches the final commit.** The three 2024 points files have the same git hashes as the Software Heritage archive [observed].

**Forks and mirrors** [observed]:
- The surviving fork network, now rooted at `halepmania/tennis_slam_pointbypoint`, has 89 forks. None was pushed after 11 Oct 2024, and none has a licence file.
- `Aneeshers/tennis-sackmann-archive`, on GitHub and Hugging Face, is stated as CC BY-NC-SA 4.0. It says it was taken "from upstream commit 6febb77". It and its 9 forks cover 2011–2024 only.
- A GitHub code search for 2025–26 Slam file names found nothing.

## 2. Datasets

| Dataset | URL | Licence as stated | Provenance | Coverage | Fields | New vs held? | Scrape of a Slam site? |
|---|---|---|---|---|---|---|---|
| COMAP MCM 2024 Problem C | contest.comap.com/undergraduate/contests/mcm/contests/2024/problems/Wimbledon_featured_matches.csv | None on the file, the data dictionary or the problem. See **COMAP licence** below | Not stated. All 7,284 rows match Sackmann's 2023 Wimbledon file on 18 fields; `serve_no` differs only on 254 double faults, where 0 became 2 [observed] | Wimbledon 2023 men's singles, round 3 to final, 31 matches | 46 columns; elapsed time only; no clock time, forced errors or text | No | Yes, indirectly: a Sackmann subset [inference] |
| Re-uploads of the MCM file | Kaggle `dengfengqi/2023-wimbledon-point-by-point-data` and `lifengju/2024-mcm-c`; Hugging Face `saxasxa`, `sarahzhoo620`, `ttydsc30`, `zhennengchi`, `zyyyhi`; Figshare 25511917 | Apache 2.0, CC BY 4.0 or none, as each uploader labels it | The COMAP file; the Figshare copy has the same MD5. Figshare also adds 13 Wimbledon and US Open 2023 matches in MCM columns, with Sackmann match ids [observed] | Same | Same | No | Yes, indirectly |
| Aneeshers mirror | github.com/Aneeshers/tennis-sackmann-archive | CC BY-NC-SA 4.0 | Sackmann commit `6febb77` | As Sackmann | As Sackmann | No: the held copy | Yes |
| Wimbledon 2024 point and match statistics | kaggle.com/datasets/rewantbhriguvanshi/wimbledon-2024-point-and-match-level-statistics | Apache 2.0 | "Base data originally sourced from" Sackmann [provider claim] | Wimbledon 2024 singles, 48,000+ points | Sackmann's, plus match totals | No | Yes |
| Point by point Dataset | kaggle.com/datasets/alessiore02/point-by-point-dataset | "Unknown" | Sackmann's file names | 2014–2024 | Sackmann's | No | Yes |
| Grand Slam Matches 2011–2023 | data.mendeley.com/datasets/hjwtvnpd7t | CC BY 4.0 | "Integration of Jeff Sackmann's point-by-point Grand Slam data", plus tennis-data.co.uk odds [provider claim] | 2011–2023 | Not opened (41 MB zip) | No, at point level | Yes |
| Multi-Source Point-by-Point Dataset | zenodo.org/records/16888520 | CC BY 4.0 | Claims ATP/WTA, scanned archives and Hawk-Eye. The file is one sheet, `2023-wimbledon-points`, with 8 Sackmann columns and no match ids [observed] | Wimbledon 2023, 20,562 rows | 8 columns | No | Yes, indirectly [inference] |
| Harris OSF project | osf.io/b4vpd | None set | Same SHA-256 as Sackmann's files [observed] | Wimbledon 2018–19 | Sackmann's | No | Yes |
| **IBM Datapalooza** | github.com/ibm-datapalooza/wimbledon-datasets | **Apache-2.0** (LICENSE file) | Posted in June 2016 by the "IBM Datapalooza" GitHub organisation for a London event. AELTC permission [not stated] | Wimbledon 2014–15 men's and ladies' singles, rounds 1–3. Also set statistics for all four Slams, 2005–2015 | Per point: timestamps for first serve, second serve and end of point; stroke (forehand, backhand, ace, double fault); shot detail; winner, unforced or forced error; rally; speed; serve direction | **Yes:** adds width, but only for 2014–15 | No: a first-party IBM release [inference] |

**COMAP licence.** The problem PDF says "©2024 by COMAP, Inc.". COMAP's Permissions/Use page allows non-profit educational copies, but no other use "without the expressed written permission of COMAP". Whether that covers the CSV is unclear.

The main session confirmed the Datapalooza repository at 17:57 UTC:
- licence `Apache-2.0`, last push 2016-06-29;
- `w14 PbP MS LS R1-R3.csv` (6.8 MB), `w15 PbP MS LS R1-R3.csv` (6.6 MB) and `Slams_Sets_201605310936.csv` (15.5 MB), plus two Wimbledon weather files.

**Set aside** as match-level or not Slam feed data:
- Kaggle `mahmoudehab6677/australian-open-2026-dataset` (CC BY 4.0): match results scraped from the TNNS Live API.
- Kaggle `mariaaqdas` US Open 2026: match results from Sportradar.
- SCORE Network, and Dataverse RQ6JVL: Match Charting Project derivatives.
- Zenodo 22777381: a US Open 2026 prediction bot, restricted access.

## 3. Official open releases

- **IBM, 2016.** The Datapalooza repository above. It is the only official-looking release under an open licence that was found, and it predates 2019.
- **Tennis Australia, 2018 ("From AO to AI").** "more than 10,000 points of Grand Slam tracking data to the public for research" [provider claim, ausopen.com, 2 Jan 2018]. No licence is stated, and the points carry no match ids. It is row 13 of the leads.
- **Tennis Australia, 2023 ("AO Data Slam").** 120,000 tracking points released to CrowdANALYTIX hackathon participants [provider claim, ausopen.com, 29 Jan 2023]. No licence is stated, and no public copy was found.
- **USTA, 2026 (Connect Innovation Challenge).** "Selected participants will gain exclusive access to premier USTA and US Open datasets" [provider claim]. This is not open.
- **AELTC.** Nothing found.
- **Supporting evidence.** The authors of a 2026 Zenodo package (record 21717759) did not share the Slam statistics they used, because "no express licence permitting their public redistribution was identified" [third-party report].

## 4. Not determined

- **Sackmann's removals.** When and why his repositories were removed, and whether any commit came after 31 Oct 2025. The mirror's use of `6febb77` suggests none did [inference].
- **Rights behind the releases.**
  - Whether COMAP had rights to the 2023 data, and whether its Permissions/Use terms apply to the CSV.
  - Whether IBM had AELTC's permission to license the 2014–15 data under Apache-2.0.
- **Tennis Australia releases.** The terms of both. The CrowdANALYTIX and tennis.com.au pages returned 403 or were empty.
- **The Mendeley zip.** Its contents; it was not downloaded.
- **Search blind spots.** A large unlabelled dump could be missed:
  - Kaggle and Hugging Face searches match only titles and ids.
  - GitHub code search skips forks and files over 384 KB.
  - Dataverse and Mendeley searches cover metadata only.
