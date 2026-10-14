"""R1-rederive (round 2): my classes of every Stage 0 match of Roland Garros 2019-2026, and my override values.

Inputs (all mine): work/sides.parquet (link_rows.py), links.csv, work/referees.parquet (referees.py),
work/stage0_rg_rows.parquet (stage0_rows.py). The score parser and status rules are Stage 0's own
(stage0_build.tokens_of, status_of, score_counts); the box checks B0-B9 are re-implemented here as Stage 0 states them.

The override box of a match: RG's statistics for the eight counts (ace, df, svpt, 1stIn, 1stWon, 2ndWon, bpSaved,
bpFaced), oriented to the raw row's winner and loser; service games (tiebreak games not counted, unfinished game of a
retirement not counted: Sackmann's convention, measured in sides.parquet) from, in order:
  derived    RG's score and MatchBeats' first server, where MatchBeats' server agrees with the alternation on every
             game it holds (der_ok);
  mb         MatchBeats' own count, where its regular games cover the score's;
  row        the row's own count, where it fits the score (Stage 0's B5);
  blank      none of these.

Classes of a match (the first that applies), as the brief lists them, computed my way:
  walkover; identity (a player of the row is not RG's player: the link pairs the match, a name does not);
  record_fails_checks; equal (all eight counts equal for both players); statistics_short (MatchBeats holds more serve
  points than RG's statistics for a player); mb_contradicts (MatchBeats or the key statistics hold every point of
  both players and give another split, aces or double faults); referee_contradicts (Court Vision 2019/2020/2022 or a
  hand chart, holding every point of the player, reads the row's value on a count that changes);
  fails_stage0_checks (the official box fails B0-B4 or B6-B9 under the row's score); proposed.

Writes: matches.csv (one row per match), sides.csv (one row per player row, every source), and
        my_overrides.csv (the proposed matches, in overrides_scope.csv's columns).
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/classify.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402  (Stage 0's score parser only)

HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]
SIX = ["svpt", "ace", "df", "first_in", "first_won", "second_won"]
OUT_NAMES = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
             "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
IDENTITY_SLIPS = {(2024, "QM126")}     # Sackmann's "T. Farquhar" (atp 212408) is RG's Thomas Faurel (round 1, R1)
CV_YEARS = {2019, 2020, 2022}


def score_facts(score: str) -> dict:
    sets, marker = B.tokens_of(score)
    status = B.STATUS[B.status_of(sets, marker)]
    sw, sl, gw, gl, tw, tl, std_tb, *_ = B.score_counts(score, False)
    return {"status": status, "status_detail": B.status_of(sets, marker), "games": gw + gl, "std_tb": std_tb}


def box_checks(w: dict, l: dict, f: dict) -> dict:
    """Stage 0's B0-B9 (box_scores) on one match; w/l hold the nine counts. Returns the failed checks."""
    out = {}
    scored = f["status"] in ("completed", "retired", "other") and f["status_detail"] != "unknown"
    sv_w, sv_l = w["sv_gms"], l["sv_gms"]
    # C25: service games recorded as 0 with serve points played are treated as missing
    if (sv_w == 0 and w["svpt"] > 0) or (sv_l == 0 and l["svpt"] > 0):
        sv_w = sv_l = np.nan
    tot = sv_w + sv_l
    if scored and not np.isnan(tot):
        excl = abs(tot - (f["games"] - f["std_tb"])) <= 1
        incl = abs(tot - f["games"]) <= 1
        out["B5"] = not (excl or incl)
    else:
        out["B5"] = False
    if out["B5"]:
        sv_w = sv_l = np.nan
    for s, sv in ((w, sv_w), (l, sv_l)):
        vals = [s[k] for k in EIGHT] + [sv]
        out["B0"] = out.get("B0", False) or any((v is not None and not np.isnan(v) and v < 0) for v in vals)
        out["B1"] = out.get("B1", False) or s["first_in"] > s["svpt"]
        out["B2"] = out.get("B2", False) or s["first_won"] > s["first_in"]
        out["B3"] = out.get("B3", False) or s["second_won"] > s["svpt"] - s["first_in"]
        out["B4"] = out.get("B4", False) or s["bp_saved"] > s["bp_faced"]
        out["B6"] = out.get("B6", False) or s["df"] > s["svpt"] - s["first_in"]
        out["B7"] = out.get("B7", False) or s["ace"] > s["first_won"] + s["second_won"]
        out["B8"] = out.get("B8", False) or (not np.isnan(sv) and (s["bp_faced"] - s["bp_saved"]) > sv)
    played = (f["games"] - f["std_tb"]) - (0 if f["status"] == "completed" else 1)
    out["B9"] = bool(scored and (w["svpt"] + l["svpt"]) < B.MIN_POINTS_PER_GAME * played)
    return out


