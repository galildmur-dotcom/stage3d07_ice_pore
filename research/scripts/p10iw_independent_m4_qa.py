#!/usr/bin/env python3
"""Read-only independent 27/343/729QP D029/D031 screen of M3 and M4."""
from pathlib import Path
import hashlib, json, sys
import p10hv_independent_scan as s

M3='3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a'
M4='00244c5f45c981fe2b05d7c60bcffe70a7e9eaac5b30eb2b9da66d137f84d50c'

def evaluate(path, digest):
    raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==digest
    xyz,tet,faces=s.read_msh(raw)
    q27=s.evaluate(xyz,tet,3,None)
    q343=s.evaluate(xyz,tet,7,q27['volume'])
    q729=s.evaluate(xyz,tet,9,q27['volume'])
    a,b=s.groups(q343),s.groups(q729)
    return {'sha256':digest,'nodes':len(xyz)-1,'Tet10':len(tet),
            'faces':dict(faces),'min_detJ_27_343_729':[q27['minj'],q343['minj'],q729['minj']],
            'CAD_volume_closure_rel729':q729['volume'].sum()/s.CAD_VOL-1,
            'total_volume729':float(q729['volume'].sum()),
            'groups343':a,'groups729':b,
            'neighbour_diagnostic':s.neighbour_quality(xyz,tet,q729['volume'])}

def main():
    m3=evaluate(Path(sys.argv[1]),M3)
    m4=evaluate(Path(sys.argv[2]),M4)
    regions={}
    for side in ('N','S'):
        k='near_p0_'+side
        a3,a4=m3['groups729'][k],m4['groups729'][k]
        b3,b4=m3['groups343'][k],m4['groups343'][k]
        ratio=a4['Veff']/a3['Veff']
        ratio343=b4['Veff']/b3['Veff']
        regions[side]={'M3_Veff729':a3['Veff'],'M4_Veff729':a4['Veff'],
                       'M3_Neff':a3['Neff'],'M4_Neff':a4['Neff'],
                       'M4_over_M3_729':ratio,'M4_over_M3_343':ratio343,
                       'reduction_percent':100*(1-ratio),
                       'qp_order_ratio_rel_drift_percent':100*abs(ratio343/ratio-1),
                       'D029_region_pass':.5<=ratio<=.75 and a4['Neff']>=30}
    qpass=bool(all(x>0 for x in m4['min_detJ_27_343_729']))
    closure=bool(abs(m4['CAD_volume_closure_rel729'])<1e-6)
    d029=bool(all(regions[x]['D029_region_pass'] for x in regions))
    result={'protocol':'P10IW_M4_INDEPENDENT_READ_ONLY_QP_AUDIT',
            'M4_provisional_until_Gmsh_qualities':True,
            'M3':m3,'M4':m4,'supported_N_S':regions,
            'checks':{'QP_27_343_729_detJ_positive':qpass,
                      'CAD_volume_closure_le_1e_6':closure,
                      'D029_N_S_ratio_0p5_to_0p75_and_Neff_ge30':d029},
            'FEM_attempts':0}
    output=Path(sys.argv[3]);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'M4':{'nodes':m4['nodes'],'Tet10':m4['Tet10'],
        'detJ':m4['min_detJ_27_343_729'],'CAD_closure':m4['CAD_volume_closure_rel729']},
        'N_S':regions,'checks':result['checks']},indent=2))

if __name__=='__main__':main()
