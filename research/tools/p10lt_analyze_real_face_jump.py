#!/usr/bin/env python3
"""Independent weighted analysis of P10LS face-bin summary (no FEM)."""
import csv, json, math, sys
from collections import defaultdict
from pathlib import Path

def main():
    folder=Path(sys.argv[1])
    groups=defaultdict(lambda: {'n':0,'stress_mean':0.,'stress_sq':0.,'stress_max':0.,
        'traction_mean':0.,'traction_sq':0.,'traction_max':0.,
        'jvp_mean':0.,'jvp_sq':0.,'jvp_max':0.})
    with (folder/'P10LS_FACE_JUMP_4D.csv').open(newline='') as fh:
        for r in csv.DictReader(fh):
            n=int(r['face_count'])
            if not n:continue
            d=int(r['recovery_degree']);step=int(r['step']);rad=int(r['radial_bin']);mu=int(r['mu_bin'])
            # Polar caps from accepted P10LM convention: mu_bin 0 south / 9 north.
            polar='south' if mu==0 else ('north' if mu==9 else 'mid')
            for key in [('all',d),('step',d,step),('radial',d,rad),('polar',d,polar),
                        ('radial_polar',d,rad,polar)]:
                x=groups[key];x['n']+=n
                for prefix,col in [('stress','stress_frobenius'),('traction','traction'),('jvp','shape_jvp')]:
                    unit='_pa_per_m' if prefix=='jvp' else '_pa'
                    m=float(r[col+'_mean'+unit]);q=float(r[col+'_rms'+unit]);z=float(r[col+'_max'+unit])
                    x[prefix+'_mean']+=n*m
                    x[prefix+'_sq']+=n*q*q
                    x[prefix+'_max']=max(x[prefix+'_max'],z)
    def summarize(x):
        n=x['n']
        return {'faces_accumulated':n,**{k+'_'+typ:(x[k+'_mean']/n if typ=='mean' else
                math.sqrt(x[k+'_sq']/n) if typ=='rms' else x[k+'_max']) for k in
                ('stress','traction','jvp') for typ in ('mean','rms','max')}}
    obj={'protocol':'P10LT_P10LS_FACE_WEIGHTED_ANALYSIS_V1',
         'definitions':'face-count-weighted global mean and RMS from bin means/RMS; max over bins; each step counted once',
         'all':{str(k[1]):summarize(v) for k,v in groups.items() if k[0]=='all'},
         'time':{str(k[1])+'_'+str(k[2]):summarize(v) for k,v in groups.items() if k[0]=='step'},
         'radial':{str(k[1])+'_'+str(k[2]):summarize(v) for k,v in groups.items() if k[0]=='radial'},
         'polar':{str(k[1])+'_'+k[2]:summarize(v) for k,v in groups.items() if k[0]=='polar'},
         'radial_polar':{str(k[1])+'_'+str(k[2])+'_'+k[3]:summarize(v) for k,v in groups.items() if k[0]=='radial_polar'}}
    dest=folder/'P10LT_P10LS_FACE_WEIGHTED_ANALYSIS.json'
    dest.write_text(json.dumps(obj,indent=2)+'\n')
    print(json.dumps({'all':obj['all'],'polar':obj['polar'],'radial':obj['radial'],
                     'time_first_last':{str(d):{str(t):obj['time'][str(d)+'_'+str(t)] for t in (1,18,36)} for d in (1,2)}},indent=2))

if __name__=='__main__':main()
