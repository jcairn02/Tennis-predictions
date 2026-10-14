"""R2-skeptic (round 2, SVX addendum): the skeptic's checks on the older editions' swaps (svx2_matches.csv), against
the lead's addendum_swaps.csv, and my scope.

    same set       my swapped matches against the lead's 382 (and its left-outs)
    independent    the hand charts' first server (2013-2026: every chart opens at 0-0 and passes the parity test) and
                   the Court Vision copy's (AO 2020-2024), against the file's, on every match both hold
    TML            Tennis My Life's row of the match: its service games against the truth and against Sackmann's
    candidate      another correction of the same raw row in the candidate's row_corrections.csv, or an override
    confirm        as the first round: my class swapped with the first server proven twice, the labels by name, the
                   score-and-break identity for the truth and not the row, the winner agreeing, no chart or Court
                   Vision file naming another first server, no other correction, B8 after. A swap whose file fails only
                   my strict proof is judged on the independent evidence and named.
Writes, in data/studies/rg_first_serve_recount/followup/review/R2-skeptic/: svx2_checked.csv, svx2_checks.json,
swaps_addendum_rows.csv
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R2-skeptic/svx2_checks.py
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

OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R2-skeptic"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
DUMP = ROOT / "data" / "dump" / "points"


def charts(df: pd.DataFrame) -> dict:
    ch = pd.read_parquet(OUT / "mcp_first_all.parquet")
    ch["event"] = np.where(ch["tournament"].str.contains("Australian", case=False), "AO", "RG")
    ch["year"] = ch["date"].astype(str).str[:4].astype(int)
    ch["rnd"] = ch["round"].astype(str).str.upper()
    groups = {k: g for k, g in ch.groupby(["event", "year", "tour"])}
    out = {}
    for r in df.itertuples(index=False):
        g = groups.get((r.event, int(r.year), r.tour))
        if g is None:
            continue
        g = g[g["rnd"].eq(str(r.round))]
        wn, ln = SX.fold(r.winner), SX.fold(r.loser)
        best = None
        for c in g.itertuples(index=False):
            a, b = SX.fold(c.p1), SX.fold(c.p2)
            sc = max(min(SX.sim(wn, a), SX.sim(ln, b)), min(SX.sim(wn, b), SX.sim(ln, a)))
            if sc >= 2 and (best is None or sc > best[0]):
                best = (sc, c)
        if best is None:
            continue
        fs = SX.fold(best[1].parity_first_server)
        who = "w" if SX.sim(fs, wn) >= 2 and SX.sim(fs, wn) >= SX.sim(fs, ln) else ("l" if SX.sim(fs, ln) >= 2 else None)
        out[r.match_id] = who
    return out


def court_vision(df: pd.DataFrame) -> dict:
    cat = pd.read_parquet(DUMP / "slam_ball_tracking" / "matches.parquet")
    cat = cat[cat["slam"].eq("AO")]
    out = {}
    for year in range(2020, 2025):
        f = DUMP / "slam_ball_tracking" / "points" / f"AO_{year}.parquet"
        if not f.exists():
            continue
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "server_id", "set_num", "game_num", "point_num"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        c = cat[cat["year"].astype(str).eq(str(year))]
        ids = {str(x).split("_")[-1]: (str(p1), str(p2), str(n1), str(n2)) for x, p1, p2, n1, n2 in
               zip(c["match_id"], c["player1_id"], c["player2_id"], c["player1"], c["player2"])}
        for r in df[df["event"].eq("AO") & df["year"].eq(year)].itertuples(index=False):
            q = pt[pt["code"].eq(str(r.code))]
            if q.empty or str(r.code) not in ids:
                continue
            key = pd.DataFrame({"s": pd.to_numeric(q["set_num"], errors="coerce"),
                                "g": pd.to_numeric(q["game_num"], errors="coerce"),
                                "p": pd.to_numeric(q["point_num"], errors="coerce")}, index=q.index)
            first = q.loc[key.sort_values(["s", "g", "p"]).index].iloc[0]
            if not (pd.to_numeric(first["set_num"], errors="coerce") == 1
                    and pd.to_numeric(first["game_num"], errors="coerce") == 1):
                continue
            p1, p2, n1, n2 = ids[str(r.code)]
            sid = str(first["server_id"])
            name = n1 if sid == p1 else n2 if sid == p2 else None
            last = SX.fold(str(name).split(".", 1)[-1]) if name else []
            wl, ll = SX.fold(r.winner), SX.fold(r.loser)
            hw, hl = bool(last) and any(t in wl for t in last), bool(last) and any(t in ll for t in last)
            out[r.match_id] = "w" if hw and not hl else "l" if hl and not hw else None
    return out


def tml(df: pd.DataFrame) -> pd.DataFrame:
    raw = pd.concat([pd.read_parquet(OUT / "raw_ao_all.parquet"), pd.read_parquet(OUT / "raw_rg.parquet")],
                    ignore_index=True)
    t = raw[raw["source"].eq("tml")].copy()
    t["year"] = t["tid"].str[:4].astype(int)
    t["event"] = np.where(t["tourney_name"].str.contains("australian", case=False), "AO", "RG")
    t["tour_l"] = np.where(t["tour"].eq("atp"), "M", "W")
    t["round"] = t["round"].astype(str).str.upper()
    t["wn"], t["ln"] = t["winner_name"].map(SX.fold), t["loser_name"].map(SX.fold)
    groups = {k: g for k, g in t.groupby(["event", "year", "tour_l", "round"])}
    out = []
    for r in df.itertuples(index=False):
        rec = {"match_id": r.match_id, "tml_w": np.nan, "tml_l": np.nan}
        g = groups.get((r.event, int(r.year), r.tour, str(r.round)))
        if g is not None:
            wn, ln = SX.fold(r.winner), SX.fold(r.loser)
            for c in g.itertuples(index=False):
                straight, crossed = min(SX.sim(wn, c.wn), SX.sim(ln, c.ln)), min(SX.sim(wn, c.ln), SX.sim(ln, c.wn))
                if max(straight, crossed) >= 2:
                    vw, vl = pd.to_numeric(c.w_SvGms, errors="coerce"), pd.to_numeric(c.l_SvGms, errors="coerce")
                    rec.update({"tml_w": vl if crossed > straight else vw, "tml_l": vw if crossed > straight else vl})
                    break
        out.append(rec)
    return pd.DataFrame(out)


def main() -> int:
    df = pd.read_csv(OUT / "svx2_matches.csv")
    lead = pd.read_csv(LEAD / "review" / "addendum_swaps.csv", dtype=str, keep_default_na=False)
    ch, cv = charts(df), court_vision(df)
    df["chart_first"] = df["match_id"].map(ch)
    df["cv_first"] = df["match_id"].map(cv)
    df = df.merge(tml(df), on="match_id", how="left")
    rc = pd.read_csv(LEAD / "confirmed" / "candidate" / "corrections" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    rk = dict(zip(rc["source_file"] + "|" + rc["source_row"].astype(str), rc["fix"] + ":" + rc["action"]))
    df["candidate_fix"] = (df["source_file"] + "|" + df["source_row"].astype(str)).map(rk)
    ov = pd.read_csv(LEAD / "confirmed" / "candidate" / "slam_box_overrides.csv", dtype=str, keep_default_na=False)
    df["candidate_override"] = df["match_id"].isin(set(ov["stage0_match_id"]))
    df["chart_ok"] = df["chart_first"].isna() | df["chart_first"].eq(df["file_first"])
    df["cv_ok"] = df["cv_first"].isna() | df["cv_first"].eq(df["file_first"])
    base = (df["labels_by_name"] & df["identity_truth"] & ~df["identity_row"] & ~df["winner_agrees"].eq(False)
            & df["chart_ok"] & df["cv_ok"] & df["candidate_fix"].isna() & ~df["candidate_override"] & df["b8_after_ok"])
    df["confirm_strict"] = df["cls"].eq("swapped") & df["proven"] & base
    # a swap whose file fails only my strict proof: the row is the truth-as-proposed exchanged, and the independent
    # evidence (identity; a chart or Court Vision) names the file's first server
    exch = df["true_w"].ne(df["true_l"]) & df["raw_w"].eq(df["true_l"]) & df["raw_l"].eq(df["true_w"])
    indep = df["chart_first"].eq(df["file_first"]) | df["cv_first"].eq(df["file_first"])
    df["confirm_on_evidence"] = df["cls"].eq("unproven") & df["file_opens_match"] & exch & base & indep
    df.to_csv(OUT / "svx2_checked.csv", index=False)
    take = df["confirm_strict"] | (df["confirm_on_evidence"] & df["match_id"].isin(set(lead["match_id"])))
    rows = lead[lead["match_id"].isin(set(df.loc[take, "match_id"]))][["source_file", "source_row", "match_id"]]
    rows.to_csv(OUT / "swaps_addendum_rows.csv", index=False)
    sw = df[df["cls"].eq("swapped")]
    allp = df[df["proven"]]

    def agree(d, col):
        h = d[d[col].notna()]
        return {"held": int(len(h)), "agree": int(h[col].eq(h["file_first"]).sum())}
    res = {"lead": int(len(lead)), "my_swapped": int(len(sw)),
           "lead_not_mine": sorted(set(lead["match_id"]) - set(sw["match_id"])),
           "mine_not_lead": sorted(set(sw["match_id"]) - set(lead["match_id"])),
           "confirmed": int(len(rows)),
           "left_out": sorted(set(lead["match_id"]) - set(rows["match_id"])),
           "swapped_checks": {
               "labels_by_name": int(sw["labels_by_name"].sum()),
               "identity_truth_only": int((sw["identity_truth"] & ~sw["identity_row"]).sum()),
               "identity_row": int(sw["identity_row"].sum()),
               "winner_disagrees": int(sw["winner_agrees"].eq(False).sum()),
               "charts": agree(sw, "chart_first"), "court_vision": agree(sw, "cv_first"),
               "file_whole": int(sw["file_whole"].sum()),
               "file_count_is_truth_where_whole": int((sw["file_whole"] & sw["file_count_is_truth"]).sum()),
               "tml_held": int(sw["tml_w"].notna().sum()),
               "tml_equals_truth": int((sw["tml_w"].eq(sw["true_w"]) & sw["tml_l"].eq(sw["true_l"])).sum()),
               "tml_equals_sackmann": int((sw["tml_w"].eq(sw["raw_w"]) & sw["tml_l"].eq(sw["raw_l"])).sum()),
               "candidate_fix": sw[sw["candidate_fix"].notna()][["match_id", "candidate_fix"]].to_dict("records"),
               "candidate_override": int(sw["candidate_override"].sum()),
               "b8_after_fails": int((~sw["b8_after_ok"]).sum()), "b8_before_fails": int((~sw["b8_before_ok"]).sum()),
               "status": sw["status"].value_counts().to_dict(),
               "row_as_if_winner_first": int(sw["row_as_if_winner_first"].sum())},
           "all_proven": {"matches": int(len(allp)), "charts": agree(allp, "chart_first"),
                          "court_vision": agree(allp, "cv_first"),
                          "identity_equal_class": {"matches": int(allp["cls"].eq("equal").sum()),
                                                   "holds": int((allp["cls"].eq("equal") & allp["identity_truth"]).sum())}},
           "judged_on_evidence": df[df["confirm_on_evidence"]][
               ["match_id", "row_score", "raw_w", "raw_l", "true_w", "true_l", "identity_truth", "identity_row",
                "chart_first", "cv_first", "file_first", "parity_dissent", "parity_games"]].to_dict("records"),
           "swapped_failing_a_check": sw[~(sw["confirm_strict"])][
               ["match_id", "labels_by_name", "identity_truth", "identity_row", "winner_agrees", "chart_ok", "cv_ok",
                "candidate_fix", "candidate_override", "b8_after_ok"]].to_dict("records")}
    (OUT / "svx2_checks.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
