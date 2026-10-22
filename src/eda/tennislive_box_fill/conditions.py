"""The two conditions of the lower-level gap-fill policy (docs/decisions/2026-10-14-lower-level-gap-fills.md), read on a
built candidate of the level-evidence builder (src/eda/lower_level_evidence/candidate_stage0.py) for one box source.

    C1  counts the same way: per tour and level, on the matches the history scores among the candidate's links, the
        source's counts equal the history's on at least C1_SHARE of them, with at least C1_MIN such matches. Service
        games are left out of the comparison when the source does not give them (TennisLive does not; Stage 0 keeps such
        a box score as 'no_svgms').
        Deciding reading: today's tables (the repository's Stage 0, with every decided repair). Beside it: the frozen
        copy of 8 Oct the builder links against, which still carries errors a repair has since fixed (Roland Garros
        2022-2026's first serves). Fixed on 14 Oct 2026 at the owner's word ("Yes add and fix those"): the first
        package's check read only the frozen copy, and men's Slam qualifying failed there alone (95.3%; 99.6% today).
    C2  fills holes at covered levels and seasons: per tour, level and season with an applied completion, on today's
        tables, either the cell already holds a box score for at least C2_SHARE of its played matches, or the fill
        brings the cell's box share closer to its level's median share over the other seasons from C2_FIRST_SEASON
        (seasons with at least C2_MIN_PLAYED played matches). The second branch, added on 14 Oct 2026 with C1's fix,
        lets a season with a hole catch up with its neighbours (men's Slam qualifying 2018: 49% against about 100% in
        every season from 2019); a level empty in most seasons (ITF before 2025) has a median near 0 and still fails.

Counts and box columns only: no outcome of any match is read for any choice (set scores are not compared here).

Writes to data/studies/tennislive_box_fill/ (or --out):
    c1_agreement.csv      tour x level: shared matches, equal on every compared count, the share, on today's tables
                          (pass) and on the frozen copy (pass_frozen)
    c1_by_count.csv       tables x tour x level x count: the share of sides whose count is equal
    c2_coverage.csv       tour x level x season (cells with an applied completion): today's box share before and after,
                          the completions (and those that still land today), the level's median over the other seasons,
                          which branch passes
    conditions.json       the summary, the failing cells, and the derive options that would undo them
    sides_check.csv       per applied completion, from names alone: side A's counts are its player's in the source, and
                          the two winners agree
    hand_check_sample.csv a random sample of applied completions (seed) for the hand check: the source page's players,
                          day, event, round and score beside Stage 0's

Run: ./python.sh src/eda/tennislive_box_fill/conditions.py --candidate <folder> [--source tennislive_pages]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402

OUT = ROOT / "data" / "studies" / "tennislive_box_fill"
TL_MATCHES = ROOT / "data" / "dump" / "points" / "tennislive" / "matches.parquet"
TODAY = ROOT / "data" / "studies" / "predictability_diagnostic"   # the repository's Stage 0: every decided repair
C1_SHARE, C1_MIN, C2_SHARE = 0.98, 30, 0.5
C2_FIRST_SEASON, C2_MIN_PLAYED = 2013, 30         # C2's level median: the model's seasons, cells big enough to read
PLAYED = ("completed", "retired")
NO_SVGMS_SOURCES = {"tennislive_pages"}           # sources that give no service games
M_COLS = ["match_id", "tour", "map_level", "year", "status", "has_box", "tournament_date", "tournament_name", "round",
          "score", "player_a_id", "player_b_id"]


def compared_counts(source: str) -> list[str]:
    return [c for c in C.BOX if not (c == "sv_gms" and source in NO_SVGMS_SOURCES)]


def stage0(folder: Path) -> pd.DataFrame:
    m = pd.read_parquet(folder / "stage0_matches.parquet", columns=M_COLS)
    m["bucket"] = LC.bucket(m["map_level"]).astype(str)
    return m


def history_counts(folder: Path, match_ids: set) -> dict:
    """The tables' box scores of these matches: the ids they score, and the counts by (match_id, side)."""
    m = pd.read_parquet(folder / "stage0_matches.parquet", columns=["match_id", "has_box"])
    boxed = set(m.loc[m["has_box"].astype(bool) & m["match_id"].isin(match_ids), "match_id"])
    p = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id", "side"] + list(C.BOX))
    return {"boxed": boxed, "counts": p[p["match_id"].isin(boxed)].set_index(["match_id", "side"])}


