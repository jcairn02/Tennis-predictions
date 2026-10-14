"""R1-rederive (independent reviewer): read Sackmann's raw rows, link them to my parsed venue records, compare.

Inputs: my own tables from parse_sources.py (work/*.parquet) and Sackmann's raw CSVs
(data/raw/public_dump/sackmann_archive/{atp,wta}/*.csv, read with the csv module, rows numbered from 1 after the header;
cross-checked against the staged copies in data/dump/matches/sackmann_archive/, column _row).
No code or table of src/eda/rg_first_serve_recount/ is read.

Writes (data/studies/rg_first_serve_recount/review/R1-rederive/):
  work/sackmann_rows.parquet   the Sackmann rows in scope (RG 2019-2025 main + qualifying, AO 2025, Paris 2024)
  links_rg.csv                 every RG document linked to a Sackmann row (or not), with the evidence of the link
  links_ol.csv                 every Olympic unit linked to a Sackmann row (or not)
  links_ao.csv                 AO 2025 MatchBeats files linked to Sackmann rows (for claim C1)
  sides.csv                    one row per Sackmann side (w/l) of every linked row: Sackmann's eight counts, the
                               official record's, the second record's recount, the class
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/link_compare.py
"""
from __future__ import annotations

import csv
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
WORK = HERE / "work"
RAW_SACK = "data/raw/public_dump/sackmann_archive"
COUNTS = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
MINE = {"ace": "ace", "df": "df", "svpt": "svpt", "1stIn": "first_in", "1stWon": "first_won", "2ndWon": "second_won",
        "bpSaved": "bp_saved", "bpFaced": "bp_faced"}
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]


# ---------------------------------------------------------------------------------------------------------------
# Sackmann's raw rows
# ---------------------------------------------------------------------------------------------------------------
def read_raw_csv(rel: str) -> pd.DataFrame:
    with open(ROOT / rel, encoding="utf-8-sig", newline="") as fh:
        rd = csv.reader(fh)
        head = next(rd)
        rows = [r for r in rd]
    n = len(head)
    width_ok = [len(r) == n for r in rows]
    rows = [(r + [""] * n)[:n] for r in rows]
    df = pd.DataFrame(rows, columns=head)
    df["width_ok"] = width_ok
    df["source_file"] = rel
    df["source_row"] = np.arange(1, len(df) + 1)
    return df


def load_sackmann() -> pd.DataFrame:
    files = []
    for y in range(2019, 2026):
        files += [(f"{RAW_SACK}/atp/atp_matches_{y}.csv", "atp"), (f"{RAW_SACK}/atp/atp_matches_qual_chall_{y}.csv", "atp"),
                  (f"{RAW_SACK}/wta/wta_matches_{y}.csv", "wta"), (f"{RAW_SACK}/wta/wta_matches_qual_itf_{y}.csv", "wta")]
    out = []
    for rel, tour in files:
        df = read_raw_csv(rel)
        y = int(re.search(r"(\d{4})\.csv$", rel).group(1))
        keep = df["tourney_id"].str.fullmatch(rf"{y}-0*520")
        if y == 2025:   # AO 2025 for claim C1
            keep |= df["tourney_id"].str.fullmatch(r"2025-0*580")
        if y == 2024:
            keep |= df["tourney_name"].str.contains("Olympic", case=False)
        d = df[keep].copy()
        d["tour"], d["year"] = tour, y
        # cross-check against the staged copy (column _row)
        st = pd.read_parquet(ROOT / "data" / "dump" / "matches" / "sackmann_archive" / tour /
                             (Path(rel).stem + ".parquet"))
        st = st[st["_row"].isin(d["source_row"])].set_index("_row")
        for c in ["tourney_id", "round", "winner_name", "loser_name", "score"] + [f"{s}_{k}" for s in "wl" for k in COUNTS]:
            a = d.set_index("source_row")[c].fillna("").astype(str).str.strip()
            b = st[c].fillna("").astype(str).str.strip().reindex(a.index)
            if not a.eq(b).all():
                raise SystemExit(f"{rel}: raw CSV and staged copy differ on {c} ({(~a.eq(b)).sum()} rows)")
        if not st["_source_file"].eq(rel).all():
            raise SystemExit(f"{rel}: staged _source_file differs")
        out.append(d)
    s = pd.concat(out, ignore_index=True)
    s["event"] = np.where(s["tourney_id"].str.contains("-0*520$"), "RG",
                          np.where(s["tourney_id"].str.contains("-0*580$"), "AO", "OG"))
    for side in "wl":
        for k in COUNTS:
            s[f"{side}_{k}"] = pd.to_numeric(s[f"{side}_{k}"].str.strip().replace("", np.nan), errors="coerce")
    return s


