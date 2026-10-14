"""Level-translation hooks for the candidate build of team role 08 (lower-level evidence): the offsets' estimation and
the translation of a lower-level match's contribution to the 17 one-step forms and to `points_52w`.

The plan, fixed before any result: data/studies/lower_level_evidence/candidates/preregistration.md.

SWITCHED OFF BY DEFAULT. Every hooked function returns its input unchanged unless the environment variable LLE_TRANSLATE
holds the path of a JSON config, so a sandbox patched with these hooks builds exactly the template while it is unset.
The config:
    forms_offsets     CSV of delta_z[statistic, channel, tour, bucket] (written here by the first full-history call
                      when it is missing and estimate_forms is true)
    rates_offsets     CSV of delta_rate[statistic, tour, bucket] (estimated before the build: offsets.py)
    record_dir        where the hook writes its records (the untranslated z it estimated from, hook_calls.jsonl)
    estimate_forms    true: estimate the form offsets from the build's own z if the file is missing
    scale             multiplies every offset (1 for the candidate; 0 and 0.5 for the linearity gate G4)
    stage0_matches    optional: Stage 0's match table (match_id -> map_level); default this tree's own

The two sandbox patches (sandbox_patch.diff), each two lines:
    stageB_adjperf.build      Z = translate_forms(ctx.rows, ctx.box_idx, Z)       after the per-match z, before step 3
    stage4.history_sums       x = translate_counts(rows, s, x, d, ok)             before the sums

The rule (pre-registration):
    forms   delta_z = the mean over player-seasons of 2010-2018 with at least 3 box rows with a finite z at MAIN and at
            the bucket of (mean z at the bucket - mean z at MAIN); z <- z - scale * delta_z for every box row of a
            lower-level match (MAIN and TEAM: 0), after the clip, before the decay-and-shrink step
    rates   the same on the pooled raw rate of the season's rows Stage 4 admits (sum x / sum d); x <- x - scale * d *
            delta_rate for spw and rpw
    cells   TQ, GSQ, CH, CHQ estimated; fewer than 100 player-seasons -> the both-tours estimate if it has 100, else
            0; ITF and ITFQ take CH's and CHQ's final values (placeholders: their box scores exist only in the holdout)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402   (bucket: Stage 0's map_level -> the study's)

ENV = "LLE_TRANSLATE"
STAGE0_MATCHES = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
TOURS = ("atp", "wta")
ESTIMATED = ("TQ", "GSQ", "CH", "CHQ")
PLACEHOLDER = {"ITF": "CH", "ITFQ": "CHQ"}
ZERO = ("MAIN", "TEAM")
BUCKETS = ("MAIN",) + ESTIMATED + tuple(PLACEHOLDER) + ("TEAM",)
YEARS = (2010, 2018)
MIN_ROWS = 3
MIN_PLAYER_SEASONS = 100
PROFILE = ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved", "bp_faced_pg", "brk", "bp_conv",
           "rpw_first", "rpw_second")
DEFENCE = ("ace", "df", "first_in", "bp_faced_pg")
FORM_SPECS = tuple([(s, "adjperf") for s in PROFILE] + [("tpw", "adjperf")] + [(s, "adjdef") for s in DEFENCE])
RATE_STATS = ("spw", "rpw")
VERIFY_TOL = 1e-12


def input_name(stat: str, channel: str) -> str:
    """The model input a (statistic, channel) pair feeds."""
    if (stat, channel) == ("tpw", "adjperf"):
        return "adjperf_tpw_2w"
    return f"form_{stat}" if channel == "adjperf" else f"formdef_{stat}"


def form_key(stat: str, channel: str) -> str:
    return f"{channel}|{stat}"


# ------------------------------------------------------------------------------------------------
# The configuration

def config() -> dict | None:
    """The hook's config, or None when LLE_TRANSLATE is unset or empty (the unpatched behaviour)."""
    path = os.environ.get(ENV, "").strip()
    if not path:
        return None
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    for k in ("forms_offsets", "rates_offsets", "record_dir", "scale"):
        if k not in cfg:
            raise KeyError(f"{path}: the hook's config lacks {k!r}")
    cfg["scale"] = float(cfg["scale"])
    cfg["_path"] = path
    return cfg


