#!/usr/bin/env python3
"""P10CN: offline, axis-regular smoothing of 200 P10CM M1 votes.

Diagnostic meridional kernel only. Does not call Gmsh/FEM, create a mesh,
calibrate physical h0, or recover missing thermal/azimuth/time physics.
Run from the Stage3D07 checkout root (or its existing scratch data root).
"""
from __future__ import annotations

import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import tempfile

ROOT = Path.cwd()
INPUT = ROOT / "research/evidence/P10CM_OFFLINE_20261120/derived/P10CM_200CELL_MULTISCALE_M1_PROPOSAL.csv"
if not INPUT.is_file():
    INPUT = ROOT / "P10CM_200CELL_MULTISCALE_M1_PROPOSAL.csv"
INPUT_SHA = "428a1d3b1d7b84e10a6c44762f0222c831a5f917283c872e06eaa11eff0781eb"
AUDIT = ROOT / "research/evidence/P10CM_OFFLINE_20261120/derived/P10CM_MULTISCALE_M1_AUDIT.json"
if not AUDIT.is_file():
    AUDIT = ROOT / "P10CM_MULTISCALE_M1_AUDIT.json"
AUDIT_SHA = "3eea935277c91b7877f8660c68d3322cf7660fb871ffbaf5e74843afe5a12737"
R_PORE_MM = 1.0
DEFAULT_ELL_MM = .20
DEFAULT_ALPHA = .50
ELL_MM = (.10, .20, .35)
ALPHA = (.25, .50, 1.0)


def insist(condition, message):
    if not condition:
        raise AssertionError(message)


def verified_file(path, expected_sha):
    contents=path.read_bytes()
    actual=sha256(contents).hexdigest()
    if actual != expected_sha:
        raise ValueError("P10CN pinned source SHA mismatch: " + str(path))
    return contents


def physical_point_mm(d_mm,mu):
    radius=R_PORE_MM+d_mm
    return radius*math.sqrt(max(0.,1.-mu*mu)), radius*mu


def sample_input():
    b=verified_file(INPUT,INPUT_SHA)
    audit=json.loads(verified_file(AUDIT,AUDIT_SHA))
    insist(audit["mesh_files_created"]==0 and audit["new_fem_runs"]==0,"P10CM must be offline")
    rows=list(csv.DictReader(b.decode("utf-8-sig").splitlines()))
    insist(len(rows)==200,"expected exactly 200 cells")
    result=[]
    used=set()
    for r in rows:
        ring=int(r["radial_bin"])
        band=int(r["polar_band"])
        key=(ring,band)
        insist(0<=ring<20 and 0<=band<10 and key not in used,"invalid source bin")
        used.add(key)
        v=int(r["refinement_votes_0_to_3"])
        insist(0<=v<=3 and r["h_over_h0_status"]=="UNSET" and r["source_phi_resolved"]=="NO",
               "source is a proxy, not calibrated 3D h")
        d=(float(r["d_lower_mm"])+float(r["d_upper_mm"]))/2.
        mu=(float(r["mu_lower"])+float(r["mu_upper"]))/2.
        rho,z=physical_point_mm(d,mu)
        volume=float(r["qp_volume_m3"])
        insist(volume>0.,"source QP volume")
        result.append({"ring":ring,"mu_bin":band,"d_mm":d,"mu":mu,"rho_mm":rho,"z_mm":z,
                       "volume_m3":volume,"w":v/3.,"votes":v})
    insist(len(used)==200 and sum(p["votes"]==3 for p in result)==31,"P10CM votes parity")
    return sorted(result,key=lambda p:(p["ring"],p["mu_bin"]))


