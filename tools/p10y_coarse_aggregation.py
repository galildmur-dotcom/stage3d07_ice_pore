#!/usr/bin/env python3
"""Read P10Y mechanical shell CSVs; group signed data without redefining B6.

Usage: python aggregate_p10y.py --h4 FILE --h4w2 FILE --out DIR
Only Python stdlib is required for CSVs. matplotlib makes optional figures.
"""
import argparse
import csv
import hashlib
import math
from pathlib import Path

PARTS = ['sum_explicit_objective_per_m',
         'sum_equilibrium_residual_per_m',
         'sum_internal_history_per_m',
         'sum_mechanical_per_m']
FUNCS = ['jpeak', 'j6', 'jen']
FINE_EDGES = [0, .02, .05, .1, .25, .5, 1, 2, 5, 15]
COARSE_EDGES = [0, .1, .25, .5, 2, 5]
ALIASES = ['explicit','equilibrium','history','mechanical']

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(2**20), b''):
            h.update(chunk)
    return h.hexdigest()

def load(path, mesh):
    with open(path, encoding='utf-8-sig', newline='') as f:
        data = list(csv.DictReader(f))
    assert len(data) == 30, f'{mesh}: 30 rows expected, got {len(data)}'
    out = {}
    for row in data:
        assert row['mesh'] == mesh and row['mode'] == 'R' and float(row['delta_um']) == 0
        func = row['functional']
        assert func in FUNCS
        lo = float(row['distance_lower_mm'])
        hi = float(row['distance_upper_mm']) if row['distance_upper_mm'] else math.inf
        assert any(abs(lo-b) < 1e-10 for b in FINE_EDGES)
        key = (func, next(b for b in FINE_EDGES if abs(lo-b)<1e-10))
        assert key not in out
        values = [float(row[k]) for k in PARTS]
        assert math.isclose(sum(values[:3]), values[3], abs_tol=1e-11), (mesh, key, values)
        out[key] = {'hi': hi, 'values': values}
    assert len(out) == 30
    for f in FUNCS:
        for i,lo in enumerate(FINE_EDGES):
            key = (f, lo)
            assert key in out
            expect = FINE_EDGES[i+1] if i+1 < len(FINE_EDGES) else math.inf
            assert math.isclose(out[key]['hi'], expect, abs_tol=1e-10) if math.isfinite(expect) else math.isinf(out[key]['hi'])
    return out

