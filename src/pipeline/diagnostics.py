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
    stake            only with stake_rule="owner_8oct": the owner's research rule of 8 Oct 2026 (units, not a decided
                     staking rule; tabpfn_thinking58/common.stake)
    flags            blocked (no pick, no EV) with the reasons: the gate's "do not bet" (gate_detail: whose earlier
                     match lacks a box score), not a main-tour match, an unsupported format, a started match, a stale
                     quote, a price or player read-back mismatch, a price off the curve; warnings (this match's own):
                     players new since Stage 0, seeds that disagree, missing serve-speed form
    decision         BET (a pick), PASS (no side +EV at Pinnacle's odds), BLOCKED, NOT PREDICTED; home_side: the side
                     Pinnacle lists first
The run's own notes (the history check, recomputed state parts, an unclean results download) apply to every match:
they go to the provenance sidecar and the sheet's header, once, not into every row.
A newer price (reprice) is read off the run's curve, so edge and EV are always at the same moment as the price.
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


def pattern_effect(pick: str, pick_off: str, status: str) -> str:
    """How the five-pattern adjustment changes the decision (empty: no change, or the adjustment is off)."""
    if status != "on" or pick == pick_off:
        return ""
    if pick and not pick_off:
        return "bet only with the patterns"
    if pick_off and not pick:
        return "the patterns remove this bet"
    return "the patterns switch the side"


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


def curve_roots(odds_logit: np.ndarray, q: np.ndarray) -> list[float]:
    """Side A's prices p* where the model's forecast equals the price, q(p*) = p*: the sign changes of
    logit q - logit p along the curve, interpolated linearly in log-odds."""
    x = np.asarray(odds_logit, dtype=float)
    y = _logit(q) - x
    roots = []
    for i in range(len(x) - 1):
        if y[i] == 0:
            roots.append(float(_expit(x[i])))
        elif y[i] * y[i + 1] < 0:
            t = y[i] / (y[i] - y[i + 1])
            roots.append(float(_expit(x[i] + t * (x[i + 1] - x[i]))))
    if len(y) and y[-1] == 0:
        roots.append(float(_expit(x[-1])))
    return roots


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


def _gate_gaps(run: Path) -> dict:
    """Per live match, whose earlier match lacks a usable box score and why: "Casper Ruud's Laver Cup RR match (Tennis
    My Life has it, but our consistency check rejected it)" (the gate's own list; the cause from the run's Stage 0)."""
    p = run / "gate_missing.csv"
    if not p.exists():
        return {}
    g = pd.read_csv(p).astype({"live_match_id": str, "match_id": str})
    s0 = run / "stage0" / "stage0_matches.parquet"
    status = (pd.read_parquet(s0, columns=["match_id", "box_status"]).astype({"match_id": str})
              .set_index("match_id")["box_status"] if s0.exists() else pd.Series(dtype=object))
    out = {}
    for mid, rows in g.groupby("live_match_id", sort=False):
        items = []
        for r in rows.itertuples():
            cause = BOX_CAUSES.get(status.get(r.match_id))
            items.append(f"{r.player_name}'s {r.tournament_name} {r.round} match" + (f" ({cause})" if cause else ""))
        items = list(dict.fromkeys(items))
        out[mid] = items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]
    return out


def _sha(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None


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
    model = _read_json(run / "pipeline_model.json").get("model", CFG.LOCAL)
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
    gaps = _gate_gaps(run)
    rows = []
    for (_, p), m in zip(pred.iterrows(), _matchup_rows(pred, mu)):
        mid = p["match_id"]
        blocked, warn = [], []
        c = curves[curves["match_id"].eq(mid)].sort_values("odds_logit")
        x, qc = c["odds_logit"].to_numpy(), c["q_a"].to_numpy()
        p_mkt, q_a, quoted = float(p["p_market_a"]), float(p["q_a"]), None
        # the five-pattern adjustment (switched on 13 Oct 2026): q_a is the prediction used; q_off the one without it
        status = p.get("patterns") if isinstance(p.get("patterns"), str) else "off"
        q_off = _num(p.get("q_a_patterns_off"), q_a if status == "off" else float("nan"))
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
        if gate != "may be bet":
            blocked.append(f"gate: {gate}" + (f" ({p['gate_reason']})" if isinstance(p.get("gate_reason"), str) else ""))
        f = frame.loc[mid] if mid in frame.index else None
        if f is not None:
            if not bool(f.get("main", True)):
                blocked.append("not a main-tour match (outside the model's population)")
            if not bool(f.get("format_supported", True)):
                blocked.append("unsupported match format")
        if not math.isnan(mins_to_start) and mins_to_start <= 0:
            blocked.append("the match has started")
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
        pick = "A" if ev_a > 0 else ("B" if ev_b > 0 else "")
        pick_off = "A" if ev_a_off > 0 else ("B" if ev_b_off > 0 else "")
        roots = curve_roots(x, qc) if len(x) else []
        nearest = min(roots, key=lambda r: abs(_logit(r) - _logit(p_mkt))) if roots else float("nan")
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
        }
        q_pick = q_a if pick == "A" else (q_b if pick == "B" else float("nan"))
        if blocked:
            pick = pick_off = ""
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
        row.update({"status": "predicted", "gate": gate, "gate_detail": gaps.get(mid), "blocked": bool(blocked),
                    "block_reasons": "; ".join(blocked) or None, "warnings": "; ".join(warn) or None,
                    "home_side": None if home_is_a is None else ("A" if home_is_a else "B"),
                    "match_id": mid, "run": run.name})
        row["decision"] = BS.decision(row)
        rows.append(row)
    link = run / "matchups_linking.csv"
    if link.exists() and left_out != "none":   # the window's other listed matches, with the reason each was left out
        lk = pd.read_csv(link)
        lk = lk[~lk["status"].eq("ok")]
        if left_out == "main":                  # main-tour singles only (not Challengers, 125s, ITF, doubles, in-play)
            lk = lk[lk["league"].astype(str).str.match(r"^(ATP|WTA) (?!Challenger|125)", case=False)
                    & ~lk["league"].astype(str).str.contains("Doubles|Qualif", case=False)]
        for _, r in lk.iterrows():
            rows.append({"day": r.get("day"), "start_utc": r.get("start_utc"), "tour": r.get("tour"),
                         "tournament": r.get("tourney_name") if isinstance(r.get("tourney_name"), str) else r.get("league"),
                         "round": r.get("round"), "player_a": r.get("home"), "player_b": r.get("away"),
                         "pinnacle_odds_a": _decimal(r.get("price_home")), "pinnacle_odds_b": _decimal(r.get("price_away")),
                         "status": "not predicted", "blocked": True, "block_reasons": r.get("reason"),
                         "run": run.name, "pick": "", "decision": "NOT PREDICTED"})
    out = pd.DataFrame(rows)
    prov = _read_json(run / "provenance.json")
    meta = {"run": CFG.rel(run), "run_name": run.name, "model": model,
            "instance": pred["instance"].iloc[0] if "instance" in pred else None,
            "checkpoint": pred["checkpoint"].iloc[0] if "checkpoint" in pred else None,
            "seeds": pred["seeds"].iloc[0] if "seeds" in pred else None, "stale_minutes": stale_minutes,
            "reprice_file": CFG.rel(reprice_file) if reprice_file else None, "venue_fee": venue_fee,
            "history_line": _read_json(run / "history.json").get("history_line"),
            "speed_km_h": ((prov.get("stage2") or {}).get("speed") or {}).get("standardiser_km_h")}
    sheet = BS.build(out, made_at=now, stake_rule=stake_rule, venue=venue, notes=notes, meta=meta)
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
                "stage2": prov.get("stage2"), "state_parts": states.get("parts_summary"),
                "history": meta["history_line"], "run_notes": notes, "files": sheet.files,
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
