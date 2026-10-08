"""The Slam box-score override table (docs/decisions/2026-10-06-slam-box-scores.md): every Stage 0 match of
Wimbledon and the US Open 2026, whose box score Stage 0 takes from Tennis My Life, gets the official feed's whole
box score; where TML's score is cut short, the feed's score and duration too.

Rows are tied by identity, not by score: the match-timing link file (slam_feeds.parquet) gives each feed record's
Stage 0 match, Stage 0 gives the TML row behind it, and Stage 0's own normalise() gives that row's key (tour,
normalised tournament id, round, the name keys of TML's winner and loser), which stage0_build.apply_box_overrides
looks up. Counts are oriented to TML's winner and loser, by who won, with the surnames checked.

Checks, each written to the summary; the table is written only when the first three hold:
    every Stage 0 match of the two events resolves to one feed record and one TML row, and every key is unique
    every winner's surname agrees between TML and the feed
    the feed's counts pass Stage 0's checks (B0-B4, B6-B8; B5 and B9 under the feed's score)
    the feed's statistics equal its own point stream (ServeNumber 0 double fault, 1 first serve, 2 second serve;
    Ace and DoubleFault name the player), reported per count

Writes data/studies/data_continuity/slam_box_overrides.csv and slam_box_overrides.json.
Run: ./python.sh src/eda/data_continuity/slam_overrides.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.data_continuity import sources as R  # noqa: E402
from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

YEAR = "2026"
SITES = {"wimbledon": "wimbledon_feed", "usopen": "usopen_feed"}
OUT_CSV = K.OUT / "slam_box_overrides.csv"
OUT_JSON = K.OUT / "slam_box_overrides.json"
COUNT_NAMES = list(B.C.BOX_SOURCE_NAMES.items())     # (contract name, Sackmann column suffix)


def feed_score(sets_json: str, winner_team: int, status: str) -> str:
    """Sackmann's score form from the feed's set list, written from the winner's side: a tiebreak set carries the
    tiebreak points of the player who lost the set, "6-7(6)"; a retirement ends with RET."""
    parts = []
    for pair in json.loads(sets_json or "[]"):
        a, b = pair
        if a.get("score") is None or b.get("score") is None:
            continue
        w, l = (a, b) if winner_team == 1 else (b, a)
        text = f"{w['score']}-{l['score']}"
        if w.get("tiebreak") is not None and l.get("tiebreak") is not None:
            set_loser = w if int(w["score"]) < int(l["score"]) else l
            text += f"({set_loser['tiebreak']})"
        parts.append(text)
    if re.search(r"retir", str(status), re.I):
        parts.append("RET")
    return " ".join(parts)


def feed_minutes(duration: str) -> str:
    m = re.fullmatch(r"\s*(\d+):(\d{2})\s*", str(duration or ""))
    return str(int(m.group(1)) * 60 + int(m.group(2))) if m else ""


def games_in(sets_json: str) -> tuple[int, int]:
    """Games in the feed's set list and how many sets ended in a tiebreak."""
    games = tbs = 0
    for a, b in json.loads(sets_json or "[]"):
        if a.get("score") is None or b.get("score") is None:
            continue
        games += int(a["score"]) + int(b["score"])
        tbs += int(a.get("tiebreak") is not None and b.get("tiebreak") is not None)
    return games, tbs


def point_counts(site: str) -> pd.DataFrame:
    """The six counts the point stream gives, per feed record and team (team_1, team_2)."""
    p = pd.read_parquet(K.DUMP / "points" / site / "points.parquet",
                        columns=["year", "event", "match_id", "PointServer", "ServeNumber", "PointWinner", "Ace",
                                 "DoubleFault"], filters=[("year", "==", YEAR)])
    p = p[p["PointServer"].isin(["1", "2"])]
    p["source_key"] = site + ":" + p["year"] + "/" + p["event"] + "/" + p["match_id"]
    rows = []
    for team in ("1", "2"):
        s = p[p["PointServer"].eq(team)]
        won = s["PointWinner"].eq(team)
        g = pd.DataFrame({"source_key": s["source_key"], "svpt": 1, "first_in": s["ServeNumber"].eq("1"),
                          "first_won": s["ServeNumber"].eq("1") & won, "second_won": s["ServeNumber"].eq("2") & won})
        g = g.groupby("source_key").sum()
        g["df"] = p[p["DoubleFault"].eq(team)].groupby("source_key").size()
        g["ace"] = p[p["Ace"].eq(team)].groupby("source_key").size()
        rows.append(g.fillna(0).astype(int).reset_index().assign(side=f"team_{team}"))
    return pd.concat(rows, ignore_index=True)


