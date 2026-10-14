"""F2: per-match verdicts for the 88 matches, from x20_f2.py's evidence (f2_matches_raw.csv, f2_referee_rows.csv).

Rules (A3-referee):
  confirm (referee)   an independent record holds the match and each player's counts equal the EXCHANGED box (most
                      counts exact, the as-recorded attribution clearly worse); the exchanged box passes B0-B9; the
                      recorded winner is the record's winner or advanced in the draw.
  confirm (internal)  no independent record, but the as-recorded box is the exact mirror of the score: the identity
                      gives each player the OTHER player's games, off by |delta| >= 3 games (one miscounted break or
                      service game cannot do that); B != 0 and D != 0, so neither an exchange of the service games
                      alone nor of the break-point counts alone explains it; the exchange makes the recorded winner
                      win more points; the recorded winner advanced; the exchanged box passes B0-B9.
  reject              the record says the box is as recorded (the exchange would corrupt it), the record is unclear,
                      or there is no record and the internal evidence is ambiguous.
Writes f2_matches.csv (all 88, verdict + reason) and f2_scope.csv (the confirmed matches, both player rows).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402

o = pd.read_csv(rc.OUT / "f2_matches_raw.csv")
# The AO 2025 official point-by-point (Infosys, data/dump/points/infosys_slams/points.parquet, counted in x50_f5.pbp)
# holds two of the 88 (checked by hand in this review, numbers in the reason): both have the box as recorded and only
# the service games exchanged.
AO25_PBP = {
    "atp|2025-580|Q2|atp:106426|atp:111513": "ao_official_pbp:as_recorded (Garin 86 serve points, 3 aces, 55 first in, "
    "14 service games; Djere 74, 7 aces, 50, 15: the aces follow the recorded attribution, only the service games are "
    "exchanged in Sackmann)",
    "wta|2025-580|R128|wta:201611|wta:215020": "ao_official_pbp:as_recorded (Blinkova 95 serve points, 0 aces, 4 double "
    "faults, 60 first in, 14 service games; Saville 88, 4, 5, 64, 15: as recorded, service games exchanged)"}
for mid, txt in AO25_PBP.items():
    cur = o.loc[o["match_id"] == mid, "referees"].fillna("").iloc[0]
    o.loc[o["match_id"] == mid, "referees"] = (cur + ";" if cur else "") + txt
u = pd.read_csv(rc.OUT / "f2_referee_rows.csv")
a = rc.wta_api_totals()[["tournament_id", "year", "wmatch", "result", "pk", "ok", "name"]]


def surname(n: str) -> str:
    ws = rc.name_key(n).split()
    return max(ws, key=len) if ws else ""


def api_winner_ok(row) -> str:
    """The WTA API's result string ('X d Y ...') names the recorded winner?"""
    m = re.match(r"^\d{4}-(\d+)$", str(row["match_id"]).split("|")[1])
    if not m:
        return ""
    x = a[(a["tournament_id"] == m.group(1)) & (a["year"] == str(row["year"]))]
    ws, ls = surname(row["winner"]), surname(row["loser"])
    for res in x["result"].dropna().unique():
        r = rc.name_key(res.split(" d ")[0]) if " d " in res else ""
        rl = rc.name_key(res.split(" d ")[1]) if " d " in res else ""
        if ws and ls and ((ws in r and ls in rl) or (ls in r and ws in rl)):
            return "yes" if ws in r else "no"
    return ""


