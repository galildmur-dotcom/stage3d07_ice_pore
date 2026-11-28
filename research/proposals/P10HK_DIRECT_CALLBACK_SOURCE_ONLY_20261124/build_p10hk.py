#!/usr/bin/env python3
"""Package only already pinned code and P10HA input for Windows source QA."""
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
    'P10HA_SPATIAL_KAPPA_1200_BINS.csv':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_SPATIAL_KAPPA_1200_BINS.csv',
}
LOCAL=['01_P10HK_BENCHMARK_NO_GMSH_NO_MESH.cmd','README_P10HK_WINDOWS_RU.md']
OUT=HERE/'P10HK_R1_DIRECT_KAPPA_CALLBACK_BENCH_WINDOWS_20261124.zip'


def main():
    for name,path in SOURCE.items():
        if not path.is_file():raise RuntimeError('P10HK package source not found '+str(path))
        shutil.copy2(path,HERE/name)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*SOURCE,*LOCAL]:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        if z.testzip() is not None:raise RuntimeError('P10HK ZIP CRC')
        for name in [*SOURCE,*LOCAL]:
            if z.read(name)!=(HERE/name).read_bytes():raise RuntimeError('P10HK ZIP byte mismatch '+name)
    print('P10HK Windows ZIP',OUT,'bytes',OUT.stat().st_size,
          'sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())


if __name__=='__main__':main()
