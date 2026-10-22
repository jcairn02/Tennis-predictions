"""Box scores first: the gaps a prediction run finds after downloading Tennis My Life, and the fills from the official
feed (docs/decisions/2026-10-08-prediction-run-box-scores.md, point 1).

gaps() reads a Stage 0 built on the fresh download (run.py --refresh builds one into the run's folder): every completed
match of an event that began within LOOKBACK_DAYS with a result but no box score. Each is classed:
    held        the frozen reference holds it: TML's own numbers only, when TML publishes them (the owner's choice)
    fillable    after the freeze, from TML: a WTA tour or WTA qualifying match (the WTA API serves its box score), or an
                ATP tour-level main-draw match (the ATP Stats Centre's keystats serve it; the men's fill, owner's
                decision of 14 Oct 2026, docs/decisions/2026-10-14-box-score-gate.md)
    unserved    everything else for now. The Slams: their feeds' live mode waits for the betting pipeline. ITF, team
                events, the WTA 125s TML lacks, the ATP Challengers (their keystats unprobed) and the ATP qualifying
                (its keystats' first serves differ from TML's: 9 of 26 Shanghai 2026 player rows equal)
fill_wta() fetches, through the WTA adapter's own client (about 2 s between requests, a receipt for every answer, a
stop on any block), each fillable match's edition list (refetched while the edition runs) and its box score (once). A
gap is linked to the API's match within the edition by the two players' name keys and the draw (main or
qualifying), and kept only when every set's games agree with TML's score. The API's counts become Stage 0's nine as
data_continuity/sources.py reads them: break points are recorded on the returner's side.
fill_atp() reads the ATP Stats Centre's keystats (the current-season files the daily serve-speed collector fetches and
decrypts, serve_speed_tabpfn/live/atp_daily.py; its raw folder, receipts and year guard). A gap is linked by TML's event
id (TML's men's tourney_id is the year and the ATP's event id), its round's range of match codes (atp_daily.ROUND_CODES;
the qualifying's QS codes) and both players' ATP codes (TML's men's player ids are the ATP's), and kept only when the
file is of the whole match (covers_match: its completed flag, or its service games adding up to TML's score) and its
own fractions agree (1st-serve points won over the first serves in, 2nd-serve points won over the rest). The collector's files on disk are read first; only codes not held complete are asked, with
the collector's client (about 2 s plus jitter, a receipt and a raw copy for every answer, a stop on any block), stopping
at the match. Keystats carry no set scores; Stage 0's own checks (B0-B9) still apply to the filled counts.

The fills take the override table's columns (stage0_build.apply_box_overrides: TML's tour, normalised tournament id,
round and the two players' name keys), so the sandbox's Stage 0 applies them with the decided Slam overrides. They are
rebuilt at every run, so a match TML has since completed takes TML's numbers, and they never reach the repository's
Stage 0 or a template build.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.prediction_run import common as P
from src.eda.prediction_run import live_rows as LR
from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage0_build as B

COUNTS = list(C.BOX_SOURCE_NAMES)                  # Stage 0's nine counts, in the override table's order
SET = re.compile(r"(\d+)-(\d+)")
ATP_LEVELS = ("FIN", "T1000", "T500", "T250")       # the ATP Stats Centre's events (not the Slams, team events)
# Stage 0's count <- (keystats label, 0 the count or numerator / 1 the denominator) (infosys_atp_backfill/checks.py)
KS_COUNTS = {"ace": ("Aces", 0), "df": ("Double Faults", 0), "svpt": ("1st Serve", 1), "first_in": ("1st Serve", 0),
             "first_won": ("1st Serve Points Won", 0), "second_won": ("2nd Serve Points Won", 0),
             "sv_gms": ("Service Games Played", 0), "bp_saved": ("Break Points Saved", 0),
             "bp_faced": ("Break Points Saved", 1)}
FRACTION = re.compile(r"^\s*(\d+)\s*(?:/\s*(\d+))?")


def reference_ids() -> set[str]:
    from src.eda.current_best_model import history as H

    return set(pd.read_parquet(H.REF_STAGE0 / "stage0_matches.parquet", columns=["match_id"])["match_id"].astype(str))


def gaps(stage0: Path, today: pd.Timestamp, held: set[str]) -> pd.DataFrame:
    """Completed matches of events that began within LOOKBACK_DAYS, without a box score, with their class."""
    m = pd.read_parquet(stage0 / "stage0_matches.parquet")
    m["match_id"] = m["match_id"].astype(str)
    recent = m["tournament_date"] >= today - pd.Timedelta(days=P.LOOKBACK_DAYS)
    g = m[recent & m["status"].eq("completed") & ~m["has_box"].astype(bool)].copy()
    g["held"] = g["match_id"].isin(held)
    wta_tour = g["tour"].eq("wta") & g["level"].isin(["GS", "FIN", "T1000", "T500", "T250"]) & g["source"].eq("tml")
    # the ATP's main draws only: there its keystats equal TML's counts (Shanghai 2026, 164 of 164 player rows), while
    # in the qualifying TML's first serves differ from the ATP's (9 of 26 rows equal): a fill there would not be the
    # numbers the training rows hold
    atp_tour = (g["tour"].eq("atp") & g["level"].isin(ATP_LEVELS) & g["source"].eq("tml")
                & ~g["qualifying"].fillna(False).astype(bool))
    g["class"] = np.select([g["held"], (wta_tour & ~g["level"].eq("GS")) | atp_tour], ["held", "fillable"], "unserved")
    return g


def tml_keys(rows: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """The override table's key of each Stage 0 match: its TML row's tour, normalised id, round and name keys."""
    own = LR.raw_of(rows, raw)
    return pd.DataFrame({"tour": rows["tour"].to_numpy(),
                         "tid": own["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True).to_numpy(),
                         "round": own["round"].astype(str).str.upper().to_numpy(),
                         "winner_key": B.S.keys_for(own["winner_name"]).to_numpy(),
                         "loser_key": B.S.keys_for(own["loser_name"]).to_numpy(),
                         "winner_name": own["winner_name"].to_numpy(), "loser_name": own["loser_name"].to_numpy(),
                         "tml_score": own["score"].to_numpy(), "stage0_match_id": rows["match_id"].to_numpy(),
                         # TML's own player ids: the ATP's codes for men (the men's fill links by them; not an
                         # override column, so override_table drops them)
                         "winner_code": own["winner_id"].astype(str).to_numpy(),
                         "loser_code": own["loser_id"].astype(str).to_numpy()},
                        index=rows.index)


def games(score: str) -> list[tuple[int, int]]:
    return [(int(a), int(b)) for a, b in SET.findall(str(score or ""))]


def api_games(m: dict, winner_side: str) -> list[tuple[int, int]]:
    out = []
    for n in range(1, 6):
        a, b = str(m.get(f"ScoreSet{n}A") or "").strip(), str(m.get(f"ScoreSet{n}B") or "").strip()
        if not (a.isdigit() and b.isdigit()):
            break
        out.append((int(a), int(b)) if winner_side == "A" else (int(b), int(a)))
    return out


def api_counts(total: dict, side: str) -> dict:
    """Stage 0's nine counts of one side of a WTA API box score (setnum 0), as data_continuity/sources.py reads them."""
    other = "b" if side == "a" else "a"

    def n(name: str, s: str = side) -> float:
        v = total.get(f"{name}{s}")
        try:
            return float(v)
        except (TypeError, ValueError):
            return float("nan")

    return {"ace": n("aces"), "df": n("dblflt"), "svpt": n("totservplayed"), "first_in": n("ptsplayed1stserv"),
            "first_won": n("ptswon1stserv"), "second_won": n("ptstotwonserv") - n("ptswon1stserv"),
            "sv_gms": n("servgamesplayed"), "bp_saved": n("breakptsplayed", other) - n("breakptsconv", other),
            "bp_faced": n("breakptsplayed", other)}


