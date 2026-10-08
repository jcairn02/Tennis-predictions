"""The Stage 3 write-up's tables, generated from the stage's output files, so that the write-up quotes only computed
numbers.

Run:  ./python.sh src/eda/shot_level/stage3_tables.py
Writes data/studies/shot_level/stage3_tables.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level.stage2_tables import MEM, STAT_WORDS, f2, interval  # noqa: E402

TOUR = {"atp": "Men", "wta": "Women"}
UNITS = {"srv_quick": "serve points in play", "ret_quick": "return points in play", "rally9": "points of 9+ shots",
         "winner_rate": "classified points", "error_rate": "classified points", "spd1": "first serves in, timed",
         "net_won": "net points", "consolidate": "games right after breaking"}
PROFILE_WORDS = {"box score (Stage D)": "Box-score profile (Stage D, the control)", "core_off": "Core, own",
                 "core_adj": "Core, opponent-adjusted", "core_def": "Core, conceded", "speed": "Serve speed",
                 "sequence": "Point sequence", "style": "Style", "all_off": "Everything, own"}
REJECT_Z = 1.645            # one-sided 95%: a planted edge is ruled out when the real gain lies this many sds below


def points_tables() -> str:
    r = json.loads((S.OUT / "stage3_points.json").read_text(encoding="utf-8"))
    P, M = r["points"], r["match"]
    out = ["**Serve points.** Gain per serve point, milli-log-loss (95% range, clustered by calendar week), on the "
           "evaluation matches; the model fitted walk-forward by season.", "",
           "| Tour | Comparison | 2014–2026 | 2019–2026 | 2022–2026 | Serve points, 2014–2026 |", "|---|---|---:|---:|---:|---:|"]
    for t in ("atp", "wta"):
        for key, words in (("M2-M1", "Box-score form over the ratings"), ("M3-M1", "Shot features over the ratings"),
                           ("M4-M2", "Shot features over the ratings and box-score form")):
            cells = [interval(P[f"{t}|{key}|{w}"]["gain_per_point_milli"], P[f"{t}|{key}|{w}"]["lo"],
                              P[f"{t}|{key}|{w}"]["hi"], 3) for w in ("all", "2019_26", "2022_26")]
            out.append(f"| {TOUR[t]} | {words} | " + " | ".join(cells) + f" | {P[f'{t}|{key}|all']['serve_points']:,} |")
    out += ["", "**From points to matches.** Each model's two serve forecasts turned into a match forecast by the earlier "
            "study's iid model; milli-log-loss per match (95% range, clustered by week).", "",
            "| Tour | Shot-informed over box-score point model, all matches | The same, matches with odds | "
            "Shot information as a feature given the odds | Given Elo |", "|---|---:|---:|---:|---:|"]
    for t in ("atp", "wta"):
        cells = []
        for k in ("iid M4 over iid M2|all matches", "iid M4 over iid M2|matches with odds",
                  "point-model increment given odds", "point-model increment given elo"):
            v = M[f"{t}|{k}"]
            cells.append(f"{interval(v['gain_milli'], v['lo'], v['hi'])} on {v['n']:,}")
        out.append(f"| {TOUR[t]} | " + " | ".join(cells) + " |")
    out += ["", "Spread of the shot features' adjustment to the serve forecast (standard deviation of M4 − M2, log-odds): "
            + ", ".join(f"{TOUR[t].lower()} {P[f'{t}|spread_M4_vs_M2_logit_sd']:.3f}" for t in ("atp", "wta")) + "."]
    return "\n".join(out)


def split_tables() -> str:
    r = json.loads((S.OUT / "stage3_points_split.json").read_text(encoding="utf-8"))
    P, M = r["points"], r["match"]
    n_r, n_s = len(r["inputs"]["rally"]), len(r["inputs"]["serve"])
    words = {"M4": f"Both ({n_r + n_s} inputs)",
             "M4r": f"Rally only ({n_r}: rally length, returns in play, how points end, net play, return depth)",
             "M4s": f"Serve only ({n_s}: first- and second-serve speed, placement)"}
    out = ["**The serve's own attributes against the rally's** (`stage3_points_split.json`). Over the ratings and "
           "box-score form: milli-log-loss per serve point, higher is better. Then each model's match forecast as a "
           "feature given the closing odds: milli-log-loss per match, higher is better. 95% ranges clustered by week; a "
           "range spanning zero is a tie.", "",
           "| Tour | Inputs added | Serve points, 2014–2026 | Serve points, 2022–2026 | Matches given the odds, 2014–2026 "
           "| Matches given the odds, 2022–2026 |", "|---|---|---:|---:|---:|---:|"]
    for t in ("atp", "wta"):
        for m in ("M4", "M4r", "M4s"):
            cells = [interval(P[f"{t}|{m}-M2|{w}"]["gain_per_point_milli"], P[f"{t}|{m}-M2|{w}"]["lo"],
                              P[f"{t}|{m}-M2|{w}"]["hi"], 4) for w in ("all", "2022_26")]
            cells += [interval(M[f"{t}|{m} given the odds|{w}"]["gain_milli"], M[f"{t}|{m} given the odds|{w}"]["lo"],
                               M[f"{t}|{m} given the odds|{w}"]["hi"], 3) for w in ("all", "2022_26")]
            out.append(f"| {TOUR[t]} | {words[m]} | " + " | ".join(cells) + " |")
    s = pd.DataFrame(r["seasons"])
    s = s[(s["tour"] == "atp") & (s["comparison"] == "M4r-M2")].sort_values("season")
    out += ["", "Men, rally inputs only, per serve point by season: " + ", ".join(
        f"{int(x.season)} {x.gain_per_point_milli:+.3f}" for x in s.itertuples()) + "."]
    return "\n".join(out)


def flexible_tables() -> str:
    r = json.loads((S.OUT / "stage3_flexible.json").read_text(encoding="utf-8"))
    out = ["**Over the recalibrated closing odds**, 2022–2026, milli-log-loss (95% range from four-week blocks):", "",
           "| Tour | Learner | Learner on the odds alone | Shot | Box score | Box score + shot | Box score + shot, over box score |",
           "|---|---|---:|---:|---:|---:|---:|"]
    learners = (("ridge", "_diff", "Ridge logistic, A − B differences"), ("gbm", "", "Gradient boosting, both players' values"),
                ("gbm_mono", "", "Gradient boosting, rising with the odds"))
    for t in ("atp", "wta"):
        R = r["results"][t]
        for m, sfx, words in learners:
            def cell(key):
                v = R.get(key)
                return interval(v["gain"], v["lo"], v["hi"]) if v else "–"
            out.append(f"| {TOUR[t]} | {words} | {cell(f'{m}|odds')} | {cell(f'{m}|shot{sfx}')} | {cell(f'{m}|box{sfx}')} | "
                       f"{cell(f'{m}|box+shot{sfx}')} | {cell(f'{m}|box+shot{sfx}|over_box_alone')} |")
    out += ["", "**Boosting over the same learner on the odds alone** (what the inputs add inside one learner):", "",
            "| Tour | Learner | Shot | Box score | Box score + shot |", "|---|---|---:|---:|---:|"]
    for t in ("atp", "wta"):
        R = r["results"][t]
        for m, _, words in learners[1:]:
            cells = [interval(R[f"{m}|{k}|over_same_learner_on_odds"]["gain"], R[f"{m}|{k}|over_same_learner_on_odds"]["lo"],
                              R[f"{m}|{k}|over_same_learner_on_odds"]["hi"]) for k in ("shot", "box", "box+shot")]
            out.append(f"| {TOUR[t]} | {words} | " + " | ".join(cells) + " |")
    out += ["", "Ridge penalties chosen on 2021 (C, smaller is stronger; grid "
            f"{min(r['design']['ridge_C']):g} to {max(r['design']['ridge_C']):g}): " + "; ".join(
                f"{TOUR[t].lower()} shot {r['results'][t]['ridge|shot_diff']['capacity']:g}, box "
                f"{r['results'][t]['ridge|box_diff']['capacity']:g}, box + shot {r['results'][t]['ridge|box+shot_diff']['capacity']:g}"
                for t in ("atp", "wta")) + ". Test matches: " + ", ".join(
                f"{TOUR[t].lower()} {r['results'][t]['matches_test']:,} (fitted on {r['results'][t]['matches_train']:,})"
                for t in ("atp", "wta")) + "."]
    out += ["", "Smallest gain this test detects with 80% power (Stage 0's formula, `common.mde_milli`): " + "; ".join(
        f"{TOUR[t].lower()} {float(S.mde_milli(r['results'][t]['matches_test'])):.2f} by the formula alone, "
        f"{float(S.mde_milli(r['results'][t]['matches_test'], inflation=1.46)):.2f} with Stage 0's multi-input inflation (× 1.46)"
        for t in ("atp", "wta")) + "."]
    return "\n".join(out)


def profile_tables() -> str:
    p = pd.read_csv(S.OUT / "stage3_profiles.csv")
    rank = pd.read_csv(S.OUT / "stage2_ranking.csv")
    band = {(r.tour, r.id.removeprefix("profile_"), r.form): r.market_band_mean for r in rank.itertuples()
            if r.id.startswith("profile_")}
    out = []
    for t in ("atp", "wta"):
        out += [f"**{TOUR[t]}.** Milli-log-loss over the base (95% range, clustered by week), evaluation matches 2013–2026 "
                "unless marked.", "",
                "| Profile | Memory | Inputs | Shuffled copies' average, given the odds (Stage 2) | Given the odds, harness's fit "
                "| Given the odds, ridge | Given the odds, ridge, 2022–2026 | Given the odds + box score, ridge | Given Elo, ridge |",
                "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        g = p[p["tour"] == t]
        order = list(dict.fromkeys(g["profile"] + "|" + g["form"]))
        for key in order:
            prof, form = key.split("|")
            h = g[(g["profile"] == prof) & (g["form"] == form)].set_index(["base", "method"])

            def c(base, method, w="all"):
                if (base, method) not in h.index:
                    return "–"
                r = h.loc[(base, method)]
                return f"{interval(r[f'gain_{w}'], r[f'lo_{w}'], r[f'hi_{w}'])}"
            b = band.get((t, prof, form))
            mem = MEM.get(form, form)
            out.append(f"| {PROFILE_WORDS.get(prof, prof)} | {mem} | {int(h['inputs'].iloc[0])} | {f2(b)} | "
                       f"{c('market', 'harness')} | {c('market', 'ridge')} | {c('market', 'ridge', '2022_26')} | "
                       f"{c('market+box', 'ridge')} | {c('elo', 'ridge')} |")
        out.append("")
    return "\n".join(out)


def planted_tables() -> str:
    pl = pd.read_csv(S.OUT / "stage3_planted.csv")
    rank = pd.read_csv(S.OUT / "stage2_ranking.csv").set_index(["tour", "id", "form"])
    prof = pd.read_csv(S.OUT / "stage3_profiles.csv").set_index(["tour", "profile", "form", "base", "method"])
    feats = pd.read_parquet(S.OUT / "stage2_features.parquet", columns=["tour", "evaluation", "p_mkt"])
    out = ["**What a planted gain means.** Root-mean-square gap between the true probability and the closing price on "
           "the evaluation matches with odds:", "", "| Tour | " + " | ".join(f"G = {g:g}" for g in (0.25, 0.5, 1, 2)) + " |",
           "|---|" + "---:|" * 4]
    for t in ("atp", "wta"):
        q = feats.loc[feats["tour"].eq(t) & feats["evaluation"].astype(bool), "p_mkt"].dropna().to_numpy()
        w = q * (1 - q)
        out.append(f"| {TOUR[t]} | " + " | ".join(f"{100 * np.sqrt((w ** 2).mean() / w.mean() * 2 * g / 1000):.1f} pp"
                                                  for g in (0.25, 0.5, 1, 2)) + " |")
    pl["label"] = pl["statistic"].map(lambda s: STAT_WORDS.get(s, s))
    for truth, words in (("career", "career"), ("season", "same-season")):
        out += ["", f"**Planted in the {words} value.** Partial correlation squared of the Stage 2 feature with the truth "
                "(given the odds); the feature's gain as a share of the oracle's (recovery, at G = 2); how often a 95% "
                "interval lies above zero, the feature (the oracle), out of 10 draws.", "",
                "| Tour | Statistic | Memory | Fit | Matches | Corr² | Recovery at G = 2 | Gain with no edge | "
                "Detected, G = 0.5 | G = 1 | G = 2 |", "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for t in ("atp", "wta"):
            g = pl[(pl["tour"] == t) & (pl["truth"] == truth)]
            for (stat, form, method), h in g.groupby(["statistic", "form", "method"], sort=False):
                h = h.set_index("planted_gain")
                det = [f"{h.loc[G, 'detected_share']:.0%} ({h.loc[G, 'oracle_detected_share']:.0%})" for G in (0.5, 1.0, 2.0)]
                out.append(f"| {TOUR[t]} | {STAT_WORDS.get(stat, stat)} | {MEM[form]} | {method} | {int(h['matches'].iloc[0]):,} | "
                           f"{h['partial_corr_sq'].iloc[0]:.2f} | {h.loc[2.0, 'recovery']:.2f} | {h.loc[0.0, 'feature_gain']:+.2f} | "
                           + " | ".join(det) + " |")
    # what the real results rule out
    out += ["", "**What the real results rule out** (career value). The real gain of the same feature on the odds (Stage 2's "
            "harness; for the profile also the ridge fit), against the gains the same pipeline produced with a planted "
            f"edge: the smallest planted G whose feature gains lie {REJECT_Z} standard deviations or more above the real gain.", "",
            "| Tour | Statistic | Memory | Fit | Real gain on the odds | Planted G = 0.5: feature gain (sd) | G = 1 | G = 2 | "
            "Smallest planted G ruled out |", "|---|---|---|---|---:|---:|---:|---:|---:|"]
    for t in ("atp", "wta"):
        g = pl[(pl["tour"] == t) & (pl["truth"] == "career")]
        for (stat, form, method), h in g.groupby(["statistic", "form", "method"], sort=False):
            h = h.set_index("planted_gain")
            if stat == "core profile":
                real = prof.loc[(t, "core_off", form, "market", method), "gain_all"]
            else:
                real = rank.loc[(t, f"{stat}|off", form), "market_imp"]
            grid = (0.25, 0.5, 1.0, 2.0)
            out_of = [h.loc[G, "feature_gain"] - REJECT_Z * h.loc[G, "feature_gain_sd"] > real for G in grid]
            # the smallest planted G from which every larger one is ruled out too
            ruled = [G for i, G in enumerate(grid) if all(out_of[i:])]
            cells = [f"{h.loc[G, 'feature_gain']:+.2f} ({h.loc[G, 'feature_gain_sd']:.2f})" for G in (0.5, 1.0, 2.0)]
            out.append(f"| {TOUR[t]} | {STAT_WORDS.get(stat, stat)} | {MEM[form]} | {method} | {real:+.2f} | "
                       + " | ".join(cells) + f" | {('%g' % min(ruled)) if ruled else 'none up to 2'} |")
    return "\n".join(out)


def depth_tables() -> str:
    d = pd.read_csv(S.OUT / "stage3_planted_depth.csv")
    d = d[d["truth"] == "career"]
    out = ["**Partial correlation squared by data depth** (career value, 52-week memory): the matches split into quarters "
           "by the smaller of the two players' denominators in the memory; median depth and corr² per quarter.", "",
           "| Tour | Statistic | Depth unit | Quarter 1 | Quarter 2 | Quarter 3 | Quarter 4 |", "|---|---|---|---:|---:|---:|---:|"]
    for t in ("atp", "wta"):
        for stat, h in d[d["tour"] == t].groupby("statistic", sort=False):
            h = h.sort_values("quartile")
            cells = [f"{r.depth_median:,.0f}: {r.partial_corr_sq:.2f}" for r in h.itertuples()]
            out.append(f"| {TOUR[t]} | {STAT_WORDS.get(stat, stat)} | {UNITS.get(stat, '')} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def main() -> int:
    parts = ["# Stage 3 tables (generated by src/eda/shot_level/stage3_tables.py)", "",
             "## Points", "", points_tables(), "", split_tables(), "", "## Flexible learners", "", flexible_tables(), "",
             "## Profiles without the fitting cost", "", profile_tables(), "## Planted edges", "", planted_tables(), "",
             "## Depth", "", depth_tables(), ""]
    (S.OUT / "stage3_tables.md").write_text("\n".join(parts), encoding="utf-8")
    print("\n".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
