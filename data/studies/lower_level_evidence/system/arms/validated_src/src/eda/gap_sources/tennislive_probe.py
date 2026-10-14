"""TennisLive.net against the data map's gaps: does it hold the sampled matches, with points and statistics?

For every "check" row of data/studies/gap_sources/sample_matches.csv (drawn by sample.py; 226 matches in five
gaps) the probe asks three questions: does TennisLive have the match page, does the page carry the point-by-point
record, and does it carry the match statistics block? A point record is compared with the match's final score
(games per set): *complete*, *only set-closing games missing* (the known TennisLive pattern: a set's game list
stops at the state before its last game), *other shortfall*, or *no points*.

How a match is reached (the site has no stable address to build: ITF slugs carry edition counters such as
"m15-monastir-2021-30", and player slugs are irregular, e.g. "lukas-klein-", "gabi-adrian-boitan"):

1. **A player's season listing.** ``/api/player-matches?tour=<atp|wta>&slug=<slug>&discipline=singles&year=<y>
   &surface=all&offset=<n>`` (60 a page, newest first), the endpoint src/ingest/point_sources/tennislive.py reads.
   It needs the per-session token of a page fetched in the same session (cookie ``TENNISLIVESESSID``); a token
   from an earlier session is refused with HTTP 403 (observed 29 Sep 2026), so each run opens with one page.
2. **The player's slug**, tried in this order for the first player, then the second: a slug already seen in a
   cached listing or search answer (same name words), the lower-case hyphenated name, the site search
   (``/api/search?q=<name>``, the site's own search box, same token), and the search on the surname alone.
3. **The match in the listing**: the opponent shares a name word with the other player and the match starts
   within 10 days before and 21 days after the tournament week start (``d``); ties go to the listed set scores
   equal to the reference score, the draw, then the tournament's own dates; at a year boundary the neighbouring
   season is read too. When no name word is shared, near-identical words are accepted (transliterations such
   as "Illia Biloborodko" / "Illya Beloborodko"), but only with set scores equal to the reference score.
4. **The match page** (``/<tour>/match/<p1>-VS-<p2>/<tournament>/``), parsed with the adapter's
   ``parse_match_page``.

The final score compared is the creator's own row (Tennis My Life or Sackmann ``score``; api-tennis set
scores for the one api-tennis match), else TennisLive's own. Completeness uses the rules of
src/eda/point_shot_sources/verify_scrape.py (``completeness``, ``short_kind``), imported; games listed without
their points are counted apart (``games_without_points``, ``point_game_share``). The page's statistics block is
also compared with the reference row's box score (Sackmann columns; both players aligned by name), and the
page's score and winner with the reference.

Pace and stops (the lane's rules): one request at a time, at least 2 s apart plus up to 1 s jitter (curl_cffi's
Safari profile, as the adapter); HTTP 403 or 429, a Cloudflare challenge or a CAPTCHA page stops the run at
once, with no retry; every request is logged to _requests.jsonl and the lane may not pass 1,000 requests over
all its runs. Nothing is fetched twice: every answer is cached with a receipt, so a rerun resumes from the cache.
TennisLive's terms forbid automated extraction and its robots.txt disallows /api/player-*; this is a bounded
measurement under the owner's decision of 23 Sep 2026 (collect regardless, non-commercial research).

Usage:
    ./python.sh src/eda/gap_sources/tennislive_probe.py [--limit N] [--gaps itf_detail,...]
    ./python.sh src/eda/gap_sources/tennislive_probe.py --offline        # rebuild the tables from the cache only

Reads data/studies/gap_sources/sample_matches.csv, the Tennis My Life and Sackmann match dumps under
data/dump/matches/ and the api-tennis fixtures under data/raw/public_dump/atp_pipeline_handoff/api_tennis/.
Writes data/raw/gap_sources/tennislive/ (verbatim answers, HTML gzipped; _receipts.jsonl; _requests.jsonl, one
line per request; _runs.jsonl, one line per online run) and data/studies/gap_sources/tennislive_matches.csv,
tennislive_summary.json. Findings: data/studies/gap_sources/research_notes/D_tennislive.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import math
import re
import sys
import time
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.point_shot_sources.verify_scrape import COMPLETE, completeness, official_sets, short_kind  # noqa: E402
from src.ingest.point_sources import common as P        # noqa: E402
from src.ingest.point_sources import tennislive as TL   # noqa: E402
from src.ingest.public_dump import common as C          # noqa: E402

SOURCE = "tennislive"
SITE = "https://www.tennislive.net"
RAW = PROJECT_ROOT / "data" / "raw" / "gap_sources"
FOLDER = RAW / SOURCE
LEDGER = FOLDER / "_requests.jsonl"          # one line per HTTP request, retries included: the budget's count
OUT = PROJECT_ROOT / "data" / "studies" / "gap_sources"
DUMP = PROJECT_ROOT / "data" / "dump" / "matches"
API_TENNIS = PROJECT_ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "api_tennis"
BUDGET = 1000
BLOCK_WORDS = ("captcha", "challenge", "blocked", "too many", "rate limit", "access denied")
PARTICLES = {"jr", "sr", "ii", "iii", "iv", "de", "da", "van", "von", "del", "der", "la", "le", "di", "dos", "du",
             "do", "e", "y"}
MAX_PAGES = 4                                  # listing pages per player and season (60 matches each)
WINDOW = (-10, 21)                             # days around the tournament week start
EXPLORATION = (
    "The ledger's first six requests (29 Sep 2026, 17:41-17:45 UTC) were made by hand before the probe ran: a "
    "player page (/atp/nicolae-frunza/), the site scripts /Frontend/assets/js/shell.js and app.js (to read how "
    "the search box calls /api/search), one /api/player-matches call that reused the token of a page fetched in "
    "an earlier Python session and was refused with HTTP 403 (no Cloudflare challenge; the adapter always reads "
    "the token from a page fetched in the same session), then the player page and the same API call in one "
    "session, which answered 200. The 403 is counted as a session-token error, not a block.")


# ------------------------------------------------------------------------------------------ fetching
def requests_made() -> int:
    if not LEDGER.exists():
        return 0
    return sum(1 for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip())


class StrictClient(P.Client):
    """P.Client's pacing, with stricter stops: HTTP 403 or 429, a Cloudflare challenge, or a page that reads as
    a CAPTCHA or challenge stops the run at once (no retry); every request is logged to LEDGER (with the first
    300 bytes of any refusal), and the lane's total across runs may not pass BUDGET."""

    def __init__(self, *, min_interval: float = 2.0, jitter: float = 1.0, budget: int = BUDGET):
        super().__init__(TL.IMPERSONATE, min_interval=min_interval, jitter=jitter, retries=2)
        self.used_before = requests_made()
        self.budget = budget
        self.kinds = Counter()

    def _log(self, url: str, status, note: str | None = None, at: str | None = None, seconds: float | None = None) -> None:
        FOLDER.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"at": at or C.utc_now_iso(), "url": url, "status": status, "note": note,
                                     "seconds": seconds}) + "\n")

    def get(self, url: str, headers: dict | None = None):
        last_error = None
        for attempt in range(self.retries + 1):
            if self.used_before + self.requests >= self.budget:
                raise P.BudgetExhausted(f"lane budget of {self.budget} requests used up")
            self._pace()
            self.requests += 1
            self.kinds[request_kind(url)] += 1
            at, t0 = C.utc_now_iso(), time.monotonic()
            self._last = t0
            try:
                response = self._session.get(url, timeout=self.timeout, headers={**self._headers, **(headers or {})})
            except Exception as err:  # network trouble is not a block: retried twice
                last_error = f"{type(err).__name__}: {err}"
                self._last = time.monotonic()
                self._log(url, None, last_error[:200], at, round(self._last - t0, 2))
                self.retried += 1
                self._sleep(5 * (attempt + 1))
                continue
            self._last = time.monotonic()           # the pause runs from the end of the answer, not its start
            status = response.status_code
            challenged = response.headers.get("cf-mitigated") == "challenge"
            head = response.content[:6000].lower()
            captcha_page = (b"<title>just a moment" in head or b"cf-chl" in head or b"g-recaptcha" in head
                            or b"h-captcha" in head or b"cf-turnstile" in head)
            refused = status in (403, 429) or challenged or captcha_page
            note = ("challenge " if challenged or captcha_page else "") + (
                response.content[:300].decode("utf-8", errors="replace") if refused else "")
            self._log(url, status, note.strip() or None, at, round(self._last - t0, 2))
            if refused:
                what = "Cloudflare challenge" if challenged else "CAPTCHA/challenge page" if captcha_page else f"HTTP {status}"
                raise P.Blocked(f"{what} for {url}")
            if status >= 500:
                last_error = f"HTTP {status}"
                self.retried += 1
                self._sleep(5 * (attempt + 1))
                continue
            return response
        raise RuntimeError(f"{last_error} for {url} after {self.retries + 1} attempts")

    def stats(self) -> dict:
        return {**super().stats(), "jitter": self.jitter, "by_kind": dict(self.kinds),
                "lane_requests_before_run": self.used_before,
                "lane_requests_after_run": self.used_before + self.requests, "lane_budget": self.budget}


