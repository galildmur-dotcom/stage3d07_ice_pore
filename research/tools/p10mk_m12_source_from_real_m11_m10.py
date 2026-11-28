#!/usr/bin/env python3
"""P10MK M12 source-only C2 priority from actual M11 R2 minus M10 signed4D."""
from pathlib import Path
import hashlib,json,subprocess,sys

ROOT=Path(__file__).resolve().parents[2]
M10=ROOT/'upload/P10LY_M10_FIRST_FULL4D_EVIDENCE.zip'
M11=ROOT/'upload/P10MI_M11_FIRST_FULL4D_EVIDENCE.zip'
PRIOR=ROOT/'p10ma_m11_source/P10MA_M11_M10_MINUS_M9_REAL_SIGNED4D_1200_BINS.csv'
COORD=ROOT/'p10lv_package/P10HA_SPATIAL_KAPPA_1200_BINS.csv'
OUT=ROOT/'p10mk_m12_source'
REV='P10MK_M12_M11_MINUS_M10_REAL_SIGNED4D_1200_BINS'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if OUT.exists():raise RuntimeError('M12 source already exists; refusing overwrite')
    for p in (M10,M11,PRIOR,COORD):
        if not p.is_file():raise RuntimeError('missing source '+str(p))
    audit=json.loads((ROOT/'research/P10MJ_M9_M10_M11_REAL_SIGNED4D_AUDIT.json').read_text())
    if audit['status']!='INDEPENDENT_ALIGNED_FULL4D_PASS':
        raise RuntimeError('independent M11−M10 4D audit absent')
    subprocess.run([sys.executable,str(ROOT/'research/tools/p10kx_m9_source_only_design.py'),
        '--m7',str(M10),'--m8',str(M11),'--source',str(PRIOR),
        '--coordinates',str(COORD),'--out',str(OUT)],check=True)
    old=OUT/'P10KX_M9_M8_MINUS_M7_SIGNED4D_1200_BINS.csv'
    new=OUT/(REV+'.csv');old.rename(new)
    oldqa=OUT/'P10KX_M9_SOURCE_ONLY_QA.json'
    qa=json.loads(oldqa.read_text())
    qa.update({'protocol':REV,'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM',
      'M10_full4d_evidence_sha256':sha(M10),'M11_full4d_evidence_sha256':sha(M11),
      'M11_mesh_sha256':audit['M11_mesh_sha256'],
      'new_source_csv':new.name,'source_csv_sha256':sha(new),
      'comparison':'M11 minus M10, 36x25 signed real full4D; C2 interpolator',
      'L1_previous_per_m':audit['M9_to_M10']['L1_per_m'],
      'L1_new_per_m':audit['M10_to_M11']['L1_per_m'],
      'L2_new_per_m':audit['M10_to_M11']['L2_per_m'],
      'late_last6_L1_fraction':audit['last_six_steps_L1_fraction'],
      'limitations':['M11→M12 nominal incremental volume target up to 20%, actual curved Veff requires D029',
                     'Signed 4D consecutive changes partially anticorrelated; no asymptotic claim',
                     'No M12 mesh; D029/D031 gates and FEM pending']})
    (OUT/'P10MK_M12_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    oldqa.unlink()
    print(json.dumps({'status':qa['status'],'source_sha256':sha(new),
        'bins':qa['bins'],'top10_source_bins':qa['top10_source_bins'],
        '4d_l1_per_m':qa['global_cellwise_l1_per_m'],
        'last_six_L1_fraction':qa['late_l1_fraction']},indent=2))

if __name__=='__main__':main()
