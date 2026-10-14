"""The reviewers' consensus on the audit's candidate fixes, and the correction tables it allows.

Six independent reviewers voted on data/studies/input_data_audit/fixes/candidates.md: A1-A3 on the box scores (F1-F6),
B1-B3 on identities, ages, odds and speed records (F7-F17). Each wrote fixes/<reviewer>/verdict.json and scope files
naming the rows it confirms. A fix is executed only where all three reviewers of its group confirm it, on the rows all
three name, with the same operation and the same values. Everything else stays as it is.

Writes data/studies/input_data_audit/fixes/:
    consensus.json         per candidate: the three votes, each reviewer's scope size, the agreed rows, what was left
    consensus_rows.csv     every agreed row with its candidate and operation
    row_corrections.csv    raw match rows for stage0_build.py (see corrections.py), with guards read from the raw rows
    id_aliases.csv         player ids for stage0_build.py
    odds_corrections.csv   tennis-data.co.uk rows for stage1_odds.py
    speed_exclusions.csv   serve-speed records for serve_speed_tabpfn/panel.py

Run: ./python.sh src/eda/input_data_audit/consensus.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.input_data_audit import common as C  # noqa: E402
from src.eda.input_data_audit import corrections as K  # noqa: E402

FIXES = K.FIXES
GROUPS = {"A": ["A1-rederive", "A2-skeptic", "A3-referee"], "B": ["B1-rederive", "B2-skeptic", "B3-referee"]}
YES = {"confirm", "confirm_narrowed"}
SIDE_COUNTS = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
               "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}


def verdicts(group: str) -> dict[str, dict]:
    return {r: json.loads((FIXES / r / "verdict.json").read_text(encoding="utf-8"))["candidates"] for r in GROUPS[group]}


def votes(v: dict[str, dict], cand: str) -> dict[str, str]:
    return {r: (c.get(cand) or {}).get("vote", "missing") for r, c in v.items()}


def scope(reviewer: str, name: str) -> pd.DataFrame:
    return pd.read_csv(FIXES / reviewer / name, dtype=str, keep_default_na=False)


def agreed(frames: dict[str, pd.DataFrame], key: list[str]) -> tuple[pd.DataFrame, dict]:
    """Rows (by key) that every reviewer's frame holds; per reviewer, its size and the rows it alone adds."""
    sets = {r: set(map(tuple, f[key].to_numpy())) for r, f in frames.items()}
    common = set.intersection(*sets.values())
    first = next(iter(frames.values()))
    rows = first[first[key].apply(tuple, axis=1).isin(common)].drop_duplicates(key)
    info = {r: {"rows": len(s), "outside_agreement": len(s - common)} for r, s in sets.items()}
    return rows.reset_index(drop=True), info


def same_values(frames: dict[str, pd.DataFrame], key: list[str], cols: dict[str, str], tol: float) -> pd.Series:
    """For the agreed keys: True where every reviewer gives the same value (within tol) in its own column."""
    vals = []
    for r, f in frames.items():
        v = f.set_index(key)[cols[r]].map(lambda x: pd.to_numeric(x, errors="coerce"))
        vals.append(v[~v.index.duplicated()].rename(r))
    t = pd.concat(vals, axis=1, join="inner")
    return (t.max(axis=1) - t.min(axis=1)).le(tol) & t.notna().all(axis=1)


# ------------------------------------------------------------------------------------------------
# Group B: identities, ages, odds, speed records

