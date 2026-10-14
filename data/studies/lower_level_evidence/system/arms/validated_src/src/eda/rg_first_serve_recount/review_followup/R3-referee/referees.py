"""R3-referee (follow-up), step 3: the independent records on every count, for Roland Garros 2019-2026.

One row per Stage 0 player row of RG 2019-2026 (Sackmann's rows; TML's men's qualifying of 2026), from
official_rows.csv (my parse: the raw row, RG's statistics, MatchBeats, key statistics, my values), with:
  CV   the Hawk-Eye Court Vision copy (2019-2024), recounted here from its point tables: serve points (rows other than
       'Faulty Serve'), first serves in (serve_num 1), points won on each serve, aces, double faults, service games
       (games of one server, is_tiebreak 0), break points faced (is_break_point on the player's serve) and saved.
       Joined on (year, RG code, RG player id).
  MCP  the Match Charting Project: the Overview totals (serve points, aces, double faults, first serves in, points
       won on each serve, break points faced and saved) and, from its points, the service games (games one player
       served outside a 6-6 tiebreak). Linked here to the raw rows by year, tour, round and both names.
  TML  Tennis My Life's own Roland-Garros rows (men's main draw and qualifying, 2019-2026): linked to RG's documents
       by my link (official.link), its two sides paired with RG's teams by name. A third record, not independent of
       the official feeds (its source is not documented here), so it is reported beside the referees, not as one.
Each record's accuracy is measured per count where the truth is not in dispute: player rows whose count is equal in
RG's statistics and the row (and in RG 2019-2021 the rows are RG's statistics). Then, on every count the proposal
changes, which value each record reads: RG's, the row's, or neither, by count, edition, sign and size, with a
likelihood ratio from the record's own error distribution and a mixture estimate of how often RG's value is the right
one.

Writes ref_rows.csv, ref_calibration.csv, ref_votes.csv, ref_votes_detail.csv, ref_summary.json into
data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/referees.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import official as OF  # noqa: E402
import r3f as F  # noqa: E402

COUNTS = ["svpt", "ace", "df", "first_in", "first_won", "second_won", "bp_faced", "bp_saved", "sv_gms"]
REFS = ["cv", "mcp", "tml"]


# ------------------------------------------------------------------------------------------------ player rows
def player_rows() -> pd.DataFrame:
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    # Stage 0's rows: Sackmann's, and TML's only where Sackmann holds none (RG 2026 qualifying); TML's 2026 main-draw
    # rows are dropped by Stage 0's link (Sackmann's blank rows take precedence) and serve only as a record here
    o = o[o["code"].notna() & ~(o["source"].eq("tml") & o["draw"].eq("main"))].copy()
    keep = ["source", "source_file", "source_row", "season", "tour", "draw", "round", "code", "score", "status",
            "court", "consistent_both", "mb_complete_both", "my_sv_from", "games", "std_tb", "winner_name", "loser_name"]
    rows = []
    for s, o_s, who in (("w", "l", "winner_name"), ("l", "w", "loser_name")):
        d = o[keep].copy()
        d["side"], d["player"] = s, o[who]
        d["rg_id"] = o[f"rg_{s}_id"].astype("Int64").astype(str)
        for c in COUNTS:
            d[f"raw_{c}"] = o[f"raw_{s}_{c}"]
            d[f"off_{c}"] = o[f"my_{s}_{c}"]
            d[f"mb_{c}"] = o.get(f"mb_{s}_{c}")
            d[f"ks_{c}"] = o.get(f"ks_{s}_{c}")
            d[f"opp_raw_{c}"] = o[f"raw_{o_s}_{c}"]
            d[f"opp_off_{c}"] = o[f"my_{o_s}_{c}"]
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------------------------------------ Court Vision
def cv_counts() -> pd.DataFrame:
    rows = []
    for f in sorted((F.DUMP / "slam_ball_tracking" / "points").glob("RG_*.parquet")):
        year = int(f.stem.split("_")[1])
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "set_num", "game_num", "serve_num", "server_id",
                                         "point_winner_id", "point_end_type", "is_break_point", "is_tiebreak"])
        pt = pt.drop_duplicates(["match_id", "point_ID"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        pts = pt[~pt["point_end_type"].eq("Faulty Serve")].copy()
        pts["won"] = pts["point_winner_id"].astype(str).eq(pts["server_id"].astype(str))
        pts["bp"] = pts["is_break_point"].astype(str).str.lower().isin(["true", "1"])
        pts["tb"] = pts["is_tiebreak"].astype(str).isin(["1", "True", "true"])
        gsrv = pts.groupby(["code", "set_num", "game_num"])["server_id"].nunique()
        gtb = pts.groupby(["code", "set_num", "game_num"])["tb"].any()
        g1 = (gsrv.eq(1) & ~gtb).rename("one")
        pts = pts.join(g1, on=["code", "set_num", "game_num"])
        for (code, sid), g in pts.groupby(["code", "server_id"]):
            n = g["serve_num"].astype(str)
            rows.append({"year": year, "code": code, "rg_id": str(sid).replace(".0", ""), "cv_svpt": len(g),
                         "cv_first_in": int(n.eq("1").sum()), "cv_first_won": int((n.eq("1") & g["won"]).sum()),
                         "cv_second_won": int((n.eq("2") & g["won"]).sum()),
                         "cv_ace": int(g["point_end_type"].eq("Ace").sum()),
                         "cv_df": int(g["point_end_type"].eq("DoubleFault").sum()),
                         "cv_bp_faced": int(g["bp"].sum()), "cv_bp_saved": int((g["bp"] & g["won"]).sum()),
                         "cv_sv_gms": int(g.loc[g["one"].fillna(False), ["set_num", "game_num"]].drop_duplicates().shape[0])})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ MCP
def mcp_table() -> pd.DataFrame:
    base = F.DUMP / "match_charting_project"
    frames = []
    for g in ("m", "w"):
        ov = pd.read_parquet(base / "stats" / f"charting-{g}-stats-Overview.parquet")
        ov = ov[ov["set"].astype(str).eq("Total")].copy()
        mm = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        ov = ov.merge(mm[["match_id", "Player 1", "Player 2", "Date", "Tournament", "Round"]], on="match_id", how="left")
        ov["tour"] = "atp" if g == "m" else "wta"
        pts = pd.concat([pd.read_parquet(f) for f in sorted((base / "points").glob(f"charting-{g}-points-20*.parquet"))],
                        ignore_index=True)
        ids = set(ov.loc[ov["Tournament"].astype(str).str.contains("Roland", case=False), "match_id"])
        pts = pts[pts["match_id"].isin(ids)].copy()
        for c in ["Set1", "Set2", "Gm1", "Gm2", "Svr"]:
            pts[c] = pd.to_numeric(pts[c], errors="coerce")
        tbset = pts["TbSet"].astype(str).str.lower().isin(["true", "1"])
        pts["tb"] = tbset & pts["Gm1"].eq(6) & pts["Gm2"].eq(6)
        pts["set_i"], pts["game_i"] = pts["Set1"] + pts["Set2"], pts["Gm1"] + pts["Gm2"]
        gm = pts[~pts["tb"]].groupby(["match_id", "set_i", "game_i"])["Svr"].agg(["nunique", "first"]).reset_index()
        gm = gm[gm["nunique"].eq(1)]
        sv = gm.groupby(["match_id", "first"]).size().rename("sv_gms").reset_index()
        sv = sv.merge(mm[["match_id", "Player 1", "Player 2"]], on="match_id")
        sv["player"] = np.where(sv["first"].eq(1), sv["Player 1"], sv["Player 2"])
        ov = ov.merge(sv[["match_id", "player", "sv_gms"]], on=["match_id", "player"], how="left")
        frames.append(ov)
    o = pd.concat(frames, ignore_index=True)
    o["year"] = pd.to_numeric(o["Date"].astype(str).str[:4], errors="coerce")
    o = o[o["Tournament"].astype(str).str.contains("Roland", case=False) & o["year"].between(2019, 2026)].copy()
    o["Round"] = o["Round"].astype(str).str.strip()
    for c in ["serve_pts", "aces", "dfs", "first_in", "first_won", "second_won", "bk_pts", "bp_saved", "sv_gms"]:
        o[c] = pd.to_numeric(o[c], errors="coerce")
    return o


def mcp_link(P: pd.DataFrame) -> pd.DataFrame:
    o = mcp_table()
    matches = P[P["side"].eq("w")]
    groups = {k: g for k, g in matches.groupby(["season", "tour", "round"])}
    rows = []
    for mid, g in o.groupby("match_id"):
        r0 = g.iloc[0]
        cand = groups.get((int(r0["year"]), r0["tour"], r0["Round"]))
        if cand is None:
            continue
        best = []
        for x in cand.itertuples():
            for p1_is_w in (True, False):
                a = F.name_ok(r0["Player 1"], x.winner_name if p1_is_w else x.loser_name)
                b = F.name_ok(r0["Player 2"], x.loser_name if p1_is_w else x.winner_name)
                if min(a, b) >= 1:
                    best.append(((min(a, b), a + b), x, p1_is_w))
        if not best:
            continue
        best.sort(key=lambda z: z[0], reverse=True)
        if len(best) > 1 and best[0][0] == best[1][0]:
            continue
        _, x, p1_is_w = best[0]
        for _, pr in g.iterrows():
            side = "w" if ((pr["player"] == r0["Player 1"]) == p1_is_w) else "l"
            rows.append({"source_file": x.source_file, "source_row": int(x.source_row), "side": side, "mcp_id": mid,
                         "mcp_svpt": pr["serve_pts"], "mcp_ace": pr["aces"], "mcp_df": pr["dfs"],
                         "mcp_first_in": pr["first_in"], "mcp_first_won": pr["first_won"],
                         "mcp_second_won": pr["second_won"], "mcp_bp_faced": pr["bk_pts"],
                         "mcp_bp_saved": pr["bp_saved"], "mcp_sv_gms": pr["sv_gms"]})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ TML
def tml_rows(docs: pd.DataFrame) -> pd.DataFrame:
    raw = pd.read_parquet(F.OUT / "sub_raw.parquet")
    raw = raw[raw["source"].eq("tml") & raw["tid"].str.fullmatch(r"20(19|2[0-6])-520")].copy()
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("int64")
    raw["season"] = pd.to_numeric(raw["season"]).astype("int64")
    L = OF.link(raw, docs)
    L = L[L["code"].notna() & L["link"].eq("names")]
    rk = raw.set_index(["_source_file", "_row"])
    out = []
    for r in L.itertuples():
        x = rk.loc[(r.source_file, r.source_row)]
        if isinstance(x, pd.DataFrame):
            x = x.iloc[0]
        for s, team in (("w", r.w_team), ("l", "B" if r.w_team == "A" else "A")):
            rec = {"year": int(r.season), "code": r.code, "team": team, "tml_file": r.source_file,
                   "tml_row": int(r.source_row)}
            for c, col in F.NINE.items():
                rec[f"tml_{c}"] = pd.to_numeric(str(x[f"{s}_{col}"]).strip() if x[f"{s}_{col}"] is not None else "",
                                                errors="coerce")
            out.append(rec)
    t = pd.DataFrame(out)
    ids = pd.concat([docs[["year", "code", "A_rg_id"]].rename(columns={"A_rg_id": "rg_id"}).assign(team="A"),
                     docs[["year", "code", "B_rg_id"]].rename(columns={"B_rg_id": "rg_id"}).assign(team="B")])
    ids["rg_id"] = pd.to_numeric(ids["rg_id"], errors="coerce").astype("Int64").astype(str)
    t = t.merge(ids, on=["year", "code", "team"], how="left")
    return t.drop_duplicates(["year", "code", "rg_id"])


# ------------------------------------------------------------------------------------------------ tests
def full_mask(D: pd.DataFrame, ref: str) -> pd.Series:
    """The record holds every point of the player row: its serve points equal RG's or the row's."""
    return D[f"{ref}_svpt"].notna() & (D[f"{ref}_svpt"].eq(D["off_svpt"]) | D[f"{ref}_svpt"].eq(D["raw_svpt"]))


def pmf(errors: np.ndarray, alpha: float = 1.0):
    errors = np.asarray(errors, dtype=float)
    b = max(np.mean(np.abs(errors)), 0.5)
    vals, cnt = np.unique(errors, return_counts=True)
    emp = dict(zip(vals.astype(int), cnt))
    n = len(errors)

    def f(k):
        lap = np.exp(-abs(int(k)) / b) * (1 - np.exp(-1 / b)) / (1 + np.exp(-1 / b))
        return (emp.get(int(k), 0) + alpha * lap) / (n + alpha)
    return f


def mixture(lo: np.ndarray, ls: np.ndarray) -> float:
    """EM estimate of the share of rows whose RG value is right, from per-row likelihoods under the two hypotheses."""
    if len(lo) == 0:
        return float("nan")
    pi = 0.5
    for _ in range(200):
        r = pi * lo / (pi * lo + (1 - pi) * ls)
        pi = float(np.mean(r))
    return pi


def main() -> int:
    P = player_rows()
    docs = OF.rg_docs()
    cv = cv_counts()
    cv["year"] = cv["year"].astype(int)
    P = P.merge(cv, left_on=["season", "code", "rg_id"], right_on=["year", "code", "rg_id"], how="left").drop(columns="year")
    M = mcp_link(P)
    P = P.merge(M, on=["source_file", "source_row", "side"], how="left")
    T = tml_rows(docs)
    P = P.merge(T.drop(columns=["team"]), left_on=["season", "code", "rg_id"], right_on=["year", "code", "rg_id"],
                how="left").drop(columns="year")
    # the lead's classes (by source file and row)
    wb = pd.read_csv(F.FOLLOW / "whole_box_rows.csv", low_memory=False)
    wb["key"] = F.rowkey(wb["source_file"], wb["source_row"]) + "|" + wb["raw_side"].astype(str)
    P["key"] = F.rowkey(P["source_file"], P["source_row"]) + "|" + P["side"]
    P = P.merge(wb[["key", "cls", "changes", "referee_against"]].rename(columns={"cls": "lead_cls"}), on="key", how="left")
    P.to_csv(F.OUT / "ref_rows.csv", index=False)

    # ---------------------------------------------------------------- calibration: where the count is not in dispute
    cal_rows = []
    cal_err: dict = {}
    sets = {"RG 2019-2021": P["season"].between(2019, 2021), "RG 2022-2025": P["season"].between(2022, 2025),
            "RG 2026": P["season"].eq(2026)}
    for ref in REFS:
        full = full_mask(P, ref)
        for name, sel in sets.items():
            for c in COUNTS:
                base = sel & full & P[f"raw_{c}"].eq(P[f"off_{c}"]) & P[f"{ref}_{c}"].notna()
                if c != "svpt":
                    base &= P[f"{ref}_svpt"].eq(P["off_svpt"])
                e = (P.loc[base, f"{ref}_{c}"] - P.loc[base, f"off_{c}"]).to_numpy(float)
                if name != "RG 2026":
                    cal_err[(ref, c, name)] = e
                for yr in ([None] + (list(range(2019, 2022)) if name == "RG 2019-2021" else
                                     list(range(2022, 2026)) if name == "RG 2022-2025" else [])):
                    ee = e if yr is None else (P.loc[base & P["season"].eq(yr), f"{ref}_{c}"]
                                               - P.loc[base & P["season"].eq(yr), f"off_{c}"]).to_numpy(float)
                    cal_rows.append({"record": ref, "set": name if yr is None else str(yr), "count": c,
                                     "rows": len(ee), "exact": round(float(np.mean(ee == 0)), 3) if len(ee) else None,
                                     "within_1": round(float(np.mean(np.abs(ee) <= 1)), 3) if len(ee) else None,
                                     "mean_error": round(float(np.mean(ee)), 2) if len(ee) else None})
    # serve points as each record holds them, on every linked row (calibration of the 'holds every point' test)
    for ref in REFS:
        for name, sel in sets.items():
            base = sel & P[f"{ref}_svpt"].notna() & P["raw_svpt"].eq(P["off_svpt"])
            e = (P.loc[base, f"{ref}_svpt"] - P.loc[base, "off_svpt"]).to_numpy(float)
            cal_rows.append({"record": ref, "set": name, "count": "svpt (all linked rows)", "rows": len(e),
                             "exact": round(float(np.mean(e == 0)), 3) if len(e) else None,
                             "within_1": round(float(np.mean(np.abs(e) <= 1)), 3) if len(e) else None,
                             "mean_error": round(float(np.mean(e)), 2) if len(e) else None})
            cal_err[(ref, "svpt", name)] = e
    cal = pd.DataFrame(cal_rows)
    cal.to_csv(F.OUT / "ref_calibration.csv", index=False)

    # ---------------------------------------------------------------- votes on the counts that change
    D = P[P["season"].between(2022, 2026) & P["lead_cls"].isin(["proposed", "referee_contradicts", "statistics_short"])].copy()
    det = []
    for ref in REFS:
        full = full_mask(D, ref)
        for c in COUNTS:
            ch = D[f"raw_{c}"].notna() & D[f"off_{c}"].notna() & D[f"raw_{c}"].ne(D[f"off_{c}"])
            hold = D[f"{ref}_svpt"].notna() if c == "svpt" else full
            h = D[ch & hold & D[f"{ref}_{c}"].notna()].copy()
            if h.empty:
                continue
            h["record"], h["count"] = ref, c
            h["d"] = h[f"raw_{c}"] - h[f"off_{c}"]
            h["ref_value"] = h[f"{ref}_{c}"]
            h["vote"] = np.select([h["ref_value"].eq(h[f"off_{c}"]), h["ref_value"].eq(h[f"raw_{c}"])],
                                  ["RG", "row"], "neither")
            cname = "RG 2019-2021"   # calibrate on the clean editions (RG = Sackmann there)
            e = cal_err.get((ref, c, cname), np.array([]))
            if len(e) < 30:
                e = np.concatenate([e, cal_err.get((ref, c, "RG 2022-2025"), np.array([]))])
            f = pmf(e) if len(e) else None
            if f is not None:
                h["lik_RG"] = [f(v - o) for v, o in zip(h["ref_value"], h[f"off_{c}"])]
                h["lik_row"] = [f(v - o) for v, o in zip(h["ref_value"], h[f"raw_{c}"])]
                h["log10_LR_RG_vs_row"] = np.log10(h["lik_RG"]) - np.log10(h["lik_row"])
            det.append(h[["record", "count", "season", "tour", "draw", "round", "code", "player", "side", "source_file",
                          "source_row", "lead_cls", f"raw_{c}", f"off_{c}", "ref_value", "d", "vote"]
                         + (["lik_RG", "lik_row", "log10_LR_RG_vs_row"] if f is not None else [])]
                       .rename(columns={f"raw_{c}": "row_value", f"off_{c}": "rg_value"}))
    det = pd.concat(det, ignore_index=True)
    # Court Vision is a referee on every count in 2022, and in 2023-2024 only on the counts it records exactly where
    # the truth is not disputed (serve points, aces, service games, break points; not double faults or the split);
    # TML copies one of the two records (Sackmann's main draw, RG's qualifying) and is never a referee
    det["valid_referee"] = (det["record"].eq("mcp")
                            | (det["record"].eq("cv") & det["season"].eq(2022))
                            | (det["record"].eq("cv") & det["season"].isin([2023, 2024])
                               & det["count"].isin(["svpt", "ace", "sv_gms", "bp_faced", "bp_saved"])))
    det["size"] = np.where(det["d"].abs().le(1), "|d|=1", np.where(det["d"].abs().le(3), "|d|=2-3", "|d|>=4"))
    det["sign"] = np.where(det["d"].gt(0), "row higher", "row lower")
    det.to_csv(F.OUT / "ref_votes_detail.csv", index=False)
    agg = []
    dv = det[det["valid_referee"]].copy()
    dv["record"] = "referees (CV where reliable, MCP)"
    for keys in (["record", "lead_cls", "count"], ["record", "lead_cls", "count", "size"],
                 ["record", "lead_cls", "count", "sign"], ["record", "lead_cls", "count", "season"]):
        for k, g in pd.concat([det[det["valid_referee"] | det["record"].eq("tml")], dv]).groupby(keys):
            rec = dict(zip(keys, k if isinstance(k, tuple) else (k,)))
            rec.update({"rows": len(g), "RG": int(g["vote"].eq("RG").sum()), "row": int(g["vote"].eq("row").sum()),
                        "neither": int(g["vote"].eq("neither").sum())})
            if "lik_RG" in g and g["lik_RG"].notna().all():
                rec["log10_LR_RG_vs_row"] = round(float(g["log10_LR_RG_vs_row"].sum()), 1)
                rec["share_RG_right_mixture"] = round(mixture(g["lik_RG"].to_numpy(float), g["lik_row"].to_numpy(float)), 3)
            agg.append(rec)
    votes = pd.DataFrame(agg)
    votes.to_csv(F.OUT / "ref_votes.csv", index=False)
    smry = {"player_rows": int(len(P)),
            "linked": {r: int(P[f"{r}_svpt"].notna().sum()) for r in REFS},
            "linked_2022_2026_by_season": {r: P[P[f"{r}_svpt"].notna()].groupby("season").size().to_dict() for r in REFS},
            "calibration_exact_2019_2021": cal[cal["set"].eq("RG 2019-2021")].pivot(index="count", columns="record",
                                                                                  values="exact").to_dict()}
    (F.OUT / "ref_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    print(json.dumps(smry, indent=1, default=str))
    print(cal[cal["set"].isin(["RG 2019-2021", "RG 2022-2025", "RG 2026", "2022", "2023", "2024"])]
          .pivot_table(index=["record", "count"], columns="set", values="exact").to_string())
    print(votes[votes.columns[:12]][votes["size"].isna() & votes["sign"].isna() & votes["season"].isna()].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
