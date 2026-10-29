"""Section A's data check (the owner's request of 13 Oct 2026; docs/studies/master_pipeline/process_log.md, Part 2):
the prediction run's gate applied to today's data before the run, so what it will do to each match is known in about
two minutes, with the cause and what fixes it, not after the 10-minute run.

The gate (src/eda/prediction_run/gate.py; docs/decisions/2026-10-14-box-score-gate.md, which replaced point 3 of the
8 Oct decision) checks every earlier completed match of either player, at the same event or with a latest possible
finish in the 14 days before the match, for a usable box score. A missing one never blocks: of a kind the training rows
nearly always hold (main tour, Challenger / WTA 125, qualifying above ITF level) it makes a bet need a 1-point edge; of a
kind they mostly lack (team events, ITF) it is only noted. A player who came through qualifying with no qualifying
match still blocks the match (the run also blocks an unknown indoor input, which only the run builds). Verdicts: "ready",
"ready once filled" (the run fills every gap from an official feed), "needs a 1-point edge", "will be blocked", and,
since 28 Oct 2026, "check failed": an error while checking that one match, said with "!!!", the others checked (one row
never holds up the rest: docs/decisions/2026-10-28-one-bad-match-left-out.md). Here:
    Stage 0      built now on the downloads on disk by the run's own builder (stage0_build.py --out-dir, about 100 s),
                 into this layer's cache, never the shared tables; reused while its inputs and code are unchanged. A
                 box score the builder's checks reject is caught too. Then, as the run's tables step does, the accepted
                 lower-level packages and each feed's current snapshot merged in (current_best_model/additions.merge,
                 about 15 s): the Challengers, ITF and qualifying matches the feeds add
    the window   each earlier match's latest possible finish from the shared timeline (a package's match: its own
                 window); one the timeline does not hold yet (newer than its last rebuild) by the timeline's own rule
                 window (match_timing/timing.rule_windows), else its event's start plus 14 days: cautious, so the check
                 errs toward a block
    the cause    Tennis My Life has none, or our consistency check rejected Tennis My Life's (Stage 0's box_status),
                 or a qualifier's qualifying match is missing
    the fix      from the run's own classes (prediction_run/fills.gaps): a tour match after the freeze is filled by
                 the run itself, a woman's from the WTA's own feed, a man's from the ATP Stats Centre (since 14 Oct
                 2026); one the frozen reference holds waits for Tennis My Life's own numbers; any other waits for
                 Tennis My Life (A1 again later); one our checks rejected needs a data repair
The run stays the authority: it downloads Tennis My Life again just before it predicts, and decides with its own gate
(and checks the indoor input, which only the run builds).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import bet_sheet as BS
from . import config as CFG
from .runner import Step, run_step

if str(CFG.ROOT) not in sys.path:
    sys.path.insert(0, str(CFG.ROOT))

CHECKS = CFG.OUT / "data_check"
CACHE = CHECKS / "stage0"                  # the Stage 0 of the latest check: a cache, rebuilt when its key changes
BUILDER = Path("src/eda/predictability_diagnostic/stage0_build.py")
CODE = (BUILDER, Path("src/eda/feature_alpha_audit/repair_data.py"))
MATCH_COLUMNS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
                 "tournament_name", "tournament_date", "status", "has_box", "box_status", "source"]
FAILED = "check failed"                  # an error while checking one match (28 Oct 2026): the others are checked
VERDICTS = {"ready": ("#E2EFDA", "#1E4620"), "ready once filled": ("#FFF2CC", "#5C4400"),
            "needs a 1-point edge": ("#FCE4D6", "#843C0C"), "will be blocked": ("#F4CCCC", "#7A0E0E"),
            FAILED: ("#C00000", "#FFFFFF")}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _key() -> dict:
    """What a Stage 0 build reads: the staged files and the level rules (stage0_build.input_record), the decided
    override and correction tables, and the builders' code. Equal keys, equal builds."""
    from src.eda.predictability_diagnostic import stage0_build as B
    tables = []
    for t in (Path(B.DECIDED_OVERRIDES), Path(B.DECIDED_CORRECTIONS)):
        tables += sorted(f for f in t.rglob("*") if f.is_file()) if t.is_dir() else [t]
    return json.loads(json.dumps({"inputs": B.input_record(),
                                  "tables": {CFG.rel(f): _sha(f) for f in tables if f.is_file()},
                                  "code": {c.as_posix(): _sha(CFG.ROOT / c) for c in CODE}}, default=str))


