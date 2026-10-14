"""The registered looks of the unpriced-leads study (docs/studies/unpriced_leads/preregistration.md): each lead group's
score, and the five groups' omnibus score, beyond the close, read once per window. Revised before the freeze on the red
team's findings (team/red_team.md, B1-B3, M1-M5, m1-m8).

The registry (frozen and hashed with the preregistration) fixes the groups, each member's values file and column, its
sign and its completeness gate; the instance's frame, book prices, input list and forecast table, with their SHA-256;
and, for the secondaries, each member's projection and scales fitted on seasons <= 2024. Every file read is checked
against the registry's hash before use.

    gate     outcome-free, before anything is fitted: for each member, tour and calendar month of the window, its input
             count over the month and its two neighbours (Stage 0's lower-level matches, Stage 0's box scores,
             TennisLive's doubles rows, or the member's own presence among the frame's matches) against the same three
             months a year earlier; below 70% the member is set to missing for that tour and month. A month whose
             year-earlier count is 0 passes. (Calibrated outcome-free on 2023-26 counts: normal variation stays above
             0.76; the women's ITF qualifying lost from 2025 and the lower levels lost from June 2026 fall below.)
    score    each member's value is re-projected on the window's own rows (least squares on the model's 48 non-price
             inputs, by tour, no intercept, rows where the value is present: reads no outcome), scaled to unit RMS in the
             window by tour, signed; a missing value counts 0. A group's score is the mean of its members' scores; the
             omnibus score is the mean of the five groups' scores, each scaled to unit RMS in the window.
    base     logit P(A wins) = s_atp L 1[men] + s_wta L 1[women] + k_atp L|L| 1[men] + k_wta L|L| 1[women] + beta s,
             L = logit of the frame's odds input (Pinnacle first, then BetOnline; margin-free), fitted in the window.
    test     beta one-sided (+ = the registered directions), cluster-robust over four-week blocks, p from t on G - 1.
    looks    Look A: H0 (the omnibus) is confirmed at p <= 0.02; only then are H1-H5 (the groups) tested, Holm at 0.02.
             Final, read with Look B: if H0 was not confirmed at Look A, the combined z of the two looks,
             z_AB = (sqrt(I_A) z_A + sqrt(I_B) z_B) / sqrt(I_A + I_B), z = Phi^-1(1 - p), I = the window's sum of
             p(1 - p) of the close, confirms H0 at one-sided 0.03; only then are H1-H5 tested on their combined z's,
             Holm at 0.03. (Bonferroni across the two looks: an overall error rate of 0.05 for H0-H5 together.)
             Look B alone is reported without verdict words.
    secondaries (registered, no verdict words): the frozen-projection score (the ≤ 2024 projections and scales); beyond
             the close and the 48 inputs (per tour, fitted in the window); the raw score; the base without curvature;
             beyond the instance's both-stages forecast; each tour; the Pinnacle and BetOnline periods; BetOnline's own
             close, all and fresh / stale; Pinnacle's own close; completed matches only (retirements out); Look A before
             the 2026 lower-level data gap (women before 18 May 2026, men before 29 Jun 2026); BetOnline's open-to-close
             move (outcome-free); an empirical-Bayes P(beta > 0) with a prior N(k b, (k b)^2), k = 0.45, b the
             discovery beta per SD; each member alone; the realisation ratio (beta per SD in the window over beta per SD
             in discovery)

Windows (by season): --dry-run seasons 2023-2024 (already read: validates the code, no verdict); --look A seasons
2025-2026 before 29 Jul 2026; --look B from 29 Jul 2026 to the registry's `look_b_end`. A look reads outcomes from 2025 on
only with --look and --owner-go "<the owner's words>". --look-a-result gives Look B the Look A result file for the final.

Run: ./python.sh src/eda/unpriced_leads/look.py --registry docs/studies/unpriced_leads/registry.json --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import norm
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402

WINDOWS = {"dry-run": (2023, 2024, "2025-01-01"), "A": (2025, 2026, "2026-07-29")}
OUT = H.OUT / "looks"
FRESH_MIN = 60.0
GATE_RATIO = 0.7
ALPHA_A, ALPHA_FINAL = 0.02, 0.03
EB_K = 0.45
GAP_START = {"wta": pd.Timestamp("2026-05-18"), "atp": pd.Timestamp("2026-06-29")}
TL_LISTED = ROOT / "data" / "dump" / "points" / "tennislive" / "listed.parquet"


def sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_hash(path: Path, expected: str | None, what: str) -> None:
    if expected and sha256(path) != expected:
        raise RuntimeError(f"{what}: {path} does not match the registry's SHA-256")


# --------------------------------------------------------------------------------------------------------- data

def instance_paths(reg: dict) -> dict:
    p = {k: ROOT / reg[k] for k in ("frame", "book_prices", "model_inputs", "forecasts")}
    for k in ("frame", "book_prices", "model_inputs"):
        check_hash(p[k], reg.get(f"{k}_sha256"), k)
    return p


def load_window(paths: dict, first: int, last: int, end: str, allow_post_2024: bool,
                start_date: str | None = None) -> pd.DataFrame:
    """The frame's rows of seasons first..last with tournament date before `end` (and from `start_date`, for Look B),
    with the result, L, blocks and inputs. Seasons from 2025 on only when allow_post_2024."""
    if last > 2024 and not allow_post_2024:
        raise RuntimeError("this window reads outcomes from 2025 on: it needs --look and --owner-go")
    names = [d["name"] for d in json.loads(paths["model_inputs"].read_text(encoding="utf-8"))["inputs"]]
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt", "odds_input", "a_won"] + \
        [f"in_{n}" for n in names]
    flt = [("season", ">=", first), ("season", "<=", last), ("tournament_date", "<", pd.Timestamp(end))]
    if start_date:
        flt.append(("tournament_date", ">=", pd.Timestamp(start_date)))
    f = pd.read_parquet(paths["frame"], columns=cols, filters=flt)
    if len(f) and (f["season"].min() < first or f["season"].max() > last or
                   f["tournament_date"].max() >= pd.Timestamp(end)):
        raise RuntimeError("the window filter failed")
    f["match_id"] = f["match_id"].astype(str)
    f = f[~f["debut_season"].astype(bool)].copy()
    for k, (a, b) in H.PAIRS.items():
        f[f"in_{k}"] = f[f"in_{a}"] - f[f"in_{b}"]
    f["y"] = f["a_won"].astype(float)
    f = f.drop(columns=["a_won"])
    f["L"] = H.lg(f["p_mkt"])
    f["block"] = H.blocks(f["tournament_date"].to_numpy(), 28)
    f["month"] = f["tournament_date"].dt.to_period("M").astype(str)
    return f.reset_index(drop=True)


def add_bases(f: pd.DataFrame, paths: dict) -> pd.DataFrame:
    """BetOnline's and Pinnacle's own margin-free closes (log-odds), the last line's freshness, the instance's
    both-stages forecast (its result column is not read here), and whether the match ended in a retirement (Stage 0's
    status; read only inside a registered look or the dry run)."""
    b = pd.read_parquet(paths["book_prices"], columns=["match_id", "pin_a", "pin_b", "bol_a", "bol_b",
                                                        "bol_after_listed_min"])
    b = b.astype({"match_id": str}).drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    for book in ("pin", "bol"):
        ia, ib = 1 / b[f"{book}_a"].to_numpy(float), 1 / b[f"{book}_b"].to_numpy(float)
        f[f"L_{book}"] = H.lg(ia / (ia + ib))
        f.loc[~(np.isfinite(ia) & np.isfinite(ib)), f"L_{book}"] = np.nan
    f["bol_fresh"] = b["bol_after_listed_min"].to_numpy(float) >= -FRESH_MIN
    q = np.full(len(f), np.nan)
    if paths["forecasts"].exists():
        a = pd.read_parquet(paths["forecasts"], columns=["match_id", "q_full"]).astype({"match_id": str})
        q = a.drop_duplicates("match_id").set_index("match_id")["q_full"].reindex(f["match_id"]).to_numpy(float)
    f["L_model"] = np.where(np.isfinite(q), H.lg(q), np.nan)
    st = pd.read_parquet(H.STAGE0_M, columns=["match_id", "status"]).astype({"match_id": str})
    st = st.drop_duplicates("match_id").set_index("match_id")["status"].reindex(f["match_id"])
    f["retired"] = (st.astype(str).str.lower() == "retired").to_numpy()
    return f


def member_values(member: dict, frame: pd.DataFrame) -> np.ndarray:
    path = ROOT / member["values"]
    check_hash(path, member.get("values_sha256"), member["column"])
    v = pd.read_parquet(path, columns=["match_id", member["column"]]).astype({"match_id": str})
    s = v.drop_duplicates("match_id").set_index("match_id")[member["column"]]
    return s.reindex(frame["match_id"]).to_numpy(float)


# ------------------------------------------------------------------------------------------- the completeness gate

_GATE_CACHE: dict = {}


def _monthly_counts(kind: str) -> pd.Series:
    """Outcome-free input counts by (tour, month): 'lower_level' Stage 0's qualifying, Challenger/WTA 125 and ITF
    matches; 'box_all' Stage 0's matches with a box score; 'doubles' TennisLive's played doubles rows."""
    if kind in _GATE_CACHE:
        return _GATE_CACHE[kind]
    if kind in ("lower_level", "box_all"):
        m = pd.read_parquet(H.STAGE0_M, columns=["tour", "level", "qualifying", "tournament_date", "has_box"])
        m["month"] = pd.to_datetime(m["tournament_date"]).dt.to_period("M").astype(str)
        if kind == "lower_level":
            m = m[m["qualifying"].astype(bool) | m["level"].isin(["CH", "ITF"])]
        else:
            m = m[m["has_box"].astype(bool)]
        s = m.groupby(["tour", "month"]).size()
    elif kind == "doubles":
        tl = pd.read_parquet(TL_LISTED, columns=["tour", "discipline", "mixed", "junior", "played", "start_utc"])
        tl = tl[(tl["discipline"] == "doubles") & (tl["mixed"] != "TRUE") & (tl["junior"] != "TRUE") &
                (tl["played"] == "TRUE")].copy()
        tl["month"] = pd.to_datetime(tl["start_utc"], errors="coerce").dt.to_period("M").astype(str)
        s = tl.groupby([tl["tour"].astype(str).str.lower(), "month"]).size()
    else:
        raise ValueError(kind)
    _GATE_CACHE[kind] = s
    return s


def _prior_month(m: str) -> str:
    return str(pd.Period(m, "M") - 12)


def _three(month: str) -> list[str]:
    p = pd.Period(month, "M")
    return [str(p - 1), str(p), str(p + 1)]


def gate_mask(member: dict, frame: pd.DataFrame, x_all: pd.Series) -> tuple[np.ndarray, dict]:
    """True where the member passes the gate (or has none). For each tour and month the input count over the month and
    its two neighbours is compared with the same three months a year earlier (three months absorb events that change
    month between years; the gate was calibrated outcome-free on 2023-26 counts, process log): below GATE_RATIO the
    member is missing for that tour and month. x_all: the member's values for every frame match (presence gate)."""
    kind = member.get("gate", "none")
    ok = np.ones(len(frame), bool)
    failed = {}
    if kind == "none":
        return ok, failed
    for tour in ("atp", "wta"):
        for month in sorted(frame.loc[frame["tour"] == tour, "month"].unique()):
            now, before = _three(month), [_prior_month(m) for m in _three(month)]
            if kind == "presence":
                cur = pd.Index([]).append([_FRAME_MONTHS.get((tour, m), pd.Index([])) for m in now])
                prev = pd.Index([]).append([_FRAME_MONTHS.get((tour, m), pd.Index([])) for m in before])
                c1 = float(np.mean(np.isfinite(x_all.reindex(cur).to_numpy(float)))) if len(cur) else np.nan
                c0 = float(np.mean(np.isfinite(x_all.reindex(prev).to_numpy(float)))) if len(prev) else np.nan
            else:
                s = _monthly_counts(kind)
                c1 = float(sum(s.get((tour, m), 0) for m in now))
                c0 = float(sum(s.get((tour, m), 0) for m in before))
            if not (np.isfinite(c0) and c0 > 0) or not np.isfinite(c1):
                continue
            if c1 / c0 < GATE_RATIO:
                failed[f"{tour} {month}"] = round(c1 / c0, 3)
                ok[((frame["tour"] == tour) & (frame["month"] == month)).to_numpy()] = False
    return ok, failed


