"""F1 (WTA 2015: serve points leave out double faults), refereed against the Match Charting Project and simulated.

Writes data/studies/input_data_audit/fixes/A3-referee/:
    f1_events_2015.csv          every WTA 2015 event (tour, Slam, Fed Cup, qualifying, ITF): rows with a raw box,
                                definition-test failures, pooled second-serve share as recorded and with svpt + df
    f1_mcp_rows.csv             every MCP-charted WTA player-match of 2014-2016 joined to Sackmann's raw row
    f1_mcp_by_event.csv         MCP agreement per event of the window and outside, split by df = 0 / df > 0
    f1_scope.csv                the scope rows (Stage 0 match_id, player_id, Sackmann _source_file, _row) with
                                the fix and the post-fix checks
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

WIN0, WIN1 = pd.Timestamp("2015-02-23"), pd.Timestamp("2015-08-24")


def raw_player_rows(years: list[int]) -> pd.DataFrame:
    """Sackmann WTA raw rows of the given years, two rows per match (the player's own counts)."""
    r = []
    for y in years:
        for pat in (f"wta_matches_{y}.parquet", f"wta_matches_qual_itf_{y}.parquet"):
            f = rc.SACK / "wta" / pat
            if f.exists():
                t = pd.read_parquet(f)
                t["file"] = pat
                r.append(t)
    r = pd.concat(r, ignore_index=True)
    r["tdate"] = pd.to_datetime(r["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    rows = []
    for side, me, op in (("w", "winner", "loser"), ("l", "loser", "winner")):
        c = rc.raw_counts(r, side)
        d = pd.DataFrame({"_source_file": r["_source_file"], "_row": r["_row"], "file": r["file"],
                          "tourney_id": r["tourney_id"], "tourney_name": r["tourney_name"],
                          "tourney_level": r["tourney_level"], "round": r["round"], "tdate": r["tdate"],
                          "score": r["score"], "side": side, "pid": "wta:" + r[f"{me}_id"].astype(str),
                          "name": r[f"{me}_name"], "oname": r[f"{op}_name"]})
        rows.append(pd.concat([d, c], axis=1))
    out = pd.concat(rows, ignore_index=True)
    out["pk"], out["ok"] = rc.keys(out["name"]), rc.keys(out["oname"])
    out["full"] = out[rc.BOX[:6]].notna().all(axis=1) & (out["svpt"] > 0)
    out["qual"] = out["round"].astype(str).str.upper().str.match(r"Q\d")
    return out


def event_table(x: pd.DataFrame) -> pd.DataFrame:
    b = x[x["full"]].copy()
    b["deffail"] = rc.definition_fails(b)
    g = b.groupby(["file", "tourney_level", "qual", "tdate", "tourney_name"]).agg(
        rows=("svpt", "size"), deffail=("deffail", "sum"), svpt=("svpt", "sum"), df=("df", "sum"),
        fi=("first_in", "sum"), sw=("second_won", "sum"), fw=("first_won", "sum"))
    g["deffail_pct"] = 100 * g["deffail"] / g["rows"]
    g["second_won_pct"] = 100 * g["sw"] / (g["svpt"] - g["fi"])
    g["second_won_pct_if_plus_df"] = 100 * g["sw"] / (g["svpt"] + g["df"] - g["fi"])
    g["first_in_pct"] = 100 * g["fi"] / g["svpt"]
    g["first_in_pct_if_plus_df"] = 100 * g["fi"] / (g["svpt"] + g["df"])
    return g.reset_index().sort_values(["tdate", "file", "qual", "tourney_name"])


def mcp_join(x: pd.DataFrame) -> pd.DataFrame:
    mc = rc.mcp_totals("wta")
    mc = mc[mc["mdate"].dt.year.isin([2014, 2015, 2016])]
    j = mc.merge(x[x["full"]], on=["pk", "ok"], suffixes=("_mcp", ""))
    j = j[(j["mdate"] - j["tdate"]).dt.days.between(-1, 16)]
    # one Sackmann row per MCP player-match: the nearest event start before the match
    j["gap"] = (j["mdate"] - j["tdate"]).dt.days.abs()
    j = j.sort_values(["match_id", "player", "gap"]).drop_duplicates(["match_id", "player"])
    # and one MCP chart per Sackmann row (a match charted twice keeps the first)
    j = j.drop_duplicates(["_source_file", "_row", "side"])
    j["in_window"] = (~j["tourney_level"].isin(["G", "D"]) & ~j["qual"]
                      & j["tdate"].between(WIN0, WIN1) & j["file"].str.startswith("wta_matches_2015"))
    j["svpt_eq"] = j["svpt"].eq(j["serve_pts"])
    j["svpt_df_eq"] = (j["svpt"] + j["df"]).eq(j["serve_pts"])
    j["df_eq"] = j["df"].eq(j["dfs"])
    j["ace_eq"] = j["ace"].eq(j["aces"])
    j["fi_eq"] = j["first_in"].eq(j["first_in_mcp"])
    j["fw_eq"] = j["first_won"].eq(j["first_won_mcp"])
    j["sw_eq"] = j["second_won"].eq(j["second_won_mcp"])
    j["bpf_eq"] = j["bp_faced"].eq(j["bk_pts"])
    j["bps_eq"] = j["bp_saved"].eq(j["bp_saved_mcp"])
    j["df0"] = j["df"].eq(0)
    j["deffail"] = rc.definition_fails(j)
    j["verdict"] = np.select([j["svpt_df_eq"] & ~j["df0"], j["svpt_eq"] & ~j["df0"], j["svpt_eq"] & j["df0"]],
                             ["excludes_df", "includes_df", "df0_either"], "neither")
    return j


def main() -> int:
    rc.OUT.mkdir(parents=True, exist_ok=True)
    x = raw_player_rows([2014, 2015, 2016])
    ev = event_table(x[x["file"].str.contains("2015")])
    ev.to_csv(rc.OUT / "f1_events_2015.csv", index=False)
    print("WTA 2015 events with raw boxes (main file, non-qualifying):")
    print(ev[~ev["qual"] & ev["file"].str.startswith("wta_matches_2015")][
        ["tourney_level", "tdate", "tourney_name", "rows", "deffail", "deffail_pct", "second_won_pct",
         "second_won_pct_if_plus_df", "first_in_pct"]].round(1).to_string(index=False))
    print("\nqualifying / ITF rows of 2015 with raw boxes:")
    q = ev[ev["qual"] | ~ev["file"].str.startswith("wta_matches_2015")]
    print(q.groupby(["file", "tourney_level", "qual"]).agg(events=("rows", "size"), rows=("rows", "sum"),
                                                          deffail=("deffail", "sum")).to_string())
    print(q[q["rows"] > 0][["file", "tourney_level", "qual", "tdate", "tourney_name", "rows", "deffail",
                            "second_won_pct", "second_won_pct_if_plus_df"]].round(1).head(80).to_string(index=False))
    # definition-test failure share by tour-season level group, all WTA 2014-16 rows
    b = x[x["full"]].copy()
    b["deffail"] = rc.definition_fails(b)
    b["year"] = b["tdate"].dt.year
    print("\ndefinition-test failures by file and level:")
    print(b.groupby(["file", "tourney_level"]).agg(rows=("deffail", "size"), fails=("deffail", "sum")).to_string())

    j = mcp_join(x)
    j.to_csv(rc.OUT / "f1_mcp_rows.csv", index=False)
    print(f"\nMCP-joined player-matches 2014-16: {len(j)}; in the window: {int(j['in_window'].sum())}")
    for w in (True, False):
        s = j[j["in_window"] == w]
        print(f"\n--- in_window={w}: {len(s)} rows")
        print(s.groupby("df0")[["svpt_eq", "svpt_df_eq", "df_eq", "ace_eq", "fi_eq", "fw_eq", "sw_eq", "bpf_eq",
                                "bps_eq"]].agg(["mean", "size"]).round(3).T.to_string())
        print(s["verdict"].value_counts().to_string())
    w = j[j["in_window"]]
    per = w.groupby(["tdate", "tourney_name"]).agg(
        rows=("verdict", "size"), excludes_df=("verdict", lambda v: (v == "excludes_df").sum()),
        includes_df=("verdict", lambda v: (v == "includes_df").sum()),
        df0_either=("verdict", lambda v: (v == "df0_either").sum()), neither=("verdict", lambda v: (v == "neither").sum()),
        svpt_df_eq=("svpt_df_eq", "mean"), svpt_eq=("svpt_eq", "mean"), fi_eq=("fi_eq", "mean"), sw_eq=("sw_eq", "mean"))
    # MCP rows of other 2015 events (outside the window and Slams), by event
    o = j[~j["in_window"] & j["file"].str.startswith("wta_matches_2015")]
    per_o = o.groupby(["tdate", "tourney_name", "tourney_level", "qual"]).agg(
        rows=("verdict", "size"), excludes_df=("verdict", lambda v: (v == "excludes_df").sum()),
        includes_df=("verdict", lambda v: (v == "includes_df").sum()),
        df0_either=("verdict", lambda v: (v == "df0_either").sum()), neither=("verdict", lambda v: (v == "neither").sum()))
    pd.concat([per.reset_index().assign(group="window (Doha is not in the proposed scope)"),
               per_o.reset_index().assign(group="2015 outside the window")], ignore_index=True)         .to_csv(rc.OUT / "f1_mcp_by_event.csv", index=False)
    print("\nMCP per event in the window:")
    print(per.round(2).to_string())
    print("\nMCP per event of 2015 outside the window:")
    print(per_o.to_string())
    print("\nrows in the window that MCP says include df already (svpt == MCP, df > 0):")
    print(w[w["verdict"].eq("includes_df")][["tdate", "tourney_name", "round", "name", "oname", "svpt", "df",
                                              "serve_pts", "dfs", "first_in", "first_in_mcp", "second_won",
                                              "second_won_mcp"]].to_string())
    print("\nrows in the window matching neither:")
    print(w[w["verdict"].eq("neither")][["tdate", "tourney_name", "round", "name", "oname", "svpt", "df", "serve_pts",
                                         "dfs", "first_in", "first_in_mcp", "first_won", "first_won_mcp", "second_won",
                                         "second_won_mcp", "ace", "aces"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
