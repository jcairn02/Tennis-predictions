"""Part E of the source-reconciliation study: birth dates and ages.

For every Stage 0 player, the birth date each source gives, the disagreements beyond a day, the majority, and the
players of the model's frame (the current best model's 67,226 matches: main-tour main draws at tennis-data's levels
from 2013) whose Stage 0 age disagrees with the majority's by 0.25 years or more.

Sources and how each reaches Stage 0's player ids (observed on the files; families count dependent copies once):
    sackmann        Sackmann's player files (data/dump/players/sackmann_archive/): Stage 0's own ids ('atp:<id>',
                    'wta:<id>') -> family sackmann
    tennis_abstract Tennis Abstract's bios (handoff tennis_abstract/, 1,904 with a date): its sackmann_id, kept only where
                    the bio's full name is Stage 0's name for that id (the scrape files one bio under several ids)
                    -> family sackmann (Jeff Sackmann's site; inference: the same database)
    open_tennis_data its players (data/dump/players/open_tennis_data/): Stage 0's id form; 'preferred_source' sackmann on
                    1,211 of 1,216 -> family derived_otd (a copy)
    tml             Tennis My Life's ATP player database (ATP codes): the code -> Stage 0 id crosswalk learned from TML
                    rows linked to Stage 0 (ctx_tml.py) -> family tml (inference: TML reads the ATP's site)
    wta_api         the WTA API's player pages of 2026 (data/dump/points/wta/player_matches/: the asked player's and each
                    opponent's dateOfBirth): the WTA id -> Stage 0 id crosswalk learned from the WTA's linked records
                    (the WTA API's match lists and the WTA website's records, oriented by names) -> family wta_official
    live_tennis_api its players (sackmann_id, kept where the Stage 0 id exists under a compatible name) -> family lta
    atp_profiles    the handoff's ATP profiles: no birth date in any of the 3,150 (reported, not used)
The majority: the official record where held (the WTA API for women; no ATP official date is held), else the date
most independent families give (ties: no majority).

Stage 0's age is Sackmann's convention (years at the tournament date, as (date - birth) / 365.25; one decimal in the
files). A frame row is off when |Stage 0's age - the majority's age at the tournament date| >= 0.25.

Writes context/dob_disagreements.csv, context/dob_frame_age_off.csv, context/dob_summary.json and
work/dob_players.parquet. Run: ./python.sh src/eda/source_reconciliation/ctx_dob.py
"""
from __future__ import annotations

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402

FAMILY = {"sackmann": "sackmann", "tennis_abstract": "sackmann", "open_tennis_data": "derived_otd", "tml": "tml",
          "wta_api": "wta_official", "live_tennis_api": "lta"}
SOURCES = list(FAMILY)
ONE_DAY = 1
AGE_TOL = 0.25


def to_date(v, fmt=None):
    if X.blank(v):
        return pd.NaT
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    try:
        if fmt:
            return pd.to_datetime(s, format=fmt, errors="coerce")
        if len(s) == 8 and s.isdigit():
            return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
        return pd.to_datetime(s[:10], errors="coerce")
    except (ValueError, TypeError):
        return pd.NaT


def players() -> pd.DataFrame:
    """Stage 0's players: id, tour, most common name, matches, frame matches."""
    m, p = C.stage0(["match_id", "tour", "tournament_date"], ["match_id", "player_id", "player_name", "age"])
    p = p.merge(m, on="match_id")
    frame = set(X.model_frame_ids())
    p["frame"] = p["match_id"].isin(frame)
    name = p.groupby(["player_id", "player_name"]).size().rename("n").reset_index().sort_values(
        ["player_id", "n"], ascending=[True, False]).drop_duplicates("player_id").set_index("player_id")["player_name"]
    g = p.groupby("player_id").agg(tour=("tour", "first"), matches=("match_id", "size"), frame_matches=("frame", "sum"))
    g["name"] = name
    return g.reset_index(), p


def sackmann() -> pd.DataFrame:
    out = []
    for tour in ("atp", "wta"):
        s = pd.read_parquet(C.DUMP / "players" / "sackmann_archive" / tour / f"{tour}_players.parquet",
                            columns=["player_id", "name_first", "name_last", "dob"])
        out.append(pd.DataFrame({"player_id": tour + ":" + s["player_id"].astype(str),
                                 "src_name": (s["name_first"].fillna("") + " " + s["name_last"].fillna("")).str.strip(),
                                 "dob": s["dob"].map(to_date), "source": "sackmann"}))
    return pd.concat(out, ignore_index=True)


