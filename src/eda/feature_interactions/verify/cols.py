"""Harness verifier: real candidate-like columns aligned to the screen's frame (no results are read).

    KN-*        the known-null set, built by screen_batch.build_all(P, L, pattern="p3_*.py") (KN-SDEV: 8 columns)
    S-IOS       centred (A + B) surface-IOS hold offence (levels.parquet) x in_iosD_hold; control in_iosD_hold
    S-AGE       centred (A + B) age x in_sets_14d; control in_sets_14d
    S-ELO       centred (A + B) overall Elo x in_elo_overall; control in_elo_overall (collinear with eta)
    HEIGHT      height_A - height_B (Stage 0, a fixed player trait, with missing values)
    IN-FORMDF   the model's own input in_form_df
    RAND        independent N(0, 1) per match (seed 7)

Run: ./python.sh src/eda/feature_interactions/verify/cols.py   (writes data/studies/feature_interactions/verify/cols.parquet)
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402

PATH = C.OUT / "verify" / "cols.parquet"
CONTROL = {"S-IOS": "in_iosD_hold", "S-AGE": "in_sets_14d", "S-ELO": "in_elo_overall"}


def build() -> pd.DataFrame:
    from src.eda.feature_interactions import screen_batch as SB
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    F = S.load(with_model=False)
    P = panel(max_season=2024)
    L = long_table()
    pos = pd.Series(np.arange(len(P)), index=P["match_id"]).reindex(F["match_id"]).to_numpy().astype(int)
    _, built = SB.build_all(P, L, pattern="p3_*.py")
    out = {"match_id": F["match_id"].to_numpy()}
    for hid, (x, *_rest) in built.items():
        X = np.asarray(x, float).reshape(len(P), -1)[pos]
        if X.shape[1] == 1:
            out[hid] = X[:, 0]
        else:
            for j in range(X.shape[1]):
                out[f"{hid}#{j}"] = X[:, j]
    lv = pd.read_parquet(C.FEATURES / "levels.parquet")
    lv["match_id"] = lv["match_id"].astype(str)
    lv = F[["match_id"]].merge(lv, on="match_id", how="left", validate="one_to_one")
    disc = (F["window"] == "discovery").to_numpy()
    for name, (mod, d) in {"S-IOS": ("lv_iosO_hold", "in_iosD_hold"), "S-AGE": ("lv_age", "in_sets_14d"),
                           "S-ELO": ("lv_elo", "in_elo_overall")}.items():
        s = lv[mod].to_numpy(float)
        out[name] = (s - np.nanmean(s[disc])) * F[d].to_numpy(float)
    out["HEIGHT"] = (P["height_a"].astype(float) - P["height_b"].astype(float)).to_numpy()[pos]
    out["IN-FORMDF"] = F["in_form_df"].to_numpy(float)
    out["RAND"] = np.random.default_rng(7).normal(size=len(F))
    return pd.DataFrame(out)


def load_cols() -> pd.DataFrame:
    return pd.read_parquet(PATH)


def hypothesis(F: pd.DataFrame, Kc: pd.DataFrame, name: str) -> S.Hypothesis:
    """The column as the batch would test it: its control (if any) and, when x has missing values, miss x eta."""
    assert (Kc["match_id"].to_numpy() == F["match_id"].to_numpy()).all()
    x = Kc[name].to_numpy(float)
    ctrl, names = [], []
    if name in CONTROL:
        ctrl.append(F[CONTROL[name]].to_numpy(float))
        names.append(CONTROL[name])
    miss = ~np.isfinite(x)
    if miss.any() and not miss.all():
        ctrl.append(miss.astype(float) * F["z_model"].to_numpy(float))
        names.append("miss x eta")
    Cm = np.column_stack(ctrl) if ctrl else None
    return S.Hypothesis(name, x, Cm, names, "+", trait="fixed" if name == "HEIGHT" else "none")


if __name__ == "__main__":
    warnings.simplefilter("ignore")
    K = build()
    K.to_parquet(PATH, index=False)
    C.log(f"cols: {K.shape}; coverage {K.drop(columns='match_id').notna().mean().round(3).to_dict()}")
