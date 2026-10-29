"""A cold-storage copy of everything in data/ that has no copy on GitHub or in the project's bucket.

A file in data/ already has a copy when
  * GitHub has it: it is tracked at HEAD, HEAD is origin's main, and the working copy equals HEAD; or
  * a zip in gs://tennis-predictions-archive/ has it: an entry with the same path, size and CRC-32. Each zip's central
    directory is read with a range request from its end, so no zip is downloaded.
The rest goes into dated zips in data/backups/<date>/, one per folder of data/ (raw, dump and studies; data/'s loose
files and any other folder go with studies). Already-compressed files (.gz, .parquet, ...) are stored, the rest
deflated. manifest.csv.gz lists every file of data/ and where its copy is, with the SHA-256 of each file zipped here.
--groups raw,dump makes a set of the downloads alone (data/raw/ and data/dump/); its plan and manifest list only those
folders.

Checks before upload: every entry's CRC (zipfile), the entries against the manifest, and Windows tar, the restore
tool, extracting the whole zip to a pipe, whose bytes must hash to the stream of file bytes recorded while packing.
Uploads use storage class COLDLINE, never overwrite an object, and send whole objects, so each object's MD5 can be
compared with the local file's.

Not copied, and listed with the reason: data/backups/ (where the zips are written), folders this account cannot read
(pytest's temporary folders) and report QA's browser profiles (caches and cookies, not data).

Steps, each reading the one before from data/backups/<date>/:
    plan    scan data/ and classify every file: plan.csv.gz, plan.json
    pack    write the zips, manifest.csv.gz and packed.json
    verify  check every zip, take its SHA-256 and MD5, and write zips.json, summary.json and README.txt
    upload  upload the zips, the manifest, summary.json and README.txt, check each object, and append the result
            to data/studies/data_continuity/backups.jsonl
Run: ./python.sh src/eda/data_continuity/backup.py {plan,pack,verify,upload} [--date YYYY-MM-DD] [--groups raw,dump]
"""
from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
import zlib
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date as Date, datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402

DATA = K.ROOT / "data"
BACKUPS = DATA / "backups"
BUCKET = "gs://tennis-predictions-archive"
PREFIX = "data"                                   # this script's sets: gs://tennis-predictions-archive/data/<date>/
# where the entry names of the September zips start; this script's zips start at the repository root ("data/...")
ZIP_ROOTS = {"public_dump/tennis_public_dump_raw_2026-09-22.zip": "data/raw/",
             "public_dump/tennis_atp_pipeline_handoff_raw_2026-09-25.zip": "data/raw/"}
EXCLUDED = [(re.compile(r"^data/backups/"), "where the backup zips are written"),
            (re.compile(r"^data/.*/report_qa/(chrome|edge)_desktop_profile/"),
             "a browser profile of report QA: caches and cookies, not data")]
STORED = {".gz", ".tgz", ".parquet", ".zip", ".7z", ".xz", ".bz2", ".zst", ".br", ".png", ".jpg", ".jpeg", ".gif",
          ".webp", ".mp4", ".pdf"}
GROUPS = ("raw", "dump", "studies")
CHUNK = 8 * 2**20
GCLOUD = shutil.which("gcloud.cmd") or shutil.which("gcloud")
TAR = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tar.exe"
FIELDS = ["path", "bytes", "mtime", "status", "where", "sha256", "crc32", "note"]


def run(*args: str, **kw) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, check=True, **kw)


def git(*args: str) -> str:
    return run("git", "-C", str(K.ROOT), *args).stdout.decode("utf-8")


def github() -> tuple[str, str, set[str]]:
    """origin's URL, HEAD's commit, and the files of data/ that GitHub holds as they are now."""
    head = git("rev-parse", "HEAD").strip()
    remote = git("ls-remote", "origin", "refs/heads/main").split()
    if not remote or remote[0] != head:
        raise SystemExit(f"origin's main is {remote[:1]} but HEAD is {head}: GitHub does not hold HEAD")
    tracked = set(git("ls-tree", "-r", "-z", "--name-only", "HEAD", "--", "data").split("\0")) - {""}
    changed = set(git("diff", "-z", "--no-renames", "--name-only", "HEAD", "--", "data").split("\0")) - {""}
    return git("remote", "get-url", "origin").strip(), head, tracked - changed


