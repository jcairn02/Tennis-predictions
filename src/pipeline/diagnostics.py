"""Section A's output: the bet-time record of a prediction run, and the bet sheet made from it (bet_sheet.py).

    predictions/<day>/bet_sheet_<local time>.xlsx                    the bet sheet: what to bet, at what odds, how much,
                                                                     and why (bet_sheet.py; the owner's request of 13 Oct)
    predictions/<day>/records/bet_sheet_<local time>.csv             the record below: every figure, sides A/B
    predictions/<day>/records/bet_sheet_<local time>.provenance.json its provenance (and the run's notes, said once)

The record: one row per match, built only from the run folder's stable files (agreed with the daily_prediction session:
predictions.csv, curves.parquet, gate.csv, provenance keys; columns may be added there, never removed or renamed) and the
matchups CSV the run was made from. Everything is side A / side B as the daily pipeline's Stage 0 sides (player_a_id is
side A); the names come from predictions.csv, which takes them from Stage 0's side rows. The bet sheet only re-says it.

What a row says (review D2's rules, process log 11:00):
    the match        day, start, minutes to start, tour, event, round, best of, surface, indoor
    the price        source, quote time and age, Pinnacle's odds of both players (with the margin), the overround, the
                     margin-free price p_market_a the model was fed, Pinnacle's stake limit
    the model        p_base_a (stage 1, the TabPFN seed mean), eta, spd_L, q_a (both stages: the forecast), the spread of
                     the 16 seeds at the own price
    the patterns     the five-pattern adjustment (switched on 13 Oct 2026; docs/studies/unpriced_leads/): patterns
                     ("on" / "off"), q_a_patterns_off and q_a_patterns_on (q_a is the one used), pattern_shift_pts_a, and
                     the decision without it (edge_a_, ev_a_pinnacle_, ev_b_pinnacle_, pick_patterns_off) with
                     patterns_effect: "bet only with the patterns", "the patterns remove this bet", "the patterns
                     switch the side", or empty
    the bet          edge_a = q_a - p_market_a; the pick is the side whose EV at Pinnacle's own odds (margin included) is
                     positive; fair odds 1/q of the pick; the least odds at which the pick is still +EV anywhere (1/q, no
                     fees); its EV at Pinnacle; at another venue too when its prices are given
    break-even       every price p* (side A's) where the model's curve crosses q = p (0 to 3 crossings happen; review D2),
                     the one nearest the current price, or "none in [0.05, 0.95]"
    zero EV          since 24 Oct 2026: each side's posted chance (margin included) at which its EV at Pinnacle's odds
                     would be zero if the line moved there with its margin kept, the model's chance re-read off the
                     curve (zero_ev_implied_a/_b: every crossing; nearest_zero_ev_implied_a/_b: the one nearest the
                     current price). The sheet's market chance is the posted price's (the owner, 24 Oct 2026)
    stake            only with stake_rule="owner_8oct": the owner's research rule of 8 Oct 2026 (units, not a decided
                     staking rule; tabpfn_thinking58/common.stake)
    flags            blocked (no pick, no EV) with the reasons: the gate's "do not bet" (since 14 Oct 2026 only an
                     unknown indoor input or a qualifier without a qualifying match; since 22 Oct 2026 also a
                     qualifying match whose round before is missing), neither a main-tour match nor tour-level
                     qualifying (bet since 22 Oct 2026), an unsupported format, a stale quote, a price or player
                     read-back mismatch, a price off the curve; warnings (this match's own): players new since Stage 0,
                     seeds that disagree, missing serve-speed form. A match's listed start never blocks (the owner,
                     24 Oct 2026: a started match cannot be bet pre-match anyway, and Pinnacle often pushes a tennis
                     start back); minutes_to_start stays in the record
    the edge bar     gate_edge_bar (gate.EDGE_BAR, 14 Oct 2026; docs/decisions/2026-10-14-box-score-gate.md): an earlier
                     match of a kind the training rows nearly always hold lacks a box score (gate_detail: whose), so a
                     side is picked only if its forecast moved the bar against it is still +EV; passed_by_bar: the
                     side the bar took away. gate_notes: missing box scores of kinds the training rows mostly lack (team
                     events, ITF), noted only
    decision         BET (a pick), PASS (no side +EV at Pinnacle's odds), BLOCKED, NOT PREDICTED; home_side: the side
                     Pinnacle lists first
    Thinking         a run with TabPFN-3.5-Thinking beside the local model (MODEL "tabpfn35_thinking", 20 Oct 2026): q_a,
                     q_a_patterns_off and everything computed from them (edge, EV, the pick, fair odds, the break-even
                     prices) are the ensemble's (the two chances averaged 50/50 in log-odds, then the patterns while
                     on); beside them q_a_local (the local model, with the patterns while
                     on), q_a_local_patterns_off and q_a_thinking (Thinking's chance: the API's own plus stage 2's
                     serve-speed term, uncalibrated, no patterns; q_a_thinking_api the API's own, from the evening of
                     20 Oct 2026).
                     When the run's Thinking call failed, the row is the local model's alone and the run's notes say so
    rests on         since 28 Oct 2026 (the production-integrity plan as revised and approved that day): the decision
                     without stage 2's serve-speed term (speed_term_pts_a: what it adds to side A's chance; pick_no_speed;
                     speed_effect: "bet only with the speed term", "the speed term removes this bet", "the speed term
                     switches the side"; it is added in log-odds to each model, so in a Thinking run to both),
                     each player's newest speed reading (speed_last_reading_a/b) and newest result in the run's tables
                     (newest_result_a/b), and missing_results: the finished matches of either player that earlier runs
                     had and this run lacks (the run's continuity check, daily_prediction/dp_continuity.py: an amber
                     note, never a block)
The odds in the record stay decimal (EV is computed from them); the sheet shows them as US odds only (20 Oct 2026).
The run's own notes (the history check, recomputed state parts, an unclean results download) apply to every match:
they go to the provenance sidecar and the sheet's header, once, not into every row.
A newer price (reprice) is read off the run's curve, so edge and EV are always at the same moment as the price.
A tour switched off for the bet day (config.BET_TOURS; the owner, 28 Oct 2026: the women's): a live run made before
the switch keeps its predictions of it in its files, and the record and the sheet leave them out, as "Not predicted"
leaves out its listings; one note says how many. A replay (C8) keeps both tours.
A match the run left out because of an error in its own row (since 28 Oct 2026; the run's left_out.json, left_out.py:
the owner asked that it be said "clearly and loudly, however still give all the other predictions") is a NOT PREDICTED
row whose reason starts LEFT_OUT_ERROR, whatever left_out= says, and the sheet's alerts, above everything, name it with
its error. An earlier qualifying round the run could not add is an alert too, and a warning on its player's match.
"""
from __future__ import annotations

