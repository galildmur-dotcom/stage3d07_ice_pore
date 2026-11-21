"""Process-local MinGW PATH gate for the existing P10DD R2 one-shot."""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

R2_NAME = "P10DD_R2_M0_H0_FULL4D_WINDOWS_20261121"
APP_NAME = "stage3d10dd_m0_h0_full4d.exe"
BUILD_NAME = "Desktop_MinGW_Release"
REQUIRED_SOURCE_HASHES = {
    "P10DD_one_click_h0.py": "b59003b149e48133b99294a396318837722d6a2d081fb1f913758b687c89a684",
    "P10DD_audit_evidence.py": "fd7f4ff21ebb918ffae6ad5f7f7d2a1bd03649f956b4695edf3ba2459090dc70",
    "01_PREPARE_OR_RUN_P10DD_M0.cmd": "4b2ca50e4169e47665c3be9ba68c254728ad2f626a6537df3da4821c9b24be74",
}


def require(test: bool, message: str) -> None:
    if not test:
        raise RuntimeError("P10DD_RUNTIME_STOP: " + message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def cache_value(contents: str, name: str) -> str:
    matches = []
    for line in contents.splitlines():
        if line.startswith(("//", "#")) or "=" not in line:
            continue
        label, value = line.split("=", 1)
        if label.split(":", 1)[0] == name:
            matches.append(value.strip().strip('"'))
    require(len(matches) == 1 and bool(matches[0]),
            "CMakeCache.txt: expected exactly one " + name)
    return matches[0]


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(str(right.resolve()))


def inspect_build(source: Path) -> tuple[Path, Path]:
    build = source / "build" / BUILD_NAME
    cache = build / "CMakeCache.txt"
    require(cache.is_file(), "CMakeCache.txt not found: " + str(cache))
    values = cache.read_text(encoding="utf-8", errors="replace")
    home = Path(cache_value(values, "CMAKE_HOME_DIRECTORY"))
    require(same_path(home, source),
            "CMake build does not belong to this exact isolated R2 source")
    compiler = Path(cache_value(values, "CMAKE_CXX_COMPILER"))
    require(compiler.is_file(), "Qt Creator C++ compiler not found: " + str(compiler))
    require(compiler.name.lower().endswith("g++.exe"),
            "not a MinGW g++ compiler: " + compiler.name)
    mingw_bin = compiler.parent
    require((mingw_bin / "libgcc_s_seh-1.dll").is_file(),
            "libgcc_s_seh-1.dll not found beside the exact Qt Creator g++.exe: "
            + str(mingw_bin))
    require((mingw_bin / "libstdc++-6.dll").is_file(),
            "libstdc++-6.dll not found beside the exact Qt Creator g++.exe")
    executable = build / APP_NAME
    require(executable.is_file(), "P10DD R2 MinGW EXE not found: " + str(executable))
    return executable, mingw_bin


def verify_original_r2(source: Path) -> None:
    require(source.is_dir(), "R2 source directory missing: " + str(source))
    original_worktree = Path("G:/ildar/Stage3D07")
    normalized = os.path.normcase(str(source.resolve()))
    prohibited = os.path.normcase(str(original_worktree.resolve()))
    require(normalized != prohibited and not normalized.startswith(prohibited + os.sep),
            "do not run from the original Stage3D07 source tree")
    for name, expected in REQUIRED_SOURCE_HASHES.items():
        target = source / name
        require(target.is_file() and digest(target) == expected,
                "R2 source launcher mismatch: " + name)
    marker = source / "P10DD_OUTPUT" / "P10DD_ONE_SHOT_CONSUMED.json"
    require(not marker.exists(),
            "one-shot marker already exists; do NOT repeat a previous physical attempt")


def choose_source() -> Path:
    sibling = Path(__file__).resolve().parent.parent / R2_NAME
    if (sibling / "P10DD_one_click_h0.py").is_file():
        print("Found existing P10DD R2 folder:", sibling)
        return sibling.resolve()
    entered = input("Full path to the ALREADY EXTRACTED P10DD R2 source folder: ")
    require(bool(entered.strip()), "R2 source folder is required")
    return Path(entered.strip().strip('"').strip("'")).resolve()


def selftest() -> int:
    source_text = (
        "// generated\n"
        "CMAKE_CXX_COMPILER:FILEPATH=C:/Program Files/Qt/Tools/mingw/bin/g++.exe\n"
        "CMAKE_HOME_DIRECTORY:INTERNAL=G:/Downloads/P10DD_R2\n")
    require(cache_value(source_text, "CMAKE_CXX_COMPILER")
            == "C:/Program Files/Qt/Tools/mingw/bin/g++.exe",
            "CMakeCache parser failed")
    with tempfile.TemporaryDirectory(prefix="p10dd_runtime_unit_") as folder:
        root = Path(folder)
        source = root / "R2"
        build = source / "build" / BUILD_NAME
        mingw_bin = root / "MinGW" / "bin"
        build.mkdir(parents=True)
        mingw_bin.mkdir(parents=True)
        compiler = mingw_bin / "g++.exe"
        compiler.touch()
        (build / APP_NAME).touch()
        (mingw_bin / "libgcc_s_seh-1.dll").touch()
        (mingw_bin / "libstdc++-6.dll").touch()
        (build / "CMakeCache.txt").write_text(
            "CMAKE_CXX_COMPILER:FILEPATH=" + str(compiler) + "\n"
            "CMAKE_HOME_DIRECTORY:INTERNAL=" + str(source) + "\n",
            encoding="utf-8")
        found_exe, found_bin = inspect_build(source)
        require(found_exe == build / APP_NAME and found_bin == mingw_bin,
                "build/MinGW bin resolution failed")
        (mingw_bin / "libgcc_s_seh-1.dll").unlink()
        rejected = False
        try:
            inspect_build(source)
        except RuntimeError as exc:
            rejected = "libgcc_s_seh-1.dll" in str(exc)
        require(rejected, "missing runtime DLL was not rejected")
    print("P10DD_RUNTIME_GATE_SELFTEST_OK cmake_parser=PASS exact_bin=PASS "
          "missing_dll=REJECTED physical_FEM=0")
    return 0


def main(argv: list[str]) -> int:
    if argv == ["--selftest"]:
        return selftest()
    require(not argv, "unknown options; only --selftest is accepted")
    require(sys.platform == "win32", "this runtime launcher is for Windows 11")
    source = choose_source()
    verify_original_r2(source)
    exe, mingw_bin = inspect_build(source)
    env = os.environ.copy()
    env["PATH"] = str(mingw_bin) + os.pathsep + env.get("PATH", "")
    print("P10DD_MINGW_RUNTIME_PATH_OK", mingw_bin, flush=True)
    print("P10DD R2 EXE:", exe, flush=True)
    print("The MinGW DLL path applies ONLY to this process tree.", flush=True)
    print("Checking --help before the one-shot physical launcher...", flush=True)
    result = subprocess.run([str(exe), "--help"], capture_output=True, text=True,
                            errors="replace", timeout=45, env=env)
    require(result.returncode == 0 and "P10DD_FULL4D" in result.stdout,
            "--help returned exit " + str(result.returncode) +
            "; details: " + (result.stdout + result.stderr)[-600:])
    print("P10DD_RUNTIME_PREFLIGHT_OK physical_FEM=0", flush=True)
    print("The original R2 launcher will now request EXE, H0 cache and the "
          "one-shot manual phrase.", flush=True)
    return subprocess.call([sys.executable, str(source / "P10DD_one_click_h0.py")],
                           cwd=source, env=env)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print("STOP:", error)
        raise SystemExit(2)
