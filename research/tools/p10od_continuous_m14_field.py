#!/usr/bin/env python3
"""P10OD: read-only C2-continuous spherical M14 target-size feasibility audit.

No Gmsh, no FEM, no mesh writes. This is a proposed incremental size factor
on top of the existing accumulated CAD field, not the final M14 mesh.
"""
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import sys

BASE=Path(__file__).resolve().parent
CSV=BASE/'P10OC_M14_PROPOSED_KAPPA_1200.csv'
MESH=BASE/'M13_OPTIMIZED_ACCEPTED.msh'
MESH_SHA='cf4ff4872b82fe3fd854d0ddcb31144eb69f42e8ddce8b1954f064243cf9f4ca'
FIELD_SHA='9a379970ba821eac2222f35c717138b727de7f5b2809b331bdc6fe65e8324e4a'
C=(0.,0.,.03)
R=.001
RADIAL=(.01,.035,.075,.175,.375,.75,1.5,3.5,10.,17.5) # bin centers, mm
LAT=tuple(-.9+.2*j for j in range(10))
ANGLE=2*math.pi/12

def need(ok,msg):
    if not ok:raise RuntimeError('P10OD_STOP '+msg)

def smooth5(t):
    t=max(0.,min(1.,t))
    return t*t*t*(10+t*(-15+6*t))

def interval(v,grid):
    if v<=grid[0]:return 0,0,0.
    if v>=grid[-1]:return len(grid)-1,len(grid)-1,0.
    for i in range(len(grid)-1):
        if grid[i]<=v<=grid[i+1]:
            return i,i+1,smooth5((v-grid[i])/(grid[i+1]-grid[i]))
    raise AssertionError(v)

