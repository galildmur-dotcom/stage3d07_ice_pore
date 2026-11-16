#!/usr/bin/env python3
"""P10AU: rebuild extended surface/volume/time comparison from P10AT and P10AS.
No FEM. Only primary verified rows; H4 and H4W2 duplicate variants retained in QA,
not treated as independent volume realizations. Missing H1 data is never imputed.
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
from mpl_toolkits.mplot3d import Axes3D  # noqa:F401

ROOT = Path(__file__).resolve().parent
IN = ROOT/'input'
OUT=ROOT/'derived'
FIG=ROOT/'figures'
OUT.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
FUNCTIONALS=('j6','jpeak','jen')
STEPS=(150,300,450,600,750,900)
NEW_ID={
 'H0':('H0','H0',136,7388,'BASE'),
 'H2':('H2','H2',494,50486,'BASE'),
 'H3':('H3','H3',866,81891,'BASE'),
 'H4':('H4','H4',1698,164319,'BASE'),
 'H4W2':('W2B2','H4W2',6636,190222,'B2'),
 'H4W2B20':('W2B20','H4W2B20',6636,292026,'B20'),
}
# use direct P10W forward/adjoint runs before their separate P10Y postprocessing copies
RUN_HINTS={
 'H0':'P10W_H0_R_FULL_',
 'H2':'P10W_H2_R_SPATIAL_',
 'H3':'P10W_H3_R_FULL_',
 'H4':'P10W_H4_R_FULL_',
 'H4W2':'P10W_H4W2_R_SPATIAL_FULL_',
 'H4W2B20':'P10W_H4W2B20_R_SPATIAL_',
}

def read(name):
 with (IN/name).open('r',newline='',encoding='utf-8-sig') as f:
  return list(csv.DictReader(f))

def write(name, rows, fields):
 with (OUT/name).open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore', lineterminator='\n')
  w.writeheader(); w.writerows(rows)

def f(x):return float(x)

def check_close(x,y,abs_tol=3e-9):
 assert abs(x-y) <= abs_tol, (x,y,x-y)

verified=read('P10AT_VERIFIED_STEPS.csv')
existing=read('P10AS_PRIMARY_STEP_SERIES.csv')
finals=read('P10AS_FINAL_DERIVATIVES_ALL.csv')
geometry=read('P10AR_GEOMETRY_H0_H4.csv')
reference=read('P10AR_DERIVATIVES_VS_TRI6.csv')
geo={r['label']:r for r in geometry}
ref={r['mesh']:r for r in reference}
assert len(verified)==144 and len(existing)==90
assert {r['mesh'] for r in verified}==set(NEW_ID)
assert {r['mesh_id'] for r in existing}=={'W4B2','W4B20','W4VSTAR','W5B2','W5B20'}

byrun=defaultdict(list)
for r in verified: byrun[(r['mesh'],r['source_sha256'])].append(r)
qa_duplicates=[]
selected=[]
for mesh in NEW_ID:
 runs=[(sha,rows) for (m,sha),rows in byrun.items() if m==mesh]
 assert runs
 # exactly one canonical original P10W run per mesh
 src=[(sha,rows) for sha,rows in runs if RUN_HINTS[mesh] in rows[0]['source_path']]
 assert len(src)==1,(mesh,len(src))
 sha,rows=src[0]
 assert len(rows)==18
 selected.extend(rows)
 if len(runs)>1:
  a={(r['functional'],int(r['time_step'])):r for r in rows}
  for other_sha,other in runs:
   if other_sha==sha:continue
   b={(r['functional'],int(r['time_step'])):r for r in other}
   assert a.keys()==b.keys()
   for field in ('explicit_objective_shape_per_m','equilibrium_residual_shape_per_m','internal_history_shape_per_m','total_mechanical_shape_per_m'):
    md=max(abs(f(a[k][field])-f(b[k][field])) for k in a)
    assert md < 3e-10,(mesh,field,md)
    qa_duplicates.append({'mesh':mesh,'chosen_sha256':sha,'alternate_sha256':other_sha,'component':field,'maximum_abs_difference_per_m':f'{md:.17g}', 'interpretation':'ROUND_OFF_LEVEL_REPLAY_NOT_INDEPENDENT_VOLUME_MESH'})
assert len(selected)==108
write('P10AU_DUPLICATE_RUN_QA.csv',qa_duplicates,['mesh','chosen_sha256','alternate_sha256','component','maximum_abs_difference_per_m','interpretation'])

combined=[]
for r in selected:
 mesh=r['mesh'];mid,name,tri,tet,var=NEW_ID[mesh]
 assert int(r['time_s']) in STEPS and r['geometry_derivative_method']=='ANALYTIC_TET10'
 if mesh in geo:
  assert int(geo[mesh]['pore_tri6'])==tri
  assert int(geo[mesh]['tet10'])==tet
 combined.append({'mesh_id':mid,'mesh_name':name,'volume_variant':var,'pore_tri6':tri,'tet10':tet,
   'functional':r['functional'],'time_step':r['time_step'],'time_s':r['time_s'],
   'explicit_per_m':r['explicit_objective_shape_per_m'],
   'equilibrium_per_m':r['equilibrium_residual_shape_per_m'],
   'history_per_m':r['internal_history_shape_per_m'],
   'mechanical_step_per_m':r['total_mechanical_shape_per_m'],
   'origin':'P10AT_VERIFIED_WITH_P10W_ADJOINT',
   'source_sha256':r['source_sha256'],'source_path':r['source_path']})
for r in existing:
 combined.append({'mesh_id':r['mesh_id'],'mesh_name':r['mesh_name'],'volume_variant':r['volume_variant'],
  'pore_tri6':r['pore_tri6'],'tet10':r['tet10'],'functional':r['functional'],
  'time_step':r['time_step'],'time_s':r['time_s'],'explicit_per_m':r['explicit_per_m'],
  'equilibrium_per_m':r['equilibrium_per_m'],'history_per_m':r['history_per_m'],
  'mechanical_step_per_m':r['mechanical_step_per_m'],'origin':'P10AS_PRIMARY_STEP_COMPONENT',
  'source_sha256':'REFER_TO_P10AS_SOURCE_ARCHIVE','source_path':'P10AS_PRIMARY_STEP_SERIES.csv'})
combined.sort(key=lambda r:(int(r['pore_tri6']),r['mesh_id'],r['functional'],int(r['time_s'])))
assert len(combined)==198
fields=list(combined[0].keys())
write('P10AU_198_VERIFIED_STEP_COMPONENTS.csv',combined,fields)

# Sum each mechanical contribution and verify algebraic decomposition
bykey=defaultdict(list)
for r in combined:
 bykey[(r['mesh_id'],r['functional'])].append(r)
assert len(bykey)==33
qa=[]
final_map={(r['mesh_id'],r['functional']):r for r in finals if r['D_R_final_per_m']}
for (mid,fun),rows in bykey.items():
 assert len(rows)==6 and {int(r['time_s']) for r in rows}==set(STEPS)
 mechanic=sum(f(r['mechanical_step_per_m']) for r in rows)
 parts=sum(f(r['explicit_per_m'])+f(r['equilibrium_per_m'])+f(r['history_per_m']) for r in rows)
 check_close(mechanic,parts,abs_tol=1e-10)
 ref_row=final_map[(mid,fun)]
 final=f(ref_row['D_R_final_per_m'])
 qa.append({'mesh_id':mid,'functional':fun,'steps':6,'mechanical_sum_per_m':f'{mechanic:.17g}',
  'sum_components_per_m':f'{parts:.17g}', 'mechanical_partition_residual_per_m':f'{parts-mechanic:.17g}',
  'final_D_R_per_m':f'{final:.17g}',
  'thermal_implied_by_final_minus_mechanical_per_m':f'{final-mechanic:.17g}',
  'final_source':ref_row['source']})
write('P10AU_BALANCE_QA.csv',qa,list(qa[0]))

# Surface grouping counts: no inferred spread for singleton groups.
groups=defaultdict(list)
for r in combined:
 groups[(r['functional'],int(r['pore_tri6']),int(r['time_s']))].append(r)
assert len(groups)==126
spread=[]
for (fun,tri,t),rr in sorted(groups.items()):
 vals=[f(x['mechanical_step_per_m']) for x in rr]
 cnt=len(vals)
 spread.append({'functional':fun,'pore_tri6':tri,'time_s':t,'mesh_count':cnt,
  'mesh_ids':';'.join(x['mesh_id'] for x in sorted(rr,key=lambda x:x['mesh_id'])),
  'min_mechanical_per_m':f'{min(vals):.17g}', 'max_mechanical_per_m':f'{max(vals):.17g}',
  'spread_mechanical_per_m':f'{max(vals)-min(vals):.17g}' if cnt>1 else '',
  'spread_status':'MEASURED_RANGE_MULTIPLE_MESHES' if cnt>1 else 'NOT_IDENTIFIABLE_SINGLE_MESH'})
write('P10AU_TIME_SURFACE_VOLUME_SPREAD.csv',spread,list(spread[0]))

# signed comparisons to a concrete B2 reference, not a fitted continuous surface.
for_ref=defaultdict(list)
for r in combined:
 for_ref[(r['functional'],int(r['pore_tri6']),int(r['time_s']))].append(r)
ref_ids={6636:'W2B2',19140:'W4B2',25758:'W5B2'}
signed=[]
for (fun,tri,t),rr in sorted(for_ref.items()):
 if tri not in ref_ids:continue
 baselines=[x for x in rr if x['mesh_id']==ref_ids[tri]]
 assert len(baselines)==1
 base=f(baselines[0]['mechanical_step_per_m'])
 for r in rr:
  if r['mesh_id']==ref_ids[tri]: continue
  signed.append({'functional':fun,'pore_tri6':tri,'time_s':t,'baseline_mesh_id':ref_ids[tri],
                 'mesh_id':r['mesh_id'],'delta_mechanical_per_m':f'{f(r["mechanical_step_per_m"])-base:.17g}'})
assert len(signed)==(1+2+1)*6*3
write('P10AU_SIGNED_DIFFERENCES_FROM_B2.csv',signed,list(signed[0]))

# scientific plots
plt.rcParams.update({'font.size':11,'axes.titlesize':13,'axes.labelsize':11,'figure.titlesize':14})
mesh_order=['H0','H2','H3','H4','W2B2','W2B20','W4B2','W4B20','W4VSTAR','W5B2','W5B20']
palette={mid:plt.cm.tab20(i/20) for i,mid in enumerate(mesh_order)}
styles={'BASE':'-','B2':'-','B20':'--','VSTAR':':' }

def meshvals(mid,fun='jpeak'):
 rows=[r for r in combined if r['mesh_id']==mid and r['functional']==fun]
 return sorted(rows,key=lambda r:int(r['time_s']))

# Full spectrum of time-step contributions (coarse series)
fig,ax=plt.subplots(figsize=(9,5.5))
for mid in mesh_order[:4]:
 a=meshvals(mid)
 ax.plot([int(r['time_s']) for r in a],[f(r['mechanical_step_per_m']) for r in a],marker='o',lw=2,label=f'{mid} · {a[0]["pore_tri6"]} Tri6')
ax.set(xlabel='Время шага, с',ylabel=r'Вклад шага в механическое $D_R j_{peak}$, м$^{-1}$', title='Грубые сетки: временные вклады в итоговую производную')
ax.axhline(0,color='gray',alpha=.6,lw=.8);ax.grid(alpha=.3);ax.legend(fontsize=9)
fig.tight_layout();fig.savefig(FIG/'P10AU_JPEAK_COARSE_TIME_CURVES.png',dpi=185);plt.close(fig)

# Fine time-step contributions group; only small variations, offsets and color by mesh
fig,ax=plt.subplots(figsize=(10,5.5))
for mid in mesh_order[4:]:
 a=meshvals(mid)
 ax.plot([int(r['time_s']) for r in a],[f(r['mechanical_step_per_m']) for r in a],marker='o',lw=1.5,label=f'{mid} ({a[0]["pore_tri6"]})')
ax.set(xlabel='Время шага, с',ylabel=r'Вклад шага в механическое $D_R j_{peak}$, м$^{-1}$', title='Пристеночные сетки W2/W4/W5: временные вклады')
ax.axhline(0,color='gray',alpha=.6,lw=.8);ax.grid(alpha=.3);ax.legend(fontsize=8,ncol=2)
fig.tight_layout();fig.savefig(FIG/'P10AU_JPEAK_FINE_TIME_CURVES.png',dpi=185);plt.close(fig)

# 3D traces including all mesh variants
fig=plt.figure(figsize=(12,8))
ax=fig.add_subplot(111,projection='3d')
for mid in mesh_order:
 a=meshvals(mid)
 x=[math.log10(int(r['pore_tri6'])) for r in a]
 y=[int(r['time_s']) for r in a]
 z=[f(r['mechanical_step_per_m']) for r in a]
 line,=ax.plot(x,y,z,marker='o',ms=3.8,lw=1.65,label=mid)
ax.set_xticks([math.log10(x) for x in [136,494,866,1698,6636,19140,25758]])
ax.set_xticklabels(['136','494','866','1698','6636','19140','25758'],rotation=20)
ax.set(xlabel='Tri6 на поре (лог. шкала)',ylabel='Время шага, с',zlabel=r'Вклад шага в $D_R j_{peak}$, м$^{-1}$',
       title='11 согласованных расчётов: поверхность × объём × временной вклад')
ax.view_init(elev=21,azim=-57)
ax.legend(loc='upper left',bbox_to_anchor=(0.01,.95),fontsize=8,ncol=2)
fig.subplots_adjust(left=.03,right=.99,top=.93,bottom=.03)
fig.savefig(FIG/'P10AU_JPEAK_3D_ALL_MESHES.png',dpi=190,bbox_inches='tight');plt.close(fig)

# W2/W4/W5 measured spread heatmap, only groups with more than one volume option
x=STEPS;y=[6636,19140,25758]
Z=np.array([[float(next(z['spread_mechanical_per_m'] for z in spread if z['functional']=='jpeak' and z['pore_tri6']==n and z['time_s']==t))*1e6 for t in x] for n in y])
fig,ax=plt.subplots(figsize=(9,4.5));im=ax.imshow(Z,aspect='auto',cmap='viridis')
ax.set_xticks(range(6),[str(q) for q in x]);ax.set_yticks(range(3),[f'{q:,}'.replace(',',' ') for q in y]);ax.set(xlabel='Время, с',ylabel='Tri6 на поверхности поры',title='Разброс между объёмными вариантами при фиксированной поверхности')
for i in range(3):
 for j in range(6):
  ax.text(j,i,f'{Z[i,j]:.1f}',ha='center',va='center',color='white' if Z[i,j]<Z.max()*.55 else 'black',fontsize=9)
cbar=fig.colorbar(im,ax=ax);cbar.set_label(r'Разброс пошагового механического вклада, $10^{-6}$ м$^{-1}$')
fig.tight_layout();fig.savefig(FIG/'P10AU_JPEAK_SPREAD_HEATMAP_W2_W4_W5.png',dpi=190);plt.close(fig)

# final derivatives (H1 geometry known but no D_R) - plot all available mesh variants
fig,ax=plt.subplots(figsize=(10,5.7))
lookup={(r['mesh_id'],r['functional']):r for r in finals if r['D_R_final_per_m']}
for mid in mesh_order:
 r=lookup[(mid,'jpeak')]
 n=int(r['pore_tri6']); v=f(r['D_R_final_per_m'])
 marker=('s' if mid.endswith('B20') else '^' if 'VSTAR' in mid else 'o')
 ax.scatter(n,v,s=68,label=mid,marker=marker,zorder=3)
ax.set_xscale('log');ax.set_xticks([136,282,494,866,1698,6636,19140,25758],[136,282,494,866,1698,6636,19140,25758])
ax.set(xlabel='Количество Tri6 на поре',ylabel=r'Полная $D_R j_{peak}$, м$^{-1}$',title='Итоговая производная: несколько объёмных вариантов при одном Tri6')
ax.grid(alpha=.3);ax.legend(fontsize=8,ncol=3)
fig.tight_layout();fig.savefig(FIG/'P10AU_JPEAK_FINAL_VS_SURFACE.png',dpi=190);plt.close(fig)

# signed changes relative to B2, showing time/surface/volume effect
fig=plt.figure(figsize=(11,7.5));ax=fig.add_subplot(111,projection='3d')
for mid in ['W2B20','W4B20','W4VSTAR','W5B20']:
 a=[r for r in signed if r['functional']=='jpeak' and r['mesh_id']==mid]
 a=sorted(a,key=lambda r:int(r['time_s']))
 x=[math.log10(r['pore_tri6']) for r in a]
 yy=[int(r['time_s']) for r in a]
 zz=[f(r['delta_mechanical_per_m'])*1e6 for r in a]
 ax.plot(x,yy,zz,marker='o',lw=2,label=mid)
ax.set_xticks([math.log10(n) for n in [6636,19140,25758]],['6636','19140','25758'])
ax.set(xlabel='Tri6 на поре',ylabel='Время шага, с',zlabel=r'Разность к B2, $10^{-6}$ м$^{-1}$',title='Временная разница объёмных вариантов относительно B2')
ax.view_init(elev=20,azim=-55);ax.legend(loc='upper left',bbox_to_anchor=(0,1),fontsize=8)
fig.subplots_adjust(left=.03,right=.99,top=.93,bottom=.03)
fig.savefig(FIG/'P10AU_JPEAK_3D_SIGNED_DIFFERENCES.png',dpi=190,bbox_inches='tight');plt.close(fig)

# Interactive offline HTML; all 11 mesh trajectories for each functional with dropdown.
try:
 import plotly.graph_objects as go
 fig=go.Figure()
 for fun in FUNCTIONALS:
  for mid in mesh_order:
   a=meshvals(mid,fun)
   fig.add_trace(go.Scatter3d(x=[int(r['pore_tri6']) for r in a],y=[int(r['time_s']) for r in a],
      z=[f(r['mechanical_step_per_m']) for r in a],mode='lines+markers',name=mid,
      visible=(fun=='jpeak'),marker={'size':3},line={'width':3},
      hovertemplate='Tri6: %{x}<br>Шаг: %{y} с<br>Вклад: %{z:.10f} м⁻¹<extra>'+mid+'</extra>'))
 buttons=[]
 for fun in FUNCTIONALS:
  visible=[f == fun for f in FUNCTIONALS for m in mesh_order]
  buttons.append({'label':fun,'method':'update','args':[{'visible':visible},{'title':f'P10AU · пошаговые механические вклады {fun} · 11 сеток'}]})
 fig.update_layout(title='P10AU · пошаговые механические вклады jpeak · 11 сеток',
   scene={'xaxis_title':'Tri6 на поре','yaxis_title':'Время, с','zaxis_title':'Шаговый вклад, м⁻¹',
          'xaxis':{'type':'log'}},
   updatemenus=[{'type':'dropdown','buttons':buttons,'x':0,'y':1.05}],
   margin={'l':0,'r':0,'b':0,'t':90},legend={'x':0.8,'y':0.9})
 fig.write_html(FIG/'P10AU_INTERACTIVE_3D_ALL_FUNCTIONALS.html',include_plotlyjs=True,full_html=True)
 html_status='CREATED_OFFLINE'
except ImportError:html_status='PLOTLY_NOT_AVAILABLE'

lines=[]
lines.append('P10AU_REBUILD_OK')
lines.append('VERIFIED_ORIGINAL_STEP_FILES=8')
lines.append('CANONICAL_HISTORICAL_MESHES=6')
lines.append('EXISTING_P10AS_MESHES=5')
lines.append('TOTAL_DISTINCT_MESHES=11')
lines.append('TOTAL_STEP_ROWS=198')
lines.append('SURFACE_LEVELS_WITH_STEPS=7')
lines.append('H1_COMPARABLE_D_R=NOT_CALCULATED')
lines.append('DUPLICATE_RUNS_H4_H4W2=ROUND_OFF_LEVEL_NOT_VOLUME_VARIANTS')
lines.append('MEANING_OF_TIME=CONTRIBUTIONS_TO_FINAL_900S_DERIVATIVE_NOT_D_R_J(t)')
lines.append('SPREAD_FOR_ONE_MESH=NOT_ESTIMABLE')
lines.append('3D_HTML='+html_status)
for n in y:
 h=[r for r in spread if r['functional']=='jpeak' and int(r['pore_tri6'])==n]
 peak=max(h,key=lambda r:float(r['spread_mechanical_per_m']))
 lines.append(f'JPEAK_MAX_STEP_SPREAD_TRI6_{n}={peak["spread_mechanical_per_m"]} AT_TIME_S={peak["time_s"]} MESHES={peak["mesh_ids"]}')
(ROOT/'VERIFY.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
