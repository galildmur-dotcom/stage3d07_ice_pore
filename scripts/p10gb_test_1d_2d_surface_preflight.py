#!/usr/bin/env python3
"""Offline 1D+2D source gate tests for P10GB; no native Gmsh/3D/FEM."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10GB_M1W_DAMPED_18_ZONE_SURFACE_PREFLIGHT_WINDOWS_20261122"
sys.path.insert(0,str(SRC))
spec=importlib.util.spec_from_file_location("p10gb_native_preflight",SRC/"P10GB_one_click_m1w.py")
app=importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def mesh1(path):
    path.write_bytes(b"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n1\n1 0 0 0\n$EndNodes\n"
                     b"$Elements\n1\n1 8 2 1 1 1 1 1\n$EndElements\n"+b" "*1200)


def mesh2(path,north,south,off,phys=8):
    node=[];tri=[];num=0
    for kind,amount in (("N",north),("S",south),("O",off)):
        for _ in range(amount):
            if kind=="N":
                points=[(0,0,.031),(.000001,0,.031),(0,.000001,.031)]
            elif kind=="S":
                points=[(0,0,.029),(.000001,0,.029),(0,.000001,.029)]
            else:
                points=[(.001,0,.03),(.001,.000001,.03),(.001,0,.030001)]
            ids=[]
            for p in points+points:
                num+=1;ids.append(num)
                node.append(f"{num} {p[0]:.12g} {p[1]:.12g} {p[2]:.12g}")
            tri.append(f"{len(tri)+1} 9 2 {phys} 7 "+" ".join(map(str,ids)))
    body="$MeshFormat\n2.2 0 8\n$EndMeshFormat\n"
    body+=f"$Nodes\n{len(node)}\n"+"\n".join(node)+"\n$EndNodes\n"
    body+=f"$Elements\n{len(tri)}\n"+"\n".join(tri)+"\n$EndElements\n"
    path.write_text(body,encoding="ascii")


def run_case(name,north,south,off,exit2=0,should_pass=False):
    commands=[]

    def fake_run(cmd,**kwargs):
        commands.append(tuple(cmd))
        if "-version" in cmd:
            return subprocess.CompletedProcess(cmd,0,b"4.15.2\n")
        if "-parse_and_exit" in cmd:
            return subprocess.CompletedProcess(cmd,0,b"Info : Done reading GEO\n")
        if "-1" in cmd:
            assert "-save_all" in cmd
            mesh1(Path(cmd[cmd.index("-o")+1]))
            return subprocess.CompletedProcess(cmd,0,b"Info : Done meshing 1D\n")
        if "-2" in cmd:
            assert "-save_all" not in cmd
            mesh2(Path(cmd[cmd.index("-o")+1]),north,south,off)
            return subprocess.CompletedProcess(cmd,exit2,b"Info : Done meshing 2D\n")
        raise AssertionError("unexpected native call")

    with tempfile.TemporaryDirectory(prefix="P10GB_2D_TEST_") as tmp:
        folder=Path(tmp)
        with patch.object(app.subprocess,"run",side_effect=fake_run):
            try:
                app.native_parse('Include "M0.geo";\n',folder)
                success=True
            except RuntimeError:
                success=False
        assert success is should_pass,(name,success,should_pass)
        assert len(commands)==4 and all("-3" not in cmd for cmd in commands)
        m=json.loads((folder/"P10GB_2D_SURFACE_GATE.json").read_text())
        assert m["polar_surface_gate"] is should_pass and m["native_3d_attempts"]==0
        assert m["geometry_surface_stats"].get("north_polar_tri6")==north if exit2==0 else True
        print("P10GB_2D_SURFACE_GUARD",name,"PASS" if success else "STOP")


def main():
    run_case("M0_or_better_18N_20S",18,20,122,should_pass=True)
    run_case("P10FX_M1V_17N_22S",17,22,147,should_pass=False)
    run_case("southern_underresolved",19,19,150,should_pass=False)
    run_case("overall_pore_too_coarse",18,20,120,should_pass=False)
    run_case("native_2D_nonzero_exit",18,20,122,exit2=1,should_pass=False)
    print("P10GB_SOURCE_ONLY_1D_2D_SURFACE_GATE_TEST_PASS_NO_GMSH_NO_3D_NO_FEM")


if __name__=="__main__":
    main()
