#!/usr/bin/env python3
"""P10HE: sample C2 P10HB mechanical kappa on pinned real M1 Tet10 for Gmsh PostView.

Never launches 1D/2D/3D meshing or FEM. The view is linear inside first-order
chord tetrahedra; it is a *different interpolation* from the original C2 RBF.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile

import numpy as np

import p10hc_continuous_kappa_geo as field

HERE=Path(__file__).resolve().parent
ROOT=Path(r'G:\ildar\Stage3D07')
GMSH=Path(r'C:\gmsh-4.15.2-Windows64\gmsh.exe')
M1_SHA='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
M1_EVIDENCE_SHA='7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3'
REV='P10HE_R1_POSTVIEW_C0_FROM_C2_NODAL_SOURCE_NO_MESH'
QA=HERE/'P10HA_KAPPA_QA.json'
CSV=HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'
GEO=HERE/'P10HE_M2_POSTVIEW_SOURCE_ONLY.geo'
VIEW=HERE/'P10HE_M1_MECHANICAL_KAPPA.pos'
REPORT=HERE/'P10HE_SOURCE_QA.json'
RESULT=HERE/'P10HE_01_RESULT.txt'


def need(x,msg):
    if not x:raise RuntimeError('P10HE_SOURCE_STOP: '+msg)


def sha(b):return hashlib.sha256(b).hexdigest()


def locate_m1_evidence():
    roots=(ROOT/'LOCAL_RUNS',ROOT/'P10GT_TOOLS_R1',Path(r'G:\Downloads'))
    candidates=[]
    for root in roots:
        if root.is_dir():candidates.extend(root.rglob('P10GT_HXT10_EVIDENCE.zip'))
    good=[]
    for p in candidates:
        if p.is_file() and sha(p.read_bytes())==M1_EVIDENCE_SHA:good.append(p)
    need(bool(good),'canonical P10GT_HXT10_EVIDENCE.zip not found in LOCAL_RUNS/P10GT_TOOLS_R1/G:\\Downloads')
    return sorted(good,key=str)[0]


def mesh_from_zip(path):
    with zipfile.ZipFile(path) as z:
        need(z.testzip() is None,'M1 evidence CRC')
        raw=z.read('P10GT_HXT10.msh')
    need(sha(raw)==M1_SHA,'M1 real mesh fingerprint')
    lines=raw.decode('utf-8').splitlines()
    need('$Nodes' in lines and '$Elements' in lines,'ASCII MSH2 expected')
    i=lines.index('$Nodes');n=int(lines[i+1])
    xyz={}
    for line in lines[i+2:i+2+n]:
        v=line.split();need(len(v)==4,'node row')
        xyz[int(v[0])]=tuple(map(float,v[1:4]))
    need(n==13978 and len(xyz)==n,'expected 13978 unique M1 nodes')
    j=lines.index('$Elements');ne=int(lines[j+1])
    tet=[]
    for line in lines[j+2:j+2+ne]:
        v=line.split();typeid=int(v[1]);k=int(v[2]);ids=list(map(int,v[3+k:]))
        if typeid==11:
            need(len(ids)==10 and all(q in xyz for q in ids),'Tet10 node list')
            tet.append(ids)
    need(len(tet)==9623,'expected real M1 9623 Tet10')
    return xyz,np.array(tet,int)


def build_view(nodes,tets,src,score,den):
    ids=np.array(sorted(nodes))
    cart=np.array([nodes[i] for i in ids])
    kap=field.rbf_at_points(src,score,field.physical_query(cart),den)
    need(len(kap)==13978 and np.isfinite(kap).all() and kap.min()>=0 and kap.max()<=1,
         'all M1 nodes kappa valid')
    kv=dict(zip(ids,kap))
    tmp=VIEW.with_suffix('.pos.tmp')
    with tmp.open('w',encoding='ascii',newline='\n') as out:
        out.write('View "P10HE_real_M1_mechanical_kappa_C0_nodal" {\n')
        for nodes10 in tets:
            coordinates=[nodes[int(i)] for i in nodes10[:4]]
            coords=','.join(f'{v:.17g}' for xyz in coordinates for v in xyz)
            values=','.join(f'{kv[int(i)]:.17g}' for i in nodes10[:4])
            # Gmsh parsed POS: SS = scalar tetrahedron (12 coords, 4 scalars).
            # ST would be scalar TRIANGLE (9 coords, 3 scalars): never use ST.
            out.write(f'SS({coords}){{{values}}};\n')
        out.write('};\n')
    tmp.replace(VIEW)
    # Approximation error at curved mid-edge nodes, in *field values*.
    pairs=((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
    residual=[]
    for q in tets:
        for j,(a,b) in enumerate(pairs):
            exact=kv[int(q[4+j])]
            chord_linear=.5*(kv[int(q[a])]+kv[int(q[b])])
            residual.append(abs(exact-chord_linear))
    residual=np.array(residual)
    return {'node_count':len(ids),'tet10_count':len(tets),
            'view_scalar_tetra_count':len(tets),
            'kappa_node_min_max':[float(kap.min()),float(kap.max())],
            'kappa_mid_edge_chord_linear_abs_max':float(residual.max()),
            'kappa_mid_edge_chord_linear_abs_p95':float(np.percentile(residual,95)),
            'kappa_mid_edge_chord_linear_abs_median':float(np.median(residual)),
            'kappa_mid_edge_chord_linear_above_0p05_count':int(np.count_nonzero(residual>.05)),
            'kappa_mid_edge_total':len(residual),
            'postview_sha256':sha(VIEW.read_bytes()),
            'postview_bytes':VIEW.stat().st_size}


def pack_evidence(report):
    dest=HERE/'P10HE_SOURCE_ONLY_EVIDENCE.zip'
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in (REPORT,RESULT,VIEW,GEO,HERE/'P10HE_GMSH_PARSE.log'):
            if p.exists():z.write(p,p.name)
    need(zipfile.ZipFile(dest).testzip() is None,'evidence CRC')
    return dest


def main():
    report={'protocol':REV,'status':'STOP','native_2d':0,'native_3d':0,'FEM':0}
    try:
        need(sys.platform=='win32','run on user Windows PC')
        need(GMSH.is_file(),'exact Gmsh 4.15.2 path missing')
        src,v25,v36,k25,k36,qa=field.load_centers(CSV,QA)
        den=qa['mechanical_only_25_36_shared_smoothing_denominator']
        provenance=locate_m1_evidence()
        nodes,tets=mesh_from_zip(provenance)
        report['M1_evidence_sha256']=M1_EVIDENCE_SHA
        report['M1_mesh_sha256']=M1_SHA
        report['projection']=build_view(nodes,tets,src,v25,den)
        # Merge the 3D scalar view into the exact P10GT source; never modify M1.
        GEO.write_text('Include "P10GT_HXT10.geo";\nMerge "P10HE_M1_MECHANICAL_KAPPA.pos";\n'
                       'Field[40]=PostView;\nField[40].ViewIndex=0;\n'
                       'Field[43]=MathEval;\nField[43].F="F7*(1-0.17*F40)^(1./3.)";\n'
                       'Background Field=43;\n',encoding='utf-8')
        # Pure source syntax verification; no mesh, no automatic run of future M2.
        cmd=[str(GMSH),str(GEO),'-parse_and_exit','-nopopup','-nt','2']
        begin=time.monotonic()
        with (HERE/'P10HE_GMSH_PARSE.log').open('wb') as stream:
            try:r=subprocess.run(cmd,cwd=HERE,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
            except subprocess.TimeoutExpired:raise RuntimeError('native PostView parse timed out 120s')
        log=(HERE/'P10HE_GMSH_PARSE.log').read_text(encoding='utf-8',errors='replace')
        report['native_parse_wall_s']=round(time.monotonic()-begin,3)
        report['native_parse_exit']=r.returncode
        need(r.returncode==0 and not re.search(r'(?m)^\s*Error\s*:',log),'PostView GEO parse fail')
        report['status']='P10HE_SOURCE_POSTVIEW_BUILD_AND_GMSH_PARSE_PASS_NO_MESH'
    except Exception as e:
        report['error']=repr(e)
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    RESULT.write_text(report['status']+'\n'+report.get('error','')+'\n',encoding='utf-8')
    dest=pack_evidence(report)
    print(report['status'],'EVIDENCE='+str(dest),flush=True)
    return 0 if report['status'].endswith('PASS_NO_MESH') else 2


if __name__=='__main__':sys.exit(main())
