#!/usr/bin/env python3
"""Plot the source-only M2 kappa(r,theta) field; never generate a mesh."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "research/proposals/P10DN_M2_COEFF20_SOURCE_ONLY_20261121/P10DN_m2_coefficient.py"
OUT = ROOT / "research/evidence/P10DN_M2_COEFFICIENT20_SOURCE_ONLY_20261121/derived/P10DN_M2_KAPPA_FIELD_PREVIEW.png"


def main() -> None:
    spec = importlib.util.spec_from_file_location("p10dn_coefficient", SRC)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    radial_mm = np.linspace(0., .8, 241)
    mu = np.linspace(-1., 1., 301)
    kappas = np.empty((len(mu), len(radial_mm)))
    for j, polar in enumerate(mu):
        for i, radial in enumerate(radial_mm):
            rho = module.PORE_R + radial/1000.
            kappas[j,i] = module.kappa_xyz(
                rho * np.sqrt(max(0, 1-polar**2)), 0,
                module.PORE_CZ + rho*polar)

    assert kappas.min() >= 0 and kappas.max() <= 1
    assert np.all(kappas[:, radial_mm >= .5] == 0)
    assert np.max(kappas[np.abs(mu) <= .6,:]) < 1e-20

    fig, axes = plt.subplots(1, 2, figsize=(11.7, 4.7),
                             gridspec_kw={"width_ratios":[1.65,1]})
    ax=axes[0]
    im=ax.pcolormesh(radial_mm,mu,kappas,shading="auto",vmin=0,vmax=1,cmap="viridis")
    ax.set_xlabel("Distance from pore wall, mm")
    ax.set_ylabel(r"$\mu=\cos\theta$ (south -1, north +1)")
    ax.set_title(r"Full-domain coefficient $\kappa(r,\theta,\varphi)$; independent of $\varphi$")
    fig.colorbar(im,ax=ax,label=r"Refinement coefficient $\kappa$")
    ax.axvline(.1,color="white",alpha=.5,ls="--",lw=.9)
    ax.axvline(.5,color="white",alpha=.5,ls="--",lw=.9)
    ax=axes[1]
    for m,color in ((1.,"#0072B2"),(.7,"#E69F00"),(.5,"#999999")):
        i=int(np.argmin(abs(mu-m)))
        ax.plot(radial_mm,1-.2*kappas[i,:],label=rf"$|\mu|={m:g}$",color=color,lw=2)
    ax.set_title("M2 / M1 target volume")
    ax.set_xlabel("Distance from pore wall, mm")
    ax.set_ylabel(r"$V_{\rm target,M2}/V_{\rm target,M1}$")
    ax.set_ylim(.77,1.025)
    ax.set_xlim(0,.8)
    ax.grid(alpha=.2)
    ax.legend(loc="lower right")
    fig.suptitle("P10DN · M2 coefficient proposal · source-only (no mesh, no FEM)",fontsize=13)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(OUT,dpi=160)
    plt.close(fig)
    print("P10DN_M2_KAPPA_PREVIEW_OK",OUT, "range=0..1 mesh=0 FEM=0")


if __name__ == "__main__":
    main()
