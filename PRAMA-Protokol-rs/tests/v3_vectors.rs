use prama_protokol::v3::{project_v3, GammaV3, KernelConfigV3, KernelV3, V3Error};
use serde_json::Value;
use std::fs;
use std::path::PathBuf;

const ATOL: f64 = 1.0e-14;
const RTOL: f64 = 1.0e-13;
const MAX_ULP: u64 = 64;
const UNIT_ROUNDOFF: f64 = f64::EPSILON / 2.0;
const C_G: f64 = 16.0;
const C_FP: f64 = 16.0;
const R_MIN: f64 = 1.0e3;

fn gamma_n(operations: usize) -> f64 {
    let product = operations as f64 * UNIT_ROUNDOFF;
    product / (1.0 - product)
}

fn fresh_sum(values: &[f64], window: usize) -> f64 {
    let start = values.len().saturating_sub(window);
    let mut total = 0.0;
    for value in &values[start..] {
        total = total + *value;
    }
    total
}

fn adversarial_omega(index: usize) -> f64 {
    let large = 1.0e16 + ((index * 104_729) % 1_000_003) as f64;
    if index % 5 == 0 {
        large
    } else {
        1.0 + (index % 17) as f64
    }
}

fn golden() -> Value {
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../tests/data/v0_3_golden_vectors_v1.json");
    serde_json::from_slice(&fs::read(path).expect("frozen v1 fixture must exist"))
        .expect("frozen v1 fixture must be valid JSON")
}

fn golden_v2() -> Value {
    let path =
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../tests/data/v0_3_golden_vectors_v2.json");
    serde_json::from_slice(&fs::read(path).expect("frozen v2 fixture must exist"))
        .expect("frozen v2 fixture must be valid JSON")
}

fn decimal(value: &Value) -> f64 {
    value.as_str().expect("decimal string").parse().unwrap()
}

fn config(document: &Value) -> KernelConfigV3 {
    let cfg = &document["configuration"];
    KernelConfigV3 {
        h: decimal(&cfg["h"]),
        tau: decimal(&cfg["tau_cert"]),
        theta_scale: decimal(&cfg["theta_scale"]),
        lambda_0: decimal(&cfg["lambda_0"]),
        lambda_min: decimal(&cfg["lambda_min"]),
        lambda_max: decimal(&cfg["lambda_max"]),
        kappa_v3: decimal(&cfg["kappa_cert"]),
        g_smooth: cfg["g_smooth"].as_str().unwrap().parse().unwrap(),
        delta_ref: decimal(&cfg["delta_ref"]),
    }
}

fn arrays(vector: &Value) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<bool>) {
    let inputs = vector["inputs"].as_array().unwrap();
    let omega: Vec<f64> = inputs
        .iter()
        .map(|row| {
            row["omega"]
                .as_str()
                .map_or(f64::NAN, |value| value.parse().unwrap())
        })
        .collect();
    let expected: Vec<f64> = inputs
        .iter()
        .map(|row| {
            row["expected"]
                .as_str()
                .map_or(f64::NAN, |value| value.parse().unwrap())
        })
        .collect();
    let mut controls = vec![0.0; inputs.len()];
    for row in vector["expected_rows"].as_array().unwrap() {
        let source = row["source_input_index"].as_u64().unwrap() as usize;
        controls[source] = decimal(&row["u_lambda"]);
    }
    let sigma_op = vec![true; inputs.len()];
    (omega, expected, controls, sigma_op)
}

fn arrays_v2(vector: &Value) -> (Vec<f64>, Vec<f64>, Vec<f64>, Vec<bool>) {
    let inputs = vector["inputs"].as_array().unwrap();
    let omega = inputs
        .iter()
        .map(|row| {
            row["omega"]
                .as_str()
                .map_or(f64::NAN, |value| value.parse().unwrap())
        })
        .collect();
    let expected = inputs
        .iter()
        .map(|row| {
            row["expected"]
                .as_str()
                .map_or(f64::NAN, |value| value.parse().unwrap())
        })
        .collect();
    let controls = inputs.iter().map(|row| decimal(&row["u_lambda"])).collect();
    let sigma_op = inputs
        .iter()
        .map(|row| row["sigma_op"].as_bool().unwrap())
        .collect();
    (omega, expected, controls, sigma_op)
}

fn ordered_bits(value: f64) -> u64 {
    let bits = value.to_bits();
    if bits & (1u64 << 63) != 0 {
        !bits
    } else {
        bits | (1u64 << 63)
    }
}

