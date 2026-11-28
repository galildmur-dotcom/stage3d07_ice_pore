#!/usr/bin/env python3
"""No-FEM negative/positive synthetic test for independent P10LM CSV auditor."""
from __future__ import annotations
import csv
import pathlib
import sys
import tempfile

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from p10lm_split_audit import audit_split,NAME


def main():
    with tempfile.TemporaryDirectory(prefix='p10lm_split_qa_') as folder:
        path=pathlib.Path(folder)
        with (path/'P10DD_SIGNED_R_THETA_PHI_T.csv').open('w',newline='') as file:
            writer=csv.writer(file)
            writer.writerow(['mesh','region','step','radial_bin','mu_bin','phi_bin','mech_explicit_per_m'])
            for step in range(1,7):
                for ir in range(10):
                    for im in range(10):
                        for ip in range(12):
                            writer.writerow(['M9','VOLUME',step,ir,im,ip,(ir+1)*0.125])
        with (path/NAME).open('w',newline='') as file:
            writer=csv.writer(file)
            writer.writerow(['mesh','step','time_end_s','radial_bin','mu_bin','phi_bin',
                             'explicit_geometry_normalization_per_m',
                             'explicit_stress_chain_per_m','explicit_sum_per_m'])
            for step in range(1,7):
                for ir in range(10):
                    for im in range(10):
                        for ip in range(12):
                            writer.writerow(['M9',step,step*150,ir,im,ip,
                                             (ir+1)*.2,-(ir+1)*.075,(ir+1)*.125])
        result=audit_split(path,'M9',6,150)
        assert result['status']=='P10LM_TWO_TERM_PHYSICAL_CSV_QA_PASS'
        assert result['rows']==7200
        # Corrupt an interior row, preserving row counts and all other fields.
        lines=(path/NAME).read_text().splitlines(keepends=True)
        fields=lines[102].rstrip('\r\n').split(',')
        fields[7]='999'
        lines[102]=','.join(fields)+'\n'
        (path/NAME).write_text(''.join(lines))
        stopped=False
        try:audit_split(path,'M9',6,150)
        except RuntimeError as err:stopped='signed per-bin closure' in str(err)
        assert stopped,'the auditor failed to reject a corrupted stress bin'
    print('P10LM_SPLIT_INDEPENDENT_AUDIT_SELFTEST_PASS rows=7200 corrupted_bin=REJECTED no_FEM=1')


if __name__=='__main__':main()
