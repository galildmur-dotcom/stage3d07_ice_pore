#!/usr/bin/env python3
"""P10HD: guarded Gmsh source-only parse + exactly one native 1D field test.

No -2/-3, no Tet10, no FEM. New immutable local one-shot markers.
"""
from __future__ import annotations
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zipfile
from P10FN_common import capped_process

HERE=Path(__file__).resolve().parent
GMSH=Path(r'C:\gmsh-4.15.2-Windows64\gmsh.exe')
PROJECT=Path(r'G:\ildar\Stage3D07')
SOURCE=HERE/'P10HC_CONTINUOUS_KAPPA_FIELDS.geo'
GEO=HERE/'P10HD_ONE_DIMENSIONAL_EVAL.geo'
PIN=HERE/'P10HD_SOURCE_SHA256.json'
PROOF=HERE/'P10HD_PREFLIGHT_PROOF.json'
RESULT=HERE/'P10HD_02_RESULT.txt'
REV='P10HD_R1_ONE_1D_ONLY_MATHEVAL_EVALUATOR_PROBE'


def need(ok,msg):
    if not ok:raise RuntimeError('P10HD_STOP: '+msg)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def utc():return datetime.now(timezone.utc)


def write_json(p,data):p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def verify():
    need(sys.platform=='win32','Windows user PC only')
    expected=json.loads(PIN.read_text(encoding='utf-8'))
    need(expected['revision']==REV,'revision changed')
    for name,digest in expected['files'].items():
        p=HERE/name
        need(p.is_file() and sha(p)==digest,'source SHA mismatch '+name)
    need(GMSH.is_file(),'Gmsh missing')
    r=subprocess.run([str(GMSH),'-version'],capture_output=True,text=True,timeout=12)
    need(r.returncode==0 and '4.15.2' in r.stdout,'require Gmsh 4.15.2')
    return {'revision':REV,'source_sha':expected['files'],'gmsh_version':'4.15.2'}


def markers():
    app=os.environ.get('LOCALAPPDATA','')
    need(app and Path(app).is_dir(),'LOCALAPPDATA missing')
    # New distinct P10HD namespace; never alter older markers.
    return (PROJECT/'LOCAL_RUNS'/'P10HD_ONE_SHOT_MARKERS'/'R1_ONE_1D.json',
            Path(app)/'Stage3D07'/'P10HD_ONE_SHOT_MARKERS'/'R1_ONE_1D.json')


def evidence(folder,status):
    dest=HERE/('P10HD_PREFLIGHT_EVIDENCE.zip' if status=='preflight' else
               'P10HD_ONE_1D_EVIDENCE.zip')
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in ('P10HD_SOURCE_SHA256.json','P10HD_PREFLIGHT_PROOF.json',
                     'P10HD_01_RESULT.txt','P10HD_02_RESULT.txt'):
            p=HERE/name
            if p.exists():z.write(p,name)
        for p in folder.iterdir():
            if p.is_file() and p.suffix.lower() in ('.log','.msh','.json'):
                z.write(p,p.name)
    need(zipfile.ZipFile(dest).testzip() is None,'evidence ZIP CRC')
    print('P10HD_SEND_ONE_EVIDENCE='+str(dest),flush=True)


def run_gmsh(folder,arguments,limit_s):
    log=folder/('P10HD_GMSH_PARSE.log' if '-parse_and_exit' in arguments else
                'P10HD_GMSH_1D.log')
    cmd=[str(GMSH),str(GEO),*arguments]
    if '-1' in arguments:
        native=capped_process(cmd,cwd=HERE,log=log,wall_s=limit_s,memory_gib=4,
                              output_dir=folder,output_gib=1)
        need(not native['stop_reason'] and native['native_exit_code']==0,
             'bounded native 1D STOP: '+repr(native))
        exitcode=native['native_exit_code'];wall=native['wall_s']
    else:
        begin=time.monotonic()
        with log.open('wb') as stream:
            proc=subprocess.Popen(cmd,cwd=HERE,stdout=stream,stderr=subprocess.STDOUT)
            try:exitcode=proc.wait(timeout=limit_s)
            except subprocess.TimeoutExpired:
                proc.kill();proc.wait()
                raise RuntimeError('native Gmsh timed out after '+str(limit_s)+' s')
        wall=time.monotonic()-begin
    need(log.stat().st_size<=6*1024**2,'native output log cap')
    txt=log.read_text(encoding='utf-8',errors='replace')
    need(exitcode==0 and not re.search(r'(?m)^\s*Error\s*:',txt),'Gmsh native return/log STOP')
    result={'native_exit_code':exitcode,'wall_s':round(wall,3),
            'log_sha256':sha(log),'log_file':log.name}
    if '-1' in arguments:result['native_resource_limits']=native
    return result


