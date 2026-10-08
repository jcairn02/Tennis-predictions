"""Flashscore files of the ATP pipeline handoff, read into one compact table of matches (one row per
Flashscore match id), for linking match start times to Stage 0 (see link_flashscore.py).

What the files hold (observed when this was written, 5 Oct 2026):
    flashscore_full/  year files     ATP and Challenger singles match pages, with ``match_start_ts`` and
                                     ``match_end_ts`` (Unix seconds), round, set scores, status
                      h2h passes     the uploader's head-to-head crawl: match pages found through other
                                     matches' head-to-head feeds; no round, no category; ``score_home`` /
                                     ``score_away`` hold the players' countries, ``country`` the event's
                      layer3         "recovered" rows with no match id and no start time: counted, not used
    flashscore_gql_stats/            match pages with statistics; tournament slug but no tournament name
    flashscore_daily/                daily result boards of April-June 2026: match id (``fs_mid``), category,
                                     board date, no start time and no set scores
    flashscore_data/, flashscore_bruteforce/
                                     result lists with a date but no match id and no start time: counted only

Every match page also carries ``h2h_json``, Flashscore's raw head-to-head feed for the two players
(entries separated by ``~``, fields by U+00AC, key and value by U+00F7). Each entry is a match with
its id (KP), start time (KC), tournament (KF), event country (KH), surface (KD), status (AC), both
participants' ids (UQ, UO), names (KJ, KK; the winner's starts with ``*``), name slugs (UE, UG) and
sets won (KU, KT). The page's own match is one of the entries. The feeds therefore also name many
matches that have no page in the files ("feed entries"), with the same start time field.

The top-level ``home_player_name`` / ``*_slug`` / ``*_fs_id`` fields of a page often belong to other
players (observed: swapped or unrelated in about half the pages of two files), so player ids and
slugs are taken from the page's own feed entry instead.

parse_all() streams every file with a pool of worker processes; each worker writes its pages and the
distinct feed entries it meets (from 2009-12-01 on) to parquet shards in a work directory, so no
process holds a whole 2-4 GB file's entries. build_records() merges the shards into one row per match
id: page fields first (year file, then statistics file, then head-to-head page, then daily board),
the feed entry's fields where the page lacks them.
"""
from __future__ import annotations

import gzip
import json
import re
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
FOLDERS = ("flashscore_full", "flashscore_gql_stats", "flashscore_daily", "flashscore_data", "flashscore_bruteforce")
SCOPE_FROM = "2009-12-01"
SCOPE_FROM_TS = int(pd.Timestamp(SCOPE_FROM, tz="UTC").timestamp())
SCOPE_FROM_DATE = SCOPE_FROM.replace("-", "")
SEP_E, SEP_F, SEP_KV = "~", "¬", "÷"
ENTRY_FLUSH = 250_000                     # distinct feed entries a worker holds before writing a shard
KIND_PRIORITY = {"year": 0, "stats": 1, "h2h": 2, "daily": 3}
# Flashscore's status codes (AC in the feeds): 3 finished, 8 retired, 9 walkover, 54 awarded. Read from the data, not
# documented: on linked matches 8 is Stage 0's "retired", 9 its "walkover" and 54 its "other" (defaulted, abandoned).
# Match pages always say 3, so the page's own feed entry gives the status.
STATUS_CODES = {"3": "finished", "8": "retired", "9": "walkover", "54": "awarded"}

REC_COLS = ["fs_match_id", "kind", "file", "line", "start_ts", "end_ts", "match_date", "board_date", "category",
            "tournament_name", "tournament_slug", "country", "surface", "round_raw", "home_name", "away_name",
            "home_sets", "away_sets", "set_scores", "status_code",
            "e_found", "e_swapped", "e_ts", "e_tournament", "e_country", "e_surface", "e_status", "e_home_id",
            "e_away_id", "e_home_name", "e_away_name", "e_home_slug", "e_away_slug", "e_home_sets", "e_away_sets",
            "e_winner", "e_gender_home", "e_gender_away"]
ENTRY_COLS = ["kp", "kc", "kf", "kh", "kd", "ac", "uq", "uo", "kj", "kk", "ue", "ug", "ku", "kt", "winner",
              "g_home", "g_away"]
NOID_COLS = ["kind", "file", "match_date", "category", "tournament_name", "tournament_slug", "home_name",
             "away_name", "score_home", "score_away", "round_raw"]


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open(encoding="utf-8", errors="replace")


