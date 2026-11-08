#!/usr/bin/env python3
"""Integration test: split 300+600s EDV trajectory gives identical checkpoint to uninterrupted run."""
import argparse, tempfile, subprocess, pathlib, csv, hashlib
p=argparse.ArgumentParser();p.add_argument('--executable',required=True);p.add_argument('--mesh',required=True);p.add_argument('--temperature',required=True)
a=p.parse_args()
exe=str(pathlib.Path(a.executable).resolve());mesh=str(pathlib.Path(a.mesh).resolve());tpath=str(pathlib.Path(a.temperature).resolve());
with tempfile.TemporaryDirectory(prefix='stage3d06_restart_') as d:
 root=pathlib.Path(d)
 def invoke(output,times,resume=False):
  cmd=[exe,'--mesh',mesh,'--temp-dir',tpath,'--out',str(output),'--law','EDV','--modulus','CONST','--times',times,'--quad','3','--cg-tol','1e-7']
  if resume:cmd.append('--resume')
  subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 ref=root/'uninterrupted';split=root/'split'
 invoke(ref,'300,600');invoke(split,'300');invoke(split,'300,600',True)
 x=(ref/'EDV_CONST'/'restart.bin').read_bytes();y=(split/'EDV_CONST'/'restart.bin').read_bytes()
 assert x==y, f'Checkpoint differs: {hashlib.sha256(x).hexdigest()} / {hashlib.sha256(y).hexdigest()}'
 for name in ('time_series.csv','G06_campaign.csv'):
  l=list(csv.DictReader((ref/name).open())) if name=='G06_campaign.csv' else list(csv.DictReader((ref/'EDV_CONST'/name).open()))
  r=list(csv.DictReader((split/name).open())) if name=='G06_campaign.csv' else list(csv.DictReader((split/'EDV_CONST'/name).open()))
  assert len(l)==len(r)==2,(name,len(l),len(r))
  for x,y in zip(l,r):
   for key in ('time_s','Psi6','PsiOmega'):
    assert float(x[key])==float(y[key]),(name,key,x[key],y[key])
 print('G06 restart PASS: 2 steps vs split + resume; bitwise identical EDV checkpoint and Psi')
