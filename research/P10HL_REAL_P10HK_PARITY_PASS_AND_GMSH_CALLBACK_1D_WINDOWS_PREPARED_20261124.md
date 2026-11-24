# P10HL — real Windows P10HK PASS, native Gmsh callback probe prepared

Date: 2026-11-24. Uploaded user `P10HK_RESULT.json`: `PASS_NUMERIC_PARITY_NO_NATIVE_GMSH_NO_MESH_NO_FEM`; 20,000 samples; maximum absolute difference between direct scalar C2 and frozen NumPy field `6.661338147750939e-16`; reference 0.7822 s, direct scalar 0.8812 s (44.059 µs/query), simulated size callback 0.9056 s (45.282 µs/query). User hardware gives approximately 22,084 callback evaluations per second in this isolated Python benchmark; actual full Gmsh meshing call count and runtime are **unknown**. Nominal volume factor 0.83–1.00; **not** actual D-025 volume GO.

Independent source result: 20,000 / 20,000 parity source-only. No prior M1/M0 physics, CAD or mesh was changed.

## P10HL native gate

Per official Gmsh 4.15.2 `gmsh.model.mesh.setSizeCallback(dim,tag,x,y,z,lc)` contract, construct **one synthetic 5-mm line in ice**, install constant background MathEval field `h0=0.5 mm`, and collect actual `lc`, `κ` and returned size at each callback invocation. This is a guarded **1D** test only; no original CAD, no original M1, no 2D/3D, no FEM, no automatic M2. It distinguishes a success (`lc` equals known constant `h0`) from a scientifically important discrepancy, instead of assuming `lc` is the original Field[7].

The immutable P10HL Windows ZIP contains `01_P10HL_ONE_SYNTHETIC_LINE_1D_ONLY.cmd`, Python driver and frozen mechanical field inputs. ZIP SHA256 `4fe1ab66a55ae32b450108d7fad8429ba8ee25edadde62cb7e5a10570420da54`, 210,447 bytes. ZIP CRC/build verified. Python syntax verified; missing gmsh Python API STOP path was executed after independent extraction in the preparation environment and correctly failed before any mesh. **Native Gmsh callback behavior not yet verified** here; requires user's Windows with Gmsh 4.15.2 Python module.

Inputs: existing Python with NumPy and `gmsh` Python API exactly 4.15.2 (searches installed module or `C:\gmsh-4.15.2-Windows64\lib\gmsh.py`). No auto-installation. Expected time on user's i7-7700K 2–20 s, conditional on working Python API. Send `P10HL_RESULT.json` and `P10HL_LOG.txt`, or `P10HL_ERROR.txt` and log on STOP.

GO is **only** for continuing to original CAD Field[7] baseline test, not M2. In P10HM perform actual original CAD/Field[7] callback numerical validation, then assess bounded 1D/2D fields and D-025 only after safe review. The mechanically driven signed M0/M1 4D source and polar/nonpolar guards remain mandatory.