def file_kind(path: Path) -> str:
    folder, name = path.parent.name, path.name
    if folder == "flashscore_full":
        if "layer3" in name:
            return "layer3"
        return "h2h" if "_h2h_" in name else "year"
    return {"flashscore_gql_stats": "stats", "flashscore_daily": "daily", "flashscore_data": "data",
            "flashscore_bruteforce": "bruteforce"}[folder]


def data_files(raw: Path = RAW) -> list[Path]:
    """Every finished data file of the five folders (not checkpoints, *.part or *.bad-* files)."""
    out = []
    for folder in FOLDERS:
        out += [p for p in (raw / folder).glob("*.jsonl*") if p.name.endswith((".jsonl", ".jsonl.gz"))]
    return sorted(out)


def to_int(value) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def text(value) -> str:
    return "" if value is None else str(value).strip()


# ------------------------------------------------------------------------------------------------
# The head-to-head feed

def gender_hint(image: str) -> str:
    """EC / ED hold a photo file name, or Flashscore's default silhouette 'men' / 'women'."""
    return {"men": "m", "women": "w"}.get(image, "")


def entry_of(chunk: str) -> dict:
    out = {}
    for field in chunk.split(SEP_F):
        key, _, value = field.partition(SEP_KV)
        if key and key not in out:
            out[key] = value
    return out


def entry_tuple(e: dict) -> tuple:
    """(kp, kc, kf, kh, kd, ac, uq, uo, kj, kk, ue, ug, ku, kt, winner, g_home, g_away)."""
    kj, kk = e.get("KJ", ""), e.get("KK", "")
    winner = "home" if kj.startswith("*") else "away" if kk.startswith("*") else ""
    return (e.get("KP", ""), to_int(e.get("KC")), e.get("KF", ""), e.get("KH", ""), e.get("KD", ""), e.get("AC", ""),
            e.get("UQ", ""), e.get("UO", ""), kj.lstrip("*").strip(), kk.lstrip("*").strip(), e.get("UE", ""),
            e.get("UG", ""), to_int(e.get("KU")), to_int(e.get("KT")), winner,
            gender_hint(e.get("EC", "")), gender_hint(e.get("ED", "")))


def feed_entries(blob: str):
    """Yield (kp, chunk) for each match entry of a head-to-head feed, without parsing its fields."""
    for chunk in blob.split(SEP_E):
        if not chunk.startswith("KC" + SEP_KV):
            continue
        head = chunk.split(SEP_F, 2)
        if len(head) < 2 or not head[1].startswith("KP" + SEP_KV):
            kp = entry_of(chunk).get("KP", "")
        else:
            kp = head[1][3:]
        if kp:
            yield kp, chunk


# ------------------------------------------------------------------------------------------------
# One file

DAILY_TOURNAMENT = re.compile(r"^(?P<name>.*?)\s*\((?P<country>[^()]*)\)\s*(?:-\s*(?P<stage>[^,]*?))?\s*,"
                              r"\s*(?P<surface>[\w ]+)$")


def split_daily_tournament(raw) -> tuple[str, str | None, str | None, str | None]:
    """A daily board's "Rome (Italy), clay" or "Tyler (USA) - Qualification, hard" as (name, country, surface, stage)."""
    m = DAILY_TOURNAMENT.match(text(raw))
    if not m:
        return text(raw), None, None, None
    return m["name"], m["country"], m["surface"].lower(), (m["stage"] or None)


