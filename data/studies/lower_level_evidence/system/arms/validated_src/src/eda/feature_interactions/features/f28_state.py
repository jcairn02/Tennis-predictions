"""B-STATE (final family after meta checkpoint 1, R-1: BOD-C1 alone, sign +, weight 0.5, no trait): BOD-C1, fatigue-
contaminated form (dPastFat). INFO-1, the one-step IOS update from each player's own matches the clock has not counted
yet, LEFT the block (USE_INFO1 = False: its premise is false, see CAVEAT) and is kept only as a descriptive sensitivity.

INFO-1 (rulings.md, "the cleanest formulation"): for player X at model match m, K = X's own earlier matches k with
lf_k + 1 > es_m (a result counts from the day after its latest finish, so these are outside every cross-player input;
almost always the previous day's round). For each k that the IOS pool counts (completed, a box score, a row in the
surface-IOS table) take, on serve points won (spw, the IOS scale y = logit((x + 1/2)/(d + 1)) - logit(mu), mu the tour's
average on the surface, Stage B's constants):
    serve residual   r_s = y(X's serve at k) - (O_X - D_opp), return residual r_r = y(opp's serve at k) - (O_opp - D_X),
                     with O, D the panel's surface-IOS states of that match (srf_O_eff_spw, srf_D_eff_spw, read at es_k:
                     leak-proof, the IOS the model already uses)
    one-step update  dO = w r_s / (W_O + w + kappa), dD = -w r_r / (W_D + w + kappa): the ridge's exact update of X's own O
                     (D) with every other rating held; w = (points / d_typ)^tau, W = X's decayed weight of earlier pool
                     matches (half-life h); h = 52 weeks, kappa = 1, tau = 1, d_typ = 73.7 / 70.6 serve points (men /
                     women): Stage B's tuned constants as the leak-proof rebuild uses them (match_timing/rebuild
                     .ios_constants), fixed, not tuned here. Opponents' ratings are not updated.
    member           x1 = (sum_K dO_A + dD_A) - (sum_K dO_B + dD_B); 0 when K is empty. The missing-update flag marks an
                     uncounted own played match with no computable update (no box score, outside the pool, retired).
CAVEAT (observed in round2/builds/body.md): the leak-proof IOS's own incremental step (src/eda/match_timing/ios_time.py,
docstring; ios_surface.py: "each player's own earlier matches that the snapshot does not hold yet are then added to their
own block") already adds these matches to the player's O and D: the panel's own IOS change correlates 0.879 with this
update (slope 1.10) on 22,696 player-matches. The meta-auditor ruled INFO-1 out of the block (checkpoint 1, R-1); its
column is the descriptive sensitivity "B-STATE INFO-1 (descriptive)". Its prevalence collapses for women from 2020
(clock widths: feasibility_round2.md section 3).

BOD-C1: PastFat_X = the mean of X's pre-match Fat (f20, tau 3 days) over X's own played matches in the 14 days before
(missing when none); x2 = PastFat_A - PastFat_B (sign +, given dFat).
Block: x = z(x2), BOD-C1 alone (clipped at its 99th percentile and divided by its SD on 2014-2021; missing where
PastFat is missing for either player, and the batch then adds 1[missing] x eta). Controls (the family's, unchanged by
R-1): adjperf_tpw_2w, ios_points_short, dFat, sets_14d, the missing-update difference, the PastFat-missing difference,
the nearest inputs (recomputed for BOD-C1 alone and fixed in f20.NEAREST); eta-mod: the symmetric missing indicators.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from src.eda.feature_interactions import common as C
from src.eda.feature_interactions.features import f20_fatigue as F

H_WEEKS, KAPPA, TAU, D_TYP = 52.0, 1.0, 1.0, {"atp": 73.68464648570998, "wta": 70.59231691162556}
LOOKBACK, PASTFAT_DAYS = 8, 14.0
# INFO-1 is OUT of the block (meta checkpoint 1, R-1 / F-1): its premise is false, the leak-proof IOS already holds the
# uncounted own match (corr 0.879, slope 1.10 against this update; round2/builds/body.md). Its column stays computable
# as a descriptive sensitivity (SENSITIVITIES below): it never gates and never enters the bundle.
USE_INFO1 = False


def _mu_spw(H: pd.DataFrame) -> np.ndarray:
    from src.eda.ufc_ideas import stageB_common as B
    means = B.surface_means()["spw"]
    keys = zip(H["tour"].astype(str), H["surface"].astype(str))
    mu = np.array([means.get(k, means.get((k[0], "all"), np.nan)) for k in keys], float)
    return np.log(mu / (1 - mu))


def ios_states(H: pd.DataFrame) -> dict:
    """Own and opponent spw O/D per history row, from the surface-IOS table (NaN outside it)."""
    sf = pd.read_parquet(C.ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet",
                         columns=["match_id", "srf_O_eff_spw_a", "srf_D_eff_spw_a", "srf_O_eff_spw_b", "srf_D_eff_spw_b"])
    sf["match_id"] = sf["match_id"].astype(str)
    sf = sf[sf["match_id"].isin(set(H["match_id"].astype(str)))]          # only the history's (<= the panel's) matches
    sf = sf.drop_duplicates("match_id").set_index("match_id")
    mid = H["match_id"].astype(str)
    is_a = (H["side"] == "A").to_numpy()
    v = {k: mid.map(sf[k]).to_numpy(float) for k in sf.columns}
    pick = lambda own, x: np.where(is_a == own, v[f"{x}_a"], v[f"{x}_b"])  # noqa: E731
    return {"O": pick(True, "srf_O_eff_spw"), "D": pick(True, "srf_D_eff_spw"),
            "O_opp": pick(False, "srf_O_eff_spw"), "D_opp": pick(False, "srf_D_eff_spw")}


def one_step(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(dO + dD of each history row's own match, 1[the row is an own played match without a computable update])."""
    if "_info1" not in H.columns:
        S = ios_states(H)
        mu = _mu_spw(H)
        sn, sd, rn, rd = (H[k].to_numpy(float) for k in ("spw_n", "spw_d", "rpw_n", "rpw_d"))
        dtyp = np.where(H["tour"].astype(str).to_numpy() == "atp", D_TYP["atp"], D_TYP["wta"])
        ok = (H["status"].astype(str).to_numpy() == "completed") & (sd > 0) & (rd > 0) & np.isfinite(S["O"]) \
            & np.isfinite(S["D"]) & np.isfinite(S["O_opp"]) & np.isfinite(S["D_opp"]) & np.isfinite(mu)
        with np.errstate(invalid="ignore", divide="ignore"):
            ys = np.log((sn + 0.5) / (sd - sn + 0.5)) - mu
            yr = np.log((rd - rn + 0.5) / (rn + 0.5)) - mu
        ws, wr = np.where(ok, (sd / dtyp) ** TAU, 0.0), np.where(ok, (rd / dtyp) ** TAU, 0.0)
        pid, t = H["pid"].to_numpy(), H["t"].to_numpy(float)
        tau_d = H_WEEKS * 7.0 / math.log(2.0)
        WO, WD = F.decayed_sum(pid, t, ws, tau_d), F.decayed_sum(pid, t, wr, tau_d)
        dO = np.where(ok, ws * (ys - (S["O"] - S["D_opp"])) / (WO + ws + KAPPA), 0.0)
        dD = np.where(ok, -wr * (yr - (S["O_opp"] - S["D"])) / (WD + wr + KAPPA), 0.0)
        H["_info1"] = dO + dD
        H["_info1_miss"] = (H["played"].to_numpy(bool) & ~ok).astype(float)
        H["_info1_dO"] = np.where(ok, dO, np.nan)
    return H["_info1"].to_numpy(float), H["_info1_miss"].to_numpy(float)


