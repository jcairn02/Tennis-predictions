"""Paced, receipted GET client for lane C of the gap-sources study (ITF listings), 29 Sep 2026.

Every response is saved verbatim under data/raw/gap_sources/itf/ (gitignored), with one line per request
in that folder's _receipts.jsonl (URL, time, status, content type, size, SHA-256, anti-bot headers seen).
The official ITF site (itftennis.com) is stored at the folder's top level (robots.txt, pages/, api/,
assets/); every other host under other/<host>/. A cached body is reused, so a rerun asks a site only for
what is missing.

Rules of the study: one request at a time per site, at least 2 s apart plus jitter (kept across runs in
_session_state.json), a hard budget per run, and a full stop on the first sign of a block (HTTP 403 or
429, an Imperva/Incapsula or Cloudflare challenge page, a CAPTCHA, or an empty body). A block is written
to _blocked.json and every later request to that host is refused by this client. Nothing here solves or
works around a challenge. The client is curl_cffi with a Chrome TLS fingerprint and ordinary browser
headers, as in src/ingest/point_sources/common.py.

What happened on itftennis.com (29 Sep 2026): robots.txt, one tournament page and GetEventFilters
answered 200 through Imperva; the first GetDrawsheet request answered HTTP 403 with an Incapsula incident
page, so the client stopped asking that host.

Usage (exploration): ./python.sh src/eda/gap_sources/itf_http.py <name> <url> [json|html|text|binary]
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "gap_sources" / "itf"
RECEIPTS = RAW / "_receipts.jsonl"
STATE = RAW / "_session_state.json"
BLOCKED = RAW / "_blocked.json"
ITF_HOST = "www.itftennis.com"

BROWSER_HEADERS = {"Accept-Language": "en-GB,en;q=0.9"}
JSON_HEADERS = {"Accept": "application/json, text/plain, */*"}

CHALLENGE_MARKERS = (b"_incapsula_resource", b"incapsula incident", b"request unsuccessful",
                     b"<title>just a moment", b"cf-chl", b"captcha", b"geo.captcha-delivery")


class Blocked(RuntimeError):
    """The site refused or challenged the client; requests to that host stop here."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json_file(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def load_receipts() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    if RECEIPTS.exists():
        for line in RECEIPTS.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                latest[r["name"]] = r
    return latest


