# P10LK — M8/M9 physical evidence and deterministic replay feasibility

**Date:** 2026-11-25. **Conclusion:** submitted full4D evidence is complete for *aggregate* signed analysis, but insufficient for a **QP-level geometry/stress replay**. No physical solve, no mesh generation, no consumed-marker reuse.

## Sources actually inspected

- `upload/P10KV_M8_FIRST_FULL4D_EVIDENCE.zip`, `P10KV_MANIFEST.json`.
- `upload/P10LC_M9_FIRST_FULL4D_EVIDENCE.zip`, `P10LC_MANIFEST.json`.
- `P10DD_SIGNED_R_THETA_PHI_T.csv` in each ZIP, streamed read-only (43,236 records per archive: 1,200 volume bins + 1 top Robin row per 36 steps).
- Original P10LC `P10FN_physics.py`: the script requires `forward_history.bin` at run time, records its SHA-256 and exports a limited evidence archive with manifest, log and selected CSVs; the history binary is not packaged.
- `stage3d10p_partial_audit.cpp`: obtains/reconstructs a forward cache and executes a reverse adjoint sweep to generate the signed partitions; exported 4D CSV is aggregated per bin, not per QP.

All nine archive members per mesh were listed. Neither archive includes `forward_history.bin`, QP tensor state files, nor backward-discrete-adjoint arrays. No `.bin`/`.npz`/`.npy`/`.h5` saved-state candidate was present in the inspected scratch workspace. The local Windows tree `G:\ildar\Stage3D07` was **not** inspected, so its retained history, if any, is unknown.

## Recomputed existing physical evidence

| Explicit derivative (per metre) | M8 | M9 | M9−M8 |
| --- | ---: | ---: | ---: |
| Entire B6 | −9.792494033485237 | −9.628060905664032 | +0.164433127821205 |
| First radial bin, wall 0–20 μm | −2.463400736027036 | −2.267376063314328 | +0.196024672712708 |
| All other radial bins together | | | −0.031591544891503 |

The *first-wall-bin* M8→M9 increase is greater than the all-B6 increase because the other bins offset it. These are sums of the original `mech_explicit` field, not any new geometrical/stress decomposition. The archived M8/M9 records pass the original manifest/4D reconciliation; the new read-only audit checks each CSV's 43,236 rows against the manifest's mechanical explicit total to absolute tolerance `1e-8`.

## QP-level replay requirements and decision

To evaluate the two new physical terms at fixed M8 and M9, one requires for every time step: (i) original Tet10 mesh and deformation velocity; (ii) complete forward displacement and local EDV QP history; (iii) temperature and law parameters; (iv) matching discrete displacement and future-history adjoint fields; (v) original B6 mask and output normalization.

The ZIP files include only the *sum* of the two terms per spatial bin. Mathematically, one number cannot uniquely reconstruct its two addends. The SHA-256 of `forward_history.bin` in each manifest certifies a file used during the original run but does not supply its contents. Even if the local forward-history cache still exists on Windows, the backwards adjoint state would need to be recovered or recomputed, and doing so is computational work that should not silently use an old consumed one-shot workflow.

**Decision:** `REPLAY_NOT_SUPPORTED_BY_ARCHIVED_EVIDENCE`. This is not proof that the user's Windows local cache lacks data. It is a precise distinction between supplied evidence and unknown external retained states. No hidden physical values are inferred.

## Next P10LL

Prepare a non-executing, one-click **read-only inventory** for the known Windows Stage3D07 result tree, including file hashes/sizes, without automatically copying large state files or running FEM. Evaluate the returned inventory before deciding whether a new separately marked and explicitly approved P10LG-instrumented physical M8/M9 run is necessary. Existing M8/M9 physical one-shot markers remain irrevocably consumed.

Reproducible evidence parser: `research/tools/p10lk_audit_m8_m9_replay_evidence.py`; machine-readable results: `research/P10LK_REPLAY_EVIDENCE_QA.json`.
