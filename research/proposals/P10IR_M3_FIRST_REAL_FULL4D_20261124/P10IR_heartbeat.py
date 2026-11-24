"""Visible 30-second progress with a Windows Job hard process-memory cap."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
import shutil
import subprocess
import time

from P10FN_common import WindowsJob, free_ram_windows, private_bytes, need

HEARTBEAT_S = 30


def compile_with_heartbeat(build_function):
    print('P10IR_BUILD_START: compiling or verifying native solver', flush=True)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(build_function)
        while True:
            try:
                result = future.result(timeout=HEARTBEAT_S)
                print('P10IR_BUILD_READY elapsed_s='+str(round(time.monotonic()-started)), flush=True)
                return result
            except TimeoutError:
                print('P10IR_BUILD_HEARTBEAT elapsed_s='+str(round(time.monotonic()-started))+
                      ' source_compile_or_selftest_still_running', flush=True)


def last_log_line(path):
    """Return a compact tail of the solver log; absence of output is normal."""
    try:
        with Path(path).open('rb') as handle:
            size = handle.seek(0, 2)
            handle.seek(max(0, size - 8192))
            data = handle.read()
        rows = [x.strip() for x in data.decode('utf-8', 'replace').splitlines() if x.strip()]
        return rows[-1][-160:] if rows else 'solver_log_has_no_lines_yet'
    except OSError:
        return 'log_temporarily_unavailable'


def run_with_heartbeat(command, *, cwd, log, wall_s, memory_gib, output_dir,
                       output_gib, env):
    need(shutil.disk_usage(Path(output_dir).parent).free >= 4*1024**3,
         'less than 4 GiB free disk; no FEM')
    available = free_ram_windows()
    need(available >= 12*1024**3, 'less than 12 GiB free RAM; no FEM')
    cap = int(min(memory_gib*1024**3, available-8*1024**3))
    need(cap >= 4*1024**3, 'insufficient safe memory headroom; no FEM')
    started = time.monotonic()
    next_beat = started + HEARTBEAT_S
    peak = 0
    code = None
    stop = ''
    proc = None
    job = WindowsJob(cap)
    print('P10IR_FEM_START: one-shot M3 900s physical 36x25s',
          'wall_limit_s='+str(wall_s), 'memory_limit_GiB='+str(round(cap/1024**3, 2)), flush=True)
    try:
        with Path(log).open('x', encoding='utf-8') as sink:
            proc = subprocess.Popen(command, cwd=cwd, env=env,
                                    stdin=subprocess.DEVNULL,
                                    stdout=sink, stderr=subprocess.STDOUT)
            job.assign(proc.pid)
            while proc.poll() is None:
                time.sleep(.5)
                if proc.poll() is not None:
                    break
                peak = max(peak, private_bytes(proc.pid))
                elapsed = time.monotonic()-started
                if elapsed >= wall_s:
                    stop = 'WALL_LIMIT'
                elif sum(f.stat().st_size for f in Path(output_dir).rglob('*')
                         if f.is_file()) > output_gib*1024**3:
                    stop = 'OUTPUT_LIMIT'
                if elapsed >= next_beat:
                    sink.flush()
                    print('P10IR_FEM_HEARTBEAT elapsed_s='+str(round(elapsed))+
                          ' peak_private_MiB='+str(round(peak/1024**2))+
                          ' log_tail='+last_log_line(log), flush=True)
                    next_beat = time.monotonic()+HEARTBEAT_S
                if stop:
                    print('P10IR_FEM_STOP_LIMIT', stop, flush=True)
                    proc.terminate()
                    break
            code = proc.wait(timeout=30)
    except BaseException as error:
        stop = stop or 'MONITOR_FAILURE_'+type(error).__name__+':'+str(error)
    finally:
        job.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
    print('P10IR_FEM_NATIVE_END exit_code='+str(code), 'stop='+stop,
          'elapsed_s='+str(round(time.monotonic()-started)), flush=True)
    return {'native_exit_code':code, 'wall_s':time.monotonic()-started,
            'peak_private_bytes_polled':peak,'job_private_limit_bytes':cap,
            'stop_reason':stop}
