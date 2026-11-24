#!/usr/bin/env python3
"""Pack pinned P10GT CAD and full physical 4D mechanical κ, R2 ghost extension."""
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
LOCAL=['P10HT_one_3d_candidate_r2.py','P10HT_guard.py',
       '01_P10HT_R2_ONE_3D_GHOST_GUARDED.cmd','README_P10HT_R2_RU.md']
OUT=HERE/'P10HT_R2_GUARDED_3D_PORE_PROBE_WINDOWS_20261124.zip'

def main():
    for name,p in PACK.items():
        if not p.is_file():raise RuntimeError('source missing '+str(p))
        shutil.copy2(p,HERE/name)
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in [*PACK,*LOCAL]:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        if z.testzip():raise RuntimeError('ZIP CRC')
        for name in [*PACK,*LOCAL]:
            if z.read(name)!=(HERE/name).read_bytes():raise RuntimeError('ZIP mismatch '+name)
    print(OUT,'bytes',OUT.stat().st_size,'sha256',hashlib.sha256(OUT.read_bytes()).hexdigest())

if __name__=='__main__':main()
