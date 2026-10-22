"""Part F, step 5: hand checks of the readers. For random gap matches played before the seal, each price this part
uses is traced back to its staged row, and side A is identified by name from Stage 0's snapshot:

    tennis-data   the staged workbook row (Stage 1's file and position): Winner/Loser names, PSW/PSL, BFEW/BFEL,
                  B365W/L, AvgW/L, MaxW/L
    OddsTrader    books_lines.parquet (book 8 BetOnline, book 130 Bet105): each side's decimal price and stamp, and
                  events.parquet's home/away names
    Polymarket    the sharp benchmark's row (winner's 30-minute price, its market) and the raw minute price history of
                  that market (the last point before the listed start minus 30 minutes, within the hour)
    BetOnline's opening (odds_psx.py's join) and Polymarket at 60 minutes (odds_score.py's join) the same way

Each check prints the raw row beside the table's value so it can be read by eye, and records whether the prices agree
and whether the name of the side the price was given to is side A's. Per-match prices go to hand_checks.parquet
(gitignored); hand_checks.json (tracked) holds only the keys and the flags.
Run: ./python.sh src/eda/source_reconciliation/odds_checks.py
"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.odds_sources import common as OC  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import odds_common as O  # noqa: E402

SEED = 20261016
K = 5
PM = C.DUMP / "odds" / "polymarket"


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return "".join(ch if ch.isalpha() or ch == " " else " " for ch in s).strip()


def surname_in(full_a: str, other: str) -> bool:
    """A's last name (Stage 0's full name) appears in the other source's name for that side."""
    parts = norm(full_a).split()
    return bool(parts) and any(p in norm(other).split() for p in parts[-2:] if len(p) > 2)


def names_a() -> pd.Series:
    _, p = C.stage0(columns_m=["match_id"], columns_p=["match_id", "side", "player_name"])
    a = p[p["side"] == "A"]
    return pd.Series(a["player_name"].to_numpy(), index=a["match_id"].astype(str).to_numpy())


def sample(df: pd.DataFrame, mask: np.ndarray, k: int = K, salt: int = 0) -> pd.DataFrame:
    idx = np.flatnonzero(mask)
    rng = np.random.default_rng(SEED + salt)
    return df.iloc[np.sort(rng.choice(idx, size=min(k, len(idx)), replace=False))]


def tennis_data(df, base, A, s1, salt) -> list[dict]:
    rows = []
    for r in sample(df, base & np.isfinite(df["p_bfe"].to_numpy(float)) & np.isfinite(df["p_avg"].to_numpy(float)),
                    salt=salt).itertuples():
        s = s1.loc[r.match_id]
        f = pd.read_parquet(ROOT / s["td_file"])
        raw = f.iloc[int(s["td_row"])]
        a_is_w = surname_in(A[r.match_id], raw["Winner"])
        a_is_l = surname_in(A[r.match_id], raw["Loser"])
        rec = {"source": "tennis-data", "match_id": r.match_id, "td_date": str(r.td_date.date()),
               "a_name_stage0": A[r.match_id], "td_winner": raw["Winner"], "td_loser": raw["Loser"],
               "staged_file": s["td_file"], "staged_position": int(s["td_row"]),
               "a_named_as": "winner" if a_is_w and not a_is_l else "loser" if a_is_l and not a_is_w else "unclear"}
        ok = True
        for book, (w, l) in {"ps": ("PSW", "PSL"), "bfe": ("BFEW", "BFEL"), "b365": ("B365W", "B365L"),
                             "avg": ("AvgW", "AvgL"), "max": ("MaxW", "MaxL")}.items():
            dw, dl = pd.to_numeric(raw.get(w), errors="coerce"), pd.to_numeric(raw.get(l), errors="coerce")
            ta, tb = getattr(r, f"{book}_a"), getattr(r, f"{book}_b")
            if rec["a_named_as"] == "winner":
                ra, rb = dw, dl
            elif rec["a_named_as"] == "loser":
                ra, rb = dl, dw
            else:
                ra = rb = np.nan
            rec[f"{book}_table_a_b"] = [None if pd.isna(ta) else float(ta), None if pd.isna(tb) else float(tb)]
            rec[f"{book}_raw_a_b"] = [None if pd.isna(ra) else float(ra), None if pd.isna(rb) else float(rb)]
            same = (pd.isna(ta) and pd.isna(tb)) or (np.isclose(ta, ra) and np.isclose(tb, rb))
            rec[f"{book}_agrees"] = bool(same)
            ok &= bool(same) or pd.isna(ta)
        rec["agrees"] = bool(ok and rec["a_named_as"] != "unclear")
        rows.append(rec)
    return rows


