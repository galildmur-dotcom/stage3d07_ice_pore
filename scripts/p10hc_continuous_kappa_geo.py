#!/usr/bin/env python3
"""P10HC: source-only continuous C2 mechanical kappa from 1200 physical bins.

Outputs deterministic Gmsh MathEval GEO and an independent continuous-field
numeric QA. Never executes Gmsh meshing or FEM. Source field can be evaluated
only after native Gmsh 4.15.2 parse preflight on the user's machine.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.spatial import cKDTree


PIN_OUTER='0b62cc5799a242cceb86c5e283113c4b634e6169ea91476b4faf9dec6296d760'
PIN_PARENT='5bc94e2939f6a96c1c2e7b9a77a721e3b1b8c02cbc2eb9342e80f53717f72909'
PIN_INNER='236defb377103ef45e8ac193264fac8213290c7d00e02fc1025e53c9f700cc3a'
C=(0.0,0.0,0.03)
PORE_R=0.001
R_SCALE=.75
A_SCALE=.60
ALPHA=.17 # nominal 17% characteristic tetra volume at kappa=1; not actual D-025 GO
EPS=1e-12


def check(ok,msg):
    if not ok:raise RuntimeError('P10HC_SOURCE_STOP: '+msg)


def sha(data):return hashlib.sha256(data).hexdigest()


def load_centers(csv_path,qa_path):
    qa=json.loads(qa_path.read_text(encoding='utf-8'))
    check(qa['source_zip_sha256']==PIN_OUTER and
          qa['primary_kappa_column']=='kappa25_mechanical_only' and
          qa['P10HB_primary_adaptation_policy'].startswith('MECHANICAL_ONLY'),
          'P10HA P10HB provenance/policy mismatch')
    with csv_path.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
    check(len(rows)==1200,'expected 1200 full physical bins')
    xyz=[];score25=[];score36=[];expected25=[];expected36=[];missing=[]
    for i,r in enumerate(rows):
        ir,im,ip=divmod(i,120)[0],(i%120)//12,i%12
        check((int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin']))==(ir,im,ip),
              'ordered physical bin coverage')
        dlo=float(r['d_lower_mm'])
        dhi=float(r['d_upper_mm']) if r['d_upper_mm'] else None
        d=0.5*(dlo+dhi) if dhi is not None else dlo
        t=float(r['theta_mid_rad']);p=float(r['phi_mid_rad'])
        xyz.append([np.log1p(d/.05),np.sin(t)*np.cos(p),
                    np.sin(t)*np.sin(p),np.cos(t)])
        score25.append(float(r['mechanical_robust_score25']))
        score36.append(float(r['mechanical_robust_score36']))
        expected25.append(float(r['kappa25_primary_for_M2_source_only']))
        expected36.append(float(r['kappa36_mechanical_only']))
        if int(r['QP_support_missing_in_any_compared_run']):missing.append(i)
    check(missing==qa['missing_support_bin_indices'],'QP unknown bins retained')
    return (np.array(xyz,float),np.array(score25),np.array(score36),
            np.array(expected25),np.array(expected36),qa)


def rbf_at_points(source,values,queries,scale_den):
    """Continuous C2 compact Wendland normalized RBF on physical r>R domain."""
    sourcescaled=source / np.array([R_SCALE,A_SCALE,A_SCALE,A_SCALE])
    tree=cKDTree(sourcescaled)
    scaled=queries / np.array([R_SCALE,A_SCALE,A_SCALE,A_SCALE])
    result=np.zeros(len(queries))
    for i,inds in enumerate(tree.query_ball_point(scaled,1.0)):
        if not inds:continue
        v=sourcescaled[inds]-scaled[i]
        q=np.linalg.norm(v,axis=1)
        w=np.maximum(1-q,0)**4*(4*q+1)
        result[i]=np.dot(w,values[inds])/(w.sum()+EPS)/scale_den
    return np.clip(result,0,1)


def physical_query(xyz):
    local=xyz-np.array(C)
    r=np.linalg.norm(local,axis=1)
    check(np.isfinite(r).all() and (r>=PORE_R-1e-12).all(),'query must be in ice')
    directions=local/np.maximum(r[:,None],1e-15)
    dmm=np.maximum(r-PORE_R,0)*1000
    return np.column_stack([np.log1p(dmm/.05),directions])


def geo_expression(source,values):
    rad='sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-30)'
    u=f'log(1+max(0,({rad}-0.001)*20000))'
    terms=[]
    for center,v in zip(source,values):
        ui,ux,uy,uz=center
        dot=f'(x*({ux:.17g})+y*({uy:.17g})+(z-0.03)*({uz:.17g}))/{rad}'
        q=f'sqrt(max(0,(({u}-({ui:.17g}))/0.75)^2+(2-2*({dot}))/0.36))'
        w=f'(max(0,1-({q}))^4)*(4*({q})+1)'
        terms.append((w,float(v)))
    numerator='+'.join(f'({w})*({v:.17g})' for w,v in terms if v>0)
    denominator='+'.join(f'({w})' for w,_ in terms)
    return numerator,denominator


def as_strcat(expression):
    # Only split between full terms; never truncate scientific mantissas.
    # For each field a single evaluated expression, not thousands of fields.
    terms=expression.split('+')
    # Splitting by '+' inside expressions would break functions: instead split
    # the raw string at arbitrary characters (StrCat concatenates verbatim).
    del terms
    return 'StrCat(\n'+',\n'.join('  '+json.dumps(expression[i:i+380])
                                  for i in range(0,len(expression),380))+'\n)'


def source_geo(centers,values,den):
    numerator,denominator=geo_expression(centers,values)
    lines=['// P10HC source-only C2 mechanical kappa; no native 2D/3D/FEM launched.',
           '// Include only after pinned P10GT_HXT10.geo (base Field[7]).',
           '// CAD: pore R=.001m, C=(0,0,.03m); u=log(1+d_mm/.05).',
           f'// alpha={ALPHA:.17g}: nominal local characteristic volume -17% at kappa=1, not D025 evidence.',
           'Field[40] = MathEval;',
           'Field[40].F = '+as_strcat(numerator)+';',
           'Field[41] = MathEval;',
           'Field[41].F = '+as_strcat(denominator)+';',
           'Field[42] = MathEval;',
           f'Field[42].F = "min(1,max(0,F40/(F41+{EPS:.17g}))/{den:.17g})";',
           'Field[43] = MathEval;',
           f'Field[43].F = "F7*(1-{ALPHA:.17g}*F42)^(1./3.)";',
           'Background Field = 43;',
           'Mesh.MeshSizeExtendFromBoundary=0;',
           'Mesh.MeshSizeFromPoints=0;',
           'Mesh.MeshSizeFromCurvature=0;']
    return '\n'.join(lines)+'\n'


def pinned_base_geo(package):
    raw=package.read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        check(z.testzip() is None,'P10GT outer package CRC')
        parent=z.read('P10GR_R1_BOUNDED_20_CASE_WINDOWS_2D_20261123.zip')
        check(sha(parent)==PIN_PARENT,'P10GR parent SHA')
    with zipfile.ZipFile(io.BytesIO(parent)) as z:
        check(z.testzip() is None,'P10GR inner CRC')
        nested=z.read('P10GP_R1_SURFACE_SOURCE_ONLY.zip')
        check(sha(nested)==PIN_INNER,'P10GP source SHA')
    with zipfile.ZipFile(io.BytesIO(nested)) as z:
        geo=z.read('B_SELF_CONTAINED_C1_SOUTH/P10GP_SURFACE.geo').decode('utf-8')
        m0=z.read('B_SELF_CONTAINED_C1_SOUTH/M0_ROTATED.geo')
        cad=z.read('B_SELF_CONTAINED_C1_SOUTH/sphere_pore_B6_refined_rotated.geo')
    old='min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.2))'
    new='min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.60000000000000009))'
    check(geo.count(old)==3 and geo.count('1-0.06*')==1,'expected pinned south source syntax')
    geo=geo.replace(old,new).replace('1-0.06*','1-0.089999999999999997*')
    geo=geo.replace('Mesh.Algorithm = 5; // Delaunay surface; Tri6 with order 2',
                    'Mesh.Algorithm = 6; // Frontal-Delaunay surface for HXT10 3D')
    check('Background Field = 7;' in geo and 'Mesh.MeshSizeFactor = 0.9378887276834518;' in geo,
          'M1 background field compatibility')
    return {'P10GT_HXT10.geo':geo.encode('utf-8'),
            'M0_ROTATED.geo':m0,
            'sphere_pore_B6_refined_rotated.geo':cad}


def main(args):
    centers,v25,v36,k25,k36,qa=load_centers(args.csv,args.qa)
    den=float(qa['mechanical_only_25_36_shared_smoothing_denominator'])
    p25=rbf_at_points(centers,v25,centers,den)
    p36=rbf_at_points(centers,v36,centers,den)
    mismatch=max(float(np.max(abs(p25-k25))),float(np.max(abs(p36-k36))))
    check(mismatch<1e-9,f'continuous source must reproduce frozen bin-centre table {mismatch}')
    # Test positive, finite and bounded on physical near-surface/far Cartesian loci.
    dirs=[]
    for theta in np.linspace(.05,np.pi-.05,21):
        for phi in np.linspace(-np.pi,np.pi,41):
            dirs.append([np.sin(theta)*np.cos(phi),np.sin(theta)*np.sin(phi),np.cos(theta)])
    dirs=np.array(dirs)
    samples=np.concatenate([np.array(C)+dirs*(PORE_R+mm/1000) for mm in (0,.02,.1,.5,2,5,15,25)])
    vals=rbf_at_points(centers,v25,physical_query(samples),den)
    check(np.isfinite(vals).all() and vals.min()>=0 and vals.max()<=1,'continuous field samples bounded')
    # Detect periodic azimuth seam at matched polar directions.
    seam=np.stack([np.array(C)+(PORE_R+.00002)*np.array([np.sin(t)*np.cos(p),
                np.sin(t)*np.sin(p),np.cos(t)]) for t in (.25,.75,1.6,2.8)
                for p in (-np.pi,np.pi)])
    seam_k=rbf_at_points(centers,v25,physical_query(seam),den)
    check(float(np.max(abs(seam_k[::2]-seam_k[1::2])))<1e-12,'azimuth seam')
    args.output.mkdir(parents=True,exist_ok=True)
    source=source_geo(centers,v25,den)
    base=pinned_base_geo(args.package)
    for name,raw in base.items(): (args.output/name).write_bytes(raw)
    (args.output/'P10HC_CONTINUOUS_KAPPA_FIELDS.geo').write_text(source,encoding='utf-8')
    (args.output/'P10HC_M2_SOURCE_ONLY.geo').write_text('Include "P10GT_HXT10.geo";\nInclude "P10HC_CONTINUOUS_KAPPA_FIELDS.geo";\n',encoding='utf-8')
    result={'protocol':'P10HC_R1_M1_CAD_CONTINUOUS_MECHANICAL_KAPPA_SOURCE_ONLY',
            'status':'MATHEMATICAL_FIELD_REPRODUCES_P10HB_BIN_CENTERS; NATIVE_GMSH_PARSE_PENDING',
            'source_sha256':{n:sha((args.output/n).read_bytes()) for n in
                    (*base,'P10HC_CONTINUOUS_KAPPA_FIELDS.geo','P10HC_M2_SOURCE_ONLY.geo')},
            'no_new_gmsh_mesh_or_FEM':True,
            'continuous_source_method':'compact Wendland C2 normalized RBF, positive epsilon, Cartesian directions for polar/azimuth continuity',
            'pore_center_m':list(C),'pore_radius_m':PORE_R,
            'nominal_kappa1_characteristic_volume_ratio':1-ALPHA,
            'no_D025_claim':'actual M2/M1 effective curved Tet10 volume requires native mesh and 343/729QP independent QA',
            'max_abs_reconstruction_at_all_1200_bin_centers':mismatch,
            'test_points':len(vals),'test_sample_min_max':[float(vals.min()),float(vals.max())],
            'phi_seam_max_abs':float(np.max(abs(seam_k[::2]-seam_k[1::2]))),
            'field40_numerator_expression_chars':len(geo_expression(centers,v25)[0]),
            'field41_denominator_expression_chars':len(geo_expression(centers,v25)[1]),
            'source_only_M1_mesh_sha256':'47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7',
            'open_outer_shell_limit':'no invented finite upper boundary; source decay supported around representative lower boundary only',
            'caveat':'Gmsh 4.15.2 MathEval parser limits/performance UNVERIFIED until native Windows parse; source-only output MUST NOT mesh or FEM automatically'}
    (args.output/'P10HC_SOURCE_FIELD_QA.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False))


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--csv',type=Path,required=True)
    ap.add_argument('--qa',type=Path,required=True)
    ap.add_argument('--package',type=Path,required=True,help='pinned P10GT source package ZIP')
    ap.add_argument('--output',type=Path,required=True)
    main(ap.parse_args())
