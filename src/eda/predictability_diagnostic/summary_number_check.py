"""Predictability diagnostic, the summary's number check: every number in report.html traced to the JSON outputs.

What "every number" covers: the page as a browser renders it (headless Chromium through Playwright), so the tables,
charts and tooltips the page's scripts draw are included; every state of every control (each panel's buttons and
menus, all their combinations within the panel); every tooltip (each mark, hit area and heat cell is sent a pointer
event and the tooltip read); and the data block the scripts draw from (window.REPORT), number by number.

How a number is tied to its source:
    * Numbers the section modules print (Python). The report is rendered a second time with every JSON number replaced
      by a tagged number that carries its path (and keeps it through arithmetic); formatting a tagged number writes an
      invisible tag after it. Each printed number then names the JSON values it was computed from.
    * Numbers the page's scripts print. The browser's number formatting (toFixed, toLocaleString) is recorded, and
      every text the scripts write is linked to the value just formatted into it. That value, at full precision, is
      found among the JSON values (as is, x 100 or x 1000), which names its path.
    * Numbers in the data block must equal a JSON value at full precision.
Then the checks: the printed number must be the rounding of its source; where the context names a tour (a tile's
ATP/WTA, a chart's title, a table's group row, column or row header, "(men)" or "(women)" just after the number), a
season, a window of years or a level (in a table's headers), the source must be of the same; a number with no tag or
link must trace to a JSON value by value alone (weaker: with tens of thousands of values, a two- or three-digit number
almost always matches something), or to the derivation and constant rules below. Anything else is reported.

Reads docs/studies/predictability_diagnostic/report.html, the section modules and data/studies/predictability_diagnostic/
(its JSON and audit4/); writes summary_number_check.csv (one row per number in each distinct context) and
summary_number_check.json (the counts, the rules applied, everything left unexplained).
Run: ./python.sh src/eda/predictability_diagnostic/summary_number_check.py   (about a minute)
The browser is the Chromium Playwright installed (the newest ms-playwright/chromium_headless_shell-* folder).
"""
from __future__ import annotations

import builtins
import importlib.util
import json
import math
import operator
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2]))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

REPORT = C.DOCS / "report.html"
OUT_CSV = C.OUT / "summary_number_check.csv"
OUT_JSON = C.OUT / "summary_number_check.json"

# The JSON each section is built from (the section modules' load() calls). The summary copies from the stages, so its
# numbers may trace to its own file or to the files it copies.
SECTION_SOURCES = {
    "masthead": ["stage0_summary.json"],
    "foot": ["stage0_summary.json"],
    "data-used": ["stage0_summary.json", "stage0_checks.json"],
    "how-predictable": ["stage1_results.json", "stage1_baselines_summary.json", "stage1_odds_summary.json"],
    "anatomy": ["stage2_results.json", "stage2_pbp_results.json"],
    "traits": ["stage3_results.json"],
    "rundown": ["stage4_results.json"],
    "in-plain-terms": ["summary_results.json"],
    "summary": ["summary_results.json"],
}
SUMMARY_UPSTREAM = ["stage1_results.json", "stage2_results.json", "stage3_results.json", "stage4_results.json",
                    "audit4/scoring.json"]
SCALES = (1.0, 100.0, 1000.0)
TOUR_WORDS = {"atp": ("ATP", "men"), "wta": ("WTA", "women")}
LEVEL_WORDS = {"Grand Slams": "GS", "Tour Finals": "FIN", "1000s": "T1000", "500s": "T500", "250s": "T250",
               "Grand Slam qualifying": "GSQ", "Slam qualifying": "GSQ", "Tour qualifying": "TQ",
               "Challenger / WTA 125": "CH", "Challenger / 125 qualifying": "CHQ", "Team events": "TEAM"}
MARK = "⁣"                                        # an invisible separator: the server-side tag's delimiter
MARK_RE = re.compile(MARK + r"(\d+)" + MARK)
# A number: an optional minus (U+2212 or a hyphen) touching it, thousands separators, decimals, an exponent, a percent
# sign. Not part of a word or an id (R32, stage0, 2026-600); an en dash before it is a range's dash, not a sign.
NUM_RE = re.compile(r"(?<![\w.,/#\-−])([−-]?)(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?:e([−+-]?\d+))?(\s?%)?(?![\w.]\w|\w)")


# ------------------------------------------------------------------------------------------------ the JSON
ID_KEYS = ("tour", "window", "stat", "id", "form", "score", "group_kind", "group_name", "level", "qualifying", "surface",
           "best_of", "dim", "value", "odds_only", "years", "kind", "check", "rate", "basis", "population", "row", "label",
           "name", "group", "era", "season", "year", "subset", "key", "rule", "pass", "code", "source", "period", "cell",
           "status", "what", "variant", "statistic", "measure", "model", "inputs", "pair", "surfaces", "days", "n")
BOOL_ID_KEYS = ("qualifying", "odds_only")


def ident(rec: dict) -> str:
    return ",".join(f"{k}={rec[k]}" for k in ID_KEYS if k in rec and (
        (isinstance(rec[k], (str, int, float)) and not isinstance(rec[k], bool)) or (k in BOOL_ID_KEYS and isinstance(rec[k], bool))))


