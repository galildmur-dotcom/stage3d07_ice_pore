#!/usr/bin/env python3
"""Independent numerical regression: baseline vs Stage3D06-P, including all EDV QP states.
Usage: python scripts/p06_compare.py BASE_RESULT_DIR OPT_RESULT_DIR [--out comparison.csv]
Inputs are per-law folders containing time_series.csv and restart.bin (same mesh/Q/time).
"""
import argparse,struct,csv,math,pathlib,hashlib
from itertools import zip_longest

H=struct.Struct('<QQQQiiIId')
def state(path):
    with path.open('rb') as f:hdrbytes=f.read(H.size)
    if len(hdrbytes)!=H.size:raise ValueError('Short checkpoint header: '+str(path))
    magic,n,ng,sig,order,step,mode,law,time=H.unpack(hdrbytes)
    if magic!=0x4943453344303602 or step<0:raise ValueError('Invalid checkpoint header')
    if path.stat().st_size!=H.size+(3*n+12*ng)*8:raise ValueError('Invalid checkpoint length')
    return (n,ng,sig,order,step,mode,law,time)

def field_diff(pathA,pathB,offset,n):
    """Chunked field comparison (works for H4 without loading >400MB checkpoints)."""
    # Fast optional numpy backend, stdlib-only fallback below.
    try:
        import numpy as np
        aa=np.memmap(pathA,dtype='<f8',mode='r',offset=offset,shape=(n,))
        bb=np.memmap(pathB,dtype='<f8',mode='r',offset=offset,shape=(n,))
        mx=scale=0.;idx=0
        for start in range(0,n,131072):
            a=np.asarray(aa[start:start+131072]);b=np.asarray(bb[start:start+131072]);
            diff=np.abs(a-b)
            if diff.size:
                candidate=float(np.max(diff));
                if candidate>mx:mx=candidate;idx=start+int(np.argmax(diff))
                scale=max(scale,float(np.max(np.abs(a))),float(np.max(np.abs(b))))
        del aa,bb
        return mx,mx/max(1.e-300,scale),idx,scale
    except ImportError:
        mx=scale=0.;idx=0
        with pathA.open('rb') as f, pathB.open('rb') as g:
            f.seek(offset);g.seek(offset)
            i=0
            while i<n:
                k=min(16384,n-i)
                xa=struct.unpack('<%dd'%k,f.read(8*k));xb=struct.unpack('<%dd'%k,g.read(8*k))
                for z,(a,b) in enumerate(zip(xa,xb)):
                    d=abs(a-b)
                    if d>mx:mx=d;idx=i+z
                    scale=max(scale,abs(a),abs(b))
                i+=k
        return mx,mx/max(1.e-300,scale),idx,scale

def compare(ref,opt):
    pathA=ref/'restart.bin';pathB=opt/'restart.bin'
    hdrA=state(pathA);hdrB=state(pathB)
    if hdrA!=hdrB:raise ValueError(f'Checkpoint headers differ: {hdrA}/{hdrB}')
    n,ng=hdrA[:2]
    u=field_diff(pathA,pathB,H.size,3*n)
    q=field_diff(pathA,pathB,H.size+3*n*8,12*ng)
    rowsA=list(csv.DictReader((ref/'time_series.csv').open()))
    rowsB=list(csv.DictReader((opt/'time_series.csv').open()))
    if len(rowsA)!=len(rowsB):raise ValueError('Time steps differ')
    out=[]
    for a,b in zip(rowsA,rowsB):
        for key in ('time_s','dt_s','Newton'):
            if float(a[key])!=float(b[key]):raise ValueError(f'Mismatch {key} {a[key]}/{b[key]}')
        for key in ('Psi6','PsiOmega','maxS1_MPa'):
            av,bv=float(a[key]),float(b[key]);diff=abs(av-bv);rel=diff/max(abs(av),1.e-100)
            out.append(dict(time_s=a['time_s'],metric=key,baseline=av,optimized=bv,abs_diff=diff,rel_diff=rel,
                            passed=rel<=1.e-6))
    out.extend([
      dict(time_s=hdrA[-1],metric='u_maxnorm',baseline=u[3],optimized=u[3],abs_diff=u[0],rel_diff=u[1],passed=u[1]<1.e-6),
      dict(time_s=hdrA[-1],metric='QP_state_maxnorm',baseline=q[3],optimized=q[3],abs_diff=q[0],rel_diff=q[1],passed=q[1]<1.e-6)
    ])
    # Streaming comparison prevents holding two complete EDV histories in memory.
    import filecmp
    bitwise=filecmp.cmp(pathA,pathB,shallow=False)
    return out,bitwise

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('baseline',type=pathlib.Path);ap.add_argument('optimized',type=pathlib.Path)
    ap.add_argument('--out',type=pathlib.Path)
    args=ap.parse_args();rows,exact=compare(args.baseline,args.optimized)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        with args.out.open('w',newline='') as f:
            wr=csv.DictWriter(f,fieldnames=list(rows[0]));wr.writeheader();wr.writerows(rows)
    print('checkpoint_bitwise_equal=',exact)
    for row in rows: print(row)
    if not all(r['passed'] for r in rows):raise SystemExit('NUMERIC REGRESSION FAILED')
    print('NUMERIC REGRESSION PASS')
