"""Merge-feasibility scan over the staged public dump.

Question: how do the staged sources join, at what scale, and what does that imply for the
structure of the cleaned database? Measures overlap between the two match sources that share a
layout (Sackmann archive, Tennis My Life), player-ID crosswalk coverage, how well odds, markets,
point-level data and exact-date sources attach to a provisional canonical singles-match table,
date precision, statistics availability and Polymarket pre-match price availability.

Link rule: exact player-name pair after normalisation (accents, case and punctuation removed;
tokens sorted so "Zhang Zhizhen" equals "Zhizhen Zhang"), inside a date window measured from the
tournament week (qualifying rows may precede it by up to 10 days, other rows by up to 3), nearest
tournament week wins and ties count as ambiguous. No fuzzy matching, so link rates are lower
bounds. The provisional canonical table (Sackmann rows plus Tennis My Life rows Sackmann lacks) is a
measuring device, not the merged database.

Reads data/dump read-only; writes data/studies/merge_feasibility/summary.json.
Run: ./python.sh src/eda/merge_feasibility/scan.py
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump"
OUT = ROOT / "data" / "studies" / "merge_feasibility"
FIRST_YEAR = 2010
SACKMANN_LOWER_TIER_END = "2026-06-02"
T0 = time.time()

MATCH_COLS = ["tourney_id", "tourney_name", "tourney_level", "tourney_date", "winner_id", "winner_name",
              "loser_id", "loser_name", "score", "round", "w_svpt", "l_svpt", "winner_rank", "loser_rank"]
SACKMANN = [  # (glob under data/dump, tour, population)
    ("matches/sackmann_archive/atp/atp_matches_[0-9]*.parquet", "atp", "main"),
    ("matches/sackmann_archive/atp/atp_matches_qual_chall_*.parquet", "atp", "qual_chall"),
    ("matches/sackmann_archive/atp/atp_matches_futures_*.parquet", "atp", "futures"),
    ("matches/sackmann_archive/wta/wta_matches_[0-9]*.parquet", "wta", "main"),
    ("matches/sackmann_archive/wta/wta_matches_qual_itf_*.parquet", "wta", "qual_itf"),
]
TML = [
    ("matches/tennis_my_life/atp_main/[0-9]*.parquet", "atp", "main"),
    ("matches/tennis_my_life/atp_challenger/*_challenger.parquet", "atp", "challenger"),
    ("matches/tennis_my_life/atp_qualifying/*_atp_quali.parquet", "atp", "qualifying"),
    ("matches/tennis_my_life/wta_main/*_wta.parquet", "wta", "main"),
    ("matches/tennis_my_life/ongoing/ongoing_tourneys.parquet", "atp", "ongoing"),
    ("matches/tennis_my_life/ongoing/challenger_ongoing_tourneys.parquet", "atp", "ongoing"),
    ("matches/tennis_my_life/ongoing/wta_ongoing_tourneys.parquet", "wta", "ongoing"),
]


def log(msg):
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def norm(name) -> str:
    name = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", name).split())


def name_key(name) -> str:
    return " ".join(sorted(norm(name).split()))


def keys_for(series: pd.Series) -> pd.Series:
    series = series.fillna("").astype(str)
    return series.map({u: name_key(u) for u in series.unique()})


def pair_of(a: pd.Series, b: pd.Series) -> pd.Series:
    pair = pd.Series(np.where(a < b, a + "|" + b, b + "|" + a), index=a.index)
    return pair.where((a != "") & (b != ""), "")


def pct(n, d):
    return round(100.0 * n / d, 1) if d else None


def file_year(path: Path):
    m = re.search(r"(\d{4})", path.name)
    return int(m.group(1)) if m else None


def records(frame: pd.DataFrame):
    return json.loads(frame.to_json(orient="records"))


# ---------------------------------------------------------------- linking helpers

def link(left, right, on, left_date="tdate", right_date="date") -> pd.DataFrame:
    """All candidate pairs (ri, li) agreeing on `on`, with gap = right date minus left date in days."""
    lcols = left[on + [left_date]].rename(columns={left_date: "_dl"}).assign(li=left.index)
    rcols = right[on + [right_date]].rename(columns={right_date: "_dr"}).assign(ri=right.index)
    j = rcols.merge(lcols, on=on)
    return j.assign(gap=(j["_dr"] - j["_dl"]).dt.days)[["ri", "li", "gap"]]


def resolve(links, left_is_qual=None, window=(-3, 21)):
    """One link per right row: gap inside window (qualifying left rows may start 10 days early),
    nearest candidate wins, ties are ambiguous. Returns (status by ri, unique links)."""
    low = np.full(len(links), window[0])
    if left_is_qual is not None:
        low = np.where(left_is_qual.reindex(links["li"]).to_numpy(dtype=bool), -10, window[0])
    links = links[(links["gap"] >= low) & (links["gap"] <= window[1])]
    links = links.assign(dist=links["gap"].abs())
    top = links[links["dist"] == links.groupby("ri")["dist"].transform("min")]
    n = top.groupby("ri")["li"].nunique()
    unique = top[top["ri"].isin(n.index[n == 1])].drop_duplicates("ri")
    return n, unique


def statuses(index, n) -> pd.Series:
    status = pd.Series("unlinked", index=index, dtype=object)
    status.loc[n.index[n == 1]] = "linked"
    status.loc[n.index[n > 1]] = "ambiguous"
    return status


def summarise_status(frame, status, by):
    t = pd.crosstab([frame[b] for b in by], status).reindex(columns=["linked", "ambiguous", "unlinked"], fill_value=0)
    t["rows"] = t.sum(axis=1)
    t["linked_pct"] = (100 * t["linked"] / t["rows"]).round(1)
    return records(t.reset_index())


def attach(name, left, frame, on, results, by, left_is_qual=None, window=(-3, 21), extra=None):
    """Link each `frame` row to one `left` (canonical) row and record rates overall and by `by`."""
    frame = frame[frame["pair"] != ""]
    n, unique = resolve(link(left, frame, on), left_is_qual, window)
    status = statuses(frame.index, n)
    res = {"rows": len(frame), "linked": int((status == "linked").sum()),
           "ambiguous": int((status == "ambiguous").sum()), "unlinked": int((status == "unlinked").sum())}
    res["linked_pct"] = pct(res["linked"], res["rows"])
    res["by"] = summarise_status(frame, status, by)
    if extra:
        res.update(extra(frame, status, unique))
    results.setdefault("links", {})[name] = res
    log(f"{name}: {res['linked']:,}/{res['rows']:,} linked ({res['linked_pct']}%), {res['ambiguous']:,} ambiguous")
    return frame, status, unique


# ---------------------------------------------------------------- canonical singles matches

def load_matches(spec, source) -> pd.DataFrame:
    frames = []
    for pattern, tour, population in spec:
        for f in sorted(DUMP.glob(pattern)):
            year = file_year(f)
            if year is not None and year < FIRST_YEAR:
                continue
            df = pd.read_parquet(f, columns=MATCH_COLS)
            df["tour"], df["population"], df["file"] = tour, population, f.name
            frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df["source"] = source
    df["tdate"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
    df["round"] = df["round"].fillna("").str.upper().replace({"3RD/4TH": "BR"})
    df["wkey"], df["lkey"] = keys_for(df["winner_name"]), keys_for(df["loser_name"])
    df["pair"] = pair_of(df["wkey"], df["lkey"])
    svpt = [pd.to_numeric(df[c], errors="coerce").fillna(0) for c in ("w_svpt", "l_svpt")]
    df["has_stats"] = (svpt[0] > 0) & (svpt[1] > 0)
    level = df["tourney_level"].fillna("")
    df["is_qual"] = df["round"].str.fullmatch(r"Q\d+")
    df["tid"] = df["tourney_id"].fillna("").str.replace(r"-0+(\d)", r"-\1", regex=True)
    df["tier"] = np.select(
        [level.eq("G"), df["population"].eq("futures") | level.str.fullmatch(r"\d+(\+H)?") | level.eq("S"),
         level.eq("C") | df["population"].eq("challenger"), level.eq("D")],
        ["slam", "itf", "challenger", "team"], default="tour")
    return df


def anchor_links(sack, rest):
    """Same tour, tournament id and round with one identical player name. In singles a player plays one
    match per round, so the other player is the same person under another spelling, or a conflict."""
    cands = []
    for rside in ("wkey", "lkey"):
        for lside in ("wkey", "lkey"):
            r = rest[["tour", "tid", "round", rside]].rename(columns={rside: "k"}).assign(ri=rest.index)
            s = sack[["tour", "tid", "round", lside]].rename(columns={lside: "k"}).assign(li=sack.index)
            cands.append(r.merge(s, on=["tour", "tid", "round", "k"])[["ri", "li"]])
    c = pd.concat(cands).drop_duplicates()
    n = c.groupby("ri")["li"].nunique()
    return n, c[c["ri"].isin(n.index[n == 1])].drop_duplicates("ri")


def build_canonical(results):
    sack = load_matches(SACKMANN, "sackmann")
    tml = load_matches(TML, "tml")
    log(f"loaded Sackmann {len(sack):,} and TML {len(tml):,} singles rows ({FIRST_YEAR}+ files)")
    out = {}
    for name, df in (("sackmann", sack), ("tml", tml)):
        named = df[df["pair"] != ""]
        out[name] = {"rows": len(df), "rows_missing_a_name": int((df["pair"] == "").sum()),
                     "exact_duplicate_matches": int(named.duplicated(subset=["tour", "round", "pair", "tdate"]).sum()),
                     "rows_by_population": records(df.groupby(["tour", "population"]).size().rename("rows").reset_index()),
                     "latest_tourney_week": records(df.groupby(["tour", "population"])["tdate"].max().dt.strftime("%Y-%m-%d")
                                                    .rename("latest").reset_index())}
    sack = sack[sack["pair"] != ""].drop_duplicates(subset=["tour", "round", "pair", "tdate"])
    tml = tml[tml["pair"] != ""].drop_duplicates(subset=["tour", "round", "pair", "tdate"])

    # pass 1: exact normalised name pair, same round, tournament weeks within 10 days
    n, ul = resolve(link(sack, tml.rename(columns={"tdate": "date"}), ["tour", "round", "pair"]), window=(-10, 10))
    status = statuses(tml.index, n).replace({"linked": "exact_name_pair"})
    # pass 2: one identical player in the same tournament and round (Sackmann rows not already taken)
    rest = tml[status == "unlinked"]
    n2, ul2 = anchor_links(sack.drop(index=ul["li"].unique()), rest)
    status.loc[n2.index[n2 == 1]] = "one_player_anchor"
    status.loc[n2.index[n2 > 1]] = "ambiguous"
    tml = tml.assign(status=status)
    cols = ["exact_name_pair", "one_player_anchor", "ambiguous", "unlinked"]
    t = pd.crosstab([tml["tour"], tml["population"]], status).reindex(columns=cols, fill_value=0)
    out["tml_rows_also_in_sackmann"] = records(t.assign(rows=t.sum(axis=1)).reset_index())
    tml["period"] = np.where(tml["tdate"] < "2026-05-25", "tourney week before 2026-05-25", "2026-05-25 on")
    t = pd.crosstab([tml["tour"], tml["period"]], status).reindex(columns=cols, fill_value=0)
    out["tml_rows_also_in_sackmann_by_period"] = records(t.reset_index())

    a = tml.loc[ul2["ri"], ["wkey", "lkey", "winner_id", "loser_id", "tour"]].reset_index(drop=True)
    b = sack.loc[ul2["li"], ["wkey", "lkey", "winner_id", "loser_id"]].reset_index(drop=True)
    w_anchor = (a["wkey"] == b["wkey"]) | (a["lkey"] == b["lkey"])  # same orientation
    other_a = np.where(a["wkey"] == b["wkey"], a["lkey"], np.where(a["lkey"] == b["lkey"], a["wkey"],
                       np.where(a["wkey"] == b["lkey"], a["lkey"], a["wkey"])))
    other_b = np.where(a["wkey"] == b["wkey"], b["lkey"], np.where(a["lkey"] == b["lkey"], b["wkey"],
                       np.where(a["wkey"] == b["lkey"], b["wkey"], b["lkey"])))
    variant = np.array([bool(set(x.split()) & set(y.split())) for x, y in zip(other_a, other_b)])
    out["one_player_anchor_links"] = {"count": len(a), "other_player_shares_a_name_token": int(variant.sum()),
                                      "other_player_different_person_or_unrelated_spelling": int((~variant).sum()),
                                      "winner_side_disagreement": int((~w_anchor).sum())}

    e1 = tml.loc[ul["ri"], ["wkey", "winner_id", "loser_id", "tour", "has_stats"]].reset_index(drop=True)
    s1 = sack.loc[ul["li"], ["wkey", "winner_id", "loser_id", "has_stats"]].reset_index(drop=True)
    same = e1["wkey"].to_numpy() == s1["wkey"].to_numpy()
    out["exact_pair_shared_matches"] = {
        "count": len(e1), "winner_disagreements": int((~same).sum()),
        "serve_stats_in_both": int((e1["has_stats"].to_numpy() & s1["has_stats"].to_numpy()).sum()),
        "serve_stats_only_tml": int((e1["has_stats"].to_numpy() & ~s1["has_stats"].to_numpy()).sum()),
        "serve_stats_only_sackmann": int((~e1["has_stats"].to_numpy() & s1["has_stats"].to_numpy()).sum())}

    # TML ATP website codes -> Sackmann ATP ids, learned from linked matches (both passes)
    atp1 = (e1["tour"].to_numpy() == "atp") & same
    atp2 = (a["tour"].to_numpy() == "atp") & w_anchor.to_numpy() & variant
    xw1 = pd.concat([pd.DataFrame({"code": e1.loc[atp1, c].to_numpy(), "sid": s1.loc[atp1, c].to_numpy()})
                     for c in ("winner_id", "loser_id")])
    xw2 = pd.concat([pd.DataFrame({"code": a.loc[atp2, c].to_numpy(), "sid": b.loc[atp2, c].to_numpy()})
                     for c in ("winner_id", "loser_id")])
    xw = pd.concat([xw1, xw2])
    per_code = xw.groupby("code")["sid"].nunique()
    per_sid = xw.groupby("sid")["code"].nunique()
    code_to_sid = xw.groupby("code")["sid"].agg(lambda s: s.value_counts().index[0])
    tml_atp = tml[tml["tour"] == "atp"]
    used_codes = set(pd.concat([tml_atp["winner_id"], tml_atp["loser_id"]]).dropna()) - {""}
    tml_only_atp = tml_atp[tml_atp["status"] == "unlinked"]
    only_codes = set(pd.concat([tml_only_atp["winner_id"], tml_only_atp["loser_id"]]).dropna()) - {""}
    out["crosswalk_tml_atp_code_to_sackmann_id"] = {
        "codes_used_in_tml_2010_on": len(used_codes),
        "codes_learned_exact_pass": int(xw1["code"].nunique()), "codes_learned_both_passes": int(len(per_code)),
        "codes_with_conflicting_sackmann_ids": int((per_code > 1).sum()),
        "sackmann_ids_with_several_codes": int((per_sid > 1).sum()),
        "codes_in_unlinked_tml_rows": len(only_codes),
        "codes_in_unlinked_tml_rows_with_a_learned_id": len(only_codes & set(code_to_sid.index))}
    other_sid = np.where(a["wkey"] == b["wkey"], b["loser_id"], b["winner_id"])
    sel = w_anchor.to_numpy() & variant
    out["one_player_anchor_links"]["players_found_under_a_second_spelling"] = int(
        pd.Series(a["tour"].to_numpy()[sel] + ":" + other_sid[sel]).nunique())

    canon = pd.concat([sack.assign(origin="sackmann"), tml[tml["status"] == "unlinked"].assign(origin="tml_only")],
                      ignore_index=True).drop(columns=["status", "period"])
    canon["year"] = canon["tdate"].dt.year

    def pid(ids, tour, origin):
        ids = ids.fillna("").astype(str)
        mapped = ids.map(code_to_sid)
        tml_atp_row = (origin == "tml_only") & (tour == "atp")
        out_ids = np.where(tml_atp_row & mapped.notna(), "atp:" + mapped.fillna(""),
                           np.where(tml_atp_row, "atpcode:" + ids, tour + ":" + ids))
        return pd.Series(out_ids, index=ids.index).where(ids != "", "")

    canon["pid_w"] = pid(canon["winner_id"], canon["tour"], canon["origin"])
    canon["pid_l"] = pid(canon["loser_id"], canon["tour"], canon["origin"])
    results["match_sources"] = out
    log(f"canonical singles table: {len(canon):,} matches")
    return canon


def measure_scale(canon, results):
    apps = pd.concat([canon[["pid_w", "tour", "tdate"]].rename(columns={"pid_w": "pid"}),
                      canon[["pid_l", "tour", "tdate"]].rename(columns={"pid_l": "pid"})])
    apps = apps[apps["pid"] != ""]
    per_player = apps.groupby("pid").size()
    heavy = per_player[per_player >= 50]
    recent = apps[apps["tdate"] >= "2022-01-01"]["pid"].nunique()
    score = canon["score"].fillna("")
    results["scale"] = {
        "canonical_singles_matches": len(canon),
        "matches_by_origin": canon["origin"].value_counts().to_dict(),
        "matches_by_tour_tier_qual": records(canon.groupby(["tour", "tier", "is_qual"]).size().rename("matches").reset_index()),
        "matches_per_year": {int(k): int(v) for k, v in canon.groupby("year").size().items()},
        "player_match_rows_two_per_match": len(apps),
        "distinct_players": int(per_player.size),
        "distinct_players_by_tour": apps.groupby("tour")["pid"].nunique().to_dict(),
        "distinct_players_active_2022_on": int(recent),
        "matches_per_player_quantiles": {str(k): float(v) for k, v in per_player.quantile([0.25, 0.5, 0.75, 0.9, 0.99]).round(0).items()},
        "players_with_fewer_than_5_matches_pct": pct((per_player < 5).sum(), per_player.size),
        "players_with_50_plus_matches": int(heavy.size),
        "share_of_player_match_rows_from_players_with_50_plus_pct": pct(heavy.sum(), len(apps)),
        "tml_atp_player_rows_without_sackmann_id": int(apps["pid"].str.startswith("atpcode:").sum()),
        "wide_feature_table_float32_GB": {f"{f}_features": round(len(apps) * f * 4 / 1e9, 2) for f in (50, 200, 500)},
        "score_markers_pct": {
            "retired": pct(score.str.contains("RET", case=False).sum(), len(canon)),
            "walkover": pct(score.str.contains("W/O|walkover", case=False).sum(), len(canon)),
            "default": pct(score.str.contains("DEF", case=False).sum(), len(canon)),
            "blank": pct(score.str.strip().eq("").sum(), len(canon))},
    }
    sel = canon[canon["year"].isin([2010, 2015, 2019, 2022, 2023, 2024, 2025, 2026])]
    table = (100 * sel.groupby(["tour", "tier", "is_qual", "year"])["has_stats"].mean()).round(1).unstack("year")
    table.columns = [str(c) for c in table.columns]
    results["serve_stats_available_pct"] = records(table.reset_index())
    log("scale measured")


def measure_players(canon, results):
    frames = []
    for tour in ("atp", "wta"):
        p = pd.read_parquet(DUMP / f"players/sackmann_archive/{tour}/{tour}_players.parquet",
                            columns=["player_id", "name_first", "name_last", "dob"])
        frames.append(p.assign(tour=tour))
    sp = pd.concat(frames, ignore_index=True)
    sp["nk"] = keys_for(sp["name_first"].fillna("") + " " + sp["name_last"].fillna(""))
    sp["pid"] = sp["tour"] + ":" + sp["player_id"]
    active = set(canon["pid_w"]) | set(canon["pid_l"])
    act = sp[sp["pid"].isin(active)]
    shared = act.groupby(["tour", "nk"])["pid"].transform("nunique") > 1
    out = {"sackmann_player_rows": len(sp), "sackmann_players_in_canonical_matches": int(len(act)),
           "active_players_sharing_a_normalised_name": int(shared.sum()),
           "most_shared_names": records(act[shared].groupby(["tour", "nk"]).size().rename("players")
                                        .sort_values(ascending=False).head(8).reset_index())}

    db = pd.read_parquet(DUMP / "players/tennis_my_life/ATP_Database.parquet", columns=["id", "player", "birthdate"])
    db["k"] = keys_for(db["player"]) + "|" + db["birthdate"].fillna("")
    sa = sp[(sp["tour"] == "atp") & (sp["dob"].fillna("") != "")]
    sa = sa.assign(k=sa["nk"] + "|" + sa["dob"]).drop_duplicates("k", keep=False)
    by_bio = db[db["birthdate"].fillna("") != ""].merge(sa[["k", "player_id"]], on="k")
    out["tml_atp_database_codes"] = len(db)
    out["tml_codes_matching_sackmann_by_name_and_birth_date"] = int(by_bio["id"].nunique())

    wta_names = dict(zip(sp.loc[sp["tour"] == "wta", "player_id"], sp.loc[sp["tour"] == "wta", "nk"]))
    tw = canon[(canon["origin"] == "tml_only") & (canon["tour"] == "wta")]
    ids = pd.concat([tw[["winner_id", "wkey"]].set_axis(["id", "k"], axis=1),
                     tw[["loser_id", "lkey"]].set_axis(["id", "k"], axis=1)]).drop_duplicates("id")
    known = ids["id"].map(wta_names)
    out["tml_only_wta_ids"] = {"distinct": len(ids), "found_in_sackmann_wta_players": int(known.notna().sum()),
                               "same_normalised_name": int((known == ids["k"]).sum())}

    lp = pd.read_parquet(DUMP / "players/live_tennis_api_zenodo/players.parquet", columns=["player_id", "sackmann_id"])
    lm = pd.read_parquet(DUMP / "matches/live_tennis_api_zenodo/matches.parquet", columns=["player1_id", "player2_id"])
    lpu = lp[lp["player_id"].isin(set(lm["player1_id"]) | set(lm["player2_id"]))]
    out["live_tennis_api_players_in_index"] = int(len(lpu))
    out["live_tennis_api_players_in_index_with_sackmann_id"] = int((lpu["sackmann_id"].fillna("") != "").sum())
    op = pd.read_parquet(DUMP / "players/open_tennis_data/players.parquet", columns=["preferred_source"])
    out["open_tennis_data_player_id_sources"] = op["preferred_source"].value_counts().to_dict()
    results["player_identity"] = out
    log("player identity measured")


# ---------------------------------------------------------------- satellite sources onto canonical

def td_key(raw) -> str:
    toks = str(raw).strip().split()
    if len(toks) < 2:
        return norm(raw)
    initial = next((c for c in norm(toks[-1]) if c.isalpha()), "")
    return norm(" ".join(toks[:-1])) + " " + initial


def td_variants(full) -> list[str]:
    """Every 'surname span + first initial' form of a full name, as tennis-data.co.uk abbreviates."""
    t = norm(full).split()
    if len(t) < 2:
        return [" ".join(t)]
    return sorted({" ".join(t[k:m]) + " " + t[0][0] for k in range(1, len(t)) for m in range(k + 1, len(t) + 1)})


def measure_tennis_data(canon, results) -> set:
    frames = []
    for f in sorted(DUMP.glob("odds/tennis_data_couk/*/*/*.parquet")):
        if file_year(f) < FIRST_YEAR:
            continue
        df = pd.read_parquet(f)
        odds_cols = [c for c in df.columns if re.fullmatch(r"(B365|PS|Max|Avg|BFE|EX|LB|UB)W", c)]
        quote = df[odds_cols].apply(pd.to_numeric, errors="coerce").gt(1.0).any(axis=1)
        frames.append(pd.DataFrame({"Date": df["Date"], "Winner": df["Winner"], "Loser": df["Loser"],
                                    "tour": f.parts[-3], "year": file_year(f), "has_quote": quote}))
    td = pd.concat(frames, ignore_index=True)
    td["date"] = pd.to_datetime(td["Date"], errors="coerce")
    td["wk"], td["lk"] = td["Winner"].map(td_key), td["Loser"].map(td_key)
    td["pair"] = (td["wk"] + ">" + td["lk"]).where((td["wk"] != "") & (td["lk"] != ""), "")
    main = canon[canon["tier"].isin(["slam", "tour", "team"]) & ~canon["is_qual"]]
    ex = pd.DataFrame({"idx": main.index, "tour": main["tour"], "tdate": main["tdate"],
                       "wv": main["winner_name"].map(td_variants), "lv": main["loser_name"].map(td_variants)})
    ex = ex.explode("wv").explode("lv")
    ex["pair"] = ex["wv"] + ">" + ex["lv"]
    ex = ex.set_index("idx")[["tour", "tdate", "pair"]]

    def extra(frame, status, unique):
        un = frame[status == "unlinked"]
        swapped = un.assign(pair=un["lk"] + ">" + un["wk"])
        sn, _ = resolve(link(ex, swapped, ["tour", "pair"]), window=(-7, 20))
        return {"unlinked_that_link_with_winner_and_loser_swapped": int((sn == 1).sum()),
                "linked_rows_with_a_bookmaker_quote": int(frame.loc[unique["ri"], "has_quote"].sum()),
                "match_day_minus_tourney_week_days_p5_p50_p95": unique["gap"].quantile([0.05, 0.5, 0.95]).tolist()}

    results["tennis_data_rows_2010_on"] = len(td)
    _, _, unique = attach("tennis_data_couk_to_canonical", ex, td, ["tour", "pair"], results, ["tour", "year"],
                          window=(-7, 20), extra=extra)
    return set(unique["li"])


def parse_list(s):
    try:
        v = json.loads(s)
        return v if isinstance(v, list) else []
    except (TypeError, ValueError):
        return []


def measure_polymarket(canon, results):
    mi = pd.read_parquet(DUMP / "odds/polymarket/market_index.parquet",
                         columns=["id", "question", "sportsMarketType", "gameStartTime", "outcomes", "outcomePrices",
                                  "event_id"])
    ev = pd.read_parquet(DUMP / "odds/polymarket/event_index.parquet", columns=["id", "bucket", "sport_date"])
    ml = mi[mi["sportsMarketType"] == "moneyline"].merge(ev.rename(columns={"id": "event_id"}), on="event_id", how="left")
    q = ml["question"].fillna("")
    singles = ml[~q.str.contains("/", regex=False) & ~q.str.contains(" & ", regex=False)].copy()
    parts = singles["question"].str.split(r"\s+vs\.?\s+", regex=True)
    keep = parts.str.len() == 2
    singles, parts = singles[keep].copy(), parts[keep]
    singles["a"] = parts.str[0].str.rsplit(":", n=1).str[-1].str.strip()
    singles["b"] = parts.str[1].str.strip()
    singles["ak"], singles["bk"] = keys_for(singles["a"]), keys_for(singles["b"])
    singles["pair"] = pair_of(singles["ak"], singles["bk"])
    start = pd.to_datetime(singles["gameStartTime"], utc=True, errors="coerce")
    start = start.fillna(pd.to_datetime(singles["sport_date"], utc=True, errors="coerce"))
    singles["date"] = start.dt.tz_convert(None).dt.normalize()
    singles["month"] = singles["date"].dt.strftime("%Y-%m")
    singles["period"] = np.where(singles["date"] < SACKMANN_LOWER_TIER_END, "before 2026-06-02", "2026-06-02 on")
    singles["bucket"] = singles["bucket"].fillna("(none)")
    results["polymarket"] = {"contracts": len(mi), "moneyline_markets": len(ml),
                             "contracts_by_type": mi["sportsMarketType"].fillna("(none)").value_counts().to_dict(),
                             "singles_moneylines_parsed": len(singles)}
    known = set(canon["wkey"]) | set(canon["lkey"])

    def extra(frame, status, unique):
        un = frame[status == "unlinked"]
        a_known, b_known = un["ak"].isin(known), un["bk"].isin(known)
        reason = pd.Series(np.select([a_known & b_known, a_known ^ b_known],
                                     ["both names in match data", "one name in match data"], "neither name in match data"),
                           index=un.index)
        m = frame.loc[unique["ri"]].reset_index(drop=True)
        c = canon.loc[unique["li"], ["wkey", "lkey", "score"]].reset_index(drop=True)
        outcomes, prices = m["outcomes"].map(parse_list), m["outcomePrices"].map(parse_list)
        agree = disagree = 0
        for o, p, wk, lk in zip(outcomes, prices, c["wkey"], c["lkey"]):
            if len(o) != 2 or p not in (["1", "0"], ["0", "1"]):
                continue
            t = set(norm(o[p.index("1")]).split())
            in_w, in_l = t <= set(wk.split()), t <= set(lk.split())
            agree += in_w and not in_l
            disagree += in_l and not in_w
        half = prices.map(lambda p: p == ["0.5", "0.5"]).to_numpy()
        sc = c["score"].fillna("")[half]
        return {"unlinked_by_reason": records(pd.crosstab([frame.loc[un.index, "bucket"], frame.loc[un.index, "period"]], reason).reset_index()),
                "settled_winner_vs_match_data_winner": {"agree": agree, "disagree": disagree},
                "linked_settled_at_half": {"markets": int(half.sum()),
                                           "match_score_says_walkover": int(sc.str.contains("W/O|walkover", case=False).sum()),
                                           "match_score_says_retired": int(sc.str.contains("RET", case=False).sum())},
                "by_month": summarise_status(frame, status, ["month"])}

    frame, status, unique = attach("polymarket_singles_moneylines_to_canonical", canon[["tdate", "pair"]], singles,
                                   ["pair"], results, ["bucket", "period"], left_is_qual=canon["is_qual"], extra=extra)
    return frame


def measure_prices(results, singles):
    ts = pd.to_datetime(singles["gameStartTime"], utc=True, errors="coerce")
    starts = pd.DataFrame({"market_id": singles["id"], "bucket": singles["bucket"],
                           "start": (ts - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)})
    starts = starts[ts.notna().to_numpy()]
    per_market = []
    for f in sorted(DUMP.glob("odds/polymarket/price_history/*/*.parquet")):
        df = pd.read_parquet(f, columns=["market_id", "t"]).merge(starts[["market_id", "start"]], on="market_id")
        if df.empty:
            continue
        df["t"] = pd.to_numeric(df["t"], errors="coerce")
        g = df.groupby("market_id").agg(n=("t", "size"), first=("t", "min"), start=("start", "first"))
        g = g.join(df[df["t"] < df["start"]].groupby("market_id").agg(last_pre=("t", "max")), how="left")
        per_market.append(g)
    pm = pd.concat(per_market)
    pm = pm[~pm.index.duplicated()].join(starts.set_index("market_id")[["bucket"]], how="left")
    pm["mins_last_pre"] = (pm["start"] - pm["last_pre"]) / 60
    pm["hours_before"] = (pm["start"] - pm["first"]) / 3600
    agg = pm.groupby("bucket").agg(markets=("n", "size"), median_minutes_observed=("n", "median"),
                                   median_hours_of_history_before_start=("hours_before", "median"),
                                   obs_within_60_min_before_start_pct=("mins_last_pre", lambda s: round(100 * (s <= 60).mean(), 1)))
    results["polymarket_prices_singles_moneylines"] = {"markets_with_history": len(pm), "rows": int(pm["n"].sum()),
                                                       "by_bucket": records(agg.round(1).reset_index())}
    log("prices measured")


def measure_detail_and_dates(canon, results, td_linked: set):
    left = canon[["tour", "tdate", "pair"]]
    frames = []
    for tour, f in (("atp", "charting-m-matches.parquet"), ("wta", "charting-w-matches.parquet")):
        m = pd.read_parquet(DUMP / "points/match_charting_project/metadata" / f, columns=["match_id", "Player 1", "Player 2", "Date"])
        frames.append(m.assign(tour=tour))
    mcp = pd.concat(frames, ignore_index=True)
    mcp["date"] = pd.to_datetime(mcp["Date"], format="%Y%m%d", errors="coerce")
    mcp = mcp[mcp["date"] >= f"{FIRST_YEAR}-01-01"].copy()
    mcp["pair"] = pair_of(keys_for(mcp["Player 1"]), keys_for(mcp["Player 2"]))
    mcp["year"] = mcp["date"].dt.year
    _, _, ul_mcp = attach("match_charting_project_to_canonical", left, mcp, ["tour", "pair"], results, ["tour"],
                          left_is_qual=canon["is_qual"])

    frames = [pd.read_parquet(f, columns=["match_id", "year", "slam", "player1", "player2"])
              for f in sorted(DUMP.glob("points/sackmann_archive/slam_pointbypoint/*-matches.parquet"))]
    slam = pd.concat(frames, ignore_index=True)
    # from about 2019 the Australian and French Open files abbreviate names ("N. Djokovic", "N Djokovic")
    abbrev = slam["player1"].fillna("").str.match(r"^[A-Z]\.?\s")
    slam["name_form"] = np.where(abbrev, "initial + surname", "full name")
    full = pair_of(keys_for(slam["player1"]), keys_for(slam["player2"]))

    def initial_first(s):  # "N. Djokovic" -> "djokovic>n" style surname key, as td_key builds
        toks = str(s).replace(".", " ").split()
        return (norm(" ".join(toks[1:])) + " " + norm(toks[0])[:1]) if len(toks) >= 2 else norm(s)

    short = pair_of(slam["player1"].map(initial_first), slam["player2"].map(initial_first))
    slam["pair"] = np.where(abbrev, short, full)
    slam["date"] = pd.to_datetime(slam["year"].astype(str) + "-07-01", errors="coerce")
    cs = canon[canon["tier"].eq("slam") & ~canon["is_qual"]]
    tn = cs["tourney_name"].map(norm)
    base = pd.DataFrame({"slam": np.select([tn.str.contains("australian"), tn.str.contains("roland|french"),
                                            tn.str.contains("us open"), tn.str.contains("wimbledon")],
                                           ["ausopen", "frenchopen", "usopen", "wimbledon"], ""),
                         "tdate": pd.to_datetime(cs["tdate"].dt.year.astype(str) + "-07-01", errors="coerce"),
                         "pair": cs["pair"], "w": cs["winner_name"], "l": cs["loser_name"]}, index=cs.index)
    variants = base.assign(wv=base["w"].map(td_variants), lv=base["l"].map(td_variants)).explode("wv").explode("lv")
    variants["pair"] = pair_of(variants["wv"], variants["lv"])
    slam_left = pd.concat([base[["slam", "tdate", "pair"]], variants[["slam", "tdate", "pair"]]])
    slam_left = slam_left.assign(_i=slam_left.index).drop_duplicates().drop(columns="_i")
    attach("slam_point_by_point_to_canonical", slam_left, slam, ["slam", "pair"], results, ["slam", "name_form"],
           window=(0, 0))

    lp = pd.read_parquet(DUMP / "players/live_tennis_api_zenodo/players.parquet", columns=["player_id", "name", "tour"])
    names = dict(zip(lp["player_id"], keys_for(lp["name"])))
    tours = dict(zip(lp["player_id"], lp["tour"]))
    lm = pd.read_parquet(DUMP / "matches/live_tennis_api_zenodo/matches.parquet",
                         columns=["match_id", "player1_id", "player2_id", "tier_key", "scheduled_time_utc"])
    lm["pair"] = pair_of(lm["player1_id"].map(names).fillna(""), lm["player2_id"].map(names).fillna(""))
    lm["tour"] = lm["player1_id"].map(tours)
    lm["date"] = pd.to_datetime(lm["scheduled_time_utc"], errors="coerce").dt.normalize()
    _, _, ul_lta = attach("live_tennis_api_index_to_canonical", left, lm, ["tour", "pair"], results, ["tier_key"],
                          left_is_qual=canon["is_qual"])

    otd = pd.read_parquet(DUMP / "matches/open_tennis_data/completed.parquet",
                          columns=["date", "match_id", "tour", "player1_name", "player2_name"])
    otd["pair"] = pair_of(keys_for(otd["player1_name"].map(lambda s: (parse_list(s) or [""])[0])),
                          keys_for(otd["player2_name"].map(lambda s: (parse_list(s) or [""])[0])))
    otd["date"] = pd.to_datetime(otd["date"], errors="coerce")
    otd["year"] = otd["date"].dt.year
    _, _, ul_otd = attach("open_tennis_data_to_canonical", left, otd, ["tour", "pair"], results, ["tour", "year"],
                          left_is_qual=canon["is_qual"])

    exact = set(ul_lta["li"]) | set(ul_otd["li"]) | set(ul_mcp["li"]) | td_linked
    window = canon[(canon["tdate"] >= "2023-01-01") & (canon["tdate"] < "2026-08-01")]
    cov = window.assign(exact_day=window.index.isin(list(exact)))
    results["exact_match_day_available_pct_tourney_weeks_2023_01_to_2026_07"] = records(
        (100 * cov.groupby(["tour", "tier", "is_qual"])["exact_day"].mean()).round(1).rename("pct").reset_index())
    log("detail layers and exact dates measured")


def measure_rankings(results):
    out = {}
    for tour in ("atp", "wta"):
        r = pd.concat([pd.read_parquet(f, columns=["ranking_date", "player"])
                       for f in sorted(DUMP.glob(f"rankings/sackmann_archive/{tour}/*.parquet"))])
        r = r[r["ranking_date"] >= f"{FIRST_YEAR}0101"]
        out[tour] = {"rows": len(r), "ranking_dates": int(r["ranking_date"].nunique()), "first": r["ranking_date"].min(),
                     "last": r["ranking_date"].max(), "players": int(r["player"].nunique())}
    results["rankings_2010_on"] = out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "scope": f"singles, files for {FIRST_YEAR} onward, staged dump as of 2026-09-22",
               "link_rule": " ".join(__doc__.split("Link rule:")[1].split("Reads data/dump")[0].split())}
    canon = build_canonical(results)
    measure_scale(canon, results)
    measure_players(canon, results)
    td_linked = measure_tennis_data(canon, results)
    singles = measure_polymarket(canon, results)
    measure_prices(results, singles)
    measure_detail_and_dates(canon, results, td_linked)
    measure_rankings(results)
    (OUT / "summary.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    log(f"wrote {OUT / 'summary.json'}")


if __name__ == "__main__":
    main()