def flatten(obj, path: str, out: list) -> None:
    """Every finite number in a JSON document with a readable path; a list's records are named by their key fields."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            flatten(v, f"{path}.{k}" if path else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            flatten(v, f"{path}[{ident(v) or i}]" if isinstance(v, dict) else f"{path}[{i}]", out)
    elif isinstance(obj, bool) or obj is None:
        return
    elif isinstance(obj, (int, float)):
        if math.isfinite(obj):
            out.append((float(obj), path))


def tour_of(path: str) -> str | None:
    hit = {t for t in ("atp", "wta") if re.search(rf"(?:^|[.\[,=|]){t}(?:$|[.\[\],|_])", path)}   # tours.atp.x, points.atp[0]
    return hit.pop() if len(hit) == 1 else None


class Index:
    """The leaves of a set of JSON files, searchable by value at each display scale."""

    def __init__(self, files: list[str]):
        leaves = []
        for name in files:
            flatten(json.loads((C.OUT / name).read_text(encoding="utf-8")), name, leaves)
        self.signed = np.array([v for v, _ in leaves])
        self.paths = [p for _, p in leaves]
        self.tours = [tour_of(p) for p in self.paths]
        values = np.abs(self.signed)
        self.order = np.argsort(values)
        self.sorted = values[self.order]

    def find(self, value: float, half: float, scale: float) -> list[int]:
        lo, hi = (value - half) / scale, (value + half) / scale
        a, b = np.searchsorted(self.sorted, lo - 1e-12, "left"), np.searchsorted(self.sorted, hi + 1e-12, "right")
        return list(self.order[a:b])

    def derived(self):
        """Values a module computes from two leaves, built on first use: a coin's log loss (ln 2) minus a leaf (better
        than a coin); the sum or difference of two leaves of one record; the men's plus the women's value. Searched at
        full precision only (the data block's numbers, the values the scripts format): a chance match is then out of
        the question."""
        if hasattr(self, "_dv"):
            return self._dv, self._dp
        vals, prov = [], []
        ln2 = math.log(2)
        for i, v in enumerate(self.signed):
            if 0 < v < ln2:
                vals.append(ln2 - v)
                prov.append(("ln 2 minus", i, -1))
        groups = {}
        for i, p in enumerate(self.paths):
            groups.setdefault(p.rsplit(".", 1)[0], []).append(i)
        for idx in groups.values():
            if not 2 <= len(idx) <= 80:
                continue
            for a_pos, a in enumerate(idx):
                for b in idx[a_pos + 1:]:
                    x, y = self.signed[a], self.signed[b]
                    vals += [x + y, x - y, y - x]
                    prov += [("sum", a, b), ("difference", a, b), ("difference", b, a)]
        pairs = {}
        for i, p in enumerate(self.paths):
            if self.tours[i]:
                pairs.setdefault(re.sub(r"(?<=[.\[,=|])(atp|wta)(?=$|[.\],|_])", "*", p), []).append(i)
        for idx in pairs.values():
            if len(idx) == 2:
                vals.append(self.signed[idx[0]] + self.signed[idx[1]])
                prov.append(("men + women", idx[0], idx[1]))
        dv = np.abs(np.array(vals))
        order = np.argsort(dv)
        self._dv, self._dp = dv[order], [prov[k] for k in order]
        return self._dv, self._dp

    def find_derived(self, value: float, half: float, scale: float) -> list[tuple]:
        dv, dp = self.derived()
        lo, hi = (value - half) / scale, (value + half) / scale
        a, b = np.searchsorted(dv, lo - 1e-12, "left"), np.searchsorted(dv, hi + 1e-12, "right")
        return dp[a:b]

    def derived_value(self, prov: tuple) -> float:
        op, a, b = prov
        x = self.signed[a]
        return math.log(2) - x if op == "ln 2 minus" else x + self.signed[b] if op in ("sum", "men + women") else x - self.signed[b]

    def describe(self, prov: tuple) -> str:
        op, a, b = prov
        if op == "ln 2 minus":
            return f"ln 2 − {self.paths[a]}"
        return f"{self.paths[a]} {'−' if op == 'difference' else '+'} {self.paths[b]}"

    def exact(self, value: float, signed: bool = True) -> list[tuple]:
        """The leaves (or two-leaf values) equal to a full-precision value, at a scale of 1, 100 or 1000. Unsigned for
        the values the page's scripts format: they print the size and write the sign apart (Math.abs(v).toFixed(2))."""
        out = []
        tol = 1e-9 * max(1.0, abs(value))
        for s in SCALES:
            for i in self.find(abs(value), tol * s, s):
                if not signed or np.sign(self.signed[i]) == np.sign(value) or value == 0:
                    out.append((self.paths[i], s, self.tours[i]))
        if not out and value != 0:
            for s in SCALES:
                for prov in self.find_derived(abs(value), tol * s, s):
                    v = self.derived_value(prov)
                    if not signed or np.sign(v) == np.sign(value):
                        t = None if prov[0] == "men + women" else self.tours[prov[1]]
                        out.append((self.describe(prov), s, t))
        return out


_INDEX = {}


def section_index(section: str) -> Index:
    files = list(SECTION_SOURCES.get(section, []))
    if section in ("summary", "in-plain-terms"):
        files += SUMMARY_UPSTREAM
    key = tuple(files)
    if key not in _INDEX:
        _INDEX[key] = Index(files)
    return _INDEX[key]


# ------------------------------------------------------------------------------------------------ tagged numbers
PROV: list[tuple] = []                                 # (description, leaf paths, value) per formatted number


def _raw(x):
    return float.__float__(x) if isinstance(x, TF) else int.__int__(x) if isinstance(x, TI) else x


def _src(x):
    return (x.desc, x.leaves) if isinstance(x, (TF, TI)) else (repr(x), ())


def _wrap(v, desc, leaves):
    if isinstance(v, bool):
        return v
    if isinstance(v, int):
        return TI(v, desc, leaves)
    if isinstance(v, float):
        return TF(v, desc, leaves)
    return v


def _tag(s: str, x, spec: str) -> str:
    """Only formatting with a format spec is tagged ('{x:.2f}', '{n:,}'): a plain '{x}' builds keys and labels
    (years, ids) as often as it prints a value, and a tag inside a key would change what the module looks up."""
    if not spec:
        return s
    PROV.append((x.desc, x.leaves, float(_raw(x))))
    return f"{s}{MARK}{len(PROV) - 1}{MARK}"


class TF(float):
    """A JSON float that remembers where it came from."""

    def __new__(cls, v, desc, leaves):
        o = float.__new__(cls, v)
        o.desc, o.leaves = desc, leaves
        return o

    def __format__(self, spec):
        return _tag(format(_raw(self), spec), self, spec)

    def __round__(self, n=None):
        r = builtins.round(_raw(self), n)
        return _wrap(r, self.desc, self.leaves)

    def __neg__(self):
        return TF(-_raw(self), f"−{self.desc}", self.leaves)

    def __pos__(self):
        return self

    def __abs__(self):
        return TF(abs(_raw(self)), f"|{self.desc}|", self.leaves)


class TI(int):
    """A JSON integer that remembers where it came from."""

    def __new__(cls, v, desc, leaves):
        o = int.__new__(cls, v)
        o.desc, o.leaves = desc, leaves
        return o

    def __format__(self, spec):
        return _tag(format(_raw(self), spec), self, spec)

    def __round__(self, n=None):
        return self

    def __neg__(self):
        return TI(-_raw(self), f"−{self.desc}", self.leaves)

    def __pos__(self):
        return self

    def __abs__(self):
        return TI(abs(_raw(self)), f"|{self.desc}|", self.leaves)


def _binary(sym, fn):
    def forward(self, other):
        if not isinstance(other, (int, float)):
            return NotImplemented
        (da, la), (db, lb) = _src(self), _src(other)
        return _wrap(fn(_raw(self), _raw(other)), f"({da} {sym} {db})", la + lb)

    def reflected(self, other):
        if not isinstance(other, (int, float)):
            return NotImplemented
        (da, la), (db, lb) = _src(other), _src(self)
        return _wrap(fn(_raw(other), _raw(self)), f"({da} {sym} {db})", la + lb)
    return forward, reflected


for _name, _sym, _fn in (("add", "+", operator.add), ("sub", "−", operator.sub), ("mul", "×", operator.mul),
                         ("truediv", "/", operator.truediv), ("floordiv", "//", operator.floordiv),
                         ("mod", "%", operator.mod), ("pow", "^", operator.pow)):
    _f, _r = _binary(_sym, _fn)
    for _cls in (TF, TI):
        setattr(_cls, f"__{_name}__", _f)
        setattr(_cls, f"__r{_name}__", _r)


def tagged(obj, path: str):
    """A JSON document with every number replaced by a tagged number named by its path (as flatten() names it)."""
    if isinstance(obj, dict):
        return {k: tagged(v, f"{path}.{k}") for k, v in obj.items()}
    if isinstance(obj, list):
        return [tagged(v, f"{path}[{ident(v) or i}]" if isinstance(v, dict) else f"{path}[{i}]") for i, v in enumerate(obj)]
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, int):
        return TI(obj, path, (path,))
    if isinstance(obj, float):
        return TF(obj, path, (path,))
    return obj


