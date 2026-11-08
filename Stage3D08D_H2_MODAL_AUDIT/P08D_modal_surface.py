#!/usr/bin/env python3
# Stage 3D-08D: L2-orthogonal 3-mode projection of a surface shape gradient.
# Python 3.8+, standard library ONLY. Reads P08D_SENSITIVITIES.csv.
# This is NOT an adjoint-derived pointwise gradient.
import argparse
import csv
import json
import math
from pathlib import Path

PI = math.pi
R_PORE = 0.001  # metres, from Stage3D07/src/tet10_shared.hpp imported mesh radius
C = (0.0, 0.0, 0.030)  # metres, physical pore centre


def y20(mu):
    # Exact normalization in Stage3D07/src/stage3d08_geometry.cpp
    return math.sqrt(5.0 / (16.0 * PI)) * (3.0 * mu * mu - 1.0)


def read_coefficients(csv_path):
    with open(csv_path, encoding='utf-8-sig', newline='') as fh:
        data = list(csv.DictReader(fh))
    if len(data) != 3 or {r.get('mode') for r in data} != {'R', 'tz', 'y20'}:
        raise ValueError('Expected exactly one row for each mode: R, tz, y20')
    rows = {r['mode']: r for r in data}
    common = ('mesh', 'dt_s', 'tend_s', 'quad', 'delta_um')
    for key in common:
        if len({r[key] for r in data}) != 1:
            raise ValueError('Inconsistent parameter: ' + key)
    r = float(rows['R']['delta_um'])
    if not (r > 0 and math.isfinite(r)):
        raise ValueError('Invalid delta_um')
    def moments(field):
        return [float(rows[m][field]) for m in ('R', 'tz', 'y20')]
    for field in ('mean_midpoint','variance_midpoint'):
        v = moments(field)
        if not all(math.isfinite(x) for x in v):
            raise ValueError('Nonfinite '+field)
        # Nominal geometry should be the same for the three central differences.
        # Midpoint values differ slightly due to O(delta^2) terms.
        avg = sum(v) / 3
        if max(abs(x-avg) for x in v) > 1e-5*max(abs(avg),1e-10):
            raise ValueError('Nominal moments diverge among shape modes: '+field)
    ds = {q:dict(zip(('R','tz','y20'), moments(q)))
          for q in ('D_mean_per_m','D_variance_per_m')}
    if any(not math.isfinite(a) for d in ds.values() for a in d.values()):
        raise ValueError('Nonfinite sensitivity')
    meta = {key:rows['R'][key] for key in common}
    return ds, meta


def gradient(mu, d, radius=R_PORE):
    # Three orthogonal surface modes: 1, mu, Y20(mu).
    # Modal directions are in metres of shape perturbation.
    area = 4*PI*radius*radius
    return (d['R']/area + 3*d['tz']/area*mu + d['y20']/(radius*radius)*y20(mu))


def test_projection(ds):
    # Integrate the projected gradient over the unperturbed sphere by
    # composite midpoint quadrature in mu=cos(theta), phi integrated exactly.
    n = 20000
    dmu = 2.0/n
    err = {}
    for name, d in ds.items():
        val = [0.0]*3
        for i in range(n):
            mu = -1+(i+0.5)*dmu
            g = gradient(mu,d)
            v = (1.,mu,y20(mu))
            for k in range(3):
                val[k]+=g*v[k]
        val = [x*dmu*2*PI*R_PORE*R_PORE for x in val]
        err[name] = {}
        for i, mode in enumerate(('R','tz','y20')):
            den = max(abs(d[mode]), 1e-12)
            err[name][mode] = abs(val[i]-d[mode])/den
            if err[name][mode]>1e-5:
                raise AssertionError('Projection moment failed: '+name+' '+mode+str(err[name][mode]))
    return err


