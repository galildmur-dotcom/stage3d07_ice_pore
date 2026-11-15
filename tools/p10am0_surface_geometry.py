#!/usr/bin/env python3
"""P10AM0: independent geometry-only audit for the spherical pore Tri6 surface.

Reads Gmsh MSH 2.2 ASCII. Evaluates *quadratic* surface patches between
mesh nodes, as well as discrete closed surface area and enclosed volume.
No FEM, no network, no files outside --out modified. Python stdlib only.
"""
import argparse
import collections
import csv
import hashlib
import math
import pathlib
import sys
import time

CENTER=(0.0,0.0,0.03)
RADIUS=0.001
DETECTION_TOL=1.e-6
GAUSS={
 3: [(0.1127016653792583,0.2777777777777778),
     (0.5,0.4444444444444444),(0.8872983346207417,0.2777777777777778)],
 4: [(0.06943184420297371,0.17392742256872693),
     (0.33000947820757187,0.32607257743127307),
     (0.6699905217924281,0.32607257743127307),
     (0.9305681557970262,0.17392742256872693)],
 6: [(0.033765242898423975,0.08566224618958517),
     (0.16939530676686776,0.1803807865240693),
     (0.38069040695840156,0.23395696728634552),
     (0.6193095930415985,0.23395696728634552),
     (0.8306046932331322,0.1803807865240693),
     (0.966234757101576,0.08566224618958517)]}

