#!/usr/bin/env python3
"""LIT-06: B20 geometry-only audit of existing Gmsh MSH2.2 Tet10/Tri6 meshes.
No FEM, no mesh generation, no changes to repository. Requires numpy.
Port of tetshape, volume_q(3), velocity_at(R) and observation_elements
from Stage3D07; same formulas validated in LIT04B. No FEM solves.
"""
import argparse, csv, hashlib, math, sys, time
from pathlib import Path
import numpy as np

C=np.array([0.,0.,0.03],dtype=np.float64); R=0.001; R6=0.006; CUTOFF=0.005
GAUSS3=((.1127016653792583,5/18),(.5,8/18),(.8872983346207417,5/18))
GAUSS6=((.033765242898424,.085662246189585),(.169395306766868,.180380786524069),(.380690406958402,.233956967286346),(.619309593041598,.233956967286346),(.830604693233132,.180380786524069),(.966234757101576,.085662246189585))
E6=((0,1),(1,2),(2,0)); E10=((0,1),(1,2),(2,0),(0,3),(1,3),(2,3))
LDER_TET=np.array([[-1,-1,-1],[1,0,0],[0,1,0],[0,0,1]],float)
LDER_TRI=np.array([[-1,-1],[1,0],[0,1]],float)
COLS=['label','mesh_file','mesh_sha256','node_count','tet10_count','pore_tri6','b6_selected_tet10','pore_area_Q6_m2','pore_volume_Q6_m3','sampled_max_radial_departure_um','sampled_rms_radial_departure_um','mean_normal_angle_deg','max_normal_angle_deg','max_normal_sample_x_m','max_normal_sample_y_m','max_normal_sample_z_m','pore_area_error_rel','pore_volume_error_rel','b6_Q3_volume_m3','b6_Q3_volume_derivative_m2','b6_Q3_normalized_dV_per_m','b6_volume_error_vs_exact_m3','b6_dV_error_vs_exact_m2','b6_volume_error_vs_surface_surrogate_m3','b6_dV_error_vs_surface_surrogate_m2','surrogate_b6_volume_m3','surrogate_b6_dV_m2','surrogate_b6_normalized_dV_per_m','b6_min_sampled_detJ_m3','b6_nonpositive_sampled_detJ_count','sec_wall']

EXPECTED={
 'H0':'e28d6049afc4b20b474152d315952361b01dce7052f7642d03a20ce8274d41f8',
 'H1':'394ee339073fe6eacfd58c549ad0b0218a9bdadf8f36a2ca435a1ca3fad0598d',
 'H2':'26057402903ebe77af3e7e6b223e2bfaa29aa0cc0c89497e6dcc53817c3c096b',
 'H3':'c210a2306dd5524ae28c50b1961cc1d017fb05c06d55df849fb893451db5010c',
 'H4':'4530988fd07d8268e024a5e738fb921b76374fe97b2f0a480218c9e0964049b9',
 'H4W2':'de96486d592634e08214134d5a32ea4bb375cc4ef351d0ad16da8ea1f2583623',
 'H4W2B20':'3b82dad07b1717d07003fa244c5ddc9a1f1fd8fe05d2523eecc9537af630a8fe',
 'H4W4B2':'3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7',
}

def sha256(p):
 s=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):s.update(b)
 return s.hexdigest()

