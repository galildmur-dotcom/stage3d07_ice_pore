#!/usr/bin/env python3
"""Source-verified Stage3D07 36x25 R/EDV_VAR M1..M11 convergence graphics."""
import csv, json, math, zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'p10mp_convergence_figures'

# Exact comparable dt25 signed4D totals from verified Git research reports and
# source-returned M6..M11 manifest postprocessing. M1=2026-11-24 P10IL dt25.
N=np.arange(1,12)
DR=np.array([2.6288060492440355,2.559851025083483,2.473214870917869,
  2.388080130362648,2.364120991403208,2.3626527877865855,
  2.372527953217,2.361333042852,2.3732842812460593,
  2.3730572408475132,2.376941218512608],dtype=float)
TET=np.array([9736,9840,10063,10399,10826,11628,12001,12546,13166,13996,15055])

# L1 is absolute sum of matched signed 4D bin changes over 36*1200+36 rows.
# There is no verified full 4D L1 M1->M2 in the cited P10IL spatial-only report.
L1={3:4.9588498165,4:2.6693487290,5:2.1364740016941726,
  6:1.9291185856420219,7:1.066029765758,8:.953928903742,
  9:.964211175178,10:.8079903924025355,11:.7222589721609709}
L2={7:.023373829751,8:.019466225814,9:.020890891626,
   10:.015109248822333023,11:.011676416504911821}

def style():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,
     'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,
     'grid.alpha':.22,'figure.dpi':160,'savefig.dpi':190})

