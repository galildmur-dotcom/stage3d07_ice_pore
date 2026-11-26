#!/usr/bin/env python3
"""Windows native Gmsh 4.15.2 quality comparison; read-only and no FEM."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE/'P10NL_MANIFEST.json'
OUTPUT = HERE/'P10NL_M13_THREE_NODE_DIAGNOSTIC_GMSH_QUALITY_RESULT.json'
THRESHOLD = {'minSICN': .20, 'minSJ': .40, 'gamma': .15, 'minDetJac': 0.}


def main():
    import gmsh
    import numpy as np
    if OUTPUT.exists():
        raise RuntimeError('P10NL_STOP: result already exists; no overwrite')
    if gmsh.__version__ != '4.15.2':
        raise RuntimeError('P10NL_STOP: exact Gmsh Python 4.15.2 required')
    m = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for prefix in ('original', 'diagnostic'):
        path = HERE/m[f'{prefix}_file']
        if hashlib.sha256(path.read_bytes()).hexdigest() != m[f'{prefix}_sha256']:
            raise RuntimeError('P10NL_STOP: SHA mismatch for '+prefix)
    results = {}
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        for label in ('original', 'diagnostic'):
            gmsh.clear()
            gmsh.open(str(HERE/m[f'{label}_file']))
            tags, _ = gmsh.model.mesh.getElementsByType(11)
            tags = np.asarray(tags, dtype=np.int64)
            if len(tags) != 18004 or len(set(tags.tolist())) != len(tags):
                raise RuntimeError('P10NL_STOP: invalid Tet10 population for '+label)
            groups = sorted(int(t) for dim, t in gmsh.model.getPhysicalGroups(2))
            qualities = {}
            for name, limit in THRESHOLD.items():
                values = np.asarray(gmsh.model.mesh.getElementQualities(tags.tolist(), qualityName=name), dtype=float)
                if values.shape != tags.shape or not np.all(np.isfinite(values)):
                    raise RuntimeError('P10NL_STOP: invalid '+name+' array for '+label)
                order = np.argsort(values)
                failures = values < limit if name != 'minDetJac' else values <= limit
                qualities[name] = {
                    'min': float(values[order[0]]), 'worst_tet_tag': int(tags[order[0]]),
                    'worst_five': [{'tet_tag': int(tags[i]), 'quality': float(values[i])} for i in order[:5]],
                    'p01': float(np.percentile(values, 1)), 'median': float(np.median(values)),
                    'nonpositive_count': int(np.count_nonzero(values <= 0)),
                    'threshold': limit, 'below_threshold_count': int(np.count_nonzero(failures)),
                    'below_threshold_tet_tags': [int(n) for n in tags[failures]],
                }
            passed = groups == list(range(2, 10)) and all(
                q['below_threshold_count'] == 0 for q in qualities.values())
            results[label] = {'file': m[f'{label}_file'], 'sha256': m[f'{label}_sha256'],
                              'Tet10': len(tags), 'physical_surface_tags': groups,
                              'qualities': qualities, 'D031_quality_gate_pass': passed}
    finally:
        gmsh.finalize()
    delta = {key: {
        'min_before': results['original']['qualities'][key]['min'],
        'min_after': results['diagnostic']['qualities'][key]['min'],
        'minimum_difference': results['diagnostic']['qualities'][key]['min'] - results['original']['qualities'][key]['min'],
        'violating_tets_before': results['original']['qualities'][key]['below_threshold_count'],
        'violating_tets_after': results['diagnostic']['qualities'][key]['below_threshold_count'],
    } for key in THRESHOLD}
    result = {
        'protocol': 'P10NL_NATIVE_GMSH_4_15_2_DIAGNOSTIC_COMPARISON_READONLY',
        'status': 'DIAGNOSTIC_EVALUATED_NOT_M13_R3_NOT_FEM_AUTHORIZED',
        'gmsh_version': '4.15.2', 'thresholds': THRESHOLD, 'meshes': results, 'changes': delta,
        'diagnostic_gate_pass': results['diagnostic']['D031_quality_gate_pass'],
        'gmsh_generation_attempts': 0, 'FEM_attempts': 0, 'marker_uses': 0,
    }
    with OUTPUT.open('x', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(json.dumps({'status': result['status'], 'diagnostic_gate_pass': result['diagnostic_gate_pass'],
                      'changes': delta, 'result_file': str(OUTPUT)}, indent=2), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as err:
        print('P10NL_READONLY_STOP '+repr(err), flush=True)
        sys.exit(2)
