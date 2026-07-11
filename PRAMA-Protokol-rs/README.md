# prama-protokol-rs

**PRAMA Protokol — Rust production core of the universal aptadynamic projection
kernel. Equivalence-certified against the validated Python reference.**

G.A.C.J. — ORCID: [0009-0009-5649-1359](https://orcid.org/0009-0009-5649-1359)
Part of the **AptadynamiK** program.
Normative specification: [AS-1](https://github.com/gacj0901/aptadynamic-cybernetics) ·
Python reference: [`prama-protokol`](https://github.com/gacj0901/prama-protokol)

> **Denomination.** The protocol is always referred to as **PRAMA Protokol** in full;
> the admissible short form is *the Protokol*.

## What this is — and what it is not

This crate is the **production armor of the Engine**: the universal kernel π
(Ω → Γ = (Δ, Ξ, λ, Θ, M, G), regime stratification, latent-collapse detection)
compiled for always-on, low-latency, embeddable deployment. It is an
operation-for-operation replica of the certified Python kernel — the same
mathematics that produced the BPA/NYISO empirical validation — verified to
machine precision (**max divergence 8.9×10⁻¹⁶; all discrete flags identical**;
see [`EQUIVALENCE-RS.md`](EQUIVALENCE-RS.md)).

It is deliberately **not** a twin of any domain repository. Per AS-1 P7, domains
are thin observation interfaces; the consolidated, hardened thing is the kernel.
`Aptadynamic-Electrical-Grid` serves future domains (water/drainage networks,
AI production, markets) as the *template* for designing an observation
interface — never as code to fork.

## Two execution modes

**Batch** (`project`) — the certified equivalent of the reference; for studies
and replays.

**Streaming** (`Kernel::step`) — O(1) per bin, constant memory; for production
monitors. All outputs match batch to near machine epsilon (unit-tested). Both
paths use a trailing/right-aligned mean followed by `G[0] = 0` and
`G[t] = smooth_M[t] - smooth_M[t-1]`.

```rust
use prama_protokol::{Kernel, KernelConfig};

let mut k = Kernel::new(KernelConfig::default());
loop {
    let (omega, expected) = next_bin(); // from the domain's observation interface
    let out = k.step(omega, expected, None);
    if out.latent_collapse { alert(out); } // operating while consuming margin
}
```

## Performance

Single thread, this container: **20.2 M bins/s** pure kernel (10M bins in
0.495 s) — ~90× the Python reference. At one bin per hour per monitored asset,
one core sustains ~72 billion asset-hours per second of wall time: throughput
will never be the constraint; observation quality will.

## CLI

`prama-project` reads `omega,expected` CSV on stdin (expected may be `nan` on
warm-up rows), writes the Γ trajectory on stdout. Used by the re-runnable
cross-language certification (`tests/equivalence_vs_python.py`) and usable for
batch pipelines without Python.

```bash
cargo build --release
./target/release/prama-project --tau 336 --gsmooth 24 < stream.csv > gamma.csv
./target/release/prama-project --bench 10000000   # internal benchmark
```

## Scope discipline

- The kernel is domain-blind: no topology, no mechanism, no domain knowledge
  may be added here (AS-1 P7, §4).
- Kernel parameters are fixed across domains given a declared bin scale
  (AS-1 C5; bin-scale declaration per the pending v1.1 clause).
- This core implements the **certified exponential-memory accumulator**. The
  genuine long-memory question (power-law kernels, motivated by the Hurst ≈ 0.63
  signature in BPA data) is a *theory-level* extension of AS-1 P2 — pre-registered
  and validated before any implementation lands here. This crate reserves the
  extension point; it does not preempt the theory.

## Roadmap

1. ~~Core + streaming + CLI + cross-language certification~~ — **done** (v0.2.0).
2. Python bindings (PyO3/maturin) so studies iterate in Python on the compiled core.
3. First production domain deployment (candidate: water & drainage networks —
   see the domain blueprint in the program's planning documents).
4. Long-memory extension point, gated on AS-1 P2 amendment.

## License

AGPL-3.0. Commercial licensing, industrial collaborations and academic research
partnerships may be available separately.
