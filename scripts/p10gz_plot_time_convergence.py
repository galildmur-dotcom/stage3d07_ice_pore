#!/usr/bin/env python3
"""Static scientific summary from independently audited P10GZ numeric JSON."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(source,target):
    d=json.loads(Path(source).read_text(encoding='utf-8'))['result']
    dt=np.array([150,75,60,50,45,36,25],int)
    c0='#2553a4'; c1='#c55c2c'
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,
                          'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,2,figsize=(12,7.8),layout='constrained')
    for mesh,col in [('M0',c0),('M1',c1)]:
        vals=np.array([d['grids'][mesh][str(int(x))]['global']['jpeak']['D_R'] for x in dt])
        axs[0,0].plot(dt,vals,'o-',color=col,label=mesh,lw=1.8,markersize=5)
        errs=np.array([d['grids'][mesh][str(int(x))]['spatial_integrated_L1_vs_25']['total_per_m'] for x in dt])
        axs[0,1].plot(dt,errs,'o-',color=col,label=mesh,lw=1.8,markersize=5)
    axs[0,0].set_title(r'Global $D_R j_{peak}$ (signed)')
    axs[0,0].set_ylabel(r'$D_R j_{peak}$, m$^{-1}$')
    axs[0,0].legend(frameon=False)
    axs[0,1].set_title('Time uncertainty: spatial bins integrated over all t')
    axs[0,1].set_ylabel(r'$\sum_{spatial}|G_{\Delta t}-G_{25}|$, m$^{-1}$')
    axs[0,1].legend(frameon=False)
    raw=np.array([d['intermesh'][str(int(x))]['jpeak_local_4D_L1'] for x in dt])
    ag=np.array([d['intermesh'][str(int(x))]['time_integrated_spatial_L1_by_component']['total_per_m'] for x in dt])
    axs[1,0].plot(dt,raw,'o-',color='#777777',lw=1.8,label='Native signed 4D bins')
    axs[1,0].plot(dt,ag,'s-',color='#167d72',lw=1.8,label='Time-integrated spatial bins')
    axs[1,0].set_title('M1–M0: L1 of binwise signed differences')
    axs[1,0].set_ylabel(r'L1, m$^{-1}$')
    axs[1,0].legend(frameon=False,fontsize=9)
    windows=[25,50,75,150]
    ratios=[d['reconstructed_4D_time_window_sensitivity'][str(x)]['noise_to_signal_ratio']*100
            for x in windows]
    axs[1,1].bar([str(w) for w in windows],ratios,color='#be8b4a',width=.58)
    axs[1,1].set_title('Time-slice sensitivity, 36 s vs 25 s')
    axs[1,1].set_xlabel('Reconstructed common time window, s')
    axs[1,1].set_ylabel('Time variation / crossmesh signal, %')
    for x,y in zip(range(4),ratios):
        axs[1,1].text(x,y+0.65,f'{y:.1f}%',ha='center',fontsize=9)
    for ax in axs.flat[:3]:
        ax.set_xlabel(r'$\Delta t$, s (smaller toward right)')
        ax.invert_xaxis()
        ax.grid(alpha=.18)
    axs[1,1].grid(axis='y',alpha=.18)
    axs[1,1].set_ylim(0,max(ratios)*1.2)
    fig.suptitle('Stage3D07 P10GZ  |  seven-level temporal study on M0 and M1',fontsize=13)
    fig.text(.5,-.012,'4D time-slice bars use conservative piecewise-constant reconstruction; '
            'they are diagnostic, not exact common-time QP reintegration.',
            ha='center',fontsize=8,color='#555555')
    Path(target).parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,dpi=175,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
