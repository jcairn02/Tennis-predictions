"""The feature store: every candidate feature that already has a builder, materialised for the best model's population
(main-tour singles with closing odds, 2013-2026, the frozen pre-rebuild model frame: 63,737 matches), one row per match,
keyed by match_id. It is the menu for a future feature-selection process; it selects nothing.

Groups (column prefixes; the catalogue docs/studies/feature_universe/README.md describes the features):
    m__     the 58 inputs of the current best model (model_frame.parquet)
    alt__   inputs the 6 Oct decisions replaced, and alternatives: the 70/30 Elo blend, surface_first, surface-only Elo,
            the pooled IOS (offence, defence, products), the surface deviations and net shift, TTT decided and offset
    pp__    each player's own pre-match values from the player panel (A and B as pairs), categoricals coded
    mk__    market fields beyond the average close (Pinnacle, maximum, Bet365 against the average; overround;
            dispersion between the best and the average prices)
    rt__    other rating systems run match by match under the time rule (rating_systems stage A, every probe clean):
            Glicko-2 (mean, deviation, volatility), TrueSkill and the correlated-surface Glicko (mean, deviation) per
            player, and their forecasts' log-odds with Glicko-1 and correlated-surface TrueSkill. Weekly rating periods
            and TrueSkill Through Time are left out (dominated; leaking)
    ad__    the opponent-adjusted profiles the model does not use (UFC-ideas stage B): adjperf / adjdef of 15 statistics,
            A - B, decayed and over 52 weeks (the career forms are left out: dominated)
    sl__    serve speed (shot-level stage 3): first and second serve over the career, decayed and 52 weeks, and the first
            serve's decayed-minus-52-week change, per player, NaN where the player has no real speed data (the source's
            values are prior-filled; its |has flags decide)
    fi__    the feature-interactions study's 33 screened members: fi__<hid>__x (the screen column; __s for a price-slope
            member's symmetric modulator; __x<j> for a Wald block's j-th column), fi__<hid>__<col> (its TabPFN
            deployment columns) and fi__<hid>__m_<member> (each block member as its builder returns it)
    fp__    the study's intermediates from each module's prepare(): per player fp__<module>__<name>_a/_b, and match-level
            values (venue pace, the indoor flag of both tours, days to the next Slam) whose swap behaviour is checked by
            re-running prepare() on the swapped panel; plus B-INJ's matches since the return and the break's length
    lv__    the 17 level sums of the levels arm (A + B)
    kn__    the six known-null placebos
    ds__    pre-declared descriptive columns (each module's SENSITIVITIES)
    ctx__   match context: tour, surface, level, indoor, best of, round, draw size, week of the year, month
Kinds: diff (negated when A and B swap), pair (exchanged with its partner), context (unchanged). Swap behaviour is checked
for every builder column. Reads no result: the panel is used without its result column. Builders that depend on the
base model's forecast (x_of_eta) are stored at the model's 2014-2024 forecast only and flagged.

Registry hygiene (hygiene()): the builders share intermediates, so one series can sit under several names. Each column
gets `canonical` (the column it equals exactly, or exactly negated with dup_sign -1; empty for the representative, chosen
by group priority m, alt, pp, mk, lv, ctx, fi, fp, ds, kn and then registry order), `near_dup_of` / `near_dup_r` (a
representative it correlates with at |r| >= 0.999 on their common rows), `degenerate` (constant, or constant within each
tour, other than m__tour itself) and `menu` (1 = a distinct, non-degenerate feature: the default candidate set). A "pair"
whose two sides are equal (to 1e-9) is re-registered as context, one whose sides are negatives as diff (its _b member then
duplicates its _a member). A near copy must also add almost no rows its representative lacks (NEAR_DUP_EXTRA).
Flags: "base-dependent: ..." (the column moves when the base forecast moves) and "market_internal" (mk__ and B-ANCHOR),
joined by "; " when both apply.

Writes data/studies/feature_universe/store.parquet, store_registry.csv and store_build.json.
Run: ./python.sh src/eda/feature_universe/build_store.py
     ./python.sh src/eda/feature_universe/build_store.py --registry-only   (re-annotates the registry from the store)
"""
from __future__ import annotations

import importlib
import json
import re
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen_batch as B  # noqa: E402
from src.eda.feature_interactions.features import levels as LV  # noqa: E402
from src.eda.feature_interactions.history import at_model, long_table  # noqa: E402
from src.eda.feature_interactions.panel import OLD, SOURCES, STATS8, panel, swap_sides  # noqa: E402
from src.eda.surface_rating_race import ttt_offset as TO  # noqa: E402

