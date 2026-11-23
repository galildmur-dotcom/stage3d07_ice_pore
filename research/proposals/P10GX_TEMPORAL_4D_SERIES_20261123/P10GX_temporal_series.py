#!/usr/bin/env python3
"""One guarded M0/M1 4D time-series; no automatic mesh adaptation or reruns."""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import zipfile

from P10FN_common import (HERE, PROJECT, MESHES, RUNS, capped_process,
                          load, need, now, require_windows, sha256,
                          validate_source, write_new, zip_evidence)
from P10FN_mesh_qa import audit as mesh_audit
from P10FN_physics import compiler_environment, ensure_binary

M0='926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6'
M1='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
P10GT_ZIP='7bff029865bd69e12b8302a9f65b6159d61f58163300fdee81555954988a6ac3'
PLAN=[(75,12),(60,15),(50,18),(45,20),(36,25),(25,36)]
CSV=('P10DD_SIGNED_R_THETA_PHI_T.csv','P10DD_FULL4D_CLOSURE_AUDIT.csv',
     'P10W_ANALYTIC_ADJOINT.csv','P10W_COMPONENTS.csv','P10W_STEP_COMPONENTS.csv')
REGIME={'mode':'R','law':'EDV_VAR','xi':0,'B6_mm':5,'t_final_s':900,'threads':4}


class Mirror:
    def __init__(self,stream,file):self.stream,self.file=stream,file
    def write(self,s):
        self.stream.write(s)
        self.file.write(s)
        self.file.flush()
    def flush(self):
        self.stream.flush()
        self.file.flush()


def sha(raw):return hashlib.sha256(raw).hexdigest()


def m1_source():
    choices=[HERE/'P10GT_HXT10_EVIDENCE.zip']
    if RUNS.exists():choices += list(RUNS.glob('**/P10GT_HXT10_EVIDENCE.zip'))
    choices += list((PROJECT/'P10GT_TOOLS_R1').glob('**/P10GT_HXT10_EVIDENCE.zip'))
    for p in choices:
        if p.is_file() and sha(p.read_bytes())==P10GT_ZIP:
            with zipfile.ZipFile(p) as z:
                need(z.testzip() is None,'P10GT CRC')
                raw=z.read('P10GT_HXT10.msh')
                need(sha(raw)==M1,'P10GT raw M1 SHA')
                return raw
    raise RuntimeError('P10GX_STOP: original P10GT_HXT10_EVIDENCE.zip absent')


def mesh_paths(*, prepare=False):
    m0=MESHES/'M0.msh'
    need(m0.is_file() and sha256(m0)==M0,'canonical Windows M0.msh unavailable or changed')
    m1=RUNS/'P10GX_IMMUTABLE_M1_STAGING'/'M1.msh'
    if m1.is_file():
        need(sha256(m1)==M1,'staged M1 changed; no overwrite')
    elif prepare:
        raw=m1_source()
        m1.parent.mkdir(parents=True,exist_ok=True)
        with m1.open('xb') as sink:sink.write(raw)
    else:
        need(bool(m1_source()),'M1 evidence missing')
    return {'M0':m0,'M1':m1}


