"""When does the other tour's data help? The tour-pooling study's segment analysis (docs/studies/tour_pooling/design.md,
section "When does the other tour's data help?": exploratory, flags only).

The forecasts. data/studies/tour_pooling/scores/forecasts.parquet, written by the study's scorer: one row per scored
match (2019 .. 28 Jul 2026) with match_id, tour, season, tournament_date, block, week, debut, level, y and, per model
(pooled, split, notour, borrow25, borrow50, borrowsim, aligned, sizectl, blend, select: whichever are complete),
q_<model> (both stages), q1_<model> (stage 1) and q_<model>_s0..s3 (each seed, both stages); q_close (the calibrated
close, no seeds). Rows from 29 Jul 2026 on (the proposed sealed holdout) are filtered out while the file is read,
before any result is.

The segments, declared in the design before any score, are defined here from the instance frame's INPUTS only
(data/studies/current_best_model/pinnacle_first_2026-10-09/model_frame.parquet, its in_* columns; its result column is
never read). Each tour (men, women) is cut by:
    level           Slams, 1000s, 500s, 250s, Finals (in_level 0, 2, 3, 4, 1)
    slam            Slam or not (added 9 Oct 2026 at the lead's request, for borrowsim, which borrows none of the
                    other tour's Slam matches)
    surface         hard, clay, grass (in_surface 0-2; carpet, women's 2013-14 only, would count as hard)
    best_of         3 or 5 (in_best_of; 5 = men's Slams only, so women have one cell, the same as all their matches)
    round           early = R128 to R16 (in_round 11-14); late = quarter-finals on (15-17) and round robins (10: the
                    Finals' groups and 12 matches at 500s, a top field)
    season          each season of the window
    favourite       thirds of |in_odds_logit|, the favourite's strength at the close, per tour; cut on the frame's
                    matches of 2019-2026 (close, middle, heavy)
    missing         NaN count among the 58 inputs leaving out indoor: none, 1-10, >10 (box scores absent). indoor is
                    recorded for men only, so counting it would put every women's match in 1-10
    surface_season  either player's first match on the surface this season (in_surf_season_a or _b = 0), or not

The readings, per window (W1 = 2022 .. 28 Jul 2026, the declared seasons; W2 = 2020-2024), debut seasons out; each
comparison is "arm vs base", + = the arm has the lower log loss (COMPARISONS, when both models are present):
    pooled vs split          + = pooled better: borrowing the other tour's data helps
    <arm> vs split           + = that model better than split (borrow25, borrow50, borrowsim, aligned, blend, select)
    borrowsim vs borrow50    + = borrowsim better: the similarity selection helps (same dose; the draws are coupled)
    sizectl vs split         + = sizectl better: composition (the other tour mixed in at the own tour's size) helps
    pooled vs sizectl        + = pooled better: size (all rows, at the pooled mix) helps
pooled vs split = (sizectl vs split) + (pooled vs sizectl) exactly, on the same matches: composition plus size.
mLL per match = 1000 x mean(LL(base) - LL(arm)), from score.paired_stats: 95% interval over four-week blocks plus the
seed term, paired by seed (matched_seeds=True) when both models carry the same seeds; P(better) = the t CDF of
estimate / se on blocks - 1 df (compare.p_better); "better" / "worse" when the interval clears 0, else "unresolved".
Benjamini-Hochberg q-values over the read cells of one window and one comparison (two-sided p from the same t). A cell
is read only with at least 100 matches and 5 four-week blocks; a cell holding exactly the matches of an earlier cell
(women's best of 3 = all their matches; men's best of 5 = men's Slams) is shown but counted once. Cells are flags, not
verdicts: with this many cells a few read P(better) near 0.95 or 0.05 by chance. The leads (q <= 0.10, or an interval
clearing 0) are also read on the scored seasons outside their window (W1: 2020-2021; W2: 2025 to 28 Jul 2026), data
that did not raise the flag.

Writes <out>/segments.csv, leads.csv, segments.md and segments.json (default out: data/studies/tour_pooling/segments/).
Run: ./python.sh src/eda/tour_pooling/segments.py [--forecasts <parquet>] [--out <folder>]
     ./python.sh src/eda/tour_pooling/segments.py --standin   # plumbing check on a stand-in through 2024: the
                                                               # instance as "pooled", the frozen reference as "split"
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402  (p_better, the stand-in's recipe)
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.tour_pooling import common as C  # noqa: E402

FORECASTS = C.OUT / "scores" / "forecasts.parquet"
OUT = C.OUT / "segments"
SEALED_FROM = pd.Timestamp("2026-07-29")       # the proposed sealed holdout: no result from here on is read
WINDOWS = {"W1": ((2022, 2026), "2022 to 28 Jul 2026 (the declared seasons)"),
           "W2": ((2020, 2024), "2020-2024 (the decided comparison's default window)")}
KNOWN_MODELS = ("pooled", "split", "notour", "borrow25", "borrow50", "borrowsim", "aligned", "sizectl", "blend",
                "select")
# (base, arm, direction): each reading is "arm vs base", + = the arm has the lower log loss
COMPARISONS = (
    ("split", "pooled", "+ = pooled better than split: borrowing the other tour's data helps"),
    ("split", "borrow25", "+ = borrow25 better than split"),
    ("split", "borrow50", "+ = borrow50 better than split"),
    ("split", "borrowsim", "+ = borrowsim better than split"),
    ("split", "aligned", "+ = aligned better than split"),
    ("split", "blend", "+ = blend better than split"),
    ("split", "select", "+ = select better than split"),
    ("borrow50", "borrowsim", "+ = borrowsim better than borrow50: the similarity selection helps (same dose)"),
    ("split", "sizectl", "+ = sizectl better than split: composition (the other tour mixed in at equal size) helps"),
    ("sizectl", "pooled", "+ = pooled better than sizectl: size (all rows at the pooled mix) helps"),
)
MATRIX = ("pooled vs split", "borrowsim vs borrow50", "sizectl vs split", "pooled vs sizectl")
MIN_MATCHES, MIN_BLOCKS = 100, 5
FAV_SEASONS = (2019, 2026)                     # the favourite thirds are cut on the frame's matches of these seasons

TOUR_NAME = {"atp": "men", "wta": "women"}
LEVELS = {0: "Slams", 2: "1000s", 3: "500s", 4: "250s", 1: "Finals"}
SURFACES = {0: "hard", 1: "clay", 2: "grass", 3: "hard"}
EARLY_ROUNDS = (11, 12, 13, 14)                # R128, R64, R32, R16 (Stage 0 round_order)
LATE_ROUNDS = (10, 15, 16, 17)                 # RR, QF, SF, F
ROUND_LABELS = {"early": "R128-R16", "late": "QF on (and RR)"}
FAVOURITE = ("close third", "middle third", "heavy third")
MISSING = ("none", "1-10", ">10")
SURF_SEASON = ("first on surface", "not first")
ORDER = {"all": ["all"], "level": list(dict.fromkeys(LEVELS.values())), "slam": ["Slam", "non-Slam"],
         "surface": ["hard", "clay", "grass"], "best_of": ["best of 3", "best of 5"],
         "round": list(ROUND_LABELS.values()), "season": [str(y) for y in range(2019, 2027)],
         "favourite": list(FAVOURITE), "missing": list(MISSING), "surface_season": list(SURF_SEASON)}
DIMENSIONS = tuple(ORDER)
SEGMENT_COLUMNS = ["all", "level", "slam", "surface", "best_of", "round", "season_cell", "favourite", "missing",
                   "surface_season", "abs_odds_logit", "fav_prob", "n_missing"]


def direction(base: str, arm: str) -> str:
    for b, a, d in COMPARISONS:
        if (b, a) == (base, arm):
            return d
    return f"+ = {arm} better than {base}"


def dimension_column(dim: str) -> str:
    return "season_cell" if dim == "season" else dim


# ------------------------------------------------------------------------------------------------
# The segments (inputs only)

def input_names() -> list[str]:
    return SA.base_inputs(C.P)[0]


def frame_inputs(path: Path | None = None) -> pd.DataFrame:
    """The instance frame's match facts and in_* inputs by match id. The result column is never selected."""
    path = Path(path) if path is not None else C.P.model_frame
    cols = [c for c in pq.read_schema(path).names
            if c in ("match_id", "tour", "season", "tournament_date") or c.startswith("in_")]
    f = pd.read_parquet(path, columns=cols)
    f["match_id"] = f["match_id"].astype(str)
    if f["match_id"].duplicated().any():
        raise RuntimeError("frame match ids are not unique")
    return f.set_index("match_id")


