"""Generate the independent Decimal oracle for PRAMA Protokol v0.3.0.

This script contains no import from either production implementation. Run it
only as part of a versioned numerical recertification.
"""

from __future__ import annotations

from decimal import Decimal, getcontext
import json
from pathlib import Path


getcontext().prec = 100
ZERO = Decimal(0)
ONE = Decimal(1)
CFG = {
    "delta_ref": Decimal(1),
    "g_smooth": 2,
    "h": Decimal(1),
    "kappa_cert": Decimal("0.1"),
    "lambda_0": Decimal(1),
    "lambda_max": Decimal(1),
    "lambda_min": Decimal("0.1"),
    "r_cert": Decimal("0.5"),
    "tau_cert": Decimal(
        "1.4426950408889634073599246810018921374266459541529859341354494069311092191811851"
    ),
    "theta_scale": Decimal(2),
}


def decimal_text(value: Decimal) -> str:
    if value == ZERO:
        return "0"
    return format(value.normalize(), "f")


def project(inputs: list[dict[str, str | bool | None]]) -> list[dict[str, str | bool | int]]:
    xi = ZERO
    area = ZERO
    capacity = CFG["lambda_0"]
    theta = CFG["theta_scale"] * capacity
    margins: list[Decimal] = []
    smooth_previous: Decimal | None = None
    rows: list[dict[str, str | bool | int]] = []
    emitted = 0

    for source_index, source in enumerate(inputs):
        if source["expected"] is None:
            if emitted:
                raise ValueError("internal missing is not a golden success vector")
            continue
        omega = Decimal(str(source["omega"]))
        expected = Decimal(str(source["expected"]))
        control = Decimal(str(source["u_lambda"]))
        delta = abs(omega - expected) / (expected + ONE)
        delta_tilde = delta / CFG["delta_ref"]
        excess = max(xi - theta, ZERO)
        area_next = area + CFG["h"] * excess
        lambda_raw = (
            capacity
            - CFG["kappa_cert"] * CFG["h"] * area_next
            + CFG["h"] * control
        )
        capacity_next = min(CFG["lambda_max"], max(CFG["lambda_min"], lambda_raw))
        theta_next = CFG["theta_scale"] * capacity_next
        xi_next = CFG["r_cert"] * xi + (ONE - CFG["r_cert"]) * delta_tilde
        margin = theta_next - xi_next
        margins.append(margin)
        width = min(len(margins), int(CFG["g_smooth"]))
        smooth = sum(margins[-width:], ZERO) / Decimal(width)
        gradient = ZERO if smooth_previous is None else smooth - smooth_previous
        rows.append(
            {
                "A": decimal_text(area_next),
                "G": decimal_text(gradient),
                "M": decimal_text(margin),
                "delta": decimal_text(delta),
                "delta_tilde": decimal_text(delta_tilde),
                "e": decimal_text(excess),
                "input_index": emitted,
                "lambda": decimal_text(capacity_next),
                "sigma_op": bool(source["sigma_op"]),
                "source_input_index": source_index,
                "state_index": emitted + 1,
                "theta": decimal_text(theta_next),
                "u_lambda": decimal_text(control),
                "valid": True,
                "xi": decimal_text(xi_next),
            }
        )
        xi = xi_next
        area = area_next
        capacity = capacity_next
        theta = theta_next
        smooth_previous = smooth
        emitted += 1
    return rows


def source_rows(values: list[str], warmup: int = 0) -> list[dict[str, str | bool | None]]:
    rows: list[dict[str, str | bool | None]] = [
        {"expected": None, "omega": None, "sigma_op": False, "u_lambda": "0"}
        for _ in range(warmup)
    ]
    rows.extend(
        {"expected": "1", "omega": value, "sigma_op": True, "u_lambda": "0"}
        for value in values
    )
    return rows


def document() -> dict:
    vectors = [
        {
            "id": "A2_REBASE_3W",
            "inputs": source_rows(["1", "5", "1", "9", "1", "13", "1"]),
        },
        {
            "id": "A2_WARMUP_REBASE",
            "inputs": source_rows(["3", "1", "7", "1", "11", "1", "15"], warmup=2),
        },
    ]
    for vector in vectors:
        vector["expected_rows"] = project(vector["inputs"])
    return {
        "configuration": {
            key: str(value) if isinstance(value, int) else decimal_text(value)
            for key, value in CFG.items()
        },
        "oracle": {
            "arithmetic": "decimal.Decimal",
            "imports_production_kernel": False,
            "precision_decimal_digits": getcontext().prec,
            "ring_reference": "fresh logical oldest_to_newest sum on every emitted row",
        },
        "schema": "prama.v0_3.golden_vectors.v2",
        "vectors": vectors,
    }


if __name__ == "__main__":
    target = Path(__file__).with_name("v0_3_golden_vectors_v2.json")
    target.write_text(
        json.dumps(document(), ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(target)
