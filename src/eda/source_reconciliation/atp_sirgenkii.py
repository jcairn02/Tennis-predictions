"""Readers of SirGenkii's copy of the ATP Stats Centre, January-April 2025 (data/dump/points/sirgenkii_infotennis/,
decrypted ATP files kept as MySQL dumps by a third party):

    atp_ks_sirgenkii         the key statistics of the match (atp_key_stats.parquet, set_n 0)
    atp_sirgenkii_recount    the nine counts recounted from the rally analysis (atp_rally_analysis.parquet)

The key statistics, as held (observed, every match): only ONE player's rows carry values; the other player's rows are
-999 in every column, in all 929 matches and every set. And the serve statistics are shares, not counts (serve1 =
first serves in / serve points, serve1_pts_won, serve2_pts_won, service_points_won, break_points_saved), next to
counts of aces, double faults, service games, break points faced and converted, return games.
So the counts are reconstructed (reconstruct()):
    the present player's serve: the integers (svpt n, first_in f, first_won w1, second_won w2) with f/n, w1/f,
        w2/(n-f) and (w1+w2)/n equal to the four shares to their five decimals;
    the absent player's serve, from the present player's RETURN shares (serve1_return_pts_won = the absent player's
        first-serve points lost / first serves in, serve2_return_pts_won, return_points_won): (n_o, f_o, a, b) the same
        way, then first_won = f_o - a, second_won = n_o - f_o - b; service games = the present player's
        return_games_played; aces, double faults and break points are not given (NaN);
    a share fixes a count only up to a common multiple, so: points per service game between 3.5 and 12.5 (Stage 0's
        men: 4.75 to 10.25 from the 1st to the 99.9th percentile), and the two players' serve points must reproduce
        total_points_won; a player's counts are kept only when exactly one solution is left (x_recon says how many).
    bp_saved of the present player = break_points_saved x break_points_faced (an integer to rounding); the absent
        player's break points are not kept (break_points_converted is a share, not a count).
The recount: each rally entry names a player (player_id) and an outcome (W: that player won the point: ace, winner;
L: lost it: double fault, forced or unforced error), so the point's winner is known; pointId is
set_game_point_serve; the score is server-first; the server is derived (atp_recount.derive_servers) from the aces,
double faults and scores only. Its break-point flags p1_break_point / p2_break_point do not say whose serve is under
threat (on aces and double faults at break point, whose server is known, each flag is set about half the time whoever
serves: flag_semantics()), so a flagged point counts as a break point faced by the derived server ('either' reading;
the two side readings are measured and reported in break_flag_reading_test).
Linked by the event linker (season 2025, the ATP event id, the match code's draw and round, both ATP codes and names);
the sirgenkii link file of match_timing is empty. A rally match is identified by its own players' codes: at AO 2025
the rally analysis files other players under a code than the results table does (x_identity 'own_players').

Run: ./python.sh src/eda/source_reconciliation/atp_sirgenkii.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import atp_common as A  # noqa: E402
from src.eda.source_reconciliation import atp_points as P  # noqa: E402
from src.eda.source_reconciliation import atp_recount as R  # noqa: E402

TOL = 0.5e-5 + 1e-9
PPG = (3.5, 12.5)              # serve points per service game allowed
NMAX = 400


def num(s) -> pd.Series:
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v != -999)


def results() -> pd.DataFrame:
    r = pd.read_parquet(A.SIRG / "atp_results.parquet")
    r = r[r["match_id"].fillna("").str.match(r"^[mqMQ][sS]\d{3}$")].copy()
    r["code"] = r["match_id"].str.upper()
    r["source_key"] = r["year"].astype(str) + "_" + r["tournament_id"].astype(str) + "_" + r["code"]
    r = r.drop(columns=["match_id"])                  # the source's code; match_id is Stage 0's from here on
    r = r.drop_duplicates("source_key").set_index("source_key", drop=False)
    hint = [P.round_hint(c) for c in r["code"]]
    r["season"] = pd.to_numeric(r["year"], errors="coerce").fillna(-1).astype(int)
    r["ev"] = pd.to_numeric(r["tournament_id"], errors="coerce").fillna(-1).astype(int)
    r["qual"] = [h[0] for h in hint]
    r["round"] = [h[1] for h in hint]
    r["c1"], r["c2"] = r["player1_id"].map(A.atp_code), r["player2_id"].map(A.atp_code)
    r["f1"], r["f2"] = r["player1_name"].fillna(""), r["player2_name"].fillna("")
    return r


# ------------------------------------------------------------------------------------------------ reconstruction
def _solutions(r1, r1w, r2w, rsw, games) -> list[tuple]:
    """(n, f, w1, w2) with f/n = r1, w1/f = r1w, w2/(n-f) = r2w, (w1+w2)/n = rsw (to TOL), n/games in PPG."""
    if any(pd.isna(x) for x in (r1, r1w, r2w, rsw)) or pd.isna(games) or games <= 0:
        return []
    n = np.arange(1, NMAX + 1, dtype=float)
    f = np.round(r1 * n)
    ok = np.abs(f / n - r1) <= TOL
    w1 = np.round(r1w * f)
    ok &= np.where(f > 0, np.abs(w1 / np.maximum(f, 1) - r1w) <= TOL, True)
    s = n - f
    w2 = np.round(r2w * s)
    ok &= np.where(s > 0, np.abs(w2 / np.maximum(s, 1) - r2w) <= TOL, True)
    ok &= np.abs((w1 + w2) / n - rsw) <= TOL
    ok &= (n / games >= PPG[0]) & (n / games <= PPG[1])
    return [(int(a), int(b), int(c), int(d)) for a, b, c, d in zip(n[ok], f[ok], w1[ok], w2[ok])]


def _solutions_return(r1ret, r2ret, rpw, games) -> list[tuple]:
    """The absent player's serve from the present player's return shares: (n_o, f_o, a, b) with a/f_o = r1ret,
    b/(n_o-f_o) = r2ret, (a+b)/n_o = rpw (to TOL), n_o/games in PPG."""
    if any(pd.isna(x) for x in (r1ret, r2ret, rpw)) or pd.isna(games) or games <= 0:
        return []
    out = []
    for n in range(1, NMAX + 1):
        if not PPG[0] <= n / games <= PPG[1]:
            continue
        f = np.arange(0, n + 1, dtype=float)
        a = np.round(r1ret * f)
        ok = np.where(f > 0, np.abs(a / np.maximum(f, 1) - r1ret) <= TOL, a == 0)
        s = n - f
        b = np.round(r2ret * s)
        ok &= np.where(s > 0, np.abs(b / np.maximum(s, 1) - r2ret) <= TOL, b == 0)
        ok &= np.abs((a + b) / n - rpw) <= TOL
        out += [(n, int(x), int(y), int(z)) for x, y, z in zip(f[ok], a[ok], b[ok])]
    return out


def reconstruct(row: pd.Series) -> dict:
    """Both players' counts from the present player's set0 row: '<field>_me' and '<field>_opp', x_recon_* counts."""
    me = _solutions(row["serve1"], row["serve1_pts_won"], row["serve2_pts_won"], row["service_points_won"],
                    row["service_games_played"])
    opp = _solutions_return(row["serve1_return_pts_won"], row["serve2_return_pts_won"], row["return_points_won"],
                            row["return_games_played"])
    tpw = row["total_points_won"]
    pairs = []
    for m in me:
        for o in opp:
            sw = m[2] + m[3]
            rt = o[2] + o[3]
            if pd.isna(tpw) or abs((sw + rt) / (m[0] + o[0]) - tpw) <= TOL:
                pairs.append((m, o))
    out = {"x_recon_me": len(me), "x_recon_opp": len(opp), "x_recon_pairs": len(pairs)}
    nan = float("nan")
    mes = {p[0] for p in pairs} if pairs else set(me)
    ops = {p[1] for p in pairs} if pairs else set(opp)
    m = next(iter(mes)) if len(mes) == 1 else None
    o = next(iter(ops)) if len(ops) == 1 else None
    out["svpt_me"], out["first_in_me"], out["first_won_me"], out["second_won_me"] = m if m else (nan,) * 4
    if o:
        n_o, f_o, a, b = o
        out["svpt_opp"], out["first_in_opp"], out["first_won_opp"], out["second_won_opp"] = n_o, f_o, f_o - a, \
            n_o - f_o - b
    else:
        out["svpt_opp"] = out["first_in_opp"] = out["first_won_opp"] = out["second_won_opp"] = nan
    for side in ("me", "opp"):
        out[f"sv_won_{side}"] = out[f"first_won_{side}"] + out[f"second_won_{side}"]
    out["ace_me"], out["df_me"] = row["aces"], row["double_faults"]
    out["ace_opp"] = out["df_opp"] = nan
    out["sv_gms_me"], out["sv_gms_opp"] = row["service_games_played"], row["return_games_played"]
    bpf = row["break_points_faced"]
    out["bp_faced_me"] = bpf
    sv = row["break_points_saved"] * bpf if pd.notna(bpf) and pd.notna(row["break_points_saved"]) else nan
    out["bp_saved_me"] = float(round(sv)) if pd.notna(sv) and abs(sv - round(sv)) < 1e-3 else nan
    # the absent player's break points are not recoverable: break_points_converted is a share (0.5 with _pct 50),
    # not a count, and no count of break points created is kept (checked against Stage 0: 2% equal if read as a count)
    out["bp_faced_opp"] = out["bp_saved_opp"] = nan
    return out


def ks_sirgenkii(xw, linker, res: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    k = pd.read_parquet(A.SIRG / "atp_key_stats.parquet")
    k = k[k["set_n"].astype(str).eq("0")].copy()
    for c in k.columns:
        if c not in ("id", "year", "tournament_id", "match_id", "round", "set_n", "player_id", "opponent_id") \
                and not c.startswith("_"):
            k[c] = num(k[c])
    k["source_key"] = k["year"].astype(str) + "_" + k["tournament_id"].astype(str) + "_" + k["match_id"].str.upper()
    present = k[k["aces"].notna() | k["serve1"].notna()]
    info = {"reader": "atp_ks_sirgenkii", "source": "data/dump/points/sirgenkii_infotennis/atp_key_stats.parquet",
            "matches_with_set0_rows": int(k["source_key"].nunique()), "player_rows_set0": int(len(k)),
            "player_rows_with_values": int(len(present)),
            "matches_with_both_players_valued": int((present.groupby("source_key").size() > 1).sum())}
    present = present.drop_duplicates("source_key").set_index("source_key")
    rec = pd.DataFrame.from_dict({key: reconstruct(r) for key, r in present.iterrows()}, orient="index")
    info["reconstruction"] = {
        "present_player_unique": int(rec["svpt_me"].notna().sum()), "present_player_rows": int(len(rec)),
        "absent_player_unique": int(rec["svpt_opp"].notna().sum()),
        "solutions_present_player": rec["x_recon_me"].value_counts().sort_index().to_dict(),
        "solutions_absent_player": rec["x_recon_opp"].value_counts().sort_index().to_dict(),
        "joint_pairs": rec["x_recon_pairs"].value_counts().sort_index().to_dict()}
    m = res.join(present[["player_id"]].rename(columns={"player_id": "present_code"}), how="inner").join(rec)
    m["present_code"] = m["present_code"].map(A.atp_code)
    me_is_1 = m["present_code"].eq(m["c1"])
    me_is_2 = m["present_code"].eq(m["c2"])
    info["dropped"] = {"present_player_not_in_results": int((~me_is_1 & ~me_is_2).sum())}
    m = m[me_is_1 | me_is_2].copy()
    me_is_1 = m["present_code"].eq(m["c1"])
    for f in A.FIELDS:
        m[f"{f}_1"] = np.where(me_is_1, m[f"{f}_me"], m[f"{f}_opp"])
        m[f"{f}_2"] = np.where(me_is_1, m[f"{f}_opp"], m[f"{f}_me"])
    for side_no, is_me in (("1", me_is_1), ("2", ~me_is_1)):
        m[f"x_from_return_side_{side_no}"] = ~is_me
    lk = linker.link(m, xw)
    m = m.join(lk)
    info["linked"] = int(m["match_id"].notna().sum())
    info["link_methods"] = m["link_method"].value_counts().to_dict()
    info["unlinked"] = m.loc[m["match_id"].isna(), "unlinked_reason"].value_counts().to_dict()
    m = m[m["match_id"].notna()].copy()
    m["complete"] = True          # the copy keeps no completion flag; set0 of a played match (x_status: not given)
    m["x_status"] = "not given"
    m["x_season"] = m["season"]
    rows = A.long_rows(m, A.FIELDS + ["x_from_return_side"],
                       extra=["complete", "link_method", "x_status", "x_season", "x_recon_me", "x_recon_opp",
                              "x_recon_pairs"])
    rows["x_code"] = pd.concat([m["c1"], m["c2"]], ignore_index=True).to_numpy()
    info["note_complete"] = ("SirGenkii keeps no match-completion flag; complete=True means only that the copy holds "
                             "set0 statistics of the match")
    return A.to_contract(rows, "atp_ks_sirgenkii", "box"), info


# ------------------------------------------------------------------------------------------------ recount
def rally_engine_points(g: pd.DataFrame, c1: str, flags: str) -> list[dict]:
    """flags 'against': pX_break_point = a break point against pX's serve (pX = results' playerX), so bp1 (player 1
    can break) = p2's flag; 'for': pX_break_point = pX can break; 'either': the flags say only that the point is a
    break point (bp_any), not whose: they are not used as server evidence, and the break point is charged to the
    derived server (the reading the data support: on aces and double faults played at break point, whose server is
    known, p1's and p2's flags are each set about half the time whoever serves)."""
    out, seen = [], set()
    for r in g.itertuples(index=False):
        if r.point_id in seen:
            continue
        seen.add(r.point_id)
        parts = str(r.point_id).split("_")
        if len(parts) != 4:
            continue
        s, gm, p, sv = (P.as_int(x) for x in parts)
        subj = A.atp_code(r.player_id)
        won_by_subject = str(r.outcome).upper() == "W"
        subj_no = 1 if subj == c1 else 2
        winner = subj_no if won_by_subject else 3 - subj_no
        f1, f2 = P.truthy(r.p1_break_point), P.truthy(r.p2_break_point)
        q = {"set": s, "game": gm, "point": p, "serve": sv, "winner": winner, "end": str(r.point_end_type or ""),
             "score": r.score, "tb": P.truthy(r.tie_break)}
        if flags == "either":
            q.update(bp1=False, bp2=False, bp_any=f1 or f2)
        else:
            q["bp1"], q["bp2"] = (f2, f1) if flags == "against" else (f1, f2)
        out.append(q)
    return out


def flag_semantics() -> dict:
    """Which side SirGenkii's break-point flags name, on aces (the subject served and won) and double faults (the
    subject served and lost) played at break point by the score (server first: receiver at 40 against 0-30, or AD)."""
    r = pd.read_parquet(A.SIRG / "atp_rally_analysis.parquet",
                        columns=["year", "tournament_id", "match_id", "player_id", "point_end_type", "score",
                                 "p1_break_point", "p2_break_point"])
    res = pd.read_parquet(A.SIRG / "atp_results.parquet", columns=["year", "tournament_id", "match_id", "player1_id"])
    res = res[res["match_id"].fillna("").str.match(r"^[mq]s\d{3}$")].drop_duplicates(["year", "tournament_id",
                                                                                       "match_id"])
    r = r.merge(res, on=["year", "tournament_id", "match_id"], how="left")
    x = r[r["point_end_type"].isin(["ACE", "DOUBLE FAULT"])].copy()
    sc = x["score"].astype(str).str.upper().str.split("-", expand=True)
    x["bp_by_score"] = (sc[1].eq("40") & sc[0].isin(["0", "15", "30"])) | sc[1].eq("AD")
    x["server_is_p1"] = x["player_id"].str.upper().eq(x["player1_id"].str.upper())
    at = x[x["bp_by_score"]]
    return {"aces_and_double_faults_at_break_point": int(len(at)),
            "server_p1": {"p1_flag": int((at["server_is_p1"] & at["p1_break_point"].eq("1")).sum()),
                          "p2_flag": int((at["server_is_p1"] & at["p2_break_point"].eq("1")).sum())},
            "server_p2": {"p1_flag": int((~at["server_is_p1"] & at["p1_break_point"].eq("1")).sum()),
                          "p2_flag": int((~at["server_is_p1"] & at["p2_break_point"].eq("1")).sum())},
            "either_flag_set_at_break_point_by_score": round(float(
                (at["p1_break_point"].eq("1") | at["p2_break_point"].eq("1")).mean()), 4),
            "a_flag_set_off_break_point_by_score": int((~x["bp_by_score"] & (x["p1_break_point"].eq("1")
                                                                              | x["p2_break_point"].eq("1"))).sum())}


def recount_sirgenkii(xw, linker, res: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    r = pd.read_parquet(A.SIRG / "atp_rally_analysis.parquet")
    r["source_key"] = r["year"].astype(str) + "_" + r["tournament_id"].astype(str) + "_" + r["match_id"].str.upper()
    info = {"reader": "atp_sirgenkii_recount", "source": "data/dump/points/sirgenkii_infotennis/atp_rally_analysis.parquet",
            "matches_with_points": int(r["source_key"].nunique()), "point_rows": int(len(r))}
    m = res[res.index.isin(set(r["source_key"]))].copy()
    info["dropped"] = {"points_without_results_row": int(len(set(r["source_key"]) - set(res.index)))}
    # identity from the rally analysis's own players: at AO 2025 (event 580) its codes name other players than the
    # results row of the same match code (14 of 14 matches); everywhere else they agree
    own = r.groupby("source_key").apply(lambda g: sorted({A.atp_code(x) for x in set(g["player_id"])
                                                          | set(g["opponent_id"])}))
    name_of = dict(zip(res["c1"], res["f1"])) | dict(zip(res["c2"], res["f2"]))
    m["x_identity"] = "results"
    for key in m.index:
        pair = own.get(key, [])
        if len(pair) == 2 and set(pair) != {m.at[key, "c1"], m.at[key, "c2"]}:
            m.loc[key, ["c1", "c2"]] = pair
            m.loc[key, ["f1", "f2"]] = [name_of.get(pair[0], ""), name_of.get(pair[1], "")]
            m.loc[key, "round"] = ""
            m.loc[key, "x_identity"] = "own_players"
    info["identity"] = m["x_identity"].value_counts().to_dict()
    info["identity_own_players_events"] = m.loc[m["x_identity"].eq("own_players"), "ev"].value_counts().to_dict()
    groups = {}
    modes = ("against", "for", "either")
    test = {mode: {"aces_against": 0, "df_against": 0, "games_against_alt": 0} for mode in modes}
    for key, g in r[r["source_key"].isin(set(m.index))].groupby("source_key"):
        c1 = m.at[key, "c1"]
        for mode in modes:
            pts = rally_engine_points(g, c1, mode)
            _, d = R.derive_servers([dict(q) for q in pts])
            test[mode]["aces_against"] += d.get("aces_against_assigned_server", 0)
            test[mode]["df_against"] += d.get("double_faults_against_assigned_server", 0)
            test[mode]["games_against_alt"] += d.get("games_evidence_against_alternation", 0)
        groups[key] = rally_engine_points(g, c1, "either")
    info["break_flag_reading_test"] = test
    info["break_flag_semantics"] = flag_semantics()
    lk = linker.link(m, xw)
    m = m.join(lk)
    info["linked"] = int(m["match_id"].notna().sum())
    info["link_methods"] = m["link_method"].value_counts().to_dict()
    info["unlinked"] = m.loc[m["match_id"].isna(), "unlinked_reason"].value_counts().to_dict()
    lm = m[m["match_id"].notna()]
    ctx = P.stage0_context(lm["match_id"], lm["p1_side"])
    wide = P.recount_all({k: groups[k] for k in lm.index}, ctx, derive=True)
    wide = lm[["source_key", "match_id", "p1_side", "link_method", "season", "c1", "c2", "x_identity"]].join(wide) \
        .join(ctx)
    wide = wide.rename(columns={"s0_status": "x_s0_status", "season": "x_season"})
    wide["x_route"] = "rally-analysis"
    rows = P.to_long(wide, extra=["complete", "link_method", "x_route", "x_s0_status", "x_season", "x_identity"])
    rows["x_code"] = pd.concat([wide["c1"], wide["c2"]], ignore_index=True).to_numpy()
    info["recounted_matches"] = int(len(wide))
    info["recounts_complete"] = int(wide["complete"].sum())
    info["incomplete_reasons"] = {
        "point_gaps": int((wide["x_point_gaps"] > 0).sum()), "game_gaps": int((wide["x_game_gaps"] > 0).sum()),
        "games_not_ending_at_last_point": int((wide["x_games_not_ending_at_last_point"] > 0).sum()),
        "set_games_differ_from_stage0": int(wide["x_sets_equal"].eq(False).sum()),
        "points_without_server": int((wide["x_points_without_server"] > 0).sum())}
    diag = [c for c in P.PER_MATCH if c in wide and c not in ("x_sets_recount", "x_sets_stage0", "x_sets_equal")]
    info["server_rule_diagnostics_sum"] = {c: float(pd.to_numeric(wide[c], errors="coerce").fillna(0).sum())
                                           for c in diag}
    info["winner_vs_stage0"] = A.winner_check(rows)
    return A.to_contract(rows, "atp_sirgenkii_recount", "recount"), info


def main() -> int:
    xw, linker = A.crosswalk(), A.EventLinker()
    res = results()
    for fn in (ks_sirgenkii, recount_sirgenkii):
        rows, info = fn(xw, linker, res)
        info["results_rows"] = int(len(res))
        A.write_reader(info["reader"], rows, info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
