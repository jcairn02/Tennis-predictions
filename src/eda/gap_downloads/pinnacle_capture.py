"""Work package P11's forward-capture test, route (A): Pinnacle's tennis listing polled at a fixed cadence, each
matchup's last price before its start kept as its close (docs/studies/gap_downloads/collection-plan.md, P11).

The pull is the bet-day recorder's (src/ingest/pinnacle.py: its client, key lookup and staging), written to its own
folders so that the bet-day path, which reads only the newest file of data/dump/odds/pinnacle/pulls/, never meets a
capture pull in the middle of a run:
    raw      data/raw/pinnacle_capture/<YYYY-MM-DD>/<HHMMSSZ>_{matchups,straight}.json.gz, receipts in _receipts.jsonl
    staged   data/dump/odds/pinnacle_capture/pulls/<YYYY-MM-DD>/<HHMMSSZ>.parquet (one row per matchup and pull)
The site's key is read once an hour (two requests a pull, three when the key is read). A cycle is skipped while a
bet-day pull (src.ingest.pinnacle) runs: one collector per host (the plan's shared rule 3). A refusal (any non-200
answer, a body that is not JSON) ends the loop: back off and report (docs/decisions/2026-10-08-scraping-approved.md).

    ./python.sh src/eda/gap_downloads/pinnacle_capture.py --every 600 --hours 36       the loop (run detached)
    ./python.sh src/eda/gap_downloads/pinnacle_capture.py --closes                    offline: each matchup's close
    ./python.sh src/eda/gap_downloads/pinnacle_capture.py --ready     offline: can the comparison run on full data?
                                                                      exit 0 yes, 1 not yet, 3 already done
    ./python.sh src/eda/gap_downloads/pinnacle_capture.py --compare   offline: route (B), TennisExplorer's record of
                                                                      the same matches; "complete" when --ready holds
The daily task's job lower_odds (src/ingest/scheduled.py) runs --ready each day and reminds the owner, weekly, until a
complete comparison is on disk (the owner's request of 22 Oct 2026).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest import pinnacle as PN                    # noqa: E402
from src.ingest.public_dump import common as C          # noqa: E402

SOURCE = "pinnacle_capture"
RAW = C.PROJECT_ROOT / "data" / "raw" / SOURCE
DUMP = C.DUMP_ROOT / "odds" / SOURCE
PULLS = DUMP / "pulls"
STUDY = C.PROJECT_ROOT / "data" / "studies" / "gap_downloads"
KEY_TTL = 3600          # seconds a key read from the site's configuration is reused
LOWER = ("itf", "challenger", "125")


def bet_day_pull_running() -> int | None:
    """The pid of a running bet-day pull (python -m src.ingest.pinnacle), or None."""
    try:
        import psutil
    except ImportError:
        return None
    me = psutil.Process().pid
    for p in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = p.info["cmdline"] or []
            if p.info["pid"] != me and "python" in (p.info["name"] or "").lower() and "src.ingest.pinnacle" in cmd:
                return p.info["pid"]
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


class Capture:
    def __init__(self):
        self.receipts = C.Receipts(SOURCE, root=RAW.parent)
        self.client = PN.Client(self.receipts)
        self.key, self.key_at = None, 0.0

    def pull(self, now: dt.datetime | None = None) -> pd.DataFrame:
        now = now or dt.datetime.now(dt.timezone.utc)
        if self.key is None or time.monotonic() - self.key_at > KEY_TTL:
            self.key = PN.api_key(self.client.get("config", PN.CONFIG_URL, None))
            self.key_at = time.monotonic()
        stamp, day = now.strftime("%H%M%SZ"), RAW / now.strftime("%Y-%m-%d")
        headers = {"X-API-Key": self.key}
        matchups = self.client.get(f"matchups_{now:%Y%m%d}_{stamp}", PN.MATCHUPS_URL, day / f"{stamp}_matchups.json.gz",
                                   headers)
        straight = self.client.get(f"straight_{now:%Y%m%d}_{stamp}", PN.STRAIGHT_URL, day / f"{stamp}_straight.json.gz",
                                   headers)
        if not isinstance(matchups, list) or not isinstance(straight, list):
            raise PN.Stop("an answer is not a list: the API changed")
        doc = {"retrieved_at": now.isoformat(timespec="seconds"), "matchups": matchups, "straight": straight}
        rows = PN.stage_pull(doc)
        path = PULLS / now.strftime("%Y-%m-%d") / f"{stamp}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        rows.to_parquet(tmp, index=False)
        tmp.replace(path)
        return rows


def loop(every: int, hours: float) -> dict:
    cap = Capture()
    end = time.monotonic() + hours * 3600
    out = {"started_at": C.utc_now_iso(), "every": every, "hours": hours, "pulls": 0, "skipped": 0, "stopped": None}
    while time.monotonic() < end:
        t0 = time.monotonic()
        busy = bet_day_pull_running()
        if busy:
            out["skipped"] += 1
            C.log(f"[{SOURCE}] {C.utc_now_iso()} a bet-day pull is running (pid {busy}): this cycle skipped")
        else:
            try:
                rows = cap.pull()
                out["pulls"] += 1
                low = rows[rows.level.isin(LOWER)] if len(rows) else rows
                C.log(f"[{SOURCE}] {C.utc_now_iso()} pull {out['pulls']}: {len(rows)} moneylines, lower levels "
                      f"{len(low)} ({int(low.usable.sum()) if len(low) else 0} usable); requests {cap.client.sent}")
            except PN.Stop as err:
                out["stopped"] = str(err)
                C.log(f"[{SOURCE}] STOPPED: {err}")
                break
        time.sleep(max(1.0, every - (time.monotonic() - t0)))
    out.update(finished_at=C.utc_now_iso(), requests=cap.client.sent)
    return out


# --------------------------------------------------------------------------------------------------------------------
# offline: each matchup's close
# --------------------------------------------------------------------------------------------------------------------
def pulls(root: Path = PULLS) -> pd.DataFrame:
    files = sorted(root.glob("20*/*.parquet"))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True) if files else pd.DataFrame()


def closes(df: pd.DataFrame) -> pd.DataFrame:
    """One row per matchup: the last usable pre-start pull (its price is the captured close), the first one (the
    earliest price seen), how many pulls listed it, the listed start (the last pull's) and whether it changed, the
    last pull listing it at all and whether it was seen in play."""
    if df.empty:
        return df
    df = df.copy()
    df["t"] = pd.to_datetime(df.retrieved_at, utc=True)
    df["start"] = pd.to_datetime(df.start_utc, utc=True)
    u = df[df.usable].sort_values("t")
    g = u.groupby("matchup_id")
    first, last = g.head(1).set_index("matchup_id"), g.tail(1).set_index("matchup_id")
    seen = df.groupby("matchup_id").agg(last_seen=("t", "max"), live_seen=("is_live", "max"),
                                        starts=("start", "nunique"), final_start=("start", "last"))
    out = last[["league", "tour", "event", "phase", "level", "qualifying", "home", "away", "price_home", "price_away",
                "decimal_home", "decimal_away", "p_home", "overround", "t"]].rename(columns={"t": "close_pull"})
    out["open_pull"] = first["t"]
    out["open_p_home"] = first["p_home"]
    out["n_pulls"] = g.size()
    out = out.join(seen)
    out["close_min_before_start"] = (out.final_start - out.close_pull).dt.total_seconds() / 60
    return out.reset_index()


def te_pages(days: list | None = None) -> pd.DataFrame:
    """TennisExplorer's lower-level match pages of the given days, read from the collector's raw folder
    (src/ingest/tennisexplorer_lower.py; no staging needed): one row per match on disk with its names, listed start and
    Pinnacle's two last prices with their last change and the opening's time."""
    import datetime as dt
    from src.ingest import tennisexplorer as T
    from src.ingest import tennisexplorer_lower as L
    rows = []
    for day in days or []:
        day = day if isinstance(day, dt.date) else dt.date.fromisoformat(str(day))
        for tour in L.TYPES:
            dp = L.day_path(tour, day)
            if not dp.exists():
                continue
            for r in L.day_rows(T.read_raw(dp), day, tour):
                mp = L.match_path(r["te_id"])
                if not mp.exists():
                    continue
                d = T.parse_match(T.read_raw(mp))
                o, _ = L.book_rows(r["te_id"], d)
                pin = next((x for x in o if x["book"] == "Pinnacle"), {})
                rows.append({"te_id": r["te_id"], "day": day.isoformat(), "event": d.get("event"), "round": d.get("round"),
                             "p1": d.get("p1"), "p2": d.get("p2"), "start_utc": d.get("start_utc"),
                             **{k: v for k, v in pin.items() if k.startswith("k")}})
    return pd.DataFrame(rows).drop_duplicates("te_id") if rows else pd.DataFrame()


def compare(caps: pd.DataFrame, te: pd.DataFrame) -> pd.DataFrame:
    """Each captured lower-level matchup against TennisExplorer's page of the same match: both players' name words the
    same (either order), the site's listed start within a day of Pinnacle's. Per match: linked, the site shows
    Pinnacle, the site's last Pinnacle prices equal the captured close (both sides within 0.005 and within 0.01, after
    orienting the sides), minutes from the site's last Pinnacle change to the listed start, and from the captured
    close's pull to it. No price is returned."""
    from src.ingest import tennisexplorer as T
    caps = caps[caps.level.isin(LOWER)].copy()
    if te.empty:
        te = pd.DataFrame(columns=["te_id", "p1", "p2", "start_utc", "k1_last", "k2_last", "k1_last_t", "k2_last_t"])
    te = te.copy()
    te["t1"], te["t2"] = te.p1.map(T.name_tokens), te.p2.map(T.name_tokens)
    te["start"] = pd.to_datetime(te.start_utc, utc=True, errors="coerce")
    rows = []
    for c in caps.itertuples():
        h, a = T.name_tokens(c.home), T.name_tokens(c.away)
        w = te[(te.start - c.final_start).abs() <= pd.Timedelta(days=1)]
        hits = [(x, False) for x in w.itertuples() if T._same_tokens(x.t1, h) and T._same_tokens(x.t2, a)] + \
               [(x, True) for x in w.itertuples() if T._same_tokens(x.t1, a) and T._same_tokens(x.t2, h)]
        row = {"matchup_id": c.matchup_id, "level": c.level, "qualifying": c.qualifying,
               "start_utc": c.final_start.isoformat() if not pd.isna(c.final_start) else None,
               "close_min_before_start": c.close_min_before_start, "linked": len(hits) == 1,
               "candidates": len(hits)}
        if len(hits) == 1:
            x, flip = hits[0]
            hk, ak = ("k2", "k1") if flip else ("k1", "k2")
            last_h, last_a = getattr(x, f"{hk}_last", None), getattr(x, f"{ak}_last", None)
            has_pin = last_h is not None and not pd.isna(last_h)
            row["te_pinnacle"] = bool(has_pin)
            if has_pin:
                dh, da = abs(float(last_h) - c.decimal_home), abs(float(last_a) - c.decimal_away)
                row.update(same_005=bool(dh <= 0.005 and da <= 0.005), same_01=bool(dh <= 0.01 and da <= 0.01))
                lt = [pd.Timestamp(t) for t in (getattr(x, "k1_last_t", None), getattr(x, "k2_last_t", None))
                      if isinstance(t, str) and t]
                if lt and not pd.isna(x.start):
                    row["te_last_change_min_before_start"] = (x.start - max(lt)).total_seconds() / 60
        rows.append(row)
    return pd.DataFrame(rows)


