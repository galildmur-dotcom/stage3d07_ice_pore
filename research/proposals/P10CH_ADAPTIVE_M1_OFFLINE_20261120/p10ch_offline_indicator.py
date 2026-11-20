"""P10CH: read-only pole-localization audit and offline candidate refinement indicator.

No FEM, remeshing, Git mutation or interpretation as a posteriori error estimate.
"""
from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / 'stage3d07_readonly'
if not (SOURCE_ROOT / 'experiments/P10BB_W5B2_SPHERICAL_20261118').is_dir():
    for candidate in (ROOT, *ROOT.parents):
        if (candidate / 'experiments/P10BB_W5B2_SPHERICAL_20261118').is_dir():
            SOURCE_ROOT = candidate
            break
    else:
        raise FileNotFoundError('Stage3D07 source tree with original P10BB CSV is required')
BASE = SOURCE_ROOT / 'experiments/P10BB_W5B2_SPHERICAL_20261118/input'
TEMP = SOURCE_ROOT / 'research/evidence/P10BE_H2_20261118/input/P10BE_CELL_TEMPORAL_COMPARE.csv'
FILES = {
    'base': (BASE/'H4W4B2_P10BA_QP_POLAR_RADIAL.csv', '219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447'),
    'bulk': (BASE/'H4W4B20_P10BA_QP_POLAR_RADIAL.csv', '3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be'),
    'wall': (BASE/'H4W5B2_P10BA_QP_POLAR_RADIAL.csv', '8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c'),
    'time': (TEMP, 'e16a580d4935580b6b5228ce3f10edd80e67534b2306ef73c8b9fb77df0ffc7e'),
}
CSV_OUT = ROOT/'P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv'
TXT_OUT = ROOT/'P10CH_OFFLINE_AUDIT.txt'
PNG_OUT = ROOT/'P10CH_SPATIAL_TEMPORAL_POLE_INDICATOR.png'


def check_rows(path: Path, expected: str, count: int):
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, path
    with path.open(newline='', encoding='utf-8-sig') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == count, (path, len(rows))
    return rows


def key(row):
    return (round(float(row['shell_lower_mm']), 8), int(row['radial_subbin']), int(row['polar_band']))


tables = {}
for name, (path, sha) in FILES.items():
    rows = check_rows(path, sha, 200 if name == 'time' else 400)
    if name != 'time':
        rows = [r for r in rows if int(r['time_step']) == 6 and abs(float(r['time_s'])-900.) < 1e-8]
    assert len(rows) == 200
    m = {key(r):r for r in rows}
    assert len(m) == 200
    tables[name] = m

keys=sorted(tables['base'],key=lambda k:(k[0],k[1],k[2]))
assert all(set(d) == set(keys) for d in tables.values())

rec=[]
for k in keys:
    a,b,c,t=(tables[z][k] for z in ('base','bulk','wall','time'))
    va,vb,vc=[float(r['total_mechanical_per_m']) for r in (a,b,c)]
    v0=float(a['qp_volume_m3'])
    assert v0>0 and all(float(r['qp_volume_m3'])>0 for r in (b,c))
    assert abs(float(a['radial_lower_mm'])-float(t['radial_lower_mm']))<1e-9
    assert abs(float(a['radial_upper_mm'])-float(t['radial_upper_mm']))<1e-9
    assert abs(float(a['mu_lower'])-float(t['mu_lower']))<1e-9
    assert abs(float(a['mu_upper'])-float(t['mu_upper']))<1e-9
    rec.append({'key':k,'r0':float(a['radial_lower_mm']),'r1':float(a['radial_upper_mm']),
                'mu0':float(a['mu_lower']),'mu1':float(a['mu_upper']),
                'qp_base':int(a['qp_count']),'vol_base':v0,
                'vol_bulk':float(b['qp_volume_m3']),'vol_wall':float(c['qp_volume_m3']),
                'sp_bulk':vb-va,'sp_wall':vc-va,
                'temporal':float(t['difference_50_minus_25_per_m']),
                'explicit_bulk':float(b['explicit_per_m'])-float(a['explicit_per_m']),
                'equil_bulk':float(b['equilibrium_per_m'])-float(a['equilibrium_per_m']),
                'explicit_wall':float(c['explicit_per_m'])-float(a['explicit_per_m']),
                'equil_wall':float(c['equilibrium_per_m'])-float(a['equilibrium_per_m'])})