def _codes(x: pd.Series) -> np.ndarray:
    """Integer codes of a float context column (NaN -> -1)."""
    v = x.to_numpy(float)
    return np.where(np.isfinite(v), np.round(v), -1).astype(int)


def favourite_cuts(f: pd.DataFrame, seasons=FAV_SEASONS) -> dict[str, tuple[float, float]]:
    """Per tour: the 1/3 and 2/3 quantiles of |in_odds_logit| over the frame's matches of the seasons (inputs only)."""
    s = f["season"].to_numpy()
    m = (s >= seasons[0]) & (s <= seasons[1])
    out = {}
    for tour in C.TOURS:
        x = np.abs(f.loc[m & (f["tour"].to_numpy() == tour), "in_odds_logit"].to_numpy(float))
        x = x[np.isfinite(x)]
        out[tour] = (float(np.quantile(x, 1 / 3)), float(np.quantile(x, 2 / 3)))
    return out


def segment_frame(f: pd.DataFrame | None = None, names: list[str] | None = None,
                  cuts: dict | None = None) -> pd.DataFrame:
    """One row per frame match (by match id): tour, season and each dimension's cell, plus the numbers behind them
    (abs_odds_logit; fav_prob, the favourite's implied probability; n_missing, without indoor; n_missing_with_indoor).
    The favourite cuts are kept in .attrs["favourite_cuts"]."""
    f = frame_inputs() if f is None else f
    names = input_names() if names is None else names
    cuts = favourite_cuts(f) if cuts is None else cuts
    tour = f["tour"].astype(str).to_numpy()
    seg = pd.DataFrame(index=f.index)
    seg["tour"] = tour
    seg["season"] = f["season"].astype(int).to_numpy()
    seg["all"] = "all"
    seg["level"] = [LEVELS.get(c, "other") for c in _codes(f["in_level"])]
    seg["slam"] = np.where(seg["level"].to_numpy() == "Slams", "Slam", "non-Slam")
    seg["surface"] = [SURFACES.get(c, "other") for c in _codes(f["in_surface"])]
    seg["best_of"] = [f"best of {c}" if c > 0 else "other" for c in _codes(f["in_best_of"])]
    rc = _codes(f["in_round"])
    seg["round"] = np.where(np.isin(rc, EARLY_ROUNDS), ROUND_LABELS["early"],
                            np.where(np.isin(rc, LATE_ROUNDS), ROUND_LABELS["late"], "other"))
    seg["season_cell"] = seg["season"].astype(str)
    ax = np.abs(f["in_odds_logit"].to_numpy(float))
    lo = np.array([cuts[t][0] for t in tour])
    hi = np.array([cuts[t][1] for t in tour])
    seg["favourite"] = np.where(~np.isfinite(ax), "no price",
                                np.where(ax <= lo, FAVOURITE[0], np.where(ax <= hi, FAVOURITE[1], FAVOURITE[2])))
    seg["abs_odds_logit"] = ax
    seg["fav_prob"] = 1 / (1 + np.exp(-ax))
    nm = f[[f"in_{n}" for n in names if n != "indoor"]].isna().sum(axis=1).to_numpy()
    seg["n_missing"] = nm
    seg["n_missing_with_indoor"] = f[[f"in_{n}" for n in names]].isna().sum(axis=1).to_numpy()
    seg["missing"] = np.where(nm == 0, MISSING[0], np.where(nm <= 10, MISSING[1], MISSING[2]))
    first = (f["in_surf_season_a"].to_numpy(float) == 0) | (f["in_surf_season_b"].to_numpy(float) == 0)
    seg["surface_season"] = np.where(first, SURF_SEASON[0], SURF_SEASON[1])
    seg.attrs["favourite_cuts"] = {t: tuple(map(float, c)) for t, c in cuts.items()}
    return seg


