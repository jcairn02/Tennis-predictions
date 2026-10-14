"""R2-skeptic (round 2): the row's score against RG's own score, for every Stage 0 match of RG 2022-2026.

The override keeps the row's score (Stage 0 checks the box against it, B5 and B9, and the features read games and
sets from it). The Slam decision of 6 Oct replaced TML's score where it was wrong; this proposal does not look at
scores. Here each set of the row's score (games, and the tie-break points the row writes) is compared with RG's
match document (team sets: games and tie-break points), read from the raw row's winner's side.

Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/:
    scores.csv          one row per match: the row's score, RG's, what differs
    scores_summary.json counts by year, source and class
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/scores.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
TOK = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


def row_sets(score: str) -> tuple[list, list]:
    sets, other = [], []
    for t in str(score or "").replace(",", " ").split():
        m = TOK.match(t)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
        else:
            other.append(t.upper())
    return sets, other


def main() -> int:
    s = pd.read_parquet(OUT / "players.parquet")
    lead = pd.read_csv(LEAD / "whole_box_rows.csv", low_memory=False).drop_duplicates("match_id")[["match_id", "cls"]]
    w = s[s["side"].eq("w") & s["year"].ge(2022) & s["code"].notna()].merge(lead, on="match_id", how="left")
    rows = []
    for x in w.itertuples(index=False):
        rs, other = row_sets(x.raw_score)
        g, og = json.loads(x.rg_set_games), json.loads(x.rg_opp_set_games)
        t, ot = json.loads(x.rg_set_tb), json.loads(x.rg_opp_set_tb)
        rg = [(a, b, ta, tb) for a, b, ta, tb in zip(g, og, t, ot) if a is not None and b is not None]
        # RG lists a set at 0-0 when a retirement came before its first game; the row leaves it out
        while rg and rg[-1][0] == 0 and rg[-1][1] == 0 and len(rg) > len(rs):
            rg.pop()
        diff = []
        if len(rs) != len(rg):
            diff.append(f"sets {len(rs)} vs {len(rg)}")
        for i, (r, q) in enumerate(zip(rs, rg), 1):
            if (r[0], r[1]) != (q[0], q[1]):
                diff.append(f"set {i} games {r[0]}-{r[1]} vs {q[0]}-{q[1]}")
            elif r[2] is not None:
                loser_tb = q[3] if q[0] > q[1] else q[2]
                if loser_tb is not None and r[2] != loser_tb:
                    diff.append(f"set {i} tb {r[2]} vs {loser_tb}")
        ret_row = any(o.startswith("RET") for o in other)
        ret_rg = str(x.rg_end_cause or "").startswith("r") or str(x.rg_opp_end_cause or "").startswith("r")
        wo_rg = str(x.rg_end_cause or "").startswith("w") or str(x.rg_opp_end_cause or "").startswith("w")
        if ret_row != ret_rg and not wo_rg:
            diff.append(f"RET marker row {ret_row} rg {ret_rg}")
        rows.append({"match_id": x.match_id, "year": x.year, "tour": x.tour, "draw": x.draw, "round": x.round,
                     "code": x.code, "source": x.source, "cls": x.cls, "status": x.status, "row_score": x.raw_score,
                     "rg_sets": json.dumps(rg), "differs": "; ".join(diff)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "scores.csv", index=False)
    d = out[out["differs"].ne("")]
    summ = {"matches": int(len(out)), "differ": int(len(d)),
            "differ_by_year_source_class": d.groupby(["year", "source", "cls"]).size().rename("n").reset_index()
            .to_dict("records"),
            "differ_rows": d[["match_id", "code", "cls", "status", "row_score", "rg_sets", "differs"]].to_dict("records")}
    (OUT / "scores_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summ.items() if k != "differ_rows"}, indent=1, default=str))
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    print(d[["match_id", "code", "cls", "status", "row_score", "rg_sets", "differs"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
