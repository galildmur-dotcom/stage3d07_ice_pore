#!/usr/bin/env python3
"""Deterministic synthetic checkpoint + VTU test on REAL curved Gmsh Tet10 H0 mesh.
Does not use or alter user campaign results.
"""
import argparse, csv, math, pathlib, struct, subprocess, tempfile

MASK=(1<<64)-1

def mesh_read(path):
    with open(path, encoding='ascii') as f:
        token_iter=iter(f.read().split())
    nodes=[]; index={}; tets=[]
    it=token_iter
    for tok in it:
        if tok=='$Nodes':
            n=int(next(it))
            for z in range(n):
                idx=int(next(it)); x,y,z=map(float,(next(it),next(it),next(it)))
                index[idx]=len(nodes);nodes.append((x,y,z))
        elif tok=='$Elements':
            n=int(next(it))
            for _ in range(n):
                eid,etype,ntags=int(next(it)),int(next(it)),int(next(it))
                tags=[int(next(it)) for _ in range(ntags)]
                length={11:10,9:6}.get(etype)
                if length is None: raise ValueError(f'unknown element {etype}')
                ids=[index[int(next(it))] for _ in range(length)]
                if etype==11:
                    assert tags[0]==1
                    ids[8],ids[9]=ids[9],ids[8]
                    tets.append(ids)
    if not nodes or not tets: raise RuntimeError('not a real mesh')
    return nodes,tets

def signature(nodes,tets):
    h=14695981039346656037
    for p in nodes:
        for x in p:
            h=((h^struct.unpack('<Q',struct.pack('<d',x))[0])*1099511628211)&MASK
    for t in tets:
        for idx in t: h=((h^idx)*1099511628211)&MASK
    return h

def run(args):
    mesh=pathlib.Path(args.mesh)
    nodes,tets=mesh_read(mesh)
    rootdir=pathlib.Path(tempfile.mkdtemp(prefix='p07d_synthetic_'))
    source=rootdir/'LOCAL_RUNS'/'H0_dt300_q3'
    mech=source/'mechanics'/'E_CONST'; thermal=source/'thermal'
    mech.mkdir(parents=True);thermal.mkdir(parents=True)
    # Affine displacement produces uniform strain e_xx=1e-5, zero temperature variation.
    eps=1.0e-5
    values=[]
    for (x,y,z) in nodes: values.extend((eps*x,0,0))
    q=3; nq=27; ng=nq*len(tets)
    ckpt=mech/'restart.bin'
    with ckpt.open('wb') as f:
        f.write(struct.pack('<QQQQiiIId',0x4943453344303602,len(nodes),ng,signature(nodes,tets),q,1,0,0,300.))
        f.write(struct.pack('<'+str(len(values))+'d',*values))
        zeros=struct.pack('<12d',*(0. for _ in range(12)))
        for _ in range(ng): f.write(zeros)
    with (thermal/'thermal_300s.vtu').open('w') as f:
        f.write('<VTKFile><UnstructuredGrid><Piece><Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">\n')
        for x,y,z in nodes: f.write(f'{x:.17g} {y:.17g} {z:.17g}\n')
        f.write('</DataArray></Points><PointData><DataArray Name="dT_K" type="Float64">\n')
        f.write('0 ' * len(nodes)+'</DataArray></PointData></Piece></UnstructuredGrid></VTKFile>')
    (rootdir/'meshes').mkdir()
    # symlink may be restricted on Windows, copy small mesh.
    import shutil
    shutil.copy2(mesh,rootdir/'meshes'/'H0.msh')
    exe=pathlib.Path(args.postprocessor)
    cmd=[str(exe),'--root',str(rootdir),'--meshes','H0','--dt','300','--quad','3','--time','300','--law','E','--modulus','CONST','--skip-history-check']
    print('Starting synthetic complete-checkpoint recovery, H0 (no FEM solves).',flush=True)
    subprocess.run(cmd,check=True,timeout=140)
    out=rootdir/'LOCAL_RUNS'/'REFINEMENT_CAMPAIGN'/'P07D'
    with (out/'P07D_SHELLS.csv').open() as f: rows=list(csv.DictReader(f))
    with (out/'P07D_STATUS.csv').open() as f: status=list(csv.DictReader(f))
    assert len(status)==1 and status[0]['status']=='PASS',status
    allones=[r for r in rows if r['zone_type']=='CUMULATIVE' and r['outer_um']=='500' and r['region']=='ALL']
    assert len(allones)==1 and allones[0]['status']=='OK',allones
    E=9.5e9;nu=.35
    expected=E*(1-nu)/((1+nu)*(1-2*nu))*eps/1e6
    actual=float(allones[0]['mean_sigma1_MPa'])
    maximum=float(status[0]['QP_max_sigma1_MPa'])
    assert math.isclose(actual,expected,rel_tol=1e-9,abs_tol=1e-10),(actual,expected)
    assert math.isclose(maximum,expected,rel_tol=1e-9,abs_tol=1e-10),(maximum,expected)
    assert float(allones[0]['volume_m3'])>0
    assert float(allones[0]['qp_count'])>0
    # Negative regression: a one-bit corrupt mesh signature MUST reject the checkpoint.
    raw=bytearray(ckpt.read_bytes())
    corrupt=bytearray(raw)
    corrupt[24]^=1  # 4th uint64_t header field is the mesh signature.
    ckpt.write_bytes(corrupt)
    bad=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    assert bad.returncode==3 and 'checkpoint header/model/mesh mismatch' in bad.stderr,(bad.returncode,bad.stderr)
    ckpt.write_bytes(raw)
    # Negative regression: incompatible quadrature is never silently accepted.
    invalid=bytearray(raw)
    struct.pack_into('<i',invalid,32,4) # checkpoint quadrature changed, paths stay identical.
    ckpt.write_bytes(invalid)
    bad=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    assert bad.returncode==3 and 'checkpoint header/model/mesh mismatch' in bad.stderr,(bad.returncode,bad.stderr)
    ckpt.write_bytes(raw)
    print(f'PASS P07D synthetic: exact stress={actual:.10g} MPa, expected={expected:.10g} MPa; '
          f'zone_rows={len(rows)}, invalid checkpoint and quadrature both rejected')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--postprocessor',required=True)
    parser.add_argument('--mesh',required=True)
    run(parser.parse_args())
