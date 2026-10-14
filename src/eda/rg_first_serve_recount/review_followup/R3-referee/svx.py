"""R3-referee, group SVX: swapped service games at the Australian Open 2025 and Roland Garros 2019-2026.

My own derivation (no code of the lead's is used for any number):
  1. MatchBeats files decrypted (adapter's blocks_of/decrypt): AO 2025 (match-beats route) and RG 2019-2026 (the route
     order of official.mb_doc). Per file: the games in file order with their set and game numbers, their points'
     servers, isTieBreak and isGameComplete; the first point's server.
  2. The first server is PROVEN when all of these hold (stricter than the brief's test): the file's first point is in
     set 1, game 1; set numbers run 1, 2, ... and game numbers run 1, 2, ... inside each set with no gap; every
     non-tiebreak game has one server for all its points; and in file order every game's server (a tiebreak's first
     point) is the one the alternation names, starting from the first server.
  3. Links: RG files through my round-2 link (official_rows.csv); AO 2025 files placed here on Sackmann's AO 2025 rows
     by tour, draw, round (the adapter's round lookup) and both names, either orientation.
  4. The truth: each player's service games from the row's score and the proven first server (the alternation of
     addendum.alternation: game slots alternate, a tiebreak set's last game is a slot without a service game, a match
     tiebreak is one slot; a retirement's score holds only finished games). Walkovers are not classed.
  5. Classes: unproven (no proven first server), incomplete (a count missing), equal, swapped (the row's two counts
     are the truth's two exchanged, and the truth's two differ), other. Where MatchBeats holds the whole match, its
     own count of completed non-tiebreak games is set beside the truth.
  6. Compared with the lead's matches.csv and proposed_swaps.csv.
Writes svx_rows.csv and svx_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx.py
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import official as OF  # noqa: E402
import r3f as F  # noqa: E402
from addendum import alternation  # noqa: E402

from src.ingest.point_sources import infosys_slams as I  # noqa: E402

SVC = F.FOLLOW / "service_games"


def parse_mb(doc: dict) -> dict:
    """The file's game sequence, the proof of the first server, and the completed non-tiebreak games per slot."""
    games = []
    for s in doc.get("setData") or []:
        for g in s.get("gameData") or []:
            pts = g.get("pointData") or []
            games.append({"set": s.get("set"), "game": g.get("game"), "tb": bool(g.get("isTieBreak")),
                          "done": g.get("isGameComplete") is not False, "servers": [str(p.get("server")) for p in pts]})
    games = [g for g in games if g["servers"]]
    pdat = doc.get("playerData") or {}
    out = {"p1_name": f"{pdat.get('tm1Ply1FirstName') or ''} {pdat.get('tm1Ply1LastName') or ''}".strip(),
           "p2_name": f"{pdat.get('tm2Ply1FirstName') or ''} {pdat.get('tm2Ply1LastName') or ''}".strip(),
           "mb_status": doc.get("matchStatus"), "complete_flag": doc.get("isMatchComplete"), "games_in_file": len(games),
           "points": sum(len(g["servers"]) for g in games)}
    if not games:
        out.update({"first": None, "proven": False, "why": "no points"})
        return out
    first = games[0]["servers"][0]
    why = []
    if not (str(games[0]["set"]) == "1" and str(games[0]["game"]) == "1"):
        why.append("first point not set 1 game 1")
    prev_set, prev_game = None, None
    expected = first
    for g in games:
        st, gm = int(g["set"]), int(g["game"])
        if prev_set is None:
            pass
        elif st == prev_set and gm != prev_game + 1:
            why.append(f"game gap {st}:{prev_game}->{gm}")
        elif st != prev_set and not (st == prev_set + 1 and gm == 1):
            why.append(f"set gap {prev_set}->{st}:{gm}")
        tb = g["tb"] or len(set(g["servers"])) > 1
        if not tb and len(set(g["servers"])) != 1:
            why.append(f"mixed servers {st}:{gm}")
        turn = g["servers"][0]
        if turn != expected:
            why.append(f"alternation {st}:{gm}")
        expected = "2" if expected == "1" else "1"
        prev_set, prev_game = st, gm
        g["is_tb"] = tb
    out.update({"first": first, "proven": not why, "why": "; ".join(why[:3])})
    for k in ("1", "2"):
        out[f"p{k}_done_regular"] = sum(1 for g in games if g["done"] and not g["is_tb"] and g["servers"][0] == k)
        out[f"p{k}_svpt"] = sum(g["servers"].count(k) for g in games)
    out["unfinished"] = sum(not g["done"] for g in games)
    return out


