#!/usr/bin/env python3
"""Package frozen original P10GT Field7 and direct κ on one isolated line."""
from pathlib import Path
import hashlib
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PACK={
    'P10GT_HXT10.geo':ROOT/'research/proposals/P10HG_CORRECT_TET10_EDGE_QA_20261124/P10GT_HXT10.geo',
    'p10hk_direct_kappa_callback_benchmark.py':ROOT/'scripts/p10hk_direct_kappa_callback_benchmark.py',
    'p10hc_continuous_kappa_geo.py':ROOT/'scripts/p10hc_continuous_kappa_geo.py',
    'P10HA_KAPPA_QA.json':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_KAPPA_QA.json',
    'P10HA_SPATIAL_KAPPA_1200_BINS.csv':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_SPATIAL_KAPPA_1200_BINS.csv'}
LOCAL=['P10HN_real_field7_callback.py','01_P10HN_REAL_FIELD7_SYNTHETIC_1D.cmd','README_P10HN_R1_RU.md']
OUT=HERE/'P10HN_R1_REAL_FIELD7_1D_WINDOWS_20261124.zip'


def main():
    for name,p in PACK.items():
        if not p.is_file():raise RuntimeError('missing '+str(p))
        shutil.copy2(p,HERE/name)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*PACK,*LOCAL]:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        if z.testzip():raise RuntimeError('ZIP CRC')
        for name in [*PACK,*LOCAL]:
            if z.read(name)!=(HERE/name).read_bytes():raise RuntimeError('byte mismatch '+name)
    print(OUT,'bytes',OUT.stat().st_size,'sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__=='__main__':main()
