#!/usr/bin/env python3
"""Check Gmsh 2.2 ASCII Tet10 mesh pore sizes, physical IDs and topology.
Only numpy is needed; reruns original FEM geometry validator for exhaustive
quadrature Jacobian tests when stage3d08_geometry is executed.
"""
import argparse, json, math, pathlib, sys
from collections import Counter
import numpy as np

def check(path):
    path = pathlib.Path(path)
    if not path.is_file(): raise ValueError(f'Missing mesh: {path}')
    with path.open(encoding='utf-8') as f:
        header=f.readline().strip()
        if header!='$MeshFormat':raise ValueError('Expected MSH2.2 ASCII')
        format_data=f.readline().split()
        if len(format_data)<3 or format_data[:2]!=['2.2','0']:raise ValueError('Only Gmsh v2.2 ASCII supported')
        if f.readline().strip()!='$EndMeshFormat':raise ValueError('Malformed mesh format')
        nodes=None;surface={k:[] for k in range(2,10)};tet_sample=[];type_counts=Counter()
        while True:
            line=f.readline()
            if not line:break
            label=line.strip()
            if label=='$Nodes':
                count=int(f.readline());nodes=np.zeros((count+1,3),dtype=np.float64)
                for _ in range(count):
                    row=f.readline().split(); index=int(row[0]);
                    if not (1<=index<=count):raise ValueError('Node ID out of range')
                    nodes[index]=list(map(float,row[1:4]))
                if f.readline().strip()!='$EndNodes':raise ValueError('Nodes not closed')
            elif label=='$Elements':
                ntotal=int(f.readline());
                for i in range(ntotal):
                    row=f.readline().split(); t=int(row[1]);n_tags=int(row[2]);phys=int(row[3]) if n_tags else None
                    v=list(map(int,row[3+n_tags:]));type_counts[t]+=1
                    if t==9:
                        if len(v)!=6:raise ValueError('Invalid Tri6 record')
                        if phys not in surface:raise ValueError(f'Unexpected surface tag {phys}')
                        surface[phys].append(v)
                    elif t==11:
                        if phys!=1 or len(v)!=10:raise ValueError('Invalid Tet10 record or volume tag')
                        if i%max(1,ntotal//5000)==0:tet_sample.append(v)
                    else:raise ValueError(f'Unexpected element type {t}')
                if f.readline().strip()!='$EndElements':raise ValueError('Elements not closed')
        if nodes is None or type_counts[11]<100 or type_counts[9]<100:raise ValueError('Missing nodes/Tet10/Tri6')
        for tag in range(2,10):
            if len(surface[tag])<1:raise ValueError(f'Missing physical surface tag {tag}')
        pore=np.asarray(surface[8],dtype=np.int64);face_xyz=nodes[pore[:,:3]]
        edge=np.concatenate((np.linalg.norm(face_xyz[:,0]-face_xyz[:,1],axis=1),
                            np.linalg.norm(face_xyz[:,1]-face_xyz[:,2],axis=1),
                            np.linalg.norm(face_xyz[:,2]-face_xyz[:,0],axis=1)))
        wall_ids=np.unique(pore.reshape(-1)); wall_xyz=nodes[wall_ids]
        radius=np.linalg.norm(wall_xyz-np.array([0,0,.03]),axis=1)
        if np.max(np.abs(radius-0.001))>5e-9:raise ValueError('Pore wall not on 1mm sphere')
        b6=np.asarray(surface[9],dtype=np.int64)
        b6_radius=np.linalg.norm(nodes[np.unique(b6.reshape(-1))]-[0,0,.03],axis=1)
        if np.max(np.abs(b6_radius-0.006))>5e-8:raise ValueError('B6 interface not on 6mm sphere')
        # Probe orientations at the corners (linear part), detects gross inversions.
        tets=np.array(tet_sample,dtype=np.int64)
        corners=nodes[tets[:,:4]]
        vol6=np.einsum('ij,ij->i',corners[:,1]-corners[:,0],np.cross(corners[:,2]-corners[:,0],corners[:,3]-corners[:,0]))
        if np.any(~np.isfinite(vol6)) or np.any(vol6<=0):raise ValueError('Sampled negative straight Tet Jacobian')
        area=.5*np.sum(np.linalg.norm(np.cross(face_xyz[:,1]-face_xyz[:,0],face_xyz[:,2]-face_xyz[:,0]),axis=1))
        res={'mesh':path.name,'nodes':int(nodes.shape[0]-1),'tet10':type_counts[11],
            'pore_tri6':len(surface[8]),'b6_tri6':len(surface[9]),
            'pore_wall_nodes':len(wall_ids),'pore_linear_area_m2':float(area),
            'pore_area_relative_deficit_linear':float(1-area/(4*math.pi*1e-6)),
            'pore_edge_median_mm':float(np.median(edge)*1000),
            'pore_edge_p90_mm':float(np.quantile(edge,.9)*1000),
            'pore_edge_min_mm':float(np.min(edge)*1000),
            'pore_edge_max_mm':float(np.max(edge)*1000),
            'max_pore_radius_error_m':float(np.max(np.abs(radius-.001))),
            'max_b6_radius_error_m':float(np.max(np.abs(b6_radius-.006))),
            'sampled_positive_linear_jacobian_count':int(len(vol6)),
            'surface_tag_tri6':{str(k):len(surface[k]) for k in surface}}
        return res

def main():
    ap=argparse.ArgumentParser();ap.add_argument('meshes',nargs='+');ap.add_argument('--out');args=ap.parse_args()
    results=[check(p) for p in args.meshes]
    for r in results:
        print(f"{r['mesh']}: {r['nodes']} nodes, {r['tet10']} Tet10, {r['pore_tri6']} pore Tri6; median wall edge={r['pore_edge_median_mm']:.5f} mm")
    byname={pathlib.Path(r['mesh']).stem:r for r in results}
    if 'HP' in byname and 'H4' in byname:
        hp=byname['HP']; h4=byname['H4']
        if not hp['pore_edge_median_mm']<0.90*h4['pore_edge_median_mm']:
            raise ValueError('HP pore edge is not >=10% finer than H4; reject mesh and adjust size field')
        if not hp['pore_tri6']>h4['pore_tri6']:
            raise ValueError('HP pore surface does not have more triangles than H4')
    if args.out:pathlib.Path(args.out).write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    print('MSH_PORE_SURFACE_AUDIT_OK (preliminary; full Tet10 quadrature check follows in stage3d08_geometry)')

if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('MSH_AUDIT_ERROR:',exc,file=sys.stderr);sys.exit(2)
