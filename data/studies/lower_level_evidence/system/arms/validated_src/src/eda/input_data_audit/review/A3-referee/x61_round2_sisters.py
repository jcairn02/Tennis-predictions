"""Round 2: the F2x matches between players who share a surname. Sackmann's raw counts against the WTA API's rows,
joined by FULL first and last name (never by surname), plus the API's seeds and player ids, printed side by side."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
E = pd.read_csv(rc.OUT / "round2_evidence.csv")
cand = pd.read_csv(rc.ROOT / "data/studies/input_data_audit/fixes/round2_A_candidates.csv")
sis = ["Birmingham|R16", "Acapulco|R32", "Auckland|R16", "Hua Hin|R32", "Wuhan|R32", "Madrid|R128", "s Hertogenbosch|R32",
       "Birmingham|Q1", "Oeiras 125 Indoor 2|R16"]
api_ms = pd.concat([rc.rd(rc.WTA / "matches" / f"{y}.parquet") for y in range(2019, 2027)], ignore_index=True)
st = pd.concat([rc.rd(rc.WTA / "stats" / f"{y}.parquet") for y in range(2019, 2027)], ignore_index=True)
st = st[st["setnum"].astype(str).eq("0")]
for _, c in cand[cand["cand"].eq("F2x")].iterrows():
    if f"{c['tournament_name']}|{c['round']}" not in sis:
        continue
    tour = "wta"
    name = c["source_file"].split("/")[-1].replace(".csv", ".parquet")
    t = pd.read_parquet(rc.SACK / tour / name)
    rr = t[t["_row"] == int(c["source_row"])].iloc[0]
    yr = str(c["tournament_date"])[:4]
    ln = rr["winner_name"].split()[-1]
    x = api_ms[(api_ms["year"].astype(str) == yr) & api_ms["match_id"].astype(str).str[:2].isin(["LS", "RS"])
               & api_ms["PlayerNameLastA"].astype(str).str.contains(ln) & api_ms["PlayerNameLastB"].astype(str).str.contains(ln)]
    print(f"\n===== {c['tournament_name']} {yr} {c['round']}: Sackmann {rr['winner_name']} (id {rr['winner_id']}) d. "
          f"{rr['loser_name']} (id {rr['loser_id']}) {rr['score']}")
    print("Sackmann w:", {b: rr[f'w_{rc.SRC[b]}'] for b in rc.BOX})
    print("Sackmann l:", {b: rr[f'l_{rc.SRC[b]}'] for b in rc.BOX})
    for _, a in x.iterrows():
        s = st[(st["tournament_id"].astype(str) == str(a["tournament_id"])) & (st["year"].astype(str) == yr)
               & (st["match_id"] == a["match_id"])]
        print(f"  API {a['tournament_id']}/{a['match_id']} round {a['RoundID']}: A = {a['PlayerNameFirstA']} {a['PlayerNameLastA']} "
              f"(id {a['PlayerIDA']}, seed {a['SeedA']}), B = {a['PlayerNameFirstB']} {a['PlayerNameLastB']} "
              f"(id {a['PlayerIDB']}, seed {a['SeedB']}); {a['ResultString']}")
        if len(s):
            s = s.iloc[0]
            for side, o in (("a", "b"), ("b", "a")):
                n = lambda col: pd.to_numeric(s[col], errors="coerce")
                box = {"ace": n(f"aces{side}"), "df": n(f"dblflt{side}"), "svpt": n(f"totservplayed{side}"),
                       "first_in": n(f"ptsplayed1stserv{side}"), "first_won": n(f"ptswon1stserv{side}"),
                       "second_won": n(f"ptstotwonserv{side}") - n(f"ptswon1stserv{side}"),
                       "sv_gms": n(f"servgamesplayed{side}"), "bp_saved": n(f"breakptsplayed{o}") - n(f"breakptsconv{o}"),
                       "bp_faced": n(f"breakptsplayed{o}")}
                print(f"    API side {side.upper()}:", box)
