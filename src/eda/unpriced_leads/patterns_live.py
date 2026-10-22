"""The combined-pattern adjustment in the daily engine (rules: docs/studies/unpriced_leads/check_now_rules.md).

It is off until the single check passes and the owner accepts it. While adjustment.json's status is "off", the engine
runs no extra step and its outputs are unchanged: no column, no provenance entry. When it is on:
    the patterns step (dp_steps.step_patterns, after the states step) runs live_members.py inside the work tree for the
    live matches (the registered members' values on the tree's own tables; G3's surface IOS is the instance's table
    with the states step's ace ratings of today's tables laid over it, since 16 Oct 2026), then build_for_run here
    computes the live gate and z with the check's frozen parameters (check_now.score_from_params) and writes
    <run>/live_patterns.parquet (match_id, z, each member's value and gate), and live_patterns.json (with the venue
    pace's coverage: venue history rows without a rating, which add nothing);
    the predict step adds b z to each match's stage-2 log-odds, at its own price and at every grid price:
        logit q = s_tour eta + b_speed spd_L + b z
    z is the same at every price, because the score reads none of the price inputs. It records z, the shift and q
    before the term (predictions.csv) and the configuration (provenance.json, stage2.patterns).
A match without a z (no row in live_patterns.parquet) gets no shift, as a member with missing data adds nothing.
A member not built for live matches (live_members.NOT_BUILT: G1's luck members, G4's lower-level pair) has no live
value. Where its gate is on, the rules' "a pattern whose data is missing for a match adds nothing" applies: it counts 0
and stays in its group's mean, and live_patterns.json lists it. Since the lower-level feed (14 Oct 2026) G4's pair is
on in every run; extend live_members.py and re-run the parity proof to give it its values.

The live gate (the rules' trailing form of the registered gate): a member with a gate is switched off for a live match
of tour t and month M when its count over the three complete months M-3..M-1 is below 70% of the same months a year
earlier (a year-earlier count of 0 passes). Counts as the registered gate takes them: Stage 0's lower-level matches or
matches with a box score (the run's tree), TennisLive's played doubles (the tree's dump), or the member's presence
among the template frame's matches (the registered values files).
Set UL_PATTERNS_CONFIG to another adjustment.json for tests.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG = Path(os.environ.get("UL_PATTERNS_CONFIG",
                             str(ROOT / "data" / "studies" / "unpriced_leads" / "check_now" / "adjustment.json")))
LIVE_FILE = "live_patterns.parquet"
MEMBERS_FILE = "live_members.parquet"
GATE_RATIO = 0.7


def config() -> dict:
    if not CONFIG.exists():
        return {"status": "off", "why": "no adjustment.json"}
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def is_on(cfg: dict | None = None) -> bool:
    cfg = config() if cfg is None else cfg
    return cfg.get("status") == "on" and float(cfg.get("size_per_unit_z") or 0.0) != 0.0


def _params(cfg: dict) -> dict:
    path = ROOT / cfg["params"]
    if hashlib.sha256(path.read_bytes()).hexdigest() != cfg["params_sha256"]:
        raise RuntimeError(f"{path} does not match adjustment.json's SHA-256")
    return json.loads(path.read_text(encoding="utf-8"))


def for_run(run_dir: Path, ids) -> dict | None:
    """None while the adjustment is off. Otherwise each match's z (0 where it has none), the shift b z in log-odds,
    and the record for provenance.json."""
    cfg = config()
    if not is_on(cfg):
        return None
    _params(cfg)
    f = Path(run_dir) / LIVE_FILE
    if not f.exists():
        raise RuntimeError(f"the pattern adjustment is on but {f} is missing: run the patterns step")
    t = pd.read_parquet(f).astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id")
    z_raw = t["z"].reindex(pd.Index(ids).astype(str)).to_numpy(float)
    z = np.where(np.isfinite(z_raw), z_raw, 0.0)
    b = float(cfg["size_per_unit_z"])
    rec = {"status": "on", "size_per_unit_z": b, "params": cfg["params"], "params_sha256": cfg["params_sha256"],
           "live_file_sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "set_at": cfg.get("set_at"),
           "matches_with_z": int(np.isfinite(z_raw).sum()), "rules": "docs/studies/unpriced_leads/check_now_rules.md"}
    return {"z": z, "z_raw": z_raw, "applied": np.isfinite(z_raw), "shift": b * z, "record": rec}


def shift(q: np.ndarray, off: np.ndarray) -> np.ndarray:
    q = np.clip(np.asarray(q, float), 1e-15, 1 - 1e-15)
    return expit(np.log(q / (1 - q)) + off)


# ------------------------------------------------------------------------------------------------- the live gate

def _months_before(month: str, n: int = 3) -> list[str]:
    p = pd.Period(month, "M")
    return [str(p - k) for k in range(n, 0, -1)]


def _ratio_ok(counts: pd.Series, tour: str, month: str) -> tuple[bool, float]:
    now = _months_before(month)
    before = [str(pd.Period(m, "M") - 12) for m in now]
    c1 = float(sum(counts.get((tour, m), 0) for m in now))
    c0 = float(sum(counts.get((tour, m), 0) for m in before))
    if not c0 > 0:
        return True, float("nan")
    return bool(c1 / c0 >= GATE_RATIO), c1 / c0


def gate_counts(kind: str, tree: Path) -> pd.Series:
    """Outcome-free counts by (tour, month), as look._monthly_counts takes them, from the tree's tables."""
    if kind in ("lower_level", "box_all"):
        m = pd.read_parquet(tree / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet",
                            columns=["tour", "level", "qualifying", "tournament_date", "has_box"])
        m["month"] = pd.to_datetime(m["tournament_date"]).dt.to_period("M").astype(str)
        m = m[m["qualifying"].astype(bool) | m["level"].isin(["CH", "ITF"])] if kind == "lower_level" \
            else m[m["has_box"].astype(bool)]
        return m.groupby(["tour", "month"]).size()
    if kind == "doubles":
        tl = pd.read_parquet(tree / "data" / "dump" / "points" / "tennislive" / "listed.parquet",
                             columns=["tour", "discipline", "mixed", "junior", "played", "start_utc"])
        tl = tl[(tl["discipline"] == "doubles") & (tl["mixed"] != "TRUE") & (tl["junior"] != "TRUE") &
                (tl["played"] == "TRUE")].copy()
        tl["month"] = pd.to_datetime(tl["start_utc"], errors="coerce").dt.to_period("M").astype(str)
        return tl.groupby([tl["tour"].astype(str).str.lower(), "month"]).size()
    raise ValueError(kind)