def request_kind(url: str) -> str:
    path = url.replace(SITE, "")
    if path.startswith("/api/player-matches"):
        return "listing"
    if path.startswith("/api/search"):
        return "search"
    if "/match/" in path:
        return "match page"
    if path.startswith("/Frontend/") or path.startswith("/assets/"):
        return "script"
    return "page"


def api_validator(body: bytes):
    """JSON, and not a refusal in disguise (a status other than "ok" that speaks of a block or the session)."""
    problem = P.json_validator(body)
    if problem:
        return problem
    try:
        payload = json.loads(body)
    except ValueError:
        return "response is not valid JSON"
    if isinstance(payload, dict) and payload.get("status") != "ok":
        text = json.dumps(payload, ensure_ascii=False)[:600].lower()
        if any(w in text for w in BLOCK_WORDS + ("token", "session", "csrf")):
            return f"refused: {text[:200]}"
    return None


class Site:
    """Cached, receipted reads of TennisLive for one run; offline, only the cache is read."""

    def __init__(self, client: StrictClient | None, receipts: C.Receipts, offline: bool):
        self.client, self.receipts, self.offline = client, receipts, offline
        self.token: str | None = None
        self.session_page: str | None = None

    # -- low level
    def final(self, name: str, dest: Path) -> dict | None:
        """The receipt of an answer already on record and final (a 200 on disk, or a 404), else None. A JSON
        answer whose status is not "ok" is saved as a 200 and is final too."""
        previous = self.receipts.get(name)
        if previous and not previous.get("error") and (
                previous.get("status") == 404 or previous.get("absent")
                or (previous.get("status") == 200 and dest.exists())):
            return previous
        return None

    def _get(self, url: str, dest: Path, name: str, *, validator, compress: bool, headers: dict | None = None,
             refresh: bool = False) -> dict:
        previous = self.final(name, dest)
        if previous and not refresh:
            return {**previous, "skipped": True}
        if self.offline:
            return {"name": name, "not_fetched": True}
        return P.fetch(self.client, url, dest, self.receipts, name=name, refresh=True, validator=validator,
                       compress=compress, headers=headers)

    @staticmethod
    def ok(r: dict, dest: Path) -> bool:
        return r.get("status") == 200 and not r.get("error") and dest.exists()

    def ensure_session(self, tour: str | None = None, slug: str | None = None) -> None:
        """A fresh page in this session for the request token: the player's own page when a player is being
        read (it also shows whether the slug exists), else the home page."""
        if self.token or self.offline:
            return
        pages = [("/", FOLDER / "session" / "home.html.gz", "session/home")]
        if tour and slug:
            pages.insert(0, (f"/{tour}/{slug}/", FOLDER / "players" / tour / slug / "page.html.gz",
                             f"players/{tour}/{slug}/page"))
        for path, dest, name in pages:
            r = self._get(SITE + path, dest, name, validator=P.html_validator, compress=True, refresh=True)
            if self.ok(r, dest):
                rt = TL.runtime_object(P.read_bytes(dest).decode("utf-8", errors="replace"))
                token = rt.get("playerLiveRequestToken") or rt.get("searchRequestToken") or rt.get("matchDetailRequestToken")
                if token:
                    self.token, self.session_page = token, path
                    return
        raise RuntimeError("no page gave a session token")

    # -- endpoints
    def listing(self, tour: str, slug: str, year: int, offset: int) -> tuple[str, dict | None]:
        """One season page of a player's matches: ("ok", payload), ("absent", None), ("not ok", payload),
        ("not fetched", None) or ("error", None)."""
        dest = FOLDER / "players" / tour / slug / f"matches_{year}_{offset}.json"
        name = f"players/{tour}/{slug}/matches_{year}_{offset}"
        page_receipt = self.receipts.get(f"players/{tour}/{slug}/page") or {}
        if page_receipt.get("status") == 404 and not self.final(name, dest):
            return "absent", None                       # the player page itself is a 404: no such slug
        if not self.offline and not self.final(name, dest):
            self.ensure_session(tour, slug)
            page_receipt = self.receipts.get(f"players/{tour}/{slug}/page") or {}
            if page_receipt.get("status") == 404:
                return "absent", None
        url = (f"{SITE}/api/player-matches?tour={tour}&slug={quote(slug)}&discipline=singles&year={year}"
               f"&surface=all&offset={offset}")
        headers = {**TL.API_HEADERS, "X-TennisLive-Token": self.token or "", "Referer": f"{SITE}/{tour}/{slug}/"}
        r = self._get(url, dest, name, validator=api_validator, compress=False, headers=headers)
        return self._json_outcome(r, dest)

    def search(self, query: str) -> tuple[str, dict | None]:
        key = C.slugify(query)
        dest = FOLDER / "search" / f"{key}.json"
        name = f"search/{key}"
        if not self.offline and not self.final(name, dest):
            self.ensure_session()
        url = f"{SITE}/api/search?q={quote(query)}"
        headers = {"Accept": "application/json", "X-Requested-With": "XMLHttpRequest", "Sec-Fetch-Dest": "empty",
                   "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin", "X-TennisLive-Token": self.token or "",
                   "Referer": SITE + (self.session_page or "/")}
        r = self._get(url, dest, name, validator=api_validator, compress=False, headers=headers)
        return self._json_outcome(r, dest)

    def match_page(self, url: str) -> tuple[str, str | None, dict]:
        parts = TL.match_path_parts(url)
        if parts is None:
            return "bad url", None, {}
        tour, players, tournament = parts
        dest = FOLDER / "matches" / tour / players / f"{tournament}.html.gz"
        r = self._get(SITE + url, dest, f"matches{url}", validator=P.html_validator, compress=True)
        if self.ok(r, dest):
            return "200", P.read_bytes(dest).decode("utf-8", errors="replace"), r
        if r.get("not_fetched"):
            return "not fetched", None, r
        return str(r.get("error") or r.get("status")), None, r

    def _json_outcome(self, r: dict, dest: Path) -> tuple[str, dict | None]:
        if str(r.get("error") or "").startswith("refused") and not r.get("skipped"):
            # an answer that speaks of a block, the token or the session: stop and look, never insist
            raise P.Blocked(f"API refused for {r.get('url')}: {r['error']}")
        if r.get("not_fetched"):
            return "not fetched", None
        if r.get("status") == 404 or r.get("absent"):
            return "absent", None
        if not self.ok(r, dest):
            return "error", None
        payload = P.read_json(dest)
        return ("ok" if isinstance(payload, dict) and payload.get("status") == "ok" else "not ok"), payload


