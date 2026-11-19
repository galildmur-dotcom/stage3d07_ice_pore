#!/usr/bin/env python3
"""Independent scalar check of the P10K/P10P discrete-adjoint algebra.

Synthetic one-state transient model, not the ice FEM and not an EXE attestation.
Checks the actual trapezoidal time weights, jpeak eighth-root chain, the
three-part shape derivative, backward history update and terminal history=0.
"""
from __future__ import annotations

import math

HORIZON = 900
STEPS = (6, 12, 18, 36)
K0, KG = 1.3, 0.1
B, A, C = 0.16, 0.42, 0.28
RG, SG, DZ, EZ = 0.035, 0.06, 0.12, 0.04
G = 0.11
INITIAL_Z = 0.3


def weights(steps: int) -> list[float]:
    return [0.5 / steps] + [
        (0.5 if n == steps else 1.0) / steps
        for n in range(1, steps + 1)
    ]


def forward(steps: int, g: float) -> tuple[float, list[tuple[float, float, float]]]:
    s = 0.0
    frames = []
    moment = weights(steps)[0] * INITIAL_Z**8
    for n in range(1, steps + 1):
        force = 0.9 + 0.4 * (n / steps)**3
        k = K0 + KG * g
        u = (force + B * s + g * RG) / k
        z = u + DZ * s + EZ * g
        frames.append((u, s, z))
        moment += weights(steps)[n] * z**8
        s = A * s + C * u + SG * g
    return moment**(1 / 8), frames


def tangent(steps: int, g: float) -> float:
    j, frames = forward(steps, g)
    s_deriv = 0.0
    dm = 0.0
    w = weights(steps)
    for n, (u, _s, z) in enumerate(frames, 1):
        du = (RG + B * s_deriv - KG * u) / (K0 + KG * g)
        dz = du + DZ * s_deriv + EZ
        dm += w[n] * 8 * z**7 * dz
        s_deriv = A * s_deriv + C * du + SG
    return dm / (8 * j**7)


def adjoint(steps: int, g: float) -> tuple[float, float, float, float]:
    j, frames = forward(steps, g)
    chain = 1 / (8 * j**7)
    explicit = equilibrium = history = 0.0
    future = 0.0
    terminal_history = None
    w = weights(steps)
    for n in range(steps, 0, -1):
        u, _s, z = frames[n - 1]
        dm_dz = 8 * z**7
        lam = -(w[n] * chain * dm_dz + C * future) / (K0 + KG * g)
        explicit += w[n] * chain * dm_dz * EZ
        equilibrium += lam * (KG * u - RG)
        h_n = future * SG
        if n == steps:
            terminal_history = h_n
        history += h_n
        future = (-B) * lam + A * future + w[n] * chain * dm_dz * DZ
    assert terminal_history == 0, "Terminal history must vanish before future update"
    return explicit, equilibrium, history, explicit + equilibrium + history


def main() -> None:
    for n in STEPS:
        w = weights(n)
        assert abs(math.fsum(w) - 1) < 1e-15
        assert w[0] == w[-1] == 0.5 / n
        assert all(x == 1 / n for x in w[1:-1])
        parts = adjoint(n, G)
        t = tangent(n, G)
        eps = 1e-6
        f = (forward(n, G + eps)[0] - forward(n, G - eps)[0]) / (2 * eps)
        err_t = abs(parts[-1] - t)
        err_f = abs(parts[-1] - f)
        if err_t > 3e-13 or err_f > 2e-9:
            raise AssertionError(f"n={n} mismatch adjoint={parts[-1]} "
                                 f"tangent={t} FD={f} errors={err_t}/{err_f}")
        print(f"SCALAR_ADJOINT_OK steps={n} dt_s={HORIZON//n} "
              f"explicit={parts[0]:+.12e} equilibrium={parts[1]:+.12e} "
              f"history={parts[2]:+.12e} total={parts[3]:+.12e} "
              f"tangent_error={err_t:.3e} independent_fd_error={err_f:.3e}")
    print("P10BU_SCALAR_REFERENCE_OK checks=4 FEM=0 "
          "proves_production_implementation=NO")


if __name__ == "__main__":
    main()