def b_candidates() -> tuple[dict, dict[str, pd.DataFrame]]:
    v = verdicts("B")
    report, out = {}, {}
    rb, r2, r3 = GROUPS["B"]

    # F7: aliases, by (second id, established id)
    f = {rb: scope(rb, "scope_F7.csv").rename(columns={"new_id": "from_id", "established_id": "to_id"}),
         r2: scope(r2, "scope_F7.csv").rename(columns={"player_id_new": "from_id", "established_id": "to_id"}),
         r3: scope(r3, "scope_F7.csv").rename(columns={"old_id": "from_id", "new_id": "to_id"})}
    rows, info = agreed(f, ["from_id", "to_id"])
    report["F7"] = {"votes": votes(v, "F7"), "per_reviewer": info, "agreed": len(rows)}
    out["F7"] = rows[["from_id", "to_id"]] if set(votes(v, "F7").values()) <= YES else rows.iloc[:0][["from_id", "to_id"]]

    # F8b (preferred to F8 by two reviewers, confirmed by all three): the age from the established birth date
    for cand, name, cols in (("F8b", "scope_F8.csv", {rb: "age_f8b", r2: "age_F8b", r3: "F8b_value"}),
                             ("F9", "scope_F9.csv", {rb: "age_new", r2: "age_F9", r3: "age_new_floor_1dp"})):
        f = {r: scope(r, name) for r in GROUPS["B"]}
        for r in f:
            f[r]["player_id"] = f[r]["player_id"].astype(str)
        key = ["match_id", "player_id"]
        rows, info = agreed(f, key)
        ok = same_values(f, key, cols, 1e-9)
        rows = rows[rows[key].apply(tuple, axis=1).isin(set(ok[ok].index))]
        rows = rows.assign(value=rows.set_index(key).index.map(
            lambda k: pd.to_numeric(f[r2].set_index(key).loc[k, cols[r2]])).to_numpy())
        unanimous = set(votes(v, cand).values()) <= YES
        report[cand] = {"votes": votes(v, cand), "per_reviewer": info, "agreed": int(len(rows)) if unanimous else 0,
                        "values_disagree": int((~ok).sum())}
        out[cand] = rows[key + ["source_file", "source_row", "value"]] if unanimous else rows.iloc[:0]

    # F11 and F12: odds rows and the books exchanged
    def books_b1(s: str) -> str:
        return " ".join(sorted(x.strip() for x in s.replace("+", ",").split(",") if x.strip()))
    for cand in ("F11", "F12"):
        f = {}
        a = scope(rb, f"scope_{cand}.csv")
        f[rb] = a.assign(books=a["exchange"].map(books_b1))
        b = scope(r2, f"scope_{cand}.csv")
        b_books = b["exchange"].map(lambda s: "avg b365 max ps" if s.startswith("every price") else books_b1(s))
        f[r2] = b.assign(books=b_books)
        c = scope(r3, f"scope_{cand}.csv")
        f[r3] = c.assign(books=c.apply(lambda x: " ".join(sorted(b for b in ("avg", "max", "ps", "b365")
                                                                  if x[f"exchange_{b}"] == "True")), axis=1))
        for r in f:
            f[r]["td_row"] = f[r]["td_row"].astype(int).astype(str)
        rows, info = agreed(f, ["match_id", "td_file", "td_row", "books"])
        unanimous = set(votes(v, cand).values()) <= YES
        report[cand] = {"votes": votes(v, cand), "per_reviewer": info, "agreed": int(len(rows)) if unanimous else 0}
        out[cand] = rows[["match_id", "td_file", "td_row", "books"]] if unanimous else rows.iloc[:0]
        if cand == "F11":
            # round 2 (F11x): the rows B1 confirmed beyond the agreed four, put to B2 and B3
            extra = f[rb][~f[rb]["match_id"].isin(rows["match_id"])][["match_id", "td_file", "td_row", "books"]]
            r2v = {r: pd.DataFrame(json.loads((FIXES / r / "round2.json").read_text(encoding="utf-8"))["F11x"])
                   for r in (r2, r3)}
            keep = extra.copy()
            for r, d in r2v.items():
                yes = d[d["vote"].eq("confirm")].assign(td_row=lambda x: x["td_row"].astype(int).astype(str),
                                                        books=lambda x: x["books"].map(books_b1))
                keep = keep.merge(yes[["match_id", "td_file", "td_row", "books"]], how="inner")
            report["F11x"] = {"proposed_by": rb, "rows": int(len(extra)),
                              "votes": {r: d.set_index("match_id")["vote"].to_dict() for r, d in r2v.items()},
                              "agreed": int(len(keep))}
            out["F11x"] = keep

    # F14 (F15 is inside it): speed records
    f = {r: scope(r, "scope_F14.csv") for r in GROUPS["B"]}
    rows, info = agreed(f, K.SPEED_KEY)
    f15 = {r: scope(r, "scope_F15.csv") for r in GROUPS["B"]}
    rows15, info15 = agreed(f15, K.SPEED_KEY)
    inside = set(map(tuple, rows15[K.SPEED_KEY].to_numpy())) <= set(map(tuple, rows[K.SPEED_KEY].to_numpy()))
    report["F14"] = {"votes": votes(v, "F14"), "per_reviewer": info, "agreed": len(rows)}
    report["F15"] = {"votes": votes(v, "F15"), "per_reviewer": info15, "agreed": len(rows15), "all_inside_F14": inside}
    out["F14"] = rows[K.SPEED_KEY + ["y_raw", "spd_max"]] if set(votes(v, "F14").values()) <= YES else rows.iloc[:0]
    for cand in ("F8", "F10", "F13", "F16", "F17", "already_handled"):
        report[cand] = {"votes": votes(v, cand)}
    return report, out


