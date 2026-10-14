"""S2b, the luck builder of the unpriced-leads study (docs/studies/unpriced_leads/, 13 Oct 2026).

Brief: docs/studies/unpriced_leads/briefs/06_luck_builder.md (binding); definitions: team/point_structure.md §§ 3-4, 7.
Memo: docs/studies/unpriced_leads/team/luck_builder.md. Outputs: data/studies/unpriced_leads/candidates/luck/.

Registered direction: results carry scoring luck; rankings, results-based ratings and the crowd read it as skill; so a
player whose recent results ran ahead of his points is over-rated by the close (negative coefficient for the lucky
player). Persistence near zero is the premise.

PER-MATCH RESIDUALS e (one per player row of H.long_table: the current Stage 0 and match clock). A row is "eligible" when
the match is completed, has a box score, is in the standard format (Stage 0 `format`), its score is a complete best of 3
or 5 (every set complete, the winner took 2 of 3 or 3 of 5 and the last set) and its serve, return and total point counts
are consistent. p_i = spw_n / spw_d (own serve-point rate), p_j = 1 - rpw_n / rpw_d (the opponent's), T_i = tpw_n,
T_j = tpw_d - tpw_n. Best of 3 or 5 is read from the score (as Stage 2 does). Rule = stage2_iid.deciding_set_rule.
    PS01 tb        tb_won_n - sum over tiebreaks of pi~_TB(p_i, p_j, target); target 10 for a deciding tiebreak under a
                   10-point rule, else 7; pi~ = the iid tiebreak probability recalibrated (below). The bias check found
                   the raw iid pi at the match's own rates far too flat (2010-12: slope 1.8 men, 2.0 women), because the
                   rates contain the tiebreak's own points; fixed before any screen:
    PS01 tb_ex     (secondary) the same at the rates WITHOUT the tiebreaks' own points (the bracket gives the loser's
                   points; each player served half of them; the player's tiebreak points split between serve and return
                   as p_i : 1 - p_j), recalibrated (2010-12 slope 0.88-1.01: the iid model fits once they are out)
    PS01 tb_raw    (sensitivity) the analyst's literal form: raw iid pi at the match's rates, no recalibration
    PS06 close     sets won among the sets that reached 5-5 (every set whose loser had 5+ games: 7-5, 7-6, 13-12 and
                   advantage sets; 5-5 is identifiable from the score) minus sum of pi~_55, the iid chance of winning a set
                   from 5-5 under that set's rule (w + t pi_TB at 6-6; w / (w + l) in an advantage set; w (1 - t^7) / (1 - t)
                   + t^7 pi_TB7 under TB7@12; w = h_i (1 - h_j), l = (1 - h_i) h_j, t = 1 - w - l, h = stage2_iid.game);
                   serving order does not matter from 5-5 (shown in the memo)
    PS06 close_notb (secondary: the "7-5 remainder") 5-5 sets that ended without a tiebreak, won minus pi~ of w / (w + l)
    PS06 dec       deciding set played: 1[won] - pi~_set(p_i, p_j, rule) (stage2_iid.set_win); 0 when none was played
    PS03 save      S - F sbar(p_i)          sign -     sbar(p) = expit(c0 + c1 logit p), binomial logistic, by tour
    PS03 faced     F - G phibar(p_i)        sign +     phibar(p) = kappa_tour * f08_clutch.bp_per_game(p)
    PS03 conv      C - Ch (1 - sbar(p_j))   sign -     (= minus the opponent's save residual in the same match)
    PS03 chance    Ch - Gopp phibar(p_j)    sign -     (= the opponent's faced residual in the same match)
    PS03 hold      save - (1 - sbar(p_i)) faced   (games held beyond the iid expectation; exact algebra in the memo) sign -
    PS03 break     conv + (1 - sbar(p_j)) chance  (breaks beyond expectation)                                     sign -
    PS03 net       hold + break                                                                                    sign -
                   S, F = bp_saved_n/_d; C, Ch = bp_conv_n/_d; G, Gopp = hold_d, brk_d scaled so that G + Gopp equals the
                   score's non-tiebreak games (some feeds count tiebreaks as service games; no break point is faced in one);
                   where Stage 0 has no service games (women 2010-12 entirely, 56% of women's 2013-16) each player's G is
                   half the non-tiebreak games (the mean of the two possible serving splits; flag g_imputed). save and
                   conv need no G
    PS04 match     y - Lambda_P, logit Lambda_P = beta_{tour,bo} (T_i - T_j) / sqrt(T_i + T_j)   (the unit of run luck,
                   PS02's companion and PS02's Elo substitute)
    PS04 flat      logit((games_won_n + .5) / (games_won_d + 1)) - kappa_{tour,bo} logit((tpw_n + .5) / (tpw_d + 1))
    PS11 vis       1[lost with more points] - 1[won with fewer points]
CALIBRATION, fitted once on eligible rows of 2010-2012 (tournament year 2010-12, surely finished before 2013:
lf + 1 <= 1 Jan 2013, and not a frame match), side A only (the B rows mirror them), by tour (and best-of where stated),
frozen in calibration.json: the recalibration slope a of pi~ = expit(a logit pi) for tb, tb_ex, close, close_notb and dec
(tour x best-of; one-parameter binomial logistic without intercept: symmetric; a cell with too few rows borrows best of
3), sbar (tour), kappa_tour of phibar, beta (tour x best-of), kappa of flat (tour x best-of, least squares through the
origin). The PS01 bias check is the table of observed tiebreak wins against the raw iid pi by pi-bins, 2010-12, at the
match's rates and without the tiebreak points (calibration.json, ps01_bias_bins).

PLAYER STATISTICS (own matches in order: safe by construction; values from STRICTLY EARLIER rows of the same player):
    decayed sums   S_h = sum_{k' < k, eligible} 2^(-(t_k - t_k') / h) e_k', t = the clock's best-estimate day (obs, made
                   monotone per player), h = 91 days (primary; names end _h91), h = 365 (_h365) and a flat 52-week sum
                   (t_k - t_k' <= 364; _w52); 0 when there is no earlier eligible row (flag hist = 0); companions: the
                   decayed counts of eligible rows (n_h91, n_h365, n_w52)
    PS04 run       sum of `match` over the earlier eligible rows at this event (the player's consecutive rows with the same
                   tournament id, as the pool's on_n / U-138: qualifying shares the id); 0 when none; run_complete = every
                   earlier played match at this event was eligible
    PS04 flat      the previous played (not walked-over) row's flat if it was eligible, else 0 (flag flat_ok);
                   flat_event (secondary): the same, only if that row is at this event
    PS11 vis       sum over the last 10 eligible rows (strictly earlier) of vis; 0 without history; companion vis_n
    PS02 elogap    stage1_baselines' overall Elo (time rule kept: a week's results reach other events after the week, a
                   round's after the round), retirements counted (its frozen "ret" constants), run twice on every Stage 0
                   match: with the result y, and with Lambda_P in place of y on eligible matches. Gap = (R_y - R_Lambda)
                   ln10 / 400 before the match, in log-odds
Screened column: A - B (H.at_frame), raw and its orthogonal part (H.orthogonal_part); the pool's I-025 (store column
fi__B-OVERREACT__luck_13w) beside them.

Blinding: outcomes are read only through the harness (H.load_frame, the lenses: matches before 1 Jan 2025). Persistence
reads per-match residuals of matches surely finished before 1 Jan 2025; calibration reads 2010-12. Values are computed
for every frame match (2013-2026); coverage counts stop at 28 Jul 2026 (the sealed set is not counted).

Outputs (data/studies/unpriced_leads/candidates/luck/): values.parquet (every frame match: match_id, per statistic
<name>_a, <name>_b, <name> = A - B, companions lk_*_a/_b, the store's U-138 / U-307 differences; no result column),
long.csv and summary.csv (the harness's readings, raw and __orth), probes.json, coverage.json, calibration.json,
loading_c.csv (the close's loading c given the brief's Z, and c_pts given its points-only part, beside the harness's
beta), persistence.csv, residual_drift.csv, correlations.csv,
orth_coef.json (the frozen projections of every orthogonal part), build_info.json.

Run: ./python.sh src/eda/unpriced_leads/build_luck.py     (about 15 minutes, CPU; deterministic)
     --no-probe skips the timing probes (for a quick rebuild of the values only)
"""
from __future__ import annotations

import os

# one BLAS thread: the harness's many small fits run 100x slower with multithreaded BLAS on a busy machine (measured
# 13 Oct: 30-60 s per lens against 0.2-0.3 s); set before numpy is imported
for _v in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402
from src.eda.predictability_diagnostic import stage2_iid as IID  # noqa: E402

OUT = H.OUT / "candidates" / "luck"
STORE = ROOT / "data" / "studies" / "feature_universe" / "store.parquet"
DAY0 = pd.Timestamp("1970-01-01")
CAL_YEARS = (2010, 2012)
CAL_END_DAY = float((pd.Timestamp("2013-01-01") - DAY0).days)
DISC_END_DAY = float((H.DISCOVERY_END - DAY0).days)
SEALED = pd.Timestamp("2026-07-29")
HALVES = {"h91": 91.0, "h365": 365.0}
FLAT_DAYS = 364.0
LN2 = float(np.log(2.0))
LN10_400 = float(np.log(10.0) / 400.0)
P_CLIP = (0.01, 0.99)
# stage1_baselines_summary.json, "chosen", rule "ret" (retirements counted): tuned there on 2013-2018, frozen
ELO_K = {"atp": {"k0": 600.0, "offset": 2.0, "shape": 0.6}, "wta": {"k0": 600.0, "offset": 1.0, "shape": 0.6}}
ELO_START = 1500.0
PCOLS = ["spw_n", "spw_d", "rpw_n", "rpw_d", "tpw_n", "tpw_d", "hold_n", "hold_d", "brk_n", "brk_d",
         "bp_saved_n", "bp_saved_d", "bp_conv_n", "bp_conv_d", "tb_won_n", "tb_won_d", "sets_won_n", "sets_won_d",
         "games_won_n", "games_won_d"]
