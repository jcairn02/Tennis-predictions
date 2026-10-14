"""Hawk-Eye Court Vision at the Australian Open and Roland Garros: the GitHub copy hawkilol/tennisSlamBallTracking.

What the repository holds, at commit f97a9b3 (8 Apr 2025; still the latest on 29 Sep 2026):
    players_matches_catalogue/catalogue_all_matches_available.csv  2,027 singles matches: AO 2020-2024, RG 2019-2024
    pbp_data_csvs/<slam>/<tour>/*_pbp.csv        one row per serve (a fault and the second serve are two rows),
                                                 64 columns, made from the JSON by the repository's src/process.py
    all_json/<slam>/<tour>/*_tracking_data.json  the Slam site's Court Vision document of the match: per point
                                                 49 fields and ``trajectoryData``, the ball's hit, peak, net and
                                                 bounce positions for every stroke of the rally (3.3 GB in all)
    all_json/ranking_history/atp/*.json          ATP ranking histories of 266 players (not fetched)

The files were scraped from the two Slams' match centres by the repository's author; the code is GPL-3.0 and
the data carry no licence. The data map's gap slam_points_ao_rg needs 2022-2024, so the JSON of those years is
fetched by default (``--json-years``).

Raw: data/raw/public_dump/slam_ball_tracking/, the repository's paths kept, the JSON gzipped on arrival
(``<name>.json.gz``), and _receipts.jsonl: URL, time, status, bytes, SHA-256 of the body and its git blob SHA-1,
checked against the tree. A file that src/eda/gap_sources/fetch_hawkilol.py already fetched and verified into
data/raw/gap_sources/hawkilol/ is copied from there instead of downloaded again (``copied_from`` in its receipt).

Staged (data/dump/points/slam_ball_tracking/; strings throughout, as the rest of the dump; a match is identified by
``slam``, ``tour``, ``year`` and the catalogue's ``match_id``, which repeats every year at Roland Garros):
    matches.parquet                    the catalogue verbatim, with each match's files and counts (n_csv_*, n_json_*)
    points/<slam>_<year>.parquet       every CSV row verbatim, keyed by match
    json_matches.parquet               each JSON's match-level fields (players, statistics as JSON text)
    json_points/<slam>_<year>.parquet  every JSON point record: scalar fields verbatim, nested ones as JSON text
    shots/<slam>_<year>.parquet        one row per ``trajectoryData`` position: point, order, position, x, y, z

Usage:
    ./python.sh -m src.ingest.public_dump.slam_ball_tracking                     # CSVs, and the JSON of 2022-2024
    ./python.sh -m src.ingest.public_dump.slam_ball_tracking --json-years all    # every match's JSON (3.3 GB)
    ./python.sh -m src.ingest.public_dump.slam_ball_tracking --stage-only        # rebuild the tables from raw
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.ingest.public_dump import common as C

SOURCE = "slam_ball_tracking"
REPO = "hawkilol/tennisSlamBallTracking"
PINNED_COMMIT = "f97a9b31e64eab8485474398414dd26523871f64"  # 8 Apr 2025, the latest on 29 Sep 2026
RAW_URL = "https://raw.githubusercontent.com/{repo}/{commit}/{path}"
TREE_URL = "https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
MIRROR = C.PROJECT_ROOT / "data" / "raw" / "gap_sources" / "hawkilol"
STUDY_DIR = C.PROJECT_ROOT / "data" / "studies" / "ao_rg_points"
META = {"README.md", "LICENSE", "src/process.py", "src/search_utils.py"}
SLAM = {"australian_open": "AO", "roland_garros": "RG"}
JSON_NAME = re.compile(r"(20\d{2})_([A-Z]{2}\d{3})_tracking_data\.json$")
CSV_NAME = re.compile(r"^(atp|wta)_(australian_open|roland_garros)_(20\d{2})_([A-Z]{2}\d{3})_pbp\.csv$")
MATCH_KEYS = ["match_id", "slam", "tour", "year"]
TRACKED = 0.9  # as lane A (src/eda/gap_sources/hawkilol_matches.py): a match is tracked when this share of points is


# --------------------------------------------------------------------------------------
# the plan
# --------------------------------------------------------------------------------------
def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def parse_years(value: str) -> set[int] | None:
    """'2022-2024' -> {2022, 2023, 2024}; '2019,2024' -> {2019, 2024}; 'all' -> None (every year); 'none' -> set()."""
    value = (value or "").strip().lower()
    if value == "all":
        return None
    if value in ("", "none"):
        return set()
    years = set()
    for part in value.split(","):
        lo, _, hi = part.partition("-")
        years |= set(range(int(lo), int(hi or lo) + 1))
    return years


def kind_of(path: str, json_years: set[int] | None) -> str | None:
    """What a repository path is to this adapter ('meta', 'catalogue', 'csv', 'json'), or None when not fetched."""
    if path in META:
        return "meta"
    if path.startswith("players_matches_catalogue/") and path.endswith(".csv"):
        return "catalogue"
    if path.startswith("pbp_data_csvs/") and path.endswith(".csv"):
        return "csv"
    m = JSON_NAME.search(path)
    if path.startswith(("all_json/australian_open/", "all_json/roland_garros/")) and m:
        return "json" if json_years is None or int(m.group(1)) in json_years else None
    return None


def raw_dest(path: str) -> Path:
    return C.raw_path(SOURCE, path + (".gz" if path.endswith(".json") else ""))


def load_tree(commit: str, receipts: C.Receipts) -> list[dict]:
    """The repository's blobs at ``commit``, from the GitHub API (or the mirror's copy if the API refuses)."""
    name = f"_tree_{commit[:12]}.json"
    dest = C.raw_path(SOURCE, name)
    rec = C.download(TREE_URL.format(repo=REPO, commit=commit), dest, receipts, name=name, validator=C.not_html)
    if rec.get("error"):
        local = MIRROR / f"_tree_{commit[:7]}.json"
        if not local.exists():
            raise RuntimeError(f"could not list the repository tree: {rec['error']}")
        body = local.read_bytes()
        dest.write_bytes(body)
        receipts.record({"name": name, "url": TREE_URL.format(repo=REPO, commit=commit), "dest": C.rel(dest),
                         "retrieved_at": C.utc_now_iso(), "copied_from": C.rel(local), "bytes": len(body),
                         "sha256": C.sha256_bytes(body), "note": f"API answer was: {rec['error']}"})
    tree = json.loads(dest.read_text(encoding="utf-8"))
    if tree.get("truncated"):
        raise RuntimeError("the tree listing is truncated")
    return [e for e in tree["tree"] if e["type"] == "blob"]


# --------------------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------------------
def mirror_times() -> dict[str, str]:
    """When fetch_hawkilol.py fetched the mirror's files (one time for its whole run)."""
    path = MIRROR / f"_receipt_{PINNED_COMMIT[:7]}.json"
    if not path.exists():
        return {}
    receipt = json.loads(path.read_text(encoding="utf-8"))
    return {f["path"]: receipt["retrieved_at"] for f in receipt.get("per_file") or [] if f.get("blob_ok")}


