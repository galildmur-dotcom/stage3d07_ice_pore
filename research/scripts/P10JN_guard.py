#!/usr/bin/env python3
"""P10JN distinct M5 bounded mesh-only, visible all-phase 30s heartbeat."""
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
MARK=HERE/'P10JN_R1_ONE_M5_ATTEMPT_CONSUMED.marker'
PROFILE_MARK_NAME='P10JN_R1_M5_a9fff03ca56b92c1_ONE_ATTEMPT.marker'
LOG=HERE/'P10JN_GMSH_LOG.txt'
RESULT=HERE/'P10JN_GUARD_RESULT.json'
EVIDENCE=HERE/'P10JN_R1_M5_UNVERIFIED_EVIDENCE.zip'
MESH=HERE/'P10JN_M5_R1_CANDIDATE_UNVERIFIED.msh'
HEARTBEAT_S=30
MAX_WALL=900
MAX_RAM=8*1024**3
MAX_LOG=32*1024**2
MAX_MESH=250*1024**2
PIN={
  'P10GT_HXT10.geo':'f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51',
  'M0_ROTATED.geo':'21cef72e9e0d7fde3a383b6db3ebde4bc6b62cf180b7b65947e5fe1fa57f0c9a',
  'sphere_pore_B6_refined_rotated.geo':'e3f4d1c472e4d047962bf05f63406f2bbb20b89f20e74ac2e6f2ba8cfd305329',
  'M4.msh':'a9fff03ca56b92c1d250e834bd116afee3cb0af1e846b848ef8215fb245e755c',
  'P10HA_SPATIAL_KAPPA_1200_BINS.csv':'98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3',
  'P10HA_KAPPA_QA.json':'361d8812af277505abc59b480042d5b049fb23ae6d664ad781868b985eeafae3',
  'P10IM_M3_KAPPA_HYPOTHESES_1200_BINS.csv':'be0a64d372f6520704bbc438247739bdeeda681930a879dff613c9b129e7b919',
  'P10IT_M2_M3_1200_BINS.csv':'e31c0b72946391fa4b36572292657197ecb8f31b315403128d0d2c70fbfc3c06',
  'P10JL_M5_SIGNED_SOURCE_1200_BINS.csv':'0c5c475ff1986359d28fd0c4539353b9af5f221069f346008cac7be4ac149a61',
  'P10JM_M5_SIZE_FIELD_QA.json':'e7f10e30fcedc19ed151cd6381222f92297ee082bfa8f6262fed54b4040a3f17',
  'P10JN_one_M5_worker.py':'1f6ec7bdb1616b87bcbe47d4ad89f06f5d8a243d95e122421c126e7dda87b55e',
  'p10ix_c2_m4_repair_preflight.py':'1970073d2accc405df81d3465849ee6d597fca453b9b6c885383e9619700f870',
  'P10IX_C2_FIELD_PREFLIGHT.json':'29e914b51798aeb5fe9891a0f7bdca4517004d12fe3b5e1c236151fa7d0a2f33',
  'p10iu_continuous_m4.py':'dfb57ca9dae1b52db4e9d3dc220def9e5df4eed86f2cc645e9e2252764252de8',
  'p10in_continuous_m3.py':'24bb42cbbf0a744cc97ea63d0b816eab4f8858ff91a85f2e53b1dd1d9008d390',
  'p10hc_continuous_kappa_geo.py':'07857c9f017265a6a3fb9391087e224ca97588a2dac147acd66c986d0996419d',
  'p10hk_direct_kappa_callback_benchmark.py':'0985ae7b23cbc6c029a6ab747d90869858adc9fb612bb1092a21ec807a97a431',
}