def page_row(kind: str, rel: str, line_no: int, r: dict) -> dict:
    """The fields of one match page (year, statistics or head-to-head file) or daily-board row."""
    row = dict.fromkeys(REC_COLS)
    row.update(kind=kind, file=rel, line=line_no, e_found=False, e_swapped=False)
    if kind == "daily":
        row["fs_match_id"] = text(r.get("fs_mid"))
        row["board_date"] = text(r.get("query_date")) or None
        row["match_date"] = text(r.get("match_date"))
        name, country, surface, stage = split_daily_tournament(r.get("tournament"))
        row.update(tournament_name=name, country=country, surface=surface)
        row.update(category=text(r.get("category")), round_raw=text(r.get("round_raw")) or text(r.get("round")) or stage,
                   home_name=text(r.get("home_player")), away_name=text(r.get("away_player")),
                   home_sets=to_int(r.get("score_home")), away_sets=to_int(r.get("score_away")))
        return row
    row["fs_match_id"] = text(r.get("match_id"))
    row["start_ts"] = to_int(r.get("match_start_ts"))
    row["end_ts"] = to_int(r.get("match_end_ts"))
    row["match_date"] = text(r.get("match_date"))
    row["category"] = text(r.get("category"))
    row["tournament_name"] = text(r.get("tournament_name"))
    row["tournament_slug"] = text(r.get("tournament_slug"))
    row["country"] = text(r.get("country"))
    row["surface"] = text(r.get("surface")).lower()
    row["round_raw"] = text(r.get("round_raw")) or text(r.get("round"))
    row["home_name"], row["away_name"] = text(r.get("home_player")), text(r.get("away_player"))
    hs, as_ = to_int(r.get("home_sets")), to_int(r.get("away_sets"))
    if hs is None and kind != "h2h":                   # head-to-head pages hold countries in score_home / away
        hs, as_ = to_int(r.get("score_home")), to_int(r.get("score_away"))
    row["home_sets"], row["away_sets"] = hs, as_
    row["set_scores"] = text(r.get("set_scores"))
    row["status_code"] = text(r.get("status"))
    return row


def add_self_entry(row: dict, e: tuple) -> None:
    """The page's own entry of its head-to-head feed, oriented as the page (home / away)."""
    (_, kc, kf, kh, kd, ac, uq, uo, kj, kk, ue, ug, ku, kt, winner, gh, ga) = e
    swapped = bool(row["home_name"]) and kj != row["home_name"] and kk == row["home_name"]
    if swapped:
        uq, uo, kj, kk, ue, ug, ku, kt, gh, ga = uo, uq, kk, kj, ug, ue, kt, ku, ga, gh
        winner = {"home": "away", "away": "home"}.get(winner, winner)
    row.update(e_found=True, e_swapped=swapped, e_ts=kc, e_tournament=kf, e_country=kh, e_surface=kd, e_status=ac,
               e_home_id=uq, e_away_id=uo, e_home_name=kj, e_away_name=kk, e_home_slug=ue, e_away_slug=ug,
               e_home_sets=ku, e_away_sets=kt, e_winner=winner, e_gender_home=gh, e_gender_away=ga)


INT_COLS = {"line", "start_ts", "end_ts", "home_sets", "away_sets", "e_ts", "e_home_sets", "e_away_sets"}
BOOL_COLS = {"e_found", "e_swapped"}


def typed(frame: pd.DataFrame) -> pd.DataFrame:
    """One dtype per column whatever a shard holds, so shards concatenate cleanly."""
    for col in frame.columns:
        if col in INT_COLS:
            frame[col] = pd.to_numeric(frame[col], errors="coerce").astype("Int64")
        elif col in BOOL_COLS:
            frame[col] = frame[col].fillna(False).astype(bool)
        else:
            frame[col] = frame[col].astype("string")
    return frame


def write_entries(buf: dict, path: Path) -> int:
    cols = list(zip(*buf.values())) if buf else [[] for _ in ENTRY_COLS]
    types = {"kc": pa.int64(), "ku": pa.int64(), "kt": pa.int64()}
    table = pa.table({c: pa.array(list(v), type=types.get(c, pa.string())) for c, v in zip(ENTRY_COLS, cols)})
    pq.write_table(table, path, compression="zstd")
    return len(buf)