def fetch_file(entry: dict, commit: str, receipts: C.Receipts, mirrored: dict[str, str], refresh: bool) -> dict:
    path, blob = entry["path"], entry["sha"]
    dest = raw_dest(path)
    previous = receipts.get(path)
    if previous and not previous.get("error") and dest.exists() and not refresh:
        return {**previous, "skipped": True}
    url = RAW_URL.format(repo=REPO, commit=commit, path=path)
    receipt = {"name": path, "url": url, "dest": C.rel(dest), "commit": commit, "git_blob_sha1": blob}
    body = None
    local = MIRROR / path
    if path in mirrored and local.exists():
        data = local.read_bytes()
        if git_blob_sha1(data) == blob:
            body = data
            receipt.update(retrieved_at=mirrored[path], copied_from=C.rel(local), copied_at=C.utc_now_iso(),
                           status=200)
    if body is None:
        receipt["retrieved_at"] = C.utc_now_iso()
        last_error = None
        for attempt in range(3):
            try:
                response = C.session().get(url, timeout=180)
                receipt["status"] = response.status_code
                if response.status_code == 200:
                    body = response.content
                    break
                last_error = f"HTTP {response.status_code}"
            except Exception as err:  # requests' exception family
                last_error = f"{type(err).__name__}: {err}"
            time.sleep(3 * (attempt + 1))
        if body is None:
            receipt["error"] = last_error
            return receipts.record(receipt)
        if git_blob_sha1(body) != blob:
            receipt["error"] = "git blob SHA-1 differs from the tree"
            return receipts.record(receipt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    part.write_bytes(gzip.compress(body) if dest.suffix == ".gz" else body)
    os.replace(part, dest)
    receipt.update(bytes=len(body), sha256=C.sha256_bytes(body), blob_ok=True, compressed=dest.suffix == ".gz")
    return receipts.record(receipt)


# --------------------------------------------------------------------------------------
# reading
# --------------------------------------------------------------------------------------
def s(value) -> str | None:
    """Verbatim string form: None stays None, booleans TRUE/FALSE, nested values JSON text."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def match_key(m) -> tuple:
    """A match's unique key: the catalogue's match_id repeats from year to year at Roland Garros ('SM001'), while
    the Australian Open's carries the year ('2022_MS101'); slam, tour and year make it unique."""
    return m.slam, m.tour, str(m.year), m.match_id


def read_json_doc(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)["courtVisionData"][0]


def catalogue_files(catalogue: pd.DataFrame, tree_paths: set[str]) -> pd.DataFrame:
    """The catalogue with each match's slam, tour, code and its CSV and JSON paths in the repository."""
    cat = catalogue.copy()
    cat["slam"] = cat["tournament"].map(SLAM)
    cat["tour"] = cat["league"].map({"atp": "M", "wta": "W"})
    cat["code"] = cat["match_id"].str.split("_").str[-1]
    cat["pbp_file"] = [f"pbp_data_csvs/{t}/{lg}/{lg}_{t}_{y}_{c}_pbp.csv"
                       for t, lg, y, c in zip(cat["tournament"], cat["league"], cat["year"], cat["code"])]
    json_by_key = {}
    for p in tree_paths:
        m = JSON_NAME.search(p)
        if p.startswith("all_json/") and m:
            parts = p.split("/")
            json_by_key[(parts[1], parts[2], m.group(1), m.group(2))] = p
    cat["json_file"] = [json_by_key.get((t, lg, str(y), c))
                        for t, lg, y, c in zip(cat["tournament"], cat["league"], cat["year"], cat["code"])]
    return cat


# --------------------------------------------------------------------------------------
# staging
# --------------------------------------------------------------------------------------
def csv_rows(group: pd.DataFrame, receipts: C.Receipts, header: list[str], counts: dict):
    """Rows of every CSV of one slam-year, in the order of ``header`` (the union of the files' headers)."""
    for m in group.itertuples(index=False):
        path = raw_dest(m.pbp_file)
        if not path.exists():
            continue
        rec = receipts.get(m.pbp_file) or {}
        frame = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[])
        keys = frame[["set_num", "game_num", "point_num"]].astype(str).agg("_".join, axis=1)
        last = ~keys.duplicated(keep="last")  # the final row of each point (its highest serve)
        tracked = frame.loc[last, "is_track_avail"].eq("True")
        counts[match_key(m)] = {"n_csv_rows": len(frame), "n_csv_points": int(last.sum()),
                                "csv_track_share": round(float(tracked.mean()), 4) if last.any() else None}
        base = [m.match_id, m.slam, m.tour, str(m.year), m.pbp_file, rec.get("sha256")]
        cols = [c for c in header[len(base):]]
        for values in frame.reindex(columns=cols).itertuples(index=False):
            yield base + [None if v is None or (isinstance(v, float) and v != v) else v for v in values]


