#!/usr/bin/env python3
"""P10Z/Stage3D07 postprocessing of two archived geometry-only mesh audits.
Only the Python standard library is required for numerical comparisons.
matplotlib is optional, used for saved PNG/SVG figures. No FEM work.
"""
from pathlib import Path
import argparse, hashlib, csv, io, zipfile, math, datetime

MESHES=['H4','H4W2','H4W2B20','H4W4B2']
CUTS=[.005,.01,.02,.05,.1,.2]

def f(x):return float(x)
def hexdigest(b):return hashlib.sha256(b).hexdigest()
def digest(path):return hexdigest(Path(path).read_bytes())
def read_zip(path, root):
    with zipfile.ZipFile(path) as z:
        expect={}
        for raw in z.read('RESULTS_INFO_SHA256.txt').decode('utf-8-sig').splitlines():
            if len(raw)>=66 and raw[64:66]=='  ':
                expect[raw[66:]]=raw[:64]
        assert set(expect)=={'P10Z_MESH_QP_SHELL_METRICS.csv','P10Z_RADIAL_CUMULATIVE.csv','P10Z_MESH_AUDIT_LOG.txt'}
        for name,h in expect.items():
            b=z.read(name)
            assert hexdigest(b)==h, (name,h)
            (root/name).write_bytes(b)
        (root/'RESULTS_INFO_SHA256.txt').write_bytes(z.read('RESULTS_INFO_SHA256.txt'))
        m=list(csv.DictReader(io.StringIO(z.read('P10Z_MESH_QP_SHELL_METRICS.csv').decode('utf-8-sig'))))
        c=list(csv.DictReader(io.StringIO(z.read('P10Z_RADIAL_CUMULATIVE.csv').decode('utf-8-sig'))))
        return m,c

