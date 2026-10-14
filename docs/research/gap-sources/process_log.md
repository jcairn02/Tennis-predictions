# Gap sources research: process log

Opened on 14 Oct 2026 for the note [itf_2025_points.md](itf_2025_points.md). The earlier notes of this folder (the gap-sources research of 29 Sep 2026) kept no log, and are not retrofitted.

---

## ITF points for January 2025 to February 2026 (itf_2025_points.md)

13-14 Oct 2026 · Lead: Claude Opus 5.5 (`claude-opus-5-5`) in Claude Code, session `8b00b734-ccf1-42cc-bd90-a3bb292e7ad2`; the note was written by a research subagent of that session · For a future reviewer

**Reconstructed, not contemporaneous:** this log was opened after the note was written (the process-log rule reached the session on 14 Oct). It records what the lead knows of the subagent's work: its brief, its report and the lead's own checks.

### 1. The request

* **The owner's words, verbatim** (13 Oct 2026, about 22:20 UTC, after choosing to defer SofaScore's flagged events): "In parallel, see if you can find this missing data somewhere else (or still at sofa score)".
* **How it was read:** "this missing data" is the ITF point-by-point of January 2025 to February 2026, which SofaScore lacks (work package P7). The lead took "still at SofaScore" and the ITF's own route (the plan's P12) itself. A subagent took the files on disk and the web, kept off the hosts other collectors used or the lead reserved.

### 4. Chronology (UTC)

| When | Step | Output |
|---|---|---|
| 13 Oct ~22:35 | Subagent launched; brief verbatim in [the study's log companion](../../studies/gap_downloads/process_log_brief_itf_2025_points.md) | – |
| 13 Oct 22:39-22:52 | The subagent's requests: Flashscore 9, Tennis Explorer 2, AiScore 2 (blocked), vendor and press pages, and one to itftennis.com against its brief (a news article; nothing returned) | the note's "Requests made" |
| 13 Oct ~23:05 | The note written; the lead read it and checked the 8 feed samples by eye | the feed format confirmed |
| 13 Oct ~23:05 | The lead asked the ITF API's `matchesByCourt` (2 requests, receipts) | 404 both; the note amended |
| 14 Oct ~23:10 | The lead copied the subagent's 8 feeds and match page from the session's scratch folder to `data/raw/gap_sources/flashscore_itf_2025/`, and amended the note (the SofaScore momentum series is empty; the court route is closed; where the answers are kept) | – |
| 14 Oct 01:07-01:25 | P13's own extract and trial re-checked the note's numbers | the extract gives the census's 42,791 and 29,614 exactly; the duration rule held on 52 of 52 without a duration |

*Correction, 14 Oct 14:20 UTC:* the row "14 Oct ~23:10" should read "13 Oct ~23:10": the copy and the amendments came before the owner approved P13 (14 Oct ~00:50).

### 7. Claims: re-checked or taken as reported

* **Re-checked by the lead:** the feed format and its codes; the handoff copy's window counts; the duration rule (the P13 trial: 131/6/0/52); the closed ITF routes (the lead's own probes).
* **Taken as reported:** the TennisLive measure (the careers' 2025 matches), the Live Tennis API index overlap, and every vendor claim.

### 8. Weak points

* The subagent's own exploration (what it tried and dropped) is not recorded beyond its note and report.
* Its scratch scripts stay in the session's scratch folder (`itf25/`), outside the repository.
