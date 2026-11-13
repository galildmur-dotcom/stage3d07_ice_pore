#!/usr/bin/env python3
"""P10Z: geometry-only Tet10 quadrature shell audit for Stage3D07/P10Y.

Reads Gmsh 2.2 ASCII msh (Tet10 type 11); does NOT solve any FEM equation.
Uses Gmsh node ordering and Duffy product Gauss-Legendre quadrature.
Q3 (27 QP/Tet10) follows the documented P10Y volume_q(3) construction.
Q4 (64 QP/Tet10) is an independent sensitivity-to-quadrature diagnostic;
Q4 results are NOT the P10Y discrete shape derivative.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import math
from pathlib import Path
import sys
import time

try:
    import numpy as np
except ImportError as exc:
    raise SystemExit("Python numpy is required. Install with: py -3 -m pip install numpy") from exc

# P10Y spatial bins: distance from nominal spherical pore surface, mm.
EDGES_MM = [0., .02, .05, .1, .25, .5, 1., 2., 5., 15.]
BINS = len(EDGES_MM)
CUMULATIVE_CUT_MM = [0.005,0.01,0.015,0.02,0.025,0.03,0.04,0.05,0.075,0.1,0.2,0.25,0.5,1.,2.,5.]
# Gmsh 2.2 10-node tetrahedra: 4 corners then edges 01,12,20,03,23,13.
EDGE_PAIRS = np.array([(0,1),(1,2),(2,0),(0,3),(2,3),(1,3)],dtype=np.intp)
D_L = np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])


def tet10_shape(u, v, t):
    """Isoparametric Tet10 shape functions and dN/d(r,s,t)."""
    l = np.stack((1. - u - v - t, u, v, t), axis=-1)
    nc = l.shape[0]
    n = np.zeros((nc,10), dtype=np.float64)
    dn = np.zeros((nc,10,3), dtype=np.float64)
    n[:,:4] = l * (2.*l - 1.)
    dn[:,:4,:] = (4.*l - 1.)[:,:,None] * D_L[None,:,:]
    for j,(a,b) in enumerate(EDGE_PAIRS):
        n[:,4+j] = 4.*l[:,a]*l[:,b]
        dn[:,4+j,:] = 4.*(l[:,a,None]*D_L[b] + l[:,b,None]*D_L[a])
    return n, dn


def quadrature(order):
    roots, weights = np.polynomial.legendre.leggauss(order)
    roots = .5*(roots + 1.)
    weights = .5*weights
    rs = []; ws = []
    for i,a in enumerate(roots):
        for j,b in enumerate(roots):
            for k,c in enumerate(roots):
                r = a
                s = (1.-a)*b
                t = (1.-a)*(1.-b)*c
                w = weights[i]*weights[j]*weights[k]*(1.-a)**2*(1.-b)
                rs.append((r,s,t)); ws.append(w)
    bary = np.array(rs, dtype=np.float64)
    n,dn = tet10_shape(bary[:,0],bary[:,1],bary[:,2])
    return n,dn,np.array(ws,dtype=np.float64)


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def read_msh2_ascii(path):
    """Return (coordinates [N,3], connectivity [E,10]). Unit: metres."""
    with open(path,'r',encoding='utf-8',errors='strict',newline=None) as f:
        if f.readline().strip() != '$MeshFormat':
            raise ValueError('Not a Gmsh .msh file')
        hdr = f.readline().split()
        if len(hdr)<3 or not hdr[0].startswith('2.') or hdr[1]!='0':
            raise ValueError('Only Gmsh 2.x ASCII MSH is supported; use Gmsh to EXPORT a NEW ASCII msh2 copy (do not overwrite source)')
        if f.readline().strip()!='$EndMeshFormat':
            raise ValueError('Invalid $MeshFormat block')
        xyz=None; ids=None; tets=[]; n_elements_declared=0
        while True:
            line=f.readline()
            if not line: break
            section=line.strip()
            if section=='$Nodes':
                n_nodes=int(f.readline())
                xyz=np.empty((n_nodes,3),dtype=np.float64)
                ids=np.empty(n_nodes,dtype=np.int64)
                for i in range(n_nodes):
                    p=f.readline().split()
                    if len(p)<4: raise ValueError(f'Truncated node table at node {i}')
                    ids[i]=int(p[0]);xyz[i]=[float(v) for v in p[1:4]]
                if f.readline().strip()!='$EndNodes':
                    raise ValueError('Missing $EndNodes')
            elif section=='$Elements':
                n_elements_declared=int(f.readline())
                for i in range(n_elements_declared):
                    fields=f.readline().split()
                    if len(fields)<3:raise ValueError(f'Truncated element table at element {i}')
                    if fields[1]!='11':continue
                    ntags=int(fields[2])
                    nodes=fields[3+ntags:3+ntags+10]
                    if len(nodes)!=10:raise ValueError('Invalid Tet10 connectivity')
                    tets.append([int(v) for v in nodes])
                if f.readline().strip()!='$EndElements':
                    raise ValueError('Missing $EndElements')
            elif section.startswith('$') and not section.startswith('$End'):
                # Skip other ASCII sections: physical names, periodic tags, etc.
                end='$End'+section[1:]
                while True:
                    x=f.readline()
                    if not x:raise ValueError(f'Unclosed section {section}')
                    if x.strip()==end:break
    if xyz is None or ids is None or not tets:
        raise ValueError('MSH2 must contain $Nodes and at least one type-11 Tet10')
    if len(np.unique(ids))!=len(ids):raise ValueError('Duplicate node IDs')
    order=np.argsort(ids)
    sorted_ids=ids[order]
    connectivity=np.asarray(tets,dtype=np.int64)
    ix=np.searchsorted(sorted_ids,connectivity)
    if np.any(ix>=len(ids)) or np.any(sorted_ids[ix]!=connectivity):
        raise ValueError('Tet10 references unknown node IDs')
    return xyz,order[ix],n_elements_declared


def jacobian_determinant(j):
    a,b,c=j[...,0,0],j[...,0,1],j[...,0,2]
    d,e,f=j[...,1,0],j[...,1,1],j[...,1,2]
    g,h,k=j[...,2,0],j[...,2,1],j[...,2,2]
    return a*(e*k-f*h)-b*(d*k-f*g)+c*(d*h-e*g)


def percentiles(chunks):
    if not chunks:return ('','','','','')
    a=np.concatenate(chunks)
    p=np.percentile(a,[10,50,90])
    return (float(p[0]),float(p[1]),float(p[2]),float(a.min()),float(a.max()))


def run_one(mesh_name, mesh_file, orders, out, center, r0_mm, chunk_elems):
    t0=time.perf_counter()
    xyz,tets,all_elements=read_msh2_ascii(mesh_file)
    if not np.all(np.isfinite(xyz)):raise ValueError('Nonfinite mesh coordinates')
    model_sha=sha256(mesh_file)
    center=np.asarray(center,dtype=float)
    radius_m=r0_mm*1e-3
    total_tets=len(tets)
    print(f'[{mesh_name}] read nodes={len(xyz)} tet10={total_tets}, total-element-records={all_elements}',flush=True)
    rows=[]; cumulative=[]
    for order in orders:
        N,dN,gw=quadrature(order)
        nq=len(gw)
        qcount=np.zeros(BINS,dtype=np.int64)
        vol_m3=np.zeros(BINS)
        sqvol_m6=np.zeros(BINS)
        elem_count=np.zeros(BINS,dtype=np.int64)
        mixed_count=np.zeros(BINS,dtype=np.int64)
        span_chunks=[[] for _ in range(BINS)]
        edge_chunks=[[] for _ in range(BINS)]
        total_vol=0.; n_inverted=0;n_negative_distance=0
        cumul_vol=np.zeros(len(CUMULATIVE_CUT_MM));cumul_n=np.zeros(len(CUMULATIVE_CUT_MM),dtype=np.int64)
        for start in range(0,total_tets,chunk_elems):
            stop=min(start+chunk_elems,total_tets)
            P=xyz[tets[start:stop]] # [E,10,3]
            xq=np.einsum('qk,ekc->eqc',N,P,optimize=True)
            Jac=np.einsum('qkj,ekc->eqcj',dN,P,optimize=True)
            det=jacobian_determinant(Jac)
            n_inverted+=int(np.count_nonzero(det<=0.))
            if n_inverted:raise ValueError(f'Invalid non-positive Tet10 Jacobian: {mesh_name} order={order}; inspect orientation and node order')
            w=det*gw[None,:]
            total_vol+=float(np.sum(w))
            dist=(np.linalg.norm(xq-center[None,None,:],axis=2)-radius_m)*1e3
            n_negative_distance+=int(np.count_nonzero(dist<0))
            for ci,cut in enumerate(CUMULATIVE_CUT_MM):
                inside=(dist<cut)
                cumul_n[ci]+=int(inside.sum())
                cumul_vol[ci]+=float(w[inside].sum())
            bin_index=np.searchsorted(EDGES_MM[1:],dist,side='right')
            qcount+=np.bincount(bin_index.ravel(),minlength=BINS)
            vol_m3+=np.bincount(bin_index.ravel(),weights=w.ravel(),minlength=BINS)
            sqvol_m6+=np.bincount(bin_index.ravel(),weights=(w*w).ravel(),minlength=BINS)
            dist_nodes=(np.linalg.norm(P-center[None,None,:],axis=2)-radius_m)*1e3
            radial_span=dist_nodes.max(axis=1)-dist_nodes.min(axis=1)
            corners=P[:,:4,:]
            lengths=np.linalg.norm(corners[:,EDGE_PAIRS[:,0],:]-corners[:,EDGE_PAIRS[:,1],:],axis=2)*1e3
            longest=lengths.max(axis=1)
            present=np.zeros((stop-start,BINS),dtype=np.bool_)
            for b in range(BINS):
                occurs=np.any(bin_index==b,axis=1)
                present[:,b]=occurs
                elem_count[b]+=int(occurs.sum())
                if np.any(occurs):
                    span_chunks[b].append(radial_span[occurs])
                    edge_chunks[b].append(longest[occurs])
            mixed=(present.sum(axis=1)>1)
            mixed_count+=np.sum(present & mixed[:,None],axis=0)
        for b in range(BINS):
            a=EDGES_MM[b]
            upper=EDGES_MM[b+1] if b+1<BINS else None
            if upper is not None:
                spherical_ref_m3=(4.*math.pi/3.)*((r0_mm+upper)**3-(r0_mm+a)**3)*1e-9
                ratio=vol_m3[b]/spherical_ref_m3
            else:
                spherical_ref_m3=float('nan');ratio=float('nan')
            hs=percentiles(span_chunks[b]);he=percentiles(edge_chunks[b]);neff=(vol_m3[b]**2/sqvol_m6[b]) if sqvol_m6[b]>0 else 0.
            rows.append({'mesh':mesh_name,'mesh_sha256':model_sha,'quadrature_order':order,
             'qp_per_tet10':nq,'shell':b,'lower_mm':a,'upper_mm':upper if upper is not None else '',
             'qp_count':int(qcount[b]),'effective_qp_count_weight':neff,
             'integration_volume_mm3':float(vol_m3[b]*1e9),
             'full_spherical_shell_reference_mm3':float(spherical_ref_m3*1e9),
             'integrated_to_full_sphere_ratio':ratio,
             'tet10_with_qp_in_shell':int(elem_count[b]),
             'tet10_with_qp_in_multiple_shells':int(mixed_count[b]),
             'radial_node_span_p10_mm':hs[0], 'radial_node_span_p50_mm':hs[1],
             'radial_node_span_p90_mm':hs[2],
             'corner_longest_edge_p10_mm':he[0],'corner_longest_edge_p50_mm':he[1],
             'corner_longest_edge_p90_mm':he[2],
             'global_mesh_quadrature_volume_mm3':total_vol*1e9,
             'total_tet10':total_tets,'total_qp':total_tets*nq,'negative_pore_distance_qp':n_negative_distance,
             'geometry_center_x_m':center[0],'geometry_center_y_m':center[1],
             'geometry_center_z_m':center[2],'pore_radius_mm':r0_mm})
        for ci,cut in enumerate(CUMULATIVE_CUT_MM):
            ref=(4.*math.pi/3.)*((r0_mm+cut)**3-r0_mm**3)
            cumulative.append({'mesh':mesh_name,'quadrature_order':order,
                'distance_upper_mm':cut,'qp_inside':int(cumul_n[ci]),
                'integration_volume_mm3':float(cumul_vol[ci]*1e9),
                'full_spherical_reference_mm3':ref,
                'integrated_to_full_sphere_ratio':float(cumul_vol[ci]*1e9/ref)})
        print(f'[{mesh_name}] Q{order} {nq} qp/tet; integrated mesh volume {total_vol*1e9:.10g} mm^3; first shell: {qcount[0]} qp, {vol_m3[0]*1e9:.10g} mm^3, {elem_count[0]} Tet10',flush=True)
    return rows,cumulative,{'mesh':mesh_name,'sha256':model_sha,'n_nodes':len(xyz),'tet10':total_tets,'all_element_records':all_elements,'seconds':time.perf_counter()-t0}


def selftest():
    for order in (3,4):
        N,dN,weights=quadrature(order)
        assert len(weights)==order**3
        assert abs(np.sum(weights)-1./6.)<1e-14
        assert np.max(abs(N.sum(axis=1)-1))<1e-14
        assert np.max(abs(dN.sum(axis=1)))<1e-14
        a=np.array([[.001,0.,.031],[.0025,0.,.031],[.001,.001,.031],[.001,0.,.033]])
        P=np.vstack((a,0.5*(a[EDGE_PAIRS[:,0]]+a[EDGE_PAIRS[:,1]])))
        J=np.einsum('qkj,kc->qcj',dN,P,optimize=True)
        det=jacobian_determinant(J)
        expected=abs(np.linalg.det(np.column_stack((a[1]-a[0],a[2]-a[0],a[3]-a[0]))))/6.
        assert np.min(det)>0
        assert abs(np.sum(weights*det)-expected)/expected<2e-12
        # Gmsh tet10 Kronecker interpolation at its 10 reference nodes:
        refcorner=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        refnodes=np.vstack((refcorner,0.5*(refcorner[EDGE_PAIRS[:,0]]+refcorner[EDGE_PAIRS[:,1]])))
        n,_=tet10_shape(refnodes[:,0],refnodes[:,1],refnodes[:,2])
        assert np.max(abs(n-np.eye(10)))<1e-14
        print(f'P10Z_SELFTEST_Q{order}_OK qp={order**3} affine_volume_m3={expected:.16e}')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mesh',action='append',default=[],help='NAME=ABS_PATH.msh (repeat for H4,H4W2)')
    ap.add_argument('--out',type=Path,help='NEW output folder')
    ap.add_argument('--orders',nargs='+',type=int,default=[3,4],choices=[3,4],help='3=actual P10Y; 4=diagnostic integration')
    ap.add_argument('--center',nargs=3,type=float,default=(0.,0.,.03),metavar=('X','Y','Z'))
    ap.add_argument('--radius-mm',type=float,default=1.)
    ap.add_argument('--chunk-elements',type=int,default=300)
    ap.add_argument('--selftest',action='store_true')
    opts=ap.parse_args()
    if opts.selftest:
        selftest()
        if not opts.mesh:return
    if not opts.mesh or not opts.out:
        ap.error('--mesh NAME=FILE.msh and --out NEW_DIR required, except --selftest')
    if opts.out.exists():
        ap.error(f'Output folder already exists (do not overwrite evidence): {opts.out}')
    if opts.chunk_elements<1:ap.error('--chunk-elements must be >=1')
    if opts.radius_mm<=0:ap.error('--radius-mm must be positive')
    names=[];paths=[]
    for item in opts.mesh:
        if '=' not in item:ap.error('--mesh must use NAME=PATH')
        name,fn=item.split('=',1)
        if not name or name in names:ap.error('Missing or duplicate mesh name')
        p=Path(fn)
        if not p.is_file():ap.error(f'Mesh file not found: {p}')
        names.append(name);paths.append(p)
    rows=[];cumulative=[];meta=[]
    for name,path in zip(names,paths):
        this,cumul,info=run_one(name,path,sorted(set(opts.orders)),opts.out,opts.center,opts.radius_mm,opts.chunk_elements)
        rows.extend(this);cumulative.extend(cumul);meta.append(info)
    opts.out.mkdir(parents=True,exist_ok=False)
    path=opts.out/'P10Z_MESH_QP_SHELL_METRICS.csv'
    with open(path,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
    cumul_file=opts.out/'P10Z_RADIAL_CUMULATIVE.csv'
    with open(cumul_file,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(cumulative[0]))
        w.writeheader();w.writerows(cumulative)
    detail=opts.out/'P10Z_MESH_AUDIT_LOG.txt'
    with open(detail,'w',encoding='utf-8') as f:
        f.write('P10Z geometry-only mesh audit; NOT FEM verification or shape-derivative convergence.\n')
        f.write('Q3 is the 27-point rule used by P10Y volume_q(3); Q4 is a 64-point geometric check.\n')
        f.write('Full-sphere volume reference valid only where a whole shell is within the solid domain.\n')
        f.write('N_eff is weight concentration, NOT independent sampling size.\n')
        f.write('Radial node span is a nodal proxy, not exact curved-element radial thickness.\n')
        f.write(f'center_m={opts.center} radius_mm={opts.radius_mm} edges_mm={EDGES_MM}\n')
        f.write(f'orders={opts.orders} chunk_elements={opts.chunk_elements}\n')
        for info in meta:f.write(f'{info}\n')
        for name in names:
            a=[r for r in rows if r['mesh']==name]
            for b in (0,1,2,3):
                q3=next((x for x in a if x['quadrature_order']==3 and x['shell']==b),None)
                q4=next((x for x in a if x['quadrature_order']==4 and x['shell']==b),None)
                if q3 and q4:
                    v3=q3['integration_volume_mm3'];v4=q4['integration_volume_mm3']
                    f.write(f'{name} shell={b} Q3_volume_mm3={v3:.16g} Q4_volume_mm3={v4:.16g} Q4_vs_Q3_rel={(v4-v3)/v4:.9g}\n')
    print(f'P10Z_MESH_SHELL_AUDIT_OK csv={path} cumulative={cumul_file} log={detail}',flush=True)

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,AssertionError) as e:
        raise SystemExit(f'P10Z_AUDIT_FAILED: {e}') from e
