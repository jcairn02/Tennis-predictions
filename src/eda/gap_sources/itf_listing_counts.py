"""Lanes C3 and C4 of the gap-sources study: ITF listings already held locally (29 Sep 2026).

C3, Live Tennis API public sample (Zenodo record 22048731 v1.0.0, data/dump/matches/live_tennis_api_zenodo/):
ITF singles rows by month, tour and draw. ITF singles are tier_key 270 (men) and 271 (women); tiers 264 and
287 and the untiered M/W rows are ITF doubles (every row has "/" pairs) and are left out. Qualifying rows
are those whose round label reads "Qualifications" or "Qualification Round n" (is_qualifying is never true for
ITF). Two naming styles ("ITF M25 Aldershot Men" and "M25 Aldershot") list some matches twice under
different player ids, so singles rows are de-duplicated on (tour, event name without the style marks,
unordered pair of surnames) within 36 hours. The index has no winners or scores, and "Cancelled" rows are
dropped. Its scheduled_time_utc is Israel local time in v1.0.0 (Zenodo v1.0.2, 28 Sep 2026, corrects this; same
rows), so times are converted from Asia/Jerusalem to UTC here.

C4, Polymarket (data/dump/odds/polymarket/, census snapshot 10 Sep 2026 plus extension of 22 Sep 2026):
moneyline markets of events in the inferred ITF bucket, dated by gameStartTime (else the event's sporting
date), split by settlement in the snapshot (1/0 = resolved winner, 0.5/0.5 = voided, else open or not yet
resolved when snapshotted). Gender comes from the league's M/W prefix when it has one, else from both player
names looked up in 2023-2026 men's and women's name lists (Sackmann match files, the Live Tennis API players,
and the ITF live-data day lists of Sep 2026), else from the event's inferred bucket_tour.

Writes data/studies/gap_sources/itf_listing_counts.csv (source, measure, tour, period_type, period, count)
and itf_listing_summary.json. Usage: ./python.sh src/eda/gap_sources/itf_listing_counts.py
"""
from __future__ import annotations

import csv
import glob
import gzip
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
DUMP = ROOT / "data" / "dump"
OUT = ROOT / "data" / "studies" / "gap_sources"
COUNTS_CSV = OUT / "itf_listing_counts.csv"
SUMMARY_JSON = OUT / "itf_listing_summary.json"
STADION_LISTS = ROOT / "data" / "raw" / "gap_sources" / "itf" / "other" / "api.itf-production.sports-data.stadion.io"

GAP_START, GAP_END = pd.Timestamp("2026-06-22", tz="UTC"), pd.Timestamp("2026-09-21", tz="UTC")  # to 20 Sep incl.
ESTIMATE_WEEKS_27_38 = {"M": 5209, "W": 5123}  # data/data_map.yaml gap itf_after_june_2026 (lead's brief)


def fold(text) -> str:
    """ASCII, lower case, letters and single spaces only ("Kužmová-Ruiz" -> "kuzmova ruiz")."""
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return " ".join(re.sub(r"[^a-z ]+", " ", text.lower()).split())


def surname(name: str) -> str:
    parts = fold(name).split()
    return parts[-1] if parts else ""


def iso_week(ts: pd.Series) -> pd.Series:
    iso = ts.dt.isocalendar()
    return iso["year"].astype(str) + "-W" + iso["week"].astype(int).map("{:02d}".format)