# ------------------------------------------------------------------------------------------------
# The forecasts

def _sealed_filter(path: Path) -> list:
    """A read filter keeping rows before SEALED_FROM, typed as the file's tournament_date column."""
    field = pq.read_schema(path).field("tournament_date")
    if pa.types.is_timestamp(field.type):
        value = SEALED_FROM
    elif pa.types.is_date(field.type):
        value = SEALED_FROM.date()
    elif pa.types.is_string(field.type) or pa.types.is_large_string(field.type):
        value = SEALED_FROM.strftime("%Y-%m-%d")
    else:
        raise RuntimeError(f"tournament_date has an unexpected type {field.type}")
    return [("tournament_date", "<", value)]


def load_forecasts(path: Path) -> pd.DataFrame:
    """The scored matches by match id. Rows from SEALED_FROM on are dropped while the file is read, so their results
    never enter memory; the check after the read refuses the file if any remains."""
    path = Path(path)
    names = pq.read_schema(path).names
    need = {"match_id", "tour", "season", "tournament_date", "block", "week", "debut", "y"}
    if need - set(names):
        raise RuntimeError(f"{path.name} lacks {sorted(need - set(names))}")
    fc = pd.read_parquet(path, filters=_sealed_filter(path))
    if len(fc) and (pd.to_datetime(fc["tournament_date"]) >= SEALED_FROM).any():
        raise RuntimeError("a sealed match was read")
    fc["match_id"] = fc["match_id"].astype(str)
    if fc["match_id"].duplicated().any():
        raise RuntimeError("forecast match ids are not unique")
    fc["tour"] = fc["tour"].astype(str)
    fc["season"] = fc["season"].astype(int)
    fc["debut"] = fc["debut"].astype(bool)
    return fc.set_index("match_id")


def models_present(fc: pd.DataFrame) -> list[str]:
    """The models with a q_<model> column: the known ones in design order, then any other (q_close is the price)."""
    others = sorted({c[2:] for c in fc.columns if c.startswith("q_") and c != "q_close"
                     and not (c.rsplit("_s", 1)[-1].isdigit() and "_s" in c[2:])} - set(KNOWN_MODELS))
    return [m for m in KNOWN_MODELS if f"q_{m}" in fc.columns] + others


def seed_ids(fc: pd.DataFrame, model: str) -> list[int]:
    pre = f"q_{model}_s"
    return sorted(int(c[len(pre):]) for c in fc.columns if c.startswith(pre) and c[len(pre):].isdigit())


