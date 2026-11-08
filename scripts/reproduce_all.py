#!/usr/bin/env python3
"""Reproduce Stage3D02 from canonical Gmsh H0/H1/H2 meshes. Python 3 stdlib.
No Gmsh needed unless remeshing. Baseline scans, uniform-state tests, GH3 and GH5.
"""
import pathlib, subprocess, sys, math, shutil
root=pathlib.Path(__file__).resolve().parents[1]

def call(a):
    print('+', ' '.join(map(str,a)), flush=True)
    subprocess.run(list(map(str,a)),cwd=root,check=True)

build=root/'build'
call(['cmake','-S',root,'-B',build,'-DCMAKE_BUILD_TYPE=Release'])
call(['cmake','--build',build,'--config','Release','-j','2'])
exe=next((p for p in [build/'stage3d02_thermal',build/'stage3d02_thermal.exe',build/'Release/stage3d02_thermal.exe'] if p.exists()),None)
if exe is None:raise RuntimeError('Could not locate executable')
call(['ctest','--test-dir',build,'-C','Release','--output-on-failure'])
call([exe,'--selftest-1d',root/'results/one_d_validation.csv'])
for tag,dt in [('300',300),('75',75),('37p5',37.5)]:
    call([exe,'--mesh',root/'meshes/SLAB3D_G02.msh','--out',root/'results'/f'SLAB3D_dt{tag}',
          '--dt',dt,'--tend',3600,'--xi',0,'--slab','--check-analytic','--no-vtu'])

for h in ['H0','H1','H2']:
    call([exe,'--mesh',root/'meshes'/f'{h}.msh','--out',root/'results'/f'uniform_{h}','--dt','600','--tend','1200','--check-uniform','--no-vtu'])
base={'H0':[300,150,75,37.5], 'H1':[300,150,75], 'H2':[300,150]}
for h,dts in base.items():
    for dt in dts:
        cmd=[exe,'--mesh',root/'meshes'/f'{h}.msh','--out',root/'results'/f'{h}_dt{str(dt).replace(".","p")}_xi0','--dt',dt,'--tend',3600,'--xi',0]
        if dt!=300:cmd.append('--no-vtu')
        call(cmd)

for h,dt,tag,xi in [
    ('H0',150,'GH3_neg',-math.sqrt(3)),('H0',150,'GH3_pos',math.sqrt(3)),
    ('H0',150,'GH5_n2',-2.856970013872806),('H0',150,'GH5_n1',-1.355626179974266),
    ('H0',150,'GH5_p1',1.355626179974266),('H0',150,'GH5_p2',2.856970013872806),
    ('H2',300,'GH3_neg',-math.sqrt(3)),('H2',300,'GH3_pos',math.sqrt(3))]:
    call([exe,'--mesh',root/'meshes'/f'{h}.msh','--out',root/'results'/f'{h}_dt{int(dt)}_{tag}','--dt',dt,'--tend',3600,'--xi',xi,'--no-vtu'])
call([sys.executable,root/'scripts/check_campaign.py'])
print('Stage3D02 complete: G02-01/G02-02 accepted')
