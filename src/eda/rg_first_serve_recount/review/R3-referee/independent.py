"""R3-referee, step 3: the independent records against Sackmann's rows and the official record.

Player rows: the lead's classification (proposed_rows.csv, control_2019_2021.csv) with Sackmann's raw counts and the
official record's; the official counts of every RG row are re-read here from the raw API files (r3common.rg_api_all)
and must equal the lead's.

  MCP   the Match Charting Project's per-player totals (Overview, set Total), linked here to the raw rows by tour,
        year, round and both names. Its error is measured where the truth is not in dispute (RG 2019-2021 rows whose
        official record equals Sackmann's; secondarily the 2022-2025 rows where they are equal). On the proposed rows,
        MCP's first serves in are compared with the official value (H_O: the official record is right) and with
        Sackmann's (H_S): exact agreement, which is closer, the counts each hypothesis predicts from MCP's own error
        distribution, and a log-likelihood ratio.
  CV    the Hawk-Eye Court Vision copy recounted here from its point tables (a 'Faulty Serve' row is a faulted first
        serve; a point is any other row; first serves in = points with serve_num 1). Reliability per edition: share
        of points played on a second serve against the official record, and exact agreement where the truth is not
        in dispute. On the proposed rows of reliable editions: the same tests as for MCP.
  SOFA  SofaScore's box scores (RG 2022-2025 main draw), linked by round and names: equal to Sackmann's or to the
        official record's?

Writes mcp_rows.csv, mcp_tests.csv, cv_reliability.csv, cv_rows.csv, cv_tests.csv, sofa_rows.csv, sofa_agreement.csv,
independent_summary.json in data/studies/rg_first_serve_recount/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/independent.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3common as C  # noqa: E402

OUT = C.OUT
MCP_ROUNDS = {"Q1", "Q2", "Q3", "R128", "R64", "R32", "R16", "QF", "SF", "F", "BR"}


# ------------------------------------------------------------------------------------------------ player table
def player_table() -> tuple[pd.DataFrame, dict]:
    d = C.lead_rows().copy()
    d = d.rename(columns={c: f"lead_{c}" for c in d.columns if c.split("_")[0] in ("mcp", "cv", "mb", "ks", "olp")})
    d["fix"] = np.where(d["proposal_class"].isin(["A", "B"]),
                        np.where(d["event"].eq("RG"), "RGFS", "OGFS") + d["proposal_class"].fillna(""), "")
    # the official counts of RG rows, re-read from the raw API files: the team whose name matches the player
    api = C.rg_api_all()
    ai = {(int(y), c): g for (y, c), g in api.groupby(["year", "code"])}
    chk = []
    for i, r in d[d["event"].eq("RG") & d["rg_code"].notna()].iterrows():
        g = ai.get((int(r["year"]), r["rg_code"]))
        if g is None:
            chk.append((i, None, "no file"))
            continue
        sc = [C.name_ok(n, r["player_name"]) for n in g["name"]]
        if max(sc) == 0 or sc[0] == sc[1]:
            chk.append((i, None, "names"))
            continue
        t = g.iloc[int(np.argmax(sc))]
        chk.append((i, t, "ok"))
    same = 0
    n = 0
    for i, t, why in chk:
        if t is None:
            continue
        n += 1
        d.loc[i, "my_rg_id"] = t["rg_id"]
        d.loc[i, "my_consistent"] = bool(t["consistent_both"])
        eq = all((pd.isna(d.loc[i, f"off_{c}"]) and (t[c] is None or pd.isna(t[c]))) or d.loc[i, f"off_{c}"] == t[c]
                 for c in ["svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved"])
        same += eq
    info = {"rg_player_rows": int(d["event"].eq("RG").sum()), "rg_rows_reparsed": n,
            "rg_rows_lead_official_equals_raw_parse": int(same),
            "rg_rows_not_reparsed": {w: int(sum(1 for _, _, x in chk if x == w)) for w in ("no file", "names")}}
    return d, info


# ------------------------------------------------------------------------------------------------ MCP
def mcp_link(P: pd.DataFrame) -> pd.DataFrame:
    base = C.DUMP / "match_charting_project"
    frames = []
    for g in ("m", "w"):
        o = pd.read_parquet(base / "stats" / f"charting-{g}-stats-Overview.parquet")
        o = o[o["set"].astype(str).eq("Total")].copy()
        mm = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        o = o.merge(mm[["match_id", "Player 1", "Player 2", "Date", "Tournament", "Round"]], on="match_id", how="left")
        o["tour"] = "atp" if g == "m" else "wta"
        frames.append(o)
    o = pd.concat(frames, ignore_index=True)
    o["year"] = pd.to_numeric(o["Date"].astype(str).str[:4], errors="coerce")
    t = o["Tournament"].astype(str).str.strip()
    o["event"] = np.where(t.eq("Roland Garros"), "RG",
                          np.where(t.str.contains("Olympic", case=False) & o["year"].eq(2024), "OG", ""))
    o = o[(o["event"].eq("RG") & o["year"].between(2019, 2025)) | o["event"].eq("OG")].copy()
    o["Round"] = o["Round"].astype(str).str.strip()
    for c in ["serve_pts", "aces", "dfs", "first_in", "first_won", "second_in", "second_won"]:
        o[c] = pd.to_numeric(o[c], errors="coerce")
    raw = C.raw_subset()
    raw = raw[(raw["tourney_name"].eq("Roland Garros") & pd.to_numeric(raw["season"]).between(2019, 2025))
              | raw["tourney_name"].eq("Paris Olympics")]
    raw = raw.rename(columns={"_source_file": "sfile", "_row": "srow"})
    groups = {k: g for k, g in raw.groupby(["tourney_name", "season", "tour", "round"])}
    rows = []
    for mid, g in o.groupby("match_id"):
        r0 = g.iloc[0]
        tn = "Roland Garros" if r0["event"] == "RG" else "Paris Olympics"
        cand = groups.get((tn, int(r0["year"]), r0["tour"], r0["Round"]))
        if cand is None:
            continue
        best = []
        for x in cand.itertuples():
            for p1_is_w in (True, False):
                a = C.name_ok(r0["Player 1"], x.winner_name if p1_is_w else x.loser_name)
                b = C.name_ok(r0["Player 2"], x.loser_name if p1_is_w else x.winner_name)
                if min(a, b) >= 1:
                    best.append(((min(a, b), a + b), x, p1_is_w))
        if not best:
            continue
        best.sort(key=lambda z: z[0], reverse=True)
        if len(best) > 1 and best[0][0] == best[1][0]:
            continue                                     # ambiguous: left out
        _, x, p1_is_w = best[0]
        for _, pr in g.iterrows():
            is_p1 = pr["player"] == r0["Player 1"]
            side = "w" if (is_p1 == p1_is_w) else "l"
            rows.append({"mcp_id": mid, "source_file": x.sfile, "source_row": int(x.srow), "side": side, "mcp_player": pr["player"],
                         "mcp_svpt": pr["serve_pts"], "mcp_first_in": pr["first_in"], "mcp_first_won": pr["first_won"],
                         "mcp_second_won": pr["second_won"], "mcp_ace": pr["aces"], "mcp_df": pr["dfs"]})
    m = pd.DataFrame(rows)
    return m


def _pmf(errors: np.ndarray, alpha: float = 1.0):
    """A smoothed pmf of integer errors: the empirical counts plus alpha times a discretised Laplace with the errors'
    own mean absolute deviation (at least 0.5) as its scale, so no error has probability zero."""
    errors = np.asarray(errors, dtype=float)
    b = max(np.mean(np.abs(errors - np.median(errors))), 0.5)
    vals, cnt = np.unique(errors, return_counts=True)
    emp = dict(zip(vals.astype(int), cnt))
    n = len(errors)

    def f(k):
        k = int(k)
        lap = (np.exp(-abs(k - np.median(errors)) / b)) * (1 - np.exp(-1 / b)) / (1 + np.exp(-1 / b))
        return (emp.get(k, 0) + alpha * lap) / (n + alpha)
    return f


def tests(d: pd.DataFrame, cal: np.ndarray, label: str, src: str) -> dict:
    """d: disputed rows with {src}_first_in, off_first_in, raw_first_in. cal: the calibration errors (src - truth)."""
    if d.empty or len(cal) == 0:
        return {"set": label, "rows": int(len(d))}
    x = d[f"{src}_first_in"].to_numpy(float)
    o = d["off_first_in"].to_numpy(float)
    s = d["raw_first_in"].to_numpy(float)
    dd = s - o
    eo, es = x - o, x - s
    f = _pmf(cal)
    cal = np.asarray(cal, dtype=float)
    exp_HO = {"exact_O": 0.0, "exact_S": 0.0, "closer_O": 0.0, "closer_S": 0.0}
    exp_HS = dict(exp_HO)
    for di in dd:
        # H_O: x = O + e  -> distance to O |e|, to S |e - d|
        exp_HO["exact_O"] += np.mean(cal == 0)
        exp_HO["exact_S"] += np.mean(cal == di)
        exp_HO["closer_O"] += np.mean(np.abs(cal) < np.abs(cal - di))
        exp_HO["closer_S"] += np.mean(np.abs(cal - di) < np.abs(cal))
        # H_S: x = S + e  -> distance to S |e|, to O |e + d|
        exp_HS["exact_S"] += np.mean(cal == 0)
        exp_HS["exact_O"] += np.mean(cal == -di)
        exp_HS["closer_S"] += np.mean(np.abs(cal) < np.abs(cal + di))
        exp_HS["closer_O"] += np.mean(np.abs(cal + di) < np.abs(cal))
    llr = np.array([np.log(f(a)) - np.log(f(b)) for a, b in zip(eo, es)])
    return {"set": label, "rows": int(len(d)), "calibration_rows": int(len(cal)),
            "calibration_exact": round(float(np.mean(cal == 0)), 3),
            "calibration_mean_error": round(float(np.mean(cal)), 2),
            "obs_exact_O": int(np.sum(eo == 0)), "obs_exact_S": int(np.sum(es == 0)),
            "obs_closer_O": int(np.sum(np.abs(eo) < np.abs(es))), "obs_closer_S": int(np.sum(np.abs(es) < np.abs(eo))),
            "obs_tie": int(np.sum(np.abs(es) == np.abs(eo))),
            **{f"HO_{k}": round(v, 1) for k, v in exp_HO.items()}, **{f"HS_{k}": round(v, 1) for k, v in exp_HS.items()},
            "mean_abs_d": round(float(np.mean(np.abs(dd))), 2),
            "log10_LR_O_vs_S": round(float(np.sum(llr) / np.log(10)), 1),
            "rows_favouring_O": int(np.sum(llr > 0)), "rows_favouring_S": int(np.sum(llr < 0))}


def run_tests(M: pd.DataFrame, src: str, cal_sets: dict, test_sets: dict) -> pd.DataFrame:
    out = []
    for cname, cal in cal_sets.items():
        for tname, d in test_sets.items():
            for mode in ("all", "svpt_equal"):
                if mode == "svpt_equal":
                    c = cal[cal[f"{src}_svpt"].eq(cal["raw_svpt"])]
                    t = d[d[f"{src}_svpt"].eq(d["off_svpt"])]
                else:
                    c, t = cal, d
                e = (c[f"{src}_first_in"] - c["raw_first_in"]).dropna().to_numpy()
                rec = tests(t.dropna(subset=[f"{src}_first_in"]), e, tname, src)
                out.append({"calibration": cname, "mode": mode, **rec})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ Court Vision
def cv_counts() -> pd.DataFrame:
    rows = []
    for f in sorted((C.DUMP / "slam_ball_tracking" / "points").glob("RG_*.parquet")):
        year = int(f.stem.split("_")[1])
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "serve_num", "server_id", "point_winner_id",
                                         "point_end_type"])
        pt = pt.drop_duplicates(["match_id", "point_ID"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        faults = pt[pt["point_end_type"].eq("Faulty Serve")].groupby(["code", "server_id"]).size()
        pts = pt[~pt["point_end_type"].eq("Faulty Serve")]
        for (code, sid), g in pts.groupby(["code", "server_id"]):
            n = g["serve_num"].astype(str)
            w = g["point_winner_id"].astype(str).eq(str(sid))
            rows.append({"year": year, "code": code, "rg_id": str(sid), "cv_svpt": len(g),
                         "cv_first_in": int(n.eq("1").sum()), "cv_first_won": int((n.eq("1") & w).sum()),
                         "cv_second_won": int((n.eq("2") & w).sum()),
                         "cv_ace": int(g["point_end_type"].eq("Ace").sum()),
                         "cv_df": int(g["point_end_type"].eq("DoubleFault").sum()),
                         "cv_fault_rows": int(faults.get((code, sid), 0))})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ SofaScore
def sofa_rows() -> pd.DataFrame:
    e = pd.read_parquet(C.DUMP / "sofascore_tournaments" / "events.parquet")
    s = pd.read_parquet(C.DUMP / "sofascore_tournaments" / "statistics.parquet")
    s = s[s["period"].eq("ALL")]
    e = e[e["unique_tournament_name"].astype(str).str.startswith("Roland")].copy()
    e["year"] = pd.to_numeric(e["season_year"], errors="coerce")
    e = e[e["year"].between(2022, 2025)]
    rmap = {"R128": "R128", "Round of 128": "R128", "Round of 64": "R64", "Round of 32": "R32", "Round of 16": "R16",
            "Quarterfinals": "QF", "Semifinals": "SF", "Final": "F", "Qualification round 1": "Q1",
            "Qualification Round 1": "Q1", "Qualification round 2": "Q2", "Qualification Round 2": "Q2",
            "Qualification Final": "Q3"}
    e["round"] = e["round_name"].map(rmap)
    e["tour"] = np.where(e["unique_tournament_name"].astype(str).str.contains("Women"), "wta", "atp")
    st = {k: g.set_index("key") for k, g in s.groupby(s["event_id"].astype(str))}
    raw = C.raw_subset()
    raw = raw[raw["tourney_name"].eq("Roland Garros") & pd.to_numeric(raw["season"]).between(2022, 2025)]
    raw = raw.rename(columns={"_source_file": "sfile", "_row": "srow"})
    groups = {k: g for k, g in raw.groupby(["season", "tour", "round"])}
    rows = []
    for r in e.itertuples():
        g = st.get(str(r.event_id))
        cand = groups.get((int(r.year), r.tour, r.round))
        if g is None or cand is None or "firstServeAccuracy" not in g.index:
            continue
        hits = []
        for x in cand.itertuples():
            for home_is_w in (True, False):
                a = C.name_ok(r.home_name, x.winner_name if home_is_w else x.loser_name)
                b = C.name_ok(r.away_name, x.loser_name if home_is_w else x.winner_name)
                if min(a, b) >= 1:
                    hits.append(((min(a, b), a + b), x, home_is_w))
        if not hits:
            continue
        hits.sort(key=lambda z: z[0], reverse=True)
        if len(hits) > 1 and hits[0][0] == hits[1][0]:
            continue
        _, x, home_is_w = hits[0]
        for side, col in (("w", "home" if home_is_w else "away"), ("l", "away" if home_is_w else "home")):
            v = lambda k: g.loc[k, col] if k in g.index else None
            fi, sv = C.frac(v("firstServeAccuracy"))
            fw, _ = C.frac(v("firstServePointsAccuracy"))
            sw, swd = C.frac(v("secondServePointsAccuracy"))
            rows.append({"source_file": x.sfile, "source_row": int(x.srow), "side": side, "sofa_event": r.event_id,
                         "sofa_svpt": sv, "sofa_first_in": fi, "sofa_first_won": fw, "sofa_second_won": sw,
                         "sofa_second_den": swd, "sofa_ace": pd.to_numeric(v("aces"), errors="coerce"),
                         "sofa_df": pd.to_numeric(v("doubleFaults"), errors="coerce")})
    return pd.DataFrame(rows)


def main() -> int:
    P, info = player_table()
    summary: dict = {"official_reparse": info}
    key = ["source_file", "source_row", "side"]
    # ---------------- MCP
    m = mcp_link(P)
    M = m.merge(P, on=key, how="inner")
    M.to_csv(OUT / "mcp_rows.csv", index=False)
    summary["mcp"] = {"linked_player_rows": int(len(m)), "with_classification": int(len(M)),
                      "by_event_year_class": M.groupby(["event", "year", "cls"]).size().rename("rows").reset_index()
                      .to_dict("records")}
    clean = M[M["event"].eq("RG") & M["year"].between(2019, 2021) & M["cls"].eq("equal")]
    later_equal = M[(M["event"].eq("OG") | M["year"].between(2022, 2025)) & M["cls"].eq("equal")]
    cal_sets = {"RG 2019-2021 equal": clean, "2022-2025/OG equal": later_equal}
    disp = M[M["fix"].ne("")]
    test_sets = {"all proposed": disp}
    for fx in ["RGFSA", "RGFSB", "OGFSA", "OGFSB"]:
        test_sets[fx] = disp[disp["fix"].eq(fx)]
        for sg in ["+", "-", "0"]:
            test_sets[f"{fx} {sg}"] = disp[disp["fix"].eq(fx) & disp["sign"].eq(sg)]
    for yr in range(2022, 2026):
        test_sets[f"RG {yr} proposed"] = disp[disp["event"].eq("RG") & disp["year"].eq(yr)]
    mt = run_tests(M, "mcp", cal_sets, test_sets)
    mt.to_csv(OUT / "mcp_tests.csv", index=False)
    # exact agreement with the truth in the calibration sets, and on 'points' rows (not proposed) for context
    summary["mcp"]["exact_first_in_rate"] = {
        name: {"rows": int(len(g)), "exact": round(float(g["mcp_first_in"].eq(g["raw_first_in"]).mean()), 3),
               "exact_given_svpt": round(float(g.loc[g["mcp_svpt"].eq(g["raw_svpt"]), "mcp_first_in"]
                                               .eq(g.loc[g["mcp_svpt"].eq(g["raw_svpt"]), "raw_first_in"]).mean()), 3),
               "svpt_equal": round(float(g["mcp_svpt"].eq(g["raw_svpt"]).mean()), 3),
               "mean_error_first_in": round(float((g["mcp_first_in"] - g["raw_first_in"]).mean()), 2)}
        for name, g in cal_sets.items()}
    # ---------------- Court Vision
    cv = cv_counts()
    rg = P[P["event"].eq("RG") & P["my_rg_id"].notna()].copy()
    rg["rg_id"] = rg["my_rg_id"].astype(float).astype(int).astype(str)
    cv["rg_id"] = cv["rg_id"].astype(str).str.replace(r"\.0$", "", regex=True)
    V = rg.merge(cv.rename(columns={"code": "rg_code"}), on=["year", "rg_code", "rg_id"], how="inner")
    V.to_csv(OUT / "cv_rows.csv", index=False)
    rel = []
    for (yr, tour), g in V.groupby(["year", "tour"]):
        eq = g[g["cls"].eq("equal")]
        comp = eq[eq["cv_svpt"].eq(eq["raw_svpt"])]
        off = g[g["off_svpt"].notna()]
        rel.append({"year": yr, "tour": tour, "rows": len(g), "equal_rows": len(eq), "equal_rows_complete": len(comp),
                    "exact_first_in_on_equal_complete": round(float(comp["cv_first_in"].eq(comp["raw_first_in"]).mean()), 3)
                    if len(comp) else None,
                    "cv_second_serve_share": round(float(1 - g["cv_first_in"].sum() / g["cv_svpt"].sum()), 3),
                    "official_second_serve_share": round(float(1 - off["off_first_in"].sum() / off["off_svpt"].sum()), 3),
                    "sackmann_second_serve_share": round(float(1 - g["raw_first_in"].sum() / g["raw_svpt"].sum()), 3),
                    "cv_fault_rows_per_second_serve_point": round(float(g["cv_fault_rows"].sum() /
                                                                        max((g["cv_svpt"] - g["cv_first_in"]).sum(), 1)), 3)})
    rel = pd.DataFrame(rel)
    rel.to_csv(OUT / "cv_reliability.csv", index=False)
    cv_cal = {"RG 2019-2020 equal": V[V["year"].between(2019, 2020) & V["cls"].eq("equal")],
              "RG 2022 equal": V[V["year"].eq(2022) & V["cls"].eq("equal")]}
    dv = V[V["fix"].ne("")]
    cv_sets = {"RG 2022 proposed": dv[dv["year"].eq(2022)]}
    for fx in ["RGFSA", "RGFSB"]:
        for sg in ["+", "-", "0"]:
            cv_sets[f"RG 2022 {fx} {sg}"] = dv[dv["year"].eq(2022) & dv["fix"].eq(fx) & dv["sign"].eq(sg)]
    cv_sets["RG 2023 proposed (unreliable edition)"] = dv[dv["year"].eq(2023)]
    cv_sets["RG 2024 proposed (unreliable edition)"] = dv[dv["year"].eq(2024)]
    ct = run_tests(V, "cv", cv_cal, cv_sets)
    ct.to_csv(OUT / "cv_tests.csv", index=False)
    # ---------------- SofaScore
    so = sofa_rows()
    S = so.merge(P, on=key, how="inner")
    S.to_csv(OUT / "sofa_rows.csv", index=False)
    agr = []
    for name, g in {"all linked": S, "equal": S[S["cls"].eq("equal")], "proposed": S[S["fix"].ne("")],
                    "proposed +": S[S["fix"].ne("") & S["sign"].eq("+")],
                    "proposed -": S[S["fix"].ne("") & S["sign"].eq("-")],
                    "proposed 0": S[S["fix"].ne("") & S["sign"].eq("0")],
                    "points": S[S["cls"].eq("points")]}.items():
        if g.empty:
            continue
        def all_eq(pre):
            return np.all([g[f"sofa_{c}"].eq(g[f"{pre}_{c}"]) for c in ["svpt", "first_in", "first_won", "second_won"]],
                          axis=0)
        agr.append({"set": name, "rows": len(g),
                    "first_in_equals_sackmann": round(float(g["sofa_first_in"].eq(g["raw_first_in"]).mean()), 3),
                    "first_in_equals_official": round(float(g["sofa_first_in"].eq(g["off_first_in"]).mean()), 3),
                    "four_counts_equal_sackmann": round(float(all_eq("raw").mean()), 3),
                    "four_counts_equal_official": round(float(all_eq("off").mean()), 3)})
    agr = pd.DataFrame(agr)
    agr.to_csv(OUT / "sofa_agreement.csv", index=False)
    summary["sofascore"] = agr.to_dict("records")
    summary["cv_reliability"] = rel.to_dict("records")
    (OUT / "independent_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(json.dumps(summary["official_reparse"], indent=1))
    print(json.dumps(summary["mcp"]["exact_first_in_rate"], indent=1))
    print(mt.to_string())
    print(rel.to_string())
    print(ct.to_string())
    print(agr.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
