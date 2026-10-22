"""Shared pieces of the ATP-official box readers (source reconciliation, part B, the ATP's own records; prefix atp_).

Everything here reads the frozen snapshot (common.SNAP), never the live Stage 0. Outputs go to
data/studies/source_reconciliation/box/ only.

What is here
    * Stage 0's men's matches (snapshot), with both players' names and each tournament's (season, ATP event id):
      Stage 0's tournament ids are "<year>-<ATP event id>" (Sackmann's convention; Tennis My Life's split events add
      "-<yyyymmdd>"), except Sackmann's combined men's-and-women's events of 2016-2020, filed as "<year>-M0nn". Those
      are mapped to the ATP's event ids by the table M_EVENTS (each checked against ManTennisData's tournament table:
      check_m_events()).
    * Name keys (as merge_feasibility/scan.py normalises: accents, case and punctuation out, words sorted) and the
      abbreviated keys "surname span + first initial".
    * The event linker: a source row (season, ATP event id, draw, round, the two players' ATP codes and names) is put
      on the Stage 0 match of the same event whose two players it matches, player by player, by Stage 0 id (through
      the ATP code crosswalk), full name, or abbreviated name, in that order of strength. Orientation comes from which
      Stage 0 side each source player matched, never from who won.
    * The contract writer (one row per match and player, the brief's columns) and the reader summary JSON.
    * Level groups, Stage 0's score parsed into set games, and a per-count equality with Stage 0 (a sanity check).
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402

BOX = C.OUT / "box"
READERS = BOX / "readers"
ATP_DUMP = C.DUMP / "points" / "infosys_atp"
CH_DUMP = C.DUMP / "points" / "infosys_challengers"
SIRG = C.DUMP / "points" / "sirgenkii_infotennis"
TDI = C.DUMP / "points" / "tdi"
MANTD = C.DUMP / "matches" / "mantennisdata"
DAILY_STAGING = C.STUDIES / "serve_speed_tabpfn" / "live" / "staging"
DAILY_RAW = C.RAW / "point_sources" / "infosys_atp_daily"
XW_PATH = BOX / "atp_crosswalk.parquet"

FAMILY = "atp_official"
COUNTS = list(C.COUNTS)
FIELDS = list(C.FIELDS)
CONTRACT = ["reader", "family", "kind", "source_key", "match_id", "player_id"] + FIELDS + ["complete", "link_method"]

# Sackmann's combined-event ids (men's and women's draws under one id), 2016-2020, and the ATP's own event ids
M_EVENTS = {20: 339, 1: 338, 4: 807, 6: 404, 7: 403, 21: 1536, 9: 416, 10: 440, 16: 741, 35: 418, 24: 422, 15: 747,
            14: 438, 56: 8998, 52: 6932}
M_NAMES = {339: "Brisbane", 338: "Sydney", 807: "Acapulco", 404: "Indian Wells", 403: "Miami", 1536: "Madrid",
           416: "Rome", 440: "Hertogenbosch", 741: "Eastbourne", 418: "Washington", 422: "Cincinnati", 747: "Beijing",
           438: "Moscow", 8998: "Adelaide", 6932: "Rio de Janeiro"}
EVENT_ID = re.compile(r"^(\d{4})-0*(\d+)(?:-\d{8})?$")
M_ID = re.compile(r"^(\d{4})-M0*(\d+)$")
SET_TOKEN = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")


def log(msg: str) -> None:
    print(msg, flush=True)


# ------------------------------------------------------------------------------------------------ names
def norm(name) -> str:
    """scan.py's normalisation, apostrophes dropped first: accents out, case folded, punctuation to spaces."""
    if name is None or (isinstance(name, float) and np.isnan(name)):
        return ""
    s = re.sub(r"['’`´]", "", str(name))
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


@lru_cache(maxsize=None)
def full_key(name) -> str:
    """Sorted normalised words of a full name ('' for fewer than two words)."""
    w = norm(name).split()
    return " ".join(sorted(w)) if len(w) >= 2 else ""