def fill_wta(fillable: pd.DataFrame, keys: pd.DataFrame, max_requests: int) -> tuple[pd.DataFrame, list[dict]]:
    """The WTA API's box score of each fillable gap, as override rows; and what happened to every gap."""
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import feeds as F
    from src.ingest.point_sources import wta as W

    notes: list[dict] = []
    if fillable.empty:
        return pd.DataFrame(), notes
    client = W.make_client(min_interval=2.0, jitter=1.0, max_requests=max_requests)
    receipts = PS.receipts_for(W.SOURCE)
    fills = []
    try:
        years = sorted(set(int(y) for y in fillable["year"]))
        for y in years:
            W.fetch_calendar(client, receipts, y, refresh=True)
        editions = {(e["tournament_id"], int(e["year"])): e for e in W.load_editions(years)}
        fillable = fillable.assign(api_tid=keys.loc[fillable.index, "tid"].str.split("-").str[1])
        for (api_tid, year), group in fillable.groupby(["api_tid", "year"]):
            edition = editions.get((str(api_tid), int(year)))
            if edition is None:
                notes += [{"match_id": mid, "outcome": "edition not in the WTA calendar"} for mid in group["match_id"]]
                continue
            W.fetch_listing(client, receipts, edition, refresh=True)
            played = [m for m in W.load_listing(str(api_tid), int(year)) if m.get("DrawMatchType") == "S"
                      and W.is_played(m)]
            for i, gap in group.iterrows():
                k = keys.loc[i]
                level = "Q" if bool(gap["qualifying"]) else "M"
                want = {k["winner_key"], k["loser_key"]}
                cands = []
                for m in played:
                    a = B.S.name_key(f"{m.get('PlayerNameFirstA') or ''} {m.get('PlayerNameLastA') or ''}")
                    b = B.S.name_key(f"{m.get('PlayerNameFirstB') or ''} {m.get('PlayerNameLastB') or ''}")
                    if m.get("DrawLevelType") == level and {a, b} == want:
                        cands.append((m, "A" if a == k["winner_key"] else "B"))
                cands = [(m, w) for m, w in cands if api_games(m, w) == games(k["tml_score"])]
                if len(cands) != 1:
                    notes.append({"match_id": gap["match_id"], "outcome": f"{len(cands)} WTA API matches agree"})
                    continue
                m, w = cands[0]
                receipt = W.fetch_endpoint(client, receipts, str(api_tid), int(year), m["MatchID"], "stats",
                                           refresh=False, extra={"tier": edition["tier"], "draw": W.draw_of(m),
                                                                 "round": m.get("RoundID"), "prediction_run": True})
                if receipt.get("status") != 200:
                    notes.append({"match_id": gap["match_id"], "outcome": f"stats {receipt.get('error') or receipt.get('status')}"})
                    continue
                rows = W.stats_rows(str(api_tid), int(year), m["MatchID"],
                                    PS.read_json(W.endpoint_dest(str(api_tid), int(year), m["MatchID"], "stats")))
                total = next((r for r in rows if str(r.get("setnum")) == "0"), None)
                if total is None:
                    notes.append({"match_id": gap["match_id"], "outcome": "stats without the match's totals"})
                    continue
                win, lose = api_counts(total, w.lower()), api_counts(total, "b" if w == "A" else "a")
                row = {"box_source": "wta_api_live", "feed_key": f"wta:{api_tid}/{year}/{m['MatchID']}",
                       **k.to_dict(), "score": "", "minutes": "", "feed_sha256": receipt.get("sha256"),
                       "feed_retrieved_at": receipt.get("retrieved_at")}
                for c, src in C.BOX_SOURCE_NAMES.items():
                    row[f"w_{src}"], row[f"l_{src}"] = win[c], lose[c]
                if any(np.isnan(v) for v in list(win.values()) + list(lose.values())):
                    notes.append({"match_id": gap["match_id"], "outcome": "stats incomplete"})
                    continue
                fills.append(row)
                notes.append({"match_id": gap["match_id"], "outcome": "filled", "feed_key": row["feed_key"]})
    except (PS.Blocked, PS.BudgetExhausted, F.Stopped) as stop:     # a block stops the fills, as the decision asks
        notes.append({"match_id": None, "outcome": f"stopped: {type(stop).__name__}: {stop}"})
    return pd.DataFrame(fills), notes