def smooth_meridional(rho,z,points,ell):
    """Normalized reflected Gaussian kernel with exact rho-even extension.

    Reflecting +/-rho_i ensures dS/d(rho)=0 at the polar axis. It is not
    the exact 3D axisymmetric Gaussian convolution: this is a 2D pilot.
    The input weights are baseline QP bin volumes, not physical errors.
    """
    insist(ell>0. and math.isfinite(ell),"positive smoothing length")
    sum_k=sum_kw=sum_dkr=sum_dkz=sum_dkrw=sum_dkzw=0.
    inv_l2=1./(ell*ell)
    for p in points:
        ri=p["rho_mm"]
        zi=p["z_mm"]
        dz=z-zi
        a=math.exp(-.5*((rho-ri)**2+dz*dz)*inv_l2)
        b=math.exp(-.5*((rho+ri)**2+dz*dz)*inv_l2)
        k=.5*(a+b)*p["volume_m3"]
        dkr=-.5*((rho-ri)*a+(rho+ri)*b)*inv_l2*p["volume_m3"]
        dkz=-dz*inv_l2*k
        w=p["w"]
        sum_k+=k
        sum_kw+=k*w
        sum_dkr+=dkr
        sum_dkz+=dkz
        sum_dkrw+=dkr*w
        sum_dkzw+=dkz*w
    insist(sum_k>0.,"kernel denominator underflow; parameter STOP")
    smooth=sum_kw/sum_k
    ds_dr=(sum_dkrw-smooth*sum_dkr)/sum_k
    ds_dz=(sum_dkzw-smooth*sum_dkz)/sum_k
    insist(-1.e-13<=smooth<=1.+1.e-13,"convex bounded normalized weight")
    return max(0.,min(1.,smooth)),ds_dr,ds_dz


def proxy_at(rho,z,points,ell,alpha):
    smooth,ds_dr,ds_dz=smooth_meridional(rho,z,points,ell)
    rel_h=1./(1.+alpha*smooth)
    log_rel_grad=alpha*math.hypot(ds_dr,ds_dz)/(1.+alpha*smooth)
    return smooth,rel_h,log_rel_grad


def synthetic_checks(points):
    # Constant inputs are exactly preserved by the normalized kernel.
    constant=[{**p,"w":.4} for p in points]
    for ell in ELL_MM:
        for rho,z in ((0.,1.05),(.45,.92),(1.1,0.),(0.,-1.09)):
            w,dr,dz=smooth_meridional(rho,z,constant,ell)
            insist(abs(w-.4)<1.e-13 and max(abs(dr),abs(dz))<1.e-11,
                   "constant-preservation/zero-gradient unit")
        # The mirror makes the extension even, with zero transverse derivative.
        for z in (-1.05,1.05):
            w,dr,dz=smooth_meridional(0.,z,points,ell)
            insist(abs(dr)<1.e-11,"zero derivative on polar axis")
            for eps in (1.e-3,1.e-5):
                a=smooth_meridional(eps,z,points,ell)[0]
                b=smooth_meridional(-eps,z,points,ell)[0]
                insist(abs(a-b)<1.e-13,"meridional reflection symmetry")
    # Exactly axisymmetric Cartesian lifting: no phi coordinate or 1/sin(theta).
    for d,mu in ((.021,-.99999),(.025,.1),(.078,.99999)):
        rho,z=physical_point_mm(d,mu)
        expected=proxy_at(rho,z,points,.20,.50)
        for phi in (.0,.5,1.43,3.87,6.2):
            x=rho*math.cos(phi);y=rho*math.sin(phi)
            got=proxy_at(math.hypot(x,y),z,points,.20,.50)
            insist(max(abs(a-b) for a,b in zip(got,expected))<1.e-13,"Cartesian rotation invariant")
    for z in (-1.025,1.025):
        expected=proxy_at(0.,z,points,.20,.50)
        insist(all(map(math.isfinite,expected)),"polar axis finite")
    # Unit-only centered differences are permitted here for the smoothing
    # formula; they are not FEM geometric derivatives or production operators.
    eps=1.e-5
    for rho,z in ((.3,.98),(.8,.6),(.05,-1.03)):
        _,analytic_r,analytic_z=smooth_meridional(rho,z,points,.20)
        numerical_r=(smooth_meridional(rho+eps,z,points,.20)[0]-
                     smooth_meridional(rho-eps,z,points,.20)[0])/(2.*eps)
        numerical_z=(smooth_meridional(rho,z+eps,points,.20)[0]-
                     smooth_meridional(rho,z-eps,points,.20)[0])/(2.*eps)
        insist(abs(numerical_r-analytic_r)<2.e-7 and abs(numerical_z-analytic_z)<2.e-7,
               "independent meridional smoothing gradient unit")
    with tempfile.TemporaryDirectory(prefix="p10cn_sha_unit_") as temp:
        corrupt=Path(temp)/"source.csv"
        corrupt.write_bytes(b"wrong source")
        try:
            verified_file(corrupt,INPUT_SHA)
        except ValueError:
            pass
        else:
            raise AssertionError("corrupted SHA should STOP")
    return "P10CN_AXIS_REFLECTION_CONSTANT_ROTATION_SHA_STOP_UNIT_OK"


