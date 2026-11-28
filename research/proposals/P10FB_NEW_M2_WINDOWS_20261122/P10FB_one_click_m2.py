#!/usr/bin/env python3
"""P10FB: NEW once-only 3D mesh of exact sign-repaired P10EY size field. NO FEM."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE / 'P10EX_PINNED_PARENT'))
import P10EX_one_click_m2 as ex

base = ex.base
REV = 'P10FB_R1_NEW_AUTHORIZED_P10EY_SIGN_REPAIRED_M2_3D_ONLY'
NEW_SHA = '2aec3e2626b3500388954e428d880c702a4bb820116af93924b8d590bf9b26f1'
PARENT_SHA = '84a0570cfc61a4fcd3084e5eed3d5926ad6cce88e2dad81a769d8ee92039ba70'
M1_SHA = ex.M1_SHA
GEO = 'P10EY_M2_C1_JOINT_STRCAT_SIGN_SOURCE_ONLY.geo'
CONFIRM = 'RUN ONE P10FB M2 3D MESH'
FILES = ('P10FB_one_click_m2.py','01_P10FB_SAFE_PREFLIGHT_ONLY.cmd',
         '02_P10FB_ONE_M2_3D_ONLY.cmd','README_P10FB_RU.md',GEO)


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as inp:
        for block in iter(lambda: inp.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def need(ok, why):
    if not ok: raise RuntimeError('P10FB_STOP: '+why)


def contract():
    baseline,old=ex.source_contract()
    new=(HERE/GEO).read_text(encoding='utf-8')
    def expression(g):
        body=g.split('Field[6].F = StrCat(',1)[1].split(');',1)[0]
        return ''.join(re.findall(r'"([^"]*)"',body))
    old_expr,new_expr=expression(old),expression(new)
    need(sha(HERE/GEO)==NEW_SHA and
         old_expr.count('+-0.0031079955054980225')==1 and
         new_expr==old_expr.replace('+-0.0031079955054980225',
                                    '-0.0031079955054980225') and
         new.count('Field[6] = MathEval;')==1 and
         new.count('Background Field=6;')==1 and
         'Mesh.Algorithm3D=10;' in new and
         'Include "sphere_pore_B6_refined.geo";' in new,
         'P10EY must be ONE sign repair of SHA-pinned P10EW; no CAD change')
    return baseline,new


def source_gate():
    # Parent original source integrity is required, but old P10EX is NOT executed.
    inherited=ex.source_gate()
    pin=json.loads((HERE/'P10FB_SOURCE_SHA256.json').read_text(encoding='utf-8'))
    need(pin.get('revision')==REV and pin.get('P10EX_parent_archive_sha256')==PARENT_SHA
         and pin.get('geo_sha256')==NEW_SHA and pin.get('M1_sha256')==M1_SHA
         and pin.get('max_native_3d_attempts')==1 and pin.get('FEM_attempts')==0
         and set(pin.get('files',{}))==set(FILES),'P10FB SHA inventory')
    for name,digest in pin['files'].items():
        need(Path(name).name==name and (HERE/name).is_file() and
             sha(HERE/name)==digest,'P10FB pinned file mismatch '+name)
    contract()
    base.REV=REV
    base.F6_SHA=NEW_SHA
    return inherited


def profile_marker():
    appdata=os.environ.get('LOCALAPPDATA','')
    need(bool(appdata) and Path(appdata).is_dir(),'Windows LOCALAPPDATA unavailable')
    return Path(appdata)/'Stage3D07'/('P10FB_R1_NEW_3D_'+M1_SHA+'.json')


def evidence(run):
    # Reuse the parent's exact evidence generation, including raw mesh when <=32MiB.
    original=ex.evidence(run)
    renamed=run/'P10FB_EVIDENCE.zip'
    need(not renamed.exists(),'P10FB evidence already exists')
    original.rename(renamed)
    with zipfile.ZipFile(renamed,'a',compression=zipfile.ZIP_DEFLATED) as out:
        for name in (GEO,'P10FB_SOURCE_SHA256.json'):
            out.write(HERE/name,'P10FB_SOURCE/'+name)
        note=run/'QA/P10FB_M2_GEOMETRY_D025_PENDING.json'
        if note.is_file(): out.write(note,'QA/'+note.name)
    return renamed


def configure():
    ex.configure()
    base.REV=REV
    base.F6_SHA=NEW_SHA
    base.RUNS=HERE/'P10FB_R1_RUNS'
    base.PROOF=base.RUNS/'P10FB_R1_PREFLIGHT_PASS.json'
    base.LOCAL_MARKER=base.RUNS/'P10FB_R1_ONE_3D_USED.json'
    base.CONFIRM=CONFIRM
    base.global_marker=profile_marker
    base.source_gate=source_gate
    base.geometry_contract=contract
    base.make_evidence=evidence


def annotate(meta,run):
    legacy=run/'QA/P10EA_M1_M2_GEOMETRY_QA.json'
    need(legacy.is_file(),'curved27QP full geometry QA missing')
    j=json.loads(legacy.read_text(encoding='utf-8'))
    need(j.get('status')=='P10EA_M2_GEOMETRY_QA_OK_NO_FEM' and
         j.get('m1_sha256')==M1_SHA and
         j.get('m2_sha256')==meta['m2_mesh_sha256'] and
         not j.get('geometry_issues'),'geometry QA must pass first')
    note={'status':'P10FB_CURVED27QP_GEOMETRY_PASS_D025_PENDING_NO_FEM',
          'm1_sha256':M1_SHA,'m2_sha256':meta['m2_mesh_sha256'],
          'geo_sha256':NEW_SHA,'D025_ratio_north':[.75,.85],
          'D025_ratio_south':[.75,.85],
          'actual_D025':'UNKNOWN_PENDING_INDEPENDENT_FIXED_3D_343_729QP',
          'kappa0_size':'diagnostic','smooth_size_field':'mandatory',
          'phi_uniformity':'not_required','global_count_cap':'not_required',
          'physical_FEM_attempts':0}
    (run/'QA/P10FB_M2_GEOMETRY_D025_PENDING.json').write_text(
        json.dumps(note,indent=2)+'\n',encoding='utf-8')


def run(preflight_only):
    base.RUNS.mkdir(parents=True,exist_ok=True)
    folder=base.RUNS/('P10FB_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    folder.mkdir()
    meta={'revision':REV,'mode':'PREFLIGHT' if preflight_only else 'ONE_3D_MESH',
          'status':'P10FB_STOP_NO_FEM','m1_sha256':M1_SHA,'new_geo_sha256':NEW_SHA,
          'native_parse_attempts':0,'native_parse_passed':[],
          'native_1d_2d_attempts':0,'native_3d_attempts':0,
          'physical_FEM_attempts':0,'wall_limit_s':base.WALL_S,
          'qa_limit_s':base.QA_WALL_S,'private_limit_bytes':base.PRIVATE_MAX,
          'mesh_limit_bytes':base.MESH_MAX,'log_limit_bytes':base.LOG_MAX,
          'started_utc':datetime.now(timezone.utc).isoformat()}
    code=2
    try:
        if not preflight_only: base.fresh_proof()
        generated=base.preflight(folder,meta,prompt=preflight_only)
        if preflight_only:
            base.save_proof(meta,folder)
            meta['status']='P10FB_PREFLIGHT_PASS_NO_M2_NO_FEM'
            code=0
        else:
            print('ONE Gmsh -3, <=900s, private<=8GiB, FEM=0. Never rerun 02.',flush=True)
            need(input('Type exactly '+CONFIRM+': ').strip()==CONFIRM,
                 'manual confirmation absent')
            msh=base.launch_m2(meta,folder,generated['B_EXACT_INLINE_F6'])
            base.quality_gate(meta,folder,Path(meta['m1_path']),msh)
            annotate(meta,folder)
            meta['status']='P10FB_CURVED_GEOMETRY_PASS_D025_PENDING_NO_FEM'
            code=0
    except BaseException as exc:
        meta['stop_reason']=str(exc)
        (folder/'P10FB_STOP_TRACE.txt').write_text(traceback.format_exc(),encoding='utf-8')
        print('P10FB STOP:',exc,flush=True)
    finally:
        meta['finished_utc']=datetime.now(timezone.utc).isoformat()
        (folder/'P10EA_RUN_MANIFEST.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
        (folder/'P10FB_RESULT.txt').write_text('RESULT='+meta['status']+'\nFEM=0\n',encoding='utf-8')
        archive=evidence(folder)
        print('RESULT:',meta['status'],'EVIDENCE:',archive,flush=True)
    return code


def selftest():
    configure()
    source_gate()
    baseline,new=contract()
    need(baseline.endswith('Background Field=2;\n') and
         new.endswith('Mesh.MeshSizeMax=1e22;\n') and
         base.CONFIRM==CONFIRM and base.WALL_S==900 and
         base.PRIVATE_MAX==8*1024**3,'pipeline/limit selftest')
    with tempfile.TemporaryDirectory(prefix='p10fb_marker_') as folder:
        saved=(base.LOCAL_MARKER,base.global_marker)
        try:
            base.LOCAL_MARKER=Path(folder)/'local.json'
            base.global_marker=lambda:Path(folder)/'profile.json'
            base.consume_one_shot(Path(folder),['gmsh.exe','candidate.geo','-3'])
            need(base.LOCAL_MARKER.is_file() and base.global_marker().is_file(),
                 'both markers must be consumed')
            try:
                base.consume_one_shot(Path(folder),['gmsh.exe','candidate.geo','-3'])
            except RuntimeError: pass
            else: need(False,'second invocation must STOP')
        finally: base.LOCAL_MARKER,base.global_marker=saved
    print('P10FB_SOURCE_SELFTEST_OK native=0 FEM=0 markers_double_run_STOP=PASS')


def main():
    p=argparse.ArgumentParser()
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--selftest',action='store_true')
    g.add_argument('--preflight-only',action='store_true')
    g.add_argument('--one-m2',action='store_true')
    args=p.parse_args()
    if args.selftest: selftest(); return 0
    configure()
    return run(args.preflight_only)


if __name__=='__main__':
    try: raise SystemExit(main())
    except (RuntimeError,ValueError,OSError,KeyError,AssertionError) as exc:
        print('P10FB STOP:',exc,file=sys.stderr)
        raise SystemExit(2)
