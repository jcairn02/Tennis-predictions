"""Red team: run binj_redo (independent) on 2013-2024 and compare with the frozen dump (frozen_dump.py).
Run: ./python.sh src/eda/feature_interactions/redteam/redo_run.py   (no result read; a_won never loaded)"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import SOURCES  # noqa: E402
from src.eda.feature_interactions.redteam import binj_redo as R  # noqa: E402

OUT = C.OUT / "redteam"


def model_frame(max_season: int = 2024) -> pd.DataFrame:
    f = pd.read_parquet(C.MODEL_FRAME, columns=["match_id", "season", "tour"])
    f = f[f["season"].between(2013, max_season)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    m = pd.read_parquet(SOURCES["stage0_matches"], columns=["match_id", "player_a_id", "player_b_id"])
    m["match_id"] = m["match_id"].astype(str)
    f = f.merge(m, on="match_id", how="left", validate="one_to_one")
    pc = pd.read_parquet(SOURCES["pieces"], columns=["match_id", "R_a", "R_b"])
    pc["match_id"] = pc["match_id"].astype(str)
    f = f.merge(pc.rename(columns={"R_a": "elo_R_a", "R_b": "elo_R_b"}), on="match_id", how="left")
    return f


def pieces_with_a() -> pd.DataFrame:
    pc = pd.read_parquet(SOURCES["pieces"], columns=["match_id", "R_a", "R_b"])
    pc["match_id"] = pc["match_id"].astype(str)
    m = pd.read_parquet(SOURCES["stage0_matches"], columns=["match_id", "player_a_id"])
    m["match_id"] = m["match_id"].astype(str)
    return pc.merge(m.rename(columns={"player_a_id": "pa"}), on="match_id", how="left")


def compare(a, b, name):
    a, b = np.asarray(a, float), np.asarray(b, float)
    both = np.isfinite(a) & np.isfinite(b)
    d = np.abs(a - b)[both]
    nan_mis = int((np.isfinite(a) != np.isfinite(b)).sum())
    print(f"{name:14s} max|d| {d.max() if len(d) else np.nan:.3e}  n>1e-9 {int((d > 1e-9).sum()):6d}  "
          f"NaN-mismatch {nan_mis}  (redo NaN {int((~np.isfinite(a)).sum())}, frozen NaN {int((~np.isfinite(b)).sum())})")


def main(opt=None) -> dict:
    warnings.simplefilter("ignore")
    opt = opt or R.OPT
    L = long_table()
    M = model_frame()
    out = R.build(L, M, pieces_with_a(), opt)
    Fz = pd.read_parquet(OUT / "frozen_binj_2024.parquet")
    assert (Fz["match_id"].to_numpy() == M["match_id"].to_numpy()).all()
    cols = {k: v for k, v in out.items() if not k.startswith("_") and np.ndim(v) == 1 and len(v) == len(M)}
    pd.DataFrame({"match_id": M["match_id"], "season": M["season"], "tour": M["tour"]} | cols).to_parquet(
        OUT / "redo_binj_2024.parquet", index=False)
    return {"out": out, "Fz": Fz, "M": M, "L": L}


if __name__ == "__main__":
    r = main()
    o, Fz = r["out"], r["Fz"]
    for mine, theirs in (("U_a", "prep__bdinj_U_a"), ("U_b", "prep__bdinj_U_b"), ("inj_a", "prep__bdinj_inj_a"),
                         ("rust_a", "prep__bdinj_rust0_a"), ("elo_ret_a", "prep__bdinj_elo_ret_a"),
                         ("dec_a", "prep__bdinj_dec_a"), ("dec_b", "prep__bdinj_dec_b"),
                         ("d43", "tab__bdinj_I043"), ("d44", "tab__bdinj_I044"), ("d45", "tab__bdinj_I045"),
                         ("x", "x")):
        compare(o[mine], Fz[theirs], f"{mine}~{theirs[6:] if theirs != 'x' else 'x'}")
