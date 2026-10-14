"""R2-skeptic: claim C1 with my own code. (a) AO 2025: the Infosys MatchBeats files (decrypted with the adapter's own
routine) recounted per player and linked to Sackmann's AO 2025 rows by tour, draw, round and names; where the point file
holds every serve point of the row, does the recount equal Sackmann's first serves in and points won? (b) the Olympic
play-by-play recount against the Olympic statistics on every side whose serve points agree.
Writes c1_check.json.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R2-skeptic/c1_check.py
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve().parent
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R2-skeptic"
SACK = ROOT / "data" / "raw" / "public_dump" / "sackmann_archive"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ao_round(code: str) -> tuple[str, str, str]:
    fam, r = code[:2], int(code[2])
    tour = "W" if fam[0] == "W" else "M"
    if fam[1] == "Q":
        return tour, "qual", {3: "Q3", 2: "Q2", 1: "Q1"}.get(r, "?")
    return tour, "main", {7: "F", 6: "SF", 5: "QF", 4: "R16", 3: "R32", 2: "R64", 1: "R128"}.get(r, "?")


def main() -> int:
    from src.ingest.point_sources import common as P
    from src.ingest.point_sources import infosys_slams as I
    lc = load("link_compare")
    rows = []
    for path in sorted((ROOT / "data" / "raw" / "point_sources" / "infosys_slams" / "AO" / "2025").glob("*/*.json.gz")):
        route, code = path.parts[-2], path.name.split(".")[0]
        blocks = I.blocks_of(route, P.read_json(path))
        if "mbData" not in blocks:
            continue
        try:
            doc = I.decrypt(blocks["mbData"])
        except Exception:      # noqa: BLE001
            continue
        if not isinstance(doc, dict) or not doc.get("setData"):
            continue
        pd_ = doc.get("playerData") or {}
        pts = [p for s in doc["setData"] for g in s.get("gameData") or [] for p in g.get("pointData") or []]
        for k in ("1", "2"):
            mine = [p for p in pts if str(p.get("server")) == k]
            f = [p for p in mine if str(p.get("serve")) == "1"]
            sec = [p for p in mine if str(p.get("serve")) == "2"]
            rows.append({"code": code, "slot": int(k),
                         "name": lc.fold(f"{pd_.get(f'tm{k}Ply1FirstName')} {pd_.get(f'tm{k}Ply1LastName')}"),
                         "svpt": len(mine), "first_in": len(f),
                         "first_won": sum(str(p.get("scorer")) == k for p in f),
                         "second_won": sum(str(p.get("scorer")) == k for p in sec)})
    mb = pd.DataFrame(rows)
    tr = mb["code"].map(ao_round)
    mb["tour"], mb["draw"], mb["round"] = tr.str[0], tr.str[1], tr.str[2]
    m = mb.pivot_table(index=["code", "tour", "draw", "round"], columns="slot", values="name", aggfunc="first") \
        .reset_index().rename(columns={1: "n1", 2: "n2"})
    m["year"], m["win1"] = 2025, None
    # Sackmann AO 2025
    recs = []
    for f in (SACK / "atp" / "atp_matches_2025.csv", SACK / "atp" / "atp_matches_qual_chall_2025.csv",
              SACK / "wta" / "wta_matches_2025.csv", SACK / "wta" / "wta_matches_qual_itf_2025.csv"):
        with open(f, encoding="utf-8", newline="") as fh:
            rr = list(csv.reader(fh))
        head = rr[0]
        for i, r in enumerate(rr[1:], 1):
            d = dict(zip(head, r))
            if d.get("tourney_name") == "Australian Open" or d.get("tourney_id", "").endswith("-580"):
                d.update({"source_file": f.name, "source_row": i, "tour": "M" if "atp" in f.name else "W"})
                recs.append(d)
    sk = pd.DataFrame(recs)
    sk["wn"], sk["ln"] = sk["winner_name"].map(lc.fold), sk["loser_name"].map(lc.fold)
    sk["draw"] = np.where(sk["round"].str.fullmatch(r"Q\d"), "qual", "main")
    sk["year"] = 2025
    lk = lc.link(sk, m, ["year", "tour", "draw", "round"], "code")
    sk = sk.merge(lk, on=["source_file", "source_row"])
    out_rows = []
    for r in sk[sk["code"].notna()].itertuples(index=False):
        for side in ("w", "l"):
            slot = (1 if r.orient == "12" else 2) if side == "w" else (2 if r.orient == "12" else 1)
            x = mb[(mb["code"] == r.code) & (mb["slot"] == slot)].iloc[0]
            g = {c: getattr(r, f"{side}_{c}") for c in ("svpt", "1stIn", "1stWon", "2ndWon")}
            if any(v in ("", None) for v in g.values()):
                continue
            out_rows.append({"code": r.code, "draw": r.draw, "side": side, "lscore": r.lscore,
                             "s_svpt": int(g["svpt"]), "s_first_in": int(g["1stIn"]), "s_first_won": int(g["1stWon"]),
                             "s_second_won": int(g["2ndWon"]), **{f"m_{c}": x[c] for c in
                                                                  ("svpt", "first_in", "first_won", "second_won")}})
    t = pd.DataFrame(out_rows)
    comp = t[t["s_svpt"].eq(t["m_svpt"])]
    res = {"ao_sackmann_rows": int(len(sk)), "ao_linked_rows": int(sk["code"].notna().sum()),
           "ao_sides_with_box": int(len(t)), "ao_complete_sides": int(len(comp))}
    for c in ("first_in", "first_won", "second_won"):
        res[f"ao_complete_equal_{c}"] = int(comp[f"s_{c}"].eq(comp[f"m_{c}"]).sum())
    res["ao_complete_by_draw"] = comp.groupby("draw").apply(
        lambda g: {"sides": len(g), "split_equal": int((g["s_first_in"].eq(g["m_first_in"]) & g["s_first_won"].eq(
            g["m_first_won"]) & g["s_second_won"].eq(g["m_second_won"])).sum())}).to_dict()
    res["ao_complete_unequal"] = comp[~(comp["s_first_in"].eq(comp["m_first_in"]) & comp["s_first_won"].eq(
        comp["m_first_won"]) & comp["s_second_won"].eq(comp["m_second_won"]))].to_dict("records")
    # (b) the Olympic play-by-play against the Olympic statistics
    s = pd.read_parquet(OUT / "my_sides.parquet")
    o = s[s["event"].eq("OG") & s["og_svpt"].notna()]
    oc = o[o["ogp_svpt"].eq(o["og_svpt"])]
    res["og_sides"] = int(len(o))
    res["og_complete_sides"] = int(len(oc))
    for c in ("first_in", "first_won", "second_won", "ace", "df"):
        res[f"og_complete_equal_{c}"] = int(oc[f"ogp_{c}"].eq(oc[f"og_{c}"]).sum())
    (OUT / "c1_check.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
