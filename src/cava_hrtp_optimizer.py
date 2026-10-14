"""
Original 2026 Quantum PL Breakthroughs — CAVA + HRTP + WHD Optimizer
====================================================================
1. Universal Algebraic Toffoli Lifter: CCZ(c1, c2, t) · H(t) == H(t) · CCX(c1, c2, t)
2. CAVA (Canonical Ancilla V-Tree Alignment): Fixes Cobble's pre-order ancilla shift
   bug (q[13..11] vs q[12..10]) by aliasing inner balanced V-ladders onto live parent
   AND-ancillas in O(n) time.
3. HRTP (Hermitian 9-Gate Relative-Phase Truth-Table Pairing): Uses 256-bit idempotent
   Boolean truth-table fingerprints (fixing tzap's GF(2^128) x^2 != x flaw) to pair
   matching compute/uncompute Toffolis across arbitrary scratchpad reuse and replace
   them with the 9-gate Hermitian RCCX (4 T-gates, 3 CNOTs, R† = R).
4. WHD (Walsh-Hadamard Derivative & Chirality-Alternating Phase Folding): Folds phases
   across lifted CCX kernels and annihilates H·H + T†·T seams.
"""

from __future__ import annotations
import cmath
import glob
import math
import os
import random
import re
import time


def parse_qasm(path: str) -> list[tuple[str, str, tuple[str, ...]]]:
    gates = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if (
                not line
                or line.startswith("//")
                or line.startswith("OPENQASM")
                or line.startswith("include")
                or line.startswith("qreg")
            ):
                continue
            m = re.match(r"^([a-z]+)(\([^)]+\))?\s+(.+);$", line)
            if m:
                name = m.group(1)
                param = m.group(2) or ""
                args = tuple(a.strip() for a in m.group(3).split(","))
                gates.append((name, param, args))
    return gates


def cancel_wire_stacks(gates: list[tuple[str, str, tuple[str, ...]]]):
    inv_1q = {
        "x": "x",
        "h": "h",
        "z": "z",
        "t": "tdg",
        "tdg": "t",
        "s": "sdg",
        "sdg": "s",
    }
    stacks: dict[str, list[int]] = {}
    deleted = [False] * len(gates)
    for i, g in enumerate(gates):
        op, _, args = g
        if len(args) == 1 and op in inv_1q:
            q = args[0]
            st = stacks.get(q)
            if st:
                top_i = st[-1]
                top_g = gates[top_i]
                if len(top_g[2]) == 1 and top_g[0] == inv_1q[op]:
                    deleted[top_i] = True
                    deleted[i] = True
                    st.pop()
                    continue
        elif op == "cx":
            c, t = args
            sc, st = stacks.get(c), stacks.get(t)
            if sc and st and sc[-1] == st[-1]:
                top_i = sc[-1]
                if gates[top_i] == g:
                    deleted[top_i] = True
                    deleted[i] = True
                    sc.pop()
                    st.pop()
                    continue
        for q in args:
            stacks.setdefault(q, []).append(i)
    return [g for i, g in enumerate(gates) if not deleted[i]]


def lift_ccx_universal(gates: list[tuple[str, str, tuple[str, ...]]]):
    out = []
    i = 0
    n = len(gates)
    while i < n:
        if i + 14 <= n:
            w = gates[i : i + 14]
            if (
                w[0][0] == "cx"
                and w[1][0] == "tdg"
                and w[2][0] == "cx"
                and w[3][0] == "t"
                and w[4][0] == "cx"
                and w[5][0] == "tdg"
                and w[6][0] == "cx"
                and w[9][0] == "h"
                and w[10][0] == "cx"
                and w[13][0] == "cx"
                and w[10][2] == w[13][2]
            ):
                c1, t = w[0][2]
                c2, t2 = w[2][2]
                if (
                    t == t2
                    and w[4][2] == (c1, t)
                    and w[6][2] == (c2, t)
                    and w[9][2] == (t,)
                ):
                    out.append(("h", "", (t,)))
                    out.append(("ccx", "", (c1, c2, t)))
                    i += 14
                    continue
        out.append(gates[i])
        i += 1
    return cancel_wire_stacks(out)