def write_csv(path, rows):
    with open(path,'w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--h4',required=True,type=Path)
    ap.add_argument('--h4w2',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    opts=ap.parse_args()
    out=opts.out
    (out/'derived').mkdir(parents=True,exist_ok=True)
    (out/'figures').mkdir(parents=True,exist_ok=True)
    a=load(opts.h4,'H4'); b=load(opts.h4w2,'H4W2')
    fine=[]; coarse=[]; cumulative=[]; overview=[]
    for fn in FUNCS:
        all_delta=[]
        full_h4 = [sum(a[(fn,k)]['values'][j] for k in FINE_EDGES) for j in range(4)]
        full_h4w2 = [sum(b[(fn,k)]['values'][j] for k in FINE_EDGES) for j in range(4)]
        full_delta=[full_h4w2[j]-full_h4[j] for j in range(4)]
        cum1=[0]*4;cum2=[0]*4
        for i,lo in enumerate(FINE_EDGES):
            hi=FINE_EDGES[i+1] if i+1<len(FINE_EDGES) else math.inf
            va=a[(fn,lo)]['values']; vb=b[(fn,lo)]['values']
            delta=[vb[k]-va[k] for k in range(4)]
            assert math.isclose(sum(delta[:3]),delta[3],abs_tol=1e-11)
            all_delta.append(delta[3])
            rr={'functional':fn,'lower_mm':lo,'upper_mm':hi if math.isfinite(hi) else '',
               **{f'H4_{t}_per_m':va[j] for j,t in enumerate(ALIASES)},
               **{f'H4W2_{t}_per_m':vb[j] for j,t in enumerate(ALIASES)},
               **{f'delta_{t}_per_m':delta[j] for j,t in enumerate(ALIASES)}}
            fine.append(rr)
            for j in range(4):cum1[j]+=va[j];cum2[j]+=vb[j]
            cc={'functional':fn,'radius_mm':hi if math.isfinite(hi) else '',
                **{f'H4_{t}_per_m':cum1[j] for j,t in enumerate(ALIASES)},
                **{f'H4W2_{t}_per_m':cum2[j] for j,t in enumerate(ALIASES)},
                **{f'delta_{t}_per_m':cum2[j]-cum1[j] for j,t in enumerate(ALIASES)}}
            cumulative.append(cc)
        for lo,hi in zip(COARSE_EDGES[:-1],COARSE_EDGES[1:]):
            keys=[k for k in FINE_EDGES if lo <= k < hi]
            aa=[sum(a[(fn,k)]['values'][j] for k in keys) for j in range(4)]
            bb=[sum(b[(fn,k)]['values'][j] for k in keys) for j in range(4)]
            dd=[bb[j]-aa[j] for j in range(4)]
            assert math.isclose(sum(dd[:3]),dd[3],abs_tol=1e-11)
            coarse.append({'functional':fn,'lower_mm':lo,'upper_mm':hi,
                **{f'H4_{t}_per_m':aa[j] for j,t in enumerate(ALIASES)},
                **{f'H4W2_{t}_per_m':bb[j] for j,t in enumerate(ALIASES)},
                **{f'delta_{t}_per_m':dd[j] for j,t in enumerate(ALIASES)}})
        groups=[r['delta_mechanical_per_m'] for r in coarse if r['functional']==fn]
        assert math.isclose(sum(groups), full_delta[3],abs_tol=1e-11)
        denom=abs(full_delta[3])
        rec={'functional':fn,'H4_mechanical_per_m':full_h4[3],
             'H4W2_mechanical_per_m':full_h4w2[3],
             'delta_mechanical_per_m':full_delta[3],
             'fine_abs_delta_per_m':sum(abs(v) for v in all_delta),
             'coarse_abs_delta_per_m':sum(abs(v) for v in groups),
             'fine_cancellation_factor':sum(abs(v) for v in all_delta)/denom,
             'coarse_cancellation_factor':sum(abs(v) for v in groups)/denom,
             'delta_explicit_per_m':full_delta[0],
             'delta_equilibrium_per_m':full_delta[1],
             'delta_history_per_m':full_delta[2]}
        overview.append(rec)
        assert all(math.isclose(cum1[j],full_h4[j],abs_tol=1e-11) for j in range(4))
        assert all(math.isclose(cum2[j],full_h4w2[j],abs_tol=1e-11) for j in range(4))
    write_csv(out/'derived'/'P10Y_FINE_BIN_COMPONENTS.csv',fine)
    write_csv(out/'derived'/'P10Y_COARSE_BIN_COMPONENTS.csv',coarse)
    write_csv(out/'derived'/'P10Y_CUMULATIVE_COMPONENTS.csv',cumulative)
    write_csv(out/'derived'/'P10Y_CANCELLATION_SUMMARY.csv',overview)
    manifest=(out/'derived'/'VERIFICATION.txt')
    with open(manifest,'w',encoding='utf-8') as f:
        f.write('P10Y H4/H4W2 data-only coarse-bin verification, 2026-11-13\n')
        f.write(f'SHA256 {opts.h4.name} {sha256(opts.h4)}\n')
        f.write(f'SHA256 {opts.h4w2.name} {sha256(opts.h4w2)}\n')
        f.write('30 rows per source, common bins, same mode R and delta_um=0.\n')
        f.write('Each mechanical component reconstructs explicit+equilibrium+history within 1e-11 per m.\n')
        f.write('All coarse and cumulative balances independently checked within 1e-11 per m.\n')
        f.write('Heat adjoint contribution is NOT spatially partitioned. No FEM calculations. Not a convergence proof.\n')
        for row in overview:
            f.write(f"{row['functional']}: total_delta_mech={row['delta_mechanical_per_m']:.15e} "
                    f"fine_cancellation={row['fine_cancellation_factor']:.8f} "
                    f"coarse_cancellation={row['coarse_cancellation_factor']:.8f}\n")
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from matplotlib.ticker import ScalarFormatter
        selected=[r for r in coarse if r['functional']=='jpeak']
        labels=[f"{r['lower_mm']:g}–{r['upper_mm']:g}" for r in selected]
        fig,ax=plt.subplots(figsize=(8.7,4.5))
        z=range(len(labels))
        ax.axhline(0,linewidth=.8,color='gray')
        ax.bar(z,[r['delta_mechanical_per_m'] for r in selected])
        ax.set_xticks(list(z),labels)
        ax.set_xlabel('Distance from pore surface, mm (nonoverlapping groups)')
        ax.set_ylabel('H4W2 − H4 mechanical contribution, m$^{-1}$')
        ax.set_title('$j_{peak}$: changes after aggregation of radial bins')
        ax.grid(axis='y',alpha=.25)
        fig.tight_layout()
        fig.savefig(out/'figures'/'P10Y_JPEAK_COARSE_SIGNED_DIFF.png',dpi=180)
        fig.savefig(out/'figures'/'P10Y_JPEAK_COARSE_SIGNED_DIFF.svg')
        plt.close(fig)
        # cumulative for jpeak: plot between initial and last physically active cutoff
        records=[r for r in cumulative if r['functional']=='jpeak' and r['radius_mm'] and float(r['radius_mm'])<=5]
        xx=[float(r['radius_mm']) for r in records]
        fig,ax=plt.subplots(figsize=(8.7,4.5))
        ax.plot([0]+xx,[0]+[r['delta_mechanical_per_m'] for r in records],'-o',markersize=4)
        tot=overview[0]['delta_mechanical_per_m']
        ax.axhline(tot,linestyle='--',color='gray',label=f'full mechanical difference {tot:.6f} m$^{{-1}}$')
        ax.set_xlabel('Upper integration radius from pore surface, mm')
        ax.set_ylabel('Cumulative mechanical difference, m$^{-1}$')
        ax.set_title('$j_{peak}$: signed accumulation H4W2 − H4')
        ax.legend(loc='best')
        ax.grid(alpha=.25)
        fig.tight_layout()
        fig.savefig(out/'figures'/'P10Y_JPEAK_CUMULATIVE_DELTA.png',dpi=180)
        fig.savefig(out/'figures'/'P10Y_JPEAK_CUMULATIVE_DELTA.svg')
        plt.close(fig)
        fig,ax=plt.subplots(figsize=(8.7,4.5))
        for key,lab in [('delta_explicit_per_m','explicit'),('delta_equilibrium_per_m','equilibrium'),('delta_history_per_m','internal history')]:
            ax.plot(z,[r[key] for r in selected],'-o',markersize=4,label=lab)
        ax.axhline(0,linewidth=.8,color='gray')
        ax.set_xticks(list(z),labels)
        ax.set_xlabel('Distance from pore surface, mm (nonoverlapping groups)')
        ax.set_ylabel('H4W2 − H4 component contribution, m$^{-1}$')
        ax.set_title('$j_{peak}$: differences of three mechanical components')
        ax.grid(axis='y',alpha=.25)
        ax.legend(loc='best')
        fig.tight_layout()
        fig.savefig(out/'figures'/'P10Y_JPEAK_COARSE_COMPONENTS.png',dpi=180)
        fig.savefig(out/'figures'/'P10Y_JPEAK_COARSE_COMPONENTS.svg')
        plt.close(fig)
    except ImportError:
        print('matplotlib missing; CSVs generated without figures')
    print('P10Y_COARSE_AGGREGATION_OK', len(fine),len(coarse),len(cumulative),len(overview))
    for row in overview:print(row)

if __name__=='__main__':main()