_FRAME_MONTHS: dict = {}


def _load_frame_months(paths: dict) -> None:
    """Outcome-free: every frame match id by (tour, month), for the presence gate's year-earlier months."""
    if _FRAME_MONTHS:
        return
    f = pd.read_parquet(paths["frame"], columns=["match_id", "tour", "tournament_date", "debut_season"])
    f = f[~f["debut_season"].astype(bool)]
    f["month"] = f["tournament_date"].dt.to_period("M").astype(str)
    for (tour, month), g in f.groupby(["tour", "month"]):
        _FRAME_MONTHS[(tour, month)] = pd.Index(g["match_id"].astype(str))


# --------------------------------------------------------------------------------------------------------- scores

def _scaled(frame: pd.DataFrame, x: np.ndarray) -> np.ndarray:
    sc = np.ones(len(frame))
    for tour in ("atp", "wta"):
        m = (frame["tour"] == tour).to_numpy()
        r = float(np.sqrt(np.nanmean(x[m] ** 2))) if np.isfinite(x[m]).any() else 0.0
        sc[m] = r if r > 0 else 1.0
    return x / sc


def member_score(m: dict, frame: pd.DataFrame, mode: str = "window", gate: np.ndarray | None = None) -> np.ndarray:
    """mode 'window' (the primary: re-projected and scaled in the window), 'frozen' (the ≤ 2024 projection and
    scales), 'raw' (no projection, scaled in the window)."""
    x = member_values(m, frame)
    if gate is not None:
        x = np.where(gate, x, np.nan)
    if mode == "window":
        x, _ = H.orthogonal_part(frame, x)
        z = _scaled(frame, x)
    elif mode == "frozen":
        x, _ = H.orthogonal_part(frame, x, coef=m["orth_coef"])
        sc = np.ones(len(frame))
        for tour in ("atp", "wta"):
            v = m["scale_orth"].get(tour)
            sc[(frame["tour"] == tour).to_numpy()] = v if v else 1.0
        z = x / sc
    elif mode == "raw":
        z = _scaled(frame, x)
    else:
        raise ValueError(mode)
    z = m["sign"] * z
    return np.where(np.isfinite(z), z, 0.0)


