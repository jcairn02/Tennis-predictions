"""Compose data/studies/feature_universe/universe.csv from the spec_*.py rows (one row per conceptual feature), fill the
coverage columns from build/coverage_keys.csv (run coverage.py first) and validate every store column against the
coordinator's store_registry.csv (read only). Writes universe.csv and build/validation.json. Reads no result.

It also writes menu.csv, the selection pool: one row per store column on the registry's menu (a distinct,
non-degenerate column; build_store.py's hygiene), with the catalogue rows that reference it or any of its copies. A copy
(registry `canonical`, or `near_dup_of` at |r| >= 0.999) stands for its representative. Per menu column:
    feature_id      its defining row: the most specific one (explicit name over a pattern, then fewest columns, then the
                    lowest id); name, family, status, timing_class, near_miss_tier and priority are that row's
    feature_ids     every row that references it or a copy
    seen_2025_2026  yes if any of them was related to 2025-2026 results (conservative)
    priority        the defining row's suggestion; "exclude" whenever any referencing row is leaking
    aliases         its copies in the store
Run: ./python.sh src/eda/feature_universe/catalogue/build_universe.py
"""
from __future__ import annotations

import fnmatch
import importlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "data" / "studies" / "feature_universe"
BUILD = OUT / "build"
sys.path.insert(0, str(HERE))
SPECS = ["spec_market", "spec_ratings", "spec_profiles", "spec_form", "spec_load", "spec_background", "spec_context",
         "spec_shot", "spec_levels", "spec_fi_a", "spec_fi_b",
         "spec_event_levels"]       # added 8 Oct 2026, last so that the earlier rows keep their ids
STATUS = {"IM": "in_model", "BN": "built_not_in_model", "BD": "buildable_from_disk", "NN": "needs_new_data",
          "XL": "excluded_leaky", "MI": "market_internal"}
TIMING = {"SC": "safe by construction", "PP": "leak-proof clock + probe passed",
          "PN": "leak-proof clock, probe needed", "LK": "leaking"}
COLS = ["feature_id", "name", "family", "subfamily", "definition", "kind", "source", "store_columns", "menu_columns",
        "status", "timing_class", "coverage_2013_2021", "coverage_2022_2024", "coverage_2025_2026", "evidence",
        "near_miss_tier", "seen_2025_2026", "caveats", "priority_suggestion"]
TIERS = ["A", "B", "C", "D", "none"]
PRIORITIES = ["high", "medium", "low", "exclude"]


def representative(reg: pd.DataFrame) -> dict[str, str]:
    """Each store column's menu representative: its canonical copy, then that copy's near-duplicate representative."""
    can = dict(zip(reg["column"], reg["canonical"].fillna("")))
    near = dict(zip(reg["column"], reg["near_dup_of"].fillna("")))
    rep = {}
    for c in reg["column"]:
        r = can[c] or c
        rep[c] = near.get(r, "") or r
    return rep


def menu_table(u: pd.DataFrame, reg: pd.DataFrame, rep: dict[str, str], registry: set[str]) -> pd.DataFrame:
    """One row per menu column (see the module docstring)."""
    menu = reg[reg["menu"] == 1].set_index("column")
    refs: dict[str, list[tuple]] = {c: [] for c in menu.index}
    for _, row in u.iterrows():
        cols, _ = expand(row["store_columns"], registry)
        pattern = "*" in row["store_columns"]
        for c in dict.fromkeys(rep[c] for c in cols):
            if c in refs:
                refs[c].append((pattern, len(cols), row["feature_id"], row))
    aliases: dict[str, list[str]] = {c: [] for c in menu.index}
    for c, r in rep.items():
        if r != c and r in aliases:
            aliases[r].append(c)
    out = []
    for c, rows in refs.items():
        m = menu.loc[c]
        rec = {"column": c, "group": m["group"], "kind": m["kind"], "partner": m["partner"] or "", "hid": m["hid"] or "",
               "store_flag": m["flag"] or ""}
        if rows:
            best = sorted(rows, key=lambda t: (t[0], t[1], t[2]))[0][3]
            leaky = any(t[3]["status"] == "excluded_leaky" for t in rows)
            rec |= {"feature_id": best["feature_id"], "name": best["name"], "family": best["family"],
                    "status": best["status"], "timing_class": best["timing_class"],
                    "feature_ids": "; ".join(sorted({t[2] for t in rows})),
                    "near_miss_tier": best["near_miss_tier"],
                    "seen_2025_2026": "yes" if any(t[3]["seen_2025_2026"] == "yes" for t in rows) else "no",
                    "priority": "exclude" if leaky else str(best["priority_suggestion"]).split(":")[0]}
        rec["aliases"] = "; ".join(aliases[c])
        rec |= {k: m[k] for k in m.index if k.startswith("cov_")}
        out.append(rec)
    return pd.DataFrame(out)


