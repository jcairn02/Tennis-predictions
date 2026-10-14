"""Independent box scores as referees on both sides of the splice: does TML after Sackmann's end agree with the
official record as well as Sackmann did before it?

A referee is a source compiled apart from Sackmann and TML: the WTA API (box scores B3), TDI (ATP, mostly June to
September 2026), the Wimbledon and US Open feeds, and SofaScore (a candidate backup more than a referee). Each is
joined to Stage 0 through the match-timing link files (data/studies/match_timing/links/), keeping links whose score
agrees with Stage 0's, and its players are matched to Stage 0's by who won.

Two comparisons:
    referee_vs_stage0.csv   the referee against Stage 0's counts (Sackmann's before the splice, TML's after; rows that
                            fail Stage 0's checks are blank there), by tour, Stage 0 source and season
    referee_three_way.csv   before the splice, on the same players: the referee against Sackmann's raw counts and
                            against TML's raw counts of the same match (tml_vs_sackmann_pairs.parquet), by tour and season
    referee_rates.csv       pooled rates (first serves in per serve point, aces, double faults, points won behind
                            each serve, break points saved) of Stage 0 and of the referee on the same players (each
                            rate over the rows where both have its counts), by referee, tour, level, Stage 0 source and
                            season: the drift check that catches a whole event shifted at once
Also referee_wta_bp_orientation.csv (which side the WTA API records break points on) and referee_summary.json.
Run after tml_vs_sackmann.py: ./python.sh src/eda/data_continuity/referees.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.data_continuity import sources as R  # noqa: E402

T0 = time.time()
LINK_FILES = {"sofascore": "sofascore", "wta_api": "wta_api", "tdi": "tdi", "slam_feeds": "slam_feeds"}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def stage0_panel() -> tuple[pd.DataFrame, pd.DataFrame]:
    m, p = K.load_stage0()
    m["tdate"] = pd.to_datetime(m["tournament_date"], errors="coerce")
    meta = m[["match_id", "tour", "year", "level", "qualifying", "tdate", "source", "status", "source_file", "source_row"]]
    base = p.merge(meta, on="match_id", how="left", validate="many_to_one")
    base["period"] = np.where(base["tdate"] < K.SPLICE, "before", "after")
    return m, K.finish(base)


def referee_panel(name: str, players: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """The referee's rows with Stage 0's match and player ids."""
    rows = R.READERS[name]()
    links = pd.read_parquet(K.LINKS / f"{LINK_FILES[name]}.parquet", columns=["match_id", "source_key", "score_agrees"])
    stats = {"records": int(rows["source_key"].nunique()), "links": int(len(links))}
    links = links[links["score_agrees"].astype("boolean").fillna(False)]
    stats["links_with_agreeing_score"] = int(len(links))
    j = rows.merge(links, on="source_key", how="inner")
    j = j[j["won"].notna()].copy()
    j["won"] = j["won"].astype(bool)
    ids = players[["match_id", "won", "player_id"]]
    one = ids.groupby(["match_id", "won"])["player_id"].transform("size").eq(1)
    j = j.merge(ids[one], on=["match_id", "won"], how="inner")
    j = j.drop_duplicates(["source", "match_id", "player_id"])
    stats["player_rows_joined"] = int(len(j))
    stats["matches_joined"] = int(j["match_id"].nunique())
    return j, stats


def raw_pairs(m: pd.DataFrame, players: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Sackmann's and TML's raw counts of the same matches, placed on Stage 0's match and player ids."""
    pairs = pd.read_parquet(K.OUT / "tml_vs_sackmann_pairs.parquet")
    where = m[m["source"].eq("sackmann")][["match_id", "source_file", "source_row"]].copy()
    where["source_row"] = where["source_row"].astype(str)
    pairs["s_row"] = pairs["s_row"].astype(str)
    j = pairs.merge(where, left_on=["s_file", "s_row"], right_on=["source_file", "source_row"], how="inner")
    j["won"] = j["role"].eq("w")
    j = j.merge(players[["match_id", "won", "player_id", "player_name"]], on=["match_id", "won"], how="inner")
    same_name = K.norm_name(j["player"]).eq(K.norm_name(j["player_name"]))
    stats = {"pair_rows": int(len(pairs)), "placed_on_stage0": int(len(j)), "name_mismatch_dropped": int((~same_name).sum())}
    return j[same_name].drop_duplicates(["match_id", "player_id"]), stats


RATES = {"first_in_pct": ("first_in", "svpt"), "ace_pct": ("ace", "svpt"), "df_pct": ("df", "svpt"),
         "first_won_pct": ("first_won", "first_in"), "second_won_pct": ("second_won", "second"),
         "bp_saved_pct": ("bp_saved", "bp_faced")}


