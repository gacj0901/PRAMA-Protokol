#!/usr/bin/env python3
"""Recertify public PRAMA Protokol v0.3.0 without domain outcomes."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import struct
import subprocess
import sys
import tomllib
from typing import Any

import numpy as np


UNIT_ROUNDOFF = 2.0**-53
C_G = 16.0
C_FP = 16.0
R_MIN = 1.0e3
ATOL = 1.0e-14
RTOL = 1.0e-13
MAX_ULP = 64
FLOAT_FIELDS = ("delta", "delta_tilde", "e", "xi", "A", "lambda", "theta", "M", "G", "u_lambda")
DISCRETE_FIELDS = ("sigma_op", "valid", "input_index", "state_index")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ordered_bits(value: float) -> int:
    bits = struct.unpack(">Q", struct.pack(">d", value))[0]
    return (~bits & 0xFFFF_FFFF_FFFF_FFFF) if bits >> 63 else bits | (1 << 63)


def gamma_n(operations: int) -> float:
    product = operations * UNIT_ROUNDOFF
    return product / (1.0 - product)


def fresh_sum(values: list[float], window: int) -> float:
    total = 0.0
    for value in values[-window:]:
        total = total + value
    return total


def adversarial_omega(index: int) -> float:
    large = 1.0e16 + float((index * 104_729) % 1_000_003)
    return large if index % 5 == 0 else 1.0 + float(index % 17)


def config_from(document: dict[str, Any], cls: type) -> Any:
    raw = document["configuration"]
    return cls(
        h=float(raw["h"]),
        tau=float(raw["tau_cert"]),
        theta_scale=float(raw["theta_scale"]),
        lambda_0=float(raw["lambda_0"]),
        lambda_min=float(raw["lambda_min"]),
        lambda_max=float(raw["lambda_max"]),
        kappa_v3=float(raw["kappa_cert"]),
        g_smooth=int(raw["g_smooth"]),
        delta_ref=float(raw["delta_ref"]),
    )


def arrays(vector: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    inputs = vector["inputs"]
    omega = np.asarray(
        [math.nan if row["omega"] is None else float(row["omega"]) for row in inputs],
        dtype=np.float64,
    )
    expected = np.asarray(
        [math.nan if row["expected"] is None else float(row["expected"]) for row in inputs],
        dtype=np.float64,
    )
    if all("u_lambda" in row for row in inputs):
        controls = np.asarray([float(row["u_lambda"]) for row in inputs], dtype=np.float64)
        sigma = np.asarray([bool(row["sigma_op"]) for row in inputs], dtype=np.bool_)
    else:
        controls = np.zeros(len(inputs), dtype=np.float64)
        for row in vector["expected_rows"]:
            controls[int(row["source_input_index"])] = float(row["u_lambda"])
        sigma = np.ones(len(inputs), dtype=np.bool_)
    return omega, expected, controls, sigma


def compare_rows(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any]:
    if len(left) != len(right):
        return {"passed": False, "row_count_equal": False, "max_abs": None, "max_ulp": None}
    max_abs = 0.0
    max_ulp = 0
    passed = True
    for left_row, right_row in zip(left, right, strict=True):
        for field in FLOAT_FIELDS:
            actual = float(left_row[field])
            expected = float(right_row[field])
            difference = abs(actual - expected)
            ulp = abs(ordered_bits(actual) - ordered_bits(expected))
            max_abs = max(max_abs, difference)
            max_ulp = max(max_ulp, ulp)
            if expected == 0.0:
                passed &= difference <= ATOL
            else:
                passed &= math.isclose(actual, expected, abs_tol=ATOL, rel_tol=RTOL)
                passed &= ulp <= MAX_ULP
        passed &= all(left_row[field] == right_row[field] for field in DISCRETE_FIELDS)
    return {"passed": bool(passed), "row_count_equal": True, "max_abs": max_abs, "max_ulp": max_ulp}


def cross_language(root: Path, rust_root: Path, project_v3: Any, config_cls: type) -> dict[str, Any]:
    records = []
    for fixture in ["v0_3_golden_vectors_v1.json", "v0_3_golden_vectors_v2.json"]:
        document = json.loads((root / "tests/data" / fixture).read_text(encoding="utf-8"))
        cfg = config_from(document, config_cls)
        rust_payload = json.loads(
            subprocess.check_output(
                ["cargo", "run", "--release", "--quiet", "--example", "v3_golden", "--", fixture],
                cwd=rust_root,
                text=True,
                encoding="utf-8",
            )
        )
        rust_vectors = {item["id"]: item for item in rust_payload["vectors"]}
        for vector in document["vectors"]:
            identifier = vector["id"]
            omega, expected, controls, sigma = arrays(vector)
            python_error = None
            python_rows: list[dict[str, Any]] = []
            try:
                python_rows = project_v3(omega, expected, cfg, controls, sigma).rows()
            except Exception as error:
                python_error = str(error)
            rust_result = rust_vectors[identifier]
            expected_error = vector.get("expected_error", {}).get("code")
            if expected_error is not None:
                passed = python_error == expected_error and rust_result["error"] == expected_error
                records.append({"fixture": fixture, "id": identifier, "passed": passed, "expected_error": expected_error})
                continue
            comparison = compare_rows(python_rows, rust_result["rows"])
            records.append(
                {
                    "fixture": fixture,
                    "id": identifier,
                    "passed": bool(comparison["passed"] and rust_result["streaming_bit_exact"]),
                    "python_vs_rust": comparison,
                    "rust_streaming_bit_exact": bool(rust_result["streaming_bit_exact"]),
                }
            )
    return {"passed": all(record["passed"] for record in records), "vectors": records}


def long_audit(kernel_cls: type, config_cls: type) -> dict[str, Any]:
    length = 66_000
    window = 24
    cfg = config_cls(g_smooth=window, tau=0.01)
    kernel = kernel_cls(cfg)
    margins: list[float] = []
    sum_abs_A = 0.0
    sum_abs_u = 0.0
    sum_abs_pi = 0.0
    coupling_scale = 0.0
    previous_lambda = cfg.lambda_0
    previous_smooth = None
    max_ring_residual = 0.0
    max_ring_ratio = 0.0
    max_g_residual = 0.0
    max_step_residual = 0.0

    for index in range(length):
        u_value = 2.5e-7 if index % 257 == 0 else 0.0
        row = kernel.step(adversarial_omega(index), 0.0, u_value, True)
        assert row is not None
        margins.append(row.M)
        audit = kernel.numeric_audit
        width = min(index + 1, window)
        fresh = fresh_sum(margins, width)
        residual = abs(audit.ring_sum - fresh)
        sum_abs_window = sum(abs(value) for value in margins[-width:])
        epoch_rows = (index + 1) % window
        if index + 1 < window:
            epoch_operations = index + 1
            epoch_budget = sum_abs_window
        elif epoch_rows == 0:
            epoch_operations = 0
            epoch_budget = 0.0
        else:
            epoch_operations = 2 * epoch_rows
            epoch_budget = sum(
                abs(margins[changed - window]) + abs(margins[changed])
                for changed in range(index + 1 - epoch_rows, index + 1)
            )
        tolerance = C_G * (
            gamma_n(epoch_operations) * epoch_budget + gamma_n(width) * sum_abs_window
        )
        max_ring_residual = max(max_ring_residual, residual)
        max_ring_ratio = max(max_ring_ratio, 0.0 if tolerance == 0.0 else residual / tolerance)
        expected_g = 0.0 if previous_smooth is None else audit.smooth_m - previous_smooth
        max_g_residual = max(max_g_residual, abs(row.G - expected_g))
        previous_smooth = audit.smooth_m
        max_step_residual = max(max_step_residual, abs(audit.lambda_step_residual))

        lambda_raw = previous_lambda - cfg.kappa_v3 * cfg.h * row.A + cfg.h * u_value
        pi = row.lambda_ - lambda_raw
        sum_abs_A += abs(row.A)
        sum_abs_u += abs(u_value)
        sum_abs_pi += abs(pi)
        coupling_scale += cfg.kappa_v3 * cfg.h * row.A
        previous_lambda = row.lambda_

    audit = kernel.numeric_audit
    operation_count = 3 * length + 12
    scale = (
        abs(previous_lambda)
        + abs(cfg.lambda_0)
        + cfg.kappa_v3 * cfg.h * sum_abs_A
        + cfg.h * sum_abs_u
        + sum_abs_pi
    )
    lambda_tolerance = C_FP * gamma_n(operation_count) * scale
    separation = coupling_scale / lambda_tolerance
    passed = (
        max_ring_ratio <= 1.0
        and max_g_residual == 0.0
        and abs(audit.lambda_ledger_residual) <= lambda_tolerance
        and separation >= R_MIN
        and audit.resummation_count == length // window
    )
    return {
        "C_G": C_G,
        "C_fp": C_FP,
        "R_min": R_MIN,
        "emitted_rows": length,
        "lambda": {
            "coupling_scale_D_T": coupling_scale,
            "final_ledger_residual": audit.lambda_ledger_residual,
            "max_step_residual": max_step_residual,
            "operation_count": operation_count,
            "separation_ratio": separation,
            "tolerance": lambda_tolerance,
        },
        "passed": bool(passed),
        "ring": {
            "max_residual": max_ring_residual,
            "max_residual_to_tolerance": max_ring_ratio,
            "resummation_count": audit.resummation_count,
            "window": window,
        },
        "I_G_max_backward_difference_residual": max_g_residual,
        "unit_roundoff": UNIT_ROUNDOFF,
    }


def ring_mutation() -> dict[str, Any]:
    length = 66_000
    window = 24
    margins: list[float] = []
    ring = [0.0] * window
    ring_pos = 0
    ring_len = 0
    ring_sum = 0.0
    for index in range(length):
        margin = -1.0e16 if index % 25 == 0 else 0.2
        margins.append(margin)
        if ring_len == window:
            ring_sum -= ring[ring_pos]
        else:
            ring_len += 1
        ring_sum += margin
        ring[ring_pos] = margin
        ring_pos = (ring_pos + 1) % window
        width = min(index + 1, window)
        fresh = fresh_sum(margins, width)
        sum_abs_window = sum(abs(value) for value in margins[-width:])
        epoch_rows = (index + 1) % window
        if index + 1 < window:
            epoch_operations = index + 1
            epoch_budget = sum_abs_window
        elif epoch_rows == 0:
            epoch_operations = 0
            epoch_budget = 0.0
        else:
            epoch_operations = 2 * epoch_rows
            epoch_budget = sum(
                abs(margins[changed - window]) + abs(margins[changed])
                for changed in range(index + 1 - epoch_rows, index + 1)
            )
        tolerance = C_G * (
            gamma_n(epoch_operations) * epoch_budget + gamma_n(width) * sum_abs_window
        )
        residual = abs(ring_sum - fresh)
        if residual > tolerance:
            return {"detected": True, "detected_at_emitted_row": index + 1, "residual": residual, "tolerance": tolerance}
    return {"detected": False, "detected_at_emitted_row": None, "residual": None, "tolerance": None}


def coupling_mutation(audit: dict[str, Any]) -> dict[str, Any]:
    residual = float(audit["lambda"]["coupling_scale_D_T"])
    tolerance = float(audit["lambda"]["tolerance"])
    return {
        "detected": abs(residual) > tolerance,
        "omitted_term": "-kappa*h*A_t",
        "protected_identity_residual": residual,
        "tolerance": tolerance,
    }


def run_suite(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, env=env, check=True, capture_output=True, text=True, encoding="utf-8")
    passed_tests = sum(
        int(value) for value in re.findall(r"(\d+) passed", completed.stdout)
    )
    recorded_command = list(command)
    if recorded_command and recorded_command[0] == sys.executable:
        recorded_command[0] = "python"
    return {
        "command": recorded_command,
        "passed_tests": passed_tests,
        "returncode": completed.returncode,
    }


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    python_root = root / "PRAMA-Protokol-py"
    rust_root = root / "PRAMA-Protokol-rs"
    sys.path.insert(0, str(python_root / "src"))
    from prama_protokol.kernel_v3 import KernelConfigV3, KernelV3, project_v3

    python_version = tomllib.loads(
        (python_root / "pyproject.toml").read_text(encoding="utf-8")
    )["project"]["version"]
    rust_version = tomllib.loads(
        (rust_root / "Cargo.toml").read_text(encoding="utf-8")
    )["package"]["version"]
    if python_version != "0.3.0" or rust_version != "0.3.0":
        raise RuntimeError(
            f"public version mismatch: Python={python_version}, Rust={rust_version}"
        )

    test_env = os.environ.copy()
    test_env["PYTHONPATH"] = str(python_root / "src")
    suites = {
        "python": run_suite(
            [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
            python_root,
            test_env,
        ),
        "rust": run_suite(["cargo", "test", "--all-targets", "--quiet"], rust_root),
    }
    cross = cross_language(root, rust_root, project_v3, KernelConfigV3)
    audit = long_audit(KernelV3, KernelConfigV3)
    mutations = {"coupling_omitted": coupling_mutation(audit), "resummation_disabled": ring_mutation()}

    hash_paths = {
        "python_kernel_v3": python_root / "src/prama_protokol/kernel_v3.py",
        "python_init": python_root / "src/prama_protokol/__init__.py",
        "python_manifest": python_root / "pyproject.toml",
        "python_tests_v3": python_root / "tests/test_kernel_v3.py",
        "rust_kernel_v3": rust_root / "src/v3.rs",
        "rust_lib": rust_root / "src/lib.rs",
        "rust_manifest": rust_root / "Cargo.toml",
        "rust_tests_v3": rust_root / "tests/v3_vectors.rs",
        "golden_v1": root / "tests/data/v0_3_golden_vectors_v1.json",
        "golden_v2": root / "tests/data/v0_3_golden_vectors_v2.json",
        "golden_v2_generator": root / "tests/data/generate_v0_3_golden_vectors_v2.py",
        "certification_runner": Path(__file__).resolve(),
        "specification": root / "SPECIFICATION.md",
    }
    passed = (
        audit["passed"]
        and cross["passed"]
        and all(record["returncode"] == 0 for record in suites.values())
        and all(record["detected"] for record in mutations.values())
    )
    artifact = {
        "artifact": "v0_3_0_numeric_recertification",
        "environment": {
            "numpy": np.__version__,
            "platform": platform.platform(),
            "python": platform.python_version(),
            "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        },
        "gates": {
            "cross_language": cross,
            "long_synthetic": audit,
            "mutations": mutations,
            "suites": suites,
        },
        "hashes": {name: sha256(path) for name, path in hash_paths.items()},
        "outcomes_accessed": False,
        "passed": bool(passed),
        "schema": "prama.numeric-recertification.v1",
        "version": {"python": python_version, "rust": rust_version},
    }
    output = root / "results/v0_3_0_numeric_recertification.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(artifact, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"artifact": str(output), "passed": passed, "sha256": sha256(output)}, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