def main() -> None:
    d = pd.read_parquet(WORK / "sides.parquet")
    d = d[d["label"].eq("stage0")].copy()
    ref = pd.read_parquet(WORK / "referees.parquet")
    d = d.merge(ref.rename(columns={"player_id": "rg_id"}), on=["year", "code", "rg_id"], how="left")
    links = pd.read_csv(HERE / "links.csv")
    links = links[links["state"].eq("paired") & links["label"].eq("stage0")]
    s0 = pd.read_parquet(WORK / "stage0_rg_rows.parquet")
    s0 = s0[["rid", "tid", "wkey", "lkey", "ov_key", "ov_key_rows", "s0_match_id", "s0_has_box", "s0_box_status",
             "group", "winner_id", "loser_id"]]
    lk = links[["rid", "sim_w", "sim_l", "row_score", "rg_games", "games_agree", "rg_end_cause", "winner_agrees"]]
    d = d.merge(lk, on="rid", how="left").merge(s0, on="rid", how="left")

    # ---------------- per-match facts
    facts = {s: score_facts(s) for s in d["row_score"].fillna("").unique()}
    d["status"] = d["row_score"].fillna("").map(lambda s: facts[s]["status"])
    d["status_detail"] = d["row_score"].fillna("").map(lambda s: facts[s]["status_detail"])
    d["games"] = d["row_score"].fillna("").map(lambda s: facts[s]["games"])
    d["std_tb"] = d["row_score"].fillna("").map(lambda s: facts[s]["std_tb"])

    # service games: the chosen value and where it comes from
    reg_games = d["games"] - d["std_tb"]
    mb_tot = d.groupby("rid")["mb_sv_gms_reg_done"].transform("sum")
    mb_cover = d["mb_sv_gms_reg_done"].notna() & mb_tot.eq(reg_games)
    raw_tot = d.groupby("rid")["raw_sv_gms"].transform(lambda s: s.sum(min_count=2))
    row_fits = d["raw_sv_gms"].notna() & d["raw_sv_gms"].gt(0) & (
        (raw_tot - reg_games).abs().le(1) | (raw_tot - d["games"]).abs().le(1))
    der_ok = d["der_ok"].fillna(False).astype(bool) & d["der_sv"].notna()
    d["sv_from"] = np.select([der_ok, mb_cover, row_fits], ["derived", "mb", "row"], "blank")
    d["off_sv_gms"] = np.select([der_ok, mb_cover, row_fits], [d["der_sv"], d["mb_sv_gms_reg_done"], d["raw_sv_gms"]],
                                np.nan)
    # a match takes its service games from one rule for both players
    rule = d.groupby("rid")["sv_from"].agg(lambda s: s.iloc[0] if s.nunique() == 1 else "mixed")
    d["sv_from_match"] = d["rid"].map(rule)

    # comparisons per side
    for k in EIGHT:
        d[f"chg_{k}"] = ~(d[f"raw_{k}"].eq(d[f"off_{k}"]))
    d["chg_sv_gms"] = ~(d["raw_sv_gms"].eq(d["off_sv_gms"]) | (d["raw_sv_gms"].isna() & d["off_sv_gms"].isna()))
    d["eq8_side"] = ~d[[f"chg_{k}" for k in EIGHT]].any(axis=1)
    opp_svpt = d.groupby("rid")["off_svpt"].transform("sum") - d["off_svpt"]
    d["mb_full"] = d["mb_svpt"].eq(d["off_svpt"]) & d["mb_opp_svpt"].eq(opp_svpt)
    d["ks_full"] = d["ks_svpt"].eq(d["off_svpt"]) & d["ks_opp_svpt"].eq(opp_svpt)
    d["mb_differs"] = d["mb_full"] & ~(d["mb_first_in"].eq(d["off_first_in"]) & d["mb_first_won"].eq(d["off_first_won"])
                                       & d["mb_second_won"].eq(d["off_second_won"]) & d["mb_ace"].eq(d["off_ace"])
                                       & d["mb_df"].eq(d["off_df"]))
    d["ks_differs"] = d["ks_full"] & ~(d["ks_first_in"].eq(d["off_first_in"]) & d["ks_first_won"].eq(d["off_first_won"])
                                       & d["ks_second_won"].eq(d["off_second_won"]) & d["ks_ace"].eq(d["off_ace"])
                                       & d["ks_df"].eq(d["off_df"]))
    d["stat_short"] = d["mb_svpt"].gt(d["off_svpt"])
    # referees: held = the referee's serve points equal RG's (or, for serve points, the row's)
    for r, ok_year in (("cv", d["year"].isin(CV_YEARS)), ("mcp", pd.Series(True, index=d.index))):
        has = d[f"{r}_svpt"].notna() & ok_year
        if r == "cv":
            has &= d["cv_gap"].fillna(0).eq(0)
        held = has & d[f"{r}_svpt"].eq(d["off_svpt"])
        d[f"{r}_held"] = held
        reads_row = pd.Series(False, index=d.index)
        for k in SIX:
            ch = d[f"chg_{k}"]
            if k == "svpt":
                rr = has & ch & d[f"{r}_svpt"].eq(d["raw_svpt"])
                ro = has & ch & d[f"{r}_svpt"].eq(d["off_svpt"])
            else:
                rr = held & ch & d[f"{r}_{k}"].eq(d[f"raw_{k}"])
                ro = held & ch & d[f"{r}_{k}"].eq(d[f"off_{k}"])
            d[f"{r}_row_{k}"] = rr
            d[f"{r}_rg_{k}"] = ro
            d[f"{r}_held_{k}"] = (has if k == "svpt" else held) & ch
            reads_row |= rr
        d[f"{r}_reads_row"] = reads_row

    # ---------------- match level
    g = d.groupby("rid")
    m = g.agg(year=("year", "first"), tour=("tour", "first"), round=("round", "first"), code=("code", "first"),
              source=("source", "first"), group=("group", "first"), source_file=("source_file", "first"),
              source_row=("source_row", "first"), s0_match_id=("s0_match_id", "first"), ov_key=("ov_key", "first"),
              ov_key_rows=("ov_key_rows", "first"), tid=("tid", "first"), wkey=("wkey", "first"),
              lkey=("lkey", "first"), row_score=("row_score", "first"), status=("status", "first"),
              status_detail=("status_detail", "first"), rg_end_cause=("rg_end_cause", "first"),
              has_stats=("has_stats", "all"), rg_checks=("rg_checks", "all"), eq8=("eq8_side", "all"),
              stat_short=("stat_short", "any"), mb_differs=("mb_differs", "any"), ks_differs=("ks_differs", "any"),
              cv_reads_row=("cv_reads_row", "any"), mcp_reads_row=("mcp_reads_row", "any"),
              sv_from=("sv_from_match", "first"), s0_has_box=("s0_has_box", "first"),
              s0_box_status=("s0_box_status", "first"), games_agree=("games_agree", "first"),
              raw_blank=("raw_svpt", lambda s: s.isna().all())).reset_index()
    m["walkover"] = m["row_score"].fillna("").str.contains("W/O", case=False) | m["rg_end_cause"].fillna("").str.contains("w/o")
    m["identity"] = [(y, c) in IDENTITY_SLIPS for y, c in zip(m["year"], m["code"])]
    off8_present = d.groupby("rid")[[f"off_{k}" for k in EIGHT]].apply(lambda x: x.notna().all().all())
    m["off8_present"] = m["rid"].map(off8_present)
    # Stage 0's checks of the official box under the row's score
    wide = d.set_index(["rid", "side"])
    fails = {}
    for rid in m["rid"]:
        try:
            w, l = wide.loc[(rid, "w")], wide.loc[(rid, "l")]
        except KeyError:
            continue
        wv = {k: float(w[f"off_{k}"]) for k in EIGHT} | {"sv_gms": float(w["off_sv_gms"])}
        lv = {k: float(l[f"off_{k}"]) for k in EIGHT} | {"sv_gms": float(l["off_sv_gms"])}
        if any(np.isnan(wv[k]) or np.isnan(lv[k]) for k in EIGHT):
            continue
        f = {"status": w["status"], "status_detail": w["status_detail"], "games": w["games"], "std_tb": w["std_tb"]}
        fails[rid] = box_checks(wv, lv, f)
    fx = pd.DataFrame.from_dict(fails, orient="index")
    fx.index.name = "rid"
    m = m.merge(fx.add_prefix("off_").reset_index(), on="rid", how="left")
    m["off_fails"] = m[[f"off_B{i}" for i in (0, 1, 2, 3, 4, 6, 7, 8, 9)]].fillna(False).any(axis=1)
    m["cls"] = np.select(
        [m["walkover"], m["identity"], ~m["rg_checks"] | ~m["off8_present"], m["eq8"], m["stat_short"],
         m["mb_differs"] | m["ks_differs"], m["cv_reads_row"] | m["mcp_reads_row"], m["off_fails"]],
        ["walkover", "identity", "record_fails_checks", "equal", "statistics_short", "mb_contradicts",
         "referee_contradicts", "fails_stage0_checks"], "proposed")
    m["group_id"] = np.select([m["year"].le(2021), m["year"].le(2025)], ["control", "W22"], "W26")
    m["draw"] = np.where(m["round"].str.fullmatch(r"Q\d"), "qual", "main")
    m.to_csv(HERE / "matches.csv", index=False)
    d.to_csv(HERE / "sides.csv", index=False)

    # ---------------- my override rows (proposed matches)
    pm = m[m["cls"].eq("proposed")]
    rows = []
    for r in pm.itertuples():
        w, l = wide.loc[(r.rid, "w")], wide.loc[(r.rid, "l")]
        rec = {"feed_key": f"RG{r.year}|{r.code}", "stage0_match_id": r.s0_match_id, "group": r.group_id,
               "source": r.source, "tour": r.tour, "tid": r.tid, "round": r.round, "winner_key": r.wkey,
               "loser_key": r.lkey, "source_file": r.source_file, "source_row": r.source_row,
               "sv_gms_from": r.sv_from}
        for side, s in (("w", w), ("l", l)):
            for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"):
                v = s[f"off_{k}"]
                rec[f"{side}_{OUT_NAMES[k]}"] = "" if pd.isna(v) else int(v)
        rows.append(rec)
    ov = pd.DataFrame(rows)
    ov.to_csv(HERE / "my_overrides.csv", index=False)

    # ---------------- report
    pd.set_option("display.width", 250)
    print(pd.crosstab([m["group_id"], m["year"]], m["cls"], margins=True).to_string())
    w26 = m[m["group_id"].eq("W26")]
    print("\nW26 by draw and tour:\n", pd.crosstab([w26["tour"], w26["draw"]], w26["cls"]).to_string())
    print("\nservice games source, proposed matches:", pm.groupby("group_id")["sv_from"].value_counts().to_dict())
    print("proposed matches:", pm.groupby("group_id").size().to_dict(), "| override rows written:", len(ov))
    print("override keys unique in their source (raw rows):", bool(pm["ov_key_rows"].eq(1).all()))


if __name__ == "__main__":
    main()
