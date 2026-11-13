#!/usr/bin/env python3
"""P10AA: lightweight comparison of the *curved spherical pore* Tri6 surfaces
for two Gmsh 2.x ASCII meshes. No FEM, no mesh modification, no Git.

Compares physical Tri6 coordinates, corner connectivity, and mid-edge nodes;
node IDs and orientation may differ. An identity check is NOT convergence.
"""
import argparse, collections, csv, datetime, hashlib, pathlib, sys, zipfile
CENTER=(0.,0.,.03)
RADIUS=.001
PORE_TOL=1e-6  # metres, classification only
COMPARE_TOL=1e-10 # metres, coordinate quantization

def sha256(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for x in iter(lambda:f.read(4*1024*1024),b''):h.update(x)
 return h.hexdigest()

def parse_surface(path):
 nodes={};faces=[];n_tri6_all=0
 with path.open('r',encoding='utf-8',newline=None) as f:
  assert f.readline().strip()=='$MeshFormat','MSH2 header missing'
  ver=f.readline().split()
  assert len(ver)>=3 and ver[0].startswith('2.') and ver[1]=='0','Expected MSH2 ASCII'
  assert f.readline().strip()=='$EndMeshFormat','EndMeshFormat missing'
  while True:
   line=f.readline()
   if not line:break
   label=line.strip()
   if label=='$Nodes':
    n=int(f.readline());assert n>0
    for _ in range(n):
     p=f.readline().split();assert len(p)>=4
     nodes[int(p[0])]=(float(p[1]),float(p[2]),float(p[3]))
    assert f.readline().strip()=='$EndNodes'
   elif label=='$Elements':
    n=int(f.readline())
    for _ in range(n):
     p=f.readline().split();assert len(p)>=3
     if p[1]!='9':continue # Tri6 is Gmsh element type 9
     k=int(p[2]);nid=[int(x) for x in p[3+k:3+k+6]]
     assert len(nid)==6
     faces.append(nid);n_tri6_all+=1
    assert f.readline().strip()=='$EndElements'
   elif label.startswith('$') and not label.startswith('$End'):
    end='$End'+label[1:]
    while True:
     x=f.readline()
     assert x, ('unexpected EOF',label)
     if x.strip()==end:break
 if not nodes or not faces:raise ValueError('Nodes/Tri6 missing from '+str(path))
 # Pick pore Tri6 when every of the 6 interpolation nodes sits on nominal sphere.
 pore=[];surface_nodes=set()
 for tri in faces:
  if all(abs(sum((nodes[i][j]-CENTER[j])**2 for j in range(3))**.5-RADIUS)<=PORE_TOL for i in tri):
   pore.append(tri);surface_nodes.update(tri)
 if not pore:raise ValueError('No pore Tri6 faces detected; check centre/radius.')
 return {'nodes':nodes,'pore_faces':pore,'pore_node_ids':surface_nodes,
         'tri6_all':n_tri6_all,'node_count':len(nodes)}

def key(p,tol):return tuple(int(round(x/tol)) for x in p)

def face_signature(nodes,face,tol):
 ids=[key(nodes[i],tol) for i in face]
 corners=tuple(sorted(ids[:3]))
 # Gmsh Tri6: midnodes 3:(0,1),4:(1,2),5:(2,0).
 edges=tuple(sorted([(tuple(sorted((ids[a],ids[b]))),ids[mid]) for a,b,mid in [(0,1,3),(1,2,4),(2,0,5)]]))
 return corners,edges

def describe(data,tol):
 ids=data['pore_node_ids'];nodes=data['nodes']
 coords=collections.Counter(key(nodes[i],tol) for i in ids)
 faces=collections.Counter(face_signature(nodes,face,tol) for face in data['pore_faces'])
 return coords,faces

def compare(a,b,tol):
 ca,fa=describe(a,tol);cb,fb=describe(b,tol)
 return {'pore_node_count_a':len(a['pore_node_ids']),
         'pore_node_count_b':len(b['pore_node_ids']),
         'pore_tri6_count_a':len(a['pore_faces']),
         'pore_tri6_count_b':len(b['pore_faces']),
         'unmatched_nodes_a':sum((ca-cb).values()),
         'unmatched_nodes_b':sum((cb-ca).values()),
         'unmatched_tri6_a':sum((fa-fb).values()),
         'unmatched_tri6_b':sum((fb-fa).values()),
         'surface_identical':ca==cb and fa==fb}

def selftest():
 xyz={1:(0.,0.,1.),2:(1.,0.,0.),3:(0.,1.,0.),4:(.5,0.,.5),5:(.5,.5,0.),6:(0.,.5,.5)}
 # cyclic orientation change, with Gmsh-consistent repositioning of midnodes
 f1=[1,2,3,4,5,6];f2=[2,3,1,5,6,4]
 assert face_signature(xyz,f1,1e-10)==face_signature(xyz,f2,1e-10)
 a={'nodes':xyz,'pore_faces':[f1],'pore_node_ids':set(f1)}
 b={'nodes':xyz,'pore_faces':[f2],'pore_node_ids':set(f2)}
 assert compare(a,b,1e-10)['surface_identical']
 c={'nodes':dict(xyz,**{}),'pore_faces':[f1],'pore_node_ids':set(f1)}
 c['nodes'][4]=(.51,0.,.49)
 assert not compare(a,c,1e-10)['surface_identical']
 print('P10AA_SURFACE_TEST_OK topology_permutation=1 changed_midnode_detected=1')

def process(path_a,path_b,out):
 sha_a=sha256(path_a);sha_b=sha256(path_b)
 if sha_a==sha_b:raise ValueError('Both selected mesh files have identical SHA-256; select independent H4W2 and H4W2B20 files')
 a=parse_surface(path_a);b=parse_surface(path_b)
 result=compare(a,b,COMPARE_TOL)
 out.mkdir(parents=True,exist_ok=True)
 fields={
 'mesh_a':str(path_a),'mesh_b':str(path_b),
 'sha256_a':sha_a,'sha256_b':sha_b,
 'center_m':str(CENTER),'radius_m':RADIUS,
 'pore_detection_tolerance_m':PORE_TOL,'comparison_tolerance_m':COMPARE_TOL,
 'all_tri6_a':a['tri6_all'],'all_tri6_b':b['tri6_all'],
 'expected_pore_tri6_each':6636,'pore_counts_match_p10w':len(a['pore_faces'])==6636 and len(b['pore_faces'])==6636,
 **result,'convergence_proof':False,
 'scope':'Gmsh Tri6 spherical pore node coordinates and corner/edge-midpoint connectivity only; IDs/orientation ignored'
 }
 with (out/'P10AA_SURFACE_IDENTITY.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=list(fields),lineterminator='\n');w.writeheader();w.writerow(fields)
 with (out/'P10AA_SURFACE_AUDIT.txt').open('w',encoding='utf-8') as f:
  f.write('P10AA curved Tri6 surface identity audit. NOT spatial convergence.\n')
  for k,v in fields.items():f.write(f'{k}={v}\n')
 # Cross-check multiple tolerances for robustness without replacing fixed decision.
 for tol in [1e-9,1e-11]:
  t=compare(a,b,tol)
  with (out/'P10AA_SURFACE_AUDIT.txt').open('a',encoding='utf-8') as f:
   f.write(f'aux_tolerance_m={tol} identical={t["surface_identical"]} unmatched_nodes={t["unmatched_nodes_a"]}/{t["unmatched_nodes_b"]} unmatched_faces={t["unmatched_tri6_a"]}/{t["unmatched_tri6_b"]}\n')
 repo=next((p for p in pathlib.Path(__file__).resolve().parents if p.name.lower()=='stage3d07'),None)
 dest=(repo.parent/'PORE_CHATGPT_EXPORTS') if repo else (pathlib.Path(__file__).resolve().parents[1]/'exports')
 dest.mkdir(parents=True,exist_ok=True)
 stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
 package=dest/f'P10AA_SURFACE_IDENTITY_{stamp}.zip'
 with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for p in sorted(out.iterdir()):
   if p.is_file():z.write(p,arcname=p.name)
 if not fields['pore_counts_match_p10w']:
  print('P10AA_WARNING: pore Tri6 count differs from P10W reference 6636; validate mesh selection')
 print('P10AA_SURFACE_IDENTICAL='+('YES' if result['surface_identical'] else 'NO'))
 print('P10AA_RESULTS_ZIP='+str(package))
 print('P10AA_AUDIT_OK  NOTE: this is a geometry identity check, not convergence proof')

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--mesh-a',type=pathlib.Path)
 ap.add_argument('--mesh-b',type=pathlib.Path)
 ap.add_argument('--out',type=pathlib.Path)
 ap.add_argument('--gui',action='store_true')
 ap.add_argument('--selftest',action='store_true')
 args=ap.parse_args()
 if args.selftest:selftest();return
 if args.gui:
  import tkinter as tk
  from tkinter import filedialog
  root=tk.Tk();root.withdraw()
  a=filedialog.askopenfilename(title='Choose H4W2.msh',filetypes=[('Gmsh files','*.msh')])
  if not a:raise ValueError('Cancelled selection H4W2')
  b=filedialog.askopenfilename(title='Choose H4W2B20.msh',filetypes=[('Gmsh files','*.msh')])
  if not b:raise ValueError('Cancelled selection H4W2B20')
  root.destroy()
  args.mesh_a=pathlib.Path(a);args.mesh_b=pathlib.Path(b)
 if not args.mesh_a or not args.mesh_b:ap.error('Use --mesh-a and --mesh-b, or --gui')
 if not args.mesh_a.is_file() or not args.mesh_b.is_file():raise ValueError('Mesh file missing')
 repo=next((p for p in pathlib.Path(__file__).resolve().parents if p.name.lower()=='stage3d07'),None)
 out=args.out or ((repo/'LOCAL_RUNS'/'P10AA_SURFACE_IDENTITY') if repo else (pathlib.Path(__file__).resolve().parents[1]/'local_results'))
 process(args.mesh_a,args.mesh_b,out)
if __name__=='__main__':
 try:main()
 except Exception as e:
  print('P10AA_STOPPED '+str(e),file=sys.stderr);sys.exit(2)
