#!/usr/bin/env python3
"""Prepare P10MI one-shot M11 R2 physical FEM; build only, NEVER run FEM."""
import ast
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT/'p10ly_package_r2/P10LY_WORK'
DESTROOT = ROOT/'p10mi_package'
DEST = DESTROOT/'P10MI_WORK'
MESH = ROOT/'p10mf_m11_r2_evidence/P10MF_M11_R2_CANDIDATE_UNVERIFIED.msh'
D029 = ROOT/'p10mf_m11_r2_evidence/P10MG_M11_R2_D029.json'
D031 = ROOT/'upload/P10MH_M11_R2_GMSH_QUALITY_RESULT.json'
SHA = 'b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726'
REV = 'P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def exact(s, old, new):
    if s.count(old) != 1:
        raise RuntimeError('P10MI replacement anchor missing/multiple: '+old[:100])
    return s.replace(old, new)

def main():
    if DESTROOT.exists():
        raise RuntimeError('P10MI output already exists: avoid overwrite')
    if digest(MESH) != SHA:
        raise RuntimeError('M11 R2 mesh SHA mismatch')
    a, b = json.loads(D029.read_text()), json.loads(D031.read_text())
    assert a['D029_PASS'] and a['CAD_PASS'] and a['curved_detJ_positive_PASS'] and a['physical_tags_PASS']
    assert a['M11_R2']['mesh_sha256'] == SHA
    assert (a['M11_R2']['nodes'], a['M11_R2']['Tet10'], a['M11_R2']['pore_Tri6']) == (21943,15055,922)
    assert b['quality_gate_pass'] and b['mesh_sha256'] == SHA and b['Tet10'] == 15055
    assert b['physical_surface_tags'] == list(range(2,10)) and b['FEM_attempts'] == 0
    for key, threshold in b['quality_thresholds'].items():
        assert b['qualities'][key]['min'] > threshold if key=='minDetJac' else b['qualities'][key]['min'] >= threshold
        assert b['qualities'][key]['nonpositive'] == 0
    pins=json.loads((OLD/'P10FN_SOURCE_SHA256.json').read_text())
    assert pins['revision']==REV and len(pins['files'])==101
    for path, expected in pins['files'].items():
        if digest(OLD/path)!=expected:
            raise RuntimeError('101-file pinned solver drift: '+path)
    shutil.copytree(OLD,DEST,ignore=shutil.ignore_patterns('__pycache__','build','*.exe'))
    (DEST/'M10.msh').unlink()
    shutil.copy2(MESH,DEST/'M11.msh')
    (DEST/'P10LY_M10_GEOMETRY_ACCEPTANCE_PASSPORT.json').unlink()
    passport={
        'protocol':'P10MI_M11_R2_D029_D031_GEOMETRY_ACCEPTANCE',
        'status':'FULL_GEOMETRY_GO','mesh_sha256':SHA,
        'nodes':21943,'tet10':15055,'pore_tri6':922,
        'north_Veff_M11_R2_over_M10_729':a['D029_poles']['near_p0_N']['729']['Veff_ratio'],
        'south_Veff_M11_R2_over_M10_729':a['D029_poles']['near_p0_S']['729']['Veff_ratio'],
        'min_curved_detJ_729':a['M11_R2']['min_curved_detJ_27_343_729'][2],
        'canonical_Gmsh_quality_min':{k:v['min'] for k,v in b['qualities'].items()},
        'D029_PASS':True,'D031_PASS':True,'FEM_attempts':0}
    pp=DEST/'P10MI_M11_R2_GEOMETRY_ACCEPTANCE_PASSPORT.json'
    pp.write_text(json.dumps(passport,indent=2)+'\n')
    src=(OLD/'P10LY_M10_FIRST_FULL4D.py').read_text()
    src=src.replace('P10LY','P10MI').replace('M10','M11')
    src=exact(src,"M11_SHA = '022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'",f"M11_SHA = '{SHA}'")
    src=exact(src,'M11_TET10 = 13996','M11_TET10 = 15055')
    src=exact(src,'M11_NODES = 20420','M11_NODES = 21943')
    src=exact(src,'M11_PORE_TRI6 = 814','M11_PORE_TRI6 = 922')
    src=exact(src,"sha256(HERE/'P10MI_M11_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='aa89df4bdb8545fdfb4c1c2ce989de63aa58cd8f87acdc2b661c93d1e303f38c'",
              f"sha256(HERE/'P10MI_M11_R2_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='{digest(pp)}'")
    src=exact(src,"'mesh_source':'P10MI_M11_D029_D031_FULL_GEOMETRY_GO_20261125'",
              "'mesh_source':'P10MI_M11_R2_D029_D031_FULL_GEOMETRY_GO_20261125'")
    # New P10MI marker namespace and one-shot evidence; 101 solver files are unchanged.
    (DEST/'P10MI_M11_R2_FIRST_FULL4D.py').write_text(src)
    (DEST/'P10MI_heartbeat.py').write_text((OLD/'P10LY_heartbeat.py').read_text().replace('P10LY','P10MI'))
    shutil.copy2(OLD/'P10LY_split_audit.py',DEST/'P10MI_split_audit.py')
    for name in ('P10LY_M10_FIRST_FULL4D.py','P10LY_heartbeat.py','P10LY_split_audit.py'):
        (DEST/name).unlink()
    cmds=[]
    for f in sorted(OLD.parent.glob('*.cmd')):
        name=f.name.replace('P10LY','P10MI').replace('M10','M11')
        s=f.read_text().replace('P10LY','P10MI').replace('M10','M11')
        s=s.replace('P10MI_M11_FIRST_FULL4D.py','P10MI_M11_R2_FIRST_FULL4D.py')
        (DESTROOT/name).write_text(s)
        cmds.append(name)
    for name in ('P10MI_M11_R2_FIRST_FULL4D.py','P10MI_heartbeat.py','P10MI_split_audit.py'):
        ast.parse((DEST/name).read_text(),filename=name)
    assert len(cmds)==2 and all('P10MI_M11_R2_FIRST_FULL4D.py' in (DESTROOT/n).read_text() for n in cmds)
    assert f"SOURCE_REVISION = '{REV}'" in src
    assert "P10MI_M11_ONE_SHOT_MARKERS" in src
    assert f"sha256(HERE/'P10MI_M11_R2_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='{digest(pp)}'" in src
    assert f"SOURCE_MANIFEST_SHA = '{digest(DEST/'P10FN_SOURCE_SHA256.json')}'" in src
    (DESTROOT/'README_P10MI_RU.md').write_text(
        '# P10MI — первый физический 4D FEM на принятой M11 R2\n\n'
        'D029 и D031 — PASS, SHA M11 R2 зафиксирован. Тот же решатель SHA101 и режим '
        'R/EDV_VAR, xi0, B6=5 мм, 36×25 с, 4 потока.\n\n'
        '1. Распакуйте ZIP в **новую** папку на Windows.\n'
        '2. Запустите `01_P10MI_PREFLIGHT_NO_FEM.cmd`: проверка SHA101/геометрии '
        'и 65-секундный нативный watchdog. Он не компилирует и не запускает FEM, маркер не расходует.\n'
        '3. Только после `P10MI_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS` запустите '
        '`02_P10MI_ONE_M11_EXTENDED_EXPLICIT_FEM.cmd` **один раз**. '
        'Маркер пишется перед физической попыткой, повтор после остановки запрещён.\n'
        '4. Ориентир 25–40 минут, жёсткий предел 2400 с, до 8 GiB RAM и 2 GiB output.\n'
        '5. Пришлите единственный `P10MI_M11_FIRST_FULL4D_EVIDENCE.zip`. '
        'Пакет не генерирует сетку; старые M9/M10 FEM-маркеры не трогает.\n')
    archive=ROOT/'P10MI_M11_R2_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for f in sorted(DESTROOT.rglob('*')):
            if f.is_file():z.write(f,arcname=str(f.relative_to(DESTROOT)))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    qa={'protocol':'P10MI_M11_R2_FIRST_FULL4D_WINDOWS_PREPARED',
        'status':'SOURCE_QA_PASS_NO_FEM','mesh_sha256':SHA,
        'source_revision':REV,'source_count':101,
        'source_manifest_sha256':digest(DEST/'P10FN_SOURCE_SHA256.json'),
        'geometry_passport_sha256':digest(pp),'archive_sha256':digest(archive),
        'archive_bytes':archive.stat().st_size,'entrypoints':cmds,
        'FEM_attempts':0,'marker_consumed':False}
    (ROOT/'research/P10MI_M11_R2_WINDOWS_PREPARATION_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':
    main()
