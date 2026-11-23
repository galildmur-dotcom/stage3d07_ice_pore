#!/usr/bin/env python3
"""Read-only P10GY 12-run native signed-4D time audit and seven-level comparison.

Time projection is conservative piecewise-constant reconstruction, NOT a
measurement of exact fine-time adjoint kernels. Pure spatial time integrals
are exact finite sums of solver-exported signed 4D bin contributions.
"""
from __future__ import annotations
from collections import defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
M0_ZIP=ROOT/'research/evidence/P10FS_FRESH_M0_R_20261122/raw/P10FN_M0_R_PHYSICS_EVIDENCE.zip'
M1_ZIP=ROOT.parent/'upload/P10FN_M1_R_PHYSICS_EVIDENCE.zip'
PINS={'M0':('926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6',
            'b5191c4f23a2a07f09b6615c52d258c119f891813e85d789fac63209710a48f4',7992),
      'M1':('47460969be26c2bd0a15e0b1425806fa350aa09aa2b4ac9f80605b433fc65ca7',
            '8b32a215653ff954a2d05be2e46ed09ddfb52c5ac6e6da65ae3f07ffc3bd81bb',9623)}
OUTER_SHA='0b62cc5799a242cceb86c5e283113c4b634e6169ea91476b4faf9dec6296d760'
PLAN={150:6,75:12,60:15,50:18,45:20,36:25,25:36}
FIELDS=('mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
        'thermal_mass_per_m','thermal_diffusion_per_m','thermal_robin_per_m')
ALLFIELDS=FIELDS+('mechanical_total_per_m','thermal_total_per_m','total_per_m')
SPATIAL_KEYS=('r_lower_mm','r_upper_mm','theta_lower_rad','theta_upper_rad',
              'phi_lower_rad','phi_upper_rad')
DATA=('P10DD_SIGNED_R_THETA_PHI_T.csv','P10DD_FULL4D_CLOSURE_AUDIT.csv',
      'P10W_ANALYTIC_ADJOINT.csv','P10W_COMPONENTS.csv','P10W_STEP_COMPONENTS.csv')


def check(ok,msg):
    if not ok:raise ValueError('P10GZ_INDEPENDENT_STOP: '+msg)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def close(a,b,label):
    check(np.isfinite(a) and np.isfinite(b) and
          abs(a-b) <= 2e-9+2e-8*max(abs(a),abs(b)),f'{label}: {a} vs {b}')


