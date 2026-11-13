# Evidence registration — P10Z-R, 2026-11-13

Status: Independently verified numerical postprocessing of 4 geometry-only P10Z mesh-audit data sets. NOT a new FEM solve, a bound on derivative error or proof of convergence.

New add-only evidence is recorded in `docs/STAGE3D10Z_REFINED_GEOMETRY_20261113.md` and this experiment directory. Existing main `PROJECT_STATE.md`, `RESEARCH_LOG.md`, `VALIDATION.md`, and `article/EVIDENCE_REGISTER_CURRENT.md` were deliberately left unchanged to avoid patch-base conflicts. Synchronize those registers in a later curated operation against an exact contemporary Git snapshot.

Input is retained byte-for-byte and SHA-256 of raw ZIP and mesh `.msh` recorded in the report. Program reproducible with Python 3, matplotlib optional for plots. All sums and file hashes checked in `derived/VERIFICATION.txt`.

Decision: H4W4B2/R P10W analytic full derivative is justified as next independent wall-refinement datum, but begin with `--preflight` and verify source/mesh/executable provenance. No convergence claim yet.
