"""The lower-level feed (13 Oct 2026; docs/studies/data_gaps_2026/): the levels the training history lost in 2026, kept
current from the newest downloads as dated snapshots of an accepted feed, which every build and prediction run merges
(src/eda/current_best_model/additions.py: accepted.json's "feeds").

Why. Sackmann's files ended in early June 2026, and since then Stage 0 has read new results only from Tennis My Life,
which publishes no ITF, women's qualifying, WTA 125 or men's Challenger qualifying; Sackmann's own women's file had
already dropped ITF qualifying with the 2025 season. The replacements were downloaded (the WTA API, the WTA website's
records, TennisLive's listings, the ITF live-data API, SofaScore, TDI) but nothing turned them into Stage 0 rows, except
one hand-made package (men's 2026 Challenger data, 10 Oct). The owner, 13 Oct 2026: "Make sure our pipeline is set up
to automatically integrate this so this doesnt happen again."

The scope (SCOPE): the levels a feed lost, each from the last week the frozen reference holds of it (inclusive; the
builder links what the reference already holds, so nothing is added twice):
    atp CH   2026-01-01 .. 2026-10-05   the 10 Oct package's men's Challenger data; Tennis My Life carries the main draws
                                         after the reference, so they stop at its last week
    atp CHQ  2026-01-01                 the 10 Oct package's; Tennis My Life has no Challenger qualifying
    atp ITF  2026-06-01
    wta CH, CHQ, ITF  2026-06-01;  wta TQ 2026-05-18;  wta GSQ 2026-01-19;  wta ITFQ 2024-12-16
Men's ITF qualifying stays out: Stage 0 never held it in any season. Main-tour levels stay out: Tennis My Life carries
them, and a main-tour repair is decided on its own evidence.

One command, --run, in order (each step its own process, its output in the run's log):
    1. build     the level-evidence study's candidate builder (src/eda/lower_level_evidence/candidate_stage0.py), every
                 source, against the frozen reference, into C:/Users/zerom/tnr_feed/candidates/<label>/
                 (TENNIS_FEED_CANDIDATES; --candidates-dir; the first, of 13 Oct 2026, in
                 data/studies/data_gaps_2026/feed/candidates/)
    2. checks    its checks (structure, Stage 0's rules, duplicates, history)
    3. identity  --hand: the hand check's verdicts must already be in the folder (the first snapshot); --auto: rule
                 verdicts on the builder's samples (auto_verdicts), written as rule verdicts, and the run stops when
                 more of them are unsure than the screen allows (SCREEN)
    4. ready     the builder's manifest and READY.txt
    5. derive    the SCOPE (--keep-since), then its checks and READY
    6. snapshot  additions.py --package <derived> --name lower_level_feed/<date>
    7. check     additions.py --check-against <derived> --only lower_level_feed/<date>: on the frozen reference the merge
                 must give the derived candidate's own tables
    8. advance   with --advance: additions.py --set-feed lower_level_feed/<date> (the policy of 13 Oct: a snapshot that
                 passes every step becomes current); men_2026_ch_chq is retired once the feed holds all of it. Refused
                 until the feed's first snapshot is accepted by hand, after its harm check
    9. record    a line in data/studies/data_gaps_2026/feed/runs.jsonl
Exit codes: 0 done; 4 the identity screen stopped the run; 5 a check failed; 1 another failure. The previous snapshot
stays current whenever a run stops.

Run: ./python.sh src/eda/data_gaps_2026/feed.py --run --auto --advance        (the weekly job)
     ./python.sh src/eda/data_gaps_2026/feed.py --run --hand --label <label>   (after the hand check of <label>)
     ./python.sh src/eda/data_gaps_2026/feed.py --auto-verdicts <candidate folder>
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "studies" / "data_gaps_2026" / "feed"
# the candidates (about 350 MB a week, rebuildable from the raw downloads) live outside data/studies, which every
# template build copies whole into its sandbox; the first ones (13 Oct 2026) are in OUT / "candidates"
CANDIDATES = Path(os.environ.get("TENNIS_FEED_CANDIDATES", "C:/Users/zerom/tnr_feed/candidates"))
RUNS = OUT / "runs.jsonl"
STATUS_LOG = OUT / "status.log"
FEED = "lower_level_feed"
PACKAGE = "men_2026_ch_chq"                           # the 10 Oct package the feed supersedes once it holds all of it
DECISION = "docs/decisions/2026-10-13-lower-level-feed.md"
BUILDER = "src/eda/lower_level_evidence/candidate_stage0.py"
ADDITIONS = "src/eda/current_best_model/additions.py"
SCOPE = ["atp:CH:2026-01-01:2026-10-05", "atp:CHQ:2026-01-01", "atp:ITF:2026-06-01",
         "wta:CH:2026-06-01", "wta:CHQ:2026-06-01", "wta:ITF:2026-06-01", "wta:TQ:2026-05-18", "wta:GSQ:2026-01-19",
         "wta:ITFQ:2024-12-16"]
# box scores only from sources that count as Stage 0 does (measured on the 9 Oct candidate's shared matches: the WTA API
# 99-100% at WTA 125 and tour qualifying, TennisLive's pages 100% at Challengers and tour qualifying, TDI 99.8-100% on
# its published counts); SofaScore's are left out (first serves in equal in 43-54% of rows)
BOX_SOURCES = "wta_api,itf_live,tdi,tennislive_pages"
# ... except TennisLive's pages at ITF, which miss points in about 15% of matches (serve points 1.8 lower on average,
# almost never higher; 282 matches shared with Sackmann's ITF box scores)
BOX_EXCLUDE = "tennislive_pages:ITF,tennislive_pages:ITFQ"
# results only where the history never held a box score (women's ITF qualifying) or the only source counts differently
# (the WTA API's Slam qualifying box scores: 4-37% of counts equal to Stage 0's)
RESULTS_ONLY = "wta:ITFQ,wta:GSQ"
# the rule screen: per kind, the largest share of a source's sampled rows that may be "unsure" (only sources with at
# least SCREEN_MIN rows sampled are judged); calibrated on the hand-checked candidate of 9 Oct (C0_now), where the rules
# give no "unsure" the hand check called wrong unnoticed (calibrate_screen)
SCREEN = {"links": 0.25, "players": 0.35}
SCREEN_MIN = 10


def log(msg: str) -> None:
    print(f"[feed {dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


def step(name: str, args: list[str], logf: Path) -> int:
    """One step as its own process (the tennis environment's Python), its output appended to the run's log."""
    log(f"{name}: {' '.join(args)}")
    with logf.open("a", encoding="utf-8") as fh:
        fh.write(f"=== {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')} {name}: {' '.join(args)}\n")
        fh.flush()
        code = subprocess.run([sys.executable, *args], cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
    log(f"{name}: exit {code}")
    return code


# ------------------------------------------------------------------------------------------------ the rule verdicts
def _day(s) -> pd.Timestamp:
    return pd.to_datetime(s, errors="coerce")


def auto_verdicts(cand: Path) -> pd.DataFrame:
    """Rule verdicts on the builder's identity samples (identity_sample_*.csv), in the hand check's file format
    (identity_verdicts.csv: kind, source, route, row, verdict, note) plus `by` = "rule". A rule says "right" only where
    the names agree without help; everything else is "unsure", never "wrong" (a rule cannot tell a split from a twin):
        links         both names graded together >= 5 (srcc_common.name_grade: 3 the same full name, 2 one name inside
                      the other or a shared surname and initial), the source's day within 14 days of Stage 0's tournament
                      date, and the same round where both give one
        players       name grade >= 2 and no country against it
        new_ids       no reference player of the tour with the same last name
        repair_moves  the two names equal once spaces and hyphens are dropped, and the same country
    It is a screen for gross failures (a source that changes how it writes names), weaker than the hand check."""
    rows = []

    def add(kind, src, route, i, ok, note):
        rows.append({"kind": kind, "source": src, "route": route, "row": i, "verdict": "right" if ok else "unsure",
                     "note": note, "by": "rule"})

    p = cand / "identity_sample_links.csv"
    if p.exists():
        lk = pd.read_csv(p)
        for i, r in lk.iterrows():
            days = abs((_day(r["src_day"]) - _day(r["s0_date"])).days) if pd.notna(_day(r["src_day"])) and pd.notna(
                _day(r["s0_date"])) else 99
            same_round = pd.isna(r["src_round"]) or pd.isna(r["s0_round"]) or str(r["src_round"]) == str(r["s0_round"])
            ok = r["name_grade"] >= 5 and days <= 14 and same_round
            add("links", r["source"], "", i, ok, f"name grade {r['name_grade']}, {days} days, round "
                                                f"{'agrees' if same_round else 'differs'}")
    p = cand / "identity_sample_players.csv"
    if p.exists():
        pl = pd.read_csv(p)
        for i, r in pl.iterrows():
            cc = str(r["src_country"]) if pd.notna(r["src_country"]) else ""
            country_ok = not cc or pd.isna(r["s0_country"]) or cc in str(r["s0_country"]).split(";")
            ok = r["name_grade"] >= 2 and country_ok
            add("players", r["source"], r["route"], i, ok, f"name grade {r['name_grade']}, country "
                                                          f"{'agrees or unknown' if country_ok else 'differs'}")
    p = cand / "identity_sample_new_ids.csv"
    if p.exists():
        nw = pd.read_csv(p)
        for i, r in nw.iterrows():
            same = r["reference_same_last_name"]
            ok = pd.isna(same) or not str(same).strip()
            add("new_ids", r["source"], "new", i, ok, "no reference player with this last name" if ok else
                f"reference players with this last name: {same}")
    p = cand / "identity_sample_repair_moves.csv"
    if p.exists():
        rm = pd.read_csv(p)
        flat = (lambda s: "".join(ch for ch in str(s).lower() if ch.isalnum()))
        for i, r in rm.iterrows():
            ok = flat(r["from_name"]) == flat(r["to_name"]) and str(r["from_c"]) == str(r["to_c"])
            add("repair_moves", r["src"], r["route"], i, ok, "same name and country" if ok else "names or countries "
                                                                                                "differ")
    return pd.DataFrame(rows, columns=["kind", "source", "route", "row", "verdict", "note", "by"])


def screen(v: pd.DataFrame) -> dict:
    """Whether the rule verdicts pass: per kind in SCREEN and source with at least SCREEN_MIN rows, the unsure share."""
    out = {"pass": True, "unsure_share": {}}
    for kind, limit in SCREEN.items():
        for src, g in v[v["kind"].eq(kind)].groupby("source"):
            if len(g) < SCREEN_MIN:
                continue
            share = float(g["verdict"].ne("right").mean())
            out["unsure_share"][f"{kind}|{src}"] = round(share, 3)
            if share > limit:
                out["pass"] = False
    return out


def calibrate_screen(hand: Path) -> dict:
    """The rule verdicts against a hand-checked candidate's own verdicts (the same samples): how often a rule says
    'right' where the hand said 'wrong' (the screen's blind spot), and the unsure shares it would have seen."""
    rule = auto_verdicts(hand)
    h = pd.read_csv(hand / "identity_verdicts.csv")
    j = rule.merge(h, on=["kind", "source", "row"], suffixes=("_rule", "_hand"), how="inner")
    return {"compared": int(len(j)),
            "rule_right_hand_wrong": int((j["verdict_rule"].eq("right") & j["verdict_hand"].eq("wrong")).sum()),
            "rule_unsure_hand_right": int((j["verdict_rule"].ne("right") & j["verdict_hand"].eq("right")).sum()),
            "by_kind": j.groupby("kind").apply(lambda g: {"n": int(len(g)),
                                                          "rule_unsure": int(g["verdict_rule"].ne("right").sum()),
                                                          "hand_wrong": int(g["verdict_hand"].eq("wrong").sum())},
                                               include_groups=False).to_dict(),
            "screen": screen(rule)}


# ------------------------------------------------------------------------------------------------ the run
def run(label: str, mode: str, advance: bool) -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    cand, gaps = CANDIDATES / label, CANDIDATES / f"{label}_gaps"
    logf = OUT / f"run_{label}.log"
    snap = label[1:] if label.startswith("F") else label
    rec = {"label": label, "mode": mode, "advance": advance, "started_at": dt.datetime.now(dt.timezone.utc)
           .isoformat(timespec="seconds"), "scope": SCOPE, "steps": {}}
    sl = ["--status-log", str(STATUS_LOG)]

    def done(code: int, why: str) -> int:
        rec.update(exit=code, why=why, minutes=round((time.time() - t0) / 60, 1),
                   finished_at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
        with RUNS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
        log(f"done: exit {code} ({why})")
        return code

    if not (cand / "READY.txt").exists():
        if not (cand / "stage0_matches.parquet").exists():
            if step("build", [BUILDER, "--label", label, "--out", str(cand), "--box-sources", BOX_SOURCES,
                              "--box-exclude", BOX_EXCLUDE] + sl, logf):
                return done(1, "the build failed")
        rec["steps"]["build"] = "done"
        chk = cand / "checks.json"
        passed = chk.exists() and json.loads(chk.read_text(encoding="utf-8")).get("pass") \
            and chk.stat().st_mtime > (cand / "stage0_matches.parquet").stat().st_mtime
        if not passed and step("checks", [BUILDER, "--label", label, "--out", str(cand), "--checks"] + sl, logf):
            return done(5, "the candidate's checks failed")       # (a resumed run keeps checks that already passed)
        if mode == "auto":
            v = auto_verdicts(cand)
            sc = screen(v)
            rec["steps"]["identity"] = {"by": "rule", **sc}
            if not sc["pass"]:
                v.to_csv(cand / "identity_verdicts_rule_failed.csv", index=False)
                return done(4, "the identity screen found too many unsure links or players")
            v.to_csv(cand / "identity_verdicts.csv", index=False)
        elif not (cand / "identity_verdicts.csv").exists():
            return done(4, f"--hand: {cand}/identity_verdicts.csv (the hand check) is missing")
        else:
            rec["steps"]["identity"] = {"by": "hand"}
        if step("ready", [BUILDER, "--label", label, "--out", str(cand), "--ready"] + sl, logf):
            return done(5, "READY refused")
    if not (gaps / "READY.txt").exists():
        if step("derive", [BUILDER, "--label", f"{label}_gaps", "--out", str(gaps), "--derive-from", str(cand),
                           "--keep-since", ",".join(SCOPE), "--results-only", RESULTS_ONLY] + sl, logf):
            return done(1, "the derive failed")
        if step("derive checks", [BUILDER, "--label", f"{label}_gaps", "--out", str(gaps), "--checks"] + sl, logf):
            return done(5, "the derived candidate's checks failed")
        if step("derive ready", [BUILDER, "--label", f"{label}_gaps", "--out", str(gaps), "--ready"] + sl, logf):
            return done(5, "READY refused (derived)")
    from src.eda.current_best_model import additions as AD
    target = f"{FEED}/{snap}"
    if not (AD.ACCEPTED / target / "manifest.json").exists():
        if step("snapshot", [ADDITIONS, "--package", str(gaps), "--name", target, "--decision", DECISION], logf):
            return done(1, "the snapshot was not written")
    man = json.loads((AD.ACCEPTED / target / "manifest.json").read_text(encoding="utf-8"))
    rec["snapshot"] = {"name": target, "added_matches": man["added_matches"], "completed": man["completed_matches"]}
    if step("check", [ADDITIONS, "--check-against", str(gaps), "--only", target], logf):
        return done(5, "the merge does not give the derived candidate's tables")
    rec["steps"]["check"] = "pass"
    if advance:
        if FEED not in AD.index().get("feeds", {}):
            # the automatic job only refreshes a feed already accepted: the first snapshot is set by hand, after its
            # harm check (docs/decisions/2026-10-13-lower-level-feed.md)
            rec["steps"]["advance"] = "refused: no first snapshot of the feed is accepted yet"
            return done(0, "written, not advanced (the feed's first snapshot is set by hand after its harm check)")
        if step("advance", [ADDITIONS, "--set-feed", target], logf):
            return done(1, "the feed was not advanced")
        rec["steps"]["advance"] = target
        cur = AD.index()
        if PACKAGE in cur["packages"]:
            code = step("retire", [ADDITIONS, "--retire", PACKAGE, "--reason",
                                   f"superseded by the feed {FEED} (its men's 2026 Challenger scope, with box scores)"],
                        logf)
            rec["steps"]["retire"] = "done" if code == 0 else "kept (the feed does not hold all of it)"
    return done(0, "advanced" if advance else "written, not advanced")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--run", action="store_true")
    g.add_argument("--auto-verdicts", metavar="CANDIDATE", help="write the rule verdicts of a built candidate (and print "
                                                                "the screen)")
    g.add_argument("--calibrate", metavar="HAND_CHECKED", help="the rule verdicts against a hand-checked candidate")
    m = ap.add_mutually_exclusive_group()
    m.add_argument("--auto", action="store_true", help="rule verdicts (the weekly job)")
    m.add_argument("--hand", action="store_true", help="the hand check's verdicts must be in the candidate already")
    ap.add_argument("--advance", action="store_true", help="make the snapshot current when every step passes")
    ap.add_argument("--label", default=None, help="the candidate's label (default F<YYYYMMDD>)")
    ap.add_argument("--candidates-dir", default=None, help=f"where the candidates are built (default {CANDIDATES})")
    a = ap.parse_args()
    if a.candidates_dir:
        globals()["CANDIDATES"] = Path(a.candidates_dir)
    if a.auto_verdicts:
        v = auto_verdicts(Path(a.auto_verdicts))
        print(json.dumps(screen(v), indent=1))
        return 0
    if a.calibrate:
        print(json.dumps(calibrate_screen(Path(a.calibrate)), indent=1, default=str))
        return 0
    if not (a.auto or a.hand):
        raise SystemExit("--run needs --auto or --hand")
    label = a.label or f"F{dt.date.today():%Y%m%d}"
    return run(label, "auto" if a.auto else "hand", a.advance)


if __name__ == "__main__":
    sys.exit(main())
