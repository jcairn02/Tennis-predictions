"""Link Sackmann's WTA rows (main and qual/ITF files) to WTA API matches, per player, and measure exact agreement of
the nine counts. Used by F2, F3b and as the measure of whether the WTA API counts what Sackmann counts.

Linking (my own): Sackmann tourney_id 'YYYY-<n>' -> WTA API event <n> of year YYYY; within the event the two players
must match by surname key (the API surname key equals the last word(s) of Sackmann's name key, or the full keys match),
and qualifying rounds go to draw 'Q', the rest to 'M'. A Sackmann row matching more than one API match is dropped.
Writes wta_api_links_<years>.parquet (one row per Sackmann match, with both players' counts from both sources aligned
by player) and prints agreement.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402


def name_match(sack_key: str, api_full: str, api_last: str) -> bool:
    if not sack_key:
        return False
    if sack_key == api_full:
        return True
    if api_last and (sack_key.endswith(" " + api_last) or sack_key == api_last):
        return True
    # compound surnames written differently: every word of the API surname appears in Sackmann's key
    w = set(sack_key.split())
    return bool(api_last) and all(x in w for x in api_last.split())


def link_year(year: int) -> pd.DataFrame:
    files = [f"wta_matches_{year}.parquet", f"wta_matches_qual_itf_{year}.parquet"]
    s = pd.concat([R.sack("wta", f) for f in files if (R.SACK / "wta" / f).exists()], ignore_index=True)
    s["event"] = s["tourney_id"].str.split("-").str[-1]
    s["is_q"] = s["round"].str.upper().str.match(r"^Q\d")
    s["wk"], s["lk"] = s["winner_name"].map(R.nkey), s["loser_name"].map(R.nkey)
    a = R.wta_api(year)
    a_by_event = {e: g for e, g in a.groupby("event")}
    rows = []
    for r in s.to_dict("records"):
        g = a_by_event.get(r["event"])
        if g is None:
            continue
        g = g[g["draw"].eq("Q" if r["is_q"] else "M")]
        hits = []
        for x in g.to_dict("records"):
            if name_match(r["wk"], x["kA"], x["lkA"]) and name_match(r["lk"], x["kB"], x["lkB"]):
                hits.append((x, "A", "B"))
            elif name_match(r["wk"], x["kB"], x["lkB"]) and name_match(r["lk"], x["kA"], x["lkA"]):
                hits.append((x, "B", "A"))
        if len(hits) != 1:
            continue
        x, ws, ls = hits[0]
        api_winner = {"2": "A", "3": "B", "4": "A", "5": "B", "6": "A", "7": "B"}.get(x["winner_code"], "")
        row = {"_source_file": r["_source_file"], "_row": r["_row"], "tourney_id": r["tourney_id"],
               "tourney_name": r["tourney_name"], "tdate": r["tdate"], "round": r["round"], "score": r["score"],
               "winner_name": r["winner_name"], "loser_name": r["loser_name"], "winner_id": r["winner_id"],
               "loser_id": r["loser_id"], "event": r["event"], "wmid": x["wmid"], "api_result": x["result"],
               "api_score": x["score"], "api_winner_is_sack_winner": api_winner == ws if api_winner else np.nan}
        for side, api_side in (("w", ws), ("l", ls)):
            for b in R.BOX:
                row[f"s_{side}_{b}"] = r[f"{side}_{b}"]
                row[f"a_{side}_{b}"] = x[f"{api_side}_{b}"]
        rows.append(row)
    return pd.DataFrame(rows)


def agreement(d: pd.DataFrame, label: str) -> pd.Series:
    out = {"label": label, "matches": len(d)}
    for b in R.BOX:
        e = []
        for side in ("w", "l"):
            e.append(d[f"s_{side}_{b}"].eq(d[f"a_{side}_{b}"]))
        out[b] = float(pd.concat(e).mean())
    allc = np.ones(len(d), dtype=bool)
    for side in ("w", "l"):
        for b in R.BOX:
            allc &= d[f"s_{side}_{b}"].eq(d[f"a_{side}_{b}"]).to_numpy()
    out["all_18_counts"] = float(allc.mean()) if len(d) else np.nan
    allc8 = np.ones(len(d), dtype=bool)
    for side in ("w", "l"):
        for b in R.BOX:
            if b == "sv_gms":
                continue
            allc8 &= d[f"s_{side}_{b}"].eq(d[f"a_{side}_{b}"]).to_numpy()
    out["all_16_no_svgms"] = float(allc8.mean()) if len(d) else np.nan
    return pd.Series(out)


if __name__ == "__main__":
    years = [int(y) for y in (sys.argv[1:] or ["2021", "2022"])]
    frames = [link_year(y) for y in years]
    d = pd.concat(frames, ignore_index=True)
    d["has_box"] = d["s_w_svpt"].gt(0) & d["s_l_svpt"].gt(0)
    tag = "_".join(map(str, years))
    d.to_parquet(R.OUT / f"wta_api_links_{tag}.parquet", index=False)
    print("linked Sackmann rows:", len(d), " with a Sackmann box:", int(d["has_box"].sum()))
    pd.set_option("display.width", 250)
    db = d[d["has_box"]]
    print(agreement(db, "all linked with box").to_string())