# ------------------------------------------------------------------------------------------------
# Group A: box scores

A_FILES = {  # candidate -> scope file per reviewer
    "F1": {"A1-rederive": "F1_scope.csv", "A2-skeptic": "f1_scope.csv", "A3-referee": "f1_scope.csv"},
    "F2": {"A1-rederive": "f2_scope.csv", "A2-skeptic": "f2_scope.csv", "A3-referee": "f2_scope.csv"},
    "F3a": {"A1-rederive": "F3a_scope.csv", "A2-skeptic": "f3a_scope.csv", "A3-referee": "f3a_scope.csv"},
    "F3b": {"A1-rederive": "F3b_scope.csv", "A2-skeptic": "f3b_scope.csv", "A3-referee": "f3b_scope.csv"},
    "F4": {"A1-rederive": "f4_scope.csv", "A2-skeptic": "f4_scope.csv", "A3-referee": "f4_scope.csv"},
}
RAW_KEY = ["source_file", "source_row"]


def a_scope(reviewer: str, cand: str) -> pd.DataFrame:
    f = scope(reviewer, A_FILES[cand][reviewer]).rename(columns={"_source_file": "source_file", "_row": "source_row"})
    f["source_row"] = pd.to_numeric(f["source_row"]).astype(int).astype(str)
    return f


def f3b_counts(reviewer: str, f: pd.DataFrame) -> pd.DataFrame:
    """Per player row of F3b: replace (with the nine counts) or blank, in one shape for every reviewer."""
    if reviewer == "A1-rederive":
        counts = {c: f[f"api_{c}"] for c in SIDE_COUNTS}
        replace = f["f3b_action"].str.startswith("replace")
    else:
        counts = {c: f[f"new_{c}"] for c in SIDE_COUNTS}
        replace = f["operation"].str.startswith("replace")
    out = pd.DataFrame({"match_id": f["match_id"], "player_id": f["player_id"], "player_name": f["player_name"],
                        "source_file": f["source_file"], "source_row": f["source_row"], "raw_side": f["raw_side"],
                        "replace": replace})
    for c, v in counts.items():
        out[c] = pd.to_numeric(v, errors="coerce").where(replace)
    return out


