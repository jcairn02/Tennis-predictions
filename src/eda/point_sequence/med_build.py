"""E1 mechanism gate, step 1: the pair table (previous match t -> next match t+1) with exposures, endpoints, covariates
and the women's fade markers. Definitions: data/studies/point_sequence/med_prereg.md (registered before any estimate).

Run:  ./python.sh src/eda/point_sequence/med_build.py

Reads (read-only): Stage 0 (predictability_diagnostic), timing.parquet, stage3_ratings.parquet, this study's
seq_matches / sequences / points_wta / wta_events. Writes data/studies/point_sequence/med_pairs.parquet and
med_build_summary.json. Computes no exposure-outcome contrast.

Closed holdout: every Stage 0 row dated on or after 1 Jan 2025 is masked before any status, score or box column is
used; a pair whose next match falls there is dropped and only counted.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import common as C  # noqa: E402
from src.eda.predictability_diagnostic import common as S0  # noqa: E402

OUT = C.OUT
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
RATINGS = S0.OUT / "stage3_ratings.parquet"
D_START = 18051    # 2019-06-04, days since 1970-01-01
D_REP = 18993      # 2022-01-01
D_HOLD = 20089     # 2025-01-01 (closed holdout from here)
MAX_GAP = 21
CAP_S = 300.0      # a gap between points counts at most 5 minutes toward playing time

CALL = "PhysioCalled"
MED = "MedicalTreatment"
INJ_REASONS = ("Injury", "Illness", "Heat")
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Exposure coding (pure functions, unit-tested in test/point_sequence/test_med.py)

def record_kind(name, reason) -> str | None:
    """call / cancel / treat / eval / toilet for one umpire-log record, None otherwise."""
    if name == CALL:
        return "call"
    if name == "PhysioCallCancelled":
        return "cancel"
    if name == "ToiletBreak":
        return "toilet"
    if name == MED:
        if reason == "PhysioCalled":
            return "call"
        if reason in ("PhysioCancelled", "NoTreatment"):
            return "cancel"
        if reason in ("TreatmentInProgress", "TreatmentComplete"):
            return "treat"
        if reason in ("PhysioEvaluationStarted", "PhysioArrived"):
            return "eval"
    return None


def treated_flag(calls: int, cancels: int, treats: int, evals: int) -> bool:
    """TREATED: a treatment record, a call not cancelled, or an evaluation with no call and no cancellation."""
    return bool(treats > 0 or calls > cancels or (evals > 0 and calls == 0 and cancels == 0))


def attribute_suspension(s_index: int, treated_sides: list[int], med_index: dict[int, list[int]]) -> int:
    """The side (1/2) an Injury/Illness/Heat suspension is attributed to, 0 if none: the only treated side, or,
    if both are treated, the side with the medical record nearest before the suspension (nearest after if none
    is before)."""
    if not treated_sides:
        return 0
    if len(treated_sides) == 1:
        return treated_sides[0]
    best_before, best_after = {}, {}
    for s in treated_sides:
        idx = np.asarray(med_index.get(s, []), dtype=float)
        before = idx[idx < s_index]
        after = idx[idx > s_index]
        best_before[s] = s_index - before.max() if before.size else np.inf
        best_after[s] = after.min() - s_index if after.size else np.inf
    if any(np.isfinite(v) for v in best_before.values()):
        return min(treated_sides, key=lambda s: (best_before[s], s))
    if any(np.isfinite(v) for v in best_after.values()):
        return min(treated_sides, key=lambda s: (best_after[s], s))
    return 0


def exposures(ev: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Per (key, side) exposure flags from the logs' non-point records."""
    ev = ev.rename(columns={"index": "idx"}).copy()
    ev["kind"] = [record_kind(n, r) for n, r in zip(ev["name"].to_numpy(object), ev["reason"].to_numpy(object))]
    own = ev[ev["kind"].notna() & ev["player_side_ab"].isin([1, 2])]
    cnt = own.groupby(["key", "player_side_ab", "kind"]).size().unstack("kind", fill_value=0)
    for k in ("call", "cancel", "treat", "eval", "toilet"):
        if k not in cnt.columns:
            cnt[k] = 0
    cnt = cnt.reset_index().rename(columns={"player_side_ab": "side_n"})
    cnt["side_n"] = cnt["side_n"].astype(int)
    cnt["treated"] = [treated_flag(a, b, c, d) for a, b, c, d in
                      zip(cnt["call"], cnt["cancel"], cnt["treat"], cnt["eval"])]
    cnt["toilet"] = cnt["toilet"] > 0
    # Injury / Illness / Heat suspensions, attributed to a treated player of the same log
    sus = ev[ev["name"].eq("Suspension") & ev["reason"].isin(INJ_REASONS)][["key", "idx", "reason"]]
    med = own[own["kind"].isin(["call", "cancel", "treat", "eval"])]
    med_idx = {k: {int(s): g2["idx"].astype(int).tolist() for s, g2 in g.groupby("player_side_ab")}
               for k, g in med.groupby("key")}
    tr = cnt[cnt["treated"]].groupby("key")["side_n"].apply(lambda s: sorted(int(v) for v in s)).to_dict()
    inj_rows, unattributed = [], 0
    by_reason = {r: 0 for r in INJ_REASONS}
    for key, sidx, reason in zip(sus["key"], sus["idx"], sus["reason"]):
        side = attribute_suspension(int(sidx), tr.get(key, []), med_idx.get(key, {}))
        if side == 0:
            unattributed += 1
        else:
            inj_rows.append((key, side))
            by_reason[reason] += 1
    inj = pd.DataFrame(inj_rows, columns=["key", "side_n"]).drop_duplicates()
    inj["injury"] = True
    cnt = cnt.merge(inj, on=["key", "side_n"], how="left")
    cnt["injury"] = cnt["injury"].astype("boolean").fillna(False).astype(bool) & cnt["treated"]
    audit = {"suspensions_injury_illness_heat": int(len(sus)), "attributed": int(len(inj_rows)),
             "unattributed_no_treated_player": int(unattributed), "attributed_by_reason": by_reason}
    return cnt[["key", "side_n", "call", "cancel", "treat", "eval", "treated", "injury", "toilet"]], audit


