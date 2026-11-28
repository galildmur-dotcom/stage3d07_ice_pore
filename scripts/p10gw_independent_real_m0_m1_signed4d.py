#!/usr/bin/env python3
"""Read-only independent signed 4D M0/P10GT-M1 pair audit from original ZIPs.

Never treats a crossmesh difference as a validated spatial error estimator.
"""
from __future__ import annotations
from collections import defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
M0=ROOT/'research/evidence/P10FS_FRESH_M0_R_20261122/raw/P10FN_M0_R_PHYSICS_EVIDENCE.zip'
M0_SHA='b5191c4f23a2a07f09b6615c52d258c119f891813e85d789fac63209710a48f4'
M1_SHA='8b32a215653ff954a2d05be2e46ed09ddfb52c5ac6e6da65ae3f07ffc3bd81bb'
M0_MESH='926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6'
M1_MESH='47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7'
FIELDS=('mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
        'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m',
        'mechanical_total_per_m','thermal_total_per_m','total_per_m')
BOUNDS=('time_start_s','time_end_s','r_lower_mm','r_upper_mm',
        'theta_lower_rad','theta_upper_rad','phi_lower_rad','phi_upper_rad')
FILE_NAMES=('P10DD_SIGNED_R_THETA_PHI_T.csv','P10DD_FULL4D_CLOSURE_AUDIT.csv',
            'P10W_ANALYTIC_ADJOINT.csv','P10W_COMPONENTS.csv','P10W_STEP_COMPONENTS.csv')


def need(ok,msg):
    if not ok:raise ValueError('P10GW_STOP: '+msg)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def read_zip(path,pin,mesh,mesh_sha):
    raw=Path(path).read_bytes()
    need(sha(raw)==pin,'ZIP SHA mismatch '+mesh)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None and set(z.namelist())==set(FILE_NAMES)|
             {'P10FN_PHYSICS_MANIFEST.json','P10FN_SOLVER_STDOUT_STDERR.txt'},
             'ZIP CRC/member names '+mesh)
        manifest=json.loads(z.read('P10FN_PHYSICS_MANIFEST.json'))
        need(manifest['mesh']==mesh and manifest['mesh_sha256']==mesh_sha and
             manifest['status']=='PHYSICS_REAL_4D_INDEPENDENT_CLOSURE_PASS' and
             manifest['native_exit_code']==0 and not manifest['stop_reason'] and
             manifest['FEM_attempts']==1 and manifest['fresh_forward'] is True and
             manifest['reuse_forward'] is False and
             manifest['parameters']=={'steps':6,'dt':150,'cutoff_mm':5,
                                      'threads':4,'law':'EDV_VAR','xi':0,'B6_mm':5},
             'native physics provenance mismatch '+mesh)
        data={n:list(csv.DictReader(io.StringIO(z.read(n).decode('utf-8-sig')))) for n in FILE_NAMES}
    return manifest,data


def f(row,key):return float(row[key])


def close(a,b,label,atol=2e-9,rtol=2e-8):
    need(abs(a-b)<=atol+rtol*max(abs(a),abs(b)),f'{label}: {a} vs {b}')


def index(data,mesh,tets):
    rows=data[FILE_NAMES[0]]
    need(len(rows)==7206,'7206 4D rows '+mesh)
    ix={}
    qp=defaultdict(lambda:[0,0])
    for row in rows:
        need(row['mesh']==mesh and row['mode']=='R' and row['functional']=='jpeak',
             '4D row provenance')
        step=int(row['step'])
        need(1<=step<=6 and f(row,'time_start_s')==150*(step-1)
             and f(row,'time_end_s')==150*step,'4D time grid')
        key=(step,row['region'],int(row['radial_bin']),int(row['mu_bin']),int(row['phi_bin']))
        need(key not in ix,'duplicate bin')
        ix[key]=row
        close(sum(f(row,k) for k in FIELDS[:3]),f(row,'mechanical_total_per_m'),'mech row')
        close(sum(f(row,k) for k in FIELDS[3:6]),f(row,'thermal_total_per_m'),'therm row')
        close(sum(f(row,k) for k in FIELDS[:6]),f(row,'total_per_m'),'total row')
        if row['region']=='VOLUME':
            need(0<=key[2]<10 and 0<=key[3]<10 and 0<=key[4]<12,
                 'physical bin range')
            qp[step][0]+=int(row['mechanical_qp'])
            qp[step][1]+=int(row['thermal_qp'])
        else:
            need(row['region']=='TOP_ROBIN' and int(row['top_robin_qp'])>0,
                 'boundary row type and support')
    need(sum(1 for k in ix if k[1]=='VOLUME')==7200 and
         sum(1 for k in ix if k[1]=='TOP_ROBIN')==6,'bin coverage')
    need(all(qp[s]==[tets*27,tets*64] for s in range(1,7)),
         'quadrature samples not conserved')
    comp={r['functional']:r for r in data['P10W_COMPONENTS.csv']}
    adj={r['functional']:r for r in data['P10W_ANALYTIC_ADJOINT.csv']}
    need(set(comp)=={'j6','jpeak','jen'} and set(adj)==set(comp),'functionals')
    for field,cfield in zip(FIELDS[:3],('explicit_objective_shape_per_m',
                'equilibrium_residual_shape_per_m','internal_history_shape_per_m')):
        close(sum(f(r,field) for r in rows),f(comp['jpeak'],cfield),'global '+field)
    for field,cfield in (('mechanical_total_per_m','total_mechanical_shape_per_m'),
                         ('thermal_total_per_m','thermal_adjoint_per_m'),
                         ('total_per_m','total_adjoint_per_m')):
        close(sum(f(r,field) for r in rows),f(comp['jpeak'],cfield),'global '+field)
    for fn in comp:
        close(f(comp[fn],'total_adjoint_per_m'),f(adj[fn],'total_adjoint_per_m'),
              'global paired '+fn)
    return ix,comp,adj,qp


