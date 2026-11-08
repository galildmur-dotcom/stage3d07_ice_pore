#!/usr/bin/env python3
import csv, argparse
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('--results',default='results/ED_material');args=p.parse_args()
root=Path(args.results)
def read(filename):
 with open(root/filename,newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
r=read('G04_relaxation_history.csv')
fig,ax=plt.subplots(figsize=(7.2,4.4))
for T,mode in ((253.15,'CONST'),(263.15,'CONST')):
 s=[x for x in r if x['model']==mode and abs(float(x['T_K'])-T)<.001]
 label=f'T = {T-273.15:.0f} °C'
 ax.plot([float(x['time_s']) for x in s],[float(x['shear_stress_MPa']) for x in s],label='BE '+label)
 ax.plot([float(x['time_s']) for x in s],[float(x['analytic_shear_stress_MPa']) for x in s],':',label='Exact '+label)
ax.set_xlabel('Time, s');ax.set_ylabel('Shear stress, MPa');ax.set_title('ED point: relaxation at fixed strain');ax.legend();ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(root/'G04_relaxation.png',dpi=170);plt.close(fig)
r=read('G04_temporal_convergence.csv')
fig,ax=plt.subplots(figsize=(7.2,4.4))
s=[x for x in r if x['mode']=='CONST' and abs(float(x['T_K'])-253.15)<.001]
ax.loglog([float(x['dt_s']) for x in s],[float(x['absolute_error_Pa']) for x in s],marker='o',label='BE error')
ax.set_xlabel('Time step, s');ax.set_ylabel('Shear-stress absolute error, Pa');ax.set_title('ED point: convergence to continuous exact relaxation');ax.legend();ax.grid(True,which='both',alpha=.3);fig.tight_layout();fig.savefig(root/'G04_temporal_convergence.png',dpi=170);plt.close(fig)
r=read('G04_stress_controlled_recovery.csv')
fig,ax=plt.subplots(figsize=(7.2,4.4))
ax.plot([float(x['time_s']) for x in r],[float(x['ed_xy']) for x in r],label='Backward Euler')
ax.plot([float(x['time_s']) for x in r],[float(x['analytic_ed_xy']) for x in r],':',label='Exact')
ax.axvline(600,linestyle='--',label='Unload')
ax.set_xlabel('Time, s');ax.set_ylabel('Delayed shear strain e_d,xy');ax.set_title('ED point: stress-controlled load and recovery');ax.legend();ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(root/'G04_recovery.png',dpi=170);plt.close(fig)
