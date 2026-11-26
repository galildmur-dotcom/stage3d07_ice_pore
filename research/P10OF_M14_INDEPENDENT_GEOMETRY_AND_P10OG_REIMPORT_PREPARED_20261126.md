# P10OF/P10OG — M14 source-free geometry passed, native serialized D031 reimport pending (2026-11-26)

## P10OE native user evidence

Received `P10OE_M14_UNVERIFIED_EVIDENCE.zip` SHA256 `c8a2108f99579fd060fb814d7e2b6cf3d07a55ee5e3b81ab933ef61d2ff7bf89`; ZIP CRC6/6 PASS, guard native exit0 wall67.582s, 15s heartbeat5, source Gmsh4.15.2, FEM0, one-shot P10OE local+profile markers **CONSUMED**. Raw and HighOrder M14 MSH2.2 have identical SHA256 **`9ee7de89b013bff50cb9b5f7ec0b87529af87751aca6bfd27d372b541fd4ea71`**. Native optimizer HighOrder 0.046s generated 0 patches because no bad elements identified; did not move any boundary node, no geometry or topology alteration.

Native D031 before and after: 19271 Tet10, pore1472 Tri6, minSICN0.236581774721 (≥.20), minSJ0.445640326593 (≥.40), gamma0.184677623825 (≥.15), minDetJac1.321954426831e-13 (>0). **All native quality gates PASS**.

## Independent source-free MSH2.2 audit

Reparsed exact native MSH with new Python independently of Gmsh: 28096 nodes, 19271 Tet10, 2816 Tri6 total; surface group2..9 counts respectively 184,182,156,156,156,156,1472,354. Pore sphere Tri6 Euler characteristic2, 738 unique corner nodes/2208 midside nodes/2208 edges; nonmanifold0, midside-edge mismatch0, max radial deviation5.421e−18m.

Analytic Tet10 curved detJ by independent tensor Gauss-Duffy points:

| per-element QPs | total QPs | minimum detJ | nonpositive |
|---:|---:|---:|---:|
| 27 | 520317 | 1.326492236290551e−13 | 0 |
| 343 | 6609953 | 1.32296036661308e−13 | 0 |
| 729 | 14048559 | 1.3225825622279635e−13 | 0 |

Tet10 corner face graph: 37311 interior face pairs, 2462 boundary faces, nonmanifold0; 24298 unique volumetric corner edges, zero conflicting Tet10 midnodes. All 2462 outer Tri6 tags2..8 exactly match boundary Tet10 corner faces, zero midside association errors. The 354 group9 Tri6 are a **valid internal B6 interface** and all match internal Tet10 face pairs, not outer boundary faces. An initial strict-all-faces surface check erroneously classified group9 as outer and produced STOP; corrected group-aware R2 check PASS. Preserve both diagnostics in research record to distinguish test error from mesh defect.

This is **P10OF_INDEPENDENT_SOURCE_FREE_GEOMETRY_PASS_NO_FEM**. Geometric acceptance remains conditional on read-only native Gmsh *reimported* D031 to establish canonical qualities for serialized exact MSH (P10OG), rather than only pre-write in-memory metrics.

## P10OG package

`P10OG_M14_REIMPORT_D031_WINDOWS_20261126.zip`, SHA256 `342dabf335fd7a5784b9f0a736ede19407841214866e8149114d66f6cfe09fed`, 1,335,474 bytes, Library `libfile_b4082c0bfef48191b8212e483cf91b9a`. Contains exact M14 MSH, independent P10OF QA JSONs, and one-click `01_P10OG_REIMPORT_M14_D031_NO_FEM.cmd`: Gmsh4.15.2 `open` exact file, read-only getElementQualities minSICN/minSJ/gamma/minDetJac all Tet10 + tags/sizes; no FEM, no generation, no optimization and no marker. Return `P10OG_M14_REIMPORT_D031_RESULT.json`. P10OE marker already consumed; never rerun.