# ---------------------------------------------------------------------------------------------------------------
# names and scores
# ---------------------------------------------------------------------------------------------------------------
def toks(name) -> frozenset:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    s = s.replace("ø", "o").replace("ł", "l").replace("đ", "d").replace("ß", "ss")
    return frozenset(t for t in re.sub(r"[^a-z]+", " ", s).split() if t)


def sim(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def sack_games(score: str) -> tuple[list[tuple[int, int]], str]:
    sets, tail = [], ""
    for tok in str(score or "").split():
        m = re.match(r"^(\d+)-(\d+)", tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2))))
        else:
            tail += tok + " "
    return sets, tail.strip()


def assign(cands_a: list, cands_b: list, score) -> list[tuple[int, int, float]]:
    """Maximum-total-similarity one-to-one assignment."""
    if not cands_a or not cands_b:
        return []
    m = np.array([[score(a, b) for b in cands_b] for a in cands_a])
    r, c = linear_sum_assignment(-m)
    return [(i, j, m[i, j]) for i, j in zip(r, c)]


# ---------------------------------------------------------------------------------------------------------------
# RG links
# ---------------------------------------------------------------------------------------------------------------
def link_rg(sack: pd.DataFrame, api: pd.DataFrame) -> pd.DataFrame:
    a = api.copy()
    a["tour"] = np.where(a["family"].isin(["SM", "QM"]), "atp", "wta")
    a["tok"] = [toks(f"{f} {l}") for f, l in zip(a["first_name"], a["last_name"])]
    a["name"] = a["first_name"].fillna("") + " " + a["last_name"].fillna("")
    m = a.pivot_table(index=["year", "code", "tour", "round_code"], columns="team",
                      values=["name", "player_id", "winner", "games", "end_cause", "country"], aggfunc="first")
    m.columns = [f"{x}_{t}" for x, t in m.columns]
    m = m.reset_index()
    tokmap = a.set_index(["year", "code", "team"])["tok"]
    out = []
    rg = sack[sack["event"].eq("RG")]
    for (y, tour, rnd), grp in m.groupby(["year", "tour", "round_code"]):
        srows = rg[(rg["year"].eq(y)) & rg["tour"].eq(tour) & rg["round"].eq(rnd)]
        ml = grp.to_dict("records")
        sl = srows.to_dict("records")
        def score(mm, ss):
            ta, tb = tokmap[(y, mm["code"], "A")], tokmap[(y, mm["code"], "B")]
            tw, tl = toks(ss["winner_name"]), toks(ss["loser_name"])
            return max(sim(ta, tw) + sim(tb, tl), sim(ta, tl) + sim(tb, tw))
        got = assign(ml, sl, score)
        used = set()
        for i, j, sc in got:
            mm, ss = ml[i], sl[j]
            used.add(i)
            ta, tb = tokmap[(y, mm["code"], "A")], tokmap[(y, mm["code"], "B")]
            tw, tl = toks(ss["winner_name"]), toks(ss["loser_name"])
            a_is_w = sim(ta, tw) + sim(tb, tl) >= sim(ta, tl) + sim(tb, tw)
            w_team = "A" if a_is_w else "B"
            l_team = "B" if a_is_w else "A"
            sw, sl_ = (sim(ta, tw), sim(tb, tl)) if a_is_w else (sim(tb, tw), sim(ta, tl))
            # score check: the RG winner's games per set against Sackmann's
            gw = [int(x) for x in str(mm[f"games_{w_team}"]).split(",") if x not in ("", "None")]
            gl = [int(x) for x in str(mm[f"games_{l_team}"]).split(",") if x not in ("", "None")]
            sets, tail = sack_games(ss["score"])
            out.append({"year": y, "code": mm["code"], "tour": tour, "round": rnd, "source_file": ss["source_file"],
                        "source_row": ss["source_row"], "winner_name": ss["winner_name"],
                        "loser_name": ss["loser_name"], "rg_w_team": w_team, "rg_w_name": mm[f"name_{w_team}"],
                        "rg_l_name": mm[f"name_{l_team}"], "sim_w": sw, "sim_l": sl_,
                        "rg_winner_flag_agrees": bool(mm[f"winner_{w_team}"]) and not bool(mm[f"winner_{l_team}"]),
                        "ioc_w": ss["winner_ioc"], "rg_ioc_w": mm[f"country_{w_team}"], "ioc_l": ss["loser_ioc"],
                        "rg_ioc_l": mm[f"country_{l_team}"],
                        "sack_score": ss["score"], "rg_games": " ".join(f"{p}-{q}" for p, q in zip(gw, gl)),
                        "games_agree": [(p, q) for p, q in zip(gw, gl)] == sets,
                        "rg_end_cause": (mm[f"end_cause_{w_team}"] or "") + "|" + (mm[f"end_cause_{l_team}"] or "")})
        for i, mm in enumerate(ml):
            if i not in used:
                out.append({"year": y, "code": mm["code"], "tour": tour, "round": rnd, "source_file": None})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------------------------------
