"""The screen batch over the hypothesis table (docs/studies/feature_interactions/builders.md, plan.md), with the harness
verifier's fixes (docs/studies/feature_interactions/meta/harness_verification.md, B4-B6, B9, B10, B13, B14).

    --prepare   result-free: builds every hypothesis of the feature modules (src/eda/feature_interactions/features/
                f<NN>_*.py) and the known-null set (p3_*.py) on the panel WITHOUT its result column, checks shapes and
                swap behaviour, measures coverage and novelty (R^2 of x on the 58 inputs, 2014-2021 rows) and writes
                the hypothesis table with a SHA-256 of every column and of every builder file
                (data/studies/feature_interactions/hypotheses/). No result is read.
    --screen    after M1 only: refuses to run unless plan.md's FROZEN_TABLE_SHA256 and FROZEN_MODULES_SHA256 lines match
                the rebuilt table and the files, and every swap test passes; then runs the screen once (base = the
                current best's forecast, gating; base = the price, reported), the levels arm H-S2, the placebos and the
                multiplicity procedures, and the known-null set through the same pipeline; writes results.

Run: ./python.sh src/eda/feature_interactions/screen_batch.py --prepare [--module f01_x,f02_y] | --screen
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel, swap_sides  # noqa: E402

HYP = C.OUT / "hypotheses"
# How each row orients its members (checkpoint 1, section 1.2, read from the module code; F-4): convention (i) members
# multiplied by their declared signs and the row tested "+", or (ii) members summed as they are and the row tested with
# the family's common sign.
MEMBER_MULTIPLIERS = {
    "B2": "+e_ace, +shield; tested +", "B-FLB": "+L*eta, +HP*eta; tested +", "B-CLUTCH": "+I-026; tested +",
    "B-VENUE": "+I-072; tested +", "B-AGE": "+I-070; tested +", "B-INFO": "+I-080, +C-2, +INFO-2; tested +",
    "B11": "+On, +I-075, +I-076; tested +", "B-STATE": "+BOD-C1; tested +",
    "B6": "+I-033, +BOD-L2, +U_rest (each s*eta); tested - (convention ii)",
    "B-REPUTE": "+I-071, +I-083, +I-055; tested - (ii)", "B-MOTIV": "+I-089, +I-090; tested - (ii)",
    "B-LOAD": "-dFat, -dOff; tested + (i)", "B-PREV": "-dPrevX, -contrast; tested + (i)",
    "B10": "-I-059, -I-088, -I-060, -I-074; tested + (i)",
    "B-INJ": "-Rust, -inj*e_pre, -Dec (Dec = -slope, a decaying serve); tested + (i)",
    "B7": "+I-023, +I-031, +I-032, -I-048(E), -I-048(F); tested + (i)",
    "B9a": "-I-024(h*Fat), -I-024(h*age), +I-058, -I-061; tested + (i)",
    "B9b": "-I-063 (-D/kappa, like dFat), +I-065, -I-066; tested + (i)",
    "B-ANCHOR": "-I-037, +I-038; tested + (i)", "B-OVERREACT": "-I-025, +I-085, -I-086, -I-091; tested + (i)",
    "I-053": "single column, tested -",
}
FEATURE_DIR = ROOT / "src" / "eda" / "feature_interactions" / "features"
FAMILY = "f[0-9][0-9]_*.py"
KNOWN_NULL = "p3_*.py"


def modules(pattern: str = FAMILY) -> list:
    """The hypothesis modules (f<NN>_*.py), or with pattern "p3_*.py" the known-null placebo set (outside the family)."""
    out = []
    only = sys.argv[sys.argv.index("--module") + 1].split(",") if "--module" in sys.argv else None
    for path in sorted(FEATURE_DIR.glob(pattern)):
        if only and path.stem not in only:
            continue
        out.append(importlib.import_module(f"src.eda.feature_interactions.features.{path.stem}"))
    return out


def sha_array(a) -> str:
    v = np.ascontiguousarray(np.asarray(a, dtype="float64"))
    v = np.where(np.isnan(v), np.nan, v).astype("<f8")
    return hashlib.sha256(v.tobytes()).hexdigest()


def sym_ok(a: np.ndarray, b: np.ndarray) -> bool:
    ok = np.isfinite(a) & np.isfinite(b)
    return bool(np.allclose(a[ok], b[ok], atol=1e-9) and (np.isfinite(a) == np.isfinite(b)).all())


def antisym_ok(a: np.ndarray, b: np.ndarray) -> bool:
    ok = np.isfinite(a) & np.isfinite(b)
    return bool(np.allclose(a[ok], -b[ok], atol=1e-9) and (np.isfinite(a) == np.isfinite(b)).all())


def evaluate(spec: dict, Q: pd.DataFrame) -> dict:
    """combine() on Q, with x_of_eta evaluated at the panel's eta_model (for the swap test, the hash, diagnostics)."""
    r = dict(spec["combine"](Q))
    if r.get("x_of_eta") is not None:
        r["x"] = r["x_of_eta"](Q["eta_model"].to_numpy(float), np.arange(len(Q)))
    return r


