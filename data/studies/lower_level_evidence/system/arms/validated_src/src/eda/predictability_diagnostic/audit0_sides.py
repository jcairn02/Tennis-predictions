"""Audit of Stage 0, check 7: sides A and B.

Side A should carry no information: the share of matches A won should be one half, and being A
should be unrelated to rank, to name and to winning. Measured on the built tables, overall, by
tour, level and year and among evaluation matches, with 95% (Wilson) intervals. The side is also
recomputed from the match id by the rule stage0.md states (one bit of SHA-256 of the match id
decides whether the lower-sorted player id is A), written here again.

Writes audit0/sides.json and audit0/sides_by_cell.csv.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_sides.py
"""
from __future__ import annotations

import hashlib
import sys
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

EVAL_LEVELS = ["GS", "FIN", "T1000", "T500", "T250", "CH"]


def chi2_half(k: np.ndarray, n: np.ndarray) -> dict:
    """Pearson chi-square that every cell's share is one half (df = number of cells), with the
    Wilson-Hilferty approximation of its upper tail."""
    e = n / 2
    stat = float((((k - e) ** 2) / e + (((n - k) - e) ** 2) / e).sum())
    df = len(n)
    z = ((stat / df) ** (1 / 3) - (1 - 2 / (9 * df))) / sqrt(2 / (9 * df))
    return {"cells": int(df), "chi2": round(stat, 1), "p_approx": round(0.5 * (1 - erf(z / sqrt(2))), 4)}


def shares(frame: pd.DataFrame, flag: str, by: list[str] | None = None) -> dict | list:
    if not by:
        return A.binom_share(int(frame[flag].sum()), len(frame))
    return [dict(zip(by, k if isinstance(k, tuple) else (k,)), **A.binom_share(int(g[flag].sum()), len(g)))
            for k, g in frame.groupby(by)]