def atp_codes(rnd: str, qualifying: bool) -> list[str]:
    """The ATP's match codes a round can carry: the main draw's by the bracket (atp_daily.ROUND_CODES), the
    qualifying's QS001-QS063 (their numbers overlap across rounds)."""
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    rnd = str(rnd).upper()
    if qualifying or (rnd.startswith("Q") and rnd != "QF"):
        return [f"QS{n:03d}" for n in range(1, 64)]
    lo, hi = AD.ROUND_CODES.get(rnd, (0, -1))
    return [f"MS{n:03d}" for n in range(lo, hi + 1)]


def held_keystats(year: int, event: str, code: str) -> dict | None:
    """The decrypted keystats of one of the collector's raw files (None when it holds none); atp_daily's guard refuses
    any year before 2026."""
    import gzip
    import json
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    path = AD.raw_path(year, event, code)
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        doc = AD.decrypt_envelope(json.load(f), year=year, path=path)
    return doc.get("stats", doc) if isinstance(doc, dict) else None


def _ks_number(value, part: int) -> float:
    m = FRACTION.match(str(value if value is not None else ""))
    if not m or (part == 1 and m.group(2) is None):
        return float("nan")
    return float(m.group(1 if part == 0 else 2))


def keystats_counts(ks: dict, code: str) -> dict | None:
    """Stage 0's nine counts of the player with this ATP code in a decrypted keystats object; None when the player is
    not in it. "consistent" says whether its own fractions agree: 1st-serve points won over the first serves in, and
    2nd-serve points won over the rest of the serve points."""
    from src.eda.serve_speed_tabpfn.live import staging as ST
    (c1, _), (c2, _) = ST.keystats_players(ks)
    side = 0 if str(c1) == code else (1 if str(c2) == code else None)
    if side is None:
        return None
    vals = ST.keystats_values(ks)
    out = {c: _ks_number((vals.get(label) or (None, None))[side], part) for c, (label, part) in KS_COUNTS.items()}
    d1 = _ks_number((vals.get("1st Serve Points Won") or (None, None))[side], 1)
    d2 = _ks_number((vals.get("2nd Serve Points Won") or (None, None))[side], 1)
    out["consistent"] = bool(d1 == out["first_in"] and d2 == out["svpt"] - out["first_in"])
    return out


