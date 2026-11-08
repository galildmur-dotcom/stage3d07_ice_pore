#!/usr/bin/env python3
"""Independent VTK readback and CONST/VAR paired field checks. Requires python-vtk & numpy."""
import argparse, csv, json, math
from pathlib import Path
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

ROOT = Path(__file__).resolve().parents[1]

def inspect(path: Path):
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(str(path))
    reader.Update()
    if reader.GetErrorCode():
        raise ValueError(f"VTK reader error {path}: {reader.GetErrorCode()}")
    grid = reader.GetOutput()
    points, cells = grid.GetNumberOfPoints(), grid.GetNumberOfCells()
    if not points or not cells:
        raise ValueError(f"Empty VTU: {path}")
    if not all(grid.GetCellType(i) == vtk.VTK_QUADRATIC_TETRA for i in range(cells)):
        raise ValueError(f"Non-Tet10 cell: {path}")
    pd, cd = grid.GetPointData(),grid.GetCellData()
    for key in ("Displacement_m", "Temperature_C"):
        if pd.GetArray(key) is None: raise ValueError(f"No {key}: {path}")
    for key in ("Sigma_xx_MPa","Sigma_yy_MPa","Sigma_zz_MPa","Principal_max_MPa", "Von_Mises_MPa"):
        if cd.GetArray(key) is None: raise ValueError(f"No {key}: {path}")
    u = vtk_to_numpy(pd.GetArray("Displacement_m"))
    s1 = vtk_to_numpy(cd.GetArray("Principal_max_MPa"))
    vm = vtk_to_numpy(cd.GetArray("Von_Mises_MPa"))
    coord=vtk_to_numpy(grid.GetPoints().GetData())
    if not np.isfinite(u).all() or not np.isfinite(s1).all() or not np.isfinite(vm).all():
        raise ValueError(f"Non-finite fields: {path}")
    if u.shape != (points,3):raise ValueError("Displacement is not 3D")
    j = int(np.argmax(s1))
    corners=[grid.GetCell(j).GetPointId(i) for i in range(4)]
    center=coord[corners].mean(axis=0)
    return {"points":points,"Tet10":cells,"max_s1_MPa":float(s1[j]),"min_s1_MPa":float(s1.min()),
            "max_von_mises_MPa":float(vm.max()),"max_displacement_m":float(np.linalg.norm(u,axis=1).max()),
            "peak_element_id":j,"peak_approx_xyz_m":center.tolist(),"u":u,"s1":s1,"coords":coord}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--results",default=str(ROOT/"results"))
    args=p.parse_args()
    folder=Path(args.results)
    rows=[]
    targets=["mechanics_H0","mechanics_H1","mechanics_H2","mechanics_H0_t900", "mechanics_H0_t1800", "mechanics_H0_q4"]
    for name in targets:
        d=folder/name
        if not d.exists():continue
        time=int(name.split("_t")[-1]) if "_t" in name else 3600
        fconst=d/f"E_CONST_t{time}.vtu"; fvar=d/f"E_VAR_t{time}.vtu"
        if not fconst.exists() or not fvar.exists():raise FileNotFoundError(f"Missing paired field in {d}")
        c=inspect(fconst);v=inspect(fvar)
        if c["points"] != v["points"] or c["Tet10"] != v["Tet10"]:raise ValueError("Paired mesh mismatch")
        if np.abs(c["coords"]-v["coords"]).max()>1e-13:raise ValueError("Paired coordinates mismatch")
        s1diff=v["s1"]-c["s1"]
        normdu=np.linalg.norm(v["u"]-c["u"],axis=1)
        rows.append({"case":name,"nodes":c["points"],"Tet10":c["Tet10"],
            "sigma1_max_CONST_MPa":c["max_s1_MPa"],"sigma1_max_VAR_MPa":v["max_s1_MPa"],
            "sigma1_max_delta_MPa":v["max_s1_MPa"]-c["max_s1_MPa"],
            "sigma1_max_delta_percent":100*(v["max_s1_MPa"]-c["max_s1_MPa"])/abs(c["max_s1_MPa"]),
            "sigma1_pointwise_RMS_delta_MPa":float(np.sqrt(np.mean(s1diff**2))),
            "sigma1_pointwise_max_abs_delta_MPa":float(np.max(np.abs(s1diff))),
            "displacement_max_abs_pair_delta_m":float(normdu.max()),
            "peak_CONST_x_m":c["peak_approx_xyz_m"][0],"peak_CONST_y_m":c["peak_approx_xyz_m"][1],"peak_CONST_z_m":c["peak_approx_xyz_m"][2],
            "peak_VAR_x_m":v["peak_approx_xyz_m"][0],"peak_VAR_y_m":v["peak_approx_xyz_m"][1],"peak_VAR_z_m":v["peak_approx_xyz_m"][2],
        })
    if not rows:raise ValueError("No VTU found")
    out=folder/"paired_fields_vtk_check.csv";out.parent.mkdir(parents=True,exist_ok=True)
    with out.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (folder/"VTK_verification.json").open("w") as f:
        json.dump({"status":"PASS","vtk_version":vtk.vtkVersion.GetVTKVersion(),"paired_cases":len(rows),"files_checked":len(rows)*2},f,indent=2)
    for r in rows:print(r["case"],"nodes",r["nodes"],"max sigma1",r["sigma1_max_CONST_MPa"],r["sigma1_max_VAR_MPa"],"delta %",r["sigma1_max_delta_percent"])
    print("Verified",len(rows)*2,"VTU, output",out)
if __name__=="__main__":main()
