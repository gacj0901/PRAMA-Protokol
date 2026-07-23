# PRAMA Protokol

**A universal, domain-blind kernel for structural viability projection from
observable behavior.**

G.A.C.J. — ORCID: [0009-0009-5649-1359](https://orcid.org/0009-0009-5649-1359)

> **Denomination.** The protocol is always referred to as **PRAMA Protokol**
> in full; the admissible short form is *the Protokol*.

## Repository boundary

This repository is the complete authority for the software contract it ships.
Its normative definition is [`SPECIFICATION.md`](SPECIFICATION.md); no other
repository is required to interpret, install, test or certify the kernel.

Dependency direction is deliberately one-way:

```text
domain implementation ──pins/imports──> PRAMA Protokol
PRAMA Protokol          ──imports─────> no domain implementation
```

Consumer projects own their adapters, data, outcome definitions,
preregistrations and empirical conclusions. They may reference a released
Protokol version. This repository does not reference or summarize individual
consumer projects and does not absorb their development history.

## What the Protokol does

The Protokol maps a dimensionless observable stream and its strictly causal
expectation onto a causal state trajectory:

```text
       Observation Interface                         fixed kernel
raw data ───────────────────> Ω=(ω,ω̂,uλ,σ_op) ─────────────> Γv3
       owned by the consumer                          owned here
```

The projection accumulates discrepancy in `Ξ`, integrates excess debt in `A`,
updates bounded capacity `λ`, derives the endogenous threshold `Θ(λ)`, and
emits viability margin `M = Θ − Ξ` with causal margin trend `G`. A declared
non-negative input `uλ` can support capacity without erasing debt or memory.

The kernel contains no topology, mechanism, domain name, dataset or outcome.
It is a measurement transform, not a phenomenon model.

## Implementations

This monorepository contains two implementations of the same contract:

```text
PRAMA-Protokol-py/   Python executable reference, v3 compliance and explicit legacy surface
PRAMA-Protokol-rs/   Rust batch/streaming core and CLI
```

Python golden vectors pin exact arithmetic. Rust is cross-certified against
the Python reference to machine precision, with identical discrete outputs.
See [`PRAMA-Protokol-py/EQUIVALENCE.md`](PRAMA-Protokol-py/EQUIVALENCE.md) and
[`PRAMA-Protokol-rs/EQUIVALENCE-RS.md`](PRAMA-Protokol-rs/EQUIVALENCE-RS.md).

## Status

**Version `0.3.0`: causal batch/streaming kernel, fail-closed activation,
periodic ring resummation and numerical ledgers implemented and jointly
certified.**

Certification establishes that the included implementations execute the same
contract. It does not establish predictive value, operational usefulness or
empirical superiority in any domain. Such claims require independent,
prospective evidence produced by a consumer.

The append-only implementation incident record is
[`ANOMALIES.md`](ANOMALIES.md).

The certified release record is
[`RELEASE_V0_3_0.md`](RELEASE_V0_3_0.md).

## Quick verification

Python:

```bash
cd PRAMA-Protokol-py
python -m pip install -e .
python -m pytest -q
```

Rust:

```bash
cd PRAMA-Protokol-rs
cargo test
```

Cross-language equivalence:

```bash
python scripts/certify_v0_3_0.py
```

## Consumer contract

A consumer supplies four things only:

1. normalized dimensionless observations `omega`;
2. a strictly causal expectation `expected`;
3. optionally, a declared non-negative capacity input `u_lambda`;
4. optionally, an independently defined operational-state mask `sigma_op`.

Leading expectation warm-up rows are excluded. Missing values after state
emission begins fail closed and never simulate relaxation.

Before interpreting outputs, the consumer must establish its observation
contract and run the applicable compliance checks. Kernel parameters and gate
thresholds are frozen before evaluation outcomes. Negative or invalid results
remain with the consumer and never trigger retrospective kernel tuning.

## Claim boundary

PRAMA Protokol does not, by itself:

- forecast an event;
- attribute a cause;
- estimate a probability or time to failure;
- define an operational intervention;
- validate an Observation Interface;
- turn implementation equivalence into empirical evidence.

Those statements are part of the normative contract, not disclaimers added
after evaluation.

## License

Released under the GNU Affero General Public License v3.0
(`AGPL-3.0-only`).
