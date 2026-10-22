"""Readers of the ATP Stats Centre's own decrypted files (staged in data/dump/points/):

    atp_ks_backfill        the key statistics of the backfill, 2018 to Oct 2021 (infosys_atp/keystats.parquet,
                           set0 = the match; atp_keystats.py maps them)
    atp_backfill_recount   the nine counts recounted from the backfill's MatchBeats points (infosys_atp/points.parquet:
                           server, serve number, scorer, ending, break-point flag; 'P' and 'DF' are double faults)
    atp_ch_recount         the Challengers of 2021-2024 (infosys_challengers/): MatchBeats points where held (2,260
                           matches; the serve number is present; endings mark aces and double faults only, which the
                           recount does not need); the 115 matches held only as rally analysis are recounted from it
                           with the server derived (atp_recount.derive_servers), x_route says which

Only the plan's files (purpose 'plan' in infosys_atp; the Challengers' 'p6 challengers') are read; the backfill's two
calibration files (2022) are left out. Linked by the event linker (season, ATP event id, draw from the match code,
round hint, both players' ATP codes and names). Orientation: player 1 / player 2 are the file's own (p1_id / p2_id;
MatchBeats' server '1' / '2'); each is placed on its Stage 0 side by id or name.

Also writes box/atp_server_rule_validation.csv: the rally analysis's derived server against MatchBeats' own server
on the same points (the backfill and the Challengers hold both routes).

Run: ./python.sh src/eda/source_reconciliation/atp_backfill.py
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
from src.eda.source_reconciliation import atp_keystats as K  # noqa: E402
from src.eda.source_reconciliation import atp_points as P  # noqa: E402
from src.eda.source_reconciliation import atp_recount as R  # noqa: E402

KEY = ["year", "event_id", "match_id"]
MB_COLS = KEY + ["set", "game", "point", "pointId", "server", "serve", "scorer", "result", "isBrkPt", "game_fields"]
RALLY_COLS = KEY + ["list", "pointId", "pointEndType", "score", "t1BreakPoint", "t2BreakPoint", "tieBreak", "serve"]


def key_of(df: pd.DataFrame) -> pd.Series:
    return df["year"].astype(str) + "_" + df["event_id"].astype(str) + "_" + df["match_id"].astype(str).str.upper()


def matches(dump: Path, purpose: str) -> pd.DataFrame:
    """The planned match codes with the linker's fields, indexed by source_key (year_event_CODE)."""
    m = pd.read_parquet(dump / "matches.parquet")
    m = m[m["purpose"].eq(purpose)].copy()
    m["source_key"] = key_of(m)
    m = m.rename(columns={"match_id": "code"})          # the Infosys match code; match_id is Stage 0's from here on
    m = m.drop_duplicates("source_key").set_index("source_key", drop=False)
    hint = [P.round_hint(c) for c in m["code"]]
    m["season"] = pd.to_numeric(m["year"], errors="coerce").fillna(-1).astype(int)
    m["ev"] = pd.to_numeric(m["event_id"], errors="coerce").fillna(-1).astype(int)
    m["qual"] = [h[0] for h in hint]
    m["round"] = [h[1] for h in hint]
    m["c1"], m["c2"] = m["p1_id"].map(A.atp_code), m["p2_id"].map(A.atp_code)
    for no in ("1", "2"):
        full = (m[f"p{no}_first_name"].fillna("") + " " + m[f"p{no}_last_name"].fillna("")).str.strip()
        m[f"f{no}"] = np.where(full != "", full, m[f"p{no}_name"].fillna(""))
        m[f"s{no}"] = m[f"p{no}_name"].fillna("")
    return m


def link(m: pd.DataFrame, xw: pd.Series, linker: A.EventLinker) -> tuple[pd.DataFrame, dict]:
    lk = linker.link(m, xw)
    m = m.join(lk)
    info = {"records_read": int(len(m)), "linked": int(m["match_id"].notna().sum()),
            "link_methods": m["link_method"].value_counts().to_dict(),
            "unlinked": m.loc[m["match_id"].isna(), "unlinked_reason"].value_counts().to_dict()}
    return m, info


