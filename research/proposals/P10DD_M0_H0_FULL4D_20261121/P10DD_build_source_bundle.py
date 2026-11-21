"""Build a reproducible, self-contained Windows source bundle (no mesh/FEM)."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TARGET = ROOT / "research/packages/P10DD_R1_M0_H0_FULL4D_WINDOWS_20261121.zip"
SUFFIXES = {".cpp", ".hpp", ".inc"}
EXTRA = (
    "CMakeLists.txt", "stage3d10dd_m0_full4d.cpp",
    "stage3d10dd_4d_partition.hpp", "p10dd_4d_synthetic_unit.cpp",
    "P10DD_one_click_h0.py", "P10DD_audit_evidence.py",
    "01_PREPARE_OR_RUN_P10DD_M0.cmd", "README_RU.md",
)


def main() -> None:
    files: list[tuple[str, Path]] = []
    for dirname in ("src", "tests"):
        for path in sorted((ROOT / dirname).iterdir()):
            if path.is_file() and path.suffix in SUFFIXES:
                files.append((f"{dirname}/{path.name}", path))
    files.extend((name, HERE / name) for name in EXTRA)
    assert len(files) > 70, "incomplete source tree"
    for name, file in files:
        assert file.is_file(), f"missing {name}"
    hashes = []
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    # Package content includes the old source too, but no Git history, archives,
    # checkpoint, .msh, .bin, results, executables or personal Windows files.
    with zipfile.ZipFile(TARGET, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8) as out:
        for name, file in files:
            data = file.read_bytes()
            hashes.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
            info = zipfile.ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(info, data)
        info = zipfile.ZipInfo("P10DD_SOURCE_SHA256SUMS.txt", (2026, 11, 21, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        out.writestr(info, "".join(hashes).encode("utf-8"))
    with zipfile.ZipFile(TARGET) as check:
        assert check.testzip() is None
        assert len(check.namelist()) == len(files) + 1
    print("P10DD_SOURCE_BUNDLE_OK")
    print("archive:", TARGET)
    print("files:", len(files) + 1)
    print("bytes:", TARGET.stat().st_size)
    print("sha256:", hashlib.sha256(TARGET.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