def _t_float(x=0.0):
    if isinstance(x, TF):
        return x
    if isinstance(x, TI):
        return TF(float(_raw(x)), x.desc, x.leaves)
    return builtins.float(x)


def _t_int(x=0, *args):
    if isinstance(x, (TF, TI)) and not args:
        return TI(builtins.int(_raw(x)), x.desc, x.leaves)
    return builtins.int(x, *args)


def _t_round(x, n=None):
    return x.__round__(n) if isinstance(x, (TF, TI)) else builtins.round(x, n)


def render_tagged(out: Path, plant=None) -> None:
    """The report rendered with tagged numbers: render_report.py's own assembly, each section module loaded afresh with
    its JSON tagged and float, int and round made to keep the tags. A plant (self-test only) alters a tagged document
    after tagging, as a module reading the wrong record would."""
    spec = importlib.util.spec_from_file_location("render_report_tagged", HERE / "render_report.py")
    rr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rr)
    plain = rr.section_modules

    def load(study_dir, name):
        doc = tagged(json.loads((study_dir / name).read_text(encoding="utf-8")), name)
        if plant and plant["file"] == name:
            swap(doc, plant)
        return doc

    def tagged_modules():
        mods = plain()
        for mod in mods:
            mod.float, mod.int, mod.round = _t_float, _t_int, _t_round
            mod.load = load
        return mods
    rr.section_modules = tagged_modules
    rr.OUT = out
    rr.main()


# Planted errors for the self-test (--self-test): each makes a section module read another record than the one its
# text names, the commonest way a report shows a wrong number. The records' key field is exchanged after tagging, so
# the numbers keep the tags of where they really came from.
PLANTS = [
    {"name": "Stage 1 headline: the men's and women's 2022-2026 records exchanged", "file": "stage1_results.json",
     "list": ["headline"], "match": {"window": "2022-2026 (headline)"}, "field": "tour", "values": ["atp", "wta"]},
    {"name": "Stage 1 headline: the men's 2013-2026 and 2022-2026 records exchanged", "file": "stage1_results.json",
     "list": ["headline"], "match": {"tour": "atp"}, "field": "window", "values": ["2013-2026", "2022-2026 (headline)"]},
    {"name": "Stage 3 persistence: the men's and women's serve points won exchanged", "file": "stage3_results.json",
     "list": ["persistence"], "match": {"stat": "spw", "surface": "all"}, "field": "tour", "values": ["atp", "wta"]},
    {"name": "Stage 4 ranking: the men's and women's ratings through the iid model exchanged", "file": "stage4_results.json",
     "list": ["ranking"], "match": {"id": "rating_matchup"}, "field": "tour", "values": ["atp", "wta"]},
    {"name": "Summary chart: the men's and women's aces exchanged", "file": "summary_results.json",
     "list": ["chart", "points"], "match": {"stat": "ace"}, "field": "tour", "values": ["atp", "wta"]},
]


def swap(doc: dict, plant: dict) -> None:
    rows = doc
    for k in plant["list"]:
        rows = rows[k]
    a, b = plant["values"]
    picked = [r for r in rows if all(r.get(k) == v for k, v in plant["match"].items()) and r.get(plant["field"]) in (a, b)]
    for r in picked:
        r[plant["field"]] = b if r[plant["field"]] == a else a


