"""The staging format for daily ATP per-match serve speeds, and its parsers. Reads no match result.

One row per match (wide), both players in the source's own order (player 1 / player 2 of the draw for Infosys and the
ATP pages; for ManTennisData, whose rows are winner / loser, the pair is put in ATP-code order so the order carries no
result):

    year, event_id, match_code (MS001 ...), round (the source's, else from the main-draw code: MS001 F, MS002-003 SF,
    MS004-007 QF ... MS064-127 R128; 99.5% right on the held Infosys links; qualifying codes give no round), match_date
    (if the source has it), p1_atp_id, p1_name, p2_atp_id, p2_name, p1_spd1, p2_spd1 (first-serve average, km/h),
    p1_first_in, p1_first_total, p2_first_in, p2_first_total, p1_spd2, p2_spd2 (second-serve average), p1_max, p2_max,
    match_completed, source, retrieved_at, collected_on (the day the row reached the project), source_file
A speed outside (40, 270] km/h is missing. Nothing here touches a match result: the parsers read the key statistics
(speeds, first serves) and the players' identities only.

Parsers:
    parse_keystats      a DECRYPTED Infosys key-statistics object (the current season's /prod/api/stats-plus route, or
                        the "keystats" member of the handoff's records); test data: the held, already-decrypted handoff
                        copies only (data/raw/public_dump/atp_pipeline_handoff/infosys_*)
    parse_handoff_record  a handoff record (year, tournament_id, match_id, match_date, players, keystats)
    from_rendered       PATH (b) HOOK: the values a rendered ATP stats page shows, as {label: (player 1, player 2)}
    mantd_rows          ManTennisData's weekly CSV rows (the fallback feed), for matches the frozen panel lacks
"""
from __future__ import annotations

import gzip
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.serve_speed_tabpfn.live import common as LC

STAGING_COLS = ["year", "event_id", "match_code", "round", "match_date", "p1_atp_id", "p1_name", "p2_atp_id", "p2_name",
                "p1_spd1", "p2_spd1", "p1_first_in", "p1_first_total", "p2_first_in", "p2_first_total", "p1_spd2",
                "p2_spd2", "p1_max", "p2_max", "match_completed", "source", "retrieved_at", "collected_on",
                "source_file"]
SPEED_LABELS = {"1st Serve Average Speed": "spd1", "2nd Serve Average Speed": "spd2", "Max Speed": "max"}
FIRST_LABELS = ("1st Serve", "First Serve")
FIRST = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")
BRACKET = {0: "F", 1: "SF", 2: "QF", 3: "R16", 4: "R32", 5: "R64", 6: "R128"}


def round_from_code(code) -> str | None:
    """The round of a main-draw Infosys code by its bracket number (MS001 the final ... MS064-127 the first of 128);
    None for qualifying (QS) codes, whose numbers overlap between rounds, and for anything else."""
    m = re.fullmatch(r"MS(\d{3})", str(code or "").upper())
    if not m or int(m.group(1)) < 1:
        return None
    return BRACKET.get(int(math.floor(math.log2(int(m.group(1))))))


def _first(value) -> tuple[float, float]:
    m = FIRST.match(str(value or ""))
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


def _row(year, event_id, match_code, rnd, match_date, p1, p2, stats: dict, completed, source, retrieved_at,
         collected_on, source_file) -> dict:
    """stats: {label: (player 1 value, player 2 value)}; p1 / p2: (ATP code, name)."""
    out = {"year": int(year), "event_id": str(event_id).strip(), "match_code": str(match_code or "").upper() or None,
           "round": rnd or round_from_code(match_code), "match_date": match_date or None,
           "p1_atp_id": LC.atp_code(p1[0]), "p1_name": p1[1], "p2_atp_id": LC.atp_code(p2[0]), "p2_name": p2[1],
           "match_completed": None if completed is None else bool(completed), "source": source,
           "retrieved_at": retrieved_at, "collected_on": collected_on, "source_file": source_file}
    for label, short in SPEED_LABELS.items():
        v = stats.get(label, (None, None))
        out[f"p1_{short}"], out[f"p2_{short}"] = LC.plaus(v[0]), LC.plaus(v[1])
    fv = next((stats[k] for k in FIRST_LABELS if k in stats), (None, None))
    (out["p1_first_in"], out["p1_first_total"]), (out["p2_first_in"], out["p2_first_total"]) = _first(fv[0]), _first(fv[1])
    return out


def keystats_values(ks: dict) -> dict:
    """{label: (player 1, player 2)} of the match ("set0") key statistics of a decrypted keystats object."""
    s0 = ((ks or {}).get("setStats") or {}).get("set0") or []
    return {e.get("name"): (e.get("player1"), e.get("player2")) for e in s0 if isinstance(e, dict)}


def keystats_players(ks: dict) -> tuple[tuple, tuple]:
    """(code, name) of player 1 and player 2 from a keystats object's `players` list (each entry uses player1* keys)."""
    pl = [p for p in ((ks or {}).get("players") or []) if isinstance(p, dict)]

    def one(p):
        name = p.get("player1Name") or " ".join(x for x in (p.get("player1FirstName"), p.get("player1LastName")) if x)
        return p.get("player1Id"), name or None
    return (one(pl[0]) if len(pl) > 0 else (None, None)), (one(pl[1]) if len(pl) > 1 else (None, None))


