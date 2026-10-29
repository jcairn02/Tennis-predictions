"""Stage 0 of the predictability diagnostic: the analysis table.

Builds two tables of singles matches at every level from 2010, and the evidence that goes with them:

    stage0_matches.parquet          one row per match: identity, level, round and order, status, score, format
    stage0_match_players.parquet    two rows per match: side A/B, won, rank, biography, box score, rates
    stage0_cleaning_log.csv         every cleaning rule with its counts by tour, level, qualifying and year
    stage0_level_applied.csv        how each source code became a level, with counts and example names
    stage0_cells.csv                matches, evaluation matches and box scores per tour, level, qualifying and year
    stage0_summary.json             sources, linking, identity, coverage, cleaning totals and known holes

Sources. Jeff Sackmann's files are the base. Tennis My Life (TML) rows are appended where no link to a
Sackmann match exists. Linking is identity-first and reuses src/eda/merge_feasibility/scan.py: exact
name pair, then the one-player anchor, with the corrections pick() describes; two passes of our own
follow (resolved player ids; the same event and players under another round label), and after the
merge the draw decides who won (the player who advanced) and repeats within an event are dropped.
TML's ATP files use ATP website codes as player ids:
the code -> Sackmann id mapping is learned from the linked matches. TML also supplies what Sackmann
lacks for an event: indoor or outdoor, the 250 / 500 split and the WTA's 500 / 1000 split.

Reads data/dump/matches (read-only) and the hand-made stage0_level_rules.csv, and records each input file's
SHA-256 (the staged file's own, and its source file's from the .meta.json) in the summary.

Box-score overrides (docs/decisions/2026-10-06-slam-box-scores.md): every build applies the decided table,
data/studies/data_continuity/slam_box_overrides.csv (Wimbledon and the US Open 2026). It replaces the box scores,
and where given the score and minutes, of named TML rows with the official Slam feed's, right after the rows are
read and before any score is parsed or box score checked. Every override must find exactly one TML row (by its
names, or since 28 Oct 2026 as re-spellings of them), or the build stops. --no-box-overrides builds without it.
--box-overrides <csv> applies another table instead, which
the live folder takes only with --confirm-live-overrides; --out-dir writes everything elsewhere. Another table may
also name Sackmann rows, through a "source" column (the Roland-Garros candidate of 9 Oct 2026,
docs/studies/rg_first_serve_recount/).

Corrections of corrupt source rows (docs/decisions/2026-10-08-corrupt-data-fixes.md): every build also applies the
tables in data/studies/input_data_audit/fixes/ (src/eda/input_data_audit/corrections.py): row_corrections.csv right
after the overrides (serve points that leave out double faults, box scores exchanged between winner and loser, copied
box scores blanked or replaced from the WTA's own statistics, impossible ages), date_corrections.csv right after them
(an event dated in another week than it was played, since 14 Oct 2026: named by match, not by row, and reported, not
stopping, once the source fixes the date itself), and id_aliases.csv after the repairs (one player's second id). Each
row correction must find its source row exactly, or the build stops. --no-corrections builds
without them; --corrections-dir <folder> applies other tables, into the live folder only with
--confirm-live-overrides.

Live rows (docs/decisions/2026-10-08-prediction-run-box-scores.md): --live-rows <parquet> adds upcoming matches as
Tennis My Life rows with a placeholder result and no box score, so that every builder after Stage 0 computes their
inputs exactly as it does for played matches. A played row of the same event, round and players is dropped first (a
replay of past matches). Only a prediction run's sandbox (src/eda/prediction_run/, marked by .prediction_run_sandbox at
its root) or an --out-dir takes them: never the repository's Stage 0.

Run: ./python.sh src/eda/predictability_diagnostic/stage0_build.py
     [--out-dir <folder>] [--no-box-overrides | --box-overrides <csv> [--confirm-live-overrides]]
     [--no-corrections | --corrections-dir <folder>] [--live-rows <parquet>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import common as A  # noqa: E402
from src.eda.input_data_audit import corrections as X  # noqa: E402
from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

LEVEL_RULES = C.OUT / "stage0_level_rules.csv"
DECIDED_OVERRIDES = ROOT / "data" / "studies" / "data_continuity" / "slam_box_overrides.csv"
DECIDED_CORRECTIONS = X.FIXES      # row_corrections.csv and id_aliases.csv (decision 2026-10-08)
CORRECTION_RULES = {  # action -> (rule id, words, cleaning-log action)
    "add_df_to_svpt": ("E1", "serve points leave out double faults (Sackmann's WTA tour events of 23 Feb - 24 Aug "
                             "2015): double faults added to serve points, both players", "fix_box"),
    "exchange_box": ("E2", "box scores exchanged between winner and loser (confirmed by the WTA's own statistics, "
                           "an official feed or the score): the nine counts exchanged back", "fix_box"),
    "exchange_svgms": ("E3", "service-game counts exchanged between winner and loser: exchanged back", "fix_box"),
    "blank_box": ("E4", "box score copied from another match (WTA Adelaide 2 2022 from Adelaide 2021; the same pair's "
                        "other meeting): blanked", "drop_box"),
    "replace_box": ("E5", "box score copied from another match (WTA Adelaide 2 2022), or contradicted by the tour's own "
                          "box and point record of the match where they agree (since 22 Oct 2026): replaced by the "
                          "tour's own statistics of this match", "replace_box"),
    "set_age": ("E6", "impossible or stale age (Tennis My Life's 2026 WTA ages written without their decimal point; "
                      "ATP Challengers of 17 Aug 2020 aged at 16 Mar 2020): the age from the birth date", "fix"),
    "replace_split": ("E7", "second serves booked as first serves (Roland Garros 2022-2025, Paris Olympics 2024): "
                            "first serves in and points won on each serve from the official record", "fix_box"),
    "set_svgms": ("E8", "service games the score disproves or leaves blank (Australian Open, Roland Garros): both set "
                        "from the score's alternation of serve, from the Slam's own record of who served first",
                  "fix_box"),
    "mark_retired": ("E10", "a retirement written without its marker, the score short of a finished match (every other "
                            "source and the tour's own record call it a retirement; since 22 Oct 2026): RET appended to "
                            "the score, so it reads as retired", "relabel"),
}
EVENT_RULES = {  # event-correction action -> (rule id, words, cleaning-log action); docs/decisions/2026-10-22-...
    "set_level": ("E11", "one edition of an event at the wrong level (Stage 0's level rules match an event by name and "
                         "code, not by year; the tour's own record gives the level): the edition's level corrected",
                  "relabel"),
    "set_surface": ("E12", "one edition of an event on the wrong surface (WTA Paris 2013-14 filed as carpet; the WTA, "
                           "tennis-data and Flashscore give hard): the edition's surface corrected", "relabel"),
}
SACKMANN_END = pd.Timestamp("2026-05-25")      # Sackmann's last main-tour week (lower tiers: 1-2 June)
SANDBOX_MARKER = ROOT / ".prediction_run_sandbox"   # the root of a prediction run's sandbox, the only home of live rows
T0 = time.time()

SOURCES = [  # (source, group, glob under data/dump/matches, tour)
    ("sackmann", "atp_main", "sackmann_archive/atp/atp_matches_[0-9]*.parquet", "atp"),
    ("sackmann", "atp_qual_chall", "sackmann_archive/atp/atp_matches_qual_chall_*.parquet", "atp"),
    ("sackmann", "atp_futures", "sackmann_archive/atp/atp_matches_futures_*.parquet", "atp"),
    ("sackmann", "wta_main", "sackmann_archive/wta/wta_matches_[0-9]*.parquet", "wta"),
    ("sackmann", "wta_qual_itf", "sackmann_archive/wta/wta_matches_qual_itf_*.parquet", "wta"),
    ("tml", "atp_main", "tennis_my_life/atp_main/[0-9]*.parquet", "atp"),
    ("tml", "atp_challenger", "tennis_my_life/atp_challenger/*_challenger.parquet", "atp"),
    ("tml", "atp_qualifying", "tennis_my_life/atp_qualifying/*_atp_quali.parquet", "atp"),
    ("tml", "wta_main", "tennis_my_life/wta_main/*_wta.parquet", "wta"),
    ("tml", "atp_ongoing", "tennis_my_life/ongoing/ongoing_tourneys.parquet", "atp"),
    ("tml", "atp_challenger_ongoing", "tennis_my_life/ongoing/challenger_ongoing_tourneys.parquet", "atp"),
    ("tml", "wta_ongoing", "tennis_my_life/ongoing/wta_ongoing_tourneys.parquet", "wta"),
]
BIO = ["id", "seed", "entry", "name", "hand", "ht", "ioc", "age", "rank", "rank_points"]
KEEP = (["tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "tourney_date", "match_num",
         "score", "best_of", "round", "minutes", "indoor", "_source_file", "_row"]
        + [f"{side}_{b}" for side in ("winner", "loser") for b in BIO]
        + [f"{side}_{c}" for side in ("w", "l") for c in C.BOX_SOURCE_NAMES.values()])

LOG: list[pd.DataFrame] = []     # affected rows per cleaning rule, turned into the cleaning log at the end
RULES: dict[str, dict] = {}      # rule id -> {rule, action}


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def note(rule_id: str, rule: str, action: str, rows: pd.DataFrame) -> None:
    """Record the rows a cleaning rule touched (by raw row id); counts are taken at the end."""
    RULES[rule_id] = {"rule": rule, "action": action}
    LOG.append(pd.DataFrame({"rule_id": rule_id, "rid": rows["rid"].to_numpy()}))


# ------------------------------------------------------------------------------------------------
# Load and normalise

def file_season(path: Path) -> int | None:
    m = re.search(r"(\d{4})", path.name)
    return int(m.group(1)) if m else None


def input_record() -> list[dict]:
    """Every staged file load_raw() reads, and the level rules, with their SHA-256. A staged file's .meta.json
    adds the SHA-256 and retrieval time of the raw file it came from, so a build can be tied to raw versions."""
    def sha(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        return digest.hexdigest()

    out = []
    for source, group, pattern, tour in SOURCES:
        for f in sorted((C.DUMP / "matches").glob(pattern)):
            season = file_season(f)
            if season is not None and season < C.FIRST_YEAR:
                continue
            meta_path = f.parent / (f.name + ".meta.json")
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                meta = {}
            out.append({"path": f.relative_to(ROOT).as_posix(), "sha256": sha(f), "rows": meta.get("rows"),
                        "source_sha256": meta.get("sha256"), "source_retrieved_at": meta.get("retrieved_at")})
    out.append({"path": LEVEL_RULES.relative_to(ROOT).as_posix(), "sha256": sha(LEVEL_RULES)})
    return out


OVERRIDE_COUNTS = [f"{side}_{c}" for side in ("w", "l") for c in C.BOX_SOURCE_NAMES.values()]


def respelled(old: str, new: str) -> bool:
    """One player's name in two spellings, as Tennis My Life re-spells a name between downloads ("Xinyu Wang" as "Xin Yu
    Wang", "Alexander" as "Aleksandr Shevchenko", 25-26 Oct 2026): the last word of either name is a word of the other,
    so a family name written first ("Wang Xinyu") still agrees. Two players who share only a first name do not."""
    a, b = S.norm(old).split(), S.norm(new).split()
    return bool(a) and bool(b) and (a[-1] in b or b[-1] in a)


def respelled_rows(tm: pd.DataFrame, ov: pd.DataFrame, src: pd.Series, todo: pd.Series) -> pd.Series:
    """For each override in ``todo`` (its name keys find no row), the row of its source that re-spelled a player's name
    since the table was built: the one row of the override's source, tour, event and round with the score the table
    recorded (tml_score) in which each player's name is the recorded one or a re-spelling of it (respelled). NaN where
    there is not exactly one such row, or the table records no score or names."""
    out = pd.Series(np.nan, index=ov.index)
    if not todo.any() or not {"tml_score", "winner_name", "loser_name"} <= set(ov.columns):
        return out
    slot = tm["source"] + "|" + tm["tour"] + "|" + tm["tid"] + "|" + tm["round"]
    want = src + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"]
    near = tm[slot.isin(set(want[todo]))].assign(slot=slot)
    for i in ov.index[todo]:
        o = ov.loc[i]
        if not o["tml_score"]:
            continue
        c = near[near["slot"].eq(want[i]) & near["score"].eq(o["tml_score"])]
        hit = c[c["winner_name"].map(lambda n: respelled(o["winner_name"], n)).astype(bool)
                & c["loser_name"].map(lambda n: respelled(o["loser_name"], n)).astype(bool)]
        if len(hit) == 1:
            out[i] = hit.index[0]
    return out


def apply_box_overrides(df: pd.DataFrame, ov: pd.DataFrame, path: str, summary: dict) -> pd.DataFrame:
    """Replace the box scores of the named rows with an official feed's, and the score and minutes where the
    override gives them (docs/decisions/2026-10-06-slam-box-scores.md).

    An override names its row by tour, normalised tournament id, round and the name keys of the row's winner and
    loser (as normalise() makes them), and gives the counts for that winner and loser in the source's own column
    names. The row is a TML row, or a Sackmann row where the table's optional ``source`` column says "sackmann"
    (the decided table's Roland-Garros rows since 9 Oct 2026; its other rows are TML's). Every override must find
    exactly one row of its source, or the build stops: a refresh that renames a round, changes the score or drops the
    row makes the table be re-keyed, never applied to the wrong match.

    Since 28 Oct 2026 (an agent's choice; docs/studies/master_pipeline/process_log.md, Part 21), a source that
    re-spelled a player's name no longer stops the build: an override whose names find no row takes the one row of its
    event and round with the recorded score whose players' names are the recorded ones or re-spellings of them
    (respelled_rows), and the summary lists it. Tennis My Life re-spelled 19 players' names on 25-26 Oct 2026, three of
    them in the table's rows. The table keeps the spellings of the files the instances were built on, so their replays
    find every row by name."""
    src = ov["source"].fillna("").replace("", "tml") if "source" in ov else pd.Series("tml", index=ov.index)
    if not set(src) <= {"tml", "sackmann"}:
        raise SystemExit(f"box overrides: unknown sources {sorted(set(src) - {'tml', 'sackmann'})} in {path}")
    tm = df[df["source"].isin(set(src))]
    key = tm["source"] + "|" + tm["tour"] + "|" + tm["tid"] + "|" + tm["round"] + "|" + tm["wkey"] + "|" + tm["lkey"]
    counts = key.value_counts()
    want = (src + "|" + ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|"
            + ov["loser_key"])
    named = pd.Series(tm.index, index=key.to_numpy())
    rows = want.map(named[~named.index.duplicated(keep=False)])      # NaN: no row by these names, or several
    respelt = want.map(counts).isna()
    rows = rows.fillna(respelled_rows(tm, ov, src, respelt))
    respelt &= rows.notna()
    bad = want[rows.isna()].tolist()
    if bad or want.duplicated().any() or rows.duplicated().any():
        raise SystemExit(f"box overrides: {len(bad)} of {len(want)} rows do not name exactly one row of their source, "
                         f"by their names or as re-spellings of them (first: {bad[:3]}); if the source only renamed "
                         f"them, re-key those rows of {path} to the current staged files "
                         "(data_continuity/slam_overrides.py rebuilds the Wimbledon and US Open rows only)")
    rows = rows.astype("int64").to_numpy()
    respelled_list = [{"override": want.iloc[k], "table": f"{ov['winner_name'].iloc[k]} d. {ov['loser_name'].iloc[k]}",
                       "source_now": f"{df.at[rows[k], 'winner_name']} d. {df.at[rows[k], 'loser_name']}"}
                      for k in np.flatnonzero(respelt.to_numpy())]
    df.loc[rows, OVERRIDE_COUNTS] = ov[OVERRIDE_COUNTS].to_numpy()
    for col in ("score", "minutes"):
        if col not in ov:                       # a table without the column replaces none
            continue
        given = ov[col].fillna("").ne("").to_numpy()
        df.loc[rows[given], col] = ov.loc[given, col].to_numpy()
    scored = ov["score"].fillna("").ne("").to_numpy() if "score" in ov else np.zeros(len(ov), dtype=bool)
    note("O1", "box score taken from the official Slam feed (decision 2026-10-06; " + path + ")", "replace_box",
         df.loc[rows])
    note("O2", "score and minutes taken from the official Slam feed, TML's being cut short (same decision)",
         "replace_score", df.loc[rows[scored]])
    summary["box_overrides"] = {"file": path, "rows": int(len(rows)), "scores_replaced": int(scored.sum()),
                                "by_source": ov.get("box_source", pd.Series(dtype=str)).value_counts().to_dict(),
                                "respelled": respelled_list}
    log(f"box overrides: {len(rows):,} rows take the official feed's box score ({int(scored.sum())} the score too; "
        f"{int(src.eq('sackmann').sum())} of them Sackmann rows)")
    if respelled_list:
        log(f"box overrides: {len(respelled_list)} found with a player's name re-spelled by the source since the table "
            f"was built: {[r['source_now'] for r in respelled_list[:3]]}")
    return df


def correction_table(folder: Path, name: str) -> pd.DataFrame:
    path = Path(folder) / name
    if not path.exists():
        raise SystemExit(f"corrections: {path} is missing; rebuild it (src/eda/input_data_audit/consensus.py) or build "
                         "with --no-corrections")
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def apply_row_corrections(df: pd.DataFrame, folder: Path, summary: dict) -> pd.DataFrame:
    """The audit's row corrections (src/eda/input_data_audit/corrections.py), logged as rules E1-E6."""
    table = correction_table(folder, X.ROW_CORRECTIONS.name)
    df, done = X.apply_row_corrections(df, table)
    for action, rows in done.items():
        if rows.empty:      # an action no row of the table uses leaves no rule in the log (E7 in the decided build)
            continue
        rid, words, act = CORRECTION_RULES[action]
        note(rid, words + " (decision 2026-10-08)", act, df.loc[rows])
    summary["row_corrections"] = {"file": (Path(folder) / X.ROW_CORRECTIONS.name).as_posix(),
                                  "rows": int(len(table)), "by_fix_action": S.records(
                                      table.groupby(["fix", "action"]).size().rename("rows").reset_index())}
    log(f"row corrections: {len(table):,} source rows corrected")
    return df


def apply_date_corrections(df: pd.DataFrame, folder: Path, summary: dict) -> pd.DataFrame:
    """The date corrections (date_corrections.csv beside the row corrections; since 14 Oct 2026, the P6 data issues'
    Tenerife repair: docs/decisions/2026-10-14-p6-data-issues.md), logged as rule E9. A folder without the table (an
    older candidate's) applies none. A correction whose match no longer reads the old date (the source fixed it) is
    reported, not applied, and does not stop the build."""
    path = Path(folder) / X.DATE_CORRECTIONS.name
    if not path.exists():
        return df
    table = pd.read_csv(path, dtype=str, keep_default_na=False)
    df, rep = X.apply_date_corrections(df, table)
    if len(rep["rows"]):
        note("E9", "event dated in another week than it was played (Tennis My Life gave the third Tenerife Challenger "
                   "of 2024 the first one's name and date; three reviewers confirmed the date the matches were played): "
                   "the event's true date (decision 2026-10-14)", "fix_date", df.loc[rep["rows"]])
    summary["date_corrections"] = {"file": path.as_posix(), "rows": int(len(table)), "applied": rep["applied"],
                                   "not_found": rep["not_found"]}
    log(f"date corrections: {rep['applied']:,} of {len(table):,} matches re-dated"
        + (f"; {len(rep['not_found'])} no longer read the old date (the source changed): {rep['not_found'][:3]}"
           if rep["not_found"] else ""))
    return df


def event_corrections(folder: Path | str | None) -> pd.DataFrame:
    """The event corrections (event_corrections.csv beside the row corrections; since 22 Oct 2026,
    docs/decisions/2026-10-22-source-reconciliation-repairs.md). Empty without corrections, or for a folder without
    the table (an older candidate's)."""
    if folder is None or not (Path(folder) / X.EVENT_CORRECTIONS.name).exists():
        return pd.DataFrame()
    return pd.read_csv(Path(folder) / X.EVENT_CORRECTIONS.name, dtype=str, keep_default_na=False)


def apply_event_corrections(sack: pd.DataFrame, tml: pd.DataFrame, table: pd.DataFrame, action: str,
                            summary: dict) -> None:
    """One field of named events (corrections.apply_event_corrections), in each source's frame in place, logged as
    rules E11 (level) and E12 (surface). An event that already reads the corrected value is reported, not applied."""
    if table.empty or not table["action"].eq(action).any():
        return
    rid, words, act = EVENT_RULES[action]
    rep: dict = {"applied": [], "already": []}
    for frame, source in ((sack, "sackmann"), (tml, "tml")):
        t = table[table["source"].eq(source)]
        if not t["action"].eq(action).any():
            continue
        _, r = X.apply_event_corrections(frame, t, action)
        rep["applied"] += r["applied"]
        rep["already"] += r["already"]
        if len(r["rows"]):
            note(rid, words + " (decision 2026-10-22)", act, frame.loc[r["rows"]])
    summary.setdefault("event_corrections", {})[action] = rep
    log(f"event corrections ({action}): {len(rep['applied'])} events corrected"
        + (f"; {len(rep['already'])} already read the corrected value: {rep['already'][:3]}" if rep["already"] else ""))


def apply_id_aliases(m: pd.DataFrame, mp: pd.DataFrame, folder: Path, summary: dict) -> tuple[pd.DataFrame,
                                                                                              pd.DataFrame]:
    """The audit's id aliases: a second id of one player mapped to the established id. An alias whose second id the
    repairs already merged has no rows left and is reported as such. Since 22 Oct 2026 so is one whose source now
    writes the established id itself (Tennis My Life's 2026 WTA file of 22 Oct for Tomljanovic, Cristian and Wolff):
    its second id has no rows, and every row of the tour under its name carries the established id. Any other alias
    without rows (the player gone, or under a third id) still stops the build. A replay of an older dump still holds
    the second ids, which the alias maps as before."""
    aliases = correction_table(folder, X.ID_ALIASES.name)
    present = aliases["from_id"].isin(set(column_items(mp["player_id"])))
    merged = {(a["source_id"], a["canonical_id"]) for a in summary.get("data_repairs", {}).get("identity_aliases", [])}
    gone = [a for a in aliases[~present].itertuples() if (a.from_id, a.to_id) not in merged]
    fixed, lost = [], []
    if gone:
        tour = mp["match_id"].map(m.set_index("match_id")["tour"])
        names = pd.unique(mp["player_name"].astype(str))
        key = mp["player_name"].astype(str).map(dict(zip(names, (A.name_key(n) for n in names))))
        for a in gone:
            ids = set(mp.loc[tour.eq(a.tour).to_numpy() & key.eq(a.name_key).to_numpy(), "player_id"])
            (fixed if ids == {a.to_id} else lost).append((a.from_id, a.to_id))
    if lost:
        raise SystemExit(f"id aliases: {lost[:3]} have no rows, were not merged into the same id by the repairs, and "
                         "their players' rows do not all carry the established id; rebuild the table")
    m, mp, report = X.apply_id_aliases(m, mp, aliases[present], A.name_key)
    summary["id_aliases"] = {"applied": report, "already_merged": aliases.loc[~present, "from_id"].tolist(),
                             "fixed_by_source": [f for f, _ in fixed]}
    log(f"id aliases: {len(report)} second ids mapped ({int((~present).sum()) - len(fixed)} already merged by the "
        f"repairs, {len(fixed)} written as the established id by the source itself: {[f for f, _ in fixed]})")
    return m, mp


def load_raw() -> pd.DataFrame:
    frames = []
    for source, group, pattern, tour in SOURCES:
        for f in sorted((C.DUMP / "matches").glob(pattern)):
            season = file_season(f)
            if season is not None and season < C.FIRST_YEAR:
                continue
            df = pd.read_parquet(f).reindex(columns=KEEP)
            df["source"], df["group"], df["tour"], df["file_season"] = source, group, tour, season
            frames.append(df)
    raw = pd.concat(frames, ignore_index=True)
    raw["rid"] = np.arange(len(raw), dtype="int64")
    return raw


def add_live_rows(raw: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    """Upcoming matches as Tennis My Life rows (group "live"), appended after every source file. Each row carries its
    tour and TML's own columns; the result is a placeholder and the box score blank, so the row is history for no
    match but its own players' later ones, which a prediction run never builds. A row whose ``live_role`` is "drop"
    only names a played match to leave out (a replay's later rounds, which had not been played at its moment).
    A live qualifying row may carry ``event_main_date`` (YYYYMMDD): the start of its event's main draw, which is not
    played yet; the event's date (C05) is then that day, as a played event's qualifying is dated (bet since 22 Oct 2026,
    docs/decisions/2026-10-22-qualifying-bets.md). Rows without it, and every build without live rows, are as before.
    A row whose ``live_role`` is "played" is an earlier qualifying round its source has not published yet, with its
    result and box score from TennisLive (prediction_run/earlier_rounds.py, since 24 Oct 2026); drop_replaced keeps the
    source's row of the same match when there is one."""
    missing = {"tour", "tourney_id", "round", "winner_name", "loser_name", "score"} - set(live.columns)
    if missing:
        raise SystemExit(f"live rows: columns missing: {sorted(missing)}")
    role = live["live_role"].fillna("live") if "live_role" in live.columns else pd.Series("live", index=live.index)
    if not role.isin(["live", "drop", "played"]).all():
        raise SystemExit("live rows: live_role must be 'live', 'drop' or 'played'")
    rows = live.reindex(columns=KEEP + ["tour"]).copy()
    rows["source"], rows["group"], rows["file_season"] = "tml", "live", None
    rows["live_role"] = role.to_numpy()
    rows["_source_file"] = rows["_source_file"].fillna("live_rows")
    if "event_main_date" in live.columns and live["event_main_date"].notna().any():
        rows["live_main_date"] = pd.to_datetime(live["event_main_date"].astype("string").str.replace(r"\.0$", "", regex=True),
                                                format="%Y%m%d", errors="coerce").to_numpy()
    out = pd.concat([raw, rows], ignore_index=True)
    out["rid"] = np.arange(len(out), dtype="int64")
    return out


def drop_replaced(df: pd.DataFrame, summary: dict) -> pd.DataFrame:
    """A played row of the same tour, event, round and players as a live row is dropped: the live row stands in for it
    (a replay of past matches, the prediction run's parity check). Upcoming matches replace nothing. Rows that only name
    a played match to leave out ("drop") go too, with that match. An earlier round filled from TennisLive ("played")
    replaces nothing: it goes when a source row of the same match stands (its source has published it since)."""
    live = df["group"].eq("live")
    played = live & df["live_role"].eq("played")
    standing = live & ~played
    ident = df["tour"] + "|" + df["tid"] + "|" + df["round"] + "|" + df["pair"]
    replaced = ~live & ident.isin(set(ident[standing]))
    named = standing & df["live_role"].eq("drop")
    superseded = played & ident.isin(set(ident[~live & ~replaced]))
    note("LV1", "a played match given again as a live row (a replay): its played row dropped, the live row (placeholder "
                "result, no box score) stands in for it", "drop_row",
         df[replaced & ident.isin(set(ident[standing & ~named]))])
    note("LV2", "a played match a replay leaves out (played after its moment): dropped", "drop_row",
         df[replaced & ~ident.isin(set(ident[standing & ~named]))])
    summary["live_rows"] = {"rows": int((standing & ~named).sum()), "played_rows_replaced": int(replaced.sum()),
                            "left_out_by_name": int(named.sum())}
    if played.any():
        note("LV3", "an earlier qualifying round filled from TennisLive (earlier_rounds.py) that its source holds: the "
                    "fill dropped, the source's row stands", "drop_row", df[superseded])
        summary["live_rows"].update(earlier_rounds_filled=int((played & ~superseded).sum()),
                                    earlier_rounds_superseded=int(superseded.sum()))
    log(f"live rows: {int((standing & ~named).sum())} added, {int(replaced.sum())} played rows dropped"
        + (f", {int((played & ~superseded).sum())} earlier rounds filled ({int(superseded.sum())} superseded)"
           if played.any() else ""))
    return df[~replaced & ~named & ~superseded].drop(columns="live_role").copy()


def text(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip()


def num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(text(s).replace("", np.nan), errors="coerce")


def mode_by(frame: pd.DataFrame, keys: list[str], col: str) -> pd.Series:
    """Most common non-missing value of ``col`` per group (ties: the smallest value)."""
    d = frame.dropna(subset=[col])
    cnt = d.groupby(keys + [col]).size().rename("_n").reset_index()
    cnt = cnt.sort_values(keys + ["_n", col], ascending=[True] * len(keys) + [False, True])
    return cnt.drop_duplicates(keys).set_index(keys)[col]


def lookup(series: pd.Series, frame: pd.DataFrame, keys: list[str]) -> pd.Series:
    """``series`` (indexed by ``keys``) read off for each row of ``frame``."""
    idx = pd.MultiIndex.from_frame(frame[keys]) if len(keys) > 1 else pd.Index(frame[keys[0]])
    return pd.Series(series.reindex(idx).to_numpy(), index=frame.index)


def column_items(s: pd.Series):
    """The values a Python loop over ``s`` yields, as one array (11 Oct 2026, for speed: pandas reads an Arrow-backed
    text column one element at a time when a loop iterates the Series, about half of Stage 0's time). For text,
    object, bool and int64 columns the array holds the very objects iteration yields, a missing value included (it
    matters for tuples in sets); any other dtype is iterated as before."""
    if isinstance(s.dtype, pd.StringDtype) or s.dtype == object or s.dtype in (np.dtype(bool), np.dtype("int64")):
        return s.to_numpy(dtype=object)
    return list(s)


def normalise(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw
    for c in ["tourney_id", "tourney_name", "tourney_level", "round", "score", "surface", "indoor",
              "winner_id", "loser_id", "winner_name", "loser_name", "match_num"]:
        df[c] = text(df[c])
    df["round"] = df["round"].str.upper().replace({"3RD/4TH": "BR"})
    df["qualifying"] = df["round"].str.fullmatch(r"Q\d")
    df["tdate"] = pd.to_datetime(df["tourney_date"], format="%Y%m%d", errors="coerce")
    id_year = pd.to_numeric(df["tourney_id"].str[:4], errors="coerce")
    df["season"] = df["file_season"].fillna(id_year).fillna(df["tdate"].dt.year).astype("Int64")
    df["tid"] = df["tourney_id"].str.replace(r"-0+(\d)", r"-\1", regex=True)
    # an event: Sackmann's tournament id is unique per event; TML reuses one id for two events of a
    # season (Adelaide 1 and 2 in 2022), so its events are the id and the name together
    df["ekey"] = np.where(df["source"].eq("tml"), df["tid"] + "|" + df["tourney_name"], df["tid"])
    df["wkey"], df["lkey"] = S.keys_for(df["winner_name"]), S.keys_for(df["loser_name"])
    df["pair"] = S.pair_of(df["wkey"], df["lkey"])
    df["code"] = df["tourney_level"]
    df["surface"] = df["surface"].str.capitalize().replace({"": pd.NA})
    df["indoor_flag"] = df["indoor"].map({"I": True, "O": False})
    return df


# ------------------------------------------------------------------------------------------------
# Scores: status, sets, games, tiebreaks

SET_TOKEN = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")
BRACKET_TOKEN = re.compile(r"^\[(\d+)-(\d+)\](?:\(\d+\))?$")


@lru_cache(maxsize=None)
def tokens_of(score: str) -> tuple[tuple, str]:
    """Set tokens (winner's games, loser's games, tiebreak points or -1, is a match tiebreak) and the
    remaining marker text, lower case."""
    s = score.replace("&nbsp;", " ").replace(",", " ").strip()
    sets, markers = [], []
    for tok in s.split():
        m = SET_TOKEN.match(tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else -1, False))
            continue
        m = BRACKET_TOKEN.match(tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), -1, True))
            continue
        markers.append(tok.lower())
    return tuple(sets), " ".join(markers)


def status_of(sets: tuple, marker: str) -> str:
    """Status detail: completed, retired, walkover, walkover_after_play, bye, defaulted, abandoned, unknown."""
    games = sum(a + b for a, b, _, br in sets if not br)
    if re.search(r"\bret|^re$|\bre\b", marker):
        return "retired"
    if re.search(r"\bdef", marker):
        return "defaulted"
    if "w/o" in marker or "walkover" in marker:
        return "walkover_after_play" if games > 0 else "walkover"
    if "bye" in marker:
        return "bye"
    if re.search(r"abd|abandon|unfinished|\bwea\b|^ab\.?$", marker):
        return "abandoned"
    if marker or not sets:
        return "unknown"
    return "completed"


STATUS = {"completed": "completed", "retired": "retired", "walkover_after_play": "retired",
          "walkover": "walkover", "bye": "walkover", "defaulted": "other", "abandoned": "other", "unknown": "other"}


def set_complete(a: int, b: int, tb: int, bracket: bool, short: bool) -> bool:
    hi, lo = max(a, b), min(a, b)
    if bracket:
        return (hi >= 7 and hi - lo >= 2) or (hi == 1 and lo == 0)
    if short:
        return hi == 4 and lo <= 3
    return (hi >= 6 and hi - lo >= 2) or (hi == 7 and lo == 6) or (hi == 13 and lo == 12) or (tb >= 0 and hi - lo == 1 and hi >= 7)


def short_like(sets: tuple) -> bool:
    """Every standard set of the score ends at four games (first to 4, tiebreak at 3-3)."""
    std = [(a, b) for a, b, _, br in sets if not br]
    return bool(std) and all(max(a, b) == 4 for a, b in std)


def is_tiebreak(a: int, b: int, tb: int, bracket: bool, short: bool) -> bool:
    hi, lo = max(a, b), min(a, b)
    if bracket:
        return True
    if short:
        return hi == 4 and lo == 3
    return tb >= 0 or (hi, lo) in ((7, 6), (13, 12))


@lru_cache(maxsize=None)
def score_counts(score: str, short: bool) -> tuple:
    """(sets_w, sets_l, games_w, games_l, tb_w, tb_l, std_tiebreaks, has_bracket, short_like, last_done),
    read from the winner's side as the sources write it.

    Games count every set as played, the unfinished last set of a retirement included. Sets and
    tiebreaks count complete sets only; ``last_done`` says whether the last set is complete by its
    numbers. A match tiebreak ([10-8]) counts as a set and a tiebreak but adds no games.
    """
    sets, _ = tokens_of(score)
    sw = sl = gw = gl = tw = tl = std_tb = 0
    bracket = any(br for *_, br in sets)
    done = False
    for a, b, tb, br in sets:
        done = set_complete(a, b, tb, br, short)
        if not br:
            gw, gl = gw + a, gl + b
        if done and a != b:
            sw, sl = sw + (a > b), sl + (b > a)
            if is_tiebreak(a, b, tb, br, short):
                tw, tl = tw + (a > b), tl + (b > a)
                std_tb += 0 if br else 1
    return sw, sl, gw, gl, tw, tl, std_tb, bracket, short_like(sets), done


def parse_scores(df: pd.DataFrame) -> pd.DataFrame:
    parsed = {s: tokens_of(s) for s in df["score"].unique()}
    df["status_detail"] = df["score"].map({s: status_of(*v) for s, v in parsed.items()})
    df["status"] = df["status_detail"].map(STATUS)
    return df


# The main tour (current_best_model/history.MAIN_TOUR, never gated by the freeze of 8 Oct 2026). A rule that reads a
# score anew applies there only: lower-level history changes through the candidate route (CLAUDE.md).
MAIN_LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "TEAM")