def main() -> int:
    m = A.load_matches(["match_id", "tour", "level", "qualifying", "year", "evaluation", "player_a_id", "player_b_id",
                        "a_won"]).set_index("match_id")
    mp = A.load_players(["match_id", "player_id", "side", "won", "player_name", "rank", "age", "seed"])
    pa = mp[mp["side"].eq("A")].set_index("match_id").add_prefix("A_")
    pb = mp[mp["side"].eq("B")].set_index("match_id").add_prefix("B_")
    x = m.join(pa).join(pb)

    # the tables agree with each other
    per = mp.groupby("match_id").agg(rows=("side", "size"), sides=("side", lambda s: "".join(sorted(s))),
                                     wins=("won", "sum"))
    lo = np.where(x["player_a_id"] < x["player_b_id"], x["player_a_id"], x["player_b_id"])
    hi = np.where(x["player_a_id"] < x["player_b_id"], x["player_b_id"], x["player_a_id"])
    low_is_a = np.array([int(hashlib.sha256(k.encode("utf-8")).hexdigest()[:8], 16) % 2 == 0 for k in x.index])
    recomputed_a = np.where(low_is_a, lo, hi)
    structure = {
        "matches": int(len(m)), "player_rows": int(len(mp)),
        "two_rows_one_A_one_B_one_winner": int(((per["rows"] == 2) & (per["sides"] == "AB") & (per["wins"] == 1)).sum()),
        "A_row_is_player_a_id": int((x["A_player_id"] == x["player_a_id"]).sum()),
        "A_row_won_equals_a_won": int((x["A_won"].astype(bool) == x["a_won"].astype(bool)).sum()),
        "side_recomputed_from_match_id_agrees": int((recomputed_a == x["player_a_id"].to_numpy()).sum()),
        "match_id_holds_the_two_sorted_ids": int(pd.Series([k.split("|")[-2:] == [a, b] for k, a, b in
                                                            zip(x.index, lo, hi)]).sum()),
    }

    x["a_won"] = x["a_won"].astype(bool)
    ev = x[x["evaluation"]]
    cells = x.groupby(["tour", "level", "year"])["a_won"].agg(["sum", "size"]).rename(columns={"sum": "a_won", "size": "n"})
    cells = cells.reset_index()
    ci = [A.binom_share(int(k), int(n)) for k, n in zip(cells["a_won"], cells["n"])]
    cells["share"], cells["lo"], cells["hi"] = [c["share"] for c in ci], [c["lo"] for c in ci], [c["hi"] for c in ci]
    cells["outside_95"] = (cells["lo"] > 0.5) | (cells["hi"] < 0.5)
    cells.to_csv(A.out_dir() / "sides_by_cell.csv", index=False)

    # rank: among matches where both players are ranked, is A the better-ranked player half the time,
    # and does the better-ranked player win equally often from either side?
    r = x[x["A_rank"].notna() & x["B_rank"].notna() & (x["A_rank"] != x["B_rank"])].copy()
    r["a_better"] = r["A_rank"] < r["B_rank"]
    r["better_won"] = np.where(r["a_better"], r["a_won"], ~r["a_won"])
    rev = r[r["evaluation"]]
    rank = {
        "matches_both_ranked": int(len(r)),
        "a_better_ranked": shares(r, "a_better"), "a_better_ranked_by_tour": shares(r, "a_better", ["tour"]),
        "a_better_ranked_evaluation_by_tour": shares(rev, "a_better", ["tour"]),
        "better_ranked_won_when_a": shares(r[r["a_better"]], "better_won"),
        "better_ranked_won_when_b": shares(r[~r["a_better"]], "better_won"),
        "a_rank_minus_b_rank_median": float((r["A_rank"] - r["B_rank"]).median()),
        "log_rank_ratio_mean": round(float(np.log(r["A_rank"] / r["B_rank"]).mean()), 4),
        "a_ranked_when_one_is": shares(x[x["A_rank"].notna() ^ x["B_rank"].notna()].assign(
            a_ranked=lambda f: f["A_rank"].notna()), "a_ranked"),
    }
    # names, ids, age and seeding
    nm = x.assign(a_first=x["A_player_name"].str.lower() < x["B_player_name"].str.lower(),
                  a_low_id=x["player_a_id"] < x["player_b_id"])
    older = x[x["A_age"].notna() & x["B_age"].notna() & (x["A_age"] != x["B_age"])].assign(
        a_older=lambda f: f["A_age"] > f["B_age"])
    seeded = x[x["A_seed"].notna() ^ x["B_seed"].notna()].assign(a_seeded=lambda f: f["A_seed"].notna())
    name = {"a_name_sorts_first": shares(nm, "a_first"), "a_name_sorts_first_evaluation": shares(nm[nm["evaluation"]], "a_first"),
            "a_has_the_lower_id": shares(nm, "a_low_id"),
            "a_won_when_a_name_sorts_first": shares(nm[nm["a_first"]], "a_won"),
            "a_won_when_b_name_sorts_first": shares(nm[~nm["a_first"]], "a_won"),
            "a_older": shares(older, "a_older"), "a_seeded_when_one_is": shares(seeded, "a_seeded")}

    summary = {
        "structure": structure,
        "a_won": {"all": shares(x, "a_won"), "by_tour": shares(x, "a_won", ["tour"]),
                  "evaluation_by_tour": shares(ev, "a_won", ["tour"]),
                  "evaluation_headline_by_tour": shares(ev[ev["year"] >= 2022], "a_won", ["tour"]),
                  "by_tour_level": shares(x, "a_won", ["tour", "level"]),
                  "cells_tour_level_year": int(len(cells)), "cells_outside_95": int(cells["outside_95"].sum()),
                  "chi2_all_cells_half": chi2_half(cells["a_won"].to_numpy(), cells["n"].to_numpy()),
                  "outside_cells": cells[cells["outside_95"]].to_dict(orient="records")},
        "rank": rank, "name_id_age_seed": name,
    }
    A.write_json("sides.json", summary)
    print(structure)
    print("A won", summary["a_won"]["all"], summary["a_won"]["evaluation_by_tour"])
    print("cells", summary["a_won"]["cells_tour_level_year"], "outside", summary["a_won"]["cells_outside_95"],
          summary["a_won"]["chi2_all_cells_half"])
    for k, v in rank.items():
        print(k, v)
    for k, v in name.items():
        print(k, v)
    return 0


if __name__ == "__main__":
    sys.exit(main())
