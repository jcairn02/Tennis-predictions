"""Audit of Stage 0, check 3: linking Tennis My Life (TML) to Sackmann.

Two random samples, each row checked against the staged source rows directly (data/dump/matches):

    * 50 appended TML rows (source 'tml'): the staged TML row is read back and compared with the
      table; Sackmann's staged rows are searched for the same match (same two players by name,
      any round, tournament weeks within 45 days); and each player's id is compared with the name
      that id carries in Sackmann's rows.
    * 50 linked rows (Sackmann matches that a TML row was linked to): the staged Sackmann row is
      read back and compared with the table, and TML's staged rows are searched for the match the
      link claims (same two players by name, tournament weeks within 45 days), then compared
      (round, set scores, winner).

The same searches then run over every appended TML row and every linked row, so the samples'
findings can be sized.
Writes audit0/linking_sample_appended.csv, audit0/linking_sample_linked.csv and audit0/linking.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_linking.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

SEED = 20260930
NEAR = 45        # days: the same match, dated by either source's tournament week
WINDOW = 400     # days: Stage 0 also links misdated editions of an event up to 366 days apart
ROWCOLS = ["tourney_id", "tourney_name", "tourney_date", "round", "winner_id", "winner_name", "loser_id", "loser_name",
           "score"]


def set_key(score) -> str:
    """The set scores alone ('6-4 7-6'), written the same way for both sources: a walkover with no
    games is 'w/o'; an unstarted last set of a retirement ('6-4 0-0 RET') is dropped; a match
    tiebreak is 'mtb' whether written [10-8] or 1-0(8)."""
    sets, marks = A.parse_score(score)
    if not sets and ("w/o" in marks or "walkover" in marks):
        return "w/o"
    toks = []
    for i, (a, b, t, mtb) in enumerate(sets):
        last = i == len(sets) - 1
        if last and (a, b) == (0, 0):
            continue
        if mtb or (last and i >= 2 and max(a, b) == 1 and min(a, b) == 0):
            toks.append("mtb" if a > b else "mtb-l")
        else:
            toks.append(f"{a}-{b}")
    return " ".join(toks)


def same_winner(tml_w: pd.Series, s_w: pd.Series, s_l: pd.Series) -> np.ndarray:
    """The TML winner is the Sackmann winner: every word agrees, or they share a distinctive word
    that the Sackmann loser's name lacks ('Fred Gil' / 'Frederico Gil')."""
    exact = tml_w.map(A.full_key).to_numpy() == s_w.map(A.full_key).to_numpy()
    loose = np.array([A.same_person(a, b) and not A.same_person(a, c) for a, b, c in zip(tml_w, s_w, s_l)], dtype=bool)
    return exact | loose


def prepare_staged() -> pd.DataFrame:
    st = A.load_staged(ROWCOLS)
    for c in ("winner_name", "loser_name", "score", "round", "tourney_name", "winner_id", "loser_id"):
        st[c] = st[c].fillna("").astype(str).str.strip()
    st["d"] = pd.to_datetime(st["tourney_date"], format="%Y%m%d", errors="coerce")
    st["wk"], st["lk"] = st["winner_name"].map(A.full_key), st["loser_name"].map(A.full_key)
    st["pair"] = np.where(st["wk"] < st["lk"], st["wk"] + "|" + st["lk"], st["lk"] + "|" + st["wk"])
    st["sets"] = st["score"].map(set_key)
    return st


def word_pairs(frame: pd.DataFrame, a: str, b: str, key: str) -> pd.DataFrame:
    """One row per (distinctive word of player a, distinctive word of player b), sorted, for loose
    name matching; ``key`` identifies the row."""
    rows = []
    for k, x, y in zip(frame[key], frame[a], frame[b]):
        for u in A.distinctive(x):
            for v in A.distinctive(y):
                rows.append((k, u + "|" + v if u < v else v + "|" + u))
    return pd.DataFrame(rows, columns=[key, "wpair"]).drop_duplicates()


