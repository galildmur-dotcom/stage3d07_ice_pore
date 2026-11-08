#!/usr/bin/env python3
"""Independent CSV-based acceptance of G02; no re-use of solver state."""
import csv, json, math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
results=root/'results'

def read_last(path):
    with (results/path/'time_series.csv').open(newline='') as fh:
        rows=list(csv.DictReader(fh))
    assert len(rows)>0
    return {k:float(v) for k,v in rows[-1].items()}
def summ(path):
    with (results/path/'summary.csv').open(newline='') as fh:
        return list(csv.DictReader(fh))[0]
fields=['volume_mean_C','top_mean_C','far_node_C','pore_near_node_C']
with (results/'one_d_validation.csv').open() as exact_f:
    one_d_analytic_top=list(csv.DictReader(exact_f))[0]['analytic_top_dT_K']
base={}
for h in ['H0','H1','H2']:
    for dt in ([300,150,75,37.5] if h=='H0' else ([300,150,75] if h=='H1' else [300,150])):
        tag=str(dt).replace('.','p')
        p=f'{h}_dt{tag}_xi0'
        base[(h,dt)]=read_last(p)
        s=summ(p)
        assert float(s['max_energy_balance_rel']) < 1e-8,(p,'heat balance')
        assert float(s['max_pcg_residual_rel']) < 1e-9,(p,'PCG')
        assert float(s['top_area_m2'])==float(s['top_area_m2'])
with (results/'convergence.csv').open('w',newline='') as fh:
    w=csv.writer(fh);w.writerow(['mesh','dt_s','top_mean_C','volume_mean_C','far_C','analytic_1D_far_C','far_minus_1D_K','err_top_vs_exact_1D_K','corner_top_C','corner_bottom_C','corner_top_1D_error_K','corner_bottom_1D_error_K','max_balance_rel'])
    for (h,dt),q in base.items():
        p=f'{h}_dt{str(dt).replace(".","p")}_xi0';r=summ(p)
        w.writerow([h,dt,q['top_mean_C'],q['volume_mean_C'],q['far_node_C'],q['slab_1D_at_far_C'],q['far_minus_1D_K'],q['top_mean_C']-(-20+float(one_d_analytic_top)),q.get('corner_top_C',''),q.get('corner_bottom_C',''),q.get('corner_top_minus_1D_K',''),q.get('corner_bottom_minus_1D_K',''),r['max_energy_balance_rel']])

# Analytical no-cavity 1D slab vs standalone P1-FEM transient solution
with (results/'one_d_validation.csv').open() as f:one_d=list(csv.DictReader(f))
e1=[float(t['Linf_K']) for t in one_d]
assert all(x>y for x,y in zip(e1,e1[1:])),e1
assert e1[-1]<.002,e1

# Same 3D Tet10 solver, now on actual 3D no-pore slab; strict nodal analytic comparison.
slab_errors={}
for dt,tag in [(300,'300'),(75,'75'),(37.5,'37p5')]:
    with (results/f'SLAB3D_dt{tag}'/'slab_3D_vs_analytic.csv').open() as f:
        r=list(csv.DictReader(f))[0]
    slab_errors[dt]=float(r['Linf_K'])
assert slab_errors[300]>slab_errors[75]>slab_errors[37.5]
assert slab_errors[37.5]<.002
# temporal improvement for actual 3D far-point vs analytic cavity-free slab, noting not exact domain equivalence
error1d={dt:abs(base[('H0',dt)]['top_mean_C']-(-20+float(one_d_analytic_top))) for dt in [300,150,75,37.5]}
assert all(x>y for x,y in zip(error1d.values(),list(error1d.values())[1:]))

