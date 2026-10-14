"""Role A of the level-evidence system: which statistics depend on the opponent, by how much (gamma), and whether the
level effect is an opponent effect. Spec: docs/studies/lower_level_evidence/system/SPEC.md (§3, §4, §6.1).

The owner (9 Oct 2026): "identify wheter a statistic is independent of its opponent or dependent to figure out if it
qualifies for an offset depending on level of skill."

The measurement, per base statistic s and tour g:

    value     y = logit((x + 1/2) / (d + 1)) per box-score player-match (log for break points faced per service game),
              the builders' own scale (src/eda/ufc_ideas/stageB_common.py: stat_arrays, to_scale); x and d from Stage 0's
              player rows, the builders' definitions (stage4_features.stat_xd): own rates <s>_n / <s>_d; the return points
              against each serve from the opponent's first_won / second_won; the defence statistics (what servers do
              against this player) from the opponent's own row
    rows      main-tour main draws (bucket MAIN), completed, standard format, box score, units > 0
    strength  the opponent's pre-match overall Elo (Stage 1, retirements counted: the frozen reference's elo_overall);
              in 100s of Elo points
    model     y = gamma * opp_elo/100 + surface + player x season fixed effect, weighted by the units d;
              intervals clustered by player (CR1)

gamma(...) is the walk-forward version role B calls: rows whose result is in by `through` on the match clock
(lf + 1 <= through). It refuses to read an outcome of the 2025-2026 holdout unless allow_holdout=True (the SPEC's
mechanical fits for seasons 2025-2026, diagnostics unread).

Run:
    ./python.sh src/eda/lower_level_evidence/classify.py --strength      copy and check the strength file
    ./python.sh src/eda/lower_level_evidence/classify.py --demo          one gamma() call, timed
    ./python.sh src/eda/lower_level_evidence/classify.py --analysis      every table of the report, then the classes
Writes data/studies/lower_level_evidence/system/classes/.
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

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as C  # noqa: E402

METHOD_VERSION = "A-classify-2026-10-09.2"     # .2: gamma()'s default start 2011 (Elo's 2010 burn-in); else as .1
GAMMA_START = "2011-01-01"
OUT = C.OUT / "system" / "classes"
SANDBOX_PD = Path("C:/Users/zerom/tnr_lle/data/studies/predictability_diagnostic")   # the first run's sandbox: read only
ELO_SOURCE = SANDBOX_PD / "stage1_baselines.parquet"
STAGE3_SOURCE = SANDBOX_PD / "stage3_ratings.parquet"
STRENGTH = OUT / "strength_elo.parquet"            # role A's checked copy of the strength columns
STRENGTH_META = OUT / "strength_elo.json"
STRENGTH_COLS = ["match_id", "elo_a_ret", "elo_b_ret", "n_a_ret", "n_b_ret"]
L10 = np.log(10.0) / 400.0

LEVELS = ("TQ", "GSQ", "CH", "CHQ")
TOURS = ("atp", "wta")
SURFACES = ("Clay", "Grass", "Carpet")             # Hard (and the few unknown) is the base
YEARS = (2013, 2024)                               # outcomes read by the analysis
FIRST_BOX_YEAR = 2010
MAIN_LEVEL_CODES = ("GS", "FIN", "T1000", "T500", "T250")

OWN = ("spw", "rpw", "tpw", "hold", "brk", "ace", "df", "first_in", "first_won", "second_won", "bp_saved", "bp_conv",
       "bp_faced_pg")
# name: (side, how, source rate in Stage 0)
STATS = {
    "ace": ("serve", "own", "ace"), "df": ("serve", "own", "df"), "first_in": ("serve", "own", "first_in"),
    "first_won": ("serve", "own", "first_won"), "second_won": ("serve", "own", "second_won"),
    "spw": ("serve", "own", "spw"), "hold": ("serve", "own", "hold"), "bp_saved": ("serve", "own", "bp_saved"),
    "bp_faced_pg": ("serve", "own", "bp_faced_pg"),
    "rpw": ("return", "own", "rpw"), "rpw_first": ("return", "opp_complement", "first_won"),
    "rpw_second": ("return", "opp_complement", "second_won"), "brk": ("return", "own", "brk"),
    "bp_conv": ("return", "own", "bp_conv"),
    "tpw": ("none", "own", "tpw"),
    "def_ace": ("defence", "opp", "ace"), "def_df": ("defence", "opp", "df"),
    "def_first_in": ("defence", "opp", "first_in"), "def_bp_faced_pg": ("defence", "opp", "bp_faced_pg"),
}
LOG_SCALE = {"bp_faced_pg", "def_bp_faced_pg"}
# the opponent's counter-statistic: what the opponent's own history says about the other side of this statistic
COUNTER = {"ace": "def_ace", "df": "def_df", "first_in": "def_first_in", "bp_faced_pg": "def_bp_faced_pg",
           "spw": "rpw", "first_won": "rpw_first", "second_won": "rpw_second", "hold": "brk", "bp_saved": "bp_conv",
           "rpw": "spw", "rpw_first": "first_won", "rpw_second": "second_won", "brk": "hold", "bp_conv": "bp_saved",
           "tpw": "tpw", "def_ace": "ace", "def_df": "df", "def_first_in": "first_in",
           "def_bp_faced_pg": "bp_faced_pg"}
WORDS = {"ace": "aces per serve point", "df": "double faults per serve point", "first_in": "first serves in",
         "first_won": "first-serve points won", "second_won": "second-serve points won", "spw": "serve points won",
         "hold": "service games held", "bp_saved": "break points saved",
         "bp_faced_pg": "break points faced per service game", "rpw": "return points won",
         "rpw_first": "return points won against the first serve",
         "rpw_second": "return points won against the second serve", "brk": "breaks (return games won)",
         "bp_conv": "break points converted", "tpw": "total points won",
         "def_ace": "aces the opponents hit against the player", "def_df": "double faults the opponents serve against him",
         "def_first_in": "first serves in the opponents put in against him",
         "def_bp_faced_pg": "break points the opponents face per service game against him"}

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _phi(z: float) -> float:
    from math import erf, sqrt
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def to_scale(stat: str, p) -> np.ndarray:
    p = np.asarray(p, dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.log(p) if stat in LOG_SCALE else np.log(p) - np.log1p(-p)


def day_of(t) -> int:
    """A date (str, Timestamp) or a day number -> the match clock's day number (days since 1970-01-01)."""
    if isinstance(t, (int, np.integer)):
        return int(t)
    if isinstance(t, (float, np.floating)):
        return int(t)
    return int((pd.Timestamp(t) - pd.Timestamp("1970-01-01")).days)


def date_of(day) -> pd.Timestamp:
    return pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(day))


# ------------------------------------------------------------------------------------------------
# The strength file

def build_strength(source: Path = ELO_SOURCE, frame: Path = C.FRAME) -> dict:
    """Copy the reference's pre-match Elo (the strength scale) into role A's folder, after checking it against the frozen
    frame's elo_overall input (ln10/400 x (R_A - R_B), every frame match). Refuses if the check fails."""
    s = pd.read_parquet(source, columns=STRENGTH_COLS)
    fr = pd.read_parquet(frame, columns=["match_id", "in_elo_overall"])
    m = fr.merge(s, on="match_id", how="left", validate="one_to_one")
    if m["elo_a_ret"].isna().any():
        raise SystemExit(f"{int(m['elo_a_ret'].isna().sum())} frame matches have no Elo in {source}")
    d = np.abs(m["in_elo_overall"].to_numpy() - L10 * (m["elo_a_ret"].to_numpy(float) - m["elo_b_ret"].to_numpy(float)))
    if d.max() > 1e-5:
        raise SystemExit(f"Elo check failed: max |difference| {d.max():.3g} log-odds")
    OUT.mkdir(parents=True, exist_ok=True)
    s.to_parquet(STRENGTH, index=False)
    meta = {"written_at_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
            "source": str(source), "source_sha256": sha256(source), "columns": STRENGTH_COLS, "rows": int(len(s)),
            "copy_sha256": sha256(STRENGTH),
            "what": "Stage 1's pre-match overall Elo (retirements counted), every Stage 0 match of the frozen tables; "
                    "the chain's build in the first run's sandbox (tnr_lle), on the frozen tables",
            "check": {"frame": str(frame), "frame_matches": int(len(m)), "max_abs_diff_logodds": float(d.max()),
                      "rule": "in_elo_overall == ln(10)/400 * (elo_a_ret - elo_b_ret), same orientation",
                      "passed": True}}
    STRENGTH_META.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return meta


def strength_frame(path: Path = STRENGTH) -> pd.DataFrame:
    if not path.exists():
        raise SystemExit(f"{path} missing: run classify.py --strength")
    if path == STRENGTH and STRENGTH_META.exists():
        meta = json.loads(STRENGTH_META.read_text(encoding="utf-8"))
        if sha256(path) != meta["copy_sha256"]:
            raise SystemExit(f"{path} does not match {STRENGTH_META.name}")
    return pd.read_parquet(path, columns=STRENGTH_COLS)