def oddstrader(df, base, A, raw_t, books, events, paid: int, name: str, salt: int) -> list[dict]:
    col = f"ot{paid}"
    rows = []
    for r in sample(df, base & np.isfinite(df[f"p_{col}"].to_numpy(float)), salt=salt).itertuples():
        t = raw_t.loc[r.match_id]
        eid = int(r.eid)
        ev = events.loc[eid]
        lines = books[(books["eid"] == eid) & (books["paid"] == paid) & (books["kind"] == "last")]
        home = lines[lines["partid"] == ev["home_partid"]]
        away = lines[lines["partid"] == ev["away_partid"]]
        a_home = surname_in(A[r.match_id], f"{ev['home_first']} {ev['home_last']}")
        a_away = surname_in(A[r.match_id], f"{ev['away_first']} {ev['away_last']}")
        side = "home" if a_home and not a_away else "away" if a_away and not a_home else "unclear"
        pa = (home if side == "home" else away)["pri"].astype(float).tolist()
        pb = (away if side == "home" else home)["pri"].astype(float).tolist()
        ta, tb = float(t[f"{col}_a"]), float(t[f"{col}_b"])
        agrees = side != "unclear" and len(pa) == 1 and len(pb) == 1 and np.isclose(pa[0], ta) and np.isclose(pb[0], tb)
        rows.append({"source": f"oddstrader {name}", "match_id": r.match_id, "td_date": str(r.td_date.date()),
                     "eid": eid, "a_name_stage0": A[r.match_id],
                     "home": f"{ev['home_first']} {ev['home_last']}", "away": f"{ev['away_first']} {ev['away_last']}",
                     "a_is": side, "table_a_b": [ta, tb], "raw_a_b": [pa, pb],
                     "stamp_utc": (home["tim_utc"].tolist() + away["tim_utc"].tolist())[:1],
                     "listed_utc": ev["dt_utc"], "after_listed_min": float(getattr(r, f"after_{col}_min")),
                     "agrees": bool(agrees)})
    return rows


def polymarket(df, base, A, s1, sb, salt) -> list[dict]:
    rows = []
    key = ["tour", "td_date", "td_winner", "td_loser"]
    for r in sample(df, base & np.isfinite(df["p_pm"].to_numpy(float)), salt=salt).itertuples():
        s = s1.loc[r.match_id]
        k = sb[(sb["tour"] == r.tour) & (sb["date"] == pd.Timestamp(s["td_date"]).normalize()) &
               (sb["winner"] == s["td_winner"]) & (sb["loser"] == s["td_loser"])]
        if len(k) != 1:
            rows.append({"source": "polymarket", "match_id": r.match_id, "agrees": False, "note": f"{len(k)} rows"})
            continue
        k = k.iloc[0]
        a_is_w = surname_in(A[r.match_id], s["td_winner"]) and not surname_in(A[r.match_id], s["td_loser"])
        a_is_l = surname_in(A[r.match_id], s["td_loser"]) and not surname_in(A[r.match_id], s["td_winner"])
        # the raw minute history of the market's first outcome: last point before start - 30 min, within the hour
        cut = float(k["pm_start_ts"]) - 30 * 60
        pts = []
        for path in sorted((PM / "price_history").glob("*/*.parquet")):
            h = pd.read_parquet(path, columns=["condition_id", "t", "p"], filters=[("condition_id", "==",
                                                                                  k["condition_id"])])
            if len(h):
                pts.append(h)
        h = pd.concat(pts) if pts else pd.DataFrame(columns=["t", "p"])
        h = h[(h["t"] < cut) & (h["t"] >= cut - 3600)].sort_values("t")
        p0 = float(h["p"].iloc[-1]) if len(h) else np.nan
        pw = p0 if int(k["winner_outcome"]) == 0 else 1 - p0
        pa_raw = pw if a_is_w else (1 - pw if a_is_l else np.nan)
        agrees = bool(np.isclose(pa_raw, r.p_pm)) and (a_is_w or a_is_l)
        rows.append({"source": "polymarket 30 min", "match_id": r.match_id, "td_date": str(r.td_date.date()),
                     "a_name_stage0": A[r.match_id], "td_winner": s["td_winner"], "td_loser": s["td_loser"],
                     "market": k["pm_title"], "condition_id": k["condition_id"], "winner_outcome": int(k["winner_outcome"]),
                     "raw_outcome0_price_at_cut": p0, "raw_points_in_hour": int(len(h)),
                     "a_is": "winner" if a_is_w else "loser" if a_is_l else "unclear",
                     "table_p_a": float(r.p_pm), "raw_p_a": pa_raw, "agrees": agrees})
    return rows


