"""The checks behind test/daily_prediction/ (each runs in its own process: it imports a tree's code).

    families      test 1: on the instance's build tree (read only), a checkpoint made by make_checkpoint into a
                  temporary state folder, then every family resumed from it against the same family recomputed in full,
                  on every row after the checkpoint day (not only the frame's): bit for bit (the IOS within 1e-6, its
                  bitwise share reported); Stage 4 and the Elo pieces' per-player parts, which have no state, against
                  the build's own stored tables
    invalidation  test 3: each family's slice hash on the tree's tables, then on copies with one row changed: a row
                  before the checkpoint day (each kind of field a family reads: a result, a box score, a player, a date
                  in the timeline, a match inserted) must change the hash of every part that reads it; a row after the
                  day must leave every hash as it is
    fit_cache     part 2: the fit from TabPFN's training caches on disk (dp_tabcache) against a run fitted by the
                  decided path, on a copy of that run's live rows: every seed's arrays bit for bit
Prints one JSON object (the last line) and writes it to --out.
Run: ./python.sh src/eda/daily_prediction/dp_selftest.py families|invalidation --day 2026-08-31 --out <json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dp_common as DC  # noqa: E402


def families(tree: Path, day: str, workers: int) -> dict:
    import numpy as np
    import pandas as pd
    import dp_elo as E
    import dp_forms as FM
    import dp_ios as IO
    import dp_pieces as PCS
    import dp_stage4 as S4
    import dp_state as SP
    import dp_store as STR
    from src.eda.predictability_diagnostic import stage3_ratings as S3
    d0 = DC.day_of(day)
    out: dict = {"tree": str(tree), "day": day, "state_root": str(DC.STATE), "families": {}}
    t0 = time.time()
    ck = STR.folder(day)
    man = SP.make_checkpoint(tree, d0, ck, workers=workers, made_from="dp_selftest families")
    out["checkpoint_seconds"] = man["seconds"]
    consts = E.constants(tree)

    def cmp_block(a, b) -> dict:
        c = DC.compare(a, b)
        c["bitwise"] = DC.bitwise(c)
        return c
    # Elo-type passes
    m, obs = PCS.stage0()
    res = {}
    for tour in ("atp", "wta"):
        inp = E.offset_inputs(m, tour, consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0)
        full, _ = E.run(inp)
        st, players = E.load_state(ck / man["families"]["elo"][tour]["file"])
        resumed, _ = E.run(inp, i0, None, E.remap(st, players, inp["players"], "offset"))
        res[f"offset_{tour}"] = {**cmp_block(resumed, full[i0:]), "matches_after": int(len(full) - i0)}
    mh = S3.load_history()
    mu = S3.mu_of(mh, S3.surface_means(mh))
    for tour in ("atp", "wta"):
        inp = E.stage3_inputs(mh, mu, tour, consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0)
        full, _ = E.run(inp)
        fm = man["families"]["stage3"][tour]
        st, players = E.load_state(ck / fm["file"])
        resumed, _ = E.run(inp, i0, None, E.remap(st, players, inp["players"], "stage3", inp["k"]))
        old = pd.read_parquet(ck / fm["block"])
        res[f"stage3_{tour}"] = {**cmp_block(resumed, full[i0:]), "matches_after": int(len(full) - i0),
                                 "saved_block_before": DC.bitwise(DC.compare(old[E.STAGE3_COLS].to_numpy("float64"),
                                                                             full[:i0]))}
    rows, typical, xd, pbp, ctx, _ = S4.load()
    for tour in ("atp", "wta"):
        inp = E.weighted_inputs(rows, tour, ctx["elo_scale"], consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0)
        for kind in E.WEIGHTED_KINDS:
            full, _ = E.run(inp, kind_w=kind)
            st, players = E.load_state(ck / man["families"]["weighted"][tour]["files"][kind])
            resumed, _ = E.run(inp, i0, None, E.remap(st, players, inp["players"], "weighted"), kind_w=kind)
            res[f"weighted_{kind}_{tour}"] = {**cmp_block(resumed, full[i0:]), "matches_after": int(len(full) - i0)}
    # the decided elo_variants (Stage 4's) against this module's full pass, for the record
    from src.eda.predictability_diagnostic import stage4_features as F
    ev = F.elo_variants(rows, ctx["elo_scale"])
    per = {}
    for tour in ("atp", "wta"):
        inp = E.weighted_inputs(rows, tour, ctx["elo_scale"], consts)
        for kind in E.WEIGHTED_KINDS:
            per[(kind, tour)] = (inp["rows_a"], E.run(inp, kind_w=kind)[0])
    mine = S4.elo_blocks(rows, per, consts)
    res["weighted_full_vs_decided_elo_variants"] = all(DC.bitwise(DC.compare(mine[k], ev[k])) for k in E.WEIGHTED_KINDS)
    out["families"]["elo"] = res
    out["elo_seconds"] = round(time.time() - t0, 1)
    # Stage B's forms
    t1 = time.time()
    import forms_state as FS
    fctx = FM.context(rows)
    chosen = FS.pinned_constants()
    specs = FM.specs_of(fctx, chosen)
    Zfull = FM.decided_z(fctx, chosen)
    Zres, old = FM.load_z(ck / man["families"]["forms"]["file"], fctx, d0)
    new = np.flatnonzero(~old)
    zn = FM.new_z(fctx, specs, new)
    zres = {}
    for k in Zres:
        Zres[k][new] = zn[k]
        zres[f"{k[1]}_{k[0]}"] = DC.bitwise(DC.compare(Zres[k], Zfull[k]))
    pool_day = fctx.rows["day"].to_numpy()[fctx.A]
    pool_new = np.flatnonzero(pool_day >= d0)
    fin = FM.inputs_for(fctx, specs, chosen, Zres, pool_new)
    ref = FM.decided_inputs(fctx, chosen, Zfull)
    fres = {col: DC.bitwise(DC.compare(fin[col], ref[col][pool_new])) for col in ref}
    out["families"]["forms"] = {"box_rows_after": int(len(new)), "z_pairs_bitwise_every_box_row": int(sum(zres.values())),
                                "z_pairs": len(zres), "pool_matches_after": int(len(pool_new)),
                                "inputs_bitwise": int(sum(fres.values())), "inputs": len(fres),
                                "not_bitwise": [k for k, v in {**zres, **fres}.items() if not v]}
    out["forms_seconds"] = round(time.time() - t1, 1)
    # Stage 4 (no state: recomputed for the day's players) against the build's stored table, float32
    t2 = time.time()
    stored = pd.read_parquet(F.FEATURES, columns=["match_id"] + list(S4.COLUMNS.values())).astype({"match_id": str})
    a_rows = rows.iloc[0::2]
    pool = F.pool_mask(rows)
    pids = a_rows["match_id"].to_numpy()[pool].astype(str)
    pdays = a_rows["day"].to_numpy()[pool]
    tg = pids[pdays >= d0]
    full_ev = {**ev}
    s4, rec4 = S4.inputs_for(rows, ctx, pbp, tg, full_ev)
    st4 = stored.set_index("match_id").loc[tg]
    out["families"]["stage4"] = {"matches_after": int(len(tg)), **rec4,
                                 "vs_stored_float32": {n: DC.bitwise(DC.compare(np.asarray(v, "float64").astype("float32"),
                                                                                st4[S4.COLUMNS[n]].to_numpy()))
                                                       for n, v in s4.items()}}
    # the Elo pieces: offset R/D and the per-player switch quantities against the build's pieces.parquet
    from src.eda.surface_elo_pieces import arms as EA
    from src.eda.surface_elo_pieces import common as PC
    from src.eda.predictability_diagnostic import stage1_baselines as B
    pieces = pd.read_parquet(PC.PIECES).astype({"match_id": str})
    offs = []
    for tour in ("atp", "wta"):
        inp = E.offset_inputs(m, tour, consts)
        offs.append(pd.DataFrame(E.run(inp)[0], columns=E.OFFSET_COLS).assign(match_id=inp["match_id"]))
    offset = pd.concat(offs, ignore_index=True)
    om = offset.set_index("match_id").reindex(m["match_id"].astype(str))
    sw = PCS.switch(m, obs, B.expected(om["R_a"].to_numpy(), om["R_b"].to_numpy()))
    tgp = pieces["match_id"].to_numpy()[(pd.to_datetime(m["tournament_date"]) >= pd.Timestamp(day)).to_numpy()]
    got = PCS.inputs(offset, sw, tgp)
    want = EA.new_inputs(pieces.set_index("match_id").loc[tgp].reset_index(drop=True))
    out["families"]["pieces"] = {"matches_after": int(len(tgp)),
                                 "vs_stored": {n: DC.bitwise(DC.compare(got[n], want[n].to_numpy("float64")))
                                               for n in got}}
    out["stage4_pieces_seconds"] = round(time.time() - t2, 1)
    del fctx, Zfull, Zres, specs
    # the surface IOS: resumed against full, every row queried on or after the day
    t3 = time.time()
    cache, pool_t = IO.build_cache()
    cfile = Path(tempfile.gettempdir()) / f"dp_selftest_cache_{os.getpid()}.npz"
    IO.save_cache(cfile, cache)
    jobs = []
    for tour, stat in IO.RUNS:
        s_ = IO.setup(cache[tour], stat)
        tgr = np.flatnonzero(s_.query >= d0)
        fi = man["families"]["ios"][f"{tour}_{stat}"]
        base = {"tour": tour, "stat": stat, "d0": d0, "cache": str(cfile), "targets": tgr.tolist()}
        jobs.append(dict(base, mode="full"))
        jobs.append(dict(base, mode="resume", ck=str(ck / fi["file"]), expect=fi["slice"]))
    results = IO.run_workers(jobs, workers)
    by = {}
    for r in results:
        by.setdefault(f"{r['tour']}_{r['stat']}", {})[r["mode"]] = r
    ios = {}
    for key, rr in by.items():
        f_, r_ = rr["full"], rr["resume"]
        if r_.get("invalid"):
            ios[key] = {"invalid": True}
            continue
        c = {k: DC.compare(r_["out"][k], f_["out"][k]) for k in ("O_eff", "D_eff", "O", "D", "E", "F")}
        ios[key] = {"rows_after": int(len(f_["out"]["rows"])), "max_abs_diff": max(v["max_abs_diff"] for v in c.values()),
                    "nan_pattern_equal": all(v["nan_pattern_equal"] for v in c.values()),
                    "bitwise_share": float(np.mean([v["bitwise_equal"] / max(v["rows"], 1) for v in c.values()])),
                    "resume_seconds": r_["seconds"], "full_seconds": f_["seconds"]}
    try:
        cfile.unlink()
    except OSError:
        pass
    out["families"]["ios"] = ios
    out["ios_seconds"] = round(time.time() - t3, 1)
    out["seconds"] = round(time.time() - t0, 1)
    return out


def invalidation(tree: Path, day: str) -> dict:
    """Slice hashes on the tree's tables and on copies with one row changed. A changed row the family reads, before the
    checkpoint day (main-tour matches: every family reads them), must change the hash; the same change after the day
    must not; and a change before the day that the family does not read (a box score the level layer weights to zero:
    an ITF match's) must not either, so a checkpoint is not thrown away for nothing."""
    import numpy as np
    import pandas as pd
    import dp_elo as E
    import dp_forms as FM
    import dp_ios as IO
    import dp_pieces as PCS
    import dp_stage4 as S4
    from src.eda.predictability_diagnostic import stage3_ratings as S3
    MAIN = ("GS", "FIN", "T1000", "T500", "T250")
    d0 = DC.day_of(day)
    consts = E.constants(tree)
    out: dict = {"tree": str(tree), "day": day, "cases": []}

    def case(family: str, change: str, when: str, expect: bool, h0: str, h1: str) -> None:
        out["cases"].append({"family": family, "change": change, "row": when, "hash_must_change": expect,
                             "hash_changed": h0 != h1, "as_required": (h0 != h1) == expect})

    def pick(mask_before, mask_after) -> tuple[int, int]:
        """The last row well before the day (400 days) and an early one after it."""
        return int(np.flatnonzero(mask_before)[-1]), int(np.flatnonzero(mask_after)[10])
    # the offset pass: a result, a player, an inserted match (main-tour matches)
    m, _ = PCS.stage0()
    t = m[m["tour"].eq("atp")]
    week = t["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    main_t = (t["level"].isin(MAIN) & ~t["qualifying"].astype(bool)).to_numpy()
    i_before, i_after = pick(main_t & (week < d0 - 400), main_t & (week >= d0))

    def offset_hash(frame):
        inp = E.offset_inputs(frame, "atp", consts)
        return E.slice_hash(inp, E.checkpoint_index(E.week_of(inp), d0))
    h0 = offset_hash(m)
    for when, i in (("before the day", i_before), ("after the day", i_after)):
        r = t.index[i]
        mm = m.copy()
        mm.loc[r, "a_won"] = not bool(mm.loc[r, "a_won"])
        case("elo offset", "a result flipped", when, when.startswith("before"), h0, offset_hash(mm))
        mm = m.copy()
        mm.loc[r, "player_b_id"] = "atp:999999999"
        case("elo offset", "a player replaced", when, when.startswith("before"), h0, offset_hash(mm))
    ins = m.loc[[t.index[i_before]]].copy()          # a past match seen twice (the layer resolves only known ids)
    mm = pd.concat([m.loc[:t.index[i_before]], ins, m.loc[t.index[i_before] + 1:]])
    mm["order"] = np.arange(len(mm))
    case("elo offset", "a match inserted", "before the day", True, h0, offset_hash(mm.reset_index(drop=True)))
    # Stage 3: a box score's serve points won
    mh = S3.load_history()
    mu = S3.mu_of(mh, S3.surface_means(mh))

    def s3_hash(frame):
        inp = E.stage3_inputs(frame, mu, "atp", consts)
        return E.slice_hash(inp, E.checkpoint_index(E.week_of(inp), d0))
    h0 = s3_hash(mh)
    wk = mh["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    rated = (mh["tour"].eq("atp") & mh["updates"]).to_numpy()
    main_h = (mh["level"].isin(MAIN) & ~mh["qualifying"].astype(bool)).to_numpy()
    rb, ra = pick(rated & main_h & (wk < d0 - 400), rated & main_h & (wk >= d0))
    itf = int(np.flatnonzero(rated & mh["level"].eq("ITF").to_numpy() & (wk < d0 - 400))[-1])
    for when, r, expect in (("before the day", rb, True), ("after the day", ra, False),
                            ("before the day, not read (an ITF box score the layer weights to zero)", itf, False)):
        mm = mh.copy()
        mm.iloc[r, mm.columns.get_loc("w_a")] = mm.iloc[r]["w_a"] - 1
        case("stage3", "serve points won changed", when, expect, h0, s3_hash(mm))
    # the games-weighted pass and Stage B's forms, on Stage 4's rows
    rows, typical, xd, pbp, ctx, _ = S4.load()

    def w_hash(rw):
        inp = E.weighted_inputs(rw, "atp", ctx["elo_scale"], consts)
        return E.slice_hash(inp, E.checkpoint_index(E.week_of(inp), d0))
    h0 = w_hash(rows)
    a = rows.iloc[0::2]
    ok_a = (a["tour"].eq("atp") & a["level"].isin(MAIN) & ~a["qualifying"].astype(bool)).to_numpy()         & np.isfinite(a["games_won_n"].to_numpy(dtype="float64"))
    wk = a["day"].to_numpy()
    jb, ja = pick(ok_a & (wk < d0 - 400), ok_a & (wk >= d0))
    for when, r in (("before the day", 2 * jb), ("after the day", 2 * ja)):
        rr = rows.copy()
        rr.iloc[r, rr.columns.get_loc("games_won_n")] = rr.iloc[r]["games_won_n"] - 1
        case("elo weighted", "games won changed", when, when.startswith("before"), h0, w_hash(rr))
    import forms_state as FS
    chosen = FS.pinned_constants()

    def f_hash(rw):
        fctx = FM.context(rw)
        return FM.slice_hash(fctx, FM.specs_of(fctx, chosen), chosen, d0)
    h0 = f_hash(rows)
    boxm = (np.isfinite(rows["ace_n"].to_numpy(dtype="float64")) & (rows["ace_d"].to_numpy(dtype="float64") > 2)
            & rows["tour"].eq("atp").to_numpy() & rows["level"].isin(MAIN).to_numpy()
            & ~rows["qualifying"].astype(bool).to_numpy())
    wk = rows["day"].to_numpy()
    rb, ra = pick(boxm & (wk < d0 - 400), boxm & (wk >= d0))
    for when, r in (("before the day", rb), ("after the day", ra)):
        rr = rows.copy()
        rr.iloc[r, rr.columns.get_loc("ace_n")] = rr.iloc[r]["ace_n"] + 1
        case("forms", "a box score count changed (aces)", when, when.startswith("before"), h0, f_hash(rr))
    del rows
    # the surface IOS: a box score value, a timeline window
    cache, _ = IO.build_cache()
    td = cache["atp"]
    main_r = np.asarray(td["lle_bucket"]) == 0                    # level code 0: MAIN
    itf_r = np.isin(np.asarray(td["lle_bucket"]), [5, 6])         # ITF, ITFQ (level_layer_ios.BUCKETS)
    for stat in ("ace", "hold"):
        s = IO.setup(td, stat)
        h0 = IO.slice_hash(s, d0)
        okr = np.asarray(td["stats"][stat]["ok"], bool)
        rb, ra = pick(okr & main_r & (s.release < d0 - 400), okr & main_r & (s.query > d0 + 3))
        ri = int(np.flatnonzero(okr & itf_r & (s.release < d0 - 400))[-1])
        for when, r, expect in (("before the day", rb, True), ("after the day", ra, False),
                                ("before the day, not read (an ITF box score the layer weights to zero)", ri, False)):
            t2 = dict(td, stats={k: dict(v) for k, v in td["stats"].items()})
            y = t2["stats"][stat]["y"].copy()
            y[r] += 0.01
            t2["stats"][stat]["y"] = y
            case(f"ios atp {stat}", "a box score value changed", when, expect, h0, IO.slice_hash(IO.setup(t2, stat), d0))
            if expect is False and "not read" in when:
                continue
            t3 = dict(td)
            for k in ("es", "lf", "obs"):
                v = td[k].copy()
                v[[r, r ^ 1]] += 1.0
                t3[k] = v
            case(f"ios atp {stat}", "a match's timeline window moved one day", when, expect, h0,
                 IO.slice_hash(IO.setup(t3, stat), d0))
    out["all_as_required"] = all(c["as_required"] for c in out["cases"])
    return out


def invalidation_e2e(root: Path, week: str, rnd: str, ck_day: str, workers: int) -> dict:
    """Test 3 through the real steps: a replay's work tree and tables (as run_day builds them), then one past main-tour
    men's match with a box score moved one day later in the work tree's timeline (well before the checkpoint), then
    the states step from the checkpoint (run A) and the same states step with every part from scratch on the same
    changed tables (run B, tier 2). Required: the IOS runs that read the match recomputed in full, every other part
    resumed, and A's 57 inputs equal B's (bit for bit outside the joint solves, the IOS within 1e-6)."""
    import shutil
    import numpy as np
    import pandas as pd
    import dp_steps as S
    import dp_worktree as WT
    S.repo_imports()
    A, B = root / "resumed", root / "full"
    S.init(A, "replay", {"week": week, "round": rnd, "winner": "A"}, None, ck_day, "0-15")
    out: dict = {"runs": [str(A), str(B)], "checkpoint": ck_day, "seconds": {}}
    box = Path(S.run_config(A)["work_tree"])
    try:
        for name, fn in (("worktree", S.step_worktree), ("matchups", S.step_matchups), ("prices", S.step_prices),
                         ("tables", S.step_tables)):
            t0 = time.time()
            fn(A)
            out["seconds"][name] = round(time.time() - t0, 1)
        m = pd.read_parquet(box / DC.PD / "stage0_matches.parquet",
                            columns=["match_id", "tour", "level", "qualifying", "has_box", "tournament_date"])
        cut = pd.Timestamp(ck_day) - pd.Timedelta(days=60)
        cand = m[m["tour"].eq("atp") & m["level"].isin(["T500", "T250"]) & ~m["qualifying"].astype(bool)
                 & m["has_box"].astype(bool) & (m["tournament_date"] < cut)]
        mid = str(cand.sort_values("tournament_date")["match_id"].iloc[-1])
        tpath = box / DC.MT / "timing.parquet"
        t = pd.read_parquet(tpath)
        sel = t["match_id"].astype(str).eq(mid).to_numpy()
        before = t.loc[sel, ["es", "lf", "obs"]].to_dict("records")
        for c in ("es", "lf", "obs"):
            t.loc[sel, c] = t.loc[sel, c] + 1
        t.to_parquet(tpath, index=False)
        out["changed"] = {"match_id": mid, "timeline_before": before,
                          "timeline_after": t.loc[sel, ["es", "lf", "obs"]].to_dict("records")}
        t0 = time.time()
        S.step_states(A, False, workers)
        out["seconds"]["states_resumed"] = round(time.time() - t0, 1)
        B.mkdir(parents=True, exist_ok=True)
        for f in ("run.json", "live_rows.parquet", "live_meta.parquet", "prices.parquet", "replay.json"):
            shutil.copy2(A / f, B / f)
        t0 = time.time()
        S.step_states(B, False, workers, full=True)
        out["seconds"]["states_full"] = round(time.time() - t0, 1)
    finally:
        if box.exists():
            out["cleanup"] = WT.cleanup(box)
    parts = DC.read_json(A / "states.json")["record"]["parts"]
    out["parts"] = parts
    recomputed = sorted(k for k, v in parts.items() if v != "resumed")
    out["recomputed"] = recomputed
    import dp_state as SP
    names = SP.model_names()
    fa = pd.read_parquet(A / "live_frame.parquet").set_index("match_id")
    fb = pd.read_parquet(B / "live_frame.parquet").set_index("match_id").loc[fa.index]
    per = {n: DC.compare(fa[f"in_{n}"].to_numpy(), fb[f"in_{n}"].to_numpy()) for n in names}
    ios = [n for n in names if n.startswith(("iosO_", "iosD_", "prod_"))]
    out["inputs_bitwise"] = int(sum(DC.bitwise(v) for v in per.values()))
    out["non_ios_bitwise"] = int(sum(DC.bitwise(per[n]) for n in names if n not in ios))
    out["ios_max_abs_diff"] = max(per[n]["max_abs_diff"] for n in ios)
    out["ios_nan_pattern_equal"] = all(per[n]["nan_pattern_equal"] for n in ios)
    out["matches"] = int(len(fa))
    out["as_required"] = (len(recomputed) > 0 and all(k.startswith("ios:atp_") for k in recomputed)
                          and out["non_ios_bitwise"] == len(names) - len(ios)
                          and out["ios_nan_pattern_equal"] and out["ios_max_abs_diff"] <= 1e-6)
    return out


FIT_INPUTS = ("live_frame.parquet", "live_meta.parquet", "run.json")   # run.json: the run's instance (since 11 Oct)


def compare_fits(a_dir: Path, b_dir: Path, seeds: list[int]) -> dict:
    """Two runs' fits seed by seed: every array of each seed's file (match ids, the grid, the own-price and the
    separate own-price probabilities) bit for bit."""
    import numpy as np
    out: dict = {"seeds": {}, "compared": 0}
    for f in sorted((Path(a_dir) / "fit").glob("season*_seed*.npz")):
        seed = int(f.stem.split("_seed")[1])
        g = Path(b_dir) / "fit" / f.name
        if seed not in seeds:
            continue
        if not g.exists():
            out["seeds"][f.stem] = {"missing": str(g)}
            continue
        with np.load(f, allow_pickle=False) as za, np.load(g, allow_pickle=False) as zb:
            res = {"arrays": sorted(set(za.files) & set(zb.files)),
                   "only_one_side": sorted(set(za.files) ^ set(zb.files))}
            for k in res["arrays"]:
                x, y = za[k], zb[k]
                res[f"{k}_bitwise"] = bool(x.shape == y.shape and x.dtype == y.dtype and x.tobytes() == y.tobytes())
                if x.dtype.kind == "f" and x.shape == y.shape:
                    d = np.abs(x - y)
                    res[f"{k}_max_abs"] = float(np.nanmax(d)) if np.isfinite(d).any() else 0.0
        out["seeds"][f.stem] = res
        out["compared"] += 1
    out["all_bitwise"] = bool(out["compared"] == len(seeds) and all(
        not r.get("missing") and all(v for k, v in r.items() if k.endswith("_bitwise")) for r in out["seeds"].values()))
    out["max_abs"] = max((v for r in out["seeds"].values() for k, v in r.items() if k.endswith("_max_abs")), default=None)
    return out


def fit_cache(src: Path, seeds: str, mode: str, tag: str, direct: str = "") -> dict:
    """The fit with TabPFN's training caches (mode "use" or "rebuild"), or the decided path ("off"), on a copy of a
    fitted run's live rows, against that run's own fit: bit for bit, seed by seed. A new run folder each time
    (<src>_fitcache_<tag>); refuses an existing one."""
    import shutil

    import dp_steps as S
    dst = DC.RUNS / f"{Path(src).name}_fitcache_{tag}"
    if dst.exists():
        raise SystemExit(f"{dst} exists: give another --tag")
    dst.mkdir(parents=True)
    for f in FIT_INPUTS:
        shutil.copy2(Path(src) / f, dst / f)
    t0 = time.time()
    S.step_fit(dst, seeds, direct, mode)
    out = {"source": str(src), "run": str(dst), "mode": mode, "seconds": round(time.time() - t0, 1),
           **compare_fits(Path(src), dst, S.span(seeds))}
    out["per_seed"] = {f.stem: {k: v for k, v in DC.read_json(f).items()
                                if k in ("how", "seconds", "fit_seconds", "predict_seconds", "load_seconds",
                                         "build_seconds", "save_seconds", "bytes", "peak_gpu_gb")}
                       for f in sorted((dst / "fit").glob("season*_seed*.json"))}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("check", choices=("families", "invalidation", "invalidation_e2e", "fit_cache"))
    ap.add_argument("--src", default=None, help="fit_cache: a fitted run whose fit is the reference")
    ap.add_argument("--seeds", default="0-15", help="fit_cache: the seeds")
    ap.add_argument("--mode", default="use", choices=("use", "rebuild", "off"), help="fit_cache: the fit's cache mode")
    ap.add_argument("--tag", default=None, help="fit_cache: the new run folder's suffix")
    ap.add_argument("--direct-seeds", default="", help="fit_cache: seeds that also predict the own prices alone")
    ap.add_argument("--root", default=None, help="invalidation_e2e: the folder of its two runs")
    ap.add_argument("--checkpoint", default="2026-06-22", help="invalidation_e2e: the checkpoint day")
    ap.add_argument("--tree", default=str(DC.BASE_TREE))
    ap.add_argument("--day", default="2026-08-31")
    ap.add_argument("--workers", type=int, default=7)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.check == "fit_cache":
        res = fit_cache(Path(a.src), a.seeds, a.mode, a.tag or DC.stamp().replace(":", ""), a.direct_seeds)
        DC.write_json(Path(a.out), res)
        print(json.dumps({k: v for k, v in res.items() if k not in ("seeds", "per_seed")}, default=str))
        return 0
    if a.check == "invalidation_e2e":                  # drives the steps from the repository's process
        root = Path(a.root) if a.root else DC.RUNS / f"invalidation_e2e_{DC.stamp()}"
        res = invalidation_e2e(root, "2026-07-13", "R16", a.checkpoint, a.workers)
        DC.write_json(Path(a.out), res)
        print(json.dumps(res, default=str))
        return 0
    tree = Path(a.tree)
    DC.enter_tree(tree, read_only=True)
    res = families(tree, a.day, a.workers) if a.check == "families" else invalidation(tree, a.day)
    DC.write_json(Path(a.out), res)
    print(json.dumps(res, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
