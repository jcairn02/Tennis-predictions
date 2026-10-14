"""The single check of the unpriced-leads study. The owner adopted it on 13 Oct 2026 in place of the two-look plan
(rules: docs/studies/unpriced_leads/check_now_rules.md, frozen with this file's SHA-256 in the process log).

One reading, on every frame match from the 2025 season on, decides whether the five groups' combined score enters the
predictions as a small adjustment on top of the current best model:
    score    the registered combined score (look.omnibus_score, mode "window", with the registered completeness gate),
             unchanged; z = the score over its RMS in the window, capped at +-3.5 (the limit: in 2013-24 it binds on
             0.8% of matches, mostly the post-Slam letdown's, and leaves the reading unchanged)
    base     the current best model's both-stages forecast (build_forecasts.py: the 16-seed mean, recalibrated per
             tour, plus the men's speed term, which is 0 where the speed column has no value), with look.fit's
             per-tour slope and curvature on its log-odds; four-week blocks, cluster-robust
    decide   the adjustment is used if beta / se >= 1.0 (the pass mark): about 72% of the time if 45% of the 2013-24
             effect survives, about 16% if none does (normal approximation; Look A's standard error scaled to 9,457
             matches)
    size     b = max(0, the posterior mean) under the prior N(m0, m0^2), m0 = 0.45 x the registered discovery beta per
             SD (look.fit on seasons <= 2024, beyond the close): the registered empirical-Bayes secondary's prior.
             b = 0 when the check does not pass. Stored per unit of z (beta per SD over z's RMS in the fit)
    live     logit q = s_tour eta + b_speed spd_L + b z, with z computed from the window's frozen parameters
             (params.json: each member's projection and scale by tour, each group's scale, the combined score's
             scale, the limit); score_from_params reproduces the window's score exactly (checked on every run)
Reported beside it, without changing the decision: the registered primary (beyond the close, uncapped) and its
realisation ratio; the stage-1 base; the close as base; the Pinnacle and BetOnline months; matches with a speed value
only; completed matches only; each group; whether the one-sided p clears the usual 5%.

Windows: --dry-run, seasons 2023-2024 (already read by the registered dry run: checks the code, no decision); the
check reads seasons 2025 on and needs --owner-go "<the owner's words>".
Run: ./python.sh src/eda/unpriced_leads/check_now.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import look as LK  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

WINDOWS = {"dry-run": (2023, 2024, "2025-01-01"), "now": (2025, 2100, "2100-01-01")}
CAP = 3.5
PASS_Z = 1.0
PRIOR_K = 0.45
OUT = H.OUT / "check_now"
FORECASTS = OUT / "forecasts.parquet"
REGISTRY = ROOT / "docs" / "studies" / "unpriced_leads" / "registry.json"


# --------------------------------------------------------------------------------------------------------- data

def add_model_bases(f: pd.DataFrame) -> pd.DataFrame:
    """The current best model's both-stages forecast (L_full) and stage 1 alone (L_s1), log-odds, from
    build_forecasts.py; spd_filled marks a speed term set to 0 for want of a speed value. No result column."""
    q = pd.read_parquet(FORECASTS, columns=["match_id", "q_full", "q_full_s1", "spd_filled"])
    q = q.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    for col, name in (("q_full", "L_full"), ("q_full_s1", "L_s1")):
        v = q[col].to_numpy(float)
        f[name] = np.where(np.isfinite(v), H.lg(np.clip(v, 1e-12, 1 - 1e-12)), np.nan)
    f["spd_filled"] = q["spd_filled"].fillna(False).astype(bool).to_numpy()
    return f


def registered_gates(groups: list[dict], frame: pd.DataFrame) -> tuple[dict, dict]:
    gates, report = {}, {}
    for g in groups:
        for m in g["members"]:
            vals = pd.read_parquet(ROOT / m["values"], columns=["match_id", m["column"]]).astype({"match_id": str})
            x_all = vals.drop_duplicates("match_id").set_index("match_id")[m["column"]]
            ok, failed = LK.gate_mask(m, frame, x_all)
            gates[m["column"]] = ok
            report[m["column"]] = failed
    return gates, report


# ------------------------------------------------------------------------------------------- frozen parameters

def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


def score_params(groups: list[dict], frame: pd.DataFrame, gates: dict, values: dict | None = None) -> dict:
    """The window's scoring parameters, fitted exactly as look.omnibus_score(mode="window") fits them: each member's
    projection on the 48 inputs and its RMS scale by tour (on its gated values present), each group's RMS, the
    combined score's RMS. Reads no outcome."""
    P = {"cap": CAP, "members": {}, "group_rms": {}, "groups": [g["id"] for g in groups]}
    scaled = []
    for g in groups:
        parts, active = [], []
        for m in g["members"]:
            x = _values(m, frame, values)
            gm = gates.get(m["column"])
            if gm is not None:
                x = np.where(gm, x, np.nan)
            xo, coef = H.orthogonal_part(frame, x)
            sc = {}
            for tour in ("atp", "wta"):
                mt = (frame["tour"] == tour).to_numpy()
                r = float(np.sqrt(np.nanmean(xo[mt] ** 2))) if np.isfinite(xo[mt]).any() else 0.0
                sc[tour] = r if r > 0 else 1.0
            P["members"][m["column"]] = {"group": g["id"], "values": m["values"], "sign": m["sign"],
                                         "gate": m.get("gate", "none"), "coef": coef, "scale": sc}
            parts.append(_member_z(frame, xo, sc, m["sign"]))
            active.append(np.ones(len(frame), bool) if gm is None else np.asarray(gm, bool))
        s = _group_mean(parts, active)
        r = _rms(s)
        P["group_rms"][g["id"]] = r if r > 0 else 1.0
        scaled.append(s / P["group_rms"][g["id"]])
    omni = np.mean(np.column_stack(scaled), axis=1)
    r = _rms(omni)
    P["omnibus_rms"] = r if r > 0 else 1.0
    return P


