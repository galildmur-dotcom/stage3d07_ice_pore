#!/usr/bin/env python3
"""Read-only checkpoint replay regression; checks exported QP maximum and source immutability."""
import argparse, csv, hashlib, math, pathlib, shutil, subprocess, sys, tempfile, xml.etree.ElementTree as ET
p=argparse.ArgumentParser();p.add_argument('--exe',type=pathlib.Path,required=True);p.add_argument('--root',type=pathlib.Path,required=True)
a=p.parse_args();r=a.root.resolve();exe=a.exe.resolve()
ref=r/'results/G06_H0_dt300/EDV_VAR';temp=r/'results/G06_thermal_H0_dt300';mesh=r/'meshes/H0.msh';times=','.join(str(t) for t in range(300,3601,300))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='stage06_qp_replay_') as tmp:
  dest=pathlib.Path(tmp)/'EDV_VAR';dest.mkdir();
  for name in ('restart.bin','time_series.csv'):shutil.copy2(ref/name,dest/name)
  hash_before=digest(dest/'restart.bin')
  argv=[str(exe),'--mesh',str(mesh),'--temp-dir',str(temp),'--out',str(tmp),'--law','EDV','--modulus','VAR','--times',times,'--quad','3','--postprocess-only']
  cp=subprocess.run(argv,capture_output=True,text=True,timeout=60)
  if cp.returncode:raise RuntimeError(cp.stdout+'\n'+cp.stderr)
  assert hash_before==digest(dest/'restart.bin'), 'Postprocessor changed checkpoint'
  with (ref/'time_series.csv').open() as f:baseline=list(csv.DictReader(f))[-1]
  with (dest/'qp_diagnostics_3600s.csv').open() as f:diagnosed=list(csv.DictReader(f))[0]
  assert abs(float(baseline['maxS1_MPa'])-float(diagnosed['QP_max_MPa']))<1e-9
  assert abs(float(baseline['Psi6'])-float(diagnosed['Phi6']))<1e-10
  assert abs(float(baseline['PsiOmega'])-float(diagnosed['PhiOmega']))<1e-10
  assert float(diagnosed['gap_from_pore_mm'])>=-1e-4
  root=ET.parse(dest/'qp_diagnostics_3600s.vtu').getroot()
  cells=root.find('.//CellData');wanted={'Principal_QP_max_MPa','QP_max_x_m','QP_max_y_m','QP_max_z_m','QP_max_index'}
  arrays={x.get('Name'):x for x in cells.findall('DataArray')}
  assert wanted.issubset(arrays), f'Missing diagnostic arrays {wanted-arrays.keys()}'
  data=[float(x) for x in arrays['Principal_QP_max_MPa'].text.split()]
  assert len(data)==7388
  assert math.isclose(max(data),float(diagnosed['QP_max_MPa']),rel_tol=1e-10)
  ranks=list(csv.DictReader((dest/'qp_top100_3600s.csv').open()))
  assert len(ranks)==100 and all(float(ranks[i]['sigma1_QP_max_MPa'])>=float(ranks[i+1]['sigma1_QP_max_MPa']) for i in range(99))
  print('QP_POSTPROCESS PASS: max=',max(data),'Phi6=',diagnosed['Phi6'],'gap_mm=',diagnosed['gap_from_pore_mm'],'checkpoint SHA256 unchanged')
