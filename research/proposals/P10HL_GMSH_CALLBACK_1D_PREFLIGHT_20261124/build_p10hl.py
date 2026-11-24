#!/usr/bin/env python3
"""Reproducible one-click diagnostic ZIP with no FEM and no original mesh."""
from pathlib import Path
import hashlib
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
SOURCE={
    'p10hk_direct_kappa_callback_benchmark.py':ROOT/'scripts/p10hk_direct_kappa_callback_benchmark.py',
    'p10hc_continuous_kappa_geo.py':ROOT/'scripts/p10hc_continuous_kappa_geo.py',
    'P10HA_KAPPA_QA.json':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_KAPPA_QA.json',
    'P10HA_SPATIAL_KAPPA_1200_BINS.csv':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_SPATIAL_KAPPA_1200_BINS.csv'}
LOCAL=['P10HL_one_line_callback.py','01_P10HL_ONE_SYNTHETIC_LINE_1D_ONLY.cmd',
       'README_P10HL_R1_WINDOWS_RU.md']
OUT=HERE/'P10HL_R1_NATIVE_GMSH_CALLBACK_1D_WINDOWS_20261124.zip'


def main():
    for name,p in SOURCE.items():
        if not p.is_file():raise RuntimeError('missing '+str(p))
        shutil.copy2(p,HERE/name)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*SOURCE,*LOCAL]:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        if z.testzip():raise RuntimeError('ZIP CRC')
        for name in [*SOURCE,*LOCAL]:
            if z.read(name)!=(HERE/name).read_bytes():raise RuntimeError('ZIP mismatch '+name)
    print(OUT,'bytes',OUT.stat().st_size,'sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__=='__main__':main()
