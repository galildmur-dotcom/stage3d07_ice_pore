#!/usr/bin/env python3
"""P10NW: one-shot save of verified in-memory optimized M13 and strict reimport audit."""
import hashlib
import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
from p10nq_native_geometry_correspondence_windows import MESH, SHA, sample
from p10nr_coordinate_topology import classify, boundary_index, match_by_position
from p10nt_topology_graph_audit import refine, verify_elements
from p10nu_canonical_quality import THRESHOLDS

HERE=Path(__file__).resolve().parent
OUTPUT=HERE/'P10NW_M13_OPTIMIZED_CANDIDATE.msh'
RESULT=HERE/'P10NW_M13_SERIALIZED_RESULT.json'
LOCAL_MARKER=HERE/'P10NW_LOCAL_CONSUMED.marker'
C=np.array([0.,0.,.03]);R=.001


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def global_marker():
    localappdata=os.environ.get('LOCALAPPDATA')
    if not localappdata:raise RuntimeError('Windows LOCALAPPDATA unavailable: STOP before mutation')
    folder=Path(localappdata)
    if not folder.is_dir():raise RuntimeError('LOCALAPPDATA directory absent')
    return folder/'P10NW_STAGE3D07_M13_OPTIMIZED_ONESHOT_CONSUMED.marker'


