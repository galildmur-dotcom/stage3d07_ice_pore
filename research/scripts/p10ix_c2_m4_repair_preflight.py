#!/usr/bin/env python3
"""P10IX source-only TWO independent changes: north size and local wall patch.

No Gmsh import, no CAD, mesh or FEM mutation. This is not a calibrated native run.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from p10iu_continuous_m4 import Field, rows

C=np.array([0.,0.,.03]);R=.001
SRC_HA='98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3'
SRC_IT='e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06'
NOLD=.11445576719134759
SOUTH=.12998093714900827
GENERIC=.1435943053641514


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def s5(t):
    q=np.clip(t,0.,1.)
    return q*q*q*(10+q*(-15+6*q))


def wendland(rho):
    if rho>=1:return 0.
    if rho<0:raise ValueError('negative distance')
    return float((1-rho)**4*(4*rho+1))


def local_patch(p,wall_direction,angular_width=.45,radial_width_mm=.50):
    v=p-C
    radius=np.linalg.norm(v)
    if radius<R-1e-10:raise ValueError('outside ice')
    ang=np.linalg.norm(v/radius-wall_direction)
    dmm=max(0.,(radius-R)*1000.)
    return wendland(ang/angular_width)*float(1-s5(dmm/radial_width_mm))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--p10ha',type=Path,required=True)
    ap.add_argument('--p10it',type=Path,required=True)
    ap.add_argument('--p10ix',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    assert sha(a.p10ha)==SRC_HA and sha(a.p10it)==SRC_IT
    f=Field(rows(a.p10ha),rows(a.p10it),'0.1')
    qa=json.loads(a.p10ix.read_text())
    assert qa['status']=='SOURCE_ONLY_NO_NEW_MESH_NO_FEM'
    assert qa['failed_M4_sha256']=='00244c5f45c981fe2b05d7c60bcffe70a7e9eaac5b30eb2b9da66d137f84d50c'
    # Three exact pore-face corner node positions, identified independently.
    face=np.array([[0.0004027639149993809,0.0007521467195290092,0.029551810068792664]])
    wall_dir=(face[0]-C)/np.linalg.norm(face[0]-C)
    bad_center=np.array(qa['field_at_bad_tet']['center_m'])
    chosen_north=.18  # candidate with observed-response proxy ≈.711; not fitted truth
    chosen_bad=.10  # max local additional log-size reduction; exploratory only
    grid=[]
    for side,sign in (('north',1),('south',-1)):
        for dmm in (0.,.03,.1,.25,.5,1.):
            for abs_mu in (.3,.55,.7,.8,.95,1.):
                for phi in (0.,.4,1.2,2.4,math.pi):
                    mu=sign*abs_mu
                    direction=np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                                        math.sqrt(1-mu*mu)*math.sin(phi),mu])
                    p=C+(R+dmm*.001)*direction
                    k,wp,hprev=f.evaluate(p,GENERIC,NOLD,SOUTH)
                    local=local_patch(p,wall_dir)
                    hnew=hprev*math.exp(-(chosen_north-NOLD)*wp*(mu>=0)-chosen_bad*local)
                    grid.append({'side':side,'d_mm':dmm,'mu':mu,'phi':phi,
                                 'kappa':k,'polar_taper':wp,'bad_wall_patch':local,
                                 'old_h_over_M3':hprev,'proposal_h_over_M3':hnew,
                                 'proposal_over_old_M4_size':hnew/hprev})
    assert all(0<r['proposal_h_over_M3']<=r['old_h_over_M3']<=1 for r in grid)
    # Cross-check literal physical periodicity/pole, interior and patch limits.
    max_seam=0.
    max_pole=0.
    for dmm in (0.,.03,.5,1.):
        for mu in (-.95,-.8,-.55,.55,.8,.95):
            def point(phi):
                return C+(R+dmm*.001)*np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                                                 math.sqrt(1-mu*mu)*math.sin(phi),mu])
            max_seam=max(max_seam,abs(local_patch(point(-math.pi),wall_dir)-
                                      local_patch(point(math.pi),wall_dir)))
        for sgn in (-1,1):
            p=C+(R+dmm*.001)*np.array([0.,0.,sgn])
            max_pole=max(max_pole,abs(local_patch(p,wall_dir)-local_patch(p,wall_dir)))
    assert max_seam<1e-13 and max_pole<1e-13
    lbad=local_patch(bad_center,wall_dir)
    qaout={'protocol':'P10IX_C2_M4_SOURCE_ONLY_TWO_FACTOR_PROPOSAL',
           'status':'SOURCE_ONLY_CANDIDATE_NOT_NATIVE_GEOMETRY_GO',
           'input_source_sha256':{'P10HA':SRC_HA,'P10IT':SRC_IT,'P10IX':sha(a.p10ix)},
           'north_old_delta':NOLD,'north_proposed_delta':chosen_north,
           'north_empirical_Veff_proxy':next(x['empirical_nominal_N_Veff_ratio']
               for x in qa['north_calibration']['candidate_deltas'] if abs(x['north_log_patch_delta']-chosen_north)<1e-12),
           'south_delta_unchanged':SOUTH,
           'near_bad_wall_extra_log_size_max':chosen_bad,
           'near_bad_wall_patch_angular_chord_width':.45,
           'near_bad_wall_patch_radial_width_mm':.5,
           'near_bad_wall_patch_at_bad_tet_centroid':lbad,
           'extra_size_factor_at_bad_tet_centroid':math.exp(-chosen_bad*lbad),
           'field_sample_min_ratio':min(r['proposal_h_over_M3'] for r in grid),
           'seam_max_abs':max_seam,'pole_max_abs':max_pole,
           'no_new_gmsh_no_FEM':True,
           'explicit_warning':'Neither north Veff nor local minSJ/minSICN improvement has been checked in a new mesh; one physical M4 observation cannot validate the empirical transfer. No repeat of P10IV R1.'}
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'P10IX_C2_FIELD_PREFLIGHT.json').write_text(json.dumps(qaout,ensure_ascii=False,indent=2)+'\n')
    with (a.out/'P10IX_C2_FIELD_SAMPLES.csv').open('w',newline='') as fcsv:
        writer=csv.DictWriter(fcsv,fieldnames=list(grid[0]));writer.writeheader();writer.writerows(grid)
    print(json.dumps(qaout,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
