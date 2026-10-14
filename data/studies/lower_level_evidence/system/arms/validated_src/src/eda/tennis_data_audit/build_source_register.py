"""Combine source evidence and editorial triage into a dated, grouped reading index."""
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs/research/tennis-data-audit"
REQUIRED = {"id", "name", "url", "category", "coverage", "granularity", "access", "rights", "evidence_status", "limitations"}
TRIAGE_REQUIRED = {"id", "recency_band", "data_dates", "latest_data_date", "data_sort_period", "date_basis", "scale_band", "scale", "review_priority", "model_role", "evidence_refs"}
AS_OF = "2026-09-11"
RECENCY = {
    "2026": "2026 data evidenced or explicitly documented",
    "2025": "Latest established data in 2025",
    "older": "Latest established data in 2024 or earlier",
    "unknown": "Latest data date unverified",
    "support": "Supporting records without a standalone data period",
}
SCALE = {
    "broad": "Broad datasets or feeds",
    "niche": "Niche or partial datasets",
    "unknown": "Scale unestablished",
    "support": "Supporting material",
}
PRIORITY = {"first": "Inspect first", "next": "Next candidate", "specialist": "Specialist use", "hold": "Defer", "support": "Reference"}
DATE_BASIS = {
    "observed_payload": "Inspected data/page",
    "provider_documentation": "Provider documentation",
    "local_snapshot": "Older local snapshot",
    "unverified": "Unverified data endpoint",
    "not_applicable": "No standalone data period",
}
LANES = [
    ("Public data", "public-data", {"public-sources.json"}),
    ("Commercial and private data", "commercial-and-private-data", {"commercial-sources.json"}),
    ("Odds and market data", "odds-and-market-data", {"market-sources.json", "polymarket-sources.json"}),
]