def surname_ok(tml_name: str, feed_display: str) -> bool:
    """The feed's surname ("J. Sinner", "A. De Minaur") within TML's full name, accents and case ignored."""
    feed = S.norm(re.sub(r"^\s*[A-Z][a-z]?\.\s*", "", str(feed_display or ""))).split()
    tml = set(S.norm(tml_name).split())
    return bool(feed) and all(t in tml for t in feed)


def main() -> int:
    m, players = K.load_stage0()
    links = pd.read_parquet(K.LINKS / "slam_feeds.parquet", columns=["match_id", "source_key", "score_agrees"])
    links = links[links["source_key"].str.match(rf"^({'|'.join(SITES)}):{YEAR}/")]
    feed = R.slam_feeds(tuple(SITES))
    feed = feed[feed["source_key"].isin(set(links["source_key"]))]
    meta = []
    receipts = {}
    for site in SITES:
        mm = pd.read_parquet(K.DUMP / "points" / site / "matches.parquet",
                             columns=["year", "event", "match_id", "entry.winner", "entry.scores.sets", "entry.duration",
                                      "entry.status", "entry.team1.displayNameA", "entry.team2.displayNameA"])
        mm = mm[mm["year"].astype(str) == YEAR]
        mm["source_key"] = site + ":" + mm["year"].astype(str) + "/" + mm["event"] + "/" + mm["match_id"]
        mm["site"] = site
        meta.append(mm)
        for line in (K.ROOT / "data" / "raw" / "point_sources" / site / "_receipts.jsonl").read_text(
                encoding="utf-8", errors="replace").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(r.get("name", "")).startswith(f"stats/{YEAR}/") and r.get("sha256") and not r.get("error"):
                receipts[(site, r["name"].split("/")[-1])] = r
    meta = pd.concat(meta, ignore_index=True).set_index("source_key")

    # Stage 0's matches of the two events, and the TML row behind each, normalised as stage0_build does
    raw = B.load_raw()
    df = B.normalise(raw)
    tm = df[df["source"].eq("tml")].set_index(["_source_file", "_row"])
    s0 = m[m["match_id"].isin(set(links["match_id"]))].copy()
    summary: dict = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
                     "stage0_matches": int(len(s0)), "stage0_sources": s0["source"].value_counts().to_dict()}
    problems = []
    if not s0["source"].eq("tml").all():
        problems.append(f"{int((~s0['source'].eq('tml')).sum())} matches are not TML rows")
    per_match = links.groupby("match_id")["source_key"].nunique()
    if (per_match != 1).any() or links["source_key"].duplicated().any():
        problems.append("a Stage 0 match links to more than one feed record, or the reverse")

    out_rows, checks = [], []
    for row in s0.itertuples():
        key = links.loc[links["match_id"].eq(row.match_id)].iloc[0]
        sk = key["source_key"]
        site = sk.split(":")[0]
        t = tm.loc[(row.source_file, int(row.source_row))]
        if isinstance(t, pd.DataFrame):
            problems.append(f"{row.match_id}: several TML rows at {row.source_file}#{row.source_row}")
            continue
        info = meta.loc[sk]
        winner_team = int(info["entry.winner"]) if str(info["entry.winner"]) in ("1", "2") else None
        f = feed[feed["source_key"].eq(sk)].set_index("side")
        if winner_team is None or len(f) != 2:
            checks.append({"match_id": row.match_id, "source_key": sk, "skipped": "no winner or no box score in the feed"})
            continue
        fw, fl = f.loc[f"team_{winner_team}"], f.loc[f"team_{3 - winner_team}"]
        names_ok = surname_ok(t["winner_name"], info[f"entry.team{winner_team}.displayNameA"]) and \
            surname_ok(t["loser_name"], info[f"entry.team{3 - winner_team}.displayNameA"])
        rec = {"box_source": SITES[site], "feed_key": sk, "stage0_match_id": row.match_id, "tour": t["tour"],
               "tid": t["tid"], "round": t["round"], "winner_key": t["wkey"], "loser_key": t["lkey"],
               "winner_name": t["winner_name"], "loser_name": t["loser_name"]}
        for side, src in (("w", fw), ("l", fl)):
            for name, col in COUNT_NAMES:
                v = src[name]
                rec[f"{side}_{col}"] = "" if pd.isna(v) else str(int(v))
        rec["score"], rec["minutes"] = "", ""
        if not bool(key["score_agrees"]):
            rec["score"] = feed_score(info["entry.scores.sets"], winner_team, info["entry.status"])
            rec["minutes"] = feed_minutes(info["entry.duration"])
        rc = receipts.get((site, sk.split("/")[-1]), {})
        rec["feed_sha256"], rec["feed_retrieved_at"] = rc.get("sha256", ""), rc.get("retrieved_at", "")
        rec["tml_score"] = t["score"]
        out_rows.append(rec)
        # Stage 0's checks on the feed's counts, under the feed's score
        games, tbs = games_in(info["entry.scores.sets"])
        box = pd.DataFrame([{c: fw[c] for c in K.COUNTS}, {c: fl[c] for c in K.COUNTS}])
        fails = K.invariant_failures(K.finish(box)).any(axis=0)
        sv = box["sv_gms"].sum()
        b5 = not (abs(sv - (games - tbs)) <= 1 or abs(sv - games) <= 1) if box["sv_gms"].notna().all() else False
        b9 = bool(box["svpt"].sum() < 4.5 * (games - tbs)) and not re.search(r"retir", str(info["entry.status"]), re.I)
        checks.append({"match_id": row.match_id, "source_key": sk, "names_ok": names_ok,
                       "row_checks_failed": ";".join(fails[fails].index), "b5_failed": b5, "b9_failed": b9})
    ov = pd.DataFrame(out_rows)
    ch = pd.DataFrame(checks)
    if ov["feed_key"].duplicated().any() or (ov["tour"] + ov["tid"] + ov["round"] + ov["winner_key"] + ov["loser_key"]).duplicated().any():
        problems.append("two overrides share a feed record or a TML key")
    keys = df[df["source"].eq("tml")]
    keycount = (keys["tour"] + "|" + keys["tid"] + "|" + keys["round"] + "|" + keys["wkey"] + "|" + keys["lkey"]).value_counts()
    want = ov["tour"] + "|" + ov["tid"] + "|" + ov["round"] + "|" + ov["winner_key"] + "|" + ov["loser_key"]
    if (want.map(keycount).fillna(0) != 1).any():
        problems.append(f"{int((want.map(keycount).fillna(0) != 1).sum())} keys do not name exactly one TML row")
    if "names_ok" in ch and (~ch["names_ok"].fillna(True)).any():
        problems.append(f"{int((~ch['names_ok'].fillna(True)).sum())} surname mismatches")
    bad_checks = ch[(ch.get("row_checks_failed", pd.Series(dtype=str)).fillna("") != "")
                    | ch.get("b5_failed", False).fillna(False) | ch.get("b9_failed", False).fillna(False)]
    if len(bad_checks):
        problems.append(f"{len(bad_checks)} feed box scores fail Stage 0's checks under the feed's score")

    # the feed's statistics against its own point stream
    pts = pd.concat([point_counts(site) for site in SITES], ignore_index=True)
    fs = feed[["source_key", "side"] + ["svpt", "first_in", "first_won", "second_won", "df", "ace"]]
    j = fs.merge(pts, on=["source_key", "side"], suffixes=("_stats", "_points"))
    j["event"] = j["source_key"].str.split(":").str[0] + "/" + j["source_key"].str.split("/").str[1]
    agree = {c: j.assign(ok=j[f"{c}_stats"].eq(j[f"{c}_points"])).groupby("event")["ok"].mean().round(4).to_dict()
             for c in ["svpt", "first_in", "first_won", "second_won", "df", "ace"]}
    summary.update({
        "overrides": int(len(ov)), "by_source": ov["box_source"].value_counts().to_dict() if len(ov) else {},
        "skipped": ch[ch.get("skipped", pd.Series(dtype=str)).notna()].to_dict("records") if "skipped" in ch else [],
        "scores_replaced": ov.loc[ov["score"].ne(""), ["stage0_match_id", "winner_name", "loser_name", "tml_score",
                                                       "score", "minutes"]].to_dict("records"),
        "surname_mismatches": int((~ch["names_ok"].fillna(True)).sum()) if "names_ok" in ch else None,
        "feed_box_scores_failing_stage0_checks": bad_checks.to_dict("records"),
        "statistics_equal_point_stream_share_by_event": agree,
        "player_rows_compared_with_point_stream": int(len(j)),
        "problems": problems,
    })
    K.write_json(OUT_JSON, summary)
    if problems:
        print("NOT WRITTEN:", problems)
        return 1
    cols = (["box_source", "feed_key", "stage0_match_id", "tour", "tid", "round", "winner_key", "loser_key",
             "winner_name", "loser_name"] + B.OVERRIDE_COUNTS + ["score", "minutes", "tml_score", "feed_sha256",
                                                                 "feed_retrieved_at"])
    ov[cols].sort_values(["box_source", "feed_key"]).to_csv(OUT_CSV, index=False)
    print(f"wrote {len(ov)} overrides; scores replaced: {len(summary['scores_replaced'])}; "
          f"point-stream agreement by event: {agree['first_in']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
