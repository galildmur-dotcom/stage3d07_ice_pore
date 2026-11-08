#!/usr/bin/env python3
"""P08B native report regression: complete, missing and invalid inputs, fixed delta comparisons."""
import argparse
import csv
import pathlib
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--report', required=True)
args = parser.parse_args()


def makecase(root, case, mesh, dt, ds, cutoff=5., corrupt=False):
    name = f'{mesh}_dt{dt}_q3_t3600_EDV_VAR_XI0'
    if cutoff != 5:
        name += '_cutoff4p000mm'
    path = root / 'LOCAL_RUNS' / 'SHAPE_STAGE08' / name
    path.mkdir(parents=True)
    (path/'P08_RUN_STATUS.txt').write_text(f'status=SUCCESS\nmesh={mesh}\n')
    with (path/'P08_J6_RADIUS_FD.csv').open('w', newline='') as out:
        w = csv.writer(out)
        w.writerow('mesh dt_s tend_s quad delta_um j6_plus j6_minus D_R_j6_per_m relative_radius_sensitivity Phi6_final_plus Phi6_final_minus steps_verified'.split())
        for d in ds:
            target = .1 + {'H0_300':0., 'H0_150':.01, 'H1_300':.002,
                           'H1_150':.015, 'H2_150':.017, 'H0_300_cutoff4':.001}[case] + .0001*d*d
            plus = .008 + target*d*1e-6
            minus = .008 - target*d*1e-6
            derivative = (plus-minus)/(2*d*1e-6)
            if corrupt:
                derivative += 1
            w.writerow([mesh,dt,3600,3,d,repr(plus),repr(minus),repr(derivative),repr(.001*derivative/.008),.013,.013,3600//dt])

with tempfile.TemporaryDirectory(prefix='p08b_synth_') as temp:
    root = pathlib.Path(temp)
    makecase(root,'H0_300','H0',300,[10.,5.,2.5])
    makecase(root,'H0_150','H0',150,[5.,2.5])
    makecase(root,'H1_300','H1',300,[5.,2.5], corrupt=True)
    makecase(root,'H1_150','H1',150,[5.,2.5])
    makecase(root,'H0_300_cutoff4','H0',300,[5.],cutoff=4.)
    # H2 intentionally absent
    p = subprocess.run([args.report, '--root', str(root)],capture_output=True,text=True,check=True)
    assert 'P08B_REPORT_OK' in p.stdout, p.stdout
    output = root/'LOCAL_RUNS'/'SHAPE_STAGE08'/'P08B'
    def rows(name):
        with (output/name).open() as f:
            return list(csv.DictReader(f))
    statuses = {r['case']:r['state'] for r in rows('P08B_CASES.csv')}
    assert statuses == {'H0_300':'COMPLETE','H0_150':'COMPLETE','H1_300':'INVALID',
                        'H1_150':'COMPLETE','H2_150':'MISSING','H0_300_cutoff4':'COMPLETE'}, statuses
    assert len(rows('P08B_DERIVATIVES.csv')) == 8, 'incorrect validated FD row count'
    assert len(rows('P08B_RICHARDSON.csv')) == 6
    comps = {r['comparison']:r for r in rows('P08B_COMPARISON.csv')}
    assert len(comps)==10
    assert comps['temporal_H0_300_to_150_d5']['status']=='READY'
    assert comps['spatial_H1_to_H2_dt150_d5']['status']=='WAITING'
    assert comps['extension_cutoff5_to_4_H0_dt300_d5']['status']=='READY'
    assert abs(float(comps['temporal_H0_300_to_150_d5']['difference']) - .01)<1e-7
    assert all((output/name).exists() for name in ['P08B_NEXT_ACTION_RU.md','P08B_CASES.csv','P08B_COMPARISON.csv'])
    # no files created by --dry-run in fresh project
    other = root/'fresh'
    p2 = subprocess.run([args.report, '--root', str(other), '--dry-run'],capture_output=True,text=True,check=True)
    assert 'MISSING' in p2.stdout
    assert not other.exists()
print('P08B synthetic report PASS: case status, invalid FD, pairwise deltas, cutoff, read-only dry run')
