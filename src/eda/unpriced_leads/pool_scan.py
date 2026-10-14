"""S1, the pool scan of the unpriced-leads study (docs/studies/unpriced_leads/team/pool_scan.md, 13 Oct 2026).

Every column of the feature universe's selection pool (data/studies/feature_universe/menu.csv) that is not one of the
current best model's inputs, screened with the study's discovery harness (src/eda/unpriced_leads/screen.py) on seasons
<= 2024 only. Outcomes are read only through the harness (load_frame and the model lens), which filters and asserts
tournament_date < 2025-01-01; the 136 rows of season 2025 whose events started on 29-30 Dec 2024 are dropped here
before anything else, so no match of season 2025 enters any reading. Everything else is outcome-free: the store has no
result column, and the 2025-26 coverage counts read only the store's own rows, which end on 28 Jul 2026 (Look A).

Candidates (fixed before any reading; see the memo's method section):
    * the menu rows whose defining catalogue row is not `in_model`, plus m__ios_points_short (catalogued in_model on
      7 Oct, dropped from the model by the owner on 9 Oct, so no longer an input);
    * kind diff: screened as is; kind pair: screened as A - B (the column minus its partner); kind context: the
      harness's slope-modifier form (L * standardised s);
    * every diff and pair is screened again as its orthogonal part, `<name>__orth` (screen.orthogonal_part: x minus its
      least-squares projection, by tour and without an intercept, on the model's 48 non-price, non-context inputs),
      through the same three lenses.
Flags carried: market_internal (mk__ and B-ANCHOR's three), base_dependent (the store's ten, eight on the menu: they
read the 7 Oct model's 2014-24 forecast), known_null (the two kn__ columns on the menu and the alt__ twins of the other
eleven), now_in_model (a context column equal to a current context input: the both-tours indoor flag since the 9 Oct
indoor decision), dropped_from_model (ios_points_short), copy_of_input (|r| >= 0.95 with one in-model input),
seen_2025_2026 (menu.csv). Added after the first full run had been seen: near_context_input (a context column with
|r| >= 0.85 with a context input, e.g. B-LEVER's s1 against best_of) and unstable (sign-flip placebo RMS z >= 3 in any
tour and encoding: rare indicators whose cluster-robust z is not trustworthy). A flagged column is screened and
reported, never shortlisted; unstable and base-dependent columns are also left out of the family counts.

Negative controls: the known nulls; and sign-flip placebos, each candidate's tested column multiplied by an independent
random sign per four-week block (3 draws per candidate and encoding, close lens only). Under the null of no information
beyond the close the flip changes nothing; under an effect it scrambles it. Their z's are the empirical null for these
columns' own distributions, missingness and clustering.

Outputs (data/studies/unpriced_leads/pool_scan/):
    long.csv               every reading (lens x era x tour) of every candidate, raw and orthogonal
    summary.csv            one row per candidate and tour
    family.csv             family, subfamily and feature-interactions block view
    shortlist_rule.csv     the rows passing the pre-declared rule (no flag; |z_pool| >= 2 with >= 3 of 4 eras of its sign;
                           for a diff or pair the same for the orthogonal part, same sign), best member per cluster
    joint.csv              post hoc: the memo's representatives read jointly (beside each other; and beside the 48 inputs)
    joint_corr.csv         their pairwise-complete correlations (outcome-free)
    placebo.csv            the sign-flip placebo readings (pooled close lens)
    negative_controls.csv  the known nulls' readings and the placebo calibration
    clusters.csv           outcome-free signal clusters (complete linkage, |r| >= 0.8, pairwise-complete r)
    join_coverage.csv      the store-to-frame join by tour and season (the store has no men's 2018)
    run.json               counts, hashes of the inputs, timings, the design constants

Run: ./python.sh src/eda/unpriced_leads/pool_scan.py      (CPU, 5-10 minutes; deterministic)
Numerics: one BLAS thread is set before numpy loads, so the digits do not depend on the machine's core count or load;
correlation ties (copies) are broken on values rounded to 9 decimals; a context column without variation within a tour
(B-LEVER's best-of-five modifier for women) is blanked for that tour, where its fit is singular.
"""
from __future__ import annotations

import os

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")   # one BLAS thread (set before numpy loads): the same digits on any machine, and
                                     # no thread oversubscription when other jobs share the CPU

import argparse  # noqa: E402
import hashlib  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.cluster.hierarchy import fcluster, linkage  # noqa: E402
from scipy.spatial.distance import squareform  # noqa: E402
from scipy.stats import norm  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as S  # noqa: E402

FU = ROOT / "data" / "studies" / "feature_universe"
STORE = FU / "store.parquet"
MENU = FU / "menu.csv"
REGISTRY = FU / "store_registry.csv"
UNIVERSE = FU / "universe.csv"
OUT = ROOT / "data" / "studies" / "unpriced_leads" / "pool_scan"

LOOK_A_END = pd.Timestamp("2026-07-28")         # the store's last day; Look A is 1 Jan 2025 - 28 Jul 2026
NULL_SD = 1.08                                  # the harness's placebo SD of z (harness_selftest.json)
SEED = 20261013
N_PLACEBO = 3
CLUSTER_R = 0.8                                 # complete linkage: every pair in a cluster has |r| >= 0.8
COPY_R = 0.95                                   # a candidate this close to one in-model input is a re-encoding
NEAR_CONTEXT_R = 0.85                           # a context modifier this close to a context input (best_of, level)
UNSTABLE_RMS = 3.0                              # placebo RMS z at or above this in any cell: the z is not trustworthy
RULE_Z, RULE_ERAS = 2.0, 3                      # the shortlist rule (fixed before the full run; see the memo)
DROPPED = {"m__ios_points_short": "dropped from the model by the owner on 9 Oct 2026 (the 57-input template)"}
CONTEXT_INPUTS = ["in_" + c for c in S.CONTEXT]
ERA_KEYS = list(S.ERAS)


# ----------------------------------------------------------------------------------------------- the candidates