def uncounted(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per row i: (sum of the updates of the player's earlier rows k with lf_k + 1 > es_i, 1[any such played row has no
    update], the number of such rows), looking back LOOKBACK rows (an uncounted window never spans more)."""
    u, miss = one_step(H)
    pid = H["pid"].to_numpy()
    es, lf = H["es"].to_numpy(float), H["lf"].to_numpy(float)
    played = H["played"].to_numpy(bool)
    n = len(H)
    tot, flag, cnt = np.zeros(n), np.zeros(n), np.zeros(n)
    for j in range(1, LOOKBACK + 1):
        k = np.arange(n) - j
        valid = (k >= 0)
        kk = np.maximum(k, 0)
        same = valid & (pid[kk] == pid)
        unc = same & played[kk] & (lf[kk] + 1 > es)
        tot += np.where(unc, u[kk], 0.0)
        flag = np.maximum(flag, np.where(unc, miss[kk], 0.0))
        cnt += unc
    return tot, flag, cnt


def past_fat(H: pd.DataFrame) -> np.ndarray:
    """BOD-C1: the mean pre-match Fat over the player's played rows in the 14 days before (strictly earlier rows)."""
    f, _ = F.fat(H)
    pid, t = H["pid"].to_numpy().astype(float), H["t"].to_numpy(float)
    played = H["played"].to_numpy(bool).astype(float)
    key = pid * 1e6 + t
    lo = np.searchsorted(key, pid * 1e6 + t - PASTFAT_DAYS, side="left")
    g = H["pid"].to_numpy()
    fp = f * played
    Sf = pd.Series(fp).groupby(g).cumsum().to_numpy() - fp          # within the player, rows strictly before
    Sn = pd.Series(played).groupby(g).cumsum().to_numpy() - played
    n = Sn - Sn[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, (Sf - Sf[lo]) / np.maximum(n, 1), np.nan)