def a_candidates() -> tuple[dict, dict[str, pd.DataFrame]]:
    v = verdicts("A")
    report, out = {}, {}
    rev = GROUPS["A"]

    # F1: every player row of the agreed matches, the same corrected serve points from all three reviewers
    f = {r: a_scope(r, "F1") for r in rev}
    rows, info = agreed(f, ["match_id", "player_id"] + RAW_KEY)
    new = {"A1-rederive": "svpt_fixed", "A2-skeptic": "new_svpt", "A3-referee": "svpt_new"}
    ok = same_values(f, ["match_id", "player_id"], new, 1e-9)
    bad_matches = {k[0] for k in ok[~ok].index}
    unanimous = set(votes(v, "F1").values()) <= YES
    keep = rows[~rows["match_id"].isin(bad_matches)]
    both = keep.groupby("match_id")["player_id"].transform("size").eq(2)    # a raw row is corrected for both players
    report["F1"] = {"votes": votes(v, "F1"), "per_reviewer": info, "agreed_player_rows": int(both.sum()),
                    "agreed_matches": int(keep.loc[both, "match_id"].nunique()) if unanimous else 0,
                    "values_disagree_matches": len(bad_matches)}
    out["F1"] = keep.loc[both].drop_duplicates(RAW_KEY)[["match_id"] + RAW_KEY] if unanimous else keep.iloc[:0]

    # F2 and F4: whole matches, by raw row
    for cand in ("F2", "F4"):
        f = {r: a_scope(r, cand) for r in rev}
        rows, info = agreed({r: x.drop_duplicates(["match_id"] + RAW_KEY) for r, x in f.items()},
                            ["match_id"] + RAW_KEY)
        unanimous = set(votes(v, cand).values()) <= YES
        report[cand] = {"votes": votes(v, cand), "per_reviewer": info, "agreed_matches": int(len(rows)) if unanimous else 0}
        out[cand] = rows[["match_id"] + RAW_KEY] if unanimous else rows.iloc[:0][["match_id"] + RAW_KEY]

    # F3: replace from the WTA's statistics (F3b) where all three confirm it with the same counts, else blank (F3a)
    f3a = {r: a_scope(r, "F3a").drop_duplicates(["match_id"] + RAW_KEY) for r in rev}
    rows_a, info_a = agreed(f3a, ["match_id"] + RAW_KEY)
    f3b = {r: f3b_counts(r, a_scope(r, "F3b")) for r in rev}
    rows_b, info_b = agreed(f3b, ["match_id", "player_id"] + RAW_KEY)
    vals = {r: x.set_index(["match_id", "player_id"]) for r, x in f3b.items()}
    same = pd.Series(True, index=rows_b.set_index(["match_id", "player_id"]).index)
    for k in same.index:
        recs = [vals[r].loc[[k]].iloc[0] for r in rev]
        same[k] = (len({bool(x["replace"]) for x in recs}) == 1
                   and all(np.allclose([x[c] for x in recs], recs[0][c], equal_nan=True) for c in SIDE_COUNTS))
    agree_b = rows_b[rows_b.set_index(["match_id", "player_id"]).index.map(same).to_numpy()]
    full_b = agree_b.groupby("match_id")["player_id"].transform("size").eq(2)
    agree_b = agree_b[full_b]
    a_ok, b_ok = set(votes(v, "F3a").values()) <= YES, set(votes(v, "F3b").values()) <= YES
    b_matches = set(agree_b["match_id"]) if b_ok else set()
    report["F3"] = {"votes_F3a": votes(v, "F3a"), "votes_F3b": votes(v, "F3b"), "per_reviewer_F3a": info_a,
                    "per_reviewer_F3b": info_b, "agreed_F3a_matches": int(len(rows_a)) if a_ok else 0,
                    "agreed_F3b_matches": len(b_matches)}
    out["F3b"] = agree_b[agree_b["match_id"].isin(b_matches)] if b_ok else agree_b.iloc[:0]
    out["F3a"] = rows_a[~rows_a["match_id"].isin(b_matches)][["match_id"] + RAW_KEY] if a_ok else rows_a.iloc[:0]
    for cand in ("F5", "F6"):
        report[cand] = {"votes": votes(v, cand)}
    r2, o2 = a_round2()
    report.update(r2)
    out.update(o2)
    return report, out


ROUND2_ACTIONS = {"F1x": "add_df_to_svpt", "F1y": "add_df_to_svpt", "F2x": "exchange_box", "F2y": "exchange_svgms",
                  "F4x": "blank_box"}


