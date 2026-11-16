#!/usr/bin/env python3
"""Rebuild P10AX from verified P10AU historical rows and new P10AW H1 primary CSV.
Only postprocessing. No FEM, no change of original files, no inferred time histories.
"""
from __future__ import annotations
import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go

ROOT=Path(__file__).resolve().parent
IN=ROOT/'input'; OUT=ROOT/'derived'; FIG=ROOT/'figures'
OUT.mkdir(exist_ok=True);FIG.mkdir(exist_ok=True)
FUNS=('j6','jpeak','jen')
TIMES=(150,300,450,600,750,900)
COARSE=('H0','H1','H2','H3','H4')
FINE=('W2B2','W2B20','W4B2','W4B20','W4VSTAR','W5B2','W5B20')
ORDER=COARSE+FINE


def read(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))


def write(name, rows, fields):
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore',lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def check_close(label,a,b,tol=2e-11):
    if not math.isfinite(a) or not math.isfinite(b) or abs(a-b)>tol:
        raise ValueError(f'FAIL {label}: {a} != {b} [diff={a-b}]')

old_steps=read(IN/'P10AU_198_VERIFIED_STEP_COMPONENTS.csv')
old_final=read(IN/'P10AU_FINAL_DERIVATIVES_H1_MISSING.csv')
old_balance=read(IN/'P10AU_BALANCE_QA.csv')
geo={r['label']:r for r in read(IN/'P10AR_GEOMETRY_H0_H4.csv')}
h1_final=read(IN/'P10AW_H1_ANALYTIC_ADJOINT.csv')
h1_component=read(IN/'P10AW_H1_COMPONENTS.csv')
h1_steps=read(IN/'P10AW_H1_STEP_COMPONENTS.csv')
assert len(old_steps)==198 and len(old_final)==36 and len(old_balance)==33
assert len(h1_final)==len(h1_component)==3 and len(h1_steps)==18
assert {r['functional'] for r in h1_final}==set(FUNS)
assert {r['functional'] for r in h1_component}==set(FUNS)
assert {r['functional'] for r in h1_steps}==set(FUNS)
assert all(r['mesh']=='H1' for r in h1_final+h1_component+h1_steps)
assert all(r['geometry_derivative_method']=='ANALYTIC_TET10' for r in h1_final+h1_component+h1_steps)
assert all(r['law']=='EDV' and r['modulus']=='VAR' and r['mode']=='R' and int(r['steps'])==6 and float(r['dt_s'])==150 for r in h1_final)
assert all(int(r['pore_tri6'])==282 and int(r['tet10'])==19412 and int(r['nodes'])==27757 for r in h1_final)
assert int(geo['H1']['pore_tri6'])==282 and int(geo['H1']['tet10'])==19412
check_close('H1 pore median',float(h1_final[0]['pore_median_edge_mm']),float(geo['H1']['pore_median_edge_mm']),tol=1e-8)
assert all(int(r['adjoint_solve_count'])==18 and int(r['forward_solve_count'])==1 for r in h1_final)
sha={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in IN.glob('*.csv')}

h1_added=[]
for r in h1_steps:
    assert int(r['time_s']) in TIMES and int(r['time_s'])==int(r['time_step'])*150
    h1_added.append(dict(mesh_id='H1',mesh_name='H1',volume_variant='BASE',pore_tri6='282',tet10='19412',
       functional=r['functional'],time_step=r['time_step'],time_s=r['time_s'],
       explicit_per_m=r['explicit_objective_shape_per_m'],equilibrium_per_m=r['equilibrium_residual_shape_per_m'],
       history_per_m=r['internal_history_shape_per_m'],mechanical_step_per_m=r['total_mechanical_shape_per_m'],
       origin='P10AW_H1_PRIMARY_CSV_CHECKED',source_sha256=sha['P10AW_H1_STEP_COMPONENTS.csv'],
       source_path='P10AW_H1_STEP_COMPONENTS.csv'))