def joins(df, base, A, salt) -> list[dict]:
    """BetOnline's opening (odds_psx.betonline_open) and Polymarket 60 min (odds_score.polymarket_60) against their
    staged rows."""
    from src.eda.source_reconciliation import odds_psx as PS
    from src.eda.source_reconciliation import odds_score as SC

    raw = pd.read_parquet(O.TABLE, columns=["match_id", "ot8_a", "ot8_b"])
    raw["match_id"] = raw["match_id"].astype(str)
    bolo, _ = PS.betonline_open(df.drop(columns=["ot8_a", "ot8_b"]).assign(ot8_a=raw["ot8_a"].to_numpy(),
                                                                          ot8_b=raw["ot8_b"].to_numpy()))
    bm = pd.read_parquet(O.BOL_MATCHES).drop_duplicates("eid").set_index("eid")
    out = []
    x = df.assign(p_bolo=bolo["p_bolo"].to_numpy())
    for r in sample(x, base & np.isfinite(x["p_bolo"].to_numpy(float)), salt=salt).itertuples():
        b = bm.loc[int(r.eid)]
        a_home = surname_in(A[r.match_id], f"{b['home_first']} {b['home_last']}")
        a_away = surname_in(A[r.match_id], f"{b['away_first']} {b['away_last']}")
        oa = b["mw_open_home"] if a_home and not a_away else b["mw_open_away"] if a_away and not a_home else np.nan
        ob = b["mw_open_away"] if a_home and not a_away else b["mw_open_home"] if a_away and not a_home else np.nan
        da, db = PS.american_to_decimal([oa])[0], PS.american_to_decimal([ob])[0]
        p = float(OC.devig(da, db))
        out.append({"source": "betonline opening (join)", "match_id": r.match_id, "eid": int(r.eid),
                    "a_name_stage0": A[r.match_id], "home": f"{b['home_first']} {b['home_last']}",
                    "away": f"{b['away_first']} {b['away_last']}", "raw_open_american_a_b": [oa, ob],
                    "table_p_a": float(r.p_bolo), "raw_p_a": p, "agrees": bool(np.isclose(p, r.p_bolo))})
    y = O.attach_y(df)
    pm60 = SC.polymarket_60(df, y)
    sb = pd.read_parquet(O.SHARP, columns=["tour", "date", "winner", "loser", "pw_pm_m60"])
    s1 = pd.read_parquet(O.STAGE1, columns=["match_id", "td_date", "td_winner", "td_loser"])
    s1["match_id"] = s1["match_id"].astype(str)
    s1 = s1.set_index("match_id")
    x = df.assign(p_pm60=pm60)
    for r in sample(x, base & np.isfinite(x["p_pm60"].to_numpy(float)), salt=salt + 1).itertuples():
        s = s1.loc[r.match_id]
        k = sb[(sb["tour"] == r.tour) & (sb["date"] == pd.Timestamp(s["td_date"]).normalize()) &
               (sb["winner"] == s["td_winner"]) & (sb["loser"] == s["td_loser"])]
        a_is_w = surname_in(A[r.match_id], s["td_winner"]) and not surname_in(A[r.match_id], s["td_loser"])
        raw_p = float(k["pw_pm_m60"].iloc[0]) if a_is_w else 1 - float(k["pw_pm_m60"].iloc[0])
        out.append({"source": "polymarket 60 min (join)", "match_id": r.match_id, "a_name_stage0": A[r.match_id],
                    "td_winner": s["td_winner"], "td_loser": s["td_loser"], "a_is": "winner" if a_is_w else "loser",
                    "table_p_a": float(r.p_pm60), "raw_p_a": raw_p, "agrees": bool(np.isclose(raw_p, r.p_pm60))})
    return out


