#!/usr/bin/env python3
"""Independent curved Tet10 27/343/729QP D029 audit of local M11 R2."""
import json,sys
from pathlib import Path
from p10kz_m9_r1_independent_d029_d031 import scan

M10_SHA='022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'
M11_R2_SHA='b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726'

def main():
    m10p,m11p,out=map(Path,sys.argv[1:4]);assert not out.exists()
    a,b=scan(m10p,M10_SHA),scan(m11p,M11_R2_SHA)
    poles={}
    for name in ('near_p0_N','near_p0_S'):
        v={}
        for q in ('343','729'):
            x=a['regions_'+q][name];y=b['regions_'+q][name]
            v[q]={'Veff_ratio':y['Veff']/x['Veff'],'M10_Neff':x['Neff'],
                  'M11_R2_Neff':y['Neff'],'M10_Veff_m3':x['Veff'],'M11_R2_Veff_m3':y['Veff']}
        v['drift_343_729']=abs(v['343']['Veff_ratio']/v['729']['Veff_ratio']-1.)
        v['pass']=.75<=v['729']['Veff_ratio']<=.85 and v['729']['M11_R2_Neff']>=30 and v['drift_343_729']<=.01
        poles[name]=v
    c=abs(b['CAD_closure_rel_729'])<1e-6
    j=all(x>0 for x in b['min_curved_detJ_27_343_729'])
    t=b['physical_surface_tags']==list(range(2,10))
    passed=c and j and t and all(x['pass'] for x in poles.values())
    result={'protocol':'P10MG_M11_R2_INDEPENDENT_CURVED_D029_PARTIAL_D031',
      'status':'D029_PASS_D031_PENDING' if passed else 'GEOMETRY_HOLD',
      'M10':{k:v for k,v in a.items() if not k.startswith('regions_')},
      'M11_R2':{k:v for k,v in b.items() if not k.startswith('regions_')},
      'D029_poles':poles,'CAD_PASS':c,'curved_detJ_positive_PASS':j,
      'physical_tags_PASS':t,'D029_PASS':passed,
      'D031_canonical_Gmsh_minSICN_minSJ_gamma':'NOT_MEASURED',
      'full_GEOMETRY_GO':False,'mesh_generation_attempts':0,'FEM_attempts':0}
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
