# Notes on the Hubble tension

The "Hubble tension" is the 4–6σ discrepancy between early-universe measurements of H₀ (CMB + ΛCDM, Planck 2018: H₀ = 67.4 ± 0.5 km/s/Mpc) and late-universe distance-ladder measurements (SH0ES 2022: H₀ = 73.04 ± 1.04 km/s/Mpc).

## What we know

- The discrepancy has grown (not shrunk) with each revision of both the Planck analysis and the distance ladder.
- TRGB (tip of the red giant branch, CCHP collaboration) gives ~69.8 km/s/Mpc, sitting between the two camps.
- Strong-lensing time delays (H0LiCOW, TDCOSMO) give H₀ ≈ 73 with larger error bars.

## Our lab's working model (internal draft v0.7)

We are investigating a **late-time dark-energy transition** — an equation-of-state w(z) that deviates from −1 between z ≈ 0.3 and z ≈ 0.02. In the fiducial form:

    w(z) = -1 + ε · tanh((z - z*) / Δz)

with z* ≈ 0.15, Δz ≈ 0.08, and ε ≈ 0.05. This shifts the inferred distance ladder by enough to ease the tension by roughly 1.2σ without breaking the CMB fit.

## Open problems

1. The model must avoid violating the null energy condition — constraints from structure growth (σ₈) are tight.
2. Cross-correlating with fσ₈ measurements from DESI DR2 (when public) is the next test.
3. Need to simulate the effect on the sound horizon at drag (r_d) — Yonatan is running CAMB modifications this week.

## Action items

- **Maya Arbel** — finalize the CAMB patch for w(z), target 2026-04-22.
- **Yonatan Peled** — write up the BAO likelihood module.
- **Group** — invite Prof. Lior Feldman (Tel Aviv) to give a seminar on bispectrum constraints, target May.
