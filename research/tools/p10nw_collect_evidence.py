#!/usr/bin/env python3
"""One-click evidence archive, preserving source files and excluding secrets/markers."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
HERE=Path(__file__).resolve().parent
OUT=HERE/'P10NW_M13_SERIALIZED_EVIDENCE.zip'
NAMES=['P10NW_M13_SERIALIZED_RESULT.json','P10NW_GMSH_SERIALIZATION_LOG.txt',
       'P10NW_M13_OPTIMIZED_CANDIDATE.msh']
if OUT.exists():raise RuntimeError('Evidence ZIP already exists: no overwrite')
with ZipFile(OUT,'x',compression=ZIP_DEFLATED,compresslevel=6) as z:
    for name in NAMES:
        f=HERE/name
        if f.is_file():
            if f.stat().st_size>64*1024*1024:raise RuntimeError(f'{name}: size cap STOP')
            z.write(f,arcname=name)
print('P10NW_EVIDENCE_READY',OUT.name,flush=True)
