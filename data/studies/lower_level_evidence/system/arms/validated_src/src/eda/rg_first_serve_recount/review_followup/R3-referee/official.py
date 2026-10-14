"""R3-referee (follow-up), step 1: RG's own records parsed here from the raw files, linked to the raw rows, and my own
eighteen values per match.

Records (read verbatim; nothing of the lead's code is used):
  * RG's statistics: data/raw/point_sources/rolandgarros/matches/<year>/<code>.json.gz (rolandgarros.com's match API),
    2019-2026: per team the name, RG id, winner flag, sets (games, tiebreak points), end cause; "first serve" in/served,
    "win on 1st serve" won/in, "win on 2nd serve" won/(served - in), aces, double faults, the opponent's "break points
    won" (won/opportunities -> faced, saved), "receiving points won", "total points won"; the record's own checks.
  * RG's MatchBeats: data/raw/point_sources/infosys_slams/RG/<year>/<route>/<code>.json.gz, decrypted with the
    adapter's decrypt and blocks_of (the site's own step), recounted per server: serve points, first serves in (serve
    1), points won on each serve, aces (A), double faults (DF); service games = games whose points one player served
    and whose isTieBreak is false (Sackmann's convention), tiebreak games, non-tiebreak games with two servers
    (anomalies); break points faced = points with isBrkPt on the player's serve, saved = those the server won.
  * RG's Infosys key statistics (staged, 2025-2026), as a further second record.
Link: each raw row of an RG tournament id (Sackmann 2019-2026, TML 2026) to the RG document of the same year, tour,
draw and round whose two players carry the row's winner's and loser's names (either order); ambiguous or weak links
are listed. Orientation is by name; RG's winner flag and the sets are checked against the row's score.
My values: RG's eight counts for the row's winner and loser; service games from MatchBeats where it holds every point
of both players (its serve points equal the statistics') and the pair fits the score (B5), else the row's own where
they fit, else blank (the rule the brief describes, recomputed here); plus diagnostics of the alternatives.

Writes official_rows.csv (one row per linked raw row, w/l side by side) and official_summary.json into
data/studies/rg_first_serve_recount/followup/review/R3-referee/.
Usage: ./python.sh src/eda/rg_first_serve_recount/review_followup/R3-referee/official.py
"""
from __future__ import annotations

import gzip
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3f as F  # noqa: E402

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402

MAIN = {1: "R128", 2: "R64", 3: "R32", 4: "R16", 5: "QF", 6: "SF", 7: "F"}
QUAL = {1: "Q1", 2: "Q2", 3: "Q3"}
COUNTS8 = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]


# ------------------------------------------------------------------------------------------------ RG's statistics
def rg_docs() -> pd.DataFrame:
    rows = []
    for f in sorted((F.RAW / "rolandgarros" / "matches").glob("*/*.json.gz")):
        year, code = int(f.parent.name), f.name.split(".")[0]
        try:
            doc = json.load(gzip.open(f))
        except Exception as err:
            rows.append({"year": year, "code": code, "parse_error": str(err)})
            continue
        m = doc.get("match") or {}
        md = m.get("matchData") or {}
        st = (doc.get("matchStatisticsSection") or {}).get("matchStatistics") or {}
        rec = {}
        for t, o in (("A", "B"), ("B", "A")):
            team = m.get(f"team{t}") or {}
            p = team["players"][0] if team.get("players") else {}
            v = (lambda k, side=t: (st.get(k) or {}).get(f"team{side}Value"))
            fi, sv = F.frac(v("firstServeRateIn"))
            fw, fwd = F.frac(v("winRateOnFirstServe"))
            sw, swd = F.frac(v("winRateOnSecondServe"))
            obw, obo = F.frac(v("breakPoint", o))
            rw, rd = F.frac(v("returnPoints"))
            num = (lambda k: int(v(k)) if v(k) not in (None, "") else None)
            rec[t] = {"name": f"{p.get('firstName', '')} {p.get('lastName', '')}".strip(), "rg_id": p.get("id"),
                      "winner": bool(team.get("winner")), "end_cause": team.get("endCause") or "",
                      "sets": [(s.get("score"), s.get("tieBreak")) for s in team.get("sets") or []],
                      "ace": num("aces"), "df": num("doubleFaults"), "svpt": sv, "first_in": fi, "first_won": fw,
                      "second_won": sw, "first_won_den": fwd, "second_won_den": swd, "bp_faced": obo,
                      "bp_saved": None if obo is None else obo - obw, "ret_won": rw, "ret_den": rd,
                      "total_won": num("totalPointsWon")}
        for t, o in (("A", "B"), ("B", "A")):
            x, y = rec[t], rec[o]
            x["consistent"] = bool(x["svpt"] is not None and y["svpt"] is not None and x["first_won_den"] == x["first_in"]
                                   and x["second_won_den"] == x["svpt"] - x["first_in"] and x["ret_den"] == y["svpt"]
                                   and x["total_won"] == x["first_won"] + x["second_won"] + x["ret_won"])
        out = {"year": year, "code": code, "type": md.get("type"), "rnd": md.get("round"),
               "round_label": md.get("roundLabel"), "status": md.get("status"), "court": md.get("courtName"),
               "minutes": md.get("durationInMinutes")}
        for t in ("A", "B"):
            for k, val in rec[t].items():
                out[f"{t}_{k}"] = val
        rows.append(out)
    d = pd.DataFrame(rows)
    d["tour"] = np.where(d["type"].astype(str).str[1].eq("D"), "wta", "atp")
    d["draw"] = np.where(d["type"].astype(str).str[0].eq("Q"), "qual", "main")
    d["round"] = [(QUAL if dr == "qual" else MAIN).get(int(r)) if pd.notna(r) else None
                  for dr, r in zip(d["draw"], d["rnd"])]
    d["consistent_both"] = d["A_consistent"].astype(bool) & d["B_consistent"].astype(bool)
    return d