def scan_file(job: tuple[str, str]) -> dict:
    """Read one file: page rows (and rows without an id, kept for a coverage check) to one shard, the
    distinct feed entries from SCOPE_FROM on to one or more shards. Returns counts and shard paths."""
    path, work = Path(job[0]), Path(job[1])
    kind = file_kind(path)
    rel = f"{path.parent.name}/{path.name}"
    stem = f"{path.parent.name}__{path.name.split('.')[0]}"
    c = Counter()
    pages, noid, seen, buf, shards = [], [], set(), {}, []
    rounds, statuses, set_forms = Counter(), Counter(), Counter()
    started = time.time()
    with open_text(path) as handle:
        for line_no, line in enumerate(handle):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                c["unparseable"] += 1
                continue
            c["records"] += 1
            if kind == "layer3":
                c["skipped_layer3_no_start_time"] += 1
                continue
            if kind in ("data", "bruteforce"):
                c["no_match_id"] += 1
                if text(r.get("match_date")) >= SCOPE_FROM_DATE:
                    noid.append({"kind": kind, "file": rel, "match_date": text(r.get("match_date")),
                                 "category": text(r.get("category")), "tournament_name": text(r.get("tournament_name")),
                                 "tournament_slug": text(r.get("tournament_slug")),
                                 "home_name": text(r.get("home_player")), "away_name": text(r.get("away_player")),
                                 "score_home": text(r.get("score_home")), "score_away": text(r.get("score_away")),
                                 "round_raw": text(r.get("round_raw")) or text(r.get("round"))})
                continue
            row = page_row(kind, rel, line_no, r)
            if not row["fs_match_id"]:
                c["no_match_id"] += 1
                continue
            c["with_match_id"] += 1
            c["with_start_time"] += row["start_ts"] is not None
            rounds[row["round_raw"]] += 1
            statuses[row["status_code"]] += 1
            set_forms[re.sub(r"\d+", "9", row["set_scores"] or "")] += 1
            blob = r.get("h2h_json") or ""
            if blob:
                c["with_feed"] += 1
                for kp, chunk in feed_entries(blob):
                    c["feed_entries_seen"] += 1
                    if kp == row["fs_match_id"] and not row["e_found"]:
                        add_self_entry(row, entry_tuple(entry_of(chunk)))
                    if kp in seen:
                        continue
                    seen.add(kp)
                    e = entry_tuple(entry_of(chunk))
                    if e[1] is None or e[1] < SCOPE_FROM_TS:
                        continue
                    buf[kp] = e
                    if len(buf) >= ENTRY_FLUSH:
                        shard = work / f"{stem}__entries_{len(shards):03d}.parquet"
                        c["feed_entries_written"] += write_entries(buf, shard)
                        shards.append(str(shard))
                        buf = {}
                c["self_entry_found"] += row["e_found"]
                if row["e_found"] and row["start_ts"] is not None and row["e_ts"] != row["start_ts"]:
                    c["self_entry_start_differs"] += 1
            in_scope = (row["start_ts"] or 0) >= SCOPE_FROM_TS or (row["match_date"] or "") >= SCOPE_FROM_DATE
            if in_scope:
                pages.append(row)
    if buf:
        shard = work / f"{stem}__entries_{len(shards):03d}.parquet"
        c["feed_entries_written"] += write_entries(buf, shard)
        shards.append(str(shard))
    c["distinct_feed_ids"] = len(seen)
    page_shard = work / f"{stem}__pages.parquet"
    typed(pd.DataFrame(pages, columns=REC_COLS)).to_parquet(page_shard, index=False)
    noid_shard = None
    if noid:
        noid_shard = work / f"{stem}__noid.parquet"
        typed(pd.DataFrame(noid, columns=NOID_COLS)).to_parquet(noid_shard, index=False)
    return {"file": rel, "kind": kind, "bytes_on_disk": path.stat().st_size, "counts": dict(c),
            "pages_in_scope": len(pages), "page_shard": str(page_shard), "noid_shard": str(noid_shard) if noid_shard else None,
            "entry_shards": shards, "rounds": dict(rounds), "statuses": dict(statuses), "set_forms": dict(set_forms.most_common(40)),
            "seconds": round(time.time() - started, 1)}


def parse_all(work: Path, workers: int = 4, log=print) -> list[dict]:
    """scan_file over every file, largest first, with ``workers`` processes."""
    work.mkdir(parents=True, exist_ok=True)
    files = sorted(data_files(), key=lambda p: -p.stat().st_size)
    log(f"parsing {len(files)} files ({sum(p.stat().st_size for p in files) / 1e9:.2f} GB on disk) with {workers} workers")
    out = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for res in pool.map(scan_file, [(str(p), str(work)) for p in files]):
            out.append(res)
            log(f"  {res['file']}: {res['counts'].get('records', 0):,} records, {res['pages_in_scope']:,} pages in scope, "
                f"{res['counts'].get('feed_entries_written', 0):,} new feed entries, {res['seconds']}s")
    return out


