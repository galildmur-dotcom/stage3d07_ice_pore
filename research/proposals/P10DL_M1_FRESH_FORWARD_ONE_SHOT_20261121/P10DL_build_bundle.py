#!/usr/bin/env python3
"""Produce deterministic standalone P10DL Windows ZIP, never starting physical FEM."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGET = REPO / "research/packages/P10DL_R1_M1_FRESH_FORWARD_ONE_SHOT_WINDOWS_20261121.zip"
P10DK = REPO / "research/proposals/P10DK_M1_FULL4D_SOURCE_ONLY_20261121"
P10DD = REPO / "research/proposals/P10DD_M0_H0_FULL4D_20261121"
EXTRA = {
    "CMakeLists.txt": HERE / "CMakeLists.txt",
    "stage3d10dl_m1_full4d.cpp": HERE / "stage3d10dl_m1_full4d.cpp",
    "stage3d10dk_m1_full4d.cpp": P10DK / "stage3d10dk_m1_full4d.cpp",
    "stage3d10dd_4d_partition.hpp": P10DD / "stage3d10dd_4d_partition.hpp",
    "p10dd_4d_synthetic_unit.cpp": P10DD / "p10dd_4d_synthetic_unit.cpp",
    "P10DK_audit_evidence.py": P10DK / "P10DK_audit_evidence.py",
    "P10DL_one_click_m1.py": HERE / "P10DL_one_click_m1.py",
    "01_RUN_ONE_P10DL_M1.cmd": HERE / "01_RUN_ONE_P10DL_M1.cmd",
    "README_RU.md": HERE / "README_RU.md",
}


def main() -> None:
    paths = dict(EXTRA)
    for name in ("src", "tests"):
        for source in sorted((REPO / name).iterdir()):
            if source.is_file() and source.suffix in {".cpp", ".hpp", ".inc"}:
                paths[f"{name}/{source.name}"] = source
    if len(paths) < 90:
        raise RuntimeError("P10DL source inventory unexpectedly short")
    data = {}
    for key, path in sorted(paths.items()):
        blob = path.read_bytes()
        if key.endswith(".cmd"):
            blob = blob.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
        data[key] = blob
    digest_table = "".join(f"{sha256(data[name]).hexdigest()}  {name}\n"
                           for name in sorted(data))
    data["P10DL_SOURCE_SHA256SUMS.txt"] = digest_table.encode("utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8) as z:
        for name, contents in sorted(data.items()):
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, contents, compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=8)
    with zipfile.ZipFile(TARGET) as z:
        if z.testzip() is not None or len(z.namelist()) != len(data):
            raise RuntimeError("P10DL ZIP CRC/count failed")
        with tempfile.TemporaryDirectory(prefix="p10dl_isolated_") as tmp:
            dest = Path(tmp)
            z.extractall(dest)
            result = subprocess.run([sys.executable, str(dest / "P10DL_one_click_m1.py"),
                                     "--selftest"], cwd=dest, capture_output=True,
                                    text=True, timeout=40)
            if result.returncode != 0 or "P10DL_LAUNCHER_SELFTEST_OK" not in result.stdout:
                raise RuntimeError("P10DL isolated launcher selftest: " + result.stdout[-300:] +
                                   result.stderr[-300:])
            preflight = dest / "P10DL_one_click_m1.py"
            import importlib.util
            spec = importlib.util.spec_from_file_location("p10dl", preflight)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            count = module.source_gate()
            if count != len(data) - 1:
                raise RuntimeError("source SHA gate inventory/count mismatch")
            altered = dest / "stage3d10dl_m1_full4d.cpp"
            altered.write_bytes(altered.read_bytes() + b"\n// deliberate damaged source\n")
            try:
                module.source_gate()
            except RuntimeError as error:
                if "published source changed" not in str(error):
                    raise
            else:
                raise RuntimeError("tampered native M1 source was accepted")
    print("P10DL_R1_BOUNDED_ONE_SHOT_ZIP_OK",
          f"files={len(data)}", f"bytes={TARGET.stat().st_size}",
          f"sha256={sha256(TARGET.read_bytes()).hexdigest()}",
          "source_shas=PASS negative_source_tamper=PASS physical_FEM=0 Gmsh=0")


if __name__ == "__main__":
    main()