# ------------------------------------------------------------------------------------------------ MatchBeats
def mb_doc(year: int, code: str):
    base = F.RAW / "infosys_slams" / "RG" / str(year)
    for route in ("match-beats", "match-centre", "match-beats-api"):
        f = base / route / f"{code}.json.gz"
        if not f.exists():
            continue
        blocks = I.blocks_of(route, json.load(gzip.open(f)))
        if "mbData" not in blocks:
            continue
        doc = I.decrypt(blocks["mbData"])
        if isinstance(doc, dict) and doc.get("setData"):
            return route, doc
    return None, None


def mb_counts(doc: dict) -> dict:
    games = []
    for s in doc.get("setData") or []:
        for g in s.get("gameData") or []:
            pts = g.get("pointData") or []
            games.append((s.get("set"), g.get("game"), bool(g.get("isTieBreak")), pts))
    pdat = doc.get("playerData") or {}
    out = {"complete": doc.get("isMatchComplete"), "status": doc.get("matchStatus"), "winner_slot": doc.get("matchWinner"),
           "points": sum(len(p) for *_, p in games), "games": len(games),
           "tb_games": sum(1 for _, _, tb, p in games if tb or len({str(x.get("server")) for x in p}) > 1),
           "mixed_non_tb": sum(1 for _, _, tb, p in games if not tb and len({str(x.get("server")) for x in p}) > 1),
           "empty_games": sum(1 for *_, p in games if not p)}
    for k in ("1", "2"):
        mine = [x for *_, p in games for x in p if str(x.get("server")) == k]
        out[f"p{k}_name"] = f"{pdat.get(f'tm{k}Ply1FirstName') or ''} {pdat.get(f'tm{k}Ply1LastName') or ''}".strip()
        out[f"p{k}_svpt"] = len(mine)
        out[f"p{k}_first_in"] = sum(str(x.get("serve")) == "1" for x in mine)
        out[f"p{k}_first_won"] = sum(str(x.get("serve")) == "1" and str(x.get("scorer")) == k for x in mine)
        out[f"p{k}_second_won"] = sum(str(x.get("serve")) == "2" and str(x.get("scorer")) == k for x in mine)
        out[f"p{k}_serve_other"] = sum(str(x.get("serve")) not in ("1", "2") for x in mine)
        out[f"p{k}_ace"] = sum(x.get("result") == "A" for x in mine)
        out[f"p{k}_df"] = sum(x.get("result") == "DF" for x in mine)
        out[f"p{k}_bp_faced"] = sum(bool(x.get("isBrkPt")) for x in mine)
        out[f"p{k}_bp_saved"] = sum(bool(x.get("isBrkPt")) and str(x.get("scorer")) == k for x in mine)
        out[f"p{k}_sv_gms"] = sum(1 for _, _, tb, p in games
                                  if not tb and p and {str(x.get("server")) for x in p} == {k})
        out[f"p{k}_sv_gms_incl_tb"] = sum(1 for _, _, tb, p in games if p and str(p[0].get("server")) == k)
    return out