def comparisons(present: list[str]) -> list[tuple[str, str]]:
    """(base, arm) pairs of COMPARISONS whose two models are both present, in declared order. notour (not a borrowing
    arm) and any other column (e.g. the frozen reference, scored for the record) are left out."""
    return [(b, a) for b, a, _ in COMPARISONS if b in present and a in present]


def attach_segments(fc: pd.DataFrame, seg: pd.DataFrame) -> pd.DataFrame:
    """The forecasts with each match's cells (the frame's definitions replace any the forecasts carry, e.g. level).
    Every scored match must be in the frame, with the same tour and season."""
    miss = fc.index.difference(seg.index)
    if len(miss):
        raise RuntimeError(f"{len(miss)} scored matches are not in the instance frame (e.g. {list(miss[:3])})")
    s = seg.loc[fc.index]
    if not (np.array_equal(s["tour"].to_numpy(), fc["tour"].to_numpy())
            and np.array_equal(s["season"].to_numpy(), fc["season"].to_numpy())):
        raise RuntimeError("the forecasts and the frame disagree on a match's tour or season")
    return fc.drop(columns=[c for c in SEGMENT_COLUMNS if c in fc.columns]).join(s[SEGMENT_COLUMNS])


# ------------------------------------------------------------------------------------------------
# One cell

def bh(p) -> np.ndarray:
    """Benjamini-Hochberg q-values; NaN p-values are left out of the family and get NaN."""
    p = np.asarray(p, float)
    q = np.full(len(p), np.nan)
    idx = np.flatnonzero(np.isfinite(p))
    m = len(idx)
    if m == 0:
        return q
    order = idx[np.argsort(p[idx], kind="mergesort")]
    ranked = p[order] * m / np.arange(1, m + 1)
    q[order] = np.minimum(np.minimum.accumulate(ranked[::-1])[::-1], 1.0)
    return q


def reading(lo: float, hi: float) -> str:
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return "no interval"
    return CMP.reading(lo, hi)


def cell_stats(sub: pd.DataFrame, base: str, arm: str) -> dict:
    """The paired reading of arm against base on these rows: + = the arm has the lower log loss. The seed term is
    paired when both carry the same seeds (two or more); otherwise each side's own seed variance (none for a model
    without per-seed columns)."""
    y = sub["y"].to_numpy(float)
    qb, qa = sub[f"q_{base}"].to_numpy(float), sub[f"q_{arm}"].to_numpy(float)
    llb, lla = C.SC.ll(qb, y), C.SC.ll(qa, y)
    kb, ka = seed_ids(sub, base), seed_ids(sub, arm)
    matched = len(kb) > 1 and kb == ka

    def seeds(model, ks, ll):
        if ks:
            return S.seed_loss(sub[[f"q_{model}_s{k}" for k in ks]].to_numpy(float), y)
        return np.array([1000 * ll.mean()])

    sb, sa = seeds(base, kb, llb), seeds(arm, ka, lla)
    blocks = sub["block"].to_numpy()
    out = {"matches": int(len(sub)), "blocks": int(len(np.unique(blocks))), "ll_base": float(llb.mean()),
           "ll_arm": float(lla.mean()), "estimate": float(1000 * (llb - lla).mean()),
           "mean_abs_logit_gap": float(np.abs(C.SC.lg(qa) - C.SC.lg(qb)).mean()),
           "seed_term": "paired" if matched else ("unpaired" if max(len(kb), len(ka)) > 1 else "none"),
           "lo": np.nan, "hi": np.nan, "se": np.nan, "p_better": np.nan, "p_two_sided": np.nan,
           "lo_week": np.nan, "hi_week": np.nan}
    if out["blocks"] < 2:
        return out
    r = S.paired_stats(llb, lla, sb, sa, blocks, sub["week"].to_numpy(), matched_seeds=matched)
    two = float(2 * student_t.sf(abs(r["estimate"]) / r["se"], r["blocks"] - 1)) if r["se"] > 0 else np.nan
    out.update({"estimate": float(r["estimate"]), "lo": float(r["lo"]), "hi": float(r["hi"]), "se": float(r["se"]),
                "p_better": CMP.p_better(r["estimate"], r["se"], r["blocks"]), "p_two_sided": two,
                "lo_week": float(r["lo_week"]), "hi_week": float(r["hi_week"])})
    return out


# ------------------------------------------------------------------------------------------------
# All cells

def window_mask(fc: pd.DataFrame, window: str) -> np.ndarray:
    (a, b), _ = WINDOWS[window]
    s = fc["season"].to_numpy()
    dates = pd.to_datetime(fc["tournament_date"]).to_numpy()
    return (s >= a) & (s <= b) & ~fc["debut"].to_numpy(bool) & (dates < np.datetime64(SEALED_FROM))