def build_all(P: pd.DataFrame, L: pd.DataFrame, pattern: str = FAMILY) -> tuple[list[dict], dict]:
    """Every hypothesis built on P without its result column: the table's rows, and {hid: (x, Cm, names, spec, new)}
    where `new` holds the hypothesis's own per-player columns (the panel plus `new` is what combine() read)."""
    P = P.drop(columns=[c for c in ("a_won",) if c in P.columns])           # builders never see the result (B10)
    rows, built = [], {}
    disc = P["season"].between(C.DISCOVERY[0], C.DISCOVERY[-1]).to_numpy()
    X58 = P[[c for c in P.columns if c.startswith("in_")]].to_numpy(float)
    for mod in modules(pattern):
        for spec in mod.HYPOTHESES:
            # a Wald block whose members include a fixed player trait has no permutation null (verifier B9): it is
            # screened with the slow-trait widening, covariance x 1.25 (plan.md, decision of 6 Oct 2026)
            new = spec["prepare"](P, L) if spec.get("prepare") else {}
            Q = P.assign(**new) if new else P
            r = evaluate(spec, Q)
            sw = evaluate(spec, swap_sides(Q))
            x = np.asarray(r["x"], float)
            X2 = x.reshape(len(P), -1)
            Xsw = np.asarray(sw["x"], float).reshape(len(P), -1)
            Cm = None if r.get("controls") is None else np.asarray(r["controls"], float).reshape(len(P), -1)
            ok_fn = sym_ok if r.get("x_times_eta") else antisym_ok
            swap_x = all(ok_fn(X2[:, j], Xsw[:, j]) for j in range(X2.shape[1]))
            Em = None
            if r.get("eta_mod_controls") is not None:
                Em = np.asarray(r["eta_mod_controls"], float).reshape(len(P), -1)
                Esw = np.asarray(sw["eta_mod_controls"], float).reshape(len(P), -1)
                swap_x = swap_x and all(sym_ok(Em[:, j], Esw[:, j]) for j in range(Em.shape[1]))
            swap_c = True if Cm is None else all(
                antisym_ok(Cm[:, j], np.asarray(sw["controls"], float).reshape(len(P), -1)[:, j])
                for j in range(Cm.shape[1]))
            r2s = []
            for j in range(X2.shape[1]):
                ok = disc & np.isfinite(X2[:, j])
                if ok.sum() > 100:
                    Z = np.nan_to_num(X58[ok])
                    beta, *_ = np.linalg.lstsq(Z, X2[ok, j], rcond=None)
                    r2s.append(float(1 - np.var(X2[ok, j] - Z @ beta) / np.var(X2[ok, j])))
            r2 = float(np.nanmax(r2s)) if r2s else np.nan
            cov = {}
            for tour in C.TOURS:
                for win, seasons in (("disc", C.DISCOVERY), ("rep", C.REPLICATION)):
                    m = (P["tour"] == tour).to_numpy() & P["season"].isin(seasons).to_numpy()
                    cov[f"cov_{win}_{tour}"] = float(np.isfinite(X2[m]).all(axis=1).mean()) if m.any() else np.nan
            row = {"hid": spec["hid"], "master": spec["master"], "module": mod.__name__.rsplit(".", 1)[-1],
                   "kind": spec["kind"], "sign": spec["sign"], "weight": spec["weight"], "trait": spec["trait"],
                   "trait_cols": json.dumps(spec.get("trait_cols", [])), "deployment": spec["deployment"],
                   "wald": bool(spec.get("wald", False)), "k": int(X2.shape[1]),
                   "x_times_eta": bool(r.get("x_times_eta", False)), "m_set": bool(r.get("m_set", False)),
                   "x_of_eta": r.get("x_of_eta") is not None,
                   "n_eta_mod_controls": 0 if Em is None else int(Em.shape[1]),
                   "controls": json.dumps(r.get("control_names", [])),
                   "swap_x": swap_x, "swap_controls": swap_c, "novelty_r2": r2, **cov,
                   "x_sha256": sha_array(x), "controls_sha256": sha_array(Cm) if Cm is not None else "",
                   "eta_mod_sha256": sha_array(Em) if Em is not None else "",
                   "member_multipliers": MEMBER_MULTIPLIERS.get(
                       spec["hid"], "Wald, two-sided" if spec.get("wald") else f"single column, tested {spec['sign']}")}
            rows.append(row)
            built[spec["hid"]] = (x, Cm, r.get("control_names", []), {**spec, "_r": r}, new)
            C.log(f"{spec['hid']} ({spec['master']}): swap {swap_x}/{swap_c}, R2 {r2:.3f}, coverage "
                  f"{ {k: round(v, 2) for k, v in cov.items()} }")
    return rows, built


