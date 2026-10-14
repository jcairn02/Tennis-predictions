"""Serve-speed sources: how much first-serve speed the project holds, what unused files already on disk would add,
and what each candidate acquisition would add to the men's serve-speed-change feature. Reads no match result.

The feature (point_sequence study, speed_prereg.md): a player's mean first-serve speed over his matches in the last
14 days minus over the last 364 days, own history in order; a match carries it when both players have a timed match
in the 14-day window. Only *presence* matters here, so every source is reduced to "this player-match is timed".

Sources of presence (cumulative scenarios):
    S0 held        what the study used: shot_level/stage1_match_stats.parquet, spd1_d > 0 per side (Infosys 2021-24,
                   SirGenkii Jan-Apr 2025, Sackmann's Slam files, SlamTracker, the AO/RG Hawk-Eye copies)
    S1 + on disk   files already on disk that the study did not read:
                   * Infosys key statistics' "1st Serve Average Speed" (Hugging Face handoff, 2021-24), for matches
                     whose points fail the study's half-timed gate
                   * the Australian Open match centre's per-set "1st Serve Average" (2026, plus Wayback captures)
                   * Flashscore's "Average 1st serve speed" in the handoff's Flashscore crawl (2024 - 17 Apr 2026),
                     linked by match_timing/links/flashscore.parquet
    S1b + ManTennisData  the public GitHub dataset msolonskyi/ManTennisData (not held; measured only when --mantd points
                   at a local copy of its atp/matches_2021.csv ... matches_2026.csv and tournaments.csv): the ATP Stats
                   Centre's rendered "1st Serve Average Speed" per player and match, ATP tour level and Challengers,
                   October 2021 onward, linked by names, tournament start date and round with the shot-level linker
    S2 + ATP files hypothetical: every ATP tour-level non-Slam match of 2025-26 (main draw and qualifying) timed, as
                   the ATP Stats Centre files would give if decrypted (electronic line calling on every court of every
                   tour-level event from 2025 is assumed to time every serve: an upper bound; ManTennisData, which
                   reads the same files through the ATP's own pages, shows whole events without speed)
    S3 + Slams     hypothetical: AO 2025, RG 2025 and RG 2026 timed in full (main draw and qualifying)
    S4 + WTA       hypothetical: every WTA tour-level non-Slam match of 2025-26 timed (no source is known)

Frame: Stage 0's main-tour main draws (GS, 1000, 500, 250, Finals; no qualifying), a proxy for the model frame of
matches with closing odds, which this script does not open beyond 2024 (2025-26 is the closed holdout). For 2015-24 the
held scenario is also counted on the meta-stack walk-forward frame and checked against speed_build_summary.json.

Run: ./python.sh src/eda/serve_speed_sources/coverage.py [--mantd DIR] (about 5 minutes; the Flashscore crawl is
streamed)
Writes data/studies/serve_speed_sources/: coverage_matches.csv (match level, by tour x level x year),
coverage_slam_editions.csv, coverage_feature.csv and coverage_feature_by_year.csv (the feature on the frame, by
scenario), coverage_feature_matches.parquet (one row per frame match, gitignored), coverage_summary.json (validation,
the men's 2025-26 counts and power, the Polymarket window, Polymarket's volume by tier)
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import speed_build as SB  # noqa: E402
from src.eda.predictability_diagnostic import common as PD  # noqa: E402

OUT = ROOT / "data" / "studies" / "serve_speed_sources"
SHOT = ROOT / "data" / "studies" / "shot_level"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
FS_LINK = ROOT / "data" / "studies" / "match_timing" / "links" / "flashscore.parquet"
WF = ROOT / "data" / "studies" / "meta_stack" / "walkforward.parquet"
HANDOFF = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff"
AO_STATS = ROOT / "data" / "dump" / "points" / "ausopen" / "set_statistics.parquet"
POLY = ROOT / "data" / "dump" / "odds" / "polymarket" / "event_index.parquet"
TOUR_LEVELS = ("T250", "T500", "T1000", "FIN")
MAIN_TOUR = ("GS",) + TOUR_LEVELS
SCENARIOS = ["S0_held", "S1_on_disk", "S1b_mantd", "S2_atp_files", "S3_slams", "S4_wta"]
MANTD_YEARS = range(2021, 2027)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Stage 0 player-match rows (no result column is read)

def player_rows() -> pd.DataFrame:
    m = pd.read_parquet(PD.MATCHES, columns=["match_id", "tour", "year", "level", "qualifying", "round_order",
                                             "tournament_id", "tournament_name", "tournament_date", "player_a_id",
                                             "player_b_id"])
    rows = pd.concat([m.assign(side="A", player_id=m["player_a_id"]), m.assign(side="B", player_id=m["player_b_id"])],
                     ignore_index=True).drop(columns=["player_a_id", "player_b_id"])
    tm = pd.read_parquet(TIMING, columns=["match_id", "obs"])
    rows = rows.merge(tm, on="match_id", how="left")
    rows["tdate"] = rows["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    rows["slam"] = slam_of(rows["level"], rows["tournament_name"])
    return rows


def slam_of(level: pd.Series, name: pd.Series) -> pd.Series:
    n = name.fillna("").str.lower()
    out = np.select([n.str.contains("austral"), n.str.contains("roland|french"), n.str.contains("wimbledon"),
                     n.str.contains("us open|u.s. open")], ["AO", "RG", "W", "USO"], "")
    return pd.Series(np.where(level.eq("GS").to_numpy(), out, ""), index=level.index)


# ------------------------------------------------------------------------------------------------
# Presence by source

def held_sides() -> pd.DataFrame:
    st = pd.read_parquet(SHOT / "stage1_match_stats.parquet", columns=["match_id", "side", "spd1_d", "spd1_src"])
    st = st[st["spd1_d"] > 0]
    return st[["match_id", "side", "spd1_src"]].rename(columns={"spd1_src": "src"})


def link_keys(source: str) -> pd.DataFrame:
    s = pd.read_parquet(SHOT / "stage0_source_matches.parquet", columns=["source", "key", "match_id"])
    return s[s["source"].eq(source) & s["match_id"].notna()][["key", "match_id"]].drop_duplicates("key")


def infosys_keystats() -> set:
    """Matches whose Infosys key statistics give both players a non-zero 1st Serve Average Speed."""
    hits = set()
    for folder in ("infosys_deep", "infosys_full"):
        for p in sorted((HANDOFF / folder).glob("*_data.jsonl*")):
            op = gzip.open if p.suffix == ".gz" else open
            with op(p, "rt", encoding="utf-8") as f:
                for line in f:
                    if "1st Serve Average Speed" not in line:
                        continue
                    r = json.loads(line)
                    s0 = ((r.get("keystats") or {}).get("setStats") or {}).get("set0") or []
                    for x in s0:
                        if x.get("name") == "1st Serve Average Speed" and plausible(x.get("player1")) \
                                and plausible(x.get("player2")):
                            hits.add(f"{r.get('year')}_{r.get('tournament_id')}_{r.get('match_id')}")
    keys = link_keys("infosys")
    return set(keys.loc[keys["key"].isin(hits), "match_id"])


def ausopen_stats() -> set:
    """Australian Open match-centre matches (2026, and Wayback captures) with both teams' 1st Serve Average."""
    a = pd.read_parquet(AO_STATS, columns=["record_key", "set", "stat", "team1_primary", "team2_primary"])
    a = a[a["stat"].eq("1st Serve Average") & a["set"].eq("All")]
    ok = a[a["team1_primary"].map(plausible) & a["team2_primary"].map(plausible)]["record_key"].unique()
    keys = link_keys("ausopen")
    return set(keys.loc[keys["key"].isin(ok), "match_id"])