def group_score(g: dict, frame: pd.DataFrame, mode: str = "window", gates: dict | None = None) -> np.ndarray:
    """The mean of the members' scores over the members active for each match: a member the completeness gate sets to
    missing for a tour and month leaves the mean there (the red team's B3: the group keeps its scale); a value missing
    for any other reason counts 0. A match with every member gated scores 0."""
    parts, active = [], []
    for m in g["members"]:
        gm = None if gates is None else gates.get(m["column"])
        parts.append(member_score(m, frame, mode, gm))
        active.append(np.ones(len(frame), bool) if gm is None else np.asarray(gm, bool))
    P, A = np.column_stack(parts), np.column_stack(active).astype(float)
    n = A.sum(axis=1)
    return np.where(n > 0, (P * A).sum(axis=1) / np.maximum(n, 1), 0.0)


def omnibus_score(groups: list[dict], frame: pd.DataFrame, mode: str = "window", gates: dict | None = None) -> np.ndarray:
    parts = []
    for g in groups:
        s = group_score(g, frame, mode, gates)
        r = float(np.sqrt(np.mean(s ** 2)))
        parts.append(s / (r if r > 0 else 1.0))
    return np.mean(np.column_stack(parts), axis=1)


# ---------------------------------------------------------------------------------------------------------- fits

