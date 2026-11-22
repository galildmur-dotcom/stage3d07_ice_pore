#!/usr/bin/env python3
"""Deterministic standalone publication bundle from P10DL-pinned solver sources.

Bulk archive and SHA-manifest generation, no user project files modified.
"""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "research/packages/P10DL_R1_M1_FRESH_FORWARD_ONE_SHOT_WINDOWS_20261121.zip"
OUTPUT = ROOT / "research/packages/P10FP_FRESH_M0_MN_WINDOWS_20261122.zip"
REV = "P10FP_R2_FRESH_M0_TO_MN_TWO_STAGE_WORKFLOW_NO_INPUT"


def selected_source():
    with zipfile.ZipFile(SOURCE) as source:
        material = {name: source.read(name) for name in source.namelist()
                    if name.startswith("src/") or name.startswith("tests/") or
                       name in ("stage3d10dd_4d_partition.hpp", "stage3d10dk_m1_full4d.cpp")}
    return material


def main():
    contents = selected_source()
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.name == "P10FN_SOURCE_SHA256.json":
            continue
        relative = path.relative_to(HERE).as_posix()
        if (path.name.endswith(".pyc") or "__pycache__" in relative or
                relative == "recipes/ACTIVE.json"):
            continue
        contents[relative] = path.read_bytes()
    assert len(contents) >= 110, len(contents)
    manifest = {"revision": REV, "origin": "P10DL PINNED C++ production source",
                "files": {name: hashlib.sha256(data).hexdigest()
                          for name, data in sorted(contents.items())}}
    raw = (json.dumps(manifest, indent=2, ensure_ascii=False)+"\n").encode("utf-8")
    (HERE/"P10FN_SOURCE_SHA256.json").write_bytes(raw)
    contents["P10FN_SOURCE_SHA256.json"] = raw
    # A future researched step replaces only ACTIVE.json, never the pinned
    # universal engine. It MUST be present in ZIP but intentionally unpinned.
    contents["recipes/ACTIVE.json"] = (HERE/"recipes/ACTIVE.json").read_bytes()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content in sorted(contents.items()):
            info = zipfile.ZipInfo(name, date_time=(2026,11,22,12,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=6)
    print("P10FN_BUNDLE_OK", OUTPUT, "files", len(contents),
          "SHA256", hashlib.sha256(OUTPUT.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