FS_SPEED = re.compile(r"Average 1st serve speed", re.I)


def flashscore_crawl() -> set:
    """Flashscore matches of the handoff's crawl with both players' Average 1st serve speed, linked to Stage 0."""
    ids = set()
    for d in ("flashscore_full", "flashscore_gql_stats"):
        for p in sorted((HANDOFF / d).glob("*.jsonl.gz")):
            with gzip.open(p, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "erve speed" not in line:
                        continue
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    if fs_record_timed(r):
                        ids.add(r.get("match_id"))
    link = pd.read_parquet(FS_LINK, columns=["match_id", "source_key"])
    return set(link.loc[link["source_key"].isin(ids), "match_id"])


def mantd_matches(folder: Path) -> tuple[set, dict]:
    """Stage 0 matches that msolonskyi/ManTennisData times for both players (a local copy of its CSVs), and counts."""
    from src.eda.shot_level import common as S
    t = pd.read_csv(folder / "tournaments.csv", usecols=["id", "start_dtm", "series_id"], dtype=str)
    parts = []
    for y in MANTD_YEARS:
        p = folder / f"matches_{y}.csv"
        if p.exists():
            parts.append(pd.read_csv(p, usecols=["id", "tournament_id", "stadie_id", "winner_name", "loser_name",
                                                 "win_average_first_serves_kmh", "los_average_first_serves_kmh"],
                                     dtype=str))
    m = pd.concat(parts, ignore_index=True).merge(t.rename(columns={"id": "tournament_id"}), on="tournament_id",
                                                  how="left")
    m = m[m["win_average_first_serves_kmh"].map(plausible) & m["los_average_first_serves_kmh"].map(plausible)]
    rows = pd.DataFrame({"tour": "M", "d": pd.to_datetime(m["start_dtm"], format="%Y%m%d", errors="coerce"),
                         "name1": m["winner_name"], "name2": m["loser_name"], "round": m["stadie_id"],
                         "draw": np.where(m["stadie_id"].astype(str).str.startswith("Q"), "qual", "main")},
                        index=m.index)
    linked = S.Stage0Linker().link(rows)
    ids = set(linked["match_id"].dropna())
    counts = {"rows_timed_both": int(len(m)), "linked": int(linked["match_id"].notna().sum()),
              "by_series": m.groupby("series_id").size().to_dict()}
    return ids, counts


def fs_record_timed(r: dict) -> bool:
    """Both players' Average 1st serve speed is a real reading: Flashscore writes "0 km/h" where it has none (most
    2024 records), so a value outside the shot-level adapters' 40-270 km/h range counts as missing."""
    if plausible(r.get("home_average_1st_serve_speed")) and plausible(r.get("away_average_1st_serve_speed")):
        return True
    return fs_both(r.get("stats_detail_json") or "")


def fs_both(stats_json: str) -> bool:
    if not FS_SPEED.search(stats_json):
        return False
    try:
        items = json.loads(stats_json)
    except ValueError:
        return False
    period = None
    for it in items:
        period = it.get("SE", period)
        if period == "Match" and str(it.get("SG", "")).lower() == "average 1st serve speed":
            return plausible(it.get("SH")) and plausible(it.get("SI"))
    return False


def plausible(v) -> bool:
    return 40.0 < num(v) <= 270.0


def num(v) -> float:
    m = re.search(r"[\d.]+", str(v or ""))
    return float(m.group(0)) if m else 0.0


# ------------------------------------------------------------------------------------------------
# Scenarios and the feature

def scenario_flags(rows: pd.DataFrame, mantd: set | None) -> pd.DataFrame:
    """One boolean column per scenario: the player-match is timed under it (cumulative). Without a ManTennisData
    copy, S1b equals S1."""
    held = held_sides()
    key = rows["match_id"] + "|" + rows["side"]
    hk = set(held["match_id"] + "|" + held["side"])
    f = pd.DataFrame(index=rows.index)
    f["S0_held"] = key.isin(hk).to_numpy()
    log("Infosys key statistics")
    ks = infosys_keystats()
    log(f"  {len(ks)} matches; Australian Open statistics")
    ao = ausopen_stats()
    log(f"  {len(ao)} matches; Flashscore crawl")
    fs = flashscore_crawl()
    log(f"  {len(fs)} matches")
    extra = ks | ao | fs
    f["S1_on_disk"] = f["S0_held"] | rows["match_id"].isin(extra).to_numpy()
    f["S1b_mantd"] = f["S1_on_disk"] | rows["match_id"].isin(mantd or set()).to_numpy()
    atp_tour = rows["tour"].eq("atp") & rows["level"].isin(TOUR_LEVELS) & rows["year"].between(2025, 2026)
    f["S2_atp_files"] = f["S1b_mantd"] | atp_tour.to_numpy()
    slams = (rows["slam"].eq("AO") & rows["year"].eq(2025)) | (rows["slam"].eq("RG") & rows["year"].between(2025, 2026))
    f["S3_slams"] = f["S2_atp_files"] | slams.to_numpy()
    wta_tour = rows["tour"].eq("wta") & rows["level"].isin(TOUR_LEVELS) & rows["year"].between(2025, 2026)
    f["S4_wta"] = f["S3_slams"] | wta_tour.to_numpy()
    src = pd.Series("", index=rows.index)
    src[rows["match_id"].isin(fs).to_numpy()] = "flashscore"
    src[rows["match_id"].isin(ao).to_numpy()] = "ausopen_stats"
    src[rows["match_id"].isin(ks).to_numpy()] = "infosys_keystats"
    f["s1_source"] = np.where(f["S0_held"], "held", src)
    return f


def feature_presence(rows: pd.DataFrame, flag: np.ndarray, targets: np.ndarray) -> np.ndarray:
    """For each target row, whether the player has a timed earlier match in the 14-day window (speed_build's rules,
    presence only: its window_feature with every timed match weighted 1)."""
    r = rows.assign(spd1_n=flag.astype(float), spd1_d=flag.astype(float))
    win = SB.window_feature(r, targets, "spd1_n")
    return (win["n2"] > 0).to_numpy()


def frame_mask(rows: pd.DataFrame) -> pd.Series:
    return rows["level"].isin(MAIN_TOUR) & ~rows["qualifying"].astype(bool) & rows["year"].between(2015, 2026)


def window_of(year: pd.Series) -> np.ndarray:
    return np.select([year.between(2015, 2021), year.between(2022, 2024), year.between(2025, 2026)],
                     ["2015-21", "2022-24", "2025-26"], "")


def group_of(rows: pd.DataFrame) -> np.ndarray:
    lv, q = rows["level"], rows["qualifying"].astype(bool)
    return np.select([lv.eq("GS") & ~q, lv.eq("GS") & q, lv.isin(TOUR_LEVELS) & ~q, lv.isin(TOUR_LEVELS) & q,
                      lv.eq("CH") & ~q, lv.eq("CH") & q, lv.eq("ITF"), lv.eq("TEAM")],
                     ["Slam main", "Slam qualifying", "Tour main", "Tour qualifying", "Challenger main",
                      "Challenger qualifying", "ITF", "Team"], "other")


def power_one_sided(n: int, beta: float = 0.09, pq: float = 0.19, var: float = 1.06) -> float:
    """Power of a two-sided 5% Wald test of beta > 0 on n matches, with the pre-registration's standard error
    1 / sqrt(n p(1-p) var(x)) (speed_prereg.md section 8)."""
    from math import erf, sqrt
    if n <= 0:
        return 0.0
    se = 1.0 / sqrt(n * pq * var)
    z = beta / se - 1.959964
    return 0.5 * (1.0 + erf(z / sqrt(2.0)))


def polymarket_tiers() -> list[dict]:
    """Polymarket's in-window tennis events and volume by its own tier bucket (context for where speed can exist)."""
    e = pd.read_parquet(POLY, columns=["in_sport_window", "bucket", "bucket_tour", "volume"])
    e = e[e["in_sport_window"].astype(str).str.lower().isin(["true", "1"])]
    e["volume"] = pd.to_numeric(e["volume"], errors="coerce").fillna(0.0)
    g = e.groupby(["bucket", "bucket_tour"]).agg(events=("bucket", "size"), volume_usd=("volume", "sum")).reset_index()
    g["volume_share"] = (g["volume_usd"] / g["volume_usd"].sum()).round(4)
    return g.sort_values("volume_usd", ascending=False).to_dict(orient="records")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mantd", type=Path, default=None,
                    help="folder holding msolonskyi/ManTennisData's atp/matches_2021.csv ... matches_2026.csv and "
                         "tournaments.csv (not held by the project; scenario S1b is measured only with it)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    log("Stage 0 rows and the clock")
    rows = player_rows()
    mantd, mantd_counts = (None, None)
    if args.mantd is not None:
        log(f"ManTennisData from {args.mantd}")
        mantd, mantd_counts = mantd_matches(args.mantd)
        log(f"  {mantd_counts}")
    flags = scenario_flags(rows, mantd)

    # 1. match-level availability: a match counts when both sides are timed
    log("match-level availability")
    mrows = rows.assign(grp=group_of(rows), **{s: flags[s].to_numpy() for s in SCENARIOS},
                        s1_source=flags["s1_source"].to_numpy())
    both = mrows.groupby("match_id").agg(tour=("tour", "first"), year=("year", "first"), grp=("grp", "first"),
                                         slam=("slam", "first"), **{s: (s, "all") for s in SCENARIOS[:3]},
                                         s1_source=("s1_source", "first"))
    both["added_on_disk"] = both["S1_on_disk"] & ~both["S0_held"]
    cm = (both.groupby(["tour", "grp", "year"])
          .agg(matches=("S0_held", "size"), held=("S0_held", "sum"), with_on_disk=("S1_on_disk", "sum"),
               with_mantd=("S1b_mantd", "sum"),
               added_infosys_keystats=("s1_source", lambda x: int((x == "infosys_keystats").sum())),
               added_ausopen_stats=("s1_source", lambda x: int((x == "ausopen_stats").sum())),
               added_flashscore=("s1_source", lambda x: int((x == "flashscore").sum())))
          .reset_index())
    cm["held_share"] = (cm["held"] / cm["matches"]).round(4)
    cm["with_on_disk_share"] = (cm["with_on_disk"] / cm["matches"]).round(4)
    cm["with_mantd_share"] = (cm["with_mantd"] / cm["matches"]).round(4)
    cm.to_csv(OUT / "coverage_matches.csv", index=False)
    slam_ed = (both[both["grp"].eq("Slam main")].groupby(["tour", "slam", "year"])
               .agg(matches=("S0_held", "size"), held=("S0_held", "sum"), with_on_disk=("S1_on_disk", "sum"))
               .reset_index())
    slam_ed.to_csv(OUT / "coverage_slam_editions.csv", index=False)

    # 2. the feature on the main-tour main-draw frame
    log("feature presence on the frame")
    fm = frame_mask(rows)
    targets = rows.index[fm].to_numpy()
    pres = {s: feature_presence(rows, flags[s].to_numpy(), targets) for s in SCENARIOS}
    side = rows.loc[targets, ["match_id", "side", "tour", "year", "level", "slam", "obs"]].copy()
    for s in SCENARIOS:
        side[s] = pres[s]
    feat = side.groupby("match_id").agg(tour=("tour", "first"), year=("year", "first"), level=("level", "first"),
                                        slam_name=("slam", "first"), obs=("obs", "first"),
                                        **{s: (s, "all") for s in SCENARIOS})
    feat["window"] = window_of(feat["year"])
    feat["slam"] = feat["level"].eq("GS")
    feat.reset_index().to_parquet(OUT / "coverage_feature_matches.parquet", index=False)
    # the Polymarket window of the tennis-data audit: 10 Sep 2025 - 10 Sep 2026, by the best-estimate match day
    lo, hi = (pd.Timestamp(d).value // 86_400_000_000_000 for d in ("2025-09-10", "2026-09-10"))
    pw = feat[feat["obs"].between(lo, hi)]
    poly_window = (pw.groupby(["tour", "slam"]).agg(frame=("S0_held", "size"), **{s: (s, "sum") for s in SCENARIOS})
                   .reset_index().to_dict(orient="records"))
    cf = feat.groupby(["tour", "window", "slam"]).agg(frame=("S0_held", "size"),
                                                      **{s: (s, "sum") for s in SCENARIOS}).reset_index()
    by_year = feat.groupby(["tour", "year", "slam"]).agg(frame=("S0_held", "size"),
                                                         **{s: (s, "sum") for s in SCENARIOS}).reset_index()
    cf.to_csv(OUT / "coverage_feature.csv", index=False)
    by_year.to_csv(OUT / "coverage_feature_by_year.csv", index=False)

    # 3. validation against the study, on its own frame (walk-forward table, 2015-24 only)
    log("validation against speed_build on the walk-forward frame (to 2024)")
    wf = pd.read_parquet(WF, columns=["match_id", "year"], filters=[("year", "<=", 2024)])
    v = feat[feat.index.isin(set(wf["match_id"])) & feat["year"].between(2015, 2024)]
    val = v.groupby(["tour", "window", "slam"]).agg(frame=("S0_held", "size"), x_present=("S0_held", "sum"))
    study = json.loads((ROOT / "data" / "studies" / "point_sequence" / "speed_build_summary.json").read_text())
    st = pd.DataFrame(study["coverage"])
    st["window"] = st["window"].map({"discovery": "2015-21", "replication": "2022-24"})
    val = val.reset_index().merge(st[["tour", "window", "slam", "frame_matches", "x_raw"]],
                                  on=["tour", "window", "slam"], how="left")

    # 4. what each scenario buys for the men's 2025-26 holdout test
    men = cf[(cf["tour"] == "atp") & (cf["window"] == "2025-26")]
    hold = {s: int(men[s].sum()) for s in SCENARIOS}
    power = {s: round(power_one_sided(n), 3) for s, n in hold.items()}
    summary = {
        "built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "reads_results": False,
        "on_disk_unused_matches": {k: int(v) for k, v in both.loc[both["added_on_disk"], "s1_source"]
                                   .value_counts().items()},
        "mantd": None if mantd_counts is None else {
            "source": "github.com/msolonskyi/ManTennisData atp/matches_2021-2026.csv, tournaments.csv",
            "folder": str(args.mantd), **mantd_counts,
            "stage0_matches_timed": len(mantd),
            "added_beyond_on_disk": int((both["S1b_mantd"] & ~both["S1_on_disk"]).sum())},
        "men_2025_26_frame_matches": int(men["frame"].sum()),
        "men_2025_26_with_feature": hold,
        "men_2025_26_power_beta_0.09": power,
        "power_note": "two-sided 5% Wald test, SE = 1/sqrt(n * 0.19 * 1.06) as speed_prereg.md section 8; beta 0.09 "
                      "is the 2022-24 replication estimate (probably inflated)",
        "validation_vs_speed_build": val.to_dict(orient="records"),
        "polymarket_window_frame_with_feature": poly_window,
        "polymarket_in_window_tiers": polymarket_tiers(),
    }
    (OUT / "coverage_summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n", encoding="utf-8")
    log("validation:\n" + val.to_string(index=False))
    log("feature coverage:\n" + cf.to_string(index=False))
    log(f"men 2025-26: {hold}; power {power}")


if __name__ == "__main__":
    main()