def fit(frame: pd.DataFrame, s: np.ndarray, base: str = "L", curv: bool = True, inputs: list[str] | None = None) -> dict:
    ok = np.isfinite(frame[base].to_numpy(float))
    g = frame[ok]
    s = np.asarray(s, float)[ok]
    if len(g) < 200 or not np.any(s != 0):
        return {"beta": np.nan, "se": np.nan, "z": np.nan, "blocks": 0, "p_one_sided": np.nan,
                "p_beta_positive": np.nan, "n": int(len(g)), "gain_mll_in_window": np.nan, "info": np.nan}
    y, blk = g["y"].to_numpy(float), g["block"].to_numpy()
    tour = g["tour"].to_numpy()
    Lb = g[base].to_numpy(float)
    B = H.tour_slope_cols(tour, Lb)
    if curv:
        B = np.column_stack([B, H.tour_slope_cols(tour, Lb * np.abs(Lb))])
    if inputs:
        X = g[[f"in_{n}" for n in inputs]].to_numpy(float)
        X = np.where(np.isfinite(X), X, 0.0)
        cols = []
        for t in ("atp", "wta"):
            mt = (tour == t)
            if mt.any():
                cols.append(X * mt[:, None])
        B = np.column_stack([B] + cols)
    rms = float(np.sqrt(np.mean(s ** 2)))
    xs = s / rms if rms > 0 else s
    Z = np.column_stack([B, xs])
    zero = np.zeros(len(y))
    b0, _ = H.fit_offset(B, y, zero, ridge=1e-6)
    b1, H1 = H.fit_offset(Z, y, zero, ridge=1e-6)
    V = H.cluster_cov(Z, y, zero, b1, H1, blk)
    se = float(np.sqrt(V[-1, -1]))
    G = int(len(np.unique(blk)))
    zval = float(b1[-1] / se)
    ll0 = -np.mean(np.where(y == 1, np.log(expit(B @ b0)), np.log(1 - expit(B @ b0))))
    ll1 = -np.mean(np.where(y == 1, np.log(expit(Z @ b1)), np.log(1 - expit(Z @ b1))))
    p = expit(Lb)
    return {"beta": float(b1[-1]), "se": se, "z": zval, "blocks": G, "p_one_sided": float(student_t.sf(zval, G - 1)),
            "p_beta_positive": float(student_t.cdf(zval, G - 1)), "n": int(len(y)),
            "gain_mll_in_window": float(1000 * (ll0 - ll1)), "info": float(np.sum(p * (1 - p)))}


