#!/usr/bin/env python3
"""Read-only P10BF evidence collector for the author's Windows Stage3D07 tree.

Only an explicit allowlist of source files and matching P10BA CSV is archived.
The program never changes the source project, invokes a solver, or reads .bin/.msh.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import zipfile


SOURCE_FILES = (
    "CMakeLists.txt",
    "src/stage3d10ba_polar_export.hpp",
    "src/stage3d10p_partial_audit.cpp",
    "src/stage3d10w_analytic_adjoint.cpp",
    "tests/stage3d10v_analytic_shape.cpp",
)

# Mechanical contribution on the final time step in the two investigated shells;
# see docs/P10BB_W5B2_SPHERICAL_RESEARCH_20261118.md.
EXPECTED_P10BB_STEP6 = {
    "H4W4B2": -0.735338450892,
    "H4W4B20": -0.734183561239,
    "H4W5B2": -0.740080366816,
}

EXE_NAMES = (
    "stage3d10az_targeted_qp_probe.exe",
    "stage3d10ba_polar_radial_audit.exe",
    "stage3d10bd_temporal_polar_audit.exe",
    "stage3d10be_temporal_polar_audit.exe",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_git(project_root: Path, *args: str) -> dict[str, object]:
    try:
        run = subprocess.run(
            ["git", "-C", str(project_root), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=20, check=False,
        )
        return {"exit_code": run.returncode, "stdout": run.stdout.strip(),
                "stderr": run.stderr.strip()[:1000]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"error": str(exc)}


def classify_p10ba(path: Path) -> dict[str, object]:
    result: dict[str, object] = {"path": str(path)}
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"time_step", "total_mechanical_per_m", "shell_lower_mm",
                        "radial_subbin", "polar_band"}
            if not required.issubset(reader.fieldnames or ()):
                result["reason"] = "missing_columns"
                return result
            rows = list(reader)
        result["rows"] = len(rows)
        if len(rows) != 400:
            result["reason"] = "expected_400_rows"
            return result
        keys = {(int(r["time_step"]), round(float(r["shell_lower_mm"]), 6),
                 int(r["radial_subbin"]), int(r["polar_band"])) for r in rows}
        last = [float(r["total_mechanical_per_m"]) for r in rows
                if int(r["time_step"]) == 6]
        if len(keys) != 400 or len(last) != 200:
            result["reason"] = "duplicate_or_missing_cells"
            return result
        total = math.fsum(last)
        result["step6_two_shells_per_m"] = total
        matches = [name for name, expected in EXPECTED_P10BB_STEP6.items()
                   if abs(total - expected) < 5e-7]
        if len(matches) == 1:
            result["classification"] = matches[0]
            result["sha256"] = file_sha256(path)
        else:
            result["reason"] = "not_a_unique_reference_match"
    except (OSError, ValueError, UnicodeError, csv.Error) as exc:
        result["reason"] = "unreadable_or_invalid"
        result["detail"] = str(exc)[:240]
    return result


def discover_csv(project_root: Path) -> tuple[list[dict[str, object]], list[str]]:
    findings: list[dict[str, object]] = []
    warnings: list[str] = []
    scanned = 0
    for folder in (project_root / "LOCAL_RUNS", project_root / "LOCAL_RUNS_OPTIMIZED"):
        if not folder.is_dir():
            warnings.append("Directory not found: " + str(folder))
            continue

        def onerror(exc: OSError) -> None:
            warnings.append("Traversal error: " + str(exc))

        for base, subdirs, filenames in os.walk(folder, onerror=onerror):
            scanned += 1
            if scanned > 30000:
                warnings.append("Directory search stopped at safety limit of 30000")
                return findings, warnings
            subdirs[:] = [x for x in subdirs if x.lower() not in
                          (".git", "build", "checkpoint", "backups")]
            for name in filenames:
                if name.lower().startswith("p10ba_qp_polar_radial") and name.lower().endswith(".csv"):
                    findings.append(classify_p10ba(Path(base) / name))
    return findings, warnings


def select_unique(findings: list[dict[str, object]]) -> tuple[dict[str, Path], list[str]]:
    selected: dict[str, Path] = {}
    warnings: list[str] = []
    for kind in EXPECTED_P10BB_STEP6:
        same = [x for x in findings if x.get("classification") == kind]
        unique_hashes = {str(x["sha256"]) for x in same}
        if len(unique_hashes) == 1:
            selected[kind] = Path(str(same[0]["path"]))
        elif not same:
            warnings.append("Missing original P10BA 400-row CSV for " + kind)
        else:
            warnings.append("Ambiguous CSV versions for " + kind +
                            "; no file was selected automatically")
    return selected, warnings


def build_archive(project_root: Path, destination: Path) -> tuple[Path, dict[str, object]]:
    manifest: dict[str, object] = {
        "protocol": "P10BF_STAGE3D07_SOURCE_AND_P10BB_EVIDENCE_EXPORT_V1",
        "created_local": dt.datetime.now().astimezone().isoformat(),
        "root": str(project_root),
        "read_only_on_project": True,
        "git_head": read_git(project_root, "rev-parse", "HEAD"),
        "git_source_status": read_git(project_root, "status", "--porcelain=v1", "--", *SOURCE_FILES),
        "source_files": {},
        "current_executables": {},
        "csv_candidates": [],
        "selected_csv": {},
        "warnings": [],
    }
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output = destination / ("P10BF_EVIDENCE_EXPORT_" + timestamp + ".zip")
    output.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=6) as zf:
        for relative in SOURCE_FILES:
            path = project_root / relative
            if not path.is_file():
                manifest["warnings"].append("Missing source: " + relative)
                continue
            manifest["source_files"][relative] = {
                "sha256": file_sha256(path), "bytes": path.stat().st_size}
            zf.write(path, "source_snapshot/" + relative)

        build_dir = project_root / "build" / "Desktop_MinGW_Release"
        for name in EXE_NAMES:
            path = build_dir / name
            if path.is_file():
                manifest["current_executables"][name] = {
                    "sha256_now": file_sha256(path), "bytes": path.stat().st_size}
            else:
                manifest["current_executables"][name] = {"status": "not_found"}

        findings, scan_warnings = discover_csv(project_root)
        manifest["csv_candidates"] = findings
        manifest["warnings"].extend(scan_warnings)
        selected, select_warnings = select_unique(findings)
        manifest["warnings"].extend(select_warnings)
        for kind, source in selected.items():
            manifest["selected_csv"][kind] = {
                "source": str(source), "sha256": file_sha256(source),
                "bytes": source.stat().st_size}
            zf.write(source, "P10BB_originals/" + kind + "/P10BA_QP_POLAR_RADIAL.csv")

        zf.writestr("EXPORT_MANIFEST.json", json.dumps(manifest, ensure_ascii=False,
                                                      indent=2) + "\n")
        zf.writestr("README_RU.txt", (
            "Stage3D07 P10BF: архив содержит только выбранные исходники, "
            "манифест и найденные небольшие CSV P10BB.\n"
            "Ни .msh, ни .bin, ни .exe не включены. "
            "Изменения в исходный проект не вносятся.\n"
            "Передайте помощнику этот ZIP целиком. Если в нём недостаёт CSV, "
            "см. warnings и csv_candidates в EXPORT_MANIFEST.json.\n"
            "Git HEAD и текущие SHA .exe не доказывают, что именно эти файлы "
            "использовались при прошлой сборке.\n"
        ))
    return output, manifest


def selftest() -> None:
    from tempfile import TemporaryDirectory

    columns = ("time_step", "shell_lower_mm", "radial_subbin", "polar_band",
               "total_mechanical_per_m")
    with TemporaryDirectory() as temp:
        findings = []
        for kind, total in EXPECTED_P10BB_STEP6.items():
            path = Path(temp) / (kind + "_P10BA_QP_POLAR_RADIAL.csv")
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(columns)
                for step in (5, 6):
                    for shell in (0.02, 0.05):
                        for rb in range(10):
                            for band in range(10):
                                val = total / 200 if step == 6 else 0
                                w.writerow((step, shell, rb, band, val))
            record = classify_p10ba(path)
            assert record.get("classification") == kind, record
            assert record.get("rows") == 400
            findings.append(record)
        found, warnings = select_unique(findings)
        assert not warnings and set(found) == set(EXPECTED_P10BB_STEP6)
    print("P10BF_COLLECTOR_SELFTEST_OK")


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--project-root", type=Path,
                      default=Path(r"G:\ildar\Stage3D07"))
    args.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args.add_argument("--selftest", action="store_true")
    opts = args.parse_args()
    if opts.selftest:
        selftest()
        return 0
    if not opts.project_root.is_dir():
        print("P10BF_STOP: project folder not found:", opts.project_root)
        return 2
    try:
        target, manifest = build_archive(opts.project_root, opts.output_dir)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print("P10BF_STOP:", exc)
        return 3
    print("P10BF_EXPORT_OK", target)
    print("source_count=", len(manifest["source_files"]))
    print("p10bb_csv_count=", len(manifest["selected_csv"]))
    print("warnings=", len(manifest["warnings"]))
    print("Send only this ZIP; do not upload forward_history.bin or meshes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