import datetime as dt
import glob
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import bet_sheet as BS
from . import config as CFG

if str(CFG.ROOT) not in sys.path:
    sys.path.insert(0, str(CFG.ROOT))
from src.eda.merge_feasibility.scan import name_key  # noqa: E402

GRID_LO, GRID_HI = 0.05, 0.95
SEED_SD_WARN = 0.03
LEFT_OUT_ERROR = "ERROR in its row, left out of the run"     # a match the run left out (left_out.py), on the sheet


def _left_out_rows(run: Path, mu: pd.DataFrame | None, held: dict) -> list[dict]:
    """The run's matches left out by an error (left_out.json) as the record's NOT PREDICTED rows, with Pinnacle's odds
    and start from the matchups CSV the run was given (its row of the same players)."""
    from . import left_out as LO
    out = []
    for r in held["matches"]:
        m = None
        if mu is not None and len(mu) and isinstance(r.get("player_a"), str) and isinstance(r.get("player_b"), str):
            keys = {name_key(r["player_a"]), name_key(r["player_b"])}
            hit = mu[mu.apply(lambda x: {name_key(str(x["player_a"])), name_key(str(x["player_b"]))} == keys, axis=1)]
            m = hit.iloc[0].to_dict() if len(hit) == 1 else None
        odds = {}
        for s in ("a", "b"):
            try:
                odds[s] = _odds(m, s) if m is not None else float("nan")
            except (TypeError, ValueError):
                odds[s] = float("nan")
        out.append({"day": r.get("day"), "start_utc": m.get("start_utc") if m is not None else None,
                    "tour": r.get("tour"), "tournament": r.get("tourney_name") or r.get("tourney_id"),
                    "round": r.get("round"), "player_a": r.get("player_a"), "player_b": r.get("player_b"),
                    "pinnacle_odds_a": odds["a"], "pinnacle_odds_b": odds["b"], "status": "not predicted",
                    "blocked": True, "block_reasons": f"{LEFT_OUT_ERROR} ({LO.STEPS.get(r.get('step'), r.get('step'))}): "
                                                      f"{r.get('reason')}",
                    "match_id": r.get("match_id"), "run": run.name, "pick": "", "decision": "NOT PREDICTED"})
    return out


def _left_out_alerts(held: dict, predicted: int) -> list[str]:
    """The sheet's alerts: each match the run left out because of an error in its row, with the error, and each earlier
    round it could not add (left_out.json)."""
    from . import left_out as LO
    out, bad = [], held["matches"]
    if bad:
        out.append(f"ERROR IN {len(bad)} ROW{'S' * (len(bad) != 1)}: {len(bad)} MATCH{'ES' * (len(bad) != 1)} LEFT OUT "
                   f"OF THIS RUN, SO NO PREDICTION. The other {predicted} match{'es were' if predicted != 1 else ' was'} "
                   "predicted as usual (below).")
        out += [f"No prediction: {LO.describe(r)}. The error: {r.get('reason')} (found at "
                f"{LO.STEPS.get(r.get('step'), r.get('step'))})." for r in bad]
    if held["earlier_rounds"]:
        n = len(held["earlier_rounds"])
        out.append(f"{n} EARLIER ROUND{'S' * (n != 1)} MISSING from the run's data (each one's player's match is "
                   "predicted without it; its note says so): "
                   + "; ".join(f"{LO.describe_earlier(e)} ({e.get('reason')})" for e in held["earlier_rounds"]) + ".")
    return out


def pattern_effect(pick: str, pick_off: str, status: str) -> str:
    """How the five-pattern adjustment changes the decision (empty: no change, or the adjustment is off)."""
    if status != "on" or pick == pick_off:
        return ""
    if pick and not pick_off:
        return "bet only with the patterns"
    if pick_off and not pick:
        return "the patterns remove this bet"
    return "the patterns switch the side"


def speed_effect(pick: str, pick_no_speed: str) -> str:
    """How stage 2's serve-speed term changes the decision (what a bet rests on, 28 Oct 2026; empty: no change)."""
    if pick == pick_no_speed:
        return ""
    if pick and not pick_no_speed:
        return "bet only with the speed term"
    if pick_no_speed and not pick:
        return "the speed term removes this bet"
    return "the speed term switches the side"


def _continuity(run: Path) -> dict:
    """The run's continuity check (daily_prediction/dp_continuity.py, since 28 Oct 2026; {} for an older run)."""
    p = run / "continuity.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _continuity_notes(cont: dict) -> list[dict]:
    """The run notes from its continuity check: finished matches earlier runs had and this run lacks, the check's own
    failure, and Tennis My Life's lagging held files and carried events as of the run. Notes, never blocks."""
    notes = []
    if cont.get("failed"):
        notes.append({"plain": "The check that no finished match had gone missing could not run, so nothing compared "
                               "this run's results with earlier runs'.", "detail": cont.get("line")})
    miss = cont.get("missing") or []
    if miss:
        ev = "; ".join(f"{e['tour'].upper()} {e['event']} ({e['matches']})" for e in cont.get("missing_events", [])[:8])
        notes.append({"plain": f"Missing results: {len(miss)} finished matches that earlier runs had are not in this "
                               f"run's data ({ev}). The model does not know them; a match whose player played one has "
                               "an amber note. Not a block.", "detail": cont.get("line")})
    for line in (cont.get("tml") or {}).get("lines") or []:
        if line.startswith(("LAGGING", "CARRIED")):
            notes.append({"plain": line, "detail": "Tennis My Life's download (src/ingest/health.py tml_status)"})
    return notes


def _num(x, default=float("nan")) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _logit(p):
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return np.log(p / (1 - p))


def _expit(x):
    return 1 / (1 + np.exp(-np.asarray(x, dtype=float)))


def _crossings(x: np.ndarray, y: np.ndarray) -> list[float]:
    """The x where y changes sign along the curve (a zero on the grid included), interpolated linearly."""
    out = []
    for i in range(len(x) - 1):
        if y[i] == 0:
            out.append(float(x[i]))
        elif y[i] * y[i + 1] < 0:
            t = y[i] / (y[i] - y[i + 1])
            out.append(float(x[i] + t * (x[i + 1] - x[i])))
    if len(y) and y[-1] == 0:
        out.append(float(x[-1]))
    return out


def curve_roots(odds_logit: np.ndarray, q: np.ndarray) -> list[float]:
    """Side A's prices p* where the model's forecast equals the price, q(p*) = p*: the sign changes of
    logit q - logit p along the curve, interpolated linearly in log-odds."""
    x = np.asarray(odds_logit, dtype=float)
    return [float(_expit(r)) for r in _crossings(x, _logit(q) - x)]


