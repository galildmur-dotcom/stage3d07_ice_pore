#!/usr/bin/env python3
"""Build distinct, one-shot M10 Gmsh-only Windows package from accepted M9."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10ky_package'
NEW=ROOT/'p10lv_package'
M9=ROOT/'p10ls_package_r2/P10LS_WORK/M9.msh'
SRC=ROOT/'p10lu_m10_source'
M9_SHA='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
FIELD='P10LU_M10_M9_MINUS_M8_REAL_SIGNED4D_1200_BINS.csv'
QA='P10LU_M10_SOURCE_ONLY_QA.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('anchor mismatch '+str(s.count(a))+' '+a[:65])
    return s.replace(a,b)

def main():
    if NEW.exists():raise RuntimeError('M10 package already created; refuse overwrite')
    if sha(M9)!=M9_SHA:raise RuntimeError('accepted M9 SHA mismatch')
    manifest=json.loads((SRC/QA).read_text())
    if manifest['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM' or manifest['source_csv_sha256']!=sha(SRC/FIELD):
        raise RuntimeError('M10 source drift')
    oldguard=(OLD/'P10KY_guard.py').read_text()
    pins=ast.literal_eval(oldguard.split('PIN=',1)[1].split('\n\n',1)[0])
    for name,digest in pins.items():
        if sha(OLD/name)!=digest:raise RuntimeError('old package pin drift '+name)
    NEW.mkdir()
    for name in pins:
        if name not in ('P10KY_one_M9_R1_worker.py','p10ky_progress.py'):
            shutil.copy2(OLD/name,NEW/name)
    shutil.copy2(M9,NEW/'M9.msh')
    shutil.copy2(SRC/FIELD,NEW/FIELD)
    shutil.copy2(SRC/QA,NEW/QA)
    worker=(OLD/'P10KY_one_M9_R1_worker.py').read_text().replace('P10KY','P10LV')
    worker=worker.replace('M9_R1','M10_R1').replace('M9 R1','M10 R1')
    worker=once(worker,"M9_FIELD_SHA='ddf7adeaeffffdab480c8bee5b234998236c53a1320aed511d6da20f0c09957f'",
        "M9_FIELD_SHA='ddf7adeaeffffdab480c8bee5b234998236c53a1320aed511d6da20f0c09957f'\n"
        "ACCEPTED_M9_SHA='"+M9_SHA+"'\nM10_FIELD_SHA='"+sha(SRC/FIELD)+"'")
    worker=once(worker,"    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
        "    if hashlib.sha256((HERE/'M9.msh').read_bytes()).hexdigest()!=ACCEPTED_M9_SHA:\n"
        "        raise RuntimeError('accepted M9 mesh SHA mismatch; no M10')\n"
        "    src10=HERE/'"+FIELD+"'\n"
        "    if hashlib.sha256(src10.read_bytes()).hexdigest()!=M10_FIELD_SHA:\n"
        "        raise RuntimeError('M10 physical M9-M8 source SHA mismatch; no mesh')\n"
        "    qa10=json.loads((HERE/'"+QA+"').read_text())\n"
        "    if qa10['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM' or qa10['source_csv_sha256']!=M10_FIELD_SHA:\n"
        "        raise RuntimeError('M10 source-only QA mismatch; no mesh')\n"
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=once(worker,"    if abs(m9.center_kappa.max()-1)>1e-12:",
        "    m10=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
        "              rows(src10),'0.1')\n"
        "    if abs(m10.center_kappa.max()-1)>1e-12:\n"
        "        raise RuntimeError('M10 source normalization mismatch; no mesh')\n"
        "    if abs(m9.center_kappa.max()-1)>1e-12:")
    worker=once(worker,'            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9',
        '            kappa10=polar_blend_m8(m10.kappa(position),dmm,mu)\n'
        '            incremental_m10=(1-.20*kappa10)**(1/3)\n'
        '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10')
    worker=once(worker,"                'M9_polar_plateau_C2':True,",
        "                'M9_polar_plateau_C2':True,\n"
        "                'accepted_M9_sha256':ACCEPTED_M9_SHA,\n"
        "                'M10_new_source_field_sha256':M10_FIELD_SHA,\n"
        "                'M10_additional_nominal_volume_reduction_max':.20,\n"
        "                'M10_polar_plateau_C2':True,")
    worker=worker.replace("'accepted_M9':False", "'accepted_M10':False")
    (NEW/'P10LV_one_M10_R1_worker.py').write_text(worker)
    progress=(OLD/'p10ky_progress.py').read_text().replace('P10KY','P10LV')
    (NEW/'p10lv_progress.py').write_text(progress)
    guard=oldguard.replace('P10KY','P10LV').replace('p10ky_progress','p10lv_progress')
    guard=guard.replace('M9_R1','M10_R1').replace('M9 R1','M10 R1')
    guard=guard.replace('P10LV_R1_ONE_M9_ATTEMPT_CONSUMED.marker','P10LV_R1_ONE_M10_ATTEMPT_CONSUMED.marker')
    guard=guard.replace('P10LV_R1_M9_40949482ac74d80a_ONE_ATTEMPT.marker',
                         'P10LV_R1_M10_a40aca54636a752a_ONE_ATTEMPT.marker')
    guard=guard.replace('P10LV_R1_M9_UNVERIFIED_EVIDENCE.zip','P10LV_R1_M10_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10LV_M9_R1_CANDIDATE_UNVERIFIED.msh','P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh')
    guard=guard.replace('P10LV_one_M9_R1_worker.py','P10LV_one_M10_R1_worker.py')
    # Guard is an exact pinned execution envelope. Rebuild the list after new fields.
    newpins={name:sha(NEW/name) for name in pins if name not in
             ('P10KY_one_M9_R1_worker.py','p10ky_progress.py')}
    for name in ('M9.msh',FIELD,QA,'P10LV_one_M10_R1_worker.py','p10lv_progress.py'):
        newpins[name]=sha(NEW/name)
    a=guard.index('PIN=');b=guard.index('\n\n',a)
    guard=guard[:a]+'PIN='+repr(newpins)+guard[b:]
    guard=guard.replace('accepted_M9=False','accepted_M10=False')
    if "MARK=HERE/'P10LV_R1_ONE_M10_ATTEMPT_CONSUMED.marker'" not in guard:
        raise RuntimeError('marker pin failed')
    if "PROFILE_MARK_NAME='P10LV_R1_M10_a40aca54636a752a_ONE_ATTEMPT.marker'" not in guard:
        raise RuntimeError('profile marker pin failed')
    (NEW/'P10LV_guard.py').write_text(guard)
    for old in OLD.glob('*.cmd'):
        s=old.read_text().replace('P10KY','P10LV').replace('M9_R1','M10_R1').replace('M9 R1','M10 R1')
        s=s.replace('M9 ', 'M10 ')
        (NEW/old.name.replace('P10KY','P10LV').replace('M9_R1','M10_R1')).write_text(s)
    for name in ('P10LV_guard.py','P10LV_one_M10_R1_worker.py','p10lv_progress.py'):
        ast.parse((NEW/name).read_text())
    (NEW/'README_P10LV_RU.md').write_text(
        '# M10 R1: один запуск Gmsh 3D, без FEM\n\n'
        'Источник адаптации — абсолютная пространственно-временная разность реальных M9 и M8 (36×25 с), '
        'не старый M8−M7. Плавное C2-поле и полярные плато сохраняются. '
        'Номинальное локальное уменьшение объёма до 20%.\n\n'
        '1. Распаковать в отдельную папку без смешивания с P10KY.\n'
        '2. Запустить 01_P10LV_M10_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd; ожидаемо 65–90 с, без FEM и без маркера.\n'
        '3. Только после PASS запустить 02_P10LV_ONE_M10_R1_MESH_ONLY.cmd; '
        'ожидаемо 1–5 минут, защитный предел 1200 с. Маркер расходуется до запуска Gmsh.\n'
        '4. Вернуть P10LV_R1_M10_UNVERIFIED_EVIDENCE.zip, без отдельной отправки .msh.\n'
        '5. Не запускать FEM до независимых D029 (фактические эффективные полярные объёмы) '
        'и D031 (канонические качества Gmsh). Нет автоматических повторов.\n')
    archive=ROOT/'P10LV_M10_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(NEW.rglob('*')):
            if p.is_file():z.write(p,arcname='P10LV_M10_R1/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    qa={'protocol':'P10LV_M10_R1_WINDOWS_SOURCE_ONLY','status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM',
      'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
      'accepted_M9_sha256':M9_SHA,'M10_field_sha256':sha(SRC/FIELD),
      'pinned_files':len(newpins),'one_shot':'distinct local and profile markers',
      'mesh_attempts':0,'FEM_attempts':0}
    (ROOT/'research/P10LV_M10_WINDOWS_PREPARED_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
