#!/usr/bin/env python3
"""P10NQ: assemble pinned Windows-only in-memory optimizer diagnostic."""
import hashlib,json,shutil,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
MESH=ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
SHA='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
DEST=ROOT/'p10nq_m13_geometry_audit_windows'
ZIP=ROOT/'P10NQ_M13_GMSH_GEOMETRY_CORRESPONDENCE_WINDOWS_20261126.zip'

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10NQ_STOP: output exists; no overwrite')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError('P10NQ_STOP: source SHA mismatch')
    DEST.mkdir();shutil.copy2(MESH,DEST/MESH.name)
    files={'research/tools/p10nq_native_geometry_correspondence_windows.py':'P10NQ_GEOMETRY_CORRESPONDENCE.py',
        'research/tools/P10NQ_RUN_GEOMETRY_AUDIT.cmd':'P10NQ_RUN_GEOMETRY_AUDIT.cmd',
        'research/P10NQ_M13_GMSH_GEOMETRY_CORRESPONDENCE_20261126.md':'README_RU.md'}
    for src,dest in files.items():shutil.copy2(ROOT/src,DEST/dest)
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.iterdir()):z.write(p,arcname=p.name)
    print(json.dumps({'zip':str(ZIP),'sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest()},indent=2))
if __name__=='__main__':main()