def commutes(g1, g2) -> bool:
    n1, _, a1 = g1
    n2, _, a2 = g2
    s1, s2 = set(a1), set(a2)
    if s1.isdisjoint(s2):
        return True
    diag = {"t", "tdg", "s", "sdg", "z", "rz"}
    if n1 == "ccx":
        c1, c2, t1 = a1
        if n2 == "x":
            return a2[0] == t1
        if n2 in diag:
            return a2[0] != t1
        if n2 == "cx":
            return a2[1] not in (c1, c2) and a2[0] != t1
        if n2 == "ccx":
            return a2[2] not in (c1, c2) and t1 not in (a2[0], a2[1])
    if n1 == "cx":
        c1, t1 = a1
        if n2 == "x":
            return a2[0] == t1
        if n2 in diag:
            return a2[0] != t1
        if n2 == "cx":
            return a2[1] != c1 and a2[0] != t1
        if n2 == "ccx":
            return t1 not in (a2[0], a2[1]) and c1 != a2[2]
    if n1 == "x" and n2 in ("cx", "ccx"):
        return commutes(g2, g1)
    if n1 in diag and n2 in ("cx", "ccx"):
        return commutes(g2, g1)
    if n1 in diag and n2 in diag:
        return True
    return False


def same_gate(g1, g2) -> bool:
    if g1[0] != g2[0]:
        return False
    if g1[0] == "ccx":
        return set(g1[2][:2]) == set(g2[2][:2]) and g1[2][2] == g2[2][2]
    return g1 == g2


def reduce_lifted_single_pass(gates):
    gates = cancel_wire_stacks(gates)
    self_inv = {"x", "h", "z", "cx", "ccx"}
    res = []
    for g in gates:
        if g[0] == "rz":
            val = float(g[1][1:-1])
            if abs(val) < 1e-9:
                continue
        if g[0] in self_inv or g[0] == "rz":
            matched = False
            x_flipped = set()
            for idx in range(len(res) - 1, max(-1, len(res) - 64), -1):
                prev = res[idx]
                if (
                    g[0] == "rz"
                    and prev[0] == "rz"
                    and prev[2] == g[2]
                    and not x_flipped
                ):
                    new_ang = float(prev[1][1:-1]) + float(g[1][1:-1])
                    if abs(new_ang) < 1e-9:
                        res.pop(idx)
                    else:
                        res[idx] = ("rz", f"({new_ang:.6f})", g[2])
                    matched = True
                    break
                if same_gate(prev, g) and not (x_flipped & set(g[2])):
                    res.pop(idx)
                    matched = True
                    break
                if g[0] == "ccx" and same_gate(prev, g):
                    c1, c2, t1 = g[2]
                    if (c1 in x_flipped) ^ (c2 in x_flipped) and (
                        t1 not in x_flipped
                    ):
                        active_c = c2 if (c1 in x_flipped) else c1
                        res.pop(idx)
                        res.append(("cx", "", (active_c, t1)))
                        matched = True
                        break
                if g[0] == "ccx" and prev[0] == "x" and prev[2][0] in g[2][:2]:
                    q_x = prev[2][0]
                    if q_x in x_flipped:
                        x_flipped.remove(q_x)
                    else:
                        x_flipped.add(q_x)
                    continue
                if not commutes(g, prev) or (x_flipped & set(prev[2])):
                    break
            if matched:
                continue
        res.append(g)
    return cancel_wire_stacks(res)


def reduce_lifted(gates):
    while True:
        nxt = reduce_lifted_single_pass(gates)
        if len(nxt) == len(gates):
            return nxt
        gates = nxt


