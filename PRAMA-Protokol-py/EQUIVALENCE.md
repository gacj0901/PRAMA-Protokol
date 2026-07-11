# Equivalence Certification

**Package:** `prama-protokol` v0.2.0
**Reference:** `Aptadynamic-Electrical-Grid` (the BPA/NYISO-validated implementation)
**Date:** 2026-07-04

## Claim

The Reference Kernel of this package (`prama_protokol.kernel.project`) and the
generalized causal expectation (`prama_protokol.interface.causal_conditional_mean`)
are **numerically identical** to the validated code they were extracted from.
The extraction changed *packaging* — the kernel now receives bare arrays and
contains zero domain references — but not one bit of *mathematics*.

## Method

Automated tests in `tests/test_equivalence.py`, run with both packages installed:

1. **Kernel projection** — a synthetic observable stream (2+ years of hourly
   bins, seasonal Poisson structure) is projected by the reference
   implementation's `projection.project` and by this package's kernel under
   the same configuration. Every Γ column (Δ, Ξ, λ, Θ, M, G), the
   latent-collapse flag, and the stratum assignment are compared with
   `numpy.array_equal` — **exact equality, not tolerance-based**.

2. **Causal expectation** — the reference's seasonal profile
   (`omega.expected_profile`, hour × month running conditional mean) is
   compared against `causal_conditional_mean` with context keys
   (month, hour). Warm-up NaN patterns and all defined values must match
   exactly.

## Result

Both tests **pass with exact equality** (verification run of 2026-07-04:
14/14 tests passed, including the two equivalence tests).

## Consequence

Because the kernel is bit-identical, the empirical validation of the
reference implementation transfers to this package: the BPA conditional
severity discrimination (ratio 16.0) and the corrected NYISO result (1.90)
were produced by *this* mathematics. From this version onward, the Separation
Theorem (AS-1 P7) is enforced by engineering: every domain implementation
depends on this package, so "same kernel across domains" is a checkable fact
(same package, same version), not a claim.

## Notes on the extraction

- The reference `ProjectionConfig` declared a `lambda_erosion` parameter that
  is **unused** in the validated code path (erosion is governed by `kappa`).
  It was dropped from `KernelConfig`; no numerical effect.
- The kernel's API changed from a domain DataFrame (column `intensity`) to
  bare arrays `(omega, expected)`; the optional `sigma_op` argument defaults
  to `omega > 0`, matching the reference's operational-state proxy.
- The compliance module's degeneration statistic (C3) was refined relative to
  the draft specification: for sparse event streams, the pass criterion is
  relative to the canonical degenerate Δ (constant-like causal reference),
  since |corr(Δ, ω)| is mechanically high when most information is the
  activity spike itself. Dense streams keep the absolute criterion.