def fmt(cov: pd.DataFrame, key: str) -> list[str]:
    if key.startswith("="):
        parts = [p.strip() for p in key[1:].split("|")]
        if len(parts) != 3:
            raise ValueError(f"literal coverage needs three parts: {key}")
        return parts
    r = cov.loc[key]
    out = []
    for p in ("p1", "p2", "p3"):
        a, w = r[f"cov_atp_{p}"], r[f"cov_wta_{p}"]
        na, nw = r[f"n_atp_{p}"], r[f"n_wta_{p}"]
        if not (np.isfinite(a) and np.isfinite(w)):
            out.append("n/a")
        elif abs(a - w) <= 0.02:
            out.append(f"{(a * na + w * nw) / (na + nw):.2f}")
        else:
            out.append(f"M {a:.2f} / W {w:.2f}")
    return out


def reason(pri: str, family: str, tier: str, ev: str, seen: str) -> str:
    """A one-line default reason for a bare priority (the spec rows give one where it is specific)."""
    if ":" in pri:
        return pri
    if tier == "B":
        why = "tier B near miss (2 <= |z| < 2.5); test it alone"
    elif tier == "C":
        why = "tier C near miss (1 <= |z| < 2)"
    elif tier == "D":
        why = "tier D near miss (strong in one window only)"
    elif family == "feature-interactions study":
        why = "its screen tied (|z| < 1 or Wald p > 0.2, 2014-24)"
    elif any(k in ev for k in ("never tested", "not tested", "no test found", "not screened", "never built")):
        why = "untested; no earlier result favours it"
    elif "inside" in ev or "member" in ev:
        why = "raw part of a screened block that tied (2014-24)"
    elif seen == "yes":
        why = "tied or small given the price in earlier studies"
    else:
        why = "a control or building block without evidence of its own"
    return f"{pri}: {why}"


def expand(store: str, registry: set[str]) -> tuple[list[str], list[str]]:
    cols, bad = [], []
    for tok in [t.strip() for t in store.split(";") if t.strip()]:
        tok = tok.split(" (")[0].strip()
        names = [tok[:-5] + "_a", tok[:-5] + "_b"] if tok.endswith("_a/_b") else [tok]
        for n in names:
            hit = sorted(fnmatch.filter(registry, n)) if "*" in n else ([n] if n in registry else [])
            (cols.extend(hit) if hit else bad.append(n))
    return cols, bad


