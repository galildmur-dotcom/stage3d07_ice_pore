#!/usr/bin/env python3
"""Build a distinct M8 R3 guarded mesh-only attempt after P10KQ STOP.

The only scientific callback change is removing an imported-function/local-name
collision. No old one-shot is retried; Gmsh/FEM are never invoked here.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10kq_package'
NEW=ROOT/'p10kr_package'
ZIP=ROOT/'P10KR_R3_M8_GUARDED_MESH_ONLY_WINDOWS_20261125.zip'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def one(s,old,new):
    if s.count(old)!=1:raise RuntimeError(f'expected one occurrence of {old!r}, got {s.count(old)}')
    return s.replace(old,new)

def main():
    if NEW.exists() or ZIP.exists():raise RuntimeError('existing P10KR output: no overwrite')
    oldguard=(OLD/'P10KQ_guard.py').read_text(encoding='utf8')
    pins=ast.literal_eval(oldguard.split('PIN=',1)[1].split('\n\n',1)[0])
    assert all(sha(OLD/name)==digest for name,digest in pins.items())
    NEW.mkdir()
    for name in pins:
        if name not in ('P10KQ_one_M8_R2_worker.py','p10kq_progress.py'):
            shutil.copy2(OLD/name,NEW/name)
    worker=(OLD/'P10KQ_one_M8_R2_worker.py').read_text(encoding='utf8')
    worker=one(worker,'from p10kp_m8_r2_polar_plateau import kappa_r2',
               'from p10kp_m8_r2_polar_plateau import kappa_r2 as polar_blend_m8')
    worker=one(worker,'kappa8=kappa_r2(m8.kappa(position),dmm,mu)',
               'kappa8=polar_blend_m8(m8.kappa(position),dmm,mu)')
    # Static regression: a callback local variable may not shadow the new callable.
    tree=ast.parse(worker)
    cb=next(x for x in ast.walk(tree) if isinstance(x,ast.FunctionDef) and x.name=='callback')
    assigned={target.id for node in ast.walk(cb)
              if isinstance(node,(ast.Assign,ast.AnnAssign,ast.NamedExpr))
              for target in (node.targets if isinstance(node,ast.Assign) else [node.target])
              if isinstance(target,ast.Name)}
    assert 'polar_blend_m8' not in assigned
    assert 'kappa_r2' in assigned  # the retained M7 R2 scalar is intentionally local
    calls=[n for n in ast.walk(cb) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
    assert sum(n.func.id=='polar_blend_m8' for n in calls)==1
    worker=worker.replace('P10KQ','P10KR').replace('M8_R2','M8_R3').replace('M8 R2','M8 R3')
    (NEW/'P10KR_one_M8_R3_worker.py').write_text(worker,encoding='utf8')
    progress=(OLD/'p10kq_progress.py').read_text(encoding='utf8').replace('P10KQ','P10KR')
    (NEW/'p10kr_progress.py').write_text(progress,encoding='utf8')
    newpins={name:sha(NEW/name) for name in pins if name not in ('P10KQ_one_M8_R2_worker.py','p10kq_progress.py')}
    newpins['P10KR_one_M8_R3_worker.py']=sha(NEW/'P10KR_one_M8_R3_worker.py')
    newpins['p10kr_progress.py']=sha(NEW/'p10kr_progress.py')
    guard=oldguard.replace('P10KQ','P10KR').replace('M8_R2','M8_R3').replace('R2_M8','R3_M8').replace('M8 R2','M8 R3')
    guard=guard.replace('p10kq_progress','p10kr_progress')
    guard=guard.replace('P10KR_R2_ONE_M8_ATTEMPT_CONSUMED.marker',
                        'P10KR_R3_ONE_M8_ATTEMPT_CONSUMED.marker')
    guard=guard.replace('P10KR_R2_M8_875c9177de24612d_ONE_ATTEMPT.marker',
                        'P10KR_R3_M8_875c9177de24612d_ONE_ATTEMPT.marker')
    guard=guard.replace('P10KR_R2_M8_UNVERIFIED_EVIDENCE.zip',
                        'P10KR_R3_M8_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10KR_R2_PREFLIGHT_PASS','P10KR_R3_PREFLIGHT_PASS')
    guard=guard.replace('P10KR_R2_DISTINCT_M8_MESH_ONLY_GUARD','P10KR_R3_DISTINCT_M8_MESH_ONLY_GUARD')
    start=guard.index('PIN=');end=guard.index('\n\n',start)
    guard=guard[:start]+'PIN='+repr(newpins)+guard[end:]
    (NEW/'P10KR_guard.py').write_text(guard,encoding='utf8')
    for src,dest in [('01_P10KQ_M8_R2_PREFLIGHT_AND_HEARTBEAT_TEST.cmd',
                      '01_P10KR_M8_R3_PREFLIGHT_AND_HEARTBEAT_TEST.cmd'),
                     ('02_P10KQ_ONE_M8_R2_MESH_ONLY.cmd',
                      '02_P10KR_ONE_M8_R3_MESH_ONLY.cmd')]:
        s=(OLD/src).read_text(encoding='utf8').replace('P10KQ','P10KR').replace('M8_R2','M8_R3').replace('M8 R2','M8 R3')
        (NEW/dest).write_text(s,encoding='utf8')
    (NEW/'README_P10KR_RU.md').write_text(
        '# P10KR — новая отдельная M8 R3 mesh-only попытка\n\n'
        'Причина STOP P10KQ: локальный скаляр `kappa_r2` в callback затенил импортированную функцию;\n'
        'исправлено именем `polar_blend_m8`, статический тест запрещает его локальное присваивание.\n'
        'Это техническое исправление, не изменение исходной 4D модели, CAD или сетки M7 R2.\n'
        'Старый P10KQ M8 R2 marker CONSUMED; запускать снова нельзя.\n\n'
        'В новой папке запустите `01_P10KR_M8_R3_PREFLIGHT_AND_HEARTBEAT_TEST.cmd`\n'
        '(около 65–80с; нужен P10KR_WATCHDOG_SELFTEST_PASS и exit0), затем ровно один раз\n'
        '`02_P10KR_ONE_M8_R3_MESH_ONLY.cmd` (15–180с ожидаемо, hard cap900с, RAM8GiB, 4 потока).\n'
        'Верните только `P10KR_R3_M8_UNVERIFIED_EVIDENCE.zip`. Никакого FEM.\n'
        'Новая сетка будет принята только после независимых D031 и фактической D029 N/S [.75,.85].\n',encoding='utf8')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(NEW.iterdir()):z.write(p,p.name)
    with zipfile.ZipFile(ZIP) as z:assert z.testzip() is None
    print(json.dumps({'status':'P10KR_M8_R3_PREPARED_NOT_RUN','sha256':sha(ZIP),
                      'source_files':len(list(NEW.iterdir())),
                      'static_no_callable_shadowing':True,'mesh_attempts':0,'FEM_attempts':0},indent=2))

if __name__=='__main__':main()
