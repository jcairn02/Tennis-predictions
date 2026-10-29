"""The weekly check of Stage 4's event-country table (owner, 22 Oct 2026: "add the weekly check";
docs/studies/men_lower_level_fill/process_log.md, section 12). Every week new event names reach Stage 0 (a sponsor's
name, a renamed event: 22 in the four weeks to 19 Oct 2026, Shanghai among them), and an evaluation event missing from
data/studies/predictability_diagnostic/stage4_event_country.csv has no country: its home-country values are blank, the
timing code cannot place its time zone (Shanghai 2026's windows were 3 days wide, not 2), and the test
test_every_evaluation_event_name_is_in_the_country_table fails.

For each evaluation event name (tour, event_key) of the Stage 0 tables read that the table does not hold, the sources
that place events by their ids are read:
    the ATP's tournament list   data/raw/public_dump/mantennisdata/atp/tournaments.csv (refreshed on Mondays by the
                                daily task's speeds job): each ATP tournament id's country code (YYYY-CODE: the first
                                two parts of Stage 0's id); New Caledonia and Guadeloupe read as France, as the table
                                reads them
    the WTA's calendar          as stage4_country.check() links it (tournament number and year)
    tennis-data.co.uk           the Location of the matches Stage 1 links, read through stage4_country.CITY
A name every source that knows it places in one country is added (--apply) as a row for the whole name, with its basis
and the date. A name the sources place in two countries, or none, is left for a person: listed in the summary, and the
weekly task alerts. The table's existing rows are never changed.

Stage 0 tables read: the repository's (the test's view), plus any --stage0 folder (the weekly task passes the coverage
job's Stage 0 built that day from today's files, so names reach the table before the next shared-table rebuild).
Writes data/studies/predictability_diagnostic/country_weekly/summary.json and proposals.csv (this run), and appends
each added row to added.csv. Exit 0: no name left without a country; 3: some left for a person; 1: an error.
Run: ./python.sh src/eda/predictability_diagnostic/stage4_country_weekly.py [--stage0 <folder>] [--apply]
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_country as CTRY  # noqa: E402

ATP_LIST = ROOT / "data" / "raw" / "public_dump" / "mantennisdata" / "atp" / "tournaments.csv"
OUT = C.OUT / "country_weekly"
TERRITORY = {"CAL": "FRA", "NCL": "FRA", "GLP": "FRA", "GUD": "FRA", "REU": "FRA", "MTQ": "FRA", "PYF": "FRA"}
COLUMNS = ["tour", "event_key", "from_year", "to_year", "tournament_id", "country", "basis"]


def evaluation_events(folders: list[Path]) -> pd.DataFrame:
    """The evaluation matches of each Stage 0 folder (match_id, tour, year, tournament_id, tournament_name,
    tournament_date, event_key), duplicates by match id dropped."""
    cols = ["match_id", "tour", "year", "evaluation", "tournament_id", "tournament_name", "tournament_date"]
    parts = []
    for f in folders:
        p = Path(f) / "stage0_matches.parquet"
        if p.exists():
            m = pd.read_parquet(p, columns=cols)
            parts.append(m[m["evaluation"].astype(bool)].drop(columns="evaluation"))
    ev = pd.concat(parts, ignore_index=True).drop_duplicates("match_id")
    ev["event_key"] = ev["tournament_name"].map(CTRY.event_key)
    return ev.reset_index(drop=True)


def missing(ev: pd.DataFrame, table: pd.DataFrame) -> pd.DataFrame:
    have = set(zip(table["tour"], table["event_key"]))
    return ev[[(t, k) not in have for t, k in zip(ev["tour"], ev["event_key"])]].reset_index(drop=True)


def atp_readings(miss: pd.DataFrame, atp: pd.DataFrame) -> pd.DataFrame:
    """(match_id, source, country, place) from the ATP's list, by the first two parts of the tournament id."""
    a = miss[miss["tour"].eq("atp")]
    key = a["tournament_id"].astype(str).str.extract(r"^(\d{4}-\d+)")[0]
    lst = atp.dropna(subset=["country_code"]).drop_duplicates("id").set_index("id")
    c = key.map(lst["country_code"]).map(lambda x: TERRITORY.get(x, x) if isinstance(x, str) else None)
    place = key.map(lst["location"])
    out = pd.DataFrame({"match_id": a["match_id"].to_numpy(), "source": "the ATP's tournament list",
                        "country": c.to_numpy(), "place": place.to_numpy()})
    return out[out["country"].notna()]


