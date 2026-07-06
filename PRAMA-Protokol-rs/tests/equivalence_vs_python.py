"""Re-runnable Rust<->Python equivalence certification.
Requires: pip install prama-protokol ; cargo build --release
Run from crate root: python tests/equivalence_vs_python.py"""
import subprocess, io
import numpy as np, pandas as pd
from prama_protokol import KernelConfig, project

rng = np.random.default_rng(99)
worst_all = 0.0
for n, tau, gs, nan_frac in [(10_000,336.0,24,0.02),(10_000,64.0,16,0.0),(50_000,336.0,24,0.05)]:
    om = rng.gamma(2.0,1.0,n); ex = np.abs(rng.normal(2.0,0.5,n))
    if nan_frac: ex[:int(n*nan_frac)] = np.nan
    gp = project(om, ex, KernelConfig(tau_memory=tau, g_smooth=gs))
    csv_in = "omega,expected\n"+"\n".join(
        f"{o:.17e},{'nan' if np.isnan(e) else format(e,'.17e')}" for o,e in zip(om,ex))
    r = subprocess.run(["./target/release/prama-project","--tau",str(tau),"--gsmooth",str(gs)],
                       input=csv_in, capture_output=True, text=True, check=True)
    gr = pd.read_csv(io.StringIO(r.stdout))
    worst = max(float(np.max(np.abs(gp[c].to_numpy()-gr[c].to_numpy())))
                for c in ["delta","xi","lambda","theta","M","G"])
    assert (gp["latent_collapse"].to_numpy()==gr["latent_collapse"].astype(bool).to_numpy()).all()
    assert (gp["stratum"].to_numpy()==gr["stratum"].to_numpy()).all()
    assert (gp["valid"].to_numpy()==gr["valid"].astype(bool).to_numpy()).all()
    worst_all = max(worst_all, worst)
    print(f"n={n} tau={tau}: max|diff|={worst:.2e}  flags identical")
assert worst_all < 1e-12, worst_all
print("CERTIFICATION: PASS")