def load_or_parse(work: Path, workers: int = 4, reparse: bool = False, log=print) -> list[dict]:
    """The per-file results of parse_all, reused from ``work``/parse_results.json when every shard it
    names still exists and the file list is unchanged (``reparse`` forces a new parse)."""
    index = work / "parse_results.json"
    files = {f"{p.parent.name}/{p.name}": p.stat().st_size for p in data_files()}
    if index.exists() and not reparse:
        results = json.loads(index.read_text(encoding="utf-8"))
        shards = [s for r in results for s in [r["page_shard"], r["noid_shard"], *r["entry_shards"]] if s]
        same_files = {r["file"]: r["bytes_on_disk"] for r in results} == files
        if same_files and all(Path(s).exists() for s in shards):
            log(f"reusing the parse of {len(results)} files in {work}")
            return results
    results = parse_all(work, workers, log)
    index.write_text(json.dumps(results, indent=1), encoding="utf-8")
    return results


# ------------------------------------------------------------------------------------------------
# Merging the shards

ROUND_CODES = {
    "final": "F", "f": "F", "semi-finals": "SF", "semifinals": "SF", "semi-final": "SF", "sf": "SF",
    "quarter-finals": "QF", "quarterfinals": "QF", "quarter-final": "QF", "qf": "QF",
    "1/8-finals": "R16", "1/16-finals": "R32", "1/32-finals": "R64", "1/64-finals": "R128",
    "round of 16": "R16", "round of 32": "R32", "round of 64": "R64", "round of 128": "R128",
    "r16": "R16", "r32": "R32", "r64": "R64", "r128": "R128",
    "3rd place": "BR", "3rd place final": "BR", "bronze medal": "BR",
}


def round_code(raw) -> str | None:
    """A Flashscore round label as Stage 0's round code; None where it cannot be read."""
    t = raw.strip().lower() if isinstance(raw, str) else ""
    if not t:
        return None
    if t in ROUND_CODES:
        return ROUND_CODES[t]
    m = re.search(r"qualification\s*[-:]?\s*(?:round\s*)?(\d)", t) or re.fullmatch(r"q(\d)", t)
    if m:
        return f"Q{m.group(1)}"
    if "group" in t or "round robin" in t:
        return "RR"
    return None


def read_shards(paths: list[str], columns: list[str] | None = None) -> pd.DataFrame:
    """Shards concatenated, text columns as pandas' default string dtype (missing is NaN, comparisons False)."""
    frames = [pd.read_parquet(p, columns=columns) for p in paths if p]
    frames = [f for f in frames if len(f)]
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns or [])
    for col in out.columns:
        if isinstance(out[col].dtype, pd.StringDtype):
            out[col] = out[col].astype("str")
    return out


def merge_entries(results: list[dict], log=print) -> tuple[pd.DataFrame, dict]:
    """One row per feed entry id: a finished version first (status 3, 8, 9 or 54), and how many ids
    carry more than one start time across feeds."""
    paths = [s for r in results for s in r["entry_shards"]]
    e = read_shards(paths)
    log(f"feed entries read from {len(paths)} shards: {len(e):,} rows (distinct within each file)")
    stats = {"rows_distinct_within_files": int(len(e))}
    kc_versions = e[["kp", "kc"]].drop_duplicates().groupby("kp").size()
    stats["ids_with_more_than_one_start_time"] = int((kc_versions > 1).sum())
    e["fin"] = e["ac"].isin(list(STATUS_CODES)).astype("int8")
    e = e.sort_values(["kp", "fin"], ascending=[True, False], kind="mergesort").drop_duplicates("kp")
    stats["distinct_ids"] = int(len(e))
    return e.drop(columns="fin").reset_index(drop=True), stats


