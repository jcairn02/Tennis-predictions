"""R1-rederive: a light referee check with the Match Charting Project (hand-charted, noisy) on my sides table.

For each side of RG 2019-2025 and Paris 2024 with an MCP chart of the same match (year, event, round, both players by
name tokens), compare MCP's first serves in with the official record's and Sackmann's. Prints, per class and sign,
how often MCP is nearer the official value, nearer Sackmann's, or equally near. Writes mcp_sides.csv.
Run: ./python.sh src/eda/rg_first_serve_recount/review/R1-rederive/mcp_check.py
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "review" / "R1-rederive"
MCP = ROOT / "data" / "dump" / "points" / "match_charting_project"


def toks(name) -> frozenset:
    s = unicodedata.normalize("NFKD", str(name or ""))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower()
    return frozenset(t for t in re.sub(r"[^a-z]+", " ", s).split() if t)


def sim(a, b) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 0.0


def main() -> None:
    pd.set_option("display.width", 250)
    frames = []
    for g in ("m", "w"):
        meta = pd.read_parquet(MCP / "metadata" / f"charting-{g}-matches.parquet")
        ov = pd.read_parquet(MCP / "stats" / f"charting-{g}-stats-Overview.parquet")
        ov = ov[ov["set"].astype(str).eq("Total")]
        meta = meta[meta["Tournament"].astype(str).str.contains("Roland Garros$|Olympics", regex=True)]
        meta = meta[~meta["Tournament"].astype(str).str.contains("Junior")]
        meta["year"] = meta["Date"].astype(str).str[:4].astype(int)
        meta = meta[meta["year"].between(2019, 2025)]
        meta["event"] = np.where(meta["Tournament"].str.contains("Olymp"), "OG", "RG")
        meta["tour"] = "atp" if g == "m" else "wta"
        j = ov.merge(meta[["match_id", "year", "event", "tour", "Round", "Player 1", "Player 2"]], on="match_id")
        frames.append(j)
    mcp = pd.concat(frames, ignore_index=True)
    for c in ("serve_pts", "first_in", "first_won", "second_won", "aces", "dfs"):
        mcp[c] = pd.to_numeric(mcp[c], errors="coerce")
    mcp["ptok"] = mcp["player"].map(toks)
    mcp["pair"] = [frozenset([toks(a), toks(b)]) for a, b in zip(mcp["Player 1"], mcp["Player 2"])]
    d = pd.read_csv(HERE / "sides.csv", keep_default_na=False, na_values=[""], dtype={"rec_id": str})
    sack = pd.read_parquet(HERE / "work" / "sackmann_rows.parquet").set_index(["source_file", "source_row"])
    out = []
    for r in d.itertuples():
        srow = sack.loc[(r.source_file, r.source_row)]
        me, opp = toks(r.name), toks(srow["loser_name"] if r.side == "w" else srow["winner_name"])
        cand = mcp[(mcp["year"].eq(r.year)) & mcp["event"].eq(r.event) & mcp["tour"].eq(r.tour)
                   & mcp["Round"].astype(str).eq(r.round)]
        best = None
        for c in cand.itertuples():
            pa, pb = list(c.pair) if len(c.pair) == 2 else (list(c.pair) * 2)[:2]
            s = max(sim(me, pa) + sim(opp, pb), sim(me, pb) + sim(opp, pa))
            if s >= 1.5 and sim(me, c.ptok) >= 0.5 and (best is None or s > best[0]):
                best = (s, c)
        if best is None:
            continue
        c = best[1]
        out.append({"event": r.event, "year": r.year, "key": r.key, "side": r.side, "name": r.name, "cls": r.cls,
                    "sign": r.sign, "s_svpt": r.s_svpt, "o_svpt": r.o_svpt, "mcp_svpt": c.serve_pts,
                    "s_first_in": r.s_first_in, "o_first_in": r.o_first_in, "mcp_first_in": c.first_in,
                    "s_first_won": r.s_first_won, "o_first_won": r.o_first_won, "mcp_first_won": c.first_won,
                    "mcp_match": c.match_id})
    m = pd.DataFrame(out)
    m.to_csv(HERE / "mcp_sides.csv", index=False)
    # compare first-serve-in rates (MCP's serve points can differ): nearer by the count, among sides where MCP's serve
    # points equal the official's (+-1)
    m["near"] = np.select([(m["mcp_first_in"] - m["o_first_in"]).abs() < (m["mcp_first_in"] - m["s_first_in"]).abs(),
                           (m["mcp_first_in"] - m["o_first_in"]).abs() > (m["mcp_first_in"] - m["s_first_in"]).abs()],
                          ["official", "sackmann"], "same")
    ok = (m["mcp_svpt"] - m["o_svpt"]).abs().le(1)
    m["lab"] = np.where(m["cls"].isin(["split", "split_other"]), m["cls"] + m["sign"], m["cls"])
    print("MCP charts linked to sides:", len(m), "| with serve points within 1 of the official:", int(ok.sum()))
    print(pd.crosstab([m.loc[ok, "event"], m.loc[ok, "lab"]], m.loc[ok, "near"]))
    eq = m[ok & m["cls"].eq("equal")]
    print("control (equal sides): MCP first serves in equal to the agreed value on",
          int(eq["mcp_first_in"].eq(eq["o_first_in"]).sum()), "of", len(eq))
    ex = m[ok & m["cls"].isin(["split", "split_other"])]
    print("disputed: MCP equals official", int(ex["mcp_first_in"].eq(ex["o_first_in"]).sum()), "| equals Sackmann",
          int(ex["mcp_first_in"].eq(ex["s_first_in"]).sum()), "of", len(ex))
    print(ex[ex["sign"].ne("+")][["event", "year", "key", "side", "name", "sign", "s_svpt", "o_svpt", "mcp_svpt",
                                  "s_first_in", "o_first_in", "mcp_first_in", "s_first_won", "o_first_won",
                                  "mcp_first_won"]].to_string())


if __name__ == "__main__":
    main()