# ------------------------------------------------------------------------------------------------
# Loading

def load_rows() -> pd.DataFrame:
    """WTA player-match rows 2019-2025 with the holdout masked (not yet ordered)."""
    m = S0.load_matches(["match_id", "tour", "year", "level", "qualifying", "round", "surface", "tournament_id",
                         "status", "status_detail", "minutes"])
    m = m[m["tour"].eq("wta") & m["year"].between(2019, 2026)].copy()
    # deviation D1: the match day is timing's best-estimate day `obs` (the exact day, else the class median offset
    # inside the window); `start` is the tournament start date (timing.py: m["start"] = to_day(tournament_date))
    t = pd.read_parquet(TIMING, columns=["match_id", "obs", "exact"])
    m = m.merge(t, on="match_id", how="left", validate="one_to_one")
    mp = pd.read_parquet(S0.MATCH_PLAYERS, columns=["match_id", "player_id", "side", "won", "age",
                                                    "spw_n", "spw_d", "has_box"])
    rows = mp.merge(m, on="match_id", how="inner", validate="many_to_one")
    rows["day"] = rows["obs"].astype(float)
    # deviation D2: the holdout also covers the 2025 season's events that start in late December 2024
    rows["holdout"] = (rows["day"] >= D_HOLD) | (rows["year"] >= 2025)
    # the closed holdout: nothing about these rows but their day and identity is kept
    for c in ("status", "status_detail", "won", "spw_n", "spw_d", "has_box", "minutes", "age"):
        rows[c] = rows[c].astype(object).where(~rows["holdout"], None)
    rows["side_n"] = rows["side"].map({"A": 1, "B": 2}).astype(int)
    return rows


