//! prama-project — CLI for cross-language equivalence testing and batch use.
//!
//! Reads CSV from stdin with header `omega,expected` (expected may be `nan`),
//! writes CSV to stdout: delta,xi,lambda,theta,M,G,latent_collapse,stratum,valid.
//! Kernel parameters via flags: --tau --gsmooth (others at validated defaults).

use prama_protokol::{project, KernelConfig};
use std::io::{self, BufRead, Write};

fn main() {
    let mut cfg = KernelConfig::default();
    let args: Vec<String> = std::env::args().collect();
    let mut i = 1;
    while i + 1 < args.len() {
        match args[i].as_str() {
            "--tau" => cfg.tau_memory = args[i + 1].parse().unwrap(),
            "--gsmooth" => cfg.g_smooth = args[i + 1].parse().unwrap(),
            _ => {}
        }
        i += 2;
    }

    if let Some(pos) = args.iter().position(|a| a == "--bench") {
        let n: usize = args[pos + 1].parse().unwrap();
        let omega: Vec<f64> = (0..n).map(|i| 1.0 + ((i % 97) as f64) * 0.03).collect();
        let expected: Vec<f64> = vec![2.0; n];
        let t0 = std::time::Instant::now();
        let g = project(&omega, &expected, &cfg, None);
        let dt = t0.elapsed().as_secs_f64();
        eprintln!(
            "bench: {} bins in {:.3}s ({:.1} M bins/s)  [checksum xi_last={:.6}]",
            n,
            dt,
            n as f64 / dt / 1e6,
            g.xi[n - 1]
        );
        return;
    }

    let stdin = io::stdin();
    let mut omega = Vec::new();
    let mut expected = Vec::new();
    for (ln, line) in stdin.lock().lines().enumerate() {
        let line = line.unwrap();
        if ln == 0 && line.starts_with("omega") {
            continue;
        }
        let mut parts = line.split(',');
        let o: f64 = parts.next().unwrap().trim().parse().unwrap();
        let e_raw = parts.next().unwrap().trim();
        let e: f64 = if e_raw.eq_ignore_ascii_case("nan") {
            f64::NAN
        } else {
            e_raw.parse().unwrap()
        };
        omega.push(o);
        expected.push(e);
    }

    let g = project(&omega, &expected, &cfg, None);
    let out = io::stdout();
    let mut w = io::BufWriter::new(out.lock());
    writeln!(w, "delta,xi,lambda,theta,M,G,latent_collapse,stratum,valid").unwrap();
    for i in 0..omega.len() {
        writeln!(
            w,
            "{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{:.17e},{},{},{}",
            g.delta[i],
            g.xi[i],
            g.lambda[i],
            g.theta[i],
            g.m[i],
            g.g[i],
            g.latent_collapse[i] as u8,
            g.stratum[i],
            g.valid[i] as u8
        )
        .unwrap();
    }
}

// --bench N: internal benchmark without I/O (invoked before CSV reading)
