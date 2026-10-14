"""Deterministic data corrections used before the dated-history rebuild.

Stable original match IDs and A/B orientation are retained for provenance joins.
Identity repair is limited to unambiguous exact-name source aliases; conflicts
are reported and left unresolved. No match outcome is used to resolve a person.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import numpy as np
import pandas as pd


@lru_cache(maxsize=None)
def name_key(value):
    if pd.isna(value):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def plain_match_tiebreak(score, level, status="completed", short=False, event_rule=False):
    """Bracket a certain deciding match tiebreak; preserve possible advantage sets.

    An unbracketed 10-4 cannot be an ordinary completed set. A 10-8 or 12-10
    can be an advantage set, including in older ITF events: without independent
    rule evidence it is never rewritten. ``event_rule`` is such evidence: the
    event plays a match tiebreak instead of its deciding set (stage0_build.
    match_tiebreak_events, from its other deciders), so its 10-8 or 13-11 is
    one too (the owner's go-ahead of 13 Oct 2026). Retirements and incomplete
    scores are left unchanged. ``level`` is retained for call compatibility,
    not inference. This function describes an observed historical score, never
    forecast format.
    """
    s = str(score)
    if short or status != "completed":
        return s
    tokens = s.split()
    if len(tokens) != 3:
        return s
    parsed = [re.fullmatch(r"(\d+)-(\d+)(?:\(\d+\))?", t) for t in tokens]
    if not all(parsed):
        return s
    points = [(int(m[1]), int(m[2])) for m in parsed]
    first = points[:2]
    if not all((max(a, b) == 6 and min(a, b) <= 4) or (max(a, b), min(a, b)) in ((7, 5), (7, 6)) for a, b in first):
        return s
    if (first[0][0] > first[0][1]) == (first[1][0] > first[1][1]):
        return s
    a, b = points[-1]
    hi, lo = max(a, b), min(a, b)
    if hi < 10 or hi - lo < 2 or (hi > 10 and hi - lo != 2):
        return s
    if hi - lo == 2 and not event_rule:
        return s
    tokens[-1] = f"[{a}-{b}]"
    return " ".join(tokens)


def repair_tables(matches, players):
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic.stage0_build import column_items, score_counts
    m, p = matches.copy().reset_index(drop=True), players.copy().reset_index(drop=True)
    if m.match_id.duplicated().any() or p.duplicated(["match_id", "side"]).any():
        raise ValueError("Repair inputs require unique matches and player sides")
    # Each match's set of sides, as groupby(...).agg(set) gave it (a missing match id left out), in one loop over plain
    # arrays: the group-by built a group for each of ~873,000 matches (11 Oct 2026, for speed; the same sets).
    sides = {}
    for mid, side in zip(column_items(p.match_id), column_items(p.side)):
        if not pd.isna(mid):
            sides.setdefault(mid, set()).add(side)
    if set(sides) != set(m.match_id) or not all(s == {"A", "B"} for s in sides.values()):
        raise ValueError("Repair inputs require exactly A and B for every match")
    original_ids = p.player_id.copy()
    attr = m.set_index("match_id")[["tour", "source", "tournament_date"]]
    q = p[["match_id", "player_id", "player_name", "country", "age"]].join(attr, on="match_id")
    q["name_key"] = q.player_name.map(name_key)
    q["country"] = q.country.astype("string").str.upper().str.strip().replace({"": pd.NA})
    q["birth_year_approx"] = pd.to_datetime(q.tournament_date).dt.year - pd.to_numeric(q.age, errors="coerce")
    trusted = q[q.source.eq("sackmann") & q.name_key.ne("")]
    groups = trusted.groupby(["tour", "name_key"], sort=False)
    years = groups.birth_year_approx.median()
    # Per (tour, name) as the group-by's Python functions gave them (a missing key left out): the sorted tuple of the
    # player ids and the set of known countries, in one loop over plain arrays (11 Oct 2026, for speed; read only
    # through .get below, so a dict serves as the Series did).
    id_sets, countries = {}, {}
    for tour, key, pid, country in zip(*(column_items(trusted[c]) for c in ("tour", "name_key", "player_id", "country"))):
        if pd.isna(tour) or pd.isna(key):
            continue
        id_sets.setdefault((tour, key), set()).add(pid)
        known = countries.setdefault((tour, key), set())
        if not pd.isna(country):
            known.add(str(country))
    ids = {k: tuple(sorted(v)) for k, v in id_sets.items()}
    aliases, conflicts, proposed = [], [], []
    for (tour, pid, key), rows in q[q.source.ne("sackmann")].groupby(["tour", "player_id", "name_key"], sort=False):
        names = ids.get((tour, key), ())
        if len(names) != 1 or names[0] == pid or not key:
            if len(names) > 1:
                conflicts.append({"tour": tour, "source_id": pid, "name": key,
                                  "reason": "multiple canonical players share exact name", "rows": len(rows)})
            continue
        target = names[0]
        year0 = years.get((tour, key), np.nan)
        observed_countries = set(rows.country.dropna().astype(str))
        known_countries = countries.get((tour, key), set())
        observed_years = rows.birth_year_approx.dropna()
        bad_age = np.isfinite(year0) and observed_years.sub(year0).abs().gt(1.5).any()
        bad_country = bool(observed_countries and known_countries and not observed_countries.intersection(known_countries))
        if bad_age or bad_country:
            conflicts.append({"tour": tour, "source_id": pid, "name": key, "candidate": target,
                              "reason": "demographic conflict", "rows": len(rows)})
            continue
        p.loc[rows.index, "player_id"] = target
        aliases.append({"tour": tour, "source_id": pid, "canonical_id": target, "name": key, "rows": len(rows)})
        proposed.append(rows.index)
    # Re-derive other-side ids from the actual paired row, never from a global id
    # replacement that could alter a different person sharing a bad source code.
    pairs = p.pivot(index="match_id", columns="side", values="player_id")
    same = pairs.A.eq(pairs.B)
    if same.any():
        bad = set(pairs.index[same])
        p.loc[p.match_id.isin(bad), "player_id"] = original_ids[p.match_id.isin(bad)]
        conflicts += [{"match_id": mid, "reason": "would collapse opponents; reverted"} for mid in sorted(bad)]
        pairs = p.pivot(index="match_id", columns="side", values="player_id")
    # A proposal rejected by the opposing-player guard is not counted as a
    # successful alias. Report actual changed rows only.
    for alias, idx in zip(aliases, proposed):
        alias["rows"] = int(p.loc[idx, "player_id"].eq(alias["canonical_id"]).sum())
    aliases = [a for a in aliases if a["rows"]]
    p["opponent_id"] = np.where(p.side.eq("A"), p.match_id.map(pairs.B), p.match_id.map(pairs.A))
    m["player_a_id"], m["player_b_id"] = m.match_id.map(pairs.A), m.match_id.map(pairs.B)
    # Correct historical score aggregates only where notation is unambiguous. (The four columns read as plain arrays
    # rather than through itertuples, which read every column of every row: 11 Oct 2026, for speed; the same values.)
    repaired_score = [plain_match_tiebreak(score, level, status, fmt == "short_sets") for score, level, status, fmt in
                      zip(*(column_items(m[c]) for c in ("score", "level", "status", "format")))]
    changed = np.asarray(repaired_score) != m.score.astype(str).to_numpy()
    counts = {}
    for idx in np.flatnonzero(changed):
        row = m.iloc[idx]
        sw, sl, gw, gl, tw, tl, *_ = score_counts(repaired_score[idx], False)
        reversed_score = getattr(row, "score_flag", "") == "read_reversed"
        if reversed_score:
            sw, sl, gw, gl, tw, tl = sl, sw, gl, gw, tl, tw
        counts[row.match_id] = (sw, sl, gw, gl, tw, tl)
    if counts:
        corrected = pd.DataFrame.from_dict(counts, orient="index", columns=["sw", "sl", "gw", "gl", "tw", "tl"])
        use = p.match_id.isin(corrected.index)
        mapped = corrected.reindex(p.loc[use, "match_id"])
        for name, cw, cl in (("sets_won", "sw", "sl"), ("games_won", "gw", "gl"), ("tb_won", "tw", "tl")):
            w, l = mapped[cw].to_numpy(), mapped[cl].to_numpy()
            p.loc[use, name + "_n"] = np.where(p.loc[use, "won"], w, l)
            p.loc[use, name + "_d"] = w + l
    m.loc[changed, "format"] = "match_tiebreak"
    m.loc[changed, "nonstandard_format"] = True
    # A negative primitive can yield an apparently valid derived statistic:
    # bp_saved=-1, bp_faced=1, service_games=10 gives hold=8/10. Drop the whole
    # paired box, including every derived mirror; preserving one side would
    # leave different histories for the same invalid observation.
    raw_box = [c for c in C.BOX if c in p]
    bad_box = p[raw_box].lt(0).any(axis=1)
    bad_box_matches = set(p.loc[bad_box, "match_id"])
    box_rows = p.match_id.isin(bad_box_matches)
    score_rates = {"tb_won", "sets_won", "games_won"}
    box_rate_cols = [f"{s}_{v}" for s in C.RATES if s not in score_rates for v in ("n", "d") if f"{s}_{v}" in p]
    p.loc[box_rows, raw_box + box_rate_cols] = np.nan
    if "has_box" in p:
        p.loc[box_rows, "has_box"] = False
    m.loc[m.match_id.isin(bad_box_matches), "has_box"] = False
    if "box_status" in m:
        m.loc[m.match_id.isin(bad_box_matches), "box_status"] = "failed_check"
    invalid = {}
    for col in [x for x in p.columns if x.endswith("_n")]:
        stat = col[:-2]
        den = stat + "_d"
        if den not in p:
            continue
        n, d = p[col], p[den]
        bad = ((n.notna() & ((n < 0) | ~np.isfinite(n)))
               | (d.notna() & ((d < 0) | ~np.isfinite(d)))
               | (n.notna() & d.notna() & (n > d) if stat != "bp_faced_pg" else False))
        invalid[stat] = int(bad.sum())
        p.loc[bad, [col, den]] = np.nan
    point_count = p.groupby("match_id", sort=False).svpt.sum(min_count=2)
    pts = m.match_id.map(point_count)
    sec = 60 * m.minutes / pts.where(pts > 0)
    bad_minutes = (m.minutes.notna() & ((m.minutes <= 0) | (pts.notna() & ((sec < 15) | (sec > 120)))))
    m.loc[bad_minutes, "minutes"] = np.nan
    meta = {"identity_aliases": aliases, "identity_conflicts_left_unresolved": conflicts,
            "identity_player_rows_changed": int(original_ids.ne(p.player_id).sum()),
            "historical_plain_match_tiebreaks_corrected": int(changed.sum()),
            "negative_primitive_box_matches_masked": len(bad_box_matches),
            "invalid_rate_rows_masked": invalid, "implausible_minutes_masked": int(bad_minutes.sum()),
            "match_id_and_side_orientation": "Original stable handles retained; canonical player IDs corrected separately.",
            "box_scores_previously_discarded": "Not reconstructed from missing derived values; the corrected raw Stage 0 builder handles subsequent source rebuilds."}
    return m, p, meta
