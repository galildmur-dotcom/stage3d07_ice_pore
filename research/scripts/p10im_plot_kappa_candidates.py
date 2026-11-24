#!/usr/bin/env python3
"""Visual comparison of P10IM candidate spatial κ profiles (phi maximum)."""
import csv
import sys

import matplotlib.pyplot as plt
import numpy as np


def main(source,target):
    with open(source,newline='') as f:rows=list(csv.DictReader(f))
    names=['source_kappa_M0_M1']+[f'beta_{x}_kappa_smoothed' for x in ('0p0','0p1','0p25','0p5')]
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    titles=['Old κ (M0→M1)','M3 candidate: thermal 0%','M3 candidate: thermal 10%',
            'M3 candidate: thermal 25%','M3 candidate: thermal 50%']
    for ax,key,title in zip(axes.flat,names,titles):
        data=np.full((10,10),np.nan)
        for r in rows:
            y=int(r['mu_bin']);x=int(r['radial_bin']);v=float(r[key])
            data[y,x]=v if np.isnan(data[y,x]) else max(v,data[y,x])
        im=ax.imshow(data,cmap='viridis',origin='lower',vmin=0,vmax=1,aspect='auto')
        ax.set_title(title)
        ax.set_xlabel('radial bin from pore wall')
        ax.set_ylabel('mu bin, south (0) → north (9)')
        ax.axvline(4.5,color='red',ls='--',lw=.9)
        for y in (0,9):
            ax.add_patch(plt.Rectangle((-.5,y-.5),5,1,fill=False,edgecolor='red',lw=1))
    axes.flat[5].axis('off')
    fig.colorbar(im,ax=axes.flat[:5],shrink=.8,label='normalized κ ∈ [0,1]')
    fig.suptitle('P10IM source-only κ: max over 12 azimuth bins (not yet CAD/Gmsh)',fontsize=14)
    fig.savefig(target,dpi=160)
    plt.close(fig)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
