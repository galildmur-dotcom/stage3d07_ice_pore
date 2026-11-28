#!/usr/bin/env python3
"""Audit *actual* selected M8 EDV prior states; no synthetic quadrature A/B.

Inputs are the P10RC compact evidence. The check makes no global FEM claims.
"""
import argparse
import hashlib
import json
import math
import struct
import zipfile
from collections import defaultdict
from pathlib import Path


def audit(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        m = json.loads(z.read("P10RC_METADATA.json"))
        frames = json.loads(z.read("P10RC_SELECTED_NODAL_FRAMES.json"))
        raw = z.read("P10RC_SELECTED_ORIGINAL_GAUSS_QP_EDV_PREVIOUS.bin")
    tets = m["selected_tet10"]
    n_tet, n_frame, n_q, n_d = len(tets), len(frames), 27, 12
    assert (n_tet, n_frame, len(raw)) == (48, 36, 48*36*27*12*8)
    assert m["status"] == "PASS_FULL_SOURCE_SHA_AND_SELECTED_REAL_STATE_EXTRACTION"
    assert [x["step"] for x in frames] == list(range(1, 37))
    assert [x["time_end_s"] for x in frames] == [25*i for i in range(1, 37)]
    n_nodes = len(m["selected_node_indices_zero_based"])
    assert n_nodes == 242
    assert all(len(f["temperature_selected_nodes"]) == n_nodes and
               len(f["u_xyz_selected_nodes"]) == n_nodes for f in frames)
    n_nonzero, n_nonfinite, max_trace, max_abs = 0, 0, 0.0, 0.0
    # State at each frame is the *previous* EDV state (beginning of that step).
    stats = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0, 0]))
    for it, vals in enumerate(struct.iter_unpack("<12d", raw)):
        frame_index = it // (n_tet * n_q)
        tet_index = (it // n_q) % n_tet
        ed, ev = vals[:6], vals[6:]
        if not all(math.isfinite(x) for x in vals):
            n_nonfinite += 1
            continue
        if any(x != 0.0 for x in vals):
            n_nonzero += 1
        max_abs = max(max_abs, *(abs(x) for x in vals))
        max_trace = max(max_trace, abs(sum(ed[:3])), abs(sum(ev[:3])))
        pole_zone = tets[tet_index]["pole"] + "/" + tets[tet_index]["zone"]
        a = stats[pole_zone][frame_index + 1]
        a[0] += sum(x*x for x in ed)
        a[1] += sum(x*x for x in ev)
        a[2] += 1
    assert n_nonfinite == 0
    by_group = {}
    for group, series in sorted(stats.items()):
        by_group[group] = [{"step": step, "previous_time_s": 25*(step-1),
                            "ed_rms": math.sqrt(a[0] / a[2]),
                            "ev_rms": math.sqrt(a[1] / a[2]),
                            "qp_count": a[2]}
                           for step, a in sorted(series.items())]
    assert sum(x["qp_count"] for k in by_group for x in by_group[k]) == 36*48*27
    assert all(x["ed_rms"] == x["ev_rms"] == 0 for k in by_group for x in by_group[k][:1])
    output = {
        "protocol": "P10RD_M8_REAL_EDV_HISTORY_PHYSICAL_GATE",
        "status": "PASS_ORIGINAL_FORWARD_STATE_CONSISTENCY_NOT_AB",
        "evidence_zip_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "forward_cache_sha256": m["original_cache_sha256"],
        "mesh_sha256": m["mesh_sha256"],
        "selected_elements": n_tet, "selected_nodes": n_nodes, "frames": n_frame,
        "original_gauss_qp_per_element": n_q,
        "edv_state_records": n_tet*n_frame*n_q,
        "nonzero_state_records": n_nonzero, "nonfinite_records": n_nonfinite,
        "max_deviatoric_trace_absolute": max_trace,
        "max_state_component_absolute": max_abs,
        "by_pole_zone_time": by_group,
        "interpretation": "EDV histories are physical original Gauss prior states. New Algoim QPs still require constitutive replay from original nodal trajectories; adjoint fields and shape-gradient integrands are not in P10RC.",
        "no_quadrature_AB_claimed": True,
    }
    return output


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence_zip", type=Path)
    ap.add_argument("output_json", type=Path)
    args = ap.parse_args()
    result = audit(args.evidence_zip)
    args.output_json.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(result["status"])
    for key, series in result["by_pole_zone_time"].items():
        print(key, "ed_RMS(step36)=", series[-1]["ed_rms"], "ev_RMS(step36)=", series[-1]["ev_rms"])
