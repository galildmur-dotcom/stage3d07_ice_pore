#!/usr/bin/env python3
"""P10NA: build *new* one-shot M13 R2 3D Gmsh package; no native execution."""
from __future__ import annotations
import ast,hashlib,json,re,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SRC=ROOT/'p10mv_m13_a_package'
DEST=ROOT/'p10na_m13_r2_package'
ARCHIVE=ROOT/'P10NA_M13_R2_TWO_LOCAL_C2_REPAIR_MESH_ONLY_WINDOWS_20261125.zip'
BAD=ROOT/'upload/P10MY_M13_R1_BAD_TET10_LOCATIONS.json'
QUALITY=ROOT/'upload/P10MX_M13_R1_GMSH_QUALITY_RESULT.json'
R1=ROOT/'p10mv_m13_evidence/P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh'
R1_SHA='3c0b292007dce69cb70559a215ce7367b6c33fc1f7c46a6ca3396041481a1b1e'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('P10NA anchor drift: '+a[:100])
    return s.replace(a,b)

def main():
    if DEST.exists() or ARCHIVE.exists():raise RuntimeError('P10NA output exists; no overwrite')
    assert sha(R1)==R1_SHA
    q=json.loads(QUALITY.read_text(encoding='utf-8-sig'))
    bad=json.loads(BAD.read_text(encoding='utf-8-sig'))
    assert q['status']=='D031_QUALITY_HOLD' and q['mesh_sha256']==R1_SHA
    assert bad['mesh_sha256']==R1_SHA and bad['failed_element_count_unique']==2
    hits=sorted((e for e in bad['elements'] if e['below_threshold']),key=lambda e:e['element_tag'])
    assert [e['element_tag'] for e in hits]==[9035,13346]
    assert all(e['wall_distance_mm']<.025 and .60<abs(e['mu_cos_theta'])<.70 for e in hits)

    DEST.mkdir()
    for p in SRC.iterdir():
        if not p.is_file():continue
        if p.name in ('P10MV_guard.py','P10MV_one_M13_R1_worker.py','p10mv_progress.py') or p.suffix=='.cmd' or p.name.startswith('README_'):
            continue
        shutil.copy2(p,DEST/p.name)
    for p in (R1,BAD,QUALITY):shutil.copy2(p,DEST/p.name)
    worker=(SRC/'P10MV_one_M13_R1_worker.py').read_text().replace('P10MV','P10NA')
    worker=worker.replace('M13_R1_CANDIDATE_UNVERIFIED','M13_R2_CANDIDATE_UNVERIFIED')
    worker=worker.replace('M13_R1_DISTINCT_GMSH','M13_R2_DISTINCT_GMSH')
    worker=worker.replace("'accepted_M13_R1':False","'accepted_M13_R2':False")
    worker=once(worker,"M13_FIELD_SHA='5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383'",
        "M13_FIELD_SHA='5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383'\n"
        f"M13_R1_UNACCEPTED_SHA='{R1_SHA}'\n"
        f"M13_R1_BAD_LOCATOR_SHA='{sha(BAD)}'\n"
        f"M13_R1_FAILED_D031_SHA='{sha(QUALITY)}'\n"
        "M13_R2_PATCH_LOGSIZE=-.045\nM13_R2_PATCH_CORE_M=.00002\nM13_R2_PATCH_RADIUS_M=.00025")
    worker=once(worker,
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
        "    if hashlib.sha256((HERE/'P10MV_M13_R1_CANDIDATE_UNVERIFIED.msh').read_bytes()).hexdigest()!=M13_R1_UNACCEPTED_SHA:\n"
        "        raise RuntimeError('R1 exact failed mesh reference drift; no R2')\n"
        "    if hashlib.sha256((HERE/'P10MY_M13_R1_BAD_TET10_LOCATIONS.json').read_bytes()).hexdigest()!=M13_R1_BAD_LOCATOR_SHA:\n"
        "        raise RuntimeError('R1 exact 2-bad-Tet locator drift; no R2')\n"
        "    if hashlib.sha256((HERE/'P10MX_M13_R1_GMSH_QUALITY_RESULT.json').read_bytes()).hexdigest()!=M13_R1_FAILED_D031_SHA:\n"
        "        raise RuntimeError('R1 D031 quality HOLD evidence drift; no R2')\n"
        "    bad13=json.loads((HERE/'P10MY_M13_R1_BAD_TET10_LOCATIONS.json').read_text(encoding='utf-8-sig'))\n"
        "    failed=sorted((r for r in bad13['elements'] if r['below_threshold']),key=lambda r:r['element_tag'])\n"
        "    if bad13['failed_element_count_unique']!=2 or [r['element_tag'] for r in failed]!=[9035,13346]:\n"
        "        raise RuntimeError('R1 failed Tet count/IDs drift; no R2')\n"
        "    repair_m13_centers=np.asarray([r['centroid_m'] for r in failed],dtype=float)\n"
        "    if np.linalg.norm(repair_m13_centers[0]-repair_m13_centers[1])<2*M13_R2_PATCH_RADIUS_M:\n"
        "        raise RuntimeError('R2 local C2 supports overlap; no mesh')\n"
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=once(worker,
        "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor*incremental_m12*incremental_m13",
        "            # Two isolated C2 local repairs around the exact failed R1 Tet10 centers.\n"
        "            extra_weight=0.\n"
        "            for center13 in repair_m13_centers:\n"
        "                d13=float(np.linalg.norm(position-center13))\n"
        "                t13=(d13-M13_R2_PATCH_CORE_M)/(M13_R2_PATCH_RADIUS_M-M13_R2_PATCH_CORE_M)\n"
        "                extra_weight+=1.-smoothstep5(max(0.,min(1.,t13)))\n"
        "            m13_r2_repair_factor=math.exp(M13_R2_PATCH_LOGSIZE*extra_weight)\n"
        "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor*incremental_m12*incremental_m13*m13_r2_repair_factor")
    worker=once(worker,"                'M13_variant':'A_existing_residual',",
        "                'M13_variant':'A_existing_residual',\n"
        "                'M13_R1_failed_mesh_sha256':M13_R1_UNACCEPTED_SHA,\n"
        "                'M13_R1_bad_locator_sha256':M13_R1_BAD_LOCATOR_SHA,\n"
        "                'M13_R2_repair_centers_m':repair_m13_centers.tolist(),\n"
        "                'M13_R2_patch_logsize':M13_R2_PATCH_LOGSIZE,\n"
        "                'M13_R2_patch_core_m':M13_R2_PATCH_CORE_M,\n"
        "                'M13_R2_patch_support_radius_m':M13_R2_PATCH_RADIUS_M,")
    worker=worker.replace("print('P10NA_M12_R1_MESH_CREATED_UNVERIFIED_NO_FEM'",
                          "print('P10NA_M13_R2_MESH_CREATED_UNVERIFIED_NO_FEM'")
    ast.parse(worker)
    (DEST/'P10NA_one_M13_R2_worker.py').write_text(worker)

    progress=(SRC/'p10mv_progress.py').read_text().replace('P10MV','P10NA')
    (DEST/'p10na_progress.py').write_text(progress)
    guard=(SRC/'P10MV_guard.py').read_text().replace('P10MV','P10NA')
    guard=guard.replace('P10NA_one_M13_R1_worker.py','P10NA_one_M13_R2_worker.py')
    guard=guard.replace('M13_R1_CANDIDATE_UNVERIFIED','M13_R2_CANDIDATE_UNVERIFIED')
    guard=guard.replace('P10NA_R1_ONE_M13_ATTEMPT_CONSUMED','P10NA_R2_ONE_M13_ATTEMPT_CONSUMED')
    guard=guard.replace('P10NA_R1_M13_e3c5c5dc9bbcae3d0b2_A_ONE_ATTEMPT',
                        'P10NA_R2_M13_3c0b292007dce69c_TWO_C2_ONE_ATTEMPT')
    guard=guard.replace('P10NA_R1_M13_UNVERIFIED_EVIDENCE','P10NA_R2_M13_UNVERIFIED_EVIDENCE')
    guard=guard.replace('P10NA_R1_DISTINCT_M13_A_C2_MESH_ONLY_GUARD',
                        'P10NA_R2_DISTINCT_M13_A_TWO_LOCAL_C2_MESH_ONLY_GUARD')
    guard=guard.replace('accepted_M13_R1=False','accepted_M13_R2=False')
    guard=guard.replace('P10NA R1','P10NA R2').replace('M13 R1 one','M13 R2 one')
    guard=guard.replace('from p10mv_progress import Watchdog','from p10na_progress import Watchdog')
    rawpin=guard.split('PIN=',1)[1].split('\n\n',1)[0]
    pin=ast.literal_eval(rawpin)
    # Keep all preexisting 45-plus SHA pins, but replace old runner files and
    # introduce independently pinned evidence of the failed R1 attempt.
    pin.pop('P10NA_one_M13_R1_worker.py',None)
    pin.pop('p10mv_progress.py',None)
    pin.pop('p10na_progress.py',None)
    pin['P10NA_one_M13_R2_worker.py']=sha(DEST/'P10NA_one_M13_R2_worker.py')
    pin['p10na_progress.py']=sha(DEST/'p10na_progress.py')
    for path in (R1,BAD,QUALITY):pin[path.name]=sha(path)
    guard=once(guard,'PIN='+rawpin,'PIN='+repr(pin))
    ast.parse(guard)
    (DEST/'P10NA_guard.py').write_text(guard)
    assert all((DEST/k).is_file() and sha(DEST/k)==v for k,v in pin.items())
    assert len(pin)==len(set(pin)) and 'P10MV_R1_ONE_M13_ATTEMPT_CONSUMED' not in guard

    (DEST/'01_P10NA_M13_R2_PREFLIGHT_NO_GMSH.cmd').write_text(
      '@echo off\nif /I "%~1"=="--visible" goto RUN\n'
      'start "P10NA M13 R2 SHA PREFLIGHT" cmd.exe /K call "%~f0" --visible\nexit /b %ERRORLEVEL%\n'
      ':RUN\ncd /d "%~dp0"\necho P10NA_M13_R2_SOURCE_PREFLIGHT_NO_GMSH_NO_FEM_NO_MARKER\n'
      'where py >nul 2>nul\nif not errorlevel 1 (\n    py -3 -u P10NA_guard.py --source-only\n'
      ') else (\n    python -u P10NA_guard.py --source-only\n)\n'
      'set "P10NA_RC=%ERRORLEVEL%"\necho P10NA_PREFLIGHT_EXIT=%P10NA_RC%\nexit /b %P10NA_RC%\n',newline='\r\n')
    (DEST/'02_P10NA_ONE_M13_R2_GMSH_MESH_ONLY.cmd').write_text(
      '@echo off\nif /I "%~1"=="--visible" goto RUN\n'
      'start "P10NA ONE M13 R2 MESH NO FEM" cmd.exe /K call "%~f0" --visible\nexit /b %ERRORLEVEL%\n'
      ':RUN\ncd /d "%~dp0"\necho P10NA_ONE_M13_R2_GMSH_ONLY_FEM_ZERO\n'
      'where py >nul 2>nul\nif not errorlevel 1 (\n    py -3 -u P10NA_guard.py --run\n'
      ') else (\n    python -u P10NA_guard.py --run\n)\n'
      'set "P10NA_RC=%ERRORLEVEL%"\necho P10NA_M13_R2_EXIT=%P10NA_RC%\nexit /b %P10NA_RC%\n',newline='\r\n')
    (DEST/'README_P10NA_RU.md').write_text(
      '# P10NA — M13 R2: отдельная однократная Gmsh-сетка, FEM=0\n\n'
      'M13 R1 не прошла D031 ровно на двух Tet10 №9035 и №13346 в тонком пристеночном слое. '
      'M13 R2 сохраняет A и все множители M1–M13, добавляя две неперекрывающиеся '
      'локальные поправки C2 радиусом 0.25 мм, ядро 0.02 мм, логарифмический размер −0.045. '
      'Это проверяемая гипотеза, не гарантия улучшения качества.\n\n'
      '1. Распаковать ZIP в **новую** пустую папку Windows 11. Python 3, numpy, Gmsh API 4.15.2.\n'
      '2. Запустить `01_P10NA_M13_R2_PREFLIGHT_NO_GMSH.cmd`. Проверка SHA без Gmsh, FEM и маркера.\n'
      '3. При PASS запустить **один раз** `02_P10NA_ONE_M13_R2_GMSH_MESH_ONLY.cmd`. '
      'Новый отдельный M13 R2 маркер расходуется перед родным Gmsh, повторы запрещены.\n'
      '4. Контроль состояния раз в 15 секунд; 20 минут, 8 GiB и 250 MiB пределы.\n'
      '5. Вернуть **один** `P10NA_R2_M13_UNVERIFIED_EVIDENCE.zip`. '
      'Не запускать FEM; затем отдельно D029 и D031. Не повторять M13 R1.\n')
    with zipfile.ZipFile(ARCHIVE,'x',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(DEST.iterdir()):
            if p.is_file():z.write(p,p.name)
    with zipfile.ZipFile(ARCHIVE) as z:assert z.testzip() is None
    print(json.dumps({'protocol':'P10NA_M13_R2_PACKAGE_BUILD','status':'BUILT_NOT_RUN_NO_GMSH_NO_FEM_NO_MARKER',
        'archive_sha256':sha(ARCHIVE),'archive_bytes':ARCHIVE.stat().st_size,
        'hash_pinned_sources':len(pin),'worker_sha256':sha(DEST/'P10NA_one_M13_R2_worker.py'),
        'failed_parent_M13_R1_sha256':R1_SHA,'two_locator_tags':[9035,13346]},indent=2))

if __name__=='__main__':main()
