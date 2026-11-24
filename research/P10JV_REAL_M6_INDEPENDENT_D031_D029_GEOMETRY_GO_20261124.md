# P10JV — real M6 first one-shot mesh independent D031 and D029 GO (2026-11-24)

## Evidence and provenance

User returned private `P10JU_R1_M6_UNVERIFIED_EVIDENCE.zip`; CRC PASS, contains local consumed marker, guard result, Gmsh log, worker result, real M6 .msh. Native Windows Gmsh 4.15.2 worker exit0; guard wall **19.02s**, native mesh generation **17.851187400054187s**, private peak polled **44,294,144 bytes**, one distinct 3D mesh attempt, **FEM_attempts=0**, preserved 10 embedded CAD surface seeds, callback calls 31065, ghost projections17. Exact candidate M6 SHA256 **`d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0`**. P10JU R1 local and LOCALAPPDATA one-shot consumed: **NEVER REPEAT M6 mesh R1**, similarly past P10JN M5 mesh/P10JP M5 FEM. Accepted predecessor M5 SHA `91b26a9a5dcc054e9ebddebc68d3e90df93956c0d7e048266d7766c0931413dd`. Original CAD SHA `f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51`.

## D031: all curved Tet10 geometry PASS

Read-only `p10ic_tet10_quality_audit.py` on returned real MSH2, Gmsh getElementQualities all 11628 curved Tet10 + independent isoparametric 27/343/729QP geometry scan. Pore Tri6 **526**, surface tags2–9 complete. Gmsh minSICN **.2827658859613808≥.20**, minSJ **.5476258603219628≥.40**, gamma **.15899532125995333≥.15**, native minDetJac **9.8417387853932e−13>0** (no nonpositive elements). Independent min detJ at 27/343/729QP **[9.85228690258638e−13,9.84374875964615e−13,9.842968435591575e−13]**, all positive. 729QP relative CAD volume closure **7.651851374745888e−9≤1e−6**, supported region 343→729 max relative Veff drift **.006300755587485218**. D030 neighbour volume diagnostic global p95 2.54434, max8.61291; polar p95 2.65486, max8.61291, **NOT hard gate**. **D031 PASS: M6 geometry GO.**

## D029 real 729QP N/S M6 over accepted M5 PASS

Independent SHA-pinned MSH2 QP read-only `p10iw_independent_m4_qa.evaluate` reused for exact accepted M5 and new M6; fixed physical supported polar N/S bins d≤0.5mm and |μ|≥.8, 60 bins each. Results:

| Side | M5 Veff729 m³ | M6 Veff729 m³ | ratio729 M6/M5 | ratio343 M6/M5 | effective-volume reduction | M5 Neff | M6 Neff |
|---|---:|---:|---:|---:|---:|---:|---:|
| N | 2.8181925371808008e−12 | 1.6475834558849923e−12 | **.5846241639448682** | .5839366221829047 | **41.53758360551318%** | 352.9415205509003 | **603.5527707262322** |
| S | 2.259408361813149e−12 | 1.6230192266185473e−12 | **.7183381517257434** | .7189963662621683 | **28.16618482742566%** | 440.15898209325826 | **612.8786679473003** |

Both real volume ratios in preregistered [.50,.75], Neff≥30; QP343/729 ratios close. Southern refinement weaker and near upper ratio bound; **still D029 PASS, do not impose symmetry not in gate**. P10JT empirical source proxy .65 did not match exact per-side real result; cannot treat transferred proxy as predictive guarantee.

## Heartbeat evidence limitation

P10JU guard JSON reports `heartbeat_count=1`, `heartbeat_interval_s=30` (main guard monitor) during short 19s native run. Independent watchdog should print at 0/15s to stdout, but **outer console transcript and preceding 01 Windows silent-child preflight output were not included in evidence ZIP**. Thus **do not claim independent watchdog visibly verified on user's Windows**. Source-only 65s regression in assistant environment previously had 4 independent beats, but that is not Windows proof. Future packages must optionally package an actual flushed watchdog trace or separate progress log without altering numerical result, and run an actual Windows silent native child test.

## Status and next step

**Accept M6 geometry/adaptation only**, FEM M6 not performed; spatial convergence of `D_R jpeak` remains unproven after M5 due cancellation. Next **P10JW** new distinctly guarded Windows M6 full signed4D FEM, exact accepted SHA `d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0`, **36×25s**, R/EDV_VAR/ξ0/B6=5mm, same-M6 forward + analytic adjoint, 4 threads, new FEM one-shot marker, no M6 remesh, true independent ≤30s watchdog under silent native, all-phase progress and evidence of actual progress; user executes locally, permission standing. Then independent 43236-row signed4D QA M6−M5, polar/nonpolar signed cancellation and convergence sequence M2–M6. Keep private mesh and 4D data off public GitHub.
