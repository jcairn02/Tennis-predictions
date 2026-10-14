"""A3-referee review: shared loaders, referees and the Stage 0 box checks, replicated (read-only).

Everything here reads; nothing writes outside data/studies/input_data_audit/fixes/A3-referee/.

Referees
    mcp_totals(tour)     Match Charting Project per player-match totals (charting-*-stats-Overview.csv, set 'Total')
    wta_api_totals()     WTA API whole-match statistics (setnum 0) per player, in Stage 0's nine counts
Stage 0
    stage0()             live (7 Oct) tables: matches and player rows
    wide(m, p)           one row per match, winner (w_) and loser (l_) counts in Stage 0 names
    sackmann_raw(tour)   Sackmann's staged raw rows (with _source_file, _row)
Checks
    box_checks(...)      Stage 0's B0-B9 on a candidate box (replicated from stage0_build.box_scores) and the
                         same frame passed through stage0_build.box_scores itself, to prove the replica
"""
from __future__ import annotations

import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data/studies/input_data_audit/fixes/A3-referee"
AUD = ROOT / "data/studies/input_data_audit"
S0 = ROOT / "data/studies/predictability_diagnostic"
SACK = ROOT / "data/dump/matches/sackmann_archive"
TML = ROOT / "data/dump/matches/tennis_my_life"
MCP = ROOT / "data/raw/public_dump/match_charting_project"
WTA = ROOT / "data/dump/points/wta"
PTS = ROOT / "data/dump/points"

BOX = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"]
SRC = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
       "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_colwidth", 80)


def rd(path: Path) -> pd.DataFrame:
    t = pq.ParquetFile(path).read().to_pandas()
    return t.loc[:, ~t.columns.duplicated()]


