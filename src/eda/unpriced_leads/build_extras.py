"""The lead's own builds for two research-backed candidates nobody else was building (unpriced-leads study, 13 Oct 2026):

RS05, a load spike against the player's own normal (the researcher's RS05; the pool's U-161, never built):
    acute = games played (singles, every level in Stage 0) in the player's strictly earlier matches whose best-estimate
            day is within the 14 days before this match's (same-day earlier rounds included);
    chronic = games in the strictly earlier matches 15-70 days before, per 14 days (/ 4);
    rs05_spike = log((acute + 10) / (chronic + 10)); rs05_flag = 1[(acute + 10) / (chronic + 10) >= 1.5]. A - B.
    Registered direction (the researcher's): a spike costs the player (-). Own sequence: safe by construction.

RS09, the draw shadow (the researcher's RS09, after Creutzburg 2024):
    per main-draw event (tournament id and date, qualifying out), each entrant's Elo at the start of the event (Stage 1's
    pre-match Elo, `elo_*_ret`, at his first main-draw match there; its result column is never read); the dominant
    players are the entrants at least 100 Elo points above the third-best entrant;
    at a match m with earliest start es, a dominant player other than m's two players is alive unless he lost a match
    at the event that surely finished before m could start (lf + 1 <= es): the match clock's rule for cross-player
    information (CLAUDE.md "Feature timing");
    rs09_shadow = S_A - S_B with S = 1[official rank <= 20] x 1[not dominant] x 1[a dominant other is alive]
                  (registered -: the shadowed player wins less than priced);
    rs09_reverse = R_A - R_B with R = 1[rank > 50] x 1[a dominant other is alive] (registered +).
    Rank is Stage 0's pre-match official rank.

Writes data/studies/unpriced_leads/candidates/extras/ (values.parquet for every frame match, no result column; long.csv,
summary.csv, probes.json, coverage.json) and screens with the harness (raw, orthogonal, with and without the
curvature base), seasons <= 2024.
Run: ./python.sh src/eda/unpriced_leads/build_extras.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402

OUT = H.OUT / "candidates" / "extras"
STAGE1 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage1_baselines.parquet"
SEALED_FROM = pd.Timestamp("2026-07-29")


# ------------------------------------------------------------------------------------------------- RS05 load spike

def build_rs05(L: pd.DataFrame) -> pd.DataFrame:
    """Per (match, player): acute and chronic games from strictly earlier rows of the same player."""
    g = L[["match_id", "player_id", "k", "obs_mono", "tday", "games", "played"]].copy()
    day = g["obs_mono"].to_numpy(float)
    day = np.where(np.isfinite(day), day, g["tday"].to_numpy(float))
    games = np.where(g["played"].to_numpy(bool) & np.isfinite(g["games"].to_numpy(float)),
                     g["games"].to_numpy(float), 0.0)
    pid = g["player_id"].to_numpy()
    order = np.lexsort((g["k"].to_numpy(), pid))
    day, games, pid_s = day[order], games[order], pid[order]
    acute = np.zeros(len(g))
    chronic = np.zeros(len(g))
    starts = np.flatnonzero(np.r_[True, pid_s[1:] != pid_s[:-1]])
    ends = np.r_[starts[1:], len(pid_s)]
    for s, e in zip(starts, ends):
        d = np.maximum.accumulate(day[s:e])
        cs = np.r_[0.0, np.cumsum(games[s:e])]          # cs[i] = games of rows before i (exclusive prefix)
        i = np.arange(e - s)
        lo14 = np.searchsorted(d, d - 14, side="left")
        lo70 = np.searchsorted(d, d - 70, side="left")
        lo14 = np.minimum(lo14, i)                      # strictly earlier rows only
        lo70 = np.minimum(lo70, lo14)
        acute[s:e] = cs[i] - cs[lo14]
        chronic[s:e] = (cs[lo14] - cs[lo70]) / 4.0
    out = pd.DataFrame({"match_id": g["match_id"].to_numpy()[order], "player_id": pid_s,
                        "rs05_acute": acute, "rs05_chronic": chronic})
    ratio = (out["rs05_acute"] + 10) / (out["rs05_chronic"] + 10)
    out["rs05_spike"] = np.log(ratio)
    out["rs05_flag"] = (ratio >= 1.5).astype(float)
    return out


# ------------------------------------------------------------------------------------------------ RS09 draw shadow

def elo_at_matches() -> pd.DataFrame:
    """Each (match, player)'s pre-match Elo from Stage 1 (the result column is not loaded)."""
    e = pd.read_parquet(STAGE1, columns=["match_id", "elo_a_ret", "elo_b_ret"]).astype({"match_id": str})
    m = pd.read_parquet(H.STAGE0_M, columns=["match_id", "player_a_id", "player_b_id"]).astype({"match_id": str})
    e = e.merge(m, on="match_id", how="inner")
    a = e[["match_id", "player_a_id", "elo_a_ret"]].rename(columns={"player_a_id": "player_id", "elo_a_ret": "elo"})
    b = e[["match_id", "player_b_id", "elo_b_ret"]].rename(columns={"player_b_id": "player_id", "elo_b_ret": "elo"})
    return pd.concat([a, b], ignore_index=True)