@contextlib.contextmanager
def recording_reads():
    """Record every data file under the repository opened for reading through pandas, NumPy, pyarrow or open() while
    the block runs (checkpoint 1, F-5: the inputs manifest)."""
    import builtins
    import pyarrow.parquet as pq
    seen: set[Path] = set()
    saved = (pd.read_parquet, pd.read_csv, np.load, pq.read_table, builtins.open)

    def rec(path):
        try:
            q = Path(path).resolve()
        except TypeError:
            return
        if q.is_file() and ROOT in q.parents and q.suffix != ".py":
            seen.add(q)

    def wrap(fn):
        def w(path, *a, **k):
            rec(path)
            return fn(path, *a, **k)
        return w

    def wrap_open(file, mode="r", *a, **k):
        if isinstance(mode, str) and not any(c in mode for c in "wax+"):
            rec(file)
        return saved[4](file, mode, *a, **k)
    pd.read_parquet, pd.read_csv, np.load, pq.read_table = (wrap(saved[0]), wrap(saved[1]), wrap(saved[2]),
                                                             wrap(saved[3]))
    builtins.open = wrap_open
    try:
        yield seen
    finally:
        pd.read_parquet, pd.read_csv, np.load, pq.read_table, builtins.open = saved


def forecast_files() -> list[Path]:
    """The forecast files the screen's H-S2 and the final test read (F-8): model seeds 0-15 and levels seeds 0-5 where
    they exist, 2014-2026, in this study's folder and the rating race's."""
    out = []
    for folder in (C.LOCAL, C.RACE_LOCAL):
        for arm in ("model", "levels"):
            out += sorted(folder.glob(f"{arm}__*__seed*.npz"))
    return out


def manifest_of(paths) -> dict:
    return {str(p.relative_to(ROOT)).replace("\\", "/"): C.sha256_file(p) for p in sorted(set(paths))}


def manifest_hash(man: dict) -> str:
    return hashlib.sha256(json.dumps(man, sort_keys=True).encode()).hexdigest()


def module_hashes() -> dict:
    """Every Python file the builders and the screen can import: features/*.py (modules and shared helpers) and the
    study's own modules."""
    return {f"features/{p.name}": C.sha256_file(p) for p in sorted(FEATURE_DIR.glob("*.py"))} | \
           {p.name: C.sha256_file(p) for p in sorted((ROOT / "src" / "eda" / "feature_interactions").glob("*.py"))}