I025_COL = "fi__B-OVERREACT__luck_13w"           # the pool's I-025 (registry: canonical of m_I-025, r 1.0)
U138_COLS = ("fp__f17_info__bd11_on_n_a", "fp__f17_info__bd11_on_n_b")   # U-138 on_n (registry canonical)
U307_COL = "fi__B11__bd11_on"                    # U-307: log1p(on_n_A) - log1p(on_n_B), B11's On member
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def num(L: pd.DataFrame, c: str) -> np.ndarray:
    return np.array(pd.to_numeric(L[c], errors="coerce").to_numpy(dtype=float, na_value=np.nan), dtype=float)


def clip_logit(p) -> np.ndarray:
    p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


# ---------------------------------------------------------------------------------------------------- the data

def load_long() -> pd.DataFrame:
    """H.long_table with the box-score columns, plus Stage 0's `format` (a string: never scrambled by the probe)."""
    L = H.long_table(player_cols=PCOLS)
    m = pd.read_parquet(H.STAGE0_M, columns=["match_id", "format"])
    m["match_id"] = m["match_id"].astype(str)
    L = L.merge(m, on="match_id", how="left", validate="many_to_one")
    return L


SET_TOKEN = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")     # stage0_build.SET_TOKEN
SCORE_FIELDS = ("ok", "bo", "n_sets", "ntb", "n55_w", "n55_l", "nt55_w", "nt55_l", "dec", "dec55", "dec_tb",
                "tbw_W", "tbw_L", "tbl_W", "tbl_L", "dec_lp", "tb_pts_missing")


def parse_score(score) -> tuple:
    """A winner-first score: (ok, best of, sets, tiebreak sets, 5-5 sets won by the match winner / loser, 5-5 sets that
    ended without a tiebreak won by the winner / loser, deciding set played, deciding set reached 5-5, deciding set
    was a tiebreak; then the tiebreak points: over the non-deciding tiebreaks won by the match winner, the points of
    their winner and loser (tbw_W, tbw_L), the same over those won by the match loser (tbl_W, tbl_L), the loser's points
    in a deciding tiebreak (dec_lp, -1 if none), and whether any tiebreak lacks its points). ok: every token a complete
    standard set, the winner took 2 of 3 or 3 of 5 and the last set. A tiebreak's bracket holds its loser's points; the
    winner's are max(7, loser + 2) in a non-deciding tiebreak (a deciding one's target comes from the rule, per row)."""
    bad = (False, 0, 0, 0, 0, 0, 0, 0, False, False, False, 0, 0, 0, 0, -1, True)
    if not isinstance(score, str):
        return bad
    sets = []
    for tok in score.replace("&nbsp;", " ").replace(",", " ").split():
        mt = SET_TOKEN.match(tok)
        if not mt:
            return bad
        sets.append((int(mt.group(1)), int(mt.group(2)), int(mt.group(3)) if mt.group(3) else -1))
    if not sets:
        return bad
    sw = sum(a > b for a, b, _ in sets)
    sl = sum(b > a for a, b, _ in sets)
    if sw + sl != len(sets) or sw not in (2, 3) or sl >= sw or sets[-1][0] <= sets[-1][1]:
        return bad
    bo = 2 * sw - 1
    dec = len(sets) == bo
    ntb = n55w = n55l = nt55w = nt55l = 0
    tbw_W = tbw_L = tbl_W = tbl_L = 0
    dec_lp, missing = -1, False
    for i, (a, b, tb) in enumerate(sets):
        hi, lo = max(a, b), min(a, b)
        complete = (hi >= 6 and hi - lo >= 2) or (hi, lo) in ((7, 6), (13, 12)) or (tb >= 0 and hi - lo == 1 and hi >= 7)
        if not complete:
            return bad
        is_tb = tb >= 0 or (hi, lo) in ((7, 6), (13, 12))
        ntb += is_tb
        if lo >= 5:
            n55w += a > b
            n55l += b > a
            if not is_tb:
                nt55w += a > b
                nt55l += b > a
        if is_tb:
            missing |= tb < 0
            lp = tb if tb >= 0 else 5
            if dec and i == len(sets) - 1:
                dec_lp = lp
            elif a > b:
                tbw_W += max(7, lp + 2)
                tbw_L += lp
            else:
                tbl_W += max(7, lp + 2)
                tbl_L += lp
    a, b, tb = sets[-1]
    last_tb = tb >= 0 or (max(a, b), min(a, b)) in ((7, 6), (13, 12))
    return (True, bo, len(sets), ntb, n55w, n55l, nt55w, nt55l, dec, bool(dec and min(a, b) >= 5), bool(dec and last_tb),
            tbw_W, tbw_L, tbl_W, tbl_L, dec_lp, missing)


def score_table(scores: pd.Series) -> dict:
    codes, uniq = pd.factorize(scores.astype(object), use_na_sentinel=True)
    parsed = [parse_score(s) for s in uniq] + [parse_score(None)]      # the last entry: a missing score
    codes = np.where(codes < 0, len(uniq), codes)
    out = {}
    for i, f in enumerate(SCORE_FIELDS):
        out[f] = np.array([r[i] for r in parsed])[codes]
    return out


def rules_of(L: pd.DataFrame) -> np.ndarray:
    """The deciding-set rule per row (stage2_iid.deciding_set_rule), computed once per event and draw; year = the
    tournament date's year (Slams never start in late December)."""
    key = pd.DataFrame({"level": L["level"].astype(str).to_numpy(), "tournament_name": L["tournament_name"].astype(str).to_numpy(),
                        "year": pd.to_datetime(L["tournament_date"]).dt.year.to_numpy(),
                        "qualifying": L["qualifying"].astype(bool).to_numpy()})
    u = key.drop_duplicates().reset_index(drop=True)
    u["rule"] = IID.deciding_set_rule(u["level"], u["tournament_name"], u["year"], u["qualifying"]).to_numpy()
    return key.merge(u, on=["level", "tournament_name", "year", "qualifying"], how="left")["rule"].to_numpy(object)


def bp_per_game(p) -> np.ndarray:
    """f08_clutch.bp_per_game: the iid break points faced per service game at serve-point probability p."""
    p = np.asarray(p, float)
    q = 1 - p
    return q ** 3 + 4 * p * q ** 3 + 10 * p ** 2 * q ** 3 + 20 * p ** 3 * q ** 3 * q / (1 - 2 * p * q)


