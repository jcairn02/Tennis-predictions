"""Shared pieces of the third-party box readers (prefix tp_) of the source-reconciliation study.

The readers (tp_sofascore.py, tp_tennislive.py, tp_atp_scraped.py, tp_flashscore.py, tp_mcp.py, tp_itf_live.py) put
box scores compiled outside the tours on Stage 0's match and player ids, one row per (match, player), in the reader
contract of the study's brief (box/readers/<reader>.parquet). This module holds what they share:

* Stage 0 from the study's frozen snapshot (common.SNAP), never the live tables: one row per match with the two
  players' names, the winner-first set scores and the round numbers the identity linker needs (``s0_frame``);
* the identity linker of the match-timing study (srcc_common.link), run here on the snapshot, for sources without a
  link file (``link``);
* orientation by names (``orient``): a source's player 1 is Stage 0's A when the names say so, graded with
  srcc_common.name_grade; never by who won;
* the contract (``to_contract``), the per-count equality with Stage 0 as a sanity check of each reader (``sanity``),
  the coverage tables (``coverage``), and the receipts of every input read (``receipts``).

Nothing here writes outside data/studies/source_reconciliation/box/.
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.match_timing import srcc_common as K  # noqa: E402  (names, set scores, the identity linker)

BOX = C.OUT / "box"
READERS = BOX / "readers"
COUNTS = C.COUNTS
FIELDS = C.FIELDS
CONTRACT = ["reader", "family", "kind", "source_key", "match_id", "player_id"] + FIELDS + ["complete", "link_method"]

# Level groups for the coverage tables (Stage 0's map_level, which splits qualifying from the main draw). For women
# "challenger" is the WTA 125 level.
LEVEL_GROUP = {"GS": "slam", "GSQ": "slam_qual", "T1000": "tour_main", "T500": "tour_main", "T250": "tour_main",
               "FIN": "tour_main", "TQ": "tour_qual", "CH": "challenger", "CHQ": "challenger_qual", "ITF": "itf",
               "ITFQ": "itf_qual", "TEAM": "team"}


def log(msg: str) -> None:
    K.log(msg)


# ------------------------------------------------------------------------------------------------ Stage 0
_S0: pd.DataFrame | None = None


def s0_frame() -> pd.DataFrame:
    """One row per Stage 0 match of the snapshot: ids, tour, year, levels, round (with the early rounds' number and
    the qualifying depth, as srcc_common.stage0 builds them), the two players' ids and names (side A, side B), the
    winner-first set scores, status and has_box. Read once per process."""
    global _S0
    if _S0 is not None:
        return _S0
    cols = ["match_id", "tour", "year", "level", "map_level", "qualifying", "round", "round_order", "tournament_id",
            "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won", "has_box",
            "box_status", "sv_gms_incl_tb", "source", "best_of"]
    m, p = C.stage0(cols, ["match_id", "side", "player_name"])
    for c in ("match_id", "tour", "level", "map_level", "round", "tournament_id", "tournament_name", "status", "score",
              "player_a_id", "player_b_id", "source", "box_status"):
        m[c] = m[c].astype(object)
    p = p.drop_duplicates(["match_id", "side"])
    for side in ("A", "B"):
        n = p[p["side"].eq(side)].set_index("match_id")["player_name"]
        m[f"name_{side.lower()}"] = m["match_id"].map(n).astype(object)
    m["tdate"] = pd.to_datetime(m["tournament_date"]).astype("datetime64[ns]")
    m["sets_w"] = m["score"].map(K.s0_sets)
    ev = ["tour", "tournament_date", "tournament_id"]
    early = m["round"].isin(K.EARLY_ROUNDS)
    first = m[early].groupby(ev)["round_order"].transform("min")
    m["round_no"] = np.nan
    m.loc[first.index, "round_no"] = (m.loc[first.index, "round_order"] - first + 1).astype("float64")
    qn = m["round"].astype(str).str.extract(r"^Q(\d)$")[0].astype("float64")
    m["qmax"] = qn.groupby([m[c] for c in ev]).transform("max")
    m["level_group"] = m["map_level"].map(LEVEL_GROUP).fillna("other")
    _S0 = m.reset_index(drop=True)
    return _S0


def s0_players() -> pd.DataFrame:
    """Stage 0's player rows (the nine counts, won, the player's name) of the snapshot."""
    _, p = C.stage0(["match_id"], ["match_id", "player_id", "side", "won", "player_name"] + COUNTS)
    return p


# ------------------------------------------------------------------------------------------------ names, linking
def grade(a, b) -> int:
    return K.name_grade(a, b)


def orient(n1, n2, na, nb) -> tuple[object, int, int]:
    """(a1, same, swap): a1 True when the source's player 1 is Stage 0's A (names graded 0-3 per side, summed: the
    direct pairing ``same`` against the crossed one ``swap``), False when player 1 is B, None when the names do not
    tell (equal grades, or the better pairing leaves a side ungraded)."""
    g11, g22 = grade(n1, na), grade(n2, nb)
    g12, g21 = grade(n1, nb), grade(n2, na)
    same, swap = g11 + g22, g12 + g21
    if same > swap and min(g11, g22) >= 1:
        return True, same, swap
    if swap > same and min(g12, g21) >= 1:
        return False, same, swap
    # one side unmatched (a changed surname), the other clear: the clear side decides when the crossed reading has
    # no support at all
    if same > swap and swap == 0 and max(g11, g22) >= 2:
        return True, same, swap
    if swap > same and same == 0 and max(g12, g21) >= 2:
        return False, same, swap
    return None, same, swap


def surname_first_to_initial_first(name) -> object:
    """Flashscore's 'Tomic B.' / 'Ramos-Vinolas A.' / 'Auger-Aliassime F.' as 'B. Tomic' (initials moved to the front),
    so that name_grade reads the initial as an initial. Names without trailing initials are returned as they are."""
    if not isinstance(name, str):
        return name
    toks = name.strip().split()
    tail = []
    while toks and len(toks[-1].rstrip(".")) <= 2 and toks[-1].endswith(".") and len(toks) > 1:
        tail.insert(0, toks.pop())
    if not tail:
        return name
    return " ".join(tail + toks)


def link(src: pd.DataFrame, by_season: bool = True) -> tuple[pd.DataFrame, pd.Series, dict]:
    """srcc_common.link on the snapshot's Stage 0, per tour and season (as lower_level_evidence/candidate_stage0.py
    link_rows does): ``src`` has sid, tour (atp/wta), day, p1, p2, sets (p1 first), rnd, qual, tid, id1, id2.
    Returns (links: sid, match_id, p1_side, pass, sc, rd, q1, q2; reason per sid; ambiguous {sid: [match ids]})."""
    S = s0_frame()
    links, reasons, amb = [], [], {}
    src = src.copy()
    src["season"] = pd.to_datetime(src["day"]).dt.year
    groups = src.groupby(["tour", "season"], sort=True) if by_season else src.groupby(["tour"], sort=True)
    for key, g in groups:
        tour = key[0] if isinstance(key, tuple) else key
        day = pd.to_datetime(g["day"])
        lo, hi = day.min() - pd.Timedelta(days=30), day.max() + pd.Timedelta(days=30)
        sl = S[(S["tour"] == tour) & (S["tdate"] >= lo) & (S["tdate"] <= hi)]
        res = K.link(g.drop(columns=["season"]).reset_index(drop=True), sl)
        links.append(res["links"])
        reasons.append(res["reason"])
        amb.update(res["ambiguous"])
        log(f"  linked {key}: {len(g):,} rows -> {len(res['links']):,} ({len(sl):,} Stage 0 matches in the window)")
    lk = pd.concat(links, ignore_index=True) if links else pd.DataFrame(columns=K.LINK_COLS)
    reason = pd.concat(reasons) if reasons else pd.Series(dtype=object)
    return lk, reason, amb


# ------------------------------------------------------------------------------------------------ the contract
def to_contract(w: pd.DataFrame, reader: str, family: str, kind: str, player_extra: list[str] | None = None,
                match_extra: list[str] | None = None) -> pd.DataFrame:
    """Wide rows (one per linked source record: source_key, match_id, a1 = the source's player 1 is Stage 0's A,
    p1_<field> / p2_<field> for the counts and ``player_extra``, complete, link_method, ``match_extra``) to the
    contract's long rows (one per match and player, the player's own serve counts)."""
    S = s0_frame().set_index("match_id")
    player_extra = player_extra or []
    match_extra = match_extra or []
    w = w[w["match_id"].notna() & w["a1"].notna()].copy()
    a1 = w["a1"].astype(bool).to_numpy()
    out = []
    for side in ("A", "B"):
        own = np.where(a1, "p1", "p2") if side == "A" else np.where(a1, "p2", "p1")
        rows = {"reader": reader, "family": family, "kind": kind, "source_key": w["source_key"].astype(str).to_numpy(),
                "match_id": w["match_id"].astype(str).to_numpy(),
                "player_id": S.loc[w["match_id"], f"player_{side.lower()}_id"].astype(str).to_numpy()}
        for f in FIELDS + player_extra:
            v1 = w[f"p1_{f}"].to_numpy() if f"p1_{f}" in w else np.full(len(w), np.nan)
            v2 = w[f"p2_{f}"].to_numpy() if f"p2_{f}" in w else np.full(len(w), np.nan)
            rows[f if f in FIELDS else f] = np.where(own == "p1", v1, v2)
        rows["complete"] = w["complete"].astype(bool).to_numpy()
        rows["link_method"] = w["link_method"].astype(str).to_numpy()
        rows["x_side"] = side
        for f in match_extra:
            rows[f] = w[f].to_numpy()
        out.append(pd.DataFrame(rows))
    df = pd.concat(out, ignore_index=True)
    for f in FIELDS:
        df[f] = pd.to_numeric(df[f], errors="coerce").astype("float64")
    cols = CONTRACT + [c for c in df.columns if c not in CONTRACT]
    return df[cols].sort_values(["match_id", "x_side"]).reset_index(drop=True)


def check_contract(df: pd.DataFrame) -> dict:
    """Structural checks: two rows per match, distinct players, Stage 0's ids, no duplicate (match, player)."""
    S = s0_frame()
    pairs = set(zip(S["match_id"], S["player_a_id"])) | set(zip(S["match_id"], S["player_b_id"]))
    per = df.groupby("match_id").size()
    return {"rows": int(len(df)), "matches": int(df["match_id"].nunique()),
            "matches_with_two_rows": int((per == 2).sum()),
            "duplicate_match_player": int(df.duplicated(["match_id", "player_id"]).sum()),
            "player_not_in_stage0_match": int(sum((m, p) not in pairs for m, p in zip(df["match_id"], df["player_id"]))),
            "source_keys_on_two_matches": int(df.groupby("source_key")["match_id"].nunique().gt(1).sum())}


