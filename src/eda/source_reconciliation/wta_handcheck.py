"""Hand checks of the WTA readers (rule 8 of the brief): for a seeded random sample of linked matches per reader, the raw
documents (data/raw/point_sources/wta/matches/<tid>_<year>/<MatchID>/<endpoint>.json.gz, as downloaded; never the
staged tables) are opened and summarised next to the reader's two rows and Stage 0's two players, so that a person can
check the counts and the orientation by eye.

What is printed per match:
    * the match list's players A/B (names, WTA ids) and Stage 0's players (names, ids, who won), and which API side the
      reader put on each Stage 0 player;
    * box (stats.json.gz): the setnum 0 row's raw fields for A and B;
    * event log (events.json.gz): straight from the raw records, per server id: Point/Ace/double-fault records, Ace
      records, Fault records without firstServe (double faults), Fault/Foot records with firstServe (first-serve
      faults), the number of Correction records, and the last scoring record's MatchScore; for a match with no
      Correction these raw counts must equal the recount's svpt, ace and df;
    * point-by-point (point-by-point.json.gz): points per feed server (blank on tiebreak points), the last point's
      sets.
The person's verdicts are written into REPORT_wta.md; this script records the keys and the side-by-side numbers in
box/wta_handcheck.json and adds the keys to each reader's JSON ("hand_check_keys").

Run: ./python.sh src/eda/source_reconciliation/wta_handcheck.py [--per-reader 6] [--seed 20261016]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import wta_common as WC  # noqa: E402

READERS = ["wta_api_box", "wta_api_slam_box", "wta_events_recount", "wta_pbp_recount", "wta_events_tbfill_recount"]
SHOW = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced", "sv_won"]


def raw(key: str, endpoint: str):
    tid, year, mid = key[4:].split("/")
    path = WC.RAW_WTA / "matches" / f"{tid}_{year}" / mid / f"{endpoint}.json.gz"
    if not path.exists():
        return None, path
    with gzip.open(path, "rt", encoding="utf-8") as h:
        return json.load(h), path


def raw_box(doc) -> dict | None:
    for row in doc if isinstance(doc, list) else []:
        if str(row.get("setnum")) == "0":
            keep = ["acesa", "acesb", "dblflta", "dblfltb", "totservplayeda", "totservplayedb", "ptsplayed1stserva",
                    "ptsplayed1stservb", "ptswon1stserva", "ptswon1stservb", "ptstotwonserva", "ptstotwonservb",
                    "servgamesplayeda", "servgamesplayedb", "breakptsplayeda", "breakptsplayedb", "breakptsconva",
                    "breakptsconvb"]
            return {k: row.get(k) for k in keep}
    return None


def raw_events(doc) -> dict:
    ev = sorted(doc.get("Events") or [], key=lambda e: e.get("Index") or 0)
    per = {}
    corrections = 0
    last_ms = None
    for e in ev:
        a = e.get("Attributes") or {}
        t = a.get("type") or e.get("Name")
        if t == "StateIndicator" and a.get("reason") == "Correction":
            corrections += 1
        srv = str(a.get("server") or "")
        if t in ("Point", "Ace", "Fault", "Foot") and srv:
            d = per.setdefault(srv, Counter())
            first = a.get("firstServe") is True
            if t == "Ace":
                d["ace"] += 1
                d["points"] += 1
            elif t == "Point":
                d["points"] += 1
            elif not first:
                d["df"] += 1
                d["points"] += 1
            else:
                d["first_serve_faults"] += 1
            if t in ("Point", "Ace") and first:
                d["points_flagged_first_serve"] += 1
            last_ms = e.get("MatchScore") or last_ms
    return {"per_server": {k: dict(v) for k, v in per.items()}, "corrections": corrections, "last_match_score": last_ms}


def raw_pbp(doc) -> dict:
    pts = doc.get("points") or []
    per = Counter(str(p.get("server") or "blank") for p in pts)
    last = pts[-1] if pts else {}
    sets = [(s.get("team"), s.get("setNumber"), s.get("score"), s.get("tieBreakScore"))
            for s in (last.get("scoreAfterPoint") or {}).get("sets") or []]
    return {"points": len(pts), "points_per_feed_server": dict(per), "last_point_sets": sets}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-reader", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20261016)
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)
    lst = WC.listing().set_index("source_key")
    s0m, s0p = WC.stage0_women()
    names = s0p.set_index(["match_id", "player_id"])["player_name"]
    out = {"seed": a.seed, "per_reader": a.per_reader, "readers": {}}
    for reader in READERS:
        f = pd.read_parquet(WC.READERS / f"{reader}.parquet")
        pool = f[f["complete"]] if f["complete"].any() else f
        if reader == "wta_events_tbfill_recount":
            pool = pool[pool["x_tb_filled"]]
        keys = list(rng.choice(sorted(pool["source_key"].unique()), size=min(a.per_reader, pool["source_key"].nunique()),
                               replace=False))
        # one match of the event-log reader with corrections, so the rewind is checked too
        if reader == "wta_events_recount":
            corr = pool[pool["x_rewound_points"] > 0]["source_key"].unique()
            keys.append(str(rng.choice(sorted(corr))))
        checks = []
        for key in keys:
            rows = f[f["source_key"] == key]
            li = lst.loc[key]
            mid = rows["match_id"].iloc[0]
            item = {"source_key": key, "match_id": mid,
                    "listing": {"A": [li["name_a"], str(li["PlayerIDA"])], "B": [li["name_b"], str(li["PlayerIDB"])],
                                "score": li.get("ScoreString"), "winner_code": li.get("Winner")},
                    "reader_rows": []}
            for _, r in rows.iterrows():
                item["reader_rows"].append({"player_id": r["player_id"], "stage0_name": names.get((mid, r["player_id"])),
                                            "api_side": r.get("x_api_side"), "s0_won": bool(r.get("x_s0_won")),
                                            **{c: (None if pd.isna(r[c]) else int(r[c])) for c in SHOW}})
            endpoint = {"wta_api_box": "stats", "wta_api_slam_box": "stats", "wta_events_recount": "events",
                        "wta_events_tbfill_recount": "events", "wta_pbp_recount": "point-by-point"}[reader]
            doc, path = raw(key, endpoint)
            item["raw_file"] = str(path.relative_to(C.ROOT)).replace("\\", "/")
            if doc is None:
                item["raw"] = "missing"
            elif endpoint == "stats":
                item["raw"] = raw_box(doc)
            elif endpoint == "events":
                item["raw"] = raw_events(doc)
                pdoc, _ = raw(key, "point-by-point")
                if reader == "wta_events_tbfill_recount" and pdoc is not None:
                    item["raw_point_by_point"] = raw_pbp(pdoc)
            else:
                item["raw"] = raw_pbp(doc)
            checks.append(item)
            print(json.dumps(item, ensure_ascii=False, default=str))
        out["readers"][reader] = checks
        jpath = WC.READERS / f"{reader}.json"
        j = json.loads(jpath.read_text(encoding="utf-8"))
        j["hand_check_keys"] = [c["source_key"] for c in checks]
        jpath.write_text(json.dumps(j, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    C.write_json(WC.BOX / "wta_handcheck.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
