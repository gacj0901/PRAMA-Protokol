use prama_protokol::{project, Kernel, KernelConfig};

#[test]
fn p4_recovery_never_modifies_xi() {
    // shock, then ω == ω̂ (Δ = 0): Ξ decays purely by its kernel while λ recovers
    let n = 3000;
    let mut omega = vec![8.0; 200];
    omega.extend(vec![1.0; n - 200]);
    let expected = vec![1.0; n];
    let cfg = KernelConfig { tau_memory: 30.0, ..Default::default() };
    let g = project(&omega, &expected, &cfg, None);
    let a = (-1.0f64 / 30.0).exp();
    let start = 205;
    for i in start..n {
        let pred = g.xi[start - 1] * a.powi((i - (start - 1)) as i32);
        assert!((g.xi[i] - pred).abs() < 1e-10, "xi deviated at {}", i);
    }
    let lam_min = g.lambda.iter().cloned().fold(f64::INFINITY, f64::min);
    assert!(g.lambda[n - 1] > lam_min, "lambda did not recover");
}

#[test]
fn stratification_quadrants() {
    use prama_protokol::stratify_one;
    assert_eq!(stratify_one(1.0, 1.0), 1);
    assert_eq!(stratify_one(1.0, -1.0), 2);
    assert_eq!(stratify_one(-1.0, 1.0), 3);
    assert_eq!(stratify_one(-1.0, -1.0), 4);
}

#[test]
fn streaming_matches_batch_on_state_coordinates() {
    // step() must reproduce batch xi/lambda/theta/M exactly; G differs by
    // design (backward difference vs central) and is excluded here.
    let n = 5000;
    let omega: Vec<f64> = (0..n).map(|i| 1.0 + ((i % 31) as f64) * 0.07).collect();
    let expected: Vec<f64> = (0..n)
        .map(|i| if i < 50 { f64::NAN } else { 2.0 + ((i % 7) as f64) * 0.01 })
        .collect();
    let cfg = KernelConfig::default();
    let batch = project(&omega, &expected, &cfg, None);
    let mut k = Kernel::new(cfg);
    for i in 0..n {
        let s = k.step(omega[i], expected[i], None);
        assert!((s.xi - batch.xi[i]).abs() < 1e-15, "xi at {}", i);
        assert!((s.lambda - batch.lambda[i]).abs() < 1e-15, "lambda at {}", i);
        assert!((s.theta - batch.theta[i]).abs() < 1e-15, "theta at {}", i);
        assert!((s.m - batch.m[i]).abs() < 1e-15, "M at {}", i);
        assert_eq!(s.valid, batch.valid[i], "valid at {}", i);
    }
}