COMPARE_JSON = STUDY / "pinnacle_capture_compare.json"
CAPTURE_RUNS = STUDY / "pinnacle_capture_runs.jsonl"
PAGES_SHARE = 0.95       # a day counts as fetched when this share of its in-scope priced matches have their page
CAPTURE_IDLE = 2 * 3600  # seconds since the newest pull after which a capture that wrote no end line counts as over


def started_days(df: pd.DataFrame) -> list[dt.date]:
    """The UTC days of the captured lower-level matchups that started before the last pull."""
    if df.empty:
        return []
    caps = closes(df)
    last_pull = pd.to_datetime(df.retrieved_at, utc=True).max()
    caps = caps[caps.level.isin(LOWER) & (caps.final_start < last_pull)]
    return sorted({t.date() for t in caps.final_start.dropna()})


def te_day_fetched(day: dt.date, today: dt.date | None = None) -> dict:
    """Whether TennisExplorer's results pages of a day are on disk (both tours) and the page of nearly every in-scope
    priced match they list (src/ingest/tennisexplorer_lower.py's folders; no request)."""
    from src.ingest import tennisexplorer as T
    from src.ingest import tennisexplorer_lower as L
    today = today or dt.datetime.now(dt.timezone.utc).date()
    types = L.calendar_types(None, {day.year, day.year - 1}, today)
    have_days, listed, pages = True, 0, 0
    for tour in L.TYPES:
        dp = L.day_path(tour, day)
        if not dp.exists():
            have_days = False
            continue
        for r in L.day_rows(T.read_raw(dp), day, tour):
            if r["priced"] and L.in_scope(r, types)[0]:
                listed += 1
                pages += int(L.match_path(r["te_id"]).exists())
    ok = have_days and listed > 0 and pages >= PAGES_SHARE * listed
    return {"day_pages": have_days, "in_scope_priced": listed, "match_pages": pages, "fetched": ok}


