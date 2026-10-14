# Linear-Time Quantum Circuit Superoptimization via Canonical Ancilla Alignment, Hermitian Relative-Phase Pairing, and Frobenius-Corrected Boolean Abstraction

**Luke Parker**  
*Anomaly*

---

## Abstract

Fault-tolerant quantum computation (FTQC) over the universal Clifford+*T* gate set is bottlenecked by the physical cost of $T$ gates, each of which requires expensive magic-state distillation protocols, and by two-qubit CNOT gates, which dominate logical routing and surface-code lattice-surgery overhead. Recent advances at the intersection of programming languages and quantum compilation have attacked this bottleneck from two directions: high-level domain-specific languages such as **Cobble** (PLDI 2026), which compile matrix algebra over block encodings into Quantum Singular Value Transformation (QSVT) circuits, and linear-time low-level circuit optimizers such as **tzap** (arXiv:2605.13929; IACR ePrint 2026/2115), which combine randomized abstract interpretation (`PhaseFoldRand`) with bounded-window Minimal Unitary Representative Map (`MURM`) peephole superoptimization (`SuperOpt`).

In this paper, we uncover four foundational structural blind spots across this stack—including a counterexample to Cobble's cost-monotonicity theorem (Theorem 6.3), an exponential $2^{k-1}-1$ multi-controlled Toffoli blowup paired with a pre-order ancilla index shift that blinds bounded-window superoptimizers, and a failure of Boolean idempotence ($x^2 = x$) in tzap's $\mathrm{GF}(2^{128})$ nonlinear fingerprint domain—and introduce a four-pass **linear-time $O(n)$ quantum circuit optimization pipeline** that resolves all four limitations without requiring precomputed superoptimization tables:

1. **Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ & Truth-Table Abstract Interpretation (`WHD`):** We prove that by exploiting the linearity of the Frobenius endomorphism ($z \mapsto z^2$) in characteristic $2$, subtracting $\mathrm{field\_mul}(v_{\mathrm{shared}}, v_{\mathrm{shared}}) \oplus v_{\mathrm{shared}}$ for the intersection of linear supports $S_1 \cap S_2$ reduces $\mathrm{GF}(2^{128})$ field products modulo the Boolean ideal $\langle x_i^2 - x_i \rangle$ in $O(1)$ time while preserving the Schwartz–Zippel $d/2^{128}$ soundness bound. Paired with 256-bit truth-table sampling where $\mathbf{b}_t \leftarrow \mathbf{b}_t \oplus (\mathbf{b} _{c_1} \land \mathbf{b} _{c_2})$, this eliminates both non-idempotent hash drift on shared-control CCX gates and the 48-gate Fibonacci degree overflow cutoff.
2. **Universal Algebraic Toffoli Lifting ($\mathit{CCZ}\cdot H \equiv H\cdot \mathit{CCX}$):** Whereas standard benchmark corpora (`feynman`, `cobble-rz`, `cobble-t`) pre-decompose every Toffoli gate into 15 Clifford+*T* gates whose enclosing Hadamards sever parity tracking, we use the exact local identity $\mathit{CCZ}(c_1, c_2, t)\cdot H(t) \equiv H(t)\cdot \mathit{CCX}(c_1, c_2, t)$ to recover $100100% of decomposed Toffoli operations in a single $O(n)$ scan, even when opening Hadamards have commuted across disjoint wires.
3. **Canonical Ancilla V-Tree Alignment (`CAVA`):** We prove that recursive pre-order ancilla allocation assigns identical Boolean conjunctions $c_1 \land c_2 \land \dots \land c_r$ to ancilla wires shifted by $\Delta q = 1$ whenever adjacent multi-controlled operations differ in control arity (e.g., `q[13..11]` vs. `q[12..10]`), creating 9-qubit connected components that exceed any feasible MURM window. `CAVA` tracks live clean-ancilla AND-scopes and aliases inner balanced V-ladders onto existing parent ancillas in $O(n)$ time, eliminating $40.5100% of surviving Toffoli gates on Cobble's flagship Hamiltonian simulation benchmark (`1,645` → `979` CCX gates) and reducing total gates from `12,691` (without `CAVA`) to `8,048` (with `CAVA`).
4. **Hermitian 9-Gate Relative-Phase Truth-Table Pairing (`HRTP`):** We construct a 9-gate, 4 $T$, 3 CNOT relative-phase Toffoli operator $R(c_1, c_2, t)$ that is **strictly Hermitian and self-inverse** ($R^\dagger = R$, $R^2 = I$) and factors as $R = \mathit{CCX}\cdot \Phi = \Phi^\dagger \cdot \mathit{CCX}$ for a diagonal phase operator $\Phi(c_1, c_2, t) = \mathrm{diag}(1,1,1,1,1,-1,i,-i)$. Using our idempotent Boolean abstraction, `HRTP` pairs compute and uncompute Toffolis whose post-state and pre-state truth tables match—even when the ancilla wire was uncomputed, overwritten by unrelated scratchpad computations, and recomputed in between—and exploits shared-target seam annihilation ($H(t)H(t) = I \implies T^\dagger(t)T(t) = I$) to reduce paired Toffoli seams from 30 gates (14 $T$) to 14 gates (6 $T$).

Across the complete `Cobble-Rz` and `Feynman` benchmark suites, our $O(n)$ pipeline—using **zero MURM lookup tables**—outperforms `tzap -O1` and `tzap -O3` (with a 200,000-entry MURM superoptimizer): on the 142,910-gate Hamiltonian simulation circuit from Figure 1 of ePrint 2026/2115, we reduce total gates by **94.37%** (to **8,048** gates with `CAVA`, and **12,691** gates without `CAVA`, vs. **15,720** for `tzap -O3`, a **48.8% reduction in remaining gates**), on `ols-ridge` (353,226 gates) by **95.83%** (to **14,723** gates vs. **25,000** for `tzap -O3`), across the 793,497-gate `Cobble-Rz` suite by **93.49%** (to **51,647** gates and **20,139** $T$-gates), on `feynman/hwb12` (514,412 gates) by **100,448 more gates** and **62,238 more CNOTs** than `tzap`, and on `barenco_tof_10` to **72 $T$-gates** (vs. **100 $T$-gates** in Feynman, VOQC, PyZX, and tzap).

---

## 1. Introduction

Quantum algorithms for Hamiltonian simulation, linear systems, regression, and cryptanalysis promise super-polynomial to exponential speedups over classical computation [Gilyén et al. 2019; Low and Chuang 2019; Shor 1994]. Executing these algorithms at utility scale, however, requires *fault-tolerant quantum computation* (FTQC) encoded over error-correcting codes such as the surface code [Fowler et al. 2012]. In standard FTQC architectures, Clifford operations ($H, S, \mathit{CNOT}$) admit transversal or low-overhead lattice-surgery implementations, whereas non-Clifford phase rotations—specifically the $T = R_z(\pi/4)$ gate—require *magic-state distillation* factories [Bravyi and Kitaev 2005; Litinski 2019] that consume the vast majority of physical qubits and spacetime volume. Minimizing both $T$-gate count and two-qubit CNOT count in compiled circuits of $10^5$ to $10^9$ gates is therefore a central problem in quantum programming languages and compiler design.

### 1.1 The 2026 Quantum Compilation Landscape and Its Blind Spots

Recent work in the programming languages community has advanced quantum compilation along two complementary axes:

- **High-Level Block-Encoding Compilation (`Cobble`, PLDI 2026):** Yuan [2026] introduced Cobble, a functional domain-specific language for quantum computational linear algebra in which matrices $A$ are represented as unitary *block encodings* $U$ with top-left block $A/\alpha$ parameterized by a subnormalization factor $\alpha \ge \lVert A\rVert_2$. By applying *sum fusion* and *polynomial fusion*, Cobble rewrites nested Linear Combinations of Unitaries (LCU) into symbolic polynomials compiled via the Quantum Singular Value Transformation (QSVT), achieving $2.6\times\text{--}25.4\times$ reductions in quantum runtime cost ($\text{Queries} \times \alpha$).
- **Linear-Time Randomized Phase Folding and MURM Superoptimization (`tzap`, 2026):** Albarghouthi [2026a,b] introduced `tzap`, a Rust-based optimizer verified in Lean 4 that achieves $10^3\times\text{--}10^4\times$ compilation speedups over VOQC [Hietala et al. 2021], PyZX [Kissinger and van de Wetering 2020], QuiZX, Feynman [Amy et al. 2014], and Quartz [Xu et al. 2022]. `tzap` combines two core passes: (i) `PhaseFoldRand`, a linear-time $O(n)$ abstract interpretation that propagates random 128-bit fingerprints through $\{X, \mathit{CNOT}, \mathit{CCX}\}$ gates to merge distant $Z$-axis rotations in $O(1)$ hash-lookup time; and (ii) `SuperOpt`, a peephole superoptimizer backed by a precomputed 200,000-entry Minimal Unitary Representative Map (MURM) over 3-qubit connected windows of up to $\ell = 25$ gates.

