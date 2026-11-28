#!/usr/bin/env python3
"""Signed radial/time component projections for read-only P10LE diagnosis."""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from p10kw_m8_m7_signed4d_audit import read_zip,KEY

PARTS=['mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m']

def table(a,b,field):
    x=a.merge(b,on=KEY,suffixes=('_old','_new'),validate='one_to_one')
    x=x[x.region=='VOLUME'].copy()
    x['delta']=x[field+'_new']-x[field+'_old']
    return x.groupby(['radial_bin','step']).delta.sum().unstack('step').sort_index().to_numpy()

def main():
    ap=argparse.ArgumentParser()
    for n in ('m7','m8','m9','out'):ap.add_argument('--'+n,required=True)
    v=vars(ap.parse_args());d=[read_zip(v[m])[0] for m in ('m7','m8','m9')]
    fig,axes=plt.subplots(3,2,figsize=(12.6,9.2),sharex=True,sharey=True,constrained_layout=True)
    for row,part in enumerate(PARTS):
        mats=[table(d[0],d[1],part),table(d[1],d[2],part)]
        vmax=max(abs(z).max() for z in mats)
        for col,mat in enumerate(mats):
            im=axes[row,col].imshow(mat,origin='lower',aspect='auto',cmap='RdBu_r',
                 norm=TwoSlopeNorm(vmin=-vmax,vcenter=0,vmax=vmax),extent=[.5,36.5,-.5,9.5])
            axes[row,col].axvline(30.5,color='black',lw=.7)
            axes[row,col].set_title(('M7→M8' if col==0 else 'M8→M9')+' '+part.replace('_per_m',''))
            axes[row,col].set_ylabel('radial bin (0 = 0–20 μm)')
            axes[row,col].set_xlabel('step (25 s)')
            axes[row,col].set_yticks(range(10))
            axes[row,col].set_xticks([1,6,12,18,24,30,36])
            fig.colorbar(im,ax=axes[row,col],shrink=.72,label='signed Δ [m⁻¹ / r bin / step]')
    fig.suptitle('Exact signed4D component differences, summed over θ and φ\n'
                 'Rows: mechanical explicit / equilibrium / history; columns: successive grids')
    fig.savefig(v['out'],dpi=155)
    print(v['out'])

if __name__=='__main__':main()