def modules_hash() -> str:
    return hashlib.sha256(json.dumps(module_hashes(), sort_keys=True).encode()).hexdigest()


TABLE_COLS = ["hid", "master", "kind", "sign", "weight", "trait", "trait_cols", "deployment", "wald", "k", "x_times_eta",
              "m_set", "x_of_eta", "n_eta_mod_controls", "controls", "x_sha256", "controls_sha256", "eta_mod_sha256",
              "member_multipliers"]


def table_hash(table: pd.DataFrame) -> str:
    return hashlib.sha256(table[TABLE_COLS].to_csv(index=False).encode()).hexdigest()


def prepare() -> int:
    warnings.simplefilter("ignore")
    with recording_reads() as seen:
        P = panel(max_season=C.REPLICATION[-1])
        L = long_table()
        rows, built = build_all(P, L)
        rows_p3, _ = build_all(P, L, pattern=KNOWN_NULL)
        S.load(with_model=True)
    T = pd.DataFrame(rows)
    T3 = pd.DataFrame(rows_p3)
    inputs = manifest_of(list(seen) + forecast_files())
    bad = T[~(T["swap_x"] & T["swap_controls"])]
    if len(bad):
        C.log(f"SWAP FAILURES: {bad['hid'].tolist()}")
    HYP.mkdir(parents=True, exist_ok=True)
    if "--module" in sys.argv:                 # an analyst's own check: a partial table, never the frozen one
        name = "partial_" + sys.argv[sys.argv.index("--module") + 1].replace(",", "+") + ".csv"
        T.to_csv(HYP / name, index=False)
        C.log(f"partial table written: {name}")
        return 0
    T.to_csv(HYP / "hypothesis_table.csv", index=False)
    if len(T3):
        T3.to_csv(HYP / "known_null_table.csv", index=False)
    C.write_json(HYP / "prepare.json", {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                                         "table_sha256": table_hash(T), "modules_sha256": modules_hash(),
                                         "inputs_sha256": manifest_hash(inputs), "inputs": inputs,
                                         "module_files": module_hashes(), "hypotheses": int(len(T)),
                                         "known_nulls": int(len(T3)), "swap_failures": bad["hid"].tolist()})
    C.log(f"{len(T)} hypotheses (+{len(T3)} known nulls); table {table_hash(T)[:16]}...; modules "
          f"{modules_hash()[:16]}...; inputs {manifest_hash(inputs)[:16]}... ({len(inputs)} files); swap failures {len(bad)}")
    return 0


def frozen(key: str) -> str | None:
    for line in (C.DOCS / "plan.md").read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip().strip("`")
    return None


def _trait_permuter(P: pd.DataFrame, new: dict, spec: dict, pos: np.ndarray, e: np.ndarray):
    """rng -> (x, controls) with each trait permuted across the players who have a value, within tour (each player
    keeps one permuted value; missing values stay with their players, so the missingness pattern is kept: B6), rebuilt
    through combine() (B14: x_of_eta and x_times_eta are applied with the base's eta)."""
    cols = {c for t in spec["trait_cols"] for c in (f"{t}_a", f"{t}_b")}
    Q = P.assign(**new) if new else P
    pa, pb = Q["player_a_id"].astype(str).to_numpy(), Q["player_b_id"].astype(str).to_numpy()
    tour = Q["tour"].astype(str).to_numpy()

    # one value per player (the first seen), and each match's players as positions in that table
    tables = {}
    for t in spec["trait_cols"]:
        va, vb = Q[f"{t}_a"].to_numpy(), Q[f"{t}_b"].to_numpy()
        table = pd.DataFrame({"p": np.r_[pa, pb], "t": np.r_[tour, tour], "v": np.r_[va, vb]}).drop_duplicates("p")
        index = pd.Index(table["p"].to_numpy())
        tables[t] = (table["v"].to_numpy(), table["t"].to_numpy(), pd.notna(table["v"]).to_numpy(),
                     index.get_indexer(pa), index.get_indexer(pb))
    original = {c: Q[c].to_numpy().copy() for c in cols}

    def permute(rng):
        # the trait columns are permuted in place and restored afterwards (no copy of the panel: verifier B13)
        try:
            for t, (v, tt, has, ia, ib) in tables.items():
                w = v.copy()
                for tour_ in np.unique(tt):
                    ix = np.flatnonzero((tt == tour_) & has)        # players with a value, within tour (B6)
                    w[ix] = v[ix[rng.permutation(len(ix))]]
                Q[f"{t}_a"] = w[ia]
                Q[f"{t}_b"] = w[ib]
            r = spec["combine"](Q)
        finally:
            for c, val in original.items():
                Q[c] = val
        if r.get("x_of_eta") is not None:
            xp = np.asarray(r["x_of_eta"](e, pos), float)
        else:
            xp = np.asarray(r["x"], float)[pos]
            if r.get("x_times_eta"):
                xp = xp * e
        Cp = None if r.get("controls") is None else np.asarray(r["controls"], float).reshape(len(Q), -1)[pos]
        return xp, Cp
    return permute


