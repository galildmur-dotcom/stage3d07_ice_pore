#!/usr/bin/env python3
"""Reproduce P10Y radial shell comparison images and CSV using original shell CSV.
Dependencies: Python 3, matplotlib. No pandas. Example:
python tools/compare_shells.py --shell H4=input/P10Y_H4_SHELL_SUMMARY.csv \
    --shell H4W2=input/P10Y_H4W2_SHELL_SUMMARY.csv --baseline H4 \
    --compare H4W2 --output .
Additional --shell H0=... H2=... H6=... overlay new meshes after verifying
identical physical setup and bin boundaries.
"""
import argparse
import csv
import math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

FUNCS = [('jpeak','j_peak'), ('j6','j_6'), ('jen','j_en')]
PARTS = [
    ('sum_explicit_objective_per_m','explicit'),
    ('sum_equilibrium_residual_per_m','equilibrium'),
    ('sum_internal_history_per_m','history'),
    ('sum_mechanical_per_m','mechanical'),
]

def read_shell_csv(path):
    grouped={}
    with open(path,encoding='utf-8-sig',newline='') as fh:
        for r in csv.DictReader(fh):
            if r['mode']!='R' or float(r['delta_um'])!=0:
                raise ValueError('Expected ANALYTIC_TET10, R, delta_um=0: '+str(path))
            f=r['functional'];lo=float(r['distance_lower_mm'])
            hi=float(r['distance_upper_mm']) if r['distance_upper_mm'] else None
            if (f,lo) in grouped:
                raise ValueError('Duplicate (functional,shell) in '+str(path))
            grouped[(f,lo)]={'lower':lo,'upper':hi, **{name:float(r[name]) for name,_ in PARTS}}
    if len(grouped)!=30:
        raise ValueError('Expected 3 functions * 10 bins in '+str(path))
    return grouped

def bin_label(lo,hi):
    fmt=lambda x: ('{:g}'.format(x)).replace('.',',')
    return '{}–{}'.format(fmt(lo),fmt(hi)) if hi is not None else fmt(lo)+'+'

def baseline_aligned(labeled):
    first=next(iter(labeled.values()))
    keys=list(first)
    for name,data in labeled.items():
        if set(data)!=set(first):
            raise ValueError('Inconsistent bin keys: '+name)
        for k in keys:
            if data[k]['upper']!=first[k]['upper']:
                raise ValueError('Inconsistent radial interval: '+str(k))
    return keys

def save_csv(path, rows, header):
    with open(path,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=header,lineterminator='\n')
        w.writeheader();w.writerows(rows)

def write_data(labeled,baseline,comp,out):
    b=labeled[baseline]; c=labeled[comp]
    rows=[];overview=[]
    for fn,_ in FUNCS:
        cum={n:0. for n in labeled}
        changes=[]
        for lo in sorted(k[1] for k in b if k[0]==fn):
            key=(fn,lo);hi=b[key]['upper']
            row={'functional':fn,'lower_mm':lo,'upper_mm':hi if hi is not None else '',
                 'bin_label_mm':bin_label(lo,hi), 'shell_width_mm':hi-lo if hi is not None else ''}
            for n,dat in labeled.items():
                obj=dat[key]
                for partname,nick in PARTS:
                    row[f'{n}_{nick}_per_m']=obj[partname]
                v=obj['sum_mechanical_per_m']
                cum[n]+=v
                row[f'{n}_cum_mechanical_per_m']=cum[n]
                row[f'{n}_mechanical_density_per_m_per_mm']=v/(hi-lo) if hi is not None else ''
            for name,nick in PARTS:
                row[f'delta_{nick}_per_m']=c[key][name]-b[key][name]
            row['delta_mechanical_density_per_m_per_mm']=row['delta_mechanical_per_m']/(hi-lo) if hi is not None else ''
            rows.append(row)
            changes.append((lo,hi,row['delta_mechanical_per_m']))
        total=sum(x[2] for x in changes)
        changes_finite=[x for x in changes if x[1] is not None]
        maxshell=max(changes_finite,key=lambda z:abs(z[2]))
        abs_sum=sum(abs(x[2]) for x in changes)
        overview.append({'functional':fn,'baseline':baseline,'compare':comp,
                         'baseline_mechanical_per_m':cum[baseline],
                         'compare_mechanical_per_m':cum[comp],
                         'delta_mechanical_per_m':total,
                         'sum_abs_delta_shell_per_m':abs_sum,
                         'ratio_sum_abs_to_net':abs_sum/abs(total) if total else '',
                         'max_abs_delta_lower_mm':maxshell[0],
                         'max_abs_delta_upper_mm':maxshell[1],
                         'max_abs_delta_per_m':maxshell[2]})
    save_csv(out/'data'/'P10Y_RADIAL_COMPARISON_ALL_MESHES.csv',rows,list(rows[0]))
    save_csv(out/'data'/'P10Y_RADIAL_DIFFERENCE_SUMMARY.csv',overview,list(overview[0]))
    return rows,overview

