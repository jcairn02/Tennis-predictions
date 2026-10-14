"""Sackmann's service games at the Infosys Slams against the Slam's own point record (the lead's check of 9 Oct 2026 of
round-2 reviewer R2's finding; docs/studies/rg_first_serve_recount/README.md § 8.6).

The truth for a completed match: the score's alternation of serve from the player the Slam's point record (MatchBeats)
has serving the first point, tiebreak games not counted (whole_box.score_sv_gms). Each match is equal, swapped (the
two players' counts exchanged; "= winner served first" where they are what the score gives if the winner served
first), other, or incomplete.

Writes data/studies/rg_first_serve_recount/followup/service_game_swaps.csv (one row per match: event, year,
match_id, class) and prints the counts by event and era.
Usage: ./python.sh src/eda/rg_first_serve_recount/service_game_swaps.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.rg_first_serve_recount import link as L  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402
from src.eda.rg_first_serve_recount import whole_box as WB  # noqa: E402
from src.ingest.point_sources import infosys_slams as I  # noqa: E402


def classify(g):
    """g: one match's two rows with side w/l, have (Sackmann's), der (truth), score."""
    w, l = g[g.side.eq("w")].iloc[0], g[g.side.eq("l")].iloc[0]
    if pd.isna(w.have) or pd.isna(l.have) or pd.isna(w.der) or pd.isna(l.der):
        return "incomplete"
    if w.have == w.der and l.have == l.der:
        return "equal"
    wf = WB.score_sv_gms(w.score, True)
    if w.der != l.der and w.have == l.der and l.have == w.der:
        return "swapped (= winner served first)" if (w.have, l.have) == wf else "swapped"
    if (w.have, l.have) == wf:
        return "as if the winner served first"
    return "other"


# --- Roland Garros 2019-2025, from the follow-up's own linked rows
rows = WB.official_sv_gms(WB.linked())
r = rows[rows["raw_side"].isin(["w", "l"]) & rows["status"].eq("completed")].copy()
r = r.assign(side=r["raw_side"], have=r["raw_sv_gms"], der=r["der_sv_gms"])
r = r[r.groupby("match_id")["side"].transform("nunique").eq(2)]
out = r.groupby("match_id").apply(classify).rename("cls").reset_index()
out = out.merge(r.drop_duplicates("match_id")[["match_id", "year"]], on="match_id")
out["era"] = np.where(out.year <= 2021, "2019-2021", np.where(out.year <= 2025, "2022-2025", "2026"))
print("RG, completed matches with both counts and a known first server:")
print(pd.crosstab(out.cls, out.era))
sw = out[out.cls.str.startswith("swapped") & out.year.le(2021)]
print("RG 2019-21 swapped:", len(sw), "| of them = winner served first:", int(sw.cls.str.contains("winner").sum()))

# --- Australian Open 2024-2025: MatchBeats against Stage 0's AO rows
m = pd.read_parquet(S.S0 / "stage0_matches.parquet")
p = pd.read_parquet(S.S0 / "stage0_match_players.parquet")
m = m[m["tournament_name"].eq("Australian Open") & m["year"].between(2024, 2025)].copy()
s0 = p.merge(m[["match_id", "year", "tour", "qualifying", "round", "score", "status"]], on="match_id")
s0["tour"] = s0["tour"].map({"atp": "M", "wta": "W"})
s0["draw"] = np.where(s0["qualifying"], "qual", "main")
s0["name_key"] = s0["player_name"].map(S.nkey)
s0["event"] = "AO"
s0m = L.stage0_matches(s0)
mb = S.mb("AO")
rounds = I.round_lookup()
mb["round"] = mb["match_id"].map(lambda c: rounds.get(("AO", c)))
fam = mb["match_id"].str[:2]
mb["tour"] = np.where(fam.str[0].eq("W"), "W", "M")
mb["draw"] = np.where(fam.str[1].eq("Q"), "qual", "main")
mm = mb.pivot_table(index=["year", "match_id", "tour", "draw", "round"], columns="slot", values="name_key",
                    aggfunc="first").reset_index().rename(columns={1: "name1", 2: "name2", "match_id": "code"})
mm["event"] = "AO"
placed = L.place(mm, s0m, ["event", "year", "tour", "draw", "round"], "name1", "name2")
placed = placed[placed["match_id"].notna()]
s0i = s0m.set_index("match_id")
recs = []
for x in placed.itertuples():
    for slot, pid in ((1 if x.a_is == "1" else 2, s0i.loc[x.match_id, "pid_a"]),
                      (2 if x.a_is == "1" else 1, s0i.loc[x.match_id, "pid_b"])):
        b = mb[(mb.year.eq(x.year)) & (mb.match_id.eq(x.code)) & (mb.slot.eq(slot))].iloc[0]
        y = s0[(s0.match_id.eq(x.match_id)) & (s0.player_id.eq(pid))].iloc[0]
        recs.append({"match_id": x.match_id, "year": x.year, "won": bool(y["won"]), "score": y["score"],
                     "status": y["status"], "have": y["sv_gms"], "served_first": bool(b["served_first"])})
ao = pd.DataFrame(recs)
ao = ao[ao.status.eq("completed")]
ao["side"] = np.where(ao.won, "w", "l")
first_w = ao[ao.served_first & ao.won].groupby("match_id").size()
known = ao.groupby("match_id")["served_first"].transform("sum").eq(1)
ao = ao[known]
ao["der"] = [WB.score_sv_gms(s, mid in first_w.index)[0 if side == "w" else 1]
             for s, mid, side in zip(ao.score, ao.match_id, ao.side)]
ao = ao[ao.groupby("match_id")["side"].transform("nunique").eq(2)]
ao_out = ao.groupby("match_id").apply(classify).rename("cls").reset_index()
print("\nAO 2024-25 (Stage 0's service games against the score's alternation from MatchBeats' first server):")
print(ao_out.cls.value_counts().to_string())
out["event"] = "RG"
ao_out = ao_out.merge(ao.drop_duplicates("match_id")[["match_id", "year"]], on="match_id")
ao_out["event"], ao_out["era"] = "AO", ao_out["year"].astype(str)
both = pd.concat([out[["event", "year", "era", "match_id", "cls"]], ao_out[["event", "year", "era", "match_id", "cls"]]],
                 ignore_index=True)
both.to_csv(WB.OUT / "service_game_swaps.csv", index=False)
print(pd.crosstab([both.event, both.era], both.cls).to_string())
