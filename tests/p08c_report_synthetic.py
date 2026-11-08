import argparse
import csv
import math
import pathlib
import subprocess
import tempfile

p=argparse.ArgumentParser()
p.add_argument('--report',required=True)
a=p.parse_args()
ms=['tx','ty','tz','y20','y21c','y21s','y22c','y22s']
with tempfile.TemporaryDirectory(prefix='p08c_synthetic_') as tmp:
    r=pathlib.Path(tmp)/'cases';out=pathlib.Path(tmp)/'summary'
    for mode in ms:
        m=r/mode;m.mkdir(parents=True)
        (m/'P08C_MODE_GUARD.txt').write_text('synthetic test guard')
        (m/'P08C_MODE_STATUS.txt').write_text(f'status=SUCCESS\nmode={mode}\nmesh=H0\ndt=300\ntend=3600\n')
        geo=m/'geometry';geo.mkdir()
        with (geo/'P08_GEOMETRIC_DERIVATIVE.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['mode','delta_um','dV_ice_damplitude_m2','exact_dV_radial_m2','relative_error_radial','expected_zero_nonradial'])
            for d in [5,2.5]:w.writerow([mode,d,0,0,0,1])
        with (m/'P08C_MODE_FD.csv').open('w',newline='') as f:
            w=csv.writer(f);w.writerow(['mode','mesh','dt_s','tend_s','quad','delta_um','j6_plus','j6_minus','D_j6_per_m','normalized_by_j6_over_R','Phi6_final_plus','Phi6_final_minus','steps_verified'])
            for d in [5,2.5]:
                delta=d*1e-6
                D=.1+(1e5*delta**2)
                jj=.0083
                w.writerow([mode,'H0',300,3600,3,d,jj+delta*D,jj-delta*D,D,.001*D/jj,.01,.01,12])
    cmd=[a.report,'--root',str(r),'--out',str(out)]
    pp=subprocess.run(cmd,capture_output=True,text=True)
    assert pp.returncode==0,(pp.stdout,pp.stderr)
    with (out/'P08C_CASES.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==8 and all(x['status']=='COMPLETE' for x in rows),rows
    with (out/'P08C_DERIVATIVES.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==16,rows
    for x in rows:
        assert math.isclose(float(x['Richardson_to_zero']),.1,rel_tol=1e-10),x
    with (out/'P08C_SYMMETRY.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==8 and sum(int(x['expected_first_derivative_zero_by_symmetry']) for x in rows)==6
    # Corrupt a single mode, ensure no invented derivatives; report stays usable.
    with (r/'y20'/'P08C_MODE_FD.csv').open('a') as f:f.write('corrupt,broken\n')
    pp=subprocess.run(cmd,capture_output=True,text=True)
    assert pp.returncode==0,pp.stderr
    with (out/'P08C_CASES.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert next(x for x in rows if x['mode']=='y20')['status']=='INVALID'
    with (out/'P08C_DERIVATIVES.csv').open(newline='') as f:rows=list(csv.DictReader(f))
    assert len(rows)==14
print('P08C_REPORT_SYNTHETIC_OK')
