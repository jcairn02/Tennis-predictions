"""Audit B of Stage 4, checks 6 and 7: claims that rest on groups under about 300 matches, and the plan's fingerprint.

    hashes          SHA-256 of candidates.md and stage4_candidates.csv, recomputed, against the values recorded in
                    stage4_features_summary.json, stage4_results.json and stage4.md; the files' modification times
                    beside the outputs' generation times
    small groups    from stage4_results.csv: every group (era, level group, window, season) of fewer than 300 matches
                    by score; whether any row read "finding" needs an era of fewer than 300 matches to reach its three
                    positive eras; and the groups behind the specific claims stage4.md makes about eras, levels,
                    seasons and windows, with their sizes

Writes data/studies/predictability_diagnostic/audit4/claims.json.

Run: ./python.sh src/eda/predictability_diagnostic/audit4_claims.py   (seconds)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import audit4_common as A  # noqa: E402

SMALL = 300
# the claims stage4.md makes about groups (section, tour, row, score, group)
CLAIMS = [
    ("4: ratings through the iid model by era (men)", "atp", "rating_matchup", "single", "elo", ["2013-16", "2017-19", "2020-21", "2022-26"]),
    ("4: ratings through the iid model by era (women)", "wta", "rating_matchup", "single", "elo", ["2017-19", "2020-21", "2022-26"]),
    ("4: points matchup 52 weeks by era (men)", "atp", "mu_points", "52 weeks", "elo", ["2013-16", "2017-19", "2020-21", "2022-26"]),
    ("4: serve point from its parts 52 weeks, 2013-16 (men)", "atp", "mu_components", "52 weeks", "elo", ["2013-16"]),
    ("4: age by era (men)", "atp", "age", "single", "elo", ["2013-16", "2017-19", "2020-21", "2022-26"]),
    ("4: ratings through the iid model at the Grand Slams", "atp", "rating_matchup", "single", "elo", ["GS"]),
    ("4: ratings through the iid model at the Grand Slams (women)", "wta", "rating_matchup", "single", "elo", ["GS"]),
    ("4: the Tour Finals (men, full coverage)", "atp", "rating_matchup", "single", "elo", ["FIN"]),
    ("4: the Tour Finals (women)", "wta", "elo_games", "single", "elo", ["FIN"]),
    ("6: the ranking season by season (men)", "atp", "rank", "single", "elo", [f"season {y}" for y in range(2013, 2027)]),
    ("6: the ranking season by season (women)", "wta", "rank", "single", "elo", [f"season {y}" for y in range(2013, 2027)]),
    ("6: ranking, points, gap in 2022-2026", "atp", "rank", "single", "elo", ["2022-2026"]),
    ("3: the market table, 2022-2026 (women's ranking)", "wta", "rank", "single", "market", ["2022-2026"]),
    ("3: the market table, 2022-2026 (men's sets over 7 days)", "atp", "sets_7d", "single", "market", ["2022-2026"]),
    ("3: the market table, 2022-2026 (women's first matches on a surface)", "wta", "surface_first", "single", "market", ["2022-2026"]),
    ("3: the market table, 2022-2026 (women's days since)", "wta", "days_since", "single", "market", ["2022-2026"]),
    ("limitations: the leaders in 2019-2026", "atp", "rating_matchup", "single", "elo", ["2019-2026"]),
]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    plan, table = A.DOCS / "candidates.md", A.OUT / "stage4_candidates.csv"
    fs = json.loads((A.OUT / "stage4_features_summary.json").read_text(encoding="utf-8"))
    rs = json.loads((A.OUT / "stage4_results.json").read_text(encoding="utf-8"))
    md = (A.DOCS / "stage4.md").read_text(encoding="utf-8")
    h_plan, h_table = sha256(plan), sha256(table)
    hashes = {"candidates_md_now": h_plan, "candidates_csv_now": h_table,
              "features_summary": fs["plan"], "results": rs["plan"],
              "stage4_md_quotes_plan_hash": h_plan in md, "stage4_md_quotes_table_hash": h_table in md,
              "all_agree": h_plan == fs["plan"]["sha256"] == rs["plan"]["sha256"]
              and h_table == fs["plan"]["candidate_table_sha256"] == rs["plan"]["candidate_table_sha256"],
              "modified_utc": {p.name: pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").isoformat(timespec="seconds")
                               for p in (plan, table, A.OUT / "stage4_features.parquet", A.OUT / "stage4_results.json")},
              "generated_utc": {"stage4_features_summary.json": fs["generated_at"], "stage4_results.json": rs["generated_at"]},
              "plan_status_line": next((ln for ln in plan.read_text(encoding="utf-8").splitlines() if ln.startswith("**Status")), None)}

    R = pd.read_csv(A.OUT / "stage4_results.csv", low_memory=False)
    rank = pd.read_csv(A.OUT / "stage4_ranking.csv")
    small = {}
    for s in ("alone", "elo", "market"):
        n = pd.to_numeric(R[f"{s}_n"], errors="coerce")
        g = R[(n > 0) & (n < SMALL)]
        small[s] = {"groups": int(len(g)), "by_kind": g["group_kind"].value_counts().to_dict(),
                    "by_group_name": g["group_name"].value_counts().head(12).to_dict(),
                    "directional_flag_agrees": bool((R.loc[n > 0, f"{s}_directional"].astype(bool) == (n[n > 0] < SMALL)).all())}
    # findings that need a small era to reach three positive eras
    era = R[R["group_kind"].eq("era")]
    rest = []
    for r in rank[rank["reading"].eq("finding")].itertuples():
        e = era[era["tour"].eq(r.tour) & era["id"].eq(r.id) & era["form"].eq(r.form)]
        n = pd.to_numeric(e["elo_n"], errors="coerce")
        pos = e[(n > 0) & (pd.to_numeric(e["elo_imp"], errors="coerce") > 0)]
        pos_big = pos[pd.to_numeric(pos["elo_n"], errors="coerce") >= SMALL]
        if len(pos_big) < 3:
            rest.append({"tour": r.tour, "id": r.id, "form": r.form, "eras_positive": int(len(pos)),
                         "eras_positive_300_plus": int(len(pos_big)),
                         "small_eras": e.loc[n < SMALL, ["group_name", "elo_n", "elo_imp"]].to_dict("records")})
    # every era group under 300 among rows above the line given Elo
    above = rank[rank["elo_clears_line"].astype(bool)][["tour", "id", "form"]]
    e2 = era.merge(above, on=["tour", "id", "form"])
    small_eras_above_line = e2[pd.to_numeric(e2["elo_n"], errors="coerce").between(1, SMALL - 1)][
        ["tour", "id", "form", "group_name", "elo_n", "elo_imp"]].to_dict("records")
    # the claims stage4.md makes about groups
    claims = []
    for text, tour, cid, form, score, groups in CLAIMS:
        g = R[R["tour"].eq(tour) & R["id"].eq(cid) & R["form"].eq(form) & R["group_name"].isin(groups)]
        n = pd.to_numeric(g[f"{score}_n"], errors="coerce")
        claims.append({"claim": text, "groups": dict(zip(g["group_name"], n.astype(int))), "smallest": int(n.min()) if len(n) else None,
                       "under_300": int((n < SMALL).sum())})
    # the Tour Finals: their sizes per tour (Stage 4 writes "285 at most" for the women, "315" for the men)
    fin = R[R["group_name"].eq("FIN")]
    fin_n = {t: {"max": int(pd.to_numeric(fin.loc[fin["tour"].eq(t), "elo_n"], errors="coerce").max()),
                 "rows_under_300": int((pd.to_numeric(fin.loc[fin["tour"].eq(t), "elo_n"], errors="coerce") < SMALL).sum()),
                 "rows": int(fin["tour"].eq(t).sum())} for t in ("atp", "wta")}
    # the second training minimum (300 non-zero training matches), added after the first run: the rows and seasons it
    # alone leaves out (training of 300 or more, but under 300 non-zero), with each row's reading
    second = []
    pat = re.compile(r"(\d{4}) \((\d+) matches; training (\d+), non-zero (\d+)\)")
    for s in ("alone", "elo", "market"):
        for r in rank.itertuples():
            txt = getattr(r, f"{s}_skipped_seasons")
            if not isinstance(txt, str):
                continue
            hit = [(int(y), int(n)) for y, n, tr, nz in pat.findall(txt) if int(tr) >= SMALL and int(nz) < SMALL]
            if hit:
                second.append({"tour": r.tour, "id": r.id, "form": r.form, "score": s, "reading": r.reading,
                               "rank_given_elo": None if pd.isna(r.rank_given_elo) else int(r.rank_given_elo), "seasons_left_out": [y for y, _ in hit],
                               "matches_left_out": int(sum(n for _, n in hit))})
    out = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "hashes": hashes,
           "small_groups": small, "findings_needing_a_small_era": rest, "small_eras_of_rows_above_the_line": small_eras_above_line,
           "claims": claims, "tour_finals": fin_n, "second_minimum": second}
    A.save_json(out, "claims.json")
    print(json.dumps({k: out[k] for k in ("hashes", "small_groups", "findings_needing_a_small_era", "tour_finals")}, indent=1, default=str)[:6000])
    for c in claims:
        print(c["claim"], "smallest", c["smallest"], "under 300:", c["under_300"])
    print("small eras of rows above the line:", len(small_eras_above_line))
    for r in small_eras_above_line[:20]:
        print(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
