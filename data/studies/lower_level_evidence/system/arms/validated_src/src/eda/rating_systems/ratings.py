"""The rating systems of the study "rating systems against Elo" (src/eda/rating_systems/): Glicko-2, its fixed-volatility
special case (Glicko-1), and TrueSkill, each run in one chronological pass under the predictability diagnostic's time rule.

Glicko-2 (Glickman, "Example of the Glicko-2 system", glicko.net/glicko/glicko2.pdf; J. Applied Statistics 28, 2001)
    Each player has a rating mu, a rating deviation phi and a volatility sigma on the Glicko-2 scale (mu = (r - 1500) /
    173.7178, phi = RD / 173.7178). Results are processed in rating periods; here a period is a tournament date (the time
    rule's "week"). In a period a player's games, each scored against the opponent's rating at the start of the period,
    give
        g(phi) = 1 / sqrt(1 + 3 phi^2 / pi^2),     E = 1 / (1 + exp(-g(phi_j) (mu - mu_j))),
        v = 1 / sum g(phi_j)^2 E (1 - E),          Delta = v sum g(phi_j) (s - E),
    a new volatility sigma' from Glickman's Illinois iteration (tolerance 1e-6), phi* = sqrt(phi^2 + sigma'^2),
    phi' = 1 / sqrt(1 / phi*^2 + 1 / v), mu' = mu + phi'^2 sum g(phi_j) (s - E).
    A period in which a player does not play adds sigma^2 to phi^2 (Glickman's rule); the periods are ``period`` days
    long, so a gap of d days since the player's last period adds (d / period - 1) sigma^2 (fractional; capped so that
    phi never exceeds the newcomer's phi0, as Glicko-1 caps RD at 350). Newcomers start at mu 0 (1500), phi0 = RD0 /
    173.7178 and sigma0.
    Glicko-1 is the same with the volatility held at sigma0 (no iteration): sigma0 plays the part of Glicko-1's c.

Glicko-2 match by match (glicko_seq_pass; a variant for tennis, not Glickman's own)
    Glickman advises rating periods of 10-15 games per player; a tennis player plays one to five matches a week, and a
    week's games scored together against the player's start-of-week rating overshoot when the rating is uncertain (a
    newcomer winning four rounds). Here each round is its own rating period (as Elo and TrueSkill update) and the drift
    is by elapsed time: the first period of a week carries k sigma^2, k = days since the player's last period / 7, later
    rounds of the event none. Step 5 generalises directly: the drift term e^x of Glickman's f(x) becomes k e^x
    (volatility_k; k = 1 is his). Glicko-1 match by match holds the volatility.

TrueSkill (Herbrich, Minka and Graepel, NIPS 2006 / 2007), two players, no draws
    Each player has a skill mean mu and variance s2; performances are skill plus N(0, beta^2) noise and the higher
    performance wins. Before a match the variance grows by tau^2 (TrueSkill's per-game dynamics) and, once per period,
    by gamma^2 per year since the player's last period (a time dynamics, as in TrueSkill Through Time; capped at the
    newcomer's sigma0^2). The winner w and loser l are updated by
        c^2 = 2 beta^2 + s2_w + s2_l,   t = (mu_w - mu_l) / c,   v = pdf(t) / cdf(t),   w = v (v + t),
        mu_w += s2_w / c v,   mu_l -= s2_l / c v,   s2_w *= 1 - s2_w / c^2 w,   s2_l *= 1 - s2_l / c^2 w.
    The scale is fixed by beta = 1; newcomers start at mu 0 and variance sigma0^2.

The time rule (the Brief's; stage1_baselines.elo_pass implements it for Elo, and these passes keep its bookkeeping)
    A player's rating for a match is their rating at the start of its week (tournament date) plus what their earlier
    rounds of the same event added. A round's results are held back until the player's next round of that event (so a
    round robin's matches never see each other) and reach the player's other events only when the week is over (so two
    events of one week never see each other).
    * Glicko (weekly periods): the period is the week. Within an event, a player's provisional rating for round r is
      the period update computed from their earlier rounds' games only (each against the opponent's rating at the start
      of the period, as a Glicko period requires); at the week's end the period update over all their games of the week
      is committed.
    * Glicko match by match, and TrueSkill: updates run match by match. A round's updates are folded in at the player's next round of the event; a
      round robin's matches of one round, each computed from the same prior, are combined by multiplying their Gaussian
      messages (adding natural parameters). At the week's end each event's change is combined the same way.
    Walkovers and matches of status "other" never move ratings (``upd``); retirements do (the owner's rule for Elo).

The surface component. As Stage 1's surface Elo, each player also has one rating per surface (hard, clay, grass, carpet),
moved only by matches on it: the same pass is run with keys player x 4 + surface on the rows with a known surface. The
forecast blends the two on the rating scale (blend_glicko / blend_trueskill).

Each pass returns one row per match: A's and B's pre-match mean, uncertainty used for the forecast (phi or the variance
s2, including the period's drift), volatility (Glicko; TrueSkill gives NaN) and rated-match counts.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.special import expit, ndtr

SCALE = 173.7178                 # Glicko-2: mu = (r - 1500) / SCALE, phi = RD / SCALE
PI2 = math.pi ** 2
VOL_EPS = 1e-6                   # Glickman's convergence tolerance for the volatility iteration
SQRT2 = math.sqrt(2.0)
INV_SQRT_2PI = 1.0 / math.sqrt(2.0 * math.pi)
DAYS_PER_YEAR = 365.25
OUT_COLS = ["mu_a", "mu_b", "u_a", "u_b", "vol_a", "vol_b", "n_a", "n_b"]   # u: phi (Glicko) or s2 (TrueSkill)


# ------------------------------------------------------------------------------------------------
# Glicko-2: the formulas

def g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / PI2)


def logistic2(x: float) -> tuple[float, float]:
    """(1 / (1 + e^-x), 1 / (1 + e^x)) without overflow, each computed directly (no 1 - p cancellation)."""
    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z), z / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z), 1.0 / (1.0 + z)


def expected(mu: float, mu_j: float, phi_j: float) -> float:
    return logistic2(g(phi_j) * (mu - mu_j))[0]


def volatility(phi: float, sigma: float, delta: float, v: float, tau: float, eps: float = VOL_EPS) -> float:
    """Glickman's step 5: the new volatility, by the Illinois iteration on f(x), x = ln(sigma'^2)."""
    a = math.log(sigma * sigma)
    phi2, d2, tau2 = phi * phi, delta * delta, tau * tau
    exp = math.exp

    def f(x):
        ex = exp(x)
        den = phi2 + v + ex
        return ex * (d2 - phi2 - v - ex) / (2.0 * den * den) - (x - a) / tau2
    A = a
    if d2 > phi2 + v:
        B = math.log(d2 - phi2 - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau
    fA, fB = f(A), f(B)
    while abs(B - A) > eps:
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB <= 0:
            A, fA = B, fB
        else:
            fA /= 2.0
        B, fB = C, fC
    return exp(A / 2.0)


def volatility_k(phi: float, sigma: float, delta: float, v: float, tau: float, k: float, eps: float = VOL_EPS) -> float:
    """Step 5 for a period whose drift is k sigma^2 (k rating periods elapsed, fractional): the root of
        f(x) = k e^x (Delta^2 - phi^2 - v - k e^x) / (2 (phi^2 + v + k e^x)^2) - (x - a) / tau^2,
    the derivative of the same approximate log posterior of x = ln sigma^2 with Delta ~ N(0, phi^2 + k sigma^2 + v).
    k = 1 is Glickman's step 5 (volatility()); k = 0 leaves sigma (no drift, nothing to learn about it)."""
    if k <= 0.0:
        return sigma
    a = math.log(sigma * sigma)
    phi2, d2, tau2 = phi * phi, delta * delta, tau * tau
    exp = math.exp

    def f(x):
        ex = k * exp(x)
        den = phi2 + v + ex
        return ex * (d2 - phi2 - v - ex) / (2.0 * den * den) - (x - a) / tau2
    A = a
    if d2 > phi2 + v:
        B = math.log((d2 - phi2 - v) / k)
    else:
        j = 1
        while f(a - j * tau) < 0:
            j += 1
        B = a - j * tau
    fA, fB = f(A), f(B)
    while abs(B - A) > eps:
        C = A + (A - B) * fA / (fB - fA)
        fC = f(C)
        if fC * fB <= 0:
            A, fA = B, fB
        else:
            fA /= 2.0
        B, fB = C, fC
    return exp(A / 2.0)


