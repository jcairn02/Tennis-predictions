"""The race's arms (input sets), the TTT inputs, the frame and the flip.

Every arm starts from the best 2026 model's 54 inputs (the closing odds' log-odds plus 53 pre-match inputs, leak-proof
IOS), as built by the Elo-pieces study (data/studies/surface_elo_pieces/frame.parquet), and changes only the rating:

    base       the 54 inputs unchanged: Stage 1's surface Elo as the 70/30 blend (75/25 women), elo_logit, and
               surface_first (A's first matches on the surface this season minus B's)
    elo_off    the Elo-pieces study's primary: elo_logit and surface_first out; overall Elo, the surface offset (its own
               piece) and two per-player pairs (this season's surface matches, days since the last surface match) in
    ttt_blend  TrueSkill Through Time as decided (3 Oct 2026; leak-proof since 5 Oct): elo_logit replaced by the log-odds
               of its forecast, the 35/65 (men) or 30/70 (women) blend of a surface-only and an overall chain
    ttt_off    elo_off's structure with TTT in Elo's place: the surface-offset TTT's two parts (overall, offset) and the
               same two pairs, in place of elo_logit and surface_first
    both_off   exploratory: elo_off's and ttt_off's rating parts together, with the pairs

and each again without the closing odds (<arm>_noodds): can the model use the rating where no price holds it?

After the race, on the owner's decision of 6 Oct 2026 to swap the old Elo blend for the offset Elo in the model:

    sprof      the model as it stood that day: base with its 21 IOS profile inputs built per surface (the surface-IOS
               study's arm sprof, kept by the owner's decision of the same day)
    model      sprof with elo_off's swap: the model after the decision

TTT inputs, A minus B (negated when A and B swap):
    ttt_logit         logit of the decided TTT's P(A wins) (match_timing/ttt_timed.parquet, p_ttt_timed)
    ttt_overall       (mu_A - mu_B) / c, c = sqrt(2 + s2_A + so2_A + s2_B + so2_B): the overall skills' part of the
                      offset TTT's z
    ttt_surf_offset   (o_A - o_B) / c: the surface offsets' part; ttt_overall + ttt_surf_offset = z, P = Phi(z)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.special import logit

from src.eda.surface_elo_pieces import arms as EA
from src.eda.surface_rating_race import common as C
from src.eda.surface_rating_race import ttt_offset as TO

BASE = list(EA.BASE)
SWITCH_COLS = list(EA.SWITCH_COLS)
TTT_DIFF = {"ttt_logit": "logit of the decided TTT's forecast (blend of overall and surface-only chains)",
            "ttt_overall": "the offset TTT's overall part of z, (mu_A - mu_B) / c",
            "ttt_surf_offset": "the offset TTT's surface-offset part of z, (o_A - o_B) / c"}
EPS = 1e-9


def _without(names, drop):
    return [n for n in names if n not in drop]


ARMS: dict[str, list[str]] = {
    "base": BASE,
    "elo_off": list(EA.ARMS["primary"]),
    "ttt_blend": ["ttt_logit" if n == "elo_logit" else n for n in BASE],
    "ttt_off": _without(BASE, {"elo_logit", "surface_first"}) + ["ttt_overall", "ttt_surf_offset"] + SWITCH_COLS,
    "both_off": _without(BASE, {"elo_logit", "surface_first"}) + ["elo_overall", "elo_surf_offset", "ttt_overall",
                                                                  "ttt_surf_offset"] + SWITCH_COLS,
}
# The owner's decision of 6 Oct 2026 (docs/decisions/2026-10-06-offset-elo.md): the offset Elo goes into the model as
# it stands that day, i.e. on top of the surface IOS profile kept the same day (docs/decisions/2026-10-06-surface-ios-
# profile.md; the surface-IOS study's arm sprof, data/studies/surface_ios/arms/sprof.parquet). In the frame the
# surface-built profile inputs are sf_<name>; in the model they keep their names.
SPROF_ARM = C.ROOT / "data" / "studies" / "surface_ios" / "arms" / "sprof.parquet"
SPROF = [f"{k}_{s}" for k in ("iosO", "iosD", "prod") for s in ("ace", "df", "first_in", "first_won", "second_won",
                                                                  "hold", "bp_saved")]
ARMS["sprof"] = [f"sf_{n}" if n in SPROF else n for n in BASE]                 # the model before the swap
ARMS["model"] = [f"sf_{n}" if n in SPROF else n for n in ARMS["elo_off"]]      # the model after it
for _a in list(ARMS):
    if not _a.endswith("_noodds") and f"{_a}_noodds" not in ARMS:
        ARMS[f"{_a}_noodds"] = _without(ARMS[_a], {"odds_logit"})
NEEDS_OFFSET_TTT = {a for a, cols in ARMS.items() if "ttt_overall" in cols}
NEEDS_SPROF = {a for a, cols in ARMS.items() if any(c.startswith("sf_") for c in cols)}
ANTISYMMETRIC = set(EA.ANTISYMMETRIC) | set(TTT_DIFF) | {f"sf_{n}" for n in SPROF}


def flip(X: pd.DataFrame) -> pd.DataFrame:
    """The same matches with A and B swapped: differences negated, pairs exchanged, context unchanged."""
    out = X.copy()
    anti = [c for c in X.columns if c in ANTISYMMETRIC]
    out[anti] = -X[anti]
    for a, b in EA.SWAP.items():
        if a in X.columns:
            out[a] = X[b].to_numpy()
    return out


def ttt_inputs(match_ids: np.ndarray, with_offset: bool = True) -> pd.DataFrame:
    """The TTT inputs for the given matches (Stage 0's A/B orientation, as the frame's)."""
    d = pd.read_parquet(C.TTT_TIMED, columns=["match_id", "p_ttt_timed"])
    out = pd.DataFrame({"match_id": match_ids}).merge(d, on="match_id", how="left", validate="one_to_one")
    out["ttt_logit"] = logit(np.clip(out["p_ttt_timed"].to_numpy(dtype="float64"), EPS, 1 - EPS))
    if with_offset:
        o = pd.read_parquet(C.TTT_OFFSET)
        o = out[["match_id"]].merge(o, on="match_id", how="left", validate="one_to_one")
        _, z_over, z_off = TO.z_parts(o)
        out["ttt_overall"], out["ttt_surf_offset"] = z_over, z_off
    return out.drop(columns=["p_ttt_timed"])


def load_frame(with_offset: bool, with_sprof: bool = False) -> pd.DataFrame:
    """The Elo-pieces study's frame plus the TTT inputs (x_ prefixed, as the frame's inputs) and, when asked, the
    surface-built IOS profile inputs of the surface-IOS study's arm sprof (x_sf_<name>)."""
    f = pd.read_parquet(C.PIECES_FRAME)
    t = ttt_inputs(f["match_id"].to_numpy(), with_offset)
    for c in t.columns:
        if c != "match_id":
            f[f"x_{c}"] = t[c].to_numpy()
    if with_sprof:
        s = pd.read_parquet(SPROF_ARM, columns=["match_id"] + [f"in_{n}" for n in SPROF])
        s = f[["match_id"]].merge(s, on="match_id", how="left", validate="one_to_one")
        for n in SPROF:
            f[f"x_sf_{n}"] = s[f"in_{n}"].to_numpy(dtype="float64")
    return f


def matrix(frame: pd.DataFrame, arm: str) -> pd.DataFrame:
    return pd.DataFrame({n: frame[f"x_{n}"].to_numpy(dtype="float64") for n in ARMS[arm]})


def job_data(frame: pd.DataFrame, arm: str, season: int):
    """(X_train, y_train, X_test, test match ids): training 2013 .. season - 1, test = the season's matches."""
    tr = frame["season"].between(C.TRAIN_FROM, season - 1).to_numpy()
    te = (frame["season"] == season).to_numpy()
    X = matrix(frame, arm)
    return (X[tr].reset_index(drop=True), frame.loc[tr, "a_won"].astype("int64").to_numpy(),
            X[te].reset_index(drop=True), frame.loc[te, "match_id"].to_numpy())