def preflight():
    installed=verify()
    for marker in markers():need(not marker.exists(),'already used 1D marker')
    folder=HERE/('P10HD_PREFLIGHT_'+utc().strftime('%Y%m%d_%H%M%S'))
    folder.mkdir(exist_ok=False)
    info=run_gmsh(folder,['-parse_and_exit','-nopopup','-nt','2'],120)
    proof={**installed,'utc':utc().isoformat(),'source':sha(SOURCE),
           'native_parse':info,'native_1d':0,'native_2d':0,'native_3d':0,'FEM':0}
    write_json(PROOF,proof)
    (HERE/'P10HD_01_RESULT.txt').write_text('P10HD_PARSE_PASS_NO_MESH\n',encoding='utf-8')
    evidence(folder,'preflight')
    return 0


def one_1d():
    installed=verify()
    need(PROOF.is_file(),'preflight is required')
    proof=json.loads(PROOF.read_text(encoding='utf-8'))
    need(proof['revision']==REV and proof['source_sha']==installed['source_sha']
         and proof['source']==sha(SOURCE),'preflight/source mismatch')
    age=(utc()-datetime.fromisoformat(proof['utc'])).total_seconds()
    need(0<=age<=86400,'preflight expires after 24 h')
    for marker in markers():need(not marker.exists(),'1D one-shot already consumed')
    for marker in markers():
        marker.parent.mkdir(parents=True,exist_ok=True)
        with marker.open('x',encoding='utf-8') as f:json.dump({'rev':REV,'utc':utc().isoformat()},f)
    folder=HERE/('P10HD_1D_'+utc().strftime('%Y%m%d_%H%M%S'))
    folder.mkdir(exist_ok=False)
    mesh=folder/'P10HD_1D.msh'
    manifest={'rev':REV,'status':'STOP','native_1d_attempts':1,
              'native_2d_attempts':0,'native_3d_attempts':0,'FEM_attempts':0}
    try:
        run=run_gmsh(folder,['-1','-nopopup','-nt','2','-format','msh2',
                             '-o',str(mesh)],300)
        need(mesh.is_file() and 0<mesh.stat().st_size<=16*1024**2,'1D msh file size')
        txt=(folder/'P10HD_GMSH_1D.log').read_text(encoding='utf-8',errors='replace')
        need('Done meshing 1D' in txt,'Gmsh did not finish 1D')
        # Need actual Line(1..4) node connectivity, not just parser success.
        msh=mesh.read_text(encoding='utf-8',errors='replace')
        need('$Elements' in msh and len(msh)>500,'1D MSH missing elements')
        manifest.update(native=run,msh_sha256=sha(mesh),msh_bytes=mesh.stat().st_size,
                        status='P10HD_ONE_NATIVE_1D_EVALUATOR_PASS')
    except Exception as error:manifest['error']=repr(error)
    write_json(folder/'P10HD_MANIFEST.json',manifest)
    write_json(RESULT,manifest)
    evidence(folder,'1d')
    return 0 if manifest['status'].endswith('PASS') else 2


if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('--preflight','--one-1d'):
        raise SystemExit('usage: --preflight OR --one-1d')
    try:sys.exit(preflight() if sys.argv[1]=='--preflight' else one_1d())
    except Exception as e:
        print(repr(e),flush=True)
        (HERE/'P10HD_02_RESULT.txt').write_text('P10HD_STOP='+repr(e)+'\n',encoding='utf-8')
        sys.exit(2)
