"""R3 scratch: simulate the proposed date fixes on an in-memory copy of Stage 0 and recompute the timeline windows of the
affected rows with timing.py's own functions. Read-only: writes only into this folder (sim_*.csv).

Checks (the brief's):
  (ii)  the class/rule window of each re-dated match (timing.py rules, anchored on the new date, draw-narrowed within
        the event) holds the match's play day;
  (i)   no player then has two matches on overlapping days (hard conflicts: another dated match of his inside his
        span at the re-dated event; listed softer overlaps: other windows touching his play days);
  (iii) in Stage 0's chronological order (tournament_date, round_order, match_num, tournament_id, match_id) each
        re-dated match then follows the players' matches of the preceding weeks and precedes the later ones.
The window code is validated first: on the CURRENT dates it must reproduce timing.parquet's es/lf for these rows.
"""
from __future__ import annotations

import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import timing as T  # noqa: E402  (pure functions only; build() is never called)
from src.eda.predictability_diagnostic import common as C  # noqa: E402

S0 = ROOT / "data/studies/predictability_diagnostic/stage0_matches.parquet"
MP = ROOT / "data/studies/predictability_diagnostic/stage0_match_players.parquet"
TM = ROOT / "data/studies/match_timing/timing.parquet"
CLS = ROOT / "data/studies/match_timing/timing_classes.csv"
TL = ROOT / "data/dump/points/tennislive/listed.parquet"
SE = ROOT / "data/dump/points/sofascore_editions/events.parquet"

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_colwidth", 48)

G1_TID, G1_NEW = "2024-2847", "2024-02-26"
G2_IDS = ["atp|2021-580|Q2|atp:106045|atp:208013", "atp|2021-580|Q2|atp:106408|atp:202103"]
G2_NEW = "2021-01-10"


def day(x) -> int:
    return int((pd.Timestamp(x) - pd.Timestamp("1970-01-01")).days)


def dstr(d) -> str:
    return "" if not np.isfinite(d) else str((pd.Timestamp("1970-01-01") + pd.Timedelta(days=int(d))).date())


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return "".join(ch if ch.isalnum() else " " for ch in s)


def surname_key(name: str) -> str:
    return norm(name).split()[-1] if norm(name).split() else ""


COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "match_num", "draw_size",
        "tournament_id", "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id",
        "a_won", "source", "order"]


def windows(sub: pd.DataFrame, cls: pd.DataFrame) -> pd.DataFrame:
    """timing.build()'s window for matches with no source day and no dated sibling in their event (true of both
    groups: no link rows exist for them, see the log), then the draw narrowing within each event."""
    m = sub.copy()
    m["start"] = pd.to_datetime(m["tournament_date"]).map(day).astype(float)
    m["anchor"] = T.anchor_day(m)
    m["ev"] = pd.factorize(m["tour"] + "|" + m["tournament_id"].astype(str) + "|" + m["tournament_date"].astype(str))[0]
    m["phase"] = np.where(m["qualifying"].astype(bool), "qual", "main")
    m["era"] = T.era_of(m["year"]).to_numpy()
    m = m.merge(cls[["tour", "level", "phase", "round", "era", "lo", "hi", "median", "basis"]],
                on=["tour", "level", "phase", "round", "era"], how="left")
    rlo, rhi, named = T.rule_windows(m)
    has_rule = np.isfinite(rlo) & np.isfinite(rhi)
    emp = m["basis"].astype(str).str.startswith("empirical").to_numpy()
    lo = np.where(named & has_rule, rlo, np.where(emp, np.fmin(m["lo"], rlo), np.where(has_rule, rlo, m["lo"])))
    hi = np.where(named & has_rule, rhi, np.where(emp, np.fmax(m["hi"], rhi), np.where(has_rule, rhi, m["hi"])))
    m["basis_w"] = np.select([named & has_rule, emp & has_rule, emp, has_rule],
                             ["named_rule", "empirical+rule", "empirical", "rule"], "default")
    m["rule_label"] = T.rule_label(m).to_numpy()
    m["es"] = m["anchor"].to_numpy() + lo
    m["lf"] = m["anchor"].to_numpy() + hi
    m, _ = T.draw_narrowing(m)
    return m


