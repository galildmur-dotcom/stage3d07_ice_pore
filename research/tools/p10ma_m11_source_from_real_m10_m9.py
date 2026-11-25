#!/usr/bin/env python3
"""P10MA M11 spatial priority: accepted M9→M10 signed4D, no Gmsh/FEM."""
from pathlib import Path
import hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parents[2]
M9=ROOT/'upload/P10LS_M9_FACE_JUMP_EVIDENCE.zip'
M10=ROOT/'upload/P10LY_M10_FIRST_FULL4D_EVIDENCE.zip'
PRIOR=ROOT/'p10lu_m10_source/P10LU_M10_M9_MINUS_M8_REAL_SIGNED4D_1200_BINS.csv'
COORD=ROOT/'p10lv_package/P10HA_SPATIAL_KAPPA_1200_BINS.csv'
OUT=ROOT/'p10ma_m11_source'
REV='P10MA_M11_M10_MINUS_M9_REAL_SIGNED4D_1200_BINS'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if OUT.exists():raise RuntimeError('M11 source already exists; refusing overwrite')
    for p in (M9,M10,PRIOR,COORD):
        if not p.is_file():raise RuntimeError('missing source '+str(p))
    subprocess.run([sys.executable,str(ROOT/'research/tools/p10kx_m9_source_only_design.py'),
        '--m7',str(M9),'--m8',str(M10),'--source',str(PRIOR),
        '--coordinates',str(COORD),'--out',str(OUT)],check=True)
    old=OUT/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'
    new=OUT/(REV+'.csv');old.rename(new)
    oldqa=OUT/'P10KX_M9_SOURCE_ONLY_QA.json'
    qa=json.loads(oldqa.read_text())
    qa.update({'protocol':REV,'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
      'M9_full4d_evidence_sha256':sha(M9),'M10_full4d_evidence_sha256':sha(M10),
      'new_source_csv':new.name,'source_csv_sha256':sha(new),
      'comparison':'M10 minus M9, 36x25 signed full4d; C2 interpolator',
      'limitations':['M9→M10 L1/L2 decrease, but asymptotic convergence not established',
                     'M11 actual polar Veff and Gmsh canonical quality pending']})
    (OUT/'P10MA_M11_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    oldqa.unlink()
    print(json.dumps({'status':qa['status'],'source_sha256':sha(new),
        'm9_evidence_sha256':sha(M9),'m10_evidence_sha256':sha(M10),
        'bins':qa['bins'],'top10_source_bins':qa['top10_source_bins'],
        '4d_l1_per_m':qa['global_cellwise_l1_per_m']},indent=2))

if __name__=='__main__':main()