# ------------------------------------------------------------------------------------------ names
def ascii_fold(text) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", str(text or "")) if not unicodedata.combining(ch))


def words(name) -> frozenset:
    parts = re.split(r"[^a-z]+", ascii_fold(name).lower())
    return frozenset(w for w in parts if len(w) >= 2 and w not in PARTICLES)


def guess_slug(name: str) -> str:
    text = ascii_fold(name).lower().replace("'", "").replace("’", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def slug_of_url(url: str | None) -> tuple[str, str] | None:
    m = re.fullmatch(r"/(atp|wta)/([^/]+)/?", str(url or ""))
    return (m.group(1), m.group(2)) if m and m.group(2) not in ("match", "ranking") else None


def name_agreement(a: frozenset, b: frozenset) -> int:
    return len(a & b)


def loose_agreement(a: frozenset, b: frozenset) -> int:
    """Words of ``a`` with a near-identical word in ``b`` (4+ letters, similarity 0.8 or more): transliteration
    variants such as "Illia Biloborodko" / "Illya Beloborodko". Used only as a fallback, and a loosely named
    match is accepted only when its listed set scores equal the reference score."""
    return sum(1 for x in a if len(x) >= 4 and any(len(y) >= 4 and SequenceMatcher(None, x, y).ratio() >= 0.8
                                                   for y in b))


class SlugIndex:
    """Player name -> TennisLive slugs, from every cached listing and search answer, with where each was seen."""

    def __init__(self):
        self.by_words: dict[frozenset, set[tuple[str, str]]] = {}
        self.seen_in: dict[tuple[str, str], set[str]] = {}

    def add(self, name, url, where: str) -> None:
        key = slug_of_url(url)
        w = words(name)
        if key and w:
            self.by_words.setdefault(w, set()).add(key)
            self.seen_in.setdefault(key, set()).add(where)

    def load(self) -> "SlugIndex":
        for path in FOLDER.glob("players/*/*/matches_*_*.json"):
            try:
                payload = P.read_json(path)
            except (OSError, ValueError):
                continue
            owner = path.parent.name
            for group in ((payload.get("data") or {}).get("groups") or []):
                for match in group.get("matches") or []:
                    for p in match.get("players") or []:
                        key = slug_of_url(p.get("url"))
                        self.add(p.get("name"), p.get("url"), "own listing" if key and key[1] == owner else "listing")
        for path in FOLDER.glob("search/*.json"):
            try:
                payload = P.read_json(path)
            except (OSError, ValueError):
                continue
            for item in payload.get("players") or []:
                self.add(item.get("name"), item.get("url"), "search")
        return self

    def known(self, name: str, tour: str) -> list[str]:
        """Slugs whose listed name has the same words as ``name`` (exactly), on this tour."""
        return sorted(slug for t, slug in self.by_words.get(words(name), set()) if t == tour)

    def provenance(self, name: str, tour: str, slug: str) -> str:
        """How the slug is known: the plain hyphenated name, the site search, or another player's listing."""
        if slug == guess_slug(name):
            return "plain-name"
        seen = self.seen_in.get((tour, slug), set())
        if "search" in seen:
            return "searched"
        return "seen in another listing" if "listing" in seen else "plain-name"


# ------------------------------------------------------------------------------------------ reference scores
BOX = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "bpSaved", "bpFaced"]


def reference_scores(checks: pd.DataFrame) -> pd.DataFrame:
    """uid -> (score, source, round, box score) from the row of the source that created the match in the map."""
    cols = ["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"] + \
        [f"{side}_{k}" for side in ("w", "l") for k in BOX]
    years = set(range(int(checks["year"].min()) - 1, int(checks["year"].max()) + 1))

    def read(pattern: str, tour: str) -> pd.DataFrame:
        frames = []
        for path in sorted(glob.glob(str(DUMP / pattern))):
            m = re.search(r"(19|20)\d{2}", Path(path).name)
            if m and int(m.group(0)) in years:
                frames.append(pd.read_parquet(path, columns=cols))
        frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=cols)
        return frame.assign(tour=tour)

    sack = pd.concat([read("sackmann_archive/atp/atp_matches_futures_*.parquet", "M"),
                      read("sackmann_archive/atp/atp_matches_20[0-9][0-9].parquet", "M"),
                      read("sackmann_archive/atp/atp_matches_qual_chall_*.parquet", "M"),
                      read("sackmann_archive/wta/wta_matches_20[0-9][0-9].parquet", "W"),
                      read("sackmann_archive/wta/wta_matches_qual_itf_*.parquet", "W")], ignore_index=True)
    tml = [read("tennis_my_life/atp_main/*.parquet", "M"), read("tennis_my_life/atp_qualifying/*.parquet", "M"),
           read("tennis_my_life/atp_challenger/*.parquet", "M"), read("tennis_my_life/wta_main/*.parquet", "W")]
    for path in sorted((DUMP / "tennis_my_life" / "ongoing").glob("*.parquet")):
        tml.append(pd.read_parquet(path, columns=cols).assign(tour="W" if "wta" in path.name else "M"))
    tml = pd.concat(tml, ignore_index=True)

    def keyed(frame: pd.DataFrame) -> pd.DataFrame:
        d = pd.to_datetime(frame["tourney_date"].astype(str).str[:8], format="%Y%m%d", errors="coerce")
        frame = frame.assign(key=frame["tour"] + "|" + frame["tourney_name"].fillna("").str.lower().str.strip() + "|"
                             + d.dt.strftime("%Y-%m-%d").fillna("") + "|" + frame["winner_name"].fillna("") + "|"
                             + frame["loser_name"].fillna(""))
        return frame.drop_duplicates("key").set_index("key")

    sack, tml = keyed(sack), keyed(tml)
    key = (checks["tour"] + "|" + checks["tname"].fillna("").str.lower().str.strip() + "|" + checks["d"].astype(str)
           + "|" + checks["name1"] + "|" + checks["name2"])
    out = pd.DataFrame({"uid": checks["uid"].to_numpy()}, index=checks.index)
    out["ref_score"], out["ref_source"], out["ref_round"], out["ref_winner"], out["ref_box"] = None, None, None, None, None
    box_cols = [f"{side}_{k}" for side in ("w", "l") for k in BOX]
    out["ref_box_source"] = None
    for idx, k, creator in zip(checks.index, key, checks["creator"]):
        for label, table in (("tml", tml), ("sackmann", sack)) if creator == "tml" else (("sackmann", sack), ("tml", tml)):
            if k not in table.index:
                continue
            row = table.loc[k]
            if out.at[idx, "ref_score"] is None:           # the score: the creator's row first
                out.loc[idx, ["ref_score", "ref_source", "ref_round", "ref_winner"]] = [row["score"], label, row["round"], 1]
            box = {c: row[c] for c in box_cols if pd.notna(row[c]) and str(row[c]).strip() != ""}
            if box and out.at[idx, "ref_box"] is None and float(box.get("w_svpt") or 0) > 0:
                out.at[idx, "ref_box"] = json.dumps(box)     # the box score: the first row that has one
                out.at[idx, "ref_box_source"] = label
    # the api-tennis creations: set scores from the fixture's scores_json (first player's games first)
    for idx in checks.index[checks["creator"].eq("api_tennis") & out["ref_score"].isna()]:
        row = checks.loc[idx]
        path = API_TENNIS / f"fixtures_{int(row['year'])}.csv.gz"
        if not path.exists():
            continue
        f = pd.read_csv(path, dtype=str, low_memory=False)
        hit = f[f["event_first_player"].eq(row["name1"]) & f["event_second_player"].eq(row["name2"])
                & f["event_date"].eq(str(row["d"]))]
        if len(hit):
            sets = json.loads(hit.iloc[0]["scores_json"] or "[]")
            score = " ".join(f"{s['score_first']}-{s['score_second']}" for s in sets)
            winner = 1 if hit.iloc[0]["event_winner"] == "First Player" else 2 if hit.iloc[0]["event_winner"] == "Second Player" else None
            out.loc[idx, ["ref_score", "ref_source", "ref_round", "ref_winner"]] = [score, "api_tennis",
                                                                                   hit.iloc[0]["tournament_round"], winner]
    return out


