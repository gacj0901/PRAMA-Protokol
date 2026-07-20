//! PRAMA Protokol v0.3.0 universal activation kernel.
//!
//! This module is separate from the certified v0.2.1 implementation in
//! `lib.rs`. Input `k` produces state `k+1`. Leading expectation warm-up is
//! excluded; missing or non-finite values after emission starts fail closed.

use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct KernelConfigV3 {
    pub h: f64,
    pub tau: f64,
    pub theta_scale: f64,
    pub lambda_0: f64,
    pub lambda_min: f64,
    pub lambda_max: f64,
    pub kappa_v3: f64,
    pub g_smooth: usize,
    pub delta_ref: f64,
}

impl Default for KernelConfigV3 {
    fn default() -> Self {
        Self {
            h: 1.0,
            tau: 336.0,
            theta_scale: 2.0,
            lambda_0: 1.0,
            lambda_min: 0.1,
            lambda_max: 1.0,
            kappa_v3: 9.957514604354753e-7,
            g_smooth: 24,
            delta_ref: 1.0,
        }
    }
}

impl KernelConfigV3 {
    pub fn validate(&self) -> Result<(), V3Error> {
        let finite = [
            self.h,
            self.tau,
            self.theta_scale,
            self.lambda_0,
            self.lambda_min,
            self.lambda_max,
            self.kappa_v3,
            self.delta_ref,
        ];
        if finite.iter().any(|value| !value.is_finite()) {
            return Err(V3Error::InvalidConfiguration(
                "all scalar parameters must be finite",
            ));
        }
        if self.h <= 0.0 {
            return Err(V3Error::InvalidConfiguration("h must be > 0"));
        }
        if self.tau <= 0.0 {
            return Err(V3Error::InvalidConfiguration("tau must be > 0"));
        }
        if self.theta_scale <= 0.0 {
            return Err(V3Error::InvalidConfiguration("theta_scale must be > 0"));
        }
        if self.lambda_min < 0.0 || self.lambda_min > self.lambda_max {
            return Err(V3Error::InvalidConfiguration("lambda bounds are invalid"));
        }
        if self.lambda_0 < self.lambda_min || self.lambda_0 > self.lambda_max {
            return Err(V3Error::InvalidConfiguration(
                "lambda_0 must lie within lambda bounds",
            ));
        }
        if self.kappa_v3 < 0.0 {
            return Err(V3Error::InvalidConfiguration("kappa_v3 must be >= 0"));
        }
        if self.g_smooth == 0 {
            return Err(V3Error::InvalidConfiguration("g_smooth must be > 0"));
        }
        if self.delta_ref <= 0.0 {
            return Err(V3Error::InvalidConfiguration("delta_ref must be > 0"));
        }
        Ok(())
    }