def ao_files() -> pd.DataFrame:
    rounds = I.round_lookup()
    rows = []
    for f in sorted((F.RAW / "infosys_slams" / "AO" / "2025" / "match-beats").glob("*.json.gz")):
        code = f.name.split(".")[0]
        blocks = I.blocks_of("match-beats", json.load(gzip.open(f)))
        if "mbData" not in blocks:
            continue
        doc = I.decrypt(blocks["mbData"])
        if not isinstance(doc, dict) or not doc.get("setData"):
            continue
        rows.append({"event": "AO", "year": 2025, "code": code, "round": rounds.get(("AO", code)),
                     "tour": "wta" if code.startswith("W") else "atp", "draw": "qual" if code[1] == "Q" else "main",
                     **parse_mb(doc)})
    return pd.DataFrame(rows)


def link_ao(raw: pd.DataFrame, files: pd.DataFrame) -> pd.DataFrame:
    groups = {k: g for k, g in files.groupby(["tour", "draw", "round"])}
    out = []
    for r in raw.itertuples():
        draw = "qual" if r.qualifying else "main"
        cand = groups.get((r.tour, draw, r.round))
        best = []
        if cand is not None:
            for x in cand.itertuples():
                for w_slot in ("1", "2"):
                    l_slot = "2" if w_slot == "1" else "1"
                    a = F.name_ok(getattr(x, f"p{w_slot}_name"), r.winner_name)
                    b = F.name_ok(getattr(x, f"p{l_slot}_name"), r.loser_name)
                    if min(a, b) >= 1:
                        best.append(((min(a, b), a + b), x.code, w_slot))
        best.sort(key=lambda z: z[0], reverse=True)
        tie = len(best) > 1 and best[0][0] == best[1][0] and best[0][1] != best[1][1]
        out.append({"key": r.key, "mb_code": best[0][1] if best and not tie else None,
                    "w_slot": best[0][2] if best and not tie else None,
                    "link_min": best[0][0][0] if best else None, "link_tie": tie})
    return pd.DataFrame(out)