def presence_counts(member: dict) -> pd.DataFrame:
    """The member's presence among the template frame's matches by (tour, month): matches with a finite registered
    value (`present`) and matches (`n`), so the gate compares pooled shares over the three months, as
    look.gate_mask's presence rule does (a window with no frame match passes)."""
    from src.eda.unpriced_leads import look as LK
    from src.eda.unpriced_leads import screen as H
    f = pd.read_parquet(H.FRAME, columns=["match_id", "tour", "tournament_date", "debut_season"])
    f = f[~f["debut_season"].astype(bool)].copy()
    f["match_id"] = f["match_id"].astype(str)
    f["month"] = f["tournament_date"].dt.to_period("M").astype(str)
    v = pd.read_parquet(ROOT / member["values"], columns=["match_id", member["column"]]).astype({"match_id": str})
    v = v.drop_duplicates("match_id").set_index("match_id")[member["column"]]
    f["present"] = np.isfinite(v.reindex(f["match_id"]).to_numpy(float)).astype(float)
    LK.check_hash(ROOT / member["values"], member.get("values_sha256"), member["column"])
    return f.groupby(["tour", "month"])["present"].agg(present="sum", n="size")


def _presence_ok(t: pd.DataFrame, tour: str, month: str) -> tuple[bool, float]:
    now = _months_before(month)
    before = [str(pd.Period(m, "M") - 12) for m in now]

    def share(months):
        rows = [t.loc[(tour, m)] for m in months if (tour, m) in t.index]
        n = sum(r["n"] for r in rows)
        return (sum(r["present"] for r in rows) / n) if n else float("nan")
    s1, s0 = share(now), share(before)
    if not (np.isfinite(s1) and np.isfinite(s0) and s0 > 0):
        return True, float("nan")
    return bool(s1 / s0 >= GATE_RATIO), s1 / s0


