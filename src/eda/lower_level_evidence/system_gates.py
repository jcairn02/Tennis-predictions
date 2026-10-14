"""The gates of the lower-level-evidence system's arms (role C1): every arm passes them before it is marked READY for role
D. Results go to data/studies/lower_level_evidence/system/arms/<ARM>/gates/.

    G1 identity      (IDENTITY, IDENTITY_ALL) the arm's frame against the frozen reference's: the same matches in the same
                     order, the same identifiers, the same result column through 2024 (a filtered read: later seasons'
                     results are never read), and every one of the 58 inputs exactly (largest difference 0, the same
                     missing cells); and the tuned constants the reference's (Stage 1, the offset, Stage 3, Stage B)
    G2 invariance    inputs no reached observation can reach do not move. "Reached": the levels the arm changes (SEP_ALL:
                     every lower level, men; REF_noITF: ITF and ITFQ box rows, both tours). Exact (difference 0, the same
                     missing cells) on: every input of a tour outside the arm; the untouched inputs (odds, context, age,
                     sets, the surface pairs) everywhere; the inputs of the families the arm switches off, everywhere;
                     points_52w where neither player has a reached box row in the 364 days to the match; the 17 forms
                     where neither player has a reached box row, nor one played against an opponent holding a reached box
                     row before it; every input of matches before the tour's first reached row, by event date and by the
                     match clock (es before that row's lf + 1: the joint solves and Elo reach no earlier match; an
                     event's late rounds start after its date). Box rows are Stage 0's has_box rows (a superset of the
                     builders', so the sets are conservative). One tolerance, fixed before it was used: the 21 surface-solver inputs within
                     1e-12 (rounding when players leave the solver's system; C2's evidence), their bit-exact count kept
    G3 direction     the changed box-score inputs move toward the player with less reached evidence: the change's
                     correlation with A's minus B's reached share of box-score evidence (two-week window for the forms,
                     365 days for points_52w) has the sign the level shifts imply (the first run's offsets, 2010-2018).
                     Required where the evidence-weighted shift is 0.05 or more; the rest reported
    G4 dose          monotone in w across the dose arms (--dose; needs SYS_w0, SYS_w50, SYS, SYS_w100): each box-score
                     input's change from SYS_w0 is smaller at w = 0.5 than at w = 1 and in the same direction; SYS's
                     reported. Across arms, so not one arm's READY condition
    G5 leaks         the builders' own probes, run inside the arm's build with the hooks on (Stage 1, Stage 3, Stage 4,
                     Stage B, the offset Elo and the surface switches): no protected match moved
    G6 level         the same-player Challenger minus main-tour gap after translation against B's residual target: phase 2
Run: ./python.sh src/eda/lower_level_evidence/system_gates.py --arm ARM [--sandbox D]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.lower_level_evidence import level_layer as L  # noqa: E402
from src.eda.lower_level_evidence import system_arms as SA  # noqa: E402

ARMS = SA.ARMS
REF_FRAME, REF_INPUTS = LC.FRAME, LC.INPUTS
SIDES = LC.OUT / "composition" / "reference_2026-10-08" / "sides.parquet"
FORMS_OFFSETS = LC.OUT / "candidates" / "offsets" / "forms_offsets.csv"
ID_COLS = ["match_id", "tour", "season", "tournament_date", "p_mkt", "tabpfn_split", "debut_season"]
FORMS = [L.input_name(s, ch) for s, ch in L.FORM_SPECS]
UNTOUCHED = ["odds_logit", "tour", "surface", "level", "indoor", "best_of", "round", "age", "age_sq", "sets_14d",
             "surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b"]
WEEK52 = 364
# G2's one tolerance, fixed before any arm's G2 ran with it: the 21 surface-solver inputs (lane 2) move by rounding alone
# when players with no row before a day leave the solver's system (C2, status 23:07 UTC: the decided solver against
# itself, ITF-only players removed, moves women's holds by 1.6e-15; REF_noITF's hooked solve 4.0e-15 men, 1.8e-15
# women; system/ios_layer/gates/decided_active_set_wta_hold.json). Every other input is compared exactly.
SURFACE_SOLVER = tuple(f"{p}_{s}" for p in ("iosO", "iosD", "prod")
                       for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved"))
SURFACE_TOL = 1e-12
# the inputs each family of the layer can move; a family switched off leaves its inputs exactly the reference's
FAMILY_INPUTS = {"points_52w": ["points_52w"], "forms": [L.input_name(s, ch) for s, ch in L.FORM_SPECS],
                 "ios": list(SURFACE_SOLVER), "ios_points_short": ["ios_points_short"], "ratings_iid": ["ratings_iid"],
                 "elo": ["elo_overall", "elo_surf_offset", "elo_games"]}


def write_json(path: Path, obj) -> None:
    SA.write_json(path, obj)


def inputs_of(path: Path) -> pd.DataFrame:
    """A frame's identifiers and inputs, without the result column."""
    cols = [c for c in pq.read_schema(path).names if c != "a_won"]
    f = pd.read_parquet(path, columns=cols)
    f["match_id"] = f["match_id"].astype(str)
    return f


def labels_through_2024(path: Path) -> pd.Series:
    f = pd.read_parquet(path, columns=["match_id", "season", "a_won"], filters=[("season", "<=", 2024)])
    if len(f) and f["season"].max() > 2024:
        raise RuntimeError("a result after 2024 was read")
    return pd.Series(f["a_won"].to_numpy(), index=f["match_id"].astype(str).to_numpy())


def diff_stats(a, b) -> dict:
    a, b = np.asarray(a, float), np.asarray(b, float)
    same_nan = bool(np.array_equal(np.isnan(a), np.isnan(b)))
    both = np.isfinite(a) & np.isfinite(b)
    gap = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
    changed = int(((a != b) & both).sum() + (np.isnan(a) != np.isnan(b)).sum())
    return {"largest_difference": gap, "same_missing": same_nan, "rows_changed": changed, "rows": int(len(a)),
            "exact": bool(gap == 0.0 and same_nan)}


def input_names(frame: pd.DataFrame) -> list[str]:
    return [c[3:] for c in frame.columns if c.startswith("in_")]


# ------------------------------------------------------------------------------------------------
# G1

