#!/usr/bin/env python3
"""P10NO guarded subprocess driver with per-method timeout and continuous progress."""
import json,subprocess,sys,time
from pathlib import Path

HERE=Path(__file__).resolve().parent
MAX_SECONDS=300

def main():
    logfile=HERE/'P10NO_GMSH_OPTIMIZATION_LOG.txt'
    if logfile.exists():raise RuntimeError('P10NO_STOP: existing log; no overwrite')
    with logfile.open('x',encoding='utf-8') as log:
        for method in ('HighOrder','HighOrderElastic'):
            print('P10NO_START',method,'watchdog_s',MAX_SECONDS,flush=True)
            argv=[sys.executable,'-u',str(HERE/'P10NO_NATIVE_OPTIMIZER.py'),method]
            start=time.monotonic()
            with subprocess.Popen(argv,cwd=HERE,stdout=log,stderr=subprocess.STDOUT) as child:
                while child.poll() is None:
                    elapsed=time.monotonic()-start
                    print(f'P10NO_RUNNING method={method} elapsed_s={elapsed:.0f}',flush=True)
                    if elapsed>MAX_SECONDS:
                        child.kill();child.wait()
                        timed=HERE/f'P10NO_{method.upper()}_TIMEOUT.json'
                        with timed.open('x',encoding='utf-8') as f:
                            json.dump({'status':'WATCHDOG_TIMEOUT','method':method,'watchdog_seconds':MAX_SECONDS,
                                       'no_optimized_mesh_written':True,'no_FEM':True,'no_marker_uses':True},f,indent=2)
                        f.write('\n')
                        break
                    try:child.wait(timeout=30)
                    except subprocess.TimeoutExpired:pass
            print('P10NO_FINISHED',method,'exit',child.returncode,'elapsed_s',round(time.monotonic()-start,1),flush=True)
    print('P10NO_ALL_DONE return JSON results and log; no meshes written',flush=True)

if __name__=='__main__':
    try:main()
    except Exception as e:print('P10NO_STOP',repr(e),flush=True);sys.exit(2)
