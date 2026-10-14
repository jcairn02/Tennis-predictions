"""F3 review (A2-skeptic): WTA Adelaide 2 2022 carries Adelaide 2021's box scores.

  1. Every Adelaide 2 2022 match in Stage 0 (with or without a box): is its raw box (all 18 counts, either
     orientation) equal to an Adelaide 2021 raw box; which one; does the box fit the 2022 score (games identity,
     points per game) and the 2021 score it is copied from.
  2. The WTA API: does it hold Adelaide 2021 (id 2014) with Sackmann's 2021 counts (so the 2021 boxes are genuine),
     and Adelaide 2 2022 (id 2030) with other counts; do the API's 2022 counts fit the 2022 scores and pass Stage 0's
     checks (B0-B9).
  3. F3b: does the WTA API measure what Sackmann measures? Exact equality per count and per player row on every
     WTA 2021-2022 match both hold, leaving out Abu Dhabi 2021, Phillip Island 2021 and Adelaide 2 2022.
Writes data/studies/input_data_audit/fixes/A2-skeptic/f3_*.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f3_adelaide.py
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd

import _common as K

C9 = K.BOX


def toks(s) -> frozenset:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return frozenset(t for t in re.findall(r"[a-z]+", s) if len(t) >= 3)


def surname(s) -> str:
    t = re.findall(r"[a-z]+", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return t[-1] if t else ""


def checks(w: dict, l_: dict, games_w: float, games_l: float, completed: bool, std_tb: int) -> dict:
    """Stage 0's B0-B9 on a pair of boxes under a score, plus the games identity (no tiebreak, completed)."""
    out = {}
    fails = []
    for tag, f in (("w", w), ("l", l_)):
        if any(pd.isna(f[c]) for c in C9 if c != "sv_gms"):
            return {"b_checks": "incomplete"}
        if any(f[c] < 0 for c in C9 if pd.notna(f[c])):
            fails.append(f"B0{tag}")
        if f["first_in"] > f["svpt"]:
            fails.append(f"B1{tag}")
        if f["first_won"] > f["first_in"]:
            fails.append(f"B2{tag}")
        if f["second_won"] > f["svpt"] - f["first_in"]:
            fails.append(f"B3{tag}")
        if f["bp_saved"] > f["bp_faced"]:
            fails.append(f"B4{tag}")
        if f["df"] > f["svpt"] - f["first_in"]:
            fails.append(f"B6{tag}")
        if f["ace"] > f["first_won"] + f["second_won"]:
            fails.append(f"B7{tag}")
        if pd.notna(f["sv_gms"]) and (f["bp_faced"] - f["bp_saved"]) > f["sv_gms"]:
            fails.append(f"B8{tag}")
    games = games_w + games_l
    sv = w["sv_gms"] + l_["sv_gms"]
    if pd.notna(sv) and abs(sv - (games - std_tb)) > 1 and abs(sv - games) > 1:
        fails.append("B5")
    played = (games - std_tb) - (0 if completed else 1)
    if w["svpt"] + l_["svpt"] < 4.5 * played:
        fails.append("B9")
    out["b_checks"] = ",".join(fails) if fails else "pass"
    if completed and std_tb == 0 and pd.notna(sv):
        bw, bl = w["bp_faced"] - w["bp_saved"], l_["bp_faced"] - l_["bp_saved"]
        out["identity_w"] = bool(w["sv_gms"] - bw + bl == games_w)
        out["identity_exchanged"] = bool(l_["sv_gms"] - bl + bw == games_w)
    out["pts_per_game"] = round((w["svpt"] + l_["svpt"]) / games, 2) if games else None
    return out


def score_games(score: str) -> tuple[int, int, int, bool]:
    gw = gl = tb = 0
    for a, b, t in re.findall(r"(\d+)-(\d+)(\(\d+\))?", str(score)):
        a, b = int(a), int(b)
        gw, gl = gw + a, gl + b
        if (max(a, b) == 7 and min(a, b) == 6) or t:
            tb += 1
    done = not re.search(r"RET|W/O|DEF|ABD", str(score), re.I)
    return gw, gl, tb, done


