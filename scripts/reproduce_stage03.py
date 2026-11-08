#!/usr/bin/env python3
"""Build and reproduce Stage3D03 E_CONST/E_VAR mechanical campaign on Tet10 H0/H1/H2."""
import argparse, subprocess, sys, time
from pathlib import Path
root=Path(__file__).resolve().parents[1]

def call(cmd,log=None):
    print('RUN:', ' '.join(map(str,cmd)),flush=True)
    if log:
        log.parent.mkdir(parents=True,exist_ok=True)
        with log.open('w',encoding='utf-8') as stream:
            subprocess.run(list(map(str,cmd)),cwd=root,stdout=stream,stderr=subprocess.STDOUT,check=True)
    else:subprocess.run(list(map(str,cmd)),cwd=root,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--thermal',action='store_true',help='Recompute input thermal VTUs using Stage3D02')
    ap.add_argument('--quick',action='store_true',help='Only H0 mechanics and five material/patch CTest tests')
    ap.add_argument('--skip-vtk',action='store_true',help='Skip optional python-vtk independent readback')
    args=ap.parse_args()
    b=root/'build';r=root/'results';r.mkdir(exist_ok=True)
    call(['cmake','-S',root,'-B',b,'-DCMAKE_BUILD_TYPE=Release'])
    call(['cmake','--build',b,'--config','Release','--parallel','2'])
    call(['ctest','--test-dir',b,'--build-config','Release','--output-on-failure'])
    exe=b/('Release/stage3d03_mechanical.exe' if (b/'Release/stage3d03_mechanical.exe').exists() else 'stage3d03_mechanical')
    th=b/('Release/stage3d02_thermal.exe' if (b/'Release/stage3d02_thermal.exe').exists() else 'stage3d02_thermal')
    if args.thermal:
        for mesh in ('H0',) if args.quick else ('H0','H1','H2'):
            call([th,'--mesh',root/'meshes'/f'{mesh}.msh','--out',r/f'{mesh}_dt300_xi0','--dt','300','--tend','3600','--xi','0'],r/f'{mesh}_thermal_reproduction.log')
    cases=[('H0',3600,'mechanics_H0',3)]
    if not args.quick:
        cases += [('H1',3600,'mechanics_H1',3),('H2',3600,'mechanics_H2',3),
                  ('H0',900,'mechanics_H0_t900',3),('H0',1800,'mechanics_H0_t1800',3),('H0',3600,'mechanics_H0_q4',4)]
    for mesh,t,folder,quad in cases:
        inp=r/f'{mesh}_dt300_xi0'/f'thermal_{t}s.vtu'
        if not inp.is_file():raise FileNotFoundError('Missing thermal input '+str(inp))
        call([exe,'--mesh',root/'meshes'/f'{mesh}.msh','--temp',inp,'--out',r/folder,
              '--model','both','--time',str(t),'--quad',str(quad)],r/f'{folder}.log')
    call([sys.executable,root/'scripts/check_material_reference.py'])
    if not args.skip_vtk and not args.quick:
        try: import vtk
        except ImportError:print('SKIP optional python-vtk validation: install vtk+numpy to run')
        else:call([sys.executable,root/'scripts/check_stage03.py'])
    print('COMPLETE Stage3D03 reproduction')
if __name__=='__main__':main()
