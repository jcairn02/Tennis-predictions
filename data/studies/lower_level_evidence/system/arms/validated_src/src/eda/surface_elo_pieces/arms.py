"""The arms (input sets) of the TabPFN-3.5-Plus test, how each new input is computed, and how a match is flipped.

Every arm starts from the best 2026 model's 54 inputs (the closing odds' log-odds plus 53 pre-match inputs, the 22 IOS
ones leak-proof: src/eda/tabpfn_leakproof/). New inputs come from data/studies/surface_elo_pieces/pieces.parquet.

    base      the 54 inputs unchanged (the current best model's representation)
    primary   the evidence-based representation (strategy.md, as amended after the audit): elo_logit and surface_first
              out; in: overall Elo, the surface offset (its own piece), and two per-player pairs (this season's surface
              matches, days since the last surface match). Career surface counts and last season's form are left out:
              beside the offset they were worse or null in every design-year fit (audit S1)
    literal   the suggestion as written: overall Elo, the surface-only rating (Stage 1's, started at 1500) and four pairs
              (career surface matches, this season's surface matches, days since the last surface match, last
              season's surface form), in place of elo_logit and surface_first
    elo_only  ablation: primary's Elo change alone (elo_logit replaced by overall Elo and the surface offset)
    switch_only ablation: primary's switch change alone (surface_first replaced by the two pairs); elo_only and
              switch_only together make primary

Kinds: "diff" inputs are A - B (negated when A and B swap), "context" inputs describe the match (unchanged), "pair"
inputs come as an (A, B) couple and are exchanged when A and B swap.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.surface_elo_pieces import common as C
from src.eda.tabpfn_leakproof import common as LP
from src.eda.tabpfn_thinking import common as T

BASE = list(T.TABPFN_NAMES)                          # 54: odds_logit, the 47 differences, the 6 context columns
BASE_DIFF = set(T.DIFF) | {"odds_logit"}
BASE_CONTEXT = set(T.CONTEXT)
LAYOFF_CAP = 1095.0                                  # days (three years); a player never seen on the surface since 2010
FORM_PRIOR = 5.0                                     # pseudo-matches shrinking last season's form toward 0

NEW_DIFF = {
    "elo_overall": "overall Elo's log-odds that A wins (Stage 1's overall rating, retirements counted)",
    "elo_surf_offset": "the surface offsets' difference in log-odds, (D_A - D_B) ln10/400: each player's offset starts "
                       "at 0 and moves only on that surface (K tuned on 2013-2018); overall Elo plus this is the "
                       "surface-offset Elo's log-odds",
    "elo_surface": "surface-only Elo's log-odds (Stage 1's surface rating, moved only on that surface, started at 1500)",
}
PAIRS = {   # name -> description; columns are <name>_a and <name>_b
    "surf_career": "log(1 + the player's rated matches on this surface since 2010)",
    "surf_season": "log(1 + the player's played matches on this surface earlier this calendar season)",
    "surf_layoff": "log(1 + days since the player's last match on this surface), capped at 3 years (never: the cap)",
    "surf_form_prev": "last season's surface form: wins above overall Elo's expectation on this surface last calendar "
                      "season, divided by (matches + 5)",
}
PAIR_COLS = [f"{p}_{s}" for p in PAIRS for s in ("a", "b")]
SWITCH_COLS = [f"{p}_{s}" for p in ("surf_season", "surf_layoff") for s in ("a", "b")]


def _without(names, drop):
    return [n for n in names if n not in drop]


ARMS: dict[str, list[str]] = {
    "base": BASE,
    "primary": _without(BASE, {"elo_logit", "surface_first"}) + ["elo_overall", "elo_surf_offset"] + SWITCH_COLS,
    "literal": _without(BASE, {"elo_logit", "surface_first"}) + ["elo_overall", "elo_surface"] + PAIR_COLS,
    "elo_only": _without(BASE, {"elo_logit"}) + ["elo_overall", "elo_surf_offset"],
    "switch_only": _without(BASE, {"surface_first"}) + SWITCH_COLS,
}
# diagnostic arms without the closing odds: can TabPFN use the representation where the price does not already hold it?
ARMS["base_noodds"] = _without(ARMS["base"], {"odds_logit"})
ARMS["primary_noodds"] = _without(ARMS["primary"], {"odds_logit"})
ANTISYMMETRIC = BASE_DIFF | set(NEW_DIFF)
SWAP = {f"{p}_a": f"{p}_b" for p in PAIRS} | {f"{p}_b": f"{p}_a" for p in PAIRS}


def new_inputs(pieces: pd.DataFrame) -> pd.DataFrame:
    """The new inputs for the matches in ``pieces`` (one row per match, columns of pieces.parquet)."""
    q = pieces
    s_a = np.where(np.isfinite(q["S_a"]), q["S_a"], q["R_a"])        # unknown surface: the overall rating
    s_b = np.where(np.isfinite(q["S_b"]), q["S_b"], q["R_b"])
    d_a, d_b = q["D_a"].fillna(0.0).to_numpy(), q["D_b"].fillna(0.0).to_numpy()
    out = pd.DataFrame(index=q.index)
    out["elo_overall"] = C.L10 * (q["R_a"] - q["R_b"]).to_numpy()
    out["elo_surf_offset"] = C.L10 * (d_a - d_b)
    out["elo_surface"] = C.L10 * (s_a - s_b)
    for s in ("a", "b"):
        out[f"surf_career_{s}"] = np.log1p(q[f"NS_{s}"].to_numpy(dtype="float64"))
        out[f"surf_season_{s}"] = np.log1p(q[f"season_n_{s}"].to_numpy(dtype="float64"))
        days = q[f"days_since_{s}"].to_numpy(dtype="float64")
        known = np.isfinite(q[f"season_n_{s}"].to_numpy(dtype="float64"))       # the surface is known
        out[f"surf_layoff_{s}"] = np.where(known, np.log1p(np.minimum(np.where(np.isfinite(days), days, LAYOFF_CAP),
                                                                      LAYOFF_CAP)), np.nan)
        out[f"surf_form_prev_{s}"] = (q[f"prev_res_{s}"] / (q[f"prev_n_{s}"] + FORM_PRIOR)).to_numpy(dtype="float64")
    return out


def flip(X: pd.DataFrame) -> pd.DataFrame:
    """The same matches with A and B swapped: differences negated, pairs exchanged, context unchanged."""
    out = X.copy()
    anti = [c for c in X.columns if c in ANTISYMMETRIC]
    out[anti] = -X[anti]
    for a, b in SWAP.items():
        if a in X.columns:
            out[a] = X[b].to_numpy()
    return out


def describe() -> dict:
    return {"arms": ARMS, "new_differences": NEW_DIFF, "pairs": PAIRS, "layoff_cap_days": LAYOFF_CAP,
            "form_prior_matches": FORM_PRIOR, "replaced_leakproof": LP.REPLACED,
            "amended_after_audit": "6 Oct 2026: primary and switch_only keep only the season and layoff pairs (S1); the "
                                   "offset enters as its own piece beside overall Elo (G2); elo_only is primary's Elo "
                                   "change alone"}