# ------------------------------------------------------------------------------------------------
# Rows

MATCH_COLS = ["match_id", "tour", "year", "tournament_date", "map_level", "status", "format", "surface", "best_of",
              "round_order", "level", "tournament_id", "has_box"]


def match_table(stage0_dir: Path = C.STAGE0_DIR, timing: Path = C.TIMING) -> pd.DataFrame:
    """Stage 0's matches with the study's bucket and the match clock (es, lf as day numbers). Reads no outcome."""
    m = C.load_matches(stage0_dir, columns=MATCH_COLS)
    t = pd.read_parquet(timing, columns=["match_id", "es", "lf"])
    m = m.merge(t, on="match_id", how="left", validate="one_to_one")
    if m["es"].isna().any() or m["lf"].isna().any():
        raise SystemExit(f"{int(m['es'].isna().sum())} matches without a clock window in {timing}")
    m["es"] = m["es"].astype("int64")
    m["lf"] = m["lf"].astype("int64")
    m["box_ok"] = m["status"].eq("completed") & m["format"].eq("standard") & m["has_box"].fillna(False).astype(bool)
    return m


def player_rows(matches: pd.DataFrame, stage0_dir: Path = C.STAGE0_DIR, strength: pd.DataFrame | None = None,
                allow_holdout: bool = False) -> pd.DataFrame:
    """Two rows per match (the player, then the same match from the opponent's side), for the given matches only (a
    filtered read: no other match's box score reaches memory). Per row: the match's keys, the player's and the
    opponent's ids and pre-match Elo, and x_<s>, d_<s> for every base statistic (NaN where the row does not enter it)."""
    if not allow_holdout:
        C.assert_no_holdout_outcomes(matches["tournament_date"], "classify.player_rows")
    cols = ["match_id", "player_id", "opponent_id", "side", "won", "has_box"]
    for s in OWN:
        cols += [f"{s}_n", f"{s}_d"]
    pl = C.load_players(stage0_dir, columns=cols, match_ids=matches["match_id"])
    pl = pl.sort_values(["match_id", "side"], kind="mergesort").reset_index(drop=True)
    n_per = pl.groupby("match_id", sort=False).size()
    if not (n_per == 2).all():
        raise SystemExit(f"{int((n_per != 2).sum())} matches without exactly two player rows")
    if not (pl["side"].to_numpy()[0::2] == "A").all():
        raise SystemExit("player rows: side A not first")
    idx = np.arange(len(pl))
    opp = idx ^ 1
    mk = matches.set_index("match_id")
    keep = ["tour", "year", "tournament_date", "bucket", "surface", "es", "lf", "box_ok", "level", "round_order",
            "best_of", "tournament_id"]
    info = mk.loc[pl["match_id"].to_numpy(), keep].reset_index(drop=True)
    out = pd.concat([pl[["match_id", "player_id", "opponent_id", "side", "won"]].reset_index(drop=True), info], axis=1)
    if strength is None:
        strength = strength_frame()
    st = strength.set_index("match_id").reindex(pl["match_id"].to_numpy())
    a = pl["side"].eq("A").to_numpy()
    ea, eb = st["elo_a_ret"].to_numpy(float), st["elo_b_ret"].to_numpy(float)
    out["elo_own"] = np.where(a, ea, eb)
    out["elo_opp"] = np.where(a, eb, ea)
    na, nb = st["n_a_ret"].to_numpy(float), st["n_b_ret"].to_numpy(float)
    out["n_opp"] = np.where(a, nb, na)
    box = out["box_ok"].to_numpy() & pl["has_box"].fillna(False).to_numpy(bool) \
        & pl["has_box"].fillna(False).to_numpy(bool)[opp]
    for name, (_, how, src) in STATS.items():
        n = pl[f"{src}_n"].to_numpy(float)
        d = pl[f"{src}_d"].to_numpy(float)
        if how == "own":
            x, u = n, d
        elif how == "opp":
            x, u = n[opp], d[opp]
        else:                                   # the opponent's serve points of that kind, not won by him
            x, u = d[opp] - n[opp], d[opp]
        ok = box & np.isfinite(x) & np.isfinite(u) & (u > 0) & (x >= 0) & (x <= u if name not in LOG_SCALE else True)
        out[f"x_{name}"] = np.where(ok, x, np.nan)
        out[f"d_{name}"] = np.where(ok, u, np.nan)
    return out