def covers_match(ks: dict, k) -> bool:
    """Whether a keystats file is of the whole match TML scored: its "matchCompleted" flag, or, since that flag reads
    False on many finished matches (Shanghai 2026: 9 of 82, e.g. Tsitsipas v Fritz 3-6 7-5 6-3, 15 service games
    each), its two players' service games adding up to the score's games, its tiebreak games counted or not, within one
    (as Stage 0's check B5 reads them)."""
    if ks.get("matchCompleted"):
        return True
    w, l = keystats_counts(ks, str(k["winner_code"])), keystats_counts(ks, str(k["loser_code"]))
    if w is None or l is None or np.isnan(w["sv_gms"]) or np.isnan(l["sv_gms"]):
        return False
    total = sum(a + b for a, b in games(k["tml_score"]))
    tiebreaks = len(re.findall(r"7-6|6-7", str(k["tml_score"] or "")))
    sv = w["sv_gms"] + l["sv_gms"]
    return total > 0 and (abs(sv - total) <= 1 or abs(sv - (total - tiebreaks)) <= 1)


def _atp_client(max_requests: int):
    """The daily collector's client, headers and receipts (atp_daily.fetch_daily's): None when the collector is off,
    or its backfill adapter is required and missing."""
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import feeds as FD
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    from src.eda.serve_speed_tabpfn.live import common as LC
    if not AD.enabled():
        return None
    try:
        A = AD._adapter()
    except AD.NotEnabled:
        if LC.read_json(LC.COLLECTOR_CFG, {}).get("require_backfill_adapter", True):
            return None
        A = None
    headers = dict(getattr(A, "HEADERS", None) or AD.site_headers())
    client = FD.FeedClient(getattr(A, "IMPERSONATE", "chrome"), min_interval=2.0, jitter=1.0,
                           max_requests=max_requests, timeout=60)
    return client, headers, PS.receipts_for(AD.SOURCE)