class Tail(io.RawIOBase):
    """The last bytes of a remote file, seekable at their positions in the whole file: enough for zipfile to read
    the central directory. Reading before the tail raises EOFError, and the caller fetches a longer tail."""

    def __init__(self, data: bytes, total: int):
        self.data, self.total, self.start, self.pos = data, total, total - len(data), 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.pos

    def seek(self, offset: int, whence: int = 0) -> int:
        self.pos = {0: offset, 1: self.pos + offset, 2: self.total + offset}[whence]
        return self.pos

    def read(self, n: int = -1) -> bytes:
        if self.pos < self.start:
            raise EOFError(f"byte {self.pos} is before the tail, which starts at {self.start}")
        i = self.pos - self.start
        out = self.data[i:] if n is None or n < 0 else self.data[i:i + n]
        self.pos += len(out)
        return out

    def readinto(self, b) -> int:
        d = self.read(len(b))
        b[:len(d)] = d
        return len(d)


def central_directory(fetch, size: int, first: int = 2**20) -> list[zipfile.ZipInfo]:
    """A zip's entries from its last bytes; ``fetch(n)`` returns the last n bytes."""
    n = first
    while True:
        try:
            return zipfile.ZipFile(Tail(fetch(min(n, size)), size)).infolist()
        except EOFError:
            if n >= size:
                raise
            n *= 4


def bucket_zips() -> dict[str, list[tuple[int, int, str]]]:
    """Every file the bucket's zips hold, by repository path: (size, CRC-32, object URL) per entry."""
    held: dict[str, list[tuple[int, int, str]]] = {}
    for line in run(GCLOUD, "storage", "ls", "-l", f"{BUCKET}/**", text=True).stdout.splitlines():
        parts = line.split()
        if len(parts) != 3 or not parts[2].endswith(".zip"):
            continue
        size, url = int(parts[0]), parts[2]
        root = ZIP_ROOTS.get(url[len(BUCKET) + 1:], "")
        for i in central_directory(lambda n: run(GCLOUD, "storage", "cat", "-r", f"-{n}", url).stdout, size):
            if not i.is_dir():
                held.setdefault(root + i.filename, []).append((i.file_size, i.CRC, url))
    return held


def scan(groups: tuple[str, ...] = GROUPS) -> tuple[list[dict], list[str]]:
    """Every file under data/ that goes into one of ``groups``' zips (path, bytes, mtime), and the folders that could
    not be read."""
    files, unreadable = [], []

    def failed(e: OSError) -> None:
        unreadable.append(Path(e.filename).relative_to(K.ROOT).as_posix() + "/")

    # studies takes whatever raw and dump do not, so it needs the whole of data/; raw and dump need only their folders
    for root in [DATA] if "studies" in groups else [DATA / g for g in groups]:
        for dirpath, _, names in os.walk(root, onerror=failed):
            for name in names:
                p = Path(dirpath) / name
                path = p.relative_to(K.ROOT).as_posix()
                if group(path) not in groups:
                    continue
                try:
                    st = p.stat()
                except FileNotFoundError:        # removed since the folder was listed
                    continue
                files.append({"path": path, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns})
    return files, sorted(u for u in unreadable if group(u) in groups)


def excluded_by(path: str) -> tuple[str, str] | None:
    """The excluded folder holding ``path``, and why it is excluded."""
    for rx, why in EXCLUDED:
        if m := rx.search(path):
            return path[:m.end()], why
    return None


def crc32(path: Path) -> int:
    c = 0
    with open(path, "rb") as f:
        while b := f.read(CHUNK):
            c = zlib.crc32(b, c)
    return c


def utc(ns: int) -> str:
    return datetime.fromtimestamp(ns / 1e9, timezone.utc).isoformat(timespec="seconds")


def group(path: str) -> str:
    """The zip a path under data/ goes into: raw or dump for those folders, studies for everything else."""
    top = path.split("/")[1] if path.count("/") > 1 else ""
    return top if top in GROUPS else "studies"


def zip_name(path: str, day: str) -> str:
    return f"tennis_data_{group(path)}_{day}.zip"