all_steps=old_steps+h1_added
all_steps.sort(key=lambda r:(int(r['pore_tri6']),r['mesh_id'],r['functional'],int(r['time_s'])))
assert len(all_steps)==216
assert len({(r['mesh_id'],r['functional'],r['time_s']) for r in all_steps})==216
write('P10AX_216_VERIFIED_STEP_COMPONENTS.csv',all_steps,list(all_steps[0]))

for r in old_final:
    if r['mesh_id']=='H1':
        fun=r['functional']
        fresh=next(x for x in h1_final if x['functional']==fun)
        assert not r['D_R_final_per_m']
        r['D_R_final_per_m']=fresh['total_adjoint_per_m']
        r['tet10']='19412'
        r['data_status']='P10AW_H1_NEW_PRIMARY_ANALYTIC_TET10'
        r['time_step_available']='1'
        r['source']='P10AW_H1_ANALYTIC_ADJOINT.csv'
    else:
        assert r['D_R_final_per_m']

final_map={(r['mesh_id'],r['functional']):r for r in old_final}
assert len(final_map)==36
write('P10AX_FINAL_DERIVATIVES_12_MESHES.csv',old_final,list(old_final[0]))

bykey=defaultdict(list)
for r in all_steps:bykey[(r['mesh_id'],r['functional'])].append(r)
assert len(bykey)==36
qa=[]
for (mesh,fun), rr in sorted(bykey.items()):
    assert len(rr)==6 and {int(x['time_s']) for x in rr}==set(TIMES)
    mech=math.fsum(float(x['mechanical_step_per_m']) for x in rr)
    part=math.fsum(float(x['explicit_per_m'])+float(x['equilibrium_per_m'])+float(x['history_per_m']) for x in rr)
    check_close(f'{mesh} {fun} sum parts',mech,part,tol=2e-10)
    final=float(final_map[mesh,fun]['D_R_final_per_m'])
    thermal=final-mech
    if mesh=='H1':
        ar=next(x for x in h1_final if x['functional']==fun)
        cr=next(x for x in h1_component if x['functional']==fun)
        check_close(f'H1 {fun} mech vs adjoint',mech,float(ar['mechanical_partial_per_m']))
        check_close(f'H1 {fun} thermal',thermal,float(ar['thermal_adjoint_per_m']))
        check_close(f'H1 {fun} total',final,float(ar['total_adjoint_per_m']))
        check_close(f'H1 {fun} components',mech,float(cr['total_mechanical_shape_per_m']))
        check_close(f'H1 {fun} partition',mech,float(cr['explicit_objective_shape_per_m'])+float(cr['equilibrium_residual_shape_per_m'])+float(cr['internal_history_shape_per_m']))
    else:
        q=next(x for x in old_balance if x['mesh_id']==mesh and x['functional']==fun)
        check_close(f'old {mesh} {fun} mech',mech,float(q['mechanical_sum_per_m']))
        check_close(f'old {mesh} {fun} total',final,float(q['final_D_R_per_m']))
    qa.append(dict(mesh_id=mesh,functional=fun,steps=6,mechanical_sum_per_m=f'{mech:.17g}',
       sum_components_per_m=f'{part:.17g}',mechanical_partition_residual_per_m=f'{part-mech:.17g}',
       thermal_per_m=f'{thermal:.17g}',final_D_R_per_m=f'{final:.17g}',
       balance_status='PASS_FULL_PRIMARY_CHECK' if mesh=='H1' else 'PASS_EXISTING_P10AU_CONFIRMED'))
write('P10AX_36_BALANCE_QA.csv',qa,list(qa[0]))

# H0-H4 numerical series: no interpolation and no convergence order claims.
coarse=[]
for mid in COARSE:
    rr=final_map[mid,'jpeak']
    coarse.append(dict(mesh=mid,pore_tri6=int(rr['pore_tri6']),tet10=int(geo[mid]['tet10']),
       pore_median_edge_mm=geo[mid]['pore_median_edge_mm'],
       sampled_max_radial_departure_um=geo[mid]['sampled_max_radial_departure_um'],
       area_Q6_vs_sphere_rel=geo[mid]['area_Q6_vs_sphere_rel'],
       D_R_j6_per_m=final_map[mid,'j6']['D_R_final_per_m'],
       D_R_jpeak_per_m=rr['D_R_final_per_m'],D_R_jen_per_m=final_map[mid,'jen']['D_R_final_per_m']))
