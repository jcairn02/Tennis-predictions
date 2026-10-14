"""A request transport that runs inside a real browser tab, for sites that bind their access token to the
browser's TLS fingerprint (SofaScore, observed 24 Sep 2026: the token's ``f`` claim is the JA4 fingerprint
of the Chrome that passed the check, and no impersonation profile reproduces it).

Start Chrome yourself, with a blank profile and a debugging port, on the site's page, e.g. in PowerShell:

    & "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222 `
        --user-data-dir="$env:LOCALAPPDATA\\sofascore-cdp" --no-first-run --no-default-browser-check `
        https://www.sofascore.com/tennis

and pass the check a visitor is shown, if one appears. The adapter then connects with Playwright over the
Chrome DevTools Protocol and evaluates ``window.fetch`` in that tab, so each request carries exactly what the
browser sends (cookies, handshake, headers), at the adapter's paced rate. Nothing here solves a check or
hides automation: the browser is launched normally and only fetch() calls are made in it.

The site's token lasts an hour and is renewed only when a page loads (observed 24 Sep 2026: after expiry the
tab's own background calls just fail). So when a call is answered with a challenge, the transport reloads
the tab, which makes the site run its check again exactly as for a returning visitor, waits for a fresh
token to appear in localStorage (``token_key``), and repeats the call. If the check wants a click, the
person at the screen has to give it; the transport says so in the log and keeps waiting.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.point_sources import common as P

# fetch() ignores or forbids these; the browser supplies its own
FORBIDDEN_HEADERS = {"origin", "referer", "user-agent", "accept-encoding", "host", "cookie", "connection",
                     "content-length", "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site"}
FETCH_JS = """async ({url, headers}) => {
  const r = await fetch(url, {headers, credentials: "include", cache: "no-store"});
  const h = {}; r.headers.forEach((v, k) => { h[k] = v; });
  return {status: r.status, headers: h, body: await r.text(), url: r.url};
}"""
RENEW_WAIT = 3600  # seconds to wait for a fresh token after reloading the tab (the check may want a click)
RENEW_RELOAD_EVERY = 300  # after this long without a token, clear the site's data and reload again (see renew)
# Cloudflare renders its widget inside a closed shadow root, so look for the site's own full-window backdrop too
CHECK_SHOWN_JS = """() => {
  if (document.querySelector('iframe[src*="challenges.cloudflare"]')) return true;
  const w = window.innerWidth, h = window.innerHeight;
  return [...document.querySelectorAll('div')].some(d => {
    if (d.hidden) return false;
    const s = getComputedStyle(d);
    if (s.position !== 'fixed' || s.visibility === 'hidden' || s.display === 'none') return false;
    const r = d.getBoundingClientRect();
    return r.width >= w * 0.9 && r.height >= h * 0.9 && d.querySelector('div') !== null;
  });
}"""


def is_challenge(status: int, body: str) -> bool:
    """SofaScore's refusal that means "no valid token": HTTP 403 with reason "challenge"."""
    if status != 403:
        return False
    try:
        return json.loads(body[:4096])["error"]["reason"] == "challenge"
    except Exception:
        return False


def token_expired(token: str | None) -> bool:
    if not token:
        return True
    try:
        exp = P.jwt_claims(token).get("exp")
    except ValueError:
        return False
    return isinstance(exp, (int, float)) and time.time() > exp


def allowed_headers(headers: dict | None) -> dict:
    """The headers fetch() may set; the browser supplies the rest itself."""
    return {k: v for k, v in (headers or {}).items() if k.lower() not in FORBIDDEN_HEADERS}


class BrowserResponse:
    """The subset of a curl_cffi response that common.Client and common.fetch read."""

    def __init__(self, status: int, headers: dict, body: str, url: str):
        self.status_code = status
        self.headers = {k.lower(): v for k, v in headers.items()}
        self.content = body.encode("utf-8")
        self.url = url


