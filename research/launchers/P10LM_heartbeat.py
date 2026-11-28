"""Visible 30-second progress with a Windows Job hard process-memory cap."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pathlib import Path
import shutil
import subprocess
import threading
import time
import re
import os

from P10FN_common import WindowsJob, free_ram_windows, private_bytes, need

HEARTBEAT_S = 15



class CpuMeter:
    """Actual kernel+user process CPU seconds via Windows GetProcessTimes.

    Read-only, never stop FEM due to unavailable permissions/telemetry.
    """
    def __init__(self, pid):
        import ctypes
        from ctypes import wintypes
        self.ctypes=ctypes
        self.ft=wintypes.FILETIME
        self.k32=ctypes.WinDLL('kernel32',use_last_error=True)
        self.k32.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.k32.OpenProcess.restype=wintypes.HANDLE
        self.k32.CloseHandle.argtypes=[wintypes.HANDLE]
        self.k32.CloseHandle.restype=wintypes.BOOL
        self.k32.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(self.ft)]*4
        self.k32.GetProcessTimes.restype=wintypes.BOOL
        self.handle=self.k32.OpenProcess(0x1000,False,pid)
        self.status='ready' if self.handle else 'OpenProcess_failed'

    def seconds(self):
        if not self.handle:return None
        t=[self.ft() for _ in range(4)]
        if not self.k32.GetProcessTimes(self.handle,*[self.ctypes.byref(x) for x in t]):
            self.status='GetProcessTimes_failed'
            return None
        raw=lambda f:(int(f.dwHighDateTime)<<32)+int(f.dwLowDateTime)
        return (raw(t[2])+raw(t[3]))/10000000.

    def close(self):
        if self.handle:self.k32.CloseHandle(self.handle);self.handle=None


class NativePhaseTracker:
    """Non-invasive coarse phase observations from solver stdout; not internal timers."""
    def __init__(self):
        self.offset=0
        self.phase='native_starting'
        self.forward_first=None
        self.adjoint_first=None
        self.last_forward_step=0
        self.last_adjoint_step=0

    def update(self, path, elapsed):
        try:
            with Path(path).open('rb') as inp:
                inp.seek(self.offset)
                data=inp.read(262144)
                self.offset=inp.tell()
        except OSError:return
        for row in data.decode('utf-8','replace').splitlines():
            if 'P10K_FORWARD scenario=' in row:
                self.phase='forward'
                if self.forward_first is None:self.forward_first=elapsed
                match=re.search(r'step=(\d+)/(\d+)',row)
                if match:self.last_forward_step=max(self.last_forward_step,int(match.group(1)))
            elif 'P10N_ADJOINT_BACKWARD step=' in row:
                self.phase='adjoint'
                if self.adjoint_first is None:self.adjoint_first=elapsed
                match=re.search(r'step=(\d+)/(\d+)',row)
                if match:self.last_adjoint_step=max(self.last_adjoint_step,int(match.group(1)))


class IndependentPulse:
    """Progress emitted independently of WindowsJob/PSAPI/log/solver stdout.

    Each heartbeat is flushed into a separate audit log;
    the main FEM monitoring loop cannot delay this thread's 15s clock.
    """
    def __init__(self, progress_log, interval_s=15):
        self.path=Path(progress_log)
        self.interval_s=interval_s
        self.started=time.monotonic()
        self.pid='starting'
        self.phase='NATIVE_SETUP'
        self.beats=0
        self.finished=threading.Event()
        self.thread=threading.Thread(target=self._loop,daemon=True,
                                     name='P10LM_Independent_Progress')

    def _loop(self):
        with self.path.open('x',encoding='utf-8') as sink:
            while not self.finished.is_set():
                self.beats+=1
                line=('P10LM_INDEPENDENT_FEM_HEARTBEAT phase='+str(self.phase)+
                      ' elapsed_s='+str(round(time.monotonic()-self.started,1))+
                      ' pid='+str(self.pid)+' native_step=unknown '
                      'progress_unknown watchdog_alive=true')
                sink.write(line+'\n')
                sink.flush()
                print(line,flush=True)
                if self.finished.wait(self.interval_s):break
            sink.write('P10LM_INDEPENDENT_FEM_END elapsed_s='+
                       str(round(time.monotonic()-self.started,1))+\
                       ' beats='+str(self.beats)+'\n')
            sink.flush()

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.finished.set()
        self.thread.join(timeout=5)
        return self.beats


def phase_with_heartbeat(phase, operation, heartbeat_s=HEARTBEAT_S):
    """Show actual alive/unknown progress even when a Python phase is silent."""
    started=time.monotonic()
    print(f'P10LM_{phase}_START elapsed_s=0',flush=True)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task=pool.submit(operation)
        while True:
            try:
                result=task.result(timeout=heartbeat_s)
                print(f'P10LM_{phase}_END elapsed_s={time.monotonic()-started:.1f}',flush=True)
                return result
            except TimeoutError:
                print(f'P10LM_{phase}_HEARTBEAT elapsed_s={time.monotonic()-started:.1f} '
                      'worker_alive=true progress_unknown',flush=True)


def compile_with_heartbeat(build_function):
    print('P10LM_BUILD_START: compiling or verifying native solver', flush=True)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(build_function)
        while True:
            try:
                result = future.result(timeout=HEARTBEAT_S)
                print('P10LM_BUILD_READY elapsed_s='+str(round(time.monotonic()-started)), flush=True)
                return result
            except TimeoutError:
                print('P10LM_BUILD_HEARTBEAT elapsed_s='+str(round(time.monotonic()-started))+
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
    pulse=IndependentPulse(Path(output_dir)/'P10LM_PROGRESS_LOG.txt').start()
    job = None
    meter=None
    tracker=NativePhaseTracker()
    last_cpu=None
    print('P10LM_FEM_START: one-shot M9 900s physical 36x25s',
          'wall_limit_s='+str(wall_s), 'memory_limit_GiB='+str(round(cap/1024**3, 2)), flush=True)
    try:
        job=WindowsJob(cap)
        with Path(log).open('x', encoding='utf-8') as sink:
            proc = subprocess.Popen(command, cwd=cwd, env=env,
                                    stdin=subprocess.DEVNULL,
                                    stdout=sink, stderr=subprocess.STDOUT)
            pulse.pid=proc.pid
            try:meter=CpuMeter(proc.pid)
            except Exception as exc:
                print('P10LM_CPU_TELEMETRY_UNAVAILABLE',repr(exc),flush=True)
                meter=None
            pulse.phase='FEM_FORWARD_AND_ADJOINT'
            job.assign(proc.pid)
            while proc.poll() is None:
                time.sleep(.5)
                if proc.poll() is not None:
                    break
                peak = max(peak, private_bytes(proc.pid))
                elapsed = time.monotonic()-started
                tracker.update(log,elapsed)
                try:last_cpu=meter.seconds() if meter else None
                except Exception as exc:
                    print('P10LM_CPU_SAMPLE_UNAVAILABLE',repr(exc),flush=True)
                    meter=None
                if elapsed >= wall_s:
                    stop = 'WALL_LIMIT'
                elif sum(f.stat().st_size for f in Path(output_dir).rglob('*')
                         if f.is_file()) > output_gib*1024**3:
                    stop = 'OUTPUT_LIMIT'
                if elapsed >= next_beat:
                    sink.flush()
                    print('P10LM_FEM_HEARTBEAT elapsed_s='+str(round(elapsed))+
                          ' pid='+str(proc.pid)+' alive=true step_unknown'+
                          ' peak_private_MiB='+str(round(peak/1024**2))+
                          ' native_phase='+tracker.phase+
                          ' last_forward_step='+str(tracker.last_forward_step)+
                          ' last_adjoint_step='+str(tracker.last_adjoint_step)+
                          ' process_CPU_s='+str(round(last_cpu,2) if last_cpu is not None else 'unknown')+
                          ' equivalent_busy_logical_CPUs='+str(round(last_cpu/elapsed,3) if last_cpu is not None and elapsed>0 else 'unknown')+
                          ' log_tail='+last_log_line(log), flush=True)
                    next_beat = time.monotonic()+HEARTBEAT_S
                if stop:
                    print('P10LM_FEM_STOP_LIMIT', stop, flush=True)
                    proc.terminate()
                    break
            code = proc.wait(timeout=30)
    except BaseException as error:
        stop = stop or 'MONITOR_FAILURE_'+type(error).__name__+':'+str(error)
    finally:
        if meter is not None:
            try:
                final_cpu=meter.seconds()
                if final_cpu is not None:last_cpu=final_cpu
            except Exception as exc:print('P10LM_CPU_FINAL_SAMPLE_UNAVAILABLE',repr(exc),flush=True)
            cpu_meter_status=meter.status
            meter.close()
        else:cpu_meter_status='not_started'
        if job is not None:job.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait()
        beat_count=pulse.stop()
    print('P10LM_FEM_NATIVE_END exit_code='+str(code), 'stop='+stop,
          'elapsed_s='+str(round(time.monotonic()-started)), flush=True)
    final_wall=time.monotonic()-started
    logical_cpus=os.cpu_count() or 1
    cpu_metrics={'process_CPU_seconds':last_cpu,
                 'average_busy_logical_CPUs':last_cpu/final_wall if last_cpu is not None and final_wall>0 else None,
                 'average_host_CPU_percent':100*last_cpu/final_wall/logical_cpus if last_cpu is not None and final_wall>0 else None,
                 'host_logical_CPUs':logical_cpus,'meter_status':cpu_meter_status,
                 'native_observed_phase':tracker.phase,
                 'native_forward_first_seen_s':tracker.forward_first,
                 'native_adjoint_first_seen_s':tracker.adjoint_first,
                 'native_forward_step_max':tracker.last_forward_step,
                 'native_adjoint_step_max':tracker.last_adjoint_step}
    print('P10LM_CPU_TELEMETRY',cpu_metrics,flush=True)
    return {'cpu_telemetry':cpu_metrics,'native_exit_code':code, 'wall_s':final_wall,
            'peak_private_bytes_polled':peak,'job_private_limit_bytes':cap,
            'stop_reason':stop,'independent_progress_heartbeat_count':beat_count,
            'independent_progress_interval_s':15}