def g1(arm: str, ref: pd.DataFrame, cand: pd.DataFrame, cand_path: Path) -> dict:
    out = {"what": "G1: the arm's frame against the frozen reference's, exactly", "rows_reference": int(len(ref)),
           "rows_arm": int(len(cand))}
    out["same_ids_in_order"] = bool(len(ref) == len(cand) and (ref["match_id"].to_numpy()
                                                               == cand["match_id"].to_numpy()).all())
    if not out["same_ids_in_order"]:
        out["pass"] = False
        return out, pd.DataFrame()
    ids = {}
    for c in ID_COLS[1:]:
        x, y = ref[c], cand[c]
        ids[c] = bool(x.equals(y)) if x.dtype == y.dtype else bool((x.astype(str) == y.astype(str)).all())
    la, lb = labels_through_2024(REF_FRAME), labels_through_2024(cand_path)
    ids["a_won_seasons_to_2024"] = bool(la.index.equals(lb.index) and (la.to_numpy() == lb.to_numpy()).all())
    out["identifiers_equal"] = ids
    names = input_names(ref)
    out["same_input_columns"] = names == input_names(cand)
    rows = [{"input": n, **diff_stats(ref[f"in_{n}"], cand[f"in_{n}"])} for n in names]
    t = pd.DataFrame(rows)
    out["inputs"] = int(len(t))
    out["inputs_exact"] = int(t["exact"].sum())
    out["inputs_not_exact"] = t.loc[~t["exact"], ["input", "largest_difference", "rows_changed"]].to_dict("records")
    ri = json.loads(REF_INPUTS.read_text(encoding="utf-8"))
    ci = json.loads((cand_path.parent / "model_inputs.json").read_text(encoding="utf-8"))
    out["model_inputs_names_kinds_equal"] = [(d["name"], d["kind"]) for d in ri["inputs"]] == \
        [(d["name"], d["kind"]) for d in ci["inputs"]]
    out["pass"] = bool(out["same_ids_in_order"] and all(ids.values()) and out["same_input_columns"]
                       and out["inputs_exact"] == 58 and out["model_inputs_names_kinds_equal"])
    return out, t


def constants_gate(arm: str, sandbox: Path | None) -> dict:
    """The builders' tuned constants in the arm's build against the reference build's."""
    rc = json.loads(SA.REF_CONSTANTS.read_text(encoding="utf-8"))
    d = ARMS / arm
    out = {"what": "the tuned constants of the arm's build equal the reference build's"}
    s1p = d / "chain_outputs" / "stage1_baselines_summary.json"
    if s1p.exists():
        out["stage1_chosen_equal"] = json.loads(s1p.read_text(encoding="utf-8"))["chosen"] == rc["stage1_chosen"]
    pmp = d / "chain_outputs" / "surface_elo_pieces_pieces_meta.json"
    if pmp.exists():
        pm = json.loads(pmp.read_text(encoding="utf-8"))
        out["offset_constants_equal"] = pm["offset_constants"] == rc["offset_constants"]
        out["offset_surface_blind_constants_equal"] = (pm["offset_surface_blind_constants"]
                                                       == rc["offset_surface_blind_constants"])
    if sandbox is not None:
        s3 = sandbox / "data" / "studies" / "predictability_diagnostic" / "stage3_ratings_summary.json"
        if s3.exists():
            ch = json.loads(s3.read_text(encoding="utf-8"))["chosen"]
            ref3 = {t: json.loads(v.replace("'", '"')) for t, v in rc["stage3_chosen"].items()}
            out["stage3_chosen_equal"] = {t: {k: float(x) for k, x in ch[t].items()} == {k: float(x) for k, x in
                                                                                          ref3[t].items()}
                                          for t in ch}
        sb = sandbox / "data" / "studies" / "ufc_ideas" / "stageB_adj_summary.json"
        if sb.exists():
            ch = json.loads(sb.read_text(encoding="utf-8"))["chosen"]
            got = {f"{c['tour']}|{c['stat']}": {k: float(c[k]) if k != "tau" else int(c[k])
                                                for k in ("h1", "K1", "tau", "h3", "K3")} for c in ch}
            out["stageB_chosen_equal"] = got == rc["stageB_chosen"]
        calls = d / "layer_calls" / "layer_calls.jsonl"
        if calls.exists():
            pins = [json.loads(x) for x in calls.read_text(encoding="utf-8").splitlines() if '"hook": "pin"' in x]
            if pins:
                out["stageB_tuned_equals_reference_in_this_build"] = pins[-1]["tuned_equals_reference"]
    flat = [v for k, v in out.items() if k.endswith("_equal") and isinstance(v, bool)]
    flat += [x for k, v in out.items() if k.endswith("_equal") and isinstance(v, dict) for x in v.values()]
    out["pass"] = bool(flat and all(flat))
    return out


# ------------------------------------------------------------------------------------------------
# G2: what the arm cannot reach

def reached_levels(cfg: dict) -> tuple[set, list]:
    """The levels whose box rows the arm changes, and its tours."""
    lv = set()
    if cfg["translate"] or cfg["weight"] != 1.0:
        lv |= set(L.LOWER)
    if cfg["itf_box"] == "exclude":
        lv |= set(L.ITF_LEVELS)
    if cfg["weight_results"] != 1.0:
        lv |= set(L.LOWER)
    return lv, list(cfg["tours"])