def score_from_params(groups: list[dict], frame: pd.DataFrame, P: dict, gates: dict | None = None,
                      values: dict | None = None, capped: bool = True) -> np.ndarray:
    """z for any frame (a window, or live rows) from frozen parameters: the members' frozen projections and scales,
    the groups' and the combined score's frozen RMS, the limit. gates: {column: bool array} (None: all pass)."""
    scaled = []
    for g in groups:
        parts, active = [], []
        for m in g["members"]:
            pm = P["members"][m["column"]]
            x = _values(m, frame, values)
            gm = None if gates is None else gates.get(m["column"])
            if gm is not None:
                x = np.where(gm, x, np.nan)
            xo, _ = H.orthogonal_part(frame, x, coef=pm["coef"])
            parts.append(_member_z(frame, xo, pm["scale"], pm["sign"]))
            active.append(np.ones(len(frame), bool) if gm is None else np.asarray(gm, bool))
        scaled.append(_group_mean(parts, active) / P["group_rms"][g["id"]])
    z = np.mean(np.column_stack(scaled), axis=1) / P["omnibus_rms"]
    return np.clip(z, -P["cap"], P["cap"]) if capped else z


def _values(m: dict, frame: pd.DataFrame, values: dict | None) -> np.ndarray:
    """The member's values aligned to the frame: from `values` ({column: Series by match id}, e.g. a live build) or
    from the registered, hash-checked values file."""
    if values is not None and m["column"] in values:
        s = values[m["column"]]
        s = s[~s.index.duplicated()]
        return s.reindex(frame["match_id"].astype(str)).to_numpy(float)
    return LK.member_values(m, frame)


def _member_z(frame: pd.DataFrame, xo: np.ndarray, scale: dict, sign: float) -> np.ndarray:
    sc = np.ones(len(frame))
    for tour in ("atp", "wta"):
        sc[(frame["tour"] == tour).to_numpy()] = scale[tour]
    z = sign * (xo / sc)
    return np.where(np.isfinite(z), z, 0.0)


