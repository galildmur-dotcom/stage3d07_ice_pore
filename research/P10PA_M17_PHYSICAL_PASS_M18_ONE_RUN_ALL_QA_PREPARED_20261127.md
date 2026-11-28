# P10PA: P10OZ M17 full4D PASS; M18 consolidated one-run prepared (2026-11-27)

## M17 physical accepted evidence

Received `P10OZ_M17_FIRST_FULL4D_EVIDENCE.zip`:
- `P10OZ_M17_REAL_FULL4D_PASS`, accepted M17 mesh SHA `54eee71ab234ec7c2eeb0dadd87bde7e897209bed828f9cc3153a7bcc5988dfd`.
- R, EDV_VAR, ξ=0, j_peak, B6=5mm, dt25, steps36, t_end=900s, 4 threads.
- Native exit 0; 3039.802226s (~50m40s), peak private 5,233,020,928 bytes (~4.87 GiB), same-mesh analytic Tet10 forward/adjoint. FEM one-shot P10OZ is consumed and never repeated.
- `P10GY_INDEPENDENT_TIME4D_CLOSURE_PASS`, 43,236 rows (43,200 VOLUME), derivative (D_Rj_{peak}(M17)=2.3650868492076955/m).
- mechanical explicit -9.246395737351165, equilibrium +8.564640004860186, history +2.981644213902828; thermal mass 0.002368405358795563, diffusion 0.06282996243705072, robin 0.
- independent per-bin two-term closure PASS: geometry +1.2394223590962812, stress -10.485818096447503, explicit -9.24639573735114.
- M16 physical derivative 2.366412779242022/m, hence M17−M16 = **−0.0013259300343265/m** (approx −0.056% relative). This is a global functional difference, not a mesh error bound.

## M18 design from real paired signed mechanical 4D

Paired M16 and M17 physical `P10DD_SIGNED_R_THETA_PHI_T.csv` sources, full 36×1200 VOLUME cells, exact time alignment:
`score(r,mu,phi)=sum_t(|Δmechanical_total|+0.25|Δmechanical_explicit|)`.
C2 size field uses 3×3×3 smoothing, periodic phi and pole-azimuth averaging. Volume factor `1−0.30κ`, edge factor `(1−0.30κ)^(1/3)`, κ range [0,1]. Accumulated M2..M17 spatial size factors all retained.

- M16 4D CSV SHA `c35fe4e6ea70b664a5050ecd00a0979904cb6e889cd505da5030f828ced8fb69`.
- M17 4D CSV SHA `14a31b1b668dec387e57f8477c3d5d4c0a4cc3ee83a73d6427ca79ace7549fd7`.
- M18 κ CSV SHA `83024409500afe03b235967d6212f2ff8e80b8560446e16eaa36d2c71283aaaf`.
- M18 source-only SHA preflight PASS 61 historical source pins + four new pins; independent topology auditor successfully read accepted M17, manifold+physical groups PASS. No Gmsh M18 mesh has been generated yet.

## Windows P10PA all-in-one mesh-only program

`P10PA_M18_ONE_RUN_HIGHORDERELASTIC_ALL_QA_WINDOWS_20261127.zip`, SHA256 `b7efeb8d1f576b06ffd6a29e9d27353303ccbea84fba4387b04ce545ee377f17`.

[Download one-run P10PA](https://chatgpt.com/library?file_id=libfile_f6b28d9f042c81919c19f7efe9652b49&account_id=personal).

Double click exactly ONE CMD: `01_P10PA_ONE_M18_MESH_HIGHORDERELASTIC_ALL_QA.cmd`.

Preflight before marker → one original CAD Tet10 generation → RAW serialize → mandatory `HighOrderElastic` → native thresholds and Tri6 boundary preservation → independent serialized MSH2 curved Tet10 detJ 27/343/729, topology, physical tags → independent fresh Gmsh reimport and four canonical metrics → one ZIP with RAW+optimized and audits or failure diagnostics. No FEM. 15s heartbeat, 3600s native CAD cap, 1200s independent audit cap, 12GiB RAM cap. One-shot CAD marker persisted under LOCALAPPDATA; never rerun after failure.

Status **M18 NOT YET ACCEPTED** until returned `P10PA_M18_COMPLETE_MESH_AND_AUDIT_EVIDENCE.zip` is reviewed. On PASS prepare separate M18 full4D physical one-shot.
