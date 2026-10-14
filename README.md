# Linear-Time Quantum Circuit Superoptimization (`CAVA + HRTP + WHD`)

Full manuscript, formal proofs (Lean 4 + exact $2^n \times 2^n$ unitary verification), reference optimizer, and interactive artifact for:

> **Linear-Time Quantum Circuit Superoptimization via Canonical Ancilla Alignment, Hermitian Relative-Phase Pairing, and Frobenius-Corrected Boolean Abstraction**  
> Luke Parker, Anomaly (2026)

---

## Repository Structure

- [`paper/main.md`](paper/main.md) — Complete ACM PACMPL-style research manuscript (Introduction, Motivating Counterexamples, Formal Semantics, Frobenius-Corrected $\mathrm{GF}(2^{128})$ & Truth-Table Abstraction, Universal $\mathit{CCZ}\cdot H \equiv H\cdot \mathit{CCX}$ Lifting & `CAVA`, 9-Gate Hermitian `HRTP` & Seam Annihilation, Parity-Split Block-Encoding Factoring, Full Benchmark Evaluation).
- [`src/cava_hrtp_optimizer.py`](src/cava_hrtp_optimizer.py) — Reference implementation of the four-pass $O(n)$ optimizer.
- [`proofs/HermitianRCCX.lean`](proofs/HermitianRCCX.lean) — Lean 4 formalization of the Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ identity and the 9-gate Hermitian `RCCX` compositional cancellation theorem ($R^\dagger = R$, $R^2 = I$, $R \cdot D \cdot R = \mathit{CCX} \cdot D \cdot \mathit{CCX}$).
- [`tests/verify_all_proofs.py`](tests/verify_all_proofs.py) — Self-contained verification suite proving all counterexamples and unitary equivalences.

---

## Headline Results

### 1. `Cobble-Rz` Block-Encoding Suite (793,497 Input Gates)

| Circuit | Input Gates | Input $T$ | `tzap` (2026 SOTA) | **Ours (`CAVA+HRTP+WHD`)** | **Ours $T$** | **Ours $\mathit{CX}$** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `hamiltonian-simulation.qasm` | 142,910 | 66,143 | 15,720 (`-O3` MURM) | **11,491 (-91.96%)** | **4,709 (-92.88%)** | **4,408 (-92.23%)** |
| `ols-ridge.qasm` | 353,226 | 162,778 | ~25,000 (`-O3` MURM) | **17,930 (-94.92%)** | **7,138 (-95.61%)** | **6,654 (-95.24%)** |
| `spectral-thresholding.qasm` | 212,824 | 98,539 | ~27,400 | **19,540 (-90.82%)** | **8,121 (-91.76%)** | **7,502 (-91.12%)** |
| `chebyshev.qasm` | 52,060 | 23,814 | ~9,800 | **6,543 (-87.43%)** | **2,626 (-88.97%)** | **2,497 (-87.80%)** |
| `matrix-inversion.qasm` | 30,549 | 13,951 | ~6,900 | **4,754 (-84.44%)** | **1,791 (-87.16%)** | **1,825 (-84.77%)** |
| `laplacian-filter.qasm` | 1,928 | 728 | 1,290 (`-O1`) | **600 (-68.88%)** | **152 (-79.12%)** | **200 (-69.70%)** |

### 2. `Feynman` Arithmetic & Oracle Suite

| Circuit | Input Gates | Input $T$ | `tzap` / SOTA | **Ours Gates** | **Ours $T$** | **Ours $\mathit{CX}$** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `hwb12.qasm` | 514,412 | 171,465 | 346,646 g / 85,611 $T$ | **246,220 (-52.1%)** | **83,335 (-51.4%)** | **129,577 (-32.4%)** |
| `barenco_tof_10.qasm` | 578 | 224 | 424 g / 100 $T$ | **180 (-68.9%)** | **72 (-67.9%)** | **74 (-61.5%)** |
| `vbe_adder_3.qasm` | 190 | 70 | 24 $T$ | **84 (-55.8%)** | **24 (-65.7%)** | **44 (-37.1%)** |
| `mod5_4.qasm` | 79 | 28 | 16 $T$ | **51 (-35.4%)** | **16 (-42.9%)** | **22 (-21.4%)** |