def facts(L: pd.DataFrame) -> dict:
    """Per row: eligibility and every quantity the residuals need (no calibration yet)."""
    F = {}
    won = L["won"].to_numpy(dtype=bool)
    F["won"] = won
    sc = score_table(L["score"])
    F.update({f"sc_{k}": v for k, v in sc.items()})
    spw_n, spw_d, rpw_n, rpw_d = num(L, "spw_n"), num(L, "spw_d"), num(L, "rpw_n"), num(L, "rpw_d")
    tpw_n, tpw_d = num(L, "tpw_n"), num(L, "tpw_d")
    with np.errstate(invalid="ignore", divide="ignore"):
        rates_ok = (spw_d > 0) & (rpw_d > 0) & (spw_n >= 0) & (spw_n <= spw_d) & (rpw_n >= 0) & (rpw_n <= rpw_d) \
            & (tpw_d > 0) & (tpw_n >= 0) & (tpw_n <= tpw_d) & (np.abs(tpw_d - spw_d - rpw_d) < 0.5) \
            & (np.abs(tpw_n - spw_n - rpw_n) < 0.5)
        p_i = np.where(rates_ok, spw_n / np.where(spw_d > 0, spw_d, 1), np.nan)
        p_j = np.where(rates_ok, 1 - rpw_n / np.where(rpw_d > 0, rpw_d, 1), np.nan)
    status = L["status"].astype(str).to_numpy()
    fmt = L["format"].astype(str).to_numpy()
    elig = (status == "completed") & L["has_box"].to_numpy(dtype=bool) & (fmt == "standard") & sc["ok"] & rates_ok
    F["elig"] = elig
    F["played"] = L["played"].to_numpy(dtype=bool)
    F["tour"] = L["tour"].astype(str).to_numpy()
    F["bo"] = np.where(elig, sc["bo"], 0)
    F["p_i"] = np.where(elig, np.clip(p_i, *P_CLIP), np.nan)
    F["p_j"] = np.where(elig, np.clip(p_j, *P_CLIP), np.nan)
    F["T_i"] = np.where(elig, tpw_n, np.nan)
    F["T_j"] = np.where(elig, tpw_d - tpw_n, np.nan)
    F["rule"] = rules_of(L)
    # tiebreaks: Stage 0's count must equal the score's (else PS01 is not computed for the row)
    tbn, tbd = num(L, "tb_won_n"), num(L, "tb_won_d")
    F["tb_ok"] = elig & np.isfinite(tbn) & np.isfinite(tbd) & (tbd == sc["ntb"]) & (tbn >= 0) & (tbn <= tbd)
    F["tb_n"], F["tb_d"] = tbn, tbd
    # PS01 secondary: the serve-point rates without the tiebreaks' own points. Each player served half of each
    # tiebreak's points; the player's tiebreak points are split between serve and return in proportion to the match's
    # serve and return rates (p_i : 1 - p_j)
    tdec = np.where(F["rule"] == "TB10@6", 10.0, 7.0)
    dlp = sc["dec_lp"].astype(float)
    decW = np.where(dlp >= 0, np.maximum(tdec, dlp + 2), 0.0)
    decL = np.where(dlp >= 0, dlp, 0.0)
    own = np.where(won, sc["tbw_W"] + sc["tbl_L"] + decW, sc["tbl_W"] + sc["tbw_L"] + decL).astype(float)
    opp = np.where(won, sc["tbw_L"] + sc["tbl_W"] + decL, sc["tbl_L"] + sc["tbw_W"] + decW).astype(float)
    npts = own + opp
    with np.errstate(invalid="ignore", divide="ignore"):
        xs = own * p_i / (p_i + 1 - p_j)
        d_i, d_j = spw_d - npts / 2, rpw_d - npts / 2
        pi_ex = (spw_n - xs) / np.where(d_i > 0, d_i, np.nan)
        pj_ex = 1 - (rpw_n - (own - xs)) / np.where(d_j > 0, d_j, np.nan)
    ex_ok = F["tb_ok"] & ~sc["tb_pts_missing"].astype(bool) & np.isfinite(pi_ex) & np.isfinite(pj_ex) \
        & (pi_ex > 0) & (pi_ex < 1) & (pj_ex > 0) & (pj_ex < 1)
    F["tb_ex_ok"] = ex_ok
    F["p_i_ex"] = np.where(ex_ok, np.clip(pi_ex, *P_CLIP), np.nan)
    F["p_j_ex"] = np.where(ex_ok, np.clip(pj_ex, *P_CLIP), np.nan)
    # break points and service games
    S, Fa = num(L, "bp_saved_n"), num(L, "bp_saved_d")
    C, Ch = num(L, "bp_conv_n"), num(L, "bp_conv_d")
    G, Go = num(L, "hold_d"), num(L, "brk_d")
    gtot = num(L, "games_won_d")
    with np.errstate(invalid="ignore", divide="ignore"):
        nontb = gtot - tbd
        scale = np.where(np.isfinite(nontb) & (G + Go > 0), nontb / (G + Go), 1.0)
    scale = np.where(np.isfinite(scale) & (scale > 0.8) & (scale <= 1.2), scale, np.nan)
    # save and conversion pieces need the break-point counts only
    F["bpS_ok"] = elig & np.isfinite(S) & np.isfinite(Fa) & np.isfinite(C) & np.isfinite(Ch) & (S >= 0) & (C >= 0) \
        & (S <= Fa) & (C <= Ch)
    # faced and chance pieces need service games: Stage 0's (scaled to the score's non-tiebreak games) or, where
    # Stage 0 has none (women 2010-12 entirely, 56% of women's 2013-16), half the non-tiebreak games each (the mean of
    # the two possible serving splits), flagged g_imputed
    exact = np.isfinite(G) & np.isfinite(Go) & (G > 0) & (Go > 0) & np.isfinite(scale)
    imput = ~exact & np.isfinite(nontb) & (nontb > 0)
    F["G"] = np.where(exact, G * scale, np.where(imput, nontb / 2, np.nan))
    F["Go"] = np.where(exact, Go * scale, np.where(imput, nontb / 2, np.nan))
    F["g_imputed"] = imput
    F["bpG_ok"] = F["bpS_ok"] & np.isfinite(F["G"]) & np.isfinite(F["Go"]) & (F["G"] > 0) & (F["Go"] > 0)
    F["S"], F["F"], F["C"], F["Ch"] = S, Fa, C, Ch
    # games and points shares (flattery)
    F["g_n"], F["g_d"] = num(L, "games_won_n"), num(L, "games_won_d")
    F["flat_ok"] = elig & np.isfinite(F["g_n"]) & np.isfinite(F["g_d"]) & (F["g_d"] > 0)
    F["tpw_n"], F["tpw_d"] = tpw_n, tpw_d
    return F


def iid_parts(F: dict) -> dict:
    """The raw iid chances on eligible rows (NaN elsewhere)."""
    e = F["elig"]
    n = len(e)
    out = {k: np.full(n, np.nan) for k in ("pi7", "pi_dectb", "pi55_std", "pi55_rule", "pi_notb", "pi_dec")}
    pi, pj = F["p_i"][e], F["p_j"][e]
    hi, hj = IID.game(pi), IID.game(pj)
    pi7 = IID.tiebreak(pi, pj, 7)
    pi10 = IID.tiebreak(pi, pj, 10)
    w, l = hi * (1 - hj), (1 - hi) * hj
    t = 1 - w - l
    rule = F["rule"][e]
    pi55_std = w + t * pi7
    r55 = np.select([rule == "TB10@6", rule == "ADV", rule == "TB7@12"],
                    [w + t * pi10, w / (w + l), w * (1 - t ** 7) / (1 - t) + t ** 7 * pi7], pi55_std)
    dec = np.full(len(pi), np.nan)
    for r in pd.unique(rule):
        m = rule == r
        dec[m] = IID.set_win(pi[m], pj[m], r)
    out["pi7"][e] = pi7
    out["pi_dectb"][e] = np.where(rule == "TB10@6", pi10, pi7)
    out["pi55_std"][e] = pi55_std
    out["pi55_rule"][e] = r55
    out["pi_notb"][e] = w / (w + l)
    out["pi_dec"][e] = dec
    x = F["tb_ex_ok"]
    out["pi7_ex"], out["pi_dectb_ex"] = np.full(n, np.nan), np.full(n, np.nan)
    p7x = IID.tiebreak(F["p_i_ex"][x], F["p_j_ex"][x], 7)
    p10x = IID.tiebreak(F["p_i_ex"][x], F["p_j_ex"][x], 10)
    out["pi7_ex"][x] = p7x
    out["pi_dectb_ex"][x] = np.where(F["rule"][x] == "TB10@6", p10x, p7x)
    return out


# ------------------------------------------------------------------------------------------------- calibration

def _fit_slope(z: np.ndarray, k: np.ndarray, n: np.ndarray) -> tuple[float, float]:
    """Binomial logistic without intercept: k successes of n at logit = a z. Returns (a, se)."""
    a = 1.0
    for _ in range(100):
        p = expit(a * z)
        g = np.sum(z * (k - n * p))
        h = np.sum(n * p * (1 - p) * z * z)
        step = g / max(h, 1e-12)
        a += step
        if abs(step) < 1e-12:
            break
    p = expit(a * z)
    return float(a), float(1 / np.sqrt(np.sum(n * p * (1 - p) * z * z)))