def independent_time_audit(folder,mesh,tets,dt,steps):
    """Step-flexible signed component closure, independent of solver report."""
    def rows(name):
        with (folder/name).open(newline='',encoding='utf-8-sig') as stream:
            return list(csv.DictReader(stream))
    data=rows(CSV[0]);summary=rows(CSV[1]);adj=rows(CSV[2]);comp=rows(CSV[3]);step_comp=rows(CSV[4])
    need(len(data)==1201*steps and len(summary)==steps,'4D row/step coverage')
    component_keys=('mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
                    'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m')
    def close(a,b,label):
        need(abs(a-b)<=2e-9+2e-8*max(abs(a),abs(b)),label)
    totals=[0.]*6
    physical_bounds={}
    for n in range(1,steps+1):
        rr=[r for r in data if int(r['step'])==n]
        need(len(rr)==1201 and len([r for r in rr if r['region']=='VOLUME'])==1200,
             '4D step bin count')
        vol=[r for r in rr if r['region']=='VOLUME']
        robin=[r for r in rr if r['region']=='TOP_ROBIN']
        need(len(robin)==1 and int(robin[0]['top_robin_qp'])>0,'Robin support')
        need(sum(int(r['mechanical_qp']) for r in vol)==tets*27 and
             sum(int(r['thermal_qp']) for r in vol)==tets*64,'4D QP support')
        unique={(int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin'])) for r in vol}
        need(len(unique)==1200,'4D spatial uniqueness')
        for r in rr:
            need(r['mesh']==mesh and r['mode']=='R' and r['functional']=='jpeak'
                 and float(r['time_start_s'])==(n-1)*dt and
                 float(r['time_end_s'])==n*dt,'4D physical time coordinates')
            v=[float(r[k]) for k in component_keys]
            close(sum(v[:3]),float(r['mechanical_total_per_m']),'4D row mech')
            close(sum(v[3:]),float(r['thermal_total_per_m']),'4D row thermal')
            close(sum(v),float(r['total_per_m']),'4D row total')
            if r['region']=='VOLUME':
                key=(int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin']))
                bounds=tuple(r[k] for k in ('r_lower_mm','r_upper_mm','theta_lower_rad',
                                             'theta_upper_rad','phi_lower_rad','phi_upper_rad'))
                if key in physical_bounds:need(physical_bounds[key]==bounds,'4D physical bins drift')
                physical_bounds[key]=bounds
        part=[sum(float(r[k]) for r in rr) for k in component_keys]
        totals=[a+b for a,b in zip(totals,part)]
        sr=[r for r in summary if int(r['step'])==n]
        need(len(sr)==1,'4D independent step report')
        close(sum(part),float(sr[0]['total_per_m']),'4D step closure')
        sc=[r for r in step_comp if int(r['time_step'])==n and r['functional']=='jpeak']
        need(len(sc)==1,'4D P10W step components')
        for k,c in zip(part[:3],('explicit_objective_shape_per_m',
                                 'equilibrium_residual_shape_per_m','internal_history_shape_per_m')):
            close(k,float(sc[0][c]),'4D signed mechanical time')
    peak=next(r for r in comp if r['functional']=='jpeak')
    for k,c in zip(totals[:3],('explicit_objective_shape_per_m',
                               'equilibrium_residual_shape_per_m','internal_history_shape_per_m')):
        close(k,float(peak[c]),'4D global component')
    full=sum(totals)
    close(full,float(peak['total_adjoint_per_m']),'4D global full')
    close(full,float(next(r for r in adj if r['functional']=='jpeak')['total_adjoint_per_m']),
          '4D analytic adjoint')
    need(len(physical_bounds)==1200,'1200 mesh-independent physical bins')
    return {'status':'P10GX_INDEPENDENT_TIME4D_CLOSURE_PASS','rows':len(data),
            'steps':steps,'dt':dt,'horizon_s':steps*dt,
            'jpeak_derivative_per_m':full,'components':dict(zip(component_keys,totals))}


def preflight():
    require_windows()
    validate_source()
    paths=mesh_paths(prepare=False)
    need(len(PLAN)==6 and all(dt*n==900 for dt,n in PLAN),'seven-level time plan')
    for mesh,p in paths.items():
        if p.is_file():need(sha256(p)==(M0 if mesh=='M0' else M1),'mesh pin')
    print('P10GX_PREFLIGHT_PASS_NO_FEM 2 meshes x 6 new dt = 12 native solves',flush=True)


def run_one(mesh,dt,n,path,exe,toolchain,build):
    sha_mesh=M0 if mesh=='M0' else M1
    lock=RUNS/'P10GX_ONE_SHOT_MARKERS'/f'{mesh}_DT{dt}_STEPS{n}_{sha_mesh[:16]}_{build["exe_sha256"][:12]}.json'
    need(not lock.exists(),'one-shot marker already consumed '+str(lock))
    folder=RUNS/f'P10GX_{mesh}_DT{dt}_{now()}'
    folder.mkdir(parents=True,exist_ok=False)
    result=folder/f'P10FN_{mesh}_DT{dt}_R'
    manifest={'protocol':'P10GX_R1_NEW_TEMPORAL_4D','mesh':mesh,'mesh_sha256':sha_mesh,
              'dt':dt,'steps':n,'regime':REGIME,'status':'CONSUMED','FEM_attempts':1,
              'exe_sha256':build['exe_sha256'],'started_utc':now(),
              'source_mesh':str(path),'one_shot':str(lock)}
    write_new(lock,manifest)
    marker=folder/'P10FN_ONE_SHOT_CONSUMED.json'
    write_new(marker,manifest)
    cmd=[str(exe),'--p10fn-authorized','--mesh',str(path),'--out',str(result),
         '--mode','R','--steps',str(n),'--dt',str(dt),'--cutoff-mm','5','--threads','4']
    env=os.environ.copy()
    env['PATH']=str(toolchain.parent)+os.pathsep+env.get('PATH','')
    env['P10FN_ONE_SHOT_MARKER']=str(marker)
    print(f'P10GX_NATIVE_START mesh={mesh} dt={dt} steps={n} marker_consumed',flush=True)
    log=folder/'P10GX_SOLVER_LOG.txt'
    try:
        manifest.update(capped_process(cmd,cwd=HERE,log=log,wall_s=2400,
                                       memory_gib=8,output_dir=folder,
                                       output_gib=2,env=env))
        need(manifest['native_exit_code']==0 and not manifest['stop_reason'],
             'native STOP no auto retry')
        for name in CSV:need((result/name).is_file(),'missing output '+name)
        manifest['independent_4d']=independent_time_audit(result,mesh,
                                          7992 if mesh=='M0' else 9623,dt,n)
        history=result/'forward_history.bin'
        need(history.is_file(),'fresh forward history missing')
        manifest['history_sha256']=sha256(history)
        manifest['status']='P10GX_REAL_TIME4D_PASS'
    except BaseException as exc:
        manifest['status']='P10GX_STOP_NO_RETRY'
        manifest['error']=repr(exc)
    finally:
        meta=folder/'P10GX_MANIFEST.json'
        meta.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        evidence=folder/f'P10GX_{mesh}_DT{dt}_EVIDENCE.zip'
        zip_evidence(evidence,[(meta,meta.name),(log,log.name),
                            *[(result/name,name) for name in CSV]])
    print('P10GX_STEP_RESULT',mesh,dt,manifest['status'],'SEND',evidence,flush=True)
    return manifest['status']=='P10GX_REAL_TIME4D_PASS',evidence


def wrap_campaign(campaign,evidence_files,complete):
    import zipfile
    dest=campaign/('P10GX_12_RUNS_EVIDENCE.zip' if complete else 'P10GX_PARTIAL_STOP_EVIDENCE.zip')
    with zipfile.ZipFile(dest,'x',compression=zipfile.ZIP_STORED) as archive:
        for file in evidence_files:
            archive.write(file,arcname=file.parent.name+'_'+file.name)
    print('P10GX_SEND_ONE_ARCHIVE',dest,flush=True)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--run',action='store_true')
    p.add_argument('--selftest',action='store_true')
    a=p.parse_args()
    if a.selftest:
        need([x*y for x,y in PLAN]==[900]*6,'time plan')
        print('P10GX_SOURCE_SELFTEST_PASS_NO_FEM',PLAN)
        return 0
    preflight()
    if not a.run:return 0
    paths=mesh_paths(prepare=True)
    for mesh,path in paths.items():
        qa=mesh_audit(path)
        need(qa['tet10']==(7992 if mesh=='M0' else 9623),'mesh changed')
    toolchain,build=ensure_binary()
    exe=HERE/'build/stage3d10fn_any_mesh_full4d.exe'
    campaign=RUNS/f'P10GX_CAMPAIGN_{now()}'
    campaign.mkdir(parents=True,exist_ok=False)
    evidence_files=[]
    # Interleave M0/M1 at each dt: each completed pair supports 4D comparison.
    for dt,n in PLAN:
        for mesh in ('M0','M1'):
            ok,evidence=run_one(mesh,dt,n,paths[mesh],exe,toolchain,build)
            evidence_files.append(evidence)
            if not ok:
                wrap_campaign(campaign,evidence_files,complete=False)
                print('P10GX_CAMPAIGN_STOP no more FEM scheduled',flush=True)
                return 2
    wrap_campaign(campaign,evidence_files,complete=True)
    print('P10GX_CAMPAIGN_COMPLETED_12_OF_12_SEND_EVIDENCE',flush=True)
    return 0


if __name__=='__main__':
    if '--selftest' not in sys.argv:
        transcript=(HERE/('P10GX_02_RESULT.txt' if '--run' in sys.argv else
                           'P10GX_01_RESULT.txt')).open('a',encoding='utf-8')
        sys.stdout=Mirror(sys.stdout,transcript)
        sys.stderr=Mirror(sys.stderr,transcript)
    try:sys.exit(main())
    except Exception as e:
        print('P10GX_STOP_NO_AUTO_RETRY',repr(e),flush=True)
        sys.exit(2)