INTRO = """## Start here for a general predictive tennis model

**Start with these five source families.** Working assumption: prioritize broad match results, player identities and statistics across seasons, then add detail where it fills a demonstrated gap. Include ATP/WTA and investigate lower tours and doubles explicitly. This is an inspection order inferred from evidence, not a measured probability of model improvement or an approved dataset choice.

| Source family | Data dates and scale | Why inspect it early | Main unresolved question |
|---|---|---|---|
| **1. [Tennis My Life current downloads](#source-pub049)** | Audited 2025–2026 files; ATP ongoing recorded dates reach **9 Sep 2026**. Thousands of ATP/WTA, Challenger and ATP qualifying season rows. | Concrete recently inspected public results/statistics. Use the current website. | Season/ongoing overlap, key defects, date semantics and conflicting rights notices. [Audit](public-tennis-data.md#fresh-public-alternatives-and-why-their-qualifications-matter). |
| **2. [Sackmann archival mirror](#source-pub003)** | Deep ATP/WTA and lower-tier history; 2026 main-tour tournament dates stop **25 May**, lower-tier dates **1–2 Jun**. | Historical complement to a current feed; player IDs and longitudinal results/statistics. | Static archive with uneven field/tier coverage. Rankings reaching June do not mean matches do. [Audit](public-tennis-data.md#sackmann-deep-history-available-mirrors-and-current-gaps). |
| **3. [Tennis-data.co.uk](#source-tennis_data_odds)** ([ATP](#source-pub014), [WTA](#source-pub015)) | ATP results **2000+**, odds **2001+**; WTA **2007+**. Inspected local snapshots reach **Jun 2026**, not a fresh September download. | Broad main-tour results plus bookmaker odds for baseline comparisons. | Lower-tier gaps, no intraday quote history, substantial 2026 Pinnacle-column missingness. [Audit](market-history-and-odds.md#bookmaker-aggregators-and-private-feeds). |
| **4. [OnCourt](#source-oncourt)** ([database distribution](#source-oncourt_mysql)) | Provider claims **1.6m+ matches**, ATP **1990+**, WTA **1997+**, plus lower tiers. **Latest delivered date unverified.** | Concrete paid candidate for large longitudinal history and documented database access. | Need a dated export, per-tour/per-field coverage and intended-use rights. Counts are provider claims. [Provider](https://www.oncourt.info/index.html), [audit](commercial-tennis-data.md). |
| **5. [Live Tennis API public sample](#source-pub010)** → [historical product](#source-livetennisapi_history) | Index **Jan 2023–13 Aug 2026**: **173,571 match metadata rows**. Score-state sample **Jun–1 Jul 2026**: **5,380 matches / 951,064 state rows**. | Inspect the public sample for lower-tier and point-state potential before considering paid history. | Index omits winners/final scores; states are not validated unique points. Chronology, final states, identity joins and rights need resolution. [Audit](public-tennis-data.md#points-and-shots-several-different-products-not-one-data-layer). |

For a **paid official feed**, investigate [Sportradar](#source-sportradar_tennis_v3) and [Stats Perform WTA](#source-statsperform_wta) after these initial samples; historical delivery and training/retention rights remain unverified. For **timestamped odds**, inspect [Betfair history](#source-betfair_history) and [The Odds API](#source-the_odds_api), as additional market inputs/comparators. [Commercial evidence](commercial-tennis-data.md), [odds evidence](market-history-and-odds.md#historical-bookmaker-and-exchange-odds).

Defer selected-match charting, tracking/video, individual draw PDFs and weather until there is a specific feature or coverage question. [Open Tennis Data](#source-pub013) is a next candidate: 26,619 inspected results through 29 August 2026, but large cohort/round gaps and derivative lineage weaken its case as a first foundation. [Audit](public-tennis-data.md#fresh-public-alternatives-and-why-their-qualifications-matter).

[TennisData.app](#source-pub012) is another next candidate: documented 2021–2026 ATP/WTA/Challenger downloads look promising, but blocked downloads leave actual freshness, row counts and completeness unverified. [Source evidence](public-tennis-data.md#fresh-public-alternatives-and-why-their-qualifications-matter).

## How to read the ordering

Within **[Public](#public-data)**, **[Commercial/private](#commercial-and-private-data)** and **[Odds/markets](#odds-and-market-data)**, the order is **data recency → scale → latest evidenced data period, newest first where known**. Partial dates stay partial: a known month can be ordered without inventing a day. Entries known only to a year follow more precisely dated entries within that year/scale group; review priority breaks ties.

- **2026 / 2025 / older:** latest established data period for the linked resource or inspected snapshot. A 2026 entry can stop in January or June; it does not imply coverage through today. Provider claims and inspected data are labeled separately. A newer unseen payload may exist.
- **Unknown:** the cutoff or tennis-specific archive extent is unverified. This does not mean old or absent data. A sample, API example, product launch, publication or retrieval date does not establish the whole archive's endpoint.
- **Broad:** substantial longitudinal tour history or a feed spanning tours/competitions. Breadth/counts may be provider claims; completeness is not implied. ATP-only can be large without covering all tennis.
- **Niche/partial:** selected matches, an event family, short capture window, restricted population, video task or contextual feature. Millions of point, weather or book rows do not equal millions of tennis matches.
- **Scale unestablished / supporting:** insufficient corpus evidence, or references such as schemas, rights announcements and rules.
- **Inspect first / Next candidate / Specialist use / Defer / Reference:** editorial search priorities, not quality scores. Use the date evidence and caveat together; current data and deep older history can complement each other.

**Avoid double counting:** Sackmann originals/mirrors/dictionary form one family; Tennis My Life website/repository another; Tennis-data ATP/WTA/odds rows overlap; Live Tennis API public/academic/commercial records overlap; OnCourt desktop/distribution overlap. Open Tennis Data and Tennis Abstract derivatives reuse other collections. Polymarket metadata/rule examples repeat parts of the same market universe. These are alternate routes or products, not independent training samples.
"""