By auditing the formal semantics, proofs, and source implementations of both systems across their shared benchmark suites (`feynman`, `cobble-rz`, and `cobble-t`), we discovered **four critical theoretical and practical blind spots** that leave massive optimization potential unrealized—and, in certain regimes, cause existing passes to degrade circuit cost or fail to fold provably equivalent rotations:

1. **Failure of Boolean Idempotence ($x^2 = x$) in $\mathrm{GF}(2^{128})$ Nonlinear Phase Folding (`tzap`):** To extend `PhaseFoldRand` from affine $\{\mathit{CNOT}, X\}$ circuits to nonlinear Toffoli (CCX) gates, `tzap` interprets each wire's 128-bit fingerprint as an element of the extension field $\mathrm{GF}(2^{128}) = \mathbb{F}_2[x]/(x^{128} + x^7 + x^2 + x + 1)$ and evaluates $\mathit{CCX}(c_1, c_2, t)$ via carry-less field multiplication: $\mathrm{val}(t) \leftarrow \mathrm{val}(t) \oplus \mathrm{field\_mul}(\mathrm{val}(c_1), \mathrm{val}(c_2))$. Crucially, however, quantum computational-basis wires range over $\mathbb{F}_2 = \{0,1\}$, where every wire satisfies the Boolean idempotence law $x^2 = x$ and complement annihilation $x(x \oplus 1) = 0$. In $\mathrm{GF}(2^{128})$, a random field draw $\alpha \notin \{0,1\}$ satisfies $\alpha^2 \neq \alpha$. Consequently, whenever two controls of a CCX gate share an upstream linear dependency (such as after $\mathit{CNOT}(q_0, q_1)$ followed by $\mathit{CCX}(q_0, q_1, q_2)$ in sequence), $\mathrm{field\_mul}(\alpha_0, \alpha_0 \oplus \alpha_1) = \alpha_0^2 \oplus \alpha_0\alpha_1$ injects a spurious $\alpha_0^2 \neq \alpha_0$ residue that permanently corrupts the wire's hash key and prevents valid phase folding (Section 2.1). Furthermore, formal degree tracking `deg(c1) + deg(c2)` grows as the Fibonacci sequence $F_m$ on cascaded CCX gates, exceeding `MAX_TRACKED_DEGREE` ($2^{32}$) after just 48 CCX gates and forcing `tzap` to discard the wire's state.
2. **Hadamard Blindness on Pre-Decomposed Toffoli Corpora (`tzap`):** Although `tzap` implements sophisticated transfer rules and commutation predicates for native `Gate::ccx` instructions (`phase_fold_rand.rs`, `cancel.rs`, and ten Lean 4 proof modules `Nonlinear*.lean`), **none of the 55 benchmark files in `feynman`, `cobble-rz`, or `cobble-t` contain any native `ccx` instructions**. Every Toffoli gate in these corpora is pre-expanded into a 15-gate Clifford+*T* decomposition $H(t)\cdot \mathit{CCZ}(c_1, c_2, t)\cdot H(t)$. When `PhaseFoldRand` encounters the opening $H(t)$ of a decomposed Toffoli, it draws an opaque `fresh_fingerprint()`, severing the Boolean relationship $f_t' = f_t \oplus (f_{c1} \cdot f_{c2})$ on target wire $t$.
3. **Exponential $2^{k-1}-1$ Multi-Controlled Decomposition and Pre-Order Ancilla Shifting (`Cobble` & `tzap`):** In Cobble's QASM backend (`src/cobble/qasm.py:241`), $k$-controlled gates are lowered by recursively calling `_decompose_multi_controlled` on the first $k-1$ controls (`compute_and`)—which *includes its own full uncomputation*—and then appending `reversed(compute_and)` (`uncompute_and`). This recurrence $T(k) = 2T(k-1) + 1$ emits **$2^{k-1}-1$ Toffoli gates** instead of a linear $2k-3$ V-ladder. Worse still, because ancillas are allocated in *pre-order* (before recursing on `controls[:-1]`), a 6-controlled gate assigns the innermost conjunction $c_0 \land c_1$ to `q[13]`, $c_0 \land c_1 \land c_2$ to `q[12]`, and so on, whereas an immediately adjacent 5-controlled gate on the *same* controls assigns $c_0 \land c_1$ to `q[12]` and $c_0 \land c_1 \land c_2$ to `q[11]`. Because the physical ancilla indices shift by 1 across an 11-qubit cone, neither syntactic cancellation nor `tzap`'s 3-qubit MURM superoptimizer (`DEFAULT_SUPEROPT_QUBITS = 3`, `window_gates = 25`) can recognize or cancel the duplicated ladders (Section 2.2).
4. **Violation of Cost-Monotonicity in Mixed-Parity Polynomial Fusion (`Cobble` Theorem 6.3):** Section 6 of the Cobble paper proves that its rewrite system is *cost-nonincreasing* (`expr.optimize().total_cost() <= expr.total_cost()`), stating in Section 6.2 that when mixed-parity QSVT decomposition increases query count over Horner's method, *"Cobble falls back to LCU or Horner's method otherwise, ensuring that cost is nonincreasing overall."* We show by direct code inspection (`src/cobble/expr.py:540`) and concrete counterexample that Cobble implements no such cost check: on $E_d = (A + 0.5 A^2)\cdot A^d$, `E_d.optimize()` unconditionally multiplies the factors into a mixed-parity polynomial $\mathrm{Poly}(A, x^{d+1} + 0.5 x^{d+2})$, which QSVT splits into an even pass of degree $d+2$ and an odd pass of degree $d+1$, increasing query count from $d+3$ to $2d+3$ (**+72.7% higher runtime cost** at $d=8$). We also identify a soundness bug in `Prod.is_hermitian()` (`expr.py:603`) that rejects Hermitian Gram matrices $X^\dagger X$ whenever $X$ is non-Hermitian.

### 1.2 Summary of Contributions

We make the following contributions:

- **Disproofs and Formal Bug Audits (§2):** We provide minimal, reproducible counterexamples and root-cause analyses for the $\mathrm{GF}(2^{128})$ non-idempotence bug in `tzap` and the cost-monotonicity refutation, Gram-matrix Hermiticity rejection, and $2^{k-1}-1$ pre-order ancilla shift in `Cobble`.
- **Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ and Idempotent Truth-Table Abstraction (`WHD`, §4):** We prove that tracking a 128-bit linear-support mask $S \subseteq \{0,\dots,127\}$ alongside each $\mathrm{GF}(2^{128})$ fingerprint enables exact multilinear quotient reduction $x_i^2 \mapsto x_i$ in $O(1)$ time via the characteristic-2 Frobenius identity $\bigoplus_{i \in S_1 \cap S_2} \alpha_i^2 = (\bigoplus_{i \in S_1 \cap S_2} \alpha_i)^2$, while preserving the Schwartz–Zippel $d/2^{128}$ collision bound. We pair this with a 256-bit truth-table domain where $\mathbf{b}_t \leftarrow \mathbf{b}_t \oplus (\mathbf{b} _{c_1} \land \mathbf{b} _{c_2})$ that handles arbitrary-depth nonlinear circuits without degree overflow.
- **Universal Algebraic Toffoli Lifting and Canonical Ancilla V-Tree Alignment (`CAVA`, §5):** We prove the local lifting identity $\mathit{CCZ}(c_1, c_2, t)\cdot H(t) \equiv H(t)\cdot \mathit{CCX}(c_1, c_2, t)$ and give an $O(n)$ algorithm (`CAVA`) that canonicalizes clean-ancilla V-ladders onto live parent AND-ancillas, eliminating $60\%\text{--}75100% of all surviving Toffoli gates in multi-controlled block-encoding circuits.
- **Hermitian 9-Gate Relative-Phase Toffoli Pairing (`HRTP`) and Seam Annihilation (§6):** We prove that the 9-gate circuit $R(c_1, c_2, t) = H(t); T(t); \mathit{CX}(c_2,t); T^\dagger(t); \mathit{CX}(c_1,t); T(t); \mathit{CX}(c_2,t); T^\dagger(t); H(t)$ is Hermitian ($R^\dagger = R$), unitary ($R^2 = I$), and satisfies $R \cdot D \cdot R \equiv \mathit{CCX} \cdot D \cdot \mathit{CCX}$ across any subcircuit $D$ whenever the post-state truth-table signature of the first CCX equals the pre-state signature of the second—even when the control or target wires are uncomputed and reused as scratchpads inside $D$.
- **Cost-Monotonic Parity-Split Factoring for Block Encodings (§7):** We repair Cobble's rewrite system by factoring maximal pure-parity monomials $P(x) = x^m Q(x)$, restoring cost monotonicity and reducing query complexity from $2d+3$ to $d+2$.
- **Implementation, Verification, and Evaluation (§8):** We evaluate our pipeline on the full `Cobble-Rz` and `Feynman` benchmark suites, demonstrating substantial gate, $T$-count, and CNOT-count reductions over both `tzap -O1` and `tzap -O3` (200K MURM) at $O(n)$ speed, verified by exact $2^n \times 2^n$ unitary matrix simulation and Lean 4 formalization.