def zero_ev_roots(odds_logit: np.ndarray, q: np.ndarray, over: float) -> tuple[list[float], list[float]]:
    """Side A's margin-free prices p* at which each side's expected profit at the posted odds would be zero if the line
    moved there with its margin `over` (1/d_a + 1/d_b) kept and spread proportionally, as the model's input removes it:
    side A then posts 1/(over·p) and side B 1/(over·(1 - p)), so A's EV is zero where q(p) = over·p and B's where
    1 - q(p) = over·(1 - p), the model's chance moving with the price along its curve. The sign changes of
    log q - log(over·p) and log(1 - q) - log(over·(1 - p)), interpolated linearly in log-odds. Each side's posted
    chance there is over·p* (A) or over·(1 - p*) (B)."""
    x = np.asarray(odds_logit, dtype=float)
    q = np.clip(np.asarray(q, dtype=float), 1e-12, 1 - 1e-12)
    p = _expit(x)
    a = _crossings(x, np.log(q) - np.log(over * p))
    b = _crossings(x, np.log(1 - q) - np.log(over * (1 - p)))
    return [float(_expit(r)) for r in a], [float(_expit(r)) for r in b]


def _nearest(roots: list[float], p: float) -> float:
    """The root nearest side A's price p, in log-odds; NaN when there is none."""
    return min(roots, key=lambda r: abs(_logit(r) - _logit(p))) if roots else float("nan")


def q_at(odds_logit: np.ndarray, q: np.ndarray, p: float) -> float:
    """The curve read at side A's price p (linear in log-odds); NaN off the grid (the daily pipeline's own rule)."""
    x = float(_logit(p))
    if not (odds_logit[0] <= x <= odds_logit[-1]):
        return float("nan")
    return float(_expit(np.interp(x, odds_logit, _logit(q))))


def _decimal(odds) -> float:
    if odds is None or (isinstance(odds, float) and math.isnan(odds)):
        return float("nan")
    x = float(odds)
    if x >= 100:
        return 1 + x / 100
    if x <= -100:
        return 1 + 100 / -x
    if 1 < x < 100:
        return x
    return float("nan")


def _payout(price) -> float:
    """Decimal payout of a venue price: decimal odds, American odds, or a share price in (0, 1) (Polymarket)."""
    x = float(price)
    if 0 < x < 1:
        return 1 / x
    return _decimal(x)


def _seed_spread(run: Path) -> pd.Series:
    files = sorted(glob.glob(str(run / "fit" / "season*_seed*.npz")))
    if not files:
        return pd.Series(dtype=float)
    own = {}
    for f in files:
        with np.load(f, allow_pickle=False) as z:
            for mid, p in zip(z["match_id"].astype(str), z["own"]):
                own.setdefault(mid, []).append(float(p))
    return pd.Series({m: float(np.std(v, ddof=1)) if len(v) > 1 else float("nan") for m, v in own.items()})


def _read_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def _speed_coverage(day: str) -> pd.DataFrame:
    """Each ATP player's serve-speed readings in the 28 days to the run's day (the live form file of that day, else the
    latest before it). spd_L is 0 both for equal forms and for no readings; this tells them apart."""
    files = sorted(CFG.SPEED_LIVE.glob("speed_form_*.parquet"))
    files = [f for f in files if f.stem.replace("speed_form_", "") <= str(day)[:10]]
    if not files:                 # no form file as of that day (e.g. a replay before the daily collector): no check
        return pd.DataFrame(columns=["k28", "last_reading"])
    f = pd.read_parquet(files[-1], columns=["player_id", "k28", "last_reading"])
    return f.astype({"player_id": str}).set_index("player_id")


def _download_warning(run: Path) -> str | None:
    """The run's refresh record: whether Tennis My Life's download completed (a held file or a lock left by an
    interrupted download makes it exit non-zero, and the run carries on with the previous copy)."""
    rec = _read_json(run / "refresh.json")
    if not rec:
        return None
    text = json.dumps(rec)
    steps = rec.get("steps") or rec.get("record") or []
    bad = [s for s in steps if isinstance(s, dict) and s.get("exit") not in (0, None)] if isinstance(steps, list) else []
    if bad or '"exit": 1' in text:
        return "the run's Tennis My Life download did not finish cleanly (held file or lock): refresh.json"
    return None


HELD_LINE = re.compile(r"\[tennis_my_life\] held (\S+?):")


def _held_in_refresh(run: Path) -> list[str]:
    """The Tennis My Life files the run's download held for review (the adapter's 'held NAME:' lines in refresh.json)."""
    rec = _read_json(run / "refresh.json")
    steps = rec.get("steps") or rec.get("record") or []
    tails = " ".join(str(s.get("tail") or "") for s in steps if isinstance(s, dict)) if isinstance(steps, list) else ""
    return list(dict.fromkeys(HELD_LINE.findall(tails)))


def _undecided_lower_level(hist: dict) -> int:
    """Lower-level changes no decision covers: the history check's gated rows. Tennis My Life's own lower-level
    corrections are decided (13 Oct 2026, docs/decisions/2026-10-13-tml-lower-level-revisions.md): history.py lists
    them as tml_lower, and in a record written before that (no tml_lower) they are the gated rows of source tml."""
    rows = [r for part in (hist.get("gated") or {}).values() for r in (part.get("by") or [])]
    return sum(int(r.get("matches") or 0) for r in rows if "tml_lower" in hist or r.get("source") != "tml")


def _run_notes(run: Path, hist: dict, recomputed: dict, download: str | None) -> list[dict]:
    """What applies to every match of the run, plainly ("plain") with the technical text ("detail"). Tennis My Life's
    own lower-level corrections are decided (13 Oct 2026) and get no note: the provenance's history line lists them."""
    notes = []
    if hist and hist.get("template_ok") is False and _undecided_lower_level(hist):
        notes.append({"plain": "History check: some lower-level matches differ from the 8 Oct reference in a way no "
                               "decision covers (another source than Tennis My Life, or a level it never supplied), and "
                               "this run uses them. Reported, not a block: the provenance lists them for a person to "
                               "look at.",
                      "detail": "history check: the lower-level history differs from the reference (history.json): "
                                + str(_read_json(run / "history.json").get("history_line") or "")})
    if recomputed:
        n = sum(int(v) for v in recomputed.values() if str(v).isdigit())
        notes.append({"plain": f"Part of the saved feature state ({n} part{'s' * (n != 1)}) was recomputed after a data "
                               "revision: a slower run, not a less accurate one.",
                      "detail": f"state parts recomputed in this run: {recomputed}"})
    held = _held_in_refresh(run) if download else []
    if held:
        notes.append({"plain": f"Tennis My Life's download held {len(held)} changed file{'s' * (len(held) != 1)} for "
                               f"review ({', '.join(held)}); this run used the copies it had. Each match's data check "
                               "still applies.",
                      "detail": f"{download}; held: {', '.join(held)} (accept after src/eda/tml_revisions/"
                                "held_check.py: docs/decisions/2026-10-13-tml-lower-level-revisions.md)"})
    elif download:
        notes.append({"plain": "Tennis My Life's download did not finish cleanly (a held file or a lock); the run used "
                               "the copy it had. Each match's data check still applies.",
                      "detail": download})
    return notes