# ----------------------------------------------------------------------------------------------- C3
def lta_itf_singles() -> tuple[pd.DataFrame, dict]:
    m = pd.read_parquet(DUMP / "matches" / "live_tennis_api_zenodo" / "matches.parquet",
                        columns=["match_id", "player1_id", "player2_id", "tournament", "tier_key", "round",
                                 "scheduled_time_utc", "event_status", "is_qualifying"])
    p = pd.read_parquet(DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet",
                        columns=["player_id", "name"]).set_index("player_id")["name"]
    facts = {"rows_total": len(m),
             "rows_by_month_all_tiers": m["scheduled_time_utc"].str[:7].value_counts().sort_index().to_dict()}
    prefix = m["tournament"].str.extract(r"^(?:ITF )?([MW])\d+")[0]
    facts["itf_doubles_rows_left_out"] = int(m["tier_key"].isin(["264", "287"]).sum()
                                             + (m["tier_key"].eq("") & prefix.notna()).sum())
    s = m[m["tier_key"].isin(["270", "271"])].copy()
    s["tour"] = s["tier_key"].map({"270": "M", "271": "W"})
    s["n1"], s["n2"] = s["player1_id"].map(p), s["player2_id"].map(p)
    facts["itf_singles_rows_with_pair_names"] = int((s["n1"].fillna("").str.contains("/")
                                                     | s["n2"].fillna("").str.contains("/")).sum())
    facts["cancelled_rows_dropped"] = int(s["event_status"].eq("Cancelled").sum())
    s = s[~s["event_status"].eq("Cancelled")]
    # v1.0.0's scheduled_time_utc is Israel local time (corrected in Zenodo v1.0.2 of 28 Sep 2026): convert.
    naive = pd.to_datetime(s["scheduled_time_utc"])
    local = naive.dt.tz_localize("Asia/Jerusalem", ambiguous="NaT", nonexistent="shift_forward")
    s["t"] = local.dt.tz_convert("UTC").fillna((naive - pd.Timedelta(hours=2)).dt.tz_localize("UTC"))
    label = s["round"].fillna("").str.replace(r"^.* - ", "", regex=True)
    s["draw"] = label.str.contains("qualif", case=False).map({True: "qualifying", False: "main"})
    s["style_itf"] = s["tournament"].str.match(r"^ITF .* (Men|Women)$")
    s["event_norm"] = (s["tournament"].str.replace(r"^ITF ", "", regex=True)
                       .str.replace(r" (Men|Women)$", "", regex=True)
                       .str.replace(r" \([^)]*\)$", "", regex=True).map(fold))
    s["pair"] = [tuple(sorted((surname(a), surname(b)))) for a, b in zip(s["n1"], s["n2"])]
    s = s.sort_values("t")
    keep, last_seen = [], {}
    for idx, tour, ev, pair, t in zip(s.index, s["tour"], s["event_norm"], s["pair"], s["t"]):
        key = (tour, ev, pair)
        prev = last_seen.get(key)
        if prev is not None and (t - prev) <= pd.Timedelta(hours=36) and all(pair):
            keep.append(False)
        else:
            keep.append(True)
        last_seen[key] = t
    s["dup"] = ~pd.Series(keep, index=s.index)
    facts["duplicate_rows_dropped"] = int(s["dup"].sum())
    facts["duplicate_rows_dropped_after_gap_start"] = int((s["dup"] & (s["t"] >= GAP_START)).sum())
    s = s[~s["dup"]]
    facts["last_scheduled_utc"] = str(s["t"].max())
    facts["first_itf_qualifying_row_utc"] = str(s.loc[s["draw"].eq("qualifying"), "t"].min())
    return s, facts