def a_round2() -> tuple[dict, dict[str, pd.DataFrame]]:
    """Round 2: extra rows found in round 1 (fixes/round2_A_candidates.csv), put to all three box-score reviewers."""
    cands = pd.read_csv(FIXES / "round2_A_candidates.csv", dtype=str, keep_default_na=False)
    report, out = {}, {}
    missing = [r for r in GROUPS["A"] if not (FIXES / r / "round2.json").exists()]
    if missing:                       # a vote not yet cast is not a confirmation
        for cand in ROUND2_ACTIONS:
            report[cand] = {"pending": missing}
            out[cand] = cands.iloc[:0][["match_id"] + RAW_KEY]
        return report, out
    r2v = {r: json.loads((FIXES / r / "round2.json").read_text(encoding="utf-8")) for r in GROUPS["A"]}
    for cand, action in ROUND2_ACTIONS.items():
        rows = cands[cands["cand"].eq(cand)]
        yes = {r: {x["match_id"] for x in d.get(cand, []) if x.get("vote") == "confirm"} for r, d in r2v.items()}
        keep = rows[rows["match_id"].isin(set.intersection(*yes.values()))]
        report[cand] = {"proposed": int(len(rows)), "confirmed_by": {r: len(s & set(rows["match_id"]))
                                                                     for r, s in yes.items()},
                        "agreed": int(len(keep)), "action": action,
                        "left_out": sorted(set(rows["match_id"]) - set(keep["match_id"]))}
        out[cand] = keep[["match_id"] + RAW_KEY]
    return report, out


# ------------------------------------------------------------------------------------------------
# The correction tables

def raw_rows(keys: pd.DataFrame) -> pd.DataFrame:
    """The raw rows (as stage0_build normalises them) named by source_file and source_row."""
    from src.eda.predictability_diagnostic import stage0_build as B
    raw = B.normalise(B.load_raw())
    raw["source_row"] = pd.to_numeric(raw["_row"]).astype("Int64").astype(str)
    raw = raw.rename(columns={"_source_file": "source_file"})
    want = keys[RAW_KEY].drop_duplicates()
    got = raw.merge(want, on=RAW_KEY)
    if len(got) != len(want) or got.duplicated(RAW_KEY).any():
        raise SystemExit(f"raw rows: {len(want)} named, {len(got)} found")
    return got


def row_table(out: dict[str, pd.DataFrame]) -> pd.DataFrame:
    parts = [out["F1"].assign(fix="F1", action="add_df_to_svpt"),
             out["F2"].assign(fix="F2", action="exchange_box"),
             out["F3a"].assign(fix="F3", action="blank_box"),
             out["F4"].assign(fix="F4", action="blank_box")]
    parts += [out[c].assign(fix=c, action=a) for c, a in ROUND2_ACTIONS.items()]
    b = out["F3b"]
    for mid, g in b.groupby("match_id"):
        rec = {"match_id": mid, "source_file": g["source_file"].iloc[0], "source_row": g["source_row"].iloc[0],
               "fix": "F3", "action": "replace_box" if g["replace"].all() else "blank_box"}
        if g["replace"].all():
            for s in ("w", "l"):
                side = g[g["raw_side"].eq(s)].iloc[0]
                rec.update({f"{s}_{K.COUNTS[i]}": int(side[c]) for i, c in enumerate(SIDE_COUNTS)})
        parts.append(pd.DataFrame([rec]))
    for cand in ("F8b", "F9"):
        parts.append(out[cand].assign(fix=cand, action="set_age"))
    rows = pd.concat(parts, ignore_index=True)
    rows["source_row"] = rows["source_row"].astype(str)
    box = rows[~rows["action"].eq("set_age")]
    twice = box.duplicated(RAW_KEY, keep=False)
    if twice.any():          # one raw row with two different box fixes is not a clear fix: neither is applied
        print("raw rows named by two box fixes, both left out:", box.loc[twice, ["fix", "match_id"]].to_dict("records"))
        rows = rows.drop(index=box.index[twice])
    raw = raw_rows(rows)
    rows = rows.merge(raw[RAW_KEY + K.ROW_GUARDS], on=RAW_KEY, how="left")
    ages = rows["action"].eq("set_age")
    who = rows.loc[ages].merge(raw[RAW_KEY + ["winner_name", "loser_name"]], on=RAW_KEY, suffixes=("", "_raw"))
    side = np.where(who["player_key"].eq(who["winner_name"].map(C.name_key)), "winner",
                    np.where(who["player_key"].eq(who["loser_name"].map(C.name_key)), "loser", ""))
    if (side == "").any():
        raise SystemExit("set_age: a player is neither the raw row's winner nor its loser")
    rows.loc[ages, "side"] = side
    cols = (["fix", "action", "match_id"] + RAW_KEY + K.ROW_GUARDS + ["side", "value"]
            + [f"{s}_{c}" for s in ("w", "l") for c in K.COUNTS])
    return rows.reindex(columns=cols).sort_values(["fix", "source_file", "source_row"]).reset_index(drop=True)