def make_profiles(out, ds, meta):
    with (out/'P08D_MODAL_PROFILE.csv').open('w',encoding='utf-8',newline='') as fh:
        w = csv.writer(fh)
        w.writerow(('theta_deg','cos_theta','Y20','g_mean_per_m3', 'g_variance_per_m3'))
        for deg in range(181):
            mu=math.cos(math.radians(deg))
            w.writerow([deg,format(mu,'.17g'), format(y20(mu),'.17g'),
                        format(gradient(mu,ds['D_mean_per_m']),'.17g'),
                        format(gradient(mu,ds['D_variance_per_m']),'.17g')])


def make_vtk(out, ds, nlat=72, nlon=144):
    # ASCII legacy VTK POLYDATA, readable by ParaView without plugins.
    # Nodes at poles occur only once; all triangles have non-zero area.
    xyz = [(C[0],C[1],C[2]+R_PORE)]
    for i in range(1,nlat):
        t=PI*i/nlat
        for j in range(nlon):
            phi=2*PI*j/nlon
            xyz.append((C[0]+R_PORE*math.sin(t)*math.cos(phi),
                        C[1]+R_PORE*math.sin(t)*math.sin(phi),
                        C[2]+R_PORE*math.cos(t)))
    south = len(xyz)
    xyz.append((C[0],C[1],C[2]-R_PORE))
    def idx(i,j):
        return 1+(i-1)*nlon+(j % nlon)
    tri=[]
    for j in range(nlon): tri.append((0,idx(1,j),idx(1,j+1)))
    for i in range(1,nlat-1):
        for j in range(nlon):
            a,b,c,d=idx(i,j),idx(i,j+1),idx(i+1,j),idx(i+1,j+1)
            tri.append((a,c,b))
            tri.append((b,c,d))
    for j in range(nlon): tri.append((idx(nlat-1,j),south,idx(nlat-1,j+1)))
    path=out/'P08D_MODAL_SURFACE.vtk'
    with path.open('w',encoding='ascii',newline='\n') as f:
        f.write('# vtk DataFile Version 3.0\nP08D 3-mode surface projection; NOT adjoint pointwise sensitivity\nASCII\nDATASET POLYDATA\n')
        f.write('POINTS %d float\n'%len(xyz))
        for p in xyz:f.write('%.12g %.12g %.12g\n'%p)
        f.write('POLYGONS %d %d\n'%(len(tri),4*len(tri)))
        for a,b,c in tri:f.write('3 %d %d %d\n'%(a,b,c))
        f.write('POINT_DATA %d\n'%len(xyz))
        for name, func in (
                ('g_mean_per_m3',lambda mu:gradient(mu,ds['D_mean_per_m'])),
                ('g_variance_per_m3',lambda mu:gradient(mu,ds['D_variance_per_m'])),
                ('Y20', y20),
                ('cos_theta',lambda mu:mu)):
            f.write('SCALARS %s float 1\nLOOKUP_TABLE default\n'%name)
            for p in xyz:
                mu=max(-1.,min(1.,(p[2]-C[2])/R_PORE))
                f.write('%.12g\n'%func(mu))
    return len(xyz),len(tri)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sens',required=True,help='P08D_SENSITIVITIES.csv')
    p.add_argument('--out',required=True,help='Output directory, separate from FEM results')
    args=p.parse_args()
    ds,meta=read_coefficients(args.sens)
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    errors=test_projection(ds)
    make_profiles(out,ds,meta)
    pts,tri=make_vtk(out,ds)
    meta.update({'pore_radius_m':R_PORE,'pore_center_m':list(C),
      'reconstruction':'L2-orthogonal low-modal projection, not full shape gradient',
      'normal':'cavity to ice, n=e_r',
      'y20_normalization':'sqrt(5/(16*pi))*(3*cos(theta)**2-1)',
      'modal_derivatives':ds,
      'test_projection_relative_errors':errors,
      'vtk_points':pts,'vtk_triangles':tri})
    (out/'P08D_MODAL_METADATA.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SUCCESS',meta['mesh'], 'points',pts,'triangles',tri,'max_projection_err',max(max(v.values()) for v in errors.values()))
    print('Outputs:',str(out))

if __name__=='__main__':main()
