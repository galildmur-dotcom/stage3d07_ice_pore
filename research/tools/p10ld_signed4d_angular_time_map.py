#!/usr/bin/env python3
"""Plot exact (r,phi)-aggregated signed4D corrections vs polar bin and time.

Each image panel is a 2D projection of the full 4D mesh-pair difference,
not a raw 4D field, convergence estimator, or error bound.
"""
import argparse
import io
import zipfile
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

KEY=['step','region','radial_bin','mu_bin','phi_bin']

def read(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        return pd.read_csv(io.BytesIO(z.read('P10DD_SIGNED_R_THETA_PHI_T.csv')))

def delta(a,b):
    x=read(a).merge(read(b),on=KEY,suffixes=('_a','_b'),validate='one_to_one')
    assert len(x)==43236
    x=x[x.region=='VOLUME'].copy()
    x['signed']=x.total_per_m_b-x.total_per_m_a
    x['absolute']=x.signed.abs()
    out=x.groupby(['step','mu_bin'])[['signed','absolute']].sum()
    return [out[name].unstack('mu_bin').sort_index().to_numpy().T for name in ('signed','absolute')]

def main():
    ap=argparse.ArgumentParser()
    for name in ['m7','m8','m9','out']:ap.add_argument('--'+name,required=True)
    a=ap.parse_args()
    p=delta(a.m7,a.m8);q=delta(a.m8,a.m9)
    fig,axs=plt.subplots(2,2,figsize=(14,7.7),sharex=True,sharey=True,constrained_layout=True)
    maxsigned=max(abs(z).max() for z in [p[0],q[0]])
    maxabs=max(z.max() for z in [p[1],q[1]])
    for row,(name,data) in enumerate([('M7 → M8',p),('M8 → M9',q)]):
        for col,(title,matrix) in enumerate([('signed Δ',data[0]),('|Δ| L1',data[1])]):
            ax=axs[row,col]
            if col==0: im=ax.imshow(matrix,origin='lower',aspect='auto',cmap='RdBu_r',
                                    norm=TwoSlopeNorm(vmin=-maxsigned,vcenter=0,vmax=maxsigned),
                                    extent=[.5,36.5,-.5,9.5])
            else:im=ax.imshow(matrix,origin='lower',aspect='auto',cmap='magma',
                              vmin=0,vmax=maxabs,extent=[.5,36.5,-.5,9.5])
            ax.set_title(f'{name}: {title}  [m⁻¹ / bin / step]')
            ax.set_yticks(range(10));ax.set_ylabel('μ bin (0 south, 9 north)')
            ax.set_xticks([1,6,12,18,24,30,36]);ax.set_xlabel('time step (25 s)')
            ax.axvline(30.5,color='cyan' if col else 'black',lw=.9,alpha=.75)
            fig.colorbar(im,ax=ax,shrink=.8)
    fig.suptitle('Signed4D differences projected over radial and azimuthal bins\n'
                 'Exact 43,200 physical volume cells per mesh; no interpolation')
    fig.savefig(a.out,dpi=170)
    print(a.out)

if __name__=='__main__':main()
