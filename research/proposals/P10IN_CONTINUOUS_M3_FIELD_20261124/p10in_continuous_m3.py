#!/usr/bin/env python3
"""P10IN: source-only C2 3D size multiplier from approved P10IM beta=0.10.

No Gmsh API, no mesh writes, no FEM. Original CAD is not modified.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np

C=np.array([0.,0.,.03])
R=.001
TARGET=.65
WENDLAND_EPS=1.e-12
EXPECTED_M2='d1ec65ffcc6e8fac7da925ecd66bbb9508450cf2ea837521442f57f45674c78b'
EXPECTED_OLD='98bc99af9783e14f7800f08ecd04fc6bee8093d0490b359e3a024f4c6c4566a3'
EXPECTED_NEW='be0a64d372f6520704bbc438247739bdeeda681930a879dff613c9b129e7b919'
CALIBRATION={
    'north':{'P10ID_over_M1':.9484586,'P10IE_over_M1':.602401,'P10IE_extra_log_size':.1390288217133428},
    'south':{'P10ID_over_M1':.8868231,'P10IE_over_M1':.703376,'P10IE_extra_log_size':.11663130879448864}}


def csv_rows(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as inp:
        return list(csv.DictReader(inp))


def smoothstep5(t):
    x=np.clip(t,0.,1.)
    return x**3*(10.+x*(-15.+6.*x))


class ContinuousKappa:
    def __init__(self,old_source,new_source):
        old=csv_rows(old_source);new=csv_rows(new_source)
        if len(old)!=1200 or len(new)!=1200:
            raise ValueError('requires exactly 1200 source bins')
        idx=lambda r:(int(r['radial_bin']),int(r['mu_bin']),int(r['phi_bin']))
        mapping={idx(r):r for r in old}
        if len(mapping)!=1200:raise ValueError('duplicate old bins')
        old=[mapping[idx(r)] for r in new]
        score=np.array([float(r['beta_0p1_score']) for r in new])
        if not np.all(np.isfinite(score)) or np.min(score)<0 or np.max(score)<=0:
            raise ValueError('invalid new source score')
        self.amplitude=score/np.max(score)
        theta=np.array([float(r['theta_mid_rad']) for r in old])
        phi=np.array([float(r['phi_mid_rad']) for r in old])
        self.directions=np.column_stack((np.sin(theta)*np.cos(phi),
                                         np.sin(theta)*np.sin(phi),np.cos(theta)))
        d=[]
        for r in old:
            lower=float(r['d_lower_mm'])
            upper=r['d_upper_mm']
            d.append((lower+float(upper))*.5 if upper else lower)
        self.u=np.log1p(np.array(d)/.05)
        self.keys=[idx(r) for r in new]
        self.weights={}
        # A second normalized Shepard pass suppresses the extrema. Recover a
        # bounded C2 peak on the source centers with a quintic map, rather
        # than over-driving the unverified native Gmsh size coefficient.
        raw_centers=[]
        for ud,direction in zip(self.u,self.directions):
            p=C+(R+.001*(math.expm1(ud)*.05))*direction
            raw_centers.append(self.raw_kappa(p))
        self.raw_center_max=max(raw_centers)
        if self.raw_center_max<=0:raise ValueError('zero interpolated maxima')
        self.slope={}
        for side,q in CALIBRATION.items():
            slope=math.log(q['P10ID_over_M1']/q['P10IE_over_M1'])/q['P10IE_extra_log_size']
            if slope<=0:raise ValueError('nonpositive empirical volume sensitivity')
            self.slope[side]=slope
        # The alpha=0.1 source hypothesis is approved, not yet the measured M3.

    def raw_kappa(self,point):
        p=np.asarray(point,dtype=float)
        rel=p-C
        radius=np.linalg.norm(rel)
        if radius<1e-15:return 0.
        direction=rel/radius
        u=math.log1p(max(0.,(radius-R)*1000.)/.05)
        dist=np.sqrt(((self.u-u)/.75)**2+
                     np.sum((self.directions-direction)**2,axis=1)/(.60**2))
        active=dist<1
        if not np.any(active):return 0.
        t=dist[active]
        weights=(1-t)**4*(4*t+1)
        return float(weights@self.amplitude[active]/(weights.sum()+WENDLAND_EPS))

    def kappa(self,point):
        """C2 bounded smoothstep after source-center peak restoration."""
        return float(smoothstep5(self.raw_kappa(point)/self.raw_center_max))

    def polar_weight(self,dmm,mu):
        # C2 patch (P10IE used C1); full within d<=.3mm, |mu|>=.8.
        return float(smoothstep5((abs(mu)-.6)/.2)*
                     (1-smoothstep5((dmm-.3)/.7)))

    def evaluate(self,p,delta_n,delta_s,delta_generic):
        rel=np.asarray(p,dtype=float)-C
        rad=np.linalg.norm(rel)
        if rad<R and rad>1e-15:
            rel=rel*R/rad;rad=R
        if rad<1e-15:return (0.,1.,0.)
        mu=float(rel[2]/rad)
        dmm=max((rad-R)*1000.,0.)
        k=self.kappa(C+rel)
        w=self.polar_weight(dmm,mu)
        local=delta_n if mu>=0 else delta_s
        hratio=math.exp(-k*delta_generic-w*local)
        return k,hratio,w


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--old-kappa',type=Path,required=True)
    p.add_argument('--new-kappa',type=Path,required=True)
    p.add_argument('--m2-msh',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if hashlib.sha256(a.m2_msh.read_bytes()).hexdigest()!=EXPECTED_M2:
        raise RuntimeError('M2 source mesh SHA mismatch; no M3 action')
    for file,expected in ((a.old_kappa,EXPECTED_OLD),(a.new_kappa,EXPECTED_NEW)):
        if hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
            raise RuntimeError('kappa source SHA mismatch; no M3 action')
    source=ContinuousKappa(a.old_kappa,a.new_kappa)
    # Evaluate strictly physical supported source centers d<=0.3mm, polar.
    polar={}
    center=[]
    for u,d,k in zip(source.u,source.directions,source.keys):
        point=C+(R+.001*(math.expm1(u)*.05))*d
        kap=source.kappa(point)
        center.append((k,point,kap))
    delta_generic=-math.log(TARGET)/3
    m3_rows=csv_rows(a.new_kappa)
    for side,bin_idx in (('north',9),('south',0)):
        candidates=[(k,point,kap) for k,point,kap in center
                    if k[1]==bin_idx and k[0]<=3 and (np.linalg.norm(point-C)-R)*1000<=.3]
        highest=max(candidates,key=lambda x:x[2])
        kmax=highest[2]
        if kmax<=0:raise RuntimeError('no supported polar kappa maximum')
        slope=source.slope[side]
        # Weighted patch calibration, NOT peak-only: robust M2 QP occupancy
        # of all 60 supported physical bins d<=0.5 mm and |mu|>=0.8.
        weights=[];ka=[];taper=[]
        for (bin_key,pt,_),row in zip(center,m3_rows):
            if bin_key[1]!=bin_idx or bin_key[0]>4:continue
            radius=np.linalg.norm(pt-C)
            weights.append(int(row['M2_QP']))
            ka.append(source.kappa(pt))
            taper.append(source.polar_weight((radius-R)*1000.,(pt[2]-C[2])/radius))
        weights=np.array(weights,dtype=float)
        ka=np.array(ka);taper=np.array(taper)
        def empirical_proxy(patch_delta):
            return float(np.average(np.exp(-slope*(delta_generic*ka+patch_delta*taper)),weights=weights))
        baseline=empirical_proxy(0.)
        low,high=0.,1.
        if empirical_proxy(high)>TARGET:raise RuntimeError('regional calibration requires huge patch delta')
        for _ in range(52):
            mid=(low+high)/2
            if empirical_proxy(mid)>TARGET:low=mid
            else:high=mid
        delta=(low+high)/2
        polar[side]={'empirical_log_Veff_sensitivity':slope,
                     'source_peak_bin':highest[0], 'source_peak_kappa':kmax,
                     'size_log_patch_delta':delta,
                     'nominal_patch_size_factor_at_full_weight':math.exp(-delta),
                     'empirical_QP_weighted_region_ratio_baseline':baseline,
                     'empirical_QP_weighted_region_ratio_after_patch':empirical_proxy(delta),
                     'region_M2_mechanical_QP':int(weights.sum()),
                     'region_QP_weighted_kappa':float(np.average(ka,weights=weights)),
                     'region_QP_weighted_patch_weight':float(np.average(taper,weights=weights)),
                     'calibration_proxy_only':True}
    delta_n=polar['north']['size_log_patch_delta']
    delta_s=polar['south']['size_log_patch_delta']
    # A coarse regional diagnostic only: physical bin center, weighted by M2
    # mechanical QP support. Never conflate this with the Tet10 Veff gate.
    for side,idx in (('north',9),('south',0)):
        weights=[];volume_proxies=[];ka=[]
        for (bin_key,pt,_),row in zip(center,m3_rows):
            if bin_key[1]!=idx or bin_key[0]>4:continue
            k,h,_=source.evaluate(pt,delta_n,delta_s,delta_generic)
            weights.append(int(row['M2_QP']))
            volume_proxies.append(h**3)
            ka.append(k)
        polar[side]['M2_QP_weighted_bin_center_h3_proxy']=float(
            np.average(volume_proxies,weights=weights))
        polar[side]['M2_QP_weighted_bin_center_kappa']=float(
            np.average(ka,weights=weights))
        polar[side]['regional_proxy_is_not_Veff_prediction']=True
    samples=[]
    for side,sgn in (('north',1),('south',-1)):
        for dmm in (0.,.02,.05,.1,.25,.3,.5,.7,1.,2.):
            for mu in (.7,.8,.95,1.):
                for phi in (0.,math.pi/2,math.pi-.00001):
                    direction=np.array([math.sqrt(1-mu*mu)*math.cos(phi),
                                        math.sqrt(1-mu*mu)*math.sin(phi),sgn*mu])
                    k,h,w=source.evaluate(C+(R+dmm*.001)*direction,delta_n,delta_s,delta_generic)
                    samples.append({'side':side,'d_mm':dmm,'mu':sgn*mu,'phi':phi,
                                    'kappa':k,'size_ratio_proxy':h,'nominal_volume_ratio_proxy':h**3,
                                    'polar_weight':w})
    # C2 topology: exact seam and physical-pole φ invariance, no shape FD.
    for dmm in (0.,.1,.5,2.):
        for mu in (-.95,-.7,.7,.95):
            pt=lambda phi:C+(R+dmm*.001)*np.array([
                math.sqrt(1-mu**2)*math.cos(phi),
                math.sqrt(1-mu**2)*math.sin(phi),mu])
            assert abs(source.evaluate(pt(math.pi),delta_n,delta_s,delta_generic)[0]-
                       source.evaluate(pt(-math.pi),delta_n,delta_s,delta_generic)[0])<1e-12
    for sign in (-1,1):
        pt=C+R*np.array([0.,0.,sign])
        assert math.isfinite(source.kappa(pt))
    out={'protocol':'P10IN_M3_CONTINUOUS_C2_KAPPA_SOURCE_ONLY_V1',
         'status':'PREFLIGHT_SOURCE_ONLY_PASS_NO_GMSH_NO_FEM',
         'M2_mesh_SHA256':EXPECTED_M2,
         'kappa_beta_thermal':.10,'target_supported_polar_Veff_M3_over_M2':TARGET,
         'prior_P10IE_calibration_empirical_north_south':polar,
         'generic_cubic_log_size_delta':delta_generic,
         'field_formula':'q=sum(a_i*W_i)/(1e-12+sum W_i); kappa=smoothstep5(q/max_source_center_q), in [0,1], C2',
         'peak_renormalization_raw_center_max':source.raw_center_max,
         'relative_size_formula':'exp(-kappa*delta_generic-wpolar*delta_side); north/south delta fit region-QP empirical slope proxy',
         'polar_blend':'C2 quintic ramp at abs(mu)=.6..8 and radial d=.3..1mm',
         'range_kappa_centers':[min(z[2] for z in center),max(z[2] for z in center)],
         'azimuth_seam_poles_preflight':True,
         'no_Gmsh_no_FEM':True,
         'not_actual_volume_or_mesh_quality_evidence':True,
         'calibration_assumption':'P10ID->P10IE local log sensitivity transferred to M2->M3; must verify 343/729 QP on next mesh',
         'samples':samples}
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'P10IN_SOURCE_ONLY_QA.json').write_text(json.dumps(out,indent=2)+'\n')
    with (a.out/'P10IN_RELATIVE_SIZE_FIELD_SAMPLES.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(samples[0]));w.writeheader();w.writerows(samples)
    print(json.dumps({k:v for k,v in out.items() if k!='samples'},indent=2))


if __name__=='__main__':main()