write('P10AX_H0_H4_FULL_SERIES.csv',coarse,list(coarse[0]))

by_group=defaultdict(list)
for r in all_steps:by_group[(r['functional'],int(r['pore_tri6']),int(r['time_s']))].append(r)
spread=[]
for (fun,tri,t),rr in sorted(by_group.items()):
    vals=[float(x['mechanical_step_per_m']) for x in rr]
    spread.append(dict(functional=fun,pore_tri6=tri,time_s=t,mesh_count=len(rr),
       mesh_ids=';'.join(sorted(x['mesh_id'] for x in rr)),
       min_mechanical_per_m=f'{min(vals):.17g}',max_mechanical_per_m=f'{max(vals):.17g}',
       spread_mechanical_per_m=f'{max(vals)-min(vals):.17g}' if len(rr)>1 else '',
       spread_status='MEASURED_MULTIPLE_MESHES' if len(rr)>1 else 'NOT_IDENTIFIABLE_SINGLE_MESH'))
write('P10AX_TEMPORAL_SPREAD_BY_TRI6.csv',spread,list(spread[0]))
assert len(spread)==8*6*3  # 5 coarse surface counts and 3 fine surface counts

# Compare each consecutive coarse level; these vary in surface AND volume discretization.
comparisons=[]
for fun in FUNS:
    for lhs,rhs in zip(COARSE[:-1],COARSE[1:]):
        a=float(final_map[lhs,fun]['D_R_final_per_m']);b=float(final_map[rhs,fun]['D_R_final_per_m'])
        comparisons.append(dict(functional=fun,mesh_a=lhs,mesh_b=rhs,
                                D_R_a_per_m=f'{a:.17g}',D_R_b_per_m=f'{b:.17g}',
                                difference_per_m=f'{b-a:.17g}',difference_percent=f'{100*(b-a)/a:.17g}'))
write('P10AX_H0_H4_CONSECUTIVE_CHANGES.csv',comparisons,list(comparisons[0]))

# Reconstruct H0-H4 temporal changes on a common six-step clock.
coarse_jpeak=[]
for mesh in COARSE:
    for step in TIMES:
        r=next(x for x in all_steps if x['mesh_id']==mesh and x['functional']=='jpeak' and int(x['time_s'])==step)
        coarse_jpeak.append(dict(mesh=mesh,pore_tri6=r['pore_tri6'],time_s=step,
            mechanical_step_per_m=r['mechanical_step_per_m'],
            explicit_per_m=r['explicit_per_m'],equilibrium_per_m=r['equilibrium_per_m'],history_per_m=r['history_per_m']))
write('P10AX_H0_H4_JPEAK_TIME_COMPONENTS.csv',coarse_jpeak,list(coarse_jpeak[0]))

# FIGURES
plt.rcParams.update({'font.size':10,'axes.titlesize':12,'axes.labelsize':10,'figure.titlesize':13})
x=[int(r['pore_tri6']) for r in coarse]
fig, axes=plt.subplots(3,1,figsize=(9,10),sharex=True)
for ax,(fun,col,scale) in zip(axes,[('j6','D_R_j6_per_m',1),('jpeak','D_R_jpeak_per_m',1),('jen','D_R_jen_per_m',1)]):
    vals=[float(r[col])*scale for r in coarse]
    ax.plot(x,vals,marker='o',lw=1.7)
    ax.scatter([282],[vals[1]],marker='D',s=72,zorder=4,label='Новый расчёт H1')
    for xx,v,mid in zip(x,vals,COARSE):
        ax.annotate(mid,(xx,v),xytext=(5,6),textcoords='offset points',fontsize=9)
    ax.set_ylabel(fr'$D_R j_{{{fun if fun!="jpeak" else "peak"}}}$, м$^{{-1}}$')
    ax.grid(alpha=.32)
    if fun=='jpeak':ax.legend(loc='upper right',fontsize=9)
