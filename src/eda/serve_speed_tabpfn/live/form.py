"""The live 28-day speed form (docs/decisions/2026-10-07-speed-nudge.md as amended on 8 Oct 2026: always the 28-day
memory). Reads no match result.

For a day D (each morning: today) and each ATP player, from his live-panel rows released by D (release <= D) within
364 days (obs >= D - 364), centred by the as-of edition offsets of D fitted on the same released rows
(panel.EditionOffsets through features_latency.Scenario), the study's two-state filter with a 28-day half-life and
every other men's constant unchanged (features_latency.MEN, hl = 28) gives, projected to D:
    f_hat (km/h), f_sd, L_hat, hist (rows), k14, k28, last_age (days since his latest reading), last_reading (date)
spd_L for a pair (A, B) on day D = clip((f_hat_A - f_hat_B) / 1.9496051535048338, -4, 4), the standardiser of the
latency run's B-M1 (latency/variants_meta.json), exactly as adaptive/columns.py; a player without rows has f_hat 0.
This is the column the adjustment uses (adaptive/adjust.py, mode L). Women: 0 (no WTA tour-level speeds).

Reuses features.py (prepare_panel), features_latency.py (Scenario, side_values_v, MEN) and panel.py (EditionOffsets) by
import; nothing of theirs is edited.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.serve_speed_tabpfn.live import common as LC

HL_L = 28.0
CLIP = 4.0
SD_L = float(json.loads((LC.STUDY / "latency" / "variants_meta.json").read_text(encoding="utf-8"))
             ["standardisation_sd_km_h"]["B_M1"])
FAR = 10 ** 6
FORM_COLS = ["player_id", "day", "f_hat", "f_sd", "L_hat", "hist", "k14", "k28", "last_age", "last_reading"]


def form_as_of(day: int, panel: pd.DataFrame, release: np.ndarray | None = None,
               players=None) -> pd.DataFrame:
    """Each ATP player's 28-day form on `day` from the panel's rows released by then (release: per panel row, aligned
    with `panel`; default the panel's `release` column)."""
    from src.eda.serve_speed_tabpfn import features as F
    from src.eda.serve_speed_tabpfn.latency import features_latency as FL
    q = panel.copy()
    q["_rel"] = q["release"].to_numpy() if release is None else np.asarray(release)
    q = q[q["use"].astype(bool)]
    q = q[np.isfinite(pd.to_numeric(q["_rel"], errors="coerce"))]
    for c in ("es", "lf", "obs", "tdate", "round_order", "n"):
        q[c] = pd.to_numeric(q[c], errors="coerce")
    q = q[q[["es", "lf", "obs", "tdate", "round_order"]].notna().all(axis=1)]
    p = F.prepare_panel(q)
    S = FL.Scenario("live", p, p["_rel"].to_numpy(np.int64), None)
    ids = sorted(set(p.loc[p["tour"].eq("atp"), "player_id"])) if players is None else list(players)
    t = pd.DataFrame({"player_id": ids, "tour": "atp", "es": float(day), "tdate": float(day + FAR),
                      "round_order": 0.0, "tournament_id": "__live__", "season": pd.Timestamp(LC.date_of(day)).year})
    sv = FL.side_values_v(S, t, dict(FL.MEN, hl=HL_L))
    out = pd.DataFrame({"player_id": t["player_id"], "day": int(day), "f_hat": sv["f_hat"].astype(float),
                        "f_sd": sv["f_sd"].astype(float), "L_hat": sv["L_hat"].astype(float),
                        "hist": sv["hist"].astype(int), "k14": sv["k14"].astype(int), "k28": sv["k28"].astype(int),
                        "last_age": sv["last_age"].astype(float)})
    out["last_reading"] = [LC.date_of(day - a) if np.isfinite(a) else None for a in out["last_age"]]
    return out[FORM_COLS]


def spd_L_from_form(form: pd.DataFrame, a, b) -> np.ndarray:
    """spd_L for pairs (a[i], b[i]) from one day's form table (a player missing from it has f_hat 0)."""
    f = form.set_index("player_id")["f_hat"]
    fa = np.array([f.get(x, 0.0) for x in np.atleast_1d(a)], dtype=float)
    fb = np.array([f.get(x, 0.0) for x in np.atleast_1d(b)], dtype=float)
    return np.clip((fa - fb) / SD_L, -CLIP, CLIP)


def spd_L(player_a, player_b, day: int, panel: pd.DataFrame | None = None, form: pd.DataFrame | None = None,
          release: np.ndarray | None = None) -> float:
    """spd_L of one pair on `day`: from a day's form table if given, else computed from the panel (default: the live
    panel on disk)."""
    if form is None:
        if panel is None:
            from src.eda.serve_speed_tabpfn.live import live_panel as LP
            panel = LP.load()
        form = form_as_of(day, panel, release=release, players=[player_a, player_b])
    return float(spd_L_from_form(form, [player_a], [player_b])[0])


def write(day: int, panel: pd.DataFrame, out: Path = LC.OUT) -> Path:
    f = form_as_of(day, panel)
    path = LC.form_path(day, out)
    out.mkdir(parents=True, exist_ok=True)
    f.to_parquet(path, index=False)
    return path
