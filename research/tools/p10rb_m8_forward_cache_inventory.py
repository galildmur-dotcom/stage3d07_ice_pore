#!/usr/bin/env python3
"""P10RB: read-only inventory of already existing Windows M8 forward cache.

Run from Windows Python, for example:
  python research/tools/p10rb_m8_forward_cache_inventory.py \
    --runs-root "G:\\ildar\\Stage3D07\\LOCAL_RUNS" \
    --output "P10RB_M8_CACHE_INVENTORY.json"

Does not create/modify FEM data, re-run EXE, modify one-shot markers or copy
multi-gigabyte histories. Optional --hash may take minutes for large files.
"""

import argparse
import hashlib
import json
from pathlib import Path


EXPECTED_HISTORY_SHA = "91961d2a76ad81edbcc1f2120aecb5b37ac158b53a402fc6d9a888a90c485fde"
EXPECTED_MESH_SHA = "40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"


def file_sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs-root", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--hash", action="store_true", help="Compute complete SHA256 of potentially multi-GiB cache")
    args = p.parse_args()
    root = args.runs_root
    if not root.is_dir():
        raise SystemExit(f"P10RB_INPUT_STOP: LOCAL_RUNS directory not found: {root}")
    matches = sorted(root.glob("P10KV_M8_R_DT25_*/P10FN_M8_DT25_R/forward_history.bin"))
    data = []
    for path in matches:
        folder = path.parent.parent
        manifest_path = folder / "P10KV_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
        item = {
            "run_folder": str(folder),
            "forward_history_path": str(path),
            "history_size_bytes": path.stat().st_size,
            "manifest_found": manifest_path.is_file(),
            "manifest_status": manifest.get("status"),
            "manifest_mesh_sha_matches": manifest.get("mesh_sha256") == EXPECTED_MESH_SHA,
            "manifest_history_sha_matches": manifest.get("history_sha256") == EXPECTED_HISTORY_SHA,
            "hash_computed": args.hash,
        }
        if args.hash:
            actual = file_sha256(path)
            item["actual_history_sha256"] = actual
            item["actual_history_sha_matches"] = actual == EXPECTED_HISTORY_SHA
        data.append(item)
    result = {
        "protocol": "P10RB_M8_EXISTING_HISTORY_INVENTORY_NO_FEM",
        "status": "EXISTING_HISTORY_CANDIDATE_FOUND" if data else "NO_EXISTING_HISTORY_FOUND",
        "run_directories_examined_pattern": "P10KV_M8_R_DT25_*/P10FN_M8_DT25_R/forward_history.bin",
        "history_candidates": data,
        "no_solver_or_adjoint_started": True,
        "note": "Forward cache presence alone does not imply that physical Algoim/EDV/adjoint evaluation can be replayed; adjoint/history state availability must be checked separately.",
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="", flush=True)


if __name__ == "__main__":
    main()
