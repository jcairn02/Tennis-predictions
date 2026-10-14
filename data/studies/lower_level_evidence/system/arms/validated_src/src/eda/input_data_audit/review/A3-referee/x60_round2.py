"""Round 2 (A3-referee): the 36 extra box-score rows of data/studies/input_data_audit/fixes/round2_A_candidates.csv.

Per match: Sackmann's raw row, Stage 0's row, the independent records, the proposed fix applied in memory, and
Stage 0's checks B0-B9 (replica and stage0_build.box_scores), the games identity on both players, points won and
the minimum-points rule, before and after.

    F1x / F1y  svpt := svpt + df for both players: MCP's charted serve points (F1x); the definition test and B6 (F1y)
    F2x        exchange all nine counts: the WTA API's whole-match statistics per player, as recorded vs exchanged,
               and its result string (winner and score)
    F2y        exchange the two players' sv_gms only: AO 2022 ball tracking (2022_MS146) and Sofascore
    F4x        blank the AO 2012 box: Sackmann's Slam point-by-point of AO 2012 and Wimbledon 2012, MCP
Writes round2_evidence.csv (one row per match) and prints the details.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
import refs  # noqa: E402

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 300)
pd.set_option("display.max_colwidth", 70)

CAND = rc.ROOT / "data/studies/input_data_audit/fixes/round2_A_candidates.csv"
ALIASES = {"alison riske": "alison amritraj riske", "sanders storm": "hunter storm", "smith tina": "nadine smith tina"}


def raw_row(source_file: str, row: int) -> pd.Series:
    tour = "atp" if "/atp/" in source_file else "wta"
    name = source_file.split("/")[-1].replace(".csv", ".parquet")
    t = pd.read_parquet(rc.SACK / tour / name)
    return t[t["_row"] == row].iloc[0]


def _val(x) -> float:
    v = rc.num(pd.Series([x]).astype("string"))[0]
    return np.nan if pd.isna(v) else float(v)


def boxes(rr: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    w = pd.DataFrame([{b: _val(rr[f"w_{rc.SRC[b]}"]) for b in rc.BOX}])
    l_ = pd.DataFrame([{b: _val(rr[f"l_{rc.SRC[b]}"]) for b in rc.BOX}])
    return w, l_


def checks(w: pd.DataFrame, l_: pd.DataFrame, s0: pd.Series, g_w, g_l, tb_w, tb_l) -> dict:
    """w / l in the RAW row's orientation; g_* / tb_* the games of the raw winner / loser."""
    c = rc.box_checks(w, l_, pd.Series([s0["score"]]), pd.Series([s0["status"]]), pd.Series([s0["status_detail"]]))
    out = {"B0_B9_pass": bool(c["has_box"][0]), "stage0_keeps": bool(c["has_box_stage0"][0]),
           "failed": ",".join(k for k in ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"] if c[k][0])}
    if pd.notna(g_w) and pd.notna(g_l):
        ident = rc.games_identity(pd.Series([g_w]), pd.Series([g_l]), w, l_, pd.Series([tb_w]), pd.Series([tb_l]))
        out["identity_both"] = bool(ident["both_fit"][0])
    pw, pl = rc.points_won(w, l_)
    out["pts_rawwinner"], out["pts_rawloser"] = float(pw[0]), float(pl[0])
    out["deffail"] = bool(rc.definition_fails(w).iloc[0] or rc.definition_fails(l_).iloc[0])
    return out


def stage0_games(m, p, mid, rr, tour):
    """Games and tiebreaks of the raw winner and loser, from Stage 0's player rows."""
    pw = p[(p["match_id"] == mid) & (p["player_id"] == f"{tour}:{rr['winner_id']}")]
    pl = p[(p["match_id"] == mid) & (p["player_id"] == f"{tour}:{rr['loser_id']}")]
    if pw.empty or pl.empty:
        return np.nan, np.nan, 0.0, 0.0
    g = lambda x, c: x.iloc[0][c] if pd.notna(x.iloc[0][c]) else (0.0 if c.startswith("tb") else np.nan)
    return g(pw, "games_won_n"), g(pl, "games_won_n"), g(pw, "tb_won_n"), g(pl, "tb_won_n")


def main() -> int:
    cand = pd.read_csv(CAND)
    print(cand["cand"].value_counts().to_dict())
    m, p = rc.stage0()
    api = rc.wta_api_totals()
    api["pk"], api["ok"] = api["pk"].replace(ALIASES), api["ok"].replace(ALIASES)
    api["sn"], api["osn"] = api["name"].map(refs.surname), api["oname"].map(refs.surname)
    ed = rc.rd(rc.WTA / "editions.parquet")[["tournament_id", "year", "title", "start_date"]]
    ed["tournament_id"], ed["year"] = ed["tournament_id"].astype(str), ed["year"].astype(str)
    api = api.merge(ed.drop_duplicates(["tournament_id", "year"]), on=["tournament_id", "year"], how="left")
    api["start"] = pd.to_datetime(api["start_date"], errors="coerce")
    mcp = refs.ref_mcp()
    ev = []
    for _, c in cand.iterrows():
        rr = raw_row(c["source_file"], int(c["source_row"]))
        tour = "atp" if "/atp/" in c["source_file"] else "wta"
        s0 = m[m["match_id"] == c["match_id"]]
        assert len(s0) == 1, c["match_id"]
        s0 = s0.iloc[0]
        assert s0["source_file"] == c["source_file"] and int(s0["source_row"]) == int(c["source_row"])
        w, l_ = boxes(rr)
        gw, gl, tbw, tbl = stage0_games(m, p, c["match_id"], rr, tour)
        rec = {"cand": c["cand"], "match_id": c["match_id"], "event": c["tournament_name"], "date": c["tournament_date"],
               "round": c["round"], "score": c["score"], "raw_winner": rr["winner_name"], "raw_loser": rr["loser_name"],
               "stage0_has_box": bool(s0["has_box"]), "stage0_box_status": s0["box_status"],
               "stage0_winner_is_raw_winner": bool(p[(p["match_id"] == c["match_id"]) & p["won"]]["player_id"].iloc[0]
                                                   == f"{tour}:{rr['winner_id']}")}
        before = checks(w, l_, s0, gw, gl, tbw, tbl)
        rec.update({f"before_{k}": v for k, v in before.items()})
        if c["cand"] in ("F1x", "F1y"):
            w2, l2 = w.copy(), l_.copy()
            w2["svpt"] += w2["df"]
            l2["svpt"] += l2["df"]
            after = checks(w2, l2, s0, gw, gl, tbw, tbl)
            rec.update({f"after_{k}": v for k, v in after.items()})
            rec.update({"w_svpt": w["svpt"][0], "w_df": w["df"][0], "l_svpt": l_["svpt"][0], "l_df": l_["df"][0]})
            # MCP
            td = pd.Timestamp(c["tournament_date"])
            for side, nm, on in (("w", rr["winner_name"], rr["loser_name"]), ("l", rr["loser_name"], rr["winner_name"])):
                x = mcp[(mcp["pk"] == rc.name_key(nm)) & (mcp["ok"] == rc.name_key(on))
                        & (mcp["date"] - td).dt.days.between(-1, 16)]
                bx = w if side == "w" else l_
                if len(x):
                    x = x.iloc[0]
                    rec[f"mcp_{side}"] = (f"MCP serve points {x['svpt']:g} (svpt {bx['svpt'][0]:g} + df {bx['df'][0]:g} = "
                                          f"{bx['svpt'][0] + bx['df'][0]:g}); first_in {x['first_in']:g}/{bx['first_in'][0]:g}, "
                                          f"first_won {x['first_won']:g}/{bx['first_won'][0]:g}, second_won "
                                          f"{x['second_won']:g}/{bx['second_won'][0]:g}, aces {x['ace']:g}/{bx['ace'][0]:g}, "
                                          f"df {x['df']:g}/{bx['df'][0]:g}")
        elif c["cand"] == "F2x":
            # WTA API: same tournament number where Sackmann's id carries it, else the edition starting within 10 days
            mt = re.match(r"^\d{4}-(\d+)$", str(rr["tourney_id"]))
            yr = str(rr["tourney_id"])[:4]
            if mt:
                cand_api = api[(api["tournament_id"] == mt.group(1)) & (api["year"] == yr)]
            else:
                cand_api = api[(api["start"] - td_).dt.days.abs().le(10)] if (td_ := pd.Timestamp(c["tournament_date"])) is not None else api
            got = {}
            for side, nm, on in (("w", rr["winner_name"], rr["loser_name"]), ("l", rr["loser_name"], rr["winner_name"])):
                pk, ok = rc.name_key(nm), rc.name_key(on)
                x = cand_api[(cand_api["pk"] == pk) & (cand_api["ok"] == ok)]
                if x.empty:
                    x = cand_api[(cand_api["sn"] == refs.surname(nm)) & (cand_api["osn"] == refs.surname(on))]
                if len(x) > 1:   # the same pair twice in one event (qualifying and main): keep the round's draw
                    dr = "RS" if str(c["round"]).startswith("Q") else "LS"
                    x = x[x["draw"] == dr]
                got[side] = x.iloc[0] if len(x) == 1 else None
            if got["w"] is not None and got["l"] is not None:
                aw = {b: got["w"][f"api_{b}"] for b in rc.BOX}
                al = {b: got["l"][f"api_{b}"] for b in rc.BOX}
                eq_rec = sum(aw[b] == w[b][0] for b in rc.BOX) + sum(al[b] == l_[b][0] for b in rc.BOX)
                eq_exc = sum(aw[b] == l_[b][0] for b in rc.BOX) + sum(al[b] == w[b][0] for b in rc.BOX)
                allzero = all(v == 0 for v in list(aw.values()) + list(al.values()))
                res = str(got["w"]["result"])
                ws = refs.surname(rr["winner_name"])
                lead = rc.name_key(res.split(" d ")[0]) if " d " in res else ""
                rec.update({"api_match": f"{got['w']['tournament_id']}/{got['w']['year']}/{got['w']['wmatch']} {got['w']['title']}",
                            "api_eq_as_recorded": int(eq_rec), "api_eq_exchanged": int(eq_exc), "api_all_zero": allzero,
                            "api_result": res, "api_names_raw_winner": bool(ws and ws in lead),
                            "api_score": got["w"]["score"]})
            else:
                rec.update({"api_match": "not found"})
            after = checks(l_, w, s0, gw, gl, tbw, tbl)      # exchanged: the raw winner takes the loser's box
            rec.update({f"after_{k}": v for k, v in after.items()})
        elif c["cand"] == "F2y":
            w2, l2 = w.copy(), l_.copy()
            w2["sv_gms"], l2["sv_gms"] = l_["sv_gms"][0], w["sv_gms"][0]
            after = checks(w2, l2, s0, gw, gl, tbw, tbl)
            rec.update({f"after_{k}": v for k, v in after.items()})
            rec.update({"w_svgms": w["sv_gms"][0], "l_svgms": l_["sv_gms"][0]})
        elif c["cand"] == "F4x":
            rec.update({f"w_{b}": w[b][0] for b in rc.BOX})
            rec.update({f"l_{b}": l_[b][0] for b in rc.BOX})
        ev.append(rec)
    E = pd.DataFrame(ev)
    E.to_csv(rc.OUT / "round2_evidence.csv", index=False)
    for cnd, g in E.groupby("cand"):
        print(f"\n===================== {cnd} ({len(g)})")
        print(g.dropna(axis=1, how="all").T.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