def search(targets: pd.DataFrame, pool: pd.DataFrame, tag: str) -> pd.DataFrame:
    """For each target (key, tour, d, pair, winner/loser names), the pool rows of the same tour
    whose two players match by name (every word, else a shared distinctive word for both) and whose
    tournament week is within WINDOW days."""
    exact = targets[["key", "tour", "d", "pair"]].merge(
        pool[["tour", "pair", "d", "_source_file", "_row"]].rename(columns={"d": "pd"}), on=["tour", "pair"])
    exact["how"] = "every word"
    tw = word_pairs(targets, "winner_name", "loser_name", "key").merge(targets[["key", "tour", "d"]], on="key")
    pool_small = pool[pool["d"].between(targets["d"].min() - pd.Timedelta(days=WINDOW),
                                        targets["d"].max() + pd.Timedelta(days=WINDOW))]
    pw = word_pairs(pool_small.assign(pk=pool_small.index), "winner_name", "loser_name", "pk")
    pw = pw.merge(pool_small[["tour", "d", "_source_file", "_row"]].rename(columns={"d": "pd"}), left_on="pk",
                  right_index=True)
    loose = tw.merge(pw, on=["tour", "wpair"])[["key", "tour", "d", "pd", "_source_file", "_row"]]
    loose["how"] = "shared words"
    cand = pd.concat([exact.drop(columns="pair"), loose], ignore_index=True)
    cand = cand[(cand["pd"] - cand["d"]).dt.days.abs() <= WINDOW]
    cand = cand.sort_values("how").drop_duplicates(["key", "_source_file", "_row"])   # 'every word' before 'shared words'
    cand = cand.merge(pool[["_source_file", "_row", "round", "sets", "winner_name", "loser_name", "tourney_name", "score",
                            "winner_id", "loser_id"]], on=["_source_file", "_row"])
    return cand.rename(columns={c: f"{tag}_{c}" for c in ("round", "sets", "winner_name", "loser_name", "tourney_name",
                                                          "score", "winner_id", "loser_id", "_source_file", "_row", "pd",
                                                          "how")})


def sackmann_names(m: pd.DataFrame, mp: pd.DataFrame) -> pd.Series:
    """player id -> the name it most often carries in Sackmann's matches of the table."""
    sk = mp[mp["match_id"].isin(m.loc[m["source"].eq("sackmann"), "match_id"])]
    top = sk.groupby(["player_id", "player_name"]).size().rename("n").reset_index()
    return top.sort_values(["player_id", "n"], ascending=[True, False]).drop_duplicates("player_id").set_index(
        "player_id")["player_name"]


event_words = A.event_words


def anchor_check(rows: pd.DataFrame, pool: pd.DataFrame) -> set:
    """Keys of rows for which TML holds a row of the same tournament id (leading zeros dropped) and
    round, sharing one player by name, with the same set scores: the same match, the other player's
    name spelled differently (as Stage 0's one-player anchor reads it)."""
    p = pool.assign(tid=pool["tourney_id"].str.replace(r"-0+(\d)", r"-\1", regex=True),
                    rnd=pool["round"].str.upper())
    j = rows[["key", "tour", "tournament_id", "round", "winner_name", "loser_name", "sets"]].merge(
        p[["tour", "tid", "rnd", "winner_name", "loser_name", "sets"]].rename(
            columns={"tid": "tournament_id", "rnd": "round", "winner_name": "tw", "loser_name": "tl", "sets": "tsets"}),
        on=["tour", "tournament_id", "round"])
    j = j[j["sets"].eq(j["tsets"]) & j["sets"].ne("")]
    one = [A.same_person(a, c) or A.same_person(a, d) or A.same_person(b, c) or A.same_person(b, d)
           for a, b, c, d in zip(j["winner_name"], j["loser_name"], j["tw"], j["tl"])]
    return set(j.loc[np.array(one, dtype=bool), "key"])