def cell(value):
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False)
    return value.replace("|", "/").replace("\n", " ").strip()


def load_triage(source_ids):
    annotations = {}
    for file in sorted(DOCS.glob("source-triage-*.json")):
        for row in json.loads(file.read_text(encoding="utf-8-sig")):
            if TRIAGE_REQUIRED - row.keys():
                raise ValueError(f"Missing triage fields: {file.name}: {row.get('id')}")
            source_id = row["id"]
            if source_id in annotations:
                raise ValueError(f"Duplicate triage ID: {source_id}")
            for field, allowed in (("recency_band", RECENCY), ("scale_band", SCALE), ("review_priority", PRIORITY), ("date_basis", DATE_BASIS)):
                if row[field] not in allowed:
                    raise ValueError(f"Invalid {field}: {source_id}: {row[field]}")
            latest = row["latest_data_date"]
            if latest is not None:
                parsed = date.fromisoformat(latest)
                if parsed > date.fromisoformat(AS_OF):
                    raise ValueError(f"Future observation endpoint: {source_id}: {latest}")
                band = row["recency_band"]
                if (band in {"2026", "2025"} and str(parsed.year) != band) or (band == "older" and parsed.year > 2024):
                    raise ValueError(f"Date/band mismatch: {source_id}")
            period = row["data_sort_period"]
            if period is not None:
                if not re.fullmatch(r"\d{4}(?:-\d{2}){0,2}", period):
                    raise ValueError(f"Invalid sorting period: {source_id}: {period}")
                parts = [int(part) for part in period.split("-")]
                parsed = date(*(parts + [1] * (3 - len(parts))))
                band = row["recency_band"]
                if parsed > date.fromisoformat(AS_OF) or band in {"unknown", "support"}:
                    raise ValueError(f"Unexpected dated sorting period: {source_id}: {period}")
                if (band in {"2026", "2025"} and str(parsed.year) != band) or (band == "older" and parsed.year > 2024):
                    raise ValueError(f"Period/band mismatch: {source_id}")
                if latest and latest != period:
                    raise ValueError(f"Exact endpoint/sort mismatch: {source_id}")
            if not isinstance(row["evidence_refs"], list) or not row["evidence_refs"]:
                raise ValueError(f"Missing triage evidence: {source_id}")
            for ref in row["evidence_refs"]:
                if not urlparse(ref).scheme and not (DOCS / ref.split("#")[0]).exists():
                    raise ValueError(f"Broken evidence link: {source_id}: {ref}")
            annotations[source_id] = {**row, "classified_on": AS_OF, "triage_file": file.name}
    if set(annotations) != source_ids:
        raise ValueError({"missing_triage": sorted(source_ids - set(annotations)), "unknown_triage": sorted(set(annotations) - source_ids)})
    return annotations


def sort_key(row):
    triage = row["triage"]
    period = triage["data_sort_period"]
    parts = [int(part) for part in period.split("-")] if period else []
    # Zero means unknown date precision, never an asserted January/first-of-month observation.
    newest_first = tuple(-part for part in parts + [0] * (3 - len(parts)))
    return (*newest_first, list(PRIORITY).index(triage["review_priority"]), row["name"].casefold())


def table_row(row):
    triage = row["triage"]
    source = f"<a id=\"source-{row['id'].lower()}\"></a>**{row['id']}** · [{cell(row['name'])}]({row['url']})"
    evidence = triage["evidence_refs"][0]
    dates = f"{cell(triage['data_dates'])}<br>[{DATE_BASIS[triage['date_basis']]}]({evidence})"
    role = f"**{PRIORITY[triage['review_priority']]}** — {cell(triage['model_role'])}"
    access = f"{cell(row['access'])}<br>{cell(row['rights']).rstrip('.')}. {cell(row['limitations'])}"
    return f"| {source} | {dates} | {cell(triage['scale'])} | {role} | {access} |"