def load(candidate: Path, source: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The source's box layers, with each match's tour, level bucket and season (the frozen copy's facts, which today's
    tables share), and the frozen copy's matches."""
    L = pd.read_parquet(candidate / "box_layers.parquet")
    L = L[L["source"].eq(source)].copy()
    m = stage0(LC.STAGE0_DIR)
    mm = m.set_index("match_id")
    for c in ("tour", "bucket", "year"):
        L[c] = L["match_id"].map(mm[c]).to_numpy()
    return L, m


def c1(L: pd.DataFrame, source: str, hist: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Shared matches, equal on every compared count, per tour and level. hist None: the frozen copy (the layers' old
    counts, where it held a box score); else history_counts() of the tables to compare with (today's)."""
    cnt = compared_counts(source)
    if hist is None:
        S = L[L["stage0_has_box"].astype(bool)].drop_duplicates("match_id").copy()
    else:
        S = L[L["match_id"].isin(hist["boxed"])].drop_duplicates("match_id").copy()
    eq = np.ones(len(S), dtype=bool)
    rows = []
    for c in cnt:
        for s in "AB":
            if hist is None:
                o = S[f"old_{s}_{c}"].to_numpy(dtype=float)
            else:
                o = hist["counts"][c].reindex(pd.MultiIndex.from_arrays(
                    [S["match_id"], np.repeat(s, len(S))])).to_numpy(dtype=float)
            n = S[f"new_{s}_{c}"].to_numpy(dtype=float)
            e = (o == n) | (np.isnan(o) & np.isnan(n))
            eq &= e
            S[f"eq_{s}_{c}"] = e
    S["all_equal"] = eq
    for (t, b), g in S.groupby(["tour", "bucket"]):
        for c in cnt:
            rows.append({"tour": t, "level": b, "count": c,
                         "sides": int(2 * len(g)),
                         "equal_share": round(float(np.r_[g[f"eq_A_{c}"], g[f"eq_B_{c}"]].mean()), 5)})
    by_count = pd.DataFrame(rows)
    a = S.groupby(["tour", "bucket"]).agg(shared=("match_id", "size"), all_equal=("all_equal", "sum")).reset_index()
    a["share"] = (a["all_equal"] / a["shared"]).round(5)
    a["pass"] = (a["share"] >= C1_SHARE) & (a["shared"] >= C1_MIN)
    return a.rename(columns={"bucket": "level"}), by_count


def c2(L: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Per tour, level and season with an applied completion, on the tables the fill lands on (m: today's): the box
    share among played matches before and after (a completion the tables already score adds nothing), the level's
    median share over the other seasons, and the two ways to pass (module docstring)."""
    ap = L[L["applied"].astype(bool)].drop_duplicates("match_id")
    has = m.drop_duplicates("match_id").set_index("match_id")["has_box"].astype(bool)
    lands = ap[ap["match_id"].isin(has.index)]
    lands = lands[~lands["match_id"].map(has).astype(bool).to_numpy()]
    played = m[m["status"].isin(PLAYED)]
    cov = played.groupby(["tour", "bucket", "year"]).agg(played=("match_id", "size"),
                                                         with_box=("has_box", "sum")).reset_index()
    cov["share"] = cov["with_box"] / cov["played"]
    keys = ["tour", "bucket", "year"]
    out = ap.groupby(keys).size().rename("completions").reset_index().merge(
        lands.groupby(keys).size().rename("completions_landing").reset_index(), on=keys, how="left").merge(
        cov[keys + ["played", "with_box"]], on=keys, how="left")
    out["completions_landing"] = out["completions_landing"].fillna(0).astype(int)
    out["share_before"] = (out["with_box"] / out["played"]).round(4)
    out["share_after"] = ((out["with_box"] + out["completions_landing"]) / out["played"]).round(4)
    ref = cov[(cov["year"] >= C2_FIRST_SEASON) & (cov["played"] >= C2_MIN_PLAYED)]
    out["level_median_other_seasons"] = [
        round(float(ref.loc[(ref["tour"] == t) & (ref["bucket"] == b) & (ref["year"] != y), "share"].median()), 4)
        if ((ref["tour"] == t) & (ref["bucket"] == b) & (ref["year"] != y)).any() else np.nan
        for t, b, y in zip(out["tour"], out["bucket"], out["year"])]
    med = out["level_median_other_seasons"]
    out["pass_half"] = out["share_before"] >= C2_SHARE
    out["pass_toward_level"] = med.notna() & ((out["share_after"] - med).abs() < (out["share_before"] - med).abs())
    out["pass"] = out["pass_half"] | out["pass_toward_level"]
    return out.rename(columns={"bucket": "level"})


def sides(L: pd.DataFrame, source: str) -> pd.DataFrame:
    """Per applied completion, re-derived from names alone: is Stage 0's side A the source's player 1 (more shared name
    words), do side A's added counts equal that player's counts in the source, and do the two winners agree. The
    builder places the counts through its link's side; this checks the placement independently."""
    from src.eda.lower_level_evidence import candidate_stage0 as F
    ap = L[L["applied"].astype(bool)].drop_duplicates("match_id")
    R, _ = F.LOADERS[source]()
    R = R.drop_duplicates("sid").set_index("sid")
    mp = pd.read_parquet(LC.STAGE0_DIR / "stage0_match_players.parquet", columns=["match_id", "side", "player_name",
                                                                                     "won"])
    mp = mp[mp["match_id"].isin(set(ap["match_id"]))].set_index(["match_id", "side"])
    words = (lambda s: set(F.name_key(s).split()) if isinstance(s, str) else set())
    cnt = [c for c in compared_counts(source) if c != "sv_gms"]
    rows = []
    for _, r in ap.iterrows():
        s, a = R.loc[r["sid"]], mp.loc[(r["match_id"], "A")]
        ka, k1, k2 = words(a["player_name"]), words(s["p1"]), words(s["p2"])
        a_is_p1 = len(ka & k1) > len(ka & k2)
        k = 1 if a_is_p1 else 2
        same = all((r[f"new_A_{c}"] == s[f"p{k}_{c}"]) or (pd.isna(r[f"new_A_{c}"]) and pd.isna(s[f"p{k}_{c}"]))
                   for c in cnt)
        rows.append({"match_id": r["match_id"], "sid": r["sid"], "a_name": a["player_name"],
                     "source_p1": s["p1"], "source_p2": s["p2"], "a_is_source_p1": a_is_p1,
                     "name_words_shared": max(len(ka & k1), len(ka & k2)), "a_counts_are_that_players": same,
                     "winners_agree": ((s["winner"] == 1) == a_is_p1) == bool(a["won"])})
    return pd.DataFrame(rows)


def hand_sample(L: pd.DataFrame, m: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    """Applied completions at random: the TennisLive page beside Stage 0's row (names from the player table)."""
    ap = L[L["applied"].astype(bool)].drop_duplicates("match_id").reset_index(drop=True)
    rng = np.random.default_rng(seed)
    take = ap.iloc[np.sort(rng.choice(len(ap), size=min(n, len(ap)), replace=False))]
    tl = pd.read_parquet(TL_MATCHES, columns=["url", "player1_name", "player2_name", "winner_id", "player1_id",
                                              "tournament_name", "stage", "score", "reference_utc", "end_reason"])
    tl = tl.drop_duplicates("url").set_index("url")
    mp = pd.read_parquet(LC.STAGE0_DIR / "stage0_match_players.parquet", columns=["match_id", "side", "player_name"])
    nm = mp.set_index(["match_id", "side"])["player_name"]
    mm = m.set_index("match_id")
    rows = []
    for _, r in take.iterrows():
        url = str(r["sid"]).split("tennislive_pages:", 1)[1]
        p, s = tl.loc[url], mm.loc[r["match_id"]]
        w = p["player1_name"] if str(p["winner_id"]) == str(p["player1_id"]) else p["player2_name"]
        rows.append({"match_id": r["match_id"], "url": url,
                     "tl_players": f"{p['player1_name']} v {p['player2_name']}", "tl_winner": w,
                     "tl_day": str(p["reference_utc"])[:10], "tl_event": p["tournament_name"], "tl_round": p["stage"],
                     "tl_score": p["score"], "tl_end": p["end_reason"],
                     "s0_players": f"{nm.get((r['match_id'], 'A'))} v {nm.get((r['match_id'], 'B'))}",
                     "s0_date": str(s["tournament_date"])[:10], "s0_event": s["tournament_name"],
                     "s0_round": s["round"], "s0_score": s["score"], "s0_status": s["status"],
                     "tour": s["tour"], "level": s["bucket"], "year": int(s["year"]),
                     "verdict": "", "note": ""})
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--source", default="tennislive_pages")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261014)
    ap.add_argument("--today", default=str(TODAY), help="the tables the fill lands on (default: the repository's)")
    a = ap.parse_args()
    cand, out, today = Path(a.candidate), Path(a.out), Path(a.today)
    out.mkdir(parents=True, exist_ok=True)
    L, m = load(cand, a.source)
    m_today = stage0(today)
    c1t, by_t = c1(L, a.source, history_counts(today, set(L["match_id"])))
    c1f, by_f = c1(L, a.source)
    keys = ["tour", "level"]
    a1 = c1t.merge(c1f.rename(columns={"shared": "shared_frozen", "all_equal": "all_equal_frozen",
                                       "share": "share_frozen", "pass": "pass_frozen"}), on=keys, how="outer")
    a1["pass"] = a1["pass"].fillna(False).astype(bool)
    a2 = c2(L, m_today)
    a1.to_csv(out / "c1_agreement.csv", index=False)
    pd.concat([by_t.assign(tables="today"), by_f.assign(tables="frozen")]).to_csv(out / "c1_by_count.csv", index=False)
    a2.to_csv(out / "c2_coverage.csv", index=False)
    applied = L[L["applied"].astype(bool)].drop_duplicates("match_id")
    cells_with_completions = set(zip(applied["tour"], applied["bucket"]))
    c1_fail = [f"{t}:{lv}" for t, lv, ok in zip(a1["tour"], a1["level"], a1["pass"])
               if not ok and (t, lv) in cells_with_completions]
    c1_untested = sorted(f"{t}:{lv}" for t, lv in cells_with_completions
                         if not ((a1["tour"] == t) & (a1["level"] == lv)).any())
    c1_fail_frozen_only = [f"{t}:{lv}" for t, lv, ok, okf in zip(a1["tour"], a1["level"], a1["pass"],
                                                               a1["pass_frozen"].fillna(False))
                           if ok and not okf and (t, lv) in cells_with_completions]
    c2_fail = a2[~a2["pass"]][["tour", "level", "year", "completions", "share_before",
                               "level_median_other_seasons"]].to_dict("records")
    summary = {
        "candidate": str(cand), "source": a.source, "today_tables": str(today),
        "thresholds": {"c1_share": C1_SHARE, "c1_min_shared": C1_MIN, "c2_share": C2_SHARE,
                       "c2_level_median_from": C2_FIRST_SEASON, "c2_level_median_min_played": C2_MIN_PLAYED},
        "compared_counts": compared_counts(a.source),
        "c1_pass_today_fail_frozen_with_completions": c1_fail_frozen_only,
        "applied_not_in_today_tables": int((~applied["match_id"].isin(set(m_today["match_id"]))).sum()),
        "applied_landing_today": int(a2["completions_landing"].sum()),
        "layer_rows": int(len(L)), "kinds": L.drop_duplicates("match_id")["kind"].value_counts().to_dict(),
        "completions_listed": int(L[L["kind"].eq("completion")]["match_id"].nunique()),
        "completions_failing_stage0_checks": int((L["kind"].eq("completion") & ~L["passes_checks"].fillna(False)
                                                  .astype(bool)).sum()),
        "completions_applied": int(len(applied)),
        "applied_by_tour_level_year": applied.groupby(["tour", "bucket", "year"]).size().rename("n").reset_index()
        .rename(columns={"bucket": "level"}).to_dict("records"),
        "c1": a1.to_dict("records"), "c1_fail_with_completions": c1_fail,
        "c1_untested_with_completions": c1_untested, "c2_fail": c2_fail,
        "results_only_option": ",".join(c1_fail + c1_untested)}
    sd = sides(L, a.source)
    sd.to_csv(out / "sides_check.csv", index=False)
    summary["sides"] = {"applied": int(len(sd)), "counts_on_the_named_player": int(sd["a_counts_are_that_players"].sum()),
                        "no_shared_name_word": int((sd["name_words_shared"] == 0).sum()),
                        "winners_agree": int(sd["winners_agree"].sum()),
                        "winners_differ": sd.loc[~sd["winners_agree"], "match_id"].tolist()}
    (out / "conditions.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    hs = hand_sample(L, m, a.sample, a.seed)
    hs.to_csv(out / "hand_check_sample.csv", index=False)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("c1", "applied_by_tour_level_year")}, indent=1,
                     default=str))
    print(a1.to_string(index=False))
    print(a2.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