# ------------------------------------------------------------------------------------------------ the browser
def chromium() -> str:
    root = Path(os.path.expandvars(r"%LOCALAPPDATA%")) / "ms-playwright"
    found = sorted(root.glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"))
    if not found:
        raise SystemExit(f"no headless Chromium under {root}")
    return str(found[-1])


# Recorded before the page's scripts run: each number the scripts format, and each text they write linked to the
# values formatted into it (the latest formatting that printed each number in the text).
HOOKS_JS = r"""
(() => {
  const calls = [];
  const keep = (out, input) => { calls.push([out, input]); if (calls.length > 40000) calls.splice(0, 10000); };
  const toFixed = Number.prototype.toFixed, toLocale = Number.prototype.toLocaleString;
  Number.prototype.toFixed = function (d) { const s = toFixed.call(this, d); keep(s, Number(this)); return s; };
  Number.prototype.toLocaleString = function (...a) { const s = toLocale.apply(this, a); keep(s, Number(this)); return s; };
  const desc = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
  Object.defineProperty(Node.prototype, 'textContent', {
    configurable: true, enumerable: desc.enumerable, get() { return desc.get.call(this); },
    set(v) {
      const links = [];
      String(v).replace(/\d[\d,]*(?:\.\d+)?/g, m => {
        for (let i = calls.length - 1; i >= 0; i--) if (calls[i][0] === m || calls[i][0] === '-' + m) { links.push([m, calls[i][1]]); break; }
        return m;
      });
      desc.set.call(this, v);
      Object.defineProperty(this, '__links', { value: links, configurable: true, writable: true, enumerable: false });
    }
  });
})();
"""

HARVEST_JS = r"""
(scope) => {
  const root = scope ? document.querySelector(scope) : document.body;
  const out = [];
  const BLOCK = 'p, li, td, th, dd, dt, h1, h2, h3, h4, summary, .tile, .note-small, .panel-head p, .lede, .status, .foot, .legend, .eyebrow, .controls, text';
  function headerGrid(table) {
    const grid = [];
    const rows = table.tHead ? [...table.tHead.rows] : [];
    rows.forEach((tr, r) => {
      grid[r] = grid[r] || [];
      let c = 0;
      [...tr.cells].forEach(cell => {
        while (grid[r][c] !== undefined) c++;
        const cs = cell.colSpan || 1, rs = cell.rowSpan || 1;
        for (let i = 0; i < rs; i++) for (let j = 0; j < cs; j++) { grid[r + i] = grid[r + i] || []; grid[r + i][c + j] = cell.textContent.trim(); }
        c += cs;
      });
    });
    return grid;
  }
  function cellContext(cell) {
    const table = cell.closest('table'); if (!table) return {};
    const tr = cell.parentElement;
    let col = 0;
    for (const c of tr.cells) { if (c === cell) break; col += c.colSpan || 1; }
    const heads = headerGrid(table).map(r => r[col]).filter(Boolean);
    let group = '';
    for (let r = tr.previousElementSibling; r; r = r.previousElementSibling) if (r.classList.contains('group')) { group = r.textContent.trim(); break; }
    const panel = table.closest('.panel');
    const before = [];                                  // the row's cells before this one: its labels
    for (const c of tr.cells) { if (c === cell) break; before.push(c.textContent.trim()); }
    return {col: heads.join(' | '), row: before.join(' | '), group,
            table: table.id || (panel && panel.querySelector('h3') ? panel.querySelector('h3').textContent.trim() : '')};
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode, text = node.textContent;
    if (!text.trim() || !/\d/.test(text)) continue;
    const el = node.parentElement;
    if (el.closest('script, style, #tip')) continue;
    const sec = el.closest('section.stage');
    const block = el.closest(BLOCK);
    const sub = el.closest('.sub');
    const svgText = el.closest('text');
    const tile = el.closest('.tile');
    const chart = el.closest('.chart, .chart-pair > div');   // a chart, or one tour's half of a pair (bars, heat tables)
    const td = el.closest('td, th');
    const pairDiv = el.closest('.pair > div');
    const item = {
      section: sec ? sec.id : (el.closest('.masthead') ? 'masthead' : (el.closest('.foot') ? 'foot' : 'page')),
      text, block: block ? block.textContent.replace(/\s+/g, ' ').trim().slice(0, 600) : '',
      code: !!el.closest('code'), heading: !!el.closest('h1, h2, h3, h4'), option: !!el.closest('option'),
      sub: sub && sub.querySelector('h3') ? sub.querySelector('h3').textContent.trim() : '',
      svg: svgText ? (svgText.getAttribute('class') || '') : null,
      chart: chart && chart.querySelector('h4') ? chart.querySelector('h4').textContent.trim() : '',
      tile: tile && tile.querySelector('.label') ? tile.querySelector('.label').textContent.trim() : '',
      tileTour: pairDiv && pairDiv.querySelector('small') ? pairDiv.querySelector('small').textContent.trim() : '',
      links: el.__links || [],
    };
    if (td) Object.assign(item, cellContext(td));
    out.push(item);
  }
  return out;
}
"""

TIPS_JS = r"""
(scope) => {
  const tip = document.getElementById('tip');
  const out = [];
  const root = scope ? document.querySelector(scope) : document;
  root.querySelectorAll('.hit, .mark, td.v, .cell').forEach(el => {
    tip.hidden = true;
    el.dispatchEvent(new PointerEvent('pointermove', {bubbles: false, clientX: 20, clientY: 20}));
    if (!tip.hidden) {
      const sec = el.closest('section.stage'), chart = el.closest('.chart');
      out.push({section: sec ? sec.id : 'page', lines: [...tip.children].map(d => [d.textContent, d.__links || []]),
                chart: chart && chart.querySelector('h4') ? chart.querySelector('h4').textContent.trim() : ''});
    }
  });
  tip.hidden = true;
  return out;
}
"""

CONTROLS_JS = r"""
() => {
  const panels = [];
  document.querySelectorAll('section.stage .panel').forEach((panel, pi) => {
    panel.setAttribute('data-check-panel', String(pi));
    const groups = [];
    panel.querySelectorAll('.seg').forEach(seg => {
      const btns = [...seg.querySelectorAll('button[type=button]')].filter(b => [...b.attributes].some(a => a.name.startsWith('data-')));
      if (!btns.length) return;
      const attr = [...btns[0].attributes].find(a => a.name.startsWith('data-')).name;
      groups.push({kind: 'button', attr, values: btns.map(b => b.getAttribute(attr)),
                   initial: (btns.find(b => b.getAttribute('aria-pressed') === 'true') || btns[0]).getAttribute(attr)});
    });
    panel.querySelectorAll('select').forEach(sel => groups.push({kind: 'select', id: sel.id, values: [...sel.options].map(o => o.value), initial: sel.value}));
    if (groups.length) panels.push({panel: String(pi), section: panel.closest('section.stage').id, groups});
  });
  return panels;
}
"""


def set_control(page, panel: str, g: dict, value: str) -> None:
    scope = f'[data-check-panel="{panel}"]'
    if g["kind"] == "button":
        page.click(f'{scope} button[{g["attr"]}="{value}"]')
    else:
        page.select_option(f'{scope} select#{g["id"]}', value)


def harvest_page(path: Path) -> dict:
    """Every text and tooltip of the page in every control state, with the scripts' formatting links."""
    from playwright.sync_api import sync_playwright
    items, tips, states, errors = [], [], [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium())
        page = browser.new_page(viewport={"width": 1280, "height": 1000})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.add_init_script(HOOKS_JS)
        page.goto(path.resolve().as_uri())
        page.wait_for_load_state("load")
        page.evaluate("() => document.querySelectorAll('details').forEach(d => { d.open = true; })")   # folded stages too

        def collect(label, scope):
            for it in page.evaluate(HARVEST_JS, scope):
                it["state"] = label
                items.append(it)
            for t in page.evaluate(TIPS_JS, scope):
                t["state"] = label
                tips.append(t)
        collect("default", None)
        report_data = page.evaluate("() => window.REPORT")
        for pnl in page.evaluate(CONTROLS_JS):
            combos = [[]]
            for g in pnl["groups"]:
                combos = [c + [(g, v)] for c in combos for v in g["values"]]
            for combo in combos:
                if all(v == g["initial"] for g, v in combo):
                    continue
                for g, v in combo:
                    set_control(page, pnl["panel"], g, v)
                label = f'{pnl["section"]} panel {pnl["panel"]}: ' + ", ".join(f'{g.get("attr") or g.get("id")}={v}' for g, v in combo)
                states.append(label)
                collect(label, f'[data-check-panel="{pnl["panel"]}"]')
            for g in pnl["groups"]:
                set_control(page, pnl["panel"], g, g["initial"])
        browser.close()
    return {"items": items, "tips": tips, "states": states, "report_data": report_data, "page_errors": errors}


# ------------------------------------------------------------------------------------------------ the numbers
def parse(m: re.Match) -> dict:
    sign, whole, frac, exp, pc = m.groups()
    decimals = len(frac) - 1 if frac else 0
    v = float(whole.replace(",", "") + (frac or ""))
    e = int(exp.replace("−", "-")) if exp else 0
    v *= 10 ** e
    return {"token": m.group(0).strip(), "value": -v if sign else v, "abs": v, "signed": bool(sign),
            "decimals": decimals, "half": 0.5 * 10 ** (-decimals) * 10 ** e, "percent": bool(pc),
            "comma": "," in whole, "start": m.start(), "end": m.end(), "digits": whole + (frac or "")}


LEVEL_NAME = re.compile(r"(?:Challenger\s*/\s*)?(?:ATP|WTA)(?:'s)?\s*(?:125|250|500|1000)s?")


def tour_hint(item: dict, after: str) -> str | None:
    """The tour the context names for a number, or None: "(men)" or "(women)" just after it, or the tile, chart,
    table group row, column or row it sits in (level names such as "WTA 125" are not tours; "Men" is the men, "atp"
    in an id is not)."""
    m = re.match(r"\s*(?:\((men|women)(?:'s)?\s*[);,]|for the (men|women)\b)", after)
    if m:
        return "atp" if (m.group(1) or m.group(2)) == "men" else "wta"
    for field in ("tileTour", "chart", "group", "col", "row"):
        txt = LEVEL_NAME.sub("", item.get(field) or "")
        found = {t for t, ws in TOUR_WORDS.items()
                 if any(re.search(rf"\b{re.escape(w)}\b", txt, 0 if w.isupper() else re.I) for w in ws)}
        if len(found) == 1:
            return found.pop()
    return None


def years_named(txt: str) -> set:
    """Windows of years ("2022–2026", "2022–26") and single seasons in a header, as (first, last) pairs."""
    out = set()
    for a, b in re.findall(r"\b((?:19|20)\d\d)\s*[–-]\s*((?:19|20)?\d\d)\b", txt):
        out.add((int(a), int(b) if len(b) == 4 else int(a[:2] + b)))
    rest = re.sub(r"\b(?:19|20)\d\d\s*[–-]\s*(?:19|20)?\d\d\b", " ", txt)
    for y in re.findall(r"\b((?:19|20)\d\d)\b", rest):
        out.add((int(y), int(y)))
    return out


def years_in_path(path: str) -> set:
    out = set()
    for key, a, b in re.findall(r"(window|era|years|group_name|season|year)=(?:season )?((?:19|20)\d\d)(?:\s*[–-]\s*((?:19|20)?\d\d))?", path):
        out.add((int(a), int(b) if len(b or "") == 4 else int(a[:2] + b) if b else int(a)))
    return out


def level_named(txt: str) -> str | None:
    hits = {code for name, code in LEVEL_WORDS.items() if re.search(rf"(?<![\w/]){re.escape(name)}(?![\w])", txt)}
    hits = {h for h in hits if not (h == "GS" and "GSQ" in hits) and not (h == "CH" and "CHQ" in hits)}
    return hits.pop() if len(hits) == 1 else None


def levels_in_path(path: str) -> set:
    out = set()
    for code, qual in re.findall(r"(?:level|group_name|value)=(GS|FIN|T1000|T500|T250|GSQ|TQ|CHQ|CH|TEAM|ITF)\b(?:,qualifying=(True|False))?", path):
        out.add({"GS": "GSQ", "CH": "CHQ"}.get(code, "TQ") if qual == "True" else code)
    return out


def kind_of(item: dict, tok: dict, text: str) -> str:
    before, after = text[:tok["start"]], text[tok["end"]:]
    if item.get("svg") == "":
        return "axis"
    if item.get("code"):
        return "code"
    if re.search(r"(?:atp|wta)\|\S*$", before) or re.search(r"(?:atp|wta)(?:code)?:$", before):
        return "identifier"                            # a player or match id, e.g. atp|2026-600|R32|atp:200266
    if (not tok["comma"] and tok["decimals"] == 0 and not tok["percent"] and tok["abs"] in (125, 250, 500, 1000)
            and (re.search(r"(?:ATP|WTA|Masters|from|->|,|and)\s*(?:'s\s*)?$", before)
                 or re.match(r"\s*(?:qualifying|main draws?|matches|events?|level|from|,|and)\b", after))):
        return "level name"                            # 250 qualifying, the WTA's 1000, 500 and 250 main draws
    if not tok["comma"] and tok["decimals"] == 0 and not tok["percent"] and 1990 <= tok["abs"] <= 2035:
        return "year"
    if re.search(r"(?:19|20)\d\d\s*[–-]\s*$", before) and tok["decimals"] == 0 and tok["abs"] < 100:
        return "year"                                  # 2013–16
    if re.search(r"\b[Ss]tage\s*$", before) or re.search(r"\b[Ss]tages\s+(?:\d+(?:,\s*|\s+and\s+|–))*$", before):
        return "stage"
    if tok["abs"] == 95 and tok["decimals"] == 0 and re.match(r"\s*range", after):
        return "range level"                           # "95% range": the level of every range in the report
    if item.get("heading") and re.fullmatch(r"\s*", before) and after.startswith("."):
        return "heading"
    return "value"


def strip_tags(text: str) -> tuple[str, list]:
    """The text without the server-side tags, and where each tag stood in it."""
    out, marks, pos, n = [], [], 0, 0
    for m in MARK_RE.finditer(text):
        out.append(text[pos:m.start()])
        n += m.start() - pos
        marks.append((n, int(m.group(1))))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), marks