def graph(labeled,base,comp,out):
    names=list(labeled)
    for fn,display in FUNCS:
        b=labeled[base]
        keys=sorted((k for k in b if k[0]==fn),key=lambda x:x[1])
        keys=[k for k in keys if b[k]['upper'] is not None and b[k]['upper']<=5]
        labels=[bin_label(b[k]['lower'],b[k]['upper']) for k in keys]
        x=list(range(len(keys)))
        cum={}; densities={}
        for n,d in labeled.items():
            acc=0.;y=[]; cd=[0.]
            for k in keys:
                v=d[k]['sum_mechanical_per_m']; acc+=v
                y.append(v/(b[k]['upper']-b[k]['lower']))
                cd.append(acc)
            cum[n]=cd; densities[n]=y
        dC=[labeled[comp][k]['sum_mechanical_per_m']-labeled[base][k]['sum_mechanical_per_m'] for k in keys]
        fig,(ax0,ax1,ax2)=plt.subplots(1,3,figsize=(17.6,6.15),gridspec_kw={'width_ratios':[1.12,1.02,1.14]})
        width=0.76/len(names)
        for j,n in enumerate(names):
            off=(j-(len(names)-1)/2)*width
            ax0.bar([xx+off for xx in x],densities[n],width=width,label=n,alpha=.86)
        ax0.axhline(0,color='.25',lw=.9)
        ax0.set_title('(a) Радиальная плотность вклада')
        ax0.set_ylabel(r'$C_k / \Delta r_k$, м$^{-1}$/мм')
        ax0.set_xticks(x);ax0.set_xticklabels(labels,rotation=53,ha='right')
        ax0.set_xlabel('Расстояние от поры, интервалы, мм')
        ax0.legend(fontsize=9)
        ax0.grid(axis='y',alpha=.2)
        edges=[0.]+[b[k]['upper'] for k in keys]
        for n in names:
            ax1.plot(edges,cum[n],marker='o',lw=1.65,ms=4,label=n)
        ax1.axhline(0,color='.25',lw=.9)
        ax1.set_xscale('symlog',linthresh=.1,linscale=1)
        ax1.set_xlim(-.006,5.5)
        ax1.set_xticks([0,.02,.05,.1,.25,.5,1,2,5])
        ax1.set_xticklabels(['0','0,02','0,05','0,1','0,25','0,5','1','2','5'],rotation=40,ha='right')
        ax1.set_ylabel(r'$G_h(r)$, м$^{-1}$')
        ax1.set_xlabel('Верхняя граница включённых слоёв, мм')
        ax1.set_title('(б) Накопленный механический вклад')
        ax1.legend(fontsize=9)
        ax1.grid(alpha=.2)
        ax2.bar(x,dC,width=.75)
        ax2.axhline(0,color='.25',lw=.9)
        ax2.set_xticks(x);ax2.set_xticklabels(labels,rotation=53,ha='right')
        ax2.set_title('(в) Межсеточное изменение по слоям')
        ax2.set_ylabel(r'$C_{k,'+comp+r'} - C_{k,'+base+r'}$, м$^{-1}$')
        ax2.set_xlabel('Расстояние от поры, интервалы, мм')
        ax2.grid(axis='y',alpha=.2)
        for ax in (ax0,ax1,ax2):
            ax.tick_params(axis='both',labelsize=9)
            ax.yaxis.set_major_locator(MaxNLocator(nbins=7))
        fig.suptitle('P10Y · '+display+' · '+base+' / '+comp+' · EDV_VAR, R, t = 900 с',fontsize=14)
        fig.text(.50,.009,'Только механическая часть сопряжённой производной; тепловой вклад не разнесён по слоям.\n'
                    'Интервалы на (а, в) равной ширины условно; (б) имеет нелинейную шкалу расстояния.',
                    ha='center',fontsize=9,color='.3')
        fig.subplots_adjust(left=.065,right=.982,bottom=.265,top=.85,wspace=.32)
        stem=f'P10Y_{base}_vs_{comp}_{fn}_RADIAL'
        fig.savefig(out/'figures'/f'{stem}.png',dpi=185)
        fig.savefig(out/'figures'/f'{stem}.svg')
        plt.close(fig)

