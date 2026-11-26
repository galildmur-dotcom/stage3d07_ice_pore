#!/usr/bin/env python3
"""P10NU: Gmsh 4.15.2 canonical Tet10 quality, before/after in-memory optimizer."""
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from p10nq_native_geometry_correspondence_windows import MESH, SHA, sample
from p10nr_coordinate_topology import classify

OUTPUT = Path(__file__).resolve().parent/'P10NU_M13_CANONICAL_QUALITY_RESULT.json'
C = np.array([0.,0.,.03])
R = .001
THRESHOLDS = {'minSICN': .20, 'minSJ': .40, 'gamma': .15, 'minDetJac': 0.}


def quality_summary(ids, q, snap, metric):
    q=np.asarray(q,dtype=float)
    if len(q)!=len(ids):raise RuntimeError(f'{metric}: wrong API quality length')
    if not np.all(np.isfinite(q)):raise RuntimeError(f'{metric}: nonfinite qualities')
    lower=THRESHOLDS[metric]
    gate=np.all(q>0) if metric=='minDetJac' else np.min(q)>=lower
    worst=np.argsort(q,kind='stable')[:20]
    locations=[]
    for idx in worst:
        eid=int(ids[int(idx)])
        conn=snap['tets'][eid]
        center=np.mean([snap['nodes'][n] for n in conn[:4]],axis=0)
        v=center-C
        dist=np.linalg.norm(v)
        mu=float(v[2]/dist) if dist>0 else None
        locations.append({'element_tag_diagnostic_only':eid,
                          'quality':float(q[idx]),
                          'corner_centroid_mm':list(map(float,center*1000)),
                          'radial_distance_from_pore_wall_mm':float((dist-R)*1000),
                          'mu_z_over_radius':mu,
                          'polar_zone':'north' if mu is not None and mu>=.8 else
                                       'south' if mu is not None and mu<=-.8 else 'nonpolar'})
    return {'count':len(q),'min':float(np.min(q)),
            'p01':float(np.percentile(q,1)),
            'p05':float(np.percentile(q,5)),
            'median':float(np.median(q)),
            'p95':float(np.percentile(q,95)),
            'max':float(np.max(q)),
            'nonpositive_count':int(np.count_nonzero(q<=0)),
            'below_threshold_count':int(np.count_nonzero(q<lower)) if metric!='minDetJac'
                                    else int(np.count_nonzero(q<=0)),
            'threshold':lower,'gate_pass':bool(gate),
            'worst_20':locations}


def native_quality(gmsh, snap, label):
    ids=np.asarray(sorted(snap['tets']),dtype=np.int64)
    print(f'P10NU_{label}_QUALITY_START elements={len(ids)}',flush=True)
    result={}
    for metric in THRESHOLDS:
        t0=time.monotonic()
        q=gmsh.model.mesh.getElementQualities(ids.tolist(),metric)
        result[metric]=quality_summary(ids,q,snap,metric)
        print(f'P10NU_{label}_{metric} min={result[metric]["min"]:.12g} '
              f'gate={result[metric]["gate_pass"]} elapsed={time.monotonic()-t0:.1f}s',flush=True)
    result['all_gates_pass']=all(z['gate_pass'] for z in result.values())
    return result


def selftest():
    # Gate semantics: the minimum must satisfy the pre-registered threshold.
    for name,thr in THRESHOLDS.items():
        q=np.array([thr+.01,thr+.2,thr+.3])
        ok=bool(np.all(q>0)) if name=='minDetJac' else bool(q.min()>=thr)
        assert ok
        q[1]=thr-.01
        bad=bool(np.all(q>0)) if name=='minDetJac' else bool(q.min()>=thr)
        assert not bad
    print('P10NU_SYNTHETIC_GATES_PASS',flush=True)


def main():
    selftest()
    if '--selftest' in sys.argv:return
    import gmsh
    if OUTPUT.exists():raise RuntimeError('P10NU_STOP: output already exists')
    if gmsh.__version__!='4.15.2':raise RuntimeError('Gmsh 4.15.2 required')
    if hashlib.sha256(MESH.read_bytes()).hexdigest()!=SHA:raise RuntimeError('M13 R2 source SHA mismatch')
    report={'protocol':'P10NU_M13_CANONICAL_GMSH_D031_QUALITY',
            'source_sha256':SHA,'status':'STARTED',
            'FEM_attempts':0,'mesh_generation_attempts':0,'mesh_files_written':0,
            'marker_uses':0,'thresholds':THRESHOLDS}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('Mesh.HighOrderFixBoundaryNodes',1)
        gmsh.option.setNumber('Mesh.HighOrderIterMax',50)
        gmsh.option.setNumber('Mesh.HighOrderPassMax',5)
        gmsh.option.setNumber('Mesh.HighOrderNumLayers',2)
        gmsh.open(str(MESH));before=sample(gmsh)
        report['before']=native_quality(gmsh,before,'BEFORE')
        t0=time.monotonic()
        print('P10NU_HIGHORDERELASTIC_IN_MEMORY_START',flush=True)
        gmsh.model.mesh.optimize('HighOrderElastic',force=True)
        report['optimizer_s']=time.monotonic()-t0
        after=sample(gmsh)
        report['boundary_tri6_preserved']=bool(classify(before,after)['all_boundary_tri6_preserved'])
        report['after']=native_quality(gmsh,after,'AFTER')
        report['quality_gate_pass']=bool(report['after']['all_gates_pass'] and
                                         report['boundary_tri6_preserved'])
        report['status']='AUDIT_COMPLETED_NO_R3_NO_FEM'
        report['decision']='QUALITY_GATE_PASS_ONLY_NOT_M13_ACCEPTANCE' if report['quality_gate_pass'] else 'QUALITY_GATE_STOP'
    except Exception as exc:
        report['status']='AUDIT_ERROR'
        report['error']=repr(exc)
        report['traceback']=traceback.format_exc()[-4500:]
    finally:gmsh.finalize()
    with OUTPUT.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2)
        f.write('\n')
    print('P10NU_DONE',report['status'],flush=True)
    if report['status']!='AUDIT_COMPLETED_NO_R3_NO_FEM':raise RuntimeError('P10NU_AUDIT_ERROR: see JSON')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('P10NU_STOP',repr(exc),flush=True)
        sys.exit(2)