def split_ids(m: pd.DataFrame, mp: pd.DataFrame, st: pd.DataFrame) -> dict:
    """Players of appended rows kept under a TML code or a name ('atpcode:...', '...:name:...') whose
    exact name has a Sackmann id in Sackmann's staged rows: one player under two ids."""
    x = mp.merge(m[["match_id", "tour", "year", "evaluation"]], on="match_id")
    code = x[x["player_id"].str.startswith("atpcode:") | x["player_id"].str.contains(":name:")].copy()
    sk = st[st["source"].eq("sackmann")]
    nm = pd.concat([sk[["tour", "winner_id", "wk"]].set_axis(["tour", "sid", "key"], axis=1),
                    sk[["tour", "loser_id", "lk"]].set_axis(["tour", "sid", "key"], axis=1)])
    nm = nm[nm["sid"].ne("")]
    top = nm.groupby(["tour", "key"])["sid"].agg(lambda s: s.value_counts().index[0])
    code["key"] = code["player_name"].map(A.full_key)
    code["sackmann_id"] = [top.get((t, k)) for t, k in zip(code["tour"], code["key"])]
    has = code[code["sackmann_id"].notna()]
    num = code[code["player_id"].str.match(r"atpcode:\d+$")]
    return {"player_rows_under_code_or_name": int(len(code)), "distinct_ids": int(code["player_id"].nunique()),
            "matches": int(code["match_id"].nunique()),
            "whose_name_has_a_sackmann_id": {"player_rows": int(len(has)), "distinct_ids": int(has["player_id"].nunique()),
                                             "matches": int(has["match_id"].nunique()),
                                             "evaluation_matches": int(has.loc[has["evaluation"], "match_id"].nunique()),
                                             "by_year": has.groupby("year").size().to_dict()},
            "numeric_tml_codes": {"distinct": int(num["player_id"].nunique()), "player_rows": int(len(num)),
                                  "equal_to_the_sackmann_id_of_the_same_name":
                                      int((num["player_id"].str.split(":").str[1] == num["sackmann_id"]).sum())},
            "examples": has[["player_id", "player_name", "sackmann_id", "year"]].drop_duplicates("player_id").head(20)
            .to_dict(orient="records")}


def id_category(v: str) -> str:
    for head in ("other player", "code only, but the name has Sackmann id"):
        if v.startswith(head):
            return head
    return v


def id_verdict(pid: str, name: str, known: pd.Series, by_name: dict | None = None) -> str:
    if pid.startswith("atpcode:") or ":name:" in pid:
        sid = (by_name or {}).get(A.full_key(name))
        return f"code only, but the name has Sackmann id {sid}" if sid else "no Sackmann id"
    other = known.get(pid)
    if other is None:
        return "id not in Sackmann's rows"
    if A.full_key(other) == A.full_key(name):
        return "same name"
    return "name variant" if A.same_person(other, name) else f"other player ({other})"