def mb_all(codes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in codes.itertuples():
        route, doc = mb_doc(int(r.year), r.code)
        if doc is None:
            continue
        rows.append({"year": int(r.year), "code": r.code, "mb_route": route, **{f"mb_{k}": v for k, v in mb_counts(doc).items()}})
    return pd.DataFrame(rows)


def keystats() -> pd.DataFrame:
    ks = pd.read_parquet(F.DUMP / "infosys_slams" / "keystats.parquet")
    ks = ks[ks["slam"].eq("RG") & ks["set_key"].eq("set0")]
    rows = []
    for (yr, mid), g in ks.groupby(["year", "match_id"]):
        st = {r["name"]: (r["player1"], r["player2"]) for r in g.to_dict("records")}
        if "First Serve" not in st:
            continue
        rec = {"year": int(yr), "code": mid}
        for j, k in ((0, "1"), (1, "2")):
            fi, sv = F.frac(st["First Serve"][j])
            bw, bo = F.frac(st.get("Break Points Won", (None, None))[1 - j])
            rec.update({f"ks{k}_svpt": sv, f"ks{k}_first_in": fi,
                        f"ks{k}_first_won": F.frac(st.get("Win On 1st Serve", (None, None))[j])[0],
                        f"ks{k}_second_won": F.frac(st.get("Win On 2nd Serve", (None, None))[j])[0],
                        f"ks{k}_ace": pd.to_numeric(st.get("Aces", (None, None))[j], errors="coerce"),
                        f"ks{k}_df": pd.to_numeric(st.get("Double Faults", (None, None))[j], errors="coerce"),
                        f"ks{k}_bp_faced": bo, f"ks{k}_bp_saved": None if bo is None else bo - bw})
        rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ the link
def score_names(a: str, b: str) -> float:
    """name_ok, and 0.5 where it finds nothing but the two names' letters are 80% alike (a transliteration:
    Anastasiya Soboleva / Anastasiia Sobolieva)."""
    s = F.name_ok(a, b)
    if s == 0 and SequenceMatcher(None, "".join(F.fold(a)), "".join(F.fold(b))).ratio() >= 0.8:
        return 0.5
    return float(s)


def link(raw: pd.DataFrame, docs: pd.DataFrame) -> pd.DataFrame:
    groups = {k: g for k, g in docs.groupby(["year", "tour", "draw", "round"])}
    out = []
    for r in raw.rename(columns={"_source_file": "sfile", "_row": "srow"}).itertuples():
        draw = "qual" if r.qualifying else "main"
        cand = groups.get((int(r.season), r.tour, draw, r.round))
        best, second = None, None
        if cand is not None:
            for d in cand.itertuples():
                for w_team in ("A", "B"):
                    l_team = "B" if w_team == "A" else "A"
                    a = score_names(getattr(d, f"{w_team}_name"), r.winner_name)
                    b = score_names(getattr(d, f"{l_team}_name"), r.loser_name)
                    if min(a, b) == 0.5 and max(a, b) < 2:     # a transliteration only beside an exact name
                        continue
                    sc = (min(a, b), a + b)
                    if sc[0] < 0.5:
                        continue
                    if best is None or sc > best[0]:
                        second, best = best, (sc, d.code, w_team)
                    elif second is None or sc > second[0]:
                        second = (sc, d.code, w_team)
        rec = {"source": r.source, "source_file": r.sfile, "source_row": int(r.srow), "season": int(r.season),
               "tour": r.tour, "draw": draw, "round": r.round, "tid": r.tid, "winner_name": r.winner_name,
               "loser_name": r.loser_name, "wkey": r.wkey, "lkey": r.lkey, "score": r.score}
        if best is None:
            out.append({**rec, "code": None, "link": "none"})
            continue
        tie = second is not None and second[0] == best[0] and second[1] != best[1]
        out.append({**rec, "code": best[1], "w_team": best[2], "link_min": best[0][0], "link_sum": best[0][1],
                    "link": "tie" if tie else "names", "second_code": second[1] if second else None,
                    "second_min": second[0][0] if second else None})
    return pd.DataFrame(out)


def score_sets(score: str) -> list[tuple[int, int, int]]:
    sets, _ = B.tokens_of(str(score or ""))
    return [(a, b, tb) for a, b, tb, br in sets if not br]


def main() -> int:
    raw = pd.read_parquet(F.OUT / "sub_raw.parquet")
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("int64")
    raw["season"] = pd.to_numeric(raw["season"]).astype("int64")
    rgr = raw[raw["tid"].str.fullmatch(r"20(19|2[0-6])-520") & (raw["source"].eq("sackmann")
                                                                | (raw["source"].eq("tml") & raw["season"].eq(2026)))].copy()
    docs = rg_docs()
    mb = mb_all(docs[["year", "code"]])
    ks = keystats()
    L = link(rgr, docs)
    d = L.merge(docs, left_on=["season", "code"], right_on=["year", "code"], how="left", suffixes=("", "_doc"))
    d = d.merge(mb, left_on=["season", "code"], right_on=["year", "code"], how="left", suffixes=("", "_mb"))
    d = d.merge(ks, left_on=["season", "code"], right_on=["year", "code"], how="left", suffixes=("", "_ks"))
    rk = raw.set_index(["_source_file", "_row"])
    out = []
    for r in d.to_dict("records"):
        x = rk.loc[(r["source_file"], r["source_row"])]
        rec = {k: r.get(k) for k in ["source", "source_file", "source_row", "season", "tour", "draw", "round", "tid",
                                       "winner_name", "loser_name", "wkey", "lkey", "score", "code", "link", "link_min",
                                       "link_sum", "second_code", "second_min", "status", "court", "minutes",
                                       "consistent_both", "mb_route", "mb_complete", "mb_status", "mb_points",
                                       "mb_games", "mb_tb_games", "mb_mixed_non_tb", "mb_empty_games"]}
        for s, who in (("w", "winner"), ("l", "loser")):
            for c, col in F.NINE.items():
                v = pd.to_numeric(str(x[f"{s}_{col}"]).strip() if x[f"{s}_{col}"] is not None else "", errors="coerce")
                rec[f"raw_{s}_{c}"] = v
        if r.get("code") is None or pd.isna(r.get("code")):
            out.append(rec)
            continue
        wt = r["w_team"]
        lt = "B" if wt == "A" else "A"
        rec.update({"rg_w_name": r[f"{wt}_name"], "rg_l_name": r[f"{lt}_name"], "rg_w_id": r[f"{wt}_rg_id"],
                    "rg_l_id": r[f"{lt}_rg_id"], "rg_w_is_winner": bool(r[f"{wt}_winner"]),
                    "rg_l_is_winner": bool(r[f"{lt}_winner"]), "rg_end_cause": (r[f"{wt}_end_cause"] or "") +
                    (r[f"{lt}_end_cause"] or "")})
        rg_sets = [(a[0], b[0], a[1], b[1]) for a, b in zip(r[f"{wt}_sets"], r[f"{lt}_sets"])]
        rec["rg_sets"] = " ".join(f"{a}-{b}" + (f"({min(ta, tb)})" if ta is not None and tb is not None else "")
                                  for a, b, ta, tb in rg_sets)
        ss = score_sets(r["score"])
        rec["score_sets_equal"] = [(a, b) for a, b, _ in ss] == [(int(a) if a is not None else -1,
                                                                  int(b) if b is not None else -1) for a, b, _, _ in rg_sets]
        for s, t in (("w", wt), ("l", lt)):
            for c in COUNTS8:
                rec[f"rg_{s}_{c}"] = r[f"{t}_{c}"]
        # MatchBeats slots paired with the teams by name
        if pd.notna(r.get("mb_route")):
            s1 = (F.name_ok(r["mb_p1_name"], r[f"{wt}_name"]), F.name_ok(r["mb_p1_name"], r[f"{lt}_name"]))
            w_slot = "1" if s1[0] > s1[1] else "2" if s1[1] > s1[0] else None
            rec["mb_w_slot"] = w_slot
            if w_slot:
                l_slot = "2" if w_slot == "1" else "1"
                for s, k in (("w", w_slot), ("l", l_slot)):
                    for c in ["svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved",
                              "sv_gms", "sv_gms_incl_tb", "serve_other"]:
                        rec[f"mb_{s}_{c}"] = r[f"mb_p{k}_{c}"]
                if pd.notna(r.get("ks1_svpt")) or pd.notna(r.get("ks2_svpt")):
                    for s, k in (("w", w_slot), ("l", l_slot)):
                        for c in ["svpt", "first_in", "first_won", "second_won", "ace", "df", "bp_faced", "bp_saved"]:
                            rec[f"ks_{s}_{c}"] = r.get(f"ks{k}_{c}")
        out.append(rec)
    o = pd.DataFrame(out)
    # ---------------------------------------------------------------- the score's games, B5, my service games
    cnt = o["score"].fillna("").map(lambda s: B.score_counts(str(s), False))
    o["games"] = cnt.map(lambda c: c[2] + c[3])
    o["std_tb"] = cnt.map(lambda c: c[6])
    o["status_parsed"] = o["score"].fillna("").map(lambda s: B.STATUS[B.status_of(*B.tokens_of(str(s)))])

    def fits(sw, sl):
        tot = sw + sl
        return ((tot - (o["games"] - o["std_tb"])).abs().le(1) | (tot - o["games"]).abs().le(1))
    o["mb_complete_both"] = o["mb_w_svpt"].eq(o["rg_w_svpt"]) & o["mb_l_svpt"].eq(o["rg_l_svpt"])
    o["mb_sv_fits"] = fits(o["mb_w_sv_gms"], o["mb_l_sv_gms"])
    o["mb_sv_exact"] = (o["mb_w_sv_gms"] + o["mb_l_sv_gms"]).eq(o["games"] - o["std_tb"]) \
        & (o["mb_w_sv_gms"] - o["mb_l_sv_gms"]).abs().le(1)
    o["raw_sv_fits"] = fits(o["raw_w_sv_gms"], o["raw_l_sv_gms"])
    o["raw_sv_exact"] = (o["raw_w_sv_gms"] + o["raw_l_sv_gms"]).eq(o["games"] - o["std_tb"]) \
        & (o["raw_w_sv_gms"] - o["raw_l_sv_gms"]).abs().le(1)
    use_mb = o["mb_complete_both"] & o["mb_sv_fits"]
    use_raw = ~use_mb & o["raw_sv_fits"] & o["raw_w_sv_gms"].notna() & o["raw_l_sv_gms"].notna() \
        & ~(o["raw_w_sv_gms"].eq(0) & o["rg_w_svpt"].gt(0)) & ~(o["raw_l_sv_gms"].eq(0) & o["rg_l_svpt"].gt(0))
    o["my_sv_from"] = np.select([use_mb, use_raw], ["matchbeats", "row"], "none")
    for s in ("w", "l"):
        o[f"my_{s}_sv_gms"] = np.where(use_mb, o[f"mb_{s}_sv_gms"], np.where(use_raw, o[f"raw_{s}_sv_gms"], np.nan))
        for c in COUNTS8:
            o[f"my_{s}_{c}"] = o[f"rg_{s}_{c}"]
    o.to_csv(F.OUT / "official_rows.csv", index=False)
    smry = {"raw_rows": int(len(o)), "by_source_season": o.groupby(["source", "season"]).size().rename("rows").reset_index()
            .astype(str).to_dict("records"),
            "link": o["link"].value_counts().to_dict(),
            "link_min_by_link": o.groupby(["link", "link_min"]).size().rename("rows").reset_index().astype(str)
            .to_dict("records"),
            "rg_winner_flag_equals_row_winner": int((o["rg_w_is_winner"].eq(True) & o["rg_l_is_winner"].eq(False)).sum()),
            "score_sets_equal": int(o["score_sets_equal"].eq(True).sum()),
            "rg_docs": int(len(docs)), "rg_docs_by_year_type": docs.groupby(["year", "type"]).size().rename("docs")
            .reset_index().astype(str).to_dict("records"),
            "rg_docs_consistent": int(docs["consistent_both"].sum()),
            "mb_docs": int(len(mb)), "mb_routes": mb.groupby(["year", "mb_route"]).size().rename("docs").reset_index()
            .astype(str).to_dict("records"),
            "my_sv_from": o.loc[o["code"].notna(), "my_sv_from"].value_counts().to_dict()}
    (F.OUT / "official_summary.json").write_text(json.dumps(smry, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(smry, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
