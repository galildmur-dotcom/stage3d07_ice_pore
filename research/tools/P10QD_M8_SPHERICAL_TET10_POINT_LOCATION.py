#!/usr/bin/env python3
"""P10QD: actual curved-M8 point-location for spherical cut quadrature.

READ ONLY. A Bezier-convex-hull uniform broad phase has no false negatives:
all Tet10 whose true images may intersect a point are candidates. The narrow
phase inverts the *quadratic* 10-node isoparametric map; it does not replace
the actual curved mesh by straight Tet4 or by the ideal spherical surface.

Only the specified inner radial interval (<=1.50 mm) is indexed. No FEM,
remeshing, geometry mutation, or physics are performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as base


def shape_batch(uvw: np.ndarray):
    """Tet10 canonical basis and its 3 reference derivatives in a batch."""
    l = np.column_stack((1.-uvw.sum(axis=1), uvw))
    dl = np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    n = np.empty((len(uvw),10), dtype=float)
    g = np.empty((len(uvw),10,3), dtype=float)
    n[:,:4] = l*(2*l-1)
    g[:,:4] = (4*l-1)[:,:,None]*dl[None,:,:]
    for k,(a,b) in enumerate(base.EDGE,start=4):
        n[:,k] = 4*l[:,a]*l[:,b]
        g[:,k,:] = 4*(l[:,a,None]*dl[b]+l[:,b,None]*dl[a])
    return n,g


def map_batch(phys: np.ndarray, uvw: np.ndarray):
    n,g=shape_batch(uvw)
    pos=np.einsum('nk,nkj->nj',n,phys)
    jac=np.einsum('nki,nkj->nij',phys,g)
    return pos,jac


class CurvedTet10Locator:
    def __init__(self, X: np.ndarray, *, halfspan=.0016, pitch=.00015):
        self.X=X
        self.halfspan=float(halfspan)
        self.pitch=float(pitch)
        self.ncells=int(math.ceil(2*halfspan/pitch))
        self.low=-self.halfspan
        ctrl=X.copy()
        for k,(a,b) in enumerate(base.EDGE,start=4):
            ctrl[:,k]=2*X[:,k]-.5*(X[:,a]+X[:,b])
        self.lo=ctrl.min(axis=1)-base.CENTER
        self.hi=ctrl.max(axis=1)-base.CENTER
        in_cube=((self.hi>=-halfspan)&(self.lo<=halfspan)).all(axis=1)
        self.active=np.flatnonzero(in_cube)
        self.cells={}
        for k in self.active:
            a=np.clip(np.floor((self.lo[k]-self.low)/pitch).astype(int),0,self.ncells-1)
            b=np.clip(np.floor((self.hi[k]-self.low)/pitch).astype(int),0,self.ncells-1)
            for i in range(a[0],b[0]+1):
                for j in range(a[1],b[1]+1):
                    for h in range(a[2],b[2]+1):
                        key=(i*self.ncells+j)*self.ncells+h
                        self.cells.setdefault(key,[]).append(int(k))
        self.cells={key:np.array(v,dtype=np.int32) for key,v in self.cells.items()}
        A=np.swapaxes(X[:,1:4,:]-X[:,0:1,:],1,2)
        d=np.linalg.det(A)
        if np.any(np.abs(d[self.active])<1e-21):
            raise ValueError('Nearly singular linear-seed Tet10 Jacobian')
        self.inv_affine=np.empty_like(A)
        self.inv_affine[self.active]=np.linalg.inv(A[self.active])
        self.stats={'query_points':0,'points_in_bbox':0,'newton_candidate_attempts':0,
                    'newton_failed_candidates':0,'multiple_hits':0,
                    'max_residual_inside_m':0.,'max_reference_error_inside':0.}

    def locate(self, point: np.ndarray):
        """Return (element_index, uvw) or (None,None), exact-bbox candidates."""
        self.stats['query_points']+=1
        p=point-base.CENTER
        idx=np.floor((p-self.low)/self.pitch).astype(int)
        if np.any(idx<0) or np.any(idx>=self.ncells):
            return None,None
        key=(int(idx[0])*self.ncells+int(idx[1]))*self.ncells+int(idx[2])
        candidates=self.cells.get(key)
        if candidates is None:
            return None,None
        keep=(np.all(p>=self.lo[candidates]-2e-14,axis=1)
              &np.all(p<=self.hi[candidates]+2e-14,axis=1))
        ids=candidates[keep]
        self.stats['points_in_bbox']+=int(len(ids)>0)
        if len(ids)==0:
            return None,None
        coords=self.X[ids]
        delta=point[None,:]-coords[:,0,:]
        uvw=np.einsum('nij,nj->ni',self.inv_affine[ids],delta)
        healthy=np.ones(len(ids),dtype=bool)
        self.stats['newton_candidate_attempts']+=len(ids)
        for _ in range(16):
            pos,jac=map_batch(coords,uvw)
            resid=pos-point[None,:]
            try:
                # NumPy >=2 does not treat an (n,3) RHS as a batch of vectors;
                # explicit (n,3,1) is unambiguous for all supported versions.
                step=np.linalg.solve(jac,resid[:,:,None])[:,:,0]
            except np.linalg.LinAlgError:
                self.stats['newton_failed_candidates']+=len(ids)
                return None,None
            healthy &= np.isfinite(step).all(axis=1)
            # Far-away candidate inversions may have extraneous nonlinear
            # roots; bounded trust steps prevent catastrophic escape.
            norms=np.linalg.norm(step,axis=1)
            factor=np.minimum(1.,1.5/np.maximum(norms,1e-300))
            uvw-=step*factor[:,None]
            if np.max(np.where(healthy,np.linalg.norm(step*factor[:,None],axis=1),0.))<3e-11:
                break
        pos,jac=map_batch(coords,uvw)
        residual=np.linalg.norm(pos-point[None,:],axis=1)
        bary=np.column_stack((1.-uvw.sum(axis=1),uvw))
        inside=healthy&(residual<=2e-11)&(bary.min(axis=1)>=-1e-9)&(bary.max(axis=1)<=1+1e-9)
        found=np.flatnonzero(inside)
        self.stats['newton_failed_candidates']+=int((~healthy).sum())
        if not len(found):
            return None,None
        if len(found)>1:
            self.stats['multiple_hits']+=1
        ix=int(found[np.argmin(ids[found])])
        self.stats['max_residual_inside_m']=max(self.stats['max_residual_inside_m'],float(residual[ix]))
        self.stats['max_reference_error_inside']=max(
            self.stats['max_reference_error_inside'],float(max(0.,-bary[ix].min(),bary[ix].max()-1.)))
        return int(ids[ix]),uvw[ix].copy()


def selftest(locator: CurvedTet10Locator, *, samples=192):
    rng=np.random.default_rng(20261128)
    inside_indices=[]
    for k in locator.active:
        # Choose genuine reference points whose physical image falls within
        # the indexed cube. This tests true inverse Tet10 mapping.
        if len(inside_indices)<samples*4:
            inside_indices.append(int(k))
    chosen=rng.choice(inside_indices,size=samples,replace=True)
    max_local=0.;max_xyz=0.; failures=[]
    for k in chosen:
        bary=rng.dirichlet(np.ones(4)*2.)
        uvw=bary[1:]
        n,_=base.tet10_shape(uvw)
        p=n@locator.X[k]
        if np.any(np.abs(p-base.CENTER)>locator.halfspan-1e-12):
            # Valid sample but outside narrow pilot index; skip explicitly.
            continue
        hit,found=locator.locate(p)
        if hit is None:
            failures.append({'element':int(k),'p':p.tolist()})
            continue
        n2,_=base.tet10_shape(found)
        max_xyz=max(max_xyz,float(np.linalg.norm(n2@locator.X[hit]-p)))
        if hit==k:
            max_local=max(max_local,float(np.max(np.abs(found-uvw))))
    if failures:
        raise ValueError(f'Known-interior point not located: {failures[:2]}')
    return {'attempts':samples,'missed_known_interior':len(failures),
            'max_physical_reprojection_error_m':max_xyz,
            'max_same_element_reference_inverse_error':max_local}


def sphere_points(ir,im,ip,q):
    """Tensor Gauss-Legendre in rho, mu=cos(theta), phi, with r^2 Jacobian."""
    rlo=base.PORE_R+base.RADIAL_LOWER_MM[ir]*.001
    rhi=base.PORE_R+base.RADIAL_LOWER_MM[ir+1]*.001
    mlo=(-1.+.2*im)
    mhi=mlo+.2
    phlo=-math.pi+ip*math.pi/6
    phhi=phlo+math.pi/6
    t,w=np.polynomial.legendre.leggauss(q)
    r=.5*(rlo+rhi)+.5*(rhi-rlo)*t
    wr=.5*(rhi-rlo)*w
    mu=.5*(mlo+mhi)+.5*(mhi-mlo)*t
    wm=.5*(mhi-mlo)*w
    phi=.5*(phlo+phhi)+.5*(phhi-phlo)*t
    wp=.5*(phhi-phlo)*w
    R,M,P=np.meshgrid(r,mu,phi,indexing='ij')
    dV=(wr[:,None,None]*wm[None,:,None]*wp[None,None,:]*R**2)
    x=R*np.sqrt(np.maximum(0.,1-M**2))*np.cos(P)
    y=R*np.sqrt(np.maximum(0.,1-M**2))*np.sin(P)
    z=R*M
    xyz=np.stack((x,y,z+.03),axis=-1).reshape(-1,3)
    return xyz,dV.ravel(),R.ravel(),M.ravel(),P.ravel()


def analytic_linear_moment(ir,im,ip):
    """Integral of (z-0.03)/1.5mm over the exact spherical sector."""
    rlo=base.PORE_R+base.RADIAL_LOWER_MM[ir]*.001
    rhi=base.PORE_R+base.RADIAL_LOWER_MM[ir+1]*.001
    mlo=-1.+.2*im
    mhi=mlo+.2
    return (rhi**4-rlo**4)/4.*(mhi**2-mlo**2)/2.*(math.pi/6)/.0015


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--q',nargs='+',type=int,default=[2,3,4,6,8,12])
    p.add_argument('--pilot-only',action='store_true',help='4 bins instead of 48')
    p.add_argument('--output',type=Path,default=Path('P10QD_M8_SPHERICAL_TET10_ALL48_QA.json'))
    args=p.parse_args()
    sha=hashlib.sha256(args.mesh.read_bytes()).hexdigest()
    if sha!=base.PINNED_M8_SHA256:
        raise SystemExit('P10QD_STOP_UNPINNED_M8')
    baseline=json.loads(args.baseline.read_text())
    if baseline['mesh_sha256']!=sha or baseline['bin_count']!=48:
        raise ValueError('P10QA baseline is absent or incompatible')
    xyz,conn,ids,types,faces=base.parse_msh(args.mesh)
    X=xyz[conn]
    locator=CurvedTet10Locator(X)
    tests=selftest(locator)
    bin_index={(b['radial_bin'],b['mu_bin'],b['phi_bin']):b for b in baseline['bins']}
    cases=[(ir,im,ip) for ir in [0,4] for im in [0,9]
           for ip in ([0] if args.pilot_only else range(12))]
    results=[]
    total_misses=0
    for ir,im,ip in cases:
        b=bin_index[(ir,im,ip)]
        lo=b['depth_records'][-1]['lower_cut_volume_m3']
        hi=b['depth_records'][-1]['upper_cut_volume_m3']
        rlo=base.PORE_R+base.RADIAL_LOWER_MM[ir]*.001
        rhi=base.PORE_R+base.RADIAL_LOWER_MM[ir+1]*.001
        ideal=(rhi**3-rlo**3)/3*.2*math.pi/6
        qs=[]
        for q in args.q:
            pts,w,r,mu,phi=sphere_points(ir,im,ip,q)
            inside=np.zeros(len(pts),dtype=bool)
            f_linear=np.zeros(len(pts),dtype=float)
            f_cubic=np.zeros(len(pts),dtype=float)
            hit_elements=[]
            stats_before=locator.stats.copy()
            for n,pt in enumerate(pts):
                ix,uv=locator.locate(pt)
                inside[n]=(ix is not None)
                if ix is not None:
                    fn,_=base.tet10_shape(uv)
                    z=(X[ix,:,2]-.03)/.0015
                    f_linear[n]=float(fn@z)
                    f_cubic[n]=float(fn@(z**3))
                    hit_elements.append(ix)
            v=float(np.sum(w[inside]))
            total_misses+=int((~inside).sum())
            lin=float(w@f_linear)
            cubic=float(w@f_cubic)
            lin_exact=analytic_linear_moment(ir,im,ip)
            qrow={'q':q,'nodes':len(w),'located':int(inside.sum()),'not_located':int((~inside).sum()),
                  'curved_M8_cut_volume_m3':v,'relative_to_ideal':v/ideal,
                  'FE_nodal_linear_moment_m3':lin,
                  'FE_nodal_linear_vs_exact_rel':abs(lin-lin_exact)/abs(lin_exact),
                  'FE_nodal_cubic_moment_m3':cubic,
                  'distinct_curved_Tet10_evaluated':len(set(hit_elements)),
                  'between_P10QA_certified_brackets':bool(lo-2e-15*ideal<=v<=hi+2e-15*ideal),
                  'bbox_candidate_attempts':locator.stats['newton_candidate_attempts']-stats_before['newton_candidate_attempts']}
            qs.append(qrow)
            if qrow['not_located'] and qrow['q']<=8:
                print(f'P10QD_MESH_EXCLUSION r={ir} mu={im} phi={ip} q={q} '
                      f'n={qrow["not_located"]}',flush=True)
        results.append({'radial_bin':ir,'mu_bin':im,'phi_bin':ip,
                        'ideal_sphere_volume_m3':ideal,'P10QA_lower_m3':lo,
                        'P10QA_upper_m3':hi,
                        'analytic_linear_moment_m3':analytic_linear_moment(ir,im,ip),
                        'q_records':qs})
        print(f'P10QD_BIN_{len(results):02d}/{len(cases)} r={ir} mu={im} phi={ip} '
              f'last_q={qs[-1]["q"]} fraction={qs[-1]["relative_to_ideal"]:.12g} '
              f'nohit={qs[-1]["not_located"]}',flush=True)
    if not all(q['between_P10QA_certified_brackets'] for c in results for q in c['q_records']):
        raise ValueError('Spherical cut quadrature contradicts certified P10QA bounds')
    max_linear_error=max(q['FE_nodal_linear_vs_exact_rel'] for c in results for q in c['q_records'])
    if max_linear_error>1e-8:
        raise ValueError(f'Linear manufactured FE moment inconsistent: {max_linear_error}')
    result={'stage':'P10QD','status':'PASS_SPHERICAL_M8_QUADRATURE_PILOT_WITH_P10QA_BRACKET_CONSISTENCY',
            'mesh_sha256':sha,'mesh_changed':False,'fem_started':False,'gmsh_generated':False,
            'method':'tensor-Gauss r,mu,phi; Bezier AABB grid; curved Tet10 Newton inverse',
            'interpolation_warning':'Point-sampled integration not a rigorous enclosure of the cut; P10QA brackets remain the volume certificates.',
            'max_linear_FE_analytic_relative_error':max_linear_error,
            'excluded_or_unlocated_samples':total_misses,'point_location_selftest':tests,
            'point_location_stats':locator.stats,'indexed_tet10':len(locator.active),
            'grid_occupied_cells':len(locator.cells),'bins':results,'physical_4D_FEM_approved':False}
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('P10QD_SPHERICAL_TET10_CUT_PILOT_AND_P10QA_BRACKET_QA_PASS',flush=True)


if __name__=='__main__':
    main()
