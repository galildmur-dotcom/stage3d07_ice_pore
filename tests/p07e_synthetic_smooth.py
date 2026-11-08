#!/usr/bin/env python3
"""P07E real curved Tet10, manufactured uniform elastic stress and checkpoint.
The analytical volume is independently recomputed for sharp shells.
Never touches LOCAL_RUNS from the user's production campaign.
"""
import argparse, csv, math, pathlib, struct, subprocess, tempfile, shutil, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p07d_synthetic_stress import mesh_read,signature

def run(opts):
    nodes,tets=mesh_read(opts.mesh)
    root=pathlib.Path(tempfile.mkdtemp(prefix='p07e_checkpoint_'))
    sd=root/'LOCAL_RUNS'/'H0_dt300_q3'; mech=sd/'mechanics'/'E_CONST';th=sd/'thermal'
    mech.mkdir(parents=True);th.mkdir(parents=True)
    (root/'meshes').mkdir();shutil.copyfile(opts.mesh,root/'meshes'/'H0.msh')
    eps=1e-5
    u=[v for x,y,z in nodes for v in (eps*x,0.,0.)]
    with (mech/'restart.bin').open('wb') as f:
        f.write(struct.pack('<QQQQiiIId',0x4943453344303602,len(nodes),len(tets)*27,signature(nodes,tets),3,1,0,0,300.))
        f.write(struct.pack('<'+str(len(u))+'d',*u))
        zero=struct.pack('<12d',*[0.]*12)
        for _ in range(len(tets)*27):f.write(zero)
    with (th/'thermal_300s.vtu').open('w') as f:
        f.write('<VTKFile><UnstructuredGrid><Piece><Points><DataArray format="ascii">\n')
        for x,y,z in nodes:f.write(f'{x:.17g} {y:.17g} {z:.17g}\n')
        f.write('</DataArray></Points><PointData><DataArray Name="dT_K">\n')
        f.write('0 '*len(nodes)+'</DataArray></PointData></Piece></UnstructuredGrid></VTKFile>')
    out=root/'p07e_out'
    cmd=[opts.postprocessor,'--root',str(root),'--out',str(out),'--meshes','H0','--dt','300','--time','300','--law','E','--modulus','CONST','--skip-history-check']
    subprocess.run(cmd,timeout=140,check=True)
    # P07E must preserve the old hard-cut observation results exactly.
    if opts.legacy:
        prior=root/'p07d_ref'
        legacy=[opts.legacy,'--root',str(root),'--out',str(prior),'--meshes','H0',
                '--dt','300','--time','300','--law','E','--modulus','CONST','--skip-history-check']
        subprocess.run(legacy,timeout=140,check=True)
        for filename in ('P07D_STATUS.csv','P07D_SHELLS.csv','P07D_COMPARISON.csv'):
            assert (prior/filename).read_bytes()==(out/filename).read_bytes(),f'P07D parity failed: {filename}'
    with (out/'P07D_STATUS.csv').open() as f:status=list(csv.DictReader(f))
    assert len(status)==1 and status[0]['status']=='PASS',status
    with (out/'P07E_SMOOTH_SHELLS.csv').open() as f:rows=list(csv.DictReader(f))
    with (out/'P07E_VOLUME_AUDIT.csv').open() as f:vol=list(csv.DictReader(f))
    assert len(rows)==144 and len(vol)==144,(len(rows),len(vol))
    E=9.5e9;nu=.35; expected=E*(1-nu)/((1+nu)*(1-2*nu))*eps/1e6
    for r,v in zip(rows,vol):
        assert r['mesh']=='H0' and r['volume_quality'] in {'VOLUME_OK','CAUTION_VOLUME','UNRELIABLE_VOLUME','LOW_SUPPORT'}
        assert r['bandwidth_um'] in {'2','5','10'}
        assert math.isclose(float(r['smoothed_volume_m3']),float(v['qp_smoothed_volume_m3']),rel_tol=1e-12)
        assert float(v['analytic_smoothed_volume_m3'])>0
        if float(r['qp_supported'])>0:
            assert math.isclose(float(r['mean_sigma1_MPa']),expected,rel_tol=1e-9,abs_tol=1e-10),(r,expected)
    # Exact independent sharp volume and analytic sector angular fraction
    z=next(x for x in vol if x['zone_type']=='BAND' and x['inner_um']=='0' and x['outer_um']=='10' and x['region']=='ALL')
    va=4*math.pi/3*((.00101)**3-(.001)**3)
    assert math.isclose(float(z['analytic_sharp_volume_m3']),va,rel_tol=1e-12)
    top=next(x for x in vol if x['zone_type']=='BAND' and x['inner_um']=='0' and x['outer_um']=='10' and x['region']=='TOP25')
    assert math.isclose(float(top['analytic_sharp_volume_m3'])/va,(1-math.cos(math.radians(25)))/2,rel_tol=1e-12)
    print(f'PASS P07E: rows={len(rows)}, uniform σ₁={expected:.12g} MPa, ideal shell volume={va:.12g}, temp root={root}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--postprocessor',required=True);p.add_argument('--mesh',required=True);p.add_argument('--legacy')
    run(p.parse_args())