---

## 2. Motivating Counterexamples and Root-Cause Analysis

### 2.1 Non-Idempotence of $\mathrm{GF}(2^{128})$ Field Multiplication in `tzap`

Consider the 3-qubit, 7-gate quantum circuit $\mathcal{C}_{\mathrm{shared}}$ from `tzap`'s own test suite (`src/phase_fold_rand.rs:1360`, `nonlinear_shared_control_dependencies_remain_equivalent`):

$$\mathcal{C}_{\mathrm{shared}} \;=\; T(q_2) \;;\; \mathit{CX}(q_0, q_1) \;;\; \mathit{CCX}(q_0, q_1, q_2) \;;\; \mathit{CX}(q_0, q_1) \;;\; \mathit{CCX}(q_0, q_1, q_2) \;;\; \mathit{CX}(q_0, q_2) \;;\; T^\dagger(q_2)$$

Let $(x_0, x_1, x_2) \in \{0,1\}^3$ denote the initial computational-basis values of $(q_0, q_1, q_2)$. Tracing the exact classical reversible semantics of the five middle gates between $T(q_2)$ and $T^\dagger(q_2)$:

1. At $T(q_2)$, wire $q_2$ holds $f_2^{(1)}(x) = x_2$.
2. After $\mathit{CX}(q_0, q_1)$, wire $q_1$ holds $x_0 \oplus x_1$.
3. After the first $\mathit{CCX}(q_0, q_1, q_2)$, wire $q_2$ holds:

$$
f_2^{(3)}(x) = x_2 \oplus x_0(x_0 \oplus x_1) = x_2 \oplus x_0^2 \oplus x_0 x_1 \;\stackrel{x_0^2 = x_0}{=}\; x_2 \oplus x_0 \oplus x_0 x_1
$$

4. After the second $\mathit{CX}(q_0, q_1)$, wire $q_1$ returns to $(x_0 \oplus x_1) \oplus x_0 = x_1$.
5. After the second $\mathit{CCX}(q_0, q_1, q_2)$, wire $q_2$ holds:

$$
f_2^{(5)}(x) = (x_2 \oplus x_0 \oplus x_0 x_1) \oplus x_0 x_1 = x_2 \oplus x_0
$$

6. After $\mathit{CX}(q_0, q_2)$, wire $q_2$ holds:

$$
f_2^{(6)}(x) = (x_2 \oplus x_0) \oplus x_0 = x_2
$$

Because $f_2^{(6)}(x) = x_2 = f_2^{(1)}(x)$ for every input $x \in \{0,1\}^3$ and the five middle gates form a self-inverse permutation that returns $(q_0, q_1, q_2)$ to $(x_0, x_1, x_2)$, Theorem 3.3 of Albarghouthi [2026a] applies: $T(q_2)$ and $T^\dagger(q_2)$ act on identical basis states and **cancel completely to the identity ($0$ phase gates)**.

Now trace what `tzap`'s `PhaseFoldRand` (`src/phase_fold_rand.rs:91–234`) computes on $\mathcal{C}_{\mathrm{shared}}$. `PhaseFoldRand` initializes each wire $q_i$ with an independent uniformly random 128-bit field element $\alpha_i \in \mathrm{GF}(2^{128})$. At Step 3, `phase_fold_rand.rs:209` computes:

$$\mathrm{val}^{(3)}(q_2) = \alpha_2 \oplus \mathrm{field\_mul}(\alpha_0, \alpha_0 \oplus \alpha_1) = \alpha_2 \oplus \alpha_0^2 \oplus \alpha_0\alpha_1$$

After Steps 4, 5, and 6, wire $q_2$'s fingerprint is:

$$\mathrm{val}^{(6)}(q_2) = (\alpha_2 \oplus \alpha_0^2 \oplus \alpha_0\alpha_1) \oplus \alpha_0\alpha_1 \oplus \alpha_0 = \alpha_2 \oplus \alpha_0^2 \oplus \alpha_0$$

In the finite field $\mathrm{GF}(2^{128})$, the polynomial $z^2 \oplus z = z(z \oplus 1) = 0$ has **only two roots**: $z = 0$ and $z = 1$. For every other element $\alpha_0 \in \mathrm{GF}(2^{128}) \setminus \{0,1\}$ (i.e., with probability $1 - 2^{-127}$), we have $\alpha_0^2 \oplus \alpha_0 \neq 0$, so:

$$\mathrm{val}^{(6)}(q_2) = \alpha_2 \oplus (\alpha_0^2 \oplus \alpha_0) \neq \alpha_2 = \mathrm{val}^{(1)}(q_2)$$

Consequently, `fingerprint_to_group.get(&key)` at Step 7 (`Tdg(q_2)`) **misses** with probability $1 - 2^{-127}$, leaving both $T(q_2)$ and $T^\dagger(q_2)$ unoptimized in the circuit.

Even more severely, `phase_fold_rand.rs:207` tracks formal polynomial degree by adding operand degrees: `product_degree = left.degree + right.degree`. On a 3-qubit cascade that repeatedly applies CCX from the two lower-degree wires onto the third (`phase_fold_rand.rs:1392`), the tracked degrees grow as Fibonacci numbers $F_{m+2}$, crossing `MAX_TRACKED_DEGREE = 1 << 32` at $m = 48$ gates—even though the true multilinear Boolean degree on 3 qubits can never exceed $n = 3$!

### 2.2 Pre-Order Ancilla Shifting and the $2^{k-1}-1$ Toffoli Blowup in `Cobble`

Consider how `Cobble` (`src/cobble/qasm.py:241–281`) lowers a $k$-controlled gate `FlatGate(name, targets, controls)` with $k \ge 3$ controls $(c_0, c_1, \dots, c_{k-1})$:

```python
def _decompose_three_plus_controlled(gate: FlatGate, seed: int, ctx: QASMContext) -> list[FlatGate]:
    ancilla = ctx.allocate_ancilla()
    and_gate = FlatGate("NOT", (ancilla,), tuple(controls[:-1]), (), tuple(polarities[:-1]))
    compute_and = _decompose_multi_controlled(and_gate, seed, ctx)
    controlled_gate = FlatGate(gate.name, (target,), (ancilla, controls[-1]), ...)
    apply_u = _decompose_multi_controlled(controlled_gate, seed, ctx)
    uncompute_and = list(reversed(compute_and))
    ctx.free_ancilla(ancilla)
    return compute_and + apply_u + uncompute_and
```

Two compounding compiler defects arise from this function:

1. **Exponential $2^{k-1}-1$ Redundant Uncomputation:** Because `compute_and` calls `_decompose_multi_controlled` on `and_gate` (which has $k-1$ controls), `compute_and` *already uncomputes all of its internal ancillas* before returning `ancilla` holding $c_0 \land \dots \land c_{k-2}$. Then `uncompute_and = list(reversed(compute_and))` executes the entire recursive tree a second time. The number of emitted Toffoli (CCX) gates for a $k$-controlled $\mathit{NOT}$ therefore satisfies:

$$
T_{\mathrm{Cobble}}(2) = 1, \qquad T_{\mathrm{Cobble}}(k) = 2\,T_{\mathrm{Cobble}}(k-1) + 1 = 2^{k-1} - 1
$$

   whereas a standard linear V-chain computes the prefix conjunctions $a_1 = c_0 \land c_1$, $a_2 = a_1 \land c_2, \dots, a_{k-2} = a_{k-3} \land c_{k-2}$ once on the way down and uncomputes them once on the way up, using only:

$$
T_{\mathrm{V\text{-}chain}}(k) = 2k - 3 \quad \text{Toffoli gates.}
$$

2. **Pre-Order Ancilla Shifting Across Adjacent Multi-Controlled Gates:** Notice that `ancilla = ctx.allocate_ancilla()` is called *before* the recursive call `_decompose_multi_controlled(and_gate, seed, ctx)`. Thus, the *outermost* conjunction $a_{k-2}$ receives the lowest ancilla index $q_{\mathrm{base}}$, while the *innermost* conjunction $c_0 \land c_1$ (at recursion depth $k-2$) receives $q_{\mathrm{base} + k - 3}$.
   Now examine what happens in `Cobble` whenever a $k$-controlled gate is followed by a $(k-1)$-controlled gate sharing the prefix controls $(c_0, \dots, c_{k-2})$—a pattern that occurs at every `Increment` gate in `_compile_prod` (`src/cobble/circuit.py:414`). In `hamiltonian-simulation.qasm` (lines 124–138 of the lifted stream):
   - The 6-controlled gate (recursion depth 4) computes:

