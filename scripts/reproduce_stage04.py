#!/usr/bin/env python3
"""Reconfigure, build, run all 15 tests, generate ED point CSV and independent check."""
from pathlib import Path
import subprocess, argparse, sys, shutil
p=argparse.ArgumentParser()
p.add_argument('--skip-figures',action='store_true')
p.add_argument('--builddir',default='build')
p.add_argument('--config',default='Release')
a=p.parse_args()
root=Path(__file__).resolve().parent.parent
build=root/a.builddir
subprocess.run(['cmake','-S',str(root),'-B',str(build),'-DCMAKE_BUILD_TYPE='+a.config],check=True)
subprocess.run(['cmake','--build',str(build),'--config',a.config,'-j2'],check=True)
subprocess.run(['ctest','--test-dir',str(build),'-C',a.config,'--output-on-failure'],check=True)
exe='stage3d04_ed_point.exe' if sys.platform.startswith('win') else 'stage3d04_ed_point'
runexes=[build/a.config/exe,build/exe]
found=next((x for x in runexes if x.is_file()),None)
if not found:raise FileNotFoundError('Point solver not found: '+str(runexes))
result=root/'results'/'ED_material';result.mkdir(parents=True,exist_ok=True)
subprocess.run([str(found),'--test','all','--out',str(result)],check=True)
subprocess.run([sys.executable,str(root/'scripts'/'check_stage04.py'),'--results',str(result)],check=True)
if not a.skip_figures:
 try:import matplotlib
 except ImportError:print('Matplotlib not installed: skipping optional figures')
 else:subprocess.run([sys.executable,str(root/'scripts'/'plot_stage04.py'),'--results',str(result)],check=True)
print('Stage 3D-04 reproducibility campaign PASS')