def fresh_stage0(*, dry_run: bool = False) -> Path | None:
    """Stage 0 on the downloads on disk, by the run's own builder, in this layer's cache (never the shared tables);
    reused while its inputs and code are unchanged. None in a dry run."""
    key = _key()
    keyfile = CACHE / "key.json"
    if (CACHE / "stage0_matches.parquet").exists() and keyfile.exists() and \
            json.loads(keyfile.read_text(encoding="utf-8")) == key:
        print(f"Stage 0: reusing {CFG.rel(CACHE)}, built on the same downloads and code")
        return CACHE
    keyfile.unlink(missing_ok=True)                    # a build cut short leaves no key: never reused
    run_step(Step("data_check_stage0", [str(BUILDER), "--out-dir", str(CACHE)],
                  note="Stage 0 on today's downloads, for the data check (never the shared tables)"), dry_run=dry_run)
    if dry_run:
        return None
    keyfile.write_text(json.dumps(key, indent=1), encoding="utf-8")
    return CACHE


def tables(folder: Path, timing: Path, packages: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, list]:
    """(matches, player rows, each match's lf, the packages merged): a Stage 0 folder and a timeline, with the accepted
    lower-level packages and each feed's current snapshot merged in as the run's tables step merges them."""
    m = pd.read_parquet(folder / "stage0_matches.parquet")
    p = pd.read_parquet(folder / "stage0_match_players.parquet")
    t = pd.read_parquet(timing)
    merged = []
    if packages:
        from src.eda.current_best_model import additions as AD
        merged = AD.listed()
        if merged:
            m, p, t, _ = AD.merge(m, p, t, merged)
    lf = t.astype({"match_id": str}).set_index("match_id")["lf"]
    return m.astype({"match_id": str}), p.astype({"match_id": str}), lf, [Path(x).name for x in merged]


def latest_finish(rows: pd.DataFrame, lf_by_id: pd.Series) -> pd.Series:
    """Each match's latest possible finish as a day number (the timeline's lf): the timeline's, else the timeline's own
    rule window for a match it does not hold yet, else its event's start plus the gate's window."""
    from src.eda.match_timing import timing as T
    from src.eda.prediction_run import common as P
    lf = rows["match_id"].map(lf_by_id).astype(float)
    miss = lf.isna().to_numpy()
    if miss.any():
        sub = rows[miss]
        _, hi, _ = T.rule_windows(sub)
        start = sub["tournament_date"].map(P.day_of).to_numpy(float) + P.WINDOW_DAYS
        lf[miss] = np.where(np.isfinite(hi), T.anchor_day(sub) + hi, start)
    return lf


BOX_CAUSES = {"failed_check": "Tennis My Life has it, but our consistency check rejected it",
              "blank": "Tennis My Life has none yet", "all_zero": "Tennis My Life's is all zeros",
              "one_side": "Tennis My Life's is incomplete", "partial": "Tennis My Life's is incomplete"}


def _fix(box_status: str, cls: str, tour: str, source: str) -> str:
    """What fills a missing box score of a kind the training rows nearly always hold (until then a bet needs a 1-point
    edge)."""
    if box_status == "failed_check":
        return "a data repair (our check or the score reading)"
    if cls == "fillable":
        return ("none: the run fills it from the ATP's own match statistics" if tour == "atp"
                else "none: the run fills it from the WTA's own feed")
    if source not in ("tml", "sackmann"):
        return f"wait for its source ({source}) to publish it: the lower-level feed takes it at its next snapshot (B8)"
    if cls == "held":
        return "wait for Tennis My Life's own numbers (the frozen reference holds this match), then A1 and check again"
    return "wait for Tennis My Life, then A1 and check again"