OUT = ROOT / "data" / "studies" / "feature_universe"
EPS = 1e-6
T0 = time.time()
KEYS = ["match_id", "tour", "season", "tournament_date", "debut_season"]
PRIORITY = ["m", "alt", "pp", "rt", "ad", "sl", "mk", "lv", "ctx", "fi", "fp", "ds", "kn"]
STUDIES = ROOT / "data" / "studies"
RATINGS = STUDIES / "rating_systems" / "stageA_ratings.parquet"
ADJ = STUDIES / "ufc_ideas" / "stageB_adj_features.parquet"
PROFILE = STUDIES / "ufc_ideas" / "stageD_profile_features.parquet"
SIDES = STUDIES / "shot_level" / "stage3_sides.parquet"
RATING_PAIRS = {"glicko2m": ("mu", "u", "vol"), "trueskill": ("mu", "u"), "glicko_cs": ("mu", "u")}
RATING_PROBS = ("p_glicko2m", "p_glicko1m", "p_trueskill", "p_glicko_cs", "p_trueskill_cs")
SPEED = ("spd1|off|career", "spd1|off|dec2", "spd1|off|w52", "spd2|off|career", "spd2|off|dec2", "spd2|off|w52",
         "spd1_change|off|dec2-w52")
NEAR_DUP = 0.999
NEAR_DUP_EXTRA = 0.005             # a near copy may exist on at most 0.5% of rows where its representative is missing
TOUR_COLUMN = "m__tour"
MARKET_INTERNAL_HIDS = {"B-ANCHOR"}  # the study's [A]-type block: artefacts of the average close (book dispersion, skew)
BASE_DEPENDENT = "base-dependent: reads the current best's 2014-2024 forecast; recompute with a new model's own"
HYGIENE =["canonical", "dup_sign", "near_dup_of", "near_dup_r", "degenerate", "menu"]


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def panel26() -> pd.DataFrame:
    """The player panel for 2013-2026, with each player's two-week form, 14-day sets and age from the 2026 rebuild
    (perplayer_2026.py), and without the result column."""
    P = panel(max_season=2026).drop(columns=["a_won"])
    for name in ("perplayer_form_2013_2026.parquet", "perplayer_load_2013_2026.parquet"):
        t = pd.read_parquet(OUT / name).set_index("match_id").reindex(P["match_id"].astype(str))
        for c in t.columns:
            P[c.replace("age_", "age_pl_") if c.startswith("age_") else c] = t[c].to_numpy(dtype=float)
    return P


class Store:
    def __init__(self, ids: np.ndarray):
        self.cols: dict[str, np.ndarray] = {}
        self.meta: list[dict] = []
        self.n = len(ids)

    def add(self, name: str, values, kind: str, group: str, source: str, desc: str, partner: str | None = None,
            hid: str = "", flag: str = "") -> None:
        v = np.asarray(values, dtype=float).reshape(-1)
        if len(v) != self.n:
            raise ValueError(f"{name}: {len(v)} rows")
        if name in self.cols:
            if np.array_equal(self.cols[name], v, equal_nan=True):
                return
            raise ValueError(f"{name}: two different columns under one name")
        self.cols[name] = v
        self.meta.append({"column": name, "group": group, "kind": kind, "partner": partner or "", "hid": hid,
                          "source": source, "desc": desc, "flag": flag})

    def add_pair(self, stem: str, a, b, group: str, source: str, desc: str, hid: str = "", flag: str = "") -> None:
        self.add(f"{stem}_a", a, "pair", group, source, desc, f"{stem}_b", hid, flag)
        self.add(f"{stem}_b", b, "pair", group, source, desc, f"{stem}_a", hid, flag)


def lg(p) -> np.ndarray:
    return logit(np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS))


def devig_logit(oa, ob) -> np.ndarray:
    qa, qb = 1.0 / np.asarray(oa, float), 1.0 / np.asarray(ob, float)
    return lg(qa / (qa + qb))


def fi_flag(base_dependent: bool, hid: str) -> str:
    return "; ".join(f for f in (BASE_DEPENDENT if base_dependent else "",
                                 "market_internal" if hid in MARKET_INTERNAL_HIDS else "") if f)


def _read(path: Path, cols: list[str], ids: np.ndarray) -> pd.DataFrame:
    """Columns of a study table (never a result column) on the store's rows, by match_id."""
    if set(cols) & {"a_won", "won", "y"}:
        raise ValueError("a result column was requested")
    t = pd.read_parquet(path, columns=["match_id"] + cols)
    t["match_id"] = t["match_id"].astype(str)
    if t["match_id"].duplicated().any():
        raise ValueError(f"{path.name}: duplicated match ids")
    return t.set_index("match_id").reindex(ids)


