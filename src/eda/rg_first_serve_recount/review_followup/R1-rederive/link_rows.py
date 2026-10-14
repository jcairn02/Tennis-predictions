"""R1-rederive (round 2): link RG's documents to Stage 0's raw rows of Roland Garros 2019-2026, myself.

Inputs: my parsed feeds (work/rg_api.parquet, mb.parquet, mb_games.parquet, ks.parquet, from parse_feeds.py) and
Stage 0's raw rows as the build reads them (work/stage0_rg_rows.parquet, from stage0_rows.py:
stage0_build.normalise(stage0_build.load_raw())). No code or table of the lead's study is read.

Rows linked:
  * Sackmann's RG rows of 2019-2026 (tournament id <year>-520, both tours, main draw and qualifying);
  * Tennis My Life's RG 2026 men's qualifying (atp_qualifying, 2026-520): the rows Stage 0 holds for it;
  * for reference only (not in Stage 0): TML's RG 2026 main-draw rows (atp 2026-520, wta 2026-903).
Within each year, tour and round, documents and rows are paired by names (token overlap, optimal one-to-one
assignment); each pair records the name similarity of both players, whether RG's winner is the row's winner, and
whether the games of every set agree (the winner's view).

Service games, three ways, per player:
  * mb_sv: MatchBeats games served, tiebreak games not counted (complete games; the unfinished game of a retirement
    apart, as mb_sv_open);
  * der_sv: derived from RG's score and MatchBeats' first server: servers alternate game by game across the match
    (a tiebreak takes one turn), so a known first server fixes every game's server; tiebreak games are not counted.
    der_ok says MatchBeats' server agrees with the derived one on every game it holds;
  * raw_SvGms: the row's own.

Writes (data/studies/rg_first_serve_recount/followup/review/R1-rederive/):
  links.csv         one row per linked (document, Stage 0 row) pair, and the documents or rows left unpaired
  work/sides.parquet  one row per row side (w/l): raw_*, off_* (RG's statistics), mb_*, ks_*, the service-game counts
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/link_rows.py
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
SRC = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon",
       "second_won": "2ndWon", "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]


def toks(name) -> frozenset:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = s.replace("ø", "o").replace("ł", "l").replace("đ", "d").replace("ß", "ss")
    return frozenset(t for t in re.sub(r"[^a-z]+", " ", s).split() if t)


def sim(a: frozenset, b: frozenset) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def row_sets(score: str) -> list[tuple[int, int]]:
    out = []
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if m:
            out.append((int(m.group(1)), int(m.group(2))))
    return out


def ints(csv: str) -> list:
    return [int(x) if x not in ("", "None", "nan") else None for x in str(csv or "").split(",")] if csv else []


# ---------------------------------------------------------------------------------------------------------------
# service games derived from the score and the first server
# ---------------------------------------------------------------------------------------------------------------
def derive_service(ga: list, gb: list, tbs_a: list, tbs_b: list, first: str, games: pd.DataFrame) -> dict:
    """Teams '1'/'2' as MatchBeats numbers them; ga/gb are team 1/team 2 games per set (RG's score, mapped).
    Returns regular games served per team (tiebreaks not counted) and whether MatchBeats' servers agree."""
    if first not in ("1", "2") or not ga:
        return {"der_sv1": np.nan, "der_sv2": np.nan, "der_ok": False, "der_checked": 0}
    other = {"1": "2", "2": "1"}
    pos = 0
    sv = {"1": 0, "2": 0}
    server_at = {}
    for k, (a, b) in enumerate(zip(ga, gb)):
        if a is None or b is None:
            continue
        # a 7-6 set is a tiebreak set (an advantage set cannot end 7-6); RG also writes the tiebreak's points
        tb = max(a, b) == 7 and min(a, b) == 6
        n_reg = a + b - (1 if tb else 0)
        for g in range(1, n_reg + 1 + (1 if tb else 0)):
            pos += 1
            srv = first if pos % 2 == 1 else other[first]
            server_at[(k + 1, g)] = srv
            if tb and g == n_reg + 1:
                continue
            sv[srv] += 1
    checked = bad = 0
    for r in games.itertuples():
        if r.server is None or pd.isna(r.server):
            continue
        exp = server_at.get((int(r.set), int(r.game)))
        if exp is None:
            continue     # the unfinished game of a retirement, beyond the score's games
        checked += 1
        bad += exp != r.server
    return {"der_sv1": sv["1"], "der_sv2": sv["2"], "der_ok": checked > 0 and bad == 0, "der_checked": checked,
            "der_bad": bad}


# ---------------------------------------------------------------------------------------------------------------
# links
# ---------------------------------------------------------------------------------------------------------------
def documents(api: pd.DataFrame) -> pd.DataFrame:
    a = api.copy()
    a["tour"] = np.where(a["family"].isin(["SM", "QM"]), "atp", "wta")
    a["name"] = a["first_name"].fillna("") + " " + a["last_name"].fillna("")
    m = a.pivot_table(index=["year", "code", "tour", "round"], columns="team",
                      values=["name", "player_id", "winner", "games", "tbs", "end_cause", "country", "has_stats"],
                      aggfunc="first")
    m.columns = [f"{x}_{t}" for x, t in m.columns]
    return m.reset_index()


def link(docs: pd.DataFrame, rows: pd.DataFrame, label: str) -> pd.DataFrame:
    out = []
    for (y, tour, rnd), grp in docs.groupby(["year", "tour", "round"]):
        rr = rows[rows["season"].eq(y) & rows["tour"].eq(tour) & rows["round"].eq(rnd)]
        if rr.empty:
            continue
        dl, rl = grp.to_dict("records"), rr.to_dict("records")
        ta = [toks(d["name_A"]) for d in dl]
        tb = [toks(d["name_B"]) for d in dl]
        tw = [toks(r["winner_name"]) for r in rl]
        tl = [toks(r["loser_name"]) for r in rl]
        sc = np.array([[max(sim(ta[i], tw[j]) + sim(tb[i], tl[j]), sim(ta[i], tl[j]) + sim(tb[i], tw[j]))
                        for j in range(len(rl))] for i in range(len(dl))])
        ri, ci = linear_sum_assignment(-sc)
        used_d, used_r = set(), set()
        for i, j in zip(ri, ci):
            if sc[i, j] < 0.5:
                continue
            d, r = dl[i], rl[j]
            used_d.add(i)
            used_r.add(j)
            a_is_w = sim(ta[i], tw[j]) + sim(tb[i], tl[j]) >= sim(ta[i], tl[j]) + sim(tb[i], tw[j])
            wt, lt = ("A", "B") if a_is_w else ("B", "A")
            sw = sim(ta[i] if a_is_w else tb[i], tw[j])
            sl = sim(tb[i] if a_is_w else ta[i], tl[j])
            gw, gl = ints(d[f"games_{wt}"]), ints(d[f"games_{lt}"])
            rg_sets = [(p, q) for p, q in zip(gw, gl) if p is not None and q is not None]
            rsets = row_sets(r["score"])
            trim = [s for s in rg_sets if s != (0, 0)]
            out.append({"label": label, "year": y, "tour": tour, "round": rnd, "code": d["code"], "rid": r["rid"],
                        "source": r["source"], "source_file": r["_source_file"], "source_row": r["_row"],
                        "winner_name": r["winner_name"], "loser_name": r["loser_name"], "w_team": wt, "l_team": lt,
                        "rg_w_name": d[f"name_{wt}"], "rg_l_name": d[f"name_{lt}"], "sim_w": sw, "sim_l": sl,
                        "rg_w_flag": bool(d[f"winner_{wt}"]), "rg_l_flag": bool(d[f"winner_{lt}"]),
                        "winner_agrees": bool(d[f"winner_{wt}"]) and not bool(d[f"winner_{lt}"]),
                        "rg_w_id": d[f"player_id_{wt}"], "rg_l_id": d[f"player_id_{lt}"],
                        "row_score": r["score"], "rg_games": " ".join(f"{p}-{q}" for p, q in rg_sets),
                        "games_agree": rg_sets == rsets or (trim == rsets and len(trim) > 0),
                        "rg_end_cause": f"{d[f'end_cause_{wt}'] or ''}|{d[f'end_cause_{lt}'] or ''}",
                        "has_stats": bool(d["has_stats_A"]), "ioc_w": r["winner_ioc"], "rg_ioc_w": d[f"country_{wt}"],
                        "ioc_l": r["loser_ioc"], "rg_ioc_l": d[f"country_{lt}"]})
        for i, d in enumerate(dl):
            if i not in used_d:
                out.append({"label": label, "year": y, "tour": tour, "round": rnd, "code": d["code"],
                            "rg_w_name": d["name_A"], "rg_l_name": d["name_B"], "has_stats": bool(d["has_stats_A"])})
        for j, r in enumerate(rl):
            if j not in used_r:
                out.append({"label": label, "year": y, "tour": tour, "round": rnd, "rid": r["rid"],
                            "source": r["source"], "source_file": r["_source_file"], "source_row": r["_row"],
                            "winner_name": r["winner_name"], "loser_name": r["loser_name"], "row_score": r["score"]})
    return pd.DataFrame(out)


def main() -> None:
    api = pd.read_parquet(WORK / "rg_api.parquet")
    mb = pd.read_parquet(WORK / "mb.parquet")
    games = pd.read_parquet(WORK / "mb_games.parquet")
    ks = pd.read_parquet(WORK / "ks.parquet")
    s0 = pd.read_parquet(WORK / "stage0_rg_rows.parquet")
    s0["season"] = s0["season"].astype(int)
    sack = s0[s0["source"].eq("sackmann") & s0["tid"].str.fullmatch(r"20(19|2[0-6])-520")]
    tml_q = s0[s0["source"].eq("tml") & s0["group"].eq("atp_qualifying") & s0["tid"].eq("2026-520")]
    tml_m = s0[s0["source"].eq("tml") & s0["season"].eq(2026) & (
        (s0["group"].eq("atp_main") & s0["tid"].eq("2026-520")) | (s0["group"].eq("wta_main") & s0["tid"].eq("2026-903")))]
    docs = documents(api)
    main_rows = pd.concat([sack, tml_q], ignore_index=True)
    lk = link(docs, main_rows, "stage0")
    lk_ref = link(docs[docs["year"].eq(2026) & docs["code"].str[0].eq("S")], tml_m, "tml_2026_main_reference")
    links = pd.concat([lk, lk_ref], ignore_index=True)
    links["state"] = np.select([links["rid"].notna() & links["code"].notna(), links["rid"].isna()],
                               ["paired", "document_unpaired"], "row_unpaired")
    links.to_csv(HERE / "links.csv", index=False)
    print("links:\n", pd.crosstab([links["label"], links["year"]], links["state"]).to_string())

    # ---------------- sides
    apix = api.set_index(["year", "code", "team"])
    mbx = mb[mb["mb_status"].eq("ok")].set_index(["year", "code", "player_id"])
    mb_by_team = mb[mb["mb_status"].eq("ok")].set_index(["year", "code", "team"])
    ksx = ks[ks["ks_status"].eq("ok")].set_index(["year", "code", "player_id"])
    gx = {k: g for k, g in games.groupby(["year", "code"])}
    rowx = pd.concat([main_rows, tml_m], ignore_index=True).set_index("rid")
    out = []
    for L in links[links["rid"].notna() & links["code"].notna()].itertuples():
        r = rowx.loc[int(L.rid)]
        oA, oB = apix.loc[(L.year, L.code, "A")], apix.loc[(L.year, L.code, "B")]
        team_of = {"w": L.w_team, "l": L.l_team}
        # MatchBeats team numbers of RG's teams A/B, by player id
        mbt = {}
        for t in ("A", "B"):
            pid = (oA if t == "A" else oB)["player_id"]
            hit = [x for x in ("1", "2") if (L.year, L.code, x) in mb_by_team.index and
                   mb_by_team.loc[(L.year, L.code, x), "player_id"] == pid]
            mbt[t] = hit[0] if hit else None
        der = {}
        if mbt["A"] and mbt["B"]:
            ga, gb = ints(oA["games"]), ints(oB["games"])
            ta, tb_ = ints(oA["tbs"]), ints(oB["tbs"])
            m1 = mb_by_team.loc[(L.year, L.code, "1")]
            first = str(m1["file_first_server"] or "")
            one, two = ("A", "B") if mbt["A"] == "1" else ("B", "A")
            g1, g2 = (ga, gb) if one == "A" else (gb, ga)
            t1, t2 = (ta, tb_) if one == "A" else (tb_, ta)
            der = derive_service(g1, g2, t1, t2, first, gx.get((L.year, L.code), pd.DataFrame(columns=["server"])))
        for side in ("w", "l"):
            t = team_of[side]
            o = oA if t == "A" else oB
            opp_t = "B" if t == "A" else "A"
            rec = {"label": L.label, "year": L.year, "tour": L.tour, "round": L.round, "code": L.code, "rid": int(L.rid),
                   "source": L.source, "source_file": L.source_file, "source_row": L.source_row, "side": side,
                   "name": r["winner_name" if side == "w" else "loser_name"], "rg_name": f"{o['first_name']} {o['last_name']}",
                   "rg_id": o["player_id"], "rg_team": t, "rg_checks": bool(o["chk_all"]) and bool(
                       (oB if t == "A" else oA)["chk_all"]), "has_stats": bool(o["has_stats"])}
            for k in SRC:
                rec[f"raw_{k}"] = r[f"{side}_{SRC[k]}"]
            for k in EIGHT:
                rec[f"off_{k}"] = o[k] if o["has_stats"] else np.nan
            key, key_opp = (L.year, L.code, o["player_id"]), (L.year, L.code, (oB if t == "A" else oA)["player_id"])
            if key in mbx.index:
                m = mbx.loc[key]
                for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "sv_gms_reg_done",
                          "sv_gms_reg_open", "sv_gms_reg_all", "tb_first_served", "fault_spd_on_1", "fault_spd_on_2"):
                    rec[f"mb_{c}"] = m[f"mb_{c}"]
                for c in ("points", "dup_ids", "odd_points", "games_no_points", "games_no_points_reg",
                          "games_mixed_server", "tb_games", "first_server"):
                    rec[f"mbf_{c}"] = m[f"file_{c}"]
                rec["mb_team"] = m["team"]
                rec["mb_is_complete"] = m["is_complete"]
                if key_opp in mbx.index:
                    rec["mb_opp_svpt"] = mbx.loc[key_opp, "mb_svpt"]
            if key in ksx.index:
                q = ksx.loc[key]
                for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved", "bpcg"):
                    rec[f"ks_{c}"] = q[f"ks_{c}"]
                if key_opp in ksx.index:
                    rec["ks_opp_svpt"] = ksx.loc[key_opp, "ks_svpt"]
            if der:
                mine = mbt[t]
                rec["der_sv"] = der["der_sv1"] if mine == "1" else der["der_sv2"]
                rec["der_ok"] = der["der_ok"]
                rec["der_checked"] = der["der_checked"]
                rec["der_bad"] = der.get("der_bad", np.nan)
            out.append(rec)
    d = pd.DataFrame(out)
    d.to_parquet(WORK / "sides.parquet", index=False)
    print("sides:", d.groupby(["label", "year"]).size().to_dict())


if __name__ == "__main__":
    main()