def parse_keystats(ks: dict, *, year, event_id, match_code, rnd=None, match_date=None, players=None,
                   retrieved_at=None, collected_on=None, source="infosys_atp_daily", source_file=None) -> dict | None:
    """One staging row from a DECRYPTED key-statistics object; None when it holds no first-serve average."""
    vals = keystats_values(ks)
    if "1st Serve Average Speed" not in vals:
        return None
    p1, p2 = players if players is not None else keystats_players(ks)
    return _row(year, event_id, match_code, rnd, match_date, p1, p2, vals, (ks or {}).get("matchCompleted"), source,
                retrieved_at, collected_on, source_file)


def parse_handoff_record(rec: dict, source_file=None) -> dict | None:
    """A Hugging Face handoff record (already decrypted by its publisher): metadata at the top, keystats inside."""
    ks = rec.get("keystats") if isinstance(rec.get("keystats"), dict) else {}
    players = ((rec.get("player1_id"), rec.get("player1_name")), (rec.get("player2_id"), rec.get("player2_name")))
    if not players[0][0] or not players[1][0]:
        players = None
    return parse_keystats(ks, year=rec.get("year"), event_id=rec.get("tournament_id"), match_code=rec.get("match_id"),
                          match_date=rec.get("match_date"), players=players, source="handoff_keystats",
                          source_file=source_file)


def handoff_rows(path: Path, limit: int | None = None) -> list[dict]:
    """Staging rows of one handoff file (only records that carry a first-serve average), up to `limit`."""
    rows = []
    op = gzip.open if str(path).endswith(".gz") else open
    with op(path, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "1st Serve Average Speed" not in line:
                continue
            try:
                r = parse_handoff_record(json.loads(line), source_file=str(path))
            except ValueError:
                continue
            if r is not None:
                rows.append(r)
                if limit and len(rows) >= limit:
                    break
    return rows


def from_rendered(values: dict, *, year, event_id, match_code, p1: tuple, p2: tuple, rnd=None, match_date=None,
                  completed=True, retrieved_at=None, collected_on=None, source_file=None) -> dict:
    """PATH (b) HOOK. The values an ATP match-stats page shows once rendered in a browser, by its own labels
    ({"1st Serve Average Speed": ("190 km/h", "185 km/h"), "1st Serve": ("51/78 (65%)", "35/63 (56%)"), ...}),
    to the same staging row as the decrypted files give. Units and percentages are stripped."""
    def clean(v):
        m = re.search(r"\d+(?:\.\d+)?", str(v or ""))
        return m.group(0) if m else None
    stats = {}
    for label, (a, b) in values.items():
        stats[label] = (a, b) if label in FIRST_LABELS else (clean(a), clean(b))
    return _row(year, event_id, match_code, rnd, match_date, p1, p2, stats, completed, "atp_page", retrieved_at,
                collected_on, source_file)


def mantd_rows(m: pd.DataFrame, collected_on: str, retrieved_at: str | None = None, source_file=None) -> list[dict]:
    """ManTennisData CSV rows (strings) to staging rows; the pair in ATP-code order (winner / loser order dropped)."""
    out = []
    url = m["stats_url"].astype(str).str.extract(r"/archive/(\d{4})/(\d+)/([a-z]{2}\d{3})", flags=re.I)
    for i, r in enumerate(m.itertuples(index=False)):
        a = (r.winner_code, r.winner_name, "win")
        b = (r.loser_code, r.loser_name, "los")
        p1, p2 = sorted([a, b], key=lambda t: str(t[0]).upper())
        stats = {}
        for label, col in (("1st Serve Average Speed", "average_first_serves_kmh"),
                           ("2nd Serve Average Speed", "average_second_serve_kmh"),
                           ("Max Speed", "fastest_first_serves_kmh")):
            stats[label] = (getattr(r, f"{p1[2]}_{col}"), getattr(r, f"{p2[2]}_{col}"))
        stats["1st Serve"] = (f"{getattr(r, p1[2] + '_first_serves_in')}/{getattr(r, p1[2] + '_first_serves_total')}",
                              f"{getattr(r, p2[2] + '_first_serves_in')}/{getattr(r, p2[2] + '_first_serves_total')}")
        year, tid = str(r.tournament_id).split("-", 1)
        row = _row(year, tid, url.iloc[i, 2], r.stadie_id, None, p1[:2], p2[:2], stats, True, "mantennisdata",
                   retrieved_at, collected_on, source_file)
        row["mantd_id"] = r.id
        out.append(row)
    return out


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in STAGING_COLS:
        if c not in df:
            df[c] = None
    extra = [c for c in df.columns if c not in STAGING_COLS]
    df = df[STAGING_COLS + extra]
    for c in ("p1_spd1", "p2_spd1", "p1_spd2", "p2_spd2", "p1_max", "p2_max", "p1_first_in", "p1_first_total",
              "p2_first_in", "p2_first_total"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    if len(df):
        df["year"] = df["year"].astype("int64")
    return df


def write(df: pd.DataFrame, name: str, out: Path = LC.STAGING) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.parquet"
    df.to_parquet(path, index=False)
    return path


def add(df: pd.DataFrame, name: str, keys: list[str], out: Path = LC.STAGING) -> Path:
    """write(), keeping the rows an earlier write of the same name holds: a second run on one day adds to the first's
    rows instead of replacing them (24 Oct 2026: the 07:30 task's run, ten minutes after the notebook's, erased six
    quarter-finals the first had staged); for a key both hold, the newer row stands."""
    path = Path(out) / f"{name}.parquet"
    if path.exists():
        df = pd.concat([pd.read_parquet(path), df], ignore_index=True)
    return write(df.drop_duplicates(keys, keep="last").reset_index(drop=True), name, Path(out))


def read_all(out: Path = LC.STAGING) -> pd.DataFrame:
    files = sorted(Path(out).glob("*.parquet")) if Path(out).exists() else []
    if not files:
        return to_frame([])
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
