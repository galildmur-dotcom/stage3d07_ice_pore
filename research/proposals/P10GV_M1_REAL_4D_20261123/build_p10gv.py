#!/usr/bin/env python3
"""Deterministic protected one-shot 4D kit built from canonical P10FP R4."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'research/packages/P10FP_R4_MINGW_DLL_PATH_M0_MN_WINDOWS_20261122.zip'
OUT=ROOT/'research/packages/P10GV_R1_P10GT_M1_ONE_SIGNED_FULL4D_WINDOWS_20261123.zip'
EVID=ROOT/'research/evidence/P10GU_P10GT_INDEPENDENT_343_729_D027.json'
M0=ROOT/'research/approvals/P10FQ_FRESH_M0_WINDOWS_20261122/M0.json'

def make():
    a0=json.loads(M0.read_text())
    a1={"schema":"P10GV_P10GU_INDEPENDENT_M1_D027_GEOMETRY_GO_V1",
        "status":"RESEARCHER_APPROVED_FOR_PHYSICS","mesh":"M1",
        "mesh_sha256":"47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7",
        "regime":a0['regime'],"approved_utc_date":"2026-11-23",
        "origin":"P10GT actual Windows HXT10, P10GU independent 27/343/729QP D-027 GO",
        "independent_report":"research/P10GU_INDEPENDENT_REAL_P10GT_HXT10_D027_GO_20261123.md",
        "evidence_zip_sha256":"7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3",
        "note":"one bounded fresh M1 forward and same-mesh analytic adjoint 4D; no M2 FEM"}
    payload={}
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None
        for name in z.namelist():
            # No older launch buttons, irrelevant recipes, or old M0 approval.
            if name.lower().endswith('.cmd') or name.startswith(('recipes/','approvals/')) or name=='README_RU.md':
                continue
            payload[name]=z.read(name)
    for name in ('P10GV_run.py','01_P10GV_PREFLIGHT_NO_FEM.cmd',
                 '02_P10GV_ONE_M1_FULL4D.cmd','README_P10GV_RU.md'):
        payload[name]=(HERE/name).read_bytes()
    # Preserve every inherited numerical source byte, but remove obsolete
    # buttons/recipes from the inventory (these are intentionally absent).
    pin=json.loads(payload['P10FN_SOURCE_SHA256.json'])
    pin['files']={k:v for k,v in pin['files'].items() if k in payload}
    assert len(pin['files'])>=90
    pin['revision']='P10GV_R1_ISOLATED_M1_4D_WITH_PINNED_P10FN_R4_SOURCES'
    payload['P10FN_SOURCE_SHA256.json']=(json.dumps(pin,indent=2)+'\n').encode()
    payload['P10GU_P10GT_INDEPENDENT_343_729_D027.json']=EVID.read_bytes()
    payload['approvals/M0.json']=json.dumps(a0,ensure_ascii=False,indent=2).encode('utf-8')+b'\n'
    payload['approvals/M1.json']=json.dumps(a1,ensure_ascii=False,indent=2).encode('utf-8')+b'\n'
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in sorted(payload):
            info=zipfile.ZipInfo(name,date_time=(2026,11,23,12,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o644<<16
            z.writestr(info,payload[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(payload)
    print('P10GV_ZIP_PASS',OUT,'files',len(payload),'size',OUT.stat().st_size,
          'SHA256',hashlib.sha256(OUT.read_bytes()).hexdigest())

if __name__=='__main__':make()
