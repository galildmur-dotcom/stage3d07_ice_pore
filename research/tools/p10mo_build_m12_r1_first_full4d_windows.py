#!/usr/bin/env python3
"""P10MO: separately guarded first M12 R1 physical 4D FEM; NEVER run FEM here."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10mi_package/P10MI_WORK'
PKG=ROOT/'p10mo_package'
DEST=PKG/'P10MO_WORK'
M12=ROOT/'p10ml_m12_evidence/P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'
D029=ROOT/'p10ml_m12_evidence/P10MM_M12_R1_D029.json'
D031=ROOT/'upload/P10MN_M12_R1_GMSH_QUALITY_RESULT.json'
SHA='e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13'
REV='P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('P10MO exact replacement anchor drift: '+a[:100])
    return s.replace(a,b)

def main():
    if PKG.exists():raise RuntimeError('P10MO output exists; do not overwrite')
    if sha(M12)!=SHA:raise RuntimeError('M12 accepted mesh SHA mismatch')
    d029=json.loads(D029.read_text());d031=json.loads(D031.read_text())
    assert d029['D029_PASS'] and d029['CAD_PASS'] and d029['curved_detJ_positive_PASS'] and d029['physical_tags_PASS']
    assert d029['M12_R1']['mesh_sha256']==SHA
    assert (d029['M12_R1']['nodes'],d029['M12_R1']['Tet10'],d029['M12_R1']['pore_Tri6'])==(23732,16333,1032)
    assert d031['quality_gate_pass'] and d031['mesh_sha256']==SHA and d031['Tet10']==16333
    assert d031['physical_surface_tags']==list(range(2,10)) and d031['FEM_attempts']==0
    for kind,threshold in d031['quality_thresholds'].items():
        if kind=='minDetJac':assert d031['qualities'][kind]['min']>threshold
        else:assert d031['qualities'][kind]['min']>=threshold
        assert d031['qualities'][kind]['nonpositive']==0
    pins=json.loads((OLD/'P10FN_SOURCE_SHA256.json').read_text())
    assert pins['revision']==REV and len(pins['files'])==101
    for name,digest in pins['files'].items():
        if sha(OLD/name)!=digest:raise RuntimeError('pinned solver revision drift '+name)
    shutil.copytree(OLD,DEST,ignore=shutil.ignore_patterns('__pycache__','build','*.exe'))
    (DEST/'M11.msh').unlink()
    shutil.copy2(M12,DEST/'M12.msh')
    (DEST/'P10MI_M11_R2_GEOMETRY_ACCEPTANCE_PASSPORT.json').unlink()
    passport={'protocol':'P10MO_M12_R1_D029_D031_GEOMETRY_ACCEPTANCE',
      'status':'FULL_GEOMETRY_GO','mesh_sha256':SHA,'nodes':23732,'tet10':16333,'pore_tri6':1032,
      'north_Veff_M12_R1_over_M11_R2_729':d029['D029_poles']['near_p0_N']['729']['Veff_ratio'],
      'south_Veff_M12_R1_over_M11_R2_729':d029['D029_poles']['near_p0_S']['729']['Veff_ratio'],
      'min_curved_detJ_729':d029['M12_R1']['min_curved_detJ_27_343_729'][2],
      'canonical_Gmsh_quality_min':{k:v['min'] for k,v in d031['qualities'].items()},
      'D029_PASS':True,'D031_PASS':True,'FEM_attempts':0}
    pp=DEST/'P10MO_M12_R1_GEOMETRY_ACCEPTANCE_PASSPORT.json'
    pp.write_text(json.dumps(passport,indent=2)+'\n')
    run=(OLD/'P10MI_M11_R2_FIRST_FULL4D.py').read_text()
    run=run.replace('P10MI','P10MO').replace('M11_R2','M12_R1').replace('M11','M12')
    run=once(run,"M12_SHA = 'b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726'",
             f"M12_SHA = '{SHA}'")
    run=once(run,'M12_TET10 = 15055','M12_TET10 = 16333')
    run=once(run,'M12_NODES = 21943','M12_NODES = 23732')
    run=once(run,'M12_PORE_TRI6 = 922','M12_PORE_TRI6 = 1032')
    run=once(run,"sha256(HERE/'P10MO_M12_R1_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='b98641002ee1597fcc1fe41ab32a06ec13fa4f2d02fb57ef8a14237307e30d3f'",
             f"sha256(HERE/'P10MO_M12_R1_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='{sha(pp)}'")
    assert "'mesh_source':'P10MO_M12_R1_D029_D031_FULL_GEOMETRY_GO_20261125'" in run
    (DEST/'P10MO_M12_R1_FIRST_FULL4D.py').write_text(run)
    (DEST/'P10MO_heartbeat.py').write_text((OLD/'P10MI_heartbeat.py').read_text().replace('P10MI','P10MO'))
    shutil.copy2(OLD/'P10MI_split_audit.py',DEST/'P10MO_split_audit.py')
    for name in ('P10MI_M11_R2_FIRST_FULL4D.py','P10MI_heartbeat.py','P10MI_split_audit.py'):
        (DEST/name).unlink()
    cmds=[]
    for p in sorted(OLD.parent.glob('*.cmd')):
        name=p.name.replace('P10MI','P10MO').replace('M11','M12')
        s=p.read_text().replace('P10MI','P10MO').replace('M11','M12')
        s=s.replace('P10MO_M12_R2_FIRST_FULL4D.py','P10MO_M12_R1_FIRST_FULL4D.py')
        (PKG/name).write_text(s);cmds.append(name)
    for name in ('P10MO_M12_R1_FIRST_FULL4D.py','P10MO_heartbeat.py','P10MO_split_audit.py'):
        ast.parse((DEST/name).read_text(),filename=name)
    assert len(cmds)==2
    assert all('P10MO_M12_R1_FIRST_FULL4D.py' in (PKG/n).read_text() for n in cmds)
    assert f"SOURCE_REVISION = '{REV}'" in run
    assert 'P10MO_M12_ONE_SHOT_MARKERS' in run
    assert f"sha256(HERE/'P10MO_M12_R1_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='{sha(pp)}'" in run
    assert f"SOURCE_MANIFEST_SHA = '{sha(DEST/'P10FN_SOURCE_SHA256.json')}'" in run
    (PKG/'README_P10MO_RU.md').write_text(
      '# P10MO — первый FEM на геометрически принятой M12 R1\n\n'
      'D029 и D031 PASS. Используется тот же SHA101-решатель, что на M11 R2. '
      'Режим R/EDV_VAR, xi0, B6=5 мм, 36×25 секунд, 4 потока.\n\n'
      '1. Распаковать ZIP в отдельную новую папку Windows.\n'
      '2. Запустить `01_P10MO_PREFLIGHT_NO_FEM.cmd`: SHA101, точная M12 и 65-секундный '
      'Windows-native watchdog без компиляции, FEM или маркера.\n'
      '3. При успешном сообщении `P10MO_WINDOWS_NATIVE_HEARTBEAT_SELFTEST_PASS` '
      'запустить **один раз** `02_P10MO_ONE_M12_EXTENDED_EXPLICIT_FEM.cmd`. '
      'Маркер пишется до физической попытки; при остановке не повторять.\n'
      '4. Ожидаемо 30–45 минут, жёсткий предел 40 минут (2400 с), 8 GiB RAM, '
      '2 GiB output. Если лимит исчерпан, не повторять самостоятельно.\n'
      '5. Прислать один `P10MO_M12_FIRST_FULL4D_EVIDENCE.zip`. '
      'Сетка не строится; старые M11/M10 одноразовые маркеры не расходуются.\n')
    archive=ROOT/'P10MO_M12_R1_FIRST_FULL4D_WINDOWS_ONE_SHOT_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(PKG.rglob('*')):
            if p.is_file():z.write(p,arcname=str(p.relative_to(PKG)))
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    qa={'protocol':'P10MO_M12_R1_FIRST_FULL4D_WINDOWS_PREPARED',
      'status':'SOURCE_QA_PASS_NO_FEM','mesh_sha256':SHA,'source_revision':REV,
      'source_count':101,'source_manifest_sha256':sha(DEST/'P10FN_SOURCE_SHA256.json'),
      'geometry_passport_sha256':sha(pp),'archive_sha256':sha(archive),
      'archive_bytes':archive.stat().st_size,'entrypoints':cmds,
      'FEM_attempts':0,'marker_consumed':False}
    (ROOT/'research/P10MO_M12_R1_WINDOWS_PREPARATION_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
