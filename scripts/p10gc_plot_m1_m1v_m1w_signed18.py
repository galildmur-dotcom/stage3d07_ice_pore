#!/usr/bin/env python3
"""Three real Gmsh mesh attempts; exact fixed-zone signed 729QP comparisons."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--m1",type=Path,required=True)
    p.add_argument("--m1v",type=Path,required=True)
    p.add_argument("--m1w",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    ds=[json.loads(path.read_text(encoding="utf-8"))
        for path in (a.m1,a.m1v,a.m1w)]
    zones=[ds[0]["sample_levels"]["9"]["zones18"],
           ds[1]["levels"]["9"]["zones18"],
           ds[2]["levels"]["9"]["zones18"]]
    for j in (1,2):
        for x,y in zip(zones[0],zones[j]):
            assert (x["radial_zone"],x["polar_zone"],x["hemisphere"])==(
                y["radial_zone"],y["polar_zone"],y["hemisphere"])
    field=["measured_M1_over_M0","M1V_over_M0_Veff_ratio",
           "M1W_over_M0_Veff_ratio"]
    matrices=[np.array([row[key] for row in rows]).reshape(3,6)
              for key,rows in zip(field,zones)]
    fig,axes=plt.subplots(1,3,figsize=(18.3,5.25),sharey=True)
    norm=TwoSlopeNorm(vmin=.60,vcenter=.825,vmax=1.11)
    for ax,k,title in zip(axes,range(3),("Old M1","M1V","M1W")):
        vals=matrices[k]
        img=ax.imshow(vals,cmap="coolwarm",norm=norm,aspect="auto")
        ax.set_xticks(range(6),("N","S","N","S","N","S"))
        ax.set_yticks(range(3),("0–100 µm","100–500 µm",">500 µm"))
        num=int(np.count_nonzero((vals>=.80)&(vals<=.85)))
        ax.set_title(f"{title}: {num}/18 PASS",fontsize=14,weight="bold")
        ax.set_xlabel("polar     transition     off-polar")
        for r in range(3):
            for c in range(6):
                q=float(vals[r,c])
                go=.80<=q<=.85
                ax.text(c,r,f"{q:.3f}\n{'PASS' if go else 'FAIL'}",
                        ha="center",va="center",fontsize=9,
                        weight="normal" if go else "bold")
                if go:
                    ax.add_patch(plt.Rectangle((c-.48,r-.47),.96,.94,
                                               fill=False,edgecolor="#088557",linewidth=2))
        ax.set_ylim(2.5,-.5)
    cax=fig.add_axes([.925,.26,.016,.45])
    fig.colorbar(img,cax=cax,label="Real Veff(mesh)/Veff(M0) by 729QP")
    fig.suptitle("Stage3D07 · Tet10 real fixed signed 3D regions · "
                 "strict target 0.80–0.85 in ALL 18 zones",y=.965,fontsize=15)
    fig.text(.5,.04,"N/S — north/south; green outline — zone passes; "
             "real meshes, NOT predicted size-field ratios",ha="center",fontsize=10)
    fig.subplots_adjust(left=.08,right=.905,bottom=.19,top=.81,wspace=.12)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.out,dpi=160)
    plt.close(fig)
    print("P10GC_THREE_REAL_MESHES_SIGNED18_PLOT_OK",a.out)


if __name__=="__main__":
    main()