def readiness(now: dt.datetime | None = None) -> dict:
    """Can the comparison run on full data: the capture over (its end line written, or no pull for CAPTURE_IDLE), and
    TennisExplorer's pages of every day on which captured matches started on disk. 'done' when a complete comparison
    is already on disk."""
    now = now or dt.datetime.now(dt.timezone.utc)
    done = False
    if COMPARE_JSON.exists():
        try:
            done = bool(json.loads(COMPARE_JSON.read_text(encoding="utf-8")).get("complete"))
        except ValueError:
            done = False
    files = sorted(PULLS.glob("20*/*.parquet"))
    newest = None
    if files:
        newest = dt.datetime.strptime(f"{files[-1].parent.name} {files[-1].stem}", "%Y-%m-%d %H%M%SZ").replace(
            tzinfo=dt.timezone.utc)
    ended = CAPTURE_RUNS.exists() and CAPTURE_RUNS.read_text(encoding="utf-8").strip() != ""
    over = bool(files) and (ended or (now - newest).total_seconds() > CAPTURE_IDLE)
    days = {d.isoformat(): te_day_fetched(d, now.date()) for d in (started_days(pulls()) if files else [])}
    ready = over and bool(days) and all(v["fetched"] for v in days.values())
    return {"done": done, "ready": ready and not done, "capture_over": over,
            "newest_pull": newest.isoformat() if newest else None, "days": days}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--every", type=int, default=600, help="seconds between pulls (default 600)")
    ap.add_argument("--hours", type=float, default=36.0)
    ap.add_argument("--closes", action="store_true", help="offline: write each lower-level matchup's close (counts)")
    ap.add_argument("--compare", action="store_true",
                    help="offline: the captured closes against TennisExplorer's pages of the same matches (counts)")
    ap.add_argument("--ready", action="store_true",
                    help="offline: whether the comparison can run on full data (exit 0 yes, 1 not yet, 3 done)")
    a = ap.parse_args(argv)
    if a.ready:
        r = readiness()
        print(json.dumps(r, indent=1))
        return 3 if r["done"] else (0 if r["ready"] else 1)
    if a.compare:
        r = readiness()
        df = pulls()
        caps = closes(df)
        last_pull = pd.to_datetime(df.retrieved_at, utc=True).max()
        caps = caps[caps.final_start < last_pull]                 # matches that have started by the last pull
        days = sorted({t.date() for t in caps.final_start.dropna()} |
                      {(t - pd.Timedelta(days=1)).date() for t in caps.final_start.dropna()})
        cmp = compare(caps, te_pages(days))
        complete = r["capture_over"] and bool(r["days"]) and all(v["fetched"] for v in r["days"].values())
        out = {"generated_at": C.utc_now_iso(), "complete": complete, "capture_over": r["capture_over"],
               "days": r["days"], "captured_lower": int(len(cmp)), "by_level": []}
        for (lv, q), g in cmp.groupby(["level", "qualifying"]):
            linked = g[g.linked]
            pin = linked[linked.get("te_pinnacle", pd.Series(False, index=linked.index)).fillna(False).astype(bool)]
            out["by_level"].append({
                "level": lv, "qualifying": bool(q), "captured": int(len(g)), "linked": int(len(linked)),
                "te_pinnacle": int(len(pin)),
                "same_to_0005": int(pin.same_005.sum()) if len(pin) else 0,
                "same_to_001": int(pin.same_01.sum()) if len(pin) else 0,
                "capture_close_min_before_start_median": float(g.close_min_before_start.median()),
                "te_last_change_min_before_start_median": float(pin.te_last_change_min_before_start.median())
                if len(pin) and "te_last_change_min_before_start" in pin and
                pin.te_last_change_min_before_start.notna().any() else None})
        STUDY.mkdir(parents=True, exist_ok=True)
        cmp.to_csv(STUDY / "pinnacle_capture_compare.csv.gz", index=False)
        (STUDY / "pinnacle_capture_compare.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(out, indent=1))
        return 0
    if a.closes:
        c = closes(pulls())
        low = c[c.level.isin(LOWER)]
        summary = {"matchups": int(len(c)), "lower": int(len(low)),
                   "by_level": low.groupby("level").agg(n=("matchup_id", "size"),
                                                        close_min_before_start_median=("close_min_before_start", "median"),
                                                        within_15_min=("close_min_before_start",
                                                                       lambda s: int((s <= 15).sum())),
                                                        start_changed=("starts", lambda s: int((s > 1).sum())),
                                                        live_seen=("live_seen", "sum")).reset_index().to_dict("records")}
        print(json.dumps(summary, indent=1, default=str))
        return 0
    out = loop(a.every, a.hours)
    STUDY.mkdir(parents=True, exist_ok=True)
    with (STUDY / "pinnacle_capture_runs.jsonl").open("a", encoding="utf-8") as h:
        h.write(json.dumps(out) + "\n")
    print(json.dumps(out))
    return 2 if out["stopped"] else 0


if __name__ == "__main__":
    sys.exit(main())
