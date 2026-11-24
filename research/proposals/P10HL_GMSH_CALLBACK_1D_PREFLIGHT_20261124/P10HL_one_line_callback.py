#!/usr/bin/env python3
"""P10HL: tiny synthetic 1D Gmsh 4.15.2 lc semantics preflight.

No original CAD edits, no 2D/3D mesh, no FEM, no M2. The synthetic line lies
in ice and produces JSON evidence of actual Gmsh size-callback input lc.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from p10hk_direct_kappa_callback_benchmark import DirectKappa
import p10hc_continuous_kappa_geo as field

GMSH_ROOT=Path(r'C:\gmsh-4.15.2-Windows64')
REPORT=HERE/'P10HL_RESULT.json'
ERROR=HERE/'P10HL_ERROR.txt'
BASE=.0005
MAX_CB=10000


def gmsh_module():
    try:return importlib.import_module('gmsh')
    except ImportError:
        possible=GMSH_ROOT/'lib'
        if (possible/'gmsh.py').is_file():
            sys.path.insert(0,str(possible))
            return importlib.import_module('gmsh')
        raise RuntimeError('Gmsh Python module not found. Gmsh 4.15.2 Python API required. '
                           'Use a Python environment with gmsh==4.15.2; DO NOT launch mesh scripts.')


def main():
    src,v25,_,_,_,qa=field.load_centers(HERE/'P10HA_SPATIAL_KAPPA_1200_BINS.csv',
                                       HERE/'P10HA_KAPPA_QA.json')
    direct=DirectKappa(src,v25,qa['mechanical_only_25_36_shared_smoothing_denominator'])
    gmsh=gmsh_module()
    version=str(getattr(gmsh,'__version__',''))
    if version!='4.15.2':
        raise RuntimeError('P10HL_STOP: expected gmsh Python API 4.15.2, got '+repr(version))
    samples=[]
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal',1)
        gmsh.model.add('P10HL_SYNTHETIC_LINE_1D_ONLY')
        # Entire interval is in ice: x = 1.1 .. 6.1 mm, y=0, z=30 mm.
        p0=gmsh.model.geo.addPoint(.0011,0,.03,BASE)
        p1=gmsh.model.geo.addPoint(.0061,0,.03,BASE)
        line=gmsh.model.geo.addLine(p0,p1)
        gmsh.model.geo.synchronize()
        gmsh.option.setNumber('Mesh.MeshSizeFromPoints',0)
        gmsh.option.setNumber('Mesh.MeshSizeFromCurvature',0)
        gmsh.option.setNumber('Mesh.MeshSizeExtendFromBoundary',0)
        gmsh.option.setNumber('Mesh.MeshSizeMin',.0001)
        gmsh.option.setNumber('Mesh.MeshSizeMax',.002)
        gmsh.option.setNumber('Mesh.MeshSizeFactor',1)
        field_id=gmsh.model.mesh.field.add('MathEval')
        gmsh.model.mesh.field.setString(field_id,'F',str(BASE))
        gmsh.model.mesh.field.setAsBackgroundMesh(field_id)

        def callback(dim,tag,x,y,z,lc):
            if len(samples)>=MAX_CB:raise RuntimeError('P10HL_STOP: callback count guard')
            k=direct.kappa(x,y,z)
            proposed=direct.size(dim,tag,x,y,z,lc)
            if len(samples)<MAX_CB:
                samples.append([int(dim),int(tag),float(x),float(y),float(z),
                                float(lc),float(k),float(proposed)])
            return proposed

        gmsh.model.mesh.setSizeCallback(callback)
        start=time.perf_counter()
        gmsh.model.mesh.generate(1)  # EXACTLY synthetic line, no 2D/3D/FEM
        elapsed=time.perf_counter()-start
        gmsh.model.mesh.removeSizeCallback()
        _,node_xyz,_=gmsh.model.mesh.getNodes()
        import numpy as np
        s=np.asarray(samples,float)
        if len(s)==0:raise RuntimeError('P10HL_STOP: native callback was not invoked')
        relative=np.abs(s[:,5]/BASE-1)
        n1=int(np.count_nonzero(s[:,0]==1))
        close=int(np.count_nonzero(relative<1e-6))
        report={'protocol':'P10HL_R1_NATIVE_GMSH_SYNTHETIC_1D_CALLBACK_LC_PROBE',
                'status':'LC_EQUALS_BACKGROUND_CONSTANT_PASS' if close==len(s) else 'LC_DIFFERS_FROM_BACKGROUND_CONSTANT_REQUIRES_ANALYSIS',
                'gmsh_version':version,
                'target_version':'4.15.2',
                'synthetic_1D_length_m':.005,'constant_background_field_m':BASE,
                'actual_callback_count':len(samples),'dimension_1_callback_count':n1,
                'lc_close_to_constant_count':close,
                'lc_min_max':[float(s[:,5].min()),float(s[:,5].max())],
                'lc_max_relative_deviation_from_constant':float(relative.max()),
                'kappa_min_max':[float(s[:,6].min()),float(s[:,6].max())],
                'returned_size_min_max':[float(s[:,7].min()),float(s[:,7].max())],
                'returned_characteristic_volume_ratio_min_max':[
                    float(((s[:,7]/s[:,5])**3).min()),float(((s[:,7]/s[:,5])**3).max())],
                'mesh_1D_wall_s':round(elapsed,4),
                'native_nodes':int(len(node_xyz)//3),
                'callback_samples_first_40_dim_tag_x_y_z_lc_kappa_h':samples[:40],
                'no_2D_3D_mesh_or_FEM':True,
                'real_M1_original_Field7_verified':False,
                'D025_verified':False,
                'next':'Original CAD Field[7] baseline verification; M2 forbidden until independent GO'}
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(report['status'],'callbacks=',len(samples),'evidence=',REPORT)
    finally:
        gmsh.finalize()


if __name__=='__main__':
    try:main()
    except Exception:
        ERROR.write_text(traceback.format_exc(),encoding='utf-8')
        print('P10HL_STOP: '+str(ERROR))
        sys.exit(2)