def read_msh2(p):
 nodes=[]; tets=[]; faces=[]; ids={};
 with open(p,'rt',encoding='utf-8-sig',errors='replace') as f:
  for line in f:
   marker=line.strip()
   if marker=='$MeshFormat':
    ver=f.readline().strip().split()
    if len(ver)<3 or ver[0]!='2.2' or ver[1]!='0':
     raise ValueError('Requires ASCII Gmsh MSH version 2.2 (use gmsh -format msh2)')
   elif marker=='$Nodes':
    n=int(f.readline())
    for i in range(n):
     s=f.readline().split()
     if len(s)!=4:raise ValueError('Malformed node')
     ids[int(s[0])]=i
     nodes.append([float(s[1]),float(s[2]),float(s[3])])
   elif marker=='$Elements':
    n=int(f.readline())
    for _ in range(n):
     s=f.readline().split()
     if len(s)<5:raise ValueError('Malformed element')
     typ=int(s[1]);nt=int(s[2]);ph=int(s[3]) if nt>0 else None
     if typ==11:
      if ph!=1:raise ValueError('Non-ice Tet10 detected')
      v=[ids[int(x)] for x in s[3+nt:]]
      if len(v)!=10:raise ValueError('Malformed Tet10')
      v[8],v[9]=v[9],v[8] # Identical to Stage3D07/tet10_shared.hpp
      tets.append(v)
     elif typ==9 and ph==8:
      v=[ids[int(x)] for x in s[3+nt:]]
      if len(v)!=6:raise ValueError('Malformed pore Tri6')
      faces.append(v)
 if not nodes or not tets or not faces:raise ValueError('Missing Nodes, Tet10 or pore Tri6')
 return np.asarray(nodes,np.float64),np.asarray(tets,np.int32),np.asarray(faces,np.int32)

def tet_quadrature():
 ws=[];ds=[]
 for a,wa in GAUSS3:
  for b,wb in GAUSS3:
   for c,wc in GAUSS3:
    r=a;s=(1-r)*b;t=(1-r)*(1-b)*c
    L=np.array([1-r-s-t,r,s,t]);d=np.empty((10,3),np.float64)
    for i in range(4):d[i]=(4*L[i]-1)*LDER_TET[i]
    for j,(i,k) in enumerate(E10):d[4+j]=4*(L[i]*LDER_TET[k]+L[k]*LDER_TET[i])
    ws.append(wa*wb*wc*(1-r)**2*(1-b));ds.append(d)
 return np.array(ws),np.moveaxis(np.array(ds),0,1) # (27,), (10,27,3)

def tri_quadrature():
 ws=[];Ns=[];Ds=[]
 for a,wa in GAUSS6:
  for b,wb in GAUSS6:
   r=a;s=(1-r)*b
   L=np.array([1-r-s,r,s]);N=np.empty(6);d=np.empty((6,2))
   for i in range(3):
    N[i]=L[i]*(2*L[i]-1);d[i]=(4*L[i]-1)*LDER_TRI[i]
   for j,(i,k) in enumerate(E6):
    N[3+j]=4*L[i]*L[k];d[3+j]=4*(L[i]*LDER_TRI[k]+L[k]*LDER_TRI[i])
   ws.append(wa*wb*(1-r));Ns.append(N);Ds.append(d)
 return np.array(ws),np.array(Ns).T,np.moveaxis(np.array(Ds),0,1) # (36,), (6,36), (6,36,2)

def velocities(points):
 d=points-C;dist=np.linalg.norm(d,axis=1)
 if np.any(dist<=0):raise ValueError('Zero radius mesh node')
 f=np.ones_like(dist)
 mid=(dist>R)&(dist<CUTOFF);t=(dist[mid]-R)/(CUTOFF-R)
 f[mid]=1-t*t*(3-2*t);f[dist>=CUTOFF]=0.
 return d*(f/dist)[:,None]

