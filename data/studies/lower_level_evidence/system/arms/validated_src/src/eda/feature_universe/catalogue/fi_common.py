"""Shared helpers and the screen's numbers for the feature-interactions rows (read from hypotheses/screen_results.csv,
descriptive_results.csv and exploratory_binj_members.csv on 7 Oct; z oriented: + = the member's declared direction;
blocks tested '-' are sign-flipped so that + is their declared direction too)."""
MOD = "src/eda/feature_interactions/features/"
# hid: (z1, z2, joint model, joint price) oriented; Wald rows: ("wald", k, p model, p price)
SCREEN = {
    "I-008": (1.07, -0.41, 0.67, 0.29), "B2": (-0.32, -1.08, -0.86, -0.59), "B7": (-0.97, 2.85, 0.76, 0.74),
    "B-AGE": (1.32, -0.01, 1.09, 1.24), "B-CLUTCH": (1.48, -0.72, 0.83, 0.84), "B-VENUE": (2.13, 1.32, 2.50, 2.72),
    "I-036": (-1.36, -0.92, -1.65, -1.37), "I-084": (-2.38, -1.82, -2.98, -3.12), "I-049": (-0.28, 0.36, -0.04, -0.17),
    "B-FLB": (1.37, -0.37, 0.94, 0.85), "I-042": (-0.34, -0.65, -0.64, -0.83), "I-082": (-0.10, 0.37, 0.12, 0.05),
    "B6": (1.33, 0.03, 1.13, 1.13), "B-ANCHOR": (-1.40, -0.31, -1.34, -1.39), "B-REPUTE": (-1.28, 1.78, -0.09, -0.60),
    "LIT-2": (0.91, -0.43, 0.53, 0.62), "B-INFO": (-0.40, 1.14, 0.30, 0.13), "B-OVERREACT": (1.64, 1.38, 2.13, 2.27),
    "B-MOTIV": (2.39, 0.49, 2.27, 2.31), "I-053": (1.71, -0.26, 1.29, 1.39), "B-LOAD": (0.81, -0.08, 0.63, 0.61),
    "B-PREV": (0.61, -1.05, -0.07, -0.26), "B9a": (0.10, 2.53, 1.48, 1.15), "B9b": (-1.19, 0.33, -0.81, -0.86),
    "B10": (0.22, 0.33, 0.37, 0.32), "B11": (1.35, 1.54, 1.97, 1.78), "B-INJ": (3.51, 1.93, 3.99, 3.92),
    "B-STATE": (0.87, 1.93, 1.79, 1.52),
    "B-LEVER": ("wald", 3, 0.21, 0.24), "B3": ("wald", 2, 0.30, 0.11), "B-RECAL": ("wald", 2, 0.60, 0.88),
    "B-SWITCH": ("wald", 4, 0.31, 0.27), "B-HOME": ("wald", 2, 0.54, 0.50),
}
NOVELTY = {"B-LEVER": 0.87, "I-008": 0.02, "B2": 0.89, "B3": 0.73, "B7": 0.11, "B-AGE": 0.64, "B-CLUTCH": 0.12,
           "B-VENUE": 0.04, "I-036": 0.21, "I-084": 0.34, "I-049": 0.59, "B-FLB": 0.67, "I-042": 0.66, "I-082": 0.38,
           "B6": 0.07, "B-ANCHOR": 0.16, "B-RECAL": 0.42, "B-REPUTE": 0.33, "LIT-2": 0.70, "B-INFO": 0.09,
           "B-OVERREACT": 0.16, "B-MOTIV": 0.05, "I-053": 0.77, "B-LOAD": 0.77, "B-PREV": 0.07, "B9a": 0.24,
           "B9b": 0.28, "B10": 0.23, "B11": 0.48, "B-SWITCH": 0.25, "B-INJ": 0.10, "B-HOME": 0.12, "B-STATE": 0.67}


def ev(hid: str) -> str:
    s = SCREEN[hid]
    if s[0] == "wald":
        return (f"[Wald {s[1]} df, two-sided] screen joint p {s[2]:.2f} model / {s[3]:.2f} price, 2014-24 "
                "(feature_interactions)")
    return (f"[z: + = declared direction] screen joint {s[2]:+.2f} model / {s[3]:+.2f} price (z1 {s[0]:+.2f}, "
            f"z2 {s[1]:+.2f}), 2014-24 (feature_interactions)")


def inside(hid: str) -> str:
    return "inside " + hid + "; not screened alone. Block: " + ev(hid)


def nov(hid: str) -> str:
    return f"novelty R2 on the 58 inputs {NOVELTY[hid]:.2f}" if hid in NOVELTY else ""


def block(hid, title, defn, kind, module, store, timing, tier, caveat, priority, seen="no", cov=None):
    cav = "; ".join(x for x in (nov(hid), caveat) if x)
    key = cov or "store:" + store.split(";")[0].strip()
    return (f"{hid} (block): {title}", hid, defn, kind, MOD + module + ".py", store, "BN", timing, key, ev(hid), tier,
            seen, cav, priority)


def member(mid, blk, title, defn, kind, module, store, timing, tier, caveat, priority, evidence=None, seen="no",
           status="BN", cov=None):
    key = cov or ("store:" + store.split(";")[0].strip() if store else "store:fi__" + blk + "__x")
    return (f"{mid}: {title}", blk, defn, kind, MOD + module + ".py", store, status, timing, key,
            evidence or inside(blk), tier, seen, caveat, priority)
