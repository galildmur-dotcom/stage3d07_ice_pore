#!/usr/bin/env python3
"""Read-only independent 27/343/729QP curved M9→M10 geometry and polar audit."""
import hashlib,json,sys
from pathlib import Path
from p10kz_m9_r1_independent_d029_d031 import scan

M9_SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
M10_SHA='022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'

def main():
    m9p,m10p,outp=map(Path,sys.argv[1:4])
    assert not outp.exists()
    m9=scan(m9p,M9_SHA)
    m10=scan(m10p,M10_SHA)
    pole={}
    for side in ('near_p0_N','near_p0_S'):
        vals={}
        for q in ('343','729'):
            before=m9['regions_'+q][side]
            after=m10['regions_'+q][side]
            vals[q]={'Veff_ratio':after['Veff']/before['Veff'],
                'M9_Veff_m3':before['Veff'],'M10_Veff_m3':after['Veff'],
                'M9_Neff':before['Neff'],'M10_Neff':after['Neff']}
        vals['ratio_relative_drift_343_to_729']=abs(vals['343']['Veff_ratio']/vals['729']['Veff_ratio']-1)
        vals['pass_nominal_15_to_25_percent']=.75<=vals['729']['Veff_ratio']<=.85
        vals['pass_support']=vals['729']['M10_Neff']>=30
        vals['pass_integration_stability']=vals['ratio_relative_drift_343_to_729']<=.01
        pole[side]=vals
    cad=abs(m10['CAD_closure_rel_729'])<1.e-6
    positive=all(x>0 for x in m10['min_curved_detJ_27_343_729'])
    tags=m10['physical_surface_tags']==list(range(2,10))
    d029=all(v['pass_nominal_15_to_25_percent'] and v['pass_support']
        and v['pass_integration_stability'] for v in pole.values())
    r={'protocol':'P10LW_M10_R1_REAL_CURVED_27_343_729_QP_D029_PARTIAL_D031',
      'status':'D029_PASS_D031_PENDING' if cad and positive and tags and d029 else 'GEOMETRY_HOLD',
      'M9':{k:v for k,v in m9.items() if not k.startswith('regions_')},
      'M10':{k:v for k,v in m10.items() if not k.startswith('regions_')},
      'D029_poles':pole,'CAD_PASS':cad,'curved_detJ_positive_PASS':positive,
      'physical_tags_PASS':tags,'D029_PASS':d029,
      'D031_canonical_Gmsh_minSICN_minSJ_gamma':'NOT_MEASURED',
      'full_GEOMETRY_GO':False,'mesh_generation_attempts':0,'FEM_attempts':0}
    outp.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r,indent=2))

if __name__=='__main__':main()
