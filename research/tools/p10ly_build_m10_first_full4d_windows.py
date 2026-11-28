#!/usr/bin/env python3
"""P10LY: separately guarded M10 physical full4D, unchanged P10LM solver."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10lm_package/P10LM_WORK'
PKG=ROOT/'p10ly_package_r2'
DEST=PKG/'P10LY_WORK'
M10=ROOT/'p10lv_m10_evidence/P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh'
D029=ROOT/'p10lv_m10_evidence/P10LW_M10_INDEPENDENT_D029.json'
D031=ROOT/'upload/P10LX_M10_R1_GMSH_QUALITY_RESULT.json'
M10_SHA='022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'
REV='P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('anchor expected exactly once: '+a[:85])
    return s.replace(a,b)

def main():
    if PKG.exists():raise RuntimeError('P10LY output exists; no overwrite')
    if sha(M10)!=M10_SHA:raise RuntimeError('M10 accepted mesh SHA drift')
    d029=json.loads(D029.read_text());d031=json.loads(D031.read_text())
    if (not d029['D029_PASS'] or not d029['CAD_PASS'] or not d029['curved_detJ_positive_PASS'] or
        not d029['physical_tags_PASS'] or d029['M10']['mesh_sha256']!=M10_SHA or
        not d031['quality_gate_pass'] or d031['mesh_sha256']!=M10_SHA or
        d031['Tet10']!=13996 or d031['physical_surface_tags']!=list(range(2,10))):
        raise RuntimeError('M10 D029/D031 not accepted')
    pins=json.loads((OLD/'P10FN_SOURCE_SHA256.json').read_text())
    if pins['revision']!=REV or len(pins['files'])!=101:raise RuntimeError('old source revision drift')
    for p,h in pins['files'].items():
        if sha(OLD/p)!=h:raise RuntimeError('old solver SHA drift '+p)
    shutil.copytree(OLD,DEST,ignore=shutil.ignore_patterns('__pycache__','build','*.exe'))
    (DEST/'M9.msh').unlink()
    shutil.copy2(M10,DEST/'M10.msh')
    # Passport is a pinned intersection of two independent geometric gates.
    passport={'protocol':'P10LY_M10_R1_D029_D031_GEOMETRY_ACCEPTANCE',
      'status':'FULL_GEOMETRY_GO','mesh_sha256':M10_SHA,'nodes':20420,
      'tet10':13996,'pore_tri6':814,
      'north_Veff_M10_over_M9_729':d029['D029_poles']['near_p0_N']['729']['Veff_ratio'],
      'south_Veff_M10_over_M9_729':d029['D029_poles']['near_p0_S']['729']['Veff_ratio'],
      'min_detJ_729':d029['M10']['min_curved_detJ_27_343_729'][2],
      'canonical_Gmsh_quality_min':{key:value['min'] for key,value in d031['qualities'].items()},
      'D029_PASS':True,'D031_PASS':True,'FEM_attempts':0}
    passport_path=DEST/'P10LY_M10_GEOMETRY_ACCEPTANCE_PASSPORT.json'
    passport_path.write_text(json.dumps(passport,indent=2)+'\n')
    run=(OLD/'P10LM_M9_TWO_TERM.py').read_text()
    run=run.replace('P10LM','P10LY').replace('M9','M10')
    run=once(run,"M10_SHA = 'a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'",
        "M10_SHA = '"+M10_SHA+"'")
    run=once(run,'M10_TET10 = 13166','M10_TET10 = 13996')
    run=once(run,'M10_NODES = 19236','M10_NODES = 20420')
    run=once(run,'M10_PORE_TRI6 = 734','M10_PORE_TRI6 = 814')
    run=once(run,"SOURCE_REVISION = 'P10LY_M10_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'",
        "SOURCE_REVISION = '"+REV+"'")
    # No alteration to the 101 pinned solver files: P10LM revision remains canonical.
    run=once(run,"sha256(HERE/'P10LB_M10_R1_GEOMETRY_ACCEPTANCE_PASSPORT_20261125.json')=='0aaf1fffb247717ef91f75472c79bc8e8fa7f4b4219b3ba8b4512373d93017b7'",
        "sha256(HERE/'P10LY_M10_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='"+sha(passport_path)+"'")
    run=run.replace('P10LY_M10_FIRST_FULL4D_EVIDENCE.zip',
                    'P10LY_M10_FIRST_FULL4D_EVIDENCE.zip')
    run=run.replace("'P10LY_M10_REAL_FULL4D_PASS'", "'P10LY_M10_REAL_FULL4D_PASS'")
    run=once(run,"'mesh_source':'P10LB_D031_D029_REAL_M10_R1_GEOMETRY_GO_20261125'",
        "'mesh_source':'P10LY_M10_D029_D031_FULL_GEOMETRY_GO_20261125'")
    (DEST/'P10LY_M10_FIRST_FULL4D.py').write_text(run)
    (DEST/'P10LY_heartbeat.py').write_text(
        (OLD/'P10LM_heartbeat.py').read_text().replace('P10LM','P10LY'))
    shutil.copy2(OLD/'P10LM_split_audit.py',DEST/'P10LY_split_audit.py')
    for name in ('P10LM_M9_TWO_TERM.py','P10LM_heartbeat.py','P10LM_split_audit.py'):
        (DEST/name).unlink()
    cmd=[]
    for p in sorted(OLD.parent.glob('*.cmd')):
        s=p.read_text().replace('P10LM','P10LY').replace('M9','M10')
        s=s.replace('P10LY_M10_TWO_TERM.py','P10LY_M10_FIRST_FULL4D.py')
        dst=PKG/p.name.replace('P10LM','P10LY').replace('M9','M10')
        dst.write_text(s)
        cmd.append(dst.name)
    for name in ('P10LY_M10_FIRST_FULL4D.py','P10LY_heartbeat.py','P10LY_split_audit.py'):
        ast.parse((DEST/name).read_text(),filename=name)
    assert len(cmd)==2
    assert all('P10LY_M10_FIRST_FULL4D.py' in (PKG/name).read_text() for name in cmd)
    assert "SOURCE_REVISION = '"+REV+"'" in run
    assert f"SOURCE_MANIFEST_SHA = '{sha(DEST/'P10FN_SOURCE_SHA256.json')}'" in run
    assert "P10LY_M10_ONE_SHOT_MARKERS" in run
    assert f"sha256(HERE/'P10LY_M10_GEOMETRY_ACCEPTANCE_PASSPORT.json')=='{sha(passport_path)}'" in run
    (PKG/'README_P10LY_RU.md').write_text(
      '# P10LY — первый физический расчёт на принятой M10\n\n'
      'Схема и исходники точно те же, что в завершённом P10LM M9; меняется только сетка. '
      'R/EDV_VAR, xi0, B6=5мм, 36×25с, 4 потока; две подписанные части explicit (geometry/stress).\n\n'
      '1. Распаковать пакет в **новую** папку.\n'
      '2. `01_P10LY_PREFLIGHT_NO_FEM.cmd`: SHA101 + M10 D029/D031 паспорт, '
      '65-секундный native heartbeat. Нет FEM и маркера.\n'
      '3. После PASS `02_P10LY_ONE_M10_EXTENDED_EXPLICIT_FEM.cmd`: компиляция и один FEM, '
      'запись отдельного маркера **до** физической попытки. Без повторов.\n'
      '4. Время ориентировочно 25–40 мин, hard limit 40 мин, 8 GiB RAM, 2 GiB output.\n'
      '5. Вернуть **один** `P10LY_M10_FIRST_FULL4D_EVIDENCE.zip`. '
      'Запускать старые P10LM/P10LS нельзя.\n')
    archive=ROOT/'P10LY_M10_FIRST_FULL4D_WINDOWS_PREPARED_R2_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(PKG.rglob('*')):
            if p.is_file():z.write(p,arcname=str(p.relative_to(PKG)))
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    qa={'protocol':'P10LY_M10_FULL4D_WINDOWS_PREPARED','status':'SOURCE_QA_PASS_NO_FEM',
      'mesh_sha256':M10_SHA,'source_revision':REV,'source_count':101,
      'source_manifest_sha256':sha(DEST/'P10FN_SOURCE_SHA256.json'),
      'geometry_passport_sha256':sha(passport_path),'archive_sha256':sha(archive),
      'archive_bytes':archive.stat().st_size,'entrypoints':cmd,
      'FEM_attempts':0,'marker_consumed':False}
    (ROOT/'research/P10LY_M10_WINDOWS_PREPARATION_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
