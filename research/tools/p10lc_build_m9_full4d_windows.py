#!/usr/bin/env python3
"""Prepare a distinct M9 full4D Windows one-shot; never execute FEM here."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10kv_package'
NEW=ROOT/'p10lc_package'
ZIP=ROOT/'P10LC_M9_R1_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261125.zip'
MESH=ROOT/'p10kz_inputs/P10KY_M9_R1_CANDIDATE_UNVERIFIED.msh'
PASSPORT=ROOT/'p10kz_inputs/P10LB_M9_R1_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json'
M9_SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def exact(s,old,new):
    if s.count(old)!=1:raise RuntimeError(f'expected exactly one source token {old!r}, found {s.count(old)}')
    return s.replace(old,new)

def main():
    if NEW.exists() or ZIP.exists():raise RuntimeError('P10LC output already present; no overwrite')
    assert sha(MESH)==M9_SHA
    geo=json.loads(PASSPORT.read_text(encoding='utf8'))
    assert geo['status']=='GEOMETRY_GO_ONLY_NO_FEM' and geo['mesh_sha256']==M9_SHA
    assert geo['D029_adaptation_target_GO'] and geo['D031_geometry_quality_GO']
    shutil.copytree(OLD/'P10KV_WORK',NEW/'P10LC_WORK')
    (NEW/'P10LC_WORK/M8.msh').unlink()
    shutil.copy2(MESH,NEW/'P10LC_WORK/M9.msh')
    shutil.copy2(PASSPORT,NEW/'P10LC_WORK/P10LB_M9_R1_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json')
    (NEW/'P10LC_WORK/P10KU_M8_R3_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json').unlink()
    oldrunner=NEW/'P10LC_WORK/P10KV_M8_FIRST_FULL4D.py'
    runner=oldrunner.read_text(encoding='utf8')
    runner=runner.replace('P10KV','P10LC').replace('M8','M9')
    runner=exact(runner,'P10KU_M9_R3_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json',
                        'P10LB_M9_R1_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json')
    runner=exact(runner,"'e0077bcaa940f62b5c1be5e069927226320b2646a960930c39299f1d294f4ca8'",
                        "'"+sha(PASSPORT)+"'")
    runner=exact(runner,"M9_SHA = '40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d'",
                        "M9_SHA = '"+M9_SHA+"'")
    runner=exact(runner,'M9_TET10 = 12546','M9_TET10 = 13166')
    runner=exact(runner,'M9_NODES = 18331','M9_NODES = 19236')
    runner=exact(runner,'M9_PORE_TRI6 = 648','M9_PORE_TRI6 = 734')
    runner=exact(runner,'P10KU_D031_D029_REAL_M9_R3_GEOMETRY_GO_20261125',
                        'P10LB_D031_D029_REAL_M9_R1_GEOMETRY_GO_20261125')
    # Distinct marker prefix + exact SHA ensures no reuse of old M8 one-shot.
    assert "RUNS/'P10LC_M9_ONE_SHOT_MARKERS'" in runner
    assert "f'M9_R_DT{DT}_STEPS{STEPS}_{M9_SHA[:16]}.json'" in runner
    assert "'--mode','R'" in runner and "'--cutoff-mm','5'" in runner
    assert 'wall_s=2400' in runner and 'memory_gib=8' in runner
    assert "independent_time_audit(result,'M9',M9_TET10,DT,STEPS)" in runner
    assert "'mesh_source':'P10LB_D031_D029_REAL_M9_R1_GEOMETRY_GO_20261125'" in runner
    ast.parse(runner)
    (NEW/'P10LC_WORK/P10LC_M9_FIRST_FULL4D.py').write_text(runner,encoding='utf8')
    oldrunner.unlink()

    oldheart=NEW/'P10LC_WORK/P10KV_heartbeat.py'
    heart=oldheart.read_text(encoding='utf8').replace('P10KV','P10LC').replace('M8','M9')
    ast.parse(heart)
    (NEW/'P10LC_WORK/P10LC_heartbeat.py').write_text(heart,encoding='utf8')
    oldheart.unlink()
    for oldname,newname in [('01_P10KV_M8_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd',
                              '01_P10LC_M9_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd'),
                             ('02_P10KV_ONE_M8_FIRST_FULL4D_FEM.cmd',
                              '02_P10LC_ONE_M9_FIRST_FULL4D_FEM.cmd')]:
        cmd=(OLD/oldname).read_text(encoding='utf8').replace('P10KV','P10LC').replace('M8','M9')
        (NEW/newname).write_text(cmd,encoding='utf8')
    readme=(
        '# P10LC — первая отдельная M9 R1 полная 4D физика\n\n'
        'Принятая сетка M9 R1 SHA256 '+M9_SHA+', 19,236 nodes / 13,166 Tet10 / 734 pore Tri6.\n'
        'P10LB geometry passport SHA256 '+sha(PASSPORT)+'.\n'
        '101 исходник C++ solver SHA сохранён от проверенного P10KV M8.\n'
        'Режим R/EDV_VAR/xi0/B6 5мм, 36×25с (900с), 4 потока, fresh forward '
        '+ analytic same-mesh adjoint, полный signed4D.\n\n'
        'В НОВОЙ папке сначала `01_P10LC_M9_PREFLIGHT_AND_WINDOWS_WATCHDOG_TEST.cmd` '
        '(~65–80с). Обязательно `P10LC_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS` и exit0. '
        'Это только проверка, никакого FEM и marker.\n'
        'Затем строго ОДИН раз `02_P10LC_ONE_M9_FIRST_FULL4D_FEM.cmd`. Ожидаемое время '
        '20–35 минут на i7-7700K (прежний M8 wall1246.545с; M9 ~5% больше Tet10). '
        'Hard wall cap 2400с, Windows Job private memory ≤8GiB, output≤2GiB; '
        'независимые сообщения каждые15с и измерение загрузки CPU. Marker создаётся '
        'до запуска solver и после STOP не подлежит повторному использованию.\n'
        'Верните только `P10LC_M9_FIRST_FULL4D_EVIDENCE.zip` из `LOCAL_RUNS/P10LC_M9_R_DT25_*`. '
        'Не присылайте истории, VTU или повторно M8 архив. FEM=0 в момент подготовки.\n')
    (NEW/'README_P10LC_RU.md').write_text(readme,encoding='utf8')
    with zipfile.ZipFile(ZIP,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(NEW.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(NEW).as_posix())
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print(json.dumps({'status':'P10LC_M9_R1_FIRST_FULL4D_PREPARED_NOT_RUN',
         'zip_sha256':sha(ZIP),'source_count':sum(x.is_file() for x in NEW.rglob('*')),
         'M9_sha256':M9_SHA,'passport_sha256':sha(PASSPORT),'FEM_attempts':0},indent=2))

if __name__=='__main__':main()
