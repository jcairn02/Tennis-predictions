"""B3-referee, F7: are the 13 split-id pairs one person each, and is the alias safe?

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f7_*.csv and f7_summary.json.

Independent evidence per pair:
  * Sackmann's player files (dob, country), Tennis My Life's ATP database (dob by ATP code), the Live Tennis API Zenodo
    players file (dob, country, its own sackmann_id link);
  * the WTA API's own player ids (data/dump/points/wta/matches/<year>.parquet): the 9 new women's ids are WTA ids; a WTA
    API match whose player is the new id and that Stage 0 holds under the ESTABLISHED id (same week, same opponent name)
    proves the two ids are one person in the WTA's own records;
  * the dob implied by every Stage 0 row's age (Sackmann rounds to 0.1 y; TML to 0.001 y).
Simulation of the alias on the 7 Oct Stage 0: same id on both sides of a match; one id twice in a round of one event;
one id at two different events of one tournament week (counted before and after, so only new collisions count).
Also runs repair_data.repair_tables in memory to see what the existing repair does with each pair.
"""
from __future__ import annotations

import glob
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
S0 = ROOT / "data/studies/predictability_diagnostic"

PAIRS = [("wta", "wta:201548", "wta:315232"), ("wta", "wta:211713", "wta:320319"), ("wta", "wta:215035", "wta:324261"),
         ("wta", "wta:223253", "wta:330332"), ("wta", "wta:214082", "wta:322082"), ("wta", "wta:221236", "wta:328897"),
         ("wta", "wta:222391", "wta:328884"), ("wta", "wta:260765", "wta:332718"), ("wta", "wta:215386", "wta:321837"),
         ("atp", "atp:213206", "atpcode:O0A6"), ("atp", "atp:149128", "atpcode:M0VL"), ("atp", "atp:212827", "atpcode:M0PF"),
         ("atp", "atp:214346", "atpcode:C0UQ")]


def key(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(re.findall(r"[a-z]+", s)))


