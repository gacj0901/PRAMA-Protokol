# PRAMA Protokol

**Operational protocol of Aptadynamic Cybernetics: structural viability evaluation from observable behavior alone.**

G.A.C.J. — ORCID: [0009-0009-5649-1359](https://orcid.org/0009-0009-5649-1359)
Part of the **AptadynamiK** program.
Normative specification: **Aptadynamic Cybernetics Specification (AS-1)** — see the [discipline repository](https://github.com/gacj0901/aptadynamic-cybernetics).

> **Denomination.** The protocol is always referred to as **PRAMA Protokol** in full; the admissible short form is *the Protokol*. The token "PRAMA" is never used in isolation.

---

## What the Protokol does

The Protokol answers one question about any system: **is it sustaining itself, or merely appearing to?**

It projects a domain's observable event stream onto six universal coordinates,

```
                O_D                    π
  Domain 𝒟 ────────► Observables Ω ────────► Γ(t) = (Δ, Ξ, λ, Θ, M, G) ────► Regimes / Alerts
             (domain-specific,        (fixed kernel,
              strictly causal)         identical across domains)
```

and evaluates the single viability condition **Ξ(t) ≤ Θ(λ(t))** — accumulated structural tension against an endogenous, history-contracted threshold. It exposes a state called **latent collapse**: the system is operational, its margin is still positive, and its margin is being consumed (σ_op = 1 ∧ M ≥ 0 ∧ G < 0). This is a structural classification, not a validated early-warning claim.

The projection kernel π never models the phenomenon: no topology, no mechanism, no causal model of the domain enters it. Only the Observation Interface O_D is domain-specific. This separation is not rhetoric; it is an architectural constraint, mechanically auditable, with a defined empirical test (AS-1 §8).

## Components

```
┌─────────────────────────────────────────────────────┐
│                PRAMA Protokol Engine                │
│                                                     │
│  Observation Interface (O_D)   ← the ONLY domain-   │
│    raw measurements → normalized  specific part     │
│    causal observables Ω           (contract C1–C5)  │
│                                                     │
│  Reference Kernel (π)          ← universal, fixed,  │
│    Ω → Γ = (Δ,Ξ,λ,Θ,M,G)         identical across   │
│                                   domains           │
│                                                     │
│  Runtime Engine                ← orchestration:     │
│    ingest → omega → projection    streaming,        │
│    → regimes → alerts             batching, replay  │
│                                                     │
│  Compliance Module             ← verification that  │
│    conformance checks, study      the principles    │
│    discipline, audit records      hold in this      │
│                                   deployment        │
└─────────────────────────────────────────────────────┘
```

## Status

**Kernel v0.2.1 is extracted and equivalence-certified. Empirical incremental value is not validated.**

This repository ships operational code:

```
src/prama_protokol/
├── kernel.py        Reference Kernel (π): Ω → Γ = (Δ, Ξ, λ, Θ, M, G),
│                    regime stratification S₁–S₄, latent-collapse detection.
│                    Domain-blind: receives bare arrays, contains zero
│                    domain references.
├── interface.py     Observation Interface contract (C1–C5) + a universal
│                    strictly causal expectation builder
│                    (CausalConditionalMean — conditional mean over any
│                    categorical context; the reference grid profile is the
│                    special case context = (month, hour)).
└── compliance.py    Mechanical contract verification: C2 truncation test,
                     C3 anti-degeneration gate, ρ_I band, C4 informational
                     density, MEM memory-ratio, N1 rescaling test — the
                     passing record, not analytical argument, establishes
                     conformance (AS-1 §8).
tests/               21 tests: structural tests of P1–P7 by construction,
                     compliance self-tests (future-leak and degenerate-Δ
                     detection), golden-vector regression, and cross-language
                     equivalence tests.
examples/            synthetic_demo.py — a runnable end-to-end story:
                     a system whose failures silently begin to beget
                     failures; first latent-collapse alert 0.5 days after
                     onset, margin exhaustion 157 days later.
```

**Equivalence certification.** The kernel is verified **bit-identical** across
the certified Python/Rust implementations (see
[`EQUIVALENCE.md`](EQUIVALENCE.md)). Equivalence certifies arithmetic identity;
it does not validate an empirical performance claim.

Quick start:

```bash
pip install -e .
python -m pytest tests/ -v        # 12 structural + compliance tests
                                  # (+2 equivalence tests if the reference
                                  #  implementation is also installed)
python examples/synthetic_demo.py
```

Current electrical-domain evidence:

| Study | Current status |
|---|---|
| **BPA G1** | Invalid for confirmatory claim because C3 failed in evaluation. |
| **NYISO G1** | Honest null under frozen historical rules. |
| **NYISO G2** | Valid confirmatory negative result: CH-L passed its gates, but the selected B-TRIV comparator outperformed the Protokol (`contrast = -0.049623`, `p = 1.0`); frozen program-falsification rule activated. |

Historical ratios `16.0` (BPA) and `1.90` (NYISO) are superseded exploratory
provenance, not current validation claims. Full record:
[`G2_RESULT_H5.md`](https://github.com/gacj0901/Aptadynamic-Electrical-Grid/blob/main/G2_RESULT_H5.md).

### Roadmap

1. ~~**Kernel extraction**~~ — **done** (v0.2.0): π is installable, strictly causal, and batch/streaming equivalent ([`EQUIVALENCE.md`](EQUIVALENCE.md)).
2. ~~**Compliance Module**~~ — **done** (v0.1.0): executable C2/C3/N1 checks with self-tests (extended in 0.2.1 to ρ_I, C4 density, MEM) that detect future-leaking expectations and degenerate Δ.
3. ~~**Observation Interface base**~~ — **done** (v0.1.0): the C1–C5 contract as an abstract base class plus a universal causal expectation builder.
4. ~~**Migrate the reference implementation**~~ — complete; the grid package pins `prama-protokol==0.2.1`.
5. **Runtime Engine** — streaming/batch orchestration (ingest → omega → projection → regimes → alerts) as a reusable layer.
6. **New domains** — require independent observation contracts and preregistration; kernel equivalence alone is not empirical validation.

Studies predating AS-1 are classified *exploratory*, per the specification's study discipline.

## How a new domain joins

Writing a domain implementation means writing **one component**: an Observation Interface satisfying the contract of AS-1 §5 —

- **C1 Strict observability** — only externally observable events; no hidden state.
- **C2 Strict causality** — expectations built from the strict past only.
- **C3 Genuine decoupling** — Δ measures deviation from the system's own causally expected behavior, never raw activity.
- **N1 Scale invariance** — dimensionless, normalization-explicit observables (historically AS-1 "C4"; in the deployed domain contract C4 is informational density).
- **C5 No retro-fitting** — kernel parameters fixed across domains; negative results reported as found.

The kernel is never modified. Each domain implementation lives in its own repository (`Aptadynamic-<Domain>`) together with its Validation Study.

## What the Protokol never does

Per AS-1 §7, a conformant deployment does **not** model the phenomenon, does **not** forecast event occurrence, does **not** produce point predictions of collapse time, and does **not** interpret — Γ is a measurement space; domain meaning is reconstructed by the domain expert. Claiming more than this on behalf of the framework is non-conformant communication.

## Authority

| Question | Authority |
|---|---|
| What must this Engine satisfy? | **AS-1** ([discipline repository](https://github.com/gacj0901/Aptadynamic-Cybernetics)) |
| Why is it mathematically true? | **Logical–Mathematical Corpus** — DOI: [10.5281/zenodo.20369325](https://doi.org/10.5281/zenodo.20369325) |
| Does it work on real data? | **Validation Studies** (domain repositories) |

## License

Released under the GNU Affero General Public License v3.0 (AGPL-3.0). Commercial licensing, industrial collaborations and academic research partnerships may be available separately.
