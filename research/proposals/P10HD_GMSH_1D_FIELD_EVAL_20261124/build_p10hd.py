#!/usr/bin/env python3
"""Build reproducible isolated Windows 1D-only Gmsh field-evaluator ZIP."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SOURCE=REPO/'research/proposals/P10HC_CONTINUOUS_M2_SOURCE_ONLY_20261124/P10HC_CONTINUOUS_KAPPA_FIELDS.geo'
COMMON=REPO/'research/proposals/P10GO_SINGLE_MATHEVAL_1D_WINDOWS_20261123/P10FN_common.py'
EXPECTED='98ce03ed4a656dd6c3e9fc69f5c9711d7d8bbdc6bf61ddaceed9e656a918a85a'
REV='P10HD_R1_ONE_1D_ONLY_MATHEVAL_EVALUATOR_PROBE'
FILE_NAMES=('P10HD_ONE_DIMENSIONAL_EVAL.geo','P10HD_one_1d.py',
            '01_P10HD_PREFLIGHT_NO_MESH.cmd','02_P10HD_ONE_NATIVE_1D_ONLY.cmd',
            'README_P10HD_RU.md','P10HC_CONTINUOUS_KAPPA_FIELDS.geo','P10FN_common.py')
OUT=HERE/'P10HD_R1_BOUNDED_ONE_1D_FIELD_EVAL_WINDOWS_20261124.zip'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if not SOURCE.is_file() or sha(SOURCE)!=EXPECTED:
        raise RuntimeError('P10HC exact source pin mismatch')
    shutil.copyfile(SOURCE,HERE/SOURCE.name)
    shutil.copyfile(COMMON,HERE/COMMON.name)
    manifest={'revision':REV,'source_P10HC_SHA256':EXPECTED,
              'files':{n:sha(HERE/n) for n in FILE_NAMES},
              'native_parse_max':1,'native_1d_max':1,'native_2d_max':0,
              'native_3d_max':0,'FEM_max':0}
    (HERE/'P10HD_SOURCE_SHA256.json').write_text(
        json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    names=(*FILE_NAMES,'P10HD_SOURCE_SHA256.json')
    with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in names:z.write(HERE/name,name)
    with zipfile.ZipFile(OUT) as z:
        assert set(z.namelist())==set(names) and z.testzip() is None
        for name in names:assert z.read(name)==(HERE/name).read_bytes()
    print('P10HD_PACKAGE',OUT,'bytes',OUT.stat().st_size,'sha256',sha(OUT),'files',len(names))


if __name__=='__main__':main()