def score_cells(fc: pd.DataFrame, pairs: list[tuple[str, str]], windows=tuple(WINDOWS)) -> pd.DataFrame:
    """Every cell of every window and comparison. A cell whose matches are exactly an earlier cell's (same window,
    comparison and tour; dimensions in DIMENSIONS order) names it in duplicate_of and is not read twice."""
    rows = []
    for w in windows:
        wm = window_mask(fc, w)
        for base, arm in pairs:
            have = fc[f"q_{arm}"].notna().to_numpy() & fc[f"q_{base}"].notna().to_numpy()
            pop = fc.loc[wm & have]
            if not len(pop):
                continue
            rows.append({"window": w, "base": base, "arm": arm, "tour": "both tours", "dimension": "all",
                         "cell": "all", "reference_row": True, "duplicate_of": "", **cell_stats(pop, base, arm)})
            for tour in C.TOURS:
                tp = pop[pop["tour"].to_numpy() == tour]
                if not len(tp):
                    continue
                seen: dict[bytes, str] = {}
                for dim in DIMENSIONS:
                    col = dimension_column(dim)
                    vals = tp[col].astype(str).to_numpy()
                    for cell in ORDER[dim] + sorted(set(vals) - set(ORDER[dim])):
                        m = vals == cell
                        if not m.any():
                            continue
                        key = np.packbits(m).tobytes()
                        dup = seen.setdefault(key, f"{dim}: {cell}")
                        rows.append({"window": w, "base": base, "arm": arm, "tour": TOUR_NAME[tour],
                                     "dimension": dim, "cell": cell, "reference_row": False,
                                     "duplicate_of": "" if dup == f"{dim}: {cell}" else dup,
                                     **cell_stats(tp[m], base, arm)})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    big = (t["matches"] >= MIN_MATCHES) & (t["blocks"] >= MIN_BLOCKS) & np.isfinite(t["p_two_sided"])
    t["read"] = big & (t["duplicate_of"] == "") & ~t["reference_row"]
    shown = t["read"] | t["reference_row"] | (big & (t["duplicate_of"] != ""))   # a twin shows its original's reading
    t["reading"] = [reading(lo, hi) if s else "not read" for lo, hi, s in zip(t["lo"], t["hi"], shown)]
    t["direction"] = [direction(b, a) for b, a in zip(t["base"], t["arm"])]
    t["comparison"] = [f"{a} vs {b}" for a, b in zip(t["arm"], t["base"])]
    t["q_bh"] = np.nan
    t["family_size"] = 0
    for _, g in t.groupby(["window", "comparison"], sort=False):
        idx = g.index[g["read"].to_numpy()]
        t.loc[idx, "q_bh"] = bh(t.loc[idx, "p_two_sided"].to_numpy())
        t.loc[g.index, "family_size"] = len(idx)
    first = ["window", "comparison", "direction", "tour", "dimension", "cell", "matches", "blocks", "estimate", "lo",
             "hi", "p_better", "reading", "q_bh", "family_size", "read", "se", "p_two_sided", "lo_week", "hi_week",
             "seed_term", "ll_base", "ll_arm", "mean_abs_logit_gap", "duplicate_of", "reference_row", "base", "arm"]
    return t[first]


# ------------------------------------------------------------------------------------------------
# The report

def fmt_cell(r) -> str:
    if not np.isfinite(r["lo"]):
        return f"{r['estimate']:+.2f} (no interval)"
    tail = f"P {r['p_better']:.2f}"
    if np.isfinite(r["q_bh"]):
        tail += f", q {r['q_bh']:.2f}"
    if r["reading"] == "not read":
        tail += ", not read"
    star = "**" if r["reading"] in ("better", "worse") else ""
    return f"{star}{r['estimate']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}]{star} ({tail})"


def matrix(g: pd.DataFrame) -> str:
    """One comparison in one window: segment cells as rows, men and women as columns."""
    g = g[~g["reference_row"]]
    lines = ["| Segment | Cell | Men | n | Women | n |", "|---|---|---|---|---|---|"]
    for dim in DIMENSIONS:
        have = set(g.loc[g["dimension"] == dim, "cell"])
        for cell in [c for c in ORDER[dim] if c in have] + sorted(have - set(ORDER[dim])):
            parts = []
            for tour in ("men", "women"):
                r = g[(g["dimension"] == dim) & (g["cell"] == cell) & (g["tour"] == tour)]
                if not len(r):
                    parts += ["–", ""]
                    continue
                r = r.iloc[0]
                if r["duplicate_of"] == "all: all":
                    txt = "same as all"
                elif r["duplicate_of"]:
                    txt = f"{fmt_cell(r)} (= {r['duplicate_of']}, counted once)"
                else:
                    txt = fmt_cell(r)
                parts += [txt, f"{r['matches']:,}"]
            lines.append(f"| {dim} | {cell} | {parts[0]} | {parts[1]} | {parts[2]} | {parts[3]} |")
    return "\n".join(lines)