# ------------------------------------------------------------------------------------------------ key statistics
def ks_backfill(xw, linker) -> tuple[pd.DataFrame, dict]:
    m, info = link(matches(A.ATP_DUMP, "plan"), xw, linker)
    k = pd.read_parquet(A.ATP_DUMP / "keystats.parquet", columns=KEY + ["set_key", "name", "player1", "player2"])
    k = k[k["set_key"].eq("set0")].drop_duplicates(KEY + ["name"])
    k["source_key"] = key_of(k)
    stats = {key: {n: (a, b) for n, a, b in zip(g["name"], g["player1"], g["player2"])}
             for key, g in k.groupby("source_key")}
    info["records_with_set0_keystats"] = len(stats)
    lm = m[m["match_id"].notna() & m.index.isin(list(stats))].copy()
    info["dropped"] = {"no_set0_keystats": int((~m.index.isin(list(stats))).sum()),
                       "unlinked_with_keystats": int((m["match_id"].isna() & m.index.isin(list(stats))).sum())}
    wide = pd.DataFrame.from_dict({key: K.counts(stats[key]) for key in lm.index}, orient="index")
    lm = lm.join(wide)
    lm["complete"] = lm["is_match_complete"].map(P.truthy)
    lm["x_status"] = lm["match_status"].fillna("")
    lm["x_season"] = lm["season"]
    rows = A.long_rows(lm, A.FIELDS + ["x_first_won_den", "x_second_den", "x_sv_won_den", "x_spd1"],
                       extra=["complete", "link_method", "x_status", "x_season"])
    win = pd.concat([lm["match_winner"].astype(str).eq("1"), lm["match_winner"].astype(str).eq("2")],
                    ignore_index=True)
    known = pd.concat([lm["match_winner"].astype(str).isin(["1", "2"])] * 2, ignore_index=True)
    rows["x_won"] = pd.Series(np.where(known, win, None), dtype=object)
    rows["x_code"] = pd.concat([lm["c1"], lm["c2"]], ignore_index=True).to_numpy()
    info["winner_vs_stage0"] = A.winner_check(rows)
    info["internal_consistency"] = _ks_consistency(rows)
    return A.to_contract(rows, "atp_ks_backfill", "box"), info


def _ks_consistency(rows: pd.DataFrame) -> dict:
    s = rows[rows["svpt"].notna()]
    eq = lambda a, b: {"n": int((a.notna() & b.notna()).sum()),  # noqa: E731
                       "equal": round(float((a == b)[a.notna() & b.notna()].mean()), 5) if (a.notna() & b.notna()).any()
                       else None}
    return {"first_won_den_eq_first_in": eq(s["x_first_won_den"], s["first_in"]),
            "second_den_eq_svpt_minus_first_in": eq(s["x_second_den"], s["svpt"] - s["first_in"]),
            "sv_won_den_eq_svpt": eq(s["x_sv_won_den"], s["svpt"]),
            "sv_won_eq_first_plus_second": eq(s["sv_won"], s["first_won"] + s["second_won"])}


# ------------------------------------------------------------------------------------------------ recounts
def _recount(m: pd.DataFrame, groups: dict, derive: bool, route: str) -> pd.DataFrame:
    """Recount every match of groups that is linked; wide rows on m's index."""
    lm = m[m["match_id"].notna() & m.index.isin(list(groups))]
    ctx = P.stage0_context(lm["match_id"], lm["p1_side"])
    wide = P.recount_all({k: groups[k] for k in lm.index}, ctx, derive=derive)
    wide = lm[["source_key", "match_id", "p1_side", "link_method", "season", "c1", "c2"]].join(wide).join(ctx)
    wide["x_route"] = route
    return wide


def _finish(wide: pd.DataFrame, reader: str, info: dict) -> tuple[pd.DataFrame, dict]:
    wide = wide.rename(columns={"s0_status": "x_s0_status", "season": "x_season"})
    rows = P.to_long(wide, extra=["complete", "link_method", "x_route", "x_s0_status", "x_season"])
    rows["x_code"] = pd.concat([wide["c1"], wide["c2"]], ignore_index=True).to_numpy()
    info["recounted_matches"] = int(len(wide))
    info["recounts_complete"] = int(wide["complete"].sum())
    info["incomplete_reasons"] = {
        "point_gaps": int((wide["x_point_gaps"] > 0).sum()), "game_gaps": int((wide["x_game_gaps"] > 0).sum()),
        "games_not_ending_at_last_point": int((wide["x_games_not_ending_at_last_point"] > 0).sum()),
        "set_games_differ_from_stage0": int(wide["x_sets_equal"].eq(False).sum()),
        "points_without_server": int((wide["x_points_without_server"] > 0).sum())}
    info["winner_vs_stage0"] = A.winner_check(rows)
    return A.to_contract(rows, reader, "recount"), info


