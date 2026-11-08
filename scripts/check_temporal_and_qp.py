#!/usr/bin/env python3
"""Stage3D06 independent, stdlib-only EDV time/peak diagnostic audit.
Reads LOCAL_RUNS generated on Windows/Qt Creator. Does not modify simulation results.
"""
import argparse, csv, math, pathlib, json, sys

PSI_AT_ZERO = 3 * (1e-3 / 2)**2  # smooth tensile spectral functional at sigma=0

def load_csv(file):
    with open(file, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def valid_series(folder, dt, tfinal, require_complete=True):
    path = folder / 'time_series.csv'
    if not path.is_file(): return None
    rows = load_csv(path)
    times = {}
    for row in rows:
        t = int(float(row['time_s']))
        if t in times:
            a=times[t]
            # duplicate lines after resume are acceptable only when physically identical
            for field in ('Psi6', 'PsiOmega', 'maxS1_MPa'):
                x,y=float(a[field]),float(row[field])
                if not math.isclose(x,y,rel_tol=1e-10,abs_tol=1e-12):
                    raise ValueError(f'Conflicting duplicate at t={t}: {field}, {x} vs {y}')
        else: times[t] = row
    if not times: return None
    times = {t:v for t,v in times.items() if t<=tfinal}
    expected = list(range(dt, tfinal+1,dt))
    got = sorted(times)
    if not got: return None
    if require_complete and got != expected:
        raise ValueError(f'{path}: incomplete or unexpected time grid: have {len(got)} times ending at {got[-1]}; expected {len(expected)} to {tfinal}.')
    if got!=list(range(dt,got[-1]+1,dt)):
        raise ValueError(f'{path}: not a uniform time grid dt={dt}')
    vals = [times[t] for t in got]
    for row in vals:
        if int(float(row['dt_s']))!=dt:raise ValueError(f'{path}: nonconforming dt')
        if float(row['residual_rel'])>=1e-6:raise ValueError(f'{path}: equilibrium residual unexpectedly large')
        if any(not math.isfinite(float(row[key])) for key in ('Psi6','PsiOmega','maxS1_MPa')):raise ValueError(f'{path}: nonfinite data')
    return times

def integrate(times,key):
    tprev=0.;fprev=PSI_AT_ZERO;area=0.
    for t,row in sorted(times.items()):
        f=float(row[key]);area+=(t-tprev)*(fprev+f)/2;tprev=t;fprev=f
    return area/tprev

def read_peak(folder, times):
    path=folder/'max_location.csv';
    if not path.is_file(): return None
    rec={}
    for r in load_csv(path):
        t=int(float(r['time_s']));s=float(r['sigma1_QP_max_MPa']);
        if t in rec:
            if not math.isclose(float(rec[t]['sigma1_QP_max_MPa']),s,rel_tol=1e-10,abs_tol=1e-12):
                raise ValueError('Inconsistent repeated max location record at t='+str(t))
        else:rec[t]=r
    for t,row in times.items():
        if t not in rec:raise ValueError(f'{path}: missing location for t={t}')
        qp=float(rec[t]['sigma1_QP_max_MPa']); csv_max=float(row['maxS1_MPa'])
        if not math.isclose(qp,csv_max,rel_tol=2e-10,abs_tol=1e-12):
            raise ValueError(f'QP peak != solver CSV maximum at time {t}')
        if float(rec[t]['distance_to_pore_surface_mm']) < -0.005:
            raise ValueError('Location lies inside cavity by >0.005 mm: geometry mismatch')
    return rec

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default='.',type=pathlib.Path,help='project root containing LOCAL_RUNS')
    p.add_argument('--mesh',default='H0',choices=['H0','H1','H2'])
    p.add_argument('--modulus',default='VAR',choices=['VAR','CONST'])
    p.add_argument('--dt',nargs='+',type=int,default=[300,150,75])
    p.add_argument('--tfinal',type=int,default=3600)
    p.add_argument('--out',type=pathlib.Path)
    a=p.parse_args()
    result=[];detail=[]
    for dt in a.dt:
        folder=a.root/'LOCAL_RUNS'/f'{a.mesh}_dt{dt}_q3'/'mechanics'/('EDV_'+a.modulus)
        if not (folder/'time_series.csv').is_file() and a.mesh=='H0' and dt==300 and a.modulus=='VAR':
            archived=a.root/'results'/'G06_H0_dt300'/'EDV_VAR'
            if (archived/'time_series.csv').is_file():folder=archived
        try:times=valid_series(folder,dt,a.tfinal)
        except ValueError as e:
            print('INVALID:',e,file=sys.stderr);return 2
        if times is None:
            print('NOT RUN:',folder);continue
        try:peak=read_peak(folder,times)
        except ValueError as e:
            print('INVALID:',e,file=sys.stderr);return 2
        tail=times[a.tfinal]
        r={'mesh':a.mesh,'modulus':a.modulus,'dt_s':dt,'n_steps':len(times),
           'maxS1_at_final_MPa':float(tail['maxS1_MPa']),
           'Phi6_at_final':float(tail['Psi6']),
           'j6':integrate(times,'Psi6'),'jOmega':integrate(times,'PsiOmega'),
           'max_equilibrium_rel':max(float(v['residual_rel']) for v in times.values()),
           'max_location_checked':bool(peak)}
        if peak:
            loc=peak[a.tfinal];r['max_gap_to_pore_mm']=float(loc['distance_to_pore_surface_mm']);r['max_elem_0based']=int(loc['element_id_0based'])
        result.append(r)
        print(f'dt={dt:4d} seconds: j6={r["j6"]:.12g}, sigma1_max={r["maxS1_at_final_MPa"]:.9g} MPa, residual<={r["max_equilibrium_rel"]:.3g}, qp_check={bool(peak)}')
        for t,row in sorted(times.items()):detail.append({'dt_s':dt,'time_s':t,'Phi6':float(row['Psi6']),'PhiOmega':float(row['PsiOmega']),'maxS1_MPa':float(row['maxS1_MPa'])})
    if not result:
        print('No completed series');return 1
    result.sort(key=lambda r:r['dt_s'],reverse=True)
    keys=('j6','jOmega','Phi6_at_final','maxS1_at_final_MPa')
    comparison=[]
    for lhs,rhs in zip(result,result[1:]):
        d={'dt_coarse_s':lhs['dt_s'],'dt_fine_s':rhs['dt_s']}
        for key in keys:
            err=lhs[key]-rhs[key];d['difference_'+key]=err;d['relative_difference_'+key+'_pct']=100*err/rhs[key] if rhs[key] else None
        comparison.append(d)
    # Empirical order is meaningful only for three nested refinements of a common final time
    order={}
    if len(result)>=3:
        for key in keys:
            a0,a1,a2=[r[key] for r in result[:3]]
            if result[0]['dt_s']==2*result[1]['dt_s']==4*result[2]['dt_s'] and (a0-a1)*(a1-a2)>0 and abs(a1-a2)>1e-14:
                order[key]=math.log2(abs((a0-a1)/(a1-a2)))
            else:order[key]=None
    print('Comparisons:',comparison)
    if order:print('Estimated orders (null means not determinable):',order)
    if a.out:
        a.out.mkdir(parents=True,exist_ok=True)
        with open(a.out/'temporal_summary.json','w',encoding='utf-8') as f:
            json.dump({'records':result,'differences':comparison,'orders':order,'PSI_at_t0':PSI_AT_ZERO},f,indent=2,ensure_ascii=False)
        with open(a.out/'temporal_summary.csv','w',newline='',encoding='utf-8') as f:
            dw=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for row in result for k in row)));dw.writeheader();dw.writerows(result)
        with open(a.out/'temporal_history.csv','w',newline='',encoding='utf-8') as f:
            dw=csv.DictWriter(f,fieldnames=list(detail[0]));dw.writeheader();dw.writerows(detail)
    return 0

if __name__=='__main__':sys.exit(main())
