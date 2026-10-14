"""The surface-IOS study's TabPFN plan: arms, seeds, test seasons and comparisons (read by dispatch.py and score.py).

A slot is one arm with one seed in one expanding window: trained on every main-tour match with closing odds from 2013 to
the season before the test season, queried on the test season. Every arm has the same rows; only its inputs differ.
The arm frames are written by arms.py (data/studies/surface_ios/arms/<arm>.parquet).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.eda.surface_ios import common as C
from src.eda.tabpfn_thinking import common as T

PHASES = {"validation": (2019, 2020, 2021),      # to choose the representation, before any test season is scored
          "test": (2022, 2023, 2024, 2025, 2026)}  # the owner's five expanding windows
YEARS = PHASES["test"]
SEEDS = (0, 1, 2, 3)                          # local fits are free: four seeds per arm and season, averaged
BASE54 = list(T.TABPFN_NAMES)                 # the odds' log-odds, then the 53 inputs, in the model's order
CONTEXT = set(T.CONTEXT)                      # tour, surface, level, indoor, best_of, round: unchanged by the swap

PROFILE = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved")
PRIORITY = ("spw", "hold", "first_won", "ace")  # the suggestion's four: return points won, breaks, return v first, aces

ARMS: dict[str, dict] = {
    "base": {"columns": BASE54,
             "desc": "the best 2026 model's 54 inputs with the leak-proof IOS (the 5 Oct 2026 refit's inputs)"},
    # R1: the same 54 columns, the 21 IOS profile inputs on the match's own surface (offence O + E_s, defence D + F_s,
    # their matchup products), each statistic at its tuned surface penalty (today's values where none beat them)
    "sprof": {"columns": BASE54,
              "sources": {f"{k}_{s}": f"{k}_{s}" for s in PROFILE for k in ("iosO", "iosD", "prod")},
              "desc": "R1, surface profile: the 21 IOS profile inputs replaced by their surface-specific versions"},
    # R2: the 54 inputs unchanged, plus the surface deviations (A - B) on the match's surface, serve and return side,
    # for the four statistics the suggestion prioritised (return points won enters through spw)
    "sdev": {"columns": BASE54 + [f"{k}_{s}" for s in PRIORITY for k in ("sdevO", "sdevD")],
             "sources": {f"{k}_{s}": f"{k}_{s}" for s in PRIORITY for k in ("sdevO", "sdevD")},
             "desc": "R2, surface deviations: the 54 inputs plus serve and return surface deviations of four statistics"},
    # P1 (the audit's proposal, 6 Oct 2026): the 54 inputs plus ONE column, the surface model's change in A's net
    # serve-and-return point advantage on this surface: (iosO_spw + iosD_spw) surface-effective minus today's
    "snet1": {"columns": BASE54 + ["dnet_spw"], "sources": {"dnet_spw": "dnet_spw"},
              "desc": "P1, net surface shift: the 54 inputs plus the surface model's change in A's net point advantage"},
    # its placebo: the same column permuted within tour x surface x season (same marginal, no link to the match)
    "snet1_perm": {"columns": BASE54 + ["dnet_spw"], "sources": {"dnet_spw": "dnetperm_spw"},
                   "desc": "placebo for P1: the column permuted within tour x surface x season"},
}
# Added after the locked test (the owner's question of 6 Oct 2026: without the odds, would it add?). The same design
# without the closing odds' column: today's 53 sporting inputs against the same 53 with the surface profile (R1, the
# representation chosen before the test). Pre-declared in strategy.md section 8 before any of these fits was scored.
NO_ODDS = [n for n in BASE54 if n != "odds_logit"]
ARMS["base_noodds"] = {"columns": NO_ODDS, "desc": "today's 53 sporting inputs, no odds"}
ARMS["sprof_noodds"] = {"columns": NO_ODDS, "sources": dict(ARMS["sprof"]["sources"]),
                        "desc": "R1 without the odds: the 53 inputs with the 21 IOS profile inputs per surface"}

# Added after the owner's decision (6 Oct 2026; the owner's question: separate models per court type, or does one model
# distinguish surfaces?). The decided model (R1 with the odds) as three surface-specific models, each trained only on its
# surface's matches (hard with the rare carpet, clay, grass) and predicting that surface's matches, against the one pooled
# model. Pre-declared in strategy.md section 9 before any of these fits ran. run_local.py fits the sub-models.
# The model's surface column codes: 0 hard, 1 clay, 2 grass, 3 carpet (carpet, rare, goes with hard).
SURFACE_GROUPS = {"hard": (0.0, 3.0), "clay": (1.0,), "grass": (2.0,)}
ARMS["sprof_bysurf"] = {"columns": BASE54, "sources": dict(ARMS["sprof"]["sources"]), "by_surface": True,
                        "desc": "R1 as three surface-specific models (hard + carpet, clay, grass)"}

CANDIDATES = ("sprof", "sdev", "snet1")        # the arms the primary is chosen from (choose_primary.py)
COMPARISONS: list[tuple[str, str]] = [("base", "sprof"), ("base", "sdev"), ("base", "snet1"), ("base", "snet1_perm"),
                                      ("base_noodds", "sprof_noodds"), ("sprof", "sprof_bysurf")]


def arm_path(arm: str) -> Path:
    return C.OUT / "arms" / f"{arm}.parquet"


def antisymmetric(names) -> list[str]:
    """Every input except the match context is an A - B difference (or the odds' log-odds): negated by the swap."""
    return [n for n in names if n not in CONTEXT]


def slots() -> dict[str, dict]:
    """Every (arm, seed, season) of the phases each arm runs in (all phases unless the arm lists its own)."""
    out = {}
    for arm, spec in ARMS.items():
        for phase in spec.get("phases", tuple(PHASES)):
            for year in PHASES[phase]:
                for seed in SEEDS:
                    out[f"{arm}_s{seed}_{year}"] = {"arm": arm, "seed": seed, "year": year, "phase": phase}
    return out


def registered_configs() -> dict[str, dict]:
    from src.eda.surface_ios import guard as G
    return {slot: G.slot_config(spec["seed"]) for slot, spec in slots().items()}


def description(slot: str) -> str:
    s = slots()[slot]
    return (f"tennis surface-IOS study: arm {s['arm']}, seed {s['seed']}, main tour 2013-{s['year'] - 1} -> "
            f"{s['year']}")


def plan_hash() -> str:
    spec = {"phases": PHASES, "seeds": SEEDS,
            "arms": {a: {"columns": v["columns"], "sources": v.get("sources", {}), "phases": v.get("phases")}
                     for a, v in ARMS.items()},
            "comparisons": COMPARISONS}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
