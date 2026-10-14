"""Follow-ups of 9 Oct 2026 to the Roland-Garros first-serve recount, at the owner's word ("Do all of these that you
think is a good idea, review it first, then execute if you do"):

  A. RG's whole box score for Roland Garros 2022-2026, under the rule of the Slam decision of 6 Oct 2026
     (docs/decisions/2026-10-06-slam-box-scores.md, point 4): "at a Slam whose official feed is held and has matched
     Sackmann's history, the feed is the box-score source". RG's statistics equal Sackmann's rows on all eight counts
     they share in 2019-2021, but for four boxes Sackmann exchanged (docs/studies/rg_first_serve_recount/ § 2.3).
  B. Those four RG 2021 boxes exchanged between winner and loser: exchange_box, the fix F2 of 8 Oct.

The official box of a player comes from RG's own records, one source per match:
    ace, df, svpt, first_in, first_won, second_won, bp_faced, bp_saved
             RG's statistics (rolandgarros.com's match API; break points from the opponent's "break points won")
    sv_gms   the completed games RG's MatchBeats has the player serving, tiebreaks not counted (Sackmann's convention
             in 2022-2025: equal in about 98% of RG rows and in every retirement), where MatchBeats holds every point
             of both players; else derived from the row's score and the player MatchBeats has serving first; else the
             row's own count; each only where it fits the score (Stage 0's B5), else blank (RG's statistics give no
             service games, so this is the one count that may stay the row's)

A match is proposed, as one override row, where all of these hold (else its class says why not):
    linked     RG's statistics are placed on the Stage 0 match by both names, and each player is the raw row's winner or
               loser by name
    record     both players' statistics pass their own consistency checks (propose.official) and give all eight
               counts
    changes    one of the eight counts differs from the raw row, the raw row has no box score, or the row's service
               games differ from RG's count where that count fits the score and agrees with the score's alternation
               of serve (the round-2 reviewers' addendum: missing, zero, or disproved by the score)
    complete   RG's statistics hold at least as many serve points as RG's MatchBeats, for both players (else the
               statistics miss points: R1's eight sides of 2024)
    second     where MatchBeats (or RG's key statistics, 2025-2026) holds every point of a player, it gives the same
               split, aces and double faults
    referee    no independent record holding every point (Court Vision 2019, 2020 and 2022; a hand chart) reads the
               row's value instead of the official one on a count that changes
    checks     the official box passes Stage 0's checks under the row's score (B0-B4, B6-B9; B5 for service games)
Walkovers and matches without a record keep their rows.

Writes, in data/studies/rg_first_serve_recount/followup/:
    whole_box_rows.csv        one row per Stage 0 player row of RG 2022-2026: the row, the official box, the class
    proposed_overrides.csv    one override row per proposed match, in stage0_build's --box-overrides format, with
                              the row's source (sackmann or tml)
    exchange_rows.csv         RG 2019-2021 player rows whose official box is the other player's raw box
    proposed_exchanges.csv    their exchange_box rows, in row_corrections.csv's format (fix RGX)
    proposal_summary.json     counts by edition and class, the counts that change, pooled rates before and after,
                              what the independent records say, the interplay with the confirmed split fix, and a
                              dry run of the whole candidate (the decided tables, these rows, the confirmed split rows
                              of matches without an override) on the raw rows with the build's own code
Reads no model result. Usage: ./python.sh src/eda/rg_first_serve_recount/whole_box.py
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

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.eda.rg_first_serve_recount import propose as PR  # noqa: E402
from src.eda.rg_first_serve_recount import recount as RC  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402

OUT = S.STUDY / "followup"
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]
NINE = list(C.BOX_SOURCE_NAMES)                  # Stage 0's contract names, in the override table's order
SECOND = ["first_in", "first_won", "second_won", "ace", "df"]
OV_COLUMNS = (["box_source", "feed_key", "stage0_match_id", "source", "tour", "tid", "round", "winner_key",
               "loser_key", "winner_name", "loser_name"] + B.OVERRIDE_COUNTS
              + ["score", "minutes", "tml_score", "feed_sha256", "feed_retrieved_at"])
ORDER = ["walkover", "no_link", "record_fails_checks", "names", "equal", "statistics_short", "mb_contradicts",
         "referee_contradicts", "fails_stage0_checks", "proposed"]
REFEREE = ["svpt", "ace", "df", "first_in", "first_won", "second_won"]
CV_YEARS = (2019, 2020, 2022)      # the Court Vision copy is a referee in these editions only (report § 2.5)


def linked() -> pd.DataFrame:
    """Every Stage 0 player row of Roland Garros 2019-2026 with every RG record beside the raw row (recount.build,
    in memory: step 1's files are not rewritten), RG's statistics as off_* (propose.official), MatchBeats' service
    games in Sackmann's convention, and RG's document receipt."""
    rows, _ = RC.build()
    rows = rows[rows["event"].eq("RG")].copy()
    mb = S.mb("RG")[["year", "match_id", "slot", "sv_gms_regular", "tb_games", "unfinished_games", "served_first"]]
    mb = mb.rename(columns={"match_id": "rg_code", "slot": "mb_slot", "sv_gms_regular": "mb_sv_gms_regular",
                            "tb_games": "mb_tb_games", "unfinished_games": "mb_unfinished_games",
                            "served_first": "mb_served_first"})
    rows = rows.merge(mb, on=["year", "rg_code", "mb_slot"], how="left")
    meta = pd.read_parquet(S.DUMP / "rolandgarros" / "matches.parquet",
                           columns=["year", "match_id", "source_sha256", "retrieved_at"])
    meta["year"] = meta["year"].astype(int)
    rows = rows.merge(meta.rename(columns={"match_id": "rg_code", "source_sha256": "rg_sha256",
                                           "retrieved_at": "rg_retrieved_at"}), on=["year", "rg_code"], how="left")
    return PR.official(rows)


def games_of(score: str) -> tuple[int, int]:
    """Games in the score and standard tiebreaks (Stage 0's score_counts; no short sets at a Slam)."""
    c = B.score_counts(str(score or ""), False)
    return c[2] + c[3], c[6]


def stage0_checks(rows: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Stage 0's box checks (stage0_build.box_scores) on the counts <prefix>_<name> of each match's two player rows,
    under the row's score: one boolean column per check, True where the match fails it."""
    f = {c: pd.to_numeric(rows[f"{prefix}_{c}"], errors="coerce") for c in NINE}
    g = rows["score"].map(games_of)
    games, tb = g.str[0], g.str[1]
    scored = rows["status"].isin(["completed", "retired"])
    by = rows["match_id"]
    sv_total = f["sv_gms"].groupby(by).transform("sum", min_count=2)
    b5 = scored & sv_total.notna() & ~((sv_total - (games - tb)).abs().le(1) | (sv_total - games).abs().le(1))
    sv = f["sv_gms"].where(~b5)
    side = pd.DataFrame({
        "B0": pd.concat([f[c] < 0 for c in NINE], axis=1).any(axis=1),
        "B1": f["first_in"] > f["svpt"], "B2": f["first_won"] > f["first_in"],
        "B3": f["second_won"] > f["svpt"] - f["first_in"], "B4": f["bp_saved"] > f["bp_faced"],
        "B6": f["df"] > f["svpt"] - f["first_in"], "B7": f["ace"] > f["first_won"] + f["second_won"],
        "B8": (f["bp_faced"] - f["bp_saved"]) > sv})
    out = side.groupby(by).transform("any")
    pts = f["svpt"].groupby(by).transform("sum", min_count=2)
    played = (games - tb) - np.where(rows["status"].eq("completed"), 0, 1)
    out["B9"] = scored & (pts < B.MIN_POINTS_PER_GAME * played)
    out["B5"] = b5
    return out.fillna(False).astype(bool)


def score_sv_gms(score: str, first_is_winner: bool) -> tuple[float, float]:
    """Service games of the row's winner and loser from the score and who served first. Servers alternate game by
    game through the match, a tiebreak taking its turn as one game; tiebreak games are not counted (Sackmann's
    convention), and a score holds only finished games, so the unfinished game of a retirement is not counted
    either."""
    sets, _ = B.tokens_of(str(score or ""))
    if not sets:
        return np.nan, np.nan
    won = {True: 0, False: 0}
    turn = 0
    for a, b, tb, bracket in sets:
        if bracket:                     # a match tiebreak in place of a set: one turn, no service game
            turn += 1
            continue
        tiebreak = B.is_tiebreak(a, b, tb, bracket, False)
        for g in range(a + b):
            if not (tiebreak and g == a + b - 1):
                won[(turn % 2 == 0) == first_is_winner] += 1
            turn += 1
    return float(won[True]), float(won[False])


def official_sv_gms(rows: pd.DataFrame, stats_svpt: str = "api_svpt") -> pd.DataFrame:
    """off_sv_gms and where it came from, the first of these that fits the score (Stage 0's B5, a match's check, so
    both players take the same source):
        matchbeats   MatchBeats' completed non-tiebreak games, where it holds every point of both players (its serve
                     points equal the statistics', column stats_svpt)
        derived      from the row's score and the player MatchBeats has serving the match's first point
        row          the row's own count
        none         blank"""
    complete = rows["mb_svpt"].eq(rows[stats_svpt]) & rows["mb_sv_gms_regular"].notna()
    both = complete.groupby(rows["match_id"]).transform("all")
    first = rows["mb_served_first"].eq(True)
    first_is_w = (first & rows["raw_side"].eq("w")).groupby(rows["match_id"]).transform("any")
    known = first.groupby(rows["match_id"]).transform("sum").eq(1)
    derived = pd.Series(np.nan, index=rows.index)
    for i in rows.index[known & rows["raw_side"].isin(["w", "l"])]:
        w, l = score_sv_gms(rows.at[i, "score"], bool(first_is_w.at[i]))
        derived.at[i] = w if rows.at[i, "raw_side"] == "w" else l
    rows["der_sv_gms"] = derived
    candidates = (("matchbeats", rows["mb_sv_gms_regular"].where(both)), ("derived", derived),
                  ("row", rows["raw_sv_gms"]))
    rows["off_sv_gms"], rows["sv_gms_from"] = np.nan, "none"
    for label, values in candidates:
        todo = rows["sv_gms_from"].eq("none")
        trial = rows.copy()
        trial.loc[todo, "off_sv_gms"] = values[todo]
        has = values.notna().groupby(rows["match_id"]).transform("all")
        fits = has & ~stage0_checks(trial, "off")["B5"]
        take = todo & fits
        rows.loc[take, "off_sv_gms"], rows.loc[take, "sv_gms_from"] = values[take], label
    return rows


def classify(rows: pd.DataFrame) -> pd.DataFrame:
    """The class of each match (on both its player rows): the first of ORDER that applies."""
    by = rows["match_id"]

    def both(s: pd.Series) -> pd.Series:
        return s.groupby(by).transform("all")

    def either(s: pd.Series) -> pd.Series:
        return s.groupby(by).transform("any")
    walkover = rows["status"].eq("walkover") | either(rows["off_svpt"].eq(0))
    no_link = ~both(rows["rg_code"].notna() & rows["api_svpt"].notna())
    record = ~rows["off_ok"] | either(rows[[f"off_{c}" for c in EIGHT]].isna().any(axis=1))
    sides = rows.groupby("match_id")["raw_side"].transform(lambda s: "".join(sorted(s.astype(str))))
    names = ~sides.eq("lw")                      # each player is the raw row's winner or its loser, by name
    no_box = rows["raw_svpt"].isna()
    differs = ~np.all([rows[f"raw_{c}"].eq(rows[f"off_{c}"]) for c in EIGHT], axis=0)
    # the row's service games differ from RG's count (MatchBeats', or the score's alternation of serve), where that
    # count fits the score and, where both exist, the two agree: the row's count is missing, zero, or one the score
    # disproves (even within B5's tolerance: 13 and 11 in a 24-game match without tiebreaks). The match is then not
    # equal, though its eight counts may be
    agreed = rows["der_sv_gms"].isna() | rows["der_sv_gms"].eq(rows["off_sv_gms"])
    sv_fix = rows["sv_gms_from"].isin(["matchbeats", "derived"]) & ~rows["raw_sv_gms"].eq(rows["off_sv_gms"]) \
        & agreed.groupby(rows["match_id"]).transform("all")
    rows["sv_gms_fix"] = sv_fix
    equal = ~either(pd.Series(differs, index=rows.index) | no_box | sv_fix)
    short = either(rows["mb_svpt"].gt(rows["api_svpt"]))
    contra = pd.Series(False, index=rows.index)
    for src in ("mb", "ks"):                     # RG's point record, and its key statistics (2025-2026)
        complete = rows[f"{src}_svpt"].eq(rows["api_svpt"])
        contra |= either(complete & ~np.all([rows[f"{src}_{c}"].eq(rows[f"off_{c}"]) for c in SECOND], axis=0))
    # an independent record holding every point (its serve points equal one side's) that reads the row's value and
    # not the official one on a count that would change: the step-2 reviewers dropped every such side
    referee = pd.Series(False, index=rows.index)
    for ref, ok in (("cv", rows["year"].isin(CV_YEARS)), ("mcp", pd.Series(True, index=rows.index))):
        full = ok & (rows[f"{ref}_svpt"].eq(rows["off_svpt"]) | rows[f"{ref}_svpt"].eq(rows["raw_svpt"]))
        for c in REFEREE:
            moves = ~rows[f"raw_{c}"].eq(rows[f"off_{c}"])
            referee |= full & moves & rows[f"{ref}_{c}"].eq(rows[f"raw_{c}"])
    rows["referee_against"] = referee
    referee = either(referee)
    fails = stage0_checks(rows, "off")
    rows["checks_failed"] = fails.drop(columns="B5").apply(lambda r: ";".join(r.index[r]), axis=1)
    failed = rows["checks_failed"].ne("")
    rows["cls"] = np.select([walkover, no_link, record, names, equal, short, contra, referee, failed],
                            ORDER[:-1], ORDER[-1])
    rows["no_box"] = no_box
    rows["changes"] = ""
    for c in EIGHT + ["sv_gms"]:
        same = rows[f"raw_{c}"].eq(rows[f"off_{c}"]) | (rows[f"raw_{c}"].isna() & rows[f"off_{c}"].isna())
        d = ~same & ~no_box
        rows.loc[d, "changes"] += c + " "
    rows.loc[no_box, "changes"] = "no box "
    rows["changes"] = rows["changes"].str.strip()
    return rows


def override_rows(rows: pd.DataFrame) -> pd.DataFrame:
    """One override row per proposed match, keyed as stage0_build.apply_box_overrides looks it up."""
    raw = S.raw_rows().set_index(["source_file", "source_row"])
    out = []
    for mid, g in rows[rows["cls"].eq("proposed")].groupby("match_id"):
        r = raw.loc[(g["source_file"].iloc[0], int(g["source_row"].iloc[0]))]
        x = {s: g[g["raw_side"].eq(s)].iloc[0] for s in ("w", "l")}
        rec = {"box_source": "rolandgarros", "feed_key": f"rolandgarros:{int(g['year'].iloc[0])}/{g['rg_code'].iloc[0]}",
               "stage0_match_id": mid, "source": r["source"], "tour": r["tour"], "tid": r["tid"], "round": r["round"],
               "winner_key": r["wkey"], "loser_key": r["lkey"], "winner_name": r["winner_name"],
               "loser_name": r["loser_name"]}
        for s in ("w", "l"):
            for name, col in C.BOX_SOURCE_NAMES.items():
                v = x[s][f"off_{name}"]
                rec[f"{s}_{col}"] = "" if pd.isna(v) else str(int(v))
        rec.update({"score": "", "minutes": "", "tml_score": r["score"], "feed_sha256": g["rg_sha256"].iloc[0],
                    "feed_retrieved_at": g["rg_retrieved_at"].iloc[0]})
        out.append(rec)
    return pd.DataFrame(out, columns=OV_COLUMNS)


def exchanges(rows: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """RG 2019-2021 matches whose two official boxes are the raw row's two boxes exchanged (all eight counts), and
    not the boxes as recorded: the evidence rows and their exchange_box rows."""
    c = rows[rows["year"].between(2019, 2021) & rows["off_ok"] & rows["raw_svpt"].notna()
             & rows["raw_side"].isin(["w", "l"])].copy()
    c = c[c.groupby("match_id")["match_id"].transform("size").eq(2)]
    other = c.groupby("match_id")
    own = np.all([c[f"raw_{x}"].eq(c[f"off_{x}"]) for x in EIGHT], axis=0)
    swapped = np.ones(len(c), dtype=bool)
    for x in EIGHT:
        opp = other[f"raw_{x}"].transform("sum") - c[f"raw_{x}"]
        swapped &= c[f"off_{x}"].eq(opp).to_numpy()
    c["own_equal"], c["exchanged_equal"] = own, swapped
    hit = c.groupby("match_id")["exchanged_equal"].transform("all") & ~c.groupby("match_id")["own_equal"].transform("all")
    ev = c[hit]
    raw = S.raw_rows().set_index(["source_file", "source_row"])
    out = []
    for mid, g in ev.groupby("match_id"):
        r = raw.loc[(g["source_file"].iloc[0], int(g["source_row"].iloc[0]))]
        out.append({"fix": "RGX", "action": "exchange_box", "match_id": mid, "source_file": g["source_file"].iloc[0],
                    "source_row": int(g["source_row"].iloc[0]), **{k: r[k] for k in K.ROW_GUARDS}})
    keep = ["year", "tour", "draw", "round", "match_id", "player_name", "won", "raw_side", "rg_code", "source_file",
            "source_row"] + [f"{p}_{x}" for x in EIGHT + ["sv_gms"] for p in ("raw", "off")]
    return ev[[k for k in keep if k in ev]], pd.DataFrame(out).reindex(columns=PR.ROW_COLUMNS)


def candidate_tables(overrides: pd.DataFrame, exchanges_: pd.DataFrame, split: pd.DataFrame,
                     swaps: pd.DataFrame | None = None,
                     sets: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The candidate's two tables: the decided override table with the RG rows appended (the RG rows carry a source
    column; the decided rows read as TML), and the decided row corrections with the split rows of matches that take no
    override, the exchanges, and the service-game swaps and sets (service_games.py) appended."""
    decided_ov = pd.read_csv(B.DECIDED_OVERRIDES, dtype=str, keep_default_na=False)
    ov = pd.concat([decided_ov.assign(source="tml"), overrides.astype(str).replace({"nan": ""})], ignore_index=True)
    ov = ov.reindex(columns=list(decided_ov.columns) + [c for c in OV_COLUMNS if c not in decided_ov.columns])
    decided = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    keep = split[~split["match_id"].isin(set(overrides["stage0_match_id"]))]
    extra = [t for t in (swaps, sets) if t is not None and len(t)]
    add = pd.concat([keep, exchanges_] + extra, ignore_index=True)
    add = add.astype(object).where(add.notna(), "").astype(str).replace(r"\.0$", "", regex=True)
    rc = pd.concat([decided, add.reindex(columns=decided.columns, fill_value="")], ignore_index=True)
    return ov.fillna(""), rc


def dry_run(ov: pd.DataFrame, rc: pd.DataFrame) -> dict:
    """Apply both candidate tables to the raw rows with the build's own code (overrides, then corrections), and
    check: every override row's counts read the table's after both steps unless a correction names the row too (none
    should), every exchange reads the boxes exchanged, and no row outside the tables changes."""
    raw = B.normalise(B.load_raw())
    counts = B.OVERRIDE_COUNTS

    def numbers(f: pd.DataFrame) -> pd.DataFrame:
        return f[counts].apply(lambda s: pd.to_numeric(s.astype(str).str.strip().replace({"": np.nan, "nan": np.nan}),
                                                       errors="coerce"))
    before = numbers(raw)
    df = B.apply_box_overrides(raw.copy(), ov, "candidate overrides", {})
    df, done = K.apply_row_corrections(df, rc)
    after = numbers(df)
    changed = ~((before == after) | (before.isna() & after.isna())).all(axis=1)
    src = ov["source"].replace("", "tml")
    key = df["source"] + "|" + df["tour"] + "|" + df["tid"] + "|" + df["round"] + "|" + df["wkey"] + "|" + df["lkey"]
    want = src + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" + ov["loser_key"]
    pos = pd.Series(df.index, index=key.to_numpy())
    ov_rows = pd.Index(pos.loc[want.to_numpy()].to_numpy())
    rc_rows = pd.Index(df.index[np.isin(K._row_key(df["_source_file"], df["_row"]).to_numpy(),
                                        K._row_key(rc["source_file"], rc["source_row"]).to_numpy())])
    table_vals = ov[counts].apply(lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce")).to_numpy()
    got = after.loc[ov_rows].to_numpy()
    reads = ((got == table_vals) | (np.isnan(got) & np.isnan(table_vals))).all(axis=1)
    rg = ov["box_source"].eq("rolandgarros").to_numpy()
    named = ov_rows.union(rc_rows)
    exch = done.get("exchange_box", pd.Index([]))
    ex_ok = True
    for r in exch:
        b, a = before.loc[r], after.loc[r]
        w, l = [f"w_{c}" for c in C.BOX_SOURCE_NAMES.values()], [f"l_{c}" for c in C.BOX_SOURCE_NAMES.values()]
        ex_ok &= bool(np.allclose(a[w].to_numpy(float), b[l].to_numpy(float), equal_nan=True)
                      and np.allclose(a[l].to_numpy(float), b[w].to_numpy(float), equal_nan=True))
    svx = done.get("exchange_svgms", pd.Index([]))
    others = [c for c in counts if c not in ("w_SvGms", "l_SvGms")]
    svs = done.get("set_svgms", pd.Index([]))
    sets_ok = None
    if len(svs):
        t = rc[rc["action"].eq("set_svgms")]
        want = pd.DataFrame({c: pd.to_numeric(t[c], errors="coerce").to_numpy() for c in ("w_SvGms", "l_SvGms")},
                            index=svs)
        sets_ok = bool((after.loc[svs, ["w_SvGms", "l_SvGms"]].to_numpy() == want.to_numpy()).all()
                       and ((after.loc[svs, others] == before.loc[svs, others])
                            | (after.loc[svs, others].isna() & before.loc[svs, others].isna())).all().all())
    sv_ok = bool(len(svx)) and bool(
        (after.loc[svx, "w_SvGms"].to_numpy() == before.loc[svx, "l_SvGms"].to_numpy()).all()
        and (after.loc[svx, "l_SvGms"].to_numpy() == before.loc[svx, "w_SvGms"].to_numpy()).all()
        and ((after.loc[svx, others] == before.loc[svx, others]) | (after.loc[svx, others].isna()
                                                                    & before.loc[svx, others].isna())).all().all())
    return {"override_rows": int(len(ov)), "override_rows_rg": int(rg.sum()),
            "override_rows_also_corrected": int(len(ov_rows.intersection(rc_rows))),
            "rg_override_rows_reading_the_table_after": int(reads[rg].sum()),
            "decided_override_rows_reading_the_table_after": int(reads[~rg].sum()),
            "correction_rows": int(len(rc)), "corrections_by_action": {a: int(len(i)) for a, i in done.items() if len(i)},
            "exchanges_read_exchanged_after": bool(ex_ok) if len(exch) else None,
            "service_game_swaps_read_exchanged_after_nothing_else_changed": sv_ok if len(svx) else None,
            "service_game_sets_read_the_table_after_nothing_else_changed": sets_ok,
            "rows_changed": int(changed.sum()), "rows_changed_outside_the_tables": int(changed[~changed.index.isin(named)].sum()),
            "rg_rows_without_a_box_before_given_one": int((before.loc[ov_rows[rg]].isna().all(axis=1)).sum())}


def referees(p: pd.DataFrame) -> dict:
    """On the counts the proposal changes: how often Court Vision (2022, a referee there) and the hand charts read the
    official value and how often the row's, where they hold every point (their serve points equal one side's)."""
    out = {}
    for c in ["svpt", "ace", "df", "first_in", "first_won", "second_won"]:
        d = p[~p["no_box"] & ~p[f"raw_{c}"].eq(p[f"off_{c}"])]
        votes = {}
        for ref, ok in (("cv", d["year"].eq(2022)), ("mcp", pd.Series(True, index=d.index))):
            full = d[f"{ref}_svpt"].eq(d["off_svpt"]) | d[f"{ref}_svpt"].eq(d["raw_svpt"])
            h = d[ok & d[f"{ref}_{c}"].notna() & full]
            votes[ref] = {"official": int(h[f"{ref}_{c}"].eq(h[f"off_{c}"]).sum()),
                          "row": int(h[f"{ref}_{c}"].eq(h[f"raw_{c}"]).sum()), "held": int(len(h))}
        out[c] = {"player_rows_changing": int(len(d)), **votes}
    return out


def pooled(g: pd.DataFrame, prefix: str) -> dict:
    h = g[g[f"{prefix}_svpt"].notna() & g[f"{prefix}_first_in"].notna()]
    sv = h[f"{prefix}_svpt"].sum()
    return {"rows": int(len(h)), "first_in_pct": round(100 * h[f"{prefix}_first_in"].sum() / sv, 2) if sv else None,
            "ace_pct": round(100 * h[f"{prefix}_ace"].sum() / sv, 2) if sv else None,
            "df_pct": round(100 * h[f"{prefix}_df"].sum() / sv, 2) if sv else None}


def editions(rows: pd.DataFrame) -> list[dict]:
    out = []
    for k, g in rows.groupby(["year", "tour", "draw"]):
        after = g.copy()
        prop = g["cls"].eq("proposed")
        for c in EIGHT + ["sv_gms"]:
            after.loc[prop, f"raw_{c}"] = g.loc[prop, f"off_{c}"]
        out.append({**dict(zip(["year", "tour", "draw"], k)), "player_rows": int(len(g)),
                    **{f"n_{c}": int(g["cls"].eq(c).sum()) for c in ORDER},
                    "before": pooled(g, "raw"), "after": pooled(after, "raw"),
                    "official": pooled(g[g["off_ok"]], "off")})
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = official_sv_gms(linked())
    ex_rows, ex_table = exchanges(rows)
    scope = classify(rows[rows["year"].between(2022, 2026)].copy())
    keep = (["year", "tour", "draw", "round", "match_id", "player_name", "won", "status", "score", "source",
             "source_file", "source_row", "raw_side", "rg_code", "api_court", "cls", "changes", "checks_failed",
             "referee_against", "sv_gms_from", "der_sv_gms", "sv_gms_fix", "off_ok"] + [f"{p}_{c}" for c in NINE for p in ("raw", "off")]
            + [f"{p}_{c}" for p in ("mb", "ks", "cv", "mcp") for c in ("svpt", "first_in", "first_won", "second_won",
                                                                      "ace", "df")]
            + ["mb_sv_gms_regular", "mb_tb_games", "mb_unfinished_games", "mb_served_first", "rg_sha256",
               "rg_retrieved_at"])
    scope[[k for k in keep if k in scope]].to_csv(OUT / "whole_box_rows.csv", index=False)
    ov = override_rows(scope)
    ov.to_csv(OUT / "proposed_overrides.csv", index=False)
    ex_rows.to_csv(OUT / "exchange_rows.csv", index=False)
    ex_table.to_csv(OUT / "proposed_exchanges.csv", index=False)

    # the interplay with the confirmed split fix of step 2
    confirmed = pd.read_csv(S.STUDY / "confirmed" / "confirmed_corrections.csv")
    rg_conf = confirmed[confirmed["fix"].str.startswith("RGFS")]
    over = set(ov["stage0_match_id"])
    p = scope[scope["cls"].eq("proposed")]
    matches = scope.drop_duplicates("match_id")
    summary = {
        "player_rows_2022_2026": int(len(scope)), "matches_2022_2026": int(len(matches)),
        "matches_by_class": matches["cls"].value_counts().reindex(ORDER).fillna(0).astype(int).to_dict(),
        "matches_by_class_and_year": matches.groupby(["year", "cls"]).size().rename("matches").reset_index()
        .to_dict("records"),
        "proposed_overrides": int(len(ov)), "proposed_by_source": ov["source"].value_counts().to_dict(),
        "proposed_by_year": ov["feed_key"].str.extract(r":(\d{4})/")[0].value_counts().sort_index().to_dict(),
        "player_rows_changing_by_count": {c: int(p["changes"].str.contains(rf"\b{c}\b").sum())
                                          for c in EIGHT + ["sv_gms"]},
        "player_rows_without_a_box_before": int(p["no_box"].sum()),
        "proposed_matches_for_service_games_only": int(p.groupby("match_id")["changes"]
                                                       .agg(lambda s: set(" ".join(s).split()) == {"sv_gms"}).sum()),
        "sv_gms_source_of_proposed_rows": p["sv_gms_from"].value_counts().to_dict(),
        "referees_on_changing_counts": referees(p),
        "confirmed_split_rows_rg": int(len(rg_conf)),
        "confirmed_split_rows_inside_proposed_overrides": int(rg_conf["match_id"].isin(over).sum()),
        "confirmed_split_rows_outside": rg_conf.loc[~rg_conf["match_id"].isin(over), "match_id"].tolist()[:50],
        "exchanges_2019_2021": ex_table[["match_id", "winner_name", "loser_name", "round"]].to_dict("records"),
        "dry_run": (S.raw_rows.cache_clear(), dry_run(*candidate_tables(ov, ex_table, confirmed)))[1],
        "editions": editions(scope),
    }
    (OUT / "proposal_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "editions"}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