def build_records(results: list[dict], log=print) -> tuple[pd.DataFrame, dict]:
    """The deduplicated table of Flashscore matches from SCOPE_FROM on, keyed by fs_match_id."""
    pages = read_shards([r["page_shard"] for r in results])
    redo = pages["kind"].eq("daily") & pages["country"].isna()          # shards written before the stage-aware regex
    if redo.any():
        parts = pages.loc[redo, "tournament_name"].map(split_daily_tournament)
        pages.loc[redo, "tournament_name"] = parts.str[0]
        pages.loc[redo, "country"] = parts.str[1]
        pages.loc[redo, "surface"] = parts.str[2]
        pages.loc[redo, "round_raw"] = pages.loc[redo, "round_raw"].where(pages.loc[redo, "round_raw"].fillna("").ne(""),
                                                                          parts.str[3])
    pages["prio"] = pages["kind"].map(KIND_PRIORITY).astype("int8")
    log(f"pages in scope: {len(pages):,} rows, {pages['fs_match_id'].nunique():,} distinct ids")
    stats = {"page_rows_in_scope": int(len(pages)), "page_ids_in_scope": int(pages["fs_match_id"].nunique()),
             "page_rows_by_kind": pages["kind"].value_counts().to_dict()}
    ts = pages.dropna(subset=["start_ts"]).groupby("fs_match_id")["start_ts"].nunique()
    stats["page_ids_with_more_than_one_start_time"] = int((ts > 1).sum())
    pages = pages.sort_values(["fs_match_id", "prio", "file", "line"], kind="mergesort")
    kinds = pages.groupby("fs_match_id")["kind"].agg(lambda s: ",".join(sorted(set(s), key=KIND_PRIORITY.get)))
    first = pages.groupby("fs_match_id", sort=False).first()          # first non-missing value per column, by priority
    first["kinds"] = kinds
    entries, estats = merge_entries(results, log)
    stats["feed_entries"] = estats
    ent = entries.set_index("kp")
    rec = first.reset_index()
    # page ids that also appear as feed entries elsewhere: fill what the page's own entry lacks
    rec = rec.merge(ent.add_prefix("x_"), left_on="fs_match_id", right_index=True, how="left")
    has_x = rec["x_kc"].notna()
    stats["pages_without_own_entry_but_in_other_feeds"] = int((~rec["e_found"].astype(bool) & has_x).sum())
    disagree = rec["start_ts"].notna() & has_x & (rec["start_ts"] != rec["x_kc"])
    stats["pages_whose_start_differs_from_other_feeds"] = int(disagree.sum())
    out = pd.DataFrame({
        "fs_match_id": rec["fs_match_id"],
        "origin": rec["kind"].map({"year": "year_file", "stats": "stats_file", "h2h": "h2h_page", "daily": "daily_board"}),
        "kinds": rec["kinds"],
        "in_feeds": has_x | rec["e_found"].astype(bool),
        "start_ts": rec["start_ts"].fillna(rec["e_ts"]).fillna(rec["x_kc"]),
        "end_ts": rec["end_ts"],
        "board_date": rec["board_date"],
        "category": rec["category"].replace({"": None}),
        "tournament_name": rec["tournament_name"].replace({"": None}).fillna(rec["e_tournament"].replace({"": None}))
                           .fillna(rec["x_kf"].replace({"": None})),
        "tournament_slug": rec["tournament_slug"].replace({"": None}),
        "country": rec["country"].replace({"": None}).fillna(rec["e_country"].replace({"": None}))
                   .fillna(rec["x_kh"].replace({"": None})),
        "surface": rec["surface"].replace({"": None}).fillna(rec["e_surface"].replace({"": None})),
        "round_raw": rec["round_raw"].replace({"": None}),
        "home_name": rec["home_name"], "away_name": rec["away_name"],
        "home_fs_id": rec["e_home_id"], "away_fs_id": rec["e_away_id"],
        "home_slug": rec["e_home_slug"], "away_slug": rec["e_away_slug"],
        "home_sets": rec["home_sets"].fillna(rec["e_home_sets"]),
        "away_sets": rec["away_sets"].fillna(rec["e_away_sets"]),
        "set_scores": rec["set_scores"].replace({"": None}),
        # pages always say 3 (finished); the feed's own entry says 8 (retired), 9 (walkover) or 54
        "status_code": rec["e_status"].replace({"": None}).fillna(rec["status_code"].replace({"": None}))
                       .fillna(rec["x_ac"].replace({"": None})),
        "winner_marker": rec["e_winner"].replace({"": None}),
        "g_home": rec["e_gender_home"], "g_away": rec["e_gender_away"],
        "src_file": rec["file"],
    })
    # page ids whose own entry was missing but which other feeds list: take ids, slugs and winner from there,
    # oriented by name
    miss = ~rec["e_found"].astype(bool) & has_x
    same = miss & (rec["x_kj"] == rec["home_name"])
    flip = miss & ~same & (rec["x_kk"] == rec["home_name"])
    for col, a, b in (("home_fs_id", "x_uq", "x_uo"), ("away_fs_id", "x_uo", "x_uq"), ("home_slug", "x_ue", "x_ug"),
                      ("away_slug", "x_ug", "x_ue"), ("g_home", "x_g_home", "x_g_away"), ("g_away", "x_g_away", "x_g_home")):
        out.loc[same, col] = rec.loc[same, a]
        out.loc[flip, col] = rec.loc[flip, b]
    out.loc[same, "winner_marker"] = rec.loc[same, "x_winner"]
    out.loc[flip, "winner_marker"] = rec.loc[flip, "x_winner"].map({"home": "away", "away": "home"})
    stats["pages_oriented_from_other_feeds"] = {"same": int(same.sum()), "swapped": int(flip.sum()),
                                                "names_differ": int((miss & ~same & ~flip).sum())}
    # feed entries that have no page anywhere
    only = entries[~entries["kp"].isin(set(rec["fs_match_id"]))]
    feed = pd.DataFrame({
        "fs_match_id": only["kp"], "origin": "feed_entry", "kinds": "feed", "in_feeds": True,
        "start_ts": only["kc"], "end_ts": pd.NA, "board_date": None, "category": None,
        "tournament_name": only["kf"].replace({"": None}), "tournament_slug": None,
        "country": only["kh"].replace({"": None}), "surface": only["kd"].replace({"": None}), "round_raw": None,
        "home_name": only["kj"], "away_name": only["kk"], "home_fs_id": only["uq"], "away_fs_id": only["uo"],
        "home_slug": only["ue"], "away_slug": only["ug"], "home_sets": only["ku"], "away_sets": only["kt"],
        "set_scores": None, "status_code": only["ac"].replace({"": None}), "winner_marker": only["winner"].replace({"": None}),
        "g_home": only["g_home"], "g_away": only["g_away"], "src_file": None})
    stats["feed_entries_without_a_page"] = int(len(feed))
    allm = pd.concat([out, feed], ignore_index=True)
    allm = finish(allm)
    return allm, stats


