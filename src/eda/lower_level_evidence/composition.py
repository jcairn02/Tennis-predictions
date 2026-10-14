"""Evidence dose and exposure: how much of each model input's evidence comes from lower levels, for which players and
matches, and where the current best model is weakest against the closing price (lower_level_evidence, role 02).

THE RENEWABLE PART. Everything below reruns unchanged on a candidate Stage 0 that carries new lower-level data:
    ./python.sh src/eda/lower_level_evidence/composition.py --stage0-dir <candidate Stage 0 folder> --label <name>
The counts are recomputed from that Stage 0; the frame (--frame) still names the model's matches; the scores (part 5)
use the model given by --model (default: the frozen reference's fits; a candidate's built folder in compare.py's layout
also works). Nothing here reads an outcome of a 2025-2026 match (the proposed holdout): parts 1-4 read no outcome at all,
and part 5 reads results of seasons <= 2024 only (season <= 2024 is checked to mean events before 30 Dec 2024 first).

WHAT IS COUNTED. For every model-frame match (67,226 main-tour matches of 2013-2026) and each side, that player's
earlier matches in Stage 0, by the study's bucket (common.bucket: MAIN, TQ, GSQ, CH, CHQ, ITF, ITFQ, TEAM), in two
channels:
    res   the results channel: every completed or retired match (walkovers and "other" left out)
    box   the box-score channel: the same with a box score (Stage 0's has_box)
and in these windows (days between tournament dates, the way the per-player inputs measure time):
    14d, 28d, 91d, 365d   events that started up to W days before this one (t_i - t_j <= W, inclusive, as Stage 4's
                          sets_14d and 52-week windows: stage4_features.py:838-839), plus this event's earlier rounds
    career                every earlier match since Stage 0 begins (2010)
    h2w, h4w, h13w, h52w  effective counts: each earlier match weighted 2^(-age / h weeks), age from tournament dates
                          (Stage 3's lookback_sums convention, stage3_traits.py:556-564). h = 2 weeks is the two-week
                          form (form_*, formdef_*, adjperf_tpw_2w: Stage B's h3 = 2); 4 and 13 weeks the short-memory
                          IOS points matchup (men, women); 52 weeks the typical long memory of the IOS profile
                          (its half-lives run 26-208 weeks by statistic, ios_constants registry)

"EARLIER" (the choice, and why not the strict match clock). A player's own earlier matches are those of events with an
earlier tournament date, plus earlier rounds of the same event (same tournament id and date). Other events of the same
week and other matches of the same round (round robin) never count. This is Stage 0's as-of rule
(predictability_diagnostic/common.py:161-181), the rule every per-player input and the leak-proof IOS's own-match step
follow (match_timing/ios_time.py:14-18). It is "surely finished before" for a player's own matches because nobody
plays two matches at once (the match-clock decision, point 1). The strict match clock (a result counts from lf + 1, read
at es) is the right rule for OTHER players' results; applied to a player's own matches it would drop the same event's
earlier rounds whenever their day windows overlap, which the inputs do count. Its error against this choice is measured,
pair by pair, on the 365-day window (clock_check.csv): matches this rule counts that the clock cannot place before the
target, contradictions (the clock says the earlier-counted match started after the target surely finished), and
same-week matches of other events that the clock shows surely finished first (which this rule leaves out).

OUTPUTS (data/studies/lower_level_evidence/composition/<label>/):
    sides.parquet           one row per model match and side: tour, season, level, rank and band, and every count
                            (<channel>_<window>_<bucket>; hard windows int16, effective counts rounded to 0.001),
                            zstd-compressed, gitignored like every parquet (rebuilt by this script in under a minute)
    shares_full.csv.gz      the lower-level share of evidence per channel and window, by tour x season x target level x
                            rank band, with each bucket's share (task 2)
    shares.csv              the same at the margins: tour; tour x era; tour x era x level; tour x era x band; tour x
                            season
    inputs_dose.csv         each input family's mirrored channel and window, its lower-level share by tour, era, level
                            and band
    itf_regime.csv          ITF's share of box-score evidence by tour and quarter; itf_any.csv: players and matches with
                            any ITF box score in their 365-day window (task 3)
    itf_preview.csv         what ITF box scores of 2018-2024 (collection plan P7) would add to the 2019-2024 model
                            matches' 365-day windows, by tour and rank band; itf_preview_unique.csv: distinct matches;
                            itf_p7_scenario.csv: the box-score channel recounted exactly with those box scores in place,
                            by tour and season (does the shift touch some seasons only?)
    exposure.csv, exposure_cross.csv   main-tour exposure per side and the less-exposed side (task 4)
    scores.csv              part 5: model (both stages; stage 1) against the recalibrated close, 2020-2024, by
                            pre-chosen exposure and dose strata, with 95% intervals and calibration slopes;
                            scores_heterogeneity.csv: per family, a Wald test that its strata's gains are equal
    clock_check.csv, summary.json   the ordering rule's error against the match clock; headline numbers, input hashes,
                            the brute-force spot check of the counts

The strata of part 5 were fixed in this file (STRATA) before any score was computed; they are descriptive, not a model
choice. Positive gains = the model has the lower log loss (better) than the recalibrated close, in mLL per match.

Run: ./python.sh src/eda/lower_level_evidence/composition.py [--stage0-dir DIR] [--frame PARQUET] [--timing PARQUET]
                                                           [--label NAME] [--out DIR] [--model reference|FOLDER]
                                                           [--no-scores]
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

from src.eda.lower_level_evidence import common as CM  # noqa: E402

LABEL = "reference_2026-10-08"
PLAYED = ("completed", "retired")
WINDOWS = (14, 28, 91, 365)                 # days between tournament dates, inclusive
HALF_LIVES = (2, 4, 13, 52)                 # weeks
WINDOW_NAMES = tuple(f"{w}d" for w in WINDOWS) + ("career",) + tuple(f"h{h}w" for h in HALF_LIVES)
CHANNELS = ("res", "box")
BUCKETS = CM.BUCKETS
LOWER = CM.LOWER
R_MULT = 32                                  # round_order < 32 (Stage 0: Q1 1 .. F 17)
ORIGIN_PAD = 400                             # days before Stage 0's first date: t - 365 never goes below 0
BANDS = ((1, 20, "1-20"), (21, 50, "21-50"), (51, 100, "51-100"), (101, 200, "101-200"), (201, np.inf, "201+"))
BAND_ORDER = [b[2] for b in BANDS] + ["unranked"]
EXPOSURE_BINS = ((0, 0, "0"), (1, 4, "1-4"), (5, 9, "5-9"), (10, 19, "10-19"), (20, np.inf, "20+"))
LEVEL_NAMES = {0.0: "Slams", 1.0: "Finals", 2.0: "1000s", 3.0: "500s", 4.0: "250s"}
ERAS = ((2013, 2018, "2013-18"), (2019, 2024, "2019-24"), (2025, 2026, "2025-26"))
SPOT_CHECKS = 300
P7_FROM, P7_TO = pd.Timestamp("2018-01-01"), pd.Timestamp("2024-12-29")             # collection plan P7: ITF 2018-2024
P7_EXPECTED_BOX = 0.98                      # the plan's expectation (84 sampled matches), a claim, not observed here

# Input families and the channel / window that mirrors their memory (inferred from the builders' own descriptions:
# tabpfn_thinking/common.py:77-127, the ios_constants registry, stageB_adj_summary.json's h3 = 2 weeks, Stage 4's windows;
# role 01 traces the code itself).
INPUT_FAMILIES = (
    ("form_*, formdef_*, adjperf_tpw_2w (17)", "box", "h2w", "opponent-adjusted two-week form: half-life 2 weeks"),
    ("ios_points_short, men", "box", "h4w", "short-memory IOS points matchup: half-life 4 weeks"),
    ("ios_points_short, women", "box", "h13w", "short-memory IOS points matchup: half-life 13 weeks"),
    ("points_52w", "box", "365d", "raw serve-against-return points, last 52 weeks"),
    ("iosO_*, iosD_*, prod_* (21)", "box", "h52w", "IOS profile, long memory: half-lives 26-208 weeks by statistic"),
    ("ratings_iid", "box", "career", "Stage 3 serve and return ratings: career, Glicko-style steps (completed only)"),
    ("elo_overall, offset Elo, elo_games (7)", "res", "career", "Elo family: every result since 2010"),
    ("sets_14d", "res", "14d", "workload: sets in the last 14 days"),
)

# Part 5's strata, fixed before any score was read. Exposure: the less-exposed side's main-tour (MAIN) results in the
# window. Dose: the 365-day share of a side's evidence below the main tour (TQ, GSQ, CH, CHQ, ITF, ITFQ over all buckets).
SHARE_BINS = ((0.0, 0.25, "0-25%"), (0.25, 0.5, "25-50%"), (0.5, 0.75, "50-75%"), (0.75, 1.0 + 1e-9, "75-100%"))
DIFF_BINS = ((0.0, 0.1, "0-0.10"), (0.1, 0.25, "0.10-0.25"), (0.25, 0.5, "0.25-0.50"), (0.5, 1.0 + 1e-9, "0.50-1"))
STRATA = ("all", "exposure_365d", "exposure_career", "dose_box_max", "dose_box_absdiff", "dose_res_max",
          "dose_res_absdiff", "exposure_x_dose")

T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def col(channel: str, window: str, bucket: str) -> str:
    return f"{channel}_{window}_{bucket}"


def band_of(rank) -> np.ndarray:
    r = np.asarray(rank, dtype="float64")
    out = np.full(len(r), "unranked", dtype=object)
    for lo, hi, name in BANDS:
        out[(r >= lo) & (r <= hi)] = name
    return out


def bin_of(x, bins, missing: str = "none", closed: bool = False) -> np.ndarray:
    """Label of each value's bin (lo, hi, name): lo <= x < hi, or lo <= x <= hi with closed=True (integer counts).
    Missing values get `missing`."""
    x = np.asarray(x, dtype="float64")
    out = np.full(len(x), missing, dtype=object)
    for lo, hi, name in bins:
        out[(x >= lo) & ((x <= hi) if closed else (x < hi))] = name
    return out


def exposure_bin(n) -> np.ndarray:
    return bin_of(n, EXPOSURE_BINS, closed=True)


def era_of(season) -> np.ndarray:
    s = np.asarray(season)
    out = np.full(len(s), "other", dtype=object)
    for lo, hi, name in ERAS:
        out[(s >= lo) & (s <= hi)] = name
    return out


def rel(path) -> str:
    """Repository-relative POSIX path when under the repository, else the absolute one."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def write_sides(sides: pd.DataFrame, path: Path) -> None:
    """The sides table as written: hard-window counts as int16 (checked to fit), effective counts rounded to 0.001
    (every summary is computed before this rounding, at full precision)."""
    out = sides.copy()
    for c in out.columns:
        if out[c].dtype == np.int32:
            if int(out[c].max()) >= np.iinfo(np.int16).max:
                raise ValueError(f"{c} does not fit int16")
            out[c] = out[c].astype(np.int16)
        elif out[c].dtype == np.float32:
            out[c] = out[c].round(3)
    out.to_parquet(path, index=False, compression="zstd", compression_level=19)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------
