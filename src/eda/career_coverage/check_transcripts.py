"""Career-coverage study: check the ATP transcriptions against independent tournament lists.

A full-season transcription can silently drop whole tournaments (one split request ignored its date
filter and repeated the first half of the season). For every season a second, short request lists
only the tournaments (EventId|EventDate|EventType|match objects) into atp_event_lists/. This script
compares that list with the transcription and names what to re-fetch: tournaments listed but not
transcribed, and tournaments whose transcribed match count (byes included) differs.

Reads data/studies/career_coverage/{atp_activity_raw, atp_event_lists}/;
writes data/studies/career_coverage/transcript_check.json.
Run: ./python.sh src/eda/career_coverage/check_transcripts.py
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import build_coverage as B

LISTS = B.OUT / "atp_event_lists"


def listed(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        p = [x.strip() for x in line.strip().split("|")]
        if len(p) >= 4 and re.fullmatch(r"\w+", p[0]) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p[1]):
            out[p[0]] = {"date": p[1], "type": p[2], "n": int(p[3]) if p[3].isdigit() else None}
    return out


def transcribed(code: str, year: int) -> Counter:
    lines = B.season_matches(code, year, B.season_files(B.ATP_RAW, code).get(year, []), [])
    seen = {(m["event_id"], m["url"], m["round"], m["wl"], m["opp_code"], m["opp_first"], m["opp_last"]) for m in lines}
    return Counter(k[0] for k in seen)


def settled_by_refetch(code: str, year: int) -> set:
    """Tournaments named in a targeted re-fetch (_fix file): the narrowest, most careful read, so it
    settles a disagreement between the season transcription and the short list."""
    out = set()
    for f in B.season_files(B.ATP_RAW, code).get(year, []):
        if "_fix" in f.name:
            out |= {ln.split("|")[1].strip() for ln in f.read_text(encoding="utf-8").splitlines()
                    if ln.startswith(("T|", "NONE|"))}
    return out


def main():
    report, refetch = [], {}
    for path in sorted(LISTS.glob("*_*.txt")):
        code, year = path.stem.split("_")[0], int(path.stem.split("_")[1])
        want, have = listed(path), transcribed(code, year)
        # entries without matches (profit-sharing payments, a tournament not yet played) have nothing to
        # transcribe; entries in a window the reading tool could not see (B.UNREAD) cannot be checked
        start, end = B.UNREAD.get(code, ("9999", "9999"))
        want = {e: v for e, v in want.items() if v["n"] != 0 and not start <= v["date"] <= end}
        settled = settled_by_refetch(code, year)
        missing = sorted(e for e in want if e not in have and e not in settled)
        extra = sorted(e for e in have if e not in want and e not in settled)
        count_diff = sorted(e for e in want if e in have and e not in settled and want[e]["n"] is not None
                            and want[e]["n"] != have[e])
        report.append({"season": f"{code}_{year}", "listed": len(want), "transcribed": len(have),
                       "missing": missing, "extra": extra, "count_differs": count_diff,
                       "settled_by_refetch": sorted(settled)})
        if missing or count_diff:
            refetch[f"{code}_{year}"] = missing + count_diff
    (B.OUT / "transcript_check.json").write_text(json.dumps({"seasons": report, "refetch": refetch}, indent=1),
                                                 encoding="utf-8")
    bad = [r for r in report if r["missing"] or r["extra"] or r["count_differs"]]
    print(f"{len(report)} seasons checked; {len(bad)} differ")
    for r in bad:
        print(f"  {r['season']}: listed {r['listed']}, transcribed {r['transcribed']}; missing {r['missing']}; "
              f"extra {r['extra']}; count differs {r['count_differs']}")


if __name__ == "__main__":
    main()