def pore_metrics(x,f,chunk=1000):
 w,N,d=tri_quadrature();area=0.;vol=0.;radmax=0.;rsum=0.;angle_sum=0.;angle_max=0.;max_normal_point=(float('nan'),)*3
 for i in range(0,len(f),chunk):
  X=x[f[i:i+chunk]]
  P=np.einsum('eij,iq->eqj',X,N,optimize=True)
  D0=np.einsum('eij,iq->eqj',X,d[:,:,0],optimize=True)
  D1=np.einsum('eij,iq->eqj',X,d[:,:,1],optimize=True)
  A=np.cross(D0,D1); aa=np.linalg.norm(A,axis=2)
  if np.any(aa<=0):raise ValueError('Degenerate Tri6 patch')
  radial=P-C;r=np.linalg.norm(radial,axis=2)
  sign=np.where(np.einsum('eqj,eqj->eq',A,radial)>=0,1.,-1.)
  # Outward from cavity, independent of input triangle winding.
  A*=sign[:,:,None];ws=w[None,:]*aa
  normal_cos=np.sum(A*radial,axis=2)/(aa*r)
  angle=np.rad2deg(np.arccos(np.clip(normal_cos,-1,1)))
  departure=np.abs(r-R)
  area+=float(np.sum(ws));vol+=float(np.sum(w[None,:]*np.sum(A*radial,axis=2)/3.))
  radmax=max(radmax,float(np.max(departure)))
  rsum+=float(np.sum(ws*departure**2));angle_sum+=float(np.sum(ws*angle))
  where=np.unravel_index(np.argmax(angle),angle.shape)
  if float(angle[where])>angle_max:
   angle_max=float(angle[where]);max_normal_point=tuple(P[where].tolist())
 return dict(pore_area_Q6_m2=area,pore_volume_Q6_m3=vol,
     sampled_max_radial_departure_um=radmax*1e6,
     sampled_rms_radial_departure_um=(rsum/area)**.5*1e6,
     mean_normal_angle_deg=angle_sum/area,max_normal_angle_deg=angle_max,
     max_normal_sample_x_m=max_normal_point[0],max_normal_sample_y_m=max_normal_point[1],
     max_normal_sample_z_m=max_normal_point[2])

def b6_metrics(x,tets,chunk=1200,velocity_override=None):
 w,D=tet_quadrature(); v=velocities(x) if velocity_override is None else velocity_override
 vtot=dvtot=0.;nselected=0;min_jac=float('inf');nonpos=0
 for begin in range(0,len(tets),chunk):
  ix=tets[begin:begin+chunk]
  corner=x[ix[:,:4]];cent=np.mean(corner,axis=1)
  selected=np.linalg.norm(cent-C,axis=1)<R6
  if not np.any(selected):continue
  ix=ix[selected];nselected+=len(ix);X=x[ix];V=v[ix]
  deriv=[np.einsum('eij,iq->eqj',X,D[:,:,k],optimize=True) for k in range(3)]
  dderiv=[np.einsum('eij,iq->eqj',V,D[:,:,k],optimize=True) for k in range(3)]
  dr,ds,dt=deriv; ddr,dds,ddt=dderiv
  c0=np.cross(ds,dt)
  jac=np.einsum('eqj,eqj->eq',dr,c0)
  djac=np.einsum('eqj,eqj->eq',ddr,c0)+np.einsum('eqj,eqj->eq',dr,np.cross(dds,dt)+np.cross(ds,ddt))
  min_jac=min(min_jac,float(np.min(jac)));nonpos+=int(np.count_nonzero(jac<=0))
  vtot+=float(np.sum(jac*w[None,:]));dvtot+=float(np.sum(djac*w[None,:]))
 if nselected==0:raise ValueError('Empty B6 mask')
 return dict(b6_selected_tet10=nselected,b6_Q3_volume_m3=vtot,b6_Q3_volume_derivative_m2=dvtot,
    b6_Q3_normalized_dV_per_m=dvtot/vtot,b6_min_sampled_detJ_m3=min_jac,
    b6_nonpositive_sampled_detJ_count=nonpos)

