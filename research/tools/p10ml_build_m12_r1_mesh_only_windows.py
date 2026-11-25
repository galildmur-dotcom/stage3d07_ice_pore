#!/usr/bin/env python3
"""P10ML: one-shot guarded M12 R1 Gmsh-only package, true M11−M10 4D C2 field."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10mf_package_final'
NEW=ROOT/'p10ml_package'
SRC=ROOT/'p10mk_m12_source'
M11=ROOT/'p10mf_m11_r2_evidence/P10MF_M11_R2_CANDIDATE_UNVERIFIED.msh'
M11_SHA='b3ad647bf3ac295c87f388782447efd33f880e11e331f497402c6596aca6c726'
FIELD='P10MK_M12_M11_MINUS_M10_REAL_SIGNED4D_1200_BINS.csv'
QA='P10MK_M12_SOURCE_ONLY_QA.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('P10ML replacement anchor mismatch: '+a[:90])
    return s.replace(a,b)

def main():
    if NEW.exists():raise RuntimeError('P10ML output already exists; no overwrite')
    if sha(M11)!=M11_SHA:raise RuntimeError('accepted M11 R2 mesh SHA mismatch')
    qa=json.loads((SRC/QA).read_text())
    if qa['source_csv_sha256']!=sha(SRC/FIELD) or qa['bins']!=1200 or qa['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM':
        raise RuntimeError('M12 source-only QA mismatch')
    guard0=(OLD/'P10MF_guard.py').read_text()
    pins=ast.literal_eval(guard0.split('PIN=',1)[1].split('\n\n',1)[0])
    for name,digest in pins.items():
        if sha(OLD/name)!=digest:raise RuntimeError('P10MF source SHA drift: '+name)
    NEW.mkdir()
    for name in pins:
        if name not in ('P10MF_one_M11_R2_worker.py','p10mf_progress.py'):
            shutil.copy2(OLD/name,NEW/name)
    shutil.copy2(M11,NEW/'M11_R2_ACCEPTED.msh')
    shutil.copy2(SRC/FIELD,NEW/FIELD)
    shutil.copy2(SRC/QA,NEW/QA)
    worker=(OLD/'P10MF_one_M11_R2_worker.py').read_text().replace('P10MF','P10ML')
    worker=once(worker,"OUT=HERE/'P10ML_M11_R2_CANDIDATE_UNVERIFIED.msh'",
                "OUT=HERE/'P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'")
    worker=once(worker,"M11_R1_SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'",
                "M11_R1_SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'\n"
                "ACCEPTED_M11_R2_SHA='"+M11_SHA+"'\nM12_FIELD_SHA='"+sha(SRC/FIELD)+"'")
    worker=once(worker,"    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
      "    if hashlib.sha256((HERE/'M11_R2_ACCEPTED.msh').read_bytes()).hexdigest()!=ACCEPTED_M11_R2_SHA:\n"
      "        raise RuntimeError('accepted M11 R2 physical mesh SHA drift; no M12')\n"
      "    src12=HERE/'"+FIELD+"'\n"
      "    if hashlib.sha256(src12.read_bytes()).hexdigest()!=M12_FIELD_SHA:\n"
      "        raise RuntimeError('M12 real M11-M10 signed 4D field SHA drift')\n"
      "    qa12=json.loads((HERE/'"+QA+"').read_text())\n"
      "    if qa12['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM' or qa12['source_csv_sha256']!=M12_FIELD_SHA:\n"
      "        raise RuntimeError('M12 source-only QA drift')\n"
      "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=once(worker,"    if abs(m11.center_kappa.max()-1)>1e-12:",
       "    m12=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
       "              rows(src12),'0.1')\n"
       "    if abs(m12.center_kappa.max()-1)>1e-12:\n"
       "        raise RuntimeError('M12 source normalization mismatch; no mesh')\n"
       "    if abs(m11.center_kappa.max()-1)>1e-12:")
    worker=once(worker,
       '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor',
       '            kappa12=polar_blend_m8(m12.kappa(position),dmm,mu)\n'
       '            incremental_m12=(1-.20*kappa12)**(1/3)\n'
       '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor*incremental_m12')
    worker=once(worker,"                'M11_polar_plateau_C2':True,",
       "                'M11_polar_plateau_C2':True,\n"
       "                'accepted_M11_R2_sha256':ACCEPTED_M11_R2_SHA,\n"
       "                'M12_new_source_field_sha256':M12_FIELD_SHA,\n"
       "                'M12_additional_nominal_volume_reduction_max':.20,\n"
       "                'M12_polar_plateau_C2':True,")
    worker=worker.replace('P10ML_M11_R2_DISTINCT_GMSH_3D_MESH_ONLY',
                          'P10ML_M12_R1_DISTINCT_GMSH_3D_MESH_ONLY')
    worker=worker.replace("'accepted_M11_R2':False","'accepted_M12_R1':False")
    worker=worker.replace('P10ML_M11_R2_MESH_CREATED_UNVERIFIED_NO_FEM','P10ML_M12_R1_MESH_CREATED_UNVERIFIED_NO_FEM')
    (NEW/'P10ML_one_M12_R1_worker.py').write_text(worker)
    (NEW/'p10ml_progress.py').write_text((OLD/'p10mf_progress.py').read_text().replace('P10MF','P10ML'))
    guard=guard0.replace('P10MF','P10ML').replace('p10mf_progress','p10ml_progress')
    guard=guard.replace("MARK=HERE/'P10ML_R2_ONE_M11_ATTEMPT_CONSUMED.marker'",
                        "MARK=HERE/'P10ML_R1_ONE_M12_ATTEMPT_CONSUMED.marker'")
    guard=guard.replace("PROFILE_MARK_NAME='P10ML_R2_M11_244249fcc62d0b26_ONE_ATTEMPT.marker'",
                        "PROFILE_MARK_NAME='P10ML_R1_M12_b3ad647bf3ac295c_ONE_ATTEMPT.marker'")
    guard=guard.replace('P10ML_R2_M11_UNVERIFIED_EVIDENCE.zip','P10ML_R1_M12_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10ML_M11_R2_CANDIDATE_UNVERIFIED.msh','P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh')
    guard=guard.replace('P10ML_one_M11_R2_worker.py','P10ML_one_M12_R1_worker.py')
    guard=guard.replace('accepted_M11_R2=False','accepted_M12_R1=False')
    guard=guard.replace('P10ML_R2_PREFLIGHT_PASS_NO_GMSH_NO_FEM',
                        'P10ML_R1_PREFLIGHT_PASS_NO_GMSH_NO_FEM')
    guard=guard.replace('P10ML_R2_DISTINCT_M11_LOCAL_C2_MESH_ONLY_GUARD',
                        'P10ML_R1_DISTINCT_M12_C2_MESH_ONLY_GUARD')
    guard=guard.replace('P10ML M11 R2 one Gmsh attempt consumed',
                        'P10ML M12 R1 one Gmsh attempt consumed')
    guard=guard.replace('P10ML M11 R2 one guarded original-CAD',
                        'P10ML M12 R1 one guarded original-CAD')
    newpins={name:sha(NEW/name) for name in pins if name not in ('P10MF_one_M11_R2_worker.py','p10mf_progress.py')}
    for name in ('M11_R2_ACCEPTED.msh',FIELD,QA,'P10ML_one_M12_R1_worker.py','p10ml_progress.py'):
        newpins[name]=sha(NEW/name)
    a=guard.index('PIN=');b=guard.index('\n\n',a)
    guard=guard[:a]+'PIN='+repr(newpins)+guard[b:]
    for check in ("MARK=HERE/'P10ML_R1_ONE_M12_ATTEMPT_CONSUMED.marker'",
                  "PROFILE_MARK_NAME='P10ML_R1_M12_b3ad647bf3ac295c_ONE_ATTEMPT.marker'",
                  "MESH=HERE/'P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'",
                  "EVIDENCE=HERE/'P10ML_R1_M12_UNVERIFIED_EVIDENCE.zip'"):
        if check not in guard:raise RuntimeError('M12 distinct one-shot guard missing: '+check)
    (NEW/'P10ML_guard.py').write_text(guard)
    cmds=[]
    for p in sorted(OLD.glob('*.cmd')):
        s=p.read_text().replace('P10MF','P10ML').replace('M11_R2','M12_R1').replace('M11 R2','M12 R1')
        s=s.replace('P10ML M11 ', 'P10ML M12 ')
        s=s.replace('source SHA20','source SHA45')
        s=s.replace('R2 ','R1 ')
        name=p.name.replace('P10MF','P10ML').replace('M11_R2','M12_R1')
        (NEW/name).write_text(s);cmds.append(name)
    assert len(cmds)==2
    for name in ('P10ML_guard.py','P10ML_one_M12_R1_worker.py','p10ml_progress.py'):
        ast.parse((NEW/name).read_text(),filename=name)
    (NEW/'README_P10ML_RU.md').write_text(
       '# P10ML — M12 R1, одна попытка построения Gmsh, без FEM\n\n'
       'Источник κ: реальное знаковое 4D-поле M11 R2−M10, 43 200 ячеек, '
       'агрегация до 1200 пространственных областей, 40% полного L1 + 60% последних 6 шагов, '
       'полярный приоритет 1.2, C2-сглаживание. Новое номинальное уменьшение объёма '
       'до 20%; все множители M1–M11 и локальная C2-коррекция M11 R2 сохранены.\n\n'
       '1. Распаковать в **новую** папку Windows.\n'
       '2. Запустить `01_P10ML_M12_R1_PREFLIGHT_AND_HEARTBEAT_TEST.cmd` '
       '(65–90 с; SHA и Gmsh-API, без меширования, FEM и маркера).\n'
       '3. После PASS запустить **один раз** `02_P10ML_ONE_M12_R1_MESH_ONLY.cmd` '
       '(ожидаемо 1–5 мин; ограничение 20 мин; без FEM).\n'
       '4. Вернуть **один** `P10ML_R1_M12_UNVERIFIED_EVIDENCE.zip`. '
       'Проверки D029/D031 требуются отдельно до физического расчёта.\n')
    archive=ROOT/'P10ML_M12_R1_GUARDED_MESH_ONLY_WINDOWS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for f in sorted(NEW.iterdir()):
            if f.is_file():z.write(f,arcname='P10ML_M12_R1/'+f.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'protocol':'P10ML_M12_R1_GUARDED_MESH_ONLY_PREPARED',
      'status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM',
      'M11_R2_accepted_sha256':M11_SHA,'M12_field_sha256':sha(SRC/FIELD),
      'pinned_files':len(newpins),'archive_sha256':sha(archive),
      'archive_bytes':archive.stat().st_size,'entrypoints':cmds,
      'mesh_attempts':0,'FEM_attempts':0,'marker_consumed':False}
    (ROOT/'research/P10ML_M12_R1_WINDOWS_PREPARED_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
