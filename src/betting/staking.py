"""Betting math: implied probabilities, EV, fractional Kelly, closing-line value.

Decimal-odds-native (tennis data sources quote decimal). This mirrors the UFC
pipeline's betting layer in spirit — EV is computed against RAW vig-inclusive
odds (conservative: you must clear the vig, not a devigged fair price), and
stake sizing is fractional Kelly with an explicit cap.

Vig removal lives here ONLY for diagnostics/feature engineering (e.g. building
a market-probability feature), never inside the EV gate.
"""

import math


def implied_prob(decimal_odds: float) -> float:
    """Vig-inclusive implied probability of decimal odds."""
    if decimal_odds <= 1.0:
        raise ValueError(f"decimal odds must exceed 1.0, got {decimal_odds}")
    return 1.0 / decimal_odds


def remove_vig_proportional(p_a: float, p_b: float) -> tuple[float, float]:
    """Proportional (multiplicative) devig of a two-way market. Diagnostics only."""
    total = p_a + p_b
    if total <= 0:
        raise ValueError("implied probabilities must be positive")
    return p_a / total, p_b / total


def ev_per_unit(model_p: float, decimal_odds: float) -> float:
    """Expected profit per 1 unit staked: p*odds - 1 (raw, vig-inclusive odds)."""
    if not 0.0 <= model_p <= 1.0:
        raise ValueError(f"model_p must be in [0,1], got {model_p}")
    return model_p * decimal_odds - 1.0


def kelly_fraction(model_p: float, decimal_odds: float) -> float:
    """Full-Kelly fraction of bankroll: (p*odds - 1) / (odds - 1). Floored at 0."""
    edge = ev_per_unit(model_p, decimal_odds)
    return max(0.0, edge / (decimal_odds - 1.0))


def stake(model_p: float, decimal_odds: float, bankroll: float,
          kelly_multiplier: float = 0.33, cap_fraction: float = 0.05) -> float:
    """Fractional Kelly stake with a hard cap (both knobs explicit, no defaults
    buried downstream). Returns 0.0 when there is no positive edge."""
    if bankroll <= 0:
        raise ValueError(f"bankroll must be positive, got {bankroll}")
    if not 0.0 < kelly_multiplier <= 1.0:
        raise ValueError(f"kelly_multiplier must be in (0,1], got {kelly_multiplier}")
    f = kelly_fraction(model_p, decimal_odds) * kelly_multiplier
    return bankroll * min(f, cap_fraction)


def clv_pct(bet_odds: float, close_odds: float) -> float:
    """Closing-line value in percent: how much better your price was than the
    close, (bet_odds / close_odds - 1) * 100. Positive = you beat the close.
    Compare same book (e.g. Pinnacle close) or the comparison is meaningless."""
    if bet_odds <= 1.0 or close_odds <= 1.0:
        raise ValueError("odds must exceed 1.0")
    return (bet_odds / close_odds - 1.0) * 100.0


def log_growth(model_p: float, decimal_odds: float, fraction: float) -> float:
    """Expected log-bankroll growth of staking `fraction` at these odds under
    the model's probability — the quantity Kelly maximizes. Useful for studies."""
    if not 0.0 < fraction < 1.0:
        raise ValueError(f"fraction must be in (0,1), got {fraction}")
    win_term = model_p * math.log(1.0 + fraction * (decimal_odds - 1.0))
    lose_term = (1.0 - model_p) * math.log(1.0 - fraction)
    return win_term + lose_term
