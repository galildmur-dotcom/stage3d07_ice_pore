"""Independent Tet10 mean-ratio and curved Tri6 topology QA; read-only MSH2."""
from __future__ import annotations

from collections import Counter, defaultdict
import math
from pathlib import Path
import statistics

from p10gi_independent_surface_audit import QUAD, jac7, norm, cross, sub, dot, quantile

CENTRE=(0.,0.,.03)
PORE=0.001
B6=0.006
EDGES=((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))


def need(ok,msg):
    if not ok:raise ValueError("P10GJ_MESH_EXTRA_STOP: "+msg)


def read_msh(path):
    nodes={}; tri=defaultdict(list); tet=[]; types=Counter()
    with Path(path).open("r",encoding="ascii") as f:
        need(next(f).strip()=="$MeshFormat","MSH header")
        need(next(f).strip()=="2.2 0 8","only ASCII MSH2.2")
        need(next(f).strip()=="$EndMeshFormat","bad MSH header end")
        for line in f:
            if line.strip()=="$Nodes":
                n=int(next(f));need(0<n<=500000,"node count resource cap")
                for _ in range(n):
                    p=next(f).split();need(len(p)==4,"bad node row")
                    node=int(p[0]);need(node not in nodes,"duplicate node")
                    v=tuple(float(x) for x in p[1:])
                    need(all(math.isfinite(x) for x in v),"nonfinite node")
                    nodes[node]=v
                need(next(f).strip()=="$EndNodes","nodes end")
            elif line.strip()=="$Elements":
                n=int(next(f));need(0<n<1000000,"element resource cap")
                for _ in range(n):
                    row=list(map(int,next(f).split()));need(len(row)>=4,"bad element row")
                    _,kind,ntags=row[:3];physical=row[3] if ntags else 0
                    ids=row[3+ntags:];types[kind]+=1
                    if kind==9:
                        need(len(ids)==6 and 2<=physical<=9,"Tri6 physical tag")
                        tri[physical].append(ids)
                    elif kind==11:
                        need(len(ids)==10 and physical==1,"Tet10 physical tag")
                        tet.append(ids)
                    else:need(False,"forbidden element type "+str(kind))
                need(next(f).strip()=="$EndElements","elements end")
    need(nodes and tet and set(tri)==set(range(2,10)),"missing physical groups")
    need(all(n in nodes for faces in tri.values() for ids in faces for n in ids),
         "unknown face node")
    need(all(n in nodes for ids in tet for n in ids),"unknown tetra node")
    return nodes,tri,tet,types


def quality_triangle(p):
    a,b,c=p[:3]
    v=cross(sub(b,a),sub(c,a))
    e2=sum(norm(sub(p[i],p[j]))**2 for i,j in ((0,1),(1,2),(2,0)))
    return 2*math.sqrt(3)*norm(v)/e2 if e2>0 else 0.


def surface(nodes,faces,physical):
    rad=PORE if physical==8 else B6
    q=[];pos={"north":[],"south":[]};area=0.;jacmin=math.inf
    rmax=0.;signs=[];corners=set();edge=Counter();mid={}
    for ids in faces:
        p=[nodes[i] for i in ids]
        q0=quality_triangle(p);need(math.isfinite(q0) and q0>.001,"bad corner Tri6")
        q.append(q0)
        v=p[:3];ctr=tuple(sum(x[k] for x in v)/3 for k in range(3))
        rr=norm(sub(ctr,CENTRE));mu=(ctr[2]-.03)/rr
        if mu>=.8:pos["north"].append(q0)
        if mu<=-.8:pos["south"].append(q0)
        corners.update(ids[:3]);signs.append(dot(cross(sub(v[1],v[0]),sub(v[2],v[0])),sub(ctr,CENTRE)))
        for a,b,m in ((ids[0],ids[1],ids[3]),(ids[1],ids[2],ids[4]),
                      (ids[2],ids[0],ids[5])):
            k=tuple(sorted((a,b)));edge[k]+=1
            if k in mid:need(mid[k]==m,"nonconforming mid-edge node")
            mid[k]=m
        for p0 in p:rmax=max(rmax,abs(norm(sub(p0,CENTRE))-rad))
        for r,s,w in QUAD:
            j=jac7(p,r,s);need(j>0 and math.isfinite(j),"bad curved surface Jacobian")
            jacmin=min(jacmin,j);area+=w*j
    need(q and pos["north"] and pos["south"],"missing polar surface coverage")
    need(all(n==2 for n in edge.values()),"open/nonmanifold sphere")
    chi=len(corners)-len(edge)+len(faces)
    need(chi==2,"sphere Euler characteristic")
    need(all(s>0 for s in signs) or all(s<0 for s in signs),"mixed sphere orientation")
    need(rmax<1e-8,"radius error")
    return {"tri6":len(faces),"q_min":min(q),"q_p05":quantile(q,.05),
            "q_median":statistics.median(q),
            "north_count":len(pos["north"]),"south_count":len(pos["south"]),
            "north_qmin":min(pos["north"]),"south_qmin":min(pos["south"]),
            "curved7_min_jac":jacmin,"curved7_area_ratio":area/(4*math.pi*rad**2),
            "max_radius_error_m":rmax,"closed_euler":chi,"every_edge_twice":True,
            "mid_edge_conforming":True}


def tet_quality(nodes,ids):
    p=[nodes[i] for i in ids[:4]]
    v=dot(sub(p[1],p[0]),cross(sub(p[2],p[0]),sub(p[3],p[0])))
    need(v>0 and math.isfinite(v),"nonpositive corner Tet10")
    denom=sum(norm(sub(p[i],p[j]))**2 for i,j in EDGES)
    return 12*(v/2)**(2/3)/denom


def audit(path):
    nodes,tri,tet,types=read_msh(path)
    q=[];qnear=[]
    for ids in tet:
        t=tet_quality(nodes,ids);q.append(t)
        centre=tuple(sum(nodes[n][i] for n in ids[:4])/4 for i in range(3))
        d=sub(centre,CENTRE);r=norm(d)
        if r-PORE<=.0005 and r>0 and abs(d[2]/r)>=.6:qnear.append(t)
    need(len(qnear)>=10,"near-polar Tet10 quality coverage missing")
    s8=surface(nodes,tri[8],8);s9=surface(nodes,tri[9],9)
    return {"nodes":len(nodes),"tet10":len(tet),
            "tri6_total":sum(map(len,tri.values())),
            "types":{str(k):v for k,v in types.items()},
            "physical_tags":[1]+sorted(tri),
            "mean_ratio_min":min(q),"mean_ratio_p01":quantile(q,.01),
            "mean_ratio_median":statistics.median(q),
            "near_polar_tet10":len(qnear),
            "near_polar_mean_ratio_min":min(qnear),
            "near_polar_mean_ratio_p05":quantile(qnear,.05),
            "pore":s8,"B6":s9}
