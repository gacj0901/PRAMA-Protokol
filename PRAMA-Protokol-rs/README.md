# PRAMA Protokol — Rust core

The Rust crate is the batch, streaming and CLI implementation of the universal
kernel defined in [`../SPECIFICATION.md`](../SPECIFICATION.md). It is certified
against the Python reference included in this same repository.

## Crate boundary

The crate receives normalized `omega`, strictly causal `expected` values, an
optional non-negative capacity input and an optional operational-state flag.
It contains no data adapter, topology, outcome definition or domain policy.
Consumer software depends on this crate; the crate never depends on a
consumer.

## Execution modes

- `v3::project_v3`: current batch projection;
- `v3::KernelV3::step`: current streaming state machine;
- `project`, `Kernel::step` and `prama-project`: compatibility API.

The current batch and streaming paths implement the same causal alignment and
periodic logical-order ring rebuild:

```text
G(1) = 0
G(n) = smooth_M(n) − smooth_M(n−1)
```

where `smooth_M` is trailing and right-aligned, with a growing prefix during
warm-up.

## Streaming example

```rust
use prama_protokol::v3::{KernelConfigV3, KernelV3};

let mut kernel = KernelV3::new(KernelConfigV3::default()).unwrap();
loop {
    let (omega, expected, u_lambda, sigma_op) = next_bin();
    if let Some(out) = kernel.step(omega, expected, u_lambda, sigma_op).unwrap() {
        consume(out);
    }
}
```

The caller owns `next_bin` and `consume`; neither is part of the universal
kernel.

## Compatibility CLI

`prama-project` preserves the previous `omega,expected` command-line surface.
The normative v0.3.0 interface is the `v3` library module.

```bash
cargo build --release
./target/release/prama-project --tau 336 --gsmooth 24 < stream.csv > gamma.csv
./target/release/prama-project --bench 10000000
```

## Verification

```bash
cargo test
cargo test --all-targets
python ../scripts/certify_v0_3_0.py
```

The cross-language harness invokes only the Python and Rust implementations
contained in this repository. [`EQUIVALENCE-RS.md`](EQUIVALENCE-RS.md) records
the certified tolerances and discrete-output identity.

Equivalence is an implementation property. It is not evidence of predictive
or operational value in any consuming domain.

## Scope discipline

- kernel equations and temporal alignment are fixed by the local
  specification;
- configuration is explicit and expressed in emitted stream bins;
- no raw-data normalization or empirical threshold is embedded here;
- arithmetic changes require a version change, anomaly entry, golden-vector
  regeneration and cross-language recertification;
- consumer-specific code, examples, conclusions and roadmaps do not belong in
  this crate.

## License

AGPL-3.0-only.
