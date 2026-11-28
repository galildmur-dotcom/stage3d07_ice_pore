#!/usr/bin/env python3
"""Read-only P10GJ M1 343/729QP against PRE-REGISTERED D-027 policy/M0.

Run on the analyst's machine after receiving evidence. No Windows Gmsh,
no FEM, no approval-file writing. Requires NumPy locally, NOT on user Windows.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research/proposals/P10GJ_ONE_ROTATED_HXT10_WINDOWS_20261123"
POLICY=SOURCE/"P10GJ_D027_GATE_POLICY.json"
BASELINE=SOURCE/"P10GJ_M0_QP_BASELINE.json"
EDGE=((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
DL=np.array([[-1.,-1.,-1.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
CAD_VOL=.06*.06*.05-4*math.pi*.001**3/3
RADS=("0_100um","100_500um","500um_plus")
POLS=("polar_abs_mu_ge_0p8","taper_abs_mu_0p6_0p8","off_abs_mu_le_0p6")
HEMS=("north","south")


def need(ok,msg):
    if not ok:raise ValueError("P10GJ_OFFLINE_STOP: "+msg)


def sha(b):return hashlib.sha256(b).hexdigest()


def rule(order):
    pt,wt=np.polynomial.legendre.leggauss(order)
    pt=(pt+1.)/2;wt=wt/2
    ns=[];ds=[];ws=[]
    for a,aw in zip(pt,wt):
        for b,bw in zip(pt,wt):
            for c,cw in zip(pt,wt):
                r=a;s=(1-r)*b;t=(1-r)*(1-b)*c
                L=np.array([1-r-s-t,r,s,t])
                N=list(L*(2*L-1));D=list((4*L[:,None]-1)*DL)
                for i,j in EDGE:
                    N.append(4*L[i]*L[j]);D.append(4*(L[i]*DL[j]+L[j]*DL[i]))
                ns.append(N);ds.append(D);ws.append(aw*bw*cw*(1-r)**2*(1-b))
    N=np.asarray(ns,dtype=float);D=np.asarray(ds,dtype=float);W=np.asarray(ws,dtype=float)
    need(abs(W.sum()-1/6)<5e-15 and np.max(abs(N.sum(axis=1)-1))<2e-14,
         "Duffy rule/partition-of-unity invalid")
    return N,D,W


def read_msh(data):
    need(len(data)<=128*1024**2,"MSH source exceeds expected resource cap")
    f=io.StringIO(data.decode("ascii"));nodes={};tets=[];faces=Counter()
    for line in f:
        if line.strip()=="$MeshFormat":
            need(next(f).strip()=="2.2 0 8","only ASCII MSH2.2")
            need(next(f).strip()=="$EndMeshFormat","malformed mesh header")
        elif line.strip()=="$Nodes":
            n=int(next(f));need(0<n<=500000,"node limit")
            for _ in range(n):
                row=next(f).split();need(len(row)==4,"node row")
                idx=int(row[0]);need(idx not in nodes,"duplicate node")
                nodes[idx]=tuple(float(v) for v in row[1:])
        elif line.strip()=="$Elements":
            n=int(next(f));need(0<n<1000000,"element limit")
            for _ in range(n):
                row=list(map(int,next(f).split()))
                kind,ntag=row[1:3];physical=row[3];idx=row[3+ntag:]
                if kind==11:
                    need(physical==1 and len(idx)==10,"Tet10 tag/connectivity")
                    tets.append(idx)
                elif kind==9:
                    need(physical in range(2,10) and len(idx)==6,"Tri6 tag")
                    faces[physical]+=1
                else:need(False,"forbidden mixed element type "+str(kind))
    need(tets and set(faces)==set(range(2,10)),"missing volume/surface coverage")
    need(all(math.isfinite(x) for p in nodes.values() for x in p),"nonfinite node")
    arr=np.zeros((max(nodes)+1,3),dtype=np.float64)
    for node,p in nodes.items():arr[node]=p
    tet=np.asarray(tets,dtype=np.int64)
    need(np.all(tet>=1) and np.all(tet<len(arr)),"out-of-range node index")
    return arr,tet,faces


def geom(p,N,D):
    # p [batch,10,3]; shape derivatives [q,10,3].
    J=np.einsum("nic,qij->nqcj",p,D,optimize=True)
    det=np.linalg.det(J)
    x=np.einsum("nic,qi->nqc",p,N,optimize=True)
    return x,det


def baseline_volumes(nodes,tets):
    N,D,W=rule(3);vol=np.zeros(len(tets),dtype=float);minj=math.inf
    for start in range(0,len(tets),96):
        end=min(start+96,len(tets));_,det=geom(nodes[tets[start:end]],N,D)
        need(bool(np.all(np.isfinite(det)) and np.all(det>0)),"nonpositive 27QP")
        vol[start:end]=det@W;minj=min(minj,float(det.min()))
    need(bool(np.all(vol>0)),"nonpositive Tet10 full volume")
    return vol,minj


def codes(x):
    diff=x-np.array((0.,0.,.03));radius=np.linalg.norm(diff,axis=2)
    need(bool(np.all(radius>0)),"QP on pore centre")
    d=radius-.001;mu=diff[:,:,2]/radius
    rad=np.where(d<.0001,0,np.where(d<.0005,1,2))
    pol=np.where(np.abs(mu)>=.8,0,np.where(np.abs(mu)>.6,1,2))
    return (rad*3+pol)*2+(mu<0).astype(np.int64)


def sample(nodes,tets,full,order):
    N,D,W=rule(order);vol=np.zeros(18);neff=np.zeros(18)
    minj=math.inf;total=0.
    for start in range(0,len(tets),64):
        end=min(start+64,len(tets));x,det=geom(nodes[tets[start:end]],N,D)
        need(bool(np.all(np.isfinite(det)) and np.all(det>0)),
             f"nonpositive {order**3}QP Jacobian")
        minj=min(minj,float(det.min()))
        weights=det*W[None,:]
        total+=float(weights.sum())
        code=codes(x).ravel()
        vol+=np.bincount(code,weights=weights.ravel(),minlength=18)
        neff+=np.bincount(code,weights=(weights/full[start:end,None]).ravel(),minlength=18)
    need(bool(np.all(vol>0) and np.all(neff>0)),"missing signed physical QP")
    return {"QP_per_tet":order**3,"region_volume":vol,"N_eff":neff,
            "V_eff":vol/neff,"min_detJ":minj,"total_volume":total}


def compare(msh_stats,ref,order):
    old=ref["levels"][str(order)]["zones18"]
    v0=np.array([r["M0_Veff_m3"] for r in old],dtype=float)
    reg0=np.array([r["M0_region_volume_m3"] for r in old],dtype=float)
    ne0=np.array([r["M0_Neff"] for r in old],dtype=float)
    ve1=msh_stats["V_eff"];q=ve1/v0
    rows=[]
    for i,(r,ratio) in enumerate(zip(old,q)):
        rows.append({"radial_zone":r["radial_zone"],
                     "polar_zone":r["polar_zone"],"hemisphere":r["hemisphere"],
                     "M0_N_eff":float(ne0[i]),"M1_N_eff":float(msh_stats["N_eff"][i]),
                     "M0_V_eff_m3":float(v0[i]),"M1_V_eff_m3":float(ve1[i]),
                     "M1_over_M0_Q_V":float(ratio),"legacy_in_0p80_0p85":bool(.8<=ratio<=.85)})
    def pack(label,ix):
        n0=float(ne0[ix].sum());n1=float(msh_stats["N_eff"][ix].sum())
        v0sum=float(reg0[ix].sum());v1sum=float(msh_stats["region_volume"][ix].sum())
        val=(v1sum/n1)/(v0sum/n0)
        return {"name":label,"M0_Neff":n0,"M1_Neff":n1,"Q_V":val,
                "M0_volume_m3":v0sum,"M1_volume_m3":v1sum}
    macros=[]
    for p in range(3):
        for h in range(2):
            ix=np.array([(r*3+p)*2+h for r in (0,1)],dtype=int)
            macros.append(pack("near_0_500um_"+POLS[p]+"_"+HEMS[h],ix))
    for r in range(3):
        for p in range(3):
            ix=np.array([(r*3+p)*2+h for h in range(2)],dtype=int)
            macros.append(pack(RADS[r]+"_"+POLS[p]+"_both",ix))
    return {"QP_per_tet":order**3,"signed18":rows,"macros":macros,
            "min_curved_detJ":float(msh_stats["min_detJ"]),
            "QP_total_curved_volume_m3":float(msh_stats["total_volume"])}


def adjudicate(evidence_zip):
    raw=Path(evidence_zip).read_bytes()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        need(z.testzip() is None,"evidence ZIP CRC failure")
        names=z.namelist();need(len(set(names))==len(names),"duplicate entries")
        need(all("/" not in n and "\\" not in n for n in names),"unsafe entries")
        manifest=json.loads(z.read("P10GJ_M1_MANIFEST.json"))
        gates=json.loads(z.read("P10GJ_D027_FROZEN_GATES.json"))
        need(sha(z.read("P10GJ_D027_FROZEN_GATES.json"))==
             manifest["frozen_gates_sha256"],"frozen policy SHA mismatch")
        fixed=json.loads(POLICY.read_text())
        need(gates["fixed_policy"]==fixed,"source D-027 policy changed")
        need(gates["M0_msh_sha256"]==
             "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6",
             "wrong canonical M0 baseline")
        ref=json.loads(BASELINE.read_text())
        mesh=z.read("P10GJ_M1_ROTATED_CANDIDATE.msh")
        need(sha(mesh)==manifest["mesh_sha256"],"candidate MSH SHA mismatch")
        nodes,tets,faces=read_msh(mesh)
        full,min27=baseline_volumes(nodes,tets)
        a=sample(nodes,tets,full,7)
        b=sample(nodes,tets,full,9)
        q7=compare(a,ref,7);q9=compare(b,ref,9)
        q7vals=np.array([x["M1_over_M0_Q_V"] for x in q7["signed18"]]);
        q9vals=np.array([x["M1_over_M0_Q_V"] for x in q9["signed18"]]);
        delta=float(np.max(np.abs(q7vals-q9vals)))
        old_mean=ref["M0"]["volume_m3"]/ref["M0"]["tet10"]
        global7=(a["total_volume"]/len(tets))/old_mean
        global9=(b["total_volume"]/len(tets))/old_mean
        freeze=manifest.get("D027_preliminary_27QP",{})
        prelim=freeze.get("27qp_preliminary_all_pass") is True
        macros=q9["macros"]
        qmacro={x["name"]:x for x in macros}
        macro_hard=[]
        m0limit=fixed["macro_QP_effective_Veff_assessment"]["minimum_baseline_effective_Tet10_for_hard_macro"]
        for row in macros:
            if row["M0_Neff"]<m0limit:continue
            upper=(fixed["macro_QP_effective_Veff_assessment"]["populated_near_polar_d_le_0p5mm_ratio_max"]
                   if row["name"].startswith("near_0_500um_polar_abs_mu_ge_0p8") else
                   fixed["macro_QP_effective_Veff_assessment"]["populated_macro_ratio_max"])
            lower=fixed["macro_QP_effective_Veff_assessment"]["populated_macro_ratio_min"]
            macro_hard.append({"name":row["name"],"ratio":row["Q_V"],
                               "allowed":[lower,upper],"pass":lower<=row["Q_V"]<=upper})
        checks={
            "native_27QP_preliminary":prelim,
            "all_343QP_detJ_positive":a["min_detJ"]>0,
            "all_729QP_detJ_positive":b["min_detJ"]>0,
            "global_QV343_in_range":.8<=global7<=.85,
            "global_QV729_in_range":.8<=global9<=.85,
            "max_18_signed_QV343_729_delta_le_0p02":delta<=.02,
            "all_populated_macro_anti_coarsening":all(r["pass"] for r in macro_hard),
            "volume_closure_343":abs(a["total_volume"]/CAD_VOL-1)<.005,
            "volume_closure_729":abs(b["total_volume"]/CAD_VOL-1)<.005}
        return {"protocol":"P10GJ_R1_D027_INDEPENDENT_343_729QP_NO_FEM",
                "evidence_zip_sha256":sha(raw),"mesh_sha256":sha(mesh),
                "nodes":len(nodes)-1,"tet10":len(tets),
                "tri6_counts":{str(k):v for k,v in sorted(faces.items())},
                "minimum_detJ_27_343_729":[min27,a["min_detJ"],b["min_detJ"]],
                "global_QV343":global7,"global_QV729":global9,
                "max_signed18_QV343_729_delta":delta,
                "legacy_strict_18of18_count":int(sum(x["legacy_in_0p80_0p85"] for x in q9["signed18"])),
                "legacy_strict_18of18_pass":all(x["legacy_in_0p80_0p85"] for x in q9["signed18"]),
                "signed343":q7,"signed729":q9,"populated_macro_hard":macro_hard,
                "D027_checks":checks,"D027_robust_mesh_gate":all(checks.values()),
                "FEM_attempts":0,"FEM_authorized":False,
                "candidate_approval":"REQUIRES_INDEPENDENT_REVIEW_AND_SEPARATE_PERMISSION"}


def selftest():
    for order in (3,7,9):
        N,D,W=rule(order)
        verts=np.array(((0.,0.,0.),(.001,0.,0.),(0.,.001,0.),(0.,0.,.001)))
        p=np.concatenate((verts,np.array([.5*(verts[i]+verts[j]) for i,j in EDGE])))
        x,d=geom(p[None,:,:],N,D)
        need(abs(float((d@W)[0])-1e-9/6)<1e-20,"affine volume parity")
        need(bool(np.allclose(d,1e-9,rtol=1e-12,atol=1e-22)),"affine Jacobian")
        inverse_vertices=verts.copy();inverse_vertices[[1,2]]=inverse_vertices[[2,1]]
        bad=np.concatenate((inverse_vertices,np.array(
            [.5*(inverse_vertices[i]+inverse_vertices[j]) for i,j in EDGE])))
        need(bool(np.all(geom(bad[None,:,:],N,D)[1]<0)),"inverted Tet10 negative case")
        need(codes(np.array([[[0.,0.,.03105],[0.,0.,.02895]]])).tolist()==[[0,1]],
             "north/south signed near-pole classification")
    print("P10GJ_OFFLINE_3_7_9_QP_AFFINE_INVERTED_SIGNED_SELFTEST_PASS")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--selftest",action="store_true")
    p.add_argument("--evidence",type=Path)
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    selftest()
    if a.selftest:return
    need(a.evidence is not None,"need --evidence")
    result=adjudicate(a.evidence)
    if a.out:
        with a.out.open("x",encoding="utf-8") as f:
            json.dump(result,f,ensure_ascii=False,indent=2)
            f.write("\n")
    print("P10GJ_OFFLINE_RESULT",json.dumps({
        "D027_robust_mesh_gate":result["D027_robust_mesh_gate"],
        "global_QV729":result["global_QV729"],
        "legacy_strict_18of18_count":result["legacy_strict_18of18_count"]}))


if __name__=="__main__":main()