def screen_one(F: pd.DataFrame, P: pd.DataFrame, pos: np.ndarray, eta: dict, hid: str, x, Cm, names, spec, new,
               base: str, n_p1: int, placebo: bool = False) -> dict:
    """One hypothesis (or known null) against one base, through the whole pipeline: the per-base x (x_of_eta,
    x_times_eta), its controls (eta-modulator controls, the M-set, miss x eta), then the screen (B5)."""
    r = spec["_r"]
    e = eta[base]
    tour_atp = (F["tour"] == "atp").to_numpy()
    xb = np.asarray(x, float)[pos].reshape(len(F), -1)
    if r.get("x_of_eta") is not None:
        xb = np.asarray(r["x_of_eta"](e, pos), float).reshape(len(F), -1)
    if r.get("x_times_eta"):
        xb = xb * e[:, None]
    # the batch's own eta terms: eta-modulator controls and the M-set (they do not depend on the trait)
    batch_terms, nm_batch = [], []
    if r.get("eta_mod_controls") is not None:
        Em = np.asarray(r["eta_mod_controls"], float).reshape(len(P), -1)[pos]
        batch_terms.append(Em * e[:, None])
        nm_batch += [f"mod{j} x eta" for j in range(Em.shape[1])]
    if r.get("m_set"):
        batch_terms.append(np.column_stack([np.where(tour_atp, e * np.abs(e), 0.0),
                                            np.where(~tour_atp, e * np.abs(e), 0.0)]))
        nm_batch += ["eta|eta| atp", "eta|eta| wta"]

    def assemble(x_rows: np.ndarray, builder_controls: np.ndarray | None):
        """Controls = the builder's + the batch's eta terms + miss x eta for this x (recomputed for a permuted x)."""
        parts = ([builder_controls] if builder_controls is not None else []) + list(batch_terms)
        names_ = list(names) + nm_batch
        miss = ~np.isfinite(np.asarray(x_rows, float).reshape(len(F), -1)).all(axis=1)
        if miss.any() and not miss.all():
            parts.append(miss.astype(float)[:, None] * e[:, None])
            names_ += ["miss x eta"]
        return (np.column_stack(parts) if parts else None), names_

    Cb, nm = assemble(xb, np.asarray(Cm)[pos] if Cm is not None else None)
    if spec.get("wald"):
        out = S.run_wald(F, hid, xb, Cb, base=base, n_p1=n_p1, weight=spec["weight"], trait=spec["trait"])
    else:
        h = S.Hypothesis(hid, xb[:, 0], Cb, nm, spec["sign"], spec["weight"], spec["trait"], None,
                         spec.get("family", ""), spec["kind"])
        if spec.get("trait_cols"):                 # fixed: folded into p_joint; slow (B7, B9a): a diagnostic only
            perm = _trait_permuter(P, new, spec, pos, e)

            def permute(rng, perm=perm):
                xp, Cp = perm(rng)
                return xp, assemble(xp, Cp)[0]
            h.permute = permute
        out = S.run(F, h, base=base, n_p1=n_p1, n_p2=1000)
    out.update({"master": spec["master"], "kind": spec["kind"], "trait": spec["trait"], "placebo": placebo,
                "controls": json.dumps(nm)})
    return out


