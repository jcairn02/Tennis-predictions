"""Flashscore's match statistics from the Hugging Face handoff on Stage 0's ids (reader tp_flashscore_stats of the
source-reconciliation study; brief: docs/studies/source_reconciliation/subagent_briefs.md).

Inputs (read-only): data/raw/public_dump/atp_pipeline_handoff/flashscore_gql_stats/*.jsonl.gz (match pages with
statistics) and the year files of flashscore_full/ (flashscore_full_<years>_{atp,challenger}.jsonl.gz: ATP and
Challenger match pages, which carry the same statistics fields). The head-to-head crawl files of flashscore_full/
(the h2h passes, 12 GB) carry no statistics fields and are not read. Link: the study's frozen link file
_snapshot/links/flashscore.parquet (source_key = Flashscore match id -> Stage 0 match_id; built by
src/eda/match_timing/link_flashscore.py). Men only: every statistics-bearing file is ATP or Challenger.

What the pages hold: the JSON's per_file lists, per file, the records read and those with statistics from
2009-12-01 on (earlier records are skipped: the link starts there). A match in two files is read once, statistics
file first; x_dup_conflict marks a match whose two copies carry different statistics.

Mapping of a page's match totals (fields home_/away_<stat>, Flashscore's "Match" section):
    ace aces · df double_faults · first_in / first_won 1st_serve_points_won "72% (47/65)" (won / first serves in) ·
    second_won 2nd_serve_points_won "44% (16/36)" (won / second serves, double faults included) · sv_won / svpt
    service_points_won "62% (63/101)" · sv_gms service_games_won "80% (12/15)" (held / service games played; tiebreak
    games not counted: in the pages read, a player's service games plus the opponent's equal the games of the score
    without tiebreaks) · bp_saved / bp_faced break_points_saved "5/8".
    Kept beside them: x_second_den (should equal svpt - first_in), x_first_pct (1st_serve_percentage, a share only),
    x_games_won (total_games_won numerator, to check the statistics' side against the set scores).
Orientation: the page's own player names (home_player, away_player: "Tomic B.", read as "B. Tomic") graded against
Stage 0's A and B (tp_common.orient); never by who won. Checks per match: x_sets_agree (the page's set scores, so
oriented, equal Stage 0's score), x_games_agree (each side's total games won equal its games in the set scores: the
statistics belong to the side the names say).
Placeholder blocks: some pages (2010-2014 above all) carry every statistic as "0% (0/0)"; where both players' serve
points read 0/0 the block is no statistics at all: its counts are blanked (x_zero_block).
Impossible splits: a player with no second serve in 20 serve points or more, or more double faults than second
serves (observed: 3,111 linked player rows, 3,086 of them with no second serve; 976 from 2012 and 2,083 from 2013
pages, which file every serve point as a first serve): first_in, first_won and second_won are blanked
(x_split_blanked), the page's values kept in x_first_in_raw, x_first_won_raw, x_second_won_raw.
complete: the page's status is finished (3), the statistics carry all nine counts for both sides, the set scores
agree with Stage 0's, and the games won do not contradict the score (x_games_agree is not False: of 639
contradicting pages, 70 equal the score with the two sides' statistics exchanged; most others are 2012-2013 pages
whose games won fit neither side; Flashscore's games won leave tiebreak games out).
x_src_won: the winner the timing study's Flashscore records give (the head-to-head feed's winner mark; sets won would
name a retiring leader), in the page's home/away order, oriented by names.
Writes box/readers/tp_flashscore_stats.{parquet,json}.
Run: ./python.sh src/eda/source_reconciliation/tp_flashscore.py [--workers 4]
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import tp_common as T  # noqa: E402

READER, FAMILY = "tp_flashscore_stats", "flashscore"
STATS_DIR = C.HANDOFF / "flashscore_gql_stats"
FULL_DIR = C.HANDOFF / "flashscore_full"
FIRST_DATE = "20091201"
FIELDS = ["aces", "double_faults", "1st_serve_percentage", "1st_serve_points_won", "2nd_serve_points_won",
          "break_points_saved", "service_points_won", "service_games_won", "total_games_won", "total_points_won"]
META = ["match_id", "home_player", "away_player", "match_date", "round", "tournament_slug", "category", "set_scores",
        "home_sets", "away_sets", "status", "year"]
FRAC = re.compile(r"\(?\s*(\d+)\s*/\s*(\d+)\s*\)?")


def stat_files() -> list[Path]:
    files = sorted(STATS_DIR.glob("*.jsonl*"))
    files += sorted(p for p in FULL_DIR.glob("flashscore_full_*.jsonl*") if "_h2h_" not in p.name and "layer3" not in p.name)
    return files


def read_file(path: str) -> tuple[str, list[dict], dict]:
    """One file's records with statistics, from FIRST_DATE on."""
    p = Path(path)
    op = gzip.open if p.suffix == ".gz" else open
    out, n, n_stats, early, bad = [], 0, 0, 0, 0
    with op(p, "rt", encoding="utf-8", errors="replace") as f:
        for line_no, line in enumerate(f, 1):
            try:
                d = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                bad += 1
                continue
            n += 1
            if str(d.get("match_date") or "") < FIRST_DATE:
                early += 1
                continue
            if not d.get("home_service_points_won") and d.get("home_aces") in (None, ""):
                continue
            n_stats += 1
            r = {k: d.get(k) for k in META}
            for side in ("home", "away"):
                for f_ in FIELDS:
                    r[f"{side}_{f_}"] = d.get(f"{side}_{f_}")
            # the page's own "Match" section of stats_detail_json, for the reader's own check
            try:
                det = json.loads(d.get("stats_detail_json") or "[]")
            except (json.JSONDecodeError, TypeError):
                det = []
            sec, match = None, {}
            for e in det:
                if "SE" in e:
                    sec = e["SE"]
                elif "SG" in e and sec == "Match":
                    match[e["SG"]] = (e.get("SH"), e.get("SI"))
            r["detail_aces"] = match.get("Aces", (None, None))
            r["detail_svc"] = match.get("Service Points Won", (None, None))
            r["file"], r["line"] = p.name, line_no
            out.append(r)
    return p.name, out, {"records": n, "with_statistics_from_2009_12": n_stats, "before_2009_12": early,
                         "unreadable_lines": bad}


