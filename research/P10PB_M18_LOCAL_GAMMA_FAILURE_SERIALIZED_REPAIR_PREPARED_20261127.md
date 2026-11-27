# P10PB M18 one-Tet10 gamma failure and serialized-only repair (2026-11-27)

## P10PA M18 evidence review

Received `P10PA_M18_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip` after the one-shot M18 CAD mesh attempt. **P10PA marker is consumed; never repeat CAD M18.**

- 27,849 Tet10; 41,463 nodes, 3,410 pore Tri6; raw SHA `eacc467e53e75ce45c7aaef53d2281ca86672b65f87193f7e93945574a9bfafd`; HighOrderElastic optimized SHA `733b3acae021b150fc6d19ed1c4d7d51496f17f8f5a49b9c72bef654b4e99c22`.
- RAW native quality: minSICN 0.130598525 (1 bad), minSJ 0.348220118 (1 bad), gamma 0.143954152 (1 bad), minDetJac 2.58311271864e-14 (>0).
- **HighOrderElastic ran without error** (~4.916 s), improved native minSICN 0.203000617 PASS, minSJ 0.599782022 PASS, but **gamma 0.14335841954619183 FAIL for one Tet10** vs threshold ≥0.15; minDetJac 2.685104662e-14 PASS, boundary exactly unchanged. Thus native gate false, independent automated audit correctly stopped; no FEM.
- Independent *local read-only* audit of serialized M18 optimized performed despite native gamma fail: physical groups 2..9 counts 184,182,156,156,156,156,3410,354; external boundary complete, interface 9 internal, groups disjoint, manifold, pore V/E/F 1707/5115/3410 Euler 2, every pore edge incidence 2. RAW vs optimized Tri6 boundary coordinate fingerprints equal.
- Independent curved Tet10 determinant 27/343/729 QPs per element: 751,923 / 9,552,207 / 20,301,921 = **30,606,051 evaluations**, all detJ positive; at 729 QPs min 2.68511761344e-14 and integrated volume 0.00017999581187804235 m³. Finite samples do not prove global positivity.
- **Scientific decision: M18_UNACCEPTED_LOCAL_GAMMA_DEFECT, NO PHYSICAL RUN.** Accepted M17 remains reference.

## Rationale and P10PB recovery

Gmsh 4.15.2 official API lists `Relocate3D`, default `Gmsh`, `Netgen`, and `HighOrderElastic` as supported `gmsh.model.mesh.optimize` methods. Reference: https://gmsh.info/doc/texinfo/ (gmsh/model/mesh/optimize).

P10PB separate Windows one-shot opens only the **serialized optimized M18 MSH** (no CAD, no mesh.generate, no FEM). Three bounded trial optimizers in order `Relocate3D`, `Gmsh`, `Netgen`, each followed by mandatory `HighOrderElastic`, with first full-pass candidate selected. Exact original RAW and Elastic hashes pinned; original files never overwritten. Strict acceptance on candidate: all four native thresholds; independent physical Tri6 coordinate fingerprints equal original RAW; independent manifold & pore Euler 2; curved 27/343/729 detJ positivity; **fresh Gmsh serialized reimport** four native metrics, physical groups and counts. Separate persistent LOCALAPPDATA one-shot recovery marker, 15-sec heartbeats, output single diagnostics ZIP regardless of candidate success. No automatic re-generation.

Archive `P10PB_M18_SERIALIZED_REPAIR_HIGHORDERELASTIC_WINDOWS_20261127.zip`, SHA256 `09942f7521119b3b8698b4b6f008a25f705baa793e8cfaad3b52195bfdadb366`. [Download](https://chatgpt.com/library?file_id=libfile_8b2150caff4481918e3b0075b0b661b0&account_id=personal)

Run ONE Windows CMD `01_P10PB_ONE_SERIALIZED_M18_RECOVERY.cmd` once, return `P10PB_M18_SERIALIZED_RECOVERY_EVIDENCE.zip`. The local preflight and Python syntax were tested, and the independent M18 MSH2 topology/curved audits were executed; native candidate recovery **has not yet been run**.

If P10PB fails, diagnose selected bad Tet10 and develop a distinctly authorized local nodal repair with objective improvements, preserving boundary and no remesh. Never relax gamma threshold to accept existing M18.
