#!/usr/bin/env python3
"""Visualize 3D C2 field probe curves; no Gmsh/FEM."""
import csv
import sys
import matplotlib.pyplot as plt


def main(source,target):
    with open(source,newline='') as f: rows=list(csv.DictReader(f))
    fig,axs=plt.subplots(1,2,figsize=(11,4.6),sharey=True,constrained_layout=True)
    for ax,side in zip(axs,('north','south')):
        for mu in (.8,.95,1.0):
            r=[x for x in rows if x['side']==side and abs(float(x['mu']))==mu and float(x['phi'])==0.]
            r.sort(key=lambda x:float(x['d_mm']))
            ax.plot([float(x['d_mm']) for x in r],
                    [float(x['size_ratio_proxy']) for x in r],
                    marker='o',markersize=3,label='|μ|='+str(mu))
        ax.axvline(.3,color='gray',ls=':',lw=1)
        ax.axvline(1.,color='gray',ls=':',lw=1)
        ax.set_title(side.capitalize()+' pole')
        ax.set_xlabel('Distance from pore wall, mm')
        ax.grid(alpha=.22)
        ax.legend()
    axs[0].set_ylabel('Nominal h_M3 / h_M2 proxy')
    fig.suptitle('P10IN C² size-field preview (not actual Gmsh element volumes)')
    fig.savefig(target,dpi=165)
    plt.close(fig)


if __name__=='__main__':main(sys.argv[1],sys.argv[2])
