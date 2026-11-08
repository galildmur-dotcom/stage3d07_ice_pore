#!/usr/bin/env python3
"""Independent Python readback of C++ point-campaign CSV, with analytical ED references."""
from pathlib import Path
import csv, json, math, argparse
from collections import defaultdict

p = argparse.ArgumentParser();p.add_argument('--results',default='results/ED_material');args=p.parse_args()
root=Path(args.results)
def read(name):
    with open(root/name,encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
Ad_ref=1.5e-3;Q=66900.; Rgas=8.31446261815324; a=1.8e-9; nu=.35; Er=9.5e9
A=lambda TK:Ad_ref*math.exp(-Q/Rgas*(1/TK-1/263.15))
E=lambda TK,m:Er if m=='CONST' else Er*(8.93-.012*(TK-273.15))/9.17
j={}
rows=read('G04_temporal_convergence.csv');groups=defaultdict(list)
for r in rows:
    m,T=r['mode'],float(r['T_K']);dt=float(r['dt_s']);N=round(600/dt)
    assert abs(N*dt-600)<1e-9
    G=E(T,m)/(2*(1+nu)); lam=A(T)*(1+2*G*a)
    d=.00068
    exact=2*G*(d-(2*G*a*d/(1+2*G*a))*(1-math.exp(-lam*600)))
    assert abs(exact-float(r['exact_shear_Pa']))<1e-6
    err=abs(float(r['computed_shear_Pa'])-exact)
    assert abs(err-float(r['absolute_error_Pa']))<1e-6
    groups[(m,T)].append((dt,err))
for group,ar in groups.items():
    ar.sort(reverse=True)
    assert len(ar)==6
    assert all(ar[k][1]>ar[k+1][1] for k in range(len(ar)-1))
errors=sorted(groups[('CONST',253.15)],reverse=True)
order=[math.log(errors[k][1]/errors[k+1][1])/math.log(2) for k in range(len(errors)-1)]
j['G04_analytical_relaxation']={'status':'PASS','temperatures_and_branches':len(groups),'max_error_Pa_dt300':errors[0][1],'min_error_Pa_dt9_375':errors[-1][1],'observed_orders':order}

rows=read('G04_stress_controlled_recovery.csv');mx=0
for r in rows:
    t=float(r['time_s']);ref=(a*1.7e6*(1-math.exp(-A(253.15)*min(t,600)))*(1 if t<=600 else math.exp(-A(253.15)*(t-600))))
    assert abs(ref-float(r['analytic_ed_xy']))<1e-15
    mx=max(mx,abs(float(r['ed_xy'])-ref))
assert mx<1e-6
j['G04_analytical_recovery']={'status':'PASS','max_abs_ED_error':mx}
rows=read('G04_material_parameters.csv')
for r in rows:
    T=float(r['T_K']);assert abs(float(r['Ad_1_s'])-A(T))<1e-16
    assert abs(float(r['E_VAR_Pa'])-E(T,'VAR'))<1e-4
    assert abs(float(r['Kd_Pa_inv'])-1.2e-9)<1e-20
j['G04_parameter_table']={'status':'PASS','temperatures':len(rows)}
rows=read('G04_cooling_point_pilot.csv')
assert len(rows)==480
pilots={}
for m in ('CONST','VAR'):
    part=[r for r in rows if r['model']==m]
    assert len(part)==240
    assert all(abs(float(r['temperature_C'])+20+3*(1-math.exp(-float(r['time_s'])/300)))<1e-12 for r in part)
    assert all(float(r['dissipation_W_m3'])>=0 for r in part)
    pilots[m]={'sigma_xy_MPa_at_3600':float(part[-1]['sigma_xy_MPa']),'ed_xy_at_3600':float(part[-1]['ed_xy'])}
j['G04_point_cooling_pilot']={'status':'PASS','note':'Prescribed strain, prescribed point temperature; NOT a 3D FEM simulation','branches':pilots}
(root/'G04_independent_readback.json').write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(j,ensure_ascii=False,indent=2))