def data_check(matchups: str | Path | None, *, stage0: str | Path | None = None, timing: str | Path | None = None,
               held: set | None = None, packages: bool = True, now: dt.datetime | None = None,
               dry_run: bool = False, show: bool = True, write: bool = True) -> pd.DataFrame | None:
    """The gate's verdict on each match of a matchups CSV (A3), before the prediction run: "ready", "ready once filled"
    (the run fills the gap from the WTA's feed) or "will be blocked", with the cause and the fix. stage0: a Stage 0
    folder to read instead of building one (e.g. a run's own stage0/); timing: a timeline (default the shared one);
    held: the frozen reference's match ids (default read); packages: merge the accepted lower-level packages and
    feeds as the run does. Writes data/studies/master_pipeline/data_check/data_check_<time>.csv and its gaps; returns
    the matches' table (None in a dry run, and with no matchups: A3 found nothing to predict)."""
    if matchups is None:
        print("Nothing to check (A3 wrote no matchups).")
        return None
    from src.eda.merge_feasibility.scan import name_key
    from src.eda.predictability_diagnostic import common as C
    from src.eda.prediction_run import common as P
    from src.eda.prediction_run import fills as FL
    from src.eda.prediction_run import gate as G
    now = now or dt.datetime.now(dt.timezone.utc)
    mu = pd.read_csv(matchups)
    folder = Path(stage0) if stage0 else fresh_stage0(dry_run=dry_run)
    if folder is None:
        print("DRY RUN  the data check reads the Stage 0 above and applies the gate's rule to each match")
        return None
    m, p, lf_by_id, merged = tables(folder, Path(timing) if timing else CFG.TIMING, packages)
    m, p = m[MATCH_COLUMNS], p[["match_id", "player_id", "player_name", "entry"]]
    ids, keys, broken = {}, None, {}
    for side in ("a", "b"):                        # a player new since the shared Stage 0 carries no id: found by name
        for i, r in mu.iterrows():
            try:
                pid = r.get(f"stage0_id_{side}")
                if not (isinstance(pid, str) and pid.strip()):
                    if keys is None:
                        keys = p.drop_duplicates("player_id").assign(tour=lambda d: d["player_id"].str.split(":").str[0])
                        keys["key"] = keys["player_name"].map(name_key)
                    hit = keys.loc[keys["tour"].eq(r["tour"]) & keys["key"].eq(name_key(r[f"player_{side}"])),
                                   "player_id"]
                    pid = hit.iloc[0] if hit.nunique() == 1 else None
            except Exception as exc:  # noqa: BLE001 - this row's check fails below, the others go on
                pid, broken[i] = None, f"{type(exc).__name__}: {exc}"
            ids[(i, side)] = pid
    hist = p[p["player_id"].isin({v for v in ids.values() if v})].merge(m, on="match_id")
    hist["lf"] = latest_finish(hist, lf_by_id) if len(hist) else []
    del m, p, keys                                  # the merged tables are large; only these players' rows are kept
    today = pd.Timestamp(now.astimezone().date())
    classes = FL.gaps(folder, today, FL.reference_ids() if held is None else held).set_index("match_id")["class"]
    # the earlier qualifying rounds the run adds from TennisLive (the CSV's sidecar: prediction_run/earlier_rounds.py)
    from src.eda.prediction_run import earlier_rounds as ER
    side_csv = ER.sidecar(matchups)
    earlier = (pd.read_csv(side_csv, dtype=str, keep_default_na=False) if side_csv.exists() else pd.DataFrame())
    if len(earlier):
        earlier["_wk"] = earlier["winner_name"].map(name_key)
        earlier["_lk"] = earlier["loser_name"].map(name_key)
        boxed = earlier["w_svpt"].astype(str).str.strip().ne("") if "w_svpt" in earlier.columns else False
        earlier["_boxed"] = boxed
    rows, gaps, errors = [], [], []

    def check_one(i, r) -> tuple[dict, list]:
        """One match's row of the table and its gaps (kept only when its check finishes)."""
        if i in broken:
            raise RuntimeError(broken[i])
        found = []
        day = P.day_of(r["day"])
        order = C.ROUND_ORDER.get(str(r["round"]), 99)
        tid = str(r["tourney_id"])
        # a qualifying match's own event is its qualifying draw (tour-level qualifying is bet since 22 Oct 2026); a
        # main-draw match's is the main draw, its players' qualifying being found in the window
        qual = str(r["round"]).upper().startswith("Q") and str(r["round"]).upper() != "QF"
        event = hist["tour"].eq(r["tour"]) & (hist["qualifying"].astype(bool) if qual else
                                              ~hist["qualifying"].astype(bool)) & (
            hist["tournament_id"].astype(str).eq(tid) | hist["tournament_id"].astype(str).str.startswith(tid + "-"))
        why, fixes, notes, checked, bar, noted, filled, blocks = [], [], [], 0, 0, 0, 0, 0
        for side in ("a", "b"):
            name, pid = r[f"player_{side}"], ids[(i, side)]
            if not pid:
                why.append(f"{name} is not in Stage 0 yet: the run finds them in Tennis My Life's rows")
                continue
            h = hist[hist["player_id"].eq(pid)]
            same = event.loc[h.index] & (h["round_order"] < order)
            recent = h["lf"].notna() & (h["lf"] >= day - P.WINDOW_DAYS) & (h["lf"] < day)
            before = h[(same | recent) & h["status"].isin(G.REQUIRED)]
            checked += len(before)
            for _, g in before[~before["has_box"].astype(bool)].iterrows():
                kind = G.kind(g["level"], g["qualifying"])
                cause = BOX_CAUSES.get(g["box_status"], f"no usable box score ({g['box_status']})")
                what = f"{name}'s {g['tournament_name']} {g['round']} match"
                row = {"Match": f"{r['player_a']} v {r['player_b']}", "Player": name,
                       "Earlier match": f"{g['tournament_name']} {g['round']} ({str(g['tournament_date'])[:10]})",
                       "Kind": kind, "Cause": cause, "Stage 0 match id": g["match_id"]}
                if G.effect(kind) == "note":                   # a kind the training rows mostly lack: noted only
                    noted += 1
                    notes.append(f"{what} ({kind}): {cause}")
                    found.append({**row, "Effect": "noted only", "Fix": ""})
                    continue
                cls = classes.get(g["match_id"], "unserved")
                fix = _fix(g["box_status"], cls, r["tour"], str(g["source"]))
                # a round the sidecar holds with TennisLive's box score: the run gives it to the row (run.tml_box_fills)
                if len(earlier) and earlier[earlier["tour"].eq(str(r["tour"])) & earlier["round"].eq(str(g["round"]))
                                            & (earlier["_wk"].eq(name_key(name)) | earlier["_lk"].eq(name_key(name)))
                                            & earlier["_boxed"]].shape[0]:
                    cls, fix = "fillable", "the run fills it from TennisLive's match page (live only)"
                bar += 1
                filled += cls == "fillable" and g["box_status"] != "failed_check"
                why.append(f"{what}: {cause}")
                fixes.append(fix)
                found.append({**row, "Effect": "a bet needs a 1-point edge", "Fix": fix})
            entry = h.loc[same, "entry"].dropna().astype(str).str.upper()
            # a main-draw match's qualifier: the qualifying rounds the run adds from TennisLive (since 25 Oct 2026)
            mine = (earlier[earlier["tour"].eq(str(r["tour"])) & earlier["round"].str.fullmatch(r"Q\d")
                            & (earlier["_wk"].eq(name_key(name)) | earlier["_lk"].eq(name_key(name)))]
                    if len(earlier) and not qual else earlier.iloc[0:0])
            if len(mine):
                notes.append(f"{name}'s qualifying here comes from TennisLive: {len(mine)} round(s), "
                             f"{int(mine['_boxed'].sum())} with a box score (live only)")
            if entry.isin(G.QUALIFIED).any() and not h.loc[same | recent, "qualifying"].astype(bool).any() \
                    and not len(mine):
                why.append(f"{name} came through qualifying, but Stage 0 holds no qualifying match of theirs (Tennis "
                           "My Life has lacked the WTA's qualifying since June 2026)")
                fixes.append("none on the day")
                blocks += 1
            # the gate's rule for a qualifying match after its first round: the round before must be in Stage 0
            here = h.assign(tournament_id=np.where(event.loc[h.index].to_numpy(), tid, h["tournament_id"].astype(str)))
            if qual and G.previous_round_missing(here, tid, order, day):
                got = (earlier[earlier["tour"].eq(str(r["tour"])) & earlier["tourney_id"].astype(str).eq(tid)
                               & earlier["round"].eq(f"Q{int(order) - 1}") & earlier["_wk"].eq(name_key(name))]
                       if len(earlier) else earlier)
                if len(got) and str(got["w_svpt"].iloc[0] if "w_svpt" in got.columns else "").strip():
                    notes.append(f"{name}'s Q{int(order) - 1} comes from TennisLive with its box score (live only)")
                elif len(got):                                 # a result without a box score: the gate's bar
                    bar += 1
                    why.append(f"{name}'s Q{int(order) - 1} comes from TennisLive without a box score "
                               f"({got['box_note'].iloc[0] if 'box_note' in got.columns else 'none'})")
                    fixes.append("none on the day")
                else:
                    why.append(G.previous_round_reason(name, str(r["round"]).upper(), order, str(r["tour"])))
                    fixes.append("none on the day: the weekly lower-level feed brings it" if r["tour"] == "wta" else
                                 "wait for Tennis My Life's qualifying file, then A1 and check again")
                    blocks += 1
        verdict = ("will be blocked" if blocks else "ready" if not bar else
                   "ready once filled" if bar == filled else "needs a 1-point edge")
        return ({f"Starts ({BS.zone_label()})": BS.when(r.get("start_utc")), "Match": f"{r['player_a']} v {r['player_b']}",
                 "Event": f"{str(r['tour']).upper()} {r.get('tourney_name', tid)} {r['round']}", "Verdict": verdict,
                 "Why": "; ".join(why), "What fixes it": "; ".join(dict.fromkeys(fixes)),
                 "Noted only": "; ".join(notes), "Earlier matches checked": checked,
                 "Missing: edge needed": bar, "Missing: noted only": noted,
                 "_order": list(VERDICTS).index(verdict), "_start": BS._start_key(r)}, found)
    for i, r in mu.iterrows():
        try:
            row, found = check_one(i, r)
        except Exception as exc:  # noqa: BLE001 - an error checking one match is said; the others are checked
            why = f"{type(exc).__name__}: {exc}"
            errors.append(f"{r.get('player_a')} v {r.get('player_b')} -- {why}")
            try:
                start, key = BS.when(r.get("start_utc")), BS._start_key(r)
            except Exception:  # noqa: BLE001 - a start that cannot be read: the row still shows
                start, key = "", float("inf")
            row, found = {f"Starts ({BS.zone_label()})": start, "Match": f"{r.get('player_a')} v {r.get('player_b')}",
                          "Event": f"{str(r.get('tour')).upper()} {r.get('tourney_name', r.get('tourney_id'))} "
                                   f"{r.get('round')}", "Verdict": FAILED,
                          "Why": f"ERROR while checking this match ({why}); the run decides with its own data",
                          "What fixes it": "look at its row in the matchups CSV", "Noted only": "",
                          "Earlier matches checked": 0, "Missing: edge needed": 0, "Missing: noted only": 0,
                          "_order": list(VERDICTS).index(FAILED), "_start": key}, []
        rows.append(row)
        gaps += found
    if errors:                                     # said loudly (28 Oct 2026); the table shows them first
        print(f"!!! ERROR while checking {len(errors)} match{'es' * (len(errors) != 1)} (verdict \"{FAILED}\"); the "
              "others are checked as usual:")
        for e in errors:
            print(f"!!!   {e}")
    out = pd.DataFrame(rows)
    if len(out):                                   # the blocked matches first, then the edge needed, each by start time
        out = out.sort_values(["_order", "_start"], ascending=[False, True], kind="stable")
    out = out.drop(columns=["_order", "_start"], errors="ignore").reset_index(drop=True)
    gaps = pd.DataFrame(gaps)
    meta = {"stage0": CFG.rel(folder), "built": _built(folder), "tml": None if stage0 else _tml_age(),
            "packages": merged, "tml_status": _tml_status()}
    if write:
        CHECKS.mkdir(parents=True, exist_ok=True)
        stamp = f"{now.astimezone():%Y-%m-%d_%H%M%S}"
        out.to_csv(CHECKS / f"data_check_{stamp}.csv", index=False)
        gaps.to_csv(CHECKS / f"data_check_{stamp}_gaps.csv", index=False)
        meta["written"] = CFG.rel(CHECKS / f"data_check_{stamp}.csv")
    if show:
        _show(out, meta)
    out.attrs["gaps"], out.attrs["meta"] = gaps, meta
    return out