def write_reader(df: pd.DataFrame, reader: str, summary: dict) -> None:
    """Write the reader's rows and JSON. A hand check already recorded (tp_handcheck.py --record) is kept when every
    key it checked is still a match of the new rows (the verdict is about those raw documents); otherwise the new
    sample stays pending and the old check is kept as hand_check_previous."""
    READERS.mkdir(parents=True, exist_ok=True)
    path = READERS / f"{reader}.json"
    if path.exists():
        try:
            old = json.loads(path.read_text(encoding="utf-8")).get("hand_check", {})
        except (json.JSONDecodeError, OSError):
            old = {}
        if old.get("status") == "checked":
            if set(old.get("keys", [])) <= set(df["match_id"]):
                summary["hand_check"] = old
            else:
                summary["hand_check_previous"] = old
    df.to_parquet(READERS / f"{reader}.parquet", index=False)
    summary = {"reader": reader, "written_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "file": str((READERS / f"{reader}.parquet").relative_to(C.ROOT)).replace("\\", "/"),
               "snapshot_manifest_sha256": C.sha256(C.SNAP / "manifest.json"), **summary}
    C.write_json(path, summary)
    log(f"wrote {reader}: {len(df):,} rows, {df['match_id'].nunique():,} matches")


# ------------------------------------------------------------------------------------------------ checks
def sanity(df: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Per-count exact equality with Stage 0's counts on the same (match, player), where both have the count: a check
    of the reader, not the study's comparison. ``by`` columns may be tour, year, level_group."""
    S = s0_frame()[["match_id", "tour", "year", "level_group"]]
    P = s0_players()
    j = df.merge(P, on=["match_id", "player_id"], how="inner", suffixes=("", "_s0")).merge(S, on="match_id", how="left")
    left = j[[f"{f}_s0" for f in COUNTS]].set_axis(COUNTS, axis=1)
    left["sv_won"] = left["first_won"] + left["second_won"]
    right = j[FIELDS]
    for c in (by or []):
        left[c] = j[c]
    return C.agreement(left, right, by=by)


def winner_check(df: pd.DataFrame, col: str = "x_src_won") -> dict:
    """The source's own winner (or the recount's), oriented by names, against Stage 0's ``won``."""
    P = s0_players()[["match_id", "player_id", "won"]]
    j = df[["match_id", "player_id", col]].merge(P, on=["match_id", "player_id"], how="inner")
    j = j[j[col].notna()]
    agree = j[col].astype(bool).eq(j["won"].astype(bool))
    return {"player_rows_with_a_winner": int(len(j)), "agree": int(agree.sum()), "disagree": int((~agree).sum()),
            "disagree_share": round(float((~agree).mean()), 5) if len(j) else None,
            "disagree_examples": j.loc[~agree, "match_id"].drop_duplicates().head(10).tolist()}


def coverage(df: pd.DataFrame, reader: str) -> pd.DataFrame:
    """Stage 0 matches the reader covers (a row with at least one count), by tour, level group and season, with Stage
    0's matches in the cell and the share."""
    S = s0_frame()[["match_id", "tour", "year", "level_group", "has_box"]]
    has = df[df[FIELDS].notna().any(axis=1)]
    mids = set(has["match_id"])
    comp = set(df.loc[df["complete"].astype(bool), "match_id"])
    t = S.assign(covered=S["match_id"].isin(mids), complete=S["match_id"].isin(comp))
    g = t.groupby(["tour", "level_group", "year"]).agg(stage0_matches=("match_id", "size"),
                                                         stage0_with_box=("has_box", "sum"),
                                                         covered=("covered", "sum"), covered_complete=("complete", "sum"))
    g = g[g["covered"] > 0].reset_index()
    g.insert(0, "reader", reader)
    g["share_of_stage0"] = (g["covered"] / g["stage0_matches"]).round(4)
    return g


def receipts(paths: list[Path]) -> list[dict]:
    out = []
    for p in paths:
        p = Path(p)
        if not p.exists():
            out.append({"path": str(p.relative_to(C.ROOT)).replace("\\", "/"), "exists": False})
            continue
        st = p.stat()
        out.append({"path": str(p.relative_to(C.ROOT)).replace("\\", "/"), "bytes": st.st_size,
                    "modified": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
                    "sha256": C.sha256(p)})
    return out


def sample_keys(df: pd.DataFrame, n: int = 6, seed: int = 20261016, where: pd.Series | None = None) -> list[str]:
    """Random linked matches for the hand check (rule 8): match ids, seeded."""
    d = df if where is None else df[where]
    mids = sorted(d["match_id"].unique())
    rng = random.Random(seed)
    return rng.sample(mids, min(n, len(mids)))


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", default_handler=str))


def tidy_counts(series: pd.Series) -> dict:
    return {str(k): int(v) for k, v in series.items()}


def env_info() -> dict:
    return {"python": sys.version.split()[0], "pandas": pd.__version__, "cwd": os.getcwd()}
