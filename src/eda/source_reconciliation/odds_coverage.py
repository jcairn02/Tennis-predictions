"""Part F, step 1: which rows carry a stand-in, and which candidate prices exist on them. Reads no result.

    1. The template's frame (template_2026-10-14): how many rows carry BetOnline as their odds input, and how many carry
       neither Pinnacle nor BetOnline (the books' average), by tour and season, from its odds_input.json, recounted from
       model_frame.parquet, and rebuilt match by match with odds_input.construct on its per-source table.
    2. The gap rows (from 1 Aug 2025, no Pinnacle close): each candidate's coverage by tour and month, to the frame's
       last match (Sep 2026; coverage reads no result, so the sealed months are counted too, and flagged).

Writes data/studies/source_reconciliation/odds/: template_counts.json, template_counts.csv (tour, season, kind, rows),
coverage.csv (tour, month, candidate, rows, priced, share, sealed_rows), coverage.json (totals).
Run: ./python.sh src/eda/source_reconciliation/odds_coverage.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import odds_common as O  # noqa: E402

# Combinations whose coverage is reported (the declared ones of odds_score.py)
COMBOS = [["bol", "bfe"], ["bol", "pm"], ["bfe", "pm"], ["bol", "bfe", "pm"], ["bol", "bfe", "pm", "otmed"],
          ["bol", "psx"], ["bol", "bfe", "psx"], ["bol", "otmed"], ["bol", "b105"]]


def template_counts(df: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    rec = json.loads(O.ODDS_INPUT_JSON.read_text(encoding="utf-8"))
    frame = pd.read_parquet(O.FRAME, columns=["match_id", "tour", "season", "odds_input"])
    frame["match_id"] = frame["match_id"].astype(str)
    j = frame.merge(df[["match_id", "kind", "td_date", "sealed", "gap"]], on="match_id", how="left", validate="one_to_one")
    same = (j["odds_input"] == j["kind"])
    by = j.groupby(["tour", "season", "odds_input"]).size().rename("rows").reset_index()
    json_by = {k: v for k, v in rec["by_tour_season_source"].items()}
    frame_by = {f"{r.tour}|{r.season}|{r.odds_input}": int(r.rows) for r in by.itertuples()}
    standin = j["odds_input"].isin(O.STANDIN)
    gap_like = standin & (j["td_date"] >= O.GAP_FROM)
    out = {
        "template": str(O.TEMPLATE.relative_to(O.ROOT)).replace("\\", "/"),
        "frame_rows": int(len(frame)),
        "odds_input_json_by_source": rec["by_source"],
        "model_frame_by_source": {k: int(v) for k, v in frame["odds_input"].value_counts().items()},
        "json_equals_frame_by_tour_season_source": json_by == frame_by,
        "rebuilt_with_construct_equal_rows": int(same.sum()),
        "rebuilt_with_construct_differ_rows": int((~same).sum()),
        "betonline_rows": int((j["odds_input"] == "betonline").sum()),
        "neither_pinnacle_nor_betonline_rows": int((j["odds_input"] == "average").sum()),
        "standin_rows_from_2025_08": {
            "betonline": int((gap_like & (j["odds_input"] == "betonline")).sum()),
            "average": int((gap_like & (j["odds_input"] == "average")).sum()),
            "before_seal": int((gap_like & ~j["sealed"]).sum()), "sealed": int((gap_like & j["sealed"]).sum())},
        "standin_rows_before_2025_08": {
            "betonline": int((standin & (j["td_date"] < O.GAP_FROM) & (j["odds_input"] == "betonline")).sum()),
            "average": int((standin & (j["td_date"] < O.GAP_FROM) & (j["odds_input"] == "average")).sum())},
        "by_tour_kind_from_2025_08": {f"{t}|{k}": int(v) for (t, k), v in
                                      j[gap_like].groupby(["tour", "odds_input"]).size().items()},
        "by_month_kind_from_2025_08": {f"{m}|{k}": int(v) for (m, k), v in
                                       j[gap_like].assign(month=j["td_date"].dt.to_period("M").astype(str))
                                       .groupby(["month", "odds_input"]).size().items()},
        "share_of_rows_by_season": {
            str(s): {k: round(float(v), 4) for k, v in g["odds_input"].value_counts(normalize=True).items()}
            for s, g in j[j["season"] >= 2024].groupby("season")},
    }
    return out, by


def coverage(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    g = df[df["gap"]].copy()
    cands = {c: g[f"p_{c}"].to_numpy(float) for c in list(O.SINGLES) + list(O.ADDED)}
    for members in COMBOS:
        cands["eq_" + "+".join(members)] = O.equal(g, members)
    rows = []
    for (tour, month), idx in g.groupby(["tour", "month"]).groups.items():
        k = g.index.get_indexer(idx)
        sealed = int(g["sealed"].to_numpy()[k].sum())
        for name, p in cands.items():
            n = int(np.isfinite(p[k]).sum())
            rows.append({"tour": tour, "month": month, "candidate": name, "rows": int(len(k)), "priced": n,
                         "share": round(n / len(k), 4), "sealed_rows": sealed})
    cov = pd.DataFrame(rows).sort_values(["candidate", "tour", "month"]).reset_index(drop=True)
    tot = {}
    for scope, m in (("all_gap_rows", np.ones(len(g), bool)), ("before_seal", ~g["sealed"].to_numpy()),
                     ("sealed", g["sealed"].to_numpy())):
        tot[scope] = {"rows": int(m.sum()),
                      **{name: {"priced": int(np.isfinite(p[m]).sum()),
                                "share": round(float(np.isfinite(p[m]).mean()), 4) if m.any() else None}
                         for name, p in cands.items()}}
    by_tour = {t: {name: round(float(np.isfinite(p[(g["tour"] == t).to_numpy()]).mean()), 4)
                   for name, p in cands.items()} for t in sorted(g["tour"].unique())}
    other_books = {s: int(np.isfinite(g[f"p_{s}"].to_numpy(float)).sum()) for s in O.ot_books(df)}
    info = {"totals": tot, "share_by_tour_all_gap_rows": by_tour,
            "gap_definition": "td_date >= 2025-08-01 and the model's input is BetOnline or the average "
                              "(odds_input.construct: no reconciled Pinnacle close)",
            "otmed_books_left_out": O.OT_LEFT_OUT,
            "oddstrader_other_books_pricing_gap_rows": {k: v for k, v in sorted(other_books.items(),
                                                                                 key=lambda kv: -kv[1]) if v},
            "other_books_per_gap_row_median_by_month": {m: float(v) for m, v in
                                                        g.groupby("month")["n_ot_other"].median().items()}}
    return cov, info


def main() -> int:
    O.OUT.mkdir(parents=True, exist_ok=True)
    df = O.load_table()
    counts, by = template_counts(df)
    O.write_json(O.OUT / "template_counts.json", counts)
    by.to_csv(O.OUT / "template_counts.csv", index=False)
    cov, info = coverage(df)
    cov.to_csv(O.OUT / "coverage.csv", index=False)
    info["inputs_sha256"] = O.sha_inputs()
    O.write_json(O.OUT / "coverage.json", info)
    print(json.dumps({k: counts[k] for k in ("betonline_rows", "neither_pinnacle_nor_betonline_rows",
                                             "standin_rows_from_2025_08", "rebuilt_with_construct_differ_rows",
                                             "json_equals_frame_by_tour_season_source")}, indent=1))
    print(json.dumps(info["totals"]["before_seal"], indent=0)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
