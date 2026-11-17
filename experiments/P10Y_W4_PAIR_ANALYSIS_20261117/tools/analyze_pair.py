#!/usr/bin/env python3
"""P10Y W4 B2/B20 radial-shape derivative comparison. Python stdlib only.

Use: python tools/analyze_pair.py --dataset ROOT_OF_THIS_EXPERIMENT
Or, from project root: python experiments/P10Y_W4_PAIR_ANALYSIS_20261117/tools/analyze_pair.py
Data: four original P10Y CSVs stored in experiment/input.
"""
import argparse
import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

INPUTS = {
    'B2': ('W4B2_P10Y_SHELL_SUMMARY.csv', 'W4B2_P10Y_PARTITION_AUDIT.csv',
           'b7d98e3831a3641d602b83627ac00adaca12404479902a4dc1a371688b9c9937',
           '417a9a3cd21c3a9eae12d09f4788129c0ca2c511924471dadd03d1dcb35449f8'),
    'B20': ('W4B20_P10Y_SHELL_SUMMARY.csv', 'W4B20_P10Y_PARTITION_AUDIT.csv',
            '825111173d3d39984ff74235512194941cbc98b5b2574dbb5bfcbf82cc5922f7',
            '685f11c7c1bcbefc58046e60424f16b9e31888e9f21573f2ef2496200bcfd815'),
}
COLUMNS = ['sum_explicit_objective_per_m', 'sum_equilibrium_residual_per_m',
           'sum_internal_history_per_m', 'sum_mechanical_per_m']
AUDIT_COLUMNS = ['global_explicit_objective_per_m', 'global_equilibrium_residual_per_m',
                 'global_internal_history_per_m', 'global_mechanical_per_m']
MEASURED_MESHES = {'B2':'H4W4B2', 'B20':'H4W4B20_P10AB'}
FUNCTIONALS = ('j6', 'jpeak', 'jen')


def read_csv(path, expected_sha):
    blob = path.read_bytes()
    assert hashlib.sha256(blob).hexdigest() == expected_sha, f'SHA256 mismatch: {path}'
    return list(csv.DictReader(blob.decode('utf-8-sig').splitlines()))


def run(dataset):
    by_shell, by_audit = {}, {}
    for key, (shell, audit, hash_shell, hash_audit) in INPUTS.items():
        s = read_csv(dataset/'input'/shell, hash_shell)
        a = read_csv(dataset/'input'/audit, hash_audit)
        assert len(s) == 30 and len(a) == 3
        assert {x['functional'] for x in a} == set(FUNCTIONALS)
        assert all(x['mesh'] == MEASURED_MESHES[key] and x['mode'] == 'R' and float(x['delta_um']) == 0 for x in s+a)
        for functional in FUNCTIONALS:
            elements = [x for x in s if x['functional'] == functional]
            assert len(elements) == 10
            audit_row = next(x for x in a if x['functional'] == functional)
            for col, audit_col in zip(COLUMNS, AUDIT_COLUMNS):
                total = math.fsum(float(x[col]) for x in elements)
                global_value = float(audit_row[audit_col])
                assert math.isclose(total, global_value, abs_tol=3e-12, rel_tol=3e-12), (key,functional,col,total,global_value)
            assert float(audit_row['max_partition_relative_error']) < 1e-10
        by_shell[key] = s
        by_audit[key] = a

    all_rows = []
    diagnostics = {}
    for functional in FUNCTIONALS:
        a = [x for x in by_shell['B2'] if x['functional'] == functional]
        b = [x for x in by_shell['B20'] if x['functional'] == functional]
        cumulative = [0.,0.,0.,0.]
        diffs = []
        for index, (before, after) in enumerate(zip(a,b)):
            assert before['distance_lower_mm'] == after['distance_lower_mm'] and before['distance_upper_mm'] == after['distance_upper_mm']
            raw_values_a = [float(before[k]) for k in COLUMNS]
            raw_values_b = [float(after[k]) for k in COLUMNS]
            delta = [new-old for new,old in zip(raw_values_b,raw_values_a)]
            for j in range(4): cumulative[j] += delta[j]
            diffs.append(delta)
            row = dict(functional=functional, shell_index=index,
                       distance_lower_mm=before['distance_lower_mm'], distance_upper_mm=before['distance_upper_mm'])
            for j,name in enumerate(('explicit','equilibrium','EDV_history','mechanical')):
                row[f'{name}_W4B2_per_m']=format(raw_values_a[j],'.17g')
                row[f'{name}_W4B20_per_m']=format(raw_values_b[j],'.17g')
                row[f'delta_{name}_B20_minus_B2_per_m']=format(delta[j],'.17g')
                row[f'cumulative_delta_{name}_per_m']=format(cumulative[j],'.17g')
            if index == 9:
                row['final_delta_mechanical_per_m'] = format(cumulative[3],'.17g')
            else:
                row['final_delta_mechanical_per_m'] = ''
            all_rows.append(row)
        ref_a=next(x for x in by_audit['B2'] if x['functional']==functional)
        ref_b=next(x for x in by_audit['B20'] if x['functional']==functional)
        global_mech = float(ref_b['global_mechanical_per_m'])-float(ref_a['global_mechanical_per_m'])
        assert math.isclose(math.fsum(z[3] for z in diffs),global_mech,abs_tol=3e-12,rel_tol=3e-12)
        diagnostics[functional] = {
           'global_mech_delta':global_mech,
           'global_explicit_delta':float(ref_b['global_explicit_objective_per_m'])-float(ref_a['global_explicit_objective_per_m']),
           'global_eq_delta':float(ref_b['global_equilibrium_residual_per_m'])-float(ref_a['global_equilibrium_residual_per_m']),
           'global_EDV_delta':float(ref_b['global_internal_history_per_m'])-float(ref_a['global_internal_history_per_m']),
           'absolute_mechanical_shell_deltas':math.fsum(abs(z[3]) for z in diffs),
           'absolute_all_component_shell_deltas':math.fsum(abs(z[j]) for z in diffs for j in range(3)),
           'max_abs_mech_shell_index':max(range(10),key=lambda i:abs(diffs[i][3])),
           'sum_0_0p25':math.fsum(z[3] for z in diffs[:4]),
           'sum_0p25_2':math.fsum(z[3] for z in diffs[4:7]),
           'sum_2_5':diffs[7][3],
        }
    destination=dataset/'derived'
    destination.mkdir(parents=True,exist_ok=True)
    output=destination/'P10Y_W4_B20_MINUS_B2_RADIAL_DIFFS.csv'
    with output.open('w',encoding='utf-8',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=list(all_rows[0]),lineterminator='\n')
        wr.writeheader();wr.writerows(all_rows)
    print('P10Y_W4_PAIR_RADIAL_ANALYSIS_OK rows=',len(all_rows),'output=',output)
    for func,d in diagnostics.items():
        print(func,'global_mechanical_delta=',f"{d['global_mech_delta']:+.12e}",
              'max_shell=',d['max_abs_mech_shell_index'],'abs_sum_ratio=',
              f"{d['absolute_mechanical_shell_deltas']/abs(d['global_mech_delta']):.6f}")
    return diagnostics

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,default=Path(__file__).resolve().parents[1])
    args=p.parse_args()
    run(args.dataset)
