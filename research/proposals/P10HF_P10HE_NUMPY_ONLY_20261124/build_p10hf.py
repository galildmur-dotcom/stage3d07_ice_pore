#!/usr/bin/env python3
"""Create immutable repaired R2 P10HE Windows source-only bundle without SciPy."""
import hashlib
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=ROOT/'research/proposals/P10HE_POSTVIEW_SOURCE_ONLY_20261124'
OUT=HERE/'P10HF_R2_P10HE_NUMPY_ONLY_SOURCE_WINDOWS_20261124.zip'
SRC={
 'P10HE_build_view.py':OLD/'P10HE_build_view.py',
 'P10HA_KAPPA_QA.json':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_KAPPA_QA.json',
 'P10HA_SPATIAL_KAPPA_1200_BINS.csv':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_SPATIAL_KAPPA_1200_BINS.csv',
 'p10hc_continuous_kappa_geo.py':ROOT/'scripts/p10hc_continuous_kappa_geo.py',
 'P10GT_HXT10.geo':ROOT/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/P10GT_HXT10.geo',
 'M0_ROTATED.geo':ROOT/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/M0_ROTATED.geo',
 'sphere_pore_B6_refined_rotated.geo':ROOT/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/sphere_pore_B6_refined_rotated.geo'}
LOCAL=('01_P10HF_POSTVIEW_NO_SCIPY.cmd','P10HF_numpy_selftest.py','README_P10HF_R2_RU.md')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for name,source in SRC.items():
        if not source.is_file():raise RuntimeError('missing input '+name)
        shutil.copyfile(source,HERE/name)
    names=(*SRC,*LOCAL)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in names:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None and set(z.namelist())==set(names)
        for n in names:assert z.read(n)==(HERE/n).read_bytes()
    print('P10HF_R2_PACKAGE',OUT,'bytes',OUT.stat().st_size,'SHA256',sha(OUT),'files',len(names))


if __name__=='__main__':main()
