"""Independent postrun audit of opt-in P10LG two-term signed4D sidecar."""
from __future__ import annotations
import csv
import math
from pathlib import Path

NAME='P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv'


def need(ok, message):
    if not ok:raise RuntimeError('P10LM_SPLIT_QA_STOP '+message)


def audit_split(directory, mesh='M9', steps=36, dt=25):
    directory=Path(directory)
    path=directory/NAME
    original=directory/'P10DD_SIGNED_R_THETA_PHI_T.csv'
    need(path.is_file() and original.is_file(),'missing split or reference CSV')
    expected=['mesh','step','time_end_s','radial_bin','mu_bin','phi_bin',
              'explicit_geometry_normalization_per_m','explicit_stress_chain_per_m',
              'explicit_sum_per_m']
    old={}
    with original.open(newline='',encoding='utf-8') as source:
        reader=csv.DictReader(source)
        need('mech_explicit_per_m' in (reader.fieldnames or []),'original schema changed')
        for row in reader:
            if row['region']!='VOLUME':continue
            key=(int(row['step']),int(row['radial_bin']),int(row['mu_bin']),int(row['phi_bin']))
            need(key not in old,'duplicate original bin')
            old[key]=float(row['mech_explicit_per_m'])
    need(len(old)==steps*1200,'original 4D bin count mismatch')
    seen=set()
    geometry=stress=explicit=0.
    n=0
    by_radial=[{'geometry':0.,'stress':0.,'explicit':0.} for _ in range(10)]
    by_pole=[{'geometry':0.,'stress':0.,'explicit':0.} for _ in range(3)]
    with path.open(newline='',encoding='utf-8') as source:
        reader=csv.DictReader(source)
        need(reader.fieldnames==expected,'split CSV schema mismatch')
        for row in reader:
            need(row['mesh']==mesh,'mesh name mismatch')
            step,ir,im,ip=(int(row[x]) for x in ('step','radial_bin','mu_bin','phi_bin'))
            need(1<=step<=steps and 0<=ir<10 and 0<=im<10 and 0<=ip<12,'invalid 4D coordinate')
            need(int(row['time_end_s'])==step*dt,'wrong time stamp')
            key=(step,ir,im,ip)
            need(key not in seen,'duplicate split bin')
            seen.add(key)
            g=float(row['explicit_geometry_normalization_per_m'])
            s=float(row['explicit_stress_chain_per_m'])
            x=float(row['explicit_sum_per_m'])
            y=old[key]
            need(all(map(math.isfinite,(g,s,x,y))),'nonfinite bin')
            # Floating-point closure uses the same absolute+scaled contract
            # but separately parses both independently emitted CSV files.
            tol=1e-10+1e-10*max(abs(g),abs(s),abs(x),abs(y))
            need(abs(g+s-x)<=tol and abs(x-y)<=tol,'signed per-bin closure')
            geometry+=g;stress+=s;explicit+=x
            n+=1
            for index, bucket in ((ir,by_radial),(0 if im==0 else 2 if im==9 else 1,by_pole)):
                bucket[index]['geometry']+=g
                bucket[index]['stress']+=s
                bucket[index]['explicit']+=x
    need(n==steps*1200,'split row count mismatch')
    need(len(seen)==len(old),'missing 4D bins')
    need(abs((geometry+stress)-explicit)<=1e-9+1e-10*abs(explicit),'global split closure')
    return {'protocol':'P10LM_INDEPENDENT_TWO_TERM_SIGNED4D_V1',
            'status':'P10LM_TWO_TERM_PHYSICAL_CSV_QA_PASS',
            'mesh':mesh,'steps':steps,'dt_s':dt,'rows':n,
            'geometry_per_m':geometry,'stress_per_m':stress,
            'explicit_per_m':explicit,
            'radial_10_bins':by_radial,
            'latitude_groups_mu_bin_0_south_1to8_mid_9_north':by_pole,
            'closure':'per-bin parsed P10LG vs separate P10DD and all-step PASS'}
