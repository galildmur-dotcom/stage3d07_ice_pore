#!/usr/bin/env python3
"""Stage 3D-05 reproducibility: builds all project targets, runs all CTest and point experiments.
Only Python standard library is needed except for optional plotting.
"""
import pathlib,subprocess,sys,argparse
ap=argparse.ArgumentParser();ap.add_argument('--build',default='build_stage05');ap.add_argument('--no-plot',action='store_true');args=ap.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent
build=(root/args.build).resolve();out=root/'results'/'EDV_material'
def call(*a):
 print('RUN:', ' '.join(str(x) for x in a),flush=True)
 subprocess.run([str(x) for x in a],cwd=root,check=True)
call('cmake','-S',root,'-B',build,'-DCMAKE_BUILD_TYPE=Release')
call('cmake','--build',build,'--config','Release','-j2')
call('ctest','--test-dir',build,'-C','Release','--output-on-failure')
binfile=build/'stage3d05_edv_point'
if sys.platform=='win32':
 binfile=build/'Release'/'stage3d05_edv_point.exe' if (build/'Release'/'stage3d05_edv_point.exe').exists() else build/'stage3d05_edv_point.exe'
call(binfile,'--test','all','--out',out)
call(sys.executable,root/'scripts'/'check_stage05.py','--results',out)
if not args.no_plot:
 try:call(sys.executable,root/'scripts'/'plot_stage05.py','--results',out)
 except subprocess.CalledProcessError as e:print('Plotting OPTIONAL, skipped:',e)
print('Stage 3D-05 VERIFIED; CTest and independent CSV readback completed.')
