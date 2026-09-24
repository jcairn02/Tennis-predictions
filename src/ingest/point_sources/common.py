"""Shared pieces for the point-by-point web sources (SofaScore, TennisLive.net).

Layout (paths relative to the project root):

    data/raw/point_sources/<source>/          verbatim responses (JSON, or gzipped HTML) plus _receipts.jsonl
    data/dump/points/<source>/                staged Parquet tables, rebuilt from the raw files by --stage
    data/studies/point_shot_sources/scrape/   small tracked summaries of each run

Both sites refuse python-requests' TLS fingerprint (SofaScore answers HTTP 403, TennisLive serves a
Cloudflare challenge), so the client is curl_cffi impersonating a browser: SofaScore accepts the chrome
profile, TennisLive the safari or firefox profiles. Requests are serialised, paced by a minimum interval
with jitter, retried on transient failures, stopped on a block, and capped by an optional budget.
Every response is cached with a receipt, so a rerun fetches only what is missing; an HTTP 404 is
recorded as a terminal answer ("absent") and not asked again unless --refresh is given.

Terms of use: both sites restrict automated extraction (see docs/studies/point_shot_sources/README.md).
The owner decided on 23 Sep 2026 to collect regardless, for non-commercial research. The request rate
here is deliberately low and nothing is fetched twice.
"""
from __future__ import annotations

import gzip
import json
import random
import sys
import time
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

PROJECT_ROOT = C.PROJECT_ROOT
RAW_ROOT = PROJECT_ROOT / "data" / "raw" / "point_sources"
DUMP_ROOT = PROJECT_ROOT / "data" / "dump" / "points"
STUDY_ROOT = PROJECT_ROOT / "data" / "studies" / "point_shot_sources" / "scrape"
REFERENCE_RECORD = PROJECT_ROOT / "data" / "studies" / "career_coverage" / "reference_record.csv"
SOFASCORE_STUDY_SUMMARY = PROJECT_ROOT / "data" / "studies" / "point_shot_sources" / "sofascore_summary.json"

log = C.log
utc_now_iso = C.utc_now_iso
sha256_bytes = C.sha256_bytes
rel = C.rel


class Blocked(RuntimeError):
    """The site refused the client (HTTP 403 or a bot challenge) after retries; stop rather than insist."""


class BudgetExhausted(RuntimeError):
    """The run's --max-requests budget is used up."""


class Client:
    """Serialised, paced, retrying GET client over curl_cffi with a browser fingerprint."""

    def __init__(self, impersonate: str, *, min_interval: float = 1.0, jitter: float = 0.5,
                 max_requests: int | None = None, timeout: int = 30, retries: int = 3,
                 headers: dict | None = None):
        from curl_cffi import requests as cr  # imported here so parsers and tests run without it

        self._session = cr.Session(impersonate=impersonate)
        if headers:
            self._session.headers.update(headers)
        self.impersonate = impersonate
        self.min_interval = min_interval
        self.jitter = jitter
        self.max_requests = max_requests
        self.timeout = timeout
        self.retries = retries
        self.requests = 0
        self.retried = 0
        self.slept = 0.0
        self._last = 0.0

    def _pace(self) -> None:
        wait = self._last + self.min_interval + random.uniform(0, self.jitter) - time.monotonic()
        if wait > 0:
            time.sleep(wait)
            self.slept += wait

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)
        self.slept += seconds

    def get(self, url: str, headers: dict | None = None):
        """GET ``url``; returns the curl_cffi response. Raises Blocked, BudgetExhausted or RuntimeError."""
        last_error = None
        for attempt in range(self.retries + 1):
            if self.max_requests is not None and self.requests >= self.max_requests:
                raise BudgetExhausted(f"request budget of {self.max_requests} used up")
            self._pace()
            self.requests += 1
            self._last = time.monotonic()
            try:
                response = self._session.get(url, timeout=self.timeout, headers=headers)
            except Exception as err:  # curl_cffi raises its own RequestsError family
                last_error = f"{type(err).__name__}: {err}"
                self.retried += 1
                self._sleep(5 * (attempt + 1))
                continue
            status = response.status_code
            challenged = response.headers.get("cf-mitigated") == "challenge"
            if status == 429:
                last_error = "HTTP 429"
                self.retried += 1
                self._sleep(30 * (2 ** attempt))
                continue
            if status >= 500:
                last_error = f"HTTP {status}"
                self.retried += 1
                self._sleep(5 * (attempt + 1))
                continue
            if status == 403 or challenged:
                last_error = "Cloudflare challenge" if challenged else "HTTP 403"
                self.retried += 1
                if attempt < self.retries:
                    self._sleep(60 * (attempt + 1))
                    continue
                raise Blocked(f"{last_error} for {url} after {attempt + 1} attempts")
            return response
        raise RuntimeError(f"{last_error} for {url} after {self.retries + 1} attempts")

    def stats(self) -> dict:
        return {"impersonate": self.impersonate, "requests": self.requests, "retried": self.retried,
                "slept_seconds": round(self.slept, 1), "min_interval": self.min_interval}


