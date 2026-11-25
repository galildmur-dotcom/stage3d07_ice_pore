#!/usr/bin/env python3
"""P10MS: source-vs-outcome 4D M10/M11/M12, read-only no mesh/FEM."""
import io,json,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[2]
ZIP={10:ROOT/'upload/P10LY_M10_FIRST_FULL4D_EVIDENCE.zip',
     11:ROOT/'upload/P10MI_M11_FIRST_FULL4D_EVIDENCE.zip',
     12:ROOT/'upload/P10MO_M12_FIRST_FULL4D_EVIDENCE.zip'}
SOURCE=ROOT/'p10mk_m12_source/P10MK_M12_M11_MINUS_M10_REAL_SIGNED4D_1200_BINS.csv'
OUT=ROOT/'p10ms_m12_diagnostic'
SPACE=['radial_bin','mu_bin','phi_bin']
KEY=['step','region']+SPACE
COMP=['mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
      'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m']

def load(mesh):
    with zipfile.ZipFile(ZIP[mesh]) as z:
        assert z.testzip() is None
        df=pd.read_csv(io.BytesIO(z.read('P10DD_SIGNED_R_THETA_PHI_T.csv')))
    assert len(df)==43236 and set(df.mesh)=={f'M{mesh}'} and not df[KEY].duplicated().any()
    assert np.abs(df[COMP].sum(axis=1)-df.total_per_m).max()<1e-9
    return df.sort_values(KEY).reset_index(drop=True)

