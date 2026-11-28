#!/usr/bin/env python3
"""Deterministic archive; narrow audited time-parametric P10FN source edits."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'research/packages/P10GV_R1_P10GT_M1_ONE_SIGNED_FULL4D_WINDOWS_20261123.zip'
OUT=ROOT/'research/packages/P10GX_R1_M0_M1_SEVEN_LEVEL_SIGNED_4D_TEMPORAL_WINDOWS_20261123.zip'


def patched(raw,old,new,label):
    need=raw.count(old)
    if need!=1:raise ValueError(f'P10GX source drift {label}: {need} matches')
    return raw.replace(old,new)


def build():
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None
        contents={n:z.read(n) for n in z.namelist()}
    for name in list(contents):
        if name.startswith('P10GV_') or name.startswith(('01_P10GV','02_P10GV')) or name=='README_P10GV_RU.md':
            del contents[name]
    fn='stage3d10fn_any_mesh_full4d.cpp'
    raw=contents[fn]
    raw=patched(raw,b'i!=3 && i!=5 && i!=7 &&',
                b'i!=3 && i!=5 && i!=7 && i!=9 && i!=11 &&', 'CLI positions')
    raw=patched(raw,b'  const std::string mode=argv[7];',
                b'''  const std::string grid=std::string(argv[9])+"x"+argv[11];
  if(grid!="6x150" && grid!="12x75" && grid!="15x60" &&
     grid!="18x50" && grid!="20x45" && grid!="25x36" &&
     grid!="36x25")return false;
  const std::string mode=argv[7];''', 'whitelisted grids')
    contents[fn]=raw
    fn='src/stage3d10p_partial_audit.cpp'
    contents[fn]=patched(contents[fn],
        b'pairs.size()==1&&c.mode=="R"&&c.steps==6&&c.dt==150,',
        b'pairs.size()==1&&c.mode=="R"&&c.steps*c.dt==900&&c.steps<=36&&c.steps>=6,',
        'dynamic 4D guard')
    fn='src/stage3d10k_h0_coupled_pilot.cpp'
    contents[fn]=patched(contents[fn],b'c.steps<=12&&c.dt>=1',
                          b'c.steps<=36&&c.dt>=1','parser step max')
    for name in ('P10GX_temporal_series.py','01_P10GX_PREFLIGHT_NO_FEM.cmd',
                 '02_P10GX_ONE_BOUNDED_12_RUN_CAMPAIGN.cmd','README_P10GX_RU.md'):
        contents[name]=(HERE/name).read_bytes()
    pin=json.loads(contents['P10FN_SOURCE_SHA256.json'])
    pin['revision']='P10GX_R1_WHITELISTED_7_GRID_4D_NO_UNBOUNDED_FEM'
    pin['files']={k:hashlib.sha256(contents[k]).hexdigest() for k in pin['files']
                  if k in contents}
    assert len(pin['files'])>=90
    contents['P10FN_SOURCE_SHA256.json']=(json.dumps(pin,indent=2)+'\n').encode()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(contents):
            info=zipfile.ZipInfo(name,date_time=(2026,11,23,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,contents[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
    print('P10GX_PACKAGE_PASS files',len(contents),'bytes',OUT.stat().st_size,
          'SHA',hashlib.sha256(OUT.read_bytes()).hexdigest())

if __name__=='__main__':build()