# Part 1: the history table and the window counts

def history_table(m: pd.DataFrame, p: pd.DataFrame) -> tuple[pd.DataFrame, pd.Timestamp]:
    """One row per Stage 0 player row: player code (tour | id), day t (since an origin 400 days before Stage 0's first
    date), event code (tournament id + date), round order, bucket, and the two channels. Rows without a player id are
    dropped (they can be no one's history)."""
    need = {"match_id", "tour", "bucket", "tournament_id", "tournament_date", "round_order", "status", "has_box"}
    missing = need - set(m.columns)
    if missing:
        raise ValueError(f"Stage 0 matches lack {sorted(missing)}")
    mm = m[sorted(need)].copy()
    mm["tournament_date"] = pd.to_datetime(mm["tournament_date"])
    origin = mm["tournament_date"].min().normalize() - pd.Timedelta(days=ORIGIN_PAD)
    mm["ev"] = pd.factorize(mm["tournament_id"].astype(str) + "|" + mm["tournament_date"].dt.strftime("%Y-%m-%d"),
                            sort=True)[0].astype(np.int64)
    h = p[["match_id", "player_id", "side"]].merge(mm, on="match_id", how="left", validate="many_to_one")
    if h["tour"].isna().any():
        raise ValueError(f"{int(h['tour'].isna().sum())} player rows name a match Stage 0 lacks")
    h = h[h["player_id"].notna()].copy()
    h["pkey"] = h["tour"].astype(str) + "|" + h["player_id"].astype(str)
    h["pcode"] = pd.factorize(h["pkey"], sort=True)[0].astype(np.int64)
    h["mcode"] = pd.factorize(h["match_id"], sort=True)[0].astype(np.int64)
    h["t"] = (h["tournament_date"] - origin).dt.days.astype(np.int64)
    h["rnd"] = h["round_order"].astype(np.int64)
    if (h["rnd"] < 0).any() or (h["rnd"] >= R_MULT).any():
        raise ValueError("round_order outside 0..31")
    h["res"] = h["status"].isin(PLAYED).to_numpy()
    h["box"] = h["res"].to_numpy() & h["has_box"].fillna(False).astype(bool).to_numpy()
    h["bucket"] = h["bucket"].astype(str)
    return h.reset_index(drop=True), origin


class Index:
    """The players' histories sorted by (player, day, event, round), with cumulative counts per channel and bucket, so
    that every window of every target is two binary searches (no per-row look-back)."""

    def __init__(self, hist: pd.DataFrame):
        self.n_players = int(hist["pcode"].max()) + 1
        self.D = int(hist["t"].max()) + 2
        self.E = int(hist["ev"].max()) + 1
        key = self.enc(hist["pcode"].to_numpy(), hist["t"].to_numpy(), hist["ev"].to_numpy(), hist["rnd"].to_numpy())
        o = np.argsort(key, kind="stable")
        self.order = o
        self.key = key[o]
        self.p = hist["pcode"].to_numpy()[o]
        self.t = hist["t"].to_numpy()[o]
        bucket = hist["bucket"].to_numpy()[o]
        ch = {"res": hist["res"].to_numpy()[o], "box": hist["box"].to_numpy()[o]}
        self.cols = [(c, b) for c in CHANNELS for b in BUCKETS]
        M = np.zeros((len(o), len(self.cols)), dtype=np.int8)
        for k, (c, b) in enumerate(self.cols):
            M[:, k] = ch[c] & (bucket == b)
        self.M = M
        self.cum = np.zeros((len(o) + 1, len(self.cols)), dtype=np.int64)
        np.cumsum(M, axis=0, dtype=np.int64, out=self.cum[1:])
        t0 = np.full(self.n_players, np.iinfo(np.int64).max, dtype=np.int64)
        np.minimum.at(t0, self.p, self.t)
        self.t0 = t0

    def enc(self, p, t, ev, rnd) -> np.ndarray:
        p, t, ev, rnd = (np.asarray(x, dtype=np.int64) for x in (p, t, ev, rnd))
        if (t < 0).any() or (t >= self.D).any() or (ev >= self.E).any():
            raise ValueError("a key component is out of range")
        return ((p * self.D + t) * self.E + ev) * R_MULT + rnd

    def bounds(self, p, t, ev, rnd) -> dict:
        """Positions in the sorted history: the player's first row, the first row of day t, and the same event's
        rows before round rnd."""
        p, t, ev, rnd = (np.asarray(x, dtype=np.int64) for x in (p, t, ev, rnd))
        z = np.zeros_like(p)
        return {"start": np.searchsorted(self.key, self.enc(p, z, z, z), side="left"),
                "day": np.searchsorted(self.key, self.enc(p, t, z, z), side="left"),
                "ev_lo": np.searchsorted(self.key, self.enc(p, t, ev, z), side="left"),
                "ev_hi": np.searchsorted(self.key, self.enc(p, t, ev, rnd), side="left")}

    def counts(self, p, t, ev, rnd) -> dict[str, np.ndarray]:
        """{window name: (targets x channel-bucket) array} for the targets (p, t, ev, rnd): their own earlier matches
        under the as-of rule, in each window."""
        p, t, ev, rnd = (np.asarray(x, dtype=np.int64) for x in (p, t, ev, rnd))
        b = self.bounds(p, t, ev, rnd)
        same_event = self.cum[b["ev_hi"]] - self.cum[b["ev_lo"]]
        out = {}
        for w in WINDOWS:
            lo = np.searchsorted(self.key, self.enc(p, np.maximum(t - w, 0), np.zeros_like(p), np.zeros_like(p)),
                                 side="left")
            out[f"{w}d"] = (self.cum[b["day"]] - self.cum[lo]) + same_event
        out["career"] = (self.cum[b["day"]] - self.cum[b["start"]]) + same_event
        for h in HALF_LIVES:
            out[f"h{h}w"] = self._decayed(h, p, t, b, same_event)
        return out

    def _decayed(self, h: float, p, t, b: dict, same_event: np.ndarray) -> np.ndarray:
        """Sum of 2^(-(t_i - t_j) / 7h) over earlier events (each player's cumulative sums restart at his first row, so
        no cancellation), plus the same event's earlier rounds at weight 1."""
        lam = 1.0 / (7.0 * h)
        v = np.exp2((self.t - self.t0[self.p]) * lam)
        res = np.zeros((len(p), len(self.cols)), dtype=np.float64)
        has = b["day"] > b["start"]
        idx = np.maximum(b["day"] - 1, 0)
        scale = np.exp2(-(t - self.t0[p]) * lam)
        half = len(BUCKETS)
        for k0 in range(0, len(self.cols), half):          # one channel at a time (memory)
            Mv = self.M[:, k0:k0 + half].astype(np.float64) * v[:, None]
            cw = pd.DataFrame(Mv).groupby(self.p, sort=False).cumsum().to_numpy()
            res[has, k0:k0 + half] = cw[idx[has]] * scale[has, None]
        return res + same_event