def main() -> int:
    reg = pd.read_csv(OUT / "store_registry.csv", keep_default_na=False)
    reg["menu"] = pd.to_numeric(reg["menu"])
    for c in [c for c in reg.columns if c.startswith("cov_")]:
        reg[c] = pd.to_numeric(reg[c], errors="coerce")
    registry = set(reg["column"])
    flags = dict(zip(reg["column"], reg["flag"]))
    rep = representative(reg)
    on_menu = dict(zip(reg["column"], reg["menu"] == 1))
    cov = pd.read_csv(BUILD / "coverage_keys.csv").set_index("key")
    rows, problems, used = [], {"bad_store": {}, "bad_cov": [], "bad_rows": []}, Counter()
    for mod in SPECS:
        m = importlib.import_module(mod)
        for t in m.ROWS:
            if len(t) != 14:
                problems["bad_rows"].append(f"{mod}: {t[0]} has {len(t)} fields")
                continue
            name, sub, defn, kind, src, store, st, tm, key, ev, tier, seen, cav, pri = t
            try:
                c1, c2, c3 = fmt(cov, key)
            except KeyError:
                problems["bad_cov"].append(f"{name}: {key}")
                c1 = c2 = c3 = "n/a"
            cols, bad = expand(store, registry)
            if bad:
                problems["bad_store"][name] = bad
            if any("base-dependent" in str(flags.get(c, "")) for c in cols):
                cav = "; ".join(x for x in (cav, "store flag: base-dependent (reads the current best's 2014-24 "
                                            "forecast; recompute with the new model's own)") if x)
            used.update(set(cols)) if "*" in store else used.update(cols)
            menu_cols = "; ".join(dict.fromkeys(rep[c] for c in cols if on_menu.get(rep[c], False)))
            rows.append({"name": name, "family": m.FAMILY, "subfamily": sub, "definition": defn, "kind": kind,
                         "source": src, "store_columns": store, "menu_columns": menu_cols, "status": STATUS[st],
                         "timing_class": TIMING[tm],
                         "coverage_2013_2021": c1, "coverage_2022_2024": c2, "coverage_2025_2026": c3, "evidence": ev,
                         "near_miss_tier": tier, "seen_2025_2026": seen, "caveats": cav,
                         "priority_suggestion": reason(pri, m.FAMILY, tier, ev, seen)})
    u = pd.DataFrame(rows)
    u.insert(0, "feature_id", [f"U-{i:03d}" for i in range(1, len(u) + 1)])
    u = u[COLS]
    u.to_csv(OUT / "universe.csv", index=False)
    explicit = Counter()
    for s in u["store_columns"]:
        if "*" not in s:
            explicit.update(expand(s, registry)[0])
    reps_used = {rep[c] for c in used}
    menu_set = {c for c, ok in on_menu.items() if ok}
    mt = menu_table(u, reg, rep, registry)
    mt.to_csv(OUT / "menu.csv", index=False)
    val = {
        "rows": len(u),
        "by_family": u["family"].value_counts().to_dict(),
        "by_status": u["status"].value_counts().to_dict(),
        "family_x_status": {f: g["status"].value_counts().to_dict() for f, g in u.groupby("family")},
        "priority": u["priority_suggestion"].str.split(":").str[0].value_counts().to_dict(),
        "tier": u["near_miss_tier"].value_counts().to_dict(),
        "in_model_inputs_covered": sorted(c for c in registry if c.startswith("m__") and c in used),
        "store_columns_referenced": len(set(used)), "store_columns_total": len(registry),
        "store_columns_unreferenced": sorted(c for c in registry if c not in used and rep[c] not in reps_used),
        "menu_columns": len(menu_set), "menu_by_group": reg.loc[reg["menu"] == 1, "group"].value_counts().to_dict(),
        "menu_unreferenced": sorted(menu_set - reps_used),
        "menu_by_priority": mt["priority"].value_counts().to_dict() if "priority" in mt else {},
        "menu_by_tier": mt["near_miss_tier"].value_counts().to_dict() if "near_miss_tier" in mt else {},
        "menu_seen_2025_2026": mt["seen_2025_2026"].value_counts().to_dict() if "seen_2025_2026" in mt else {},
        "store_columns_in_two_rows": sorted(c for c, n in explicit.items() if n > 1),
        "rows_without_store": int((u["store_columns"] == "").sum()),
        **problems,
    }
    val["in_model_inputs_covered"] = len(val["in_model_inputs_covered"])
    (BUILD / "validation.json").write_text(json.dumps(val, indent=1))
    print(json.dumps({k: v for k, v in val.items() if k not in ("family_x_status",)}, indent=1)[:3000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