fn assert_numeric(actual: f64, expected: f64, label: &str) {
    if expected == 0.0 {
        assert!(actual.abs() <= ATOL, "{label}: zero rule failed: {actual}");
        return;
    }
    let difference = (actual - expected).abs();
    assert!(
        difference <= ATOL.max(RTOL * expected.abs()),
        "{label}: isclose failed: {actual} != {expected}"
    );
    let ulp = ordered_bits(actual).abs_diff(ordered_bits(expected));
    assert!(ulp <= MAX_ULP, "{label}: {ulp} ULP > {MAX_ULP}");
}

fn float_column<'a>(gamma: &'a GammaV3, field: &str) -> &'a [f64] {
    match field {
        "delta" => &gamma.delta,
        "delta_tilde" => &gamma.delta_tilde,
        "e" => &gamma.e,
        "xi" => &gamma.xi,
        "A" => &gamma.A,
        "lambda" => &gamma.lambda,
        "theta" => &gamma.theta,
        "M" => &gamma.M,
        "G" => &gamma.G,
        "u_lambda" => &gamma.u_lambda,
        _ => panic!("unknown field {field}"),
    }
}

fn assert_against_golden(gamma: &GammaV3, vector: &Value, cfg: &KernelConfigV3) {
    let rows = vector["expected_rows"].as_array().unwrap();
    assert_eq!(gamma.len(), rows.len());
    let fields = [
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
    ];
    for (index, expected) in rows.iter().enumerate() {
        for field in fields {
            assert_numeric(
                float_column(gamma, field)[index],
                decimal(&expected[field]),
                &format!("{}[{index}].{field}", vector["id"].as_str().unwrap()),
            );
        }
        assert_eq!(
            gamma.sigma_op[index],
            expected["sigma_op"].as_bool().unwrap()
        );
        assert_eq!(gamma.valid[index], expected["valid"].as_bool().unwrap());
        assert_eq!(
            gamma.input_index[index],
            expected["input_index"].as_u64().unwrap() as usize
        );
        assert_eq!(
            gamma.state_index[index],
            expected["state_index"].as_u64().unwrap() as usize
        );
        assert_eq!(gamma.e[index] > 0.0, decimal(&expected["e"]) > 0.0);
        assert_eq!(gamma.M[index] < 0.0, decimal(&expected["M"]) < 0.0);
        assert_eq!(gamma.G[index] < 0.0, decimal(&expected["G"]) < 0.0);
        assert_eq!(
            gamma.lambda[index] == cfg.lambda_min,
            decimal(&expected["lambda"]) == cfg.lambda_min
        );
    }
}

#[test]
fn v01_v11_match_frozen_decimal_json() {
    let document = golden();
    let cfg = config(&document);
    for vector in document["vectors"].as_array().unwrap() {
        let identifier = vector["id"].as_str().unwrap();
        let (omega, expected, controls, sigma_op) = arrays(vector);
        if identifier == "V10_INTERNAL_MISSING" {
            assert_eq!(
                project_v3(&omega, &expected, &cfg, Some(&controls), Some(&sigma_op)),
                Err(V3Error::InternalMissingAfterStart)
            );
            continue;
        }
        let gamma = project_v3(&omega, &expected, &cfg, Some(&controls), Some(&sigma_op))
            .expect("valid v1 vector");
        assert_against_golden(&gamma, vector, &cfg);
    }
}

#[test]
fn v030_v2_matches_independent_decimal_json() {
    let document = golden_v2();
    assert_eq!(
        document["schema"].as_str().unwrap(),
        "prama.v0_3.golden_vectors.v2"
    );
    assert!(!document["oracle"]["imports_production_kernel"]
        .as_bool()
        .unwrap());
    let cfg = config(&document);
    for vector in document["vectors"].as_array().unwrap() {
        let (omega, expected, controls, sigma_op) = arrays_v2(vector);
        let gamma = project_v3(&omega, &expected, &cfg, Some(&controls), Some(&sigma_op))
            .expect("valid v2 vector");
        assert_against_golden(&gamma, vector, &cfg);
    }
}

