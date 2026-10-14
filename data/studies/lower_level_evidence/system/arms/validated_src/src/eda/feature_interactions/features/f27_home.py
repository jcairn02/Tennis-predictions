"""B-HOME, home crowd, travel and hype (math audit block; a 2-df Wald test, weight 0.5; fixed-like trait: the batch
permutes the players' countries within tour, M4): I-078 (two-sided) and I-079 (two-sided).

    venue    each model match's event country: Stage 4's hand-made table (stage4_country.event_country), else f23's
             SUPPLEMENT by event name, else the tour finals' host by year (f23.FINALS); Monte Carlo is coded Monaco
             (the club is in France: a stated limitation)
    H_X      1[X's country (Stage 0; Stage 4's ISO-to-IOC aliases) == the venue], missing when either is unknown
    g        1[level is a 250 or a 500] (fixed by the math audit)
    wc_X     1[X entered on a wild card]
Columns: c1 = (H_A - H_B) g (I-078's first column); c2 = H_A wc_A - H_B wc_B (I-079's primary). I-078's H x JL and
H x log rank columns are sensitivities, not built here.
Controls (the final family): dH, dwc, the home-missing difference, the nearest inputs (a fixed list: the permutation
re-runs this builder); eta-mod: g. Where the venue is unknown x is missing and the batch adds 1[missing] x eta (S11).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.feature_interactions.features import f20_fatigue as F
from src.eda.feature_interactions.features import f23_arrival as G

SMALL = ("T250", "T500")


def prepare_home(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    from src.eda.predictability_diagnostic import stage4_country as SC
    ev = pd.DataFrame({"tour": P["tour"].astype(str).to_numpy(), "year": P["season"].astype(int).to_numpy(),
                       "tournament_id": P["tournament_id"].astype(str).to_numpy(),
                       "tournament_name": P["tournament_name"].astype(str).to_numpy(),
                       "level": P["level"].astype(str).to_numpy()})
    s4 = SC.event_country(ev).astype("object").to_numpy()
    keys = ev["tournament_name"].map(SC.event_key).to_numpy()
    venue = []
    for i, r in enumerate(ev.itertuples(index=False)):
        c = G._code(s4[i]) if isinstance(s4[i], str) else None
        if c is None and keys[i] in G.SUPPLEMENT:
            c = G.SUPPLEMENT[keys[i]]
        if c is None and r.level == "FIN":
            c = next((cc for lo, hi, cc in G.FINALS.get(r.tour, []) if lo <= r.year <= hi), None)
        venue.append(c if c is not None else "")
    return {"bdh_venue": np.asarray(venue, dtype=object)}


_ALIAS = None


def _player_code(country) -> np.ndarray:
    """Stage 0's player country as a venue code ('' when unknown), vectorised (the permutation calls this often)."""
    global _ALIAS
    if _ALIAS is None:
        from src.eda.predictability_diagnostic import stage4_country as SC
        _ALIAS = {**G.ALIASES, **SC.PLAYER_ALIASES}
    s = pd.Series(np.asarray(country, dtype=object))
    s = s.map(lambda v: v if isinstance(v, str) else "")
    s = s.replace(_ALIAS)
    return np.where(s.isin(list(G.COUNTRY)), s, "").astype(object)


def home_parts(P: pd.DataFrame):
    venue = np.asarray(P["bdh_venue"], dtype=object)
    known_v = venue != ""
    out = []
    for side in "ab":
        pc = _player_code(P[f"country_{side}"].to_numpy(object))
        out.append(np.where(known_v & (pc != ""), (pc == venue).astype(float), np.nan))
    wca = (P["entry_a"].astype(str).to_numpy() == "WC").astype(float)
    wcb = (P["entry_b"].astype(str).to_numpy() == "WC").astype(float)
    g = P["level"].astype(str).isin(SMALL).to_numpy(float)
    return out[0], out[1], wca, wcb, g


def combine_home(P: pd.DataFrame) -> dict:
    ha, hb, wca, wcb, g = home_parts(P)
    c1 = (ha - hb) * g
    c2 = ha * wca - hb * wcb
    X = np.column_stack([c1, c2])
    named = {"home_a-b": np.nan_to_num(ha) - np.nan_to_num(hb), "wc_a-b": wca - wcb,
             "home_missing_a-b": F.miss_diff(ha, hb)}
    ctrl, names = F.controls(P, named, X, F.NEAREST.get("B-HOME") or NEAREST_HOME or None)
    mods = F.centre(P, g)[:, None]                   # the family's controls: dH, dwc, g eta, Std (no other sum x eta)
    return {"x": X, "controls": ctrl, "control_names": names, "eta_mod_controls": mods,
            "tabpfn": {"bdh_home_x_small": (c1, "diff", None), "bdh_home_x_wc": (c2, "diff", None)}}


NEAREST_HOME: list[str] = ["elo_overall", "elo_games", "ratings_iid"]   # fixed (also in f20.NEAREST["B-HOME"])

HYPOTHESES = [
    {"hid": "B-HOME", "master": "I-078+I-079", "kind": "W", "sign": "two", "weight": 0.5, "trait": "fixed",
     "trait_cols": ["country"], "deployment": "diff", "wald": True, "prepare": prepare_home, "combine": combine_home,
     "family": "14", "members": {"I-078": "two", "I-079": "two"}},
]
