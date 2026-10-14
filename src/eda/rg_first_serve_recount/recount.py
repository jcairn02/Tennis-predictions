"""The Roland-Garros first-serve recount, step 1 of checklist item 6 (docs/studies/adoption_framework/checklist.md):
can first serves in (and serve points) be recounted per match, and does the recount hold where the truth is known?

Builds one row per Stage 0 player row of Roland Garros 2019-2026 and the Paris Olympics 2024 with every source's
counts beside Sackmann's (sources.py), and the agreement tables:

    rows.parquet                 the linked table (raw_* = the Sackmann row as read, before Stage 0's checks;
                                 s0_* = Stage 0; api_* = RG's own statistics; mb_* = RG's MatchBeats recounted;
                                 ks_* = RG's key statistics 2025-26; cv_* = Court Vision recounted; ol_* = the
                                 Olympic results; mcp_* = the Match Charting Project)
    links.json                   what each source holds and how much of it was placed on Stage 0
    agree_<a>_vs_<b>.csv         exact agreement per count, by event, year, tour and draw
    editions.csv                 pooled first serves in, and points won on first and second serve, per source
    ao_check.csv                 the same two point sources at the Australian Open against Stage 0's AO rows
    disputed_referees.csv        rows where RG's record and Sackmann's disagree on first serves in, with what the
                                 independent records (Court Vision, MCP) say

Reads no model result. Usage: ./python.sh src/eda/rg_first_serve_recount/recount.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.rg_first_serve_recount import link as L  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402

OUT = S.STUDY
POINT_COUNTS = ["ace", "df", "svpt", "first_in", "first_won", "second_won"]
EIGHT = POINT_COUNTS + ["bp_faced", "bp_saved"]
GROUP = ["event", "year", "tour", "draw"]


def attach_raw(rows: pd.DataFrame) -> pd.DataFrame:
    """The Sackmann row's own counts for each player row (w_ or l_ by the result), as read before Stage 0's checks."""
    raw = S.raw_rows()
    raw = raw[raw["source_file"].isin(rows["source_file"].dropna().unique())]
    keep = ["source_file", "source_row", "tourney_id", "round", "winner_name", "loser_name"]
    cols = {f"{s}_{c}": f"{s}_{c}" for s in ("w", "l") for c in S.RAW_COUNTS.values()}
    r = raw[keep + list(cols)].copy()
    for c in cols:
        r[c] = pd.to_numeric(r[c].replace("", np.nan), errors="coerce")
    r = r.rename(columns={"round": "raw_round"})
    rows = rows.copy()
    rows["source_row"] = pd.to_numeric(rows["source_row"]).astype("Int64")
    rows = rows.merge(r, on=["source_file", "source_row"], how="left")
    # the side of the raw row this player is, by name (Stage 0 keeps the raw winner; the name confirms it)
    wk, lk = rows["winner_name"].map(S.nkey), rows["loser_name"].map(S.nkey)
    side = np.select([rows["name_key"].eq(wk), rows["name_key"].eq(lk)], ["w", "l"],
                     np.where(rows["won"], "w?", "l?"))
    rows["raw_side"] = side
    for b, c in S.RAW_COUNTS.items():
        rows[f"raw_{b}"] = np.where(np.char.startswith(side.astype(str), "w"), rows[f"w_{c}"], rows[f"l_{c}"])
    return rows


def build() -> tuple[pd.DataFrame, dict]:
    s0 = S.stage0()
    rows = s0[["match_id", "player_id", "player_name", "name_key", "event", "year", "tour", "draw", "round", "won",
               "side", "score", "status", "has_box", "source", "source_file", "source_row"] + S.BOX].copy()
    rows = rows.rename(columns={b: f"s0_{b}" for b in S.BOX})
    info = {}

    # RG's own statistics, placed by names; then MatchBeats, key statistics and Court Vision through RG's codes
    codes = L.rg_codes(s0)
    api = S.api().rename(columns={"match_id": "code"})
    a = api.merge(codes, on=["year", "code", "team"], how="left")
    info["api"] = {"teams": int(len(api)), "matches": int(api[["year", "code"]].drop_duplicates().shape[0]),
                   "with_statistics": int(api["has_statistics"].sum()),
                   "placed_teams": int(a["match_id"].notna().sum()),
                   "unplaced_matches": [f"{y} {c}" for y, c in
                                        a[a["match_id"].isna()][["year", "code"]].drop_duplicates().itertuples(index=False)]}
    acols = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved", "first_won_den",
             "second_won_den", "ret_won", "ret_den", "total_won"]
    a = a[a["match_id"].notna()][["match_id", "player_id", "code", "team", "court", "has_statistics", "winner",
                                  "end_cause"] + acols]
    a = a.rename(columns={c: f"api_{c}" for c in acols + ["court", "has_statistics", "winner", "end_cause"]})
    a = a.rename(columns={"code": "rg_code", "team": "api_team"})
    rows = rows.merge(a, on=["match_id", "player_id"], how="left")

    mb = S.mb("RG")
    mbp = L.pair_slots(mb, S.api(), ["year", "match_id"], "name_key", "name_key", "slot", "team") \
        .rename(columns={"match_id": "rg_code", "slot": "mb_slot", "team": "api_team", "pair_score": "mb_pair"})
    m = mb.rename(columns={"match_id": "rg_code", "slot": "mb_slot"})
    mcols = ["svpt", "first_in", "first_won", "second_won", "serve_other", "ace", "df", "sv_gms", "route", "court"]
    m = m.merge(mbp, on=["year", "rg_code", "mb_slot"])[["year", "rg_code", "api_team", "mb_slot"] + mcols]
    m = m.rename(columns={c: f"mb_{c}" for c in mcols})
    rows = rows.merge(m, on=["year", "rg_code", "api_team"], how="left")
    info["mb"] = {"player_rows": int(len(mb)), "matches": int(mb[["year", "match_id"]].drop_duplicates().shape[0]),
                  "paired_to_rg_statistics": int(len(m)), "placed_on_stage0": int(rows["mb_svpt"].notna().sum())}

    ks = S.keystats().rename(columns={"match_id": "rg_code", "slot": "mb_slot"})
    ks = ks.rename(columns={c: f"ks_{c}" for c in ["ace", "df", "svpt", "first_in", "first_won", "second_won",
                                                    "bp_faced", "bp_saved"]})
    rows = rows.merge(ks, on=["year", "rg_code", "mb_slot"], how="left")
    info["ks"] = {"player_rows": int(len(ks)), "placed_on_stage0": int(rows["ks_svpt"].notna().sum())}

    cv = S.court_vision("RG")
    cvp = L.pair_slots(cv.assign(nk=cv["name"].map(S.nkey)), S.api().assign(nk=lambda d: d["name_key"]),
                       ["year", "match_id"], "nk", "nk", "slot", "team")
    c = cv.rename(columns={"match_id": "rg_code", "slot": "cv_slot"})
    cvp = cvp.rename(columns={"match_id": "rg_code", "slot": "cv_slot", "team": "api_team", "pair_score": "cv_pair"})
    ccols = ["svpt", "first_in", "first_won", "second_won", "ace", "df", "na_rows"]
    c = c.merge(cvp, on=["year", "rg_code", "cv_slot"])[["year", "rg_code", "api_team"] + ccols]
    rows = rows.merge(c.rename(columns={x: f"cv_{x}" for x in ccols}), on=["year", "rg_code", "api_team"], how="left")
    info["cv"] = {"player_rows": int(len(cv)), "paired_to_rg_statistics": int(len(c)),
                  "placed_on_stage0": int(rows["cv_svpt"].notna().sum())}

    # the Olympics
    ou, placed = L.og_units(s0)
    ol = S.olympics().merge(ou, on=["unit", "athlete_code"])
    ocols = ["svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved", "second_in",
             "second_served", "spw", "status"]
    ol = ol[["match_id", "player_id", "unit", "athlete_code"] + ocols].rename(columns={x: f"ol_{x}" for x in ocols})
    pbp = S.olympics_pbp()
    pcols = ["svpt", "first_in", "first_won", "second_won", "ace", "df", "unknown_results"]
    ol = ol.merge(pbp.rename(columns={x: f"olp_{x}" for x in pcols}), on=["unit", "athlete_code"], how="left")
    rows = rows.merge(ol.drop(columns="athlete_code"), on=["match_id", "player_id"], how="left")
    info["ol"] = {"units": int(S.olympics()["unit"].nunique()), "placed_units": int(placed["match_id"].notna().sum()),
                  "unplaced": placed[placed["match_id"].isna()]["unit"].tolist()}

    mc = L.mcp_rows(s0)
    rows = rows.merge(mc, on=["match_id", "player_id"], how="left")
    info["mcp"] = {"placed_player_rows": int(rows["mcp_svpt"].notna().sum())}

    rows = attach_raw(rows)
    return rows, info


def agreement(rows: pd.DataFrame, a: str, b: str, counts: list[str], where=None) -> pd.DataFrame:
    """Exact agreement of source a with source b per count, over rows that hold both (b's svpt present)."""
    d = rows if where is None else rows[where]
    d = d[d[f"{a}_svpt"].notna() & d[f"{b}_svpt"].notna()]
    out = []
    for k, g in d.groupby(GROUP):
        rec = dict(zip(GROUP, k))
        rec["rows"] = len(g)
        eq = {}
        for c in counts:
            if f"{a}_{c}" in g and f"{b}_{c}" in g:
                eq[c] = g[f"{a}_{c}"].eq(g[f"{b}_{c}"])
                rec[c] = round(float(eq[c].mean()), 4)
        rec["all"] = round(float(np.all(list(eq.values()), axis=0).mean()), 4)
        sv = g[f"{a}_svpt"].eq(g[f"{b}_svpt"])
        if sv.any():
            rec["first_in_given_svpt"] = round(float(g.loc[sv, f"{a}_first_in"].eq(g.loc[sv, f"{b}_first_in"]).mean()), 4)
            d_fi = g.loc[sv, f"{b}_first_in"] - g.loc[sv, f"{a}_first_in"]
            rec[f"{b}_higher_given_svpt"] = round(float((d_fi > 0).mean()), 4)
            rec[f"{b}_lower_given_svpt"] = round(float((d_fi < 0).mean()), 4)
        out.append(rec)
    return pd.DataFrame(out)


def editions(rows: pd.DataFrame) -> pd.DataFrame:
    out = []
    for k, g in rows.groupby(GROUP):
        rec = dict(zip(GROUP, k))
        for src in ("raw", "api", "mb", "cv", "ol", "ks"):
            if f"{src}_svpt" not in g:
                continue
            h = g[g[f"{src}_svpt"].notna() & g[f"{src}_first_in"].notna()]
            if h.empty:
                continue
            sv, fi = h[f"{src}_svpt"].sum(), h[f"{src}_first_in"].sum()
            rec[f"{src}_rows"] = len(h)
            rec[f"{src}_first_in_pct"] = round(100 * fi / sv, 2)
            rec[f"{src}_first_won_pct"] = round(100 * h[f"{src}_first_won"].sum() / fi, 2)
            rec[f"{src}_second_won_pct"] = round(100 * h[f"{src}_second_won"].sum() / (sv - fi), 2)
        out.append(rec)
    return pd.DataFrame(out)


def ao_check() -> pd.DataFrame:
    """The same point sources at the Australian Open (whose Stage 0 rows agree with the hand charts, input-data
    audit 3.2): RG's provider's MatchBeats (AO 2024-25, Infosys) and the Court Vision copy (AO 2020-24), recounted
    and placed on Stage 0's AO rows by year, draw, round and names."""
    from src.ingest.point_sources import infosys_slams as I
    m = pd.read_parquet(S.S0 / "stage0_matches.parquet")
    p = pd.read_parquet(S.S0 / "stage0_match_players.parquet")
    m = m[m["tournament_name"].eq("Australian Open") & m["year"].between(2020, 2026)].copy()
    s0 = p.merge(m[["match_id", "year", "tour", "qualifying", "round"]], on="match_id")
    s0["tour"] = s0["tour"].map({"atp": "M", "wta": "W"})
    s0["draw"] = np.where(s0["qualifying"], "qual", "main")
    s0["name_key"] = s0["player_name"].map(S.nkey)
    s0["event"] = "AO"
    s0m = L.stage0_matches(s0)
    rounds = I.round_lookup()
    out = []
    for src, df, code_col in (("mb", S.mb("AO"), "match_id"), ("cv", S.court_vision("AO"), "match_id")):
        if df.empty:
            continue
        df = df.copy()
        if src == "cv":
            df["name_key"] = df["name"].map(S.nkey)
        df["round"] = df[code_col].map(lambda c: rounds.get(("AO", c)))
        fam = df[code_col].str[:2]
        df["tour"] = np.where(fam.str[0].eq("W"), "W", "M")
        df["draw"] = np.where(fam.str[1].eq("Q"), "qual", "main")
        mm = df.pivot_table(index=["year", code_col, "tour", "draw", "round"], columns="slot", values="name_key",
                            aggfunc="first").reset_index().rename(columns={1: "name1", 2: "name2", code_col: "code"})
        mm["event"] = "AO"
        placed = L.place(mm, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
        placed = placed[placed["match_id"].notna()]
        s0i = s0m.set_index("match_id")
        for r in placed.itertuples():
            for slot, pid in ((1 if r.a_is == "1" else 2, s0i.loc[r.match_id, "pid_a"]),
                              (2 if r.a_is == "1" else 1, s0i.loc[r.match_id, "pid_b"])):
                x = df[(df["year"].eq(r.year)) & (df[code_col].eq(r.code)) & (df["slot"].eq(slot))].iloc[0]
                y = s0[(s0["match_id"].eq(r.match_id)) & (s0["player_id"].eq(pid))].iloc[0]
                out.append({"source": src, "year": r.year, "tour": r.tour, "draw": r.draw, "code": r.code,
                            "match_id": r.match_id, "player": y["player_name"], "has_box": bool(y["has_box"]),
                            **{f"src_{c}": x[c] for c in POINT_COUNTS}, **{f"s0_{c}": y[c] for c in POINT_COUNTS}})
    return pd.DataFrame(out)


def ao_summary(ao: pd.DataFrame) -> pd.DataFrame:
    d = ao[ao["has_box"]]
    out = []
    for k, g in d.groupby(["source", "year", "tour", "draw"]):
        rec = dict(zip(["source", "year", "tour", "draw"], k))
        rec["rows"] = len(g)
        for c in POINT_COUNTS:
            rec[c] = round(float(g[f"src_{c}"].eq(g[f"s0_{c}"]).mean()), 4)
        rec["all"] = round(float(np.all([g[f"src_{c}"].eq(g[f"s0_{c}"]) for c in POINT_COUNTS], axis=0).mean()), 4)
        sv = g["src_svpt"].eq(g["s0_svpt"])           # the point file holds every point the box counts
        rec["complete_rows"] = int(sv.sum())
        for c in ("first_in", "first_won", "second_won"):
            rec[f"{c}_given_complete"] = round(float(g.loc[sv, f"src_{c}"].eq(g.loc[sv, f"s0_{c}"]).mean()), 4)
        rec["src_first_in_pct"] = round(100 * g["src_first_in"].sum() / g["src_svpt"].sum(), 2)
        rec["s0_first_in_pct"] = round(100 * g["s0_first_in"].sum() / g["s0_svpt"].sum(), 2)
        out.append(rec)
    return pd.DataFrame(out)


def referees(rows: pd.DataFrame) -> pd.DataFrame:
    """Rows where RG's statistics (or the Olympic results) and Sackmann's row disagree on first serves in while
    agreeing on serve points, with the independent records' first serves in."""
    off = rows["event"].eq("OG")
    ref = np.where(off, rows["ol_first_in"], rows["api_first_in"])
    refsv = np.where(off, rows["ol_svpt"], rows["api_svpt"])
    d = rows[(pd.notna(ref)) & rows["raw_first_in"].notna() & (rows["raw_svpt"] == refsv)
             & (rows["raw_first_in"] != ref)].copy()
    d["official_first_in"] = np.where(d["event"].eq("OG"), d["ol_first_in"], d["api_first_in"])
    keep = ["event", "year", "tour", "draw", "round", "player_name", "match_id", "raw_svpt", "raw_first_in",
            "official_first_in", "mb_first_in", "cv_svpt", "cv_first_in", "mcp_svpt", "mcp_first_in"]
    d = d[[c for c in keep if c in d]]
    for src in ("cv", "mcp"):
        if f"{src}_first_in" not in d:
            continue
        h = d[f"{src}_first_in"].notna()
        d.loc[h, f"{src}_sides_with"] = np.select(
            [d.loc[h, f"{src}_first_in"].eq(d.loc[h, "official_first_in"]),
             d.loc[h, f"{src}_first_in"].eq(d.loc[h, "raw_first_in"])], ["official", "sackmann"], "neither")
        dist_o = (d.loc[h, f"{src}_first_in"] - d.loc[h, "official_first_in"]).abs()
        dist_s = (d.loc[h, f"{src}_first_in"] - d.loc[h, "raw_first_in"]).abs()
        d.loc[h, f"{src}_closer_to"] = np.select([dist_o < dist_s, dist_s < dist_o], ["official", "sackmann"], "equal")
    return d


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows, info = build()
    rows.to_parquet(OUT / "rows.parquet", index=False)
    tabs = {
        "api_vs_raw": agreement(rows, "api", "raw", EIGHT),
        "mb_vs_api": agreement(rows, "mb", "api", POINT_COUNTS),
        "mb_vs_raw": agreement(rows, "mb", "raw", POINT_COUNTS),
        "ks_vs_api": agreement(rows, "ks", "api", EIGHT),
        "cv_vs_api": agreement(rows, "cv", "api", POINT_COUNTS),
        "cv_vs_raw": agreement(rows, "cv", "raw", POINT_COUNTS),
        "ol_vs_raw": agreement(rows, "ol", "raw", EIGHT),
        "olp_vs_ol": agreement(rows, "olp", "ol", POINT_COUNTS),
        "mcp_vs_api": agreement(rows, "mcp", "api", POINT_COUNTS),
        "mcp_vs_raw": agreement(rows, "mcp", "raw", POINT_COUNTS),
        "mcp_vs_ol": agreement(rows, "mcp", "ol", POINT_COUNTS),
    }
    for name, t in tabs.items():
        t.to_csv(OUT / f"agree_{name}.csv", index=False)
    editions(rows).to_csv(OUT / "editions.csv", index=False)
    ao = ao_check()
    ao.to_csv(OUT / "ao_rows.csv", index=False)
    ao_summary(ao).to_csv(OUT / "ao_check.csv", index=False)
    referees(rows).to_csv(OUT / "disputed_referees.csv", index=False)
    (OUT / "links.json").write_text(json.dumps(info, indent=1, default=str) + "\n", encoding="utf-8")
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("unplaced_matches", "unplaced")}
                      for k, v in info.items()}, indent=1))
    for name in ("api_vs_raw", "mb_vs_api", "mb_vs_raw", "ol_vs_raw"):
        print(f"\n== {name}\n", tabs[name].to_string())
    print("\n== AO\n", ao_summary(ao).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