# Why an earlier match has no usable box score, from its box_status in the run's own Stage 0 (stage0_build.box_scores):
# a box score Tennis My Life published can still be dropped by Stage 0's consistency checks (13 Oct 2026: two Laver Cup
# matches, their 10-8 and 13-11 match tiebreaks read as full sets, failed the points-per-game check B9)
BOX_CAUSES = {"failed_check": "Tennis My Life has it, but our consistency check rejected it",
              "blank": "Tennis My Life has none", "all_zero": "Tennis My Life's is all zeros",
              "one_side": "Tennis My Life's is incomplete", "partial": "Tennis My Life's is incomplete"}


def _gate_gaps(run: Path) -> tuple[dict, dict]:
    """Per live match, whose earlier match lacks a usable box score and why: "Casper Ruud's Laver Cup RR match (Tennis
    My Life has it, but our consistency check rejected it)" (the gate's own list; the cause from the run's Stage 0).
    Two dicts: the gaps that set the edge bar (since 14 Oct 2026: a kind the training rows nearly always hold; before,
    every gap, and each blocked the bet) and the gaps only noted (team events, ITF)."""
    p = run / "gate_missing.csv"
    if not p.exists():
        return {}, {}
    g = pd.read_csv(p).astype({"live_match_id": str, "match_id": str})
    if "effect" not in g.columns:                       # a run before 14 Oct 2026: every gap counted
        g["effect"] = "edge bar"
    s0 = run / "stage0" / "stage0_matches.parquet"
    status = (pd.read_parquet(s0, columns=["match_id", "box_status"]).astype({"match_id": str})
              .set_index("match_id")["box_status"] if s0.exists() else pd.Series(dtype=object))
    out = ({}, {})
    for (mid, eff), rows in g.groupby(["live_match_id", "effect"], sort=False):
        items = []
        for r in rows.itertuples():
            cause = BOX_CAUSES.get(status.get(r.match_id))
            kind = f"{r.kind}, " if eff == "note" and isinstance(getattr(r, "kind", None), str) else ""
            items.append(f"{r.player_name}'s {r.tournament_name} {r.round} match" +
                         (f" ({kind}{cause})" if cause else (f" ({kind[:-2]})" if kind else "")))
        items = list(dict.fromkeys(items))
        out[0 if eff != "note" else 1][mid] = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
    return out


def _selected_instance() -> str | None:
    """The live model's name: the notebook's selection, the one place that names it (22 Oct 2026); None with none."""
    from .train import selected_instance_name
    return selected_instance_name()


def _model_block(run: Path, pred: pd.DataFrame) -> str | None:
    """A live run's model against the live model the notebook's selection names (22 Oct 2026; master pipeline process
    log, Part 9): a bet rests only on the selected model. A run made with another one (the selection changed since,
    or a run started outside the notebook) blocks every match; a replay or other non-live run is not checked."""
    if not run.name.startswith("live_"):
        return None
    made = {Path(str(x)).name for x in pred["instance"].dropna()} if "instance" in pred.columns else set()
    live = _selected_instance()
    if live is None:
        return "no live model is selected (the notebook's selection): use_instance(), then run A4 again"
    if not made:
        return f"the run does not record its model, so it cannot be checked against the selected live model {live}"
    if made != {live}:
        return f"made with {', '.join(sorted(made))}, not the selected live model {live}: run A4 again"
    return None


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


def _thinking_line(th: dict | None) -> str:
    """The run's Thinking call in one line, for the sheet's Run tab: the fit, the served model, the tokens, or why not."""
    th = th or {}
    if th.get("ensemble") != "on":
        return f"asked for, failed: {th.get('failed') or 'no Thinking forecast in the run'}"
    parts = []
    for season, s in sorted((th.get("seasons") or {}).items()):
        served = s.get("served") or {}
        parts.append(f"season {season}: fit {s.get('fitted_train_set_id')} (seed 0), served {served.get('weights')} "
                     f"(package {served.get('package_version')}), {s.get('query_rows')} rows, "
                     f"{s.get('tokens_used_daily_counter')} tokens on the daily counter")
    return f"on, weight {th.get('weight_local')} local / {1 - float(th.get('weight_local') or 0.5)} Thinking; " + \
        "; ".join(parts)


def _id(x) -> str | None:
    return str(x) if isinstance(x, str) and x.strip() else None


def _present_ids(r) -> set:
    """The resolved Stage 0 ids a matchups row carries (a player new since Stage 0 has none)."""
    return {i for i in (_id(r.get("stage0_id_a")), _id(r.get("stage0_id_b"))) if i}


def _odds(row, side: str) -> float:
    """A side's bookmaker odds with the margin (the column `odds_<side>`, American or decimal; older files:
    `odds_<side>_american`)."""
    v = row.get(f"odds_{side}")
    if v is None or (isinstance(v, float) and math.isnan(v)):
        v = row.get(f"odds_{side}_american")
    return _decimal(v)


def _utc(value):
    """A timestamp as UTC; a value without a time zone is read as UTC (and flagged by the caller)."""
    t = pd.Timestamp(value)
    return (t.tz_localize("UTC"), True) if t.tzinfo is None else (t.tz_convert("UTC"), False)


def _matchup_rows(pred: pd.DataFrame, mu: pd.DataFrame | None) -> list[dict | None]:
    """Each prediction's row of the matchups CSV: by the resolved Stage 0 ids, else by the pair of names."""
    out = []
    for _, p in pred.iterrows():
        hit = None
        if mu is not None and len(mu):
            ids = {str(p["player_a_id"]), str(p["player_b_id"])}
            if {"stage0_id_a", "stage0_id_b"} <= set(mu.columns):
                m = mu[mu.apply(lambda r: _present_ids(r) == ids, axis=1)]
                if len(m) == 1:
                    hit = m.iloc[0].to_dict()
            if hit is None and isinstance(p.get("player_a"), str):
                keys = {name_key(p["player_a"]), name_key(p["player_b"])}
                m = mu[mu.apply(lambda r: {name_key(r["player_a"]), name_key(r["player_b"])} == keys, axis=1)]
                if len(m) == 1:
                    hit = m.iloc[0].to_dict()
        out.append(hit)
    return out