def stage(receipts: C.Receipts, cat: pd.DataFrame) -> dict:
    now = C.utc_now_iso()
    out = {"points": [], "json_points": [], "shots": []}
    counts: dict[str, dict] = {}
    json_counts: dict[str, dict] = {}
    json_match_rows = []
    for (slam, year), group in cat.groupby(["slam", "year"], sort=True):
        tag = f"{slam}_{year}"
        # per-point CSVs
        header_union: list[str] = []
        for p in group["pbp_file"]:
            path = raw_dest(p)
            if path.exists():
                with path.open(encoding="utf-8") as handle:
                    for col in handle.readline().rstrip("\r\n").split(","):
                        if col not in header_union:
                            header_union.append(col)
        header = MATCH_KEYS + ["source_file", "source_sha256"] + header_union
        prov = C.Provenance(SOURCE, C.rel(C.raw_path(SOURCE, "pbp_data_csvs")), None, now, {"commit": PINNED_COMMIT})
        stats = C.stage_rows(header, enumerate(csv_rows(group, receipts, header, counts), 1),
                             C.dump_path("points", SOURCE, "points", f"{tag}.parquet"), prov)
        out["points"].append({"file": stats["dest"], "rows": stats["rows"], "bytes": stats["bytes"]})
        # JSON documents, where fetched
        docs = [(m, raw_dest(m.json_file)) for m in group.itertuples(index=False)
                if isinstance(m.json_file, str) and raw_dest(m.json_file).exists()]
        if not docs:
            continue
        point_fields: list[str] = []
        for m, path in docs[:5]:
            for rec in read_json_doc(path).get("pointsData", {}).values():
                point_fields += [k for k in rec if k != "trajectoryData" and k not in point_fields]

        def point_rows():
            for m, path in docs:
                doc = read_json_doc(path)
                rec = receipts.get(m.json_file) or {}
                points = doc.get("pointsData") or {}
                tracked = sum(1 for p in points.values() if p.get("trajectoryData"))
                json_counts[match_key(m)] = {"n_json_points": len(points), "n_json_points_tracked": tracked,
                                             "n_json_positions": sum(len(p.get("trajectoryData") or []) for p in points.values())}
                json_match_rows.append([m.match_id, m.slam, m.tour, str(m.year), m.json_file, rec.get("sha256")]
                                       + [s(doc.get(k)) for k in JSON_MATCH_FIELDS])
                for key, p in points.items():
                    extra = sorted(k for k in p if k != "trajectoryData" and k not in point_fields)
                    row = [m.match_id, m.slam, m.tour, str(m.year), key, m.json_file, rec.get("sha256")]
                    row += [s(p.get(k)) for k in point_fields]
                    row.append(json.dumps({k: p[k] for k in extra}, ensure_ascii=False, sort_keys=True) if extra else None)
                    yield row

        def shot_rows():
            for m, path in docs:
                for key, p in (read_json_doc(path).get("pointsData") or {}).items():
                    for n, t in enumerate(p.get("trajectoryData") or [], 1):
                        yield [m.match_id, m.slam, m.tour, str(m.year), key, str(n), s(t.get("position")),
                               s(t.get("x")), s(t.get("y")), s(t.get("z")),
                               json.dumps({k: v for k, v in t.items() if k not in ("position", "x", "y", "z")})
                               if set(t) - {"position", "x", "y", "z"} else None]

        prov = C.Provenance(SOURCE, C.rel(C.raw_path(SOURCE, "all_json")), None, now, {"commit": PINNED_COMMIT})
        header = MATCH_KEYS + ["point_key", "source_file", "source_sha256"] + point_fields + ["other_fields"]
        stats = C.stage_rows(header, enumerate(point_rows(), 1),
                             C.dump_path("points", SOURCE, "json_points", f"{tag}.parquet"), prov)
        out["json_points"].append({"file": stats["dest"], "rows": stats["rows"], "bytes": stats["bytes"]})
        header = MATCH_KEYS + ["point_key", "seq", "position", "x", "y", "z", "other_fields"]
        stats = C.stage_rows(header, enumerate(shot_rows(), 1),
                             C.dump_path("points", SOURCE, "shots", f"{tag}.parquet"), prov)
        out["shots"].append({"file": stats["dest"], "rows": stats["rows"], "bytes": stats["bytes"]})
        C.log(f"[{SOURCE}] staged {tag}: {len(group)} matches, {len(docs)} JSON documents")
    # match-level tables
    if json_match_rows:
        header = MATCH_KEYS + ["source_file", "source_sha256"] + JSON_MATCH_FIELDS
        prov = C.Provenance(SOURCE, C.rel(C.raw_path(SOURCE, "all_json")), None, now, {"commit": PINNED_COMMIT})
        stats = C.stage_rows(header, enumerate(json_match_rows, 1), C.dump_path("points", SOURCE, "json_matches.parquet"), prov)
        out["json_matches"] = {"rows": stats["rows"], "bytes": stats["bytes"]}
    cat_rec = receipts.get("players_matches_catalogue/catalogue_all_matches_available.csv") or {}
    base_cols = [c for c in cat.columns if c not in ("slam", "tour", "code", "pbp_file", "json_file")]
    count_cols = ["n_csv_rows", "n_csv_points", "csv_track_share", "n_json_points", "n_json_points_tracked",
                  "n_json_positions", "tracked"]
    rows = []
    for m in cat.itertuples(index=False):
        key = match_key(m)
        m = m._asdict()
        c = {**counts.get(key, {}), **json_counts.get(key, {})}
        if c.get("n_json_points"):
            c["tracked"] = c["n_json_points_tracked"] / c["n_json_points"] >= TRACKED
        rows.append([s(m[k]) for k in base_cols] + [m["slam"], m["tour"], m["pbp_file"], m["json_file"],
                    s(isinstance(m["json_file"], str) and raw_dest(m["json_file"]).exists())]
                    + [s(c.get(k)) for k in count_cols])
    header = base_cols + ["slam", "tour", "pbp_file", "json_file", "json_on_disk"] + count_cols
    prov = C.Provenance(SOURCE, "players_matches_catalogue/catalogue_all_matches_available.csv",
                        cat_rec.get("sha256"), cat_rec.get("retrieved_at"), {"commit": PINNED_COMMIT})
    stats = C.stage_rows(header, enumerate(rows, 1), C.dump_path("points", SOURCE, "matches.parquet"), prov)
    out["matches"] = {"rows": stats["rows"], "bytes": stats["bytes"]}
    for name in ("points", "json_points", "shots"):
        C.log(f"[{SOURCE}] {name}: {sum(f['rows'] for f in out[name]):,} rows in {len(out[name])} files")
    return out