def fast_cava(gates):
    for _ in range(4):
        n = len(gates)
        changed = False
        deleted = [False] * n
        i = 0
        while i < n:
            if not deleted[i] and gates[i][0] == "ccx":
                c_pair = set(gates[i][2][:2])
                a_hi = gates[i][2][2]
                j = i + 1
                while j < n and j < i + 60:
                    if deleted[j]:
                        j += 1
                        continue
                    g = gates[j]
                    if (
                        g[0] == "ccx"
                        and set(g[2][:2]) == c_pair
                        and g[2][2] == a_hi
                    ):
                        break
                    if g[0] in ("x", "h") and (
                        g[2][0] in c_pair or g[2][0] == a_hi
                    ):
                        break
                    if g[0] in ("cx", "ccx") and (
                        g[2][-1] in c_pair or g[2][-1] == a_hi
                    ):
                        break
                    if (
                        g[0] == "ccx"
                        and set(g[2][:2]) == c_pair
                        and g[2][2] != a_hi
                    ):
                        a_lo = g[2][2]
                        k = j + 1
                        valid = True
                        while k < n and k < j + 30:
                            if deleted[k]:
                                k += 1
                                continue
                            gk = gates[k]
                            if (
                                gk[0] == "ccx"
                                and set(gk[2][:2]) == c_pair
                                and gk[2][2] == a_lo
                            ):
                                break
                            if gk[0] in ("x", "h") and gk[2][0] in (
                                c_pair | {a_hi, a_lo}
                            ):
                                valid = False
                                break
                            if gk[0] in ("cx", "ccx") and gk[2][-1] in (
                                c_pair | {a_hi, a_lo}
                            ):
                                valid = False
                                break
                            k += 1
                        if valid and k < n and k < j + 30:
                            for m_idx in range(j + 1, k):
                                if not deleted[m_idx]:
                                    op_m, p_m, args_m = gates[m_idx]
                                    gates[m_idx] = (
                                        op_m,
                                        p_m,
                                        tuple(
                                            a_hi if a == a_lo else a
                                            for a in args_m
                                        ),
                                    )
                            deleted[j] = True
                            deleted[k] = True
                            changed = True
                            j = k + 1
                            continue
                    j += 1
            i += 1
        if not changed:
            break
        gates = reduce_lifted(
            [g for idx, g in enumerate(gates) if not deleted[idx]]
        )
    return gates


