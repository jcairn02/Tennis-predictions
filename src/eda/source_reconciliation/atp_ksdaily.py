"""Reader atp_ks_daily: the daily serve-speed collector's 2026 key statistics (the ATP Stats Centre's current-season
files, decrypted).

Its staged tables (data/studies/serve_speed_tabpfn/live/staging/atp_daily_<date>.parquet) keep only the speeds and the
first serves in / attempts, not the box score. The full key statistics are in the collector's raw files
(data/raw/point_sources/infosys_atp_daily/<year>/<event>/keystats-api/<CODE>.json.gz), which it decrypts itself:
they are read here through the collector's own guarded decryption (serve_speed_tabpfn/live/atp_daily.decrypt_envelope:
2026 files only, never the backfill folder), in memory, read-only, as prediction_run/fills.py held_keystats() does.
As held on 16 Oct 2026: Shanghai 2026 (event 5014) only. The key statistics map as atp_keystats.py; complete = the
file's matchCompleted flag (it reads False on some finished matches: fills.py covers_match notes 9 of 82 at Shanghai
2026), with x_sv_games_fit saying whether the two players' service games fit Stage 0's score (tiebreaks counted or
not, within one, as Stage 0's check B5).
Orientation: the file's own player list (ATP codes, names), placed on Stage 0's sides by the event linker.

Run: ./python.sh src/eda/source_reconciliation/atp_ksdaily.py
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402
from src.eda.source_reconciliation import atp_keystats as K  # noqa: E402
from src.eda.source_reconciliation import atp_points as P  # noqa: E402

READER = "atp_ks_daily"


def read_files() -> pd.DataFrame:
    from src.eda.serve_speed_tabpfn.live import atp_daily as AD
    rows = []
    for path in sorted(A.DAILY_RAW.glob("*/*/keystats-api/*.json.gz")):
        meta = AD.parse_path(path)
        AD.guard(meta["year"], path)
        with gzip.open(path, "rt", encoding="utf-8") as f:
            env = json.load(f)
        doc = AD.decrypt_envelope(env, year=meta["year"], path=path)
        ks = doc.get("stats", doc) if isinstance(doc, dict) else {}
        pl = [p for p in (ks.get("players") or []) if isinstance(p, dict)]
        s0 = ((ks.get("setStats") or {}).get("set0")) or []
        stats = {e.get("name"): (e.get("player1"), e.get("player2")) for e in s0 if isinstance(e, dict)}
        r = {"source_key": f"{meta['year']}_{meta['event']}_{meta['mid']}", "file": str(path.relative_to(A.C.ROOT)),
             "year": meta["year"], "event": meta["event"], "code": meta["mid"],
             "matchCompleted": ks.get("matchCompleted"), "has_set0": bool(s0), "stats_json": json.dumps(stats)}
        for no, p in ((1, pl[0] if len(pl) > 0 else {}), (2, pl[1] if len(pl) > 1 else {})):
            r[f"c{no}"] = A.atp_code(p.get("player1Id"))
            r[f"f{no}"] = " ".join(x for x in (p.get("player1FirstName"), p.get("player1LastName")) if x)
            r[f"s{no}"] = p.get("player1Name") or ""
        r.update(K.counts(stats))
        rows.append(r)
    return pd.DataFrame(rows)


def sv_games_fit(sv1, sv2, sets) -> bool | None:
    if pd.isna(sv1) or pd.isna(sv2) or not isinstance(sets, tuple) or not sets:
        return None
    games = sum(a + b for a, b in sets)
    tbs = sum(1 for a, b in sets if {a, b} == {7, 6})
    tot = sv1 + sv2
    return bool(abs(tot - games) <= 1 or abs(tot - (games - tbs)) <= 1)


def main() -> int:
    d = read_files()
    info = {"reader": READER, "source": "data/raw/point_sources/infosys_atp_daily/<year>/<event>/keystats-api/"
                                        "<CODE>.json.gz (decrypted in memory by the collector's guarded routine)",
            "files_read": int(len(d)), "events": d["event"].value_counts().to_dict() if len(d) else {},
            "staged_tables_hold": "speeds and first serves in / attempts only (staging/atp_daily_<date>.parquet)"}
    d = d.set_index("source_key", drop=False)
    info["files_without_set0"] = int((~d["has_set0"]).sum())
    d = d[d["has_set0"]].copy()
    hint = [P.round_hint(c) for c in d["code"]]
    d["season"] = d["year"].astype(int)
    d["ev"] = pd.to_numeric(d["event"], errors="coerce").fillna(-1).astype(int)
    d["qual"] = [h[0] for h in hint]
    d["round"] = [h[1] for h in hint]
    linker = A.EventLinker()
    lk = linker.link(d, A.crosswalk())
    d = d.join(lk)
    info["linked"] = int(d["match_id"].notna().sum())
    info["link_methods"] = d["link_method"].value_counts().to_dict()
    info["unlinked"] = d.loc[d["match_id"].isna(), "unlinked_reason"].value_counts().to_dict()
    lm = d[d["match_id"].notna()].copy()
    ctx = P.stage0_context(lm["match_id"], lm["p1_side"])
    lm["x_sv_games_fit"] = [sv_games_fit(a, b, s) for a, b, s in zip(lm["sv_gms_1"], lm["sv_gms_2"], ctx["s0_sets"])]
    lm["complete"] = lm["matchCompleted"].fillna(False).astype(bool)
    lm["x_status"] = np.where(lm["complete"], "matchCompleted", "matchCompleted false")
    lm["x_season"] = lm["season"]
    lm["x_file"] = lm["file"]
    rows = A.long_rows(lm, A.FIELDS + ["x_first_won_den", "x_second_den", "x_sv_won_den", "x_spd1"],
                       extra=["complete", "link_method", "x_status", "x_season", "x_sv_games_fit", "x_file"])
    rows["x_code"] = pd.concat([lm["c1"], lm["c2"]], ignore_index=True).to_numpy()
    info["complete_flag"] = lm["complete"].value_counts().to_dict()
    info["sv_games_fit_the_score"] = lm["x_sv_games_fit"].astype(str).value_counts().to_dict()
    info["not_complete_but_sv_games_fit"] = int((~lm["complete"] & lm["x_sv_games_fit"].eq(True)).sum())
    info["winner_vs_stage0"] = None
    info["note_winner"] = "key statistics name no winner"
    A.write_reader(READER, A.to_contract(rows, READER, "box"), info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