def live_gates(groups: list[dict], tours: np.ndarray, months: np.ndarray, tree: Path) -> tuple[dict, dict]:
    """{column: bool array (True = on)} for live matches, and the ratios behind each switched-off member."""
    cache: dict = {}
    gates, report = {}, {}
    for g in groups:
        for m in g["members"]:
            kind = m.get("gate", "none")
            if kind == "none":
                continue
            key = kind if kind != "presence" else ("presence", m["column"])
            if key not in cache:
                cache[key] = presence_counts(m) if kind == "presence" else gate_counts(kind, tree)
            ok = np.ones(len(tours), bool)
            for i, (t, mo) in enumerate(zip(tours, months)):
                passed, r = (_presence_ok if kind == "presence" else _ratio_ok)(cache[key], t, mo)
                ok[i] = passed
                if not passed:
                    report.setdefault(m["column"], {})[f"{t} {mo}"] = round(r, 3)
            gates[m["column"]] = ok
    return gates, report


# ---------------------------------------------------------------------------------------------- z for a run

def build_for_run(run_dir: Path, tree: Path) -> dict:
    """z for the run's live matches from live_members.parquet (written inside the tree), the live inputs and meta, the
    live gate and the check's frozen parameters: writes <run>/live_patterns.parquet."""
    from src.eda.unpriced_leads import check_now as CN
    from src.eda.unpriced_leads import screen as H
    cfg = config()
    P = _params(cfg)
    reg = json.loads(CN.REGISTRY.read_text(encoding="utf-8"))
    groups = reg["groups"]
    run_dir = Path(run_dir)
    vals = pd.read_parquet(run_dir / MEMBERS_FILE).astype({"match_id": str}).drop_duplicates("match_id")
    lf = pd.read_parquet(run_dir / "live_frame.parquet").astype({"match_id": str}).drop_duplicates("match_id")
    meta = pd.read_parquet(run_dir / "live_meta.parquet").astype({"match_id": str}).drop_duplicates("match_id")
    frame = lf.merge(meta[["match_id", "day"]], on="match_id", how="left", validate="one_to_one")
    if "tour" not in frame.columns:
        frame = frame.merge(meta[["match_id", "tour"]], on="match_id", how="left", validate="one_to_one")
    for k, (a, b) in H.PAIRS.items():
        frame[f"in_{k}"] = frame[f"in_{a}"] - frame[f"in_{b}"]
    frame["month"] = pd.to_datetime(frame["day"]).dt.to_period("M").astype(str)
    gates, gate_report = live_gates(groups, frame["tour"].to_numpy(), frame["month"].to_numpy(), Path(tree))
    values = {c: vals.set_index("match_id")[c] for c in vals.columns if c != "match_id"}
    z = CN.score_from_params(groups, frame, P, gates, values=values)
    # a member not built for live matches (live_members.NOT_BUILT) whose gate is on has no value here: the rules' "a
    # pattern whose data is missing for a match adds nothing" applies (it counts 0 and stays in its group's mean). Since
    # 14 Oct 2026 the lower-level feed restores the lower levels in every run's tables, so G4's lower-level pair is on.
    # (Until 14 Oct such matches were paused instead, which the feed would have turned into a pause of every match.)
    from src.eda.unpriced_leads import live_members as LM
    missing_on = {c: int(np.asarray(gates.get(c, np.ones(len(frame), bool))).sum()) for c in LM.NOT_BUILT}
    missing_on = {c: n for c, n in missing_on.items() if n}
    out = pd.DataFrame({"match_id": frame["match_id"].to_numpy(), "z": z})
    for c, s in values.items():
        out[c] = s.reindex(frame["match_id"]).to_numpy(float)
        if c in gates:
            out[f"gate_{c}"] = gates[c]
    out.to_parquet(run_dir / LIVE_FILE, index=False)
    rec = {"matches": int(len(out)), "z_present": int(np.isfinite(z).sum()),
           "not_built_but_on_counted_as_missing": missing_on, "gate_off": gate_report,
           "params_sha256": cfg["params_sha256"]}
    lm = (run_dir / MEMBERS_FILE).with_suffix(".json")          # live_members.py's record of what G3 read
    if lm.exists():
        j = json.loads(lm.read_text(encoding="utf-8"))
        rec["venue_pace"] = {"venue_rows": j.get("venue_rows"),
                             "venue_rows_without_rating": j.get("venue_rows_without_rating"),
                             "ratings_from_run": (j.get("ios") or {}).get("run_matches"),
                             "ace_gap_equal_to_input": (j.get("frame_check") or {}).get("equal")}
    (run_dir / "live_patterns.json").write_text(json.dumps(rec, indent=1, default=float), encoding="utf-8")
    return rec