verdicts, reasons = [], []
for _, r in o.iterrows():
    refs_ = str(r["referees"]) if pd.notna(r["referees"]) else ""
    says = dict(re.findall(r"(\w+):(exchange|as_recorded|unclear)", refs_))
    delta_w = None
    exch = [k for k, v in says.items() if v == "exchange"]
    asrec = [k for k, v in says.items() if v == "as_recorded"]
    win = api_winner_ok(r) if "wta_api" in says else ""
    winner_ok = r["winner_plays_later"] or win == "yes"
    B, D = r["B_breaks_diff"], r["D_svgms_diff"]
    delta = 2 * B - D
    if exch and not asrec:
        if r["exch_passes_B0_B9"] and winner_ok:
            v = "confirm"
            why = (f"independent record says exchange: {refs_}; exchanged box passes B0-B9; recorded winner "
                   f"{'is the record winner' if win == 'yes' else 'advanced'}")
            if not r["exch_identity_both"]:
                why += ("; residual: after the exchange one player's service games are one short of the score "
                        "(Sackmann's own count; the record's other counts agree)")
        else:
            v, why = "reject", f"record says exchange but checks fail (B0-B9 {r['exch_passes_B0_B9']}, winner ok {winner_ok})"
    elif asrec:
        v = "reject"
        why = (f"independent record says the box is AS RECORDED: {refs_}; the exchange would corrupt it "
               f"(B={B:g}: the identity miss is the service-game counts, not the box)")
    elif refs_:
        v, why = "reject", f"independent record unclear: {refs_}"
    else:
        strong = (abs(delta) >= 3 and B != 0 and D != 0 and r["exch_identity_both"] and r["exch_passes_B0_B9"]
                  and r["winner_plays_later"] and r["loser_pts_rec"] > r["winner_pts_rec"])
        if strong:
            v = "confirm"
            why = (f"no independent record; internal: as recorded the identity gives each player the other's games "
                   f"(off by {abs(delta):g}), B={B:g}, D={D:g} (no partial exchange explains it), exchanged identity "
                   f"exact for both, points {r['winner_pts_rec']:g}-{r['loser_pts_rec']:g} become "
                   f"{r['loser_pts_rec']:g}-{r['winner_pts_rec']:g}, min-points rule as recorded "
                   f"{'violated' if not r['min_points_feasible_rec'] else 'met'}, recorded winner advanced; the same pattern "
                   f"holds in 18 refereed matches and the independent record confirmed the exchange in all 18")
        else:
            bits = []
            if B == 0:
                bits.append("B=0: an exchange of the service games alone fits the identity equally (and the "
                            "independent records of six such matches show exactly that)")
            if D == 0:
                bits.append("D=0: an exchange of the break-point counts alone fits equally")
            if abs(delta) < 3 and B != 0:
                bits.append(f"as-recorded identity off by only {abs(delta):g} game(s): one miscounted break fits too")
            if not r["exch_identity_both"]:
                bits.append("exchanged box still fails the games identity")
            if not r["winner_plays_later"]:
                bits.append("no later round to confirm the recorded winner (final / team tie)")
            if r["loser_pts_rec"] <= r["winner_pts_rec"]:
                bits.append(f"as recorded the winner already wins more points ({r['winner_pts_rec']:g}-"
                            f"{r['loser_pts_rec']:g})")
            if "read_reversed" in str(r.get("score_flag", "")) or str(r["score"]).startswith("1-6 2-6"):
                bits.append("score written from the loser's side and the box as recorded gives the recorded winner 3 games: the raw row is consistent with the recorded winner LOSING, so the winner label, not the box, may be wrong")
            v, why = "reject", "no independent record; " + "; ".join(bits)
    verdicts.append(v)
    reasons.append(why)
o["verdict"], o["reason"] = verdicts, reasons
o["referee_used"] = o["referees"].fillna("none")
cols = ["match_id", "tour", "year", "tournament", "round", "score", "winner", "winner_id", "loser", "loser_id",
        "_source_file", "_row", "verdict", "referee_used", "reason", "exch_passes_B0_B9", "exch_identity_both",
        "B_breaks_diff", "D_svgms_diff", "winner_pts_rec", "loser_pts_rec", "min_points_feasible_rec",
        "winner_plays_later", "tml"]
o[cols].to_csv(rc.OUT / "f2_matches.csv", index=False)
print(o["verdict"].value_counts().to_string())
print(o.groupby(["verdict", o["referee_used"].ne("none")]).size().to_string())
pd.set_option("display.width", 250)
pd.set_option("display.max_colwidth", 200)
pd.set_option("display.max_rows", 200)
print(o[o["verdict"].eq("reject")][["tournament", "year", "round", "winner", "loser", "reason"]].to_string())
print(o[o["verdict"].eq("confirm") & o["referee_used"].eq("none")][["tournament", "year", "round", "winner", "loser",
                                                                    "reason"]].to_string())
# scope rows: both players of the confirmed matches, with the side each holds in Sackmann's raw row
raw = {}
for f in sorted(set(o["_source_file"])):
    tour = "atp" if "/atp/" in f else "wta"
    name = f.split("/")[-1].replace(".csv", ".parquet")
    t = pd.read_parquet(rc.SACK / tour / name)
    raw[f] = t.set_index("_row")
sc = []
for _, r in o[o["verdict"].eq("confirm")].iterrows():
    rr = raw[r["_source_file"]].loc[int(r["_row"])]
    tour = r["tour"]
    for who, oth in (("winner", "loser"), ("loser", "winner")):
        pid = r[f"{who}_id"]
        side = "w" if f"{tour}:{rr['winner_id']}" == pid else ("l" if f"{tour}:{rr['loser_id']}" == pid else "?")
        sc.append({"match_id": r["match_id"], "player_id": pid, "player_name": r[who],
                   "takes_counts_of": r[oth], "_source_file": r["_source_file"], "_row": r["_row"],
                   "raw_side": side, "raw_svpt_now": rr[f"{side}_svpt"] if side != "?" else None,
                   "operation": "exchange all nine counts (w_* <-> l_*) of this raw row"})
pd.DataFrame(sc).to_csv(rc.OUT / "f2_scope.csv", index=False)
print("confirmed matches:", o["verdict"].eq("confirm").sum(), "scope rows:", len(sc))