def build_candidates() -> pd.DataFrame:
    """One row per screened candidate (a pair is one candidate, A - B), with its catalogue fields and flags."""
    menu = pd.read_csv(MENU)
    reg = pd.read_csv(REGISTRY)
    uni = pd.read_csv(UNIVERSE).set_index("feature_id")
    kn = reg[reg["column"].str.startswith("kn__")]
    kn_cols = set(kn["column"]) | set(kn["canonical"].dropna()) | set(kn["near_dup_of"].dropna())
    keep = menu[(menu["status"] != "in_model") | menu["column"].isin(list(DROPPED))].copy()
    by_col = keep.set_index("column")
    rows, done = [], set()
    for r in keep.sort_values("column").itertuples(index=False):
        if r.kind == "pair":
            a, b = (r.column, r.partner) if r.column.endswith("_a") else (r.partner, r.column)
            if a in done:
                continue
            done.add(a)
            name = a[:-2] + "_a-b"
            seen = "yes" if "yes" in (by_col.loc[a, "seen_2025_2026"], by_col.loc[b, "seen_2025_2026"]) else "no"
            src = by_col.loc[a]
        else:
            a, b, name, seen, src = r.column, None, r.column, r.seen_2025_2026, by_col.loc[r.column]
        flag = str(src["store_flag"]) if isinstance(src["store_flag"], str) else ""
        fid = src["feature_id"]
        rows.append({
            "name": name, "kind": src["kind"], "col_a": a, "col_b": b, "group": src["group"],
            "feature_id": fid, "catalogue_name": src["name"], "family": src["family"],
            "subfamily": uni.loc[fid, "subfamily"] if fid in uni.index else np.nan,
            "fi_block": src["hid"] if isinstance(src["hid"], str) else np.nan,
            "status": src["status"], "timing_class": src["timing_class"], "near_miss_tier": src["near_miss_tier"],
            "priority": src["priority"], "seen_2025_2026": seen,
            "market_internal": ("market_internal" in flag) or src["group"] == "mk",
            "base_dependent": "base-dependent" in flag,
            "known_null": (a in kn_cols) or (b in kn_cols if b else False),
            "dropped_from_model": a in DROPPED,
            "aliases": src["aliases"] if isinstance(src["aliases"], str) else "",
        })
    c = pd.DataFrame(rows).sort_values("name", kind="stable").reset_index(drop=True)
    if c["name"].duplicated().any():
        raise RuntimeError("duplicate candidate names")
    return c


# --------------------------------------------------------------------------------------------- the data, aligned

def load_screen_frame() -> pd.DataFrame:
    """The harness's frame (outcomes < 2025-01-01, asserted there), seasons <= 2024 only."""
    f = S.load_frame()
    f = f[f["season"] <= 2024].reset_index(drop=True)
    if f["tournament_date"].max() >= S.DISCOVERY_END:
        raise RuntimeError("a 2025 outcome is in the frame")
    return f


def read_store(cols: list[str]) -> pd.DataFrame:
    st = pd.read_parquet(STORE, columns=["match_id", "tour", "season", "tournament_date", "debut_season"] + cols)
    st["match_id"] = st["match_id"].astype(str)
    if not st["match_id"].is_unique:
        raise RuntimeError("store match_id not unique")
    return st


def candidate_values(store: pd.DataFrame, cand: pd.Series, rows: np.ndarray) -> np.ndarray:
    """The candidate on the given store rows (-1 = absent): A - B for a pair, else the column."""
    def col(c):
        v = store[c].to_numpy(float)
        out = np.full(len(rows), np.nan)
        ok = rows >= 0
        out[ok] = v[rows[ok]]
        return out
    if cand["kind"] == "pair":
        return col(cand["col_a"]) - col(cand["col_b"])
    return col(cand["col_a"])


def join_rows(store: pd.DataFrame, match_ids: pd.Series) -> np.ndarray:
    pos = pd.Series(np.arange(len(store)), index=store["match_id"])
    return pos.reindex(match_ids.astype(str).to_numpy()).fillna(-1).to_numpy(int)


def join_coverage(store: pd.DataFrame) -> pd.DataFrame:
    """Outcome-free: the current frame's rows (to 28 Jul 2026, no result column read) found in the store."""
    fo = pd.read_parquet(S.FRAME, columns=["match_id", "tour", "season", "tournament_date", "debut_season"],
                         filters=[("tournament_date", "<=", LOOK_A_END)])
    fo["match_id"] = fo["match_id"].astype(str)
    fo = fo[(fo["season"] >= 2013) & ~fo["debut_season"].astype(bool)]
    fo["in_store"] = fo["match_id"].isin(set(store["match_id"]))
    g = fo.groupby(["tour", "season"]).agg(frame_rows=("match_id", "size"), in_store=("in_store", "sum"))
    st = store[~store["debut_season"].astype(bool)].groupby(["tour", "season"]).size().rename("store_rows")
    g = g.join(st, how="outer").fillna(0).astype(int).reset_index()
    g["share_in_store"] = np.where(g["frame_rows"] > 0, g["in_store"] / g["frame_rows"].clip(lower=1), np.nan)
    return g


# --------------------------------------------------------------------------------------- outcome-free relations

def nearest_input(frame: pd.DataFrame, x: np.ndarray, names: list[str]) -> tuple[str, float]:
    """The in-model input with the largest |pairwise-complete r| with x (rows where both are present)."""
    X = frame[[f"in_{n}" for n in names]].to_numpy(float)
    best, br = "", 0.0
    okx = np.isfinite(x)
    for j, n in enumerate(names):
        ok = okx & np.isfinite(X[:, j])
        if ok.sum() < 200:
            continue
        a, b = x[ok], X[ok, j]
        if a.std() == 0 or b.std() == 0:
            continue
        r = round(float(np.corrcoef(a, b)[0, 1]), 9)     # rounded: near-exact ties break by input order
        if abs(r) > abs(br):
            best, br = n, r
    return best, br