def evaluate(points,ell,alpha):
    # The local element-count proxy scales only as inverse h^3, not DOF or RAM.
    total_v=sum(p["volume_m3"] for p in points)
    total_cost=0.
    min_h=1.
    max_s=0.
    for p in points:
        s,rel_h,g=proxy_at(p["rho_mm"],p["z_mm"],points,ell,alpha)
        total_cost+=p["volume_m3"]/(rel_h**3)
        min_h=min(min_h,rel_h)
        max_s=max(max_s,s)
    max_grad=0.
    max_axis_deriv=0.
    # Oversample shell and angle, not just the original centers.
    for i in range(17):
        d=.020+.080*i/16.
        for j in range(81):
            mu=-1.+2.*j/80.
            rho,z=physical_point_mm(d,mu)
            s,grad_r,grad_z=smooth_meridional(rho,z,points,ell)
            max_grad=max(max_grad,alpha*math.hypot(grad_r,grad_z)/(1.+alpha*s))
            if j in (0,80):
                max_axis_deriv=max(max_axis_deriv,abs(grad_r))
    return {"ell_mm":ell,"alpha":alpha,
            "smooth_weight_max_at_source_centers":max_s,
            "minimum_h_trial_over_h0_at_centers":min_h,
            "local_isotropic_tet_count_volume_proxy":total_cost/total_v,
            "max_sampled_grad_log_relative_h_per_mm":max_grad,
            "max_axis_radial_derivative_of_smooth_weight_per_mm":max_axis_deriv,
            "full_mesh_count_ram_or_wall_time":"NOT_PREDICTABLE_FROM_THIS_SHELL_ONLY"}


