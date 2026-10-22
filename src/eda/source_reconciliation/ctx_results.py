"""Part C of the source-reconciliation study: results and scores. For every Stage 0 match another source holds, the
winner, the set scores (with tiebreak points where both give them) and the status (completed, retired, walkover,
defaulted) compared with Stage 0's; the disagreements classed; each class judged by the official record where held,
else by the other independent sources; and the Stage 0 rows that two or more independent sources contradict.

Sources: the match-timing link files tennis_data, open_tennis_data, api_tennis, flashscore, slam_feeds, wta_api, tdi,
sofascore, live_tennis_api (status only), infosys (winner and status only), read by ctx_readers; TennisLive's event
listings, the WTA website's records and the ITF's live data, linked by ctx_selflink (run it first); and Tennis My Life's
own rows of Stage 0's Sackmann matches (ctx_tml.py, run it first; a dependent copy, family sackmann_tml).

Stages:
    gather      work/results_<source>.parquet: one row per linked Stage 0 match: the source's values oriented to
                Stage 0's player A, and the classes
    summarize   results_by_source.csv, results_status_pairs.csv, results_set_classes.csv, results_verdicts.csv,
                results_contradicted.csv, results_coverage.csv, results_summary.json; work/results_votes.parquet,
                work/results_disagreements.parquet

Classes. Winner: agree / differ / no_src_winner / unoriented. Sets (ctx_common.compare_sets2): identical,
tb_points_differ, mt_written_otherwise and long_set_capped (definitional), src_shorter / src_longer (one is the start
of the other), mirrored, games_differ, count_differs, no_src_sets, no_s0_sets, no_sets. Status, after reading a
source's 'awarded' as a default (Flashscore's and api-tennis's word for a default win; inference): agree,
vocabulary (defaulted against retired: the coarser word for the same early end), default_no_play (defaulted against
walkover, no game in Stage 0's score), no_src_status (none, or 'unknown'), or '<stage 0>|<source>'.

A family's relation to Stage 0 per field: agree, definitional (the definitional classes above; a truncation where
either source marks the match as not completed) or against; families whose sources split abstain. A Stage 0 value is
listed as contradicted when two or more independent families are against it.

No result is scored: two sources' values of the same match are compared, for every date (the brief's rule 6).

Run: ./python.sh src/eda/source_reconciliation/ctx_results.py [--stage gather|summarize|all] [--sources a,b]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402
from src.eda.source_reconciliation import ctx_readers as R  # noqa: E402

LINK_SOURCES = ["tennis_data", "open_tennis_data", "api_tennis", "flashscore", "slam_feeds", "wta_api", "tdi",
                "sofascore", "live_tennis_api", "infosys"]
SELF_SOURCES = ["tennislive", "wta_site", "itf_live"]
ALL = LINK_SOURCES + SELF_SOURCES + ["tml"]
DEPENDENT = ["derived_otd", "sackmann_tml"]
S0 = ["name_a", "name_b", "player_a_id", "player_b_id", "a_won", "score", "score_flag", "status_detail", "tour", "year",
      "level", "map_level", "tournament_name", "tournament_date", "round", "source"]
MARKED_NOT_DONE = {"retired", "walkover_after_play", "defaulted", "abandoned", "walkover", "bye", "unknown"}
AGAINST_SETS = {"games_differ", "mirrored", "count_differs"}
DEFINITIONAL_SETS = {"mt_written_otherwise", "long_set_capped"}
TRUNC = {"src_shorter", "src_longer"}
AGREE_SETS = {"identical", "tb_points_differ"}
NOT_COMPARED = {"no_src_sets", "no_s0_sets", "no_sets", "unoriented"}


def games_text(sets) -> str | None:
    """A-first games only ('6-4 3-6 7-6'), a Stage 0 match tiebreak in brackets, trailing 0-0 sets dropped; None when
    no sets."""
    if sets is None:
        return None
    s = X.trim(sets)
    return " ".join((f"[{a[0]}-{a[1]}]" if len(a) > 4 and a[4] else f"{a[0]}-{a[1]}") for a in s) if s else ""


def clean_sets(s) -> list:
    """Sets as (int, int, int | None, int | None): a parquet round trip turns missing tiebreak points into NaN."""
    if not isinstance(s, (list, tuple, np.ndarray)):
        return []
    out = []
    for x in s:
        x = list(x) + [None] * (4 - len(x))
        g1, g2 = X.int_or_none(x[0]), X.int_or_none(x[1])
        if g1 is None or g2 is None:
            break
        t1 = None if X.blank(x[2]) else X.int_or_none(x[2])
        t2 = None if X.blank(x[3]) else X.int_or_none(x[3])
        out.append((g1, g2, t1, t2))
    return out


def internal(sets, p1_won, status) -> str:
    """Whether a source's own sets fit its own winner: 'ok', 'winner_lost_more_sets' (a completed match whose listed
    winner took fewer sets), 'not_checked' (no winner, no sets, a tie in sets, or a retirement / walkover)."""
    if X.blank(p1_won) or not sets or status not in (None, "completed"):
        return "not_checked"
    s = X.trim(sets)
    a = sum(1 for x in s if x[0] > x[1])
    b = sum(1 for x in s if x[1] > x[0])
    if a == b:
        return "not_checked"
    return "ok" if (a > b) == (float(p1_won) == 1.0) else "winner_lost_more_sets"


def status_relation(s0: str, src, s0_games: str | None) -> str:
    if X.blank(src) or src == "unknown":
        return "no_src_status"
    src = "defaulted" if src == "awarded" else src
    if src == s0:
        return "agree"
    if {s0, src} == {"defaulted", "retired"}:
        return "vocabulary"
    if {s0, src} == {"defaulted", "walkover"} and not s0_games:
        return "default_no_play"
    return f"{s0}|{src}"


def tml_frame() -> pd.DataFrame:
    """Tennis My Life's own rows of Stage 0's Sackmann matches (ctx_tml.py; names checked), winner first, in the
    readers' layout. Stage 0's own TML rows are left out: there TML is Stage 0's source. The status is read from the
    score as Stage 0's builder reads it, a score short of its best-of without a marker counting as a retirement."""
    from src.eda.predictability_diagnostic import stage0_build as B
    t = pd.read_parquet(X.WORK / "tml_rows.parquet")
    t = t[t["names_ok"] & t["via"].ne("stage0_tml")].drop_duplicates("match_id").copy()
    sets, status = [], []
    for sc, bo in zip(t["score"], t["best_of"]):
        ss, marker = X.s0_sets_w(sc if isinstance(sc, str) else "")
        out = []
        for w, l, tb, br in ss:
            tw = tl = None
            if tb is not None and not br and {w, l} == {7, 6}:
                tl, tw = tb, max(7, tb + 2)
            out.append((w, l, tw if w > l else tl, tl if w > l else tw))
        sets.append(out)
        if not isinstance(sc, str) or not sc.strip():
            status.append(None)
            continue
        st = X.S0_STATUS.get(B.status_of(tuple((a, b, -1, br) for a, b, _, br in ss), marker), "unknown")
        need = (X.int_or_none(bo) or 3) // 2 + 1
        if st == "completed" and sum(1 for w, l, _, _ in ss if w > l) < need:
            st = "retired"
        status.append(st)
    return pd.DataFrame({
        "match_id": t["match_id"].to_numpy(), "source_key": t["tml_key"].to_numpy(),
        "link_method": ("tml_" + t["via"].astype(str) + "_" + t["link_status"].astype(str)).to_numpy(),
        "score_agrees": None, "p1": t["winner_name"].to_numpy(), "p2": t["loser_name"].to_numpy(), "p1_won": 1.0,
        "sets": sets, "status": status, "seed1": t["winner_seed"].map(X.seed_num).to_numpy(),
        "seed2": t["loser_seed"].map(X.seed_num).to_numpy(), "entry1": t["winner_entry"].to_numpy(),
        "entry2": t["loser_entry"].to_numpy(), "surface_raw": t["surface"].to_numpy(), "indoor_raw": t["indoor"].to_numpy(),
        "level_raw": t["tourney_level"].to_numpy(), "round_raw": t["round"].to_numpy(),
        "best_of_raw": t["best_of"].to_numpy(), "draw_raw": t["draw_size"].to_numpy(),
        "tournament_raw": t["tourney_name"].to_numpy(), "day_raw": t["tourney_date"].to_numpy(),
        "linker_side": None})


