"""R3-referee, group SVX addendum: the editions fetched later (AO 2018-2024 and 2026, static match-beats route; RG
2013-2015, match-beats-api route). RG 2016-2018 are left aside, as asked.

My own derivation, as svx.py:
  * Stage 0's raw rows (stage0_build.normalise(load_raw()), read once): Sackmann's rows of these editions.
  * The files decrypted and parsed with svx.parse_mb (the stricter proof of the first server, completed non-tiebreak
    games per slot), placed on the rows by tour, draw, round (the adapter's round lookup) and both names.
  * The truth from the row's score and the proven first server (addendum.alternation); classes as in svx.py.
  * Referees naming the server point by point: Court Vision for the AO 2020-2024 main draws (its server ids are the
    MatchBeats files' player ids, so its first server maps onto the file's slots), with a tiebreak counted only where
    both players serve; the hand charts (AO 2018-2026, RG 2013-2015), placed by tour, round and both names.
  * Compared with the lead's addendum_swaps.csv and service_games/matches.csv.
Writes svx_add<tag>_raw.parquet, svx_add<tag>_rows.csv and svx_add<tag>_summary.json into
data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_addendum.py
           [--editions AO2018-2024,AO2026,RG2013-2015] [--tag ""] [--list addendum_swaps.csv]
       (addendum 2: --editions RG2016-2018 --tag 2 --list addendum2_swaps.csv)
"""
from __future__ import annotations

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402
from addendum import alternation  # noqa: E402
from svx import parse_mb  # noqa: E402

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402

EDITIONS = [("AO", y, "match-beats") for y in (2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026)] + \
           [("RG", y, "match-beats-api") for y in (2013, 2014, 2015)]
NAME = {"AO": "Australian Open", "RG": "Roland Garros"}
ROUTE = {"AO": "match-beats", "RG": "match-beats-api"}     # the routes the later fetches used


def editions_of(text: str | None) -> list[tuple[str, int, str]]:
    """'AO2018-2024,AO2026,RG2013-2015' -> [(slam, year, route), ...]; None -> the addendum-1 editions."""
    if not text:
        return EDITIONS
    out = []
    for part in text.upper().split(","):
        slam, years = part.strip()[:2], part.strip()[2:]
        lo, _, hi = years.partition("-")
        out += [(slam, y, ROUTE[slam]) for y in range(int(lo), int(hi or lo) + 1)]
    return out


def files(editions: list[tuple[str, int, str]]) -> pd.DataFrame:
    rounds = I.round_lookup()
    rows = []
    for slam, year, route in editions:
        for f in sorted((F.RAW / "infosys_slams" / slam / str(year) / route).glob("*.json.gz")):
            code = f.name.split(".")[0]
            try:
                blocks = I.blocks_of(route, json.load(gzip.open(f)))
                doc = I.decrypt(blocks["mbData"]) if "mbData" in blocks else None
            except Exception as err:          # recorded, never dropped silently
                rows.append({"event": slam, "year": year, "mb_code": code, "error": str(err)})
                continue
            if not isinstance(doc, dict) or not doc.get("setData"):
                rows.append({"event": slam, "year": year, "mb_code": code, "error": "empty"})
                continue
            fam = code[:2]
            women = fam[0] == "W" if slam == "AO" else fam[1] == "D"
            qual = fam[1] == "Q" if slam == "AO" else fam[0] == "Q"
            pdat = doc.get("playerData") or {}
            rows.append({"event": slam, "year": year, "mb_code": code, "route": route,
                         "round": rounds.get((slam, code)), "tour": "wta" if women else "atp",
                         "draw": "qual" if qual else "main", "p1_id": str(pdat.get("tm1Ply1Id")),
                         "p2_id": str(pdat.get("tm2Ply1Id")), **parse_mb(doc)})
    return pd.DataFrame(rows)