def write_rows(path, rows):
    with open(path,'w',newline='',encoding='utf-8') as fh:
        w=csv.DictWriter(fh,fieldnames=list(rows[0]),lineterminator='\n')
        w.writeheader();w.writerows(rows)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--base',required=True)
    p.add_argument('--refined',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    dest=Path(args.out); (dest/'derived').mkdir(parents=True,exist_ok=True)
    (dest/'figures').mkdir(exist_ok=True)
    basefolder=dest/'input'/'BASE'; refinefolder=dest/'input'/'REFINED'
    basefolder.mkdir(parents=True,exist_ok=True);refinefolder.mkdir(parents=True,exist_ok=True)
    m1,c1=read_zip(args.base,basefolder)
    m2,c2=read_zip(args.refined,refinefolder)
    ms=m1+m2;cs=c1+c2
    assert len(ms)==80 and len(cs)==128
    assert set(r['mesh'] for r in ms)==set(MESHES)
    assert set(int(r['quadrature_order']) for r in ms)=={3,4}
    shell={(r['mesh'],int(r['quadrature_order']),int(r['shell'])):r for r in ms}
    cumulative={(r['mesh'],int(r['quadrature_order']),f(r['distance_upper_mm'])):r for r in cs}
    assert len(shell)==80 and len(cumulative)==128
    lines=['P10Z 4-mesh geometry-only audit checks / 2026-11-13',
           f'base_zip_sha256={digest(args.base)}', f'refined_zip_sha256={digest(args.refined)}',
           'All three primary file SHA256 per ZIP: verified from RESULTS_INFO_SHA256.txt']
    for mesh in MESHES:
        for order in [3,4]:
            q=[shell[mesh,order,i] for i in range(10)]
            assert len({r['mesh_sha256'] for r in q})==1
            assert all(f(r['geometry_center_z_m'])==.03 and f(r['pore_radius_mm'])==1. for r in q)
            assert all(int(r['negative_pore_distance_qp'])==0 for r in q)
            assert sum(int(r['qp_count']) for r in q)==int(q[0]['total_qp'])==int(q[0]['total_tet10'])*order**3
            total=sum(f(r['integration_volume_mm3']) for r in q)
            global_vol=f(q[0]['global_mesh_quadrature_volume_mm3'])
            assert abs(total-global_vol)<3e-8, (mesh,order,total,global_vol)
            for cut,last in [(0.02,0),(0.05,1),(0.1,2),(0.25,3),(0.5,4),(1.,5),(2.,6),(5.,7)]:
                a=cumulative[mesh,order,cut]
                expected=sum(f(q[i]['integration_volume_mm3']) for i in range(last+1))
                assert abs(f(a['integration_volume_mm3'])-expected)<1e-7,(mesh,order,cut)
            lines.append(f'{mesh} Q{order}: tet10={q[0]["total_tet10"]}, qp={q[0]["total_qp"]}, volume_mm3={global_vol:.12f}, sum_resid_mm3={total-global_vol:.4e}, sha={q[0]["mesh_sha256"]}')
        assert abs(f(shell[mesh,3,0]['global_mesh_quadrature_volume_mm3'])-f(shell[mesh,4,0]['global_mesh_quadrature_volume_mm3']))<1e-7
    (dest/'derived'/'VERIFICATION.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8')

    shell_rows=[]
    for mesh in MESHES:
        for i in range(10):
            r3=shell[mesh,3,i];r4=shell[mesh,4,i]
            ref=f(r3['full_spherical_shell_reference_mm3']) if r3['full_spherical_shell_reference_mm3'] else float('nan')
            v3=f(r3['integration_volume_mm3']);v4=f(r4['integration_volume_mm3'])
            shell_rows.append(dict(mesh=mesh,shell=i,lower_mm=r3['lower_mm'],upper_mm=r3['upper_mm'],
                qp_q3=int(r3['qp_count']),qp_q4=int(r4['qp_count']),
                n_eff_q3=f(r3['effective_qp_count_weight']),n_eff_q4=f(r4['effective_qp_count_weight']),
                tet_with_qp_q3=int(r3['tet10_with_qp_in_shell']),
                radial_node_span_p50_q3_mm=f(r3['radial_node_span_p50_mm']) if r3['radial_node_span_p50_mm'] else '',
                integration_q3_mm3=v3,integration_q4_mm3=v4,analytic_sphere_mm3=ref if i<9 else '',
                q3_minus_sphere_pct=100*(v3/ref-1) if i<9 else '',
                q4_minus_sphere_pct=100*(v4/ref-1) if i<9 else '',
                q4_minus_q3_as_sphere_pct=100*(v4-v3)/ref if i<9 else ''))
    write_rows(dest/'derived'/'P10Z_4MESH_SHELLS_Q3_Q4.csv',shell_rows)

    cum_rows=[]
    all_cuts=sorted(set(f(r['distance_upper_mm']) for r in cs))
    for cut in all_cuts:
        for mesh in MESHES:
            r3=cumulative[mesh,3,cut];r4=cumulative[mesh,4,cut]
            ref=f(r3['full_spherical_reference_mm3']);v3=f(r3['integration_volume_mm3']);v4=f(r4['integration_volume_mm3'])
            cum_rows.append(dict(mesh=mesh,distance_upper_mm=cut,qp_q3=int(r3['qp_inside']),qp_q4=int(r4['qp_inside']),
                volume_q3_mm3=v3,volume_q4_mm3=v4,analytic_reference_mm3=ref,
                error_q3_pct=100*(v3/ref-1),error_q4_pct=100*(v4/ref-1),
                q4_minus_q3_pct_of_sphere=100*(v4-v3)/ref,
                q4_minus_q3_abs_pct_of_sphere=100*abs(v4-v3)/ref))
    write_rows(dest/'derived'/'P10Z_4MESH_CUMULATIVE_Q3_Q4.csv',cum_rows)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,ax=plt.subplots(figsize=(8.6,4.5))
        for mesh in MESHES:
            vals=[next(z for z in cum_rows if z['mesh']==mesh and z['distance_upper_mm']==x)['error_q3_pct'] for x in all_cuts if x<=.1]
            ax.plot([x*1000 for x in all_cuts if x<=.1],vals,marker='o',markersize=3,label=mesh)
        ax.set_xlabel('Distance from wall (micrometres)')
        ax.set_ylabel('Q3 cumulative volume error vs ideal sphere (%)')
        ax.axhline(0,linewidth=.8,color='gray')
        ax.legend(ncols=2);ax.grid(True,alpha=.25);fig.tight_layout()
        for ext in ['png','svg']:fig.savefig(dest/'figures'/f'P10Z_Q3_CUMULATIVE_ERRORS.{ext}',dpi=200)
        plt.close(fig)
        fig,ax=plt.subplots(figsize=(8.6,4.5))
        vals3=[next(z for z in cum_rows if z['mesh']==mesh and z['distance_upper_mm']==.02)['error_q3_pct'] for mesh in MESHES]
        vals4=[next(z for z in cum_rows if z['mesh']==mesh and z['distance_upper_mm']==.02)['error_q4_pct'] for mesh in MESHES]
        xs=list(range(4))
        ax.bar([x-.2 for x in xs],vals3,width=.4,label='Q3 (27 points)')
        ax.bar([x+.2 for x in xs],vals4,width=.4,label='Q4 (64 points)')
        ax.set_xticks(xs,MESHES);ax.set_ylabel('0–0.02 mm shell volume error vs ideal sphere (%)')
        ax.axhline(0,linewidth=.8,color='gray');ax.legend();ax.grid(True,axis='y',alpha=.25)
        fig.tight_layout()
        for ext in ['png','svg']:fig.savefig(dest/'figures'/f'P10Z_FIRST_SHELL_Q3_Q4.{ext}',dpi=200)
        plt.close(fig)
    except ImportError:
        print('No matplotlib: CSV generated, figures skipped')
    print('P10Z_POSTPROCESS_OK meshes=',MESHES)

if __name__=='__main__':main()