@lru_cache(maxsize=None)
def name_key(name) -> str:
    """Accents dropped, lower case, words sorted (as the audit's common.name_key)."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower()
    return " ".join(sorted(re.findall(r"[a-z]+", s)))


def keys(s: pd.Series) -> pd.Series:
    return s.map(name_key)


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.astype("string").str.strip().replace("", pd.NA), errors="coerce")


# ------------------------------------------------------------------------------------------------
# Stage 0

def stage0() -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.read_parquet(S0 / "stage0_matches.parquet")
    p = pd.read_parquet(S0 / "stage0_match_players.parquet")
    return m, p


def wide(m: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    """One row per match: match columns, then the winner's (w_) and loser's (l_) id, name, games and nine counts."""
    keep = ["match_id", "player_id", "player_name", "won", "games_won_n", "games_won_d", "tb_won_n", "tb_won_d",
            "sets_won_n"] + BOX
    w = p.loc[p["won"], keep].drop(columns="won")
    l_ = p.loc[~p["won"], keep].drop(columns="won")
    w = w.rename(columns={c: f"w_{c}" for c in keep if c != "match_id"})
    l_ = l_.rename(columns={c: f"l_{c}" for c in keep if c != "match_id"})
    return m.merge(w, on="match_id", how="left").merge(l_, on="match_id", how="left")


def sackmann_raw(tour: str, pattern: str | None = None) -> pd.DataFrame:
    files = sorted((SACK / tour).glob(pattern or f"{tour}_matches_*.parquet"))
    out = []
    for f in files:
        if "doubles" in f.name or f.name.endswith(".json"):
            continue
        r = pd.read_parquet(f)
        r["file"] = f.name
        out.append(r)
    return pd.concat(out, ignore_index=True)


def raw_counts(r: pd.DataFrame, side: str) -> pd.DataFrame:
    return pd.DataFrame({b: num(r[f"{side}_{SRC[b]}"]) for b in BOX}, index=r.index)


# ------------------------------------------------------------------------------------------------
# Referees

def mcp_totals(tour: str) -> pd.DataFrame:
    """MCP per player-match: the match's date, tournament, round, players, and the player's totals."""
    g = {"atp": "m", "wta": "w"}[tour]
    mm = pd.read_csv(MCP / f"charting-{g}-matches.csv", dtype=str, on_bad_lines="skip", encoding="utf-8")
    ov = pd.read_csv(MCP / f"charting-{g}-stats-Overview.csv", dtype=str, on_bad_lines="skip", encoding="utf-8")
    ov = ov[ov["set"].eq("Total")].copy()
    for c in ["serve_pts", "aces", "dfs", "first_in", "first_won", "second_in", "second_won", "bk_pts", "bp_saved",
              "return_pts", "return_pts_won"]:
        ov[c] = pd.to_numeric(ov[c], errors="coerce")
    mm["mdate"] = pd.to_datetime(mm["Date"], format="%Y%m%d", errors="coerce")
    x = mm.merge(ov, on="match_id")
    x["pk"] = keys(x["player"])
    other = np.where(x["player"].eq(x["Player 1"]), x["Player 2"], x["Player 1"])
    x["ok"] = pd.Series(other, index=x.index).map(name_key)
    x = x.drop_duplicates(["match_id", "player"])
    return x


WTA_MAP = {  # Stage 0 count -> function of the whole-match row and the side ('a' or 'b')
    "ace": lambda r, s, o: r[f"aces{s}"],
    "df": lambda r, s, o: r[f"dblflt{s}"],
    "svpt": lambda r, s, o: r[f"totservplayed{s}"],
    "first_in": lambda r, s, o: r[f"ptsplayed1stserv{s}"],
    "first_won": lambda r, s, o: r[f"ptswon1stserv{s}"],
    "second_won": lambda r, s, o: r[f"ptstotwonserv{s}"] - r[f"ptswon1stserv{s}"],
    "sv_gms": lambda r, s, o: r[f"servgamesplayed{s}"],
    "bp_faced": lambda r, s, o: r[f"breakptsplayed{o}"],
    "bp_saved": lambda r, s, o: r[f"breakptsplayed{o}"] - r[f"breakptsconv{o}"],
}


def wta_api_totals() -> pd.DataFrame:
    """WTA API, one row per singles player-match (whole match, setnum 0), with the nine counts in Stage 0's names,
    the player's and opponent's name keys, the event (tournament_id, year), draw (LS main / RS qualifying) and round."""
    st, ms = [], []
    for y in range(2019, 2027):
        t = rd(WTA / "stats" / f"{y}.parquet")
        st.append(t[t["setnum"].astype(str).eq("0")])
        ms.append(rd(WTA / "matches" / f"{y}.parquet"))
    st = pd.concat(st, ignore_index=True)
    ms = pd.concat(ms, ignore_index=True)
    st = st[st["match_id"].astype(str).str[:2].isin(["LS", "RS"])].copy()
    stat_cols = ["acesa", "acesb", "dblflta", "dblfltb", "ptswon1stserva", "ptswon1stservb", "ptsplayed1stserva",
                 "ptsplayed1stservb", "ptstotwonserva", "ptstotwonservb", "totservplayeda", "totservplayedb",
                 "breakptsconva", "breakptsconvb", "breakptsplayeda", "breakptsplayedb", "servgamesplayeda",
                 "servgamesplayedb", "pts1stservlosta", "pts1stservlostb", "totptswona", "totptswonb"]
    for c in stat_cols:
        st[c] = pd.to_numeric(st[c].astype("string").str.strip(), errors="coerce")
    for c in ["tournament_id", "year"]:
        st[c] = st[c].astype(str)
        ms[c] = ms[c].astype(str)
    ms = ms.drop_duplicates(["tournament_id", "year", "match_id"])
    st = st.drop_duplicates(["tournament_id", "year", "match_id"])
    st = st.merge(ms[["tournament_id", "year", "match_id", "RoundID", "ScoreString", "Winner", "PlayerNameFirstA",
                      "PlayerNameLastA", "PlayerNameFirstB", "PlayerNameLastB", "MatchState", "ResultString",
                      "MatchTimeStamp"]], on=["tournament_id", "year", "match_id"], how="left")
    rows = []
    for s, o in (("a", "b"), ("b", "a")):
        S, O = s.upper(), o.upper()
        d = pd.DataFrame({"tournament_id": st["tournament_id"], "year": st["year"], "wmatch": st["match_id"],
                          "draw": st["match_id"].str[:2], "round": st["RoundID"], "score": st["ScoreString"],
                          "result": st["ResultString"], "side": s,
                          "name": st[f"PlayerNameFirst{S}"].fillna("") + " " + st[f"PlayerNameLast{S}"].fillna(""),
                          "oname": st[f"PlayerNameFirst{O}"].fillna("") + " " + st[f"PlayerNameLast{O}"].fillna("")})
        for b in BOX:
            d[f"api_{b}"] = pd.to_numeric(WTA_MAP[b](st, s, o), errors="coerce")
        rows.append(d)
    out = pd.concat(rows, ignore_index=True)
    out["pk"], out["ok"] = keys(out["name"]), keys(out["oname"])
    return out


# ------------------------------------------------------------------------------------------------
# Score-derived counts and the box checks

def score_parts(score: pd.Series, short: pd.Series | None = None, level: pd.Series | None = None,
                status: pd.Series | None = None) -> pd.DataFrame:
    from src.eda.feature_alpha_audit.repair_data import plain_match_tiebreak
    from src.eda.predictability_diagnostic.stage0_build import score_counts
    short = short if short is not None else pd.Series(False, index=score.index)
    level = level if level is not None else pd.Series("", index=score.index)
    status = status if status is not None else pd.Series("completed", index=score.index)
    vals = [score_counts(plain_match_tiebreak(s, lv, st, sh), bool(sh))
            for s, lv, st, sh in zip(score.astype(str), level, status, short)]
    cols = ["sets_w", "sets_l", "games_w", "games_l", "tb_w", "tb_l", "std_tb", "has_bracket", "short_like", "last_done"]
    return pd.DataFrame(vals, columns=cols, index=score.index)


def box_checks(w: pd.DataFrame, l_: pd.DataFrame, score: pd.Series, status: pd.Series, status_detail: pd.Series,
               short: pd.Series | None = None) -> pd.DataFrame:
    """Stage 0's checks on a candidate box (w, l: the nine counts in Stage 0 names, numeric, NaN = blank).

    Returns per match: B0..B9 flags (B5 drops service games only), 'fails_box' (any check that drops the box),
    'has_box' (Stage 0 would keep it), and 'has_box_stage0' from stage0_build.box_scores on the same frame."""
    from src.eda.predictability_diagnostic import stage0_build as SB
    idx = w.index
    sp = score_parts(score, short, None, status)
    games, std_tb = sp["games_w"] + sp["games_l"], sp["std_tb"]
    scored = status.isin(["completed", "retired", "other"]) & score.astype(str).ne("") & ~status_detail.eq("unknown")
    full = w[BOX].notna().all(axis=1) & l_[BOX].notna().all(axis=1)
    out = pd.DataFrame(index=idx)
    sv_total = w["sv_gms"] + l_["sv_gms"]
    excl = (sv_total - (games - std_tb)).abs() <= 1
    incl = (sv_total - games).abs() <= 1
    out["B5"] = (scored & sv_total.notna() & ~excl & ~incl).fillna(False)
    wf, lf = w.copy(), l_.copy()
    wf.loc[out["B5"], "sv_gms"] = np.nan
    lf.loc[out["B5"], "sv_gms"] = np.nan
    for k in ["B0", "B1", "B2", "B3", "B4", "B6", "B7", "B8"]:
        out[k] = False
    for f in (wf, lf):
        out["B0"] |= f.lt(0).any(axis=1)
        out["B1"] |= (f["first_in"] > f["svpt"]).fillna(False)
        out["B2"] |= (f["first_won"] > f["first_in"]).fillna(False)
        out["B3"] |= (f["second_won"] > f["svpt"] - f["first_in"]).fillna(False)
        out["B4"] |= (f["bp_saved"] > f["bp_faced"]).fillna(False)
        out["B6"] |= (f["df"] > f["svpt"] - f["first_in"]).fillna(False)
        out["B7"] |= (f["ace"] > f["first_won"] + f["second_won"]).fillna(False)
        out["B8"] |= ((f["bp_faced"] - f["bp_saved"]) > f["sv_gms"]).fillna(False)
    pts = w["svpt"] + l_["svpt"]
    played = (games - std_tb) - np.where(status.eq("completed"), 0, 1)
    out["B9"] = (scored & (pts < SB.MIN_POINTS_PER_GAME * played)).fillna(False)
    out["fails_box"] = out[["B0", "B1", "B2", "B3", "B4", "B6", "B7", "B8", "B9"]].any(axis=1)
    out["full"] = full
    out["has_box"] = full & ~out["fails_box"]
    # the same frame through Stage 0's own function
    df = pd.DataFrame(index=idx)
    for side, f in (("w", w), ("l", l_)):
        for b in BOX:
            v = f[b]
            df[f"{side}_{SRC[b]}"] = v.map(lambda x: "" if pd.isna(x) else str(int(x)))
    df["games_w"], df["games_l"], df["std_tb"] = sp["games_w"], sp["games_l"], sp["std_tb"]
    df["status"], df["score"], df["status_detail"] = status.values, score.astype(str).values, status_detail.values
    df["rid"] = np.arange(len(df))
    df = SB.box_scores(df)
    out["has_box_stage0"] = df["has_box"].to_numpy()
    out["box_status_stage0"] = df["box_status"].to_numpy()
    return out


def definition_fails(f: pd.DataFrame) -> pd.Series:
    """second_won + df > svpt - first_in: impossible when serve points include double faults."""
    return (f["second_won"] + f["df"]) > (f["svpt"] - f["first_in"])


def games_identity(gw: pd.Series, gl: pd.Series, w: pd.DataFrame, l_: pd.DataFrame, tbw: pd.Series, tbl: pd.Series
                   ) -> pd.DataFrame:
    """games won = own service games - own breaks conceded + opponent's breaks conceded, per side.
    Tiebreak games may or may not be in the service games: the identity holds 'excl' (tiebreaks won added on top)
    or 'incl' (tiebreak games counted as service games). Returns per match whether each side fits either way."""
    bw, bl = w["bp_faced"] - w["bp_saved"], l_["bp_faced"] - l_["bp_saved"]
    out = pd.DataFrame(index=w.index)
    for name, g, own, ob, xb, tb in (("w", gw, w, bw, bl, tbw), ("l", gl, l_, bl, bw, tbl)):
        base = own["sv_gms"] - ob + xb
        fits_excl = (base + tb) == g
        fits_incl = base == g
        out[f"{name}_fits"] = (fits_excl | fits_incl)
    out["both_fit"] = out["w_fits"] & out["l_fits"]
    return out


def points_won(w: pd.DataFrame, l_: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    pw = w["first_won"] + w["second_won"] + (l_["svpt"] - l_["first_won"] - l_["second_won"])
    pl = l_["first_won"] + l_["second_won"] + (w["svpt"] - w["first_won"] - w["second_won"])
    return pw, pl


def progression(m: pd.DataFrame, p: pd.DataFrame, match_ids: list[str]) -> pd.DataFrame:
    """For each match: did the recorded winner / loser play a later round of the same event (tour, tournament_id)?"""
    from src.eda.predictability_diagnostic import common as PC
    sub = m[m["match_id"].isin(match_ids)][["match_id", "tour", "tournament_id", "round", "round_order"]]
    ev = m[m["tournament_id"].isin(sub["tournament_id"])][["match_id", "tour", "tournament_id", "round", "round_order",
                                                           "player_a_id", "player_b_id"]]
    rows = []
    for r in sub.itertuples():
        pw = p[(p["match_id"] == r.match_id) & p["won"]]["player_id"].iloc[0]
        pl = p[(p["match_id"] == r.match_id) & ~p["won"]]["player_id"].iloc[0]
        later = ev[(ev["tour"] == r.tour) & (ev["tournament_id"] == r.tournament_id)
                   & (ev["round_order"] > r.round_order) & (ev["round"] != "RR")]
        # qualifying winners go on to the main draw (round_order of main-draw rounds is higher)
        wl = later[(later["player_a_id"] == pw) | (later["player_b_id"] == pw)]
        ll = later[(later["player_a_id"] == pl) | (later["player_b_id"] == pl)]
        rows.append({"match_id": r.match_id, "winner_plays_later": len(wl) > 0, "loser_plays_later": len(ll) > 0,
                     "winner_next": ";".join(sorted(set(wl["round"]))), "loser_next": ";".join(sorted(set(ll["round"])))})
    return pd.DataFrame(rows)
