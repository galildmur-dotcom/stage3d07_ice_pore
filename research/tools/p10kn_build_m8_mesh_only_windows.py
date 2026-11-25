#!/usr/bin/env python3
"""Build distinct P10KN M8 Gmsh-only Windows one-shot, never run native mesh/FEM."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,zipfile
ROOT=Path(__file__).resolve().parent
BASE=ROOT/'p10kg_pkg'
NEW=ROOT/'p10kn_pkg'
ZIP=ROOT/'P10KN_M8_R1_GUARDED_GMSH_MESH_ONLY_WINDOWS_20261125.zip'
P10KM=ROOT/'p10km_result'
M7=ROOT/'p10kh_m7_r2_audit/P10KG_M7_R2_CANDIDATE_UNVERIFIED.msh'
M7_SHA='875c9177de24612d0078f7a792b4b7641a2e604973cb1353500710c87693bb3d'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def rep(text,a,b):
    need(a in text,'missing source token '+repr(a))
    return text.replace(a,b)

def main():
    need(not NEW.exists() and not ZIP.exists(),'existing P10KN delivery must not be overwritten')
    need(sha(M7)==M7_SHA,'P10KI accepted M7 SHA drift')
    qa=json.loads((P10KM/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())
    need(qa['status']=='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM','P10KM design not accepted')
    spec=importlib.util.spec_from_file_location('p10kg_base_guard',BASE/'P10KG_guard.py')
    module=importlib.util.module_from_spec(spec)
    # Guard import requires the baseline progress library on sys.path.
    import sys
    sys.path.insert(0,str(BASE))
    spec.loader.exec_module(module)
    NEW.mkdir()
    # Copy only immutable pinned deps; never copy old guard/worker/markers/output.
    for name in module.PIN:
        if name in ('P10KG_one_M7_R2_worker.py','p10kg_progress.py'):continue
        shutil.copy2(BASE/name,NEW/name)
    shutil.copy2(M7,NEW/'M7.msh')
    for name in ('P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv','P10KM_M8_SOURCE_ONLY_DESIGN_QA.json'):
        shutil.copy2(P10KM/name,NEW/name)
    progress=(BASE/'p10kg_progress.py').read_text(encoding='utf8').replace('P10KG','P10KN')
    (NEW/'p10kn_progress.py').write_text(progress,encoding='utf8')
    worker=(BASE/'P10KG_one_M7_R2_worker.py').read_text(encoding='utf8')
    worker=rep(worker,'P10KG new distinct M7 R2 polar C2 collar candidate after M7 R1 D031 STOP.',
               'P10KN distinct M8 R1 continuation from accepted M7 R2; mesh only.')
    worker=rep(worker,"OUT=HERE/'P10KG_M7_R2_CANDIDATE_UNVERIFIED.msh'",
               "OUT=HERE/'P10KN_M8_R1_CANDIDATE_UNVERIFIED.msh'")
    worker=rep(worker,"ACCEPTED_M6_SHA='d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0'",
               "ACCEPTED_M6_SHA='d581a498f79564e0931dcd147abfe25ca21c608bbb0ed39cb2b2b9281a7ef7b0'\nACCEPTED_M7_SHA='"+M7_SHA+"'")
    worker=rep(worker,"    qa7=json.loads((HERE/'P10KA_M7_C2_SIZE_PREFLIGHT_QA.json').read_text())",
               "    if hashlib.sha256((HERE/'M7.msh').read_bytes()).hexdigest()!=ACCEPTED_M7_SHA:\n"
               "        raise RuntimeError('P10KI M7 R2 accepted mesh SHA drift; no M8')\n"
               "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())\n"
               "    if km['status']!='PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM' or km['source_bins']!=1200:\n"
               "        raise RuntimeError('P10KM source-only field QA drift; no M8')\n"
               "    qa7=json.loads((HERE/'P10KA_M7_C2_SIZE_PREFLIGHT_QA.json').read_text())")
    worker=rep(worker,"    if abs(new.raw_center_max-.5976436567744664)>1e-12:",
               "    m8=Field(rows(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv'),\n"
               "             rows(HERE/'P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv'),'0.1')\n"
               "    if abs(m8.raw_max)<=0 or abs(m8.center_kappa.max()-1)>1e-12:\n"
               "        raise RuntimeError('P10KM 4D priority field normalization drift')\n"
               "    if abs(new.raw_center_max-.5976436567744664)>1e-12:")
    worker=rep(worker,"            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7",
               "            kappa8=m8.kappa(position)\n"
               "            incremental_m8=(1-.20*kappa8)**(1/3)\n"
               "            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8")
    worker=rep(worker,"result={'protocol':'P10KG_M7_R2_DISTINCT_GMSH_3D_MESH_ONLY',",
               "result={'protocol':'P10KN_M8_R1_DISTINCT_GMSH_3D_MESH_ONLY',")
    worker=rep(worker,"'accepted_M6_sha256':ACCEPTED_M6_SHA,",
               "'accepted_M6_sha256':ACCEPTED_M6_SHA,\n"
               "                'accepted_M7_R2_sha256':ACCEPTED_M7_SHA,\n"
               "                'M8_source_field_sha256':hashlib.sha256((HERE/'P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv').read_bytes()).hexdigest(),\n"
               "                'M8_additional_nominal_volume_reduction_max':.20,")
    worker=worker.replace('P10KG_M7_R2_MESH_CREATED_UNVERIFIED_NO_FEM','P10KN_M8_R1_MESH_CREATED_UNVERIFIED_NO_FEM')
    worker=worker.replace('P10KG_WORKER_RESULT.json','P10KN_WORKER_RESULT.json').replace('P10KG_WORKER_ERROR.txt','P10KN_WORKER_ERROR.txt')
    worker=worker.replace('P10KG_WORKER_STOP','P10KN_WORKER_STOP')
    (NEW/'P10KN_one_M8_R1_worker.py').write_text(worker,encoding='utf8')
    pin={name:sha(NEW/name) for name in module.PIN if name not in ('P10KG_one_M7_R2_worker.py','p10kg_progress.py')}
    for name in ('M7.msh','P10KM_M8_LATE_TIME_SIGNED4D_1200_BINS.csv',
                 'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json','P10KN_one_M8_R1_worker.py','p10kn_progress.py'):
        pin[name]=sha(NEW/name)
    guard=(BASE/'P10KG_guard.py').read_text(encoding='utf8')
    start=guard.index('PIN={')
    end=guard.index('\n\n\ndef need(',start)
    guard=guard[:start]+'PIN='+repr(pin)+guard[end:]
    guard=guard.replace('P10KG','P10KN').replace('p10kg_progress','p10kn_progress')
    for a,b in [('P10KN_R2_ONE_M7_ATTEMPT_CONSUMED.marker','P10KN_R1_ONE_M8_ATTEMPT_CONSUMED.marker'),
                ('P10KN_R2_M7_6867fbafefa7efbb_ONE_ATTEMPT.marker','P10KN_R1_M8_875c9177de24612d_ONE_ATTEMPT.marker'),
                ('P10KN_R2_M7_UNVERIFIED_EVIDENCE.zip','P10KN_R1_M8_UNVERIFIED_EVIDENCE.zip'),
                ('P10KN_M7_R2_CANDIDATE_UNVERIFIED.msh','P10KN_M8_R1_CANDIDATE_UNVERIFIED.msh'),
                ('P10KN_one_M7_R2_worker.py','P10KN_one_M8_R1_worker.py'),
                ('P10KN_R2_PREFLIGHT_PASS','P10KN_R1_PREFLIGHT_PASS'),
                ('P10KN_R2_DISTINCT_M7_MESH_ONLY_GUARD','P10KN_R1_DISTINCT_M8_MESH_ONLY_GUARD'),
                ('P10KN M7 R2','P10KN M8 R1'),
                ('one-shot P10KN M7 mesh marker','one-shot P10KN M8 mesh marker'),
                ('accepted_M7=False','accepted_M8=False')]:
        guard=rep(guard,a,b)
    guard=guard.replace('one distinct M7 R2','one distinct M8 R1')
    (NEW/'P10KN_guard.py').write_text(guard,encoding='utf8')
    for old,new in [('01_P10KG_PREFLIGHT_AND_HEARTBEAT_NO_MESH.cmd','01_P10KN_M8_PREFLIGHT_AND_HEARTBEAT_TEST.cmd'),
                    ('02_P10KG_ONE_M7_R2_MESH_ONLY.cmd','02_P10KN_ONE_M8_R1_MESH_ONLY.cmd')]:
        txt=(BASE/old).read_text(encoding='utf8').replace('P10KG','P10KN').replace('M7 R2','M8 R1').replace('M7','M8')
        (NEW/new).write_text(txt,encoding='utf8')
    (NEW/'README_P10KN_RU.md').write_text(
      '# P10KN — новая отдельная M8 R1 Gmsh mesh-only попытка (FEM=0)\n\n'
      'P10KM адаптация: 1200×36 signed4D, сохраняется весь M7 R2 callback, к нему домножается (1−0.2κ8)^(1/3).\n'
      'Именно 20% объёмного размера, а не длины ребра. Два скрипта:\n'
      '1. 01_P10KN_M8_PREFLIGHT_AND_HEARTBEAT_TEST.cmd: SHA source/mesh, Gmsh Python4.15.2, 65с реальный silent-child, 15с прогресс, без маркера/сетки.\n'
      '2. Только после PASS ОДИН раз 02_P10KN_ONE_M8_R1_MESH_ONLY.cmd: отдельный M8 marker в папке и LOCALAPPDATA, Gmsh 3D, wall максимум900с, RAM8GiB, log32MiB, mesh250MiB, FEM0.\n'
      'Отдайте P10KN_R1_M8_UNVERIFIED_EVIDENCE.zip; качество D031/D029 проверяется отдельно, M8 ещё не принята.\n'
      'Никогда не запускать второй раз после потребления M8 marker. Старые M7/M6 markers не трогать.\n',encoding='utf8')
    with zipfile.ZipFile(ZIP,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(NEW.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(NEW).as_posix())
    with zipfile.ZipFile(ZIP) as z:need(z.testzip() is None,'ZIP CRC failed')
    print(json.dumps({'status':'P10KN_M8_WINDOWS_GMSH_ONE_SHOT_PREPARED_NOT_RUN',
          'archive_sha256':sha(ZIP),'source_files':len(list(NEW.iterdir())),
          'M8_mesh_attempts':0,'FEM_attempts':0},indent=2))
if __name__=='__main__':main()