def numbers_in_page(h: dict) -> list[dict]:
    """Every number in the harvested texts and tooltips, once per distinct context, with its tag or link."""
    seen, rows = set(), []

    def add(section, where, state, item, raw_text, links, context):
        item = {k: strip_tags(v)[0] if isinstance(v, str) else v for k, v in item.items()}   # labels without tags
        text, marks = strip_tags(raw_text)
        link_pool = list(links)
        for m in NUM_RE.finditer(text):
            tok = parse(m)
            tag = [i for pos, i in marks if tok["start"] < pos <= tok["end"] + 1]
            link = None
            # only a number with a decimal point or a thousands separator is linked: a bare integer ("44 matches",
            # "per 100 played") is as often written without formatting, and would link to any earlier "44"
            if re.search(r"[.,]", tok["digits"]):
                for k, (s, v) in enumerate(link_pool):
                    if s.replace(",", "") == tok["digits"].replace(",", ""):
                        link = v
                        link_pool.pop(k)
                        break
            around = text[max(0, tok["start"] - 80): tok["end"] + 80]
            rows.append({**{k: tok[k] for k in ("token", "value", "abs", "signed", "decimals", "half", "percent")},
                         "section": section, "where": where, "state": state, "kind": kind_of(item, tok, text),
                         "tour": tour_hint(item, text[tok["end"]:]), "text": re.sub(r"\s+", " ", around).strip(),
                         "context": context, "tag": tag[0] if tag else None, "link": link,
                         "header": " | ".join(x for x in (item.get("group"), item.get("col"), item.get("row"),
                                                          item.get("tile")) if x)})

    for it in h["items"]:
        if it.get("option"):
            continue                                   # a menu's labels; the chosen row's numbers are in its chart
        key = (it["section"], it["text"], it["block"], it.get("col"), it.get("row"), it.get("group"), it.get("chart"),
               it.get("tile"), it.get("tileTour"), it.get("svg"), json.dumps(it.get("links")))
        if key in seen:
            continue
        seen.add(key)
        context = " | ".join(x for x in (it.get("sub"), it.get("tile"), it.get("chart"), it.get("table"), it.get("group"),
                                        it.get("col"), it.get("row"), strip_tags(it["block"])[0][:160]) if x)
        add(it["section"], "text" if it["svg"] is None else "chart", it["state"], it, it["text"], it.get("links") or [], context)
    for t in h["tips"]:
        for line, links in t["lines"]:
            key = (t["section"], line, t["chart"], json.dumps(links))
            if key in seen:
                continue
            seen.add(key)
            add(t["section"], "tooltip", t["state"], {"chart": t["chart"], "svg": None}, line, links,
                " | ".join(x for x in (t["chart"], " / ".join(strip_tags(l)[0] for l, _ in t["lines"])[:200]) if x))
    return rows


