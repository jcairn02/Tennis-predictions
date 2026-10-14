"""Tennis My Life's staged dump as it stood when the frozen reference's Stage 0 was built (8 Oct 2026, 18:53 UTC), for
the replay of the prediction run (docs/studies/level_layer_adoption/).

Why. A prediction run rebuilds Stage 0 from the staged dump (data/dump/matches/tennis_my_life/), and Tennis My Life's
download of 10 Oct 2026 (14:30 UTC) revised past rows (Challengers 2017-2021, qualifying ids 2007-2019 and 2022,
2025-2026 ranks, ids and ages). A replay built on today's dump would differ from the template frame (built on the
frozen tables) for those data reasons, not for its code path. The replay is a test of the code path, so its sandbox
reads the dump of the freeze.

How. Per staged file: the version current at FREEZE is the last receipt (_receipts.jsonl) retrieved by then; when today's
staged copy carries another version, that version's CSV (the current file, or the copy the adapter kept in
superseded/) is staged again with the adapter's own staging (public_dump.common.stage_delimited), under the provenance
the original staging wrote (its source path, sha256 and first retrieval). Every other staged file is copied as it is.
The repository's dump and raw folders are only read. Proof that the view is right: Stage 0 built on it, without live
rows, must equal the frozen Stage 0 byte for byte (run in the replay's sandbox; the record says so).

Writes OUT/matches/tennis_my_life/ (outside the repository) and OUT/freeze_dump.json.
Run: ./python.sh src/eda/level_layer_adoption/freeze_dump.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.ingest.public_dump import common as PC  # noqa: E402

FREEZE = pd.Timestamp("2026-10-08T18:53:10Z")      # rebuild_stage0's start (data_continuity/rebuilds/2026-10-08T1853Z)
RAW = ROOT / "data" / "raw" / "public_dump" / "tennis_my_life"
DUMP = ROOT / "data" / "dump" / "matches" / "tennis_my_life"
OUT = Path("C:/Users/zerom/tnr_dump_freeze")


def main() -> int:
    rec = [json.loads(x) for x in (RAW / "_receipts.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    r = pd.DataFrame(rec)
    r["t"] = pd.to_datetime(r["retrieved_at"], utc=True)
    ok = r["error"].isna() if "error" in r else pd.Series(True, index=r.index)
    if "held" in r:
        ok &= r["held"].isna()
    r = r[ok & r["sha256"].notna()]
    out_dir = OUT / "matches" / "tennis_my_life"
    if out_dir.exists():
        raise SystemExit(f"{out_dir} exists")
    report = {"freeze": str(FREEZE), "files": {}}
    for parquet in sorted(DUMP.rglob("*.parquet")):
        rel = parquet.relative_to(DUMP)
        meta = json.loads(parquet.with_name(parquet.name + ".meta.json").read_text(encoding="utf-8"))
        name = Path(meta["source_path"]).relative_to(Path("data/raw/public_dump/tennis_my_life")).as_posix() \
            if str(meta.get("source_path", "")).startswith("data/raw/public_dump/tennis_my_life") else None
        if name is None:
            raise SystemExit(f"{parquet}: its meta names no source CSV ({meta.get('source_path')})")
        mine = r[r["name"] == name].sort_values("t")
        then = mine[mine["t"] <= FREEZE]
        if then.empty:
            report["files"][str(rel)] = "absent at the freeze: left out"
            continue
        want = then.iloc[-1]["sha256"]
        dst = out_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if meta["sha256"] == want:
            shutil.copy2(parquet, dst)
            shutil.copy2(parquet.with_name(parquet.name + ".meta.json"), dst.with_name(dst.name + ".meta.json"))
            report["files"][str(rel)] = "as staged"
            continue
        # the freeze's version: the current CSV when it is that version, else the copy kept in superseded/
        src = RAW / name
        if PC.sha256_file(src) != want:
            stem = Path(name).stem
            cands = list((RAW / "superseded" / Path(name).parent).glob(f"{stem}.*.{want[:12]}.csv"))
            if len(cands) != 1:
                raise SystemExit(f"{name}: the freeze's version {want[:12]} is not kept ({len(cands)} candidates)")
            src = cands[0]
        if PC.sha256_file(src) != want:
            raise SystemExit(f"{src}: not the version {want[:12]}")
        first = mine[mine["sha256"] == want].iloc[0].to_dict()
        prov = PC.Provenance("tennis_my_life", meta["source_path"], want, first["retrieved_at"])
        stats = PC.stage_delimited(src, dst, prov)
        PC.staged_meta(meta.get("branch", "matches"), "tennis_my_life", dst, first, stats,
                       catalog_name=name, catalog_mtime=first.get("catalog_mtime"),
                       catalog_size=first.get("catalog_size"))
        report["files"][str(rel)] = {"restaged_from": str(src), "sha256": want, "today": meta["sha256"]}
    (OUT / "freeze_dump.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    n = sum(isinstance(v, dict) for v in report["files"].values())
    print(f"{len(report['files'])} staged files; {n} re-staged to the freeze's version; written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
