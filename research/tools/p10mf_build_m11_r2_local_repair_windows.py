#!/usr/bin/env python3
"""P10MF: one distinct M11 R2 Gmsh attempt with localized C2 size correction."""
import ast,hashlib,json,math,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OLD=ROOT/'p10mb_package_r2'
NEW=ROOT/'p10mf_package_final'
BAD=ROOT/'upload/P10ME_M11_R1_BAD_TET10_LOCATIONS.json'
M11_R1=ROOT/'p10mb_m11_evidence/P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh'
M11_SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def once(s,a,b):
    if s.count(a)!=1:raise RuntimeError('P10MF anchor mismatch '+str(s.count(a))+' '+a[:65])
    return s.replace(a,b)

def main():
    if NEW.exists():raise RuntimeError('P10MF package already exists; no overwrite')
    if sha(M11_R1)!=M11_SHA:raise RuntimeError('M11 R1 mesh SHA changed')
    bad=json.loads(BAD.read_text())
    failed=[x for x in bad['elements'] if x['below_threshold']]
    if (bad['mesh_sha256']!=M11_SHA or len(failed)!=1 or
        bad['failed_element_count_unique']!=1 or failed[0]['element_tag']!=17197):
        raise RuntimeError('local correction anchor is not uniquely verified')
    point=failed[0]['centroid_m']
    if not math.isclose(failed[0]['wall_distance_mm'],.11800508404669953,rel_tol=1e-9):
        raise RuntimeError('M11 localized defect position drift')
    guard0=(OLD/'P10MB_guard.py').read_text()
    pins=ast.literal_eval(guard0.split('PIN=',1)[1].split('\n\n',1)[0])
    for name,digest in pins.items():
        if sha(OLD/name)!=digest:raise RuntimeError('M11 R1 pinned source drift '+name)
    NEW.mkdir()
    for name in pins:
        if name not in ('P10MB_one_M11_R1_worker.py','p10mb_progress.py'):
            shutil.copy2(OLD/name,NEW/name)
    shutil.copy2(M11_R1,NEW/'M11_R1_REFERENCE.msh')
    shutil.copy2(BAD,NEW/'P10ME_M11_R1_BAD_TET10_LOCATIONS.json')
    worker=(OLD/'P10MB_one_M11_R1_worker.py').read_text().replace('P10MB','P10MF')
    worker=worker.replace('M11_R1','M11_R2').replace('M11 R1','M11 R2')
    anchor="M11_FIELD_SHA='a101bbd5eac302f7dc09d8bc32c991f3adbf00fc598db090d379c8a1a007686c'"
    worker=once(worker,anchor,anchor+"\nM11_R1_SHA='"+M11_SHA+"'\n"
        "BAD_LOCATOR_SHA='"+sha(BAD)+"'\n"
        "REPAIR_CENTER=np.asarray("+repr(point)+",dtype=float)\n"
        "REPAIR_RADIUS_M=.00030\nREPAIR_CORE_M=.00002\nREPAIR_LOG_SIZE=-.045")
    worker=once(worker,"    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())",
        "    if hashlib.sha256((HERE/'M11_R1_REFERENCE.msh').read_bytes()).hexdigest()!=M11_R1_SHA:\n"
        "        raise RuntimeError('M11 R1 accepted diagnostic reference SHA changed')\n"
        "    loc=HERE/'P10ME_M11_R1_BAD_TET10_LOCATIONS.json'\n"
        "    if hashlib.sha256(loc.read_bytes()).hexdigest()!=BAD_LOCATOR_SHA:\n"
        "        raise RuntimeError('P10ME actual bad tet locator SHA changed')\n"
        "    km=json.loads((HERE/'P10KM_M8_SOURCE_ONLY_DESIGN_QA.json').read_text())")
    worker=once(worker,
        '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11',
        '            # Additional compact C2 collar around the unique failing R1 Tet10.\n'
        '            repair_d=float(np.linalg.norm(position-REPAIR_CENTER))\n'
        '            repair_t=(repair_d-REPAIR_CORE_M)/(REPAIR_RADIUS_M-REPAIR_CORE_M)\n'
        '            repair_weight=1.-smoothstep5(max(0.,min(1.,repair_t)))\n'
        '            repair_factor=math.exp(REPAIR_LOG_SIZE*repair_weight)\n'
        '            ratio=old_factor*new_factor*m4_factor*m5_factor*m6_factor*incremental_m7*incremental_m8*incremental_m9*incremental_m10*incremental_m11*repair_factor')
    worker=once(worker,"                'M11_polar_plateau_C2':True,",
        "                'M11_polar_plateau_C2':True,\n"
        "                'M11_R1_defect_tag':17197,\n"
        "                'M11_R1_defect_locator_sha256':BAD_LOCATOR_SHA,\n"
        "                'R2_C2_repair_center_m':REPAIR_CENTER.tolist(),\n"
        "                'R2_C2_repair_core_m':REPAIR_CORE_M,\n"
        "                'R2_C2_repair_support_radius_m':REPAIR_RADIUS_M,\n"
        "                'R2_repair_log_size':REPAIR_LOG_SIZE,")
    worker=worker.replace("'accepted_M11':False","'accepted_M11_R2':False")
    (NEW/'P10MF_one_M11_R2_worker.py').write_text(worker)
    (NEW/'p10mf_progress.py').write_text((OLD/'p10mb_progress.py').read_text().replace('P10MB','P10MF'))
    guard=guard0.replace('P10MB','P10MF').replace('p10mb_progress','p10mf_progress')
    guard=guard.replace('M11_R1','M11_R2').replace('M11 R1','M11 R2')
    guard=guard.replace('P10MF_R1_ONE_M11_ATTEMPT_CONSUMED.marker','P10MF_R2_ONE_M11_ATTEMPT_CONSUMED.marker')
    guard=guard.replace('P10MF_R1_M11_022166c7fb9555a5_ONE_ATTEMPT.marker',
                        'P10MF_R2_M11_244249fcc62d0b26_ONE_ATTEMPT.marker')
    guard=guard.replace('P10MF_R1_M11_UNVERIFIED_EVIDENCE.zip','P10MF_R2_M11_UNVERIFIED_EVIDENCE.zip')
    guard=guard.replace('P10MF_one_M11_R1_worker.py','P10MF_one_M11_R2_worker.py')
    guard=guard.replace('accepted_M11=False','accepted_M11_R2=False')
    guard=guard.replace('P10MF_R1_PREFLIGHT_PASS_NO_GMSH_NO_FEM',
                        'P10MF_R2_PREFLIGHT_PASS_NO_GMSH_NO_FEM')
    guard=guard.replace('P10MF_R1_DISTINCT_M9_MESH_ONLY_GUARD',
                        'P10MF_R2_DISTINCT_M11_LOCAL_C2_MESH_ONLY_GUARD')
    newpins={name:sha(NEW/name) for name in pins if name not in ('P10MB_one_M11_R1_worker.py','p10mb_progress.py')}
    for name in ('M11_R1_REFERENCE.msh','P10ME_M11_R1_BAD_TET10_LOCATIONS.json',
                 'P10MF_one_M11_R2_worker.py','p10mf_progress.py'):
        newpins[name]=sha(NEW/name)
    a=guard.index('PIN=');b=guard.index('\n\n',a)
    guard=guard[:a]+'PIN='+repr(newpins)+guard[b:]
    for value in ("MARK=HERE/'P10MF_R2_ONE_M11_ATTEMPT_CONSUMED.marker'",
        "PROFILE_MARK_NAME='P10MF_R2_M11_244249fcc62d0b26_ONE_ATTEMPT.marker'",
        "MESH=HERE/'P10MF_M11_R2_CANDIDATE_UNVERIFIED.msh'",
        "EVIDENCE=HERE/'P10MF_R2_M11_UNVERIFIED_EVIDENCE.zip'"):
        if value not in guard:raise RuntimeError('distinct R2 guard mismatch '+value)
    (NEW/'P10MF_guard.py').write_text(guard)
    cmds=[]
    for p in sorted(OLD.glob('*.cmd')):
        s=p.read_text().replace('P10MB','P10MF').replace('M11_R1','M11_R2').replace('M11 R1','M11 R2')
        s=s.replace('R1 ','R2 ')
        name=p.name.replace('P10MB','P10MF').replace('M11_R1','M11_R2')
        (NEW/name).write_text(s);cmds.append(name)
    assert len(cmds)==2
    for name in ('P10MF_guard.py','P10MF_one_M11_R2_worker.py','p10mf_progress.py'):
        ast.parse((NEW/name).read_text(),filename=name)
    (NEW/'README_P10MF_RU.md').write_text(
       '# P10MF — отдельная M11 R2 локальная C2-коррекция (без FEM)\n\n'
       'Основание: ровно один R1 Tet10 №17197 с SICN 0.18624 и SJ 0.39175, '
       'расстояние 0.118 mm от стенки, mu 0.659. '
       'Сохраняется вся M1–M11 C2 адаптация; добавляется только гладкий '
       'множитель размера exp(−0.045*w) в шаровом воротнике радиуса 0.30 mm '
       'вокруг центра проблемного элемента с ядром 0.02 mm. '
       'Физический FEM запрещён до повторных D029/D031.\n\n'
       '1. Запустить `01_P10MF_M11_R2_PREFLIGHT_AND_HEARTBEAT_TEST.cmd` '
       '(65–90 с, без Gmsh-генерации и маркера).\n'
       '2. После PASS запустить `02_P10MF_ONE_M11_R2_MESH_ONLY.cmd` '
       '(одна попытка, отдельный маркер, ожидание 1–5 мин, предел 20 мин).\n'
       '3. Прислать один `P10MF_R2_M11_UNVERIFIED_EVIDENCE.zip`. '
       'Никакого автоматического повтора.\n')
    archive=ROOT/'P10MF_M11_R2_LOCAL_C2_REPAIR_MESH_ONLY_WINDOWS_FINAL_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(NEW.iterdir()):
            if p.is_file():z.write(p,arcname='P10MF_M11_R2/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    report={'protocol':'P10MF_M11_R2_DISTINCT_LOCAL_C2_REPAIR','status':'PREPARED_NO_GMSH_NO_MESH_NO_FEM',
        'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
        'old_M11_sha256':M11_SHA,'bad_element_tag':17197,
        'repair_center_m':point,'radius_m':.00030,'log_size':-.045,
        'pinned_files':len(newpins),'FEM_attempts':0,'mesh_attempts':0}
    (ROOT/'research/P10MF_M11_R2_PREPARED_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