#[test]
fn batch_and_streaming_are_bit_exact_for_every_successful_vector() {
    let document = golden();
    let cfg = config(&document);
    for vector in document["vectors"].as_array().unwrap() {
        if vector["id"].as_str().unwrap() == "V10_INTERNAL_MISSING" {
            continue;
        }
        let (omega, expected, controls, sigma_op) = arrays(vector);
        let batch = project_v3(&omega, &expected, &cfg, Some(&controls), Some(&sigma_op)).unwrap();
        let mut stream = KernelV3::new(cfg).unwrap();
        let mut emitted = 0usize;
        for source in 0..omega.len() {
            if let Some(row) = stream
                .step(
                    omega[source],
                    expected[source],
                    controls[source],
                    Some(sigma_op[source]),
                )
                .unwrap()
            {
                assert_eq!(row.delta, batch.delta[emitted]);
                assert_eq!(row.delta_tilde, batch.delta_tilde[emitted]);
                assert_eq!(row.e, batch.e[emitted]);
                assert_eq!(row.xi, batch.xi[emitted]);
                assert_eq!(row.A, batch.A[emitted]);
                assert_eq!(row.lambda, batch.lambda[emitted]);
                assert_eq!(row.theta, batch.theta[emitted]);
                assert_eq!(row.M, batch.M[emitted]);
                assert_eq!(row.G, batch.G[emitted]);
                assert_eq!(row.u_lambda, batch.u_lambda[emitted]);
                assert_eq!(row.sigma_op, batch.sigma_op[emitted]);
                assert_eq!(row.valid, batch.valid[emitted]);
                assert_eq!(row.input_index, batch.input_index[emitted]);
                assert_eq!(row.state_index, batch.state_index[emitted]);
                emitted += 1;
            }
        }
        assert_eq!(emitted, batch.len());
    }
}

#[test]
fn fail_closed_errors_do_not_mutate_stream_state() {
    let cfg = config(&golden());
    let mut tested = KernelV3::new(cfg).unwrap();
    let first = tested.step(3.0, 1.0, 0.0, Some(true)).unwrap();
    assert_eq!(
        tested.step(0.0, f64::NAN, 0.0, Some(true)),
        Err(V3Error::InternalMissingAfterStart)
    );
    let second = tested.step(3.0, 1.0, 0.0, Some(true)).unwrap();

    let mut clean = KernelV3::new(cfg).unwrap();
    assert_eq!(first, clean.step(3.0, 1.0, 0.0, Some(true)).unwrap());
    assert_eq!(second, clean.step(3.0, 1.0, 0.0, Some(true)).unwrap());

    assert!(matches!(
        project_v3(&[1.0], &[-1.0], &cfg, None, None),
        Err(V3Error::InvalidInput(_))
    ));
    assert!(matches!(
        project_v3(&[1.0], &[1.0], &cfg, Some(&[-0.1]), None),
        Err(V3Error::InvalidInput(_))
    ));
    assert!(matches!(
        project_v3(&[-1.0e308], &[1.0e308], &cfg, None, None),
        Err(V3Error::InvalidInput("non-finite arithmetic result"))
    ));
}

#[test]
fn v030_ring_schedule_warmup_and_boundaries() {
    for window in [1usize, 2, 24, 64] {
        let cfg = KernelConfigV3 {
            g_smooth: window,
            ..Default::default()
        };
        let mut lengths = vec![
            window.saturating_sub(1).max(1),
            window,
            window + 1,
            2 * window - 1,
            2 * window,
            2 * window + 1,
        ];
        lengths.sort_unstable();
        lengths.dedup();
        for length in lengths {
            let mut kernel = KernelV3::new(cfg).unwrap();
            let mut margins = Vec::new();
            let mut previous_smooth = None;
            for index in 0..length {
                let row = kernel
                    .step(adversarial_omega(index), 0.0, 0.0, Some(true))
                    .unwrap()
                    .unwrap();
                margins.push(row.M);
                let audit = kernel.numeric_audit();
                let width = (index + 1).min(window);
                let fresh = fresh_sum(&margins, width);
                assert_eq!(audit.emitted_count, index + 1);
                assert_eq!(audit.ring_len, width);
                assert_eq!(audit.resummation_count, (index + 1) / window);
                assert_eq!(audit.smooth_m, Some(audit.ring_sum / width as f64));
                if (index + 1) % window == 0 {
                    assert_eq!(audit.ring_sum, fresh);
                }
                match previous_smooth {
                    None => assert_eq!(row.G, 0.0),
                    Some(previous) => assert_eq!(row.G, audit.smooth_m.unwrap() - previous),
                }
                previous_smooth = audit.smooth_m;
            }
        }
    }
}

