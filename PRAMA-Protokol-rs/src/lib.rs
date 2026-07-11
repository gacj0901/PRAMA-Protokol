//! PRAMA Protokol — Reference Kernel (π), Rust production core.
//!
//! Universal aptadynamic projection:  Ω → Γ(t) = (Δ, Ξ, λ, Θ, M, G).
//!
//! This is an **operation-for-operation replica** of the certified Python
//! kernel (`prama-protokol` v0.2.0), with unified causal batch/streaming G.
//! code that produced the BPA/NYISO empirical validation. Every arithmetic
//! step follows the same order as the reference so that results agree to
//! near machine precision (see EQUIVALENCE-RS.md; the only tolerated
//! divergence source is the platform `exp` in the kernel constant).
//!
//! Domain-blind by construction (AS-1 P7): inputs are two bare f64 slices
//! (the observable stream ω and its strictly causal expectation ω̂, NaN on
//! warm-up rows). No domain knowledge exists or may be added here.
//!
//! Streaming note: `Kernel::step` exposes the O(1) per-bin update for
//! always-on production monitors; `project` is the batch form.

/// Universal kernel parameters (fixed across domains — AS-1 C5).
/// Defaults are the validated configuration, in bins.
#[derive(Clone, Copy, Debug)]
pub struct KernelConfig {
    pub tau_memory: f64,      // bins: memory scale of Ξ
    pub lambda_eq: f64,       // permissivity equilibrium
    pub lambda_recovery: f64, // bounded recovery rate r (P4)
    pub lambda_min: f64,      // floor of permissivity
    pub theta_scale: f64,     // Θ(λ) = theta_scale · λ
    pub g_smooth: usize,      // bins: smoothing window for D⁺M
    pub kappa: f64,           // erosion coefficient of λ by excess
}

impl Default for KernelConfig {
    fn default() -> Self {
        Self {
            tau_memory: 24.0 * 14.0,
            lambda_eq: 1.0,
            lambda_recovery: 0.005,
            lambda_min: 0.1,
            theta_scale: 2.0,
            g_smooth: 24,
            kappa: 0.05,
        }
    }
}

/// Γ trajectory (column-major, one Vec per coordinate).
#[derive(Debug, Default)]
pub struct Gamma {
    pub delta: Vec<f64>,
    pub xi: Vec<f64>,
    pub lambda: Vec<f64>,
    pub theta: Vec<f64>,
    pub m: Vec<f64>,
    pub g: Vec<f64>,
    pub latent_collapse: Vec<bool>,
    pub stratum: Vec<u8>,
    pub valid: Vec<bool>,
}

/// Batch projection. `sigma_op`: optional operational indicator; defaults to ω > 0.
pub fn project(
    omega: &[f64],
    expected: &[f64],
    cfg: &KernelConfig,
    sigma_op: Option<&[bool]>,
) -> Gamma {
    assert_eq!(omega.len(), expected.len(), "omega and expected must match");
    let n = omega.len();

    // Δ — exactly the reference formula on valid rows, 0.0 elsewhere
    let mut valid = vec![false; n];
    let mut delta = vec![0.0f64; n];
    for i in 0..n {
        if !expected[i].is_nan() {
            valid[i] = true;
            delta[i] = (omega[i] - expected[i]).abs() / (expected[i] + 1.0);
        }
    }

    // Recursions — same order of operations as the reference
    let a = (-1.0 / cfg.tau_memory).exp();
    let mut xi = vec![0.0f64; n];
    let mut lam = vec![cfg.lambda_eq; n];
    let mut theta = vec![0.0f64; n];
    if n > 0 {
        theta[0] = cfg.theta_scale * cfg.lambda_eq;
    }
    for i in 1..n {
        xi[i] = a * xi[i - 1] + (1.0 - a) * delta[i];
        let excess = (xi[i] - theta[i - 1]).max(0.0);
        let d_lam = -cfg.kappa * excess + cfg.lambda_recovery * (cfg.lambda_eq - lam[i - 1]);
        lam[i] = (lam[i - 1] + d_lam).clamp(cfg.lambda_min, cfg.lambda_eq);
        theta[i] = cfg.theta_scale * lam[i];
    }

    // Trailing/right-aligned rolling mean, then the normative causal difference:
    // G[0] = 0; G[t] = smooth_M[t] - smooth_M[t-1].
    let m: Vec<f64> = (0..n).map(|i| theta[i] - xi[i]).collect();
    let sm = rolling_mean_min1(&m, cfg.g_smooth);
    let g = backward_difference(&sm);

    let mut latent = vec![false; n];
    let mut stratum = vec![1u8; n];
    for i in 0..n {
        let sop = match sigma_op {
            Some(s) => s[i],
            None => omega[i] > 0.0,
        };
        latent[i] = sop && m[i] >= 0.0 && g[i] < 0.0 && valid[i];
        stratum[i] = if valid[i] {
            stratify_one(m[i], g[i])
        } else {
            1
        };
    }

    Gamma {
        delta,
        xi,
        lambda: lam,
        theta,
        m,
        g,
        latent_collapse: latent,
        stratum,
        valid,
    }
}

