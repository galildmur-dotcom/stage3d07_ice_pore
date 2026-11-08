# Stage 3D-10G — Checkpointed full-history adjoint (04 Nov 2026)

## Purpose

Validate bounded-in-time backward discrete adjoint in the small, physically
nonlinear 2-Tet10 verification task. It supports six constitutive settings
(E/ED/EDV × CONST/VAR) and four observable sources (j6, jpeak, jen,
experimental smooth safety *only as test*). The geometry derivative still
uses a central perturbation of frozen geometry in the synthetic test; this
is NOT an implemented Hadamard surface gradient or coupled thermal adjoint.

## Changes in this patch

- New `src/stage3d10g_checkpoint_replay.hpp`: writes/reads **named** state
  snapshots every 4 steps, includes the established P09D5 binary checkpoint
  header and raw displacement + state layout, and adds a separate `.checksum`
  FNV64 sidecar to detect corruption. The unmodified production `restart.bin`
  contains **no checksum**; the sidecar belongs exclusively to Stage 10G.
- Updated `tests/stage3d10d_transient_adjoint.cpp`: new conditional target;
  Stage 10D, 10E and 10F target behavior remains unchanged.
- `PATCH_CMAKE_Stage3D10G.txt`: append once to the existing `CMakeLists.txt`.

**Do not overwrite your 200-GB project or build directory with this archive.**
Copy only the new header and the updated test into matching `src` / `tests`
folders, making a backup of the existing test first. Add the target from
`PATCH_CMAKE_Stage3D10G.txt` if it is not already present. Do not replace
the full project `CMakeLists.txt`; it may have local modifications.

## Qt Creator Windows / Desktop MinGW Release

- Target: `stage3d10g_checkpoint_replay`.
- Arguments: **empty**.
- Working directory: the build directory automatically set by Qt Creator
  (test data are written to a temporary test-owned directory and removed).
- Threads: OpenMP 4 threads (set inside the test).
- Estimated runtime on i7-7700K / 64 GB: first release compilation **1–5 min**,
  numerical verification typically **10–90 seconds**. This is a provisional
  estimate, not a measured benchmark on your workstation.
- Memory: small; no HP4/HP8 meshes, large VTU, or mechanical campaigns.

Send **only the final line** beginning with `P10G_CHECKPOINT_REPLAY_OK`.
If it fails, send the full build/runtime error (text); no 200-GB archive.

## Local GCC verification

Executed with `g++ -std=c++20 -O2 -fopenmp` and all three macros. Output:

```
P10G_CHECKPOINT_REPLAY_OK models=6 observables=4 comparisons=24 checkpoint_files=24 max_frames=4 total_replayed_steps=288 objective_rel=0.000000000000e+00 temperature_gradient_rel=0.000000000000e+00 shape_gradient_rel=0.000000000000e+00 worst_adjoint_equilibrium_rel=5.000284278389e-13 checksum_bitflip_detected=1 mismatched_model_detected=1
```

These zero values are bit-for-bit replay agreement at this model/problem,
**not** discretization error estimates or evidence of mesh convergence.

## Scientific and computational interpretation

The full history scheme stores O(N_t S) time state data in RAM. A fixed
checkpoint interval K stores O(K S) time state data in RAM and writes
O(N_t S/K) data to disk, where S denotes displacement/history state size.
Each reverse window replays its K forward steps and checks the terminal
reconstructed state against the saved checkpoint **bitwise**.

The current test intentionally replays once **per functional** (4 repeats):
there are 24 comparisons and 288 replayed forward steps. For production
HP4/HP8, group multiple functional adjoints into one window or employ a
multilevel schedule to avoid redundant expensive nonlinear solves.

The old time-based `--checkpoint-hours 6` restart policy overwrites one
checkpoint, whereas a reverse adjoint needs a set of retained snapshots.
Stage 10G does **not** alter the old restart policy. The next implementation
stage should integrate retained snapshots into production Stage09C / EDV_VAR,
apply safe storage budgeting and optional multi-observable reverse sweeps,
then validate on H0/H2 before HP4/HP8. Peak time/space limits must be
measured, not inferred from this tiny test.