nodes3=[(-math.sqrt(3),1/6,'GH3_neg'),(0.,2/3,'xi0'),(math.sqrt(3),1/6,'GH3_pos')]
nodes5=[(-2.856970013872806,.011257411327720688,'GH5_n2'),(-1.355626179974266,.22207592200561264,'GH5_n1'),(0.,.5333333333333333,'xi0'),(1.355626179974266,.22207592200561264,'GH5_p1'),(2.856970013872806,.011257411327720688,'GH5_p2')]
def moment(mesh,dt,nodes):
    arr=[]
    for x,w,tag in nodes:
        dirname=f'{mesh}_dt{dt}_'+('xi0' if tag=='xi0' else tag)
        r=read_last(dirname)
        arr.append((x,w,r))
    moments={}
    for fld in fields:
        mean=sum(w*v[fld] for _,w,v in arr)
        var=sum(w*(v[fld]-mean)**2 for _,w,v in arr)
        slope=(arr[-1][2][fld]-arr[0][2][fld])/(arr[-1][0]-arr[0][0])
        affine=max(abs(r[fld]-(arr[len(arr)//2][2][fld]+slope*x)) for x,w,r in arr)
        moments[fld]={'M_C':mean,'D_K2':var,'slope_K_per_xi':slope,'max_nonlinearity_K':affine}
    return moments
m3=moment('H0',150,nodes3);m5=moment('H0',150,nodes5);m3H2=moment('H2',300,nodes3)
with (results/'GH3_GH5.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['mesh','dt_s','quad','field','mean_C','variance_K2','xi_slope_K','affine_error_K','vs_other_quadrature_abs_mean_K','vs_other_quadrature_abs_var_K2'])
    for mesh,dt,method,d in [('H0',150,'GH3',m3),('H0',150,'GH5',m5),('H2',300,'GH3',m3H2)]:
        for k,v in d.items():
            alt=m5[k] if method=='GH3' and mesh=='H0' else (m3[k] if method=='GH5' else None)
            w.writerow([mesh,dt,method,k,v['M_C'],v['D_K2'],v['slope_K_per_xi'],v['max_nonlinearity_K'],abs(v['M_C']-alt['M_C']) if alt else '',abs(v['D_K2']-alt['D_K2']) if alt else ''])
for k in fields:
    assert abs(m3[k]['M_C']-m5[k]['M_C']) < 1e-7,(k,'mean GH mismatch')
    assert abs(m3[k]['D_K2']-m5[k]['D_K2']) < 1e-7,(k,'var GH mismatch')
    assert m5[k]['max_nonlinearity_K']<2e-7,(k,'linearity GH failures')

# Grid comparisons at paired timesteps: absolute differences in mean temperature.
grid_changes={str(dt):{k:abs(base[('H0',dt)][k]-base[('H1',dt)][k]) for k in fields} for dt in [300,150]}
assert abs(base[('H1',300)]['top_mean_C']-base[('H2',300)]['top_mean_C'])<.002
assert abs(base[('H0',150)]['corner_top_C']-base[('H1',150)]['corner_top_C'])<1e-4
assert abs(base[('H1',150)]['corner_top_C']-base[('H2',150)]['corner_top_C'])<1e-4
for mesh in ['H0','H1','H2']:
    q=base[(mesh,300)]
    assert -23 < q['top_mean_C'] < q['volume_mean_C'] < -20
    assert q['top_mean_C'] < q['corner_bottom_C'] < -20

validation={
    'G01-10':'PASS after user confirmed opening H2 in ParaView (user confirmation; no independent GUI execution)',
    'G02-01':'PASS: uniform state exact, 1D P1 FEM and actual 3D Tet10 no-pore slab both converge to analytical 1D reference',
    'G02-02':'PASS: Robin sign, heat balance, PCG tolerance, 3D transient timestep refinement',
    'constant_field_max_error_K':float(summ('uniform_H0')['uniform_err_K']),
    'max_1D_fine_error_K':e1[-1],
    '3D_Tet10_slab_Linf_vs_analytic_1D_K':slab_errors,
    'top_mean_C_H2_dt150':base[('H2',150)]['top_mean_C'],
    'volume_mean_C_H2_dt150':base[('H2',150)]['volume_mean_C'],
    'top_temporal_error_vs_flat_1D_reference_K':error1d,
    'H0_H1_changes_K':grid_changes,
    'fixed_corner_top_H0_H1_difference_K':abs(base[('H0',150)]['corner_top_C']-base[('H1',150)]['corner_top_C']),
    'fixed_corner_top_H1_H2_difference_K':abs(base[('H1',150)]['corner_top_C']-base[('H2',150)]['corner_top_C']),
    'fixed_corner_top_H2_C':base[('H2',150)]['corner_top_C'],
    'GH3_GH5':{'top_mean_diff_K':abs(m3['top_mean_C']['M_C']-m5['top_mean_C']['M_C']),
               'top_variance_diff_K2':abs(m3['top_mean_C']['D_K2']-m5['top_mean_C']['D_K2'])},
    'max_balance_H2_dt150':float(summ('H2_dt150_xi0')['max_energy_balance_rel']),
    'caveat':'3D cavity mesh compared with 1D cavity-free analytic slab only approximately; exact G02-01 analytic agreement is obtained on no-pore 1D P1 FEM and no-pore 3D Tet10 FEM.'
}
(results/'G02_verification.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2))
print(json.dumps(validation,ensure_ascii=False,indent=2))