def main():
    if OUT.exists():raise RuntimeError('P10MS output exists; no overwrite')
    x={m:load(m) for m in ZIP}
    for a,b in ((10,11),(11,12)):
        assert x[a][KEY].equals(x[b][KEY])
        for col in ('time_start_s','time_end_s','r_lower_mm','r_upper_mm',
                    'theta_lower_rad','theta_upper_rad','phi_lower_rad','phi_upper_rad'):
            assert np.allclose(x[a][col],x[b][col],rtol=0,atol=1e-12,equal_nan=True),col
    source=pd.read_csv(SOURCE).sort_values(SPACE).reset_index(drop=True)
    assert len(source)==1200 and not source[SPACE].duplicated().any()
    vol=x[12].region.eq('VOLUME')
    old=(x[11].loc[vol,'total_per_m'].to_numpy()-x[10].loc[vol,'total_per_m'].to_numpy())
    new=(x[12].loc[vol,'total_per_m'].to_numpy()-x[11].loc[vol,'total_per_m'].to_numpy())
    base=x[12].loc[vol,SPACE+['step']].copy()
    base['old_abs']=np.abs(old);base['new_abs']=np.abs(new)
    base['old_signed']=old;base['new_signed']=new
    grouped=base.groupby(SPACE).agg(old_L1=('old_abs','sum'),new_L1=('new_abs','sum'),
                old_signed=('old_signed','sum'),new_signed=('new_signed','sum')).reset_index()
    assert len(grouped)==1200
    grouped=grouped.sort_values(SPACE).reset_index(drop=True)
    assert grouped[SPACE].equals(source[SPACE])
    for col in ('beta_0.1_score','late_l1_per_m','all_l1_per_m'):
        grouped[col]=source[col]
    assert np.max(np.abs(grouped.old_L1-source.all_l1_per_m))<1e-11
    grouped['L1_reduction']=grouped.old_L1-grouped.new_L1
    grouped['L1_ratio']=np.divide(grouped.new_L1,grouped.old_L1,
                                 out=np.full(len(grouped),np.nan),where=grouped.old_L1>1e-15)
    grouped['polar']=grouped.mu_bin.isin((0,9))
    grouped['nearwall']=grouped.radial_bin.isin((0,1,2))
    grouped['critical']=grouped.polar&grouped.nearwall
    grouped['late_old_target']=grouped.late_l1_per_m
    grouped['late_new_actual']=base[base.step>=31].groupby(SPACE).new_abs.sum().reset_index().new_abs.to_numpy()
    score=grouped['beta_0.1_score']
    rank=score.rank(method='average')
    delta=grouped['L1_reduction']
    qa={'protocol':'P10MS_M12_ACTUAL_REFINEMENT_PRIORITY_VS_4D_OUTCOME',
        'status':'READONLY_ALIGNED_4D_SOURCE_TARGET_AUDIT_PASS',
        'full_bins':43236,'volume_bins':43200,'spatial_bins':1200,
        'source_score_definition':'0.4 all-time absolute L1 + 0.6 last6 L1, polar factor 1.2, C2 interpolation',
        'global_old_L1':float(grouped.old_L1.sum()),
        'global_new_L1':float(grouped.new_L1.sum()),
        'global_L1_ratio':float(grouped.new_L1.sum()/grouped.old_L1.sum()),
        'source_score_vs_signed_L1_reduction_pearson':float(np.corrcoef(score,delta)[0,1]),
        'source_score_vs_signed_L1_reduction_spearman':float(rank.corr(delta.rank())),
        'consecutive_full4d_cosine':float(np.dot(old,new)/(np.linalg.norm(old)*np.linalg.norm(new))),
        'groups':{},'top_target_bins':{},'top_persistent_bins':{},
        'new_mesh_generation_attempts':0,'new_FEM_attempts':0,
        'caveat':'Priority score is only an intended C2 mesh-size field, not a measured local effective volume reduction or causal test'}
    for name,mask in [('polar',grouped.polar),('nonpolar',~grouped.polar),
                      ('nearwall_0_2',grouped.nearwall),('polar_nearwall_0_2',grouped.critical),
                      ('south',grouped.mu_bin.eq(0)),('north',grouped.mu_bin.eq(9))]:
        z=grouped[mask]
        qa['groups'][name]={'bins':len(z),'old_L1':float(z.old_L1.sum()),
                            'new_L1':float(z.new_L1.sum()),
                            'ratio_new_to_old':float(z.new_L1.sum()/z.old_L1.sum()) if z.old_L1.sum()>0 else None}
    for frac in (.05,.1,.2,.3):
        keep=grouped.sort_values('beta_0.1_score',ascending=False).head(int(1200*frac))
        qa['top_target_bins'][str(frac)]={'count':len(keep),'old_L1':float(keep.old_L1.sum()),
           'new_L1':float(keep.new_L1.sum()),
           'ratio_new_to_old':float(keep.new_L1.sum()/keep.old_L1.sum()),
           'new_error_L1_share':float(keep.new_L1.sum()/grouped.new_L1.sum())}
    for name,part in [('highest_new_L1',grouped.nlargest(10,'new_L1')),
                      ('largest_L1_increase',grouped.nsmallest(10,'L1_reduction'))]:
        qa['top_persistent_bins'][name]=part[SPACE+['old_L1','new_L1','L1_reduction','beta_0.1_score']].to_dict('records')
    OUT.mkdir()
    grouped.to_csv(OUT/'P10MS_1200_BIN_SOURCE_VS_4D_OUTCOME.csv',index=False,float_format='%.17g')
    (OUT/'P10MS_DIAGNOSTIC_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.dpi':160,
       'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,2,figsize=(13,10),layout='constrained')
    def heat(column):
        table=grouped.groupby(['radial_bin','mu_bin'])[column].sum().unstack(fill_value=0)
        return table.to_numpy()
    oldmap=heat('old_L1');newmap=heat('new_L1');change=oldmap-newmap
    for ax,mat,title in [(axs[0,0],oldmap,'M10→M11: L1 по радиусу и широте'),
                         (axs[0,1],newmap,'M11→M12: L1 по радиусу и широте')]:
        im=ax.imshow(mat,aspect='auto',origin='lower',vmin=0,vmax=max(oldmap.max(),newmap.max()),cmap='magma')
        ax.set(xlabel='Индекс широты μ',ylabel='Индекс радиального слоя',title=title)
        ax.set_xticks(range(10));ax.set_yticks(range(10))
        fig.colorbar(im,ax=ax,shrink=.75,label='L1, м⁻¹')
    m=abs(change).max();im=axs[1,0].imshow(change,aspect='auto',origin='lower',vmin=-m,vmax=m,cmap='RdBu')
    axs[1,0].set(xlabel='Индекс широты μ',ylabel='Индекс радиального слоя',
                  title='Снижение L1: положительное = улучшение')
    axs[1,0].set_xticks(range(10));axs[1,0].set_yticks(range(10))
    fig.colorbar(im,ax=axs[1,0],shrink=.75,label='L1(M10→M11) − L1(M11→M12), м⁻¹')
    # Group score by deciles: report aggregate rather than unstable per-bin ratios.
    ordered=grouped.sort_values('beta_0.1_score').reset_index(drop=True)
    groups=np.array_split(np.arange(len(ordered)),10)
    ratios=[ordered.iloc[g].new_L1.sum()/ordered.iloc[g].old_L1.sum() if ordered.iloc[g].old_L1.sum()>0 else np.nan for g in groups]
    axs[1,1].bar(range(1,11),ratios,color=['#b65752' if r>1 else '#2d8f89' for r in ratios])
    axs[1,1].axhline(1,color='#333',ls='--')
    axs[1,1].set(xlabel='Дециль целевого показателя M12 (10 = максимальный)',
       ylabel='L1(M11→M12) / L1(M10→M11)',title='Эффективность в группах приоритета')
    axs[1,1].set_xticks(range(1,11))
    fig.suptitle('Stage3D07 P10MS — где адаптация M12 не улучшила локальную 4D-разность',
                 fontsize=15,weight='bold')
    fig.savefig(OUT/'P10MS_M12_ADAPTATION_EFFICIENCY_4D.png',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print(json.dumps({k:qa[k] for k in ('status','global_L1_ratio',
        'source_score_vs_signed_L1_reduction_spearman','consecutive_full4d_cosine',
        'groups','top_target_bins')},indent=2))

if __name__=='__main__':main()
