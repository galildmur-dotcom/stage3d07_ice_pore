#!/usr/bin/env python3
"""Prepare read-only canonical Gmsh locator of under-threshold M11 Tet10."""
import ast,hashlib,json,shutil,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'p10me_package'
MESH=ROOT/'p10mb_m11_evidence/P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh'
QUAL=ROOT/'upload/P10MD_M11_R1_GMSH_QUALITY_RESULT.json'
SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if DEST.exists():raise RuntimeError('P10ME source package exists; no overwrite')
    q=json.loads(QUAL.read_text())
    if (sha(MESH)!=SHA or q['mesh_sha256']!=SHA or q['Tet10']!=15191 or
        q['quality_gate_pass'] or q['gmsh_version']!='4.15.2'):
        raise RuntimeError('M11 original quality evidence not pinned')
    DEST.mkdir()
    shutil.copy2(MESH,DEST/'P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh')
    shutil.copy2(QUAL,DEST/'P10MD_M11_R1_GMSH_QUALITY_RESULT.json')
    script='''#!/usr/bin/env python3
"""Read-only D031 failing Tet10 locator. Never mesh, smooth, or modify Gmsh geometry."""
from pathlib import Path
import hashlib,json,math,sys

HERE=Path(__file__).resolve().parent
MESH=HERE/'P10MB_M11_R1_CANDIDATE_UNVERIFIED.msh'
QUAL=HERE/'P10MD_M11_R1_GMSH_QUALITY_RESULT.json'
OUT=HERE/'P10ME_M11_R1_BAD_TET10_LOCATIONS.json'
SHA='244249fcc62d0b26877164dae1cc6a6528edd1d1e5973edad4dc79aad7872dab'
THRESH={'minSICN':.20,'minSJ':.40,'gamma':.15,'minDetJac':0.}

def main():
    import gmsh
    import numpy as np
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh 4.15.2 required')
    if not MESH.is_file() or hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:
        raise RuntimeError('exact M11 mesh missing or SHA drift')
    original=json.loads(QUAL.read_text())
    if original['mesh_sha256']!=SHA or original['quality_gate_pass']:
        raise RuntimeError('original D031 evidence missing or changed')
    if OUT.exists():raise RuntimeError('existing diagnostic output, no overwrite')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',0)
        gmsh.open(str(MESH))
        tags,flat=gmsh.model.mesh.getElementsByType(11)
        tags=np.asarray(tags,dtype=np.int64)
        conn=np.asarray(flat,dtype=np.int64).reshape(-1,10)
        if len(tags)!=15191:raise RuntimeError('Tet10 count drift')
        qualities={}
        for name in THRESH:
            arr=np.asarray(gmsh.model.mesh.getElementQualities(tags.tolist(),qualityName=name),dtype=float)
            if len(arr)!=len(tags) or not np.isfinite(arr).all():
                raise RuntimeError('invalid quality array '+name)
            if abs(float(arr.min())-float(original['qualities'][name]['min']))>max(1e-11,abs(float(arr.min()))*1e-9):
                raise RuntimeError('original canonical quality minimum mismatch '+name)
            qualities[name]=arr
        bad=np.zeros(len(tags),dtype=bool)
        per_metric={}
        for name,limit in THRESH.items():
            flagged=qualities[name]<(limit if name!='minDetJac' else 0.)
            if name=='minDetJac':flagged|=(qualities[name]<=0)
            bad|=flagged
            per_metric[name]={'count_below_threshold':int(flagged.sum()),
                'minimum':float(qualities[name].min()),'threshold':limit,
                'worst_element_tag':int(tags[np.argmin(qualities[name])])}
        node_tags,node_xyz,_=gmsh.model.mesh.getNodes()
        node_lookup={int(tag):np.asarray(node_xyz[3*i:3*i+3],dtype=float)
                     for i,tag in enumerate(node_tags)}
        indices=np.where(bad)[0]
        # Also include 20 lowest rows for each metric, even if few are under threshold.
        extra=np.concatenate([np.argsort(v)[:20] for v in qualities.values()])
        relevant=np.unique(np.concatenate((indices,extra)))
        rows=[]
        for i in relevant:
            corners=np.asarray([node_lookup[int(k)] for k in conn[i,:4]])
            centroid=corners.mean(axis=0)
            d=centroid-np.array([0.,0.,.03]);r=float(np.linalg.norm(d))
            mu=float(d[2]/r)
            row={'element_tag':int(tags[i]),'centroid_m':[float(x) for x in centroid],
                'wall_distance_mm':float((r-.001)*1000),
                'mu_cos_theta':mu,'polar_region':'north' if mu>=.8 else 'south' if mu<=-.8 else 'other',
                'below_threshold':bool(bad[i]),
                'quality':{k:float(v[i]) for k,v in qualities.items()}}
            rows.append(row)
        rows.sort(key=lambda a:(not a['below_threshold'],a['quality']['minSICN']))
        data={'protocol':'P10ME_READONLY_M11_BAD_TET10_LOCATOR_V1',
            'status':'MEASURED_NO_MESH_NO_FEM','gmsh_version':gmsh.__version__,
            'mesh_sha256':SHA,'Tet10':len(tags),'failed_element_count_unique':len(indices),
            'counts_by_metric':per_metric,'reported_rows':len(rows),'elements':rows,
            'mesh_generation_attempts':0,'FEM_attempts':0}
        OUT.write_text(json.dumps(data,indent=2)+'\\n')
        print('P10ME_M11_READONLY_DIAGNOSTIC_PASS unique_bad='+str(len(indices))+
              ' reported='+str(len(rows)),flush=True)
        print('P10ME_SEND_ONE_FILE '+OUT.name,flush=True)
    finally:
        gmsh.finalize()

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('P10ME_READONLY_STOP '+repr(error),flush=True)
        sys.exit(2)
'''
    ast.parse(script)
    (DEST/'p10me_readonly_bad_tet10.py').write_text(script)
    cmd='''@echo off
setlocal
if /I not "%~1"=="--visible" (
  start "P10ME M11 READONLY BAD TET10" cmd.exe /K call "%~f0" --visible
  exit /b 0
)
cd /d "%~dp0"
echo P10ME_M11_BAD_TET10_READONLY no Gmsh generation, FEM or marker
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -u p10me_readonly_bad_tet10.py
) else (
  python -u p10me_readonly_bad_tet10.py
)
set "P10ME_RC=%ERRORLEVEL%"
echo P10ME_READONLY_END exit=%P10ME_RC%
exit /b %P10ME_RC%
'''
    (DEST/'01_P10ME_READONLY_BAD_TET10.cmd').write_text(cmd)
    (DEST/'README_P10ME_RU.md').write_text(
      '# P10ME — локализация M11 Tet10 ниже D031 порогов\n\n'
      'Распаковать архив в новую папку и запустить `01_P10ME_READONLY_BAD_TET10.cmd`. '
      'Программа сверяет M11 SHA-256 и старый D031, затем **только читает** '
      'канонические качества Gmsh 4.15.2. Она выдаёт номера и центроиды '
      'проблемных Tet10, расстояние до стенки, принадлежность полярной зоне '
      'и 20 худших элементов для каждого показателя. '
      'Меширование, сглаживание, FEM и потребление маркера отсутствуют. '
      'Вернуть один файл `P10ME_M11_R1_BAD_TET10_LOCATIONS.json`; ожидание 5–30 с.\n')
    archive=ROOT/'P10ME_M11_R1_READONLY_BAD_TET10_WINDOWS_20261125.zip'
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=8) as z:
        for p in sorted(DEST.iterdir()):z.write(p,arcname='P10ME_M11_R1/'+p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    result={'status':'PREPARED_READONLY_NO_GMSH_NO_MESH_NO_FEM','mesh_sha256':SHA,
        'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
        'files':5,'mesh_attempts':0,'FEM_attempts':0}
    (ROOT/'research/P10ME_M11_BAD_TET10_READONLY_QA.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
