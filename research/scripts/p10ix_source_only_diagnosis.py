#!/usr/bin/env python3
"""P10IX: diagnose rejected M4 element and inspect C2 correction candidates.

Never calls generate, optimize, write, or FEM. Only reads accepted M3 and rejected M4.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math

import gmsh
import numpy as np

import p10iu_continuous_m4 as source
from p10hv_independent_scan import read_msh

P10IW_M4='00244c5f45c981fe2b05d7c60bcffe70a7e9eaac5b30eb2b9da66d137f84d50c'
P10IP_M3='3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a'
C=np.array([0.,0.,.03]); R=.001
SEEDS=np.asarray([
 [0.26941639574807263,-0.3072105205978578,0.9127083333333333],
 [-0.44259957737323596,-0.029009508941602872,-0.89625],
 [-0.3664985668021997,-0.04825045168171063,0.9291666666666667],
 [-0.13134391727355096,-0.38692670321280165,0.9127083333333333],
 [-0.3415222951421483,0.14146316650066504,-0.9291666666666667],
 [-0.3518912793613243,-0.27001567548838806,0.89625],
 [-0.03210374145325526,-0.09457457261178873,0.995],
 [-0.20560787249210954,0.013476251945206928,0.9785416666666666],
 [-0.3573941704668299,0.3134262755102313,-0.8797916666666666],
 [-0.08304296248882778,-0.05548753356456836,-0.995]])


def h(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def fields(old_file,new_file):
    f=source.Field(source.rows(old_file), source.rows(new_file),'0.1')
    assert abs(f.raw_max-.5594154013460116)<1e-12
    return f


def local_mesh_probe(path,f):
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        gmsh.open(str(path))
        tags,_=gmsh.model.mesh.getElementsByType(11)
        sicn=gmsh.model.mesh.getElementQualities(tags,'minSICN')
        sj=gmsh.model.mesh.getElementQualities(tags,'minSJ')
        idx=int(np.argmin(sicn));tid=int(tags[idx])
        _,node_tags,_,_=gmsh.model.mesh.getElement(tid)
        points=np.array([gmsh.model.mesh.getNode(int(n))[0] for n in node_tags])
        center=points[:4].mean(axis=0)
        v=center-C;rr=np.linalg.norm(v);mu=v[2]/rr
        # Build exact shared-corner-neighbor set independently from MSH2.
        mesh_xyz,tet,faces=read_msh(path.read_bytes())
        index=np.where(np.all(tet[:,:4]==np.asarray(node_tags[:4]),axis=1))[0]
        # The two data sources may differ in element orientation; use unordered corner identity.
        if not len(index):
            ids=set(map(int,node_tags[:4]))
            index=np.asarray([j for j,row in enumerate(tet) if set(map(int,row[:4]))==ids])
        assert len(index)==1
        current=int(index[0]);corners=set(map(int,tet[current,:4]))
        adj=[]
        for el_id,t in enumerate(tet):
            if el_id==current:continue
            intersection=len(corners.intersection(map(int,t[:4])))
            if intersection>=3:
                center_other=mesh_xyz[t[:4]].mean(axis=0)
                vother=center_other-C
                adj.append({'array_index':el_id,'shared_corner_nodes':intersection,
                            'distance_to_wall_mm':float((np.linalg.norm(vother)-R)*1000),
                            'mu':float(vother[2]/np.linalg.norm(vother))})
        # Detect whether one or more triangular faces of this tetra lie on pore Tri6.
        pore_corner_faces=set()
        kinds,_,conn=gmsh.model.mesh.getElements(2,8)
        for k,array in zip(kinds,conn):
            if int(k)==9:
                for row in np.asarray(array).reshape(-1,6):
                    pore_corner_faces.add(frozenset(map(int,row[:3])))
        import itertools
        faces_on_pore=[list(comb) for comb in itertools.combinations(corners,3)
                       if frozenset(comb) in pore_corner_faces]
        dist_to_seeds=[float(np.linalg.norm(center-(C+R*d/np.linalg.norm(d)))*1000) for d in SEEDS]
        pwall=C+R*v/rr
        _,_,h0=f.evaluate(center,.1435943053641514,.11445576719134759,.12998093714900827)
        return {'worst_element_tag':tid,'minSICN':float(sicn[idx]),'minSJ':float(sj[idx]),
                'bad_SICN_count':int((sicn<.2).sum()),'bad_SJ_count':int((sj<.4).sum()),
                'center_m':center.tolist(),'center_dwall_mm':float((rr-R)*1000),
                'center_mu':float(mu),'pore_surface_faces':faces_on_pore,
                'corner_radii_from_sphere_mm':((np.linalg.norm(points[:4]-C,axis=1)-R)*1000).tolist(),
                'corner_pore_wall_tolerance_1um_count':int(np.count_nonzero(
                    abs(np.linalg.norm(points[:4]-C,axis=1)-R)<1e-6)),
                'adjacent_shared_face_tets':adj,
                'nearest_seed_mm':min(dist_to_seeds),'nearest_seed_index':int(np.argmin(dist_to_seeds)),
                'M4_nominal_field_ratio_at_bad_centroid':h0,
                'M4_source_kappa_at_bad_centroid':f.kappa(center),
                'M4_source_kappa_at_nearest_wall':f.kappa(pwall)}
    finally:gmsh.finalize()


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--m3',type=Path,required=True)
    a.add_argument('--m4',type=Path,required=True)
    a.add_argument('--p10ha',type=Path,required=True)
    a.add_argument('--p10it',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    opt=a.parse_args()
    assert h(opt.m3)==P10IP_M3 and h(opt.m4)==P10IW_M4
    f=fields(opt.p10ha,opt.p10it)
    diag=local_mesh_probe(opt.m4,f)
    # Empirical transfer: only ONE actual M3->M4 point, therefore treat as
    # hypothesis and present several bounded north coefficients, no native run.
    nobs=.7901141639278331
    n_proxy=.65
    old=.11445576719134759
    old_eff=float(-math.log(nobs)/(3*(.1435943053641514*.22615873473232162+
                                     old*.9952021676579245)))
    # A local log-volume response under a fixed topology is an unverified proxy.
    # Use observed base actual ratio and this slope to form a diagnostic interval.
    candidates=[]
    for delta in (.14,.16,.18,.20,.22):
        pred=nobs*math.exp(-3*old_eff*.9952021676579245*(delta-old))
        candidates.append({'north_log_patch_delta':delta,
                           'empirical_nominal_N_Veff_ratio':pred,
                           'north_size_factor_vs_old_patch':math.exp(-(delta-old)),
                           'target_band_proxy_only':.5<=pred<=.75})
    out={'protocol':'P10IX_FIRST_M4_STOP_SOURCE_ONLY_DIAGNOSIS',
         'status':'SOURCE_ONLY_NO_NEW_MESH_NO_FEM',
         'old_M3_sha256':P10IP_M3,'failed_M4_sha256':P10IW_M4,
         'input_P10HA_sha256':h(opt.p10ha),'input_P10IT_sha256':h(opt.p10it),
         'field_at_bad_tet':diag,
         'north_calibration':{'actual_N_ratio':nobs,'P10IU_cube_proxy':n_proxy,
                              'observed_response_slope_diagnostic':old_eff,
                              'old_north_patch_log_delta':old,
                              'candidate_deltas':candidates},
         'warnings':['No independent M4 replica has been generated.',
                     'No tested candidate for correcting minSJ/minSICN exists.',
                     'North interpolation is a single-experiment phenomenological proxy.',
                     'D029 target status must remain distinct from D031 geometry GO.']}
    opt.out.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
