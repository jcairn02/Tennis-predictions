"""R3-referee, step 6: light, independent checks of claims C1 and C3 with this reviewer's own links.

C1  the MatchBeats recount is exact where the truth is known: the AO 2025 MatchBeats files (decrypted with the adapter's
    decrypt and blocks_of) recounted per player and placed on Stage 0's AO 2025 player rows by the code's round, the
    tour and both names; where the point file holds every serve point Stage 0 counts, do first serves in and points
    won on each serve agree?
C3  in the editions before the fault, RG's own statistics (parsed here from the raw API files) equal Sackmann's raw
    rows on all eight counts: RG 2019-2021 matches placed on the raw rows by round, tour and both names.

Writes claims_check.json. Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/claims_check.py
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3common as C  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402

OUT = C.OUT


def place(cands: pd.DataFrame, n1: str, n2: str):
    """The unique candidate row (winner_name / loser_name) whose two names match n1, n2 in either order; returns
    (row, n1_is_winner) or None."""
    hits = []
    for x in cands.itertuples():
        for n1w in (True, False):
            a = C.name_ok(n1, x.winner_name if n1w else x.loser_name)
            b = C.name_ok(n2, x.loser_name if n1w else x.winner_name)
            if min(a, b) >= 1:
                hits.append(((min(a, b), a + b), x, n1w))
    if not hits:
        return None
    hits.sort(key=lambda z: z[0], reverse=True)
    if len(hits) > 1 and hits[0][0] == hits[1][0] and hits[0][1].Index != hits[1][1].Index:
        return None
    return hits[0][1], hits[0][2]


def c1() -> dict:
    m = pd.read_parquet(C.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet")
    p = pd.read_parquet(C.ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_match_players.parquet")
    m = m[m["tournament_name"].eq("Australian Open") & m["year"].eq(2025)]
    p = p[p["match_id"].isin(set(m["match_id"]))]
    a = p[p["side"].eq("A")].set_index("match_id")
    b = p[p["side"].eq("B")].set_index("match_id")
    mm = m.set_index("match_id")[["tour", "round", "has_box"]].copy()
    mm["winner_name"] = a["player_name"].reindex(mm.index)       # A / B as the two names (order irrelevant here)
    mm["loser_name"] = b["player_name"].reindex(mm.index)
    groups = {k: g for k, g in mm.groupby(["tour", "round"])}
    rounds = I.round_lookup()
    rows = []
    for f in sorted((C.RAW / "infosys_slams" / "AO" / "2025" / "match-beats").glob("*.json.gz")):
        code = f.name.split(".")[0]
        rnd = rounds.get(("AO", code))
        tour = "wta" if code[0] == "W" else "atp"
        blocks = I.blocks_of("match-beats", json.load(gzip.open(f)))
        if "mbData" not in blocks:
            continue
        doc = I.decrypt(blocks["mbData"])
        if not isinstance(doc, dict) or not doc.get("setData"):
            continue
        pts = [q for s in doc["setData"] for g in (s.get("gameData") or []) for q in (g.get("pointData") or [])]
        pdat = doc.get("playerData") or {}
        names = {k: f"{pdat.get(f'tm{k}Ply1FirstName') or ''} {pdat.get(f'tm{k}Ply1LastName') or ''}" for k in ("1", "2")}
        cand = groups.get((tour, rnd))
        if cand is None:
            continue
        hit = place(cand, names["1"], names["2"])
        if hit is None:
            continue
        x, one_is_a = hit
        for k in ("1", "2"):
            mine = [q for q in pts if str(q.get("server")) == k]
            is_a = (k == "1") == one_is_a
            s0 = p[(p["match_id"].eq(x.Index)) & (p["side"].eq("A" if is_a else "B"))].iloc[0]
            rows.append({"code": code, "match_id": x.Index, "has_box": bool(s0["has_box"]),
                         "mb_svpt": len(mine), "mb_first_in": sum(str(q.get("serve")) == "1" for q in mine),
                         "mb_first_won": sum(str(q.get("serve")) == "1" and str(q.get("scorer")) == k for q in mine),
                         "mb_second_won": sum(str(q.get("serve")) == "2" and str(q.get("scorer")) == k for q in mine),
                         "s0_svpt": s0["svpt"], "s0_first_in": s0["first_in"], "s0_first_won": s0["first_won"],
                         "s0_second_won": s0["second_won"]})
    d = pd.DataFrame(rows)
    d = d[d["has_box"]]
    comp = d[d["mb_svpt"].eq(d["s0_svpt"])]
    return {"ao2025_player_rows_placed_with_box": int(len(d)), "complete_rows": int(len(comp)),
            **{f"{c}_equal_on_complete": int(comp[f"mb_{c}"].eq(comp[f"s0_{c}"]).sum())
               for c in ("first_in", "first_won", "second_won")},
            "all_three_equal_on_complete": int(np.all([comp[f"mb_{c}"].eq(comp[f"s0_{c}"]) for c in
                                                       ("first_in", "first_won", "second_won")], axis=0).sum())}


def c3() -> dict:
    api = C.rg_api_all()
    api = api[api["year"].between(2019, 2021) & api["svpt"].notna()]
    raw = C.raw_subset()
    raw = raw[raw["tourney_name"].eq("Roland Garros") & pd.to_numeric(raw["season"]).between(2019, 2021)]
    raw = raw.rename(columns={"_source_file": "sfile", "_row": "srow"})
    groups = {k: g for k, g in raw.groupby(["season", "tour", "round"])}
    rounds = I.round_lookup()
    out = []
    for (year, code), g in api.groupby(["year", "code"]):
        if len(g) != 2:
            continue
        tour = "wta" if code[1] == "D" else "atp"
        cand = groups.get((year, tour, rounds.get(("RG", code))))
        if cand is None:
            continue
        A, B = g.iloc[0], g.iloc[1]
        hit = place(cand, A["name"], B["name"])
        if hit is None:
            out.append({"year": year, "code": code, "placed": False})
            continue
        x, a_is_w = hit
        for t, side in ((A, "w" if a_is_w else "l"), (B, "l" if a_is_w else "w")):
            rec = {"year": year, "code": code, "placed": True, "side": side, "winner_flag_ok": bool(t["winner"]) == (side == "w")}
            eq = []
            for k, c in (("ace", "ace"), ("df", "df"), ("svpt", "svpt"), ("first_in", "1stIn"), ("first_won", "1stWon"),
                         ("second_won", "2ndWon"), ("bp_faced", "bpFaced"), ("bp_saved", "bpSaved")):
                v = getattr(x, f"{side}_{c}")
                v = float(v) if v not in (None, "") else np.nan
                eq.append(v == float(t[k]) if t[k] is not None else False)
            rec["all_eight_equal"] = bool(all(eq))
            out.append(rec)
    d = pd.DataFrame(out)
    pl = d[d["placed"]]
    return {"rg_2019_2021_matches_with_statistics": int(api.groupby(["year", "code"]).ngroups),
            "player_rows_placed": int(len(pl)), "matches_not_placed": int((~d["placed"]).sum()),
            "all_eight_equal": int(pl["all_eight_equal"].sum()),
            "winner_flag_agrees": int(pl["winner_flag_ok"].sum()),
            "not_equal_by_year": pl[~pl["all_eight_equal"]].groupby("year").size().to_dict()}


def main() -> int:
    res = {"C1_AO2025_matchbeats_vs_stage0": c1(), "C3_rg_statistics_vs_sackmann_2019_2021": c3()}
    (OUT / "claims_check.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