class PageSession:
    """Runs GET requests as fetch() calls inside one browser tab reached over CDP."""

    def __init__(self, cdp_url: str, origin: str, url_map: dict[str, str] | None = None,
                 token_key: str | None = None):
        from playwright.sync_api import sync_playwright  # imported here so parsers and tests run without it

        self.cdp_url = cdp_url
        self.origin = origin.rstrip("/")
        self.url_map = url_map or {}
        self.token_key = token_key
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.connect_over_cdp(cdp_url)
        self.version = self._browser.version
        self.page = self._find_page()
        self.reloads = 0
        self.renewals = 0
        self.renewals_failed = 0
        self.resets = 0

    def _token(self) -> str | None:
        if not self.token_key:
            return None
        try:
            return self.page.evaluate(f"localStorage.getItem({json.dumps(self.token_key)})")
        except Exception:  # mid-reload
            return None

    def _check_shown(self) -> bool:
        try:
            return bool(self.page.evaluate(CHECK_SHOWN_JS))
        except Exception:
            return False

    def _reload(self, timeout: int) -> None:
        self.reloads += 1
        try:
            self.page.reload(wait_until="domcontentloaded", timeout=timeout * 1000)
        except Exception:
            self.page = self._find_page()

    def _reset_site_data(self) -> None:
        """Clear the tab's cookies and the site's storage: the state a visitor with a fresh profile has.

        Observed 24 Sep 2026: a fresh profile passed the site's check silently at once, while a tab that had
        been polling for hours was asked for a click, and after a while was shown no check at all."""
        try:
            cdp = self.page.context.new_cdp_session(self.page)
            cdp.send("Network.clearBrowserCookies")
            cdp.send("Storage.clearDataForOrigin", {"origin": self.origin, "storageTypes": "all"})
            cdp.detach()
            self.resets += 1
            P.log("[browser] cleared the site's cookies and storage before reloading (a fresh visitor's state)")
        except Exception as err:
            P.log(f"[browser] could not clear the site's data: {type(err).__name__}: {err}")

    def renew(self, timeout: int = 30) -> bool:
        """Reload the tab so the site runs its check and stores a fresh token; True when a new one appeared.

        Waits up to RENEW_WAIT seconds. The first reload is the site's ordinary renewal; if no token has
        appeared after RENEW_RELOAD_EVERY seconds, the site's data is cleared and the tab reloaded again,
        every RENEW_RELOAD_EVERY seconds. Once a minute the log says whether the check is visible, so that
        whoever watches it can go and click."""
        before = self._token()
        started = time.monotonic()
        last_reload = None
        last_word = 0.0
        P.log("[browser] challenge answered; reloading the tab for a fresh token")
        while time.monotonic() - started < RENEW_WAIT:
            if last_reload is None or time.monotonic() - last_reload >= RENEW_RELOAD_EVERY:
                if last_reload is not None:
                    self._reset_site_data()
                self._reload(timeout)
                last_reload = time.monotonic()
            time.sleep(2)
            token = self._token()
            if token and token != before and not token_expired(token):
                self.renewals += 1
                P.log(f"[browser] token renewed {round(time.monotonic() - started)} s after the reload ({self.renewals} so far)")
                return True
            if time.monotonic() - last_word >= 60:
                waited = round(time.monotonic() - started)
                if self._check_shown():
                    P.log(f"[browser] waiting {waited} s: the site's check is showing in the Chrome window and needs a click there")
                else:
                    P.log(f"[browser] waiting {waited} s for a fresh token; if a check appears in the Chrome window, click it")
                last_word = time.monotonic()
        self.renewals_failed += 1
        P.log(f"[browser] no fresh token after {RENEW_WAIT} s; giving up this renewal")
        return False

    def _find_page(self):
        context = self._browser.contexts[0]
        for page in context.pages:
            if page.url.startswith(self.origin):
                return page
        page = context.new_page()
        page.goto(self.origin + "/", wait_until="domcontentloaded")
        return page

    def _rewrite(self, url: str) -> str:
        for prefix, replacement in self.url_map.items():
            if url.startswith(prefix):
                return replacement + url[len(prefix):]
        return url

    def _evaluate(self, target: str, sent: dict, timeout: int) -> dict:
        try:
            return self.page.evaluate(FETCH_JS, {"url": target, "headers": sent})
        except Exception as err:  # the tab was reloading (the site does that after storing a token)
            message = str(err)
            if "Execution context was destroyed" in message or "Target closed" in message or "navigation" in message:
                self.page = self._find_page()
                self.page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
                return self.page.evaluate(FETCH_JS, {"url": target, "headers": sent})
            raise

    def get(self, url: str, timeout: int = 30, headers: dict | None = None) -> BrowserResponse:
        sent = allowed_headers(headers)
        target = self._rewrite(url)
        result = self._evaluate(target, sent, timeout)
        if is_challenge(result["status"], result["body"]) and self.token_key and self.renew(timeout):
            result = self._evaluate(target, sent, timeout)
        return BrowserResponse(result["status"], result["headers"], result["body"], result["url"])

    def close(self) -> None:
        try:
            self._browser.close()  # disconnects; the user's Chrome window stays open
        finally:
            self._playwright.stop()


class BrowserClient(P.Client):
    """common.Client with a browser tab as its transport (same pacing, retries, block handling and stats)."""

    def __init__(self, cdp_url: str = "http://localhost:9222", *, origin: str, url_map: dict[str, str] | None = None,
                 token_key: str | None = None, min_interval: float = 2.0, jitter: float = 1.0,
                 max_requests: int | None = None, timeout: int = 30, retries: int = 3, headers: dict | None = None):
        session = PageSession(cdp_url, origin, url_map, token_key)
        super().__init__(f"browser:{session.version}", session=session, min_interval=min_interval, jitter=jitter,
                         max_requests=max_requests, timeout=timeout, retries=retries, headers=headers)
        self.block_retries = 2  # after a failed renewal, two more minutes in case the check waits for a click

    def stats(self) -> dict:
        return {**super().stats(), "transport": "browser", "cdp_url": self._session.cdp_url,
                "page_reloads": self._session.reloads, "token_renewals": self._session.renewals,
                "renewals_failed": self._session.renewals_failed, "site_data_resets": self._session.resets}

    def close(self) -> None:
        self._session.close()
