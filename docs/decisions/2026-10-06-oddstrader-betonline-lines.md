# Collect BetOnline's tennis opening and last lines from OddsTrader without written permission

**Decided by the owner on 6 October 2026.** Recorded the same day, before the download.

## Decision

Pull, from the odds service behind oddstrader.com, every ATP and WTA singles match listed from 1 January 2024 to 6 October 2026:

| What | Books | Markets |
|---|---|---|
| Opening line and last line, each with its timestamp | BetOnline (OddsTrader book 8) and its sister brand SportsBetting.ag (book 131) | Match winner (market 126) and total games (market 396) |

Line history only where a closing line needs it: matches whose last line is stamped after the start. That set is measured first and reported before it is pulled.

**Basis.** The [BetOnline lines research](../research/betonline-lines/README.md) found OddsTrader the only free source of these lines for 2024–2026. Its terms allow "lawful personal and informational purposes" and say "Automated access may require written permission". Offered the choice of emailing OddsTrader first, the owner chose to pull now and accept that risk, for non-commercial research. The light pull was chosen over full history: about 300 requests instead of about 45,000.

## Limits

* **Pace.** About 2 seconds between requests, plus jitter, with a `--max-requests` budget. Every response is kept with a receipt, and nothing is fetched twice.
* **Blocks.** Stop and report on any block: HTTP 403 or 429, a bot challenge, a redirect, or a connection reset. Don't escalate.
* **Not allowed:** logging in or using the owner's OddsTrader account or any token; solving a CAPTCHA; working around a block.
* **No republishing.** This repository is public. Raw responses and staged tables stay in the gitignored `data/raw/` and `data/dump/`. Tracked evidence holds counts, not prices.
* **Working rules.** Run through `./python.sh` only. No git commits. Don't delete files.

## Where the collection lives

* adapter `src/ingest/oddstrader.py`;
* verbatim responses in `data/raw/oddstrader/`;
* staged tables in `data/dump/odds/oddstrader/`;
* run summaries and coverage in `data/studies/betonline_lines/`;
* the write-up in [docs/research/betonline-lines/README.md](../research/betonline-lines/README.md).

## Not changed by this decision

* **The terms.** OddsTrader's terms are unchanged; they are quoted in the research note.
* **The project's status.** No dataset, model or venue is selected.
