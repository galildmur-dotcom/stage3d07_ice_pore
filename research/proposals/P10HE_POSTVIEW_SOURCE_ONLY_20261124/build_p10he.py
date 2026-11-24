#!/usr/bin/env python3
"""Deterministic Windows package for source-only PostView generation from real M1."""
import hashlib
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/'P10HE_R1_REAL_M1_C2_SAMPLE_C0_POSTVIEW_SOURCE_ONLY_WINDOWS_20261124.zip'
INPUTS={
    'P10HA_KAPPA_QA.json':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_KAPPA_QA.json',
    'P10HA_SPATIAL_KAPPA_1200_BINS.csv':ROOT/'research/evidence/P10HA_KAPPA_SOURCE_PILOT_20261124/P10HA_SPATIAL_KAPPA_1200_BINS.csv',
    'p10hc_continuous_kappa_geo.py':ROOT/'scripts/p10hc_continuous_kappa_geo.py',
    'P10GT_HXT10.geo':ROOT/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/P10GT_HXT10.geo',
    'M0_ROTATED.geo':ROOT/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/M0_ROTATED.geo',
    'sphere_pore_B6_refined_rotated.geo':ROOT/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/sphere_pore_B6_refined_rotated.geo'}
STATIC=('P10HE_build_view.py','README_P10HE_RU.md','01_P10HE_BUILD_POSTVIEW_NO_MESH.cmd')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    for name,src in INPUTS.items():
        if not src.is_file():raise RuntimeError('missing source '+str(src))
        shutil.copyfile(src,HERE/name)
    names=(*INPUTS,*STATIC)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n in names:z.write(HERE/n,n)
    with zipfile.ZipFile(OUT) as z:
        assert len(names)==len(set(names)) and z.testzip() is None
        assert set(z.namelist())==set(names)
        for n in names:assert z.read(n)==(HERE/n).read_bytes()
    print('P10HE_PACKAGE',OUT,'bytes',OUT.stat().st_size,'SHA256',sha(OUT),'files',len(names))


if __name__=='__main__':main()