# Olympic links
# ---------------------------------------------------------------------------------------------------------------
OL_ROUND = {"First Round": "R64", "Second Round": "R32", "Third Round": "R16", "Quarter-final": "QF",
            "Semi-final": "SF", "Gold Medal Match": "F", "Bronze Medal Match": "BR"}


def link_ol(sack: pd.DataFrame, ol: pd.DataFrame) -> pd.DataFrame:
    o = ol.copy()
    o["tour"] = np.where(o["gender"].eq("M"), "atp", "wta")
    o["round"] = o["round_desc"].map(OL_ROUND)
    o["tok"] = [toks(f"{g} {f}") for g, f in zip(o["given"], o["family"])]
    og = sack[sack["event"].eq("OG")]
    out = []
    for (tour, rnd), grp in o.groupby(["tour", "round"]):
        units = list(grp.groupby("unit"))
        srows = og[og["tour"].eq(tour) & og["round"].eq(rnd)].to_dict("records")
        def pair(u):
            g = u[1]
            w = g[g["wlt"].eq("W")]
            l = g[g["wlt"].eq("L")]
            return (w.iloc[0] if len(w) else None), (l.iloc[0] if len(l) else None)
        def score(u, ss):
            w, l = pair(u)
            if w is None or l is None:
                return 0.0
            return sim(w["tok"], toks(ss["winner_name"])) + sim(l["tok"], toks(ss["loser_name"]))
        got = assign(units, srows, score)
        used = set()
        for i, j, sc in got:
            u, ss = units[i], srows[j]
            used.add(i)
            w, l = pair(u)
            sets, tail = sack_games(ss["score"])
            fr = str(w["final_result"] or "")
            ol_sets = [(int(m.group(1)), int(m.group(2))) for m in
                       (re.match(r"^\s*(\d+)-(\d+)", s) for s in fr.split(",")) if m]
            out.append({"unit": u[0], "tour": tour, "round": rnd, "source_file": ss["source_file"],
                        "source_row": ss["source_row"], "winner_name": ss["winner_name"],
                        "loser_name": ss["loser_name"], "ol_w_athlete": w["athlete"], "ol_l_athlete": l["athlete"],
                        "ol_w_name": w["name"], "ol_l_name": l["name"],
                        "sim_w": sim(w["tok"], toks(ss["winner_name"])), "sim_l": sim(l["tok"], toks(ss["loser_name"])),
                        "ioc_w": ss["winner_ioc"], "ol_ioc_w": w["org"], "ioc_l": ss["loser_ioc"], "ol_ioc_l": l["org"],
                        "sack_score": ss["score"], "ol_final_result": fr, "games_agree": ol_sets == sets})
        for i, u in enumerate(units):
            if i not in used:
                out.append({"unit": u[0], "tour": tour, "round": rnd, "source_file": None})
    # Sackmann Olympic rows with no unit
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------------------------------
# AO 2025 links (claim C1)
# ---------------------------------------------------------------------------------------------------------------
AO_ROUND = {"7": "F", "6": "SF", "5": "QF", "4": "R16", "3": "R32", "2": "R64", "1": "R128"}
AO_QROUND = {"3": "Q3", "2": "Q2", "1": "Q1"}


