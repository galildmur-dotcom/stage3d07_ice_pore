#!/usr/bin/env python3
"""P10MB: guarded M11 Gmsh-only mesh continuation with real M10−M9 C2 field."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10lv_package'
NEW=ROOT/'p10mb_package_r2'
M10=ROOT/'p10lv_m10_evidence/P10LV_M10_R1_CANDIDATE_UNVERIFIED.msh'
SRC=ROOT/'p10ma_m11_source'
M10_SHA='022166c7fb9555a511cf2cd2479ceb949c6b809d05d124832d8d7644c0bebc9c'
FIELD='P10MA_M11_M10_MINUS_M9_REAL_SIGNED4D_1200_BINS.csv'
QA='P10MA_M11_SOURCE_ONLY_QA.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('P10MB anchor mismatch '+str(s.count(a))+' '+a[:70])
    return s.replace(a,b)

def main():
    if NEW.exists():raise RuntimeError('P10MB already created; refusing overwrite')
    if sha(M10)!=M10_SHA:raise RuntimeError('accepted M10 SHA mismatch')
    qa=json.loads((SRC/QA).read_text())
    if qa['source_csv_sha256']!=sha(SRC/FIELD) or qa['bins']!=1200 or qa['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM':
        raise RuntimeError('M11 4D source QA drift')
    guard0=(OLD/'P10LV_guard.py').read_text()
    pin=ast.literal_eval(guard0.split('PIN=',1)[1].split('\n\n',1)[0])
    for name,h in pin.items():
        if sha(OLD/name)!=h:raise RuntimeError('old M10 worker source pin mismatch: '+name)
    NEW.mkdir()
    for name in pin:
        if name not in ('P10LV_one_M10_R1_worker.py','p10lv_progress.py'):
            shutil.copy2(OLD/name,NEW/name)
    shutil.copy2(M10,NEW/'M10.msh')
    shutil.copy2(SRC/FIELD,NEW/FIELD)
    shutil.copy2(SRC/QA,NEW/QA)
    worker=(OLD/'P10LV_one_M10_R1_worker.py').read_text().replace('P10LV','P10MB')
    worker=worker.replace('M10_R1','M11_R1').replace('M10 R1','M11 R1')
    worker=once(worker,"M10_FIELD_SHA='02e8a749aef3576f7b33f4e15aef5811c3f5d209dac1fc77e5c5d3cd4fde061a'",
        "M10_FIELD_SHA='02e8a749aef3576f7b33f4e15aef5811c3f5d209dac1fc77e5c5d3cd4fde061a'\n"
        "ACCEPTED_M10_SHA='"+M10_SHA+"'\nM11_FIELD_SHA='"+sha(SRC/FIELD)+"'")
    worker=once(worker,"    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
        "    if hashlib.sha256((HERE/'M10.msh').read_bytes()).hexdigest()!=ACCEPTED_M10_SHA:\n"
        "        raise RuntimeError('accepted M10 mesh SHA mismatch; no M11')\n"
        "    src11=HERE/'"+FIELD+"'\n"
        "    if hashlib.sha256(src11.read_bytes()).hexdigest()!=M11_FIELD_SHA:\n"
        "        raise RuntimeError('M11 true M10-M9 source SHA mismatch; no mesh')\n"
        "    qa11=json.loads((HERE/'"+QA+"').read_text())\n"
        "    if qa11['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM' or qa11['source_csv_sha256']!=M11_FIELD_SHA:\n"
        "        raise RuntimeError('M11 source-only QA mismatch; no mesh')\n"
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=once(worker,"    if abs(m10.center_kappa.max()-1)>1e-12:",
        "    m11=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
        "              rows(src11),'0.1')\n"
        "    if abs(m11.center_kappa.max()-1)>1e-12:\n"
        "        raise RuntimeError('M11 source normalization mismatch; no mesh')\n"
        "    if abs(m10.center_kappa.max()-1)>1e-12:")
    worker=once(worker,
        '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10',
        '            kappa11=polar_blend_m8(m11.kappa(position),dmm,mu)\n'
        '            incremental_m11=(1-.20*kappa11)**(1/3)\n'
        '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11')
    worker=once(worker,"                'M10_polar_plateau_C2':True,",
        "                'M10_polar_plateau_C2':True,\n"
        "                'accepted_M10_sha256':ACCEPTED_M10_SHA,\n"
        "                'M11_new_source_field_sha256':M11_FIELD_SHA,\n"
        "                'M11_additional_nominal_volume_reduction_max':.20,\n"
        "                'M11_polar_plateau_C2':True,")
    worker=worker.replace("'accepted_M10':False","'accepted_M11':False")
    (NEW/'P10MB_one_M11_R1_worker.py').write_text(worker)
    (NEW/'p10mb_progress.py').write_text((OLD/'p10lv_progress.py').read_text().replace('P10LV','P10MB'))
    guard=guard0.replace('P10LV','P10MB').replace('p10lv_progress','p10mb_progress')
    guard=guard.replace('M10_R1','M11_R1').replace('M10 R1','M11 R1')
    guard=guard.replace('P10MB_R1_ONE_M10_ATTEMPT_CONSUMED.marker','P10MB_R1_ONE_M11_ATTEMPT_CONSUMED.marker')
    guard=guard.replace('P10MB_R1_M10_a40aca54636a752a_ONE_ATTEMPT.marker',
                        'P10MB_R1_M11_022166c7fb9555a5_ONE_ATTEMPT.marker')
    guard=guard.replace('P10MB_R1_M10_UNVERIFIED_EVIDENCE.zip','P10MB_R1_M11_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10MB_M10_R1_CANDIDATE_UNVERIFIED.msh','P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh')
    guard=guard.replace('P10MB_one_M10_R1_worker.py','P10MB_one_M11_R1_worker.py')
    guard=guard.replace('accepted_M10=False','accepted_M11=False')
    newpin={name:sha(NEW/name) for name in pin if name not in ('P10LV_one_M10_R1_worker.py','p10lv_progress.py')}
    for name in ('M10.msh',FIELD,QA,'P10MB_one_M11_R1_worker.py','p10mb_progress.py'):
        newpin[name]=sha(NEW/name)
    a=guard.index('PIN=');b=guard.index('\n\n',a)
    guard=guard[:a]+'PIN='+repr(newpin)+guard[b:]
    assert "MARK=HERE/'P10MB_R1_ONE_M11_ATTEMPT_CONSUMED.marker'" in guard
    assert "PROFILE_MARK_NAME='P10MB_R1_M11_022166c7fb9555a5_ONE_ATTEMPT.marker'" in guard
    assert "MESH=HERE/'P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh'" in guard
    (NEW/'P10MB_guard.py').write_text(guard)
    names=[]
    for p in sorted(OLD.glob('*.cmd')):
        s=p.read_text().replace('P10LV','P10MB').replace('M10_R1','M11_R1').replace('M10 R1','M11 R1')
        s=s.replace('M10 ','M11 ')
        name=p.name.replace('P10LV','P10MB').replace('M10_R1','M11_R1')
        (NEW/name).write_text(s);names.append(name)
    assert len(names)==2
    for name in ('P10MB_guard.py','P10MB_one_M11_R1_worker.py','p10mb_progress.py'):
        ast.parse((NEW/name).read_text(),filename=name)
    (NEW/'README_P10MB_RU.md').write_text(
        '# P10MB M11 — один запуск Gmsh 3D, без физического FEM\n\n'
        'Новая адаптация по реальной M10−M9 4D разности, 1200 корзин, '
        'с плавающим C2-полем, усиленным приоритетом обоих полюсов. '
        'Номинальное дополнительное уменьшение локального объёма до 20%. '
        'Все ранее накопленные множители M1–M10 сохранены.\n\n'
        '1. Распаковать в отдельную папку.\n'
        '2. `01_P10MB_M11_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd`: SHA40, транзитивные GEO, '
        'Gmsh 4.15.2 и 65-секундный watchdog без Gmsh-меширования, FEM и маркера.\n'
        '3. Только после PASS — `02_P10MB_ONE_M11_R1_MESH_ONLY.cmd`: '
        'единственная попытка Gmsh, новый локальный и профильный маркер до запуска. '
        'Ожидаемо 1–5 мин, лимит 20 мин, независимые heartbeat до 15 с.\n'
        '4. Вернуть один архив `P10MB_R1_M11_UNVERIFIED_EVIDENCE.zip`. '
        'Не повторять второй этап и не запускать FEM до D029/D031 приёмки.\n')
    archive=ROOT/'P10MB_M11_R1_GUARDED_MESH_ONLY_WINDOWS_R2_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(NEW.rglob('*')):
            if p.is_file():z.write(p,arcname='P10MB_M11_R1/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    qa={'protocol':'P10MB_M11_R1_WINDOWS_SOURCE_ONLY','status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM',
      'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
      'accepted_M10_sha256':M10_SHA,'M11_field_sha256':sha(SRC/FIELD),
      'pinned_files':len(newpin),'one_shot':'distinct local and profile markers',
      'mesh_attempts':0,'FEM_attempts':0}
    (ROOT/'research/P10MB_M11_WINDOWS_PREPARED_QA.json').write_text(json.dumps(qa,indent=2)+'\n')
    print(json.dumps(qa,indent=2))

if __name__=='__main__':main()
