"""The unpriced-leads study's long list (synthesis 1 and 2, 13 Oct 2026): every idea of the four round-1 memos, with what
became of it (a group member, built and screened but not chosen, a registered download protocol, prospective only, a
test-design item, or not built and why) and, where it was built, its discovery reading on seasons <= 2024 (both tours,
pooled z of the raw A - B and of its orthogonal part, from the builders' summary files). The dispositions are the lead's
judgements, written after the discovery readings (process log, Synthesis 2).

Writes data/studies/unpriced_leads/longlist.csv.
Run: ./python.sh src/eda/unpriced_leads/longlist.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
TEAM = ROOT / "docs" / "studies" / "unpriced_leads" / "team"
CAND = ROOT / "data" / "studies" / "unpriced_leads" / "candidates"
POOL = ROOT / "data" / "studies" / "unpriced_leads" / "pool_scan" / "summary.csv"
OUT = ROOT / "data" / "studies" / "unpriced_leads" / "longlist.csv"

# id -> (disposition, built column as "family:candidate" or "", note)
D = {
    # point structure (B2)
    "PS01": ("built; folded into G1 through close-set luck (r 0.83)", "luck:PS01_tb", "near 0 in 2023-24"),
    "PS02": ("built; not chosen", "luck:PS02_elogap", "the close's loading is large and the outcome takes back little (beta ~ -0.2 c); orthogonal part ~0"),
    "PS03": ("G1 member (net break-point luck)", "luck:PS03_net", "pieces separately are mirror pairs; chance creation reads against its sign"),
    "PS04": ("G1 member (flattery); run luck not chosen", "luck:PS04_flat", "run luck: c < 0 and the line moves against it before the close"),
    "PS05": ("registered protocol (partial data: ATP non-Slam per-point speeds need the P9 decryption)", "", "appendix: partial-information leads"),
    "PS06": ("G1 member (close-set luck)", "luck:PS06_close", "deciding-set luck weaker (z -1.65)"),
    "PS07": ("not built", "", "partial data (ranking points table); lower rank"),
    "PS08": ("not built", "", "needs the clock; I-009 failed a skill gate"),
    "PS09": ("registered protocol (WTA advanced statistics, 2021-26; three discovery seasons)", "", "appendix"),
    "PS10": ("not built", "", "needs the clock and a reliability gate similar splits failed"),
    "PS11": ("built; not chosen", "luck:PS11_vis", "weak"),
    "PS12": ("not built", "", "long tail"), "PS13": ("not built", "", "long tail"), "PS14": ("not built", "", "long tail"),
    "PS15": ("not built", "", "too thin (no tracked 2025-26)"), "PS16": ("not built", "", "two Slams only"),
    "PS17": ("not built", "", "medium-high overlap with form inputs"), "PS18": ("not new", "", "a contrast of iosO/iosD"),
    "PS19": ("not built", "", "long tail"), "PS20": ("not built", "", "long tail"),
    # rhythm and body (B1)
    "RB01": ("G5 member (doubles at other events, days -7..-1)", "rhythm:rb01_d7_else", "doubles at the same event read nothing"),
    "RB02": ("built; not chosen", "rhythm:rb02_dblrust", "null"),
    "RB03": ("G5 member (rest under 20 h)", "rhythm:rb03_lt20", "continuous shortness null"),
    "RB04": ("built; not chosen", "rhythm:rb04_gap", "+1.50, men only"),
    "RB05": ("built; not chosen", "rhythm:rb05_ratio", "priced: the line moves against it (z -10.2)"),
    "RB06": ("built; not chosen", "rhythm:rb06_late", "null"),
    "RB07": ("registered protocol (G3 extension; weather download)", "", "Burke et al. 2023: the previous match's heat is priced"),
    "RB08": ("registered protocol (weather download)", "", "G3 extension, secondary"),
    "RB09": ("not built", "", "near U-179 (physio: retirement risk, not results)"),
    "RB10": ("built; not chosen", "rhythm:rb10_drift", "signs flip by tour and era"),
    "RB11": ("not built", "", "partial (careers before 2010)"), "RB12": ("not built", "", "near U-045"),
    "RB13": ("built; not chosen", "rhythm:rb13_qcost", "it is the qualifier tag (r 0.998), spanned by the inputs"),
    "RB14": ("G5 member (the bye seed's cold start)", "rhythm:rb14_cold28", "the signal inside U-138; concentrated in 2017-19"),
    "RB15": ("built; not chosen", "rhythm:rb15_r90", "signs opposite by tour, no mechanism"),
    "RB16": ("registered protocol (withdrawals: Wikipedia download)", "", "rare: bundle only"),
    "RB17": ("not built", "", "priors negative (B-SWITCH)"), "RB18": ("registered protocol (G3 extension; altitude)", "", ""),
    "RB19": ("not built", "", "travel closed by the literature and the pool (U-151)"),
    "RB20": ("built; not chosen", "rhythm:rb20_excess", "priced: the line moves against it (z -15.5)"),
    "RB21": ("not built", "", "two Slams only"), "RB22": ("= PS05", "", ""),
    "RB23": ("built; not chosen", "rhythm:rb23_offseason", "null"),
    "RB24": ("not built", "", "partial"), "RB25": ("not built", "", "partial"), "RB26": ("not built", "", "partial"),
    # market (B3)
    "MP-01": ("built; not chosen", "market:mp01_lop_move", "the totals' late move +2.3 but -0.4 beyond the model; +1.8 with the curvature base"),
    "MP-02": ("built; not chosen", "market:mp02_bol", "no continuation at either book; fresh/stale split kept as a test-design note"),
    "MP-03": ("not built", "", "needs the line history"),
    "MP-04": ("registered protocol (G3 extension; wind at the scheduled hour, indoor placebo)", "", ""),
    "MP-05": ("registered protocol (G3 extension; heat x age)", "", "with RB07"),
    "MP-06": ("registered protocol (G3 extension; altitude x serve gap)", "", "with RB18"),
    "MP-07": ("not built", "", "needs the clock; the related cliffs and points to defend were null"),
    "MP-08": ("built; not chosen", "market:mp08_seed", "null"),
    "MP-09": ("built; not chosen", "market:mp09_defend", "null"),
    "MP-10": ("built; not chosen", "market:mp10_rec", "fails its reliability gate (split-half -0.04); the line chases it (+8.8)"),
    "MP-11": ("= RB03", "", ""), "MP-12": ("test design (freshness split in the registration)", "", ""),
    "MP-13": ("prospective only (2025-26 data; register now, read on matches after the registration date)", "", "appendix"),
    "MP-14": ("= the pool's B-VENUE (G3)", "", ""), "MP-15": ("= RB01", "", ""), "MP-16": ("= RB13", "", ""),
    "MP-17": ("= RB16", "", ""), "MP-18": ("not built", "", "market structure with a 2026 break"),
    "MP-19": ("not built", "", "the clientele gate failed; popularity weak in the literature"),
    "MP-20": ("not built", "", "partial"), "MP-21": ("not built", "", "download"),
    "MP-22": ("built; not chosen", "rhythm:mp22_slam_r1", "null"), "MP-23": ("not built", "", "long tail"),
    "MP-24": ("test design (retirement settlement)", "", ""), "MP-25": ("test design (stale close split)", "", ""),
    "MP-26": ("not built", "", "2025-26 only"), "MP-27": ("not available", "", ""), "MP-28": ("not available", "", "no table of balls"),
    # researcher (R1)
    "RS01": ("= G1 (the luck builder's family)", "", ""), "RS02": ("= G1", "", ""), "RS03": ("= G1", "", ""),
    "RS04": ("= G1 (deciding-set luck, weaker)", "", ""),
    "RS05": ("built by the lead; not chosen", "extras:rs05_spike", "it is sets_14d again (R^2 0.61; orthogonal -1.09), opposite to the researcher's sign"),
    "RS06": ("pool (U-144/U-296), screened by S1", "", "odometer x age: not shortlisted"),
    "RS07": ("= RB03", "", ""), "RS08": ("= RB01", "", ""),
    "RS09": ("built by the lead; not chosen", "extras:rs09_R", "it is the status axis (with rank > 50 jointly: -0.01)"),
    "RS10": ("not built", "", "a candidate extension of G4 (own translation ratio); persistence untested"),
    "RS11": ("= MP-08/09 (null)", "", ""), "RS12": ("= RB07", "", ""),
    "RS13": ("registered protocol (G3 extension; edition pace from Court Vision bounces)", "", ""),
    "RS14": ("not built", "", "partial (speed)"), "RS15": ("not built", "", "volatility not a trait (pool reliability 0.05)"),
    "RS16": ("test design (settlement)", "", ""), "RS17": ("= RB16", "", ""), "RS18": ("= RB13", "", ""),
    "RS19": ("pool (B-MOTIV): G2 is its post-Slam member", "", ""), "RS20": ("not built", "", "long tail"),
    "RS21": ("not built", "", "partial"), "RS22": ("not built", "", "not recommended by the literature"),
    "RS23": ("= RB18", "", ""), "RS24": ("= MP-04", "", ""), "RS25": ("not available", "", ""),
    "RS26": ("not available", "", ""), "RS27": ("not available", "", ""), "RS28": ("not built", "", "partial (tracking)"),
    "RS29": ("not built", "", "pressure traits closed"), "RS30": ("not built", "", "market-internal"),
}


def readings() -> pd.DataFrame:
    rows = []
    for fam in ("luck", "market", "rhythm", "extras"):
        s = pd.read_csv(CAND / fam / "summary.csv")
        if "base" in s.columns:
            s = s[s["base"].astype(str).isin(["L", "odds_input", "odds input", "close"]) | s["base"].isna()]
        s = s[s["tour"] == "both"]
        for _, r in s.iterrows():
            rows.append({"key": f"{fam}:{r['name']}", "z_pool": r["z_pool"], "eras_same_sign": r.get("eras_same_sign")})
    return pd.DataFrame(rows).drop_duplicates("key").set_index("key")


def main() -> int:
    frames = []
    for role in ("rhythm_body", "point_structure", "market_practitioner", "researcher"):
        d = pd.read_csv(TEAM / f"{role}_ideas.csv")
        d.insert(0, "source", role)
        frames.append(d)
    L = pd.concat(frames, ignore_index=True)
    R = readings()
    disp, col, note, zr, zo, er = [], [], [], [], [], []
    for i in L["id"].astype(str):
        dd, cc, nn = D.get(i, ("(not classified)", "", ""))
        disp.append(dd)
        col.append(cc)
        note.append(nn)
        if cc and cc in R.index:
            zr.append(float(R.loc[cc, "z_pool"]))
            er.append(R.loc[cc, "eras_same_sign"])
            zo.append(float(R.loc[cc + "__orth", "z_pool"]) if cc + "__orth" in R.index else np.nan)
        else:
            zr.append(np.nan)
            zo.append(np.nan)
            er.append(np.nan)
    L["disposition"] = disp
    L["built_column"] = col
    L["z_raw_2013_24_both"] = zr
    L["z_orth_2013_24_both"] = zo
    L["eras_same_sign"] = er
    L["lead_note"] = note
    keep = ["source", "id", "name", "area", "data_status", "model_overlap", "exposed_2025_26", "your_rank",
            "disposition", "built_column", "z_raw_2013_24_both", "z_orth_2013_24_both", "eras_same_sign", "lead_note",
            "definition", "mechanism"]
    L[keep].to_csv(OUT, index=False)
    print(L["disposition"].str.split(r" \(|;").str[0].value_counts().to_string())
    print("unclassified:", int((L["disposition"] == "(not classified)").sum()), "of", len(L))
    return 0


if __name__ == "__main__":
    sys.exit(main())
