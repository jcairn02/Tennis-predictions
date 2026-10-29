"""The holdout register and the look ledger (docs/holdouts/README.md; decision:
docs/decisions/2026-10-29-holdout-soft-rule.md).

register.csv lists the protected periods: recent matches kept unseen for one question each. looks.csv logs every read
of recent results, and the decisions that rest on those reads. Both serve a soft rule: the owner may spend, move or
read a period; agents ask before measuring what a period protects, and log every read without being asked.

Run:
    ./python.sh src/eda/holdouts/ledger.py check --from <day> --to <day> [--tours atp|wta|both] [--levels tour|lower|all]
        the open periods a window of match days touches, and what each protects
    ./python.sh src/eda/holdouts/ledger.py add --by "<who>" --from <day> --to <day> --tours <t> --levels <l>
            --model <main|womens|props|itf|...> --what "<what was measured>" --where <report or log>
            [--market "match winner"] [--options <k>] [--se <mLL>] [--periods H1,H2] [--done-on <day>] [--note "..."]
        appends a read; prints its id and the periods it touched (computed from the window unless --periods is given)
    ./python.sh src/eda/holdouts/ledger.py decide --by "<who>" --uses L0002,L0003 --what "<the decision>"
            --chose <reading|harm-check> --where <decision or report> [--done-on <day>] [--note "..."]
        appends a decision resting on logged reads
    ./python.sh src/eda/holdouts/ledger.py status
        per period: the reads that touched it, the decisions resting on them, and each decision's optimism terms
From Python:
    from src.eda.holdouts import ledger
    ledger.touched("2026-07-01", "2026-10-28", tours="atp", levels="tour")     # the register rows a window touches
    ledger.warn(first, last, tours="atp", levels="all", tool="harness.py")    # the same, said on stderr

Levels: "tour" is the main model's matches (ATP and WTA 250s and above, Slams included, main draws and their
qualifying); "lower" is Challengers, WTA 125s, ITF and their qualifying; "all" is both. The check compares days, tours
and levels only: each period's own source defines its exact matches, and --periods records a narrower touch.
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, datetime
from pathlib import Path

from scipy import integrate
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[3]
HOLDOUTS = ROOT / "docs" / "holdouts"
REGISTER = HOLDOUTS / "register.csv"
LOOKS = HOLDOUTS / "looks.csv"

REGISTER_COLUMNS = ["id", "name", "protects", "tours", "levels", "first_day", "last_day", "status", "read_plan",
                    "source", "note"]
LOOK_COLUMNS = ["id", "kind", "done_on", "logged", "by", "periods", "first_day", "last_day", "tours", "levels",
                "market", "model", "what", "options", "se_mll", "uses", "chose", "where", "note"]
TOURS = ("atp", "wta", "both")
LEVELS = ("tour", "lower", "all")
CHOSE = ("reading", "harm-check")


# ------------------------------------------------------------------------------------------------
# Reading

def _day(x) -> date:
    """A day from 'YYYY-MM-DD', a date, a datetime, a pandas Timestamp or a numpy datetime64."""
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def register(path: Path = REGISTER) -> list[dict]:
    """The protected periods, as written."""
    return _read(path)


def looks(path: Path = LOOKS) -> list[dict]:
    """The ledger's rows (reads and decisions), in order."""
    return _read(path)


def _choice(name: str, value: str, allowed: tuple) -> str:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(allowed)}, not {value!r}")
    return value


def touched(first, last, tours: str = "both", levels: str = "all", register_path: Path = REGISTER) -> list[dict]:
    """The register's periods, read or open, that a window of match days touches by days, tours and levels. A released
    period protects nothing and is left out."""
    lo, hi = _day(first), _day(last)
    if lo > hi:
        raise ValueError(f"the window starts after it ends: {lo} > {hi}")
    _choice("tours", tours, TOURS)
    _choice("levels", levels, LEVELS)
    out = []
    for r in register(register_path):
        if r["status"] == "released":
            continue
        start = _day(r["first_day"])
        end = _day(r["last_day"]) if r["last_day"] else date.max
        if hi < start or lo > end:
            continue
        if "both" not in (tours, r["tours"]) and tours != r["tours"]:
            continue
        if "all" not in (levels, r["levels"]) and levels != r["levels"]:
            continue
        out.append(r)
    return out


def warn(first, last, tours: str = "both", levels: str = "all", tool: str = "this tool",
         register_path: Path = REGISTER) -> list[dict]:
    """touched(), said on stderr with what each period protects and the soft rule. Returns the periods."""
    hits = touched(first, last, tours, levels, register_path)
    for r in hits:
        print(f"note: {tool}'s window {_day(first)} .. {_day(last)} reaches {r['id']}, {r['name']} (from "
              f"{r['first_day']}), which protects: {r['protects']} Soft rule: ask the owner before measuring that on "
              f"these matches, and log every read (docs/holdouts/README.md).", file=sys.stderr)
    return hits


# ------------------------------------------------------------------------------------------------
# Writing

