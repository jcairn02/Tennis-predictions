"""R1-rederive: apply my scope to the staged Sackmann rows in memory with the project's replace_split
(src/eda/input_data_audit/corrections.py) and check the result. Nothing is written outside my folder.

Checks: every named row found once with its guards; serve points, aces, double faults and serve points won unchanged;
the three counts equal my values; Stage 0's per-side checks B1 (1stIn <= svpt), B2 (1stWon <= 1stIn),
B3 (2ndWon <= svpt - 1stIn), B6 (df <= svpt - 1stIn), B7 (ace <= 1stWon + 2ndWon) and the stricter
2ndWon + df <= svpt - 1stIn hold on every corrected side; nothing else in the rows changes.
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/apply_check.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import corrections as X  # noqa: E402

HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"


def main() -> None:
    scope = pd.read_csv(HERE / "scope.csv")
    files = sorted(scope["source_file"].unique())
    frames = []
    for rel in files:
        tour = "atp" if "/atp/" in rel else "wta"
        f = ROOT / "data" / "dump" / "matches" / "sackmann_archive" / tour / (Path(rel).stem + ".parquet")
        frames.append(pd.read_parquet(f))
    raw = pd.concat(frames, ignore_index=True)
    before = raw.copy()
    # the table: one row per match row, the guards from the source, the sides' three counts from my scope
    rows = []
    src = raw.set_index(["_source_file", "_row"])
    for (sf, sr), g in scope.groupby(["source_file", "source_row"]):
        s = src.loc[(sf, int(sr))]
        r = {"fix": g["fix"].iloc[0], "action": "replace_split", "source_file": sf, "source_row": int(sr),
             "tourney_id": s["tourney_id"], "round": s["round"], "winner_name": s["winner_name"],
             "loser_name": s["loser_name"]}
        for side in ("w", "l"):
            h = g[g["side"].eq(side)]
            r[f"{side}_svpt"] = s[f"{side}_svpt"]
            if len(h):
                r[f"{side}_ace"], r[f"{side}_df"] = s[f"{side}_ace"], s[f"{side}_df"]
                r[f"{side}_1stIn"] = int(h["first_in"].iloc[0])
                r[f"{side}_1stWon"] = int(h["first_won"].iloc[0])
                r[f"{side}_2ndWon"] = int(h["second_won"].iloc[0])
        rows.append(r)
    table = pd.DataFrame(rows).astype(object).where(lambda t: t.notna(), "")
    table = table.astype(str)
    after, done = X.apply_row_corrections(raw.copy(), table)
    changed = done["replace_split"]
    print("rows named:", len(table), "| rows changed:", len(changed))
    num = lambda s: pd.to_numeric(s.astype(str).str.strip().replace("", np.nan), errors="coerce")  # noqa: E731
    problems = []
    key = scope.set_index(["source_file", "source_row", "side"])
    a = after.set_index(["_source_file", "_row"])
    b = before.set_index(["_source_file", "_row"])
    for (sf, sr, side), r in key.iterrows():
        na, nb = a.loc[(sf, sr)], b.loc[(sf, sr)]
        got = [num(pd.Series([na[f"{side}_{c}"]])).iloc[0] for c in ("1stIn", "1stWon", "2ndWon")]
        if got != [r["first_in"], r["first_won"], r["second_won"]]:
            problems.append((sf, sr, side, "values", got))
        for c in ("svpt", "ace", "df", "SvGms", "bpSaved", "bpFaced"):
            if str(na[f"{side}_{c}"]) != str(nb[f"{side}_{c}"]):
                problems.append((sf, sr, side, c))
        spw_a = num(pd.Series([na[f"{side}_1stWon"]])).iloc[0] + num(pd.Series([na[f"{side}_2ndWon"]])).iloc[0]
        spw_b = num(pd.Series([nb[f"{side}_1stWon"]])).iloc[0] + num(pd.Series([nb[f"{side}_2ndWon"]])).iloc[0]
        if spw_a != spw_b:
            problems.append((sf, sr, side, "spw"))
        sv, fi, fw, sw = (num(pd.Series([na[f"{side}_{c}"]])).iloc[0] for c in ("svpt", "1stIn", "1stWon", "2ndWon"))
        ace, dfs = (num(pd.Series([na[f"{side}_{c}"]])).iloc[0] for c in ("ace", "df"))
        checks = {"B1": fi > sv, "B2": fw > fi, "B3": sw > sv - fi, "B6": dfs > sv - fi, "B7": ace > fw + sw,
                  "strict": sw + (0 if np.isnan(dfs) else dfs) > sv - fi}
        for k, v in checks.items():
            if bool(v):
                problems.append((sf, sr, side, k))
    # nothing else changed: compare every column outside the corrected sides' three counts
    split_cols = {f"{s}_{c}" for s in ("w", "l") for c in ("1stIn", "1stWon", "2ndWon")}
    other = [c for c in raw.columns if c not in split_cols]
    def norm(f: pd.DataFrame) -> pd.DataFrame:
        return f.astype(object).where(f.notna(), "").astype(str)
    diff_other = (norm(after[other]) != norm(before[other])).any(axis=1).sum()
    untouched = ~after.index.isin(changed)
    diff_untouched = (norm(after.loc[untouched]) != norm(before.loc[untouched])).any(axis=1).sum()
    print("problems:", len(problems), problems[:10])
    print("rows with any other column changed:", int(diff_other), "| rows outside the table changed:", int(diff_untouched))


if __name__ == "__main__":
    main()
