#!/usr/bin/env python3
"""Read-only Stage3D07 signed 4D convergence audit M17..M21.

Distinguishes signed contributions from differences, measures fine/coarsened
norms, positive/negative variation and time/polar concentration. No FEM/Gmsh.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile
import numpy as np

ROOT=Path(__file__).resolve().parent
OUTPUT_DIR=ROOT.parent if ROOT.name=='tools' and ROOT.parent.name=='research' else ROOT
SOURCES={
 'M17':('P10OZ_M17_FIRST_FULL4D_EVIDENCE.zip','P10OZ_MANIFEST.json',
        '5661ecc401019959c9cad9f0277f16f2c47d4c0bdb61450ab3465582ee3e078d'),
 'M18':('P10PD_M18_FIRST_FULL4D_EVIDENCE.zip','P10PD_MANIFEST.json',
        '6d75dc44ca1d3a3a86170b6a8577cb90d38e35e8349cc44b6d862832b432a5d5'),
 'M19':('P10PI_M19_FIRST_FULL4D_EVIDENCE.zip','P10PI_MANIFEST.json',
        '033d6097783ec34edd1d0a256c013fe569e2cb54d7f8d392980a53d0183b5b46'),
 'M20':('P10PL_M20_FIRST_FULL4D_EVIDENCE.zip','P10PL_MANIFEST.json',
        'ab5c98b6f3a3c4576eeb31027b8d8f7ef33f02a73a9f83d8827a067173c0d508'),
 'M21':('P10PP_M21_FIRST_FULL4D_EVIDENCE.zip','P10PP_MANIFEST.json',
        '78c40462b9d4aed113555a6d0bdf211cd724f1517852290a3ef0d5b7e7f0924d'),
}
FIELDS=('total_per_m','mechanical_total_per_m','thermal_total_per_m',
        'mech_explicit_per_m','mech_equilibrium_per_m','mech_history_per_m',
        'thermal_mass_per_m','thermal_diffusion_per_m',
        'mechanical_volume_m3','thermal_volume_m3')
SHAPE=(36,10,10,12)

def need(ok,msg):
    if not ok:raise RuntimeError('P10PR_STOP '+msg)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda:f.read(4*1024*1024),b''):h.update(part)
    return h.hexdigest()

def get(tag):
    fn,mn,digest=SOURCES[tag]
    candidates=(ROOT/'upload'/fn,ROOT.parent/'upload'/fn,
                ROOT.parent.parent/'upload'/fn)
    p=next((candidate for candidate in candidates if candidate.is_file()),candidates[0])
    need(p.is_file() and sha(p)==digest,'source SHA '+tag)
    out={field:np.full(SHAPE,np.nan) for field in FIELDS}
    with zipfile.ZipFile(p) as z:
        need(z.testzip() is None,'ZIP CRC '+tag)
        m=json.loads(z.read(mn))
        need(m['status'].endswith('REAL_FULL4D_PASS') and m['mesh']==tag and
             m['native_exit_code']==0 and m['regime']['steps']==36 and
             m['regime']['dt_s']==25 and
             m['independent_4d']['status']=='P10GY_INDEPENDENT_TIME4D_CLOSURE_PASS' and
             m['two_term_explicit']['status']=='P10OP_TWO_TERM_PHYSICAL_CSV_QA_PASS',
             'physical acceptance '+tag)
        rows=csv.DictReader(io.StringIO(z.read('P10DD_SIGNED_R_THETA_PHI_T.csv').decode('utf-8-sig')))
        keys=set();bound={}
        for row in rows:
            need(row['mesh']==tag and row['mode']=='R' and row['functional']=='jpeak','identity')
            if row['region']!='VOLUME':continue
            t,r,u,p=(int(row[k]) for k in ('step','radial_bin','mu_bin','phi_bin'))
            k=(t-1,r,u,p)
            need(0<=t-1<36 and 0<=r<10 and 0<=u<10 and 0<=p<12 and k not in keys,
                 'invalid/duplicate 4D key')
            keys.add(k)
            for field in FIELDS:out[field][k]=float(row[field])
            bound[k]=tuple(float(row[x]) for x in ('time_start_s','time_end_s',
                'r_lower_mm','r_upper_mm','theta_lower_rad','theta_upper_rad',
                'phi_lower_rad','phi_upper_rad') if row[x]!='')
        need(len(keys)==43200 and all(np.isfinite(x).all() for x in out.values()),
             'incomplete 4D '+tag)
        need(abs(np.sum(out['total_per_m'])-m['independent_4d']['jpeak_derivative_per_m'])<1e-8,
             'global sum mismatch '+tag)
        need(np.max(np.abs(out['total_per_m']-out['mechanical_total_per_m']-
                           out['thermal_total_per_m']))<1e-10,
             'total component mismatch '+tag)
        need(np.max(np.abs(out['mechanical_total_per_m']-
                           out['mech_explicit_per_m']-
                           out['mech_equilibrium_per_m']-
                           out['mech_history_per_m']))<1e-10,
             'mechanical decomposition mismatch '+tag)
    return m,out,bound

def signed_stats(x):
    return {'signed':float(np.sum(x)),
            'positive':float(np.sum(np.maximum(x,0.))),
            'negative':float(np.sum(np.minimum(x,0.))),
            'absolute':float(np.sum(np.abs(x))),
            'rms_component':float(np.linalg.norm(x.ravel()))}

def coarse_stats(delta):
    operations={
        'full_43200':delta,
        'integrated_phi_3600':np.sum(delta,axis=3),
        'integrated_time_1200':np.sum(delta,axis=0),
        'integrated_time_and_phi_100':np.sum(delta,axis=(0,3)),
        'integrated_time_phi_and_radial_10mu':np.sum(delta,axis=(0,1,3)),
        'integrated_time_phi_and_latitude_10radial':np.sum(delta,axis=(0,2,3)),
        'temporal_series_36':np.sum(delta,axis=(1,2,3)),
        'global_one':np.sum(delta,keepdims=True),
    }
    return {k:float(np.sum(np.abs(v))) for k,v in operations.items()}

def coarse_relative(a,b):
    transformations={
        'full_43200':lambda x:x,
        'integrated_phi_3600':lambda x:np.sum(x,axis=3),
        'integrated_time_1200':lambda x:np.sum(x,axis=0),
        'integrated_time_and_phi_100':lambda x:np.sum(x,axis=(0,3)),
        'integrated_time_phi_and_radial_10mu':lambda x:np.sum(x,axis=(0,1,3)),
        'integrated_time_phi_and_latitude_10radial':lambda x:np.sum(x,axis=(0,2,3)),
        'temporal_series_36':lambda x:np.sum(x,axis=(1,2,3)),
    }
    return {key:{'absolute_difference':float(np.sum(abs(fn(b)-fn(a)))),
                 'next_field_absolute':float(np.sum(abs(fn(b)))),
                 'relative_L1':float(np.sum(abs(fn(b)-fn(a)))/np.sum(abs(fn(b))))}
            for key,fn in transformations.items()}

def relative_metrics(a,b):
    d=b-a
    base=float(np.sum(np.abs(b)))
    same_sign=((a>=0)==(b>=0))
    nontrivial=(np.maximum(abs(a),abs(b))>1e-8)
    flips=~same_sign
    weighted_flip=float(np.sum(np.maximum(abs(a[flips]),abs(b[flips]))))
    azimuthal_residual=d-np.mean(d,axis=3,keepdims=True)
    return {'difference':signed_stats(d),
            'fine_L1_relative_to_next_L1':float(np.sum(abs(d))/base),
            'fine_L2_relative_to_next_L2':float(np.linalg.norm(d.ravel())/np.linalg.norm(b.ravel())),
            'cosine_similarity':float(np.dot(a.ravel(),b.ravel())/(
                np.linalg.norm(a.ravel())*np.linalg.norm(b.ravel()))),
            'sign_agreement_all_fraction':float(np.mean(same_sign)),
            'sign_flip_count':int(np.sum(flips)),
            'sign_flip_weight_relative_to_next_L1':weighted_flip/base,
            'sign_agreement_nontrivial_fraction':float(np.mean(same_sign[nontrivial]))
                 if np.any(nontrivial) else None,
            'azimuthal_residual_fraction_squared_L2':float(
                np.linalg.norm(azimuthal_residual)**2/np.linalg.norm(d)**2),
            'azimuthal_cancellation_fraction_L1':float(
                1.-np.sum(abs(np.sum(d,axis=3)))/np.sum(abs(d))),
            'coarsened_L1_difference':coarse_stats(d),
            'coarsened_relative_L1':coarse_relative(a,b),
            'absolute_share_polar_mu0_9':float(np.sum(abs(d[:,:, [0,9],:]))/np.sum(abs(d))),
            'absolute_share_r0_3':float(np.sum(abs(d[:,:4,:,:]))/np.sum(abs(d))),
            'absolute_share_last6_steps':float(np.sum(abs(d[30:]))/np.sum(abs(d))),
            'abs_by_time':list(map(float,np.sum(abs(d),axis=(1,2,3)))),
            'signed_by_time':list(map(float,np.sum(d,axis=(1,2,3)))),
            'abs_by_latitude':list(map(float,np.sum(abs(d),axis=(0,1,3)))),
            'signed_by_latitude':list(map(float,np.sum(d,axis=(0,1,3)))),
            'abs_by_radius':list(map(float,np.sum(abs(d),axis=(0,2,3)))),
            'signed_by_radius':list(map(float,np.sum(d,axis=(0,2,3)))),
            'components':{k:{'signed_change':float(np.sum(bv-av)),
                           'absolute_change':float(np.sum(abs(bv-av)))}
                          for k,(av,bv) in []},
           }

def volume_partition_metrics(a,b):
    """Check bin assignment on geometrically identical domains, one time step."""
    a=a[0]
    b=b[0]
    signed_a=float(np.sum(a))
    signed_b=float(np.sum(b))
    return {'geometry_volume_m3_M_old':signed_a,
            'geometry_volume_m3_M_new':signed_b,
            'relative_global_volume_difference':float(abs(signed_b-signed_a)/signed_b),
            'relative_binwise_volume_L1':float(np.sum(abs(b-a))/np.sum(b)),
            'relative_phi_integrated_volume_L1':float(
                np.sum(abs(np.sum(b-a,axis=2)))/np.sum(b)),
            'binwise_volume_difference_m3':float(np.sum(abs(b-a)))}

def direction_cosine(a,b):
    return float(np.dot(a.ravel(),b.ravel())/
                 (np.linalg.norm(a.ravel())*np.linalg.norm(b.ravel())))

def main():
    manifests={};data={};bounds={}
    for tag in SOURCES:
        manifests[tag],data[tag],bounds[tag]=get(tag)
        print('P10PR_SOURCE_PASS',tag,
              manifests[tag]['independent_4d']['jpeak_derivative_per_m'],flush=True)
    first=bounds['M17']
    for tag in list(SOURCES)[1:]:
        need(first.keys()==bounds[tag].keys(),'4D keys mismatch '+tag)
        need(all(all(abs(a-b)<1e-12 for a,b in zip(first[k],bounds[tag][k]))
                 for k in first),'4D spatial/temporal bounds mismatch '+tag)
    per_mesh={tag:{field:signed_stats(v) for field,v in columns.items()}
              for tag,columns in data.items()}
    pairs={}
    tags=list(SOURCES)
    for old,new in zip(tags,tags[1:]):
        row=relative_metrics(data[old]['total_per_m'],data[new]['total_per_m'])
        row['components']={field:{'signed_change':float(np.sum(data[new][field]-data[old][field])),
                                  'absolute_change':float(np.sum(abs(data[new][field]-data[old][field])))}
                           for field in FIELDS}
        row['volume_bin_partition']={field:volume_partition_metrics(data[old][field],data[new][field])
                for field in ('mechanical_volume_m3','thermal_volume_m3')}
        need(abs(row['difference']['signed']-(per_mesh[new]['total_per_m']['signed']-
                 per_mesh[old]['total_per_m']['signed']))<1e-10,'pair signed closure')
        row['signed_cancellation_factor']=row['difference']['absolute']/abs(row['difference']['signed'])
        pairs[f'{old}_{new}']=row
        print('P10PR_PAIR',old,new,'signed',row['difference']['signed'],
              'L1',row['difference']['absolute'],
              'L1rel',row['fine_L1_relative_to_next_L1'],
              'L2rel',row['fine_L2_relative_to_next_L2'],
              'cosine',row['cosine_similarity'],flush=True)
    # A positive cosine between successive differences indicates a persistent
    # refinement trend; negative fine-bin cosine is compatible with sampling
    # oscillations, but by itself does not prove their cause.
    for first,second in zip(list(pairs),list(pairs)[1:]):
        a,b=first.split('_')
        c=second.split('_')[1]
        need(b==second.split('_')[0],'pair continuity')
        d_prev=data[b]['total_per_m']-data[a]['total_per_m']
        d_next=data[c]['total_per_m']-data[b]['total_per_m']
        pairs[second]['previous_difference_direction_cosine']={
            'full_43200':direction_cosine(d_prev,d_next),
            'phi_integrated_3600':direction_cosine(
                np.sum(d_prev,axis=3),np.sum(d_next,axis=3))}
    # All positive/negative values of each actual mesh, distinct from differences.
    report={'protocol':'P10PR_FIVE_REAL_MESHES_SIGNED4D_CONVERGENCE_READ_ONLY',
            'status':'PASS_5MESHES_4D_GRID_CRC_SHA_AND_CLOSURE',
            'source_zip_sha256':{tag:SOURCE[2] for tag,SOURCE in SOURCES.items()},
            'grid':{'shape':SHAPE,'count':43200,'identical_bins':True},
            'per_mesh':per_mesh,'pairs':pairs,
            'note':'Values are bin-integrated contributions in m^-1; positive/negative'
                ' differences may cancel even when actual contributions have same sign.'}
    (OUTPUT_DIR/'P10PR_FIVE_MESHES_SIGNED4D_CONVERGENCE.json').write_text(
        json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

if __name__=='__main__':main()