def glicko2_update_k(mu: float, phi: float, sigma: float, sv: float, sd: float, tau: float, vol: bool, k: float,
                     phi_cap: float):
    """A period of the match-by-match Glicko-2: steps 3-7 with the drift k sigma'^2 (k periods of time elapsed since the
    player's last period; 0 between rounds of one event), phi* capped at the newcomer's phi0."""
    if sv < 1e-300:
        return mu, min(math.sqrt(phi * phi + k * sigma * sigma), phi_cap), sigma
    v = 1.0 / sv
    s_new = volatility_k(phi, sigma, v * sd, v, tau, k) if vol else sigma
    ps2 = min(phi * phi + k * s_new * s_new, phi_cap * phi_cap)
    phi_new = 1.0 / math.sqrt(1.0 / ps2 + sv)
    return mu + phi_new * phi_new * sd, phi_new, s_new


def glicko2_update(mu: float, phi: float, sigma: float, sv: float, sd: float, tau: float, vol: bool = True):
    """One rating period from the sums sv = sum g(phi_j)^2 E (1 - E) (= 1 / v) and sd = sum g(phi_j) (s - E):
    Glickman's steps 3-7. With vol False the volatility is kept (Glicko-1). Returns (mu', phi', sigma'). A period whose
    information underflows (every game a certainty, only at absurd constants) moves nothing but the drift."""
    if sv < 1e-300:
        return mu, min(math.sqrt(phi * phi + sigma * sigma), 1e6), sigma
    v = 1.0 / sv
    s_new = volatility(phi, sigma, v * sd, v, tau) if vol else sigma
    phi_new = 1.0 / math.sqrt(1.0 / (phi * phi + s_new * s_new) + sv)
    return mu + phi_new * phi_new * sd, phi_new, s_new


def glicko2_rate(mu: float, phi: float, sigma: float, games, tau: float, vol: bool = True):
    """A rating period from a list of games (mu_j, phi_j, s) in the Glicko-2 scale: the reference form of the update
    (Glickman's worked example is a test)."""
    sv = sd = 0.0
    for mu_j, phi_j, s in games:
        gj = g(phi_j)
        e, q = logistic2(gj * (mu - mu_j))
        sv += gj * gj * e * q
        sd += gj * (s - e)
    return glicko2_update(mu, phi, sigma, sv, sd, tau, vol)


def p_glicko(mu_a, mu_b, phi_a, phi_b):
    """P(A beats B) with both players' uncertainty (Glickman's expected outcome: g of the combined deviation)."""
    mu_a, mu_b, phi_a, phi_b = (np.asarray(x, dtype="float64") for x in (mu_a, mu_b, phi_a, phi_b))
    gg = 1.0 / np.sqrt(1.0 + 3.0 * (phi_a ** 2 + phi_b ** 2) / PI2)
    return expit(gg * (mu_a - mu_b))


# ------------------------------------------------------------------------------------------------
# Glicko: the pass under the time rule

def glicko_pass(week, event, rnd, ka, kb, a_won, act, upd, n_keys: int, rd0: float = 350.0, sigma0: float = 0.06,
                tau: float = 0.5, period: float = 7.0, vol: bool = True) -> np.ndarray:
    """One chronological Glicko-2 (vol True) or Glicko-1 (vol False) pass. Inputs are sequences in the table's order:
    week (the tournament date in days), event (a code unique within its week), rnd (round order), ka and kb (the sides'
    keys 0..n_keys-1: players, or player x surface), a_won, act (the rows this component rates; others get NaN) and
    upd (whether the result moves ratings). Returns OUT_COLS per row: mu, the phi used for the forecast, sigma, counts."""
    phi0 = rd0 / SCALE
    n = len(week)
    MU, PHI, SIG, TL, NN = [0.0] * n_keys, [phi0] * n_keys, [sigma0] * n_keys, [None] * n_keys, [0] * n_keys
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_pa, o_pb, o_sa, o_sb, o_na, o_nb = cols
    # per (key, event) of the current week: [round, earlier rounds' sv, sd, count, pending sv, sd, count,
    #                                       provisional mu (None: stale), phi, sigma]
    ent: dict = {}
    pre: dict = {}            # key -> (mu, phi with the empty periods' drift, sigma) at the start of the week
    cur = None
    sqrt, exp = math.sqrt, math.exp
    for i in range(n):
        D = week[i]
        if D != cur:
            if ent:
                _glicko_commit(ent, pre, MU, PHI, SIG, TL, NN, cur, tau, vol)
            cur = D
        if not act[i]:
            continue
        e, r = event[i], rnd[i]
        side = []
        for k in (ka[i], kb[i]):
            st = pre.get(k)
            if st is None:
                tl, ph = TL[k], PHI[k]
                if tl is not None:
                    gap = (D - tl) / period - 1.0
                    if gap > 0.0:
                        ph = sqrt(ph * ph + gap * SIG[k] * SIG[k])
                        if ph > phi0:
                            ph = phi0
                st = pre[k] = (MU[k], ph, SIG[k])
            x = ent.get((k, e))
            if x is None:
                x = ent[(k, e)] = [r, 0.0, 0.0, 0, 0.0, 0.0, 0, None, 0.0, 0.0]
            elif x[0] < r:
                if x[6]:
                    x[1] += x[4]
                    x[2] += x[5]
                    x[3] += x[6]
                    x[4] = x[5] = 0.0
                    x[6] = 0
                    x[7] = None
                x[0] = r
            if x[3] == 0:
                mu_p, phi_p, sig_p = st[0], sqrt(st[1] * st[1] + st[2] * st[2]), st[2]
            else:
                if x[7] is None:
                    x[7], x[8], x[9] = glicko2_update(st[0], st[1], st[2], x[1], x[2], tau, vol)
                mu_p, phi_p, sig_p = x[7], x[8], x[9]
            side.append((st, x, mu_p, phi_p, sig_p, NN[k] + x[3]))
        (sta, xa, o_mua[i], o_pa[i], o_sa[i], o_na[i]), (stb, xb, o_mub[i], o_pb[i], o_sb[i], o_nb[i]) = side
        if upd[i]:
            won = a_won[i]
            gb = 1.0 / sqrt(1.0 + 3.0 * stb[1] * stb[1] / PI2)
            ea, qa = logistic2(gb * (sta[0] - stb[0]))          # A's expected score against B, and 1 minus it
            xa[4] += gb * gb * ea * qa
            xa[5] += gb * (qa if won else -ea)
            xa[6] += 1
            ga = 1.0 / sqrt(1.0 + 3.0 * sta[1] * sta[1] / PI2)
            eb, qb = logistic2(ga * (stb[0] - sta[0]))
            xb[4] += ga * ga * eb * qb
            xb[5] += ga * (-eb if won else qb)
            xb[6] += 1
    return np.array(cols, dtype="float64").T