def match_tiebreak_events(df: pd.DataFrame, decider: pd.Series, ev_key: list[str]) -> pd.Series:
    """The rows of each main-tour event that plays a match tiebreak instead of its deciding set: one of its completed
    deciders is certainly a match tiebreak (a 10-7 ends no set) and every decider's last "set" reaches 10. Such an
    event's 10-8 or 13-11 is a match tiebreak too, which plain_match_tiebreak cannot tell from the score alone (the
    owner's go-ahead of 13 Oct 2026: the Laver Cup 2026's two, read as sets of 18 and 24 games, had their box scores
    dropped as covering part of the match; docs/studies/master_pipeline/process_log.md, Part 2). The bracketed share
    (mtb_event) misses such events: Tennis My Life writes no brackets."""
    from src.eda.feature_alpha_audit.repair_data import plain_match_tiebreak
    main = df["level"].isin(MAIN_LEVELS) & ~df["qualifying"].astype(bool)
    d = df[decider & main]
    if d.empty:
        return pd.Series(False, index=df.index)
    last = d["score"].astype(str).str.split().str[-1].str.extract(r"^\[?(\d+)-(\d+)")
    reaches = last.apply(pd.to_numeric, errors="coerce").max(axis=1).ge(10)
    certain = pd.Series([plain_match_tiebreak(s, lv, "completed", sh) != s for s, lv, sh in
                         zip(column_items(d["score"].astype(str)), column_items(d["level"]),
                             column_items(d["short_event"]))], index=d.index)
    ev = d[ev_key].assign(reaches=reaches, certain=certain).groupby(ev_key).agg(
        reaches=("reaches", "all"), certain=("certain", "any"))
    return lookup(ev["reaches"] & ev["certain"], df, ev_key).fillna(False).astype(bool) & main


