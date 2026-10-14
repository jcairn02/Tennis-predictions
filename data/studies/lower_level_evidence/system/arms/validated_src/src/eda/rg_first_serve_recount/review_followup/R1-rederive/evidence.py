"""R1-rederive (round 2): the lead's claims E1-E5 and E7, recomputed from my own tables.

Inputs (mine): work/*.parquet, links.csv, sides.csv, matches.csv; the live Stage 0 tables' RG rows
(work/stage0_rg_matches.parquet, stage0_rg_match_players.parquet, saved by stage0_rows.py); round 1's confirmed
corrections (data/studies/rg_first_serve_recount/confirmed/confirmed_corrections.csv, a decided-by-review table, not
the follow-up proposal). No table of the follow-up proposal is read.

Writes evidence.json and rgx.csv (the four exchanged boxes, every count) in my output folder, and prints the tallies.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/evidence.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]
SIX = ["svpt", "ace", "df", "first_in", "first_won", "second_won"]
NINE = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
EV: dict = {}


def pct(a, b) -> float:
    return round(100.0 * a / b, 1) if b else float("nan")


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 300)
    api = pd.read_parquet(WORK / "rg_api.parquet")
    mb = pd.read_parquet(WORK / "mb.parquet")
    ks = pd.read_parquet(WORK / "ks.parquet")
    d = pd.read_csv(HERE / "sides.csv", low_memory=False)
    m = pd.read_csv(HERE / "matches.csv", low_memory=False)
    for c in ("der_ok", "mb_full", "ks_full", "cv_held", "mcp_held"):
        d[c] = d[c].astype(str).eq("True")
    d = d.merge(m[["rid", "cls", "group_id", "draw"]], on="rid", how="left")

    # ---------------- E1: the feed held
    docs = api[api["team"].eq("A")]
    EV["E1_held"] = {
        "rg_documents": docs.groupby("year").size().to_dict(),
        "rg_documents_with_statistics": docs.groupby("year")["has_stats"].sum().astype(int).to_dict(),
        "rg_team_rows_failing_own_checks": int((api["has_stats"] & ~api["chk_all"]).sum()),
        "matchbeats_files_with_points": mb[mb["team"].eq("1")].groupby("year").size().to_dict(),
        "matchbeats_files_empty": mb[mb["mb_status"].ne("ok")].groupby("year").size().to_dict(),
        "keystats_files": ks[ks["ks_team"].eq("1")].groupby("year").size().to_dict()}
    print("E1 held:", json.dumps(EV["E1_held"]))

    # ---------------- E1: matched Sackmann's history (2019-2021)
    c = d[d["year"].le(2021)]
    boxed = c[c["raw_svpt"].notna() & c["off_svpt"].notna()]
    eq8 = boxed[[f"raw_{k}" for k in EIGHT]].to_numpy() == boxed[[f"off_{k}" for k in EIGHT]].to_numpy()
    boxed = boxed.assign(eq8=eq8.all(axis=1))
    EV["E1_control"] = {"linked_player_rows": int(len(c)), "with_both_boxes": int(len(boxed)),
                        "all_eight_equal": int(boxed["eq8"].sum()),
                        "not_equal": boxed[~boxed["eq8"]][["year", "code", "side", "name"]].to_dict("records"),
                        "rows_without_a_box": int(len(c) - len(boxed))}
    print("E1 control:", EV["E1_control"]["all_eight_equal"], "of", len(boxed), "| not equal:",
          [(r["code"], r["side"], r["name"]) for r in EV["E1_control"]["not_equal"]])

    # ---------------- E1: service games, MatchBeats (tiebreaks not counted) against the rows
    sv = {}
    for era, lo, hi in (("2019-2021", 2019, 2021), ("2022-2025", 2022, 2025)):
        e = d[d["year"].between(lo, hi) & d["source"].eq("sackmann")]
        e_box = e[e["raw_sv_gms"].notna()]
        both = e_box[e_box["mb_sv_gms_reg_done"].notna()]
        sv[era] = {"rows_with_row_and_mb": int(len(both)),
                   "equal_mb_done": int(both["raw_sv_gms"].eq(both["mb_sv_gms_reg_done"]).sum()),
                   "pct_of_rows_with_mb": pct(both["raw_sv_gms"].eq(both["mb_sv_gms_reg_done"]).sum(), len(both)),
                   "rows_with_row_count": int(len(e_box)),
                   "pct_of_rows_with_row_count": pct(both["raw_sv_gms"].eq(both["mb_sv_gms_reg_done"]).sum(), len(e_box)),
                   "equal_with_tiebreaks_counted": int(both["raw_sv_gms"].eq(both["mb_sv_gms_reg_done"] +
                                                                             both["mb_tb_first_served"]).sum()),
                   "equal_derived": int(both["raw_sv_gms"].eq(both["der_sv"]).sum())}
        # 2019-2021: rows that equal neither way
        if lo == 2019:
            neither = both[~both["raw_sv_gms"].eq(both["mb_sv_gms_reg_done"]) &
                           ~both["raw_sv_gms"].eq(both["mb_sv_gms_reg_done"] + both["mb_tb_first_served"])]
            sv[era]["equal_neither_way"] = int(len(neither))
    EV["E1_service_games"] = sv
    print("E1 service games:", json.dumps(sv))

    # ---------------- E7: classes
    w = m[m["year"].ge(2022)]
    EV["E7_classes_2022_2026"] = w["cls"].value_counts().to_dict()
    EV["E7_proposed"] = {"2022-2025": int(((w["cls"] == "proposed") & w["year"].le(2025)).sum()),
                         "2026": w[(w["cls"] == "proposed") & w["year"].eq(2026)].groupby(["tour", "draw"]).size()
                         .rename(lambda x: f"{x[0]}_{x[1]}" if isinstance(x, tuple) else x).to_dict()}
    print("E7:", EV["E7_classes_2022_2026"], EV["E7_proposed"])
    print(m[m["cls"].isin(["referee_contradicts", "statistics_short", "walkover", "identity"]) & m["year"].ge(2022)]
          [["year", "code", "round", "cls", "row_score"]].to_string())

    # ---------------- E2: what the referees say on the counts that change (proposed rows)
    for scope, sel in (("W22", d["group_id"].eq("W22")), ("W22+W26", d["group_id"].isin(["W22", "W26"])),
                       ("W22+W26 non-blank", d["group_id"].isin(["W22", "W26"]) & d["raw_svpt"].notna())):
        p = d[sel & d["cls"].eq("proposed")]
        tab = {}
        for k in SIX:
            ch = p[f"chg_{k}"].astype(str).eq("True")
            row = {"rows_changing": int(ch.sum())}
            for r in ("cv", "mcp"):
                cvy = p["year"].eq(2022) if r == "cv" else pd.Series(True, index=p.index)
                held = p[f"{r}_held_{k}"].astype(str).eq("True") & cvy
                row[f"{r}_rg"] = int((p[f"{r}_rg_{k}"].astype(str).eq("True") & cvy).sum())
                row[f"{r}_row"] = int((p[f"{r}_row_{k}"].astype(str).eq("True") & cvy).sum())
                row[f"{r}_held"] = int(held.sum())
            tab[k] = row
        EV[f"E2_{scope}"] = tab
        print(f"E2 {scope}:\n", pd.DataFrame(tab).T.to_string())
    # ace and double-fault direction where they change (W22 proposed)
    p = d[d["group_id"].eq("W22") & d["cls"].eq("proposed")]
    dirs = {}
    for k in ("ace", "df"):
        ch = p[p[f"chg_{k}"].astype(str).eq("True")]
        diff = ch[f"raw_{k}"] - ch[f"off_{k}"]
        dirs[k] = {"changing": int(len(ch)), "row_lower": int((diff < 0).sum()), "row_lower_by_one": int((diff == -1).sum()),
                   "row_higher": int((diff > 0).sum()), "row_blank": int(diff.isna().sum())}
    EV["E2_direction_W22"] = dirs
    print("E2 direction:", dirs)
    # the excluded referee_contradicts matches: what the referee read
    rc = d[d["cls"].eq("referee_contradicts")]
    keep = ["year", "code", "side", "name"] + [f"{p_}_{k}" for k in SIX for p_ in ("raw", "off")] + \
        ["cv_svpt", "cv_first_in", "cv_first_won", "cv_second_won", "cv_ace", "cv_df", "mcp_svpt", "mcp_first_in",
         "mcp_first_won", "mcp_second_won", "mcp_ace", "mcp_df"]
    rc_rows = rc[rc[[f"chg_{k}" for k in SIX]].astype(str).eq("True").any(axis=1)][keep]
    rc_rows.to_csv(HERE / "referee_contradicts_rows.csv", index=False)
    # all referee reads (any group) on changing counts, including the excluded matches
    pa = d[d["group_id"].eq("W22") & d["cls"].isin(["proposed", "referee_contradicts"])]
    allr = {}
    for k in SIX:
        allr[k] = {f"{r}_{x}": int((pa[f"{r}_{x}_{k}"].astype(str).eq("True") &
                                    (pa["year"].eq(2022) if r == "cv" else True)).sum())
                   for r in ("cv", "mcp") for x in ("rg", "row")}
    EV["E2_including_excluded_W22"] = allr
    print("E2 including the excluded matches (W22):\n", pd.DataFrame(allr).T.to_string())

    # ---------------- E3: service games of proposed rows
    p = d[d["group_id"].isin(["W22", "W26"]) & d["cls"].eq("proposed")]
    EV["E3_sv_from"] = p.groupby("group_id")["sv_from"].value_counts().unstack(fill_value=0).to_dict("index")
    # rows where MatchBeats (or my derived count) changes Sackmann's count in 2022-2025
    q = p[p["group_id"].eq("W22")]
    chg = q[q["raw_sv_gms"].notna() & ~q["raw_sv_gms"].eq(q["off_sv_gms"])]
    tot_off = q.groupby("rid")["off_sv_gms"].transform("sum")
    fits = (tot_off - (q["games"] - q["std_tb"])).abs().le(0)
    EV["E3_W22_changed_sv"] = {"rows": int(len(chg)), "fit_score_exactly": int(fits.loc[chg.index].sum()),
                               "mb_count_equals_mine": int(chg["mb_sv_gms_reg_done"].eq(chg["off_sv_gms"]).sum())}
    print("E3 sv_from:", EV["E3_sv_from"], "| W22 rows whose service games change:", EV["E3_W22_changed_sv"])
    ex = chg[chg["name"].str.contains("Nakashima|Gojo|Kovalik", regex=True)]
    print(ex[["year", "code", "side", "name", "row_score", "games", "std_tb", "raw_sv_gms", "mb_sv_gms_reg_done",
              "der_sv", "off_sv_gms", "sv_from"]].to_string())
    print("all W22 proposed rows whose service games change:")
    print(chg[["year", "code", "side", "name", "row_score", "games", "std_tb", "raw_sv_gms", "mb_sv_gms_reg_done",
               "der_sv", "off_sv_gms", "sv_from"]].to_string())
    # matches whose service games are not derived
    print("proposed rows not derived:")
    print(p[p["sv_from"].ne("derived")][["year", "code", "side", "name", "row_score", "raw_sv_gms",
                                         "mb_sv_gms_reg_done", "mbf_points", "mb_svpt", "off_svpt", "sv_from",
                                         "off_sv_gms"]].to_string())

    # ---------------- E4: RG 2026 in Stage 0 today
    sm = pd.read_parquet(WORK / "stage0_rg_matches.parquet")
    sp = pd.read_parquet(WORK / "stage0_rg_match_players.parquet")
    s26 = sm[sm["year"].eq(2026) & sm["tournament_id"].eq("2026-520")]
    def flat(s: pd.Series) -> dict:
        return {"|".join(map(str, k)) if isinstance(k, tuple) else str(k): int(v) for k, v in s.items()}
    e4 = {"matches": flat(s26.groupby(["tour", "qualifying", "source"]).size()),
          "with_box": flat(s26.groupby(["tour", "qualifying"])["has_box"].sum())}
    q26 = s26[s26["qualifying"] & s26["tour"].eq("atp")]
    pl = sp[sp["match_id"].isin(set(q26["match_id"]))]
    e4["qual_player_rows_with_sv_gms_in_stage0"] = int(pl["sv_gms"].notna().sum())
    e4["qual_matches_without_box"] = int((~q26["has_box"]).sum())
    tq = d[d["year"].eq(2026) & d["source"].eq("tml")]
    e4["tml_player_rows"] = int(len(tq))
    e4["tml_sv_gms_zero"] = int(tq["raw_sv_gms"].eq(0).sum())
    e4["tml_sv_gms_blank"] = int(tq["raw_sv_gms"].isna().sum())
    both = tq[tq["raw_svpt"].notna() & tq["off_svpt"].notna()]
    e4["tml_rows_with_both"] = int(len(both))
    for k in ("svpt", "first_in", "ace", "df", "first_won", "second_won"):
        diff = (both[f"raw_{k}"] - both[f"off_{k}"]).abs()
        e4[f"tml_{k}_equal_pct"] = pct((diff == 0).sum(), len(both))
        e4[f"tml_{k}_within1_pct"] = pct((diff <= 1).sum(), len(both))
    e4["pooled_first_in_tml_pct"] = round(100 * both["raw_first_in"].sum() / both["raw_svpt"].sum(), 2)
    e4["pooled_first_in_rg_pct"] = round(100 * both["off_first_in"].sum() / both["off_svpt"].sum(), 2)
    # TML's main-draw rows (not in Stage 0) against RG, for the record
    ref = pd.read_parquet(WORK / "sides.parquet")
    ref = ref[ref["label"].eq("tml_2026_main_reference")]
    rb = ref[ref["raw_svpt"].notna() & ref["off_svpt"].notna()]
    e4["tml_main_reference_rows"] = int(len(rb))
    e4["tml_main_first_in_equal_pct"] = pct((rb["raw_first_in"] == rb["off_first_in"]).sum(), len(rb))
    e4["tml_main_pooled_first_in_pct"] = {t: round(100 * g["raw_first_in"].sum() / g["raw_svpt"].sum(), 2)
                                          for t, g in rb.groupby("tour")}
    e4["rg_main_pooled_first_in_pct"] = {t: round(100 * g["off_first_in"].sum() / g["off_svpt"].sum(), 2)
                                         for t, g in rb.groupby("tour")}
    e4["women_qual_in_stage0"] = int((s26["qualifying"] & s26["tour"].eq("wta")).sum())
    EV["E4"] = e4
    print("E4:", json.dumps(e4))

    # ---------------- E5 / RGX: the four exchanged boxes
    s0 = pd.read_parquet(WORK / "stage0_rg_rows.parquet")
    rgx = m[m["year"].le(2021) & m["cls"].eq("proposed")]
    out = []
    for r in rgx.itertuples():
        sw = d[(d["rid"] == r.rid) & (d["side"] == "w")].iloc[0]
        sl = d[(d["rid"] == r.rid) & (d["side"] == "l")].iloc[0]
        row = s0[s0["rid"].eq(r.rid)].iloc[0]
        rec = {"year": r.year, "code": r.code, "round": r.round, "source_file": r.source_file,
               "source_row": int(r.source_row), "winner_name": row["winner_name"], "loser_name": row["loser_name"],
               "row_score": r.row_score, "rg_games_winner_view": sw.get("rg_games", ""),
               "rg_winner": sw["rg_name"], "winner_id": row["winner_id"], "loser_id": row["loser_id"],
               "winner_seed": row["winner_seed"], "loser_seed": row["loser_seed"],
               "winner_rank": row["winner_rank"], "loser_rank": row["loser_rank"]}
        eq_as = eq_x = True
        for k in EIGHT:
            rec[f"raw_w_{k}"], rec[f"raw_l_{k}"] = sw[f"raw_{k}"], sl[f"raw_{k}"]
            rec[f"rg_w_{k}"], rec[f"rg_l_{k}"] = sw[f"off_{k}"], sl[f"off_{k}"]
            eq_as &= sw[f"raw_{k}"] == sw[f"off_{k}"] and sl[f"raw_{k}"] == sl[f"off_{k}"]
            eq_x &= sw[f"raw_{k}"] == sl[f"off_{k}"] and sl[f"raw_{k}"] == sw[f"off_{k}"]
        rec["equal_as_recorded"], rec["equal_exchanged"] = bool(eq_as), bool(eq_x)
        rec["raw_w_sv_gms"], rec["raw_l_sv_gms"] = sw["raw_sv_gms"], sl["raw_sv_gms"]
        rec["mb_w_sv_gms"], rec["mb_l_sv_gms"] = sw["mb_sv_gms_reg_done"], sl["mb_sv_gms_reg_done"]
        rec["der_w_sv_gms"], rec["der_l_sv_gms"] = sw["der_sv"], sl["der_sv"]
        rec["mb_w_svpt"], rec["mb_l_svpt"] = sw["mb_svpt"], sl["mb_svpt"]
        rec["mb_w_first_in"], rec["mb_l_first_in"] = sw["mb_first_in"], sl["mb_first_in"]
        rec["mb_w_ace"], rec["mb_l_ace"] = sw["mb_ace"], sl["mb_ace"]
        # who played the next round: the row's winner or loser, in Sackmann's rows and RG's documents
        nxt = {"R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F"}[r.round]
        later = s0[s0["source"].eq("sackmann") & s0["tid"].eq(r.tid) & s0["round"].eq(nxt)]
        rec["next_round_has_winner_id"] = bool(((later["winner_id"] == row["winner_id"]) |
                                                (later["loser_id"] == row["winner_id"])).any())
        rec["next_round_has_loser_id"] = bool(((later["winner_id"] == row["loser_id"]) |
                                               (later["loser_id"] == row["loser_id"])).any())
        ad = api[api["year"].eq(r.year) & api["round"].eq(nxt) & api["family"].eq(r.code[:2])]
        rec["rg_next_round_has_rg_winner"] = bool(ad["player_id"].eq(str(sw["rg_id"])).any())
        rec["rg_next_round_has_rg_loser"] = bool(ad["player_id"].eq(str(sl["rg_id"])).any())
        out.append(rec)
    x = pd.DataFrame(out)
    links = pd.read_csv(HERE / "links.csv")
    x = x.merge(links[links["state"].eq("paired")][["year", "code", "rg_games", "games_agree", "winner_agrees",
                                                      "sim_w", "sim_l"]], on=["year", "code"], how="left")
    x.to_csv(HERE / "rgx.csv", index=False)
    print("RGX:\n", x.T.to_string())
    EV["E5_RGX"] = x[["year", "code", "winner_name", "loser_name", "equal_as_recorded", "equal_exchanged",
                      "raw_w_sv_gms", "raw_l_sv_gms", "der_w_sv_gms", "der_l_sv_gms", "next_round_has_winner_id",
                      "next_round_has_loser_id", "rg_next_round_has_rg_winner", "rg_next_round_has_rg_loser",
                      "games_agree", "winner_agrees", "source_file", "source_row"]].to_dict("records")

    # ---------------- E7: round 1's confirmed split rows inside the proposed overrides
    cc = pd.read_csv(ROOT / "data" / "studies" / "rg_first_serve_recount" / "confirmed" / "confirmed_corrections.csv")
    cc = cc[cc["fix"].str.startswith("RG")]
    pm = m[m["cls"].eq("proposed")][["rid", "source_file", "source_row"]]
    inside = cc.merge(pm, on=["source_file", "source_row"], how="left")
    same = 0
    for r in inside[inside["rid"].notna()].itertuples():
        ok = True
        for side in ("w", "l"):
            given = getattr(r, f"{side}_1stIn")
            if pd.isna(given):
                continue
            s = d[(d["rid"] == r.rid) & (d["side"] == side)].iloc[0]
            ok &= (given == s["off_first_in"] and getattr(r, f"{side}_1stWon") == s["off_first_won"]
                   and getattr(r, f"{side}_2ndWon") == s["off_second_won"])
        same += ok
    EV["E7_round1_rows"] = {"rg_rows": int(len(cc)), "inside_proposed": int(inside["rid"].notna().sum()),
                            "same_split": int(same),
                            "outside": inside[inside["rid"].isna()][["source_file", "source_row", "winner_name",
                                                                     "loser_name"]].to_dict("records")}
    print("E7 round 1 rows:", {k: v for k, v in EV["E7_round1_rows"].items() if k != "outside"})
    out_rows = inside[inside["rid"].isna()].merge(
        m[["source_file", "source_row", "cls", "code", "year"]], on=["source_file", "source_row"], how="left")
    print(out_rows[["year", "code", "winner_name", "loser_name", "cls"]].to_string())

    # ---------------- E7: pooled first serves in after the overrides, by edition and draw
    dd = d[d["year"].between(2022, 2026)].copy()
    use_off = dd["cls"].eq("proposed")
    dd["new_first_in"] = np.where(use_off, dd["off_first_in"], dd["raw_first_in"])
    dd["new_svpt"] = np.where(use_off, dd["off_svpt"], dd["raw_svpt"])
    okb = dd["new_svpt"].notna() & dd["new_first_in"].notna()
    pooled = dd[okb].groupby(["year", "tour", "draw"]).agg(new_fi=("new_first_in", "sum"), new_sv=("new_svpt", "sum"))
    a = api[api["has_stats"]].copy()
    a["tour"] = np.where(a["family"].isin(["SM", "QM"]), "atp", "wta")
    a["draw"] = np.where(a["family"].str.startswith("Q"), "qual", "main")
    rgp = a[a["year"].ge(2022)].groupby(["year", "tour", "draw"]).agg(rg_fi=("first_in", "sum"), rg_sv=("svpt", "sum"))
    raw = dd[dd["raw_svpt"].notna()].groupby(["year", "tour", "draw"]).agg(raw_fi=("raw_first_in", "sum"),
                                                                         raw_sv=("raw_svpt", "sum"))
    pr = pooled.join(rgp).join(raw)
    pr["after_pct"] = (100 * pr["new_fi"] / pr["new_sv"]).round(2)
    pr["rg_pct"] = (100 * pr["rg_fi"] / pr["rg_sv"]).round(2)
    pr["before_pct"] = (100 * pr["raw_fi"] / pr["raw_sv"]).round(2)
    pr.to_csv(HERE / "pooled_after.csv")
    print("pooled first serves in (before / after / RG's own):\n", pr[["before_pct", "after_pct", "rg_pct"]].to_string())
    EV["E7_pooled"] = pr[["before_pct", "after_pct", "rg_pct"]].reset_index().to_dict("records")

    def keys_to_str(o):
        if isinstance(o, dict):
            return {("|".join(map(str, k)) if isinstance(k, tuple) else str(k)): keys_to_str(v) for k, v in o.items()}
        if isinstance(o, list):
            return [keys_to_str(v) for v in o]
        return o
    (HERE / "evidence.json").write_text(json.dumps(keys_to_str(EV), indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
