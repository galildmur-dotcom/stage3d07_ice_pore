#!/usr/bin/env python3
"""Read-only independent audit of the exact P10CA one-H0 evidence ZIP.

This tool NEVER invokes FEM. It intentionally does not infer an OS exit code.
"""
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import Counter, defaultdict
from decimal import Decimal, getcontext
from pathlib import Path

getcontext().prec = 45


def D(value):
    d = Decimal(value)
    if not d.is_finite():
        raise ValueError("nonfinite numeric input")
    return d


def read_csv(z, name):
    with z.open(name) as stream:
        return list(csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8-sig")))


def main(path):
    data = path.read_bytes()
    findings = {"zip_sha256": hashlib.sha256(data).hexdigest(),
                "zip_bytes": len(data)}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        bad = z.testzip()
        assert bad is None, f"invalid zip member: {bad}"
        assert len(z.infolist()) == 13
        assert len(set(z.namelist())) == 13
        findings["zip_files"] = len(z.namelist())
        result = z.read("P10CA_RESULT.txt").decode("utf-8-sig")
        manifest = json.loads(z.read("P10CA_RUN_MANIFEST.json"))
        stdout = z.read("physical_stdout.txt").decode("utf-8-sig")
        stderr = z.read("physical_stderr.txt").decode("utf-8-sig")
        assert "P10CA_STOP physical ExitCode unavailable" in result
        assert "RESULT=P10CA_ONE_H0_PHYSICAL_QP_OK" not in result
        assert manifest["physical_attempted"] is True
        assert manifest["physical_verified"] is False
        assert "ORIGINAL_STATE_PRESERVED=YES" in result
        assert "P10BX_THERMAL_QP_INTEGRATED_OK" in stdout
        assert "P10W_ANALYTIC_ADJOINT_OK" in stdout
        assert "central_fd_evaluations=0" in stdout
        assert "P10W_ANALYTIC_ADJOINT_FAIL" not in stdout
        assert "P10BX_THERMAL_QP_INTEGRATED_FAIL" not in stdout
        assert "P10W_ERROR" not in stderr
        bins = read_csv(z, "P10BX_THERMAL_QP_STEP_BINS.csv")
        audits = read_csv(z, "P10BX_THERMAL_STEP_AUDIT.csv")
        gradients = read_csv(z, "P10W_ANALYTIC_ADJOINT.csv")
        components = read_csv(z, "P10W_COMPONENTS.csv")
        mechanical_steps = read_csv(z, "P10W_STEP_COMPONENTS.csv")
        assert (len(bins), len(audits), len(gradients), len(components),
                len(mechanical_steps)) == (606, 6, 3, 3, 18)
        assert sorted(int(a["step"]) for a in audits) == list(range(1, 7))
        assert Counter(int(b["step"]) for b in bins) == Counter({s: 101 for s in range(1, 7)})
        bystep = defaultdict(list)
        for b in bins:
            s = int(b["step"])
            sh, po = int(b["shell_bin"]), int(b["polar_bin"])
            assert b["mesh"] == "H0" and b["functional"] == "jpeak"
            assert D(b["time_s"]) == 150*s
            assert (sh == -1 and po == -1) or (0 <= sh < 10 and 0 <= po < 10)
            bystep[s].append(b)
            for k in ("mass_per_m", "diffusion_per_m", "robin_per_m", "total_per_m"):
                D(b[k])
            assert abs(D(b["mass_per_m"])+D(b["diffusion_per_m"])+
                       D(b["robin_per_m"])-D(b["total_per_m"])) < D("1e-12")
        radial = {i: {"total": Decimal(0), "mass": Decimal(0),
                      "diffusion": Decimal(0), "qp": 0, "volume": Decimal(0)}
                  for i in range(10)}
        polar = {i: Decimal(0) for i in range(10)}
        all_csr, all_qp = Decimal(0), Decimal(0)
        step_results = []
        for a in sorted(audits, key=lambda x: int(x["step"])):
            s = int(a["step"])
            rows = bystep[s]
            assert len({(int(r["shell_bin"]), int(r["polar_bin"])) for r in rows}) == 101
            top = [r for r in rows if r["shell_bin"] == "-1"]
            assert len(top) == 1 and top[0]["polar_bin"] == "-1"
            assert int(a["thermal_qp_count"]) == 472832
            assert int(a["top_robin_qp_count"]) == 2592
            assert D(a["top_robin_area_m2"]) > 0
            assert a["mesh"] == "H0" and a["functional"] == "jpeak"
            assert D(a["time_s"]) == s*150
            counts = sum(int(r["qp_count"]) for r in rows if r["shell_bin"] != "-1")
            assert counts == int(a["thermal_qp_count"])
            assert int(top[0]["qp_count"]) == int(a["top_robin_qp_count"])
            volume = sum((D(r["volume_m3"]) for r in rows if r["shell_bin"] != "-1"), Decimal(0))
            assert abs(volume-D(a["thermal_volume_m3"])) < D("1e-16")
            parts = {k:sum((D(r[k]) for r in rows), Decimal(0))
                     for k in ("mass_per_m", "diffusion_per_m", "robin_per_m", "total_per_m")}
            assert abs(parts["mass_per_m"]-D(a["qp_mass_per_m"])) < D("1e-12")
            assert abs(parts["diffusion_per_m"]-D(a["qp_diffusion_per_m"])) < D("1e-12")
            assert abs(parts["robin_per_m"]-D(a["qp_robin_per_m"])) < D("1e-12")
            qp, csr, tol = D(a["qp_total_per_m"]),D(a["csr_total_per_m"]),D(a["allowed_abs_error_per_m"])
            err = abs(qp-csr)
            assert abs(parts["total_per_m"]-qp) <= tol
            assert err <= tol
            assert abs(err-D(a["abs_partition_error_per_m"])) < D("1e-16")
            all_csr += csr
            all_qp += parts["total_per_m"]
            step_results.append({"step":s,"time_s":150*s,"qp_total_per_m":str(qp),
                                 "csr_total_per_m":str(csr),"absolute_error":str(err),
                                 "tolerance":str(tol),"local_sum_error":str(abs(parts["total_per_m"]-qp)),
                                 "mass_per_m":str(parts["mass_per_m"]),
                                 "diffusion_per_m":str(parts["diffusion_per_m"]),
                                 "robin_per_m":str(parts["robin_per_m"])})
            for r in rows:
                sh = int(r["shell_bin"])
                if sh < 0:
                    continue
                radial[sh]["total"] += D(r["total_per_m"])
                radial[sh]["mass"] += D(r["mass_per_m"])
                radial[sh]["diffusion"] += D(r["diffusion_per_m"])
                radial[sh]["qp"] += int(r["qp_count"])
                radial[sh]["volume"] += D(r["volume_m3"])
                polar[int(r["polar_bin"])] += D(r["total_per_m"])
        g = {row["functional"]:row for row in gradients}
        c = {row["functional"]:row for row in components}
        assert set(g) == set(c) == {"j6","jpeak","jen"}
        for k in g:
            gradient = g[k]
            assert (gradient["mesh"],gradient["law"],gradient["modulus"],gradient["mode"],
                    gradient["geometry_derivative_method"]) == ("H0","EDV","VAR","R","ANALYTIC_TET10")
            assert abs(D(gradient["mechanical_partial_per_m"])+D(gradient["thermal_adjoint_per_m"])-D(gradient["total_adjoint_per_m"])) < D("1e-12")
            assert abs(D(c[k]["total_mechanical_shape_per_m"])-D(gradient["mechanical_partial_per_m"])) < D("1e-12")
            assert abs(D(c[k]["total_adjoint_per_m"])-D(gradient["total_adjoint_per_m"])) < D("1e-12")
            rows = [r for r in mechanical_steps if r["functional"] == k]
            assert len(rows) == 6 and sorted(int(r["time_step"]) for r in rows) == list(range(1,7))
            for r in rows:
                mechanical_sum = sum((D(r[x]) for x in (
                    "explicit_objective_shape_per_m","equilibrium_residual_shape_per_m",
                    "internal_history_shape_per_m")),Decimal(0))
                assert abs(mechanical_sum-D(r["total_mechanical_shape_per_m"])) < D("1e-12")
            assert abs(sum((D(r["total_mechanical_shape_per_m"]) for r in rows),Decimal(0))-
                       D(gradient["mechanical_partial_per_m"])) < D("1e-11")
        assert abs(all_csr-D(g["jpeak"]["thermal_adjoint_per_m"])) < D("1e-10")
        assert abs(all_qp-D(g["jpeak"]["thermal_adjoint_per_m"])) < D("1e-10")
        findings["status"] = "STOP_EXE_EXITCODE_UNAVAILABLE_BUT_NUMERICAL_H0_QP_CSR_AUDIT_PASS"
        findings["result_note"] = "Not native exit0 certified; no re-run permitted by this audit"
        findings["mesh_sha256"] = manifest["mesh_sha256"]
        findings["exe_sha256"] = manifest["exe_sha256"]
        findings["wall_s"] = manifest["wall_seconds"]
        findings["max_observed_process_bytes"] = manifest["max_observed_process_bytes"]
        findings["max_observed_output_bytes"] = manifest["max_observed_output_bytes"]
        findings["allstep_csr_thermal_per_m"] = str(all_csr)
        findings["allstep_local_qp_thermal_per_m"] = str(all_qp)
        findings["allstep_abs_difference"] = str(abs(all_qp-all_csr))
        findings["functionals"] = {k:{q: g[k][q] for q in
            ("objective","mechanical_partial_per_m","thermal_adjoint_per_m",
             "total_adjoint_per_m")} for k in g}
        findings["steps"] = step_results
        findings["radial_shells"] = [{"shell_bin":i,
           **{k:(str(v) if isinstance(v,Decimal) else v) for k,v in vals.items()}}
           for i,vals in radial.items()]
        findings["polar_bands"] = [{"polar_bin":i,"total":str(val)}
                                    for i,val in polar.items()]
        findings["inner_0_to_2mm_thermal_per_m"] = str(sum((radial[i]["total"] for i in range(7)),Decimal(0)))
        findings["shell_2_to_5mm_thermal_per_m"] = str(radial[7]["total"])
        findings["outside_5mm_thermal_per_m"] = str(radial[8]["total"]+radial[9]["total"])
    print(json.dumps(findings,indent=2,ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
