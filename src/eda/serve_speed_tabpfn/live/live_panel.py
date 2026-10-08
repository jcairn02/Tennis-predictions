"""The live speed panel: the study's frozen speed_panel.parquet, unchanged, plus the new daily rows. Reads no match result.

    frozen rows   every row of speed_panel.parquet as it is, plus `release`: the day the row may enter features. That is
                  the scenario's release (default B, the weekly feed through which these rows came:
                  latency/availability.parquet), capped at FROZEN_IN_HAND (7 Oct 2026, when every frozen row was in
                  hand) but never before lf + 1, and live_source = "frozen"
    new rows      linked staged matches (link.py) not already in the frozen panel, one row per side, on the
                  key-statistic basis: y = first-serve average - 0.5 (the ceiling rule), n = first serves in,
                  basis "ks"; release = the collection day; drops as panel.py's (no clock, men < 120 km/h, n < 10)
                  give use = False. A match two collections bring is kept from the first
The frozen file is only read; the live panel is written to live/speed_panel_live.parquet.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.serve_speed_tabpfn.live import common as LC

FROZEN_IN_HAND = "2026-10-07"
KS_SHIFT = -0.5
MEN_MIN, MIN_N = 120.0, 10
TOUR_LEVELS = ("T250", "T500", "T1000", "FIN")


def frozen_rows(scenario: str = "B") -> pd.DataFrame:
    from src.eda.serve_speed_tabpfn import panel as P
    from src.eda.serve_speed_tabpfn.latency import availability as AV
    p = P.load_panel(use_only=False)
    col = AV.SCENARIOS[scenario]
    av = AV.load(["match_id", "side", col])
    p = p.merge(av, on=["match_id", "side"], how="left", validate="one_to_one")
    assert p[col].notna().all()
    # in hand since FROZEN_IN_HAND, but never before the match surely finished (lf + 1; the clock rule)
    p["release"] = np.maximum(np.minimum(p[col].to_numpy(np.int64), LC.day_of(FROZEN_IN_HAND)),
                              p["lf"].to_numpy(np.int64) + 1)
    p = p.drop(columns=[col])
    p["collected_on"] = None
    p["live_source"] = "frozen"
    p["release_scenario"] = scenario
    return p


def _family(level: str, qual: bool) -> str:
    base = "tour" if level in TOUR_LEVELS else "ch" if level == "CH" else "other"
    return f"{base}|{'Q' if qual else 'M'}"


def new_rows(linked: pd.DataFrame) -> pd.DataFrame:
    """Long rows (one per side) from linked staged matches with a match id and an orientation."""
    from src.eda.predictability_diagnostic import common as PD
    lk = linked[linked["match_id"].notna() & linked["side_p1"].isin(["A", "B"])].copy()
    if lk.empty:
        return pd.DataFrame()
    out = []
    for side in ("A", "B"):
        own = np.where(lk["side_p1"].eq(side), "p1", "p2")
        opp = np.where(own == "p1", "p2", "p1")

        def pick(stem, src=own):
            return np.array([lk[f"{o}_{stem}"].iloc[k] for k, o in enumerate(src)])
        level = lk["level_s0"].where(lk["in_stage0"], lk.get("level_tml"))
        rnd = lk["round_s0"].where(lk["in_stage0"], lk.get("round_tml")).fillna(lk["round"])
        qual = lk["qualifying_s0"].where(lk["in_stage0"], lk.get("qual_tml"))
        qual = qual.fillna(rnd.astype(str).str.startswith("Q") & rnd.ne("QF")).astype(bool)
        spd1 = pick("spd1").astype(float)
        first_in = pick("first_in").astype(float)
        first_tot = pick("first_total").astype(float)
        spd2 = pick("spd2").astype(float)
        d = pd.DataFrame({
            "match_id": lk["match_id"].to_numpy(), "side": side,
            "player_id": np.where(own == "p1", lk["pid_p1"], lk["pid_p2"]),
            "opp_id": np.where(opp == "p1", lk["pid_p1"], lk["pid_p2"]),
            "tour": "atp", "year": lk["year"].astype(int).to_numpy(), "level": level.to_numpy(),
            "qualifying": qual.to_numpy(), "round": rnd.to_numpy(),
            "round_order": rnd.map(PD.ROUND_ORDER).to_numpy(), "tournament_id": lk["tid"].to_numpy(),
            "tdate": pd.to_numeric(lk["tdate"], errors="coerce").to_numpy(),
            "es": pd.to_numeric(lk["es"], errors="coerce").to_numpy(),
            "lf": pd.to_numeric(lk["lf"], errors="coerce").to_numpy(),
            "obs": pd.to_numeric(lk["obs"], errors="coerce").to_numpy(),
            "source": lk["source"].to_numpy(),
            "source_key": lk.get("mantd_id", pd.Series(None, index=lk.index)).fillna(
                lk["year"].astype(str) + "_" + lk["event_id"].astype(str) + "_" + lk["match_code"].astype(str)).to_numpy(),
            "basis": "ks", "kind": "keystat", "y_raw": spd1, "y": spd1 + KS_SHIFT, "n": first_in, "f1": first_in,
            "spd2_raw": spd2, "spd2": spd2 + KS_SHIFT, "n2": first_tot - first_in, "spd_max": pick("max").astype(float),
            "collected_on": lk["collected_on"].to_numpy(), "link_method": lk["link_method"].to_numpy(),
            "in_stage0": lk["in_stage0"].to_numpy(), "live_source": "daily"})
        out.append(d)
    n = pd.concat(out, ignore_index=True)
    n = n[np.isfinite(n["y_raw"])].copy()
    n["mq"] = np.where(n["qualifying"], "Q", "M")
    n["family"] = [_family(lv, q) for lv, q in zip(n["level"].fillna("T250"), n["qualifying"])]
    n["edition"] = n["tournament_id"] + "|" + n["mq"] + "|ks"
    n["event"] = n["tournament_id"].str.split("-", n=1).str[1]
    n["slam"] = ""
    n["obs_raw"] = n["obs"]
    n["rel"] = n["lf"] + 1
    n["release"] = [LC.day_of(c) for c in n["collected_on"]]
    n["n"] = n["n"].fillna(0).round().astype("int64")
    reason = pd.Series("", index=n.index, dtype=object)
    reason[n[["es", "lf", "obs"]].isna().any(axis=1)] = "no_clock"
    reason[(reason == "") & (n["y"] < MEN_MIN)] = "implausible"
    reason[(reason == "") & (n["n"] < MIN_N)] = "low_n"
    n["drop_reason"] = reason
    n["use"] = reason.eq("")
    # never before the match surely finished
    n["release"] = np.maximum(n["release"], (n["lf"].fillna(-10**6) + 1).astype("int64"))
    return n


def build(linked: pd.DataFrame, scenario: str = "B", out: Path = LC.OUT) -> tuple[pd.DataFrame, dict]:
    fr = frozen_rows(scenario)
    nw = new_rows(linked)
    keys = set(zip(fr["match_id"], fr["side"]))
    if len(nw):
        nw = nw[[k not in keys for k in zip(nw["match_id"], nw["side"])]]
        nw = nw.sort_values(["match_id", "side", "release"]).drop_duplicates(["match_id", "side"], keep="first")
        for c in ("es", "lf", "obs", "tdate", "rel", "round_order"):
            nw[c] = pd.to_numeric(nw[c], errors="coerce").astype("Int64")
    live = pd.concat([fr, nw], ignore_index=True, sort=False)
    for c in ("es", "lf", "obs", "tdate", "rel", "release", "round_order", "n"):
        live[c] = pd.to_numeric(live[c], errors="coerce")
    ok = live["es"].notna() & live["lf"].notna() & live["obs"].notna() & live["tdate"].notna()
    for c in ("es", "lf", "obs", "tdate", "rel", "release", "n"):
        live.loc[ok, c] = live.loc[ok, c].astype("int64")
    live["use"] = live["use"].astype(bool) & ok
    assert not live.duplicated(["match_id", "side"]).any()
    out.mkdir(parents=True, exist_ok=True)
    live.to_parquet(out / LC.PANEL_LIVE.name, index=False)
    summ = {"frozen_rows": int(len(fr)), "new_rows": int(len(nw)), "new_use": int(nw["use"].sum()) if len(nw) else 0,
            "new_by_source": nw["source"].value_counts().to_dict() if len(nw) else {},
            "new_by_link": nw["link_method"].value_counts().to_dict() if len(nw) else {},
            "release_scenario_frozen": scenario, "frozen_in_hand": FROZEN_IN_HAND}
    (out / "live_panel_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    return live, summ


def load(out: Path = LC.OUT) -> pd.DataFrame:
    return pd.read_parquet(out / LC.PANEL_LIVE.name)