def lookup(repo,label):
 names={'H0':['meshes/H0.msh','P10M_MESHES/H0.msh'],
        'H1':['P10M_MESHES/H1.msh','meshes/H1.msh'],
        'H2':['P10M_MESHES/H2.msh','meshes/H2.msh'],
        'H3':['P10M_MESHES/H3.msh','meshes/H3.msh'],
        'H4':['P10M_MESHES/H4.msh','meshes/H4.msh'],
        'H4W2':['P10M_MESHES/H4W2.msh','meshes/H4W2.msh'],
        'H4W2B20':['P10M_MESHES/H4W2B20.msh'],
        'H4W4B2':['P10M_MESHES/H4W4B2.msh'],
        'H4W4B20':['P10M_MESHES/H4W4B20_P10AB.msh','P10M_MESHES/H4W4B20.msh'],
        'H4W5B20':['P10M_MESHES/H4W5B20_P10AE.msh','P10M_MESHES/H4W5B20.msh'],
        'H4W5B2':['P10M_MESHES/H4W5B2_P10AC.msh','P10M_MESHES/H4W5B2.msh']}
 for part in names.get(label,[]):
  p=repo/part
  if p.is_file():return p
 raise FileNotFoundError('Mesh not found for '+label+'; checked: '+', '.join(names.get(label,[])))

def audit(label,mesh,allow_sha_mismatch=False):
 t0=time.perf_counter();digest=sha256(mesh)
 if label in EXPECTED and digest!=EXPECTED[label] and not allow_sha_mismatch:
  raise ValueError('SHA256 mesh mismatch '+label+': got '+digest+' expected '+EXPECTED[label])
 x,tets,faces=read_msh2(mesh)
 print('LOADED',label,'nodes',len(x),'Tet10',len(tets),'Tri6',len(faces),flush=True)
 p=pore_metrics(x,faces);q=b6_metrics(x,tets)
 exact_cav=4*math.pi*R**3/3;exact_area=4*math.pi*R**2
 exact_shell=4*math.pi*(R6**3-R**3)/3;exact_d=-4*math.pi*R**2
 surfV=4*math.pi*R6**3/3-p['pore_volume_Q6_m3'];surfd=-3*p['pore_volume_Q6_m3']/R
 values=dict(label=label,mesh_file=str(mesh),mesh_sha256=digest,node_count=len(x),tet10_count=len(tets),pore_tri6=len(faces),
     **p,**q,pore_area_error_rel=p['pore_area_Q6_m2']/exact_area-1,
     pore_volume_error_rel=p['pore_volume_Q6_m3']/exact_cav-1,
     b6_volume_error_vs_exact_m3=q['b6_Q3_volume_m3']-exact_shell,
     b6_dV_error_vs_exact_m2=q['b6_Q3_volume_derivative_m2']-exact_d,
     b6_volume_error_vs_surface_surrogate_m3=q['b6_Q3_volume_m3']-surfV,
     b6_dV_error_vs_surface_surrogate_m2=q['b6_Q3_volume_derivative_m2']-surfd,
     surrogate_b6_volume_m3=surfV,surrogate_b6_dV_m2=surfd,
     surrogate_b6_normalized_dV_per_m=surfd/surfV,sec_wall=round(time.perf_counter()-t0,2))
 print('AUDIT_OK',label,'V_B6',q['b6_Q3_volume_m3'],'dV_B6',q['b6_Q3_volume_derivative_m2'],
       'dr_max_um',p['sampled_max_radial_departure_um'],'normal_max_deg',p['max_normal_angle_deg'],flush=True)
 return values