def tennis_abstract(names: pd.Series) -> tuple[pd.DataFrame, dict]:
    rows = []
    for f in sorted(glob.glob(str(C.HANDOFF / "tennis_abstract" / "player_bios_*.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("dob_iso") and r.get("sackmann_id"):
                    rows.append({"sid": str(r["sackmann_id"]), "src_name": r.get("fullname"), "dob": r["dob_iso"]})
    t = pd.DataFrame(rows)
    stats = {"bios_with_date_and_id": int(len(t))}
    t["player_id"] = "atp:" + t["sid"]
    t["s0_name"] = t["player_id"].map(names)
    t["grade"] = [X._grade(a, b) if isinstance(b, str) else 0 for a, b in zip(t["src_name"], t["s0_name"])]
    stats["id_in_stage0"] = int(t["s0_name"].notna().sum())
    stats["kept_same_full_name"] = int((t["grade"] == 3).sum())
    t = t[t["grade"] == 3]
    t["dob"] = t["dob"].map(to_date)
    return t.assign(source="tennis_abstract")[["player_id", "src_name", "dob", "source"]], stats


def open_tennis_data() -> pd.DataFrame:
    o = pd.read_parquet(C.DUMP / "players" / "open_tennis_data" / "players.parquet",
                        columns=["player_id", "name", "birth_date", "preferred_source"])
    return pd.DataFrame({"player_id": o["player_id"].astype(str), "src_name": o["name"],
                         "dob": o["birth_date"].map(to_date), "source": "open_tennis_data"})


def tml(names: pd.Series) -> tuple[pd.DataFrame, dict]:
    """TML's ATP database by ATP code, through the code -> Stage 0 id crosswalk of TML rows linked to Stage 0: a code
    taken where at least 80% of its linked appearances name one Stage 0 id and no other code claims that id."""
    t = pd.read_parquet(X.WORK / "tml_rows.parquet")
    t = t[t["names_ok"]]
    m = X.stage0_matches().set_index("match_id")
    t = t[t["match_id"].isin(m.index)]
    mm = m.loc[t["match_id"]]
    aw = mm["a_won"].to_numpy(dtype=bool)
    same = t["tml_winner_is_s0_winner"].to_numpy(dtype=bool)
    win_id = np.where(aw, mm["player_a_id"].to_numpy(), mm["player_b_id"].to_numpy())
    los_id = np.where(aw, mm["player_b_id"].to_numpy(), mm["player_a_id"].to_numpy())
    s0w, s0l = np.where(same, win_id, los_id), np.where(same, los_id, win_id)
    pairs = pd.DataFrame({"code": np.concatenate([t["winner_id"].to_numpy(), t["loser_id"].to_numpy()]),
                          "s0": np.concatenate([s0w, s0l]),
                          "tour": np.concatenate([mm["tour"].to_numpy(), mm["tour"].to_numpy()])})
    pairs = pairs[pairs["tour"].eq("atp") & pairs["code"].notna()]
    cnt = pairs.groupby(["code", "s0"]).size().rename("n").reset_index()
    cnt["tot"] = cnt.groupby("code")["n"].transform("sum")
    best = cnt[cnt["n"] >= 0.8 * cnt["tot"]].sort_values("n", ascending=False).drop_duplicates("code")
    claimed = best.groupby("s0")["code"].nunique()
    best = best[best["s0"].isin(claimed.index[claimed == 1])]
    xw = dict(zip(best["code"], best["s0"]))
    db = pd.read_parquet(C.DUMP / "players" / "tennis_my_life" / "ATP_Database.parquet",
                         columns=["id", "player", "birthdate"])
    db["player_id"] = db["id"].astype(str).map(xw)
    stats = {"codes_in_linked_rows": int(cnt["code"].nunique()), "codes_mapped": int(len(xw)),
             "database_rows": int(len(db)), "database_rows_mapped": int(db["player_id"].notna().sum())}
    db = db[db["player_id"].notna()]
    db["s0_name"] = db["player_id"].map(names)
    db["grade"] = [X._grade(a, b) if isinstance(b, str) else 0 for a, b in zip(db["player"], db["s0_name"])]
    stats["mapped_names_compatible"] = int((db["grade"] >= 2).sum())
    db = db[db["grade"] >= 2]
    return pd.DataFrame({"player_id": db["player_id"], "src_name": db["player"], "dob": db["birthdate"].map(to_date),
                         "source": "tml"}), stats


def wta_crosswalk() -> tuple[dict, dict]:
    """WTA id -> Stage 0 id from the WTA's records linked to Stage 0 and oriented by names: the WTA API's match lists
    (the link file) and the WTA website's records (ctx_selflink). A WTA id is taken where 80% of its linked
    appearances name one Stage 0 id and no other WTA id claims that Stage 0 id."""
    from src.eda.source_reconciliation import ctx_readers as R
    m = X.stage0_matches().set_index("match_id")
    parts = []
    r = pd.read_parquet(X.WORK / "results_wta_api.parquet", columns=["match_id", "source_key", "p1_side"])
    ids = R.wta_api(r["source_key"])[["wta_id1", "wta_id2"]]
    r = r.join(ids, on="source_key")
    parts.append(r.rename(columns={"wta_id1": "id1", "wta_id2": "id2"})[["match_id", "p1_side", "id1", "id2"]])
    s = pd.read_parquet(X.WORK / "results_wta_site.parquet", columns=["match_id", "source_key", "p1_side"])
    rows = pd.read_parquet(X.WORK / "selfrows_wta_site.parquet", columns=["sid", "id1", "id2"]).set_index("sid")
    s = s.join(rows, on="source_key")
    parts.append(s[["match_id", "p1_side", "id1", "id2"]])
    a = pd.concat(parts, ignore_index=True)
    a = a[a["p1_side"].isin(["A", "B"])]
    mm = m.loc[a["match_id"]]
    pa, pb = mm["player_a_id"].to_numpy(), mm["player_b_id"].to_numpy()
    s1 = np.where(a["p1_side"].eq("A"), pa, pb)
    s2 = np.where(a["p1_side"].eq("A"), pb, pa)
    pairs = pd.DataFrame({"wid": np.concatenate([a["id1"].to_numpy(), a["id2"].to_numpy()]),
                          "s0": np.concatenate([s1, s2])})
    pairs = pairs[pairs["wid"].notna() & pairs["wid"].astype(str).ne("") & pairs["wid"].astype(str).ne("None")]
    pairs["wid"] = pairs["wid"].astype(str).str.replace(r"\.0$", "", regex=True)
    cnt = pairs.groupby(["wid", "s0"]).size().rename("n").reset_index()
    cnt["tot"] = cnt.groupby("wid")["n"].transform("sum")
    best = cnt[cnt["n"] >= 0.8 * cnt["tot"]].sort_values("n", ascending=False).drop_duplicates("wid")
    claimed = best.groupby("s0")["wid"].nunique()
    best = best[best["s0"].isin(claimed.index[claimed == 1])]
    return dict(zip(best["wid"], best["s0"])), {"wta_ids_in_linked_rows": int(cnt["wid"].nunique()),
                                                "wta_ids_mapped": int(len(best))}


def wta_api(names: pd.Series) -> tuple[pd.DataFrame, dict]:
    w = pd.read_parquet(C.DUMP / "points" / "wta" / "player_matches" / "2026.parquet",
                        columns=["asked_id", "asked_fullName", "asked_dateOfBirth", "opponent_id", "opponent_fullName",
                                 "opponent_dateOfBirth"])
    a = pd.concat([w[["asked_id", "asked_fullName", "asked_dateOfBirth"]].set_axis(["wid", "src_name", "dob"], axis=1),
                   w[["opponent_id", "opponent_fullName", "opponent_dateOfBirth"]].set_axis(["wid", "src_name", "dob"],
                                                                                           axis=1)])
    a = a[a["wid"].notna() & a["dob"].notna()]
    a["wid"] = a["wid"].astype(str).str.replace(r"\.0$", "", regex=True)
    # one date per WTA id: the asked page's, else the most common opponent copy
    a = a.groupby(["wid", "src_name", "dob"]).size().rename("n").reset_index().sort_values(
        ["wid", "n"], ascending=[True, False])
    dates_per_id = a.groupby("wid")["dob"].nunique()
    a = a.drop_duplicates("wid")
    xw, stats = wta_crosswalk()
    a["player_id"] = a["wid"].map(xw)
    stats.update(wta_ids_with_date=int(len(a)), wta_ids_with_two_dates=int((dates_per_id > 1).sum()),
                 mapped=int(a["player_id"].notna().sum()))
    a = a[a["player_id"].notna()]
    a["s0_name"] = a["player_id"].map(names)
    a["grade"] = [X._grade(x, y) if isinstance(y, str) else 0 for x, y in zip(a["src_name"], a["s0_name"])]
    stats["mapped_names_compatible"] = int((a["grade"] >= 1).sum())
    a = a[a["grade"] >= 1]
    return pd.DataFrame({"player_id": a["player_id"], "src_name": a["src_name"], "dob": a["dob"].map(to_date),
                         "source": "wta_api"}), stats


def live_tennis_api(names: pd.Series) -> tuple[pd.DataFrame, dict]:
    lp = pd.read_parquet(C.DUMP / "players" / "live_tennis_api_zenodo" / "players.parquet",
                         columns=["player_id", "name", "tour", "birthday", "sackmann_id"])
    lp = lp[lp["sackmann_id"].notna() & lp["sackmann_id"].astype(str).str.strip().ne("") & lp["birthday"].notna()
            & lp["birthday"].astype(str).str.strip().ne("")]
    rows = []
    for _, r in lp.iterrows():
        sid = str(r["sackmann_id"]).replace(".0", "")
        for tour in ("atp", "wta"):
            pid = f"{tour}:{sid}"
            n = names.get(pid)
            if isinstance(n, str) and X._grade(r["name"], n) >= 2:
                rows.append({"player_id": pid, "src_name": r["name"], "dob": to_date(r["birthday"], "%d.%m.%Y"),
                             "source": "live_tennis_api"})
    out = pd.DataFrame(rows).drop_duplicates("player_id")
    return out, {"players_with_sackmann_id_and_date": int(len(lp)), "mapped_names_compatible": int(len(out))}


def majority(g: pd.DataFrame) -> tuple:
    """(majority date, basis, families agreeing, families giving a date) for one player's dates."""
    g = g[g["dob"].notna()]
    if g.empty:
        return pd.NaT, "none", 0, 0
    off = g[g["family"].eq("wta_official")]
    # one date per family: the family's first source in SOURCES order (sackmann before tennis_abstract)
    fam = g.sort_values("order").drop_duplicates("family")
    indep = fam[~fam["family"].eq("derived_otd")]
    nfam = int(indep["family"].nunique())
    if len(off):
        d = off["dob"].iloc[0]
        agree = int((indep["dob"].sub(d).abs() <= pd.Timedelta(days=ONE_DAY)).sum())
        return d, "official_wta", agree, nfam
    if indep.empty:
        return fam["dob"].iloc[0], "dependent_only", 1, 0
    cnt = indep.groupby("dob").size().sort_values(ascending=False)
    if len(cnt) == 1:
        return cnt.index[0], "all_agree" if nfam > 1 else "single_family", int(cnt.iloc[0]), nfam
    if cnt.iloc[0] > cnt.iloc[1]:
        return cnt.index[0], "majority", int(cnt.iloc[0]), nfam
    return pd.NaT, "tie", int(cnt.iloc[0]), nfam


def main() -> int:
    pl, prow = players()
    names = pl.set_index("player_id")["name"]
    stats = {}
    frames = [sackmann()]
    ta, stats["tennis_abstract"] = tennis_abstract(names)
    frames.append(ta)
    frames.append(open_tennis_data())
    t, stats["tml"] = tml(names)
    frames.append(t)
    w, stats["wta_api"] = wta_api(names)
    frames.append(w)
    lt, stats["live_tennis_api"] = live_tennis_api(names)
    frames.append(lt)
    stats["atp_profiles"] = atp_profiles_count()
    d = pd.concat(frames, ignore_index=True)
    d = d[d["player_id"].isin(set(pl["player_id"])) & d["dob"].notna()]
    # a date before 1900 or after 2015 is no birth date of a professional (Sackmann's placeholders)
    d = d[(d["dob"] >= "1900-01-01") & (d["dob"] <= "2015-12-31")]
    d["family"] = d["source"].map(FAMILY)
    d["order"] = d["source"].map({s: i for i, s in enumerate(SOURCES)})
    d = d.drop_duplicates(["player_id", "source"])
    stats["dates_by_source"] = d["source"].value_counts().to_dict()
    wide = d.pivot(index="player_id", columns="source", values="dob")
    for s in SOURCES:
        if s not in wide:
            wide[s] = pd.NaT
    maj = {pid: majority(g) for pid, g in d.groupby("player_id")}
    wide["majority"] = pd.Series({k: v[0] for k, v in maj.items()})
    wide["majority_basis"] = pd.Series({k: v[1] for k, v in maj.items()})
    wide["families_agreeing"] = pd.Series({k: v[2] for k, v in maj.items()})
    wide["families_with_date"] = pd.Series({k: v[3] for k, v in maj.items()})
    span = d.groupby("player_id")["dob"].agg(lambda s: (s.max() - s.min()).days)
    wide["span_days"] = span
    wide = wide.join(pl.set_index("player_id")[["name", "tour", "matches", "frame_matches"]], how="left")
    wide["sackmann_minus_majority_days"] = (wide["sackmann"] - wide["majority"]).dt.days
    # Stage 0's ages against the majority's, frame rows
    fr = prow[prow["frame"]].copy()
    fr["tdate"] = pd.to_datetime(fr["tournament_date"])
    fr["majority"] = fr["player_id"].map(wide["majority"])
    fr["sackmann_dob"] = fr["player_id"].map(wide["sackmann"])
    fr["age_majority"] = (fr["tdate"] - fr["majority"]).dt.days / 365.25
    fr["age_sackmann"] = (fr["tdate"] - fr["sackmann_dob"]).dt.days / 365.25
    fr["diff"] = fr["age"] - fr["age_majority"]
    fr["diff_sackmann"] = fr["age"] - fr["age_sackmann"]
    off = fr[fr["diff"].abs() >= AGE_TOL]
    offp = off.groupby("player_id").agg(rows=("match_id", "size"), max_abs_diff=("diff", lambda s: float(s.abs().max())),
                                        mean_diff=("diff", "mean"),
                                        first_date=("tdate", "min"), last_date=("tdate", "max"),
                                        stage0_age_example=("age", "first"),
                                        majority_age_example=("age_majority", "first")).reset_index()
    offp = offp.join(wide[["name", "tour", "majority", "majority_basis", "sackmann", "tml", "wta_api",
                           "live_tennis_api", "tennis_abstract", "open_tennis_data", "frame_matches"]], on="player_id")
    # every Stage 0 player row (not only the frame): Stage 0's age against the majority's
    allr = prow.copy()
    allr["tdate"] = pd.to_datetime(allr["tournament_date"])
    allr["majority"] = allr["player_id"].map(wide["majority"])
    allr["diff"] = allr["age"] - (allr["tdate"] - allr["majority"]).dt.days / 365.25
    alloff = allr[allr["diff"].abs() >= AGE_TOL]
    mm = X.stage0_matches().set_index("match_id")
    alloff = alloff.join(mm[["level", "qualifying", "year", "source"]], on="match_id")
    allp = alloff.groupby("player_id").agg(rows=("match_id", "size"), max_abs_diff=("diff", lambda s: float(s.abs().max())),
                                           first_year=("year", "min"), last_year=("year", "max"),
                                           levels=("level", lambda s: ";".join(sorted(set(map(str, s))))),
                                           stage0_sources=("source", lambda s: ";".join(sorted(set(map(str, s)))))
                                           ).reset_index()
    allp = allp.join(wide[["name", "tour", "majority", "majority_basis", "sackmann", "tml", "wta_api",
                           "live_tennis_api", "tennis_abstract", "frame_matches"]], on="player_id")
    for c in ("majority", "sackmann", "tml", "wta_api", "live_tennis_api", "tennis_abstract"):
        allp[c] = pd.to_datetime(allp[c]).dt.strftime("%Y-%m-%d")
    allp.sort_values("rows", ascending=False).to_csv(X.OUT / "dob_all_rows_age_off.csv", index=False)
    # frame players whose sources disagree by 0.25 years or more with no majority (two families, one date each)
    unres = wide[(wide["frame_matches"] > 0) & wide["majority"].isna() & (wide["span_days"] >= AGE_TOL * 365.25)]
    unres = unres.reset_index()[["player_id", "name", "tour", "matches", "frame_matches"] + SOURCES +
                                ["majority_basis", "span_days"]]
    for c in SOURCES:
        unres[c] = pd.to_datetime(unres[c]).dt.strftime("%Y-%m-%d")
    unres.sort_values("frame_matches", ascending=False).to_csv(X.OUT / "dob_frame_unresolved.csv", index=False)
    stats["all_rows_age_off"] = {"player_rows": int(len(alloff)), "players": int(alloff["player_id"].nunique()),
                                 "by_level": alloff["level"].value_counts().to_dict(),
                                 "by_stage0_source": alloff["source"].value_counts().to_dict()}
    stats["frame_players_unresolved_ge_quarter_year"] = int(len(unres))
    X.WORK.mkdir(parents=True, exist_ok=True)
    wide.reset_index().to_parquet(X.WORK / "dob_players.parquet", index=False)
    dis = wide[wide["span_days"] > ONE_DAY].copy()
    out = dis.reset_index()[["player_id", "name", "tour", "matches", "frame_matches"] + SOURCES +
                            ["majority", "majority_basis", "families_agreeing", "families_with_date", "span_days",
                             "sackmann_minus_majority_days"]]
    for c in SOURCES + ["majority"]:
        out[c] = pd.to_datetime(out[c]).dt.strftime("%Y-%m-%d")
    out = out.sort_values(["frame_matches", "matches"], ascending=False)
    out.to_csv(X.OUT / "dob_disagreements.csv", index=False)
    for c in ("majority", "sackmann", "tml", "wta_api", "live_tennis_api", "tennis_abstract", "open_tennis_data",
              "first_date", "last_date"):
        offp[c] = pd.to_datetime(offp[c]).dt.strftime("%Y-%m-%d")
    offp.sort_values("rows", ascending=False).to_csv(X.OUT / "dob_frame_age_off.csv", index=False)
    # pairwise agreement between sources (players both date)
    pair = []
    for i, a in enumerate(SOURCES):
        for b in SOURCES[i + 1:]:
            x = wide[[a, b]].dropna()
            if x.empty:
                continue
            dd = (x[a] - x[b]).dt.days.abs()
            pair.append({"a": a, "b": b, "players": int(len(x)), "same_day": int((dd == 0).sum()),
                         "within_one_day": int((dd <= 1).sum()), "more_than_one_day": int((dd > 1).sum()),
                         "more_than_one_year": int((dd > 365).sum())})
    stats.update({
        "stage0_players": int(len(pl)), "players_with_a_date": int(wide.index.nunique()),
        "players_with_two_or_more_families": int((wide["families_with_date"] >= 2).sum()),
        "players_disagreeing_beyond_a_day": int(len(dis)),
        "players_disagreeing_in_frame": int((dis["frame_matches"] > 0).sum()),
        "majority_basis": wide["majority_basis"].value_counts().to_dict(),
        "sackmann_differs_from_majority_beyond_a_day": int((wide["sackmann_minus_majority_days"].abs() > 1).sum()),
        "pairwise": pair,
        "frame_player_rows": int(len(fr)), "frame_rows_with_majority": int(fr["majority"].notna().sum()),
        "frame_rows_age_off": int(len(off)), "frame_players_age_off": int(offp["player_id"].nunique()),
        "frame_rows_stage0_age_vs_sackmann_off": int((fr["diff_sackmann"].abs() >= AGE_TOL).sum()),
        "frame_rows_without_stage0_age": int(fr["age"].isna().sum()),
        "age_tolerance_years": AGE_TOL})
    X.write_json(X.OUT / "dob_summary.json", stats)
    X.log(json.dumps({k: v for k, v in stats.items() if k != "pairwise"}, default=str)[:3000])
    return 0


def atp_profiles_count() -> dict:
    n = with_dob = 0
    for f in sorted(glob.glob(str(C.HANDOFF / "atp_player_scrape" / "profiles" / "*.jsonl"))):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                n += 1
                with_dob += int(bool(str(r.get("dob") or "").strip()))
    return {"profiles": n, "with_birth_date": with_dob}


if __name__ == "__main__":
    sys.exit(main())