def _glicko_commit(ent, pre, MU, PHI, SIG, TL, NN, D, tau, vol) -> None:
    """The week's end: each key that played a rating-moving match this week gets the period update over all its games
    of the week (every event, every round), from its rating at the start of the week."""
    tot: dict = {}
    for (k, _), x in ent.items():
        c = x[3] + x[6]
        if c:
            t = tot.get(k)
            if t is None:
                tot[k] = [x[1] + x[4], x[2] + x[5], c]
            else:
                t[0] += x[1] + x[4]
                t[1] += x[2] + x[5]
                t[2] += c
    for k, (sv, sd, c) in tot.items():
        mu, ph, sg = pre[k]
        MU[k], PHI[k], SIG[k] = glicko2_update(mu, ph, sg, sv, sd, tau, vol)
        TL[k] = D
        NN[k] += c
    ent.clear()
    pre.clear()


def glicko_seq_pass(week, event, rnd, ka, kb, a_won, act, upd, n_keys: int, rd0: float = 350.0, sigma0: float = 0.06,
                    tau: float = 0.5, period: float = 7.0, vol: bool = True) -> np.ndarray:
    """Glicko-2 match by match, with drift by elapsed time (inputs and output as glicko_pass).

    Each round a player plays is a rating period of its games (one, or a round robin's several), scored against the
    opponents' ratings at the start of the round, as TrueSkill and Elo update. The drift is time's alone: a player's
    first period of a week carries k sigma^2 with k = days since their last period / ``period``; later rounds of the
    event carry none (glicko2_update_k; the volatility is then left as it is). The opponent's g uses their current
    deviation including their pending drift. Round robins, and several events of one week, are combined as in
    trueskill_pass (natural parameters of the Gaussian rating, 1 / phi^2 and mu / phi^2; the volatility averaged)."""
    phi0 = rd0 / SCALE
    p0sq = phi0 * phi0
    n = len(week)
    MU, PHI, SIG, TL, NN = [0.0] * n_keys, [phi0] * n_keys, [sigma0] * n_keys, [None] * n_keys, [0] * n_keys
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_pa, o_pb, o_sa, o_sb, o_na, o_nb = cols
    # per (key, event) of the current week: [round, mu, phi, sigma (after the folded rounds), drift k still to apply,
    #                                       pending sv, pending sd, pending count, folded count]
    ent: dict = {}
    pre: dict = {}            # key -> (mu, phi, sigma, k) at the start of the week
    cur = None
    sqrt = math.sqrt
    for i in range(n):
        D = week[i]
        if D != cur:
            if ent:
                _glicko_seq_commit(ent, pre, MU, PHI, SIG, TL, NN, cur, tau, vol, phi0)
            cur = D
        if not act[i]:
            continue
        e, r = event[i], rnd[i]
        side = []
        for k in (ka[i], kb[i]):
            st = pre.get(k)
            if st is None:
                tl = TL[k]
                st = pre[k] = (MU[k], PHI[k], SIG[k], 0.0 if tl is None else (D - tl) / period)
            x = ent.get((k, e))
            if x is None:
                x = ent[(k, e)] = [r, st[0], st[1], st[2], st[3], 0.0, 0.0, 0, 0]
            elif x[0] < r:
                if x[7]:
                    _seq_fold(x, tau, vol, phi0)
                x[0] = r
            ps2 = x[2] * x[2] + x[4] * x[3] * x[3]
            side.append((x, sqrt(ps2 if ps2 < p0sq else p0sq), NN[k] + x[8]))
        (xa, pa, na), (xb, pb, nb) = side
        o_mua[i], o_mub[i], o_pa[i], o_pb[i], o_sa[i], o_sb[i], o_na[i], o_nb[i] = xa[1], xb[1], pa, pb, xa[3], xb[3], na, nb
        if upd[i]:
            won = a_won[i]
            gb = 1.0 / sqrt(1.0 + 3.0 * pb * pb / PI2)
            ea, qa = logistic2(gb * (xa[1] - xb[1]))
            xa[5] += gb * gb * ea * qa
            xa[6] += gb * (qa if won else -ea)
            xa[7] += 1
            ga = 1.0 / sqrt(1.0 + 3.0 * pa * pa / PI2)
            eb, qb = logistic2(ga * (xb[1] - xa[1]))
            xb[5] += ga * ga * eb * qb
            xb[6] += ga * (-eb if won else qb)
            xb[7] += 1
    return np.array(cols, dtype="float64").T


def _seq_fold(x: list, tau: float, vol: bool, phi0: float) -> None:
    x[1], x[2], x[3] = glicko2_update_k(x[1], x[2], x[3], x[5], x[6], tau, vol, x[4], phi0)
    x[4] = 0.0
    x[8] += x[7]
    x[5] = x[6] = 0.0
    x[7] = 0


def _glicko_seq_commit(ent, pre, MU, PHI, SIG, TL, NN, D, tau, vol, phi0) -> None:
    tot: dict = {}
    for (k, _), x in ent.items():
        if x[7]:
            _seq_fold(x, tau, vol, phi0)
        if x[8]:
            tot.setdefault(k, []).append(x)
    for k, xs in tot.items():
        if len(xs) == 1:
            MU[k], PHI[k], SIG[k] = xs[0][1], xs[0][2], xs[0][3]
            NN[k] += xs[0][8]
        else:
            mu0, phi_, sig0, kd = pre[k]
            s20 = min(phi_ * phi_ + kd * sig0 * sig0, phi0 * phi0)
            prec, pm = 1.0 / s20, mu0 / s20
            for x in xs:
                prec += 1.0 / (x[2] * x[2]) - 1.0 / s20
                pm += x[1] / (x[2] * x[2]) - mu0 / s20
                NN[k] += x[8]
            prec = max(prec, 1e-12)
            MU[k], PHI[k], SIG[k] = pm / prec, math.sqrt(1.0 / prec), sum(x[3] for x in xs) / len(xs)
        TL[k] = D
    ent.clear()
    pre.clear()


# ------------------------------------------------------------------------------------------------
# TrueSkill: the formulas

def vw(t: float) -> tuple[float, float]:
    """TrueSkill's v(t) = pdf(t) / cdf(t) and w(t) = v (v + t) for a win with no draw margin (asymptotic form far in
    the lower tail, where the cdf underflows)."""
    if t > -20.0:
        v = INV_SQRT_2PI * math.exp(-0.5 * t * t) / (0.5 * math.erfc(-t / SQRT2))
    else:
        v = -t - 1.0 / t + 2.0 / t ** 3
    return v, v * (v + t)


