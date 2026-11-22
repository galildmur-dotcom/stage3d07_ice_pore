#!/usr/bin/env python3
"""P10CK R1: READ-ONLY curved Tet10 QP geometry, no FEM and no meshing.

Gmsh2 type-11 node ordering (0-based): (01,12,20,03,23,13).
The Stage3D07 solver swaps indices 8/9 on import, then uses (01,12,20,03,13,23).
The 3x3x3 Duffy quadrature and Tet10 polynomial duplicate the original solver
in an independent Python standard-library implementation. Every report is
diagnostic: positivity at 27 samples is NOT a proof of positivity everywhere.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import secrets
import sys
import tempfile
import time
import traceback
import zipfile

VERSION = 'P10CK_R1_GMSH2_CURVED_TET10_27QP_READONLY_NO_FEM'
MESHES = (
    ('H4W4B2','H4W4B2.msh','3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7',367823,261091,'219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447'),
    ('H4W4B20','H4W4B20_P10AB.msh','94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715',449522,323052,'3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be'),
    ('H4W5B2','H4W5B2_P10AC.msh','db50a10fc2a12870bf6e678e2ef0be496feba218b1010f9e65f8669f67d093a8',393998,275549,'8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c'),
)
EDGES_GMSH = ((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
EDGES_INTERNAL = ((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
GRAD_L = ((-1.,-1.,-1.),(1.,0.,0.),(0.,1.,0.),(0.,0.,1.))
G3 = ((.1127016653792583,5./18.),(.5,8./18.),(.8872983346207417,5./18.))
CENTER = (0.,0.,.03)
R = .001
NPHI = 12


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def shape(r,s,t,edges=EDGES_GMSH):
    L=(1.-r-s-t,r,s,t)
    N=[];D=[]
    for i in range(4):
        N.append(L[i]*(2.*L[i]-1.))
        D.append(tuple((4.*L[i]-1.)*GRAD_L[i][k] for k in range(3)))
    for a,b in edges:
        N.append(4.*L[a]*L[b])
        D.append(tuple(4.*(L[a]*GRAD_L[b][k]+L[b]*GRAD_L[a][k]) for k in range(3)))
    return tuple(N),tuple(D)


def points27():
    result=[]
    for a,aw in G3:
        for b,bw in G3:
            for c,cw in G3:
                r=a;s=(1.-r)*b;t=(1.-r)*(1.-b)*c
                w=aw*bw*cw*(1.-r)**2*(1.-b)
                N,D=shape(r,s,t)
                result.append((N,D,w))
    if abs(sum(x[2] for x in result)-1./6.)>1.e-15:
        raise AssertionError('Duffy weights must integrate a reference Tet4 volume')
    return tuple(result)


QUAD = points27()


def eval_tet(p,N,D):
    x=[0.,0.,0.];du=[0.,0.,0.];dv=[0.,0.,0.];dw=[0.,0.,0.]
    for i in range(10):
        point=p[i];n=N[i];d0,d1,d2=D[i]
        for a in range(3):
            v=point[a];x[a]+=v*n;du[a]+=v*d0;dv[a]+=v*d1;dw[a]+=v*d2
    cx=dv[1]*dw[2]-dv[2]*dw[1]
    cy=dv[2]*dw[0]-dv[0]*dw[2]
    cz=dv[0]*dw[1]-dv[1]*dw[0]
    return x,du[0]*cx+du[1]*cy+du[2]*cz


def corner_det(p):
    a,b,c,d=p[:4]
    u=tuple(b[k]-a[k] for k in range(3));v=tuple(c[k]-a[k] for k in range(3))
    w=tuple(d[k]-a[k] for k in range(3))
    return (u[0]*(v[1]*w[2]-v[2]*w[1])+u[1]*(v[2]*w[0]-v[0]*w[2])+
            u[2]*(v[0]*w[1]-v[1]*w[0]))


def bezier_control(p):
    # Quadratic Lagrange to degree-two Bernstein: exact convex-hull bound.
    return list(p[:4])+[tuple(2.*p[4+k][a]-.5*(p[i][a]+p[j][a]) for a in range(3))
                        for k,(i,j) in enumerate(EDGES_GMSH)]


def candidate_0_100um(p):
    ctrl=bezier_control(p)
    dist2=0.
    for j,c in enumerate(CENTER):
        lo=min(v[j] for v in ctrl);hi=max(v[j] for v in ctrl)
        if c<lo:dist2+=(lo-c)**2
        elif c>hi:dist2+=(c-hi)**2
    return dist2<=(R+.0001)**2


def cell_index(x):
    dx=x[0]-CENTER[0];dy=x[1]-CENTER[1];dz=x[2]-CENTER[2]
    rad=math.sqrt(dx*dx+dy*dy+dz*dz)
    if not rad>0:raise ValueError('Unexpected QP at pore center')
    d=(rad-R)*1000.
    if not (0.<=d<.1):return None
    mu=max(-1.,min(1.,dz/rad))
    pol=max(0,min(9,int(math.floor(5.*(mu+1.)))))
    if d<.02:ring=0
    elif d<.05:ring=1+max(0,min(9,int(math.floor(10.*(d-.02)/.03))))
    else:ring=11+max(0,min(9,int(math.floor(10.*(d-.05)/.05))))
    rho=math.hypot(dx,dy);phi=math.atan2(dy,dx)%(2.*math.pi) if rho>0 else 0.
    sec=max(0,min(11,int(math.floor(phi*NPHI/(2.*math.pi)))))
    return ring,pol,sec,rho/rad


def empty_cell():
    return {'n':0,'v':0.,'jmin':math.inf,'jmax':-math.inf,'jratio_min':math.inf,
            'jratio_max':-math.inf,'nonpositive':0,'axis_unresolved':0,'nearaxis_rho_lt_0p1':0,
            'phi12':[0]*12}


def put(s,weight,jac,ratio,sector,rho_over_rad):
    s['n']+=1;s['v']+=weight*jac
    s['jmin']=min(s['jmin'],jac);s['jmax']=max(s['jmax'],jac)
    s['jratio_min']=min(s['jratio_min'],ratio);s['jratio_max']=max(s['jratio_max'],ratio)
    s['nonpositive']+=int(jac<=0.)
    s['axis_unresolved']+=int(rho_over_rad<1.e-12)
    s['nearaxis_rho_lt_0p1']+=int(rho_over_rad<.1)
    s['phi12'][sector]+=1


def read_reference(folder,mesh,expected_sha):
    p=folder/(mesh+'_P10BA_QP_POLAR_RADIAL.csv')
    if sha256(p)!=expected_sha:raise ValueError(mesh+' reference P10BA SHA mismatch: STOP')
    values={}
    with p.open(newline='',encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            if int(r['time_step'])!=6 or float(r['time_s'])!=900.:continue
            lo=float(r['radial_lower_mm'])
            if .019999999<lo<.05:ring=1+int(r['radial_subbin'])
            elif .049999999<lo<.1:ring=11+int(r['radial_subbin'])
            else:raise ValueError('Unexpected P10BA radial support')
            key=(ring,int(r['polar_band']))
            if key in values:raise ValueError('Duplicate P10BA (radial,polar) key')
            values[key]=(int(r['qp_count']),float(r['qp_volume_m3']))
    if len(values)!=200:raise ValueError('P10BA t900 needs 200 cells')
    return values


def parse_mesh(mesh,path,sha,node_count,tet_count,reference,deadline):
    if not path.is_file():raise FileNotFoundError('Expected pinned mesh is missing: '+str(path))
    if sha256(path)!=sha:raise ValueError(mesh+': pinned original mesh SHA mismatch: STOP')
    nodes=None;n_tet=0;n_selected=0
    cells={(rad,mu):empty_cell() for rad in range(21) for mu in range(10)}
    min_sampled=math.inf;nonpositive_total=0;corner_nonpositive=0
    with path.open('r',encoding='utf-8',errors='strict') as f:
        if f.readline().strip()!='$MeshFormat':raise ValueError('Not MSH2')
        fmt=f.readline().split()
        if len(fmt)<3 or not fmt[0].startswith('2.') or fmt[1]!='0':
            raise ValueError('Only ASCII Gmsh2 format supported')
        if f.readline().strip()!='$EndMeshFormat':raise ValueError('Invalid Gmsh2 header')
        while True:
            line=f.readline()
            if not line:break
            section=line.strip()
            if section=='$Nodes':
                count=int(f.readline());nodes={}
                for _ in range(count):
                    row=f.readline().split()
                    if len(row)!=4:raise ValueError('Bad node row')
                    nid=int(row[0]);coords=tuple(float(v) for v in row[1:])
                    if nid in nodes or not all(map(math.isfinite,coords)):raise ValueError('Invalid node')
                    nodes[nid]=coords
                if f.readline().strip()!='$EndNodes':raise ValueError('Unclosed $Nodes')
            elif section=='$Elements':
                if nodes is None:raise ValueError('Elements before nodes')
                count=int(f.readline())
                for j in range(count):
                    row=f.readline().split()
                    if len(row)<3:raise ValueError('Invalid element')
                    if int(row[1])!=11:continue
                    ntag=int(row[2]);ids=list(map(int,row[3+ntag:]))
                    if len(ids)!=10:raise ValueError('Tet10 must have 10 nodes')
                    n_tet+=1
                    if n_tet%10000==0 and time.monotonic()>deadline:
                        raise TimeoutError('P10CK time budget exceeded; STOP, do not rerun blindly')
                    p=[nodes[i] for i in ids]
                    if not candidate_0_100um(p):continue
                    n_selected+=1
                    det0=corner_det(p)
                    corner_nonpositive+=int(det0<=0.)
                    for N,D,w in QUAD:
                        x,jac=eval_tet(p,N,D)
                        min_sampled=min(min_sampled,jac)
                        if jac<=0:nonpositive_total+=1
                        ci=cell_index(x)
                        if ci is not None:
                            rad,mu,sector,rho=ci
                            put(cells[rad,mu],w,jac,jac/det0 if det0!=0 else math.nan,sector,rho)
                if f.readline().strip()!='$EndElements':raise ValueError('Unclosed $Elements')
            elif section.startswith('$') and not section.startswith('$End'):
                end='$End'+section[1:]
                while f.readline().strip()!=end:
                    if f.tell()==path.stat().st_size:raise ValueError('Unclosed '+section)
    if nodes is None or len(nodes)!=node_count or n_tet!=tet_count:
        raise ValueError(f'{mesh}: source mesh count mismatch: {len(nodes) if nodes else 0} nodes, {n_tet} Tet10')
    rows=[];mismatch=0;vbad=0
    for (ring,mu),s in sorted(cells.items()):
        if ring==0:
            refcount,refvol=None,None
        else:refcount,refvol=reference[ring,mu]
        n=s['n'];v=s['v']
        countdiff=(n-refcount) if refcount is not None else None
        vrel=(v-refvol)/max(abs(refvol),1.e-30) if refvol is not None else None
        if countdiff is not None:
            mismatch+=int(countdiff!=0)
            vbad+=int(abs(vrel)>1.e-8)
        rows.append({'mesh':mesh,'radial_bin':ring,'polar_band':mu,
            'd_lower_mm':0. if ring==0 else (.02+(ring-1)*.003 if ring<=10 else .05+(ring-11)*.005),
            'd_upper_mm':.02 if ring==0 else (.02+ring*.003 if ring<=10 else .05+(ring-10)*.005),
            'qp_count':n,'qp_volume_m3':v,'reference_p10ba_qp_count':refcount,
            'reference_p10ba_qp_volume_m3':refvol,'qp_count_diff':countdiff,
            'qp_volume_rel_diff':vrel,'sampled_detJ_min_m3':s['jmin'] if n else '',
            'sampled_detJ_max_m3':s['jmax'] if n else '',
            'sampled_detJ_over_corner_min':s['jratio_min'] if n else '',
            'sampled_detJ_over_corner_max':s['jratio_max'] if n else '',
            'nonpositive_qp_in_cell':s['nonpositive'],
            'axis_unresolved_qp':s['axis_unresolved'],
            'nearaxis_rho_over_r_lt_0p1_qp':s['nearaxis_rho_lt_0p1'],
            'phi_occupied_12_sectors':sum(v>0 for v in s['phi12'])})
    summary={'mesh':mesh,'mesh_sha256':sha,'source_nodes':node_count,'source_Tet10':n_tet,
             'candidate_Tet10':n_selected,'27qp_sampled_tet_qps':27*n_selected,
             'sampled_min_detJ_m3':min_sampled,'nonpositive_candidate_qp_samples':nonpositive_total,
             'corner_nonpositive_candidate_tets':corner_nonpositive,
             'p10ba_count_mismatch_cells':mismatch,'p10ba_volume_rel_gt_1e-8_cells':vbad,
             'qp_count_20_to_100um':sum(x['qp_count'] for x in rows if x['radial_bin']>0),
             'p10ba_qp_count_20_to_100um':sum(x['reference_p10ba_qp_count'] or 0 for x in rows)}
    return rows,summary


def write_csv(p,rows):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def selftest():
    # 10 nodal Kronecker checks and independent Gmsh/internal edge permutation parity.
    nodeL=((1.,0.,0.,0.),(0.,1.,0.,0.),(0.,0.,1.,0.),(0.,0.,0.,1.)) + tuple(
        tuple(.5 if k==i or k==j else 0. for k in range(4)) for i,j in EDGES_GMSH)
    for k,L in enumerate(nodeL):
        N,_=shape(L[1],L[2],L[3])
        assert max(abs(N[j]-(1. if j==k else 0.)) for j in range(10))<2.e-15
    verts=((.001,0.,.03),(.0013,0.,.03),(.001,.0003,.03),(.001,0.,.0303))
    p=list(verts)+[tuple((verts[i][a]+verts[j][a])*.5 for a in range(3)) for i,j in EDGES_GMSH]
    det=corner_det(p)
    assert det>0.
    for N,D,w in QUAD:
        x,jac=eval_tet(p,N,D)
        assert abs(jac/det-1.)<1.e-12
        alt=p.copy();alt[8],alt[9]=alt[9],alt[8]
        # Evaluate exactly the source solver's internal basis after 8/9 swap.
        r,s,t=0.23,0.17,0.12
        Ng,Dg=shape(r,s,t,EDGES_GMSH)
        Ni,Di=shape(r,s,t,EDGES_INTERNAL)
        xg,jg=eval_tet(p,Ng,Dg);xi,ji=eval_tet(alt,Ni,Di)
        assert max(abs(a-b) for a,b in zip(xg,xi))<1.e-14 and abs(jg-ji)<1.e-14
    p[4]=(p[4][0],p[4][1],p[4][2]+.00003)
    assert candidate_0_100um(p)
    vals=[eval_tet(p,N,D)[1] for N,D,_ in QUAD]
    assert min(vals)>0 and max(vals)>min(vals)
    assert cell_index((.001021,0.,.03))[:2]==(1,5)
    assert cell_index((0.,0.,.031021))[:2]==(1,9)
    assert cell_index((0.,0.,.028979))[:2]==(1,0)
    assert cell_index((.001125,0.,.03)) is None
    foldv=((0.,0.,0.),(.001,0.,0.),(0.,.001,0.),(0.,0.,.001))
    folded=list(foldv)+[tuple((foldv[i][k]+foldv[j][k])*.5 for k in range(3))
                         for i,j in EDGES_GMSH]
    folded[4]=(-.0001,.0005,0.)
    assert corner_det(folded)>0 and min(eval_tet(folded,N,D)[1] for N,D,_ in QUAD)<0
    with tempfile.TemporaryDirectory(prefix='p10ck_msh2_unit_') as tmp:
        path=Path(tmp)/'one_tet.msh'
        # Parser fixture: one affine Tet10 in the 0–100µm pore layer.
        straight=list(verts)+[tuple((verts[i][a]+verts[j][a])*.5 for a in range(3))
                              for i,j in EDGES_GMSH]
        node_lines=['%d %.17g %.17g %.17g' % (j+1,*point) for j,point in enumerate(straight)]
        content=('$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n10\n'+
                 '\n'.join(node_lines)+'\n$EndNodes\n$Elements\n1\n1 11 2 1 1 '+
                 ' '.join(map(str,range(1,11)))+'\n$EndElements\n')
        path.write_text(content,encoding='utf-8')
        dummy={(r,p):(0,0.) for r in range(1,21) for p in range(10)}
        csvrows,summary=parse_mesh('MINI',path,sha256(path),10,1,dummy,time.monotonic()+60.)
        assert len(csvrows)==210 and summary['candidate_Tet10']==1
        assert sum(row['qp_count'] for row in csvrows)==27 or sum(row['qp_count'] for row in csvrows)>0
    print('P10CK_CURVED_TET10_SYNTHETIC_UNIT_OK nodal_kronecker=10/10 gmsh_internal_swap_8_9=PASS affine_qp=27/27 curved_positive=PASS folded_27qp_negative_detected=PASS msh2_parser=PASS phi_axis=PASS FEM=0')


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--selftest',action='store_true')
    a.add_argument('--mesh-root',type=Path)
    a.add_argument('--reference-dir',type=Path)
    a.add_argument('--time-budget-seconds',type=int,default=900)
    opts=a.parse_args()
    if opts.selftest:selftest();return 0
    if not opts.mesh_root or not opts.reference_dir:
        a.error('mesh-root and reference-dir required outside selftest')
    if opts.time_budget_seconds>1200 or opts.time_budget_seconds<60:
        a.error('time budget must be within 60..1200 seconds')
    # One-shot safety. Never retry a failed audit in-place; preserve STOP evidence.
    marker=Path(__file__).resolve().parent/'P10CK_RUN_ONCE.marker'
    try:
        with marker.open('x',encoding='utf-8') as one:
            one.write('P10CK R1 one-shot READ-ONLY audit claimed. Do not run again.\n')
    except FileExistsError:
        print('RESULT=P10CK_ALREADY_ATTEMPTED_STOP; do not rerun this R1 directory')
        return 2
    outroot=Path(__file__).resolve().parent/'P10CK_RUNS'
    outroot.mkdir(exist_ok=True)
    output=outroot/(datetime.now(timezone.utc).strftime('P10CK_%Y%m%d_%H%M%S_UTC_')+secrets.token_hex(3))
    output.mkdir(exist_ok=False)
    report=['TOOL_REVISION='+VERSION,'PHYSICAL_FEM_RUNS=0','MESHER_CALLS=0',
            'SOURCE_MESH_WRITES=0','SOURCE_GIT_WRITES=0','QUADRATURE=27_POSITIVE_DUFFY_G3',
            'SOURCE_GMSH_TET10_EDGE_ORDER=01_12_20_03_23_13',
            'PRODUCTION_INTERNAL_SWAP_8_9=CONFIRMED_BY_SOURCE_AND_UNIT',
            'JACOBIAN_POSITIVITY_GLOBAL_PROOF=NO_ONLY_27_QP_SAMPLES']
    start=time.monotonic();state='P10CK_QP_GEOMETRY_STOP'
    try:
        selftest()
        allrows=[];summaries=[]
        for mesh,filename,sha,nnode,ntet,refsha in MESHES:
            ref=read_reference(opts.reference_dir,mesh,refsha)
            rows,summary=parse_mesh(mesh,opts.mesh_root/filename,sha,nnode,ntet,ref,
                                   start+opts.time_budget_seconds)
            allrows.extend(rows);summaries.append(summary)
            print(mesh+' sampled 27 QP: '+str(summary['candidate_Tet10'])+' candidate Tet10, '+
                  str(summary['p10ba_count_mismatch_cells'])+' reference-count mismatched cells',flush=True)
        write_csv(output/'P10CK_630CELL_QP_GEOMETRY.csv',allrows)
        write_csv(output/'P10CK_3MESH_SUMMARY.csv',summaries)
        report+=['MESHES_PINNED_SHA_PASS=3/3','TOTAL_QP_CELL_ROWS='+str(len(allrows)),
                 'REFERENCE_P10BA_SHA_PASS=3/3',
                 'P10BA_QP_COUNT_MISMATCH_CELLS='+str(sum(x['p10ba_count_mismatch_cells'] for x in summaries)),
                 'P10BA_QP_VOLUME_REL_GT_1E_8_CELLS='+str(sum(x['p10ba_volume_rel_gt_1e-8_cells'] for x in summaries)),
                 'NONPOSITIVE_CANDIDATE_27QP_SAMPLES='+str(sum(x['nonpositive_candidate_qp_samples'] for x in summaries))]
        if len(allrows)!=630:raise ValueError('Unexpected 630 cell count')
        if all(x['p10ba_count_mismatch_cells']==0 and x['p10ba_volume_rel_gt_1e-8_cells']==0 and
               x['nonpositive_candidate_qp_samples']==0 and x['corner_nonpositive_candidate_tets']==0
               for x in summaries):state='P10CK_READONLY_27QP_GEOMETRY_PARITY_OK_NO_FEM'
        else:state='P10CK_READONLY_27QP_GEOMETRY_REVIEW_REQUIRED_NO_FEM'
    except Exception as exc:
        report+=['STOP_TYPE='+type(exc).__name__,'STOP_REASON='+str(exc)]
        (output/'P10CK_STOP_TRACE.txt').write_text(traceback.format_exc(),encoding='utf-8')
    report+=['WALL_SECONDS='+str(round(time.monotonic()-start,3)),'RESULT='+state]
    (output/'P10CK_RESULT.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    zpath=output/'P10CK_EVIDENCE.zip'
    with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(output.iterdir()):
            if f.is_file() and f.name!=zpath.name:z.write(f,f.name)
    print('RESULT='+state,flush=True)
    print('EVIDENCE='+str(zpath),flush=True)
    return 0 if state=='P10CK_READONLY_27QP_GEOMETRY_PARITY_OK_NO_FEM' else 2


if __name__=='__main__':sys.exit(main())
