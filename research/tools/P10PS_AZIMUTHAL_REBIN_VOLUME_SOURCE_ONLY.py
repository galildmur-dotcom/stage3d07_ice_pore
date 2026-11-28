#!/usr/bin/env python3
"""P10PS: read-only real M19-M21 azimuthal grouping and volume sensitivity.

NO CAD / GMSH / MESH GENERATION / FEM; uses pinned signed4D CSVs through
the independent P10PR SHA/CRC/physical-closure reader. Outputs JSON only.
The test does NOT certify pointwise convergence or corrected cut-cell integration.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np

import P10PR_M17_M21_CONVERGENCE_AUDIT as p10pr

SOURCE = p10pr.OUTPUT_DIR
GROUP_SIZES = (1, 2, 3, 4, 6, 12)


def check(ok, reason):
    if not ok:
        raise RuntimeError('P10PS_STOP ' + reason)


def grouping(x, width, offset=0):
    check(x.shape[-1] == 12 and width in GROUP_SIZES, 'shape/group width')
    return np.roll(x, -offset, axis=-1).reshape(*x.shape[:-1], 12//width, width).sum(axis=-1)


def discrepancy(a, b):
    den = float(np.sum(np.abs(b)))
    check(den > 0 and np.isfinite(den), 'zero denominator')
    return float(np.sum(np.abs(b-a))/den)


def group_sweep(a, b):
    out = {}
    for w in GROUP_SIZES:
        metrics = [discrepancy(grouping(a,w,j),grouping(b,w,j)) for j in range(w)]
        out[str(12//w)+'_phi_sectors'] = {
            'group_width_original_phi_bins':w,
            'offset_relative_L1':metrics,
            'min_relative_L1':min(metrics),
            'max_relative_L1':max(metrics),
            'mean_relative_L1':sum(metrics)/w,
        }
    return out


def negative_qa():
    x=np.ones((2,3,12),dtype=float)
    for w in GROUP_SIZES:
        for j in range(w):
            y=grouping(x,w,j)
            check(y.shape==(2,3,12//w), 'shape conservation')
            check(np.all(y==w), 'constant density conservation')
            check(abs(float(np.sum(y))-72.)<1e-12, 'global conservation')
    bad=False
    try:
        grouping(x,5,0)
    except RuntimeError:
        bad=True
    check(bad, 'invalid-group rejection')
    # Alternating perturbations must cancel when pairs of azimuthal bins merge.
    a=np.ones((1,1,12))
    b=a+np.array([1,-1]*6).reshape(1,1,12)*0.1
    check(discrepancy(a,b)>0.09, 'positive fine perturbation')
    check(discrepancy(grouping(a,2),grouping(b,2))<1e-14,
          'paired oscillation cancellation')
    return 'PASS_CONSERVATION_INVALID_GROUP_AND_ALTERNATING_SIGN'


def main():
    negative=negative_qa()
    inputs={}
    for mesh in ('M19','M20','M21'):
        manifest, fields, bounds=p10pr.get(mesh)
        inputs[mesh]={'source_sha256':p10pr.SOURCES[mesh][2],
                      'data':fields,
                      'num_tet10':manifest['mesh_qa']['tet10']}
        check(all(np.all(fields[f][0]==fields[f][t])
                  for f in ('mechanical_volume_m3','thermal_volume_m3')
                  for t in range(1,36)), 'volume time-invariance '+mesh)
        print('P10PS_SOURCE_PASS',mesh,'tet10',inputs[mesh]['num_tet10'])
    pairs={}
    for old,new in (('M19','M20'),('M20','M21')):
        prev=inputs[old]['data']
        nxt=inputs[new]['data']
        a=prev['total_per_m']
        b=nxt['total_per_m']
        row={'physical_signed4d':group_sweep(a,b),
             'mechanical_volume_m3':group_sweep(
                prev['mechanical_volume_m3'][0],nxt['mechanical_volume_m3'][0]),
             'thermal_volume_m3':group_sweep(
                prev['thermal_volume_m3'][0],nxt['thermal_volume_m3'][0]),
             'global_derivative_change_m_inv':float(np.sum(b-a))}
        check(abs(row['global_derivative_change_m_inv']-(
                np.sum(b)-np.sum(a)))<1e-10,'signed closure')
        pairs[old+'_'+new]=row
        print('P10PS_PAIR_PASS',old,new)
    report={'protocol':'P10PS_AZIMUTHAL_REBIN_AND_VOLUME_SOURCE_ONLY',
            'status':'PASS_PINNED_REAL_M19_M20_M21_READ_ONLY',
            'negative_qa':negative,
            'source_sha256':{tag:inputs[tag]['source_sha256'] for tag in inputs},
            'physical_scoped_meshes':{tag:inputs[tag]['num_tet10'] for tag in inputs},
            'pairs':pairs,
            'interpretation_limit':
             'Azimuthal grouping is a diagnostic, not a physical correction; '
             'a fixed spatial angular partition needs a conservative cut-cell '
             'or boundary-aware integration scheme before local error certification.'}
    (SOURCE/'P10PS_AZIMUTHAL_REBIN_VOLUME_QA.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('P10PS_FINAL_PASS',flush=True)


if __name__=='__main__':
    main()
