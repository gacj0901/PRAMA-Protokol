# Anomalies

## 0.1.0 batch causality violation (corrected in 0.2.0)

Version 0.1.0 computed `G` with a central difference in Python batch and Rust
batch. Thus an interior `G[t]` could depend on `M[t+1]`, violating prefix
causality. Rust streaming already used a one-step backward difference.

Version 0.2.0 unifies Python batch, Rust batch and Rust streaming under
`G[0] = 0` and `G[t] = smooth_M[t] - smooth_M[t-1]` for `t > 0`, where
`smooth_M` is a trailing, right-aligned mean with `min_periods=1`. Empirical
results produced with 0.1.0 must be revalidated and are not current 0.2.0
evidence.