def trueskill_rate_1v1(mu_w: float, s2_w: float, mu_l: float, s2_l: float, beta: float = 1.0):
    """The winner's and loser's posterior (mu, s2) from their priors (dynamics already added)."""
    c2 = 2.0 * beta * beta + s2_w + s2_l
    c = math.sqrt(c2)
    v, w = vw((mu_w - mu_l) / c)
    return ((mu_w + s2_w / c * v, s2_w * (1.0 - s2_w / c2 * w)),
            (mu_l - s2_l / c * v, s2_l * (1.0 - s2_l / c2 * w)))


def p_trueskill(mu_a, mu_b, s2_a, s2_b, beta: float = 1.0):
    """P(A beats B): P(perf_A > perf_B) = cdf((mu_A - mu_B) / sqrt(2 beta^2 + s2_A + s2_B))."""
    mu_a, mu_b, s2_a, s2_b = (np.asarray(x, dtype="float64") for x in (mu_a, mu_b, s2_a, s2_b))
    return ndtr((mu_a - mu_b) / np.sqrt(2.0 * beta * beta + s2_a + s2_b))


# ------------------------------------------------------------------------------------------------
# TrueSkill: the pass under the time rule

def trueskill_pass(week, event, rnd, ka, kb, a_won, act, upd, n_keys: int, sigma0: float = 2.0, tau: float = 0.02,
                   gamma: float = 0.0, beta: float = 1.0) -> np.ndarray:
    """One chronological TrueSkill pass (inputs as glicko_pass). sigma0: a newcomer's skill standard deviation; tau: the
    per-match dynamics; gamma: the dynamics per square-root year since the player's last period; beta: the performance
    noise (1 fixes the scale). Returns OUT_COLS per row: mu, the variance used for the forecast (including tau^2), NaN
    for the volatility, counts."""
    n = len(week)
    s0sq, tau2, gam2, beta2 = sigma0 * sigma0, tau * tau, gamma * gamma, beta * beta
    MU, S2, TL, NN = [0.0] * n_keys, [s0sq] * n_keys, [None] * n_keys, [0] * n_keys
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_sa, o_sb, _, _, o_na, o_nb = cols
    # per (key, event) of the current week: [round, mu, s2 (after the folded rounds), pending d_precision,
    #                                       pending d_precision-mean, pending count, folded count]
    ent: dict = {}
    pre: dict = {}            # key -> (mu, s2 with the time dynamics) at the start of the week
    cur = None
    sqrt, exp, erfc = math.sqrt, math.exp, math.erfc
    for i in range(n):
        D = week[i]
        if D != cur:
            if ent:
                _trueskill_commit(ent, pre, MU, S2, TL, NN, cur, tau2)
            cur = D
        if not act[i]:
            continue
        e, r = event[i], rnd[i]
        side = []
        for k in (ka[i], kb[i]):
            st = pre.get(k)
            if st is None:
                s2, tl = S2[k], TL[k]
                if tl is not None and gam2 > 0.0:
                    s2 += gam2 * (D - tl) / DAYS_PER_YEAR
                    if s2 > s0sq:
                        s2 = s0sq
                st = pre[k] = (MU[k], s2)
            x = ent.get((k, e))
            if x is None:
                x = ent[(k, e)] = [r, st[0], st[1], 0.0, 0.0, 0, 0]
            elif x[0] < r:
                if x[5]:
                    _fold(x, tau2)
                x[0] = r
            side.append((x, NN[k] + x[6]))
        (xa, na), (xb, nb) = side
        mua, s2a, mub, s2b = xa[1], xa[2] + tau2, xb[1], xb[2] + tau2
        o_mua[i], o_mub[i], o_sa[i], o_sb[i], o_na[i], o_nb[i] = mua, mub, s2a, s2b, na, nb
        if upd[i]:
            if a_won[i]:
                mw, sw, ml, sl, xw, xl = mua, s2a, mub, s2b, xa, xb
            else:
                mw, sw, ml, sl, xw, xl = mub, s2b, mua, s2a, xb, xa
            c2 = 2.0 * beta2 + sw + sl
            c = sqrt(c2)
            t = (mw - ml) / c
            if t > -20.0:
                v = INV_SQRT_2PI * exp(-0.5 * t * t) / (0.5 * erfc(-t / SQRT2))
            else:
                v = -t - 1.0 / t + 2.0 / t ** 3
            w = v * (v + t)
            mw2, sw2 = mw + sw / c * v, sw * (1.0 - sw / c2 * w)
            ml2, sl2 = ml - sl / c * v, sl * (1.0 - sl / c2 * w)
            xw[3] += 1.0 / sw2 - 1.0 / sw
            xw[4] += mw2 / sw2 - mw / sw
            xw[5] += 1
            xl[3] += 1.0 / sl2 - 1.0 / sl
            xl[4] += ml2 / sl2 - ml / sl
            xl[5] += 1
    return np.array(cols, dtype="float64").T


def _fold(x: list, tau2: float) -> None:
    """Fold a round's pending messages into the in-event state: the round's prior (the state plus tau^2) times the
    messages of the round's matches (natural parameters added)."""
    s2p = x[2] + tau2
    prec = 1.0 / s2p + x[3]
    x[1] = (x[1] / s2p + x[4]) / prec
    x[2] = 1.0 / prec
    x[6] += x[5]
    x[3] = x[4] = 0.0
    x[5] = 0


def _trueskill_commit(ent, pre, MU, S2, TL, NN, D, tau2) -> None:
    """The week's end: each key that played a rating-moving match this week takes its events' final states; several
    events of one week (each run from the same start) are combined by adding their changes in natural parameters."""
    tot: dict = {}
    for (k, _), x in ent.items():
        if x[5]:
            _fold(x, tau2)
        if x[6]:
            tot.setdefault(k, []).append(x)
    for k, xs in tot.items():
        if len(xs) == 1:
            MU[k], S2[k] = xs[0][1], xs[0][2]
            NN[k] += xs[0][6]
        else:
            mu0, s20 = pre[k]
            prec, pm = 1.0 / s20, mu0 / s20
            for x in xs:
                prec += 1.0 / x[2] - 1.0 / s20
                pm += x[1] / x[2] - mu0 / s20
                NN[k] += x[6]
            prec = max(prec, 1e-12)
            MU[k], S2[k] = pm / prec, 1.0 / prec
        TL[k] = D
    ent.clear()
    pre.clear()


# ------------------------------------------------------------------------------------------------
# TrueSkill Through Time, run causally with a trailing smoothing window

