#!/usr/bin/env python3
"""P10CI R1. Read-only mesh-only diagnostic for three pinned Gmsh2 Tet10 meshes.

No solver, gmsh remesh, FEM preflight, Qt build, network, or edits of source meshes.
The geometric indicators use *straight corner tetrahedra and centroids*, NOT
the curved Tet10 QP Jacobian or an a-posteriori goal-error estimator.
Python 3 standard library only.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import math
from pathlib import Path
import secrets
import statistics
import sys
import time
import traceback
import zipfile

VERSION = 'P10CI_R1_MSH2_CORNER_CENTROID_AUDIT_NO_FEM'
EXPECTED_INDICATOR = '84b738960d712ba11eca880a86f98782905dc6dcc6cd3c72c70e4c97c42406c3'
MESHES = (
    ('H4W4B2', 'H4W4B2.msh', '3f6bf10717e566c5268e0b716e13c887365e0d3c61e46c156fdbe6ba1aa3d2c7', 367823, 261091),
    ('H4W4B20', 'H4W4B20_P10AB.msh', '94ab3df693265dbb4e7e723eb3c54642f4c385a465d91a1db4436ab66adc6715', 449522, 323052),
    ('H4W5B2', 'H4W5B2_P10AC.msh', 'db50a10fc2a12870bf6e678e2ef0be496feba218b1010f9e65f8669f67d093a8', 393998, 275549),
)
PORE_CENTER = (0.0, 0.0, 0.03)  # m
RADIUS_M = .001
EDGE_PAIRS = ((0,1),(1,2),(2,0),(0,3),(2,3),(1,3))
PHI_SECTORS = 12


def sha256_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda: f.read(4*1024*1024), b''):
            h.update(data)
    return h.hexdigest()


def percentile(values, p):
    if not values:
        return ''
    a = sorted(values)
    k = p*(len(a)-1)
    i = int(k)
    return a[i] + (a[min(i+1, len(a)-1)]-a[i])*(k-i)


def length(v):
    return math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])


def sub(a, b):
    return (a[0]-b[0],a[1]-b[1],a[2]-b[2])


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def geometry(p):
    """Straight-sided corner-Tet proxies, never a curved Tet10 quality proof."""
    a,b,c,d = p[:4]
    ab,ac,ad = sub(b,a),sub(c,a),sub(d,a)
    determinant = sum(x*y for x,y in zip(ab, cross(ac,ad)))
    lengths = [length(sub(p[i],p[j])) for i,j in EDGE_PAIRS]
    edge_max = max(lengths)
    volume = abs(determinant)/6.
    shape_quality = 12.*(3.*volume)**(2./3.)/sum(x*x for x in lengths) if volume>0 else 0.
    midside_deviation = 0.
    for k,(i,j) in enumerate(EDGE_PAIRS):
        midpoint = tuple((p[i][u]+p[j][u])*.5 for u in range(3))
        midside_deviation = max(midside_deviation, length(sub(p[k+4],midpoint))/max(lengths[k],1e-30))
    mid = tuple(sum(p[k][u] for k in range(4))*.25 for u in range(3))
    return determinant, volume, shape_quality, edge_max, midside_deviation, mid


def xyz_index(x):
    d = sub(x, PORE_CENTER)
    r = length(d)
    if r == 0 or not math.isfinite(r):
        raise ValueError('Geometry coordinate at pore center/nonfinite')
    mu = max(-1., min(1., d[2]/r))
    mu_band = max(0,min(9,int((mu+1.)*5.)))
    rho = math.hypot(d[0],d[1])
    phi = math.atan2(d[1], d[0]) % (2.*math.pi) if rho>0 else 0.
    phi_sector = min(PHI_SECTORS-1,int(phi*PHI_SECTORS/(2.*math.pi)))
    return (r-RADIUS_M)*1000.,mu_band,phi_sector,rho,phi


def phi_corner_span(corners):
    azimuths=[]
    for p in corners:
        dx,dy = p[0]-PORE_CENTER[0],p[1]-PORE_CENTER[1]
        if math.hypot(dx,dy)<1.e-13:
            return None
        azimuths.append(math.atan2(dy,dx)%(2.*math.pi))
    a=sorted(azimuths)
    gaps=[a[i+1]-a[i] for i in range(3)]+[a[0]+2.*math.pi-a[-1]]
    return math.degrees(2.*math.pi-max(gaps))


def load_indicator(path):
    if sha256_file(path)!=EXPECTED_INDICATOR:
        raise ValueError('P10CH indicator SHA-256 mismatch: STOP')
    with path.open(newline='',encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=200:
        raise ValueError('Indicator must have exactly 200 cells')
    radial=sorted({(float(x['r_lower_mm']),float(x['r_upper_mm'])) for x in rows})
    if len(radial)!=20 or any(abs(radial[i][1]-radial[i+1][0])>1e-8 for i in range(19)):
        raise ValueError('Indicator radial bin edges inconsistent')
    if abs(radial[0][0]-.02)>1.e-8 or abs(radial[-1][1]-.1)>1.e-8:
        raise ValueError('Expected indicator support 0.02–0.1 mm only')
    cellmap={}
    for x in rows:
        ring=(float(x['r_lower_mm']),float(x['r_upper_mm']))
        k=(radial.index(ring),int(x['polar_band']))
        if k in cellmap or not (0<=k[1]<10):
            raise ValueError('Repeated or invalid indicator cell')
        cellmap[k]={'selected':int(x['chosen_top_20pct']),
                    'priority':float(x['spatial_volume_normalized_consensus_rank']),
                    'bulk':float(x['delta_bulk_per_m']),
                    'wall':float(x['delta_wall_per_m'])}
    if len(cellmap)!=200 or sum(x['selected'] for x in cellmap.values())!=40:
        raise ValueError('Indicator selection invariant failed')
    return radial,cellmap


def radial_bin(mm, radial):
    if mm<radial[0][0] or mm>=radial[-1][1]:
        return None
    # Exactly 20 rings, intentionally simple and deterministic.
    for j,(lo,hi) in enumerate(radial):
        if lo<=mm<hi:
            return j
    return None


def skip_section(f, section):
    marker='$End'+section[1:]
    while True:
        line=f.readline()
        if not line:
            raise ValueError('Unclosed MSH section: '+section)
        if line.strip()==marker:
            break


def summarize_cell(mesh,cell,metric,stats):
    n=stats['n']
    phi=stats['phi']
    q=stats['q'];edges=stats['edge'];spans=stats['span'];curve=stats['curve']
    return {
        'mesh':mesh,'radial_bin':cell[0],'polar_band':cell[1],
        'selected_top40':metric['selected'],'priority':metric['priority'],
        'abs_delta_bulk_per_m':abs(metric['bulk']),'abs_delta_wall_per_m':abs(metric['wall']),
        'tet10_centroids':n,'corner_volume_proxy_m3':stats['volume'],
        'corner_quality_min':min(q) if q else '',
        'corner_quality_p05':percentile(q,.05),'corner_quality_p50':percentile(q,.5),
        'corner_quality_below_0p1':sum(v<.1 for v in q),
        'max_corner_edge_p50_mm':percentile(edges,.5),
        'phi_occupied_sectors':sum(v>0 for v in phi),
        'phi_sector_count_min':min(phi),'phi_sector_count_max':max(phi),
        'phi_sector_count_cv':(statistics.pstdev(phi)/statistics.mean(phi)) if n else '',
        'phi_corner_span_p50_deg':percentile(spans,.5),
        'phi_corner_span_p90_deg':percentile(spans,.9),
        'phi_span_gt90_count':sum(v>90 for v in spans),
        'phi_axis_unresolved_corners':stats['axis_unresolved'],
        'radial_cross_centroid_tets':stats['radial_cross'],
        'polar_cross_centroid_tets':stats['polar_cross'],
        'midside_dev_over_edge_p90':percentile(curve,.9),
        'corner_nonpositive_count':stats['corner_nonpositive'],
    }


def empty_stats():
    return {'n':0,'volume':0.,'q':[],'edge':[],'span':[],'curve':[],
            'phi':[0]*PHI_SECTORS,'radial_cross':0,'polar_cross':0,
            'axis_unresolved':0,'corner_nonpositive':0}


def analyze_mesh(name,path,expected_sha,expected_nodes,expected_tets,radial,cellmap):
    actual_sha=sha256_file(path)
    if actual_sha!=expected_sha:
        raise ValueError(f'{name}: pinned mesh SHA mismatch: observed {actual_sha}, expected {expected_sha}. STOP')
    t0=time.perf_counter()
    points=None;n_tets=0;n_elements=0;n_inside=0
    raw={k:empty_stats() for k in cellmap}
    nearwall={band:empty_stats() for band in range(10)}
    n_b6_other=0
    with path.open('r',encoding='utf-8',errors='strict') as f:
        if f.readline().strip()!='$MeshFormat':
            raise ValueError(name+': Gmsh format marker missing')
        fmt=f.readline().split()
        if len(fmt)<3 or not fmt[0].startswith('2.') or fmt[1]!='0':
            raise ValueError(name+': only Gmsh 2.x ASCII supported')
        if f.readline().strip()!='$EndMeshFormat':
            raise ValueError(name+': invalid format terminator')
        while True:
            line=f.readline()
            if not line:
                break
            label=line.strip()
            if label=='$Nodes':
                count=int(f.readline());points={}
                for i in range(count):
                    s=f.readline().split()
                    if len(s)!=4:
                        raise ValueError(name+': node line invalid')
                    node_id=int(s[0]);p=tuple(float(v) for v in s[1:])
                    if node_id in points or not all(math.isfinite(v) for v in p):
                        raise ValueError(name+': duplicate/nonfinite node')
                    points[node_id]=p
                if f.readline().strip()!='$EndNodes':
                    raise ValueError(name+': missing $EndNodes')
            elif label=='$Elements':
                if points is None:
                    raise ValueError(name+': $Elements before $Nodes')
                n_elements=int(f.readline())
                for i in range(n_elements):
                    s=f.readline().split()
                    if len(s)<3:
                        raise ValueError(name+': truncated element row')
                    if int(s[1])!=11:
                        continue
                    ntags=int(s[2]);ids=list(map(int,s[3+ntags:]))
                    if len(ids)!=10:
                        raise ValueError(name+': Tet10 must have 10 node IDs')
                    p=[points[j] for j in ids]
                    n_tets+=1
                    determinant,volume,q,edge_max,curve,mid=geometry(p)
                    d,b,ph,rho,_=xyz_index(mid)
                    rid=radial_bin(d,radial)
                    if rid is None:
                        if d<0:
                            n_inside+=1
                            continue
                        if 0.<=d<.02:
                            sraw=nearwall[b]
                        else:
                            if d<=5.0:
                                n_b6_other+=1
                            continue
                    else:
                        sraw=raw[(rid,b)]
                    sraw['n']+=1;sraw['volume']+=volume
                    sraw['q'].append(q);sraw['edge'].append(edge_max*1000.)
                    sraw['curve'].append(curve);sraw['phi'][ph]+=1
                    if determinant<=0:
                        sraw['corner_nonpositive']+=1
                    span=phi_corner_span(p[:4])
                    if span is None:
                        sraw['axis_unresolved']+=1
                    else:
                        sraw['span'].append(span)
                    locs=[xyz_index(x) for x in p[:4]]
                    if any(not ((0.<=x[0]<.02) if rid is None else
                                (radial_bin(x[0],radial)==rid)) for x in locs):
                        sraw['radial_cross']+=1
                    if any(x[1]!=b for x in locs):
                        sraw['polar_cross']+=1
                if f.readline().strip()!='$EndElements':
                    raise ValueError(name+': missing $EndElements')
            elif label.startswith('$') and not label.startswith('$End'):
                skip_section(f,label)
    if points is None or len(points)!=expected_nodes or n_tets!=expected_tets:
        raise ValueError(f'{name}: mesh count mismatch: nodes {len(points) if points else 0}, Tet10 {n_tets}')
    rows=[summarize_cell(name,k,cellmap[k],raw[k]) for k in sorted(raw)]
    first_wall_rows=[]
    for b in range(10):
        row=summarize_cell(name,(-1,b),{'selected':0,'priority':'','bulk':0.,'wall':0.},nearwall[b])
        row['abs_delta_bulk_per_m']='';row['abs_delta_wall_per_m']=''
        first_wall_rows.append(row)
    n_pore=sum(x['tet10_centroids'] for x in rows)
    return rows,first_wall_rows,{'mesh':name,'mesh_sha256':actual_sha,'node_count':len(points),
                 'tet10_count':n_tets,'all_element_records':n_elements,
                 'tet10_near_pore_centroids':n_pore,
                 'tet10_0_to_20um_centroids':sum(x['tet10_centroids'] for x in first_wall_rows),
                 'tet10_100um_to_B6_centroids':n_b6_other,
                 'tet10_centroid_inside_nominal_pore':n_inside,
                 'near_pore_corner_nonpositive_count':sum(x['corner_nonpositive_count'] for x in rows),
                 'seconds':time.perf_counter()-t0}


def group_rows(rows,cellmap):
    result=[]
    for mesh in [v[0] for v in MESHES]:
        part=[x for x in rows if x['mesh']==mesh]
        for group,pick in (
            ('top40',lambda x:x['selected_top40']==1),
            ('remaining160',lambda x:x['selected_top40']==0),
            ('polar0_9',lambda x:x['polar_band'] in (0,9)),
            ('middle1_8',lambda x:x['polar_band'] not in (0,9)),
        ):
            ss=[x for x in part if pick(x)]
            n=sum(x['tet10_centroids'] for x in ss)
            result.append({'mesh':mesh,'group':group,'cells':len(ss),
                'tet10_centroids':n,'straight_corner_volume_proxy_m3':sum(x['corner_volume_proxy_m3'] for x in ss),
                'corner_low_quality_below_0p1':sum(x['corner_quality_below_0p1'] for x in ss),
                'radial_cross_centroid_tets':sum(x['radial_cross_centroid_tets'] for x in ss),
                'polar_cross_centroid_tets':sum(x['polar_cross_centroid_tets'] for x in ss),
                'phi_axis_unresolved_corners':sum(x['phi_axis_unresolved_corners'] for x in ss),
                'corner_nonpositive_count':sum(x['corner_nonpositive_count'] for x in ss)})
    return result


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def selftest():
    a=1.
    p=((0,0,0),(a,0,0),(a/2,a*math.sqrt(3)/2,0),
       (a/2,a*math.sqrt(3)/6,a*math.sqrt(2/3)))
    full=p+tuple(tuple((p[i][j]+p[k][j])/2 for j in range(3)) for i,k in EDGE_PAIRS)
    det,v,q,edge,curve,_=geometry(full)
    assert det>0 and abs(q-1)<1e-12 and abs(edge-a)<1e-12 and curve==0
    assert xyz_index((0,0,.032))[1]==9
    assert xyz_index((0,0,.028))[1]==0
    assert phi_corner_span(((.001,0,.03),(0,.001,.03),(-.001,0,.03),(0,-.001,.03)))==270.
    print('P10CI_SYNTHETIC_GEOMETRY_UNIT_OK regular_tetra_quality=1 bins=10 phi_sectors=12 FEM=0')


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--selftest',action='store_true')
    a.add_argument('--mesh-root',type=Path)
    a.add_argument('--indicator',type=Path)
    opts=a.parse_args()
    if opts.selftest:
        selftest();return 0
    if not opts.mesh_root or not opts.indicator:
        a.error('--mesh-root and --indicator required outside selftest')
    runs=Path(__file__).resolve().parent/'P10CI_RUNS'
    runs.mkdir(exist_ok=True)
    out=runs/(datetime.now(timezone.utc).strftime('P10CI_%Y%m%d_%H%M%S_UTC_')+secrets.token_hex(3))
    out.mkdir(exist_ok=False)
    status='P10CI_MESH_ONLY_STOP';lines=['TOOL_REVISION='+VERSION,'PHYSICAL_FEM_RUNS=0',
            'SOURCE_MESH_WRITES=0','GMSH_REMESH=0','MESHER_CALLS=0']
    start=time.perf_counter()
    try:
        radial,cellmap=load_indicator(opts.indicator)
        lines+=['INDICATOR_SHA256='+EXPECTED_INDICATOR,'P10CH_CELLS=200','P10CH_TOP40=40']
        rows=[];summaries=[];uncovered=[]
        for name,filename,sha,nnode,ntet in MESHES:
            path=opts.mesh_root/filename
            if not path.is_file():
                raise FileNotFoundError(f'Expected exact mesh absent: {path}')
            this_rows,first_wall,summary=analyze_mesh(name,path,sha,nnode,ntet,radial,cellmap)
            rows+=this_rows;summaries.append(summary)
            uncovered+=first_wall
            print(f'{name}: PINNED_SHA_OK, {summary["tet10_count"]} Tet10, '
                  f'{summary["tet10_near_pore_centroids"]} near-pore centroids',flush=True)
        group=group_rows(rows,cellmap)
        write_csv(out/'P10CI_200CELL_MESH_GEOMETRY.csv',rows)
        write_csv(out/'P10CI_0_TO_20UM_UNCOVERED_POLE_GEOMETRY.csv',uncovered)
        write_csv(out/'P10CI_GROUP_SUMMARY.csv',group)
        write_csv(out/'P10CI_MESH_COUNTS.csv',summaries)
        lines+=['MESHES_PINNED_SHA_PASS=3/3','TOTAL_CELL_ROWS=600','UNCOVERED_WALL_0_TO_20UM_ROWS=30',
                'INDICATOR_RADIAL_SUPPORT_MM=0.02_TO_0.1','GROUP_SUMMARY_ROWS=12',
                'GEOMETRY_CLASSIFICATION=CORNER_CENTROID_APPROXIMATION_NOT_TET10_QP',
                'CURVED_TET10_JACOBIAN_POSITIVITY=NOT_CHECKED',
                'ADAPTIVE_M1_MESH_CREATED=NO','SPATIAL_CONVERGENCE_PROVEN=NO']
        status='P10CI_MESH_ONLY_GEOMETRY_OK_NO_FEM'
    except Exception as exc:
        lines+=['STOP_TYPE='+type(exc).__name__,'STOP_REASON='+str(exc)]
        (out/'P10CI_STOP_TRACE.txt').write_text(traceback.format_exc(),encoding='utf-8')
    lines+=['WALL_SECONDS='+str(round(time.perf_counter()-start,3)),
            'RESULT='+status]
    result=out/'P10CI_RESULT.txt'
    result.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    package=out/'P10CI_EVIDENCE.zip'
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for f in sorted(out.iterdir()):
            if f.is_file() and f.name!='P10CI_EVIDENCE.zip':
                z.write(f,f.name)
    print('RESULT='+status)
    print('EVIDENCE='+str(package))
    return 0 if status=='P10CI_MESH_ONLY_GEOMETRY_OK_NO_FEM' else 2


if __name__=='__main__':
    sys.exit(main())
