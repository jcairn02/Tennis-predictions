"""A check that the sources the project depends on are still there and still the same. No data is downloaded: only
status codes, last-change dates, file manifests, licence texts and Software Heritage's archive visits.

Each run appends one line per watched item to data/studies/data_continuity/canary.jsonl and writes the latest run to
canary_latest.json. Flags, compared with the previous run where one exists:
    GONE       the address no longer answers 200 (Sackmann's results repositories have answered 404 since June 2026)
    STALE      nothing changed for longer than the item's allowed gap (in season)
    SHRANK     a manifest lists fewer files, or a file is smaller than at the previous run
    REVISED    a file of an earlier season changed since the previous run (TML corrects old seasons)
    TERMS      the licence statement changed
    UNARCHIVED Software Heritage holds no full visit, or none in the last 180 days
Only open endpoints are asked (GitHub, Hugging Face, Tennis My Life, Software Heritage); sites whose terms forbid
automated access are not.

Run: ./python.sh src/eda/data_continuity/canary.py      (one run is about 25 requests)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.ingest.public_dump import common as C  # noqa: E402

LOG = K.OUT / "canary.jsonl"
LATEST = K.OUT / "canary_latest.json"
ARCHIVE_DAYS = 180

# item, kind, address, allowed gap in days (None: not expected to change)
WATCH = [
    ("sackmann_tennis_atp", "github", "JeffSackmann/tennis_atp", None),
    ("sackmann_tennis_wta", "github", "JeffSackmann/tennis_wta", None),
    ("sackmann_slam_pointbypoint", "github", "JeffSackmann/tennis_slam_pointbypoint", None),
    ("match_charting_project", "github", "JeffSackmann/tennis_MatchChartingProject", 60),
    ("sackmann_archive_mirror", "github", "Aneeshers/tennis-sackmann-archive", None),
    ("tml_github", "github", "Tennismylife/TML-Database", None),
    ("sirgenkii_infotennis", "github", "SirGenkii/infotennis", None),
    ("slam_ball_tracking", "github", "hawkilol/tennisSlamBallTracking", None),
    ("atp_pipeline_handoff", "huggingface", "atlas-polybot/atp-pipeline-handoff", None),
    ("tml_manifest", "tml_manifest", "https://stats.tennismylife.org/api/data-files", 10),
    ("tml_readme_terms", "terms", "https://raw.githubusercontent.com/Tennismylife/TML-Database/master/README.md", None),
    ("tml_site_terms", "terms", "https://stats.tennismylife.org/tennis-match-database", None),
]
TERMS_LINE = re.compile(r"licen[cs]e|commercial|\bMIT\b|creative commons|permission|copyright", re.I)


def get(url: str, timeout: int = 60):
    try:
        return C.session().get(url, timeout=timeout)
    except Exception as err:  # noqa: BLE001 - a failed check is recorded, never raised
        return err


def github(repo: str) -> dict:
    r = get(f"https://api.github.com/repos/{repo}")
    if isinstance(r, Exception):
        return {"status": None, "error": str(r)}
    out = {"status": r.status_code, "url": f"https://github.com/{repo}"}
    if r.status_code == 200:
        d = r.json()
        out.update(pushed_at=d.get("pushed_at"), licence=(d.get("license") or {}).get("spdx_id"),
                   archived=d.get("archived"), size_kb=d.get("size"))
    out["software_heritage"] = heritage(f"https://github.com/{repo}")
    return out


def heritage(origin: str, attempts: int = 3) -> dict:
    """Software Heritage's latest visit with a snapshot, and its latest visit of any kind. Its API is slow and
    sometimes times out (20 s for one query on 6 Oct 2026), so each query is tried up to three times; a query that
    never answers is recorded as an error, not as a missing archive."""
    base = f"https://archive.softwareheritage.org/api/1/origin/{origin}/visit/latest/"
    out = {}
    for label, url in (("last_full", base + "?require_snapshot=true"), ("last_any", base)):
        for attempt in range(attempts):
            r = get(url, timeout=120)
            if isinstance(r, Exception) or r.status_code >= 500:
                out[label] = {"error": type(r).__name__ if isinstance(r, Exception) else f"HTTP {r.status_code}"}
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code == 200:
                d = r.json()
                out[label] = {"date": (d.get("date") or "")[:10], "status": d.get("status")}
            else:
                out[label] = {"http": r.status_code}
            break
        time.sleep(1)
    return out


def huggingface(repo: str) -> dict:
    r = get(f"https://huggingface.co/api/datasets/{repo}")
    if isinstance(r, Exception):
        return {"status": None, "error": str(r)}
    out = {"status": r.status_code, "url": f"https://huggingface.co/datasets/{repo}"}
    if r.status_code == 200:
        d = r.json()
        out.update(last_modified=d.get("lastModified"), sha=d.get("sha"), gated=d.get("gated"),
                   licence=(d.get("cardData") or {}).get("license"))
    return out


TML_HELD = C.RAW_ROOT / "tennis_my_life"
SHRINK_SHARE = 0.02      # allowed shrinkage of a file the project does not hold


def tml_manifest(url: str) -> dict:
    """The manifest, and for each file the project holds the number of Windows line endings in its copy: a
    re-export with Unix line endings shrinks a file by exactly that many bytes (2024.csv on 5 Oct 2026)."""
    r = get(url)
    if isinstance(r, Exception):
        return {"status": None, "error": str(r)}
    out = {"status": r.status_code, "url": url}
    if r.status_code == 200:
        files = r.json().get("files", [])
        out["count"] = len(files)
        out["files"] = {f["name"]: [f.get("mtime"), f.get("size")] for f in files}
        out["newest_mtime"] = max((f.get("mtime") or "" for f in files), default=None)
        out["crlf"] = {n: (TML_HELD / n).read_bytes().count(b"\r\n") for n in out["files"] if (TML_HELD / n).is_file()}
    return out


LICENCE_URL = re.compile(r'\\?"license\\?"\s*:\s*\\?"(https?://[^"\\]+)')
LICENCE_TEXT = re.compile(r"License:\s*(?:<[^>]+>\s*)*([A-Za-z][A-Za-z0-9 .\-]{1,40}?)\s*(?:<|\"|\\|$)")


def terms_statements(text: str, is_html: bool) -> list[str]:
    """The licence statements of a page, normalised so that a rebuilt page with the same terms hashes the same:
    for HTML the declared licence URLs and the text after "License:"; for Markdown the lines that mention a licence,
    commercial use, permission or copyright."""
    if is_html:
        found = {f"license url: {u}" for u in LICENCE_URL.findall(text)}
        found |= {f"license text: {t.strip()}" for t in LICENCE_TEXT.findall(text)}
        return sorted(found)
    return sorted({" ".join(s.split()) for s in text.splitlines() if TERMS_LINE.search(s)})


def terms(url: str) -> dict:
    r = get(url)
    if isinstance(r, Exception):
        return {"status": None, "error": str(r)}
    out = {"status": r.status_code, "url": url}
    if r.status_code == 200:
        lines = terms_statements(r.text, "html" in (r.headers.get("Content-Type") or ""))
        out["terms_lines"] = lines[:20]
        out["terms_sha256"] = hashlib.sha256("\n".join(lines).encode()).hexdigest()
    return out


CHECK = {"github": github, "huggingface": huggingface, "tml_manifest": tml_manifest, "terms": terms}


def previous() -> dict[str, dict]:
    last: dict[str, dict] = {}
    if LOG.exists():
        for line in LOG.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            last[rec["item"]] = rec
    return last


def utc(stamp) -> pd.Timestamp:
    t = pd.Timestamp(stamp)
    return t.tz_localize("UTC") if t.tzinfo is None else t.tz_convert("UTC")


def season_of(name: str) -> int | None:
    m = re.search(r"(\d{4})", name)
    return int(m.group(1)) if m else None


def flags(item: str, gap, now: pd.Timestamp, cur: dict, old: dict | None) -> list[str]:
    """The flags of one item, from this run's record and the previous run's (pure; tested). December, the
    off-season, raises no STALE flag."""
    out = []
    if cur.get("status") != 200:
        out.append("GONE")
    stamp = cur.get("pushed_at") or cur.get("last_modified") or cur.get("newest_mtime")
    if gap is not None and stamp and now.month != 12:
        age = (now - utc(stamp)).days
        if age > gap:
            out.append(f"STALE ({age} days)")
    if old and cur.get("files") and old.get("files"):
        if cur["count"] < old.get("count", 0):
            out.append(f"SHRANK (files {old['count']} -> {cur['count']})")
        crlf = cur.get("crlf") or {}
        smaller = []
        for n, (_, s) in cur["files"].items():
            before = old["files"].get(n, [None, None])[1]
            if s is None or before is None or "ongoing" in n or s >= before:
                continue
            allowance = crlf[n] if n in crlf else SHRINK_SHARE * before    # line endings explain this much
            if before - s > allowance:
                smaller.append(n)
        if smaller:
            out.append(f"SHRANK ({len(smaller)} files smaller: {', '.join(sorted(smaller)[:5])})")
        revised = [n for n, (m, _) in cur["files"].items() if n in old["files"] and m != old["files"][n][0]
                   and (season_of(n) or now.year) < now.year]
        if revised:
            out.append(f"REVISED ({len(revised)} earlier-season files: {', '.join(sorted(revised)[:5])})")
    if old and cur.get("terms_sha256") and old.get("terms_sha256") and cur["terms_sha256"] != old["terms_sha256"]:
        out.append("TERMS")
    sh = cur.get("software_heritage")
    if sh is not None:
        last = sh.get("last_full") or {}
        if "error" in last:
            out.append(f"ARCHIVE UNKNOWN (Software Heritage did not answer: {last['error']})")
        elif last.get("date"):
            if (now - utc(last["date"])).days > ARCHIVE_DAYS:
                out.append(f"UNARCHIVED (last Software Heritage snapshot {last['date']})")
        else:
            out.append("UNARCHIVED (no Software Heritage snapshot)")
    return out


def main() -> int:
    now = pd.Timestamp.now(tz="UTC")
    old = previous()
    records = []
    for item, kind, address, gap in WATCH:
        cur = CHECK[kind](address)
        rec = {"checked_at": now.isoformat(timespec="seconds"), "item": item, "kind": kind, **cur}
        rec["flags"] = flags(item, gap, now, cur, old.get(item))
        records.append(rec)
        print(f"{item:28s} {str(cur.get('status')):4s} {'; '.join(rec['flags']) or 'ok'}", flush=True)
        time.sleep(0.5)
    K.OUT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        for rec in records:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    K.write_json(LATEST, {"checked_at": now.isoformat(timespec="seconds"),
                          "flags": {r["item"]: r["flags"] for r in records if r["flags"]},
                          "items": [{k: v for k, v in r.items() if k != "files"} for r in records]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
