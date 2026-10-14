"""Stage 0, part 3: every number the Stage 0 write-up quotes, in one file.

Reads the outputs of stage0_sources.py and stage0_coverage.py and writes data/studies/shot_level/stage0_summary.json:
the sources (matches, links, years, families carried), the scorable matches per family with their detectable gains,
the same by source group, season and level, the inflation factors, and what the earlier studies' features were built
from (the box-score fields and the three point-by-point features, read from their code's constants).

Run:  ./python.sh src/eda/shot_level/stage0_summary.py   (seconds; prints the write-up's tables)
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402

FAM = list(S.FAMILIES)
FAM_ANY = FAM + ["any"]


INPUTS = ["data/studies/predictability_diagnostic/stage0_matches.parquet",
          "data/studies/predictability_diagnostic/stage0_match_players.parquet",
          "data/studies/predictability_diagnostic/stage4_features.parquet",
          "src/eda/predictability_diagnostic/common.py", "src/eda/predictability_diagnostic/stage3_traits.py",
          "src/eda/ufc_ideas/common.py", "src/eda/data_map/measure.py",
          "data/studies/feature_alpha_audit/repairs/repair_date_audit.parquet"]


def provenance() -> list[dict]:
    """The earlier studies' tables and code this stage read, with their modification times and hashes: a concurrent
    audit (docs/studies/feature_alpha_audit/) was repairing that code on 2 Oct 2026 and writes its repaired tables
    elsewhere, so the originals' versions are recorded here."""
    out = []
    for rel in INPUTS:
        p = ROOT / rel
        h = hashlib.sha256()
        with open(p, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        out.append({"path": rel, "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
                    "sha256": h.hexdigest()})
    return out


def r1(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 1)


def r3(x):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 3)


def sources_table(src: pd.DataFrame) -> list[dict]:
    out = []
    for s, g in src.groupby("source", sort=False):
        lk = g[g["match_id"].notna()]
        yrs = pd.to_numeric(lk["year"], errors="coerce").dropna()
        rec = {"source": s, "name": S.SOURCES[s]["name"], "grain": S.SOURCES[s]["grain"],
               "tours": sorted(g["tour"].dropna().unique().tolist()), "matches": int(len(g)),
               "linked": int(len(lk)), "link_rate": r3(len(lk) / len(g)) if len(g) else None,
               "linked_from_2010": int((yrs >= 2010).sum()),
               "matches_from_2010": int((pd.to_numeric(g["year"], errors="coerce") >= 2010).sum()),
               "years": [int(yrs.min()), int(yrs.max())] if len(yrs) else None,
               "points": int(g["n_points"].sum()),
               "linked_with": {f: int(lk[f"has_{f}"].sum()) for f in FAM}}
        rec["link_rate_from_2010"] = r3(rec["linked_from_2010"] / rec["matches_from_2010"]) if rec["matches_from_2010"] else None
        out.append(rec)
    return out


