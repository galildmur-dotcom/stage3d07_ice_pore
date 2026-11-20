#!/usr/bin/env python3
"""P10CM: signed, multiscale M1 indicator pilot from EXISTING P10BB/P10CH CSV.

No gmsh, FEM, mesh generation, or physical four-dimensional field is involved.
Must run from the Stage3D07 research checkout root, or the prior scratch data root.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import statistics
import tempfile


ROOT = Path.cwd()
INPUT = ROOT / "research/evidence/P10CH_OFFLINE_20261120/derived/P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv"
if not INPUT.is_file():
    INPUT = ROOT / "P10CH_M1_OFFLINE_CANDIDATE_200CELLS.csv"
INPUT_SHA = "84b738960d712ba11eca880a86f98782905dc6dcc6cd3c72c70e4c97c42406c3"
REF_DIR = ROOT / "experiments/P10BB_W5B2_SPHERICAL_20261118/input"
if not REF_DIR.is_dir():
    REF_DIR = ROOT / "stage3d07_readonly/experiments/P10BB_W5B2_SPHERICAL_20261118/input"
REF_SHA = {
    "H4W4B2": "219b237e42305f1e4db3089f6501bdd59034dc664f9eee83c5bdc0888e15d447",
    "H4W4B20": "3803ed656045384727109952c9331c4e073e4cec9f718a3a7770ecf3a28bd1be",
    "H4W5B2": "8ad499250082e919942e8ea105ed0b21463cfd5083085af3f004ee293294c11c",
}
GEOMETRY = ROOT / "research/evidence/P10CL_REAL_CURVED_QP_ANALYSIS_20261120/derived/P10CL_INDEPENDENT_QP_GEOMETRY_AUDIT.json"
if not GEOMETRY.is_file():
    GEOMETRY = ROOT / "P10CL_INDEPENDENT_QP_GEOMETRY_AUDIT.json"
GEOMETRY_SHA = "5f35152042172a853d79c00dfafa44d0a1eb0ffca798cdf48c0cad4d71f46e2f"


def verified_rows(p: Path, expected_hash: str):
    b = p.read_bytes()
    actual_hash = sha256(b).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError(f"P10CM source SHA mismatch for {p}: {actual_hash}")
    return list(csv.DictReader(b.decode("utf-8-sig").splitlines()))


def insist(ok, why):
    if not ok:
        raise AssertionError(why)


def ranks01(values):
    """Normalized 1-based competition-free ranks; equal values get mean rank."""
    n = len(values)
    ordering = sorted(range(n), key=lambda i: values[i])
    answer = [0.] * n
    i = 0
    while i < n:
        j = i + 1
        while j < n and values[ordering[j]] == values[ordering[i]]:
            j += 1
        middle = ((i + 1) + j) / (2. * n)
        for k in range(i, j):
            answer[ordering[k]] = middle
        i = j
    return answer


def coarsen(fine, grouping):
    grouped = defaultdict(lambda: [0., 0., 0., 0., 0])
    for k, row in fine.items():
        g = grouping(k)
        v = grouped[g]
        v[0] += row["bulk"]
        v[1] += row["wall"]
        v[2] += row["volume"]
        v[3] += abs(row["bulk"])
        v[4] += abs(row["wall"])
    return dict(grouped)


def ranked_groups(coarse, choose):
    keys = sorted(coarse)
    scores_b = [abs(coarse[k][0]) / coarse[k][2] for k in keys]
    scores_w = [abs(coarse[k][1]) / coarse[k][2] for k in keys]
    if max(scores_b)==0. or max(scores_w)==0.:
        raise ValueError("All signed coarse signals vanished in one spatial comparison; cannot rank")
    rb, rw = ranks01(scores_b), ranks01(scores_w)
    priorities = {k: min(rb[i], rw[i]) for i, k in enumerate(keys)}
    order = sorted(keys, key=lambda k: (-priorities[k], k))
    return set(order[:choose]), priorities


def coverage(fine, chosen):
    all_bulk = sum(abs(v["bulk"]) for v in fine.values())
    all_wall = sum(abs(v["wall"]) for v in fine.values())
    return {"cells":len(chosen),
            "polar_cells":sum(mu in (0, 9) for _, mu in chosen),
            "bulk_abs_share":sum(abs(fine[k]["bulk"]) for k in chosen) / all_bulk,
            "wall_abs_share":sum(abs(fine[k]["wall"]) for k in chosen) / all_wall}


def rotated_lookup(ring, mu, angle, weights):
    """Test Cartesian evaluation, including coordinate axis, no 1/sin(theta)."""
    edges = [.02 + i * .003 for i in range(11)] + [.05 + i * .005 for i in range(1, 11)]
    d = (edges[ring] + edges[ring+1]) / 2. * .001
    R = .001 + d
    polar_mu = -1. + (mu + .5) * .2
    rho = R * math.sqrt(max(0.,1. - polar_mu*polar_mu))
    x = rho * math.cos(angle)
    y = rho * math.sin(angle)
    z = .03 + R * polar_mu
    rr = math.sqrt(x*x + y*y + (z-.03)**2)
    return weights[cartesian_cell_index(x,y,z)]


def cartesian_cell_index(x,y,z):
    edges = [.02 + i * .003 for i in range(11)] + [.05 + i * .005 for i in range(1, 11)]
    rr=math.sqrt(x*x+y*y+(z-.03)**2)
    insist(rr>0.,"pore center undefined")
    recovered_d_mm = (rr-.001)*1000.
    recovered_mu = max(-1.,min(1.,(z-.03)/rr))
    recovered_ring = next(i for i in range(20) if edges[i] <= recovered_d_mm < edges[i+1])
    recovered_band = max(0,min(9,int((recovered_mu+1.)*5.)))
    return recovered_ring,recovered_band


def synthetic_units():
    probe = {(i,mu): {"bulk":float((-1)**i*(i+1)),"wall":float((-1)**(i+1)*(i+2)),
                      "volume":float(1+i+mu)} for i in range(20) for mu in range(10)}
    for group_fn in (lambda k:(k[0]//10,k[1]), lambda k:k[1]):
        coarse = coarsen(probe,group_fn)
        for channel, index in (("bulk",0),("wall",1)):
            insist(math.isclose(sum(g[index] for g in coarse.values()),
                                sum(v[channel] for v in probe.values()),rel_tol=0.,abs_tol=1.e-11),
                   "synthetic signed coarsening closure")
    opposite = {(i,0): {"bulk":float((-1)**i),"wall":float((-1)**i),"volume":1.} for i in range(20)}
    grouped = coarsen(opposite, lambda k:0)
    insist(sum(abs(x["bulk"]) for x in opposite.values())==20.,"synthetic fine L1")
    insist(grouped[0][0]==0. and grouped[0][3]==20.,"synthetic cancellation")
    insist(max(abs(rotated_lookup(0,9,phi, {(0,9):.75})-.75) for phi in [0.,.3,1.9,3.14,6.27])<1.e-14,
           "synthetic azimuthal rotation invariance")
    for ring,mu in ((0,0),(0,9),(19,0),(19,9),(8,5)):
        for phi in (0.,.6,2.9,4.7,6.27):
            insist(rotated_lookup(ring,mu,phi,{(ring,mu):.125})==.125,
                   "arbitrary azimuth rotation invariance")
    for axis_z,expected_band in ((.031025,9),(.028975,0)):
        insist(cartesian_cell_index(0.,0.,axis_z)==(1,expected_band),
               "axis-safe theta=0/pi mapping")
    with tempfile.TemporaryDirectory(prefix="p10cm_sha_gate_unit_") as temp:
        p=Path(temp)/"corrupted.csv"
        p.write_bytes(b"source corruption must STOP")
        try:
            verified_rows(p,INPUT_SHA)
        except ValueError:
            pass
        else:
            raise AssertionError("SHA mismatch should STOP")
    return "P10CM_SYNTHETIC_SIGNED_COARSENING_AND_CARTESIAN_ROTATION_OK"


def main():
    unit_result = synthetic_units()
    rows = verified_rows(INPUT,INPUT_SHA)
    insist(len(rows)==200,"expected 200 P10CH cells")
    geom_bytes = GEOMETRY.read_bytes()
    insist(sha256(geom_bytes).hexdigest()==GEOMETRY_SHA,"P10CL geometry evidence SHA")
    geom = json.loads(geom_bytes)
    insist(geom["sampled_positive_is_global_J_proof"] is False,"no global J proof")
    for mesh in REF_SHA:
        quality=geom["mesh"][mesh]
        insist(quality["candidate_min_detJ_m3"]>0.,"existing sampled Jacobian quality prerequisite")
        for region in quality["groups"].values():
            insist(region["unresolved_axis_qp"]==0 and region["phi_sector_coverage_12_cells"]==region["n_cells"],
                   "existing 12 phi sectors/axis geometry prerequisite")

    references = {}
    for mesh, checksum in REF_SHA.items():
        rr = verified_rows(REF_DIR / (mesh+"_P10BA_QP_POLAR_RADIAL.csv"),checksum)
        t900 = [r for r in rr if int(r["time_step"])==6 and float(r["time_s"])==900.]
        insist(len(t900)==200,"P10BA t900 200 cells")
        bykey = {}
        for r in t900:
            ring = int(r["radial_subbin"]) + (0 if float(r["radial_lower_mm"])<.05-1.e-9 else 10)
            key = (ring,int(r["polar_band"]))
            insist(key not in bykey,"duplicate P10BA cell")
            bykey[key] = r
        insist(len(bykey)==200,"distinct P10BA keys")
        references[mesh] = bykey

    fine = {}
    original_selected = set()
    by_shell = lambda k:(0 if k[0]<10 else 1,k[1])
    by_band = lambda k:k[1]
    for row in rows:
        lo=float(row["r_lower_mm"])
        rbin = round((lo-.02)/.003) if lo < .05-1.e-9 else 10+round((lo-.05)/.005)
        mu=int(row["polar_band"])
        key=(rbin,mu)
        insist(key not in fine,"duplicate P10CH cell")
        orig=references["H4W4B2"][key]
        bulk=references["H4W4B20"][key]
        wall=references["H4W5B2"][key]
        base_i=float(orig["total_mechanical_per_m"])
        db=float(bulk["total_mechanical_per_m"])-base_i
        dw=float(wall["total_mechanical_per_m"])-base_i
        v=float(orig["qp_volume_m3"])
        insist(abs(db-float(row["delta_bulk_per_m"]))<2.e-15,"bulk signed delta primary parity")
        insist(abs(dw-float(row["delta_wall_per_m"]))<2.e-15,"wall signed delta primary parity")
        insist(abs(v-float(row["physical_volume_m3"]))<2.e-21,"QP volume primary parity")
        insist(v>0. and float(row["qp_base"])==float(orig["qp_count"]),"positive baseline QP data")
        fine[key] = {"bulk":db,"wall":dw,"volume":v,"temporal":float(row["delta_H2_dt50_minus_25_per_m"]),
                     "source_rank":float(row["spatial_volume_normalized_consensus_rank"])}
        if int(row["chosen_top_20pct"]) == 1:
            original_selected.add(key)
    insist(len(fine)==200 and len(original_selected)==40,"P10CH fine top40")
    insist(set(fine)=={(r,mu) for r in range(20) for mu in range(10)},"20 x 10 regular grid")

    fine_values={k:[v["bulk"],v["wall"],v["volume"],abs(v["bulk"]),abs(v["wall"])] for k,v in fine.items()}
    shell = coarsen(fine,by_shell)
    band = coarsen(fine,by_band)
    insist(len(shell)==20 and len(band)==10,"three radial scales")
    select_fine, scores_fine = ranked_groups(fine_values,40)
    select_shell, scores_shell = ranked_groups(shell,4)
    select_band, scores_band = ranked_groups(band,2)
    sf = select_fine
    ss = {k for k in fine if by_shell(k) in select_shell}
    sb = {k for k in fine if by_band(k) in select_band}
    insist(len(sf)==len(ss)==len(sb)==40,"all three have 40 cells")

    # Recompute signed closure, separately for bulk/wall; not an error estimate.
    signed = {}
    for channel, index in (("bulk",0),("wall",1)):
        total=sum(v[channel] for v in fine.values())
        shell_total=sum(x[index] for x in shell.values())
        band_total=sum(x[index] for x in band.values())
        insist(math.isclose(total,shell_total,rel_tol=0.,abs_tol=2.e-16),"fine-to-shell signed parity")
        insist(math.isclose(total,band_total,rel_tol=0.,abs_tol=2.e-16),"fine-to-band signed parity")
        fine_abs=sum(abs(v[channel]) for v in fine.values())
        shell_abs=sum(abs(x[index]) for x in shell.values())
        band_abs=sum(abs(x[index]) for x in band.values())
        signed[channel]={"signed_total_per_m":total,"fine_abs_sum_per_m":fine_abs,
                         "shell_abs_sum_per_m":shell_abs,"band_abs_sum_per_m":band_abs,
                         "shell_retention_vs_fine":shell_abs/fine_abs,
                         "band_retention_vs_fine":band_abs/fine_abs}

    core3=sf&ss&sb
    core2={k for k in fine if int(k in sf)+int(k in ss)+int(k in sb)>=2}
    score_votes={k:int(k in sf)+int(k in ss)+int(k in sb) for k in fine}
    results={"tool":"P10CM_OFFLINE_MULTISCALE_M1_INDICATOR_NO_MESH_NO_FEM",
             "input_P10CH_sha256":INPUT_SHA,"source_P10BA_sha256":REF_SHA,
             "input_P10CL_geometry_json_sha256":GEOMETRY_SHA,
             "source_P10CH_fine40_vs_recomputed_overlap":len(original_selected&sf),
             "fine40_recomputed_vs_original_Jaccard":len(original_selected&sf)/len(original_selected|sf),
             "selection":{"fine40":coverage(fine,sf),"shell4groups40":coverage(fine,ss),
                          "band2groups40":coverage(fine,sb),
                          "core_three_scales":coverage(fine,core3),
                          "majority_two_or_more":coverage(fine,core2),
                          "original_P10CH_fine40":coverage(fine,original_selected)},
             "selected_shell_groups":[list(k) for k in sorted(select_shell)],
             "selected_polar_bands":sorted(select_band),
             "intersections":{"fine_shell":len(sf&ss),"fine_band":len(sf&sb),
                              "shell_band":len(ss&sb),"all_three":len(core3),
                              "all_three_polar":sum(mu in(0,9) for _,mu in core3)},
             "signed_coarsening":signed,
             "all_200_cell_phi_by_time_physics":"ABSENT_NOT_INFERRED",
             "geometry_positive_at_27QP_only":True,
             "h_over_h0_physical_calibration":"UNSET_NO_GMSH_MESH_CREATED",
             "synthetic_unit":unit_result,
             "new_fem_runs":0,"mesher_calls":0,"mesh_files_created":0,
             "requires_new_physical_M1_authorization":True}

    csv_path=ROOT/"P10CM_200CELL_MULTISCALE_M1_PROPOSAL.csv"
    fields=["radial_bin","polar_band","d_lower_mm","d_upper_mm","mu_lower","mu_upper",
            "delta_bulk_per_m","delta_wall_per_m","qp_volume_m3",
            "score_fine","score_shell","score_band","fine_top40","two_shell_top4","one_shell_top2",
            "refinement_votes_0_to_3","majority_two_or_more","stable_three_scale_core",
            "h_over_h0_status","source_phi_resolved"]
    with csv_path.open("w",newline="",encoding="utf-8") as f:
        wr=csv.DictWriter(f,fieldnames=fields)
        wr.writeheader()
        for r in range(20):
            lower=.02+r*.003 if r<10 else .05+(r-10)*.005
            upper=.02+(r+1)*.003 if r<10 else .05+(r-9)*.005
            for mu in range(10):
                k=(r,mu)
                row=fine[k]
                wr.writerow({"radial_bin":r,"polar_band":mu,"d_lower_mm":f"{lower:.9f}",
                             "d_upper_mm":f"{upper:.9f}","mu_lower":f"{-1+mu*.2:.9f}",
                             "mu_upper":f"{-1+(mu+1)*.2:.9f}",
                             "delta_bulk_per_m":f"{row['bulk']:.17g}",
                             "delta_wall_per_m":f"{row['wall']:.17g}",
                             "qp_volume_m3":f"{row['volume']:.17g}",
                             "score_fine":f"{scores_fine[k]:.9f}",
                             "score_shell":f"{scores_shell[by_shell(k)]:.9f}",
                             "score_band":f"{scores_band[by_band(k)]:.9f}",
                             "fine_top40":int(k in sf),"two_shell_top4":int(k in ss),
                             "one_shell_top2":int(k in sb),
                             "refinement_votes_0_to_3":score_votes[k],
                             "majority_two_or_more":int(k in core2),
                             "stable_three_scale_core":int(k in core3),
                             "h_over_h0_status":"UNSET", "source_phi_resolved":"NO"})
    json_path=ROOT/"P10CM_MULTISCALE_M1_AUDIT.json"
    json_path.write_text(json.dumps(results,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.colors import ListedColormap,BoundaryNorm
    theta=np.degrees(np.arccos(np.linspace(1.,-1.,11)))
    d_edges=np.array([.02+i*.003 for i in range(11)]+[.05+i*.005 for i in range(1,11)])*1000.
    flags=[sf,ss,sb,core2]
    names=["Fine 200 bins: top 40", "2 radial shells: 4 groups", "1 radial shell: 2 polar bands", "Majority vote: at least 2/3"]
    fig, axes=plt.subplots(2,2,figsize=(12.7,8.0),sharex=True,sharey=True,layout="constrained")
    cmap=ListedColormap(["#f0f0f0","#1b9e77"])
    norm=BoundaryNorm([-.5,.5,1.5],2)
    for ax, selected, title in zip(axes.flat, flags,names):
        array=np.array([[int((r,9-c) in selected) for c in range(10)] for r in range(20)])
        ax.pcolormesh(theta,d_edges,array,cmap=cmap,norm=norm,shading="flat")
        ax.set_title(title+f"\nselected {len(selected)} cells, polar {sum(mu in (0,9) for _,mu in selected)}")
        ax.axvline(np.degrees(np.arccos(.8)),ls="--",color="#fca311",lw=1.3)
        ax.axvline(np.degrees(np.arccos(-.8)),ls="--",color="#fca311",lw=1.3)
        ax.axhline(50,ls=":",color="#555555",lw=.8)
        ax.set_xticks([0,36.87,60,90,120,143.13,180],["0","36.9","60","90","120","143.1","180"])
        ax.set_xlabel("polar angle θ from +z (deg)")
    for ax in axes[:,0]:
        ax.set_ylabel("distance from pore wall (µm)")
    fig.suptitle("P10CM offline mechanical Δ: sensitivity of provisional M1 regions to radial coarsening\n"
                 "No mesh, FEM, thermal/φ/t fields or a posteriori error estimate",fontsize=12)
    fig.savefig(ROOT/"P10CM_MULTISCALE_M1_CANDIDATE_COMPARISON.png",dpi=180)
    plt.close(fig)
    print(unit_result)
    print("P10CM_PRIMARY_SIGNED_COARSENING_PARITY_OK_NO_FEM")
    for name,value in results["selection"].items():
        print(name,"count",value["cells"],"polar",value["polar_cells"],
              "L1_bulk",f"{value['bulk_abs_share']:.4f}","L1_wall",f"{value['wall_abs_share']:.4f}")
    print("overlap fine/shell/band",results["intersections"],
          "original fine overlap",results["source_P10CH_fine40_vs_recomputed_overlap"])
    print("signed retention",signed)


if __name__=="__main__":
    main()