#[test]
fn v030_long_stream_ring_and_lambda_ledgers() {
    let length = 66_000usize;
    let window = 24usize;
    let cfg = KernelConfigV3 {
        tau: 0.01,
        g_smooth: window,
        ..Default::default()
    };
    let mut kernel = KernelV3::new(cfg).unwrap();
    let mut margins = Vec::with_capacity(length);
    let mut sum_abs_a = 0.0;
    let mut sum_abs_u = 0.0;
    let mut sum_abs_pi = 0.0;
    let mut coupling_scale = 0.0;
    let mut previous_lambda = cfg.lambda_0;
    let mut max_ring_residual: f64 = 0.0;
    let mut max_ring_ratio: f64 = 0.0;

    for index in 0..length {
        let u_value = if index % 257 == 0 { 2.5e-7 } else { 0.0 };
        let row = kernel
            .step(adversarial_omega(index), 0.0, u_value, Some(true))
            .unwrap()
            .unwrap();
        margins.push(row.M);
        let audit = kernel.numeric_audit();
        let width = (index + 1).min(window);
        let fresh = fresh_sum(&margins, width);
        let residual = (audit.ring_sum - fresh).abs();
        let sum_abs_window: f64 = margins[margins.len() - width..]
            .iter()
            .map(|value| value.abs())
            .sum();
        let epoch_rows = (index + 1) % window;
        let (epoch_operations, epoch_budget) = if index + 1 < window {
            (index + 1, sum_abs_window)
        } else if epoch_rows == 0 {
            (0, 0.0)
        } else {
            let epoch_start = index + 1 - epoch_rows;
            let mut budget = 0.0;
            for changed in epoch_start..=index {
                budget += margins[changed - window].abs() + margins[changed].abs();
            }
            (2 * epoch_rows, budget)
        };
        let tolerance =
            C_G * (gamma_n(epoch_operations) * epoch_budget + gamma_n(width) * sum_abs_window);
        max_ring_residual = max_ring_residual.max(residual);
        max_ring_ratio = max_ring_ratio.max(if tolerance == 0.0 {
            0.0
        } else {
            residual / tolerance
        });
        assert!(residual <= tolerance);

        let lambda_raw = previous_lambda - cfg.kappa_v3 * cfg.h * row.A + cfg.h * u_value;
        let pi = row.lambda - lambda_raw;
        sum_abs_a += row.A.abs();
        sum_abs_u += u_value.abs();
        sum_abs_pi += pi.abs();
        coupling_scale += cfg.kappa_v3 * cfg.h * row.A;
        previous_lambda = row.lambda;
    }

    let audit = kernel.numeric_audit();
    let operation_count = 3 * length + 12;
    let scale = previous_lambda.abs()
        + cfg.lambda_0.abs()
        + cfg.kappa_v3 * cfg.h * sum_abs_a
        + cfg.h * sum_abs_u
        + sum_abs_pi;
    let lambda_tolerance = C_FP * gamma_n(operation_count) * scale;
    let separation = coupling_scale / lambda_tolerance;
    assert_eq!(audit.resummation_count, length / window);
    assert!(max_ring_residual > 0.0);
    assert!(max_ring_ratio <= 1.0);
    assert!(audit.lambda_ledger_residual.abs() <= lambda_tolerance);
    assert!(separation >= R_MIN);
    assert!(coupling_scale > lambda_tolerance);
}

#[test]
fn v030_disabled_resummation_mutation_is_detected() {
    let length = 66_000usize;
    let window = 24usize;
    let mut margins = Vec::with_capacity(length);
    let mut ring = vec![0.0; window];
    let mut ring_pos = 0usize;
    let mut ring_len = 0usize;
    let mut ring_sum = 0.0;
    let mut detected_at = None;

    for index in 0..length {
        let margin = if index % 25 == 0 { -1.0e16 } else { 0.2 };
        margins.push(margin);
        if ring_len == window {
            ring_sum -= ring[ring_pos];
        } else {
            ring_len += 1;
        }
        ring_sum += margin;
        ring[ring_pos] = margin;
        ring_pos = (ring_pos + 1) % window;

        let width = (index + 1).min(window);
        let fresh = fresh_sum(&margins, width);
        let sum_abs_window: f64 = margins[margins.len() - width..]
            .iter()
            .map(|value| value.abs())
            .sum();
        let epoch_rows = (index + 1) % window;
        let (epoch_operations, epoch_budget) = if index + 1 < window {
            (index + 1, sum_abs_window)
        } else if epoch_rows == 0 {
            (0, 0.0)
        } else {
            let epoch_start = index + 1 - epoch_rows;
            let mut budget = 0.0;
            for changed in epoch_start..=index {
                budget += margins[changed - window].abs() + margins[changed].abs();
            }
            (2 * epoch_rows, budget)
        };
        let tolerance =
            C_G * (gamma_n(epoch_operations) * epoch_budget + gamma_n(width) * sum_abs_window);
        if (ring_sum - fresh).abs() > tolerance {
            detected_at = Some(index + 1);
            break;
        }
    }
    assert!(detected_at.is_some());
    assert!(detected_at.unwrap() <= length);
}