JSON_MATCH_FIELDS = ["isMatchComplete", "eventType", "courtName", "courtId", "setsCompleted", "pointId",
                     "matchStatus", "playersData", "statsData"]


# --------------------------------------------------------------------------------------
# run
# --------------------------------------------------------------------------------------
def run(args) -> dict:
    started = time.time()
    receipts = C.Receipts(SOURCE)
    commit = PINNED_COMMIT
    json_years = parse_years(args.json_years)
    blobs = load_tree(commit, receipts)
    plan = [(kind_of(e["path"], json_years), e) for e in blobs]
    plan = [(k, e) for k, e in plan if k]
    summary = {"source": SOURCE, "repo": REPO, "commit": commit, "started_at": C.utc_now_iso(),
               "json_years": args.json_years, "planned": dict(Counter(k for k, _ in plan)),
               "planned_bytes": sum(e["size"] for _, e in plan)}
    C.log(f"[{SOURCE}] {len(plan)} files planned ({summary['planned_bytes'] / 1e6:,.0f} MB): {summary['planned']}")
    if not args.stage_only:
        mirrored = mirror_times()
        outcomes = Counter()
        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for rec in pool.map(lambda ke: fetch_file(ke[1], commit, receipts, mirrored, args.refresh), plan):
                how = "error" if rec.get("error") else "held" if rec.get("skipped") else \
                    "copied" if rec.get("copied_from") else "downloaded"
                outcomes[how] += 1
                done += 1
                if done % 250 == 0 or done == len(plan):
                    C.log(f"[{SOURCE}] {done}/{len(plan)} files: {dict(outcomes)}")
        summary["outcomes"] = dict(outcomes)
    errors = [r for r in receipts.all().values() if r.get("error")]
    summary["receipts_with_errors"] = len(errors)
    summary["error_examples"] = [{"name": r["name"], "error": r["error"]} for r in errors[:20]]
    summary["receipts"] = receipt_counts(receipts)
    path = STUDY_DIR / "slam_ball_tracking_summary.json"
    if not args.no_stage:
        catalogue = pd.read_csv(raw_dest("players_matches_catalogue/catalogue_all_matches_available.csv"), dtype=str,
                                keep_default_na=False)
        cat = catalogue_files(catalogue, {e["path"] for e in blobs})
        summary["staged"] = stage(receipts, cat)
    elif path.exists():  # a run that does not stage keeps the record of the last one that did
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous.get("staged"):
            summary["staged"] = previous["staged"]
            summary["staged_by_run_finished_at"] = previous.get("staged_by_run_finished_at") or previous.get("finished_at")
    summary["finished_at"] = C.utc_now_iso()
    summary["seconds"] = round(time.time() - started, 1)
    STUDY_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    return summary


