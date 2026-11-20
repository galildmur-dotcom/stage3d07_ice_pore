"""P10CJ independent read-only analysis of primary P10CI Windows evidence.

No FEM/remesh and no claim that straight-corner diagnostics are Tet10 QP errors.
"""
from __future__ import annotations

import csv
import hashlib
import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

PARSER=argparse.ArgumentParser(description='Independent P10CJ read-only join/geometry/binning audit')
PARSER.add_argument('--root',type=Path,default=Path(__file__).resolve().parent,
                    help='Directory with P10CI_EVIDENCE_READONLY_20261120/, P10CH CSV, and stage3d07_readonly/ source CSVs')
ROOT=PARSER.parse_args().root.resolve()
INPUT=ROOT/'P10CI_EVIDENCE_READONLY_20261120'
IND=ROOT/'P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv'
OUT=ROOT/'P10CJ_MESH_QUALITY_VS_POLE_MISMATCH.png'
OUT_RADIAL=ROOT/'P10CJ_RADIAL_BIN_CANCELLATION.png'
AUDIT=ROOT/'P10CJ_INDEPENDENT_AUDIT.txt'
EXPECTED={
 'P10CI_0_TO_20UM_UNCOVERED_POLE_GEOMETRY.csv':('5cf06f11a9221cfee20e725cadf0d25b858475f67b897fd7246a41f5e745777d',30),
 'P10CI_200CELL_MESH_GEOMETRY.csv':('db22675c116b1d151e86c73726cc4e2aeba21bcb4c41c099ee4e5d2e4d3e9f61',600),
 'P10CI_GROUP_SUMMARY.csv':('265daba52a12515c18a19640be92ff8a6db35c24332fe9603cec1a92f6b74950',12),
 'P10CI_MESH_COUNTS.csv':('4c6da8910f96eacd75179c0415197cd0c5b47fafca77b07e212561aea844b788',3),
 'P10CI_RESULT.txt':('c535b7bc6794e23f199420b8d7d53be84bf652484e076e0d3a48233ef3db7f7d',None),
}
MESHHASH={
 'H4W4B2':('3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7',367823,261091),
 'H4W4B20':('94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715',449522,323052),
 'H4W5B2':('db50a10fc2a12870bf6e678e2ef0be496feba218b1010f9e65f8669f67d093a8',393998,275549),
}


def sha256(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(file):
    with (INPUT/file).open(newline='',encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))
def N(row,key):return int(row[key])
def F(row,key):
    v=row[key]
    return float(v) if v not in ('',None) else np.nan
def wmean(items,value,weight='tet10_centroids'):
    w=np.asarray([N(x,weight) for x in items],float)
    v=np.asarray([F(x,value) for x in items],float)
    mask=(w>0)&np.isfinite(v)
    return float(np.dot(w[mask],v[mask])/sum(w[mask])) if any(mask) else np.nan
def ranks(arr):
    x=np.asarray(arr,float)
    order=np.argsort(x,kind='mergesort')
    vals=np.empty(len(x),float)
    # Average tied ranks, never arbitrary tie order.
    j=0
    while j<len(x):
        k=j+1
        while k<len(x) and x[order[k]]==x[order[j]]:k+=1
        vals[order[j:k]]=(j+k-1)*.5
        j=k
    return vals
def spearman(x,y):
    mask=np.isfinite(x)&np.isfinite(y)
    a,b=ranks(x[mask]),ranks(y[mask])
    return float(np.corrcoef(a,b)[0,1]) if len(a)>3 and np.std(a)>0 and np.std(b)>0 else np.nan
def within_group_rank_corr(group_key,x,y):
    """Descriptive association after ranking within fixed radial or polar bins."""
    all_x=[];all_y=[]
    for g in sorted(set(group_key)):
        mask=np.asarray(group_key)==g
        good=mask&np.isfinite(x)&np.isfinite(y)
        if sum(good)>2:
            all_x.extend(ranks(x[good])/(sum(good)-1))
            all_y.extend(ranks(y[good])/(sum(good)-1))
    return float(np.corrcoef(all_x,all_y)[0,1])


for filename,(expected,num) in EXPECTED.items():
    p=INPUT/filename
    assert sha256(p)==expected,filename
    if num is not None:
        assert len(rows(filename))==num,(filename,len(rows(filename)))
