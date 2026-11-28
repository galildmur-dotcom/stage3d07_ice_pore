#!/usr/bin/env python3
"""Read-only P10LK audit of M8/M9 ZIP evidence and replay prerequisites."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[2]
INPUTS = {
    'M8': ROOT / 'upload/P10KV_M8_FIRST_FULL4D_EVIDENCE.zip',
    'M9': ROOT / 'upload/P10LC_M9_FIRST_FULL4D_EVIDENCE.zip',
}


def audit_archive(mesh, file):
    with zipfile.ZipFile(file, 'r') as z:
        names = sorted(z.namelist())
        manifest_name = f'P10{"KV" if mesh == "M8" else "LC"}_MANIFEST.json'
        manifest = json.loads(z.read(manifest_name))
        with z.open('P10DD_SIGNED_R_THETA_PHI_T.csv') as raw:
            reader = csv.DictReader(io.TextIOWrapper(raw, encoding='utf-8'))
            fields = reader.fieldnames or []
            rows = 0
            explicit = 0.
            first_shell_explicit = 0.
            for row in reader:
                rows += 1
                if row['region'] == 'VOLUME':
                    val = float(row['mech_explicit_per_m'])
                    explicit += val
                    if row['radial_bin'] == '0':
                        first_shell_explicit += val
        has_qp_arrays = [n for n in names if n.lower().endswith(('.bin','.npy','.npz','.h5','.hdf5','.vtu','.vtk'))]
        return {
            'zip':str(file.relative_to(ROOT)),
            'zip_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
            'mesh_sha256':manifest['mesh_sha256'],
            'status':manifest['status'],
            'steps':manifest['regime']['steps'],
            'dt_s':manifest['regime']['dt_s'],
            'native_exit_code':manifest['native_exit_code'],
            'FEM_attempts_recorded':manifest['FEM_attempts'],
            'archive_members':names,
            'archived_binary_qp_state_candidates':has_qp_arrays,
            'forward_history_sha256_only':manifest.get('history_sha256'),
            'forward_history_bin_archived':'forward_history.bin' in names,
            'reverse_adjoint_qp_arrays_archived':False,
            '4d_csv_rows':rows,
            '4d_csv_columns':fields,
            'explicit_from_4d_csv':explicit,
            'explicit_in_manifest':manifest['independent_4d']['components']['mech_explicit_per_m'],
            'wall_0_20um_explicit_from_4d_csv':first_shell_explicit,
        }


def main():
    found = {mesh:audit_archive(mesh,path) for mesh,path in INPUTS.items()}
    for mesh,d in found.items():
        assert d['status'].endswith('_PASS')
        assert d['4d_csv_rows'] == 43236
        assert abs(d['explicit_from_4d_csv'] - d['explicit_in_manifest']) < 1e-8
        assert not d['archived_binary_qp_state_candidates']
        assert not d['forward_history_bin_archived']
        assert d['native_exit_code'] == 0
    disk_candidates = [str(p.relative_to(ROOT)) for pattern in ('*.bin','*.npz','*.npy','*.h5','*.hdf5')
                       for p in ROOT.rglob(pattern) if p.is_file()]
    # A SHA-256 digest of the forward history proves existence at run time,
    # not retention or availability of adjoints for QP-level postprocessing.
    result={
        'protocol':'P10LK_M8_M9_REPLAY_READONLY_INVENTORY',
        'status':'PASS_INVENTORY_REPLAY_NOT_SUPPORTED_BY_ARCHIVED_EVIDENCE',
        'mesh':found,
        'workspace_saved_state_candidates':disk_candidates,
        'm9_minus_m8_mech_explicit_per_m':found['M9']['explicit_in_manifest']-found['M8']['explicit_in_manifest'],
        'm9_minus_m8_first_0_20um_mech_explicit_per_m':found['M9']['wall_0_20um_explicit_from_4d_csv']-found['M8']['wall_0_20um_explicit_from_4d_csv'],
        'replay_requires':[
            'complete per-step forward displacement and QP EDV history on each exact mesh',
            'per-step discrete adjoint displacement and required future-history adjoints',
            'pinned mesh/temperature/shape velocity/mask and law/control parameters',
            'matching time grid and source hashes',
        ],
        'conclusion':'Neither submitted evidence ZIP contains QP states, forward_history.bin, or adjoint arrays. Existing 4D CSV aggregates are not invertible to per-QP geometry/stress components. A local Windows forward_history.bin might exist but would not alone provide the backward adjoint fields.',
        'FEM_attempts':0,'mesh_generation_attempts':0,
    }
    out=ROOT/'research/P10LK_REPLAY_EVIDENCE_QA.json'
    out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='mesh'},indent=2,ensure_ascii=False))
    for mesh, d in found.items():
        print(mesh,'members',len(d['archive_members']),'csv_rows',d['4d_csv_rows'],
              'explicit',d['explicit_in_manifest'],'wall',d['wall_0_20um_explicit_from_4d_csv'])


if __name__=='__main__':main()