def record(receipt: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    with RECEIPTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")


def challenge_in(body: bytes) -> str | None:
    head = body[:20000].lower()
    for marker in CHALLENGE_MARKERS:
        if marker in head:
            return marker.decode()
    return None


def dest_for(host: str, name: str) -> Path:
    return RAW / name if host == ITF_HOST else RAW / "other" / host / name


class Fetcher:
    def __init__(self, *, min_interval: float = 2.5, jitter: float = 1.5, budget: int = 60,
                 impersonate: str = "chrome"):
        from curl_cffi import requests as cr

        self.session = cr.Session(impersonate=impersonate)
        self.session.headers.update(BROWSER_HEADERS)
        self.min_interval, self.jitter, self.budget = min_interval, jitter, budget
        self.impersonate = impersonate
        self.requests = 0
        self.receipts = load_receipts()
        # Anonymous session cookies are kept between runs, as a browser would keep them, with the last
        # request time per host, so separate runs stay paced.
        state = read_json_file(STATE, {})
        if "cookies" in state and "hosts" not in state:  # first layout: itftennis.com only
            state = {"hosts": {ITF_HOST: state}}
        self._hosts: dict[str, dict] = state.get("hosts", {})
        for host, info in self._hosts.items():
            for k, v in (info.get("cookies") or {}).items():
                self.session.cookies.set(k, v, domain="." + host.removeprefix("www."))
        self.blocked: dict[str, dict] = read_json_file(BLOCKED, {})

    def _save_state(self, host: str, last: float) -> None:
        suffix = host.removeprefix("www.")
        cookies = {c.name: c.value for c in self.session.cookies.jar if (c.domain or "").lstrip(".").endswith(suffix)}
        self._hosts[host] = {"cookies": cookies, "last_request_epoch": last}
        STATE.write_text(json.dumps({"hosts": self._hosts}, indent=1), encoding="utf-8")

    def _pace(self, host: str) -> None:
        last = float(self._hosts.get(host, {}).get("last_request_epoch") or 0.0)
        wait = last + self.min_interval + random.uniform(0, self.jitter) - time.time()
        if wait > 0:
            time.sleep(wait)

    def get(self, name: str, url: str, *, expect: str = "json", refresh: bool = False,
            headers: dict | None = None) -> tuple[dict, bytes | None]:
        """Return (receipt, body). ``name`` is the file name under the host's folder. Raises Blocked."""
        host = urlsplit(url).hostname or ""
        dest = dest_for(host, name)
        prev = self.receipts.get(name)
        if prev and not refresh and prev.get("status") in (200, 404) and not prev.get("problem"):
            body = dest.read_bytes() if dest.exists() else None
            if prev.get("status") == 404 or body is not None:
                return {**prev, "cached": True}, body
        if host in self.blocked:
            raise Blocked(f"{host} blocked this client earlier ({self.blocked[host]['problem']}); not asking again")
        if self.requests >= self.budget:
            raise RuntimeError(f"request budget of {self.budget} used up before {url}")
        self._pace(host)
        self.requests += 1
        started = time.time()
        hdrs = dict(JSON_HEADERS if expect == "json" else {})
        hdrs.update(headers or {})
        receipt = {"name": name, "url": url, "host": host, "retrieved_at": utc_now(), "impersonate": self.impersonate}
        try:
            resp = self.session.get(url, headers=hdrs, timeout=60, allow_redirects=True)
        except Exception as err:  # network error: recorded, not retried
            receipt["problem"] = f"{type(err).__name__}: {err}"
            record(receipt)
            self.receipts[name] = receipt
            self._save_state(host, started)
            return receipt, None
        body = resp.content or b""
        h = {k.lower(): v for k, v in resp.headers.items()}
        cookies = sorted({c.split("=", 1)[0].strip() for c in resp.headers.get_list("set-cookie")}) \
            if hasattr(resp.headers, "get_list") else []
        receipt.update(status=resp.status_code, final_url=str(resp.url), content_type=h.get("content-type"),
                       bytes=len(body), sha256=hashlib.sha256(body).hexdigest(),
                       server=h.get("server"), x_cdn=h.get("x-cdn"), x_iinfo=h.get("x-iinfo"),
                       cf_ray=h.get("cf-ray"), cf_mitigated=h.get("cf-mitigated"), set_cookie_names=cookies)
        marker = challenge_in(body) if expect != "binary" else None
        if marker == "captcha" and resp.status_code == 200 and len(body) > 50000:
            marker = None  # a full page that merely mentions a captcha (a form script), not a challenge page
        problem = None
        if resp.status_code in (403, 429):
            problem = f"HTTP {resp.status_code}"
        elif h.get("cf-mitigated") == "challenge":
            problem = "Cloudflare challenge"
        elif marker:
            problem = f"challenge marker {marker!r}"
        elif resp.status_code == 200 and not body.strip():
            problem = "empty body"
        elif expect == "json" and resp.status_code == 200 and body.strip()[:1] not in (b"{", b"["):
            problem = "non-JSON body where JSON was expected"
        if problem:
            receipt["problem"] = problem
        dest.parent.mkdir(parents=True, exist_ok=True)
        if body:
            dest.write_bytes(body)
        record(receipt)
        self.receipts[name] = receipt
        self._save_state(host, started)
        if problem and problem != "non-JSON body where JSON was expected":
            self.blocked[host] = {"problem": problem, "url": url, "at": receipt["retrieved_at"], "name": name}
            BLOCKED.write_text(json.dumps(self.blocked, indent=1), encoding="utf-8")
            raise Blocked(f"{problem} at {url} (status {resp.status_code}, {len(body)} bytes)")
        return receipt, body


def main(argv: list[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    name, url = argv[1], argv[2]
    expect = argv[3] if len(argv) > 3 and not argv[3].startswith("--") else ("json" if "/api/" in url else "html")
    f = Fetcher(budget=1)
    try:
        receipt, body = f.get(name, url, expect=expect, refresh="--refresh" in argv)
    except Blocked as err:
        print("BLOCKED:", err)
        print(json.dumps(f.receipts.get(name), indent=1))
        return 2
    print(json.dumps(receipt, indent=1))
    if body and expect != "binary":
        print(body[:1500].decode("utf-8", "replace"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