def decomposition(sub: pd.DataFrame) -> str:
    """pooled vs split = (sizectl vs split) + (pooled vs sizectl): composition plus size, per tour (one window's rows,
    when all three comparisons are present). The sum is exact on the same matches."""
    need = ("pooled vs split", "sizectl vs split", "pooled vs sizectl")
    if not all((sub["comparison"] == c).any() for c in need):
        return ""
    lines = ["### Pooled vs split = composition + size (all + = the first-named model better)\n",
             "| Tour | Pooled vs split (total) | Composition: sizectl vs split | Size: pooled vs sizectl | Sum |",
             "|---|---|---|---|---|"]
    for tour in ("both tours", "men", "women"):
        cells = []
        for c in need:
            r = sub[(sub["comparison"] == c) & (sub["tour"] == tour) & (sub["dimension"] == "all")]
            cells.append(r.iloc[0] if len(r) else None)
        if any(x is None for x in cells):
            continue
        same = cells[0]["matches"] == cells[1]["matches"] == cells[2]["matches"]
        total = cells[1]["estimate"] + cells[2]["estimate"]
        lines.append(f"| {tour} | {fmt_cell(cells[0])} | {fmt_cell(cells[1])} | {fmt_cell(cells[2])} | "
                     f"{total:+.2f}{'' if same else ' (different matches)'} |")
    return "\n".join(lines) + "\n"


def leads(t: pd.DataFrame, q_max: float = 0.10) -> pd.DataFrame:
    g = t[t["read"]]
    return g[(g["q_bh"] <= q_max) | g["reading"].isin(["better", "worse"])].sort_values(
        ["window", "comparison", "p_two_sided"])


# The scored seasons outside each window: where a lead found in the window can be checked (W1's are 2020-2021; W2's
# are 2025 to 28 Jul 2026). Not independent confirmation in the strict sense (the same models and design), but data
# that did not raise the flag.
OUTSIDE = {"W1": (2020, 2021), "W2": (2025, 2026)}
TOUR_CODE = {v: k for k, v in TOUR_NAME.items()}


def outside_check(fc: pd.DataFrame, ld: pd.DataFrame) -> pd.DataFrame:
    """Each lead's cell read on the scored seasons outside its window (same comparison, same direction)."""
    out = ld.copy()
    for col in ("outside_seasons", "outside_matches", "outside_estimate", "outside_lo", "outside_hi",
                "outside_p_better"):
        out[col] = np.nan if col != "outside_seasons" else ""
    s = fc["season"].to_numpy()
    dates = pd.to_datetime(fc["tournament_date"]).to_numpy()
    base_mask = ~fc["debut"].to_numpy(bool) & (dates < np.datetime64(SEALED_FROM))
    for i, r in ld.iterrows():
        a, b = OUTSIDE[r["window"]]
        m = (base_mask & (s >= a) & (s <= b) & (fc["tour"].to_numpy() == TOUR_CODE[r["tour"]])
             & (fc[dimension_column(r["dimension"])].astype(str).to_numpy() == r["cell"])
             & fc[f"q_{r['arm']}"].notna().to_numpy() & fc[f"q_{r['base']}"].notna().to_numpy())
        out.loc[i, "outside_seasons"] = f"{a}-{b}"
        if m.sum() == 0:
            continue
        c = cell_stats(fc.loc[m], r["base"], r["arm"])
        out.loc[i, ["outside_matches", "outside_estimate", "outside_lo", "outside_hi", "outside_p_better"]] = \
            [c["matches"], c["estimate"], c["lo"], c["hi"], c["p_better"]]
    return out