def target(path: str, day: str) -> str:
    return f"{BUCKET}/{PREFIX}/{day}/{zip_name(path, day)}"


def write_rows(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tally(rows: list[dict], key: str) -> dict:
    out: dict[str, dict] = {}
    for r in rows:
        t = out.setdefault(r[key], {"files": 0, "bytes": 0})
        t["files"] += 1
        t["bytes"] += int(r["bytes"] or 0)
    return out


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def plan(out: Path, day: str, groups: tuple[str, ...] = GROUPS) -> None:
    origin, head, on_github = github()
    held = bucket_zips()
    started = now()
    files, unreadable = scan(groups)
    excluded: dict[str, str] = {}
    check = []
    for f in files:
        f["mtime"] = utc(f.pop("mtime_ns"))
        if hit := excluded_by(f["path"]):
            excluded[hit[0]] = hit[1]
            f.update(status="excluded", note=hit[1])
        elif f["path"] in on_github:
            f.update(status="github", where=f"{origin}@{head}")
        elif same := [h for h in held.get(f["path"], []) if h[0] == f["bytes"]]:
            check.append((f, same))
        else:
            f.update(status="copy", where=target(f["path"], day))
    with ThreadPoolExecutor(8) as pool:
        for (f, same), c in zip(check, pool.map(lambda fs: crc32(K.ROOT / fs[0]["path"]), check)):
            if url := next((u for _, crc, u in same if crc == c), None):
                f.update(status="bucket", where=url)
            else:
                f.update(status="copy", where=target(f["path"], day))
    rows = sorted(files, key=lambda r: r["path"]) + [
        {"path": u, "bytes": "", "mtime": "", "status": "unreadable", "where": "",
         "note": "this account cannot list the folder (access denied)"} for u in unreadable]
    out.mkdir(parents=True, exist_ok=True)
    write_rows(out / "plan.csv.gz", rows)
    by_status = tally(rows, "status")
    K.write_json(out / "plan.json", {
        "planned_at": started, "origin": origin, "head": head, "groups": list(groups), "by_status": by_status,
        "copy_by_zip": tally([{**r, "zip": r["where"].rsplit("/", 1)[1]} for r in rows if r["status"] == "copy"],
                             "zip"),
        "unreadable": unreadable, "excluded": excluded})
    for k, v in by_status.items():
        print(f"{k:>10}: {v['files']:>8,} files {v['bytes'] / 1e9:8.3f} GB")


def pack_one(job: tuple[str, list[dict]]) -> tuple[list[dict], dict]:
    """Write one zip (never over an existing file); return its manifest rows and the hash of its file stream."""
    zpath, rows = Path(job[0]), job[1]
    stream, total, done = hashlib.sha256(), 0, []
    with zipfile.ZipFile(zpath, "x", allowZip64=True, strict_timestamps=False) as z:
        for k, r in enumerate(rows):
            p = K.ROOT / r["path"]
            try:
                src = open(p, "rb")
            except FileNotFoundError:
                done.append({**r, "status": "removed", "where": "", "note": "removed after the plan"})
                continue
            except OSError as e:
                done.append({**r, "status": "unreadable", "where": "", "note": f"{type(e).__name__}: {e}"})
                continue
            with src:
                before = os.fstat(src.fileno())
                info = zipfile.ZipInfo.from_file(p, r["path"], strict_timestamps=False)
                info.compress_type = zipfile.ZIP_STORED if p.suffix.lower() in STORED else zipfile.ZIP_DEFLATED
                sha, n = hashlib.sha256(), 0
                with z.open(info, "w", force_zip64=before.st_size > 2**30) as dst:
                    while b := src.read(CHUNK):
                        sha.update(b)
                        stream.update(b)
                        dst.write(b)
                        n += len(b)
            after = p.stat()
            if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns) or n != before.st_size:
                note = "changed while being read; the zip holds the bytes read"
            elif n != int(r["bytes"]):
                note = f"changed after the plan ({int(r['bytes']):,} bytes then)"
            else:
                note = ""
            done.append({**r, "status": "zipped", "bytes": n, "mtime": utc(before.st_mtime_ns),
                         "sha256": sha.hexdigest(), "crc32": f"{info.CRC:08x}", "note": note})
            total += n
            if (k + 1) % 20000 == 0:
                print(f"{zpath.name}: {k + 1:,} of {len(rows):,} files, {total / 1e9:.2f} GB", flush=True)
    print(f"{zpath.name}: done, {len(done):,} files, {total / 1e9:.2f} GB", flush=True)
    return done, {"zip": zpath.name, "stream_sha256": stream.hexdigest(), "stream_bytes": total}