def logged_keys() -> tuple[pd.DataFrame, dict]:
    """match_id -> primary WTA log key, for logs that count as logged (prereg section 1)."""
    sm = pd.read_parquet(OUT / "seq_matches.parquet",
                         columns=["source", "key", "match_id", "primary_in_source", "log", "score_check", "n_points"])
    w = sm[sm["source"].eq("wta") & sm["match_id"].notna() & sm["primary_in_source"].fillna(False)
           & sm["log"].eq("full")].copy()
    mp = pd.read_parquet(S0.MATCH_PLAYERS, columns=["match_id", "svpt", "has_box"])
    box = mp.groupby("match_id").agg(box_svpt=("svpt", "sum"), box_all=("has_box", "all")).reset_index()
    w = w.merge(box, on="match_id", how="left")
    mislink = w["score_check"].isin(["winner_differs", "sets_differ"])
    short = w["box_all"].astype("boolean").fillna(False).astype(bool) & (w["box_svpt"] > 0) \
        & (w["n_points"] < 0.9 * w["box_svpt"])
    audit = {"linked_primary_full_logs": int(len(w)), "excluded_mislink": int(mislink.sum()),
             "excluded_short": int((short & ~mislink).sum())}
    w = w[~mislink & ~short]
    if w["match_id"].duplicated().any():
        raise RuntimeError("two primary WTA logs for one Stage 0 match")
    return w[["match_id", "key"]], audit


def log_minutes(keys: set[str]) -> pd.DataFrame:
    """Playing time of each log (gaps between consecutive points capped at 5 min) and its point count."""
    p = pd.read_parquet(OUT / "points_wta.parquet", columns=["key", "seq", "t_utc"])
    p = p[p["key"].isin(keys)].sort_values(["key", "seq"], kind="mergesort")
    gap = p.groupby("key")["t_utc"].diff()
    p["gapc"] = gap.clip(lower=0, upper=CAP_S)
    g = p.groupby("key").agg(n_pts=("seq", "size"), nt=("t_utc", "nunique"), cap_s=("gapc", "sum"))
    g["log_min"] = g["cap_s"] / 60.0
    g["time_ok"] = (g["nt"] / g["n_pts"] >= 0.5) & (g["log_min"] >= 10)
    return g.reset_index()[["key", "n_pts", "log_min", "time_ok"]]


def seq_serve_counts(match_ids: set[str]) -> pd.DataFrame:
    """Serve points played and won per (match_id, side 1/2) from usable sequences."""
    d = ds.dataset(OUT / "sequences.parquet")
    tab = d.to_table(columns=["match_id", "usable", "server", "winner"],
                     filter=ds.field("usable") & ds.field("match_id").isin(sorted(match_ids)))
    s = tab.to_pandas()
    s["match_id"] = s["match_id"].astype(str)
    s = s[s["winner"].isin([1, 2]) & s["server"].isin([1, 2])]
    s["won"] = (s["winner"] == s["server"]).astype(int)
    g = s.groupby(["match_id", "server"]).agg(seq_svpt=("won", "size"), seq_spw=("won", "sum")).reset_index()
    g = g.rename(columns={"server": "side_n"})
    g["side_n"] = g["side_n"].astype(int)
    return g


# ------------------------------------------------------------------------------------------------
# Fade markers (secondary family)