# ------------------------------------------------------------------------------------------ matching
def listing_matches(payload: dict) -> list[dict]:
    out = []
    for group in ((payload or {}).get("data") or {}).get("groups") or []:
        for match in group.get("matches") or []:
            if match.get("doubles"):
                continue
            players = match.get("players") or []
            if len(players) != 2:
                continue
            out.append({"url": match.get("url"), "ts": match.get("startTimestamp"), "state": match.get("state"),
                        "stage": match.get("stageCode") or match.get("stage"), "tournament": group.get("name"),
                        "tournament_url": group.get("url"), "info": group.get("info"),
                        "names": [players[0].get("name"), players[1].get("name")],
                        "urls": [players[0].get("url"), players[1].get("url")],
                        "words": [words(players[0].get("name")), words(players[1].get("name"))],
                        "winner_side": next((i for i, p in enumerate(players) if p.get("id") == match.get("winnerId")), None),
                        "games": listed_games(players), "start_times": group.get("startTimes") or []})
    return out


def listed_games(players: list[dict]) -> list[int]:
    """Games per set of a listed match, from both players' set scores (a tiebreak set is {"score": 7, ...})."""
    sets = [p.get("sets") or [] for p in players]
    out = []
    for a, b in zip(*sets):
        a = a.get("score") if isinstance(a, dict) else a
        b = b.get("score") if isinstance(b, dict) else b
        try:
            out.append(int(a) + int(b))
        except (TypeError, ValueError):
            return []
    return out


def match_time(m: dict) -> pd.Timestamp | None:
    if m["ts"]:
        return pd.Timestamp(int(m["ts"]), unit="s")
    for text in m["start_times"]:
        try:
            return pd.Timestamp(dt.datetime.strptime(text, "%b %d, %Y"))
        except (TypeError, ValueError):
            continue
    return None


def find_in(matches: list[dict], w1: frozenset, w2: frozenset, d: pd.Timestamp, draw: str,
            official: list[int] | None = None, slam: bool = False) -> dict | None:
    """The listed match of the two players inside the date window. Ties (players who met in neighbouring
    weeks) go to: more name words shared, the reference score's games per set, the draw (qualifying or main),
    a start inside the tournament's own span (3 days before its week to 8 days after, 15 at a Slam), then the
    date nearest the week start."""
    lo, hi = d + pd.Timedelta(days=WINDOW[0]), d + pd.Timedelta(days=WINDOW[1] + 1)
    span = (d - pd.Timedelta(days=3), d + pd.Timedelta(days=15 if slam else 8))
    for agreement, how in ((name_agreement, "exact"), (loose_agreement, "loose")):
        best, best_key = None, None
        for m in matches:
            t = match_time(m)
            if t is None or not lo <= t <= hi:
                continue
            a, b = m["words"]
            score = 0
            for x, y in ((a, b), (b, a)):
                s1, s2 = agreement(w1, x), agreement(w2, y)
                if s1 and s2:
                    score = max(score, s1 + s2)
            if not score:
                continue
            score_ok = bool(official) and m.get("games") == official
            if how == "loose" and not score_ok:
                continue
            qual_listed = "qualif" in str(m["stage"] or "").lower()
            key = (score, score_ok, (draw == "qual") == qual_listed, span[0] <= t <= span[1],
                   -abs((t - d).total_seconds()))
            if best_key is None or key > best_key:
                best, best_key = {**m, "time": t, "listed_score_agrees": score_ok if official else None,
                                  "name_match": how}, key
        if best is not None:
            return best
    return None


def season_years(d: pd.Timestamp, year: int) -> list[int]:
    years = [year]
    if d.month == 1 and d.day <= 10:
        years.append(year - 1)
    if d.month == 12 and d.day >= 15:
        years.append(year + 1)
    return years