def pack(out: Path) -> None:
    rows = read_rows(out / "plan.csv.gz")
    jobs: dict[str, list[dict]] = {}
    for r in rows:
        if r["status"] == "copy":
            jobs.setdefault(str(out / r["where"].rsplit("/", 1)[1]), []).append(r)
    with ProcessPoolExecutor(len(jobs)) as pool:
        results = list(pool.map(pack_one, sorted(jobs.items())))
    packed = {r["path"]: r for done, _ in results for r in done}
    write_rows(out / "manifest.csv.gz", [packed.get(r["path"], r) for r in rows])
    K.write_json(out / "packed.json", {"packed_at": now(), "streams": [s for _, s in results]})


def check_one(job: tuple[str, dict, dict]) -> dict:
    """CRC-check one zip, compare its entries with the manifest, extract it to a pipe with Windows tar and hash the
    bytes, and take the zip's SHA-256 and MD5."""
    zpath, expected, stream = Path(job[0]), job[1], job[2]
    with zipfile.ZipFile(zpath) as z:
        bad = z.testzip()
        entries = {i.filename: (i.file_size, f"{i.CRC:08x}") for i in z.infolist()}
    if bad is not None:
        raise SystemExit(f"{zpath.name}: bad CRC in {bad}")
    if entries != expected:
        raise SystemExit(f"{zpath.name}: the entries differ from the manifest "
                         f"({len(set(entries) ^ set(expected))} names, of {len(expected):,})")
    listed = run(str(TAR), "-tf", str(zpath)).stdout.count(b"\n")
    tar = subprocess.Popen([str(TAR), "-xOf", str(zpath)], stdout=subprocess.PIPE)
    piped, n = hashlib.sha256(), 0
    while b := tar.stdout.read(CHUNK):
        piped.update(b)
        n += len(b)
    if tar.wait() != 0 or listed != len(expected) or (piped.hexdigest(), n) != (stream["stream_sha256"],
                                                                                stream["stream_bytes"]):
        raise SystemExit(f"{zpath.name}: tar listed {listed:,} of {len(expected):,} entries and extracted {n:,} "
                         f"bytes (exit {tar.returncode}); expected {stream['stream_bytes']:,} bytes, stream "
                         f"SHA-256 {stream['stream_sha256']}, got {piped.hexdigest()}")
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with open(zpath, "rb") as f:
        while b := f.read(CHUNK):
            sha.update(b)
            md5.update(b)
    print(f"{zpath.name}: {len(entries):,} entries; CRCs, manifest and tar extraction agree", flush=True)
    return {"zip": zpath.name, "bytes": zpath.stat().st_size, "files": len(entries),
            "data_bytes": stream["stream_bytes"], "sha256": sha.hexdigest(),
            "md5": base64.b64encode(md5.digest()).decode()}


def verify(out: Path, day: str) -> None:
    rows = read_rows(out / "manifest.csv.gz")
    streams = {s["zip"]: s for s in json.loads((out / "packed.json").read_text(encoding="utf-8"))["streams"]}
    expected: dict[str, dict] = {}
    for r in rows:
        if r["status"] == "zipped":
            expected.setdefault(r["where"].rsplit("/", 1)[1], {})[r["path"]] = (int(r["bytes"]), r["crc32"])
    with ProcessPoolExecutor(len(expected)) as pool:
        zips = list(pool.map(check_one, [(str(out / z), e, streams[z]) for z, e in sorted(expected.items())]))
    planned = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    summary = {"made": day, "snapshot": planned["planned_at"], "origin": planned["origin"], "head": planned["head"],
               "groups": planned.get("groups", list(GROUPS)),
               "bucket": f"{BUCKET}/{PREFIX}/{day}/", "storage_class": "COLDLINE",
               "by_status": tally(rows, "status"), "zips": zips,
               "earlier_zips": tally([r for r in rows if r["status"] == "bucket"], "where"),
               "unreadable": [r["path"] for r in rows if r["status"] == "unreadable"],
               "removed": [r["path"] for r in rows if r["status"] == "removed"],
               "excluded": planned["excluded"],
               "changed_while_read": [r["path"] for r in rows if r["note"].startswith("changed while")]}
    K.write_json(out / "zips.json", {"zips": zips})
    K.write_json(out / "summary.json", summary)
    with open(out / "README.txt", "w", encoding="utf-8", newline="\r\n") as f:
        f.write(readme(summary))
    print(json.dumps({k: summary[k] for k in ("by_status", "zips")}, indent=1))