def _built(folder: Path) -> str:
    s = folder / "stage0_summary.json"
    if not s.exists():
        return "?"
    t = json.loads(s.read_text(encoding="utf-8")).get("generated_at")
    return f"{BS.when(t)} {BS.zone_label()}" if t else "?"


def _tml_age() -> str:
    from .data import last_run_of
    last = last_run_of("tml")
    if last is None:
        return "never fetched by the scheduled task"
    hours = (dt.datetime.now().astimezone() - last).total_seconds() / 3600
    return f"fetched {BS.when(last)} {BS.zone_label()} ({hours:.0f} h ago)"


def _tml_status() -> list[str]:
    """Tennis My Life's held files (lagging after a day), carried events and corrections (src/ingest/health.py)."""
    try:
        from src.ingest import health as H
        return H.tml_status()["lines"]
    except Exception as exc:  # noqa: BLE001 - a status line never stops the check
        return [f"Tennis My Life status unknown ({type(exc).__name__}: {exc})"]


def _show(out: pd.DataFrame, meta: dict) -> None:
    n = out["Verdict"].value_counts().to_dict() if len(out) else {}
    head = (f"Data check before the prediction run: {len(out)} matches; " +
            ", ".join(f"{n[v]} {v}" for v in VERDICTS if n.get(v)) + ".")
    lines = [f"Tennis My Life's results and box scores: {meta['tml']}. Stage 0 built on them {meta['built']}." if
             meta["tml"] else f"Stage 0 read from {meta['stage0']} (built {meta['built']}).",
             *meta.get("tml_status", []),
             f"Lower-level packages and feeds merged in, as the run merges them: {', '.join(meta['packages']) or 'none'}.",
             "The run downloads again and decides with its own gate; this check errs toward a gap. A missing box "
             "score never blocks (rule of 14 Oct 2026): it makes a bet need a 1-point edge, or is only noted."]
    if BS._in_notebook():
        from IPython.display import HTML, display
        e = html.escape
        parts = [f"<div style='font-family:Segoe UI,Calibri,sans-serif'><h3 style='margin:4px 0'>{e(head)}</h3>"]
        parts += [f"<div style='margin:2px 0'>{e(x)}</div>" for x in lines]
        if len(out):
            sty = out.style.apply(lambda row: [f"background-color:{VERDICTS[row['Verdict']][0]};color:"
                                               f"{VERDICTS[row['Verdict']][1]}" for _ in row], axis=1)
            sty = sty.hide(axis="index").set_table_styles([
                {"selector": "th", "props": f"background-color:{BS.HEAD[0]};color:{BS.HEAD[1]};padding:4px 6px;"
                                            "text-align:left"},
                {"selector": "td", "props": "padding:3px 6px;border-bottom:1px solid #d0d0d0;vertical-align:top"},
                {"selector": "", "props": "border-collapse:collapse;font-size:12.5px;margin-top:6px"}])
            parts.append(sty.to_html())
        parts.append("</div>")
        display(HTML("".join(parts)))
    else:
        print(head, *lines, sep="\n")
        if len(out):
            with pd.option_context("display.width", 250, "display.max_columns", 20, "display.max_colwidth", 70):
                print(out.drop(columns=["Why", "What fixes it", "Noted only"]).to_string(index=False))
            for _, r in out[(out["Why"].str.len() > 0) | (out["Noted only"].str.len() > 0)].iterrows():
                print(f"  {r['Match']} ({r['Verdict']}): " + "; ".join(x for x in (
                    r["Why"] and f"{r['Why']}. Fix: {r['What fixes it']}",
                    r["Noted only"] and f"noted only: {r['Noted only']}") if x))
