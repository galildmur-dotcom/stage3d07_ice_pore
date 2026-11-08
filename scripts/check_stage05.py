#!/usr/bin/env python3
"""Independent stdlib-only scalar bisection readback of G05 E/ED/EDV constitutive point CSV.
Does not invoke C++ code, and uses MPa as the primary scalar solve unit.
"""
import argparse, csv, math, json, pathlib
p=argparse.ArgumentParser();p.add_argument('--results',default='results/EDV_material'); args=p.parse_args()
base=pathlib.Path(args.results)
Eref=9.5e9; nu=.35; alpha=149e-6/3; m=3.1
Kd=1.2e-3/1e6; a=1.5*Kd
KN_MPa=2.56e-7; Q=66900; Rg=8.31446261815324
EPS=(.0012,-.0007,.00032,.00068,-.00027,.00018)
weights=(1,1,1,2,2,2)
def dprod(x,y):return sum(w*u*v for w,u,v in zip(weights,x,y))
def root_bisect(x0,theta):
    lo,hi=0.,x0
    if x0==0 or theta==0:return x0
    for _ in range(90):
        mid=(lo+hi)/2
        if mid+theta*mid**m>x0:hi=mid
        else:lo=mid
    return (lo+hi)/2

def update(ed,ev,mode,model,t,dt):
    TK=253.15-3*(1-math.exp(-t/300))
    TC=TK-273.15
    E=Eref if mode=='CONST' else Eref*(8.93-.012*TC)/9.17
    G=E/(2*(1+nu));K=E/(3*(1-2*nu))
    Ar=math.exp(-Q/Rg*(1/TK-1/263.15))
    b=dt*1.5e-3*Ar if model!='E' else 0.
    # viscous scalar expressed using MPa consistently with MPa^-m coefficient
    KN=KN_MPa*Ar if model=='EDV' else 0.
    A=1/(2*G)+b*a/(1+b)
    d=[EPS[i]-(sum(EPS[:3])/3 if i<3 else 0) for i in range(6)]
    rhs=[d[i]-ev[i]-ed[i]/(1+b) for i in range(6)]
    qtrial=math.sqrt(1.5*dprod(rhs,rhs))/A/1e6
    theta=dt*1.5*KN/(1e6*A)
    qbar=root_bisect(qtrial,theta)
    factor=qbar/qtrial if qtrial>0 else 1.
    s=[x/A*factor for x in rhs]
    newed=[(ed[i]+b*a*s[i])/(1+b) for i in range(6)]
    newev=[ev[i]+dt*1.5*KN*(qbar**(m-1))*s[i]/1e6 for i in range(6)]
    sigma=[s[i]+(K*(sum(EPS[:3])-3*alpha*(TK-253.15)) if i<3 else 0) for i in range(6)]
    return newed,newev,sigma,qbar

def check_csv(csv_file):
    maxerr=0.;groups={};n=0
    with open(csv_file,newline='') as f:
        reader=csv.DictReader(f)
        for row in reader:
            mode=row['mode'];model=row.get('model','EDV');t=float(row['time_s']);dt=0 if t==0 else 15.
            key=(model,mode)
            if key not in groups:groups[key]=([0.]*6,[0.]*6)
            ed,ev=groups[key]
            ed,ev,sig,q=update(ed,ev,mode,model,t,dt)
            groups[key]=ed,ev
            for value,target in [(float(row['sigma_xy_MPa']),sig[3]/1e6),(float(row['q_MPa']),q),
                                 (float(row['e_d_xy']),ed[3]),(float(row['e_v_xy']),ev[3])]:
                rel=abs(value-target)/max(1e-8,abs(target),abs(value))
                maxerr=max(rel,maxerr)
                if rel>2e-10:raise ValueError(f'{csv_file.name}: {key}, {t}s, {value} vs {target} (rel={rel})')
            n+=1
    return {'rows':n,'groups':len(groups),'max_relative_error':maxerr}
result={}
for filename in ('G05_point_cooling.csv','G05_E_ED_EDV_pairs.csv'):
    result[filename]=check_csv(base/filename)
# Additional readback on time convergence data (monotonic error decrease)
with open(base/'G05_time_convergence.csv',newline='') as f: rows=list(csv.DictReader(f))
errs=[float(r['relative_stress_error_against_8192']) for r in rows[:-1]]
if not all(x>y for x,y in zip(errs,errs[1:])):raise ValueError('time convergence is not monotone')
result['G05_time_convergence.csv']={'rows':len(rows),'monotone':True,'coarse_relative':errs[0],'refined_relative':errs[-1]}
(base/'G05_independent_readback.json').write_text(json.dumps({'status':'PASS',**result},indent=2)+'\n')
print(json.dumps({'status':'PASS',**result},indent=2))
