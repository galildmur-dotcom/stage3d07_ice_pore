#!/usr/bin/env python3
"""Rebuild P10AA tables and figures from embedded, timestamped primary/archive records.
No FEM calls. Run: python tools/rebuild.py [--no-figures]
"""
from pathlib import Path
import argparse,csv,math,collections
ROOT=Path(__file__).resolve().parents[1]
NAMES=['H0','H2','H3','H4','H4W2','H4W2B20','H4W4B2']
FUNCTIONS=['j6','jpeak','jen']
EDGES={'H0':.4523727752,'H2':.2457370843,'H3':.186181392389,'H4':.133149100938,
       'H4W2':.0672051980254,'H4W2B20':.0672051980254,'H4W4B2':.039376064622480653}
TETS={'H0':7388,'H2':50486,'H3':81891,'H4':164319,'H4W2':190222,'H4W2B20':292026,'H4W4B2':261091}
TRANSITIONS=[('H0','H2','global'),('H2','H3','global'),('H3','H4','global'),
 ('H4','H4W2','near_wall'),('H4W2','H4W2B20','bulk'),('H4W2','H4W4B2','near_wall_plus_band'),
 ('H4W2B20','H4W4B2','different_refinement_paths')]
def readcsv(name):
 with (ROOT/'input'/name).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writetable(name,rows,cols):
 p=ROOT/'derived'/name
 with p.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(rows)
