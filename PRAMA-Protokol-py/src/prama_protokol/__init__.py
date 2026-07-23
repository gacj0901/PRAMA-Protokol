"""PRAMA Protokol — operational protocol of Aptadynamic Cybernetics.

Structural viability evaluation from observable behavior alone.

    from prama_protokol import project_v3, KernelConfigV3
    gamma = project_v3(omega, expected)       # Ω → Γ_v3

Normative software contract: repository-local ``SPECIFICATION.md``.
"""

from .kernel import KernelConfig, project, stratify
from .kernel_v3 import (
    GammaRowV3,
    GammaV3,
    KernelConfigV3,
    KernelV3,
    NumericAuditV3,
    V3ProjectionError,
    project_v3,
)
from .interface import (
    ObservationInterface,
    CausalConditionalMean,
    causal_conditional_mean,
)
from . import compliance, compliance_legacy

__version__ = "0.3.0"

__all__ = [
    "KernelConfig",
    "project",
    "stratify",
    "GammaRowV3",
    "GammaV3",
    "KernelConfigV3",
    "KernelV3",
    "NumericAuditV3",
    "V3ProjectionError",
    "project_v3",
    "ObservationInterface",
    "CausalConditionalMean",
    "causal_conditional_mean",
    "compliance",
    "compliance_legacy",
]