def receipt_counts(receipts: C.Receipts) -> dict:
    """What the receipts record, by kind of file and by how each file arrived, with the first and last fetch time."""
    recs = [r for r in receipts.all().values() if not r["name"].startswith("_tree_")]
    how = Counter(("error" if r.get("error") else "copied from the research copy" if r.get("copied_from")
                   else "downloaded", kind_of(r["name"], None) or "other") for r in recs)
    times = sorted(r["retrieved_at"] for r in recs if r.get("retrieved_at"))
    return {"files": len(recs), "by_how_and_kind": {f"{h}|{k}": n for (h, k), n in sorted(how.items())},
            "bytes": sum(r.get("bytes") or 0 for r in recs), "first_fetch": times[0] if times else None,
            "last_fetch": times[-1] if times else None}


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json-years", default="2022-2024",
                        help="years whose tracking JSON is fetched: '2022-2024' (default), '2019,2024', 'all' or 'none'")
    parser.add_argument("--workers", type=int, default=4, help="parallel downloads (GitHub's raw host)")
    parser.add_argument("--refresh", action="store_true", help="fetch files already held again")
    parser.add_argument("--stage-only", action="store_true", help="no downloads; rebuild the tables from raw")
    parser.add_argument("--no-stage", action="store_true", help="download only")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    summary = run(parser.parse_args())
    C.log(f"[{SOURCE}] done in {summary['seconds']} s; {summary['receipts_with_errors']} receipts with errors")
    return 1 if summary["receipts_with_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
