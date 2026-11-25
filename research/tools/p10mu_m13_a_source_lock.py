#!/usr/bin/env python3
"""P10MU: strict read-only M13 A source and accepted M12 lock; never calls Gmsh/FEM."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELD = ROOT/'p10mt_m13_source_only/P10MT_M13_A_existing_residual_1200_BINS.csv'
QA = ROOT/'p10mt_m13_source_only/P10MT_THREE_FIELDS_SOURCE_ONLY_QA.json'
M12 = ROOT/'p10mn_package/P10ML_M12_R1_CANDIDATE_UNVERIFIED.msh'
M12_QUALITY = ROOT/'upload/P10MN_M12_R1_GMSH_QUALITY_RESULT.json'
EXPECTED_M12_SHA = 'e3c5c5dc9bbcae3d0b2649e7afd4af49b47f6cb6db63329492975fb920abbd13'
EXPECTED_FIELD_SHA = '5c63f14eb16ae9b2e5eb35b9257fcb17e401e82d53e17e29a787fbfd0ac73383'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    assert sha(M12) == EXPECTED_M12_SHA, 'accepted M12 geometry SHA mismatch'
    assert sha(FIELD) == EXPECTED_FIELD_SHA, 'M13 A source SHA mismatch'
    quality = json.loads(M12_QUALITY.read_text(encoding='utf-8-sig'))
    assert quality['quality_gate_pass'] is True
    assert quality['mesh_sha256'] == EXPECTED_M12_SHA
    assert quality['Tet10'] == 16333
    qa = json.loads(QA.read_text())
    assert qa['status'] == 'PASS_SOURCE_ONLY_NO_GMSH_NO_MESH_NO_FEM'
    assert qa['bins'] == 1200
    a = qa['variants']['A_existing_residual']
    assert a['csv_sha256'] == EXPECTED_FIELD_SHA
    assert a['c2_status'].startswith('analytical positive Wendland C2')
    assert a['center_nominal_Veff_ratio_min_max'] == [0.8, 1.0]
    assert a['seam_error'] < 1e-10 and a['pole_error'] < 1e-12
    print(json.dumps({
        'protocol': 'P10MU_M13_A_SOURCE_LOCK',
        'status': 'PASS_READONLY_SOURCE_LOCK_NO_GMSH_NO_FEM_NO_MARKER',
        'parent_mesh_M12_sha256': EXPECTED_M12_SHA,
        'parent_mesh_M12_Tet10': 16333,
        'parent_mesh_M12_D031_quality_pass': True,
        'M13_selected': 'A_existing_residual',
        'M13_field_sha256': EXPECTED_FIELD_SHA,
        'M13_bins': 1200,
        'M13_nominal_incremental_volume_ratio_range': [0.8, 1.0],
        'M13_no_automatic_mesh_or_FEM_authorization': True,
        'new_mesh_attempts': 0, 'FEM_attempts': 0, 'marker_uses': 0,
    }, indent=2))


if __name__ == '__main__':
    main()