def report(t: pd.DataFrame, meta: dict, ld: pd.DataFrame | None = None) -> str:
    out = [f"# Tour pooling: when does the other tour's data help? (segment flags)"
           f"{' — STAND-IN, not the study' if meta['standin'] else ''}\n",
           f"Generated by `src/eda/tour_pooling/segments.py` on {meta['generated_at']}. Exploratory, as declared in the "
           "design (`docs/studies/tour_pooling/design.md`, \"When does the other tour's data help?\"). **Every cell is a "
           "flag, not a verdict.**\n"]
    if meta["standin"]:
        out.append("> **Stand-in.** \"pooled\" is the Pinnacle-first instance and \"split\" the frozen reference (the "
                   "books' average as odds input), seasons through 2024 only. It exercises the code on real data; its "
                   "numbers say nothing about tour pooling.\n")
    cuts = "; ".join(f"{TOUR_NAME[k]}: close third = favourite ≤ {v['p_lo']:.0%}, heavy third = favourite > "
                     f"{v['p_hi']:.0%}" for k, v in meta["favourite_cuts"].items())
    out += [f"* **Forecasts:** `{meta['forecasts']}` (SHA-256 {meta['forecasts_sha256'][:12]}…), {meta['rows']:,} rows "
            f"read; rows from 29 Jul 2026 are filtered out at read time. Models: {', '.join(meta['models'])}.",
            "* **Unit and direction:** mLL per match = 1000 × mean log-loss difference. Each reading is \"arm vs "
            "base\", **+ = the arm (named first) better**; every table states its direction. **Pooled vs split: + = "
            "pooled better, i.e. borrowing the other tour's data helps.** 95% intervals over four-week blocks plus "
            "the seed term (paired by seed when both models carry seeds 0–3). Bold = the interval clears 0 "
            "(\"better\"/\"worse\"); otherwise \"unresolved\". P = P(better), t on blocks − 1 df. q = "
            "Benjamini–Hochberg over the read cells of that window and comparison.",
            f"* **Read cells** need ≥ {MIN_MATCHES} matches and ≥ {MIN_BLOCKS} four-week blocks; smaller ones are shown "
            "and marked \"not read\". Debut seasons out.",
            f"* **Favourite thirds** (|close log-odds| per tour, cut on the frame's 2019–2026 matches): {cuts}.",
            "* **Missing inputs** count NaNs among the 58 inputs except `indoor` (recorded for men only).\n"]
    for w, (_, label) in WINDOWS.items():
        sub = t[t["window"] == w]
        if sub.empty:
            continue
        out.append(f"## {w}: {label}\n")
        totals = ["| Comparison | Direction | Both tours | Men | Women | Read cells | Clear 0 (≈ by chance) | "
                  "Mean \\|Δ log-odds\\| men / women |",
                  "|---|---|---|---|---|---|---|---|"]
        for comp in dict.fromkeys(sub["comparison"]):
            g = sub[sub["comparison"] == comp]
            ref = g[g["reference_row"]].iloc[0]
            men = g[(g["tour"] == "men") & (g["dimension"] == "all")]
            wom = g[(g["tour"] == "women") & (g["dimension"] == "all")]
            n_read = int(g["read"].sum())
            n_clear = int(g.loc[g["read"], "reading"].isin(["better", "worse"]).sum())
            gap = " / ".join(f"{x.iloc[0]['mean_abs_logit_gap']:.3f}" if len(x) else "–" for x in (men, wom))
            totals.append(f"| {comp} | {ref['direction']} | {fmt_cell(ref)} | "
                          f"{fmt_cell(men.iloc[0]) if len(men) else '–'} | {fmt_cell(wom.iloc[0]) if len(wom) else '–'} | "
                          f"{n_read} | {n_clear} (≈ {0.05 * n_read:.1f}) | {gap} |")
        out.append("\n".join(totals) + "\n")
        out.append("Mean \\|Δ log-odds\\| = the average distance between the two models' forecasts in log-odds (0.04 is "
                   "about 1 percentage point at an even match): how much the change of training rows moves the price.\n")
        dec = decomposition(sub)
        if dec:
            out.append(dec)
        for comp in MATRIX:
            g = sub[sub["comparison"] == comp]
            if len(g):
                out.append(f"### {comp[0].upper()}{comp[1:]} by segment ({g['direction'].iloc[0]})\n")
                out.append(matrix(g) + "\n")
    ld = leads(t) if ld is None else ld
    out.append("## The leads (q ≤ 0.10, or the interval clears 0)\n")
    if ld.empty:
        out.append("None: no read cell clears 0, and none has q ≤ 0.10.\n")
    else:
        out.append("\"Outside\" reads the same cell, comparison and direction on the scored seasons outside the window "
                   "(W1: 2020–2021; W2: 2025 to 28 Jul 2026): data that did not raise the flag.\n")
        out += ["| Window | Comparison | Direction | Tour | Segment | Cell | n | Estimate [95%] | P(better) | q (BH) | "
                "Outside: seasons, n, estimate [95%], P(better) |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
        for _, r in ld.iterrows():
            side = "–"
            if "outside_estimate" in ld.columns and np.isfinite(r["outside_estimate"]):
                iv = (f"[{r['outside_lo']:+.2f}, {r['outside_hi']:+.2f}]" if np.isfinite(r["outside_lo"])
                      else "(no interval)")
                pb = f"{r['outside_p_better']:.2f}" if np.isfinite(r["outside_p_better"]) else "–"
                side = (f"{r['outside_seasons']}, {int(r['outside_matches']):,}, {r['outside_estimate']:+.2f} {iv}, "
                        f"P {pb}")
            out.append(f"| {r['window']} | {r['comparison']} | {r['direction']} | {r['tour']} | {r['dimension']} | "
                       f"{r['cell']} | {r['matches']:,} | {r['estimate']:+.2f} [{r['lo']:+.2f}, {r['hi']:+.2f}] | "
                       f"{r['p_better']:.3f} | {r['q_bh']:.2f} | {side} |")
        out.append("")
    out.append("**Caveat.** Cells are flags, not verdicts. With this many cells, a few read P(better) near 0.95 or 0.05 "
               "by chance (a 13-cell table shows one about once). The segments overlap (men's best of 5 = men's "
               "Slams), so cells are not independent, and W1 and W2 share 2022–2024. A lead found here was found in "
               "the scored seasons and needs confirmation outside them before any suggestion.\n")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------
# The stand-in (a plumbing check only; seasons through 2024, so no 2025-26 result is read)

def standin(through: int = 2024) -> Path:
    from src.eda.current_best_model import reference as R
    _, P_new, _ = CMP.candidate(str(C.INSTANCE))
    P_ref = R.paths("reference")
    new, ref = CMP.inputs_frame(P_new), CMP.inputs_frame(P_ref)
    info = CMP.scoring_info(ref, new, CMP.outcomes(P_ref, through), CMP.outcomes(P_new, through), through,
                            base="candidate")
    z = R.speed_column("reference")
    info = info[np.isfinite(z.reindex(info.index).to_numpy(float))]
    seasons = tuple(range(CMP.FIT_FROM, through + 1))
    test = tuple(range(CMP.SCORE_FROM, through + 1))
    ids = info.index[info["season"].isin(test).to_numpy()]
    out = info.loc[ids, ["tour", "season", "tournament_date", "block", "week", "debut", "level", "y"]].copy()
    for name, P, frame in (("pooled", P_new, new), ("split", P_ref, ref)):
        p = CMP.seed_table(P, frame, seasons).reindex(info.index)
        if p.isna().any().any():
            raise SystemExit(f"stand-in: forecasts missing for {name}")
        eta = pd.Series(C.SC.lg(p.mean(axis=1).to_numpy()), index=p.index)
        q, qk = CMP.forecasts(p, info, CMP.walk_forward(eta, info, z, test), z, ids)
        q1, _ = CMP.forecasts(p, info, CMP.walk_forward(eta, info, None, test), None, ids)
        out[f"q_{name}"], out[f"q1_{name}"] = q, q1
        for k in range(qk.shape[1]):
            out[f"q_{name}_s{k}"] = qk[:, k]
    out["q_close"] = CMP.close_forecast(info, "p_cand", test, ids)[0]
    folder = OUT / "standin"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "forecasts_standin.parquet"
    out.reset_index().to_parquet(path, index=False)
    C.log(f"stand-in: {len(out):,} matches, seasons {test[0]}-{through}, written {path.relative_to(ROOT)}")
    return path


# ------------------------------------------------------------------------------------------------

def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.as_posix()


def run(forecasts: Path = FORECASTS, out_dir: Path = OUT, seg: pd.DataFrame | None = None,
        standin_run: bool = False) -> pd.DataFrame:
    forecasts, out_dir = Path(forecasts), Path(out_dir)
    fc = load_forecasts(forecasts)
    present = models_present(fc)
    pairs = comparisons(present)
    if not pairs:
        raise SystemExit(f"{forecasts.name}: no split forecasts, or nothing to compare with them ({present})")
    seg = segment_frame() if seg is None else seg
    cuts = seg.attrs.get("favourite_cuts", {})
    fcs = attach_segments(fc, seg)
    t = score_cells(fcs, pairs)
    ld = outside_check(fcs, leads(t))
    out_dir.mkdir(parents=True, exist_ok=True)
    ld.to_csv(out_dir / "leads.csv", index=False)
    meta = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "forecasts": _rel(forecasts),
            "forecasts_sha256": hashlib.sha256(forecasts.read_bytes()).hexdigest(), "rows": int(len(fc)),
            "models": present, "comparisons": [f"{a} vs {b}" for b, a in pairs],
            "windows": {k: v[1] for k, v in WINDOWS.items()},
            "favourite_cuts": {t_: {"abs_logit": list(c), "p_lo": float(1 / (1 + np.exp(-c[0]))),
                                    "p_hi": float(1 / (1 + np.exp(-c[1])))} for t_, c in cuts.items()},
            "min_matches": MIN_MATCHES, "min_blocks": MIN_BLOCKS, "sealed_from": str(SEALED_FROM.date()),
            "standin": standin_run,
            "unit": "mLL per match = 1000 x mean(LL(split) - LL(arm)); + = the arm better than split (pooled vs "
                    "split: + = borrowing the other tour's data helps); 95% interval over four-week blocks plus the "
                    "seed term (paired by seed when both carry the same seeds); P(better) = t CDF on blocks - 1 df; "
                    "q_bh = Benjamini-Hochberg over the read cells of one window and comparison"}
    t.to_csv(out_dir / "segments.csv", index=False)
    (out_dir / "segments.md").write_text(report(t, meta, ld), encoding="utf-8")
    C.write_json(out_dir / "segments.json", meta)
    C.log(f"segments: {len(t)} rows, {int(t['read'].sum())} read -> {_rel(out_dir)}")
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--forecasts", default=str(FORECASTS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--standin", action="store_true", help="build and score the stand-in (seasons through 2024)")
    a = ap.parse_args()
    if a.standin:
        run(standin(), Path(a.out) if a.out else OUT / "standin", standin_run=True)
        return 0
    path = Path(a.forecasts) if Path(a.forecasts).is_absolute() else ROOT / a.forecasts
    if not path.exists():
        raise SystemExit(f"{_rel(path)}: not written yet (the study's scorer writes it once the arms are fitted)")
    run(path, Path(a.out) if a.out else OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
