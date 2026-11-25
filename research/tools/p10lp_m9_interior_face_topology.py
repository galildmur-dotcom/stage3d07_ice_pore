#!/usr/bin/env python3
"""Read-only M9 Tet10 face-pair and polar-wall support audit (no stresses)."""
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MESH=ROOT/'p10lm_package/P10LM_WORK/M9.msh'
PIN='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
FACES=((1,2,3),(0,3,2),(0,1,3),(0,2,1))
EDGE_MID={(0,1):4,(1,2):5,(0,2):6,(0,3):7,(1,3):8,(2,3):9}
SHELL_MM=(0.,.02,.05,.1,.25,.5,1.,2.,5.,15.)


def parse():
    nodes={};tets=[]
    with MESH.open(encoding='utf8') as f:
        for line in f:
            if line.strip()=='$Nodes':
                count=int(next(f))
                for _ in range(count):
                    fields=next(f).split();nodes[int(fields[0])]=tuple(map(float,fields[1:4]))
            elif line.strip()=='$Elements':
                count=int(next(f))
                for _ in range(count):
                    fields=list(map(int,next(f).split()))
                    if fields[1]==11:
                        tet=fields[3+fields[2]:]
                        tet[8],tet[9]=tet[9],tet[8] # identical to production MSH import
                        tets.append(tet)
    return nodes,tets


def main():
    assert hashlib.sha256(MESH.read_bytes()).hexdigest()==PIN
    nodes,tets=parse();faces=defaultdict(list)
    for e,t in enumerate(tets):
        for side,which in enumerate(FACES):
            key=tuple(sorted(t[i] for i in which))
            faces[key].append((e,side))
    tally=Counter();near_pole=Counter()
    interior=boundary=nonmanifold=0
    for key,incidences in faces.items():
        if len(incidences)==1:boundary+=1;continue
        if len(incidences)!=2:nonmanifold+=1;continue
        interior+=1
        e,side=incidences[0]
        tet=tets[e]
        corners=FACES[side]
        mids=[tet[EDGE_MID[tuple(sorted((corners[a],corners[b])))] ]
              for a,b in ((0,1),(1,2),(2,0))]
        # Curved triangular face at barycentric (1/3,1/3,1/3):
        # each vertex N=-1/9; each edge N=4/9.
        c=tuple((-sum(nodes[tet[i]][j] for i in corners)
                 +4*sum(nodes[mid][j] for mid in mids))/9 for j in range(3))
        d=(c[0],c[1],c[2]-.03)
        r=math.sqrt(sum(q*q for q in d))
        if r==0:continue
        w=(r-.001)*1000
        ir=next((i-1 for i in range(1,len(SHELL_MM)) if w<SHELL_MM[i]),len(SHELL_MM)-1)
        mu=d[2]/r
        im=min(9,max(0,int((mu+1)*5)))
        tally[(ir,im)]+=1
        if ir==0:near_pole[im]+=1
    assert not nonmanifold
    report={'protocol':'P10LP_M9_EXACT_TET10_INTERIOR_FACE_TOPOLOGY',
            'mesh_sha256':PIN,'nodes':len(nodes),'tet10':len(tets),
            'unique_faces':len(faces),'interior_faces':interior,
            'exterior_faces':boundary,'nonmanifold_faces':nonmanifold,
            'first_0_20um_face_centroids_per_mu_bin':{str(k):near_pole[k] for k in range(10)},
            'face_centroids_per_radial_bin':{str(i):sum(tally[(i,im)] for im in range(10)) for i in range(10)},
            'face_centroids_per_radial_and_mu_bin':{
                str(i):{str(im):tally[(i,im)] for im in range(10)} for i in range(10)},
            'first_0_20um_face_centroids_total':sum(near_pole.values()),
            'first_0_20um_face_centroids_polar_north_mu9':near_pole[9],
            'first_0_20um_face_centroids_polar_south_mu0':near_pole[0],
            'note':'Topological availability, not stress jump; centroid evaluated by exact quadratic Tri6 face mapping.',
            'FEM_attempts':0,'mesh_generation_attempts':0}
    (ROOT/'research/P10LP_M9_FACE_SUPPORT_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