def odds_table(out: dict[str, pd.DataFrame]) -> pd.DataFrame:
    t = pd.concat([out["F11"].assign(fix="F11"), out["F11x"].assign(fix="F11"), out["F12"].assign(fix="F12")],
                  ignore_index=True)
    names = []
    for r in t.itertuples():
        raw = pd.read_parquet(ROOT / r.td_file, columns=["Winner", "Loser", "Date"]).iloc[int(r.td_row)]
        names.append({"td_winner": str(raw["Winner"]).strip(), "td_loser": str(raw["Loser"]).strip(),
                      "td_date_text": str(raw["Date"])[:10]})
    t = pd.concat([t, pd.DataFrame(names)], axis=1).assign(action="exchange_prices")
    return t[["fix", "action", "match_id", "td_file", "td_row", "books"] + K.ODDS_GUARDS]


def main() -> int:
    report, out = b_candidates()
    ra, oa = a_candidates()
    report.update(ra)
    out.update(oa)
    for cand in ("F8b", "F9"):
        f = scope(GROUPS["B"][1], "scope_F8.csv" if cand == "F8b" else "scope_F9.csv")
        name = f.drop_duplicates(["match_id", "player_id"]).set_index(["match_id", "player_id"])["player_name"]
        out[cand] = out[cand].assign(player_key=[C.name_key(name.loc[k]) for k in
                                                 zip(out[cand]["match_id"], out[cand]["player_id"])])
        out[cand]["source_row"] = pd.to_numeric(out[cand]["source_row"]).astype(int).astype(str)
    rows = row_table(out)
    rows.to_csv(K.ROW_CORRECTIONS, index=False)
    to_tour = out["F7"]["to_id"].str.split(":").str[0]
    stage0 = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_match_players.parquet",
                             columns=["player_id", "player_name"])
    key_of = stage0.drop_duplicates("player_id").set_index("player_id")["player_name"].map(C.name_key)
    aliases = out["F7"].assign(tour=to_tour.to_numpy(), name_key=out["F7"]["from_id"].map(key_of).to_numpy())
    aliases[["tour", "from_id", "to_id", "name_key"]].to_csv(K.ID_ALIASES, index=False)
    odds_table(out).to_csv(K.ODDS_CORRECTIONS, index=False)
    out["F14"].assign(fix="F14").to_csv(K.SPEED_EXCLUSIONS, index=False)
    report["tables"] = {"row_corrections": rows.groupby(["fix", "action"]).size().rename("rows").reset_index()
                        .to_dict("records"),
                        "id_aliases": int(len(aliases)),
                        "odds_corrections": int(len(out["F11"]) + len(out["F11x"]) + len(out["F12"])),
                        "speed_exclusions": int(len(out["F14"]))}
    report["generated_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    (FIXES / "consensus.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    for k, r in report.items():
        print(k, r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
