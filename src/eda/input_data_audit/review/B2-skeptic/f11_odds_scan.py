"""B2-skeptic review of F11-F13 (closing odds). Read-only.

For every Stage 1 row (7 Oct build) linked to a tennis-data.co.uk row, the raw row is re-read and every individual book
it prints (B365, B&W, BFE, CB, EX, GB, IW, LB, PS, SB, SJ, UB) is compared with the average (AvgW/AvgL, the only price
the model uses: p_mkt = p_avg_a) and the maximum (MaxW/MaxL). Oriented to tennis-data's W/L (not to Stage 0's A/B).

Hard facts that hold for a sound row (the average and maximum are OddsPortal's over a book set that includes the
printed books; tennis-data's own B365/PS columns are its own close, so small timing gaps are allowed):
    H1  AvgX <= MaxX on each side X                   (an average cannot exceed the maximum it averages)
    H2  MaxX >= every printed book's X price, within a tolerance calibrated on all rows
A row's average is REVERSED (candidate) when, with at least two printed books:
    R0  the stored average is far from the books: |p_avg - median p_books| >= 0.15;
    R1  every printed book's favourite is the opposite of the average's favourite;
    R2  the printed books agree with each other (implied-probability spread <= 0.10);
    R3  the exchanged average (AvgW<->AvgL) reproduces the books: |p_avg_exchanged - median p_books| <= 0.05;
    R4  after the exchange (and the max's, when the max is reversed) H1 and H2 hold on both sides.
The maximum is exchanged too when the stored order violates H2 on a side and the exchanged order violates it on none.
Note: H1/H2 cannot tell "average and maximum reversed" from "every printed book reversed" when avg and max move
together; ranks and Elo are then the deciding external evidence (printed for each row).

Writes data/studies/input_data_audit/fixes/B2-skeptic/:
    f11_raw_books.parquet     the per-row book table (all linked rows)
    f11_reversed_scan.csv     every row meeting R1-R4, with the max decision
    f11_flagged_rows.csv      the rows of the agent's a07/a04/a06 tables, with every book printed and the checks
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
ODDS_DIR = ROOT / "data/studies/input_data_audit/odds"
BOOKS = ["B365", "B&W", "BFE", "CB", "EX", "GB", "IW", "LB", "PS", "SB", "SJ", "UB"]


def num(s: pd.Series) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v > 1.0)


def load_raw(files: list[str]) -> pd.DataFrame:
    frames = []
    for f in files:
        d = pd.read_parquet(ROOT / f)
        keep = {"td_file": f, "td_row": np.arange(len(d)), "src_row": d.get("_row"), "src_file": d.get("_source_file"),
                "Winner": d["Winner"], "Loser": d["Loser"], "WRank": pd.to_numeric(d["WRank"], errors="coerce"),
                "LRank": pd.to_numeric(d["LRank"], errors="coerce"), "Comment": d["Comment"], "Date": d["Date"]}
        for b in BOOKS + ["Max", "Avg"]:
            for s in "WL":
                c = f"{b}{s}"
                keep[c] = num(d[c]) if c in d.columns else np.nan
        frames.append(pd.DataFrame(keep))
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    o = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage1_odds.parquet")
    o = o[o["td_file"].notna()].copy()
    o["td_row"] = o["td_row"].astype("int64")
    raw = load_raw(sorted(o["td_file"].astype(str).unique()))
    x = o.merge(raw, on=["td_file", "td_row"], how="left", validate="one_to_one")
    # implied probability that tennis-data's W wins, per book (normalised)
    for b in BOOKS + ["Max", "Avg"]:
        w, l_ = x[f"{b}W"], x[f"{b}L"]
        x[f"p_{b}"] = (1 / w) / (1 / w + 1 / l_)
    P = x[[f"p_{b}" for b in BOOKS]]
    x["n_books"] = P.notna().sum(axis=1)
    x["p_books_med"] = P.median(axis=1)
    x["books_spread"] = P.max(axis=1) - P.min(axis=1)
    bw = x[[f"{b}W" for b in BOOKS]]
    bl = x[[f"{b}L" for b in BOOKS]]
    x["book_max_W"], x["book_max_L"] = bw.max(axis=1), bl.max(axis=1)
    x["book_min_W"], x["book_min_L"] = bw.min(axis=1), bl.min(axis=1)
    # H1 / H2 as stored and as exchanged (relative shortfall: max below the best printed book)
    x["h1_stored"] = (x["AvgW"] <= x["MaxW"] + 1e-9) & (x["AvgL"] <= x["MaxL"] + 1e-9)
    x["h2_short_W"] = (x["book_max_W"] - x["MaxW"]) / x["book_max_W"]
    x["h2_short_L"] = (x["book_max_L"] - x["MaxL"]) / x["book_max_L"]
    x["h2_short_W_ex"] = (x["book_max_W"] - x["MaxL"]) / x["book_max_W"]
    x["h2_short_L_ex"] = (x["book_max_L"] - x["MaxW"]) / x["book_max_L"]
    sound = x["n_books"].ge(2) & x["AvgW"].notna() & x["MaxW"].notna()
    q = x.loc[sound, ["h2_short_W", "h2_short_L"]].stack().quantile([.5, .9, .99, .999, .9999])
    print("H2 shortfall quantiles (max below best printed book, share):", q.round(4).to_dict())
    tol = 0.10   # a max more than 10% below the best printed book on that side is a violation
    x["h2_bad_stored"] = (x["h2_short_W"] > tol) | (x["h2_short_L"] > tol)
    x["h2_bad_both_sides_stored"] = (x["h2_short_W"] > tol) & (x["h2_short_L"] > tol)
    x["h2_bad_exchanged"] = (x["h2_short_W_ex"] > tol) | (x["h2_short_L_ex"] > tol)
    print("rows with H1 failing (avg > max on a side):", int((~x["h1_stored"] & sound).sum()))
    print("rows with H2 failing as stored:", int((x["h2_bad_stored"] & sound).sum()),
          "| on both sides:", int((x["h2_bad_both_sides_stored"] & sound).sum()))
    # reversal of the average
    pa = x["p_Avg"]
    opp = ((P.sub(0.5).mul(pa - 0.5, axis=0) < 0) | P.isna()).all(axis=1) & x["n_books"].ge(2)
    x["R0"] = (pa - x["p_books_med"]).abs().ge(0.15)
    x["R1"] = opp
    x["R2"] = x["books_spread"].le(0.10)
    x["p_avg_exchanged"] = 1 - pa
    x["R3"] = (x["p_avg_exchanged"] - x["p_books_med"]).abs().le(0.05)
    x["max_exchange"] = x["h2_bad_stored"] & ~x["h2_bad_exchanged"]
    maxW_new = np.where(x["max_exchange"], x["MaxL"], x["MaxW"])
    maxL_new = np.where(x["max_exchange"], x["MaxW"], x["MaxL"])
    h2_after = np.where(x["max_exchange"], x["h2_bad_exchanged"], x["h2_bad_stored"])
    x["R4"] = (x["AvgL"] <= maxW_new + 1e-9) & (x["AvgW"] <= maxL_new + 1e-9) & ~h2_after
    x["stored_violates_hard_fact"] = ~x["h1_stored"] | x["h2_bad_stored"]
    x["reversed_certain"] = x["R0"] & x["R1"] & x["R2"] & x["R3"] & x["R4"]
    # ranks as a further, independent check: the lower-ranked number is the better player
    x["rank_fav_is_W"] = np.where(x["WRank"].notna() & x["LRank"].notna(), x["WRank"] < x["LRank"], np.nan)
    x["avg_fav_is_W"] = pa > 0.5
    x["books_fav_is_W"] = x["p_books_med"] > 0.5
    cols = ["match_id", "tour", "year", "level", "round", "link", "td_file", "td_row", "src_file", "src_row", "Winner",
            "Loser", "WRank", "LRank", "Comment", "AvgW", "AvgL", "MaxW", "MaxL"] + \
           [f"{b}{s}" for b in BOOKS for s in "WL"] + \
           ["n_books", "p_Avg", "p_avg_exchanged", "p_books_med", "books_spread", "p_Max", "h1_stored", "h2_short_W",
            "h2_short_L", "h2_bad_stored", "h2_bad_exchanged", "max_exchange", "stored_violates_hard_fact", "R0", "R1",
            "R2", "R3", "R4", "reversed_certain",
            "rank_fav_is_W", "books_fav_is_W", "avg_fav_is_W", "a_won_stage1"]
    x["a_won_stage1"] = np.nan
    x.to_parquet(OUT / "f11_raw_books.parquet", index=False)
    rev = x[x["reversed_certain"]]
    rev[[c for c in cols if c in rev.columns]].to_csv(OUT / "f11_reversed_scan.csv", index=False)
    print("reversed (R1-R4):", len(rev))
    print(rev[["match_id", "Winner", "Loser", "WRank", "LRank", "AvgW", "AvgL", "MaxW", "MaxL", "B365W", "B365L", "PSW",
               "PSL", "n_books", "p_Avg", "p_books_med", "books_spread", "max_exchange", "stored_violates_hard_fact"]].to_string())
    # partial: R1 with only one book, or R1+R2 without R3
    part = x[x["R0"] & x["R1"] & ~x["reversed_certain"]]
    print("\nR1 (all >=2 books opposite) but not certain:", len(part))
    print(part[["match_id", "Winner", "Loser", "WRank", "LRank", "AvgW", "AvgL", "MaxW", "MaxL", "B365W", "B365L", "PSW",
                "PSL", "n_books", "p_Avg", "p_books_med", "books_spread", "avg_coherent", "R2", "R3", "R4"]].to_string())
    # the agent's tables
    ids = set()
    for f in ["a07_avg_vs_books.csv", "a04_avg_gt_max.csv", "a06_winner_swapped.csv", "a06_placeholders.csv"]:
        t = pd.read_csv(ODDS_DIR / f)
        ids |= {(m, f) for m in t["match_id"]}
    src = pd.DataFrame(sorted(ids), columns=["match_id", "agent_table"])
    fl = src.merge(x, on="match_id", how="left")
    fl[["agent_table"] + [c for c in cols if c in fl.columns]].to_csv(OUT / "f11_flagged_rows.csv", index=False)


if __name__ == "__main__":
    main()