def receipts_for(source: str) -> C.Receipts:
    return C.Receipts(source, root=RAW_ROOT)


def raw_path(source: str, *parts: str) -> Path:
    return RAW_ROOT.joinpath(source, *parts)


def dump_path(source: str, *parts: str) -> Path:
    return DUMP_ROOT.joinpath(source, *parts)


def fetch(client: Client, url: str, dest: Path, receipts: C.Receipts, *, name: str, refresh: bool = False,
          validator=None, compress: bool = False, extra: dict | None = None, headers: dict | None = None) -> dict:
    """GET ``url`` into ``dest`` and record a receipt.

    Outcomes, all recorded: status 200 with the body saved (gzipped when ``compress``); status 404 with
    no file (a terminal "absent" answer, reused on later runs); any other status or a validator problem
    as ``error`` (retried on the next run). Blocked and BudgetExhausted propagate so the run stops."""
    previous = receipts.get(name)
    if previous and not refresh:
        if previous.get("status") == 200 and not previous.get("error") and dest.exists():
            return {**previous, "skipped": True}
        if previous.get("status") == 404 and not previous.get("error"):
            return {**previous, "skipped": True}
    receipt = {"name": name, "url": url, "dest": rel(dest), "retrieved_at": utc_now_iso()}
    if extra:
        receipt.update(extra)
    try:
        response = client.get(url, headers=headers)
    except (Blocked, BudgetExhausted):
        raise
    except Exception as err:
        receipt["error"] = f"{type(err).__name__}: {err}"
        return receipts.record(receipt)
    receipt.update(status=response.status_code, content_type=response.headers.get("content-type"),
                   final_url=str(response.url))
    if response.status_code == 404:
        return receipts.record(receipt)
    if response.status_code != 200:
        receipt["error"] = f"HTTP {response.status_code}"
        return receipts.record(receipt)
    body = response.content
    problem = validator(body) if validator else None
    if problem:
        receipt["error"] = problem
        return receipts.record(receipt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(gzip.compress(body) if compress else body)
    receipt.update(bytes=len(body), sha256=sha256_bytes(body), compressed=compress)
    return receipts.record(receipt)


def read_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def read_json(path: Path):
    return json.loads(read_bytes(path).decode("utf-8"))


def json_validator(body: bytes):
    head = body[:64].lstrip()
    return None if head.startswith((b"{", b"[")) else "response is not JSON"


def html_validator(body: bytes):
    head = body[:512].lstrip().lower()
    if not head.startswith((b"<!doctype", b"<html")):
        return "response is not an HTML document"
    if b"<title>just a moment" in body[:4096].lower():
        return "Cloudflare challenge page"
    return None


def write_summary(name: str, data: dict) -> Path:
    STUDY_ROOT.mkdir(parents=True, exist_ok=True)
    path = STUDY_ROOT / name
    path.write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    return path


def study_players() -> dict[str, str]:
    """ATP player code -> SofaScore team id for the ten career-coverage players, from the study summary."""
    summary = json.loads(SOFASCORE_STUDY_SUMMARY.read_text(encoding="utf-8"))
    return {code: str(info["sofascore_id"]) for code, info in summary["players"].items()}


def stage_table(source: str, dest: Path, header: list[str], rows: list[list], *, source_file: str,
                retrieved_at: str | None, extra: dict | None = None) -> dict:
    """Write ``rows`` as a string Parquet table with the dump's provenance columns and a sidecar."""
    prov = C.Provenance(source, source_file, None, retrieved_at, extra)
    stats = C.stage_rows(header, ((i + 1, r) for i, r in enumerate(rows)), dest, prov)
    C.write_meta(dest, {"branch": "points", "source": source, "dest": rel(dest), "rows": stats["rows"],
                        "columns": stats["columns"], "bytes": stats["bytes"], "source_path": source_file,
                        "retrieved_at": retrieved_at, **(extra or {})})
    return stats


def s(value) -> str | None:
    """Verbatim string form for staging: None stays None, bools become TRUE/FALSE, the rest str()."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
