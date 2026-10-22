"""Part F of the source-reconciliation study: the odds input where Pinnacle's close is missing (shared pieces).

The current best model's odds input is "Pinnacle first" (docs/decisions/2026-10-09-pinnacle-first-odds-input.md;
src/eda/current_best_model/odds_input.py): Pinnacle's close (tennis-data's to July 2025, reconciled with OddsTrader's
timed copy, then OddsTrader's to 7 Sep 2025), else BetOnline's last line, else the books' average. So the training
rows from August 2025 on carry BetOnline's line as a stand-in for a Pinnacle close that was never recorded. This part
asks which available price, or combination of prices, is the best stand-in.

Everything here reads the template instance of 14 Oct 2026 (its per-source table, written by odds_input.py --apply
through src/eda/odds_sources/table.py) and the odds-sources study's rules (late OddsTrader lines dropped, proportional
margin removal, log-odds averages, four-week blocks). Nothing here writes outside data/studies/source_reconciliation/odds/.

The seal: matches played from 29 Jul 2026 on are the proposed sealed holdout. Their results are never read: `results()`
reads a_won through a parquet filter on both the tournament's start date and tennis-data's match day, so the column
of a later row never leaves the file. Every other column (prices, dates) may be read for every row: comparing two
sources' prices reads no result.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import odds_input as OI  # noqa: E402
from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.odds_sources import pools as P  # noqa: E402
from src.eda.odds_sources import quality as Q  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

TEMPLATE = C.STUDIES / "current_best_model" / "template_2026-10-14"
TABLE = TEMPLATE / "odds_sources.parquet"            # one row per frame match, every source's price for side A
ODDS_INPUT_JSON = TEMPLATE / "odds_input.json"
FRAME = TEMPLATE / "model_frame.parquet"
SHARP = C.STUDIES / "sharp_benchmark" / "matches.parquet"    # Polymarket at nine horizons (tennis-data rows 2025-26)
BOL_MATCHES = C.DUMP / "odds" / "oddstrader" / "betonline_matches.parquet"   # BetOnline opening and last line
OT_BOOKS = C.DUMP / "odds" / "oddstrader" / "books_lines.parquet"
OT_EVENTS = C.DUMP / "odds" / "oddstrader" / "events.parquet"
STAGE1 = C.STAGE0_LIVE / "stage1_odds.parquet"      # tennis-data's file and row per match (hand checks only)
OUT = C.OUT / "odds"

SEAL = C.SEAL                                       # 2026-07-29
GAP_FROM = pd.Timestamp("2025-08-01")               # Pinnacle's faithful close runs out (tennis-data from August 2025)
PS_FAITHFUL_UNTIL = pd.Timestamp(P.PS_FAITHFUL_UNTIL)   # 2025-07-31
PIN_FIT_FROM = pd.Timestamp("2018-01-01")           # OddsTrader's books (and the proxy's fit) start in 2018
STANDIN = ("betonline", "average")                  # odds_input.construct's kinds without a Pinnacle close
OT_LEFT_OUT = {"ot8": "BetOnline", "ot131": "SportsBetting.ag (BetOnline's clone)", "ot20": "Pinnacle",
               # faulty ids found by the odds-sources study (§ 2.3), before this part; neither prices a gap row
               "ot88": "not a match-winner line (738 gross disagreements per 1,000)",
               "ot63": "sides against the result (2.6 gross per 1,000, 17% of its splits)"}
OTMED_MIN = 3

# The candidates, fixed before any result in the gap was read (REPORT.md, "Process").
SINGLES = {
    "bol": "BetOnline's last line (OddsTrader id 8; today's stand-in)",
    "bfe": "Betfair exchange close (tennis-data BFEW/BFEL)",
    "pm": "Polymarket, 30 min before the listed start (sharp benchmark)",
    "psx": "tennis-data's PSW/PSL after July 2025",
    "b365": "Bet365 close (tennis-data)",
    "avg": "The books' average (tennis-data, OddsPortal's panel)",
    "max": "The books' maximum (tennis-data, OddsPortal's panel)",
    "otmed": "OddsTrader's other books, median of log-odds (>= 3 books)",
}
# Added after the identity checks (odds_psx.py, distance to Pinnacle), before any gap result for them was read
# (declared.json "additions"): the OddsTrader book nearest to Pinnacle's own close after the August 2025 change.
ADDED = {
    "b105": "Bet105's last line (OddsTrader id 130), late lines dropped",
    "b105_pre": "Bet105's last line, only lines stamped at or before the listed start",
}
SHORT = {"bol": "BetOnline", "bfe": "Betfair", "pm": "Polymarket 30 min", "psx": "tennis-data PS after Jul 2025",
         "b365": "Bet365", "avg": "Average", "max": "Maximum", "otmed": "OddsTrader median", "pin": "Pinnacle",
         "b105": "Bet105", "b105_pre": "Bet105 (stamped by the listed start)", "pm60": "Polymarket 60 min"}


def short(name: str) -> str:
    if name in SHORT:
        return SHORT[name]
    if name.startswith("eq_"):
        return "Equal: " + " + ".join(SHORT.get(m, m) for m in name[3:].split("+"))
    if name.startswith("wf_"):
        return "Walk-forward weights: " + " + ".join(SHORT.get(m, m) for m in name[3:].split("+"))
    return name


# --------------------------------------------------------------------------------------------- reading
def table_columns() -> list[str]:
    return [c for c in pq.read_schema(TABLE).names if c != "a_won"]


def load_table() -> pd.DataFrame:
    """The template's per-source table without its result column; OddsTrader's lines stamped over 30 minutes after the
    listed start dropped (quality.drop_late, as the model's input); with the model's own odds-input kind and chance
    (odds_input.construct) and Pinnacle's reconciled close (pools.reconciled)."""
    raw = pd.read_parquet(TABLE, columns=table_columns())
    raw["match_id"] = raw["match_id"].astype(str)
    built = OI.construct(raw)                                   # reads no result
    df = Q.drop_late(raw).reset_index(drop=True)
    if not (df["match_id"].to_numpy() == built["match_id"].to_numpy()).all():
        raise RuntimeError("odds_input.construct changed the row order")
    df["kind"] = built["odds_input"].to_numpy()
    df["p_input"] = built["p_input"].to_numpy(float)
    df["p_pin"], _, df["pin_choice"] = P.reconciled(df, with_choice=True)
    df["td_date"] = pd.to_datetime(df["td_date"])
    df["tournament_date"] = pd.to_datetime(df["tournament_date"])
    df["month"] = df["td_date"].dt.to_period("M").astype(str)
    df["sealed"] = ((df["td_date"] >= SEAL) | (df["tournament_date"] >= SEAL)).to_numpy()
    df["gap"] = ((df["td_date"] >= GAP_FROM) & df["kind"].isin(STANDIN)).to_numpy()
    df["pin_known"] = np.isfinite(df["p_pin"].to_numpy(float))
    return add_candidates(df)


def ot_books(df: pd.DataFrame) -> list[str]:
    """OddsTrader's closing books that enter the "other books" median: all kept by table.py except BetOnline, its clone
    and Pinnacle."""
    return [s for s in Q.closing_ot(df) if s not in OT_LEFT_OUT]


def add_candidates(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["p_bol"] = df["p_ot8"].to_numpy(float)
    after = (df["td_date"] > PS_FAITHFUL_UNTIL).to_numpy()
    df["p_psx"] = np.where(after, df["p_ps"].to_numpy(float), np.nan)
    df["p_pm"] = df["p_pm_m30"].to_numpy(float)
    books = ot_books(df)
    P_ = df[[f"p_{s}" for s in books]].to_numpy(float)
    df["p_otmed"] = OC.median_logit(P_, OTMED_MIN)
    df["n_ot_other"] = np.isfinite(P_).sum(axis=1)
    df["p_b105"] = df["p_ot130"].to_numpy(float)
    df["p_b105_pre"] = np.where((df["after_ot130_min"] <= 0).to_numpy(), df["p_ot130"].to_numpy(float), np.nan)
    return df


def results(columns_extra: tuple[str, ...] = ()) -> pd.Series:
    """a_won (1.0 when side A won) of the frame's matches played before SEAL, by match id. The parquet filter keeps
    later rows' results inside the file."""
    filt = [("tournament_date", "<", pd.Timestamp(SEAL).to_pydatetime()),
            ("td_date", "<", pd.Timestamp(SEAL).to_pydatetime())]
    t = pq.read_table(TABLE, columns=["match_id", "a_won", "tournament_date", "td_date", *columns_extra], filters=filt)
    r = t.to_pandas()
    if len(r) and (pd.to_datetime(r["td_date"]).max() >= SEAL or pd.to_datetime(r["tournament_date"]).max() >= SEAL):
        raise RuntimeError("a result from the sealed holdout was read")
    return pd.Series(r["a_won"].astype(float).to_numpy(), index=r["match_id"].astype(str).to_numpy(), name="y")


def attach_y(df: pd.DataFrame) -> np.ndarray:
    """The result per row of df (NaN for sealed rows, which results() never returns)."""
    y = results()
    return y.reindex(df["match_id"].astype(str)).to_numpy(float)


# --------------------------------------------------------------------------------------------- combining
def lg(p) -> np.ndarray:
    return OC.lg(p)


def ex(z) -> np.ndarray:
    return OC.ex(z)


def equal(df: pd.DataFrame, members: list[str], min_count: int | None = None) -> np.ndarray:
    """Equal log-odds average of the members' margin-free chances; NaN unless min_count of them price the match
    (default: all of them)."""
    P_ = df[[f"p_{m}" for m in members]].to_numpy(float)
    return OC.mean_logit(P_, min_count=len(members) if min_count is None else min_count)


# --------------------------------------------------------------------------------------------- scoring
def log_loss(p, y) -> np.ndarray:
    return OC.log_loss(p, y)


def kl(p_ref, q) -> np.ndarray:
    """KL(p_ref || q) per match, nats: the log loss q gives away against p_ref if p_ref were the true chance."""
    p = np.clip(np.asarray(p_ref, float), OC.EPS, 1 - OC.EPS)
    q = np.clip(np.asarray(q, float), OC.EPS, 1 - OC.EPS)
    return p * np.log(p / q) + (1 - p) * np.log((1 - p) / (1 - q))


def ci(v, clusters, scale: float = 1000.0) -> dict:
    """odds_sources' clustered mean (four-week blocks by default), plus the SE, P(the mean is below 0), i.e.
    P(the first-named better) for a difference "A - B" of log losses, and the two-sided p-value of "no difference".
    P and p use the same t distribution on G - 1 degrees of freedom as the interval, so P(better) exceeds 0.975 exactly
    when the 95% interval clears 0 (with few blocks the normal approximation would overstate it)."""
    out = OC.mean_ci(v, clusters, scale)
    if out["est"] is None or out["blocks"] < 2 or not np.isfinite(out["hi"]):
        out.update(se=None, p_neg=None, p_two_sided=None)
        return out
    dof = out["blocks"] - 1
    tq = student_t.ppf(0.975, dof)
    se = (out["hi"] - out["est"]) / tq
    out["se"] = se
    if se > 0:
        out["p_neg"] = float(student_t.cdf(-out["est"] / se, dof))
        out["p_two_sided"] = float(2 * student_t.cdf(-abs(out["est"]) / se, dof))
    else:
        out["p_neg"], out["p_two_sided"] = (1.0 if out["est"] < 0 else 0.0), 0.0
    return out


def verdict(c: dict) -> str:
    """"better" / "worse" for a difference "candidate - base" (lower log loss is better) when the 95% interval clears
    0, else "unresolved"."""
    if not c or c.get("est") is None:
        return "-"
    if c["hi"] < 0:
        return "better"
    if c["lo"] > 0:
        return "worse"
    return "unresolved"


def fmt(c: dict | None, digits: int = 2) -> str:
    if not c or c.get("est") is None:
        return "—"
    return f"{c['est']:+.{digits}f} [{c['lo']:+.{digits}f}, {c['hi']:+.{digits}f}]"


def fmt_v(c: dict | None, digits: int = 2) -> str:
    """The difference with its verdict and P(better), as the reports write it."""
    if not c or c.get("est") is None:
        return "—"
    v = verdict(c)
    tail = f", P(better) {c['p_neg']:.2f}" if v == "unresolved" and c.get("p_neg") is not None else ""
    return f"{fmt(c, digits)}, {v}{tail}"


def paired(p_a, p_b, y, blocks, mask=None) -> dict:
    """Log loss of A minus B (mLL, + = A worse), on the rows where both are priced and the result is known."""
    p_a, p_b, y = np.asarray(p_a, float), np.asarray(p_b, float), np.asarray(y, float)
    m = np.isfinite(p_a) & np.isfinite(p_b) & np.isfinite(y)
    if mask is not None:
        m &= np.asarray(mask, bool)
    if m.sum() < 30:
        return {"est": None, "n": int(m.sum())}
    out = ci(log_loss(p_a[m], y[m]) - log_loss(p_b[m], y[m]), np.asarray(blocks)[m])
    out["ll_a"] = round(float(log_loss(p_a[m], y[m]).mean()), 5)
    out["ll_b"] = round(float(log_loss(p_b[m], y[m]).mean()), 5)
    return out


def sha_inputs() -> dict:
    """SHA-256 of the files this part reads."""
    files = [TABLE, ODDS_INPUT_JSON, FRAME, SHARP, BOL_MATCHES, STAGE1]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): C.sha256(p) for p in files if p.exists()}


def write_json(path: Path, value) -> None:
    C.write_json(path, value)
