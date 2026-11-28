#!/usr/bin/env python3
"""P10GR: bounded, one-shot 20-case Gmsh surface-parameter experiment."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import importlib.util
import csv
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
PROJECT = Path(r"G:\ildar\Stage3D07")
RUNS = PROJECT / "LOCAL_RUNS"
P10GP_ZIP = HERE / "P10GP_R1_SURFACE_SOURCE_ONLY.zip"
P10GP_SHA = "236defb377103ef45e8ac193264fac8213290c7d00e02fc1025e53c9f700cc3a"
P10GP_HELPER = HERE / "P10GP_windows_2d.py"
P10GP_HELPER_SHA = "__PIN_HELPER_SHA__"
P10GH_HELPER_SHA = "__PIN_GMSH_HELPER_SHA__"
PROOF = HERE / "P10GR_PREFLIGHT_PROOF.json"
RESULT = HERE / "P10GR_02_RESULT.txt"
GMSH_SHA = "317c43391e5b1fab3a1dd80dc5245dad6e2d087910f4b8ebc234bd6d4b8f41a1"
M0_SHA = "926a9c903765ce77fd560300d10614d3cece3d4cd4d7813027e45e92d33870d6"
REV = "P10GR_R1_PRESPECIFIED_20_SURFACE_CASES_NO_3D_FEM"
ALPHAS = (0.03, 0.06, 0.09)
MU_ENDS = (-0.7, -0.5, -0.2)  # plateau mu<=-0.8, fade to mu_end
ALGORITHMS = (5, 6)  # Delaunay vs Frontal-Delaunay
MAX_CASES = 20
MAX_LOG = 2 * 1024**2
MAX_MSH = 4 * 1024**2
MAX_TOTAL_ZIP = 100 * 1024**2
FACTOR = "0.9378887276834518"
OLD_TS = "min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/0.2))"


def need(value, reason):
    if not value: raise RuntimeError("P10GR_STOP: " + reason)


def sha(raw): return hashlib.sha256(raw).hexdigest()
def file_sha(path): return sha(path.read_bytes())
def utc(): return datetime.now(timezone.utc)


def load_helper():
    need(file_sha(P10GP_HELPER) == P10GP_HELPER_SHA, "P10GP helper hash mismatch")
    gmsh_helper = HERE / "P10GH_surface_compare.py"
    need(file_sha(gmsh_helper) == P10GH_HELPER_SHA, "Gmsh runtime hash mismatch")
    spec = importlib.util.spec_from_file_location("p10gr_gp", P10GP_HELPER)
    gp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gp)
    gp.RUNTIME_SHA = P10GH_HELPER_SHA
    return gp


def cases():
    out=[]
    for algorithm in ALGORITHMS:
        out.append((f"ALGO{algorithm}_A00_BASE",algorithm,0.,-0.6))
        for alpha in ALPHAS:
            for end in MU_ENDS:
                name=f"ALGO{algorithm}_A{int(round(100*alpha)):02d}_MU{int(round(100*abs(end))):02d}"
                out.append((name,algorithm,alpha,end))
    need(len(out)==MAX_CASES and len(set(x[0] for x in out))==MAX_CASES, "case count")
    return out


def generate():
    need(file_sha(P10GP_ZIP)==P10GP_SHA, "source ZIP changed")
    gp=load_helper()
    source=gp.parent_files()
    template=source["B_SELF_CONTAINED_C1_SOUTH/P10GP_SURFACE.geo"].decode("utf-8")
    base=source["A_ORIGINAL_F3/P10GP_SURFACE.geo"].decode("utf-8")
    need(template.count(OLD_TS)==3 and template.count("1-0.06*")==1,
         "original alpha/angle syntax changed")
    need(base.count("Background Field = 3")==1 and template.count("Background Field = 7")==1,
         "background field changed")
    output={}
    meta={}
    for name,alg,alpha,end in cases():
        if alpha==0:
            driver=base
        else:
            new_ts="min(1,max(0,(((z-0.03)/sqrt(x*x+y*y+(z-0.03)*(z-0.03)+1e-24))+0.8)/"+format(end+.8,".17g")+"))"
            driver=template.replace(OLD_TS,new_ts).replace("1-0.06*","1-"+format(alpha,".17g")+"*")
            need(driver.count(new_ts)==3 and "F3*" not in driver and "F4*" not in driver,
                 "nested size field reference or incomplete angle substitution")
        need(driver.count("Mesh.Algorithm = 5;")==1, "algorithm anchor changed")
        driver=driver.replace("Mesh.Algorithm = 5; // Delaunay surface; Tri6 with order 2",
                              f"Mesh.Algorithm = {alg}; // selected 2D algorithm; Tri6 with order 2")
        need(f"Mesh.Algorithm = {alg};" in driver and FACTOR in driver,
             "algorithm or global size factor changed")
        output[name+"/P10GR.geo"]=driver.encode("utf-8")
        for key in ("M0_ROTATED.geo","sphere_pore_B6_refined_rotated.geo"):
            original=source["A_ORIGINAL_F3/"+key]
            output[name+"/"+key]=original
        meta[name]={"algorithm":alg,"south_alpha":alpha,"south_plateau_mu_max":-.8,
                    "south_fade_mu_end":end,"expected_south_wall_h_ratio":1-alpha}
    return output,meta


def math_qa():
    """Independent alpha/angular window, C1 and no hidden field links."""
    files,meta=generate()
    m0=files[cases()[0][0]+"/M0_ROTATED.geo"].decode("utf-8")
    match=re.search(r"Field\[3\]\.F\s*=\s*StrCat\((.*?)\);",m0,re.S)
    need(match is not None,"original baseline MathEval missing")
    baseline="".join(re.findall(r'"([^"\\]*)"',match.group(1)))
    need(len(baseline)==732,"baseline source length changed")
    safe={"__builtins__":{},"sqrt":math.sqrt,"min":min,"max":max}
    baseline_code=compile(baseline,"original_field3","eval")
    max_error=0.
    for name,config in meta.items():
        a,end=config["south_alpha"],config["south_fade_mu_end"]
        samples=[]
        for i in range(2001):
            mu=-1+2*i/2000
            t=min(1.,max(0.,(mu+.8)/(end+.8)))
            f=1-a*(1-t*t*(3-2*t))
            samples.append(f)
        need(abs(min(samples)-(1-a))<1e-13 and abs(max(samples)-1)<1e-13,
             "incorrect angular factor range")
        driver=files[name+"/P10GR.geo"].decode("utf-8")
        need(not re.search(r"\bF[345]\b",re.sub(r'//[^\n]*','',driver)) if a else True,
             "nested field reference remains")
        if a:
            match=re.search(r"Field\[7\]\.F\s*=\s*StrCat\((.*?)\);",driver,re.S)
            need(match is not None,"inlined field missing")
            actual="".join(re.findall(r'"([^"\\]*)"',match.group(1)))
            need("F3" not in actual and "F4" not in actual and "F5" not in actual,
                 "indirect reference found")
            actual_code=compile(actual,"inlined_field7","eval")
        else:
            actual_code=baseline_code
        for j in range(11):
            d=.002*j/10
            r=.001+d
            tr=min(1.,max(0.,(d-.0005)/.0005))
            wr=1-tr*tr*(3-2*tr)
            for i in range(201):
                mu=-1+2*i/200
                xyz={"x":r*math.sqrt(max(0.,1-mu*mu)),"y":0.,"z":.03+r*mu}
                t=min(1.,max(0.,(mu+.8)/(end+.8)))
                ws=1-t*t*(3-2*t)
                base=eval(baseline_code,safe,xyz)
                observed=eval(actual_code,safe,xyz)
                expected=base*(1-a*wr*ws)
                max_error=max(max_error,abs(observed-expected))
                need(abs(observed-expected)<=2e-13 and observed>0.,
                     "full MathEval mismatch or nonpositive size")
    need(max_error<=2e-13,"field formula regression")
    return {"cases":len(meta),"angular_samples_per_case":2001,
            "full_field_evaluations_per_case":2211,"max_full_field_error_m":max_error,
            "alpha":list(ALPHAS),"mu_end":list(MU_ENDS),"algorithms":list(ALGORITHMS),
            "source_sha256":{k:sha(v) for k,v in files.items()}}


def neighbour_grading(mesh):
    """Face-adjacent surface Tri6 characteristic corner-edge jump statistics."""
    nodes={}; pore=[]
    with mesh.open("r",encoding="ascii") as stream:
        for line in stream:
            if line.strip()=="$Nodes":
                for _ in range(int(next(stream))):
                    b=next(stream).split();nodes[int(b[0])]=tuple(map(float,b[1:4]))
            if line.strip()=="$Elements":
                for _ in range(int(next(stream))):
                    b=list(map(int,next(stream).split()))
                    if b[1]==9 and b[3]==8:
                        pore.append(b[3+b[2]:3+b[2]+3])
    edge_map={}
    for cell in pore:
        p=[nodes[i] for i in cell]
        center=tuple(sum(v[k] for v in p)/3 for k in range(3))
        rho=math.dist(center,(0,0,.03))
        mu=(center[2]-.03)/rho
        lengths=[math.dist(p[a],p[b]) for a,b in ((0,1),(1,2),(2,0))]
        characteristic=statistics.median(lengths)
        for i,j in ((0,1),(1,2),(2,0)):
            edge_map.setdefault(tuple(sorted((cell[i],cell[j]))),[]).append((characteristic,mu))
    values={"all":[],"north":[],"south":[]}
    for attached in edge_map.values():
        need(len(attached)==2,"pore triangulation not 2-manifold")
        jump=max(attached[0][0],attached[1][0])/min(attached[0][0],attached[1][0])
        values["all"].append(jump)
        if any(mu>=.8 for _,mu in attached):values["north"].append(jump)
        if any(mu<=-.8 for _,mu in attached):values["south"].append(jump)
    def q95(v):
        s=sorted(v);pos=(len(s)-1)*.95;i=int(pos)
        return s[i]+(s[min(i+1,len(s)-1)]-s[i])*(pos-i)
    return {zone:{"pairs":len(v),"p95":q95(v),"max":max(v)} for zone,v in values.items()}


def write_comparison(folder,result):
    """Exploratory ranking, never a geometry or D-027 GO decision."""
    cases_result=result["cases"]
    rows=[]
    for name,algorithm,alpha,end in cases():
        x=cases_result.get(name)
        if not x or x["status"]!="PASS":continue
        a=cases_result.get(f"ALGO{algorithm}_A00_BASE")
        if not a or a["status"]!="PASS":continue
        size=x["pore_edge_size"];bs=a["pore_edge_size"]
        def ratio(z):return size[z]["median_edge_m"]/bs[z]["median_edge_m"]
        q=x["surface"]["q_corner_min"];base_q=a["surface"]["q_corner_min"]
        g=x["neighbour_grading"]["all"]["max"]
        south_grad=x["neighbour_grading"]["south"]["max"]
        south_ratio=ratio("south");north_ratio=ratio("north");equator_ratio=ratio("equator")
        rows.append({"case":name,"algorithm":algorithm,"alpha":alpha,"mu_end":end,
                     "south_edge_B_over_baseline":south_ratio,
                     "north_edge_B_over_baseline":north_ratio,
                     "equator_edge_B_over_baseline":equator_ratio,
                     "q_corner_min":q,"q_corner_min_over_baseline":q/base_q,
                     "q_corner_p05":x["surface"]["q_corner_p05"],
                     "pore_tri6":x["surface"]["pore_tri6"],
                     "neighbor_all_max":g,"neighbor_south_max":south_grad,
                     "neighbor_all_p95":x["neighbour_grading"]["all"]["p95"],
                     "exploratory_screening":int(alpha>0 and south_ratio<=.98 and
                          abs(north_ratio-1)<=.03 and abs(equator_ratio-1)<=.03 and
                          q>=.45 and g<=2.2)})
    rows.sort(key=lambda v:(-v["exploratory_screening"],v["south_edge_B_over_baseline"],
                            -v["q_corner_min"],v["neighbor_all_max"]))
    if rows:
        with (folder/"P10GR_COMPARISON.csv").open("x",encoding="utf-8",newline="") as out:
            writer=csv.DictWriter(out,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    result["comparison_rows"]=len(rows)
    result["selection_rule"]="exploratory_screening, not D027/3D GO; no auto winner"


def get_markers():
    user=os.environ.get("LOCALAPPDATA","")
    need(user and Path(user).is_dir(), "LOCALAPPDATA unavailable")
    return (RUNS/"P10GR_LOCKS"/(M0_SHA[:24]+".json"),
            Path(user)/"Stage3D07"/"P10GR_SCAN"/(M0_SHA[:24]+".json"))


def free():
    need(all(not p.exists() for p in get_markers()), "one-shot already consumed; never retry 02")


def write_files(folder,files):
    for name,data in files.items():
        path=folder/name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open("xb") as out: out.write(data)
        need(file_sha(path)==sha(data), "generated GEO bytes differ")


def windows_installed(gp):
    installed=gp.installation()
    need(installed["Gmsh_SHA256"]==GMSH_SHA and installed["M0_SHA256"]==M0_SHA,
         "Windows pin changed")
    return installed


def evidence(folder):
    dest=folder/"P10GR_SCAN_EVIDENCE.zip"
    with zipfile.ZipFile(dest,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path!=dest and path.suffix.lower() in (".geo",".log",".msh",".json",".txt",".csv"):
                z.write(path,path.relative_to(folder).as_posix())
    need(dest.stat().st_size <= MAX_TOTAL_ZIP and zipfile.ZipFile(dest).testzip() is None,
         "evidence size/CRC")
    print("P10GR_SEND_ONE_EVIDENCE_ZIP",dest,flush=True)
    return dest


def dump(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def preflight():
    gp=load_helper(); files,meta=generate(); q=math_qa(); installed=windows_installed(gp); free()
    folder=RUNS/("P10GR_PREFLIGHT_"+utc().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(exist_ok=False)
    write_files(folder,files)
    parse=[]
    for name,_,_,_ in cases():
        geo=folder/name/"P10GR.geo"
        cmd=[str(gp.GMSH),str(geo),"-parse_and_exit","-nopopup","-nt","2"]
        run=subprocess.run(cmd,cwd=geo.parent,capture_output=True,timeout=45)
        logs=run.stdout+run.stderr
        (geo.parent/"P10GR_PARSE.log").write_bytes(logs)
        need(run.returncode==0 and not re.search(rb"\bError\s*:",logs),name+" parse STOP")
        parse.append({"case":name,"exit":run.returncode,"log_sha256":sha(logs)})
    proof={"revision":REV,"time":utc().isoformat(),"installed":installed,
           "source_sha256":q["source_sha256"],"cases":meta,"parse":parse,
           "native_2d":0,"native_3d":0,"FEM":0}
    dump(PROOF,proof); dump(folder/"P10GR_PREFLIGHT.json",proof)
    evidence(folder)
    print("P10GR_PREFLIGHT_PASS_NO_MESH",flush=True)


def scan():
    gp=load_helper(); files,meta=generate(); installed=windows_installed(gp); free()
    need(PROOF.is_file(),"run 01 first")
    proof=json.loads(PROOF.read_text(encoding="utf-8"))
    age=(utc()-datetime.fromisoformat(proof["time"])).total_seconds()
    need(proof["revision"]==REV and proof["installed"]==installed and
         proof["source_sha256"]=={k:sha(v) for k,v in files.items()} and 0<=age<=24*3600,
         "preflight expired/changed")
    folder=RUNS/("P10GR_SCAN_"+utc().strftime("%Y%m%d_%H%M%S_%f"))
    folder.mkdir(exist_ok=False)
    write_files(folder,files)
    for marker in get_markers():
        marker.parent.mkdir(parents=True,exist_ok=True)
        with marker.open("x",encoding="utf-8") as f:
            json.dump({"revision":REV,"created":utc().isoformat(),"max_2d_cases":MAX_CASES},f)
    result={"revision":REV,"status":"STOP_INCOMPLETE", "native_2d_attempts":0,
            "native_3d_attempts":0,"FEM_attempts":0,"cases":{},"installed":installed,
            "case_policy":meta}
    try:
        gmsh=gp.load_runtime()
        gmsh.MAX_SECONDS=90
        gmsh.MAX_MSH=MAX_MSH
        gmsh.MAX_LOG=MAX_LOG
        for index,(name,alg,alpha,end) in enumerate(cases(),1):
            path=folder/name
            print(f"P10GR_CASE {index}/{MAX_CASES} {name}: native -2 90s 2GiB; no 3D/FEM",flush=True)
            result["native_2d_attempts"]+=1
            try:
                native=gmsh.run_surface_bounded(path/"P10GR.geo",path/"P10GR.msh",path/"P10GR.log")
                surface=gmsh.audit_surface(path/"P10GR.msh")
                size=gp.pore_edge_sizes(path/"P10GR.msh")
                grading=neighbour_grading(path/"P10GR.msh")
                row={"status":"PASS","native":native,"surface":surface,
                     "pore_edge_size":size,"neighbour_grading":grading}
            except Exception as exc:
                row={"status":"STOP","error":repr(exc)}
            result["cases"][name]=row
            dump(folder/"P10GR_PROGRESS.json",result)
            if row["status"]!="PASS":
                result["status"]="STOP_AFTER_CASE_"+name
                break
        else:
            result["status"]="ALL_20_2D_COMPLETED_PENDING_INDEPENDENT_AUDIT"
    except Exception as exc:
        result["error"]=repr(exc)
        (folder/"P10GR_STOP_TRACE.txt").write_text(traceback.format_exc(),encoding="utf-8")
    finally:
        try:
            write_comparison(folder,result)
        except Exception as exc:
            result["comparison_error"]=repr(exc)
        dump(folder/"P10GR_MANIFEST.json",result)
        out=evidence(folder)
        RESULT.write_text("P10GR_RESULT="+result["status"]+"\nEVIDENCE="+str(out)+
                          "\nDO_NOT_REPEAT_02=YES\n",encoding="utf-8")
    return 0 if result["status"].startswith("ALL_20") else 2


def main():
    need(len(sys.argv)==2,"use --selftest/--preflight/--one-scan")
    if sys.argv[1]=="--selftest":
        stats=math_qa();print("P10GR_SOURCE_MATH_20_CASES_PASS",stats["cases"],flush=True)
        return 0
    if sys.argv[1]=="--preflight":
        preflight();return 0
    if sys.argv[1]=="--one-scan": return scan()
    need(False,"unknown command")


if __name__=="__main__":
    try:raise SystemExit(main())
    except Exception as exc:
        print("P10GR_STOP",repr(exc),file=sys.stderr,flush=True)
        raise SystemExit(2)