def read(path) -> pd.DataFrame:
    t = pq.ParquetFile(path).read().to_pandas()
    return t.loc[:, ~t.columns.duplicated()]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = pd.read_parquet(S0 / "stage0_match_players.parquet")
    m = pd.read_parquet(S0 / "stage0_matches.parquet")
    d = p[["match_id", "player_id", "opponent_id", "side", "player_name", "age", "country", "rank"]].merge(
        m[["match_id", "tour", "level", "qualifying", "round", "tournament_id", "tournament_name", "tournament_date",
           "source"]], on="match_id")
    d["key"] = d.player_name.map(key)
    d["tdate"] = pd.to_datetime(d.tournament_date)
    yrfrac = d.tdate.dt.year + (d.tdate.dt.dayofyear - 1) / 365.25
    d["dob_approx"] = yrfrac - d.age.where(d.age < 100)

    sa = read(ROOT / "data/dump/players/sackmann_archive/atp/atp_players.parquet").assign(tour="atp")
    sw = read(ROOT / "data/dump/players/sackmann_archive/wta/wta_players.parquet").assign(tour="wta")
    sk = pd.concat([sa, sw], ignore_index=True)
    sk["key"] = (sk.name_first.fillna("") + " " + sk.name_last.fillna("")).map(key)
    sk["cid"] = sk.tour + ":" + sk.player_id.astype(str)
    tml = read(ROOT / "data/dump/players/tennis_my_life/ATP_Database.parquet")
    zen = read(ROOT / "data/dump/players/live_tennis_api_zenodo/players.parquet")
    zen["key"] = zen.name.map(key)
    w = pd.concat([read(f) for f in sorted(glob.glob(str(ROOT / "data/dump/points/wta/matches/*.parquet")))],
                  ignore_index=True)
    w = w[w.DrawMatchType.astype(str).eq("S")] if "DrawMatchType" in w else w
    w["date"] = pd.to_datetime(w.MatchTimeStamp, errors="coerce", utc=True, format="ISO8601").dt.tz_localize(None)

    rows, evidence = [], []
    for tour, est, new in PAIRS:
        e, n = d[d.player_id.eq(est)], d[d.player_id.eq(new)]
        k = n.key.iloc[0]
        same_key_ids = d[(d.tour.eq(tour)) & d.key.eq(k)].groupby("player_id").size().to_dict()
        sk_same = sk[(sk.tour.eq(tour)) & sk.key.eq(k)][["cid", "dob", "ioc"]].to_dict("records")
        ev = {"tour": tour, "established_id": est, "new_id": new, "name_key": k,
              "established_rows": len(e), "new_rows": len(n),
              "established_names": sorted(e.player_name.unique().tolist()),
              "new_names": sorted(n.player_name.unique().tolist()),
              "established_countries": e.country.value_counts().to_dict(), "new_countries": n.country.value_counts().to_dict(),
              "established_dob_from_ages": [round(float(e.dob_approx.min()), 3), round(float(e.dob_approx.max()), 3)] if e.dob_approx.notna().any() else None,
              "new_dob_from_ages": sorted(set(round(float(x), 3) for x in n.dob_approx.dropna())),
              "new_ages_raw": n.age.tolist(),
              "stage0_ids_with_this_key": same_key_ids,
              "sackmann_ids_with_this_key": sk_same,
              "established_last": str(e.tdate.max().date()), "new_dates": sorted(set(str(x.date()) for x in n.tdate))}
        num = new.split(":")[1]
        if tour == "atp":
            t = tml[tml.id.eq(num)]
            ev["tml_atp_database"] = t[["id", "player", "birthdate", "ioc"]].to_dict("records")
        z = zen[zen.key.eq(k)]
        ev["zenodo_same_name"] = z[["player_id", "name", "tour", "country", "birthday", "sackmann_id"]].to_dict("records")
        if tour == "wta":
            a = w[w.PlayerIDA.astype(str).eq(num)].assign(me="A")
            b = w[w.PlayerIDB.astype(str).eq(num)].assign(me="B")
            ww = pd.concat([a, b])
            ev["wta_api_matches_with_new_id"] = int(len(ww))
            ev["wta_api_names"] = sorted(set((ww.PlayerNameFirstA.where(ww.me.eq("A"), ww.PlayerNameFirstB) + " "
                                              + ww.PlayerNameLastA.where(ww.me.eq("A"), ww.PlayerNameLastB)).tolist()))
            ev["wta_api_countries"] = sorted(set(ww.PlayerCountryA.where(ww.me.eq("A"), ww.PlayerCountryB).astype(str)))
            # cross-match: WTA API match (new id) <-> Stage 0 match of the ESTABLISHED id, same opponent name, within 8 days
            ww["opp"] = (ww.PlayerNameFirstB.where(ww.me.eq("A"), ww.PlayerNameFirstA) + " "
                         + ww.PlayerNameLastB.where(ww.me.eq("A"), ww.PlayerNameLastA)).map(key)
            eo = e.merge(d[["match_id", "player_id", "key"]].rename(columns={"player_id": "opp_id", "key": "opp"}),
                         left_on=["match_id", "opponent_id"], right_on=["match_id", "opp_id"], how="left")
            hits = 0
            tested = 0
            for r in ww.dropna(subset=["date"]).itertuples():
                c = eo[eo.opp.eq(r.opp) & (r.date - eo.tdate).dt.days.between(-1, 16)]
                tested += 1
                hits += int(len(c) > 0)
            ev["wta_api_new_id_matches_found_under_established_id"] = hits
            ev["wta_api_new_id_matches_tested"] = tested
            # and does the WTA API, for the new id's own Stage 0 matches, hold the new id?
            no = n.merge(d[["match_id", "player_id", "key"]].rename(columns={"player_id": "opp_id", "key": "opp"}),
                         left_on=["match_id", "opponent_id"], right_on=["match_id", "opp_id"], how="left")
            ok = 0
            for r in no.itertuples():
                c = ww[ww.opp.eq(r.opp) & (ww.date - r.tdate).dt.days.between(-1, 16)]
                ok += int(len(c) > 0)
            ev["new_id_stage0_matches_found_in_wta_api_under_new_id"] = f"{ok}/{len(no)}"
        evidence.append(ev)

    # --- simulate the alias on the 7 Oct Stage 0 -----------------------------------------------------------------
    amap = {new: est for _, est, new in PAIRS}

    def collisions(df: pd.DataFrame) -> dict:
        same_both = df.groupby("match_id").player_id.nunique().lt(2)
        r = df.groupby(["tournament_id", "tournament_name", "qualifying", "round", "player_id"]).match_id.nunique()
        twice_in_round = r[r > 1]
        wk = df.groupby(["tour", "tournament_date", "player_id"]).tournament_id.nunique()
        two_events = wk[wk > 1]
        return {"same_id_both_sides": set(same_both[same_both].index),
                "twice_in_round": set(twice_in_round.index), "two_events_same_week": set(two_events.index)}

    before = collisions(d)
    d2 = d.copy()
    d2["player_id"] = d2.player_id.replace(amap)
    after = collisions(d2)
    sim = {k: sorted(map(str, after[k] - before[k])) for k in after}
    sim["before_counts"] = {k: len(v) for k, v in before.items()}

    # --- what does the existing repair do with these pairs? ------------------------------------------------------
    try:
        from src.eda.feature_alpha_audit.repair_data import repair_tables
        m2, p2, meta = repair_tables(m, p)
        rep = {}
        for tour, est, new in PAIRS:
            rows_new = p.player_id.eq(new)
            rep[new] = {"rows": int(rows_new.sum()), "now": p2.loc[rows_new, "player_id"].value_counts().to_dict(),
                        "conflicts": [c for c in meta["identity_conflicts_left_unresolved"] if c.get("source_id") == new]}
        sim["repair_tables_on_oct07"] = rep
    except Exception as ex:  # pragma: no cover - diagnostic only
        sim["repair_tables_on_oct07"] = f"failed: {ex!r}"

    (OUT / "f7_evidence.json").write_text(json.dumps({"pairs": evidence, "simulation": sim}, indent=1, default=str),
                                          encoding="utf-8")
    print(json.dumps({"pairs": evidence, "simulation": sim}, indent=1, default=str))


if __name__ == "__main__":
    main()
