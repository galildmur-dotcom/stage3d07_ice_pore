#!/usr/bin/env python3
"""Immutable R3 source-only 3D PostView package with corrected Tet10 edges."""
import hashlib
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
R2=ROOT/'research/proposals/P10HF_P10HE_NUMPY_ONLY_20261124'
SOURCE=ROOT/'research/proposals/P10HE_POSTVIEW_SOURCE_ONLY_20261124/P10HE_build_view.py'
OUT=HERE/'P10HG_R3_CORRECT_TET10_MIDEDGE_QA_WINDOWS_20261124.zip'
COPY={n:R2/n for n in (
  'P10HA_KAPPA_QA.json','P10HA_SPATIAL_KAPPA_1200_BINS.csv',
  'p10hc_continuous_kappa_geo.py','P10GT_HXT10.geo',
  'M0_ROTATED.geo','sphere_pore_B6_refined_rotated.geo')}
LOCAL=('01_P10HG_CORRECTED_EDGE_QA_NO_MESH.cmd','P10HG_edge_order_selftest.py','README_P10HG_R3_RU.md')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    for name,source in COPY.items():
        if not source.is_file():raise RuntimeError('missing source '+name)
        shutil.copyfile(source,HERE/name)
    s=SOURCE.read_text(encoding='utf-8')
    old="REV='P10HE_R1_POSTVIEW_C0_FROM_C2_NODAL_SOURCE_NO_MESH'"
    if s.count(old)!=1 or s.count('GMSH_TET10_EDGES=((0,1),(1,2),(2,0),(3,0),(3,2),(3,1))')!=1:
        raise RuntimeError('unexpected P10HE source before R3 relabel')
    s=s.replace(old,"REV='P10HG_R3_TET10_CORRECT_EDGES_C0_SOURCE_RECHECK'")
    (HERE/'P10HE_build_view.py').write_text(s,encoding='utf-8')
    names=(*COPY,*LOCAL,'P10HE_build_view.py')
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in names:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None and set(z.namelist())==set(names)
        for n in names:assert z.read(n)==(HERE/n).read_bytes()
    print('P10HG_R3',OUT,'bytes',OUT.stat().st_size,'SHA256',sha(OUT),'files',len(names))


if __name__=='__main__':main()
