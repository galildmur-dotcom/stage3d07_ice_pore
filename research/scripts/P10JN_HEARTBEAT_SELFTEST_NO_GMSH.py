#!/usr/bin/env python3
"""Silent-child independent heartbeat regression: compressed 1s time scale, no Gmsh/FEM."""
from __future__ import annotations
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile

from P10JN_guard import monitor


def main():
    print('P10JN_HEARTBEAT_SELFTEST_START silent_child_duration_s=2.5',flush=True)
    with tempfile.TemporaryDirectory(prefix='p10jn_heartbeat_') as folder:
        log=Path(folder)/'silent.log'
        log.touch()
        silent=subprocess.Popen([sys.executable,'-c','import time;time.sleep(2.5)'],
                                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        output=io.StringIO()
        with redirect_stdout(output):
            result=monitor(silent,log,Path(folder)/'not_generated.msh',interval=1.,wall=10.)
        lines=[line for line in output.getvalue().splitlines() if 'P10JN_GMSH_HEARTBEAT' in line]
        assert result['status']=='WORKER_FINISHED' and result['exit_code']==0
        assert len(lines)>=2 and result['heartbeat_count']>=2
        assert all('native_step=unknown' in line and 'alive=1' in line for line in lines)
        assert len(set(lines))==len(lines)
        print('P10JN_HEARTBEAT_SELFTEST_PASS', 'heartbeats='+str(len(lines)),
              'native_child_stdout_lines=0',flush=True)


if __name__=='__main__':main()
