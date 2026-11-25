#!/usr/bin/env python3
"""Read-only independent curved Tet10 D029/D031 audit: accepted M7 vs M8 R3.

Reuses the exact historical P10HV curved 27/343/729QP parser/integration.
Never invokes Gmsh generation, modifies an MSH, or runs FEM.
"""
import hashlib
import json
from pathlib import Path
import sys
import p10hv_independent_scan as exact

M7='875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d'
M8='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'

def one(path, expected):
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected, 'mesh SHA mismatch'
    xyz,tets,faces=exact.read_msh(raw)
    base=exact.evaluate(xyz,tets,3,None)
    q343=exact.evaluate(xyz,tets,7,base['volume'])
    q729=exact.evaluate(xyz,tets,9,base['volume'])
    return {'sha256':expected,'nodes':len(xyz)-1,'Tet10':len(tets),
            'pore_Tri6':int(faces[8]),'physical_surface_tags':sorted(faces),
            'min_curved_detJ_27_343_729':[base['minj'],q343['minj'],q729['minj']],
            'CAD_closure_rel729':float(q729['volume'].sum()/exact.CAD_VOL-1),
            'regions343':exact.groups(q343),'regions729':exact.groups(q729)}

def main():
    old=one(Path(sys.argv[1]),M7)
    print('M7_729QP_PASS',flush=True)
    new=one(Path(sys.argv[2]),M8)
    print('M8_729QP_PASS',flush=True)
    comparison={}
    for key in ('near_p0_N','near_p0_S'):
        item={}
        for order in ('343','729'):
            a=old['regions'+order][key]
            b=new['regions'+order][key]
            item[order]={'ratio':b['Veff']/a['Veff'],
                         'M7_Neff':a['Neff'],'M8_Neff':b['Neff'],
                         'M7_Veff_m3':a['Veff'],'M8_Veff_m3':b['Veff']}
        item['relative_ratio_drift_343_to_729']=abs(item['343']['ratio']/item['729']['ratio']-1)
        item['D029_target_15_to_25pct']=.75<=item['729']['ratio']<=.85
        comparison[key]=item
    all_positive=all(min(x['min_curved_detJ_27_343_729'])>0 for x in (old,new))
    geo_basic=(all_positive and abs(new['CAD_closure_rel729'])<1e-6 and
               new['physical_surface_tags']==list(range(2,10)))
    result={'protocol':'P10KS_M8_R3_INDEPENDENT_CURVED_QP_D029_D031',
            'status':'D029_GO_ONLY_IF_TARGETS_AND_SUPPORT',
            'M7':{k:v for k,v in old.items() if not k.startswith('regions')},
            'M8_R3':{k:v for k,v in new.items() if not k.startswith('regions')},
            'comparison':comparison,
            'basic_curved_CAD_tags_PASS':geo_basic,
            'D029_target_PASS':all(v['D029_target_15_to_25pct'] and v['729']['M8_Neff']>=30 and
                                    v['relative_ratio_drift_343_to_729']<=.01
                                    for v in comparison.values()),
            'full_D031_Gmsh_minSICN_minSJ_gamma':'NOT_MEASURED_IN_THIS_ENVIRONMENT',
            'FEM_attempts':0,'mesh_generation_attempts':0,
            'spatial_convergence_proven':False}
    print(json.dumps(result,indent=2))
    Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
