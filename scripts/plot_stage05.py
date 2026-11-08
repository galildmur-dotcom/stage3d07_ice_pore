#!/usr/bin/env python3
"""Optional plots: matplotlib required. Raw CSV is source of truth."""
import argparse,csv,pathlib
p=argparse.ArgumentParser();p.add_argument('--results',default='results/EDV_material');args=p.parse_args()
r=pathlib.Path(args.results)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
rows=list(csv.DictReader(open(r/'G05_E_ED_EDV_pairs.csv',newline='')))
for kind, ylabel, title, name in [('sigma_xy_MPa','Shear stress, MPa','Prescribed-strain material point: E / ED / EDV','G05_model_comparison.png'),('e_v_xy','Viscous strain (tensor component)','Permanent viscous strain in EDV point test','G05_viscous_history.png')]:
 fig,ax=plt.subplots(figsize=(9,5))
 for model in ('E','ED','EDV'):
  if kind=='e_v_xy' and model!='EDV':continue
  for mode in ('CONST','VAR'):
   sub=[x for x in rows if x['model']==model and x['mode']==mode]
   ax.plot([float(x['time_s'])/60 for x in sub],[float(x[kind]) for x in sub],label=f'{model} E_{mode}',linewidth=1.8 if mode=='CONST' else 1.1,linestyle='-' if mode=='CONST' else '--')
 ax.set(title=title,xlabel='Time, min',ylabel=ylabel)
 ax.grid(alpha=.25);ax.legend(fontsize=9)
 fig.tight_layout();fig.savefig(r/name,dpi=160);plt.close(fig)
rows=list(csv.DictReader(open(r/'G05_time_convergence.csv',newline='')))
fig,ax=plt.subplots(figsize=(7,5))
ax.loglog([float(x['dt_s']) for x in rows[:-1]],[float(x['relative_stress_error_against_8192']) for x in rows[:-1]],'o-')
ax.set(title='EDV material point: backward Euler temporal refinement',xlabel='Time step, s',ylabel='Relative shear-stress error vs N=8192')
ax.grid(True,which='both',alpha=.25);fig.tight_layout();fig.savefig(r/'G05_temporal_convergence.png',dpi=160);plt.close(fig)
print('PLOTS: G05_model_comparison.png G05_viscous_history.png G05_temporal_convergence.png')
