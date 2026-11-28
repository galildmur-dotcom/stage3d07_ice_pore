#!/usr/bin/env python3
"""Pack audited static source-only P10HC Windows parse preflight."""
import hashlib
from pathlib import Path
import zipfile

HERE=Path(__file__).resolve().parent
PKG=HERE/'P10HC_R1_CONTINUOUS_MECHANICAL_KAPPA_WINDOWS_PARSE_ONLY_20261124.zip'
FILES=('P10GT_HXT10.geo','M0_ROTATED.geo','sphere_pore_B6_refined_rotated.geo',
       'P10HC_CONTINUOUS_KAPPA_FIELDS.geo','P10HC_M2_SOURCE_ONLY.geo',
       'P10HC_SOURCE_FIELD_QA.json','P10HC_windows_preflight.py',
       '01_P10HC_PREFLIGHT_PARSE_ONLY.cmd','README_P10HC_WINDOWS_RU.md')


def main():
    for name in FILES:
        if not (HERE/name).is_file():raise SystemExit('missing '+name)
    with zipfile.ZipFile(PKG,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name in FILES:z.write(HERE/name,name)
    with zipfile.ZipFile(PKG) as z:
        assert z.testzip() is None and set(z.namelist())==set(FILES)
        for name in FILES:assert z.read(name)==(HERE/name).read_bytes()
    print('P10HC_PACKAGED',PKG,'bytes',PKG.stat().st_size,
          'SHA256',hashlib.sha256(PKG.read_bytes()).hexdigest(),'source_files',len(FILES))


if __name__=='__main__':main()
