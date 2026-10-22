"""Addendum 1 to the lock-in (serve/return-leads study): the cleaner versions' frozen scales, their seen readings as
registered, and the power of the unseen check for each.

    C1  the luck score: the mean of oriented save luck and hold luck (unpriced leads' build_luck.py, PS03_save and
        PS03_hold, 91-day half-life), each over its frozen RMS, the mean over its frozen RMS. Oriented +: the player
        luckier on break points and holds than his serve points imply is expected to lose to the close
    C2  the serve/return balance: (O_spw - D_spw)_A - (O_spw - D_spw)_B, surface-effective IOS on serve points won,
        over its frozen RMS. Oriented +: the serve-heavy player (at equal overall strength) is expected to lose to it
    C3  the second-serve speed form spd2_L (the speed builder's spd2_L_B: the serve-speed stage's 28-day builder run
        on second serves), over its frozen RMS of non-zero values. Oriented +: a man whose second serve sped up is
        expected to beat the close
Scales: the men's matches with tournament dates 1 Jan 2025 - 28 Jul 2026, as the lock-in's (outcome-free).
Readings: readings.read (seen matches only). Power: timeline.py's calendar and noncentral-t power, one look at
one-sided 0.05, for the 2025-26 strength in full, 0.45 of it, and the 2013-24 strength.

Writes data/studies/serve_return_leads/addendum_scales.json, addendum_seen.csv, addendum_power.csv.
Run: ./python.sh src/eda/serve_return_leads/addendum_scales.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.serve_return_leads import decompose as D  # noqa: E402
from src.eda.serve_return_leads import readings as R  # noqa: E402
from src.eda.serve_return_leads import timeline as T  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

SPEED = C.OUT / "speed" / "builder_columns.parquet"


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x ** 2)))


def raw_values(f: pd.DataFrame) -> dict:
    c, _ = D.candidates(f)
    sp = pd.read_parquet(SPEED, columns=["match_id", "spd2_L_B"]).astype({"match_id": str})
    sp = sp.drop_duplicates("match_id").set_index("match_id")["spd2_L_B"].reindex(f["match_id"]).to_numpy(float)
    return {"save": -np.nan_to_num(c["PS03_save"]), "hold": -np.nan_to_num(c["PS03_hold"]),
            "ST": -np.nan_to_num(c["ST"]), "spd2": np.nan_to_num(sp)}


def scales(f: pd.DataFrame, v: dict) -> dict:
    w = ((f["tournament_date"] >= C.SCALE_WINDOW[0]) & (f["tournament_date"] < C.SCALE_WINDOW[1])).to_numpy()
    sc = {"window": [str(C.SCALE_WINDOW[0].date()), "2026-07-28"], "matches": int(w.sum()),
          "save": _rms(v["save"][w]), "hold": _rms(v["hold"][w]), "ST": _rms(v["ST"][w]),
          "spd2": _rms(v["spd2"][w][v["spd2"][w] != 0])}
    luck = (v["save"] / sc["save"] + v["hold"] / sc["hold"]) / 2
    sc["C1"] = _rms(luck[w])
    return sc


def scores(v: dict, sc: dict) -> dict:
    luck = (v["save"] / sc["save"] + v["hold"] / sc["hold"]) / 2
    return {"C1": luck / sc["C1"], "C2": v["ST"] / sc["ST"], "C3": v["spd2"] / sc["spd2"]}


def main() -> int:
    f = R.seen_frame("atp")
    v = raw_values(f)
    sc = scales(f, v)
    C.write_json(C.OUT / "addendum_scales.json", sc)
    s = scores(v, sc)
    seen = pd.concat([R.read(f, s[k], k, +1, forms=("raw",)) for k in ("C1", "C2", "C3")], ignore_index=True)
    seen.to_csv(C.OUT / "addendum_seen.csv", index=False)
    cal, _ = T.unseen_calendar()
    blk = H.blocks(cal["d"].to_numpy(), 28)
    rows = []
    for k in ("C1", "C2", "C3"):
        r = seen[(seen["candidate"] == k) & (seen["base"] == "L")].set_index("window")
        b, se, n = r.loc["2025-26", "beta"], r.loc["2025-26", "se"], r.loc["2025-26", "n"]
        b_old = r.loc["2013-24", "beta"]
        for date in ("2027-01-31", "2027-05-31", "2027-08-31", "2027-12-31"):
            m = (cal["d"] <= pd.Timestamp(date)).to_numpy()
            N, G = int(m.sum()), int(len(np.unique(blk[m])))
            se_n = se * np.sqrt(n / N)
            rows.append({"score": k, "date": date, "unseen_men": N, "blocks": G,
                         "full": T.power(b / se_n, G, 0.05), "0.45": T.power(0.45 * b / se_n, G, 0.05),
                         "2013-24 strength": T.power(b_old / se_n, G, 0.05)})
    pw = pd.DataFrame(rows)
    pw.to_csv(C.OUT / "addendum_power.csv", index=False)
    pd.set_option("display.width", 250)
    print(sc)
    print(seen.pivot_table(index=["candidate", "base"], columns="window", values="z")
          [["2013-16", "2017-19", "2020-22", "2023-24", "2013-24", "2020-24", "2025-26"]].round(2).to_string())
    print(pw.round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