# ------------------------------------------------------------------------------------------------ the rules
_DOCS = {}


def J(name: str) -> dict:
    if name not in _DOCS:
        _DOCS[name] = json.loads((C.OUT / name).read_text(encoding="utf-8"))
    return _DOCS[name]


def _tml_rows(tour: str, unlinked: bool) -> int:
    return sum(v for r in J("stage0_summary.json")["merge"]["tml_rows_by_link"] if r["tour"] == tour
               for k, v in r.items() if k not in ("tour", "group", "period") and (unlinked or k != "unlinked"))


# Numbers a section module computes from several JSON values (a total across tours or over a list's records), for a
# number that carries no tag (its sum was taken over plain values). Each rule names the sentence, the printed number
# and the formula, written from the sentence's meaning.
DERIVED_RULES = [
    ("data-used", "461,670", "Jeff Sackmann's files are the base", "ATP matches from Sackmann, both periods",
     lambda: sum(r["matches"] for r in J("stage0_summary.json")["tables"]["sources"] if r["tour"] == "atp" and r["source"] == "sackmann")),
    ("data-used", "405,621", "Jeff Sackmann's files are the base", "WTA matches from Sackmann, both periods",
     lambda: sum(r["matches"] for r in J("stage0_summary.json")["tables"]["sources"] if r["tour"] == "wta" and r["source"] == "sackmann")),
    ("data-used", "196,332", "Jeff Sackmann's files are the base", "Tennis My Life rows, both tours, every link status",
     lambda: _tml_rows("atp", True) + _tml_rows("wta", True)),
    ("data-used", "190,877", "Jeff Sackmann's files are the base", "Tennis My Life rows linked to a Sackmann match, both tours",
     lambda: _tml_rows("atp", False) + _tml_rows("wta", False)),
    ("data-used", "16,221", "The last weeks are thin", "ITF matches in the same weeks of 2025, both tours",
     lambda: sum(r["matches"] for r in J("stage0_summary.json")["holes"]["qualifying_same_weeks_2025"]
                 if r["level"] == "ITF" and not r["qualifying"])),
    ("data-used", "17,590", "Under 90% of matches have one", "WTA box scores without service games, 2010-2014",
     lambda: sum(r["matches"] for r in J("stage0_summary.json")["holes"]["box_without_service_games"]
                 if r["tour"] == "wta" and 2010 <= r["year"] <= 2014)),
    ("data-used", "2,431", "Dates of TML-only matches", "links 32-366 days apart, both tours",
     lambda: sum(r["rows"] for r in J("stage0_summary.json")["merge"]["links_by_agreement"] if r["days"] == "32-366")),
    ("how-predictable", "9,647,948", "No look-ahead", "protected pre-match ratings checked by the probe, both tours and both retirement rules",
     lambda: sum(p["protected_matches_checked"] for p in J("stage1_baselines_summary.json")["probe_by_round"].values())),
    ("anatomy", "1,824,960", "point-by-point files record", "points kept, both tours",
     lambda: sum(J("stage2_pbp_results.json")["matches"][t]["points_kept"] for t in C.TOURS)),
    ("anatomy", "3,596", "Grand Slam deciding sets", "analysed matches under an advantage deciding set, both tours",
     lambda: sum(r["matches"] for r in J("stage2_results.json")["population"]["deciding_rules"] if r["rule"] == "ADV")),
    ("traits", "3,300,122", "The time rule", "protected pre-match values checked by the probe, both tours",
     lambda: sum(J("stage3_results.json")["ratings"]["probe_by_round"][t]["protected_matches_checked"] for t in C.TOURS)),
    ("traits", "185,839", "The time rule", "later values the probe changed, both tours",
     lambda: sum(J("stage3_results.json")["ratings"]["probe_by_round"][t]["later_matches_changed"] for t in C.TOURS)),
]

# Numbers that are part of a definition, a rule of the method or an illustration, not results: (section, number as
# printed, words around it, why).
CONSTANT_RULES = [
    ("data-used", "4.5", "fewer than 4.5 serve points per game", "the threshold of cleaning rule C39, part of its definition"),
    ("data-used", "250", "(Winston-Salem 2026): 250", "a level's name: the level rule L3 assigns"),
    ("how-predictable", "0.001", "a thousandth (0.001) is one", "the definition of a milli-log-loss"),
    ("how-predictable", "2.50", "odds of 2.50", "an illustration of decimal odds"),
]

# Numbers in the page's data block that set the drawing, not results.
DATA_CONSTANTS = [
    ("data-used", r"^data-used\.bins\[", "the colour key's bin edges (the last is 100.01, so that 100% falls inside it)"),
]


# ------------------------------------------------------------------------------------------------ the checks
def context_checks(r: dict, sources: list[tuple]) -> list[str]:
    """What the context says the number is, against its sources: (description, scale, tour) for each."""
    problems = []
    tours = {t for _, _, t in sources}
    if r["tour"] and None not in tours and r["tour"] not in tours:
        problems.append(f"the context names the {'men' if r['tour'] == 'atp' else 'women'}, the source is the other tour's")
    yrs = years_named(r["header"])
    path_years = set().union(*(years_in_path(d) for d, _, _ in sources)) if sources else set()
    if yrs and path_years and not (yrs & path_years):
        problems.append(f"the headers name {sorted(yrs)}, the source {sorted(path_years)}")
    lvl = level_named(r["header"])
    path_lvls = set().union(*(levels_in_path(d) for d, _, _ in sources)) if sources else set()
    if lvl and path_lvls and lvl not in path_lvls:
        problems.append(f"the headers name level {lvl}, the source {sorted(path_lvls)}")
    return problems