def add(a,b): return (a[0]+b[0],a[1]+b[1],a[2]+b[2])
def sub(a,b): return (a[0]-b[0],a[1]-b[1],a[2]-b[2])
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def dot(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def norm(a):return math.sqrt(dot(a,a))

def shape(r,s):
 l0=1-r-s;l1=r;l2=s
 n=(l0*(2*l0-1),l1*(2*l1-1),l2*(2*l2-1),4*l0*l1,4*l1*l2,4*l2*l0)
 dr=(1-4*l0,4*l1-1,0,4*(l0-l1),4*l2,-4*l2)
 ds=(1-4*l0,0,4*l2-1,-4*l1,4*l1,4*(l0-l2))
 return n,dr,ds

def integration_rule(order):
 result=[]
 for a,wa in GAUSS[order]:
  for b,wb in GAUSS[order]:
   r=a;s=(1-a)*b
   n,dr,ds=shape(r,s)
   result.append((n,dr,ds,wa*wb*(1-a)))
 return result

def parse_msh(path):
 nodes={};faces=[];n_all_tri6=0;all_records=0
 with path.open('r',encoding='utf-8',errors='strict') as f:
  if f.readline().strip()!='$MeshFormat':raise ValueError('Expected MSH2 ASCII header')
  head=f.readline().split()
  if len(head)<3 or not head[0].startswith('2.') or head[1]!='0':raise ValueError('Only ASCII MSH2 is supported')
  if f.readline().strip()!='$EndMeshFormat':raise ValueError('Invalid MSH2 header')
  for line in f:
   item=line.strip()
   if item=='$Nodes':
    count=int(next(f))
    for _ in range(count):
     fields=next(f).split();nodes[int(fields[0])]=tuple(map(float,fields[1:4]))
    if next(f).strip()!='$EndNodes':raise ValueError('Invalid MSH2 nodes section')
   elif item=='$Elements':
    count=int(next(f));all_records=count
    for _ in range(count):
     fields=next(f).split()
     if fields[1]!='9':continue
     num_tags=int(fields[2]);ids=tuple(map(int,fields[3+num_tags:3+num_tags+6]))
     if len(ids)!=6:raise ValueError('Bad Tri6 connectivity')
     faces.append(ids);n_all_tri6+=1
    if next(f).strip()!='$EndElements':raise ValueError('Invalid MSH2 elements section')
   elif item.startswith('$') and not item.startswith('$End'):
    terminator='$End'+item[1:]
    for subline in f:
     if subline.strip()==terminator:break
    else:raise ValueError('Unterminated MSH2 section '+item)
 if not nodes or not faces:raise ValueError('No nodes or Tri6 found')
 pore=[]
 for tri in faces:
  if all(abs(norm(sub(nodes[i],CENTER))-RADIUS)<DETECTION_TOL for i in tri):pore.append(tri)
 if not pore:raise ValueError('No pore Tri6 detected')
 edges=collections.Counter()
 for t in pore:
  for a,b in ((0,1),(1,2),(2,0)):edges[tuple(sorted((t[a],t[b])))]+=1
 nonmanifold=sum(1 for x in edges.values() if x!=2)
 if nonmanifold:raise ValueError(f'Pore surface not closed/manifold: {nonmanifold} corner edges have incidence != 2')
 return nodes,pore,n_all_tri6,all_records,len(edges)

def sha256(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for part in iter(lambda:f.read(8*1024*1024),b''):h.update(part)
 return h.hexdigest()

def audit(label,path):
 started=time.perf_counter();mesh_sha=sha256(path)
 nodes,pore,n_tri6_all,total_elements,n_edges=parse_msh(path)
 rules={k:integration_rule(k) for k in (3,4,6)}
 output={k:{'area':0.,'volume':0.,'l2rad':0.,'meanangle':0.,'maxrad':0.,'maxangle':0.} for k in rules}
 nodeerr=0.;invfaces=0;min_darea=float('inf')
 for tri in pore:
  xyz=[nodes[i] for i in tri]
  for x in xyz:nodeerr=max(nodeerr,abs(norm(sub(x,CENTER))-RADIUS))
  center_shape,ddr,dds=shape(1/3,1/3)
  xx=tuple(sum(center_shape[i]*xyz[i][j] for i in range(6)) for j in range(3))
  tr=tuple(sum(ddr[i]*xyz[i][j] for i in range(6)) for j in range(3))
  ts=tuple(sum(dds[i]*xyz[i][j] for i in range(6)) for j in range(3))
  ori=1 if dot(cross(tr,ts),sub(xx,CENTER))>=0 else -1
  if ori<0:invfaces+=1
  for order,qs in rules.items():
   rec=output[order]
   for n,dr,ds,w in qs:
    x=(sum(n[i]*xyz[i][j] for i in range(6)) for j in range(3))
    p=tuple(x);a=tuple(sum(dr[i]*xyz[i][j] for i in range(6)) for j in range(3))
    b=tuple(sum(ds[i]*xyz[i][j] for i in range(6)) for j in range(3))
    cv=cross(a,b);da=norm(cv)
    if not da>0 or not math.isfinite(da):raise ValueError('Degenerate surface quadrature patch')
    if order==6:min_darea=min(min_darea,da)
    rvec=sub(p,CENTER);radius=norm(rvec);rad=abs(radius-RADIUS)
    cosang=max(-1.,min(1.,ori*dot(cv,rvec)/(da*radius)))
    angle=math.acos(cosang)
    area=w*da
    rec['area']+=area
    rec['volume']+=w*ori*dot(cv,rvec)/3.0
    rec['l2rad']+=area*rad*rad
    rec['meanangle']+=area*angle
    rec['maxrad']=max(rec['maxrad'],rad)
    rec['maxangle']=max(rec['maxangle'],angle)
 a=4*math.pi*RADIUS**2;v=4*math.pi*RADIUS**3/3
 q=output[6]
 res={'label':label,'mesh_file':str(path),'mesh_sha256':mesh_sha,
      'nodes':len(nodes),'element_records':total_elements,'tri6_total':n_tri6_all,
      'pore_tri6':len(pore),'pore_edges':n_edges,'orientation_flip_faces':invfaces,
      'node_max_radial_departure_um':nodeerr*1e6,
      'area_Q3_m2':output[3]['area'],'area_Q4_m2':output[4]['area'],'area_Q6_m2':q['area'],
      'area_exact_sphere_m2':a,'area_Q6_vs_sphere_rel':q['area']/a-1,
      'area_Q4_vs_Q6_rel':output[4]['area']/q['area']-1,
      'volume_Q3_m3':output[3]['volume'],'volume_Q4_m3':output[4]['volume'],
      'volume_Q6_m3':q['volume'],'volume_exact_sphere_m3':v,
      'volume_Q6_vs_sphere_rel':q['volume']/v-1,
      'volume_Q4_vs_Q6_rel':output[4]['volume']/q['volume']-1,
      'sampled_max_radial_departure_um':q['maxrad']*1e6,
      'sampled_rms_radial_departure_um':math.sqrt(q['l2rad']/q['area'])*1e6,
      'sampled_mean_normal_angle_deg':q['meanangle']/q['area']*180/math.pi,
      'sampled_max_normal_angle_deg':q['maxangle']*180/math.pi,
      'min_patch_cross_norm_m2':min_darea,'wall_s':time.perf_counter()-started}
 return res

def selftest():
 for r,s in [(0.2,0.1),(0,0),(1,0),(0,1),(1/3,1/3)]:
  n,d1,d2=shape(r,s)
  assert abs(sum(n)-1)<5e-15 and abs(sum(d1))<5e-15 and abs(sum(d2))<5e-15
 for order in (3,4,6):
  rule=integration_rule(order)
  assert abs(sum(q[3] for q in rule)-0.5)<1e-14
  assert abs(sum((q[0][1]+.5*q[0][3]+.5*q[0][4])*q[3] for q in rule)-1/6)<1e-14
 # Flat reference triangle, edge midpoints; cross area exactly 1/2.
 xyz=[(0.,0.,0.),(1.,0.,0.),(0.,1.,0.),(.5,0.,0.),(.5,.5,0.),(0.,.5,0.)]
 for order in (3,4,6):
  aa=0.
  for n,dr,ds,w in integration_rule(order):
   tr=tuple(sum(dr[i]*xyz[i][j] for i in range(6)) for j in range(3))
   ts=tuple(sum(ds[i]*xyz[i][j] for i in range(6)) for j in range(3))
   aa+=norm(cross(tr,ts))*w
  assert abs(aa-.5)<1e-14
 print('P10AM0_SELFTEST_OK tri6_partition=1 triangle_rules=1 planar_area=1')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--mesh',action='append',default=[],help='LABEL=full_path_to_ascii_msh2 (repeat)')
 p.add_argument('--out',type=pathlib.Path)
 p.add_argument('--selftest',action='store_true')
 args=p.parse_args()
 if args.selftest:selftest();return
 if not args.mesh or args.out is None:p.error('Provide --mesh LABEL=PATH (one or more) and --out NEW_DIRECTORY')
 if args.out.exists():raise ValueError('Output must be NEW directory: '+str(args.out))
 checks=[];labels=set()
 for item in args.mesh:
  if '=' not in item:raise ValueError('--mesh needs LABEL=PATH')
  label,raw=item.split('=',1);path=pathlib.Path(raw)
  if not label or label in labels:raise ValueError('Mesh labels must be nonempty and unique')
  if not path.is_file():raise ValueError('Mesh missing: '+str(path))
  labels.add(label);checks.append((label,path))
 args.out.mkdir(parents=True)
 rows=[]
 for label,path in checks:
  print(f'P10AM0_START mesh={label} file={path}',flush=True)
  row=audit(label,path);rows.append(row)
  print('P10AM0_MESH_OK mesh={label} pore_tri6={pore_tri6} max_radial_um={sampled_max_radial_departure_um:.10g} mean_normal_angle_deg={sampled_mean_normal_angle_deg:.10g} wall_s={wall_s:.3f}'.format(**row),flush=True)
 with (args.out/'P10AM0_SURFACE_GEOMETRY.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 with (args.out/'P10AM0_MANIFEST.txt').open('w',encoding='utf-8') as f:
  f.write('P10AM0 geometry-only surface audit. NOT FEM error, not shape derivative convergence.\n')
  f.write('Uses sampled Gaussian points on Gmsh quadratic Tri6 (Q6 reference).\n')
  f.write('Sphere center=(0,0,0.03) m, radius=0.001 m.\n')
  for row in rows:f.write(f"{row['label']} SHA256={row['mesh_sha256']} pore_faces={row['pore_tri6']}\n")
 print('P10AM0_AUDIT_OK meshes={}'.format(len(rows)))
 print('P10AM0_OUTPUT='+str(args.out/'P10AM0_SURFACE_GEOMETRY.csv'))

if __name__=='__main__':
 try:main()
 except Exception as e:print('P10AM0_ERROR: '+str(e),file=sys.stderr);sys.exit(2)