def _next_id(path: Path, prefix: str) -> str:
    n = [int(r["id"][1:]) for r in looks(path) if r["id"][:1] == prefix and r["id"][1:].isdigit()]
    return f"{prefix}{(max(n) + 1) if n else 1:04d}"


def _append(path: Path, row: dict) -> None:
    new = not path.exists() or path.stat().st_size == 0
    if not new:
        with path.open("rb") as f:                       # a hand edit may have left the last line unterminated
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with path.open("a", newline="", encoding="utf-8") as g:
                    g.write("\r\n")
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOOK_COLUMNS)
        if new:
            w.writeheader()
        w.writerow(row)


def _required(**fields) -> None:
    for name, value in fields.items():
        if value is None or not str(value).strip():
            raise ValueError(f"--{name.replace('_', '-')} is required")


def _number(value, name: str, kind=float, least: float = 0):
    if value is None or str(value).strip() == "":
        return ""
    v = kind(value)
    if v < least:
        raise ValueError(f"--{name} must be at least {least}")
    return v


def _stamp(now: datetime | None) -> str:
    return (now or datetime.now().astimezone()).isoformat(timespec="minutes")


def add_look(by: str, first, last, tours: str, levels: str, model: str, what: str, where: str,
             market: str = "match winner", options=None, se_mll=None, periods: str | list | None = None,
             done_on=None, note: str = "", path: Path = LOOKS, register_path: Path = REGISTER,
             now: datetime | None = None) -> dict:
    """Appends a read of results and returns the row written. Its periods are those the window touches, unless
    `periods` names a narrower set (ids of the register)."""
    _required(by=by, model=model, what=what, where=where)
    lo, hi = _day(first), _day(last)
    hits = [r["id"] for r in touched(lo, hi, tours, levels, register_path)]
    if periods is not None:
        given = [p.strip() for p in (periods.split(",") if isinstance(periods, str) else periods) if p.strip()]
        known = {r["id"] for r in register(register_path)}
        unknown = [p for p in given if p not in known]
        if unknown:
            raise ValueError(f"--periods names no period of the register: {', '.join(unknown)}")
        hits = given
    row = {"id": _next_id(path, "L"), "kind": "look", "done_on": _day(done_on or _stamp(now)).isoformat(),
           "logged": _stamp(now), "by": by, "periods": ";".join(hits) or "none", "first_day": lo.isoformat(),
           "last_day": hi.isoformat(), "tours": tours, "levels": levels, "market": market or "match winner",
           "model": model, "what": what, "options": _number(options, "options", int, 1),
           "se_mll": _number(se_mll, "se"), "uses": "", "chose": "", "where": where, "note": note}
    _append(path, row)
    return row


def add_decision(by: str, uses: str | list, what: str, chose: str, where: str, done_on=None, note: str = "",
                 path: Path = LOOKS, now: datetime | None = None) -> dict:
    """Appends a decision resting on logged reads and returns the row written. Its periods are its reads' periods."""
    _required(by=by, what=what, where=where)
    _choice("chose", chose, CHOSE)
    read = {r["id"]: r for r in looks(path) if r["kind"] == "look"}
    ids = [u.strip() for u in (uses.split(",") if isinstance(uses, str) else uses) if u.strip()]
    unknown = [u for u in ids if u not in read]
    if not ids or unknown:
        raise ValueError(f"--uses must name logged reads (unknown: {', '.join(unknown) or 'none given'})")
    periods = sorted({p for u in ids for p in read[u]["periods"].split(";") if p and p != "none"})
    row = {c: "" for c in LOOK_COLUMNS}
    row.update({"id": _next_id(path, "D"), "kind": "decision", "done_on": _day(done_on or _stamp(now)).isoformat(),
                "logged": _stamp(now), "by": by, "periods": ";".join(periods) or "none", "what": what,
                "uses": ";".join(ids), "chose": chose, "where": where, "note": note})
    _append(path, row)
    return row


# ------------------------------------------------------------------------------------------------
# Reading back: how much each period has been used

def expected_max(k: int) -> float:
    """The expected maximum of k independent standard normals (0 for one option): the m_k of the clean-holdout
    rebuild's selection-bias arithmetic (docs/studies/clean_holdout_rebuild/02_contamination_and_forecast.md, § 1)."""
    if k <= 1:
        return 0.0
    return integrate.quad(lambda x: x * k * norm.pdf(x) * norm.cdf(x) ** (k - 1), -12, 12)[0]