JUNIOR_NAME = re.compile(r"^J\d{1,3}\b|\bjunior|\bboys\b|\bgirls\b|\bU1[2468]\b|\bgrade\s*[a-c1-5]\b", re.I)
ITF_MEN = re.compile(r"^M\d{2,3}\b")
ITF_WOMEN = re.compile(r"^W\d{2,3}\b")
SLAM = re.compile(r"^(?:Australian Open|French Open|Roland Garros|Wimbledon|US Open)\b", re.I)
EXHIBITION = re.compile(r"Others matches|UTR Pro|Exo-Tennis|Exhibition|Tie Break Tens|\bUTS\b|Ultimate Tennis Showdown|"
                        r"World Tennis League|International Tennis Series|Mubadala|World Tennis Championship|"
                        r"Kooyong|Boodles|Battle of the|Adria Tour|Diriyah|Six Kings|Champions Battle|"
                        r"Credit One Bank Invitational|All American|Young Kings|Altec Styslinger|Matchplay|"
                        r"A Day at the Drive|One Night with|Fast4|World Tennis Challenge|Liga Mapfre|"
                        r"Challenge Elite FFT|Masters France|Legends|Showdown|Charity", re.I)
TEAM = re.compile(r"Davis Cup|Fed Cup|Billie Jean King Cup|BJK Cup|ATP Cup|United Cup|Laver Cup|Hopman Cup|Olympic|"
                  r"World Team|Team Cup", re.I)


