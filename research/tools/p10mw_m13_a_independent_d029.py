#!/usr/bin/env python3
"""Read-only 27/343/729-QP curved Tet10 geometry M13 A vs accepted M12."""
import hashlib
import json
from pathlib import Path
from p10kz_m9_r1_independent_d029_d031 import scan

ROOT=Path(__file__).resolve().parents[2]
M12=ROOT/'p10mn_package/P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'
M13=ROOT/'p10mv_m13_evidence/P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh'
OUT=ROOT/'p10mv_m13_evidence/P10MW_M13_R1_D029.json'
M12_SHA='e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13'
M13_SHA='3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'

def main():
    assert not OUT.exists(),'D029 cannot overwrite previous evidence'
    guard=json.loads((M13.parent/'P10MV_GUARD_RESULT.json').read_text(encoding='utf-8-sig'))
    worker=json.loads((M13.parent/'P10MV_WORKER_RESULT.json').read_text(encoding='utf-8-sig'))
    assert guard['status']=='WORKER_FINISHED' and guard['exit_code']==0
    assert guard['new_mesh_3D_attempts']==1 and guard['FEM_attempts']==0
    assert guard['mesh_sha256']==worker['candidate_mesh_sha256']==M13_SHA
    assert worker['M13_variant']=='A_existing_residual' and worker['accepted_M12_R1_sha256']==M12_SHA
    assert worker['Tet10']==18048 and worker['gmsh_version']=='4.15.2'
    a,b=scan(M12,M12_SHA),scan(M13,M13_SHA)
    assert a['Tet10']==16333 and b['Tet10']==18048
    pole={}
    for name in ('near_p0_N','near_p0_S'):
        v={}
        for order in ('343','729'):
            x=a['regions_'+order][name];y=b['regions_'+order][name]
            v[order]={'Veff_ratio':y['Veff']/x['Veff'],
                      'M12_Neff':x['Neff'],'M13_Neff':y['Neff'],
                      'M12_Veff_m3':x['Veff'],'M13_Veff_m3':y['Veff']}
        v['drift_343_729']=abs(v['343']['Veff_ratio']/v['729']['Veff_ratio']-1.)
        v['nominal_15_25_percent_accepted']=.75<=v['729']['Veff_ratio']<=.85
        v['pass']=v['nominal_15_25_percent_accepted'] and v['729']['M13_Neff']>=30 and v['drift_343_729']<=.01
        pole[name]=v
    cad=abs(b['CAD_closure_rel_729'])<1e-6
    jac=all(x>0 for x in b['min_curved_detJ_27_343_729'])
    tags=b['physical_surface_tags']==list(range(2,10))
    passed=cad and jac and tags and all(x['pass'] for x in pole.values())
    qa={'protocol':'P10MW_M13_A_R1_INDEPENDENT_CURVED_D029',
        'status':'D029_PASS_D031_PENDING' if passed else 'D029_GEOMETRY_HOLD',
        'M12_R1':{k:v for k,v in a.items() if not k.startswith('regions_')},
        'M13_R1':{k:v for k,v in b.items() if not k.startswith('regions_')},
        'D029_poles':pole,'CAD_PASS':cad,'curved_detJ_positive_PASS':jac,
        'physical_tags_PASS':tags,'D029_PASS':passed,
        'D031_canonical_Gmsh_quality':'NOT_MEASURED',
        'full_GEOMETRY_GO':False,'mesh_generation_attempts':0,'FEM_attempts':0}
    OUT.write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2),flush=True)

if __name__=='__main__': main()