    pub fn r(&self) -> Result<f64, V3Error> {
        self.validate()?;
        Ok((-self.h / self.tau).exp())
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub enum V3Error {
    InvalidConfiguration(&'static str),
    LengthMismatch(&'static str),
    EmptyInput,
    NoValidRows,
    InternalMissingAfterStart,
    InvalidInput(&'static str),
}

impl Display for V3Error {
    fn fmt(&self, formatter: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::InvalidConfiguration(message) => {
                write!(formatter, "invalid v0.3 configuration: {message}")
            }
            Self::LengthMismatch(name) => write!(formatter, "{name} length must match omega"),
            Self::EmptyInput => write!(formatter, "inputs must be non-empty"),
            Self::NoValidRows => write!(formatter, "no_valid_rows"),
            Self::InternalMissingAfterStart => {
                write!(formatter, "internal_missing_after_start")
            }
            Self::InvalidInput(message) => write!(formatter, "invalid v0.3 input: {message}"),
        }
    }
}

impl Error for V3Error {}

#[allow(non_snake_case)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct GammaRowV3 {
    pub delta: f64,
    pub delta_tilde: f64,
    pub e: f64,
    pub xi: f64,
    pub A: f64,
    pub lambda: f64,
    pub theta: f64,
    pub M: f64,
    pub G: f64,
    pub u_lambda: f64,
    pub sigma_op: bool,
    pub valid: bool,
    pub input_index: usize,
    pub state_index: usize,
}

#[allow(non_snake_case)]
#[derive(Clone, Debug, Default, PartialEq)]
pub struct GammaV3 {
    pub delta: Vec<f64>,
    pub delta_tilde: Vec<f64>,
    pub e: Vec<f64>,
    pub xi: Vec<f64>,
    pub A: Vec<f64>,
    pub lambda: Vec<f64>,
    pub theta: Vec<f64>,
    pub M: Vec<f64>,
    pub G: Vec<f64>,
    pub u_lambda: Vec<f64>,
    pub sigma_op: Vec<bool>,
    pub valid: Vec<bool>,
    pub input_index: Vec<usize>,
    pub state_index: Vec<usize>,
}

#[allow(non_snake_case)]
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct NumericAuditV3 {
    pub emitted_count: usize,
    pub resummation_count: usize,
    pub ring_len: usize,
    pub ring_sum: f64,
    pub smooth_m: Option<f64>,
    pub lambda_sum_A: f64,
    pub lambda_sum_u: f64,
    pub lambda_sum_pi: f64,
    pub lambda_step_residual: f64,
    pub lambda_ledger_residual: f64,
}

impl GammaV3 {
    pub fn len(&self) -> usize {
        self.delta.len()
    }

    pub fn is_empty(&self) -> bool {
        self.delta.is_empty()
    }

    fn push(&mut self, row: GammaRowV3) {
        self.delta.push(row.delta);
        self.delta_tilde.push(row.delta_tilde);
        self.e.push(row.e);
        self.xi.push(row.xi);
        self.A.push(row.A);
        self.lambda.push(row.lambda);
        self.theta.push(row.theta);
        self.M.push(row.M);
        self.G.push(row.G);
        self.u_lambda.push(row.u_lambda);
        self.sigma_op.push(row.sigma_op);
        self.valid.push(row.valid);
        self.input_index.push(row.input_index);
        self.state_index.push(row.state_index);
    }
}

#[allow(non_snake_case)]
pub struct KernelV3 {
    cfg: KernelConfigV3,
    r: f64,
    xi: f64,
    A: f64,
    lambda: f64,
    theta: f64,
    started: bool,
    input_index: usize,
    m_ring: Vec<f64>,
    ring_pos: usize,
    ring_len: usize,
    ring_sum: f64,
    smooth_m_prev: Option<f64>,
    resummation_count: usize,
    lambda_sum_A: f64,
    lambda_sum_u: f64,
    lambda_sum_pi: f64,
    lambda_step_residual: f64,
    lambda_ledger_residual: f64,
}

impl KernelV3 {
    pub fn new(cfg: KernelConfigV3) -> Result<Self, V3Error> {
        let r = cfg.r()?;
        Ok(Self {
            cfg,
            r,
            xi: 0.0,
            A: 0.0,
            lambda: cfg.lambda_0,
            theta: cfg.theta_scale * cfg.lambda_0,
            started: false,
            input_index: 0,
            m_ring: vec![0.0; cfg.g_smooth],
            ring_pos: 0,
            ring_len: 0,
            ring_sum: 0.0,
            smooth_m_prev: None,
            resummation_count: 0,
            lambda_sum_A: 0.0,
            lambda_sum_u: 0.0,
            lambda_sum_pi: 0.0,
            lambda_step_residual: 0.0,
            lambda_ledger_residual: 0.0,
        })
    }

    pub fn started(&self) -> bool {
        self.started
    }

    pub fn numeric_audit(&self) -> NumericAuditV3 {
        NumericAuditV3 {
            emitted_count: self.input_index,
            resummation_count: self.resummation_count,
            ring_len: self.ring_len,
            ring_sum: self.ring_sum,
            smooth_m: self.smooth_m_prev,
            lambda_sum_A: self.lambda_sum_A,
            lambda_sum_u: self.lambda_sum_u,
            lambda_sum_pi: self.lambda_sum_pi,
            lambda_step_residual: self.lambda_step_residual,
            lambda_ledger_residual: self.lambda_ledger_residual,
        }
    }

    pub fn step(
        &mut self,
        omega: f64,
        expected: f64,
        u_lambda: f64,
        sigma_op: Option<bool>,
    ) -> Result<Option<GammaRowV3>, V3Error> {
        if expected.is_nan() {
            if self.started {
                return Err(V3Error::InternalMissingAfterStart);
            }
            return Ok(None);
        }
        if !expected.is_finite() {
            return Err(V3Error::InvalidInput("expected must be finite"));
        }
        if !omega.is_finite() {
            return Err(V3Error::InvalidInput("omega must be finite"));
        }
        if expected < 0.0 {
            return Err(V3Error::InvalidInput("expected must be >= 0"));
        }
        if !u_lambda.is_finite() || u_lambda < 0.0 {
            return Err(V3Error::InvalidInput("u_lambda must be finite and >= 0"));
        }

        let delta = (omega - expected).abs() / (expected + 1.0);
        let delta_tilde = delta / self.cfg.delta_ref;

        let e = if self.xi > self.theta {
            self.xi - self.theta
        } else {
            0.0
        };
        let a_next = self.A + self.cfg.h * e;

        let lambda_raw =
            self.lambda - self.cfg.kappa_v3 * self.cfg.h * a_next + self.cfg.h * u_lambda;
        let lambda_next = lambda_raw.clamp(self.cfg.lambda_min, self.cfg.lambda_max);
        let theta_next = self.cfg.theta_scale * lambda_next;

        let xi_next = self.r * self.xi + (1.0 - self.r) * delta_tilde;
        let margin = theta_next - xi_next;

        let mut ring_sum = self.ring_sum;
        let mut ring_len = self.ring_len;
        let ring_pos = self.ring_pos;
        if ring_len == self.m_ring.len() {
            ring_sum -= self.m_ring[ring_pos];
        } else {
            ring_len += 1;
        }
        ring_sum += margin;
        let next_ring_pos = (ring_pos + 1) % self.m_ring.len();
        let emitted_count = self.input_index + 1;
        let mut resummation_count = self.resummation_count;
        if emitted_count % self.m_ring.len() == 0 {
            // Rebuild after insertion in logical oldest-to-newest order. Read
            // the candidate without mutating the live ring so validation
            // remains fail-closed.
            ring_sum = 0.0;
            let oldest = if ring_len == self.m_ring.len() {
                next_ring_pos
            } else {
                0
            };
            for offset in 0..ring_len {
                let position = (oldest + offset) % self.m_ring.len();
                let value = if position == ring_pos {
                    margin
                } else {
                    self.m_ring[position]
                };
                ring_sum = ring_sum + value;
            }
            resummation_count += 1;
        }
        let smooth_m = ring_sum / ring_len as f64;
        let g = match self.smooth_m_prev {
            Some(previous) => smooth_m - previous,
            None => 0.0,
        };

        let pi = lambda_next - lambda_raw;
        let lambda_sum_a = self.lambda_sum_A + a_next;
        let lambda_sum_u = self.lambda_sum_u + u_lambda;
        let lambda_sum_pi = self.lambda_sum_pi + pi;
        let lambda_step_residual = lambda_next - self.lambda
            + self.cfg.kappa_v3 * self.cfg.h * a_next
            - self.cfg.h * u_lambda
            - pi;
        let lambda_ledger_residual = lambda_next - self.cfg.lambda_0
            + self.cfg.kappa_v3 * self.cfg.h * lambda_sum_a
            - self.cfg.h * lambda_sum_u
            - lambda_sum_pi;

        let computed = [
            delta,
            delta_tilde,
            e,
            a_next,
            lambda_raw,
            lambda_next,
            theta_next,
            xi_next,
            margin,
            ring_sum,
            smooth_m,
            g,
            pi,
            lambda_sum_a,
            lambda_sum_u,
            lambda_sum_pi,
            lambda_step_residual,
            lambda_ledger_residual,
        ];
        if computed.iter().any(|value| !value.is_finite()) {
            return Err(V3Error::InvalidInput("non-finite arithmetic result"));
        }

        let k = self.input_index;
        let row = GammaRowV3 {
            delta,
            delta_tilde,
            e,
            xi: xi_next,
            A: a_next,
            lambda: lambda_next,
            theta: theta_next,
            M: margin,
            G: g,
            u_lambda,
            sigma_op: sigma_op.unwrap_or(omega > 0.0),
            valid: true,
            input_index: k,
            state_index: k + 1,
        };

        self.m_ring[ring_pos] = margin;
        self.ring_pos = next_ring_pos;
        self.ring_len = ring_len;
        self.ring_sum = ring_sum;
        self.smooth_m_prev = Some(smooth_m);
        self.resummation_count = resummation_count;
        self.lambda_sum_A = lambda_sum_a;
        self.lambda_sum_u = lambda_sum_u;
        self.lambda_sum_pi = lambda_sum_pi;
        self.lambda_step_residual = lambda_step_residual;
        self.lambda_ledger_residual = lambda_ledger_residual;
        self.xi = xi_next;
        self.A = a_next;
        self.lambda = lambda_next;
        self.theta = theta_next;
        self.input_index += 1;
        self.started = true;
        Ok(Some(row))
    }
}

pub fn project_v3(
    omega: &[f64],
    expected: &[f64],
    cfg: &KernelConfigV3,
    u_lambda: Option<&[f64]>,
    sigma_op: Option<&[bool]>,
) -> Result<GammaV3, V3Error> {
    if omega.is_empty() {
        return Err(V3Error::EmptyInput);
    }
    if expected.len() != omega.len() {
        return Err(V3Error::LengthMismatch("expected"));
    }
    if u_lambda.is_some_and(|values| values.len() != omega.len()) {
        return Err(V3Error::LengthMismatch("u_lambda"));
    }
    if sigma_op.is_some_and(|values| values.len() != omega.len()) {
        return Err(V3Error::LengthMismatch("sigma_op"));
    }

    let mut kernel = KernelV3::new(*cfg)?;
    let mut gamma = GammaV3::default();
    for source_index in 0..omega.len() {
        let control = u_lambda.map_or(0.0, |values| values[source_index]);
        let operational = sigma_op.map(|values| values[source_index]);
        if let Some(row) = kernel.step(
            omega[source_index],
            expected[source_index],
            control,
            operational,
        )? {
            gamma.push(row);
        }
    }
    if gamma.is_empty() {
        return Err(V3Error::NoValidRows);
    }
    Ok(gamma)
}
