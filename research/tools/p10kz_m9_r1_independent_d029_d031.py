#!/usr/bin/env python3
"""Independent read-only curved Tet10 M8→M9 D029 and partial D031 scan."""
import argparse
import hashlib
import json
from pathlib import Path
import p10hv_independent_scan as exact

M8_SHA='40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'
M9_SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'


def scan(path,expected):
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==expected, 'mesh SHA drift'
    xyz,tets,faces=exact.read_msh(raw)
    q27=exact.evaluate(xyz,tets,3,None)
    q343=exact.evaluate(xyz,tets,7,q27['volume'])
    q729=exact.evaluate(xyz,tets,9,q27['volume'])
    return {'mesh_sha256':expected,'nodes':len(xyz)-1,'Tet10':len(tets),
            'pore_Tri6':int(faces[8]),'physical_surface_tags':sorted(faces),
            'min_curved_detJ_27_343_729':[float(q['minj']) for q in (q27,q343,q729)],
            'CAD_closure_rel_729':float(q729['volume'].sum()/exact.CAD_VOL-1),
            'regions_343':exact.groups(q343),'regions_729':exact.groups(q729)}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('m8',type=Path)
    ap.add_argument('m9',type=Path)
    ap.add_argument('output',type=Path)
    a=ap.parse_args()
    m8=scan(a.m8,M8_SHA)
    m9=scan(a.m9,M9_SHA)
    pole={}
    for side in ('near_p0_N','near_p0_S'):
        values={}
        for k in ('343','729'):
            before=m8['regions_'+k][side]
            after=m9['regions_'+k][side]
            values[k]={'Veff_ratio':after['Veff']/before['Veff'],
                       'M8_Neff':before['Neff'],'M9_Neff':after['Neff'],
                       'M8_Veff_m3':before['Veff'],'M9_Veff_m3':after['Veff']}
        values['ratio_relative_drift_343_to_729']=abs(values['343']['Veff_ratio']/values['729']['Veff_ratio']-1)
        values['pass']=.75<=values['729']['Veff_ratio']<=.85 and values['729']['M9_Neff']>=30 and values['ratio_relative_drift_343_to_729']<=.01
        pole[side]=values
    cad=abs(m9['CAD_closure_rel_729'])<1e-6
    positive=all(x>0 for x in m9['min_curved_detJ_27_343_729'])
    tags=m9['physical_surface_tags']==list(range(2,10))
    out={'protocol':'P10KZ_M9_R1_INDEPENDENT_CURVED_27_343_729_QP_D029_PARTIAL_D031',
         'status':'D029_PASS_PARTIAL_D031_FULL_GMSH_QUALITY_PENDING' if cad and positive and tags and all(x['pass'] for x in pole.values()) else 'GEOMETRY_HOLD',
         'm8':{k:v for k,v in m8.items() if not k.startswith('regions_')},
         'm9':{k:v for k,v in m9.items() if not k.startswith('regions_')},
         'D029_poles':pole,'CAD_PASS':cad,'curved_detJ_positive_PASS':positive,
         'physical_tags_PASS':tags,'D029_PASS':all(x['pass'] for x in pole.values()),
         'D031_canonical_Gmsh_minSICN_minSJ_gamma':'NOT_MEASURED',
         'full_GEOMETRY_GO':False,'mesh_generation_attempts':0,'FEM_attempts':0}
    assert not a.output.exists()
    a.output.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
