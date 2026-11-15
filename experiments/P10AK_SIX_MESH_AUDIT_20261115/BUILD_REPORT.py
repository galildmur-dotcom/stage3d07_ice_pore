#!/usr/bin/env python3
"""Reproduce the P10AK six-mesh gradient comparison from bundled primary CSVs.
Only Python stdlib is needed for CSV results. matplotlib is optional for figures.
No FEM execution, no Git changes, no access to users' absolute paths.
"""
from pathlib import Path
import csv, math, shutil, hashlib, zipfile, io
ROOT=Path(__file__).resolve().parent
IN=ROOT/'input'; OUT=ROOT/'derived'; OUT.mkdir(exist_ok=True)
SOURCE={
'W4B2':('P10W_ANALYTIC_ADJOINT_W4B2.csv','P10W_COMPONENTS_W4B2.csv','P10W_STEP_COMPONENTS_W4B2.csv',261091),
'W4B20':('P10W_ANALYTIC_ADJOINT_W4B20.csv','P10W_COMPONENTS_W4B20.csv','P10W_STEP_COMPONENTS_W4B20.csv',323052),
'W5B2':('P10W_ANALYTIC_ADJOINT_W5B2.csv','P10W_COMPONENTS_W5B2.csv','P10W_STEP_COMPONENTS_W5B2.csv',275549),
'W5B20':('P10W_ANALYTIC_ADJOINT_W5B20.csv','P10W_COMPONENTS_W5B20.csv','P10W_STEP_COMPONENTS_W5B20.csv',337365),
}
FS=('j6','jpeak','jen'); S=('W2B2','W2B20','W4B2','W4B20','W5B2','W5B20')