def link_ao(sack: pd.DataFrame, mb: pd.DataFrame) -> pd.DataFrame:
    ao = mb[mb["slam"].eq("AO") & mb["mb_status"].eq("ok")].copy()
    ao["tour"] = np.where(ao["code"].str[0].eq("M"), "atp", "wta")
    ao["round"] = [(AO_QROUND if c[1] == "Q" else AO_ROUND)[c[2]] for c in ao["code"]]
    ao["tok"] = [toks(f"{f} {l}") for f, l in zip(ao["mb_first"], ao["mb_last"])]
    tokmap = ao.set_index(["code", "team"])["tok"]
    s = sack[sack["event"].eq("AO")]
    out = []
    for (tour, rnd), grp in ao.groupby(["tour", "round"]):
        codes = sorted(grp["code"].unique())
        srows = s[s["tour"].eq(tour) & s["round"].eq(rnd)].to_dict("records")
        def score(c, ss):
            t1, t2 = tokmap[(c, "1")], tokmap[(c, "2")]
            tw, tl = toks(ss["winner_name"]), toks(ss["loser_name"])
            return max(sim(t1, tw) + sim(t2, tl), sim(t1, tl) + sim(t2, tw))
        for i, j, sc in assign(codes, srows, score):
            c, ss = codes[i], srows[j]
            t1, t2 = tokmap[(c, "1")], tokmap[(c, "2")]
            tw, tl = toks(ss["winner_name"]), toks(ss["loser_name"])
            one_is_w = sim(t1, tw) + sim(t2, tl) >= sim(t1, tl) + sim(t2, tw)
            out.append({"code": c, "tour": tour, "round": rnd, "source_file": ss["source_file"],
                        "source_row": ss["source_row"], "winner_name": ss["winner_name"],
                        "loser_name": ss["loser_name"], "w_team": "1" if one_is_w else "2",
                        "sim": sc})
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------------------------------------------
# sides and classes
# ---------------------------------------------------------------------------------------------------------------
def classify(d: pd.DataFrame, pre: str) -> pd.Series:
    """Sackmann's side (s_*) against a record (pre_*): the class of the brief, computed my way."""
    diff = {k: d[f"s_{k}"] - d[f"{pre}{k}"] for k in EIGHT}
    split = (diff["first_in"] != 0) | (diff["first_won"] != 0) | (diff["second_won"] != 0)
    spw = (d["s_first_won"] + d["s_second_won"]) - (d[f"{pre}first_won"] + d[f"{pre}second_won"])
    points = (diff["svpt"] != 0) | (spw != 0)
    other = (diff["ace"] != 0) | (diff["df"] != 0) | (diff["bp_faced"] != 0) | (diff["bp_saved"] != 0)
    cls = np.select([d[f"s_svpt"].isna(), d[f"{pre}svpt"].isna(), points, split & ~other, split & other, other],
                    ["no_box", "no_record", "points", "split", "split_other", "other"], "equal")
    return pd.Series(cls, index=d.index)


