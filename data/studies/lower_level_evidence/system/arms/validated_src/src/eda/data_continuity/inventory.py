"""The preservation register: every raw folder, its size, whether it has receipts, which data-map entry claims it,
the rights and backup notes that entry records, and whether any copy outside this PC is recorded.

data/raw/ is gitignored, so a fresh clone holds none of it. Two copies outside the working tree exist, both zips in
the project's Google Cloud Storage bucket: the Hugging Face dump's (data/LARGE_FILES.md, section 5), and the public data
dump of 22 September (its README.txt in the bucket, read 6 Oct 2026). The second covers only the files of
data/raw/public_dump/ that have not changed since it was made, so a folder's covered bytes are counted file by file.

Writes data/studies/data_continuity/preservation_register.csv and preservation_register.json.
Run: ./python.sh src/eda/data_continuity/inventory.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402

RAW = K.ROOT / "data" / "raw"
CATALOG = K.ROOT / "data" / "data_map.yaml"
# copies outside the working tree that the repository records (data/LARGE_FILES.md)
OFF_MACHINE = {"data/raw/public_dump/atp_pipeline_handoff/":
               "gs://tennis-predictions-archive/public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip (Coldline)"}
# a zip of data/raw/public_dump/ without the Hugging Face folder, made on 23 Sep 2026 from the dump of 22 September
# (576 files, 1.7 GB): it holds a file only if the file has not changed since. Cut-off: the start of 23 Sep (UTC).
PARTIAL = ("data/raw/public_dump/",
           "gs://tennis-predictions-archive/public_dump/tennis_public_dump_raw_2026-09-22.zip (Coldline)",
           pd.Timestamp("2026-09-23T00:00:00Z").timestamp())
# upstreams that no longer serve what was downloaded (observed: canary.jsonl, the study reports)
UPSTREAM = {
    "data/raw/public_dump/sackmann_archive/": "original repositories 404 since June 2026; third-party mirror online",
    "data/raw/point_shot_sources/pbp_copy_2015/": "original repository 404; third-party copies online",
    "data/raw/point_shot_sources/pbp_copy_2018/": "original repository 404; third-party copies online",
    "data/raw/sackmann/": "original repositories 404 since June 2026",
    "data/raw/point_sources/tdi/": "listing keeps about 92 days; older pages still answer but are not listed",
    "data/raw/point_sources/ausopen/": "API serves the current edition only",
    "data/raw/public_dump/tennis_my_life/": "publisher revises files in place (2024.csv on 5 Oct 2026)",
    "data/raw/public_dump/tennis_data_couk/": "live site gone; Wayback captures",
}


def folders() -> list[Path]:
    """Source folders: data/raw/<group>/<source>/, or a group with no subfolders; loose files count as sources."""
    out = []
    for group in sorted(p for p in RAW.iterdir() if p.is_dir()):
        subs = sorted(p for p in group.iterdir() if p.is_dir())
        files = [p for p in group.iterdir() if p.is_file() and p.name != "_receipts.jsonl"]
        out += subs + files if subs else [group]
    return out


def measure(path: Path, cutoff: float | None = None) -> dict:
    """Size, file count, receipts and newest change; with ``cutoff``, also the bytes unchanged since then."""
    if path.is_file():
        st = path.stat()
        return {"bytes": st.st_size, "files": 1, "receipts": False,
                "newest": pd.Timestamp(st.st_mtime, unit="s", tz="UTC"),
                "unchanged_bytes": st.st_size if cutoff is not None and st.st_mtime <= cutoff else 0}
    n = size = unchanged = 0
    newest = 0.0
    receipts = False
    for p in path.rglob("*"):
        if p.is_file():
            st = p.stat()
            n, size, newest = n + 1, size + st.st_size, max(newest, st.st_mtime)
            unchanged += st.st_size if cutoff is not None and st.st_mtime <= cutoff else 0
            receipts = receipts or p.name == "_receipts.jsonl"
    return {"bytes": size, "files": n, "receipts": receipts,
            "newest": pd.Timestamp(newest, unit="s", tz="UTC") if newest else pd.NaT, "unchanged_bytes": unchanged}


def main() -> int:
    catalog = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    claims = []
    for d in catalog["datasets"]:
        for r in d.get("raw") or []:
            claims.append((r.rstrip("/") + "/", d))
    rows = []
    for path in folders():
        key = path.relative_to(K.ROOT).as_posix() + ("/" if path.is_dir() else "")
        owners = [d for r, d in claims if key.startswith(r) or r.startswith(key)]
        whole = next((v for k, v in OFF_MACHINE.items() if key.startswith(k)), "")
        partial = not whole and key.startswith(PARTIAL[0])
        m = measure(path, PARTIAL[2] if partial else None)
        covered = m["bytes"] if whole else m.pop("unchanged_bytes", 0)
        m.pop("unchanged_bytes", None)
        note = whole or (f"{PARTIAL[1]}: the {covered / 1e9:.2f} GB unchanged since 23 Sep" if covered else "")
        rows.append({
            "folder": key, **m, "gb": round(m["bytes"] / 1e9, 3), "covered_gb": round(covered / 1e9, 3),
            "catalog_entries": ";".join(sorted({d["id"] for d in owners})) or "UNMAPPED",
            "rights": " | ".join(sorted({str(d.get("rights")) for d in owners if d.get("rights")})),
            "backup_note": " | ".join(sorted({" ".join(str(d.get("backup")).split()) for d in owners if d.get("backup")})),
            "off_machine_copy": note,
            "upstream": next((v for k, v in UPSTREAM.items() if key.startswith(k)), ""),
        })
    reg = pd.DataFrame(rows).sort_values("bytes", ascending=False)
    reg["newest"] = reg["newest"].astype(str)
    K.OUT.mkdir(parents=True, exist_ok=True)
    reg.to_csv(K.OUT / "preservation_register.csv", index=False)
    covered_gb = reg["covered_gb"].sum()
    K.write_json(K.OUT / "preservation_register.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "raw_gb": round(reg["bytes"].sum() / 1e9, 2),
        "raw_gb_with_an_off_machine_copy": round(covered_gb, 2),
        "raw_gb_without": round(reg["bytes"].sum() / 1e9 - covered_gb, 2),
        "folders": int(len(reg)), "folders_without_receipts": int((~reg["receipts"]).sum()),
        "unmapped_folders": reg.loc[reg["catalog_entries"].eq("UNMAPPED"), "folder"].tolist(),
        "unmapped_gb": round(reg.loc[reg["catalog_entries"].eq("UNMAPPED"), "bytes"].sum() / 1e9, 2),
        "upstream_no_longer_serves": reg.loc[reg["upstream"].ne(""), ["folder", "upstream"]].to_dict("records"),
    })
    print(reg[["folder", "gb", "files", "receipts", "catalog_entries", "off_machine_copy"]].head(45).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
