#!/usr/bin/env python3
"""P10MZ: source-only diagnosis and C2 repair supports for two failed M13 Tet10."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
BAD=ROOT/'upload/P10MY_M13_R1_BAD_TET10_LOCATIONS.json'
Q=ROOT/'upload/P10MX_M13_R1_GMSH_QUALITY_RESULT.json'
OUT=ROOT/'p10mz_m13_r2_source_only/P10MZ_M13_R2_LOCAL_C2_REPAIR_HYPOTHESIS.json'
M13_SHA='3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'
sys.path.insert(0,str(ROOT/'p10mf_package_final'))
from p10iu_continuous_m4 import Field, rows
from p10kp_m8_r2_polar_plateau import kappa_r2

def s5(x):
    z=np.clip(x,0.,1.)
    return z**3*(10+z*(-15+6*z))

def weight(dist_m,core_m=.00002,radius_m=.00025):
    return float(1.-s5((dist_m-core_m)/(radius_m-core_m)))

def main():
    if OUT.exists():raise RuntimeError('P10MZ no overwrite')
    bad=json.loads(BAD.read_text(encoding='utf-8-sig'))
    q=json.loads(Q.read_text(encoding='utf-8-sig'))
    assert bad['status']=='MEASURED_NO_MESH_NO_FEM' and bad['mesh_sha256']==M13_SHA
    assert q['status']=='D031_QUALITY_HOLD' and q['mesh_sha256']==M13_SHA
    assert bad['Tet10']==q['Tet10']==18048
    flagged=[r for r in bad['elements'] if r['below_threshold']]
    assert len(flagged)==bad['failed_element_count_unique']==2
    assert set(r['element_tag'] for r in flagged)=={13346,9035}
    f=Field(rows(ROOT/'p10mf_package_final/P10HA_SPATIAL_KAPPA_1200_BINS.csv'),
            rows(ROOT/'p10mt_m13_source_only/P10MT_M13_A_existing_residual_1200_BINS.csv'),'0.1')
    old_repair=np.array([6.6736773608749115e-06,.0008410310311933411,.03073658511697876])
    sites=[]
    for r in flagged:
        p=np.array(r['centroid_m'])
        base=float(f.kappa(p))
        blended=kappa_r2(base,r['wall_distance_mm'],r['mu_cos_theta'])
        olddist=float(np.linalg.norm(p-old_repair))
        sites.append({'element_tag':r['element_tag'],'centroid_m':r['centroid_m'],
            'wall_distance_mm':r['wall_distance_mm'],'mu':r['mu_cos_theta'],
            'minSICN':r['quality']['minSICN'],'minSJ':r['quality']['minSJ'],
            'M13_A_raw_kappa':base,'M13_A_after_polar_C2_blend_kappa':blended,
            'M13_A_local_nominal_Vratio':1-.20*blended,
            'distance_to_M11_R2_repair_mm':olddist*1000,
            'inside_old_M11_repair_support':olddist<.0003,
            'old_M11_repair_weight':weight(olddist,.00002,.00030)})
    d=float(np.linalg.norm(np.array(sites[0]['centroid_m'])-sites[1]['centroid_m']))
    assert d>2*.00025, 'candidate compact supports unexpectedly overlap'
    # Diagnostic, not a certified remedy: a 250µm positive-support C2 local
    # log-size factor exp(-0.045*w) is a controlled prospective R2 hypothesis.
    # The second center already overlaps inherited M11 local repair.
    data={'protocol':'P10MZ_M13_R2_SOURCE_ONLY_LOCAL_C2_HYPOTHESIS',
       'status':'SOURCE_QA_ONLY_REPAIR_UNTESTED_NO_GMSH_NO_MESH_NO_FEM',
       'M13_R1_mesh_sha256':M13_SHA,'M13_R1_Tet10':18048,
       'source_locator_sha256':hashlib.sha256(BAD.read_bytes()).hexdigest(),
       'failed_Tet10':len(flagged),'sites':sites,
       'between_defects_mm':d*1000,'proposed_two_compact_supports_overlapping':False,
       'provisional_log_size_correction':-0.045,
       'provisional_core_m':.00002,'provisional_outer_support_radius_m':.00025,
       'provisional_patch_min_local_size_factor':math.exp(-.045),
       'provisional_patch_min_local_volume_factor':math.exp(-.135),
       'c2_mechanism':'S5 radial ramp with zero derivatives through second order at both boundaries',
       'caution':'DO NOT claim that reducing h fixes minSJ/minSICN: one failed Tet10 is already in M11 R2 repair; future M13 R2 must be separately guarded and D029/D031 audited',
       'M13_R1_marker_consumed':True,'new_mesh_attempts':0,'FEM_attempts':0}
    OUT.parent.mkdir(exist_ok=False)
    OUT.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'status':data['status'],'sites':sites,'between_defects_mm':d*1000},indent=2))

if __name__=='__main__':main()