def read_csv(path):
 with path.open(newline='',encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def write_csv(path,records,cols):
 with path.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(records)

def parse():
 z={}
 for k,(g,c,t,n) in SOURCE.items():
  grads={r['functional']:r for r in read_csv(IN/g)}
  comps={r['functional']:r for r in read_csv(IN/c)}
  steps={(r['functional'],int(r['time_step'])):r for r in read_csv(IN/t)}
  assert len(grads)==3 and len(comps)==3 and len(steps)==18
  assert all(int(row['tet10'])==n for row in grads.values())
  z[k]={'grad':grads,'components':comps,'steps':steps,'tet10':n}
 old=read_csv(IN/'P10AC_FIVE_MESH_SERIES.csv')
 assert len(old)==15
 for r in old:
  k=r['mesh'].split('_P10')[0].removeprefix('H4')
  if k=='W2':k='W2B2'
  if k in z:
   assert math.isclose(float(r['D_R_per_m']),float(z[k]['grad'][r['functional']]['total_adjoint_per_m']),rel_tol=3e-15,abs_tol=1e-15)
 return z,old

def main():
 z,old=parse(); lookup={}
 for r in old:
  k=r['mesh'].split('_P10')[0].removeprefix('H4')
  if k=='W2':k='W2B2'
  lookup[k,r['functional']]={'J':float(r['J']),'D':float(r['D_R_per_m'])}
 for k in z:
  for f in FS:
   r=z[k]['grad'][f];lookup[k,f]={'J':float(r['objective']),'D':float(r['total_adjoint_per_m'])}
 assert len(lookup)==18
 nmesh={'W2B2':190222,'W2B20':292026,**{k:d['tet10'] for k,d in z.items()}}
 rows=[{'mesh':k,'tet10':nmesh[k],'functional':f,'J':f'{lookup[k,f]["J"]:.17g}','D_R_per_m':f'{lookup[k,f]["D"]:.17g}','provenance':('P10AC prior-five-mesh series' if k.startswith('W2') else 'primary P10W CSV')} for f in FS for k in S]
 write_csv(OUT/'P10AK_SIX_MESH_DERIVATIVES.csv',rows,['mesh','tet10','functional','J','D_R_per_m','provenance'])
 pairs=[('W2B2','W4B2','wall W2->W4 at B2'),('W4B2','W5B2','wall W4->W5 at B2'),('W2B20','W4B20','wall W2->W4 at B20'),('W4B20','W5B20','wall W4->W5 at B20'),('W2B2','W2B20','bulk B2->B20 at W2'),('W4B2','W4B20','bulk B2->B20 at W4'),('W5B2','W5B20','bulk B2->B20 at W5')]
 comps=[]
 for a,b,desc in pairs:
  for f in FS:
   aa,bb=lookup[a,f],lookup[b,f]
   comps.append({'from_mesh':a,'to_mesh':b,'comparison':desc,'functional':f,'delta_J':f'{bb["J"]-aa["J"]:.17g}','relative_delta_J_percent':f'{(bb["J"]-aa["J"])/aa["J"]*100:.12g}','delta_D_R_per_m':f'{bb["D"]-aa["D"]:.17g}','relative_delta_D_percent':f'{(bb["D"]-aa["D"])/aa["D"]*100:.12g}'})
 write_csv(OUT/'P10AK_GRID_COMPARISONS.csv',comps,list(comps[0]))
 interactions=[]
 for f in FS:
  walld2=lookup['W5B2',f]['D']-lookup['W4B2',f]['D']
  walld20=lookup['W5B20',f]['D']-lookup['W4B20',f]['D']
  bulk4=lookup['W4B20',f]['D']-lookup['W4B2',f]['D']
  bulk5=lookup['W5B20',f]['D']-lookup['W5B2',f]['D']
  interaction=walld20-walld2
  assert math.isclose(interaction,bulk5-bulk4,abs_tol=3e-16)
  interactions.append({'functional':f,'wall_W4_to_W5_B2':f'{walld2:.17g}','wall_W4_to_W5_B20':f'{walld20:.17g}','bulk_B2_to_B20_W4':f'{bulk4:.17g}','bulk_B2_to_B20_W5':f'{bulk5:.17g}','mixed_difference_per_m':f'{interaction:.17g}','mixed_difference_relative_to_W5B20_percent':f'{interaction/lookup["W5B20",f]["D"]*100:.10g}'})
 write_csv(OUT/'P10AK_MESH_INTERACTIONS.csv',interactions,list(interactions[0]))
 balance=[]
 for k in z:
  for f in FS:
   r=z[k]['grad'][f];c=z[k]['components'][f]
   total=float(r['total_adjoint_per_m']);mech=float(c['total_mechanical_shape_per_m']);thermal=float(c['thermal_adjoint_per_m'])
   msum=sum(float(c[q]) for q in ['explicit_objective_shape_per_m','equilibrium_residual_shape_per_m','internal_history_shape_per_m'])
   tsum=sum(float(z[k]['steps'][f,t]['total_mechanical_shape_per_m']) for t in range(1,7))
   step_component_resid=max(abs(sum(float(z[k]['steps'][f,t][q]) for q in ['explicit_objective_shape_per_m','equilibrium_residual_shape_per_m','internal_history_shape_per_m'])-float(z[k]['steps'][f,t]['total_mechanical_shape_per_m'])) for t in range(1,7))
   tol=2e-12
   assert max(abs(msum-mech),abs(tsum-mech),abs(total-mech-thermal),step_component_resid)<tol
   balance.append({'mesh':k,'functional':f,'mechanical_component_balance_abs':f'{abs(msum-mech):.17g}','mechanical_step_balance_abs':f'{abs(tsum-mech):.17g}','total_gradient_balance_abs':f'{abs(total-mech-thermal):.17g}','max_per_step_component_balance_abs':f'{step_component_resid:.17g}','accepted':1})
 write_csv(OUT/'P10AK_BALANCE_CHECKS.csv',balance,list(balance[0]))
 cpairs=[('W4B2','W5B2'),('W4B20','W5B20'),('W4B2','W4B20'),('W5B2','W5B20')]
 cols=['explicit_objective_shape_per_m','equilibrium_residual_shape_per_m','internal_history_shape_per_m','total_mechanical_shape_per_m','thermal_adjoint_per_m','total_adjoint_per_m']
 cr=[]; sr=[]
 for a,b in cpairs:
  for f in FS:
   vals={field:float(z[b]['components'][f][field])-float(z[a]['components'][f][field]) for field in cols}
   rec={'from_mesh':a,'to_mesh':b,'functional':f,**{x:f'{v:.17g}' for x,v in vals.items()},'component_abs_sum_to_total_delta_ratio':f'{sum(abs(vals[c]) for c in cols[:3]+cols[4:5])/abs(vals[cols[-1]]):.10g}' if vals[cols[-1]]!=0 else ''}
   cr.append(rec)
   for t in range(1,7):
    cur={'from_mesh':a,'to_mesh':b,'functional':f,'time_step':t,'time_s':150*t}
    for field in cols[:4]:cur[field]=f'{float(z[b]["steps"][f,t][field])-float(z[a]["steps"][f,t][field]):.17g}'
    sr.append(cur)
 write_csv(OUT/'P10AK_COMPONENT_DELTAS.csv',cr,list(cr[0]))
 write_csv(OUT/'P10AK_STEP_DELTAS.csv',sr,list(sr[0]))
 # Plots are not required for regeneration of the numeric tables.
 try:
  import matplotlib
  matplotlib.use('Agg')
  (ROOT/'figures').mkdir(exist_ok=True)  # figures are intentionally excluded from this text-only evidence subset
  import matplotlib.pyplot as plt
  plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
  xs=[2,4,5]
  fig,ax=plt.subplots(figsize=(8.4,4.8))
  for band in ['B2','B20']:
   ys=[lookup[f'W{w}{band}','jpeak']['D'] for w in xs]
   ax.plot(xs,ys,marker='o',label=band)
  ax.set_xlabel('Уровень пристеночного уточнения W');ax.set_ylabel(r'$D_R j_{peak}$, на м');ax.set_title('Производная jpeak: две серии B2 / B20');ax.grid(alpha=.25);ax.set_xticks(xs);ax.legend();fig.tight_layout();fig.savefig(ROOT/'figures'/'P10AK_JPEAK_B2_B20.png',dpi=170);plt.close(fig)
  fig,ax=plt.subplots(figsize=(8.5,4.9))
  for a,b in [('W4B2','W5B2'),('W4B20','W5B20')]:
   v=[float(z[b]['steps']['jpeak',t]['total_mechanical_shape_per_m'])-float(z[a]['steps']['jpeak',t]['total_mechanical_shape_per_m']) for t in range(1,7)]
   ax.plot([150*t for t in range(1,7)],v,marker='o',label=f'{a} → {b}')
  ax.axhline(0,linewidth=.8,color='0.4');ax.grid(alpha=.25);ax.set_xlabel('Время, с');ax.set_ylabel(r'$\Delta (D_R j_{peak})_{mech}$, на м');ax.set_title('Покомпонентная компенсация по времени: вклад механики');ax.legend();fig.tight_layout();fig.savefig(ROOT/'figures'/'P10AK_JPEAK_STEP_W4_W5.png',dpi=170);plt.close(fig)
 except ImportError:pass
 # Marker to machine-audit completeness, not an FDP proof.
 print('P10AK_SIX_MESH_AUDIT_OK meshes=6 functionals=3 base_meshes_with_step_components=4 component_pairs=4 max_balance_abs='+f'{max(float(v[q]) for v in balance for q in ["mechanical_component_balance_abs","mechanical_step_balance_abs","total_gradient_balance_abs","max_per_step_component_balance_abs"]):.12g}')

if __name__=='__main__':main()
