"""The six context inputs and the odds input of chosen matches, as the frames build them.

Context (tabpfn_thinking/build_frame.py): tour, surface and level codes (tabpfn_thinking/common.CODES; the level from
Stage 4's level group), indoor (indoor_fill/status.py: the rule computes on all of Stage 0 and filters to the ids, so a
call for the chosen matches gives the full call's values), the scheduled best-of (build_frame.scheduled_best_of: event
metadata, never the score) and the round's order. Whether the match belongs to the frame's population (main tour, a
supported format, completed or retired) is returned beside them.

Tour-level and Slam qualifying (the owner, 22 Oct 2026: docs/decisions/2026-10-22-qualifying-bets.md) is predicted and
bet with the live model, its inputs built as the qualifying-targets study built them (src/eda/qualifying_targets/
frame.py): Stage 4's groups TQ and GSQ coded 6 and 7 (the event-levels study's codes; training holds GS 0 .. T250 4
only), best of 5 where Stage 0 records 5 for a men's Slam qualifying match, else the scheduled 3, and Stage 0's round
order (Q1 1, Q2 2, Q3 3). `bettable` marks the main tour and that qualifying.

The odds input (current_best_model/odds_input.rewrite): in_odds_logit = log(p / (1 - p)) of the margin-free Pinnacle-
first chance of A. Live: Pinnacle's current line, margin removed (BetOnline's while Pinnacle has none); a replay: the
instance's own price for the match.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

QUALIFYING_LEVELS = {"TQ": 6.0, "GSQ": 7.0}      # Stage 4's groups of tour-level and Slam qualifying, and their codes


def inputs(target_ids, group: pd.Series) -> tuple[dict, pd.DataFrame]:
    """group: Stage 4's level group by match id (stage4_features.prepare's rows["group"], side A)."""
    from src.eda.indoor_fill import status as IF
    from src.eda.predictability_diagnostic import common as C
    from src.eda.tabpfn_thinking import build_frame as BF
    from src.eda.tabpfn_thinking import common as T
    ids = pd.Index(np.asarray(target_ids).astype(str))
    m = pd.read_parquet(C.MATCHES, columns=BF.MATCH_COLS + ["tour", "year", "status"])
    m["match_id"] = m["match_id"].astype(str)
    m = m.set_index("match_id").reindex(ids).reset_index()
    if m["tour"].isna().any():
        raise RuntimeError(f"{int(m['tour'].isna().sum())} target matches are not in Stage 0")
    g = group.reindex(ids).to_numpy()
    meta = m.assign(group=g)
    bo, supported = BF.scheduled_best_of(meta)
    recorded = m["best_of"].astype("float64").to_numpy()
    bo = np.where((m["tour"].to_numpy() == "atp") & (g == "GSQ") & (recorded == 5), 5.0, bo)
    indoor, source = IF.for_matches(ids)
    out = {"tour": m["tour"].map(T.CODES["tour"]).astype("float64").to_numpy(),
           "surface": m["surface"].map(T.CODES["surface"]).astype("float64").to_numpy(),
           "level": pd.Series(g).map({**T.CODES["level"], **QUALIFYING_LEVELS}).astype("float64").to_numpy(),
           "indoor": np.asarray(indoor, dtype="float64"),
           "best_of": np.asarray(bo, dtype="float64"),
           "round": m["round_order"].astype("float64").to_numpy()}
    info = pd.DataFrame({"match_id": ids, "tour": m["tour"].to_numpy(), "group": g, "status": m["status"].to_numpy(),
                         "main": pd.Series(g).isin(T.MAIN_GROUPS).to_numpy(),
                         "qualifying": pd.Series(g).isin(list(QUALIFYING_LEVELS)).to_numpy(),
                         "format_supported": supported, "indoor_source": np.asarray(source, dtype=object)})
    info["bettable"] = info["main"] | info["qualifying"]
    info["frame_population"] = info["main"] & info["format_supported"] & info["status"].isin(["completed", "retired"])
    return out, info


def odds_logit(p) -> np.ndarray:
    """odds_input.rewrite's in_odds_logit, the same operations."""
    p = np.asarray(p, dtype="float64")
    if not ((p > 0) & (p < 1)).all():
        raise ValueError("every price must be strictly between 0 and 1")
    return np.log(p / (1.0 - p))
