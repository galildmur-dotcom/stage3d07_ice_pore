#!/usr/bin/env python3
"""Plot only available pilot maximum-centroid tensile stresses. Figures are not convergence evidence."""
import csv
from pathlib import Path
import matplotlib.pyplot as plt
r=Path(__file__).resolve().parents[1]/'results'
with (r/'paired_fields_vtk_check.csv').open() as f:
    data={d['case']:d for d in csv.DictReader(f)}
fig,ax=plt.subplots(figsize=(7.4,4.3))
for m,label in (('sigma1_max_CONST_MPa','E_CONST'),('sigma1_max_VAR_MPa','E_VAR(T)')):
    cases=['mechanics_H0_t900','mechanics_H0_t1800','mechanics_H0']
    ax.plot([900,1800,3600],[float(data[k][m]) for k in cases],marker='o',label=label)
ax.set_xlabel('Time (s)');ax.set_ylabel('Maximum element-centroid principal stress (MPa)')
ax.set_title('H0: pilot thermoelastic response (xi=0)');ax.grid(True,alpha=.3);ax.legend()
fig.tight_layout();fig.savefig(r/'H0_elastic_stress_history.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.4,4.3))
for m,label in (('sigma1_max_CONST_MPa','E_CONST'),('sigma1_max_VAR_MPa','E_VAR(T)')):
    cases=['mechanics_H0','mechanics_H1','mechanics_H2']
    ax.plot(['H0','H1','H2'],[float(data[k][m]) for k in cases],marker='o',label=label)
ax.set_ylabel('Maximum element-centroid principal stress (MPa)')
ax.set_title('Peak stress not yet mesh-converged (t=3600 s)');ax.grid(True,alpha=.3);ax.legend()
fig.tight_layout();fig.savefig(r/'stress_mesh_pilot_nonconvergence.png',dpi=180);plt.close(fig)
