# Equivalence Certification — Rust core vs certified Python reference

**Crate:** `prama-protokol-rs` v0.2.0
**Reference:** `prama-protokol` (Python) v0.2.1 — kernel arithmetic
identical to 0.2.0; the 0.2.1 changes touch only the compliance module,
tests and documentation.
**Certification run:** 2026-07-11, against certified Python commit
`69a51de562910539a2b4c3755f167dd0789ad32d` (0.2.1, including causal G
from `c576fd4`). Rule in force: a
certification record is valid only if its run postdates every
kernel-touching change it covers (see `../ANOMALIES.md`). Earlier record
of 2026-07-05 is superseded.

## Method
Randomized streams (gamma observables, noisy expectations, NaN warm-up fractions
0–5%) projected by both implementations under multiple configurations, including
the validated grid configuration (tau=336, g_smooth=24) and the LLM-domain
configuration (tau=64, g_smooth=16). Comparison via the CLI (`prama-project`)
with 17-significant-digit CSV round-trip. Re-runnable: `tests/equivalence_vs_python.py`.

## Result — PASS
| Trial | n | config | max |diff| over Γ | latent / stratum / valid |
|---|---|---|---|---|
| 0 | 10,000 | 336/24, 2% NaN | 8.9e-16 | identical |
| 1 | 10,000 | 64/16 | 4.4e-16 | identical |
| 2 | 50,000 | 336/24, 5% NaN | 8.9e-16 | identical |

Maximum divergence is at machine epsilon (sources: platform `exp` in the kernel
constant and decimal round-trip). All discrete outputs — latent-collapse flags,
strata S₁–S₄, validity masks — are **exactly identical**. The empirical validation
of the 0.2.0 reference therefore transfers to this core. Empirical conclusions
from 0.1.0 do not transfer and require revalidation (see `../ANOMALIES.md`).

## Performance (same container, single thread)
- Pure kernel: **20.2 M bins/s** (10M bins in 0.495 s) — ~90× the Python reference.
- Streaming `Kernel::step`: O(1) per bin; all coordinates and discrete outputs
  match batch. `G` is the same causal one-step backward difference in all modes.

## Causal alignment
Python batch, Rust batch and `StepOut.g` use the same trailing/right-aligned
mean and one-step backward difference. Length and temporal alignment are
identical, with `G[0] = 0`.