def prepare_state(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = F.history(P, L)
    tot, flag, cnt = uncounted(H)
    f, _ = F.fat(H)
    out = {}
    for k, v in {"info1": tot, "info1_miss": flag, "info1_n": cnt, "pastfat": past_fat(H), "fat": f}.items():
        out[f"bdst_{k}_a"], out[f"bdst_{k}_b"] = F.at_model(P, H, v)
    return out


def state_members(P: pd.DataFrame) -> dict:
    (ia, ib), (pa, pb) = F.ab(P, "bdst_info1"), F.ab(P, "bdst_pastfat")
    return {"INFO-1": ia - ib, "BOD-C1": pa - pb}


def combine_state(P: pd.DataFrame) -> dict:
    M = state_members(P)
    x = F.block(P, [(M["INFO-1"], +1), (M["BOD-C1"], +1)] if USE_INFO1 else [(M["BOD-C1"], +1)])
    (ma, mb), (pa, pb), (fa, fb) = F.ab(P, "bdst_info1_miss"), F.ab(P, "bdst_pastfat"), F.ab(P, "bdst_fat")
    named = {"in_adjperf_tpw_2w": F.col(P, "in_adjperf_tpw_2w"), "in_ios_points_short": F.col(P, "in_ios_points_short"),
             "fat_a-b": fa - fb, "in_sets_14d": F.col(P, "in_sets_14d"), "update_missing_a-b": ma - mb,
             "pastfat_missing_a-b": F.miss_diff(pa, pb)}
    ctrl, names = F.controls(P, named, x, F.NEAREST.get("B-STATE"))
    mods = np.column_stack([F.centre(P, np.fmax(ma, mb)), F.centre(P, F.sym_miss(pa, pb))])
    tab = {"bdst_pastfat": (M["BOD-C1"], "diff", None)}
    if USE_INFO1:
        tab["bdst_info1"] = (M["INFO-1"], "diff", None)
    # the controls stay as the family lists them (R-1: "the same controls"), the update-missing flag included
    return {"x": x, "controls": ctrl, "control_names": names, "eta_mod_controls": mods, "tabpfn": tab}


# descriptive sensitivities (meta checkpoint 1, F-6 interface): run once in the batch if its scope includes them; never
# gate, never enter the bundle. P carries B-STATE's prepare() columns.
SENSITIVITIES = {"B-STATE INFO-1 (descriptive)": lambda P: state_members(P)["INFO-1"]}
SENSITIVITY_OF = {name: "B-STATE" for name in SENSITIVITIES}


HYPOTHESES = [
    {"hid": "B-STATE", "master": "INFO-1+BOD-C1" if USE_INFO1 else "BOD-C1", "kind": "W", "sign": "+", "weight": 0.5, "trait": "none",
     "deployment": "diff", "prepare": prepare_state, "combine": combine_state, "family": "16/11",
     "members": {"INFO-1": "+", "BOD-C1": "+"} if USE_INFO1 else {"BOD-C1": "+"}},
]
