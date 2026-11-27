# P10PB failure and P10PC local M18 Tet10 repair preparation (2026-11-27)

## Evidence and disposition
- P10PB_M18_SERIALIZED_RECOVERY_EVIDENCE.zip: one-shot marker consumed, process exit 2. Do not repeat P10PB.
- Original post-HighOrderElastic M18 mesh SHA256: `733b3acae021b150fc6d19ed1c4d7d51496f17f8f5a49b9c72bef654b4e99c22`; original RAW mesh SHA256: `eacc467e53e75ce45c7aaef53d2281ca86672b65f87193f7e93945574a9bfafd`.
- P10PB Relocate3D: PETSc linear system did not converge (reason -3). P10PB Netgen: native memory access violation.
- P10PB Gmsh optimization: gamma improved to 0.2777757 but altered topology (164 unlabeled external faces; two orphan physical boundary faces; 86 Tet10 and 22 nodes removed); rejected despite native metrics PASS.
- M18 NOT accepted. No physical FEM run.

## Local geometric defect
- Original Tet10 sequential index 21577 (zero-based), corner tags [14417, 15584, 15562, 15563], gamma 0.1433584195463 (required >= 0.15), centroid in mm approximately (0.208267, -0.972947, 31.166668).
- Independent corner-based gamma = 3 * inradius / circumradius agrees with Gmsh native metric at 1e-13 scale.
- All four corner nodes are internal. Constrained source-only local study moved only corner node 15562 by (5.119978271398385e-7, 1.435949555762397e-6, 1.7855255299440477e-6) meters, norm 2.347806 micrometers; nine interior incident quadratic midside nodes moved by half that vector.
- Result source-only local candidate SHA256 `584a44a728859a28ea0d14799e57f7d5b418383c57274f9372329998d253ce15`. Neighborhood min gamma 0.160001565471. No external boundary node changed; original connectivity and Tri6 physical groups preserved. 27/343/729 point per Tet10 curved detJ sampling all strictly positive (30,606,051 total evaluations, minimum detJ 2.6851176134e-14).
- These source-only calculations are NOT native Gmsh acceptance and finite quadrature samples are not proof everywhere.

## P10PC Windows one-shot package
- Filename `P10PC_M18_LOCAL_TET10_HIGHORDERELASTIC_WINDOWS_20261127.zip`
- Library file ID `libfile_87ba5d4834a48191ac44feecd6967618`
- SHA256 `33d2f244f178ba85eb0ddcdfaf8708652f7c9dfb05dfd45c0448dda496c43abb`
- Exactly one double-click entry point: `01_P10PC_ONE_LOCAL_M18_HIGHORDERELASTIC_ALL_QA.cmd`; no PowerShell.
- Requires Windows Python with Gmsh Python package 4.15.2 and NumPy. Preflight validates both source and RAW SHA and no consumed marker; permanent LOCALAPPDATA marker prevents repeating same protocol after any attempt, even moving unpacked folder.
- No CAD operation, no new mesh generation, no FEM.
- Native `gmsh.model.mesh.optimize('HighOrderElastic', force=False)` is mandatory, followed by native quality gates (minSICN >=0.20, minSJ >=0.40, gamma >=0.15, minDetJac >0).
- Separate read-only independent reimport audit verifies external boundary, topology, physical Tri6 counts, curved Jacobians 27/343/729 QPs/Tet10, and native metrics after reimport.
- Output exactly one `P10PC_M18_LOCAL_TET10_REPAIR_EVIDENCE.zip`, including logs, JSON reports, untouched RAW and source candidate, and output candidate if created. Send it for review.
- **Status PREPARED_UNEXECUTED**. Until independent QA on the user's Windows Gmsh passes and evidence is reviewed, M18 remains UNACCEPTED and physical FEM prohibited.
