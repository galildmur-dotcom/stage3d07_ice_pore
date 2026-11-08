#!/usr/bin/env python3
import csv,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).resolve().parents[1];out=root/'results'
def read(path):
    with path.open() as f:return [{k:(float(v) if k not in ('mesh','quad','field') and v!='' else v) for k,v in r.items()} for r in csv.DictReader(f)]
d=read(out/'H2_dt300_xi0/time_series.csv')
t=[0]+[r['time_s'] for r in d]
fig,ax=plt.subplots(figsize=(8.2,4.8))
ax.plot(t,[-20]+[r['ambient_C'] for r in d],label='Ambient')
ax.plot(t,[-20]+[r['top_mean_C'] for r in d],label='Top mean')
ax.plot(t,[-20]+[r['volume_mean_C'] for r in d],label='Ice volume mean')
ax.set_xlabel('Time, s');ax.set_ylabel('Temperature, °C');ax.set_title('3D transient conduction, H2, xi=0')
ax.grid(True,alpha=.3);ax.legend();fig.tight_layout();fig.savefig(out/'temperature_history_H2.png',dpi=180);plt.close(fig)

fine=read(out/'convergence.csv');dd=[r for r in fine if r['mesh']=='H0'];
fig,ax=plt.subplots(figsize=(7,4.5));ax.plot([x['dt_s'] for x in dd],[abs(x['err_top_vs_exact_1D_K']) for x in dd],marker='o')
ax.set_xlabel('Backward Euler timestep, s');ax.set_ylabel('Absolute top temperature difference, K');ax.set_title('Temporal convergence vs no-pore 1D reference')
ax.grid(True,alpha=.3);fig.tight_layout();fig.savefig(out/'temporal_convergence_H0.png',dpi=180);plt.close(fig)

r=read(out/'GH3_GH5.csv');r=[x for x in r if x['mesh']=='H0' and x['field']=='top_mean_C'];
fig,ax=plt.subplots(figsize=(6.5,4.5));ax.bar(['GH3','GH5'],[v['variance_K2'] for v in r]);ax.set_ylim(0,.105)
ax.set_ylabel('Variance of top-mean temperature, K²');ax.set_title('Thermal GH3/GH5 consistency, H0, 150 s')
fig.tight_layout();fig.savefig(out/'GH3_GH5_variance.png',dpi=180);plt.close(fig)
print('PASS: three numerical figures saved')
