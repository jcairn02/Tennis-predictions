"""Bet timing, step 1: the sample. Every model-frame match of 2018-2026 with the prices a bettor could have fed the
current best model before the close, the moment each price was available, and whether every model input existed by then.
Seasons 2020-2026 are scored; 2018-2019 add training rows for the arms trained on BetOnline's lines (fits_lines.py).

    BetOnline   the opening line and the last line OddsTrader recorded (src/ingest/oddstrader.py), linked to the frame's
                tennis-data rows exactly as the BetOnline-lines study and the Thinking-58 study link them (the sharp
                benchmark's linker; Stage 1's tennis-data keys). A pair outside overround 1.00-1.20, a broken opening pair
                or a close the adapter flags uncertain (stamped over 30 minutes after the listed start, or not two-sided)
                gives no price; so does an opening stamped after the listed start. Decimal odds for A and B, P(A) with
                the margin removed proportionally (as the model's own odds input), the UTC stamps and the hours before
                OddsTrader's listed start
    Polymarket  P(A) at 48, 24, 12, 6, 3 and 1 hours and 30 minutes before the listed start (the sharp benchmark's
                pw_pm_m<minutes>: the last price before the cut-off, if no older than an hour), 2025-2026, with the taker
                fee rate in force at each moment (src/eda/line_sharpening/timing_frame.fee_rate)
    known_<b>   every input of the forecast existed when price b was quoted. A player's previous match at an earlier
                round of the same event is over once the matchup is listed; a previous match at another event must have
                surely finished: its latest possible finish day (match-timing study) ends before the quote (a local day
                ends at most 1.33 days after its UTC midnight)
    opener      both players are in their first match of the event
    spd_L       the speed adjustment's column (28-day memory, weekly feed: adaptive/columns.parquet spd_L_B)

A is oriented by Stage 1 (tennis-data's winner unless the row was linked with winner and loser exchanged) and checked
against the market average's odds, which must agree with Stage 1's for A on every priced row. Nothing else here reads
a result. Snapshot: Stage 0, Stage 1 and the timeline as they stood before the 7 Oct 2026 rebuild (the model frame's).

Writes data/studies/bet_timing/frame.parquet (gitignored: OddsTrader's lines are not republished) and frame_counts.json.
Run: ./python.sh src/eda/bet_timing/frame.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.bet_timing import common as C  # noqa: E402
from src.eda.betonline_lines import sharpness as SH  # noqa: E402
from src.eda.line_sharpening.timing_frame import LATE_RATE, fee_rate  # noqa: E402
from src.eda.sharp_benchmark import build as BLD  # noqa: E402
from src.eda.surface_elo_pieces.early_price_frame import previous_match_lf  # noqa: E402

KEY = ["tour", "td_date", "td_winner", "td_loser"]
MAX_UNJOINED_SHARE = 0.01


def model_rows() -> pd.DataFrame:
    """The frame's matches of the scored seasons with Stage 1's tennis-data keys and A's orientation."""
    cols = ["match_id", "tour", "season", "tournament_date", "debut_season", "p_mkt", "a_won", "in_level", "in_round",
            "in_best_of"]
    f = pd.read_parquet(C.MODEL_FRAME, columns=cols)
    f = f[f["season"].isin(C.FRAME_SEASONS)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    s1 = pd.read_parquet(C.STAGE1, columns=["match_id", "status", "link", "td_date", "td_winner", "td_loser", "avg_a"])
    s1["match_id"] = s1["match_id"].astype(str)
    f = f.merge(s1, on="match_id", how="left", validate="one_to_one")
    if f["td_winner"].isna().any():
        raise RuntimeError("a frame match has no tennis-data row in Stage 1")
    f["a_is_w"] = f["a_won"].astype(bool).to_numpy() ^ f["link"].eq("winner_swapped").to_numpy()
    f["td_date"] = pd.to_datetime(f["td_date"]).dt.normalize()
    f["td_winner"], f["td_loser"] = f["td_winner"].astype(str), f["td_loser"].astype(str)
    if f.duplicated(KEY).any():
        raise RuntimeError("frame matches are not unique by tour, day, winner and loser")
    return f


def utc_seconds(iso: pd.Series) -> np.ndarray:
    """Seconds since the epoch of ISO stamps; NaN where there is none."""
    t = pd.to_datetime(iso, utc=True, errors="coerce")
    return (t - pd.Timestamp("1970-01-01", tz="UTC")).dt.total_seconds().to_numpy(dtype=float)


def betonline(rows: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    td = SH.load_tennis_data(tuple(sorted(rows["season"].unique())))
    bo, frame = SH.betonline_markets()
    m = SH.attach_betonline(td, bo, BLD.link(td, frame))
    m = m.merge(bo[["eid", "dt_ms", "mw_open_utc", "mw_close_utc"]], on="eid", how="left", validate="many_to_one")
    keep = ["tour", "date", "winner", "loser", "AvgW", "AvgL", "eid", "BOLOW", "BOLOL", "BOLCW", "BOLCL", "ok_bolo",
            "ok_bol", "dt_ms", "mw_open_utc", "mw_close_utc", "mw_close_after_listed_min"]
    m = m[keep].rename(columns={"date": "td_date", "winner": "td_winner", "loser": "td_loser"})
    m["td_date"] = pd.to_datetime(m["td_date"]).dt.normalize()
    m["td_winner"], m["td_loser"] = m["td_winner"].astype(str), m["td_loser"].astype(str)
    if m.duplicated(KEY).any():
        raise RuntimeError("tennis-data rows are not unique by tour, day, winner and loser")
    o = rows[["match_id", "season", "avg_a", "a_is_w"] + KEY].merge(m, on=KEY, how="left", validate="one_to_one")
    unjoined = o["AvgW"].isna() & o["avg_a"].notna()
    a = o["a_is_w"].to_numpy(bool)
    avg_w = np.where(a, o["AvgW"], o["AvgL"])
    k = np.isfinite(avg_w) & o["avg_a"].notna().to_numpy()
    if not np.allclose(o["avg_a"].to_numpy(float)[k], avg_w[k]):
        raise RuntimeError("A's market-average odds disagree between the two loaders: orientation is wrong")
    out = pd.DataFrame({"match_id": o["match_id"]})
    for kind, (w, l), ok in (("open", ("BOLOW", "BOLOL"), "ok_bolo"), ("close", ("BOLCW", "BOLCL"), "ok_bol")):
        da = np.where(a, o[w], o[l]).astype(float)
        db = np.where(a, o[l], o[w]).astype(float)
        good = o[ok].fillna(False).astype(bool).to_numpy() & np.isfinite(da) & np.isfinite(db)
        out[f"bol_{kind}_a"], out[f"bol_{kind}_b"] = np.where(good, da, np.nan), np.where(good, db, np.nan)
        out[f"ok_bol_{kind}"] = good
    out["t_listed"] = o["dt_ms"].to_numpy(float) / 1000.0
    out["t_bol_open"] = utc_seconds(o["mw_open_utc"])
    out["t_bol_close"] = utc_seconds(o["mw_close_utc"])
    out["h_bol_open"] = (out["t_listed"] - out["t_bol_open"]) / 3600.0
    out["h_bol_close"] = (out["t_listed"] - out["t_bol_close"]) / 3600.0
    late_open = out["ok_bol_open"] & ~(out["h_bol_open"] > 0)
    out.loc[late_open, "ok_bol_open"] = False
    for kind in ("open", "close"):
        ok = out[f"ok_bol_{kind}"].to_numpy()
        out[f"p_bol_{kind}"] = np.where(ok, C.devig(out[f"bol_{kind}_a"], out[f"bol_{kind}_b"]), np.nan)
    counts = {"orientation_checked_rows": int(k.sum()), "unjoined_tennis_data_rows": int(unjoined.sum()),
              "linked_to_betonline": int(o["eid"].notna().sum()),
              "openings_after_listed_start_dropped": int(late_open.sum())}
    if unjoined.mean() > MAX_UNJOINED_SHARE:
        raise RuntimeError(f"{int(unjoined.sum())} frame matches did not join their tennis-data row")
    return out, counts


def polymarket(rows: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    pw = [f"pw_pm_m{m}" for m in C.PM_HORIZONS.values()]
    sb = pd.read_parquet(C.SHARP, columns=["tour", "date", "winner", "loser", "condition_id", "pm_start_ts"] + pw)
    sb["td_date"] = pd.to_datetime(sb["date"]).dt.normalize()
    sb = sb.drop(columns="date").rename(columns={"winner": "td_winner", "loser": "td_loser"})
    sb["td_winner"], sb["td_loser"] = sb["td_winner"].astype(str), sb["td_loser"].astype(str)
    dup = sb.duplicated(KEY, keep=False)
    sb = sb[~dup]
    o = rows[["match_id", "a_is_w"] + KEY].merge(sb, on=KEY, how="left", validate="one_to_one")
    start = pd.to_numeric(o["pm_start_ts"], errors="coerce").to_numpy(float)
    if np.nanmedian(start) > 1e11:                                     # milliseconds, not seconds
        start = start / 1000.0
    a = o["a_is_w"].to_numpy(bool)
    out = pd.DataFrame({"match_id": o["match_id"], "condition_id": o["condition_id"], "pm_start": start})
    fees = pd.read_parquet(C.SHARP_MARKETS, columns=["condition_id", "fees_enabled", "fee_rate"])
    fees = fees.drop_duplicates("condition_id")
    f = out[["condition_id"]].merge(fees, on="condition_id", how="left")
    rate = np.where(f["fee_rate"].notna(), f["fee_rate"].fillna(0.0) * f["fees_enabled"].fillna(False).astype(float),
                    LATE_RATE)
    for name, minutes in C.PM_HORIZONS.items():
        p = o[f"pw_pm_m{minutes}"].to_numpy(float)
        out[f"p_{name}"] = np.where(a, p, 1.0 - p)
        out[f"t_{name}"] = start - 60.0 * minutes
        out[f"fee_{name}"] = np.where(np.isfinite(out[f"p_{name}"]), fee_rate(out[f"t_{name}"].to_numpy(), rate), np.nan)
    counts = {"linked_to_polymarket": int(out["condition_id"].notna().sum()), "duplicate_sharp_keys_dropped": int(dup.sum()),
              "priced": {name: int(np.isfinite(out[f"p_{name}"]).sum()) for name in C.PM_HORIZONS}}
    return out, counts


def previous(rows: pd.DataFrame) -> pd.DataFrame:
    m = pd.read_parquet(C.STAGE0, columns=["match_id", "tour", "tournament_id", "tournament_date", "round_order",
                                           "order", "status", "player_a_id", "player_b_id"])
    m["match_id"] = m["match_id"].astype(str)
    tm = pd.read_parquet(C.TIMING, columns=["match_id", "lf"])
    tm["match_id"] = tm["match_id"].astype(str)
    lf = tm.set_index("match_id")["lf"].reindex(m["match_id"]).to_numpy(float)
    prev_lf, same_event, _ = previous_match_lf(m, lf)
    idx = pd.Series(np.arange(len(m)), index=m["match_id"]).reindex(rows["match_id"]).to_numpy()
    if np.isnan(idx.astype(float)).any():
        raise RuntimeError("a frame match is missing from Stage 0's snapshot")
    idx = idx.astype(int)
    return pd.DataFrame({"match_id": rows["match_id"].to_numpy(), "prev_lf_a": prev_lf[idx, 0],
                         "prev_lf_b": prev_lf[idx, 1], "same_event_a": same_event[idx, 0],
                         "same_event_b": same_event[idx, 1], "opener": ~same_event[idx].any(axis=1)})


def known(prev: pd.DataFrame, t_seconds) -> np.ndarray:
    """Every input existed at time t: each player's previous match is an earlier round of this event, or none, or it
    surely finished before t (its latest possible finish day had ended in every time zone)."""
    t_days = np.asarray(t_seconds, dtype=float) / 86400.0
    ok = np.isfinite(t_days)
    for side in ("a", "b"):
        lf = prev[f"prev_lf_{side}"].to_numpy(float)
        ok &= prev[f"same_event_{side}"].to_numpy(bool) | (lf + C.LOCAL_DAY_END <= t_days)
    return ok


def main() -> int:
    rows = model_rows()
    bol, bol_counts = betonline(rows)
    pm, pm_counts = polymarket(rows)
    prev = previous(rows)
    sp = pd.read_parquet(C.SPEED_COLUMNS, columns=["match_id", "spd_L_B"]).rename(columns={"spd_L_B": "spd_L"})
    sp["match_id"] = sp["match_id"].astype(str)
    x = rows[["match_id", "tour", "season", "tournament_date", "debut_season", "status", "p_mkt", "in_level", "in_round",
              "in_best_of"]].rename(columns={"p_mkt": "p_td", "in_level": "level", "in_round": "round_order",
                                             "in_best_of": "best_of"})
    for part in (bol, pm, prev):
        x = x.merge(part, on="match_id", how="left", validate="one_to_one")
    x = x.merge(sp, on="match_id", how="left", validate="one_to_one")
    if x["spd_L"].isna().any():
        raise RuntimeError("the speed column is missing for some frame matches")
    x["known_bol_open"] = known(prev, x["t_bol_open"]) & x["ok_bol_open"]
    x["known_bol_close"] = known(prev, x["t_bol_close"]) & x["ok_bol_close"]
    for name in C.PM_HORIZONS:
        x[f"known_{name}"] = known(prev, x[f"t_{name}"]) & np.isfinite(x[f"p_{name}"])
    x["block"] = C.blocks(x["tournament_date"].to_numpy())
    x["week"] = C.blocks(x["tournament_date"].to_numpy(), 7)
    C.OUT.mkdir(parents=True, exist_ok=True)
    x.to_parquet(C.FRAME, index=False)

    # the 24-hour and 30-minute prices against the early-price frame of the Elo-pieces study (same source, same link)
    ep = pd.read_parquet(ROOT / "data" / "studies" / "surface_elo_pieces" / "early_price_frame.parquet",
                         columns=["match_id", "p_early_a", "p_close_a"])
    ep["match_id"] = ep["match_id"].astype(str)
    chk = x[["match_id", "p_pm_h24", "p_pm_m30"]].merge(ep, on="match_id")
    swapped = rows.set_index("match_id").reindex(chk["match_id"])["link"].eq("winner_swapped").to_numpy()
    agree = {}
    for mine, theirs in (("p_pm_h24", "p_early_a"), ("p_pm_m30", "p_close_a")):
        both = np.isfinite(chk[mine]) & np.isfinite(chk[theirs])
        same = np.isclose(chk[mine], chk[theirs], atol=1e-12) & both
        agree[mine] = {"both_priced": int(both.sum()), "equal": int(same.sum()),
                       "differ_on_swapped_rows": int((both & ~same & swapped).sum()),
                       "differ_otherwise": int((both & ~same & ~swapped).sum())}
    counts = {"frame_matches": int(len(x)), "by_season": x.groupby("season").size().to_dict(),
              "betonline": bol_counts, "polymarket": pm_counts, "check_against_early_price_frame": agree,
              "priced": {b: int(x[f"ok_{b}"].sum()) if f"ok_{b}" in x else int(np.isfinite(x[f"p_{b}"]).sum())
                         for b in C.PRICE_BLOCKS},
              "known_at_quote": {b: int(x[f"known_{b}"].sum()) for b in C.PRICE_BLOCKS},
              "betonline_open_and_close_by_season": x[x["ok_bol_open"] & x["ok_bol_close"]].groupby("season").size()
              .to_dict(),
              "betonline_open_hours_before_listed_start": {q: round(float(x.loc[x["ok_bol_open"], "h_bol_open"]
                                                                           .quantile(q)), 2)
                                                            for q in (0.1, 0.25, 0.5, 0.75, 0.9)},
              "betonline_open_hours_by_season": {
                  str(s): {q: round(float(g["h_bol_open"].quantile(q)), 2) for q in (0.1, 0.5, 0.9)}
                  for s, g in x[x["ok_bol_open"]].groupby("season")},
              "betonline_linked_share_by_season": {
                  str(s): round(float(g["ok_bol_open"].mean()), 4) for s, g in x.groupby("season")},
              "openers": int(x["opener"].sum())}
    C.write_json(C.OUT / "frame_counts.json", counts)
    C.log(f"frame.parquet: {len(x)} matches; {counts['priced']}; known {counts['known_at_quote']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