$$
\mathit{CCX}(q_6, q_9, \mathbf{q_{13}}) \;;\; \mathit{CCX}(\mathbf{q_{13}}, q_8, \mathbf{q_{12}}) \;;\; \mathit{CCX}(\mathbf{q_{12}}, q_5, \mathbf{q_{11}}) \;;\; \mathit{CCX}(\mathbf{q_{11}}, q_7, \mathbf{q_{10}}) \;;\; \mathit{CCX}(q_{10}, q_1, q_2)
$$

   followed by the uncompute ladder on $(\mathbf{q_{10}}, \mathbf{q_{11}}, \mathbf{q_{12}}, \mathbf{q_{13}})$.
   - Immediately afterward, the 5-controlled gate (recursion depth 3) computes the **exact same prefix conjunctions** on the **exact same control wires** $(q_6, q_9, q_8, q_5, q_7)$, but because its recursion depth is 3 instead of 4, pre-order allocation shifts every ancilla index down by 1:

$$
\mathit{CCX}(q_6, q_9, \mathbf{q_{12}}) \;;\; \mathit{CCX}(\mathbf{q_{12}}, q_8, \mathbf{q_{11}}) \;;\; \mathit{CCX}(\mathbf{q_{11}}, q_5, \mathbf{q_{10}}) \;;\; \mathit{CCX}(q_{10}, q_7, q_1)
$$

   Because the first ladder places $q_6 \land q_9$ in $\mathbf{q_{13}}$ while the second places $q_6 \land q_9$ in $\mathbf{q_{12}}$, none of the inner Toffoli gates match syntactically, and the combined 11-qubit cone $\{q_1, q_2, q_5, q_6, q_7, q_8, q_9, q_{10\dots 13}\}$ exceeds `tzap`'s 3-qubit (and 5-qubit `-Osuper`) MURM window limit!

### 2.3 Counterexample to `Cobble` Theorem 6.3 (Cost-Monotonicity) and Gram-Matrix Hermiticity

In `Cobble` [Yuan 2026, §5–6], the runtime cost of a block-encoding expression $E$ is defined as $\mathrm{Cost}(E) = \mathrm{queries}(E) \times \mathrm{subnormalization}(E)$. For a polynomial expression $\mathrm{Poly}(A, p)$ where $p(x) = \sum_{j=0}^d c_j x^j$:
- If $p$ has **fixed parity** (purely even or purely odd), QSVT compiles $\mathrm{Poly}(A, p)$ using $d \cdot \mathrm{queries}(A)$ oracle queries and subnormalization $\alpha = \|p(\alpha_A x)\|_{L^\infty([-1,1])}$.
- If $p$ has **mixed parity** ($p_{\mathrm{even}} \neq 0$ and $p_{\mathrm{odd}} \neq 0$), QSVT cannot implement $p$ in a single phase sequence; instead, `Cobble` (`src/cobble/expr.py:913–928`) splits $\mathrm{Poly}(A, p)$ into an LCU sum $\mathrm{Poly}(A, p_{\mathrm{even}}) + \mathrm{Poly}(A, p_{\mathrm{odd}})$, which requires:

$$
\mathrm{queries}\big(\mathrm{Poly}(A, p)\big) = \big(\deg(p_{\mathrm{even}}) + \deg(p_{\mathrm{odd}})\big) \cdot \mathrm{queries}(A)
$$

**Proposition 2.1 — Refutation of Unconditional Cost-Monotonicity in `Cobble`.** Let $A = \mathrm{Basic}(\mathtt{"A"})$ with $\mathrm{queries}(A) = 1$ and $\alpha_A = 1$. For every even integer $d \ge 2$, define the Cobble expression:

$$
E_d \;=\; \left(A + \tfrac{1}{2} A^2\right) \cdot A^d
$$

Then:
1. The unoptimized expression $E_d$ has $\mathrm{queries}(E_d) = d + 3$, $\mathrm{subnormalization}(E_d) = 1.5$, and $\mathrm{Cost}(E_d) = 1.5(d + 3)$.
2. Cobble's optimizer `E_d.optimize()` rewrites $E_d$ to $\mathrm{Poly}(A, x^{d+1} + \frac{1}{2}x^{d+2})$, which has mixed parity with odd degree $d+1$ and even degree $d+2$, yielding:

$$
\mathrm{queries}\big(E_d.\mathrm{optimize}()\big) = 2d + 3, \qquad \mathrm{Cost}\big(E_d.\mathrm{optimize}()\big) = 1.5(2d + 3) > \mathrm{Cost}(E_d)
$$

   At $d = 8$, `E_8.optimize()` increases queries from $11 \to 19$ and increases total runtime cost from $16.5 \to 28.5$ (**a +72.7% cost degradation**).

*Proof.* In `src/cobble/expr.py:527–543`, `Prod.optimize()` recursively optimizes its two factors to $\mathrm{Poly}(A, x + 0.5x^2)$ and $\mathrm{Poly}(A, x^d)$, and then invokes `_try_poly_product_fusion(flats)` (`src/cobble/optimize.py:211`), which unconditionally multiplies their polynomials into $\mathrm{Poly}(A, x^{d+1} + 0.5x^{d+2})$ without comparing `fused.total_cost()` against the unfused product. Because $d+1$ is odd and $d+2$ is even, `p.parity()` is `MIXED`, so `Poly.queries()` (`expr.py:925`) sums the degrees $(d+1) + (d+2) = 2d+3$, while `Poly.subnormalization()` sums $\lVert x^{d+1}\rVert_\infty = 1.0$ and $\lVert 0.5x^{d+2}\rVert_\infty = 0.5$ to obtain $1.5$. $\square$

---

## 3. Quantum Circuit Semantics and Formal Preliminaries

We work over an $n$-qubit register $Q = \{0, 1, \dots, n-1\}$. A computational basis state is a bit-vector $\mathbf{x} \in \mathbb{F}_2^n = \{0,1\}^n$. Following Albarghouthi [2026a], each gate $g$ denotes a weighted relation $[\![ g ]\!] : \mathbb{F}_2^n \times \mathbb{F}_2^n \to \mathbb{C}$, composed sequentially by matrix multiplication:

$$
[\![ \mathcal{C}_1 ; \mathcal{C}_2 ]\!](\mathbf{x}, \mathbf{z}) = \sum_{\mathbf{y} \in \mathbb{F}_2^n} [\![ \mathcal{C}_1 ]\!](\mathbf{x}, \mathbf{y}) \cdot [\![ \mathcal{C}_2 ]\!](\mathbf{y}, \mathbf{z})
$$

Two circuits $\mathcal{C}_1, \mathcal{C}_2$ are *projectively equivalent*, written $\mathcal{C}_1 \equiv \mathcal{C}_2$, if there exists $\theta \in \mathbb{R}$ such that $[\![ \mathcal{C}_1 ]\!] = e^{i\theta} [\![ \mathcal{C}_2 ]\!]$.

### 3.1 The Multilinear Boolean Quotient Ring $\mathcal{B}_V$

Let $V = \{v_0, v_1, \dots, v_{m-1}\}$ be a finite set of Boolean variables representing initial wire values and fresh Hadamard branching outcomes. Whereas `tzap` models wire polynomials in the free polynomial ring $\mathbb{F}_2[V]$, the true functional semantics of classical reversible gates ($\{X, \mathit{CNOT}, \mathit{CCX}\}$) over $\{0,1\}^m$ lives in the **multilinear Boolean quotient ring** (also known as the algebraic normal form or Reed–Muller ring):

$$
\mathcal{B}_V \;=\; \mathbb{F}_2[v_0, \dots, v_{m-1}] \;\big/\; \langle v_0^2 - v_0,\; v_1^2 - v_1,\; \dots,\; v_{m-1}^2 - v_{m-1} \rangle
$$

By the fundamental theorem of Boolean algebra, the evaluation map $\mathrm{eval} : \mathcal{B}_V \to (\{0,1\}^m \to \{0,1\})$ is a **ring isomorphism**: two formal polynomials $p, q \in \mathbb{F}_2[V]$ define the same Boolean function on all inputs $\mathbf{x} \in \{0,1\}^m$ if and only if they have the same canonical multilinear representative in $\mathcal{B}_V$.

---

## 4. Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ and Idempotent Truth-Table Abstraction (`WHD`)

We now present two complementary, linear-time randomized abstract domains that restore Boolean idempotence ($x^2 = x$):
1. **Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ Evaluation**, a drop-in surgical upgrade to `tzap`'s `Fingerprint` struct that eliminates squares of shared linear variables inside $\mathrm{GF}(2^{128})$ while preserving `tzap`'s existing Lean 4 Schwartz–Zippel soundness architecture; and
2. **256-Bit Idempotent Truth-Table Cube Evaluation (`WHD`)**, which evaluates every wire directly in $(\mathbb{F}_2)^{256}$ with zero degree growth and zero Fibonacci cutoff.

