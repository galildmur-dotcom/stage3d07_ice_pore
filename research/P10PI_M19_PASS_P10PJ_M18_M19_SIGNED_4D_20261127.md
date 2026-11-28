# P10PI M19 physical PASS and P10PJ M18→M19 signed 4D comparison (2026-11-27)

- P10PI status: `P10PI_M19_REAL_FULL4D_PASS`; forward 36/36, analytic adjoint 36/36; independent signed 4D closure and two-term explicit split PASS.
- M19 accepted mesh SHA-256: `8357cbbdd62cfb603a49e2ef361e86f8723b464634f4284033dff0aef3457aeb` (50,355 nodes, 33,810 Tet10, 4,380 pore Tri6; 27QP Jacobian test accepted).
- M19 derivative: `2.3593864685556034 m^-1`; elapsed `4713.8877 s`; peak private `7203803136 bytes`. No repeat of consumed M19 attempt.
- Input P10PI evidence ZIP SHA-256: `033d6097783ec34edd1d0a256c013fe569e2cb54d7f8d392980a53d0183b5b46`.
- Input M18 evidence ZIP SHA-256: `6d75dc44ca1d3a3a86170b6a8577cb90d38e35e8349cc44b6d862832b432a5d5`.

## Independent comparison P10PJ

| mesh | dR jpeak (m^-1) |
|---|---:|
| M17 | 2.3650868492076955 |
| M18 | 2.367014709423416 |
| M19 | 2.3593864685556034 |

M19−M18 = `-0.0076282408678127744 m^-1`, relative to M18 `-0.00322272643150196` (~−0.3223%). The previous M18−M17 difference was +0.001927860215720667 (0.0815%). **Do not claim mesh convergence.**

Signed 4D cells: 36 × 10 × 10 × 12 = 43,200. Matching grid and global closure independently checked. Signed positive sum: +0.22327983869352733 m^-1; negative sum: −0.2309080795613435 m^-1; cancellation ratio 59.54032209065491.

Absolute local difference fractions: steps 31–36 = 0.5345867142908387; radial bins 0–3 = 0.5196897756626001; polar mu bins 0 and 9 = 0.265728091377908.

P10PJ standalone read-only script and proposed 1200-cell M20 kappa are bundled in `P10PJ_M18_M19_LOCAL_4D_DIAGNOSTIC_20261127.zip`, SHA-256 `d4f73caa86b6f3478823a41805c5cdf8a0e17c8dd3e96a246cfe8c48a64794e3`.

**M20 is a candidate only, not an error certificate or FEM permission.** Any future mesh must use `HighOrderElastic` and pass all independent QA before physical runs. No CAD, no mesh, no FEM in P10PJ.