ZIP_TEXT = {
    "raw": "data\\raw\\: downloads as served, with receipts, except the files the bucket's earlier zips hold unchanged",
    "dump": "data\\dump\\: the staged Parquet tables (the adapters rebuild them from raw)",
    "studies": "data\\studies\\: study outputs that git does not hold (Parquet tables, files over 50 MB, untracked\n"
               "      and changed files), and data\\'s own files that GitHub does not hold as they are now",
}


SCOPE = {"raw": "data\\raw\\", "dump": "data\\dump\\", "studies": "data\\'s other folders and files"}


def set_day(url: str) -> str:
    """The date a bucket zip's name ends with (..._YYYY-MM-DD.zip), which orders the sets for a restore."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", url)
    return m.group(1) if m else ""


def readme(s: dict) -> str:
    day, head = s["made"], s["head"]
    whole = s.get("groups", list(GROUPS)) == list(GROUPS)
    scope = "data\\" if whole else " and ".join(SCOPE[g] for g in s["groups"])
    zipped = s["by_status"].get("zipped", {"files": 0, "bytes": 0})
    lines = [
        f"Tennis-predictions: cold-storage copy of the files in {scope} that GitHub and the earlier zips do not hold",
        "",
        f"Made:     {day}, from the working tree at commit {head[:7]} (GitHub's main); snapshot {s['snapshot']}",
        f"What:     every file under Tennis-predictions\\{scope} with no copy outside the PC: {zipped['files']:,} files,",
        f"          {zipped['bytes'] / 1e9:.2f} GB. A file counted as copied if GitHub holds it as it is now (tracked at",
        "          that commit and unchanged), or if a zip in this bucket holds it with the same size and CRC-32.",
    ]
    if not whole:
        lines += [f"Scope:    {scope} only; this set neither holds nor lists the rest of data\\."]
    lines += [""]
    for z in s["zips"]:
        lines += [f"  {z['zip']}: {z['files']:,} files, {z['data_bytes'] / 1e9:.2f} GB unzipped, "
                  f"{z['bytes']:,} bytes", f"      SHA-256 {z['sha256']}", f"      {ZIP_TEXT[z['zip'].split('_')[2]]}",
                  ""]
    lines += [
        f"  manifest.csv.gz: every file of {scope} at the snapshot: bytes, modified time, and where its copy is",
        "      (status github, bucket or zipped, and the commit or zip); SHA-256 and CRC-32 for the zipped files. The",
        "      files not copied are listed too, with the reason.",
        "  summary.json: the counts, and anything that changed while being read.",
        "",
        "Restore data\\ completely:" if whole else f"Restore {scope}:",
        f"  1. git clone {s['origin']} <repo>, then git -C <repo> checkout {head}",
    ]
    earlier = sorted(s["earlier_zips"], key=lambda u: (set_day(u), u))
    if earlier:
        lines += ["  2. the earlier zips that hold files of this snapshot unchanged, oldest first:"]
        for url in earlier:
            root = ZIP_ROOTS.get(url[len(BUCKET) + 1:], "")
            into = "<repo>" + ("\\" + root.strip("/").replace("/", "\\") if root else "")
            lines += [f"       gcloud storage cp {url} .", f"       tar -x -f {url.rsplit('/', 1)[1]} -C {into}"]
    lines += [f"  {3 if earlier else 2}. these zips into <repo>"
              + (", after the earlier ones, so that newer versions replace older ones:" if earlier else ":")]
    for z in s["zips"]:
        lines += [f"       gcloud storage cp {s['bucket']}{z['zip']} .", f"       tar -x -f {z['zip']} -C <repo>"]
    lines += [
        "  Their paths start with data\\. Before upload, Windows tar extracted each zip to a pipe and gave exactly",
        "  the bytes it was made from. Files that the earlier zips hold but the manifest does not list had been",
        "  removed or moved by the snapshot.",
        "",
        "Not copied:",
    ]
    lines += [f"  {u}  (this account could not read the folder)" for u in s["unreadable"]]
    lines += [f"  {root}  ({why})" for root, why in s["excluded"].items()]
    if not whole:
        lines += [f"  the rest of data\\  (outside this set's scope, {scope})"]
    if s["changed_while_read"] or s["removed"]:
        lines += ["", "Changed while being read (the zip holds the bytes read) or removed before it:"]
        lines += [f"  {p}" for p in s["changed_while_read"] + s["removed"]]
    lines += [
        "",
        "Storage class COLDLINE: billed for at least 90 days; each download adds a small retrieval fee.",
        "",
        "Rights: third-party data under its own terms. Several sources were collected against their sites' terms, on",
        "the owner's decisions, for non-commercial research (data\\data_map.yaml lists each dataset's rights). This is",
        "a private backup; do not make the bucket or the files public.",
    ]
    return "\n".join(lines) + "\n"


def upload(out: Path, day: str) -> None:
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    dest = f"{BUCKET}/{PREFIX}/{day}/"
    env = {**os.environ, "CLOUDSDK_STORAGE_PARALLEL_COMPOSITE_UPLOAD_ENABLED": "False"}
    objects = []
    for p in [out / z["zip"] for z in summary["zips"]] + [out / n for n in ("manifest.csv.gz", "summary.json",
                                                                                "README.txt")]:
        md5 = hashlib.md5()
        with open(p, "rb") as f:
            while b := f.read(CHUNK):
                md5.update(b)
        local = base64.b64encode(md5.digest()).decode()
        print(f"uploading {p.name} ({p.stat().st_size / 1e9:.2f} GB)", flush=True)
        subprocess.run([GCLOUD, "storage", "cp", "--no-clobber", "--storage-class=COLDLINE", str(p), dest],
                       check=True, env=env)
        meta = json.loads(run(GCLOUD, "storage", "objects", "describe", dest + p.name, "--format=json").stdout)
        if (int(meta["size"]), meta.get("md5_hash"), meta["storage_class"]) != (p.stat().st_size, local, "COLDLINE"):
            raise SystemExit(f"{p.name}: the object differs: size {meta['size']}, MD5 {meta.get('md5_hash')} "
                             f"(local {local}), class {meta['storage_class']}")
        objects.append({"object": dest + p.name, "bytes": int(meta["size"]), "md5": local,
                        "storage_class": meta["storage_class"], "created": meta["creation_time"]})
        print("  checked: size, MD5 and storage class agree", flush=True)
    sha = {z["zip"]: z["sha256"] for z in summary["zips"]}
    record = {"made": day, "snapshot": summary["snapshot"], "head": summary["head"], "bucket": dest,
              "groups": summary.get("groups", list(GROUPS)), "by_status": summary["by_status"],
              "objects": [{**o, "sha256": sha.get(o["object"].rsplit("/", 1)[1])} for o in objects]}
    with open(K.OUT / "backups.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["plan", "pack", "verify", "upload"])
    ap.add_argument("--date", default=Date.today().isoformat())
    ap.add_argument("--groups", default=",".join(GROUPS),
                    help="plan only: the zips to make (default all three); raw,dump copies the downloads alone")
    a = ap.parse_args()
    if not set(a.groups.split(",")) <= set(GROUPS):
        ap.error(f"--groups takes some of {','.join(GROUPS)}")
    groups = tuple(g for g in GROUPS if g in a.groups.split(","))
    out = BACKUPS / a.date
    {"plan": lambda: plan(out, a.date, groups), "pack": lambda: pack(out), "verify": lambda: verify(out, a.date),
     "upload": lambda: upload(out, a.date)}[a.step]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
