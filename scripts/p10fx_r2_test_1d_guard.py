#!/usr/bin/env python3
"""Offline unit tests for R2 1D preflight diagnostics; no real Gmsh, 3D or FEM."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"research/proposals/P10FX_R2_NATIVE_1D_EVIDENCE_WINDOWS_20261122"
sys.path.insert(0,str(SRC))
spec=importlib.util.spec_from_file_location("p10fx_r2_guard",SRC/"P10FX_one_click_m1v.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def case(label, rc, log, write_mesh=True, size=1600):
    calls=[]

    def fake_run(cmd, **kwargs):
        calls.append(tuple(cmd))
        if "-version" in cmd:
            return subprocess.CompletedProcess(cmd,0,b"4.15.2\n")
        if "-parse_and_exit" in cmd:
            return subprocess.CompletedProcess(cmd,0,b"Info : Source parsed\n")
        if "-1" in cmd:
            if write_mesh:
                dst=Path(cmd[cmd.index("-o")+1])
                start=b"$MeshFormat\n2.2 0 8\n$EndMeshFormat\n$Nodes\n1\n1 0 0 0\n$EndNodes\n$Elements\n1\n"
                dst.write_bytes(start+b"0"*max(0,size-len(start)))
            return subprocess.CompletedProcess(cmd,rc,log.encode("utf-8"))
        raise AssertionError("unexpected native process")

    with tempfile.TemporaryDirectory(prefix="P10FX_R2_TEST_") as tmp:
        folder=Path(tmp)
        with patch.object(module.subprocess,"run",side_effect=fake_run):
            try:
                module.native_parse("Include \"M0.geo\";\n",folder)
                passed=True
            except RuntimeError:
                passed=False
        m=json.loads((folder/"P10FX_1D_GATE_METRICS.json").read_text())
        assert m["native_1d_verified"]==passed
        assert m["native_1d_exit"]==rc and m["native_3d_attempts"]==0
        assert m["FEM_attempts"]==0 and len(calls)==3
        assert all("-3" not in cmd for cmd in calls)
        print("P10FX_R2_1D_GUARD",label,"PASS" if passed else "STOP")
        return passed


def main():
    done="Info : Done meshing 1D\nInfo : Done writing mesh\n"
    assert case("valid",0,done)
    assert not case("nonzero_return_hidden_by_clean_log",1,done)
    assert not case("native_log_error",0,done+"Error : field failure\n")
    assert not case("output_mesh_absent",0,done,write_mesh=False)
    assert not case("output_mesh_too_small",0,done,size=200)
    assert not case("done_line_missing",0,"Info : Meshing 1D...\n")
    print("P10FX_R2_ALL_1D_DIAGNOSTIC_BRANCHES_TEST_PASS_NO_GMSH_NO_3D_NO_FEM")


if __name__=="__main__":
    main()
