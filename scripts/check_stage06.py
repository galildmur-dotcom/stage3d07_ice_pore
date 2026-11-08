#!/usr/bin/env python3
"""Independent acceptance check for 3D spatial Stage06 output; stdlib-only."""
import csv, math, pathlib, argparse, json, xml.etree.ElementTree as ET
p=argparse.ArgumentParser();p.add_argument('--campaign',default='results/G06_H0_dt300');p.add_argument('--reference',default='results');p.add_argument('--out',default='results/G06_validation.json');arg=p.parse_args()
root=pathlib.Path(arg.campaign);expected=list(range(300,3601,300));rows=list(csv.DictReader((root/'G06_campaign.csv').open()));parsed={}
for row in rows:
 key=(row['law'],row['modulus']);parsed.setdefault(key,[]).append(row)
assert len(parsed)==6, 'Expected 6 distinct model pairs'
summary={}
for key,rr in parsed.items():
 assert [int(r['time_s']) for r in rr]==expected,(key,'incomplete time grid')
 for r in rr:
  assert all(math.isfinite(float(r[k])) for k in ('max_principal_MPa','Psi6','PsiOmega','relative_residual','gauge_mean_uz_m','volume6_m3'))
  assert float(r['relative_residual']) < 2e-7
  assert abs(float(r['gauge_mean_uz_m'])) < 1e-14
  assert abs(float(r['volume6_m3'])-4*math.pi/3*(6**3-1)*1e-9)/ (4*math.pi/3*(6**3-1)*1e-9) < .0003
  assert int(r['Newton_steps'])<=5
  assert float(r['Psi6'])>0 and float(r['PsiOmega'])>0
 label=f'{key[0]}_{key[1]}';t=[int(r['time_s']) for r in rr]
 phi6=[float(r['Psi6']) for r in rr];phiO=[float(r['PsiOmega']) for r in rr];
 # At t=0 the body is initially stress-free; regularized Psi(0)=3*(epsilon_s/2)^2.
 p0=3*(1e-3/2)**2
 j6=sum((a+b)*.5*(t1-t0) for a,b,t0,t1 in zip([p0]+phi6[:-1],phi6,[0]+t[:-1],t))/t[-1]
 jO=sum((a+b)*.5*(t1-t0) for a,b,t0,t1 in zip([p0]+phiO[:-1],phiO,[0]+t[:-1],t))/t[-1]
 summary[label]={'max_sigma1_MPa_at_3600':float(rr[-1]['max_principal_MPa']), 'Phi6_at_3600':phi6[-1], 'PhiOmega_at_3600':phiO[-1], 'j6_trapezoid':j6, 'jOmega_trapezoid':jO,'max_newton':max(int(r['Newton_steps']) for r in rr),'max_relative_equilibrium_residual':max(float(r['relative_residual']) for r in rr),'peak_memory_kB':max(int(r['VmHWM_kB']) for r in rr)}
# Reuse original E-only 3D independent solver on the same thermo-field: field should match.
def disp(path):
 root=ET.parse(path).getroot()
 arr=next(a for a in root.iter('DataArray') if a.attrib.get('Name')=='Displacement_m')
 return [float(v) for v in arr.text.split()]
for mod in ('CONST','VAR'):
 a=disp(root/f'E_{mod}'/'mechanics_3600s.vtu')
 b=disp(pathlib.Path(arg.reference)/'mechanics_H0'/f'E_{mod}_t3600.vtu')
 assert len(a)==len(b)
 err=math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))/max(1e-20,math.sqrt(sum(x*x for x in b)))
 summary[f'elastic_parity_{mod}']={'relative_displacement_l2':err}
 assert err<1e-4, ('E-only parity too inaccurate',mod,err)
path=pathlib.Path(arg.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(summary,indent=2),encoding='utf-8')
for k,v in summary.items():print(k,v)
print('PASS stage06: all 72 steps, 6 matched branches, independent E displacement parity')
