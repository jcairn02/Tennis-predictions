"""Task 1/5: which workbook bytes each Stage 1 build read. For every tour/season: the last successful download before the
30 Sep build (2026-09-30T21:25:39Z) and after it, and whether today's file is the same bytes.
Output: out/a13_receipts.csv
"""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd

from _common import OUTD, RAW, ROOT

rows = [json.loads(l) for l in open(RAW / "_receipts.jsonl", encoding="utf-8")]
by = defaultdict(list)
for r in rows:
    by[r.get("name")].append(r)
cut = "2026-09-30T21:25:39+00:00"
out = []
for n in sorted(by):
    if not (n.startswith("atp/") or n.startswith("wta/")):
        continue
    ok = [r for r in by[n] if not r.get("error") and r.get("sha256")]
    fails = [r for r in by[n] if r.get("error") and r["retrieved_at"] <= cut]
    b = [r for r in ok if r["retrieved_at"] <= cut]
    a = [r for r in ok if r["retrieved_at"] > cut]
    b, a = (b[-1] if b else None), (a[-1] if a else None)
    dest = ROOT / (a or b or {"dest": "missing"})["dest"]
    cur = hashlib.sha256(dest.read_bytes()).hexdigest() if dest.is_file() else None
    out.append({"name": n, "on_30sep_route": b and b.get("route"), "on_30sep_wayback": b and b.get("wayback_timestamp"),
                "on_30sep_sha": b and b["sha256"][:12], "failed_attempts_before_30sep": "; ".join(r["error"] for r in fails)[:120],
                "after_route": a and a.get("route"), "after_retrieved": a and a["retrieved_at"][:10],
                "after_last_modified": a and a.get("last_modified"), "current_sha": cur and cur[:12],
                "current_equals_30sep": bool(b and cur == b["sha256"])})
out = pd.DataFrame(out)
out.to_csv(OUTD / "a13_receipts.csv", index=False)
pd.set_option("display.width", 250)
print(out[out["name"].str[-4:].astype(int) >= 2013].to_string())
