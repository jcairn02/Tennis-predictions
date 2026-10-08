"""Harness verifier: the history's within-player order (bug B3) and the proposed fix, result-free.

history.long_table sorts each player's matches by the clock's best-estimate day `obs` first. For undated matches obs is
an estimate, and it can put a later round of the same event before an earlier one (a qualifier's Q3 before its Q2, a
QF before an R16): prior(...) then reads a match that had not yet been played. The fix sorts events by the player's
first best-estimate day at the event and rounds by round_order inside it; rest_days uses the running maximum of obs.

Run: ./python.sh src/eda/feature_interactions/verify/history_order.py
Writes data/studies/feature_interactions/verify/history_order.json
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402


def reorder(L: pd.DataFrame) -> pd.DataFrame:
    """The proposed fix, applied to long_table()'s output (the same lines would replace its sort)."""
    L = L.copy()
    L["ev_obs"] = L.groupby(["player_id", "tournament_id", "tday"])["obs"].transform("min")
    L = L.sort_values(["player_id", "ev_obs", "tday", "tournament_id", "round_order", "match_num"], kind="stable")
    L["k"] = L.groupby("player_id").cumcount()
    g = L.groupby("player_id")
    L["obs_mono"] = g["obs"].cummax()
    L["rest_days"] = L["obs_mono"] - g["obs_mono"].shift(1)
    L["rest_min"] = L["es"] - g["lf"].shift(1)
    return L.reset_index(drop=True)


def reversals(L: pd.DataFrame) -> pd.Series:
    g = L.groupby("player_id")
    same = (g["tournament_id"].shift(1) == L["tournament_id"]) & (g["tday"].shift(1) == L["tday"])
    return same & (g["round_order"].shift(1) > L["round_order"])


def main() -> int:
    warnings.simplefilter("ignore")
    model_ids = set(pd.read_parquet(C.MODEL_FRAME, columns=["match_id"])["match_id"].astype(str))
    L0 = long_table()
    L1 = reorder(L0)
    out = {}
    for tag, L in (("current", L0), ("fixed", L1)):
        rev = reversals(L)
        ism = L["match_id"].isin(model_ids)
        L = L.assign(prev_id=L.groupby("player_id")["match_id"].shift(1))
        out[tag] = {"rows": int(len(L)), "round_reversals": int(rev.sum()), "at_model_rows": int((rev & ism).sum()),
                    "negative_rest_days": int((L["rest_days"] < 0).sum())}
        out[tag + "_prev"] = L.loc[ism, ["match_id", "player_id", "prev_id", "rest_days"]].set_index(["match_id", "player_id"])
    a, b = out.pop("current_prev"), out.pop("fixed_prev")
    j = a.join(b, lsuffix="_cur", rsuffix="_fix")
    out["model_rows"] = int(len(j))
    out["model_rows_prev_match_changes"] = int((j["prev_id_cur"].fillna("") != j["prev_id_fix"].fillna("")).sum())
    out["model_rows_rest_days_changes"] = int(((j["rest_days_cur"] - j["rest_days_fix"]).abs() > 1e-9).sum())
    C.write_json(C.OUT / "verify" / "history_order.json", out)
    C.log(str(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
