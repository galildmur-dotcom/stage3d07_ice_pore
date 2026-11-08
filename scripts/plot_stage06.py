#!/usr/bin/env python3
"""Create static comparison graphs from genuine G06 campaign CSV (matplotlib optional)."""
import csv,pathlib,matplotlib.pyplot as plt
base=pathlib.Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((base/'results/G06_H0_dt300/G06_campaign.csv').open()))
for col,title,ylabel,out in [('max_principal_MPa','Maximum quadrature-point principal stress, H0','MPa','G06_stress_history_H0.png'),('Psi6','Instantaneous local tensile indicator Phi6, H0','dimensionless','G06_Phi6_history_H0.png')]:
 fig,ax=plt.subplots(figsize=(8,4.5))
 for law in ('E','ED','EDV'):
  for mod in ('CONST','VAR'):
   s=[r for r in rows if (r['law'],r['modulus'])==(law,mod)]
   ax.plot([float(r['time_s'])/60 for r in s],[float(r[col]) for r in s],label=f'{law} {mod}',linestyle='--' if mod=='VAR' else '-')
 ax.set_xlabel('Time, min');ax.set_ylabel(ylabel);ax.set_title(title);ax.grid(alpha=.3);ax.legend(ncol=3,fontsize=8);fig.tight_layout();fig.savefig(base/'results'/out,dpi=140);plt.close(fig)
 print('Generated',out)