def screen() -> int:
    warnings.simplefilter("ignore")
    want_t, want_m = frozen("FROZEN_TABLE_SHA256"), frozen("FROZEN_MODULES_SHA256")
    if not want_t or not want_m:
        raise SystemExit("plan.md has no FROZEN_TABLE_SHA256 / FROZEN_MODULES_SHA256 line: the table is not frozen (M1)")
    if modules_hash() != want_m:
        raise SystemExit(f"the builder files changed since the freeze: {modules_hash()} != {want_m}")
    want_i = frozen("FROZEN_INPUTS_SHA256")
    frozen_inputs = json.loads((HYP / "prepare.json").read_text(encoding="utf-8"))["inputs"]
    if not want_i or manifest_hash(frozen_inputs) != want_i:
        raise SystemExit("plan.md's FROZEN_INPUTS_SHA256 is missing or does not match prepare.json's inputs")
    now = {k: C.sha256_file(ROOT / k) for k in frozen_inputs}
    changed = [k for k in frozen_inputs if now[k] != frozen_inputs[k]]
    if changed:
        raise SystemExit(f"input files changed since the freeze: {changed[:10]} ({len(changed)} in all)")
    P = panel(max_season=C.REPLICATION[-1])
    L = long_table()
    rows, built = build_all(P, L)
    T = pd.DataFrame(rows)
    if table_hash(T) != want_t:
        raise SystemExit(f"the rebuilt table's hash {table_hash(T)} differs from the frozen {want_t}")
    if (~(T["swap_x"] & T["swap_controls"])).any():
        raise SystemExit(f"swap failures: {T.loc[~(T['swap_x'] & T['swap_controls']), 'hid'].tolist()}")
    F = S.load(with_model=True)
    pos = pd.Series(np.arange(len(P)), index=P["match_id"].astype(str)).reindex(F["match_id"]).to_numpy()
    if np.isnan(pos).any():
        raise RuntimeError("screen rows missing from the panel")
    pos = pos.astype(int)
    Pn = P.drop(columns=["a_won"])
    eta = {b: F[f"z_{b}"].to_numpy(float) for b in ("model", "market")}
    out = []
    for hid, (x, Cm, names, spec, new) in built.items():
        for base in ("model", "market"):
            r = screen_one(F, Pn, pos, eta, hid, x, Cm, names, spec, new, base, n_p1=200 if base == "model" else 0)
            out.append(r)
            C.log(f"{hid} vs {base}: z1 {r.get('z1_adj', np.nan):+.2f} z2 {r.get('z2_adj', np.nan):+.2f} joint "
                  f"p {r['p_joint']:.4f}")
    out.append(s2_row())
    R = pd.DataFrame(out)
    M = R[R["base"] == "model"].copy()
    p_eff = np.where(M["filter_pass"] & M["replicates"], M["p_joint"], 1.0)
    M["p_holm"] = S.weighted_holm(p_eff, M["weight"].to_numpy(float))
    M["q_bh"] = S.weighted_bh(p_eff, M["weight"].to_numpy(float))
    M["claim"] = M["p_holm"] < 0.05
    M["bundle_eligible"] = M["q_bh"] < 0.10
    R = R.merge(M[["hid", "p_holm", "q_bh", "claim", "bundle_eligible"]], on="hid", how="left")
    R.to_csv(HYP / "screen_results.csv", index=False)
    # P3: the known-null set through the same pipeline, outside the family; an alarm if more than one would pass the
    # family's Bonferroni line
    _, built_p3 = build_all(P, L, pattern=KNOWN_NULL)
    K = pd.DataFrame([screen_one(F, Pn, pos, eta, hid, x, Cm, names, spec, new, "model", n_p1=200, placebo=True)
                      for hid, (x, Cm, names, spec, new) in built_p3.items()])
    K["p_eff"] = np.where(K["filter_pass"] & K["replicates"], K["p_joint"], 1.0)
    K["passes_family_bonferroni"] = K["p_eff"] < 0.05 / max(len(M), 1)
    K.to_csv(HYP / "known_null_results.csv", index=False)
    n_pass = int(K["passes_family_bonferroni"].sum())
    C.log(f"P3 known nulls passing: {n_pass} of {len(K)}" + ("  ** ALARM: the screen may be miscalibrated **"
                                                             if n_pass > 1 else ""))
    C.log(f"claims: {M.loc[M['claim'], 'hid'].tolist()}; bundle-eligible: {M.loc[M['bundle_eligible'], 'hid'].tolist()}")
    descriptive(F, Pn, pos, eta, built).to_csv(HYP / "descriptive_results.csv", index=False)
    return 0