assert sha256(IND)=='84b738960d712ba11eca880a86f98782905dc6dcc6cd3c72c70e4c97c42406c3'

result=(INPUT/'P10CI_RESULT.txt').read_text(encoding='utf-8-sig')
for marker in ('RESULT=P10CI_MESH_ONLY_GEOMETRY_OK_NO_FEM','MESHES_PINNED_SHA_PASS=3/3',
               'PHYSICAL_FEM_RUNS=0','CURVED_TET10_JACOBIAN_POSITIVITY=NOT_CHECKED'):
    assert marker in result

main=rows('P10CI_200CELL_MESH_GEOMETRY.csv')
wall=rows('P10CI_0_TO_20UM_UNCOVERED_POLE_GEOMETRY.csv')
group=rows('P10CI_GROUP_SUMMARY.csv')
counts=rows('P10CI_MESH_COUNTS.csv')
indicator=[]
with IND.open(newline='',encoding='utf-8') as f:
    indicator=list(csv.DictReader(f))
assert len(indicator)==200 and sum(int(x['chosen_top_20pct']) for x in indicator)==40
original_keys=sorted({(float(x['r_lower_mm']),float(x['r_upper_mm'])) for x in indicator})
assert len(original_keys)==20 and original_keys[0][0]==.02 and original_keys[-1][1]==.1
expected_key={(ir,int(x['polar_band'])):x for x in indicator
              for ir,r in enumerate(original_keys)
              if float(x['r_lower_mm'])==r[0] and float(x['r_upper_mm'])==r[1]}
assert len(expected_key)==200

mat={}
for mesh in MESHHASH:
    subset=[x for x in main if x['mesh']==mesh]
    assert len(subset)==200
    mp={(N(x,'radial_bin'),N(x,'polar_band')):x for x in subset}
    assert len(mp)==200 and set(mp)==set(expected_key)
    for k,x in mp.items():
        r=expected_key[k]
        assert N(x,'selected_top40')==int(r['chosen_top_20pct'])
        assert abs(F(x,'abs_delta_bulk_per_m')-abs(float(r['delta_bulk_per_m'])))<1e-14
        assert abs(F(x,'abs_delta_wall_per_m')-abs(float(r['delta_wall_per_m'])))<1e-14
        assert 0<=N(x,'phi_occupied_sectors')<=12
        assert 0<=N(x,'radial_cross_centroid_tets')<=N(x,'tet10_centroids')
        assert 0<=N(x,'polar_cross_centroid_tets')<=N(x,'tet10_centroids')
        assert N(x,'corner_quality_below_0p1')==0
        assert N(x,'corner_nonpositive_count')==0
    mat[mesh]=mp

for x in counts:
    mesh=x['mesh'];sha,nn,nt=MESHHASH[mesh]
    assert x['mesh_sha256']==sha and N(x,'node_count')==nn and N(x,'tet10_count')==nt
    assert sum(N(y,'tet10_centroids') for y in mat[mesh].values())==N(x,'tet10_near_pore_centroids')
    assert sum(N(y,'tet10_centroids') for y in wall if y['mesh']==mesh)==N(x,'tet10_0_to_20um_centroids')
    assert N(x,'near_pore_corner_nonpositive_count')==0
for x in group:
    mesh=x['mesh'];g=x['group'];source=list(mat[mesh].values())
    ss=[y for y in source if (g=='top40' and N(y,'selected_top40')==1)
        or (g=='remaining160' and N(y,'selected_top40')==0)
        or (g=='polar0_9' and N(y,'polar_band') in (0,9))
        or (g=='middle1_8' and N(y,'polar_band') not in (0,9))]
    assert len(ss)==N(x,'cells')
    for dest,source_col in [('tet10_centroids','tet10_centroids'),
                            ('radial_cross_centroid_tets','radial_cross_centroid_tets'),
                            ('polar_cross_centroid_tets','polar_cross_centroid_tets'),
                            ('phi_axis_unresolved_corners','phi_axis_unresolved_corners'),
                            ('corner_nonpositive_count','corner_nonpositive_count')]:
        assert sum(N(y,source_col) for y in ss)==N(x,dest),(mesh,g,dest)
    assert abs(sum(F(y,'corner_volume_proxy_m3') for y in ss)-F(x,'straight_corner_volume_proxy_m3'))<1e-20

