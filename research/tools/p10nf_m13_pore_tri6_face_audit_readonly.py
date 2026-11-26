#!/usr/bin/env python3
"""P10NF: compare bad Tet10 pore-facing triangles with all curved Tri6 surface faces."""
import hashlib,json,math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'p10nf_m13_pore_faces/P10NF_R1_R2_PORE_TRI6_FACE_QUALITY.json'
SOURCES=(('R1',ROOT/'p10mv_m13_evidence/P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh',
    ROOT/'upload/P10MY_M13_R1_BAD_TET10_LOCATIONS.json',
    '3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'),
   ('R2',ROOT/'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh',
    ROOT/'upload/P10ND_M13_R2_BAD_TET10_LOCATIONS.json',
    '57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'))

def read(path):
    nodes={};tet={};surface={}
    with path.open(encoding='ascii') as f:
        for line in f:
            if line.strip()=='$Nodes':
                for _ in range(int(next(f))):
                    tag,*coords=next(f).split();nodes[int(tag)]=np.array([float(v) for v in coords])
            elif line.strip()=='$Elements':
                for _ in range(int(next(f))):
                    row=list(map(int,next(f).split()));eid,kind,nt=row[:3];phys=row[3] if nt else 0
                    conn=row[3+nt:]
                    if kind==11:tet[eid]=conn
                    elif kind==9 and phys==8:surface[tuple(sorted(conn[:3]))]=(eid,conn)
    return nodes,tet,surface

def faceinfo(nodes,conn):
    p=np.asarray([nodes[k] for k in conn[:3]])
    a,b,c=(float(np.linalg.norm(p[i]-p[j])) for i,j in ((0,1),(1,2),(2,0)))
    angles=[]
    for u,v,w in ((a,c,b),(a,b,c),(b,c,a)):
        cos=np.clip((u*u+v*v-w*w)/(2*u*v),-1.,1.)
        angles.append(math.degrees(math.acos(cos)))
    return {'min_corner_angle_deg':min(angles),'max_corner_angle_deg':max(angles),
        'min_corner_edge_mm':min(a,b,c)*1000,'max_corner_edge_mm':max(a,b,c)*1000}

def main():
    if OUT.exists():raise RuntimeError('P10NF no overwrite')
    out={'protocol':'P10NF_BAD_TET_PORE_TRI6_FACE_READONLY','status':'MEASURED_NO_GMSH_NO_FEM_NO_MARKER',
         'meshes':{},'mesh_generation_attempts':0,'FEM_attempts':0}
    for name,mesh,loc,expected in SOURCES:
        assert hashlib.sha256(mesh.read_bytes()).hexdigest()==expected
        bad=json.loads(loc.read_text(encoding='utf-8-sig'))
        assert bad['mesh_sha256']==expected
        nodes,tets,surface=read(mesh)
        allmin=np.array([faceinfo(nodes,conn)['min_corner_angle_deg'] for _,conn in surface.values()])
        faces=[]
        for record in (r for r in bad['elements'] if r['below_threshold']):
            cn=tets[record['element_tag']];surfaceface=[k for k in cn[:4] if
                    any(k in key for key in surface)]
            # The bad boundary tetrahedra share exactly 3 corner nodes with the pore.
            target=[(key,val) for key,val in surface.items() if set(key)<=set(cn[:4])]
            assert len(target)==1,(name,record['element_tag'],len(target))
            _,(tri_tag,tri)=target[0]
            info=faceinfo(nodes,tri)
            info.update({'failed_tet_tag':record['element_tag'],'pore_tri6_tag':tri_tag,
                         'min_angle_percentile_among_pore_tri6':float(100*(allmin<=info['min_corner_angle_deg']).mean()),
                         'failed_minSJ':record['quality']['minSJ']})
            faces.append(info)
        out['meshes'][name]={'mesh_sha256':expected,'pore_Tri6':len(surface),
             'pore_face_min_angle_deg':float(allmin.min()),
             'pore_face_min_angle_p01_deg':float(np.percentile(allmin,1)),
             'pore_face_min_angle_median_deg':float(np.median(allmin)),
             'bad_tet_pore_faces':faces}
    OUT.parent.mkdir()
    OUT.write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
