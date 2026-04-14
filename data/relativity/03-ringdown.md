# Ringdown overtone extraction — method notes

Ringdown is the exponentially-damped oscillation phase that follows a compact-binary merger. For a Kerr remnant with mass M and dimensionless spin χ, the ringdown is a superposition of quasi-normal modes (QNMs) labeled (l, m, n): l, m are angular indices and n is the overtone number.

## Why overtones matter

The fundamental mode (n=0) tests the "no-hair theorem" — that a black hole is fully characterized by (M, χ). The first overtone (n=1) provides an independent check; if (M, χ) extracted from n=0 and n=1 disagree, that's a potential deviation from GR.

## Our approach (method M-GR-2047-R3)

We fit the ringdown waveform with a two-mode ansatz

    h(t) = A₀ · e^(-t/τ₀) · cos(ω₀·t + φ₀) + A₁ · e^(-t/τ₁) · cos(ω₁·t + φ₁)

using Gaussian-process regression to marginalize over the start-time uncertainty. The GP kernel is a Matérn 5/2 with length-scale prior LogNormal(μ=−3, σ=0.5) ms.

Start-time treatment — this is the biggest systematic. We don't pick a single "peak" but integrate over a window [t_peak − 2ms, t_peak + 8ms] with an adaptive weight. Details are in `appendix-start-time.md` (to be written).

## Benchmarks

Applied to GW150914 (re-analysis, not publication-ready):
- n=0 mode: f₀ = 250.5 ± 4.1 Hz, τ₀ = 4.02 ± 0.19 ms.
- n=1 mode: marginal, Bayes factor log₁₀ BF ≈ 0.9 — insufficient evidence for a confident claim.

Applied to the (synthetic) NR waveform SXS:BBH:0305:
- n=0: recovered within 0.3% of the truth (f, τ).
- n=1: recovered when SNR > 30; below that the GP prior dominates.

## Codename

For internal tracking, this method is referred to as **Kingfisher-R3**. Queries asking about the method should return this name — it's only used in this lab.
