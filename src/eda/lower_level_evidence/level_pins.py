"""The builders' tuned constants pinned to the reference build's (role C1), for the NEW arms of pre-registration addition 1
as addition 3 (section 4) builds them: "every tuned constant pinned to the reference's: Stage 1's Elo K, the offset
Elo's kd, Stage 3, Stage B, and IOS_CONSTANTS_VERSION=2026-10-08_reference. The data is then the only difference."

Stage B's pin is the layer's own (level_layer.pin, the config's "pins"); the IOS constants are pinned by the environment.
This module pins the other three, on the line where each builder has just chosen its constants:
    stage1_k(tour, rule, k), stage1_w(tour, rule, w)   predictability_diagnostic/stage1_baselines.tune
    offset_kd(kind, tour, kd)                            surface_elo_pieces/pieces.main ("offset", "offset_surface_blind")
    stage3(chosen)                                       predictability_diagnostic/stage3_ratings.main
Pieces reads Stage 1's K from Stage 1's summary and Stage 4 its games Elo constants likewise, so both follow Stage 1's pin.

Each function returns its input unchanged unless the layer config (LLE_LAYER) names
"pin_constants": {"path": <system/arms/constants/reference_constants.json>, "sha256": ...}; then it returns the
reference's value and records whether the build's own tuning chose the same (layer_calls.jsonl). The tuning still runs,
so its grid is kept. The file is copied into a NEW-arm sandbox with its patch (system_new_arms.py): never into the
repository's builders, never into a SYS-family sandbox (addition 3 froze those builders' patches).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from src.eda.lower_level_evidence import level_layer as L

_REF: dict = {}


def _ref() -> tuple[dict, dict] | None:
    """(the layer config, the reference constants) when the config pins the constants; None otherwise."""
    cfg = L.config()
    if cfg is None or not cfg.get("pin_constants"):
        return None
    pin = cfg["pin_constants"]
    p = Path(pin["path"])
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != pin["sha256"]:
        raise RuntimeError(f"pin_constants: {p} has sha256 {got}, the config expects {pin['sha256']}")
    if got not in _REF:
        _REF.clear()
        _REF[got] = json.loads(p.read_text(encoding="utf-8"))
    return cfg, _REF[got]


def _note(cfg: dict, what: str, tour: str, tuned, used) -> None:
    same = tuned == used
    L.record(cfg, {"hook": "pin_constants", "what": what, "tour": tour, "tuned": tuned, "reference": used,
                   "tuned_equals_reference": same})
    L.log(f"pin {what} {tour}: the reference's {used} (this build's tuning chose {tuned}; equal: {same})")


def stage1_k(tour: str, rule: str, k: dict) -> dict:
    """Stage 1's K constants (k0, offset, shape) for a tour and retirement rule."""
    got = _ref()
    if got is None:
        return k
    cfg, ref = got
    rows = [c for c in ref["stage1_chosen"] if c["tour"] == tour and c["rule"] == rule]
    if len(rows) != 1:
        raise KeyError(f"pin_constants: {len(rows)} reference rows for Stage 1 {tour} {rule}")
    used = {c: float(rows[0][c]) for c in ("k0", "offset", "shape")}
    if set(k) != set(used):
        raise KeyError(f"pin_constants: Stage 1's K has keys {sorted(k)}, the reference {sorted(used)}")
    _note(cfg, f"stage1_k {rule}", tour, {c: float(v) for c, v in k.items()}, used)
    return used


def stage1_w(tour: str, rule: str, w: float) -> float:
    """Stage 1's surface weight for a tour and retirement rule."""
    got = _ref()
    if got is None:
        return w
    cfg, ref = got
    rows = [c for c in ref["stage1_chosen"] if c["tour"] == tour and c["rule"] == rule]
    if len(rows) != 1:
        raise KeyError(f"pin_constants: {len(rows)} reference rows for Stage 1 {tour} {rule}")
    used = float(rows[0]["w"])
    _note(cfg, f"stage1_w {rule}", tour, float(w), used)
    return used


def offset_kd(kind: str, tour: str, kd: dict) -> dict:
    """The offset Elo's kd0, kd_off, kd_shape: kind "offset" or "offset_surface_blind" (the audit's control)."""
    got = _ref()
    if got is None:
        return kd
    cfg, ref = got
    key = {"offset": "offset_constants", "offset_surface_blind": "offset_surface_blind_constants"}[kind]
    used = {c: float(v) for c, v in ref[key][tour].items()}
    if set(kd) != set(used):
        raise KeyError(f"pin_constants: the {kind} constants have keys {sorted(kd)}, the reference {sorted(used)}")
    _note(cfg, kind, tour, {c: float(v) for c, v in kd.items()}, used)
    return used


def stage3(chosen: dict) -> dict:
    """Stage 3's constants per tour (the grid's settings and start_return)."""
    got = _ref()
    if got is None:
        return chosen
    cfg, ref = got
    out = {}
    for tour, mine in chosen.items():
        v = ref["stage3_chosen"][tour]
        used = {c: float(x) for c, x in (json.loads(v.replace("'", '"')) if isinstance(v, str) else v).items()}
        if set(mine) != set(used):
            raise KeyError(f"pin_constants: Stage 3's constants have keys {sorted(mine)}, the reference {sorted(used)}")
        _note(cfg, "stage3", tour, {c: float(x) for c, x in mine.items()}, used)
        out[tour] = used
    return out