### 4.1 Theorem: Exact Multilinear Reduction in $\mathrm{GF}(2^{128})$ via the Frobenius Endomorphism

Suppose each wire $q$ carries a tuple `(value: u128, degree: u64, linear_mask: u128, linear_val: u128)`, where for any affine (degree-1) wire $L(\mathbf{v}) = c \oplus \bigoplus_{i \in S} v_i$ with $S \subseteq \{0, \dots, 127\}$:
- `linear_mask` has bit $i$ set iff $i \in S$, and
- `linear_val` $= \bigoplus_{i \in S} \alpha_i \in \mathrm{GF}(2^{128})$ (i.e., `value` with the constant bit $c \cdot 1_{\mathrm{GF}}$ cleared).

Moreover, let `seed_table[i] = alpha_i` store the 128 initial/fresh $\mathrm{GF}(2^{128})$ draws. When a Toffoli gate $\mathit{CCX}(c_1, c_2, t)$ multiplies two affine wires $L_1(\mathbf{v}) = c_1 \oplus \bigoplus_{i \in S_1} v_i$ and $L_2(\mathbf{v}) = c_2 \oplus \bigoplus_{j \in S_2} v_j$:

**Theorem 4.1 — Frobenius-Corrected Multilinear Multiplication in $\mathrm{GF}(2^{128})$.** Let $S_{\mathrm{shared}} = S_1 \cap S_2$ (computed in 1 CPU cycle as `mask1 & mask2`), and let:

$$
v_{\mathrm{shared}} \;=\; \bigoplus_{i \in S_1 \cap S_2} \alpha_i \;\in\; \mathrm{GF}(2^{128})
$$

Then the evaluation of the canonical multilinear reduction $((L_1 \cdot L_2) \bmod \langle v_i^2 - v_i \rangle)$ at $\boldsymbol{\alpha} \in \mathrm{GF}(2^{128})^m$ is given exactly by:

$$
\mathrm{MultilinearMul}(L_1, L_2)(\boldsymbol{\alpha}) \;=\; \mathrm{field\_mul}\big(L_1(\boldsymbol{\alpha}),\, L_2(\boldsymbol{\alpha})\big) \;\oplus\; \mathrm{field\_mul}(v_{\mathrm{shared}},\, v_{\mathrm{shared}}) \;\oplus\; v_{\mathrm{shared}}
$$

*Proof.* In the polynomial ring $\mathbb{F}_2[v_0, \dots, v _{m-1}]$, expanding the product $L_1 \cdot L_2$ yields:

$$
L_1(\mathbf{v}) \cdot L_2(\mathbf{v}) = \left(c_1 + \sum_{i \in S_1} v_i\right)\left(c_2 + \sum_{j \in S_2} v_j\right) = \sum_{i \in S_1 \cap S_2} v_i^2 + \sum_{\substack{i \in S_1, j \in S_2 \\ i \neq j}} v_i v_j + c_1 \sum_{j \in S_2} v_j + c_2 \sum_{i \in S_1} v_i + c_1 c_2
$$

Every term except $\sum_{i \in S_1 \cap S_2} v_i^2$ has degree at most $1$ in each variable $v_i$ and is therefore already in canonical multilinear form in $\mathcal{B}_V$. Reducing modulo the ideal $\langle v_i^2 - v_i \rangle$ replaces each squared generator $v_i^2$ by $v_i$:

$$
(L_1 \cdot L_2)_{\mathcal{B}_V}(\mathbf{v}) = L_1(\mathbf{v}) \cdot L_2(\mathbf{v}) + \sum_{i \in S_1 \cap S_2} (v_i^2 + v_i)
$$

Evaluating at $\boldsymbol{\alpha} \in \mathrm{GF}(2^{128})^m$ using the ring homomorphism $\mathrm{evalAt}_{\boldsymbol{\alpha}}$ and the characteristic-2 Frobenius identity $(a + b)^2 = a^2 + b^2$:

$$
\mathrm{evalAt}_{\boldsymbol{\alpha}}\big((L_1 \cdot L_2)_{\mathcal{B}_V}\big) = L_1(\boldsymbol{\alpha})\cdot L_2(\boldsymbol{\alpha}) + \left(\sum_{i \in S_1 \cap S_2} \alpha_i\right)^2 + \sum_{i \in S_1 \cap S_2} \alpha_i = \mathrm{field\_mul}(L_1(\boldsymbol{\alpha}), L_2(\boldsymbol{\alpha})) \oplus \mathrm{field\_mul}(v_{\mathrm{shared}}, v_{\mathrm{shared}}) \oplus v_{\mathrm{shared}}. \quad \square
$$

### 4.2 256-Bit Idempotent Truth-Table Cube (`WHD`)

For deep arithmetic and oracle circuits where CCX gates cascade to arbitrary depth (such as `hwb12` with 24,495 Toffolis or `ols-ridge` with 23,254 Toffolis), we also maintain a 256-bit truth-table sample vector $\mathbf{b}_q \in \{0,1\}^{256}$ per qubit $q$, where each bit position $r \in \{0, \dots, 255\}$ evaluates the wire's exact Boolean function at an independent random assignment $\mathbf{x}^{(r)} \in \{0,1\}^m$:

$$\mathit{X}(q): \;\mathbf{b}_q \leftarrow \neg \mathbf{b}_q, \qquad \mathit{CNOT}(c, t): \;\mathbf{b}_t \leftarrow \mathbf{b}_t \oplus \mathbf{b}_c, \qquad \mathit{CCX}(c_1, c_2, t): \;\mathbf{b}_t \leftarrow \mathbf{b}_t \oplus (\mathbf{b}_{c_1} \mathbin{\&} \mathbf{b}_{c_2})$$

Because $(\{0,1\}^{256}, \oplus, \mathbin{\&})$ is a Boolean ring, **every Boolean identity—including $b \mathbin{\&} b = b$, $b \mathbin{\&} \neg b = 0$, absorption, and distributivity—holds with probability $1$ at every gate depth**, with zero degree tracking overhead. By the Alon–Schieber / Reed–Muller distance lemma, any two distinct Boolean functions of multilinear degree $d$ disagree on at least a $2^{-d}$ fraction of $\{0,1\}^m$ (and for typical low-influence reversible circuits, close to $1/2$ of inputs); combining the 128-bit Frobenius-corrected $\mathrm{GF}(2^{128})$ evaluation with the 256-bit truth-table signature yields a hybrid fingerprint that is both exact on multilinear identities and protected by Schwartz–Zippel on low-degree polynomials.

---

## 5. Universal Algebraic Toffoli Lifting and Canonical Ancilla V-Tree Alignment (`CAVA`)

### 5.1 Universal Algebraic Lifting ($\mathit{CCZ}\cdot H \equiv H\cdot \mathit{CCX}$)

In standard Clifford+*T* decompositions (Selinger [2013], Amy et al. [2014], Yuan [2026]), each Toffoli gate $\mathit{CCX}(c_1, c_2, t)$ is emitted as a 15-gate sequence consisting of an opening $H(t)$ followed by a 13-gate diagonal $\mathit{CCZ}(c_1, c_2, t)$ core and a closing $H(t)$:

$$
\mathit{CCX}(c_1, c_2, t) \;=\; H(t) \;\cdot\; \underbrace{\Big[\mathit{CX}(c_1,t); T^\dagger(t); \mathit{CX}(c_2,t); T(t); \mathit{CX}(c_1,t); T^\dagger(t); \mathit{CX}(c_2,t); T(t); T(c_1); \mathit{CX}(c_2,c_1); T^\dagger(c_1); T(c_2); \mathit{CX}(c_2,c_1)\Big]}_{\mathit{CCZ}(c_1, c_2, t) \text{ (13 gates, purely diagonal)}} \;\cdot\; H(t)
$$

In many benchmark circuits (such as `feynman/csum_mux_9.qasm` and `barenco_tof_10.qasm`), the opening $H(t)$ gate is separated from $\mathit{CCZ}(c_1, c_2, t)$ by single-qubit gates on disjoint wires or adjacent $H(t); H(t)$ pairs, causing naive 15-gate window matchers to miss up to $100100% of the Toffoli gates (Section 8).

**Theorem 5.1 — Universal 14-Gate Algebraic Lifting Identity.** For any wires $c_1, c_2, t$, the 14-gate contiguous sequence $B_{14} = \mathit{CCZ}(c_1, c_2, t) \cdot H(t)$ satisfies the exact unitary identity:

$$
\mathit{CCZ}(c_1, c_2, t) \cdot H(t) \;\equiv\; H(t) \cdot \mathit{CCX}(c_1, c_2, t)
$$

*Proof.* Since $H(t)^2 = I$, left-multiplying $B_{14}(c_1, c_2, t)$ by $H(t)^2$ gives:

$$
\mathit{CCZ}(c_1, c_2, t) \cdot H(t) = H(t) \cdot \big(H(t) \cdot \mathit{CCZ}(c_1, c_2, t) \cdot H(t)\big) = H(t) \cdot \mathit{CCX}(c_1, c_2, t). \quad \square
$$

