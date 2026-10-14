"""R3-referee (follow-up), step 4: what the referees say about the differences the two bars treat differently.

Reads ref_rows.csv (referees.py). For every RG 2022-2026 match the lead proposes or leaves out as
referee_contradicts or statistics_short:
  * each player row's differences, RG's statistics against the row: per count the sign and size; the first-serve sign
    ('+' the row has more first serves in, '-' fewer, '0' the same with points won moved);
  * the match's pattern: 'blank' (no box in the row), 'plus' (a '+' side), 'minus_only' (only '-'/'0' sides),
    'both_minus' (both sides '-'), 'other_only' (the split equal on both sides, another count differs);
  * the whole-split test (round 1's joint test): where a referee holds every point of the row (Court Vision 2022 or a
    hand chart; serve points equal to RG's), the points it would have to reclassify to read RG's split (k_RG) and the
    row's (k_row), scored with the distribution of k where the truth is not disputed (RG 2019-2021, where RG = the
    row); per pattern and size, and a mixture estimate of the share of rows whose RG split is right;
  * the referees' votes on the other counts (aces, double faults, serve points, break points, service games) by sign.
Everything is computed over the refereed rows BEFORE the lead's referee exclusion, so that the share estimates how
often RG's value is right where no referee looks.

Writes bar_rows.csv, bar_matches.csv, bar_tests.csv and bar_summary.json into
data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/bar_analysis.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402

SPLIT = ["first_in", "first_won", "second_won"]
OTHER = ["svpt", "ace", "df", "bp_faced", "bp_saved", "sv_gms"]


def cats(d: pd.DataFrame, p: str, sv: str | None = None) -> np.ndarray:
    s = d[sv or f"{p}_svpt"].to_numpy(float)
    fi, fw, sw = (d[f"{p}_{c}"].to_numpy(float) for c in SPLIT)
    return np.stack([fw, fi - fw, sw, s - fi - sw], axis=-1)


def k_moves(d: pd.DataFrame, ref: str, rec: str) -> np.ndarray:
    return np.abs(cats(d, ref) - cats(d, rec)).sum(axis=1) / 2


def pmf_k(k: np.ndarray, alpha: float = 1.0):
    k = np.asarray(k, dtype=float)
    lam = max(np.mean(k), 0.25)
    vals, cnt = np.unique(k, return_counts=True)
    emp = dict(zip(vals, cnt))
    n = len(k)

    def f(x):
        geo = (1 / (1 + lam)) * (lam / (1 + lam)) ** x
        return (emp.get(x, 0) + alpha * geo) / (n + alpha)
    return f


def mixture(lo: np.ndarray, ls: np.ndarray) -> float:
    if len(lo) == 0:
        return float("nan")
    pi = 0.5
    for _ in range(300):
        r = pi * lo / (pi * lo + (1 - pi) * ls)
        pi = float(np.mean(r))
    return pi


def main() -> int:
    P = pd.read_csv(F.OUT / "ref_rows.csv", low_memory=False)
    P = P[P["season"].between(2019, 2026)].copy()
    P["d_first_in"] = P["raw_first_in"] - P["off_first_in"]
    split_moves = P["raw_first_won"].ne(P["off_first_won"]) | P["raw_second_won"].ne(P["off_second_won"])
    blank = P["raw_svpt"].isna()
    P["sign"] = "?"
    P.loc[blank, "sign"] = "blank"
    P.loc[~blank & P["d_first_in"].gt(0), "sign"] = "+"
    P.loc[~blank & P["d_first_in"].lt(0), "sign"] = "-"
    P.loc[~blank & P["d_first_in"].eq(0) & split_moves, "sign"] = "0"
    P.loc[~blank & P["d_first_in"].eq(0) & ~split_moves, "sign"] = "="
    P["n_changes"] = sum(P[f"raw_{c}"].ne(P[f"off_{c}"]) & P[f"raw_{c}"].notna() & P[f"off_{c}"].notna()
                         for c in SPLIT + OTHER)
    P["max_abs_d"] = pd.concat([(P[f"raw_{c}"] - P[f"off_{c}"]).abs() for c in SPLIT + OTHER[:-1]], axis=1).max(axis=1)
    # the match's pattern
    g = P.groupby(["source_file", "source_row"])
    signs = g["sign"].agg(lambda s: "".join(sorted(s)))
    P["match_signs"] = P.set_index(["source_file", "source_row"]).index.map(signs)

    def pattern(s: str) -> str:
        if "blank" in s:
            return "blank"
        if "+" in s:
            return "plus"
        if s == "--":
            return "both_minus"
        if "-" in s or "0" in s:
            return "minus_or_zero"
        return "other_only"
    P["pattern"] = P["match_signs"].map(pattern)
    P.to_csv(F.OUT / "bar_rows.csv", index=False)

    # ---------------------------------------------------------------- whole-split test, per referee
    tests, rows = [], []
    cal = {}
    for ref in ("cv", "mcp"):
        okyear = P["season"].isin([2019, 2020, 2022]) if ref == "cv" else pd.Series(True, index=P.index)
        base = P[okyear & P["season"].between(2019, 2021) & P[f"{ref}_svpt"].eq(P["off_svpt"])
                 & np.all([P[f"raw_{c}"].eq(P[f"off_{c}"]) for c in SPLIT + ["svpt"]], axis=0)]
        kc = k_moves(base, ref, "off")
        cal[ref] = {"rows": int(len(kc)), "k0": round(float(np.mean(kc == 0)), 3), "mean_k": round(float(np.mean(kc)), 2)}
        f = pmf_k(kc)
        S = P[okyear & P["season"].between(2022, 2026) & P["lead_cls"].isin(["proposed", "referee_contradicts"])
              & P["sign"].isin(["+", "-", "0"]) & P[f"{ref}_svpt"].eq(P["off_svpt"]) & P["raw_svpt"].eq(P["off_svpt"])
              & P[f"{ref}_first_in"].notna()].copy()
        S["k_RG"], S["k_row"] = k_moves(S, ref, "off"), k_moves(S, ref, "raw")
        S["lik_RG"] = [f(k) for k in S["k_RG"]]
        S["lik_row"] = [f(k) for k in S["k_row"]]
        S["ref"] = ref
        S["size"] = np.where(S["d_first_in"].abs().le(1), "|d|<=1", np.where(S["d_first_in"].abs().le(3), "|d|=2-3",
                                                                             "|d|>=4"))
        rows.append(S)
    S = pd.concat(rows, ignore_index=True)
    S[["ref", "season", "tour", "draw", "round", "code", "player", "side", "source_file", "source_row", "lead_cls",
       "sign", "pattern", "size", "raw_svpt", "raw_first_in", "raw_first_won", "raw_second_won", "off_first_in",
       "off_first_won", "off_second_won", "cv_first_in", "cv_first_won", "cv_second_won", "mcp_first_in",
       "mcp_first_won", "mcp_second_won", "k_RG", "k_row"]].to_csv(F.OUT / "bar_split_rows.csv", index=False)
    for keys in (["lead_cls"], ["sign"], ["pattern"], ["size"], ["sign", "size"], ["pattern", "sign"], ["ref", "sign"],
                 ["ref", "pattern"], ["season"]):
        for scope, T in (("all refereed (before the exclusion)", S),
                         ("proposed only", S[S["lead_cls"].eq("proposed")])):
            for k, h in T.groupby(keys):
                rec = {"scope": scope, **dict(zip(keys, k if isinstance(k, tuple) else (k,)))}
                rec.update({"rows": int(len(h)), "RG_closer": int((h["k_RG"] < h["k_row"]).sum()),
                            "row_closer": int((h["k_row"] < h["k_RG"]).sum()),
                            "tie": int((h["k_row"] == h["k_RG"]).sum()),
                            "RG_exact": int(h["k_RG"].eq(0).sum()), "row_exact": int(h["k_row"].eq(0).sum()),
                            "log10_LR_RG_vs_row": round(float(np.sum(np.log10(h["lik_RG"]) - np.log10(h["lik_row"]))), 1),
                            "share_RG_right": round(mixture(h["lik_RG"].to_numpy(float), h["lik_row"].to_numpy(float)), 3)})
                tests.append(rec)
    T = pd.DataFrame(tests)
    T.to_csv(F.OUT / "bar_tests.csv", index=False)

    # ---------------------------------------------------------------- the matches by pattern and size
    m = P[P["season"].between(2022, 2026)].drop_duplicates(["source_file", "source_row"])
    pm = m.groupby(["lead_cls", "pattern"]).size().rename("matches").reset_index()
    mx = P[P["season"].between(2022, 2026)].groupby(["source_file", "source_row"]).agg(
        lead_cls=("lead_cls", "first"), pattern=("pattern", "first"), season=("season", "first"), draw=("draw", "first"),
        tour=("tour", "first"), max_abs_d=("max_abs_d", "max"), n_changes=("n_changes", "sum"),
        refereed=("cv_svpt", lambda s: bool(s.notna().any()))).reset_index()
    mcp_any = P[P["season"].between(2022, 2026)].groupby(["source_file", "source_row"])["mcp_svpt"].apply(
        lambda s: bool(s.notna().any()))
    mx["refereed"] = mx["refereed"] | mx.set_index(["source_file", "source_row"]).index.map(mcp_any)
    mx.to_csv(F.OUT / "bar_matches.csv", index=False)
    prop = mx[mx["lead_cls"].eq("proposed")]
    smry = {
        "calibration_whole_split_2019_2021": cal,
        "matches_by_class_and_pattern": pm.to_dict("records"),
        "proposed_matches_by_pattern_and_max_difference": prop.assign(
            size=np.where(prop["max_abs_d"].isna(), "blank", np.where(prop["max_abs_d"].le(1), "max |d|<=1",
                                                                      np.where(prop["max_abs_d"].le(3), "max |d|=2-3",
                                                                               "max |d|>=4"))))
        .groupby(["pattern", "size"]).size().rename("matches").reset_index().to_dict("records"),
        "proposed_matches_refereed": int(prop["refereed"].sum()),
        "whole_split_tests": T[T["scope"].eq("all refereed (before the exclusion)")].to_dict("records"),
    }
    (F.OUT / "bar_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 300)
    print(json.dumps({k: v for k, v in smry.items() if k != "whole_split_tests"}, indent=1, default=str))
    print(T.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
