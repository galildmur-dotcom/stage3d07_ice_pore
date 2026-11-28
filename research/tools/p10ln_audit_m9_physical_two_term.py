#!/usr/bin/env python3
"""Read-only independent P10LN audit of P10LM physical M9 evidence.

Recompute all 4D split aggregates from raw CSV, compare to manifest and
historical accepted P10LC M9, and audit pole by radial shell and time.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[2]
NEW=ROOT/'upload/P10LM_M9_FIRST_FULL4D_EVIDENCE.zip'
OLD=ROOT/'upload/P10LC_M9_FIRST_FULL4D_EVIDENCE.zip'
OUT=ROOT/'research/P10LN_M9_PHYSICAL_TWO_TERM_INDEPENDENT_QA.json'
SHA_M9='a40aca54636a752afe4d7babe9d03e741b2e988b9ad3dbb6f356728bff035a58'
SHA_HEADER='0a470e43668a751dc0514f94e8e33ad2b8615c9d56c633579dd7112fafcec2b3'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b,label,tol=2e-9):
    if abs(a-b)>tol:
        raise RuntimeError(f'P10LN {label} mismatch {a:.17g} {b:.17g}')


def main():
    with zipfile.ZipFile(NEW) as z,zipfile.ZipFile(OLD) as prior:
        assert z.testzip() is None and prior.testzip() is None
        m=json.loads(z.read('P10LM_MANIFEST.json'))
        p=json.loads(prior.read('P10LC_MANIFEST.json'))
        assert m['status']=='P10LM_M9_REAL_FULL4D_PASS'
        assert m['native_exit_code']==0 and m['FEM_attempts']==1
        assert not m['stop_reason']
        assert m['mesh_sha256']==p['mesh_sha256']==SHA_M9
        assert m['P10LG_header_sha256']==SHA_HEADER
        assert m['regime']==p['regime']
        assert m['source_revision']=='P10LM_M9_TWO_TERM_EXPLICIT_INSTRUMENTED_P10LG_V1'
        old={}
        with z.open('P10DD_SIGNED_R_THETA_PHI_T.csv') as raw:
            reader=csv.DictReader(io.TextIOWrapper(raw,encoding='utf8'))
            for row in reader:
                if row['region']!='VOLUME':continue
                key=tuple(int(row[k]) for k in ('step','radial_bin','mu_bin','phi_bin'))
                if key in old:raise RuntimeError('duplicate source bin')
                old[key]=float(row['mech_explicit_per_m'])
        assert len(old)==43200
        sums={'geometry':0.,'stress':0.,'explicit':0.}
        by_radial=[dict.fromkeys(sums,0.) for _ in range(10)]
        by_pole=[dict.fromkeys(sums,0.) for _ in range(3)]
        radial_polar=[[dict.fromkeys(sums,0.) for _ in range(3)] for _ in range(10)]
        by_time=[dict.fromkeys(sums,0.) for _ in range(36)]
        seen=set()
        with z.open('P10LG_EXPLICIT_GEOMETRY_STRESS_4D.csv') as raw:
            reader=csv.DictReader(io.TextIOWrapper(raw,encoding='utf8'))
            assert reader.fieldnames==['mesh','step','time_end_s','radial_bin','mu_bin','phi_bin',
                'explicit_geometry_normalization_per_m','explicit_stress_chain_per_m','explicit_sum_per_m']
            for row in reader:
                step,ir,im,ip=(int(row[k]) for k in ('step','radial_bin','mu_bin','phi_bin'))
                key=(step,ir,im,ip)
                if key in seen:raise RuntimeError('duplicate sidecar bin')
                seen.add(key)
                assert row['mesh']=='M9' and int(row['time_end_s'])==step*25
                g=float(row['explicit_geometry_normalization_per_m'])
                s=float(row['explicit_stress_chain_per_m'])
                e=float(row['explicit_sum_per_m'])
                assert all(math.isfinite(v) for v in (g,s,e))
                close(g+s,e,'internal bin closure',tol=1e-10)
                close(e,old[key],'independent original P10DD bin',tol=1e-10)
                pole=0 if im==0 else 2 if im==9 else 1
                for output in (sums,by_radial[ir],by_pole[pole],radial_polar[ir][pole],by_time[step-1]):
                    output['geometry']+=g
                    output['stress']+=s
                    output['explicit']+=e
        assert len(seen)==43200
        close(sums['geometry']+sums['stress'],sums['explicit'],'global internal')
        for key,k in (('geometry','geometry_per_m'),('stress','stress_per_m'),('explicit','explicit_per_m')):
            close(sums[key],m['two_term_explicit'][k],'manifest component')
        close(sums['explicit'],m['independent_4d']['components']['mech_explicit_per_m'],'manifest original explicit')
        old_components=p['independent_4d']['components']
        new_components=m['independent_4d']['components']
        parity={k:{'prior':old_components[k],'now':new_components[k],
                   'delta':new_components[k]-old_components[k]} for k in old_components}
        for k in old_components:close(old_components[k],new_components[k],'same mesh '+k,tol=1e-8)
        close(p['independent_4d']['jpeak_derivative_per_m'],
              m['independent_4d']['jpeak_derivative_per_m'],'same mesh total',tol=1e-8)
        n=m['cpu_telemetry']
        result={
            'protocol':'P10LN_INDEPENDENT_REAL_M9_TWO_TERM_PHYSICAL_AUDIT',
            'status':'PASS_REAL_M9_WITH_INDEPENDENT_CSV_AND_PRIOR_RUN_PARITY',
            'zip_sha256':sha(NEW),'zip_crc':'PASS',
            'physical_mesh':'M9','mesh_sha256':SHA_M9,
            'cpp_header_sha256':SHA_HEADER,
            'native_exit_code':m['native_exit_code'],'FEM_attempts_recorded':m['FEM_attempts'],
            'wall_s':m['wall_s'],'peak_private_bytes':m['peak_private_bytes_polled'],
            'average_busy_logical_cpus':n['average_busy_logical_CPUs'],
            'rows_checked':len(seen),'original_binned_rows_checked':len(old),
            'all_B6_per_m':sums,'by_radial_10_bins_per_m':by_radial,
            'by_latitude_south_mu0_middle_mu1to8_north_mu9_per_m':by_pole,
            'by_radial_and_latitude_per_m':radial_polar,
            'by_time_36_steps_per_m':by_time,
            'prior_P10LC_vs_new_P10LM_parity':parity,
            'prior_P10LC_total_derivative_per_m':p['independent_4d']['jpeak_derivative_per_m'],
            'new_P10LM_total_derivative_per_m':m['independent_4d']['jpeak_derivative_per_m'],
            'physical_M8_two_term_decomposition':'NOT_YET_MEASURED',
            'M8_M9_decomposition_attribution':'NOT_YET_ESTABLISHED',
            'FEM_attempts_this_audit':0,'mesh_generation_attempts_this_audit':0}
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in
        ('by_radial_10_bins_per_m','by_latitude_south_mu0_middle_mu1to8_north_mu9_per_m',
         'by_radial_and_latitude_per_m','by_time_36_steps_per_m','prior_P10LC_vs_new_P10LM_parity')},
        indent=2,ensure_ascii=False))
    print('POLAR_FIRST_SHELL',json.dumps(radial_polar[0],ensure_ascii=False))


if __name__=='__main__':main()