def main() -> None:
    m = pd.read_parquet(S0, columns=COLS)
    m["tournament_date"] = pd.to_datetime(m["tournament_date"])
    nm = (pd.read_parquet(MP, columns=["player_id", "player_name"]).drop_duplicates("player_id")
          .set_index("player_id")["player_name"])
    tm = pd.read_parquet(TM, columns=["match_id", "es", "lf", "obs", "exact", "window_basis", "sources"])
    cls = pd.read_csv(CLS)
    m = m.merge(tm, on="match_id", how="left")
    m["a_name"], m["b_name"] = m["player_a_id"].map(nm), m["player_b_id"].map(nm)

    # ---------------- link files: do any hold these match ids? ----------------
    ids_all = set(m.loc[m["tournament_id"].astype(str).eq(G1_TID), "match_id"]) | set(G2_IDS)
    hits = []
    for p in sorted((ROOT / "data/studies/match_timing/links").glob("*.parquet")):
        try:
            cols = pd.read_parquet(p).columns
        except Exception:
            continue
        if "match_id" not in cols:
            continue
        f = pd.read_parquet(p, columns=["match_id"])
        n = int(f["match_id"].isin(ids_all).sum())
        if n:
            hits.append((p.name, n))
    print("link rows holding the G1/G2 match ids:", hits or "none")

    # ================================ G1 ================================
    g1 = m[m["tournament_id"].astype(str).eq(G1_TID)].copy()
    assert len(g1) == 31, len(g1)
    cur = windows(g1, cls)
    chk = cur[["match_id", "es", "lf"]].merge(tm[["match_id", "es", "lf"]], on="match_id", suffixes=("_sim", "_tm"))
    ok = bool(((chk["es_sim"] == chk["es_tm"]) & (chk["lf_sim"] == chk["lf_tm"])).all())
    print(f"G1 validation: re-implemented windows on the current date reproduce timing.parquet: {ok} "
          f"({int(((chk['es_sim'] == chk['es_tm']) & (chk['lf_sim'] == chk['lf_tm'])).sum())}/31)")
    new = g1.copy()
    new["tournament_date"] = pd.Timestamp(G1_NEW)
    sim = windows(new, cls)

    # play days from the local copies of TennisLive and SofaScore (no request made), matched by the two surnames
    tl = pd.read_parquet(TL, columns=["event_name", "discipline", "round", "player1_name", "player2_name", "score",
                                      "start_utc", "stage"])
    tl = tl[tl["event_name"].astype(str).eq("ATP Tenerife 3 Challenger") & tl["discipline"].eq("singles")].copy()
    tl["start_utc"] = pd.to_datetime(tl["start_utc"], utc=True, errors="coerce")
    tl["k"] = [frozenset([surname_key(a), surname_key(b)]) for a, b in zip(tl["player1_name"], tl["player2_name"])]
    se = pd.read_parquet(SE, columns=["tournament_name", "start_utc", "round_name", "home_name", "away_name"])
    se = se[se["tournament_name"].astype(str).eq("Tenerife 3, Spain")].copy()
    se["start_utc"] = pd.to_datetime(se["start_utc"], utc=True, errors="coerce")
    se["k"] = [frozenset([surname_key(a), surname_key(b)]) for a, b in zip(se["home_name"], se["away_name"])]

    def key_of(r):
        return frozenset([surname_key(r["a_name"]), surname_key(r["b_name"])])

    sim["k"] = sim.apply(key_of, axis=1)
    tl_day = tl.groupby("k")["start_utc"].agg(lambda s: sorted({str(x.date()) for x in s}))
    se_day = se.groupby("k")["start_utc"].agg(lambda s: sorted({str(x.date()) for x in s}))
    sim["tl_day"] = sim["k"].map(tl_day)
    sim["sofa_day"] = sim["k"].map(se_day)
    # Tenerife is on UTC+0 in winter (WET): the UTC day is the local day
    def play(r):
        d = set()
        for c in ("tl_day", "sofa_day"):
            if isinstance(r[c], list):
                d |= set(r[c])
        return sorted(d)
    sim["play_days"] = sim.apply(play, axis=1)
    sim["play_day"] = [day(p[0]) if len(p) == 1 else np.nan for p in sim["play_days"]]
    sim["es_new"], sim["lf_new"] = sim["es"], sim["lf"]
    sim = sim.merge(cur[["match_id", "es", "lf"]].rename(columns={"es": "es_old", "lf": "lf_old"}), on="match_id")
    sim["in_window"] = (sim["play_day"] >= sim["es_new"]) & (sim["play_day"] <= sim["lf_new"])
    sim["in_old_window"] = (sim["play_day"] >= sim["es_old"]) & (sim["play_day"] <= sim["lf_old"])
    out = sim[["match_id", "round", "a_name", "b_name", "score", "tl_day", "sofa_day", "es_old", "lf_old", "es_new",
               "lf_new", "basis_w", "rule_label", "in_window", "in_old_window"]].copy()
    for c in ["es_old", "lf_old", "es_new", "lf_new"]:
        out[c] = out[c].map(dstr)
    print(out.drop(columns=["match_id"]).to_string())
    print("G1 (ii): play day found for", int(np.isfinite(sim["play_day"]).sum()), "of 31; inside the new window:",
          int(sim["in_window"].sum()), "; inside the old window:", int(sim["in_old_window"].sum()))
    # web-only version of (ii): the event's own span (26 Feb - 3 Mar, final Sunday 3 Mar) against the new windows
    ev_lo, ev_hi = day("2024-02-26"), day("2024-03-03")
    fin = sim[sim["round"].eq("F")]
    print("G1 (ii, web only): every new window intersects 26 Feb - 3 Mar:",
          bool(((sim["es_new"] <= ev_hi) & (sim["lf_new"] >= ev_lo)).all()),
          "; the final's window holds Sun 3 Mar:", bool(((fin["es_new"] <= ev_hi) & (fin["lf_new"] >= ev_hi)).all()))
    out.to_csv(HERE / "sim_g1_windows.csv", index=False)

    # ---------- (i) and (iii): the players' other matches around both dates ----------
    pl = sorted(set(g1["player_a_id"]) | set(g1["player_b_id"]))
    sim_idx = sim.set_index("match_id")
    long = pd.concat([m[["match_id", "player_a_id"]].rename(columns={"player_a_id": "pid"}),
                      m[["match_id", "player_b_id"]].rename(columns={"player_b_id": "pid"})])
    long = long[long["pid"].isin(pl)].merge(m, on="match_id", how="left")
    long["is_g1"] = long["tournament_id"].astype(str).eq(G1_TID)
    # the simulated copy: new date and windows for the 31; everyone else unchanged
    S = long.copy()
    S.loc[S["is_g1"], "tournament_date"] = pd.Timestamp(G1_NEW)
    S.loc[S["is_g1"], "es"] = S.loc[S["is_g1"], "match_id"].map(sim_idx["es_new"]).to_numpy()
    S.loc[S["is_g1"], "lf"] = S.loc[S["is_g1"], "match_id"].map(sim_idx["lf_new"]).to_numpy()
    S["play"] = np.where(S["is_g1"], S["match_id"].map(sim_idx["play_day"]),
                         np.where(S["exact"].fillna(False).astype(bool), S["obs"], np.nan))
    hard, soft, order_rows = [], [], []
    for pid, g in S.groupby("pid"):
        mine = g[g["is_g1"]]
        span_lo, span_hi = mine["play"].min(), mine["play"].max()
        other = g[~g["is_g1"]]
        # hard: another match of his dated (exact) inside his Tenerife 3 span, or whose whole window lies inside it
        h = other[((other["play"] >= span_lo) & (other["play"] <= span_hi))
                  | ((other["es"] >= span_lo) & (other["lf"] <= span_hi))]
        for _, r in h.iterrows():
            hard.append({"pid": pid, "name": nm.get(pid), "match_id": r["match_id"],
                         "event": r["tournament_name"], "date": r["tournament_date"].date(), "round": r["round"],
                         "es": dstr(r["es"]), "lf": dstr(r["lf"]), "exact_day": dstr(r["play"])})
        # soft: another window touching any of his Tenerife 3 play days
        for _, r in other.iterrows():
            touch = [dstr(d) for d in mine["play"] if r["es"] <= d <= r["lf"]]
            if touch:
                soft.append({"pid": pid, "name": nm.get(pid), "event": r["tournament_name"],
                             "date": r["tournament_date"].date(), "round": r["round"], "es": dstr(r["es"]),
                             "lf": dstr(r["lf"]), "exact": bool(r["exact"]) if pd.notna(r["exact"]) else False,
                             "touches_t3_days": ";".join(touch)})
        # (iii) chronological order with the new date
        gg = C.chrono_sort(g.assign(match_num=g["match_num"])).reset_index(drop=True)
        pos = np.flatnonzero(gg["is_g1"].to_numpy())
        first, last = pos.min(), pos.max()
        contiguous = bool((np.diff(pos) == 1).all())
        prev = gg.iloc[first - 1] if first > 0 else None
        nxt = gg.iloc[last + 1] if last + 1 < len(gg) else None
        t3_first, t3_last = mine["play"].min(), mine["play"].max()

        def info(r):
            if r is None:
                return {}
            pday = r["play"] if np.isfinite(r["play"]) else np.nan
            return {"event": r["tournament_name"], "date": str(r["tournament_date"].date()), "round": r["round"],
                    "es": dstr(r["es"]), "lf": dstr(r["lf"]), "day": dstr(pday)}
        pi, ni = info(prev), info(nxt)
        prev_ok = prev is None or (prev["es"] <= t3_first and (not np.isfinite(prev["play"]) or prev["play"] <= t3_first))
        next_ok = nxt is None or (nxt["lf"] >= t3_last and (not np.isfinite(nxt["play"]) or nxt["play"] >= t3_last))
        order_rows.append({"pid": pid, "name": nm.get(pid), "t3_matches": len(mine), "t3_contiguous": contiguous,
                           "t3_first": dstr(t3_first), "t3_last": dstr(t3_last),
                           **{f"prev_{k}": v for k, v in pi.items()}, "prev_ok": prev_ok,
                           **{f"next_{k}": v for k, v in ni.items()}, "next_ok": next_ok})
    hard, soft, order_rows = pd.DataFrame(hard), pd.DataFrame(soft), pd.DataFrame(order_rows)
    print("\nG1 (i) hard conflicts after the fix (another match of the player dated inside his Tenerife 3 span):")
    print(hard.to_string() if len(hard) else "  none")
    print("\nG1 (i) softer overlaps after the fix (another match's window touches one of his Tenerife 3 play days):")
    print(soft.to_string() if len(soft) else "  none")
    print("\nG1 (iii) order after the fix:")
    print(order_rows.to_string())
    print("all contiguous:", bool(order_rows["t3_contiguous"].all()), "; prev ok:", bool(order_rows["prev_ok"].all()),
          "; next ok:", bool(order_rows["next_ok"].all()))
    hard.to_csv(HERE / "sim_g1_conflicts_after.csv", index=False)
    soft.to_csv(HERE / "sim_g1_overlaps_after.csv", index=False)
    order_rows.to_csv(HERE / "sim_g1_order_after.csv", index=False)

    # the same checks on the CURRENT date: what the misdating does now
    B = long.copy()
    B["play"] = np.where(B["is_g1"], B["match_id"].map(sim_idx["play_day"]),
                         np.where(B["exact"].fillna(False).astype(bool), B["obs"], np.nan))
    before = []
    for pid, g in B.groupby("pid"):
        mine = g[g["is_g1"]]
        wlo, whi = mine["es"].min(), mine["lf"].max()   # the misdated rows' current windows (19-31 Jan)
        other = g[~g["is_g1"] & (g["play"] >= wlo) & (g["play"] <= whi)]
        for _, r in other.iterrows():
            before.append({"pid": pid, "name": nm.get(pid), "event": r["tournament_name"],
                           "date": r["tournament_date"].date(), "round": r["round"], "exact_day": dstr(r["play"])})
    before = pd.DataFrame(before)
    print("\nG1 now: other matches of these players with an exact day inside the misdated rows' windows (19-31 Jan):")
    print(before.to_string() if len(before) else "  none")
    before.to_csv(HERE / "sim_g1_conflicts_now.csv", index=False)
    # Stage 0's order now: matches of these players at events dated after 2024-01-21 and before 2024-02-26 that the
    # misdated rows precede (in order) although they were played later
    later = long[~long["is_g1"] & (long["tournament_date"] > pd.Timestamp("2024-01-21"))
                 & (long["tournament_date"] < pd.Timestamp(G1_NEW))]
    print("matches of these players dated 22 Jan - 25 Feb 2024 (they follow the misdated rows in Stage 0's order "
          "though played before them):", later["match_id"].nunique())
    # clock: later matches that start (es) after a misdated result counts (old lf + 1) and before that match's play day
    reads = []
    for _, t3 in sim.iterrows():
        for pid in (t3["player_a_id"], t3["player_b_id"]):
            g = long[(long["pid"] == pid) & ~long["is_g1"]]
            r = g[(g["es"] >= t3["lf_old"] + 1) & (g["es"] < t3["play_day"])]
            reads += list(r["match_id"])
    print("Stage 0 matches of the same players whose earliest start falls after a misdated result counts and before "
          "that match was played (distinct):", len(set(reads)))

    # ================================ G2 ================================
    g2 = m[m["match_id"].isin(G2_IDS)].copy()
    cur2 = windows(g2, cls)
    chk2 = cur2[["match_id", "es", "lf"]].merge(tm[["match_id", "es", "lf"]], on="match_id", suffixes=("_sim", "_tm"))
    print("\nG2 validation: reproduces timing.parquet:",
          bool(((chk2["es_sim"] == chk2["es_tm"]) & (chk2["lf_sim"] == chk2["lf_tm"])).all()))
    new2 = g2.copy()
    new2["tournament_date"] = pd.Timestamp(G2_NEW)
    sim2 = windows(new2, cls)
    q2_day = day("2021-01-12")      # Q2 of the Doha qualifying (10-13 Jan; Q1 10-11, Q2 12, Q3 13: schedule_rules.csv
    #                                 rows 454-456; the ATP's 10-13 Jan announcement)
    rows = []
    for (_, a), (_, b) in zip(cur2.iterrows(), sim2.iterrows()):
        rows.append({"match_id": a["match_id"], "players": f"{a['a_name']} v {a['b_name']}",
                     "label_now": a["rule_label"], "window_now": f"{dstr(a['es'])}..{dstr(a['lf'])}",
                     "label_fixed": b["rule_label"], "basis_fixed": b["basis_w"],
                     "window_fixed": f"{dstr(b['es'])}..{dstr(b['lf'])}",
                     "q2_day_in_now": bool(a["es"] <= q2_day <= a["lf"]),
                     "q2_day_in_fixed": bool(b["es"] <= q2_day <= b["lf"])})
    rows = pd.DataFrame(rows)
    print(rows.to_string())
    # the variant that would hold: the same rows renamed as Sackmann's event (label AO21_QUALIFYING)
    alt = new2.copy()
    alt["tournament_name"] = "Doha Aus Open Qualies"
    sim3 = windows(alt, cls)
    print("variant (date AND name as Sackmann's): windows", [f"{dstr(a)}..{dstr(b)}" for a, b in zip(sim3["es"], sim3["lf"])],
          "label", sim3["rule_label"].unique().tolist())
    rows.to_csv(HERE / "sim_g2_windows.csv", index=False)
    # twins and the players' neighbouring matches
    pl2 = set(g2["player_a_id"]) | set(g2["player_b_id"])
    near = m[(m["player_a_id"].isin(pl2) | m["player_b_id"].isin(pl2))
             & (m["tournament_date"] >= pd.Timestamp("2020-12-01")) & (m["tournament_date"] <= pd.Timestamp("2021-03-01"))]
    near = near.assign(es_d=near["es"].map(dstr), lf_d=near["lf"].map(dstr))
    print(near.sort_values(["tournament_date", "round_order"])[
        ["match_id", "tournament_name", "tournament_date", "round", "status", "score", "a_name", "b_name", "a_won",
         "source", "es_d", "lf_d", "exact"]].to_string())


if __name__ == "__main__":
    main()
