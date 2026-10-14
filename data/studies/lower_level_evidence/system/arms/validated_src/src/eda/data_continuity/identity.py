"""Player identity across the splice: do players keep their history when their results start coming from TML?

Stage 0 gives a TML ATP player Sackmann's id when its ATP code was learned from matches both sources hold
(stage0_build.crosswalk); otherwise the code itself becomes the id (rule C61). A player whose earlier matches are only
in Sackmann's files, ITF and Futures above all (TML has no ITF files), therefore starts again under a new id once
TML is the only source. This counts them after the splice and tests the repair the merge-feasibility study proposed:
an exact name plus birth date, TML's player table against Sackmann's.

Writes data/studies/data_continuity/identity_splits.csv (one row per post-splice ATP-code player) and
identity_splits.json. Run: ./python.sh src/eda/data_continuity/identity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402
from src.eda.merge_feasibility import scan as S  # noqa: E402

TML_PLAYERS = K.ROOT / "data/raw/public_dump/tennis_my_life/ATP_Database.csv"
SACKMANN_PLAYERS = K.ROOT / "data/raw/public_dump/sackmann_archive/atp/atp_players.csv"


PLACEHOLDER_DATES = {"1970-01-01", "1900-01-01"}       # TML's ATP_Database uses 1970-01-01 for unknown


def ymd(s: pd.Series) -> pd.Series:
    out = pd.to_datetime(s.astype(str).str.strip(), format="%Y%m%d", errors="coerce").dt.strftime("%Y-%m-%d")
    return out.where(~out.isin(PLACEHOLDER_DATES))


def main() -> int:
    m, p = K.load_stage0()
    m["tdate"] = pd.to_datetime(m["tournament_date"], errors="coerce")
    j = p.merge(m[["match_id", "tdate", "source", "level"]], on="match_id")
    post = j[(j["tdate"] >= K.SPLICE) & j["source"].eq("tml")]
    codes = post[post["player_id"].str.startswith("atpcode:")]
    per = codes.groupby(["player_id", "player_name"]).agg(matches=("match_id", "nunique"),
                                                          levels=("level", lambda s: ";".join(sorted(set(s))))).reset_index()
    per["code"] = per["player_id"].str.split(":").str[1]
    per["key"] = per["player_name"].map(S.name_key)
    earlier = j[(j["tdate"] < K.SPLICE) & j["player_id"].str.startswith("atp:")][["player_id", "player_name"]].drop_duplicates()
    earlier["key"] = earlier["player_name"].map(S.name_key)
    by_name = earlier.groupby("key")["player_id"].agg(lambda s: ";".join(sorted(set(s))))
    per["earlier_ids_same_name"] = per["key"].map(by_name).fillna("")
    tml = pd.read_csv(TML_PLAYERS, dtype=str, keep_default_na=False)
    sk = pd.read_csv(SACKMANN_PLAYERS, dtype=str, keep_default_na=False)
    tml["dob"], sk["dob"] = ymd(tml["birthdate"]), ymd(sk["dob"])
    sk["key"] = (sk["name_first"] + " " + sk["name_last"]).map(S.name_key)
    per = per.merge(tml[["id", "dob"]].rename(columns={"id": "code"}), on="code", how="left")
    cand = per.merge(sk[["player_id", "key", "dob"]].rename(columns={"player_id": "sackmann_id"}), on=["key", "dob"],
                     how="left").dropna(subset=["sackmann_id"])
    n = cand.groupby("player_id")["sackmann_id"].nunique()
    one = cand[cand["player_id"].isin(n.index[n == 1])].drop_duplicates("player_id").set_index("player_id")["sackmann_id"]
    per["name_and_birth_date"] = per["player_id"].map(one).fillna("")
    per["in_tml_player_table"] = per["dob"].notna() | per["code"].isin(set(tml["id"]))
    per = per.drop(columns=["key"]).sort_values("matches", ascending=False)
    per.to_csv(K.OUT / "identity_splits.csv", index=False)
    split = per["earlier_ids_same_name"].ne("")
    K.write_json(K.OUT / "identity_splits.json", {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "post_splice_tml_player_rows": int(len(post)),
        "post_splice_player_ids_by_kind": post["player_id"].str.split(":").str[0].value_counts().to_dict(),
        "atp_code_players": int(len(per)), "their_matches": int(codes["match_id"].nunique()),
        "share_a_name_with_an_earlier_sackmann_id": int(split.sum()),
        "matches_of_those": int(per.loc[split, "matches"].sum()),
        "resolved_by_name_and_birth_date": int(per["name_and_birth_date"].ne("").sum()),
        "in_tml_player_table": int(per["in_tml_player_table"].sum()),
        "with_a_birth_date": int(per["dob"].notna().sum()),
        "tml_player_table": C_rel(TML_PLAYERS),
    })
    print(per.head(20).to_string())
    return 0


def C_rel(path: Path) -> str:
    return path.relative_to(K.ROOT).as_posix()


if __name__ == "__main__":
    sys.exit(main())