class Resolver:
    def __init__(self, site: Site):
        self.site = site
        self.slugs = SlugIndex().load()
        self.bad_slugs: set[tuple[str, str]] = set()

    def season(self, tour: str, slug: str, year: int, d: pd.Timestamp) -> tuple[str, list[dict], int]:
        """A player's season listing, page by page until the window's start is passed: (outcome, matches, pages)."""
        matches, pages, outcome = [], 0, "ok"
        lo = d + pd.Timedelta(days=WINDOW[0])
        for page in range(MAX_PAGES):
            status, payload = self.site.listing(tour, slug, year, page * 60)
            if status != "ok":
                outcome = status if page == 0 else outcome
                break
            pages += 1
            got = listing_matches(payload)
            matches.extend(got)
            data = payload.get("data") or {}
            total, limit = int(data.get("total") or 0), int(data.get("limit") or 60)
            if total == 0 and page == 0:
                outcome = "empty"
            times = [t for t in (match_time(m) for m in got) if t is not None]
            if (page + 1) * limit >= total or not got or (times and min(times) < lo):
                break
        for m in matches:
            for name, url in zip(m["names"], m["urls"]):
                key = slug_of_url(url)
                self.slugs.add(name, url, "own listing" if key and key[1] == slug else "listing")
        return outcome, matches, pages

    def search_slugs(self, name: str, tour: str, attempts: list[str]) -> list[str]:
        """Player slugs the site search returns for the full name, then the surname alone, best agreement first."""
        target = words(name)
        found: list[tuple[int, str]] = []
        queries = [name]
        parts = [w for w in re.split(r"\s+", ascii_fold(name).strip()) if w]
        if len(parts) >= 2:
            queries.append(parts[-1] if len(parts[-1]) >= 4 else " ".join(parts[-2:]))
        for q in queries:
            status, payload = self.site.search(q)
            items = (payload or {}).get("players") or [] if status == "ok" else []
            attempts.append(f"search '{q}': {status}, {len(items)} players")
            for item in items:
                key = slug_of_url(item.get("url"))
                if not key or key[0] != tour:
                    continue
                self.slugs.add(item.get("name"), item.get("url"), "search")
                agree = name_agreement(target, words(item.get("name")))
                if agree:
                    found.append((agree, key[1]))
            if found:
                break
        return [s for _, s in sorted(set(found), key=lambda x: (-x[0], x[1]))][:3]

    def resolve(self, row: pd.Series) -> dict:
        tour = "atp" if row["tour"] == "M" else "wta"
        d = pd.Timestamp(row["d"])
        year = int(row["year"])
        w = {1: words(row["name1"]), 2: words(row["name2"])}
        official = official_sets(row["ref_score"]) if isinstance(row.get("ref_score"), str) else []
        slam = row["level"] in ("GS", "GSQ")
        attempts: list[str] = []
        tried: set[tuple[str, int]] = set()
        missing = []                                      # answers not in the cache (offline runs)

        def look(side: int, slug: str) -> dict | None:
            if (tour, slug) in self.bad_slugs:
                return None
            for y in season_years(d, year):
                if (slug, y) in tried:
                    continue
                tried.add((slug, y))
                outcome, matches, pages = self.season(tour, slug, y, d)
                attempts.append(f"name{side} '{slug}' {y}: {outcome}, {len(matches)} listed")
                if outcome in ("absent", "not ok"):
                    self.bad_slugs.add((tour, slug))
                    return None
                if outcome == "not fetched":
                    missing.append(slug)
                    return None
                hit = find_in(matches, w[1], w[2], d, row["draw"], official, slam)
                if hit:
                    how = self.slugs.provenance(row[f"name{side}"], tour, slug)
                    loose = "; names matched loosely" if hit.get("name_match") == "loose" else ""
                    return {**hit, "found_via": f"name{side} listing (slug: {how}{loose})", "listing_slug": slug,
                            "listing_year": y}
            return None

        order = [1, 2]
        # a player already listed for this season goes first (no request), then the one with a known slug
        cached = {s: any((FOLDER / "players" / tour / slug / f"matches_{year}_0.json").exists()
                         for slug in self.slugs.known(row[f"name{s}"], tour) + [guess_slug(row[f"name{s}"])])
                  for s in order}
        known = {s: bool(self.slugs.known(row[f"name{s}"], tour)) for s in order}
        order.sort(key=lambda s: (not cached[s], not known[s], s))
        for s in order:                                   # slugs seen on the site, then the plain name
            candidates = self.slugs.known(row[f"name{s}"], tour)
            guess = guess_slug(row[f"name{s}"])
            for slug in candidates + ([guess] if guess and guess not in candidates else []):
                hit = look(s, slug)
                if hit:
                    return {**hit, "attempts": attempts}
        for s in order:                                   # the site search
            for slug in self.search_slugs(row[f"name{s}"], tour, attempts):
                hit = look(s, slug)
                if hit:
                    return {**hit, "attempts": attempts}
        if missing or any(": not fetched" in a for a in attempts):
            return {"found_via": "not fetched", "attempts": attempts}
        return {"found_via": "not found", "attempts": attempts}


# ------------------------------------------------------------------------------------------ the page
def inspect(html: str) -> dict:
    parsed = TL.parse_match_page(html)
    meta = parsed["meta"]
    per_set: dict[int, int] = {}
    last_after: dict[int, int | None] = {}
    for g in parsed["games"]:
        if g["game"] > 0:
            per_set[g["set"]] = max(per_set.get(g["set"], 0), g["game"])
            m = re.fullmatch(r"(\d+)-(\d+)", str(g["after"] or "").strip())
            last_after[g["set"]] = int(m.group(1)) + int(m.group(2)) if m else None
    sets = list(range(1, max(per_set) + 1)) if per_set else []      # aligned by set number; a missing set is 0
    per_set = {s: per_set.get(s, 0) for s in sets}
    periods = Counter(st["period"] for st in parsed["statistics"])
    return {"tl_score": meta.get("score"), "tl_state": meta.get("state"), "tl_end_reason": meta.get("end_reason"),
            "tl_best_of": meta.get("best_of"), "tl_date": meta.get("date_shown"), "tl_round": meta.get("round_shown"),
            "tl_tournament": meta.get("tournament_name"), "tl_names": " | ".join(str(n) for n in meta.get("player_names") or []),
            "tl_winner_side": next((i for i, k in enumerate(("player1_id", "player2_id"))
                                    if meta.get(k) is not None and meta.get(k) == meta.get("winner_id")), None),
            "record_games": [per_set[s] for s in sets], "last_after": [last_after.get(s) for s in sets],
            "sets_listed": meta.get("sets_listed"), "games_listed": meta.get("games_listed"),
            "games_without_points": meta.get("games_without_points"), "points_listed": meta.get("points_listed"),
            "pbp_unavailable_notice": meta.get("pbp_unavailable_notice"),
            "stats_available": bool(parsed["statistics"]), "stats_rows": len(parsed["statistics"]),
            "stats_match_rows": periods.get("match", 0), "stats_periods": ";".join(sorted(periods)),
            "stats_names": ";".join(st["name"] for st in parsed["statistics"] if st["period"] == "match"),
            "stats_unavailable_notice": meta.get("stats_unavailable_notice"),
            "tl_box": tl_box(parsed["statistics"])}


