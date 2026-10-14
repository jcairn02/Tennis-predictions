"""Pinnacle's current tennis lines: the recorder of the decided live price.

The model's odds input at bet time is Pinnacle's current line with the margin removed proportionally (BetOnline's
while Pinnacle has none), at every venue (docs/decisions/2026-10-09-pinnacle-first-odds-input.md). Pinnacle's own
website reads a public guest API; this adapter makes the same three GETs (probed on 9 Oct 2026,
data/raw/pinnacle/probe/):

    GET https://www.pinnacle.com/config/app.json                         the site's public configuration; the guest
                                                                        API's key is its api.haywire.apiKey
    GET https://guest.api.arcadia.pinnacle.com/0.1/sports/33/matchups?withSpecials=false
                                                                        every listed tennis matchup: league ("ATP Shanghai
                                                                        - R2"), participants (home/away), start time,
                                                                        live status; "(Games)" children are alternates
    GET https://guest.api.arcadia.pinnacle.com/0.1/sports/33/markets/straight?primaryOnly=true
                                                                        the main markets; the match moneyline is
                                                                        type "moneyline", period 0, on the top-level matchup

Each pull is one key fetch and two listing fetches, paced (PAUSE seconds plus jitter); a pull less than MIN_INTERVAL
seconds after the last one is not made (the last one is used). The bodies are kept gzipped as
data/raw/pinnacle/<YYYY-MM-DD>/<HHMMSSZ>_{matchups,straight}.json.gz, with one receipt per request in
data/raw/pinnacle/_receipts.jsonl. Each pull's match moneylines are staged to their own file,
data/dump/odds/pinnacle/pulls/<YYYY-MM-DD>/<HHMMSSZ>.parquet (one row per matchup): a price history from the first
pull on, with no shared file rewritten.

Only pre-match prices are staged as usable: a live (in-play) matchup's moneyline sits on a live "Sets" child and is
kept out, as are alternates, closed markets, markets whose cutoff or start is not after the pull, specials and
doubles. A non-200 answer, a body that is not JSON (a challenge page) or a key that cannot be found stops the pull
(Stop) and the receipts say why: back off and report, never retry in a loop
(docs/decisions/2026-10-08-scraping-approved.md). No login, no CAPTCHA.

    ./python.sh -m src.ingest.pinnacle                one pull now (or the last one, if under a minute old)
    ./python.sh -m src.ingest.pinnacle --stage-only   restage every pull's file from the raw copies
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import random
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingest.public_dump import common as C  # noqa: E402

SOURCE = "pinnacle"
RAW = C.PROJECT_ROOT / "data" / "raw" / SOURCE
DUMP = C.DUMP_ROOT / "odds" / SOURCE
PULLS = DUMP / "pulls"
MIN_INTERVAL = 60    # seconds: a pull sooner than this after the last one reuses the last one
CONFIG_URL = "https://www.pinnacle.com/config/app.json"
API = "https://guest.api.arcadia.pinnacle.com/0.1"
MATCHUPS_URL = f"{API}/sports/33/matchups?withSpecials=false"
STRAIGHT_URL = f"{API}/sports/33/markets/straight?primaryOnly=true"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) tennis-predictions/1.0 (research use; python-requests)"
PAUSE = 2.0          # seconds between requests, plus up to one second of jitter
LEAGUE = re.compile(r"^(?P<tour>ATP|WTA|ITF)\s+(?P<rest>.+?)(?:\s+-\s+(?P<phase>[^-]+))?$")


class Stop(RuntimeError):
    """An answer that must end the pull: a block, a challenge page, a missing key."""


# --------------------------------------------------------------------------------------
# the pull
# --------------------------------------------------------------------------------------
class Client:
    def __init__(self, receipts: C.Receipts):
        self.sess = requests.Session()
        self.sess.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json",
                                  "Referer": "https://www.pinnacle.com/", "Origin": "https://www.pinnacle.com"})
        self.receipts = receipts
        self._last = 0.0
        self.sent = 0

    def get(self, name: str, url: str, dest: Path | None, headers: dict | None = None) -> object:
        wait = self._last + PAUSE + random.random() - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        receipt = {"name": name, "url": url, "retrieved_at": C.utc_now_iso(), "dest": C.rel(dest) if dest else None}
        try:
            r = self.sess.get(url, headers=headers or {}, timeout=60, allow_redirects=False)
        except requests.RequestException as err:
            self.receipts.record({**receipt, "error": f"{type(err).__name__}: {err}"})
            raise Stop(f"{name}: {type(err).__name__}: {err}") from err
        finally:
            self._last = time.monotonic()
            self.sent += 1
        body = r.content
        receipt.update(status=r.status_code, content_type=r.headers.get("Content-Type"), bytes=len(body),
                       sha256=C.sha256_bytes(body))
        if r.status_code != 200:
            self.receipts.record({**receipt, "error": f"HTTP {r.status_code}"})
            raise Stop(f"{name}: HTTP {r.status_code} (a block or a changed API: stopped, not retried)")
        try:
            doc = json.loads(body)
        except ValueError:
            self.receipts.record({**receipt, "error": "body is not JSON (a challenge page?)"})
            raise Stop(f"{name}: the answer is not JSON (a challenge page?): stopped") from None
        if dest is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            C.write_atomic(dest, gzip.compress(body))
        self.receipts.record(receipt)
        return doc


def api_key(config: dict) -> str:
    key = (((config.get("api") or {}).get("haywire") or {}).get("apiKey"))
    if not isinstance(key, str) or len(key) < 16:
        raise Stop("the site's configuration names no guest API key (api.haywire.apiKey): the site changed")
    return key


def pull(now: dt.datetime | None = None) -> dict:
    """One pull: the key, the matchups and the main markets; raw copies kept; returns the stamp and the two bodies."""
    now = now or dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%H%M%SZ")
    day = RAW / now.strftime("%Y-%m-%d")
    receipts = C.Receipts(SOURCE, root=RAW.parent)
    client = Client(receipts)
    key = api_key(client.get("config", CONFIG_URL, None))
    headers = {"X-API-Key": key}
    matchups = client.get(f"matchups_{now:%Y%m%d}_{stamp}", MATCHUPS_URL, day / f"{stamp}_matchups.json.gz", headers)
    straight = client.get(f"straight_{now:%Y%m%d}_{stamp}", STRAIGHT_URL, day / f"{stamp}_straight.json.gz", headers)
    if not isinstance(matchups, list) or not isinstance(straight, list):
        raise Stop("an answer is not a list: the API changed")
    return {"retrieved_at": now.isoformat(timespec="seconds"), "matchups": matchups, "straight": straight,
            "files": [C.rel(day / f"{stamp}_matchups.json.gz"), C.rel(day / f"{stamp}_straight.json.gz")],
            "requests": client.sent}


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def decimal_from_american(price) -> float:
    p = float(price)
    if p >= 100:
        return 1.0 + p / 100.0
    if p <= -100:
        return 1.0 + 100.0 / -p
    return float("nan")                       # American prices lie outside (-100, 100)


def parse_league(name: str) -> dict:
    """'ATP Shanghai - R2' -> tour atp, event 'Shanghai', phase 'R2', level 'tour'; Challenger, 125, ITF, doubles,
    qualifying flagged."""
    m = LEAGUE.match(str(name).strip())
    if not m:
        return {"tour": None, "event": str(name), "phase": None, "level": "other", "doubles": "doubles" in str(name).lower()}
    tour, rest, phase = m.group("tour"), m.group("rest").strip(), (m.group("phase") or "").strip() or None
    low = f"{rest} {phase or ''}".lower()
    level = "tour"
    if tour == "ITF" or rest.lower().startswith(("men ", "women ")):
        level = "itf"
    elif "challenger" in low:
        level = "challenger"
    elif re.search(r"\b125k?\b", low):
        level = "125"
    event = re.sub(r"^(Challenger|125k?)\s+", "", rest, flags=re.I).strip()
    qual = bool(phase and re.match(r"^(q|qual|qualifying|qualifiers?)\b", phase, flags=re.I)) or "qualif" in low
    return {"tour": tour.lower(), "event": event, "phase": phase, "level": level, "doubles": "doubles" in low,
            "qualifying": qual}


def stage_pull(doc: dict) -> pd.DataFrame:
    """The match moneylines of one pull: one row per top-level matchup with an open period-0 moneyline."""
    by_id = {m["id"]: m for m in doc["matchups"] if isinstance(m, dict) and "id" in m}
    rows = []
    for mk in doc["straight"]:
        if mk.get("type") != "moneyline" or mk.get("period") != 0:
            continue
        mu = by_id.get(mk.get("matchupId"))
        prices = {p.get("designation"): p.get("price") for p in mk.get("prices", []) if isinstance(p, dict)}
        reason = None
        pulled = pd.Timestamp(doc["retrieved_at"])
        if mu is None:
            reason = "no matchup listed (a special?)"
        elif mu.get("parentId") is not None or mu.get("isLive"):
            reason = "in-play (live) market"
        elif mu.get("status") not in (None, "pending"):
            reason = f"matchup {mu.get('status')}"
        elif mk.get("isAlternate"):
            reason = "alternate market"
        elif mk.get("status") != "open":
            reason = f"market {mk.get('status')}"
        elif set(prices) != {"home", "away"}:
            reason = "not exactly a home and an away price"
        elif not mk.get("cutoffAt") or pd.Timestamp(mk["cutoffAt"]) <= pulled:
            reason = "market cutoff not after the pull"
        elif not mu.get("startTime") or pd.Timestamp(mu["startTime"]) <= pulled:
            reason = "start not after the pull"
        if mu is None:
            continue
        lg = parse_league((mu.get("league") or {}).get("name", ""))
        parts = {p.get("alignment"): p.get("name") for p in mu.get("participants", []) if isinstance(p, dict)}
        if reason is None and (lg["doubles"] or any("/" in str(n) for n in parts.values())):
            reason = "doubles"
        d_home, d_away = (decimal_from_american(prices[s]) if s in prices else float("nan") for s in ("home", "away"))
        over = 1 / d_home + 1 / d_away if d_home == d_home and d_away == d_away else float("nan")
        limit = next((x.get("amount") for x in mk.get("limits", []) if x.get("type") == "maxRiskStake"), None)
        rows.append({
            "retrieved_at": doc["retrieved_at"], "matchup_id": int(mu["id"]), "league": (mu.get("league") or {}).get("name"),
            "league_id": (mu.get("league") or {}).get("id"), "tour": lg["tour"], "event": lg["event"], "phase": lg["phase"],
            "level": lg["level"], "qualifying": bool(lg.get("qualifying")), "best_of": (mu.get("league") or {}).get("bestOfX"),
            "start_utc": mu.get("startTime"), "status": mu.get("status"), "is_live": bool(mu.get("isLive")),
            "home": parts.get("home"), "away": parts.get("away"),
            "price_home": prices.get("home"), "price_away": prices.get("away"),
            "decimal_home": d_home, "decimal_away": d_away, "overround": over,
            "p_home": (1 / d_home) / over if over == over else float("nan"),
            "max_risk_stake": limit, "cutoff_at": mk.get("cutoffAt"), "market_version": mk.get("version"),
            "usable": reason is None, "reason": reason})
    return pd.DataFrame(rows)


def pull_path(retrieved_at: str) -> Path:
    t = pd.Timestamp(retrieved_at).tz_convert("UTC")
    return PULLS / t.strftime("%Y-%m-%d") / f"{t.strftime('%H%M%SZ')}.parquet"


def save_pull(rows: pd.DataFrame, retrieved_at: str) -> Path:
    path = pull_path(retrieved_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    rows.to_parquet(tmp, index=False)
    tmp.replace(path)
    return path


def latest_path() -> Path | None:
    files = sorted(PULLS.glob("20*/*.parquet"))
    return files[-1] if files else None


def record(force: bool = False) -> pd.DataFrame:
    """One pull, staged to its own file. Returns this pull's rows (every match moneyline, usable or not, with the
    reason). Within MIN_INTERVAL seconds of the last pull, the last pull is returned instead (force=False)."""
    last = latest_path()
    if last is not None and not force:
        when = dt.datetime.strptime(f"{last.parent.name} {last.stem}", "%Y-%m-%d %H%M%SZ").replace(tzinfo=dt.timezone.utc)
        age = (dt.datetime.now(dt.timezone.utc) - when).total_seconds()
        if age < MIN_INTERVAL:
            C.log(f"[{SOURCE}] the last pull is {age:.0f} s old: reused, nothing sent")
            return pd.read_parquet(last)
    doc = pull()
    rows = stage_pull(doc)
    path = save_pull(rows, doc["retrieved_at"])
    usable = int(rows["usable"].sum()) if len(rows) else 0
    C.log(f"[{SOURCE}] {doc['requests']} requests; {len(rows)} match moneylines, {usable} usable pre-match; "
          f"staged {C.rel(path)}")
    return rows


def restage() -> int:
    """Restage every raw pull kept, each to its own file."""
    n = 0
    for m in sorted(RAW.glob("20*/*_matchups.json.gz")):
        s = m.with_name(m.name.replace("_matchups", "_straight"))
        if not s.exists():
            continue
        day = m.parent.name
        t = m.name.split("_")[0]
        when = dt.datetime.strptime(f"{day} {t}", "%Y-%m-%d %H%M%SZ").replace(tzinfo=dt.timezone.utc)
        doc = {"retrieved_at": when.isoformat(timespec="seconds"),
               "matchups": json.loads(gzip.decompress(m.read_bytes())),
               "straight": json.loads(gzip.decompress(s.read_bytes()))}
        save_pull(stage_pull(doc), doc["retrieved_at"])
        n += 1
    return n


def latest_pull() -> pd.DataFrame:
    """The rows of the most recent pull (empty if none)."""
    path = latest_path()
    return pd.read_parquet(path) if path is not None else pd.DataFrame()


def history(days: int = 7) -> pd.DataFrame:
    """Every pull of the last `days` days, one row per matchup per pull: the recorded price history."""
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).strftime("%Y-%m-%d")
    files = [f for f in sorted(PULLS.glob("20*/*.parquet")) if f.parent.name >= since]
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage-only", action="store_true", help="no HTTP: restage every pull from the raw copies")
    ap.add_argument("--force", action="store_true", help=f"pull even within {MIN_INTERVAL} s of the last pull")
    a = ap.parse_args()
    if a.stage_only:
        C.log(f"[{SOURCE}] restaged {restage()} pulls")
        return 0
    try:
        rows = record(force=a.force)
    except Stop as err:
        C.log(f"[{SOURCE}] STOPPED: {err}")
        return 2
    show = rows[rows["usable"]] if len(rows) else rows
    if len(show):
        print(show[["league", "start_utc", "home", "away", "price_home", "price_away", "p_home"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
