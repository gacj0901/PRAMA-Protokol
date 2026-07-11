use prama_protokol::{project, Kernel, KernelConfig};

#[test]
fn p4_recovery_never_modifies_xi() {
    // shock, then ω == ω̂ (Δ = 0): Ξ decays purely by its kernel while λ recovers
    let n = 3000;
    let mut omega = vec![8.0; 200];
    omega.extend(vec![1.0; n - 200]);
    let expected = vec![1.0; n];
    let cfg = KernelConfig {
        tau_memory: 30.0,
        ..Default::default()
    };
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
fn streaming_matches_batch_completely() {
    let n = 5000;
    let omega: Vec<f64> = (0..n).map(|i| 1.0 + ((i % 31) as f64) * 0.07).collect();
    let expected: Vec<f64> = (0..n)
        .map(|i| {
            if i < 50 {
                f64::NAN
            } else {
                2.0 + ((i % 7) as f64) * 0.01
            }
        })
        .collect();
    let cfg = KernelConfig::default();
    let batch = project(&omega, &expected, &cfg, None);
    let mut k = Kernel::new(cfg);
    for i in 0..n {
        let s = k.step(omega[i], expected[i], None);
        assert!((s.xi - batch.xi[i]).abs() < 1e-15, "xi at {}", i);
        assert!(
            (s.lambda - batch.lambda[i]).abs() < 1e-15,
            "lambda at {}",
            i
        );
        assert!((s.theta - batch.theta[i]).abs() < 1e-15, "theta at {}", i);
        assert!((s.m - batch.m[i]).abs() < 1e-15, "M at {}", i);
        assert!((s.g - batch.g[i]).abs() < 1e-15, "G at {}", i);
        assert_eq!(
            s.latent_collapse, batch.latent_collapse[i],
            "latent at {}",
            i
        );
        assert_eq!(s.stratum, batch.stratum[i], "stratum at {}", i);
        assert_eq!(s.valid, batch.valid[i], "valid at {}", i);
    }
}

#[test]
fn prefix_causality_and_edges() {
    for &window in &[1usize, 64] {
        let cfg = KernelConfig {
            g_smooth: window,
            ..Default::default()
        };
        assert!(project(&[], &[], &cfg, None).g.is_empty());
        let one = project(&[1.0], &[f64::NAN], &cfg, None);
        assert_eq!(one.g, vec![0.0]);
        assert_eq!(one.valid, vec![false]);

        let omega = vec![1.0, 3.0, 0.5, 5.0, 1.0];
        let expected = vec![f64::NAN, f64::NAN, 2.0, 1.0, 2.0];
        let a = project(&omega, &expected, &cfg, None);
        let mut changed_o = omega.clone();
        let mut changed_e = expected.clone();
        changed_o[4] = 999.0;
        changed_e[4] = 0.01;
        let b = project(&changed_o, &changed_e, &cfg, None);
        for i in 0..4 {
            assert_eq!(a.delta[i], b.delta[i]);
            assert_eq!(a.xi[i], b.xi[i]);
            assert_eq!(a.lambda[i], b.lambda[i]);
            assert_eq!(a.theta[i], b.theta[i]);
            assert_eq!(a.m[i], b.m[i]);
            assert_eq!(a.g[i], b.g[i]);
            assert_eq!(a.latent_collapse[i], b.latent_collapse[i]);
            assert_eq!(a.stratum[i], b.stratum[i]);
            assert_eq!(a.valid[i], b.valid[i]);
        }
    }
}