def recount_backfill(xw, linker) -> tuple[pd.DataFrame, dict]:
    m, info = link(matches(A.ATP_DUMP, "plan"), xw, linker)
    p = pd.read_parquet(A.ATP_DUMP / "points.parquet", columns=MB_COLS)
    p["source_key"] = key_of(p)
    groups = {k: P.mb_points(g) for k, g in p.groupby("source_key") if k in m.index}
    info["records_with_points"] = len(groups)
    info["dropped"] = {"no_points": int((~m.index.isin(list(groups))).sum()),
                       "unlinked_with_points": int((m["match_id"].isna() & m.index.isin(list(groups))).sum())}
    wide = _recount(m, groups, derive=False, route="match-beats")
    return _finish(wide, "atp_backfill_recount", info)


def recount_challengers(xw, linker) -> tuple[pd.DataFrame, dict]:
    m, info = link(matches(A.CH_DUMP, "p6 challengers"), xw, linker)
    p = pd.read_parquet(A.CH_DUMP / "points.parquet", columns=MB_COLS)
    p["source_key"] = key_of(p)
    mb = {k: P.mb_points(g) for k, g in p.groupby("source_key") if k in m.index}
    r = pd.read_parquet(A.CH_DUMP / "rally.parquet", columns=RALLY_COLS)
    r["source_key"] = key_of(r)
    ra = {k: P.rally_points(g) for k, g in r.groupby("source_key") if k in m.index and k not in mb}
    info["records_with_matchbeats"] = len(mb)
    info["records_with_rally_only"] = len(ra)
    info["dropped"] = {"no_points": int((~m.index.isin(list(mb) + list(ra))).sum()),
                       "unlinked_with_points": int((m["match_id"].isna() & m.index.isin(list(mb) + list(ra))).sum())}
    wide = pd.concat([_recount(m, mb, derive=False, route="match-beats"),
                      _recount(m, ra, derive=True, route="rally-analysis")])
    return _finish(wide, "atp_ch_recount", info)


# ------------------------------------------------------------------------------------------------ server rule check
def validate_server_rule() -> pd.DataFrame:
    """The derived server (rally analysis) against MatchBeats' server, point by point, where both routes hold a match."""
    out = []
    for name, dump, purpose in (("backfill_2018_2021", A.ATP_DUMP, "plan"),
                                ("challengers_2021_2024", A.CH_DUMP, "p6 challengers")):
        keys = set(matches(dump, purpose).index)
        p = pd.read_parquet(dump / "points.parquet", columns=MB_COLS)
        p["source_key"] = key_of(p)
        p = p[p["source_key"].isin(keys)]
        r = pd.read_parquet(dump / "rally.parquet", columns=RALLY_COLS)
        r["source_key"] = key_of(r)
        r = r[r["source_key"].isin(set(p["source_key"]))]
        truth = {(k, P.as_int(s), P.as_int(g), P.as_int(q)): P.as_int(v)
                 for k, s, g, q, v in zip(p["source_key"], p["set"], p["game"], p["point"], p["server"])}
        n = same = matches_n = matches_all_same = 0
        diag_tot = {}
        no_server = 0
        for k, g in r.groupby("source_key"):
            pts = P.rally_points(g)
            servers, diag = R.derive_servers([dict(q) for q in pts if q["winner"] in (1, 2)])
            for d, v in diag.items():
                diag_tot[d] = diag_tot.get(d, 0) + v
            m_n = m_same = 0
            for q in pts:
                t = truth.get((k, q["set"], q["game"], q["point"]))
                if t is None:
                    continue
                d = servers.get((q["set"], q["game"], q["point"]))
                if d is None:
                    no_server += 1
                    continue
                m_n += 1
                m_same += d == t
            n += m_n
            same += m_same
            matches_n += 1
            matches_all_same += (m_n > 0 and m_n == m_same)
        out.append({"route_pair": name, "matches": matches_n, "points_compared": n, "server_equal": same,
                    "share_equal": round(same / n, 6) if n else None, "points_without_derived_server": no_server,
                    "matches_every_point_equal": matches_all_same, **diag_tot})
    return pd.DataFrame(out)


def main() -> int:
    xw, linker = A.crosswalk(), A.EventLinker()
    for fn, name in ((ks_backfill, "atp_ks_backfill"), (recount_backfill, "atp_backfill_recount"),
                     (recount_challengers, "atp_ch_recount")):
        rows, info = fn(xw, linker)
        info["reader"] = name
        A.write_reader(name, rows, info)
    v = validate_server_rule()
    v.to_csv(A.BOX / "atp_server_rule_validation.csv", index=False)
    print(v.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
