# Equivalence Certification — Rust core vs Python reference

**Crate:** `prama-protokol-rs` v0.3.0

**Reference:** the local Python v0.3.0 implementation

**Normative contract:** [`../SPECIFICATION.md`](../SPECIFICATION.md)

**Joint result:**
[`../results/v0_3_0_numeric_recertification.json`](../results/v0_3_0_numeric_recertification.json)

## Method

The certification runner loads the independent v1 and v2 vectors, projects
each input through Python batch, Rust batch and Rust streaming, then compares
all emitted fields. The suite also covers configuration validation, leading
warm-up, fail-closed internal gaps, causal backward difference, capacity
controls, debt accumulation, capacity clipping and periodic ring rebuilds.

Continuous fields are compared under the declared absolute, relative and ULP
limits. Boolean flags and temporal indices are exact. Batch and streaming are
bit-identical within each language.

## Long-run audit

An adversarial stream of at least 66,000 emitted rows verifies:

- ring sum against a fresh logical oldest-to-newest reconstruction;
- smoothed margin and causal `G`;
- capacity step and cumulative ledger identities;
- a distinguishable accumulated-debt coupling;
- detection of an omitted-coupling mutation;
- detection of disabled periodic ring rebuilds.

## Re-run

From the repository root:

```bash
python scripts/certify_v0_3_0.py
```

The command runs the Python suite, all Rust targets, cross-language vectors,
long numerical audit and mutations, then writes the joint result artifact.

## Claim boundary

PASS certifies implementation equivalence and numerical custody only. It does
not imply an empirical conclusion for any use of the kernel.
