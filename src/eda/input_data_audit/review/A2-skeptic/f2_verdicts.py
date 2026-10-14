"""F2 review (A2-skeptic): per-match verdicts for the 88 "exchanged box score" matches.

Reads f2_detail.csv (from f2_swapped.py) and compares each match with every independent record held:
  * WTA API (2019-2026), matched by season and both surnames (tournament id preferred; Slams 580/520/540/560 ->
    901/903/904/905), counts mapped as in src/eda/data_continuity/sources.py;
  * Wimbledon / US Open feeds (src/eda/data_continuity/sources.slam_feeds), SofaScore (sources.sofascore);
  * sirgenkii's ATP key statistics (2025), Infosys AO 2025 point by point, the Match Charting Project.
For each record: does its winner equal Stage 0's winner, and how many counts equal Stage 0's as recorded against
exchanged. Then the internal evidence (identity error k, games margin, points) with the coincidence analysis.
Writes data/studies/input_data_audit/fixes/A2-skeptic/f2_verdicts.csv (all 88) and f2_records.csv.
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f2_verdicts.py
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

import _common as K
from src.eda.data_continuity import sources as DS

SLAM_WTA = {"580": "901", "520": "903", "540": "904", "560": "905"}
FIELDS = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]


def toks(s) -> set:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return {t for t in re.findall(r"[a-z]+", s) if len(t) >= 3}


def surname(s) -> str:
    t = re.findall(r"[a-z]+", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return t[-1] if t else ""


def stage0_boxes(r) -> tuple[dict, dict]:
    a = {c: getattr(r, c) for c in FIELDS}
    b = {c: getattr(r, f"o_{c}") for c in FIELDS}
    return (a, b) if r.won else (b, a)


def compare(sw: dict, sl: dict, rw: dict, rl: dict) -> tuple[int, int, int]:
    """Counts equal as recorded (Stage 0 winner = record's winner-player) and exchanged; fields compared."""
    rec = exc = n = 0
    for c in FIELDS:
        if c not in rw or pd.isna(rw.get(c)) or pd.isna(rl.get(c)):
            continue
        n += 2
        rec += int(float(sw[c]) == float(rw[c])) + int(float(sl[c]) == float(rl[c]))
        exc += int(float(sw[c]) == float(rl[c])) + int(float(sl[c]) == float(rw[c]))
    return rec, exc, n


def main() -> None:
    x = pd.read_csv(K.OUT / "f2_detail.csv", parse_dates=["tournament_date"])
    x["sw"], x["sl"] = x["winner_name"].map(surname), x["loser_name"].map(surname)
    records = []

    # ---- WTA API
    api = K.wta_api()
    api["ta"], api["tb"] = api["name_a"].map(toks), api["name_b"].map(toks)
    for r in x[x["tour"].eq("wta")].itertuples():
        c = api[api["year"].astype(str).eq(str(r.year))]
        hit = [(r.sw in a and r.sl in b) or (r.sl in a and r.sw in b) for a, b in zip(c["ta"], c["tb"])]
        c = c[hit]
        tid = str(r.tournament_id).split("-")[-1]
        tid = SLAM_WTA.get(tid, tid)
        if len(c) > 1:
            c = c[c["tournament_id"].astype(str).eq(tid)]
        if len(c) != 1 or str(c.iloc[0]["tournament_id"]) != tid:
            continue
        a = c.iloc[0]
        w_side = "a" if r.sw in a["ta"] else "b"
        l_side = "b" if w_side == "a" else "a"
        rw = {f: a[f"{w_side}_{f}"] for f in FIELDS}
        rl = {f: a[f"{l_side}_{f}"] for f in FIELDS}
        sw, sl = stage0_boxes(r)
        rec, exc, n = compare(sw, sl, rw, rl)
        g_w = a[f"games_{w_side}"]
        idw = rw["sv_gms"] - (rw["bp_faced"] - rw["bp_saved"]) + (rl["bp_faced"] - rl["bp_saved"])
        records.append({"match_id": r.match_id, "source": "wta_api", "record": a["key"], "record_result": a["ResultString"],
                        "record_winner_is_stage0_winner": a["winner_side"] == w_side, "equal_as_recorded": rec,
                        "equal_exchanged": exc, "fields": n,
                        "record_own_identity_holds": (bool(idw == g_w) if not a["any_tb"] else None)})

    # ---- Wimbledon / US Open feeds
    sf = DS.slam_feeds()
    names = []
    for site in ("wimbledon", "usopen"):
        m = pd.read_parquet(K.ROOT / "data/dump/points" / site / "matches.parquet",
                            columns=["year", "event", "match_id", "entry.team1.lastNameA", "entry.team2.lastNameA"])
        m["source_key"] = site + ":" + m["year"].astype(str) + "/" + m["event"].astype(str) + "/" + m["match_id"].astype(str)
        names.append(m)
    names = pd.concat(names)
    sf = sf.merge(names[["source_key", "year", "entry.team1.lastNameA", "entry.team2.lastNameA"]], on="source_key")
    sf["name"] = np.where(sf["side"].eq("team_1"), sf["entry.team1.lastNameA"], sf["entry.team2.lastNameA"])
    sf["sn"] = sf["name"].map(lambda s: " ".join(sorted(toks(s))))
    site_of = {"540": "wimbledon", "560": "usopen"}
    for r in x.itertuples():
        site = site_of.get(str(r.tournament_id).split("-")[-1])
        if site is None:      # only the same Slam's own feed is a record of this match
            continue
        c = sf[sf["year"].astype(str).eq(str(r.year)) & sf["source_key"].str.startswith(site + ":")]
        keys = set(c.loc[c["sn"].map(lambda s: r.sw in s), "source_key"]) & set(c.loc[c["sn"].map(lambda s: r.sl in s), "source_key"])
        for k in keys:
            cc = c[c["source_key"].eq(k)]
            w = cc[cc["sn"].map(lambda s: r.sw in s)].iloc[0]
            l_ = cc[cc["sn"].map(lambda s: r.sl in s)].iloc[0]
            sw, sl = stage0_boxes(r)
            rec, exc, n = compare(sw, sl, w.to_dict(), l_.to_dict())
            records.append({"match_id": r.match_id, "source": k.split(":")[0], "record": k,
                            "record_winner_is_stage0_winner": bool(w["won"]) if pd.notna(w["won"]) else None,
                            "equal_as_recorded": rec, "equal_exchanged": exc, "fields": n})

    # ---- SofaScore
    so = DS.sofascore()
    ev = []
    for col in ("sofascore", "sofascore_editions", "sofascore_tournaments"):
        e = pd.read_parquet(K.ROOT / "data/dump/points" / col / "events.parquet",
                            columns=["event_id", "start_utc", "home_name", "away_name"])
        ev.append(e)
    ev = pd.concat(ev).drop_duplicates("event_id")
    ev["source_key"] = "sofascore:" + ev["event_id"].astype(str)
    so = so.merge(ev, on="source_key", how="left")
    so["name"] = np.where(so["side"].eq("home"), so["home_name"], so["away_name"])
    so["sn"] = so["name"].map(lambda s: " ".join(sorted(toks(s))))
    so["year"] = so["start_utc"].astype(str).str[:4]
    for r in x.itertuples():
        c = so[so["year"].eq(str(r.year))]
        keys = set(c.loc[c["sn"].map(lambda s: r.sw in s), "source_key"]) & set(c.loc[c["sn"].map(lambda s: r.sl in s), "source_key"])
        for k in keys:
            cc = c[c["source_key"].eq(k)]
            w = cc[cc["sn"].map(lambda s: r.sw in s)].iloc[0]
            l_ = cc[cc["sn"].map(lambda s: r.sl in s)].iloc[0]
            sw, sl = stage0_boxes(r)
            rec, exc, n = compare(sw, sl, w.to_dict(), l_.to_dict())
            records.append({"match_id": r.match_id, "source": "sofascore", "record": k,
                            "record_winner_is_stage0_winner": bool(w["won"]) if pd.notna(w["won"]) else None,
                            "equal_as_recorded": rec, "equal_exchanged": exc, "fields": n})

    # ---- sirgenkii ATP key statistics (2025): service points won share, total points won share, aces, dfs
    kr = pd.read_parquet(K.ROOT / "data/dump/points/sirgenkii_infotennis/atp_results.parquet")
    ks = pd.read_parquet(K.ROOT / "data/dump/points/sirgenkii_infotennis/atp_key_stats.parquet")
    for r in x[x["tour"].eq("atp")].itertuples():
        c = kr[kr["year"].astype(str).eq(str(r.year))]
        hit = [(r.sw in toks(a) and r.sl in toks(b)) or (r.sl in toks(a) and r.sw in toks(b))
               for a, b in zip(c["player1_name"], c["player2_name"])]
        for _, h in c[hit].iterrows():
            kk = ks[(ks["year"].astype(str) == str(h["year"])) & (ks["tournament_id"].astype(str) == str(h["tournament_id"]))
                    & (ks["match_id"].astype(str) == str(h["match_id"])) & (ks["set_n"].astype(str) == "0")]
            pid_w = h["player1_id"] if r.sw in toks(h["player1_name"]) else h["player2_id"]
            kw = kk[kk["player_id"].astype(str).str.lower() == str(pid_w).lower()]
            if kw.empty or float(kw.iloc[0]["aces"]) < 0:
                continue
            kw = kw.iloc[0]
            sw, sl = stage0_boxes(r)
            tp_rec = (sw["first_won"] + sw["second_won"] + sl["svpt"] - sl["first_won"] - sl["second_won"]) / (sw["svpt"] + sl["svpt"])
            tp_exc = 1 - tp_rec
            records.append({"match_id": r.match_id, "source": "sirgenkii_keystats", "record": f"{h['tournament_id']}/{h['match_id']}",
                            "record_winner_is_stage0_winner": None,
                            "equal_as_recorded": int(float(kw["aces"]) == sw["ace"]) + int(float(kw["double_faults"]) == sw["df"])
                            + int(float(kw["service_games_played"]) == sw["sv_gms"]) + int(float(kw["break_points_faced"]) == sw["bp_faced"]),
                            "equal_exchanged": int(float(kw["aces"]) == sl["ace"]) + int(float(kw["double_faults"]) == sl["df"])
                            + int(float(kw["service_games_played"]) == sl["sv_gms"]) + int(float(kw["break_points_faced"]) == sl["bp_faced"]),
                            "fields": 4, "note": f"winner's total points won share: record {float(kw['total_points_won']):.4f}, "
                                                f"Stage 0 as recorded {tp_rec:.4f}, exchanged {tp_exc:.4f}"})

    # ---- Infosys AO 2025 point by point (some points missing): serve points, aces, double faults, points won
    im = pd.read_parquet(K.INFOSYS / "matches.parquet", columns=["slam", "year", "match_id", "p1_name", "p2_name", "match_winner"])
    im = im[im["slam"].eq("AO") & im["year"].astype(str).eq("2025")]
    ip = pd.read_parquet(K.INFOSYS / "points.parquet", columns=["slam", "year", "match_id", "server", "serve", "scorer", "result"],
                         filters=[("slam", "==", "AO"), ("year", "==", "2025")])
    for r in x[x["year"].eq(2025)].itertuples():
        hit = [(r.sw in toks(a) and r.sl in toks(b)) or (r.sl in toks(a) and r.sw in toks(b)) for a, b in zip(im["p1_name"], im["p2_name"])]
        for _, h in im[hit].iterrows():
            p = ip[ip["match_id"].eq(h["match_id"])]
            wno = "1" if r.sw in toks(h["p1_name"]) else "2"
            lno = "2" if wno == "1" else "1"
            def cnt(no):
                s = p[p["server"].astype(str).eq(no)]
                return {"svpt": len(s), "ace": int(s["result"].eq("A").sum()), "df": int(s["result"].eq("DF").sum()),
                        "won": int(p["scorer"].astype(str).eq(no).sum())}
            cw, cl = cnt(wno), cnt(lno)
            sw, sl = stage0_boxes(r)
            pts_w_rec = sw["first_won"] + sw["second_won"] + sl["svpt"] - sl["first_won"] - sl["second_won"]
            pts_l_rec = sl["first_won"] + sl["second_won"] + sw["svpt"] - sw["first_won"] - sw["second_won"]
            d_rec = sum(abs(sw[f] - cw[f]) + abs(sl[f] - cl[f]) for f in ("svpt", "ace", "df"))
            d_exc = sum(abs(sw[f] - cl[f]) + abs(sl[f] - cw[f]) for f in ("svpt", "ace", "df"))
            records.append({"match_id": r.match_id, "source": "infosys_ao2025_points", "record": h["match_id"],
                            "record_winner_is_stage0_winner": str(h["match_winner"]) == wno,
                            "equal_as_recorded": None, "equal_exchanged": None, "fields": None,
                            "note": f"points held {len(p)}; record W svpt/ace/df/won {cw}, L {cl}; Stage 0 W svpt {sw['svpt']}, ace {sw['ace']}, "
                                    f"df {sw['df']}, won {pts_w_rec}; L svpt {sl['svpt']}, ace {sl['ace']}, df {sl['df']}, won {pts_l_rec}; "
                                    f"abs diff svpt+ace+df as recorded {d_rec}, exchanged {d_exc}"})

    # ---- MCP
    for g, tour in (("m", "atp"), ("w", "wta")):
        mc = K.mcp(g)
        for r in x[x["tour"].eq(tour)].itertuples():
            kw, kl = K.name_key(r.winner_name), K.name_key(r.loser_name)
            c = mc[(mc["pk"] == kw) & (mc["ok"] == kl) & (mc["date"] - r.tournament_date).dt.days.between(-10, 16)]
            if c.empty:
                continue
            w = c.iloc[0]
            l_ = mc[(mc["match_id"] == w["match_id"]) & (mc["pk"] == kl)].iloc[0]
            sw, sl = stage0_boxes(r)
            m_w = {"svpt": w["serve_pts"], "ace": w["aces"], "df": w["dfs"], "first_in": w["first_in"], "first_won": w["first_won"],
                   "second_won": w["second_won"]}
            m_l = {"svpt": l_["serve_pts"], "ace": l_["aces"], "df": l_["dfs"], "first_in": l_["first_in"], "first_won": l_["first_won"],
                   "second_won": l_["second_won"]}
            rec, exc, n = compare(sw, sl, m_w, m_l)
            d_rec = sum(abs(sw[f] - m_w[f]) + abs(sl[f] - m_l[f]) for f in m_w)
            d_exc = sum(abs(sw[f] - m_l[f]) + abs(sl[f] - m_w[f]) for f in m_w)
            records.append({"match_id": r.match_id, "source": "mcp", "record": w["match_id"], "record_winner_is_stage0_winner": None,
                            "equal_as_recorded": rec, "equal_exchanged": exc, "fields": n,
                            "note": f"abs diff over 6 counts: as recorded {d_rec}, exchanged {d_exc}"})

    rec = pd.DataFrame(records)
    rec.to_csv(K.OUT / "f2_records.csv", index=False)
    pd.set_option("display.width", 400)
    pd.set_option("display.max_colwidth", 220)
    print(rec.drop(columns=["record_result"], errors="ignore").to_string())

    # ---- verdicts
    if "score_flag" not in x:
        m = pd.read_parquet(K.S0 / "stage0_matches.parquet", columns=["match_id", "score_flag"])
        x = x.merge(m, on="match_id", how="left")
    sw0 = pd.read_csv(K.AUDIT / "box_swapped_oct07.csv")[["match_id", "edition"]]
    x = x.merge(sw0, on="match_id", how="left")
    out = []
    for r in x.itertuples():
        rr = rec[rec["match_id"].eq(r.match_id)]
        sup, ref, notes = [], [], []      # strong record for the exchange / any record for "as recorded" / conflicts
        for _, q in rr.iterrows():
            if q["source"] == "sirgenkii_keystats":
                tag = "exchanged" if q["equal_exchanged"] > q["equal_as_recorded"] else "as recorded"
                (sup if tag == "exchanged" else ref).append(f"{q['source']} {q['record']} (ATP key statistics): "
                                                            f"equal as recorded {q['equal_as_recorded']:g}/4, exchanged {q['equal_exchanged']:g}/4; {q['note']}")
                continue
            if q["source"] == "infosys_ao2025_points":
                d = re.search(r"as recorded (\d+\.?\d*), exchanged (\d+\.?\d*)", q["note"])
                dr, de = float(d.group(1)), float(d.group(2))
                (sup if de < dr else ref).append(f"{q['source']} {q['record']}: |diff| svpt+ace+df as recorded {dr:g}, exchanged {de:g}")
                continue
            if pd.isna(q["fields"]) or q["fields"] == 0:
                continue
            txt = f"{q['source']} {q['record']}: equal as recorded {q['equal_as_recorded']:g}/{q['fields']:g}, exchanged {q['equal_exchanged']:g}/{q['fields']:g}"
            if q.get("record_winner_is_stage0_winner") is False:
                notes.append(f"{q['source']} names the other winner")
            if q["equal_exchanged"] >= q["fields"] - 4 and q["equal_exchanged"] > q["equal_as_recorded"] + 4:
                sup.append(txt)
            elif q["equal_as_recorded"] > q["equal_exchanged"]:
                ref.append(txt)
            # otherwise: weak or no direction (SofaScore's own conventions, the WTA API's Slam rows); never decides alone
        big_k = abs(r.k) >= 4
        prog_ok = r.progression in ("winner advanced", "winner in main draw") or (
            r.progression == "both in main draw" and "winner entry Q" in str(r.progression_note))
        margin_ok = r.margin >= 4 and r.winner_pts < r.loser_pts
        reversed_score = str(r.score_flag) == "read_reversed"
        if sup and not ref and not notes:
            verdict, why = "confirm", "independent record holds the exchanged box: " + "; ".join(sup)
        elif ref:
            verdict, why = "reject", "independent record agrees with Stage 0 as recorded (exchanged fit is a coincidence): " + "; ".join(ref)
        elif sup and notes:
            verdict, why = "reject", "record conflict: " + "; ".join(sup + notes)
        elif reversed_score:
            verdict, why = ("reject", f"score written from the recorded winner's losing side ({r.score}, read reversed by Stage 0) and "
                            "the box fits that reading: the winner label, not the box, may be wrong; no record of who won")
        elif big_k and prog_ok and margin_ok:
            verdict, why = ("confirm", f"internal only: exchanged identity exact with |k|={abs(r.k):g} (other-error rate at this k <0.6%), "
                            f"recorded winner advanced ({r.progression}), as recorded the winner of a {r.winner_games:g}-{r.loser_games:g} "
                            f"games match wins fewer points ({r.winner_pts:g}-{r.loser_pts:g}; <0.2% of clean matches at margin >=4)")
        else:
            verdict, why = ("reject", f"no independent record; |k|={abs(r.k):g}, games {r.winner_games:g}-{r.loser_games:g}: an exchanged fit "
                            f"by coincidence has probability {r.p_coinc_fit:.2f} per failing match (~28 such coincidences expected "
                            f"outside the two 2021 events), and the points do not discriminate (winner has fewer points in "
                            f"{100 * r.p_wfp_if_box_right:.0f}% of clean matches with this margin)"
                            + ("" if prog_ok or r.progression.startswith("no next") or r.progression == "final" else f"; progression: {r.progression}"))
        out.append({"match_id": r.match_id, "edition": r.edition if hasattr(r, "edition") else None, "round": r.round,
                    "score": r.score, "winner": r.winner_name, "loser": r.loser_name, "k": r.k, "winner_games": r.winner_games,
                    "loser_games": r.loser_games, "winner_pts_as_recorded": r.winner_pts, "loser_pts_as_recorded": r.loser_pts,
                    "progression": r.progression, "score_flag": r.score_flag, "source_file": r.source_file,
                    "source_row": r.source_row, "verdict": verdict, "reason": why})
    v = pd.DataFrame(out)
    v.to_csv(K.OUT / "f2_verdicts.csv", index=False)
    print(v["verdict"].value_counts().to_dict())
    print(v[["match_id", "k", "progression", "verdict", "reason"]].to_string())


if __name__ == "__main__":
    main()