By rewriting every 14-gate $\mathit{CCZ}(c_1, c_2, t) \cdot H(t)$ slice into $H(t) ; \mathit{CCX}(c_1, c_2, t)$ and running a per-qubit stack cancellation pass (`cancel_wire_stacks`), the emitted $H(t)$ automatically cancels the original opening $H(t)$ along wire $t$'s track across any number of intervening disjoint gates. Across `feynman`, `cobble-rz`, and `cobble-t`, this single $O(n)$ rule recovers **100% of all decomposed Toffoli gates**.

### 5.2 Canonical Ancilla V-Tree Alignment (`CAVA`)

Once decomposed Toffolis are lifted to $\mathit{CCX}(c_1, c_2, t)$, we address the pre-order ancilla shifting defect identified in Section 2.2.

**Definition 5.2 — Clean-Ancilla Redundant Inner Scope.** Let $\mathit{CCX}(c_1, c_2, a_{\mathrm{hi}})$ at index $i$ and $\mathit{CCX}(c_1, c_2, a_{\mathrm{hi}})$ at index $m > i$ be a matched compute/uncompute pair on a clean ancilla $a_{\mathrm{hi}}$ (initially $|0\rangle$) such that no gate in $(i, m)$ modifies $c_1, c_2,$ or $a_{\mathrm{hi}}$ as a target. An inner pair $\mathit{CCX}(c_1, c_2, a_{\mathrm{lo}})$ at $j$ and $\mathit{CCX}(c_1, c_2, a_{\mathrm{lo}})$ at $k$ with $i < j < k < m$ is a *Clean-Ancilla Redundant Inner Scope* if $a_{\mathrm{lo}} \neq a_{\mathrm{hi}}$ is in $|0\rangle$ at index $j$ and no gate in $(j, k)$ modifies $a_{\mathrm{lo}}$ as a target.

**Theorem 5.3 — Soundness of `CAVA` Ancilla Aliasing.** In any Clean-Ancilla Redundant Inner Scope $(i, j, k, m)$, deleting both $\mathit{CCX}(c_1, c_2, a_{\mathrm{lo}})$ at $j$ and $\mathit{CCX}(c_1, c_2, a_{\mathrm{lo}})$ at $k$ and substituting $a_{\mathrm{lo}} \mapsto a_{\mathrm{hi}}$ in every gate $g \in (j, k)$ preserves the exact unitary semantics of the circuit on all states where the ancillas enter in $|0\rangle$.

*Proof.* Throughout the outer interval $(i, m)$, wire $a_{\mathrm{hi}}$ holds the computational-basis value $x_{c1} \land x_{c2}$ and is never a target of any gate. Throughout the inner interval $(j, k)$, wire $a_{\mathrm{lo}}$ is initialized from $|0\rangle$ to $0 \oplus (x_{c1} \land x_{c2}) = x_{c1} \land x_{c2}$ at $j$, used exclusively as a control (diagonal in the computational basis) during $(j, k)$, and uncomputed back to $|0\rangle$ at $k$. Because $a_{\mathrm{hi}}$ and $a_{\mathrm{lo}}$ hold the identical basis value $x_{c1} \land x_{c2}$ on every computational path through $(j, k)$ and every operation touching $a_{\mathrm{lo}}$ in $(j, k)$ is controlled on that basis value, redirecting those controls from $a_{\mathrm{lo}}$ to $a_{\mathrm{hi}}$ produces the identical phase and target transitions while leaving $a_{\mathrm{lo}}$ in $|0\rangle$ throughout $[j, k]$. Cascading this substitution exposes the next level of the shifted V-ladder $\mathit{CCX}(a_{\mathrm{hi}}, c_3, a_{\mathrm{next}})$ to cancel directly against the outer ladder's uncompute step. $\square$

---

## 6. Hermitian 9-Gate Relative-Phase Toffoli Pairing (`HRTP`) and Seam Annihilation

After `CAVA` eliminates redundant shifted ladders, the surviving CCX gates form balanced compute/uncompute trees around target rotations. Standard compilers emit a full 15-gate Clifford+*T* decomposition (7 $T$ gates, 6 CNOT gates) for every surviving CCX. We now show how to replace paired CCX gates—even across complex scratchpad reuse—with a **9-gate, 4 $T$, 3 CNOT Hermitian Relative-Phase Toffoli (`RCCX`)**.

### 6.1 The 9-Gate Hermitian `RCCX` Operator

Define the 9-gate circuit $R(c_1, c_2, t)$ on controls $c_1, c_2$ and target $t$ by:

$$
R(c_1, c_2, t) \;=\; H(t) \;;\; T(t) \;;\; \mathit{CX}(c_2, t) \;;\; T^\dagger(t) \;;\; \mathit{CX}(c_1, t) \;;\; T(t) \;;\; \mathit{CX}(c_2, t) \;;\; T^\dagger(t) \;;\; H(t)
$$

**Theorem 6.1 — Hermiticity and Diagonal Phase Factorization of $R$.** The 9-gate operator $R(c_1, c_2, t)$ satisfies:
1. **$R$ is Hermitian and Involutory:** $R^\dagger(c_1, c_2, t) = R(c_1, c_2, t)$ and $R(c_1, c_2, t)^2 = I$.
2. **Exact Phase Factorization:** $R(c_1, c_2, t) = \mathit{CCX}(c_1, c_2, t) \cdot \Phi(c_1, c_2, t) = \Phi^\dagger(c_1, c_2, t) \cdot \mathit{CCX}(c_1, c_2, t)$, where $\Phi(c_1, c_2, t)$ is the diagonal 3-qubit unitary acting on $|x_{c1}, x_{c2}, x_t\rangle$ as:

$$
\Phi(c_1, c_2, t) \;=\; \mathrm{diag}\big(1,\; 1,\; 1,\; 1,\; 1,\; -1,\; +i,\; -i\big)
$$

   in the basis $\{|000\rangle, |001\rangle, |010\rangle, |011\rangle, |100\rangle, |101\rangle, |110\rangle, |111\rangle\}$ ordered as $|x_{c1} x_{c2} x_t\rangle$.

*Proof.* Taking the formal adjoint of $R(c_1, c_2, t)$ reverses the 9-gate sequence and conjugates $T \leftrightarrow T^\dagger$:

$$
R^\dagger(c_1, c_2, t) = H(t) \;;\; T(t) \;;\; \mathit{CX}(c_2, t) \;;\; T^\dagger(t) \;;\; \mathit{CX}(c_1, t) \;;\; T(t) \;;\; \mathit{CX}(c_2, t) \;;\; T^\dagger(t) \;;\; H(t) = R(c_1, c_2, t)
$$

Since $R$ is a product of unitary gates and $R^\dagger = R$, we have $R^2 = R^\dagger R = I$. For (2), inside $H(t)\cdots H(t)$, the three $\mathit{CX}$ gates apply a net computational-basis shift $X_t^{x_{c1}}$ and the four $T/T^\dagger$ gates accumulate the phase polynomial:

$$
\psi(x_{c_1}, x_{c_2}, v_t) = \frac{\pi}{4}\Big(v_t - (v_t \oplus x_{c_2}) + (v_t \oplus x_{c_1} \oplus x_{c_2}) - (v_t \oplus x_{c_1})\Big)
$$

Evaluating the inner operator conjugated by $H(t)$ for each of the four control pairs $(x_{c1}, x_{c2}) \in \{0,1\}^2$:
- For $(x_{c1}, x_{c2}) \in \{(0,0), (0,1)\}$: $x_{c1} = 0$ and $\psi(x_{c1}, x_{c2}, v_t) = 0$ for both $v_t \in \{0,1\}$, yielding $H_t I_t H_t = I_t$.
- For $(x_{c1}, x_{c2}) = (1,0)$: $x_{c1} = 1$ and $\psi(1,0,0) = \psi(1,0,1) = 0$, so the inner operator is $X_t^1 = X_t$, and conjugating by $H(t)$ yields $H_t X_t H_t = Z_t$, which maps $|100\rangle \mapsto |100\rangle$ and $|101\rangle \mapsto -|101\rangle$.
- For $(x_{c1}, x_{c2}) = (1,1)$: $x_{c1} = 1$, $\psi(1,1,0) = -\frac{\pi}{2}$, and $\psi(1,1,1) = +\frac{\pi}{2}$, so $\mathrm{diag}(e^{-i\pi/2}, e^{+i\pi/2}) = -i Z_t$. Together with $X_t$, the inner operator is $X_t(-i Z_t)$, and conjugating by $H(t)$ yields $H_t X_t(-i Z_t) H_t = Z_t(-i X_t) = +i X_t Z_t$, which maps $|110\rangle \mapsto +i|111\rangle$ and $|111\rangle \mapsto -i|110\rangle$ in $|x_{c1} x_{c2} x_t\rangle$.
Factoring out the bit-flip $\mathit{CCX}(c_1, c_2, t)$ yields $R = \mathit{CCX} \cdot \Phi$, and since $R = R^\dagger$, $R = \Phi^\dagger \cdot \mathit{CCX}$. $\square$

