# P10BD H2 — run-manifest provenance audit (2026-11-18)

Three original JSON manifests were received from the Windows runs and matched
by their internal `run_id` rather than the uploaded `(4)/(5)/(6)` suffix.

| run_id suffix | dt s | steps | status | exit | manifest wall s |
|---|---:|---:|---|---:|---:|
| DT150_20261118_145403 | 150 | 6 | completed | 0 | 1301.1085975 |
| DT75_20261118_145403 | 75 | 12 | completed | 0 | 2576.2272148 |
| DT50_20261118_145403 | 50 | 18 | completed | 0 | 3691.5015934 |

The three runs report identical:

- mesh path `G:\ildar\Stage3D07\P10M_MESHES\H2.msh`;
- mesh SHA-256 `26057402903ebe77af3e7e6b223e2bfaa29aa0cc0c89497e6dcc53817c3c096b`;
- `model=EDV`, `temperature_model=VAR`, `mode=R`, cutoff 5 mm, threads 4;
- `argv[0]=...\stage3d10bd_temporal_polar_audit.exe`;
- executable SHA-256 `c53696b37a823454dfb3896d9758562f0d2196edc3ebd70b549607151dfb762e`;
- full temporal horizon `dt*steps=900 s`.

Original uploaded manifest SHA-256 values:

- dt150: `b134b131c53f5a24165c0de51e6d903b46579e53fd688eb4987d4fe80fe1c12c`;
- dt75: `5894c833d4e7282d21e1f6273510ea71a8964a43d7d27de4baecd2b00a963f4e`;
- dt50: `d97cda7b50dd97ae0e8e3b2e416473bac76a3259f0600a1e7120f845355cfebe`.

## Detected limitations of automatic manifest generation

1. The field `program` states `stage3d10ba_polar_radial_audit` for all three
   manifests, whereas their actual `argv[0]` is the P10BD executable.
   The `program` string is likely a hard-coded P10BA identifier, not reliable
   executable provenance. Do not silently correct the original JSON.
2. `code.git_commit_at_cmake_configure` is `UNKNOWN`: the exact Git commit
   active when CMake configured is **not independently recorded**. The exact
   executable hash remains available and matches all three runs.
3. `produced_files` lists only three P10Y spatial audit CSVs, not the later
   P10BD polar CSVs, P10W global CSV, or the complete output inventory.
   Therefore the list is not exhaustive.
4. No P10BE results are implied or certified by these three manifests.

## Outcome

Manifest collection for P10BD **complete**: all three finished runs have
individual immutable input records with mesh and executable hashes. The
automatic **provenance metadata remains partly defective** (incorrect program
label, missing build Git hash, incomplete file inventory). Record these as
known issues for a future non-urgent manifest generator repair. They do not
negate the previously checked P10BD numerical CSV comparisons, but must be
disclosed if the run provenance is cited in a paper.

Next: execute one independent P10BE H2 / dt25 / 36-step run; obtain its
manifest and full spherical comparison. No rerun of P10BD required.