def descriptive(F, Pn, pos, eta, built) -> pd.DataFrame:
    """The batch's frozen descriptive outputs (checkpoint 1, F-6), never gating and outside the family: every module's
    SENSITIVITIES (screened with their hypothesis's controls; SENSITIVITY_OF names it, else the name's first word),
    and the sharp-anchor diagnostic C-1 (Pinnacle's de-vigged log-odds minus the average's, beyond eta; and eta's gain
    over the calibrated Pinnacle and over the calibrated average on the matches with both)."""
    D = []
    for mod in modules():
        of = getattr(mod, "SENSITIVITY_OF", {})
        for name, fn in getattr(mod, "SENSITIVITIES", {}).items():
            hid = of.get(name, name.split()[0])
            x0, Cm, names, spec, new = built[hid]
            Q = Pn.assign(**new) if new else Pn
            xs = np.asarray(fn(Q), float)
            spec_d = {**spec, "trait_cols": [], "wald": False, "sign": "two",
                      "_r": {**spec["_r"], "x_of_eta": None, "x_times_eta": False}}
            for base in ("model", "market"):
                r = screen_one(F, Pn, pos, eta, f"desc: {name}", xs, Cm, names, spec_d, new, base, n_p1=0,
                               placebo=True)
                r["descriptive_of"] = hid
                D.append(r)
    # C-1: the sharp anchor
    ps = Pn["p_ps_a"].to_numpy(float)
    x_ps = C.lg(ps) - Pn["in_odds_logit"].to_numpy(float)
    x_ps[~np.isfinite(ps)] = np.nan
    spec_ps = {"hid": "C-1", "master": "C-1", "kind": "M", "sign": "two", "weight": 1.0, "trait": "none",
               "deployment": "none", "_r": {}}
    for base in ("model", "market"):
        r = screen_one(F, Pn, pos, eta, "desc: C-1 Pinnacle minus average", x_ps, None, [], spec_ps, {}, base, n_p1=0,
                       placebo=True)
        r["descriptive_of"] = "C-1"
        D.append(r)
    D.extend(sharp_anchor_gains(F, x_ps[pos] + F["z_market"].to_numpy(float)))
    return pd.DataFrame(D)


