#!/usr/bin/env python3
"""Package pinned R1 scientific test with local isolated Gmsh API bootstrap."""
from pathlib import Path
import hashlib
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R1=ROOT/'research/proposals/P10HL_GMSH_CALLBACK_1D_PREFLIGHT_20261124'
PACK={name:R1/name for name in (
    'P10HL_one_line_callback.py','p10hk_direct_kappa_callback_benchmark.py',
    'p10hc_continuous_kappa_geo.py','P10HA_KAPPA_QA.json',
    'P10HA_SPATIAL_KAPPA_1200_BINS.csv')}
LOCAL=['01_P10HL_R2_INSTALL_LOCAL_GMSH_AND_1D.cmd','README_P10HL_R2_RU.md']
OUT=HERE/'P10HL_R2_LOCAL_GMSH_API_1D_WINDOWS_20261124.zip'


def main():
    for name,path in PACK.items():
        if not path.is_file():raise RuntimeError('missing '+str(path))
        shutil.copy2(path,HERE/name)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*PACK,*LOCAL]:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        if z.testzip():raise RuntimeError('ZIP CRC')
        for name in [*PACK,*LOCAL]:
            if z.read(name)!=(HERE/name).read_bytes():raise RuntimeError('ZIP mismatch '+name)
    print(OUT,'bytes',OUT.stat().st_size,'sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__=='__main__':main()
