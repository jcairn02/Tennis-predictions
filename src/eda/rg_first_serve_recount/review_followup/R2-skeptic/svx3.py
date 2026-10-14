"""R2-skeptic (round 2, SVX addendum 2): Roland Garros 2016-2018, with my own parse, links and code.

    parse   the RG 2016-2018 MatchBeats files (API route, else the static route), decrypted with the adapter's routine
            -> rg1618_mb_points.parquet, rg1618_mb_meta.parquet
    match   Stage 0's RG 2016-2018 matches (Sackmann's rows; raw rows from raw_rg.parquet, the build's own loader)
            placed on the files by tour, draw and round (from RG's own codes) and both names
    test    as svx2.py: both first-server proofs, the truth from the row's score, classes, the label test, the
            score-and-break identity, the file's own count, B8; the hand charts' first server; Tennis My Life's rows;
            the candidate's other corrections and overrides
    scope   the lead's addendum2_swaps.csv rows that pass every test (a swap whose file fails only my strict proof
            would be judged on the independent evidence and named) -> swaps_addendum2_rows.csv
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/: rg1618_matches.csv, svx3_checks.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import svx as SX  # noqa: E402
import svx2 as S2  # noqa: E402  (code_keys, num)
import svx2_checks as C2  # noqa: E402  (charts, tml)
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
RAW = ROOT / "data" / "raw" / "point_sources"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
NINE = S2.NINE
YEARS = (2016, 2017, 2018)


def parse() -> tuple[pd.DataFrame, pd.DataFrame]:
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    order = {"match-beats-api": 0, "match-beats": 1}
    pts, meta = [], []
    for year in YEARS:
        files: dict[str, tuple] = {}
        for route in order:
            for path in sorted((RAW / "infosys_slams" / "RG" / str(year) / route).glob("*.json.gz")):
                code = path.name.split(".")[0]
                if code not in files or order[route] < order[files[code][0]]:
                    files[code] = (route, path)
        for code, (route, path) in sorted(files.items()):
            rec = {"slam": "RG", "year": year, "code": code, "route": route}
            try:
                blocks = I.blocks_of(route, P.read_json(path))
                doc = I.decrypt(blocks["mbData"]) if "mbData" in blocks else None
            except Exception as err:   # noqa: BLE001 - recorded
                meta.append({**rec, "problem": f"{type(err).__name__}: {err}"})
                continue
            if not isinstance(doc, dict) or not doc.get("setData"):
                meta.append({**rec, "problem": "empty"})
                continue
            pdat = doc.get("playerData") or {}
            meta.append({**rec, "problem": None, "complete": doc.get("isMatchComplete"),
                         "status": doc.get("matchStatus"), "winner_slot": doc.get("matchWinner"),
                         **{f"p{k}_{f}": pdat.get(f"tm{k}Ply1{F}") for k in (1, 2)
                            for f, F in (("first", "FirstName"), ("last", "LastName"), ("id", "Id"))}})
            i = 0
            for si, s in enumerate(doc.get("setData") or [], 1):
                for gi, g in enumerate(s.get("gameData") or [], 1):
                    for p in g.get("pointData") or []:
                        i += 1
                        pts.append({"slam": "RG", "year": year, "code": code, "set": s.get("set", si), "set_i": si,
                                    "game": g.get("game", gi), "game_i": gi, "tb": bool(g.get("isTieBreak")),
                                    "idx": i, "pointId": p.get("pointId"), "server": str(p.get("server")),
                                    "serve": str(p.get("serve")), "scorer": str(p.get("scorer")),
                                    "result": p.get("result")})
    p, m = pd.DataFrame(pts), pd.DataFrame(meta)
    p.to_parquet(OUT / "rg1618_mb_points.parquet", index=False)
    m.to_parquet(OUT / "rg1618_mb_meta.parquet", index=False)
    print("RG 2016-2018 files:", m.groupby(["year", "route"]).size().to_dict(), m["problem"].value_counts(dropna=False)
          .to_dict(), len(p), "points")
    return p, m


def main() -> int:
    pts, meta = parse()
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "year", "qualifying", "round",
                                                                 "tournament_name", "status", "source", "source_file",
                                                                 "source_row"])
    m = m[m["tournament_name"].eq("Roland Garros") & m["year"].isin(YEARS)].copy()
    raw = pd.read_parquet(OUT / "raw_rg.parquet")
    raw["_row"] = raw["_row"].astype("Int64")
    m["source_row"] = pd.to_numeric(m["source_row"]).astype("Int64")
    m = m.merge(raw.rename(columns={"_source_file": "source_file", "_row": "source_row", "round": "raw_round",
                                    "tour": "raw_tour", "source": "raw_source"}),
                on=["source_file", "source_row"], how="left")
    meta = meta[meta["problem"].isna()].copy()
    by = {k: g for k, g in pts.groupby(["year", "code"])}
    keys = meta["code"].map(lambda c: S2.code_keys("RG", c))
    meta["tour_l"], meta["draw"], meta["round"] = keys.str[0], keys.str[1], keys.str[2]
    meta["n1"] = (meta["p1_first"].fillna("") + " " + meta["p1_last"].fillna("")).map(SX.fold)
    meta["n2"] = (meta["p2_first"].fillna("") + " " + meta["p2_last"].fillna("")).map(SX.fold)
    groups = {k: g for k, g in meta.groupby(["year", "tour_l", "draw", "round"])}
    rows = []
    for x in m.itertuples(index=False):
        tour_l, draw = ("M" if x.tour == "atp" else "W"), ("qual" if x.qualifying else "main")
        cand = groups.get((int(x.year), tour_l, draw, x.round))
        wn, ln = SX.fold(x.winner_name), SX.fold(x.loser_name)
        scored = []
        if cand is not None:
            for c in cand.itertuples(index=False):
                for orient, (a, b) in (("12", (c.n1, c.n2)), ("21", (c.n2, c.n1))):
                    s1, s2 = SX.sim(wn, a), SX.sim(ln, b)
                    scored.append(((min(s1, s2), s1 + s2), c.code, orient, c.winner_slot))
        scored.sort(key=lambda t: t[0], reverse=True)
        rec = {"event": "RG", "match_id": x.match_id, "year": int(x.year), "tour": tour_l, "draw": draw,
               "round": x.round, "status": x.status, "source": x.source, "source_file": x.source_file,
               "source_row": x.source_row, "row_score": x.score, "winner": x.winner_name, "loser": x.loser_name}
        box = {f"{sd}_{c}": S2.num(getattr(x, f"{sd}_{c}")) for sd in ("w", "l") for c in NINE}
        rec.update({"raw_w": box["w_SvGms"], "raw_l": box["l_SvGms"],
                    "w_bp_lost": box["w_bpFaced"] - box["w_bpSaved"], "l_bp_lost": box["l_bpFaced"] - box["l_bpSaved"],
                    **{f"row_{k}": v for k, v in box.items()}})
        if not scored or scored[0][0][0] < 1 or any(s[0] == scored[0][0] and (s[1], s[2]) != (scored[0][1], scored[0][2])
                                                     for s in scored[1:]):
            rec["code"] = None
            rows.append(rec)
            continue
        best = scored[0]
        w_slot = 1 if best[2] == "12" else 2
        rec.update({"code": best[1], "link_score": best[0][0], "w_slot": w_slot,
                    "winner_agrees": (None if pd.isna(best[3]) or int(best[3]) == 0 else int(best[3]) == w_slot)})
        p = by.get((int(x.year), best[1]), pd.DataFrame())
        rec.update(SX.proofs(p, SX.score_sets(x.score)))
        if len(p):
            for k in ("1", "2"):
                q = p[p["server"].eq(k)]
                rec[f"f{k}_ace"], rec[f"f{k}_df"] = int(q["result"].eq("A").sum()), int(q["result"].eq("DF").sum())
                rec[f"f{k}_won"] = int(q["scorer"].eq(k).sum())
        rows.append(rec)
    df = pd.DataFrame(rows)
    report = {"stage0_matches": int(len(m)), "linked": int(df["code"].notna().sum()),
              "unlinked": df[df["code"].isna()][["match_id", "winner", "loser"]].to_dict("records")}
    df = df[df["code"].notna() & df["has_file"].eq(True)].copy()
    df["proven"] = df["in_order_proof"] & df["parity_dissent"].eq(0) & df["parity_slot"].eq(df["first_slot"])
    df["w_first"] = df["first_slot"].astype(str).eq(df["w_slot"].astype(int).astype(str))
    t = [SX.truth(SX.score_sets(sc), bool(wf)) for sc, wf in zip(df["row_score"], df["w_first"])]
    df["true_w"], df["true_l"] = [a for a, _ in t], [b for _, b in t]
    df.loc[df["status"].eq("walkover"), ["true_w", "true_l"]] = np.nan
    asw = [SX.truth(SX.score_sets(sc), True) for sc in df["row_score"]]
    df["as_if_w_first_w"], df["as_if_w_first_l"] = [a for a, _ in asw], [b for _, b in asw]

    def cls(r):
        if not r["proven"]:
            return "unproven"
        if pd.isna(r["raw_w"]) or pd.isna(r["raw_l"]) or pd.isna(r["true_w"]):
            return "incomplete"
        if r["raw_w"] == r["true_w"] and r["raw_l"] == r["true_l"]:
            return "equal"
        if r["true_w"] != r["true_l"] and r["raw_w"] == r["true_l"] and r["raw_l"] == r["true_w"]:
            return "swapped"
        return "other"
    df["cls"] = df.apply(cls, axis=1)
    df["row_as_if_winner_first"] = df["raw_w"].eq(df["as_if_w_first_w"]) & df["raw_l"].eq(df["as_if_w_first_l"])
    ws = df["w_slot"].astype(int).astype(str)

    def slot(col, which):
        return np.where(ws.eq("1") == (which == "w"), df[f"f1_{col}"], df[f"f2_{col}"])
    fw = {"svpt": np.where(ws.eq("1"), df["file_svpt_1"], df["file_svpt_2"]), "ace": slot("ace", "w"),
          "df": slot("df", "w"), "won": slot("won", "w")}
    fl = {"svpt": np.where(ws.eq("1"), df["file_svpt_2"], df["file_svpt_1"]), "ace": slot("ace", "l"),
          "df": slot("df", "l"), "won": slot("won", "l")}
    rw = {"svpt": df["row_w_svpt"], "ace": df["row_w_ace"], "df": df["row_w_df"],
          "won": df["row_w_1stWon"] + df["row_w_2ndWon"]}
    rl = {"svpt": df["row_l_svpt"], "ace": df["row_l_ace"], "df": df["row_l_df"],
          "won": df["row_l_1stWon"] + df["row_l_2ndWon"]}
    named = sum(np.abs(fw[k] - rw[k]) + np.abs(fl[k] - rl[k]) for k in fw)
    exch = sum(np.abs(fw[k] - rl[k]) + np.abs(fl[k] - rw[k]) for k in fw)
    df["labels_by_name"] = named < exch
    gs = df["row_score"].map(lambda s: B.score_counts(str(s or ""), False))
    df["gw"], df["gl"] = gs.map(lambda c: c[2] - c[4]), gs.map(lambda c: c[3] - c[5])

    def holds(sw_, sl_):
        return (df["gw"] == sw_ - df["w_bp_lost"] + df["l_bp_lost"]) & (df["gl"] == sl_ - df["l_bp_lost"] + df["w_bp_lost"])
    df["identity_truth"], df["identity_row"] = holds(df["true_w"], df["true_l"]), holds(df["raw_w"], df["raw_l"])
    df["row_games_per_set"] = df["row_score"].map(lambda sc: json.dumps([a + b for a, b, _ in SX.score_sets(sc)]))
    df["file_whole"] = df["file_games_per_set"].eq(df["row_games_per_set"]) & df["status"].eq("completed")
    fcw = np.where(ws.eq("1"), df["file_count_1"], df["file_count_2"])
    fcl = np.where(ws.eq("1"), df["file_count_2"], df["file_count_1"])
    df["file_count_is_truth"] = (fcw == df["true_w"]) & (fcl == df["true_l"])
    df["b8_after_ok"] = ~((df["w_bp_lost"] > df["raw_l"]) | (df["l_bp_lost"] > df["raw_w"]))
    df["b8_before_ok"] = ~((df["w_bp_lost"] > df["raw_w"]) | (df["l_bp_lost"] > df["raw_l"]))
    df["file_first"] = np.where(df["w_first"], "w", "l")
    ch = C2.charts(df)
    df["chart_first"] = df["match_id"].map(ch)
    df = df.merge(C2.tml(df), on="match_id", how="left")
    rc = pd.read_csv(LEAD / "confirmed" / "candidate" / "corrections" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    rk = dict(zip(rc["source_file"] + "|" + rc["source_row"].astype(str), rc["fix"] + ":" + rc["action"]))
    df["candidate_fix"] = (df["source_file"] + "|" + df["source_row"].astype(str)).map(rk)
    ov = pd.read_csv(LEAD / "confirmed" / "candidate" / "slam_box_overrides.csv", dtype=str, keep_default_na=False)
    df["candidate_override"] = df["match_id"].isin(set(ov["stage0_match_id"]))
    df["chart_ok"] = df["chart_first"].isna() | df["chart_first"].eq(df["file_first"])
    base = (df["labels_by_name"] & df["identity_truth"] & ~df["identity_row"] & ~df["winner_agrees"].eq(False)
            & df["chart_ok"] & df["candidate_fix"].isna() & ~df["candidate_override"] & df["b8_after_ok"])
    df["confirm_strict"] = df["cls"].eq("swapped") & df["proven"] & base
    df.to_csv(OUT / "rg1618_matches.csv", index=False)
    lead = pd.read_csv(LEAD / "review" / "addendum2_swaps.csv", dtype=str, keep_default_na=False)
    rows_ok = lead[lead["match_id"].isin(set(df.loc[df["confirm_strict"], "match_id"]))][
        ["source_file", "source_row", "match_id"]]
    rows_ok.to_csv(OUT / "swaps_addendum2_rows.csv", index=False)
    sw = df[df["cls"].eq("swapped")]
    allp = df[df["proven"]]
    h = allp[allp["chart_first"].notna()]
    res = {**report, "files_matched": int(len(df)),
           "classes": df.pivot_table(index="year", columns="cls", values="match_id", aggfunc="count",
                                     fill_value=0).to_dict("index"),
           "lead": int(len(lead)), "my_swapped": int(len(sw)),
           "lead_not_mine": sorted(set(lead["match_id"]) - set(sw["match_id"])),
           "mine_not_lead": sorted(set(sw["match_id"]) - set(lead["match_id"])),
           "confirmed": int(len(rows_ok)), "left_out": sorted(set(lead["match_id"]) - set(rows_ok["match_id"])),
           "swapped_checks": {
               "labels_by_name": int(sw["labels_by_name"].sum()),
               "identity_truth_only": int((sw["identity_truth"] & ~sw["identity_row"]).sum()),
               "winner_disagrees": int(sw["winner_agrees"].eq(False).sum()),
               "charts_held": int(sw["chart_first"].notna().sum()),
               "charts_agree": int(sw["chart_first"].eq(sw["file_first"]).sum()),
               "file_whole": int(sw["file_whole"].sum()),
               "file_count_is_truth_where_whole": int((sw["file_whole"] & sw["file_count_is_truth"]).sum()),
               "tml_held": int(sw["tml_w"].notna().sum()),
               "tml_equals_truth": int((sw["tml_w"].eq(sw["true_w"]) & sw["tml_l"].eq(sw["true_l"])).sum()),
               "tml_equals_sackmann": int((sw["tml_w"].eq(sw["raw_w"]) & sw["tml_l"].eq(sw["raw_l"])).sum()),
               "candidate_fix": int(sw["candidate_fix"].notna().sum()),
               "candidate_override": int(sw["candidate_override"].sum()),
               "b8_after_fails": int((~sw["b8_after_ok"]).sum()), "b8_before_fails": int((~sw["b8_before_ok"]).sum()),
               "status": sw["status"].value_counts().to_dict(),
               "row_as_if_winner_first": int(sw["row_as_if_winner_first"].sum())},
           "all_proven": {"matches": int(len(allp)), "charts_held": int(len(h)),
                          "charts_agree": int(h["chart_first"].eq(h["file_first"]).sum()),
                          "identity_equal_class": {"matches": int(allp["cls"].eq("equal").sum()),
                                                   "holds": int((allp["cls"].eq("equal") & allp["identity_truth"]).sum())}},
           "other_2017": {"matches": int((df["cls"].eq("other") & df["year"].eq(2017)).sum()),
                          "row_below_truth_total_by": df[df["cls"].eq("other") & df["year"].eq(2017)]
                          .eval("(raw_w + raw_l) - (true_w + true_l)").describe().round(1).to_dict()},
           "swapped_failing_a_check": sw[~sw["confirm_strict"]][
               ["match_id", "labels_by_name", "identity_truth", "identity_row", "winner_agrees", "chart_ok",
                "candidate_fix", "candidate_override", "b8_after_ok"]].to_dict("records")}
    (OUT / "svx3_checks.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k not in ("unlinked",)}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