def score_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Per-match counts from the score, once each event's format (short sets or not; a match tiebreak by the event's
    rule: match_tiebreak_events, in ``mtb_rule``) is known."""
    from src.eda.feature_alpha_audit.repair_data import plain_match_tiebreak
    rule = df["mtb_rule"] if "mtb_rule" in df else pd.Series(False, index=df.index)
    counted = [plain_match_tiebreak(s, lv, st, sh, mr) for s, lv, st, sh, mr in
               zip(column_items(df["score"]), column_items(df.get("level", pd.Series("", index=df.index))),
                   column_items(df.get("status", pd.Series("completed", index=df.index))),
                   column_items(df["short_event"]), column_items(rule))]
    keys = list(zip(counted, df["short_event"]))
    vals = {k: score_counts(*k) for k in set(keys)}
    arr = np.array([vals[k] for k in keys], dtype="int64")
    cols = ["sets_w", "sets_l", "games_w", "games_l", "tb_w", "tb_l", "std_tb", "has_bracket", "short_like", "last_done"]
    for i, c in enumerate(cols):
        df[c] = arr[:, i]
    for c in ("has_bracket", "short_like", "last_done"):
        df[c] = df[c].astype(bool)
    return df


# ------------------------------------------------------------------------------------------------
# Levels

def rule_levels(df: pd.DataFrame) -> pd.DataFrame:
    rules = pd.read_csv(LEVEL_RULES, dtype=str, keep_default_na=False).sort_values("order", key=lambda s: s.astype(int))
    level = pd.Series(pd.NA, index=df.index, dtype="object")
    refine = pd.Series(False, index=df.index)
    rule_no = pd.Series(pd.NA, index=df.index, dtype="object")
    name = df["tourney_name"].str.lower()
    for r in rules.itertuples():
        todo = level.isna()
        m = todo.copy()
        if r.source != "*":
            m &= df["source"].eq(r.source)
        if r.tour != "*":
            m &= df["tour"].eq(r.tour)
        if r.code != "*":
            m &= df["code"].str.fullmatch(r.code)
        if r.name:
            m &= name.str.contains(r.name, regex=True)
        level[m], refine[m], rule_no[m] = r.level, r.refine == "tml_majority", r.order
    df["level"], df["refine"], df["level_rule"] = level, refine, rule_no
    return df


def event_levels(df: pd.DataFrame) -> pd.Series:
    """Each event's level: the most common level of its main-draw rows, else of all its rows."""
    keys = ["source", "tour", "ekey"]
    lv = mode_by(df[~df["qualifying"]], keys, "level").combine_first(mode_by(df, keys, "level"))
    return lookup(lv, df, keys)


# ------------------------------------------------------------------------------------------------
# Duplicates inside one source

def id_or_name(ids: pd.Series, keys: pd.Series) -> pd.Series:
    return ids.where(ids != "", "name:" + keys)


