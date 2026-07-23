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
an extraction-era comparison had become circular after dependency direction
was corrected: the comparator was a downstream wrapper around this package.

0.2.1 corrects the record: kernel identity is pinned by golden vectors
(`tests/golden_gamma.npz`, bit-exact regression); the live
cross-implementation certification is Python↔Rust, wholly contained in this
repository, and was re-run over the 0.2.1 tree (see `EQUIVALENCE-RS.md`). Rule
made explicit: a certification record is valid only if its run postdates every
kernel-touching change it covers. Downstream software is never an identity
anchor for the universal kernel.

## Indefinite incremental ring drift (bounded in 0.3.0)

The compatibility streaming kernel maintained its trailing-margin sum only by
subtracting the outgoing value and adding the incoming value. Floating-point
cancellation error could therefore accumulate with total process age rather
than with the fixed window size. Finite equivalence trials did not establish a
bounded error contract for indefinite streaming.

Version 0.3.0 introduces a separate state machine with deterministic periodic
ring rebuilds. After inserting each multiple of the smoothing-window length,
the ring sum is reconstructed in logical order from oldest to newest. Python
batch, Python streaming, Rust batch and Rust streaming share the same calendar
and addition order.

The release also exposes independent ring and capacity ledgers. Its
certification includes a long adversarial stream and two blocking mutations:
disabled ring rebuilds and omitted accumulated-debt coupling. Both must be
detected before the release can pass. The compatibility API and its frozen
vectors remain available; its numerical behavior is not rewritten
retroactively.
## Normative compliance surface bound to the compatibility kernel (corrected after 0.3.0)

The public Python module named `prama_protokol.compliance` remained imported
from the package root after v3 became normative, but its default configuration,
projection, memory parameter and internal Xi replica still belonged to the
frozen pre-v3 compatibility kernel. A passing record from that module therefore
did not mechanically certify `KernelV3/project_v3`.

The post-0.3.0 tree binds `compliance` exclusively to `KernelConfigV3`,
`project_v3` and `GammaV3`, emits the `prama.compliance.v3` schema and
rejects compatibility configurations. The former implementation remains
available only as `compliance_legacy`. No kernel recurrence or certified
golden vector changed; this is a correction of the public verification surface.