def arr(name):return np.array([r[name] for r in rec],dtype=float)
ds1,ds2,dt=arr('sp_bulk'),arr('sp_wall'),arr('temporal')
assert abs(np.abs(ds1).sum()-.032245)<.0001
assert abs(np.abs(ds2).sum()-.041149149346)<1e-10
assert abs(np.abs(dt).sum()-.0227496541049496)<1e-11
assert np.allclose(ds1,arr('explicit_bulk')+arr('equil_bulk'),atol=1e-12)
assert np.allclose(ds2,arr('explicit_wall')+arr('equil_wall'),atol=1e-12)
vol=arr('vol_base')
qp=arr('qp_base').astype(int)
poles=np.array([r['key'][2] in (0,9) for r in rec])

def normalized_abs(a):return np.abs(a)/np.abs(a).sum()
def ranks(x):
    order=np.argsort(x,kind='mergesort')
    res=np.empty(len(x),dtype=float)
    res[order]=np.arange(len(x),dtype=float)/(len(x)-1.)
    return res

frac1,frac2,fract=(normalized_abs(z) for z in (ds1,ds2,dt))
vol1,vol2=normalized_abs(ds1/vol),normalized_abs(ds2/vol)
# Conservative agreement: retain a high priority only if both independent
# spatial perturbations rank the same cell high, with volume normalization.
rank_vol1,rank_vol2=ranks(np.abs(ds1)/vol),ranks(np.abs(ds2)/vol)
consensus=np.minimum(rank_vol1,rank_vol2)
selected=np.argsort(-consensus,kind='mergesort')[:40]
selection=np.zeros(len(rec),dtype=bool);selection[selected]=True
raw_consensus=np.minimum(ranks(np.abs(ds1)),ranks(np.abs(ds2)))
raw_selected=set(np.argsort(-raw_consensus,kind='mergesort')[:40])
overlap=len(set(selected).intersection(raw_selected))

pole_shares=[float(x[poles].sum()) for x in (frac1,frac2,fract)]
qp_share=float(qp[poles].sum()/qp.sum())
vol_share=float(vol[poles].sum()/vol.sum())
for actual,expected in zip(pole_shares,[.870058,.877966,.944512]):assert abs(actual-expected)<3e-5

theta_mid=np.degrees(np.arccos(np.arange(.9,-1.0,-.2)))
assert len(theta_mid)==10
ordered_radial=sorted({(r['r0'],r['r1']) for r in rec})
assert len(ordered_radial)==20
lookup={(r['r0'],r['r1'],r['key'][2]):i for i,r in enumerate(rec)}
def matrix(series):
    result=np.zeros((20,10))
    for ir,rad in enumerate(ordered_radial):
        for col,p in enumerate(range(9,-1,-1)):
            result[ir,col]=series[lookup[rad+(p,)]]
    return result

with CSV_OUT.open('w',newline='',encoding='utf-8') as f:
    w=csv.writer(f)
    w.writerow(['r_lower_mm','r_upper_mm','mu_lower','mu_upper','polar_band',
                'qp_base','physical_volume_m3','physical_volume_bulk_m3','physical_volume_wall_m3',
                'delta_bulk_per_m','delta_wall_per_m','delta_H2_dt50_minus_25_per_m',
                'delta_explicit_bulk_per_m','delta_equilibrium_bulk_per_m',
                'delta_explicit_wall_per_m','delta_equilibrium_wall_per_m',
                'spatial_volume_normalized_consensus_rank','chosen_top_20pct',
                'temporal_rank_H2_descriptive_only'])
    for i,r in enumerate(rec):
        w.writerow([r['r0'],r['r1'],r['mu0'],r['mu1'],r['key'][2],
                    r['qp_base'],r['vol_base'],r['vol_bulk'],r['vol_wall'],
                    r['sp_bulk'],r['sp_wall'],r['temporal'],r['explicit_bulk'],
                    r['equil_bulk'],r['explicit_wall'],r['equil_wall'],
                    consensus[i],int(selection[i]),ranks(np.abs(dt))[i]])

