# How a hypothesis is built (for the EDA analysts)

6 October 2026. Every hypothesis in the frozen table is built the same way, so that one screen judges all of them on the same matches. Building reads **no results** (`a_won`) and no season after 2024. The screen (`src/eda/feature_interactions/screen.py`) is run once, by the orchestrator, after M1.

## Shared inputs

| Helper | What it gives |
|---|---|
| `panel.panel(max_season=2024)` | one row per model-frame match (2013–2024, debut seasons included), each player's pre-match values side by side as `<name>_a`, `<name>_b` (surface IOS O/D/E/F for spw, ace, df, first_in, first_won, second_won, hold, bp_saved; Elo R/D/N/NS and surface counters; Stage 3 serve/return ratings with sd and points; TTT offset parts; the two-week profile and load per player; rank, points, seed, entry, age, height, hand, country), the match context, odds fields (avg, ps, max, b365), the clock's es/lf, and the 58 inputs as `in_<name>`. Side A = Stage 0's `player_a_id` |
| `history.long_table()` | every player's own matches at every level, 2010–2026, one row per (match, player), ordered by the player's own sequence (`k`), with past-match facts (level, surface, indoor, sets, games, tiebreaks, minutes, retirement, walkover, box score) and `rest_days` (best-estimate days). `prior(L, col, n)` is the n-th previous match; `at_model(L, col, match_ids)` reads a per-row value for side A and B at model matches |
| `panel.check_swap(f, P, kind)` | f(P) must change sign (kind `"diff"`) or stay equal (`"context"`) when A and B swap |

## The pattern

1. **Per-player values first.** Compute each player's pre-match quantity from strictly earlier information (the panel's columns, or `history` rows shifted to strictly earlier matches) and put it in the panel as `<name>_a`, `<name>_b`. Anything that combines different players' results (a field statistic, a venue estimate from other matches, a jointly solved rating) uses the leak-proof clock (a result counts from the day after its latest finish, `lf + 1`; a match reads the state as of its earliest start, `es`) and must pass `src/eda/match_timing/probe.py`.
2. **Then the combination.** A function of the panel that uses only `_a`/`_b` columns and match context returns the primary column x (antisymmetric). `check_swap(x_fn, P, "diff")` must pass. Modulators (symmetric) are centred on the 2014–2021 rows before products are formed (no results involved).
3. **Controls.** The marginality set of the hypothesis's type (critique M2, written in its master-list row), the one to three nearest existing inputs (by correlation on 2014–2021 rows, chosen without results) and missingness controls (miss_A − miss_B; the symmetric missing indicator × η, which the batch forms). Every control is antisymmetric.
4. **The TabPFN deployment.** The columns the arm would add (diff, context or pair kind), registered through `registry.register`.
5. **Diagnostics, result-free, written beside the builder:** coverage per tour in 2014–2021 and 2022–2024 (and the 2025–2026 row count only), the swap test, the novelty R² of x on the 58 inputs (2014–2021 rows), its correlation with the three nearest inputs, its distribution.

## The module

One module per family, `src/eda/feature_interactions/features/f<NN>_<slug>.py`, exposing

```python
HYPOTHESES = [
    {"hid": "H-001", "master": "I-001", "kind": "S", "sign": "+", "weight": 1.0, "trait": "none",
     "deployment": "diff", "prepare": prepare_h001, "combine": combine_h001},
]

def prepare_h001(P, L) -> dict:
    """New per-player columns, aligned to P's rows: {"<name>_a": array, "<name>_b": array, ...} (may be empty)."""

def combine_h001(P) -> dict:
    """Only P's `_a`/`_b` columns and match context (no history, no file reads): the swap test runs on this."""
    return {"x": ..., "controls": ..., "control_names": [...],          # arrays aligned to P's rows
            "tabpfn": {"col_name": (array, "diff" | "context" | "pair", partner_or_None)}}
```

**What `combine` may return** (the batch, `screen_batch.py`, forms the rest per base, η being the current best's out-of-sample log-odds or the price):

| Key | Meaning |
|---|---|
| `x` | the primary column, antisymmetric, shape (n,). A **signed-sum block** returns the sum of its members, each standardised on the 2014–2021 rows (result-free) and multiplied by its declared sign. A **Wald block** (a block with a two-sided member, math audit) returns shape (n, k) and the hypothesis row carries `"wald": True` |
| `x_times_eta: True` | `x` is a symmetric modulator s (centred on 2014–2021 rows); the batch tests s·η. Use it for price-slope ideas. Their control set is the M-set plus the nearest inputs, **never s·η itself** (the math audit's finding 1) |
| `eta_mod_controls` | symmetric modulators (n, m); the batch adds each s_j·η as a control |
| `m_set: True` | the batch adds η·\|η\| per tour (η per tour × season and η³ per tour are always in the screen) |
| `x_of_eta` | a function `(eta, rows) -> x` for a column that depends on the base's η non-linearly (e.g. I-042's τ = ĥ_B/p − ĥ_A/(1 − p), p = σ(η)): `rows` indexes the panel's rows; the batch calls it with each base's η on the screen rows, and with the panel's `eta_model` for the swap test and the hash |
| `controls` | antisymmetric control columns (n, m), with `control_names` |
| `tabpfn` | the deployment columns `{name: (array, kind, partner)}` |

The swap test checks `x` as antisymmetric, or as symmetric when `x_times_eta`, and `eta_mod_controls` as symmetric.

For a fixed player trait (hand, height, country), `prepare` also returns the trait as `<trait>_a/_b`, and the hypothesis row carries `"trait": "fixed", "trait_cols": ["<trait>"]`: the batch then permutes the trait across players within each tour (the critique's M4) and re-runs `combine`.

Constants (half-lives, shrinkage, windows) are set from the originator's specification or tuned only on targets that involve neither the price nor the current best (forecasting the statistic itself, or prediction without odds) on 2013–2018. Record each constant and how it was chosen in the module's docstring. After M1 nothing in a builder changes; a variant made later is exploratory and cannot enter the bundle.
