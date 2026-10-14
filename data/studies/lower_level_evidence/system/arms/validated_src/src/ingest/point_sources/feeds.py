"""Shared pieces for the official point feeds (study official_point_feeds): the Australian Open match centre
first, then the Wimbledon, US Open and WTA feeds.

Collected under the owner's decision of 24 Sep 2026 (docs/decisions/2026-09-24-official-point-feeds.md): the
feeds are read regardless of the sites' no-scraping terms, for non-commercial research, within its limits.
Those are about 2 s between requests plus jitter, a --max-requests budget, everything cached and nothing
fetched twice, a stop and report on any block with no escalation, and no logins, tokens, CAPTCHA solving,
decryption or working around a redirect or a 403.

Layout, as for SofaScore and TennisLive (common.py):

    data/raw/point_sources/<source>/          verbatim responses plus _receipts.jsonl
    data/dump/points/<source>/                staged string Parquet, rebuilt from the raw files by --stage-only
    data/studies/official_point_feeds/        run summaries (<source>_summary.json, runs.jsonl) and checks

FeedClient is common.Client with a stricter block policy:
    * a source's ``not_found`` function is asked first, so that a site's own way of saying "no such
      document" (API Gateway's 403 "Missing Authentication Token", say) is returned as an answer;
    * any other HTTP 403, an HTTP 429, a bot challenge, a redirect (never followed) or a connection reset
      stops the run at once, with no retry;
    * HTTP 5xx and other transport errors are retried up to three times with a growing pause, then left to
      common.fetch to record as an error, which the next run retries.
FailureStreak stops a run after a few fetches in a row that brought no document, so a site that has changed
or gone is not pressed further.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P

STUDY_ROOT = P.PROJECT_ROOT / "data" / "studies" / "official_point_feeds"
DECISION = "docs/decisions/2026-09-24-official-point-feeds.md"
# Markers of a bot-manager or challenge page served in place of data (the feeds themselves never send HTML).
CHALLENGE_MARKERS = (b"captcha", b"cf-chl", b"challenge-platform", b"_incapsula_", b"pardon our interruption",
                     b"access denied", b"are you a robot", b"request unsuccessful")


def block_reason(response) -> str | None:
    """Why a response counts as a block under the decision's rules, or None."""
    status = response.status_code
    headers = response.headers
    if 300 <= status < 400:
        return f"HTTP {status} redirect to {headers.get('location')!r} (not followed)"
    if status == 429:
        return "HTTP 429 (rate limited)"
    if headers.get("cf-mitigated") == "challenge":
        return f"HTTP {status} Cloudflare challenge"
    if headers.get("x-amzn-waf-action"):
        return f"HTTP {status} AWS WAF action {headers.get('x-amzn-waf-action')!r}"
    if status == 403:
        return f"HTTP 403 ({response.content[:120].decode('utf-8', errors='replace').strip()!r})"
    if "html" in (headers.get("content-type") or "").lower():
        head = response.content[:4096].lower()
        marker = next((m for m in CHALLENGE_MARKERS if m in head), None)
        if marker:
            return f"HTTP {status} challenge page ({marker.decode()!r} in an HTML answer)"
    return None


def is_reset(error: Exception) -> bool:
    return "reset" in str(error).lower()


class FeedClient(P.Client):
    """common.Client with the official feeds' block policy (module docstring)."""

    def __init__(self, impersonate: str = "chrome", *, not_found=None, min_interval: float = 2.0,
                 jitter: float = 1.0, max_requests: int | None = None, timeout: int = 30, retries: int = 3,
                 headers: dict | None = None, session=None):
        super().__init__(impersonate, min_interval=min_interval, jitter=jitter, max_requests=max_requests,
                         timeout=timeout, retries=retries, headers=headers, session=session)
        self.not_found = not_found
        self.not_found_answers = 0

    def get(self, url: str, headers: dict | None = None):
        """GET ``url`` without following redirects; raises Blocked, BudgetExhausted or RuntimeError."""
        last_error = None
        for attempt in range(self.retries + 1):
            if self.max_requests is not None and self.requests >= self.max_requests:
                raise P.BudgetExhausted(f"request budget of {self.max_requests} used up")
            self._pace()
            self.requests += 1
            self._last = time.monotonic()
            try:
                response = self._session.get(url, timeout=self.timeout, allow_redirects=False,
                                             headers={**self._headers, **(headers or {})})
            except Exception as err:  # curl_cffi raises its own RequestsError family
                last_error = f"{type(err).__name__}: {err}"
                if is_reset(err):
                    raise P.Blocked(f"connection reset for {url}: {last_error}")
                self.retried += 1
                self._sleep(5 * (attempt + 1))
                continue
            if self.not_found and self.not_found(response):
                self.not_found_answers += 1
                return response
            block = block_reason(response)
            if block:
                raise P.Blocked(f"{block} for {url}")
            if response.status_code >= 500:
                last_error = f"HTTP {response.status_code}"
                self.retried += 1
                self._sleep(5 * (attempt + 1))
                continue
            return response
        raise RuntimeError(f"{last_error} for {url} after {self.retries + 1} attempts")

    def stats(self) -> dict:
        return {**super().stats(), "jitter": self.jitter, "not_found_answers": self.not_found_answers}


class Stopped(RuntimeError):
    """The run stopped itself: the site kept answering without documents (FailureStreak)."""


class FailureStreak:
    """Stops a run once ``limit`` fetches in a row brought no document (an error, a 404 or another absence).

    Cached answers are ignored: only what the site says now counts."""

    def __init__(self, limit: int = 5):
        self.limit = limit
        self.count = 0

    def note(self, receipt: dict) -> None:
        if receipt.get("skipped"):
            return
        failed = receipt.get("error") or receipt.get("absent") or receipt.get("status") != 200
        self.count = self.count + 1 if failed else 0
        if self.limit and self.count >= self.limit:
            last = receipt.get("error") or receipt.get("absent") or f"HTTP {receipt.get('status')}"
            raise Stopped(f"{self.count} fetches in a row brought no document (last: {receipt.get('name')}: {last})")


def write_summary(name: str, data: dict) -> Path:
    return P.write_summary(name, data, root=STUDY_ROOT)
