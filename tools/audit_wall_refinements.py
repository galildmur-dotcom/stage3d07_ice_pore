#!/usr/bin/env python3
"""Stage 3D-09D4. Independently check MSH2.2 pore-wall mesh refinement.
Uses NumPy (already needed by inspect_pore_mesh.py); no solver/Qt required.
Geometric checks do not replace full curved Tet10 Jacobian checks on deformations.
"""
from __future__ import annotations
import argparse, csv, json, pathlib, sys
from inspect_pore_mesh import check
LEVELS={'HP':1, 'HP2':2, 'HP4':4, 'HP8':8}

def audit(root:pathlib.Path, selected:list[str]):
    baseline=check(root/'meshes/HP.msh')
    data=[baseline]
    warnings=[]
    for name in selected:
        if name=='HP':continue
        f=LEVELS[name]
        path=root/f'meshes/{name}.msh'
        if not path.is_file():
            print(f'{name}: NOT GENERATED (source: gmsh/sphere_pore_{name}_wall.geo)')
            continue
        obj=check(path)
        actual=obj['pore_edge_median_mm']
        expected=baseline['pore_edge_median_mm']/f
        ratio=actual/expected
        if not (.85 <= ratio <= 1.15):raise RuntimeError(f'{name}: actual median {actual} mm; expected {expected} mm ±15%')
        if obj['pore_tri6'] < baseline['pore_tri6']*f*f*.67:raise RuntimeError(f'{name}: too few pore faces')
        obj['target_mm']=expected
        obj['actual_to_target']=ratio
        data.append(obj)
        print(f'{name}: {obj["nodes"]} nodes, {obj["tet10"]} Tet10, {obj["pore_tri6"]} pore faces; median {actual:.6f} mm, HP ratio={baseline["pore_edge_median_mm"]/actual:.3f}x')
    report=root/'HP_LEVELS_AUDIT.json'
    report.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print('P09D4_MESH_FAMILY_GEOMETRY_OK; audit:',report)
    return data

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parents[1])
    ap.add_argument('--levels',nargs='+',choices=LEVELS,default=['HP2','HP4','HP8'])
    args=ap.parse_args();audit(args.root,args.levels)
if __name__=='__main__':
    try:main()
    except Exception as exc:print('P09D4_AUDIT_ERROR:',exc,file=sys.stderr);sys.exit(2)