def main():
    points=sample_input()
    unit=synthetic_checks(points)
    sensitivity=[evaluate(points,ell,alpha) for ell in ELL_MM for alpha in ALPHA]
    baseline=next(r for r in sensitivity if r["ell_mm"]==DEFAULT_ELL_MM and r["alpha"]==DEFAULT_ALPHA)
    result={"protocol":"P10CN_CARTESIAN_MERIDIONAL_REFLECTION_SMOOTHING_OFFLINE_NO_MESH_NO_FEM",
            "source_csv_sha256":INPUT_SHA,"source_audit_sha256":AUDIT_SHA,
            "input_rows":len(points),"input_votes":{"0":151,"1":9,"2":9,"3":31},
            "kernel":"positive_volume_weighted_gaussian_reflected_rho_i_positive_negative",
            "kernel_is_exact_3d_axisymmetric_heat_kernel":False,
            "distance_unit":"mm","ell_parameter_mm":list(ELL_MM),"alpha_parameter":list(ALPHA),
            "baseline_display_only":{"ell_mm":DEFAULT_ELL_MM,"alpha":DEFAULT_ALPHA},
            "parameters_physically_calibrated":False,
            "baseline":baseline,"sensitivity":sensitivity,"synthetic_unit":unit,
            "spatial_support_only":"20_TO_100_UM_DIAGNOSTIC_SHELL",
            "h0_mesh_size_values_available":False,"full_B6_cost_estimate_available":False,
            "thermal_and_phi_time_resolved_physical_components":False,
            "actual_mesh_created":False,"gmsh_calls":0,"physical_fem_runs":0}
    (ROOT/"P10CN_SMOOTHING_SENSITIVITY.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")

    out=ROOT/"P10CN_200CELL_MERIDIONAL_SMOOTHING.csv"
    fields=["radial_bin","polar_band","d_lower_mm","d_upper_mm","mu_lower","mu_upper",
            "initial_vote_0_to_3","initial_w_votes_over_3","qp_volume_m3",
            "smooth_w_ell_0p20mm","trial_h_over_h0_alpha_0p50","grad_log_hrel_per_mm",
            "real_h0_mm_status","phi_thermal_time_physics"]
    with out.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for p in points:
            s,h,g=proxy_at(p["rho_mm"],p["z_mm"],points,DEFAULT_ELL_MM,DEFAULT_ALPHA)
            r=p["ring"];mu=p["mu_bin"]
            lo=.02+.003*r if r<10 else .05+.005*(r-10)
            hi=.02+.003*(r+1) if r<10 else .05+.005*(r-9)
            writer.writerow({"radial_bin":r,"polar_band":mu,
                             "d_lower_mm":f"{lo:.9f}","d_upper_mm":f"{hi:.9f}",
                             "mu_lower":f"{-1+.2*mu:.9f}","mu_upper":f"{-1+.2*(mu+1):.9f}",
                             "initial_vote_0_to_3":p["votes"],"initial_w_votes_over_3":f"{p['w']:.9f}",
                             "qp_volume_m3":f"{p['volume_m3']:.17g}",
                             "smooth_w_ell_0p20mm":f"{s:.12g}",
                             "trial_h_over_h0_alpha_0p50":f"{h:.12g}",
                             "grad_log_hrel_per_mm":f"{g:.12g}",
                             "real_h0_mm_status":"UNAVAILABLE","phi_thermal_time_physics":"NOT_AVAILABLE"})

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    theta=np.degrees(np.arccos(np.linspace(1.,-1.,11)))
    d_edges=np.array([.02+i*.003 for i in range(11)]+[.05+i*.005 for i in range(1,11)])*1000.
    by={(p["ring"],p["mu_bin"]):p for p in points}
    raw=np.array([[by[r,9-j]["w"] for j in range(10)] for r in range(20)])
    smooth=np.array([[smooth_meridional(by[r,9-j]["rho_mm"],by[r,9-j]["z_mm"],points,DEFAULT_ELL_MM)[0]
                      for j in range(10)] for r in range(20)])
    fig,axs=plt.subplots(1,2,figsize=(12.5,4.6),sharex=True,sharey=True,layout="constrained")
    for ax,mat,title in zip(axs,(raw,smooth),
                            ("P10CM original: vote/3", "P10CN reflected meridional smoothing (ℓ=0.20 mm)")):
        pcm=ax.pcolormesh(theta,d_edges,mat,vmin=0.,vmax=1.,cmap="viridis",shading="flat")
        ax.set_title(title)
        ax.set_xlabel("polar θ from +z (degrees)")
        ax.axvline(np.degrees(np.arccos(.8)),ls="--",color="white",lw=.9)
        ax.axvline(np.degrees(np.arccos(-.8)),ls="--",color="white",lw=.9)
        ax.set_xticks([0,36.87,90,143.13,180],["0","36.9","90","143.1","180"])
    axs[0].set_ylabel("distance from pore wall (µm)")
    c=fig.colorbar(pcm,ax=axs,shrink=.83,pad=.015);c.set_label("dimensionless provisional weight, not FEM error")
    fig.suptitle("P10CN: axis-regular, φ-invariant diagnostic smoothing; 20–100 µm only\n"
                 "No M1 mesh, physical h0, thermal field or full-domain memory estimate",fontsize=11)
    fig.savefig(ROOT/"P10CN_AXIS_REGULAR_SMOOTHING_COMPARISON.png",dpi=180)
    plt.close(fig)
    print(unit)
    print("P10CN_OFFLINE_AXIS_REGULAR_SMOOTHING_PASS_NO_MESH_NO_FEM")
    for r in sensitivity:
        print("ell_mm",r["ell_mm"],"alpha",r["alpha"],
              "local_count_proxy",round(r["local_isotropic_tet_count_volume_proxy"],6),
              "max_grad_logh_per_mm",round(r["max_sampled_grad_log_relative_h_per_mm"],6))


if __name__=="__main__":
    main()