audit={
 'STATUS':'P10CH_OFFLINE_INDICATOR_OK_NO_FEM',
 'CELL_COUNT':200, 'STEPS_SPATIAL':'step6 t900s',
 'SPATIAL_BULK_ABS_SUM_PER_M':float(np.abs(ds1).sum()),
 'SPATIAL_WALL_ABS_SUM_PER_M':float(np.abs(ds2).sum()),
 'TEMPORAL_H2_DT50_MINUS_DT25_ABS_SUM_PER_M':float(np.abs(dt).sum()),
 'SPATIAL_BULK_SIGNED_SUM_PER_M':float(ds1.sum()),
 'SPATIAL_WALL_SIGNED_SUM_PER_M':float(ds2.sum()),
 'POLE_L1_SHARE_BULK':pole_shares[0], 'POLE_L1_SHARE_WALL':pole_shares[1],
 'POLE_L1_SHARE_TEMPORAL_H2':pole_shares[2],
 'POLE_BASE_QP_SHARE':qp_share, 'POLE_BASE_QP_VOLUME_SHARE':vol_share,
 'CANDIDATE_TOP40_SPATIAL_BULK_L1_COVERAGE':float(frac1[selection].sum()),
 'CANDIDATE_TOP40_SPATIAL_WALL_L1_COVERAGE':float(frac2[selection].sum()),
 'CANDIDATE_TOP40_AT_POLES':int(np.sum(selection&poles)),
 'TOP40_RAW_INTEGRAL_VS_VOLUME_NORMALIZED_OVERLAP':overlap,
 'SPATIAL_SIGN_AGREEMENT_COUNT':int(np.sum(ds1*ds2>0)),
 'SPATIAL_SIGN_AGREEMENT_IN_CANDIDATE_TOP40':int(np.sum((ds1*ds2>0)&selection)),
 'CANDIDATE_TEMPORAL_H2_DT50_MINUS_DT25_L1_COVERAGE_DESCRIPTIVE':float(fract[selection].sum()),
 'MAX_PHYSICAL_CELL_QP_VOLUME_RELATIVE_DIFF_BULK':float(np.max(np.abs(arr('vol_bulk')/vol-1))),
 'MAX_PHYSICAL_CELL_QP_VOLUME_RELATIVE_DIFF_WALL':float(np.max(np.abs(arr('vol_wall')/vol-1))),
 'WARNING':'Heuristic indicator only; no phi, no proven a posteriori error or temporal convergence.',
}
TXT_OUT.write_text('P10CH READ-ONLY AUDIT\n'+'\n'.join(f'{k}={v}' for k,v in audit.items())+'\n',encoding='utf-8')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5})
fig,axes=plt.subplots(2,2,figsize=(15.5,10.5),dpi=150,layout='constrained')
fig.suptitle('P10CH: где повторяются локальные изменения производной?',fontsize=15,fontweight='bold')
for ax,values,title,cmap in [
  (axes[0,0],frac1,'H4 W4B2 → W4B20: доля |Δ| по ячейкам','magma'),
  (axes[0,1],frac2,'H4 W4B2 → W5B2: доля |Δ| по ячейкам','magma'),
  (axes[1,0],consensus,'Согласованный пространственный приоритет (0–1)','viridis')]:
    vmax=1. if values is consensus else max(float(frac1.max()),float(frac2.max()))
    im=ax.imshow(matrix(values),origin='upper',aspect='auto',cmap=cmap,vmin=0,vmax=vmax)
    ax.set_title(title,fontsize=11.5)
    ax.set_xticks(range(10),[f'{v:.0f}' for v in theta_mid])
    ax.set_xlabel('Полярный угол θ, градусы (+z → −z)')
    ax.set_yticks(range(0,20,2),[f'{ordered_radial[j][0]:.3f}–{ordered_radial[j][1]:.3f}' for j in range(0,20,2)],fontsize=8.7)
    ax.set_ylabel('Расстояние от поры, мм')
    cbar=fig.colorbar(im,ax=ax,shrink=.82,pad=.02)
    cbar.set_label('Относительная доля L1' if values is not consensus else 'Ранг согласованности')

ax=axes[1,1];xs=np.arange(10)
def polar_sums(z):
    return np.array([sum(z[i] for i,r in enumerate(rec) if r['key'][2]==p) for p in range(9,-1,-1)])
for y,l,c in [(frac1,'Доп. объём W4B20','#315d88'),(frac2,'Пристеночное W5B2','#d36e47'),(fract,'Время H2, 50–25 с','#719a65')]:
    ax.plot(xs,polar_sums(y),marker='o',lw=2,label=l,color=c)
ax.set_xticks(xs,[f'{v:.0f}' for v in theta_mid]);ax.set_xlabel('Полярный угол θ, градусы')
ax.set_ylabel('Доля суммарного |Δ| в угловой полосе')
ax.set_title('Приполюсная локализация по трём сравнениям',fontsize=11.5)
ax.grid(alpha=.22);ax.legend(fontsize=9,loc='upper center')
fig.savefig(PNG_OUT,facecolor='white')
print(TXT_OUT.read_text(encoding='utf-8'))
print(PNG_OUT, CSV_OUT)