def main() -> int:
    src = pd.read_parquet(S.OUT / "stage0_source_matches.parquet")
    cov = pd.read_csv(S.OUT / "stage0_coverage.csv", dtype={"season": str, "level_group": str})
    cj = json.loads((S.OUT / "stage0_coverage.json").read_text(encoding="utf-8"))
    sj = json.loads((S.OUT / "stage0_sources.json").read_text(encoding="utf-8"))
    head = cov[(cov["season"] == "all") & (cov["level_group"] == "all")]

    def cell(tour, fam, window, k, subset, group="all"):
        r = head[(head["tour"] == tour) & (head["family"] == fam) & (head["window"] == window) & (head["k"] == k)
                 & (head["subset"] == subset) & (head["group"] == group)]
        if r.empty:
            return None
        r = r.iloc[0]
        return {"eligible": int(r["eligible"]), "covered": int(r["covered"]), "share": r3(r["share"]),
                "mde_single_input": r3(r["mde_single_input"]), "mde_profile": r3(r["mde_profile"]),
                "mde_family_wide": r3(r["mde_family_wide"])}

    table = {}
    for t in C.TOURS:
        for f in FAM_ANY:
            table[f"{t}|{f}"] = {
                "market_52w_k3": cell(t, f, "52w", 3, "market"),
                "market_13w_k3": cell(t, f, "13w", 3, "market"),
                "market_career_k3": cell(t, f, "career", 3, "market"),
                "market_52w_k1": cell(t, f, "52w", 1, "market"),
                "market_52w_k10": cell(t, f, "52w", 10, "market"),
                "recent_52w_k3": cell(t, f, "52w", 3, "market_2022_26"),
                "recent_13w_k3": cell(t, f, "13w", 3, "market_2022_26"),
                "evaluation_52w_k3": cell(t, f, "52w", 3, "evaluation"),
                "repaired_52w_k3": cell(t, f, "52w", 3, "repaired_market"),
                "repaired_2019_26_52w_k3": cell(t, f, "52w", 3, "repaired_market_2019_26"),
                "repaired_2019_26_13w_k3": cell(t, f, "13w", 3, "repaired_market_2019_26"),
                "repaired_2022_26_52w_k3": cell(t, f, "52w", 3, "repaired_market_2022_26")}
    groups = {}
    for t in C.TOURS:
        for f in FAM_ANY:
            for g in ("all", "slams", "atp_feeds", "charts", "wta_api"):
                c = cell(t, f, "52w", 3, "market", g)
                groups[f"{t}|{f}|{g}"] = c["covered"] if c else None
    seasons = {}
    s = cov[(cov["subset"] == "market") & (cov["window"] == "52w") & (cov["k"] == 3) & (cov["group"] == "all")
            & (cov["season"] != "all")]
    for (t, f), g in s.groupby(["tour", "family"]):
        seasons[f"{t}|{f}"] = {str(y): r3(v) for y, v in zip(g["season"], g["share"])}
    levels = {}
    lv = cov[(cov["subset"] == "evaluation") & (cov["window"] == "52w") & (cov["k"] == 3) & (cov["group"] == "all")
             & (cov["level_group"] != "all")]
    for (t, f), g in lv.groupby(["tour", "family"]):
        levels[f"{t}|{f}"] = {lg: r3(v) for lg, v in zip(g["level_group"], g["share"])}
    infl = cj["inflation"]
    examples = {str(n): {"ideal": r3(S.mde_milli(n)), "single_input": r3(S.mde_milli(n, inflation=infl["single_input_median_ratio"])),
                         "profile": r3(S.mde_milli(n, inflation=infl["multi_input_median_ratio"]))}
                for n in (2000, 5000, 10000, 20000, 30000)}
    # the inflation ratio by source of rows
    it = pd.read_csv(S.OUT / "stage0_inflation.csv")
    infl_by_source = {s: {"rows": int(len(g)), "median": r3(g["ratio"].median()), "mean": r3(g["ratio"].mean()),
                          "max": r3(g["ratio"].max())} for s, g in it.groupby("source")}
    # the family-wide line against one test: the ratio of the two detectable gains, and the ranges by tour (tracking
    # aside) of the detectable gains quoted in the write-up
    fw_ratio = r3(((3.23 + 0.8416) / (1.96 + 0.8416)) ** 2)
    ranges = {}
    for t in C.TOURS:
        for key in ("market_52w_k3", "recent_52w_k3"):
            cells = [table[f"{t}|{f}"][key] for f in FAM if f != "tracking"]
            ranges[f"{t}|{key}"] = {"single": [r3(min(c["mde_single_input"] for c in cells)), r3(max(c["mde_single_input"] for c in cells))],
                                    "profile": [r3(min(c["mde_profile"] for c in cells)), r3(max(c["mde_profile"] for c in cells))],
                                    "family_wide": [r3(min(c["mde_family_wide"] for c in cells)), r3(max(c["mde_family_wide"] for c in cells))]}
    # headroom: matches with odds not yet scorable (any family, 52 weeks, k = 3), and the detectable gain if all were
    headroom = {}
    for t in C.TOURS:
        a = table[f"{t}|any"]["market_52w_k3"]
        headroom[t] = {"covered": a["covered"], "eligible": a["eligible"], "uncovered_share": r3(1 - a["covered"] / a["eligible"]),
                       "n_increase": r3(a["eligible"] / a["covered"] - 1),
                       "mde_reduction": r3(1 - a["covered"] / a["eligible"])}
    group_shares = {k: (r3(v / table[f"{k.split('|')[0]}|any"]["market_52w_k3"]["eligible"]) if v is not None else None)
                    for k, v in groups.items()}
    # long rallies per annotated Infosys match: points that ended on the 9th shot or later
    inf = src[(src["source"] == "infosys") & src["has_rally"] & src["rally_buckets"].notna()]
    b = np.array([json.loads(x) for x in inf["rally_buckets"]])
    long_rallies = {"matches": int(len(b)), "mean_points": r1(b.sum(1).mean()), "mean_long_9plus": r1((b[:, 9] + b[:, 10]).mean()),
                    "share_long_9plus": r3((b[:, 9] + b[:, 10]).sum() / b.sum())}
    # Grand Slam main draws: share of Stage 0's matches carrying any shot-level family, by Slam and season
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "tournament_name"])
    gs = m[m["level"].eq("GS") & ~m["qualifying"]].copy()
    carry = set(src.loc[src["match_id"].notna() & src[[f"has_{f}" for f in FAM]].any(axis=1), "match_id"])
    gs["carries"] = gs["match_id"].isin(carry)
    gs["slam"] = gs["tournament_name"].str.lower().map(
        lambda n: next((s for s, pat in {"AO": "australian", "RG": "roland|french", "W": "wimbledon", "USO": "us open"}.items()
                        if pd.Series([n]).str.contains(pat).iloc[0]), "other"))
    slam_cov = {f"{s}|{y}": r3(v) for (s, y), v in gs[gs["year"] >= 2011].groupby(["slam", "year"])["carries"].mean().items()}
    summary = {
        "earlier_studies": {
            "box_fields": C.BOX, "rates": list(C.RATES),
            "point_by_point_features": [
                "Stage 2: big points in the Grand Slam point-by-point files (an analysis, src/eda/predictability_diagnostic/stage2_pbp.py)",
                "Stage 4: big-point play on return (stage4_features.pbp_history)",
                "UFC ideas Stage C: late-match decline (stageC_fatigue.py)"],
            "shot_level_fields_used": []},
        "stage0_matches_with_shot_data": cj["stage0_matches_with_shot_data"],
        "source_matches_total": int(len(src)),
        "sources": sources_table(src), "source_notes": sj["notes"], "thresholds": sj["thresholds"],
        "coverage": table, "by_group_market_52w_k3": groups, "by_season_market_52w_k3": seasons,
        "by_level_evaluation_52w_k3": levels, "inflation": infl, "inflation_by_source": infl_by_source,
        "mde_examples": examples, "family_wide_over_single": fw_ratio, "mde_ranges_excluding_tracking": ranges,
        "headroom_any_52w_k3": headroom, "group_shares_market_52w_k3": group_shares,
        "infosys_long_rallies": long_rallies, "grand_slam_main_draw_carrying_share": slam_cov,
        "market_v": cj["market_v"], "inputs": provenance()}
    (S.OUT / "stage0_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    # the write-up's tables, printed
    print("SOURCES")
    for r in summary["sources"]:
        print(f"| {r['source']} | {','.join(r['tours'])} | {r['years']} | {r['matches']:,} | {r['matches_from_2010']:,} | "
              f"{r['linked']:,} ({100 * (r['link_rate_from_2010'] or 0):.1f}% from 2010) | {r['points']:,} | "
              + " | ".join(f"{r['linked_with'][f]:,}" for f in FAM) + " |")
    print("\nCOVERAGE market 2013-26, 52w k3 | 13w k3 | 2022-26 52w k3 | 2022-26 13w k3")
    for t in C.TOURS:
        for f in FAM_ANY:
            c = table[f"{t}|{f}"]
            a, b, rr, r13 = c["market_52w_k3"], c["market_13w_k3"], c["recent_52w_k3"], c["recent_13w_k3"]
            print(f"| {t} | {f} | {a['covered']:,} of {a['eligible']:,} ({100 * a['share']:.0f}%) | {a['mde_single_input']:.2f} | "
                  f"{a['mde_profile']:.2f} | {b['covered']:,} ({100 * b['share']:.0f}%) | {rr['covered']:,} of {rr['eligible']:,} "
                  f"({100 * rr['share']:.0f}%) | {rr['mde_single_input']:.2f} | {rr['mde_profile']:.2f} | {r13['covered']:,} ({100 * r13['share']:.0f}%) |")
    print("\nGROUPS (market 52w k3)")
    for t in C.TOURS:
        for f in FAM_ANY:
            print(f"| {t} | {f} | " + " | ".join(str(groups[f"{t}|{f}|{g}"]) for g in ("all", "slams", "atp_feeds", "charts", "wta_api")) + " |")
    print("\nINFLATION", infl)
    print("MDE examples", examples)
    print("SEASONS rally/ending/speed/tracking")
    for t in C.TOURS:
        for f in ("rally", "ending", "speed", "tracking"):
            print(t, f, seasons[f"{t}|{f}"])
    print("LEVELS")
    for t in C.TOURS:
        for f in ("any", "rally"):
            print(t, f, levels[f"{t}|{f}"])
    print("\nREPAIRED RULE: 2013-26 52w k3 | 2019-26 52w k3 | 2019-26 13w k3 | 2022-26 52w k3")
    for t in C.TOURS:
        for f in FAM_ANY:
            c = table[f"{t}|{f}"]
            a, b, b13, d = c["repaired_52w_k3"], c["repaired_2019_26_52w_k3"], c["repaired_2019_26_13w_k3"], c["repaired_2022_26_52w_k3"]
            print(f"| {t} | {f} | {a['covered']:,} of {a['eligible']:,} ({100 * a['share']:.0f}%) | {b['covered']:,} of {b['eligible']:,} "
                  f"({100 * b['share']:.0f}%) | {b['mde_single_input']:.2f} | {b['mde_profile']:.2f} | {b13['covered']:,} ({100 * b13['share']:.0f}%) | "
                  f"{d['covered']:,} of {d['eligible']:,} ({100 * d['share']:.0f}%) |")
    print("INFLATION BY SOURCE", infl_by_source)
    print("FAMILY-WIDE / SINGLE", fw_ratio)
    print("RANGES", ranges)
    print("HEADROOM", headroom)
    print("GROUP SHARES", {k: v for k, v in group_shares.items() if k.split("|")[1] in ("any", "rally")})
    print("LONG RALLIES", long_rallies)
    print("SLAMS", slam_cov)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ------------------------------------------------------------------------------------------------
# The write-up's tables, generated from stage0_summary.json (so stage0.md quotes only computed numbers)

FAMILY_WORDS = {"rally": "rally length", "ending": "how points end", "speed": "serve speed", "placement": "serve placement",
                "net": "net play", "return": "return depth", "stroke": "stroke mix", "tracking": "ball tracking", "any": "any"}
SOURCE_WORDS = {"mcp": "Match Charting Project (volunteer charts)",
                "slam_pbp": "Grand Slam point-by-point (Sackmann's copies of the IBM and Infosys feeds)",
                "slamtracker": "Wimbledon and US Open feeds (IBM SlamTracker)",
                "slam_tracking": "Australian Open and Roland Garros Court Vision (hawkilol copy)",
                "ausopen": "Australian Open match centre", "infosys": "ATP Infosys match centre (Hugging Face handoff)",
                "court_vision": "ATP Court Vision (Hugging Face handoff)", "sirgenkii": "SirGenkii infotennis (ATP, Jan–Apr 2025)",
                "tdi": "TDI Tennis Results (ATP and Challenger)",
                "wta_advanced": "WTA official API, advanced statistics (match totals)"}
ORDER = ["mcp", "slam_pbp", "slamtracker", "slam_tracking", "ausopen", "infosys", "court_vision", "sirgenkii", "tdi",
         "wta_advanced"]


def tables(summary: dict) -> str:
    fam = list(S.FAMILIES)
    out = []
    src = {r["source"]: r for r in summary["sources"]}
    out.append("| Source | Tours | Years linked | Matches read (from 2010) | Linked (share from 2010) | Points | Rally | "
               "Ending | Speed | Placement | Net | Return | Stroke | Tracking |")
    out.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for s in ORDER:
        r = src[s]
        tours = "both" if len(r["tours"]) == 2 else ("men" if r["tours"] == ["M"] else "women")
        yrs = f"{r['years'][0]}–{r['years'][1]}" if r["years"][0] != r["years"][1] else str(r["years"][0])
        pts = f"{r['points']:,}" if r["points"] else "totals"
        share = f"{100 * r['link_rate_from_2010']:.1f}%" if r["link_rate_from_2010"] < 1 else "100%"
        out.append(f"| {SOURCE_WORDS[s]} | {tours} | {yrs} | {r['matches_from_2010']:,} | {r['linked']:,} ({share}) | "
                   f"{pts} | " + " | ".join(f"{r['linked_with'][f]:,}" for f in fam) + " |")
    out.append("")
    cov = summary["coverage"]
    out.append("| Tour | Family | 52 weeks, 2013–2026 | One statistic | Profile | 13 weeks, 2013–2026 | 52 weeks, 2022–2026 "
               "| One statistic | Profile | 13 weeks, 2022–2026 |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for t, word in (("atp", "Men"), ("wta", "Women")):
        for i, f in enumerate(fam + ["any"]):
            c = cov[f"{t}|{f}"]
            a, b, r, r13 = c["market_52w_k3"], c["market_13w_k3"], c["recent_52w_k3"], c["recent_13w_k3"]
            of_a = f" of {a['eligible']:,}" if i == 0 else ""
            of_r = f" of {r['eligible']:,}" if i == 0 else ""
            out.append(f"| {word} | {FAMILY_WORDS[f]} | {a['covered']:,}{of_a} ({100 * a['share']:.0f}%) | "
                       f"{a['mde_single_input']:.2f} | {a['mde_profile']:.2f} | {b['covered']:,} ({100 * b['share']:.0f}%) | "
                       f"{r['covered']:,}{of_r} ({100 * r['share']:.0f}%) | {r['mde_single_input']:.2f} | "
                       f"{r['mde_profile']:.2f} | {r13['covered']:,} ({100 * r13['share']:.0f}%) |")
    out.append("")
    g = summary["by_group_market_52w_k3"]
    out.append("| Tour | Family | All sources | Grand Slam feeds | ATP feeds (Infosys, Court Vision, SirGenkii, TDI) | "
               "Volunteer charts | WTA advanced statistics |")
    out.append("|---|---|---:|---:|---:|---:|---:|")
    for t, word, fams in (("atp", "Men", ["rally", "ending", "speed", "tracking"]),
                          ("wta", "Women", ["rally", "ending", "speed", "net"])):
        for f in fams:
            vals = []
            for grp in ("all", "slams", "atp_feeds", "charts", "wta_api"):
                v = g[f"{t}|{f}|{grp}"]
                vals.append("–" if (t == "atp" and grp == "wta_api") or (t == "wta" and grp == "atp_feeds") else f"{v:,}")
            out.append(f"| {word} | {FAMILY_WORDS[f]} | " + " | ".join(vals) + " |")
    out.append("")
    out.append("| Tour | Family | 52 weeks, 2013–2026 | 52 weeks, 2019–2026 | One statistic | Profile | 13 weeks, "
               "2019–2026 | 52 weeks, 2022–2026 |")
    out.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for t, word in (("atp", "Men"), ("wta", "Women")):
        for i, f in enumerate(["rally", "ending", "speed", "net", "tracking", "any"]):
            c = cov[f"{t}|{f}"]
            a, b, b13, d = c["repaired_52w_k3"], c["repaired_2019_26_52w_k3"], c["repaired_2019_26_13w_k3"], c["repaired_2022_26_52w_k3"]
            ofa = f" of {a['eligible']:,}" if i == 0 else ""
            ofb = f" of {b['eligible']:,}" if i == 0 else ""
            ofd = f" of {d['eligible']:,}" if i == 0 else ""
            out.append(f"| {word} | {FAMILY_WORDS[f]} | {a['covered']:,}{ofa} ({100 * a['share']:.0f}%) | "
                       f"{b['covered']:,}{ofb} ({100 * b['share']:.0f}%) | {b['mde_single_input']:.2f} | "
                       f"{b['mde_profile']:.2f} | {b13['covered']:,} ({100 * b13['share']:.0f}%) | "
                       f"{d['covered']:,}{ofd} ({100 * d['share']:.0f}%) |")
    out.append("")
    se = summary["by_season_market_52w_k3"]
    seasons = ["2013", "2014", "2015", "2016", "2017", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]
    out.append("| Season | " + " | ".join(seasons) + " |")
    out.append("|---|" + "---:|" * len(seasons))
    for t, f, label in (("atp", "rally", "Men, rally length"), ("atp", "tracking", "Men, ball tracking"),
                        ("wta", "rally", "Women, rally length"), ("wta", "ending", "Women, how points end")):
        vals = [se[f"{t}|{f}"].get(y) for y in seasons]
        out.append(f"| {label} | " + " | ".join("0" if v == 0 else f"{v:.2f}" for v in vals) + " |")
    return "\n".join(out) + "\n"


def write_tables() -> None:
    summary = json.loads((S.OUT / "stage0_summary.json").read_text(encoding="utf-8"))
    (S.OUT / "stage0_tables.md").write_text(tables(summary), encoding="utf-8")


if __name__ == "__main__" and "--tables" in sys.argv:
    write_tables()
