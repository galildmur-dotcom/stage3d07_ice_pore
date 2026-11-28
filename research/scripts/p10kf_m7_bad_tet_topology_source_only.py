#!/usr/bin/env python3
"""P10KF: independent local topology around failed M7 Tet10 7442; read-only."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import gmsh
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'p10kf_result'
MESH={
    'M6':ROOT/'p10jw_pkg/P10JW_WORK/M6.msh',
    'M7':ROOT/'p10kc_m7_audit/P10KB_M7_R1_CANDIDATE_UNVERIFIED.msh',
}
P0=np.array([.0008776081131662888,-.00008336233558697972,.029325718609695052])
CENTER=np.array([0.,0.,.03]);R=.001
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
 [-0.08304296248882778,-0.05548753356456836,-0.995],
])


def inspect(label,path):
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        gmsh.open(str(path))
        t,c=gmsh.model.mesh.getElementsByType(11)
        con=np.asarray(c).reshape(-1,10)
        ids=np.asarray(t)
        q=np.asarray(gmsh.model.mesh.getElementQualities(ids,qualityName='minSICN'))
        tags,x,_=gmsh.model.mesh.getNodes()
        xyz={int(k):v for k,v in zip(tags,np.asarray(x).reshape(-1,3))}
        pos=np.array([[xyz[int(k)] for k in e[:4]] for e in con])
        cen=pos.mean(axis=1)
        dist=np.linalg.norm(cen-P0[None,:],axis=1)
        target=int(np.argmin(dist)) if label=='M6' else int(np.flatnonzero(ids==7442)[0])
        # All 4 triangular faces from each Tet10's four corner nodes.
        face_map=defaultdict(list)
        for i,n in enumerate(con[:,:4]):
            a,b,c,d=map(int,n)
            for face in ((a,b,c),(a,b,d),(a,c,d),(b,c,d)):
                face_map[tuple(sorted(face))].append(i)
        nn=con[target,:4]
        neighbours=set()
        for k in ((nn[0],nn[1],nn[2]),(nn[0],nn[1],nn[3]),
                  (nn[0],nn[2],nn[3]),(nn[1],nn[2],nn[3])):
            neighbours.update(face_map[tuple(sorted(map(int,k)))])
        neighbours.discard(target)
        pore_tags,pore_nodes=gmsh.model.mesh.getElementsByType(9,8)
        pore_faces={tuple(sorted(map(int,row[:3]))) for row in np.asarray(pore_nodes).reshape(-1,6)}
        shared_surface=sum(tuple(sorted(map(int,k))) in pore_faces for k in
                   ((nn[0],nn[1],nn[2]),(nn[0],nn[1],nn[3]),
                    (nn[0],nn[2],nn[3]),(nn[1],nn[2],nn[3])))
        region=np.linalg.norm(cen-P0[None,:],axis=1)<.00065
        rel=cen-CENTER
        mu=rel[:,2]/np.linalg.norm(rel,axis=1)
        wall_mm=(np.linalg.norm(rel,axis=1)-R)*1000
        corner_edges=np.linalg.norm(pos[target,:,None,:]-pos[target,None,:,:],axis=-1)
        target_q=float(q[target])
        records=[]
        for i in sorted(neighbours):
            records.append({'element':int(ids[i]),'minSICN':float(q[i]),
                            'centroid_distance_to_bad_mm':float(dist[i]*1000),
                            'mu':float(mu[i]),'wall_distance_mm':float(wall_mm[i])})
        seed_points=CENTER+R*SEEDS/np.linalg.norm(SEEDS,axis=1)[:,None]
        seed_min=float(np.linalg.norm(seed_points-P0[None,:],axis=1).min()*1000)
        # Quantify local variation by same centroid-distance neighbourhood in M6.
        return {'mesh':label,'target_element':int(ids[target]),
                'target_minSICN':target_q,
                'target_centroid_m':cen[target].tolist(),
                'target_wall_distance_mm':float(wall_mm[target]),
                'target_mu':float(mu[target]),
                'target_corner_edge_min_max_mm':[float(corner_edges[np.triu_indices(4,1)].min()*1000),
                                                 float(corner_edges[np.triu_indices(4,1)].max()*1000)],
                'target_direct_pore_surface_faces':int(shared_surface),
                'target_closest_pinned_CAD_seed_distance_mm':seed_min,
                'face_neighbor_count':len(records),
                'face_neighbors':records,
                'local_centroid_radius_mm':.65,
                'local_count':int(region.sum()),
                'local_SICN_min':float(q[region].min()),
                'local_SICN_p05':float(np.quantile(q[region],.05)),
                'local_SICN_median':float(np.median(q[region])),
                'local_SICN_below_0p2_count':int((q[region]<.2).sum()),
                '_plot_distance':dist[region]*1000,
                '_plot_quality':q[region],
                '_plot_mu':mu[region]}
    finally:gmsh.finalize()


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    v={label:inspect(label,path) for label,path in MESH.items()}
    fig,axs=plt.subplots(1,2,figsize=(12.2,4.5),constrained_layout=True)
    for name,color in (('M6','#2b689e'),('M7','#d35c37')):
        rec=v[name]
        axs[0].scatter(rec['_plot_distance'],rec['_plot_quality'],s=12,
                       alpha=.5,label=name,color=color)
        axs[1].scatter(rec['_plot_mu'],rec['_plot_quality'],s=12,
                       alpha=.5,label=name,color=color)
    for ax in axs:
        ax.axhline(.2,ls='--',color='#b02e37',label='D031 minSICN threshold')
        ax.set_ylabel('Tet10 minSICN');ax.set_ylim(0,1.05);ax.legend()
        ax.grid(alpha=.2)
    axs[0].set_xlabel('corner-centroid distance from failed M7 Tet10 7442, mm')
    axs[1].set_xlabel('μ = cos θ (southern negative)')
    axs[0].set_title('Local quality around failed M7 element')
    axs[1].set_title('Same physical region: M6 vs M7')
    fig.savefig(OUT/'P10KF_M6_M7_LOCAL_SICN_NEIGHBOURHOOD.png',dpi=155)
    plt.close(fig)
    for rec in v.values():
        for key in list(rec):
            if key.startswith('_plot_'):del rec[key]
    result={'protocol':'P10KF_M7_R1_TET7442_LOCAL_TOPOLOGY_READ_ONLY',
            'status':'PASS_SOURCE_ONLY_NO_NEW_MESH_NO_FEM',
            'input_SHA256':{m:hashlib.sha256(p.read_bytes()).hexdigest() for m,p in MESH.items()},
            'comparisons':v,
            'D031_conclusion':'M7 fails due to a single element 7442 minSICN=.1626; M6 has no element below .20',
            'D029_conclusion':'M7 R1 observed polar size reduction too weak; P10KE C2 collar is hypothesis only',
            'decision':'STOP M7 R1. Do not reuse consumed P10KB. Next distinct M7 R2 mesh-only must still be independently D031/D029 audited; no FEM.'}
    (OUT/'P10KF_M7_TET7442_LOCAL_TOPOLOGY_QA.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