def sides(sack: pd.DataFrame, links_rg: pd.DataFrame, links_ol: pd.DataFrame, api: pd.DataFrame, mb: pd.DataFrame,
          ks: pd.DataFrame, ol: pd.DataFrame, pbp: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sk = sack.set_index(["source_file", "source_row"])
    # RG
    apix = api.set_index(["year", "code", "team"])
    mbx = mb[mb["slam"].eq("RG") & mb["mb_status"].eq("ok")].set_index(["year", "code", "player_id"])
    ksx = ks[ks["ks_status"].eq("ok")].set_index(["year", "code", "player_id"]) if len(ks) else None
    for L in links_rg[links_rg["source_file"].notna()].itertuples():
        srow = sk.loc[(L.source_file, int(L.source_row))]
        for side, team in (("w", L.rg_w_team), ("l", "B" if L.rg_w_team == "A" else "A")):
            o = apix.loc[(L.year, L.code, team)]
            opp = apix.loc[(L.year, L.code, "B" if team == "A" else "A")]
            r = {"event": "RG", "year": L.year, "tour": L.tour, "round": L.round, "key": L.code,
                 "source_file": L.source_file, "source_row": L.source_row, "side": side,
                 "name": srow["winner_name" if side == "w" else "loser_name"],
                 "rec_name": f"{o['first_name']} {o['last_name']}", "rec_id": o["player_id"],
                 "rec_checks": bool(o["chk_all"]) and bool(opp["chk_all"]), "end_cause": L.rg_end_cause,
                 "games_agree": L.games_agree, "sim": L.sim_w if side == "w" else L.sim_l}
            for k, c in MINE.items():
                r[f"s_{c}"] = srow[f"{side}_{k}"]
                r[f"o_{c}"] = o[c] if o["has_stats"] else np.nan
            r["s_SvGms"] = srow[f"{side}_SvGms"]
            key = (L.year, L.code, o["player_id"])
            key_opp = (L.year, L.code, opp["player_id"])
            if key in mbx.index and key_opp in mbx.index:
                m, mo = mbx.loc[key], mbx.loc[key_opp]
                for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df"):
                    r[f"m_{c}"] = m[f"mb_{c}"]
                r["m_opp_svpt"] = mo["mb_svpt"]
            if ksx is not None and key in ksx.index and key_opp in ksx.index:
                q, qo = ksx.loc[key], ksx.loc[key_opp]
                for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved"):
                    r[f"k_{c}"] = q[f"ks_{c}"]
                r["k_opp_svpt"] = qo["ks_svpt"]
            rows.append(r)
    # Olympics
    olx = ol.set_index(["unit", "athlete"])
    pbx = pbp.set_index(["unit", "athlete"])
    for L in links_ol[links_ol["source_file"].notna()].itertuples():
        srow = sk.loc[(L.source_file, int(L.source_row))]
        for side, ath, oath in (("w", L.ol_w_athlete, L.ol_l_athlete), ("l", L.ol_l_athlete, L.ol_w_athlete)):
            o, opp = olx.loc[(L.unit, ath)], olx.loc[(L.unit, oath)]
            r = {"event": "OG", "year": 2024, "tour": L.tour, "round": L.round, "key": L.unit,
                 "source_file": L.source_file, "source_row": L.source_row, "side": side,
                 "name": srow["winner_name" if side == "w" else "loser_name"], "rec_name": o["name"], "rec_id": ath,
                 "rec_checks": bool(o["chk_all"]) and bool(opp["chk_all"]), "end_cause": "",
                 "games_agree": L.games_agree, "sim": L.sim_w if side == "w" else L.sim_l}
            for k, c in MINE.items():
                r[f"s_{c}"] = srow[f"{side}_{k}"]
                r[f"o_{c}"] = o[c]
            r["s_SvGms"] = srow[f"{side}_SvGms"]
            p, po = pbx.loc[(L.unit, ath)], pbx.loc[(L.unit, oath)]
            for c in ("svpt", "first_in", "first_won", "second_won", "ace", "df"):
                r[f"m_{c}"] = p[f"pbp_{c}"]
            r["m_opp_svpt"] = po["pbp_svpt"]
            rows.append(r)
    d = pd.DataFrame(rows)
    for c in EIGHT:
        d[f"s_{c}"] = pd.to_numeric(d[f"s_{c}"], errors="coerce")
        d[f"o_{c}"] = pd.to_numeric(d[f"o_{c}"], errors="coerce")
    d["cls"] = classify(d, "o_")
    d["d_first_in"] = d["s_first_in"] - d["o_first_in"]
    d["d_first_won"] = d["s_first_won"] - d["o_first_won"]
    d["d_second_won"] = d["s_second_won"] - d["o_second_won"]
    d["sign"] = np.select([d["d_first_in"] > 0, d["d_first_in"] < 0], ["+", "-"], "0")
    # second record complete for the row = same serve points for both players as the official record
    opp_o_svpt = d.groupby(["source_file", "source_row"])["o_svpt"].transform("sum") - d["o_svpt"]
    d["m_complete"] = d["m_svpt"].eq(d["o_svpt"]) & d["m_opp_svpt"].eq(opp_o_svpt)
    d["m_split_agrees"] = d["m_first_in"].eq(d["o_first_in"]) & d["m_first_won"].eq(d["o_first_won"]) & \
        d["m_second_won"].eq(d["o_second_won"])
    if "k_svpt" in d:
        d["k_complete"] = d["k_svpt"].eq(d["o_svpt"]) & d["k_opp_svpt"].eq(opp_o_svpt)
        d["k_split_agrees"] = d["k_first_in"].eq(d["o_first_in"]) & d["k_first_won"].eq(d["o_first_won"]) & \
            d["k_second_won"].eq(d["o_second_won"])
    # does the second record reproduce Sackmann's split instead (the other side of the dispute)?
    d["m_equals_sack_split"] = d["m_first_in"].eq(d["s_first_in"]) & d["m_first_won"].eq(d["s_first_won"]) & \
        d["m_second_won"].eq(d["s_second_won"])
    return d


def main() -> None:
    api = pd.read_parquet(WORK / "rg_api.parquet")
    mb = pd.read_parquet(WORK / "mb_points.parquet")
    ks = pd.read_parquet(WORK / "rg_ks25.parquet")
    ol = pd.read_parquet(WORK / "ol_stats.parquet")
    pbp = pd.read_parquet(WORK / "ol_pbp.parquet")
    sack = load_sackmann()
    sack.to_parquet(WORK / "sackmann_rows.parquet", index=False)
    print("sackmann rows", sack.groupby(["event", "year", "tour"]).size().to_dict())
    lr = link_rg(sack, api)
    lr.to_csv(HERE / "links_rg.csv", index=False)
    lo = link_ol(sack, ol)
    lo.to_csv(HERE / "links_ol.csv", index=False)
    la = link_ao(sack, mb)
    la.to_csv(HERE / "links_ao.csv", index=False)
    print("rg links", lr["source_file"].notna().sum(), "of", len(lr), "| ol links", lo["source_file"].notna().sum(),
          "of", len(lo), "| ao links", len(la))
    d = sides(sack, lr, lo, api, mb, ks, ol, pbp)
    d.to_csv(HERE / "sides.csv", index=False)
    print(d.groupby(["event", "year", "cls"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
