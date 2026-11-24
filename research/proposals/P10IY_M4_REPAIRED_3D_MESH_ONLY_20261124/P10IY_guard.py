#!/usr/bin/env python3
"""P10IY one-shot bounded M4 mesh-only guard, 30-s console heartbeat."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile

HERE=Path(__file__).resolve().parent
MARK=HERE/'P10IY_R1_ONE_M4_REPAIR_ATTEMPT_CONSUMED.marker'
PROFILE_MARK_NAME='P10IY_R1_M4_3d6ce765dced7d14_REPAIR_ONE_ATTEMPT.marker'
LOG=HERE/'P10IY_GMSH_LOG.txt'
RESULT=HERE/'P10IY_GUARD_RESULT.json'
EVIDENCE=HERE/'P10IY_R1_M4_REPAIR_UNVERIFIED_EVIDENCE.zip'
MAX_WALL=900
MAX_RAM=8*1024**3
MAX_LOG=32*1024**2
MAX_MESH=250*1024**2
PIN={
  'P10GT_HXT10.geo':'f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51',
  'M0_ROTATED.geo':'21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a',
  'sphere_pore_B6_refined_rotated.geo':'e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329',
  'M2.msh':'d1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b',
  'M3.msh':'3d6ce765dced7d146ef5228be3b0a8210b4466ed08a0c9f5a20d1917dc2a8c3a',
  'P10HA_SPATIAL_KAPPA_1200_BINS.csv':'98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3',
  'P10HA_KAPPA_QA.json':'361d8812af277505abc59b480042d5b049fb23ae6d664ad781868b985eeafae3',
  'P10IM_M3_KAPPA_HYPOTHESES_1200_BINS.csv':'be0a64d372f6520704bbc438247739bdeeda681930a879dff613c9b129e7b919',
  'P10IT_M2_M3_1200_BINS.csv':'e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06',
  'P10IY_one_M4_worker.py':'ce30f3e9017e66c8d72484bee2a1e1315b0a58d3b959a4e286227335e48a4d42',
  'p10ix_c2_m4_repair_preflight.py':'1970073d2accc405df81d3465849ee6d597fca453b9b6c885383e9619700f870',
  'P10IX_C2_FIELD_PREFLIGHT.json':'29e914b51798aeb5fe9891a0f7bdca4517004d12fe3b5e1c236151fa7d0a2f33',
  'p10iu_continuous_m4.py':'dfb57ca9dae1b52db4e9d3dc220def9e5df4eed86f2cc645e9e2252764252de8',
  'p10in_continuous_m3.py':'24bb42cbbf0a744cc97ea63d0b816eab4f8858ff91a85f2e53b1dd1d9008d390',
  'p10hc_continuous_kappa_geo.py':'07857c9f017265a6a3fb9391087e224ca97588a2dac147acd66c986d0996419d',
  'p10hk_direct_kappa_callback_benchmark.py':'0985ae7b23cbc6c029a6ab747d90869858adc9fb612bb1092a21ec807a97a431',
}


def need(condition,text):
    if not condition:raise RuntimeError('P10IY_STOP_NO_GMSH: '+text)


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda:stream.read(2**20),b''):h.update(block)
    return h.hexdigest()


def profile_mark():
    base=os.environ.get('LOCALAPPDATA')
    need(bool(base),'LOCALAPPDATA missing: cannot protect cross-folder one-shot')
    parent=Path(base)/'Stage3D07_OneShot_Markers'
    return parent/PROFILE_MARK_NAME


def check_preflight(check_api=True):
    for name,digest in PIN.items():
        p=HERE/name
        need(p.is_file() and sha(p)==digest,'source SHA wrong: '+name)
    # Closure of the full native Gmsh Include graph: a missing transitive GEO
    # stopped the former R1 after marker consumption and before meshing.
    visited=set()
    def check_includes(name):
        need(name not in visited,'recursive/duplicate GEO include: '+name)
        visited.add(name)
        source=HERE/name
        need(source.is_file(),'missing transitive GEO include: '+name)
        for child in re.findall(r'(?m)^\s*Include\s+"([^"\n]+)"\s*;',
                                source.read_text(encoding='utf-8')):
            need(child in PIN,'uncontrolled GEO include: '+child)
            check_includes(child)
    check_includes('P10GT_HXT10.geo')
    need(visited=={'P10GT_HXT10.geo','M0_ROTATED.geo',
                   'sphere_pore_B6_refined_rotated.geo'},'unexpected GEO include graph')
    need(not MARK.exists(),'one-shot P10IY M4 mesh marker already consumed; NO repeat')
    if sys.platform=='win32':
        need(not profile_mark().exists(),'profile marker already consumed; NO repeat across folders')
    need(not (HERE/'P10IY_M4_R2_CANDIDATE_UNVERIFIED.msh').exists(),
         'candidate output already exists; never overwrite')
    if check_api:
        import gmsh
        need(getattr(gmsh,'__version__',None)=='4.15.2',
             'Python gmsh 4.15.2 required; no marker consumed')
    print('P10IY_R1_PREFLIGHT_PASS_NO_GMSH_NO_FEM sources='+str(len(PIN))+' geo_includes=3',flush=True)


def private_bytes(pid):
    if sys.platform!='win32':
        try:
            for row in (Path('/proc')/str(pid)/'status').read_text().splitlines():
                if row.startswith('VmRSS:'):return int(row.split()[1])*1024
        except (FileNotFoundError,PermissionError):pass
        return None
    import ctypes
    from ctypes import wintypes
    class PMC(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[
            (k,ctypes.c_size_t) for k in ('peak_working','working','peak_paged','paged',
                'peak_nonpaged','nonpaged','pagefile','peak_pagefile','private')]
    k=ctypes.windll.kernel32;ps=ctypes.windll.psapi
    k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    k.OpenProcess.restype=wintypes.HANDLE
    ps.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(PMC),wintypes.DWORD]
    ps.GetProcessMemoryInfo.restype=wintypes.BOOL
    k.CloseHandle.argtypes=[wintypes.HANDLE]
    k.CloseHandle.restype=wintypes.BOOL
    handle=k.OpenProcess(0x0410,False,pid)
    if not handle:return None
    try:
        c=PMC();c.cb=ctypes.sizeof(c)
        return int(c.private) if ps.GetProcessMemoryInfo(handle,ctypes.byref(c),c.cb) else None
    finally:k.CloseHandle(handle)


def package_evidence():
    members=[MARK,RESULT,LOG,HERE/'P10IY_WORKER_RESULT.json',
             HERE/'P10IY_WORKER_ERROR.txt',HERE/'P10IY_M4_R2_CANDIDATE_UNVERIFIED.msh']
    with zipfile.ZipFile(EVIDENCE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for p in members:
            if p.is_file():out.write(p,p.name)
    with zipfile.ZipFile(EVIDENCE) as z:need(z.testzip() is None,'evidence CRC')
    print('P10IY_SEND_ONE_EVIDENCE',EVIDENCE,flush=True)


def run():
    check_preflight()
    need(sys.platform=='win32','Windows-only one-shot guard')
    user_mark=profile_mark()
    user_mark.parent.mkdir(parents=True,exist_ok=True)
    with user_mark.open('x',encoding='ascii') as out:
        out.write('P10IY M4 one Gmsh attempt consumed; do not repeat from any folder\n')
    with MARK.open('x',encoding='ascii') as out:
        out.write('P10IY M4 one guarded original-CAD 3D mesh-only; FEM=0\n')
    start=time.monotonic();next_report=0;peak=0;code=None;status='UNKNOWN'
    print('P10IY_NATIVE_M4_GMSH_START marker_consumed=1 wall_limit_s=900 memory_limit_GiB=8',flush=True)
    with LOG.open('x',encoding='utf-8') as stream:
        proc=subprocess.Popen([sys.executable,'-u',str(HERE/'P10IY_one_M4_worker.py')],
            cwd=HERE,stdout=stream,stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
        while proc.poll() is None:
            elapsed=time.monotonic()-start
            ram=private_bytes(proc.pid)
            if ram is not None:peak=max(peak,ram)
            if elapsed>=next_report:
                print('P10IY_HEARTBEAT elapsed_s='+str(round(elapsed))+
                      ' private_MiB='+str(round(peak/2**20))+
                      ' gmsh_log_bytes='+str(LOG.stat().st_size),flush=True)
                next_report+=30
            if elapsed>MAX_WALL:status='STOP_WALL';code=124
            elif ram is not None and ram>MAX_RAM:status='STOP_MEMORY';code=125
            elif LOG.stat().st_size>MAX_LOG:status='STOP_LOG';code=126
            else:
                mesh=HERE/'P10IY_M4_R2_CANDIDATE_UNVERIFIED.msh'
                if mesh.exists() and mesh.stat().st_size>MAX_MESH:
                    status='STOP_OUTPUT';code=127
            if code is not None:
                proc.kill();proc.wait();break
            time.sleep(.5)
        if code is None:
            code=proc.returncode
            status='WORKER_FINISHED' if code==0 else 'WORKER_STOP'
    mesh=HERE/'P10IY_M4_R2_CANDIDATE_UNVERIFIED.msh'
    if code==0 and (not mesh.is_file() or mesh.stat().st_size>MAX_MESH):
        status='STOP_MISSING_MESH';code=128
    result={'protocol':'P10IY_R1_DISTINCT_REPAIRED_M4_MESH_ONLY_GUARD',
            'status':status,'exit_code':code,'wall_s':round(time.monotonic()-start,3),
            'peak_private_bytes_polled':peak,'one_shot_consumed':True,
            'profile_marker_consumed':user_mark.exists(),
            'new_mesh_3D_attempts':1,'FEM_attempts':0,'accepted_M4':False,
            'mesh_sha256':sha(mesh) if mesh.is_file() else None}
    RESULT.write_text(json.dumps(result,indent=2)+'\n')
    print('P10IY_NATIVE_END',status,'exit='+str(code),'wall_s='+str(result['wall_s']),flush=True)
    package_evidence()
    return 0 if code==0 else 2


if __name__=='__main__':
    arg=argparse.ArgumentParser();arg.add_argument('--run',action='store_true')
    arg.add_argument('--source-only',action='store_true')
    opts=arg.parse_args()
    try:
        need(not (opts.run and opts.source_only),'mutually exclusive modes')
        sys.exit(run() if opts.run else (check_preflight(check_api=not opts.source_only) or 0))
    except Exception as e:
        print('P10IY_STOP_NO_RETRY',repr(e),flush=True)
        if MARK.exists() and not EVIDENCE.exists():
            package_evidence()
        sys.exit(2)