def _fit_logit2(x: np.ndarray, k: np.ndarray, n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Binomial logistic with intercept and slope on x. Returns (b, se)."""
    X = np.column_stack([np.ones(len(x)), x])
    b = np.zeros(2)
    for _ in range(100):
        p = expit(X @ b)
        g = X.T @ (k - n * p)
        Hm = (X.T * (n * p * (1 - p))) @ X
        step = np.linalg.solve(Hm, g)
        b += step
        if np.abs(step).max() < 1e-12:
            break
    p = expit(X @ b)
    Hm = (X.T * (n * p * (1 - p))) @ X
    return b, np.sqrt(np.diag(np.linalg.inv(Hm)))


def cal_rows(L: pd.DataFrame, F: dict) -> np.ndarray:
    """Eligible side-A rows of tournament years 2010-12 that surely finished before 2013 and are not frame matches."""
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    lf = num(L, "lf")
    frame_ids = set(pd.read_parquet(H.FRAME, columns=["match_id"])["match_id"].astype(str))
    not_frame = ~L["match_id"].astype(str).isin(frame_ids).to_numpy()
    return F["elig"] & (L["side"].astype(str).to_numpy() == "A") & (yr >= CAL_YEARS[0]) & (yr <= CAL_YEARS[1]) \
        & (lf + 1 <= CAL_END_DAY) & not_frame


def _cells(F: dict, m: np.ndarray, by_bo: bool) -> list[tuple[str, int, np.ndarray]]:
    out = []
    for tour in ("atp", "wta"):
        for bo in ((3, 5) if by_bo else (0,)):
            c = m & (F["tour"] == tour) & ((F["bo"] == bo) if by_bo else True)
            out.append((tour, bo, c))
    return out


def calibrate(L: pd.DataFrame, F: dict, P: dict) -> dict:
    """Every frozen constant, fitted on cal_rows; also the PS01 bias table (observed tiebreak wins against raw pi)."""
    m = cal_rows(L, F)
    cal = {"population": {"rows": int(m.sum()), "atp": int((m & (F["tour"] == "atp")).sum()),
                          "wta": int((m & (F["tour"] == "wta")).sum()),
                          "rule": "eligible side-A rows, tournament year 2010-2012, lf + 1 <= 2013-01-01, not frame matches"}}

    def slope_cells(name, z_k_n):
        res = {}
        for tour, bo, c in _cells(F, m, True):
            z, k, n = z_k_n(c)
            ok = np.isfinite(z) & np.isfinite(k) & (n > 0)
            if ok.sum() < 200 or n[ok].sum() < 500:
                res[f"{tour}_bo{bo}"] = None
                continue
            a, se = _fit_slope(z[ok], k[ok], n[ok])
            res[f"{tour}_bo{bo}"] = {"a": a, "se": se, "records": int(ok.sum()), "trials": float(n[ok].sum())}
        for tour in ("atp", "wta"):
            if res.get(f"{tour}_bo5") is None:
                res[f"{tour}_bo5"] = dict(res[f"{tour}_bo3"], borrowed_from="bo3")
        cal[name] = res

    tbn, tbd, dectb = F["tb_n"], F["tb_d"], F["sc_dec_tb"].astype(float)

    # PS01: records are tiebreaks; non-deciding ones share pi7, the deciding one has its target (all 7 points in 2010-12)
    def tb_records(c, ex=False):
        c = c & (F["tb_ex_ok"] if ex else F["tb_ok"])
        p7, pdt = (P["pi7_ex"], P["pi_dectb_ex"]) if ex else (P["pi7"], P["pi_dectb"])
        cd = c & (dectb > 0)
        nd = np.where(c, tbd - dectb, 0)
        # wins in non-deciding tiebreaks: total wins minus the deciding tiebreak's win (the match winner's)
        wd = np.where(c, dectb * F["won"], 0)
        z = np.r_[clip_logit(p7[c]), clip_logit(pdt[cd])]
        k = np.r_[(tbn - wd)[c], F["won"][cd].astype(float)]
        n = np.r_[nd[c], np.ones(int(cd.sum()))]
        return z, k, n, np.r_[F["bo"][c], F["bo"][cd]]

    slope_cells("a_tb", lambda c: tb_records(c)[:3])
    slope_cells("a_tb_ex", lambda c: tb_records(c, ex=True)[:3])

    n55w, n55l, dec55 = F["sc_n55_w"], F["sc_n55_l"], F["sc_dec55"].astype(float)
    won = F["won"]
    mine55 = np.where(won, n55w, n55l).astype(float)
    n55 = (n55w + n55l).astype(float)

    def z_55(c):
        z = np.r_[clip_logit(P["pi55_std"][c]), clip_logit(P["pi55_rule"][c & (dec55 > 0)])]
        k = np.r_[(mine55 - dec55 * won)[c], won[c & (dec55 > 0)].astype(float)]
        n = np.r_[(n55 - dec55)[c], np.ones(int((c & (dec55 > 0)).sum()))]
        return z, k, n
    slope_cells("a_close", z_55)

    nt_mine = np.where(won, F["sc_nt55_w"], F["sc_nt55_l"]).astype(float)
    nt = (F["sc_nt55_w"] + F["sc_nt55_l"]).astype(float)
    slope_cells("a_close_notb", lambda c: (clip_logit(P["pi_notb"][c]), nt_mine[c], nt[c]))
    dec = F["sc_dec"].astype(bool)
    slope_cells("a_dec", lambda c: (clip_logit(P["pi_dec"][c & dec]), won[c & dec].astype(float),
                                    np.ones(int((c & dec).sum()))))

    # PS03: sbar by tour (saves of break points faced, on logit p_i); phibar's kappa by tour
    cal["sbar"], cal["phibar_kappa"] = {}, {}
    for tour in ("atp", "wta"):
        c = m & F["bpS_ok"] & (F["tour"] == tour)
        # both sides of each match: side A rows only were selected, so add the mirrored B quantities (p_j, C, Ch)
        x = np.r_[clip_logit(F["p_i"][c]), clip_logit(F["p_j"][c])]
        k = np.r_[F["S"][c], F["Ch"][c] - F["C"][c]]
        n = np.r_[F["F"][c], F["Ch"][c]]
        ok = n > 0
        b, se = _fit_logit2(x[ok], k[ok], n[ok])
        cal["sbar"][tour] = {"c0": float(b[0]), "c1": float(b[1]), "se": se.tolist(), "player_matches": int(len(x)),
                             "bp_faced": float(n.sum()), "saved_share": float(k.sum() / n.sum()),
                             "naive_iid_share": float(np.sum(n * expit(x)) / n.sum())}
        c = m & F["bpG_ok"] & (F["tour"] == tour)
        Fsum = float(F["F"][c].sum() + F["Ch"][c].sum())
        Esum = float(np.sum(F["G"][c] * bp_per_game(F["p_i"][c])) + np.sum(F["Go"][c] * bp_per_game(F["p_j"][c])))
        cal["phibar_kappa"][tour] = {"kappa": Fsum / Esum, "bp_faced": Fsum, "iid_expected": Esum,
                                     "player_matches": int(2 * c.sum()),
                                     "service_games_imputed_share": float(F["g_imputed"][c].mean()) if c.any() else None}

    # PS04: beta (points-implied win probability) and kappa (games share on points share), tour x best-of
    cal["beta"], cal["kappa_flat"] = {}, {}
    T_i, T_j = F["T_i"], F["T_j"]
    with np.errstate(invalid="ignore", divide="ignore"):
        u = (T_i - T_j) / np.sqrt(T_i + T_j)
        lg_g = clip_logit((F["g_n"] + 0.5) / (F["g_d"] + 1))
        lg_p = clip_logit((F["tpw_n"] + 0.5) / (F["tpw_d"] + 1))
    for tour, bo, c in _cells(F, m, True):
        key = f"{tour}_bo{bo}"
        if c.sum() < 200:
            cal["beta"][key] = dict(cal["beta"][f"{tour}_bo3"], borrowed_from="bo3")
            cal["kappa_flat"][key] = dict(cal["kappa_flat"][f"{tour}_bo3"], borrowed_from="bo3")
            continue
        a, se = _fit_slope(u[c], won[c].astype(float), np.ones(int(c.sum())))
        cal["beta"][key] = {"beta": a, "se": se, "matches": int(c.sum())}
        cf = c & F["flat_ok"]
        kap = float(np.sum(lg_g[cf] * lg_p[cf]) / np.sum(lg_p[cf] ** 2))
        cal["kappa_flat"][key] = {"kappa": kap, "matches": int(cf.sum()),
                                  "r2": float(1 - np.sum((lg_g[cf] - kap * lg_p[cf]) ** 2) / np.sum(lg_g[cf] ** 2))}

    # the PS01 bias check: tiebreak records folded to the side the raw pi favours, by pi-bins; at the match's rates
    # (the brief's definition) and at the rates without the tiebreaks' own points (the secondary)
    rows = []
    for version, ex, slope in (("match_rates", False, "a_tb"), ("rates_without_tiebreak_points", True, "a_tb_ex")):
        for tour in ("atp", "wta"):
            c = m & (F["tour"] == tour)
            z, k, n, bo = tb_records(c, ex=ex)
            p = expit(z)
            fav = p >= 0.5
            pf = np.where(fav, p, 1 - p)
            kf = np.where(fav, k, n - k)
            a = np.where(bo == 5, cal[slope][f"{tour}_bo5"]["a"], cal[slope][f"{tour}_bo3"]["a"])
            pr = expit(a * np.abs(z))
            edges = [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.9, 1.0001]
            for lo_, hi_ in zip(edges[:-1], edges[1:]):
                b = (pf >= lo_) & (pf < hi_) & (n > 0)
                if not b.any():
                    continue
                nb = float(n[b].sum())
                obs = float(kf[b].sum() / nb)
                rows.append({"version": version, "tour": tour, "pi_bin": f"[{lo_:.2f},{min(hi_, 1):.2f})",
                             "tiebreaks": nb, "mean_raw_pi": float(np.sum(n[b] * pf[b]) / nb), "observed_share": obs,
                             "observed_se": float(np.sqrt(obs * (1 - obs) / nb)),
                             "mean_recalibrated_pi": float(np.sum(n[b] * pr[b]) / nb)})
    cal["ps01_bias_bins"] = rows
    return cal


def _cell_value(cal_part: dict, F: dict, field: str) -> np.ndarray:
    """A tour x best-of constant per row (NaN where the row is not eligible)."""
    out = np.full(len(F["tour"]), np.nan)
    for key, v in cal_part.items():
        tour, bo = key.split("_bo")
        m = (F["tour"] == tour) & (F["bo"] == int(bo))
        out[m] = v[field]
    return out


# --------------------------------------------------------------------------------------------------- residuals

RES_NAMES = ["tb", "tb_raw", "tb_ex", "close", "close_notb", "dec", "save", "faced", "conv", "chance", "hold", "break",
             "net", "match", "flat", "vis"]
DECAYED_ALL = ("tb", "close", "close_notb", "dec", "save", "faced", "conv", "chance", "hold", "break", "net", "match")
DECAYED_H91_ONLY = ("tb_raw", "tb_ex")


def residuals(F: dict, P: dict, cal: dict) -> dict:
    """Per row: every residual e (NaN where the row does not qualify)."""
    E = {}
    won = F["won"].astype(float)

    def recal(pi, name):
        return expit(_cell_value(cal[name], F, "a") * clip_logit(pi))

    dectb = F["sc_dec_tb"].astype(float)
    exp_tb = (F["tb_d"] - dectb) * recal(P["pi7"], "a_tb") + dectb * recal(P["pi_dectb"], "a_tb")
    E["tb"] = np.where(F["tb_ok"], F["tb_n"] - exp_tb, np.nan)
    # sensitivities: the analyst's literal form (raw iid at the match's rates) and the rates without tiebreak points
    exp_raw = (F["tb_d"] - dectb) * P["pi7"] + dectb * P["pi_dectb"]
    E["tb_raw"] = np.where(F["tb_ok"], F["tb_n"] - exp_raw, np.nan)
    exp_ex = (F["tb_d"] - dectb) * recal(P["pi7_ex"], "a_tb_ex") + dectb * recal(P["pi_dectb_ex"], "a_tb_ex")
    E["tb_ex"] = np.where(F["tb_ex_ok"], F["tb_n"] - np.where(F["tb_d"] > 0, exp_ex, 0.0), np.nan)
    n55 = (F["sc_n55_w"] + F["sc_n55_l"]).astype(float)
    dec55 = F["sc_dec55"].astype(float)
    mine55 = np.where(F["won"], F["sc_n55_w"], F["sc_n55_l"]).astype(float)
    exp55 = (n55 - dec55) * recal(P["pi55_std"], "a_close") + dec55 * recal(P["pi55_rule"], "a_close")
    E["close"] = np.where(F["elig"], mine55 - exp55, np.nan)
    nt = (F["sc_nt55_w"] + F["sc_nt55_l"]).astype(float)
    nt_mine = np.where(F["won"], F["sc_nt55_w"], F["sc_nt55_l"]).astype(float)
    E["close_notb"] = np.where(F["elig"], nt_mine - nt * recal(P["pi_notb"], "a_close_notb"), np.nan)
    dec = F["sc_dec"].astype(bool)
    E["dec"] = np.where(F["elig"], np.where(dec, won - recal(P["pi_dec"], "a_dec"), 0.0), np.nan)

    tour = F["tour"]
    c0 = np.select([tour == "atp", tour == "wta"], [cal["sbar"]["atp"]["c0"], cal["sbar"]["wta"]["c0"]], np.nan)
    c1 = np.select([tour == "atp", tour == "wta"], [cal["sbar"]["atp"]["c1"], cal["sbar"]["wta"]["c1"]], np.nan)
    kp = np.select([tour == "atp", tour == "wta"], [cal["phibar_kappa"]["atp"]["kappa"],
                                                    cal["phibar_kappa"]["wta"]["kappa"]], np.nan)
    sb_i = expit(c0 + c1 * clip_logit(F["p_i"]))
    sb_j = expit(c0 + c1 * clip_logit(F["p_j"]))
    okS, okG = F["bpS_ok"], F["bpG_ok"]
    e_s = F["S"] - F["F"] * sb_i
    e_f = F["F"] - F["G"] * kp * bp_per_game(F["p_i"])
    e_c = F["C"] - F["Ch"] * (1 - sb_j)
    e_ch = F["Ch"] - F["Go"] * kp * bp_per_game(F["p_j"])
    E["save"] = np.where(okS, e_s, np.nan)
    E["faced"] = np.where(okG, e_f, np.nan)
    E["conv"] = np.where(okS, e_c, np.nan)
    E["chance"] = np.where(okG, e_ch, np.nan)
    E["hold"] = np.where(okG, e_s - (1 - sb_i) * e_f, np.nan)
    E["break"] = np.where(okG, e_c + (1 - sb_j) * e_ch, np.nan)
    E["net"] = E["hold"] + E["break"]

    beta = _cell_value(cal["beta"], F, "beta")
    with np.errstate(invalid="ignore", divide="ignore"):
        u = (F["T_i"] - F["T_j"]) / np.sqrt(F["T_i"] + F["T_j"])
    lam = expit(beta * u)
    E["lambda_p"] = np.where(F["elig"], lam, np.nan)
    E["match"] = np.where(F["elig"], won - lam, np.nan)
    kap = _cell_value(cal["kappa_flat"], F, "kappa")
    lg_g = clip_logit((F["g_n"] + 0.5) / (F["g_d"] + 1))
    lg_p = clip_logit((F["tpw_n"] + 0.5) / (F["tpw_d"] + 1))
    E["flat"] = np.where(F["flat_ok"], lg_g - kap * lg_p, np.nan)
    E["vis"] = np.where(F["elig"], ((~F["won"]) & (F["T_i"] > F["T_j"])).astype(float)
                        - (F["won"] & (F["T_i"] < F["T_j"])).astype(float), np.nan)
    return E


# ------------------------------------------------------------------------------------------------- aggregation

def _player_index(L: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(player code, non-decreasing along the rows; t = obs_mono in days)."""
    pc = pd.factorize(L["player_id"])[0]
    if np.any(np.diff(pc) < 0):
        raise RuntimeError("the long table is not grouped by player")
    t = num(L, "obs_mono")
    return pc, t


def _excl_cumsum(pc: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Per player, the sum of v over STRICTLY EARLIER rows: the inclusive prefix sum shifted by one row (bit-exact:
    never inclusive-minus-own)."""
    inc = pd.Series(v).groupby(pc).cumsum().to_numpy()
    out = np.r_[0.0, inc[:-1]]
    first = np.r_[True, pc[1:] != pc[:-1]]
    out[first] = 0.0
    return out


def decayed(pc: np.ndarray, t: np.ndarray, e: np.ndarray, h: float) -> tuple[np.ndarray, np.ndarray]:
    """S = sum over strictly earlier rows with e finite of 2^(-(t_k - t_k') / h) e_k'; N the same of 1."""
    t0 = pd.Series(t).groupby(pc).transform("first").to_numpy()
    u = (t - t0) * LN2 / h
    ok = np.isfinite(e)
    eu = np.exp(u)
    S = np.exp(-u) * _excl_cumsum(pc, np.where(ok, eu * np.where(ok, e, 0.0), 0.0))
    N = np.exp(-u) * _excl_cumsum(pc, np.where(ok, eu, 0.0))
    return S, N


def flat_window(pc: np.ndarray, t: np.ndarray, e: np.ndarray, days: float = FLAT_DAYS) -> tuple[np.ndarray, np.ndarray]:
    """Sum (and count) over strictly earlier rows with e finite and t_k - t_k' <= days."""
    ok = np.isfinite(e)
    key = pc.astype(float) * 1e6 + t
    if np.any(np.diff(key) < 0):
        raise RuntimeError("days are not monotone within players")
    j = np.searchsorted(key, key - days, side="left")
    Ex = _excl_cumsum(pc, np.where(ok, e, 0.0))
    Nx = _excl_cumsum(pc, ok.astype(float))
    return Ex - Ex[j], Nx - Nx[j]


def player_stats(L: pd.DataFrame, cal: dict) -> pd.DataFrame:
    """The builder probed by H.timing_probe: every player statistic per (match, player), from L's facts only."""
    F = facts(L)
    P = iid_parts(F)
    E = residuals(F, P, cal)
    pc, t = _player_index(L)
    out = {"match_id": L["match_id"].astype(str).to_numpy(), "player_id": L["player_id"].to_numpy()}
    elig = F["elig"]
    base = np.where(elig, 0.0, np.nan)
    for hn, h in HALVES.items():
        _, N = decayed(pc, t, base, h)
        out[f"n_{hn}"] = N
    _, N52 = flat_window(pc, t, base)
    out["n_w52"] = N52
    out["hist"] = (_excl_cumsum(pc, elig.astype(float)) > 0).astype(float)
    for r in DECAYED_ALL:
        for hn, h in HALVES.items():
            out[f"{r}_{hn}"], _ = decayed(pc, t, E[r], h)
        out[f"{r}_w52"], _ = flat_window(pc, t, E[r])
    for r in DECAYED_H91_ONLY:
        out[f"{r}_h91"], _ = decayed(pc, t, E[r], HALVES["h91"])
    # PS04 run luck: earlier eligible rows in the same event segment (consecutive rows with the same tournament id)
    tid = L["tournament_id"].astype(str).to_numpy()
    new_seg = np.r_[True, (pc[1:] != pc[:-1]) | (tid[1:] != tid[:-1])]
    seg = np.cumsum(new_seg) - 1
    em = E["match"]
    out["run"] = _excl_cumsum(seg, np.where(np.isfinite(em), em, 0.0))
    run_n = _excl_cumsum(seg, np.isfinite(em).astype(float))
    played = F["played"]
    run_played = _excl_cumsum(seg, played.astype(float))
    out["run_n"] = run_n
    out["on_n"] = run_played                               # = the pool's on_n (U-138), rebuilt here as a check
    out["run_complete"] = (run_n == run_played).astype(float)
    # PS04 flattery: the previous played row (any event; and the same-event secondary)
    n = len(L)
    idx = np.arange(n)
    pidx = pd.Series(np.where(played, idx, -1)).groupby(pc).cummax().to_numpy()
    prev = np.r_[-1, pidx[:-1]]
    prev[np.r_[True, pc[1:] != pc[:-1]]] = -1
    pv = np.maximum(prev, 0)
    fl = E["flat"]
    has = (prev >= 0) & np.isfinite(fl[pv])
    out["flat"] = np.where(has, fl[pv], 0.0)
    out["flat_ok"] = has.astype(float)
    seg_start = pd.Series(idx).groupby(seg).transform("min").to_numpy()
    has_ev = has & (prev >= seg_start)
    out["flat_event"] = np.where(has_ev, fl[pv], 0.0)
    out["flat_event_ok"] = has_ev.astype(float)
    # PS11: the last 10 eligible rows, strictly earlier
    v = E["vis"]
    okv = np.isfinite(v)
    A = _excl_cumsum(pc, np.where(okv, v, 0.0))
    M = _excl_cumsum(pc, okv.astype(float)).astype(np.int64)
    okrows = np.flatnonzero(okv)
    pok = pc[okrows]
    first_row = pd.Series(idx).groupby(pc).transform("min").to_numpy()
    start = np.searchsorted(pok, pc, side="left")
    deep = M > 10
    pos = np.where(deep, start + M - 10, 0)
    r = np.where(deep, okrows[np.minimum(pos, len(okrows) - 1)], first_row)
    out["vis"] = A - A[r]
    out["vis_n"] = np.minimum(M, 10).astype(float)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ PS02: the Elo gap

def _elo_two(week, event, rnd, a, b, upd, res1, res2, n_players, k0, offset, shape) -> np.ndarray:
    """stage1_baselines.elo_pass's overall rating, run with two result vectors at once (same K, same counts).
    Returns per match: A's and B's rating before it under res1, then under res2."""
    R1 = [ELO_START] * n_players
    R2 = [ELO_START] * n_players
    N = [0] * n_players
    out = np.empty((len(week), 4))
    lo: dict = {}
    cur = None
    for i in range(len(week)):
        if week[i] != cur:
            for (p, _), st in lo.items():
                R1[p] += st[0] + st[4]
                R2[p] += st[1] + st[5]
                N[p] += st[2] + st[6]
            lo.clear()
            cur = week[i]
        e, r, pa, pb = event[i], rnd[i], a[i], b[i]
        xa = lo.get((pa, e))
        if xa is None:
            xa = lo[(pa, e)] = [0.0, 0.0, 0, r, 0.0, 0.0, 0]
        elif xa[3] < r:
            xa[0] += xa[4]; xa[1] += xa[5]; xa[2] += xa[6]; xa[3] = r; xa[4] = 0.0; xa[5] = 0.0; xa[6] = 0  # noqa: E702
        xb = lo.get((pb, e))
        if xb is None:
            xb = lo[(pb, e)] = [0.0, 0.0, 0, r, 0.0, 0.0, 0]
        elif xb[3] < r:
            xb[0] += xb[4]; xb[1] += xb[5]; xb[2] += xb[6]; xb[3] = r; xb[4] = 0.0; xb[5] = 0.0; xb[6] = 0  # noqa: E702
        ra1, rb1 = R1[pa] + xa[0], R1[pb] + xb[0]
        ra2, rb2 = R2[pa] + xa[1], R2[pb] + xb[1]
        out[i, 0], out[i, 1], out[i, 2], out[i, 3] = ra1, rb1, ra2, rb2
        if upd[i]:
            na, nb = N[pa] + xa[2], N[pb] + xb[2]
            ka, kb = k0 / (na + offset) ** shape, k0 / (nb + offset) ** shape
            s1 = res1[i] - 1.0 / (1.0 + 10.0 ** ((rb1 - ra1) / 400.0))
            s2 = res2[i] - 1.0 / (1.0 + 10.0 ** ((rb2 - ra2) / 400.0))
            xa[4] += ka * s1
            xb[4] -= kb * s1
            xa[5] += ka * s2
            xb[5] -= kb * s2
            xa[6] += 1
            xb[6] += 1
    return out


def elo_gap(L: pd.DataFrame, cal: dict, with_ratings: bool = False) -> pd.DataFrame:
    """The builder of PS02 (probed): both Elo runs over every match of L (side A rows), per tour, in the time rule's
    order (tournament date, event, round). Lambda_P replaces y on eligible matches."""
    F = facts(L)
    E = residuals(F, iid_parts(F), cal)
    sideA = L["side"].astype(str).to_numpy() == "A"
    d = pd.DataFrame({"match_id": L["match_id"].astype(str).to_numpy()[sideA],
                      "a": L["player_id"].to_numpy()[sideA], "b": L["opponent_id"].to_numpy()[sideA],
                      "tour": F["tour"][sideA], "tday": num(L, "tday")[sideA],
                      "tid": L["tournament_id"].astype(str).to_numpy()[sideA],
                      "rnd": num(L, "round_order")[sideA], "mnum": L["match_num"].astype(str).to_numpy()[sideA],
                      "status": L["status"].astype(str).to_numpy()[sideA],
                      "y": F["won"][sideA].astype(float), "lam": E["lambda_p"][sideA]})
    d = d.sort_values(["tour", "tday", "tid", "rnd", "mnum", "match_id"], kind="mergesort").reset_index(drop=True)
    upd = d["status"].isin(["completed", "retired"]).to_numpy()
    res2 = np.where(np.isfinite(d["lam"].to_numpy()), d["lam"].to_numpy(), d["y"].to_numpy())
    parts = []
    for tour in ("atp", "wta"):
        g = d[d["tour"] == tour]
        if g.empty:
            continue
        ii = g.index.to_numpy()
        players, codes = np.unique(np.r_[g["a"].to_numpy(), g["b"].to_numpy()], return_inverse=True)
        event = pd.factorize(g["tday"].astype(str) + "|" + g["tid"])[0]
        k = ELO_K[tour]
        o = _elo_two(g["tday"].tolist(), event.tolist(), g["rnd"].astype(int).tolist(), codes[:len(g)].tolist(),
                     codes[len(g):].tolist(), upd[ii].tolist(), d["y"].to_numpy()[ii].tolist(), res2[ii].tolist(),
                     len(players), k["k0"], k["offset"], k["shape"])
        ga = (o[:, 0] - o[:, 2]) * LN10_400
        gb = (o[:, 1] - o[:, 3]) * LN10_400
        pa = pd.DataFrame({"match_id": g["match_id"].to_numpy(), "player_id": g["a"].to_numpy(), "elogap": ga})
        pb = pd.DataFrame({"match_id": g["match_id"].to_numpy(), "player_id": g["b"].to_numpy(), "elogap": gb})
        if with_ratings:
            pa["elo_y"], pb["elo_y"] = o[:, 0], o[:, 1]
            pa["elo_lam"], pb["elo_lam"] = o[:, 2], o[:, 3]
        parts += [pa, pb]
    return pd.concat(parts, ignore_index=True)


# ------------------------------------------------------------------------------------------- the statistics screened

def stat_list() -> list[dict]:
    """name, the per-player column, the registered sign, the per-match residual unit, tier, informative flag."""
    S = []
    prim = [("PS01_tb", "tb", "-"), ("PS06_close", "close", "-"), ("PS06_dec", "dec", "-"),
            ("PS03_save", "save", "-"), ("PS03_faced", "faced", "+"), ("PS03_conv", "conv", "-"),
            ("PS03_chance", "chance", "-"), ("PS03_hold", "hold", "-"), ("PS03_break", "break", "-"),
            ("PS03_net", "net", "-")]
    for name, r, sign in prim:
        S.append({"name": name, "col": f"{r}_h91", "sign": sign, "unit": r, "tier": "primary", "inf": "hist"})
    S += [{"name": "PS04_run", "col": "run", "sign": "-", "unit": "match", "tier": "primary", "inf": "run_complete"},
          {"name": "PS04_flat", "col": "flat", "sign": "-", "unit": "flat", "tier": "primary", "inf": "flat_ok"},
          {"name": "PS11_vis", "col": "vis", "sign": "+", "unit": "vis", "tier": "primary", "inf": "vis_any"},
          {"name": "PS02_elogap", "col": "elogap", "sign": "-", "unit": "match", "tier": "primary", "inf": "hist"},
          {"name": "I025_pool", "col": None, "sign": "-", "unit": "match", "tier": "pool comparison", "inf": "store"}]
    S += [{"name": "PS01_tb_ex", "col": "tb_ex_h91", "sign": "-", "unit": "tb_ex", "tier": "secondary", "inf": "hist"},
          {"name": "PS01_tb_raw", "col": "tb_raw_h91", "sign": "-", "unit": "tb_raw", "tier": "sensitivity",
           "inf": "hist"},
          {"name": "PS06_close_notb", "col": "close_notb_h91", "sign": "-", "unit": "close_notb", "tier": "secondary",
           "inf": "hist"},
          {"name": "PS04_flat_event", "col": "flat_event", "sign": "-", "unit": "flat", "tier": "secondary",
           "inf": "run_complete"},
          {"name": "PS02_match", "col": "match_h91", "sign": "-", "unit": "match", "tier": "secondary", "inf": "hist"}]
    stems = {"tb": "PS01_tb", "close": "PS06_close", "close_notb": "PS06_close_notb", "dec": "PS06_dec",
             "save": "PS03_save", "faced": "PS03_faced", "conv": "PS03_conv", "chance": "PS03_chance",
             "hold": "PS03_hold", "break": "PS03_break", "net": "PS03_net", "match": "PS02_match"}
    signs = {s["unit"]: s["sign"] for s in S if s["col"] and s["col"].endswith("_h91")}
    for r, stem in stems.items():
        for suf in ("h365", "w52"):
            S.append({"name": f"{stem}_{suf}", "col": f"{r}_{suf}", "sign": signs[r], "unit": r,
                      "tier": "decay secondary", "inf": "hist"})
    return S


def store_columns(match_ids: pd.Series) -> pd.DataFrame:
    """The pool's I-025 and U-138 / U-307 from the feature store, by match id (NaN where the store lacks the match)."""
    cols = ["match_id", I025_COL, "fp__f18_overreact__luck_a", "fp__f18_overreact__luck_b", U307_COL, *U138_COLS]
    s = pd.read_parquet(STORE, columns=cols)
    s["match_id"] = s["match_id"].astype(str)
    s = s.drop_duplicates("match_id").set_index("match_id")
    return s.reindex(match_ids.astype(str).to_numpy())


def informative(A: dict, Bm: dict, inf: str) -> np.ndarray:
    """Both players have the history the statistic needs (0 is then a measured value, not a default)."""
    if inf == "hist":
        return (A["hist"] > 0) & (Bm["hist"] > 0)
    if inf == "run_complete":
        return (A["run_complete"] > 0) & (Bm["run_complete"] > 0)
    if inf == "flat_ok":
        return (A["flat_ok"] > 0) & (Bm["flat_ok"] > 0)
    if inf == "vis_any":
        return (A["vis_n"] > 0) & (Bm["vis_n"] > 0)
    raise ValueError(inf)


COMPANIONS = ["n_h91", "n_h365", "n_w52", "hist", "run_n", "run_complete", "on_n", "flat_ok", "flat_event_ok", "vis_n"]


def at_frame_all(V: pd.DataFrame, cols: list[str], frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """H.at_frame for many columns at once (one index): (A's values, B's values), NaN where absent."""
    v = V[["match_id", "player_id"] + cols].drop_duplicates(["match_id", "player_id"]).astype({"match_id": str})
    v = v.set_index(["match_id", "player_id"])[cols]
    ka = pd.MultiIndex.from_arrays([frame["match_id"].astype(str), frame["player_a_id"]])
    kb = pd.MultiIndex.from_arrays([frame["match_id"].astype(str), frame["player_b_id"]])
    return v.reindex(ka).reset_index(drop=True), v.reindex(kb).reset_index(drop=True)


def values_for(V: pd.DataFrame, frame: pd.DataFrame, stats: list[dict]) -> tuple[pd.DataFrame, dict]:
    """Per frame row: every statistic's A, B and A - B, the companions (lk_<c>_a/_b), and the informative masks."""
    out = {"match_id": frame["match_id"].astype(str).to_numpy()}
    cols = COMPANIONS + [s["col"] for s in stats if s["col"] is not None]
    VA, VB = at_frame_all(V, list(dict.fromkeys(cols)), frame)
    A, Bm = {}, {}
    for c in COMPANIONS:
        a, b = VA[c].to_numpy(float), VB[c].to_numpy(float)
        out[f"lk_{c}_a"], out[f"lk_{c}_b"] = a, b
        A[c], Bm[c] = a, b
    store = store_columns(frame["match_id"])
    masks = {}
    for s in stats:
        if s["col"] is None:
            a = store["fp__f18_overreact__luck_a"].to_numpy(float)
            b = store["fp__f18_overreact__luck_b"].to_numpy(float)
            x = store[I025_COL].to_numpy(float)
            masks[s["name"]] = np.isfinite(x)
        else:
            a, b = VA[s["col"]].to_numpy(float), VB[s["col"]].to_numpy(float)
            x = a - b
            masks[s["name"]] = informative(A, Bm, s["inf"]) & np.isfinite(x)
        out[f"{s['name']}_a"], out[f"{s['name']}_b"], out[s["name"]] = a, b, x
    out["U138_on_n_store"] = store[U138_COLS[0]].to_numpy(float) - store[U138_COLS[1]].to_numpy(float)
    out["U307_on_log_store"] = store[U307_COL].to_numpy(float)
    return pd.DataFrame(out), masks


# ------------------------------------------------------------------------------- the close's loading c (§ 4 gate)

def skill_inputs() -> list[str]:
    """Point-based skill Z: the model's 49 non-price inputs without elo_* and points_52w (point_structure.md § 4)."""
    return [n for n in H.diff_input_names() if not n.startswith("elo_") and n != "points_52w"]


CONVERSION_INPUTS = ("hold", "brk", "bp_saved", "bp_conv", "bp_faced_pg")


def points_only_inputs() -> list[str]:
    """A sensitivity of the gate (added after the first gate readings, for a structural reason): Z without the inputs
    that are themselves conversion results (holds, breaks, break points saved, converted and faced per game: form_*,
    formdef_*, iosO/D_*, prod_*), which carry the very luck being tested."""
    return [n for n in skill_inputs() if not any(n.endswith(s) for s in CONVERSION_INPUTS)]


def _ols_c(frame: pd.DataFrame, m: np.ndarray, zn: list[str], x: np.ndarray) -> tuple[float, float]:
    Z = frame.loc[m, [f"in_{n}" for n in zn]].to_numpy(float)
    Z = np.where(np.isfinite(Z), Z, 0.0)
    Z = Z[:, np.abs(Z).sum(axis=0) > 0]                       # an input absent in the whole cell carries nothing
    X = np.column_stack([Z, H.rms_scale(x[m])])
    coef, se = H.ols_cluster(X, frame.loc[m, "L"].to_numpy(float), frame.loc[m, "block"].to_numpy())
    return float(coef[-1]), float(se[-1])


def _pool(est: pd.Series, se: pd.Series) -> tuple[float, float]:
    ok = np.isfinite(se) & (se > 0)
    w = 1 / se[ok] ** 2
    if w.sum() == 0:
        return np.nan, np.nan
    return float((w * est[ok]).sum() / w.sum()), float(np.sqrt(1 / w.sum()))


def loading_c(frame: pd.DataFrame, x: np.ndarray, name: str, long: pd.DataFrame) -> list[dict]:
    """Per tour and era (<= 2024): least squares of the close's log-odds L on Z and x (x per its RMS in the cell; no
    intercept: antisymmetric), clustered by four-week block; pooled over eras by inverse variance; beside the harness's
    close-lens beta for the same cell. c uses the brief's Z; c_pts the points-only Z (points_only_inputs)."""
    zn, zp = skill_inputs(), points_only_inputs()
    rows = []
    for tour in ("atp", "wta"):
        for era, (a, b) in H.ERAS.items():
            m = (frame["tour"] == tour).to_numpy() & frame["season"].between(a, b).to_numpy()
            c, sc = _ols_c(frame, m, zn, x)
            cp, scp = _ols_c(frame, m, zp, x)
            r = long[(long["name"] == name) & (long["lens"] == "close") & (long["era"] == era) & (long["tour"] == tour)]
            rows.append({"name": name, "tour": tour, "era": era, "c": c, "se_c": sc,
                         "z_c": c / sc if sc > 0 else np.nan, "c_pts": cp, "se_c_pts": scp,
                         "z_c_pts": cp / scp if scp > 0 else np.nan, "n": int(m.sum()),
                         "beta": float(r["beta"].iloc[0]) if len(r) else np.nan,
                         "se_beta": float(r["se"].iloc[0]) if len(r) else np.nan,
                         "z_beta": float(r["z"].iloc[0]) if len(r) else np.nan})
    d = pd.DataFrame(rows)
    for tour, g in list(d.groupby("tour")) + [("both", d)]:
        c, sc = _pool(g["c"], g["se_c"])
        cp, scp = _pool(g["c_pts"], g["se_c_pts"])
        bp, sb = _pool(g["beta"], g["se_beta"])
        rows.append({"name": name, "tour": tour, "era": "2013-24 pooled", "c": c, "se_c": sc, "z_c": c / sc,
                     "c_pts": cp, "se_c_pts": scp, "z_c_pts": cp / scp, "n": int(g["n"].sum()), "beta": bp,
                     "se_beta": sb, "z_beta": bp / sb if sb else np.nan, "eras_c_positive": int((g["c"] > 0).sum()),
                     "eras_c_pts_positive": int((g["c_pts"] > 0).sum())})
    return rows


# --------------------------------------------------------------------------------------- persistence (<= 2024 only)

def persistence(L: pd.DataFrame, F: dict, E: dict) -> pd.DataFrame:
    """Per per-match residual (and the serve-point rate as a skill reference): split-half (alternate eligible matches
    of a player-season, 10+ in each half) and season-to-season (20+ matches in both seasons) correlations, by tour.
    Rows: matches surely finished before 1 Jan 2025, tournament years 2010-2024."""
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    keep = (num(L, "lf") + 1 <= DISC_END_DAY) & (yr >= 2010) & (yr <= 2024)
    units = {k: E[k] for k in RES_NAMES}
    units["spw_rate (skill reference)"] = np.where(F["elig"], F["p_i"], np.nan)
    rows = []
    base = pd.DataFrame({"tour": F["tour"], "pid": L["player_id"].to_numpy(), "yr": yr, "k": num(L, "k")})
    for name, v in units.items():
        m = keep & np.isfinite(v)
        d = base[m].assign(v=v[m]).sort_values(["pid", "k"], kind="mergesort")
        d["half"] = d.groupby(["pid", "yr"]).cumcount() % 2
        g = d.groupby(["tour", "pid", "yr", "half"])["v"].agg(["mean", "size"]).unstack("half")
        g = g[(g[("size", 0)] >= 10) & (g[("size", 1)] >= 10)]
        s = d.groupby(["tour", "pid", "yr"])["v"].agg(["mean", "size"])
        s = s[s["size"] >= 20].reset_index()
        nxt = s.assign(yr=s["yr"] - 1).rename(columns={"mean": "mean_next", "size": "size_next"})
        ss = s.merge(nxt, on=["tour", "pid", "yr"], how="inner")
        for tour in ("atp", "wta"):
            gt = g.loc[tour] if tour in g.index.get_level_values(0) else None
            r_sh = float(np.corrcoef(gt[("mean", 0)], gt[("mean", 1)])[0, 1]) \
                if gt is not None and len(gt) > 20 else np.nan
            st = ss[ss["tour"] == tour]
            r_ss = float(np.corrcoef(st["mean"], st["mean_next"])[0, 1]) if len(st) > 20 else np.nan
            mt = m & (F["tour"] == tour)
            rows.append({"unit": name, "tour": tour, "split_half_r": r_sh,
                         "spearman_brown": 2 * r_sh / (1 + r_sh) if np.isfinite(r_sh) else np.nan,
                         "player_seasons": int(len(gt)) if gt is not None else 0,
                         "season_to_season_r": r_ss, "season_pairs": int(len(st)),
                         "per_match_mean": float(np.mean(v[mt])), "per_match_sd": float(np.std(v[mt]))})
    return pd.DataFrame(rows)


def residual_drift(L: pd.DataFrame, F: dict, E: dict) -> pd.DataFrame:
    """Per tournament year (2010-2024, matches surely finished before 2025) and tour: the mean per-match residual of
    the pieces that are not antisymmetric within a match (save, faced, hold, break, net)."""
    yr = pd.to_datetime(L["tournament_date"]).dt.year.to_numpy()
    keep = (num(L, "lf") + 1 <= DISC_END_DAY) & (yr >= 2010) & (yr <= 2024)
    rows = []
    for k in ("save", "faced", "hold", "break", "net"):
        v = E[k]
        d = pd.DataFrame({"tour": F["tour"], "yr": yr, "v": v})[keep & np.isfinite(v)]
        g = d.groupby(["tour", "yr"])["v"].agg(["mean", "size"]).reset_index()
        g["piece"] = k
        rows.append(g)
    return pd.concat(rows, ignore_index=True)


# ------------------------------------------------------------------------------------------------------------ main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-probe", action="store_true", help="skip the timing probes")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    log("long table")
    L = load_long()
    F = facts(L)
    P = iid_parts(F)
    log("calibration (2010-12)")
    cal = calibrate(L, F, P)
    (OUT / "calibration.json").write_text(json.dumps(cal, indent=1), encoding="utf-8")
    log("player statistics")
    V = player_stats(L, cal)
    Gp = elo_gap(L, cal)
    V = V.merge(Gp, on=["match_id", "player_id"], how="left", validate="one_to_one")
    stat_cols = [c for c in V.columns if c not in ("match_id", "player_id", "elogap")]
    probes = {"cuts": ["2016-06-01", "2019-03-01", "2022-09-01"], "seed": 20261013,
              "rule": "both counts must be 0 (screen.timing_probe)"}
    if not args.no_probe:
        log("timing probe: player statistics")
        probes["player_stats"] = {"value_cols": stat_cols,
                                  "result": H.timing_probe(lambda X: player_stats(X, cal), L, stat_cols)}
        log("timing probe: PS02 Elo gap")
        probes["elo_gap"] = {"value_cols": ["elogap"],
                             "result": H.timing_probe(lambda X: elo_gap(X, cal), L, ["elogap"])}
        bad = sum(v["future_rows_changed"] + v["own_rows_changed"] for p in ("player_stats", "elo_gap")
                  for v in probes[p]["result"].values())
        probes["all_zero"] = bool(bad == 0)
        log(f"probes: changed rows in total {bad}")
        (OUT / "probes.json").write_text(json.dumps(probes, indent=1), encoding="utf-8")
    stats = stat_list()

    log("values for every frame match (outcome-free)")
    fo = H.frame_outcome_free()
    vals, masks_all = values_for(V, fo, stats)
    vals.to_parquet(OUT / "values.parquet", index=False)

    log("screens, seasons <= 2024")
    frame = H.load_frame()
    fv, masks = values_for(V, frame, stats)
    long_parts, orth_coef, xs = [], {}, {}
    for s in stats:
        x = fv[s["name"]].to_numpy(float)
        xs[s["name"]] = x
        long_parts.append(H.screen(frame, x, s["name"]).assign(tier=s["tier"], registered_sign=s["sign"]))
        xo, coef = H.orthogonal_part(frame, x)
        orth_coef[s["name"]] = coef
        long_parts.append(H.screen(frame, xo, s["name"] + "__orth").assign(tier=s["tier"], registered_sign=s["sign"]))
    long = pd.concat(long_parts, ignore_index=True)
    long.to_csv(OUT / "long.csv", index=False)
    summ = H.summarize(long)
    meta = {s["name"]: s for s in stats}
    base = summ["name"].str.replace("__orth", "", regex=False)
    summ["tier"] = base.map(lambda n: meta[n]["tier"])
    summ["registered_sign"] = base.map(lambda n: meta[n]["sign"])
    summ["z_pool_oriented"] = np.where(summ["registered_sign"] == "-", -1, 1) * summ["z_pool"]
    present = {}
    for s in stats:
        for tour in H.TOURS:
            mt = np.ones(len(frame), bool) if tour == "both" else (frame["tour"] == tour).to_numpy()
            mt = mt & frame["season"].between(2013, 2024).to_numpy()        # pandas 3: to_numpy() can be read-only
            present[(s["name"], tour)] = float(masks[s["name"]][mt].mean())
    summ["informative_2013_24"] = [present[(b, t)] for b, t in zip(base, summ["tour"])]
    summ.to_csv(OUT / "summary.csv", index=False)
    (OUT / "orth_coef.json").write_text(json.dumps(orth_coef), encoding="utf-8")

    log("coverage (outcome-free; matches before 29 Jul 2026, debut seasons out)")
    keep = (~fo["debut_season"].astype(bool) & (fo["tournament_date"] < SEALED)).to_numpy()
    fk = fo[keep].reset_index(drop=True)
    cov = {"rule": "frame rows before 2026-07-29 (the sealed set is not counted), debut seasons out; as_built = the "
                   "value exists (0 when there is no history); informative = both players have the history the "
                   "statistic needs (memo, coverage)", "rows": {}}
    for tour in ("atp", "wta"):
        for lab, (a, b) in (("2013_24", (2013, 2024)), ("2025_26", (2025, 2026))):
            cov["rows"][f"{tour}_{lab}"] = int(((fk["tour"] == tour) & fk["season"].between(a, b)).sum())
    for s in stats:
        x = vals[s["name"]].to_numpy(float)[keep]
        xi = np.where(masks_all[s["name"]][keep], x, np.nan)
        cov[s["name"]] = {"as_built": H.coverage_2025_26(fk, x), "informative": H.coverage_2025_26(fk, xi)}
    nb = {}
    for tour in ("atp", "wta"):
        for lab, (a, b) in (("2013_24", (2013, 2024)), ("2025_26", (2025, 2026))):
            mt = (fk["tour"] == tour).to_numpy() & fk["season"].between(a, b).to_numpy()
            na = vals["lk_n_h91_a"].to_numpy(float)[keep][mt]
            nbb = vals["lk_n_h91_b"].to_numpy(float)[keep][mt]
            nb[f"{tour}_{lab}"] = {"mean_decayed_count_h91": float(np.nanmean(np.r_[na, nbb])),
                                   "share_both_count_h91_ge_1": float(np.mean((na >= 1) & (nbb >= 1)))}
    cov["decayed_counts"] = nb
    (OUT / "coverage.json").write_text(json.dumps(cov, indent=1), encoding="utf-8")

    log("the close's loading c (<= 2024)")
    lc = []
    for s in stats:
        lc += loading_c(frame, xs[s["name"]], s["name"], long)
    pd.DataFrame(lc).to_csv(OUT / "loading_c.csv", index=False)

    log("persistence and drift (<= 2024)")
    E = residuals(F, P, cal)
    persistence(L, F, E).to_csv(OUT / "persistence.csv", index=False)
    residual_drift(L, F, E).to_csv(OUT / "residual_drift.csv", index=False)

    log("correlations (<= 2024)")
    cnames = [s["name"] for s in stats if s["tier"] != "decay secondary"]
    C = pd.DataFrame({n: xs[n] for n in cnames})
    C["sets_14d"] = frame["in_sets_14d"].to_numpy(float)
    C["U138_on_n_store"] = fv["U138_on_n_store"].to_numpy(float)
    C["U307_on_log_store"] = fv["U307_on_log_store"].to_numpy(float)
    C["on_n_rebuilt"] = fv["lk_on_n_a"].to_numpy(float) - fv["lk_on_n_b"].to_numpy(float)
    C["d_count_h91"] = fv["lk_n_h91_a"].to_numpy(float) - fv["lk_n_h91_b"].to_numpy(float)
    for n in ("elo_overall", "points_52w", "iosO_hold", "form_bp_saved", "form_bp_faced_pg", "form_hold"):
        C[n] = frame[f"in_{n}"].to_numpy(float)
    C.corr(min_periods=1000).to_csv(OUT / "correlations.csv")
    info = {"seconds": round(time.time() - T0, 1), "long_table_rows": int(len(L)),
            "eligible_rows": int(F["elig"].sum()), "frame_rows_all": int(len(fo)),
            "frame_rows_le_2024": int(len(frame)), "statistics": stats, "skill_inputs_for_c": skill_inputs(),
            "points_only_inputs_for_c_pts": points_only_inputs(),
            "store_rows_matched_le_2024": int(np.isfinite(xs["I025_pool"]).sum())}
    (OUT / "build_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    log("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