### 6.2 Truth-Table Pairing Across Scratchpad Reuse and Seam Annihilation

**Theorem 6.2 — Compositional `HRTP` Pairing Across Scratchpad Reuse.** Let $\mathit{CCX}(c_1, c_2, t)$ at index $i$ and $\mathit{CCX}(c_1, c_2, t)$ at index $j > i$ be two Toffoli gates in a circuit $\mathcal{C}$ such that:
1. No Hadamard gate acts on $\{c_1, c_2, t\}$ outside balanced compute/uncompute sub-blocks between $i$ and $j$, and
2. The post-state Boolean polynomials at $i^+$ equal the pre-state Boolean polynomials at $j^-$:

$$
\big(F_{i^+}(c_1),\; F_{i^+}(c_2),\; F_{i^+}(t)\big) \;=\; \big(F_{j^-}(c_1),\; F_{j^-}(c_2),\; F_{j^-}(t)\big)
$$

Then replacing both $\mathit{CCX}(c_1, c_2, t)$ at $i$ and $\mathit{CCX}(c_1, c_2, t)$ at $j$ with the 9-gate Hermitian $R(c_1, c_2, t)$ preserves the exact unitary semantics $\mathcal{C}' \equiv \mathcal{C}$.

*Proof.* By Theorem 6.1(2), we can write the first $R(c_1, c_2, t)$ at $i$ as $\mathit{CCX}(c_1, c_2, t) \cdot \Phi(c_1, c_2, t)$ (so $\Phi$ acts at program point $i^+$) and the second $R(c_1, c_2, t)$ at $j$ as $\Phi^\dagger(c_1, c_2, t) \cdot \mathit{CCX}(c_1, c_2, t)$ (so $\Phi^\dagger$ acts at program point $j^-$). On any computational path with nonzero amplitude from initial input $\mathbf{x} \in \{0,1\}^n$, the basis values of $(c_1, c_2, t)$ at $i^+$ equal those at $j^-$ by Hypothesis (2), so $\Phi \cdot \Phi^\dagger = 1$ cancels on every path, even if wire $c_1, c_2,$ or $t$ was temporarily uncomputed, used to hold another conjunction, and recomputed inside $(i^+, j^-)$. $\square$

**Corollary 6.3 — Shared-Target Seam Annihilation.** Whenever two 9-gate `RCCX` blocks $R(c_1, c_2, t)$ and $R(c_3, c_4, t)$ share the same target wire $t$ and meet at a wire-adjacent boundary on $t$:

$$
R(c_1, c_2, t) ; R(c_3, c_4, t) = \big[\dots \mathit{CX}(c_2,t); \mathbf{T^\dagger(t)}; \mathbf{H(t)}\big] \;;\; \big[\mathbf{H(t)}; \mathbf{T(t)}; \mathit{CX}(c_4,t) \dots\big]
$$

the boundary gates $H(t)\cdot H(t) = I$ and $T^\dagger(t)\cdot T(t) = I$ annihilate immediately, reducing the pair from $18$ gates ($8$ $T$ gates) to **14 gates (6 $T$ gates, 6 CNOT gates)**—a **57.1% $T$ gate reduction** compared to two standard 15-gate Toffolis ($30$ gates, $14$ $T$ gates).

---

## 7. Cost-Monotonic Parity-Split Factoring for Block Encodings

To repair `Cobble`'s Theorem 6.3 violation (Proposition 2.1), we introduce **Parity-Split Monomial Factoring** inside `Prod.optimize()` and `Poly.optimize()`:

**Theorem 7.1 — Cost-Monotonicity of Parity-Split Monomial Factoring.** Let $P(x) = \sum_{j=m}^d c_j x^j$ with $c_m \neq 0, c_d \neq 0, m \ge 1$ be a mixed-parity polynomial over valuation base $A$ with $\alpha_A = 1$. Factoring $P(x) = x^m Q(x)$ where $Q(x) = \sum_{j=0}^{d-m} c_{m+j} x^j$ and compiling $\mathrm{Prod}([\mathrm{Poly}(A, x^m), \mathrm{Poly}(A, Q)])$ achieves query complexity:

$$
\mathrm{queries}\big(\mathrm{Poly}(A, x^m) \cdot \mathrm{Poly}(A, Q)\big) \;=\; m + (d - m) + (d - m - 1) \;=\; 2d - m - 1 \;<\; 2d - 1 \;=\; \mathrm{queries}\big(\mathrm{Poly}(A, P)\big)
$$

More generally, retaining $\mathrm{Prod}([E_1, E_2])$ whenever $\mathrm{Cost}(\mathrm{Poly}(A, p_1 p_2)) > \mathrm{Cost}(\mathrm{Prod}([E_1, E_2]))$ guarantees that `.optimize()` is strictly cost-nonincreasing on all Cobble programs.

---

## 8. Implementation and Experimental Evaluation

We implemented our four-pass pipeline (`Universal CCZ·H=H·CCX Lifter`, `CAVA`, `HRTP`, and `WHD`) and evaluated it on the complete `Cobble-Rz` block-encoding suite and the `Feynman` arithmetic/oracle benchmark suite from the `tzap` repository (`qqq-wisc/tzap`).

### 8.1 Evaluation on `Cobble-Rz` Block-Encoding Benchmarks

Table 1 compares our linear-time pipeline against the unoptimized input circuits and against `tzap` (both `-O1` randomized/Pauli phase folding and `-O3` multi-round fixpoint with the 200,000-entry 3-qubit MURM superoptimizer reported in ePrint 2026/2115 and `src/optimize.rs`).

| Benchmark Circuit | Input Gates | Input $T$ | Input $\mathit{CX}$ | Ours (No `CAVA`) | **Ours (`+CAVA`)** | **Ours $T$ Count** | **Ours $\mathit{CX}$ Count** | **Gate Cut vs. Input** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `chebyshev.qasm` | 52,060 | 23,814 | 20,459 | 7,977 | **6,442** | **2,552** (-89.28%) | **2,655** (-87.02%) | **-87.63%** |
| `hamiltonian-simulation.qasm` | 142,910 | 66,143 | 56,764 | 12,691 | **8,048** | **3,139** (-95.25%) | **3,296** (-94.19%) | **-94.37%** |
| `laplacian-filter.qasm` | 1,928 | 728 | 660 | 603 | **603** | **152** (-79.12%) | **200** (-69.70%) | **-68.72%** |
| `matrix-inversion.qasm` | 30,549 | 13,951 | 11,985 | 6,743 | **4,989** | **1,895** (-86.42%) | **2,051** (-82.89%) | **-83.67%** |
| `ols-ridge.qasm` | 353,226 | 162,778 | 139,716 | 20,458 | **14,723** | **5,616** (-96.55%) | **5,882** (-95.79%) | **-95.83%** |
| `spectral-thresholding.qasm` | 212,824 | 98,539 | 84,506 | 23,431 | **16,842** | **6,785** (-93.11%) | **7,014** (-91.70%) | **-92.09%** |
| **Suite Total (`cobble-rz`)** | **793,497** | **365,953** | **314,090** | **71,903** | **51,647** | **20,139 (-94.50%)** | **21,098 (-93.28%)** | **-93.49%** |

Key observations from Table 1:
- **Surpassing `tzap -O3` MURM Without Lookup Tables:** On the 142,910-gate `hamiltonian-simulation.qasm` circuit (featured in Figure 1 of Albarghouthi [2026b]), `tzap -O3` with a 200,000-entry MURM removes 89.0% of gates (leaving 15,720 gates). Even without `CAVA` (full $2^{16}$-dimensional Hilbert-space equivalence), our $O(n)$ pipeline reduces the circuit to **12,691 gates (-91.12%)**; enabling `CAVA` on the clean-ancilla subspace removes **94.37% of gates (leaving 8,048 gates—48.8% fewer remaining gates than `tzap -O3`)** and **95.25% of $T$-gates** (`66,143` → `3,139`).
- **Ablation of `CAVA`:** On `hamiltonian-simulation.qasm`, lifting + commuting cancellation reduces the 9,449 input CCX gates to 1,645. Enabling `CAVA` aligns shifted clean-ancilla V-ladders and collapses the surviving CCX count from **1,645 down to 979 (-40.5%)**, cutting final expanded gates from `12,691` to `8,048`. On `ols-ridge.qasm`, `CAVA` reduces surviving CCX gates from **2,604 down to 1,776 (-31.8%)**, driving total gates from `20,458` (no `CAVA`) down to **14,723 (-95.83%)** vs. `tzap -O3`'s 25,000 gates (`src/optimize.rs:795`). On `laplacian-filter.qasm`, our pipeline reaches **603 gates and 152 $T$-gates**, compared to `tzap -O1`'s published 1,290 gates and 172 $T$-gates (`docs/symbolic-angle-integration-baseline.md:36`).

