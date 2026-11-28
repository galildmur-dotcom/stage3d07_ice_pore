#!/usr/bin/env python3
"""P10LU: reuse audited C2 spatial-priority algorithm on real M8→M9 4D data.

No Gmsh, mesh generation, FEM, or one-shot marker writes.
"""
from pathlib import Path
import hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parents[2]
M8=ROOT/'upload/P10KV_M8_FIRST_FULL4D_EVIDENCE.zip'
M9=ROOT/'upload/P10LS_M9_FACE_JUMP_EVIDENCE.zip'
PRIOR=ROOT/'p10kx_source/P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'
COORD=ROOT/'p10ky_package/P10HA_SPATIAL_KAPPA_1200_BINS.csv'
OUT=ROOT/'p10lu_m10_source'
REV='P10LU_M10_M9_MINUS_M8_REAL_SIGNED4D_1200_BINS'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if OUT.exists():raise RuntimeError('source-only output exists: no overwrite')
    for p in (M8,M9,PRIOR,COORD):
        if not p.is_file():raise RuntimeError('missing independently obtained input '+str(p))
    subprocess.run([sys.executable,str(ROOT/'research/tools/p10kx_m9_source_only_design.py'),
        '--m7',str(M8),'--m8',str(M9),'--source',str(PRIOR),
        '--coordinates',str(COORD),'--out',str(OUT)],check=True)
    old=OUT/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'
    new=OUT/(REV+'.csv')
    old.rename(new)
    oldqa=OUT/'P10KX_M9_SOURCE_ONLY_QA.json'
    qa=json.loads(oldqa.read_text())
    qa.update({'protocol':REV,'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
      'M8_full4d_evidence_sha256':sha(M8),'M9_full4d_evidence_sha256':sha(M9),
      'new_source_csv':new.name,'source_csv_sha256':sha(new),
      'comparison':'M9 minus M8, 36x25 signed full4d; C2 interpolator',
      'limitations':['No proof of asymptotic convergence',
       'Actual M10 polar effective volume and Gmsh canonical quality must be tested after meshing']})
    (OUT/'P10LU_M10_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    oldqa.unlink()
    print(json.dumps({'status':qa['status'],'source_sha256':qa['source_csv_sha256'],
        'm8_evidence_sha256':sha(M8),'m9_evidence_sha256':sha(M9),
        'bins':qa['bins'],'top10':qa['top10_source_bins']},indent=2))

if __name__=='__main__':main()