def drop_repeats(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """Same event, round and players listed twice. Same winner: keep one (the row with a box score,
    then the earliest). Different winners: keep neither (the source contradicts itself)."""
    name = {"sackmann": "Sackmann", "tml": "TML"}.get(source, source)
    a, b = id_or_name(df["winner_id"], df["wkey"]), id_or_name(df["loser_id"], df["lkey"])
    lo, hi = np.where(a < b, a, b), np.where(a < b, b, a)
    key = df["tour"] + "|" + df["ekey"] + "|" + df["round"] + "|" + lo + "|" + hi
    dup = key.duplicated(keep=False)
    grp = df[dup].assign(key=key[dup], stats=num(df.loc[dup, "w_svpt"]).fillna(0) > 0,
                         scored=df.loc[dup, "status"].ne("other"))
    conflict = grp.groupby("key")["winner_id"].transform("nunique") > 1
    drop_conflict = grp[conflict]
    keep_order = grp[~conflict].sort_values(["key", "stats", "scored", "rid"], ascending=[True, False, False, True])
    drop_repeat = keep_order[keep_order.duplicated("key", keep="first")]
    note(f"D1_{source}", f"{name}: the same match listed twice in one event (same round and players, same winner); "
         "one kept, preferring the row with a box score", "drop_row", drop_repeat)
    note(f"D2_{source}", f"{name}: the same event, round and players listed twice with different winners; "
         "both dropped", "drop_row", drop_conflict)
    out = df.drop(index=drop_repeat.index.union(drop_conflict.index))
    # the same match copied into two events of the same week (same round, players, date and score)
    a, b = id_or_name(out["winner_id"], out["wkey"]), id_or_name(out["loser_id"], out["lkey"])
    lo, hi = np.where(a < b, a, b), np.where(a < b, b, a)
    key = out["tour"] + "|" + out["round"] + "|" + lo + "|" + hi + "|" + out["tourney_date"] + "|" + out["score"]
    copies = out.assign(key=key).sort_values(["key", "tid", "rid"])
    copies = copies[copies.duplicated("key", keep="first") & copies["score"].ne("")]
    note(f"D3_{source}", f"{name}: the same match (same round, players, week and score) copied into a second event; "
         "the copy under the later tournament id dropped", "drop_row", copies)
    return out.drop(index=copies.index)


# ------------------------------------------------------------------------------------------------
# Linking Tennis My Life to Sackmann

def orient_pairs(t: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    """For linked (TML row, Sackmann row) pairs, which TML id is which Sackmann id, matched by name.

    t and s are aligned frames (same length, one link per position). A player is matched on an
    identical name key; the other player follows when the names share a word (as in scan.py)."""
    rows = []
    tw, tl, sw, sl = t["wkey"].to_numpy(), t["lkey"].to_numpy(), s["wkey"].to_numpy(), s["lkey"].to_numpy()
    tiw, til, siw, sil = t["winner_id"].to_numpy(), t["loser_id"].to_numpy(), s["winner_id"].to_numpy(), s["loser_id"].to_numpy()
    tour = t["tour"].to_numpy()

    def share(x, y):
        return bool(set(x.split()) & set(y.split()))

    for i in range(len(t)):
        if tw[i] == sw[i]:
            pairs = [(tiw[i], siw[i], True), (til[i], sil[i], tl[i] == sl[i] or share(tl[i], sl[i]))]
        elif tw[i] == sl[i]:
            pairs = [(tiw[i], sil[i], True), (til[i], siw[i], tl[i] == sw[i] or share(tl[i], sw[i]))]
        elif tl[i] == sl[i]:
            pairs = [(til[i], sil[i], True), (tiw[i], siw[i], share(tw[i], sw[i]))]
        elif tl[i] == sw[i]:
            pairs = [(til[i], siw[i], True), (tiw[i], sil[i], share(tw[i], sl[i]))]
        else:
            pairs = []
        for a, b, ok in pairs:
            if ok and a and b:
                rows.append((tour[i], a, b))
    return pd.DataFrame(rows, columns=["tour", "tml_id", "sackmann_id"])


def crosswalk(pairs: pd.DataFrame) -> tuple[pd.Series, dict]:
    """TML id -> Sackmann id by majority over linked matches, per tour."""
    counts = pairs.groupby(["tour", "tml_id", "sackmann_id"]).size().rename("n").reset_index()
    counts = counts.sort_values(["tour", "tml_id", "n", "sackmann_id"], ascending=[True, True, False, True])
    best = counts.drop_duplicates(["tour", "tml_id"])
    per_code = counts.groupby(["tour", "tml_id"])["sackmann_id"].nunique()
    per_sid = counts.groupby(["tour", "sackmann_id"])["tml_id"].nunique()
    stats = {}
    for tour in C.TOURS:
        p = pairs[pairs["tour"] == tour]
        stats[tour] = {"links_used": int(len(p)), "tml_ids_learned": int((best["tour"] == tour).sum()),
                       "tml_ids_with_conflicting_sackmann_ids": int((per_code.loc[tour] > 1).sum()) if tour in per_code.index.get_level_values(0) else 0,
                       "sackmann_ids_with_several_tml_ids": int((per_sid.loc[tour] > 1).sum()) if tour in per_sid.index.get_level_values(0) else 0,
                       "pairs_where_tml_id_equals_sackmann_id_pct": S.pct(int((p["tml_id"] == p["sackmann_id"]).sum()), len(p))}
    xw = best.set_index(["tour", "tml_id"])["sackmann_id"]
    return xw, stats


GENERIC_WORDS = {"ch", "challenger", "open", "atp", "wta", "itf", "masters", "the", "de", "del", "of", "cup", "tennis",
                 "international", "championships", "championship", "trophy", "tournament", "classic", "k"}


@lru_cache(maxsize=None)
def name_words(name: str) -> frozenset:
    """Distinctive words of a tournament name ('Rimini CH' -> {'rimini'})."""
    return frozenset(w for w in S.norm(name).split() if w not in GENERIC_WORDS and not w.isdigit() and len(w) > 1)


def same_event(t_rows: pd.DataFrame, s_rows: pd.DataFrame) -> np.ndarray:
    """2 if the tournament ids agree, 1 if the tournament names share a distinctive word, else 0 (aligned rows)."""
    tid_eq = t_rows["tid"].to_numpy() == s_rows["tid"].to_numpy()
    words = np.array([bool(name_words(a) & name_words(b))
                      for a, b in zip(t_rows["tourney_name"].to_numpy(), s_rows["tourney_name"].to_numpy())])
    return np.where(tid_eq, 2, np.where(words, 1, 0))


@lru_cache(maxsize=None)
def set_scores(score: str) -> tuple:
    """The set scores alone ('6-2 7-6(0)' and '6-2 7-6' agree), for comparing two sources' records."""
    return tuple((a, b, br) for a, b, _, br in tokens_of(score)[0])


def pick(cand: pd.DataFrame, t: pd.DataFrame, s: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index]:
    """One Sackmann row per TML row and one TML row per Sackmann row, from candidate pairs (ri, li, gap).

    A candidate is acceptable when the tournament weeks are within 10 days (scan.py's window), or when
    the set scores are identical and either the weeks are within a month or the event agrees (same
    tournament id, or a shared word in its name) within a season. TML dates some Challengers weeks off,
    and gives a season's later editions of a Challenger the first edition's name and date, sometimes
    its id too: every Forli Challenger of 2022 reads 'Forli 1' with the first one's date.
    scan.py's resolve() then takes the nearest week, which misreads a pair who met in the same round
    of two events a week apart; here a candidate in the same event (same tournament id, else a shared
    word in the tournament name) comes first, then identical set scores, then the nearest week.
    Equal best candidates make the TML row ambiguous. When two TML rows claim one Sackmann row, the
    better-ranked keeps it and the other stays unlinked.
    Returns the kept links (ri, li, ev, sc, dist) and the ambiguous TML row ids."""
    cols = ["ri", "li", "ev", "sc", "dist"]
    if cand.empty:
        return pd.DataFrame(columns=cols), pd.Index([])
    c = cand.copy()
    c["dist"] = c["gap"].abs()
    ts, ss = t.loc[c["ri"], "score"].map(set_scores).to_numpy(), s.loc[c["li"], "score"].map(set_scores).to_numpy()
    c["sc"] = np.array([a == b and len(a) > 0 for a, b in zip(ts, ss)])
    c["ev"] = same_event(t.loc[c["ri"]], s.loc[c["li"]])
    ok = (c["dist"] <= 10) | (c["sc"] & ((c["dist"] <= 31) | ((c["ev"] >= 1) & (c["dist"] <= 366))))
    c = c[ok]
    if c.empty:
        return pd.DataFrame(columns=cols), pd.Index([])
    order = ["ev", "sc", "dist"]
    c = c.sort_values(["ri"] + order + ["li"], ascending=[True, False, False, True, True])
    top = c.drop_duplicates("ri")
    ties = c.merge(top[["ri"] + order], on=["ri"] + order).groupby("ri")["li"].nunique()
    ambiguous = ties.index[ties > 1]
    kept = top[~top["ri"].isin(ambiguous)].sort_values(["li"] + order + ["ri"], ascending=[True, False, False, True, True])
    return kept.drop_duplicates("li")[cols], ambiguous


def anchor_candidates(s: pd.DataFrame, t: pd.DataFrame) -> pd.DataFrame:
    """scan.py's one-player anchor (same tour, tournament id and round, one identical player name key),
    keeping every candidate with its date gap rather than only the rows with a single one: both
    sources reuse a Challenger's id for its several editions in a season, and anchor_links() never
    compares dates."""
    cands = []
    for rside in ("wkey", "lkey"):
        for lside in ("wkey", "lkey"):
            r = t[["tour", "tid", "round", rside, "tdate"]].rename(columns={rside: "k"}).assign(ri=t.index)
            left = s[["tour", "tid", "round", lside, "tdate"]].rename(columns={lside: "k", "tdate": "sdate"}).assign(li=s.index)
            cands.append(r.merge(left, on=["tour", "tid", "round", "k"])[["ri", "li", "tdate", "sdate"]])
    c = pd.concat(cands).drop_duplicates(["ri", "li"])
    c["gap"] = (c["tdate"] - c["sdate"]).dt.days
    return c[["ri", "li", "gap"]]


def id_pairs(rows: pd.DataFrame, a: pd.Series, b: pd.Series) -> pd.Series:
    return pd.Series(np.where(a < b, a + "|" + b, b + "|" + a), index=rows.index)


def link_tml(sack: pd.DataFrame, tml: pd.DataFrame, summary: dict) -> tuple[pd.DataFrame, pd.Series]:
    """Link every TML row to at most one Sackmann row, and each Sackmann row to at most one TML row
    (pass 4 excepted: it finds TML's own repeats). Returns tml with link_status, link_rid and
    link_event (2 same tournament id, 1 shared name word, 0 neither), and the TML id -> Sackmann id
    crosswalk."""
    s = sack.set_index("rid", drop=False)
    t = tml.set_index("rid", drop=False)
    s_named, t_named = s[s["pair"] != ""], t[t["pair"] != ""]
    status = pd.Series("unlinked", index=t.index, dtype=object)
    # pass 1 (scan.py's candidates): the exact normalised name pair in the same tour and round
    cand = S.link(s_named, t_named.rename(columns={"tdate": "date"}), ["tour", "round", "pair"])
    u1, amb1 = pick(cand, t, s)
    status.loc[u1["ri"]] = "exact_name_pair"
    status.loc[amb1] = "ambiguous"
    # audit of scan.py's own choices on the same rows (reported, not used)
    n1_scan, u1_scan = S.resolve(cand, window=(-10, 10))
    theirs, mine = u1_scan.set_index("ri")["li"], u1.set_index("ri")["li"]
    both = theirs.index.intersection(mine.index)
    other = theirs.loc[both][theirs.loc[both].to_numpy() != mine.loc[both].to_numpy()]
    audit = {"pass1_scan_links": int(len(theirs)),
             "pass1_scan_link_to_another_sackmann_row_than_stage0": int(len(other)),
             "pass1_scan_link_that_stage0_rejects": int(len(theirs.index.difference(mine.index))),
             "pass1_scan_rows_sharing_a_sackmann_row_with_another_tml_row": int(theirs.duplicated(keep=False).sum())}
    # pass 2 (scan.py): one identical player in the same tournament and round; not round robins, where a
    # player plays several matches in one round
    rest = t_named[status.reindex(t_named.index).eq("unlinked") & t_named["round"].ne("RR")]
    free = s_named[~s_named["rid"].isin(u1["li"]) & s_named["round"].ne("RR")]
    cand2 = anchor_candidates(free, rest)
    u2, amb2 = pick(cand2, t, s)
    # scan.py's anchor as scan.py runs it, after its own pass 1: every round, no date check
    rest_scan = t_named[S.statuses(t_named.index, n1_scan).eq("unlinked")]
    n2s, u2s = S.anchor_links(s_named.drop(index=u1_scan["li"].unique()), rest_scan)
    gap_s = (t.loc[u2s["ri"], "tdate"].to_numpy() - s.loc[u2s["li"], "tdate"].to_numpy()) / np.timedelta64(1, "D")
    same_s = np.array([set_scores(a) == set_scores(b) for a, b in
                       zip(t.loc[u2s["ri"], "score"].to_numpy(), s.loc[u2s["li"], "score"].to_numpy())])
    audit.update({"pass2_scan_anchor_links": int(len(u2s)),
                  "pass2_scan_anchor_links_more_than_31_days_apart": int((np.abs(gap_s) > 31).sum()),
                  "pass2_scan_anchor_links_more_than_31_days_apart_with_other_set_scores":
                      int(((np.abs(gap_s) > 31) & ~same_s).sum()),
                  "pass2_scan_anchor_links_in_round_robins": int(t.loc[u2s["ri"], "round"].eq("RR").sum())})
    summary["scan_py_audit"] = audit
    summary["pass2_anchor_candidates_rejected"] = int(cand2["ri"].nunique() - len(u2) - len(amb2))
    status.loc[u2["ri"]] = "one_player_anchor"
    status.loc[amb2] = "ambiguous"
    links = pd.concat([u1, u2], ignore_index=True)

    pairs = orient_pairs(t.loc[links["ri"]].reset_index(drop=True), s.loc[links["li"]].reset_index(drop=True))
    xw, xw_stats = crosswalk(pairs)
    summary["crosswalk"] = xw_stats

    # pass 3: the two resolved player ids in the same tour and round
    rest = t[status.eq("unlinked") & t["winner_id"].ne("") & t["loser_id"].ne("")].copy()
    rest["ids"] = id_pairs(rest, resolve_ids(rest, "winner", xw), resolve_ids(rest, "loser", xw))
    s3 = s[~s["rid"].isin(links["li"]) & s["winner_id"].ne("") & s["loser_id"].ne("")].copy()
    s3["ids"] = id_pairs(s3, s3["tour"] + ":" + s3["winner_id"], s3["tour"] + ":" + s3["loser_id"])
    cand = rest[["rid", "tour", "round", "ids", "tdate"]].rename(columns={"rid": "ri"}).merge(
        s3[["rid", "tour", "round", "ids", "tdate"]].rename(columns={"rid": "li", "tdate": "sdate"}),
        on=["tour", "round", "ids"])
    cand["gap"] = (cand["tdate"] - cand["sdate"]).dt.days
    u3, amb3 = pick(cand[["ri", "li", "gap"]], t, s)
    status.loc[u3["ri"]] = "resolved_ids"
    status.loc[amb3] = "ambiguous"
    links = pd.concat([links, u3], ignore_index=True)

    # pass 4: the same event and the same two players under another round label (a pair meets once per
    # event outside round robins; at team events TML calls ATP Cup group matches R128 and 2020's
    # knockout matches RR, so there round robins count too, and a pair who met twice is ambiguous).
    # A Sackmann row may be claimed again: this pass also finds TML's own repeats.
    ev = event_map(t, s, links)
    rr_ok_t = t["round"].ne("RR") | t["level"].eq("TEAM")
    rest = t[status.eq("unlinked") & t["winner_id"].ne("") & t["loser_id"].ne("") & rr_ok_t].copy()
    rest["ids"] = id_pairs(rest, resolve_ids(rest, "winner", xw), resolve_ids(rest, "loser", xw))
    rest["stid"] = pd.Series(list(zip(rest["tour"], rest["ekey"])), index=rest.index).map(ev)
    s4 = s[s["winner_id"].ne("") & s["loser_id"].ne("") & (s["round"].ne("RR") | s["level"].eq("TEAM"))].copy()
    s4["ids"] = id_pairs(s4, s4["tour"] + ":" + s4["winner_id"], s4["tour"] + ":" + s4["loser_id"])
    cand = rest[rest["stid"].notna()][["rid", "tour", "stid", "ids"]].rename(columns={"rid": "ri"}).merge(
        s4[["rid", "tour", "tid", "ids"]].rename(columns={"rid": "li", "tid": "stid"}), on=["tour", "stid", "ids"])
    n4 = cand.groupby("ri")["li"].nunique()
    status.loc[n4.index[n4 == 1]] = "same_event_other_round"
    status.loc[n4.index[n4 > 1]] = "ambiguous"
    u4 = cand[cand["ri"].isin(n4.index[n4 == 1])][["ri", "li"]].assign(ev=2, sc=True, dist=0)
    links = pd.concat([links, u4], ignore_index=True)

    out = tml.copy()
    out["link_status"] = status.reindex(out["rid"]).to_numpy()
    by_ri = links.drop_duplicates("ri").set_index("ri")
    out["link_rid"] = out["rid"].map(by_ri["li"]).astype("Int64")
    out["link_event"] = out["rid"].map(by_ri["ev"]).astype("Int64")
    out["link_days"] = out["rid"].map(by_ri["dist"]).astype("Int64")
    out["link_same_score"] = out["rid"].map(by_ri["sc"]).astype("boolean")
    lk = out.dropna(subset=["link_rid"])
    summary["links_by_agreement"] = S.records(
        lk.assign(days=pd.cut(lk["link_days"].astype(float), [-1, 10, 31, 366], labels=["0-10", "11-31", "32-366"]))
        .groupby(["tour", "link_status", "link_event", "link_same_score", "days"], observed=True).size()
        .rename("rows").reset_index())
    return out, xw


def resolve_ids(rows: pd.DataFrame, side: str, xw: pd.Series) -> pd.Series:
    """A TML player id in the canonical id system: the learned Sackmann id, else the TML id itself
    (WTA files share Sackmann's numbers; ATP codes keep an 'atpcode:' prefix)."""
    ids = rows[f"{side}_id"]
    mapped = pd.Series(list(zip(rows["tour"], ids)), index=rows.index).map(xw)
    fallback = np.where(rows["tour"].eq("atp"), "atpcode:" + ids, "wta:" + ids)
    out = pd.Series(np.where(mapped.notna(), rows["tour"] + ":" + mapped.fillna(""), fallback), index=rows.index)
    return out.where(ids != "", "")


def unambiguous_name_ids(known: pd.DataFrame) -> pd.Series:
    """Resolve exact names only when every observed canonical ID agrees."""
    nonblank = known[known["key"].notna() & known["key"].ne("")]
    grouped = nonblank.groupby(["tour", "key"])["pid"]
    count = grouped.nunique()
    return grouped.first().loc[count == 1]


def event_map(t: pd.DataFrame, s: pd.DataFrame, links: pd.DataFrame) -> dict:
    """(tour, TML event) -> Sackmann tournament id, by majority over the event's linked rows."""
    lk = pd.DataFrame({"tour": t.loc[links["ri"], "tour"].to_numpy(), "ttid": t.loc[links["ri"], "ekey"].to_numpy(),
                       "stid": s.loc[links["li"], "tid"].to_numpy()})
    top = lk.groupby(["tour", "ttid", "stid"]).size().rename("n").reset_index()
    top = top.sort_values(["tour", "ttid", "n", "stid"], ascending=[True, True, False, True]).drop_duplicates(["tour", "ttid"])
    return {(a, b): c for a, b, c in zip(top["tour"], top["ttid"], top["stid"])}


# ------------------------------------------------------------------------------------------------
# Box scores

def box_frame(df: pd.DataFrame, side: str) -> pd.DataFrame:
    return pd.DataFrame({b: num(df[f"{side}_{src}"]) for b, src in C.BOX_SOURCE_NAMES.items()}, index=df.index)


def box_kind(df: pd.DataFrame, side: str) -> pd.Series:
    """Per side: blank, all_zero, no_svgms (only service games blank), partial, full."""
    filled = pd.DataFrame({b: text(df[f"{side}_{src}"]).ne("") for b, src in C.BOX_SOURCE_NAMES.items()})
    vals = box_frame(df, side)
    n = filled.sum(axis=1)
    nonzero = (vals.fillna(0) != 0).sum(axis=1)
    kind = np.select([n == 0, nonzero == 0, (n == 8) & ~filled["sv_gms"], n < 9],
                     ["blank", "all_zero", "no_svgms", "partial"], "full")
    return pd.Series(kind, index=df.index)


BOX_CHECKS = [  # (id, plain words, required by the Brief, what a failure drops)
    ("B0", "negative box-score count", True, "box"),
    ("B1", "first serves in exceed serve points", True, "box"),
    ("B2", "first-serve points won exceed first serves in", True, "box"),
    ("B3", "second-serve points won exceed second serves", True, "box"),
    ("B4", "break points saved exceed break points faced", True, "box"),
    ("B5", "service games disagree with the games in the score by more than one, whether tiebreaks count as "
           "service games or not", True, "service games"),
    ("B6", "double faults exceed second serves", False, "box"),
    ("B7", "aces exceed serve points won", False, "box"),
    ("B8", "breaks conceded exceed service games (checked where service games pass B5)", False, "box"),
    ("B9", "fewer than 4.5 serve points per game in the score (a game has at least 4 points): the counts cover "
           "part of the match", False, "box"),
]
MIN_POINTS_PER_GAME = 4.5


def box_scores(df: pd.DataFrame) -> pd.DataFrame:
    """The nine counts per side, kept only where both sides are present and pass the checks.

    A service-games count that disagrees with the score (B5) is dropped on its own: the point counts
    do not depend on it (TML's women's Wimbledon 2026 has plausible points and impossible service
    games). Any other failed check drops the match's box score. Service games may include tiebreak
    games (the Slam feeds count them, Sackmann's other files do not); both are accepted and recorded
    in ``sv_gms_incl_tb`` where a tiebreak makes the difference visible."""
    w, l = box_frame(df, "w"), box_frame(df, "l")
    kw, kl = box_kind(df, "w"), box_kind(df, "l")
    kinds = pd.DataFrame({"w": kw, "l": kl})
    status = pd.Series("full", index=df.index, dtype="object")
    blank = (kw == "blank") & (kl == "blank")
    zero = kinds.isin(["all_zero"]).any(axis=1) & ~blank
    one_side = kinds.isin(["blank"]).any(axis=1) & ~blank & ~zero
    partial = kinds.isin(["partial"]).any(axis=1) & ~blank & ~zero & ~one_side
    status[blank], status[zero], status[one_side], status[partial] = "blank", "all_zero", "one_side", "partial"
    ok = status.eq("full")
    no_sv = ok & kinds.isin(["no_svgms"]).any(axis=1)
    status[no_sv] = "no_svgms"
    note("C20", "box score blank for both players: missing", "flag_missing", df[blank])
    note("C21", "box score all zero for a player: missing, not zero", "flag_missing", df[zero])
    note("C22", "box score for one player only: missing for the match (return rates need both)", "flag_missing", df[one_side])
    note("C23", "box score with some counts blank (other than service games): missing", "flag_missing", df[partial])
    note("C24", "service games blank, the other eight counts present: kept, service-game rates missing",
         "flag_partial", df[no_sv])
    usable = status.isin(["full", "no_svgms"])
    # Capture negatives before the service-game plausibility branch can replace
    # an invalid negative with NaN and hide it from the whole-box check.
    negative_box = w.lt(0).any(axis=1) | l.lt(0).any(axis=1)
    # service games recorded as zero although serve points were played: blank, not zero
    zero_sv = usable & ((w["sv_gms"].fillna(-1) == 0) & (w["svpt"] > 0) | (l["sv_gms"].fillna(-1) == 0) & (l["svpt"] > 0))
    note("C25", "service games recorded as 0 with serve points played: service games treated as missing",
         "flag_partial", df[zero_sv])
    status[zero_sv] = "no_svgms"
    for f in (w, l):
        f.loc[status.eq("no_svgms"), "sv_gms"] = np.nan
    games = df["games_w"] + df["games_l"]
    std_tb = df["std_tb"]
    scored = df["status"].isin(["completed", "retired", "other"]) & df["score"].ne("") & ~df["status_detail"].eq("unknown")
    # B5 first: a service-games count that fits the score neither way is dropped on its own
    sv_total = w["sv_gms"] + l["sv_gms"]
    excl_tb = (sv_total - (games - std_tb)).abs() <= 1
    incl_tb = (sv_total - games).abs() <= 1
    b5 = (usable & scored & sv_total.notna() & ~excl_tb & ~incl_tb).fillna(False)
    df["sv_gms_incl_tb"] = pd.Series(np.where(usable & scored & (std_tb > 0) & incl_tb & ~excl_tb, True,
                                              np.where(usable & scored & (std_tb > 0) & excl_tb & ~incl_tb, False, pd.NA)),
                                     index=df.index, dtype="boolean")
    fails = {"B5": b5, "B0": negative_box}
    for f in (w, l):
        f.loc[b5, "sv_gms"] = np.nan
        checks = {
            "B0": f.lt(0).any(axis=1),
            "B1": f["first_in"] > f["svpt"],
            "B2": f["first_won"] > f["first_in"],
            "B3": f["second_won"] > f["svpt"] - f["first_in"],
            "B4": f["bp_saved"] > f["bp_faced"],
            "B6": f["df"] > f["svpt"] - f["first_in"],
            "B7": f["ace"] > f["first_won"] + f["second_won"],
            "B8": (f["bp_faced"] - f["bp_saved"]) > f["sv_gms"],
        }
        for k, v in checks.items():
            fails[k] = fails.get(k, pd.Series(False, index=df.index)) | v.fillna(False)
    pts = w["svpt"] + l["svpt"]
    played = (games - std_tb) - np.where(df["status"].eq("completed"), 0, 1)
    fails["B9"] = (scored & (pts < MIN_POINTS_PER_GAME * played)).fillna(False)
    failed = pd.Series(False, index=df.index)
    for cid, words, required, drops in BOX_CHECKS:
        hit = usable & fails[cid]
        if drops == "box":
            note(f"C3{cid[1]}", f"box score check{'' if required else ' (added)'}: {words}; box score dropped",
                 "drop_box", df[hit])
            failed |= hit
        else:
            note(f"C3{cid[1]}", f"box score check: {words}; service games dropped, the other counts kept",
                 "drop_svgms", df[hit])
    status[b5 & ~failed & status.eq("full")] = "no_svgms"
    status[failed] = "failed_check"
    has = status.isin(["full", "no_svgms"])
    for f in (w, l):
        f.loc[~has, :] = np.nan
    df["box_status"], df["has_box"] = status, has
    for b in C.BOX:
        df[f"w_{b}"], df[f"l_{b}"] = w[b], l[b]
    return df


NEXT_ROUND = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF",
              "QF": "SF", "SF": "F"}


def progression(rows: pd.DataFrame) -> pd.Series:
    """Who plays the next round of the same event: 'winner' (the recorded winner only), 'loser' (the
    recorded loser only), 'both' or 'neither'; '' where the event holds no next round (finals, round
    robins, the last qualifying round) and at team events, where a player's team can advance after a
    lost rubber. The Brief's rule is that the player who advanced won."""
    nxt = rows["round"].map(NEXT_ROUND)
    tour, tid, rnd, pid_w, pid_l = (column_items(rows[c]) for c in ("tour", "tid", "round", "pid_w", "pid_l"))
    nx = column_items(nxt)
    seen = set()
    for pid in (pid_w, pid_l):
        seen |= set(zip(tour, tid, rnd, pid))
    held = set(zip(tour, tid, rnd))
    check = nxt.notna() & rows["level"].ne("TEAM") & pd.Series(
        [(a, b, c) in held for a, b, c in zip(tour, tid, nx)], index=rows.index)
    w_on = pd.Series([(a, b, c, d) in seen for a, b, c, d in zip(tour, tid, nx, pid_w)], index=rows.index)
    l_on = pd.Series([(a, b, c, d) in seen for a, b, c, d in zip(tour, tid, nx, pid_l)], index=rows.index)
    out = np.select([w_on & ~l_on, l_on & ~w_on, w_on & l_on], ["winner", "loser", "both"], "neither")
    return pd.Series(np.where(check, out, ""), index=rows.index)


def swap_sides(rows: pd.DataFrame, mask: pd.Series) -> pd.DataFrame:
    """Exchange everything recorded for the winner with what is recorded for the loser, on ``mask``."""
    pairs = [(f"winner_{b}", f"loser_{b}") for b in BIO] + [(f"w_{c}", f"l_{c}") for c in C.BOX_SOURCE_NAMES.values()]
    pairs += [("wkey", "lkey"), ("pid_w", "pid_l")]
    for a, b in pairs:
        rows.loc[mask, [a, b]] = rows.loc[mask, [b, a]].to_numpy()
    return rows


# ------------------------------------------------------------------------------------------------
# The two tables

def player_columns(df: pd.DataFrame, me: str, opp: str) -> pd.DataFrame:
    """One player's row of stage0_match_players; me/opp are 'w' or 'l'."""
    side = {"w": "winner", "l": "loser"}
    p = pd.DataFrame(index=df.index)
    p["match_id"] = df["match_id"]
    p["player_id"], p["opponent_id"] = df[f"pid_{me}"], df[f"pid_{opp}"]
    p["won"] = me == "w"
    p["player_name"] = df[f"{side[me]}_name"]
    p["rank"] = num(df[f"{side[me]}_rank"]).where(lambda x: x > 0)
    p["rank_points"] = num(df[f"{side[me]}_rank_points"]).where(lambda x: x >= 0)
    p["seed"] = num(df[f"{side[me]}_seed"]).where(lambda x: x > 0)
    entry = text(df[f"{side[me]}_entry"]).str.upper().str.replace(r"\s+", "", regex=True)
    p["entry"] = entry.replace({"AL": "ALT", "A": "ALT", "": pd.NA})
    p["age"] = num(df[f"{side[me]}_age"]).where(lambda x: x > 0)
    p["height"] = num(df[f"{side[me]}_ht"]).where(lambda x: x >= 100)
    p["hand"] = text(df[f"{side[me]}_hand"]).str.upper().replace({"": pd.NA})
    p["country"] = text(df[f"{side[me]}_ioc"]).str.upper().replace({"": pd.NA})
    for b in C.BOX:
        p[b] = df[f"{me}_{b}"]
    p["has_box"] = df["has_box"]
    me_b = {b: df[f"{me}_{b}"] for b in C.BOX}
    op_b = {b: df[f"{opp}_{b}"] for b in C.BOX}
    spw = me_b["first_won"] + me_b["second_won"]
    rpw = op_b["svpt"] - op_b["first_won"] - op_b["second_won"]
    rates = {
        "spw": (spw, me_b["svpt"]), "rpw": (rpw, op_b["svpt"]), "tpw": (spw + rpw, me_b["svpt"] + op_b["svpt"]),
        "hold": (me_b["sv_gms"] - (me_b["bp_faced"] - me_b["bp_saved"]), me_b["sv_gms"]),
        "brk": (op_b["bp_faced"] - op_b["bp_saved"], op_b["sv_gms"]),
        "ace": (me_b["ace"], me_b["svpt"]), "df": (me_b["df"], me_b["svpt"]),
        "first_in": (me_b["first_in"], me_b["svpt"]), "first_won": (me_b["first_won"], me_b["first_in"]),
        "second_won": (me_b["second_won"], me_b["svpt"] - me_b["first_in"]),
        "bp_saved": (me_b["bp_saved"], me_b["bp_faced"]),
        "bp_conv": (op_b["bp_faced"] - op_b["bp_saved"], op_b["bp_faced"]),
        "bp_faced_pg": (me_b["bp_faced"], me_b["sv_gms"]),
    }
    trust = df["score_ok"]
    sets = {"w": df["sets_w"], "l": df["sets_l"]}
    games = {"w": df["games_w"], "l": df["games_l"]}
    tbs = {"w": df["tb_w"], "l": df["tb_l"]}
    rates["tb_won"] = (tbs[me], tbs["w"] + tbs["l"])
    rates["sets_won"] = (sets[me], sets["w"] + sets["l"])
    rates["games_won"] = (games[me], games["w"] + games["l"])
    for name, (n, d) in rates.items():
        n, d = n.astype("float64"), d.astype("float64")
        if name in ("tb_won", "sets_won", "games_won"):
            n, d = n.where(trust), d.where(trust)
        p[f"{name}_n"], p[f"{name}_d"] = n, d
    return p


def build(out_dir: Path | str | None = None, box_overrides: Path | str | None = DECIDED_OVERRIDES,
          confirm_live_overrides: bool = False, corrections: Path | str | None = DECIDED_CORRECTIONS,
          live_rows: Path | str | None = None) -> None:
    """Build Stage 0. With no arguments it writes the live tables in data/studies/predictability_diagnostic/ with
    the decided box-score overrides and corrections applied. ``out_dir`` writes all six outputs there instead;
    ``box_overrides=None`` builds without overrides and ``corrections=None`` without corrections; any other table
    (see apply_box_overrides, apply_row_corrections) goes into the live folder only with ``confirm_live_overrides``.
    ``live_rows`` adds upcoming matches (add_live_rows), only in a prediction run's sandbox or an ``out_dir``."""
    out = Path(out_dir) if out_dir is not None else C.OUT
    other = box_overrides is not None and Path(box_overrides).resolve() != DECIDED_OVERRIDES.resolve()
    other |= corrections is not None and Path(corrections).resolve() != DECIDED_CORRECTIONS.resolve()
    if other and out.resolve() == C.OUT.resolve() and not confirm_live_overrides:
        raise SystemExit("an override or correction table other than the decided one goes into the live Stage 0 "
                         "tables only with --confirm-live-overrides; use --out-dir for a dry run")
    if live_rows is not None and out.resolve() == C.OUT.resolve() and not SANDBOX_MARKER.exists():
        raise SystemExit("live rows (upcoming matches with placeholder results) go only into a prediction run's sandbox "
                         "(src/eda/prediction_run/) or an --out-dir, never into the repository's Stage 0")
    if box_overrides is not None and not Path(box_overrides).exists():
        raise SystemExit(f"box overrides: {box_overrides} is missing; rebuild it (src/eda/data_continuity/"
                         "slam_overrides.py) or build with --no-box-overrides")
    summary: dict = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                     "inputs": {}, "merge": {}, "cleaning": {}}
    raw = load_raw()
    if live_rows is not None:
        raw = add_live_rows(raw, pd.read_parquet(live_rows))
    log(f"loaded {len(raw):,} rows from {raw['group'].nunique()} file groups")
    summary["inputs"]["rows_by_source_group"] = S.records(
        raw.groupby(["source", "group"]).agg(files=("_source_file", "nunique"), rows=("rid", "size"),
                                             first_week=("tourney_date", "min"),
                                             last_week=("tourney_date", "max")).reset_index())
    summary["inputs"]["files"] = input_record()
    df = normalise(raw)
    if live_rows is not None:
        df = drop_replaced(df, summary)
        summary["live_rows"]["file"] = Path(live_rows).as_posix()
    if box_overrides is not None:
        rel_path = Path(box_overrides).resolve()
        rel_path = rel_path.relative_to(ROOT).as_posix() if rel_path.is_relative_to(ROOT) else rel_path.as_posix()
        df = apply_box_overrides(df, pd.read_csv(box_overrides, dtype=str, keep_default_na=False), rel_path, summary)
    if corrections is not None:
        df = apply_row_corrections(df, Path(corrections), summary)
        df = apply_date_corrections(df, Path(corrections), summary)
    events = event_corrections(corrections)
    df = parse_scores(df)
    df = rule_levels(df)
    snapshots = [df[["rid", "tour", "level", "qualifying", "season"]]]   # where each raw row sits, for the log

    # rows outside the window, and rows that cannot be placed in an event's order
    off = df["tdate"].isna() | (df["tdate"].dt.year < df["season"] - 1) | (df["tdate"].dt.year > df["season"])
    note("C01", "dated more than a season away from the file it sits in (TML's 2024 Challenger file holds Noumea "
         "matches of 2007-2008), or undated: dropped", "drop_row", df[off])
    early = ~off & (df["tdate"] < pd.Timestamp(f"{C.FIRST_YEAR - 1}-12-01"))
    note("C02", f"dated before December {C.FIRST_YEAR - 1}: dropped", "drop_row", df[early])
    unknown_round = ~off & ~early & ~df["round"].isin(list(C.ROUND_ORDER))
    note("C03", "round label missing or unknown: dropped (it cannot be ordered)", "drop_row", df[unknown_round])
    no_name = ~off & ~early & ~unknown_round & df["pair"].eq("")
    note("C04", "a player's name missing: dropped", "drop_row", df[no_name])
    df = df[~(off | early | unknown_round | no_name)].copy()

    # one date per TML event, as in Sackmann: the main draw's first date (TML dates some qualifying rows
    # the day before or days after the main draw, and in 2026 each match of a two-week event and each
    # Davis Cup rubber by its day). Rows more than 21 days away from it are left alone.
    tm = df["source"].eq("tml")
    main_day = df[tm & ~df["qualifying"]].groupby(["tour", "ekey"])["tdate"].min()
    any_day = df[tm].groupby(["tour", "ekey"])["tdate"].min()
    if "live_main_date" in df.columns and df["live_main_date"].notna().any():
        # a live qualifying row's event whose main draw is not played yet: the start the linker gives it (add_live_rows)
        hint = df[tm & df["live_main_date"].notna()].groupby(["tour", "ekey"])["live_main_date"].min()
        main_day = main_day.combine_first(hint)
    day = lookup(main_day.combine_first(any_day), df, ["tour", "ekey"])
    move = tm & day.notna() & df["tdate"].ne(day) & ((df["tdate"] - day).dt.days.abs() <= 21)
    note("C05", "TML row dated apart from its event's main draw (qualifying dated the day before or after it; "
         "matches of 2026 and Davis Cup rubbers dated by the day played): given the main draw's first date",
         "fill", df[move])
    df.loc[move, "tdate"] = day[move]

    sack = drop_repeats(df[df["source"] == "sackmann"].copy(), "sackmann")
    tml = drop_repeats(df[df["source"] == "tml"].copy(), "tml")
    log(f"after repeats: Sackmann {len(sack):,}, TML {len(tml):,}")

    tml, xw = link_tml(sack, tml, summary["merge"])
    tml["period"] = np.where(tml["tdate"] < SACKMANN_END, "before 2026-05-25", "2026-05-25 on")
    summary["merge"]["tml_rows_by_link"] = S.records(pd.crosstab([tml["tour"], tml["group"], tml["period"]],
                                                                 tml["link_status"]).reset_index())
    log("TML linked: " + ", ".join(f"{k} {v:,}" for k, v in tml["link_status"].value_counts().items()))

    # levels: rule level, each event's main-draw level, then Sackmann's ambiguous codes from TML's levels
    tml["level"] = event_levels(tml).fillna(tml["level"])
    lk = tml[tml["link_rid"].notna()].copy()
    lk["link_rid"] = lk["link_rid"].astype("int64")
    s_by_rid = sack.set_index("rid", drop=False)
    lk["stour"] = s_by_rid.loc[lk["link_rid"], "tour"].to_numpy()
    lk["stid"] = s_by_rid.loc[lk["link_rid"], "tid"].to_numpy()
    tml_level = mode_by(lk.rename(columns={"level": "tl"}), ["stour", "stid"], "tl")
    before = sack["level"].copy()
    sack["level"] = event_levels(sack).fillna(sack["level"])
    ev_refine = sack.groupby(["tour", "tid"])["refine"].any().rename_axis(["stour", "stid"])
    refine = lookup(ev_refine, sack.rename(columns={"tour": "stour", "tid": "stid"}), ["stour", "stid"]).fillna(False).astype(bool)
    from_tml = lookup(tml_level, sack.rename(columns={"tour": "stour", "tid": "stid"}), ["stour", "stid"])
    use = refine & from_tml.notna()
    sack.loc[use, "level"] = from_tml[use]
    note("L1", "Sackmann's level code does not separate 250 from 500 (ATP) or 500 from 1000 (WTA): the level "
         "TML gives the same matches is used", "relabel", sack[use & sack["level"].ne(before)])
    note("L2", "ambiguous Sackmann level code and no TML match in the event: the code's default kept "
         "(A, I and W -> 250, P -> 500, PM -> 1000)", "flag", sack[refine & from_tml.isna()])
    note("L3", "TML files a non-Masters event under M (Winston-Salem 2026): 250", "relabel",
         tml[tml["level_rule"].eq("12")])
    apply_event_corrections(sack, tml, events, "set_level", summary)      # one edition's level (22 Oct 2026)
    unlevelled = pd.concat([sack[sack["level"].isna()], tml[tml["level"].isna()]])
    note("L4", "no level rule matches: dropped", "drop_row", unlevelled)
    sack, tml = sack[sack["level"].notna()].copy(), tml[tml["level"].notna()].copy()
    lk = lk[lk["rid"].isin(tml["rid"]) & lk["link_rid"].isin(sack["rid"])]

    # indoor / outdoor for Sackmann events, and blank surfaces, from the TML rows of the same event
    ev_indoor = mode_by(lk.assign(ind=lk["indoor_flag"].astype("object")), ["stour", "stid"], "ind")
    ev_surface = mode_by(lk, ["stour", "stid"], "surface")
    skey = sack.rename(columns={"tour": "stour", "tid": "stid"})
    sack["indoor_flag"] = lookup(ev_indoor, skey, ["stour", "stid"])
    fill = lookup(ev_surface, skey, ["stour", "stid"])
    blank_surface = sack["surface"].isna()
    note("F1", "Sackmann surface blank: taken from the TML rows of the same event", "fill",
         sack[blank_surface & fill.notna()])
    sack.loc[blank_surface, "surface"] = fill[blank_surface]
    apply_event_corrections(sack, tml, events, "set_surface", summary)    # one edition's surface (22 Oct 2026)
    snapshots.append(pd.concat([sack, tml])[["rid", "tour", "level", "qualifying", "season"]])

    # TML-only rows: event id, date, season, name and level from Sackmann where it holds the event
    only = tml[tml["link_status"].eq("unlinked")].copy()
    ev = mode_by(lk, ["tour", "ekey"], "stid")
    only["stid"] = lookup(ev, only, ["tour", "ekey"])
    mapped = only["stid"].notna()
    # a TML id that names two events (Adelaide 1 and 2 in 2022) gets the event's date appended
    events_per_id = tml.assign(d=tml["tdate"].dt.strftime("%Y%m%d")).groupby(["tour", "tid"])[["ekey", "d"]] \
        .apply(lambda g: len(g.drop_duplicates()))
    shared = lookup(events_per_id, only, ["tour", "tid"]).gt(1) & ~mapped
    only.loc[shared, "tid"] = only.loc[shared, "tid"] + "-" + only.loc[shared, "tdate"].dt.strftime("%Y%m%d")
    sq = sack.groupby(["tour", "tid", "qualifying"])["tdate"].min()
    sany = sack.groupby(["tour", "tid"])["tdate"].min()
    only_s = only.assign(tid=only["stid"])
    sdate = lookup(sq, only_s, ["tour", "tid", "qualifying"]).fillna(lookup(sany, only_s, ["tour", "tid"]))
    sev = pd.DataFrame({"season": sack.groupby(["tour", "tid"])["season"].first(),
                        "name": sack.groupby(["tour", "tid"])["tourney_name"].first(),
                        "level": mode_by(sack, ["tour", "tid"], "level"),
                        "surface": mode_by(sack, ["tour", "tid"], "surface")})
    for col, target in (("season", "season"), ("name", "tourney_name"), ("level", "level")):
        v = lookup(sev[col], only_s, ["tour", "tid"])
        only.loc[mapped, target] = v[mapped]
    surf = lookup(sev["surface"], only_s, ["tour", "tid"])
    only.loc[mapped & only["surface"].isna(), "surface"] = surf[mapped & only["surface"].isna()]
    only.loc[mapped, "tdate"] = sdate[mapped]
    only.loc[mapped, "tid"] = only.loc[mapped, "stid"]
    # a TML-only event whose id Sackmann uses for an event of another date: kept apart
    other_date = lookup(sany, only, ["tour", "tid"])
    clash = ~mapped & other_date.notna() & ((only["tdate"] - other_date).dt.days.abs() > 7)
    only.loc[clash, "tid"] = "tml-" + only.loc[clash, "tid"]
    summary["merge"]["tml_only"] = {
        "rows": int(len(only)), "in_an_event_sackmann_also_holds": int(mapped.sum()),
        "tournament_id_clashes_renamed": int(clash.sum()), "tml_ids_naming_two_events_renamed": int(shared.sum()),
        "by_tour_period": S.records(only.groupby(["tour", "period"]).size().rename("rows").reset_index())}
    log(f"TML-only rows appended: {len(only):,} ({int(mapped.sum()):,} in events Sackmann also holds)")

    # canonical player ids
    sack["pid_w"], sack["pid_l"] = sack["tour"] + ":" + sack["winner_id"], sack["tour"] + ":" + sack["loser_id"]
    only["pid_w"], only["pid_l"] = resolve_ids(only, "winner", xw), resolve_ids(only, "loser", xw)
    allrows = pd.concat([sack, only], ignore_index=True)
    known = pd.concat([allrows[["tour", "wkey", "pid_w"]].set_axis(["tour", "key", "pid"], axis=1),
                       allrows[["tour", "lkey", "pid_l"]].set_axis(["tour", "key", "pid"], axis=1)])
    known = known[known["pid"].ne("") & ~known["pid"].str.endswith(":")]
    # A name shared by several canonical IDs cannot resolve a blank source ID.
    by_name = unambiguous_name_ids(known)
    blank_id = pd.Series(False, index=allrows.index)
    for pid, key in (("pid_w", "wkey"), ("pid_l", "lkey")):
        miss = allrows[pid].eq("") | allrows[pid].str.endswith(":")
        blank_id |= miss
        found = lookup(by_name, allrows.rename(columns={key: "key"}), ["tour", "key"])
        allrows.loc[miss, pid] = found[miss].fillna(allrows.loc[miss, "tour"] + ":name:" + allrows.loc[miss, key])
    note("C60", "player id blank in the source: the id the same name has elsewhere (else a name-based id)", "fill",
         allrows[blank_id])
    atpcode = allrows["pid_w"].str.startswith("atpcode:") | allrows["pid_l"].str.startswith("atpcode:")
    note("C61", "TML player without a Sackmann id (newer than Sackmann's files): ATP website code kept as the id",
         "flag", allrows[atpcode])
    same = allrows["pid_w"].eq(allrows["pid_l"])
    note("C62", "both players resolve to the same id: dropped", "drop_row", allrows[same])
    allrows = allrows[~same].copy()

    # match id; a match both sources list that the links missed is kept once, from Sackmann
    lo = np.where(allrows["pid_w"] < allrows["pid_l"], allrows["pid_w"], allrows["pid_l"])
    hi = np.where(allrows["pid_w"] < allrows["pid_l"], allrows["pid_l"], allrows["pid_w"])
    allrows["pid_lo"], allrows["pid_hi"] = lo, hi
    allrows["match_id"] = allrows["tour"] + "|" + allrows["tid"] + "|" + allrows["round"] + "|" + lo + "|" + hi
    allrows = allrows.sort_values(["match_id", "source", "rid"])   # 'sackmann' sorts before 'tml'
    dup = allrows.duplicated("match_id", keep="first")
    note("D4", "the same match id twice after the merge (a TML row of a match Sackmann holds that the links "
         "missed): the Sackmann row kept", "drop_row", allrows[dup])
    allrows = allrows[~dup].copy()
    # outside round robins a player plays once per round of an event: a TML-only row whose player already has a
    # Sackmann match in the same event and round repeats that match under a misidentified opponent
    # (TML's Wimbledon 2025 lists Karolina Muchova against 'Xin Tong Wang' as well)
    sk = allrows[allrows["source"].eq("sackmann") & allrows["round"].ne("RR")]
    s_tour, s_tid, s_rnd = (column_items(sk[c]) for c in ("tour", "tid", "round"))
    held = (set(zip(s_tour, s_tid, s_rnd, column_items(sk["pid_w"])))
            | set(zip(s_tour, s_tid, s_rnd, column_items(sk["pid_l"]))))
    tm = allrows["source"].eq("tml") & allrows["round"].ne("RR")
    clash = tm & pd.Series([(a, b, c, d) in held or (a, b, c, e) in held for a, b, c, d, e in
                            zip(*(column_items(allrows[c]) for c in ("tour", "tid", "round", "pid_w", "pid_l")))],
                           index=allrows.index)
    note("D6", "a TML-only match whose player already has a Sackmann match in the same event and round (a repeat "
         "with a misidentified opponent): dropped", "drop_row", allrows[clash])
    allrows = allrows[~clash].copy()
    snapshots.append(only[["rid", "tour", "level", "qualifying", "season"]])

    # the player who advanced won: a recorded loser who plays the next round, where the recorded winner
    # does not, won the match
    prog = progression(allrows)
    swapped = prog.eq("loser")
    note("D5", "the recorded loser plays the next round of the event and the recorded winner does not: winner and "
         "loser exchanged (the player who advanced won)", "relabel", allrows[swapped])
    allrows = swap_sides(allrows, swapped)
    summary["progression"] = S.records(pd.crosstab([allrows["tour"], allrows["level"]], prog).reset_index())

    # each event's format, then the counts read from the score
    allrows["year"] = allrows["season"].astype("int64")
    comp = allrows["status"].eq("completed")
    toks = allrows["score"].map(lambda s: tokens_of(s)[0])
    allrows["_short"] = toks.map(short_like)
    allrows["_bracket"] = toks.map(lambda t: any(br for *_, br in t))
    bo = num(allrows["best_of"])
    decider = comp & (toks.map(len) == bo)
    ev_key = ["tour", "tid"]
    short_share = allrows[comp].groupby(ev_key)["_short"].mean()
    mtb_share = allrows[decider].groupby(ev_key)["_bracket"].mean()
    allrows["short_event"] = lookup(short_share, allrows, ev_key).fillna(0).ge(0.5)
    allrows["mtb_event"] = lookup(mtb_share, allrows, ev_key).fillna(0).ge(0.5)
    allrows["mtb_rule"] = match_tiebreak_events(allrows, decider, ev_key)
    plain_bracket = allrows["score"].map(lambda s: "[" in str(s))
    allrows = score_columns(allrows)
    by_rule = allrows["mtb_rule"] & allrows["has_bracket"] & ~plain_bracket
    if by_rule.any():                              # the rows the event's rule alone bracketed
        from src.eda.feature_alpha_audit.repair_data import plain_match_tiebreak
        sub = allrows[by_rule]
        by_rule.loc[sub.index] = [plain_match_tiebreak(s, lv, st, sh) == s for s, lv, st, sh in
                                  zip(column_items(sub["score"]), column_items(sub["level"]),
                                      column_items(sub["status"]), column_items(sub["short_event"]))]
    allrows["format"] = np.select([allrows["short_event"] | (allrows["short_like"] & comp),
                                   allrows["mtb_event"] | allrows["has_bracket"]],
                                  ["short_sets", "match_tiebreak"], "standard")
    allrows["nonstandard_format"] = allrows["format"].ne("standard")
    note("C40", "played in short sets (first to 4 games; the Next Gen ATP Finals): flagged", "flag",
         allrows[allrows["format"].eq("short_sets")])
    note("C41", "a match tiebreak replaces the deciding set (the Laver Cup, some Davis Cup ties, some women's ITF "
         "events of 2019): flagged", "flag", allrows[allrows["format"].eq("match_tiebreak")])
    note("C42", "a 10-8, 11-9 or longer deciding score read as a match tiebreak by its main-tour event's rule (the "
         "event's other deciders are certainly match tiebreaks; 13 Oct 2026): counted as one, not as a set", "flag",
         allrows[by_rule])
    for d, rid, words in (("walkover", "C10", "walkover (no point played): kept, never evaluated"),
                          ("bye", "C11", "score says BYE for a two-player match: treated as a walkover"),
                          ("walkover_after_play", "C12", "walkover marker after games were played: treated as a retirement"),
                          ("retired", "C13", "retirement: kept, the player who advanced won, flagged"),
                          ("defaulted", "C14", "default (disqualification): status other, not evaluated"),
                          ("abandoned", "C15", "abandoned or unfinished: status other, not evaluated"),
                          ("unknown", "C16", "score blank or unreadable: status other, not evaluated")):
        note(rid, words, "flag", allrows[allrows["status_detail"].eq(d)])
    # a completed match whose score does not show the winner finishing it
    need = (bo // 2 + 1).fillna(2)
    normal = comp & (allrows["sets_w"] >= need)
    rev = comp & ~normal & (allrows["sets_l"] >= need) & (allrows["sets_l"] > allrows["sets_w"])
    unmarked = comp & ~normal & ~rev & ~allrows["last_done"]
    bestof = comp & ~normal & ~rev & allrows["last_done"] & (allrows["sets_w"] > allrows["sets_l"])
    odd = comp & ~(normal | rev | unmarked | bestof)
    for a, b in (("sets_w", "sets_l"), ("games_w", "games_l"), ("tb_w", "tb_l")):
        allrows.loc[rev, [a, b]] = allrows.loc[rev, [b, a]].to_numpy()
    allrows.loc[unmarked, "status"], allrows.loc[unmarked, "status_detail"] = "retired", "retired_unmarked"
    allrows["score_ok"] = (allrows["status"].isin(["completed", "retired", "other"])
                           & allrows["status_detail"].ne("unknown") & ~odd)
    allrows["score_flag"] = np.select([rev, unmarked, bestof, odd],
                                      ["read_reversed", "retirement_unmarked", "short_of_best_of", "inconsistent"], "")
    note("C17", "completed, but the score is written from the loser's side (read the other way it is a complete "
         "win for the recorded winner): read reversed", "relabel", allrows[rev])
    note("C18", "completed, but the last set is unfinished and the winner short of the sets needed (6-2 0-0): "
         "a retirement without its marker, treated as retired", "relabel", allrows[unmarked])
    note("C19", "completed, every set finished, the winner ahead but short of best-of (a best-of-3 rubber in a "
         "best-of-5 tie): kept, flagged", "flag", allrows[bestof])
    note("C1A", "completed, but the score fits neither player finishing the match: score-derived counts dropped",
         "drop_score", allrows[odd])

    allrows = box_scores(allrows)
    # Sackmann matches left without a box score whose TML record has serve points for both players (not used)
    tml_box = lk[(num(lk["w_svpt"]).fillna(0) > 0) & (num(lk["l_svpt"]).fillna(0) > 0)]["link_rid"]
    gap = allrows[allrows["source"].eq("sackmann") & ~allrows["has_box"] & allrows["rid"].isin(set(tml_box))]
    summary["merge"]["sackmann_without_box_where_tml_has_one"] = S.records(
        gap.assign(evaluated=gap["level"].isin(C.EVAL_LEVELS) & gap["year"].ge(C.EVAL_FROM))
        .groupby(["tour", "evaluated", "box_status"]).size().rename("matches").reset_index())
    minutes = num(allrows["minutes"])
    allrows["minutes_clean"] = minutes.where(minutes > 0)
    note("C50", "minutes blank or zero: missing", "flag_missing", allrows[allrows["minutes_clean"].isna()])

    # evaluation flag, sides, the order
    allrows["round_order"] = allrows["round"].map(C.ROUND_ORDER).astype("int64")
    allrows["evaluation"] = C.in_evaluation(allrows)
    low_a = allrows["match_id"].map(C.side_is_low)
    allrows["player_a_id"] = np.where(low_a, allrows["pid_lo"], allrows["pid_hi"])
    allrows["player_b_id"] = np.where(low_a, allrows["pid_hi"], allrows["pid_lo"])
    allrows["a_won"] = allrows["player_a_id"].eq(allrows["pid_w"])
    link_of = lk.drop_duplicates("link_rid").set_index("link_rid")["link_status"]
    m = pd.DataFrame({
        "match_id": allrows["match_id"], "tour": allrows["tour"], "year": allrows["year"],
        "era": C.era_of(allrows["year"]), "level": allrows["level"], "qualifying": allrows["qualifying"].astype(bool),
        "evaluation": allrows["evaluation"], "round": allrows["round"], "round_order": allrows["round_order"],
        "match_num": allrows["match_num"], "surface": allrows["surface"],
        "indoor": allrows["indoor_flag"].astype("boolean"), "best_of": num(allrows["best_of"]).astype("Int64"),
        "draw_size": num(allrows["draw_size"]).astype("Int64"), "tournament_id": allrows["tid"],
        "tournament_name": allrows["tourney_name"], "tournament_date": allrows["tdate"],
        "status": allrows["status"], "status_detail": allrows["status_detail"], "score": allrows["score"],
        "score_flag": allrows["score_flag"], "minutes": allrows["minutes_clean"], "format": allrows["format"],
        "nonstandard_format": allrows["nonstandard_format"], "has_box": allrows["has_box"],
        "box_status": allrows["box_status"], "sv_gms_incl_tb": allrows["sv_gms_incl_tb"],
        "player_a_id": allrows["player_a_id"],
        "player_b_id": allrows["player_b_id"], "a_won": allrows["a_won"], "source": allrows["source"],
        "tml_link": np.where(allrows["source"].eq("sackmann"), allrows["rid"].map(link_of).fillna("none"), "tml_only"),
        "source_file": allrows["_source_file"], "source_row": allrows["_row"]})
    m["map_level"] = C.map_level(m["level"], m["qualifying"])
    m = C.chrono_sort(m).reset_index(drop=True)
    m["order"] = np.arange(len(m), dtype="int64")

    mp = pd.concat([player_columns(allrows, "w", "l"), player_columns(allrows, "l", "w")], ignore_index=True)
    a_of = m.set_index("match_id")["player_a_id"]
    mp["side"] = np.where(mp["player_id"].eq(mp["match_id"].map(a_of)), "A", "B")
    mp = mp.merge(m[["match_id", "order"]], on="match_id").sort_values(["order", "side"]).drop(columns="order")
    first = ["match_id", "player_id", "opponent_id", "side", "won"]
    mp = mp[first + [c for c in mp.columns if c not in first]].reset_index(drop=True)

    # Apply the same deterministic corrections as the dated-history repair so
    # a future raw rebuild cannot silently restore split identities, bad boxes
    # or implausible workload. Match handles and A/B labels remain stable.
    from src.eda.feature_alpha_audit.repair_data import repair_tables
    m, mp, summary["data_repairs"] = repair_tables(m, mp)
    if corrections is not None:
        m, mp = apply_id_aliases(m, mp, Path(corrections), summary)

    out.mkdir(parents=True, exist_ok=True)
    m.to_parquet(out / C.MATCHES.name, index=False)
    mp.to_parquet(out / C.MATCH_PLAYERS.name, index=False)
    log(f"wrote {len(m):,} matches and {len(mp):,} player rows to {out}")

    where = pd.concat(snapshots).drop_duplicates("rid", keep="last").rename(columns={"season": "year"})
    where["kept"] = where["rid"].isin(allrows["rid"])
    write_cleaning_log(m, where, summary, out)
    write_level_applied(allrows, out)
    write_summary(m, mp, summary, out)
    log("done")


# ------------------------------------------------------------------------------------------------
# Evidence

def write_cleaning_log(m: pd.DataFrame, where: pd.DataFrame, summary: dict, out_dir: Path = C.OUT) -> None:
    """stage0_cleaning_log.csv: every rule with its count in each tour x level x qualifying x year cell.

    The share is of the cell's matches in the final table; for a rule that drops rows, the rows it
    dropped are added to that base."""
    hits = pd.concat(LOG, ignore_index=True).merge(where, on="rid", how="left")
    hits["level"] = hits["level"].fillna("(none)")
    hits["qualifying"] = hits["qualifying"].fillna(False).astype(bool)
    hits["year"] = hits["year"].astype("Int64")
    counts = (hits.groupby(["rule_id", "tour", "level", "qualifying", "year"], dropna=False).size()
              .rename("count").reset_index())
    base = m.groupby(["tour", "level", "qualifying", "year"]).size().rename("cell_matches").reset_index()
    base["year"] = base["year"].astype("Int64")
    out = counts.merge(base, on=["tour", "level", "qualifying", "year"], how="left")
    out["cell_matches"] = out["cell_matches"].fillna(0).astype(int)
    out["action"] = out["rule_id"].map({k: v["action"] for k, v in RULES.items()})
    out["rule"] = out["rule_id"].map({k: v["rule"] for k, v in RULES.items()})
    drops = out["action"].eq("drop_row")
    denom = out["cell_matches"] + np.where(drops, out["count"], 0)
    out["pct_of_cell"] = (100 * out["count"] / denom.where(denom > 0)).round(2)
    out["over_1pct"] = out["action"].isin(["drop_row", "drop_box", "drop_svgms", "drop_score"]) & (out["pct_of_cell"] > 1)
    out = out[["rule_id", "rule", "action", "tour", "level", "qualifying", "year", "count", "cell_matches",
               "pct_of_cell", "over_1pct"]].sort_values(["rule_id", "tour", "level", "qualifying", "year"])
    out.to_csv(out_dir / "stage0_cleaning_log.csv", index=False)
    totals = out.groupby(["rule_id"])["count"].sum()
    over_cells = out[out["over_1pct"]].groupby("rule_id").size()
    summary["cleaning"]["rules"] = [
        {"rule_id": rid, "rule": r["rule"], "action": r["action"], "count": int(totals.get(rid, 0)),
         "cells_over_1pct": int(over_cells.get(rid, 0))} for rid, r in sorted(RULES.items())]
    summary["cleaning"]["cells_over_1pct"] = S.records(out[out["over_1pct"]])
    log(f"cleaning log: {len(out):,} rows, {int(out['over_1pct'].sum()):,} cells over 1%")


def write_level_applied(allrows: pd.DataFrame, out_dir: Path = C.OUT) -> None:
    g = allrows.groupby(["source", "tour", "code", "level_rule", "level", "qualifying"], dropna=False).agg(
        matches=("rid", "size"), first_year=("year", "min"), last_year=("year", "max"),
        examples=("tourney_name", lambda s: "; ".join(s.value_counts().index[:4]))).reset_index()
    g.to_csv(out_dir / "stage0_level_applied.csv", index=False)


def write_summary(m: pd.DataFrame, mp: pd.DataFrame, summary: dict, out_dir: Path = C.OUT) -> None:
    """stage0_summary.json (everything stage0.md and the report quote) and stage0_cells.csv."""
    ev = m[m["evaluation"]]
    tour_of = m.set_index("match_id")["tour"]
    mpt = mp.assign(tour=mp["match_id"].map(tour_of))
    per_player = mpt.groupby(["tour", "player_id"]).size()
    pct = lambda s: round(100 * float(s.mean()), 1) if len(s) else None   # noqa: E731
    summary["tables"] = {
        "matches": int(len(m)), "player_rows": int(len(mp)),
        "matches_by_tour": m["tour"].value_counts().to_dict(),
        "matches_by_source": m["source"].value_counts().to_dict(),
        "matches_by_tml_link": m["tml_link"].value_counts().to_dict(),
        "players_by_tour": per_player.groupby(level=0).size().to_dict(),
        "matches_per_player_median_by_tour": per_player.groupby(level=0).median().to_dict(),
        "first_week": str(m["tournament_date"].min().date()), "last_week": str(m["tournament_date"].max().date()),
        "evaluation_matches": int(len(ev)), "evaluation_by_tour": ev["tour"].value_counts().to_dict(),
        "evaluation_headline_by_tour": ev[ev["year"].isin(list(C.HEADLINE_YEARS))]["tour"].value_counts().to_dict(),
        "evaluation_box_pct_by_tour": {t: pct(g["has_box"]) for t, g in ev.groupby("tour")},
        "evaluation_retired_pct_by_tour": {t: pct(g["status"].eq("retired")) for t, g in ev.groupby("tour")},
        "evaluation_nonstandard_by_tour": ev[ev["nonstandard_format"]].groupby(["tour", "level", "format"]).size()
        .rename("matches").reset_index().to_dict(orient="records"),
        "side_a_won_pct": pct(m["a_won"]),
        "evaluation_scope_left_out_by_status": S.records(
            m[m["level"].isin(C.EVAL_LEVELS) & m["year"].ge(C.EVAL_FROM) & ~m["evaluation"]]
            .groupby(["tour", "status", "status_detail"]).size().rename("matches").reset_index()),
        "status": S.records(m.groupby(["tour", "status", "status_detail"]).size().rename("matches").reset_index()),
        "format": S.records(m[m["nonstandard_format"]].groupby(["tour", "level", "format"]).size()
                            .rename("matches").reset_index()),
        "box_status": S.records(m.groupby(["tour", "box_status"]).size().rename("matches").reset_index()),
        "sources": S.records(m.assign(period=np.where(m["tournament_date"] < SACKMANN_END, "before 2026-05-25",
                                                      "2026-05-25 on"))
                             .groupby(["tour", "source", "period"]).size().rename("matches").reset_index()),
        "levels": S.records(m.groupby(["tour", "level", "qualifying"]).agg(
            matches=("match_id", "size"), evaluation=("evaluation", "sum"),
            box_pct=("has_box", lambda s: round(100 * s.mean(), 1)),
            first_year=("year", "min"), last_week=("tournament_date", "max")).reset_index()
            .assign(last_week=lambda f: f["last_week"].dt.strftime("%Y-%m-%d"))),
    }
    cell = m.groupby(["tour", "level", "qualifying", "year"]).agg(
        matches=("match_id", "size"), evaluation=("evaluation", "sum"), with_box=("has_box", "sum"),
        box_in_source=("box_status", lambda s: int((~s.isin(["blank", "all_zero", "one_side", "partial"])).sum())),
        retired=("status", lambda s: int(s.eq("retired").sum())),
        walkover=("status", lambda s: int(s.eq("walkover").sum())),
        a_won=("a_won", "sum"), from_tml=("source", lambda s: int(s.eq("tml").sum()))).reset_index()
    cell["box_pct"] = (100 * cell["with_box"] / cell["matches"]).round(1)
    cell["box_in_source_pct"] = (100 * cell["box_in_source"] / cell["matches"]).round(1)
    cell.to_csv(out_dir / "stage0_cells.csv", index=False)
    summary["coverage"] = S.records(cell[["tour", "level", "qualifying", "year", "matches", "evaluation", "with_box",
                                          "box_pct", "box_in_source_pct"]])
    # what the table lacks, measured
    evp = mpt[mpt["match_id"].isin(ev["match_id"])]
    after = m["tournament_date"] >= SACKMANN_END
    same_weeks_2025 = m["tournament_date"].between(SACKMANN_END - pd.Timedelta(days=364),
                                                   m["tournament_date"].max() - pd.Timedelta(days=364))
    holes = {
        "indoor_known_pct": {f"{t}|{lv}": pct(g["indoor"].notna()) for (t, lv), g in m.groupby(["tour", "level"])},
        "minutes_known_pct": {f"{t}|{lv}": pct(g["minutes"].notna()) for (t, lv), g in m.groupby(["tour", "level"])},
        "evaluation_rank_known_pct": {t: pct(g["rank"].notna()) for t, g in evp.groupby("tour")},
        "qualifying_since_2026_05_25": S.records(m[after].groupby(["tour", "level", "qualifying"]).size()
                                                 .rename("matches").reset_index()),
        "qualifying_same_weeks_2025": S.records(m[same_weeks_2025].groupby(["tour", "level", "qualifying"]).size()
                                                .rename("matches").reset_index()),
        "last_week_by_tour_level": S.records(m.groupby(["tour", "level", "qualifying"])["tournament_date"].max()
                                             .dt.strftime("%Y-%m-%d").rename("last_week").reset_index()),
        "sv_gms_incl_tb_events": S.records(m[m["sv_gms_incl_tb"].eq(True)].groupby(["tour", "level", "year"])
                                           ["tournament_name"].agg(lambda s: "; ".join(sorted(s.unique())))
                                           .rename("events").reset_index()),
        "box_without_service_games": S.records(m[m["box_status"].eq("no_svgms")].groupby(["tour", "year"]).size()
                                               .rename("matches").reset_index()),
    }
    summary["holes"] = holes
    (out_dir / "stage0_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default=None, help="write the six outputs here instead of the live folder")
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--box-overrides", default=str(DECIDED_OVERRIDES),
                       help="CSV of box-score overrides (default: the decided table; see apply_box_overrides)")
    which.add_argument("--no-box-overrides", action="store_true", help="build without any box-score overrides")
    ap.add_argument("--confirm-live-overrides", action="store_true",
                    help="allow an override or correction table other than the decided one into the live tables")
    fixes = ap.add_mutually_exclusive_group()
    fixes.add_argument("--corrections-dir", default=str(DECIDED_CORRECTIONS),
                       help="folder of row_corrections.csv and id_aliases.csv (default: the decided tables)")
    fixes.add_argument("--no-corrections", action="store_true", help="build without the audit's corrections")
    ap.add_argument("--live-rows", default=None,
                    help="parquet of upcoming matches as TML rows (a prediction run's sandbox or --out-dir only)")
    a = ap.parse_args()
    build(a.out_dir, None if a.no_box_overrides else a.box_overrides, a.confirm_live_overrides,
          None if a.no_corrections else a.corrections_dir, a.live_rows)