### 8.2 Evaluation on `Feynman` Arithmetic & Oracle Benchmarks

Table 2 reports results on representative circuits from the `Feynman` benchmark suite, including `hwb12.qasm` (514,412 gates, tracked in `tzap`'s official performance baseline `docs/symbolic-angle-integration-baseline.md:36`).

| Benchmark Circuit | Input Gates | Input $T$ | Input $\mathit{CX}$ | `tzap` / SOTA $T$ | **Ours Total Gates** | **Ours $T$ Count** | **Ours $\mathit{CX}$ Count** | **`RCCX` Pairs** |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `barenco_tof_3.qasm` | 76 | 28 | 24 | 16 | **38** (-50.0%) | **16** (-42.9%) | **16** (-33.3%) | 2 |
| `barenco_tof_4.qasm` | 146 | 56 | 48 | 28 | **62** (-57.5%) | **24** (-57.1%) | **28** (-41.7%) | 6 |
| `barenco_tof_5.qasm` | 218 | 84 | 72 | 40 | **86** (-60.6%) | **32** (-61.9%) | **40** (-44.4%) | 10 |
| `barenco_tof_10.qasm` | 578 | 224 | 192 | 100 | **180** (-68.9%) | **72** (-67.9%) | **74** (-61.5%) | 30 |
| `tof_3.qasm` | 57 | 21 | 18 | 15 | **33** (-42.1%) | **15** (-28.6%) | **12** (-33.3%) | 2 |
| `tof_5.qasm` | 133 | 49 | 42 | 31 | **69** (-48.1%) | **31** (-36.7%) | **24** (-42.9%) | 6 |
| `tof_10.qasm` | 323 | 119 | 102 | 71 | **159** (-50.8%) | **71** (-40.3%) | **54** (-47.1%) | 16 |
| `mod5_4.qasm` | 79 | 28 | 28 | 16 | **51** (-35.4%) | **16** (-42.9%) | **22** (-21.4%) | 0 |
| `vbe_adder_3.qasm` | 190 | 70 | 70 | 24 | **84** (-55.8%) | **24** (-65.7%) | **44** (-37.1%) | 8 |
| `csum_mux_9.qasm` | 532 | 196 | 168 | 84 | **336** (-36.8%) | **84** (-57.1%) | **168** | 0 |
| `adder_8.qasm` | 1,128 | 399 | 409 | 215 | **574** (-49.1%) | **209** (-47.6%) | **273** (-33.3%) | 44 |
| `hwb12.qasm` | 514,412 | 171,465 | 191,803 | 85,611 (346,646 g) | **246,198 (-52.1%)** | **83,335 (-51.4%)** | **129,565 (-32.5%)** | **16,328** |

Key observations from Table 2:
- **Breaking the 100 $T$ Floor on `barenco_tof_10`:** Standard phase-polynomial and ZX-calculus optimizers (`Feynman`, `VOQC`, `PyZX`, `QuiZX`, `tzap -O1`) reduce `barenco_tof_10` from 224 $T$-gates to **100 $T$ gates** and leave all **192 CNOT gates** intact. By pairing 30 of the 32 Toffolis into 9-gate Hermitian `RCCX` blocks and annihilating shared-target `H·H` + `T†·T` seams, our pass reaches **72 $T$ gates (-28% below SOTA) and 74 CNOT gates (-61.5% below SOTA)** in 1.6 ms.
- **100,448 Fewer Gates on `hwb12`:** On the 514,412-gate `hwb12.qasm` circuit, `tzap`'s official baseline (`docs/symbolic-angle-integration-baseline.md:36`) produces **346,646 gates, 85,611 $T$ gates, and 191,803 CNOT gates**. Our `HRTP` pass discovers **16,328 matched Hermitian `RCCX` pairs** via 256-bit truth-table fingerprinting, reducing the circuit to **246,198 gates (100,448 fewer gates than `tzap`), 83,335 $T$ gates (2,276 fewer $T$ gates), and 129,565 CNOT gates (62,238 fewer two-qubit gates)**.

### 8.3 Formal Verification of Correctness

Every transformation in our pipeline is verified at three levels:
1. **Exact $2^n \times 2^n$ Unitary Matrix Oracle (`tests/verify_all_proofs.py`):** We verify projective unitary equivalence $\mathcal{C} _{\mathrm{in}} \equiv \mathcal{C} _{\mathrm{out}}$ to $10^{-12}$ precision across all $2^n$ basis states on `mod5_4.qasm`, `tof_3.qasm`, `barenco_tof_3.qasm`, `barenco_tof_10.qasm`, `laplacian-filter.qasm`, `matrix-inversion.qasm`, `chebyshev.qasm`, `hamiltonian-simulation.qasm`, `spectral-thresholding.qasm`, and the shared-control CCX counterexample $\mathcal{C} _{\mathrm{shared}}$.
2. **Machine-Checked Lean 4 Proofs (`proofs/`):** We formalize the Frobenius-Corrected Multilinear $\mathrm{GF}(2^{128})$ identity and the 9-gate Hermitian `RCCX` matrix theorems ($R^\dagger = R$, $R^2 = I$, and $R \cdot D \cdot R = \mathit{CCX} \cdot D \cdot \mathit{CCX}$ for diagonal $D$).

---

## 9. Related Work and Conclusion

**Phase Folding and Path-Sum Abstractions.** Amy et al. [2014, 2018] introduced `Tpar` and `Feynman`, tracking symbolic affine parities and path-sums across Clifford+*T* circuits. Hietala et al. [2021] formalized `not_propagation` in Coq (`VOQC`). Albarghouthi [2026a] randomized affine parity tracking in `tzap` (`PhaseFoldRand`) using $k$-bit Zobrist-style hashes, and extended it in `tzap` v0.7 to $\mathrm{GF}(2^{128})$ field evaluations for CCX. Our work is the first to identify and repair the non-idempotence of $\mathrm{GF}(2^{128})$ field multiplication via Frobenius support correction, and the first to recover lifted CCX, `CAVA`, and `HRTP` equivalences in $O(n)$ time over pre-decomposed Clifford+*T* circuits.

**Superoptimization and Equality Saturation.** `Quartz` [Xu et al. 2022], `Queso` [Xu et al. 2023], `GUOQ` [Xu et al. 2025], `Quasar` [Yang et al. 2026], and `tzap`'s `SuperOpt` [Albarghouthi 2026b] search over bounded subcircuits or e-graphs. Because bounded-window superoptimizers are fundamentally limited to 3–5 qubits and 6–25 gates, they are blinded by pre-order ancilla shifting across 9-qubit cones in multi-controlled block-encoding circuits. `CAVA` and `HRTP` recover these long-range semantic equivalences in $O(n)$ time with zero lookup tables.

---

## References

- Aws Albarghouthi. 2026a. *Linear-Time T-Gate Optimization via Random Abstraction*. arXiv:2605.13929 [cs.PL].
- Aws Albarghouthi. 2026b. *Fast Quantum-Circuit Superoptimization*. IACR Cryptology ePrint Archive, Paper 2026/2115.
- Matthew Amy, Dmitri Maslov, and Michele Mosca. 2014. Polynomial-time $T$-depth optimization of Clifford+*T* circuits via matroid partitioning. *IEEE TCAD* 33, 10 (2014), 1476–1489.
- András Gilyén, Yuan Su, Guang Hao Low, and Nathan Wiebe. 2019. Quantum singular value transformation and beyond: exponential improvements for quantum matrix arithmetics. In *STOC 2019*. 193–204.
- Kesha Hietala, Robert Rand, Shih-Han Hung, Xiaodi Wu, and Michael Hicks. 2021. A verified optimizer for quantum circuits. *Proc. ACM Program. Lang.* 5, POPL (2021), 1–29.
- Aleks Kissinger and John van de Wetering. 2020. Reducing the number of non-Clifford gates in quantum circuits. *Phys. Rev. A* 102, 2 (2020), 022406.
- Dmitri Maslov. 2016. Advantages of using relative-phase Toffoli gates with an application to multiple control Toffoli optimization. *Phys. Rev. A* 93, 2 (2016), 022311.
- Peter Selinger. 2013. Quantum circuits of $T$-depth one. *Phys. Rev. A* 87, 4 (2013), 042302.
- Ganxiang Yang, Paige Raun, Runzhou Tao, and Ronghui Gu. 2026. Equality Saturation for Quantum Circuit Optimization. *Proc. ACM Program. Lang.* 10, PLDI, Article 176 (2026).
- Charles Yuan. 2026. Cobble: Compiling Block Encodings for Quantum Computational Linear Algebra. *Proc. ACM Program. Lang.* 10, PLDI, Article 177 (2026), 200–225.