def selftest():
 w,d=tet_quadrature(); assert abs(sum(w)-1/6)<1e-14
 # Positive affine Tet10, inside B6, all nodes placed on true midpoints.
 base=np.array([[.002,0.,.03],[.0021,0.,.03],[.002,.0001,.03],[.002,0.,.0301]],dtype=float)
 X=np.vstack([base,[(base[i]+base[j])/2 for i,j in E10]])
 # Since b6_metrics expects imported numbering, the mesh has already gone through importer swap.
 # Element's logical vertex/edge order is the Stage3D07 post-swap internal order.
 tet=np.array([list(range(10))],dtype=np.int32)
 vel=X-C
 got=b6_metrics(X,tet,velocity_override=vel)
 V=(.0001**3)/6
 assert abs(got['b6_Q3_volume_m3']-V)<1e-23,(got,V)
 assert abs(got['b6_Q3_volume_derivative_m2']-3*V)<1e-23,got
 assert got['b6_nonpositive_sampled_detJ_count']==0
 # P10V-like nonuniform radial velocity: compare analytic Q3 dJac against centered geometry FD.
 actual=b6_metrics(X,tet)
 field=velocities(X);eps=1e-7
 zero=np.zeros_like(X)
 plus=b6_metrics(X+eps*field,tet,velocity_override=zero)['b6_Q3_volume_m3']
 minus=b6_metrics(X-eps*field,tet,velocity_override=zero)['b6_Q3_volume_m3']
 fd=(plus-minus)/(2*eps)
 assert abs(fd-actual['b6_Q3_volume_derivative_m2'])/abs(actual['b6_Q3_volume_derivative_m2'])<1e-7
 # Linear 6-node triangle in plane: geometry is exactly flat and area is 0.5.
 pts=np.array([[0.,0.,.03],[1.,0.,.03],[0.,1.,.03],[.5,0.,.03],[.5,.5,.03],[0.,.5,.03]],float)
 tw,tn,td=tri_quadrature()
 assert abs(float(sum(tw))-0.5)<1e-13
 X=pts[None,:,:]; D0=np.einsum('eij,iq->eqj',X,td[:,:,0]);D1=np.einsum('eij,iq->eqj',X,td[:,:,1]);
 assert np.max(np.abs(np.linalg.norm(np.cross(D0,D1),axis=-1)-1))<1e-13
 print('LIT06_SELFTEST_OK: affine Tet10 Q3 V and dV; affine Tri6 Q6 area; derivative vs centered geometry FD; Gauss weights')

def main():
 p=argparse.ArgumentParser(description='Stage3D07 LIT06 geometry-only B20 B6 audit')
 p.add_argument('--repo',default=r'G:\ildar\Stage3D07')
 p.add_argument('--labels',nargs='+',default=['H4W2B20','H4W4B20','H4W5B20'])
 p.add_argument('--out',default='OUTPUT_LIT06_B20')
 p.add_argument('--selftest',action='store_true')
 p.add_argument('--allow-sha-mismatch',action='store_true')
 args=p.parse_args()
 selftest()
 if args.selftest:return
 repo=Path(args.repo);out=Path(args.out);dest=out/'LIT06_B20_Q3_GEOMETRY.csv'
 if dest.exists():raise FileExistsError(f'Output exists: {dest}. Select a fresh --out folder')
 out.mkdir(parents=True,exist_ok=True)
 # Preflight all meshes BEFORE any potentially lengthy geometry audit.
 sources=[]
 for label in args.labels:
  if '=' in label:
   name,path=label.split('=',1);m=Path(path)
  else:name=label;m=lookup(repo,name)
  if not m.is_file():
   raise FileNotFoundError('Missing mesh '+name+': '+str(m))
  sources.append((name,m))
 print('LIT06_PREFLIGHT_OK meshes='+str(len(sources)),flush=True)
 results=[];errors=[]
 for name,m in sources:
  try:
   results.append(audit(name,m,args.allow_sha_mismatch))
  except Exception as exc:
   print('LIT06_MESH_ERROR',name,type(exc).__name__,str(exc),file=sys.stderr);errors.append((name,str(exc)))
 if results:
  with dest.open('w',newline='',encoding='utf-8') as f:
   writer=csv.DictWriter(f,fieldnames=COLS);writer.writeheader();writer.writerows(results)
  print('LIT06_CSV_WRITTEN',dest)
 if errors:raise SystemExit(2)
 print('LIT06_B20_GEOMETRY_AUDIT_OK meshes='+str(len(results)))
if __name__=='__main__':main()
