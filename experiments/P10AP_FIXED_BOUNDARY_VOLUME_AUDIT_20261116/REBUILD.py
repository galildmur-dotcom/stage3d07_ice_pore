#!/usr/bin/env python3
"""Rebuild P10AP derived CSV files from the original six P10W CSVs.
Only Python standard library is needed. No FEM or Git actions.
"""
from pathlib import Path
import csv
from collections import defaultdict
root = Path(__file__).resolve().parent
ip = root / 'input'
od = root / 'derived'
od.mkdir(exist_ok=True)

def read(name):
    with (ip / name).open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def num(x): return float(x)

def data(name):
    rows=read(name)
    assert len(rows)==3 and {r['functional'] for r in rows}=={'j6','jpeak','jen'},(name,rows)
    return {r['functional']:r for r in rows}

baseA=data('P10W_BASE_ADJOINT.csv'); starA=data('P10W_VSTAR_ADJOINT.csv')
baseC=data('P10W_BASE_COMPONENTS.csv');starC=data('P10W_VSTAR_COMPONENTS.csv')
refA=data('P10W_W4B20_REFERENCE.csv')
baseT=read('P10W_BASE_STEPS.csv');starT=read('P10W_VSTAR_STEPS.csv')
colsC=['explicit_objective_shape_per_m','equilibrium_residual_shape_per_m','internal_history_shape_per_m', 'total_mechanical_shape_per_m', 'thermal_adjoint_per_m', 'total_adjoint_per_m']
for name,a,c,t in [('BASE',baseA,baseC,baseT),('VSTAR',starA,starC,starT)]:
    assert len(t)==18 and len({(r['functional'],r['time_step']) for r in t})==18
    assert all(float(r['dt_s'])==150 and int(r['steps'])==6 and r['mode']=='R' and r['geometry_derivative_method']=='ANALYTIC_TET10' for r in a.values())
    assert {r['mesh'] for r in a.values()}=={r['mesh'] for r in c.values()}=={r['mesh'] for r in t}
    for k in ['j6','jpeak','jen']:
        aa=a[k];cc=c[k];tt=[r for r in t if r['functional']==k]
        for r in tt:
            val=sum(num(r[x]) for x in colsC[:3]); assert abs(val-num(r['total_mechanical_shape_per_m']))<1e-12
        assert abs(sum(num(r['total_mechanical_shape_per_m']) for r in tt)-num(cc['total_mechanical_shape_per_m']))<3e-12
        assert abs(sum(num(cc[x]) for x in colsC[:3])-num(cc['total_mechanical_shape_per_m']))<3e-12
        assert abs(num(cc['total_mechanical_shape_per_m'])+num(cc['thermal_adjoint_per_m'])-num(cc['total_adjoint_per_m']))<3e-12
        assert abs(num(aa['total_adjoint_per_m'])-num(cc['total_adjoint_per_m']))<3e-12
        assert abs(num(aa['objective'])-num(cc['objective']))<1e-12
assert {r['mesh'] for r in baseA.values()}=={'H4W4B2'}
assert {r['mesh'] for r in starA.values()}=={'H4W4B2_VSTAR12000_P10AM3'}

rows=[]
for k in ['j6','jpeak','jen']:
    a,b=baseA[k],starA[k]
    delta=num(b['total_adjoint_per_m'])-num(a['total_adjoint_per_m'])
    dB20=num(refA[k]['total_adjoint_per_m'])-num(a['total_adjoint_per_m'])
    comp={c:num(starC[k][c])-num(baseC[k][c]) for c in colsC}
    compAbs=sum(abs(comp[c]) for c in colsC[:3])+abs(comp['thermal_adjoint_per_m'])
    rows.append({'functional':k,'base_objective':a['objective'],'vstar_objective':b['objective'],
                 'delta_objective':num(b['objective'])-num(a['objective']),
                 'base_derivative_per_m':a['total_adjoint_per_m'],
                 'vstar_derivative_per_m':b['total_adjoint_per_m'],
                 'delta_derivative_per_m':delta,
                 'delta_relative_percent':100*delta/num(a['total_adjoint_per_m']),
                 'base_to_W4B20_delta_per_m':dB20,
                 'ratio_abs_W4B20_delta_over_VSTAR_delta':abs(dB20/delta),
                 'sum_abs_four_component_changes':compAbs,
                 'component_change_cancellation_ratio':compAbs/max(abs(delta),1e-100),
                 **{'delta_'+c:comp[c] for c in colsC}})
with (od/'P10AP_VSTAR_DELTAS.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator="\n");w.writeheader();w.writerows(rows)

ti={(r['functional'],int(r['time_step'])):r for r in baseT}
tj={(r['functional'],int(r['time_step'])):r for r in starT}
assert ti.keys()==tj.keys()
steps=[]
for k in ['j6','jpeak','jen']:
    for n in range(1,7):
        a,b=ti[(k,n)],tj[(k,n)]
        r={'functional':k,'time_step':n,'time_s':n*150}
        for c in colsC[:4]:
            r['delta_'+c]=num(b[c])-num(a[c])
        steps.append(r)
with (od/'P10AP_STEP_DELTAS.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(steps[0]),lineterminator="\n");w.writeheader();w.writerows(steps)
for rr in rows:
    k=rr['functional']
    x=sum(r['delta_total_mechanical_shape_per_m'] for r in steps if r['functional']==k)
    assert abs(x-rr['delta_total_mechanical_shape_per_m'])<3e-12
print('P10AP_REBUILD_OK functionals=3 step_rows=18 controls=OK')
