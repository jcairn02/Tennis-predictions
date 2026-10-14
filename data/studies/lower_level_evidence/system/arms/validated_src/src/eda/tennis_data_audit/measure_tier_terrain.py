"""Measure, by tennis tier, (1) Polymarket lifetime volume from the saved Gamma census,
(2) statistics depth in the saved Sackmann 2025 files, (3) odds coverage in the saved
tennis-data.co.uk workbooks. Feeds docs/research/tennis-data-audit/tennis-data-terrain.html.

Output: data/studies/tennis_data_audit/tier_terrain/tier_measurements.json

Interpreter: this is a self-contained research utility. It was run on 22 Sep 2026 with the
explicitly chosen existing `ufc-ag` conda env (pandas + openpyxl) because the project's
dedicated `tennis` env is absent; nothing was installed or changed. Read-only over project files.

Tier assignment for Polymarket events is an INFERENCE from provider league/title names via an
explicit alias map; ATP/WTA-series events whose names are not in the map are assumed to be
Challenger / WTA 125 level ("inferred lower tier"). The residual is reported so it can be checked.
Counts are Gamma event records, not deduplicated physical matches; volume is the platform's
lifetime field, not in-window fills.
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "data/studies/tennis_data_audit/tier_terrain"
EV = ROOT / "data/studies/tennis_data_audit/polymarket/events.jsonl"

SLAM_ATP = {"Australian Open Men's", "Roland Garros ATP", "Wimbledon ATP", "US Open ATP"}
SLAM_WTA = {"Australian Open Women's", "Roland Garros WTA", "Wimbledon WTA", "US Open WTA"}
M1000_BOTH = {"BNP Paribas Open", "Miami Open", "Madrid Open", "Internazionali BNL d'Italia",
              "National Bank Open", "Canadian Open", "Cincinnati Open"}
M1000_ATP = M1000_BOTH | {"Rolex Monte Carlo Masters", "Shanghai Rolex Masters", "Rolex Paris Masters"}
M1000_WTA = M1000_BOTH | {"Qatar Total Open", "Dubai Duty Free Tennis Championships", "China Open", "Wuhan Tennis Open"}
ATP500 = {"Rotterdam Open", "Dallas Open", "Qatar Open", "Rio Open", "Mexican Open", "Dubai Tennis Championships",
          "Barcelona Open", "BMW Open", "Hamburg European Open", "Halle Open", "HSBC Championships",
          "Mubadala Citi DC Open", "Japan Open Tennis Championships", "China Open", "Erste Bank Open", "Swiss Indoors Basel"}
ATP250 = {"Brisbane International", "Hong Kong Tennis Open", "Adelaide International", "ASB Classic", "Open Sud de France",
          "Delray Beach Open", "Argentina Open", "Open 13", "Chile Open", "Grand Prix Hassan II",
          "US Men's Clay Court Championships", "Bucharest Open", "Estoril Open", "Geneva Open", "Libema Open",
          "Stuttgart Open", "Mallorca Championships", "Lexus Eastbourne Open", "Swedish Open", "Swiss Open",
          "Generali Open", "Croatia Open", "Los Cabos Open", "Winston-Salem Open", "Hellenic Championship",
          "Open de Moselle", "Almaty Open", "Nordic Open", "European Open", "Hangzhou Open", "Chengdu Open",
          "Tiriac Open", "Marrakech", "Belgrade Open"}
WTA500 = {"Brisbane International", "Adelaide International", "Mubadala Abu Dhabi Open", "Upper Austria Ladies Linz",
          "Merida Open Akron", "Credit One Charleston Open", "Porsche Tennis Grand Prix", "Internationaux de Strasbourg",
          "HSBC Championships", "Grass Court Championships", "Bad Homburg Open", "Mubadala Citi DC Open",
          "Monterrey Open", "Guadalajara Open", "Korea Open", "Pan Pacific Open", "Ningbo Open"}
WTA250 = {"ASB Classic", "Hobart International", "ATX Open", "Transylvania Open", "Copa Colsanitas",
          "Open Capfinances Rouen Metropole", "GP SAR La Princesse Lalla Meryem", "Libema Open", "Nottingham Open",
          "Lexus Eastbourne Open", "Iasi Open", "Livesport Prague Open", "Hamburg European Open", "Palermo",
          "Athens Open", "The Memphis Classic", "Guangzhou Open", "Jiangxi Open", "Japan Women's Open",
          "Prudential Hong Kong Tennis Open", "Chennai Open", "Ostrava Open", "Singapore Open", "Tennis in the Land",
          "SP Open", "Cleveland Open"}
UNCERTAIN = {"Estoril Open", "Athens Open", "The Memphis Classic", "Ostrava Open", "Merida Open Akron", "Palermo",
             "Upper Austria Ladies Linz", "European Open"}
FINALS_PREFIX = ("ATP World Tour Finals", "WTA Finals", "Next Gen ATP Finals")
TEAM = ("Laver Cup", "Davis Cup", "United Cup", "Billie Jean King Cup", "Hopman")
EXHIB = ("Six Kings Slam", "Battle of the Sexes", "Garden Cup", "UTS", "Ultimate Tennis Showdown")
ITF_NAME = re.compile(r"^(ITF\b|M15\b|M25\b|W15\b|W35\b|W50\b|W75\b|W100\b)")
QUAL = re.compile(r"Qualification", re.I)
JUNIOR = re.compile(r"Juniors", re.I)
OUTRIGHT = re.compile(r"\bWinner\b|Champion", re.I)

BUCKET_ORDER = [
    "Grand Slam singles (main draw)",
    "Tournament-winner futures (mostly Slams)",
    "Grand Slam qualifying",
    "Grand Slam juniors",
    "Tour Finals (ATP/WTA/Next Gen)",
    "Masters 1000 / WTA 1000 (main draw)",
    "ATP 500 / WTA 500 (main draw)",
    "ATP 250 / WTA 250 (main draw)",
    "Main-tour qualifying (1000/500/250)",
    "Challenger / WTA 125 (inferred from bare names)",
    "ITF World Tennis Tour",
    "Doubles (all tiers)",
    "Team events & exhibitions",
    "Props, exact-score wrappers & other",
]


def series_key(e):
    s = {x["slug"] for x in e["series"]}
    for k in ("itf", "atp-doubles", "wta-doubles", "atp", "wta", "wimbledon"):
        if k in s:
            return k
    return "none"


def league_of(e):
    md = e.get("eventMetadata") or {}
    lg = md.get("league")
    if lg:
        return lg.strip()
    t = e["title"]
    return t.split(":")[0].strip() if ":" in t else t.strip()


def tour_of(e, skey):
    slug = e["slug"]
    if skey in ("atp", "atp-doubles") or slug.startswith("atp-"):
        return "ATP"
    if skey in ("wta", "wta-doubles") or slug.startswith("wta-"):
        return "WTA"
    lg = league_of(e)
    if "Men" in lg or " ATP" in lg:
        return "ATP"
    if "Women" in lg or " WTA" in lg:
        return "WTA"
    return "?"


def classify(e):
    """Return (bucket, tour, tier_detail, confidence)."""
    skey = series_key(e)
    lg = league_of(e)
    title = e["title"]
    tour = tour_of(e, skey)
    base = re.sub(r",\s*Qualification.*$", "", lg).strip()
    base = re.sub(r"\s+(ATP|WTA)$", "", base).strip() if base not in SLAM_ATP | SLAM_WTA else base
    conf = "measured-name" if base not in UNCERTAIN else "uncertain-name"

    if any(t in title for t in TEAM) or any(t in lg for t in TEAM):
        return "Team events & exhibitions", tour, "team", "measured-name"
    if any(t in title for t in EXHIB) or any(t in lg for t in EXHIB):
        return "Team events & exhibitions", tour, "exhibition", "measured-name"
    if skey == "itf" or ITF_NAME.match(lg):
        return "ITF World Tennis Tour", tour, "ITF", "measured-name"
    if JUNIOR.search(lg):
        return "Grand Slam juniors", tour, "juniors", "measured-name"
    if skey in ("atp-doubles", "wta-doubles") or "Doubles" in title:
        return "Doubles (all tiers)", tour, "doubles", "measured-name"
    if e["market_count"] >= 1 and skey == "none" and OUTRIGHT.search(title) and " vs" not in title.lower():
        return "Tournament-winner futures (mostly Slams)", tour, "outright", "measured-name"
    if skey == "none" and ("Exact Score" in title or "Will " in title or "Who will" in title or title in ("Wimbledon 2026", "US Open 2026")):
        return "Props, exact-score wrappers & other", tour, "prop/other", "measured-name"

    is_q = bool(QUAL.search(lg))
    slam = lg in SLAM_ATP or lg in SLAM_WTA or base in {"Australian Open", "Roland Garros", "Wimbledon", "US Open", "French Open"}
    if slam:
        # Polymarket's "Australian Open Men's/Women's" leagues also hold qualifying (11-15 Jan 2026,
        # before the 18 Jan main draw) and junior matches (nine-contract events from 24 Jan).
        # The other three Slams label those "..., Qualification" and "... Juniors".
        if lg.startswith("Australian Open"):
            day = e["sport_date"][:10]
            if day < "2026-01-18":
                return "Grand Slam qualifying", tour, "slam", "inferred-date"
            if day >= "2026-01-24" and e["market_count"] == 9:
                return "Grand Slam juniors", tour, "juniors", "inferred-contracts"
        return ("Grand Slam qualifying" if is_q else "Grand Slam singles (main draw)"), tour, "slam", "measured-name"
    if lg.startswith(FINALS_PREFIX):
        return "Tour Finals (ATP/WTA/Next Gen)", tour, "finals", "measured-name"

    tier = None
    if tour == "ATP":
        if base in M1000_ATP:
            tier = "1000"
        elif base in ATP500:
            tier = "500"
        elif base in ATP250:
            tier = "250"
    elif tour == "WTA":
        if base in M1000_WTA:
            tier = "1000"
        elif base in WTA500:
            tier = "500"
        elif base in WTA250:
            tier = "250"
    else:
        if base in M1000_BOTH:
            tier = "1000"
    if tier is None:
        if skey in ("atp", "wta") or tour in ("ATP", "WTA"):
            return "Challenger / WTA 125 (inferred from bare names)", tour, "lower-inferred", "inferred"
        return "Props, exact-score wrappers & other", tour, "unclassified", "inferred"
    if is_q:
        return "Main-tour qualifying (1000/500/250)", tour, tier + "Q", conf
    bucket = {"1000": "Masters 1000 / WTA 1000 (main draw)", "500": "ATP 500 / WTA 500 (main draw)",
              "250": "ATP 250 / WTA 250 (main draw)"}[tier]
    return bucket, tour, tier, conf


def vol(e):
    v = e.get("volume")
    return None if v in (None, "") else float(v)


def main():
    events = []
    with EV.open(encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            if not e.get("in_sport_window"):
                continue
            if any(s["slug"] == "cfb-2025" for s in e["series"]) or (e.get("sport") or {}).get("sport") == "cfb":
                continue
            events.append(e)
    assert len(events) == 33320, len(events)

    rows = []
    for e in events:
        b, tour, detail, conf = classify(e)
        rows.append({"bucket": b, "tour": tour, "detail": detail, "conf": conf, "league": league_of(e),
                     "vol": vol(e), "contracts": e["market_count"], "month": e["sport_date"][:7], "title": e["title"], "url": e["url"]})

    total_vol = sum(r["vol"] or 0 for r in rows)
    by_bucket = {}
    for b in BUCKET_ORDER:
        g = [r for r in rows if r["bucket"] == b]
        vols = [r["vol"] for r in g if r["vol"] is not None]
        pos = [v for v in vols if v > 0]
        by_bucket[b] = {
            "events": len(g), "contracts": sum(r["contracts"] for r in g),
            "events_with_volume_field": len(vols), "events_no_volume_field": len(g) - len(vols), "events_positive_volume": len(pos),
            "volume_usd": round(sum(vols), 2), "share_of_total": round(sum(vols) / total_vol, 4),
            "median_volume_per_event_with_field": round(median(vols), 2) if vols else None,
            "median_volume_per_positive_event": round(median(pos), 2) if pos else None,
            "mean_volume_per_event_with_field": round(sum(vols) / len(vols), 2) if vols else None,
            "atp_volume": round(sum(r["vol"] or 0 for r in g if r["tour"] == "ATP"), 2),
            "wta_volume": round(sum(r["vol"] or 0 for r in g if r["tour"] == "WTA"), 2),
            "atp_events": sum(r["tour"] == "ATP" for r in g), "wta_events": sum(r["tour"] == "WTA" for r in g),
            "uncertain_name_volume": round(sum(r["vol"] or 0 for r in g if r["conf"] == "uncertain-name"), 2),
            "top_leagues": [{"league": k, "volume": round(v, 0), "events": n} for k, v, n in sorted(
                ((k, sum(r["vol"] or 0 for r in g if r["league"] == k), sum(r["league"] == k for r in g))
                 for k in {r["league"] for r in g}), key=lambda x: -x[1])[:12]],
        }
    assert sum(v["events"] for v in by_bucket.values()) == len(rows)

    residual = Counter()
    residual_n = Counter()
    for r in rows:
        if r["detail"] == "lower-inferred":
            residual[(r["tour"], r["league"])] += r["vol"] or 0
            residual_n[(r["tour"], r["league"])] += 1
    residual_top = [{"tour": t, "league": l, "volume": round(v), "events": residual_n[(t, l)]} for (t, l), v in residual.most_common(60)]

    # Cross-check the inferred lower tier against tournament names in the Sackmann 2025-26 files.
    raw = ROOT / "data/studies/tennis_data_audit/public/raw"
    import unicodedata

    def norm(s):
        s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
        s = re.sub(r"\bch$", "", s).strip()
        s = re.sub(r"\b125\b", "", s)
        s = re.sub(r"\b(indoor|outdoor)\b", "", s)
        s = re.sub(r"\s+\d+$", "", s.strip()).strip()
        s = re.sub(r"\s+\d+$", "", s).strip()
        return re.sub(r"\s+", " ", s)

    sack_levels = {}
    for fname in ("atp_matches_2025.csv", "atp_matches_2026.csv", "atp_matches_qual_chall_2025.csv", "atp_matches_qual_chall_2026.csv",
                  "atp_matches_futures_2025.csv", "atp_matches_futures_2026.csv", "wta_matches_2025.csv", "wta_matches_2026.csv",
                  "wta_matches_qual_itf_2025.csv", "wta_matches_qual_itf_2026.csv"):
        df = pd.read_csv(raw / fname, low_memory=False, dtype={"tourney_level": str}, usecols=["tourney_name", "tourney_level"])
        for name, lvl in df.drop_duplicates().itertuples(index=False):
            lvl = str(lvl)
            cat = ("challenger_or_125" if lvl == "C" else "itf" if lvl in ("15", "25", "35", "50", "75", "100") else
                   "main_tour" if lvl in ("A", "I", "P", "PM", "M", "G", "F") else "other")
            key = norm(re.sub(r"^(W|M)\d+\s+", "", str(name)))
            sack_levels.setdefault(key, set()).add(cat)
    cross = defaultdict(lambda: {"volume": 0.0, "events": 0, "leagues": set()})
    for r in rows:
        if r["detail"] != "lower-inferred":
            continue
        key = norm(re.sub(r"\s*\(Doubles\)$", "", r["league"]))
        cats = sack_levels.get(key)
        if not cats:
            cat = "unmatched"
        elif "challenger_or_125" in cats and "itf" not in cats and "main_tour" not in cats:
            cat = "challenger_or_125"
        elif "itf" in cats and "challenger_or_125" not in cats and "main_tour" not in cats:
            cat = "itf_only_name"
        elif "main_tour" in cats and "challenger_or_125" not in cats:
            cat = "main_tour_name"
        else:
            cat = "ambiguous_name"
        cross[cat]["volume"] += r["vol"] or 0
        cross[cat]["events"] += 1
        cross[cat]["leagues"].add(r["league"])
    lower_total = sum(c["volume"] for c in cross.values()) or 1
    crosscheck = {k: {"volume": round(v["volume"]), "share_of_inferred_volume": round(v["volume"] / lower_total, 4), "events": v["events"],
                      "distinct_leagues": len(v["leagues"]), "example_leagues": sorted(v["leagues"])[:25]} for k, v in cross.items()}
    numbered = [r for r in rows if r["detail"] == "lower-inferred" and re.search(r"\s\d$", r["league"])]
    nvols = [r["vol"] for r in numbered if r["vol"] is not None]
    numbered_check = {"events": len(numbered), "volume": round(sum(nvols)), "median_volume": round(median(nvols)) if nvols else None,
                      "itf_series_median_volume": round(median([r["vol"] for r in rows if r["bucket"] == "ITF World Tennis Tour" and r["vol"] is not None])),
                      "note": "Numbered town names (Oeiras 3, Kigali 2) sit in the ATP/WTA product series with atp-/wta- slugs; ITF listings use the itf series and itf- slugs."}

    # Who plays where: player overlap across files (2025), by Sackmann player ID within a tour, by name across tours.
    def players(fname, levels=None):
        df = pd.read_csv(raw / fname, low_memory=False, dtype={"tourney_level": str},
                         usecols=["tourney_level", "winner_id", "loser_id", "winner_name", "loser_name"])
        if levels:
            df = df[df["tourney_level"].astype(str).isin(levels)]
        ids = set(df["winner_id"].dropna().astype(int)) | set(df["loser_id"].dropna().astype(int))
        names = set(df["winner_name"].dropna().astype(str).str.lower()) | set(df["loser_name"].dropna().astype(str).str.lower())
        return ids, names
    atp_main_ids, atp_main_names = players("atp_matches_2025.csv", ["G", "M", "A", "F"])
    atp_ch_ids, _ = players("atp_matches_qual_chall_2025.csv", ["C"])
    atp_fut_ids, _ = players("atp_matches_futures_2025.csv")
    wta_main_ids, wta_main_names = players("wta_matches_2025.csv", ["G", "PM", "P", "I", "F"])
    wta_125_ids, _ = players("wta_matches_qual_itf_2025.csv", ["C"])
    wta_itf_ids, _ = players("wta_matches_qual_itf_2025.csv", ["15", "35", "50", "75", "100"])
    overlap = {
        "atp_main_players": len(atp_main_ids), "atp_main_also_in_challenger": len(atp_main_ids & atp_ch_ids),
        "atp_challenger_players": len(atp_ch_ids), "atp_challenger_also_in_itf": len(atp_ch_ids & atp_fut_ids),
        "atp_itf_players": len(atp_fut_ids), "atp_main_also_in_itf": len(atp_main_ids & atp_fut_ids),
        "wta_main_players": len(wta_main_ids), "wta_main_also_in_125": len(wta_main_ids & wta_125_ids),
        "wta_main_also_in_itf": len(wta_main_ids & wta_itf_ids), "wta_125_players": len(wta_125_ids),
        "wta_125_also_in_itf": len(wta_125_ids & wta_itf_ids), "wta_itf_players": len(wta_itf_ids),
        "atp_wta_shared_names_main": len(atp_main_names & wta_main_names),
        "note": "2025 files; a player counts once per file; ATP and WTA IDs are separate numbering systems, so the cross-tour check uses names.",
    }

    monthly = {}
    for r in rows:
        m = monthly.setdefault(r["month"], defaultdict(float))
        grp = ("ITF" if r["bucket"] == "ITF World Tennis Tour" else
               "Main tour" if r["bucket"] in BUCKET_ORDER[0:9] else
               "Challenger/125" if r["bucket"] == BUCKET_ORDER[9] else "Other")
        m[grp] += r["vol"] or 0
        m["events"] += 1
        m["events_with_volume_field"] += 1 if r["vol"] is not None else 0
    monthly = {k: {g: round(v, 0) for g, v in d.items()} for k, d in sorted(monthly.items())}

    top_events = sorted((r for r in rows if r["vol"]), key=lambda r: -r["vol"])[:15]
    top_events = [{"title": r["title"], "bucket": r["bucket"], "volume": round(r["vol"]), "contracts": r["contracts"], "url": r["url"]} for r in top_events]

    level_names = {
        ("atp_main", "G"): "Grand Slam", ("atp_main", "M"): "Masters 1000", ("atp_main", "A"): "ATP 500/250 (A)",
        ("atp_main", "D"): "Team (Davis/United Cup)", ("atp_main", "F"): "ATP Finals",
        ("atp_qc", "C"): "Challenger main draw", ("atp_qc", "G"): "Slam qualifying", ("atp_qc", "M"): "1000 qualifying", ("atp_qc", "A"): "500/250 qualifying",
        ("atp_fut", "15"): "ITF M15", ("atp_fut", "25"): "ITF M25",
        ("wta_main", "G"): "Grand Slam", ("wta_main", "PM"): "WTA 1000", ("wta_main", "P"): "WTA 500", ("wta_main", "I"): "WTA 250",
        ("wta_main", "D"): "Team (BJK/United Cup)", ("wta_main", "F"): "WTA Finals", ("wta_main", "50+H"): "legacy label 50+H", ("wta_main", "35+H"): "legacy label 35+H",
        ("wta_qi", "C"): "WTA 125", ("wta_qi", "100"): "ITF W100", ("wta_qi", "75"): "ITF W75", ("wta_qi", "50"): "ITF W50", ("wta_qi", "35"): "ITF W35", ("wta_qi", "15"): "ITF W15",
        ("wta_qi", "G"): "Slam qualifying", ("wta_qi", "PM"): "1000 qualifying", ("wta_qi", "P"): "500 qualifying", ("wta_qi", "I"): "250 qualifying",
    }
    sack = []
    for key, fname in (("atp_main", "atp_matches_2025.csv"), ("atp_qc", "atp_matches_qual_chall_2025.csv"), ("atp_fut", "atp_matches_futures_2025.csv"),
                       ("wta_main", "wta_matches_2025.csv"), ("wta_qi", "wta_matches_qual_itf_2025.csv")):
        df = pd.read_csv(raw / fname, low_memory=False, dtype={"tourney_level": str})
        for lvl, g in df.groupby("tourney_level", dropna=False):
            sack.append({"file": key, "level": str(lvl), "label": level_names.get((key, str(lvl)), f"{key}:{lvl}"), "rows": int(len(g)),
                         "serve_stats_share": round(float(g["w_svpt"].notna().mean()), 3),
                         "minutes_share": round(float(g["minutes"].notna().mean()), 3),
                         "winner_rank_share": round(float(g["winner_rank"].notna().mean()), 3),
                         "loser_rank_share": round(float(g["loser_rank"].notna().mean()), 3),
                         "tournaments": int(g["tourney_id"].nunique()),
                         "qualifying_rows": int(g["round"].astype(str).str.startswith("Q").sum())})

    td = []
    for tour in ("atp", "wta"):
        for yr in (2025, 2026):
            df = pd.read_excel(ROOT / f"data/raw/tennis_data_couk/{tour}/{yr}.xlsx")
            col = "Series" if "Series" in df.columns else "Tier"
            for tier, g in df.groupby(col):
                td.append({"tour": tour.upper(), "year": yr, "tier": tier, "rows": int(len(g)),
                           "b365_share": round(float(g["B365W"].notna().mean()), 3),
                           "pinnacle_share": round(float(g["PSW"].notna().mean()), 3),
                           "avg_share": round(float(g["AvgW"].notna().mean()), 3),
                           "betfair_share": round(float(g["BFEW"].notna().mean()), 3) if "BFEW" in g else None,
                           "last_date": str(g["Date"].max())[:10]})

    out = {"window": "2025-09-10 to 2026-09-10 sporting dates; Gamma snapshot 2026-09-10; measured 2026-09-22",
           "total_events": len(rows), "total_contracts": sum(r["contracts"] for r in rows), "total_volume_usd": round(total_vol),
           "events_missing_volume_field": sum(r["vol"] is None for r in rows),
           "bucket_order": BUCKET_ORDER, "by_bucket": by_bucket, "residual_inferred_lower_top": residual_top,
           "inferred_lower_name_crosscheck": crosscheck, "numbered_name_check": numbered_check, "player_overlap_2025": overlap,
           "monthly": monthly, "top_events": top_events, "sackmann_2025": sack, "tennis_data_couk": td,
           "limitations": ["Tier assignment is name-based inference; the residual list should be checked against official calendars.",
                           "Volume is Polymarket's lifetime field per event, not in-window fills; missing fields count as zero here.",
                           "March 2026 records largely lack the volume field, understating Indian Wells and Miami.",
                           "Sackmann and tennis-data counts are physical rows, not audited completeness."]}
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "tier_measurements.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print("total volume", round(total_vol), "events", len(rows))
    for b in BUCKET_ORDER:
        v = by_bucket[b]
        print(f"{v['share_of_total']*100:5.1f}%  {v['volume_usd']:>14,.0f}  ev={v['events']:>6}  nofield={v['events_no_volume_field']:>5}  med={v['median_volume_per_positive_event'] or 0:>10,.0f}  ATPev={v['atp_events']:>5} WTAev={v['wta_events']:>5}  {b}")
    print("CROSSCHECK", json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "example_leagues"} for k, v in crosscheck.items()}, indent=1))
    for k, v in crosscheck.items():
        print("  ", k, v["example_leagues"])
    print("NUMBERED", numbered_check)
    print("OVERLAP", json.dumps(overlap, indent=1))
    for s in sack:
        if s["level"] == "C":
            print("C level", s["file"], "rows", s["rows"], "qualifying_rows", s["qualifying_rows"])


if __name__ == "__main__":
    main()
