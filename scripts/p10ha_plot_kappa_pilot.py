#!/usr/bin/env python3
"""Inspect distinct azimuth and polar bins; not a physical mesh plot."""
import csv
from pathlib import Path
import sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(source,target):
    with Path(source).open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
    assert len(rows)==1200
    keys=('kappa25_smooth','kappa25_mechanical_only')
    fields={k:np.array([float(r[k]) for r in rows]).reshape(10,10,12) for k in keys}
    fig,axs=plt.subplots(2,2,figsize=(12,8.6),layout='constrained')
    for i,ir in enumerate((0,3)):
        for j,k in enumerate(keys):
            ax=axs[i,j];img=ax.imshow(fields[k][ir],origin='lower',aspect='auto',vmin=0,vmax=1,
                                        cmap='viridis',interpolation='nearest')
            ax.set_title(f"{'All active components' if j==0 else 'Mechanical components only'}; radial shell {ir}")
            ax.set_xlabel('Azimuth φ bin, retained (12 sectors)')
            ax.set_ylabel('Polar μ bin, retained (10 bands)')
            ax.set_xticks([0,3,6,9,11]);ax.set_yticks([0,1,4,8,9]);
    fig.colorbar(img,ax=axs.ravel().tolist(),label='Source-only smooth κ, no 3D Gmsh field',shrink=.79)
    fig.suptitle('P10HA: sensitivity of spatial κ to physical-component weighting',fontsize=13)
    fig.savefig(target,dpi=170,bbox_inches='tight')
    plt.close(fig)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