def link(raw: pd.DataFrame, fl: pd.DataFrame) -> pd.DataFrame:
    groups = {k: g for k, g in fl[fl["round"].notna()].groupby(["event", "year", "tour", "draw", "round"])}
    out = []
    for r in raw.itertuples():
        cand = groups.get((r.event, int(r.season), r.tour, "qual" if r.qualifying else "main", r.round))
        best = []
        if cand is not None:
            for x in cand.itertuples():
                for w_slot in ("1", "2"):
                    l_slot = "2" if w_slot == "1" else "1"
                    a = F.name_ok(getattr(x, f"p{w_slot}_name"), r.winner_name)
                    b = F.name_ok(getattr(x, f"p{l_slot}_name"), r.loser_name)
                    if min(a, b) >= 1:
                        best.append(((min(a, b), a + b), x.mb_code, w_slot))
        best.sort(key=lambda z: z[0], reverse=True)
        tie = len(best) > 1 and best[0][0] == best[1][0] and best[0][1] != best[1][1]
        out.append({"key": r.key, "mb_code": best[0][1] if best and not tie else None,
                    "w_slot": best[0][2] if best and not tie else None,
                    "link_min": best[0][0][0] if best else None, "link_tie": tie})
    return pd.DataFrame(out)


def cv_ao(years: set[int]) -> pd.DataFrame:
    rows = []
    for yr in sorted(years & set(range(2020, 2025))):
        f = F.DUMP / "slam_ball_tracking" / "points" / f"AO_{yr}.parquet"
        if not f.exists():
            continue
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "set_num", "game_num", "point_num", "server_id",
                                         "point_end_type"])
        pt = pt[~pt["point_end_type"].eq("Faulty Serve")].drop_duplicates(["match_id", "point_ID"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        for c in ("set_num", "game_num", "point_num"):
            pt[c] = pd.to_numeric(pt[c], errors="coerce")
        for code, g in pt.groupby("code"):
            g = g.sort_values(["set_num", "game_num", "point_num"])
            gm = g.groupby(["set_num", "game_num"], sort=True).agg(
                servers=("server_id", lambda s: tuple(dict.fromkeys(s.astype(str)))),
                first=("server_id", lambda s: str(s.iloc[0]))).reset_index()
            reg = gm[gm["servers"].map(len).eq(1)]
            cnt = reg["first"].value_counts()
            rows.append({"year": yr, "mb_code": code, "cv_first_id": gm["first"].iloc[0],
                         "cv_starts_at_1_1": bool(gm["set_num"].iloc[0] == 1 and gm["game_num"].iloc[0] == 1),
                         "cv_games": int(len(gm)), "cv_counts": {str(k): int(v) for k, v in cnt.items()}})
    return pd.DataFrame(rows, columns=["year", "mb_code", "cv_first_id", "cv_starts_at_1_1", "cv_games", "cv_counts"])


def mcp(pairs: set[tuple[str, int]]) -> pd.DataFrame:
    base = F.DUMP / "match_charting_project"
    out = []
    for g in ("m", "w"):
        mm = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        t = mm["Tournament"].astype(str)
        yr = pd.to_numeric(mm["Date"].astype(str).str[:4], errors="coerce")
        ev = np.where(t.str.contains("Roland", case=False), "RG",
                      np.where(t.str.contains("Australian", case=False), "AO", ""))
        sel = pd.Series([(e, int(y)) in pairs if e and pd.notna(y) else False for e, y in zip(ev, yr)], index=mm.index)
        mm = mm[sel].copy()
        pts = pd.concat([pd.read_parquet(f) for f in sorted((base / "points").glob(f"charting-{g}-points-*.parquet"))],
                        ignore_index=True)
        pts = pts[pts["match_id"].isin(set(mm["match_id"]))].copy()
        for c in ["Pt", "Set1", "Set2", "Gm1", "Gm2", "Svr"]:
            pts[c] = pd.to_numeric(pts[c], errors="coerce")
        tbset = pts["TbSet"].astype(str).str.lower().isin(["true", "1"])
        pts["tb"] = tbset & pts["Gm1"].eq(6) & pts["Gm2"].eq(6)
        pts["set_i"], pts["game_i"] = pts["Set1"] + pts["Set2"], pts["Gm1"] + pts["Gm2"]
        for mid, p in pts.sort_values(["match_id", "Pt"]).groupby("match_id"):
            m = mm[mm["match_id"].eq(mid)].iloc[0]
            games = p.groupby(["set_i", "game_i"], sort=True).agg(svr=("Svr", lambda s: tuple(dict.fromkeys(s))),
                                                                   first=("Svr", "first"), tb=("tb", "any")).reset_index()
            reg = games[~games["tb"] & games["svr"].map(len).eq(1)]
            out.append({"mcp_id": mid, "tour": "atp" if g == "m" else "wta",
                        "event": "AO" if "Australian" in str(m["Tournament"]) else "RG",
                        "year": int(str(m["Date"])[:4]), "round": str(m["Round"]).strip(), "p1": m["Player 1"],
                        "p2": m["Player 2"], "mcp_first": int(games["first"].iloc[0]),
                        "mcp_starts_at_0_0": bool(games["set_i"].iloc[0] == 0 and games["game_i"].iloc[0] == 0),
                        "mcp_games": int(len(games)), "mcp_p1": int((reg["first"] == 1).sum()),
                        "mcp_p2": int((reg["first"] == 2).sum())})
    return pd.DataFrame(out)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--editions", default=None)
    ap.add_argument("--tag", default="")
    ap.add_argument("--list", default="addendum_swaps.csv")
    args = ap.parse_args()
    editions = editions_of(args.editions)
    pairs = {(s, y) for s, y, _ in editions}
    raw = B.normalise(B.load_raw())
    raw = raw[raw["source"].eq("sackmann")]
    yr = pd.to_numeric(raw["season"], errors="coerce")
    ev = np.where(raw["tourney_name"].eq(NAME["AO"]), "AO", np.where(raw["tourney_name"].eq(NAME["RG"]), "RG", ""))
    sel = pd.Series([(e, int(y)) in pairs if e and pd.notna(y) else False for e, y in zip(ev, yr)], index=raw.index)
    raw = raw[sel].copy()
    del yr, ev
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("int64")
    raw["season"] = pd.to_numeric(raw["season"]).astype("int64")
    raw["key"] = F.rowkey(raw["_source_file"], raw["_row"])
    raw["event"] = np.where(raw["tourney_name"].eq(NAME["AO"]), "AO", "RG")
    raw.astype({c: "object" for c in raw.columns if raw[c].dtype == object}).to_parquet(
        F.OUT / f"svx_add{args.tag}_raw.parquet", index=False)
    fl = files(editions)
    L = link(raw, fl)
    d = raw.merge(L, on="key", how="left").merge(fl.drop(columns=["round", "tour", "draw"]),
                                                 left_on=["event", "season", "mb_code"],
                                                 right_on=["event", "year", "mb_code"], how="left")
    s0 = pd.read_parquet(F.S0 / "stage0_matches.parquet", columns=["match_id", "source_file", "source_row", "status"])
    s0["key"] = F.rowkey(s0["source_file"], s0["source_row"])
    s0 = s0.drop_duplicates("key").set_index("key")
    num = lambda s: pd.to_numeric(s.astype("object").where(s.notna(), "").astype(str).str.strip().replace("", np.nan),
                                  errors="coerce")
    d["row_w"], d["row_l"] = num(d["w_SvGms"]), num(d["l_SvGms"])
    d["svpt_w_row"], d["svpt_l_row"] = num(d["w_svpt"]), num(d["l_svpt"])
    d["status_s0"] = d["key"].map(s0["status"])
    d["match_id"] = d["key"].map(s0["match_id"])
    d["first_side"] = [None if (pd.isna(f) or not isinstance(w, str)) else ("w" if str(f) == w else "l")
                       for f, w in zip(d["first"], d["w_slot"])]
    tw, tl = [], []
    for sc, fs, st in zip(d["score"], d["first_side"], d["status_s0"]):
        if fs is None or st == "walkover":
            tw.append(np.nan)
            tl.append(np.nan)
        else:
            a, b = alternation(sc, fs == "w")
            tw.append(a)
            tl.append(b)
    d["true_w"], d["true_l"] = tw, tl
    other = lambda s: None if not isinstance(s, str) else ("2" if s == "1" else "1")
    d["mb_w"] = [r.get(f"p{w}_done_regular") if isinstance(w, str) else np.nan for w, r in zip(d["w_slot"], d.to_dict("records"))]
    d["mb_l"] = [r.get(f"p{other(w)}_done_regular") if isinstance(w, str) else np.nan
                 for w, r in zip(d["w_slot"], d.to_dict("records"))]
    d["mb_svpt_w"] = [r.get(f"p{w}_svpt") if isinstance(w, str) else np.nan for w, r in zip(d["w_slot"], d.to_dict("records"))]
    d["mb_svpt_l"] = [r.get(f"p{other(w)}_svpt") if isinstance(w, str) else np.nan
                      for w, r in zip(d["w_slot"], d.to_dict("records"))]
    d["mb_whole"] = d["mb_svpt_w"].eq(d["svpt_w_row"]) & d["mb_svpt_l"].eq(d["svpt_l_row"])

    def cls(r) -> str:
        if not isinstance(r["mb_code"], str):
            return "no file"
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
    d["row_as_if_winner_first"] = [(rw, rl) == alternation(sc, True) for rw, rl, sc in zip(d["row_w"], d["row_l"], d["score"])]
    d["games"] = d["score"].fillna("").map(lambda s: sum(B.score_counts(str(s), False)[2:4]))
    # ---------------------------------------------------------------- Court Vision (AO 2020-2024)
    cv = cv_ao({y for s, y in pairs if s == "AO"})
    d = d.merge(cv.rename(columns={"year": "season"}), on=["season", "mb_code"], how="left")
    w_id = [r.get(f"p{w}_id") if isinstance(w, str) else None for w, r in zip(d["w_slot"], d.to_dict("records"))]
    l_id = [r.get(f"p{other(w)}_id") if isinstance(w, str) else None for w, r in zip(d["w_slot"], d.to_dict("records"))]
    d["cv_first_side"] = [None if not isinstance(c, str) else ("w" if c == a else "l" if c == b else "?")
                          for c, a, b in zip(d["cv_first_id"], w_id, l_id)]
    d["cv_w"] = [c.get(a) if isinstance(c, dict) else np.nan for c, a in zip(d["cv_counts"], w_id)]
    d["cv_l"] = [c.get(b) if isinstance(c, dict) else np.nan for c, b in zip(d["cv_counts"], l_id)]
    # ---------------------------------------------------------------- the charts
    mc = mcp(pairs)
    rows = []
    groups = {k: g for k, g in d.groupby(["event", "season", "tour", "round"])}
    for r in mc.itertuples():
        cand = groups.get((r.event, r.year, r.tour, r.round))
        if cand is None:
            continue
        best = []
        for x in cand.itertuples():
            for p1_is_w in (True, False):
                a = F.name_ok(r.p1, x.winner_name if p1_is_w else x.loser_name)
                b = F.name_ok(r.p2, x.loser_name if p1_is_w else x.winner_name)
                if min(a, b) >= 1:
                    best.append(((min(a, b), a + b), x.key, p1_is_w))
        best.sort(key=lambda z: z[0], reverse=True)
        if not best or (len(best) > 1 and best[0][0] == best[1][0]):
            continue
        _, key, p1_is_w = best[0]
        rows.append({"key": key, "mcp_id": r.mcp_id, "mcp_first_side": "w" if (r.mcp_first == 1) == p1_is_w else "l",
                     "mcp_w": r.mcp_p1 if p1_is_w else r.mcp_p2, "mcp_l": r.mcp_p2 if p1_is_w else r.mcp_p1,
                     "mcp_starts_at_0_0": r.mcp_starts_at_0_0, "mcp_games": r.mcp_games})
    if rows:
        d = d.merge(pd.DataFrame(rows).drop_duplicates("key"), on="key", how="left")
    retired = d["status_s0"].eq("retired")
    for ref, start in (("cv", "cv_starts_at_1_1"), ("mcp", "mcp_starts_at_0_0")):
        if f"{ref}_games" not in d:
            continue
        full = d[f"{ref}_games"].notna() & (d[f"{ref}_games"] >= d["games"]) & d[start].fillna(False).astype(bool)
        d[f"{ref}_holds"] = full
        d[f"{ref}_first_agrees"] = np.where(full, d[f"{ref}_first_side"] == d["first_side"], None)
        extra = retired & (d[f"{ref}_games"] == d["games"] + 1)
        tw_ = d["true_w"] + np.where(extra & (d[f"{ref}_w"] > d["true_w"]), 1, 0)
        tl_ = d["true_l"] + np.where(extra & (d[f"{ref}_l"] > d["true_l"]), 1, 0)
        rt = full & d[f"{ref}_w"].eq(tw_) & d[f"{ref}_l"].eq(tl_)
        rr = full & d[f"{ref}_w"].eq(d["row_w"]) & d[f"{ref}_l"].eq(d["row_l"])
        d[f"{ref}_reading"] = np.select([~full, rt & rr, rt, rr], ["not held", "both (row = truth)", "truth", "row"],
                                        "neither")
    # ---------------------------------------------------------------- the lead's tables
    lm = pd.read_csv(F.FOLLOW / "service_games" / "matches.csv", low_memory=False)
    lm["key"] = F.rowkey(lm["source_file"], lm["source_row"])
    d["lead_cls"] = d["key"].map(lm.drop_duplicates("key").set_index("key")["cls"])
    ad = pd.read_csv(F.FOLLOW / "review" / args.list, dtype=str, keep_default_na=False)
    ad["key"] = F.rowkey(ad["source_file"], ad["source_row"])
    d["lead_addendum"] = d["key"].isin(set(ad["key"]))
    keep = [c for c in ["event", "season", "tour", "round", "qualifying", "key", "match_id", "_source_file", "_row",
                        "winner_name", "loser_name", "score", "status_s0", "mb_code", "route", "link_min", "link_tie",
                        "w_slot", "first", "first_side", "proven", "why", "row_w", "row_l", "true_w", "true_l", "mb_w",
                        "mb_l", "mb_whole", "unfinished", "my_cls", "row_as_if_winner_first", "games", "cv_first_side",
                        "cv_w", "cv_l", "cv_games", "cv_holds", "cv_first_agrees", "cv_reading", "mcp_id",
                        "mcp_first_side", "mcp_w", "mcp_l", "mcp_games", "mcp_holds", "mcp_first_agrees",
                        "mcp_reading", "lead_cls", "lead_addendum"] if c in d]
    d[keep].to_csv(F.OUT / f"svx_add{args.tag}_rows.csv", index=False)
    p = d[d["lead_addendum"]]
    smry = {
        "files": fl.groupby(["event", "year"]).size().rename("files").reset_index().to_dict("records"),
        "file_errors": fl["error"].notna().sum() if "error" in fl else 0,
        "rows": d.groupby(["event", "season"]).size().rename("rows").reset_index().to_dict("records"),
        "linked": int(d["mb_code"].notna().sum()), "link_ties": int(d["link_tie"].fillna(False).sum()),
        "classes": d.groupby(["event", "season", "my_cls"]).size().rename("matches").reset_index().to_dict("records"),
        "my_class_vs_lead": pd.crosstab(d["my_cls"], d["lead_cls"].fillna("(absent)")).to_dict(),
        "addendum_swaps": int(len(ad)), "addendum_found": int(p.shape[0]),
        "addendum_my_class": p["my_cls"].value_counts().to_dict(),
        "my_swapped_not_in_addendum": d.loc[d["my_cls"].eq("swapped") & ~d["lead_addendum"],
                                            ["event", "season", "match_id", "winner_name", "loser_name"]].to_dict("records"),
        "addendum_mb_equals_truth": int((p["mb_w"].eq(p["true_w"]) & p["mb_l"].eq(p["true_l"])).sum()),
        "addendum_mb_whole": int(p["mb_whole"].sum()),
        "addendum_row_as_if_winner_first": int(p["row_as_if_winner_first"].sum()),
        "addendum_link_min": p["link_min"].value_counts().to_dict(),
        "referees": {ref: {"held": int(d[f"{ref}_holds"].sum()) if f"{ref}_holds" in d else 0,
                           "first_agrees": d.loc[d.get(f"{ref}_holds", pd.Series(False, index=d.index)).astype(bool),
                                                 f"{ref}_first_agrees"].value_counts(dropna=False).to_dict()
                           if f"{ref}_holds" in d else {},
                           "readings_by_class": d[d.get(f"{ref}_holds", pd.Series(False, index=d.index)).astype(bool)]
                           .groupby(["my_cls", f"{ref}_reading"]).size().rename("matches").reset_index().to_dict("records")
                           if f"{ref}_holds" in d else [],
                           "addendum_held": int(p[f"{ref}_holds"].sum()) if f"{ref}_holds" in p else 0,
                           "addendum_readings": p.loc[p[f"{ref}_holds"].astype(bool), f"{ref}_reading"].value_counts()
                           .to_dict() if f"{ref}_holds" in p else {}}
                     for ref in ("cv", "mcp")},
        "unproven_reasons": d.loc[d["my_cls"].eq("unproven"), "why"].value_counts().head(15).to_dict(),
    }
    (F.OUT / f"svx_add{args.tag}_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n",
                                                           encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str)[:9000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
