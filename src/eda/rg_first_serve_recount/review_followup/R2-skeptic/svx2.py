"""R2-skeptic (round 2, SVX addendum): the swapped-service-game test on the older editions (AO 2018-2024 and 2026, RG
2013-2015), with my own parse (svx_inputs2.py), links and code, and every check of the first round in one pass.

Per Stage 0 match of those editions with a MatchBeats file:
    link           the file placed on the match by tour, draw and round (from RG's or the AO's own match code) and both
                   names (folded word sets); unique best pairing required
    first server   both proofs of svx.py (opening point and in-order alternation; parity over every held game)
    truth, class   as svx.py: the row's score and the first server; equal / swapped / other / incomplete / unproven
    labels         per slot, the file's serve points, aces, double faults and serve points won against the row's box by
                   name and exchanged (the box itself not exchanged; the server labels right)
    identity       games won on serve = service games - service games lost + the opponent's lost, from the row's own
                   score and break points: for the truth and for the row
    independent    the hand charts' first server (2013-2026) and the Court Vision copy's (AO 2020-2024)
    other          TML's row of the match; another correction of the same raw row in the candidate; B8 after the
                   exchange; the file's own count where it holds the whole match
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/: svx2_matches.csv, svx2_summary.json
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx2.py
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

import svx as SX  # noqa: E402  (my proofs, truth, score parsing, name similarity)
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
DUMP = ROOT / "data" / "dump" / "points"
NINE = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
AO_MAIN = {"1": "R128", "2": "R64", "3": "R32", "4": "R16", "5": "QF", "6": "SF", "7": "F"}
AO_QUAL = {"1": "Q1", "2": "Q2", "3": "Q3"}


def code_keys(slam: str, code: str) -> tuple[str, str, str]:
    if slam == "AO":
        tour = "W" if code[0] == "W" else "M"
        draw = "qual" if code[1] == "Q" else "main"
        return tour, draw, (AO_QUAL if draw == "qual" else AO_MAIN).get(code[2], "?")
    fam, n = code[:2], int(code[2:])
    tour = "W" if fam[1] == "D" else "M"
    if fam[0] == "Q":
        return tour, "qual", ("Q3" if 16 <= n <= 31 else "Q2" if 32 <= n <= 63 else "Q1" if 64 <= n <= 127 else "?")
    return tour, "main", ("F" if n == 1 else "SF" if n <= 3 else "QF" if n <= 7 else "R16" if n <= 15 else
                          "R32" if n <= 31 else "R64" if n <= 63 else "R128" if n <= 127 else "?")


def num(v) -> float:
    return pd.to_numeric(v, errors="coerce") if v not in (None, "", "nan") else np.nan


def main() -> int:
    m = pd.read_parquet(S0 / "stage0_matches.parquet", columns=["match_id", "tour", "year", "qualifying", "round",
                                                                 "tournament_name", "status", "source", "source_file",
                                                                 "source_row"])
    raw = pd.concat([pd.read_parquet(OUT / "raw_ao_all.parquet"), pd.read_parquet(OUT / "raw_rg.parquet")],
                    ignore_index=True)
    raw["_row"] = raw["_row"].astype("Int64")
    raw = raw.drop_duplicates(["_source_file", "_row"])
    m["source_row"] = pd.to_numeric(m["source_row"]).astype("Int64")
    sel = (m["tournament_name"].eq("Australian Open") & m["year"].isin([2018, 2019, 2020, 2021, 2022, 2023, 2024, 2026])) | \
          (m["tournament_name"].eq("Roland Garros") & m["year"].between(2013, 2015))
    m = m[sel].merge(raw.rename(columns={"_source_file": "source_file", "_row": "source_row", "round": "raw_round",
                                         "tour": "raw_tour", "source": "raw_source"}),
                     on=["source_file", "source_row"], how="left")
    meta = pd.read_parquet(OUT / "old_mb_meta.parquet")
    meta = meta[meta["problem"].isna()].copy()
    pts = pd.read_parquet(OUT / "old_mb_points.parquet")
    by = {k: g for k, g in pts.groupby(["slam", "year", "code"])}
    keys = meta.apply(lambda r: code_keys(r["slam"], r["code"]), axis=1)
    meta["tour_l"], meta["draw"], meta["round"] = keys.str[0], keys.str[1], keys.str[2]
    meta["n1"] = (meta["p1_first"].fillna("") + " " + meta["p1_last"].fillna("")).map(SX.fold)
    meta["n2"] = (meta["p2_first"].fillna("") + " " + meta["p2_last"].fillna("")).map(SX.fold)
    groups = {k: g for k, g in meta.groupby(["slam", "year", "tour_l", "draw", "round"])}
    rows = []
    for x in m.itertuples(index=False):
        slam = "AO" if x.tournament_name == "Australian Open" else "RG"
        tour_l = "M" if x.tour == "atp" else "W"
        draw = "qual" if x.qualifying else "main"
        cand = groups.get((slam, int(x.year), tour_l, draw, x.round))
        wn, ln = SX.fold(x.winner_name), SX.fold(x.loser_name)
        scored = []
        if cand is not None:
            for c in cand.itertuples(index=False):
                for orient, (a, b) in (("12", (c.n1, c.n2)), ("21", (c.n2, c.n1))):
                    s1, s2 = SX.sim(wn, a), SX.sim(ln, b)
                    scored.append(((min(s1, s2), s1 + s2), c.code, orient, c.winner_slot))
        scored.sort(key=lambda t: t[0], reverse=True)
        rec = {"event": slam, "match_id": x.match_id, "year": int(x.year), "tour": tour_l, "draw": draw,
               "round": x.round, "status": x.status, "source": x.source, "source_file": x.source_file,
               "source_row": x.source_row, "row_score": x.score, "winner": x.winner_name, "loser": x.loser_name}
        box = {f"{sd}_{c}": num(getattr(x, f"{sd}_{c}")) for sd in ("w", "l") for c in NINE}
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
        p = by.get((slam, int(x.year), best[1]), pd.DataFrame())
        rec.update(SX.proofs(p, SX.score_sets(x.score)))
        # per-slot counts for the label test
        if len(p):
            for k in ("1", "2"):
                q = p[p["server"].eq(k)]
                rec[f"f{k}_ace"], rec[f"f{k}_df"] = int(q["result"].eq("A").sum()), int(q["result"].eq("DF").sum())
                rec[f"f{k}_won"] = int(q["scorer"].eq(k).sum())
        rows.append(rec)
    df = pd.DataFrame(rows)
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
    # labels: the file's per-slot counts against the row's box, by name and exchanged
    ws = df["w_slot"].astype(int).astype(str)

    def slot(col, which):
        return np.where(ws.eq("1") == (which == "w"), df[f"f1_{col}"], df[f"f2_{col}"])
    fw = {"svpt": np.where(ws.eq("1"), df["file_svpt_1"], df["file_svpt_2"]),
          "ace": slot("ace", "w"), "df": slot("df", "w"), "won": slot("won", "w")}
    fl = {"svpt": np.where(ws.eq("1"), df["file_svpt_2"], df["file_svpt_1"]),
          "ace": slot("ace", "l"), "df": slot("df", "l"), "won": slot("won", "l")}
    rw = {"svpt": df["row_w_svpt"], "ace": df["row_w_ace"], "df": df["row_w_df"],
          "won": df["row_w_1stWon"] + df["row_w_2ndWon"]}
    rl = {"svpt": df["row_l_svpt"], "ace": df["row_l_ace"], "df": df["row_l_df"],
          "won": df["row_l_1stWon"] + df["row_l_2ndWon"]}
    named = sum(np.abs(fw[k] - rw[k]) + np.abs(fl[k] - rl[k]) for k in fw)
    exch = sum(np.abs(fw[k] - rl[k]) + np.abs(fl[k] - rw[k]) for k in fw)
    df["label_named_dist"], df["label_exchanged_dist"] = named, exch
    df["labels_by_name"] = named < exch
    # identity from the row's score and break points
    gs = df["row_score"].map(lambda s: B.score_counts(str(s or ""), False))
    df["gw"], df["gl"] = gs.map(lambda c: c[2] - c[4]), gs.map(lambda c: c[3] - c[5])

    def holds(sw_, sl_):
        return (df["gw"] == sw_ - df["w_bp_lost"] + df["l_bp_lost"]) & (df["gl"] == sl_ - df["l_bp_lost"] + df["w_bp_lost"])
    df["identity_truth"], df["identity_row"] = holds(df["true_w"], df["true_l"]), holds(df["raw_w"], df["raw_l"])
    # the file's own count where it holds the whole match
    df["row_games_per_set"] = df["row_score"].map(lambda sc: json.dumps([a + b for a, b, _ in SX.score_sets(sc)]))
    df["file_whole"] = df["file_games_per_set"].eq(df["row_games_per_set"]) & df["status"].eq("completed")
    fcw = np.where(ws.eq("1"), df["file_count_1"], df["file_count_2"])
    fcl = np.where(ws.eq("1"), df["file_count_2"], df["file_count_1"])
    df["file_count_is_truth"] = (fcw == df["true_w"]) & (fcl == df["true_l"])
    # B8 before and after
    df["b8_after_ok"] = ~((df["w_bp_lost"] > df["raw_l"]) | (df["l_bp_lost"] > df["raw_w"]))
    df["b8_before_ok"] = ~((df["w_bp_lost"] > df["raw_w"]) | (df["l_bp_lost"] > df["raw_l"]))
    df["file_first"] = np.where(df["w_first"], "w", "l")
    df.to_csv(OUT / "svx2_matches.csv", index=False)
    summ = {"matches_with_a_file": int(len(df)),
            "classes": df.pivot_table(index=["event", "year"], columns="cls", values="match_id", aggfunc="count",
                                      fill_value=0).reset_index().to_dict("records")}
    (OUT / "svx2_summary.json").write_text(json.dumps(summ, indent=1, default=str) + "\n", encoding="utf-8")
    print(df.pivot_table(index=["event", "year"], columns="cls", values="match_id", aggfunc="count",
                         fill_value=0).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