class TTT:
    """TrueSkill Through Time (Dangauthier, Herbrich, Minka and Graepel, NIPS 2007; Landfried and Mocskos, J. Stat.
    Software 112(6), 2025): one skill node per player and batch (here a week), linked along each player's history by a
    Gaussian drift of gamma^2 per year, games as TrueSkill factors, solved by expectation propagation (EP) with forward
    and backward messages along every player's chain. Messages are kept in natural parameters (precision, precision x
    mean); a uniform message is (0, 0).

    add_batch(t, games) adds a finished week: a node per player with a rating-moving match (its forward message from
    the player's previous node, drifted, or the prior N(0, sigma0^2)), the week's games (winner key, loser key), then
    ``batch_iters`` EP passes over them. smooth(window, sweeps) runs ``sweeps`` backward-then-forward passes over the last
    ``window`` batches, re-scoring each game against the current estimate of both players (so an old win is credited at
    what the opponent later proved to be worth); nodes older than the window keep their messages. latest(k, t) is the
    player's current estimate drifted to time t (their last node has no backward message)."""

    def __init__(self, n_keys: int, sigma0: float, gamma: float, beta: float = 1.0):
        self.s0sq, self.gam2, self.beta2 = sigma0 * sigma0, gamma * gamma, beta * beta
        self.key, self.time, self.prev, self.next, self.games = [], [], [], [], []
        self.fpi, self.fnu, self.bpi, self.bnu, self.lpi, self.lnu = [], [], [], [], [], []
        self.gw, self.gl, self.mwpi, self.mwnu, self.mlpi, self.mlnu = [], [], [], [], [], []
        self.batches = []                          # (time, nodes, games), in time order
        self.last = [-1] * n_keys

    def _drift(self, pi: float, nu: float, days: float) -> tuple[float, float]:
        if pi <= 0.0:
            return 0.0, 0.0
        v = 1.0 / pi + self.gam2 * days / DAYS_PER_YEAR
        return 1.0 / v, nu / pi / v

    def _fwd(self, nd: int) -> None:
        p = self.prev[nd]
        if p < 0:
            self.fpi[nd], self.fnu[nd] = 1.0 / self.s0sq, 0.0
        else:
            self.fpi[nd], self.fnu[nd] = self._drift(self.fpi[p] + self.lpi[p], self.fnu[p] + self.lnu[p],
                                                     self.time[nd] - self.time[p])

    def _bwd(self, nd: int) -> None:
        q = self.next[nd]
        if q < 0:
            self.bpi[nd] = self.bnu[nd] = 0.0
        else:
            self.bpi[nd], self.bnu[nd] = self._drift(self.bpi[q] + self.lpi[q], self.bnu[q] + self.lnu[q],
                                                     self.time[q] - self.time[nd])

    def _game(self, g: int) -> None:
        """One EP update of game g: each player's cavity (posterior without this game's message), TrueSkill's moment
        matching from the two cavities, the new messages (posterior over cavity)."""
        w, l = self.gw[g], self.gl[g]
        cpw = self.fpi[w] + self.bpi[w] + self.lpi[w] - self.mwpi[g]
        cnw = self.fnu[w] + self.bnu[w] + self.lnu[w] - self.mwnu[g]
        cpl = self.fpi[l] + self.bpi[l] + self.lpi[l] - self.mlpi[g]
        cnl = self.fnu[l] + self.bnu[l] + self.lnu[l] - self.mlnu[g]
        if cpw <= 1e-12 or cpl <= 1e-12:
            return
        mw, sw, ml, sl = cnw / cpw, 1.0 / cpw, cnl / cpl, 1.0 / cpl
        c2 = 2.0 * self.beta2 + sw + sl
        c = math.sqrt(c2)
        t = (mw - ml) / c
        if t > -20.0:
            v = INV_SQRT_2PI * math.exp(-0.5 * t * t) / (0.5 * math.erfc(-t / SQRT2))
        else:
            v = -t - 1.0 / t + 2.0 / t ** 3
        ww = v * (v + t)
        sw2, sl2 = sw * (1.0 - sw / c2 * ww), sl * (1.0 - sl / c2 * ww)
        npw, nnw = 1.0 / sw2 - cpw, (mw + sw / c * v) / sw2 - cnw
        npl, nnl = 1.0 / sl2 - cpl, (ml - sl / c * v) / sl2 - cnl
        self.lpi[w] += npw - self.mwpi[g]
        self.lnu[w] += nnw - self.mwnu[g]
        self.lpi[l] += npl - self.mlpi[g]
        self.lnu[l] += nnl - self.mlnu[g]
        self.mwpi[g], self.mwnu[g], self.mlpi[g], self.mlnu[g] = npw, nnw, npl, nnl

    def add_batch(self, t: float, games: list, batch_iters: int = 2) -> None:
        node_of: dict = {}
        for kw, kl in games:
            for k in (kw, kl):
                if k in node_of:
                    continue
                nd = len(self.key)
                p = self.last[k]
                self.key.append(k)
                self.time.append(t)
                self.prev.append(p)
                self.next.append(-1)
                self.games.append([])
                for arr in (self.fpi, self.fnu, self.bpi, self.bnu, self.lpi, self.lnu):
                    arr.append(0.0)
                if p >= 0:
                    self.next[p] = nd
                self.last[k] = nd
                node_of[k] = nd
                self._fwd(nd)
        gids = []
        for kw, kl in games:
            g = len(self.gw)
            self.gw.append(node_of[kw])
            self.gl.append(node_of[kl])
            for arr in (self.mwpi, self.mwnu, self.mlpi, self.mlnu):
                arr.append(0.0)
            self.games[node_of[kw]].append(g)
            self.games[node_of[kl]].append(g)
            gids.append(g)
        self.batches.append((t, list(node_of.values()), gids))
        for _ in range(batch_iters):
            for g in gids:
                self._game(g)

    def smooth(self, window: int, sweeps: int = 1) -> None:
        lo = max(0, len(self.batches) - window)
        for _ in range(sweeps):
            for bi in range(len(self.batches) - 1, lo - 1, -1):
                _, nodes, games = self.batches[bi]
                for nd in nodes:
                    self._bwd(nd)
                for g in games:
                    self._game(g)
            for bi in range(lo, len(self.batches)):
                _, nodes, games = self.batches[bi]
                for nd in nodes:
                    self._fwd(nd)
                for g in games:
                    self._game(g)

    def posterior(self, nd: int) -> tuple[float, float]:
        pi = self.fpi[nd] + self.bpi[nd] + self.lpi[nd]
        return (self.fnu[nd] + self.bnu[nd] + self.lnu[nd]) / pi, 1.0 / pi

    def latest(self, k: int, t: float) -> tuple[float, float]:
        nd = self.last[k]
        if nd < 0:
            return 0.0, self.s0sq
        mu, s2 = self.posterior(nd)
        return mu, min(s2 + self.gam2 * (t - self.time[nd]) / DAYS_PER_YEAR, self.s0sq)


