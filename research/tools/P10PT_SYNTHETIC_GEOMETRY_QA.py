#!/usr/bin/env python3
"""P10PT: compile/run the bounded geometry-only curved-Tet10 cut pilot.

Does NOT launch FEM, CAD, Gmsh or generate a mesh. No user action required.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parent
OUT_DIR=ROOT.parent if ROOT.name=='tools' and ROOT.parent.name=='research' else ROOT
SOURCE=ROOT/'P10PT_CUT_TET10_GEOMETRY_SOURCE_ONLY.cpp'
if not SOURCE.exists() and ROOT.name=='tools':
    SOURCE=ROOT/'P10PT_CUT_TET10_GEOMETRY_SOURCE_ONLY.cpp'


def need(ok,msg):
    if not ok:
        raise RuntimeError('P10PT_STOP '+msg)


def parse(raw):
    data={'CURVED_TET10_PLANE':{},'AFFINE_TET_POLAR_SECTOR':{}}
    for line in raw.splitlines():
        if not line.startswith('P10PT_MEASURE '):continue
        _,mode,*fields=line.split()
        need(mode in data,'mode')
        row=dict(item.split('=',1) for item in fields)
        d=int(row.pop('depth'))
        need(d not in data[mode],'duplicate depth')
        data[mode][d]={k:float(v) for k,v in row.items()}
    return data


def main():
    need(SOURCE.is_file(),'C++ source absent')
    sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(prefix='p10pt_') as td:
        exe=Path(td)/'p10pt_geometry'
        compilation=subprocess.run(['g++','-std=c++20','-O2','-Wall',
            '-Wextra','-pedantic',str(SOURCE),'-o',str(exe)],
            capture_output=True,text=True,timeout=60,check=False)
        need(compilation.returncode==0,'C++ compile: '+compilation.stderr[:500])
        run=subprocess.run([str(exe)],capture_output=True,text=True,
                            timeout=60,check=False)
        need(run.returncode==0,'C++ synthetic: '+run.stderr[:500])
        need(run.stdout.rstrip().endswith('P10PT_SOURCE_ONLY_SYNTHETIC_GEOMETRY_PASS'),
             'C++ PASS marker')
    data=parse(run.stdout)
    for mode,curves in data.items():
        need(set(curves)=={0,8,12,16,20,24},'incomplete depth curve '+mode)
        for depth,row in curves.items():
            need(all(math.isfinite(x) for x in row.values()),'nonfinite QA')
            need(row['reference']>0 and row['estimate']>=0,'negative volume')
            need(row['relative_error']>=0,'negative error')
        need(curves[24]['relative_error']<curves[0]['relative_error'],
             'no improvement '+mode)
    need(data['CURVED_TET10_PLANE'][24]['relative_error']<5e-4,
         'curved map planar-cut tolerance')
    need(data['AFFINE_TET_POLAR_SECTOR'][24]['relative_error']<2e-5,
         'analytic polar-sector tolerance')
    report={'protocol':'P10PT_PUBLISHED_CUT_CELL_CONCEPT_SYNTHETIC_GEOMETRY_QA',
        'status':'PASS_SYNTHETIC_ONLY_NOT_PRODUCTION_NOT_PHYSICAL',
        'CXX_STD':'C++20','compiler_flags':'-O2 -Wall -Wextra -pedantic',
        'source_sha256':sha,
        'tests':['quadratic Tet10 interpolation of volume-preserving curved map',
         'negative test corrupted Tet10 edge midpoint',
         'conservative positive complementary volume partition',
         'analytic curved-element x-plane cut',
         'analytic octant spherical annular polar/azimuthal sector',
         'adaptive longest-edge refinement 0/8/12/16/20/24'],
        'curves':{mode:{str(depth):row for depth,row in curves.items()}
                  for mode,curves in data.items()},
        'limitations':['geometric-only reference elements, no physical state',
         'no general guaranteed curved-Tet10 intersection enclosure',
         'no claimed high-order asymptotic convergence',
         'no same-mesh re-evaluation of EDV internal variables']}
    (OUT_DIR/'P10PT_SYNTHETIC_GEOMETRY_QA.json').write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10PT_ALL_QA_PASS_CXX_NO_CAD_NO_GMSH_NO_FEM')
    print('P10PT_POLAR_REL_ERR',data['AFFINE_TET_POLAR_SECTOR'][24]['relative_error'])
    print('P10PT_CURVED_PLANE_REL_ERR',data['CURVED_TET10_PLANE'][24]['relative_error'])


if __name__=='__main__':main()