axes[-1].set_xscale('log')
axes[-1].set_xticks(x,[str(q) for q in x])
axes[-1].set_xlabel('Количество криволинейных Tri6 на поверхности поры')
fig.suptitle('Полная серия H0–H4: геометрические производные по радиусу поры')
fig.text(.5,.007,'Одновременно меняются поверхностные и объёмные сетки; это не чистая поверхностная сходимость',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.025,1,.97))
fig.savefig(FIG/'P10AX_H0_H4_ALL_THREE_DERIVATIVES.png',dpi=190)
fig.savefig(FIG/'P10AX_H0_H4_ALL_THREE_DERIVATIVES.svg')
plt.close(fig)

fig,ax=plt.subplots(figsize=(10,5.8))
for mid in COARSE:
    rr=sorted((r for r in all_steps if r['mesh_id']==mid and r['functional']=='jpeak'),key=lambda q:int(q['time_s']))
    ax.plot([int(r['time_s']) for r in rr],[float(r['mechanical_step_per_m']) for r in rr],marker='o',lw=1.8,label=f'{mid} · {rr[0]["pore_tri6"]} Tri6')
ax.axhline(0,color='gray',alpha=.6,lw=.8)
ax.set(xlabel='Время шага, с',ylabel=r'Вклад шага в механическую часть $D_Rj_{peak}$, м$^{-1}$',
       title='H0–H4: разложение итоговой производной по временным шагам')
ax.grid(alpha=.3);ax.legend(fontsize=9)
fig.tight_layout();fig.savefig(FIG/'P10AX_H0_H4_JPEAK_TIME_CURVES.png',dpi=190)
fig.savefig(FIG/'P10AX_H0_H4_JPEAK_TIME_CURVES.svg');plt.close(fig)

# Full graph: H0-H4 baseline and distinct volume variants for same pore Tri6.
fig,(ax,az)=plt.subplots(1,2,figsize=(13.8,5.7),gridspec_kw={'width_ratios':[1.08,1]})
for mid in COARSE:
    r=final_map[mid,'jpeak'];xx=int(r['pore_tri6']);yy=float(r['D_R_final_per_m'])
    ax.scatter([xx],[yy],marker='D' if mid=='H1' else 'o',s=64 if mid=='H1' else 34)
    ax.annotate(mid,(xx,yy),xytext=(5,5),textcoords='offset points',fontsize=9)
ax.plot(x,[float(final_map[mid,'jpeak']['D_R_final_per_m']) for mid in COARSE],lw=1.2)
ax.set_xscale('log');ax.set_xticks([136,282,494,866,1698],[136,282,494,866,1698]);ax.grid(alpha=.32)
ax.set(xlabel='Tri6 на поре',ylabel=r'$D_Rj_{peak}$, м$^{-1}$',title='Основная серия H0–H4')

markers={'B2':'o','B20':'s','VSTAR':'^'}
for mid in FINE:
    r=final_map[mid,'jpeak'];xx=int(r['pore_tri6']);yy=float(r['D_R_final_per_m'])
    kind='B20' if mid.endswith('B20') else 'VSTAR' if 'VSTAR' in mid else 'B2'
    az.scatter([xx],[yy],marker=markers[kind],s=55,label=f'{mid} · {r["tet10"]} Tet10')
for xx in [6636,19140,25758]:
    ys=[float(final_map[mid,'jpeak']['D_R_final_per_m']) for mid in FINE if int(final_map[mid,'jpeak']['pore_tri6'])==xx]
    az.plot([xx,xx],[min(ys),max(ys)],lw=2,zorder=0,alpha=.7)
az.set(xlabel='Tri6 на поре',title='Пристеночные варианты: разные объёмные сетки')
az.set_xticks([6636,19140,25758],['6 636','19 140','25 758']);az.grid(alpha=.32)
az.legend(loc='best',fontsize=7.7)
fig.suptitle(r'$D_R j_{peak}$: одно поверхностное разбиение допускает разные объёмные сетки')
fig.tight_layout();fig.savefig(FIG/'P10AX_JPEAK_SURFACE_WITH_VOLUME_SPREAD.png',dpi=190)
fig.savefig(FIG/'P10AX_JPEAK_SURFACE_WITH_VOLUME_SPREAD.svg');plt.close(fig)