def component_fig(labeled,base,comp,out):
    fn='jpeak';b=labeled[base]
    keys=sorted((k for k in b if k[0]==fn and b[k]['upper'] is not None and b[k]['upper']<=5),key=lambda k:k[1])
    names=['explicit','equilibrium','history']
    vals=[]
    for code,label in zip(['sum_explicit_objective_per_m','sum_equilibrium_residual_per_m','sum_internal_history_per_m'],names):
        vals.append([labeled[comp][k][code]-labeled[base][k][code] for k in keys])
    fig,ax=plt.subplots(figsize=(12,5.2))
    x=list(range(len(keys)));w=.23
    for i,(name,v) in enumerate(zip(names,vals)):
        ax.bar([xx+(i-1)*w for xx in x],v,width=w,label=name)
    ax.axhline(0,color='.25',lw=.9)
    ax.set_xticks(x)
    ax.set_xticklabels([bin_label(b[k]['lower'],b[k]['upper']) for k in keys])
    ax.set_xlabel('Расстояние от поверхности поры, мм (интервалы по категориям)')
    ax.set_ylabel(r'Изменение составляющих $D_R j_{peak}$, м$^{-1}$')
    ax.set_title('P10Y · j_peak · изменение составляющих по слоям: H4W2 − H4')
    ax.legend(ncol=3)
    ax.grid(axis='y',alpha=.2)
    fig.text(.5,.013,'Разложение механической части; тепловой вклад показан только глобально в CSV.',ha='center',fontsize=9,color='.35')
    fig.subplots_adjust(left=.095,right=.98,bottom=.18,top=.88)
    name=f'P10Y_{base}_vs_{comp}_jpeak_COMPONENT_DIFF'
    fig.savefig(out/'figures'/f'{name}.png',dpi=185)
    fig.savefig(out/'figures'/f'{name}.svg')
    plt.close(fig)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shell',action='append',required=True,help='NAME=PATH, repeat for further meshes')
    parser.add_argument('--baseline',required=True)
    parser.add_argument('--compare',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    labeled={}
    for arg in args.shell:
        name,sep,path=arg.partition('=')
        if not sep or not name.strip() or not path.strip():
            parser.error('Invalid --shell NAME=PATH: '+arg)
        labeled[name]=read_shell_csv(Path(path))
    if args.baseline not in labeled or args.compare not in labeled:
        parser.error('baseline/compare not in --shell list')
    baseline_aligned(labeled)
    out=args.output; (out/'data').mkdir(parents=True,exist_ok=True);(out/'figures').mkdir(parents=True,exist_ok=True)
    _,overview=write_data(labeled,args.baseline,args.compare,out)
    graph(labeled,args.baseline,args.compare,out)
    component_fig(labeled,args.baseline,args.compare,out)
    for row in overview:
        print('SUMMARY',row)
    print('P10Y_RADIAL_COMPARISON_OK figures=8 csv=2')

if __name__=='__main__':main()