def fade_markers(day_of: pd.Series) -> tuple[pd.DataFrame, dict]:
    """Per (match_id, side) excess fade slopes from the WTA-log sequences (prereg section 8)."""
    d = ds.dataset(OUT / "sequences.parquet")
    cols = ["match_id", "seq", "game_idx", "pt_no", "is_tb", "server", "winner", "serve_no", "end", "ender", "t_utc"]
    s = d.to_table(columns=cols, filter=(ds.field("source") == "wta") & ds.field("usable")).to_pandas()
    s["match_id"] = s["match_id"].astype(str)
    s = s.sort_values(["match_id", "seq"], kind="mergesort").reset_index(drop=True)
    s["day"] = s["match_id"].map(day_of)
    s = s[s["day"].notna() & (s["day"] < D_HOLD)].reset_index(drop=True)
    # score state before each point, within its game
    known = s["winner"].isin([1, 2])
    srv_won = ((s["winner"] == s["server"]) & known).astype(int)
    rcv_won = ((s["winner"] != s["server"]) & known).astype(int)
    gk = [s["match_id"], s["game_idx"]]
    sb = srv_won.groupby(gk).cumsum() - srv_won
    rb = rcv_won.groupby(gk).cumsum() - rcv_won
    st = np.where(np.minimum(sb, rb) >= 3, np.where(sb == rb, "D", np.where(sb > rb, "AS", "AR")),
                  sb.clip(upper=3).astype(str) + "-" + rb.clip(upper=3).astype(str))
    s["state"] = np.where(s["is_tb"] == 1, "TB", st)
    s["deuce_court"] = ((s["pt_no"] - 1) % 2 == 0).astype(int)
    s["x"] = s["seq"] / 100.0
    s["fsi"] = (s["serve_no"] == 1).astype(float)
    s["dfault"] = ((s["end"] == C.END["df"]) & (s["ender"] == s["server"])).astype(float)
    prev_t = s.groupby("match_id")["t_utc"].shift(1)
    prev_g = s.groupby("match_id")["game_idx"].shift(1)
    gap = s["t_utc"] - prev_t
    s["tempo"] = np.where((prev_g == s["game_idx"]) & gap.between(5, 120), gap, np.nan)
    s["endk"] = np.where(s["end"] == C.END["ace"], "ace", np.where(s["end"] == C.END["df"], "df", "other"))
    disc = ((s["day"] >= D_START) & (s["day"] < D_REP)).to_numpy()
    states = sorted(s["state"].unique())
    audit = {"points": int(len(s)), "discovery_points": int(disc.sum()), "states": states}

    def resid(ycol: str, extra: bool) -> np.ndarray:
        y = s[ycol].to_numpy(float)
        ok = ~np.isnan(y)
        Xc = [np.ones(len(s)), s["deuce_court"].to_numpy(float)]
        stv = s["state"].to_numpy(object)
        for lev in states[1:]:
            Xc.append((stv == lev).astype(float))
        if extra:
            Xc.append((s["serve_no"] == 2).to_numpy(float))
            Xc.append((s["endk"] == "ace").to_numpy(float))
            Xc.append((s["endk"] == "df").to_numpy(float))
        X = np.column_stack(Xc)
        fit = ok & disc
        beta, *_ = np.linalg.lstsq(X[fit], y[fit], rcond=None)
        r = y - X @ beta
        r[~ok] = np.nan
        return r

    res = {"fsi": resid("fsi", False), "dfault": resid("dfault", False), "tempo": resid("tempo", True)}
    npts = s.groupby("match_id")["seq"].transform("size")
    base = pd.DataFrame({"match_id": s["match_id"], "side_n": s["server"].astype(int), "x": s["x"],
                         "n_match": npts, "day": s["day"]})
    out = []
    for name, r in res.items():
        b = base.assign(r=r).dropna(subset=["r"])
        b = b[b["side_n"].isin([1, 2])]
        g = b.groupby(["match_id", "side_n"])
        mx, mr = g["x"].transform("mean"), g["r"].transform("mean")
        b = b.assign(sxy=(b["x"] - mx) * (b["r"] - mr), sxx=(b["x"] - mx) ** 2)
        a = b.groupby(["match_id", "side_n"]).agg(sxy=("sxy", "sum"), sxx=("sxx", "sum"), n=("r", "size"),
                                                  n_match=("n_match", "first"), day=("day", "first")).reset_index()
        need = 20 if name == "tempo" else 30
        a = a[(a["n"] >= need) & (a["sxx"] > 0)].copy()
        a["slope"] = a["sxy"] / a["sxx"]
        out.append(a.assign(marker=name)[["match_id", "side_n", "marker", "slope", "n", "n_match", "day"]])
    mk = pd.concat(out, ignore_index=True)
    # excess over the discovery mean slope in its match-length decile, oriented (positive = fading), standardised
    dmask = ((mk["day"] >= D_START) & (mk["day"] < D_REP)).to_numpy()
    cuts = np.quantile(mk.loc[dmask & mk["marker"].eq("fsi").to_numpy(), "n_match"], np.linspace(0, 1, 11)[1:-1])
    mk["len_dec"] = np.searchsorted(cuts, mk["n_match"].to_numpy(), side="right")
    norm = mk[dmask].groupby(["marker", "len_dec"])["slope"].mean().rename("norm").reset_index()
    mk = mk.merge(norm, on=["marker", "len_dec"], how="left")
    dmask = ((mk["day"] >= D_START) & (mk["day"] < D_REP)).to_numpy()
    sign = mk["marker"].map({"fsi": -1.0, "dfault": 1.0, "tempo": 1.0})
    mk["fade"] = sign * (mk["slope"] - mk["norm"])
    sd = mk[dmask].groupby("marker")["fade"].std()
    mk["fade_z"] = mk["fade"] / mk["marker"].map(sd)
    audit.update({"length_decile_cuts": cuts.tolist(), "discovery_sd_fade": sd.to_dict(),
                  "discovery_mean_slope": mk[dmask].groupby("marker")["slope"].mean().to_dict(),
                  "player_matches": mk.groupby("marker").size().to_dict(),
                  "tempo_gap_points": int(s["tempo"].notna().sum()),
                  "tempo_median_s": float(np.nanmedian(s["tempo"]))})
    wide = mk.pivot_table(index=["match_id", "side_n"], columns="marker", values=["fade_z", "fade", "slope"])
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    return wide.reset_index(), audit