def move_fit(frame: pd.DataFrame, s: np.ndarray) -> dict:
    """Outcome-free: BetOnline's open-to-close move on the score (least squares, per-tour slope on the opening)."""
    bt = pd.read_parquet(H.BET_TIMING, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                "p_bol_open", "p_bol_close", "ok_bol_open", "ok_bol_close",
                                                "known_bol_open"])
    bt = bt[~bt["debut_season"].astype(bool)].copy()
    keep = bt["ok_bol_open"].astype(bool) & bt["ok_bol_close"].astype(bool) & bt["known_bol_open"].astype(bool) & \
        np.isfinite(bt["p_bol_open"]) & np.isfinite(bt["p_bol_close"])
    bt = bt[keep.to_numpy()].copy()
    bt["match_id"] = bt["match_id"].astype(str)
    ser = pd.Series(np.asarray(s, float), index=frame["match_id"].to_numpy())
    ser = ser[~ser.index.duplicated()]
    x = ser.reindex(bt["match_id"]).to_numpy(float)
    ok = np.isfinite(x)
    g = bt[ok]
    if len(g) < 200 or not np.any(x[ok] != 0):
        return {"beta": np.nan, "z": np.nan, "n": int(len(g))}
    Lo = H.lg(g["p_bol_open"])
    mv = H.lg(g["p_bol_close"]) - Lo
    X = np.column_stack([H.tour_slope_cols(g["tour"].to_numpy(), np.asarray(Lo)), H.rms_scale(x[ok])])
    b, se = H.ols_cluster(X, np.asarray(mv), H.blocks(g["tournament_date"].to_numpy(), 28))
    return {"beta": float(b[-1]), "z": float(b[-1] / se[-1]) if se[-1] > 0 else np.nan, "n": int(len(g))}


