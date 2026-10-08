"""Universe rows: match context and venue. Field order as spec_market."""
FAMILY = "context"
Z = "[z: + = declared direction]"
G = "[mLL: + = feature or arm better; tie = interval spans 0]"
ROWS = [
    ("tour", "match", "0 men / 1 women", "context", "model frame (Stage 0)", "m__tour; ctx__tour", "IM", "SC",
     "store:m__tour", "context inputs of every model since stage 4", "none", "yes", "", "high: incumbent"),
    ("surface", "match", "0 hard, 1 clay, 2 grass, 3 carpet", "context", "Stage 0", "m__surface; ctx__surface", "IM", "SC",
     "store:m__surface", G + " one model vs a model per surface -0.28 [-0.77, +0.21] tie (surface_ios)", "none", "yes", "",
     "high: incumbent"),
    ("level", "match", "0 Slam, 1 Finals, 2 1000, 3 500, 4 250", "context", "Stage 0", "m__level; ctx__level", "IM", "SC",
     "store:m__level", "context input", "none", "yes", "", "high: incumbent"),
    ("indoor (the model's flag)", "match", "1 indoor / 0 outdoor from Stage 0", "context", "Stage 0",
     "m__indoor; ctx__indoor", "IM", "SC", "store:m__indoor", "context input", "none", "yes",
     "men only: women 0% in m__indoor and in the store's ctx__indoor", "high: incumbent (but fill the women's gap)"),
    ("indoor, both tours (tennis-data Court)", "match", "Stage 0's flag, else tennis-data.co.uk's Court field, else the "
     "event's majority", "context", "f09_venue.match_indoor (Court via stage1_odds td_file + td_row position; "
     "f25_switch's join)", "fp__f09_venue__f09_indoor", "BN", "SC", "store:fp__f09_venue__f09_indoor",
     "99.2% agreement with Stage 0 on 27,289 men's matches (round 0); used by B-SWITCH and I-073", "none", "no",
     "the indoor flag of both tours (m__indoor is men only)", "medium: fills women's missing indoor"),
    ("best of", "match", "scheduled best of (men's Slam main draws 5)", "context", "Stage 0", "m__best_of; ctx__best_of",
     "IM", "SC", "store:m__best_of", "[mLL] Elo x best of five onE 0.298 [0.182, 0.414], onM 0.114 tie; TabPFN shuffle "
     "share 0.00 (tabpfn_thinking)", "none", "yes", "", "high: incumbent (cheap)"),
    ("round", "match", "Stage 0 round_order (Q1 = 1 ... RR = 10, R128 = 11 ... F = 17)", "context", "Stage 0",
     "m__round; ctx__round", "IM", "SC", "store:m__round", "context input; [z: + = declared direction] B-FLB's later-round slope block +0.94 (Tier D)",
     "none", "yes", "", "high: incumbent"),
    ("draw size", "match", "the event's draw size", "context", "Stage 0: draw_size", "ctx__draw_size", "BN", "SC",
     "store:ctx__draw_size", "used to find the first main-draw round (B-FLB)", "none", "no", "", "low"),
    ("week of the year", "calendar", "ISO week of the event", "context", "Stage 0", "ctx__week", "BN", "SC",
     "store:ctx__week", "never tested alone; B-MOTIV may have changed with the 2023 Masters calendar", "none", "no", "",
     "low"),
    ("month", "calendar", "month of the event", "context", "Stage 0", "ctx__month", "BN", "SC", "store:ctx__month",
     "I-061 uses 1[month >= 9]", "none", "no", "", "low"),
    ("Slam proximity", "calendar", "days to the next Grand Slam main draw of the tour; 1[within 8 days]", "context",
     "f19_motiv.prepare_motiv (nslam_days)", "fp__f19_motiv__nslam_days", "BN", "SC", "store:fp__f19_motiv__nslam_days",
     Z + " the I-089 member of B-MOTIV (+2.27; z1 +2.39, z2 +0.49)", "B", "no",
     "a calendar fact; the planned 1[within 8 days] is nslam_days <= 8; computed from the Slams present in the data, "
     "so missing from Wimbledon 2026 on (563 rows: the US Open 2026 is not in the frozen frame); live use needs the "
     "published calendar", "medium: raw block of B-MOTIV"),
    ("venue pace (leak-proof)", "venue", "v_e: the venue's logit-scale ace excess over its earlier editions and this "
     "edition's earlier days (2-year half-life, shrunk 2,000 points)", "context", "f09_venue.venue_state (f09_ve)",
     "fp__f09_venue__f09_ve", "BN", "PP", "store:fp__f09_venue__f09_ve",
     Z + " B-VENUE (v_e x dO_ace) +2.50 model / +2.72 price (z1 +2.13, z2 +1.32); eligible on the price lens (q 0.075)",
     "A", "no", "a field statistic: leak-proof clock, probe passed (five cuts); venue = tour x name x surface",
     "high: symmetric context beside the ace ratings"),
    ("indoor serve and return deviations", "venue", "per-player indoor serve (G) and return (H) deviations from the "
     "surface IOS", "pair", "f09_venue.indoor_state", "fp__f09_venue__f09_G_a/_b; fp__f09_venue__f09_H_a/_b", "BN", "PP",
     "store:fp__f09_venue__f09_G_ab", "I-073 dropped by its gate (split-season carry-over <= 0.124 < 0.15)", "none", "no",
     "", "exclude: failed its reliability gate"),
    ("attention and crowding", "venue", "attention index (level, round depth, star power, other matches that day)",
     "context", "f17_info (crowd_n)", "fp__f17_info__crowd_n", "BN", "SC", "store:fp__f17_info__crowd_n",
     Z + " inside B-INFO's I-080 (block +0.30)", "none", "no", "", "low"),
    ("scheduled start time of day", "venue", "start_utc in the match-timing link files, to local time", "context",
     "match_timing/links/*: start_utc; srcc_tz.py, flashscore_tz.py", "", "BD", "SC", "=M 0.99 / W 0.75 | 1.00 | not measured",
     "never tested (session, heat, night)", "none", "no", "some starts are scheduled, not actual", "low"),
    ("altitude, weather, balls, court-speed index", "venue", "external conditions", "context",
     "not held (gazetteer, weather archive, ball brand, CPI)", "", "NN", "SC", "=0 | 0 | 0",
     "PF register C01-C07, untested", "none", "no", "", "low: venue pace already proxies speed"),
    ("clock width (exact day vs window)", "data quality", "1 when the match day is exact", "context",
     "match_timing/timing (pre-rebuild): exact", "", "BN", "SC", "=1.00 | 1.00 | 1.00",
     "a data-quality flag (INFO-1's blind spot collapses for women from 2020)", "none", "no",
     "exact-day share M 9% / W 20% (2013-21), M 17% / W 86% (2022-24)", "exclude: not a skill"),
]
