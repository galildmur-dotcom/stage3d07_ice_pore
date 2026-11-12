# -*- coding: utf-8 -*-
"""Regenerate P10Y/H4W2 radial figures using matplotlib and standard CSV I/O.
Run from any directory: python experiments/P10Y_H4W2_R_20261112/tools/rebuild_radial_figures.py
Requires matplotlib. Outputs are within the same evidence directory.
"""
import csv
from pathlib import Path
from collections import defaultdict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'data'/'P10Y_SHELL_SUMMARY.csv'
rows=list(csv.DictReader(source.open(encoding='utf-8-sig',newline='')))
funcs=['jpeak','j6','jen']
by={f:[r for r in rows if r['functional']==f and r['distance_upper_mm']!=''] for f in funcs}
for f in funcs:
 assert len(by[f])==9,f

# produce enhanced shareable data for reproducibility
output=ROOT/'data'/'P10Y_H4W2_RADIAL_DENSITY_CUMULATIVE.csv'
with output.open('w',encoding='utf-8-sig',newline='') as fp:
 w=csv.writer(fp, lineterminator='\n')
 w.writerow(['mesh','mode','functional','distance_lower_mm','distance_upper_mm','distance_mid_mm','shell_width_mm','explicit_per_m','equilibrium_per_m','history_per_m','mechanical_shell_per_m','mechanical_density_per_m_per_mm','mechanical_cumulative_per_m'])
 for f in funcs:
  cumulative=0.0
  for r in by[f]:
   lo=float(r['distance_lower_mm']); hi=float(r['distance_upper_mm']); width=hi-lo
   val=float(r['sum_mechanical_per_m']); cumulative+=val
   w.writerow([r['mesh'],r['mode'],f,lo,hi,(lo+hi)/2,width,float(r['sum_explicit_objective_per_m']),float(r['sum_equilibrium_residual_per_m']),float(r['sum_internal_history_per_m']),val,val/width,cumulative])

plt.rcParams.update({'svg.hashsalt':'P10Y-H4W2-R-20261112', 'font.family':'DejaVu Sans','font.size':10,'axes.titlesize':12,'axes.labelsize':10,'figure.dpi':160,'savefig.dpi':260,'axes.spines.top':False,'axes.spines.right':False})

def draw(f,tag):
 a=by[f][:8]
 lows=[float(r['distance_lower_mm']) for r in a]
 highs=[float(r['distance_upper_mm']) for r in a]
 vals=[float(r['sum_mechanical_per_m']) for r in a]
 widths=[h-l for l,h in zip(lows,highs)]
 dens=[v/w for v,w in zip(vals,widths)]
 cum=[]; v=0.
 for x in vals: v+=x; cum.append(v)
 labels=[f'{l:g}–{h:g}' for l,h in zip(lows,highs)]
 fig,axs=plt.subplots(1,2,figsize=(13.4,5.8))
 fig.subplots_adjust(left=.08,right=.98,bottom=.30,top=.81,wspace=.26)
 fig.suptitle(f'H4W2 · Аналитическая механическая часть $D_R {tag}$ · режим R, 900 с',fontweight='bold',fontsize=13)
 ax=axs[0]
 ax.bar(range(8),dens,alpha=.82,linewidth=0)
 ax.axhline(0,color='black',lw=.85)
 ax.set_xticks(range(8),labels,rotation=48,ha='right')
 ax.set_ylabel('Вклад на 1 мм радиальной толщины, (ед. J/м)/мм')
 ax.set_xlabel('Расстояние от поверхности поры, мм (интервалы)')
 ax.set_title('Радиальная плотность $C_k/\\Delta r_k$')
 ax.grid(axis='y',alpha=.18)
 ax=axs[1]
 x=[.0001]+highs
 y=[0]+cum
 ax.step(x,y,where='post',lw=2.2)
 ax.plot(highs,cum,'o',ms=4)
 ax.axhline(0,color='black',lw=.85)
 ax.set_xscale('symlog',linthresh=.02)
 ax.set_xlim(0,5.2)
 ax.set_xticks([0,.02,.05,.1,.25,.5,1,2,5])
 ax.set_xticklabels(['0','0,02','0,05','0,1','0,25','0,5','1','2','5'],rotation=35)
 ax.set_ylabel('Накопленная механическая часть, ед. J/м')
 ax.set_xlabel('Удаление от поверхности поры, мм')
 ax.set_title('Накопленная сумма $\\sum_{r_k\\leq r} C_k$')
 ax.grid(alpha=.18)
 ax.text(.03,.94,f'Итог: {cum[-1]:+.8g}',transform=ax.transAxes,fontsize=10,va='top',bbox=dict(boxstyle='round,pad=.4',facecolor='white',alpha=.9,edgecolor='.8'))
 fig.text(.5,.045,'Только механическая часть; тепловое сопряжённое слагаемое не распределено по слоям. Источник: P10Y_SHELL_SUMMARY.csv.',ha='center',va='bottom',fontsize=8.5)
 for ext in ('png','svg'):
  fig.savefig(ROOT/'figures'/f'P10Y_H4W2_{f}_radial.{ext}',bbox_inches='tight',pad_inches=.23, metadata={'Date': None} if ext=='svg' else None)
 plt.close(fig)
 print(f, 'sum=',cum[-1], 'r<=2=',cum[6], '2-5=',vals[7], 'maxabsdensity at',labels[max(range(8),key=lambda i:abs(dens[i]))],max(dens,key=abs))

for f,tag in [('jpeak',r'j_{\mathrm{peak}}'),('j6','j_6'),('jen','j_{\mathrm{en}}')]:
 draw(f,tag)
print('output files',[(x.name,x.stat().st_size) for x in (ROOT/'figures').glob('P10Y_H4W2_*')])