def need(condition,text):
    if not condition:raise RuntimeError('P10JN_STOP_NO_GMSH: '+text)


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
    print('P10JN_PREFLIGHT_START sources='+str(len(PIN))+' native_Gmsh=0 FEM=0',flush=True)
    started=time.monotonic()
    for index,(name,digest) in enumerate(PIN.items(),1):
        p=HERE/name
        need(p.is_file() and sha(p)==digest,'source SHA wrong: '+name)
        print('P10JN_PREFLIGHT_PROGRESS sha='+str(index)+'/'+str(len(PIN))+
              ' elapsed_s='+str(round(time.monotonic()-started,2)),flush=True)
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
    need(not MARK.exists(),'one-shot P10JN M5 mesh marker already consumed; NO repeat')
    if sys.platform=='win32':
        need(not profile_mark().exists(),'profile marker already consumed; NO repeat across folders')
    need(not MESH.exists(),
         'candidate output already exists; never overwrite')
    if check_api:
        import gmsh
        need(getattr(gmsh,'__version__',None)=='4.15.2',
             'Python gmsh 4.15.2 required; no marker consumed')
    print('P10JN_R1_PREFLIGHT_PASS_NO_GMSH_NO_FEM sources='+str(len(PIN))+
          ' geo_includes=3 elapsed_s='+str(round(time.monotonic()-started,2)),flush=True)


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
    print('P10JN_PACKAGE_START evidence='+EVIDENCE.name,flush=True)
    members=[MARK,RESULT,LOG,HERE/'P10JN_WORKER_RESULT.json',
             HERE/'P10JN_WORKER_ERROR.txt',MESH]
    with zipfile.ZipFile(EVIDENCE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as out:
        for p in members:
            if p.is_file():out.write(p,p.name)
    with zipfile.ZipFile(EVIDENCE) as z:need(z.testzip() is None,'evidence CRC')
    print('P10JN_PACKAGE_END size_bytes='+str(EVIDENCE.stat().st_size),flush=True)
    print('P10JN_SEND_ONE_EVIDENCE',EVIDENCE,flush=True)


def tail(path):
    try:
        with path.open('rb') as source:
            size=source.seek(0,2)
            source.seek(max(0,size-4096))
            lines=[row.strip() for row in source.read().decode('utf-8','replace').splitlines() if row.strip()]
        return lines[-1][-145:] if lines else 'native_log_has_no_lines_yet'
    except OSError:
        return 'native_log_not_yet_available'


def monitor(proc,log,mesh,*,interval=HEARTBEAT_S,wall=MAX_WALL,ramlimit=MAX_RAM,
            loglimit=MAX_LOG,meshlimit=MAX_MESH):
    """Heartbeat independent of child stdout; injectable interval for silent-child QA."""
    start=time.monotonic();next_report=0.;peak=0;code=None;status='UNKNOWN'
    beats=0;previous_log_size=-1;last_log_change=start
    while proc.poll() is None:
        now=time.monotonic();elapsed=now-start
        ram=private_bytes(proc.pid)
        if ram is not None:peak=max(peak,ram)
        logbytes=log.stat().st_size if log.is_file() else 0
        meshbytes=mesh.stat().st_size if mesh.is_file() else 0
        if logbytes!=previous_log_size:
            last_log_change=now;previous_log_size=logbytes
        if elapsed>=next_report:
            beats+=1
            print('P10JN_GMSH_HEARTBEAT phase=3D pid='+str(proc.pid)+
                  ' alive=1 elapsed_s='+str(round(elapsed,1))+
                  ' peak_private_MiB='+str(round(peak/2**20))+
                  ' log_bytes='+str(logbytes)+' mesh_bytes='+str(meshbytes)+
                  ' log_unchanged_s='+str(round(now-last_log_change,1))+
                  ' native_step=unknown log_tail='+tail(log),flush=True)
            next_report+=interval
        if elapsed>wall:status='STOP_WALL';code=124
        elif ram is not None and ram>ramlimit:status='STOP_MEMORY';code=125
        elif logbytes>loglimit:status='STOP_LOG';code=126
        elif meshbytes>meshlimit:status='STOP_OUTPUT';code=127
        if code is not None:
            proc.kill();proc.wait();break
        time.sleep(.20 if interval<5 else .5)
    if code is None:
        code=proc.returncode
        status='WORKER_FINISHED' if code==0 else 'WORKER_STOP'
    return {'status':status,'exit_code':code,'wall_s':round(time.monotonic()-start,3),
            'peak_private_bytes_polled':peak,'heartbeat_count':beats,
            'heartbeat_interval_s':interval}


def run():
    print('P10JN_RUN_START phase=preflight expected_mesh_s=10-120 max_wall_s=900',flush=True)
    check_preflight()
    need(sys.platform=='win32','Windows-only one-shot guard')
    user_mark=profile_mark()
    user_mark.parent.mkdir(parents=True,exist_ok=True)
    with user_mark.open('x',encoding='ascii') as out:
        out.write('P10JN M5 one Gmsh attempt consumed; do not repeat from any folder\n')
    with MARK.open('x',encoding='ascii') as out:
        out.write('P10JN M5 one guarded original-CAD 3D mesh-only; FEM=0\n')
    print('P10JN_GMSH_START marker_consumed=1 wall_limit_s=900 memory_limit_GiB=8',flush=True)
    try:
        with LOG.open('x',encoding='utf-8') as stream:
            proc=subprocess.Popen([sys.executable,'-u',str(HERE/'P10JN_one_M5_worker.py')],
                cwd=HERE,stdout=stream,stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,env={**os.environ,'OPENBLAS_NUM_THREADS':'1'})
            result=monitor(proc,LOG,MESH)
    except BaseException as exc:
        result={'status':'STOP_MONITOR','exit_code':129,'wall_s':None,
                'peak_private_bytes_polled':0,'heartbeat_count':0,
                'error':repr(exc)}
    if result['exit_code']==0 and (not MESH.is_file() or MESH.stat().st_size>MAX_MESH):
        result.update(status='STOP_MISSING_MESH',exit_code=128)
    result.update(protocol='P10JN_R1_DISTINCT_M5_MESH_ONLY_GUARD',
                  one_shot_consumed=True,profile_marker_consumed=user_mark.exists(),
                  new_mesh_3D_attempts=1,FEM_attempts=0,accepted_M5=False,
                  mesh_sha256=sha(MESH) if MESH.is_file() else None)
    RESULT.write_text(json.dumps(result,indent=2)+'\n')
    print('P10JN_GMSH_END status='+result['status']+' exit='+str(result['exit_code'])+
          ' wall_s='+str(result['wall_s']),flush=True)
    package_evidence()
    return 0 if result['exit_code']==0 else 2


if __name__=='__main__':
    arg=argparse.ArgumentParser();arg.add_argument('--run',action='store_true')
    arg.add_argument('--source-only',action='store_true')
    opts=arg.parse_args()
    try:
        need(not (opts.run and opts.source_only),'mutually exclusive modes')
        sys.exit(run() if opts.run else (check_preflight(check_api=not opts.source_only) or 0))
    except Exception as e:
        print('P10JN_STOP_NO_RETRY',repr(e),flush=True)
        if MARK.exists() and not EVIDENCE.exists():
            package_evidence()
        sys.exit(2)