def external(S: Store, P: pd.DataFrame, ids: np.ndarray) -> dict:
    """rt__, ad__ and sl__ from earlier studies' tables, after checking that their side A is the model frame's."""
    checks = {}
    z = P["in_odds_logit"].to_numpy(float)
    # rating systems: side A checked by the rated-match counts, which equal the panel's Elo N exactly when aligned
    cols = ["n_a", "n_b"] + [f"{s}_{k}_{x}" for s, ks in RATING_PAIRS.items() for k in ks for x in "ab"] + list(RATING_PROBS)
    R = _read(RATINGS, cols, ids)
    na, nb = R["n_a"].to_numpy(float), R["n_b"].to_numpy(float)
    Na, Nb = P["elo_N_a"].to_numpy(float), P["elo_N_b"].to_numpy(float)
    ok = np.isfinite(na) & np.isfinite(Na)
    checks["ratings_side_a"] = float(((na == Na) & (nb == Nb))[ok].mean())
    if checks["ratings_side_a"] < 0.999:
        raise ValueError(f"rating systems: side A matches on {checks['ratings_side_a']:.4f} of rows")
    words = {"mu": "mean", "u": "deviation (uncertainty)", "vol": "volatility"}
    for s, ks in RATING_PAIRS.items():
        for k in ks:
            S.add_pair(f"rt__{s}_{k}", R[f"{s}_{k}_a"], R[f"{s}_{k}_b"], "rt", "rating_systems/stageA_ratings",
                       f"{s} {words[k]} before the match (match by match, time rule)")
    for p in RATING_PROBS:
        S.add(f"rt__{p[2:]}_logit", lg(R[p]), "diff", "rt", "rating_systems/stageA_ratings",
              f"{p[2:]}'s forecast that A wins, log-odds (match by match, time rule)")
    # opponent-adjusted profiles: stage D's market column fixes the side, and stage D's decayed columns equal stage B's
    D = _read(PROFILE, ["p_mkt", "adjperf_tpw|decayed", "adjperf_ace|decayed"], ids)
    lp = lg(D["p_mkt"])
    both = np.isfinite(lp) & np.isfinite(z)
    checks["profile_side_a_max_gap"] = float(np.max(np.abs(lp[both] - z[both])))
    names = [c for c in pq.read_schema(ADJ).names if c.endswith("|decayed") or c.endswith("|52 weeks")]
    A = _read(ADJ, names, ids)
    checks["adj_equals_profile"] = bool(all(np.allclose(A[c].to_numpy(float), D[c].to_numpy(float), equal_nan=True)
                                            for c in ("adjperf_tpw|decayed", "adjperf_ace|decayed")))
    if checks["profile_side_a_max_gap"] > 1e-9 or not checks["adj_equals_profile"]:
        raise ValueError(f"opponent-adjusted profiles: side check failed {checks}")
    for c in names:
        stat, window = c.split("|")
        tag = "decayed" if window == "decayed" else "52w"
        S.add(f"ad__{stat}_{tag}", A[c], "diff", "ad", "ufc_ideas/stageB_adj_features",
              f"{stat.replace('_', ' ', 1)} ({window}), A - B")
    # serve speed: stage 3 sides, value only where the source has real data for the player
    cols = [f"{x}|{s}" for s in SPEED for x in "AB"] + [f"{x}|{s}|has" for s in SPEED for x in "AB"] + ["p_mkt"]
    T = _read(SIDES, cols, ids)
    lp = lg(T["p_mkt"])
    both = np.isfinite(lp) & np.isfinite(z)
    checks["sides_side_a_max_gap"] = float(np.max(np.abs(lp[both] - z[both])))
    if checks["sides_side_a_max_gap"] > 1e-9:
        raise ValueError(f"serve speed: side check failed {checks}")
    for s in SPEED:
        stat, _, window = s.split("|")
        v = {x: np.where(T[f"{x}|{s}|has"].to_numpy(float) > 0, T[f"{x}|{s}"].to_numpy(float), np.nan) for x in "AB"}
        S.add_pair(f"sl__{stat}_{window.replace('-', '_')}", v["A"], v["B"], "sl", "shot_level/stage3_sides",
                   f"serve speed {stat} ({window}); NaN without real speed data")
    return checks


def return_history(S: Store, P: pd.DataFrame, L: pd.DataFrame) -> None:
    """B-INJ's raw blocks the screen combined: played matches since the latest return from a break, and its length."""
    from src.eda.feature_interactions.features import f20_fatigue as F20
    from src.eda.feature_interactions.features import f26_impairment as F26
    H = F20.history(P, L)
    F26.layoffs(H)
    for k, desc in (("ret_n", "played matches since the latest return from a break of 6+ weeks beyond the field's norm "
                              "(0 at the return; NaN if none)"),
                    ("ret_gap", "days of that break (the return's gap since the previous played match)")):
        a, b = F20.at_model(P, H, H[k].to_numpy(float))
        S.add_pair(f"fp__f26_impairment__{k}", a, b, "fp", "f26_impairment.layoffs", desc, "B-INJ")