def bet_diagnostics(run: str | Path | None = None, *, reprice_file: str | Path | None = None,
                    venue_prices: dict | None = None, venue: str = "", venue_fee: float = 0.0,
                    stale_minutes: float = 30, stake_rule: str | None = None, now: dt.datetime | None = None,
                    left_out: str = "main", write: bool = True, show: bool = True) -> pd.DataFrame:
    """The bet-time record of a run (default: the latest live run) and its bet sheet. reprice_file: a reprice() output,
    whose newer prices (and the q read off the curve) replace the run's. venue_prices: {player name: price} at another
    venue (decimal or American odds, or a share price in (0, 1)), with venue_fee a fraction of net winnings.
    stake_rule="owner_8oct" adds the owner's research staking rule in units. left_out: the window's listed matches that
    were not predicted, with the reason: "main" (main-tour singles, the default), "all", or "none". A live run writes
    predictions/<first day>/bet_sheet_<local time>.xlsx and, in records/, the record (.csv) and its provenance; other
    runs write the three into the run folder. A new set each call: the file a bet rested on is never replaced. show:
    the sheet in the notebook. Returns the record."""
    from .predict import latest_run
    run = Path(run) if run else latest_run()
    if run is None or not (run / "predictions.csv").exists():
        raise RuntimeError(f"no predictions in {run}")
    now = now or dt.datetime.now(dt.timezone.utc)
    if now.tzinfo is None:                                 # a time without a zone is read as UTC, like the quotes
        now = now.replace(tzinfo=dt.timezone.utc)
    pred = pd.read_csv(run / "predictions.csv").astype({"match_id": str})
    curves = pd.read_parquet(run / "curves.parquet").astype({"match_id": str})
    frame = pd.read_parquet(run / "live_frame.parquet").astype({"match_id": str}).set_index("match_id")
    mu = pd.read_csv(run / "matchups_input.csv") if (run / "matchups_input.csv").exists() else None
    hist = _read_json(run / "history.json").get("history", {})
    states = _read_json(run / "states.json")
    prov = _read_json(run / "provenance.json")
    # Thinking beside the local model (20 Oct 2026): asked for when predictions.csv carries its columns; the ensemble is
    # what the run predicted only when its call succeeded (else the local model alone, said once in the notes)
    asked = "q_a_thinking" in pred.columns or \
        _read_json(run / "pipeline_model.json").get("model") == CFG.THINKING_MODEL
    ensemble = bool(len(pred)) and "ensemble" in pred.columns and (pred["ensemble"].astype(str) == "on").all()
    model = CFG.THINKING_MODEL if ensemble else CFG.LOCAL
    spread = _seed_spread(run)
    rep = rep_prices = None
    if reprice_file:
        rep = pd.read_csv(reprice_file).astype({"match_id": str}).set_index("match_id")
        pp = Path(reprice_file).with_name(Path(reprice_file).stem + "_prices.csv")
        rep_prices = pd.read_csv(pp).astype({"match_id": str}).set_index("match_id") if pp.exists() else None
    from src.eda.tabpfn_thinking import common as T
    surfaces = {v: k for k, v in T.CODES["surface"].items()}
    venue_keys = {name_key(k): v for k, v in (venue_prices or {}).items()}
    recomputed = {k: v for k, v in (states.get("parts_summary") or {}).items() if k != "resumed"}
    # the form file as of the sheet's own time: a sheet remade later must not read readings collected after it
    speed = _speed_coverage(min(str(pred["day"].max())[:10], f"{now.astimezone():%Y-%m-%d}"))
    download = _download_warning(run)
    notes = _run_notes(run, hist, recomputed, download)      # the run's own: said once, not on every row
    cont = _continuity(run)
    notes += _continuity_notes(cont)
    missing_by = cont.get("missing_by_player") or {}
    newest = cont.get("newest_result") or {}
    if asked and not ensemble:
        notes.insert(0, {"plain": "TabPFN-3.5-Thinking was asked for, but its call failed: every chance, edge and "
                                  "decision on this sheet is the current best model's alone. A new run (A4) tries again.",
                         "detail": f"thinking: {(prov.get('thinking') or {}).get('failed') or 'no Thinking forecast'}"})
    model_block = _model_block(run, pred)          # the run's model is the selected live model, or nothing is bet
    if model_block:
        notes.insert(0, {"plain": f"Every match is blocked: {model_block}.",
                         "detail": f"model check (22 Oct 2026): {model_block}"})
    gaps, noted = _gate_gaps(run)
    # a tour switched off since a live run was made (config.BET_TOURS, 28 Oct 2026); a replay (C8) keeps both tours
    off = CFG.off_mask(pred) & run.name.startswith("live_")
    if len(pred) and off.all():
        raise RuntimeError(f"every match of {run.name} is {CFG.off_names()}, and {CFG.off_names()} matches are switched "
                           "off (config.BET_TOURS): no sheet")
    shown = pred[~off]
    # the matches the run left out because of an error in their own row, and the earlier rounds it could not add
    # (left_out.json, 28 Oct 2026); a switched-off tour's are the switch's (counted in its note, not shown)
    from . import left_out as LO
    held = LO.read(run)
    off_rec = [r for r in held["matches"] if r.get("switched_off")
               or (run.name.startswith("live_") and CFG.tour_off(r.get("tour")))]
    held = {"matches": [r for r in held["matches"] if r not in off_rec], "earlier_rounds": held["earlier_rounds"]}
    rows = []
    for (_, p), m in zip(shown.iterrows(), _matchup_rows(shown, mu)):
        mid = p["match_id"]
        blocked, warn = ([model_block] if model_block else []), []
        mine = {name_key(x) for x in (p.get("player_a"), p.get("player_b")) if isinstance(x, str) and x.strip()}
        for e in held["earlier_rounds"]:                 # this match's player's earlier round, not in the run's data
            if mine & {name_key(x) for x in (e.get("winner"), e.get("loser")) if isinstance(x, str) and x.strip()}:
                warn.append(f"MISSING EARLIER ROUND: {LO.describe_earlier(e)} is not in the run's data, so this match "
                            f"is predicted without it ({e.get('reason')})")
        c = curves[curves["match_id"].eq(mid)].sort_values("odds_logit")
        x, qc = c["odds_logit"].to_numpy(), c["q_a"].to_numpy()
        p_mkt, q_a, quoted = float(p["p_market_a"]), float(p["q_a"]), None
        # the five-pattern adjustment (switched on 13 Oct 2026): q_a is the prediction used; q_off the one without it
        status = p.get("patterns") if isinstance(p.get("patterns"), str) else "off"
        q_off = _num(p.get("q_a_patterns_off"), q_a if status == "off" else float("nan"))
        # an ensemble run: q_a and q_off are the 50/50 log-odds ensemble's; each model's own chance beside them
        each = {c: _num(p.get(c)) for c in ("q_a_local", "q_a_local_patterns_off", "q_a_thinking")} if ensemble else {}
        d_a = d_b = over = limit = float("nan")
        home_is_a = None
        if m is not None:
            if isinstance(p.get("player_a"), str):
                home_is_a = name_key(m["player_a"]) == name_key(p["player_a"])
            pids = {str(p["player_a_id"]), str(p["player_b_id"])}
            ida, idb = _id(m.get("stage0_id_a")), _id(m.get("stage0_id_b"))
            if (ida or idb) and not _present_ids(m) <= pids:
                blocked.append("players read back differ from the linked ids")
            if ida:
                home_is_a = ida == str(p["player_a_id"])
            elif idb:
                home_is_a = idb == str(p["player_b_id"])
            if home_is_a is not None:
                pa_csv = float(m["p_a"]) if home_is_a else 1 - float(m["p_a"])
                if abs(pa_csv - p_mkt) > 1e-9:
                    blocked.append(f"price read-back mismatch ({pa_csv:.6f} sent, {p_mkt:.6f} used)")
                d_home, d_away = _odds(m, "a"), _odds(m, "b")
                d_a, d_b = (d_home, d_away) if home_is_a else (d_away, d_home)
                over, limit = m.get("overround", float("nan")), m.get("max_risk_stake", float("nan"))
            quoted = m.get("quoted_at")
            if isinstance(m.get("notes"), str) and m["notes"]:
                warn.append(m["notes"])
        if rep is not None and mid in rep.index:
            r = rep.loc[mid]
            p_mkt, q_a = float(r["p_market_a"]), float(r["q_a"])
            q_off = _num(r.get("q_a_patterns_off"), q_a if status == "off" else float("nan"))
            each = {c: _num(r.get(c)) for c in each}            # each model's curve read at the new price too
            if math.isnan(q_a):
                blocked.append(f"new price off the curve ({r.get('note')}): needs a new run")
            if rep_prices is not None and mid in rep_prices.index:
                rp = rep_prices.loc[mid]                       # live_prices wrote it oriented to side A
                quoted = rp.get("quoted_at", quoted)
                d_a, d_b = _odds(rp, "a"), _odds(rp, "b")
                over, limit = rp.get("overround", over), rp.get("max_risk_stake", limit)
        quoted = quoted if isinstance(quoted, str) and quoted else p.get("price_quoted_at")
        start = _utc(m["start_utc"])[0] if m is not None and isinstance(m.get("start_utc"), str) else None
        mins_to_start = (start - pd.Timestamp(now)).total_seconds() / 60 if start is not None else float("nan")
        age = float("nan")
        if isinstance(quoted, str) and quoted:
            qt, naive = _utc(quoted)
            age = (pd.Timestamp(now) - qt).total_seconds() / 60
            if naive:
                warn.append("the quote time carries no time zone: read as UTC")
        gate = str(p["gate"])
        if not gate.startswith("may be bet"):         # since 14 Oct 2026 only the indoor and qualifier checks block
            # the gate's blocking reasons, without its counts of missing box scores (gate_detail names those)
            why = [x.strip() for x in p["gate_reason"].split("; ") if x.strip() and not re.match(r"^\d+ earlier", x.strip())] \
                if isinstance(p.get("gate_reason"), str) else []
            blocked.append(f"gate: {gate}" + (f" ({' | '.join(why)})" if why else ""))
        # the edge bar a missing box score of a kind the training rows nearly always hold sets (gate.EDGE_BAR); a run
        # made before 14 Oct 2026 has none
        bar = _num(p.get("gate_edge_bar"), 0.0)
        bar = 0.0 if math.isnan(bar) else bar
        f = frame.loc[mid] if mid in frame.index else None
        if f is not None:
            # the main tour, and since 22 Oct 2026 its qualifying (docs/decisions/2026-10-22-qualifying-bets.md); a run
            # made before then has no "bettable" column and reads "main" as before
            if not bool(f.get("bettable", f.get("main", True))):
                blocked.append("not a main-tour or tour-level qualifying match (outside the model's population)")
            if not bool(f.get("format_supported", True)):
                blocked.append("unsupported match format")
        # no block for a listed start that has passed (the owner, 24 Oct 2026: "If it started I cant bet it. If it uses
        # a "live line" then I wont be able to bet it ... just give me the prediction")
        if not math.isnan(age) and age > stale_minutes:
            blocked.append(f"quote {age:.0f} min old (over {stale_minutes:.0f}): reprice")
        if not (GRID_LO <= p_mkt <= GRID_HI):
            warn.append("price outside the curve's 0.05-0.95: a later price cannot be read off it")
        sd = float(spread.get(mid, float("nan")))
        if not math.isnan(sd) and sd > SEED_SD_WARN:
            warn.append(f"the 16 seeds disagree (sd {sd:.3f})")
        k28 = {}
        if p["tour"] == "atp":
            for side in ("a", "b"):
                pid = str(p[f"player_{side}_id"])
                k28[side] = int(speed.loc[pid, "k28"]) if pid in speed.index else 0
            if min(k28.values()) == 0:
                warn.append("serve-speed form missing for a player (spd_L reads no data as 0)")
        q_b = 1 - q_a
        if math.isnan(d_a) or math.isnan(d_b):
            # without the bookmaker's own odds (its margin included) no EV can be computed: the margin-free price would
            # show losing bets as +EV (review V1, item 1)
            blocked.append("no bookmaker odds with their margin: no EV (pass odds, or use min_odds_to_bet = 1/q)")
            ev_a = ev_b = ev_a_off = ev_b_off = float("nan")
        else:
            ev_a, ev_b = q_a * d_a - 1, q_b * d_b - 1
            ev_a_off, ev_b_off = q_off * d_a - 1, (1 - q_off) * d_b - 1
        # with a bar, a side is picked only if its forecast moved the bar against it is still +EV at the odds (the
        # rule the gate review's replay tested); the EVs reported stay the forecast's own
        bars = [((q_a - bar) * d_a - 1, (q_b - bar) * d_b - 1),
                ((q_off - bar) * d_a - 1, (1 - q_off - bar) * d_b - 1)] if bar > 0 else \
            [(ev_a, ev_b), (ev_a_off, ev_b_off)]
        pick = "A" if bars[0][0] > 0 else ("B" if bars[0][1] > 0 else "")
        pick_off = "A" if bars[1][0] > 0 else ("B" if bars[1][1] > 0 else "")
        # what the bet rests on (28 Oct 2026): the same decision without stage 2's serve-speed term, which is added in
        # log-odds to each model (in a Thinking run to both, so to their average), before the patterns
        spd = _num(p.get("speed_term"), 0.0)
        q_ns = float(_expit(_logit(q_a) - spd)) if spd else q_a
        pick_ns = pick
        if spd and not (math.isnan(d_a) or math.isnan(d_b)):
            ns = ((q_ns - bar) * d_a - 1, (1 - q_ns - bar) * d_b - 1)
            pick_ns = "A" if ns[0] > 0 else ("B" if ns[1] > 0 else "")
        # the side the bar took away (it was +EV, but not by the bar)
        under_bar = ("A" if ev_a > 0 else ("B" if ev_b > 0 else "")) if bar > 0 and not pick else ""
        roots = curve_roots(x, qc) if len(x) else []
        nearest = _nearest(roots, p_mkt)
        # where each side's EV at the posted odds would be zero if Pinnacle's line moved there, its margin kept: the
        # sheet's "Zero edge if Pinnacle moves to" (24 Oct 2026; the margin kept is an agent's choice)
        over_now = 1 / d_a + 1 / d_b if not (math.isnan(d_a) or math.isnan(d_b)) else float("nan")
        zero_a, zero_b = zero_ev_roots(x, qc, over_now) if len(x) and math.isfinite(over_now) else ([], [])
        zero_near_a, zero_near_b = _nearest(zero_a, p_mkt), _nearest(zero_b, p_mkt)
        if not len(x):
            edge_note = "no curve for this match"
        elif roots:
            edge_note = ""
        else:
            edge_note = (f"no crossing in [0.05, 0.95]: the model favours side "
                         f"{'A' if qc[0] > _expit(x[0]) else 'B'} at every price")
        row = {
            "day": p["day"], "start_utc": m.get("start_utc") if m is not None else None,
            "minutes_to_start": round(mins_to_start) if not math.isnan(mins_to_start) else None,
            "tour": p["tour"], "tournament": p["tournament"], "round": p["round"],
            "best_of": f.get("in_best_of") if f is not None else None,
            "surface": surfaces.get(int(f["in_surface"])) if f is not None and not pd.isna(f.get("in_surface")) else None,
            "indoor": (bool(f["in_indoor"]) if f is not None and not pd.isna(f.get("in_indoor")) else None),
            "indoor_source": f.get("indoor_source") if f is not None else None,
            "player_a": p.get("player_a"), "player_b": p.get("player_b"),
            "player_a_id": p["player_a_id"], "player_b_id": p["player_b_id"],
            "price_source": (m.get("price_source") if m is not None else None) or p.get("price_source"),
            "quoted_at": quoted, "quote_age_min": round(age, 1) if not math.isnan(age) else None,
            "pinnacle_odds_a": round(d_a, 4), "pinnacle_odds_b": round(d_b, 4), "overround": over,
            "p_market_a": round(p_mkt, 6), "max_risk_stake": limit,
            "model": model, "p_base_a": round(float(p["p_base_a"]), 6), "eta": round(float(p["eta"]), 6),
            "spd_L": round(float(p["spd_L"]), 4), "speed_readings_28d_a": k28.get("a"),
            "speed_readings_28d_b": k28.get("b"), "q_a": round(q_a, 6), "q_b": round(q_b, 6),
            "patterns": status,
            "q_a_patterns_off": round(q_off, 6) if math.isfinite(q_off) else None,
            "q_a_patterns_on": round(q_a, 6) if status == "on" else None,
            "pattern_shift_pts_a": round(100 * (q_a - q_off), 3) if math.isfinite(q_off) else None,
            "edge_a_patterns_off": round(q_off - p_mkt, 6) if math.isfinite(q_off) else None,
            "ev_a_pinnacle_patterns_off": round(ev_a_off, 4) if math.isfinite(ev_a_off) else None,
            "ev_b_pinnacle_patterns_off": round(ev_b_off, 4) if math.isfinite(ev_b_off) else None,
            "fair_odds_a": round(1 / q_a, 4), "fair_odds_b": round(1 / q_b, 4),
            "seed_sd": round(sd, 4) if not math.isnan(sd) else None,
            "edge_a": round(q_a - p_mkt, 6), "ev_a_pinnacle": round(ev_a, 4), "ev_b_pinnacle": round(ev_b, 4),
            "break_even_p_a": ";".join(f"{r:.4f}" for r in roots) or None,
            "nearest_break_even_p_a": round(nearest, 4) if not math.isnan(nearest) else None,
            "break_even_note": edge_note or None,
            # each side's posted chance, margin included, at those zero-EV prices, and the one nearest the current price
            "zero_ev_implied_a": ";".join(f"{over_now * r:.4f}" for r in zero_a) or None,
            "nearest_zero_ev_implied_a": round(over_now * zero_near_a, 4) if math.isfinite(zero_near_a) else None,
            "zero_ev_implied_b": ";".join(f"{over_now * (1 - r):.4f}" for r in zero_b) or None,
            "nearest_zero_ev_implied_b": round(over_now * (1 - zero_near_b), 4) if math.isfinite(zero_near_b) else None,
        }
        row.update({c: round(v, 6) if math.isfinite(v) else None for c, v in each.items()})
        q_pick = q_a if pick == "A" else (q_b if pick == "B" else float("nan"))
        if blocked:
            pick = pick_off = pick_ns = ""
        names = {"a": p.get("player_a"), "b": p.get("player_b")}
        gone = []
        for s in ("a", "b"):                    # per player and event: "Ann Li's Wuhan R64, R32 (event of 2026-10-12)"
            by_event: dict = {}
            for x in missing_by.get(str(p[f"player_{s}_id"]), []):
                by_event.setdefault((x["event"], x["date"]), []).append(x["round"])
            gone += [f"{names[s]}'s {ev} {', '.join(rounds)} (event of {day})" for (ev, day), rounds in by_event.items()]

        def newest_of(s: str) -> str | None:
            n = newest.get(str(p[f"player_{s}_id"]))
            return f"{n['event']} {n['round']} ({n['day']})" if n else None
        row.update({
            "speed_term_pts_a": round(100 * (q_a - q_ns), 3) if spd else 0.0, "pick_no_speed": pick_ns,
            "speed_effect": speed_effect(pick, pick_ns) or None,
            "speed_last_reading_a": p.get("speed_last_reading_a") if p["tour"] == "atp" else None,
            "speed_last_reading_b": p.get("speed_last_reading_b") if p["tour"] == "atp" else None,
            "newest_result_a": newest_of("a"), "newest_result_b": newest_of("b"),
            "missing_results": "; ".join(gone) or None})
        row.update({
            "pick_patterns_off": pick_off, "patterns_effect": pattern_effect(pick, pick_off, status) or None,
            "pick": pick, "pick_player": (p.get("player_a") if pick == "A" else p.get("player_b")) if pick else None,
            "p_pick": round(q_pick, 6) if pick else None,
            "fair_odds_pick": round(1 / q_pick, 4) if pick else None,
            "min_odds_to_bet": round(1 / q_pick, 4) if pick else None,
            "pinnacle_odds_pick": round(d_a if pick == "A" else d_b, 4) if pick else None,
            "ev_pinnacle_pick": round(ev_a if pick == "A" else ev_b, 4) if pick else None})
        if venue_keys and not blocked:
            for side, name, q in (("a", p.get("player_a"), q_a), ("b", p.get("player_b"), q_b)):
                v = venue_keys.get(name_key(name)) if isinstance(name, str) else None
                if v is not None:
                    pay = _payout(v)
                    row[f"venue_payout_{side}"] = round(pay, 4)
                    row[f"ev_{side}_{venue or 'venue'}"] = round(q * (1 + (pay - 1) * (1 - venue_fee)) - 1, 4)
        if stake_rule == "owner_8oct" and pick:
            from src.eda.tabpfn_thinking58.common import stake
            row["stake_units_owner_8oct_research"] = round(float(stake(row["pinnacle_odds_pick"])), 3)
        row.update({"status": "predicted", "gate": gate, "gate_detail": gaps.get(mid),
                    "gate_edge_bar": bar if bar > 0 else None, "gate_notes": noted.get(mid),
                    "passed_by_bar": under_bar if under_bar and not blocked else None, "blocked": bool(blocked),
                    "block_reasons": "; ".join(blocked) or None, "warnings": "; ".join(warn) or None,
                    "home_side": None if home_is_a is None else ("A" if home_is_a else "B"),
                    "match_id": mid, "run": run.name})
        row["decision"] = BS.decision(row)
        rows.append(row)
    link = run / "matchups_linking.csv"
    listed_off = 0
    if link.exists() and left_out != "none":   # the window's other listed matches, with the reason each was left out
        lk = pd.read_csv(link)
        lk = lk[~lk["status"].eq("ok")]
        if left_out == "main":                  # main-tour singles and their qualifying (not Challengers, 125s, ITF,
            lk_off = CFG.off_mask(lk) & run.name.startswith("live_")   # doubles, in-play), not a switched-off tour's
            listed_off = int(lk_off.sum())
            lk = lk[~lk_off]
            lk = lk[lk["league"].astype(str).str.match(r"^(ATP|WTA) (?!Challenger|125)", case=False)
                    & ~lk["league"].astype(str).str.contains("Doubles", case=False)]
        for _, r in lk.iterrows():
            rows.append({"day": r.get("day"), "start_utc": r.get("start_utc"), "tour": r.get("tour"),
                         "tournament": r.get("tourney_name") if isinstance(r.get("tourney_name"), str) else r.get("league"),
                         "round": r.get("round"), "player_a": r.get("home"), "player_b": r.get("away"),
                         "pinnacle_odds_a": _decimal(r.get("price_home")), "pinnacle_odds_b": _decimal(r.get("price_away")),
                         "status": "not predicted", "blocked": True, "block_reasons": r.get("reason"),
                         "run": run.name, "pick": "", "decision": "NOT PREDICTED"})
    rows += _left_out_rows(run, mu, held)              # always shown: an error in a row is said loudly (28 Oct 2026)
    if off.any() or listed_off or off_rec:
        what = [f"this run's {int(off.sum())} {CFG.off_names()} predictions" if off.any() else "",
                f"the {listed_off} {CFG.off_names()} listings it did not predict" if listed_off else "",
                f"the {len(off_rec)} {CFG.off_names() or 'switched-off'} matches it left out before predicting"
                if off_rec else ""]
        notes.append({"plain": f"{(CFG.off_names() or 'Some tours').capitalize()} matches are switched off (the owner, "
                               "28 Oct 2026): "
                               f"{' and '.join(w for w in what if w)} are not on this sheet. The run's files keep them.",
                      "detail": f"config.BET_TOURS = {CFG.BET_TOURS} (docs/decisions/2026-10-28-women-switched-off.md)"})
    alerts = _left_out_alerts(held, len(shown))
    out = pd.DataFrame(rows)
    meta = {"run": CFG.rel(run), "run_name": run.name, "model": model,
            "instance": pred["instance"].iloc[0] if "instance" in pred else None,
            "checkpoint": pred["checkpoint"].iloc[0] if "checkpoint" in pred else None,
            "seeds": pred["seeds"].iloc[0] if "seeds" in pred else None, "stale_minutes": stale_minutes,
            "reprice_file": CFG.rel(reprice_file) if reprice_file else None, "venue_fee": venue_fee,
            "history_line": _read_json(run / "history.json").get("history_line"),
            "speed_km_h": ((prov.get("stage2") or {}).get("speed") or {}).get("standardiser_km_h"),
            "thinking": _thinking_line(prov.get("thinking")) if asked else None}
    sheet = BS.build(out, made_at=now, stake_rule=stake_rule, venue=venue, notes=notes, meta=meta, alerts=alerts)
    if write:
        live = run.name.startswith("live_")
        day = str(pred["day"].min())[:10]                 # the daily pipeline archives a run under its first day too
        base = CFG.PREDICTIONS / day if live else run
        records = base / "records" if live else run
        stem = first = f"bet_sheet_{sheet.made_at:%Y-%m-%d_%H%M}"
        k = 1
        while (base / f"{stem}.xlsx").exists() or (records / f"{stem}.csv").exists():
            k += 1                                        # one set per call: the file a bet rested on is never replaced
            stem = f"{first}_{k}"
        records.mkdir(parents=True, exist_ok=True)
        path, xlsx = records / f"{stem}.csv", base / f"{stem}.xlsx"
        sheet.files = {"Bet sheet": CFG.rel(xlsx), "Record (every figure)": CFG.rel(path),
                       "Provenance": CFG.rel(path.with_suffix(".provenance.json"))}
        out.to_csv(path, index=False)
        side = {"made_at": now.isoformat(timespec="seconds"),
                "written_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "run": CFG.rel(run),
                "model": model,
                "instance": meta["instance"], "checkpoint": meta["checkpoint"],
                "stage2": prov.get("stage2"), "thinking": prov.get("thinking"),
                "state_parts": states.get("parts_summary"),
                "history": meta["history_line"], "run_notes": notes, "alerts": alerts,
                "left_out": {**held, "switched_off": off_rec}, "files": sheet.files,
                "inputs": {n: _sha(run / n) for n in ("predictions.csv", "curves.parquet", "gate.csv",
                                                      "matchups_input.csv", "provenance.json")},
                "reprice_file": str(reprice_file) if reprice_file else None,
                "parameters": {"stale_minutes": stale_minutes, "venue": venue, "venue_fee": venue_fee,
                               "venue_prices": venue_prices, "stake_rule": stake_rule},
                "code_sha256": {"diagnostics.py": _sha(Path(__file__)), "bet_sheet.py": _sha(Path(BS.__file__))},
                "rules": __doc__}
        path.with_suffix(".provenance.json").write_text(json.dumps(side, indent=1, default=str), encoding="utf-8")
        try:
            BS.write_workbook(sheet, xlsx)
        except ImportError as e:                          # openpyxl is in the tennis env; elsewhere the record stands
            sheet.files.pop("Bet sheet")
            print(f"no workbook ({e}); the record is written")
    if show:
        BS.show(sheet)
    return out