def main():
    if OUT.exists():raise RuntimeError('P10MP outputs already exist; do not overwrite')
    assert len(DR)==len(TET)==11 and np.all(np.isfinite(DR))
    assert all(1<=k<=11 and v>0 for k,v in L1.items())
    assert math.isclose(DR[10],2.376941218512608,rel_tol=0,abs_tol=1e-14)
    OUT.mkdir()
    diff=np.diff(DR)
    rel=100*diff/DR[:-1]
    l1bins=np.array(sorted(L1))
    l2bins=np.array(sorted(L2))
    style()

    fig,ax=plt.subplots(2,2,figsize=(13.2,9.5),layout='constrained')
    a=ax[0,0]
    a.plot(N,DR,'o-',color='#17569e',lw=2.1,ms=6)
    a.axhline(DR[-1],ls='--',color='#999999',alpha=.6,label='Уровень M11 (не точный предел)')
    a.set(xlabel='Номер сетки M',ylabel=r'$D_R J_{peak}$, м$^{-1}$',
          title='(а) Производная формы: M1–M11')
    a.set_xticks(N)
    for i in (0,3,5,8,10):a.annotate(f'{DR[i]:.4f}',(N[i],DR[i]),xytext=(2,9),textcoords='offset points',fontsize=9)
    a.legend(loc='upper right',fontsize=8)

    a=ax[0,1]
    sel=N>=5
    a.plot(N[sel],DR[sel],'o-',color='#0a8b86',lw=2.1,ms=6)
    a.axhline(DR[-1],ls='--',color='#aaa',alpha=.65)
    a.set(xlabel='Номер сетки M',ylabel=r'$D_R J_{peak}$, м$^{-1}$',
          title='(б) Увеличенный фрагмент: M5–M11')
    a.set_xticks(N[sel]);a.yaxis.set_major_locator(MaxNLocator(6))
    for i in range(4,11):a.annotate(f'{DR[i]:.4f}',(N[i],DR[i]),xytext=(4,8 if i%2 else -17),textcoords='offset points',fontsize=8)

    a=ax[1,0]
    colors=np.where(diff>0,'#bc643e','#3c76ad')
    a.bar(N[1:],diff,color=colors,width=.65)
    a.axhline(0,color='#333',lw=1)
    a.set(xlabel='Новая сетка Mᵢ',ylabel=r'$D_R J_{peak}(M_i)-D_R J_{peak}(M_{i-1})$, м$^{-1}$',
          title='(в) Знаковая межсеточная разность')
    a.set_xticks(N[1:])

    a=ax[1,1]
    a.semilogy(N[1:],np.abs(diff),'o-',color='#78469c',lw=2,ms=6)
    a.set(xlabel='Новая сетка Mᵢ',ylabel=r'$|\Delta D_R J_{peak}|$, м$^{-1}$ (лог. масштаб)',
          title='(г) Модуль межсеточной разности')
    a.set_xticks(N[1:]);a.set_ylim(1e-4,.2)
    fig.suptitle('Stage3D07  |  R / EDV_VAR / ξ=0 / B6=5 mm / 36×25 s',fontsize=16,weight='bold')
    fig.savefig(OUT/'P10MP_M1_M11_GLOBAL_DERIVATIVE.png',bbox_inches='tight')
    plt.close(fig)

    fig,ax=plt.subplots(2,2,figsize=(13.2,9.5),layout='constrained')
    a=ax[0,0]
    a.plot(TET,DR,'o-',lw=2,color='#17569e',ms=6)
    for i in range(11):a.annotate(f'M{i+1}',(TET[i],DR[i]),xytext=(3,7 if i%2 else -14),textcoords='offset points',fontsize=9)
    a.set(xlabel='Число элементов Tet10',ylabel=r'$D_R J_{peak}$, м$^{-1}$',
          title='(д) Производная и число элементов (неравномерное h)')

    a=ax[0,1]
    a.semilogy(l1bins,[L1[k] for k in l1bins],'o-',color='#a45136',lw=2,ms=6,label='signed 4D L1')
    a.set(xlabel='Новая сетка Mᵢ',ylabel='Σ|разность знаковых 4D-ячеек|, м⁻¹',
          title='(е) Норма L1 разности полных 4D-полей')
    a.set_xticks(N[1:]);a.set_ylim(.5,7)
    a.text(.03,.08,'M1→M2: в источнике только пространственная L1',transform=a.transAxes,
       fontsize=9,color='#5c4b46',bbox={'facecolor':'white','edgecolor':'none','alpha':.8})

    a=ax[1,0]
    a.plot(l2bins,[L2[k] for k in l2bins],'o-',color='#0a8b86',lw=2,ms=6)
    a.set(xlabel='Новая сетка Mᵢ',ylabel='L2 разности согласованных 4D-ячеек, м⁻¹',
          title='(ж) Норма L2 полных 4D-полей (с M6→M7)')
    a.set_xticks(l2bins)

    a=ax[1,1]
    cancel=np.array([L1[k]/abs(DR[k-1]-DR[k-2]) for k in l1bins])
    a.semilogy(l1bins,cancel,'o-',color='#78469c',lw=2,ms=6)
    a.set(xlabel='Новая сетка Mᵢ',ylabel='L1 / |глобальная знаковая Δ| (лог. масштаб)',
          title='(з) Коэффициент компенсации знаковых вкладов')
    a.set_xticks(l1bins)
    a.annotate('M9→M10: ~3559×',(10,cancel[-2]),xytext=(7.2,2200),
               arrowprops={'arrowstyle':'->','color':'#777'},fontsize=10)
    fig.suptitle('Stage3D07  |  Локальная сходимость и компенсация вкладов',fontsize=16,weight='bold')
    fig.savefig(OUT/'P10MP_M1_M11_LOCAL_4D_CONVERGENCE.png',bbox_inches='tight')
    plt.close(fig)

    with (OUT/'P10MP_M1_M11_VERIFIED_SERIES.csv').open('w',newline='') as f:
        writer=csv.writer(f)
        writer.writerow(['mesh','Tet10','D_R_jpeak_per_m','delta_global_per_m',
          'relative_delta_percent','matched_full4d_signed_bin_L1_per_m',
          'matched_full4d_signed_bin_L2_per_m','cancellation_factor'])
        for i in range(11):
            step=i+1
            d='' if i==0 else float(diff[i-1])
            writer.writerow([f'M{step}',TET[i],format(DR[i],'.16g'),d,
              '' if i==0 else float(rel[i-1]),L1.get(step,''),L2.get(step,''),
              '' if step not in L1 else L1[step]/abs(float(diff[i-1]))])

    qa={'protocol':'P10MP_M1_M11_SOURCE_VERIFIED_CONVERGENCE_FIGURES',
       'regime':'R EDV_VAR xi0 B6 5mm steps36 dt25',
       'M1_original_dt150_excluded':True,
       'M1_dt25_source':'P10IL M1 M2 dt25 real signed4D',
       'M2_M5_sources':'P10IJ P10IS P10JK P10JR',
       'M6_M8_sources':'P10JX P10KK P10KW',
       'M9_M11_sources':'P10LD P10LZ P10MJ physical ZIP manifests',
       'missing_full4d_L1_M1_M2':True,
       'full4d_L2_available_only_from_M6_M7':True,
       'note':'L1/L2 are norms of signed-bin Δ over matched canonical 4D partition, not continuum FE error norms',
       'FEM_attempts':0,'mesh_generation_attempts':0}
    (OUT/'P10MP_SOURCES_AND_LIMITATIONS.json').write_text(json.dumps(qa,indent=2)+'\n')
    archive=ROOT/'P10MP_M1_M11_DERIVATIVE_AND_4D_CONVERGENCE_GRAPHS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(OUT.iterdir()):z.write(p,arcname=p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    print(json.dumps({'status':'FIGURES_PASS_NO_FEM','min':float(DR.min()),
      'last':float(DR[-1]),'last_delta':float(diff[-1]),
      'last_L1':L1[11],'last_L2':L2[11],'archive':str(archive)},indent=2))

if __name__=='__main__':main()
