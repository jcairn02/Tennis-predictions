# Pre-registration, addition 7b: NEW_SYS_BOTH as built (option c), before its first reading

Written by the lead on 10 October 2026, 15:37 UTC. The file's own SHA-256 is in `preregistration_addition_7b.sha256`.

**Timing.** NEW_SYS_BOTH became READY at 15:34:16 UTC. At writing, 6 of its 32 fits existed and it had no reading. The only rule-test file was `rule_test_before_NEW_SYS_BOTH.json`, the interim record kept before this arm existed.

## What NEW_SYS_BOTH is

Role C1 built it as addition 7, section 1, specifies (option c).

| Item | SHA-256 | Notes |
|---|---|---|
| Strength file `arms/strength/NEW_C0_now_elo_optC.parquet` | 1a9c211aa9382758bb5e98d945d6670816487bcc3bba913b47bc50dc5bd56324 | Reference matches keep the reference's strength_elo. The 298,008 new matches take NEW_ASIS's plain Elo, re-centred by tour and season. No missing values |
| `src/eda/lower_level_evidence/system_arms.py` | d4beb8a3cfd15e05b129a758893d0246ae6376b8aec13863ab02384d19920036 | Replaces addition 7's 793a0fa1. The only change: NEW_STRENGTH points at the option-(c) file above |
| Frame | cf93c0ef… | |
| Config | a5a6fefe… | |

The NEW-arm gates pass: identifiers, untouched inputs, lane-0 check, constants and G5. The debut_season difference is waived under addition 7.

The option-(a) build is kept, unread, at `arms/NEW_SYS_BOTH_optA_unread/`. It is never scored.

## How it is read

Its first reading is its reading of record (addition 6, section 2). The rule-test verdict (addition 4) is NEW_SYS_BOTH against SYS_BOTH, a harm check for each tour:
* dev, for C0_now's additions of 2018–2024;
* the holdout, for those of 2025–2026.
