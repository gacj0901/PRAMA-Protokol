"""Public certification tests for the PRAMA Protokol v0.3.0 kernel."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct

import numpy as np
import pytest

from prama_protokol.kernel_v3 import (
    GammaV3,
    KernelConfigV3,
    KernelV3,
    V3ProjectionError,
    project_v3,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = REPO_ROOT / "tests/data/v0_3_golden_vectors_v1.json"
GOLDEN_SHA256 = "582ceb787df876ad5ca9793929f88a5e5843a667e3c7477e7671e30bd67461f3"
GOLDEN_V2_PATH = REPO_ROOT / "tests/data/v0_3_golden_vectors_v2.json"
GOLDEN_V2_SHA256 = "135cea771adf656201c08f34dd0c2cb9a7fd51ee3c120ab937141ee513dae1e0"
FLOAT_FIELDS = (
    "delta",
    "delta_tilde",
    "e",
    "xi",
    "A",
    "lambda",
    "theta",
    "M",
    "G",
    "u_lambda",
)
ATOL = 1.0e-14
RTOL = 1.0e-13
MAX_ULP = 64
UNIT_ROUNDOFF = 2.0**-53
C_G = 16.0
C_FP = 16.0
R_MIN = 1.0e3


def _load_golden() -> dict:
    raw = GOLDEN_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_SHA256
    return json.loads(raw)


GOLDEN = _load_golden()
VECTORS = {vector["id"]: vector for vector in GOLDEN["vectors"]}


def _config() -> KernelConfigV3:
    cfg = GOLDEN["configuration"]
    return KernelConfigV3(
        h=float(cfg["h"]),
        tau=float(cfg["tau_cert"]),
        theta_scale=float(cfg["theta_scale"]),
        lambda_0=float(cfg["lambda_0"]),
        lambda_min=float(cfg["lambda_min"]),
        lambda_max=float(cfg["lambda_max"]),
        kappa_v3=float(cfg["kappa_cert"]),
        g_smooth=int(cfg["g_smooth"]),
        delta_ref=float(cfg["delta_ref"]),
    )


def _source_arrays(vector: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    omega = np.asarray(
        [math.nan if row["omega"] is None else float(row["omega"]) for row in vector["inputs"]],
        dtype=np.float64,
    )
    expected = np.asarray(
        [
            math.nan if row["expected"] is None else float(row["expected"])
            for row in vector["inputs"]
        ],
        dtype=np.float64,
    )
    controls = np.zeros(len(omega), dtype=np.float64)
    for row in vector["expected_rows"]:
        controls[int(row["source_input_index"])] = float(row["u_lambda"])
    sigma_op = np.ones(len(omega), dtype=np.bool_)
    return omega, expected, controls, sigma_op


def _ordered_bits(value: float) -> int:
    signed = struct.unpack(">q", struct.pack(">d", value))[0]
    return 0x8000_0000_0000_0000 - signed if signed < 0 else signed


def _assert_numeric(actual: float, expected: float, label: str) -> None:
    if expected == 0.0:
        assert abs(actual) <= ATOL, f"{label}: zero rule failed: {actual}"
        return
    assert math.isclose(actual, expected, rel_tol=RTOL, abs_tol=ATOL), (
        f"{label}: isclose failed: {actual} != {expected}"
    )
    ulp = abs(_ordered_bits(actual) - _ordered_bits(expected))
    assert ulp <= MAX_ULP, f"{label}: {ulp} ULP > {MAX_ULP}"


def _assert_gamma_matches_golden(gamma: GammaV3, vector: dict) -> None:
    expected_rows = vector["expected_rows"]
    assert len(gamma) == len(expected_rows)
    actual = gamma.as_dict()
    for i, expected_row in enumerate(expected_rows):
        for field in FLOAT_FIELDS:
            _assert_numeric(
                float(actual[field][i]),
                float(expected_row[field]),
                f"{vector['id']}[{i}].{field}",
            )
        assert bool(actual["sigma_op"][i]) is bool(expected_row["sigma_op"])
        assert bool(actual["valid"][i]) is bool(expected_row["valid"])
        assert int(actual["input_index"][i]) == int(expected_row["input_index"])
        assert int(actual["state_index"][i]) == int(expected_row["state_index"])
        assert bool(actual["e"][i] > 0.0) is (float(expected_row["e"]) > 0.0)
        assert bool(actual["M"][i] < 0.0) is (float(expected_row["M"]) < 0.0)
        assert bool(actual["G"][i] < 0.0) is (float(expected_row["G"]) < 0.0)
        assert bool(actual["lambda"][i] == _config().lambda_min) is (
            float(expected_row["lambda"]) == _config().lambda_min
        )


def _gamma_n(operations: int) -> float:
    product = operations * UNIT_ROUNDOFF
    return product / (1.0 - product)


def _fresh_sum(values: list[float], window: int) -> float:
    total = 0.0
    for value in values[-window:]:
        total = total + value
    return total


def _adversarial_omega(index: int) -> float:
    large = 1.0e16 + float((index * 104_729) % 1_000_003)
    return large if index % 5 == 0 else 1.0 + float(index % 17)


@pytest.mark.parametrize(
    "vector_id",
    [identifier for identifier in VECTORS if identifier != "V10_INTERNAL_MISSING"],
)
def test_v01_v11_against_frozen_decimal_json(vector_id: str) -> None:
    vector = VECTORS[vector_id]
    omega, expected, controls, sigma_op = _source_arrays(vector)
    gamma = project_v3(omega, expected, _config(), controls, sigma_op)
    _assert_gamma_matches_golden(gamma, vector)


@pytest.mark.parametrize(
    "vector_id",
    [identifier for identifier in VECTORS if identifier != "V10_INTERNAL_MISSING"],
)
def test_batch_and_streaming_are_bit_exact(vector_id: str) -> None:
    vector = VECTORS[vector_id]
    omega, expected, controls, sigma_op = _source_arrays(vector)
    batch = project_v3(omega, expected, _config(), controls, sigma_op)
    stream = KernelV3(_config())
    rows = []
    for i in range(len(omega)):
        row = stream.step(omega[i], expected[i], controls[i], sigma_op[i])
        if row is not None:
            rows.append(row)
    streamed = GammaV3.from_rows(rows)
    assert batch.as_dict().keys() == streamed.as_dict().keys()
    for field, values in batch.as_dict().items():
        assert np.array_equal(values, streamed.as_dict()[field]), field


def test_v10_internal_missing_fails_closed_without_state_mutation() -> None:
    vector = VECTORS["V10_INTERNAL_MISSING"]
    omega, expected, controls, sigma_op = _source_arrays(vector)
    with pytest.raises(V3ProjectionError, match="internal_missing_after_start"):
        project_v3(omega, expected, _config(), controls, sigma_op)

    tested = KernelV3(_config())
    first = tested.step(omega[0], expected[0], 0.0, True)
    with pytest.raises(V3ProjectionError, match="internal_missing_after_start"):
        tested.step(omega[1], expected[1], 0.0, True)
    second_after_error = tested.step(omega[2], expected[2], 0.0, True)

    clean = KernelV3(_config())
    clean_first = clean.step(omega[0], expected[0], 0.0, True)
    clean_second = clean.step(omega[2], expected[2], 0.0, True)
    assert first == clean_first
    assert second_after_error == clean_second


def test_v030_decimal_v2_oracle_and_generator_are_frozen() -> None:
    raw = GOLDEN_V2_PATH.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == GOLDEN_V2_SHA256
    document = json.loads(raw)
    assert document["schema"] == "prama.v0_3.golden_vectors.v2"
    assert document["oracle"]["imports_production_kernel"] is False

    generator_path = GOLDEN_V2_PATH.with_name("generate_v0_3_golden_vectors_v2.py")
    spec = importlib.util.spec_from_file_location("v030_decimal_oracle", generator_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    regenerated = (
        json.dumps(
            module.document(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    assert regenerated == raw

    raw_cfg = document["configuration"]
    cfg = KernelConfigV3(
        h=float(raw_cfg["h"]),
        tau=float(raw_cfg["tau_cert"]),
        theta_scale=float(raw_cfg["theta_scale"]),
        lambda_0=float(raw_cfg["lambda_0"]),
        lambda_min=float(raw_cfg["lambda_min"]),
        lambda_max=float(raw_cfg["lambda_max"]),
        kappa_v3=float(raw_cfg["kappa_cert"]),
        g_smooth=int(raw_cfg["g_smooth"]),
        delta_ref=float(raw_cfg["delta_ref"]),
    )
    for vector in document["vectors"]:
        omega = np.asarray(
            [math.nan if row["omega"] is None else float(row["omega"]) for row in vector["inputs"]]
        )
        expected = np.asarray(
            [
                math.nan if row["expected"] is None else float(row["expected"])
                for row in vector["inputs"]
            ]
        )
        controls = np.asarray([float(row["u_lambda"]) for row in vector["inputs"]])
        sigma_op = np.asarray([bool(row["sigma_op"]) for row in vector["inputs"]])
        gamma = project_v3(omega, expected, cfg, controls, sigma_op)
        assert len(gamma) == len(vector["expected_rows"])
        actual = gamma.as_dict()
        for index, expected_row in enumerate(vector["expected_rows"]):
            for field in FLOAT_FIELDS:
                _assert_numeric(
                    float(actual[field][index]),
                    float(expected_row[field]),
                    f"{vector['id']}[{index}].{field}",
                )
            for field in ("sigma_op", "valid", "input_index", "state_index"):
                assert actual[field][index] == expected_row[field]


def test_fail_closed_validation() -> None:
    cfg = _config()
    with pytest.raises(V3ProjectionError, match="non-empty"):
        project_v3(np.array([]), np.array([]), cfg)
    with pytest.raises(V3ProjectionError, match="same shape"):
        project_v3(np.array([1.0]), np.array([1.0, 1.0]), cfg)
    with pytest.raises(V3ProjectionError, match="omega must be finite"):
        project_v3(np.array([math.inf]), np.array([1.0]), cfg)
    with pytest.raises(V3ProjectionError, match="expected must be >= 0"):
        project_v3(np.array([1.0]), np.array([-1.0]), cfg)
    with pytest.raises(V3ProjectionError, match="u_lambda"):
        project_v3(np.array([1.0]), np.array([1.0]), cfg, np.array([-0.1]))
    with pytest.raises(V3ProjectionError, match="non-finite arithmetic"):
        project_v3(np.array([-1.0e308]), np.array([1.0e308]), cfg)
    with pytest.raises(V3ProjectionError, match="no_valid_rows"):
        project_v3(np.array([1.0, 1.0]), np.array([math.nan, math.nan]), cfg)
    with pytest.raises(V3ProjectionError, match="delta_ref"):
        KernelConfigV3(delta_ref=0.0)


@pytest.mark.parametrize("window", [1, 2, 24, 64])
def test_v030_ring_schedule_warmup_and_boundaries(window: int) -> None:
    cfg = KernelConfigV3(g_smooth=window)
    lengths = sorted({max(1, window - 1), window, window + 1, 2 * window - 1, 2 * window, 2 * window + 1})
    for length in lengths:
        kernel = KernelV3(cfg)
        margins: list[float] = []
        previous_smooth: float | None = None
        for index in range(length):
            row = kernel.step(_adversarial_omega(index), 0.0, 0.0, True)
            assert row is not None
            margins.append(row.M)
            audit = kernel.numeric_audit
            width = min(index + 1, window)
            fresh = _fresh_sum(margins, width)
            assert audit.emitted_count == index + 1
            assert audit.ring_len == width
            assert audit.resummation_count == (index + 1) // window
            assert audit.smooth_m == audit.ring_sum / width
            if (index + 1) % window == 0:
                assert audit.ring_sum == fresh
            if previous_smooth is None:
                assert row.G == 0.0
            else:
                assert row.G == audit.smooth_m - previous_smooth
            previous_smooth = audit.smooth_m


def test_v030_long_stream_ledgers_and_mutations() -> None:
    length = 66_000
    window = 24
    cfg = KernelConfigV3(g_smooth=window, tau=0.01)
    kernel = KernelV3(cfg)
    margins: list[float] = []
    sum_abs_A = 0.0
    sum_abs_u = 0.0
    sum_abs_pi = 0.0
    coupling_scale = 0.0
    previous_lambda = cfg.lambda_0
    max_ring_residual = 0.0
    max_ring_ratio = 0.0

    for index in range(length):
        u_value = 2.5e-7 if index % 257 == 0 else 0.0
        row = kernel.step(_adversarial_omega(index), 0.0, u_value, True)
        assert row is not None
        margins.append(row.M)
        audit = kernel.numeric_audit
        width = min(index + 1, window)
        fresh = _fresh_sum(margins, width)
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
            epoch_budget = 0.0
            epoch_start = index + 1 - epoch_rows
            for changed in range(epoch_start, index + 1):
                epoch_budget += abs(margins[changed - window]) + abs(margins[changed])
        tolerance = C_G * (
            _gamma_n(epoch_operations) * epoch_budget
            + _gamma_n(width) * sum_abs_window
        )
        max_ring_residual = max(max_ring_residual, residual)
        max_ring_ratio = max(max_ring_ratio, 0.0 if tolerance == 0.0 else residual / tolerance)
        assert residual <= tolerance

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
    lambda_tolerance = C_FP * _gamma_n(operation_count) * scale
    separation = coupling_scale / lambda_tolerance
    assert audit.resummation_count == length // window
    assert max_ring_residual > 0.0
    assert max_ring_ratio <= 1.0
    assert abs(audit.lambda_ledger_residual) <= lambda_tolerance
    assert separation >= R_MIN

    # Omitting -kappa*h*A makes the protected identity miss by D_T. This is
    # the preregistered coupling mutation, evaluated only after distinguishability.
    assert coupling_scale > lambda_tolerance


def test_v030_disabled_resummation_mutation_is_detected() -> None:
    length = 66_000
    window = 24
    margins: list[float] = []
    mutant_ring = [0.0] * window
    mutant_pos = 0
    mutant_len = 0
    mutant_sum = 0.0
    detected_at: int | None = None

    # A large negative margin every 25 rows is admissible for M=theta-xi;
    # the intervening +0.2 values model the lambda-floor ceiling. The 25/24
    # phase drift eventually places a full-small window on a rebase boundary,
    # where an indefinitely incremental sum cannot hide behind a large scale.
    for index in range(length):
        margin = -1.0e16 if index % 25 == 0 else 0.2
        margins.append(margin)
        if mutant_len == window:
            mutant_sum -= mutant_ring[mutant_pos]
        else:
            mutant_len += 1
        mutant_sum += margin
        mutant_ring[mutant_pos] = margin
        mutant_pos = (mutant_pos + 1) % window

        width = min(index + 1, window)
        fresh = _fresh_sum(margins, width)
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
            epoch_budget = 0.0
            epoch_start = index + 1 - epoch_rows
            for changed in range(epoch_start, index + 1):
                epoch_budget += abs(margins[changed - window]) + abs(margins[changed])
        tolerance = C_G * (
            _gamma_n(epoch_operations) * epoch_budget
            + _gamma_n(width) * sum_abs_window
        )
        if abs(mutant_sum - fresh) > tolerance:
            detected_at = index + 1
            break

    assert detected_at is not None
    assert detected_at <= length
