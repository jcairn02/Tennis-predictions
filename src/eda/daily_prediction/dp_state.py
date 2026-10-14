"""The state path: a checkpoint of every family, and the model's 57 inputs of chosen matches from it.

Runs inside a tree (dp_common.enter_tree): the instance's build tree (read only: checkpoints from the template's own
tables, and the tests), or a run's work tree (today's tables, with the live rows).

    make_checkpoint(...)   every family's state before the checkpoint day, its slice hash, the instance's constants
                           files (dp_store)
    inputs(...)            the 57 inputs of the target matches: each family part resumed from the checkpoint when its
                           slice is unchanged on the tree's tables, recomputed in full when not (recorded), or every
                           part in full (ck None: the lean full build, tier 2)

The order matters where one family reads another's output: Stage 3's table is written (work tree) or checked (read-only
tree) before Stage 4's loader reads it; the games-weighted pass reads Stage 4's rows and constants.

Storage casts, as the chain stores each family (the frames then read float64): Stage 4's six and Stage B's 17 inputs
float32; the IOS, the Elo pieces, the context and the odds input float64.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC
import dp_context as CX
import dp_elo as E
import dp_forms as FM
import dp_ios as IO
import dp_pieces as PCS
import dp_stage4 as S4
import dp_store as ST

FLOAT32 = set(S4.COLUMNS) | set(FM.FRAME_NAMES)


def model_names(instance: Path = DC.INSTANCE) -> list[str]:
    return [d["name"] for d in json.loads((instance / "model_inputs.json").read_text(encoding="utf-8"))["inputs"]]


def _mods():
    from src.eda.predictability_diagnostic import stage1_baselines as B
    from src.eda.predictability_diagnostic import stage3_ratings as S3
    return B, S3


# ------------------------------------------------------------------------------------------------
# The checkpoint

def make_checkpoint(tree: Path, d0: int, ck: Path, workers: int = 7, made_from: str = "") -> dict:
    """Every family's state before day d0 on the tree's tables, into folder ck (written last: the manifest)."""
    B, S3 = _mods()
    t_all = time.time()
    if (ck / "manifest.json").exists():
        raise SystemExit(f"{ck} already holds a checkpoint")
    ck.mkdir(parents=True, exist_ok=True)
    consts = E.constants(tree)
    fam: dict = {"elo": {}, "stage3": {}, "weighted": {}, "forms": {}, "ios": {}}
    rec: dict = {}
    # the offset pass
    t0 = time.time()
    m, obs = PCS.stage0()
    for tour in ("atp", "wta"):
        inp = E.offset_inputs(m, tour, consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0)
        _, st = E.run(inp, 0, i0)
        f = ck / "elo" / f"{tour}_offset.pkl"
        fam["elo"][tour] = {"slice": E.slice_hash(inp, i0), "i0": i0, "matches": len(inp["match_id"]),
                            "file": str(f.relative_to(ck)), "bytes": E.save_state(f, st, inp["players"])}
    rec["offset_seconds"] = round(time.time() - t0, 1)
    # Stage 3: the state and the outputs before i0 (Stage 4's loader reads the whole table)
    t0 = time.time()
    mh = S3.load_history()
    mu = S3.mu_of(mh, S3.surface_means(mh))
    for tour in ("atp", "wta"):
        inp = E.stage3_inputs(mh, mu, tour, consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0)
        out, st = E.run(inp, 0, i0)
        f = ck / "elo" / f"{tour}_stage3.pkl"
        blk = pd.DataFrame(out, columns=E.STAGE3_COLS)
        blk.insert(0, "match_id", inp["match_id"][:i0])
        fb = ck / "elo" / f"{tour}_stage3_block.parquet"
        blk.to_parquet(fb, index=False)
        fam["stage3"][tour] = {"slice": E.slice_hash(inp, i0), "i0": i0, "file": str(f.relative_to(ck)),
                               "block": str(fb.relative_to(ck)), "bytes": E.save_state(f, st, inp["players"])}
    rec["stage3_seconds"] = round(time.time() - t0, 1)
    # Stage 4's rows: the games-weighted pass and Stage B's z
    t0 = time.time()
    rows, typical, xd, pbp, ctx, _ = S4.load()
    rec["stage4_rows_seconds"] = round(time.time() - t0, 1)
    t0 = time.time()
    for tour in ("atp", "wta"):
        inp = E.weighted_inputs(rows, tour, ctx["elo_scale"], consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0)
        part = {"slice": E.slice_hash(inp, i0), "i0": i0, "files": {}}
        for kind in E.WEIGHTED_KINDS:
            _, st = E.run(inp, 0, i0, kind_w=kind)
            f = ck / "elo" / f"{tour}_weighted_{kind}.pkl"
            E.save_state(f, st, inp["players"])
            part["files"][kind] = str(f.relative_to(ck))
        fam["weighted"][tour] = part
    rec["weighted_seconds"] = round(time.time() - t0, 1)
    t0 = time.time()
    import forms_state as FS
    fctx = FM.context(rows)
    chosen = FS.pinned_constants()
    specs = FM.specs_of(fctx, chosen)
    Z = FM.decided_z(fctx, chosen)
    fz = ck / "forms" / "z.parquet"
    fam["forms"] = {"slice": FM.slice_hash(fctx, specs, chosen, d0), "file": str(fz.relative_to(ck)),
                    **FM.save_z(fz, fctx, Z, d0)}
    rec["forms_seconds"] = round(time.time() - t0, 1)
    del fctx, Z, specs
    # the surface IOS: 14 runs in workers
    t0 = time.time()
    cache, pool = IO.build_cache()
    cache_file = ck / "_cache_tmp.npz"
    IO.save_cache(cache_file, cache)
    rec["ios_cache_seconds"] = round(time.time() - t0, 1)
    jobs = [{"tour": t, "stat": s, "mode": "checkpoint", "d0": d0, "cache": str(cache_file),
             "out": str(ck / "ios" / f"{t}_{s}.npz")} for t, s in IO.RUNS]
    t0 = time.time()
    for r in IO.run_workers(jobs, workers):
        fam["ios"][f"{r['tour']}_{r['stat']}"] = {"slice": r["slice"], "file": f"ios/{r['tour']}_{r['stat']}.npz",
                                                   **r["checkpoint"], "record": r["record"], "setup": r["setup"]}
    rec["ios_runs_seconds"] = round(time.time() - t0, 1)
    try:
        cache_file.unlink()
    except OSError as e:
        rec["cache_not_deleted"] = str(e)
    manifest = {"instance": DC.INSTANCE_ID, "day": DC.date_of(d0), "d0": int(d0), "made_at": DC.stamp(),
                "made_on_tree": str(tree), "made_from": made_from,
                "tables": {"stage0_sha256": DC.sha256(Path(tree) / DC.PD / "stage0_matches.parquet"),
                           "timing_sha256": DC.sha256(Path(tree) / DC.MT / "timing.parquet")},
                "layer_config": str(DC.layer_config_for(tree)), "constants": consts,
                "constants_files": ST.copy_constants(tree, ck), "code": ST.code_hashes(), "families": fam,
                "seconds": {**rec, "total": round(time.time() - t_all, 1)}}
    ST.write_manifest(ck, manifest)
    return manifest


# ------------------------------------------------------------------------------------------------
# The inputs of chosen matches

def _part_status(man: dict | None, name: str, key: str, got: str) -> tuple[bool, str]:
    """Resume a part? (its slice unchanged), and how it is recorded."""
    if man is None:
        return False, "full (no checkpoint)"
    want = man["families"][name][key]["slice"] if key else man["families"][name]["slice"]
    return (True, "resumed") if want == got else (False, "slice changed: recomputed in full")


def forms_family(a: dict) -> dict:
    """Stage B's 17 inputs of the target matches, self-contained so that it runs in its own process (inputs() starts
    it once Stage 3's table is written): Stage 4's rows loaded here (stage4_features.load_rows, which reads that table;
    nothing inputs() runs on the rows before Stage B changes them: no in-place write in stat_xd, pbp_history,
    constants, weighted_inputs or inputs_for), the context, z resumed from the checkpoint when its slice is unchanged
    (else the decided forms_z in full), step 3 for the targets. a: target_ids, ck, d0."""
    import forms_state as FS
    t_all = time.time()
    target_ids = np.asarray(a["target_ids"]).astype(str)
    ck = Path(a["ck"]) if a.get("ck") else None
    man = ST.read_manifest(ck) if ck is not None else None
    d0 = a["d0"]
    out: dict = {"parts": {}, "seconds": {}}
    t0 = time.time()
    rows, _ = S4._F().load_rows()
    out["seconds"]["forms_rows"] = round(time.time() - t0, 1)
    t0 = time.time()
    fctx = FM.context(rows)
    chosen = FS.pinned_constants()
    specs = FM.specs_of(fctx, chosen)
    out["seconds"]["forms_context"] = round(time.time() - t0, 1)
    t0 = time.time()
    resume, out["parts"]["forms:"] = _part_status(man, "forms", "", FM.slice_hash(fctx, specs, chosen, d0) if man else "")
    if resume:
        Z, old = FM.load_z(ck / man["families"]["forms"]["file"], fctx, d0)
        new = np.flatnonzero(~old)
        zn = FM.new_z(fctx, specs, new)
        for k in Z:
            Z[k][new] = zn[k]
        out["forms_new_box_rows"] = int(len(new))
    else:
        Z = FM.decided_z(fctx, chosen)
    pool_ids = rows["match_id"].to_numpy()[fctx.A].astype(str)
    pool_pos = pd.Index(pool_ids).get_indexer(target_ids)
    if (pool_pos < 0).any():
        raise RuntimeError(f"{int((pool_pos < 0).sum())} target matches are not in Stage B's pool")
    feats = FM.inputs_for(fctx, specs, chosen, Z, pool_pos)
    out["forms"] = {name: np.asarray(feats[col]) for name, col in FM.FRAME_NAMES.items()}
    out["seconds"]["forms"] = round(time.time() - t0, 1)
    out["seconds"]["forms_family"] = round(time.time() - t_all, 1)
    return out


def ios_family(a: dict) -> dict:
    """The surface IOS's 21 inputs of the target matches, self-contained so that it runs in its own process from the
    start of inputs() (it reads no other family's output): the solver cache from the tree's tables, the 14 runs in
    worker processes with single-threaded BLAS (resumed where the slice is unchanged, else in full), three inputs a
    statistic. a: target_ids, ck, d0, workers, cache_dir."""
    t_all = time.time()
    target_ids = np.asarray(a["target_ids"]).astype(str)
    ck = Path(a["ck"]) if a.get("ck") else None
    man = ST.read_manifest(ck) if ck is not None else None
    d0 = a["d0"]
    out: dict = {"parts": {}, "seconds": {}}
    t0 = time.time()
    cache, pool = IO.build_cache()
    cache_file = Path(a["cache_dir"]) / f"_ios_cache_{DC.stamp()}.npz"
    IO.save_cache(cache_file, cache)
    pidx = pool.set_index(pool["match_id"].astype(str))
    tp = pidx.reindex(target_ids)
    if tp["pos_a"].isna().any():
        raise RuntimeError(f"{int(tp['pos_a'].isna().sum())} target matches are not in the IOS pool")
    out["seconds"]["ios_cache"] = round(time.time() - t0, 1)
    t0 = time.time()
    jobs = []
    for tour, stat in IO.RUNS:
        sel = tp["tour"].eq(tour).to_numpy()
        rows_a = tp["pos_a"].to_numpy()[sel].astype(np.int64)
        tg = np.sort(np.r_[rows_a, rows_a + 1])
        job = {"tour": tour, "stat": stat, "d0": d0 if d0 is not None else 0, "cache": str(cache_file),
               "targets": tg.tolist()}
        if man is not None and len(tg):
            fi = man["families"]["ios"][f"{tour}_{stat}"]
            job.update({"mode": "resume", "ck": str(ck / fi["file"]), "expect": fi["slice"]})
        else:
            job["mode"] = "full"
        if len(tg):
            jobs.append(job)
    results = IO.run_workers(jobs, a["workers"])
    redo = [dict(j, mode="full") for j, r in zip(jobs, results) if r.get("invalid")]
    if redo:
        again = {(r["tour"], r["stat"]): r for r in IO.run_workers(redo, a["workers"])}
        results = [again.get((r["tour"], r["stat"]), r) for r in results]
    ios = {}
    for r in results:
        key = f"{r['tour']}_{r['stat']}"
        out["parts"][f"ios:{key}"] = ("resumed" if r["mode"] == "resume" else
                                      ("full (no checkpoint)" if man is None else "slice changed: recomputed in full"))
        sel = tp["tour"].eq(r["tour"]).to_numpy()
        vals = IO.match_inputs(cache[r["tour"]], r["out"], tp["pos_a"].to_numpy()[sel].astype(np.int64), r["stat"])
        for name, v in vals.items():
            ios.setdefault(name, np.full(len(target_ids), np.nan))[sel] = v
    out["ios_runs"] = {f"{r['tour']}_{r['stat']}": {"mode": r["mode"], "record": r.get("record"),
                                                   "seconds": r.get("seconds")} for r in results}
    try:
        cache_file.unlink()
    except OSError as e:
        out["cache_not_deleted"] = str(e)
    out["seconds"]["ios_runs"] = round(time.time() - t0, 1)
    out["seconds"]["ios_family"] = round(time.time() - t_all, 1)
    out["ios"] = ios
    return out


def inputs(tree: Path, read_only: bool, d0: int | None, ck: Path | None, target_ids, prices,
           workers: int = 7, cache_dir: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """The 57 inputs (the instance's order, in_<name>) of the target matches. ck None: every family in full (tier 2).
    prices: the margin-free chance of each target's side A (the odds input).

    Three processes (part 2: scheduling only, each family computes what it computed in one process): the surface IOS
    in its own from the start (ios_family), Stage B's forms in its own once Stage 3's table is written
    (forms_family), the Elo passes, Stage 3, Stage 4, the Elo pieces and the context here."""
    from concurrent.futures import ProcessPoolExecutor
    B, S3 = _mods()
    t_all = time.time()
    target_ids = np.asarray(target_ids).astype(str)
    if len(set(target_ids)) != len(target_ids):
        raise ValueError("target match ids repeat")
    man = ST.read_manifest(ck) if ck is not None else None
    if man is not None and d0 is None:
        d0 = int(man["d0"])
    consts = E.constants(tree)
    rec: dict = {"checkpoint": None if ck is None else str(ck), "d0": None if d0 is None else DC.date_of(d0),
                 "targets": int(len(target_ids)), "parts": {}, "seconds": {}}
    if man is not None:
        if consts != man["constants"]:
            raise ST.InvalidCheckpoint("the tree's constants differ from the checkpoint's (install them first)")
        bad = [k for k, ok in ST.check_constants(ck, tree, man).items() if not ok]
        if bad:
            raise ST.InvalidCheckpoint(f"constants files differ from the checkpoint's: {bad}")

    def part(name: str, key: str, got: str) -> bool:
        """Resume this part? (its slice unchanged); recorded either way."""
        if man is None:
            rec["parts"][f"{name}:{key}"] = "full (no checkpoint)"
            return False
        want = man["families"][name][key]["slice"] if key else man["families"][name]["slice"]
        ok = want == got
        rec["parts"][f"{name}:{key}"] = "resumed" if ok else "slice changed: recomputed in full"
        return ok

    # the surface IOS, in its own process from the start (section 6 below collects it)
    job = {"target_ids": target_ids.tolist(), "ck": None if ck is None else str(ck), "d0": d0}
    ex = ProcessPoolExecutor(max_workers=2)
    ios_fut = ex.submit(ios_family, {**job, "workers": workers, "cache_dir": str(cache_dir or (DC.OUT / "tmp"))})
    # 1. the offset pass
    t0 = time.time()
    m, obs = PCS.stage0()
    offs = []
    for tour in ("atp", "wta"):
        inp = E.offset_inputs(m, tour, consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0) if d0 is not None else 0
        if part("elo", tour, E.slice_hash(inp, i0) if man else ""):
            st, players = E.load_state(ck / man["families"]["elo"][tour]["file"])
            out, _ = E.run(inp, i0, None, E.remap(st, players, inp["players"], "offset"))
            ids = inp["match_id"][i0:]
        else:
            out, _ = E.run(inp)
            ids = inp["match_id"]
        offs.append(pd.DataFrame(out, columns=E.OFFSET_COLS).assign(match_id=ids))
    offset = pd.concat(offs, ignore_index=True)
    rec["seconds"]["offset"] = round(time.time() - t0, 1)
    # 2. Stage 3, its whole table
    t0 = time.time()
    mh = S3.load_history()
    mu = S3.mu_of(mh, S3.surface_means(mh))
    block = np.full((len(mh), 12), np.nan)
    for tour in ("atp", "wta"):
        inp = E.stage3_inputs(mh, mu, tour, consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0) if d0 is not None else 0
        if part("stage3", tour, E.slice_hash(inp, i0) if man else ""):
            fm = man["families"]["stage3"][tour]
            st, players = E.load_state(ck / fm["file"])
            out, _ = E.run(inp, i0, None, E.remap(st, players, inp["players"], "stage3", inp["k"]))
            old = pd.read_parquet(ck / fm["block"])
            if not np.array_equal(old["match_id"].astype(str).to_numpy(), inp["match_id"][:i0]):
                raise RuntimeError(f"stage3 {tour}: the saved outputs' matches differ from today's before the checkpoint")
            block[inp["rows"][:i0]] = old[E.STAGE3_COLS].to_numpy("float64")
            block[inp["rows"][i0:]] = out
        else:
            out, _ = E.run(inp)
            block[inp["rows"]] = out
    tab = E.stage3_table(mh, mu, block)
    if read_only:
        stored = pd.read_parquet(S3.RATINGS)
        same = (np.array_equal(stored["match_id"].astype(str).to_numpy(), tab["match_id"].astype(str).to_numpy())
                and all(np.array_equal(np.asarray(stored[c]), np.asarray(tab[c]), equal_nan=tab[c].dtype.kind == "f")
                        for c in tab.columns if c not in ("match_id", "tour")))
        rec["stage3_table"] = "equals the tree's stored table" if same else "DIFFERS from the tree's stored table"
        if not same:
            raise RuntimeError("Stage 3's table differs from the read-only tree's: Stage 4 would read another")
    else:
        tab.to_parquet(S3.RATINGS, index=False, compression="zstd")
        rec["stage3_table"] = f"written to {S3.RATINGS}"
    rec["seconds"]["stage3"] = round(time.time() - t0, 1)
    # 4. Stage B's forms, in its own process now that Stage 3's table is in place (Stage 4's rows read it)
    forms_fut = ex.submit(forms_family, job)
    # 3. Stage 4's rows, the games-weighted pass, Stage 4's six inputs
    t0 = time.time()
    rows, typical, xd, pbp, ctx, _ = S4.load()
    rec["seconds"]["stage4_rows"] = round(time.time() - t0, 1)
    t0 = time.time()
    per = {}
    for tour in ("atp", "wta"):
        inp = E.weighted_inputs(rows, tour, ctx["elo_scale"], consts)
        i0 = E.checkpoint_index(E.week_of(inp), d0) if d0 is not None else 0
        resume = part("weighted", tour, E.slice_hash(inp, i0) if man else "")
        for kind in E.WEIGHTED_KINDS:
            if resume:
                st, players = E.load_state(ck / man["families"]["weighted"][tour]["files"][kind])
                out, _ = E.run(inp, i0, None, E.remap(st, players, inp["players"], "weighted"), kind_w=kind)
                per[(kind, tour)] = (inp["rows_a"][i0:], out)
            else:
                out, _ = E.run(inp, kind_w=kind)
                per[(kind, tour)] = (inp["rows_a"], out)
    elo_w = S4.elo_blocks(rows, per, consts)
    rec["seconds"]["weighted"] = round(time.time() - t0, 1)
    s4, rec["stage4"] = S4.inputs_for(rows, ctx, pbp, target_ids, elo_w)
    rec["seconds"]["stage4_inputs"] = rec["stage4"]["seconds"]
    group = pd.Series(rows["group"].to_numpy()[0::2], index=rows["match_id"].to_numpy()[0::2].astype(str))
    del rows
    # 5. the Elo pieces
    t0 = time.time()
    om = offset.set_index("match_id")
    ra = om["R_a"].reindex(m["match_id"].astype(str)).to_numpy()
    rb = om["R_b"].reindex(m["match_id"].astype(str)).to_numpy()
    sw = PCS.switch(m, obs, B.expected(ra, rb))
    pieces = PCS.inputs(offset, sw, target_ids)
    rec["seconds"]["pieces"] = round(time.time() - t0, 1)
    # 7. context and the odds input
    t0 = time.time()
    context, info = CX.inputs(target_ids, group)
    odds = CX.odds_logit(prices)
    rec["seconds"]["context"] = round(time.time() - t0, 1)
    # 4 and 6. the forms and the surface IOS from their processes
    t0 = time.time()
    fr, ir = forms_fut.result(), ios_fut.result()
    ex.shutdown()
    rec["seconds"]["waited_for_forms_and_ios"] = round(time.time() - t0, 1)
    forms, ios = fr.pop("forms"), ir.pop("ios")
    for r in (fr, ir):
        rec["parts"].update(r.pop("parts"))
        rec["seconds"].update(r.pop("seconds"))
        rec.update(r)
    # 8. the frame row of each target
    values = {"odds_logit": odds, **s4, **forms, **ios, **context, **pieces}
    names = model_names()
    missing = [n for n in names if n not in values]
    if missing:
        raise RuntimeError(f"inputs not built: {missing}")
    frame = pd.DataFrame({"match_id": target_ids})
    for n in names:
        v = np.asarray(values[n], dtype="float64")
        frame[f"in_{n}"] = v.astype("float32").astype("float64") if n in FLOAT32 else v
    frame = frame.merge(info, on="match_id", how="left")
    rec["seconds"]["total"] = round(time.time() - t_all, 1)
    return frame, rec
