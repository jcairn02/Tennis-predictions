"""B3-referee, F11/F12/F13: every flagged odds row against its raw tennis-data row, and the proposed exchange simulated.

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f11_f13_rows.csv, f11_f13_summary.json and
f11_stage1_scan.csv.

For each match_id in the odds agent's a07 (reversed/garbled), a04 (average above maximum), a06 winner-swapped and
placeholder tables:
  * the live (7 Oct) Stage 1 row: link, td_file, td_row, prices for A and B;
  * the raw tennis-data row (data/dump/odds/tennis_data_couk/...): every bookmaker pair on it, ranks, set scores, comment;
  * p(A) by every individual book, by the average and by the maximum; ranks; Stage 0's result;
  * the exchange simulated: average (and maximum) of A and B swapped; does the new average agree with the books, sit
    at or under the maximum on both sides, and keep its overround (an exchange never changes it)?
Also: the whole 7 Oct Stage 1 scanned for the same signature (average opposed by >= 2 agreeing books, > 0.20 away; or
average above the maximum by > 0.10 on a side) to see whether rows outside the model frame share it.
Only p_avg_a (AvgW/AvgL de-vigged) reaches the model's odds_logit (checked: in_odds_logit == logit(p_avg_a), 30 Sep).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
ODDS = ROOT / "data/studies/input_data_audit/odds"
S1 = ROOT / "data/studies/predictability_diagnostic/stage1_odds.parquet"
S0 = ROOT / "data/studies/predictability_diagnostic"

PAIRS = ["Avg", "Max", "B365", "PS", "EX", "LB", "SJ", "CB", "GB", "IW", "SB", "UB", "B&W"]


def num(s):
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v > 1.0)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s1 = pd.read_parquet(S1)
    p = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=["match_id", "side", "player_name", "rank", "won"])
    a = p[p.side.eq("A")].set_index("match_id")
    b = p[p.side.eq("B")].set_index("match_id")
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "score", "status", "tournament_name", "round"])
    m = m.set_index("match_id")

    flagged = []
    for f, tag in [("a07_avg_vs_books.csv", None), ("a04_avg_gt_max.csv", "avg_gt_max"),
                   ("a06_winner_swapped.csv", "winner_swapped_link"), ("a06_placeholders.csv", "placeholder_or_status")]:
        t = pd.read_csv(ODDS / f)
        for r in t.itertuples():
            flagged.append((r.match_id, getattr(r, "flag", None) if tag is None else tag, f))
    fl = pd.DataFrame(flagged, columns=["match_id", "flag", "table"])
    fl = fl.groupby("match_id").agg(flags=("flag", lambda s: "+".join(sorted(set(map(str, s))))),
                                    tables=("table", lambda s: "+".join(sorted(set(s))))).reset_index()

    raw_cache: dict[str, pd.DataFrame] = {}
    rows = []
    for r in fl.itertuples():
        s = s1[s1.match_id.eq(r.match_id)]
        if s.empty:
            rows.append({"match_id": r.match_id, "flags": r.flags, "in_stage1_oct07": False})
            continue
        s = s.iloc[0]
        f = str(s.td_file)
        if f not in raw_cache:
            raw_cache[f] = pd.read_parquet(ROOT / f)
        raw = raw_cache[f].iloc[int(s.td_row)]
        a_won = bool(a.loc[r.match_id, "won"])
        a_is_w = (not a_won) if s.link == "winner_swapped" else a_won
        rec = {"match_id": r.match_id, "flags": r.flags, "tables": r.tables, "in_stage1_oct07": True,
               "tournament": m.loc[r.match_id, "tournament_name"], "round": m.loc[r.match_id, "round"],
               "stage0_score": m.loc[r.match_id, "score"], "stage0_status": m.loc[r.match_id, "status"],
               "name_a": a.loc[r.match_id, "player_name"], "name_b": b.loc[r.match_id, "player_name"],
               "a_won": a_won, "rank_a": a.loc[r.match_id, "rank"], "rank_b": b.loc[r.match_id, "rank"],
               "link": s.link, "td_file": f, "td_row": int(s.td_row), "td_winner": raw.get("Winner"),
               "td_loser": raw.get("Loser"), "td_wrank": raw.get("WRank"), "td_lrank": raw.get("LRank"),
               "td_sets": " ".join(f"{raw.get(f'W{k}')}-{raw.get(f'L{k}')}" for k in range(1, 6)
                                   if pd.notna(raw.get(f"W{k}")) and str(raw.get(f"W{k}")) not in ("", "nan")),
               "td_comment": raw.get("Comment"), "a_is_td_winner": a_is_w,
               "stage1_avg_a": s.avg_a, "stage1_avg_b": s.avg_b, "stage1_max_a": s.max_a, "stage1_max_b": s.max_b,
               "stage1_p_avg_a": s.p_avg_a}
        books = {}
        for k in PAIRS:
            w, l_ = num(pd.Series([raw.get(f"{k}W")])).iloc[0], num(pd.Series([raw.get(f"{k}L")])).iloc[0]
            if pd.isna(w) or pd.isna(l_):
                continue
            oa, ob = (w, l_) if a_is_w else (l_, w)
            books[k] = (oa, ob, (1 / oa) / (1 / oa + 1 / ob))
            rec[f"{k}_a"], rec[f"{k}_b"], rec[f"p_{k}"] = oa, ob, round(books[k][2], 4)
        refs = {k: v for k, v in books.items() if k not in ("Avg", "Max")}
        pr = np.array([v[2] for v in refs.values()]) if refs else np.array([])
        rec["n_books"] = len(refs)
        rec["books_median_p_a"] = float(np.median(pr)) if len(pr) else np.nan
        rec["books_spread"] = float(pr.max() - pr.min()) if len(pr) else np.nan
        if "Avg" in books:
            oa, ob, pa = books["Avg"]
            rec["avg_dev_from_books"] = abs(pa - rec["books_median_p_a"]) if len(pr) else np.nan
            rec["avg_after_exchange_p_a"] = 1 - pa
            rec["avg_after_exchange_dev"] = abs(1 - pa - rec["books_median_p_a"]) if len(pr) else np.nan
            rec["books_all_oppose_avg"] = bool(len(pr) and ((pr - 0.5) * (pa - 0.5) < 0).all())
            rec["overround_avg"] = 1 / oa + 1 / ob
            if "Max" in books:
                ma, mb, pm = books["Max"]
                rec["avg_above_max_a"], rec["avg_above_max_b"] = oa - ma, ob - mb
                rec["after_exchange_avg_above_max_a"], rec["after_exchange_avg_above_max_b"] = ob - ma, oa - mb
                rec["max_dev_from_books"] = abs(pm - rec["books_median_p_a"]) if len(pr) else np.nan
                rec["max_after_exchange_dev"] = abs(1 - pm - rec["books_median_p_a"]) if len(pr) else np.nan
                rec["after_both_exchanged_avg_above_max"] = max(ob - mb, oa - ma)
            # Max >= every individual book on each side (as an OddsPortal maximum should be, allowing 0.05)
            if "Max" in books and refs:
                ma, mb, _ = books["Max"]
                rec["max_below_a_book_a"] = bool(any(v[0] > ma + 0.05 for v in refs.values()))
                rec["max_below_a_book_b"] = bool(any(v[1] > mb + 0.05 for v in refs.values()))
                rec["exchanged_max_below_a_book"] = bool(any(v[0] > mb + 0.05 or v[1] > ma + 0.05 for v in refs.values()))
        rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "f11_f13_rows.csv", index=False)

    # ---- whole Stage 1 scan for the same signature ----
    frame = set(pd.read_parquet(ROOT / "data/studies/surface_rating_race/model/model_frame.parquet",
                                columns=["match_id"]).match_id)
    lk = s1[s1.td_file.notna()].copy()
    scan = []
    for f, g in lk.groupby("td_file"):
        raw = raw_cache.get(f)
        if raw is None:
            raw = pd.read_parquet(ROOT / f)
        r = raw.iloc[g.td_row.astype(int).to_numpy()].reset_index(drop=True)
        g = g.reset_index(drop=True)
        a_won = g.match_id.map(a.won).astype(bool).to_numpy()
        a_is_w = np.where(g.link.eq("winner_swapped"), ~a_won, a_won)

        def pa(k):
            if f"{k}W" not in r:
                return np.full(len(g), np.nan)
            w, l_ = num(r[f"{k}W"]).to_numpy(float), num(r[f"{k}L"]).to_numpy(float)
            pw = (1 / w) / (1 / w + 1 / l_)
            return np.where(a_is_w, pw, 1 - pw)

        P = pd.DataFrame({k: pa(k) for k in PAIRS})
        refs = P.drop(columns=["Avg", "Max"])
        n = refs.notna().sum(axis=1)
        med = refs.median(axis=1)
        spread = refs.max(axis=1) - refs.min(axis=1)
        opp = ((refs.sub(0.5).mul(P.Avg - 0.5, axis=0) < 0) | refs.isna()).all(axis=1)
        far = ((refs.sub(P.Avg, axis=0).abs() > 0.20) | refs.isna()).all(axis=1)
        rev2 = opp & far & (n >= 2) & (spread <= 0.15)
        ga = g.avg_a.to_numpy(float) - g.max_a.to_numpy(float)
        gb = g.avg_b.to_numpy(float) - g.max_b.to_numpy(float)
        gt = (np.nan_to_num(ga, nan=-9) > 0.10) | (np.nan_to_num(gb, nan=-9) > 0.10)
        sel = rev2.to_numpy() | gt
        for i in np.flatnonzero(sel):
            scan.append({"match_id": g.match_id[i], "td_file": f, "td_row": int(g.td_row[i]), "in_model_frame": g.match_id[i] in frame,
                         "reversed_vs_2plus_books": bool(rev2.iloc[i]), "avg_above_max_gt_0.10": bool(gt[i]),
                         "p_avg_a": P.Avg.iloc[i], "books_median": med.iloc[i], "n_books": int(n.iloc[i]),
                         "p_max_a": P.Max.iloc[i], "avg_a": g.avg_a[i], "avg_b": g.avg_b[i], "max_a": g.max_a[i], "max_b": g.max_b[i]})
    sc = pd.DataFrame(scan)
    sc.to_csv(OUT / "f11_stage1_scan.csv", index=False)
    summ = {"flagged_match_ids": int(len(out)), "in_stage1_oct07": int(out.in_stage1_oct07.sum()),
            "stage1_scan_rows": int(len(sc)),
            "stage1_scan_in_frame": int(sc.in_model_frame.sum()) if len(sc) else 0,
            "stage1_scan": sc.to_dict("records")}
    (OUT / "f11_f13_summary.json").write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
    pd.set_option("display.width", 400)
    pd.set_option("display.max_columns", 80)
    pd.set_option("display.max_colwidth", 40)
    print(out.drop(columns=[c for c in out.columns if c.startswith("p_") is False and c.endswith(("_a", "_b"))
                            and c.split("_")[0] in [k for k in PAIRS]], errors="ignore").to_string())
    print(sc.to_string())


if __name__ == "__main__":
    main()