def _group_mean(parts: list[np.ndarray], active: list[np.ndarray]) -> np.ndarray:
    Pm, A = np.column_stack(parts), np.column_stack(active).astype(float)
    n = A.sum(axis=1)
    return np.where(n > 0, (Pm * A).sum(axis=1) / np.maximum(n, 1), 0.0)


# --------------------------------------------------------------------------------------------------- decision

def posterior(beta: float, se: float, m0: float) -> dict:
    """The normal prior N(m0, m0^2) updated with the window's beta and se (per SD)."""
    w0, w1 = 1.0 / m0 ** 2, 1.0 / se ** 2
    mean = (m0 * w0 + beta * w1) / (w0 + w1)
    return {"prior_mean": m0, "prior_sd": m0, "mean": float(mean), "sd": float(np.sqrt(1.0 / (w0 + w1))),
            "data_weight": float(w1 / (w0 + w1))}


def run(window: str, owner_go: str | None) -> tuple[dict, dict]:
    if window == "now" and not owner_go:
        raise RuntimeError("the check reads results from 2025 on: it needs --owner-go with the owner's words")
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    paths = LK.instance_paths(reg)
    first, last, end = WINDOWS[window]
    frame = LK.load_window(paths, first, last, end, allow_post_2024=(window == "now"))
    frame = LK.add_bases(frame, paths)
    frame = add_model_bases(frame)
    if window == "dry-run":                      # the rebuilt forecast equals the one the registered looks read
        both = np.isfinite(frame["L_model"]) & np.isfinite(frame["L_full"])
        d = float(np.max(np.abs(frame.loc[both, "L_model"] - frame.loc[both, "L_full"])))
        if d > 1e-9:
            raise RuntimeError(f"the rebuilt forecast differs from the registered one (max {d:.2e})")
    LK._load_frame_months(paths)
    groups = reg["groups"]
    gates, gate_report = registered_gates(groups, frame)
    # the registered score and the frozen parameters that reproduce it
    s = LK.omnibus_score(groups, frame, "window", gates)
    P = score_params(groups, frame, gates)
    z_unc = score_from_params(groups, frame, P, gates, capped=False)
    repro = float(np.max(np.abs(z_unc - s / P["omnibus_rms"])))
    if repro > 1e-9:
        raise RuntimeError(f"the frozen parameters do not reproduce the registered score (max {repro:.2e})")
    z = np.clip(z_unc, -CAP, CAP)
    # the prior: the registered discovery beta per SD (seasons <= 2024, beyond the close)
    disc = H.load_frame()
    bd = LK.fit(disc, LK.omnibus_score(groups, disc, "window"))["beta"]
    m0 = PRIOR_K * bd
    # the decision reading
    dec = LK.fit(frame, z, base="L_full")
    ok = np.isfinite(frame["L_full"].to_numpy())
    z_rms_fit = _rms(z[ok])
    passes = bool(np.isfinite(dec["z"]) and dec["z"] >= PASS_Z)
    post = posterior(dec["beta"], dec["se"], m0)
    b_per_sd = max(0.0, post["mean"]) if passes else 0.0
    b_per_z = b_per_sd / z_rms_fit
    # beside it
    def sub(mask: np.ndarray, base: str = "L_full", score: np.ndarray | None = None) -> dict:
        sc = z if score is None else score
        mask = np.asarray(mask, bool)
        return LK.fit(frame[mask].reset_index(drop=True), sc[mask], base=base)
    src = frame["odds_input"].astype(str).str.lower()
    prim = LK.fit(frame, s)
    beside = {
        "registered_primary_beyond_the_close_uncapped": dict(prim, realisation_per_sd=prim["beta"] / bd),
        "beyond_the_close_capped": LK.fit(frame, z, base="L"),
        "beyond_stage_1_alone": LK.fit(frame, z, base="L_s1"),
        "uncapped_beyond_the_model": LK.fit(frame, z_unc, base="L_full"),
        "pinnacle_months": sub(src.str.contains("pinnacle").to_numpy()),
        "betonline_months": sub(src.str.contains("betonline").to_numpy()),
        "matches_with_a_speed_value": sub(~frame["spd_filled"].to_numpy()),
        "completed_matches_only": sub(~frame["retired"].to_numpy()),
        "groups": {g["id"]: dict(LK.fit(frame, LK.group_score(g, frame, "window", gates), base="L_full"),
                                 name=g["name"]) for g in groups},
        "share_of_matches_at_the_limit": float(np.mean(np.abs(z_unc) > CAP)),
    }
    decision = {
        "window": window, "seasons": [first, last], "end": end, "owner_go": owner_go,
        "run_at": time.strftime("%Y-%m-%d %H:%M:%S"), "matches": int(len(frame)),
        "matches_with_the_base": int(ok.sum()), "last_date": str(frame["tournament_date"].max().date()),
        "by_tour": frame["tour"].value_counts().to_dict(),
        "reading": dec, "pass_mark_beta_over_se": PASS_Z, "passes": passes,
        "usual_5pct_one_sided": bool(dec["p_one_sided"] <= 0.05),
        "discovery_beta_per_sd": bd, "prior_k": PRIOR_K, "posterior": post,
        "size_per_sd": b_per_sd, "size_per_unit_z": b_per_z, "z_rms_in_fit": z_rms_fit, "cap": CAP,
        "largest_adjustment_log_odds": b_per_z * CAP,
        "beside": beside, "gate_failures": gate_report,
        "registry_sha256": LK.sha256(REGISTRY), "forecasts_sha256": LK.sha256(FORECASTS),
        "code_sha256": LK.sha256(Path(__file__)), "reproduction_max_abs": repro,
        "verdict": ("dry run: no decision" if window == "dry-run" else
                    ("passes: use the adjustment at the size above" if passes else
                     "does not pass: the adjustment stays off")),
    }
    params = dict(P, window=window, seasons=[first, last], last_date=decision["last_date"],
                  size_per_unit_z=b_per_z, passes=passes, registry_sha256=decision["registry_sha256"],
                  code_sha256=decision["code_sha256"], made_at=decision["run_at"])
    return decision, params


