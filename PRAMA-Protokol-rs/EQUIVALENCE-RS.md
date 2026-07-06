# Equivalence Certification — Rust core vs certified Python reference

**Crate:** `prama-protokol-rs` v0.1.0
**Reference:** `prama-protokol` (Python) v0.1.0 — itself bit-identical to the
BPA/NYISO-validated implementation (see EQUIVALENCE.md in that repository).
**Date:** 2026-07-05

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
of the reference therefore transfers to this core.

## Performance (same container, single thread)
- Pure kernel: **20.2 M bins/s** (10M bins in 0.495 s) — ~90× the Python reference.
- Streaming `Kernel::step`: O(1) per bin; state coordinates (Ξ, λ, Θ, M) match
  batch to 1e-15 (unit test). G uses a backward difference in streaming vs
  numpy-gradient central differences in batch — a documented, deliberate divergence
  (a streaming monitor cannot see the future bin; the batch estimator can).

## Declared divergence
`StepOut.g` (streaming) ≠ batch `G` on interior points by construction. Any study
mixing modes must declare which estimator it uses. Batch mode is the certified
equivalent of the reference; streaming mode is the production estimator.