def pairwise_corr(X: np.ndarray, min_n: int = 500) -> np.ndarray:
    """Pairwise-complete correlations of the columns of X (NaN = missing), by matrix products; NaN below min_n."""
    M = np.isfinite(X).astype(float)
    mu = np.nanmean(np.where(M > 0, X, np.nan), axis=0)
    sd = np.nanstd(np.where(M > 0, X, np.nan), axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    Z0 = np.where(M > 0, (X - mu) / sd, 0.0)
    N = M.T @ M
    Sx = Z0.T @ M
    Sxx = (Z0 ** 2).T @ M
    Sxy = Z0.T @ Z0
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = Sxy - Sx * Sx.T / N
        vx = Sxx - Sx ** 2 / N
        r = cov / np.sqrt(vx * vx.T)
    r[N < min_n] = np.nan
    np.fill_diagonal(r, 1.0)
    return r


def li_ji_meff(r: np.ndarray) -> float:
    """Li & Ji (2005) effective number of tests from a correlation matrix (missing r treated as 0)."""
    if len(r) == 0:
        return 0.0
    rr = np.where(np.isfinite(r), r, 0.0)
    rr = (rr + rr.T) / 2
    lam = np.abs(np.linalg.eigvalsh(rr))
    return float(np.sum((lam >= 1).astype(float) + (lam - np.floor(lam))))


def clusters(names: list[str], r: np.ndarray, prefix: str) -> dict[str, str]:
    if len(names) == 1:
        return {names[0]: f"{prefix}001"}
    d = 1 - np.abs(np.where(np.isfinite(r), r, 0.0))
    d = np.round((d + d.T) / 2, 9)                     # rounded: no merge order hangs on the last bits
    np.fill_diagonal(d, 0.0)
    lab = fcluster(linkage(squareform(np.clip(d, 0, None), checks=False), method="complete"),
                   t=1 - CLUSTER_R, criterion="distance")
    # number clusters by their first member in name order, so ids are stable
    first: dict[int, int] = {}
    for i, l in enumerate(lab):
        first.setdefault(int(l), i)
    order = {l: k + 1 for k, l in enumerate(sorted(first, key=first.get))}
    return {n: f"{prefix}{order[int(l)]:03d}" for n, l in zip(names, lab)}


# ------------------------------------------------------------------------------------------------------ helpers

def move_lens_safe(frame: pd.DataFrame, x, name: str, kind: str = "diff") -> pd.DataFrame:
    """screen.move_lens tour by tour, with a NaN reading where the candidate is absent from a tour's BetOnline rows
    (the harness's least squares is singular there and raises for every tour). Same arithmetic otherwise."""
    bt = S._move_frame()
    s = pd.Series(np.asarray(x, float), index=frame["match_id"].astype(str).to_numpy())
    s = s[~s.index.duplicated()]
    xb = s.reindex(bt["match_id"]).to_numpy(float)
    if kind == "context":
        ok = np.isfinite(xb)
        mu, sd = (np.nanmean(xb[ok]), np.nanstd(xb[ok])) if ok.any() else (0.0, 1.0)
        xb = bt["Lo"].to_numpy(float) * np.where(ok, (xb - mu) / (sd if sd > 0 else 1.0), np.nan)
    rows = []
    for tour in S.TOURS:
        m = np.ones(len(bt), bool) if tour == "both" else (bt["tour"] == tour).to_numpy()
        g = bt[m]
        xs = S.rms_scale(xb[m])
        r = {"name": name, "kind": kind, "lens": "move", "era": "2018-24", "tour": tour, "beta": np.nan,
             "se": np.nan, "z": np.nan, "n": int(len(g)), "present": float(np.mean(np.isfinite(xb[m])))}
        if np.any(xs != 0):
            X = np.column_stack([S.tour_slope_cols(g["tour"].to_numpy(), g["Lo"].to_numpy(float)), xs])
            try:
                b, se = S.ols_cluster(X, g["move"].to_numpy(float), g["block"].to_numpy())
                r.update({"beta": float(b[-1]), "se": float(se[-1]),
                          "z": float(b[-1] / se[-1]) if se[-1] > 0 else np.nan})
            except np.linalg.LinAlgError:
                pass
        rows.append(r)
    return pd.DataFrame(rows)


def screen_safe(frame: pd.DataFrame, x, name: str, kind: str) -> tuple[pd.DataFrame, bool]:
    """screen.screen; on a singular move-lens fit, the same lenses with the move lens taken tour by tour."""
    try:
        return S.screen(frame, x, name, kind), False
    except np.linalg.LinAlgError:
        out = pd.concat([S.close_lens(frame, x, name, kind), S.model_lens(frame, x, name, kind),
                         move_lens_safe(frame, x, name, kind)], ignore_index=True)
        r2 = S.redundancy(frame, x, kind)
        out["r2_inputs"] = out["tour"].map(r2)
        return out, True


def pooled(h: pd.DataFrame, eras: list[str]) -> tuple[float, float]:
    """Inverse-variance pool of the close lens's era readings over the named eras: (z, beta)."""
    h = h[h["era"].isin(eras) & np.isfinite(h["se"]) & (h["se"] > 0)]
    if h.empty:
        return np.nan, np.nan
    w = 1 / h["se"] ** 2
    b = float((w * h["beta"]).sum() / w.sum())
    return b / float(np.sqrt(1 / w.sum())), b


def sign_flip(x: np.ndarray, blk: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    labels, ix = np.unique(blk, return_inverse=True)
    s = rng.choice(np.array([-1.0, 1.0]), size=len(labels))
    return x * s[ix]


# Chosen AFTER the scan (post hoc), for the memo: one representative per area of the game it discusses, read jointly so
# that the memo can say which areas are distinct signals and which are one phenomenon under several names.
JOINT = ["fi__B-MOTIV__post_slam", "pp__rank_points_a-b", "pp__seeded_a-b", "fp__f14_anchor__fame_a-b",
         "fi__B-VENUE__x", "el__low_share_diff", "fp__f12_salience__hasL_a-b", "fp__f26_impairment__bdinj_rust0_a-b",
         "fi__B11__bd11_on", "fp__f07_evidence_age__f07_s0_a-b", "fi__B-STATE__x", "ad__adjperf_spw_decayed",
         "fi__B-OVERREACT__luck_13w", "pp__elo_N_a-b", "alt__surface_first", "fp__f23_arrival__bd10_trav_a-b",
         "lv__iosO_first_won", "lv__elo"]


def joint_check(frame: pd.DataFrame, cols: dict[str, np.ndarray], kinds: dict[str, str]) -> pd.DataFrame:
    """Each listed candidate's coefficient beside all the others (and, in a second reading, beside the model's 48
    non-price inputs as linear controls), per era and tour as the close lens fits it (tour slopes on L, no intercept,
    columns scaled by their RMS, missing = 0, cluster-robust over four-week blocks), the eras pooled by inverse
    variance. Outcomes <= 2024 only (the screened frame). Descriptive and post hoc."""
    names = [n for n in JOINT if n in cols]
    X_all = np.column_stack([S.candidate_x(frame, cols[n], "context" if kinds[n] == "context" else "diff")
                             for n in names])
    inputs = frame[[f"in_{n}" for n in S.diff_input_names()]].to_numpy(float)
    inputs = np.where(np.isfinite(inputs), inputs, 0.0)
    rows = []
    for ctrl in (False, True):
        for tour in S.TOURS:
            per_era = []
            for era, (a, b) in S.ERAS.items():
                m = frame["season"].between(a, b).to_numpy()
                if tour != "both":
                    m = m & (frame["tour"] == tour).to_numpy()
                g = frame[m]
                Z = [S.tour_slope_cols(g["tour"].to_numpy(), g["L"].to_numpy(float))]
                Z.append(np.column_stack([S.rms_scale(X_all[m, k]) for k in range(len(names))]))
                if ctrl:
                    Z.append(np.column_stack([S.rms_scale(inputs[m, k]) for k in range(inputs.shape[1])]))
                Z = np.column_stack(Z)
                y = g["y"].to_numpy(float)
                zero = np.zeros(len(y))
                bta, H = S.fit_offset(Z, y, zero)
                V = S.cluster_cov(Z, y, zero, bta, H, g["block"].to_numpy())
                k0 = Z.shape[1] - len(names) - (inputs.shape[1] if ctrl else 0)
                per_era.append((bta[k0:k0 + len(names)], np.sqrt(np.clip(np.diag(V)[k0:k0 + len(names)], 0, None))))
            for k, n in enumerate(names):
                bs = np.array([p[0][k] for p in per_era])
                ss = np.array([p[1][k] for p in per_era])
                ok = np.isfinite(ss) & (ss > 0)
                w = 1 / ss[ok] ** 2
                bp = float((w * bs[ok]).sum() / w.sum())
                sp = float(np.sqrt(1 / w.sum()))
                rows.append({"candidate": n, "tour": tour, "controls": "48 inputs" if ctrl else "none",
                             "beta_joint": bp, "z_joint": bp / sp,
                             "eras_same_sign_joint": int((np.sign(bs[ok]) == np.sign(bp)).sum()),
                             **{f"z_joint_{e}": float(bs[i] / ss[i]) if ok[i] else np.nan
                                for i, e in enumerate(S.ERAS)}})
    return pd.DataFrame(rows)


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------------------------------------- run

def run(n_placebo: int = N_PLACEBO, limit: int | None = None) -> dict:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    cands = build_candidates()
    if limit:
        cands = cands.head(limit)
    frame = load_screen_frame()
    names48 = S.diff_input_names()
    cols = sorted(set(cands["col_a"]) | set(cands["col_b"].dropna()))
    store = read_store(cols)
    jc = join_coverage(store)
    jc.to_csv(OUT / "join_coverage.csv", index=False)

    rows_f = join_rows(store, frame["match_id"])
    st_nd = ~store["debut_season"].astype(bool).to_numpy()
    st_tour = store["tour"].to_numpy()
    st_season = store["season"].to_numpy()
    st_rows_all = np.arange(len(store))
    blk = frame["block"].to_numpy()
    tour_f = frame["tour"].to_numpy()

    long_parts, plc_rows, extra, tested_cols = [], [], [], {}
    for i, c in cands.iterrows():
        x = candidate_values(store, c, rows_f)
        xs = candidate_values(store, c, st_rows_all)
        rec = {"name": c["name"]}
        # outcome-free coverage: the store's own rows (2025-26 = Look A, 1 Jan 2025 - 28 Jul 2026), by tour
        for tour in ("atp", "wta"):
            for lab, (a, b) in (("2013_24", (2013, 2024)), ("2025_26", (2025, 2026))):
                m = st_nd & (st_tour == tour) & (st_season >= a) & (st_season <= b)
                rec[f"cov_{tour}_{lab}"] = float(np.mean(np.isfinite(xs[m]))) if m.any() else np.nan
            m = tour_f == tour
            rec[f"cov_{tour}_2013_24_frame"] = float(np.mean(np.isfinite(x[m])))
        # outcome-free relations to the model's inputs
        if c["kind"] == "context":
            best, br = "", 0.0
            for ci in CONTEXT_INPUTS:
                v = frame[ci].to_numpy(float)
                ok = np.isfinite(x) & np.isfinite(v)
                if ok.sum() > 200 and x[ok].std() > 0 and v[ok].std() > 0:
                    r = round(float(np.corrcoef(x[ok], v[ok])[0, 1]), 9)
                    if abs(r) > abs(br):
                        best, br = ci[3:], r
        else:
            best, br = nearest_input(frame, x, names48)
        rec["nearest_input"], rec["r_nearest_input"] = best, br
        extra.append(rec)
        # the candidate's values on the screened rows (a context's raw s), for the outcome-free clusters
        tested_cols[c["name"]] = x
        # the screens (a pair is screened as its A - B, i.e. as the harness's "diff")
        skind = "context" if c["kind"] == "context" else "diff"
        lr, fb = screen_safe(frame, x, c["name"], skind)
        lr["encoding"] = "raw"
        long_parts.append(lr)
        xo = None
        if skind == "diff":
            xo, _ = S.orthogonal_part(frame, x)
            lo, fbo = screen_safe(frame, xo, c["name"] + "__orth", "diff")
            lo["encoding"] = "orth"
            long_parts.append(lo)
            fb = fb or fbo
        rec["move_lens_by_tour"] = fb
        # sign-flip placebos (close lens only), on the tested column
        xx = S.candidate_x(frame, x, skind)
        for enc, col in (("raw", xx), ("orth", xo)):
            if col is None:
                continue
            for d in range(n_placebo):
                rng = np.random.default_rng([SEED, i, d, 0 if enc == "raw" else 1])
                cl = S.close_lens(frame, sign_flip(col, blk, rng), c["name"], "diff")
                for tour, h in cl.groupby("tour"):
                    p = h[h["era"] == "2013-24 pooled"]
                    if len(p):
                        plc_rows.append({"name": c["name"], "encoding": enc, "draw": d, "tour": tour,
                                         "z_pool": float(p["z"].iloc[0]),
                                         "eras_same_sign": p["eras_same_sign"].iloc[0]})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(cands)} candidates, {time.time() - t0:.0f}s", flush=True)

    long = pd.concat(long_parts, ignore_index=True).rename(columns={"kind": "screen_kind"})
    long["candidate"] = long["name"].str.replace(r"__orth$", "", regex=True)
    plc = pd.DataFrame(plc_rows)
    extra = pd.DataFrame(extra)

    # A context candidate with no variation within a tour is not identifiable there: L * s is a multiple of that
    # tour's own price slope, so the fit is singular and its numbers are rounding noise (e.g. B-LEVER's best-of-five
    # modifier for women). Those (candidate, tour) readings are blanked in every lens and in the placebos.
    degenerate = []
    for c in cands.itertuples(index=False):
        if c.kind != "context":
            continue
        x = tested_cols[c.name]
        ok = np.isfinite(x)
        scale = float(np.std(x[ok])) if ok.any() else 0.0
        for tour in ("atp", "wta"):
            m = (tour_f == tour) & ok
            if m.sum() < 2 or float(np.std(x[m])) <= 1e-9 * max(scale, 1e-12):
                degenerate.append((c.name, tour))
    if degenerate:
        dkey = pd.MultiIndex.from_tuples(degenerate)
        dl = pd.MultiIndex.from_arrays([long["candidate"], long["tour"]]).isin(dkey)
        long.loc[dl, ["beta", "se", "z", "eras_same_sign", "eras_abs_z_ge_2"]] = np.nan
        if len(plc):
            dp = pd.MultiIndex.from_arrays([plc["name"], plc["tour"]]).isin(dkey)
            plc.loc[dp, ["z_pool", "eras_same_sign"]] = np.nan

    # ---- summaries: raw and orthogonal, one row per candidate and tour
    raw = S.summarize(long[long["encoding"] == "raw"].rename(columns={"screen_kind": "kind"}))
    raw = raw.rename(columns={"name": "candidate"}).drop(columns="kind")
    orth = S.summarize(long[long["encoding"] == "orth"].rename(columns={"screen_kind": "kind"}))
    orth["candidate"] = orth["name"].str.replace(r"__orth$", "", regex=True)
    keep_o = ["beta_pool", "z_pool", "eras_same_sign", "eras_abs_z_ge_2", "z_2013-16", "z_2017-19", "z_2020-22",
              "z_2023-24", "z_model_2020_24", "z_move_2018_24", "r2_inputs", "p_pool", "q_pool"]
    orth = orth[["candidate", "tour"] + keep_o].rename(columns={k: f"{k}_orth" for k in keep_o})
    summ = raw.merge(orth, on=["candidate", "tour"], how="left")

    # split-sample readings (close lens, from the eras): 2013-19 and 2020-24, raw and orthogonal
    sp = []
    for (name, tour, enc), h in long[(long["lens"] == "close")].groupby(["candidate", "tour", "encoding"]):
        z1, _ = pooled(h, ["2013-16", "2017-19"])
        z2, _ = pooled(h, ["2020-22", "2023-24"])
        e = h[h["era"].isin(ERA_KEYS) & np.isfinite(h["se"]) & (h["se"] > 0)]
        nmin = float((e["present"] * e["n"]).min()) if len(e) else np.nan
        sfx = "" if enc == "raw" else "_orth"
        sp.append({"candidate": name, "tour": tour, f"z_close_2013_19{sfx}": z1, f"z_close_2020_24{sfx}": z2,
                   f"min_era_present_n{sfx}": nmin})
    sp = pd.DataFrame(sp).groupby(["candidate", "tour"], as_index=False).first()
    summ = summ.merge(sp, on=["candidate", "tour"], how="left")
    for sfx in ("", "_orth"):
        summ[f"rep_2020_24{sfx}"] = np.sign(summ[f"z_close_2013_19{sfx}"]) * summ[f"z_close_2020_24{sfx}"]
        summ[f"absorb_model{sfx}"] = summ[f"z_model_2020_24{sfx}"] / summ[f"z_close_2020_24{sfx}"]

    # ---- clusters (outcome-free), on the screened frame's rows
    kind_of = dict(zip(cands["name"], cands["kind"]))
    names_dp = [n for n in cands["name"] if kind_of[n] != "context"]
    names_c = [n for n in cands["name"] if kind_of[n] == "context"]
    cl_map, r_mats = {}, {}
    for nm, prefix in ((names_dp, "D"), (names_c, "C")):
        if not nm:
            continue
        X = np.column_stack([tested_cols[n] for n in nm])
        r = pairwise_corr(X)
        r_mats[prefix] = (nm, r)
        cl_map.update(clusters(nm, r, prefix))
    clus = pd.DataFrame({"candidate": list(cl_map), "cluster": list(cl_map.values())})
    # each cluster's representative: its member with the most rows present (then name order)
    cov_tot = extra.set_index("name")[["cov_atp_2013_24", "cov_wta_2013_24"]].sum(axis=1)
    clus["cov"] = clus["candidate"].map(cov_tot)
    clus = clus.sort_values(["cluster", "cov", "candidate"], ascending=[True, False, True], kind="stable")
    clus["cluster_size"] = clus.groupby("cluster")["candidate"].transform("size")
    clus["representative"] = clus.groupby("cluster")["candidate"].transform("first")
    # largest |r| with another candidate
    mx = {}
    for prefix, (nm, r) in r_mats.items():
        rr = np.round(np.abs(np.where(np.isfinite(r), r, 0.0)), 9)   # ties (copies) go to the first in name order
        np.fill_diagonal(rr, 0.0)
        for k, n in enumerate(nm):
            j = int(np.argmax(rr[k])) if len(nm) > 1 else k
            mx[n] = (nm[j] if len(nm) > 1 else "", float(rr[k, j]) if len(nm) > 1 else 0.0)
    clus["nearest_candidate"] = clus["candidate"].map(lambda n: mx[n][0])
    clus["abs_r_nearest_candidate"] = clus["candidate"].map(lambda n: mx[n][1])
    clus = clus.drop(columns="cov").sort_values(["cluster", "candidate"]).reset_index(drop=True)
    clus.to_csv(OUT / "clusters.csv", index=False)

    # ---- assemble the summary
    meta = cands.rename(columns={"name": "candidate"})
    summ = meta.merge(summ, on="candidate", how="right")
    summ = summ.merge(extra.rename(columns={"name": "candidate"}), on="candidate", how="left")
    summ = summ.merge(clus[["candidate", "cluster", "cluster_size", "representative"]], on="candidate", how="left")
    summ["copy_of_input"] = (summ["kind"] != "context") & (summ["r_nearest_input"].abs() >= COPY_R)
    summ["now_in_model"] = (summ["kind"] == "context") & (summ["r_nearest_input"].abs() >= COPY_R)
    summ["near_context_input"] = (summ["kind"] == "context") & (summ["r_nearest_input"].abs() >= NEAR_CONTEXT_R) & \
        ~summ["now_in_model"]
    # the placebo spread of this candidate's own z (pooled over its draws), raw and orthogonal
    if len(plc):
        ps = plc.groupby(["name", "tour", "encoding"])["z_pool"].agg(lambda s: float(np.sqrt(np.mean(s ** 2))))
        ps = ps.unstack("encoding")
        ps.columns = [f"placebo_rms_z_{c}" for c in ps.columns]
        summ = summ.merge(ps.reset_index().rename(columns={"name": "candidate"}), on=["candidate", "tour"],
                          how="left")
        rms_max = summ[[c for c in summ.columns if c.startswith("placebo_rms_z_")]].max(axis=1)
        summ["placebo_rms_max"] = rms_max.groupby(summ["candidate"]).transform("max")   # over tours and encodings
        summ["unstable"] = summ["placebo_rms_max"] >= UNSTABLE_RMS
    else:
        summ["unstable"] = False
    # the market's open-to-close move against the close-lens direction (outcome-free): toward = the line moves the
    # way the effect points before the close (partly learned), against = it moves the other way
    for sfx in ("", "_orth"):
        zm, zp = summ[f"z_move_2018_24{sfx}"], summ[f"z_pool{sfx}"]
        summ[f"move_vs_effect{sfx}"] = np.where(~np.isfinite(zm) | ~np.isfinite(zp), "",
                                                np.where(zm.abs() < 2, "flat",
                                                         np.where(np.sign(zm) == np.sign(zp), "toward", "against")))
    # eligibility for the shortlist and the pre-declared rule
    reasons = []
    for _, r in summ.iterrows():
        why = [k for k in ("base_dependent", "market_internal", "known_null", "now_in_model", "near_context_input",
                           "dropped_from_model", "copy_of_input", "unstable") if bool(r[k])]
        reasons.append(";".join(why))
    summ["not_eligible_because"] = reasons
    summ["eligible"] = summ["not_eligible_because"] == ""
    ctx = summ["kind"] == "context"
    raw_ok = (summ["z_pool"].abs() >= RULE_Z) & (summ["eras_same_sign"] >= RULE_ERAS)
    orth_ok = (summ["z_pool_orth"].abs() >= RULE_Z) & (summ["eras_same_sign_orth"] >= RULE_ERAS) & \
        (np.sign(summ["z_pool_orth"]) == np.sign(summ["z_pool"]))
    summ["passes_rule"] = summ["eligible"] & raw_ok & (ctx | orth_ok)
    summ["rank_raw"] = np.nan
    summ["rank_orth"] = np.nan
    for tour in S.TOURS:
        m = (summ["tour"] == tour) & summ["eligible"] & (summ["eras_same_sign"] >= RULE_ERAS)
        summ.loc[m, "rank_raw"] = summ.loc[m, "z_pool"].abs().rank(ascending=False, method="min")
        m = (summ["tour"] == tour) & summ["eligible"] & ~ctx & (summ["eras_same_sign_orth"] >= RULE_ERAS)
        summ.loc[m, "rank_orth"] = summ.loc[m, "z_pool_orth"].abs().rank(ascending=False, method="min")
    first = ["candidate", "tour", "kind", "group", "family", "subfamily", "fi_block", "feature_id", "catalogue_name",
             "col_a", "col_b", "seen_2025_2026", "near_miss_tier", "priority", "market_internal", "base_dependent",
             "known_null", "now_in_model", "near_context_input", "dropped_from_model", "copy_of_input", "unstable",
             "placebo_rms_max", "eligible", "not_eligible_because", "passes_rule", "rank_raw", "rank_orth",
             "nearest_input", "r_nearest_input", "cluster", "cluster_size", "representative",
             "cov_atp_2013_24", "cov_wta_2013_24", "cov_atp_2025_26", "cov_wta_2025_26", "cov_atp_2013_24_frame",
             "cov_wta_2013_24_frame", "present_2013_24", "min_era_present_n",
             "beta_pool", "z_pool", "eras_same_sign", "eras_abs_z_ge_2", "z_2013-16", "z_2017-19", "z_2020-22",
             "z_2023-24", "z_close_2013_19", "z_close_2020_24", "rep_2020_24", "z_model_2020_24", "absorb_model",
             "z_move_2018_24", "move_vs_effect", "r2_inputs", "p_pool", "q_pool",
             "beta_pool_orth", "z_pool_orth", "eras_same_sign_orth", "eras_abs_z_ge_2_orth", "z_2013-16_orth",
             "z_2017-19_orth", "z_2020-22_orth", "z_2023-24_orth", "z_close_2013_19_orth", "z_close_2020_24_orth",
             "rep_2020_24_orth", "z_model_2020_24_orth", "absorb_model_orth", "z_move_2018_24_orth",
             "move_vs_effect_orth", "r2_inputs_orth", "p_pool_orth", "q_pool_orth"]
    rest = [c for c in summ.columns if c not in first]
    summ = summ[[c for c in first if c in summ.columns] + rest]
    tord = {"both": 0, "atp": 1, "wta": 2}
    summ = summ.sort_values(["candidate", "tour"], key=lambda s: s.map(tord) if s.name == "tour" else s,
                            kind="stable").reset_index(drop=True)
    summ.to_csv(OUT / "summary.csv", index=False)

    # ---- the rule's shortlist: rows passing the pre-declared rule, the best member of each cluster per tour
    sl = summ[summ["passes_rule"]].copy()
    sl["rank_mean"] = np.where(sl["kind"] == "context", sl["rank_raw"], sl[["rank_raw", "rank_orth"]].mean(axis=1))
    sl = sl.sort_values(["tour", "rank_mean", "candidate"], key=lambda s: s.map(tord) if s.name == "tour" else s,
                        kind="stable")
    sl["cluster_members_passing"] = sl.groupby(["tour", "cluster"])["candidate"].transform(lambda s: "; ".join(s))
    sl = sl.drop_duplicates(["tour", "cluster"], keep="first")
    sl_cols = ["tour", "rank_mean", "candidate", "kind", "family", "subfamily", "fi_block", "feature_id",
               "catalogue_name", "seen_2025_2026", "near_miss_tier", "z_pool", "eras_same_sign", "z_2013-16",
               "z_2017-19", "z_2020-22", "z_2023-24", "z_pool_orth", "eras_same_sign_orth", "z_model_2020_24",
               "z_model_2020_24_orth", "z_move_2018_24", "move_vs_effect", "z_move_2018_24_orth", "move_vs_effect_orth",
               "r2_inputs", "nearest_input", "r_nearest_input", "q_pool", "q_pool_orth", "cov_atp_2025_26",
               "cov_wta_2025_26", "cluster", "cluster_members_passing", "rank_raw", "rank_orth"]
    sl[sl_cols].to_csv(OUT / "shortlist_rule.csv", index=False)

    # ---- long table
    long = long.merge(cands[["name", "kind", "group", "family", "seen_2025_2026"]].rename(columns={"name": "candidate"}),
                      on="candidate", how="left")
    lcols = ["candidate", "encoding", "name", "kind", "screen_kind", "group", "family", "seen_2025_2026", "lens", "era",
             "tour",
             "beta", "se", "z", "n", "present", "eras_same_sign", "eras_abs_z_ge_2", "r2_inputs"]
    long[lcols].to_csv(OUT / "long.csv", index=False)
    plc.to_csv(OUT / "placebo.csv", index=False)

    # ---- the family view
    fam = family_view(summ, plc, r_mats)
    fam.to_csv(OUT / "family.csv", index=False)

    # ---- negative controls
    neg = negative_controls(summ, plc)
    neg.to_csv(OUT / "negative_controls.csv", index=False)

    # ---- the post-hoc joint reading of the memo's representatives, and their outcome-free correlations
    if all(n in tested_cols for n in JOINT):
        jt = joint_check(frame, tested_cols, kind_of)
        zs = summ.set_index(["candidate", "tour"])
        jt["z_pool_single"] = [zs.loc[(r.candidate, r.tour), "z_pool"] for r in jt.itertuples()]
        jt["z_pool_orth_single"] = [zs.loc[(r.candidate, r.tour), "z_pool_orth"] for r in jt.itertuples()]
        jt.to_csv(OUT / "joint.csv", index=False)
        rj = pairwise_corr(np.column_stack([tested_cols[n] for n in JOINT]))
        pd.DataFrame(rj, index=JOINT, columns=JOINT).round(3).to_csv(OUT / "joint_corr.csv")

    info = {
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "seconds": round(time.time() - t0, 1),
        "frame_rows_screened": int(len(frame)), "frame_last_date": str(frame["tournament_date"].max().date()),
        "frame_rows_joined_to_store": int((rows_f >= 0).sum()),
        "candidates": int(len(cands)), "by_kind": cands["kind"].value_counts().to_dict(),
        "by_group": cands["group"].value_counts().to_dict(),
        "orth_candidates": int(cands["kind"].isin(["diff", "pair"]).sum()),
        "flags": {k: int(cands[k].sum()) for k in ("market_internal", "base_dependent", "known_null",
                                                    "dropped_from_model")},
        "now_in_model": summ.loc[summ["now_in_model"] & (summ["tour"] == "both"), "candidate"].tolist(),
        "near_context_input": summ.loc[summ["near_context_input"] & (summ["tour"] == "both"), "candidate"].tolist(),
        "unstable": summ.loc[summ["unstable"] & (summ["tour"] == "both"), "candidate"].tolist(),
        "not_identifiable_blanked": [f"{n} ({t})" for n, t in degenerate],
        "blas_threads": {v: os.environ.get(v) for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")},
        "eligible_candidates": int(summ.loc[summ["tour"] == "both", "eligible"].sum()),
        "passing_rule_rows": {t: int(summ.loc[summ["tour"] == t, "passes_rule"].sum()) for t in S.TOURS},
        "copy_of_input": summ.loc[summ["copy_of_input"] & (summ["tour"] == "both"), "candidate"].tolist(),
        "clusters": {p: int(clus.loc[clus["cluster"].str.startswith(p), "cluster"].nunique()) for p in ("D", "C")},
        "design": {"null_sd": NULL_SD, "seed": SEED, "n_placebo": n_placebo, "cluster_r": CLUSTER_R,
                   "copy_r": COPY_R, "look_a_end": str(LOOK_A_END.date()), "inputs_for_orth": len(names48),
                   "dropped": DROPPED},
        "inputs_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in
                          (MENU, REGISTRY, UNIVERSE, STORE, S.FRAME, S.ANALYSIS, S.BET_TIMING,
                           ROOT / "src" / "eda" / "unpriced_leads" / "screen.py", Path(__file__).resolve())},
    }
    (OUT / "run.json").write_text(json.dumps(info, indent=1, default=str), encoding="utf-8")
    return info


def _expected(n: int, thr: float) -> float:
    return float(n * 2 * norm.sf(thr / NULL_SD))


def family_view(summ: pd.DataFrame, plc: pd.DataFrame, r_mats: dict) -> pd.DataFrame:
    """For each family, family x subfamily and feature-interactions block, tour and encoding: counts of |z_pool| >= 2
    and >= 3 against N(0, 1.08^2) and the group's own sign-flip placebos, distinct clusters, Li-Ji M_eff, the most
    consistent columns, and the split-sample and model-lens readings oriented by the 2013-19 sign."""
    r_lookup = {}
    for prefix, (nm, r) in r_mats.items():
        for k, n in enumerate(nm):
            r_lookup[n] = (prefix, k)
    out = []
    specs = [("family", ["family"]), ("subfamily", ["family", "subfamily"]), ("fi_block", ["fi_block"])]
    excl = summ["unstable"] | summ["base_dependent"]     # left out of the counts: untrustworthy z or not clean
    for level, keys in specs:
        s_all = summ.dropna(subset=keys)
        n_ex = s_all[excl.loc[s_all.index]].groupby(keys + ["tour"]).size()
        s = s_all[~excl.loc[s_all.index]]
        for gkey, h in s.groupby(keys + ["tour"], sort=True):
            gk = gkey[:-1]
            tour = gkey[-1]
            members = h["candidate"].tolist()
            n_excluded = int(n_ex.get(gkey, 0))
            # Li-Ji on the members' correlation (within one kind block; context and diff are separate blocks)
            meff = 0.0
            for prefix, (nm, r) in r_mats.items():
                idx = [r_lookup[m][1] for m in members if r_lookup.get(m, ("", -1))[0] == prefix]
                if idx:
                    meff += li_ji_meff(r[np.ix_(idx, idx)])
            for enc, sfx in (("raw", ""), ("orth", "_orth")):
                z = h[f"z_pool{sfx}"]
                ok = np.isfinite(z)
                if ok.sum() == 0:
                    continue
                hh = h[ok]
                pl = plc[(plc["encoding"] == enc) & (plc["tour"] == tour) & plc["name"].isin(hh["candidate"])]
                n = int(ok.sum())
                ez = hh[f"eras_same_sign{sfx}"]
                he = hh[hh["eligible"]]          # the most consistent among the columns without a flag
                cons = he.assign(az=he[f"z_pool{sfx}"].abs()).sort_values(
                    [f"eras_same_sign{sfx}", "az"], ascending=[False, False])
                top = "; ".join(f"{r.candidate} ({r[f'z_pool{sfx}']:+.2f}, {int(r[f'eras_same_sign{sfx}'])}/4)"
                                for _, r in cons.head(3).iterrows())
                o = np.sign(hh[f"z_close_2013_19{sfx}"])
                strong = hh[hh[f"z_pool{sfx}"].abs() >= 2]
                out.append({
                    "level": level, "family": gk[0] if level != "fi_block" else np.nan,
                    "subfamily": gk[1] if level == "subfamily" else np.nan,
                    "fi_block": gk[0] if level == "fi_block" else np.nan, "tour": tour, "encoding": enc,
                    "n_cols": n, "n_excluded_unstable_or_base_dependent": n_excluded,
                    "n_clusters": int(hh["cluster"].nunique()), "m_eff": round(meff, 2),
                    "n_abs_z_ge_2": int((hh[f"z_pool{sfx}"].abs() >= 2).sum()),
                    "exp_ge_2_null": round(_expected(n, 2), 2),
                    "exp_ge_2_placebo": round(float(np.mean(pl["z_pool"].abs() >= 2)) * n, 2) if len(pl) else np.nan,
                    "n_abs_z_ge_3": int((hh[f"z_pool{sfx}"].abs() >= 3).sum()),
                    "exp_ge_3_null": round(_expected(n, 3), 2),
                    "exp_ge_3_placebo": round(float(np.mean(pl["z_pool"].abs() >= 3)) * n, 2) if len(pl) else np.nan,
                    "n_4_eras_same_sign_and_abs_z_ge_2": int(((ez == 4) & (hh[f"z_pool{sfx}"].abs() >= 2)).sum()),
                    "clusters_abs_z_ge_2": int(strong["cluster"].nunique()),
                    "mean_oriented_z_close_2020_24": float(np.nanmean(o * hh[f"z_close_2020_24{sfx}"])),
                    "mean_oriented_z_model_2020_24": float(np.nanmean(o * hh[f"z_model_2020_24{sfx}"])),
                    "mean_oriented_z_move_2018_24": float(np.nanmean(o * hh[f"z_move_2018_24{sfx}"])),
                    "median_r2_inputs": float(np.nanmedian(hh["r2_inputs"])),
                    "seen_2025_2026_share": float(np.mean(hh["seen_2025_2026"] == "yes")),
                    "n_passing_rule": int(hh["passes_rule"].sum()),
                    "most_consistent_eligible": top,
                })
    return pd.DataFrame(out)


def negative_controls(summ: pd.DataFrame, plc: pd.DataFrame) -> pd.DataFrame:
    rows = []
    kn = summ[summ["known_null"]]
    for _, r in kn.iterrows():
        rows.append({"control": "known_null", "candidate": r["candidate"], "tour": r["tour"],
                     "z_pool": r["z_pool"], "eras_same_sign": r["eras_same_sign"], "z_model_2020_24": r["z_model_2020_24"],
                     "z_move_2018_24": r["z_move_2018_24"], "z_pool_orth": r.get("z_pool_orth"),
                     "z_model_2020_24_orth": r.get("z_model_2020_24_orth"), "r2_inputs": r["r2_inputs"]})
    unstable = set(summ.loc[summ["unstable"], "candidate"])
    for (tour, enc), h0 in plc.groupby(["tour", "encoding"]):
        h = h0[~h0["name"].isin(unstable)]
        z = h["z_pool"].to_numpy(float)
        z = z[np.isfinite(z)]
        rows.append({"control": "sign_flip_placebo_without_unstable", "candidate": f"all ({enc})", "tour": tour,
                     "n_draws": int(len(z)), "z_mean": float(z.mean()), "z_sd": float(z.std()),
                     "share_abs_z_ge_2": float(np.mean(np.abs(z) >= 2)), "share_abs_z_ge_3": float(np.mean(np.abs(z) >= 3)),
                     "normal_ref_ge_2": float(2 * norm.sf(2 / NULL_SD)), "normal_ref_ge_3": float(2 * norm.sf(3 / NULL_SD)),
                     "share_4_eras_same_sign": float(np.mean(h["eras_same_sign"] == 4))})
    for (tour, enc), h in plc.groupby(["tour", "encoding"]):
        z = h["z_pool"].to_numpy(float)
        z = z[np.isfinite(z)]
        rows.append({"control": "sign_flip_placebo", "candidate": f"all ({enc})", "tour": tour,
                     "n_draws": int(len(z)), "z_mean": float(z.mean()), "z_sd": float(z.std()),
                     "share_abs_z_ge_2": float(np.mean(np.abs(z) >= 2)), "share_abs_z_ge_3": float(np.mean(np.abs(z) >= 3)),
                     "normal_ref_ge_2": float(2 * norm.sf(2 / NULL_SD)), "normal_ref_ge_3": float(2 * norm.sf(3 / NULL_SD)),
                     "share_4_eras_same_sign": float(np.mean(h["eras_same_sign"] == 4))})
    # by kind of column: sparse indicators and context modifiers may behave differently
    kinds = summ[summ["tour"] == "both"].set_index("candidate")["kind"]
    for (tour, enc), h in plc.groupby(["tour", "encoding"]):
        for kind, hk in h.groupby(h["name"].map(kinds)):
            z = hk["z_pool"].to_numpy(float)
            z = z[np.isfinite(z)]
            rows.append({"control": "sign_flip_placebo_by_kind", "candidate": f"{kind} ({enc})", "tour": tour,
                         "n_draws": int(len(z)), "z_mean": float(z.mean()), "z_sd": float(z.std()),
                         "share_abs_z_ge_2": float(np.mean(np.abs(z) >= 2)),
                         "share_abs_z_ge_3": float(np.mean(np.abs(z) >= 3))})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--placebos", type=int, default=N_PLACEBO)
    ap.add_argument("--limit", type=int, default=None, help="first N candidates only (a smoke test)")
    args = ap.parse_args()
    info = run(n_placebo=args.placebos, limit=args.limit)
    print(json.dumps({k: v for k, v in info.items() if k not in ("inputs_sha256",)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
