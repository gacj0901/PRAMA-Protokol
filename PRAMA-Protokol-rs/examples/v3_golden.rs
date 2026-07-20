//! Deterministic v0.3.0 bridge: project frozen JSON vectors and emit Rust rows.

use prama_protokol::v3::{project_v3, GammaRowV3, KernelConfigV3, KernelV3};
use serde_json::{json, Value};
use std::env;
use std::fs;
use std::path::PathBuf;

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
    let mut controls = vec![0.0; inputs.len()];
    for row in vector["expected_rows"].as_array().unwrap() {
        controls[row["source_input_index"].as_u64().unwrap() as usize] = decimal(&row["u_lambda"]);
    }
    let sigma_op = vec![true; inputs.len()];
    (omega, expected, controls, sigma_op)
}

#[allow(non_snake_case)]
fn row_json(row: GammaRowV3) -> Value {
    json!({
        "A": row.A,
        "G": row.G,
        "M": row.M,
        "delta": row.delta,
        "delta_tilde": row.delta_tilde,
        "e": row.e,
        "input_index": row.input_index,
        "lambda": row.lambda,
        "sigma_op": row.sigma_op,
        "state_index": row.state_index,
        "theta": row.theta,
        "u_lambda": row.u_lambda,
        "valid": row.valid,
        "xi": row.xi,
    })
}

fn main() {
    let fixture_name = env::args()
        .nth(1)
        .unwrap_or_else(|| "v0_3_golden_vectors_v1.json".to_string());
    let fixture = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../tests/data")
        .join(fixture_name);
    let document: Value = serde_json::from_slice(&fs::read(fixture).unwrap()).unwrap();
    let cfg = config(&document);
    let mut outputs = Vec::new();

    for vector in document["vectors"].as_array().unwrap() {
        let identifier = vector["id"].as_str().unwrap();
        let (omega, expected, controls, sigma_op) = arrays(vector);
        match project_v3(&omega, &expected, &cfg, Some(&controls), Some(&sigma_op)) {
            Err(error) => outputs.push(json!({
                "error": error.to_string(),
                "id": identifier,
                "rows": [],
                "streaming_bit_exact": true,
            })),
            Ok(batch) => {
                let mut stream = KernelV3::new(cfg).unwrap();
                let mut rows = Vec::new();
                let mut emitted = 0usize;
                let mut exact = true;
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
                        exact &= row.delta == batch.delta[emitted]
                            && row.delta_tilde == batch.delta_tilde[emitted]
                            && row.e == batch.e[emitted]
                            && row.xi == batch.xi[emitted]
                            && row.A == batch.A[emitted]
                            && row.lambda == batch.lambda[emitted]
                            && row.theta == batch.theta[emitted]
                            && row.M == batch.M[emitted]
                            && row.G == batch.G[emitted]
                            && row.u_lambda == batch.u_lambda[emitted]
                            && row.sigma_op == batch.sigma_op[emitted]
                            && row.valid == batch.valid[emitted]
                            && row.input_index == batch.input_index[emitted]
                            && row.state_index == batch.state_index[emitted];
                        rows.push(row_json(row));
                        emitted += 1;
                    }
                }
                exact &= emitted == batch.len();
                outputs.push(json!({
                    "error": null,
                    "id": identifier,
                    "rows": rows,
                    "streaming_bit_exact": exact,
                }));
            }
        }
    }

    println!(
        "{}",
        serde_json::to_string(&json!({"vectors": outputs})).unwrap()
    );
}