# ------------------------------------------------------------------------------------------------
# Pairs

def level_group(level) -> str:
    if level in ("T1000", "FIN"):
        return "T1000F"
    if level in ("T500", "T250", "CH"):
        return str(level)
    return "other"


def assemble() -> tuple[pd.DataFrame, dict]:
    """All WTA player-match rows with exposures, minutes, p_serve and M2 parts, ordered, with next / previous
    positions."""
    summary: dict = {"registered": "data/studies/point_sequence/med_prereg.md"}
    rows = load_rows()
    n0 = len(rows)
    log(f"player-match rows: {n0:,} (holdout-masked {int(rows['holdout'].sum()):,})")
    lk, laudit = logged_keys()
    summary["logged_keys"] = laudit
    rows = rows.merge(lk, on="match_id", how="left", validate="many_to_one")
    rows["logged"] = rows["key"].notna()
    ev = pd.read_parquet(OUT / "wta_events.parquet", columns=["key", "index", "name", "reason", "player_side_ab"])
    ev = ev[ev["key"].isin(set(lk["key"]))]
    ex, eaudit = exposures(ev)
    summary["injury_attribution"] = eaudit
    rows = rows.merge(ex, on=["key", "side_n"], how="left", validate="many_to_one")
    for c in ("call", "cancel", "treat", "eval"):
        rows[c] = rows[c].fillna(0).astype(int)
    for c in ("treated", "injury", "toilet"):
        rows[c] = rows[c].astype("boolean").fillna(False).astype(bool) & rows["logged"]
    opp = rows[["match_id", "side_n", "treated"]].copy()
    opp["side_n"] = 3 - opp["side_n"]
    rows = rows.merge(opp.rename(columns={"treated": "opp_treated"}), on=["match_id", "side_n"], how="left",
                      validate="one_to_one")
    rows["opp_treated"] = rows["opp_treated"].astype("boolean").fillna(False).astype(bool) & rows["logged"]
    rows = rows.merge(log_minutes(set(lk["key"])), on="key", how="left", validate="many_to_one")
    rp = pd.read_parquet(RATINGS, columns=["match_id", "p_serve_a", "p_serve_b"])
    rows = rows.merge(rp, on="match_id", how="left", validate="many_to_one")
    rows["p_serve"] = np.where(rows["side_n"] == 1, rows["p_serve_a"], rows["p_serve_b"])
    rows["opp_p_serve"] = np.where(rows["side_n"] == 1, rows["p_serve_b"], rows["p_serve_a"])
    sc = seq_serve_counts(set(rows["match_id"]))
    rows = rows.merge(sc, on=["match_id", "side_n"], how="left", validate="many_to_one")
    box_ok = rows["has_box"].astype("boolean").fillna(False).astype(bool) & (pd.to_numeric(rows["spw_d"]) > 0)
    rows["svpt"] = np.where(box_ok, pd.to_numeric(rows["spw_d"]), rows["seq_svpt"]).astype(float)
    rows["spw"] = np.where(box_ok, pd.to_numeric(rows["spw_n"]), rows["seq_spw"]).astype(float)
    rows["m2_src"] = np.where(box_ok, "box", np.where(rows["seq_svpt"].notna(), "sequence", "none"))
    rows.loc[rows["holdout"], ["svpt", "spw"]] = np.nan
    rows.loc[rows["holdout"], "m2_src"] = "holdout"
    rows["m2"] = np.where(rows["svpt"] > 0, 100.0 * (rows["spw"] / rows["svpt"] - rows["p_serve"]), np.nan)
    if len(rows) != n0:
        raise RuntimeError("a merge changed the number of player-match rows")
    rows = rows.sort_values(["player_id", "order"], kind="mergesort").reset_index(drop=True)
    if rows[["player_id", "order"]].duplicated().any():
        raise RuntimeError("two rows of one player share an order value")
    # next informative match (skip byes and walkovers she received; holdout rows stay, so they end a pair) and the
    # previous match she played
    status = rows["status"].to_numpy(object)
    won = rows["won"].to_numpy(object)
    hold = rows["holdout"].to_numpy(bool)
    played = np.isin(status, ["completed", "retired", "other"]) & ~hold
    received_wo = (status == "walkover") & (won == True)  # noqa: E712
    bye = rows["status_detail"].to_numpy(object) == "bye"
    informative = hold | ~(received_wo | bye)
    pos = np.arange(len(rows), dtype=float)
    r = pd.DataFrame({"pid": rows["player_id"].to_numpy(object), "inf": np.where(informative, pos, np.nan),
                      "ply": np.where(played, pos, np.nan)})
    nxt = r.groupby("pid")["inf"].shift(-1)
    rows["next_pos"] = nxt.groupby(r["pid"]).bfill().to_numpy()
    prv = r.groupby("pid")["ply"].shift(1)
    rows["prev_pos"] = prv.groupby(r["pid"]).ffill().to_numpy()
    rows["played"] = played
    return rows, summary