def raw_box(row, side: str) -> dict:
    return {c: row[f"{side}_{K.RAW[c]}"] for c in C9}


def main() -> None:
    pd.set_option("display.width", 300)
    pd.set_option("display.max_colwidth", 80)
    raw = K.sackmann("wta", "*202[12]")
    raw["tid"] = raw["tourney_id"].astype(str)
    a21 = raw[raw["tid"].eq("2021-2030")].copy()
    a22 = raw[raw["tid"].eq("2022-2030")].copy()
    print("raw rows: Adelaide 2021", len(a21), "Adelaide 2 2022", len(a22))

    def key(r, first, second):
        return tuple(r[f"{first}_{K.RAW[c]}"] for c in C9) + tuple(r[f"{second}_{K.RAW[c]}"] for c in C9)

    idx21 = {}
    for _, r in a21.iterrows():
        idx21[key(r, "w", "l")] = (r, "same orientation")
        idx21[key(r, "l", "w")] = (r, "exchanged orientation")

    api = K.wta_api([2021, 2022])
    api["ta"], api["tb"] = api["name_a"].map(toks), api["name_b"].map(toks)
    api21 = api[api["tournament_id"].astype(str).eq("2014") & api["year"].astype(str).eq("2021")]
    api22 = api[api["tournament_id"].astype(str).eq("2030") & api["year"].astype(str).eq("2022")]
    print("API rows: Adelaide 2021 (2014)", len(api21), "Adelaide 2 2022 (2030)", len(api22))

    def api_find(frame, wn, ln):
        """Best API row by shared name tokens (both players must share at least one; Riske Amritraj = Riske,
        Hunter = Storm Sanders by first name)."""
        tw, tl = toks(wn), toks(ln)
        best, best_score, best_ws = None, 0, None
        for _, h in frame.iterrows():
            for ws, a, b in (("a", h["ta"], h["tb"]), ("b", h["tb"], h["ta"])):
                s1, s2 = len(tw & a), len(tl & b)
                if s1 >= 1 and s2 >= 1 and s1 + s2 > best_score:
                    best, best_score, best_ws = h, s1 + s2, ws
        if best is None:
            return None, None, None
        return best, best_ws, ("b" if best_ws == "a" else "a")

    # ---- 2021 boxes against the API (genuine?)
    g21 = []
    for _, r in a21.iterrows():
        h, ws, ls = api_find(api21, r["winner_name"], r["loser_name"])
        if h is None:
            g21.append({"match": f"{r['winner_name']} d. {r['loser_name']} {r['score']}", "api": "not found"})
            continue
        eq = sum(float(r[f"w_{K.RAW[c]}"]) == float(h[f"{ws}_{c}"]) for c in C9 if pd.notna(r[f"w_{K.RAW[c]}"])) + \
            sum(float(r[f"l_{K.RAW[c]}"]) == float(h[f"{ls}_{c}"]) for c in C9 if pd.notna(r[f"l_{K.RAW[c]}"]))
        n = sum(pd.notna(r[f"w_{K.RAW[c]}"]) for c in C9) * 2
        g21.append({"match": f"{r['winner_name']} d. {r['loser_name']} {r['score']}", "api": h["key"], "equal": eq, "of": n})
    g21 = pd.DataFrame(g21)
    g21.to_csv(K.OUT / "f3_adelaide2021_vs_api.csv", index=False)
    print("Adelaide 2021: Sackmann vs API (2014):", int(g21["api"].eq("not found").sum()), "of", len(g21), "not found in the API")

    # ---- each Adelaide 2 2022 match
    s0 = pd.read_parquet(K.S0 / "stage0_matches.parquet")
    s0 = s0[s0["tournament_id"].eq("2022-2030")]
    p0 = pd.read_parquet(K.S0 / "stage0_match_players.parquet")
    rows = []
    for _, r in a22.iterrows():
        k = key(r, "w", "l")
        has_counts = not all(pd.isna(v) for v in k)
        src, orient = idx21.get(k, (None, None))
        gw, gl, tb, done = score_games(r["score"])
        wbox, lbox = raw_box(r, "w"), raw_box(r, "l")
        ck = checks(wbox, lbox, gw, gl, done and gw + gl > 0, tb) if has_counts else {}
        rec = {"source_file": r["_source_file"], "source_row": r["_row"], "round": r["round"], "match_num": r["match_num"],
               "match": f"{r['winner_name']} d. {r['loser_name']} {r['score']}", "has_counts": has_counts,
               "copy_of_2021": (f"{src['winner_name']} d. {src['loser_name']} {src['score']} [{src['round']}, match_num {src['match_num']}]"
                                if src is not None else None),
               "copy_orientation": orient, "raw_checks_on_2022_score": ck.get("b_checks"),
               "raw_identity_2022": ck.get("identity_w"), "raw_identity_2022_exchanged": ck.get("identity_exchanged"),
               "raw_pts_per_game_2022": ck.get("pts_per_game")}
        if src is not None:
            sgw, sgl, stb, sdone = score_games(src["score"])
            # in the copy's own orientation: the 2021 winner's box
            ck21 = checks(raw_box(src, "w"), raw_box(src, "l"), sgw, sgl, sdone and sgw + sgl > 0, stb)
            rec.update({"box_checks_on_2021_score": ck21.get("b_checks"), "identity_2021": ck21.get("identity_w"),
                        "pts_per_game_2021": ck21.get("pts_per_game")})
        # Stage 0
        sm = s0[(s0["source_file"] == r["_source_file"]) & (s0["source_row"] == r["_row"])]
        if len(sm) == 1:
            rec.update({"match_id": sm.iloc[0]["match_id"], "stage0_has_box": bool(sm.iloc[0]["has_box"]),
                        "stage0_box_status": sm.iloc[0]["box_status"], "stage0_status": sm.iloc[0]["status"]})
            pr = p0[p0["match_id"].eq(sm.iloc[0]["match_id"])]
            rec["player_ids"] = ";".join(pr["player_id"])
        # API
        h, ws, ls = api_find(api22, r["winner_name"], r["loser_name"])
        if h is not None:
            abw = {c: h[f"{ws}_{c}"] for c in C9}
            abl = {c: h[f"{ls}_{c}"] for c in C9}
            apist = h["stats_status"]
            have = not all(pd.isna(v) for v in list(abw.values()) + list(abl.values()))
            rec.update({"api_key": h["key"], "api_result": h["ResultString"], "api_winner_same": h["winner_side"] == ws,
                        "api_has_stats": have, "api_stats_status": apist})
            if have:
                cka = checks(abw, abl, gw, gl, done and gw + gl > 0, tb)
                eqc = sum(float(abw[c]) == float(wbox[c]) for c in C9 if pd.notna(abw[c]) and pd.notna(wbox[c])) + \
                    sum(float(abl[c]) == float(lbox[c]) for c in C9 if pd.notna(abl[c]) and pd.notna(lbox[c]))
                rec.update({"api_checks_on_2022_score": cka.get("b_checks"), "api_identity_2022": cka.get("identity_w"),
                            "api_pts_per_game": cka.get("pts_per_game"), "api_equal_to_sackmann_of18": eqc,
                            **{f"api_w_{c}": abw[c] for c in C9}, **{f"api_l_{c}": abl[c] for c in C9}})
        rows.append(rec)
    t = pd.DataFrame(rows)
    t.to_csv(K.OUT / "f3_adelaide2_2022_matches.csv", index=False)
    show = ["round", "match", "has_counts", "copy_of_2021", "copy_orientation", "raw_checks_on_2022_score", "raw_identity_2022",
            "identity_2021", "stage0_has_box", "stage0_status", "api_has_stats", "api_winner_same",
            "api_checks_on_2022_score", "api_identity_2022", "api_equal_to_sackmann_of18"]
    print(t[[c for c in show if c in t]].to_string())
    print("Stage 0 matches with box:", int(t["stage0_has_box"].sum()), "; copies among them:",
          int((t["stage0_has_box"] & t["copy_of_2021"].notna()).sum()))

    # ---- F3b: WTA API vs Sackmann, WTA 2021-2022, clean events
    d = K.stage0()
    d = d[d["tour"].eq("wta") & d["year"].isin([2021, 2022]) & d["has_box"] & d["source"].eq("sackmann")]
    d = d[~d["tournament_id"].isin(["2021-2028", "2021-2027", "2022-2030"])]
    ed = K._dedup(K.WTA / "editions.parquet")[["tournament_id", "year", "start_date"]]
    ed["start_date"] = pd.to_datetime(ed["start_date"], errors="coerce")
    api = api.merge(ed, on=["tournament_id", "year"], how="left")
    api = api[~(api["tournament_id"].astype(str).isin(["2028", "2027"]) & api["year"].astype(str).eq("2021"))
              & ~(api["tournament_id"].astype(str).eq("2030") & api["year"].astype(str).eq("2022"))]
    api["sa"], api["sb"] = api["name_a"].map(surname), api["name_b"].map(surname)
    by_pair = {}
    for i, rr in api.iterrows():
        by_pair.setdefault((str(rr["year"]), frozenset((rr["sa"], rr["sb"]))), []).append(i)
    rows = []
    a_rows = d[d["side"].eq("A")]
    for r in a_rows.itertuples():
        pk = (str(r.year), frozenset((surname(r.player_name), surname(r.o_player_name))))
        cands = by_pair.get(pk, [])
        cands = [i for i in cands if pd.notna(api.at[i, "start_date"]) and abs((api.at[i, "start_date"] - r.tournament_date).days) <= 10]
        if len(cands) != 1:
            continue
        h = api.loc[cands[0]]
        side_a = "a" if surname(r.player_name) == h["sa"] else "b"
        side_b = "b" if side_a == "a" else "a"
        rec = {"match_id": r.match_id, "level": r.level, "year": r.year, "qualifying": r.qualifying}
        for who, s in (("A", side_a), ("B", side_b)):
            for c in C9:
                mine = getattr(r, c) if who == "A" else getattr(r, f"o_{c}")
                rec[f"{who}_{c}_eq"] = (float(mine) == float(h[f"{s}_{c}"])) if pd.notna(mine) and pd.notna(h[f"{s}_{c}"]) else np.nan
        rows.append(rec)
    j = pd.DataFrame(rows)
    long = []
    for who in ("A", "B"):
        x = j[["match_id", "level", "year", "qualifying"] + [f"{who}_{c}_eq" for c in C9]].copy()
        x.columns = ["match_id", "level", "year", "qualifying"] + C9
        long.append(x)
    long = pd.concat(long, ignore_index=True)
    long["all9"] = long[C9].fillna(False).astype(bool).all(axis=1)
    long["all8_no_svgms"] = long[[c for c in C9 if c != "sv_gms"]].fillna(False).astype(bool).all(axis=1)
    summ = long.groupby(["year", "level"]).agg(player_rows=("all9", "size"), all9_equal=("all9", "mean"),
                                               all8_equal=("all8_no_svgms", "mean"),
                                               **{f"{c}_equal": (c, "mean") for c in C9})
    tot = long.agg({"all9": "mean", "all8_no_svgms": "mean"})
    summ.to_csv(K.OUT / "f3b_api_vs_sackmann_2021_2022.csv")
    print(summ.round(4).to_string())
    print("overall player rows", len(long), "all nine equal", round(float(tot["all9"]), 4), "eight (no sv_gms)",
          round(float(tot["all8_no_svgms"]), 4))
    print("matches joined", len(j), "of", len(a_rows))


if __name__ == "__main__":
    main()