def ttt_pass(week, event, rnd, ka, kb, a_won, act, upd, n_keys: int, sigma0: float = 2.0, gamma: float = 0.4,
             beta: float = 1.0, window: int = 26, sweeps: int = 1, batch_iters: int = 2, hold=None,
             hold_days: float = 14.0) -> np.ndarray:
    """TrueSkill Through Time under the time rule (inputs and output as trueskill_pass). LEAKS across overlapping
    events (the match-timing audit, 5 Oct 2026): its smoothing passes a batch's results to every player, and a batch
    holds every match of a start date, events still running included. For new work use ttt_pass_timed (the leak-proof
    timeline; docs/decisions/2026-10-05-match-timing.md). A player's rating at the start
    of a week is their TTT estimate from every earlier week (smoothed over the trailing ``window`` weeks), drifted to the
    week's date; within the week their earlier rounds of the same event are added by TrueSkill's update, round by round,
    as in trueskill_pass (tau 0). When the week is over its rating-moving matches join the TTT model as one batch,
    which is then smoothed.

    ``hold`` (a flag per row, optional) marks events that run for about two weeks under one start date (a Grand Slam).
    The week's rule treats every round as known once the start date's week is over, but the second week's rounds are
    played during the next week's events; a filtering rating cannot pass them to another player, smoothing can. With
    ``hold`` such an event's matches join the model only at the first date at least ``hold_days`` after its start
    date (and at that date in time), a conservative variant that also withholds its first week."""
    n = len(week)
    model = TTT(n_keys, sigma0, gamma, beta)
    beta2 = beta * beta
    NN = [0] * n_keys
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_sa, o_sb, _, _, o_na, o_nb = cols
    ent: dict = {}
    pre: dict = {}
    done: list = []           # the week's rating-moving matches as (winner key, loser key)
    held: list = []           # held batches: [release date, games]
    hd: dict = {}             # this week's held matches, by event
    cur = None
    sqrt, exp, erfc = math.sqrt, math.exp, math.erfc
    for i in range(n):
        D = week[i]
        if D != cur:
            batches = [(float(cur), done)] if done else []
            if hd:
                held.extend([float(cur) + hold_days, g] for g in hd.values())
            due = sorted((r, g) for r, g in held if r <= D)
            held[:] = [x for x in held if x[0] > D]
            batches += [(r, g) for r, g in due]
            for t_b, games in batches:
                model.add_batch(t_b, games, batch_iters)
                model.smooth(window, sweeps)
                for kw, kl in games:
                    NN[kw] += 1
                    NN[kl] += 1
            done = []
            hd = {}
            ent.clear()
            pre.clear()
            cur = D
        if not act[i]:
            continue
        e, r = event[i], rnd[i]
        side = []
        for k in (ka[i], kb[i]):
            st = pre.get(k)
            if st is None:
                st = pre[k] = model.latest(k, float(D))
            x = ent.get((k, e))
            if x is None:
                x = ent[(k, e)] = [r, st[0], st[1], 0.0, 0.0, 0, 0]
            elif x[0] < r:
                if x[5]:
                    _fold(x, 0.0)
                x[0] = r
            side.append((x, NN[k] + x[6]))
        (xa, na), (xb, nb) = side
        mua, s2a, mub, s2b = xa[1], xa[2], xb[1], xb[2]
        o_mua[i], o_mub[i], o_sa[i], o_sb[i], o_na[i], o_nb[i] = mua, mub, s2a, s2b, na, nb
        if upd[i]:
            won = a_won[i]
            pair = (ka[i], kb[i]) if won else (kb[i], ka[i])
            if hold is not None and hold[i]:
                hd.setdefault(e, []).append(pair)
            else:
                done.append(pair)
            if won:
                mw, sw, ml, sl, xw, xl = mua, s2a, mub, s2b, xa, xb
            else:
                mw, sw, ml, sl, xw, xl = mub, s2b, mua, s2a, xb, xa
            c2 = 2.0 * beta2 + sw + sl
            c = sqrt(c2)
            t = (mw - ml) / c
            if t > -20.0:
                v = INV_SQRT_2PI * exp(-0.5 * t * t) / (0.5 * erfc(-t / SQRT2))
            else:
                v = -t - 1.0 / t + 2.0 / t ** 3
            w = v * (v + t)
            mw2, sw2 = mw + sw / c * v, sw * (1.0 - sw / c2 * w)
            ml2, sl2 = ml - sl / c * v, sl * (1.0 - sl / c2 * w)
            xw[3] += 1.0 / sw2 - 1.0 / sw
            xw[4] += mw2 / sw2 - mw / sw
            xw[5] += 1
            xl[3] += 1.0 / sl2 - 1.0 / sl
            xl[4] += ml2 / sl2 - ml / sl
            xl[5] += 1
    return np.array(cols, dtype="float64").T


def ttt_pass_timed(es, lf, event, rnd, ka, kb, a_won, act, upd, n_keys: int, sigma0: float = 2.0, gamma: float = 0.4,
                   beta: float = 1.0, window_days: float = 182.0, sweeps: int = 1, batch_iters: int = 2,
                   smooth_every: str = "week") -> np.ndarray:
    """TrueSkill Through Time on the leak-proof timeline (src/eda/match_timing/; docs/decisions/2026-10-05-match-
    timing.md): ttt_pass's model and outputs with the two-time rule in place of the tournament week, because ttt_pass's
    smoothing passes a result to every player, so a week's batch let the second week of a Grand Slam (or any event still
    running under an earlier start date) reach matches played before it.

    es, lf: per row, the match's earliest possible start and latest possible finish day. A rating-moving match joins
    the model in the batch of its release day lf + 1, at time lf. A row's forecast reads the model as of its es (drifted
    to that day) plus the TrueSkill updates of each player's own earlier matches that are not released yet, folded as
    ttt_pass folds a week's earlier rounds (rows are in the table's order, which is each player's own order; matches of
    the same event and round, round robins, do not fold into each other). Smoothing covers the batches of the trailing
    ``window_days``, after each batch (smooth_every "batch") or once per calendar week of the query days ("week", the
    default, as often as ttt_pass's weekly batches). With es = lf = the tournament week, "batch" smoothing and
    window_days spanning ttt_pass's ``window`` batches, it is ttt_pass."""
    from bisect import bisect_right
    n = len(es)
    model = TTT(n_keys, sigma0, gamma, beta)
    beta2 = beta * beta
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_sa, o_sb, _, _, o_na, o_nb = cols
    NN = [0] * n_keys
    pending = [dict() for _ in range(n_keys)]   # per key: row -> (event, round, d_pi, d_nu); played, not yet released
    by_release: dict = {}                        # release day -> [(row, winner key, loser key)]
    times: list = []                             # each added batch's time, in order
    last_week = last_day = None
    pre: dict = {}                               # this query day's states (the model drifted to the day)
    sqrt, exp, erfc = math.sqrt, math.exp, math.erfc
    for i in sorted(range(n), key=lambda r: (es[r], r)):
        S = es[i]
        due = sorted(r for r in by_release if r <= S)
        for r in due:
            games = by_release.pop(r)
            model.add_batch(float(r - 1), [(w, l) for _, w, l in games], batch_iters)
            times.append(float(r - 1))
            for j, w, l in games:
                pending[w].pop(j, None)
                pending[l].pop(j, None)
                NN[w] += 1
                NN[l] += 1
            if smooth_every == "batch":
                model.smooth(len(times) - bisect_right(times, r - 1 - window_days), sweeps)
        if due and smooth_every == "week" and S // 7 != last_week:
            model.smooth(len(times) - bisect_right(times, S - 1 - window_days), sweeps)
            last_week = S // 7
        if due or S != last_day:
            pre.clear()
            last_day = S
        if not act[i]:
            continue
        side = []
        for k in (ka[i], kb[i]):
            st = pre.get(k)
            if st is None:
                st = pre[k] = model.latest(k, float(S))
            mu, s2 = st
            dpi = dnu = 0.0
            cnt = 0
            for j, (e, r, a, b) in pending[k].items():
                if j < i and not (e == event[i] and r == rnd[i]):
                    dpi, dnu, cnt = dpi + a, dnu + b, cnt + 1
            if cnt:
                prec = 1.0 / s2 + dpi
                mu, s2 = (mu / s2 + dnu) / prec, 1.0 / prec
            side.append((mu, s2, NN[k] + cnt))
        (mua, s2a, na), (mub, s2b, nb) = side
        o_mua[i], o_mub[i], o_sa[i], o_sb[i], o_na[i], o_nb[i] = mua, mub, s2a, s2b, na, nb
        if upd[i]:
            won = a_won[i]
            kw, kl = (ka[i], kb[i]) if won else (kb[i], ka[i])
            mw, sw, ml, sl = (mua, s2a, mub, s2b) if won else (mub, s2b, mua, s2a)
            c2 = 2.0 * beta2 + sw + sl
            c = sqrt(c2)
            t = (mw - ml) / c
            if t > -20.0:
                v = INV_SQRT_2PI * exp(-0.5 * t * t) / (0.5 * erfc(-t / SQRT2))
            else:
                v = -t - 1.0 / t + 2.0 / t ** 3
            w = v * (v + t)
            mw2, sw2 = mw + sw / c * v, sw * (1.0 - sw / c2 * w)
            ml2, sl2 = ml - sl / c * v, sl * (1.0 - sl / c2 * w)
            pending[kw][i] = (event[i], rnd[i], 1.0 / sw2 - 1.0 / sw, mw2 / sw2 - mw / sw)
            pending[kl][i] = (event[i], rnd[i], 1.0 / sl2 - 1.0 / sl, ml2 / sl2 - ml / sl)
            by_release.setdefault(lf[i] + 1, []).append((i, kw, kl))
    return np.array(cols, dtype="float64").T