def main() -> int:
    df = O.load_table()
    y = O.attach_y(df)
    base = df["gap"].to_numpy() & np.isfinite(y)            # gap rows before the seal
    A = names_a()
    s1 = pd.read_parquet(O.STAGE1, columns=["match_id", "td_file", "td_row", "td_date", "td_winner", "td_loser"])
    s1["match_id"] = s1["match_id"].astype(str)
    s1 = s1.set_index("match_id")
    raw_t = pd.read_parquet(O.TABLE, columns=["match_id", "ot8_a", "ot8_b", "ot130_a", "ot130_b"])
    raw_t["match_id"] = raw_t["match_id"].astype(str)
    raw_t = raw_t.set_index("match_id")
    books = pd.read_parquet(O.OT_BOOKS, columns=["kind", "eid", "paid", "partid", "pri", "tim_utc"],
                            filters=[("paid", "in", [8, 130])])
    events = pd.read_parquet(O.OT_EVENTS, columns=["eid", "dt_utc", "home_partid", "home_first", "home_last",
                                                   "away_partid", "away_first", "away_last"]).drop_duplicates("eid")
    events = events.set_index("eid")
    sb = pd.read_parquet(O.SHARP, columns=["tour", "date", "winner", "loser", "condition_id", "winner_outcome",
                                           "pm_title", "pm_start_ts", "pw_pm_m30"])
    sb["date"] = pd.to_datetime(sb["date"]).dt.normalize()
    psx_rows = base & np.isfinite(df["p_psx"].to_numpy(float))
    checks = (tennis_data(df, psx_rows, A, s1, 1) +                                  # 2025 rows, PS still quoted
              tennis_data(df, base & (df["td_date"] >= "2026-01-15").to_numpy(), A, s1, 2) +
              oddstrader(df, base, A, raw_t, books, events, 8, "BetOnline", 3) +
              oddstrader(df, base, A, raw_t, books, events, 130, "Bet105", 4) +
              polymarket(df, base, A, s1, sb, 5) + joins(df, base, A, 6))
    det = pd.DataFrame([{k: (json.dumps(v, default=str) if isinstance(v, (list, dict)) else v)
                         for k, v in r.items()} for r in checks])
    det.to_parquet(O.OUT / "hand_checks.parquet", index=False)
    summary = {"seed": SEED, "per_reader": {}, "rule": "gap rows before the seal, drawn at random (numpy default_rng)"}
    for r in checks:
        g = summary["per_reader"].setdefault(r["source"], {"checked": 0, "agree": 0, "keys": []})
        g["checked"] += 1
        g["agree"] += int(bool(r.get("agrees")))
        g["keys"].append({"match_id": r["match_id"], "agrees": bool(r.get("agrees")),
                          "a_side_identified_as": r.get("a_named_as") or r.get("a_is")})
    O.write_json(O.OUT / "hand_checks.json", summary)
    for r in checks:
        print(json.dumps(r, default=str, ensure_ascii=False))
    print(json.dumps({k: (v["checked"], v["agree"]) for k, v in summary["per_reader"].items()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
