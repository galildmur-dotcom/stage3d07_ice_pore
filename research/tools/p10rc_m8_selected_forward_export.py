#!/usr/bin/env python3
"""P10RC: extract 48 selected real M8 forward histories from frozen P10KV cache.

Read-only to all project inputs. Original 1.22-GB file is SHA256 checked and
never copied/modified. Creates one compact ZIP in the unpacked package folder.
No Gmsh, FEM, adjoint or Algoim call. Not a complete physical A/B test.
"""

import argparse
import hashlib
import json
import math
import struct
import time
import zipfile
from pathlib import Path


MESH_SHA = "40949482ac74d80ae7ac44c88af527a705650d34c1ffcd0de7cd01dc2bd2fa8d"
CACHE_SHA = "91961d2a76ad81edbcc1f2120aecb5b37ac158b53a402fc6d9a888a90c485fde"
MAGIC = 0x314E303133454349
NODES, TETS, QP_PER_TET, STEPS, DT, STATE_BYTES = 18331, 12546, 27, 36, 25, 96
NQ = TETS * QP_PER_TET
HEADER_BYTES = 10 * 8 + 3 * 8
TEMP_BYTES, U_BYTES, PREV_BYTES = NODES * 8, 3 * NODES * 8, NQ * STATE_BYTES
FRAME_BYTES = (8 + TEMP_BYTES) + (8 + U_BYTES) + (8 + PREV_BYTES)
EXPECTED_BYTES = HEADER_BYTES + STEPS * FRAME_BYTES + (8 + U_BYTES) + (8 + PREV_BYTES) + 8


def sha256_with_progress(path):
    h = hashlib.sha256()
    last = time.monotonic()
    processed = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
            processed += len(chunk)
            if time.monotonic() - last >= 15:
                print(f"P10RC_HASH_PROGRESS bytes={processed}", flush=True)
                last = time.monotonic()
    return h.hexdigest()


def load_mesh(mesh_path):
    raw = mesh_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != MESH_SHA:
        raise ValueError("Accepted M8.msh SHA mismatch")
    tags = []
    tet = []
    lines = iter(raw.decode("utf-8").splitlines())
    for line in lines:
        if line == "$Nodes":
            for _ in range(int(next(lines))):
                tags.append(int(next(lines).split()[0]))
        elif line == "$Elements":
            for _ in range(int(next(lines))):
                p = list(map(int, next(lines).split()))
                if p[1] == 11 and p[3] == 1:
                    ids = list(p[3 + p[2]:])
                    if len(ids) != 10:
                        raise ValueError("Malformed M8 Tet10")
                    # C++ tet10_shared.hpp::read_msh swaps Gmsh midside 8/9.
                    ids[8], ids[9] = ids[9], ids[8]
                    tet.append((p[0], ids))
    if len(tags) != NODES or len(tet) != TETS or len(set(tags)) != NODES:
        raise ValueError("M8 node / tet order mismatch")
    id_to_ord = {tag: i for i, tag in enumerate(tags)}
    return tet, id_to_ord