# 3D observed time-step contributions (not derivative at variable final time).
fig=plt.figure(figsize=(12.5,8.5));ax=fig.add_subplot(111,projection='3d')
for mid in ORDER:
    rr=sorted((r for r in all_steps if r['mesh_id']==mid and r['functional']=='jpeak'),key=lambda q:int(q['time_s']))
    ax.plot([math.log10(int(r['pore_tri6'])) for r in rr],[int(r['time_s']) for r in rr],
        [float(r['mechanical_step_per_m']) for r in rr],marker='o',ms=3.1,lw=1.6,label=mid)
x_ticks=[136,282,494,866,1698,6636,19140,25758]
ax.set_xticks([math.log10(v) for v in x_ticks])
ax.set_xticklabels([str(v) for v in x_ticks],rotation=25)
ax.set(xlabel='Tri6 на поре (лог. шкала)',ylabel='Время шага, с',
       zlabel=r'Механический вклад шага в $D_Rj_{peak}$, м$^{-1}$',
       title='12 сеточных вариантов: поверхность × время × вклад производной')
ax.legend(loc='upper left',bbox_to_anchor=(0.01,.96),fontsize=8,ncol=2)
ax.view_init(elev=21,azim=-57)
fig.subplots_adjust(left=.03,right=.99,top=.93,bottom=.02)
fig.savefig(FIG/'P10AX_JPEAK_3D_12_MESHES.png',dpi=185,bbox_inches='tight');plt.close(fig)

# Interactive offline 3D by functional. Three choices, 12 trajectories each.
fig=go.Figure()
for fi,fun in enumerate(FUNS):
  for mid in ORDER:
    rr=sorted((r for r in all_steps if r['mesh_id']==mid and r['functional']==fun),key=lambda q:int(q['time_s']))
    fig.add_trace(go.Scatter3d(x=[int(r['pore_tri6']) for r in rr],
       y=[int(r['time_s']) for r in rr],
       z=[float(r['mechanical_step_per_m']) for r in rr],name=mid,
       mode='lines+markers',marker=dict(size=4),line=dict(width=4),
       text=[f'{mid}; {r["pore_tri6"]} Tri6; {r["tet10"]} Tet10; t={r["time_s"]} с; шаговой мех. вклад={float(r["mechanical_step_per_m"]):.10g}' for r in rr],
       hovertemplate='%{text}<extra></extra>',visible=(fi==1)))
buttons=[]
for i,fun in enumerate(FUNS):
  visibility=[j//len(ORDER)==i for j in range(3*len(ORDER))]
  buttons.append(dict(label=fun,method='update',args=[{'visible':visibility},
    {'title':f'P10AX: пошаговый механический вклад D_R {fun} — 12 сеток'}]))
fig.update_layout(title='P10AX: пошаговый механический вклад D_R jpeak — 12 сеток',
    scene=dict(xaxis=dict(title='Tri6 на поре',type='log'),yaxis=dict(title='Время шага, с'),
               zaxis=dict(title='Механический вклад, м⁻¹')),
    updatemenus=[dict(type='buttons',buttons=buttons,direction='right',x=.45,y=1.05)],
    width=1250,height=790,legend=dict(title='Сеточный вариант',orientation='v'))
fig.write_html(FIG/'P10AX_INTERACTIVE_3D_12_MESHES.html',include_plotlyjs=True,full_html=True)

print('P10AX_REBUILD_OK meshes=12 Tri6_levels=8 steps=216 functionals=3 balances=36')
print('H1_JPEAK=',final_map['H1','jpeak']['D_R_final_per_m'])
print('H1_JPEAK_STEP900=',next(r['mechanical_step_per_m'] for r in all_steps if r['mesh_id']=='H1' and r['functional']=='jpeak' and int(r['time_s'])==900))
