"""Non-destructive, source-independent P07 inventory fixtures."""
import csv
import pathlib
import struct
import subprocess
import sys
import tempfile

exe = pathlib.Path(sys.argv[1]).resolve()

def history(root, mesh='H3', dt=300, q=3, mod='VAR', steps=12, checkpoint=False, invalid=False):
    dest = root / 'LOCAL_RUNS' / f'{mesh}_dt{dt}_q{q}' / 'mechanics' / f'EDV_{mod}'
    dest.mkdir(parents=True, exist_ok=True)
    with (dest/'time_series.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['time_s','dt_s','Psi6','PsiOmega','maxS1_MPa','Newton','CG','residual_rel','wall_s'])
        for i in range(1,steps+1):
            t = dt*i
            if invalid and i == steps: t -= dt
            w.writerow([t,dt,0.001 + t*1e-8,0.002+t*1e-8,0.1+t*1e-6,2,140,1e-10,0.4])
    with (dest/'polar_caps_history.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['time_s','top','bottom','topvol','bottomvol'])
        w.writerow([steps*dt,0.125,0.113,1.0,1.0])
    if checkpoint:
        n, ng = 100, 200
        content = struct.pack('<QQQQiiIId', 0x4943453344303602, n, ng, 1234, q, steps, int(mod=='VAR'),2,float(steps*dt))
        (dest/'restart.bin').write_bytes(content + b'\0' * (24*n+ng*8))

with tempfile.TemporaryDirectory(prefix='p7-regression-') as tmp:
    project=pathlib.Path(tmp)/'Stage3D07_project'
    prior=pathlib.Path(tmp)/'OldStage3D06'
    history(prior,mesh='H3',dt=300,checkpoint=True)
    history(project,mesh='H3',dt=150,steps=24,checkpoint=False)
    history(project,mesh='H4',dt=25,steps=6,checkpoint=True)
    history(project,mesh='H2',dt=75,steps=48,checkpoint=True,invalid=True)
    cp=subprocess.run([str(exe),'--root',str(project),'--no-siblings','--scan-root',str(prior)],capture_output=True,text=True,check=True)
    output=project/'LOCAL_RUNS'/'REFINEMENT_CAMPAIGN'
    with (output/'P07_INVENTORY.csv').open(newline='') as f:
        rows={(x['mesh'],int(x['dt_s']),x['modulus'],int(x['quadrature'])):x for x in csv.DictReader(f)}
    assert len(rows)==23,len(rows)
    assert rows[('H3',300,'VAR',3)]['status']=='COMPLETE',rows[('H3',300,'VAR',3)]
    assert rows[('H3',150,'VAR',3)]['status']=='HISTORY_ONLY'
    assert rows[('H4',25,'VAR',3)]['status']=='PARTIAL'
    assert rows[('H2',75,'VAR',3)]['status']=='INVALID_HISTORY'
    assert rows[('H3',75,'VAR',4)]['status']=='MISSING'
    pairs=list(csv.DictReader((output/'P07_CONVERGENCE_DATA.csv').open(newline='')))
    assert len(pairs)==1 and pairs[0]['comparison']=='temporal',pairs
    assert int(pairs[0]['shared_first900_points'])==3,pairs
    assert 'campaign_full_checkpoints=1/16' in cp.stdout,cp.stdout
    print('PASS: external root discovery, strict history, checkpoint header, invalid/partial/missing, temporal pair, no FEM runs')
