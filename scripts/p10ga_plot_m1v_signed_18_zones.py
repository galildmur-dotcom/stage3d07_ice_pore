#!/usr/bin/env python3
"""Plot measured fixed-zone Veff ratios for failed M1 and real M1V."""
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
    p.add_argument("--old",type=Path,required=True)
    p.add_argument("--new",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    old=json.loads(a.old.read_text(encoding="utf-8"))
    new=json.loads(a.new.read_text(encoding="utf-8"))
    old_zone=old["sample_levels"]["9"]["zones18"]
    new_zone=new["levels"]["9"]["zones18"]
    assert len(old_zone)==len(new_zone)==18
    for x,y in zip(old_zone,new_zone):
        assert (x["radial_zone"],x["polar_zone"],x["hemisphere"])==(
            y["radial_zone"],y["polar_zone"],y["hemisphere"])
    arrays=[np.array([z["measured_M1_over_M0"] for z in old_zone]).reshape(3,6),
            np.array([z["M1V_over_M0_Veff_ratio"] for z in new_zone]).reshape(3,6)]
    plt.rcParams.update({"font.size":10})
    fig,ax=plt.subplots(1,2,figsize=(14.0,5.1),sharey=True,
                       gridspec_kw={"wspace":.09})
    norm=TwoSlopeNorm(vmin=.62,vcenter=.825,vmax=1.10)
    label=["N","S","N","S","N","S"]
    for k in range(2):
        heat=ax[k].imshow(arrays[k],cmap="coolwarm",norm=norm,aspect="auto")
        ax[k].set_xticks(range(6),label)
        ax[k].set_yticks(range(3),["0–100 µm","100–500 µm",">500 µm"])
        ax[k].set_title(("Previous M1 (rejected)" if k==0 else "New M1V (geometry PASS, 18-zone STOP)"),
                        fontsize=12,weight="bold")
        ax[k].set_xlabel("Polar |µ| ≥ 0.8       0.6–0.8       |µ| ≤ 0.6")
        for r in range(3):
            for c in range(6):
                val=arrays[k][r,c];good=.8<=val<=.85
                ax[k].text(c,r,f"{val:.3f}\n{'PASS' if good else 'FAIL'}",
                           color="black",ha="center",va="center",fontsize=9,
                           weight="bold" if not good else "normal")
                if good:
                    ax[k].add_patch(plt.Rectangle((c-.48,r-.47),.96,.94,
                                                  fill=False,edgecolor="#10834f",linewidth=2.0))
        ax[k].set_ylim(2.5,-.5)
    cax=fig.add_axes([.89,.25,.018,.49])
    fig.colorbar(heat,cax=cax,label="QP effective Tet10 volume ratio to M0")
    cnt=[int(np.count_nonzero((v>=.8)&(v<=.85))) for v in arrays]
    fig.suptitle(f"Stage3D07: strict 0.80–0.85 in all 18 fixed signed 3D zones · "
                 f"729 QP/Tet10 · PASS {cnt[0]}/18 → {cnt[1]}/18",fontsize=13,y=.98)
    fig.text(.5,.035,"N/S = north/south; green outline = zone satisfies the target; "
             "colors show actual 3D fixed-region volume ratios",ha="center",fontsize=10)
    fig.subplots_adjust(left=.09,right=.86,bottom=.17,top=.84)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(a.out,dpi=180)
    plt.close(fig)
    print("P10GA_SIGNED_18_ZONE_FIGURE_OK",a.out,flush=True)


if __name__=="__main__":
    main()