def sharp_anchor_gains(F: pd.DataFrame, z_ps: np.ndarray) -> list[dict]:
    """eta's gain over the calibrated Pinnacle and over the calibrated average close, on the matches with both
    (descriptive; a slope per tour, leave-one-season-out in 2014-2021 and fitted on 2014-2021 for 2022-2024)."""
    from scipy.special import expit
    y = F["a_won"].to_numpy(float)
    season, tour = F["season"].to_numpy(), F["tour"].to_numpy()
    ok = np.isfinite(z_ps)
    cols = {"model": F["z_model"].to_numpy(float), "average": F["z_market"].to_numpy(float), "pinnacle": z_ps}
    cal = {k: np.full(len(F), np.nan) for k in cols}
    for k, z in cols.items():
        for t in C.TOURS:
            for s_ in C.DISCOVERY + C.REPLICATION:
                fit_rows = ok & (tour == t) & (np.isin(season, C.DISCOVERY) & (season != s_) if s_ in C.DISCOVERY
                                              else np.isin(season, C.DISCOVERY))
                rows = ok & (tour == t) & (season == s_)
                if rows.any() and fit_rows.sum() > 500:
                    b, _ = S.T.fit_logistic(z[fit_rows][:, None], y[fit_rows])
                    cal[k][rows] = expit(b[0] * z[rows])
    out = []
    for window, seasons in (("discovery", C.DISCOVERY), ("replication", C.REPLICATION)):
        k = ok & np.isin(season, seasons) & np.isfinite(cal["model"]) & np.isfinite(cal["pinnacle"])
        for ref in ("average", "pinnacle"):
            c = S.T.compare(S.T.ll(cal[ref][k], y[k]), S.T.ll(cal["model"][k], y[k]), F.loc[k, "tournament_date"].to_numpy())
            out.append({"hid": f"desc: C-1 eta vs calibrated {ref}", "base": "model", "window": window, "matches": c["n"],
                        "gain": c["gain"], "lo": c["lo"], "hi": c["hi"], "descriptive_of": "C-1", "placebo": True,
                        "note": "mLL, positive = the current best's forecast has the lower log loss"})
    return out


def s2_row() -> dict:
    """H-S2 (plan.md), the levels arm, as one member of the family: the disjoint-seed encompassing t of the arm's
    deviation (levels seeds 3-5 minus model seeds 3-5) beyond the base (model seeds 0-2), on 2016-2021 (z1) and
    2022-2024 (z2), joined like every hypothesis; one-sided, weight 1."""
    from src.eda.feature_interactions import tabpfn_tests as TT
    seasons = range(2016, 2025)
    f = TT.frame(seasons)
    eta_b = C.lg(f["match_id"].map(TT.forecasts("model", (0, 1, 2), seasons)).to_numpy(float))
    dev = (C.lg(f["match_id"].map(TT.forecasts("levels", (3, 4, 5), seasons)).to_numpy(float))
           - C.lg(f["match_id"].map(TT.forecasts("model", (3, 4, 5), seasons)).to_numpy(float)))
    w1 = f["season"].between(2016, 2021).to_numpy()
    w2 = f["season"].between(2022, 2024).to_numpy()
    r1 = TT.encompassing(f[w1].reset_index(drop=True), eta_b[w1], dev[w1])
    r2 = TT.encompassing(f[w2].reset_index(drop=True), eta_b[w2], dev[w2])
    widen = np.sqrt(1.25)                              # the slow-trait widening (checkpoint 1, R-7)
    r1["t"], r2["t"] = r1["t"] / widen, r2["t"] / widen
    zj = S.joint_z(r1["t"], r2["t"], r1["n"], r2["n"])
    p_lev = TT.forecasts("levels", range(6), seasons)
    p_mod = TT.forecasts("model", range(6), seasons)
    pa, pb = f["match_id"].map(p_mod).to_numpy(float), f["match_id"].map(p_lev).to_numpy(float)
    g = TT.paired_gain(f, TT.calibrated(f, pa), TT.calibrated(f, pb), f["season"].between(2020, 2024).to_numpy())
    return {"hid": "H-S2", "master": "S2", "kind": "S", "base": "model", "sign": "+", "weight": 1.0, "trait": "slow",
            "widen": float(widen),
            "z1_adj": r1["t"], "z2_adj": r2["t"], "n1": r1["n"], "n2": r2["n"], "z_joint": zj,
            "p_joint": S.p_value(zj, "+"), "filter_pass": bool(r1["t"] > 1.0), "replicates": bool(r2["t"] > 0.67),
            "b1": r1["b"], "b2": r2["b"], "gain_rep_both": g["gain"], "lo_rep_both": g["lo"], "hi_rep_both": g["hi"],
            "note": "TabPFN levels arm; encompassing t (disjoint seeds); effect size: paired gain 2020-2024, 6 seeds, "
                    "walk-forward slopes"}


if __name__ == "__main__":
    if "--prepare" in sys.argv:
        sys.exit(prepare())
    if "--screen" in sys.argv:
        sys.exit(screen())
    raise SystemExit("--prepare or --screen")