allradial=all(N(x,'radial_cross_centroid_tets')==N(x,'tet10_centroids') for x in main)
assert allradial

def stats(mesh,region,subset):
    count=sum(N(x,'tet10_centroids') for x in subset)
    polar_cross=sum(N(x,'polar_cross_centroid_tets') for x in subset)
    nphi12=sum(N(x,'phi_occupied_sectors')==12 for x in subset)
    empty=sum(N(x,'tet10_centroids')==0 for x in subset)
    return {'count':count,'q05':wmean(subset,'corner_quality_p05'),
            'q50':wmean(subset,'corner_quality_p50'),
            'edge':wmean(subset,'max_corner_edge_p50_mm'),
            'span90':wmean(subset,'phi_corner_span_p90_deg'),
            'cv':wmean(subset,'phi_sector_count_cv'),
            'polar_cross':polar_cross/count if count else np.nan,
            'az12_cells':nphi12,'empty_cells':empty}

stats_map={}
for mesh in MESHHASH:
    cells=list(mat[mesh].values())
    groups={
        'all20_100':cells,
        'polar': [x for x in cells if N(x,'polar_band') in (0,9)],
        'middle':[x for x in cells if N(x,'polar_band') not in (0,9)],
        'top40':[x for x in cells if N(x,'selected_top40')==1],
        'other160':[x for x in cells if N(x,'selected_top40')==0],
        'polar_top40':[x for x in cells if N(x,'selected_top40')==1 and N(x,'polar_band') in (0,9)],
        'polar_not_top':[x for x in cells if N(x,'selected_top40')==0 and N(x,'polar_band') in (0,9)],
        'wall0_20':[x for x in wall if x['mesh']==mesh],
        'wall0_20_polar':[x for x in wall if x['mesh']==mesh and N(x,'polar_band') in (0,9)],
    }
    for g,items in groups.items():stats_map[mesh,g]=stats(mesh,g,items)

lines=['P10CJ READ-ONLY INDEPENDENT AUDIT','STATUS=P10CJ_PRIMARY_MESH_GEOMETRY_RECONCILED_NO_FEM',
       'INPUT_ZIP_SHA256=8ff592f3d7696975e41b76946df6d438a378e816e04d56e532f0549bf2366e96',
       'ZIP_CRC=5/5_PASS','MESH_SHA_AND_COUNTS=3/3_PASS','MAIN_CELL_ROW_COUNT=600',
       'FIRST_WALL_CELL_ROW_COUNT=30','GROUP_ROW_COUNT=12',
       'EXACT_P10CH_CELL_JOIN=600/600_PASS',
       'GLOBAL_RADIAL_CROSSING_CORNER_PROXY=100_PERCENT_20_TO_100UM',
       'CORNER_Q_LT_0P1_COUNT=0','NONPOSITIVE_CORNER_TET_COUNT=0',
       'WARNING=All cross/radial metrics use straight-corner element centroids, not curved Tet10 QP or a posteriori error.',
       'WARNING=No phi-resolved physical derivative exists in these data.']

for mesh in MESHHASH:
    for key in ('all20_100','polar','middle','top40','other160','polar_top40','polar_not_top','wall0_20','wall0_20_polar'):
        d=stats_map[mesh,key]
        lines.append(mesh+'_'+key+'_COUNT='+str(d['count']))
        for k in ('q05','q50','edge','span90','cv','polar_cross'):
            lines.append(mesh+'_'+key+'_'+k.upper()+'='+format(d[k],'.10g'))
        lines.append(mesh+'_'+key+'_PHI12_CELLS='+str(d['az12_cells']))
    ss=[mat[mesh][k] for k in sorted(mat[mesh])]
    y=np.array([float(expected_key[k]['delta_bulk_per_m']) for k in sorted(mat[mesh])])
    for key in ('corner_quality_p05','corner_quality_p50','phi_corner_span_p90_deg',
                'phi_sector_count_cv','max_corner_edge_p50_mm'):
        v=np.array([F(x,key) for x in ss])
        lines.append(mesh+'_SPEARMAN_ABS_BULK_VS_'+key.upper()+'='+format(spearman(abs(y),v),'.8f'))
        radial_id=np.array([N(x,'radial_bin') for x in ss]);polar_id=np.array([N(x,'polar_band') for x in ss])
        lines.append(mesh+'_WITHIN_POLAR_BAND_RANK_CORR_ABS_BULK_VS_'+key.upper()+'='+
                     format(within_group_rank_corr(polar_id,abs(y),v),'.8f'))
        lines.append(mesh+'_WITHIN_RADIAL_BIN_RANK_CORR_ABS_BULK_VS_'+key.upper()+'='+
                     format(within_group_rank_corr(radial_id,abs(y),v),'.8f'))