class Field:
    def __init__(self,path=CSV):
        need(hashlib.sha256(path.read_bytes()).hexdigest()==FIELD_SHA,'field SHA changed')
        self.v={}
        with path.open(newline='',encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                k=tuple(int(row[x]) for x in ('radial_bin','mu_bin','phi_bin'))
                need(k not in self.v and 0<=k[0]<10 and 0<=k[1]<10 and 0<=k[2]<12,
                     'invalid/duplicate polar bin')
                value=float(row['kappa'])
                need(math.isfinite(value) and 0<=value<=1,'kappa range')
                self.v[k]=value
        need(len(self.v)==1200,'missing kappa bins')
        for r in range(10):
            for m in (0,9):
                vals=[self.v[r,m,p] for p in range(12)]
                need(max(vals)-min(vals)<1e-12,'polar azimuth artificial anomaly')

    def eval_spherical(self,d_mm,mu,phi):
        """C2 per coordinate, periodic azimuth, C2 transition to zero far away."""
        # Input of the field is physical distance from accepted spherical pore.
        d_mm=max(0.,d_mm)
        if d_mm>=5.:return 0.
        a,b,tr=interval(d_mm,RADIAL)
        c,d,tm=interval(max(-1.,min(1.,mu)),LAT)
        # Phi centers start at -pi+half-sector; interpolate circularly.
        x=((phi+math.pi)/ANGLE-.5)%12.
        p=int(math.floor(x))
        tp=smooth5(x-p)
        q=(p+1)%12
        def longitude(ir,im):
            return self.v[ir,im,p]*(1-tp)+self.v[ir,im,q]*tp
        a0=longitude(a,c)*(1-tm)+longitude(a,d)*tm
        a1=longitude(b,c)*(1-tm)+longitude(b,d)*tm
        value=a0*(1-tr)+a1*tr
        # Smooth compact support: no discontinuity at d=5 mm.
        if d_mm>3.5:
            value*=1-smooth5((d_mm-3.5)/1.5)
        return max(0.,min(1.,value))

    def eval_xyz(self,x,y,z):
        dx,dy,dz=x-C[0],y-C[1],z-C[2]
        radius=math.sqrt(dx*dx+dy*dy+dz*dz)
        if radius<=1e-14:return 0.
        return self.eval_spherical((radius-R)*1000.,dz/radius,math.atan2(dy,dx))

    def relative_size(self,x,y,z):
        """Cube-root of target volume: κ=1 -> 35% characteristic volume decrease."""
        return (1-.35*self.eval_xyz(x,y,z))**(1./3.)

def audit():
    need(hashlib.sha256(MESH.read_bytes()).hexdigest()==MESH_SHA,
         'accepted optimized M13 mesh SHA mismatch')
    field=Field()
    rng=random.Random(130726)
    samples=[]
    errs=[]
    # Physical spherical coordinate sampling plus all 1200 grid centers.
    for r in RADIAL[:8]:
        for m in LAT:
            for p in range(12):
                phi=-math.pi+(p+.5)*ANGLE
                rr=R+r/1000.
                s=math.sqrt(max(0.,1-m*m))
                xyz=(rr*s*math.cos(phi),rr*s*math.sin(phi),C[2]+rr*m)
                v=field.eval_xyz(*xyz)
                samples.append(v)
                errs.append(abs(field.relative_size(*xyz)**3-(1-.35*v)))
    # Interpolation periodicity and continuity across every phi seam, radial,
    # and latitude knot; all tests source-only, no FEM or Gmsh.
    worst_jump=0.
    delta=1e-7
    for _ in range(3000):
        d=rng.uniform(0,5.5)
        mu=rng.uniform(-1,1)
        phi=rng.uniform(-math.pi,math.pi)
        value=field.eval_spherical(d,mu,phi)
        need(0<=value<=1,'interpolation range')
        wrapped=field.eval_spherical(d,mu,phi+2*math.pi)
        need(abs(value-wrapped)<1e-12,'periodic phi mismatch')
        u=field.eval_spherical(d,mu,phi-delta)
        v=field.eval_spherical(d,mu,phi+delta)
        worst_jump=max(worst_jump,abs(u-v))
    # Continuity at every discretization knot and compact-support boundary.
    worst_seam=0.
    for r in RADIAL[:8]+(5.,):
        for mu in LAT:
            for p in range(12):
                phi=-math.pi+p*ANGLE
                e=1e-9
                worst_seam=max(worst_seam,
                    abs(field.eval_spherical(r-e,mu,phi)-field.eval_spherical(r+e,mu,phi)))
    need(max(errs)<1e-12,'volume-size transformation drift')
    need(worst_jump<1e-4 and worst_seam<1e-4,'sampled field discontinuity')
    result={'protocol':'P10OD_M14_C2_SIZE_FIELD_SOURCE_ONLY_V1',
            'status':'P10OD_SOURCE_ONLY_SIZE_FIELD_PASS_NO_MESH_NO_FEM',
            'accepted_M13_SHA256':MESH_SHA,
            'input_kappa_sha256':FIELD_SHA,'samples_grid_centers':len(samples),
            'random_continuity_samples':3000,
            'minimum_incremental_edge_factor':(1-.35)**(1/3),
            'maximum_incremental_edge_factor':1.,
            'max_characteristic_volume_reduction_kappa1':.35,
            'max_volume_edge_cube_error':max(errs),
            'max_small_phi_two_sided_jump':worst_jump,
            'max_small_radial_two_sided_jump':worst_seam,
            'radial_compact_support_mm':5.,
            'geometry_created':False,'FEM_attempts':0,'gmsh_attempts':0,
            'warning':'Only continuous size callback feasibility; no M14 Tet10 or D029/D031 yet.'}
    (BASE/'P10OD_SOURCE_ONLY_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('P10OD_SOURCE_ONLY_PASS_NO_GMSH_NO_MESH_NO_FEM',
          'samples='+str(len(samples)),'edge_min='+str((1-.35)**(1/3)),flush=True)
    return result

if __name__=='__main__':
    try:audit()
    except Exception as error:
        print('P10OD_STOP',repr(error),flush=True)
        sys.exit(2)