def values(rows: pd.DataFrame, stat: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(y on the builders' scale, units d, ok) for one statistic."""
    x, d = rows[f"x_{stat}"].to_numpy(float), rows[f"d_{stat}"].to_numpy(float)
    ok = np.isfinite(x) & np.isfinite(d) & (d > 0)
    y = np.full(len(rows), np.nan)
    y[ok] = to_scale(stat, (x[ok] + 0.5) / (d[ok] + 1.0))
    ok &= np.isfinite(y)
    return y, d, ok


# ------------------------------------------------------------------------------------------------
# The within-player-season weighted regression with player-clustered intervals

def codes(*arrays) -> np.ndarray:
    if len(arrays) == 1:
        return pd.factorize(pd.Series(arrays[0]))[0]
    key = pd.MultiIndex.from_arrays([pd.Series(a).to_numpy() for a in arrays])
    return pd.factorize(key)[0]


def demean(v: np.ndarray, g: np.ndarray, w: np.ndarray, sw: np.ndarray) -> np.ndarray:
    if v.ndim == 1:
        return v - (np.bincount(g, weights=w * v, minlength=len(sw)) / sw)[g]
    return np.column_stack([demean(v[:, j], g, w, sw) for j in range(v.shape[1])])


def fe_wls(y: np.ndarray, w: np.ndarray, X: np.ndarray, group: np.ndarray, cluster: np.ndarray,
           controls: np.ndarray | None = None) -> dict:
    """Weighted least squares of y on X (and controls) after removing a fixed effect per group (exact within
    transformation). Returns the coefficients on X with a cluster-robust covariance (CR1: G/(G-1) (N-1)/(N-k); the
    groups nest in the clusters), the weighted sums of squares with and without X (for the partial R2), and counts."""
    X = np.atleast_2d(X.T).T if X.ndim == 1 else X
    k_x = X.shape[1]
    Z = X if controls is None or controls.shape[1] == 0 else np.column_stack([X, controls])
    group = pd.factorize(pd.Series(group))[0]
    cluster = pd.factorize(pd.Series(cluster))[0]
    sw = np.bincount(group, weights=w)
    yt = demean(y, group, w, sw)
    Zt = demean(Z, group, w, sw)
    keep = np.abs(Zt).sum(axis=0) > 1e-12            # a control constant within every group carries nothing
    if not keep[:k_x].all():
        raise ValueError("a regressor of interest has no within-group variation")
    Zt = Zt[:, keep]
    WZ = Zt * w[:, None]
    A = Zt.T @ WZ
    beta = np.linalg.solve(A, WZ.T @ yt)
    e = yt - Zt @ beta
    S = WZ * e[:, None]
    G = int(cluster.max()) + 1
    Sc = np.column_stack([np.bincount(cluster, weights=S[:, j], minlength=G) for j in range(S.shape[1])])
    Ainv = np.linalg.inv(A)
    n, k = len(y), Zt.shape[1]
    V = Ainv @ (Sc.T @ Sc) @ Ainv * (G / (G - 1.0)) * ((n - 1.0) / (n - k))
    ssr = float(np.sum(w * e ** 2))
    if Zt.shape[1] > k_x:                            # controls only
        Zc = Zt[:, k_x:]
        bc = np.linalg.lstsq(Zc * np.sqrt(w)[:, None], yt * np.sqrt(w), rcond=None)[0]
        ssr0 = float(np.sum(w * (yt - Zc @ bc) ** 2))
    else:
        ssr0 = float(np.sum(w * yt ** 2))
    return {"beta": beta[:k_x], "V": V[:k_x, :k_x], "ssr": ssr, "ssr0": ssr0, "sst_within": float(np.sum(w * yt ** 2)),
            "n": n, "groups": int(group.max()) + 1, "clusters": G, "resid": e, "yt": yt, "Xt": Zt[:, :k_x]}


def surface_dummies(surface: pd.Series | np.ndarray) -> np.ndarray:
    s = pd.Series(surface).astype("string").fillna("Hard").to_numpy()
    return np.column_stack([(s == v).astype(float) for v in SURFACES])


# ------------------------------------------------------------------------------------------------
# gamma(): the walk-forward function role B calls

_CACHE: dict = {}


def _main_rows(through_day: int, start_day: int, stage0_dir: Path, timing: Path, strength_path: Path,
               allow_holdout: bool) -> pd.DataFrame:
    key = (str(stage0_dir), str(timing), str(strength_path))
    if key not in _CACHE:
        _CACHE[key] = {"matches": match_table(stage0_dir, timing), "rows": {}}
    cache = _CACHE[key]
    m = cache["matches"]
    sel = m["bucket"].eq("MAIN") & m["box_ok"] & ((m["lf"] + 1) <= through_day) \
        & (m["tournament_date"] >= date_of(start_day))
    want = m.loc[sel]
    hold = C.in_holdout(want["tournament_date"])
    if hold.any() and not allow_holdout:
        raise PermissionError(f"gamma(through={date_of(through_day).date()}): {int(hold.sum())} main-tour matches of the "
                              "2025-2026 holdout would have their outcome read; pass allow_holdout=True only for the "
                              "SPEC's mechanical walk-forward fits (diagnostics unread)")
    parts = []
    for part, ids in (("pre", want.loc[~hold.to_numpy()]), ("hold", want.loc[hold.to_numpy()])):
        if ids.empty:
            continue
        if part not in cache["rows"]:
            base = m.loc[m["bucket"].eq("MAIN") & m["box_ok"]
                         & (C.in_holdout(m["tournament_date"]) == (part == "hold"))]
            cache["rows"][part] = player_rows(base, stage0_dir, strength_frame(strength_path),
                                              allow_holdout=(part == "hold"))
        r = cache["rows"][part]
        parts.append(r[r["match_id"].isin(set(ids["match_id"]))])
    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def fit_gamma(rows: pd.DataFrame, stat: str, extra_controls: np.ndarray | None = None) -> dict:
    """One statistic, one set of rows (one tour): gamma per 100 Elo of the opponent, within player x season."""
    y, d, ok = values(rows, stat)
    ok &= np.isfinite(rows["elo_opp"].to_numpy(float))
    r = rows.loc[ok]
    ctrl = surface_dummies(r["surface"])
    if extra_controls is not None:
        ctrl = np.column_stack([ctrl, extra_controls[ok]])
    empty = {"gamma": np.nan, "se": np.nan, "gamma_lo": np.nan, "gamma_hi": np.nan, "n_rows": int(ok.sum()),
             "n_player_seasons": 0, "n_players": 0, "partial_r2": np.nan, "sd_match": np.nan,
             "_res": None, "_y": y[ok], "_d": d[ok], "_rows": r}
    if ok.sum() < 3:
        return empty
    try:
        res = fe_wls(y[ok], d[ok], r["elo_opp"].to_numpy(float) / 100.0,
                     codes(r["player_id"].to_numpy(), r["year"].to_numpy()), r["player_id"].to_numpy(), ctrl)
    except (ValueError, np.linalg.LinAlgError):       # no within-player-season variation (a statistic not recorded)
        return empty
    g, se = float(res["beta"][0]), float(np.sqrt(res["V"][0, 0]))
    return {"gamma": g, "se": se, "gamma_lo": g - 1.96 * se, "gamma_hi": g + 1.96 * se, "n_rows": int(res["n"]),
            "n_player_seasons": res["groups"], "n_players": res["clusters"],
            "partial_r2": (res["ssr0"] - res["ssr"]) / res["ssr0"] if res["ssr0"] > 0 else np.nan,
            "sd_match": float(np.std(y[ok])), "_res": res, "_y": y[ok], "_d": d[ok], "_rows": r}


def gamma(through, tours=TOURS, stats=None, start=GAMMA_START, stage0_dir: Path = C.STAGE0_DIR,
          timing: Path = C.TIMING, strength_path: Path = STRENGTH, allow_holdout: bool = False) -> pd.DataFrame:
    """gamma per base statistic and tour, from main-tour box scores whose results are in by `through` on the match clock.

    through        a date or a match-clock day number: rows with lf + 1 <= through enter (a result is in at lf + 1).
                   For season Y use season_cutoff(Y): the earliest possible start of season Y's first main-tour match.
    tours, stats   subsets (default: both tours, every base statistic of STATS)
    start          the first tournament date used (default 2011-01-01). 2010 is left out: Stage 1's Elo starts every
                   player at 1500 in January 2010, and in 2010 its noise halves gamma (men's total points -0.031 per
                   100 Elo against -0.053 to -0.061 in every season 2011-2024; gamma_by_season.csv). The report's
                   analysis uses 2013-2024
    allow_holdout  False (default) refuses if a 2025-2026 outcome would be read. True only for the SPEC's mechanical
                   walk-forward fits of seasons 2025-2026, whose diagnostics stay unread before the holdout readout

    Returns one row per (tour, stat): gamma (logit units, or log units for break points faced per service game, per 100
    Elo of the opponent's pre-match Elo), se, gamma_lo, gamma_hi (95%, clustered by player), n_rows, n_player_seasons,
    n_players, partial_r2, sd_match, side, through, start, last_result_day (the latest lf + 1 used), strength_source,
    method_version. Within player x season, surface held fixed, weighted by the statistic's units."""
    through_day, start_day = day_of(through), day_of(start)
    rows = _main_rows(through_day, start_day, Path(stage0_dir), Path(timing), Path(strength_path), allow_holdout)
    stats = list(STATS) if stats is None else list(stats)
    out = []
    for g in tours:
        r = rows[rows["tour"].eq(g)] if len(rows) else rows
        for s in stats:
            base = {"tour": g, "stat": s, "side": STATS[s][0], "through": date_of(through_day).date().isoformat(),
                    "start": date_of(start_day).date().isoformat(), "gamma_unit": "log" if s in LOG_SCALE else "logit",
                    "strength_source": f"{Path(strength_path).name}: elo_a_ret / elo_b_ret (opponent's pre-match Elo, "
                                       "per 100 points)", "method_version": METHOD_VERSION}
            if len(r) == 0:
                out.append({**base, "gamma": np.nan, "n_rows": 0})
                continue
            f = fit_gamma(r, s)
            last = date_of(int(f["_rows"]["lf"].max()) + 1).date().isoformat() if len(f["_rows"]) else None
            out.append({**base, **{k: v for k, v in f.items() if not k.startswith("_")}, "last_result_day": last})
    return pd.DataFrame(out)


def season_cutoff(season: int, stage0_dir: Path = C.STAGE0_DIR, timing: Path = C.TIMING) -> pd.Timestamp:
    """The earliest possible start (es) of season Y's first main-tour match: parameters for season Y are fitted on
    results in by that day (lf + 1 <= cutoff). Reads no outcome."""
    key = (str(stage0_dir), str(timing), "cut")
    if key not in _CACHE:
        m = match_table(stage0_dir, timing)
        _CACHE[key] = m.loc[m["bucket"].eq("MAIN")].groupby("year")["es"].min()
    s = _CACHE[key]
    if season not in s.index:
        raise KeyError(f"no main-tour match in season {season}")
    return date_of(int(s.loc[season]))


# ------------------------------------------------------------------------------------------------
# The analysis behind the report (outcomes of 2013-2024 only)

def analysis_rows(stage0_dir: Path = C.STAGE0_DIR, timing: Path = C.TIMING) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Every box-score-eligible match of 2010-2024 (events before the holdout), every level, both sides."""
    m = match_table(stage0_dir, timing)
    pre = m.loc[m["box_ok"] & ~C.in_holdout(m["tournament_date"]) & m["year"].between(FIRST_BOX_YEAR, YEARS[1])]
    C.assert_no_holdout_outcomes(pre["tournament_date"], "classify.analysis_rows")
    rows = player_rows(pre, stage0_dir, strength_frame())
    return m, rows


def sd_signal(rows: pd.DataFrame, stat: str, min_matches: int = 5) -> float:
    """Between-player-season SD of the statistic's true value on the main tour (logit), net of sampling noise."""
    y, d, ok = values(rows, stat)
    r = rows.loc[ok, ["player_id", "year"]].copy()
    r["x"] = rows.loc[ok, f"x_{stat}"].to_numpy()
    r["d"] = d[ok]
    g = r.groupby(["player_id", "year"]).agg(x=("x", "sum"), d=("d", "sum"), n=("x", "size"))
    g = g[g["n"] >= min_matches]
    p = (g["x"] + 0.5) / (g["d"] + 1.0)
    v = to_scale(stat, p)
    if stat in LOG_SCALE:
        samp = 1.0 / (g["x"] + 0.5)
    else:
        samp = 1.0 / ((g["d"] + 1.0) * p * (1 - p))
    tot = float(np.var(v))
    return float(np.sqrt(max(0.0, tot - float(np.mean(samp)))))


def main_tour(rows: pd.DataFrame, tour: str, years=YEARS) -> pd.DataFrame:
    return rows[rows["tour"].eq(tour) & rows["bucket"].eq("MAIN") & rows["year"].between(*years)]


def table_gamma(rows: pd.DataFrame) -> pd.DataFrame:
    out = []
    for g in TOURS:
        mt = main_tour(rows, g)
        for s in STATS:
            f = fit_gamma(mt, s)
            sdo = float(np.std(f["_rows"]["elo_opp"].to_numpy() / 100.0))
            sig = sd_signal(mt, s)
            out.append({"tour": g, "stat": s, "side": STATS[s][0], "words": WORDS[s],
                        **{k: v for k, v in f.items() if not k.startswith("_")},
                        "unit": "log per 100 Elo" if s in LOG_SCALE else "logit per 100 Elo",
                        "gamma_per_sd_match": f["gamma"] / f["sd_match"],
                        "sd_opp_elo_100": sdo, "std_effect": f["gamma"] * sdo / f["sd_match"],
                        "sd_signal": sig, "gamma_per_sd_signal": f["gamma"] / sig if sig > 0 else np.nan,
                        "mean_rate": float(np.average(1 / (1 + np.exp(-f["_y"])) if s not in LOG_SCALE
                                                      else np.exp(f["_y"]), weights=f["_d"]))})
            log(f"  gamma {g} {s}: {f['gamma']:+.4f} [{f['gamma_lo']:+.4f}, {f['gamma_hi']:+.4f}] "
                f"partial R2 {out[-1]['partial_r2']:.4f}")
    return pd.DataFrame(out)


def table_by_season(rows: pd.DataFrame) -> pd.DataFrame:
    """gamma in each single season 2010-2024 (main tour): the stability check behind gamma()'s start year."""
    out = []
    for g in TOURS:
        for y in range(FIRST_BOX_YEAR, YEARS[1] + 1):
            r = rows[rows["tour"].eq(g) & rows["bucket"].eq("MAIN") & rows["year"].eq(y)]
            for s in STATS:
                f = fit_gamma(r, s)
                out.append({"tour": g, "year": y, "stat": s, "gamma": f["gamma"], "se": f["se"],
                            "n_rows": f["n_rows"], "sd_opp_elo": float(np.std(r["elo_opp"]))})
    return pd.DataFrame(out)


def table_robust(rows: pd.DataFrame) -> pd.DataFrame:
    """gamma by era (2013-2018, 2019-2024), with event level and round held fixed, and inside the Challengers."""
    out = []
    for g in TOURS:
        for s in STATS:
            specs = {}
            for era, yrs in (("2013-2018", (2013, 2018)), ("2019-2024", (2019, 2024))):
                specs[era] = fit_gamma(main_tour(rows, g, yrs), s)
            mt = main_tour(rows, g)
            lv = pd.get_dummies(mt["level"].astype(str)).to_numpy(float)
            rd = pd.get_dummies(mt["round_order"].astype(str)).to_numpy(float)
            specs["level+round"] = fit_gamma(mt, s, np.column_stack([lv, rd]))
            for L in ("CH", "TQ"):
                lr = rows[rows["tour"].eq(g) & rows["bucket"].eq(L) & rows["year"].between(*YEARS)]
                try:
                    specs[f"inside_{L}"] = fit_gamma(lr, s)
                except (ValueError, np.linalg.LinAlgError):
                    pass
            row = {"tour": g, "stat": s}
            for k, f in specs.items():
                row[f"gamma_{k}"] = f["gamma"]
                row[f"se_{k}"] = f["se"]
                row[f"n_{k}"] = f["n_rows"]
            a, b = specs["2013-2018"], specs["2019-2024"]
            row["era_diff"] = b["gamma"] - a["gamma"]
            row["era_diff_se"] = float(np.hypot(a["se"], b["se"]))
            out.append(row)
        log(f"  robustness {g} done")
    return pd.DataFrame(out)


def clock_history(rows: pd.DataFrame, stat: str, tour: str, days: int = 365, k_matches: float = 5.0) -> tuple:
    """Per player: sorted (lf, cumulative x, cumulative d) of his rows of `stat` (every level), for the clock lookup:
    a target at es reads rows with lf + 1 <= es and lf >= es - days. Per player's own matches, every level."""
    y, d, ok = values(rows, stat)
    r = rows.loc[ok & rows["tour"].eq(tour).to_numpy(), ["player_id", "lf"]].copy()
    r["x"] = rows.loc[r.index, f"x_{stat}"].to_numpy(float)
    r["d"] = rows.loc[r.index, f"d_{stat}"].to_numpy(float)
    mu = float(r.loc[rows.loc[r.index, "year"].between(2010, 2018), "x"].sum()
               / r.loc[rows.loc[r.index, "year"].between(2010, 2018), "d"].sum())
    k = k_matches * float(r["d"].mean())
    return r, mu, k


def counter_values(hist: pd.DataFrame, mu: float, k: float, stat: str, who: np.ndarray, es: np.ndarray,
                   days: int = 365) -> np.ndarray:
    """The shrunk pooled rate of `who`'s rows with es - days <= lf <= es - 1 (in at lf + 1 <= es), on the scale."""
    pid = pd.Index(pd.unique(np.concatenate([hist["player_id"].to_numpy(), who])))
    hc = pid.get_indexer(hist["player_id"].to_numpy()).astype(np.int64)
    big = np.int64(1 << 20)
    key = hc * big + hist["lf"].to_numpy(np.int64)
    o = np.argsort(key, kind="mergesort")
    key = key[o]
    cx = np.r_[0.0, np.cumsum(hist["x"].to_numpy(float)[o])]
    cd = np.r_[0.0, np.cumsum(hist["d"].to_numpy(float)[o])]
    wc = pid.get_indexer(who).astype(np.int64)
    hi = np.searchsorted(key, wc * big + (es.astype(np.int64) - 1), side="right")
    lo = np.searchsorted(key, wc * big + (es.astype(np.int64) - days), side="left")
    sx, sd = cx[hi] - cx[lo], cd[hi] - cd[lo]
    return to_scale(stat, (sx + k * mu) / (sd + k))


def table_counter(rows: pd.DataFrame, stage3: pd.DataFrame | None) -> pd.DataFrame:
    """Within player-season partial R2 of the opponent's Elo, of his counter-statistic (the leak-free 365-day shrunk
    running rate of his own earlier rows, every level, on the match clock), and of both; for the points statistics also
    the opponent's Stage 3 rating (one scale, every level)."""
    out = []
    for g in TOURS:
        mt = main_tour(rows, g)
        for s in STATS:
            cs = COUNTER[s]
            hist, mu, k = clock_history(rows, cs, g)
            # the counter-statistic of the OPPONENT: his rows of cs are the rows where he is the player
            cv = counter_values(hist, mu, k, cs, mt["opponent_id"].to_numpy(), mt["es"].to_numpy())
            y, d, ok = values(mt, s)
            ok &= np.isfinite(cv)
            r = mt.loc[ok]
            grp = codes(r["player_id"].to_numpy(), r["year"].to_numpy())
            ctrl = surface_dummies(r["surface"])
            el = r["elo_opp"].to_numpy(float) / 100.0
            c = cv[ok]
            fits = {"elo": np.column_stack([el]), "counter": np.column_stack([c]), "both": np.column_stack([el, c])}
            if stage3 is not None and s in ("spw", "rpw", "tpw", "first_won", "second_won", "rpw_first",
                                            "rpw_second", "hold", "brk"):
                s3 = stage3.reindex(r["match_id"].to_numpy())
                a = r["side"].eq("A").to_numpy()
                opp_ret = np.where(a, s3["return_b"].to_numpy(float), s3["return_a"].to_numpy(float))
                opp_srv = np.where(a, s3["serve_b"].to_numpy(float), s3["serve_a"].to_numpy(float))
                ok3 = np.isfinite(opp_ret) & np.isfinite(opp_srv)
                if ok3.all():
                    fits["stage3"] = np.column_stack([opp_srv, opp_ret])
                    fits["elo+stage3"] = np.column_stack([el, opp_srv, opp_ret])
            row = {"tour": g, "stat": s, "counter": cs, "n_rows": int(ok.sum())}
            for name, X in fits.items():
                res = fe_wls(y[ok], d[ok], X, grp, r["player_id"].to_numpy(), ctrl)
                row[f"r2_{name}"] = (res["ssr0"] - res["ssr"]) / res["ssr0"]
                if name == "both":
                    row["gamma_elo_given_counter"] = float(res["beta"][0])
                    row["se_elo_given_counter"] = float(np.sqrt(res["V"][0, 0]))
            out.append(row)
        log(f"  counter-skill {g} done")
    return pd.DataFrame(out)


def level_panel(rows: pd.DataFrame, tour: str, level: str, stat: str | None, min_rows: int = 3) -> pd.DataFrame:
    """Player-seasons with >= min_rows box scores at MAIN and at `level` (of `stat`, or of serve points for the
    statistic-free gap), 2013-2024: per level, the units-weighted means of the value and of the opponent's Elo."""
    sel = rows["tour"].eq(tour) & rows["bucket"].isin(["MAIN", level]) & rows["year"].between(*YEARS)
    r = rows.loc[sel]
    s = stat or "spw"
    y, d, ok = values(r, s)
    ok &= np.isfinite(r["elo_opp"].to_numpy(float))
    w = d if stat else np.ones(len(r))
    t = pd.DataFrame({"player_id": r["player_id"].to_numpy()[ok], "year": r["year"].to_numpy()[ok],
                      "lev": np.where(r["bucket"].to_numpy()[ok] == "MAIN", "M", "L"), "w": w[ok],
                      "wy": (w * np.nan_to_num(y))[ok], "we": (w * r["elo_opp"].to_numpy(float))[ok] / 100.0})
    a = t.groupby(["player_id", "year", "lev"]).agg(w=("w", "sum"), wy=("wy", "sum"), we=("we", "sum"),
                                                    n=("w", "size")).unstack("lev")
    a = a.dropna()
    a = a[(a[("n", "M")] >= min_rows) & (a[("n", "L")] >= min_rows)]
    p = pd.DataFrame({"player_id": a.index.get_level_values(0), "year": a.index.get_level_values(1),
                      "dy": (a[("wy", "L")] / a[("w", "L")] - a[("wy", "M")] / a[("w", "M")]).to_numpy(),
                      "de": (a[("we", "L")] / a[("w", "L")] - a[("we", "M")] / a[("w", "M")]).to_numpy()})
    return p


def cluster_mean(v: np.ndarray, cl: np.ndarray) -> tuple[float, float]:
    """Mean of v (equal weights) and its standard error clustered by cl."""
    m = float(np.mean(v))
    c = pd.factorize(pd.Series(cl))[0]
    s = np.bincount(c, weights=v - m)
    G, n = len(s), len(v)
    se = float(np.sqrt(np.sum(s ** 2) * G / (G - 1.0)) / n) if G > 1 else np.nan
    return m, se


def table_levels(rows: pd.DataFrame, gam: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Per statistic, tour and level: the raw same-player shift R, the opponent part gamma x Delta, the residual delta."""
    gaps = []
    for g in TOURS:
        for L in LEVELS:
            p = level_panel(rows, g, L, None)
            n_rows = int((rows["tour"].eq(g) & rows["bucket"].eq(L) & rows["year"].between(*YEARS)
                          & np.isfinite(rows["d_spw"].to_numpy(float))).sum())
            if len(p) == 0:
                gaps.append({"tour": g, "level": L, "n_ps": 0, "delta_elo_100": np.nan, "se": np.nan,
                             "box_rows": n_rows})
                continue
            m, se = cluster_mean(p["de"].to_numpy(), p["player_id"].to_numpy())
            gaps.append({"tour": g, "level": L, "n_ps": int(len(p)), "delta_elo_100": m, "se": se,
                         "box_rows": n_rows})
    gaps = pd.DataFrame(gaps)
    out = []
    gi = gam.set_index(["tour", "stat"])
    for g in TOURS:
        for s in STATS:
            gm, gse = float(gi.loc[(g, s), "gamma"]), float(gi.loc[(g, s), "se"])
            for L in LEVELS:
                p = level_panel(rows, g, L, s)
                row = {"tour": g, "stat": s, "level": L, "n_ps": int(len(p))}
                if len(p) < 2:
                    out.append(row)
                    continue
                cl = p["player_id"].to_numpy()
                R, Rse = cluster_mean(p["dy"].to_numpy(), cl)
                D, Dse = cluster_mean(p["de"].to_numpy(), cl)
                res, rse = cluster_mean(p["dy"].to_numpy() - gm * p["de"].to_numpy(), cl)
                rse = float(np.hypot(rse, D * gse))
                row.update({"raw_shift": R, "raw_lo": R - 1.96 * Rse, "raw_hi": R + 1.96 * Rse,
                            "delta_elo_100": D, "explained": gm * D, "explained_share": gm * D / R if R != 0 else np.nan,
                            "residual": res, "residual_lo": res - 1.96 * rse, "residual_hi": res + 1.96 * rse})
                out.append(row)
        log(f"  level decomposition {g} done")
    return gaps, pd.DataFrame(out)


def table_levels_stage3(rows: pd.DataFrame, stage3: pd.DataFrame, lev_elo: pd.DataFrame) -> pd.DataFrame:
    """The level decomposition of the points statistics with a statistic-specific strength on one scale: the opponent's
    Stage 3 ratings (pre-match, every level, joint online solve). serve points won: his return rating; return points
    won: his serve rating; total points won: both. Beside Elo's explained share from table_levels."""
    s3 = stage3.reindex(rows["match_id"].to_numpy())
    a = rows["side"].eq("A").to_numpy()
    r = rows.copy()
    r["opp_srv"] = np.where(a, s3["serve_b"].to_numpy(float), s3["serve_a"].to_numpy(float))
    r["opp_ret"] = np.where(a, s3["return_b"].to_numpy(float), s3["return_a"].to_numpy(float))
    spec = {"spw": ["opp_ret"], "rpw": ["opp_srv"], "tpw": ["opp_srv", "opp_ret"]}
    out = []
    for g in TOURS:
        mt = main_tour(r, g)
        for s, cols in spec.items():
            y, d, ok = values(mt, s)
            X = mt[cols].to_numpy(float)
            ok &= np.isfinite(X).all(axis=1)
            res = fe_wls(y[ok], d[ok], X[ok], codes(mt["player_id"].to_numpy()[ok], mt["year"].to_numpy()[ok]),
                         mt["player_id"].to_numpy()[ok], surface_dummies(mt["surface"].to_numpy()[ok]))
            beta, V = res["beta"], res["V"]
            for L in LEVELS:
                sel = r["tour"].eq(g) & r["bucket"].isin(["MAIN", L]) & r["year"].between(*YEARS)
                q = r.loc[sel]
                yq, dq, okq = values(q, s)
                Xq = q[cols].to_numpy(float)
                okq &= np.isfinite(Xq).all(axis=1)
                t = pd.DataFrame({"player_id": q["player_id"].to_numpy()[okq], "year": q["year"].to_numpy()[okq],
                                  "lev": np.where(q["bucket"].to_numpy()[okq] == "MAIN", "M", "L"), "w": dq[okq],
                                  "wy": (dq * np.nan_to_num(yq))[okq]})
                for j, c in enumerate(cols):
                    t[f"wx{j}"] = (dq * np.nan_to_num(Xq[:, j]))[okq]
                agg = {"w": ("w", "sum"), "wy": ("wy", "sum"), "n": ("w", "size")}
                agg.update({f"wx{j}": (f"wx{j}", "sum") for j in range(len(cols))})
                p = t.groupby(["player_id", "year", "lev"]).agg(**agg).unstack("lev").dropna()
                p = p[(p[("n", "M")] >= 3) & (p[("n", "L")] >= 3)]
                if len(p) < 100:
                    continue
                dy = (p[("wy", "L")] / p[("w", "L")] - p[("wy", "M")] / p[("w", "M")]).to_numpy()
                dx = np.column_stack([(p[(f"wx{j}", "L")] / p[("w", "L")] - p[(f"wx{j}", "M")] / p[("w", "M")])
                                      .to_numpy() for j in range(len(cols))])
                cl = p.index.get_level_values(0).to_numpy()
                R, Rse = cluster_mean(dy, cl)
                E = float(dx.mean(axis=0) @ beta)
                resid, rse = cluster_mean(dy - dx @ beta, cl)
                dm = dx.mean(axis=0)
                rse = float(np.sqrt(rse ** 2 + dm @ V @ dm))
                e_elo = lev_elo[lev_elo["tour"].eq(g) & lev_elo["stat"].eq(s) & lev_elo["level"].eq(L)]
                out.append({"tour": g, "stat": s, "level": L, "strength": "+".join(cols), "n_ps": int(len(p)),
                            "raw_shift": R, "explained_stage3": E, "share_stage3": E / R if R else np.nan,
                            "residual_stage3": resid, "residual_lo": resid - 1.96 * rse,
                            "residual_hi": resid + 1.96 * rse,
                            "share_elo": float(e_elo["explained_share"].iloc[0]) if len(e_elo) else np.nan,
                            "residual_elo": float(e_elo["residual"].iloc[0]) if len(e_elo) else np.nan})
    return pd.DataFrame(out)


def table_results(rows: pd.DataFrame) -> pd.DataFrame:
    """A check of the machinery on results: within player-season, the win (0/1) on the opponent's Elo, beside the same
    regression of Elo's own expectation. If Elo is calibrated inside the main tour the two slopes agree."""
    out = []
    for g in TOURS:
        mt = main_tour(rows, g)
        mt = mt[np.isfinite(mt["elo_own"].to_numpy(float)) & np.isfinite(mt["elo_opp"].to_numpy(float))]
        won = mt["won"].astype(float).to_numpy()
        expd = 1.0 / (1.0 + 10.0 ** ((mt["elo_opp"].to_numpy(float) - mt["elo_own"].to_numpy(float)) / 400.0))
        grp = codes(mt["player_id"].to_numpy(), mt["year"].to_numpy())
        X = mt["elo_opp"].to_numpy(float) / 100.0
        ctrl = surface_dummies(mt["surface"])
        a = fe_wls(won, np.ones(len(mt)), X, grp, mt["player_id"].to_numpy(), ctrl)
        b = fe_wls(expd, np.ones(len(mt)), X, grp, mt["player_id"].to_numpy(), ctrl)
        out.append({"tour": g, "n_rows": len(mt), "slope_win": float(a["beta"][0]),
                    "se_win": float(np.sqrt(a["V"][0, 0])), "slope_elo_expectation": float(b["beta"][0]),
                    "se_elo_expectation": float(np.sqrt(b["V"][0, 0])), "unit": "probability per 100 Elo"})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------
# Serve speed (stage 2)

def speed_checks(strength: pd.DataFrame) -> dict:
    """First-serve speed: the gradient on the opponent's Elo inside the main tour, and the same player's Challenger
    speed against his main-tour speed, raw and after stage 2's edition centring (the season-end snapshot). Men only;
    rows of events before the holdout."""
    from src.eda.serve_speed_tabpfn import panel as SP
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    full = LP.frozen_panel()
    counts = (full[full["tour"].eq("atp") & full["use"].astype(bool) & full["level"].eq("CH")]
              .groupby("year").size().to_dict())
    p = full[full["tour"].eq("atp") & full["use"].astype(bool)].copy()
    p = p[~C.in_holdout(p["tournament_date"]) & (p["year"] <= YEARS[1])].copy()
    C.assert_no_holdout_outcomes(p["tournament_date"], "classify.speed_checks")
    st = strength.set_index("match_id").reindex(p["match_id"].to_numpy())
    a = p["side"].eq("A").to_numpy()
    p["elo_opp"] = np.where(a, st["elo_b_ret"].to_numpy(float), st["elo_a_ret"].to_numpy(float))
    p["lvl"] = np.where(p["level"].isin(MAIN_LEVEL_CODES) & ~p["qualifying"].astype(bool), "MAIN",
                        np.where(p["level"].eq("CH") & ~p["qualifying"].astype(bool), "CH",
                                 np.where(p["level"].eq("CH"), "CHQ", "OTHER")))
    # stage 2's centring: the edition offsets as of each season's end, from rows released by then (all before the holdout)
    eo = SP.EditionOffsets(full, "atp", cache=False)
    p["gamma_ed"] = np.nan
    for y in sorted(p["year"].unique()):
        day = day_of(f"{y}-12-28")
        k = p["year"].eq(y).to_numpy()
        p.loc[k, "gamma_ed"] = eo.gamma(p.loc[k, "edition"].to_numpy(), day)
    p["y_c"] = p["y"] - p["gamma_ed"]
    w = 1.0 / (SP.TAU2 + SP.S_SERVE ** 2 / np.maximum(p["n"].to_numpy(float), 1.0))
    p["w"] = w
    out = {"challenger_rows_by_year_usable": {int(k): int(v) for k, v in counts.items()},
           "constants": {"tau2": SP.TAU2, "s": SP.S_SERVE, "spd_L_standardiser_kmh": 1.9496051535048338}}
    # the gradient on the opponent's Elo inside the main tour (player x season fixed effects; basis held fixed)
    mt = p[p["lvl"].eq("MAIN") & np.isfinite(p["elo_opp"]) & p["year"].between(*YEARS)]
    basis = (mt["basis"].astype(str) == "ks").to_numpy(float)[:, None]
    grad = {}
    lv_rd = np.column_stack([pd.get_dummies(mt["level"].astype(str)).to_numpy(float),
                             pd.get_dummies(mt["round_order"].astype(str)).to_numpy(float)])
    for col, extra in (("y", None), ("y_c", None), ("y_c_level_round", lv_rd)):
        ctrl = np.column_stack([surface_dummies(mt["surface"]), basis])
        if extra is not None:
            ctrl = np.column_stack([ctrl, extra])
        res = fe_wls(mt[col.split("_level")[0]].to_numpy(float), mt["w"].to_numpy(),
                     mt["elo_opp"].to_numpy(float) / 100.0,
                     codes(mt["player_id"].to_numpy(), mt["year"].to_numpy()), mt["player_id"].to_numpy(), ctrl)
        b, se = float(res["beta"][0]), float(np.sqrt(res["V"][0, 0]))
        grad[col] = {"gamma_kmh_per_100_elo": b, "lo": b - 1.96 * se, "hi": b + 1.96 * se, "n_rows": res["n"],
                     "partial_r2": (res["ssr0"] - res["ssr"]) / res["ssr0"]}
    grad["sd_match_kmh"] = float(mt["y"].std())
    ps = mt.groupby(["player_id", "year"])["y"].agg(["mean", "size"])
    grad["sd_between_player_seasons_kmh"] = float(ps.loc[ps["size"] >= 5, "mean"].std())
    out["gradient_main_tour"] = grad
    # the same player, Challenger (main draw; and with qualifying) against main tour, same season
    comp = {}
    for name, levs in (("CH", ["CH"]), ("CH+CHQ", ["CH", "CHQ"])):
        r = p[p["lvl"].isin(["MAIN"] + levs)].copy()
        r["L"] = np.where(r["lvl"].eq("MAIN"), "M", "L")
        res_n = {}
        for min_rows in (1, 2):
            agg = {}
            for col in ("y", "y_c", "elo_opp"):
                r["wv"] = r["w"] * r[col]
                a2 = r.groupby(["player_id", "year", "L"]).agg(w=("w", "sum"), wv=("wv", "sum"), n=("w", "size"))
                a2 = a2.unstack("L").dropna()
                a2 = a2[(a2[("n", "M")] >= min_rows) & (a2[("n", "L")] >= min_rows)]
                agg[col] = (a2[("wv", "L")] / a2[("w", "L")] - a2[("wv", "M")] / a2[("w", "M")])
            pl = agg["y"].index.get_level_values(0).to_numpy()
            entry = {"player_seasons": int(len(pl)), "players": int(len(np.unique(pl)))}
            for col, lab in (("y", "raw_kmh"), ("y_c", "centred_kmh"), ("elo_opp", "opp_elo_gap_points")):
                v = agg[col].to_numpy(float)
                ok = np.isfinite(v)
                if ok.sum() >= 2:
                    m_, se_ = cluster_mean(v[ok], pl[ok])
                    entry[lab] = {"mean": m_, "lo": m_ - 1.96 * se_, "hi": m_ + 1.96 * se_,
                                  "p_positive": float(_phi(m_ / se_)) if se_ > 0 else np.nan}
            res_n[f"min_{min_rows}_rows_each"] = entry
        comp[name] = res_n
    out["challenger_vs_main_same_player_season"] = comp
    # where the Challenger editions' offsets come from: own fit or the family mean, at the season-end snapshot
    ch = p[p["lvl"].isin(["CH", "CHQ"])]
    out["challenger_edition_offsets"] = {
        "rows": int(len(ch)), "mean_gamma_ed_kmh": float(ch["gamma_ed"].mean()),
        "mean_raw_kmh": float(ch["y"].mean()), "mean_centred_kmh": float(ch["y_c"].mean()),
        "main_mean_raw_kmh": float(mt["y"].mean()), "main_mean_centred_kmh": float(mt["y_c"].mean())}
    return out


# ------------------------------------------------------------------------------------------------
# The classes

INPUTS = [
    # name, base statistics, side, family
    ("odds_logit", "", "none", "market"),
    ("ratings_iid", "spw+rpw", "serve+return", "online_point_ratings"),
    ("elo_games", "results", "none", "results_ratings"),
    ("adjperf_tpw_2w", "tpw", "none", "one_step_forms"),
    ("ios_points_short", "spw+rpw", "serve+return", "joint_solves"),
    ("points_52w", "spw+rpw", "serve+return", "raw_rates"),
    ("sets_14d", "workload", "none", "workload"),
    ("age", "age", "none", "intrinsic"), ("age_sq", "age", "none", "intrinsic"),
    ("form_ace", "ace", "serve", "one_step_forms"), ("form_df", "df", "serve", "one_step_forms"),
    ("form_first_in", "first_in", "serve", "one_step_forms"),
    ("form_first_won", "first_won", "serve", "one_step_forms"),
    ("form_second_won", "second_won", "serve", "one_step_forms"), ("form_hold", "hold", "serve", "one_step_forms"),
    ("form_bp_saved", "bp_saved", "serve", "one_step_forms"),
    ("form_bp_faced_pg", "bp_faced_pg", "serve", "one_step_forms"), ("form_brk", "brk", "return", "one_step_forms"),
    ("form_bp_conv", "bp_conv", "return", "one_step_forms"),
    ("form_rpw_first", "rpw_first", "return", "one_step_forms"),
    ("form_rpw_second", "rpw_second", "return", "one_step_forms"),
    ("formdef_ace", "def_ace", "defence", "one_step_forms"), ("formdef_df", "def_df", "defence", "one_step_forms"),
    ("formdef_first_in", "def_first_in", "defence", "one_step_forms"),
    ("formdef_bp_faced_pg", "def_bp_faced_pg", "defence", "one_step_forms"),
    ("iosO_ace", "ace", "serve", "joint_solves"), ("iosD_ace", "def_ace", "defence", "joint_solves"),
    ("iosO_df", "df", "serve", "joint_solves"), ("iosD_df", "def_df", "defence", "joint_solves"),
    ("iosO_first_in", "first_in", "serve", "joint_solves"),
    ("iosD_first_in", "def_first_in", "defence", "joint_solves"),
    ("iosO_first_won", "first_won", "serve", "joint_solves"), ("iosD_first_won", "rpw_first", "return", "joint_solves"),
    ("iosO_second_won", "second_won", "serve", "joint_solves"),
    ("iosD_second_won", "rpw_second", "return", "joint_solves"),
    ("iosO_hold", "hold", "serve", "joint_solves"), ("iosD_hold", "brk", "return", "joint_solves"),
    ("iosO_bp_saved", "bp_saved", "serve", "joint_solves"), ("iosD_bp_saved", "bp_conv", "return", "joint_solves"),
    ("prod_ace", "ace+def_ace", "serve+defence", "joint_solves"),
    ("prod_df", "df+def_df", "serve+defence", "joint_solves"),
    ("prod_first_in", "first_in+def_first_in", "serve+defence", "joint_solves"),
    ("prod_first_won", "first_won+rpw_first", "serve+return", "joint_solves"),
    ("prod_second_won", "second_won+rpw_second", "serve+return", "joint_solves"),
    ("prod_hold", "hold+brk", "serve+return", "joint_solves"),
    ("prod_bp_saved", "bp_saved+bp_conv", "serve+return", "joint_solves"),
    ("tour", "", "none", "context"), ("surface", "", "none", "context"), ("level", "", "none", "context"),
    ("indoor", "", "none", "context"), ("best_of", "", "none", "context"), ("round", "", "none", "context"),
    ("elo_overall", "results", "none", "results_ratings"), ("elo_surf_offset", "results", "none", "results_ratings"),
    ("surf_season_a", "workload", "none", "workload"), ("surf_season_b", "workload", "none", "workload"),
    ("surf_layoff_a", "workload", "none", "workload"), ("surf_layoff_b", "workload", "none", "workload"),
    ("spd_L", "speed", "serve", "stage2_speed"),
]
FIXED_CLASS = {"market": "CTX", "context": "CTX", "intrinsic": "INTR", "workload": "WORK", "results_ratings": "RES"}


def reference_gap(gaps: pd.DataFrame, tour: str) -> float:
    g = gaps[gaps["tour"].eq(tour) & gaps["n_ps"].gt(0)]
    return float(np.average(np.abs(g["delta_elo_100"]), weights=g["box_rows"]))


def classify_stats(gam: pd.DataFrame, lev: pd.DataFrame, gaps: pd.DataFrame, thr: dict) -> pd.DataFrame:
    """Apply the fixed thresholds (thresholds.json) to every base statistic and tour."""
    k = 0.10
    out = []
    for r in gam.itertuples(index=False):
        ref = reference_gap(gaps, r.tour)
        opp_part = abs(r.gamma) * ref
        sig_ok = (r.gamma_lo > 0) or (r.gamma_hi < 0)
        cls = "OPP" if sig_ok and opp_part >= k * r.sd_signal else "ENV"
        row = {"tour": r.tour, "stat": r.stat, "side": r.side, "class": cls, "gamma": r.gamma, "gamma_lo": r.gamma_lo,
               "gamma_hi": r.gamma_hi, "gamma_unit": r.unit, "sd_signal": r.sd_signal, "sd_match": r.sd_match,
               "reference_gap_elo_100": ref, "opp_part_ref_gap": opp_part,
               "opp_part_in_sd_signal": opp_part / r.sd_signal}
        real = []
        for L in LEVELS:
            x = lev[lev["tour"].eq(r.tour) & lev["stat"].eq(r.stat) & lev["level"].eq(L)]
            if x.empty or x["n_ps"].iloc[0] < 100 or not np.isfinite(x["raw_shift"].iloc[0]):
                row[f"level_shift_{L}"] = x["raw_shift"].iloc[0] if not x.empty and "raw_shift" in x else np.nan
                row[f"explained_share_{L}"] = np.nan
                row[f"residual_{L}"] = np.nan
                row[f"delta_{L}"] = "not identified"
                continue
            x = x.iloc[0]
            row[f"level_shift_{L}"] = x["raw_shift"]
            row[f"level_shift_{L}_lo"] = x["raw_lo"]
            row[f"level_shift_{L}_hi"] = x["raw_hi"]
            row[f"explained_{L}"] = x["explained"]
            row[f"explained_share_{L}"] = x["explained_share"] if abs(x["raw_shift"]) >= 0.05 * r.sd_signal else np.nan
            row[f"residual_{L}"] = x["residual"]
            row[f"residual_{L}_lo"] = x["residual_lo"]
            row[f"residual_{L}_hi"] = x["residual_hi"]
            row[f"n_ps_{L}"] = int(x["n_ps"])
            if cls == "OPP":
                v, lo, hi = x["residual"], x["residual_lo"], x["residual_hi"]
            else:
                v, lo, hi = x["raw_shift"], x["raw_lo"], x["raw_hi"]
            is_real = ((lo > 0) or (hi < 0)) and abs(v) >= k * r.sd_signal
            row[f"delta_{L}"] = "real" if is_real else "not real"
            if is_real:
                real.append(L)
        row["delta_levels"] = ",".join(real)
        out.append(row)
    return pd.DataFrame(out)


def rule_for(cls: str, family: str, delta_levels: str) -> str:
    if cls in ("INTR", "WORK", "CTX"):
        return "untouched"
    if cls == "RES":
        return "w_results only"
    dl = f" at {delta_levels}" if delta_levels else ""
    if family in ("joint_solves", "online_point_ratings"):
        return f"solve handles the opponent; level term delta{dl}; weight w" if delta_levels \
            else "solve handles the opponent; weight w only (no level term)"
    if family == "stage2_speed":
        return "untouched"   # replaced by the speed verdict in build_classes
    if cls == "OPP":
        return f"translate: gamma x (opponent Elo - reference) + delta{dl}; weight w" if delta_levels \
            else "translate: gamma x (opponent Elo - reference), delta 0; weight w"
    return f"delta only{dl}; weight w" if delta_levels else "weight only"


def build_classes(stat_cls: pd.DataFrame, speed: dict, thr: dict) -> pd.DataFrame:
    rows = []
    sc = stat_cls.set_index(["tour", "stat"])
    base_cols = ["gamma", "gamma_lo", "gamma_hi", "gamma_unit"] + \
        [c for L in LEVELS for c in (f"level_shift_{L}", f"explained_share_{L}", f"residual_{L}")]
    for g in TOURS:
        for s in STATS:
            r = sc.loc[(g, s)]
            rows.append({"name": s, "kind": "stat", "tour": g, "base_stat": s, "side": STATS[s][0], "family": "",
                         "class": r["class"], **{c: r.get(c, np.nan) for c in base_cols},
                         "delta_levels": r["delta_levels"],
                         "rule": rule_for(r["class"], "one_step_forms", r["delta_levels"]) + " (forms and raw rates); "
                         + rule_for(r["class"], "joint_solves", r["delta_levels"]) + " (joint solves)",
                         "opp_part_in_sd_signal": r["opp_part_in_sd_signal"], "sd_signal": r["sd_signal"]})
        v = speed.get("verdict", {})
        for name, side, cls, rule, extra in (
                ("results", "none", "RES", "w_results only (Elo is opponent-adjusted by construction)", {}),
                ("age", "none", "INTR", "untouched", {}),
                ("workload", "none", "WORK", "untouched (a set is a set)", {}),
                ("speed", "serve", v.get("class", "ENV") if g == "atp" else "CTX",
                 v.get("rule", "untouched") if g == "atp" else "untouched (no women's speeds in stage 2)",
                 {"gamma": v.get("gamma"), "gamma_lo": v.get("gamma_lo"), "gamma_hi": v.get("gamma_hi"),
                  "gamma_unit": "km/h per 100 Elo", "level_shift_CH": v.get("centred_shift_CH")}
                 if g == "atp" else {})):
            rows.append({"name": name, "kind": "stat", "tour": g, "base_stat": name, "side": side, "family": "",
                         "class": cls, "rule": rule, **extra})
        for name, base, side, fam in INPUTS:
            row = {"name": name, "kind": "input", "tour": g, "base_stat": base, "side": side, "family": fam}
            if fam in FIXED_CLASS:
                row["class"] = FIXED_CLASS[fam]
                row["rule"] = rule_for(row["class"], fam, "")
            elif fam == "stage2_speed":
                v = speed.get("verdict", {})
                row["class"] = v.get("class", "ENV")
                row["rule"] = v.get("rule", "untouched")
                row["gamma"] = v.get("gamma")
                row["gamma_lo"] = v.get("gamma_lo")
                row["gamma_hi"] = v.get("gamma_hi")
                row["gamma_unit"] = "km/h per 100 Elo"
                row["level_shift_CH"] = v.get("centred_shift_CH")
                if g == "wta":
                    row["class"], row["rule"] = "CTX", "untouched (spd_L is 0 for every woman)"
            else:
                parts = base.split("+")
                cl = [sc.loc[(g, p), "class"] for p in parts]
                row["class"] = "OPP" if "OPP" in cl else "ENV"
                dls = sorted({L for p in parts for L in str(sc.loc[(g, p), "delta_levels"]).split(",") if L},
                             key=LEVELS.index)
                row["delta_levels"] = ",".join(dls)
                row["rule"] = rule_for(row["class"], fam, row["delta_levels"])
                if len(parts) == 1:
                    for c in base_cols:
                        row[c] = sc.loc[(g, parts[0]), c]
                else:
                    for p in parts:
                        row[f"gamma_{p}"] = sc.loc[(g, p), "gamma"]
            rows.append(row)
    cols = ["name", "kind", "tour", "base_stat", "side", "family", "class", "gamma", "gamma_lo", "gamma_hi",
            "gamma_unit"] + [c for L in LEVELS for c in (f"level_shift_{L}", f"explained_share_{L}", f"residual_{L}")] \
        + ["rule", "delta_levels", "opp_part_in_sd_signal", "sd_signal"]
    t = pd.DataFrame(rows)
    extra = [c for c in t.columns if c not in cols]
    return t[cols + extra]


def speed_verdict(sp: dict, ref_gap_atp: float) -> dict:
    k = 0.10 * sp["constants"]["spd_L_standardiser_kmh"]
    g = sp["gradient_main_tour"]["y_c"]
    opp_dep = (g["lo"] > 0 or g["hi"] < 0) and abs(g["gamma_kmh_per_100_elo"]) * ref_gap_atp >= k
    c = sp["challenger_vs_main_same_player_season"]["CH"]["min_1_rows_each"].get("centred_kmh", {})
    lev = bool(c) and (c["lo"] > 0 or c["hi"] < 0) and abs(c["mean"]) >= k
    v = {"materiality_kmh": k, "opponent_dependent": bool(opp_dep), "level_problem": bool(lev),
         "gamma": g["gamma_kmh_per_100_elo"], "gamma_lo": g["lo"], "gamma_hi": g["hi"],
         "opp_part_ref_gap_kmh": abs(g["gamma_kmh_per_100_elo"]) * ref_gap_atp,
         "opp_part_in_between_player_sd": abs(g["gamma_kmh_per_100_elo"]) * ref_gap_atp
         / sp["gradient_main_tour"]["sd_between_player_seasons_kmh"],
         "centred_shift_CH": c.get("mean"), "centred_shift_CH_lo": c.get("lo"), "centred_shift_CH_hi": c.get("hi"),
         "centred_shift_CH_p_reads_high": c.get("p_positive")}
    if opp_dep and not lev:
        # the class follows the fixed rule; the treatment does not translate: stage 2 centres every speed on its
        # edition's offset (y = alpha_player + gamma_edition), which takes out each edition's average opponent strength,
        # the part that differs by level; translating by gamma as well would count it twice (see A_classes.md)
        v["class"], v["rule"] = "OPP", "untouched by the layer: stage 2's edition centring removes each edition's " \
                                       "average opponent strength (the level part); no residual level shift resolved"
    elif opp_dep and lev:
        v["class"], v["rule"] = "OPP", "guard: Challenger speed rows shifted by the measured centred offset, or held " \
                                       "out of spd_L's history (w = 0)"
    elif lev:
        v["class"], v["rule"] = "ENV", "guard: Challenger speed rows shifted by the measured centred offset, or held " \
                                       "out of spd_L's history (w = 0)"
    else:
        v["class"], v["rule"] = "ENV", "untouched (no opponent dependence; no level shift beyond 0.195 km/h measured)"
    return v


# ------------------------------------------------------------------------------------------------
# The run

def run_analysis() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    thr_path = OUT / "thresholds.json"
    thr = json.loads(thr_path.read_text(encoding="utf-8"))
    rec = {"started_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "method_version": METHOD_VERSION,
           "thresholds_sha256": sha256(thr_path), "strength": json.loads(STRENGTH_META.read_text(encoding="utf-8"))}
    log("loading rows (2010-2024, every level, events before the holdout)")
    m, rows = analysis_rows()
    rec["rows"] = {"player_rows": int(len(rows)), "matches": int(rows["match_id"].nunique()),
                   "max_tournament_date": str(rows["tournament_date"].max().date()),
                   "max_year": int(rows["year"].max())}
    log(f"  {len(rows):,} player rows of {rows['match_id'].nunique():,} matches")
    log("gamma, main specification")
    gam = table_gamma(rows)
    gam.to_csv(OUT / "gamma_main.csv", index=False)
    log("results check")
    table_results(rows).to_csv(OUT / "results_check.csv", index=False)
    log("level decomposition")
    gaps, lev = table_levels(rows, gam)
    gaps.to_csv(OUT / "level_opponent_gaps.csv", index=False)
    lev.to_csv(OUT / "level_decomposition.csv", index=False)
    log("robustness: eras, level and round, inside the Challengers; each season")
    table_robust(rows).to_csv(OUT / "gamma_robust.csv", index=False)
    table_by_season(rows).to_csv(OUT / "gamma_by_season.csv", index=False)
    log("counter-skill")
    s3 = pd.read_parquet(STAGE3_SOURCE, columns=["match_id", "serve_a", "serve_b", "return_a", "return_b"]) \
        .set_index("match_id")
    rec["stage3_source_sha256"] = sha256(STAGE3_SOURCE)
    table_counter(rows, s3).to_csv(OUT / "counter_skill.csv", index=False)
    log("level decomposition with Stage 3's one-scale ratings (points statistics)")
    table_levels_stage3(rows, s3, lev).to_csv(OUT / "level_decomposition_stage3.csv", index=False)
    log("serve speed")
    sp = speed_checks(strength_frame())
    sp["verdict"] = speed_verdict(sp, reference_gap(gaps, "atp"))
    (OUT / "speed_checks.json").write_text(json.dumps(sp, indent=1, default=float), encoding="utf-8")
    log("classes")
    stat_cls = classify_stats(gam, lev, gaps, thr)
    cls = build_classes(stat_cls, sp, thr)
    # written explicitly: "none" = no level where delta is real; "n/a" = the class has no delta (RES, INTR, WORK, CTX)
    stat_cls.assign(delta_levels=stat_cls["delta_levels"].replace("", "none")) \
        .to_csv(OUT / "stat_classes_detail.csv", index=False)
    cls["delta_levels"] = cls["delta_levels"].replace("", "none")
    cls.loc[cls["class"].isin(["RES", "INTR", "WORK", "CTX"]) | cls["delta_levels"].isna(), "delta_levels"] = \
        np.where(cls["class"].isin(["OPP", "ENV"]), "none", "n/a")[
            (cls["class"].isin(["RES", "INTR", "WORK", "CTX"]) | cls["delta_levels"].isna()).to_numpy()]
    cls.to_csv(OUT / "classes.csv", index=False)
    (OUT / "classes.sha256").write_text(f"{sha256(OUT / 'classes.csv')}  classes.csv\n", encoding="utf-8")
    rec["finished_utc"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    rec["seconds"] = round(time.time() - T0, 1)
    rec["outputs"] = {p.name: sha256(p) for p in sorted(OUT.glob("*.csv"))}
    (OUT / "run.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    log("done")


def demo() -> None:
    t = time.time()
    cut = season_cutoff(2020)
    g = gamma(cut)
    first = time.time() - t
    t = time.time()
    gamma(season_cutoff(2021))
    second = time.time() - t
    pd.set_option("display.width", 200)
    print(g[["tour", "stat", "gamma", "gamma_lo", "gamma_hi", "n_rows", "last_result_day"]].to_string(index=False))
    print(f"cutoff 2020: {cut.date()}; first call {first:.1f} s (loads), next call {second:.1f} s")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strength", action="store_true", help="copy and check the strength file")
    ap.add_argument("--demo", action="store_true", help="one gamma() call, timed")
    ap.add_argument("--analysis", action="store_true", help="every table of the report, then the classes")
    a = ap.parse_args()
    if a.strength:
        print(json.dumps(build_strength(), indent=1))
    if a.demo:
        demo()
    if a.analysis:
        run_analysis()


if __name__ == "__main__":
    main()