def holm(p: list[float]) -> list[float]:
    """Holm-adjusted p-values; a NaN p stays NaN and does not count among the hypotheses (the red team's m4)."""
    p = np.asarray(p, float)
    adj = np.full(len(p), np.nan)
    idx = np.flatnonzero(np.isfinite(p))
    m = len(idx)
    run = 0.0
    for i, k in enumerate(idx[np.argsort(p[idx])]):
        run = max(run, (m - i) * p[k])
        adj[k] = min(run, 1.0)
    return adj.tolist()


def eb_positive(beta: float, se: float, b_disc: float) -> float:
    """P(beta > 0 | data) under a normal prior N(k b, (k b)^2), k = EB_K: the red team's empirical-Bayes secondary."""
    if not (np.isfinite(beta) and np.isfinite(se) and se > 0):
        return np.nan
    m0, s0 = EB_K * b_disc, abs(EB_K * b_disc) if b_disc else 1.0
    w = 1 / s0 ** 2 + 1 / se ** 2
    mean = (m0 / s0 ** 2 + beta / se ** 2) / w
    return float(norm.cdf(mean * np.sqrt(w)))


def secondaries(frame: pd.DataFrame, s: np.ndarray, s_frozen: np.ndarray, s_raw: np.ndarray, inputs: list[str],
                window: str) -> dict:
    sec = {"frozen_projection": fit(frame, s_frozen), "beyond_close_and_48_inputs": fit(frame, s, inputs=inputs),
           "raw_score": fit(frame, s_raw), "no_curvature": fit(frame, s, curv=False),
           "beyond_model": fit(frame, s, base="L_model"), "bol_close": fit(frame, s, base="L_bol"),
           "pin_close": fit(frame, s, base="L_pin")}
    fr = frame["bol_fresh"].to_numpy(bool)
    sec["bol_close_fresh"] = fit(frame[fr].reset_index(drop=True), s[fr], base="L_bol")
    sec["bol_close_stale"] = fit(frame[~fr].reset_index(drop=True), s[~fr], base="L_bol")
    for tour in ("atp", "wta"):
        m = (frame["tour"] == tour).to_numpy()
        sec[f"tour_{tour}"] = fit(frame[m].reset_index(drop=True), s[m])
    src = frame["odds_input"].astype(str).str.lower()
    for lab, m in (("period_pinnacle", src.str.contains("pinnacle").to_numpy()),
                   ("period_betonline", src.str.contains("betonline").to_numpy())):
        sec[lab] = fit(frame[m].reset_index(drop=True), s[m])
    comp = ~frame["retired"].to_numpy(bool)
    sec["completed_only"] = fit(frame[comp].reset_index(drop=True), s[comp])
    if window == "A":
        pre = np.array([d < GAP_START[t] for d, t in zip(frame["tournament_date"], frame["tour"])])
        sec["before_2026_data_gap"] = fit(frame[pre].reset_index(drop=True), s[pre])
    sec["move_outcome_free"] = move_fit(frame, s)
    return sec


