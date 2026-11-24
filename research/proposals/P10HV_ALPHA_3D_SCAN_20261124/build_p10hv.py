#!/usr/bin/env python3
"""Reproducible standalone source-only Windows alpha scan bundle."""
from pathlib import Path
import hashlib
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CAD=ROOT/'research/proposals/P10HG_CORRECT_TET10_EDGE_QA_20261124'
PACK={
    'P10GT_HXT10.geo':CAD/'P10GT_HXT10.geo',
    'M0_ROTATED.geo':CAD/'M0_ROTATED.geo',
    'sphere_pore_B6_refined_rotated.geo':CAD/'sphere_pore_B6_refined_rotated.geo',
    'p10hk_direct_kappa_callback_benchmark.py':ROOT/'scripts/p10hk_direct_kappa_callback_benchmark.py',
    'p10hc_continuous_kappa_geo.py':ROOT/'scripts/p10hc_continuous_kappa_geo.py',
    'P10HA_KAPPA_QA.json':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_KAPPA_QA.json',
    'P10HA_SPATIAL_KAPPA_1200_BINS.csv':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_SPATIAL_KAPPA_1200_BINS.csv'}
LOCAL=['P10HV_three_alpha_3d.py','P10HV_guard.py',
       '01_P10HV_THREE_ALPHA_3D_NO_FEM.cmd','README_P10HV_R1_RU.md']
OUT=HERE/'P10HV_R1_THREE_ALPHA_3D_CANDIDATES_WINDOWS_20261124.zip'


def main():
    for name,p in PACK.items():
        if not p.is_file():raise RuntimeError('missing pinned source '+str(p))
        shutil.copy2(p,HERE/name)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*PACK,*LOCAL]:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        if z.testzip():raise RuntimeError('ZIP CRC')
        for name in [*PACK,*LOCAL]:
            if z.read(name)!=(HERE/name).read_bytes():raise RuntimeError('ZIP mismatch '+name)
    print(OUT,'bytes',OUT.stat().st_size,'sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())

if __name__=='__main__':main()