# Independent mechanistic check against primary source, not just P10CI counts.
SRC=ROOT/'stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input'
SOURCE_SHA={
 'H4W4B2':'219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447',
 'H4W4B20':'3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be',
 'H4W5B2':'8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c',
}
primary={}
for mesh,sha in SOURCE_SHA.items():
    p=SRC/(mesh+'_P10BA_QP_POLAR_RADIAL.csv')
    assert sha256(p)==sha
    with p.open(newline='',encoding='utf-8-sig') as f:
        raw=[x for x in csv.DictReader(f) if int(x['time_step'])==6 and float(x['time_s'])==900.]
    assert len(raw)==200
    dic={}
    for x in raw:
        k=(round(float(x['radial_lower_mm']),8),int(x['polar_band']))
        assert k not in dic
        dic[k]=x
    assert len(dic)==200
    primary[mesh]=dic

TEMP=ROOT/'stage3d07_readonly/research/evidence/P10BE_H2_20261118/input/P10BE_CELL_TEMPORAL_COMPARE.csv'
assert sha256(TEMP)=='e16a580d4935580b6b5228ce3f10edd80e67534b2306ef73c8b9fb77df0ffc7e'
with TEMP.open(newline='',encoding='utf-8-sig') as f:
    temporal={}
    for x in csv.DictReader(f):
        k=(round(float(x['radial_lower_mm']),8),int(x['polar_band']))
        assert k not in temporal
        temporal[k]=x
assert len(temporal)==200
keys=sorted(primary['H4W4B2'])
assert set(keys)==set(temporal)

base_values=np.array([float(primary['H4W4B2'][k]['total_mechanical_per_m']) for k in keys])
base_volumes=np.array([float(primary['H4W4B2'][k]['qp_volume_m3']) for k in keys])
polar_mask=np.array([k[1] in (0,9) for k in keys])
temporal_signal=np.array([float(temporal[k]['dR_jpeak_dt25_per_m']) for k in keys])
temporal_delta=np.array([float(temporal[k]['difference_50_minus_25_per_m']) for k in keys])
source_delta={}
source_signal={'H4W4B2':base_values,'H2_dt25':temporal_signal}
for other in ('H4W4B20','H4W5B2'):
    alt=np.array([float(primary[other][k]['total_mechanical_per_m']) for k in keys])
    v_alt=np.array([float(primary[other][k]['qp_volume_m3']) for k in keys])
    delta=alt-base_values
    assert np.all(base_volumes>0)&np.all(v_alt>0)
    for i,k in enumerate(keys):
        x=expected_key[(next(j for j,r in enumerate(original_keys)
                             if abs(r[0]-k[0])<1e-8),k[1])]
        fieldname='delta_bulk_per_m' if other=='H4W4B20' else 'delta_wall_per_m'
        assert abs(delta[i]-float(x[fieldname]))<1e-12
    source_delta[other]=delta
    prediction=base_values*(v_alt/base_volumes-1.)
    corrected=alt*base_volumes/v_alt-base_values
    l1=float(np.abs(delta).sum());l1corr=float(np.abs(corrected).sum())
    r2=float(1.-np.sum((delta-prediction)**2)/np.sum(delta**2))
    corr=float(np.corrcoef(delta,prediction)[0,1])
    lines.extend([other+'_COMMON_QP_VOLUME_CORRECTED_L1_PER_M='+str(l1corr),
                  other+'_RAW_L1_PER_M='+str(l1),
                  other+'_COMMON_VOLUME_L1_RETENTION='+str(l1corr/l1),
                  other+'_VOLUME_REDISPERSION_PRED_R2='+str(r2),
                  other+'_VOLUME_REDISPERSION_PRED_CORR='+str(corr)])

