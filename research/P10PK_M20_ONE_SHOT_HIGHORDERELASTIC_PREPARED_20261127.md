# P10PK M20 single CAD / HighOrderElastic / independent QA — source-only preparation

Prepared on 2026-11-27. **No M20 mesh or FEM has been run**.

- Input accepted M19 mesh SHA-256: `8357cbbdd62cfb603a49e2ef361e86f8723b464634f4284033dff0aef3457aeb`.
- Input P10PJ kappa CSV SHA-256: `56d2da1728fd83ebc702cd4acc978b9a3bd6aae69f632bf7e737dc0eb49fcf3e`.
- C2-continuous interpolation, periodic longitude, polar caps longitude averaged, 1200 cells. Maximum target characteristic volume reduction `35%` for kappa=1.
- Cumulative mesh size field through M19 plus incremental M20; Tet10, mandatory `gmsh.model.mesh.optimize('HighOrderElastic')`.
- Reimport serialized mesh in new process. Independent topology, pore Tri6 closure, curved 27QP detJ, native quality minSICN/minSJ/gamma/minDetJac. FEM=0.
- One-shot marker in extracted folder and `%LOCALAPPDATA%`, prohibiting repeat attempts. 15-second progress heartbeats. No PowerShell.
- Source-only test checked all 61 pinned historical files and new source pins and passed M20 C2 audit. Gmsh is unavailable in preparation environment, so **M20 generation and full QA remain pending execution on user's Windows 11 machine**.
- Windows archive: `P10PK_M20_ONE_RUN_HIGHORDERELASTIC_ALL_QA_WINDOWS_20261127.zip`, SHA-256 `59e07c8ab0fd8442f04d54f23fe9205c958b3fa07a955c8c6072c1f4353468b7`.
- User returns only `P10PK_M20_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip`. In case of failed attempt: send diagnostics, **never repeat**.

The M20 kappa is a comparative research priority, not a certified discretization error estimator.