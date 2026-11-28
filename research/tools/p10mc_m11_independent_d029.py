#!/usr/bin/env python3
"""Independent read-only 27/343/729QP curved M10→M11 polar volume gate."""
import json,sys
from pathlib import Path
from p10kz_m9_r1_independent_d029_d031 import scan

M10_SHA='022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'
M11_SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'

def main():
    before,after,out=map(Path,sys.argv[1:4])
    assert not out.exists()
    x,y=scan(before,M10_SHA),scan(after,M11_SHA)
    poles={}
    for name in ('near_p0_N','near_p0_S'):
        v={}
        for q in ('343','729'):
            a=x['regions_'+q][name];b=y['regions_'+q][name]
            v[q]={'Veff_ratio':b['Veff']/a['Veff'],'M10_Neff':a['Neff'],
                  'M11_Neff':b['Neff'],'M10_Veff_m3':a['Veff'],'M11_Veff_m3':b['Veff']}
        v['ratio_relative_drift_343_to_729']=abs(v['343']['Veff_ratio']/v['729']['Veff_ratio']-1)
        v['pass_nominal_15_to_25_percent']=.75<=v['729']['Veff_ratio']<=.85
        v['pass_support']=v['729']['M11_Neff']>=30
        v['pass_integration_stability']=v['ratio_relative_drift_343_to_729']<=.01
        poles[name]=v
    cad=abs(y['CAD_closure_rel_729'])<1e-6
    det=all(z>0 for z in y['min_curved_detJ_27_343_729'])
    tags=y['physical_surface_tags']==list(range(2,10))
    d029=all(z['pass_nominal_15_to_25_percent'] and z['pass_support']
            and z['pass_integration_stability'] for z in poles.values())
    result={'protocol':'P10MC_M11_R1_INDEPENDENT_CURVED_D029_PARTIAL_D031',
       'status':'D029_PASS_D031_PENDING' if cad and det and tags and d029 else 'GEOMETRY_HOLD',
       'M10':{k:v for k,v in x.items() if not k.startswith('regions_')},
       'M11':{k:v for k,v in y.items() if not k.startswith('regions_')},
       'D029_poles':poles,'CAD_PASS':cad,'curved_detJ_positive_PASS':det,
       'physical_tags_PASS':tags,'D029_PASS':d029,
       'D031_canonical_Gmsh_minSICN_minSJ_gamma':'NOT_MEASURED',
       'full_GEOMETRY_GO':False,'mesh_generation_attempts':0,'FEM_attempts':0}
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