def wta_readings(miss: pd.DataFrame, editions: pd.DataFrame) -> pd.DataFrame:
    """(match_id, source, country, place) from the WTA's calendar, linked as stage4_country.check() links it."""
    w = miss[miss["tour"].eq("wta")]
    num = w["tournament_id"].astype(str).str.extract(r"^\d{4}-[A-Z]?0*(\d+)$")[0]
    e = editions.assign(tid=editions["tournament_id"].astype(str).str.lstrip("0"),
                        year=editions["year"].astype(int)).drop_duplicates(["tid", "year"])
    j = pd.DataFrame({"match_id": w["match_id"].to_numpy(), "tid": num.to_numpy(),
                      "year": w["year"].astype(int).to_numpy()}).merge(e[["tid", "year", "country"]],
                                                                       on=["tid", "year"], how="left")
    j["c"] = j["country"].map(CTRY.wta_country)
    out = pd.DataFrame({"match_id": j["match_id"], "source": "the WTA's calendar", "country": j["c"],
                        "place": j["country"]})
    return out[out["country"].notna()]


def td_readings(miss: pd.DataFrame, odds: Path = CTRY.ODDS) -> pd.DataFrame:
    """(match_id, source, country, place) from tennis-data's Location, for the matches Stage 1 links."""
    if not odds.exists() or not len(miss):
        return pd.DataFrame(columns=["match_id", "source", "country", "place"])
    o = pd.read_parquet(odds, columns=["match_id", "td_file", "td_row"])
    o = o[o["td_file"].notna() & o["match_id"].isin(set(miss["match_id"]))]
    parts = []
    for f, g in o.groupby("td_file"):
        loc = pd.read_parquet(ROOT / f, columns=["Location"])["Location"].to_numpy()
        parts.append(pd.DataFrame({"match_id": g["match_id"].to_numpy(),
                                   "place": loc[g["td_row"].astype(int).to_numpy()]}))
    if not parts:
        return pd.DataFrame(columns=["match_id", "source", "country", "place"])
    t = pd.concat(parts, ignore_index=True)
    t["place"] = t["place"].map(lambda s: CTRY.ascii_fold(s) if isinstance(s, str) else None)
    t["country"] = t["place"].map(CTRY.CITY)
    t["source"] = "tennis-data's Location"
    return t[t["country"].notna()][["match_id", "source", "country", "place"]]


def decide(miss: pd.DataFrame, readings: pd.DataFrame) -> pd.DataFrame:
    """One row per missing (tour, event_key): its names, matches, dates and ids, every source's countries, and the
    decision: 'add' when the sources that know it give one country, else 'person' (none, or more than one)."""
    r = readings.merge(miss[["match_id", "tour", "event_key"]], on="match_id", how="inner")
    rows = []
    for (tour, key), g in miss.groupby(["tour", "event_key"], sort=True):
        rg = r[(r["tour"] == tour) & (r["event_key"] == key)]
        countries = sorted(set(rg["country"].dropna()))
        by_source = {s: sorted(set(x["country"])) for s, x in rg.groupby("source")}
        places = {s: sorted({str(p) for p in x["place"].dropna()}) for s, x in rg.groupby("source")}
        if len(countries) == 1:
            decision, why = "add", ""
        elif countries:
            decision, why = "person", f"the sources place it in {len(countries)} countries ({', '.join(countries)})"
        else:
            decision, why = "person", "no source places it"
        rows.append({"tour": tour, "event_key": key,
                     "names": "; ".join(sorted(set(g["tournament_name"].astype(str)))),
                     "matches": int(len(g)), "first": str(pd.to_datetime(g["tournament_date"]).min().date()),
                     "last": str(pd.to_datetime(g["tournament_date"]).max().date()),
                     "tournament_ids": "; ".join(sorted(set(g["tournament_id"].astype(str)))),
                     "country": countries[0] if len(countries) == 1 else None,
                     "sources": json.dumps(by_source), "places": json.dumps(places), "decision": decision, "why": why})
    return pd.DataFrame(rows, columns=["tour", "event_key", "names", "matches", "first", "last", "tournament_ids",
                                       "country", "sources", "places", "decision", "why"])


def basis(row: pd.Series, today: str) -> str:
    places = json.loads(row["places"])
    parts = [f"{s}: {', '.join(p)}" if p else s for s, p in sorted(places.items())]
    return f"{'; '.join(parts)} (the weekly check, {today})"


