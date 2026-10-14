"""F1 review (A2-skeptic): WTA 2015, serve points that leave out double faults.

Attacks:
  1. Rebuild the event list on the live (7 Oct) Stage 0 and compare with the audit's (30 Sep) list and row count.
  2. Per row against the Match Charting Project: which of svpt / svpt + df equals MCP's serve points; does
     "svpt equals MCP" occur only with df = 0; do the other counts (first_in, first_won, second_won, df, ace) agree.
  3. Per row, a two-sided bound from the score's service games (no tiebreak, completed): over a player's service
     games, serve points won minus serve points lost lies in [2H - 4B, 4H - 2B] (H holds, B breaks), and
     points lost >= 4B, points won >= 4H. A row that passes as recorded but fails with svpt + df would be broken
     by the fix.
  4. Per-row likelihood of the two readings from a fit on clean WTA rows (2014, 2016 tour main draws).
  5. Boundary events (Doha out, Kuala Lumpur in), neighbouring weeks, qualifying, Fed Cup, Slams of 2015.
  6. Rounds: does the fault hold in late rounds (where another feed might be used)?
Writes data/studies/input_data_audit/fixes/A2-skeptic/f1_*.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f1_wta2015.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import _common as K


def pooled(g: pd.DataFrame) -> pd.Series:
    sv, fi, sw, df = g["svpt"].sum(), g["first_in"].sum(), g["second_won"].sum(), g["df"].sum()
    return pd.Series({"rows": len(g), "second_won_pct": 100 * sw / (sv - fi),
                      "second_won_pct_if_plus_df": 100 * sw / (sv + df - fi),
                      "first_in_pct": 100 * fi / sv, "first_in_pct_if_plus_df": 100 * fi / (sv + df),
                      "def_fail_rows": int(g["def_fail"].sum())})


def bounds(d: pd.DataFrame) -> pd.DataFrame:
    """Two-sided service-game bounds, as recorded and with svpt + df. Only completed matches without tiebreaks."""
    B = d["bp_faced"] - d["bp_saved"]
    H = d["sv_gms"] - B
    spw = d["first_won"] + d["second_won"]
    out = pd.DataFrame(index=d.index)
    ok = d["status"].eq("completed") & d["tb_won_d"].fillna(-1).eq(0) & d["sv_gms"].notna()
    out["bound_testable"] = ok
    for tag, svpt in (("raw", d["svpt"]), ("cor", d["svpt"] + d["df"])):
        spl = svpt - spw
        diff = spw - spl
        good = (diff >= 2 * H - 4 * B) & (diff <= 4 * H - 2 * B) & (spl >= 4 * B) & (spw >= 4 * H)
        out[f"bound_ok_{tag}"] = good.where(ok)
        out[f"diff_{tag}"] = diff.where(ok)
    out["H"], out["B"] = H.where(ok), B.where(ok)
    return out


def main() -> None:
    d = K.stage0()
    d = d[d["has_box"]].copy()
    d["def_fail"] = (d["second_won"] + d["df"]) > (d["svpt"] - d["first_in"])
    d = pd.concat([d, bounds(d)], axis=1)
    wta = d[d["tour"].eq("wta")]

    # ---- 1. the event list on the live tables
    w = wta[wta["year"].eq(2015) & wta["level"].isin(["T1000", "T500", "T250"]) & ~wta["qualifying"]
            & wta["tournament_date"].between("2015-02-23", "2015-08-24")]
    ev = w.groupby(["tournament_date", "tournament_name"]).apply(pooled).reset_index()
    ev["in_fault"] = ev["second_won_pct"] > 49
    audit = pd.read_csv(K.AUDIT / "box_wta2015_events.csv")
    audit["tournament_date"] = pd.to_datetime(audit["tournament_date"])
    ev = ev.merge(audit[["tournament_date", "tournament_name", "rows", "in_fault"]].rename(
        columns={"rows": "audit_rows_sep30", "in_fault": "audit_in_fault"}), on=["tournament_date", "tournament_name"],
        how="outer")
    scope = w.merge(ev.loc[ev["in_fault"].eq(True), ["tournament_date", "tournament_name"]],
                    on=["tournament_date", "tournament_name"])
    print(f"window events {len(ev)}, in fault {int(ev['in_fault'].sum())}, scope rows (live) {len(scope)}, "
          f"audit rows sep30 {int(audit.loc[audit['in_fault'], 'rows'].sum())}")
    print("sources in scope:", scope["source"].value_counts().to_dict(), "statuses:", scope["status"].value_counts().to_dict())

    # ---- 2. MCP per row (window rows and other WTA rows of 2014-16)
    mc = K.mcp("w")
    mc = mc[mc["date"].dt.year.isin([2014, 2015, 2016])]
    x = wta[wta["year"].isin([2014, 2015, 2016])].copy()
    x["pk"], x["ok"] = x["player_name"].map(K.name_key), x["o_player_name"].map(K.name_key)
    j = x.merge(mc, on=["pk", "ok"], suffixes=("", "_mcp"))
    j = j[(j["date"] - j["tournament_date"]).dt.days.between(-1, 16)]
    j = j.drop_duplicates(["match_id", "player_id"])   # one chart per Stage 0 player row
    in_scope = set(zip(scope["match_id"], scope["player_id"]))
    j["in_scope"] = [(a, b) in in_scope for a, b in zip(j["match_id"], j["player_id"])]
    j["svpt_eq"] = j["svpt"].eq(j["serve_pts"])
    j["svpt_df_eq"] = (j["svpt"] + j["df"]).eq(j["serve_pts"])
    j["svpt_eq_df_pos"] = j["svpt_eq"] & j["df"].gt(0)
    for c, mcol in (("df", "dfs"), ("ace", "aces"), ("first_in", "first_in_mcp"), ("first_won", "first_won_mcp"),
                    ("second_won", "second_won_mcp")):
        j[f"{c}_eq"] = j[c].eq(j[mcol])
    j["svpt_minus_mcp"] = j["svpt"] - j["serve_pts"]
    j["svpt_df_minus_mcp"] = j["svpt"] + j["df"] - j["serve_pts"]
    j["group"] = np.where(j["in_scope"], "F1 scope", np.where(
        j["tournament_date"].between("2015-02-23", "2015-08-24") & j["year"].eq(2015) & ~j["qualifying"]
        & j["level"].isin(["T1000", "T500", "T250"]), "window, not in scope", "other WTA 2014-16"))
    cols = ["svpt_eq", "svpt_df_eq", "svpt_eq_df_pos", "df_eq", "ace_eq", "first_in_eq", "first_won_eq", "second_won_eq"]
    summ = j.groupby("group")[cols].mean().round(3)
    summ["rows"] = j.groupby("group").size()
    print(summ.to_string())
    keep = ["group", "match_id", "player_id", "player_name", "o_player_name", "tournament_name", "tournament_date",
            "round", "score", "status", "svpt", "df", "serve_pts", "dfs", "first_in", "first_in_mcp", "second_won",
            "second_won_mcp", "svpt_minus_mcp", "svpt_df_minus_mcp", "match_id_mcp"] + cols
    j[keep].to_csv(K.OUT / "f1_mcp_rows.csv", index=False)

    # rows in scope where svpt alone equals MCP with df > 0, or neither equals
    sc = j[j["in_scope"]]
    print("scope MCP rows:", len(sc), "svpt==MCP:", int(sc["svpt_eq"].sum()), "of which df>0:",
          int(sc["svpt_eq_df_pos"].sum()), "svpt+df==MCP:", int(sc["svpt_df_eq"].sum()),
          "neither:", int((~sc["svpt_eq"] & ~sc["svpt_df_eq"]).sum()))
    print("distribution svpt+df - MCP (scope):", sc["svpt_df_minus_mcp"].value_counts().sort_index().to_dict())
    print("distribution svpt - MCP (other WTA 2014-16):",
          j.loc[j["group"].eq("other WTA 2014-16"), "svpt_minus_mcp"].value_counts().sort_index().to_dict())
    print(sc.loc[sc["svpt_eq_df_pos"] | (~sc["svpt_eq"] & ~sc["svpt_df_eq"]),
                 ["tournament_name", "round", "player_name", "o_player_name", "svpt", "df", "serve_pts", "dfs",
                  "svpt_df_minus_mcp", "match_id_mcp"]].to_string())

    # per-event MCP verdicts
    mev = sc.groupby("tournament_name").agg(mcp_rows=("svpt_eq", "size"), mcp_svpt_df_eq=("svpt_df_eq", "sum"),
                                            mcp_svpt_eq=("svpt_eq", "sum"), mcp_svpt_eq_df_pos=("svpt_eq_df_pos", "sum"))

    # ---- 3. bounds
    for name, g in (("F1 scope", scope), ("other WTA tour main 2014+2016", wta[wta["year"].isin([2014, 2016])
                                                                       & wta["level"].isin(["T1000", "T500", "T250"])
                                                                       & ~wta["qualifying"]])):
        t = g[g["bound_testable"]]
        print(f"{name}: bound-testable rows {len(t)}; ok raw {t['bound_ok_raw'].mean():.4f}, ok cor "
              f"{t['bound_ok_cor'].mean():.4f}; raw ok & cor fails {int((t['bound_ok_raw'] & ~t['bound_ok_cor'].astype(bool)).sum())}; "
              f"cor ok & raw fails {int((t['bound_ok_cor'] & ~t['bound_ok_raw'].astype(bool)).sum())}")

    # ---- 4. likelihood of the two readings, from clean rows (WTA tour main 2014, 2016; inclusive by MCP)
    clean = wta[wta["year"].isin([2014, 2016]) & wta["level"].isin(["T1000", "T500", "T250"]) & ~wta["qualifying"]
                & wta["bound_testable"]]
    Xc = np.c_[clean["H"], clean["B"]]
    coef, *_ = np.linalg.lstsq(Xc, clean["diff_raw"], rcond=None)   # clean rows: raw == true reading
    res = clean["diff_raw"] - Xc @ coef
    sd = float(res.std())
    print(f"clean fit: diff = {coef[0]:.3f} H + {coef[1]:.3f} B, residual SD {sd:.2f}")
    t = scope[scope["bound_testable"]].copy()
    pred = np.c_[t["H"], t["B"]] @ coef
    t["llr_cor_vs_raw"] = (((t["diff_raw"] - pred) / sd) ** 2 - ((t["diff_cor"] - pred) / sd) ** 2) / 2
    print("scope: mean residual raw %.2f, cor %.2f; rows favouring raw (llr < -2): %d of %d" % (
        float((t["diff_raw"] - pred).mean()), float((t["diff_cor"] - pred).mean()), int((t["llr_cor_vs_raw"] < -2).sum()), len(t)))
    t["resid_raw"], t["resid_cor"] = t["diff_raw"] - pred, t["diff_cor"] - pred
    lev = t.groupby("tournament_name").agg(bound_rows=("llr_cor_vs_raw", "size"), llr_sum=("llr_cor_vs_raw", "sum"),
                                           mean_resid_raw=("resid_raw", "mean"), mean_resid_cor=("resid_cor", "mean"),
                                           raw_ok_cor_fail=("bound_ok_cor", lambda s: int((~s.astype(bool) & t.loc[s.index, "bound_ok_raw"].astype(bool)).sum())))
    # the same for Doha, and clean events
    def event_llr(g):
        g = g[g["bound_testable"]]
        p = np.c_[g["H"], g["B"]] @ coef
        return pd.Series({"bound_rows": len(g), "mean_resid_raw": float((g["diff_raw"] - p).mean()),
                          "mean_resid_cor": float((g["diff_cor"] - p).mean())})

    # ---- per-event table
    pe = ev.merge(mev, left_on="tournament_name", right_index=True, how="left").merge(
        lev, left_on="tournament_name", right_index=True, how="left")
    out_of_scope = w[~w["tournament_name"].isin(scope["tournament_name"].unique())]
    for nm, g in out_of_scope.groupby("tournament_name"):
        r = event_llr(g)
        for c in r.index:
            pe.loc[pe["tournament_name"].eq(nm), c] = r[c]
    pe.to_csv(K.OUT / "f1_events.csv", index=False)
    print(pe.to_string())

    # ---- 5. neighbours: every WTA 2015 event (tour, qualifying, Fed Cup, Slams), 2014 and 2016 for reference
    nb = wta[wta["year"].isin([2015])].copy()
    nb["draw"] = np.where(nb["qualifying"], "Q", "M")
    nbe = nb.groupby(["tournament_date", "tournament_name", "level", "draw"]).apply(pooled).reset_index()
    nbe.to_csv(K.OUT / "f1_wta2015_all_editions.csv", index=False)
    print(nbe[nbe["rows"] >= 10].to_string())

    # ---- 6. rounds inside the scope
    rr = scope.groupby("round").apply(pooled)
    print(rr.to_string())
    rr.to_csv(K.OUT / "f1_scope_by_round.csv")

    # scope file
    scope_out = scope[["match_id", "player_id", "player_name", "tournament_name", "tournament_date", "round", "source",
                       "source_file", "source_row", "side", "won", "svpt", "df", "def_fail"]].copy()
    scope_out.to_csv(K.OUT / "f1_scope_candidate.csv", index=False)


if __name__ == "__main__":
    main()
