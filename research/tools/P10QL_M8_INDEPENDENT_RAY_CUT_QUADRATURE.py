#!/usr/bin/env python3
"""P10QL genuine M8 independent cut integration by three-axis ray slicing.

For a curved P2 Tet10, the physical boundary pullbacks are P4/P2.
On each ray: compute all actual polynomial interface intersections directly
with numpy.roots, then integrate the actual cubic det(J)*g_h by its exact
antiderivative. Only the two-dimensional transverse integral uses n*n
Gauss-Legendre nodes. No Algoim quadrature, no CAD/Gmsh/FEM/mesh mutation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import time

import numpy as np

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8
import P10QI_M8_REFERENCE_GRADIENT_POLYNOMIAL_PREFLIGHT as qi

CENTRE=np.array([0.,0.,.03]); MM=1000.
RADIAL=(0.,.02,.05,.1,.25,.5,1.,2.,5.,15.)
EXPS=np.array(qi.MONOMIALS)
MOMENTS=np.array([qi.exact_monomial_integral(e) for e in qi.MONOMIALS])
GRID=np.array([[i/3,j/3,k/3] for i in range(4)
               for j in range(4-i) for k in range(4-i-j)])
MONO_MATRIX=qi.mono_matrix(GRID)


def trim_polynomial(p):
    # Relative coefficient threshold is only for irrelevant leading near-zero
    # terms; a genuine quartic is preserved by retaining its finite tail.
    a=np.asarray(p,dtype=float)
    if not np.all(np.isfinite(a)):raise ValueError('P10QL_INVALID_POLYNOMIAL')
    scale=max(1.,float(np.max(abs(a))))
    while len(a)>1 and abs(a[-1])<5e-15*scale:
        a=a[:-1]
    return a


def roots_in_segment(p):
    coeff=trim_polynomial(p)
    if len(coeff)<2:return []
    roots=np.polynomial.polynomial.polyroots(coeff)
    accepted=[]
    for r in roots:
        if abs(r.imag)<2e-8 and -1e-11<r.real<1+1e-11:
            val=max(0.,min(1.,float(r.real)))
            if 2e-12<val<1-2e-12:accepted.append(val)
    out=[]
    for v in sorted(accepted):
        if not out or v-out[-1]>2e-9:out.append(v)
    return out


class RayChild:
    def __init__(self,term):
        self.term=term
        self.nodes=np.asarray(term['nodes'],dtype=float)
        self.field=np.asarray(term['field'],dtype=float)
        self.status=tuple(term['status'])
        self.active=[i for i,v in enumerate(self.status) if v==0]
        self.sector=(int(term['radial_bin']),int(term['mu_bin']),int(term['phi_bin']))
        if len(self.active)<1 or len(self.active)>2 or any(v==-1 for v in self.status):
            raise ValueError('P10QL_REQUIRE_ONE_OR_TWO_ACTUAL_BOUNDARIES')
        polyn=[];volume=[]
        for p in GRID:
            _,g,d,_=qi.mapped_and_numerator(self.nodes,self.field,p)
            polyn.append(g);volume.append(d)
        self.cubic=np.linalg.solve(MONO_MATRIX,np.asarray(polyn))
        self.det=np.linalg.solve(MONO_MATRIX,np.asarray(volume))
        exg=float(self.cubic@MOMENTS)
        exv=float(self.det@MOMENTS)
        if abs(exg-term['exact_full_gradient_m3'])>1e-11*abs(exg) or \
           abs(exv-term['exact_full_volume_m3'])>1e-11*abs(exv):
            raise ValueError('P10QL_EXACT_CUBIC_FULL_MOMENT_WRONG')
        self.exact_full_gradient=exg
        self.exact_full_volume=exv

    def physical_poly(self, xyz):
        # xyz[t=0], xyz[t=1/2], xyz[t=1] -> physical P2 in t.
        a=(xyz-CENTRE)*MM
        r0=a[0];r1=a[2]
        r2=2*(a[2]-2*a[1]+a[0])
        rlin=a[2]-a[0]-r2
        return np.array([r0,rlin,r2]).T

    def constraint(self,phys,which):
        x,y,z=phys
        rr=np.polynomial.polynomial.polymul(x,x)
        rr=np.polynomial.polynomial.polyadd(rr,np.polynomial.polynomial.polymul(y,y))
        rr=np.polynomial.polynomial.polyadd(rr,np.polynomial.polynomial.polymul(z,z))
        rb,mb,pb=self.sector
        if which==0:return np.polynomial.polynomial.polysub([((1+RADIAL[rb])**2)],rr)
        if which==1:return np.polynomial.polynomial.polysub(rr,[((1+RADIAL[rb+1])**2)])
        if which==2:return (1 if mb!=9 else -1)*z
        if which==3:
            xy=np.polynomial.polynomial.polyadd(
                np.polynomial.polynomial.polymul(x,x),
                np.polynomial.polynomial.polymul(y,y))
            return np.polynomial.polynomial.polysub(.64*xy,.36*np.polynomial.polynomial.polymul(z,z))
        angle=-math.pi+math.pi*pb/6
        if which==5:angle+=math.pi/6
        az=np.polynomial.polynomial.polyadd(-math.sin(angle)*x,math.cos(angle)*y)
        return -az if which==4 else az

    def moment_on_ray(self,axis,s,t,cut=True):
        others=[i for i in range(3) if i!=axis]
        fixed=[s,(1-s)*t]
        wmax=(1-s)*(1-t)
        if wmax<=0:return 0.,0.,0
        refs=np.zeros((3,3),dtype=float)
        refs[:,others[0]]=fixed[0]
        refs[:,others[1]]=fixed[1]
        refs[:,axis]=[0.,.5*wmax,wmax]
        xyz=qi.shape_at(refs)@self.nodes
        phys=self.physical_poly(xyz)
        constraints=[self.constraint(phys,j) for j in self.active] if cut else []
        roots=[0.,1.]
        for poly in constraints:roots.extend(roots_in_segment(poly))
        roots=sorted(set(roots))
        powers=np.array([s**i for i in range(4)])
        otherpower=np.array([fixed[1]**i for i in range(4)])
        grad_coeff=np.zeros(4);vol_coeff=np.zeros(4)
        for k,exp in enumerate(EXPS):
            n=exp[axis];pref=powers[exp[others[0]]]*otherpower[exp[others[1]]]*wmax**n
            grad_coeff[n]+=self.cubic[k]*pref
            vol_coeff[n]+=self.det[k]*pref
        ans_g=0.;ans_v=0.;accepted=0
        for lo,hi in zip(roots,roots[1:]):
            if hi-lo<2e-12:continue
            mid=(lo+hi)/2
            if constraints and any(np.polynomial.polynomial.polyval(mid,p)>0 for p in constraints):
                continue
            accepted+=1
            anti=np.array([(hi**(i+1)-lo**(i+1))/(i+1) for i in range(4)])
            ans_g+=float(grad_coeff@anti)
            ans_v+=float(vol_coeff@anti)
        factor=(1-s)*wmax
        return factor*ans_g,factor*ans_v,accepted

    def integrate(self,axis,n,cut=True):
        if axis not in (0,1,2) or not(4<=n<=512):
            raise ValueError('P10QL_AXIS_OR_TRANSVERSE_ORDER_OUTSIDE_GUARD')
        nodes,weights=np.polynomial.legendre.leggauss(n)
        nodes=(nodes+1)*.5;weights=weights*.5
        g=0.;v=0.;accepted=0
        for s,sw in zip(nodes,weights):
            for t,tw in zip(nodes,weights):
                rg,rv,ac=self.moment_on_ray(axis,float(s),float(t),cut=cut)
                g+=sw*tw*rg;v+=sw*tw*rv;accepted+=ac
        return {'cut_gradient_m3':g,'cut_volume_m3':v,
                'transverse_Gauss_points':n*n,'accepted_ray_segments':accepted}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--child-report',type=Path,required=True)
    p.add_argument('--algoim-report',type=Path,required=True)
    p.add_argument('--indices',type=int,nargs='+',required=True)
    p.add_argument('--axes',type=int,nargs='+',default=[0,1,2])
    p.add_argument('--orders',type=int,nargs='+',default=[16,32,64,128])
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    mesh_sha=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    rep=json.loads(a.child_report.read_text())
    gl=json.loads(a.algoim_report.read_text())
    if mesh_sha!=m8.PINNED_M8_SHA256 or rep['mesh_sha256']!=mesh_sha or \
       gl['mesh_sha256']!=mesh_sha or gl['quadrature_strategy']!='gl':
        raise ValueError('P10QL_WRONG_M8_OR_UNCHECKED_ALGOIM')
    level=rep.get('min_h_one',0)
    match=[v for v in gl['partitions'] if v['min_h_one']==level]
    if len(match)!=1:raise ValueError('P10QL_NO_MATCHING_GL_H_LEVEL')
    gldata=match[0]['terminals'];terminals=rep['terminals']
    if len(gldata)!=len(terminals):raise ValueError('P10QL_SOURCE_AND_ALGOIM_NUMBER_MISMATCH')
    if not a.indices or len(set(a.indices))!=len(a.indices) or \
       any(x<0 or x>=len(terminals) for x in a.indices):
        raise ValueError('P10QL_CELL_INDICES_INVALID')
    if sorted(set(a.axes))!=sorted(a.axes) or any(ax not in (0,1,2) for ax in a.axes) or \
       len(set(a.orders))!=len(a.orders) or sorted(a.orders)!=a.orders or \
       any(x<4 or x>512 for x in a.orders):
        raise ValueError('P10QL_AXIS_OR_ORDER_INVALID')
    results=[]
    for i in a.indices:
        term=terminals[i];ga=gldata[i]
        if 'q' not in ga or term['group'] not in ('one','multi'):
            raise ValueError('P10QL_NON_CUT_SENT_TO_INDEPENDENT_INTEGRATOR')
        c=RayChild(term)
        info={'index':i,'group':term['group'],'h_depth':term['h_depth'],
              'active_boundaries':c.active,'exact_full_gradient_m3':c.exact_full_gradient,
              'exact_full_volume_m3':c.exact_full_volume,
              'algoim_gl_q8_cut_gradient_m3':ga['q']['8']['cut_gradient_m3'],
              'algoim_gl_q8_cut_volume_m3':ga['q']['8']['cut_volume_m3'],
              'ray_axes':{}}
        for axis in a.axes:
            rec={}
            full=c.integrate(axis,8,cut=False)
            fullg=abs(full['cut_gradient_m3']-c.exact_full_gradient)/max(abs(c.exact_full_gradient),1e-25)
            fullv=abs(full['cut_volume_m3']-c.exact_full_volume)/c.exact_full_volume
            if max(fullg,fullv)>1e-10:
                raise ValueError('P10QL_INDEPENDENT_RAY_FULL_ANALYTIC_MOMENT_FAILED')
            info.setdefault('axis_full_analytic_relative',{})[str(axis)]={'gradient':fullg,'volume':fullv}
            for n in a.orders:
                start=time.monotonic();value=c.integrate(axis,n)
                value['elapsed_s']=time.monotonic()-start
                if not math.isfinite(value['cut_gradient_m3']) or \
                   value['cut_volume_m3']<0 or value['cut_volume_m3']>1.00000001*c.exact_full_volume:
                    raise ValueError('P10QL_CUT_OUTSIDE_FULL_OR_NOT_FINITE')
                rec[str(n)]=value
            info['ray_axes'][str(axis)]=rec
            last=rec[str(a.orders[-1])]['cut_gradient_m3'];prev=rec[str(a.orders[-2])]['cut_gradient_m3']
            print(f'P10QL_RAY cell={i} axis={axis} n={a.orders[-1]} '
                  f'gradient={last:.16g} delta={last-prev:.3g} '
                  f'vs_algoim={last-ga["q"]["8"]["cut_gradient_m3"]:.3g}',flush=True)
        results.append(info)
    output={'stage':'P10QL','status':'INDEPENDENT_RAY_SLICING_DIAGNOSTIC_NOT_PHYSICS_CERTIFICATION',
            'mesh_sha256':mesh_sha,'child_report':a.child_report.name,
            'algoim_gl_report':a.algoim_report.name,
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'method':'three-axis P4/P2 direct polynomial roots + exact cubic 1D primitive + '
                     'two-dimensional tensor Gauss-Legendre',
            'n_values':a.orders,'selected_axes':a.axes,
            'CAD_or_Gmsh_or_FEM_executed':False,'physical_4D_FEM_approved':False,
            'results':results}
    a.output.write_text(json.dumps(output,indent=2)+'\n')
    print('P10QL_INDEPENDENT_RAY_CUT_QUADRATURE_COMPLETE_PHYSICS_NOT_CERTIFIED',flush=True)


if __name__=='__main__':main()