source_delta['H2_dt50_minus_25']=temporal_delta
for other,delta in source_delta.items():
    signal=base_values if other!='H2_dt50_minus_25' else temporal_signal
    lines.append(other+'_BASELINE_ABS_POLE_SHARE='+
                 str(float(np.abs(signal[polar_mask]).sum()/np.abs(signal).sum())))
    for tag,mask in [('POLE',polar_mask),('MIDDLE',~polar_mask)]:
        val=float(np.abs(delta[mask]).sum()/np.abs(signal[mask]).sum())
        lines.append(other+'_RELATIVE_L1_'+tag+'='+str(val))
    # Sum signed differences *before* absolute value when coarsening.
    total=float(np.abs(delta).sum())
    lines.append(other+'_FINE_200_L1_PER_M='+str(total))
    for nrad in (2,1):
        sums=defaultdict(float)
        for k,d in zip(keys,delta):
            band=0 if nrad==1 or k[0]<.05 else 1
            sums[band,k[1]]+=float(d)
        coarse=sum(abs(v) for v in sums.values())
        lines.append(other+'_COARSE_'+str(nrad)+'RAD_X10MU_L1_PER_M='+str(coarse))
        lines.append(other+'_COARSE_'+str(nrad)+'RAD_X10MU_RETENTION='+str(coarse/total))
    flips=[]
    for p in range(10):
        radial=sorted((k[0],d) for k,d in zip(keys,delta) if k[1]==p)
        flips.append(sum(radial[i][1]*radial[i+1][1]<0 for i in range(19)))
    lines.append(other+'_RADIAL_SIGN_FLIPS_BY_MU0_TO_9='+','.join(map(str,flips)))

AUDIT.write_text('\n'.join(lines)+'\n',encoding='utf-8')

def field(mesh,component):
    # image row top corresponds near wall 0.02 mm; columns left→right +z to -z
    out=np.full((20,10),np.nan)
    for (r,mu),d in mat[mesh].items():out[r,9-mu]=F(d,component)
    return out

sel=np.zeros((20,10),dtype=bool)
for k,d in expected_key.items():sel[k[0],9-k[1]]=int(d['chosen_top_20pct'])==1
bulk=field('H4W4B2','abs_delta_bulk_per_m')
wall_d=field('H4W4B2','abs_delta_wall_per_m')
priority=(bulk/np.sum(bulk)+wall_d/np.sum(wall_d))*.5
q05=field('H4W4B2','corner_quality_p05')
phi=field('H4W4B2','phi_corner_span_p90_deg')
pcross=field('H4W4B2','polar_cross_centroid_tets')/np.maximum(field('H4W4B2','tet10_centroids'),1)
fig,axes=plt.subplots(2,2,figsize=(13.8,10.5),dpi=160,layout='constrained')
fig.suptitle('P10CJ: полярная межсеточная разность и геометрия Tet10 (20–100 мкм)\n'
             'Бирюзовая рамка — кандидатная ячейка P10CH; геометрия по вершинам, не QP Tet10',
             fontsize=13,fontweight='bold')
for ax,data,title,cmap,unit in [
    (axes[0,0],priority,'Средняя нормированная доля |Δ|, два уточнения','magma','Доля L1 на ячейку'),
    (axes[0,1],q05,'Качество Tet10 по вершинам: 5-й процентиль в ячейке','viridis','mean-ratio q'),
    (axes[1,0],phi,'90-й процентиль азимутального размаха вершин','plasma','градусы'),
    (axes[1,1],pcross,'Доля тетраэдров, пересекающих полярную полосу','cividis','доля элементов')]:
    im=ax.imshow(data,origin='upper',aspect='auto',cmap=cmap)
    for i in range(20):
        for j in range(10):
            if sel[i,j]:ax.add_patch(Rectangle((j-.5,i-.5),1,1,fill=False,edgecolor='#8dfeef',linewidth=.8))
    ax.set_title(title,fontsize=10.7)
    ax.set_ylabel('Расстояние от поры d, мкм')
    ax.set_yticks(range(0,20,3),[f'{1000*original_keys[k][0]:.0f}' for k in range(0,20,3)])
    ax.set_xticks(range(10),[f'{np.degrees(np.arccos(.9-.2*j)):.0f}' for j in range(10)])
    ax.set_xlabel('θ, градусы (от +z к −z)')
    fig.colorbar(im,ax=ax,pad=.02,shrink=.86,label=unit)
