#!/usr/bin/env python3
"""P10IL scientific heatmaps of M1 -> M2 signed spatial jpeak derivatives."""
from collections import defaultdict
import csv
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm


def main(source,output):
    signed=np.zeros((10,10))
    absolute=np.zeros((10,10))
    with Path(source).open(newline='') as f:
        for r in csv.DictReader(f):
            i=int(r['radial_bin']);j=int(r['mu_bin'])
            v=float(r['M2_minus_M1_total_per_m'])
            signed[j,i]+=v
            absolute[j,i]+=abs(v)
    fig,(a,b)=plt.subplots(1,2,figsize=(13,5.5),constrained_layout=True)
    vmax=max(abs(signed.min()),abs(signed.max()))
    a.imshow(signed,origin='lower',aspect='auto',cmap='RdBu_r',
             norm=TwoSlopeNorm(vcenter=0,vmin=-vmax,vmax=vmax))
    im=b.imshow(absolute,origin='lower',aspect='auto',cmap='magma')
    radial=['0–.02','.02–.05','.05–.1','.1–.25','.25–.5',
            '.5–1','1–2','2–5','5–15','>15']
    for panel in (a,b):
        panel.set_xticks(range(10),radial,rotation=55,ha='right')
        panel.set_yticks(range(10),[f'{-0.9+j*0.2:+.1f}' for j in range(10)])
        panel.set_xlabel('Distance from pore wall, mm')
        panel.set_ylabel('Polar cos(theta) bin center (south → north)')
        panel.axvline(4.5,color='cyan',lw=1.2,ls='--')
        for j in (0,9):
            for i in range(5):
                panel.add_patch(plt.Rectangle((i-.5,j-.5),1,1,
                                               fill=False,edgecolor='cyan',lw=1.2))
    a.set_title('Signed M2−M1 contribution, m⁻¹\n(sum over 12 azimuth sectors)')
    b.set_title('|M2−M1| spatial sum, m⁻¹\n(sum of 12 absolute sector contributions)')
    fig.colorbar(im,ax=b,label='Absolute difference, m⁻¹')
    fig.suptitle('P10IL: physical R/EDV_VAR jpeak derivative, same dt=25 s',fontsize=13)
    fig.savefig(output,dpi=165)
    plt.close(fig)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
