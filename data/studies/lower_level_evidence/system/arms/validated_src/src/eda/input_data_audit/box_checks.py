"""The box scores the model's averages are built from: whole events or seasons that read wrong for the same players.

Stage 0's row checks (B0-B9) only catch a count that is impossible inside its own row. A fault like a season of serve
speeds reading 4 km/h high passes them, because every row is plausible. This script looks for such faults four ways:

    1. accounting identities across the two players of a match (common.identity_flags): box scores exchanged between
       winner and loser, service games that cannot alternate, breaks that do not add up to the score;
    2. a definition test: second-serve points won plus double faults cannot exceed the second-serve points
       (common.serve_points_exclude_dfs), true whenever serve points include double faults;
    3. box scores repeated verbatim in another match of Sackmann's raw files (copied events, same-pair repeats);
    4. level shifts against the same players elsewhere (common.edition_effects, with player x season x surface
       baselines) and pooled rates by tour, level and season, then checked against independent records where held:
       the Match Charting Project (hand-charted points) and Roland Garros's own key statistics (decrypted Infosys files).

Writes data/studies/input_data_audit/:
    box_identity_editions_<snap>.csv   flagged editions: identity failures, swapped-box fits, winner-fewer-points share
    box_swapped_<snap>.csv             the matches whose box scores fit only when exchanged
    box_svpt_df_editions_<snap>.csv    flagged editions: impossible-row share and pooled second-serve win share
    box_wta2015_events.csv             the WTA tour events of 23 Feb - 24 Aug 2015, pooled rates as recorded and corrected
    box_wta2015_vs_mcp.csv             WTA 2014-16 serve points against the Match Charting Project
    box_raw_copies.csv                 pairs of raw Sackmann rows that share a 16-count box score
    box_rg2025_vs_keystats.csv         Stage 0's Roland Garros 2025 counts against RG's key statistics
    box_slams_vs_mcp.csv               first serves in at each Slam 2019-2025 against the Match Charting Project
    box_pooled_rates_<snap>.csv        pooled rates by tour, level group and season
    box_edition_effects_<snap>.parquet same-player edition effects (first serves in, first-/second-serve points won,
                                       aces, double faults), with each edition's deviation from its event's median
    box_ages_<snap>.csv                ages that are impossible or inconsistent with the player's other rows
    box_summary.json
Run: ./python.sh src/eda/input_data_audit/box_checks.py        (about 10 minutes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.input_data_audit import common as C  # noqa: E402

RAW_COUNTS = ["w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_bpSaved", "w_bpFaced",
              "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_bpSaved", "l_bpFaced"]


def edition_label(d: pd.DataFrame) -> pd.Series:
    return (d["tour"] + "|" + d["level"].astype(str) + "|" + d["tournament_name"].astype(str) + "|"
            + d["year"].astype(str) + "|" + np.where(d["qualifying"], "Q", "M") + "|" + d["source"])


# ------------------------------------------------------------------------------------------------
# 1. Identities

def identities(d: pd.DataFrame, snap: str, summary: dict) -> None:
    b = d[d["has_box"] & d["side"].eq("A")].copy()
    f = C.identity_flags(b)
    b = pd.concat([b, f], axis=1)
    b["edition"] = edition_label(b)
    comp = b["status"].eq("completed")
    g = b.assign(comp=comp).groupby("edition").agg(
        date=("tournament_date", "min"), matches=("comp", "sum"), testable=("identity_testable", "sum"),
        games_identity_fails=("games_identity_fails", "sum"), swapped_box_fits=("swapped_box_fits", "sum"),
        svg_not_alternating=("svg_not_alternating", "sum"), winner_fewer_points=("winner_fewer_points", "sum"))
    g["games_identity_fail_pct"] = 100 * g["games_identity_fails"] / g["testable"].replace(0, np.nan)
    g["winner_fewer_points_pct"] = 100 * g["winner_fewer_points"] / g["matches"].replace(0, np.nan)
    flagged = ((g["swapped_box_fits"] > 0) | ((g["games_identity_fail_pct"] >= 10) & (g["testable"] >= 5))
               | ((g["winner_fewer_points_pct"] >= 15) & (g["matches"] >= 8))
               | (g["svg_not_alternating"] >= 0.1 * g["matches"]) & (g["matches"] >= 8))
    g[flagged].sort_values("date").to_csv(C.OUT / f"box_identity_editions_{snap}.csv")   # flagged editions only
    sw = b[b["swapped_box_fits"]][["match_id", "edition", "round", "score", "player_name", "o_player_name", "won",
                                    "winner_fewer_points"]]
    sw.to_csv(C.OUT / f"box_swapped_{snap}.csv", index=False)
    summary[f"identities_{snap}"] = {
        "matches_with_box": int(len(b)), "completed": int(comp.sum()),
        "winner_fewer_points_pct": round(100 * float(b["winner_fewer_points"].sum() / comp.sum()), 2),
        "games_identity_testable": int(b["identity_testable"].sum()),
        "games_identity_fails": int(b["games_identity_fails"].sum()),
        "swapped_box_fits": int(b["swapped_box_fits"].sum()),
        "swapped_box_fits_by_edition": sw["edition"].value_counts().head(10).to_dict()}
    C.log(f"{snap}: {int(b['swapped_box_fits'].sum())} matches fit only with the box scores exchanged")


# ------------------------------------------------------------------------------------------------
# 2. Serve points without double faults

def svpt_df(d: pd.DataFrame, snap: str, summary: dict) -> pd.DataFrame:
    b = d[d["has_box"]].copy()
    b["impossible"] = C.serve_points_exclude_dfs(b)
    b["edition"] = edition_label(b)
    r = C.pooled_rates(b, ["edition"])
    r["impossible_share"] = b.groupby("edition")["impossible"].mean()
    r["date"] = b.groupby("edition")["tournament_date"].min()
    women = r.index.str.startswith("wta|")
    flagged = (r["impossible_share"] > 0) | ((r["rows"] >= 20) & (r["second_won_pct"] > np.where(women, 49, 55)))
    r[flagged].sort_values("date").to_csv(C.OUT / f"box_svpt_df_editions_{snap}.csv")   # flagged editions only
    by_tour_year = b.groupby(["tour", "year"])["impossible"].mean().unstack(0)
    summary[f"svpt_df_{snap}"] = {
        "impossible_rows": int(b["impossible"].sum()), "rows": int(len(b)),
        "tour_years_with_any": {f"{t}{y}": round(float(v), 4) for (y, t), v in by_tour_year.stack().items() if v > 0}}
    return b


def wta2015_window(b: pd.DataFrame) -> pd.DataFrame:
    """WTA tour main draws of 23 Feb - 24 Aug 2015 (the window where the definition test fails) and their pooled
    rates; an event is in the fault when its pooled second-serve win share exceeds 49% (women's norm about 45%)."""
    w = b[b["tour"].eq("wta") & b["year"].eq(2015) & b["level"].isin(["T1000", "T500", "T250"]) & ~b["qualifying"]
          & b["tournament_date"].between("2015-02-23", "2015-08-24")]
    r = C.pooled_rates(w, ["tournament_date", "tournament_name"])
    r["impossible_share"] = w.groupby(["tournament_date", "tournament_name"])["impossible"].mean()
    r["in_fault"] = r["second_won_pct"] > 49
    return r


def wta2015_vs_mcp(summary: dict) -> None:
    mm = pd.read_csv(C.MCP / "charting-w-matches.csv", dtype=str, on_bad_lines="skip")
    ov = pd.read_csv(C.MCP / "charting-w-stats-Overview.csv", dtype=str, on_bad_lines="skip")
    ov = ov[ov["set"].eq("Total")].copy()
    for c in ["serve_pts", "dfs", "first_in"]:
        ov[c] = pd.to_numeric(ov[c], errors="coerce")
    mm["date"] = pd.to_datetime(mm["Date"], format="%Y%m%d", errors="coerce")
    m = mm[mm["date"].dt.year.isin([2014, 2015, 2016])].merge(ov, on="match_id")
    m["pk"] = m["player"].map(C.name_key)
    m["ok"] = np.where(m["player"].eq(m["Player 1"]), m["Player 2"], m["Player 1"])
    m["ok"] = m["ok"].map(C.name_key)
    rows = []
    for yr in (2014, 2015, 2016):
        r = pd.read_parquet(C.SACKMANN / "wta" / f"wta_matches_{yr}.parquet")
        r["tdate"] = pd.to_datetime(r["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
        for side in ("w", "l"):
            me, op = ("winner", "loser") if side == "w" else ("loser", "winner")
            rows.append(pd.DataFrame({"tdate": r["tdate"], "tourney": r["tourney_name"], "pk": r[f"{me}_name"].map(C.name_key),
                                      "ok": r[f"{op}_name"].map(C.name_key),
                                      "s_svpt": pd.to_numeric(r[f"{side}_svpt"], errors="coerce"),
                                      "s_df": pd.to_numeric(r[f"{side}_df"], errors="coerce")}))
    s = pd.concat(rows, ignore_index=True)
    j = m.merge(s, on=["pk", "ok"])
    j = j[(j["date"] - j["tdate"]).dt.days.between(-1, 16)].drop_duplicates(["match_id", "player"])
    tour_event = ~j["tourney"].isin(C.SLAMS)
    j["window"] = np.where(tour_event & j["tdate"].between("2015-02-23", "2015-08-24"),
                           "WTA tour events 23 Feb - 24 Aug 2015", "other WTA matches 2014-16")
    j["svpt_equals_mcp"] = j["s_svpt"].eq(j["serve_pts"])
    j["svpt_plus_df_equals_mcp"] = (j["s_svpt"] + j["s_df"]).eq(j["serve_pts"])
    g = j.groupby("window").agg(player_matches=("player", "size"), svpt_equals_mcp=("svpt_equals_mcp", "mean"),
                                svpt_plus_df_equals_mcp=("svpt_plus_df_equals_mcp", "mean"))
    g.to_csv(C.OUT / "box_wta2015_vs_mcp.csv")
    summary["wta2015_vs_mcp"] = g.round(3).to_dict(orient="index")


# ------------------------------------------------------------------------------------------------
# 3. Copied box scores in the raw files

def raw_copies(summary: dict) -> None:
    frames = []
    for tour in ("atp", "wta"):
        for f in sorted((C.SACKMANN / tour).glob(f"{tour}_matches_*.parquet")):
            if "doubles" in f.name:
                continue
            r = pd.read_parquet(f)
            if not set(RAW_COUNTS + ["winner_name", "loser_name"]) <= set(r.columns):
                continue
            r = r[["tourney_id", "tourney_name", "tourney_date", "match_num", "round", "winner_name", "loser_name",
                   "score"] + RAW_COUNTS].copy()
            r["file"], r["tour"] = f.name, tour
            frames.append(r)
    raw = pd.concat(frames, ignore_index=True)
    for c in RAW_COUNTS:
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw = raw[raw["w_svpt"].fillna(0) >= 20]
    raw["key"] = raw[RAW_COUNTS].fillna(-1).astype(int).astype(str).agg("|".join, axis=1)
    dup = raw[raw["key"].duplicated(keep=False)].sort_values(["key", "tourney_date"])
    pairs = []
    for _, x in dup.groupby("key"):
        a = x.iloc[0]
        for i in range(1, len(x)):
            b = x.iloc[i]
            same_match = a["winner_name"] == b["winner_name"] and a["loser_name"] == b["loser_name"] and a["score"] == b["score"]
            if same_match:
                continue           # the same match listed twice: Stage 0 drops repeats (rules D1-D3)
            pairs.append({"tour": a["tour"], "source_event": a["tourney_name"], "source_date": a["tourney_date"],
                          "source_match": f"{a['winner_name']} d. {a['loser_name']} {a['score']}",
                          "copy_event": b["tourney_name"], "copy_date": b["tourney_date"], "copy_round": b["round"],
                          "copy_match": f"{b['winner_name']} d. {b['loser_name']} {b['score']}",
                          "same_players": {a["winner_name"], a["loser_name"]} == {b["winner_name"], b["loser_name"]}})
    p = pd.DataFrame(pairs)
    p.to_csv(C.OUT / "box_raw_copies.csv", index=False)
    top = p.groupby(["tour", "copy_event", "copy_date"]).size().sort_values(ascending=False).head(12)
    summary["raw_copies"] = {
        "pairs_other_match": int(len(p)), "same_players": int(p["same_players"].sum()),
        "by_copy_event": {" ".join(map(str, k)): int(v) for k, v in top.items()}}
    C.log(f"raw copies: {len(p)} rows carry another match's box score")


# ------------------------------------------------------------------------------------------------
# 4. Roland Garros and the Olympics against independent records

def rg2025_vs_keystats(d: pd.DataFrame, summary: dict) -> None:
    k = pd.read_parquet(C.INFOSYS / "keystats.parquet", columns=["slam", "year", "match_id", "set_key", "name",
                                                                 "player1", "player2"])
    k = k[k["set_key"].eq("set0") & k["name"].isin(["First Serve", "Win On 1st Serve", "Win On 2nd Serve"])]
    k = k.drop_duplicates(["slam", "year", "match_id", "name"])
    m = pd.read_parquet(C.INFOSYS / "matches.parquet", columns=["slam", "year", "match_id", "p1_first_name",
                                                                "p1_last_name", "p2_first_name", "p2_last_name"])
    names = {no: m[f"p{no}_first_name"].fillna("") + " " + m[f"p{no}_last_name"].fillna("") for no in ("1", "2")}

    def frac(s: pd.Series, i: int) -> pd.Series:
        return pd.to_numeric(s.astype(str).str.extract(r"(\d+)\s*/\s*(\d+)")[i], errors="coerce")

    rows = []
    for no, other in (("1", "2"), ("2", "1")):
        w = k.pivot_table(index=["slam", "year", "match_id"], columns="name", values=f"player{no}", aggfunc="first").reset_index()
        w = w.merge(m[["slam", "year", "match_id"]].assign(pk=names[no].map(C.name_key), ok=names[other].map(C.name_key)),
                    on=["slam", "year", "match_id"])
        rows.append(pd.DataFrame({"year": w["year"].astype(int), "pk": w["pk"], "ok": w["ok"],
                                  "rg_first_in": frac(w["First Serve"], 0), "rg_svpt": frac(w["First Serve"], 1),
                                  "rg_first_won": frac(w["Win On 1st Serve"], 0), "rg_second_won": frac(w["Win On 2nd Serve"], 0)}))
    ks = pd.concat(rows, ignore_index=True)
    s = d[d["has_box"] & d["tournament_name"].eq("Roland Garros") & d["year"].isin([2025, 2026])].copy()
    s["pk"], s["ok"] = s["player_name"].map(C.name_key), s["o_player_name"].map(C.name_key)
    j = s.merge(ks, on=["year", "pk", "ok"])
    j["draw"] = np.where(j["qualifying"], "qualifying", "main")
    g = j.groupby(["tour", "year", "draw", "source"]).agg(
        player_matches=("first_in", "size"), first_in_equal=("first_in", lambda x: float((x == j.loc[x.index, "rg_first_in"]).mean())),
        stage0_first_in=("first_in", "sum"), stage0_svpt=("svpt", "sum"), rg_first_in=("rg_first_in", "sum"), rg_svpt=("rg_svpt", "sum"))
    g["stage0_first_in_pct"] = 100 * g["stage0_first_in"] / g["stage0_svpt"]
    g["rg_first_in_pct"] = 100 * g["rg_first_in"] / g["rg_svpt"]
    g = g.drop(columns=["stage0_first_in", "stage0_svpt", "rg_first_in", "rg_svpt"])
    g.to_csv(C.OUT / "box_rg2025_vs_keystats.csv")
    summary["rg2025_vs_keystats"] = {" ".join(map(str, i)): r.round(3).to_dict() for i, r in g.iterrows()}


def slams_vs_mcp(summary: dict) -> None:
    out = []
    for tour, g in (("atp", "m"), ("wta", "w")):
        mm = pd.read_csv(C.MCP / f"charting-{g}-matches.csv", dtype=str, on_bad_lines="skip")
        ov = pd.read_csv(C.MCP / f"charting-{g}-stats-Overview.csv", dtype=str, on_bad_lines="skip")
        ov = ov[ov["set"].eq("Total")].copy()
        for c in ["serve_pts", "first_in"]:
            ov[c] = pd.to_numeric(ov[c], errors="coerce")
        mm["date"] = pd.to_datetime(mm["Date"], format="%Y%m%d", errors="coerce")
        m = mm[mm["date"].dt.year.between(2019, 2025)].merge(ov, on="match_id")
        m["pk"] = m["player"].map(C.name_key)
        m["ok"] = np.where(m["player"].eq(m["Player 1"]), m["Player 2"], m["Player 1"])
        m["ok"] = m["ok"].map(C.name_key)
        rows = []
        for yr in range(2019, 2026):
            r = pd.read_parquet(C.SACKMANN / tour / f"{tour}_matches_{yr}.parquet")
            r["tdate"] = pd.to_datetime(r["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
            for side in ("w", "l"):
                me, op = ("winner", "loser") if side == "w" else ("loser", "winner")
                rows.append(pd.DataFrame({"tdate": r["tdate"], "tourney": r["tourney_name"],
                                          "pk": r[f"{me}_name"].map(C.name_key), "ok": r[f"{op}_name"].map(C.name_key),
                                          "s_svpt": pd.to_numeric(r[f"{side}_svpt"], errors="coerce"),
                                          "s_fi": pd.to_numeric(r[f"{side}_1stIn"], errors="coerce")}))
        s = pd.concat(rows, ignore_index=True)
        j = m.merge(s, on=["pk", "ok"])
        j = j[(j["date"] - j["tdate"]).dt.days.between(-1, 16)].drop_duplicates(["match_id", "player"])
        j["tour"] = tour
        out.append(j)
    j = pd.concat(out, ignore_index=True)
    j["event"] = j["tourney"].where(j["tourney"].isin(C.SLAMS), "other events")
    j["season"] = j["tdate"].dt.year
    j["equal"] = j["s_fi"].eq(j["first_in"])
    g = j.groupby(["tour", "event", "season"]).agg(player_matches=("equal", "size"), first_in_equal=("equal", "mean"),
                                                   s_fi=("s_fi", "sum"), s_svpt=("s_svpt", "sum"),
                                                   m_fi=("first_in", "sum"), m_svpt=("serve_pts", "sum"))
    g["stage0_first_in_pct"] = 100 * g["s_fi"] / g["s_svpt"]
    g["mcp_first_in_pct"] = 100 * g["m_fi"] / g["m_svpt"]
    g["difference_pp"] = g["stage0_first_in_pct"] - g["mcp_first_in_pct"]
    g = g.drop(columns=["s_fi", "s_svpt", "m_fi", "m_svpt"])
    g.to_csv(C.OUT / "box_slams_vs_mcp.csv")
    rg = g.xs("Roland Garros", level="event")
    summary["slams_vs_mcp_roland_garros"] = {f"{t} {s}": {"difference_pp": round(float(r["difference_pp"]), 2),
                                                          "first_in_equal": round(float(r["first_in_equal"]), 2),
                                                          "player_matches": int(r["player_matches"])}
                                             for (t, s), r in rg.iterrows()}
    ev = g.index.get_level_values("event")
    others = g[ev.isin(["Australian Open", "Wimbledon", "US Open"]) & (g["player_matches"] >= 20).to_numpy()]
    summary["slams_vs_mcp_other_slams_max_abs_pp"] = round(float(others["difference_pp"].abs().max()), 2)


# ------------------------------------------------------------------------------------------------
# 5. Level shifts and pooled rates

def level_group(d: pd.DataFrame) -> pd.Series:
    lv = np.where(d["level"].isin(["T1000", "T500", "T250", "FIN"]), "TOUR", d["level"].astype(str))
    return pd.Series(lv, index=d.index) + np.where(d["qualifying"], "-Q", "")


def shifts(d: pd.DataFrame, snap: str) -> None:
    b = d[d["has_box"] & d["status"].isin(["completed", "retired"])].copy()
    b["level_group"] = level_group(b)
    C.pooled_rates(b, ["tour", "level_group", "year"]).to_csv(C.OUT / f"box_pooled_rates_{snap}.csv")
    b = b[b["surface"].notna()]
    b["event"] = b["tour"] + "|" + b["tournament_name"].map(C.event_key) + "|" + np.where(b["qualifying"], "Q", "M")
    edition = b["event"] + "|" + b["year"].astype(str) + "|" + b["source"]
    base = b["player_id"] + "|" + b["year"].astype(str) + "|" + b["surface"].astype(str)
    stats = {"first_in": (b["first_in"], b["svpt"], 20), "first_won": (b["first_won"], b["first_in"], 12),
             "second_won": (b["second_won"], b["svpt"] - b["first_in"], 8), "ace": (b["ace"], b["svpt"], 20),
             "df": (b["df"], b["svpt"], 20)}
    parts = []
    for tour in ("atp", "wta"):
        t = b["tour"].eq(tour)
        cols = {}
        for name, (num, den, mind) in stats.items():
            e = C.edition_effects(num[t], den[t], base[t], edition[t], mind)
            cols[name] = 100 * e["delta"]
            if name == "first_in":
                cols["rows"] = e["rows"]
        parts.append(pd.DataFrame(cols))
        C.log(f"{snap} {tour}: edition effects done")
    e = pd.concat(parts)
    e.index.name = "edition"
    e = e.reset_index()
    e[["tour", "event_name", "draw", "year", "source"]] = e["edition"].str.split("|", expand=True)
    e["event"] = e["tour"] + "|" + e["event_name"] + "|" + e["draw"]
    e["year"] = e["year"].astype(int)
    for c in stats:
        e[f"{c}_vs_event_median"] = e[c] - e.groupby("event")[c].transform("median")
    e["editions_of_event"] = e.groupby("event")["edition"].transform("size")
    e.to_parquet(C.OUT / f"box_edition_effects_{snap}.parquet", index=False)


# ------------------------------------------------------------------------------------------------
# 6. Ages

def ages(d: pd.DataFrame, snap: str, summary: dict) -> None:
    a = d[d["age"].notna()][["match_id", "player_id", "player_name", "age", "tournament_date", "tour", "level", "year",
                             "source"]].copy()
    a["impossible"] = (a["age"] < 13) | (a["age"] > 60)
    ok = a[~a["impossible"]].copy()
    days = (ok["tournament_date"] - pd.Timestamp("1970-01-01")).dt.days.astype(float)
    ok["birth_day"] = days - ok["age"] * 365.25
    ok["off_days"] = ok["birth_day"] - ok.groupby("player_id")["birth_day"].transform("median")
    bad = pd.concat([a[a["impossible"]].assign(kind="impossible"),
                     ok[ok["off_days"].abs() > 120].assign(kind="inconsistent with the player's other rows")])
    bad.drop(columns=["birth_day"], errors="ignore").to_csv(C.OUT / f"box_ages_{snap}.csv", index=False)
    counts = bad.groupby(["kind", "tour", "source", "year"]).size()
    summary[f"ages_{snap}"] = {"impossible": int(a["impossible"].sum()),
                               "inconsistent": int((ok["off_days"].abs() > 120).sum()),
                               "by_source_year": {" ".join(map(str, k)): int(v) for k, v in counts.items()}}


def main() -> int:
    C.OUT.mkdir(parents=True, exist_ok=True)
    summary: dict = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                     "snapshots": {k: str(v.relative_to(C.ROOT)) for k, v in C.SNAPSHOTS.items()}}
    for snap in ("sep30", "oct07"):
        d = C.load_player_rows(snap)
        C.log(f"{snap}: {len(d):,} player rows, {int(d['has_box'].sum()):,} with a box score")
        identities(d, snap, summary)
        b = svpt_df(d, snap, summary)
        if snap == "sep30":
            w = wta2015_window(b)
            w.to_csv(C.OUT / "box_wta2015_events.csv")
            summary["wta2015_window"] = {"events": int(len(w)), "events_in_fault": int(w["in_fault"].sum()),
                                         "player_rows_in_fault": int(w.loc[w["in_fault"], "rows"].sum()),
                                         "second_won_pct_in_fault": round(float(w.loc[w["in_fault"], "second_won_pct"].median()), 2),
                                         "second_won_pct_if_corrected": round(float(w.loc[w["in_fault"], "second_won_pct_if_svpt_plus_df"].median()), 2)}
            rg2025_vs_keystats(d, summary)
        shifts(d, snap)
        ages(d, snap, summary)
    wta2015_vs_mcp(summary)
    raw_copies(summary)
    slams_vs_mcp(summary)
    C.write_json(C.OUT / "box_summary.json", summary)
    C.log("box_summary.json written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