def count_slow(hist: pd.DataFrame, p: int, t: int, ev: int, rnd: int) -> dict[str, dict[tuple[str, str], float]]:
    """Brute force for one target (tests and the spot check): the same counts from the rule written out directly."""
    g = hist[hist["pcode"] == p]
    earlier = (g["t"] < t) | ((g["t"] == t) & (g["ev"] == ev) & (g["rnd"] < rnd))
    g = g[earlier]
    age = t - g["t"].to_numpy()
    out = {}
    for w in WINDOW_NAMES:
        if w == "career":
            wt = np.ones(len(g))
        elif w.endswith("d"):
            wt = (age <= int(w[:-1])).astype(float)
        else:
            wt = np.exp2(-age / (7.0 * float(w[1:-1])))
        rec = {}
        for c in CHANNELS:
            on = g[c].to_numpy(bool)
            for bk in BUCKETS:
                rec[(c, bk)] = float(wt[on & (g["bucket"].to_numpy() == bk)].sum())
        out[w] = rec
    return out


def targets_table(hist: pd.DataFrame, frame: pd.DataFrame, players: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The model frame's matches as target sides (A and B), with their keys in the history, Stage 0's rank, and the
    frame's season, level and debut flag."""
    f = frame[["match_id", "tour", "season", "tournament_date", "debut_season", "in_level"]].copy()
    f["match_id"] = f["match_id"].astype(str)
    h = hist[["match_id", "mcode", "side", "player_id", "pcode", "t", "ev", "rnd", "bucket", "tournament_date", "res"]]
    h = h[h["match_id"].isin(set(f["match_id"]))]
    tg = f.merge(h, on="match_id", how="inner", suffixes=("", "_s0"), validate="one_to_many")
    rk = players[["match_id", "player_id", "rank"]].drop_duplicates(["match_id", "player_id"])
    tg = tg.merge(rk, on=["match_id", "player_id"], how="left", validate="one_to_one")
    info = {"frame_matches": int(len(f)), "matches_found_in_stage0": int(tg["match_id"].nunique()),
            "frame_matches_missing_from_stage0": int(len(f) - tg["match_id"].nunique()),
            "target_sides": int(len(tg)),
            "sides_per_match_not_two": int((tg.groupby("match_id").size() != 2).sum()),
            "target_buckets": tg["bucket"].value_counts().to_dict(),
            "target_not_played": int((~tg["res"]).sum()),
            "date_mismatch_frame_vs_stage0": int((pd.to_datetime(tg["tournament_date"])
                                                  != pd.to_datetime(tg["tournament_date_s0"])).sum())}
    tg["level"] = tg["in_level"].map(LEVEL_NAMES).fillna("other")
    tg["band"] = band_of(tg["rank"])
    tg["era"] = era_of(tg["season"].to_numpy())
    tg = tg.drop(columns=["tournament_date_s0", "res"]).sort_values(["match_id", "side"]).reset_index(drop=True)
    return tg, info


def side_counts(ix: Index, tg: pd.DataFrame) -> pd.DataFrame:
    """The sides table: target facts plus every count, <channel>_<window>_<bucket> (hard windows int32, effective counts
    float32)."""
    res = ix.counts(tg["pcode"], tg["t"], tg["ev"], tg["rnd"])
    keep = ["match_id", "side", "tour", "player_id", "season", "era", "tournament_date", "level", "debut_season",
            "rank", "band"]
    parts = [tg[keep].reset_index(drop=True)]
    for w in WINDOW_NAMES:
        arr = res[w]
        dtype = np.float32 if w.startswith("h") else np.int32
        parts.append(pd.DataFrame(arr.astype(dtype), columns=[col(c, w, b) for c, b in ix.cols]))
    return pd.concat(parts, axis=1)


def spot_check(ix: Index, hist: pd.DataFrame, tg: pd.DataFrame, sides: pd.DataFrame, n: int = SPOT_CHECKS,
               seed: int = 7) -> dict:
    """Recount n random sides by brute force; every count must agree (hard windows exactly, effective counts to 1e-6
    relative)."""
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(tg), size=min(n, len(tg)), replace=False)
    hs = hist.set_index("pcode", drop=False).sort_index()
    bad = []
    for i in pick:
        r = tg.iloc[i]
        g = hs.loc[[int(r["pcode"])]]
        slow = count_slow(g, int(r["pcode"]), int(r["t"]), int(r["ev"]), int(r["rnd"]))
        for w, rec in slow.items():
            for (c, b), v in rec.items():
                got = float(sides.iloc[i][col(c, w, b)])
                tol = 1e-6 * max(1.0, abs(v)) if w.startswith("h") else 0.0
                if abs(got - v) > tol + 1e-9:
                    bad.append({"match_id": r["match_id"], "side": r["side"], "window": w, "channel": c, "bucket": b,
                                "fast": got, "slow": v})
    return {"sides_checked": int(len(pick)), "values_checked": int(len(pick) * len(WINDOW_NAMES) * len(ix.cols)),
            "wrong": len(bad), "first_wrong": bad[:5], "passed": not bad}


# ------------------------------------------------------------------------------------------------
# The ordering rule against the match clock (365-day window, pair by pair)