def read_csv(z,name):
    return list(csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig'))))


def parse_one(raw,mesh,dt,require_manifest):
    check(sha(raw)==PINS[mesh][1] if dt==150 else True,'baseline SHA '+mesh)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        check(z.testzip() is None,'inner CRC')
        check(set(DATA).issubset(set(z.namelist())),'incomplete 4D CSV')
        manifest=json.loads(z.read('P10GY_MANIFEST.json' if require_manifest else
                                   'P10FN_PHYSICS_MANIFEST.json'))
        if require_manifest:
            check(manifest['protocol']=='P10GY_R1_NEW_TEMPORAL_4D' and
                  manifest['status']=='P10GY_REAL_TIME4D_PASS' and
                  manifest['dt']==dt and manifest['steps']==PLAN[dt] and
                  manifest['independent_4d']['rows']==1201*PLAN[dt] and
                  manifest['independent_4d']['status']=='P10GY_INDEPENDENT_TIME4D_CLOSURE_PASS',
                  'dynamic evidence protocol/4D status')
        check(manifest['mesh']==mesh and manifest['mesh_sha256']==PINS[mesh][0] and
              manifest.get('native_exit_code')==0 and not manifest.get('stop_reason') and
              manifest.get('FEM_attempts')==1, 'native provenance')
        rows=read_csv(z,DATA[0]);closure=read_csv(z,DATA[1]);
        adj=read_csv(z,DATA[2]);comp=read_csv(z,DATA[3]);steps=read_csv(z,DATA[4])
    n=PLAN[dt]
    check(len(rows)==1201*n and len(closure)==n,'expected 4D rows')
    vals=np.full((n,1200,9),np.nan,dtype=float)
    support=np.full((n,1200,2),-1,dtype=int)
    robin=np.full((n,9),np.nan,dtype=float)
    bounds={}
    for row in rows:
        check(row['mesh']==mesh and row['mode']=='R' and row['functional']=='jpeak',
              'physical mode/function')
        j=int(row['step'])-1
        check(0<=j<n and int(row['time_start_s'])==j*dt and
              int(row['time_end_s'])==(j+1)*dt,'physical time support')
        v=np.array([float(row[k]) for k in ALLFIELDS])
        close(float(np.sum(v[:3])),float(v[6]),'row mech')
        close(float(np.sum(v[3:6])),float(v[7]),'row thermal')
        close(float(np.sum(v[:6])),float(v[8]),'row total')
        if row['region']=='VOLUME':
            ir,im,ip=[int(row[k]) for k in ('radial_bin','mu_bin','phi_bin')]
            check(0<=ir<10 and 0<=im<10 and 0<=ip<12,'spatial key')
            idx=(ir*10+im)*12+ip
            check(np.isnan(vals[j,idx,8]),'duplicate physical bin')
            vals[j,idx,:]=v
            support[j,idx]=[int(row['mechanical_qp']),int(row['thermal_qp'])]
            bb=tuple(row[k] for k in SPATIAL_KEYS)
            if idx in bounds:check(bb==bounds[idx],'drift in physical spatial bin bounds')
            bounds[idx]=bb
        else:
            check(row['region']=='TOP_ROBIN' and np.isnan(robin[j,8]) and
                  int(row['top_robin_qp'])>0,'top Robin')
            robin[j,:]=v
    check(not np.isnan(vals).any() and not np.isnan(robin).any() and len(bounds)==1200,
          'complete every time/space bin')
    check(np.all(support>=0),'quadrature support not negative')
    check(np.all(np.sum(support[:,:,0],axis=1)==PINS[mesh][2]*27) and
          np.all(np.sum(support[:,:,1],axis=1)==PINS[mesh][2]*64),
          'mechanical/thermal QP total')
    time_comp=vals.sum(axis=1)+robin
    check(len(steps)>=3*n,'step components count')
    for j in range(n):
        cr=[r for r in closure if int(r['step'])==j+1]
        check(len(cr)==1,'unique closure row')
        close(float(time_comp[j,8]),float(cr[0]['total_per_m']),'step full closure')
        sc=[r for r in steps if r['functional']=='jpeak' and int(r['time_step'])==j+1]
        check(len(sc)==1,'P10W time component')
        for k,field in enumerate(('explicit_objective_shape_per_m',
                     'equilibrium_residual_shape_per_m','internal_history_shape_per_m')):
            close(float(time_comp[j,k]),float(sc[0][field]),'time mechanical '+field)
    global_comp=time_comp.sum(axis=0)
    official={r['functional']:r for r in comp}
    check(set(official)=={'j6','jpeak','jen'},'all three functional rows')
    ad={r['functional']:r for r in adj}
    check(set(ad)==set(official),'adjoint functional coverage')
    for key in official:
        close(float(official[key]['total_adjoint_per_m']),
              float(ad[key]['total_adjoint_per_m']),'functional '+key)
    peak=official['jpeak']
    for k,name in enumerate(('explicit_objective_shape_per_m',
                             'equilibrium_residual_shape_per_m','internal_history_shape_per_m')):
        close(float(global_comp[k]),float(peak[name]),'global component '+name)
    for k,name in ((6,'total_mechanical_shape_per_m'),
                   (7,'thermal_adjoint_per_m'),(8,'total_adjoint_per_m')):
        close(float(global_comp[k]),float(peak[name]),'global total '+name)
    if require_manifest:
        close(float(manifest['independent_4d']['jpeak_derivative_per_m']),
              float(global_comp[8]),'manifest 4D numeric')
    return {'mesh':mesh,'dt':dt,'n':n,'manifest':manifest,
            'f':{k:{'J':float(v['objective']),'D_R':float(v['total_adjoint_per_m'])}
                 for k,v in official.items()},
            'vals':vals,'support':support,'robin':robin,'bounds':bounds,
            'global_signed':global_comp}


def projection(x, dt, target_dt=25):
    # Dense temporal 25 s output, integral-conserving *piecewise constant*
    # reconstruction of each discrete interval contribution. Not an exact
    # physical re-integration of the finer adjoint kernel.
    n=900//target_dt
    out=np.zeros((n,)+x.shape[1:],float)
    for j in range(x.shape[0]):
        s,e=j*dt,(j+1)*dt
        for k in range(s//target_dt,(e-1)//target_dt+1):
            overlap=max(0,min(e,(k+1)*target_dt)-max(s,k*target_dt))
            if overlap:out[k]+=x[j]*(overlap/dt)
    check(np.allclose(out.sum(axis=0),x.sum(axis=0),rtol=1e-12,atol=1e-9),
          'conservative time projection')
    return out


def norm(x):return float(np.abs(x).sum())


def aggregate(grids):
    result={}
    bounds0=grids[('M0',150)]['bounds']
    for g in grids.values():check(g['bounds']==bounds0,'mesh/time physical spatial bin geometry mismatch')
    for mesh in ('M0','M1'):
        fine=grids[(mesh,25)]
        fv=fine['vals'];fp=projection(fv,25)
        a={}
        for dt in sorted(PLAN,reverse=True):
            g=grids[(mesh,dt)]
            s=g['vals'].sum(axis=0)
            ref=fv.sum(axis=0)
            d=s-ref
            # Exact signed spatial-bin time integral difference (time indexing
            # has been summed, so no reconstruction assumption).
            spatial={name:norm(d[:,k]) for k,name in enumerate(ALLFIELDS)}
            # Reconstructed time-resolved difference, only a diagnostic upper
            # bound on discretely represented time curves.
            rp=projection(g['vals'],dt)
            a[str(dt)]={'dt':dt,'steps':g['n'],'global':g['f'],
                         'global_parts':{name:float(g['global_signed'][k])
                                         for k,name in enumerate(ALLFIELDS)},
                         'global_delta_from_25':{k:g['f'][k]['D_R']-fine['f'][k]['D_R']
                                                for k in ('j6','jpeak','jen')},
                         'spatial_integrated_L1_vs_25':spatial,
                         'time_projected_4D_L1_vs_25':{
                             name:norm((rp-fp)[:,:,k]) for k,name in enumerate(ALLFIELDS)},
                         'zero_mechanical_qp_spatial_bins':int(np.count_nonzero(
                              (g['support'][:,:,0].sum(axis=0)==0))),
                         'native_wall_s':g['manifest'].get('wall_s'),
                         'native_peak_private_bytes':g['manifest'].get('peak_private_bytes_polled')}
        result[mesh]=a
    comparisons={}
    for dt in sorted(PLAN,reverse=True):
        m0,m1=grids[('M0',dt)],grids[('M1',dt)]
        d=m1['vals']-m0['vals']
        s0,s1=m0['vals'].sum(axis=0),m1['vals'].sum(axis=0)
        ds=s1-s0
        total=norm(d[:,:,8])
        ir=np.arange(1200)//120
        im=(np.arange(1200)//12)%10
        t=(np.arange(m0['n'])+1)*dt
        cap=np.isin(im,[0,9]);wall=ir<=2;late=t>600
        comparisons[str(dt)]={
            'jpeak_signed_delta':m1['f']['jpeak']['D_R']-m0['f']['jpeak']['D_R'],
            'native_4D_L1_by_component':{name:norm(d[:,:,k])
                                          for k,name in enumerate(ALLFIELDS)},
            'time_integrated_spatial_L1_by_component':{
                name:norm(ds[:,k]) for k,name in enumerate(ALLFIELDS)},
            'jpeak_local_4D_L1':total,
            'absolute_4D_L1_shares_percent':{
                'polar_caps':100*norm(d[:,cap,8])/total,
                'near_wall_0_100um':100*norm(d[:,wall,8])/total,
                'late_time_600_900':100*norm(d[late,:,8])/total,
                'intersection_polar_near_late':100*norm(d[late][:,cap&wall,8])/total},
            'time_step_L1':[{ 'start_s':j*dt,'end_s':(j+1)*dt,
                              'L1':norm(d[j,:,8]),'signed':float(d[j,:,8].sum())}
                             for j in range(m0['n'])]
        }
    # Finest time uncertainty for spatial integrals should be directly
    # compared to finest intermesh spatial signal, component by component.
    comp='25'
    ratios={}
    for name in ALLFIELDS:
        emax=max(result['M0']['36']['spatial_integrated_L1_vs_25'][name],
                 result['M1']['36']['spatial_integrated_L1_vs_25'][name])
        spatial=comparisons[comp]['time_integrated_spatial_L1_by_component'][name]
        ratios[name]={'max_M0_M1_temporal_L1_dt36_vs25':emax,
                      'M1_minus_M0_spatial_L1_dt25':spatial,
                      'ratio':emax/spatial if spatial>0 else None}
    fine0=grids[('M0',25)]['vals'].sum(axis=0)
    fine1=grids[('M1',25)]['vals'].sum(axis=0)
    time0=grids[('M0',36)]['vals'].sum(axis=0)-fine0
    time1=grids[('M1',36)]['vals'].sum(axis=0)-fine1
    local_signal=np.abs(fine1[:,8]-fine0[:,8])
    local_time=np.maximum(np.abs(time0[:,8]),np.abs(time1[:,8]))
    signal_total=float(local_signal.sum())
    local_robust={
        'signal_L1':signal_total,
        'noise_max_between_two_meshes_L1':float(local_time.sum()),
        'signal_mass_share_where_signal_gt_2x_time_percent':
             float(100*local_signal[local_signal>2*local_time].sum()/signal_total),
        'signal_mass_share_where_signal_gt_5x_time_percent':
             float(100*local_signal[local_signal>5*local_time].sum()/signal_total),
        'signal_mass_share_where_signal_gt_10x_time_percent':
             float(100*local_signal[local_signal>10*local_time].sum()/signal_total),
        'number_spatial_bins_signal_le_time':int(np.count_nonzero(local_signal<=local_time)),
        'number_spatial_bins_total':1200,
        'note':'sensitivity analysis of *spatial time-integrated* signed total; ratios 2/5/10 are diagnostics, not frozen acceptance gates',
    }
    full0=projection(grids[('M0',25)]['vals'],25)[:,:,8]
    full1=projection(grids[('M1',25)]['vals'],25)[:,:,8]
    coarse0=projection(grids[('M0',36)]['vals'],36)[:,:,8]
    coarse1=projection(grids[('M1',36)]['vals'],36)[:,:,8]
    four_signal=np.abs(full1-full0)
    four_time=np.maximum(np.abs(coarse0-full0),np.abs(coarse1-full1))
    four_total=float(four_signal.sum())
    four_robust={
        'time_projection':'25s piecewise-constant conservative reconstruction',
        'signal_L1_4D':four_total,
        'max_per_4D_bin_temporal_perturbation_L1':float(four_time.sum()),
        'noise_L1_over_signal_L1':float(four_time.sum()/four_total),
        'signal_mass_share_where_signal_gt_2x_time_percent':
            float(100*four_signal[four_signal>2*four_time].sum()/four_total),
        'signal_mass_share_where_signal_gt_5x_time_percent':
            float(100*four_signal[four_signal>5*four_time].sum()/four_total),
        'number_time_spatial_bins_signal_le_time':int(np.count_nonzero(four_signal<=four_time)),
        'number_time_spatial_bins_total':int(four_signal.size),
        'warning':'interpolated diagnostic only: not exact physical common-time QP re-integration',
    }
    temporal_scales={}
    for window in (25,50,75,150):
        k=window//25
        reshape=lambda x:x.reshape(900//window,k,1200).sum(axis=1)
        wsignal=np.abs(reshape(full1)-reshape(full0))
        wnoise=np.maximum(np.abs(reshape(coarse0)-reshape(full0)),
                          np.abs(reshape(coarse1)-reshape(full1)))
        totalw=norm(wsignal)
        temporal_scales[str(window)]={
            'time_window_s':window,'intermesh_L1':totalw,
            'temporal_max_per_bin_L1':norm(wnoise),
            'noise_to_signal_ratio':norm(wnoise)/totalw if totalw else None,
            'signal_mass_where_gt_5x_temporal_percent':
              100*norm(wsignal[wsignal>5*wnoise])/totalw if totalw else None}
    # Crossmesh difference-of-differences has correlated temporal errors;
    # report that stability separately from independent-mesh temporal noise.
    change36=(grids[('M1',36)]['vals'].sum(axis=0)-
              grids[('M0',36)]['vals'].sum(axis=0))
    change25=(fine1-fine0)
    stable={}
    for k,name in enumerate(ALLFIELDS):
        signal=norm(change25[:,k]); drift=norm(change36[:,k]-change25[:,k])
        stable[name]={'L1_delta_mesh_dt25':signal,
                      'L1_delta_of_crossmesh_indicators_dt36_vs25':drift,
                      'drift_ratio':drift/signal if signal else None}
    # The same 25 s reconstruction yields the time-resolved version.
    delta36=coarse1-coarse0
    delta25=full1-full0
    reconstructed_change={'L1_delta_mesh_dt25':norm(delta25),
                          'L1_delta_of_crossmesh_indicator_dt36_vs25':norm(delta36-delta25),
                          'drift_ratio':norm(delta36-delta25)/norm(delta25),
                          'warning':'reconstruction-based; time windows do not exactly align for dt36'}
    return {'grids':result,'intermesh':comparisons,
            'fine_pair_dt36_25_temporal_vs_intermesh_spatial_L1_ratios':ratios,
            'local_spatial_signal_vs_time_sensitivity':local_robust,
            'time_resolved_reconstruction_sensitivity':four_robust,
            'reconstructed_4D_time_window_sensitivity':temporal_scales,
            'crossmesh_indicator_dt36_vs25_stability_by_component':stable,
            'time_resolved_crossmesh_indicator_stability':reconstructed_change}


def audit(path):
    raw=Path(path).read_bytes();check(sha(raw)==OUTER_SHA,'original outer ZIP fingerprint')
    grids={}
    with zipfile.ZipFile(io.BytesIO(raw)) as outer:
        check(len(outer.namelist())==12 and outer.testzip() is None,'12 nested ZIP CRC')
        names=outer.namelist()
        markers=set()
        for name in names:
            found=re.search(r'P10GY_(M[01])_DT(\d+)_EVIDENCE\.zip$',name)
            check(found is not None,'unknown nested evidence name '+name)
            mesh,dt=found.group(1),int(found.group(2))
            check(dt in PLAN and (mesh,dt) not in grids,'duplicate/unknown dt pair')
            g=parse_one(outer.read(name),mesh,dt,True)
            marker=g['manifest']['one_shot']
            check('P10GY_ONE_SHOT_MARKERS' in marker and marker not in markers,
                  'wrong/repeated one-shot marker')
            markers.add(marker)
            grids[(mesh,dt)]=g
    check(len(grids)==12 and set(grids)=={(m,dt) for m in ('M0','M1') for dt in PLAN if dt!=150},
          'expected six time levels times two meshes')
    for mesh,path150 in (('M0',M0_ZIP),('M1',M1_ZIP)):
        grids[(mesh,150)]=parse_one(path150.read_bytes(),mesh,150,False)
    derived=aggregate(grids)
    return {'protocol':'P10GZ_R1_REAL_P10GY_12_4D_TIME_LEVELS_INDEPENDENT_AUDIT',
            'outer_zip_sha256':OUTER_SHA,'inner_count':12,
            'mesh_sha256':{m:v[0] for m,v in PINS.items()},
            'source_7_level_timestep_s':sorted(PLAN,reverse=True),
            'all_14_physical_ZIP_CRC_SHA_NATIVE_4D_CLOSURE_PASS':True,
            'independent_QP_and_4D_bin_support_PASS':True,
            'time_projection_method':'interval-conservative piecewise-constant (diagnostic, not exact 4D field)',
            'result':derived}


if __name__=='__main__':
    print(json.dumps(audit(Path(sys.argv[1])),ensure_ascii=False,indent=2))
