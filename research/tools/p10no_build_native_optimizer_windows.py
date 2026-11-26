#!/usr/bin/env python3
"""P10NO guarded package assembly; no native Gmsh operation is run here."""
import hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
EXPECTED='57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
DEST=ROOT/'p10no_m13_native_optimizer_windows'
ZIP=ROOT/'P10NO_M13_NATIVE_GMSH_HIGHORDER_OPTIMIZER_WINDOWS_20261126.zip'

def main():
    if DEST.exists() or ZIP.exists():raise RuntimeError('P10NO_STOP: output exists')
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError('P10NO_STOP: source SHA mismatch')
    DEST.mkdir()
    shutil.copy2(SOURCE,DEST/SOURCE.name)
    files={
        'research/tools/p10no_native_gmsh_highorder_optimizer_windows.py':'P10NO_NATIVE_OPTIMIZER.py',
        'research/tools/p10no_run_native_optimizer_windows.py':'P10NO_RUN_NATIVE_OPTIMIZERS.py',
        'research/tools/P10NO_RUN_NATIVE_OPTIMIZERS.cmd':'P10NO_RUN_NATIVE_OPTIMIZERS.cmd',
        'research/P10NO_M13_NATIVE_GMSH_OPTIMIZER_DIAGNOSTIC_20261126.md':'README_RU.md'}
    for source,target in files.items():shutil.copy2(ROOT/source,DEST/target)
    manifest={'protocol':'P10NO_GMSH_NATIVE_OPTIMIZER_DIAGNOSTIC',
        'status':'PREPARED_NO_GMSH_OPTIMIZE_YET_NO_M13_R3',
        'source_sha256':EXPECTED,'source_file':SOURCE.name,'methods':['HighOrder','HighOrderElastic'],
        'gmsh_version_required':'4.15.2','optimizes_in_memory':True,
        'writes_optimized_mesh':False,'FEM_attempts':0,'marker_uses':0}
    (DEST/'P10NO_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(DEST.iterdir()):z.write(p,arcname=p.name)
    print(json.dumps({'archive':str(ZIP),'sha256':hashlib.sha256(ZIP.read_bytes()).hexdigest()},indent=2))

if __name__=='__main__':main()
