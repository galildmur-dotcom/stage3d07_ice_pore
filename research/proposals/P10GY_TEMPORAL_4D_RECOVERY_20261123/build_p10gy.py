#!/usr/bin/env python3
"""Post-mortem audited repair: parameterized 4D writer + mandatory writer unit."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'research/packages/P10GX_R1_M0_M1_SEVEN_LEVEL_SIGNED_4D_TEMPORAL_WINDOWS_20261123.zip'
OUT=ROOT/'research/packages/P10GY_R2_M0_M1_SEVEN_DT_FIXED_4D_WRITER_WINDOWS_20261123.zip'

def patch_once(raw,old,new,label):
    if raw.count(old)!=1:raise ValueError(f'P10GY source drift {label}: {raw.count(old)}')
    return raw.replace(old,new)

def build():
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None
        files={k:z.read(k) for k in z.namelist()}
    for name in list(files):
        if name.startswith(('P10GX_','01_P10GX','02_P10GX')) or name=='README_P10GX_RU.md':
            del files[name]
    template=(ROOT/'research/proposals/P10GX_TEMPORAL_4D_SERIES_20261123/P10GX_temporal_series.py').read_bytes()
    files['P10GY_temporal_series.py']=template.replace(b'P10GX',b'P10GY')
    for name in ('01_P10GY_PREFLIGHT_NO_FEM.cmd',
                 '02_P10GY_NEW_12_RUN_CAMPAIGN.cmd','README_P10GY_RU.md'):
        files[name]=(HERE/name).read_bytes()
    fn='stage3d10dd_4d_partition.hpp'
    files[fn]=patch_once(files[fn],
        b'if(steps!=6||dt!=150||mechanics.size()!=std::size_t(steps)||',
        b'if(steps<6||steps>36||steps*dt!=900||mechanics.size()!=std::size_t(steps)||',
        'fix final 4D CSV gate')
    fn='stage3d10fn_any_mesh_full4d.cpp'
    inject=b'''    // P10GY: mandatory dynamic 12/36-step CSV writer selftest, no FEM.
    const auto temp=fs::temp_directory_path()/
      ("P10GY_DYNAMIC_4D_"+std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    fs::create_directory(temp);
    try {
      for(const auto grid: {std::pair<int,int>{12,75},std::pair<int,int>{36,25}}){
        std::vector<ice3d::p10dd::Snapshot> a(std::size_t(grid.first));
        std::vector<ice3d::p10dd::Snapshot> b(std::size_t(grid.first));
        ice3d::p10dd::Parts reference{};
        ice3d::p10dd::write_csv(temp,"M1",grid.first,grid.second,a,b,reference);
        std::ifstream csv(temp/"P10DD_SIGNED_R_THETA_PHI_T.csv");
        std::size_t lines=0;std::string line;
        while(std::getline(csv,line))++lines;
        if(lines!=std::size_t(grid.first)*1201+1)return 8;
      }
    }catch(...){fs::remove_all(temp);throw;}
    fs::remove_all(temp);
    std::cout<<"P10GY_DYNAMIC_4D_WRITER_12_36_SELFTEST_OK no_FEM=1\\n";
'''
    files[fn]=patch_once(files[fn],b'    if(code!=0)return code;\n',
                         b'    if(code!=0)return code;\n'+inject,'insert writer selftest')
    pin=json.loads(files['P10FN_SOURCE_SHA256.json'])
    pin['revision']='P10GY_R2_FIXED_4D_WRITER_12_36_SELFTEST_GUARDED_ONE_SHOTS'
    pin['files']={k:hashlib.sha256(files[k]).hexdigest() for k in pin['files'] if k in files}
    assert len(pin['files'])>=90
    files['P10FN_SOURCE_SHA256.json']=(json.dumps(pin,indent=2)+'\n').encode()
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(2026,11,23,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,files[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as z:assert z.testzip() is None
    print('P10GY_FIXED_ZIP_PASS',OUT,'files',len(files),'bytes',OUT.stat().st_size,
          'SHA256',hashlib.sha256(OUT.read_bytes()).hexdigest())

if __name__=='__main__':build()