def frac(v) -> tuple[float, float]:
    m = FRAC.search(str(v or ""))
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


def num(v) -> float:
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return np.nan


def set_games(text) -> list[tuple[int, int]]:
    """'6-7 6-4 3-6' (home first) -> [(6, 7), (6, 4), (3, 6)]; tiebreak points, if written, dropped."""
    out = []
    for tok in str(text or "").split():
        m = re.match(r"^(\d+)(?:\(\d+\))?-(\d+)(?:\(\d+\))?$", tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--cache", default=None, help="a parquet path (scratch) to keep the parsed records between runs")
    args = ap.parse_args()
    t0 = time.time()
    files = stat_files()
    T.log(f"{len(files)} files")
    cache = Path(args.cache) if args.cache else None
    if cache and cache.exists() and cache.with_suffix(".json").exists():
        R = pd.read_parquet(cache)
        for c in ("detail_aces", "detail_svc"):
            R[c] = R[c].map(lambda v: tuple(v) if v is not None else (None, None))
        per_file = json.loads(cache.with_suffix(".json").read_text(encoding="utf-8"))
        T.log(f"read the parsed records from {cache}")
    else:
        recs, per_file = [], {}
        with ProcessPoolExecutor(args.workers) as ex:
            for name, rows, st in ex.map(read_file, [str(p) for p in files]):
                recs.extend(rows)
                per_file[name] = st
                T.log(f"  {name}: {st}")
        R = pd.DataFrame(recs)
        if cache:
            c2 = R.copy()
            for c in ("detail_aces", "detail_svc"):
                c2[c] = c2[c].map(lambda v: [None if x is None else str(x) for x in v])
            c2.to_parquet(cache, index=False)
            cache.with_suffix(".json").write_text(json.dumps(per_file), encoding="utf-8")
    rec_inputs = T.receipts(files)
    R["from_stats_folder"] = R["file"].str.startswith("gql_stats")
    R = R.sort_values(["match_id", "from_stats_folder"], ascending=[True, False], kind="mergesort")
    dup_ids = R["match_id"][R["match_id"].duplicated()].unique()
    # do the copies of a match in two files agree on the statistics?
    sig_cols = [f"{s}_{f}" for s in ("home", "away") for f in FIELDS if f != "1st_serve_percentage"]
    sig = R[sig_cols].astype(object).where(R[sig_cols].notna(), "").astype(str).agg("|".join, axis=1)
    R["sig"] = sig
    conflicts = R[R["match_id"].isin(dup_ids)].groupby("match_id")["sig"].nunique().gt(1)
    R = R.drop_duplicates("match_id", keep="first").reset_index(drop=True)
    T.log(f"{len(R):,} distinct matches with statistics ({len(dup_ids):,} in two files, "
          f"{int(conflicts.sum()):,} with different statistics)")
    out = pd.DataFrame({"match_id_fs": R["match_id"]})
    for side in ("home", "away"):
        out[f"{side}_ace"] = R[f"{side}_aces"].map(num)
        out[f"{side}_df"] = R[f"{side}_double_faults"].map(num)
        fw = R[f"{side}_1st_serve_points_won"].map(frac)
        out[f"{side}_first_won"], out[f"{side}_first_in"] = fw.str[0], fw.str[1]
        sw = R[f"{side}_2nd_serve_points_won"].map(frac)
        out[f"{side}_second_won"], out[f"{side}_x_second_den"] = sw.str[0], sw.str[1]
        sp = R[f"{side}_service_points_won"].map(frac)
        out[f"{side}_sv_won"], out[f"{side}_svpt"] = sp.str[0], sp.str[1]
        sg = R[f"{side}_service_games_won"].map(frac)
        out[f"{side}_x_holds"], out[f"{side}_sv_gms"] = sg.str[0], sg.str[1]
        bp = R[f"{side}_break_points_saved"].map(frac)
        out[f"{side}_bp_saved"], out[f"{side}_bp_faced"] = bp.str[0], bp.str[1]
        out[f"{side}_x_first_pct"] = pd.to_numeric(R[f"{side}_1st_serve_percentage"].astype(str).str.rstrip("%"),
                                                   errors="coerce")
        out[f"{side}_x_games_won"] = R[f"{side}_total_games_won"].map(frac).str[0]
    # placeholder blocks: every line "0% (0/0)" (pages of 2010-2014 above all): no statistics, not zero counts
    zero = out["home_svpt"].fillna(0).eq(0) & out["away_svpt"].fillna(0).eq(0)
    out["x_zero_block"] = zero
    count_cols = [f"{s}_{c}" for s in ("home", "away") for c in C.FIELDS + ["x_second_den", "x_holds", "x_first_pct",
                                                                           "x_games_won"]]
    out.loc[zero, count_cols] = np.nan
    # an impossible first/second split: no second serve in 20 serve points or more, or more double faults than
    # second serves (pages of 2012-2013 file every serve point as a first serve): the split is blanked, the page's
    # values kept in x_*_raw
    for side in ("home", "away"):
        sec = out[f"{side}_svpt"] - out[f"{side}_first_in"]
        bad = ((sec == 0) & (out[f"{side}_svpt"] >= 20)) | (out[f"{side}_df"] > sec)
        out[f"{side}_x_split_blanked"] = bad
        for f in ("first_in", "first_won", "second_won"):
            out[f"{side}_x_{f}_raw"] = out[f"{side}_{f}"]
            out.loc[bad, f"{side}_{f}"] = np.nan
    out["x_detail_agrees"] = [(a == (r1, r2)) and (b == (s1_, s2_)) for a, b, r1, r2, s1_, s2_ in
                              zip(R["detail_aces"].map(tuple), R["detail_svc"].map(tuple), R["home_aces"],
                                  R["away_aces"], R["home_service_points_won"], R["away_service_points_won"])]
    out["x_file"], out["x_line"] = R["file"], R["line"]
    out["x_dup_conflict"] = R["match_id"].isin(set(conflicts.index[conflicts]))
    out["status"] = R["status"].astype(str)
    out["home_player"], out["away_player"] = R["home_player"], R["away_player"]
    out["sets"] = R["set_scores"].map(set_games)
    out["home_sets"], out["away_sets"] = R["home_sets"].map(num), R["away_sets"].map(num)
    out["x_date"] = R["match_date"].astype(str)
    # link and orient
    links = C.links("flashscore")
    S = T.s0_frame().set_index("match_id")
    links = links[links["match_id"].isin(S.index)].set_index("source_key")
    L = out[out["match_id_fs"].isin(links.index)].copy()
    L["match_id"] = L["match_id_fs"].map(links["match_id"])
    L["link_method"] = L["match_id_fs"].map(links["link_method"]).str.split(";").str[0]
    na, nb = S.loc[L["match_id"], "name_a"].to_numpy(), S.loc[L["match_id"], "name_b"].to_numpy()
    h = L["home_player"].map(T.surname_first_to_initial_first)
    a = L["away_player"].map(T.surname_first_to_initial_first)
    o = [T.orient(x, y, p, q) for x, y, p, q in zip(h, a, na, nb)]
    L["a1"] = [x[0] for x in o]
    L["g_same"], L["g_swap"] = [x[1] for x in o], [x[2] for x in o]
    a_won = S.loc[L["match_id"], "a_won"].to_numpy()
    s0s = S.loc[L["match_id"], "sets_w"].to_numpy()
    # the winner: the timing study's Flashscore records (the head-to-head feed marks the winner; sets won would name
    # a retiring leader), read in the page's own home/away order
    fr = pd.read_parquet(C.SNAP / "links" / "flashscore_records.parquet",
                         columns=["fs_match_id", "home_name", "away_name", "winner"]).set_index("fs_match_id")
    fr = fr[~fr.index.duplicated()]
    rh, ra, rw = (L["match_id_fs"].map(fr[c]) for c in ("home_name", "away_name", "winner"))
    same_order = rh.eq(L["home_player"]) & ra.eq(L["away_player"])
    swapped_order = rh.eq(L["away_player"]) & ra.eq(L["home_player"])
    home_won = np.where(same_order & rw.isin(["home", "away"]), rw.eq("home"),
                        np.where(swapped_order & rw.isin(["home", "away"]), rw.eq("away"), np.nan))
    sets_ok, games_ok = [], []
    for sets, a1, aw, ss, hg, ag in zip(L["sets"], L["a1"], a_won, s0s, L["home_x_games_won"], L["away_x_games_won"]):
        if a1 is None or not sets:
            sets_ok.append(False)
        else:
            ab = [(x, y) if a1 else (y, x) for x, y in sets]
            wf = ab if aw else [(y, x) for x, y in ab]
            sets_ok.append(bool(T.K.sets_equal(tuple(wf), ss)))
        if np.isnan(hg) or np.isnan(ag) or (hg + ag) == 0:
            games_ok.append(np.nan)                 # the page gives no games won
        else:
            # Flashscore's games won leave tiebreak games out: a 7-6 set counts 6-6, a match tiebreak (10-x) nothing;
            # a set of 10 games or more is read both ways (an advantage set, or a match tiebreak)
            base = [(6, 6) if (x, y) in ((7, 6), (6, 7)) else (x, y) for x, y in sets]
            alt = [(0, 0) if max(x, y) >= 10 else (x, y) for x, y in base]
            games_ok.append(bool(sets) and any((hg, ag) == (sum(x for x, _ in b), sum(y for _, y in b))
                                               for b in (base, alt)))
    L["x_sets_agree"], L["x_games_agree"], L["home_won"] = sets_ok, games_ok, home_won
    nine = [f"{s}_{c}" for s in ("home", "away") for c in C.COUNTS]
    L["complete"] = L["status"].eq("3") & L[nine].notna().all(axis=1) & L["x_sets_agree"] & \
        ~pd.Series(L["x_games_agree"], index=L.index).eq(False)
    w = pd.DataFrame({"source_key": L["match_id_fs"], "match_id": L["match_id"], "a1": L["a1"],
                      "complete": L["complete"], "link_method": L["link_method"]})
    for side, k in (("home", "p1"), ("away", "p2")):
        for f in C.FIELDS + ["x_second_den", "x_holds", "x_first_pct", "x_games_won", "x_split_blanked",
                             "x_first_in_raw", "x_first_won_raw", "x_second_won_raw"]:
            w[f"{k}_{f}"] = L[f"{side}_{f}"].to_numpy()
        w[f"{k}_x_src_name"] = L[f"{side}_player"].to_numpy()
        w[f"{k}_x_src_side"] = side
    hw = pd.to_numeric(pd.Series(L["home_won"].to_numpy()), errors="coerce").to_numpy()     # 1.0 / 0.0 / NaN
    w["p1_x_src_won"] = np.where(np.isnan(hw), np.nan, hw == 1)
    w["p2_x_src_won"] = np.where(np.isnan(hw), np.nan, hw == 0)
    for c in ("x_sets_agree", "x_games_agree", "x_detail_agrees", "x_dup_conflict", "x_zero_block", "x_file", "x_line",
              "x_date"):
        w[c] = L[c].to_numpy()
    w["x_status"] = L["status"].to_numpy()
    w["x_name_grade_same"], w["x_name_grade_swap"] = L["g_same"].to_numpy(), L["g_swap"].to_numpy()
    rows = T.to_contract(w, READER, FAMILY, "box",
                         player_extra=["x_second_den", "x_holds", "x_first_pct", "x_games_won", "x_split_blanked",
                                       "x_first_in_raw", "x_first_won_raw", "x_second_won_raw", "x_src_name",
                                       "x_src_side", "x_src_won"],
                         match_extra=["x_sets_agree", "x_games_agree", "x_detail_agrees", "x_dup_conflict",
                                      "x_zero_block", "x_file", "x_line", "x_date", "x_status", "x_name_grade_same",
                                      "x_name_grade_swap"])
    rows["x_games_agree"] = rows["x_games_agree"].astype("boolean")
    rows["x_src_won"] = rows["x_src_won"].astype("boolean")
    cons = {"second_den_equals_svpt_minus_first_in": (rows["x_second_den"] == rows["svpt"] - rows["first_in"]),
            "sv_won_equals_first_won_plus_second_won": (rows["sv_won"] == rows["first_won"] + rows["second_won"]),
            "first_pct_equals_first_in_over_svpt": ((rows["first_in"] / rows["svpt"] * 100).round() == rows["x_first_pct"])}
    have = rows[["svpt", "first_in", "x_second_den"]].notna().all(axis=1)
    summary = {
        "inputs": rec_inputs, "per_file": per_file,
        "records": {"distinct_matches_with_statistics": int(len(R)), "in_two_files": int(len(dup_ids)),
                    "in_two_files_with_different_statistics": int(conflicts.sum()),
                    "detail_section_agrees": int(out["x_detail_agrees"].sum())},
        "linked": {"matches_with_statistics_in_link_file": int(len(L)),
                   "by_link_method": T.tidy_counts(L["link_method"].value_counts())},
        "dropped": {"not_in_link_file": int(len(out) - len(L)), "orientation_unresolved": int(L["a1"].isna().sum())},
        "checks": {"sets_agree": int(L["x_sets_agree"].sum()),
                   "games_compared": int(pd.Series(L["x_games_agree"]).notna().sum()),
                   "games_agree": int(pd.Series(L["x_games_agree"]).eq(True).sum()),
                   "placeholder_zero_blocks_blanked": int(L["x_zero_block"].sum()),
                   "player_rows_split_blanked": int(L["home_x_split_blanked"].sum() + L["away_x_split_blanked"].sum()),
                   "complete": int(L["complete"].sum())},
        "self_consistency_share": {k: round(float(v[have].mean()), 5) for k, v in cons.items()},
        "contract_checks": T.check_contract(rows),
        "winner_vs_stage0": T.winner_check(rows),
        "definitions": __doc__.split("Mapping of a page's")[1].split("Writes box")[0].strip(),
        "sanity_vs_stage0_by_level_group": T.records(T.sanity(rows, by=["level_group"])),
        "hand_check": {"keys": T.sample_keys(rows, where=rows["complete"]), "status": "pending"},
    }
    T.write_reader(rows, READER, summary)
    T.log(f"done in {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