def _key(v: np.ndarray) -> bytes:
    """The exact series, NaN and +-inf normalised, as bytes (equal bytes = equal columns)."""
    w = np.where(np.isfinite(v), v, np.nan) + 0.0                     # + 0.0 turns -0.0 into 0.0
    return np.nan_to_num(w, nan=-9.87654321e300).tobytes()


def near_duplicates(X: np.ndarray, min_rows: int = 1000) -> tuple[np.ndarray, np.ndarray]:
    """Pairwise-complete Pearson correlations of the columns of X (NaN = missing), by five matrix products, and the
    pairwise counts of rows where both exist."""
    M = np.isfinite(X).astype(float)
    X0 = np.where(M > 0, X - np.nanmean(np.where(M > 0, X, np.nan), axis=0), 0.0)
    n = M.T @ M
    si, sj = X0.T @ M, M.T @ X0
    sii, sjj = (X0 ** 2).T @ M, M.T @ (X0 ** 2)
    sij = X0.T @ X0
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (n * sij - si * sj) / np.sqrt((n * sii - si ** 2) * (n * sjj - sj ** 2))
    r[n < min_rows] = np.nan
    return r, n


def hygiene(store: pd.DataFrame, reg: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Annotate the registry: degenerate pairs, exact (and negated) duplicates, near-duplicates, degenerate columns,
    the default menu. The store is not changed."""
    reg = reg.drop(columns=[c for c in HYGIENE if c in reg.columns]).copy()
    if "kind_built" in reg.columns:                                    # start from the builders' kinds every time
        reg["kind"], reg["partner"] = reg["kind_built"], reg["partner_built"]
    else:
        reg["kind_built"], reg["partner_built"] = reg["kind"], reg["partner"]
    vals = {c: store[c].to_numpy(dtype="float64") for c in reg["column"]}
    reg["canonical"], reg["dup_sign"], reg["degenerate"] = "", np.nan, ""
    idx = {c: i for i, c in enumerate(reg["column"])}
    # 1. "pairs" whose sides are equal (a match-level value) or negatives (a split difference)
    collapsed = []
    for c in reg.loc[reg["kind"] == "pair", "column"]:
        if not c.endswith("_a"):
            continue
        p = reg.at[idx[c], "partner"]
        same = np.allclose(vals[c], vals[p], rtol=0.0, atol=1e-9, equal_nan=True)
        neg = not same and np.allclose(vals[c], -vals[p], rtol=0.0, atol=1e-9, equal_nan=True)
        if same or neg:
            reg.loc[[idx[c], idx[p]], "kind"] = "context" if same else "diff"
            reg.loc[[idx[c], idx[p]], "partner"] = ""
            reg.at[idx[p], "canonical"], reg.at[idx[p], "dup_sign"] = c, 1.0 if same else -1.0
            collapsed.append((c, "equal" if same else "negated"))
    # 2. exact and negated duplicates, the representative by group priority then registry order
    order = sorted(range(len(reg)), key=lambda i: (PRIORITY.index(reg.at[i, "group"]), i))
    first: dict[bytes, str] = {}
    for i in order:
        c = reg.at[i, "column"]
        if reg.at[i, "canonical"]:
            continue
        k, kn = _key(vals[c]), _key(-vals[c])
        if k in first:
            reg.at[i, "canonical"], reg.at[i, "dup_sign"] = first[k], 1.0
        elif kn in first and np.isfinite(vals[c]).any() and np.nanmax(np.abs(vals[c])) > 0:
            reg.at[i, "canonical"], reg.at[i, "dup_sign"] = first[kn], -1.0
        else:
            first[k] = c
    # 3. degenerate columns: constant, or constant within each tour (a coding of the tour; m__tour itself is kept)
    tour = store["tour"].astype(str).to_numpy()
    for i, c in enumerate(reg["column"]):
        if c == TOUR_COLUMN:
            continue
        v = vals[c]
        fin = np.isfinite(v)
        if not fin.any() or np.nanmin(v) == np.nanmax(v):
            reg.at[i, "degenerate"] = "constant"
        elif all(np.nanmin(v[fin & (tour == t)]) == np.nanmax(v[fin & (tour == t)])
                 for t in np.unique(tour) if (fin & (tour == t)).any()):
            reg.at[i, "degenerate"] = "constant_within_tour"
    # 4. near-duplicates among the representatives
    reps = [i for i in order if not reg.at[i, "canonical"] and not reg.at[i, "degenerate"]]
    X = np.column_stack([vals[reg.at[i, "column"]] for i in reps])
    X = np.where(np.isfinite(X), X, np.nan)
    r, n = near_duplicates(X)
    reg["near_dup_of"], reg["near_dup_r"] = "", np.nan
    for b in range(len(reps)):
        # a near copy also adds (almost) no rows its representative lacks: a column that fills another's gaps (the
        # indoor flag of both tours against the model's men-only flag) is not redundant
        hit = [a for a in range(b) if np.isfinite(r[a, b]) and abs(r[a, b]) >= NEAR_DUP
               and n[b, b] - n[a, b] <= NEAR_DUP_EXTRA * n[b, b] and not reg.at[reps[a], "near_dup_of"]]
        if hit:
            a = max(hit, key=lambda a: abs(r[a, b]))
            reg.at[reps[b], "near_dup_of"] = reg.at[reps[a], "column"]
            reg.at[reps[b], "near_dup_r"] = float(r[a, b])
    reg["menu"] = ((reg["canonical"] == "") & (reg["degenerate"] == "") & (reg["near_dup_of"] == "")).astype(int)
    # pairs on the menu must still have their partner on it
    for c in reg.loc[(reg["kind"] == "pair") & (reg["menu"] == 1), "column"]:
        p = reg.at[idx[c], "partner"]
        if reg.at[idx[p], "menu"] != 1:
            reg.loc[[idx[c], idx[p]], "menu"] = 0
    pairs = reg[reg["kind"] == "pair"].set_index("column")["partner"]
    checks = {"pairs_collapsed": collapsed,
              "exact_duplicates": int((reg["dup_sign"] == 1).sum()),
              "negated_duplicates": int((reg["dup_sign"] == -1).sum()),
              "degenerate": reg.loc[reg["degenerate"] != "", ["column", "degenerate"]].values.tolist(),
              "near_duplicates": int((reg["near_dup_of"] != "").sum()),
              "menu_columns": int(reg["menu"].sum()),
              "menu_by_group": reg.loc[reg["menu"] == 1, "group"].value_counts().to_dict(),
              "pairs_consistent": bool(all(pairs.get(p, "") == c for c, p in pairs.items()))}
    cols = [c for c in reg.columns if not c.startswith("cov_")] + [c for c in reg.columns if c.startswith("cov_")]
    return reg[cols], checks


def registry_only() -> int:
    """Re-annotate store_registry.csv from the existing store (no rebuild)."""
    store = pd.read_parquet(OUT / "store.parquet")
    reg = pd.read_csv(OUT / "store_registry.csv", keep_default_na=False,
                      dtype={"partner": str, "partner_built": str, "hid": str, "flag": str, "canonical": str,
                             "near_dup_of": str, "degenerate": str})
    for c in [c for c in reg.columns if c.startswith("cov_")] + ["dup_sign", "near_dup_r"]:
        if c in reg.columns:
            reg[c] = pd.to_numeric(reg[c], errors="coerce")
    reg, hchecks = hygiene(store, reg)
    checks = json.loads((OUT / "store_build.json").read_text(encoding="utf-8"))
    checks["hygiene"] = hchecks
    checks["pairs_consistent"] = hchecks["pairs_consistent"]
    reg.to_csv(OUT / "store_registry.csv", index=False)
    C.write_json(OUT / "store_build.json", checks)
    log(f"registry re-annotated: {hchecks['menu_columns']} menu columns of {len(reg)}; exact duplicates "
        f"{hchecks['exact_duplicates']}, negated {hchecks['negated_duplicates']}, near {hchecks['near_duplicates']}, "
        f"degenerate {len(hchecks['degenerate'])}")
    return 0


def main() -> int:
    if "--registry-only" in sys.argv[1:]:
        return registry_only()
    warnings.simplefilter("ignore")
    P = panel26()
    L = long_table()
    ids = P["match_id"].astype(str).to_numpy()
    S = Store(ids)
    checks: dict = {}

    # m__: the model's 58 inputs
    mi = json.loads(C.MODEL_INPUTS.read_text(encoding="utf-8"))["inputs"]
    for d in mi:
        partner = ""
        if d["kind"] == "pair":
            stem, side = d["name"].rsplit("_", 1)
            partner = f"m__{stem}_{'b' if side == 'a' else 'a'}"
        S.add(f"m__{d['name']}", P[f"in_{d['name']}"], d["kind"], "m", "surface_rating_race/model/model_frame.parquet",
              f"model input {d['name']} ({d['source']})", partner)
    log(f"m__: {len(mi)} columns")

    # alt__: replaced inputs and alternatives
    pf = pd.read_parquet(C.ROOT / "data" / "studies" / "surface_elo_pieces" / "frame.parquet",
                         columns=["match_id", "x_elo_logit", "x_surface_first", "x_elo_surface"])
    pf["match_id"] = pf["match_id"].astype(str)
    pf = pf.set_index("match_id").reindex(ids)
    for c, desc in (("elo_logit", "the 70/30 (men) or 75/25 (women) surface Elo blend's log-odds (replaced 6 Oct)"),
                    ("surface_first", "A's first matches on the surface this season minus B's (replaced 6 Oct)"),
                    ("elo_surface", "surface-only Elo's log-odds")):
        S.add(f"alt__{c}", pf[f"x_{c}"], "diff", "alt", "surface_elo_pieces/frame.parquet", desc)
    for s in STATS8:
        oa, ob = P[f"ios_curO_{s}_a"].to_numpy(float), P[f"ios_curO_{s}_b"].to_numpy(float)
        da, db = P[f"ios_curD_{s}_a"].to_numpy(float), P[f"ios_curD_{s}_b"].to_numpy(float)
        S.add(f"alt__iosO_cur_{s}", oa - ob, "diff", "alt", "surface_ios/surface_features (cur)",
              f"pooled (all-surface) IOS offence of {s}, A - B (the pre-6-Oct input)")
        S.add(f"alt__iosD_cur_{s}", da - db, "diff", "alt", "surface_ios/surface_features (cur)",
              f"pooled IOS defence of {s}, A - B")
        S.add(f"alt__prod_cur_{s}", oa * (-db) - ob * (-da), "diff", "alt", "surface_ios/surface_features (cur)",
              f"pooled IOS matchup product of {s}")
        S.add(f"alt__sdevO_{s}", P[f"ios_srfE_{s}_a"] - P[f"ios_srfE_{s}_b"], "diff", "alt",
              "surface_ios/surface_features", f"surface deviation of the offence of {s}, A - B")
        S.add(f"alt__sdevD_{s}", P[f"ios_srfF_{s}_a"] - P[f"ios_srfF_{s}_b"], "diff", "alt",
              "surface_ios/surface_features", f"surface deviation of the defence of {s}, A - B")
    t = pd.read_parquet(OLD / "match_timing" / "ttt_timed.parquet", columns=["match_id", "p_ttt_timed"])
    t["match_id"] = t["match_id"].astype(str)
    S.add("alt__ttt_logit", lg(t.set_index("match_id").reindex(ids)["p_ttt_timed"]), "diff", "alt",
          "match_timing/ttt_timed (pre-rebuild)", "the decided TrueSkill Through Time's log-odds (the blend)")
    o = pd.read_parquet(C.ROOT / "data" / "studies" / "surface_rating_race" / "ttt_offset.parquet")
    o["match_id"] = o["match_id"].astype(str)
    o = o.set_index("match_id").reindex(ids).reset_index()
    _, z_over, z_off = TO.z_parts(o)
    S.add("alt__ttt_overall", z_over, "diff", "alt", "surface_rating_race/ttt_offset", "the offset TTT's overall part")
    S.add("alt__ttt_surf_offset", z_off, "diff", "alt", "surface_rating_race/ttt_offset", "the offset TTT's surface part")
    log("alt__ done")

    # pp__: each player's own pre-match values (numeric pairs; categoricals coded)
    skip = {"player_a_id", "player_b_id"}
    for c in [c for c in P.columns if c.endswith("_a") and c[:-2] + "_b" in P.columns and c not in skip]:
        stem = c[:-2]
        if stem in ("hand", "entry", "country", "avg", "ps", "max", "b365") or stem.startswith("in_"):
            continue
        a, b = pd.to_numeric(P[c], errors="coerce"), pd.to_numeric(P[stem + "_b"], errors="coerce")
        if a.notna().mean() == 0:
            continue
        S.add_pair(f"pp__{stem}", a, b, "pp", "feature_interactions/panel.py", f"each player's {stem}")
    S.add_pair("pp__hand_left", (P["hand_a"] == "L").astype(float).where(P["hand_a"].notna()),
               (P["hand_b"] == "L").astype(float).where(P["hand_b"].notna()), "pp", "Stage 0 players (pre-rebuild)",
               "left-handed (1) or not (0)")
    for code in ("Q", "WC", "LL", "PR", "SR", "ALT"):
        S.add_pair(f"pp__entry_{code}", (P["entry_a"].astype(str) == code).astype(float),
                   (P["entry_b"].astype(str) == code).astype(float), "pp", "Stage 0 players (pre-rebuild)",
                   f"entry code {code} (1/0)")
    S.add_pair("pp__seeded", P["seed_a"].notna().astype(float), P["seed_b"].notna().astype(float), "pp",
               "Stage 0 players (pre-rebuild)", "seeded at the event (1/0)")
    L2 = L[["match_id", "side", "rest_days"]]                  # rest before the match, from the player's own sequence
    ra, rb = at_model(L2, "rest_days", ids)
    S.add_pair("pp__rest_days", ra, rb, "pp", "feature_interactions/history.py",
               "days since the player's previous match (best-estimate days)")
    log("pp__ done")

    # mk__: market fields beyond the average close
    z_avg = devig_logit(P["avg_a"], P["avg_b"])
    for book in ("ps", "max", "b365"):
        z = devig_logit(P[f"{book}_a"], P[f"{book}_b"])
        S.add(f"mk__{book}_minus_avg", z - z_avg, "diff", "mk", "Stage 1 odds (pre-rebuild)",
              f"{book}'s de-vigged log-odds minus the average's", flag="market_internal")
    S.add("mk__overround_avg", P["overround_avg"], "context", "mk", "Stage 1 odds", "the average close's overround",
          flag="market_internal")
    disp = (1 / P["max_a"] + 1 / P["max_b"]) - (1 / P["avg_a"] + 1 / P["avg_b"])
    S.add("mk__dispersion", disp, "context", "mk", "Stage 1 odds",
          "the best prices' implied sum minus the average's (more negative = books disagree more)", flag="market_internal")
    # swap checks for mk__ (the panel's swap exchanges the odds sides)
    Ps = swap_sides(P)
    checks["mk_ps_antisymmetric"] = bool(np.allclose(
        devig_logit(Ps["ps_a"], Ps["ps_b"]) - devig_logit(Ps["avg_a"], Ps["avg_b"]),
        -(devig_logit(P["ps_a"], P["ps_b"]) - z_avg), equal_nan=True))
    log("mk__ done")

    # fi__, fp__, ds__: the study's builders
    swap_fail = []
    for path in sorted(B.FEATURE_DIR.glob(B.FAMILY)):
        mod = importlib.import_module(f"src.eda.feature_interactions.features.{path.stem}")
        for spec in mod.HYPOTHESES:
            hid = spec["hid"]
            new = spec["prepare"](P, L) if spec.get("prepare") else {}
            Q = P.assign(**new) if new else P
            r = B.evaluate(spec, Q)
            rs = B.evaluate(spec, swap_sides(Q))
            # which of its columns read the base model's forecast? (they must be recomputed with a new model's own)
            Qe = Q.assign(eta_model=Q["eta_model"] + 0.37)
            re_ = B.evaluate(spec, Qe)
            moved = lambda a, b: not np.allclose(np.asarray(a, float), np.asarray(b, float), equal_nan=True)  # noqa: E731
            eta_x = moved(r["x"], re_["x"])
            eta_tab = {t for t in (r.get("tabpfn") or {}) if moved(r["tabpfn"][t][0], re_["tabpfn"][t][0])}
            for k in [k for k in new if k.endswith("_a") and k[:-2] + "_b" in new]:
                S.add_pair(f"fp__{path.stem}__{k[:-2]}", new[k], new[k[:-2] + "_b"], "fp", f"{path.stem}.prepare",
                           f"per-player intermediate of {hid}", hid)
            # match-level intermediates (no _a/_b partner): kind from prepare() re-run on the swapped panel
            paired = {k for k in new if (k.endswith("_a") and k[:-2] + "_b" in new)
                      or (k.endswith("_b") and k[:-2] + "_a" in new)}
            single = {}
            for k in [k for k in new if k not in paired and np.ndim(new[k]) == 1 and len(new[k]) == len(P)]:
                try:
                    single[k] = np.asarray(new[k], dtype=float)
                except (TypeError, ValueError):
                    continue
            if single:
                new_s = spec["prepare"](swap_sides(P), L)
                for k, v in single.items():
                    vs = np.asarray(new_s[k], dtype=float)
                    kind = "context" if B.sym_ok(v, vs) else "diff" if B.antisym_ok(v, vs) else ""
                    if not kind:
                        swap_fail.append(f"fp__{path.stem}__{k}")
                        continue
                    S.add(f"fp__{path.stem}__{k}", v, kind, "fp", f"{path.stem}.prepare",
                          f"match-level intermediate of {hid}", hid=hid)
            X = np.asarray(r["x"], float).reshape(len(P), -1)
            Xs = np.asarray(rs["x"], float).reshape(len(P), -1)
            flag = fi_flag(eta_x, hid)
            for j in range(X.shape[1]):
                if r.get("x_times_eta"):
                    name, kind, ok = f"fi__{hid}__s" + (f"{j}" if X.shape[1] > 1 else ""), "context", \
                        B.sym_ok(X[:, j], Xs[:, j])
                else:
                    name = f"fi__{hid}__x" + (f"{j}" if X.shape[1] > 1 else "")
                    kind, ok = "diff", B.antisym_ok(X[:, j], Xs[:, j])
                if not ok:
                    swap_fail.append(name)
                S.add(name, X[:, j], kind, "fi", path.stem, f"{hid}'s screen column", hid=hid, flag=flag)
            for tname, (arr, kind, partner) in (r.get("tabpfn") or {}).items():
                a = np.asarray(arr, float)
                b_s = np.asarray(rs["tabpfn"][tname][0], float)
                if kind == "diff":
                    ok = B.antisym_ok(a, b_s)
                elif kind == "context":
                    ok = B.sym_ok(a, b_s)
                else:
                    ok = np.allclose(a, np.asarray(rs["tabpfn"][partner][0], float), equal_nan=True)
                if not ok:
                    swap_fail.append(f"fi__{hid}__{tname}")
                S.add(f"fi__{hid}__{tname}", a, kind, "fi", path.stem, f"{hid}'s TabPFN deployment column",
                      f"fi__{hid}__{partner}" if partner else None, hid, fi_flag(tname in eta_tab, hid))
            # every block member as its builder returns it (several are stored nowhere else: I-085, I-055, C-2)
            for mname, mval in (r.get("members") or {}).items():
                a = np.asarray(mval, dtype=float).reshape(-1)
                if a.shape[0] != len(P):
                    continue
                b_s = np.asarray(rs["members"][mname], dtype=float).reshape(-1)
                kind = "diff" if B.antisym_ok(a, b_s) else "context" if B.sym_ok(a, b_s) else ""
                name = f"fi__{hid}__m_" + re.sub(r"[^0-9A-Za-z_-]+", "_", mname).strip("_")
                if not kind:
                    swap_fail.append(name)
                    continue
                S.add(name, a, kind, "fi", path.stem, f"{hid}'s member {mname}", hid=hid,
                      flag=fi_flag(moved(a, re_["members"][mname]), hid))
        for name, fn in getattr(mod, "SENSITIVITIES", {}).items():
            hid = getattr(mod, "SENSITIVITY_OF", {}).get(name, name.split()[0])
            spec = next(s for s in mod.HYPOTHESES if s["hid"] == hid)
            new = spec["prepare"](P, L) if spec.get("prepare") else {}
            Q = P.assign(**new) if new else P
            safe = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
            S.add(f"ds__{safe}", fn(Q), "diff", "ds", path.stem, f"descriptive: {name}", hid=hid)
        log(f"{path.stem}: done")
    checks["fi_swap_failures"] = swap_fail
    return_history(S, P, L)
    checks["external"] = external(S, P, ids)
    log(f"return history and external tables done: {checks['external']}")

    # lv__: the 17 level sums
    F_lv, specs = LV.build(P)
    for n, sp in specs.items():
        S.add(f"lv__{n[3:]}", F_lv[n], "context", "lv", "feature_interactions/features/levels.py", sp["desc"])
    # kn__: the known nulls
    _, built = B.build_all(P, L, pattern=B.KNOWN_NULL)
    for hid, (x, Cm, names, spec, new) in built.items():
        X = np.asarray(x, float).reshape(len(P), -1)
        for j in range(X.shape[1]):
            S.add(f"kn__{hid}" + (f"__x{j}" if X.shape[1] > 1 else ""), X[:, j], "diff", "kn", "p3_known_null.py",
                  f"known-null placebo {hid}", hid=hid)
    # ctx__: match context
    for c in ("tour", "surface", "level", "indoor", "best_of", "round"):
        S.add(f"ctx__{c}", P[f"in_{c}"], "context", "ctx", "model frame", f"match context: {c} (the model's coding)")
    S.add("ctx__draw_size", pd.to_numeric(P["draw_size"], errors="coerce"), "context", "ctx", "Stage 0", "draw size")
    day = pd.to_datetime(P["tournament_date"])
    S.add("ctx__week", day.dt.isocalendar().week.astype(float), "context", "ctx", "Stage 0", "ISO week of the event")
    S.add("ctx__month", day.dt.month.astype(float), "context", "ctx", "Stage 0", "month of the event")
    log("lv__, kn__, ctx__ done")

    # write
    keys = P[KEYS].reset_index(drop=True)
    store = pd.concat([keys, pd.DataFrame(S.cols)], axis=1)
    reg = pd.DataFrame(S.meta)
    seasons = store["season"].to_numpy()
    for lo, hi, tag in ((2013, 2021, "cov_2013_2021"), (2022, 2024, "cov_2022_2024"), (2025, 2026, "cov_2025_2026")):
        m = (seasons >= lo) & (seasons <= hi)
        reg[tag] = [float(np.isfinite(store.loc[m, c].to_numpy(float)).mean()) for c in reg["column"]]
    # every pair must have its partner, and every pair partner must point back (again after hygiene)
    reg, checks["hygiene"] = hygiene(store, reg)
    checks["pairs_consistent"] = checks["hygiene"]["pairs_consistent"]
    checks["columns"] = int(len(reg))
    checks["by_group"] = reg["group"].value_counts().to_dict()
    checks["inputs_sha256"] = {k: C.sha256_file(v) for k, v in SOURCES.items() if v.exists()}
    OUT.mkdir(parents=True, exist_ok=True)
    store.to_parquet(OUT / "store.parquet", index=False)
    reg.to_csv(OUT / "store_registry.csv", index=False)
    C.write_json(OUT / "store_build.json", checks)
    log(f"store {store.shape}; groups {checks['by_group']}; swap failures {len(swap_fail)}; pairs consistent "
        f"{checks['pairs_consistent']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
