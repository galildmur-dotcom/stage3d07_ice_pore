#!/usr/bin/env python3
"""Native Gmsh one-line 1D probe with exact pinned P10GT Field[7] formula.

The CAD is NOT opened. Exact original Field[7] StrCat expression and global
MeshSizeFactor are copied from SHA-pinned original P10GT geo. No 2D/3D/FEM.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import math
from pathlib import Path
import re
import sys
import time
import traceback

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from p10hk_direct_kappa_callback_benchmark import DirectKappa
import p10hc_continuous_kappa_geo as field

GEO=HERE/'P10GT_HXT10.geo'
GEO_SHA='f1227074616375c28706e1e55cddde370b9a9fca069aab88513b4313c8239f51'
REPORT=HERE/'P10HN_RESULT.json'
ERROR=HERE/'P10HN_ERROR.txt'
GMSH_ROOT=Path(r'C:\gmsh-4.15.2-Windows64')


def official_source():
    if hashlib.sha256(GEO.read_bytes()).hexdigest()!=GEO_SHA:
        raise RuntimeError('P10HN_STOP: original Field7 source SHA mismatch')
    txt=GEO.read_text(encoding='utf-8')
    m=re.search(r'Field\[7\] = MathEval;\s*Field\[7\]\.F = StrCat\((.*?)\);\s*Background Field = 7;',txt,re.S)
    if not m:raise RuntimeError('P10HN_STOP: source Field7 structure unexpected')
    parts=json.loads('['+m.group(1)+']')
    expression=''.join(parts)
    factor_match=re.search(r'^Mesh\.MeshSizeFactor\s*=\s*([0-9.eE+-]+);',txt,re.M)
    if not factor_match:raise RuntimeError('P10HN_STOP: source factor missing')
    factor=float(factor_match.group(1))
    # Field-only source, no original CAD Include or mesh generation commands.
    fieldgeo='Field[7]=MathEval;\nField[7].F=StrCat(\n'+m.group(1)+'\n);\nBackground Field=7;\n'
    fieldgeo+=f'Mesh.MeshSizeFactor={factor:.17g};\n'
    fieldgeo+='Mesh.MeshSizeFromPoints=0;\nMesh.MeshSizeFromCurvature=0;\nMesh.MeshSizeExtendFromBoundary=0;\n'
    (HERE/'P10HN_FIELD7_ONLY.geo').write_text(fieldgeo,encoding='utf-8')
    return expression,factor


def math_eval(expression,x,y,z):
    # Original checked fixed SHA expression. Disable builtins entirely.
    code=compile(expression.replace('^','**'),'<frozen_Field7>','eval')
    return float(eval(code,{'__builtins__':{},'min':min,'max':max,'sqrt':math.sqrt},
                      {'x':float(x),'y':float(y),'z':float(z)}))


def import_gmsh():
    try:mod=importlib.import_module('gmsh')
    except ImportError:
        loc=GMSH_ROOT/'lib'
        if not (loc/'gmsh.py').is_file():
            raise RuntimeError('P10HN_STOP: no gmsh Python API (run P10HL R2 local installer first)')
        sys.path.insert(0,str(loc));mod=importlib.import_module('gmsh')
    if str(getattr(mod,'__version__',''))!='4.15.2':
        raise RuntimeError('P10HN_STOP: Gmsh Python version not 4.15.2')
    return mod


def main():
    expr,factor=official_source()
    src,v25,_,_,_,qa=field.load_centers(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(src,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh=import_gmsh()
    gmsh.initialize()
    samples=[]
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.open(str(HERE/'P10HN_FIELD7_ONLY.geo'))
        # One radial line entirely in ice, wall distance 0.1..23.1mm.
        p0=gmsh.model.geo.addPoint(.0011,0,.03)
        p1=gmsh.model.geo.addPoint(.0241,0,.03)
        gmsh.model.geo.addLine(p0,p1)
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeMin',1e-6)
        gmsh.option.setNumber('Mesh.MeshSizeMax',.02)

        def callback(dim,tag,x,y,z,lc):
            if len(samples)>=20000:raise RuntimeError('P10HN_STOP: 20k callback guard')
            f7=math_eval(expr,x,y,z)
            k=direct.kappa(x,y,z)
            h=direct.size(dim,tag,x,y,z,lc)
            samples.append([int(dim),int(tag),float(x),float(y),float(z),
                            float(lc),float(f7),float(k),float(h)])
            return h

        gmsh.model.mesh.setSizeCallback(callback)
        begin=time.perf_counter()
        gmsh.model.mesh.generate(1)
        wall=time.perf_counter()-begin
        gmsh.model.mesh.removeSizeCallback()
        if not samples:raise RuntimeError('P10HN_STOP: callback never invoked')
        a=np.asarray(samples)
        # Because the pinned geometry's MeshSizeFactor is <1, check BOTH
        # alternatives. Native evidence decides which is actually passed.
        f7=a[:,6]
        valid=f7>0
        if not np.all(valid):raise RuntimeError('P10HN_STOP: invalid Field7 math expression')
        ratios=a[:,5]/f7
        deviations_raw=np.abs(ratios-1)
        deviations_scaled=np.abs(ratios-factor)
        status=('LC_EQUALS_F7_PASS' if np.max(deviations_raw)<1e-6 else
                'LC_EQUALS_F7_TIMES_GLOBAL_FACTOR_PASS' if np.max(deviations_scaled)<1e-6 else
                'LC_NOT_IDENTICAL_TO_F7_OR_SCALED_F7_REQUIRES_ANALYSIS')
        nodes=gmsh.model.mesh.getNodes()[0]
        result={'protocol':'P10HN_R1_NATIVE_PINNED_F7_MATHEVAL_SYNTHETIC_1D_CALLBACK',
                'status':status,'gmsh_version':gmsh.__version__,
                'pinned_P10GT_geo_sha256':GEO_SHA,
                'base_field_id':7,'original_MeshSizeFactor':factor,
                'native_callback_count':len(samples),
                'native_1D_nodes':len(nodes),'1D_wall_s':round(wall,4),
                'lc_min_max':[float(a[:,5].min()),float(a[:,5].max())],
                'F7_direct_min_max':[float(f7.min()),float(f7.max())],
                'lc_over_independent_F7_min_max':[float(ratios.min()),float(ratios.max())],
                'max_abs_lc_over_F7_minus_1':float(deviations_raw.max()),
                'max_abs_lc_over_F7_minus_factor':float(deviations_scaled.max()),
                'kappa_min_max':[float(a[:,7].min()),float(a[:,7].max())],
                'nominal_size_ratio_min_max':[float((a[:,8]/a[:,5]).min()),float((a[:,8]/a[:,5]).max())],
                'first_40_dim_tag_x_y_z_lc_F7_kappa_h':samples[:40],
                'original_CAD_loaded':False,'original_M1_loaded':False,
                'native_2D_3D_or_FEM':0,'M2_GO':False}
        REPORT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(status,'callbacks',len(samples),'report',REPORT)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HN_STOP',ERROR)
        sys.exit(2)