# ------------------------------------------------------------------------------------------------
# Correlated surface skills: one Gaussian skill per surface, correlated (the Bayesian form of the surface blend)

N_SURF = 4                       # hard, clay, grass, carpet (stage1_baselines.SURFACES)


def _apply_message(mu: list, cov: list, s: int, lam: float, eta: float) -> None:
    """Add, in place, a Gaussian message on the skill of surface s (or on the surfaces' average when s < 0): precision
    lam and precision-mean eta in information form. Sherman-Morrison: with a the projection and Sa = cov a,
    mu += Sa (eta - lam a.mu) / (1 + lam a'Sa),  cov -= Sa Sa' lam / (1 + lam a'Sa)."""
    if s >= 0:
        sa = [cov[N_SURF * i + s] for i in range(N_SURF)]
        m, v = mu[s], cov[(N_SURF + 1) * s]
    else:
        sa = [sum(cov[N_SURF * i:N_SURF * i + N_SURF]) / N_SURF for i in range(N_SURF)]
        m, v = sum(mu) / N_SURF, sum(sa) / N_SURF
    den = 1.0 + lam * v
    f = (eta - lam * m) / den
    k = lam / den
    for i in range(N_SURF):
        mu[i] += sa[i] * f
        ki = k * sa[i]
        for j in range(N_SURF):
            cov[N_SURF * i + j] -= ki * sa[j]


def _marginal(mu: list, cov: list, s: int) -> tuple[float, float]:
    if s >= 0:
        return mu[s], cov[(N_SURF + 1) * s]
    return sum(mu) / N_SURF, sum(cov) / (N_SURF * N_SURF)


def correlated_pass(week, event, rnd, a, b, surf, a_won, upd, n_players: int, sigma0: float = 2.0, gamma: float = 0.4,
                    rho: float = 0.8, link: str = "probit", beta: float = 1.0, rho_drift: float | None = None) -> np.ndarray:
    """Correlated surface skills, match by match under the time rule (as trueskill_pass). Each player has a skill per
    surface, jointly Gaussian: a newcomer N(0, sigma0^2 C), C = (1 - rho) I + rho 11' (every pair of surfaces correlated
    rho), and a drift of gamma^2 C_d per year since the player's last period, C_d the same form with rho_drift (rho when
    not given; 1 when a change of form is the same on every surface), capped so that no surface's variance exceeds
    sigma0^2. A match on surface s observes the difference of the two players' skills on s (the surfaces' average where
    the surface is unknown):
        link "probit"  TrueSkill's moment matching on that difference, P = cdf(d / sqrt(2 beta^2 + v_A + v_B));
        link "logit"   the Glicko (Kalman) step, P = logistic(g(sqrt(v_A + v_B)) d), each side updated with
                       g(sqrt(v_opponent)) as in Glicko-1.
    The result moves the played surface's skill, and the other surfaces' through the covariance (exact Gaussian
    conditioning: _apply_message). rho = 1 is the overall rating alone (TrueSkill with tau 0, or Glicko-1 match by match
    with sigma^2 = gamma^2 x 7 / 365.25); smaller rho lets the surfaces part. Round robins and several events of one week
    combine by adding the matches' messages (information form). Returns OUT_COLS: the match surface's mean, its
    variance (probit) or deviation (logit), NaN, rated-match counts."""
    n = len(week)
    C = [(1.0 if i == j else rho) for i in range(N_SURF) for j in range(N_SURF)]
    rd = rho if rho_drift is None else rho_drift
    Cd = [(1.0 if i == j else rd) for i in range(N_SURF) for j in range(N_SURF)]
    s0sq, gam2 = sigma0 * sigma0, gamma * gamma
    MU = [None] * n_players
    COV = [None] * n_players
    TL, NN = [None] * n_players, [0] * n_players
    cols = [[math.nan] * n for _ in OUT_COLS]
    o_mua, o_mub, o_ua, o_ub, _, _, o_na, o_nb = cols
    probit = link == "probit"
    beta2 = beta * beta
    ent: dict = {}            # (player, event) -> [round, mu, cov, pending messages, all messages, folded count]
    pre: dict = {}            # player -> (mu, cov) at the start of the week, drift added
    cur = None
    sqrt, exp, erfc = math.sqrt, math.exp, math.erfc
    for i in range(n):
        D = week[i]
        if D != cur:
            if ent:
                for p, xs in _group_entries(ent).items():
                    cnt = sum(x[5] + sum(1 for _ in x[3]) for x in xs)
                    if not cnt:
                        continue
                    mu, cov = list(pre[p][0]), list(pre[p][1])
                    for x in xs:
                        for msg in x[4]:
                            _apply_message(mu, cov, *msg)
                    MU[p], COV[p], TL[p] = mu, cov, cur
                    NN[p] += cnt
                ent.clear()
                pre.clear()
            cur = D
        e, r, s = event[i], rnd[i], surf[i]
        side = []
        for p in (a[i], b[i]):
            st = pre.get(p)
            if st is None:
                if MU[p] is None:
                    st = ([0.0] * N_SURF, [s0sq * c for c in C])
                else:
                    cov = list(COV[p])
                    if TL[p] is not None and gam2 > 0.0:
                        dy = (D - TL[p]) / DAYS_PER_YEAR
                        room = (s0sq - max(cov[(N_SURF + 1) * k] for k in range(N_SURF))) / gam2
                        dy = min(dy, max(room, 0.0))
                        for k in range(N_SURF * N_SURF):
                            cov[k] += gam2 * dy * Cd[k]
                    st = (list(MU[p]), cov)
                pre[p] = st
            x = ent.get((p, e))
            if x is None:
                x = ent[(p, e)] = [r, list(st[0]), list(st[1]), [], [], 0]
            elif x[0] < r:
                for msg in x[3]:
                    _apply_message(x[1], x[2], *msg)
                x[5] += len(x[3])
                x[3] = []
                x[0] = r
            side.append((x, NN[p] + x[5]))
        (xa, na), (xb, nb) = side
        ma, va = _marginal(xa[1], xa[2], s)
        mb, vb = _marginal(xb[1], xb[2], s)
        o_mua[i], o_mub[i], o_na[i], o_nb[i] = ma, mb, na, nb
        if probit:
            o_ua[i], o_ub[i] = va, vb
        else:
            o_ua[i], o_ub[i] = sqrt(va), sqrt(vb)
        if upd[i]:
            won = a_won[i]
            if probit:
                mw, vw_, ml, vl = (ma, va, mb, vb) if won else (mb, vb, ma, va)
                c2 = 2.0 * beta2 + vw_ + vl
                c = sqrt(c2)
                t = (mw - ml) / c
                if t > -20.0:
                    v = INV_SQRT_2PI * exp(-0.5 * t * t) / (0.5 * erfc(-t / SQRT2))
                else:
                    v = -t - 1.0 / t + 2.0 / t ** 3
                w = v * (v + t)
                mw2, vw2 = mw + vw_ / c * v, vw_ * (1.0 - vw_ / c2 * w)
                ml2, vl2 = ml - vl / c * v, vl * (1.0 - vl / c2 * w)
                lw, ew = 1.0 / vw2 - 1.0 / vw_, mw2 / vw2 - mw / vw_
                ll_, el = 1.0 / vl2 - 1.0 / vl, ml2 / vl2 - ml / vl
                (la, ea_), (lb, eb_) = ((lw, ew), (ll_, el)) if won else ((ll_, el), (lw, ew))
            else:
                gb = 1.0 / sqrt(1.0 + 3.0 * vb / PI2)
                pa, qa = logistic2(gb * (ma - mb))
                la = gb * gb * pa * qa
                ea_ = la * ma + gb * (qa if won else -pa)
                ga = 1.0 / sqrt(1.0 + 3.0 * va / PI2)
                pb, qb = logistic2(ga * (mb - ma))
                lb = ga * ga * pb * qb
                eb_ = lb * mb + ga * (-pb if won else qb)
            for xx, lam, eta in ((xa, la, ea_), (xb, lb, eb_)):
                xx[3].append((s, lam, eta))
                xx[4].append((s, lam, eta))
    return np.array(cols, dtype="float64").T