def pooled_rates(j: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Each rate pooled (sums, not means of ratios) over the rows where both Stage 0 and the referee have its two
    counts, for each version: ``stage0_<rate>`` and ``referee_<rate>``, with the rows each rate used."""
    f = j.assign(second=j["svpt"] - j["first_in"], second_ref=j["svpt_ref"] - j["first_in_ref"])
    parts = []
    for name, (n, d) in RATES.items():
        ok = f[[n, d, f"{n}_ref", f"{d}_ref"]].notna().all(axis=1)
        s = f[ok].groupby(by)[[n, d, f"{n}_ref", f"{d}_ref"]].sum()
        parts.append(pd.DataFrame({f"stage0_{name}": (100 * s[n] / s[d]).round(2),
                                   f"referee_{name}": (100 * s[f"{n}_ref"] / s[f"{d}_ref"]).round(2),
                                   f"rows_{name}": f[ok].groupby(by).size()}))
    return pd.concat(parts, axis=1)


def side(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    out = frame[["match_id", "player_id"]].copy()
    for f in K.FIELDS:
        out[f] = frame[f"{prefix}{f}"]
    return out


def main() -> int:
    m, base = stage0_panel()
    log(f"Stage 0: {len(m):,} matches, {len(base):,} player rows")
    pairs, pair_stats = raw_pairs(m, base)
    log(f"raw pairs on Stage 0: {len(pairs):,} ({pair_stats})")
    sack_raw, tml_raw = side(pairs, "s_"), side(pairs, "t_")
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "splice": str(K.SPLICE.date()), "raw_pairs": pair_stats, "referees": {}}
    vs_stage0, three = [], []
    orientation, rates = [], []
    for name in ("wta_api", "tdi", "slam_feeds", "sofascore"):
        ref, stats = referee_panel(name, base)
        log(f"{name}: {stats}")
        for src, sub in ref.groupby("source"):
            j = base.merge(sub[["match_id", "player_id"] + K.FIELDS + [c for c in ("bp_faced_alt", "bp_saved_alt") if c in sub]],
                           on=["match_id", "player_id"], how="inner", suffixes=("", "_ref"))
            left = j[["tour", "source", "period", "year", "level"] + K.FIELDS]
            right = j[[f"{f}_ref" for f in K.FIELDS]].set_axis(K.FIELDS, axis=1)
            a = K.agreement(left, right, ["tour", "source", "period", "year"])
            a.insert(0, "referee", src)
            vs_stage0.append(a)
            rates.append(pooled_rates(j, ["tour", "level", "source", "year"]).reset_index().assign(referee=src))
            if src == "wta_api":
                alt = right.copy()
                alt["bp_faced"], alt["bp_saved"] = j["bp_faced_alt"].to_numpy(), j["bp_saved_alt"].to_numpy()
                for label, r in (("returner side (used)", right), ("server side", alt)):
                    o = K.agreement(left, r, ["tour"], fields=["bp_faced", "bp_saved"])
                    o.insert(0, "reading", label)
                    orientation.append(o)
            # three-way, before the splice: the same players in Sackmann raw, TML raw and the referee
            t3 = sack_raw.merge(tml_raw, on=["match_id", "player_id"], suffixes=("_s", "_t")).merge(
                sub[["match_id", "player_id"] + K.FIELDS], on=["match_id", "player_id"])
            t3 = t3.merge(base[["match_id", "player_id", "tour", "year"]], on=["match_id", "player_id"])
            ref_vals = t3[K.FIELDS]
            for label, suffix in (("sackmann", "_s"), ("tml", "_t")):
                vals = t3[[f"{f}{suffix}" for f in K.FIELDS]].set_axis(K.FIELDS, axis=1)
                a3 = K.agreement(vals.assign(tour=t3["tour"], year=t3["year"]), ref_vals, ["tour", "year"])
                a3.insert(0, "against", label)
                a3.insert(0, "referee", src)
                three.append(a3)
            summary["referees"][src] = {**stats, "player_rows_compared_with_stage0": int(len(j)),
                                        "player_rows_three_way": int(len(t3))}
    out_a = pd.concat(vs_stage0, ignore_index=True)
    out_a.to_csv(K.OUT / "referee_vs_stage0.csv", index=False)
    out_t = pd.concat(three, ignore_index=True)
    out_t.to_csv(K.OUT / "referee_three_way.csv", index=False)
    pd.concat(orientation, ignore_index=True).to_csv(K.OUT / "referee_wta_bp_orientation.csv", index=False)
    out_r = pd.concat(rates, ignore_index=True)
    out_r = out_r[["referee"] + [c for c in out_r.columns if c != "referee"]]
    out_r.to_csv(K.OUT / "referee_rates.csv", index=False)
    K.write_json(K.OUT / "referee_summary.json", summary)
    log("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