/// Regime stratification S₁–S₄ on the (M, G) plane (AS-1 §6).
#[inline]
pub fn stratify_one(m: f64, g: f64) -> u8 {
    if m > 0.0 && g < 0.0 {
        2
    } else if m <= 0.0 && g >= 0.0 {
        3
    } else if m <= 0.0 && g < 0.0 {
        4
    } else {
        1
    }
}

/// pandas `Series.rolling(window, min_periods=1).mean()` replica.
fn rolling_mean_min1(x: &[f64], window: usize) -> Vec<f64> {
    let n = x.len();
    let mut out = vec![0.0f64; n];
    let mut acc = 0.0f64;
    for i in 0..n {
        acc += x[i];
        if i >= window {
            acc -= x[i - window];
            out[i] = acc / window as f64;
        } else {
            out[i] = acc / (i + 1) as f64;
        }
    }
    out
}

/// Strictly causal one-step backward difference.
fn backward_difference(x: &[f64]) -> Vec<f64> {
    let n = x.len();
    let mut out = vec![0.0f64; n];
    for i in 1..n {
        out[i] = x[i] - x[i - 1];
    }
    out
}

/// O(1) streaming state for always-on production monitors.
/// Feed one pair per bin. Smoothing is trailing/right-aligned and G is a
/// causal one-step backward difference; there is no full-window delay.
pub struct Kernel {
    cfg: KernelConfig,
    a: f64,
    xi: f64,
    lam: f64,
    theta_prev: f64,
    started: bool,
    // rolling-mean ring buffer over M for the smoothed gradient
    ring: Vec<f64>,
    ring_pos: usize,
    ring_len: usize,
    ring_sum: f64,
    sm_prev: Option<f64>,
}

/// One streaming output bin.
#[derive(Debug, Clone, Copy)]
pub struct StepOut {
    pub delta: f64,
    pub xi: f64,
    pub lambda: f64,
    pub theta: f64,
    pub m: f64,
    /// Backward-difference gradient of smoothed M (streaming estimator of D⁺M).
    pub g: f64,
    pub latent_collapse: bool,
    pub stratum: u8,
    pub valid: bool,
}

impl Kernel {
    pub fn new(cfg: KernelConfig) -> Self {
        let a = (-1.0 / cfg.tau_memory).exp();
        let w = cfg.g_smooth.max(1);
        Self {
            cfg,
            a,
            xi: 0.0,
            lam: cfg.lambda_eq,
            theta_prev: cfg.theta_scale * cfg.lambda_eq,
            started: false,
            ring: vec![0.0; w],
            ring_pos: 0,
            ring_len: 0,
            ring_sum: 0.0,
            sm_prev: None,
        }
    }

    pub fn step(&mut self, omega: f64, expected: f64, sigma_op: Option<bool>) -> StepOut {
        let valid = !expected.is_nan();
        let delta = if valid {
            (omega - expected).abs() / (expected + 1.0)
        } else {
            0.0
        };

        let (xi, lam, theta);
        if !self.started {
            // bin 0 of the batch recursion: xi=0, lam=eq, theta=scale*eq
            self.started = true;
            xi = 0.0;
            lam = self.cfg.lambda_eq;
            theta = self.cfg.theta_scale * self.cfg.lambda_eq;
        } else {
            xi = self.a * self.xi + (1.0 - self.a) * delta;
            let excess = (xi - self.theta_prev).max(0.0);
            let d_lam = -self.cfg.kappa * excess
                + self.cfg.lambda_recovery * (self.cfg.lambda_eq - self.lam);
            lam = (self.lam + d_lam).clamp(self.cfg.lambda_min, self.cfg.lambda_eq);
            theta = self.cfg.theta_scale * lam;
        }
        self.xi = xi;
        self.lam = lam;
        self.theta_prev = theta;

        let m = theta - xi;
        // streaming rolling mean of M
        if self.ring_len == self.ring.len() {
            self.ring_sum -= self.ring[self.ring_pos];
        } else {
            self.ring_len += 1;
        }
        self.ring[self.ring_pos] = m;
        self.ring_pos = (self.ring_pos + 1) % self.ring.len();
        self.ring_sum += m;
        let sm = self.ring_sum / self.ring_len as f64;
        let g = match self.sm_prev {
            Some(p) => sm - p, // backward difference (streaming D⁺M estimator)
            None => 0.0,
        };
        self.sm_prev = Some(sm);

        let sop = sigma_op.unwrap_or(omega > 0.0);
        StepOut {
            delta,
            xi,
            lambda: lam,
            theta,
            m,
            g,
            latent_collapse: sop && m >= 0.0 && g < 0.0 && valid,
            stratum: if valid { stratify_one(m, g) } else { 1 },
            valid,
        }
    }
}