def report(m1):
    man0,data0=read_zip(M0,M0_SHA,'M0',M0_MESH)
    man1,data1=read_zip(m1,M1_SHA,'M1',M1_MESH)
    ix0,c0,_,qp0=index(data0,'M0',7992)
    ix1,c1,_,qp1=index(data1,'M1',9623)
    need(ix0.keys()==ix1.keys(),'crossmesh 4D bin keys')
    for key in ix0:
        for bound in BOUNDS:
            need(ix0[key][bound]==ix1[key][bound],
                 'crossmesh physical support differs '+str(key)+' '+bound)
    funcs={}
    for fn in sorted(c0):
        o=f(c0[fn],'total_adjoint_per_m');n=f(c1[fn],'total_adjoint_per_m')
        funcs[fn]={'M0_per_m':o,'M1_per_m':n,'delta_per_m':n-o,
                   'relative_delta_percent':100*(n-o)/abs(o),
                   'M0_objective':f(c0[fn],'objective'),
                   'M1_objective':f(c1[fn],'objective')}
    components={}
    for k in FIELDS:
        o=sum(f(r,k) for r in ix0.values());n=sum(f(r,k) for r in ix1.values())
        components[k]={'M0_per_m':o,'M1_per_m':n,'delta_per_m':n-o,
                       'absolute_bin_L1_delta_per_m':sum(abs(f(ix1[b],k)-f(ix0[b],k)) for b in ix0)}
    projections={axis:defaultdict(lambda:{'signed':0.,'l1':0.,'count':0}) for axis in
                 ('time','radial','mu','phi','region')}
    top=[]
    for key in sorted(ix0):
        o=ix0[key];n=ix1[key]
        delta=f(n,'total_per_m')-f(o,'total_per_m')
        top.append({'key':key,'delta_per_m':delta,'abs_delta_per_m':abs(delta),
                    'M0_mechanical_qp':int(o['mechanical_qp']),
                    'M1_mechanical_qp':int(n['mechanical_qp'])})
        for axis,part in (('time',key[0]),('radial',key[2]),
                          ('mu',key[3]),('phi',key[4]),('region',key[1])):
            if axis!='region' and key[1]!='VOLUME':continue
            item=projections[axis][part]
            item['signed']+=delta;item['l1']+=abs(delta);item['count']+=1
    top.sort(key=lambda r:r['abs_delta_per_m'],reverse=True)
    total_l1=sum(r['abs_delta_per_m'] for r in top)
    def share(pred):return 100*sum(r['abs_delta_per_m'] for r in top if pred(r))/total_l1
    cuts={'polar_caps_mu0_9_percent':share(lambda r:r['key'][1]=='VOLUME' and r['key'][3] in(0,9)),
          'near_pore_first_0p1mm_percent':share(lambda r:r['key'][1]=='VOLUME' and r['key'][2]<=2),
          'last_300s_percent':share(lambda r:r['key'][0]>=5),
          'polar_near_and_last300_percent':share(lambda r:r['key'][1]=='VOLUME' and r['key'][2]<=2 and r['key'][3] in(0,9) and r['key'][0]>=5)}
    return {'protocol':'P10GW_INDEPENDENT_REAL_P10FS_M0_P10GV_M1_SIGNED_4D',
            'M0_zip_sha256':M0_SHA,'M1_zip_sha256':M1_SHA,
            'mesh_sha256':{'M0':M0_MESH,'M1':M1_MESH},
            'M1_native':{'exit':man1['native_exit_code'],'wall_s':man1['wall_s'],
                         'peak_private_bytes':man1['peak_private_bytes_polled'],
                         'exe_sha256':man1['executable_sha256'],
                         'history_sha256':man1['history_sha256']},
            'independent_row_count':{'M0':len(ix0),'M1':len(ix1)},
            'physical_4d_bounds_exact_equal':True,
            'crossmesh_qp':{'M0':dict(qp0),'M1':dict(qp1)},
            'global_functionals':funcs,'signed_components_jpeak':components,
            'axis_projections':{a:{str(k):v for k,v in sorted(x.items(),key=lambda t:str(t[0]))}
                                 for a,x in projections.items()},
            'delta_jpeak_per_m':funcs['jpeak']['delta_per_m'],
            'signed_bin_L1_delta_per_m':total_l1,
            'signed_bin_cancellation_factor':total_l1/abs(funcs['jpeak']['delta_per_m']),
            'abs_delta_4d_shares':cuts,
            'top20_bin_deltas':top[:20],
            'verdict':'REAL_M0_M1_SIGNED4D_COMPARE_PASS_TIMESTEP_UNCERTAINTY_NOT_CLEARED_NO_M2_MARK',
            'M2_automatic_GO':False}


if __name__=='__main__':
    print(json.dumps(report(Path(sys.argv[1])),indent=2,ensure_ascii=False))
