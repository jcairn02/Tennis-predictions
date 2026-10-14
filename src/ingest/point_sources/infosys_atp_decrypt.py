"""Decrypt and audit the locally downloaded ATP Infosys envelopes, without HTTP.

The owner requested decryption of the entire local backfill on 8 October 2026.
Raw envelopes are preserved. Plain JSON retains every decoded field and mirrors
the raw year/event/route/match layout under data/dump/points/infosys_atp/decrypted/.

Run: ./python.sh -m src.ingest.point_sources.infosys_atp_decrypt
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.ingest.point_sources.common import PROJECT_ROOT
from src.ingest.point_sources.infosys_slams import decrypt

RAW = PROJECT_ROOT / "data/raw/point_sources/infosys_atp"
OUTPUT = PROJECT_ROOT / "data/dump/points/infosys_atp/decrypted"
REPORT = PROJECT_ROOT / "data/studies/serve_speed_acquisition/infosys_atp_decryption"
INVENTORY = PROJECT_ROOT / "data/studies/serve_speed_acquisition/infosys_atp_files.csv"
SCHEMAS = {
    "keystats": ("players", "setStats"),
    "match-beats": ("playerData", "setData", "matchId", "eventId"),
    "rally-analysis": ("playerDetails", "rallyData"),
    "court-vision": ("courtVisionData",),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def positive_speed(value):
    """Recognize positive finite values, including Court Vision's '194.38 KPH'.

    Do not discard anomalous speeds: this is a faithful export, not cleaning.
    """
    if isinstance(value, bool) or value is None:
        return None
    text = str(value).strip()
    text = re.sub(r"\s*(?:KPH|KM/H)$", "", text, flags=re.I)
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) and number > 0 else None


def dictionaries(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from dictionaries(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from dictionaries(value)


def audit(doc, route: str, event: str, match: str) -> dict:
    schema_ok = isinstance(doc, dict) and all(key in doc for key in SCHEMAS[route])
    result = {"tennis_schema_ok": schema_ok, "identity_ok": True,
              "players": "", "speed_fields": 0, "positive_speed_values": 0,
              "min_positive_speed": None, "max_positive_speed": None,
              "speed_values_outside_50_300": 0, "point_records": 0}
    if not schema_ok:
        return result
    if route == "match-beats":
        result["identity_ok"] = (str(doc["eventId"]) == event and
                                 str(doc["matchId"]).upper() == match.upper())
    names = set()
    speeds = []
    for obj in dictionaries(doc):
        if "pointId" in obj and "serveSpeed" in obj:
            result["point_records"] += 1
        for key, value in obj.items():
            if key.endswith("Name") and (key.startswith("player") or key.startswith("tm")):
                if isinstance(value, str) and value.strip():
                    names.add(value.strip())
        fields = []
        if route in ("match-beats", "rally-analysis"):
            fields = [obj[k] for k in ("serveSpeed", "faultSrvSpd") if k in obj]
        elif route == "keystats" and "speed" in str(obj.get("name", "")).lower():
            fields = [obj[k] for k in ("player1", "player2") if k in obj]
        elif route == "court-vision" and "a81" in obj and "a12" in obj:
            # a50 maps point IDs to trajectories. a16 is the point's serve speed;
            # a21 also repeats speed information, so count only a16 per point.
            fields = [obj["a16"]] if "a16" in obj else []
            result["point_records"] += 1
        result["speed_fields"] += len(fields)
        speeds.extend(n for v in fields if (n := positive_speed(v)) is not None)
    result.update(players=" | ".join(sorted(names)), positive_speed_values=len(speeds),
                  min_positive_speed=min(speeds) if speeds else None,
                  max_positive_speed=max(speeds) if speeds else None,
                  speed_values_outside_50_300=sum(n < 50 or n > 300 for n in speeds))
    return result


def main() -> int:
    started = datetime.now(timezone.utc).isoformat()
    paths = sorted(RAW.rglob("*.json.gz"))
    if not paths:
        raise SystemExit(f"No envelopes found in {RAW}")
    with INVENTORY.open(encoding="utf-8", newline="") as handle:
        inventory = {row["path"]: row for row in csv.DictReader(handle)}
    rows = []
    for index, path in enumerate(paths, 1):
        parts = path.relative_to(RAW).parts
        year, event, route, filename = parts
        match = filename.removesuffix(".json.gz")
        target = OUTPUT / year / event / route / f"{match}.json"
        stored = path.read_bytes()
        row = {"raw_file": relative(path), "decrypted_file": relative(target),
               "year": year, "event_id": event, "route": route, "match_id": match,
               "purpose": inventory.get(relative(path), {}).get("purpose", "unknown"),
               "raw_stored_bytes": len(stored), "raw_stored_sha256": sha(stored),
               "envelope_sha256": "", "receipt_sha256_ok": False,
               "was_encrypted": False, "decrypted_ok": False,
               "output_bytes": 0, "output_sha256": "", "output_roundtrip_ok": False,
               "tennis_schema_ok": False, "identity_ok": False, "players": "",
               "speed_fields": 0, "positive_speed_values": 0,
               "min_positive_speed": None, "max_positive_speed": None,
               "speed_values_outside_50_300": 0, "point_records": 0, "error": ""}
        try:
            body = gzip.decompress(stored)
            row["envelope_sha256"] = sha(body)
            expected = inventory.get(relative(path), {}).get("sha256")
            row["receipt_sha256_ok"] = bool(expected) and sha(body) == expected
            envelope = json.loads(body)
            row["was_encrypted"] = bool(envelope.get("response"))
            doc = decrypt(envelope)
            row["decrypted_ok"] = True
            row.update(audit(doc, route, event, match))
            plain = (json.dumps(doc, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                if target.read_bytes() != plain:
                    raise ValueError("Existing output differs; preserved it instead of overwriting")
            else:
                target.write_bytes(plain)
            saved = target.read_bytes()
            row.update(output_bytes=len(saved), output_sha256=sha(saved),
                       output_roundtrip_ok=saved == plain and json.loads(saved) == doc)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
        if index % 500 == 0 or index == len(paths):
            print(f"Decrypted/audited {index}/{len(paths)} files", flush=True)

    # Re-read every original after processing, and detect additions/removals.
    after = set(RAW.rglob("*.json.gz"))
    originals_unchanged = after == set(paths) and all(
        sha((PROJECT_ROOT / row["raw_file"]).read_bytes()) == row["raw_stored_sha256"]
        for row in rows
    )
    counts = Counter()
    by_year_route = {}
    speed_matches = set()
    for row in rows:
        for flag in ("was_encrypted", "decrypted_ok", "output_roundtrip_ok", "tennis_schema_ok",
                     "identity_ok", "receipt_sha256_ok"):
            counts[flag] += bool(row[flag])
        counts["files_with_positive_speeds"] += row["positive_speed_values"] > 0
        counts["files_without_positive_speeds"] += row["positive_speed_values"] == 0
        counts["files_with_errors"] += bool(row["error"])
        counts["speed_values_outside_50_300"] += row["speed_values_outside_50_300"]
        key = f"{row['year']}/{row['route']}"
        cell = by_year_route.setdefault(key, Counter())
        cell["files"] += 1
        cell["files_with_positive_speeds"] += row["positive_speed_values"] > 0
        cell["positive_speed_values"] += row["positive_speed_values"]
        cell["errors"] += bool(row["error"])
        if row["positive_speed_values"]:
            speed_matches.add((row["year"], row["event_id"], row["match_id"]))
    complete = (originals_unchanged and not counts["files_with_errors"] and
                all(counts[k] == len(paths) for k in ("decrypted_ok", "output_roundtrip_ok",
                    "tennis_schema_ok", "identity_ok", "receipt_sha256_ok")))
    summary = {
        "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_folder": relative(RAW), "decrypted_folder": relative(OUTPUT),
        "files": len(paths), "raw_stored_bytes": sum(r["raw_stored_bytes"] for r in rows),
        "decrypted_bytes": sum(r["output_bytes"] for r in rows),
        "originals_unchanged": originals_unchanged, "all_checks_passed": complete,
        "counts": dict(counts), "unique_matches_with_positive_speeds": len(speed_matches),
        "by_year_route": by_year_route,
        "errors": [{"file": r["raw_file"], "error": r["error"]} for r in rows if r["error"]],
        "notes": ["Entire local folder processed, including the four calibration files of 2022/2025.",
                  "Valid tennis files can contain missing, zero or empty speed fields.",
                  "All decoded fields retained; Court Vision's a-number field names remain as served.",
                  "Counts of speed values include multiple routes and per-set aggregates, not unique serves.",
                  "50-300 is an audit flag only; unusual values are preserved and not cleaned.",
                  "Player metadata is present in source payloads; cross-source identity reconciliation is separate."]}
    REPORT.mkdir(parents=True, exist_ok=True)
    with (REPORT / "files.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "README.md").write_text(
        "# Decrypted ATP Infosys match data\n\n"
        "Plain UTF-8 JSON, at `<year>/<event>/<route>/<match>.json`. "
        "Every field of the decoded payload is retained. The encrypted originals remain "
        "under `data/raw/point_sources/infosys_atp/`.\n\n"
        "Routes: key statistics (per-match/per-set box scores and speeds), MatchBeats "
        "(point data), rally analysis (point data), and Court Vision (tracking). "
        "Some files contain no positive serve speeds. Court Vision retains its original "
        "`a...` field names; speed fields may include the unit `KPH`.\n\n"
        "Audit: `data/studies/serve_speed_acquisition/infosys_atp_decryption/summary.json` "
        "and `files.csv` record content checks, missing speeds, receipt hashes, output "
        "hashes and preservation of originals.\n\n"
        "Reproduce offline: `./python.sh -m src.ingest.point_sources.infosys_atp_decrypt`.\n",
        encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
