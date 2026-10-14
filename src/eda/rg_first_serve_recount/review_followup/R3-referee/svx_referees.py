"""R3-referee, group SVX, step 2: the independent records that name the server point by point.

  CV   the Hawk-Eye Court Vision copy (RG 2019-2024; AO 2020-2024 does not overlap AO 2025): per RG code, the games in
       order (set_num, game_num) with their server id, from the rows other than 'Faulty Serve'; the first server; the
       alternation of serve in the copy's own sequence; service games per player (games one player served outside
       tiebreaks). Joined to the row's sides by RG's player ids (official_rows.csv).
  MCP  the Match Charting Project's point files (Roland Garros 2019-2026 and the Australian Open 2025): per chart the
       server of the first point and service games per player (games one player served outside a 6-6 tiebreak, set by
       Set1+Set2 and game by Gm1+Gm2), placed on the raw rows by tour, round and both names.
A referee holds a match when it has its first game and as many games as the score (the unfinished game of a retirement
set apart for its server). Then, per match: does the referee's first server equal MatchBeats'; do its service games
equal the truth (the score's alternation) and differ from the row's exchanged ones. Calibrated on the 'equal' matches
(row = truth).
Writes svx_ref_rows.csv and svx_ref_summary.json into data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/svx_referees.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


def cv_matches() -> pd.DataFrame:
    rows = []
    for f in sorted((F.DUMP / "slam_ball_tracking" / "points").glob("RG_*.parquet")):
        yr = int(f.stem.split("_")[1])
        pt = pd.read_parquet(f, columns=["match_id", "point_ID", "set_num", "game_num", "point_num", "server_id",
                                         "point_end_type", "is_tiebreak"])
        pt = pt[~pt["point_end_type"].eq("Faulty Serve")].drop_duplicates(["match_id", "point_ID"])
        pt["code"] = pt["match_id"].astype(str).str.split("_").str[-1]
        for c in ("set_num", "game_num", "point_num"):
            pt[c] = pd.to_numeric(pt[c], errors="coerce")
        for code, g in pt.groupby("code"):
            g = g.sort_values(["set_num", "game_num", "point_num"])
            gm = g.groupby(["set_num", "game_num"], sort=True).agg(
                servers=("server_id", lambda s: tuple(dict.fromkeys(s.astype(str)))),
                first=("server_id", lambda s: str(s.iloc[0])),
                tb=("is_tiebreak", lambda s: bool(s.astype(str).isin(["1", "True", "true"]).any()))).reset_index()
            first = gm["first"].iloc[0]
            ids = sorted({x for t in gm["servers"] for x in t})
            other = next((i for i in ids if i != first), None)
            expected, alt_ok = first, True
            gaps = False
            prev = None
            for r in gm.itertuples():
                if prev is not None and ((r.set_num == prev[0] and r.game_num != prev[1] + 1)
                                         or (r.set_num != prev[0] and not (r.set_num == prev[0] + 1 and r.game_num == 1))):
                    gaps = True
                alt_ok &= r.first == expected
                expected = other if expected == first else first
                prev = (r.set_num, r.game_num)
            # a tiebreak is a game both players serve in: the copy also flags the games after 6-6 of an
            # advantage final set (RG to 2021) as tiebreak games, so its own flag is not used
            regular = gm[gm["servers"].map(len).eq(1)]
            cnt = regular["first"].value_counts()
            rows.append({"year": yr, "code": code, "cv_first": str(first).replace(".0", ""),
                         "cv_starts_at_1_1": bool(gm["set_num"].iloc[0] == 1 and gm["game_num"].iloc[0] == 1),
                         "cv_alternation_ok": bool(alt_ok), "cv_gaps": bool(gaps), "cv_games": int(len(gm)),
                         "cv_last_server": str(gm["first"].iloc[-1]).replace(".0", ""),
                         "cv_counts": {str(k).replace(".0", ""): int(v) for k, v in cnt.items()}})
    return pd.DataFrame(rows)


def mcp_matches() -> pd.DataFrame:
    base = F.DUMP / "match_charting_project"
    out = []
    for g in ("m", "w"):
        mm = pd.read_parquet(base / "metadata" / f"charting-{g}-matches.parquet")
        t = mm["Tournament"].astype(str)
        yr = pd.to_numeric(mm["Date"].astype(str).str[:4], errors="coerce")
        sel = (t.str.contains("Roland", case=False) & yr.between(2019, 2026)) | \
              (t.str.contains("Australian", case=False) & yr.eq(2025))
        mm = mm[sel].copy()
        pts = pd.concat([pd.read_parquet(f) for f in sorted((base / "points").glob(f"charting-{g}-points-20*.parquet"))],
                        ignore_index=True)
        pts = pts[pts["match_id"].isin(set(mm["match_id"]))].copy()
        for c in ["Pt", "Set1", "Set2", "Gm1", "Gm2", "Svr"]:
            pts[c] = pd.to_numeric(pts[c], errors="coerce")
        tbset = pts["TbSet"].astype(str).str.lower().isin(["true", "1"])
        pts["tb"] = tbset & pts["Gm1"].eq(6) & pts["Gm2"].eq(6)
        pts["set_i"], pts["game_i"] = pts["Set1"] + pts["Set2"], pts["Gm1"] + pts["Gm2"]
        for mid, p in pts.sort_values(["match_id", "Pt"]).groupby("match_id"):
            m = mm[mm["match_id"].eq(mid)].iloc[0]
            games = p.groupby(["set_i", "game_i"], sort=True).agg(svr=("Svr", lambda s: tuple(dict.fromkeys(s))),
                                                                   first=("Svr", "first"), tb=("tb", "any")).reset_index()
            reg = games[~games["tb"] & games["svr"].map(len).eq(1)]
            expected, alt_ok = games["first"].iloc[0], True
            for r in games.itertuples():
                alt_ok &= r.first == expected
                expected = 2 if expected == 1 else 1
            out.append({"mcp_id": mid, "tour": "atp" if g == "m" else "wta",
                        "event": "AO" if "Australian" in str(m["Tournament"]) else "RG",
                        "year": int(str(m["Date"])[:4]), "round": str(m["Round"]).strip(),
                        "p1": m["Player 1"], "p2": m["Player 2"],
                        "mcp_first": int(games["first"].iloc[0]),
                        "mcp_starts_at_0_0": bool(games["set_i"].iloc[0] == 0 and games["game_i"].iloc[0] == 0),
                        "mcp_alternation_ok": bool(alt_ok), "mcp_games": int(len(games)),
                        "mcp_p1": int((reg["first"] == 1).sum()), "mcp_p2": int((reg["first"] == 2).sum())})
    return pd.DataFrame(out)


def main() -> int:
    d = pd.read_csv(F.OUT / "svx_rows.csv", low_memory=False)
    o = pd.read_csv(F.OUT / "official_rows.csv", low_memory=False)
    o["key"] = F.rowkey(o["source_file"], o["source_row"])
    ids = o.drop_duplicates("key").set_index("key")[["rg_w_id", "rg_l_id"]]
    d = d.join(ids, on="key")
    d["games"] = d["score"].fillna("").map(lambda s: sum(B.score_counts(str(s), False)[2:4]))
    d["unfinished_server"] = np.nan
    # ---------------------------------------------------------------- Court Vision
    cv = cv_matches()
    d = d.merge(cv.rename(columns={"year": "season", "code": "mb_code"}), on=["season", "mb_code"], how="left")
    w_id = d["rg_w_id"].astype("Int64").astype(str)
    l_id = d["rg_l_id"].astype("Int64").astype(str)
    d["cv_first_side"] = np.where(d["cv_first"].isna(), None, np.where(d["cv_first"] == w_id, "w",
                                                                      np.where(d["cv_first"] == l_id, "l", "?")))
    d["cv_w"] = [c.get(i) if isinstance(c, dict) else np.nan for c, i in zip(d["cv_counts"], w_id)]
    d["cv_l"] = [c.get(i) if isinstance(c, dict) else np.nan for c, i in zip(d["cv_counts"], l_id)]
    # ---------------------------------------------------------------- MCP
    mc = mcp_matches()
    rows = []
    groups = {k: g for k, g in d.groupby(["event", "season", "tour", "round"])}
    for r in mc.itertuples():
        cand = groups.get((r.event, r.year, r.tour, r.round))
        if cand is None:
            continue
        best = []
        for x in cand.itertuples():
            for p1_is_w in (True, False):
                a = F.name_ok(r.p1, x.winner_name if p1_is_w else x.loser_name)
                b = F.name_ok(r.p2, x.loser_name if p1_is_w else x.winner_name)
                if min(a, b) >= 1:
                    best.append(((min(a, b), a + b), x.key, p1_is_w))
        best.sort(key=lambda z: z[0], reverse=True)
        if not best or (len(best) > 1 and best[0][0] == best[1][0]):
            continue
        _, key, p1_is_w = best[0]
        rows.append({"key": key, "mcp_id": r.mcp_id, "mcp_first_side": ("w" if (r.mcp_first == 1) == p1_is_w else "l"),
                     "mcp_w": r.mcp_p1 if p1_is_w else r.mcp_p2, "mcp_l": r.mcp_p2 if p1_is_w else r.mcp_p1,
                     "mcp_alternation_ok": r.mcp_alternation_ok, "mcp_starts_at_0_0": r.mcp_starts_at_0_0,
                     "mcp_games": r.mcp_games})
    M = pd.DataFrame(rows).drop_duplicates("key")
    d = d.merge(M, on="key", how="left")
    # ---------------------------------------------------------------- readings
    retired = d["status_s0"].eq("retired")
    for ref in ("cv", "mcp"):
        full = d[f"{ref}_games"].notna() & (d[f"{ref}_games"] >= d["games"]) & \
            d[f"cv_starts_at_1_1" if ref == "cv" else "mcp_starts_at_0_0"].fillna(False).astype(bool)
        d[f"{ref}_holds"] = full
        d[f"{ref}_first_agrees"] = np.where(full, d[f"{ref}_first_side"] == d["first_side"], None)
        # a retirement's unfinished game: the referee counts it for its server, the truth does not
        extra_w = retired & (d[f"{ref}_games"] == d["games"] + 1)
        tw = d["true_w"] + np.where(extra_w & (d[f"{ref}_w"] > d["true_w"]), 1, 0)
        tl = d["true_l"] + np.where(extra_w & (d[f"{ref}_l"] > d["true_l"]), 1, 0)
        reads_truth = full & d[f"{ref}_w"].eq(tw) & d[f"{ref}_l"].eq(tl)
        reads_row = full & d[f"{ref}_w"].eq(d["row_w"]) & d[f"{ref}_l"].eq(d["row_l"])
        d[f"{ref}_reading"] = np.select([~full, reads_truth & reads_row, reads_truth, reads_row],
                                        ["not held", "both (row = truth)", "truth", "row"], "neither")
    d.to_csv(F.OUT / "svx_ref_rows.csv", index=False)
    smry = {}
    for ref in ("cv", "mcp"):
        h = d[d[f"{ref}_holds"]]
        smry[ref] = {
            "matches_held": int(len(h)),
            "first_server_agrees_with_matchbeats": {k: int(v) for k, v in
                                                     h[f"{ref}_first_agrees"].value_counts(dropna=False).items()},
            "readings_by_class": h.groupby(["my_cls", f"{ref}_reading"]).size().rename("matches").reset_index()
            .to_dict("records"),
            "proposed_held": int(h["lead_proposed"].sum()),
            "proposed_readings": h.loc[h["lead_proposed"], f"{ref}_reading"].value_counts().to_dict(),
            "proposed_by_edition": h[h["lead_proposed"]].groupby(["event", "season"]).size().rename("matches")
            .reset_index().to_dict("records")}
    both = d[d["lead_proposed"] & (d["cv_holds"] | d["mcp_holds"])]
    smry["proposed_held_by_any"] = int(len(both))
    smry["proposed_against"] = d.loc[d["lead_proposed"] & (d["cv_reading"].isin(["row", "neither"])
                                                          | d["mcp_reading"].isin(["row", "neither"])),
                                     ["event", "season", "match_id", "winner_name", "loser_name", "score", "row_w",
                                      "row_l", "true_w", "true_l", "cv_w", "cv_l", "cv_reading", "mcp_w", "mcp_l",
                                      "mcp_reading"]].to_dict("records")
    (F.OUT / "svx_ref_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
