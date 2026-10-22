"""The cross-source comparison of box scores: every reader against every other, against the recounts, and against
the accounting identities of the match's own score.

Inputs: every reader in data/studies/source_reconciliation/box/readers/<reader>.parquet (the contract in
docs/studies/source_reconciliation/subagent_briefs.md), and the frozen Stage 0 for each match's tour, level, season,
status and score.

Outputs (data/studies/source_reconciliation/box/):
    engine_coverage.csv     per reader: player rows, matches, by tour x level group x season
    engine_pairs.csv        per (reader A, reader B) and count: rows where both hold it, exact share, within one, mean
                            difference (B - A), by tour x level group x season band
    engine_identities.csv   per reader: the share of complete matches whose two boxes pass each accounting identity
                            with Stage 0's score (I1 games, I2 the serving order, I3 definition checks)
    engine_identity_pairs.csv  each reader and Stage 0 on the same player rows: the share passing I1 and I2
    engine_accuracy.csv     every reader against every recount reader's complete rows (the referee), count by count
    engine_long.parquet     the long table of every reader's counts with Stage 0's match meta (gitignored)

Run: ./python.sh src/eda/source_reconciliation/box_engine.py [--readers a,b,...]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

BOX = C.OUT / "box"
READERS = BOX / "readers"
T0 = time.time()

LEVEL_GROUP = {"GS": "slam", "GSQ": "qual", "TQ": "qual", "CHQ": "qual", "ITFQ": "qual", "FIN": "tour",
               "T1000": "tour", "T500": "tour", "T250": "tour", "TEAM": "team", "CH": "challenger", "ITF": "itf"}
BANDS = [(1968, 2012, "-2012"), (2013, 2018, "2013-18"), (2019, 2020, "2019-20"), (2021, 2024, "2021-24"),
         (2025, 2025, "2025"), (2026, 2026, "2026")]


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def band(year: pd.Series) -> pd.Series:
    out = pd.Series("other", index=year.index, dtype=object)
    for lo, hi, name in BANDS:
        out[year.between(lo, hi)] = name
    return out


def games_from_score(score: str) -> tuple[int, int, int, int, int, int, int]:
    """From Stage 0's score (written from the winner's side): games won by the row's winner and loser, tiebreak games
    won by each, sets counted, and the service games each would have served had the WINNER served first (sv_wf) ...
    which also gives the LOSER-first count by symmetry (the pair reversed).
    A tiebreak game counts as a game won (7-6) and takes one turn in the serving order, but is not a service game. A
    match tiebreak in lieu of a deciding set ([10-8]) counts as one game, as Sackmann's scores count it, and as one
    tiebreak. Service games: within a set the players alternate; a tiebreak is one turn; the next set's first server is
    the player whose turn comes next (the one who received first in the tiebreak)."""
    sets, _ = B.tokens_of(score)
    gw = gl = tw = tl = 0
    turn_w = True           # True: the winner is to serve the next turn (winner served first)
    sv_w = sv_l = 0
    for a, b, tb, bracket in sets:
        is_tb = bracket or tb >= 0 or (max(a, b), min(a, b)) in ((7, 6), (13, 12))
        if bracket:
            games, tbs = 0, 1
            if a > b:
                gw += 1
                tw += 1
            elif b > a:
                gl += 1
                tl += 1
        else:
            gw += a
            gl += b
            tbs = 1 if is_tb else 0
            games = a + b - tbs
            if is_tb:
                if a > b:
                    tw += 1
                elif b > a:
                    tl += 1
        # serve the set's non-tiebreak games in alternation, then the tiebreak turn
        first = (games + 1) // 2
        second = games // 2
        if turn_w:
            sv_w += first
            sv_l += second
        else:
            sv_l += first
            sv_w += second
        if (games + tbs) % 2 == 1:
            turn_w = not turn_w
    return gw, gl, tw, tl, len(sets), sv_w, sv_l


def meta() -> pd.DataFrame:
    m, p = C.stage0(["match_id", "tour", "year", "map_level", "qualifying", "status", "score", "tournament_date",
                     "source", "sv_gms_incl_tb", "best_of"], ["match_id", "player_id", "won"])
    m["level_group"] = m["map_level"].map(LEVEL_GROUP).fillna("other")
    m["band"] = band(m["year"].astype(int))
    g = [games_from_score(s) for s in m["score"].fillna("").astype(str)]
    arr = np.array(g, dtype="int64")
    m["g_w"], m["g_l"], m["tb_w"], m["tb_l"], m["n_sets"], m["sv_wf_w"], m["sv_wf_l"] = arr.T
    return m, p


def load_readers(names: list[str] | None) -> pd.DataFrame:
    import pyarrow.parquet as pq

    parts = []
    for path in sorted(READERS.glob("*.parquet")):
        name = path.stem
        if names and name not in names:
            continue
        have = set(pq.read_schema(path).names)
        if not {"reader", "family", "kind", "match_id", "player_id", "complete"} <= have:
            log(f"  {name}: not a reader table (no contract columns); skipped")
            continue
        f = pd.read_parquet(path)
        keep = ["reader", "family", "kind", "source_key", "match_id", "player_id", "complete"] + C.FIELDS
        f = f[[c for c in keep if c in f.columns]].copy()
        for c in C.FIELDS:
            if c not in f:
                f[c] = np.nan
        f["match_id"] = f["match_id"].astype(str)
        f["player_id"] = f["player_id"].astype(str)
        f["complete"] = f["complete"].astype(bool)
        dups = f.duplicated(["match_id", "player_id"]).sum()
        if dups:
            log(f"  {name}: {dups:,} duplicate (match, player) rows; keeping the first")
            f = f.drop_duplicates(["match_id", "player_id"])
        parts.append(f)
        log(f"  {name}: {len(f):,} rows, {f['match_id'].nunique():,} matches")
    return pd.concat(parts, ignore_index=True)


def with_opponent(long: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    """Each reader row with the same reader's row of the opponent (columns o_<field>) and Stage 0's won flag."""
    opp = p[["match_id", "player_id", "won"]].copy()
    opp_id = p.merge(p, on="match_id", suffixes=("", "_o"))
    opp_id = opp_id[opp_id["player_id"] != opp_id["player_id_o"]][["match_id", "player_id", "player_id_o"]]
    long = long.merge(opp, on=["match_id", "player_id"], how="left")
    long = long.merge(opp_id, on=["match_id", "player_id"], how="left")
    o = long[["reader", "match_id", "player_id"] + C.FIELDS].rename(
        columns={"player_id": "player_id_o", **{c: f"o_{c}" for c in C.FIELDS}})
    return long.merge(o, on=["reader", "match_id", "player_id_o"], how="left")


def identities(long: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Per reader row: the accounting identities of the two boxes with Stage 0's score.
    I1  games: a player's games (from the score) = own holds + breaks of the opponent + tiebreak games won, where
        holds = sv_gms - (bp_faced - bp_saved). Completed matches with a standard score only.
    I2  service games follow the serving order the score implies: (sv_gms, opponent's sv_gms) equals the pair the
        score gives for one of the two possible first servers (tiebreaks take a turn but are not service games).
        Completed matches only.
    I3  the definition checks: first_in <= svpt; first_won <= first_in; second_won + df <= svpt - first_in;
        bp_saved <= bp_faced; ace <= first_won + second_won.
    Each is True, False, or NaN where a count it needs is missing."""
    f = long.merge(m[["match_id", "status", "g_w", "g_l", "tb_w", "tb_l", "sv_wf_w", "sv_wf_l", "sv_gms_incl_tb"]],
                   on="match_id", how="left")
    won = f["won"].astype("boolean").fillna(False).to_numpy()
    games = np.where(won, f["g_w"], f["g_l"])
    tbs = np.where(won, f["tb_w"], f["tb_l"])
    holds = f["sv_gms"] - (f["bp_faced"] - f["bp_saved"])
    brk = f["o_bp_faced"] - f["o_bp_saved"]
    i1 = (holds + brk + tbs) == games
    done = f["status"].eq("completed")
    need1 = f[["sv_gms", "bp_faced", "bp_saved", "o_bp_faced", "o_bp_saved"]].notna().all(axis=1) & done
    f["I1"] = i1.where(need1)
    # the player's own count and the opponent's under each first server (sv_wf_* assume the winner served first)
    own_wf = np.where(won, f["sv_wf_w"], f["sv_wf_l"])
    opp_wf = np.where(won, f["sv_wf_l"], f["sv_wf_w"])
    i2 = ((f["sv_gms"] == own_wf) & (f["o_sv_gms"] == opp_wf)) | ((f["sv_gms"] == opp_wf) & (f["o_sv_gms"] == own_wf))
    need2 = f[["sv_gms", "o_sv_gms"]].notna().all(axis=1) & done
    f["I2"] = i2.where(need2)
    second = f["svpt"] - f["first_in"]
    checks = [(f["first_in"] <= f["svpt"]), (f["first_won"] <= f["first_in"]), (f["second_won"] + f["df"] <= second),
              (f["bp_saved"] <= f["bp_faced"]), (f["ace"] <= f["first_won"] + f["second_won"])]
    need3 = f[["svpt", "first_in", "first_won", "second_won", "df", "bp_saved", "bp_faced", "ace"]].notna().all(axis=1)
    i3 = checks[0]
    for c in checks[1:]:
        i3 = i3 & c
    f["I3"] = i3.where(need3)
    return f


