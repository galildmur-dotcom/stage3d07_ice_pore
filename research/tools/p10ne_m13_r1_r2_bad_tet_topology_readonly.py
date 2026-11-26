#!/usr/bin/env python3
"""P10NE: source-only exact Gmsh2 Tet10 bad-element topology, no meshing/FEM."""
import hashlib,itertools,json,math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'p10ne_m13_bad_topology/P10NE_M13_R1_R2_BAD_TET10_TOPOLOGY.json'
INPUTS=(('R1',ROOT/'p10mv_m13_evidence/P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh',
  ROOT/'upload/P10MY_M13_R1_BAD_TET10_LOCATIONS.json',
  '3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'),
 ('R2',ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh',
  ROOT/'upload/P10ND_M13_R2_BAD_TET10_LOCATIONS.json',
  '57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'))
PAIRS=list(itertools.combinations(range(4),2))

def read_msh(path):
    nodes={};tet={};surface=set();seed=set()
    with path.open(encoding='ascii') as f:
        for line in f:
            if line.strip()=='$Nodes':
                n=int(next(f))
                for _ in range(n):
                    t,*xyz=next(f).split();nodes[int(t)]=np.array([float(v) for v in xyz])
            if line.strip()=='$Elements':
                n=int(next(f))
                for _ in range(n):
                    fields=list(map(int,next(f).split()))
                    eid,kind,nt=fields[:3];physical=fields[3] if nt else None
                    cn=fields[3+nt:]
                    if kind==11:tet[eid]=cn
                    elif kind==9 and physical==8:surface.update(cn)
                    elif kind==15 and physical==8:seed.update(cn)
    return nodes,tet,surface,seed

def main():
    if OUT.exists():raise RuntimeError('P10NE output already exists; no overwrite')
    data={'protocol':'P10NE_M13_R1_R2_READONLY_BAD_TET10_TOPOLOGY',
          'status':'MEASURED_NO_GMSH_NO_MESH_NO_FEM_NO_MARKERS',
          'meshes':{},'FEM_attempts':0,'mesh_generation_attempts':0}
    sites=[]
    for name,path,locator,expected in INPUTS:
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        report=json.loads(locator.read_text(encoding='utf-8-sig'))
        assert report['mesh_sha256']==expected
        nodes,tets,surface,seeds=read_msh(path)
        records=[]
        for bad in (r for r in report['elements'] if r['below_threshold']):
            tag=bad['element_tag'];conn=tets[tag]
            corners=np.asarray([nodes[i] for i in conn[:4]])
            edges=[float(np.linalg.norm(corners[i]-corners[j])*1000) for i,j in PAIRS]
            center=corners.mean(axis=0)
            assert np.linalg.norm(center-bad['centroid_m'])<1e-10
            records.append({'element_tag':tag,'centroid_m':bad['centroid_m'],
                'wall_distance_mm':bad['wall_distance_mm'],'mu':bad['mu_cos_theta'],
                'minSICN':bad['quality']['minSICN'],'minSJ':bad['quality']['minSJ'],
                'corner_on_pore_count':sum(n in surface for n in conn[:4]),
                'ten_node_on_pore_count':sum(n in surface for n in conn),
                'corner_edge_length_min_mm':min(edges),'corner_edge_length_max_mm':max(edges),
                'corner_edge_ratio_max_over_min':max(edges)/min(edges),
                'corner_node_tags':conn[:4],
                'any_embedded_seed_node':bool(set(conn)&seeds)})
            sites.append((name,np.array(bad['centroid_m'])))
        data['meshes'][name]={'mesh_sha256':expected,'nodes':len(nodes),'Tet10':len(tets),
            'pore_surface_node_count':len(surface),'embedded_pore_seed_node_count':len(seeds),
            'bad_Tet10_count':len(records),'bad_elements':records}
    data['R2_bad_distance_to_R1_bad_mm']={str(data['meshes']['R1']['bad_elements'][i]['element_tag']):
       float(np.linalg.norm(sites[2][1]-sites[i][1])*1000) for i in range(2)}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))

if __name__=='__main__':main()
