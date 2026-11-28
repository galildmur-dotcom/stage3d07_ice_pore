# P10HM — real P10HL R1 dependency STOP, local Gmsh API recovery R2

Date 2026-11-24. User uploaded `P10HL_ERROR.txt` and `P10HL_LOG.txt`. Windows Python was `C:\Program Files\Python313`, source extraction at `G:\Downloads\P10HL_R1_NATIVE_GMSH_CALLBACK_1D_WINDOWS_20261124`. Exception `ModuleNotFoundError: No module named 'gmsh'`, followed by explicit `P10HL_STOP` before any `gmsh.initialize()` or `gmsh.model.mesh.generate(1)`. **0 native 1D/2D/3D meshes, 0 FEM, 0 M2**. This is an environment dependency STOP, not invalid κ and not a measured `lc` discrepancy.

P10HK real benchmark remains PASS: 20,000 queries, scalar accuracy `6.661338e−16`, 45.282 µs/size query. No need to repeat P10HK.

Official Gmsh 4.15.2 has Windows x86-64 wheel `gmsh-4.15.2-py2.py3-none-win_amd64.whl` (~42.2 MB), published 2026-03-24: https://pypi.org/project/gmsh/4.15.2/ . New P10HL R2 program creates isolated `.p10hl_env` using existing Python 3.13 and `--system-site-packages` (reuse existing NumPy). It installs only pinned `gmsh==4.15.2` with pip **inside that local folder**, automatically if needed, then runs the unchanged R1 synthetic one-line 1D callback diagnostic. No system Python or installed Gmsh executable is modified. Python package installation requires user machine Internet; no installation if already present and valid. Errors are captured in `P10HL_INSTALL_LOG.txt` and must stop before native meshing.

R2 ZIP SHA256 `b407a9031fc7a10b5d6d2b77b75270ce02a94bc18b08b79e10c7b342ca9e57f4`, 210,715 bytes. Verified CRC and file byte identity after building.

Expected initial setup + synthetic Gmsh 1D test **1–5 min**, network dependent; repeated test about **2–20 s**. Return `P10HL_RESULT.json` and `P10HL_LOG.txt` for scientific verdict. Do not create M2 or start FEM. For actual original Field[7], separate later gate.
