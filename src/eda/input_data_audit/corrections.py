"""Corrections of named source rows that the input-data audit found corrupt, applied by the builders that read them.

Only rows that every reviewer confirmed corrupt, with one clear fix, are in the tables
(data/studies/input_data_audit/fixes/; how they were decided: docs/studies/input_data_audit/README.md, section 9, and
docs/decisions/2026-10-08-corrupt-data-fixes.md). Each table names its rows by source file and row, guarded by what the
source writes on that row, so a refreshed source that moves or rewrites a row stops the build instead of correcting
the wrong match.

    row_corrections.csv    raw match rows (stage0_build.py, right after the rows are read):
                           add_df_to_svpt  serve points that leave out double faults: svpt += df, both players
                           exchange_box    the winner's and the loser's nine counts exchanged
                           exchange_svgms  the winner's and the loser's service games exchanged, nothing else
                           blank_box       the nine counts of both players blanked (another match's statistics)
                           replace_box     the nine counts of both players taken from the official record given
                           replace_split   first serves in and points won on the first and second serve
                                           (1stIn, 1stWon, 2ndWon) taken from the official record, on each side
                                           whose three are given; that side's svpt, ace and df must equal the
                                           table's and its serve points won (1stWon + 2ndWon) may not change
                                           (proposed for the Roland-Garros first-serve recount, 9 Oct 2026:
                                           docs/studies/rg_first_serve_recount/; no decided table uses it)
                           set_svgms       both players' service games (SvGms) set to the table's, where the row
                                           still reads the table's serve points (w_svpt, l_svpt) and the service
                                           games it replaces (value: "<winner>/<loser>", blank for a missing count)
                                           (the Infosys Slams' service games, 9 Oct 2026: the same study; no decided
                                           table uses it)
                           set_age         one player's age (side winner or loser) set to the value given
                           mark_retired    a retirement written without its marker: " RET" appended to the score,
                                           where the row still reads the score given (value); a row that already
                                           reads it with the marker is left alone (since 22 Oct 2026, the source
                                           reconciliation's repairs: docs/decisions/2026-10-22-source-reconciliation-
                                           repairs.md)
    event_corrections.csv  one field of every row of a named event (stage0_build.py; since 22 Oct 2026, the same
                           decision): set_level after Stage 0's level rules and their refinement from Tennis My Life,
                           set_surface after its surface fill. Stage 0's level rules match an event by name and code,
                           not by year, so one edition's level or surface could not be corrected before. Named by source,
                           tour, tournament id (Stage 0's), name and season, guarded by the value it replaces; see
                           apply_event_corrections
    id_aliases.csv         Stage 0 player ids (stage0_build.py, after repair_tables): one person's second id mapped to
                           the established one, on every row of the second id
    odds_corrections.csv   tennis-data.co.uk rows (stage1_odds.py, right after the rows are read): exchange_prices
                           exchanges the winner's and the loser's price of each book named
    speed_exclusions.csv   serve-speed records (serve_speed_tabpfn/panel.py): not a candidate for their player-match,
                           which takes its next valid record
    date_corrections.csv   event dates of named matches (stage0_build.py, right after the row corrections; since
                           14 Oct 2026, docs/decisions/2026-10-14-p6-data-issues.md): set_tourney_date. Unlike the
                           tables above it names its match, not its row (by source file, tournament id, round and both
                           players, and the date it replaces), since Tennis My Life rewrites its files' row order; see
                           apply_date_corrections
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
FIXES = ROOT / "data" / "studies" / "input_data_audit" / "fixes"
ROW_CORRECTIONS = FIXES / "row_corrections.csv"
ID_ALIASES = FIXES / "id_aliases.csv"
ODDS_CORRECTIONS = FIXES / "odds_corrections.csv"
SPEED_EXCLUSIONS = FIXES / "speed_exclusions.csv"
DATE_CORRECTIONS = FIXES / "date_corrections.csv"
DATE_KEYS = ["source_file", "tourney_id", "round", "winner_name", "loser_name"]
EVENT_CORRECTIONS = FIXES / "event_corrections.csv"
EVENT_ACTIONS = {"set_level": "level", "set_surface": "surface"}    # action -> the Stage 0 field it sets
EVENT_KEYS = ["source", "tour", "tournament_id", "tourney_name", "year"]

COUNTS = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]   # Sackmann's names
BOX_ACTIONS = ("add_df_to_svpt", "exchange_box", "exchange_svgms", "blank_box", "replace_box", "replace_split",
               "set_svgms")
SPLIT_COUNTS = ["1stIn", "1stWon", "2ndWon"]
ROW_ACTIONS = BOX_ACTIONS + ("set_age", "mark_retired")
RETIRED_MARK = "RET"
ROW_GUARDS = ["tourney_id", "round", "winner_name", "loser_name"]
ODDS_GUARDS = ["td_winner", "td_loser", "td_date_text"]
SPEED_KEY = ["source", "source_key", "match_id", "side"]


def _text(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip()


def _row_key(files: pd.Series, rows: pd.Series) -> pd.Series:
    """'<source file>#<row>' with the row as a whole number."""
    return _text(files) + "#" + pd.to_numeric(rows, errors="coerce").astype("Int64").astype(str)


def _locate(frame_keys: pd.Series, want: pd.Series, what: str) -> np.ndarray:
    """Positions in frame_keys of each wanted key: every key must occur there exactly once."""
    counts = frame_keys.value_counts()
    bad = [k for k in want if counts.get(k, 0) != 1]
    if bad:
        raise SystemExit(f"{what}: {len(bad)} of {len(want)} rows do not name exactly one source row (first: {bad[:3]}); "
                         "rebuild the table from the current sources")
    pos = pd.Series(np.arange(len(frame_keys)), index=frame_keys.to_numpy())
    return pos.loc[want.to_numpy()].to_numpy()


def _guard(frame: pd.DataFrame, rows: pd.Index, table: pd.DataFrame, guards: list[str], what: str,
           width: int | None = None) -> None:
    for g in guards:
        have, want = _text(frame.loc[rows, g]), _text(table[g])
        if width:
            have, want = have.str[:width], want.str[:width]
        diff = have.to_numpy() != want.to_numpy()
        if diff.any():
            i = int(np.flatnonzero(diff)[0])
            raise SystemExit(f"{what}: row {table.index[i]} of the table expects {g} {want.iloc[i]!r}, the source has "
                             f"{have.iloc[i]!r}; rebuild the table from the current sources")


def _put(df: pd.DataFrame, at: pd.Index, col: str, values) -> None:
    """Write numbers into df.loc[at, col] in the column's own kind: as numbers into a numeric column, else as text
    the way the source files write them (whole numbers without a decimal point, blank for missing)."""
    v = pd.to_numeric(pd.Series(list(values), dtype="object"), errors="coerce").to_numpy(dtype="float64")
    if pd.api.types.is_numeric_dtype(df[col].dtype):
        df.loc[at, col] = v
    else:
        df.loc[at, col] = ["" if np.isnan(x) else format(x, ".10g") for x in v]


MOVED: list[str] = []          # the last call's corrections found by their match after the source moved their row


def _match_key(f: pd.DataFrame, file_col: str) -> pd.Series:
    """Source file and the four guards (tournament id, round, winner, loser), as the source writes them."""
    out = _text(f[file_col])
    for g in ROW_GUARDS:
        out = out + "|" + _text(f[g])
    return out


def _row_positions(df: pd.DataFrame, table: pd.DataFrame, rowkey: pd.Series) -> np.ndarray:
    """Positions in df of the table's distinct row keys. A correction's row is the one its source file and row name
    when that row's tournament id, round and names equal the guards, as before. Since 21 Oct 2026, when they do not
    (Tennis My Life rewrote the file's row order: its 2026 WTA file, 17-19 Oct), it is the one row of the file whose
    tournament id, round and both names equal the guards, as the date corrections have named their matches since
    14 Oct. No such row, or two, stops the build as before: a correction is never applied to another match."""
    global MOVED
    first = ~rowkey.duplicated().to_numpy()
    keys, t_first = rowkey[first].to_numpy(), table.loc[first]
    want = _match_key(t_first, "source_file").to_numpy()
    df_key = _row_key(df["_source_file"], df["_row"])
    df_match = _match_key(df, "_source_file")
    by_row = pd.Series(np.arange(len(df)), index=df_key.to_numpy())
    by_row = by_row[~by_row.index.duplicated(keep=False)]
    by_match = pd.Series(np.arange(len(df)), index=df_match.to_numpy())
    n_match = by_match.index.value_counts()
    by_match = by_match[~by_match.index.duplicated(keep=False)]
    match_text = df_match.to_numpy()
    out, moved = np.empty(len(keys), dtype=np.int64), []
    for i, (k, m) in enumerate(zip(keys, want)):
        p = by_row.get(k)
        if p is not None and match_text[p] == m:
            out[i] = p
        elif m in by_match.index:
            out[i] = int(by_match[m])
            moved.append(k)
        else:
            raise SystemExit(f"row corrections: {k} names no row whose tournament id, round and names equal its guards "
                             f"({int(n_match.get(m, 0))} rows of its file match them); rebuild the table from the "
                             "current sources")
    MOVED = moved
    if moved:
        print(f"row corrections: {len(moved)} rows found by their match, their source having moved them (first: "
              f"{moved[:3]})", flush=True)
    return out


def apply_row_corrections(df: pd.DataFrame, table: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, pd.Index]]:
    """Correct the named raw match rows (columns w_<count>, l_<count>, winner_age, loser_age, score, _source_file, _row
    and the guards). Every correction must find exactly one row by source file and row whose tournament id, round and
    names equal the guards, or, since 21 Oct 2026 when its source moved it, exactly one row of its file with those
    guards (_row_positions); else the build stops. A row takes at most one box correction, one age per side and one
    score correction. Returns the frame and, per action, the index of the rows it changed."""
    done: dict[str, pd.Index] = {a: df.index[:0] for a in ROW_ACTIONS}
    if table.empty:
        return df, done
    table = table.reset_index(drop=True)
    unknown = set(table["action"]) - set(ROW_ACTIONS)
    if unknown:
        raise SystemExit(f"row corrections: unknown actions {sorted(unknown)}")
    rowkey = _row_key(table["source_file"], table["source_row"])
    family = np.where(table["action"].eq("set_age"), "age:" + _text(table.get("side", pd.Series("", index=table.index))),
                      np.where(table["action"].eq("mark_retired"), "score", "box"))
    twice = pd.Series(rowkey + "|" + family).duplicated()
    if twice.any():
        raise SystemExit(f"row corrections: a row named twice for the same fields (first: {rowkey[twice].iloc[0]})")
    pos = _row_positions(df, table, rowkey)
    at_of = pd.Series(df.index[pos], index=rowkey.drop_duplicates().to_numpy())
    rows = pd.Index(at_of.loc[rowkey.to_numpy()].to_numpy())
    _guard(df, rows, table, ROW_GUARDS, "row corrections")
    for action in ROW_ACTIONS:
        sel = table["action"].eq(action).to_numpy()
        at = rows[sel]
        done[action] = at
        if at.empty:
            continue
        if action == "add_df_to_svpt":
            for side in ("w", "l"):
                svpt = pd.to_numeric(_text(df.loc[at, f"{side}_svpt"]).replace("", np.nan), errors="coerce")
                dfs = pd.to_numeric(_text(df.loc[at, f"{side}_df"]).replace("", np.nan), errors="coerce")
                if svpt.isna().any() or dfs.isna().any():
                    raise SystemExit("row corrections: add_df_to_svpt on a row without serve points or double faults")
                _put(df, at, f"{side}_svpt", svpt + dfs)
        elif action == "exchange_box":
            w = df.loc[at, [f"w_{c}" for c in COUNTS]].to_numpy(copy=True)
            l = df.loc[at, [f"l_{c}" for c in COUNTS]].to_numpy(copy=True)
            for i, c in enumerate(COUNTS):
                _put(df, at, f"w_{c}", l[:, i])
                _put(df, at, f"l_{c}", w[:, i])
        elif action == "exchange_svgms":
            w = df.loc[at, "w_SvGms"].to_numpy(copy=True)
            _put(df, at, "w_SvGms", df.loc[at, "l_SvGms"].to_numpy(copy=True))
            _put(df, at, "l_SvGms", w)
        elif action == "blank_box":
            for c in [f"{s}_{c}" for s in ("w", "l") for c in COUNTS]:
                _put(df, at, c, [np.nan] * len(at))
        elif action == "replace_box":
            cols = [f"{s}_{c}" for s in ("w", "l") for c in COUNTS]
            vals = table.loc[sel, cols].apply(pd.to_numeric, errors="coerce")
            if vals.isna().any().any():
                raise SystemExit("row corrections: replace_box needs all eighteen counts")
            for c in cols:
                _put(df, at, c, vals[c])
        elif action == "replace_split":
            _replace_split(df, at, table.loc[sel])
        elif action == "set_svgms":
            _set_svgms(df, at, table.loc[sel])
        elif action == "mark_retired":
            done[action] = _mark_retired(df, at, table.loc[sel])
        else:
            side = table.loc[sel, "side"].to_numpy()
            value = pd.to_numeric(table.loc[sel, "value"], errors="coerce").to_numpy()
            if np.isnan(value).any() or not set(side) <= {"winner", "loser"}:
                raise SystemExit("row corrections: set_age needs side winner or loser and a numeric value")
            for s in ("winner", "loser"):
                if (side == s).any():
                    _put(df, at[side == s], f"{s}_age", value[side == s])
    return df, done


def apply_date_corrections(df: pd.DataFrame, table: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Event dates of named matches (date_corrections.csv; since 14 Oct 2026, the P6 data issues' Tenerife repair:
    docs/decisions/2026-10-14-p6-data-issues.md). Unlike the row corrections, a date correction names its match, not its
    row: by source file, tournament id, round and both players, as the source writes them, and by the date it replaces
    (old_value, YYYYMMDD as the source writes it). Tennis My Life rewrites its files' row order (none of the 2024
    Challenger file's rows kept its position on 13 Oct 2026), and a row number would stop every build at its next
    revision. The matched row takes ``value`` in tourney_date and in the parsed tdate, before Stage 0's event dating
    (rule C05) reads them. A correction whose match no longer reads the old date (the source fixed it, or changed the
    match) does nothing and is reported (``not_found``, by the table's match_id); one that finds two rows stops the build.
    Returns the frame and a report: applied, not_found, rows (the frame index of the corrected rows)."""
    report = {"applied": 0, "not_found": [], "rows": df.index[:0]}
    if table.empty:
        return df, report
    unknown = set(table["action"]) - {"set_tourney_date"}
    if unknown:
        raise SystemExit(f"date corrections: unknown actions {sorted(unknown)}")

    def key(f: pd.DataFrame, names: list[str]) -> pd.Series:
        parts = [_text(f[c]).str.upper() if c == "round" else _text(f[c]) for c in names]
        out = parts[0]
        for p in parts[1:]:
            out = out + "|" + p
        return out

    have = pd.Series(key(df, ["_source_file", "tourney_id", "round", "winner_name", "loser_name"]).to_numpy() + "|"
                     + _text(df["tourney_date"]).to_numpy(), index=df.index)
    want = key(table, DATE_KEYS) + "|" + _text(table["old_value"])
    hits = have[have.isin(set(want))]
    twice = hits.duplicated(keep=False)
    if twice.any():
        raise SystemExit(f"date corrections: one correction finds two rows ({hits[twice].iloc[0]})")
    at = pd.Series(hits.index, index=hits.to_numpy())
    found = want.isin(set(hits))
    report["not_found"] = list(table.loc[~found.to_numpy(), "match_id"])
    rows = pd.Index(at.loc[want[found].to_numpy()].to_numpy())
    value = table.loc[found.to_numpy(), "value"].to_numpy()
    if len(rows):
        if pd.api.types.is_numeric_dtype(df["tourney_date"]):
            df.loc[rows, "tourney_date"] = [int(v) for v in value]
        else:
            df.loc[rows, "tourney_date"] = value
        df.loc[rows, "tdate"] = pd.to_datetime(pd.Series(value), format="%Y%m%d").to_numpy()
    report.update(applied=int(len(rows)), rows=rows)
    return df, report


def _replace_split(df: pd.DataFrame, at: pd.Index, rows: pd.DataFrame) -> None:
    """replace_split on the frame rows ``at`` (in the order of the table rows ``rows``): on each side whose three
    split counts are given, check that the source row still reads the table's svpt (and ace and df, where given) and
    that its serve points won equal the new split's, then write the three counts. Any mismatch stops the build."""
    def number(values) -> np.ndarray:
        return pd.to_numeric(_text(pd.Series(list(values), dtype="object")).replace("", np.nan),
                             errors="coerce").to_numpy(dtype="float64")

    def column(name: str) -> np.ndarray:            # a column the table does not have reads as blank
        return number(rows[name]) if name in rows else np.full(len(rows), np.nan)
    for s in ("w", "l"):
        new = {c: column(f"{s}_{c}") for c in SPLIT_COUNTS}
        given = np.vstack([~np.isnan(v) for v in new.values()])
        if (given.any(axis=0) & ~given.all(axis=0)).any():
            raise SystemExit("row corrections: replace_split needs a side's three split counts, or none of them")
        has = given.all(axis=0)
        if not has.any():
            continue
        where = at[has]
        new = {c: v[has] for c, v in new.items()}
        want = {c: column(f"{s}_{c}")[has] for c in ("svpt", "ace", "df")}
        cur = {c: number(df.loc[where, f"{s}_{c}"]) for c in ("svpt", "ace", "df", "1stWon", "2ndWon")}
        if np.isnan(want["svpt"]).any():
            raise SystemExit("row corrections: replace_split needs the side's serve points as a guard")
        for c in ("svpt", "ace", "df"):
            off = ~np.isnan(want[c]) & ~(cur[c] == want[c])
            if off.any():
                i = int(np.flatnonzero(off)[0])
                raise SystemExit(f"row corrections: replace_split expects {s}_{c} {want[c][i]:g} on {where[i]}, the "
                                 f"source has {cur[c][i]:g}; rebuild the table from the current sources")
        if not np.array_equal(cur["1stWon"] + cur["2ndWon"], new["1stWon"] + new["2ndWon"]):
            raise SystemExit("row corrections: replace_split would change a side's serve points won")
        fi, fw, sw, sv = new["1stIn"], new["1stWon"], new["2ndWon"], want["svpt"]
        if ((fw > fi) | (fi > sv) | (sw > sv - fi) | (np.minimum(np.minimum(fi, fw), sw) < 0)).any():
            raise SystemExit("row corrections: replace_split gives a split that does not fit the serve points")
        for c in SPLIT_COUNTS:
            _put(df, where, f"{s}_{c}", new[c])


def _set_svgms(df: pd.DataFrame, at: pd.Index, rows: pd.DataFrame) -> None:
    """set_svgms on the frame rows ``at`` (in the order of the table rows ``rows``): check that each source row still
    reads the table's serve points and the service games the table replaces, then write both players' new service
    games. Any mismatch stops the build."""
    def number(values) -> np.ndarray:
        return pd.to_numeric(_text(pd.Series(list(values), dtype="object")).replace("", np.nan),
                             errors="coerce").to_numpy(dtype="float64")

    def same(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        return (a == b) | (np.isnan(a) & np.isnan(b))

    def column(name: str) -> np.ndarray:            # a column the table does not have reads as blank
        return number(rows[name]) if name in rows else np.full(len(rows), np.nan)
    new = {s: column(f"{s}_SvGms") for s in ("w", "l")}
    if any(np.isnan(v).any() for v in new.values()):
        raise SystemExit("row corrections: set_svgms needs both players' service games")
    value = rows["value"] if "value" in rows else pd.Series("", index=rows.index)
    old = _text(value).str.split("/", expand=True).reindex(columns=[0, 1])
    if old.isna().any().any():
        raise SystemExit('row corrections: set_svgms needs the service games it replaces as value "<w>/<l>"')
    for i, s in enumerate(("w", "l")):
        for col, want in ((f"{s}_svpt", column(f"{s}_svpt")), (f"{s}_SvGms", number(old[i]))):
            if col.endswith("svpt") and np.isnan(want).any():
                raise SystemExit("row corrections: set_svgms needs both players' serve points as a guard")
            have = number(df.loc[at, col])
            off = ~same(have, want)
            if off.any():
                j = int(np.flatnonzero(off)[0])
                raise SystemExit(f"row corrections: set_svgms expects {col} {want[j]:g} on {at[j]}, the source has "
                                 f"{have[j]:g}; rebuild the table from the current sources")
    for s in ("w", "l"):
        _put(df, at, f"{s}_SvGms", new[s])


def _mark_retired(df: pd.DataFrame, at: pd.Index, rows: pd.DataFrame) -> pd.Index:
    """mark_retired on the frame rows ``at`` (in the order of the table rows ``rows``): a row that reads the table's
    score (value) takes " RET" after it; a row that already reads it with the marker (the source fixed it) is left
    alone; any other score stops the build. Returns the rows changed."""
    want = _text(rows["value"] if "value" in rows else pd.Series("", index=rows.index)).to_numpy()
    if (want == "").any():
        raise SystemExit("row corrections: mark_retired needs the score it marks as value")
    have = _text(df.loc[at, "score"]).str.split().str.join(" ").to_numpy()
    plain = have == want
    marked = have == np.char.add(want.astype(str), " " + RETIRED_MARK)
    if not (plain | marked).all():
        i = int(np.flatnonzero(~(plain | marked))[0])
        raise SystemExit(f"row corrections: mark_retired expects the score {want[i]!r} on {at[i]}, the source has "
                         f"{have[i]!r}; rebuild the table from the current sources")
    df.loc[at[plain], "score"] = [f"{w} {RETIRED_MARK}" for w in want[plain]]
    return at[plain]


def apply_event_corrections(df: pd.DataFrame, table: pd.DataFrame, action: str) -> tuple[pd.DataFrame, dict]:
    """One field of every row of each named event (event_corrections.csv; since 22 Oct 2026, the source
    reconciliation's repairs: docs/decisions/2026-10-22-source-reconciliation-repairs.md). ``action`` picks the table's
    rows applied in this call: set_level (Stage 0's ``level``, after its level rules and their refinement from Tennis
    My Life) or set_surface (``surface``, after its surface fill). An event is named by source, tour, Stage 0's
    tournament id (``tid``), the source's name and the season, as Stage 0 reads them; ``old_value`` is the value the
    correction replaces. An event whose rows all read old_value takes ``value``; one whose rows all read value already
    (a source or a rule now gives it) is left alone and reported; an event not found, or found with another name,
    season or value, stops the build: a correction is never applied to another event.
    Returns the frame and a report: applied and already (the events, as source|tour|tournament id) and rows (the
    frame index of the rows changed)."""
    report: dict = {"applied": [], "already": [], "rows": df.index[:0]}
    if action not in EVENT_ACTIONS:
        raise SystemExit(f"event corrections: unknown action {action!r}")
    if table.empty:
        return df, report
    unknown = set(table["action"]) - set(EVENT_ACTIONS)
    if unknown:
        raise SystemExit(f"event corrections: unknown actions {sorted(unknown)}")
    key = _text(table["source"]) + "|" + _text(table["tour"]) + "|" + _text(table["tournament_id"]) + "|" \
        + _text(table["action"])
    if key.duplicated().any():
        raise SystemExit(f"event corrections: an event named twice for one field ({key[key.duplicated()].iloc[0]})")
    field = EVENT_ACTIONS[action]
    changed = []
    for t in table[table["action"].eq(action)].itertuples():
        name = f"{t.source}|{t.tour}|{t.tournament_id}"
        hit = (df["source"].eq(t.source) & df["tour"].eq(t.tour) & df["tid"].eq(t.tournament_id)).to_numpy()
        if not hit.any():
            raise SystemExit(f"event corrections: {name} names no rows; rebuild the table from the current sources")
        names = set(_text(df.loc[hit, "tourney_name"]))
        seasons = set(pd.to_numeric(df.loc[hit, "season"], errors="coerce").astype("Int64").astype(str))
        if names != {str(t.tourney_name)} or seasons != {str(int(t.year))}:
            raise SystemExit(f"event corrections: {name} expects {t.tourney_name!r} of {t.year}, the rows read "
                             f"{sorted(names)} of {sorted(seasons)}; rebuild the table from the current sources")
        have = set(_text(df.loc[hit, field]))
        if have == {str(t.value)}:
            report["already"].append(name)
            continue
        if have != {str(t.old_value)}:
            raise SystemExit(f"event corrections: {name} expects its {field} {t.old_value!r}, its rows read "
                             f"{sorted(have)}; rebuild the table from the current sources")
        at = df.index[hit]
        df.loc[at, field] = t.value
        changed.append(at)
        report["applied"].append(name)
    if changed:
        report["rows"] = changed[0].append(changed[1:]) if len(changed) > 1 else changed[0]
    return df, report


def apply_id_aliases(m: pd.DataFrame, mp: pd.DataFrame, aliases: pd.DataFrame,
                     name_key) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Map each alias's second id to the established id on every player row, then re-derive opponent_id and the
    match's player_a_id / player_b_id from the paired rows (as repair_tables does). match_id and side stay as they
    are. Every row of a second id must carry the alias's name key, the established id must exist in the tour, and no
    match may end with one id on both sides, or the build stops."""
    if aliases.empty:
        return m, mp, []
    tour_of = m.set_index("match_id")["tour"]
    tours = mp["match_id"].map(tour_of)
    report = []
    for a in aliases.itertuples():
        hit = mp["player_id"].eq(a.from_id) & tours.eq(a.tour)
        if not hit.any():
            raise SystemExit(f"id aliases: {a.from_id} has no rows in the {a.tour} tables")
        if not (mp["player_id"].eq(a.to_id) & tours.eq(a.tour)).any():
            raise SystemExit(f"id aliases: the established id {a.to_id} has no rows in the {a.tour} tables")
        keys = set(mp.loc[hit, "player_name"].map(name_key))
        if keys != {a.name_key}:
            raise SystemExit(f"id aliases: {a.from_id}'s rows are named {sorted(keys)}, the table expects {a.name_key!r}")
        mp.loc[hit, "player_id"] = a.to_id
        report.append({"tour": a.tour, "from_id": a.from_id, "to_id": a.to_id, "rows": int(hit.sum())})
    pairs = mp.pivot(index="match_id", columns="side", values="player_id")
    same = pairs["A"].eq(pairs["B"])
    if same.any():
        raise SystemExit(f"id aliases: {int(same.sum())} matches would have one id on both sides "
                         f"(first: {pairs.index[same][:3].tolist()})")
    mp["opponent_id"] = np.where(mp["side"].eq("A"), mp["match_id"].map(pairs["B"]), mp["match_id"].map(pairs["A"]))
    m["player_a_id"], m["player_b_id"] = m["match_id"].map(pairs["A"]), m["match_id"].map(pairs["B"])
    return m, mp, report


def apply_odds_corrections(td: pd.DataFrame, table: pd.DataFrame, books: dict) -> tuple[pd.DataFrame, list[dict]]:
    """Exchange the winner's and the loser's price of each book named in `books` (e.g. "avg max") on the named
    tennis-data rows (td_file, td_row), guarded by the names and the date as published."""
    if table.empty:
        return td, []
    table = table.reset_index(drop=True)
    unknown = set(table["action"]) - {"exchange_prices"}
    if unknown:
        raise SystemExit(f"odds corrections: unknown actions {sorted(unknown)}")
    key = _text(table["td_file"]) + "#" + pd.to_numeric(table["td_row"]).astype(int).astype(str)
    if key.duplicated().any():
        raise SystemExit(f"odds corrections: a row named twice ({key[key.duplicated()].iloc[0]})")
    rows = td.index[_locate(_text(td["td_file"]) + "#" + td["td_row"].astype(str), key, "odds corrections")]
    _guard(td, rows, table, ODDS_GUARDS, "odds corrections", width=10)
    report = []
    for r, t in zip(rows, table.itertuples()):
        names = str(t.books).split()
        if not names or set(names) - set(books):
            raise SystemExit(f"odds corrections: unknown books {t.books!r}")
        for b in names:
            w, l = books[b]
            td.loc[r, [w, l]] = td.loc[r, [l, w]].to_numpy(copy=True)
        report.append({"td_file": t.td_file, "td_row": int(t.td_row), "books": t.books})
    return td, report


def speed_exclusions(rec: pd.DataFrame, table: pd.DataFrame) -> pd.Series:
    """True on the speed records the table names (source, source_key, match_id, side). Every named record must exist
    exactly once, or the build stops."""
    if table.empty:
        return pd.Series(False, index=rec.index)
    def key(f: pd.DataFrame) -> pd.Series:
        parts = [f[c].map(lambda x: "" if pd.isna(x) else str(x)) for c in SPEED_KEY]
        return parts[0].str.cat(parts[1:], sep="|")
    have, want = key(rec), key(table)
    _locate(have.reset_index(drop=True), want.reset_index(drop=True), "speed exclusions")
    return have.isin(set(want))
