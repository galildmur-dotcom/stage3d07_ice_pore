# Stage3D07 — consolidated one-run mesh construction and independent audit SOP (2026-11-27)

## User-approved process change

From M17 onward prepare one Windows double-click program/archive that performs the entire mesh-only sequence on the user's PC, then returns **one evidence archive** for review and GitHub recording. No PowerShell and no interactive input.

1. Source-only SHA-256 preflight of immutable references, geometries, derived full-4D mechanical κ field, scripts, gmsh 4.15.2, and dependencies. Must occur **before consuming the one-shot marker**.
2. Exactly one permitted Gmsh 3D Tet10 CAD mesh generation; persist RAW MSH immediately; mandatory `HighOrderElastic` immediately afterward; persist optimized MSH. Strictly no repeat on error.
3. In-process native Gmsh metrics minSICN≥0.20, minSJ≥0.40, gamma≥0.15, minDetJac>0 and physical boundary preservation.
4. **Independent implementation** loads serialized RAW and optimized MSH from disk and verifies SHA, Tet10 elements and node count, physical Tri6 group 2..9 matching, boundary coordinate fingerprints up to node renumbering, corner-face manifold, physical group 9 internal, pore Euler characteristic 2 and edge incidence 2; curved Tet10 determinant at 27/343/729 sampling nodes per element (zero nonpositive). Numerical sampling is not a global positivity theorem.
5. Separate fresh Gmsh process reimports optimized serialized MSH and checks native metrics and physical-group counts again (D031).
6. Aggregator signs every gate and source/result hashes and produces a **single ZIP** with logs, guards, reports and optimized MSH; can return FAIL with full diagnostic evidence. Zero FEM in this program.
7. User sends one ZIP; assistant verifies manifest and full evidence, records result and scientific conclusions to research GitHub; only if **all** gates PASS, marks M17 accepted and prepares a separate one-click physical run (R/EDV_VAR ξ=0 B6=5mm Δt=25s ×36, full signed-4D mechanical+thermal, analytic Tet10 geometry/adjoint on identical mesh).

Operational: heartbeat at most 15–30 sec even for quiet children; independent watchdog and bounded wall/memory/log/output; distinct persistent one-shot marker across copied folders, never re-run consumed one-shot; recovery from saved RAW, if needed, is separately authorized and distinct from CAD generation. Always use `HighOrderElastic` after mesh generation.

## M16 final acceptance evidence (P10OR/P10OS/P10OT/P10OU)

P10OS optimized M16 SHA-256: `b417aeb71193f38f706e11bf64a365cdc5708ff14580d9460f9bfc3bdf95b972`.
- 21,683 Tet10; 32,155 nodes.
- Native quality: minSICN=0.26342805207715786; minSJ=0.749767513034984; gamma=0.2280394657547726; minDetJac=5.379367236427244e-14; all zero violations.
- Independent P10OT MSH2 boundary, topology and 27/343/729 curved determinant audit: PASS; no nonpositive among 23,829,617 points.
- P10OU independent Gmsh 4.15.2 serialized reimport: **PASS_M16_SERIALIZED_GMSH_REIMPORT_NO_FEM**, physical group Tri6 counts 2..9 = 184,182,156,156,156,156,2286,354; elapsed 0.476s; zero mesh generation, zero FEM, zero optimization.
- **Decision: M16_ACCEPTED_MESH_ONLY.** Not a physical result. Next step: M17 based on accepted M16 and full signed-4D mechanical sensitivity field from M16−M15, with target ~30% characteristic-volume decrease at κ=1, and the consolidated one-run audited mesh package.

No retrospective change to previous M16 one-shot markers; existing evidence remains immutable.