def record(cfg: dict, entry: dict) -> None:
    d = Path(cfg["record_dir"])
    d.mkdir(parents=True, exist_ok=True)
    entry = {"time_utc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "pid": os.getpid(),
             "config": cfg["_path"], "scale": cfg["scale"], **entry}
    with (d / "hook_calls.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")


def log(msg: str) -> None:
    print(f"[translate_hooks] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Buckets

_BUCKET_CACHE: dict = {}


def bucket_map(stage0_matches: Path) -> pd.Series:
    """match_id -> the study's bucket (common.bucket of Stage 0's map_level), cached per file."""
    p = Path(stage0_matches)
    st = p.stat()
    key = (str(p), st.st_size, st.st_mtime_ns)
    if key not in _BUCKET_CACHE:
        m = pd.read_parquet(p, columns=["match_id", "map_level"])
        _BUCKET_CACHE.clear()
        _BUCKET_CACHE[key] = pd.Series(LC.bucket(m["map_level"]).astype(str).to_numpy(), index=m["match_id"].to_numpy())
    return _BUCKET_CACHE[key]


def buckets_of(match_ids, cfg: dict | None = None) -> np.ndarray:
    path = Path((cfg or {}).get("stage0_matches") or STAGE0_MATCHES)
    b = bucket_map(path).reindex(np.asarray(match_ids)).to_numpy()
    if pd.isna(b).any():
        raise KeyError(f"{int(pd.isna(b).sum())} rows' matches are not in {path}")
    return b.astype(str)


# ------------------------------------------------------------------------------------------------
# Estimation

def cluster_se_mean(values: np.ndarray, clusters: np.ndarray) -> tuple[float, int]:
    """SE of a mean with a cluster sandwich and the G / (G - 1) factor; (nan, G) with fewer than 2 clusters."""
    v = np.asarray(values, float)
    if len(v) == 0:
        return np.nan, 0
    _, ix = np.unique(np.asarray(clusters), return_inverse=True)
    G = int(ix.max()) + 1
    if G < 2:
        return np.nan, G
    infl = np.bincount(ix, weights=v - v.mean())
    return float(np.sqrt(G / (G - 1) * np.dot(infl, infl)) / len(v)), G


def season_diffs(level_table: pd.DataFrame, bucket: str) -> pd.DataFrame:
    """Per qualifying player-season (>= MIN_ROWS rows at MAIN and at the bucket): tour, player, year and the value at
    the bucket minus the value at MAIN. level_table: one row per (tour, player, year, bucket) with columns value, n."""
    main = level_table[level_table["bucket"] == "MAIN"].set_index(["tour", "player", "year"])
    low = level_table[level_table["bucket"] == bucket].set_index(["tour", "player", "year"])
    both = main.index.intersection(low.index)
    a, b = main.loc[both], low.loc[both]
    ok = ((a["n"] >= MIN_ROWS) & (b["n"] >= MIN_ROWS)).to_numpy()
    out = pd.DataFrame({"tour": both.get_level_values("tour")[ok], "player": both.get_level_values("player")[ok],
                        "year": both.get_level_values("year")[ok],
                        "diff": (b["value"].to_numpy() - a["value"].to_numpy())[ok]})
    return out[np.isfinite(out["diff"].to_numpy())].reset_index(drop=True)


def offsets_from_levels(level_tables: dict[str, pd.DataFrame], kind: str) -> pd.DataFrame:
    """The offsets table from per-key level tables ({key: (tour, player, year, bucket, value, n)}): every key x tour x
    bucket of BUCKETS, with the own-tour estimate, the both-tours estimate, the value used and its source."""
    rows = []
    for key, lt in level_tables.items():
        used = {}
        for b in ESTIMATED:
            d = season_diffs(lt, b)
            se_both, g_both = cluster_se_mean(d["diff"].to_numpy(), d["player"].to_numpy())
            both = {"n": int(len(d)), "est": float(d["diff"].mean()) if len(d) else np.nan, "se": se_both,
                    "players": g_both}
            for t in TOURS:
                dt = d[d["tour"] == t]
                se, g = cluster_se_mean(dt["diff"].to_numpy(), dt["player"].to_numpy())
                est = float(dt["diff"].mean()) if len(dt) else np.nan
                if len(dt) >= MIN_PLAYER_SEASONS:
                    val, src = est, "own tour"
                elif both["n"] >= MIN_PLAYER_SEASONS:
                    val, src = both["est"], "both tours (own tour under 100 player-seasons)"
                else:
                    val, src = 0.0, "zero (under 100 player-seasons on both tours)"
                used[(t, b)] = val
                rows.append({"kind": kind, "key": key, "tour": t, "bucket": b, "player_seasons": int(len(dt)),
                             "players": g, "estimate": est, "se": se,
                             "lo": est - 1.96 * se if np.isfinite(se) else np.nan,
                             "hi": est + 1.96 * se if np.isfinite(se) else np.nan,
                             "both_tours_player_seasons": both["n"], "both_tours_players": both["players"],
                             "both_tours_estimate": both["est"], "both_tours_se": both["se"],
                             "value_used": float(val), "source": src})
        for t in TOURS:
            for b, src_b in PLACEHOLDER.items():
                rows.append({"kind": kind, "key": key, "tour": t, "bucket": b, "value_used": float(used[(t, src_b)]),
                             "source": f"placeholder: {src_b}'s value (no box score before the holdout)"})
            for b in ZERO:
                rows.append({"kind": kind, "key": key, "tour": t, "bucket": b, "value_used": 0.0,
                             "source": "zero by definition" if b == "MAIN" else "zero: team events are not translated"})
    return pd.DataFrame(rows)


def in_years(year: np.ndarray) -> np.ndarray:
    y = np.asarray(year)
    return (y >= YEARS[0]) & (y <= YEARS[1])


def form_level_table(z: np.ndarray, tour, player, year, bucket) -> pd.DataFrame:
    """(tour, player, year, bucket) -> the mean z and the count of finite z, seasons 2010-2018."""
    z = np.asarray(z, float)
    m = np.isfinite(z) & in_years(year) & np.isin(bucket, ("MAIN",) + ESTIMATED)
    df = pd.DataFrame({"tour": np.asarray(tour)[m], "player": np.asarray(player)[m], "year": np.asarray(year)[m],
                       "bucket": np.asarray(bucket)[m], "z": z[m]})
    g = df.groupby(["tour", "player", "year", "bucket"], sort=True)["z"].agg(["mean", "size"]).reset_index()
    return g.rename(columns={"mean": "value", "size": "n"})


def rate_level_table(x: np.ndarray, d: np.ndarray, ok: np.ndarray, tour, player, year, bucket) -> pd.DataFrame:
    """(tour, player, year, bucket) -> the pooled rate (sum x / sum d) and the count of admitted rows, 2010-2018."""
    x, d = np.asarray(x, float), np.asarray(d, float)
    m = np.asarray(ok, bool) & (d > 0) & in_years(year) & np.isin(bucket, ("MAIN",) + ESTIMATED)
    df = pd.DataFrame({"tour": np.asarray(tour)[m], "player": np.asarray(player)[m], "year": np.asarray(year)[m],
                       "bucket": np.asarray(bucket)[m], "x": x[m], "d": d[m]})
    g = df.groupby(["tour", "player", "year", "bucket"], sort=True).agg(x=("x", "sum"), d=("d", "sum"),
                                                                         n=("x", "size")).reset_index()
    g["value"] = g["x"] / g["d"]
    return g[["tour", "player", "year", "bucket", "value", "n"]]


def estimate_forms(Z: dict, tour, player, year, bucket) -> pd.DataFrame:
    """delta_z for every (statistic, channel) of FORM_SPECS present in Z (per box row, untranslated)."""
    tables = {form_key(s, ch): form_level_table(Z[(s, ch)], tour, player, year, bucket) for s, ch in FORM_SPECS
              if (s, ch) in Z}
    out = offsets_from_levels(tables, "forms")
    out["input"] = [input_name(k.split("|")[1], k.split("|")[0]) for k in out["key"]]
    return out


def estimate_rates(xd: dict, tour, player, year, bucket) -> pd.DataFrame:
    """delta_rate for spw and rpw from {stat: (x, d, ok)} (Stage 4's stat_xd)."""
    tables = {s: rate_level_table(*xd[s], tour, player, year, bucket) for s in RATE_STATS if s in xd}
    return offsets_from_levels(tables, "rates")


def full_history(year) -> bool:
    y = np.asarray(year)
    return len(y) > 0 and int(y.min()) <= YEARS[0] and int(y.max()) >= YEARS[1]


def read_offsets(path) -> pd.DataFrame:
    t = pd.read_csv(path)
    need = {"key", "tour", "bucket", "value_used"}
    if not need <= set(t.columns):
        raise ValueError(f"{path}: an offsets table needs {sorted(need)}")
    return t


def lookup(table: pd.DataFrame, key: str, tour: np.ndarray, bucket: np.ndarray) -> np.ndarray:
    """Per row: the offset used for (key, tour, bucket); a bucket or tour the table lacks is an error."""
    t = table[table["key"] == key]
    if t.empty:
        raise KeyError(f"no offsets for {key}")
    m = {(r.tour, r.bucket): float(r.value_used) for r in t.itertuples(index=False)}
    keys = list(zip(np.asarray(tour).tolist(), np.asarray(bucket).tolist()))
    missing = {k for k in set(keys) if k not in m}
    if missing:
        raise KeyError(f"{key}: no offset for {sorted(missing)[:5]}")
    return np.array([m[k] for k in keys], dtype=float)


def same_offsets(a: pd.DataFrame, b: pd.DataFrame) -> tuple[bool, float]:
    """Whether two offsets tables agree on every value used (and estimate), to VERIFY_TOL."""
    cols = ["key", "tour", "bucket"]
    j = a.merge(b, on=cols, how="outer", suffixes=("_a", "_b"), indicator=True)
    if not (j["_merge"] == "both").all():
        return False, np.inf
    gap = 0.0
    for c in ("value_used", "estimate"):
        x, y = j[f"{c}_a"].to_numpy(float), j[f"{c}_b"].to_numpy(float)
        if not np.array_equal(np.isnan(x), np.isnan(y)):
            return False, np.inf
        both = np.isfinite(x) & np.isfinite(y)
        if both.any():
            gap = max(gap, float(np.max(np.abs(x[both] - y[both]))))
    return gap <= VERIFY_TOL, gap


# ------------------------------------------------------------------------------------------------
# The hooks

def translate_forms(rows: pd.DataFrame, box_idx: np.ndarray, Z: dict) -> dict:
    """Stage B's per-match z with every lower-level box row translated: z - scale * delta_z[statistic, channel, tour,
    bucket]. Unchanged (the same dict) when the hook is off or Z holds none of the 17 (statistic, channel) pairs."""
    cfg = config()
    if cfg is None:
        return Z
    keys = [k for k in FORM_SPECS if k in Z]
    if not keys:
        return Z
    t0 = time.time()
    mids = rows["match_id"].to_numpy()[box_idx]
    bucket = buckets_of(mids, cfg)
    tour = rows["tour"].to_numpy()[box_idx].astype(str)
    year = rows["year"].to_numpy()[box_idx].astype(int)
    player = rows["player_id"].to_numpy()[box_idx].astype(str)
    path = Path(cfg["forms_offsets"])
    full = full_history(year)
    action = "read"
    if not path.exists():
        if not (cfg.get("estimate_forms") and full):
            raise FileNotFoundError(f"{path}: no form offsets, and this call cannot estimate them (estimate_forms "
                                    f"{cfg.get('estimate_forms')}, full history {full})")
        table = estimate_forms({k: Z[k] for k in keys}, tour, player, year, bucket)
        path.parent.mkdir(parents=True, exist_ok=True)
        table.to_csv(path, index=False, float_format="%.17g")
        rec = pd.DataFrame({"row": np.asarray(box_idx, dtype="int64"), "match_id": mids, "player_id": player,
                            "tour": tour, "year": year, "bucket": bucket})
        for s, ch in keys:
            rec[f"z_{ch}_{s}"] = np.asarray(Z[(s, ch)], dtype="float64")
        Path(cfg["record_dir"]).mkdir(parents=True, exist_ok=True)
        rec.to_parquet(Path(cfg["record_dir"]) / "forms_z_untranslated.parquet", index=False, compression="zstd")
        action = "estimated"
    table = read_offsets(path)
    if full and action == "read":
        again = estimate_forms({k: Z[k] for k in keys}, tour, player, year, bucket)
        ok, gap = same_offsets(table, again)
        if not ok:
            raise RuntimeError(f"the stored form offsets ({path}) differ from this build's z (largest gap {gap})")
        action = "verified"
    scale = cfg["scale"]
    out = dict(Z)
    lower = np.isin(bucket, LC.LOWER)
    for s, ch in keys:
        delta = lookup(table, form_key(s, ch), tour, bucket)
        out[(s, ch)] = np.asarray(Z[(s, ch)], dtype="float64") - scale * delta
    record(cfg, {"hook": "forms", "action": action, "full_history": full, "box_rows": int(len(box_idx)),
                 "lower_rows": int(lower.sum()), "keys": [form_key(s, ch) for s, ch in keys],
                 "seconds": round(time.time() - t0, 2)})
    log(f"forms: {action}; {len(keys)} (statistic, channel) pairs; {int(lower.sum()):,} of {len(box_idx):,} box rows "
        f"lower-level; scale {scale}")
    return out


def translate_counts(rows: pd.DataFrame, stat: str, x: np.ndarray, d: np.ndarray, ok: np.ndarray) -> np.ndarray:
    """Stage 4's history count x with every lower-level row of spw and rpw translated: x - scale * d * delta_rate.
    Unchanged (the same array) when the hook is off or the statistic is not spw or rpw."""
    if stat not in RATE_STATS:
        return x
    cfg = config()
    if cfg is None:
        return x
    t0 = time.time()
    mids = rows["match_id"].to_numpy()
    bucket = buckets_of(mids, cfg)
    tour = rows["tour"].to_numpy().astype(str)
    year = rows["year"].to_numpy().astype(int)
    table = read_offsets(cfg["rates_offsets"])
    action = "read"
    if full_history(year):
        player = rows["player_id"].to_numpy().astype(str)
        again = estimate_rates({stat: (x, d, ok)}, tour, player, year, bucket)
        ok_, gap = same_offsets(table[table["key"] == stat], again)
        if not ok_:
            raise RuntimeError(f"the stored rate offsets of {stat} differ from this build's rows (largest gap {gap})")
        action = "verified"
    delta = lookup(table, stat, tour, bucket)
    okb = np.asarray(ok, bool)
    out = np.where(okb, np.asarray(x, float) - cfg["scale"] * np.asarray(d, float) * delta, np.asarray(x, float))
    lower = okb & np.isin(bucket, LC.LOWER)
    record(cfg, {"hook": "rates", "stat": stat, "action": action, "full_history": full_history(year),
                 "rows": int(len(rows)), "lower_rows": int(lower.sum()), "seconds": round(time.time() - t0, 2)})
    log(f"rates {stat}: {action}; {int(lower.sum()):,} lower-level rows of {int(okb.sum()):,} admitted; scale "
        f"{cfg['scale']}")
    return out