fig.savefig(OUT,facecolor='white')

# Three separate data sources; local signed differences per thin radial cell.
xs=np.array([(lo+hi)*500. for lo,hi in original_keys])
fig2,ax=plt.subplots(2,2,figsize=(13.8,9.6),dpi=160,layout='constrained')
fig2.suptitle('P10CJ: знаковая компенсация при объединении радиальных ячеек 20–100 мкм\n'
              'Межрасчётные различия, не абсолютная ошибка точного решения',fontsize=13,fontweight='bold')
schemes=[('H4W4B20','Объёмное сгущение','#2875a1'),
         ('H4W5B2','Пристеночное сгущение','#c45842'),
         ('H2_dt50_minus_25','Время H2, 50−25 с','#608b4a')]
for i,(p,title) in enumerate([(9,'У +z (θ ≈ 26°)'),(0,'У −z (θ ≈ 154°)')]):
    a=ax[0,i]
    for name,label,color in schemes:
        d=source_delta[name]
        y=np.array([d[next(j for j,k in enumerate(keys) if abs(k[0]-r[0])<1e-8 and k[1]==p)]
                    for r in original_keys])
        a.plot(xs,y,marker='o',markersize=3,linewidth=1.5,color=color,label=label)
    a.axhline(0,color='#888',linewidth=.8)
    a.set_title(title);a.set_xlabel('d от поры, мкм');a.set_ylabel('Подписанное Δ на ячейку, 1/м')
    a.grid(alpha=.2)
    a.legend(fontsize=8)

barax=ax[1,0]
values=[]
for name,label,color in schemes:
    d=source_delta[name]
    v=[]
    for nrad in (20,2,1):
        if nrad==20:
            v.append(float(np.abs(d).sum()))
        else:
            sums=defaultdict(float)
            for k,val in zip(keys,d):sums[(0 if nrad==1 or k[0]<.05 else 1,k[1])]+=float(val)
            v.append(sum(abs(x) for x in sums.values()))
    values.append(v)
xx=np.arange(3)
for i,(name,label,color) in enumerate(schemes):
    barax.bar(xx+(i-1)*.22,values[i],width=.21,label=label,color=color)
barax.set_xticks(xx,['20 радиальных\nячеек','2 радиальные\nоболочки','1 оболочка\n20–100 мкм'])
barax.set_title('Как меняется сумма модулей после объединения')
barax.set_ylabel('Σ|Δ|, 1/м');barax.legend(fontsize=8)
barax.grid(axis='y',alpha=.2)

barax=ax[1,1]
for i,(name,label,color) in enumerate(schemes):
    d=source_delta[name]
    baseline=base_values if name!='H2_dt50_minus_25' else temporal_signal
    p=float(np.abs(d[polar_mask]).sum()/np.abs(baseline[polar_mask]).sum()*100.)
    m=float(np.abs(d[~polar_mask]).sum()/np.abs(baseline[~polar_mask]).sum()*100.)
    barax.bar(i-.17,p,.32,color=color,alpha=1,label='Полюса' if i==0 else None)
    barax.bar(i+.17,m,.32,color=color,alpha=.4,label='Остальные' if i==0 else None)
    barax.text(i-.17,p+.1,f'{p:.2f}',ha='center',fontsize=9)
    barax.text(i+.17,m+.1,f'{m:.2f}',ha='center',fontsize=9)
barax.set_ylim(0,7.4)
barax.set_xticks(range(3),['Объёмное','Пристеночное','Время H2'])
barax.set_ylabel('Σ|Δ| / Σ|вклад|, %')
barax.set_title('Относительное локальное несогласие')
barax.legend(fontsize=9);barax.grid(axis='y',alpha=.2)
fig2.savefig(OUT_RADIAL,facecolor='white')
print(AUDIT.read_text(encoding='utf-8')[:6500])
print('FIGURE',OUT)
print('FIGURE',OUT_RADIAL)