def reading(frame: pd.DataFrame, disc: pd.DataFrame, s, s_disc, s_frozen, s_raw, inputs, window) -> dict:
    r = fit(frame, s)
    rd = fit(disc, s_disc)
    r.update({"beta_discovery_per_sd": rd["beta"], "z_discovery": rd["z"],
              "realisation_per_sd": r["beta"] / rd["beta"] if rd["beta"] else np.nan,
              "realisation_se": r["se"] / abs(rd["beta"]) if rd["beta"] else np.nan,
              "eb_p_beta_positive": eb_positive(r["beta"], r["se"], rd["beta"])})
    r["secondary"] = secondaries(frame, s, s_frozen, s_raw, inputs, window)
    return r


def verdict(p: float, p_lower: float, alpha: float) -> str:
    """p: the one-sided p in the registered direction; p_lower: the one-sided p in the other direction (both
    Holm-adjusted for H1-H5, the red team's m4)."""
    if not np.isfinite(p):
        return "no reading"
    if p <= alpha:
        return "confirmed: unpriced in the registered direction"
    if np.isfinite(p_lower) and p_lower <= alpha:
        return "contrary (the registered direction is rejected)"
    return "unresolved"


def p_lower(r: dict) -> float:
    return float(student_t.cdf(r["z"], r["blocks"] - 1)) if np.isfinite(r.get("z", np.nan)) else np.nan


def run(registry_path: Path, window: str, owner_go: str | None, look_a_result: Path | None = None) -> dict:
    reg = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    paths = instance_paths(reg)
    allow = window in ("A", "B")
    if allow and not owner_go:
        raise RuntimeError("a registered look needs --owner-go with the owner's words")
    if window == "B":
        start, end = "2026-07-29", reg["look_b_end"]
        frame = load_window(paths, 2026, 2100, end, allow_post_2024=True, start_date=start)
    else:
        first, last, end = WINDOWS[window]
        start = f"season {first}"
        frame = load_window(paths, first, last, end, allow_post_2024=allow)
    frame = add_bases(frame, paths)
    _load_frame_months(paths)
    inputs = [n for n in H.diff_input_names()]
    disc = H.load_frame()
    groups = reg["groups"]
    # the completeness gate (outcome-free)
    gates, gate_report = {}, {}
    for g in groups + reg.get("look_b_only", []):
        for m in g["members"]:
            vals = pd.read_parquet(ROOT / m["values"], columns=["match_id", m["column"]]).astype({"match_id": str})
            x_all = vals.drop_duplicates("match_id").set_index("match_id")[m["column"]]
            ok, failed = gate_mask(m, frame, x_all)
            gates[m["column"]] = ok
            gate_report[m["column"]] = failed
    out = {"window": window, "start": start, "end": end, "registry": str(registry_path),
           "registry_sha256": sha256(registry_path), "owner_go": owner_go, "run_at": time.strftime("%Y-%m-%d %H:%M:%S"),
           "matches": int(len(frame)), "by_tour": frame["tour"].value_counts().to_dict(),
           "alpha_look_a": ALPHA_A, "alpha_final": ALPHA_FINAL, "gate_failures": gate_report}
    s = omnibus_score(groups, frame, "window", gates)
    o = reading(frame, disc, s, omnibus_score(groups, disc, "window"), omnibus_score(groups, frame, "frozen", gates),
                omnibus_score(groups, frame, "raw", gates), inputs, window)
    rows = []
    for g in groups:
        sg = group_score(g, frame, "window", gates)
        rg = reading(frame, disc, sg, group_score(g, disc, "window"), group_score(g, frame, "frozen", gates),
                     group_score(g, frame, "raw", gates), inputs, window)
        rg.update({"id": g["id"], "name": g["name"]})
        rg["members"] = {m["column"]: fit(frame, member_score(m, frame, "window", gates[m["column"]]))
                         for m in g["members"]}
        rg["members_secondary_only"] = {m["column"]: fit(frame, member_score(m, frame, "window", None))
                                        for m in g.get("secondary_members", [])}
        rows.append(rg)
    # verdicts
    if window == "A":
        o["verdict"] = verdict(o["p_one_sided"], p_lower(o), ALPHA_A)
        gate_open = o["verdict"].startswith("confirmed")
        adj = holm([rg["p_one_sided"] for rg in rows])
        adj_low = holm([p_lower(rg) for rg in rows])
        for rg, a, al in zip(rows, adj, adj_low):
            rg["p_holm"], rg["p_holm_lower"] = a, al
            rg["verdict"] = (verdict(a, al, ALPHA_A) if gate_open
                             else "not tested (H0 not confirmed at this look)")
    elif window == "B":
        o["verdict"] = "Look B alone: no verdict (see the final)"
        for rg in rows:
            rg["verdict"] = "Look B alone: no verdict"
        if look_a_result:
            out["final"] = final_combination(json.loads(Path(look_a_result).read_text(encoding="utf-8")), o, rows)
        for h in reg.get("look_b_only", []):
            sh = group_score(h, frame, "window", gates)
            rh = fit(frame, sh)
            rh["verdict"] = verdict(rh["p_one_sided"], p_lower(rh), 0.05)
            out.setdefault("look_b_only", {})[h["id"]] = rh
    else:
        o["verdict"] = "dry run: no verdict"
        for rg in rows:
            rg["p_holm"] = np.nan
            rg["verdict"] = "dry run: no verdict"
    out["omnibus"] = o
    out["groups"] = rows
    return out


