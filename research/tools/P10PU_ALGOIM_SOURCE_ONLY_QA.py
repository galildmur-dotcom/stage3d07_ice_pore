#!/usr/bin/env python3
"""P10PU: verify an actual upstream Algoim single-level-set C++ pilot.

Source-only geometric QA. No FEM, no mesh, no Gmsh, no PowerShell.
Explicit --algoim-root pointing to an independently obtained upstream checkout.
Upstream Algoim is NOT copied into Stage3D07's repository.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
OUTPUT=HERE.parent if HERE.name=='tools' and HERE.parent.name=='research' else HERE
CPP=HERE/'P10PU_ALGOIM_SPHERICAL_SHELL_PILOT.cpp'
REF='da1d81499608e1d499695d255f0233140b8c81e8'


def need(cond,what):
    if not cond:raise RuntimeError('P10PU_STOP '+what)


def parse_log(lines):
    rows={'shell':{},'curved_cap':{},'matched':None}
    for line in lines.splitlines():
        if line.startswith('P10PU_ALGOIM_SHELL '):kind='shell'
        elif line.startswith('P10PU_ALGOIM_CURVED_TET10_CAP '):kind='curved_cap'
        elif line.startswith('P10PU_ALGOIM_P10PT_MATCHED_CAP '):kind='matched'
        else:continue
        fields=dict(token.split('=',1) for token in line.split()[1:])
        q=int(fields.pop('q'))
        v={k:float(x) for k,x in fields.items()}
        need(kind=='matched' or q not in rows[kind],'duplicate q')
        if kind=='matched':rows['matched']={'q':q,**v}
        else:rows[kind][q]=v
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--algoim-root',required=True,type=Path)
    args=ap.parse_args()
    upstream=args.algoim_root.resolve()
    need((upstream/'algoim/quadrature_general.hpp').is_file(),'Algoim header')
    need((upstream/'LICENSE').is_file(),'Algoim license')
    need(CPP.is_file(),'pilot source')
    checked=subprocess.run(['git','-C',str(upstream),'rev-parse','HEAD'],
                  capture_output=True,text=True,timeout=15,check=False)
    need(checked.returncode==0,'upstream git revision')
    revision=checked.stdout.strip()
    need(revision==REF,'upstream revision changed; audit again before using')
    sha=hashlib.sha256(CPP.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='p10pu_algoim_') as td:
        exe=Path(td)/'p10pu_geometry'
        cc=subprocess.run(['g++','-std=c++20','-O2',
              '-I'+str(upstream/'algoim'),str(CPP),'-o',str(exe)],
              capture_output=True,text=True,timeout=60,check=False)
        need(cc.returncode==0,'C++20 compile: '+cc.stderr[:200])
        run=subprocess.run([str(exe)],capture_output=True,text=True,
                           timeout=60,check=False)
        need(run.returncode==0,'C++20 execution: '+run.stderr[:200])
        need('P10PU_ALGOIM_SINGLE_LEVELSET_SHELL_SOURCE_ONLY_PASS' in run.stdout,
             'source-only PASS marker')
    rows=parse_log(run.stdout)
    need(set(rows['shell'])=={2,3,4,5,6,8},'shell q coverage')
    need(set(rows['curved_cap'])=={2,3,4,5,6,8},'curved cap q coverage')
    need(rows['matched'] is not None,'P10PT matched cap')
    need(all(row['positive_weights']==1 for curve in
             (rows['shell'],rows['curved_cap']) for row in curve.values()),
         'positive raw quadrature weights')
    need(all(rows['shell'][q]['relative_error']>
             rows['shell'][q2]['relative_error']
             for q,q2 in zip((2,3,4,5,6),(3,4,5,6,8))),
         'observed shell q convergence')
    need(rows['shell'][8]['relative_error']<1e-8,'shell accuracy')
    need(rows['curved_cap'][8]['relative_error']<1e-13,'curved cap accuracy')
    need(rows['matched']['relative_error']<1e-12,'matched P10PT cap')
    report={
      'protocol':'P10PU_REAL_UPSTREAM_ALGOIM_SINGLE_LEVELSET_SOURCE_ONLY',
      'status':'PASS_SINGLE_LEVELSET_GEOMETRY_ONLY_NOT_MULTIPOLY_NOT_PHYSICAL',
      'upstream_repository':'https://github.com/algoim/algoim',
      'upstream_revision':revision,'pilot_source_sha256':sha,
      'compiler':'g++ -std=c++20 -O2',
      'observed':{'shell':{str(k):v for k,v in rows['shell'].items()},
                  'curved_tet10_cap':{str(k):v for k,v in rows['curved_cap'].items()},
                  'same_geometry_as_P10PT':rows['matched']},
      'limitations':['This is the one-interface quadGen method in a bounding box',
        'Concentric radial shell is the DIFFERENCE of two positive quadratures;',
        'it is NOT one positive quadrature supported on the annular shell.',
        'Simultaneous radial, polar and azimuth boundaries NOT tested.',
        'Multi-polynomial algorithm needs LAPACKE and C++17 compatibility audit.',
        'No FEM, no physical EDV variables, no demonstration of M21 convergence.']}
    (OUTPUT/'P10PU_ALGOIM_SOURCE_ONLY_QA.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('P10PU_REAL_ALGOIM_SOURCE_ONLY_PASS_NO_FEM_NO_GMSH')
    print('P10PU_SHELL_Q8_RELATIVE_ERROR',rows['shell'][8]['relative_error'])
    print('P10PU_CURVED_CAP_Q8_RELATIVE_ERROR',rows['curved_cap'][8]['relative_error'])


if __name__=='__main__':main()