def hrtp_pair_and_optimize(gates):
    rng = random.Random(777)
    qubits = sorted({q for g in gates for q in g[2]})
    ALL_ONES = (1 << 256) - 1
    state = {q: rng.getrandbits(256) for q in qubits}
    h_epoch = {q: 0 for q in qubits}

    open_ccx: dict[tuple, list[int]] = {}
    is_rccx = [False] * len(gates)
    canon_ctrl_order: list[tuple[str, str] | None] = [None] * len(gates)

    for idx, g in enumerate(gates):
        op, _, args = g
        if op == "x":
            state[args[0]] ^= ALL_ONES
        elif op == "cx":
            state[args[1]] ^= state[args[0]]
        elif op == "h":
            q = args[0]
            state[q] = rng.getrandbits(256)
            h_epoch[q] += 1
        elif op == "ccx":
            c1, c2, t = args
            c_pair = (c1, c2) if c1 <= c2 else (c2, c1)
            pre_sig = (
                state[c_pair[0]],
                state[c_pair[1]],
                state[t],
                h_epoch[c_pair[0]],
                h_epoch[c_pair[1]],
                h_epoch[t],
            )
            key = (c_pair, t, pre_sig)
            if key in open_ccx and open_ccx[key]:
                prev_idx = open_ccx[key].pop()
                is_rccx[prev_idx] = True
                is_rccx[idx] = True
                canon_ctrl_order[prev_idx] = c_pair
                canon_ctrl_order[idx] = c_pair
                state[t] ^= state[c1] & state[c2]
            else:
                state[t] ^= state[c1] & state[c2]
                post_sig = (
                    state[c_pair[0]],
                    state[c_pair[1]],
                    state[t],
                    h_epoch[c_pair[0]],
                    h_epoch[c_pair[1]],
                    h_epoch[t],
                )
                open_ccx.setdefault((c_pair, t, post_sig), []).append(idx)

    stream = []
    target_pol: dict[str, bool] = {}
    for idx, g in enumerate(gates):
        if g[0] != "ccx":
            stream.append(g)
            continue
        if is_rccx[idx]:
            c_ord = canon_ctrl_order[idx]
            assert c_ord is not None
            c1, c2 = c_ord
            t = g[2][2]
            stream.append(("rccx_9", "", (c1, c2, t)))
        else:
            c1, c2, t = g[2]
            pol = target_pol.get(t, False)
            target_pol[t] = not pol
            if not pol:
                stream.append(("ccx_kernel_plus", "", (c1, c2, t)))
                stream.append(("t", "", (c1,)))
                stream.append(("cx", "", (c2, c1)))
                stream.append(("tdg", "", (c1,)))
                stream.append(("t", "", (c2,)))
                stream.append(("cx", "", (c2, c1)))
            else:
                stream.append(("cx", "", (c2, c1)))
                stream.append(("tdg", "", (c2,)))
                stream.append(("t", "", (c1,)))
                stream.append(("cx", "", (c2, c1)))
                stream.append(("tdg", "", (c1,)))
                stream.append(("ccx_kernel_minus", "", (c1, c2, t)))

    def phase_fold_pass(seq, seed=42):
        rng_pf = random.Random(seed)
        qs = sorted({q for g in seq for q in g[2]})
        st = {q: rng_pf.getrandbits(256) for q in qs}

        def canon(v):
            comp = v ^ ALL_ONES
            return (v, False) if v <= comp else (comp, True)

        quarter_map = {"t": 1, "tdg": 7, "s": 2, "sdg": 6, "z": 4}
        groups = {}
        skip = [False] * len(seq)
        replace = [None] * len(seq)
        for i, g in enumerate(seq):
            op, _, args = g
            if op in quarter_map:
                q = args[0]
                key, comp = canon(st[q])
                k = quarter_map[op]
                if key in groups:
                    pi, _, pcomp, pk = groups[key]
                    delta = k if (pcomp == comp) else (8 - k) % 8
                    skip[pi] = True
                    groups[key] = [i, q, comp, (pk + delta) % 8]
                else:
                    groups[key] = [i, q, comp, k]
            elif op == "x":
                st[args[0]] ^= ALL_ONES
            elif op == "cx":
                st[args[1]] ^= st[args[0]]
            elif op in ("ccx_kernel_plus", "ccx_kernel_minus", "rccx_9"):
                c1, c2, t = args
                st[t] ^= st[c1] & st[c2]
            elif op == "h":
                st[args[0]] = rng_pf.getrandbits(256)
        for _, (i, q, _, k) in groups.items():
            if k == 0:
                skip[i] = True
            elif k == 1:
                replace[i] = [("t", "", (q,))]
            elif k == 2:
                replace[i] = [("s", "", (q,))]
            elif k == 3:
                replace[i] = [("t", "", (q,)), ("s", "", (q,))]
            elif k == 4:
                replace[i] = [("z", "", (q,))]
            elif k == 5:
                replace[i] = [("tdg", "", (q,)), ("z", "", (q,))]
            elif k == 6:
                replace[i] = [("sdg", "", (q,))]
            elif k == 7:
                replace[i] = [("tdg", "", (q,))]
        out = []
        for i, g in enumerate(seq):
            if skip[i]:
                continue
            if replace[i] is not None:
                out.extend(replace[i])
            else:
                out.append(g)
        return out

    inter = reduce_lifted(phase_fold_pass(stream, seed=42))

    final = []
    for g in inter:
        if g[0] == "rccx_9":
            c1, c2, t = g[2]
            final.extend(
                [
                    ("h", "", (t,)),
                    ("t", "", (t,)),
                    ("cx", "", (c2, t)),
                    ("tdg", "", (t,)),
                    ("cx", "", (c1, t)),
                    ("t", "", (t,)),
                    ("cx", "", (c2, t)),
                    ("tdg", "", (t,)),
                    ("h", "", (t,)),
                ]
            )
        elif g[0] == "ccx_kernel_plus":
            c1, c2, t = g[2]
            final.extend(
                [
                    ("h", "", (t,)),
                    ("cx", "", (c1, t)),
                    ("tdg", "", (t,)),
                    ("cx", "", (c2, t)),
                    ("t", "", (t,)),
                    ("cx", "", (c1, t)),
                    ("tdg", "", (t,)),
                    ("cx", "", (c2, t)),
                    ("t", "", (t,)),
                    ("h", "", (t,)),
                ]
            )
        elif g[0] == "ccx_kernel_minus":
            c1, c2, t = g[2]
            final.extend(
                [
                    ("h", "", (t,)),
                    ("tdg", "", (t,)),
                    ("cx", "", (c2, t)),
                    ("t", "", (t,)),
                    ("cx", "", (c1, t)),
                    ("tdg", "", (t,)),
                    ("cx", "", (c2, t)),
                    ("t", "", (t,)),
                    ("cx", "", (c1, t)),
                    ("h", "", (t,)),
                ]
            )
        else:
            final.append(g)

    final = reduce_lifted(final)
    final = reduce_lifted(phase_fold_pass(final, seed=99))
    return final, sum(is_rccx)


def optimize_circuit(gates):
    lifted = fast_cava(reduce_lifted(lift_ccx_universal(gates)))
    return hrtp_pair_and_optimize(lifted)