def extract(cache, mesh_path, selection):
    if cache.stat().st_size != EXPECTED_BYTES:
        raise ValueError(f"Cache file size {cache.stat().st_size} != expected {EXPECTED_BYTES}")
    print("P10RC_CACHE_SIZE_PASS", EXPECTED_BYTES, flush=True)
    actual = sha256_with_progress(cache)
    if actual != CACHE_SHA:
        raise ValueError("Original M8 forward cache SHA256 mismatch")
    print("P10RC_CACHE_SHA256_PASS", flush=True)
    tet, node_map = load_mesh(mesh_path)
    chosen = selection["selected_tet10"]
    if (selection.get("mesh_sha256") != MESH_SHA or len(chosen) != 48 or
            len({x["tet10_msh_volume_ordinal_zero_based"] for x in chosen}) != 48):
        raise ValueError("P10RA pilot selection mismatch")
    selected = []
    nodes = set()
    for x in chosen:
        ord0 = x["tet10_msh_volume_ordinal_zero_based"]
        if not (0 <= ord0 < TETS) or tet[ord0][0] != x["tet10_gmsh_element_id"]:
            raise ValueError("Original M8 Tet10 ordinal or Gmsh tag mismatch")
        tag_ids = tet[ord0][1]
        indices = [node_map[t] for t in tag_ids]
        nodes.update(indices)
        selected.append({**x, "node_indices_zero_based_fe_order": indices})
    node_indices = sorted(nodes)
    states = bytearray()
    frames = []
    with cache.open("rb") as f:
        head = struct.unpack("<10Q", f.read(80))
        if not (head[0] == MAGIC and head[1] == 1 and head[2] == STATE_BYTES and
                head[4:9] == (NODES, TETS, NQ, STEPS, DT) and
                struct.unpack("<d",struct.pack("<Q",head[9]))[0] == 5.0):
            raise ValueError("M8 forward cache header/mesh/time/layout mismatch")
        objectives = struct.unpack("<3d", f.read(24))
        for step in range(1, STEPS + 1):
            f.read(8)
            temp_offset = f.tell()
            f.seek(TEMP_BYTES, 1)
            f.read(8)
            u_offset = f.tell()
            f.seek(U_BYTES, 1)
            f.read(8)
            state_offset = f.tell()
            f.seek(PREV_BYTES, 1)
            end = f.tell()
            tvals, uvals = [], []
            for n in node_indices:
                f.seek(temp_offset + n * 8)
                tvals.append(struct.unpack("<d", f.read(8))[0])
                f.seek(u_offset + n * 24)
                uvals.append(struct.unpack("<3d", f.read(24)))
            for x in selected:
                f.seek(state_offset + x["tet10_msh_volume_ordinal_zero_based"] * QP_PER_TET * STATE_BYTES)
                chunk = f.read(QP_PER_TET * STATE_BYTES)
                if len(chunk) != QP_PER_TET * STATE_BYTES:
                    raise ValueError("Truncated selected EDV prior-QP history")
                states.extend(chunk)
            f.seek(end)
            if any(not math.isfinite(v) for v in tvals):
                raise ValueError("Nonfinite temperature trajectory")
            frames.append({"step": step, "time_end_s": step * DT,
                           "temperature_selected_nodes": tvals,
                           "u_xyz_selected_nodes": uvals})
            if step % 6 == 0:
                print(f"P10RC_EXTRACT_PROGRESS step={step}/{STEPS}", flush=True)
        final_u_header = f.read(8)
        f.seek(U_BYTES, 1)
        final_q_header = f.read(8)
        f.seek(PREV_BYTES, 1)
        tail = f.read(8)
        if len(final_u_header) != 8 or len(final_q_header) != 8 or len(tail) != 8:
            raise ValueError("Truncated cache final state")
        if struct.unpack("<d", tail)[0] != 900.0 or f.read(1):
            raise ValueError("Invalid cache final time or trailing data")
    expected = STEPS * len(selected) * QP_PER_TET * STATE_BYTES
    if len(states) != expected:
        raise ValueError("Selected QP history size mismatch")
    metadata = {
        "protocol": "P10RC_M8_REAL_FORWARD_STATES_SELECTED_48_READ_ONLY",
        "status": "PASS_FULL_SOURCE_SHA_AND_SELECTED_REAL_STATE_EXTRACTION",
        "original_cache_sha256": actual, "mesh_sha256": MESH_SHA,
        "cached_mesh_signature_u64": head[3],
        "objective_j6_jpeak_jen": objectives,
        "steps": STEPS, "dt_s": DT,
        "state_layout": "P10N cache original 96-byte C++ State, 12 float64 (EDV e_d[6],e_v[6]); verify struct layout before physical evaluation",
        "state_blob_order": "step=1..36, P10RA selected_tet10 JSON order, q=0..26, 96 raw bytes",
        "selected_tet10": selected,
        "selected_node_indices_zero_based": node_indices,
        "selected_tet_count": len(selected),
        "selected_state_bytes": len(states),
        "limitations": "Original Gauss-QP prior EDV states, not reconstructed at Algoim QPs; no local adjoint futures or physical A/B integrals here.",
    }
    return metadata, frames, bytes(states)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache", required=True, type=Path)
    p.add_argument("--mesh", required=True, type=Path)
    p.add_argument("--selection", required=True, type=Path)
    p.add_argument("--out-dir", required=True, type=Path)
    args = p.parse_args()
    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    bundle = out / "P10RC_M8_SELECTED_FORWARD_EVIDENCE.zip"
    status_path = out / "P10RC_M8_EXPORT_STATUS.json"
    if bundle.exists():
        raise SystemExit("P10RC_STOP: output ZIP exists, refusing overwrite")
    try:
        selection = json.loads(args.selection.read_text(encoding="utf-8"))
        metadata, frames, state_bytes = extract(args.cache, args.mesh, selection)
        with zipfile.ZipFile(bundle, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            z.writestr("P10RC_METADATA.json", json.dumps(metadata, ensure_ascii=False, indent=2))
            z.writestr("P10RC_SELECTED_NODAL_FRAMES.json", json.dumps(frames, ensure_ascii=False))
            z.writestr("P10RC_SELECTED_ORIGINAL_GAUSS_QP_EDV_PREVIOUS.bin", state_bytes)
        with zipfile.ZipFile(bundle) as z:
            if z.testzip() is not None:
                raise ValueError("Output ZIP CRC failure")
        status = {"protocol": "P10RC_M8_SELECTED_CACHE_EXPORT", "status": "PASS",
                  "output_zip": bundle.name, "output_zip_sha256": sha256_with_progress(bundle),
                  "source_cache_unchanged": True, "new_FEM_or_adjoint_started": False}
    except Exception as exc:
        # Never leave an apparently complete evidence ZIP after a failed run.
        if bundle.exists():
            bundle.unlink()
        status = {"protocol": "P10RC_M8_SELECTED_CACHE_EXPORT", "status": "STOP",
                  "error": str(exc), "source_cache_unchanged": True,
                  "new_FEM_or_adjoint_started": False}
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("P10RC_FINAL_STATUS", status["status"], flush=True)
    print("P10RC_SEND", status["output_zip"] if status["status"] == "PASS" else status_path.name, flush=True)
    if status["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