def add_rows(table_path: Path, rows: list[list[str]]) -> list[tuple[str, str]]:
    """The rows added to the table in its sorted place (tour, event_key), its existing rows untouched, LF endings,
    written through a temporary file. The table is read again here, so a row another writer added meanwhile is kept
    and a key now present is not added twice. Returns the (tour, event_key) pairs added."""
    head, *body = [ln for ln in table_path.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n") if ln]
    if head.split(",") != COLUMNS:
        raise SystemExit(f"{table_path}: unexpected header {head!r}")
    current = pd.read_csv(io.StringIO("\n".join([head] + body)), dtype=str, keep_default_na=False)
    have = set(zip(current["tour"], current["event_key"]))
    new = [r for r in rows if (r[0], r[1]) not in have]
    if not new:
        return []
    old = list(current.itertuples(index=False, name=None))
    keyed = [(r[0], r[1], 0, i, list(r)) for i, r in enumerate(old)] + [(r[0], r[1], 1, i, r) for i, r in enumerate(new)]
    keyed.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    buf = io.StringIO()
    pd.DataFrame([k[4] for k in keyed], columns=COLUMNS).to_csv(buf, index=False, lineterminator="\n")
    tmp = table_path.with_name(table_path.name + ".part")
    tmp.write_bytes(buf.getvalue().encode("utf-8"))
    os.replace(tmp, table_path)
    return [(r[0], r[1]) for r in new]


def run(folders: list[Path], apply: bool, today: str | None = None) -> dict:
    today = today or dt.date.today().isoformat()
    table = CTRY.load_table()
    ev = evaluation_events(folders)
    miss = missing(ev, table)
    readings = pd.concat([atp_readings(miss, pd.read_csv(ATP_LIST, usecols=["id", "location", "country_code"],
                                                         dtype=str)),
                          wta_readings(miss, pd.read_parquet(CTRY.WTA_EDITIONS, columns=["tournament_id", "year",
                                                                                         "country"])),
                          td_readings(miss)], ignore_index=True)
    d = decide(miss, readings)
    OUT.mkdir(parents=True, exist_ok=True)
    added: list[tuple[str, str]] = []
    if apply and (d["decision"] == "add").any():
        rows = [[r["tour"], r["event_key"], "", "", "", r["country"], basis(r, today)]
                for _, r in d[d["decision"] == "add"].iterrows()]
        added = add_rows(CTRY.TABLE, rows)
    was_added = pd.Series([(t, k) in set(added) for t, k in zip(d["tour"], d["event_key"])], index=d.index, dtype=bool)
    if was_added.any():
        f = OUT / "added.csv"
        d[was_added].assign(added_on=today).to_csv(f, mode="a", header=not f.exists(), index=False,
                                                     lineterminator="\n")
    d.to_csv(OUT / "proposals.csv", index=False, lineterminator="\n")
    person = d[d["decision"] == "person"]
    got = d[was_added]
    summary = {"as_of": today, "stage0_folders": [str(f) for f in folders], "applied": apply,
               "evaluation_names": int(ev[["tour", "event_key"]].drop_duplicates().shape[0]),
               "missing_names": int(len(d)), "added": len(added),
               "added_names": [f"{t}|{k}|{c}" for t, k, c in zip(got["tour"], got["event_key"], got["country"])],
               "would_add": [] if apply else d.loc[d["decision"] == "add", ["tour", "event_key", "country"]]
               .to_dict("records"),
               "for_a_person": [f"{t}|{k}" for t, k in zip(person["tour"], person["event_key"])],
               "for_a_person_detail": person[["tour", "event_key", "names", "matches", "first", "last",
                                              "tournament_ids", "why"]].to_dict("records")}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage0", action="append", default=[], help="another Stage 0 folder to read (repeatable)")
    ap.add_argument("--apply", action="store_true", help="add the names the sources place in one country")
    a = ap.parse_args()
    folders = [C.MATCHES.parent] + [Path(f) for f in a.stage0]
    s = run(folders, a.apply)
    print(json.dumps({k: s[k] for k in ("as_of", "evaluation_names", "missing_names", "added", "added_names",
                                        "would_add", "for_a_person")}, indent=1, default=str))
    return 3 if s["for_a_person"] else 0


if __name__ == "__main__":
    sys.exit(main())
