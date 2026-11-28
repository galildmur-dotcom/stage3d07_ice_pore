#!/usr/bin/env python3
"""P10EZ: isolated Windows-only, once-only 1D evaluation of exact P10EY MathEval."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from P10DO_windows_guards import child_private_bytes, free_windows_ram

HERE = Path(__file__).resolve().parent
RUNS = HERE / "P10EZ_RUNS"
SOURCE = HERE / "P10EY_M2_C1_JOINT_STRCAT_SIGN_SOURCE_ONLY.geo"
EXPECTED = "2aec3e2626b3500388954e428d880c702a4bb820116af93924b8d590bf9b26f1"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
CONFIRM = "RUN ONE P10EZ MATH 1D"
WALL = 20
MEMORY = 2 * 1024**3
MAX_LOG = 2 * 1024**2
MAX_MSH = 10 * 1024**2


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def check(test, why):
    if not test:
        raise RuntimeError("P10EZ_STOP: " + why)


def source_check():
    check(SOURCE.is_file() and sha(SOURCE) == EXPECTED, "exact P10EY GEO changed")
    source = SOURCE.read_text(encoding="utf-8")
    check(source.count('Field[6].F = StrCat(') == 1 and
          source.count('Background Field=6;') == 1 and
          source.count('Include "sphere_pore_B6_refined.geo";') == 1,
          "unexpected P10EY source structure")
    strings = re.findall(r'^\s*"([^"]*)"', source, flags=re.M)
    check(len(strings) == 7 and list(map(len, strings)) == [600]*6+[597],
          "Gmsh StrCat tokens changed")
    expression = "".join(strings)
    check(len(expression) == 4197 and
          not any(pair in expression for pair in ('+-', '-+', '++', '--', '*-', '/-')),
          "MathEx sign / length contract")
    return source


def generated_geo():
    source = source_check()
    fields = source[source.index('Field[6] = MathEval;'):]
    # Three separate physical curves: north and south polar caps and equator.
    # No 3D pore/ice CAD, no surfaces or volumes; F6 expression unmodified.
    geometry = '''SetFactory("Built-in");
Point(1) = {0,0,0.03105,0.0001};
Point(2) = {0,0,0.03305,0.0001};
Point(3) = {0,0,0.02895,0.0001};
Point(4) = {0,0,0.02695,0.0001};
Point(5) = {0.00105,0,0.03,0.0001};
Point(6) = {0.00305,0,0.03,0.0001};
Line(1) = {1,2};
Line(2) = {3,4};
Line(3) = {5,6};
Physical Curve("NORTH",101) = {1};
Physical Curve("SOUTH",102) = {2};
Physical Curve("EQUATOR",103) = {3};
'''
    return geometry + fields + '\nMesh.ElementOrder=1;\nMesh.MshFileVersion=2.2;\n'


def marker_path():
    appdata = os.getenv('LOCALAPPDATA', '')
    check(bool(appdata) and Path(appdata).is_dir(), "LOCALAPPDATA unavailable")
    return Path(appdata) / "Stage3D07" / "P10EZ_MATHEX_1D_ONCE.json"


def guard_run(exe, argv, cwd, log, mesh, timeout):
    # Poll the exact child private bytes, wall clock, log and mesh sizes.
    start = time.monotonic()
    peak = 0
    kill_reason = None
    with log.open('x', encoding='utf-8') as stream:
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                 stdout=stream, stderr=subprocess.STDOUT)
        try:
            while child.poll() is None:
                peak = max(peak, child_private_bytes(child))
                if time.monotonic()-start > timeout:
                    kill_reason = 'WALL_LIMIT'
                elif peak > MEMORY:
                    kill_reason = 'PRIVATE_LIMIT'
                elif log.stat().st_size > MAX_LOG:
                    kill_reason = 'LOG_LIMIT'
                elif mesh.is_file() and mesh.stat().st_size > MAX_MSH:
                    kill_reason = 'MSH_LIMIT'
                if kill_reason:
                    child.kill()
                    break
                time.sleep(.1)
            child.wait(timeout=5)
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)
    return {'exit': child.returncode, 'wall_s': time.monotonic()-start,
            'log_bytes': log.stat().st_size, 'peak_private_bytes':peak,
            'kill_reason':kill_reason}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=['selftest','preflight','one-1d'], required=True)
    args = ap.parse_args()
    source_check()
    geo = generated_geo()
    check('Line(3)' in geo and 'Volume(' not in geo and 'Surface(' not in geo,
          "not a three-line-only geometry")
    if args.mode == 'selftest':
        print('P10EZ_SOURCE_TEST_PASS exact_P10EY_SHA=YES three_lines=YES native=0')
        return 0
    check(os.name == 'nt', 'Windows native Gmsh only')
    check(not str(HERE).casefold().startswith(r'g:\ildar\stage3d07'),
          'extract outside active Stage3D07 tree')
    check(not (RUNS/'P10EZ_ONE_USED.json').exists() and not marker_path().exists(),
          'one-shot already consumed; NEVER REMOVE MARKERS')
    exe = Path(os.getenv('P10EZ_GMSH_EXE', r'C:\gmsh-4.15.2-Windows64\gmsh.exe'))
    check(exe.is_file() and sha(exe) == GMSH_SHA, 'native Gmsh binary SHA mismatch')
    check(shutil.disk_usage(HERE).free > 300*1024**2, 'insufficient free disk')
    check(free_windows_ram() >= 4*1024**3, 'less than 4 GiB free RAM')
    RUNS.mkdir(exist_ok=True)
    run = RUNS / ('P10EZ_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    run.mkdir()
    meta = {'mode':args.mode, 'p10ey_source_sha256':EXPECTED,
            'gmsh_exe_sha256':GMSH_SHA,'native_1d_attempts':0,
            'native_2d_3d_attempts':0,'FEM_attempts':0}
    try:
        out = run/'P10EZ_THREE_LINES.geo'
        out.write_text(geo,encoding='utf-8')
        meta['test_geo_sha256'] = sha(out)
        v = subprocess.run([str(exe),'-version'],capture_output=True,text=True,timeout=10)
        check(v.returncode == 0 and '4.15.2' in v.stdout+v.stderr, 'Gmsh version')
        p = subprocess.run([str(exe),str(out),'-parse_and_exit'],
                           capture_output=True,text=True,timeout=15,cwd=str(run))
        (run/'P10EZ_PARSE.log').write_text(p.stdout+p.stderr,encoding='utf-8')
        check(p.returncode == 0 and not re.search(r'(?im)^\s*Error\s*:',p.stdout+p.stderr),
              'native GEO parse failed')
        proof = RUNS/'P10EZ_PREFLIGHT.json'
        if args.mode == 'preflight':
            proof.write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),
                                         'test_geo_sha256':sha(out), 'source_sha256':EXPECTED,
                                         'gmsh_sha256':GMSH_SHA},indent=2),encoding='utf-8')
            meta['result']='P10EZ_PREFLIGHT_PASS_NO_MESH'
        else:
            check(proof.is_file(), 'first run button 01')
            pmeta=json.loads(proof.read_text(encoding='utf-8'))
            age=(datetime.now(timezone.utc)-datetime.fromisoformat(pmeta['utc'])).total_seconds()
            check(0<=age<=86400 and pmeta['test_geo_sha256']==sha(out) and
                  pmeta['source_sha256']==EXPECTED and pmeta['gmsh_sha256']==GMSH_SHA,
                  'preflight proof invalid or older than 24h')
            check(input('Type exactly '+CONFIRM+': ').strip()==CONFIRM,
                  'manual confirmation absent')
            marker={'utc':datetime.now(timezone.utc).isoformat(), 'run':run.name,
                    'source_sha256':EXPECTED,'kind':'one native 1D Gmsh invocation'}
            marker_path().parent.mkdir(exist_ok=True)
            # Both exclusive markers are permanently consumed BEFORE native Popen.
            with marker_path().open('x',encoding='utf-8') as f: json.dump(marker,f)
            with (RUNS/'P10EZ_ONE_USED.json').open('x',encoding='utf-8') as f: json.dump(marker,f)
            meta['native_1d_attempts']=1
            msh=run/'P10EZ_THREE_LINES.msh'
            meta['native']=guard_run(exe,[str(exe),str(out),'-1','-nt','2',
                                        '-format','msh2','-o',str(msh)],str(run),
                                     run/'P10EZ_NATIVE.log',msh,WALL)
            output=(run/'P10EZ_NATIVE.log').read_text(encoding='utf-8',errors='replace')
            check(meta['native']['exit']==0 and msh.is_file() and
                  0<msh.stat().st_size<MAX_MSH and
                  not re.search(r'(?im)^\s*Error\s*:',output), 'native MathEval FAIL')
            # Verify every physical line has 1D elements in MSH2.
            lines=msh.read_text(encoding='utf-8',errors='replace').splitlines()
            i=lines.index('$Elements')
            n=int(lines[i+1]); tags=set()
            for s in lines[i+2:i+2+n]:
                a=list(map(int,s.split()))
                if a[1]==1 and a[2]>=1: tags.add(a[3])
            check({101,102,103}<=tags, 'not all three curves meshed')
            meta['native']['physical_curve_tags']=sorted(tags)
            meta['native']['mesh_sha256']=sha(msh)
            meta['result']='P10EZ_NATIVE_1D_THREE_CURVES_PASS_NO_3D_NO_FEM'
    except BaseException as exc:
        meta['result']='P10EZ_STOP_NO_3D_NO_FEM'
        meta['stop_reason']=str(exc)
        (run/'P10EZ_TRACE.txt').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        (run/'P10EZ_MANIFEST.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False),encoding='utf-8')
        archive=run/'P10EZ_EVIDENCE.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for f in sorted(run.iterdir()):
                if f.is_file() and f != archive and f.stat().st_size<MAX_MSH:
                    z.write(f,f.name)
        print('RESULT=',meta['result'],'EVIDENCE=',archive)
    return 0 if 'PASS' in meta['result'] else 2


if __name__=='__main__':
    sys.exit(main())
