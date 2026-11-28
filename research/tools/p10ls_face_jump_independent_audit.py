"""Independently check complete 36x25 P1/P2 reconstructed M9 face-jump CSV."""
import csv
import math
from pathlib import Path

NAME='P10LS_FACE_JUMP_4D.csv'
FIELDS=['mesh','step','time_end_s','recovery_degree','radial_bin','mu_bin','phi_bin',
        'face_count','stress_frobenius_mean_pa','stress_frobenius_rms_pa',
        'stress_frobenius_max_pa','traction_mean_pa','traction_rms_pa',
        'traction_max_pa','shape_jvp_mean_pa_per_m','shape_jvp_rms_pa_per_m',
        'shape_jvp_max_pa_per_m']

def need(condition,message):
    if not condition:raise RuntimeError('P10LS_FACE_QA_STOP '+message)

def audit(directory,mesh='M9',steps=36,dt=25):
    p=Path(directory)/NAME
    need(p.is_file(),'missing face-jump CSV')
    counts={};degree_stats={1:[],2:[]};seen=set()
    with p.open(newline='',encoding='utf8') as file:
        rows=csv.DictReader(file)
        need(rows.fieldnames==FIELDS,'face CSV schema changed')
        for row in rows:
            s,d,ir,im,ip=(int(row[x]) for x in
                 ('step','recovery_degree','radial_bin','mu_bin','phi_bin'))
            need(row['mesh']==mesh and 1<=s<=steps and d in (1,2) and
                 0<=ir<10 and 0<=im<10 and 0<=ip<12,'coordinate invalid')
            need(int(row['time_end_s'])==s*dt,'time stamp drift')
            key=(s,d,ir,im,ip)
            need(key not in seen,'duplicate face bin')
            seen.add(key)
            n=int(row['face_count'])
            need(n>=0,'negative face count')
            counts[key]=n
            metrics=[float(row[k]) for k in FIELDS[8:]]
            need(all(math.isfinite(v) and v>=0 for v in metrics),'nonfinite/negative jump')
            for a,b,c in ((0,1,2),(3,4,5),(6,7,8)):
                need(metrics[a]<=metrics[b]+1e-8*max(1.,metrics[b]) and
                     metrics[b]<=metrics[c]+1e-8*max(1.,metrics[c]),
                     'invalid mean/RMS/max ordering')
            if n==0:need(all(v==0. for v in metrics),'unsupported bin populated')
            if ir==0:need(n==0,'unexpected first-shell face centroid')
            degree_stats[d].append((s,ir,im,ip,n,metrics))
    need(len(seen)==steps*2*1200,'missing face rows')
    counted={}
    for s in range(1,steps+1):
        a=b=0
        for ir in range(10):
            for im in range(10):
                for ip in range(12):
                    ka=(s,1,ir,im,ip);kb=(s,2,ir,im,ip)
                    need(counts[ka]==counts[kb],'P1/P2 physical face support differs')
                    a+=counts[ka];b+=counts[kb]
        need(a==b and 0<a<=25470,'invalid B6 face support')
        counted[str(s)]=a
    need(len(set(counted.values()))==1,'static B6 face count changed across steps')
    return {'protocol':'P10LS_INDEPENDENT_P1_P2_REAL_M9_FACE_JUMP_QA',
            'status':'P10LS_FACE_CSV_INDEPENDENT_PASS',
            'mesh':mesh,'steps':steps,'dt_s':dt,'rows':len(seen),
            'face_pairs_per_step':counted['1'],
            'first_0_20um_face_centroid_support':0,
            'support_equal_P1_P2_each_4d_bin':True,
            'support_static_over_time':True}
