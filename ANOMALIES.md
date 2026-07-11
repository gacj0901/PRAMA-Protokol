# Anomalies

## 0.1.0 batch causality violation (corrected in 0.2.0)

Version 0.1.0 computed `G` with a central difference in Python batch and Rust
batch. Thus an interior `G[t]` could depend on `M[t+1]`, violating prefix
causality. Rust streaming already used a one-step backward difference.

Version 0.2.0 unifies Python batch, Rust batch and Rust streaming under
`G[0] = 0` and `G[t] = smooth_M[t] - smooth_M[t-1]` for `t > 0`, where
`smooth_M` is a trailing, right-aligned mean with `min_periods=1`. Empirical
results produced with 0.1.0 must be revalidated and are not current 0.2.0
evidence.

## 0.2.0 certification records predated the change they certified (corrected in 0.2.1)

The commit that made `G` causal (`c576fd4`, 2026-07-11) modified
`kernel.py` and `lib.rs`, but the equivalence records it shipped kept
run dates of 2026-07-04 (`EQUIVALENCE.md`) and 2026-07-05
(`EQUIVALENCE-RS.md`) — certification runs dated BEFORE the kernel
change, over a test suite that the same commit extended. Additionally,
the Python↔reference equivalence test had become circular: the grid
repository now imports its kernel from this package, so the test
compared the package against a wrapper around itself.

0.2.1 corrects the record: the extraction-time certification is frozen
as history in `EQUIVALENCE.md`; kernel identity is pinned by golden
vectors (`tests/golden_gamma.npz`, bit-exact regression); the live
cross-implementation certification is Python↔Rust and was re-run over
the 0.2.1 tree (see `EQUIVALENCE-RS.md` for the run record). Rule made
explicit: a certification record is valid only if its run postdates
every kernel-touching change it covers.