def check_number(r: dict) -> None:
    if r["kind"] != "value":
        r["status"] = r["kind"]
        return
    idx = section_index(r["section"])
    if r["tag"] is not None:                           # printed by a section module from tagged JSON values
        desc, leaves, value = PROV[r["tag"]]
        tours = {tour_of(leaf) for leaf in leaves} - {None}
        tour = tours.pop() if len(tours) == 1 else None    # computed from both tours' values: no single tour
        sources = [(leaf, 1.0, tour) for leaf in leaves] or [(desc, 1.0, None)]
        r["source"] = desc
        r["source_value"] = value
        ok = abs(abs(value) - r["abs"]) <= r["half"] * (1 + 1e-9) + 1e-12
        problems = ([] if ok else [f"printed {r['token']}, the tagged value is {value:g}"]) + context_checks(r, sources)
        if not leaves:
            problems.append("computed from no JSON value")
        r["status"] = "tagged" if not problems else "tagged: " + "; ".join(problems)
        return
    if r["link"] is not None and not float(r["link"]).is_integer():   # printed by the page's scripts from this value
        # (an integer is not linked: the scripts print counts and rounded values through Math.round, and the latest
        # formatting that printed "44" can be any 44; integers are judged by value below)
        v = float(r["link"])
        sources = idx.exact(v, signed=False)
        if sources:
            r["source"] = sources[0][0] + ("" if sources[0][1] == 1 else f" × {sources[0][1]:g}")
            r["source_value"] = v
            ok = abs(abs(v) - r["abs"]) <= r["half"] * (1 + 1e-9) + 1e-12
            fit = [s for s in sources if not r["tour"] or s[2] in (r["tour"], None)]
            problems = ([] if ok else [f"printed {r['token']}, the formatted value is {v:g}"]) + context_checks(r, fit or sources)
            r["status"] = "linked" if not problems else "linked: " + "; ".join(problems)
            return
        # the script formatted a value it computed or rounded first (Math.round for a count): judge by value
    trace_by_value(r, idx)


def trace_by_value(r: dict, idx: Index) -> None:
    """A number with no tag or link: some JSON value of its section must print as it (the weak check)."""
    hits = [(i, s) for s in ((100.0, 1.0) if r["percent"] else SCALES) for i in idx.find(r["abs"], r["half"], s)]
    same = [(i, s) for i, s in hits if (idx.signed[i] < 0) == (r["value"] < 0) or idx.signed[i] == 0]
    pool = same if r["signed"] else hits
    if r["tour"]:
        pool = [(i, s) for i, s in pool if idx.tours[i] in (r["tour"], None)]
    for sec, token, phrase, what, f in DERIVED_RULES:
        if r["section"] == sec and r["token"] == token and phrase in (r["text"] + " " + r["context"]):
            v = float(f())
            ok = abs(abs(v) - r["abs"]) <= r["half"] + 1e-9
            r.update({"status": "derived (rule)" if ok else "derived (rule): it does not match", "source": what,
                      "source_value": v})
            return
    for sec, token, phrase, why in CONSTANT_RULES:
        if r["section"] == sec and r["token"] == token and phrase in (r["text"] + " " + r["context"]):
            r.update({"status": "constant", "source": why})
            return
    if pool:
        i, s = pool[0]
        r.update({"status": "value only", "source": idx.paths[i] + ("" if s == 1 else f" × {s:g}"),
                  "source_value": float(idx.signed[i])})
    else:
        r["status"] = "untraced"


def check_data(h: dict) -> list[dict]:
    """Every number in the data block must equal a JSON value of its section (or two combined) at full precision."""
    rows = []
    for section, data in (h["report_data"] or {}).items():
        leaves = []
        flatten(data, section, leaves)
        idx = section_index(section)
        for v, path in leaves:
            r = {"section": section, "where": "data", "value": v, "abs": abs(v), "path_in_page": path}
            why = next((w for sec, pat, w in DATA_CONSTANTS if section == sec and re.search(pat, path)), None)
            if v == 0:
                r["status"] = "zero"
            elif why:
                r.update({"status": "constant", "source": why})
            elif float(v).is_integer() and 1990 <= v <= 2035 and (re.search(r"\.pts\[\d+\]\[0\]$|year|season", path)):
                r["status"] = "year"
            else:
                src = idx.exact(v)
                if src:
                    tours = {t for _, _, t in src}
                    t_page = tour_of(path)
                    bad = t_page and None not in tours and t_page not in tours
                    r.update({"status": "exact: other tour" if bad else "exact", "source": src[0][0], "candidates": len(src)})
                else:
                    r["status"] = "untraced"
            rows.append(r)
    return rows


