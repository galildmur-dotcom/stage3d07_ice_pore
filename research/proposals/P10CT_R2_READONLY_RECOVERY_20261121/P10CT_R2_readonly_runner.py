#!/usr/bin/env python3
"""One-shot, SHA-gated read-only QA of the existing P10CT R1 Windows U0 mesh.

No Gmsh, no FEM, no changes to the original .msh. All Python stderr is saved.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

REV = "P10CT_R2_READONLY_RECOVERY_20261121"
MESH_SHA = "1a4690d1c57c8b520d596f9a864f754a8d84151bfd1fdd36f56631488779c6a3"
MESH_BYTES = 16218389
PINNED = {
    "P10CT_R2_u0_mesh_audit.py": "4e519954eed039fa2b05dcbb8efa9931fdee2b1611d87084a59cb0746d57e7d3",
    "P10CK_curved_qp_audit.py": "6386d37ade7c6cadcfdfdb511e01a06310ea9c974ee4fd7878a704bcdac9dc90",
    "P10CP_mesh_b6_profile.py": "675bc41523af2013cfdce59ac66c25417e5e7efd9a400c6088b8c454788360f3",
}
MESH_OBSERVED = Path(r"G:\Downloads\P10CT_R1_U0_MESH_ONLY_WINDOWS_20261121\P10CT_RUNS\P10CT_20261121_051002_957\P10CT_U0_h2mm.msh")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def find_mesh(root: Path):
    # Exact path from the ORIGINAL P10CT Gmsh STDOUT, then narrow same-run fallbacks.
    candidate = [MESH_OBSERVED]
    for parent in [Path(r"G:\Downloads"), Path.home() / "Downloads", root.parent]:
        base = parent / "P10CT_R1_U0_MESH_ONLY_WINDOWS_20261121" / "P10CT_RUNS"
        if base.is_dir():
            candidate.extend(sorted(base.glob("P10CT_*/P10CT_U0_h2mm.msh")))
    present = [x for x in dict.fromkeys(candidate) if x.is_file()]
    if not present:
        raise FileNotFoundError("Original P10CT U0 .msh not found at logged G:\\Downloads path or narrow fallback; no new Gmsh allowed")
    for p in present:
        if p.stat().st_size == MESH_BYTES and sha256(p) == MESH_SHA:
            return p
    raise ValueError("Existing .msh differs from pinned original P10CT SHA-256 or size; STOP without substitution")


def run_python(args, timeout, stdout_file, stderr_file):
    started = time.monotonic()
    try:
        cp = subprocess.run([sys.executable, *args], text=True, encoding="utf-8",
                            errors="replace", capture_output=True, timeout=timeout,
                            cwd=Path(__file__).resolve().parent, check=False)
        stdout_file.write_text(cp.stdout, encoding="utf-8")
        stderr_file.write_text(cp.stderr, encoding="utf-8")
        return cp.returncode, round(time.monotonic() - started, 3)
    except subprocess.TimeoutExpired as exc:
        stdout_file.write_text((exc.stdout or b"").decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or ""), encoding="utf-8")
        stderr_file.write_text((exc.stderr or b"").decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or ""), encoding="utf-8")
        raise TimeoutError("READONLY_QA_TIME_GUARD_600S") from exc


def main():
    root = Path(__file__).resolve().parent
    # Never write into the user's Stage3D07 source project or source mesh run.
    try:
        root.relative_to(Path(r"G:\ildar\Stage3D07"))
    except ValueError:
        pass
    else:
        print("RESULT=P10CT_R2_STOP_TOOL_EXTRACTED_INSIDE_PROJECT", flush=True)
        return 2

    run_root = root / "P10CT_R2_RUNS"
    if run_root.exists() and any(run_root.iterdir()):
        print("RESULT=P10CT_R2_STOP_ALREADY_ATTEMPTED_HERE", flush=True)
        return 2
    run_root.mkdir(exist_ok=True)
    run_dir = run_root / datetime.now(timezone.utc).strftime("P10CT_R2_%Y%m%d_%H%M%S_%f_UTC")
    run_dir.mkdir(exist_ok=False)
    lines = [f"TOOL_REVISION={REV}", "GMSH_CALLS=0", "PHYSICAL_FEM_RUNS=0",
             "SOURCE_MESH_WRITES=0", "EXPECTED_ORIGINAL_MESH_SHA256=" + MESH_SHA,
             "EXPECTED_ORIGINAL_MESH_BYTES=" + str(MESH_BYTES)]
    status = "P10CT_R2_STOP_READONLY_NO_FEM"
    exitcode = 2
    began = time.monotonic()
    try:
        for name, expected in PINNED.items():
            path = root / name
            if not path.is_file() or sha256(path) != expected:
                raise ValueError("PINNED_SOURCE_SHA_MISMATCH_OR_MISSING: " + name)
        lines.append("PINNED_SOURCE_SHA=PASS_3_OF_3")
        mesh = find_mesh(root)
        lines.append("EXISTING_MESH_SHA=PASS")
        lines.append("EXISTING_MESH_PATH=" + str(mesh))

        unit_out = run_dir / "P10CT_R2_UNIT_STDOUT.txt"
        unit_err = run_dir / "P10CT_R2_UNIT_STDERR.txt"
        unit_code, unit_secs = run_python([str(root / "P10CT_R2_u0_mesh_audit.py"), "--selftest"], 60, unit_out, unit_err)
        lines.append("UNIT_EXIT=" + str(unit_code))
        lines.append("UNIT_SECONDS=" + str(unit_secs))
        if unit_code != 0:
            raise RuntimeError("SELFTEST_FAILED: see complete stderr in evidence")

        qa_dir = run_dir / "QA"
        qa_dir.mkdir()
        qa_code, qa_secs = run_python([str(root / "P10CT_R2_u0_mesh_audit.py"),
                                       "--mesh", str(mesh), "--out-dir", str(qa_dir),
                                       "--target-size-mm", "2.0"], 600,
                                      run_dir / "P10CT_R2_QA_STDOUT.txt", run_dir / "P10CT_R2_QA_STDERR.txt")
        lines.append("QA_EXIT=" + str(qa_code))
        lines.append("QA_SECONDS=" + str(qa_secs))
        if qa_code != 0:
            raise RuntimeError("READONLY_QA_FAILED: exact Python traceback retained in evidence")
        summary_path = qa_dir / "P10CT_U0_SUMMARY.json"
        if not summary_path.is_file():
            raise RuntimeError("READONLY_QA_EXIT0_BUT_SUMMARY_ABSENT")
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("mesh_sha256") != MESH_SHA:
            raise ValueError("FINAL_QA_MESH_SHA_MISMATCH")
        lines += ["QA_ALL_TET10_27QP=" + str(summary.get("curved_27qp_samples")),
                  "QA_CURVED_NONPOSITIVE_COUNT=" + str(summary.get("curved_qp_nonpositive_count")),
                  "QA_CURVED_BAD_TET10=" + str(summary.get("curved_tet10_with_nonpositive_27qp_count")),
                  "QA_GEOMETRY_ONLY_ACCEPTANCE=" + str(summary.get("geometry_only_acceptance")),
                  "QA_CORNER_CENTROIDS_INSIDE_PORE=" + str(summary.get("zone_profile", {}).get("corner_centroid_inside_pore", {}).get("tet10"))]
        status = "P10CT_R2_READONLY_U0_QA_COMPLETE_NO_FEM"
        exitcode = 0
    except Exception as exc:
        lines.append("STOP_TYPE=" + type(exc).__name__)
        lines.append("STOP_REASON=" + str(exc))
        (run_dir / "P10CT_R2_STOP_TRACE.txt").write_text(traceback.format_exc(), encoding="utf-8")
    finally:
        lines += ["WALL_SECONDS=" + str(round(time.monotonic() - began, 3)), "RESULT=" + status]
        (run_dir / "P10CT_R2_RESULT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        evidence = run_dir / "P10CT_R2_EVIDENCE.zip"
        with zipfile.ZipFile(evidence, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as out:
            for src in sorted(run_dir.rglob("*")):
                if src.is_file() and src != evidence:
                    out.write(src, src.relative_to(run_dir).as_posix())
        print("RESULT=" + status, flush=True)
        print("EVIDENCE=" + str(evidence), flush=True)
    return exitcode


if __name__ == "__main__":
    sys.exit(main())