def _group_entries(ent: dict) -> dict:
    out: dict = {}
    for (p, _), x in ent.items():
        out.setdefault(p, []).append(x)
    return out


# ------------------------------------------------------------------------------------------------
# The two components and the blend

def run(h: dict, system: str, cfg: dict) -> dict:
    """The overall and surface components of one system on one tour's history (rating_systems.common.history):
    {"overall": array, "surface": array}, each with OUT_COLS per match (the surface one NaN where the surface is
    unknown)."""
    a, b, surf, n = h["a"], h["b"], h["surf"], h["n_players"]
    if system in ("trueskill_cs", "glicko_cs"):        # one surface-specific forecast; no separate surface component
        if system == "trueskill_cs":
            kw = {"sigma0": cfg["sigma0"], "gamma": cfg["gamma"], "link": "probit"}
        else:                                           # Glicko's constants: RD0 and the weekly drift sigma
            kw = {"sigma0": cfg["rd0"] / SCALE, "gamma": cfg["sigma0"] * math.sqrt(DAYS_PER_YEAR / 7.0), "link": "logit"}
        return {"overall": correlated_pass(h["week"], h["event"], h["rnd"], a, b, surf, h["a_won"], h["upd"], n,
                                           rho=cfg["rho"], rho_drift=cfg.get("rho_drift"), **kw)}
    every = h["all"]
    known = h["surf_known"]
    ksa = [p * 4 + s if s >= 0 else 0 for p, s in zip(a, surf)]
    ksb = [p * 4 + s if s >= 0 else 0 for p, s in zip(b, surf)]
    out = {}
    for comp, (ka, kb, act, nk) in {"overall": (a, b, every, n), "surface": (ksa, ksb, known, 4 * n)}.items():
        if comp == "surface" and not cfg.get("surface", True):
            continue
        if system in ("glicko2", "glicko1"):
            out[comp] = glicko_pass(h["week"], h["event"], h["rnd"], ka, kb, h["a_won"], act, h["upd"], nk,
                                    rd0=cfg["rd0"], sigma0=cfg["sigma0"], tau=cfg.get("tau", 0.5),
                                    period=cfg.get("period", 7.0), vol=(system == "glicko2"))
        elif system in ("glicko2m", "glicko1m"):
            out[comp] = glicko_seq_pass(h["week"], h["event"], h["rnd"], ka, kb, h["a_won"], act, h["upd"], nk,
                                        rd0=cfg["rd0"], sigma0=cfg["sigma0"], tau=cfg.get("tau", 0.5),
                                        period=cfg.get("period", 7.0), vol=(system == "glicko2m"))
        elif system == "trueskill":
            out[comp] = trueskill_pass(h["week"], h["event"], h["rnd"], ka, kb, h["a_won"], act, h["upd"], nk,
                                       sigma0=cfg["sigma0"], tau=cfg["tau"], gamma=cfg["gamma"])
        elif system in ("ttt", "ttt_hold"):
            out[comp] = ttt_pass(h["week"], h["event"], h["rnd"], ka, kb, h["a_won"], act, h["upd"], nk,
                                 sigma0=cfg["sigma0"], gamma=cfg["gamma"], window=int(cfg.get("window", 26)),
                                 sweeps=int(cfg.get("sweeps", 1)),
                                 hold=h.get("fortnight") if system == "ttt_hold" else None)
        elif system == "ttt_timed":                     # the leak-proof timeline: h["es"], h["lf"] per row
            out[comp] = ttt_pass_timed(h["es"], h["lf"], h["event"], h["rnd"], ka, kb, h["a_won"], act, h["upd"], nk,
                                       sigma0=cfg["sigma0"], gamma=cfg["gamma"],
                                       window_days=float(cfg["window_days"]), sweeps=int(cfg.get("sweeps", 1)),
                                       smooth_every=cfg.get("smooth_every", "week"))
        else:
            raise ValueError(system)
    return out


def blend(system: str, res: dict, w: float) -> np.ndarray:
    """P(A wins) from the overall and surface components: means blended (1 - w) overall + w surface, as Stage 1's
    surface Elo blends ratings; the uncertainty blended the same way on the variance scale. Overall alone where the
    surface is unknown (or w is 0)."""
    o = res["overall"]
    s = res.get("surface")
    if s is None or w == 0.0:
        mua, mub, ua, ub = o[:, 0], o[:, 1], o[:, 2], o[:, 3]
    else:
        known = np.isfinite(s[:, 0])
        sm_a, sm_b = np.where(known, s[:, 0], o[:, 0]), np.where(known, s[:, 1], o[:, 1])
        su_a, su_b = np.where(known, s[:, 2], o[:, 2]), np.where(known, s[:, 3], o[:, 3])
        mua, mub = (1 - w) * o[:, 0] + w * sm_a, (1 - w) * o[:, 1] + w * sm_b
        if system in ("trueskill", "ttt", "ttt_hold", "ttt_timed"):
            ua, ub = (1 - w) * o[:, 2] + w * su_a, (1 - w) * o[:, 3] + w * su_b
        else:
            ua = np.sqrt((1 - w) * o[:, 2] ** 2 + w * su_a ** 2)
            ub = np.sqrt((1 - w) * o[:, 3] ** 2 + w * su_b ** 2)
    if system in ("trueskill", "trueskill_cs", "ttt", "ttt_hold", "ttt_timed"):  # u is a variance
        return p_trueskill(mua, mub, ua, ub)
    return p_glicko(mua, mub, ua, ub)                    # u is a deviation (phi)
