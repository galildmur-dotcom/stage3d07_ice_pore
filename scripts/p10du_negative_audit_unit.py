#!/usr/bin/env python3
"""Negative controls on copies of P10DT ZIP; no Gmsh/FEM and no original edits."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
INPUT = HERE.parent/"research/evidence/P10DU_P10DT_REAL_NESTED_F3_1D_STOP_20261121/input/P10DT_EVIDENCE.zip"
spec = importlib.util.spec_from_file_location("p10du_readonly_auditor", HERE/"p10du_audit_p10dt_windows.py")
assert spec and spec.loader
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)


def must_fail(path: Path, expected: str, verify_outer: bool = False) -> None:
    try:
        auditor.audit(path, verify_outer_sha=verify_outer)
    except ValueError as err:
        assert expected in str(err), (expected, str(err))
    else:
        raise AssertionError("modified evidence was accepted: " + expected)


def mutate(path: Path, target: str, update) -> None:
    with zipfile.ZipFile(INPUT) as z:
        content = {name: z.read(name) for name in z.namelist()}
    content[target] = update(content[target])
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in content.items():
            z.writestr(name, data)


def change_json(data: bytes, field: str, value: str) -> bytes:
    obj = json.loads(data)
    obj[field] = value
    return (json.dumps(obj, ensure_ascii=False)+"\n").encode("utf-8")


def change_argv(data: bytes) -> bytes:
    obj = json.loads(data)
    obj["variants"][1]["argv"][2] = "-3"
    return (json.dumps(obj, ensure_ascii=False)+"\n").encode("utf-8")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="p10du_negative_") as tmp:
        target = Path(tmp)/"altered.zip"
        mutate(target, "GEO/B_NESTED_CONSTANT_F3.geo", lambda b: b+b"\n// TAMPER")
        must_fail(target, "original Windows ZIP SHA changed", verify_outer=True)
        must_fail(target, "original Windows generated GEO bytes")
        mutate(target, "B_NESTED_CONSTANT_F3_TAIL.txt", lambda b: b+b"\n// TAMPER")
        must_fail(target, "full native Gmsh stdout log")
        mutate(target, "P10DT_RUN_MANIFEST.json", lambda b: change_json(b, "status", "FAKE_PASS"))
        must_fail(target, "evidence result/status")
        mutate(target, "P10DT_RUN_MANIFEST.json", change_argv)
        must_fail(target, "one-dimensional native argv")
        mutate(target, "P10DT_RUN_MANIFEST.json", lambda b: change_json(
            b, "accepted_original_m1_sha256", "NOT_THE_ORIGINAL_M1"))
        must_fail(target, "Windows preflight/Gmsh/M1/limits/no-FEM")
    print("P10DU_NEGATIVE_AUDIT_OK outer_SHA_STOP=1 GEO_STOP=1 log_tail_STOP=1",
          "status_STOP=1 mode_3D_STOP=1 original_M1_STOP=1 native_Gmsh=0 FEM=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
