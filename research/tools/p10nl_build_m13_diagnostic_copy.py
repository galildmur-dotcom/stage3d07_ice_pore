#!/usr/bin/env python3
"""P10NL: construct a non-meshed, non-FEM diagnostic copy of pinned M13 R2."""
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/tools'))
from p10nf_m13_pore_tri6_face_audit_readonly import read
from p10hv_independent_scan import EDGE, rule

SOURCE = ROOT / 'p10na_m13_r2_evidence/P10NA_M13_R2_CANDIDATE_UNVERIFIED.msh'
EXPECTED = '57403ba43fa299417d519046cebdf50fa4968b670c071a8b7882748b50f51e9c'
P10NK = ROOT / 'p10nk_m13_three_nodes/P10NK_M13_R2_THREE_NODE_CONSTRAINED_729QP.json'
DEST = ROOT / 'p10nl_m13_diagnostic_quality'
COPY_NAME = 'P10NL_M13_R2_THREE_NODE_DIAGNOSTIC_NOT_R3.msh'
ZIP_NAME = 'P10NL_M13_R2_THREE_NODE_DIAGNOSTIC_GMSH_QUALITY_WINDOWS_20261126.zip'
NODES = (8680, 8681, 9115)
DISTANCES_MM = (0.010, 0.005, 0.005)
C = np.array([0., 0., .03])


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if DEST.exists():
        raise RuntimeError('P10NL_STOP: package directory already exists; no overwrite')
    if digest(SOURCE) != EXPECTED:
        raise RuntimeError('P10NL_STOP: source mesh SHA256 mismatch')
    qa = json.loads(P10NK.read_text())
    best = qa['best_feasible']
    assert qa['mesh_sha256'] == EXPECTED
    assert [best['node_delta_mm'][str(n)] for n in NODES] == list(DISTANCES_MM)
    nodes, tets, surface = read(SOURCE)
    pore = {n for _, conn in surface.values() for n in conn}
    assert not set(NODES) & pore
    affected = {eid: conn for eid, conn in tets.items() if set(NODES) & set(conn[:4])}
    assert len(affected) == qa['affected_Tet10_count'] == 67
    dirs = {n: (nodes[n]-C)/np.linalg.norm(nodes[n]-C) for n in NODES}
    pivot_face = np.mean([nodes[n] for n in tets[9478][:4] if n in pore], axis=0)
    dirs[8680] = (pivot_face-C)/np.linalg.norm(pivot_face-C)
    move = {n: dirs[n] * (mm * .001) for n, mm in zip(NODES, DISTANCES_MM)}
    for conn in affected.values():
        for j, (a, b) in enumerate(EDGE):
            mid = conn[4+j]
            vector = (move.get(conn[a], np.zeros(3)) + move.get(conn[b], np.zeros(3))) / 2
            if np.any(vector):
                if mid in move and not np.allclose(move[mid], vector, atol=1e-18, rtol=0):
                    raise RuntimeError('P10NL_STOP: inconsistent midside edge displacement')
                move[mid] = vector
    assert len(move) == qa['changed_node_count'] == 47
    assert not move.keys() & pore
    assert not [eid for eid, conn in tets.items() if eid not in affected and move.keys() & set(conn)]
    newnodes = dict(nodes)
    for n, vector in move.items():
        newnodes[n] = nodes[n] + vector
    taglist = sorted(affected)
    p0 = np.asarray([[nodes[n] for n in affected[tag]] for tag in taglist])
    p1 = np.asarray([[newnodes[n] for n in affected[tag]] for tag in taglist])
    _, D, W = rule(9)

    def metrics(p):
        J = np.einsum('nic,qij->nqcj', p, D, optimize=True)
        singular = np.linalg.svd(J, compute_uv=False)
        det = np.linalg.det(J)
        return singular[:, :, -1].min(axis=1) / singular[:, :, 0].max(axis=1), det.min(axis=1), (det * W[None, :]).sum(axis=1)

    # Match P10NK's per-quadrature-point minimum of the singular-value ratio.
    def sigma(p):
        s = np.linalg.svd(np.einsum('nic,qij->nqcj', p, D, optimize=True), compute_uv=False)
        return np.min(s[:, :, -1] / s[:, :, 0], axis=1)

    _, det0, vol0 = metrics(p0)
    _, det1, vol1 = metrics(p1)
    s0, s1 = sigma(p0), sigma(p1)
    if not np.all(det0 > 0) or not np.all(det1 > 0):
        raise RuntimeError('P10NL_STOP: nonpositive sampled detJ')
    assert np.isclose(s0.min(), qa['baseline_worst_sigma_ratio'], atol=1e-12)
    assert np.isclose(s1.min(), best['min_sigma_ratio_all'], atol=1e-12)
    assert np.allclose([np.min(vol1/vol0), np.max(vol1/vol0)], best['volume_ratio_min_max'], atol=1e-11)
    assert np.isclose(vol1.sum()/vol0.sum(), best['star_total_curved_volume_ratio'], atol=1e-11)

    DEST.mkdir()
    shutil.copy2(SOURCE, DEST / SOURCE.name)
    data = SOURCE.read_text(encoding='ascii').splitlines(keepends=True)
    start = next(i for i, line in enumerate(data) if line.strip() == '$Nodes')
    count = int(data[start+1].strip())
    modified = set()
    for index in range(start+2, start+2+count):
        fields = data[index].split()
        tag = int(fields[0])
        if tag in move:
            xyz = newnodes[tag]
            ending = '\r\n' if data[index].endswith('\r\n') else '\n'
            data[index] = f'{tag} {xyz[0]:.17g} {xyz[1]:.17g} {xyz[2]:.17g}{ending}'
            modified.add(tag)
    assert modified == move.keys()
    copy_path = DEST / COPY_NAME
    copy_path.write_text(''.join(data), encoding='ascii', newline='')
    revised, tets_new, surface_new = read(copy_path)
    assert tets == tets_new and surface == surface_new
    assert nodes.keys() == revised.keys()
    assert all(np.array_equal(nodes[n], revised[n]) for n in nodes.keys()-move.keys())
    assert all(np.array_equal(nodes[n], revised[n]) for n in pore)
    assert all(np.linalg.norm(revised[n]-nodes[n]) > 0 for n in move)
    manifest = {
        'protocol': 'P10NL_M13_R2_THREE_NODE_DIAGNOSTIC_COPY_NO_GMSH_GENERATION',
        'status': 'SOURCE_ONLY_PREPARED_NOT_GMSH_VALIDATED_NOT_M13_R3',
        'original_file': SOURCE.name, 'original_sha256': EXPECTED,
        'diagnostic_file': COPY_NAME, 'diagnostic_sha256': digest(copy_path),
        'Tet10': len(tets), 'nodes': len(nodes), 'pore_Tri6': len(surface),
        'changed_node_tags': sorted(move), 'changed_node_count': len(move),
        'affected_tet_count': len(affected), 'affected_tet_tags': taglist,
        'pivot_displacements_mm': dict(zip(map(str, NODES), DISTANCES_MM)),
        'pore_nodes_unchanged': True, 'connectivity_unchanged': True,
        'sampled_729qp_min_sigma_ratio_before': float(s0.min()),
        'sampled_729qp_min_sigma_ratio_after': float(s1.min()),
        'sampled_729qp_all_detJ_positive': True,
        'sampled_curved_volume_ratio_min_max': [float((vol1/vol0).min()), float((vol1/vol0).max())],
        'sampled_total_star_volume_ratio': float(vol1.sum()/vol0.sum()),
        'native_Gmsh_qualities_not_yet_measured': True,
        'gmsh_generation_attempts': 0, 'FEM_attempts': 0, 'marker_uses': 0,
    }
    (DEST/'P10NL_MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    shutil.copy2(ROOT/'research/tools/p10nl_native_gmsh_quality_windows.py', DEST/'P10NL_NATIVE_GMSH_QUALITY.py')
    shutil.copy2(ROOT/'research/tools/P10NL_RUN_NATIVE_GMSH_QUALITY.cmd', DEST/'P10NL_RUN_NATIVE_GMSH_QUALITY.cmd')
    shutil.copy2(ROOT/'research/P10NL_M13_THREE_NODE_DIAGNOSTIC_PROTOCOL_20261126.md', DEST/'README_RU.md')
    zip_path = ROOT/ZIP_NAME
    if zip_path.exists():
        raise RuntimeError('P10NL_STOP: ZIP already exists; no overwrite')
    with zipfile.ZipFile(zip_path, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for item in sorted(DEST.iterdir()):
            z.write(item, arcname=item.name)
    print(json.dumps({'zip': str(zip_path), 'manifest': manifest}, indent=2))


if __name__ == '__main__':
    main()