def final_combination(a: dict, ob: dict, rows_b: list[dict]) -> dict:
    """The final: H0 on the combined z of Looks A and B (only if Look A did not confirm it), then H1-H5 on theirs."""
    def comb(ra: dict, rb: dict) -> dict:
        za, zb = norm.isf(ra["p_one_sided"]), norm.isf(rb["p_one_sided"])
        ia, ib = ra["info"], rb["info"]
        z = (np.sqrt(ia) * za + np.sqrt(ib) * zb) / np.sqrt(ia + ib)
        return {"z_combined": float(z), "p_combined": float(norm.sf(z)), "info_a": ia, "info_b": ib}
    res = {"look_a_verdict": a["omnibus"]["verdict"]}
    if a["omnibus"]["verdict"].startswith("confirmed"):
        res["note"] = "H0 was confirmed at Look A; the final is not needed for H0 (Look B is a replication reading)"
        return res
    c = comb(a["omnibus"], ob)
    c["verdict"] = "confirmed: unpriced in the registered direction" if c["p_combined"] <= ALPHA_FINAL else "unresolved"
    res["omnibus"] = c
    if c["verdict"].startswith("confirmed"):
        ga = {g["id"]: g for g in a["groups"]}
        cg = {rb["id"]: comb(ga[rb["id"]], rb) for rb in rows_b}
        adj = holm([v["p_combined"] for v in cg.values()])
        for (k, v), p in zip(cg.items(), adj):
            v["p_holm"] = p
            v["verdict"] = "confirmed: unpriced in the registered direction" if p <= ALPHA_FINAL else "unresolved"
        res["groups"] = cg
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--look", choices=["A", "B"])
    ap.add_argument("--owner-go")
    ap.add_argument("--look-a-result")
    a = ap.parse_args()
    window = "dry-run" if a.dry_run else a.look
    if window is None:
        raise SystemExit("choose --dry-run or --look A|B")
    res = run(Path(a.registry), window, a.owner_go, Path(a.look_a_result) if a.look_a_result else None)
    d = OUT / window
    d.mkdir(parents=True, exist_ok=True)
    (d / "result.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    o = res["omnibus"]
    print(f"OMNIBUS beta {o['beta']:+.4f} z {o['z']:+.2f} p1 {o['p_one_sided']:.4f} real/SD "
          f"{o['realisation_per_sd']:+.2f} EB {o['eb_p_beta_positive']:.2f}  {o['verdict']}")
    for g in res["groups"]:
        print(f"{g['id']:>4} {g['name'][:44]:<44} beta {g['beta']:+.4f} z {g['z']:+.2f} p1 {g['p_one_sided']:.4f} "
              f"real/SD {g['realisation_per_sd']:+.2f}  {g['verdict']}")
    print("gate failures:", {k: len(v) for k, v in res["gate_failures"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