def fill_atp(fillable: pd.DataFrame, keys: pd.DataFrame, max_requests: int,
             ask: bool = True) -> tuple[pd.DataFrame, list[dict]]:
    """The ATP Stats Centre's box score of each fillable men's gap, as override rows; and what happened to every gap.
    ask=False reads only the collector's files on disk (no request)."""
    import hashlib
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import feeds as F
    from src.ingest.point_sources import infosys_slams as I
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    from src.eda.serve_speed_tabpfn.live import staging as ST

    notes: list[dict] = []
    if fillable.empty:
        return pd.DataFrame(), notes
    fills, conn = [], None
    try:
        for i, gap in fillable.iterrows():
            k = keys.loc[i]
            tid = str(k["tid"])
            if not re.fullmatch(r"\d{4}-\d+", tid):
                notes.append({"match_id": gap["match_id"], "outcome": f"not an ATP event id ({tid})"})
                continue
            year, event = int(tid[:4]), tid.split("-")[1]
            want = {str(k["winner_code"]), str(k["loser_code"])}
            codes = atp_codes(k["round"], bool(gap["qualifying"]))
            found, how = None, "held"
            for code in codes:                           # the collector's own files first: no request
                ks = held_keystats(year, event, code)
                if ks and {str(c) for c, _ in ST.keystats_players(ks)} == want:
                    found = (code, ks)
                    break
            if (found is None or not covers_match(found[1], k)) and not ask:
                notes.append({"match_id": gap["match_id"], "outcome": "not held complete (files on disk only)"})
                continue
            if found is None or not covers_match(found[1], k):
                if conn is None:
                    conn = _atp_client(max_requests) or False
                if not conn:
                    notes.append({"match_id": gap["match_id"], "outcome": "the ATP collector is off: not asked"})
                    continue
                client, headers, receipts = conn
                found, how = None, "asked"
                for code in codes:
                    ks = held_keystats(year, event, code)
                    if ks and {str(c) for c, _ in ST.keystats_players(ks)} != want:
                        continue                         # another match's code (a code's players never change)
                    AD.guard(year)
                    rec = PS.fetch(client, AD.HOST + AD.ROUTES["keystats-api"].format(year=year, event=event, mid=code),
                                   AD.raw_path(year, event, code), receipts, name=f"{year}/{event}/keystats-api/{code}",
                                   refresh=True, validator=I.envelope_validator, compress=True, headers=headers,
                                   extra={"year": year, "event": event, "match_id": code, "round": k["round"],
                                          "prediction_run": True})
                    if rec.get("status") != 200 or rec.get("error"):
                        continue
                    ks = held_keystats(year, event, code)
                    if ks and {str(c) for c, _ in ST.keystats_players(ks)} == want:
                        found = (code, ks)
                        break
            if found is None:
                notes.append({"match_id": gap["match_id"], "outcome": "not found in the ATP Stats Centre"})
                continue
            code, ks = found
            if not covers_match(ks, k):
                notes.append({"match_id": gap["match_id"], "outcome": "the ATP's file is not of the whole match"})
                continue
            win, lose = keystats_counts(ks, str(k["winner_code"])), keystats_counts(ks, str(k["loser_code"]))
            if any(np.isnan(v) for v in [*(win[c] for c in COUNTS), *(lose[c] for c in COUNTS)]):
                notes.append({"match_id": gap["match_id"], "outcome": "stats incomplete"})
                continue
            if not (win["consistent"] and lose["consistent"]):
                notes.append({"match_id": gap["match_id"], "outcome": "stats inconsistent"})
                continue
            path = AD.raw_path(year, event, code)
            row = {"box_source": "atp_keystats_live", "feed_key": f"atp:{year}/{event}/{code}",
                   **{c: k[c] for c in ("tour", "tid", "round", "winner_key", "loser_key", "winner_name", "loser_name",
                                        "tml_score", "stage0_match_id")},
                   "score": "", "minutes": "", "feed_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "feed_retrieved_at": pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC").isoformat()}
            for c, src in C.BOX_SOURCE_NAMES.items():
                row[f"w_{src}"], row[f"l_{src}"] = win[c], lose[c]
            fills.append(row)
            notes.append({"match_id": gap["match_id"], "outcome": "filled", "feed_key": row["feed_key"], "how": how})
    except (PS.Blocked, PS.BudgetExhausted, F.Stopped) as stop:     # a block stops the fills, as the decision asks
        notes.append({"match_id": None, "outcome": f"stopped: {type(stop).__name__}: {stop}"})
    return pd.DataFrame(fills), notes