def box_rows() -> pd.DataFrame:
    """Every player-row of a Stage 0 match with a box score (has_box; completed, standard format): player, tour, day,
    level, opponent."""
    m = LC.load_matches(columns=["match_id", "tour", "tournament_date", "map_level", "status", "format", "has_box",
                                 "player_a_id", "player_b_id"])
    m = m[m["has_box"].astype(bool) & m["status"].eq("completed") & m["format"].eq("standard")]
    a = pd.DataFrame({"player": m["player_a_id"].to_numpy(), "opp": m["player_b_id"].to_numpy()})
    b = pd.DataFrame({"player": m["player_b_id"].to_numpy(), "opp": m["player_a_id"].to_numpy()})
    base = pd.DataFrame({"match_id": m["match_id"].to_numpy(), "tour": m["tour"].to_numpy(),
                         "day": pd.to_datetime(m["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64"),
                         "bucket": m["bucket"].to_numpy()})
    return pd.concat([pd.concat([base, a], axis=1), pd.concat([base, b], axis=1)], ignore_index=True)


def reach_sets(frame: pd.DataFrame, cfg: dict) -> dict:
    """Per frame match: whether the arm can reach its points_52w, its forms, anything at all (by date), for both
    players (A and B from Stage 0)."""
    lv, tours = reached_levels(cfg)
    m = LC.load_matches(columns=["match_id", "player_a_id", "player_b_id"]).set_index("match_id")
    fr = frame[["match_id", "tour", "tournament_date"]].copy()
    fr["day"] = pd.to_datetime(fr["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    fr["a"] = m["player_a_id"].reindex(fr["match_id"]).to_numpy()
    fr["b"] = m["player_b_id"].reindex(fr["match_id"]).to_numpy()
    rows = box_rows()
    rows = rows[rows["tour"].isin(tours)]
    hit = rows[rows["bucket"].isin(lv)]
    first_hit = hit.groupby("player")["day"].min()
    # forms: a row is flagged if it is at a reached level or its opponent held a reached row on or before its day
    rows = rows.assign(opp_first=first_hit.reindex(rows["opp"]).to_numpy())
    flagged = rows[rows["bucket"].isin(lv) | (rows["opp_first"] <= rows["day"])]
    first_flag = flagged.groupby("player")["day"].min()
    hit_days = hit.groupby("player")["day"].apply(lambda s: np.sort(s.to_numpy()))

    def any_hit_in(player, lo, hi):
        d = hit_days.get(player)
        if d is None:
            return False
        i = np.searchsorted(d, lo, side="left")
        return i < len(d) and d[i] <= hi
    in_scope = fr["tour"].isin(tours).to_numpy()
    pts = np.array([any_hit_in(p, d - WEEK52, d) for p, d in zip(fr["a"], fr["day"])]) | \
        np.array([any_hit_in(p, d - WEEK52, d) for p, d in zip(fr["b"], fr["day"])])
    fa = first_flag.reindex(fr["a"]).to_numpy(dtype="float64")
    fb = first_flag.reindex(fr["b"]).to_numpy(dtype="float64")
    forms = (fa <= fr["day"].to_numpy()) | (fb <= fr["day"].to_numpy())
    # "anything": a reached row can move a match through a player's own sequence (ordered by event date) or through a
    # cross-player solve on the match clock (a result counts from lf + 1 and is read at es). An event's late rounds
    # start after its start date, so the event date alone is not conservative (CLAUDE.md: tournament start dates are
    # not match timestamps): a match is unreachable only when both clocks say so. Changed 10 Oct 02:25 UTC after
    # REF_noITF's G2 flagged 7 women's QF-F matches of an event that started 4 days before the first ITF box row's
    tour_first = hit.groupby("tour")["day"].min()
    tf = tour_first.reindex(fr["tour"]).to_numpy(dtype="float64")
    by_event = np.where(np.isnan(tf), False, fr["day"].to_numpy() >= tf)
    tm = pd.read_parquet(LC.TIMING, columns=["match_id", "es", "lf"]).set_index("match_id")
    hit_lf = tm["lf"].reindex(hit["match_id"].to_numpy()).to_numpy(dtype="float64") + 1.0
    if np.isnan(hit_lf).any():
        raise RuntimeError(f"{int(np.isnan(hit_lf).sum())} reached box rows have no lf on the timeline")
    first_count = pd.Series(hit_lf, index=hit["tour"].to_numpy()).groupby(level=0).min()
    fc = first_count.reindex(fr["tour"]).to_numpy(dtype="float64")
    es = tm["es"].reindex(fr["match_id"].to_numpy()).to_numpy(dtype="float64")
    by_clock = np.where(np.isnan(fc), False, ~(es < fc))                  # an unknown es counts as reachable
    anything = by_event | by_clock
    return {"in_scope": in_scope, "points_52w": in_scope & pts, "forms": in_scope & forms,
            "anything": in_scope & anything, "levels": sorted(lv), "tours": tours,
            "tour_first_reached_day": {t: str(np.datetime64(int(v), "D")) for t, v in tour_first.items()},
            "tour_first_reached_count_day": {t: str(np.datetime64(int(v), "D")) for t, v in first_count.items()}}


def g2(arm: str, ref: pd.DataFrame, cand: pd.DataFrame, cfg: dict) -> dict:
    R = reach_sets(ref, cfg)
    names = input_names(ref)
    checks = []

    def check(label, inputs, mask):
        for n in inputs:
            st = diff_stats(ref[f"in_{n}"].to_numpy()[mask], cand[f"in_{n}"].to_numpy()[mask])
            st["bit_exact"] = st["exact"]
            if n in SURFACE_SOLVER:                       # rounding only (SURFACE_TOL above); bit_exact kept
                st["tolerance"] = SURFACE_TOL
                st["exact"] = bool(st["same_missing"] and st["largest_difference"] <= SURFACE_TOL)
            checks.append({"set": label, "input": n, "matches": int(mask.sum()), **st})
    out_scope = ~R["in_scope"]
    check("tours outside the arm: every input", names, out_scope)
    check("untouched inputs, every match", [n for n in UNTOUCHED if n in names], np.ones(len(ref), bool))
    off = [n for f, ins in FAMILY_INPUTS.items() if not cfg["families"][f] for n in ins if n in names]
    if off:
        check("families switched off: their inputs, every match", off, np.ones(len(ref), bool))
    check("before the tour's first reached row: every input", names, R["in_scope"] & ~R["anything"])
    check("points_52w: neither player with a reached box row in 364 days", ["points_52w"],
          R["in_scope"] & ~R["points_52w"])
    check("forms: neither player reached (own rows or opponents' norms)", FORMS, R["in_scope"] & ~R["forms"])
    t = pd.DataFrame(checks)
    fails = t[~t["exact"]]
    moved = {}
    for n in names:
        st = diff_stats(ref[f"in_{n}"].to_numpy()[R["in_scope"]], cand[f"in_{n}"].to_numpy()[R["in_scope"]])
        moved[n] = st["rows_changed"]
    rounding = t[t["exact"] & ~t["bit_exact"]]
    out = {"what": "G2: inputs the arm cannot reach do not move (exact; the 21 surface-solver inputs within "
                   f"{SURFACE_TOL:g}, rounding when players leave the solver's system)", "reached_levels": R["levels"],
           "tours": R["tours"], "tour_first_reached_day": R["tour_first_reached_day"],
           "tour_first_reached_count_day": R["tour_first_reached_count_day"],
           "sets": {s: int(g["matches"].iloc[0]) for s, g in t.groupby("set")},
           "checks": int(len(t)), "checks_bit_exact": int(t["bit_exact"].sum()),
           "within_rounding_tolerance_only": rounding[["set", "input", "rows_changed",
                                                       "largest_difference"]].to_dict("records"),
           "failed": fails[["set", "input", "matches", "rows_changed",
                            "largest_difference"]].to_dict("records"),
           "inputs_moved_in_the_arm's_tours": {k: v for k, v in moved.items() if v},
           "pass": bool(fails.empty)}
    return out, t


# ------------------------------------------------------------------------------------------------
# G3: direction

def side_shares(window: str, levels: list) -> pd.DataFrame:
    cols = [f"box_{window}_{b}" for b in LC.BUCKETS]
    s = pd.read_parquet(SIDES, columns=["match_id", "side"] + cols)
    tot = s[cols].sum(axis=1).to_numpy(float)
    low = s[[f"box_{window}_{b}" for b in levels]].sum(axis=1).to_numpy(float)
    s["share"] = np.where(tot > 0, low / np.where(tot > 0, tot, 1.0), np.nan)
    a = s[s["side"] == "A"].set_index("match_id")
    b = s[s["side"] == "B"].set_index("match_id")
    return pd.DataFrame({"gap": a["share"] - b["share"].reindex(a.index)})


def g3(arm: str, ref: pd.DataFrame, cand: pd.DataFrame, cfg: dict) -> tuple[dict, pd.DataFrame]:
    lv, tours = reached_levels(cfg)
    lv = sorted(lv)
    ids = ref["match_id"].to_numpy()
    tour = ref["tour"].to_numpy()
    sh = {"h2w": side_shares("h2w", lv).reindex(ids)["gap"].to_numpy(float),
          "365d": side_shares("365d", lv).reindex(ids)["gap"].to_numpy(float)}
    offs = pd.read_csv(FORMS_OFFSETS)
    ev = pd.read_parquet(SIDES, columns=["tour"] + [f"box_h2w_{b}" for b in lv])
    wts = {t: {b: float(g[f"box_h2w_{b}"].sum()) for b in lv} for t, g in ev.groupby("tour")}
    rows = []
    for n in ["points_52w"] + FORMS:
        win = "365d" if n == "points_52w" else "h2w"
        d = cand[f"in_{n}"].to_numpy(float) - ref[f"in_{n}"].to_numpy(float)
        for t in tours:
            m = (tour == t) & np.isfinite(d) & np.isfinite(sh[win])
            if m.sum() < 3 or np.std(d[m]) == 0:
                rows.append({"input": n, "tour": t, "matches": int(m.sum()), "changed": int((d[m] != 0).sum()),
                             "correlation": np.nan, "required": False, "sign_as_expected": None})
                continue
            corr = float(np.corrcoef(d[m], sh[win][m])[0, 1])
            if n == "points_52w":
                dbar, expected = np.nan, -1
                required = cfg["weight"] != 1.0 or cfg["translate"]
            else:
                key = [k for k in offs["key"].unique() if L.input_name(k.split("|")[1], k.split("|")[0]) == n][0]
                o = offs[(offs["key"] == key) & (offs["tour"] == t)].set_index("bucket")["value_used"]
                tot = sum(wts[t].values())
                dbar = float(sum(o.get(b, 0.0) * wts[t][b] for b in lv) / tot) if tot > 0 else 0.0
                expected = -int(np.sign(dbar)) if dbar != 0 else 0
                required = abs(dbar) >= 0.05 and (cfg["weight"] != 1.0 or cfg["translate"])
            ok = (np.sign(corr) == expected) if expected != 0 else None
            rows.append({"input": n, "tour": t, "window": win, "matches": int(m.sum()), "changed": int((d[m] != 0).sum()),
                         "correlation": corr, "evidence_weighted_shift": dbar, "expected_sign": expected,
                         "sign_as_expected": ok, "required": bool(required)})
    t3 = pd.DataFrame(rows)
    req = t3[t3["required"]]
    bad = req.loc[~req["sign_as_expected"].fillna(False).astype(bool), ["input", "tour", "correlation"]]
    env = {}
    still = []
    for c in bad.to_dict("records"):
        r = env_rule(cfg, ref, cand, c["input"], c["tour"], lv, sh["h2w"]) if cfg["translate"] else None
        if r is None:
            still.append(c)               # any other G3 failure holds the arm and goes to the lead
        else:
            env[f"{c['input']}|{c['tour']}"] = r      # recorded, never holding the arm (the lead's ruling)
    out = {"what": "G3: the changed box-score inputs against A's minus B's reached share of box-score evidence",
           "reached_levels": lv, "required_cells": int(len(req)),
           "required_as_expected": int(len(req) - len(bad)),
           "failed": still,
           "env_rule": env,
           "note": "expected signs: the first run's level offsets (2010-2018; forms_offsets.csv), weighted by the "
                   "frame's two-week box evidence at the reached levels; points_52w: negative (raw rates are higher "
                   "below the main tour). Not required where the weighted shift is under 0.05 or the arm moves no "
                   "box-score weight (REF-type arms report only). A failed cell of an ENV-class input (A's classes: "
                   "delta only) in a translating arm follows the lead's ruling of 10 Oct (after SYS's form_first_in): "
                   "it passes if its dev seasons' cells follow the sign of B's fitted delta (own rows minus the "
                   "opponents' norm rows) wherever that season's weighted delta shift is 0.05 or more, and is "
                   "otherwise not required; it is recorded (env_rule) and never holds the arm. Any other failed cell "
                   "holds the arm",
           "pass": not still}
    return out, t3


DEV_SEASONS = range(2013, 2025)


def env_rule(cfg: dict, ref: pd.DataFrame, cand: pd.DataFrame, name: str, tour: str, lv: list, share) -> dict | None:
    """The lead's ruling of 10 Oct (SYS's form_first_in): for an ENV-class input (A's class: delta only) of a translating
    arm, G3 follows B's walk-forward parameters, not the first run's static offsets. Per dev season Y (2013-2024; the
    sealed seasons' parameters are not read): the correlation of the input's change with the reached-share gap, and the
    weighted delta shift D_Y = sum over the reached levels of the frame's two-week box evidence of season Y times
    (delta of the player's own statistic minus the signed delta of the opponents' norm view), over that evidence, with
    season Y's parameters (season_used = max(Y, the floor)). Required where |D_Y| >= 0.05, with the sign -sign(D_Y).
    None when the input is not ENV-class on the tour or is no one-step form (the rule does not apply)."""
    if L.classes_table(cfg) is None:
        return None
    row = L.class_row(cfg, name, tour, "input")
    if row is None or str(row["class"]) != "ENV":
        return None
    spec = [(s, ch) for s, ch in L.FORM_SPECS if L.input_name(s, ch) == name]
    if not spec:
        return None
    s, ch = spec[0]
    views = L.form_views(s, ch)
    (own, osign), (nview, nsign) = views["own"], views["norm"]
    t = L.params_table(cfg)
    floor = cfg.get("params_season_floor")
    sides = pd.read_parquet(SIDES, columns=["match_id", "tour"] + [f"box_h2w_{b}" for b in lv])
    seasons = ref.set_index("match_id")["season"]
    sides["season"] = seasons.reindex(sides["match_id"]).to_numpy()
    d = cand[f"in_{name}"].to_numpy(float) - ref[f"in_{name}"].to_numpy(float)
    rows = []
    for y in DEV_SEASONS:
        yu = max(y, floor) if floor is not None else y

        def delta(stat, level):
            # the layer applies delta only at A's delta_levels of the statistic the row is
            if level not in L.delta_levels(cfg, stat, tour, "stat"):
                return 0.0
            key = (yu, tour, stat, level)
            return float(t["delta"].get(key, 0.0)) if key in t.index else 0.0
        ev = sides[(sides["tour"] == tour) & (sides["season"] == y)]
        w = {b: float(ev[f"box_h2w_{b}"].sum()) for b in lv}
        tot = sum(w.values())
        D = (sum(w[b] * (osign * delta(own, b) - nsign * delta(nview, b)) for b in lv) / tot) if tot > 0 else 0.0
        m = (ref["tour"].to_numpy() == tour) & (ref["season"].to_numpy() == y) & np.isfinite(d) & np.isfinite(share)
        corr = float(np.corrcoef(d[m], share[m])[0, 1]) if m.sum() > 3 and np.std(d[m]) > 0 else np.nan
        required = abs(D) >= 0.05
        ok = bool(np.isfinite(corr) and np.sign(corr) == -np.sign(D)) if required else None
        rows.append({"season": y, "weighted_delta_shift": D, "correlation": corr, "required": required,
                     "sign_as_expected": ok})
    req = [r for r in rows if r["required"]]
    against = [r["season"] for r in req if not r["sign_as_expected"]]
    return {"input": name, "tour": tour, "class": "ENV", "own": own, "norm_view": nview, "norm_sign": nsign,
            "seasons": rows, "required_seasons": len(req), "seasons_against": against,
            "verdict": ("not required: no dev season's weighted delta shift reaches 0.05" if not req else
                        "passes: follows B's delta in every required season" if not against else
                        f"not required under the lead's rule: against B's delta in season(s) {against} of "
                        f"{[r['season'] for r in req]}"),
            "pass": not against}


# ------------------------------------------------------------------------------------------------
# G4: dose, across the dose arms (phase 2; inputs only)

DOSE_ARMS = (("SYS_w0", 0.0), ("SYS_w50", 0.5), ("SYS", "fitted"), ("SYS_w100", 1.0))
BOX_INPUTS = (["points_52w", "ratings_iid", "ios_points_short"] + FORMS + list(SURFACE_SOLVER))


def g4(tours=("atp",)) -> tuple[dict, pd.DataFrame]:
    """The box-score inputs' change from SYS_w0 (no lower-level box evidence) must grow with w: per input and tour, the
    mean absolute change at w = 0.5 below that at w = 1, and the two changes positively correlated (one direction, two
    sizes). SYS (fitted w, capped at 1) is reported, not judged: its change sits where its per-cell weights put it.
    Matches where the four arms' values are all finite. A diagnostic across arms, not one arm's READY condition."""
    frames = {}
    for arm, _ in DOSE_ARMS:
        p = ARMS / arm / "model_frame.parquet"
        if not p.exists():
            return {"pass": None, "note": f"{arm} is not built"}, pd.DataFrame()
        frames[arm] = inputs_of(p)
    ids = frames["SYS_w0"]["match_id"].to_numpy()
    if any(not np.array_equal(f["match_id"].to_numpy(), ids) for f in frames.values()):
        raise SystemExit("the dose arms' frames are not in one order")
    tour = frames["SYS_w0"]["tour"].to_numpy()
    rows = []
    for n in BOX_INPUTS:
        v = {a: frames[a][f"in_{n}"].to_numpy(float) for a, _ in DOSE_ARMS}
        for t in tours:
            m = (tour == t) & np.logical_and.reduce([np.isfinite(x) for x in v.values()])
            d50, d100, dsys = (v[a][m] - v["SYS_w0"][m] for a in ("SYS_w50", "SYS_w100", "SYS"))
            a50, a100, asys = (float(np.mean(np.abs(d))) if m.any() else 0.0 for d in (d50, d100, dsys))
            moved = a100 > 0
            corr = float(np.corrcoef(d50, d100)[0, 1]) if moved and np.std(d50) > 0 else np.nan
            rows.append({"input": n, "tour": t, "matches": int(m.sum()), "mean_abs_change_w50": a50,
                         "mean_abs_change_w100": a100, "mean_abs_change_SYS": asys,
                         "SYS_over_w100": asys / a100 if moved else np.nan, "corr_w50_w100": corr,
                         "monotone": bool(a50 < a100) if moved else None,
                         "one_direction": bool(corr > 0) if moved and np.isfinite(corr) else None})
    t4 = pd.DataFrame(rows)
    judged = t4[t4["monotone"].notna()]
    ok = judged["monotone"].astype(bool) & judged["one_direction"].fillna(False).astype(bool)
    out = {"what": "G4: the box-score inputs' change from SYS_w0 grows with w (w = 0.5 below w = 1, same direction)",
           "inputs_judged": int(len(judged)), "inputs_passing": int(ok.sum()),
           "failed": judged.loc[~ok, ["input", "tour", "mean_abs_change_w50", "mean_abs_change_w100",
                                      "corr_w50_w100"]].to_dict("records"),
           "pass": bool(ok.all()) if len(judged) else None}
    return out, t4


# ------------------------------------------------------------------------------------------------
# G5: the builders' own probes, inside the arm's build

def g5(arm: str, sandbox: Path | None) -> dict:
    out = {"what": "G5: the builders' own leak probes in the arm's build, hooks on: no protected match moved"}
    if sandbox is None:
        out["pass"] = None
        out["note"] = "no sandbox given"
        return out
    pd_ = sandbox / "data" / "studies" / "predictability_diagnostic"
    res = {}
    s1 = json.loads((pd_ / "stage1_baselines_summary.json").read_text(encoding="utf-8"))["probe_by_round"]
    res["stage1_elo"] = {k: v["protected_matches_changed"] for k, v in s1.items()}
    s3 = json.loads((pd_ / "stage3_ratings_summary.json").read_text(encoding="utf-8"))["probe_by_round"]
    res["stage3_ratings"] = {k: v["protected_matches_changed"] for k, v in s3.items()}
    s4 = json.loads((pd_ / "stage4_features_summary.json").read_text(encoding="utf-8"))["probe"]
    res["stage4_features"] = {k: v["protected_changed"] for k, v in s4["variants"].items()}
    res["stage4_control_caught"] = {k: v["control_protected_changed"] for k, v in s4["variants"].items()}
    sb = json.loads((sandbox / "data" / "studies" / "ufc_ideas" / "stageB_adj_summary.json").read_text(
        encoding="utf-8"))["probe"]
    res["stageB_adjperf"] = sb["protected_changed"]
    res["stageB_control_caught"] = sb["control_protected_changed"]
    pm = json.loads((sandbox / "data" / "studies" / "surface_elo_pieces" / "pieces_meta.json").read_text(
        encoding="utf-8"))
    res["offset_elo"] = {t: {k: v["protected_matches_changed"] for k, v in d.items()}
                         for t, d in pm["elo_probes"].items()}
    res["surface_switch"] = pm["leak_probe_surface_switch"]["protected_moved_total"]
    out["probes"] = res
    vals = (list(res["stage1_elo"].values()) + list(res["stage3_ratings"].values())
            + list(res["stage4_features"].values()) + [res["stageB_adjperf"], res["surface_switch"]]
            + [x for d in res["offset_elo"].values() for x in d.values()])
    controls = list(res["stage4_control_caught"].values()) + [res["stageB_control_caught"]]
    out["protected_moved_total"] = int(sum(vals))
    out["controls_caught"] = bool(all(c > 0 for c in controls))
    out["pass"] = bool(out["protected_moved_total"] == 0 and out["controls_caught"])
    return out


# ------------------------------------------------------------------------------------------------
# For role D: which tour-seasons the arm changes (inputs only; no result read)

def season_profile(ref: pd.DataFrame, cand: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """Per tour and season: matches with any of the 58 inputs changed (difference or missingness), and per input the
    matches changed. Tells D whether an arm's early seasons equal the reference's (so its 2019-2024 fits can be the
    reference's)."""
    names = input_names(ref)
    changed = np.zeros(len(ref), bool)
    per = {}
    for n in names:
        a, b = ref[f"in_{n}"].to_numpy(float), cand[f"in_{n}"].to_numpy(float)
        ch = (np.isnan(a) != np.isnan(b)) | (np.isfinite(a) & np.isfinite(b) & (a != b))
        per[n] = ch
        changed |= ch
    key = ref[["tour", "season"]].astype({"season": int})
    rows = []
    for (t, s), g in key.groupby(["tour", "season"]):
        idx = g.index.to_numpy()
        rows.append({"tour": t, "season": int(s), "matches": int(len(idx)), "matches_changed": int(changed[idx].sum()),
                     "inputs_changed": int(sum(per[n][idx].any() for n in names))})
    t = pd.DataFrame(rows)
    early = t[t["season"] <= 2024]
    out = {"matches_changed": int(changed.sum()),
           "every_input_to_2024_equal": {tt: bool(g["matches_changed"].sum() == 0) for tt, g in early.groupby("tour")},
           "first_changed_season": {tt: (int(g.loc[g["matches_changed"] > 0, "season"].min())
                                         if (g["matches_changed"] > 0).any() else None) for tt, g in t.groupby("tour")}}
    return out, t


C2_INPUTS = LC.OUT / "system" / "ios_layer" / "inputs"
C2_NAMES = {"IDENTITY": "IDENTITY_m1", "IDENTITY_ALL": "IDENTITY_m1",   # C2's identity build: the reference's 22
            "SYS_BOTH": "SYS_BOTH_cap"}       # C2, status 01:51 UTC: SYS_BOTH's config, the cap and the form-(b) fix
# the layer version a C2 build used, where its record does not name it (C2's status line names it)
C2_KNOWN_LAYER = {"SYS_BOTH_cap": "26e21291822f42e4c9e7771f518149d1cb85116bdeb5196285fa22eeca37411f"}


def c2_end_to_end(arm: str, cand: pd.DataFrame) -> dict:
    """The arm's 22 IOS-family inputs against C2's own build of the same IOS fingerprint (system/ios_layer/inputs/
    <ARM>.parquet), bit for bit: C2's offer of an end-to-end check (READY_ios_hooks.txt)."""
    p = C2_INPUTS / f"{C2_NAMES.get(arm, arm)}.parquet"
    if not p.exists():
        return {"checked": False, "note": f"{p} does not exist"}
    # C2's fingerprint names neither level_layer.py's version nor the cap (C2, status 00:50 UTC): a fitted-w arm is
    # compared only with a C2 build that names the same layer version as this arm's build
    cfg = L.load_config(ARMS / arm / "layer_config.json")
    meta = json.loads(p.with_suffix(".json").read_text(encoding="utf-8")) if p.with_suffix(".json").exists() else {}
    # the same IOS fingerprint (C2's: what the IOS outputs depend on), when C2's record names it
    c2 = SA.SB.c2_module()
    want_fp = ((meta.get("consistency") or {}).get("want") or {}).get("ios_part")
    mine_fp = c2.fingerprint(cfg) if c2 is not None else None
    if want_fp and mine_fp and want_fp != mine_fp and p.stem != "IDENTITY_m1":   # the identity file: the reference's
        return {"checked": False, "note": f"{p.name} has IOS fingerprint {want_fp[:12]}, this arm {mine_fp[:12]}: not "
                                          "comparable"}
    if cfg["weight"] == "fitted":
        runs = json.loads((ARMS / arm / "build.json").read_text(encoding="utf-8"))["runs"]
        mine = runs[-1].get("level_layer_sha256_in_sandbox") or runs[-1].get("level_layer_sha256")
        theirs = meta.get("level_layer_sha256") or C2_KNOWN_LAYER.get(p.stem)
        if theirs != mine:
            return {"checked": False, "note": f"{p.name} does not name this build's level_layer.py ({mine[:12]}); with "
                                              "fitted w the cap changes the solves, so the files are not comparable"}
    c = pd.read_parquet(p)
    c["match_id"] = c["match_id"].astype(str)
    c = c.set_index("match_id").reindex(cand["match_id"].to_numpy())
    cols = [x for x in c.columns if x.startswith("in_")]
    rows = {x[3:]: diff_stats(c[x].to_numpy(float), cand[x].to_numpy(float)) for x in cols}
    return {"checked": True, "file": str(p), "inputs": len(cols),
            "exact": int(sum(v["exact"] for v in rows.values())),
            "not_exact": {k: v for k, v in rows.items() if not v["exact"]}, "pass": all(v["exact"] for v in rows.values())}


def ready(arm: str) -> int:
    """READY.txt for role D, written only when every gate of the arm passed."""
    d = ARMS / arm
    s = json.loads((d / "gates" / "summary.json").read_text(encoding="utf-8"))
    if arm.startswith("IDENTITY"):
        ok = all(s.get(k) is True for k in ("G1", "constants", "G5_builder_probes"))
        SA.status_line(f"{arm} gates: G1 {s.get('G1')}, constants {s.get('constants')}, builder probes "
                       f"{s.get('G5_builder_probes')} (arms/{arm}/gates/); no READY.txt: the identity arm is the "
                       "reference and is not for fitting")
        print(f"{arm}: identity arm, no READY.txt (gates pass: {ok})")
        return 0 if ok else 1
    need = (["identifiers", "untouched", "lane0_check", "constants", "G5_builder_probes"]
            if arm in SA.PHASE3 + SA.NEW_PRE else ["G2", "G3", "constants", "G5_builder_probes"])
    if s.get("C2_end_to_end") != "not available":
        need.append("C2_end_to_end")
    failed = [k for k in need if s.get(k) is not True]
    waived = []
    wp = d / "gates" / "waivers.json"
    if failed == ["G3"] and wp.exists():
        # a G3 cell the lead ruled on (arms/<ARM>/gates/waivers.json: the cells, the ruling's status-log time): READY
        # only when every failed required cell is one of the ruled cells
        w = json.loads(wp.read_text(encoding="utf-8"))
        ruled = {(c["input"], c["tour"]) for c in w["cells"]}
        cells = json.loads((d / "gates" / "g3_direction.json").read_text(encoding="utf-8"))["failed"]
        if cells and all((c["input"], c["tour"]) in ruled for c in cells):
            waived = [f"G3 {c['input']} {c['tour']} (corr {c['correlation']:+.3f}; the lead's ruling {w['ruling']})"
                      for c in cells]
            failed = []
    if failed:
        print(f"{arm}: not READY, gates not passed: {failed}")
        return 1
    if arm in SA.GATED:
        # addition 3, section 5: no SYS-family arm is READY before IDENTITY_ALL passes G1 with the frozen modules
        ia = ARMS / "IDENTITY_ALL" / "gates" / "summary.json"
        si = json.loads(ia.read_text(encoding="utf-8")) if ia.exists() else {}
        if not (si.get("G1") is True and si.get("constants") is True):
            print(f"{arm}: gates pass, but not READY: IDENTITY_ALL has not passed G1 (pre-registration addition 3, §5)")
            return 1
        need.append("IDENTITY_ALL G1")
    g3p = d / "gates" / "g3_direction.json"
    env = json.loads(g3p.read_text(encoding="utf-8")).get("env_rule", {}) if g3p.exists() else {}
    if env:
        waived += [f"G3 {k.replace('|', ' ')} judged by the lead's ENV rule: {v['verdict']}" for k, v in env.items()]
    prof = s.get("season_profile", {})
    lines = [f"READY: arm {arm} (role C1), {SA.now()}",
             f"frame       {d / 'model_frame.parquet'}  sha256 {SA.sha256(d / 'model_frame.parquet')}",
             f"inputs      {d / 'model_inputs.json'}",
             f"config      {d / 'layer_config.json'}  sha256 {s['config_sha256']}",
             f"gates       {d / 'gates'} : " + ", ".join(f"{k} pass" for k in need)
             + (f"; G3 with ruled exceptions: {'; '.join(waived)}" if waived else ""),
             f"changed     {prof.get('matches_changed')} matches; every input to 2024 equal to the reference's: "
             f"{prof.get('every_input_to_2024_equal')}; first changed season {prof.get('first_changed_season')}",
             "the result column is the reference's (checked through 2024 by a filtered read for the identity arms; "
             "the frame's a_won is copied by the chain, never read here)"]
    (d / "READY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    SA.status_line(f"READY {arm}: gates {', '.join(need)} pass"
                   + (f" (G3 with ruled exceptions: {'; '.join(waived)})" if waived else "")
                   + f"; {prof.get('matches_changed')} matches changed; "
                   f"inputs to 2024 equal {prof.get('every_input_to_2024_equal')} (arms/{arm}/READY.txt)")
    print("\n".join(lines))
    return 0


# ------------------------------------------------------------------------------------------------

def run(arm: str, sandbox: str | None) -> int:
    d = ARMS / arm
    cand_path = d / "model_frame.parquet"
    if not cand_path.exists():
        raise SystemExit(f"{cand_path} does not exist: the arm is not built")
    cfg = L.load_config(d / "layer_config.json")
    sb = Path(sandbox) if sandbox else None
    gdir = d / "gates"
    gdir.mkdir(parents=True, exist_ok=True)
    ref, cand = inputs_of(REF_FRAME), inputs_of(cand_path)
    summary = {"arm": arm, "frame_sha256": SA.sha256(cand_path), "config_sha256": SA.sha256(d / "layer_config.json"),
               "checked_at": SA.now()}
    if (d / "build.json").exists():
        # which code built it and where lane 2's runs went (C2's caution: a lane-2 folder serves one arm name once)
        last = json.loads((d / "build.json").read_text(encoding="utf-8"))["runs"][-1]
        summary["build"] = {k: last.get(k) for k in ("sandbox", "level_layer_sha256_in_sandbox",
                                                    "level_layer_ios_sha256_in_sandbox", "lane2_runs_dir",
                                                    "started_at", "finished_at")}
    if arm.startswith("IDENTITY"):
        r1, t1 = g1(arm, ref, cand, cand_path)
        t1.to_csv(gdir / "g1_inputs.csv", index=False)
        write_json(gdir / "g1_identity.json", r1)
        summary["G1"] = r1["pass"]
        rc = constants_gate(arm, sb)
        write_json(gdir / "constants.json", rc)
        summary["constants"] = rc["pass"]
        print("G1", {k: r1[k] for k in ("pass", "inputs_exact", "inputs_not_exact", "identifiers_equal")})
        print("constants", rc)
    elif arm in SA.PHASE3 + SA.NEW_PRE:
        # a NEW arm (addition 3 section 4): new data, not the layer, moves its inputs, so G2 and G3 (which read the
        # frozen Stage 0's reach) do not apply. Checked: the same frame matches, identifiers and results through 2024;
        # the inputs no Stage 0 row feeds exactly the reference's; the constants pinned; F's lane-0 check passed
        same = bool(len(ref) == len(cand) and (ref["match_id"].to_numpy() == cand["match_id"].to_numpy()).all())
        if not same:
            raise SystemExit("the arm's frame is not in the reference's order")
        ids = {c: bool(ref[c].equals(cand[c])) if ref[c].dtype == cand[c].dtype
               else bool((ref[c].astype(str) == cand[c].astype(str)).all()) for c in ID_COLS[1:]}
        la, lb = labels_through_2024(REF_FRAME), labels_through_2024(cand_path)
        ids["a_won_seasons_to_2024"] = bool(la.index.equals(lb.index) and (la.to_numpy() == lb.to_numpy()).all())
        summary["identifiers_equal"] = ids
        # debut_season (a player's first season in Stage 0) is derived from the history the candidate extends: an
        # earlier added match can end a debut. Reported, not required (10 Oct, NEW_ASIS: 10 of 67,226 matches)
        dd = ref["debut_season"].astype(str).to_numpy() != cand["debut_season"].astype(str).to_numpy()
        summary["debut_season_changed_matches"] = int(dd.sum())
        summary["identifiers"] = bool(all(v for k, v in ids.items() if k != "debut_season"))
        fixed = ["odds_logit", "tour", "surface", "level", "indoor", "best_of", "round", "age", "age_sq"]
        rows = [{"input": n, **diff_stats(ref[f"in_{n}"], cand[f"in_{n}"])} for n in fixed]
        write_json(gdir / "untouched_inputs.json", rows)
        summary["untouched"] = bool(all(r["exact"] for r in rows))
        l0 = d / "lane0_check.json"
        summary["lane0_check"] = bool(json.loads(l0.read_text(encoding="utf-8")).get("pass")) if l0.exists() else False
        rc = constants_gate(arm, sb)
        write_json(gdir / "constants.json", rc)
        summary["constants"] = rc["pass"]
        print("NEW arm", {k: summary[k] for k in ("identifiers", "untouched", "lane0_check", "constants")})
    else:
        same = bool(len(ref) == len(cand) and (ref["match_id"].to_numpy() == cand["match_id"].to_numpy()).all())
        summary["same_matches_in_order"] = same
        if not same:
            raise SystemExit("the arm's frame is not in the reference's order")
        ids = {c: bool(ref[c].equals(cand[c])) if ref[c].dtype == cand[c].dtype
               else bool((ref[c].astype(str) == cand[c].astype(str)).all()) for c in ID_COLS[1:]}
        la, lb = labels_through_2024(REF_FRAME), labels_through_2024(cand_path)
        ids["a_won_seasons_to_2024"] = bool(la.index.equals(lb.index) and (la.to_numpy() == lb.to_numpy()).all())
        summary["identifiers_equal"] = ids
        if not all(ids.values()):
            raise SystemExit(f"the arm's identifiers or results differ from the reference's: {ids}")
        r2, t2 = g2(arm, ref, cand, cfg)
        t2.to_csv(gdir / "g2_invariance.csv", index=False)
        write_json(gdir / "g2_invariance.json", r2)
        summary["G2"] = r2["pass"]
        print("G2", {k: r2[k] for k in ("pass", "sets", "failed")})
        r3, t3 = g3(arm, ref, cand, cfg)
        t3.to_csv(gdir / "g3_direction.csv", index=False)
        write_json(gdir / "g3_direction.json", r3)
        summary["G3"] = r3["pass"]
        print("G3", {k: r3[k] for k in ("pass", "required_cells", "required_as_expected", "failed")})
        rc = constants_gate(arm, sb)
        write_json(gdir / "constants.json", rc)
        summary["constants"] = rc["pass"]
    prof, tprof = season_profile(ref, cand)
    tprof.to_csv(gdir / "season_profile.csv", index=False)
    summary["season_profile"] = prof
    print("season profile", prof)
    e2e = c2_end_to_end(arm, cand)
    write_json(gdir / "c2_end_to_end.json", e2e)
    summary["C2_end_to_end"] = e2e.get("pass") if e2e.get("checked") else "not available"
    print("C2 end to end", {k: v for k, v in e2e.items() if k != "not_exact"})
    r5 = g5(arm, sb)
    write_json(gdir / "g5_builder_probes.json", r5)
    summary["G5_builder_probes"] = r5["pass"]
    summary["G4"] = "phase 2 (the dose arms)"
    summary["G6"] = "phase 2 (B's residual target)"
    print("G5", r5)
    write_json(gdir / "summary.json", summary)
    print(json.dumps(summary, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm")
    ap.add_argument("--sandbox")
    ap.add_argument("--ready", action="store_true", help="write READY.txt if every gate of the arm passed")
    ap.add_argument("--dose", action="store_true", help="G4 across SYS_w0, SYS_w50, SYS and SYS_w100")
    a = ap.parse_args()
    if a.dose:
        r4, t4 = g4()
        d = ARMS / "g4"
        d.mkdir(parents=True, exist_ok=True)
        t4.to_csv(d / "g4_dose.csv", index=False)
        write_json(d / "g4_dose.json", r4)
        print(json.dumps(r4, indent=1, default=str))
        return 0
    if not a.arm:
        raise SystemExit("--arm is required")
    if a.ready:
        return ready(a.arm)
    return run(a.arm, a.sandbox)


if __name__ == "__main__":
    sys.exit(main())