def pairs(rows: pd.DataFrame, summary: dict) -> pd.DataFrame:
    day = rows["day"].to_numpy(float)
    t = rows[rows["played"].to_numpy() & (day >= D_START) & (day < D_HOLD)].copy()
    t["window"] = np.where(t["day"] < D_REP, "discovery", "replication")
    t["season"] = (pd.Timestamp("1970-01-01") + pd.to_timedelta(t["day"], unit="D")).dt.year

    def take(posname: str, prefix: str, cols: list[str]) -> pd.DataFrame:
        p = t[posname].to_numpy()
        ok = ~np.isnan(p)
        out = pd.DataFrame(index=t.index)
        for c in cols:
            v = np.full(len(t), None, dtype=object)
            v[ok] = rows[c].to_numpy(object)[p[ok].astype(int)]
            out[f"{prefix}{c}"] = v
        return out

    ncols = ["match_id", "player_id", "side_n", "day", "exact", "holdout", "status", "won", "level", "qualifying",
             "surface", "tournament_id", "age", "svpt", "spw", "p_serve", "m2", "m2_src"]
    t = pd.concat([t, take("next_pos", "n_", ncols), take("prev_pos", "p_", ncols)], axis=1)
    for pfx in ("n_", "p_"):
        same = t[f"{pfx}player_id"].isna() | (t[f"{pfx}player_id"] == t["player_id"])
        if not same.all():
            raise RuntimeError(f"{pfx} position points at another player")
    t["gap_raw"] = pd.to_numeric(t["n_day"]) - t["day"]
    t["prev_gap_raw"] = t["day"] - pd.to_numeric(t["p_day"])
    summary["negative_gaps"] = {"next": int((t["gap_raw"] < 0).sum()), "previous": int((t["prev_gap_raw"] < 0).sum())}
    t["gap"] = t["gap_raw"].clip(lower=0)
    t["prev_gap"] = t["prev_gap_raw"].clip(lower=0)
    t["has_next"] = t["n_match_id"].notna()
    t["next_holdout"] = t["n_holdout"].astype("boolean").fillna(False).astype(bool)
    t["next_le21"] = t["has_next"] & (t["gap"] <= MAX_GAP)
    t["t_won"] = t["won"].astype(bool)
    t["own_ret"] = t["status"].eq("retired") & ~t["t_won"]
    t["m1"] = (t["n_status"].isin(["retired", "walkover"]) & (t["n_won"] == False)).astype(float)  # noqa: E712
    t.loc[~t["next_le21"] | t["next_holdout"], "m1"] = np.nan
    t["n_completed"] = t["n_status"].eq("completed")
    t["same_event"] = t["n_tournament_id"].astype(object) == t["tournament_id"].astype(object)
    t["level_group"] = [level_group(lv) for lv in t["level"]]
    t["surface_t"] = t["surface"].where(t["surface"].isin(["Hard", "Clay", "Grass"]), "other")
    t["surface_n"] = t["n_surface"].where(t["n_surface"].isin(["Hard", "Clay", "Grass"]), "other")
    # minutes of t: the log's capped playing time; broken log clocks fall back to Stage 0, then to points x rate
    tok = t["time_ok"].astype("boolean").fillna(False).astype(bool)
    st0 = pd.to_numeric(t["minutes"])
    t["minutes_src"] = np.where(tok, "log", np.where(st0.notna(), "stage0", "points"))
    dmask = t["window"].eq("discovery") & t["logged"] & tok
    rate = float((t.loc[dmask, "log_min"] / t.loc[dmask, "n_pts"]).median())
    t["minutes_t"] = np.where(t["minutes_src"].eq("log"), t["log_min"],
                              np.where(t["minutes_src"].eq("stage0"), st0, t["n_pts"] * rate))
    age_n = pd.to_numeric(t["n_age"])
    age_t = pd.to_numeric(t["age"])
    t["age_x"] = age_n.where(age_n.notna(), age_t + t["gap"] / 365.25)
    t["age_missing"] = t["age_x"].isna().astype(float)
    t["fresh_stale"] = np.where(t["t_won"] & t["same_event"], "fresh",
                                np.where(~t["t_won"] & ~t["same_event"], "stale", "other"))
    summary["minutes"] = {"discovery_median_min_per_point": rate}
    return t


