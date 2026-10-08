"""Round 0, body-and-schedule brainstormer: how often each body/schedule situation occurs (prevalence and power only).

No relation to any match's outcome or odds is computed. The current match's result is never read; earlier matches'
results are read only to say who retired or gave a walkover in a player's previous match (a feature input).
Target rows: main-tour main draws (GS, T1000, T500, T250, FIN), seasons 2013-2021 (discovery) and 2022-2024
(replication). History: every level, seasons up to 2024.

Run: ./python.sh src/eda/feature_interactions/round0/body/counts.py
Writes: data/studies/feature_interactions/round0/body/counts.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic import stage4_country as SC  # noqa: E402  (read-only import)

S0 = ROOT / "data/studies/predictability_diagnostic"
TM = ROOT / "data/studies/match_timing/timing.parquet"
OUT = ROOT / "data/studies/feature_interactions/round0/body"
MAIN = {"GS", "T1000", "T500", "T250", "FIN"}

CONTINENT = {
    # Europe
    **{c: "EU" for c in ["AND", "AUT", "AZE", "BEL", "BIH", "BUL", "CRO", "CZE", "ESP", "EST", "FIN", "FRA", "GBR",
                         "GEO", "GER", "GRE", "HUN", "IRL", "ITA", "LAT", "LTU", "LUX", "MDA", "MKD", "MON", "NED",
                         "POL", "POR", "ROU", "RUS", "SLO", "SMR", "SRB", "SUI", "SVK", "SWE", "TUR", "UKR"]},
    # Middle East / central Asia
    **{c: "ME" for c in ["BRN", "ISR", "KSA", "QAT", "UAE", "KAZ", "UZB", "PAK"]},
    # Asia / Oceania
    **{c: "AS" for c in ["CHN", "HKG", "IND", "JPN", "KOR", "MAS", "PHI", "SGP", "THA", "TPE", "VIE"]},
    **{c: "OC" for c in ["AUS", "NZL"]},
    # Americas
    **{c: "NA" for c in ["USA", "CAN", "MEX", "DOM", "PUR", "PAN"]},
    **{c: "SA" for c in ["ARG", "BOL", "BRA", "CHI", "COL", "ECU", "PAR", "PER", "URU"]},
    # Africa
    **{c: "AF" for c in ["CGO", "CIV", "EGY", "MAR", "RSA", "RWA", "TUN"]},
}


def load() -> pd.DataFrame:
    m = pd.read_parquet(S0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "year", "level", "qualifying", "round", "round_order",
                                 "surface", "indoor", "best_of", "tournament_id", "tournament_name",
                                 "tournament_date", "status", "minutes", "order"])
    m = m[m["year"] <= 2024].copy()
    m["event_country"] = SC.event_country(m)
    t = pd.read_parquet(TM, columns=["match_id", "es", "lf", "obs", "exact"])
    m = m.merge(t, on="match_id", how="left")
    # 'won' is read only to attribute an EARLIER match's retirement or walkover; the current match's result is
    # dropped below before anything is counted.
    p = pd.read_parquet(S0 / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "won", "entry", "country", "age", "rank",
                                 "sets_won_d", "games_won_d", "tpw_d"])
    d = p.merge(m, on="match_id", how="inner")
    return d.sort_values(["player_id", "order"]).reset_index(drop=True)


def per_player(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("player_id", sort=False)
    # previous scheduled match (walkovers included): how it ended for this player
    prev_status = g["status"].shift(1)
    prev_won = g["won"].shift(1)
    d["prev_retired_self"] = (prev_status == "retired") & (prev_won == False)  # noqa: E712
    d["prev_retired_opp"] = (prev_status == "retired") & (prev_won == True)  # noqa: E712
    d["prev_wo_given"] = (prev_status == "walkover") & (prev_won == False)  # noqa: E712
    d["prev_wo_received"] = (prev_status == "walkover") & (prev_won == True)  # noqa: E712
    d = d.drop(columns=["won"])  # nothing below may see a result

    played = d["status"].isin(["completed", "retired"])
    q = d[played].copy()
    gq = q.groupby("player_id", sort=False)
    for col in ["obs", "exact", "minutes", "tournament_id", "event_country", "surface", "indoor", "best_of",
                "sets_won_d", "round"]:
        q[f"prev_{col}"] = gq[col].shift(1)
    # last match of the previous tournament (different tournament id): its round and day
    q["new_event"] = q["tournament_id"] != q["prev_tournament_id"]
    q["evt_rank"] = gq["new_event"].cumsum()
    last_in_evt = q.groupby(["player_id", "evt_rank"], sort=False).tail(1)[
        ["player_id", "evt_rank", "obs", "round", "level", "event_country", "tournament_id", "minutes", "best_of"]]
    last_in_evt = last_in_evt.rename(columns={c: f"pe_{c}" for c in last_in_evt.columns if c not in ("player_id",)})
    last_in_evt["evt_rank"] = last_in_evt["pe_evt_rank"] + 1
    q = q.merge(last_in_evt.drop(columns=["pe_evt_rank"]), on=["player_id", "evt_rank"], how="left")
    # rolling loads over obs days (strictly earlier matches in the player's order)
    out = {k: np.full(len(q), np.nan) for k in
           ["m7", "m14", "m28", "min7", "min14", "min28", "min7_ok", "min28_ok", "evts42"]}
    q = q.sort_values(["player_id", "order"]).reset_index(drop=True)
    starts = q.groupby("player_id", sort=False).indices
    obs = q["obs"].to_numpy()
    mins = q["minutes"].to_numpy()
    tid = q["tournament_id"].astype(str).to_numpy()
    for _, idx in starts.items():
        o = obs[idx]
        mm = mins[idx]
        has = ~np.isnan(mm)
        cm = np.concatenate([[0.0], np.cumsum(np.where(has, mm, 0.0))])
        ch = np.concatenate([[0], np.cumsum(has)])
        for w, key in [(7, "7"), (14, "14"), (28, "28")]:
            lo = np.searchsorted(o, o - w, side="left")
            n = np.arange(len(idx)) - lo
            out[f"m{key}"][idx] = n
            out[f"min{key}"][idx] = cm[np.arange(len(idx))] - cm[lo]
            if key in ("7", "28"):
                out[f"min{key}_ok"][idx] = (ch[np.arange(len(idx))] - ch[lo]) == n
        lo42 = np.searchsorted(o, o - 42, side="left")
        t = tid[idx]
        out["evts42"][idx] = [len(set(t[a:i])) for i, a in enumerate(lo42)]
    for k, v in out.items():
        q[k] = v
    q["rest"] = q["obs"] - q["prev_obs"]
    q["rest_exact"] = q["exact"].astype(bool) & q["prev_exact"].fillna(False).astype(bool)
    q["gap_prev_event"] = q["obs"] - q["pe_obs"]
    return q


def summarise(q: pd.DataFrame) -> dict:
    tgt = q[q["level"].isin(MAIN) & ~q["qualifying"] & (q["year"] >= 2013)].copy()
    tgt["window"] = np.where(tgt["year"] <= 2021, "2013-2021", "2022-2024")
    res: dict = {}
    for (tour, win), x in tgt.groupby(["tour", "window"]):
        key = f"{tour}|{win}"
        r: dict = {"player_matches": int(len(x)), "matches": int(x["match_id"].nunique())}
        r["exact_this_and_prev"] = round(float(x["rest_exact"].mean()), 4)
        bins = [-1, 0, 1, 2, 6, 13, 29, 89, 10_000]
        labels = ["0", "1", "2", "3-6", "7-13", "14-29", "30-89", "90+"]
        r["rest_days_share"] = (pd.cut(x["rest"], bins=bins, labels=labels).value_counts(normalize=True)
                                .reindex(labels).round(4).to_dict())
        same_event = x["tournament_id"] == x["prev_tournament_id"]
        r["prev_same_event_share"] = round(float(same_event.mean()), 4)
        r["prev_minutes_known_share"] = round(float(x["prev_minutes"].notna().mean()), 4)
        thr = 180 if tour == "atp" else 150
        r[f"prev_minutes_ge_{thr}_share_of_known"] = round(float((x["prev_minutes"] >= thr).sum()
                                                                 / max(1, x["prev_minutes"].notna().sum())), 4)
        r["min28_complete_share"] = round(float((x["min28_ok"] == 1).mean()), 4)
        for f in ["prev_retired_self", "prev_retired_opp", "prev_wo_given", "prev_wo_received"]:
            r[f + "_share"] = round(float(x[f].mean()), 4)
        r["prev_retired_self_and_rest_le_14"] = int((x["prev_retired_self"] & (x["rest"] <= 14)).sum())
        newevt = ~same_event
        r["first_match_of_event_share"] = round(float(newevt.mean()), 4)
        fe = x[newevt]
        r["first_match_prev_event_final_and_gap_le_4"] = int(((fe["pe_round"] == "F") & (fe["gap_prev_event"] <= 4)).sum())
        r["first_match_prev_event_SF_or_F_and_gap_le_4"] = int((fe["pe_round"].isin(["SF", "F"]) & (fe["gap_prev_event"] <= 4)).sum())
        cont_this = fe["event_country"].map(CONTINENT)
        cont_prev = fe["pe_event_country"].map(CONTINENT)
        both = cont_this.notna() & cont_prev.notna() & (fe["gap_prev_event"] <= 21)
        r["first_match_prev_event_within_21d_both_continents_known"] = int(both.sum())
        r["...of_which_continent_change"] = int((both & (cont_this != cont_prev)).sum())
        r["...of_which_continent_change_and_gap_le_7"] = int((both & (cont_this != cont_prev) & (fe["gap_prev_event"] <= 7)).sum())
        r["layoff_ge_42d_share"] = round(float((x["rest"] >= 42).mean()), 4)
        r["layoff_ge_42d_not_jan_share"] = round(float(((x["rest"] >= 42) & (x["tournament_date"].dt.month != 1)
                                                         & ~((x["tournament_date"].dt.month == 12))).mean()), 4)
        r["events_in_last_42d_ge_4_share"] = round(float((x["evts42"] >= 4).mean()), 4)
        r["home_share"] = round(float((SC.player_country(x["country"]) == x["event_country"]).mean()), 4)
        r["entry_share"] = x["entry"].fillna("-").value_counts(normalize=True).head(8).round(4).to_dict()
        r["age_ge_32_share"] = round(float((x["age"] >= 32).mean()), 4)
        r["indoor_switch_first_match_share"] = round(float((newevt & (x["indoor"] != x["prev_indoor"])).mean()), 4)
        r["prev_best_of_5_share_first_match"] = round(float(((fe["pe_best_of"] == 5) & (fe["gap_prev_event"] <= 14)).mean()), 4)
        res[key] = r
    # rest asymmetry within a match (both players' previous matches within 14 days, exact days)
    pair = tgt.groupby("match_id").agg(n=("player_id", "size"), r1=("rest", "first"), r2=("rest", "last"),
                                       e=("rest_exact", "all"), tour=("tour", "first"), window=("window", "first"),
                                       m1=("min14", "first"), m2=("min14", "last"))
    pair = pair[(pair["n"] == 2) & pair["e"] & (pair[["r1", "r2"]].max(axis=1) <= 14)]
    pair["asym"] = (pair["r1"] - pair["r2"]).abs()
    res["rest_asymmetry_exact_both_within_14d"] = {
        f"{t}|{w}": {"matches": int(len(x)), **(pd.cut(x["asym"], [-1, 0, 1, 2, 100], labels=["0", "1", "2", "3+"])
                                               .value_counts(normalize=True).round(4).to_dict())}
        for (t, w), x in pair.groupby(["tour", "window"])}
    return res


def main() -> None:
    d = load()
    q = per_player(d)
    res = summarise(q)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "counts.json").write_text(json.dumps(res, indent=1, default=str))
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