def main() -> int:
    raw = pd.read_parquet(F.OUT / "sub_raw.parquet")
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("int64")
    raw["season"] = pd.to_numeric(raw["season"]).astype("int64")
    raw["key"] = F.rowkey(raw["_source_file"], raw["_row"])
    s0 = pd.read_parquet(F.S0 / "stage0_matches.parquet", columns=["match_id", "source_file", "source_row", "status",
                                                                  "status_detail", "tournament_name", "year"])
    s0["key"] = F.rowkey(s0["source_file"], s0["source_row"])
    s0 = s0.drop_duplicates("key").set_index("key")
    # ---------------------------------------------------------------- AO 2025
    files = ao_files()
    ao = raw[raw["source"].eq("sackmann") & raw["tourney_name"].eq("Australian Open") & raw["season"].eq(2025)].copy()
    la = link_ao(ao, files)
    ao = ao.merge(la, on="key", how="left").merge(files.drop(columns=["round", "tour", "draw", "event", "year"]).rename(columns={"code": "mb_code"}), on="mb_code", how="left")
    ao["event"] = "AO"
    # ---------------------------------------------------------------- RG 2019-2026 (my round-2 link)
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    o = o[o["code"].notna() & o["source"].eq("sackmann")].copy()
    o["key"] = F.rowkey(o["source_file"], o["source_row"])
    rec = []
    for r in o.itertuples():
        route, doc = OF.mb_doc(int(r.season), r.code)
        if doc is None:
            continue
        p = parse_mb(doc)
        ws = None
        if p.get("p1_name"):
            s1 = (F.name_ok(p["p1_name"], r.winner_name), F.name_ok(p["p1_name"], r.loser_name))
            ws = "1" if s1[0] > s1[1] else "2" if s1[1] > s1[0] else None
        rec.append({"key": r.key, "mb_code": r.code, "w_slot": ws, "route": route, **p})
    rgm = pd.DataFrame(rec)
    rg = raw[raw["key"].isin(set(rgm["key"]))].merge(rgm, on="key", how="left")
    rg["event"] = "RG"
    d = pd.concat([ao, rg], ignore_index=True)
    d = d[d["mb_code"].notna()].copy()
    # ---------------------------------------------------------------- truth and classes
    num = lambda s: pd.to_numeric(s.astype("object").where(s.notna(), "").astype(str).str.strip().replace("", np.nan),
                                  errors="coerce")
    d["row_w"], d["row_l"] = num(d["w_SvGms"]), num(d["l_SvGms"])
    d["svpt_w_row"], d["svpt_l_row"] = num(d["w_svpt"]), num(d["l_svpt"])
    d["status_s0"] = d["key"].map(s0["status"])
    d["status_detail_s0"] = d["key"].map(s0["status_detail"])
    d["first_side"] = np.where(d["first"].isna() | d["w_slot"].isna(), None,
                               np.where(d["first"].astype(str) == d["w_slot"].astype(str), "w", "l"))
    tw, tl = [], []
    for sc, fs, st in zip(d["score"], d["first_side"], d["status_s0"]):
        if fs is None or st == "walkover":
            tw.append(np.nan)
            tl.append(np.nan)
            continue
        a, b = alternation(sc, fs == "w")
        tw.append(a)
        tl.append(b)
    d["true_w"], d["true_l"] = tw, tl
    for s, k in (("w", "w_slot"), ("l", None)):
        pass
    d["mb_w"] = [r[f"p{r['w_slot']}_done_regular"] if isinstance(r["w_slot"], str) else np.nan for _, r in d.iterrows()]
    d["mb_l"] = [r[f"p{'2' if r['w_slot'] == '1' else '1'}_done_regular"] if isinstance(r["w_slot"], str) else np.nan
                 for _, r in d.iterrows()]
    d["mb_svpt_w"] = [r[f"p{r['w_slot']}_svpt"] if isinstance(r["w_slot"], str) else np.nan for _, r in d.iterrows()]
    d["mb_svpt_l"] = [r[f"p{'2' if r['w_slot'] == '1' else '1'}_svpt"] if isinstance(r["w_slot"], str) else np.nan
                      for _, r in d.iterrows()]
    d["mb_whole"] = d["mb_svpt_w"].eq(d["svpt_w_row"]) & d["mb_svpt_l"].eq(d["svpt_l_row"]) & d["unfinished"].le(1)

    def cls(r) -> str:
        if r["status_s0"] == "walkover":
            return "walkover"
        if not bool(r["proven"]) or r["first_side"] is None:
            return "unproven"
        if any(pd.isna(r[c]) for c in ("row_w", "row_l", "true_w", "true_l")):
            return "incomplete"
        if r["row_w"] == r["true_w"] and r["row_l"] == r["true_l"]:
            return "equal"
        if r["true_w"] != r["true_l"] and r["row_w"] == r["true_l"] and r["row_l"] == r["true_w"]:
            return "swapped"
        return "other"
    d["my_cls"] = d.apply(cls, axis=1)
    d["as_if_winner_first"] = [alternation(sc, True) for sc in d["score"]]
    d["row_as_if_winner_first"] = [(rw, rl) == aw for rw, rl, aw in zip(d["row_w"], d["row_l"], d["as_if_winner_first"])]
    # ---------------------------------------------------------------- the lead's tables
    lm = pd.read_csv(SVC / "matches.csv", low_memory=False)
    lm["key"] = F.rowkey(lm["source_file"], lm["source_row"])
    lead_cls = lm.drop_duplicates("key").set_index("key")["cls"]
    ps = pd.read_csv(SVC / "proposed_swaps.csv", dtype=str, keep_default_na=False)
    ps["key"] = F.rowkey(ps["source_file"], ps["source_row"])
    d["lead_cls"] = d["key"].map(lead_cls)
    d["lead_proposed"] = d["key"].isin(set(ps["key"]))
    d["match_id"] = d["key"].map(s0["match_id"])
    keep = ["event", "season", "tour", "round", "qualifying", "key", "match_id", "_source_file", "_row", "winner_name",
            "loser_name", "score", "status_s0", "status_detail_s0", "mb_code", "route", "link_min", "w_slot", "first",
            "first_side", "proven", "why", "row_w", "row_l", "true_w", "true_l", "mb_w", "mb_l", "mb_whole",
            "unfinished", "my_cls", "row_as_if_winner_first", "lead_cls", "lead_proposed"]
    d[keep].to_csv(F.OUT / "svx_rows.csv", index=False)
    smry = {
        "files_ao2025": int(len(files)), "ao2025_rows": int(len(ao)), "ao2025_linked": int(ao["mb_code"].notna().sum()),
        "ao2025_link_ties": int(ao["link_tie"].sum()) if "link_tie" in ao else None,
        "rg_rows_with_a_file": int(len(rg)),
        "classes_by_event_year": d.groupby(["event", "season", "my_cls"]).size().rename("matches").reset_index()
        .to_dict("records"),
        "my_class_vs_lead": pd.crosstab(d["my_cls"], d["lead_cls"].fillna("(absent)")).to_dict(),
        "lead_proposed": int(len(ps)), "lead_proposed_found_here": int(d["lead_proposed"].sum()),
        "lead_proposed_my_class": d.loc[d["lead_proposed"], "my_cls"].value_counts().to_dict(),
        "my_swapped_not_proposed": d.loc[d["my_cls"].eq("swapped") & ~d["lead_proposed"],
                                         ["event", "season", "match_id", "winner_name", "loser_name"]].to_dict("records"),
        "swapped_row_as_if_winner_first": int((d["my_cls"].eq("swapped") & d["row_as_if_winner_first"]).sum()),
        "swapped_mb_whole_equals_truth": int((d["my_cls"].eq("swapped") & d["mb_whole"]
                                              & d["mb_w"].eq(d["true_w"]) & d["mb_l"].eq(d["true_l"])).sum()),
        "swapped_mb_whole": int((d["my_cls"].eq("swapped") & d["mb_whole"]).sum()),
        "unproven_reasons": d.loc[d["my_cls"].eq("unproven"), "why"].value_counts().head(20).to_dict(),
    }
    (F.OUT / "svx_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