_INITIAL = re.compile(r"^[a-z]$")


@lru_cache(maxsize=None)
def abbr_keys(name) -> tuple:
    """'surname span + first initial' keys of a name, full ('Felix Auger Aliassime' -> 'aliassime f',
    'auger aliassime f') or abbreviated ('F. Auger-Aliassime', 'F. AUGER-ALIASSIME' -> 'auger aliassime f');
    two-word names also surname-first ('Zhang Zhizhen' -> 'zhang z' and 'zhizhen z')."""
    raw = str(name or "")
    toks = norm(raw.replace(".", ". ")).split()
    if len(toks) < 2:
        return ()
    if _INITIAL.match(toks[0]):                      # abbreviated: initials first
        i = 0
        while i < len(toks) and _INITIAL.match(toks[i]):
            i += 1
        rest = toks[i:]
        if not rest:
            return ()
        keys = {" ".join(rest) + " " + toks[0], rest[-1] + " " + toks[0]}
        return tuple(sorted(keys))
    ini = toks[0][0]
    keys = {" ".join(toks[i:]) + " " + ini for i in range(1, len(toks))}
    if len(toks) == 2:
        keys.add(toks[0] + " " + toks[1][0])
    return tuple(sorted(keys))


@lru_cache(maxsize=None)
def surname_keys(name) -> tuple:
    """Words of three letters or more (for the one-player anchor only)."""
    return tuple(sorted({w for w in norm(name).split() if len(w) >= 3}))


def atp_code(v) -> str:
    """An ATP player code, upper case, 'ATP' prefix dropped ('ATPD643' -> 'D643')."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    s = str(v).strip().upper()
    if len(s) > 4 and s.startswith("ATP"):
        s = s[3:]
    return s


# ------------------------------------------------------------------------------------------------ Stage 0
S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "tournament_id", "tournament_name",
           "tournament_date", "status", "status_detail", "score", "has_box", "box_status", "sv_gms_incl_tb",
           "player_a_id", "player_b_id", "a_won", "source"]


def event_of(tournament_id: str) -> tuple[int, int] | None:
    """(season, ATP event id) of a Stage 0 men's tournament id, or None (ITF, team events, unknown M ids)."""
    t = str(tournament_id or "")
    m = EVENT_ID.match(t)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = M_ID.match(t)
    if m and int(m.group(2)) in M_EVENTS:
        return int(m.group(1)), M_EVENTS[int(m.group(2))]
    return None


def level_group(level, qualifying) -> str:
    if bool(qualifying):
        return "qualifying"
    return {"GS": "slam", "T1000": "tour_main", "T500": "tour_main", "T250": "tour_main", "FIN": "tour_main",
            "CH": "challenger", "TEAM": "team", "ITF": "itf"}.get(str(level), "other")


@lru_cache(maxsize=1)
def s0_men(first_year: int = 2015) -> pd.DataFrame:
    """Stage 0's men's matches from first_year (snapshot), one row per match, with both sides' names, the event key,
    the level group and the set games of the score (winner first)."""
    m = pd.read_parquet(C.SNAP / "stage0_matches.parquet", columns=S0_COLS,
                        filters=[("tour", "==", "atp"), ("year", ">=", first_year)])
    p = pd.read_parquet(C.SNAP / "stage0_match_players.parquet", columns=["match_id", "side", "player_name"])
    p = p[p["match_id"].isin(set(m["match_id"]))]
    names = p.drop_duplicates(["match_id", "side"]).pivot(index="match_id", columns="side", values="player_name")
    m["name_a"] = m["match_id"].map(names["A"])
    m["name_b"] = m["match_id"].map(names["B"])
    ev = [event_of(t) for t in m["tournament_id"]]
    m["season"] = [e[0] if e else -1 for e in ev]
    m["ev"] = [e[1] if e else -1 for e in ev]
    m["level_group"] = [level_group(lv, q) for lv, q in zip(m["level"], m["qualifying"])]
    m["qual_level"] = np.where(m["qualifying"].astype(bool),
                               np.where(m["level"].eq("GS"), "GS", np.where(m["level"].eq("CH"), "CH", "tour")), "")
    m["sets_w"] = m["score"].map(score_sets)
    return m.reset_index(drop=True)


