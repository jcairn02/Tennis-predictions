"""Readers of the ATP Stats Centre records in the Hugging Face handoff (data/raw/public_dump/atp_pipeline_handoff/
infosys_deep/ and infosys_full/, <year>_data.jsonl[.gz]; 2018-2019 and 2021-2024; the 1970 file is undated):

    atp_ks_handoff           the key statistics of the match (keystats.setStats.set0), mapped by atp_keystats.py
    atp_mb_handoff_recount   the nine counts recounted from the record's rally analysis (rally_analysis.rallyData:
                             every point filed under the side and kind that ended it, with its serve number, score
                             before the point (server first), break-point flags, tiebreak flag); the server is derived
                             (atp_recount.derive_servers; validated against MatchBeats in atp_backfill.py). complete
                             also needs the record's own rally_analysis.pointsMissing to be False
                             (x_complete_before_source_flag keeps the engine's verdict alone)

One record per match: the two folders hold most matches twice; as match_timing/srcb_sources.load_infosys, the
infosys_deep copy is kept first. A reader takes the deep copy when it holds what the reader needs (set0 key statistics;
rally points) and the full copy otherwise (x_folder says which). Where both copies hold set0 key statistics, their
values are compared (box/atp_handoff_copies.csv).
Singles only (match codes MSnnn / QSnnn). Orientation: player 1 / player 2 are the record's player1_id / player2_id;
the key statistics' own player list and the rally analysis's playerDetails are matched to them by ATP code (a record
whose lists name other players is dropped from that reader, counted). Linked by the event linker; the infosys link
file (match_timing) is compared, not used (x_linkfile_match_id).

Run: ./python.sh src/eda/source_reconciliation/atp_handoff.py [--workers 4]
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
from concurrent.futures import ProcessPoolExecutor
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
from src.eda.source_reconciliation import common as C  # noqa: E402

FOLDERS = ("infosys_deep", "infosys_full")


def _code(v) -> str:
    return A.atp_code(v)


def _record(r: dict, folder: str, fname: str, line: int) -> dict:
    """One handoff record reduced to identity, key-statistic counts and the rally recount (no Stage 0 needed)."""
    code = str(r.get("match_id") or "").upper()
    out = {"folder": folder, "file": fname, "line": line, "year": r.get("year"), "tid": r.get("tournament_id"),
           "code": code, "match_date": r.get("match_date")}
    out["source_key"] = f"{r.get('year')}_{r.get('tournament_id')}_{code}"
    c1, c2 = _code(r.get("player1_id")), _code(r.get("player2_id"))
    out["c1"], out["c2"] = c1, c2
    ms = r.get("match_status") or {}
    pdx = ms.get("playerData") or {}
    out["f1"] = f"{pdx.get('tm1Ply1FirstName') or ''} {pdx.get('tm1Ply1LastName') or ''}".strip()
    out["f2"] = f"{pdx.get('tm2Ply1FirstName') or ''} {pdx.get('tm2Ply1LastName') or ''}".strip()
    out["s1"], out["s2"] = r.get("player1_name") or "", r.get("player2_name") or ""
    out["status"] = ms.get("matchStatus")
    w = ms.get("matchWinner")
    tm1, tm2 = _code(pdx.get("tm1Ply1Id")), _code(pdx.get("tm2Ply1Id"))
    # the winner flag refers to the status block's tm1 / tm2; put it on the record's player1 / player2
    if w in (1, 2, "1", "2") and {tm1, tm2} == {c1, c2}:
        wc = tm1 if int(w) == 1 else tm2
        out["winner_no"] = 1 if wc == c1 else 2
    else:
        out["winner_no"] = None
    ks = r.get("keystats") or {}
    s0 = ((ks.get("setStats") or {}).get("set0")) or []
    out["ks_completed"] = ks.get("matchCompleted")
    out["has_ks"] = bool(s0)
    if s0:
        pl = ks.get("players") or []
        k1 = _code(pl[0].get("player1Id")) if len(pl) > 0 and isinstance(pl[0], dict) else ""
        k2 = _code(pl[1].get("player1Id")) if len(pl) > 1 and isinstance(pl[1], dict) else ""
        stats = {e.get("name"): (e.get("player1"), e.get("player2")) for e in s0 if isinstance(e, dict)}
        if (k1, k2) == (c1, c2) or not (k1 or k2):
            out["ks_orient"] = "same"
        elif (k1, k2) == (c2, c1):
            out["ks_orient"] = "swapped"
            stats = {n: (b, a) for n, (a, b) in stats.items()}
        else:
            out["ks_orient"] = "other_players"
        out["ks_stats_json"] = json.dumps(stats)
        out.update({"ks_" + k: v for k, v in K.counts(stats).items()})
    ra = r.get("rally_analysis") or {}
    data = ra.get("rallyData") or []
    out["has_rally"] = bool(data)
    if data:
        det = ra.get("playerDetails") or []
        t1 = _code(det[0].get("player1Id")) if len(det) > 0 and isinstance(det[0], dict) else ""
        t2 = _code(det[1].get("player1Id")) if len(det) > 1 and isinstance(det[1], dict) else ""
        swap = False
        if (t1, t2) == (c1, c2) or not (t1 or t2):
            out["ra_orient"] = "same"
        elif (t1, t2) == (c2, c1):
            out["ra_orient"] = "swapped"
            swap = True
        else:
            out["ra_orient"] = "other_players"
        out["ra_points_missing_flag"] = ra.get("pointsMissing")
        out["ra_completed"] = ra.get("matchCompleted")
        pts, seen = [], set()
        for cat in data:
            for lst in ("t1err", "t1win", "t2err", "t2win"):
                for e in cat.get(lst) or []:
                    if not isinstance(e, dict) or e.get("pointId") in seen:
                        continue
                    seen.add(e.get("pointId"))
                    p = P.rally_point(e.get("pointId"), lst, e.get("pointEndType"), e.get("score"),
                                      e.get("t1BreakPoint"), e.get("t2BreakPoint"), e.get("tieBreak"))
                    if p:
                        if swap:
                            p["winner"] = 3 - p["winner"] if p["winner"] in (1, 2) else p["winner"]
                            p["bp1"], p["bp2"] = p["bp2"], p["bp1"]
                        pts.append(p)
        rc = R.recount_match(pts, None, None, False, derive=True, no_ad=int(r.get("tournament_id") or 0)
                             in P.NEXT_GEN_FINALS)
        out.update({"rc_" + k: v for k, v in rc.items()})
    return out


def _file(path: str) -> list[dict]:
    p = Path(path)
    op = gzip.open if p.suffix == ".gz" else open
    rows = []
    with op(p, "rt", encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except ValueError:
                rows.append({"folder": p.parent.name, "file": p.name, "line": n, "bad_json": True})
                continue
            code = str(r.get("match_id") or "").upper()
            if not (code.startswith("MS") or code.startswith("QS")):
                rows.append({"folder": p.parent.name, "file": p.name, "line": n, "not_singles": True})
                continue
            rows.append(_record(r, p.parent.name, p.name, n))
    return rows


def read_all(workers: int) -> pd.DataFrame:
    paths = sorted(str(p) for d in FOLDERS for p in (C.HANDOFF / d).glob("*_data.jsonl*"))
    paths.sort(key=lambda s: -Path(s).stat().st_size)
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for part in ex.map(_file, paths):
            rows.extend(part)
            A.log(f"  read {len(part):,} records ({part[0]['folder'] if part else ''}/{part[0]['file'] if part else ''})")
    return pd.DataFrame(rows)


def typed(df: pd.DataFrame) -> pd.DataFrame:
    """Object columns made parquet-safe: all-bool -> boolean, all-number -> float, anything else -> string."""
    df = df.copy()
    for c in df.columns:
        if df[c].dtype != object:
            continue
        v = df[c].dropna()
        if v.empty:
            df[c] = df[c].astype("string")
        elif v.map(lambda x: isinstance(x, (bool, np.bool_))).all():
            df[c] = df[c].astype("boolean")
        elif v.map(lambda x: isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, bool)).all():
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = df[c].map(lambda x: None if x is None or (isinstance(x, float) and np.isnan(x)) else str(x)) \
                .astype("string")
    return df


RECORDS = A.BOX / "atp_handoff_records.parquet"      # per-record intermediate (git-ignored), for --reuse


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--reuse", action="store_true", help="read the per-record intermediate instead of the JSON")
    args = ap.parse_args()
    if args.reuse and RECORDS.exists():
        raw = pd.read_parquet(RECORDS)
    else:
        raw = typed(read_all(args.workers))
        A.BOX.mkdir(parents=True, exist_ok=True)
        raw.to_parquet(RECORDS, index=False)
    common = {"source": "data/raw/public_dump/atp_pipeline_handoff/{infosys_deep,infosys_full}/<year>_data.jsonl[.gz]",
              "records_read": int(len(raw)),
              "records_by_folder_file": raw.groupby(["folder", "file"]).size().rename("n").reset_index()
              .to_dict(orient="records"),
              "left_out": {"bad_json": int(raw.get("bad_json", pd.Series(dtype=bool)).fillna(False).sum()),
                           "not_singles": int(raw.get("not_singles", pd.Series(dtype=bool)).fillna(False).sum())}}
    r = raw[raw["source_key"].notna()].copy()
    r["year"] = pd.to_numeric(r["year"], errors="coerce")
    undated = ~r["year"].between(2010, 2026)
    common["left_out"]["no_season_1970_file"] = int(undated.sum())
    r = r[~undated].copy()
    r["season"] = r["year"].astype(int)
    r["ev"] = pd.to_numeric(r["tid"], errors="coerce").fillna(-1).astype(int)
    hint = [P.round_hint(c) for c in r["code"]]
    r["qual"] = [h[0] for h in hint]
    r["round"] = [h[1] for h in hint]
    # the two copies of a match's key statistics
    both = r[r["has_ks"].fillna(False).astype(bool)].groupby("source_key")["folder"].nunique()
    copies = r[r["source_key"].isin(both[both > 1].index) & r["has_ks"].fillna(False).astype(bool)]
    cmp = copies.pivot_table(index="source_key", columns="folder", values="ks_stats_json", aggfunc="first")
    same = (cmp["infosys_deep"] == cmp["infosys_full"]) if len(cmp) else pd.Series(dtype=bool)
    pd.DataFrame({"matches_in_both_copies_with_keystats": [int(len(cmp))],
                  "identical_set0_keystats": [int(same.sum())]}).to_csv(A.BOX / "atp_handoff_copies.csv",
                                                                       index=False)
    common["copies"] = {"matches_with_keystats_in_both_copies": int(len(cmp)),
                        "identical_set0_keystats": int(same.sum()),
                        "differing_examples": list(cmp.index[~same][:10]) if len(cmp) else []}
    # one record per match and reader: the deep copy first, when it holds what the reader needs
    r["deep_first"] = r["folder"].map({"infosys_deep": 0, "infosys_full": 1})
    r = r.sort_values(["source_key", "deep_first", "line"])
    keys = r.drop_duplicates("source_key")[["source_key", "season", "ev", "qual", "round", "c1", "c2", "f1", "f2",
                                            "s1", "s2"]].set_index("source_key", drop=False)
    common["matches"] = int(len(keys))
    linker = A.EventLinker()
    lk = linker.link(keys, A.crosswalk())
    keys = keys.join(lk)
    lf = A.C.links("infosys", columns=["match_id", "source_key"]).drop_duplicates("source_key").set_index("source_key")
    keys["x_linkfile_match_id"] = keys.index.map(lf["match_id"])
    agree = keys["match_id"].notna() & keys["x_linkfile_match_id"].notna()
    # where only the link file places a record, its match is taken, the players oriented inside it by id or name
    only_lf = keys.index[keys["match_id"].isna() & keys["x_linkfile_match_id"].notna()
                         & ~keys["x_linkfile_match_id"].isin(set(keys["match_id"].dropna()))]
    xw = A.crosswalk()
    fallback = 0
    for k in only_lf:
        side = A.orient_in_match(linker, keys.at[k, "x_linkfile_match_id"],
                                 A.player_keys(keys.at[k, "c1"], keys.at[k, "f1"], keys.at[k, "s1"], xw),
                                 A.player_keys(keys.at[k, "c2"], keys.at[k, "f2"], keys.at[k, "s2"], xw))
        if side:
            keys.loc[k, ["match_id", "p1_side", "link_method"]] = [keys.at[k, "x_linkfile_match_id"], side,
                                                                   "infosys_link_file"]
            fallback += 1
    common["linked"] = int(keys["match_id"].notna().sum())
    common["link_methods"] = keys["link_method"].value_counts().to_dict()
    common["unlinked"] = keys.loc[keys["match_id"].isna(), "unlinked_reason"].value_counts().to_dict()
    common["vs_infosys_link_file"] = {
        "both_linked": int(agree.sum()),
        "same_match_id": int((keys.loc[agree, "match_id"] == keys.loc[agree, "x_linkfile_match_id"]).sum()),
        "only_link_file": int(len(only_lf)), "only_link_file_taken_oriented": fallback,
        "only_event_linker": int((keys["match_id"].notna() & keys["x_linkfile_match_id"].isna()).sum()),
        "differ_examples": keys.loc[agree & (keys["match_id"] != keys["x_linkfile_match_id"]),
                                    ["match_id", "x_linkfile_match_id"]].head(10).reset_index().to_dict("records")}
    link_cols = ["match_id", "p1_side", "link_method", "x_linkfile_match_id"]
    ctx_all = P.stage0_context(keys["match_id"], keys["p1_side"])

    # ---- atp_ks_handoff
    ks = r[r["has_ks"].fillna(False).astype(bool)].drop_duplicates("source_key").set_index("source_key", drop=False)
    info = dict(common, reader="atp_ks_handoff")
    info["records_with_set0_keystats"] = int(len(ks))
    info["orientation"] = ks["ks_orient"].value_counts().to_dict()
    ks = ks[ks["ks_orient"].ne("other_players")]
    ks = ks.join(keys[link_cols])
    info["dropped"] = {"keystats_name_other_players": int(info["orientation"].get("other_players", 0)),
                       "unlinked": int(ks["match_id"].isna().sum())}
    ks = ks[ks["match_id"].notna()].copy()
    ks = ks.rename(columns={c: c[3:] for c in ks.columns if c.startswith("ks_") and c[-2:] in ("_1", "_2")})
    ks["complete"] = ks["ks_completed"].fillna(False).astype(bool)
    ks["x_status"] = ks["status"].fillna("")
    ks["x_folder"] = ks["folder"]
    ks["x_season"] = ks["season"]
    ks["x_match_date"] = ks["match_date"]
    rows = A.long_rows(ks, A.FIELDS + ["x_first_won_den", "x_second_den", "x_sv_won_den", "x_spd1"],
                       extra=["complete", "link_method", "x_status", "x_folder", "x_season", "x_match_date",
                              "x_linkfile_match_id"])
    wn = pd.concat([ks["winner_no"], ks["winner_no"]], ignore_index=True)
    rows["x_won"] = pd.Series(np.where(wn.isna(), None, wn.astype(float) == rows["x_player_no"].astype(float)),
                              dtype=object)
    rows["x_code"] = pd.concat([ks["c1"], ks["c2"]], ignore_index=True).to_numpy()
    info["winner_vs_stage0"] = A.winner_check(rows)
    s = rows[rows["svpt"].notna()]
    info["internal_consistency"] = {
        "first_won_den_eq_first_in": float((s["x_first_won_den"] == s["first_in"]).mean()),
        "second_den_eq_svpt_minus_first_in": float((s["x_second_den"] == s["svpt"] - s["first_in"]).mean()),
        "sv_won_den_eq_svpt": float((s["x_sv_won_den"] == s["svpt"]).mean()),
        "sv_won_eq_first_plus_second": float((s["sv_won"] == s["first_won"] + s["second_won"]).mean()),
        "rows": int(len(s))}
    A.write_reader("atp_ks_handoff", A.to_contract(rows, "atp_ks_handoff", "box"), info)

    # ---- atp_mb_handoff_recount
    ra = r[r["has_rally"].fillna(False).astype(bool)].drop_duplicates("source_key").set_index("source_key", drop=False)
    info = dict(common, reader="atp_mb_handoff_recount", route="rally_analysis (the handoff holds no MatchBeats)")
    info["records_with_rally_points"] = int(len(ra))
    info["orientation"] = ra["ra_orient"].value_counts().to_dict()
    info["points_missing_flag"] = ra["ra_points_missing_flag"].astype(str).value_counts().to_dict()
    ra = ra[ra["ra_orient"].ne("other_players")]
    ra = ra.join(keys[link_cols])
    info["dropped"] = {"rally_names_other_players": int(info["orientation"].get("other_players", 0)),
                       "unlinked": int(ra["match_id"].isna().sum())}
    ra = ra[ra["match_id"].notna()].copy()
    ra = ra.rename(columns={c: c[3:] for c in ra.columns if c.startswith("rc_")})
    ctx = ctx_all.loc[ra.index]
    fin = [R.finalize({c: ra.at[k, c] for c in ("x_sets_recount", "x_games_not_ending_at_last_point",
                                                   "x_final_game_unfinished", "x_points", "x_point_gaps",
                                                   "x_game_gaps", "x_points_without_server")},
                      ctx.at[k, "s0_sets"], ctx.at[k, "p1_is_winner"], ctx.at[k, "s0_status"] == "retired")
           for k in ra.index]
    for c in ("x_sets_stage0", "x_sets_equal", "complete"):
        ra[c] = [f[c] for f in fin]
    # the source's own pointsMissing flag also rules a recount out: where it is set, recounts that pass the gap and
    # set-score checks still differ from the key statistics far more often (serve points equal in 93.75% of player rows
    # against 99.90% where it is not set; observed while building this reader), so points can be missing without a gap
    # in the point numbers
    flag = ra["ra_points_missing_flag"].fillna(False).astype(bool)
    ra["x_complete_before_source_flag"] = ra["complete"].astype(bool)
    ra["complete"] = ra["complete"].astype(bool) & ~flag
    ra["x_s0_status"] = ctx["s0_status"]
    ra["x_folder"] = ra["folder"]
    ra["x_season"] = ra["season"]
    ra["x_points_missing_flag"] = ra["ra_points_missing_flag"]
    rows = P.to_long(ra, extra=["complete", "link_method", "x_s0_status", "x_folder", "x_season",
                                "x_points_missing_flag", "x_complete_before_source_flag", "x_linkfile_match_id"])
    rows["x_code"] = pd.concat([ra["c1"], ra["c2"]], ignore_index=True).to_numpy()
    info["recounted_matches"] = int(len(ra))
    info["recounts_complete"] = int(ra["complete"].sum())
    info["incomplete_reasons"] = {
        "point_gaps": int((ra["x_point_gaps"] > 0).sum()), "game_gaps": int((ra["x_game_gaps"] > 0).sum()),
        "games_not_ending_at_last_point": int((ra["x_games_not_ending_at_last_point"] > 0).sum()),
        "set_games_differ_from_stage0": int(ra["x_sets_equal"].eq(False).sum()),
        "points_without_server": int((ra["x_points_without_server"] > 0).sum()),
        "source_flags_points_missing": int(flag.sum()),
        "passed_the_checks_but_source_flags_points_missing": int((ra["x_complete_before_source_flag"] & flag).sum())}
    diag = [c for c in P.PER_MATCH if c.startswith("x_") and c in ra and c not in
            ("x_sets_recount", "x_sets_stage0", "x_sets_equal")]
    info["server_rule_diagnostics_sum"] = {c: float(pd.to_numeric(ra[c], errors="coerce").fillna(0).sum())
                                           for c in diag}
    info["winner_vs_stage0"] = A.winner_check(rows)
    A.write_reader("atp_mb_handoff_recount", A.to_contract(rows, "atp_mb_handoff_recount", "recount"), info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
