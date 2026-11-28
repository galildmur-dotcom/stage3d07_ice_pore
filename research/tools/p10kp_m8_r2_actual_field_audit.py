#!/usr/bin/env python3
"""P10KP actual pinned P10KM field source-only audit; NO Gmsh or FEM."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from p10kp_m8_r2_polar_plateau import kappa_r2, polar_plateau, selftest, size_ratio


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-dir', required=True, type=Path)
    ap.add_argument('--output-dir', required=True, type=Path)
    args = ap.parse_args()
    root = args.source_dir.resolve()
    sys.path.insert(0, str(root))
    from p10iu_continuous_m4 import C, R, Field, rows
    old = root / 'P10HA_SPATIAL_KAPPA_1200_BINS.csv'
    new = root / 'P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv'
    kmqa = json.loads((root / 'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())
    assert kmqa['source_bins'] == 1200
    field = Field(rows(old), rows(new), '0.1')
    audit_rows = []
    for i, key in enumerate(field.keys):
        p = field.center_points[i]
        distance = float(field.dmm[i])
        mu = float(field.xyz[i, 2])
        base = field.kappa(p)
        revised = kappa_r2(base, distance, mu)
        audit_rows.append(dict(radial_bin=key[0],mu_bin=key[1],phi_bin=key[2],
                               distance_mm=distance,mu=mu,
                               source_qp=int(field.qp[i]),
                               base_kappa=base,plateau=polar_plateau(distance,mu),
                               revised_kappa=revised,base_volume_ratio=1-.2*base,
                               revised_volume_ratio=1-.2*revised))
    qa = dict(protocol='P10KP_M8_R2_ACTUAL_P10KM_FIELD_SOURCE_ONLY',
              status='PASS_SOURCE_ONLY_REAL_FIELD_NO_MESH_NO_FEM',
              source_sha256=sha(new),coordinate_sha256=sha(old),
              source_bins=len(audit_rows),
              mathematical_unit=selftest(),regions={},mesh_attempts=0,FEM_attempts=0)
    assert len(audit_rows)==1200
    for side, pole_bin in (('north',9),('south',0)):
        part=[r for r in audit_rows if r['radial_bin']<=4 and r['mu_bin']==pole_bin]
        assert len(part)==60
        weights=np.array([r['source_qp'] for r in part],dtype=float)
        assert np.all(weights>0)
        def weighted(name):return float(np.average([r[name] for r in part],weights=weights))
        qa['regions'][side]={
            'source_center_count':len(part),'source_QP_weight_sum':int(weights.sum()),
            'baseline_weighted_kappa':weighted('base_kappa'),
            'new_weighted_kappa':weighted('revised_kappa'),
            'baseline_weighted_nominal_volume_ratio':weighted('base_volume_ratio'),
            'new_weighted_nominal_volume_ratio':weighted('revised_volume_ratio'),
            'minimum_plateau':min(r['plateau'] for r in part),
            'maximum_plateau':max(r['plateau'] for r in part)}
        assert abs(qa['regions'][side]['new_weighted_nominal_volume_ratio']-.8)<1e-12
    # Test actual interpolated Cartesian field across the polar core and C2 boundary.
    max_core_error=0.;seam_error=0.;pole_error=0.;n=0
    for d in (0.,.02,.05,.1,.25,.5,.50001,.75,1.,2.,5.):
        for mu in (-1.,-.95,-.8,-.7,-.6,0.,.6,.7,.8,.95,1.):
            values=[]
            for phi in (-math.pi,-2.,0.,2.,math.pi):
                direction=np.array([math.sqrt(max(0.,1-mu*mu))*math.cos(phi),
                                    math.sqrt(max(0.,1-mu*mu))*math.sin(phi),mu])
                p=C+(R+.001*d)*direction
                revised=kappa_r2(field.kappa(p),d,mu)
                assert 0<=revised<=1 and .8-1e-12<=size_ratio(revised)**3<=1+1e-12
                if d<=.5 and abs(mu)>=.8:
                    max_core_error=max(max_core_error,abs(revised-1))
                values.append(revised)
                n+=1
            seam_error=max(seam_error,abs(values[0]-values[-1]))
            if abs(mu)==1:pole_error=max(pole_error,max(values)-min(values))
    assert seam_error<1e-12 and pole_error<1e-12 and max_core_error<1e-12
    qa['physical_sample_count']=n
    qa['max_core_error']=max_core_error
    qa['max_phi_seam_error']=seam_error
    qa['max_pole_coordinate_error']=pole_error
    qa['limitations']=['Center QP weights are legacy source support, not new M8 quadrature',
                       '0.8 is a nominal field volume ratio, not actual Tet10 Veff',
                       'Independent native Gmsh D029 and D031 must decide mesh acceptance']
    args.output_dir.mkdir(parents=True,exist_ok=True)
    (args.output_dir/'P10KP_REAL_FIELD_QA.json').write_text(
        json.dumps(qa,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    with (args.output_dir/'P10KP_REAL_FIELD_1200_BINS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(audit_rows[0]));w.writeheader();w.writerows(audit_rows)
    print(json.dumps(qa,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
