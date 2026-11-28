#!/usr/bin/env python3
"""P10HK source-only scalar-call Gmsh size-callback benchmark on real 4D κ.

No import of gmsh, no mesh, no FEM; tests callback-compatible point-by-point
normalized Wendland C2 evaluation and nominal size ratio 0.83 <= V/V0 <= 1.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'scripts'))
import p10hc_continuous_kappa_geo as field


class DirectKappa:
    """One-time precomputation; exact same kernel and EPS as frozen P10HC."""
    def __init__(self,source,values,den):
        scale=np.array([field.R_SCALE,field.A_SCALE,field.A_SCALE,field.A_SCALE])
        scaled=source/scale
        order=np.argsort(scaled[:,0],kind='stable')
        self.rad=scaled[order,0]
        self.unit=scaled[order,1:]
        self.value=np.asarray(values)[order]
        self.den=float(den)

    def kappa(self,x,y,z):
        dx=float(x)-field.C[0]
        dy=float(y)-field.C[1]
        dz=float(z)-field.C[2]
        r=float(np.sqrt(dx*dx+dy*dy+dz*dz))
        if not np.isfinite(r) or r<field.PORE_R-1e-12:
            raise RuntimeError('P10HK_PHYSICAL_STOP: callback point inside spherical pore')
        radial=np.log1p(max(r-field.PORE_R,0)*1000/.05)/field.R_SCALE
        lo=np.searchsorted(self.rad,radial-1,side='right')
        hi=np.searchsorted(self.rad,radial+1,side='left')
        if lo==hi:return 0.
        directions=np.array([dx,dy,dz])/(r*field.A_SCALE)
        d2=(self.rad[lo:hi]-radial)**2+np.einsum(
            'ij,ij->i',self.unit[lo:hi]-directions,self.unit[lo:hi]-directions)
        within=d2<1
        if not np.any(within):return 0.
        q=np.sqrt(np.maximum(d2[within],0))
        w=(1-q)**4*(4*q+1)
        val=float(np.dot(w,self.value[lo:hi][within])/(w.sum()+field.EPS)/self.den)
        return min(1.,max(0.,val))

    def size(self,dim,tag,x,y,z,lc):
        """Gmsh 4.15.2 setSizeCallback(dim,tag,x,y,z,lc) signature.

        lc must be the same base size from the pinned Field[7]; this is not
        an empirical proof that Gmsh actually passes Field[7] as lc.
        """
        if not np.isfinite(lc) or lc<=0:
            raise RuntimeError('P10HK_SIZE_STOP: non-positive base lc')
        return lc*(1-field.ALPHA*self.kappa(x,y,z))**(1/3)


def main():
    p=ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124'
    if not (p/'P10HA_KAPPA_QA.json').is_file():p=HERE
    src,v25,_,_,_,qa=field.load_centers(p/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',
                                      p/'P10HA_KAPPA_QA.json')
    den=qa['mechanical_only_25_36_shared_smoothing_denominator']
    direct=DirectKappa(src,v25,den)
    rng=np.random.default_rng(20261124)
    n=20000
    mu=rng.uniform(-1,1,n)
    phi=rng.uniform(-np.pi,np.pi,n)
    a=np.sqrt(1-mu*mu)
    r=field.PORE_R+rng.choice(np.array([0.,.00002,.0001,.0005,.002,.005,.015,.025]),size=n)
    xyz=np.column_stack((r*a*np.cos(phi),r*a*np.sin(phi),field.C[2]+r*mu))
    begin=time.perf_counter()
    reference=field.rbf_at_points(src,v25,field.physical_query(xyz),den)
    tref=time.perf_counter()-begin
    begin=time.perf_counter()
    observed=np.array([direct.kappa(*point) for point in xyz])
    tsingle=time.perf_counter()-begin
    diff=np.abs(observed-reference)
    if np.max(diff)>1e-12:raise RuntimeError('P10HK_STOP: callback differs from frozen continuous source')
    # Test Gmsh-compatible callable with simulated lc; we do NOT claim to
    # have tested its actual background-field lc behavior in native Gmsh.
    begin=time.perf_counter()
    sizes=np.array([direct.size(3,0,*point,.0002) for point in xyz])
    tcallback=time.perf_counter()-begin
    ratio=(sizes/.0002)**3
    if np.min(ratio)<.83-1e-12 or np.max(ratio)>1+1e-12:
        raise RuntimeError('P10HK_STOP: nominal volume ratio outside 0.83..1')
    out={'protocol':'P10HK_R1_DIRECT_CONTINUOUS_MECHANICAL_KAPPA_SIZE_CALLBACK_SOURCE_ONLY',
         'status':'PASS_NUMERIC_PARITY_NO_NATIVE_GMSH_NO_MESH_NO_FEM',
         'samples':n,'p10ha_P10HB_policy':'mechanical_only_4D_M0_M1',
         'max_abs_vs_frozen_numpy_source':float(np.max(diff)),
         'reference_vectorized_wall_s':round(tref,4),
         'single_point_callback_eval_wall_s':round(tsingle,4),
         'single_point_callback_eval_us_per_query':round(tsingle/n*1e6,3),
         'simulated_size_callback_wall_s':round(tcallback,4),
         'simulated_size_callback_us_per_query':round(tcallback/n*1e6,3),
         'nominal_characteristic_volume_ratio_min_max':[float(ratio.min()),float(ratio.max())],
         'gmsh_setSizeCallback_signature_tested_in_python':True,
         'native_gmsh_callback_or_baseline_field7_verified':False,
         'D025_curved_tet10_real_volume_certified':False,
         'next':'guarded native Gmsh setSizeCallback lc / Field[7] preflight, no mesh',
         'native_1d_2d_3d_FEM_attempts':0}
    print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
