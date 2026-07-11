# Equivalence Certification — Python package

**Package:** `prama-protokol` v0.2.1
**Live cross-implementation certification:** Python ↔ Rust, see
`../PRAMA-Protokol-rs/EQUIVALENCE-RS.md`.
**Kernel identity pin:** golden vectors, `tests/golden_gamma.npz`
(regenerated 2026-07-11 over the 0.2.1 kernel; kernel arithmetic is
identical to 0.2.0 — the 0.2.1 changes touch only the compliance module,
tests and documentation).

## Historical record — extraction-time certification (FROZEN)

At extraction (certified run of 2026-07-04, package v0.2.0-pre), the
Reference Kernel (`prama_protokol.kernel.project`) and the generalized
causal expectation (`prama_protokol.interface.causal_conditional_mean`)
were verified **numerically identical** — exact equality, not
tolerance-based — to the implementation they were extracted from
(`Aptadynamic-Electrical-Grid`, then containing its own kernel). Every Γ
column (Δ, Ξ, λ, Θ, M, G), the latent-collapse flag and the stratum
assignment matched under `numpy.array_equal`; warm-up NaN patterns of the
seasonal expectation matched exactly.

That comparison is **no longer executable and no longer meaningful**: the
grid repository has since inverted the dependency and imports its kernel
from this package (`from prama_protokol import project`). A comparison of
the package against a wrapper around itself would be circular and certify
nothing. The old cross-repository test has therefore been replaced by a
golden-vector regression (`tests/test_equivalence.py`) that pins the
kernel's exact numerical identity; any future divergence — however small —
fails bit-exact reproduction and requires a version bump, an ANOMALIES.md
entry, fixture regeneration and Rust recertification.

## Consequence (corrected)

No empirical validation is claimed to transfer through this document.
Empirical results produced with 0.1.0 kernels (central-difference G) are
non-revalidated (see `../ANOMALIES.md`). Evidence produced with the
0.2.x causal kernel stands on its own runs in the domain repositories,
under their own gates; this package certifies kernel identity, not
domain conclusions.
