"""Gap sources, lane A: women's website-only Tennis Abstract charts of 2018-2026 and the Hugging Face copy.

Reads:
* data/studies/granular_data_leads/tennis_abstract_chart_gap.csv: every chart id on the Tennis Abstract index
  (meta.html of 23 Sep 2026) or in the Match Charting Project export; website-only = on_website and not
  in_export.
* data/raw/gap_sources/ramizheman/_tree_9a1fc64.json: the file listing of the Hugging Face dataset
  ramizheman/TennisNLData at commit 9a1fc64da03bcc2abccd80d9d2d32389a4adcf81 (fetched from the public Hub API
  if missing). Each file is named <date>_<event>[_<round>]_<player 1>_vs_<player 2>.json and holds one chart
  (its match.raw_text field is the chart id); files are mapped to chart ids by date and both player names.
* data/studies/data_map/matches.parquet: the data map's women's rows (gap women_shots = tour W, levels GS, FIN,
  T1000, T500, T250, years 2018-2026, best grain below shot).

Links each women's website-only chart of 2018-2026 to a data-map row: a women's match with both surnames whose
listed date lies from 21 days before to 7 days after the chart date (the map lists most matches under the
tournament's start date, and some WTA Finals rows under shifted dates) and whose tournament name shares a word
with the chart's event. The level comes from the linked row, or is guessed from the event name (the most common
level of that tournament name in the map; qualifying rounds as GSQ / TQ) when unlinked.

Writes:
* data/studies/gap_sources/women_charts.csv: one row per women's website-only chart of 2018-2026.
* data/studies/gap_sources/women_charts_summary.json: counts by year, level and HF presence.
Run: ./python.sh src/eda/gap_sources/women_charts.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd
import requests

from hawkilol_matches import norm

ROOT = Path(__file__).resolve().parents[3]
GAP = ROOT / "data" / "studies" / "granular_data_leads" / "tennis_abstract_chart_gap.csv"
HF_DIR = ROOT / "data" / "raw" / "gap_sources" / "ramizheman"
HF_SHA = "9a1fc64da03bcc2abccd80d9d2d32389a4adcf81"
TREE = HF_DIR / f"_tree_{HF_SHA[:7]}.json"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
OUT = ROOT / "data" / "studies" / "gap_sources"
TARGET = ["GS", "FIN", "T1000", "T500", "T250"]
# later name -> earlier name, both ways (the chart id keeps the name used when charted)
ALIAS = {"HRUNCAKOVA": "KUZMOVA", "BAINDL": "KOZLOVA", "SAVILLE": "GAVRILOVA", "HUNTER": "SANDERS",
         "AMRITRAJ": "RISKE", "GORGES": "GOERGES"}
ALIAS.update({v: k for k, v in list(ALIAS.items())})


def load_tree() -> list[dict]:
    if not TREE.exists():
        out, url = [], f"https://huggingface.co/api/datasets/ramizheman/TennisNLData/tree/{HF_SHA}?recursive=true"
        while url:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            out.extend(r.json())
            m = re.search(r'<([^>]+)>;\s*rel="next"', r.headers.get("Link", ""))
            url = m.group(1) if m else None
        TREE.parent.mkdir(parents=True, exist_ok=True)
        TREE.write_text(json.dumps(out), encoding="utf-8")
    return [e for e in json.loads(TREE.read_text(encoding="utf-8")) if e["path"].endswith(".json")]


def chart_parts(cid: str) -> dict:
    p = cid.split("-")
    return {"date": p[0], "tour": p[1], "event": "-".join(p[2:-3]), "round": p[-3], "p1": p[-2], "p2": p[-1]}


def hf_to_chart(files: list[dict], chart_ids: list[str]) -> dict[str, list[str]]:
    """chart id -> HF file names (date equal, player 2 equal, player 1 a suffix of the text before '_vs_')."""
    by_date = defaultdict(list)
    for cid in chart_ids:
        c = chart_parts(cid)
        by_date[c["date"]].append((cid, norm(c["p1"]), norm(c["p2"])))
    hits = defaultdict(list)
    for e in files:
        stem = e["path"][:-5]
        if "_vs_" not in stem:
            continue
        date, rest = stem[:10].replace("-", ""), stem[11:]
        left, right = rest.rsplit("_vs_", 1)
        nl, nr = norm(left), norm(right)
        for cid, n1, n2 in by_date.get(date, []):
            if n2 == nr and nl.endswith(n1):
                hits[cid].append(e["path"])
    return hits


EVENT_ALIAS = {"NURNBERG": "NUREMBERG", "JIANGXI": "JIUJIANG", "BJK": "BILLIE", "ROSMALEN": "HERTOGENBOSCH",
               "SHERTOGENBOSCH": "HERTOGENBOSCH", "QUEENS": "QUEEN", "PETERSBURG": "PETERSBURG"}
EVENT_STOP = {"ITF", "WTA", "THE", "OPEN", "INTERNATIONAL", "CLASSIC", "TROPHY", "CHAMPIONSHIPS", "CUP"}


def event_tokens(name: str) -> set[str]:
    """Normalised word tokens of a tournament name, for comparing chart events with data-map names."""
    raw = {norm(t) for t in re.split(r"[^A-Za-z]+", str(name))}
    toks = {EVENT_ALIAS.get(t, t) for t in raw if len(t) >= 2 and t not in EVENT_STOP}
    return toks or {norm(name)}


def last_tokens(name: str) -> set[str]:
    toks = [norm(t) for t in re.split(r"[\s_\-]+", str(name)) if norm(t)]
    out = {toks[-1]} if toks else set()
    return out | {ALIAS[t] for t in out if t in ALIAS}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    gap = pd.read_csv(GAP, dtype=str)
    files = load_tree()
    hf = hf_to_chart(files, gap["chart_id"].tolist())

    w = gap[(gap["tour"] == "women") & (gap["on_website"] == "True") & (gap["in_export"] == "False")].copy()
    w["year"] = w["date"].str[:4].astype(int)
    w_all_years = len(w)
    w = w[w["year"].between(2018, 2026)].copy()

    mp = pd.read_parquet(MAP, columns=["uid", "tour", "level", "draw", "year", "d", "name1", "name2", "tname",
                                       "best"])
    mp = mp[(mp["tour"] == "W") & mp["year"].between(2017, 2026)].copy()
    tok_index: dict[str, set[int]] = defaultdict(set)
    toks1 = {}
    toks2 = {}
    for i, n1, n2 in zip(mp.index, mp["name1"], mp["name2"]):
        t1 = {norm(t) for t in re.split(r"[\s\-]+", str(n1)) if len(norm(t)) >= 2}
        t2 = {norm(t) for t in re.split(r"[\s\-]+", str(n2)) if len(norm(t)) >= 2}
        toks1[i], toks2[i] = t1, t2
        for t in t1 | t2:
            tok_index[t].add(i)
    # event name -> modal level among women's rows 2018-2026 (tournament names without trailing numbers)
    ev_level = Counter()
    for tname, level in zip(mp["tname"].fillna(""), mp["level"]):
        ev_level[(norm(re.sub(r"\s+\d+$", "", tname)), level)] += 1
    ev_best: dict[str, str] = {}
    for (ev, level), n in sorted(ev_level.items(), key=lambda x: -x[1]):
        ev_best.setdefault(ev, level)
    ev_keys = sorted(ev_best, key=len, reverse=True)

    rows = []
    for _, r in w.iterrows():
        c = chart_parts(r["chart_id"])
        date = pd.Timestamp(c["date"])
        a, b = last_tokens(c["p1"]), last_tokens(c["p2"])
        cand = set().union(*(tok_index.get(t, set()) for t in a)) & set().union(*(tok_index.get(t, set()) for t in b))
        cand = [i for i in cand if (toks1[i] & a and toks2[i] & b) or (toks1[i] & b and toks2[i] & a)]
        cand = [i for i in cand if date - pd.Timedelta(days=21) <= mp.at[i, "d"] <= date + pd.Timedelta(days=7)]
        ev_t = event_tokens(c["event"])
        scored = sorted(((len(ev_t & event_tokens(mp.at[i, "tname"])), mp.at[i, "d"], i) for i in cand),
                        reverse=True)
        link, m = "none", None
        if scored and scored[0][0] > 0:
            m = mp.loc[scored[0][2]]
            link = "one" if len(cand) == 1 else f"best of {len(cand)}"
        elif scored:
            link = f"event differs ({len(cand)})"  # same players met elsewhere within the window
        ev = norm(c["event"])
        ev_guess = next((ev_best[k] for k in ev_keys if k and ev.startswith(k)), None)
        if ev_guess and re.fullmatch(r"Q\d", c["round"]):
            ev_guess = "GSQ" if ev_guess == "GS" else "TQ"  # qualifying round of that event
        level = m["level"] if m is not None else ev_guess
        in_gap = (m is not None and m["level"] in TARGET and m["best"] != "shot")
        rows.append({
            "chart_id": r["chart_id"], "date": r["date"], "year": r["year"], "event": c["event"],
            "round": c["round"], "player1": c["p1"].replace("_", " "), "player2": c["p2"].replace("_", " "),
            "in_hf_copy": r["chart_id"] in hf, "hf_files": ";".join(hf.get(r["chart_id"], [])),
            "level_guess": level, "level_source": "data map row" if m is not None else
            ("event name" if ev_guess else "unknown"),
            "map_uid": int(m["uid"]) if m is not None else None,
            "map_tname": m["tname"] if m is not None else None,
            "map_draw": m["draw"] if m is not None else None,
            "map_best": m["best"] if m is not None else None, "map_link": link,
            "in_women_shots_gap": bool(in_gap),
            "target_level_unlinked": m is None and ev_guess in TARGET,
            "url": r["url"],
        })
    t = pd.DataFrame(rows).sort_values(["date", "chart_id"])
    t.to_csv(OUT / "women_charts.csv", index=False)

    def cube(frame: pd.DataFrame, keys: list[str]) -> dict:
        return {"|".join(map(str, k if isinstance(k, tuple) else (k,))): int(v)
                for k, v in frame.groupby(keys).size().items()}

    target = t[t["level_guess"].isin(TARGET)]
    in_gap = t[t["in_women_shots_gap"]]
    by_year = []
    for y in range(2018, 2027):
        ty, tg, tt = t[t["year"] == y], in_gap[in_gap["year"] == y], target[target["year"] == y]
        by_year.append({"year": y, "website_only": len(ty), "in_hf": int(ty["in_hf_copy"].sum()),
                        "target_levels": len(tt), "target_levels_in_hf": int(tt["in_hf_copy"].sum()),
                        "in_gap_linked": len(tg), "in_gap_linked_in_hf": int(tg["in_hf_copy"].sum()),
                        "in_gap_linked_website_only_not_hf": int((~tg["in_hf_copy"]).sum())})
    hf_women = sum(1 for cid in hf if chart_parts(cid)["tour"] == "W")
    summary = {
        "hf": {"dataset": "ramizheman/TennisNLData", "commit": HF_SHA, "json_files": len(files),
               "bytes": sum(e.get("size", 0) for e in files),
               "files_mapped_to_chart_ids": sum(len(v) for v in hf.values()),
               "distinct_chart_ids": len(hf), "distinct_women_chart_ids": hf_women,
               "website_only_chart_ids": int(gap[gap["chart_id"].isin(hf.keys()) & (gap["on_website"] == "True")
                                                 & (gap["in_export"] == "False")].shape[0]),
               "women_website_only_chart_ids_all_years": int(gap[gap["chart_id"].isin(hf.keys())
                                                                 & (gap["tour"] == "women")
                                                                 & (gap["on_website"] == "True")
                                                                 & (gap["in_export"] == "False")].shape[0]),
               "files_not_mapped": [e["path"] for e in files
                                    if e["path"] not in {p for v in hf.values() for p in v}]},
        "women_website_only_all_years": w_all_years,
        "women_website_only_2018_2026": len(t),
        "in_hf_2018_2026": int(t["in_hf_copy"].sum()),
        "by_year": by_year,
        "by_level_guess": cube(t.fillna({"level_guess": "unknown"}), ["level_guess"]),
        "by_level_guess_and_hf": cube(t.fillna({"level_guess": "unknown"}), ["level_guess", "in_hf_copy"]),
        "level_source": cube(t, ["level_source"]),
        "map_link": cube(t, ["map_link"]),
        "in_gap_linked": len(in_gap), "in_gap_linked_in_hf": int(in_gap["in_hf_copy"].sum()),
        "in_gap_by_level": cube(in_gap, ["level_guess"]),
        "in_gap_by_level_and_hf": cube(in_gap, ["level_guess", "in_hf_copy"]),
        "target_level_unlinked": int(t["target_level_unlinked"].sum()),
        "linked_but_map_best_shot": int(((t["map_best"] == "shot")).sum()),
    }
    (OUT / "women_charts_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("by_year",)}, indent=1)[:4000])
    print(pd.DataFrame(by_year).to_string())


if __name__ == "__main__":
    main()