def main() -> None:
    rows, summary = assemble()
    t = pairs(rows, summary)
    log(f"played t in window: {len(t):,}")
    day_of = rows.drop_duplicates("match_id").set_index("match_id")["day"]
    mk, maudit = fade_markers(day_of)
    t = t.merge(mk, on=["match_id", "side_n"], how="left", validate="many_to_one")
    sm = pd.read_parquet(OUT / "seq_matches.parquet", columns=["match_id", "source", "chosen", "usable"])
    wseq = set(sm.loc[sm["chosen"] & sm["usable"] & sm["source"].eq("wta"), "match_id"])
    t["t_wta_seq"] = t["match_id"].isin(wseq)
    summary["fade_markers"] = maudit
    summary["minutes"]["minutes_src_logged_pairs"] = t[t["logged"]]["minutes_src"].value_counts().to_dict()

    keep = ["player_id", "match_id", "side_n", "key", "day", "window", "season", "status", "t_won", "own_ret",
            "level", "qualifying", "level_group", "surface_t", "logged", "call", "cancel", "treat", "eval", "treated",
            "injury", "toilet", "opp_treated", "n_pts", "log_min", "time_ok", "minutes_t", "minutes_src", "age",
            "p_serve", "opp_p_serve", "has_next", "next_holdout", "next_le21", "gap", "gap_raw", "n_exact",
            "n_match_id", "n_status",
            "n_won", "n_level", "n_qualifying", "surface_n", "n_completed", "same_event", "m1", "n_svpt", "n_spw",
            "n_p_serve", "n_m2", "n_m2_src", "age_x", "age_missing", "fresh_stale", "p_match_id", "prev_gap",
            "p_svpt", "p_p_serve", "p_m2", "p_m2_src", "t_wta_seq",
            "fade_z_fsi", "fade_z_dfault", "fade_z_tempo", "fade_fsi", "fade_dfault", "fade_tempo",
            "slope_fsi", "slope_dfault", "slope_tempo"]
    for c in keep:
        if c not in t.columns:
            t[c] = np.nan
    out = t[keep].copy()
    for c in ("n_svpt", "n_spw", "n_p_serve", "n_m2", "p_svpt", "p_p_serve", "p_m2", "gap", "prev_gap", "age",
              "season", "n_pts", "log_min", "minutes_t", "age_x"):
        out[c] = pd.to_numeric(out[c], errors="coerce").astype(float)
    out["gap_raw"] = pd.to_numeric(out["gap_raw"], errors="coerce").astype(float)
    for c in ("n_won", "n_qualifying", "time_ok", "qualifying", "n_exact"):
        out[c] = out[c].astype("boolean")
    for c in ("n_status", "n_level", "n_m2_src", "p_m2_src", "n_match_id", "p_match_id", "key", "status", "level",
              "surface_n", "surface_t"):
        out[c] = out[c].astype("string")
    out.to_parquet(OUT / "med_pairs.parquet", index=False)
    log(f"wrote med_pairs.parquet ({len(out):,} rows)")

    # counts (no outcome contrast)
    c = {}
    for wname, g in out.groupby("window"):
        g21 = g[g["next_le21"] & ~g["next_holdout"]]
        prim = g21[g21["logged"] & ~g21["own_ret"]]
        c[wname] = {
            "played_t": int(len(g)), "logged_t": int(g["logged"].sum()),
            "t_with_next_le21": int(g["next_le21"].sum()), "dropped_next_in_holdout": int(g["next_holdout"].sum()),
            "pairs_le21": int(len(g21)), "pairs_le21_logged": int(g21["logged"].sum()),
            "pairs_own_ret_excluded": int((g21["logged"] & g21["own_ret"]).sum()),
            "primary_pairs": int(len(prim)), "treated": int(prim["treated"].sum()),
            "injury": int(prim["injury"].sum()), "toilet": int(prim["toilet"].sum()),
            "toilet_among_untreated": int((prim["toilet"] & ~prim["treated"]).sum()),
            "opp_treated_among_untreated": int((prim["opp_treated"] & ~prim["treated"]).sum()),
            "m2_available": int(prim["n_m2"].notna().sum()),
            "m2_src": prim["n_m2_src"].value_counts().to_dict(),
            "players": int(prim["player_id"].nunique()),
            "triples_base": int((prim["t_wta_seq"] & prim["n_m2"].notna() & prim["p_m2"].notna()
                                 & (prim["prev_gap"] <= MAX_GAP)).sum()),
        }
    by_year = []
    for y, g in out[out["next_le21"] & ~out["next_holdout"]].groupby("season"):
        tourish = g["level"].isin(["T1000", "T500", "T250", "FIN", "CH"])
        prim = g[g["logged"] & ~g["own_ret"]]
        by_year.append({"season": int(y), "pairs": int(len(g)), "logged_share_all": round(float(g["logged"].mean()), 4),
                        "pairs_tour_125_q": int(tourish.sum()),
                        "logged_share_tour_125_q": round(float(g.loc[tourish, "logged"].mean()), 4),
                        "primary_pairs": int(len(prim)), "treated": int(prim["treated"].sum()),
                        "treated_share": round(float(prim["treated"].mean()), 4), "injury": int(prim["injury"].sum()),
                        "toilet_share": round(float(prim["toilet"].mean()), 4)})
    summary["counts"] = c
    summary["by_season"] = by_year
    summary["inputs"] = [C.file_sig(p) for p in (S0.MATCHES, S0.MATCH_PLAYERS, TIMING, RATINGS,
                                                 OUT / "seq_matches.parquet", OUT / "sequences.parquet",
                                                 OUT / "points_wta.parquet", OUT / "wta_events.parquet")]
    C.write_json(OUT / "med_build_summary.json", summary)
    log("wrote med_build_summary.json")
    print(json.dumps({"counts": c, "by_season": by_year, "logged_keys": summary["logged_keys"],
                      "injury": summary["injury_attribution"], "minutes": summary["minutes"],
                      "fade": {k: v for k, v in maudit.items() if k != "states"}}, indent=1, default=str))


if __name__ == "__main__":
    main()
