#!/usr/bin/env python3
"""Verify four P10QA depth-16 physical cut-volume pilots against all48 depth12."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import P10PX_M8_CONSERVATIVE_TET10_TRIAGE as m8


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh', type=Path, required=True)
    p.add_argument('--full', type=Path, required=True)
    p.add_argument('--pilot', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path('P10QA_M8_DEPTH16_PILOT_SUMMARY_QA.json'))
    p.add_argument('--csv', type=Path, default=Path('P10QA_M8_DEPTH16_PILOT_CONVERGENCE.csv'))
    a=p.parse_args()
    pinned=hashlib.sha256(a.mesh.read_bytes()).hexdigest()
    full=json.loads(a.full.read_text(encoding='utf-8'))
    pilot=json.loads(a.pilot.read_text(encoding='utf-8'))
    if pinned!=m8.PINNED_M8_SHA256 or full['mesh_sha256']!=pinned or pilot['mesh_sha256']!=pinned:
        raise ValueError('M8 identity mismatch')
    if full['max_depth']!=12 or full['bin_count']!=48 or pilot['max_depth']!=16 or pilot['bin_count']!=4:
        raise ValueError('incomplete primary or pilot coverage')
    if pilot['status']!='PASS_PILOT_CURVED_M8_PHYSICAL_CUT_VOLUME_BRACKETS':
        raise ValueError('pilot did not complete')
    lookup={(b['radial_bin'],b['mu_bin'],b['phi_bin']):b for b in full['bins']}
    expected={(0,0,0),(0,9,6),(4,0,0),(4,9,6)}
    lines=['radial_bin,mu_bin,phi_bin,depth,lower_m3,upper_m3,interval_width_m3,relative_width_to_ideal,relative_width_to_midpoint']
    groups=[]
    for b in pilot['bins']:
        key=(b['radial_bin'],b['mu_bin'],b['phi_bin'])
        if key not in expected:
            raise ValueError('unexpected bin in pilot')
        expected.remove(key)
        old=lookup[key]
        if b['candidate_count']!=old['candidate_count']:
            raise ValueError('candidate identity changed')
        ref_tol=1e-12*b['candidate_total_physical_m3']
        for i in range(13):
            for name in ('lower_cut_volume_m3','upper_cut_volume_m3','unresolved_leaves'):
                if abs(b['depth_records'][i][name]-old['depth_records'][i][name])>ref_tol:
                    raise ValueError(f'pilot prefixes changed: {key} {i} {name}')
        r0=m8.PORE_R+m8.RADIAL_LOWER_MM[key[0]]/1000.
        r1=m8.PORE_R+m8.RADIAL_LOWER_MM[key[0]+1]/1000.
        ideal=(r1**3-r0**3)/3.*.2*(math.pi/6.)
        prior_lower=-1e-30
        prior_upper=b['candidate_total_physical_m3']+1e-30
        for d in b['depth_records']:
            lo=d['lower_cut_volume_m3'];hi=d['upper_cut_volume_m3']
            if lo<prior_lower-ref_tol or hi>prior_upper+ref_tol or hi<lo-ref_tol:
                raise ValueError('nonmonotone physical bracket')
            midpoint=(lo+hi)/2.
            width=hi-lo
            lines.append(','.join(str(x) for x in (key[0],key[1],key[2],d['depth'],
                         f'{lo:.17g}',f'{hi:.17g}',f'{width:.17g}',
                         f'{width/ideal:.17g}',f'{width/midpoint:.17g}')))
            prior_lower,prior_upper=lo,hi
        record={"radial_bin":key[0],"mu_bin":key[1],"phi_bin":key[2],
                "ideal_spherical_sector_m3":ideal,
                "depths":{}}
        for level in [8,10,12,14,16]:
            d=b['depth_records'][level]
            width=d['upper_cut_volume_m3']-d['lower_cut_volume_m3']
            mid=.5*(d['upper_cut_volume_m3']+d['lower_cut_volume_m3'])
            record['depths'][str(level)]={"lower_m3":d['lower_cut_volume_m3'],
                "upper_m3":d['upper_cut_volume_m3'],
                "width_over_ideal":width/ideal,
                "width_over_cut_midpoint":width/max(mid,1e-30),
                "ideal_inside_bracket":d['lower_cut_volume_m3']<=ideal<=d['upper_cut_volume_m3'],
                "unresolved_leaves":d['unresolved_leaves']}
        groups.append(record)
    if expected:
        raise ValueError('missing some expected pilot bins')
    report={'stage':'P10QA','status':'PASS_4_BIN_DEPTH16_PHYSICAL_BRACKET_PILOT',
            'mesh_sha256':pinned,'pilot_bins':groups,
            'note':'Physical bracket widths; ideal sphere is external benchmark, not an exact identity of M8 discretization.',
            'mesh_changed':False,'fem_started':False,'gmsh_generated':False}
    a.csv.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    a.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('P10QA_PILOT_DEPTH16_INDEPENDENT_QA_PASS',flush=True)


if __name__=='__main__':
    main()