def clock_check(ix: Index, hist: pd.DataFrame, tg: pd.DataFrame, timing: pd.DataFrame | None) -> tuple[pd.DataFrame, dict]:
    """Every (target side, history row) pair with the row's tournament date in [t_i - 365, t_i], the target's own row
    excepted, classified by the as-of rule and by the clock (lf_j < es_i: surely finished first; es_j > lf_i: surely
    started after the target finished). Rows by bucket (results channel)."""
    if timing is None:
        return pd.DataFrame(), {"skipped": "no timing table"}
    tm = timing[["match_id", "es", "lf"]].drop_duplicates("match_id").set_index("match_id")
    h_es = tm["es"].reindex(hist["match_id"]).to_numpy(float)[ix.order]
    h_lf = tm["lf"].reindex(hist["match_id"]).to_numpy(float)[ix.order]
    h_mid = hist["mcode"].to_numpy()[ix.order]
    h_ev = hist["ev"].to_numpy()[ix.order]
    h_rnd = hist["rnd"].to_numpy()[ix.order]
    h_bucket = hist["bucket"].to_numpy()[ix.order]
    h_res = hist["res"].to_numpy()[ix.order]
    t_es = tm["es"].reindex(tg["match_id"]).to_numpy(float)
    t_lf = tm["lf"].reindex(tg["match_id"]).to_numpy(float)
    p, t = tg["pcode"].to_numpy(np.int64), tg["t"].to_numpy(np.int64)
    z = np.zeros_like(p)
    lo = np.searchsorted(ix.key, ix.enc(p, np.maximum(t - 365, 0), z, z), side="left")
    hi = np.searchsorted(ix.key, ix.enc(p, t + 1, z, z), side="left")
    n = hi - lo
    ti = np.repeat(np.arange(len(tg)), n)
    rows = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + np.repeat(lo, n)
    own = h_mid[rows] == tg["mcode"].to_numpy()[ti]
    ti, rows = ti[~own], rows[~own]
    keep = h_res[rows]                                       # the results channel
    ti, rows = ti[keep], rows[keep]
    tj, tt = ix.t[rows], t[ti]
    same_day = tj == tt
    same_ev = same_day & (h_ev[rows] == tg["ev"].to_numpy()[ti])
    asof = (tj < tt) | (same_ev & (h_rnd[rows] < tg["rnd"].to_numpy()[ti]))
    other_event_same_week = same_day & ~same_ev
    known = np.isfinite(h_lf[rows]) & np.isfinite(t_es[ti])
    clock_first = known & (h_lf[rows] < t_es[ti])
    clock_after = known & (h_es[rows] > t_lf[ti])
    age = tt - tj
    recs = []
    for bk in BUCKETS + ("all",):
        mb = np.ones(len(rows), bool) if bk == "all" else (h_bucket[rows] == bk)
        rec = {"bucket": bk,
               "counted_365d": int((asof & mb).sum()),
               "counted_same_event": int((asof & same_ev & mb).sum()),
               "counted_not_placed_first_by_clock": int((asof & mb & known & ~clock_first).sum()),
               "of_which_same_event": int((asof & same_ev & mb & known & ~clock_first).sum()),
               "counted_but_clock_says_after": int((asof & mb & clock_after).sum()),
               "counted_without_clock_days": int((asof & mb & ~known).sum()),
               "left_out_other_event_same_week": int((other_event_same_week & mb).sum()),
               "left_out_but_clock_says_first": int((other_event_same_week & mb & clock_first).sum())}
        for w in WINDOWS:
            inside = age <= w
            rec[f"asof_{w}d"] = int((asof & inside & mb).sum())
            rec[f"strict_clock_{w}d"] = int((clock_first & inside & mb).sum())
        recs.append(rec)
    out = pd.DataFrame(recs)
    allr = out[out["bucket"] == "all"].iloc[0]
    summ = {"pairs_in_365d_ranges": int(len(rows)),
            "counted": int(allr["counted_365d"]),
            "counted_not_placed_first_by_clock": int(allr["counted_not_placed_first_by_clock"]),
            "share_counted_not_placed_first": float(allr["counted_not_placed_first_by_clock"] / allr["counted_365d"])
            if allr["counted_365d"] else None,
            "of_which_same_event_earlier_rounds": int(allr["of_which_same_event"]),
            "contradictions_clock_says_after": int(allr["counted_but_clock_says_after"]),
            "left_out_other_events_same_week": int(allr["left_out_other_event_same_week"]),
            "left_out_but_clock_says_first": int(allr["left_out_but_clock_says_first"]),
            "matches_missing_from_timing": int((~np.isfinite(t_es)).sum())}
    return out, summ


# ------------------------------------------------------------------------------------------------
# Part 2: shares