def gather_one(source: str, m: pd.DataFrame) -> pd.DataFrame:
    if source == "tml":
        j = tml_frame()
    elif source in LINK_SOURCES:
        lk = C.links(source, ["match_id", "source_key", "link_method", "score_agrees"])
        lk["match_id"] = lk["match_id"].astype(str)
        df = R.READERS[source](lk["source_key"])
        j = lk.join(df, on="source_key")
        j["linker_side"] = None
    else:
        lk = pd.read_parquet(X.WORK / f"selflink_{source}.parquet")
        rows = pd.read_parquet(X.WORK / f"selfrows_{source}.parquet")
        j = lk.merge(rows, on="sid", how="left").rename(columns={"sid": "source_key"})
        j["linker_side"] = j["p1_side"]
        j["link_method"] = "selflink_" + j["pass"].astype(str)
        j["score_agrees"] = j["sc"]
        j["p1_won"] = np.where(j["winner"].astype(float) == 1, 1.0, np.where(j["winner"].astype(float) == 2, 0.0, np.nan))
        j["sets"] = [list(s) if s is not None else [] for s in j["sets4"]]
        j["status"] = j["status_hint"].map(X.norm_status)
        if "seed1" in j:
            j["seed1"], j["seed2"] = j["seed1"].map(X.seed_num), j["seed2"].map(X.seed_num)
        j = j.rename(columns={"score": "src_score", "tour": "src_tour", "round": "src_round"})
        j["surface_raw"] = j["ev_surface_raw"] if "ev_surface_raw" in j else j.get("ev_surface")
        j["indoor_raw"] = j.get("ev_indoor")
        j["level_raw"] = (j["ev_kind"].astype(str) + "|" + j["ev_rank"].astype(str)) if "ev_kind" in j else j.get("ev_level")
        j["round_raw"] = j["round_raw"] if "round_raw" in j else j.get("rnd")
        j["draw_raw"] = j["draw_raw"] if "draw_raw" in j else j.get("ev_draw")
        j["tournament_raw"] = j.get("ev_name")
        j["day_raw"] = j["day"].astype(str) if "day" in j else None
        j = j.drop(columns=["p1_side"])
    j = j.join(m[S0], on="match_id")
    j = j[j["name_a"].notna()].copy()
    j["sets"] = [clean_sets(s) for s in j["sets"]]
    j["src_internal"] = [internal(s, w, st) for s, w, st in zip(j["sets"], j["p1_won"], j["status"])]
    j["sets_reoriented"] = False
    if source == "wta_site":
        # the Kaggle copy writes some rows' scores from the other side than its listed winner (the lower-level
        # package's loader aligns names to ids and the winner, not the score): its sets are turned to its own winner
        flip = j["src_internal"].eq("winner_lost_more_sets")
        j.loc[flip, "sets"] = pd.Series([[(b, a, tb, ta) for a, b, ta, tb in s] for s in j.loc[flip, "sets"]],
                                        index=j.index[flip], dtype=object)
        j["sets_reoriented"] = flip
    j = X.orient_frame(j)
    if source == "tennis_data":
        # tennis-data lists winner first; where the names tie (same-surname pairs), Stage 1's pass says who won
        tie = j["p1_side"].isna()
        sw = j["link_method"].astype(str).str.contains("winner_swapped")
        j.loc[tie, "p1_side"] = np.where(j.loc[tie, "a_won"].astype(bool) ^ sw[tie], "A", "B")
        j.loc[tie, "orient_how"] = "stage1_pass"
    if source in SELF_SOURCES:
        tie = j["p1_side"].isna() & j["linker_side"].notna()
        j.loc[tie, "p1_side"] = j.loc[tie, "linker_side"]
        j.loc[tie, "orient_how"] = "linker"
    norec = j["p1"].isna() & j["p2"].isna()
    j.loc[norec, "orient_how"] = "no_record"      # e.g. an AO capture taken before the match ended: no result held
    j = X.to_a(j)
    j["source"] = source
    j["family"] = X.FAMILY[source]
    s0w = j["a_won"].astype(float)
    j["winner_cmp"] = np.select([norec, j["p1_side"].isna(), j["a_won_src"].isna(), j["a_won_src"] == s0w],
                                ["no_record", "unoriented", "no_src_winner", "agree"], "differ")
    s0sets = [X.s0_sets_a(sc, bool(aw), fl == "read_reversed", lv == "GS")
              for sc, aw, fl, lv in zip(j["score"], j["a_won"], j["score_flag"], j["level"])]
    cls = [X.compare_sets2(s, r) if s is not None else ("unoriented", 0) for s, r in zip(j["sets_a"], s0sets)]
    j["sets_cmp"] = [c[0] for c in cls]
    j["sets_n"] = [c[1] for c in cls]
    j["s0_games"] = [games_text(s) for s in s0sets]
    j["src_games"] = [games_text(s) for s in j["sets_a"]]
    j["s0_sets_text"] = [X.sets_text(s) for s in s0sets]
    j["src_sets_text"] = [X.sets_text(s) if s is not None else None for s in j["sets_a"]]
    # tiebreak points: 7-6 sets with the games equal in both, where both give the loser's points
    tbn, tbd = [], []
    for s, r in zip(j["sets_a"], s0sets):
        n = d = 0
        if s is not None:
            for x, y in zip(X.trim(s), X.trim(r)):
                if y[4] or not (x[0] == y[0] and x[1] == y[1]):
                    continue
                tx, ty = X.tb_loser_points(x), X.tb_loser_points(y)
                if tx is not None and ty is not None:
                    n += 1
                    d += int(tx != ty)
        tbn.append(n)
        tbd.append(d)
    j["tb_compared"], j["tb_differ"] = tbn, tbd
    j["s0_status"] = j["status_detail"].map(X.s0_status)
    j["s0_status_detail"] = j["status_detail"]
    j["s0_score_flag"] = j["score_flag"]
    j["src_status"] = j["status"]
    j["status_cmp"] = [status_relation(a, b, g) for a, b, g in zip(j["s0_status"], j["src_status"], j["s0_games"])]
    keep = ["match_id", "source", "family", "source_key", "link_method", "score_agrees", "orient_how", "p1_side",
            "p1", "p2", "a_won", "a_won_src", "winner_cmp", "s0_games", "src_games", "s0_sets_text", "src_sets_text",
            "sets_cmp", "sets_n", "tb_compared", "tb_differ", "s0_status", "s0_status_detail", "s0_score_flag",
            "src_status", "status_cmp", "seed_a_src",
            "seed_b_src", "entry_a_src", "entry_b_src", "surface_raw", "indoor_raw", "level_raw", "round_raw",
            "best_of_raw", "draw_raw", "tournament_raw", "day_raw", "src_internal", "sets_reoriented"]
    for c in keep:
        if c not in j:
            j[c] = None
    out = j[keep].copy()
    for c in ("a_won_src", "seed_a_src", "seed_b_src"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in ("source_key", "link_method", "orient_how", "p1_side", "p1", "p2", "entry_a_src", "entry_b_src",
              "surface_raw", "indoor_raw", "level_raw", "round_raw", "best_of_raw", "draw_raw", "tournament_raw",
              "day_raw", "src_status", "src_games", "src_sets_text"):
        out[c] = out[c].map(lambda v: None if X.blank(v) else str(v))
    out["score_agrees"] = out["score_agrees"].astype("boolean")
    out["sets_reoriented"] = out["sets_reoriented"].astype(bool)
    return out


def gather(sources) -> None:
    m = X.stage0_matches().set_index("match_id")
    X.WORK.mkdir(parents=True, exist_ok=True)
    for s in sources:
        if s in SELF_SOURCES and not (X.WORK / f"selflink_{s}.parquet").exists():
            X.log(f"[{s}] no self-link table: run ctx_selflink.py first; skipped")
            continue
        X.log(f"[{s}] gathering")
        out = gather_one(s, m)
        out.to_parquet(X.WORK / f"results_{s}.parquet", index=False)
        X.log(f"[{s}] {len(out):,} rows; winner {out['winner_cmp'].value_counts().to_dict()}; "
              f"sets {out['sets_cmp'].value_counts().head(8).to_dict()}")


# ------------------------------------------------------------------------------------------------ summaries

def load_all() -> pd.DataFrame:
    frames = [pd.read_parquet(X.WORK / f"results_{s}.parquet") for s in ALL if (X.WORK / f"results_{s}.parquet").exists()]
    return pd.concat(frames, ignore_index=True)


def relations(r: pd.DataFrame) -> pd.DataFrame:
    """Each link's relation to Stage 0 per field: agree / definitional / against / none."""
    r = r.copy()
    r["rel_winner"] = np.select([r["winner_cmp"].eq("agree"), r["winner_cmp"].eq("differ")], ["agree", "against"], "none")
    # a truncation is definitional where Stage 0 marks the match as not completed (a marker in its score: RET, W/O,
    # DEF ...; an unmarked short score is no such mark) or the source does
    not_done = r["s0_status_detail"].isin(MARKED_NOT_DONE) | (r["src_status"].notna() & r["src_status"].ne("completed"))
    r["rel_games"] = np.select([r["sets_cmp"].isin(AGREE_SETS), r["sets_cmp"].isin(DEFINITIONAL_SETS),
                                r["sets_cmp"].isin(TRUNC) & not_done, r["sets_cmp"].isin(TRUNC),
                                r["sets_cmp"].isin(AGAINST_SETS)],
                               ["agree", "definitional", "definitional", "against", "against"], "none")
    r["rel_status"] = np.select([r["status_cmp"].eq("agree"), r["status_cmp"].isin(["vocabulary", "default_no_play"]),
                                 r["status_cmp"].eq("no_src_status")], ["agree", "definitional", "none"], "against")
    r["val_winner"] = np.where(r["a_won_src"] == 1, "A", np.where(r["a_won_src"] == 0, "B", None))
    r["val_games"] = r["src_games"]
    r["val_status"] = r["src_status"].map(lambda s: None if X.blank(s) else ("defaulted" if s == "awarded" else s))
    return r


def by_source(r: pd.DataFrame) -> pd.DataFrame:
    r = r.assign(
        oriented=r["p1_side"].notna(), winner_known=r["winner_cmp"].isin(["agree", "differ"]),
        winner_differ=r["winner_cmp"].eq("differ"), sets_compared=~r["sets_cmp"].isin(NOT_COMPARED),
        sets_identical=r["sets_cmp"].eq("identical"), sets_tb_differ=r["sets_cmp"].eq("tb_points_differ"),
        sets_definitional=r["sets_cmp"].isin(DEFINITIONAL_SETS), sets_truncated=r["sets_cmp"].isin(TRUNC),
        sets_against=r["rel_games"].eq("against"), status_known=~r["status_cmp"].eq("no_src_status"),
        status_definitional=r["rel_status"].eq("definitional"), status_against=r["rel_status"].eq("against"),
        internal_bad=r["src_internal"].eq("winner_lost_more_sets"))
    cols = ["oriented", "winner_known", "winner_differ", "sets_compared", "sets_identical", "sets_tb_differ",
            "sets_definitional", "sets_truncated", "sets_against", "tb_compared", "tb_differ", "status_known",
            "status_definitional", "status_against", "internal_bad", "sets_reoriented"]
    g = r.groupby(["source", "family", "tour", "map_level"], dropna=False)
    t = g[cols].sum().astype(int)
    t.insert(0, "links", g.size())
    t = t.reset_index()
    t["winner_differ_pct"] = (100 * t["winner_differ"] / t["winner_known"].where(t["winner_known"] > 0)).round(3)
    t["sets_against_pct"] = (100 * t["sets_against"] / t["sets_compared"].where(t["sets_compared"] > 0)).round(3)
    t["tb_differ_pct"] = (100 * t["tb_differ"] / t["tb_compared"].where(t["tb_compared"] > 0)).round(3)
    t["status_against_pct"] = (100 * t["status_against"] / t["status_known"].where(t["status_known"] > 0)).round(3)
    return t


def family_votes(r: pd.DataFrame) -> pd.DataFrame:
    """One vote per (match, independent family, field): the relation to Stage 0 where the family's sources share it
    (and the value they give, 'split' where those values differ), 'split' where their relations differ. Families
    dependent on Stage 0's own source (Open Tennis Data, TML) do not vote."""
    v = r[~r["family"].isin(DEPENDENT)]
    out = []
    for field in ("winner", "games", "status"):
        sub = v[v[f"rel_{field}"].ne("none")][["match_id", "family", f"rel_{field}", f"val_{field}"]]
        g = sub.groupby(["match_id", "family"]).agg(rel=(f"rel_{field}", "first"), nrel=(f"rel_{field}", "nunique"),
                                                    val=(f"val_{field}", "first"), nval=(f"val_{field}", "nunique"),
                                                    sources=(f"rel_{field}", "size")).reset_index()
        g["relation"] = np.where(g["nrel"] == 1, g["rel"], "split")
        g["value"] = np.where(g["nval"] <= 1, g["val"], "split")
        out.append(g.assign(field=field)[["match_id", "family", "field", "relation", "value", "sources"]])
    return pd.concat(out, ignore_index=True)


def s0_values(m: pd.DataFrame) -> pd.DataFrame:
    s0 = pd.DataFrame({"match_id": m.index, "winner": np.where(m["a_won"].astype(bool), "A", "B"),
                       "games": [games_text(X.s0_sets_a(sc, bool(aw), fl == "read_reversed", lv == "GS"))
                                 for sc, aw, fl, lv in zip(m["score"], m["a_won"], m["score_flag"], m["level"])],
                       "status": m["status_detail"].map(X.s0_status).to_numpy()})
    return s0.set_index("match_id")


def s0_long(s0: pd.DataFrame) -> pd.Series:
    return s0.stack().rename("stage0_value")


def contradicted(v: pd.DataFrame, s0: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Stage 0 values that two or more independent families are against (a split family abstains)."""
    v = v[v["relation"].ne("split")]
    agg = v.assign(a=v["relation"].eq("against"), g=v["relation"].eq("agree"), d=v["relation"].eq("definitional")) \
        .groupby(["match_id", "field"])[["a", "g", "d"]].sum().reset_index()
    hit = agg[agg["a"] >= 2].rename(columns={"a": "families_against", "g": "families_agreeing", "d": "families_definitional"})
    if hit.empty:
        return pd.DataFrame()
    vv = v.merge(hit[["match_id", "field"]], on=["match_id", "field"])
    vv["fv"] = vv["family"] + ":" + vv["value"].astype(str)
    comp = vv[vv["relation"].eq("against")].sort_values("family").groupby(["match_id", "field"])["fv"].agg("; ".join)
    agree = vv[vv["relation"].isin(["agree", "definitional"])].sort_values("family").groupby(
        ["match_id", "field"])["fv"].agg("; ".join)
    off = vv[vv["family"].isin(list(X.OFFICIAL))].sort_values("family").assign(
        ofv=lambda d: d["family"] + ":" + d["relation"] + ":" + d["value"].astype(str)).groupby(
        ["match_id", "field"])["ofv"].agg("; ".join)
    out = hit.join(comp.rename("competing_values"), on=["match_id", "field"])
    out = out.join(agree.rename("agreeing_values"), on=["match_id", "field"])
    out = out.join(off.rename("official_relation"), on=["match_id", "field"])
    out = out.join(s0_long(s0), on=["match_id", "field"])
    mm = m.reindex(out["match_id"])
    for c in ("tour", "year", "map_level", "tournament_name", "round", "source", "name_a", "name_b", "status_detail"):
        out[c] = mm[c].to_numpy()
    out["stage0_score"] = mm["score"].to_numpy()
    out["tournament_date"] = pd.to_datetime(mm["tournament_date"].to_numpy()).strftime("%Y-%m-%d")
    out = out.rename(columns={"source": "stage0_source"})
    out["in_model_frame"] = out["match_id"].isin(set(X.model_frame_ids()))
    vals = out["competing_values"].fillna("").str.split("; ").map(lambda xs: {x.split(":", 1)[1] for x in xs if ":" in x})
    out["competitors_agree_on_one_value"] = vals.map(len).eq(1)
    out["official_against"] = out["official_relation"].fillna("").str.contains(":against:", regex=False)
    out["official_for_stage0"] = out["official_relation"].fillna("").str.contains(r":(agree|definitional):", regex=True)
    cols = ["match_id", "field", "stage0_value", "competing_values", "competitors_agree_on_one_value",
            "families_against", "families_agreeing", "families_definitional", "agreeing_values", "official_relation",
            "official_against", "official_for_stage0", "in_model_frame", "tour", "year", "map_level",
            "tournament_name", "tournament_date", "round", "name_a", "name_b", "stage0_score", "status_detail",
            "stage0_source"]
    return out[cols].sort_values(["field", "tour", "year", "match_id"])


def verdicts(r: pd.DataFrame, v: pd.DataFrame, s0: pd.DataFrame) -> pd.DataFrame:
    """For every link not agreeing with Stage 0 on a field (against or definitional), who the other independent
    families side with: the official record where an official family other than the link's own holds the match, else
    the others' majority. Siding with Stage 0 = relation agree / definitional; with the source = against Stage 0 with
    the same value as the source's. Dependent sources are judged by the independent families too."""
    vv = v[v["relation"].ne("split")]
    recs = []
    for field in ("winner", "games", "status"):
        d = r[r[f"rel_{field}"].isin(["against", "definitional"])]
        if d.empty:
            continue
        fv = vv[vv["field"].eq(field) & vv["match_id"].isin(set(d["match_id"]))]
        by_match = {k: g for k, g in fv.groupby("match_id")}
        cls_col = {"winner": "winner_cmp", "games": "sets_cmp", "status": "status_cmp"}[field]
        for row in d[["match_id", "source", "family", "tour", "map_level", f"rel_{field}", f"val_{field}",
                      cls_col]].to_dict("records"):
            g = by_match.get(row["match_id"])
            sval = row[f"val_{field}"]
            off_s0 = off_src = maj_s0 = maj_src = maj_other = 0
            if g is not None:
                others = g[g["family"] != row["family"]]
                for fam, rel, value in zip(others["family"], others["relation"], others["value"]):
                    with_s0 = rel in ("agree", "definitional")
                    with_src = rel == "against" and value == sval
                    if fam in X.OFFICIAL:
                        off_s0 += int(with_s0)
                        off_src += int(with_src)
                    maj_s0 += int(with_s0)
                    maj_src += int(with_src)
                    maj_other += int(not with_s0 and not with_src)
            if off_s0 or off_src:
                verdict = ("official_stage0" if off_s0 > off_src else "official_source" if off_src > off_s0
                           else "official_split")
            elif maj_s0 or maj_src:
                verdict = ("majority_stage0" if maj_s0 > maj_src else "majority_source" if maj_src > maj_s0
                           else "majority_tie")
            else:
                verdict = "no_other_source" if maj_other == 0 else "others_differ_from_both"
            recs.append({"match_id": row["match_id"], "source": row["source"], "family": row["family"],
                         "field": field, "relation": row[f"rel_{field}"], "class": row[cls_col],
                         "tour": row["tour"], "map_level": row["map_level"],
                         "stage0_value": s0.at[row["match_id"], field], "source_value": sval, "verdict": verdict})
    return pd.DataFrame(recs)


def summarize() -> None:
    m = X.stage0_matches().set_index("match_id")
    r = load_all()
    r = r.join(m[["tour", "map_level"]], on="match_id")
    r = relations(r)
    X.log(f"loaded {len(r):,} result links over {r['match_id'].nunique():,} Stage 0 matches")
    by_source(r).to_csv(X.OUT / "results_by_source.csv", index=False)
    sp = r.groupby(["source", "s0_status", "status_cmp"]).size().rename("rows").reset_index()
    sp.to_csv(X.OUT / "results_status_pairs.csv", index=False)
    r.groupby(["source", "sets_cmp", "s0_status"]).size().rename("rows").reset_index() \
        .to_csv(X.OUT / "results_set_classes.csv", index=False)
    votes = family_votes(r)
    votes.to_parquet(X.WORK / "results_votes.parquet", index=False)
    s0 = s0_values(m)
    con = contradicted(votes, s0, m)
    con.to_csv(X.OUT / "results_contradicted.csv", index=False)
    ver = verdicts(r, votes, s0)
    ver.to_parquet(X.WORK / "results_disagreements.parquet", index=False)
    vt = ver.groupby(["source", "family", "field", "relation", "class", "verdict"]).size().rename("rows").reset_index()
    vt.to_csv(X.OUT / "results_verdicts.csv", index=False)
    indep = r[~r["family"].isin(DEPENDENT)]
    cov = indep.groupby("match_id")["family"].nunique()
    mm = m[["tour", "map_level", "year"]].copy()
    mm["families"] = cov.reindex(mm.index).fillna(0).astype(int)
    frame = set(X.model_frame_ids())
    mm["frame"] = mm.index.isin(frame)
    covt = mm.groupby(["tour", "map_level"]).agg(matches=("families", "size"),
                                                 with_any=("families", lambda s: int((s > 0).sum())),
                                                 with_two_or_more=("families", lambda s: int((s >= 2).sum()))).reset_index()
    covt.to_csv(X.OUT / "results_coverage.csv", index=False)
    summ = {"links": int(len(r)), "stage0_matches_linked": int(r["match_id"].nunique()),
            "stage0_matches": int(len(m)),
            "stage0_matches_with_an_independent_source": int((mm["families"] > 0).sum()),
            "model_frame_matches": int(mm["frame"].sum()),
            "model_frame_with_two_or_more_independent_families": int((mm["frame"] & (mm["families"] >= 2)).sum()),
            "links_by_source": r["source"].value_counts().to_dict(),
            "orientation_by_source": {s: g["orient_how"].value_counts(dropna=False).rename(str).to_dict()
                                      for s, g in r.groupby("source")},
            "winner_by_source": {s: g["winner_cmp"].value_counts().to_dict() for s, g in r.groupby("source")},
            "sets_by_source": {s: g["sets_cmp"].value_counts().to_dict() for s, g in r.groupby("source")},
            "status_by_source": {s: g["status_cmp"].value_counts().head(15).to_dict() for s, g in r.groupby("source")},
            "internal_inconsistency_by_source": {s: int(g["src_internal"].eq("winner_lost_more_sets").sum())
                                                 for s, g in r.groupby("source")},
            "wta_site_sets_reoriented_to_its_winner": int(r.loc[r["source"].eq("wta_site"), "sets_reoriented"].sum()),
            "contradicted_by_field": con["field"].value_counts().to_dict() if len(con) else {},
            "contradicted_in_model_frame_by_field": con[con["in_model_frame"]]["field"].value_counts().to_dict()
            if len(con) else {}}
    X.write_json(X.OUT / "results_summary.json", summ)
    X.log(f"contradicted: {summ['contradicted_by_field']}; in the frame {summ['contradicted_in_model_frame_by_field']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all", choices=["gather", "summarize", "all"])
    ap.add_argument("--sources", default=",".join(ALL))
    args = ap.parse_args()
    if args.stage in ("gather", "all"):
        gather([s.strip() for s in args.sources.split(",") if s.strip()])
    if args.stage in ("summarize", "all"):
        summarize()
    return 0


if __name__ == "__main__":
    sys.exit(main())