def form(x):return format(x,'.17g')
def main(figures=True):
 legacy=readcsv('p10w_h0_h2_h3_from_sop.csv')
 previous=readcsv('p10w_four_mesh_archive.csv')
 primary=readcsv('p10w_h4w4b2_primary_adjoint.csv')
 components=readcsv('p10w_h4w4b2_primary_components.csv')
 assert len(legacy)==9 and len(previous)==12 and len(primary)==3 and len(components)==3
 assert {r['functional'] for r in primary}==set(FUNCTIONS)
 vals={}
 for r in legacy+previous:
  key=(r['mesh'],r['functional']); assert key not in vals,(key,'duplicate')
  vals[key]={'J':float(r['J']),'D':float(r['D_R_per_m']),
             'source':'SOP_snapshot' if r in legacy else r['source']}
 for r in primary:
  key=('H4W4B2',r['functional']); prev=vals[key]
  assert math.isclose(prev['J'],float(r['objective']),abs_tol=1.e-14,rel_tol=0)
  assert math.isclose(prev['D'],float(r['total_adjoint_per_m']),abs_tol=1.e-13,rel_tol=0)
  vals[key]={'J':float(r['objective']),'D':float(r['total_adjoint_per_m']),
             'source':'new_primary_csv_20261113'}
  assert r['geometry_derivative_method']=='ANALYTIC_TET10' and r['mode']=='R'
  assert r['law']=='EDV' and r['modulus']=='VAR' and r['steps']=='6' and r['dt_s']=='150'
  assert r['mesh']=='H4W4B2' and int(r['tet10'])==TETS['H4W4B2']
  assert math.isclose(float(r['mechanical_partial_per_m'])+float(r['thermal_adjoint_per_m']),
                      float(r['total_adjoint_per_m']),abs_tol=1.e-13)
 for r in components:
  ps=sum(float(r[k]) for k in ['explicit_objective_shape_per_m','equilibrium_residual_shape_per_m','internal_history_shape_per_m'])
  assert math.isclose(ps,float(r['total_mechanical_shape_per_m']),abs_tol=1e-12)
  p=next(x for x in primary if x['functional']==r['functional'])
  assert math.isclose(float(r['total_adjoint_per_m']),float(p['total_adjoint_per_m']),abs_tol=1e-12)
 assert len(vals)==21
 # nearest-wall independently measured q3 features; q4 numbers not used in this table
 geom={}
 for fname in ['p10z_baseline_shell_qp.csv','p10z_refined_shell_qp.csv']:
  for r in readcsv(fname):
   if int(r['quadrature_order'])==3 and int(r['shell'])==0:
    assert r['mesh'] not in geom
    geom[r['mesh']]=r
 assert set(geom)=={'H4','H4W2','H4W2B20','H4W4B2'},set(geom)
 rows=[]
 for mesh in NAMES:
  for f in FUNCTIONS:
   v=vals[mesh,f];g=geom.get(mesh,{})
   rows.append({'mesh':mesh,'functional':f,'J':form(v['J']),'D_R_per_m':form(v['D']),
     'pore_edge_median_mm':form(EDGES[mesh]),'tet10':TETS[mesh],
     'qp27_first_shell':g.get('qp_count',''),
     'median_radial_span_first_shell_mm':g.get('radial_node_span_p50_mm',''),
     'provenance':v['source']})
 writetable('P10AA_R_SEVEN_MESH_SERIES.csv',rows,list(rows[0]))
 comp=[]
 for a,b,kind in TRANSITIONS:
  for f in FUNCTIONS:
   x=vals[a,f];y=vals[b,f]
   deltaJ=y['J']-x['J'];deltaD=y['D']-x['D']
   comp.append({'start_mesh':a,'end_mesh':b,'refinement_type':kind,'functional':f,
    'delta_J':form(deltaJ),'relative_delta_J_percent':form(100*deltaJ/x['J']),
    'delta_D_per_m':form(deltaD),'relative_delta_D_percent':form(100*deltaD/x['D']),
    'abs_relative_derivative_change_over_objective_change':form(abs((deltaD/x['D'])/(deltaJ/x['J']))) if deltaJ!=0 else '',
    'is_continuum_error_bound':'NO'})
 writetable('P10AA_COMPARISONS.csv',comp,list(comp[0]))
 # exact components from primary H4W4 and earlier H4W2 from original numeric P10W archived evidence file
 old={'explicit_objective_shape_per_m':-9.809479545789413,
      'equilibrium_residual_shape_per_m':10.538196453192576,
      'internal_history_shape_per_m':1.574311436787695,
      'thermal_adjoint_per_m':.059834534623766}
 new=next(r for r in components if r['functional']=='jpeak')
 changes=[]
 for k in old:
  n=float(new[k]);o=old[k]
  changes.append({'component':k,'H4W2_per_m':form(o),'H4W4B2_per_m':form(n),'delta_per_m':form(n-o)})
 writetable('P10AA_JPEAK_COMPONENT_CHANGE.csv',changes,list(changes[0]))
 total_delta=sum(float(r['delta_per_m']) for r in changes)
 full_diff=vals['H4W4B2','jpeak']['D']-vals['H4W2','jpeak']['D']
 assert math.isclose(total_delta,full_diff,abs_tol=1e-12), (total_delta,full_diff)
 total_component_abs=sum(abs(float(r['delta_per_m'])) for r in changes)
 # required scientific numerical invariants
 d1=vals['H4W2','jpeak']['D']-vals['H4','jpeak']['D']
 d2=vals['H4W4B2','jpeak']['D']-vals['H4W2','jpeak']['D']
 d_bulk=vals['H4W2B20','jpeak']['D']-vals['H4W2','jpeak']['D']
 assert d1>0 and d2>0 and d_bulk<0
 assert vals['H3','jpeak']['D']<vals['H2','jpeak']['D']
 assert vals['H3','jpeak']['D']<vals['H4','jpeak']['D']
 verification=[
  'P10AA_CONSISTENCY_OK 7_meshes=1 functionals=3 rows=21 transitions=7',
  'P10AA_LAST_H4W4B2_PRIMARY_MATCH_OK objective_and_derivative=1 analytic_tet10=1',
  f'P10AA_JPEAK_WALL_DELTAS  H4_to_H4W2={d1:.15g} H4W2_to_H4W4B2={d2:.15g} ratio={abs(d1/d2):.9f}',
  f'P10AA_JPEAK_BULK_DELTA  H4W2_to_H4W2B20={d_bulk:.15g} wall_to_bulk_abs_ratio={abs(d2/d_bulk):.9f}',
  f'P10AA_JPEAK_COMPONENT_DELTA_SUM_CHECK delta_full={full_diff:.17g} sum_parts={total_delta:.17g} abs_parts={total_component_abs:.17g} cancellation_abs_over_net={total_component_abs/abs(full_diff):.8f}',
  'P10AA_CONVERGENCE_PROOF=NO',
  'P10AA_NOTE=Do not infer Richardson order or exact error bounds from mixed non-nested mesh families.',
 ]
 (ROOT/'derived/P10AA_VERIFICATION.txt').write_text('\n'.join(verification)+'\n',encoding='utf-8')
 if figures:
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  from matplotlib.ticker import FormatStrFormatter
  names=['H0','H2','H3','H4','H4W2','H4W4B2']
  fig,ax=plt.subplots(figsize=(9.3,5.6))
  wall=[EDGES[m] for m in names]
  ds=[vals[m,'jpeak']['D'] for m in names]
  ax.plot(wall,ds,'o-',lw=1.6,ms=6,label='General and near-wall refinement')
  b='H4W2B20';ax.scatter([EDGES[b]],[vals[b,'jpeak']['D']],marker='s',s=82,label='Extra bulk refinement')
  for m,x,y in zip(names,wall,ds):
   ax.annotate(m,(x,y),xytext=(5,6),textcoords='offset points',fontsize=9)
  ax.annotate(b,(EDGES[b],vals[b,'jpeak']['D']),xytext=(10,-17),textcoords='offset points',fontsize=9)
  ax.set_xscale('log');ax.invert_xaxis();ax.set_xticks([.04,.067205,.133149,.186181,.245737,.45237]);ax.set_xticklabels(['0.040','0.067','0.133','0.186','0.246','0.452'])
  ax.set_xlabel('Median surface edge, mm (NOT a complete spatial-resolution parameter)')
  ax.set_ylabel('D_R j_peak, 1/m');ax.set_title('Seven available discrete shape derivatives, not an extrapolation')
  ax.grid(True,alpha=.3);ax.legend(fontsize=9,loc='upper center');fig.tight_layout()
  fig.savefig(ROOT/'figures/P10AA_JPEAK_D_VS_WALL_EDGE.png',dpi=185)
  fig.savefig(ROOT/'figures/P10AA_JPEAK_D_VS_WALL_EDGE.svg')
  plt.close(fig)
  # Compare relative variations of J and derivative at comparable selected transitions
  pairs=[('H2','H3'),('H3','H4'),('H4','H4W2'),('H4W2','H4W2B20'),('H4W2','H4W4B2')]
  labels=['H2→H3','H3→H4','H4→H4W2','W2→W2B20','W2→W4B2']
  vJ=[abs(100*(vals[b,'jpeak']['J']/vals[a,'jpeak']['J']-1)) for a,b in pairs]
  vD=[abs(100*(vals[b,'jpeak']['D']/vals[a,'jpeak']['D']-1)) for a,b in pairs]
  import numpy as np
  x=np.arange(len(labels));fig,ax=plt.subplots(figsize=(9.3,5.0))
  ax.bar(x-0.18,vJ,width=.34,label='|delta J| / |J_start|')
  ax.bar(x+0.18,vD,width=.34,label='|delta D| / |D_start|')
  ax.set_xticks(x,labels);ax.set_ylabel('Relative change, %');ax.set_title('j_peak: objective value vs. geometric derivative')
  ax.set_yscale('symlog',linthresh=.01);ax.set_ylim(0,2.5);ax.grid(axis='y',alpha=.25)
  ax.legend();fig.tight_layout()
  fig.savefig(ROOT/'figures/P10AA_JPEAK_RELATIVE_CHANGES.png',dpi=185)
  fig.savefig(ROOT/'figures/P10AA_JPEAK_RELATIVE_CHANGES.svg')
  plt.close(fig)
 print('\n'.join(verification))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--no-figures',action='store_true');a=p.parse_args();main(not a.no_figures)