def lower_share(sides: pd.DataFrame, channel: str, window: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(lower-level evidence, all evidence, share) per side; share NaN where the side has no evidence."""
    tot = sides[[col(channel, window, b) for b in BUCKETS]].to_numpy(float).sum(axis=1)
    low = sides[[col(channel, window, b) for b in LOWER]].to_numpy(float).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        share = np.where(tot > 0, low / np.where(tot > 0, tot, 1.0), np.nan)
    return low, tot, share


def shares(sides: pd.DataFrame, keys: list[str], windows=WINDOW_NAMES) -> pd.DataFrame:
    """Per group, channel and window: sides, evidence (sum of counts), the pooled lower-level share, each bucket's
    pooled share, the mean of the sides' own shares, the share of sides with no evidence, and the share of sides with
    evidence whose lower-level share exceeds one half ("lower levels dominate")."""
    out = []
    for c in CHANNELS:
        for w in windows:
            low, tot, sh = lower_share(sides, c, w)
            g = sides[keys].copy()
            g["_tot"], g["_low"], g["_sh"] = tot, low, sh
            g["_none"] = (tot == 0).astype(float)
            g["_dom"] = np.where(tot > 0, (sh > 0.5).astype(float), np.nan)
            for b in BUCKETS:
                g[f"_{b}"] = sides[col(c, w, b)].to_numpy(float)
            agg = g.groupby(keys, observed=True, dropna=False).agg(
                sides=("_tot", "size"), evidence=("_tot", "sum"), lower=("_low", "sum"),
                mean_side_share=("_sh", "mean"), no_evidence=("_none", "mean"), lower_dominates=("_dom", "mean"),
                **{f"n_{b}": (f"_{b}", "sum") for b in BUCKETS}).reset_index()
            agg.insert(len(keys), "channel", c)
            agg.insert(len(keys) + 1, "window", w)
            ev = agg["evidence"].where(agg["evidence"] > 0)
            agg["share_lower"] = agg["lower"] / ev
            for b in BUCKETS:
                agg[f"share_{b}"] = agg[f"n_{b}"] / ev
            agg["evidence_per_side"] = agg["evidence"] / agg["sides"]
            out.append(agg)
    return pd.concat(out, ignore_index=True)


def margins(sides: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for name, keys in (("tour", ["tour"]), ("tour x era", ["tour", "era"]),
                       ("tour x era x level", ["tour", "era", "level"]), ("tour x era x band", ["tour", "era", "band"]),
                       ("tour x season", ["tour", "season"]), ("tour x level x band", ["tour", "level", "band"])):
        s = shares(sides, keys)
        s.insert(0, "grouping", name)
        parts.append(s)
    return pd.concat(parts, ignore_index=True)


def inputs_dose(sides: pd.DataFrame) -> pd.DataFrame:
    """Each input family's mirrored channel and window: its lower-level share, by tour and era, level and band."""
    rows = []
    for fam, c, w, desc in INPUT_FAMILIES:
        sub = sides
        if fam.endswith(", men"):
            sub = sides[sides["tour"] == "atp"]
        elif fam.endswith(", women"):
            sub = sides[sides["tour"] == "wta"]
        for keys in (["tour", "era"], ["tour", "era", "level"], ["tour", "era", "band"]):
            s = shares(sub, keys, windows=(w,))
            s = s[s["channel"] == c]
            s.insert(0, "input_family", fam)
            s.insert(1, "memory", desc)
            s.insert(2, "grouping", " x ".join(keys))
            rows.append(s)
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------------------------------------
# Part 3: the ITF box-score regime and a preview of P7

def quarter_of(dates) -> np.ndarray:
    d = pd.to_datetime(pd.Series(dates))
    return (d.dt.year.astype(str) + "Q" + d.dt.quarter.astype(str)).to_numpy()


def itf_regime(sides: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = sides.copy()
    q = quarter_of(s["tournament_date"])
    s["period"] = np.where(pd.to_datetime(s["tournament_date"]) < pd.Timestamp("2023-01-01"), "2013-2022", q)
    rows = []
    for (tour, period), g in s.groupby(["tour", "period"]):
        rec = {"tour": tour, "period": period, "sides": len(g), "matches": g["match_id"].nunique()}
        for w in ("28d", "91d", "365d"):
            tot = g[[col("box", w, b) for b in BUCKETS]].to_numpy(float).sum()
            for b in ("ITF", "ITFQ"):
                rec[f"box_share_{b}_{w}"] = float(g[col("box", w, b)].sum() / tot) if tot else np.nan
            rec[f"box_lower_share_{w}"] = float(g[[col("box", w, b) for b in LOWER]].to_numpy(float).sum() / tot) \
                if tot else np.nan
            rec[f"res_share_ITF_{w}"] = float(g[col("res", w, "ITF")].sum()
                                              / g[[col("res", w, b) for b in BUCKETS]].to_numpy(float).sum())
        rec["sides_with_ITF_box_365d"] = float((g[col("box", "365d", "ITF")] > 0).mean())
        rec["sides_with_ITF_or_ITFQ_box_365d"] = float(((g[col("box", "365d", "ITF")] + g[col("box", "365d", "ITFQ")])
                                                        > 0).mean())
        rows.append(rec)
    reg = pd.DataFrame(rows)
    # players and matches with any ITF box score in the 365-day window
    s["any_itf_box"] = (s[col("box", "365d", "ITF")] + s[col("box", "365d", "ITFQ")]) > 0
    s["regime"] = np.where(s["season"] >= 2025, "2025-26", "2013-24")
    anyr = []
    for keys in (["tour", "regime"], ["tour", "regime", "band"], ["tour", "regime", "level"]):
        for k, g in s.groupby(keys):
            k = k if isinstance(k, tuple) else (k,)
            per_match = g.groupby("match_id")["any_itf_box"].any()
            anyr.append({"grouping": " x ".join(keys), **dict(zip(keys, k)), "sides": len(g),
                         "sides_with_any": int(g["any_itf_box"].sum()),
                         "players": int(g["player_id"].nunique()),
                         "players_with_any": int(g.loc[g["any_itf_box"], "player_id"].nunique()),
                         "matches": int(len(per_match)), "matches_with_any_side": int(per_match.sum())})
    return reg, pd.DataFrame(anyr)


def itf_preview(sides: pd.DataFrame, hist: pd.DataFrame, tg: pd.DataFrame, origin: pd.Timestamp
                ) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Model matches of 2019-2024: ITF results-only matches (no box score) inside each side's 365-day window, i.e. what
    P7 (SofaScore, ITF 2018-2024) would turn into box-score evidence if it covers them; and the box-score channel's
    lower-level share today against that ceiling. Distinct matches: every ITF results-only match of 2018-2024 that lies
    in the 365-day window of at least one 2019-2024 model match of the same player."""
    s = sides[(sides["season"] >= 2019) & (sides["season"] <= 2024)].copy()
    s["itf_res_only"] = s[col("res", "365d", "ITF")] - s[col("box", "365d", "ITF")]
    s["itfq_res_only"] = s[col("res", "365d", "ITFQ")] - s[col("box", "365d", "ITFQ")]
    low, tot, sh = lower_share(s, "box", "365d")
    s["box_low"], s["box_tot"], s["box_share"] = low, tot, sh
    with np.errstate(invalid="ignore", divide="ignore"):
        for name, add in (("with_itf", s["itf_res_only"]), ("with_itf_itfq", s["itf_res_only"] + s["itfq_res_only"])):
            nt = tot + add.to_numpy(float)
            s[f"box_share_{name}"] = np.where(nt > 0, (low + add.to_numpy(float)) / np.where(nt > 0, nt, 1), np.nan)
    rows = []
    for keys in (["tour"], ["tour", "band"], ["tour", "level"]):
        for k, g in s.groupby(keys):
            k = k if isinstance(k, tuple) else (k,)
            rows.append({"grouping": " x ".join(keys), **dict(zip(keys, k)), "sides": len(g),
                         "itf_results_only_in_windows": int(g["itf_res_only"].sum()),
                         "per_side": float(g["itf_res_only"].mean()),
                         "sides_with_any": float((g["itf_res_only"] > 0).mean()),
                         "itfq_results_only_in_windows": int(g["itfq_res_only"].sum()),
                         "itf_box_already_in_windows": int(g[col("box", "365d", "ITF")].sum()),
                         "box_evidence_in_windows": int(g["box_tot"].sum()),
                         "box_lower_share_today": float(g["box_low"].sum() / g["box_tot"].sum()),
                         "box_lower_share_if_itf_boxed": float((g["box_low"].sum() + g["itf_res_only"].sum())
                                                               / (g["box_tot"].sum() + g["itf_res_only"].sum())),
                         "box_lower_share_if_itf_itfq_boxed": float(
                             (g["box_low"].sum() + g["itf_res_only"].sum() + g["itfq_res_only"].sum())
                             / (g["box_tot"].sum() + g["itf_res_only"].sum() + g["itfq_res_only"].sum())),
                         "expected_new_box_at_p7_yield": float(P7_EXPECTED_BOX * g["itf_res_only"].sum())})
    prev = pd.DataFrame(rows)
    # distinct ITF matches that P7 would box and that reach a 2019-2024 model match's 365-day window
    targ = tg[(tg["season"] >= 2019) & (tg["season"] <= 2024)][["pcode", "t", "band", "tour"]]
    big = int(hist["t"].max()) + 400
    tkey = targ["pcode"].to_numpy(np.int64) * big + targ["t"].to_numpy(np.int64)
    o = np.argsort(tkey, kind="stable")
    tkey, tband = tkey[o], targ["band"].to_numpy()[o]
    lo_t, hi_t = (P7_FROM - origin).days, (P7_TO - origin).days
    uniq = []
    for bk in ("ITF", "ITFQ"):
        h = hist[(hist["bucket"] == bk) & hist["res"] & ~hist["box"] & hist["t"].between(lo_t, hi_t)]
        q = h["pcode"].to_numpy(np.int64) * big + h["t"].to_numpy(np.int64) + 1      # first target day after the match
        pos = np.searchsorted(tkey, q, side="left")
        ok = pos < len(tkey)
        nxt = np.where(ok, tkey[np.minimum(pos, len(tkey) - 1)], -1)
        same_player = ok & (nxt // big == h["pcode"].to_numpy(np.int64))
        gap = (nxt % big) - h["t"].to_numpy(np.int64)
        inside = same_player & (gap <= 365)
        hh = h.assign(inside=inside, band_next=np.where(inside, tband[np.minimum(pos, len(tkey) - 1)], None))
        per_match = hh.groupby("match_id").agg(inside=("inside", "any"), tour=("tour", "first"))
        best_band = hh[hh["inside"]].assign(br=lambda d: d["band_next"].map({b: i for i, b in enumerate(BAND_ORDER)}))
        best_band = best_band.sort_values("br").drop_duplicates("match_id").set_index("match_id")["band_next"]
        per_match["band"] = best_band.reindex(per_match.index)
        for tour, g in per_match.groupby("tour"):
            uniq.append({"bucket": bk, "tour": tour, "band": "all", "results_only_2018_2024": int(len(g)),
                         "in_a_model_window": int(g["inside"].sum()),
                         "share_in_a_model_window": float(g["inside"].mean())})
            for band, gb in g[g["inside"]].groupby("band"):
                uniq.append({"bucket": bk, "tour": tour, "band": band, "results_only_2018_2024": np.nan,
                             "in_a_model_window": int(len(gb)), "share_in_a_model_window": np.nan})
    un = pd.DataFrame(uniq, columns=["bucket", "tour", "band", "results_only_2018_2024", "in_a_model_window",
                                     "share_in_a_model_window"])
    summ = {"model_sides_2019_2024": int(len(s)),
            "itf_results_only_incidences": int(s["itf_res_only"].sum()),
            "distinct_itf_matches_in_a_window": {r["tour"]: int(r["in_a_model_window"]) for _, r in
                                                 un[(un["bucket"] == "ITF") & (un["band"] == "all")].iterrows()}}
    return prev, un, summ


SCENARIO_WINDOWS = ("h2w", "h13w", "365d", "h52w")


def p7_scenario(hist: pd.DataFrame, tg: pd.DataFrame, sides: pd.DataFrame) -> pd.DataFrame:
    """What-if, by tour and season: every ITF main-draw result of 2018-2024 without a box score is given one (P7 at a
    100% yield; the plan expects ~98%), and the box-score channel is recounted exactly. The lower-level share of the
    box-score evidence today and in the scenario, per window. A change confined to some seasons is the shape the
    input check calls "uneven" (input-data audit finding #6)."""
    h2 = hist.copy()
    flip = ((h2["bucket"] == "ITF") & h2["res"] & ~h2["box"]
            & h2["tournament_date"].between(P7_FROM, P7_TO)).to_numpy()
    h2.loc[flip, "box"] = True
    ix2 = Index(h2)
    res = ix2.counts(tg["pcode"], tg["t"], tg["ev"], tg["rnd"])
    k_box = [k for k, (c, _) in enumerate(ix2.cols) if c == "box"]
    k_low = [k for k, (c, b) in enumerate(ix2.cols) if c == "box" and b in LOWER]
    rows = []
    for w in SCENARIO_WINDOWS:
        tot2, low2 = res[w][:, k_box].sum(axis=1), res[w][:, k_low].sum(axis=1)
        low1, tot1, _ = lower_share(sides, "box", w)
        g = pd.DataFrame({"tour": sides["tour"], "season": sides["season"], "low1": low1, "tot1": tot1,
                          "low2": low2, "tot2": tot2})
        for (tour, season), x in g.groupby(["tour", "season"]):
            rows.append({"tour": tour, "season": int(season), "window": w, "sides": len(x),
                         "box_evidence_today": float(x["tot1"].sum()), "box_evidence_p7": float(x["tot2"].sum()),
                         "box_lower_share_today": float(x["low1"].sum() / x["tot1"].sum()),
                         "box_lower_share_p7": float(x["low2"].sum() / x["tot2"].sum())})
    out = pd.DataFrame(rows)
    out["change_points"] = 100 * (out["box_lower_share_p7"] - out["box_lower_share_today"])
    out.attrs["flipped_rows"] = int(flip.sum())
    return out


# ------------------------------------------------------------------------------------------------
# Part 4: exposure

def per_match(sides: pd.DataFrame) -> pd.DataFrame:
    """One row per model match with both sides' exposure and dose, and the less-exposed side's facts."""
    s = sides.copy()
    s["main365"] = s[col("res", "365d", "MAIN")].astype(float)
    s["maincar"] = s[col("res", "career", "MAIN")].astype(float)
    for c in CHANNELS:
        _, tot, sh = lower_share(s, c, "365d")
        s[f"share_{c}"], s[f"tot_{c}"] = sh, tot
    a = s[s["side"] == "A"].set_index("match_id")
    b = s[s["side"] == "B"].set_index("match_id").reindex(a.index)
    m = a[["tour", "season", "era", "tournament_date", "level", "debut_season"]].copy()
    for k in ("main365", "maincar", "share_res", "share_box", "tot_box", "rank", "band"):
        m[f"{k}_a"], m[f"{k}_b"] = a[k], b[k]
    less_a = (m["main365_a"] < m["main365_b"]) | ((m["main365_a"] == m["main365_b"])
                                                    & (m["maincar_a"] <= m["maincar_b"]))
    m["less_side"] = np.where(less_a, "A", "B")
    for k in ("main365", "maincar", "share_res", "share_box", "rank", "band"):
        m[f"less_{k}"] = np.where(less_a, m[f"{k}_a"], m[f"{k}_b"])
    m["min_main365"] = np.fmin(m["main365_a"], m["main365_b"])
    m["min_maincar"] = np.fmin(m["maincar_a"], m["maincar_b"])
    for c in CHANNELS:
        m[f"max_share_{c}"] = np.fmax(m[f"share_{c}_a"], m[f"share_{c}_b"])
        m[f"absdiff_share_{c}"] = (m[f"share_{c}_a"] - m[f"share_{c}_b"]).abs()
        m[f"diff_share_{c}"] = m[f"share_{c}_a"] - m[f"share_{c}_b"]
    return m


def exposure_tables(sides: pd.DataFrame, pm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    s = sides.copy()
    s["exp365"] = exposure_bin(s[col("res", "365d", "MAIN")])
    s["expcar"] = exposure_bin(s[col("res", "career", "MAIN")])
    rows = []
    for what, c in (("per side, MAIN results in 365 days", "exp365"), ("per side, MAIN results in the career", "expcar")):
        for keys in (["tour", "era"], ["tour", "era", "band"], ["tour", "era", "level"]):
            t = s.groupby(keys + [c], observed=True).size().rename("sides").reset_index()
            t["share"] = t["sides"] / t.groupby(keys)["sides"].transform("sum")
            t = t.rename(columns={c: "bucket"})
            t.insert(0, "measure", what)
            t.insert(1, "grouping", " x ".join(keys))
            rows.append(t)
    pm = pm.copy()
    pm["less_exp365"] = exposure_bin(pm["min_main365"])
    pm["less_low"] = pm["min_main365"] < 10
    for keys in (["tour", "era"], ["tour", "era", "level"]):
        t = pm.groupby(keys + ["less_exp365"], observed=True).size().rename("sides").reset_index()
        t["share"] = t["sides"] / t.groupby(keys)["sides"].transform("sum")
        t = t.rename(columns={"less_exp365": "bucket", "sides": "matches"})
        t.insert(0, "measure", "per match, the less-exposed side's MAIN results in 365 days")
        t.insert(1, "grouping", " x ".join(keys))
        rows.append(t)
    expo = pd.concat(rows, ignore_index=True)
    # the cross: the less-exposed side's exposure against its own 365-day lower-level share, and who he is
    pm["less_share_bin_res"] = bin_of(pm["less_share_res"], SHARE_BINS, "no evidence")
    pm["less_share_bin_box"] = bin_of(pm["less_share_box"], SHARE_BINS, "no evidence")
    cross = []
    for keys in (["tour", "era", "less_exp365", "less_share_bin_res"], ["tour", "era", "less_exp365", "less_band"],
                 ["tour", "era", "less_exp365", "less_share_bin_box"], ["tour", "era", "less_exp365", "level"]):
        t = pm.groupby(keys, observed=True).size().rename("matches").reset_index()
        t["share_within_exposure_bucket"] = t["matches"] / t.groupby(keys[:3])["matches"].transform("sum")
        t = t.rename(columns={keys[3]: "value"})
        t.insert(0, "crossed_with", keys[3])
        cross.append(t)
    cross = pd.concat(cross, ignore_index=True)
    summ = {}
    for (tour, era), g in pm.groupby(["tour", "era"]):
        summ[f"{tour} {era}"] = {"matches": int(len(g)), "less_exposed_under_10_main_365d": float(g["less_low"].mean()),
                                 "less_exposed_zero_main_365d": float((g["min_main365"] == 0).mean()),
                                 "median_less_exposed_main_365d": float(g["min_main365"].median())}
    summ["all"] = {"matches": int(len(pm)), "less_exposed_under_10_main_365d": float(pm["less_low"].mean())}
    return expo, cross, summ


# ------------------------------------------------------------------------------------------------
# Part 5: where the model is weak against the close (results of seasons <= 2024 only)

def strata_of(pm: pd.DataFrame) -> dict[str, pd.Series]:
    """{family: label per match} for the pre-chosen strata (see STRATA at the top)."""
    out = {"all": pd.Series("all", index=pm.index)}
    out["exposure_365d"] = pd.Series(exposure_bin(pm["min_main365"]), index=pm.index)
    out["exposure_career"] = pd.Series(exposure_bin(pm["min_maincar"]), index=pm.index)
    for c in CHANNELS:
        out[f"dose_{c}_max"] = pd.Series(bin_of(pm[f"max_share_{c}"], SHARE_BINS, "no evidence"), index=pm.index)
        out[f"dose_{c}_absdiff"] = pd.Series(bin_of(pm[f"absdiff_share_{c}"], DIFF_BINS, "a side without evidence"),
                                             index=pm.index)
    lowx = np.where(pm["min_main365"] < 10, "less-exposed side <10 MAIN in 365d", "both sides >=10")
    dose = np.where(pm["max_share_box"] >= 0.5, "max box lower share >=50%", "max box lower share <50%")
    out["exposure_x_dose"] = pd.Series(np.char.add(np.char.add(lowx.astype(str), " | "), dose.astype(str)),
                                       index=pm.index)
    return out


def fit_cluster(Z: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Logistic regression (no implicit intercept) with a cluster-sandwich SE (G / (G - 1))."""
    from scipy.special import expit
    from src.eda.serve_speed_tabpfn import common as SC
    beta, _ = SC.fit_logistic(Z, y)
    p = expit(Z @ beta)
    H = (Z.T * (p * (1 - p))) @ Z
    Hinv = np.linalg.pinv(H)
    sc = Z * (y - p)[:, None]
    _, ix = np.unique(clusters, return_inverse=True)
    G = int(ix.max()) + 1
    S = np.zeros((G, Z.shape[1]))
    np.add.at(S, ix, sc)
    cov = Hinv @ (S.T @ S * (G / max(G - 1, 1))) @ Hinv
    return beta, np.sqrt(np.maximum(np.diag(cov), 0))


def heterogeneity(d: np.ndarray, labels: np.ndarray, clusters: np.ndarray, min_n: int = 50) -> dict:
    """Wald test that a per-match quantity d (the gain in mLL) has the same mean in every stratum with at least min_n
    matches; the strata means' covariance is cluster-robust (G / (G - 1)), clusters the 4-week blocks. The seeds'
    variance is left out (small beside the blocks')."""
    from scipy.stats import chi2
    labs = [v for v in pd.unique(labels) if (labels == v).sum() >= min_n]
    if len(labs) < 2:
        return {"strata": len(labs), "chi2": np.nan, "df": 0, "p_value": np.nan}
    _, ix = np.unique(clusters, return_inverse=True)
    G = int(ix.max()) + 1
    means, U = [], np.zeros((G, len(labs)))
    for k, v in enumerate(labs):
        m = labels == v
        mu = float(d[m].mean())
        means.append(mu)
        np.add.at(U[:, k], ix[m], (d[m] - mu) / m.sum())
    V = U.T @ U * G / (G - 1)
    Cm = np.zeros((len(labs) - 1, len(labs)))
    Cm[:, 0], Cm[np.arange(len(labs) - 1), np.arange(1, len(labs))] = -1.0, 1.0
    diff = Cm @ np.array(means)
    W = float(diff @ np.linalg.pinv(Cm @ V @ Cm.T) @ diff)
    return {"strata": len(labs), "chi2": W, "df": len(labs) - 1, "p_value": float(chi2.sf(W, len(labs) - 1))}


def outcomes_through_2024(model_frame: Path) -> pd.Series:
    """a_won of seasons <= 2024, after checking that those rows are all events before 30 Dec 2024 (the holdout's
    start): the selection is verified on dates alone, then the result column is read with the same filter."""
    sel = pd.read_parquet(model_frame, columns=["match_id", "season", "tournament_date"],
                          filters=[("season", "<=", 2024)])
    CM.assert_no_holdout_outcomes(sel["tournament_date"], "part 5 outcomes")
    y = pd.read_parquet(model_frame, columns=["match_id", "season", "tournament_date", "a_won"],
                        filters=[("season", "<=", 2024)])
    if len(y) != len(sel) or int(y["season"].max()) > 2024:
        raise RuntimeError("the outcome read differs from the checked selection")
    CM.assert_no_holdout_outcomes(y["tournament_date"], "part 5 outcomes")
    return pd.Series(y["a_won"].astype(float).to_numpy(), index=y["match_id"].astype(str).to_numpy())


def scores(pm: pd.DataFrame, model: str = "reference") -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """The model (both stages, and stage 1 alone) against its frame's recalibrated close, 2020-2024 (2019 only
    calibrates), debut seasons out, by stratum. compare.py's loaders and recipe (current_best_model/compare.py:76-110,
    228-292); intervals: serve_speed_tabpfn/score.paired_stats (4-week blocks plus the seeds' variance)."""
    from scipy.stats import norm
    from src.eda.current_best_model import compare as CP
    from src.eda.current_best_model import reference as R
    from src.eda.serve_speed_tabpfn import common as SC
    from src.eda.serve_speed_tabpfn import score as SS

    name, P, folder = CP.candidate(model)
    frame = CP.inputs_frame(P)
    y = outcomes_through_2024(P.model_frame)
    info = CP.scoring_info(frame, frame, y, y, 2024)
    CM.assert_no_holdout_outcomes(info["tournament_date"], "part 5 scoring rows")
    seasons = tuple(range(CP.FIT_FROM, 2025))
    test = tuple(range(CP.SCORE_FROM, 2025))
    p = CP.seed_table(P, frame, seasons).reindex(info.index)
    if p.isna().any().any():
        raise SystemExit("forecasts missing")
    if folder is not None and (folder / "speed_columns.parquet").exists():
        z = pd.read_parquet(folder / "speed_columns.parquet", columns=["match_id", "spd_L_B"]) \
            .astype({"match_id": str}).set_index("match_id")["spd_L_B"]
    else:
        z = R.speed_column("reference")
    eta = pd.Series(SC.lg(p.mean(axis=1).to_numpy()), index=p.index)
    par2 = CP.walk_forward(eta, info, z, test)
    par1 = CP.walk_forward(eta, info, None, test)
    keep = (~info["debut"]) & info["season"].isin(list(test))
    pool = info.index[keep.to_numpy()]
    strata = strata_of(pm.reindex(pool))
    missing = int(pm.reindex(pool)["tour"].isna().sum())
    rows = []
    for fam in STRATA:
        lab = strata[fam]
        for tour in ("both", "atp", "wta"):
            for val in sorted(lab.dropna().unique()):
                mask = (lab == val).to_numpy()
                if tour != "both":
                    mask = mask & (info.loc[pool, "tour"] == tour).to_numpy()
                ids = pool[mask]
                if len(ids) < 50:
                    rows.append({"family": fam, "stratum": val, "tour": tour, "matches": int(len(ids)),
                                 "note": "fewer than 50 matches: not scored"})
                    continue
                yy = info.loc[ids, "y"].to_numpy(float)
                f2 = CP.forecasts(p, info, par2, z, ids)
                f1 = CP.forecasts(p, info, par1, None, ids)
                cl = CP.close_forecast(info, "p_ref", test, ids)
                blk, wk = info.loc[ids, "block"].to_numpy(), info.loc[ids, "week"].to_numpy()
                rec = {"family": fam, "stratum": val, "tour": tour, "matches": int(len(ids)),
                       "ll_model": float(SC.ll(f2[0], yy).mean()), "ll_stage1": float(SC.ll(f1[0], yy).mean()),
                       "ll_close": float(SC.ll(cl[0], yy).mean())}
                for tag, arm in (("", f2), ("stage1_", f1)):
                    r = SS.paired_stats(SC.ll(cl[0], yy), SC.ll(arm[0], yy), SS.seed_loss(cl[1], yy),
                                        SS.seed_loss(arm[1], yy), blk, wk)
                    rec[f"{tag}gain"] = r["estimate"]
                    rec[f"{tag}lo"], rec[f"{tag}hi"] = r["lo"], r["hi"]
                    rec[f"{tag}p_better"] = float(norm.cdf(r["estimate"] / r["se"])) if r["se"] > 0 else np.nan
                    rec[f"{tag}reading"] = "better" if r["lo"] > 0 else "worse" if r["hi"] < 0 else "unresolved"
                for tag, q in (("close_raw", info.loc[ids, "p_ref"].to_numpy(float)), ("close_recal", cl[0]),
                               ("model", f2[0])):
                    b, se = fit_cluster(SC.lg(q)[:, None], yy, blk)
                    rec[f"slope_{tag}"], rec[f"slope_{tag}_se"] = float(b[0]), float(se[0])
                if fam.endswith("absdiff") and val != "a side without evidence":
                    c = "box" if "_box_" in fam else "res"
                    d = pm.loc[ids, f"diff_share_{c}"].to_numpy(float)
                    focal_a = d >= 0                     # the side with the larger lower-level share
                    yf = np.where(focal_a, yy, 1 - yy)
                    for tag, q in (("close", cl[0]), ("model", f2[0])):
                        qf = np.where(focal_a, q, 1 - q)
                        Z = np.column_stack([np.ones(len(ids)), SC.lg(qf)])
                        b, se = fit_cluster(Z, yf, blk)
                        rec[f"intercept_{tag}_for_more_lower_side"] = float(b[0])
                        rec[f"intercept_{tag}_se"] = float(se[0])
                rows.append(rec)
    out = pd.DataFrame(rows)
    # are the strata's gains different from each other? (both stages against the close, per family and tour)
    y_all = info.loc[pool, "y"].to_numpy(float)
    d_all = 1000 * (SC.ll(CP.close_forecast(info, "p_ref", test, pool)[0], y_all)
                    - SC.ll(CP.forecasts(p, info, par2, z, pool)[0], y_all))
    blk_all, tour_all = info.loc[pool, "block"].to_numpy(), info.loc[pool, "tour"].to_numpy()
    het = []
    for fam in STRATA[1:]:
        lab = strata[fam].to_numpy().astype(str)
        for tour in ("both", "atp", "wta"):
            m = np.ones(len(pool), bool) if tour == "both" else tour_all == tour
            het.append({"family": fam, "tour": tour, **heterogeneity(d_all[m], lab[m], blk_all[m])})
    het = pd.DataFrame(het)
    allrow = out[(out["family"] == "all") & (out["tour"] == "both")].iloc[0]
    summ = {"model": name, "scored_seasons": [test[0], test[-1]], "results_read_through": 2024,
            "matches_scored": int(len(pool)), "matches_without_composition": missing,
            "harness_check_all_matches_gain_vs_close": [float(allrow["gain"]), float(allrow["lo"]), float(allrow["hi"])],
            "reference_readme_value": "+1.37 [+0.67, +2.08] (comparisons/reference/scores.csv: 1.374456)",
            "heterogeneity": het.to_dict("records")}
    return out, summ, het


# ------------------------------------------------------------------------------------------------

def run(stage0_dir: Path = CM.STAGE0_DIR, frame_path: Path = CM.FRAME, label: str = LABEL, out: Path | None = None,
        timing_path: Path | None = CM.TIMING, model: str = "reference", with_scores: bool = True,
        spot: int = SPOT_CHECKS) -> dict:
    stage0_dir, frame_path = Path(stage0_dir), Path(frame_path)
    out = Path(out) if out else CM.OUT / "composition" / label
    out.mkdir(parents=True, exist_ok=True)
    log(f"Stage 0 {stage0_dir}; frame {frame_path}; out {out}")
    m = CM.load_matches(stage0_dir, columns=["match_id", "tour", "map_level", "tournament_id", "tournament_date",
                                             "round_order", "status", "has_box"])
    pl = CM.load_players(stage0_dir, columns=["match_id", "player_id", "side", "rank"])
    hist, origin = history_table(m, pl)
    log(f"history: {len(hist):,} player rows, {hist['pcode'].nunique():,} players")
    ix = Index(hist)
    frame = CM.load_frame(frame_path, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                "in_level"])
    tg, tinfo = targets_table(hist, frame, pl)
    log(f"targets: {len(tg):,} sides of {tinfo['matches_found_in_stage0']:,} matches")
    sides = side_counts(ix, tg)
    log("counts done")
    sc = spot_check(ix, hist, tg, sides, n=spot)
    log(f"spot check: {sc['wrong']} wrong of {sc['values_checked']:,}")
    write_sides(sides, out / "sides.parquet")
    timing = pd.read_parquet(timing_path, columns=["match_id", "es", "lf"]) if timing_path else None
    cc, ccs = clock_check(ix, hist, tg, timing)
    cc.to_csv(out / "clock_check.csv", index=False)
    log(f"clock check: {ccs}")
    full = shares(sides, ["tour", "season", "level", "band"])
    full.to_csv(out / "shares_full.csv.gz", index=False, compression="gzip")
    mg = margins(sides)
    mg.to_csv(out / "shares.csv", index=False)
    inputs_dose(sides).to_csv(out / "inputs_dose.csv", index=False)
    log("shares written")
    reg, anyr = itf_regime(sides)
    reg.to_csv(out / "itf_regime.csv", index=False)
    anyr.to_csv(out / "itf_any.csv", index=False)
    prev, un, prs = itf_preview(sides, hist, tg, origin)
    prev.to_csv(out / "itf_preview.csv", index=False)
    un.to_csv(out / "itf_preview_unique.csv", index=False)
    scen = p7_scenario(hist, tg, sides)
    scen.to_csv(out / "itf_p7_scenario.csv", index=False)
    prs["p7_scenario_player_rows_given_a_box_score"] = scen.attrs["flipped_rows"]
    pm = per_match(sides)
    expo, cross, es = exposure_tables(sides, pm)
    expo.to_csv(out / "exposure.csv", index=False)
    cross.to_csv(out / "exposure_cross.csv", index=False)
    log("ITF and exposure written")
    summary = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "label": label,
        "stage0_dir": rel(stage0_dir), "frame": rel(frame_path), "timing": rel(timing_path) if timing_path else None,
        "sha256": {"stage0_matches": sha256_file(stage0_dir / "stage0_matches.parquet"),
                   "stage0_match_players": sha256_file(stage0_dir / "stage0_match_players.parquet"),
                   "frame": sha256_file(frame_path)},
        "stage0_matches": int(len(m)), "stage0_buckets": m["bucket"].value_counts().to_dict(),
        "history_rows": int(len(hist)), "players": int(hist["pcode"].nunique()),
        "origin": str(origin.date()), "targets": tinfo, "spot_check": sc, "clock_check": ccs,
        "windows": list(WINDOW_NAMES), "itf_preview": prs, "exposure": es,
        "holdout": "parts 1-4 read no outcome; part 5 reads results of seasons <= 2024 only",
    }
    if with_scores:
        sco, ss, het = scores(pm, model)
        sco.to_csv(out / "scores.csv", index=False)
        het.to_csv(out / "scores_heterogeneity.csv", index=False)
        summary["scores"] = ss
        log(f"scores: {ss['harness_check_all_matches_gain_vs_close']}")
    summary["seconds"] = round(time.time() - T0, 1)
    (out / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log(f"written {out}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0-dir", default=str(CM.STAGE0_DIR), help="folder with stage0_matches/_match_players")
    ap.add_argument("--frame", default=str(CM.FRAME), help="the model frame naming the model's matches")
    ap.add_argument("--timing", default=str(CM.TIMING), help="the match timeline (es, lf), or '' to skip the check")
    ap.add_argument("--label", default=LABEL)
    ap.add_argument("--out", default=None, help="default data/studies/lower_level_evidence/composition/<label>")
    ap.add_argument("--model", default="reference", help="part 5's forecasts: reference, or a built folder")
    ap.add_argument("--no-scores", action="store_true", help="skip part 5")
    ap.add_argument("--spot", type=int, default=SPOT_CHECKS, help="sides recounted by brute force")
    a = ap.parse_args()
    run(Path(a.stage0_dir), Path(a.frame), a.label, Path(a.out) if a.out else None,
        Path(a.timing) if a.timing else None, a.model, not a.no_scores, a.spot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