def create_marker(path,detail):
    with os.fdopen(os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:
        f.write(detail+'\n')


def quality(gmsh,snap):
    ids=sorted(snap['tets'])
    out={}
    for k,gate in THRESHOLDS.items():
        t0=time.monotonic()
        q=np.asarray(gmsh.model.mesh.getElementQualities(ids,k),float)
        if len(q)!=len(ids) or not np.all(np.isfinite(q)):
            raise RuntimeError(f'bad Gmsh quality API for {k}')
        out[k]={'minimum':float(q.min()),'median':float(np.median(q)),
                'below_gate_count':int(np.count_nonzero(q<=0 if k=='minDetJac' else q<gate)),
                'pass':bool(np.all(q>0)) if k=='minDetJac' else bool(q.min()>=gate),
                'threshold':gate, 'elapsed_s':time.monotonic()-t0}
        print(f'P10NW_{k} min={out[k]["minimum"]:.12g} PASS={out[k]["pass"]}',flush=True)
    return out


def pore_check(snap):
    ids=snap['by_phys'][8]['node_ids']
    xyz=np.array([snap['nodes'][n] for n in ids])
    return {'pore_nodes':len(ids),
            'max_sphere_radial_error_m':float(np.max(np.abs(np.linalg.norm(xyz-C,axis=1)-R)))}


def compare_quality(a,b):
    out={}
    for key in THRESHOLDS:
        x,y=a[key]['minimum'],b[key]['minimum']
        diff=abs(x-y)/max(abs(x),abs(y),1e-20)
        out[key]={'relative_min_difference':diff,'same_within_1e_8':diff<=1e-8}
    return out


def selftest():
    assert compare_quality({k:{'minimum':v+1} for k,v in THRESHOLDS.items()},
                           {k:{'minimum':v+1} for k,v in THRESHOLDS.items()})['minSJ']['same_within_1e_8']
    assert not compare_quality({k:{'minimum':v+1} for k,v in THRESHOLDS.items()},
                               {k:{'minimum':v+2} for k,v in THRESHOLDS.items()})['minSJ']['same_within_1e_8']
    print('P10NW_SYNTHETIC_SERIALIZATION_GATES_PASS',flush=True)


def main():
    selftest()
    if '--selftest' in sys.argv:return
    if sys.platform!='win32':raise RuntimeError('P10NW_WINDOWS_ONLY_STOP')
    import gmsh
    if gmsh.__version__!='4.15.2':raise RuntimeError('gmsh==4.15.2 required')
    if sha(MESH)!=SHA:raise RuntimeError('pinned source M13 R2 SHA mismatch')
    marker=global_marker()
    if any(p.exists() for p in (OUTPUT,RESULT,LOCAL_MARKER,marker)):
        raise RuntimeError('P10NW one-shot already used or output exists: STOP')
    record={'protocol':'P10NW_M13_OPTIMIZED_SERIALIZATION_ONESHOT',
            'status':'STARTED_NO_WRITE','source_sha256':SHA,
            'optimized_mesh_written':False,'FEM_attempts':0,
            'new_mesh_generation_attempts':0,'optimizer':'HighOrderElastic',
            'one_shot_local_marker':LOCAL_MARKER.name,
            'global_marker_name':marker.name}
    gmsh.initialize()
    consumed=False
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.option.setNumber('Mesh.HighOrderFixBoundaryNodes',1)
        gmsh.option.setNumber('Mesh.HighOrderIterMax',50)
        gmsh.option.setNumber('Mesh.HighOrderPassMax',5)
        gmsh.option.setNumber('Mesh.HighOrderNumLayers',2)
        gmsh.option.setNumber('Mesh.MshFileVersion',2.2)
        gmsh.option.setNumber('Mesh.Binary',0)
        gmsh.open(str(MESH));original=sample(gmsh)
        t0=time.monotonic()
        print('P10NW_IN_MEMORY_OPTIMIZER_START',flush=True)
        gmsh.model.mesh.optimize('HighOrderElastic',force=True)
        record['optimizer_s']=time.monotonic()-t0
        optimized=sample(gmsh)
        record['boundary_tri6_preserved']=bool(classify(original,optimized)['all_boundary_tri6_preserved'])
        record['optimized_quality']=quality(gmsh,optimized)
        record['optimized_pore']=pore_check(optimized)
        if not record['boundary_tri6_preserved'] or not all(v['pass'] for v in record['optimized_quality'].values()):
            raise RuntimeError('P10NW_IN_MEMORY_GATE_STOP_BEFORE_WRITE')
        if record['optimized_pore']['max_sphere_radial_error_m']>1e-9:
            raise RuntimeError('P10NW_PORE_GEOMETRY_STOP_BEFORE_WRITE')
        graph=refine(original,optimized)
        if graph['status']!='UNIQUE_GRAPH_LABEL_BIJECTION':
            raise RuntimeError('P10NW_IN_MEMORY_GRAPH_STOP_BEFORE_WRITE')
        stats=verify_elements(original,optimized,graph['vertex_bijection'])
        if not stats['verified_vertex_topology_preserved']:
            raise RuntimeError('P10NW_IN_MEMORY_TOPOLOGY_STOP_BEFORE_WRITE')
        record['in_memory_tet10_topology_pass']=True
        # A global marker is consumed BEFORE writing; never delete it on STOP.
        create_marker(marker,'P10NW CONSUMED before optimized M13 .msh write')
        consumed=True
        create_marker(LOCAL_MARKER,'P10NW CONSUMED; no repeat even after error')
        print('P10NW_ONESHOT_CONSUMED_WRITE_START',flush=True)
        gmsh.write(str(OUTPUT))
        record['optimized_mesh_written']=True
        record['optimized_mesh_sha256']=sha(OUTPUT)
        record['optimized_mesh_size_bytes']=OUTPUT.stat().st_size
        if not (0<OUTPUT.stat().st_size<=64*1024*1024):
            raise RuntimeError('P10NW_OUTPUT_SIZE_GATE_STOP')
        print('P10NW_WRITTEN_SHA256',record['optimized_mesh_sha256'],flush=True)
        # Re-open the actual bytes, rather than trusting the in-memory mesh.
        gmsh.clear()
        gmsh.open(str(OUTPUT));reloaded=sample(gmsh)
        record['reloaded_quality']=quality(gmsh,reloaded)
        record['quality_min_parity']=compare_quality(record['optimized_quality'],record['reloaded_quality'])
        record['reloaded_boundary_tri6_preserved']=bool(classify(optimized,reloaded)['all_boundary_tri6_preserved'])
        record['reloaded_pore']=pore_check(reloaded)
        check=refine(optimized,reloaded)
        record['reimport_graph_status']=check['status']
        if check['vertex_bijection'] is not None:
            record['reimport_topology']=verify_elements(optimized,reloaded,check['vertex_bijection'])
        else:
            record['reimport_topology']={'verified_vertex_topology_preserved':False}
        record['reload_pass']=bool(
            all(v['pass'] for v in record['reloaded_quality'].values()) and
            all(v['same_within_1e_8'] for v in record['quality_min_parity'].values()) and
            record['reloaded_boundary_tri6_preserved'] and
            record['reimport_topology']['verified_vertex_topology_preserved'] and
            record['reimport_topology']['corner_displacement_max_mm']<=1e-9 and
            record['reimport_topology']['mid_edge_displacement_max_mm']<=1e-9 and
            record['reloaded_pore']['max_sphere_radial_error_m']<=1e-9)
        record['status']='SERIALIZED_M13_REIMPORT_PASS_NO_FEM' if record['reload_pass'] else 'SERIALIZED_M13_REIMPORT_STOP'
    except Exception as exc:
        record['status']='AUDIT_ERROR_AFTER_ONESHOT_CONSUMED' if consumed else 'PREFLIGHT_STOP_NO_WRITE'
        record['error']=repr(exc)
        record['traceback']=traceback.format_exc()[-3500:]
    finally:
        gmsh.finalize()
    with RESULT.open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print('P10NW_DONE',record['status'],flush=True)
    if record['status']!='SERIALIZED_M13_REIMPORT_PASS_NO_FEM':raise RuntimeError('P10NW_STOP: see evidence')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print('P10NW_STOP',repr(exc),flush=True)
        sys.exit(2)
