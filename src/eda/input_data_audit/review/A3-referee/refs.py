"""A3-referee: independent records of a match's box score, in one long form (read-only).

Each ref_* returns one row per player-match:
    ref, year, date (when known), event, round, name, oname, pk, ok, and the counts it holds among
    ace, df, svpt, first_in, first_won, second_won, sv_gms, bp_saved, bp_faced (NaN where it holds none).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

P = rc.PTS
COLS = ["ref", "year", "date", "event", "round", "name", "oname", "pk", "ok"] + rc.BOX


def _finish(d: pd.DataFrame, ref: str) -> pd.DataFrame:
    d = d.copy()
    d["ref"] = ref
    for c in COLS:
        if c not in d:
            d[c] = np.nan
    d["pk"], d["ok"] = rc.keys(d["name"]), rc.keys(d["oname"])
    d["year"] = pd.to_numeric(d["year"], errors="coerce")
    d["date"] = pd.to_datetime(d["date"], errors="coerce", utc=True).dt.tz_localize(None)
    for b in rc.BOX:
        d[b] = pd.to_numeric(d[b], errors="coerce")
    return d[COLS]


def frac(s: pd.Series, i: int) -> pd.Series:
    return pd.to_numeric(s.astype(str).str.extract(r"(\d+)\s*/\s*(\d+)")[i], errors="coerce")


def ref_wta_api() -> pd.DataFrame:
    a = rc.wta_api_totals()
    ed = rc.rd(rc.WTA / "editions.parquet")[["tournament_id", "year", "title", "start_date"]]
    ed["tournament_id"], ed["year"] = ed["tournament_id"].astype(str), ed["year"].astype(str)
    a = a.merge(ed.drop_duplicates(["tournament_id", "year"]), on=["tournament_id", "year"], how="left")
    d = a.rename(columns={f"api_{b}": b for b in rc.BOX})
    d["event"] = d["tournament_id"] + "|" + d["title"].fillna("") + "|" + d["draw"]
    d["date"] = d["start_date"]
    return _finish(d, "wta_api")


def ref_mcp() -> pd.DataFrame:
    out = []
    for tour in ("atp", "wta"):
        x = rc.mcp_totals(tour)
        d = pd.DataFrame({"year": x["mdate"].dt.year, "date": x["mdate"], "event": x["Tournament"], "round": x["Round"],
                          "name": x["player"],
                          "oname": np.where(x["player"].eq(x["Player 1"]), x["Player 2"], x["Player 1"]),
                          "ace": x["aces"], "df": x["dfs"], "svpt": x["serve_pts"], "first_in": x["first_in"],
                          "first_won": x["first_won"], "second_won": x["second_won"], "bp_faced": x["bk_pts"],
                          "bp_saved": x["bp_saved"], "mcp_id": x["match_id"]})
        out.append(d)
    return _finish(pd.concat(out, ignore_index=True), "mcp")


def ref_slam_pbp() -> pd.DataFrame:
    """Sackmann's Slam point-by-point (2011-2024), per player: serve points, aces, double faults, first serves in,
    first- and second-serve points won, service games, break points faced and saved."""
    folder = P / "sackmann_archive" / "slam_pointbypoint"
    out = []
    for f in sorted(folder.glob("*-matches.parquet")):
        if "doubles" in f.name or "mixed" in f.name:
            continue
        pf = folder / f.name.replace("-matches.parquet", "-points.parquet")
        if not pf.exists():
            continue
        mt = rc.rd(f)
        pt = rc.rd(pf)
        for c in ["PointServer", "PointWinner", "P1Ace", "P2Ace", "P1DoubleFault", "P2DoubleFault", "ServeNumber",
                  "P1BreakPoint", "P2BreakPoint", "P1BreakPointWon", "P2BreakPointWon", "SetNo", "GameNo"]:
            pt[c] = pd.to_numeric(pt[c], errors="coerce") if c in pt else np.nan
        pt = pt[pt["PointServer"].isin([1, 2])]
        has_sn = pt["ServeNumber"].notna().mean() > 0.9
        yr, slam = f.name.split("-")[0], f.name.split("-")[1]
        for k, o in ((1, 2), (2, 1)):
            s = pt[pt["PointServer"] == k]
            g = s.groupby("match_id")
            won = s["PointWinner"] == k
            d = pd.DataFrame({
                "svpt": g.size(), "ace": g[f"P{k}Ace"].sum(), "df": g[f"P{k}DoubleFault"].sum(),
                "sv_gms": g[["SetNo", "GameNo"]].apply(lambda z: z.drop_duplicates().shape[0]),
                "bp_faced": g[f"P{o}BreakPoint"].sum(),
                "bp_saved": g[f"P{o}BreakPoint"].sum() - g[f"P{o}BreakPointWon"].sum()})
            if has_sn:
                d["first_in"] = s[s["ServeNumber"] == 1].groupby("match_id").size()
                d["first_won"] = s[(s["ServeNumber"] == 1) & won].groupby("match_id").size()
                d["second_won"] = s[(s["ServeNumber"] == 2) & won].groupby("match_id").size()
                d[["first_in", "first_won", "second_won"]] = d[["first_in", "first_won", "second_won"]].fillna(0)
            d = d.reset_index().merge(mt[["match_id", "player1", "player2", "round"]], on="match_id", how="left")
            d["name"] = d["player1"] if k == 1 else d["player2"]
            d["oname"] = d["player2"] if k == 1 else d["player1"]
            d["year"], d["event"] = yr, slam
            d["first_in_note"] = "ServeNumber==1"
            out.append(d)
    return _finish(pd.concat(out, ignore_index=True), "slam_pbp")


def ref_ibm(site: str) -> pd.DataFrame:
    """US Open / Wimbledon official statistics (IBM feed), whole match."""
    t = pq.read_table(P / site / "statistics.parquet", columns=["year", "event", "match_id", "section", "period", "team",
                                                                "key", "value"]).to_pandas()
    t = t[(t["section"] == "base_stats") & (t["period"] == "match")]
    w = t.pivot_table(index=["year", "event", "match_id", "team"], columns="key", values="value", aggfunc="first")
    w = w.apply(pd.to_numeric, errors="coerce").reset_index()
    m = rc.rd(P / site / "matches.parquet")
    names = m[["year", "event", "match_id", "entry.team1.firstNameA", "entry.team1.lastNameA", "entry.team2.firstNameA",
               "entry.team2.lastNameA", "entry.roundNameShort"]].copy()
    for c in ["year", "event", "match_id"]:
        names[c] = names[c].astype(str)
        w[c] = w[c].astype(str)
    w = w.merge(names.drop_duplicates(["year", "event", "match_id"]), on=["year", "event", "match_id"], how="left")
    out = []
    for team, oteam in (("team_1", "team_2"), ("team_2", "team_1")):
        a = w[w["team"] == team].set_index(["year", "event", "match_id"])
        b = w[w["team"] == oteam].set_index(["year", "event", "match_id"]).reindex(a.index)
        n1 = "entry.team1" if team == "team_1" else "entry.team2"
        n2 = "entry.team2" if team == "team_1" else "entry.team1"
        d = pd.DataFrame({"svpt": a["t_f_srv"], "first_in": a["t_f_srv_in"], "first_won": a["t_f_srv_w"],
                          "second_won": a["t_s_srv_w"], "ace": a["t_ace"], "df": a["df"],
                          "bp_faced": b["t_bp"], "bp_saved": b["t_bp"] - b["t_bp_w"],
                          "name": a[f"{n1}.firstNameA"].fillna("") + " " + a[f"{n1}.lastNameA"].fillna(""),
                          "oname": a[f"{n2}.firstNameA"].fillna("") + " " + a[f"{n2}.lastNameA"].fillna(""),
                          "round": a["entry.roundNameShort"]}).reset_index()
        d["event"] = site + "|" + d["event"]
        out.append(d)
    return _finish(pd.concat(out, ignore_index=True), site)


def ref_sofascore() -> pd.DataFrame:
    out = []
    for folder in ("sofascore", "sofascore_editions", "sofascore_tournaments"):
        ev = rc.rd(P / folder / "events.parquet")
        st = rc.rd(P / folder / "statistics.parquet")
        st = st[st["period"].eq("ALL")]
        keymap = {"aces": "ace", "doubleFaults": "df", "firstServeAccuracy": "fsa", "firstServePointsAccuracy": "fspa",
                  "secondServePointsAccuracy": "sspa", "serviceGamesTotal": "svg", "breakPointsSaved": "bps"}
        st = st[st["key"].isin(keymap) & st["group"].eq("Service")]
        for side, other in (("home", "away"), ("away", "home")):
            w = st.pivot_table(index="event_id", columns="key", values=side, aggfunc="first")
            d = pd.DataFrame(index=w.index)
            d["ace"] = pd.to_numeric(w.get("aces"), errors="coerce")
            d["df"] = pd.to_numeric(w.get("doubleFaults"), errors="coerce")
            d["first_in"], d["svpt"] = frac(w["firstServeAccuracy"], 0), frac(w["firstServeAccuracy"], 1)
            d["first_won"] = frac(w["firstServePointsAccuracy"], 0)
            d["second_won"] = frac(w["secondServePointsAccuracy"], 0)
            d["sv_gms"] = pd.to_numeric(w.get("serviceGamesTotal"), errors="coerce")
            d["bp_saved"], d["bp_faced"] = frac(w["breakPointsSaved"], 0), frac(w["breakPointsSaved"], 1)
            d = d.reset_index().merge(ev[["event_id", "start_utc", "tournament_name", "round_name", f"{side}_name",
                                          f"{other}_name", "season_year"]], on="event_id", how="left")
            d = d.rename(columns={f"{side}_name": "name", f"{other}_name": "oname", "start_utc": "date",
                                  "tournament_name": "event", "round_name": "round", "season_year": "year"})
            d["year"] = pd.to_datetime(d["date"], errors="coerce").dt.year
            out.append(d)
    return _finish(pd.concat(out, ignore_index=True).drop_duplicates(["event_id", "name"]), "sofascore")


def ref_tennislive() -> pd.DataFrame:
    st = rc.rd(P / "tennislive" / "statistics.parquet")
    st = st[st["period"].eq("match")]
    mt = rc.rd(P / "tennislive" / "matches.parquet")
    out = []
    for me, op in (("player1", "player2"), ("player2", "player1")):
        v = st.pivot_table(index="url", columns="name", values=f"{me}_value", aggfunc="first")
        dd = st.pivot_table(index="url", columns="name", values=f"{me}_detail", aggfunc="first")
        ov = st.pivot_table(index="url", columns="name", values=f"{op}_detail", aggfunc="first")
        d = pd.DataFrame(index=v.index)
        d["ace"] = pd.to_numeric(v.get("Aces"), errors="coerce")
        d["df"] = pd.to_numeric(v.get("Double faults"), errors="coerce")
        d["first_in"], d["svpt"] = frac(dd["First serve"], 0), frac(dd["First serve"], 1)
        d["first_won"] = frac(dd["First serve points won"], 0)
        d["second_won"] = frac(dd["Second serve points won"], 0)
        bpc = ov.get("Break points converted")
        d["bp_faced"] = frac(bpc, 1) if bpc is not None else np.nan
        d["bp_saved"] = (frac(bpc, 1) - frac(bpc, 0)) if bpc is not None else np.nan
        d = d.reset_index().merge(mt[["url", f"{me}_name", f"{op}_name", "tournament_name", "date_shown", "round_shown",
                                      "start_times"]], on="url", how="left")
        d = d.rename(columns={f"{me}_name": "name", f"{op}_name": "oname", "tournament_name": "event",
                              "round_shown": "round"})
        d["date"] = pd.to_datetime(d["date_shown"], errors="coerce")
        d["year"] = d["url"].str.extract(r"-(\d{4})/?$")[0]
        d["date"] = d["date"].fillna(pd.to_datetime(d["start_times"], errors="coerce"))
        out.append(d)
    return _finish(pd.concat(out, ignore_index=True), "tennislive")


def ref_tdi() -> pd.DataFrame:
    st = rc.rd(P / "tdi" / "statistics.parquet")
    st = st[st["period"].eq("match")]
    mt = rc.rd(P / "tdi" / "matches.parquet")
    lab = st["label"].unique().tolist()
    out = []
    for me, op in (("team_a", "team_b"), ("team_b", "team_a")):
        v = st.pivot_table(index="match_id", columns="label", values=me, aggfunc="first")
        o = st.pivot_table(index="match_id", columns="label", values=op, aggfunc="first")
        d = pd.DataFrame(index=v.index)

        def col(frame, name):
            return pd.to_numeric(frame[name], errors="coerce") if name in frame else np.nan
        d["ace"] = col(v, "Aces")
        d["df"] = col(v, "Double Faults")
        d["sv_gms"] = col(v, "Service Games Played")
        d["bp_faced"] = col(v, "Break Points Faced")
        d["bp_saved"] = col(v, "Break Points Saved")
        for lname, b in (("1st Serve In", "first_in"), ("1st Serve Points Won", "first_won"),
                         ("2nd Serve Points Won", "second_won"), ("Total Service Points Played", "svpt")):
            if lname in v:
                d[b] = frac(v[lname], 0) if v[lname].astype(str).str.contains("/").any() else col(v, lname)
        d = d.reset_index().merge(mt[["match_id", f"{me}_names", f"{op}_names", "tournament", "completed_on", "round",
                                      "atp_year"]], on="match_id", how="left")
        d = d.rename(columns={f"{me}_names": "name", f"{op}_names": "oname", "tournament": "event",
                              "completed_on": "date", "atp_year": "year"})
        out.append(d)
    r = _finish(pd.concat(out, ignore_index=True), "tdi")
    r.attrs["labels"] = lab
    return r


def ref_infosys() -> pd.DataFrame:
    """Roland Garros / AO key statistics (decrypted Infosys), whole match."""
    k = rc.rd(P / "infosys_slams" / "keystats.parquet")
    k = k[k["set_key"].eq("set0")]
    m = rc.rd(P / "infosys_slams" / "matches.parquet")
    out = []
    for no, other in (("1", "2"), ("2", "1")):
        w = k.pivot_table(index=["slam", "year", "match_id"], columns="name", values=f"player{no}", aggfunc="first")
        o = k.pivot_table(index=["slam", "year", "match_id"], columns="name", values=f"player{other}", aggfunc="first")
        d = pd.DataFrame(index=w.index)

        def g(frame, name, i=None):
            if name not in frame:
                return np.nan
            return frac(frame[name], i) if i is not None else pd.to_numeric(frame[name], errors="coerce")
        d["first_in"], d["svpt"] = g(w, "First Serve", 0), g(w, "First Serve", 1)
        d["first_won"] = g(w, "Win On 1st Serve", 0)
        d["second_won"] = g(w, "Win On 2nd Serve", 0)
        d["ace"] = g(w, "Aces")
        d["df"] = g(w, "Double Faults")
        bp = "Break Points Won" if "Break Points Won" in o else None
        if bp:
            d["bp_faced"], d["bp_saved"] = g(o, bp, 1), g(o, bp, 1) - g(o, bp, 0)
        d = d.reset_index().merge(m[["slam", "year", "match_id", "p1_first_name", "p1_last_name", "p2_first_name",
                                     "p2_last_name"]], on=["slam", "year", "match_id"], how="left")
        d["name"] = d[f"p{no}_first_name"].fillna("") + " " + d[f"p{no}_last_name"].fillna("")
        d["oname"] = d[f"p{other}_first_name"].fillna("") + " " + d[f"p{other}_last_name"].fillna("")
        d["event"] = d["slam"].astype(str) + "|" + d["match_id"].astype(str)
        out.append(d)
    return _finish(pd.concat(out, ignore_index=True), "infosys")


def ref_tml() -> pd.DataFrame:
    out = []
    for f in sorted(rc.TML.glob("*/*.parquet")):
        if f.name.endswith(".json"):
            continue
        t = pd.read_parquet(f)
        if "w_svpt" not in t:
            continue
        t = t[pd.to_numeric(t["w_svpt"], errors="coerce").fillna(0) > 0]
        if t.empty:
            continue
        for side, me, op in (("w", "winner", "loser"), ("l", "loser", "winner")):
            c = rc.raw_counts(t, side)
            d = pd.DataFrame({"date": pd.to_datetime(t["tourney_date"].astype(str), format="%Y%m%d", errors="coerce"),
                              "event": t["tourney_name"], "round": t["round"], "name": t[f"{me}_name"],
                              "oname": t[f"{op}_name"], "tml_file": f.parent.name + "/" + f.name,
                              "tml_score": t["score"], "tml_side": side})
            d["year"] = d["date"].dt.year
            out.append(pd.concat([d, c], axis=1))
    return _finish(pd.concat(out, ignore_index=True), "tml")


ALL = {"wta_api": ref_wta_api, "mcp": ref_mcp, "slam_pbp": ref_slam_pbp, "usopen": lambda: ref_ibm("usopen"),
       "wimbledon": lambda: ref_ibm("wimbledon"), "sofascore": ref_sofascore, "tennislive": ref_tennislive,
       "tdi": ref_tdi, "infosys": ref_infosys}


def load_all(names=None) -> pd.DataFrame:
    out = []
    for n, fn in ALL.items():
        if names and n not in names:
            continue
        try:
            r = fn()
            out.append(r)
            print(f"  ref {n}: {len(r):,} player-matches", flush=True)
        except Exception as e:  # noqa: BLE001
            print(f"  ref {n}: FAILED {type(e).__name__}: {e}", flush=True)
    return pd.concat(out, ignore_index=True)


def surname(name) -> str:
    """The longest word of a name, accents dropped: a fallback key when first names differ."""
    k = rc.name_key(name)
    ws = k.split()
    return max(ws, key=len) if ws else ""