def finish(m: pd.DataFrame) -> pd.DataFrame:
    """Typed columns, winner, status, round code, singles / junior flags, a category guess from names,
    and gender (from the category, the ITF name prefix, Flashscore's default silhouettes, then the players'
    other matches)."""
    m = m.copy()
    m["start_utc"] = pd.to_datetime(pd.to_numeric(m["start_ts"], errors="coerce"), unit="s", utc=True)
    m["end_utc"] = pd.to_datetime(pd.to_numeric(m["end_ts"], errors="coerce"), unit="s", utc=True)
    m["board_date"] = pd.to_datetime(m["board_date"], errors="coerce")
    for c in ("home_sets", "away_sets"):
        m[c] = pd.to_numeric(m[c], errors="coerce").astype("Int64")
    by_sets = np.where(m["home_sets"].fillna(-1) > m["away_sets"].fillna(-1), "home",
                       np.where(m["away_sets"].fillna(-1) > m["home_sets"].fillna(-1), "away", None))
    m["winner"] = m["winner_marker"].where(m["winner_marker"].notna(), pd.Series(by_sets, index=m.index))
    m["winner_disagrees_with_sets"] = m["winner_marker"].notna() & pd.notna(by_sets) & (m["winner_marker"] != by_sets)
    code = m["status_code"].astype("object").where(m["status_code"].notna(), None)
    m["status"] = [STATUS_CODES.get(s, "other") if isinstance(s, str) and s else None for s in code]
    m["round"] = m["round_raw"].map(round_code)
    names = m["home_name"].fillna("") + " " + m["away_name"].fillna("")
    tn = m["tournament_name"].fillna("")
    m["is_doubles"] = names.str.contains("/", regex=False) | m["category"].fillna("").str.contains("doubles")
    m["is_junior"] = tn.str.contains(JUNIOR_NAME) | m["category"].fillna("").str.contains("boys|girls")
    m["is_exhibition"] = tn.str.contains(EXHIBITION)
    m["category_guess"] = np.select(
        [tn.str.contains(ITF_MEN) | tn.str.contains(ITF_WOMEN), tn.str.contains(SLAM), tn.str.contains(TEAM),
         m["category"].fillna("").str.startswith("challenger")],
        ["ITF", "GS", "TEAM", "CH"], None)
    m = infer_gender(m)
    keep = ["fs_match_id", "origin", "kinds", "in_feeds", "start_utc", "end_utc", "board_date", "gender", "gender_basis",
            "category", "category_guess", "tournament_name", "tournament_slug", "country", "surface", "round_raw",
            "round", "home_name", "away_name", "home_fs_id", "away_fs_id", "home_slug", "away_slug", "winner",
            "home_sets", "away_sets", "set_scores", "status", "status_code", "winner_disagrees_with_sets",
            "is_doubles", "is_junior", "is_exhibition", "src_file"]
    return m[keep].sort_values(["start_utc", "fs_match_id"], kind="mergesort").reset_index(drop=True)


CATEGORY_GENDER = {"atp": "men", "challenger-men": "men", "itf-men": "men", "wta": "women", "challenger-women": "women",
                   "itf-women": "women", "boys": "men", "girls": "women"}


def infer_gender(m: pd.DataFrame) -> pd.DataFrame:
    cat = m["category"].fillna("")
    g = pd.Series(None, index=m.index, dtype="object")
    basis = pd.Series(None, index=m.index, dtype="object")
    for prefix, gender in CATEGORY_GENDER.items():
        hit = g.isna() & cat.str.startswith(prefix + "-")
        g[hit], basis[hit] = gender, "category"
    tn = m["tournament_name"].fillna("")
    for rx, gender in ((ITF_MEN, "men"), (ITF_WOMEN, "women")):
        hit = g.isna() & tn.str.contains(rx)
        g[hit], basis[hit] = gender, "itf_name_prefix"
    sil = pd.Series(np.where(m["g_home"].eq("m") | m["g_away"].eq("m"), "men",
                             np.where(m["g_home"].eq("w") | m["g_away"].eq("w"), "women", None)), index=m.index)
    conflict = (m["g_home"].eq("m") | m["g_away"].eq("m")) & (m["g_home"].eq("w") | m["g_away"].eq("w"))
    hit = g.isna() & sil.notna() & ~conflict
    g[hit], basis[hit] = sil[hit], "default_silhouette"
    # players' genders from their labelled matches, then every match of a labelled player
    lab = pd.concat([pd.DataFrame({"pid": m.loc[g.notna(), c], "g": g[g.notna()]}) for c in ("home_fs_id", "away_fs_id")])
    lab = lab[lab["pid"].fillna("") != ""]
    counts = lab.groupby(["pid", "g"]).size().unstack(fill_value=0)
    for col in ("men", "women"):
        if col not in counts:
            counts[col] = 0
    player = pd.Series(np.where(counts["men"] > 0, np.where(counts["women"] > 0, "conflict", "men"), "women"),
                       index=counts.index)
    ph, pa_ = m["home_fs_id"].map(player), m["away_fs_id"].map(player)
    via = pd.Series(np.where(ph.isin(["men", "women"]) & (pa_.isna() | (pa_ == ph)), ph,
                             np.where(pa_.isin(["men", "women"]) & ph.isna(), pa_, None)), index=m.index)
    hit = g.isna() & via.notna()
    g[hit], basis[hit] = via[hit], "players_other_matches"
    m["gender"], m["gender_basis"] = g, basis
    return m
