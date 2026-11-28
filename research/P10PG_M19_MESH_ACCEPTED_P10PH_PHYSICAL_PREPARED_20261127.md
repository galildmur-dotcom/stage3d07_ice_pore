# P10PG M19 mesh accepted; P10PH physical full4D one-shot prepared (2026-11-27)

## M19 geometry acceptance
- User evidence ZIP P10PG_M19_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip SHA256 cb437f79522462549c1bdaae7c2b8c8f6dafdc7b840637f0f011059a7039761d; Library libfile_0e4b152b16f48191b1956eb1c9c24c97. ZIP CRC PASS.
- One CAD mesh attempt consumed; zero FEM. Guard status ALL_GATES_PASS_M19_CANDIDATE_REVIEW, native worker exit 0, independent audit exit 0.
- Accepted optimized M19 mesh P10PG_M19_HIGHORDERELASTIC_UNVERIFIED.msh SHA256 8357cbbdd62cfb603a49e2ef361e86f8723b464634f4284033dff0aef3457aeb; RAW SHA256 155d6165f6cbc3ce4685ffebaff4c68f4301e166e38707539c67f41b65e3b8b1.
- 50355 nodes, 33810 Tet10, pore 4380 Tri6. External physical surface preserved under mandatory HighOrderElastic; manifold, physical matching, internal group9, disjointness, closed pore, Euler2 all PASS.
- Independent curved Tet10 detJ 27/343/729 QPs per tet: total 37,157,190 evaluations, zero nonpositive, 729QP min 1.7039340453752153e-14. Finite sampling not mathematical proof everywhere.
- Independent reimport quality: minSICN 0.2810609109718399 (>=0.20), minSJ 0.7627566137882292 (>=0.40), gamma 0.21861891839304545 (>=0.15), minDetJac 1.7037234956127638e-14 (>0). All PASS.
- Mesh-only run wall 131.36s, peak generation private bytes 850251776. No rerun of P10PG.
- Independent audit JSON SHA256 c17715dc8a62f95e2e84189b14ae7dacfdc543adc61948e646343c040793090d. Native worker result SHA256 1feb356ac521a07a963c55a93d0e5cd4b6533dd07ef560d64b8dd3798e70829f.
- Scientific disposition: ACCEPT M19 MESH for first separately guarded analytic FEM. No M19 physical result yet.

## P10PH pinned M19 first full 4D Windows one-shot
- Deliverable P10PH_M19_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261127.zip SHA256 a2144c7af64d188225632b313249bd4207bc36035287f64043d641d060652231; Library libfile_b9df0e47a2f481919d1e3524fcfb1d4e.
- Based on independently successful P10PD M18 solver revision, unchanged 101-file SHA manifest 20e38ffc44f4499d5114f9d0e714246f93f28d5ca1d14adb1c94bb1552dc940f. New M19 mesh and both P10PG QA JSON pinned.
- Local source/mesh preflight PASS on exact accepted M19; 27QP curved Tet10 geometry PASS. Python bytecode and ZIP CRC PASS. Windows native C++ and FEM not executed by agent.
- Exactly one CMD 01_P10PH_ONE_M19_FIRST_FULL4D_FEM.cmd, preserving P10PH_WORK nested path, no PowerShell, CAD or remeshing.
- Regime R/EDV_VAR/xi=0/B6=5mm/36x25s/900s/4 threads; fresh forward and same-mesh analytic adjoint, signed 4D and explicit two-term closure; central geometry finite differences prohibited.
- Windows native 65s watchdog selftest, compile/selftest before marker; permanent profile and project markers BEFORE native FEM, never repeat after attempt. 15s heartbeat, 5400s wall, 12GiB RAM, 3GiB output caps.
- On completion user returns one P10PH_M19_FIRST_FULL4D_EVIDENCE.zip from G:/ildar/Stage3D07/LOCAL_RUNS/P10PH_M19_R_DT25_*/.
- P10PH status PREPARED_UNEXECUTED; do not prematurely report physical acceptance. Next scientifically compare signed M18->M19 4D differences, especially final steps, near-wall and polar contributions.