def _ratio(text) -> tuple[int, int] | None:
    m = re.fullmatch(r"\s*(\d+)\s*/\s*(\d+)\s*", str(text or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _int(text) -> int | None:
    m = re.fullmatch(r"\s*(\d+)\s*", str(text or ""))
    return int(m.group(1)) if m else None


def tl_box(statistics: list[dict]) -> list[dict] | None:
    """The match statistics block as a Sackmann-style box score per TennisLive player (page order): aces, double
    faults, serve points, first serves in and won, second-serve points won, break points faced and saved (read
    from the opponent's "break points converted")."""
    rows = {st["name"]: st for st in statistics if st["period"] == "match"}
    if not rows:
        return None
    out = [{}, {}]
    for side, key in ((0, "player1"), (1, "player2")):
        first = _ratio((rows.get("First serve") or {}).get(f"{key}_detail"))
        won1 = _ratio((rows.get("First serve points won") or {}).get(f"{key}_detail"))
        won2 = _ratio((rows.get("Second serve points won") or {}).get(f"{key}_detail"))
        out[side].update(ace=_int((rows.get("Aces") or {}).get(f"{key}_value")),
                         df=_int((rows.get("Double faults") or {}).get(f"{key}_value")),
                         svpt=first[1] if first else None, **{"1stIn": first[0] if first else None,
                                                             "1stWon": won1[0] if won1 else None,
                                                             "2ndWon": won2[0] if won2 else None})
        conv = _ratio((rows.get("Break points converted") or {}).get(f"{key}_detail"))
        other = out[1 - side]
        other["bpFaced"] = conv[1] if conv else None
        other["bpSaved"] = conv[1] - conv[0] if conv else None
    return out


def box_compare(ref_box: str | None, tl: list[dict] | None, winner_side) -> dict:
    """TennisLive's statistics against the reference box score (winner first): fields compared and equal."""
    if not isinstance(ref_box, str) or not ref_box or not tl or winner_side is None or pd.isna(winner_side):
        return {"box_compared": False}
    ref = json.loads(ref_box)
    try:
        if float(ref.get("w_svpt") or 0) <= 0:
            return {"box_compared": False}
    except (TypeError, ValueError):
        return {"box_compared": False}
    def compare(sides: dict) -> tuple[int, int, int, list[str]]:
        compared, equal, worst, differ = 0, 0, 0, []
        for side, box in sides.items():
            for k in BOX:
                r, t = ref.get(f"{side}_{k}"), box.get(k)
                if r is None or t is None:
                    continue
                try:
                    r = int(float(r))
                except (TypeError, ValueError):
                    continue
                compared += 1
                if r == t:
                    equal += 1
                else:
                    worst = max(worst, abs(r - t))
                    differ.append(f"{side}_{k} ref {r} / tl {t}")
        return compared, equal, worst, differ

    compared, equal, worst, differ = compare({"w": tl[int(winner_side)], "l": tl[1 - int(winner_side)]})
    s_compared, s_equal, _, _ = compare({"w": tl[1 - int(winner_side)], "l": tl[int(winner_side)]})
    swapped = equal < compared and s_compared == compared and s_equal == compared
    return {"box_compared": compared > 0, "box_fields": compared, "box_fields_equal": equal,
            "box_all_equal": compared > 0 and equal == compared, "box_max_abs_diff": worst,
            "box_swapped": swapped,
            "box_differences": "the two players' box scores are exactly swapped" if swapped else ("; ".join(differ) or None)}


def tl_side(tl_names: list[str], name: str) -> int | None:
    """Which of TennisLive's two players (page order) is ``name``: shared name words, else near-identical words."""
    target = words(name)
    for agreement in (name_agreement, loose_agreement):
        hits = [i for i, n in enumerate(tl_names) if agreement(words(n), target)]
        if len(hits) == 1:
            return hits[0]
    return None


def verdict(official: list[int], info: dict) -> tuple[str, str | None, str | None]:
    """(verdict, completeness kind, short kind) of a fetched page."""
    if not info.get("points_listed"):
        return "no points", None, None
    record = info["record_games"]
    kind = completeness(official, record)
    if kind is None:
        return "no score to compare", None, None
    if kind in COMPLETE:
        return "complete", kind, None
    if kind == "short":
        sk = short_kind(official, record, info["last_after"])
        return ("only set-closing games missing" if sk == "set closers only" else "other shortfall"), kind, sk
    return "other shortfall (more games than the score)", kind, None


# ------------------------------------------------------------------------------------------ run
def wilson(k: int, n: int) -> list:
    if n == 0:
        return [None, None]
    z, p = 1.96, k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [round(mid - half, 3), round(mid + half, 3)]


def interleave(checks: pd.DataFrame) -> pd.DataFrame:
    """Round robin over the gaps, edition by edition, so an early stop still leaves every gap measured."""
    queues = []
    for _, g in checks.groupby("gap", sort=True):
        queues.append([r for _, r in g.sort_values(["stratum", "edition", "uid"]).iterrows()])
    order = []
    while any(queues):
        for q in queues:
            if q:
                order.append(q.pop(0))
    return pd.DataFrame(order)


def period(gap: str, year: int) -> str:
    if gap != "itf_detail":
        return str(year)
    return "2018" if year <= 2018 else "2019-21" if year <= 2021 else "2022-23" if year <= 2023 else "2024"


def run(args) -> int:
    P.configure_stdout()
    started = time.time()
    sample = pd.read_csv(OUT / "sample_matches.csv")
    checks = sample[sample["role"] == "check"].copy()
    if args.gaps:
        checks = checks[checks["gap"].isin(args.gaps.split(","))]
    refs = reference_scores(checks)
    checks = checks.join(refs.drop(columns=["uid"]))
    checks = interleave(checks)
    if args.limit:
        checks = checks.head(args.limit)
    receipts = C.Receipts(SOURCE, root=RAW)
    client = None if args.offline else StrictClient(min_interval=args.min_interval, jitter=args.jitter)
    site = Site(client, receipts, args.offline)
    resolver = Resolver(site)
    rows, stopped = [], None
    try:
        for n, (_, row) in enumerate(checks.iterrows(), 1):
            rec = {k: row[k] for k in ("gap", "stratum", "edition", "uid", "tour", "level", "draw", "year", "d",
                                       "name1", "name2", "tname", "creator", "ref_score", "ref_source", "ref_round",
                                       "ref_box_source")}
            hit = resolver.resolve(row)
            rec.update(found_via=hit["found_via"], listing_slug=hit.get("listing_slug"),
                       listing_year=hit.get("listing_year"), attempts=" || ".join(hit.get("attempts") or []))
            official = official_sets(rec["ref_score"]) if isinstance(rec["ref_score"], str) and rec["ref_score"] else []
            if hit["found_via"] not in ("not found", "not fetched"):
                rec.update(tl_url=hit["url"], tl_listed_names=" | ".join(str(x) for x in hit["names"]),
                           tl_listed_tournament=hit["tournament"], tl_listed_stage=hit["stage"],
                           tl_listed_start=hit["time"].strftime("%Y-%m-%d %H:%M") if hit.get("time") is not None else None,
                           tl_listed_state=hit["state"], tl_listed_games=" ".join(str(x) for x in hit.get("games") or []),
                           listed_score_agrees=hit.get("listed_score_agrees"))
                if hit["url"]:
                    status, html, _ = site.match_page(hit["url"])
                    rec["page_status"] = status
                    if html is not None:
                        info = inspect(html)
                        tl_official = official_sets(info["tl_score"]) if info.get("tl_score") else []
                        rec["score_source"] = "reference" if official else "tennislive"
                        use = official or tl_official
                        rec["score_games"] = " ".join(str(x) for x in use)
                        rec["tl_score_games"] = " ".join(str(x) for x in tl_official)
                        rec["score_agrees"] = (tl_official == official) if official and tl_official else None
                        v, kind, sk = verdict(use, info)
                        rec.update({k: info[k] for k in info if k not in ("record_games", "last_after", "tl_box")})
                        tl_names = (info.get("tl_names") or "").split(" | ")
                        side = info.get("tl_winner_side")
                        ref_winner = row.get("ref_winner")
                        winner_side = None                        # TennisLive's index of the reference winner
                        if len(tl_names) == 2 and pd.notna(ref_winner):
                            winner_name = row["name1"] if int(ref_winner) == 1 else row["name2"]
                            winner_side = tl_side(tl_names, winner_name)
                            if side is not None and winner_side is not None:
                                rec["winner_agrees"] = int(side) == winner_side
                        rec.update(box_compare(row.get("ref_box"), info["tl_box"], winner_side))
                        total = sum(use)
                        with_points = int(info.get("games_listed") or 0) - int(info.get("games_without_points") or 0)
                        rec.update(score_games_total=total, games_with_points=with_points,
                                   point_game_share=round(min(with_points, total) / total, 3) if total else None)
                        rec["games_by_set"] = " ".join(str(x) for x in info["record_games"])
                        rec["last_after_by_set"] = " ".join("" if x is None else str(x) for x in info["last_after"])
                        rec["pbp_available"] = bool(info.get("points_listed"))
                        rec.update(verdict=v, completeness=kind, short_kind=sk)
                    else:
                        rec.update(pbp_available=False, stats_available=False, verdict="no page")
                else:
                    rec.update(page_status="listed without a page", pbp_available=False, stats_available=False,
                               verdict="no page")
            else:
                rec.update(page_status=hit["found_via"], pbp_available=False, stats_available=False,
                           verdict=hit["found_via"])
            rec["score_games"] = rec.get("score_games") or " ".join(str(x) for x in official)
            rows.append(rec)
            P.log(f"[{n}/{len(checks)}] {rec['gap']} {rec['uid']} {rec['name1']} v {rec['name2']} ({rec['tname']} "
                  f"{rec['year']}): {rec['found_via']}; page {rec.get('page_status')}; {rec.get('verdict')}; "
                  f"requests={client.requests if client else 0}")
    except (P.Blocked, P.BudgetExhausted) as stop:
        stopped = f"{type(stop).__name__}: {stop}"
        P.log(f"STOPPED: {stopped}")
    frame = pd.DataFrame(rows)
    done = set(frame["uid"]) if len(frame) else set()
    if args.limit or args.gaps or stopped:          # keep earlier rows of matches this run did not reach
        path = OUT / "tennislive_matches.csv"
        if path.exists():
            old = pd.read_csv(path)
            frame = pd.concat([old[~old["uid"].isin(done)], frame], ignore_index=True)
    cols = ["gap", "stratum", "edition", "uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname",
            "found_via", "listing_slug", "listing_year", "tl_url", "tl_listed_names", "tl_listed_tournament",
            "tl_listed_stage", "tl_listed_start", "tl_listed_state", "tl_listed_games", "listed_score_agrees",
            "page_status", "pbp_available", "points_listed", "sets_listed", "games_listed", "games_by_set",
            "score_games", "score_games_total", "games_with_points", "point_game_share", "score_source", "ref_score",
            "ref_source",
            "ref_round", "tl_score", "tl_score_games", "score_agrees", "last_after_by_set", "games_without_points",
            "verdict", "completeness", "short_kind", "stats_available", "stats_rows", "stats_match_rows",
            "stats_periods", "stats_names", "ref_box_source", "box_compared", "box_fields", "box_fields_equal",
            "box_all_equal", "box_swapped",
            "box_max_abs_diff", "box_differences", "winner_agrees", "pbp_unavailable_notice",
            "stats_unavailable_notice", "tl_state", "tl_end_reason", "tl_best_of", "tl_date", "tl_round",
            "tl_tournament", "tl_names", "tl_winner_side", "creator", "attempts"]
    for c in cols:
        if c not in frame.columns:
            frame[c] = None
    frame = frame[cols].sort_values(["gap", "stratum", "edition", "uid"])
    frame.to_csv(OUT / "tennislive_matches.csv", index=False)
    summary = summarize(frame)
    runs_path = FOLDER / "_runs.jsonl"
    this_run = {"started_at": dt.datetime.fromtimestamp(started, dt.timezone.utc).isoformat(timespec="seconds"),
                "finished_at": C.utc_now_iso(), "seconds": round(time.time() - started, 1), "stopped": stopped,
                "client": client.stats() if client else "offline", "args": vars(args), "matches_processed": len(rows)}
    if client is not None:
        with runs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(this_run, default=str) + "\n")
    runs = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines() if line.strip()] \
        if runs_path.exists() else []
    summary["requests"] = request_summary()
    summary["exploration"] = EXPLORATION
    summary["runs"] = runs
    summary["this_run"] = this_run
    summary["generated_at"] = C.utc_now_iso()
    (OUT / "tennislive_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    P.log(json.dumps(summary["by_gap"], indent=1, default=str))
    return 1 if stopped else 0


def request_summary() -> dict:
    """Every request of the lane, from the ledger: counts by kind and status, first and last access time."""
    if not LEDGER.exists():
        return {"total": 0}
    lines = [json.loads(line) for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"total": len(lines), "budget": BUDGET,
            "by_kind_status": dict(sorted(Counter(f"{request_kind(x['url'])}|{x['status']}" for x in lines).items())),
            "refusals": [x for x in lines if x["status"] in (403, 429) or (x.get("note") or "").startswith("challenge")],
            "first_at": lines[0]["at"] if lines else None, "last_at": lines[-1]["at"] if lines else None}


def summarize(frame: pd.DataFrame) -> dict:
    out = {"definitions": {
        "checked": "check rows of sample_matches.csv processed",
        "page_found": "a TennisLive match page answered HTTP 200 for the match",
        "with_points": "the page lists at least one point state",
        "complete": "games per set equal the final score's (verify_scrape.completeness: exact, a retirement's "
                    "unfinished game listed, or a match tiebreak as one game)",
        "only_set_closing_missing": "short, and every missing game is the one that closed its set",
        "other_shortfall": "short in some other way (or longer than the score)",
        "all_points_complete": "complete, and no listed game lacks its points",
        "games_with_points_share": "games listed with their points / games in the final score, per record "
                                   "(share_games_with_points_90: records at 90% or more, over all checked)",
        "with_statistics": "the page carries the match statistics block (8 match-level rows on every page seen)",
        "box_score_check": "the statistics block as a box score (aces, double faults, serve points, first serves "
                           "in, first- and second-serve points won, break points faced and saved; both players) "
                           "against the reference row's box score; 'players_swapped': the two players' values "
                           "are exactly exchanged",
        "winner_agrees": "the page's winner is the reference winner", "score_agrees_with_reference":
            "the page's final score has the reference score's games per set"}, "by_gap": {}, "by_stratum": {},
        "itf_by_tour_period": {}, "itf_by_tour_year": {}}
    if frame.empty:
        return out

    def cell(g: pd.DataFrame) -> dict:
        n = len(g)
        found = g["page_status"].astype(str).eq("200")
        pts = g["pbp_available"].astype(str).str.lower().eq("true")
        v = g["verdict"].astype(str)
        comp = v.eq("complete")
        closers = v.eq("only set-closing games missing")
        other = v.str.startswith("other shortfall")
        allpts = comp & pd.to_numeric(g["games_without_points"], errors="coerce").fillna(0).eq(0)
        stats = g["stats_available"].astype(str).str.lower().eq("true")
        counts = {"checked": n, "page_found": int(found.sum()), "with_points": int(pts.sum()),
                  "complete": int(comp.sum()), "only_set_closing_missing": int(closers.sum()),
                  "other_shortfall": int(other.sum()), "no_points_on_page": int((found & ~pts).sum()),
                  "all_points_complete": int(allpts.sum()), "with_statistics": int(stats.sum()),
                  "not_found": int(g["found_via"].astype(str).eq("not found").sum()),
                  "not_fetched": int(g["found_via"].astype(str).eq("not fetched").sum()),
                  "page_not_200": int((~found & ~g["found_via"].astype(str).isin(["not found", "not fetched"])).sum())}
        for k in ("page_found", "with_points", "complete", "all_points_complete", "with_statistics"):
            counts[f"share_{k}"] = [round(counts[k] / n, 3) if n else None, wilson(counts[k], n)]
        pf = counts["page_found"]
        counts["of_pages_with_points"] = [round(counts["with_points"] / pf, 3) if pf else None, wilson(counts["with_points"], pf)]
        wp = counts["with_points"]
        counts["of_point_records_complete"] = [round(counts["complete"] / wp, 3) if wp else None, wilson(counts["complete"], wp)]
        share = pd.to_numeric(g["point_game_share"], errors="coerce")
        counts["games_with_points_share"] = {
            "records": int(share.notna().sum()), "median": round(float(share.median()), 3) if share.notna().any() else None,
            "at_least_90pct": int(share.ge(0.9).sum()), "at_least_75pct": int(share.ge(0.75).sum()),
            "below_50pct": int(share.lt(0.5).sum()), "zero": int(share.eq(0).sum())}
        counts["share_games_with_points_90"] = [round(int(share.ge(0.9).sum()) / n, 3) if n else None,
                                                wilson(int(share.ge(0.9).sum()), n)]
        counts["found_via"] = dict(Counter(g["found_via"].astype(str)))
        bc = g[g["box_compared"].astype(str).str.lower().eq("true")]
        fields = pd.to_numeric(bc["box_fields"], errors="coerce").sum()
        counts["box_score_check"] = {
            "matches_compared": int(len(bc)),
            "all_fields_equal": int(bc["box_all_equal"].astype(str).str.lower().eq("true").sum()),
            "players_swapped": int(bc["box_swapped"].astype(str).str.lower().eq("true").sum()),
            "fields_compared": int(fields),
            "fields_equal": int(pd.to_numeric(bc["box_fields_equal"], errors="coerce").sum()),
            "max_abs_diff": int(pd.to_numeric(bc["box_max_abs_diff"], errors="coerce").max()) if len(bc) else None}
        wa = g["winner_agrees"].dropna().astype(str).str.lower()
        counts["winner_agrees"] = {"compared": int(len(wa)), "agree": int(wa.eq("true").sum())}
        sa = g["score_agrees"].dropna().astype(str).str.lower()
        counts["score_agrees_with_reference"] = {"compared": int(len(sa)), "agree": int(sa.isin(["true", "1.0"]).sum())}
        return counts

    for gap, g in frame.groupby("gap"):
        out["by_gap"][gap] = cell(g)
        out["by_gap"][gap]["weighted_to_gap"] = weighted(g)
        out["by_gap"][gap]["editions"] = edition_view(g)
    for (gap, stratum), g in frame.groupby(["gap", "stratum"]):
        out["by_stratum"][f"{gap}|{stratum}"] = cell(g)
    itf = frame[frame["gap"].eq("itf_detail")]
    for (tour, per), g in itf.groupby([itf["tour"], itf["year"].astype(int).map(lambda y: period("itf_detail", y))]):
        out["itf_by_tour_period"][f"{tour}|{per}"] = cell(g)
        out["itf_by_tour_period"][f"{tour}|{per}"]["weighted_to_gap"] = weighted(g)
        out["itf_by_tour_period"][f"{tour}|{per}"]["editions"] = edition_view(g)
    for (tour, year), g in itf.groupby(["tour", "year"]):
        out["itf_by_tour_year"][f"{tour}|{year}"] = cell(g)
    for tour, g in itf.groupby("tour"):
        out["itf_by_tour_period"][f"{tour}|all"] = cell(g)
        out["itf_by_tour_period"][f"{tour}|all"]["weighted_to_gap"] = weighted(g)
        out["itf_by_tour_period"][f"{tour}|all"]["editions"] = edition_view(g)
    out["all"] = cell(frame)
    out["notes_on_intervals"] = (
        "Wilson 95% intervals treat the checked matches as independent draws. They are not: matches come in "
        "clusters of 2-4 per drawn edition, and coverage tends to be shared by a tournament's matches, so the "
        "intervals are too narrow; 'editions' shows how the outcome falls by edition. 'weighted_to_gap' weights "
        "each stratum by its number of gap matches (sample_editions.csv), which the raw shares do not.")
    return out


FLAGS = {"page_found": lambda g: g["page_status"].astype(str).eq("200"),
         "with_points": lambda g: g["pbp_available"].astype(str).str.lower().eq("true"),
         "complete": lambda g: g["verdict"].astype(str).eq("complete"),
         "only_set_closing_missing": lambda g: g["verdict"].astype(str).eq("only set-closing games missing"),
         "games_with_points_90": lambda g: pd.to_numeric(g["point_game_share"], errors="coerce").ge(0.9),
         "with_statistics": lambda g: g["stats_available"].astype(str).str.lower().eq("true")}


def weighted(g: pd.DataFrame) -> dict:
    """Shares with each stratum weighted by its gap matches (within-stratum shares are about self-weighting:
    editions were drawn proportional to size and a fixed number of matches taken in each)."""
    editions = pd.read_csv(OUT / "sample_editions.csv")
    sizes = editions.drop_duplicates(["gap", "stratum"]).set_index(["gap", "stratum"])["stratum_gap_matches"]
    total, acc = 0.0, Counter()
    for (gap, stratum), s in g.groupby(["gap", "stratum"]):
        n_s = float(sizes.get((gap, stratum), 0))
        total += n_s
        for k, f in FLAGS.items():
            acc[k] += n_s * float(f(s).mean())
    return {k: round(acc[k] / total, 3) if total else None for k in FLAGS} | {"gap_matches_represented": int(total)}


def edition_view(g: pd.DataFrame) -> dict:
    """Per drawn edition: were all, some or none of its checked matches found / with points / complete?"""
    out = {"editions": int(g["edition"].nunique())}
    for k in ("page_found", "with_points", "complete"):
        per = FLAGS[k](g).groupby(g["edition"]).agg(["sum", "size"])
        out[k] = {"all": int((per["sum"] == per["size"]).sum()),
                  "some": int(((per["sum"] > 0) & (per["sum"] < per["size"])).sum()),
                  "none": int((per["sum"] == 0).sum())}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gaps", help="comma list of gap ids (default: every gap in the sample)")
    parser.add_argument("--limit", type=int, help="only the first N matches of the interleaved order (dry runs)")
    parser.add_argument("--min-interval", type=float, default=2.0, help="seconds between requests (plus jitter)")
    parser.add_argument("--jitter", type=float, default=1.0)
    parser.add_argument("--offline", action="store_true", help="no HTTP: rebuild the tables from cached answers")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