@lru_cache(maxsize=1)
def s0_players() -> pd.DataFrame:
    """Stage 0's men's player rows (snapshot) of the matches in s0_men(): ids, side, won and the nine counts."""
    ids = set(s0_men()["match_id"])
    p = pd.read_parquet(C.SNAP / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "won", "player_name"] + COUNTS)
    return p[p["match_id"].isin(ids)].reset_index(drop=True)


def score_sets(score) -> tuple:
    """Stage 0's score as ((winner games, loser games), ...), tiebreak points dropped; () when none."""
    out = []
    for tok in str(score or "").split():
        m = SET_TOKEN.match(tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return tuple(out)


def check_m_events() -> list[dict]:
    """M_EVENTS checked against ManTennisData's tournament table: each ATP id exists in the seasons Stage 0 files it,
    under a name containing the expected city."""
    t = pd.read_parquet(MANTD / "atp_tournaments.parquet", columns=["year", "code", "name", "start_dtm"])
    m = s0_men()
    rows = []
    for (y, tid, tname), _ in m[m["tournament_id"].str.match(r"^\d{4}-M\d+$")].groupby(
            ["year", "tournament_id", "tournament_name"]):
        e = event_of(tid)
        hit = t[(t["year"].astype(str) == str(y)) & (t["code"].astype(str) == str(e[1]))] if e else t.iloc[0:0]
        rows.append({"stage0_id": tid, "stage0_name": tname, "atp_event": e[1] if e else None,
                     "mantd_names": ";".join(hit["name"].astype(str)),
                     "expected_city": M_NAMES.get(e[1], "") if e else "",
                     "ok": bool(e) and len(hit) == 1 and norm(M_NAMES.get(e[1], "")).split()[0] in norm(
                         " ".join(hit["name"].astype(str)) + " " + tname)})
    return rows


# ------------------------------------------------------------------------------------------------ crosswalk
def crosswalk() -> pd.Series:
    """ATP code -> Stage 0 player id (box/atp_crosswalk.parquet, built by atp_crosswalk.py); empty if not built."""
    if not XW_PATH.exists():
        return pd.Series(dtype=object)
    x = pd.read_parquet(XW_PATH)
    return x.set_index("code")["pid"]


# ------------------------------------------------------------------------------------------------ the linker
STRENGTH = {"I": 3, "F": 2, "A": 1, "S": 0}


def player_keys(code: str, full: str, short: str = "", xw: pd.Series | None = None) -> dict:
    """{key: strength} of one source player: 'I:<Stage 0 id>' through the crosswalk, 'F:' full-name key,
    'A:' abbreviated keys (from the full and the short name), 'S:' surname words."""
    out = {}
    c = atp_code(code)
    if xw is not None and c and c in xw.index:
        out["I:" + str(xw[c])] = 3
    fk = full_key(full)
    if fk:
        out["F:" + fk] = 2
    for nm in (full, short):
        for k in abbr_keys(nm):
            out.setdefault("A:" + k, 1)
    for nm in (full, short):
        for k in surname_keys(nm):
            out.setdefault("S:" + k, 0)
    return out


def stage0_keys(pid: str, name: str) -> dict:
    out = {"I:" + str(pid): 3}
    fk = full_key(name)
    if fk:
        out["F:" + fk] = 2
    for k in abbr_keys(name):
        out.setdefault("A:" + k, 1)
    for k in surname_keys(name):
        out.setdefault("S:" + k, 0)
    return out


class EventLinker:
    """Stage 0's men's matches indexed by (season, ATP event id) and player key."""

    def __init__(self, s0: pd.DataFrame | None = None):
        self.s0 = s0_men() if s0 is None else s0
        self.index: dict = defaultdict(lambda: defaultdict(list))
        self.events = set()
        s = self.s0
        for i, (season, ev, pa, pb, na, nb) in enumerate(zip(s["season"], s["ev"], s["player_a_id"], s["player_b_id"],
                                                              s["name_a"], s["name_b"])):
            if ev < 0:
                continue
            idx = self.index[(int(season), int(ev))]
            self.events.add((int(season), int(ev)))
            for side, pid, nm in (("A", pa, na), ("B", pb, nb)):
                for k, st in stage0_keys(pid, nm).items():
                    idx[k].append((i, side, st))
        self.qual = s["qualifying"].astype(bool).to_numpy()
        self.round = s["round"].astype(str).to_numpy()

    def _hits(self, idx: dict, keys: dict) -> dict:
        """{(row, side): best strength} of one source player's keys in one event."""
        best = {}
        for k, st in keys.items():
            for i, side, st0 in idx.get(k, ()):
                s_ = min(st, st0)
                if best.get((i, side), -1) < s_:
                    best[(i, side)] = s_
        return best

    def link_one(self, season, ev, keys1: dict, keys2: dict, qual=None, rnd: str = "") -> tuple:
        """(row, side of player 1, method, n_candidates, reason) for one source row; row None when not linked."""
        try:
            key = (int(season), int(ev))
        except (TypeError, ValueError):
            return None, None, "", 0, "no_event_key"
        if key not in self.events:
            return None, None, "", 0, "event_not_in_stage0"
        idx = self.index[key]
        h1, h2 = self._hits(idx, keys1), self._hits(idx, keys2)
        cands = {}
        for (i, s1), st1 in h1.items():
            s2 = "B" if s1 == "A" else "A"
            st2 = h2.get((i, s2))
            if st2 is None:
                continue
            if qual is not None and not pd.isna(qual) and bool(qual) != bool(self.qual[i]):
                continue
            strength = (min(st1, st2), max(st1, st2))
            # a one-player anchor (the other matched only by a surname word) needs the matched one at name level
            if strength[0] == 0 and strength[1] < 2:
                continue
            old = cands.get(i)
            if old is None or strength > old[1]:
                cands[i] = (s1, strength)
        if not cands:
            return None, None, "", 0, "no_pair_in_event"
        top = max(v[1] for v in cands.values())
        best = [(i, v[0]) for i, v in cands.items() if v[1] == top]
        if len(best) > 1 and rnd:
            same = [(i, s) for i, s in best if self.round[i] == rnd]
            if same:
                best = same
        if len(best) > 1:
            return None, None, "", len(best), "ambiguous"
        i, s1 = best[0]
        names = {3: "id", 2: "full", 1: "abbr", 0: "anchor"}
        method = f"event+{names[top[0]]}/{names[top[1]]}"
        return i, s1, method, len(cands), ""

    def link(self, rows: pd.DataFrame, xw: pd.Series | None = None) -> pd.DataFrame:
        """rows: season, ev, qual (bool/NaN), round ('' if unknown), c1, c2 (ATP codes), f1, f2 (full names),
        s1, s2 (short names, optional). Returns, on rows' index: match_id, p1_side, link_method, n_cand,
        unlinked_reason. A Stage 0 match claimed by two source rows keeps the stronger link (equal: both dropped,
        'duplicate')."""
        out = []
        for r in rows.itertuples():
            k1 = player_keys(getattr(r, "c1", ""), getattr(r, "f1", ""), getattr(r, "s1", ""), xw)
            k2 = player_keys(getattr(r, "c2", ""), getattr(r, "f2", ""), getattr(r, "s2", ""), xw)
            i, side, method, n, why = self.link_one(r.season, r.ev, k1, k2, getattr(r, "qual", None),
                                                    str(getattr(r, "round", "") or ""))
            out.append((r.Index, i, side, method, n, why))
        res = pd.DataFrame(out, columns=["rid", "row", "p1_side", "link_method", "n_cand", "unlinked_reason"])
        res = res.set_index("rid")
        res["match_id"] = [self.s0.at[int(i), "match_id"] if pd.notna(i) else None for i in res["row"]]
        # one source row per Stage 0 match: the strongest link keeps it; a tie at the top drops them all
        res["rank"] = res["link_method"].map(_method_rank)
        dup = res["match_id"].notna() & res.duplicated("match_id", keep=False)
        drop = []
        for _, g in res[dup].groupby("match_id"):
            top = g["rank"].max()
            winners = g.index[g["rank"] == top]
            drop += list(g.index[g["rank"] < top])
            if len(winners) > 1:
                drop += list(winners)
        if drop:
            res.loc[drop, ["match_id", "p1_side", "link_method"]] = [None, None, ""]
            res.loc[drop, "unlinked_reason"] = "duplicate"
        return res.drop(columns=["row", "rank"])


def orient_in_match(linker: EventLinker, match_id: str, k1: dict, k2: dict) -> str | None:
    """Stage 0 side of source player 1 inside a match placed by another linker (a match-timing link file): the
    assignment under which both players match (id, full or abbreviated name), the stronger one; None when neither
    does or both do equally."""
    s = linker.s0
    if not hasattr(linker, "_row_of"):
        linker._row_of = pd.Series(s.index, index=s["match_id"])
    if match_id not in linker._row_of.index:
        return None
    r = s.loc[linker._row_of[match_id]]
    ka, kb = stage0_keys(r["player_a_id"], r["name_a"]), stage0_keys(r["player_b_id"], r["name_b"])

    def best(src, s0):
        return max([min(v, s0[k]) for k, v in src.items() if k in s0] or [-1])
    straight = min(best(k1, ka), best(k2, kb))
    crossed = min(best(k1, kb), best(k2, ka))
    if max(straight, crossed) < 1 or straight == crossed:
        return None
    return "A" if straight > crossed else "B"


def _method_rank(m: str) -> int:
    if not m:
        return -1
    a, b = m.split("+")[1].split("/")
    order = {"anchor": 0, "abbr": 1, "full": 2, "id": 3}
    return order[a] * 10 + order[b]


# ------------------------------------------------------------------------------------------------ contract
def to_contract(df: pd.DataFrame, reader: str, kind: str) -> pd.DataFrame:
    """The brief's columns, typed, plus every x_ column; one row per (match, player)."""
    out = pd.DataFrame(index=df.index)
    out["reader"] = reader
    out["family"] = FAMILY
    out["kind"] = kind
    for c in ("source_key", "match_id", "player_id", "link_method"):
        out[c] = df[c].astype("string") if c in df else pd.Series(pd.NA, index=df.index, dtype="string")
    for c in FIELDS:
        out[c] = pd.to_numeric(df[c], errors="coerce").astype("float64") if c in df else np.nan
    out["complete"] = df["complete"].astype(bool) if "complete" in df else False
    for c in df.columns:
        if c.startswith("x_"):
            out[c] = df[c]
    return out[CONTRACT + [c for c in out.columns if c.startswith("x_")]].reset_index(drop=True)


def write_reader(name: str, rows: pd.DataFrame, info: dict) -> None:
    """box/readers/<name>.parquet (per-match rows, git-ignored) and <name>.json (aggregates and ids only)."""
    READERS.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(READERS / f"{name}.parquet", index=False)
    info = dict(info)
    info["rows_written"] = int(len(rows))
    info["matches_written"] = int(rows["match_id"].nunique())
    info["sanity_vs_stage0"] = stage0_equality(rows)
    info["winner_vs_stage0"] = info.get("winner_vs_stage0")
    C.write_json(READERS / f"{name}.json", info)
    log(f"wrote {READERS / (name + '.parquet')}: {len(rows):,} rows, {rows['match_id'].nunique():,} matches")


def stage0_equality(rows: pd.DataFrame, by_complete: bool = True) -> dict:
    """Per count: rows where both the reader and Stage 0 hold a value, and the share equal (a sanity check of the
    reader, not the study's comparison)."""
    p = s0_players().set_index(["match_id", "player_id"])
    r = rows.dropna(subset=["match_id", "player_id"]).set_index(["match_id", "player_id"])
    r = r[~r.index.duplicated()]
    j = r.join(p[COUNTS], how="inner", rsuffix="_s0")
    out = {}
    subsets = {"all": j}
    if by_complete:
        subsets["complete"] = j[j["complete"].astype(bool)]
    for nm, sub in subsets.items():
        d = {}
        for c in COUNTS:
            both = sub[c].notna() & sub[c + "_s0"].notna()
            n = int(both.sum())
            d[c] = {"n": n, "equal": round(float((sub.loc[both, c] == sub.loc[both, c + "_s0"]).mean()), 4) if n else None}
        out[nm] = d
    return out


def winner_check(rows: pd.DataFrame, won_col: str = "x_won") -> dict:
    """The source's (or the recount's) winner against Stage 0's `won`, on rows that state one."""
    p = s0_players().set_index(["match_id", "player_id"])["won"]
    r = rows.dropna(subset=["match_id", "player_id"])
    r = r[r[won_col].notna()] if won_col in r else r.iloc[0:0]
    s0w = pd.Series([p.get((m, q)) for m, q in zip(r["match_id"], r["player_id"])], index=r.index)
    ok = s0w.notna()
    same = (r.loc[ok, won_col].astype(bool) == s0w[ok].astype(bool))
    return {"player_rows_with_a_winner": int(ok.sum()), "same_as_stage0": int(same.sum()),
            "share_not_equal": round(float(1 - same.mean()), 5) if len(same) else None,
            "match_ids_not_equal_examples": sorted(set(r.loc[ok, "match_id"][~same]))[:20]}


def coverage(rows: pd.DataFrame) -> pd.DataFrame:
    """Matches covered by a reader, by season and level group (Stage 0's), with the complete ones."""
    s = s0_men().set_index("match_id")
    m = rows.dropna(subset=["match_id"]).groupby("match_id")["complete"].all()
    f = pd.DataFrame({"match_id": m.index, "complete": m.to_numpy()})
    f["year"] = f["match_id"].map(s["year"])
    f["level_group"] = f["match_id"].map(s["level_group"])
    return f.groupby(["year", "level_group"]).agg(matches=("match_id", "size"),
                                                 complete=("complete", "sum")).reset_index()


def side_ids(match_id: pd.Series, p1_side: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Stage 0 player ids of source player 1 and player 2 from the linked match and player 1's side."""
    s = s0_men().set_index("match_id")
    a = match_id.map(s["player_a_id"])
    b = match_id.map(s["player_b_id"])
    p1 = pd.Series(np.where(p1_side.eq("A"), a, np.where(p1_side.eq("B"), b, None)), index=match_id.index)
    p2 = pd.Series(np.where(p1_side.eq("A"), b, np.where(p1_side.eq("B"), a, None)), index=match_id.index)
    return p1, p2


def long_rows(wide: pd.DataFrame, fields: list[str], extra: list[str] | None = None) -> pd.DataFrame:
    """Wide (one row per source match, columns <field>_1 and <field>_2 for players 1 and 2, plus match_id, p1_side)
    to the contract's long form (one row per match and player), with player_id from the linked side."""
    extra = extra or []
    p1, p2 = side_ids(wide["match_id"], wide["p1_side"].fillna(""))
    parts = []
    for no, pid in (("1", p1), ("2", p2)):
        d = {"source_key": wide["source_key"], "match_id": wide["match_id"], "player_id": pid,
             "x_player_no": int(no)}
        for f in fields:
            d[f] = wide.get(f"{f}_{no}", pd.Series(np.nan, index=wide.index))
        for e in extra:
            d[e] = wide[e]
        parts.append(pd.DataFrame(d))
    return pd.concat(parts, ignore_index=True)


def json_ready(v):
    return json.loads(json.dumps(v, default=C._jsonable))
