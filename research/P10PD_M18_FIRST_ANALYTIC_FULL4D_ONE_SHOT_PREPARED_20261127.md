# P10PD: first M18 full-4D physical one-shot bundle, prepared 2026-11-27

Status: PREPARED, NOT EXECUTED. User must run Windows one-shot. No FEM started by agent.
Accepted M18 mesh SHA256 ddd9ee5eafdaa6e1b6959e5bd5d842cc37181dacdaef13d7ad21c45031da9ee1, 41463 nodes, 27849 Tet10, 3410 pore Tri6. The source is P10PC_M18_LOCAL_HIGHORDERELASTIC_UNVERIFIED.msh from successfully accepted P10PC evidence. Native and independent quality PASS; false P10PC exit 2 from catching successful SystemExit(0) was diagnosed in earlier report.
Strict acceptance report SHA256 ee0c845354b19cb16f3c85c449ba8fbb68032bb74e0dde98aab4fbf16a05e365. Native HighOrderElastic report SHA256 540f02a71945a35f96af02551a1e6392bb44aa8291bc33dd0082c5cd25bc6b05.

Deliverable ZIP P10PD_M18_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127.zip SHA256 cee0d489c2a2fa2a0ce6a77f6642b001edd370f118366f007ea87ef7d7607970, Library libfile_848ca182a65c81918601e29763ef0d89.
Exactly one CMD 01_P10PD_ONE_M18_FIRST_FULL4D_FEM.cmd, with correct nested P10PD_WORK/P10PD_M18_FIRST_FULL4D.py path checked. No PowerShell, CAD, or mesh generation in this stage. Mandatory HighOrderElastic was already performed at P10PC, not repeated.
Derived from previously physically successful P10OZ M17 full4D Windows package; the full pinned 101-file original solver inventory is unchanged (manifest SHA256 20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f). No central geometry finite differences.
Mesh preflight: accepted exact SHA, both QA report SHAs, native metrics, independent topology/curved reimport, Tet10 27QP geometry; local non-Windows surrogate preflight passed. Cannot execute Windows native C++ or FEM in current Linux container.
Physical regime: R, EDV_VAR, xi0, B6=5mm, 36x25s=900s, OpenMP threads4, signed 4D plus two-term explicit mechanical split and analytic adjoint. Independent 4D temporal and split audits after run.
Single launcher sequentially invokes preflight, real Windows native 65s silent heartbeat test, C++20 MinGW Release compilation/selftest, then consumes both LOCALAPPDATA and LOCAL_RUNS markers BEFORE physical EXE. Never repeat if consumed. Windows Job memory cap 12GiB, FEM wall 5400s, output limit 3GiB, 15s progress.
On completion user returns one P10PD_M18_FIRST_FULL4D_EVIDENCE.zip in G:/ildar/Stage3D07/LOCAL_RUNS/P10PD_M18_R_DT25_*/. Before any physical result, scientific status remains P10PD_PREPARED_NOT_RUN.
Known P10PC bug avoided: P10PD entrypoint catches Exception, not BaseException; explicit SystemExit(0) is not converted to error.