def status(path: Path = LOOKS, register_path: Path = REGISTER) -> str:
    """Per period: the reads that touched it, the decisions resting on them and, for a decision the reading chose,
    each read's optimism term se x m_k (mLL, as if the read's window held the whole period; scale it by the share of
    the period's matches the window held, counted at the period's read)."""
    rows = looks(path)
    reads = [r for r in rows if r["kind"] == "look"]
    decided = [r for r in rows if r["kind"] == "decision"]
    by_id = {r["id"]: r for r in reads}
    out = []
    for p in register(register_path):
        pid = p["id"]
        mine = [r for r in reads if pid in r["periods"].split(";")]
        resting = [d for d in decided if pid in d["periods"].split(";")]
        span = f"from {p['first_day']}" + (f" to {p['last_day']}" if p["last_day"] else " (open)")
        out += [f"{pid}  {p['name']}  |  {p['tours']}, {p['levels']}, {span}  |  {p['status']}",
                f"    protects: {p['protects']}",
                f"    reads: {len(mine)}"]
        out += [f"      {r['id']}  {r['done_on']}  [{r['model']}]  {r['what']}" for r in mine]
        out.append(f"    decisions resting on them: {len(resting)}")
        for d in resting:
            out.append(f"      {d['id']}  {d['done_on']}  [{d['chose']}]  {d['what']}  (uses {d['uses'].replace(';', ', ')})")
            if d["chose"] == "harm-check":
                out.append("        optimism: about 0 (the reading could only veto)")
                continue
            for u in d["uses"].split(";"):
                r = by_id.get(u)
                if r is None or pid not in r["periods"].split(";"):
                    continue
                if r["options"] and r["se_mll"]:
                    k, se = int(r["options"]), float(r["se_mll"])
                    out.append(f"        optimism term {u}: se {se:g} x m_{k} {expected_max(k):.2f} = "
                               f"{se * expected_max(k):.3f} mLL, times the share of {pid}'s matches its window held")
                else:
                    out.append(f"        optimism term {u}: not computable (its options or se are not logged)")
        out.append("")
    seen = [r["id"] for r in rows]
    twice = sorted({i for i in seen if seen.count(i) > 1})
    if twice:
        out.append(f"warning: ids written twice (two sessions at once?): {', '.join(twice)}")
    return "\n".join(out).rstrip() + "\n"


# ------------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="the periods a window touches")
    c.add_argument("--from", dest="first", required=True)
    c.add_argument("--to", dest="last", required=True)
    c.add_argument("--tours", default="both", choices=TOURS)
    c.add_argument("--levels", default="all", choices=LEVELS)

    r = sub.add_parser("add", help="log a read of results")
    r.add_argument("--by", required=True)
    r.add_argument("--from", dest="first", required=True)
    r.add_argument("--to", dest="last", required=True)
    r.add_argument("--tours", required=True, choices=TOURS)
    r.add_argument("--levels", required=True, choices=LEVELS)
    r.add_argument("--model", required=True, help="main, womens, props, itf, or another model's name")
    r.add_argument("--what", required=True, help="what was measured, in plain words")
    r.add_argument("--where", required=True, help="the report or process log that holds it")
    r.add_argument("--market", default="match winner")
    r.add_argument("--options", help="the options the reading chose among, the status quo included (adopt or not = 2)")
    r.add_argument("--se", help="the standard error of the options' difference, in mLL")
    r.add_argument("--periods", help="the periods actually touched, when narrower than the window's (e.g. H1)")
    r.add_argument("--done-on", help="the day of the read, when not today")
    r.add_argument("--note", default="")

    d = sub.add_parser("decide", help="log a decision resting on logged reads")
    d.add_argument("--by", required=True)
    d.add_argument("--uses", required=True, help="the reads it rests on, e.g. L0002,L0003")
    d.add_argument("--what", required=True, help="the decision, in plain words")
    d.add_argument("--chose", required=True, choices=CHOSE,
                   help="reading: the reading chose; harm-check: the kind of change decided, the reading could only veto")
    d.add_argument("--where", required=True, help="the decision record or report")
    d.add_argument("--done-on", help="the day of the decision, when not today")
    d.add_argument("--note", default="")

    sub.add_parser("status", help="how much each period has been used")

    a = ap.parse_args(argv)
    try:
        if a.cmd == "check":
            hits = touched(a.first, a.last, a.tours, a.levels)
            if not hits:
                print(f"{_day(a.first)} .. {_day(a.last)} ({a.tours}, {a.levels}) touches no protected period.")
            for r in hits:
                print(f"{r['id']}  {r['name']}, from {r['first_day']} ({r['tours']}, {r['levels']}; {r['status']})\n"
                      f"    protects: {r['protects']}\n    source: {r['source']}")
            if hits:
                print("Soft rule: before measuring what a period protects on its matches, offer the owner the choice "
                      "(unless the instruction already says), and log every read (docs/holdouts/README.md).")
        elif a.cmd == "add":
            r = add_look(a.by, a.first, a.last, a.tours, a.levels, a.model, a.what, a.where, a.market, a.options,
                         a.se, a.periods, a.done_on, a.note)
            print(f"logged {r['id']}: periods {r['periods']}")
        elif a.cmd == "decide":
            r = add_decision(a.by, a.uses, a.what, a.chose, a.where, a.done_on, a.note)
            print(f"logged {r['id']}: periods {r['periods']}")
        else:
            sys.stdout.write(status())
    except ValueError as e:
        ap.error(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main())
