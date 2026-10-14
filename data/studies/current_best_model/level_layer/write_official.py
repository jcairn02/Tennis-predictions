"""Writes official.json (the level layer's config in the current best model) from the study's tested SYS config, once.
Every setting is SYS's; the changes are listed in CHANGED and recorded in the file. Refuses to overwrite a different
official.json: a new config is a new decision. Run from the repository root: ./python.sh <this file>"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
HERE = ROOT / "data" / "studies" / "current_best_model" / "level_layer"
SYS = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "arms" / "configs" / "SYS.json"
STAGE1 = (ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "instance" /
          "chain_outputs" / "stage1_baselines_summary.json")
EXPECT = {"params_sha256": "4c559abd356f7c9f0f53c958c5d8293ae55d0cdfa62c4e9da689c94c91a801fb",
          "classes_sha256": "58e7862273bfaf8bfbe6283c72b54e80f219ff36c0f83df795076d52ae940c26",
          "strength": "4fa9a573e7d0fbc34ab95f5f6c5efc97b835471a0f676bb5f14c182321c34d0d"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    s = json.loads(SYS.read_text(encoding="utf-8"))
    assert s["params_sha256"] == EXPECT["params_sha256"] == sha(Path(s["params"]))
    assert s["classes_sha256"] == EXPECT["classes_sha256"] == sha(Path(s["classes"]))
    assert s["strength"]["sha256"] == EXPECT["strength"] == sha(Path(s["strength"]["path"]))
    assert sha(Path(s["pins"]["stageB_adjperf"]["path"])) == s["pins"]["stageB_adjperf"]["sha256"]
    k = {c["tour"]: {x: float(c[x]) for x in ("k0", "offset", "shape")}
         for c in json.loads(STAGE1.read_text(encoding="utf-8"))["chosen"] if c["rule"] == "ret"}
    cfg = {k_: v for k_, v in s.items() if k_ not in ("what", "written_at")}
    cfg.update({
        "name": "official",
        "record_dir": None,                              # each build records into its own tree (layer_config.resolve)
        "families": {**s["families"], "ios_points_short": False},
        "params_season_ceiling": "last_fitted",
        "strength_k": k,
        "strength_policy": "per build: the plain pre-match Elo on the build's own Stage 0 with strength_k "
                           "(src/eda/current_best_model/layer_config.py --resolve); the strength named here is the "
                           "frozen one, which the build's must equal on the reference's matches",
        "what": "the level layer of the current best model, men (docs/decisions/2026-10-10-level-evidence-layer.md): "
                "the level-evidence study's SYS, every setting as tested",
        "from": {"config": str(SYS), "sha256": sha(SYS), "stage1_k_from": str(STAGE1), "stage1_k_sha256": sha(STAGE1)},
        "changed_from_sys": {
            "name": "SYS -> official",
            "record_dir": "SYS's study folder -> null here; each build's own tree",
            "families.ios_points_short": "true -> false: the input was dropped on 9 Oct 2026 (the IOS part still runs "
                                         "for the 'ios' family, whose pooled solves lane 3's mapping check reads)",
            "params_season_ceiling": "absent -> last_fitted: seasons after the last fitted one read its parameters",
            "strength": "the frozen strength_elo.parquet, replaced in each build by the build's own plain Elo",
            "strength_k": "added: the frozen reference's Stage 1 K (retirements counted), which the strength uses"},
    })
    out = HERE / "official.json"
    text = json.dumps(cfg, indent=1) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") != text:
        raise SystemExit(f"{out} exists with another content: a new config is a new decision")
    HERE.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    (HERE / "official.sha256").write_text(f"{sha(out)} *official.json\n", encoding="utf-8")
    sys.path.insert(0, str(ROOT))
    from src.eda.lower_level_evidence import level_layer_ios as LI
    LI.validate_config(dict(cfg), str(out))
    print(out, sha(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