def plain(d: dict) -> str:
    r = d["reading"]
    lines = [f"Check window: {d['window']} ({d['matches']:,} matches, {d['matches_with_the_base']:,} with the model's "
             f"forecast; last {d['last_date']}).",
             f"On top of the full current model, the combined patterns lean {'the right way' if r['beta'] > 0 else 'the wrong way'}: "
             f"{r['z']:+.2f} standard errors (pass mark +{d['pass_mark_beta_over_se']:.1f}).",
             f"Verdict: {d['verdict']}."]
    if d["window"] != "dry-run" and d["passes"]:
        lines.append(f"Size: {d['size_per_sd']:.4f} log-odds per SD of the score; the largest adjustment allowed is "
                     f"{d['largest_adjustment_log_odds']:.3f} log-odds.")
    p = d["beside"]["registered_primary_beyond_the_close_uncapped"]
    lines.append(f"Against the closing odds alone (the original question): {p['z']:+.2f} standard errors; "
                 f"{p['realisation_per_sd']:.0%} of the 2013-24 strength per SD.")
    lines.append(f"The usual scientific standard (one-sided 5%): {'met' if d['usual_5pct_one_sided'] else 'not met'}.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--owner-go")
    a = ap.parse_args()
    window = "dry-run" if a.dry_run else "now"
    decision, params = run(window, a.owner_go)
    d = OUT / window
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(decision, indent=1, default=float), encoding="utf-8")
    (d / "params.json").write_text(json.dumps(params, indent=1, default=float), encoding="utf-8")
    text = plain(decision)
    (d / "summary.txt").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