def pair_table(long: pd.DataFrame, m: pd.DataFrame, base: list[str]) -> pd.DataFrame:
    """Every base reader against every other reader, count by count."""
    mm = m[["match_id", "tour", "level_group", "band"]]
    rows = []
    for a in base:
        A = long[long["reader"] == a][["match_id", "player_id"] + C.FIELDS]
        for b in sorted(long["reader"].unique()):
            if b == a:
                continue
            Bf = long[long["reader"] == b][["match_id", "player_id"] + C.FIELDS]
            j = A.merge(Bf, on=["match_id", "player_id"], suffixes=("", "_b")).merge(mm, on="match_id", how="left")
            if j.empty:
                continue
            left = j[["tour", "level_group", "band"] + C.FIELDS]
            right = j[[f"{c}_b" for c in C.FIELDS]].set_axis(C.FIELDS, axis=1)
            t = C.agreement(left, right, ["tour", "level_group", "band"])
            t.insert(0, "reader_b", b)
            t.insert(0, "reader_a", a)
            rows.append(t)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def accuracy_table(long: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Every reader against every recount reader, on the recount's complete rows only (the referee), count by count.
    reader_a is the reader judged, reader_b the referee; mean_diff is referee minus reader."""
    mm = m[["match_id", "tour", "level_group", "band"]]
    refs = sorted(long.loc[long["kind"].eq("recount"), "reader"].unique())
    rows = []
    for r in refs:
        R = long[(long["reader"] == r) & long["complete"]][["match_id", "player_id"] + C.FIELDS]
        for a in sorted(long["reader"].unique()):
            if a == r:
                continue
            A = long[long["reader"] == a][["match_id", "player_id"] + C.FIELDS]
            j = A.merge(R, on=["match_id", "player_id"], suffixes=("", "_r")).merge(mm, on="match_id", how="left")
            if j.empty:
                continue
            t = C.agreement(j[["tour", "level_group", "band"] + C.FIELDS],
                            j[[f"{c}_r" for c in C.FIELDS]].set_axis(C.FIELDS, axis=1), ["tour", "level_group", "band"])
            t.insert(0, "referee", r)
            t.insert(0, "reader", a)
            rows.append(t)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def identity_pairs(ids: pd.DataFrame, m: pd.DataFrame, base: str = "lead_stage0") -> pd.DataFrame:
    """The identities of each reader and of the base reader on the SAME player rows (both evaluable), so that a
    reader that blanks failing rows (Stage 0) is not flattered by its own blanks."""
    mm = m[["match_id", "tour", "level_group", "band"]]
    B0 = ids[ids["reader"] == base][["match_id", "player_id", "I1", "I2"]]
    rows = []
    for a in sorted(ids["reader"].unique()):
        if a == base:
            continue
        A = ids[ids["reader"] == a][["match_id", "player_id", "I1", "I2"]]
        j = A.merge(B0, on=["match_id", "player_id"], suffixes=("", "_base")).merge(mm, on="match_id", how="left")
        for k in ("I1", "I2"):
            both = j[k].notna() & j[f"{k}_base"].notna()
            if not both.any():
                continue
            g = j[both].groupby(["tour", "level_group", "band"]).agg(
                n=(k, "size"), reader_pass=(k, lambda s: float(s.astype(float).sum())),
                base_pass=(f"{k}_base", lambda s: float(s.astype(float).sum()))).reset_index()
            g.insert(0, "identity", k)
            g.insert(0, "reader", a)
            rows.append(g)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    if not out.empty:
        out["reader_share"] = out["reader_pass"] / out["n"]
        out["base_share"] = out["base_pass"] / out["n"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--readers", default="")
    ap.add_argument("--base", default="lead_stage0,lead_sackmann_raw,lead_tml_raw")
    args = ap.parse_args()
    names = [x for x in args.readers.split(",") if x] or None
    m, p = meta()
    log(f"Stage 0: {len(m):,} matches")
    long = load_readers(names)
    long = long.merge(m[["match_id"]], on="match_id", how="inner")
    long = with_opponent(long, p)
    log(f"long: {len(long):,} rows, readers {sorted(long['reader'].unique())}")

    cov = long.merge(m[["match_id", "tour", "level_group", "band"]], on="match_id", how="left")
    cov = cov.groupby(["reader", "tour", "level_group", "band"]).agg(rows=("player_id", "size"),
                                                                     matches=("match_id", "nunique"),
                                                                     complete=("complete", "sum")).reset_index()
    cov.to_csv(BOX / "engine_coverage.csv", index=False)

    base = [b for b in args.base.split(",") if b in set(long["reader"])]
    pairs = pair_table(long, m, base)
    pairs.to_csv(BOX / "engine_pairs.csv", index=False)
    log(f"pairs: {len(pairs):,} rows")

    ids = identities(long, m)
    idt = ids.merge(m[["match_id", "tour", "level_group", "band"]], on="match_id", how="left")
    agg = idt.groupby(["reader", "tour", "level_group", "band"]).agg(
        I1_n=("I1", "count"), I1_pass=("I1", lambda s: float(s.astype(float).sum())),
        I2_n=("I2", "count"), I2_pass=("I2", lambda s: float(s.astype(float).sum())),
        I3_n=("I3", "count"), I3_pass=("I3", lambda s: float(s.astype(float).sum()))).reset_index()
    for k in ("I1", "I2", "I3"):
        agg[f"{k}_share"] = agg[f"{k}_pass"] / agg[f"{k}_n"].where(agg[f"{k}_n"] > 0)
    agg.to_csv(BOX / "engine_identities.csv", index=False)
    identity_pairs(ids, m).to_csv(BOX / "engine_identity_pairs.csv", index=False)
    acc = accuracy_table(long, m)
    acc.to_csv(BOX / "engine_accuracy.csv", index=False)
    log(f"accuracy: {len(acc):,} rows")
    ids[["reader", "family", "kind", "source_key", "match_id", "player_id", "player_id_o", "won", "complete"]
        + C.FIELDS + [f"o_{c}" for c in C.FIELDS] + ["I1", "I2", "I3"]].to_parquet(BOX / "engine_long.parquet",
                                                                                   index=False)
    log("written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