def main():
    combined = []
    for file in sorted(DOCS.glob("*-sources.json")):
        rows = json.loads(file.read_text(encoding="utf-8-sig"))
        for row in rows:
            if REQUIRED - row.keys():
                raise ValueError(f"Missing fields {file.name}: {row.get('id')}: {REQUIRED-row.keys()}")
            if urlparse(row["url"]).scheme not in ("http", "https"):
                raise ValueError("Invalid URL: " + row["url"])
            combined.append({**row, "register_file": file.name})
    if len({r["id"] for r in combined}) != len(combined):
        raise ValueError("Duplicate source IDs")
    source_ids = {row["id"] for row in combined}
    annotations = load_triage(source_ids)
    for row in combined:
        row["triage"] = {key: value for key, value in annotations[row["id"]].items() if key != "id"}
    count = len(combined)
    unique = len({r["url"] for r in combined})
    lines = ["# Tennis data source register", "",
             f"**{count} investigated records, {unique} distinct main URLs, organized by data date and scale.** All sources are retained, including mirrors, private leads, tools, rights announcements and negative findings. This is not a count of independent datasets.", "",
             "**Organized 11 September 2026.** Data measurements remain the 10 September audit or explicitly labeled older local snapshots. Selected primary documentation was revisited on 11 September; this is not a fresh download of every dataset. The [complete JSON register](source-register.json) retains every original coverage, granularity, access, rights, evidence and provenance field, plus date/scale/priority annotations. See the [research synthesis](README.md) for detailed findings.", "", INTRO, "",
             "## Coverage of this organization", "",
             "| Section | 2026 | 2025 | 2024 or earlier | Date unknown | Supporting | Total |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    seen = []
    for title, anchor, files in LANES:
        rows = [row for row in combined if row["register_file"] in files]
        counts = Counter(row["triage"]["recency_band"] for row in rows)
        lines.append(f"| [{title}](#{anchor}) | " + " | ".join(str(counts[band]) for band in RECENCY) + f" | {len(rows)} |")
    lines.append("")
    for title, anchor, files in LANES:
        rows = [row for row in combined if row["register_file"] in files]
        lines.extend([f"## {title}", "", f"**{len(rows)} records.** Date groups come first; scale groups sit inside each date group.", ""])
        for band, label in RECENCY.items():
            dated = [row for row in rows if row["triage"]["recency_band"] == band]
            if not dated:
                continue
            lines.extend([f"### {label}", ""])
            for scale, scale_label in SCALE.items():
                selected = [row for row in dated if row["triage"]["scale_band"] == scale]
                if not selected:
                    continue
                lines.extend([f"#### {scale_label} ({len(selected)})", "",
                              "| Source | Data dates / evidence | Scale and population | Review priority and model use | Access, rights and limitations |",
                              "|---|---|---|---|---|"])
                for row in sorted(selected, key=sort_key):
                    lines.append(table_row(row))
                    seen.append(row["id"])
                lines.append("")
    if len(seen) != count or set(seen) != source_ids:
        raise ValueError("Not every source was rendered exactly once")
    lines.extend(["## Maintenance", "",
                  "The original `*-sources.json` files hold source evidence. The [public](source-triage-public.json), [commercial/private](source-triage-commercial.json) and [odds/market](source-triage-odds.json) triage files hold editorial classifications and supporting references, dated 11 September 2026. `data_sort_period` preserves the known year, month or day for ordering the described evidence; it is not a promise of complete archive coverage. The [generator](../../../src/eda/tennis_data_audit/build_source_register.py) merges them into this page and the full register, rejecting missing/duplicate IDs, invalid labels and broken local evidence links. Refresh evidence before promoting unknown cutoffs to current coverage.", ""])
    (DOCS / "source-register.json").write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (DOCS / "source-register.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"source_records": count, "distinct_main_urls": unique, "classified_records": len(annotations), "rendered_records": len(seen), "registry_validation": "pass"}))


if __name__ == "__main__":
    main()