# ------------------------------------------------------------------------------------------------ the page itself
def typed_in_templates() -> dict:
    """Numbers typed into the section modules' prose (outside their f-string expressions), for the record: each is a
    definition, a rule of the method or an illustration, never a result."""
    out = {}
    for f in sorted(HERE.glob("report_*.py")):
        src = re.split(r'\nJS = r"""', f.read_text(encoding="utf-8"))[0]
        found = Counter()
        for groups in re.findall(r"f?'''(.*?)'''|f?\"\"\"(.*?)\"\"\"|f'([^'\n]*<[^'\n]*)'|f\"([^\"\n]*<[^\"\n]*)\"", src, flags=re.S):
            s = next(g for g in groups if g)
            s = re.sub(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", " ", s)
            s = re.sub(r"<[^>]*>|&[a-z]+;|&#\d+;", " ", s)
            for m in NUM_RE.finditer(s):
                tok = m.group(0).strip()
                if not re.fullmatch(r"(?:19|20)\d\d", tok):
                    found[tok] += 1
        out[f.name] = dict(sorted(found.items(), key=lambda kv: (-kv[1], kv[0])))
    return out


def value_only_power(rows: list[dict]) -> dict:
    """How often the weak check would notice a wrong number: each value-only number moved by one unit in its last
    printed digit, up and down, and traced again."""
    caught = []
    for r in rows:
        if r.get("status") != "value only":
            continue
        idx = section_index(r["section"])
        res = []
        for d in (1, -1):
            a = r["abs"] + d * 2 * r["half"]
            if a <= 0:
                continue
            m = dict(r, abs=a, value=-a if r["value"] < 0 else a, status=None)
            trace_by_value(m, idx)
            res.append(m["status"] == "untraced")
        if res:
            caught.append(sum(res) / len(res))
    return {"numbers": len(caught), "share_of_one_digit_errors_caught": round(float(np.mean(caught)), 3) if caught else None}


def sanity(rows: list[dict]) -> list[dict]:
    """Numbers that look wrong in themselves, whatever their source: a value outside its own 95% range, "N of M" with
    N above M, a share above 100%."""
    found, seen = [], set()
    num = r"(−?\d[\d,]*(?:\.\d+)?)"
    for r in rows:
        t = r["text"]
        if (r["section"], t) in seen:
            continue
        seen.add((r["section"], t))
        f = lambda s: float(s.replace(",", "").replace("−", "-"))
        for m in re.finditer(num + r"%?\s*(?:milli-log-loss\s*)?\((?:men|women)?[;,]?\s*(?:95% range\s*)?" + num + r"\s*(?:to|–)\s*" + num + r"\)", t):
            v, lo, hi = (f(x) for x in m.groups())
            if all(float(x).is_integer() and 1990 <= x <= 2035 for x in (lo, hi)):
                continue                               # "(2019–2026)": years, not a range
            if not lo - 0.011 <= v <= hi + 0.011:
                found.append({"section": r["section"], "check": "value outside its 95% range", "text": t})
        for m in re.finditer(r"(?<![\d.,])" + num + r" of " + num + r"(?![\d.,%])", t):
            a, b = (f(x) for x in m.groups())
            if a > b and not re.search(r"of the|of a|of its", t[m.end() - len(m.group(2)) - 4: m.end()]):
                found.append({"section": r["section"], "check": "N of M with N above M", "text": t})
        if r.get("percent") and r["abs"] > 100.05 and r.get("kind") == "value":
            found.append({"section": r["section"], "check": "a share above 100%", "text": t})
    return found


def page_text(h: dict) -> Counter:
    return Counter((it["section"], strip_tags(it["text"])[0]) for it in h["items"] if it["state"] == "default")


def self_test() -> int:
    """Each planted error must make the check flag numbers; the unplanted page must flag none."""
    out = []
    for plant in [None] + PLANTS:
        with tempfile.TemporaryDirectory() as tmp:
            html_path = Path(tmp) / "report_tagged.html"
            render_tagged(html_path, plant)
            h = harvest_page(html_path)
        rows = numbers_in_page(h)
        for r in rows:
            check_number(r)
        flagged = [r for r in rows if r["status"].startswith(("tagged:", "linked:"))]
        in_data = [d for d in check_data(h) if d["status"] not in ("exact", "zero", "year", "constant")]
        out.append({"plant": plant["name"] if plant else "none (the page as built)", "flagged": len(flagged),
                    "flagged_in_data": len(in_data),
                    "caught": bool(flagged) if plant else not (flagged or in_data),
                    "examples": [{k: r[k] for k in ("section", "where", "token", "status", "header", "text")} for r in flagged[:4]],
                    "data_examples": [{k: d.get(k) for k in ("section", "path_in_page", "value", "status", "source")} for d in in_data[:4]]})
        print(f'{out[-1]["plant"]}: {len(flagged)} numbers flagged on the page, {len(in_data)} in the data block')
    (C.OUT / "summary_number_check_selftest.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    return 0 if all(x["caught"] for x in out) else 1


def main() -> int:
    t0 = datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory() as tmp:
        tagged_html = Path(tmp) / "report_tagged.html"
        render_tagged(tagged_html)
        h = harvest_page(tagged_html)
    real = harvest_page(REPORT)
    # the tagged page must read as the real page once its tags are removed
    a, b = page_text(h), page_text(real)
    only_tagged, only_real = a - b, b - a

    rows = numbers_in_page(h)
    for r in rows:
        check_number(r)
    data = check_data(h)
    text_df, data_df = pd.DataFrame(rows), pd.DataFrame(data)

    ok_status = {"tagged", "linked", "derived (rule)", "constant", "value only", "axis", "year", "stage", "heading", "range level",
                 "level name", "identifier", "code"}
    problems = text_df[~text_df["status"].isin(ok_status)]
    data_problems = data_df[~data_df["status"].isin({"exact", "zero", "year", "constant"})]
    values = text_df[text_df["kind"] == "value"]
    cols = ["section", "where", "state", "kind", "token", "status", "tour", "header", "source", "source_value", "text", "context"]
    out = text_df.reindex(columns=cols)
    out.to_csv(OUT_CSV, index=False)
    res = {
        "generated_at": t0.isoformat(timespec="seconds"),
        "report": str(REPORT.relative_to(C.ROOT)).replace("\\", "/"),
        "control_states": len(h["states"]), "page_errors": h["page_errors"] + real["page_errors"],
        "text_items": len(h["items"]), "tooltips_read": len(h["tips"]),
        "numbers": int(len(text_df)), "values": int(len(values)),
        "by_status": text_df["status"].value_counts().to_dict(),
        "values_by_status": values["status"].value_counts().to_dict(),
        "values_by_section_and_status": {f"{s}|{k}": int(v) for (s, k), v in values.groupby(["section", "status"]).size().items()},
        "data_block": {"numbers": int(len(data_df)), "by_status": data_df["status"].value_counts().to_dict()},
        "problems": problems.reindex(columns=cols).to_dict("records"),
        "data_problems": data_problems.to_dict("records"),
        "value_only_power": value_only_power(rows),
        "sanity": sanity(rows),
        "tagged_page_differs_from_real": {"only_in_tagged": [list(k) + [v] for k, v in only_tagged.items()],
                                          "only_in_real": [list(k) + [v] for k, v in only_real.items()]},
        "rules": {"derived": [{"section": s, "number": t, "sentence": p, "what": w} for s, t, p, w, _ in DERIVED_RULES],
                  "constant": [{"section": s, "number": t, "words": p, "why": w} for s, t, p, w in CONSTANT_RULES],
                  "data_constant": [{"section": s, "path": p, "why": w} for s, p, w in DATA_CONSTANTS]},
        "typed_in_templates": typed_in_templates(),
        "seconds": round((datetime.now(timezone.utc) - t0).total_seconds(), 1),
    }
    OUT_JSON.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(f"{len(text_df):,} numbers in {len(h['states'])} control states and {len(h['tips']):,} tooltip readings; "
          f"{len(values):,} values: " + ", ".join(f"{k} {v:,}" for k, v in res["values_by_status"].items()))
    print(f"data block: {len(data_df):,} numbers: " + ", ".join(f"{k} {v:,}" for k, v in res["data_block"]["by_status"].items()))
    print(f"problems: {len(problems)} in text, {len(data_problems)} in the data block; tagged page differs from the real "
          f"page in {sum(only_tagged.values())} and {sum(only_real.values())} text items; page errors: {res['page_errors']}")
    return 0 if problems.empty and data_problems.empty else 1


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