def fill_all(fillable: pd.DataFrame, keys: pd.DataFrame | None, max_requests: int) -> tuple[pd.DataFrame, list[dict]]:
    """The women's fills from the WTA API and the men's from the ATP Stats Centre, together."""
    if fillable.empty:
        return pd.DataFrame(), []
    out, notes = [], []
    for tour, fill in (("wta", fill_wta), ("atp", fill_atp)):
        part = fillable[fillable["tour"].eq(tour)]
        if len(part):
            f, n = fill(part, keys.loc[part.index], max_requests)
            out.append(f)
            notes += n
    out = [f for f in out if len(f)]
    return (pd.concat(out, ignore_index=True) if out else pd.DataFrame()), notes


def override_table(fills: pd.DataFrame) -> pd.DataFrame:
    """The decided Slam overrides and the run's fills, in the override table's columns."""
    decided = pd.read_csv(B.DECIDED_OVERRIDES, dtype=str, keep_default_na=False)
    if fills.empty:
        return decided
    f = fills.reindex(columns=decided.columns).astype(object).where(fills.reindex(columns=decided.columns).notna(), "")
    for col in [c for c in decided.columns if c.startswith(("w_", "l_"))]:
        f[col] = pd.to_numeric(fills[col]).astype(int).astype(str)
    return pd.concat([decided, f], ignore_index=True)


def agreement(found: pd.DataFrame, raw: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """For matches TML already scored: the share of player rows where the WTA API's count (as a fill would give it)
    equals TML's, count by count. Both sides are in TML's orientation (its winner and loser)."""
    own = LR.raw_of(matches, raw).assign(match_id=matches["match_id"].to_numpy()).set_index("match_id")
    f = found.set_index("stage0_match_id")
    rows = []
    for c, src in C.BOX_SOURCE_NAMES.items():
        api = pd.concat([pd.to_numeric(f[f"w_{src}"]), pd.to_numeric(f[f"l_{src}"])])
        tml = pd.concat([pd.to_numeric(own.loc[f.index, f"w_{src}"], errors="coerce"),
                         pd.to_numeric(own.loc[f.index, f"l_{src}"], errors="coerce")])
        rows.append({"count": c, "player_rows": int(len(api)), "equal": int((api.to_numpy() == tml.to_numpy()).sum()),
                     "share_equal": round(float((api.to_numpy() == tml.to_numpy()).mean()), 4) if len(api) else None,
                     "mean_api_minus_tml": round(float((api.to_numpy() - tml.to_numpy()).mean()), 3) if len(api) else None})
    return pd.DataFrame(rows)


def main() -> int:
    """Check the fill against TML where TML has the box score: the agreement the fills would bring. --tour atp reads
    the men's from the ATP Stats Centre (with --max-requests 0, only the collector's files on disk: no request)."""
    import argparse
    import json

    ap = argparse.ArgumentParser(description=main.__doc__)
    ap.add_argument("--stage0", default=str(C.OUT), help="the Stage 0 folder (default: the repository's)")
    ap.add_argument("--events", required=True, help="comma list of Stage 0 tournament ids")
    ap.add_argument("--tour", default="wta", choices=["wta", "atp"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-requests", type=int, default=200)
    a = ap.parse_args()
    m = pd.read_parquet(Path(a.stage0) / "stage0_matches.parquet")
    m["match_id"] = m["match_id"].astype(str)
    scored = m[m["tournament_id"].isin(a.events.split(",")) & m["tour"].eq(a.tour) & m["status"].eq("completed")
               & m["has_box"].astype(bool) & m["source"].eq("tml")]
    raw = LR.staged_tml(sorted({int(y) for y in scored["year"]}))
    keys = tml_keys(scored, raw)
    if a.tour == "wta":
        found, notes = fill_wta(scored, keys, a.max_requests)
    else:                                               # --max-requests 0: the collector's files only, no request
        found, notes = fill_atp(scored, keys, a.max_requests, ask=a.max_requests > 0)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    table = agreement(found, raw, scored[scored["match_id"].isin(set(found.get("stage0_match_id", [])))]) \
        if len(found) else pd.DataFrame()
    table.to_csv(out / "fill_agreement.csv", index=False)
    summary = {"matches": int(len(scored)), "fetched": int(len(found)),
               "outcomes": pd.Series([n["outcome"] for n in notes]).value_counts().to_dict(),
               "agreement": table.to_dict("records")}
    (out / "fill_agreement.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
