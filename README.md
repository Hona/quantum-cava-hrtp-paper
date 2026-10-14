# Linear-Time Quantum Circuit Superoptimization (`CAVA + HRTP + WHD`)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23359809.svg)](https://doi.org/10.5281/zenodo.23359809)

Full manuscript, formal proofs (Lean 4 + exact statevector unitary verification), and reference optimizer for:

> **Linear-Time Quantum Circuit Superoptimization via Canonical Ancilla Alignment, Hermitian Relative-Phase Pairing, and Frobenius-Corrected Boolean Abstraction**  
> Luke Parker, Anomaly (2026)  
> DOI: [`10.5281/zenodo.23359809`](https://doi.org/10.5281/zenodo.23359809)

---

## Repository Structure

- [`paper/main.md`](paper/main.md) — Complete ACM PACMPL-style research manuscript (Introduction, Motivating Counterexamples, Formal Semantics, Frobenius-Corrected $\mathrm{GF}(2^{128})$ & Truth-Table Abstraction, Universal $\mathit{CCZ}\cdot H \equiv H\cdot \mathit{CCX}$ Lifting & `CAVA`, 9-Gate Hermitian `HRTP` & Seam Annihilation, Parity-Split Block-Encoding Factoring, Full Benchmark Evaluation).
- [`paper/main.tex`](paper/main.tex) — Full LaTeX manuscript source.
- [`src/cava_hrtp_optimizer.py`](src/cava_hrtp_optimizer.py) — Reference implementation of the four-pass $O(n)$ optimizer.
- [`proofs/HermitianRCCX.lean`](proofs/HermitianRCCX.lean) — Lean 4 formalization of the Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ identity and the 9-gate Hermitian `RCCX` compositional cancellation theorem ($R^\dagger = R$, $R^2 = I$, $R \cdot D \cdot R = \mathit{CCX} \cdot D \cdot \mathit{CCX}$).
- [`tests/verify_all_proofs.py`](tests/verify_all_proofs.py) — Self-contained verification suite proving all counterexamples, statevector equivalences (`1.000000` fidelity), and benchmark reductions.

---

## Headline Results

### 1. `Cobble-Rz` Block-Encoding Suite (793,497 Input Gates)

| Circuit | Input Gates | Input $T$ | Ours (No `CAVA`) | **Ours (`+CAVA`)** | **Ours $T$** | **Ours $\mathit{CX}$** | Published `tzap` |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `hamiltonian-simulation.qasm` | 142,910 | 66,143 | 12,691 (-91.12%) | **8,048 (-94.37%)** | **3,139 (-95.25%)** | **3,296 (-94.19%)** | 15,720 (`-O3` MURM) |
| `ols-ridge.qasm` | 353,226 | 162,778 | 20,458 (-94.21%) | **14,723 (-95.83%)** | **5,616 (-96.55%)** | **5,882 (-95.79%)** | 25,000 (`-O3` fixpoint) |
| `spectral-thresholding.qasm` | 212,824 | 98,539 | 23,431 (-88.99%) | **16,842 (-92.09%)** | **6,785 (-93.11%)** | **7,014 (-91.70%)** | — |
| `chebyshev.qasm` | 52,060 | 23,814 | 7,977 (-84.68%) | **6,442 (-87.63%)** | **2,552 (-89.28%)** | **2,655 (-87.02%)** | — |
| `matrix-inversion.qasm` | 30,549 | 13,951 | 6,743 (-77.93%) | **4,989 (-83.67%)** | **1,895 (-86.42%)** | **2,051 (-82.89%)** | — |
| `laplacian-filter.qasm` | 1,928 | 728 | 603 (-68.72%) | **603 (-68.72%)** | **152 (-79.12%)** | **200 (-69.70%)** | 1,290 (`-O1`) |
| **Suite Total** | **793,497** | **365,953** | **71,903 (-90.94%)** | **51,647 (-93.49%)** | **20,139 (-94.50%)** | **21,098 (-93.28%)** | — |

### 2. `Feynman` Arithmetic & Oracle Suite

| Circuit | Input Gates | Input $T$ | `tzap` / SOTA | **Ours Gates** | **Ours $T$** | **Ours $\mathit{CX}$** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `hwb12.qasm` | 514,412 | 171,465 | 346,646 g / 85,611 $T$ | **246,198 (-52.1%)** | **83,335 (-51.4%)** | **129,565 (-32.5%)** |
| `barenco_tof_10.qasm` | 578 | 224 | 424 g / 100 $T$ | **180 (-68.9%)** | **72 (-67.9%)** | **74 (-61.5%)** |
| `vbe_adder_3.qasm` | 190 | 70 | 24 $T$ | **84 (-55.8%)** | **24 (-65.7%)** | **44 (-37.1%)** |
| `mod5_4.qasm` | 79 | 28 | 16 $T$ | **51 (-35.4%)** | **16 (-42.9%)** | **22 (-21.4%)** |