MAIN_LEVELS = ("GS", "T1000", "T500", "T250", "FIN")


def build_rs09(L: pd.DataFrame, elo: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per (match, player) of main-draw matches at main-tour events (the levels the frame holds): S, R and the count
    of dominant others alive at es."""
    elo = elo_at_matches() if elo is None else elo
    keep = (~L["qualifying"].astype(bool)).to_numpy() & L["level"].isin(MAIN_LEVELS).to_numpy()
    M = L.loc[keep, ["match_id", "player_id", "opponent_id", "won", "es", "lf", "tournament_id", "tday",
                     "round_order", "match_num", "rank", "k"]].copy()
    M = M.merge(elo, on=["match_id", "player_id"], how="left")
    M["ev"] = M["tournament_id"].astype(str) + "|" + M["tday"].astype(str)
    # Elo at the start of the event: the player's first main-draw row there
    first = M.sort_values(["ev", "player_id", "k"]).drop_duplicates(["ev", "player_id"])
    start_elo = first.set_index(["ev", "player_id"])["elo"]
    rows = []
    for ev, h in M.groupby("ev", sort=False):
        se = start_elo.loc[ev].dropna() if ev in start_elo.index.get_level_values(0) else pd.Series(dtype=float)
        if len(se) < 3:
            continue
        third = np.sort(se.to_numpy())[::-1][2]
        dom = set(se.index[se.to_numpy() >= third + 100])
        if not dom:
            continue
        # each dominant player's elimination: the latest-finishing day of a lost match at the event (a loss counts
        # from lf + 1); a dominant player who never lost here stays alive
        loss_lf = {}
        for d in dom:
            lost = h[(h["player_id"] == d) & (~h["won"].astype(bool))]
            loss_lf[d] = float(lost["lf"].min()) if len(lost) else np.inf
        for _, r in h.iterrows():
            others = [d for d in dom if d not in (r["player_id"], r["opponent_id"])]
            alive = sum(1 for d in others if not (loss_lf[d] + 1 <= r["es"]))
            rows.append((r["match_id"], r["player_id"], alive, r["player_id"] in dom, r["rank"]))
    out = pd.DataFrame(rows, columns=["match_id", "player_id", "rs09_alive", "rs09_dominant", "rank"])
    rk = pd.to_numeric(out["rank"], errors="coerce")
    on = out["rs09_alive"] >= 1
    out["rs09_S"] = ((rk <= 20) & ~out["rs09_dominant"] & on).astype(float)
    out["rs09_R"] = ((rk > 50) & on).astype(float)
    return out.drop(columns=["rank"])


# ------------------------------------------------------------------------------------------------------- main

def align(frame: pd.DataFrame, vals: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = pd.DataFrame({"match_id": frame["match_id"].astype(str).to_numpy()})
    for c in cols:
        a, b = H.at_frame(vals, c, frame)
        out[f"{c}_a"], out[f"{c}_b"] = a, b
        out[c] = a - b
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    L = H.long_table()
    elo = elo_at_matches()
    v5 = build_rs05(L)
    v9 = build_rs09(L, elo)
    fa = H.frame_outcome_free()
    cols5, cols9 = ["rs05_spike", "rs05_flag"], ["rs09_S", "rs09_R"]
    V = align(fa, v5, cols5).merge(align(fa, v9, cols9).drop(columns=[]), on="match_id")
    # a main-draw match whose event has no dominant player gets 0 (no shadow), not missing
    for c in cols9:
        present = np.isfinite(V[f"{c}_a"]) | np.isfinite(V[f"{c}_b"])
        for s in ("_a", "_b"):
            V[c + s] = V[c + s].fillna(0.0)
        V[c] = V[c + "_a"] - V[c + "_b"]
        V[c + "_event_has_dominant"] = present.astype(float)
    V.to_parquet(OUT / "values.parquet", index=False)
    # timing probes: RS05 (own sequence: both checks); RS09 (cross-player: the future check only is valid)
    probes = {"rs05": H.timing_probe(build_rs05, L, ["rs05_spike", "rs05_flag"]),
              "rs09": H.timing_probe(lambda X: build_rs09(X, elo), L, ["rs09_S", "rs09_R"]),
              "note": "rs09 combines different players' results: only the future-row check applies; its own-row "
                      "check can move legitimately (a same-event result with lf + 1 <= es after the cut)."}
    (OUT / "probes.json").write_text(json.dumps(probes, indent=1), encoding="utf-8")
    # coverage, outcome-free, frame rows before the sealed set
    keep = (fa["tournament_date"] < SEALED_FROM).to_numpy()
    cov = {c: H.coverage_2025_26(fa[keep], V.loc[keep, c].to_numpy(float)) for c in cols5 + cols9}
    nz = {c: {f"{t}_{lab}": float(np.mean(V.loc[keep & (fa["tour"] == t).to_numpy()
                                                & fa["season"].between(a, b).to_numpy(), c] != 0))
              for t in ("atp", "wta") for lab, (a, b) in (("2013_24", (2013, 2024)), ("2025_26", (2025, 2026)))}
          for c in cols5 + cols9}
    (OUT / "coverage.json").write_text(json.dumps({"present": cov, "nonzero": nz}, indent=1), encoding="utf-8")
    # screens, seasons <= 2024
    f = H.load_frame()
    Vi = V.drop_duplicates("match_id").set_index("match_id")
    longs = []
    for c in cols5 + cols9:
        x = Vi[c].reindex(f["match_id"]).to_numpy(float)
        xo, _ = H.orthogonal_part(f, x)
        for nm, xx in ((c, x), (c + "__orth", xo)):
            longs.append(H.screen(f, xx, nm, "diff"))
            cl = H.close_lens(f, xx, nm, "diff", curv=True)
            cl["r2_inputs"] = np.nan
            longs.append(cl)
    long = pd.concat(longs, ignore_index=True)
    long.to_csv(OUT / "long.csv", index=False)
    s1 = H.summarize(long, lens="close")
    s2 = H.summarize(long, lens="close+curv")[["name", "tour", "z_pool", "eras_same_sign"]].rename(
        columns={"z_pool": "z_pool_curv", "eras_same_sign": "eras_same_sign_curv"})
    summ = s1.merge(s2, on=["name", "tour"], how="left")
    summ.to_csv(OUT / "summary.csv", index=False)
    pd.set_option("display.width", 250)
    print(json.dumps(probes, indent=1))
    print(json.dumps(nz, indent=1))
    print(summ[["name", "tour", "z_pool", "eras_same_sign", "z_pool_curv", "z_2013-16", "z_2017-19", "z_2020-22",
                "z_2023-24", "z_model_2020_24", "z_move_2018_24", "r2_inputs"]].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