def main() -> int:
    m = A.load_matches(["match_id", "tour", "tournament_id", "tournament_name", "tournament_date", "level", "qualifying",
                        "round", "score", "status", "source", "tml_link", "source_file", "source_row", "year",
                        "evaluation"])
    mp = A.load_players(["match_id", "player_id", "side", "won", "player_name"])
    names = A.names_by_side(mp)
    m = m.join(names, on="match_id")
    m["d"] = m["tournament_date"]
    m["wk"], m["lk"] = m["winner_name"].map(A.full_key), m["loser_name"].map(A.full_key)
    m["pair"] = np.where(m["wk"] < m["lk"], m["wk"] + "|" + m["lk"], m["lk"] + "|" + m["wk"])
    m["sets"] = m["score"].map(set_key)
    m["key"] = m["match_id"]
    st = prepare_staged()
    sk_pool, tml_pool = st[st["source"].eq("sackmann")], st[st["source"].eq("tml")]
    known = sackmann_names(m, mp)

    # ---------------------------------------------------------------- appended TML rows
    app = m[m["source"].eq("tml")].copy()
    own = app.merge(st[["_source_file", "_row"] + ROWCOLS + ["d"]].rename(columns={"d": "staged_d"}),
                    left_on=["source_file", "source_row"], right_on=["_source_file", "_row"], how="left")
    own["staged_found"] = own["_row"].notna()
    sw = own["winner_name_x"].eq(own["winner_name_y"].fillna("").str.strip())
    sl = own["winner_name_x"].eq(own["loser_name_y"].fillna("").str.strip())
    own["names_as_staged"] = np.select([sw & own["loser_name_x"].eq(own["loser_name_y"].fillna("").str.strip()), sl],
                                       ["same", "winner and loser exchanged (rule D5)"], "differ")
    own["score_as_staged"] = own["score_x"].eq(own["score_y"].fillna("").str.strip())
    own["round_as_staged"] = own["round_x"].eq(own["round_y"].fillna("").str.strip().str.upper())
    own["days_moved"] = (own["tournament_date"] - own["staged_d"]).dt.days
    hits = search(app, sk_pool, "sack")
    ak = app.set_index("key")
    hits["same_sets"] = hits["sack_sets"].eq(ak.loc[hits["key"], "sets"].to_numpy()) & hits["sack_sets"].ne("")
    hits["same_round"] = hits["sack_round"].str.upper().eq(ak.loc[hits["key"], "round"].to_numpy())
    hits["days"] = (hits["sack_pd"] - ak.loc[hits["key"], "d"].to_numpy()).dt.days.abs()
    hits["near"] = hits["days"] <= NEAR
    hits["exact"] = hits["sack_how"].eq("every word")
    hits["same_event_name"] = [bool(event_words(a) & event_words(b)) for a, b in
                               zip(hits["sack_tourney_name"], ak.loc[hits["key"], "tournament_name"])]
    # the same match: identical set scores and either the same event (a shared distinctive word in the
    # tournament name) or tournament weeks at most 7 days apart; within 45 days the player names may
    # differ if the round or event agrees, further apart they must agree word for word in the same
    # round and event (a misdated edition). Two events weeks apart with the same score are two matches.
    week = hits["days"] <= 7
    hits["same_match"] = hits["same_sets"] & (week | hits["same_event_name"]) & (
        (hits["near"] & (hits["exact"] | hits["same_round"] | hits["same_event_name"]))
        | (hits["same_round"] & hits["exact"] & hits["same_event_name"]))
    hits["other_scores"] = hits["near"] & hits["exact"] & ~hits["same_sets"]
    hits = hits[hits["same_match"] | hits["other_scores"]]
    best = hits.sort_values(["key", "same_match", "near", "same_round"], ascending=[True, False, False, False]) \
        .drop_duplicates("key")
    app = app.merge(best[["key", "sack_tourney_name", "sack_round", "sack_score", "sack_pd", "sack_how", "same_match",
                          "near", "same_round", "days", "sack__source_file", "sack__row"]], on="key", how="left")
    app["sackmann_holds_it"] = np.select(
        [app["same_match"].eq(True) & app["near"].eq(True), app["same_match"].eq(True), app["sack_round"].notna()],
        ["yes: same players and set scores, within 45 days",
         "yes: same players, set scores and round, 46-400 days apart (a misdated edition)",
         "same players within 45 days, other scores (another match)"], "no")
    sk_ids = pd.concat([sk_pool[["tour", "wk", "winner_id"]].set_axis(["tour", "key", "sid"], axis=1),
                        sk_pool[["tour", "lk", "loser_id"]].set_axis(["tour", "key", "sid"], axis=1)])
    sk_ids = sk_ids[sk_ids["sid"].ne("")].groupby(["tour", "key"])["sid"].agg(lambda s: s.value_counts().index[0])
    by_name = {t: sk_ids.xs(t).to_dict() for t in ("atp", "wta")}
    app["winner_id_check"] = [id_verdict(p, n, known, by_name[t]) for p, n, t in
                              zip(app["winner_id"], app["winner_name"], app["tour"])]
    app["loser_id_check"] = [id_verdict(p, n, known, by_name[t]) for p, n, t in
                             zip(app["loser_id"], app["loser_name"], app["tour"])]
    app = app.merge(own[["match_id", "staged_found", "names_as_staged", "score_as_staged", "round_as_staged",
                         "days_moved"]], on="match_id")
    wrong_id = app["winner_id_check"].str.startswith("other") | app["loser_id_check"].str.startswith("other")
    sample_a = app.sample(50, random_state=SEED)
    cols_a = ["match_id", "tournament_name", "tournament_date", "round", "winner_name", "loser_name", "score",
              "source_file", "source_row", "staged_found", "names_as_staged", "score_as_staged", "round_as_staged",
              "days_moved", "sackmann_holds_it", "sack_tourney_name", "sack_round", "sack_score", "sack_how",
              "winner_id", "winner_id_check", "loser_id", "loser_id_check"]
    sample_a[cols_a].to_csv(A.out_dir() / "linking_sample_appended.csv", index=False)

    # ---------------------------------------------------------------- linked Sackmann rows
    lk = m[m["source"].eq("sackmann") & m["tml_link"].ne("none")].copy()
    s_own = lk.merge(st[["_source_file", "_row"] + ROWCOLS], left_on=["source_file", "source_row"],
                     right_on=["_source_file", "_row"], how="left")
    s_own["names_as_staged"] = np.where(
        s_own["winner_name_x"].eq(s_own["winner_name_y"].fillna("").str.strip())
        & s_own["loser_name_x"].eq(s_own["loser_name_y"].fillna("").str.strip()), "same",
        np.where(s_own["winner_name_x"].eq(s_own["loser_name_y"].fillna("").str.strip()), "exchanged (rule D5)", "differ"))
    s_own["score_as_staged"] = s_own["score_x"].eq(s_own["score_y"].fillna("").str.strip())
    th = search(lk, tml_pool, "tml")
    kk = lk.set_index("key")
    th["same_sets"] = th["tml_sets"].eq(kk.loc[th["key"], "sets"].to_numpy()) & th["tml_sets"].ne("")
    th["same_round"] = th["tml_round"].str.upper().eq(kk.loc[th["key"], "round"].to_numpy())
    th["same_winner"] = same_winner(th["tml_winner_name"], kk.loc[th["key"], "winner_name"],
                                    kk.loc[th["key"], "loser_name"])
    th["winner_is_sackmann_loser"] = same_winner(th["tml_winner_name"], kk.loc[th["key"], "loser_name"],
                                                 kk.loc[th["key"], "winner_name"])
    th["days"] = (th["tml_pd"] - kk.loc[th["key"], "d"].to_numpy()).dt.days
    th["near"] = th["days"].abs() <= NEAR
    # the same match: same set scores (or both walkovers) and winner, dated within 45 days, or further
    # apart in the same round with the names agreeing word for word (a misdated edition, which
    # Stage 0 links up to 366 days)
    th["agree"] = th["same_sets"] & th["same_winner"] & (th["near"] | (th["same_round"] & th["tml_how"].eq("every word")))
    th = th[th["near"] | th["agree"]]
    per = th.groupby("key").agg(tml_rows_found=("tml__row", "size"), tml_rows_agreeing=("agree", "sum"))
    bestl = th.sort_values(["key", "agree", "same_round", "near"], ascending=[True, False, False, False]).drop_duplicates("key")
    lk = lk.merge(per, left_on="key", right_index=True, how="left").merge(
        bestl[["key", "tml_tourney_name", "tml_round", "tml_score", "tml_winner_name", "tml_loser_name", "tml_how",
               "same_sets", "same_round", "same_winner", "winner_is_sackmann_loser", "near", "days", "tml__source_file",
               "tml__row"]], on="key", how="left")
    lk["tml_rows_found"] = lk["tml_rows_found"].fillna(0).astype(int)
    lk["tml_rows_agreeing"] = lk["tml_rows_agreeing"].fillna(0).astype(int)
    agree = lk["tml_rows_agreeing"].ge(1)
    via_event = lk["key"].isin(anchor_check(lk[~agree], tml_pool))
    lk["verdict"] = np.select(
        [agree & lk["same_round"].eq(True) & lk["near"].eq(True),
         agree & lk["near"].eq(True),
         agree,
         via_event,
         lk["tml_rows_found"].ge(1) & lk["winner_is_sackmann_loser"].eq(True),
         lk["tml_rows_found"].ge(1) & lk["same_winner"].eq(True),
         lk["tml_rows_found"].ge(1)],
        ["agrees: players, set scores, winner and round, within 45 days",
         "agrees except the round label",
         "agrees: same match dated 46-400 days apart (misdated edition)",
         "agrees through the event: same tournament id and round, one player, same set scores",
         "disagrees: TML's winner is Sackmann's loser",
         "disagrees: same winner, other set scores",
         "disagrees: other"], "no TML row for the pair (45 days; 400 in the same round)")
    lk = lk.merge(s_own[["match_id", "names_as_staged", "score_as_staged"]], on="match_id")
    sample_l = lk.sample(50, random_state=SEED)
    cols_l = ["match_id", "tml_link", "tournament_name", "tournament_date", "round", "winner_name", "loser_name", "score",
              "source_file", "source_row", "names_as_staged", "score_as_staged", "verdict", "tml_rows_found",
              "tml_tourney_name", "tml_round", "tml_score", "tml_winner_name", "tml_loser_name", "days", "tml_how",
              "tml__source_file", "tml__row"]
    sample_l[cols_l].to_csv(A.out_dir() / "linking_sample_linked.csv", index=False)

    # the ids given to appended rows, across the table
    summary = {
        "appended": {
            "rows": int(len(app)), "staged_row_found": int(app["staged_found"].sum()),
            "names_as_staged": app["names_as_staged"].value_counts().to_dict(),
            "score_as_staged": int(app["score_as_staged"].sum()), "round_as_staged": int(app["round_as_staged"].sum()),
            "date_moved_days": app["days_moved"].value_counts().sort_index().to_dict(),
            "sackmann_holds_it": app.groupby(["sackmann_holds_it"]).size().to_dict(),
            "sackmann_holds_it_by_period": app.assign(period=np.where(app["tournament_date"] >= "2026-05-25", "2026-05-25 on",
                                                                      "before")).groupby(["period", "sackmann_holds_it"])
            .size().rename("rows").reset_index().to_dict(orient="records"),
            "sackmann_holds_it_by_kind": app.loc[app["sackmann_holds_it"].str.startswith("yes")].assign(
                kind=lambda f: np.select([f["tournament_name"].str.contains("Davis Cup"),
                                          f["tournament_name"].str.contains("BJK|Billie Jean", regex=True)],
                                         ["Davis Cup", "Billie Jean King Cup"], f["tournament_name"] + " " +
                                         f["year"].astype(str)))
            .groupby(["kind", "level"]).agg(rows=("match_id", "size"), evaluation=("evaluation", "sum")).reset_index()
            .to_dict(orient="records"),
            "sackmann_holds_it_rows": app.loc[app["sackmann_holds_it"].str.startswith("yes"),
                                              ["match_id", "score", "sack_tourney_name", "sack_round", "sack_score",
                                               "winner_id_check", "loser_id_check"]].to_dict(orient="records"),
            "id_checks": pd.concat([app["winner_id_check"], app["loser_id_check"]]).map(id_category)
            .value_counts().to_dict(),
            "rows_with_an_id_of_another_player": int(wrong_id.sum()),
            "rows_with_an_id_of_another_player_list": app.loc[wrong_id, ["match_id", "tournament_name", "winner_name",
                                                                         "winner_id_check", "loser_name", "loser_id_check",
                                                                         "sackmann_holds_it"]].to_dict(orient="records"),
            "sample": {"seed": SEED, "sackmann_holds_it": sample_a["sackmann_holds_it"].value_counts().to_dict(),
                       "id_checks": pd.concat([sample_a["winner_id_check"], sample_a["loser_id_check"]])
                       .map(id_category).value_counts().to_dict(),
                       "names_as_staged": sample_a["names_as_staged"].value_counts().to_dict(),
                       "score_as_staged": int(sample_a["score_as_staged"].sum()),
                       "round_as_staged": int(sample_a["round_as_staged"].sum()),
                       "periods": sample_a.assign(p=np.where(sample_a["tournament_date"] >= "2026-05-25", "2026-05-25 on",
                                                             "before"))["p"].value_counts().to_dict()},
        },
        "linked": {
            "rows": int(len(lk)), "by_link": lk["tml_link"].value_counts().to_dict(),
            "names_as_staged": lk["names_as_staged"].value_counts().to_dict(),
            "score_as_staged": int(lk["score_as_staged"].sum()),
            "verdict": lk["verdict"].value_counts().to_dict(),
            "verdict_by_link": lk.groupby(["tml_link", "verdict"]).size().rename("rows").reset_index()
            .to_dict(orient="records"),
            "sample": {"seed": SEED, "verdict": sample_l["verdict"].value_counts().to_dict(),
                       "by_link": sample_l["tml_link"].value_counts().to_dict(),
                       "names_as_staged": sample_l["names_as_staged"].value_counts().to_dict(),
                       "score_as_staged": int(sample_l["score_as_staged"].sum())},
            "evaluation_rows_by_verdict": lk[lk["evaluation"]]["verdict"].value_counts().to_dict(),
            "not_agreeing": lk.loc[~lk["verdict"].str.startswith("agrees"),
                                   ["match_id", "tml_link", "winner_name", "loser_name", "score", "verdict",
                                    "tml_tourney_name", "tml_round", "tml_score", "tml_winner_name", "tml_loser_name",
                                    "days"]].to_dict(orient="records"),
        },
        "identity_of_appended_players": split_ids(m, mp, st),
    }
    moved = app[app["days_moved"].abs() > 21]
    summary["appended"]["dates_moved_more_than_21_days"] = moved[["match_id", "tournament_name", "tournament_date",
                                                                  "days_moved", "source_file", "source_row"]] \
        .to_dict(orient="records")
    A.write_json("linking.json", summary)
    for part in ("appended", "linked", "identity_of_appended_players"):
        print(part, {k: v for k, v in summary[part].items() if not isinstance(v, list)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
