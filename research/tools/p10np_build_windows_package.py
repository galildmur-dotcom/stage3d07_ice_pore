#!/usr/bin/env python3
"""P10NP: assemble SHA-pinned no-FEM Windows diagnostic package."""
import hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
DEST=ROOT/'p10np_m13_boundary_restore_windows'
ZIP=ROOT/'P10NP_M13_GMSH_ELASTIC_BOUNDARY_RESTORE_WINDOWS_20261126.zip'

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10NP_STOP: output exists; no overwrite')
    if hashlib.sha256(SRC.read_bytes()).hexdigest()!=SHA:raise RuntimeError('P10NP_STOP: source SHA mismatch')
    DEST.mkdir();shutil.copy2(SRC,DEST/SRC.name)
    paths={
        'research/tools/p10np_native_boundary_restoration_windows.py':'P10NP_NATIVE_BOUNDARY_RESTORATION.py',
        'research/tools/P10NP_RUN_BOUNDARY_RESTORATION.cmd':'P10NP_RUN_BOUNDARY_RESTORATION.cmd',
        'research/P10NP_M13_BOUNDARY_RESTORATION_PROTOCOL_20261126.md':'README_RU.md'}
    for src,dst in paths.items():shutil.copy2(ROOT/src,DEST/dst)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.iterdir()):z.write(p,arcname=p.name)
    print(json.dumps({'zip':str(ZIP),'sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':main()
