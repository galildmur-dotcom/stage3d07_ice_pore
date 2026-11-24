#!/usr/bin/env python3
"""P10IU: positive C2 spatial continuation of P10IT M2/M3 source, no Gmsh/FEM."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np

C = np.array([0., 0., .03])
R = .001
TARGET = .65
PARTS = ('radial_bin', 'mu_bin', 'phi_bin')


def rows(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def s5(x):
    z = np.clip(x, 0., 1.)
    return z**3*(10+z*(-15+6*z))


class Field:
    def __init__(self, old_rows, new_rows, beta):
        self.beta = beta
        old = {tuple(int(r[p]) for p in PARTS): r for r in old_rows}
        new = {tuple(int(r[p]) for p in PARTS): r for r in new_rows}
        assert len(old) == len(new) == 1200 and set(old) == set(new)
        self.keys = sorted(old)
        score = np.array([float(new[k]['beta_'+str(beta)+'_score']) for k in self.keys])
        assert np.isfinite(score).all() and score.min() >= 0 and score.max() > 0
        self.amp = score/score.max()
        th = np.array([float(old[k]['theta_mid_rad']) for k in self.keys])
        ph = np.array([float(old[k]['phi_mid_rad']) for k in self.keys])
        self.xyz = np.stack([np.sin(th)*np.cos(ph),np.sin(th)*np.sin(ph),np.cos(th)], axis=1)
        dd = []
        for k in self.keys:
            lo = float(old[k]['d_lower_mm'])
            hi = old[k]['d_upper_mm']
            dd.append(.5*(lo+float(hi)) if hi else lo)
        self.dmm = np.array(dd)
        self.u = np.log1p(self.dmm/.05)
        self.qp = np.array([int(new[k]['M3_QP']) for k in self.keys])
        assert np.all(self.qp>0)
        self.center_points = C+(R+.001*self.dmm[:,None])*self.xyz
        raw = np.array([self.raw(p) for p in self.center_points])
        self.raw_max = raw.max()
        assert self.raw_max > 0
        self.center_kappa = s5(raw/self.raw_max)

    def raw(self, p):
        rel = p-C
        radius = np.linalg.norm(rel)
        assert radius>=R*(1-1e-10)
        direction = rel/radius
        u = math.log1p(max(0.,(radius-R)*1000)/.05)
        rho = np.sqrt(((self.u-u)/.75)**2 + ((self.xyz-direction)**2).sum(axis=1)/.60**2)
        active = rho < 1
        if not np.any(active):return 0.
        q = rho[active]
        w = (1-q)**4*(4*q+1)
        return float(w@self.amp[active]/(w.sum()+1e-12))

    def kappa(self, p):
        return float(s5(self.raw(p)/self.raw_max))

    @staticmethod
    def taper(dmm, mu):
        return float(s5((abs(mu)-.6)/.2) * (1-s5((dmm-.3)/.7)))

    def evaluate(self, p, logbase, dn, ds):
        rel = p-C
        radius = float(np.linalg.norm(rel))
        if radius<R-1e-10:raise ValueError('outside ice domain')
        mu = rel[2]/radius
        dmm=max((radius-R)*1000,0)
        k = self.kappa(p)
        w = self.taper(dmm,mu)
        correction = dn if mu>=0 else ds
        h = math.exp(-logbase*k - correction*w)
        return k,w,h


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--old',type=Path,required=True)
    ap.add_argument('--new',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    old=rows(args.old);new=rows(args.new)
    fields={b:Field(old,new,b) for b in ('0','0.1','0.25')}
    f=fields['0.1']
    logbase=-math.log(TARGET)/3
    sides={}
    for side,idx in (('north',9),('south',0)):
        selected=np.array([k[0]<=4 and k[1]==idx for k in f.keys])
        w=f.qp[selected].astype(float)
        k=f.center_kappa[selected]
        taper=np.array([f.taper(d, xyz[2]) for d,xyz in zip(f.dmm[selected],f.xyz[selected])])
        def cube_proxy(patch):
            return float(np.average(np.exp(-3*(logbase*k+patch*taper)),weights=w))
        base=cube_proxy(0)
        low,high=0.,.7
        assert cube_proxy(high)<=TARGET
        for _ in range(55):
            mid=(low+high)/2
            if cube_proxy(mid)>TARGET:low=mid
            else:high=mid
        patch=(low+high)/2
        # Sensitivity interval: patch values for alternative hypothetical cube-proxy targets.
        variations={}
        for desired in (.50,.65,.75):
            lo,hi=0.,.7
            if base<=desired:
                variations[str(desired)]=0.
                continue
            for _ in range(55):
                mid=(lo+hi)/2
                if cube_proxy(mid)>desired:lo=mid
                else:hi=mid
            variations[str(desired)]=(lo+hi)/2
        sides[side]={'supported_bins':int(selected.sum()),'M3_QP':int(w.sum()),
            'qp_weighted_kappa':float(np.average(k,weights=w)),
            'qp_weighted_taper':float(np.average(taper,weights=w)),
            'unpatched_cube_proxy':base,
            'calibrated_patch_log_size':patch,
            'calibrated_cube_proxy':cube_proxy(patch),
            'patch_log_size_scenario_targets':variations,
            'patch_nominal_size_factor':math.exp(-patch),
            'NOTE':'All cube proxies are source-center geometry-only assumptions, not actual Tet10 Veff'}
    dn=sides['north']['calibrated_patch_log_size']
    ds=sides['south']['calibrated_patch_log_size']
    samples=[]
    for side,sign in (('north',1),('south',-1)):
        for dmm in (0.,.02,.05,.1,.25,.3,.5,.7,1.,2.,5.):
            for absmu in (.6,.7,.8,.95,1.):
                for phi in (0.,math.pi/2,math.pi-1e-6):
                    mu=sign*absmu
                    vec=np.array([math.sqrt(1-mu**2)*math.cos(phi),
                                  math.sqrt(1-mu**2)*math.sin(phi),mu])
                    p=C+(R+.001*dmm)*vec
                    k,w,h=f.evaluate(p,logbase,dn,ds)
                    samples.append({'side':side,'d_mm':dmm,'mu':mu,'phi':phi,
                        'kappa':k,'polar_taper':w,'M4_M3_size_proxy':h,'cube_proxy':h**3})
    # Periodicity is physical Cartesian equality; explicitly test seam and poles.
    max_seam=0.
    max_pole=0.
    for dmm in (0.,.02,.1,.5,2.):
        for mu in (-.95,-.8,-.6,.6,.8,.95):
            def point(phi):
                return C+(R+.001*dmm)*np.array([math.sqrt(1-mu**2)*math.cos(phi),
                                                math.sqrt(1-mu**2)*math.sin(phi),mu])
            a=f.evaluate(point(-math.pi),logbase,dn,ds)
            b=f.evaluate(point(math.pi),logbase,dn,ds)
            max_seam=max(max_seam,max(abs(x-y) for x,y in zip(a,b)))
        for sign in (-1,1):
            vals=[]
            for phi in (0.,.4,1.7,2.8):
                p=C+(R+.001*dmm)*np.array([0.,0.,sign])
                vals.append(f.evaluate(p,logbase,dn,ds))
            max_pole=max(max_pole,max(abs(x-y) for v in vals for x,y in zip(vals[0],v)))
    assert max_seam<1e-12 and max_pole<1e-12
    assert all(0<=r['kappa']<=1 and 0<r['M4_M3_size_proxy']<=1 for r in samples)
    qa={'protocol':'P10IU_C2_CONTINUOUS_3D_M4_SOURCE_ONLY',
        'status':'PASS_SOURCE_ONLY_NO_GMSH_NO_FEM',
        'P10IT_csv_sha256':sha(args.new),'P10HA_coordinate_reference_sha256':sha(args.old),
        'beta_primary':.1,'beta_diagnostics':[0.,.25],
        'source_1200_bins':len(f.keys),
        'continuation':'positive normalized compact Wendland C2 in log radial / Cartesian angular dimensions, S5 peak restoration',
        'max_raw_at_centers':float(f.raw_max),
        'center_kappa_stats_by_beta':{b:{'max':float(x.center_kappa.max()),
            'mean':float(x.center_kappa.mean()),'north_max':float(x.center_kappa[[k[1]==9 for k in x.keys]].max()),
            'south_max':float(x.center_kappa[[k[1]==0 for k in x.keys]].max())} for b,x in fields.items()},
        'nominal_target_cube_proxy':TARGET,'generic_log_size_delta':logbase,
        'north_south':sides,
        'samples_count':len(samples),'sample_kappa_range':[min(r['kappa'] for r in samples),max(r['kappa'] for r in samples)],
        'sample_size_ratio_range':[min(r['M4_M3_size_proxy'] for r in samples),max(r['M4_M3_size_proxy'] for r in samples)],
        'azimuth_seam_max_abs_difference':max_seam,
        'polar_exact_coordinate_max_abs_difference':max_pole,
        'c2_status':'analytical construction; numerical C2 derivative test not performed',
        'caveat':'No M4 Tet10 mesh. No actual D029 regional volume/quality acceptance. No FEM or temporal/spatial convergence claim.'}
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'P10IU_SOURCE_ONLY_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False)+'\n')
    with (args.out/'P10IU_SIZE_FIELD_SAMPLES.csv').open('w',newline='') as out:
        w=csv.DictWriter(out,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)
    print(json.dumps(qa,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
