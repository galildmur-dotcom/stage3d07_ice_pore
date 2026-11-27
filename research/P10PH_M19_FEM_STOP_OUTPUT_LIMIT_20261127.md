# P10PH M19 physical one-shot stopped at output cap: no M19 FEM result (2026-11-27)

## Evidence and disposition
- User one-shot archive P10PH_M19_FIRST_FULL4D_EVIDENCE.zip SHA256 5c982338ac9042847c8b6857c4a6653852a8b29a6b093f66a2fd5ad3c2298504; CRC PASS; Library libfile_8e4c78dcebe481918ddbc1d95fe7a373.
- Manifest status P10PH_STOP_NO_RETRY, FEM_attempts=1, mesh generation=0. Physical marker G:/ildar/Stage3D07/LOCAL_RUNS/P10PH_M19_ONE_SHOT_MARKERS/M19_R_DT25_STEPS36_8357cbbdd62cfb60.json consumed; NEVER repeat P10PH.
- Accepted M19 mesh SHA256 8357cbbdd62cfb603a49e2ef361e86f8723b464634f4284033dff0aef3457aeb passed strict source, quality, and curved geometry preflight. 50355 nodes, 33810 Tet10, 4380 pore Tri6.
- Windows native watchdog 65s premarker PASS; source SHA inventory PASS, native compile and executable selftest PASS.
- Native FEM exit code 1, stop_reason OUTPUT_LIMIT after 1191.114s (19m 51s), average host CPU 18.698%, peak private memory 5,676,834,816 bytes (~5.29 GiB) under 12GiB Job cap.
- Forward reached step 35/36, no adjoint started, no signed 4D CSVs. Last step 35 Newton residual 5.83657650104e-13, relative 6.39232099666e-14; no solver divergence identified.
- P10N_PREFLIGHT in native log explicitly predicted history_gib=2.93820977211 (for 36 steps, M19 33810 Tet10), state_buffers_gib=3.26467752457. Existing P10PH watchdog output_gib=3 checks recursively all output files, including growing history and service files. Thus expected history alone uses nearly all 3 GiB; limit was insufficient. Root cause is disk-output cap, not Gmsh geometry or physics solver.
- This is NOT a successful M19 physical calculation; do not compare dR jpeak M19 to M18 or infer convergence.

## Risk-controlled next protocol proposal (NOT authorized or run yet)
- A genuinely new explicitly approved one-shot physical attempt (new protocol identity, not rerun of P10PH) is required because forward state was not serialized as a completed cache; cannot resume partial 35/36 from this evidence.
- Before new attempt, add deterministic output-size budget calculation using native preflight history_gib and expected sidecars; require >=8 GiB free disk at start (and account for existing data). Set output limit conservatively to 5 GiB if budget verifies expected total below that, while retaining hard memory and wall watchdogs. Do not silently remove output limit.
- Preserve exact 101 source pins, exact accepted M19 SHA, dt=25s, 36 steps, analytic Tet10 no central FD, same-mesh adjoint, 15s progress, permanent one-shot markers. No CAD or mesh generation.
- Next step should be source-only revised budget preflight and user's direction before consuming a separate physical attempt; no automatic rerun.