# ----------------------------------------------------------------------------------------------- C4
def name_gender_lists() -> dict[str, set[str]]:
    names = {"M": set(), "W": set()}
    arch = DUMP / "matches" / "sackmann_archive"
    for tour, pattern in (("M", "atp/atp_matches_*20[2][3456].parquet"), ("W", "wta/wta_matches_*20[2][3456].parquet")):
        for f in glob.glob(str(arch / pattern)):
            if "doubles" in f:
                continue
            d = pd.read_parquet(f, columns=["winner_name", "loser_name"])
            names[tour] |= set(map(fold, d["winner_name"].dropna())) | set(map(fold, d["loser_name"].dropna()))
    lp = pd.read_parquet(DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet", columns=["name", "tour"])
    for tour, tags in (("M", {"atp", "ATP"}), ("W", {"wta", "WTA"})):
        names[tour] |= set(map(fold, lp.loc[lp["tour"].isin(tags), "name"].dropna()))
    for path in STADION_LISTS.glob("wttCompleteMatchList_*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for t in (doc.get("data") or {}).values():
            for matches in (t.get("courts") or {}).values():
                for mt in matches or []:
                    disc = mt.get("_drawDiscipline") or {}
                    if (disc.get("type") or "").lower() != "singles":
                        continue
                    tour = {"men": "M", "women": "W"}.get(disc.get("gender"))
                    for side in mt.get("sides") or []:
                        for sp in side.get("sidePlayer") or []:
                            nm = ((sp.get("player") or {}).get("_name"))
                            if tour and nm:
                                names[tour].add(fold(nm))
    both = names["M"] & names["W"]
    return {"M": names["M"] - both, "W": names["W"] - both, "ambiguous": both}


def player_gender(name: str, lists: dict) -> str | None:
    f = fold(name)
    if not f:
        return None
    if f in lists["M"]:
        return "M"
    if f in lists["W"]:
        return "W"
    parts = f.split()
    if len(parts) >= 3:  # "Pedro Andre De Almeida Santos" vs "Pedro De Almeida Santos": first + last
        short = f"{parts[0]} {parts[-1]}"
        if short in lists["M"]:
            return "M"
        if short in lists["W"]:
            return "W"
    return None


CENSUS_MARKETS = ROOT / "data" / "studies" / "tennis_data_audit" / "polymarket" / "markets.jsonl.gz"
EXTENSION_MARKETS = ROOT / "data" / "raw" / "public_dump" / "polymarket_catalog" / "markets_extension.jsonl.gz"
DESC = re.compile(r"match between .+? and .+? in the (?P<label>.+?)(?:, (?P<draw>Main Draw|Qualifying)\b|, originally)")


def description_gender(label: str) -> str | None:
    if (re.match(r"^ITF Men\b", label) or re.search(r"\bM\d{2}\b", label) or re.search(r" Men$", label)
            or re.search(r"\bF\d+\b", label)):
        return "M"
    if re.match(r"^ITF Women\b", label) or re.search(r"\bW\d{2,3}\b", label) or re.search(r" Women$", label):
        return "W"
    return None


def market_descriptions() -> dict[str, tuple[str, str | None, str | None]]:
    """Market id -> (event label, draw label, gender) from the first sentence of each ITF moneyline's rules
    ("... in the ITF Men Hurghada, originally scheduled ..."; from Aug 2026 "... in the W50 Yecla, Main Draw, ...")."""
    out = {}
    for path in (CENSUS_MARKETS, EXTENSION_MARKETS):
        if not path.exists():
            continue
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                if '"moneyline"' not in line or '"itf-' not in line:
                    continue
                m = json.loads(line)
                if m.get("sportsMarketType") != "moneyline" or not str(m.get("event_slug", "")).startswith("itf-"):
                    continue
                first = (m.get("description") or "").split("\n")[0]
                hit = DESC.search(first)
                label = hit.group("label") if hit else ""
                out[str(m["id"])] = (label, hit.group("draw") if hit else None, description_gender(label))
    return out


def polymarket_itf(lists: dict) -> tuple[pd.DataFrame, dict]:
    e = pd.read_parquet(DUMP / "odds" / "polymarket" / "event_index.parquet",
                        columns=["id", "title", "sport_date", "league", "bucket", "bucket_tour", "catalog"])
    e = e[e["bucket"].eq("ITF World Tennis Tour")]
    mk = pd.read_parquet(DUMP / "odds" / "polymarket" / "market_index.parquet",
                         columns=["id", "question", "sportsMarketType", "gameStartTime", "outcomes", "outcomePrices",
                                  "event_id", "catalog"])
    ml = mk[mk["sportsMarketType"].eq("moneyline") & mk["event_id"].isin(e["id"])].merge(
        e.rename(columns={"id": "event_id", "catalog": "event_catalog"}), on="event_id", how="left")
    ml["t"] = pd.to_datetime(ml["gameStartTime"].fillna(ml["sport_date"]), utc=True, errors="coerce", format="mixed")
    prices = ml["outcomePrices"].map(lambda v: json.loads(v) if isinstance(v, str) and v.startswith("[") else [])
    ml["settlement"] = prices.map(lambda p: "resolved_1_0" if sorted(p) == ["0", "1"] else
                                  "void_0.5_0.5" if p == ["0.5", "0.5"] else "unresolved_in_snapshot")
    outcomes = ml["outcomes"].map(lambda v: json.loads(v) if isinstance(v, str) and v.startswith("[") else [])
    league_prefix = ml["league"].fillna("").str.extract(r"^([MW])\d+")[0]
    desc = market_descriptions()
    ml["desc_label"] = ml["id"].map(lambda i: desc.get(str(i), ("", None, None))[0])
    ml["draw_label"] = ml["id"].map(lambda i: desc.get(str(i), ("", None, None))[1]).fillna("unlabelled")
    desc_gender = ml["id"].map(lambda i: desc.get(str(i), ("", None, None))[2])
    by_names, methods = [], []
    for players, dg, lp, bt in zip(outcomes, desc_gender, league_prefix, ml["bucket_tour"]):
        gs = [player_gender(n, lists) for n in players]
        found = {g for g in gs if g}
        if dg in ("M", "W"):
            by_names.append(dg)
            methods.append("rules_text")
        elif isinstance(lp, str) and lp in "MW":
            by_names.append(lp)
            methods.append("league_prefix")
        elif len(found) == 1:
            by_names.append(found.pop())
            methods.append("player_names_both" if all(gs) else "player_names_one")
        elif bt in ("ATP", "WTA"):
            by_names.append({"ATP": "M", "WTA": "W"}[bt])
            methods.append("bucket_tour")
        else:
            by_names.append("unknown")
            methods.append("conflict" if len(found) > 1 else "none")
    ml["tour"], ml["tour_method"] = by_names, methods
    facts = {"itf_moneylines_total": len(ml), "itf_events_total": int(ml["event_id"].nunique()),
             "settlement_all": ml["settlement"].value_counts().to_dict(),
             "tour_method_all": ml["tour_method"].value_counts().to_dict(),
             "draw_label_all": ml["draw_label"].value_counts().to_dict(),
             "first_labelled": {lab: str(ml.loc[ml["draw_label"].eq(lab), "t"].min()) for lab in ("Main Draw", "Qualifying")},
             "first_match_utc": str(ml["t"].min()), "last_match_utc": str(ml["t"].max())}
    return ml, facts


# ----------------------------------------------------------------------------------------------- cross-checks
def stadion_singles() -> pd.DataFrame:
    """Singles matches of the ITF live-data day lists (15-29 Sep 2026) with draw, round and surname pair."""
    rows = []
    for path in sorted(STADION_LISTS.glob("wttCompleteMatchList_*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for t in (doc.get("data") or {}).values():
            for matches in (t.get("courts") or {}).values():
                for mt in matches or []:
                    disc = mt.get("_drawDiscipline") or {}
                    if (disc.get("type") or "").lower() != "singles":
                        continue
                    names = [((sp.get("player") or {}).get("_name")) for side in mt.get("sides") or []
                             for sp in side.get("sidePlayer") or []]
                    rows.append({"id": mt.get("id"), "day": mt.get("dateStartLocal"),
                                 "tour": {"men": "M", "women": "W"}.get(disc.get("gender")),
                                 "draw": "qualifying" if "qualif" in (mt.get("_drawName") or "").lower() else "main",
                                 "status": ((mt.get("matchStatus") or {}).get("_name") or "").lower(),
                                 "pair": tuple(sorted(surname(n) for n in names if n))})
    return pd.DataFrame(rows).drop_duplicates("id")


def match_pairs(pm: pd.DataFrame, ref: pd.DataFrame, days: int = 1) -> tuple[pd.Series, pd.Series]:
    """For each Polymarket row, the draw of a reference row with the same surname pair within ``days`` days
    (or None); and for each reference row, whether some Polymarket row matched it."""
    idx = defaultdict(list)
    for i, pair, day in zip(ref.index, ref["pair"], ref["day"]):
        idx[pair].append((i, pd.Timestamp(day)))
    hit_ref = set()
    draws = []
    for pair, day in zip(pm["pair"], pm["day"]):
        d = pd.Timestamp(day)
        found = next((i for i, rd in idx.get(pair, []) if abs((rd - d).days) <= days and i not in hit_ref), None)
        if found is None:
            found = next((i for i, rd in idx.get(pair, []) if abs((rd - d).days) <= days), None)
        if found is not None:
            hit_ref.add(found)
        draws.append(ref.at[found, "draw"] if found is not None else None)
    return pd.Series(draws, index=pm.index), pd.Series(ref.index.isin(list(hit_ref)), index=ref.index)


def crosschecks(pm: pd.DataFrame, lta: pd.DataFrame) -> dict:
    pm = pm.copy()
    pm["pair"] = pm["outcomes"].map(lambda v: tuple(sorted(surname(n) for n in json.loads(v)))
                                    if isinstance(v, str) and v.startswith("[") else ())
    pm["day"] = pm["t"].dt.strftime("%Y-%m-%d")
    out = {}
    st = stadion_singles()
    lo, hi = "2026-09-15", "2026-09-22"  # both lists complete for these days
    pw = pm[(pm["day"] >= lo) & (pm["day"] <= hi)]
    sw = st[(st["day"] >= lo) & (st["day"] <= hi)].reset_index(drop=True)
    draw, hit = match_pairs(pw, sw)
    done = sw["status"].isin(["complete", "walkover", "retired"])
    out["polymarket_vs_itf_live_lists_2026-09-15..22"] = {
        "polymarket_moneylines": len(pw), "matched_to_qualifying": int((draw == "qualifying").sum()),
        "matched_to_main": int((draw == "main").sum()), "unmatched": int(draw.isna().sum()),
        "itf_singles_with_a_market": {f"{t} {d}": f"{int((hit & done & (sw.tour == t) & (sw.draw == d)).sum())} of "
                                      f"{int((done & (sw.tour == t) & (sw.draw == d)).sum())}"
                                      for t in ("M", "W") for d in ("main", "qualifying")}}
    lt = lta[(lta["t"] >= GAP_START)].copy()
    lt["day"] = lt["t"].dt.strftime("%Y-%m-%d")
    lt = lt.reset_index(drop=True)[["day", "tour", "draw", "pair", "t"]]
    pl = pm[(pm["t"] >= GAP_START) & (pm["t"] < pd.Timestamp("2026-08-14", tz="UTC"))]
    draw, hit = match_pairs(pl, lt)
    lt["week"] = iso_week(lt["t"])
    by_week = {}
    for week, g in lt.groupby("week"):
        h = hit.loc[g.index]
        by_week[week] = {f"{t} {d}": f"{int(h[(g.tour == t) & (g.draw == d)].sum())} of {int(((g.tour == t) & (g.draw == d)).sum())}"
                         for t in ("M", "W") for d in ("main", "qualifying") if ((g.tour == t) & (g.draw == d)).any()}
    tab = pd.crosstab(pl["draw_label"], draw.fillna("unmatched"))
    out["polymarket_vs_live_tennis_api_2026-06-22..08-13"] = {
        "polymarket_moneylines": len(pl), "matched_to_lta_main": int((draw == "main").sum()),
        "matched_to_lta_qualifying": int((draw == "qualifying").sum()), "unmatched": int(draw.isna().sum()),
        "rules_text_draw_label_vs_lta_draw": {f"{a} -> {b}": int(tab.at[a, b]) for a in tab.index for b in tab.columns},
        "lta_rows_with_a_market_by_week": by_week}
    return out


# ----------------------------------------------------------------------------------------------- build
def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows: list[dict] = []

    def add(source, measure, tour, period_type, period, count, note=""):
        rows.append({"source": source, "measure": measure, "tour": tour, "period_type": period_type,
                     "period": period, "count": int(count), "note": note})

    lta, lta_facts = lta_itf_singles()
    lta["month"] = lta["t"].dt.strftime("%Y-%m")
    lta["week"] = iso_week(lta["t"])
    y = lta[lta["t"] >= pd.Timestamp("2025-01-01", tz="UTC")]
    for (month, tour, draw), n in y.groupby(["month", "tour", "draw"]).size().items():
        add("live_tennis_api_zenodo_v1.0.0", f"itf_singles_{draw}_listed", tour, "month", month, n,
            "no winner or score in the index")
    itf_months = set(y["month"].unique())
    for month in pd.period_range("2025-01", "2026-08", freq="M").astype(str):
        for tour in ("M", "W"):
            for draw in ("qualifying", "main"):
                if not ((y["month"] == month) & (y["tour"] == tour) & (y["draw"] == draw)).any():
                    add("live_tennis_api_zenodo_v1.0.0", f"itf_singles_{draw}_listed", tour, "month", month, 0,
                        "no rows" + ("; no ITF singles rows of either tour this month although other tiers have "
                                     f"{lta_facts['rows_by_month_all_tiers'].get(month, 0):,}"
                                     if month not in itf_months else ""))
    after = lta[lta["t"] >= GAP_START]
    for (week, tour, draw), n in after.groupby(["week", "tour", "draw"]).size().items():
        add("live_tennis_api_zenodo_v1.0.0", f"itf_singles_{draw}_listed", tour, "iso_week", week, n,
            "index ends 2026-08-13 (week 33 partial)" if week == "2026-W33" else "")
    for tour in ("M", "W"):
        for draw in ("qualifying", "main"):
            sel = after[(after["tour"] == tour) & (after["draw"] == draw)]
            add("live_tennis_api_zenodo_v1.0.0", f"itf_singles_{draw}_listed", tour, "total",
                "2026-06-22..2026-08-13", len(sel))
            w27 = sel[sel["t"] >= pd.Timestamp("2026-06-29", tz="UTC")]
            add("live_tennis_api_zenodo_v1.0.0", f"itf_singles_{draw}_listed", tour, "total",
                "2026-W27..2026-W33 (to 2026-08-13)", len(w27))

    lists = name_gender_lists()
    pm, pm_facts = polymarket_itf(lists)
    gap = pm[(pm["t"] >= GAP_START) & (pm["t"] < GAP_END)].copy()
    gap["month"] = gap["t"].dt.strftime("%Y-%m")
    gap["week"] = iso_week(gap["t"])
    lab = {"Main Draw": "main", "Qualifying": "qualifying", "unlabelled": "unlabelled"}
    for (month, tour, dl, st), n in gap.groupby(["month", "tour", "draw_label", "settlement"]).size().items():
        add("polymarket_catalog", f"itf_moneyline_{lab[dl]}_{st}", tour, "month", month, n,
            "catalog snapshots of 2026-09-10 (census) and 2026-09-22 (extension); draw from the rules text "
            "(Qualifying labelled from 10 Aug, Main Draw from 1 Sep 2026; unlabelled is mostly main draw)")
    for (week, tour, dl, st), n in gap.groupby(["week", "tour", "draw_label", "settlement"]).size().items():
        add("polymarket_catalog", f"itf_moneyline_{lab[dl]}_{st}", tour, "iso_week", week, n)
    for tour in ("M", "W", "unknown"):
        if tour == "unknown" and not (gap["tour"] == "unknown").any():
            continue
        for st in ("resolved_1_0", "void_0.5_0.5", "unresolved_in_snapshot"):
            add("polymarket_catalog", f"itf_moneyline_{st}", tour, "total", "2026-06-22..2026-09-20",
                ((gap["tour"] == tour) & (gap["settlement"] == st)).sum())
        w = gap[(gap["tour"] == tour) & (gap["t"] >= pd.Timestamp("2026-06-29", tz="UTC"))]
        add("polymarket_catalog", "itf_moneyline_resolved_1_0", tour, "total", "2026-W27..2026-W38",
            (w["settlement"] == "resolved_1_0").sum())
        add("polymarket_catalog", "itf_moneyline_all", tour, "total", "2026-W27..2026-W38", len(w))
        res = w[w["settlement"] == "resolved_1_0"]
        add("polymarket_catalog", "itf_moneyline_main_resolved_1_0", tour, "total", "2026-W27..2026-W38",
            res["draw_label"].isin(["Main Draw", "unlabelled"]).sum(),
            "Main Draw label plus unlabelled markets (unlabelled = main draw, see summary crosschecks)")
        add("polymarket_catalog", "itf_moneyline_qualifying_resolved_1_0", tour, "total", "2026-W27..2026-W38",
            (res["draw_label"] == "Qualifying").sum(), "Qualifying label, first seen on a 27 Jul 2026 match")
        if tour in ESTIMATE_WEEKS_27_38:
            add("data_map_estimate", "itf_main_missing_estimate", tour, "total", "2026-W27..2026-W38",
                ESTIMATE_WEEKS_27_38[tour], "gap itf_after_june_2026 as briefed")

    OUT.mkdir(parents=True, exist_ok=True)
    with COUNTS_CSV.open("w", newline="", encoding="utf-8") as handle:
        wr = csv.DictWriter(handle, fieldnames=["source", "measure", "tour", "period_type", "period", "count", "note"])
        wr.writeheader()
        for r in sorted(rows, key=lambda r: (r["source"], r["measure"], r["tour"], r["period_type"], r["period"])):
            wr.writerow(r)

    w27_38 = gap[gap["t"] >= pd.Timestamp("2026-06-29", tz="UTC")]
    resolved = w27_38[w27_38["settlement"] == "resolved_1_0"]
    summary = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "live_tennis_api": lta_facts,
        "live_tennis_api_after_gap_start": {f"{t} {d}": int(n) for (t, d), n in
                                            after.groupby(["tour", "draw"]).size().items()},
        "polymarket": pm_facts,
        "polymarket_gap_window": {
            "window": "match time 2026-06-22 to 2026-09-20 (UTC)", "moneylines": len(gap),
            "by_tour_settlement": {f"{t} {s}": int(n) for (t, s), n in gap.groupby(["tour", "settlement"]).size().items()},
            "tour_method": gap["tour_method"].value_counts().to_dict(),
            "weeks_27_38_resolved_1_0": {t: int((resolved["tour"] == t).sum()) for t in ("M", "W", "unknown")
                                         if (resolved["tour"] == t).any()},
            "weeks_27_38_resolved_1_0_by_draw_label": {f"{t} {d}": int(n) for (t, d), n in
                                                       resolved.groupby(["tour", "draw_label"]).size().items()},
            "by_draw_label": gap["draw_label"].value_counts().to_dict(),
            "weeks_27_38_resolved_1_0_total": len(resolved),
            "weeks_27_38_resolved_main_draw": {t: int(((resolved["tour"] == t) & resolved["draw_label"].isin(
                ["Main Draw", "unlabelled"])).sum()) for t in ("M", "W")},
            "weeks_27_38_resolved_qualifying": {t: int(((resolved["tour"] == t) & (resolved["draw_label"] ==
                "Qualifying")).sum()) for t in ("M", "W")},
            "main_draw_note": "unlabelled markets (before 1 Sep 2026) are counted as main draw: 5,741 of the 5,742 "
                              "unlabelled markets of 22 Jun-13 Aug that match a Live Tennis API row match a main-draw row",
            "estimate_missing_weeks_27_38": ESTIMATE_WEEKS_27_38,
            "share_of_estimate_resolved": round(len(resolved) / sum(ESTIMATE_WEEKS_27_38.values()), 3),
        },
        "name_lists": {k: len(v) for k, v in lists.items()},
        "crosschecks": crosschecks(pm, lta),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=1, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
